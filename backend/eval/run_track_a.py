"""Track A — danh gia Retrieval & Dedup tren gold facts.

Chay tu thu muc backend/ (da activate venv, DB dang chay):
    python -m eval.run_track_a                       # chay du 6 cau hinh
    python -m eval.run_track_a --configs P_hybrid+dedup,B2_vector --repeats 3
    python -m eval.run_track_a --no-cache            # lan chay cuoi de do do tre
    python -m eval.run_track_a --allow-mock          # chi de smoke-test luong chay

Bo qua extraction: nap thang `facts` da gan nhan qua dedup.process(), ghi lai
fact_id -> gold key de tinh Precision/Recall/MRR/Stale/Redundancy chinh xac.
"""
import argparse
import glob
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.db import get_conn
from app.repositories.fact_repository import FactRepository
from app.services.embedding_provider import get_embedding_provider
from app.services.llm_provider import get_llm_provider
from app.services.dedup_service import DedupService
from app.services.baselines import NoDedupService
from app.services.ranking_service import RankingService
from app.services.retrievers import make_retriever
from eval.metrics import ACTIONS, confusion, mean, pct, score_query, std

# ten cau hinh -> (retriever, bat dedup?)
CONFIGS = {
    "B0_none": ("none", False),
    "B1_keyword": ("keyword", False),
    "B2_vector": ("vector", False),
    "A1_vector+dedup": ("vector", True),
    "A2_hybrid": ("hybrid", False),
    "P_hybrid+dedup": ("hybrid", True),
}
QUALITY_KEYS = ["precision", "recall", "mrr", "stale", "redundancy", "fp"]


# ----------------------------------------------------------------- wrappers
def _retry(fn, stats, tries=5, base=2.0):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # 429 / loi mang cua Gemini
            stats["retries"] += 1
            if i == tries - 1:
                raise
            print(f"   [retry {i + 1}/{tries - 1}] {type(e).__name__}: {str(e)[:80]}")
            time.sleep(base * 2 ** i)


class SafeEmbedder:
    """Retry + cache embedding (cache lam do tre embedding bi sai -> xem --no-cache)."""

    def __init__(self, inner, cache, tag, stats):
        self.inner, self.cache, self.tag, self.stats = inner, cache, tag, stats

    def embed(self, text):
        key = f"{self.tag}|{text}"
        if self.cache is not None and key in self.cache:
            return self.cache[key]
        vec = _retry(lambda: self.inner.embed(text), self.stats)
        if self.cache is not None:
            self.cache[key] = vec
        return vec


class SafeLLM:
    def __init__(self, inner, stats):
        self.inner, self.stats = inner, stats

    def classify_relationship(self, new_fact, candidates):
        return _retry(lambda: self.inner.classify_relationship(new_fact, candidates), self.stats)


# ----------------------------------------------------------------- DB helpers
def create_user(name):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO users (username) VALUES (%s) RETURNING user_id", (name,)
        ).fetchone()
        conn.commit()
        return row[0]


def delete_users(ids):
    if not ids:
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM users WHERE user_id = ANY(%s)", (ids,))
        conn.commit()


def set_age(fact_id, days):
    """Lui moc thoi gian cua fact (de test recency decay)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE facts SET created_at = now() - make_interval(days => %s), "
            "updated_at = now() - make_interval(days => %s) WHERE fact_id = %s",
            (days, days, fact_id),
        )
        conn.commit()


# ----------------------------------------------------------------- core run
def run_user(user, cfg, retr, dedup, k, sleep, run_id, user_ids):
    uid = create_user(f"eval_{run_id}_{cfg}_{user['user_key']}")
    user_ids.append(uid)
    row2key = {}
    facts = sorted(user["facts"], key=lambda f: f["turn"])  # sort on dinh
    queries = sorted(user["queries"], key=lambda q: q["after_turn"])
    fi, writes, qrecs = 0, [], []

    for q in queries:
        while fi < len(facts) and facts[fi]["turn"] <= q["after_turn"]:
            f = facts[fi]
            fi += 1
            out = dedup.process(uid, f["category"], f["content"])
            canon = f["target"] if f["action"] == "REINFORCE" else f["key"]
            if out.get("fact"):
                row2key.setdefault(str(out["fact"]["fact_id"]), canon)
                if f.get("age_days") and out["action"] in ("ADD", "CONFLICT"):
                    set_age(out["fact"]["fact_id"], f["age_days"])
            writes.append({"run": run_id, "config": cfg, "user": user["user_key"],
                           "key": f["key"], "gold": f["action"], "pred": out["action"],
                           "timings": out["timings"]})
            time.sleep(sleep)

        results, timings = retr.retrieve_timed(uid, q["text"], top_k=k)
        keys = [row2key.get(str(r["fact_id"])) or f"?{r['fact_id']}" for r in results]
        m = score_query(q, keys)
        qrecs.append({"run": run_id, "config": cfg, "user": user["user_key"],
                      "qid": q["qid"], "type": q["type"], "keys": keys,
                      "metrics": m, "timings": timings})
        time.sleep(sleep)
    return writes, qrecs


# ----------------------------------------------------------------- reporting
def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fmt(v):
    return "-" if v is None or v != v else f"{v:.3f}"


def metric_vals(recs, key):
    return [r["metrics"][key] for r in recs if key in r["metrics"]]


def report(configs, qrecs, writes, repeats, cache_on):
    print("\n## Bang 1 — Chat luong truy hoi (trung binh; ± = do lech chuan giua cac lan chay)\n")
    rows = []
    for c in configs:
        recs = [r for r in qrecs if r["config"] == c]
        cells = []
        for key in QUALITY_KEYS:
            per_run = []
            for run in range(repeats):
                vals = metric_vals([r for r in recs if r["run"] == run], key)
                if vals:
                    per_run.append(mean(vals))
            cells.append("-" if not per_run else
                         f"{mean(per_run):.3f}" + (f" ± {std(per_run):.3f}" if repeats > 1 else ""))
        rows.append([c] + cells)
    print(table(["Config", "P@k", "R@k", "MRR", "Stale@k", "Redund.@k", "FP (no_relevant)"], rows))

    print("\n## Bang 2 — Theo loai query\n")
    types = sorted({r["type"] for r in qrecs})
    rows = []
    for c in configs:
        for t in types:
            recs = [r for r in qrecs if r["config"] == c and r["type"] == t]
            rows.append([c, t, len(recs)] + [fmt(mean(metric_vals(recs, k)) if metric_vals(recs, k) else None)
                                              for k in QUALITY_KEYS])
    print(table(["Config", "Type", "n", "P@k", "R@k", "MRR", "Stale@k", "Redund.@k", "FP"], rows))

    print("\n## Bang 3 — Do chinh xac dedup (so voi gold action)\n")
    for c in configs:
        if not CONFIGS[c][1]:
            continue
        pairs = [(w["gold"], w["pred"]) for w in writes if w["config"] == c]
        mat, acc = confusion(pairs)
        print(f"**{c}** — accuracy = {acc:.3f} (n={len(pairs)})\n")
        print(table(["gold \\ pred"] + ACTIONS,
                    [[g] + [mat[g][p] for p in ACTIONS] for g in ACTIONS[:3]]))
        print()

    print("## Bang 4 — Do tre (ms)\n")
    if cache_on:
        print("> CANH BAO: cache embedding dang BAT -> do tre embed bi thap gia tao. "
              "Chay lai voi --no-cache truoc khi dua so nay vao bao cao.\n")
    rows = []
    for c in configs:
        rt = [r["timings"]["total"] for r in qrecs if r["config"] == c]
        wt = [w["timings"]["total"] for w in writes if w["config"] == c]
        stages = defaultdict(list)
        for r in qrecs:
            if r["config"] == c:
                for s, v in r["timings"].items():
                    if s != "total":
                        stages[s].append(v)
        detail = ", ".join(f"{s}={mean(v):.0f}" for s, v in stages.items()) or "-"
        rows.append([c, f"{pct(rt, 50):.0f}", f"{pct(rt, 95):.0f}",
                     f"{pct(wt, 50):.0f}", f"{pct(wt, 95):.0f}", detail])
    print(table(["Config", "Read p50", "Read p95", "Write p50", "Write p95", "Read stage mean"], rows))


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="eval/dataset")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--k", type=int, default=settings.RANK_TOP_K)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--sleep", type=float, default=0.0, help="nghi giua cac thao tac (tranh rate limit)")
    ap.add_argument("--no-cache", action="store_true", help="tat cache embedding (de do do tre)")
    ap.add_argument("--keep", action="store_true", help="giu lai user/facts trong DB sau khi chay")
    ap.add_argument("--allow-mock", action="store_true")
    ap.add_argument("--out", default="eval/results")
    args = ap.parse_args()

    if settings.USE_MOCK_LLM and not args.allow_mock:
        sys.exit("Dang o che do MOCK (thieu GEMINI_API_KEY hoac USE_MOCK_LLM=true). "
                 "So lieu tren mock vo nghia; dung --allow-mock neu chi smoke-test.")

    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in configs:
        if c not in CONFIGS:
            sys.exit(f"Config khong hop le: {c}. Hop le: {list(CONFIGS)}")

    users = []
    for p in sorted(glob.glob(str(Path(args.data) / "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        if "turns" in d and "facts" in d:
            users.append(d)
    if not users:
        sys.exit(f"Khong tim thay user nao trong {args.data}")
    print(f"{len(users)} user, {len(configs)} config, repeats={args.repeats}, k={args.k}, "
          f"mock={settings.USE_MOCK_LLM}, embed_cache={not args.no_cache}")

    stats = {"retries": 0}
    tag = "mock" if settings.USE_MOCK_LLM else f"gemini-embedding-001-{settings.EMBEDDING_DIM}"
    cache_path = Path("eval/.embed_cache.json")
    cache = None
    if not args.no_cache:
        cache = json.load(open(cache_path)) if cache_path.exists() else {}
    repo = FactRepository(get_conn)
    embedder = SafeEmbedder(get_embedding_provider(), cache, tag, stats)
    llm = SafeLLM(get_llm_provider(), stats)
    ranker = RankingService()

    qrecs, writes, user_ids = [], [], []
    try:
        for run in range(args.repeats):
            for cfg in configs:
                kind, dedup_on = CONFIGS[cfg]
                retr = make_retriever(kind, repo, embedder, ranker)
                dedup = (DedupService(repo, embedder, llm) if dedup_on
                         else NoDedupService(repo, embedder))
                print(f"[run {run + 1}/{args.repeats}] {cfg}")
                for u in users:
                    w, q = run_user(u, cfg, retr, dedup, args.k, args.sleep, run, user_ids)
                    writes += w
                    qrecs += q
    finally:
        if cache is not None:
            json.dump(cache, open(cache_path, "w"))
        if not args.keep:
            delete_users(user_ids)

    report(configs, qrecs, writes, args.repeats, cache is not None)
    print(f"\n(retry API: {stats['retries']} lan — neu > 0 thi do tre cua cac mau bi retry bi phong dai)")

    Path(args.out).mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) / f"track_a_{datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump({"args": vars(args), "queries": qrecs, "writes": writes},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"Raw ket qua: {out_path}")


if __name__ == "__main__":
    main()
