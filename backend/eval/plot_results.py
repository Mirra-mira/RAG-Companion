"""Tong hop ket qua tu track_a_*.json va ve bieu do (matplotlib).

Chay tu backend/ (sau khi da chay run_track_a):
    python -m eval.plot_results                          # dung file JSON moi nhat
    python -m eval.plot_results eval/results/track_a_20260107_123456.json

Dau ra:
  - Bang tong hop Markdown: eval/results/<ten_input>_summary.md
  - Bieu do PNG:           eval/results/images/*.png
"""
import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend -> chi save PNG, khong mo cua so
import matplotlib.pyplot as plt

from eval.metrics import confusion, mean, pct

# Thu tu metric trong bang tong hop
QUALITY_KEYS = ["precision", "recall", "mrr", "stale", "redundancy", "fp"]
QUALITY_LABELS = {
    "precision": "Precision@k",
    "recall":    "Recall@k",
    "mrr":       "MRR",
    "stale":     "Stale@k",
    "redundancy":"Redundancy@k",
    "fp":        "FP (no_relevant)",
}


# ---------------------------------------------------------------- IO
def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def latest_json(folder):
    files = sorted(glob.glob(str(Path(folder) / "track_a_*.json")))
    if not files:
        sys.exit(f"Khong tim thay file track_a_*.json nao trong {folder}. "
                 f"Hay chay `python -m eval.run_track_a` truoc.")
    return files[-1]


# ---------------------------------------------------------------- Aggregate
def aggregate_quality(queries):
    """Trung binh moi metric theo config (gop toan bo user + run)."""
    by_cfg = defaultdict(lambda: defaultdict(list))
    for q in queries:
        for k, v in q["metrics"].items():
            by_cfg[q["config"]][k].append(v)
    return {cfg: {k: mean(vs) if vs else float("nan") for k, vs in m.items()}
            for cfg, m in by_cfg.items()}


def aggregate_latency(queries, writes):
    r = defaultdict(list)
    w = defaultdict(list)
    for q in queries:
        r[q["config"]].append(q["timings"]["total"])
    for ww in writes:
        w[ww["config"]].append(ww["timings"]["total"])
    cfgs = sorted(set(list(r) + list(w)))
    return {c: {
        "read_p50":  pct(r[c], 50) if r[c] else 0,
        "read_p95":  pct(r[c], 95) if r[c] else 0,
        "write_p50": pct(w[c], 50) if w[c] else 0,
        "write_p95": pct(w[c], 95) if w[c] else 0,
    } for c in cfgs}


def aggregate_dedup(writes):
    """Accuracy dedup theo config.
    Chi tinh cho config THUC SU co dedup (pred co the khac ADD).
    NoDedupService luon pred=ADD -> accuracy = ty le ADD trong gold, vo nghia.
    """
    by_cfg = defaultdict(list)
    for ww in writes:
        by_cfg[ww["config"]].append((ww["gold"], ww["pred"]))
    out = {}
    for cfg, pairs in by_cfg.items():
        preds = {p for _, p in pairs}
        if preds <= {"ADD"}:
            continue
        if pairs:
            _, acc = confusion(pairs)
            out[cfg] = acc
    return out


# ---------------------------------------------------------------- Plots
def _nan_to_zero(xs):
    return [0.0 if v != v or v is None else v for v in xs]


def plot_quality(agg, out_path):
    cfgs = list(agg)
    metrics = ["precision", "recall", "mrr"]
    width = 0.25
    x = list(range(len(cfgs)))
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, m in enumerate(metrics):
        values = _nan_to_zero([agg[c].get(m) for c in cfgs])
        ax.bar([xi + i * width for xi in x], values, width, label=QUALITY_LABELS[m])
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(cfgs, rotation=30, ha="right")
    ax.set_ylabel("Điểm số")
    ax.set_title("Chất lượng truy hồi theo cấu hình")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_stale_redundancy(agg, out_path):
    cfgs = list(agg)
    stale  = _nan_to_zero([agg[c].get("stale") for c in cfgs])
    redund = _nan_to_zero([agg[c].get("redundancy") for c in cfgs])
    width = 0.35
    x = list(range(len(cfgs)))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([xi - width/2 for xi in x], stale,  width, label="Stale@k",      color="#d62728")
    ax.bar([xi + width/2 for xi in x], redund, width, label="Redundancy@k", color="#ff7f0e")
    ax.set_xticks(x)
    ax.set_xticklabels(cfgs, rotation=30, ha="right")
    ax.set_ylabel("Tỷ lệ")
    ax.set_title("Tỷ lệ fact lỗi thời (stale) và trùng lặp (redundancy)")
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_latency(lat, out_path):
    cfgs = list(lat)
    read_p50  = [lat[c]["read_p50"]  for c in cfgs]
    read_p95  = [lat[c]["read_p95"]  for c in cfgs]
    write_p50 = [lat[c]["write_p50"] for c in cfgs]
    write_p95 = [lat[c]["write_p95"] for c in cfgs]
    width = 0.2
    x = list(range(len(cfgs)))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([xi - 1.5*width for xi in x], read_p50,  width, label="Read p50")
    ax.bar([xi - 0.5*width for xi in x], read_p95,  width, label="Read p95")
    ax.bar([xi + 0.5*width for xi in x], write_p50, width, label="Write p50")
    ax.bar([xi + 1.5*width for xi in x], write_p95, width, label="Write p95")
    ax.set_xticks(x)
    ax.set_xticklabels(cfgs, rotation=30, ha="right")
    ax.set_ylabel("Độ trễ (ms)")
    ax.set_title("Độ trễ read/write theo cấu hình")
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_dedup(ded, out_path):
    cfgs = list(ded)
    acc  = [ded[c] for c in cfgs]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(cfgs, acc, color="#2ca02c")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Độ chính xác")
    ax.set_title("Độ chính xác dedup (so với gold action)")
    for i, v in enumerate(acc):
        ax.text(i, v + 0.02, f"{v:.3f}", ha="center")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- Markdown
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fmt(v):
    return "-" if v is None or v != v else f"{v:.3f}"


def build_markdown(src, agg, lat, ded, img_rel):
    lines = [
        "# Tong hop ket qua Track A",
        "",
        f"Nguon du lieu: `{src}`",
        "",
        "## 1. Chat luong truy hoi (trung binh toan dataset)",
        "",
        md_table(
            ["Config"] + [QUALITY_LABELS[k] for k in QUALITY_KEYS],
            [[c] + [fmt(agg[c].get(k)) for k in QUALITY_KEYS] for c in agg],
        ),
        "",
        f"![quality]({img_rel}/quality_by_config.png)",
        "",
        f"![stale]({img_rel}/stale_by_config.png)",
        "",
        "## 2. Do tre (ms)",
        "",
        md_table(
            ["Config", "Read p50", "Read p95", "Write p50", "Write p95"],
            [[c, f"{lat[c]['read_p50']:.0f}", f"{lat[c]['read_p95']:.0f}",
              f"{lat[c]['write_p50']:.0f}", f"{lat[c]['write_p95']:.0f}"] for c in lat],
        ),
        "",
        f"![latency]({img_rel}/latency_by_config.png)",
        "",
    ]
    if ded:
        lines += [
            "## 3. Do chinh xac dedup",
            "",
            md_table(["Config", "Accuracy"], [[c, f"{v:.3f}"] for c, v in ded.items()]),
            "",
            f"![dedup]({img_rel}/dedup_accuracy.png)",
            "",
        ]
    return "\n".join(lines)


# ---------------------------------------------------------------- Main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="Duong dan JSON (bo trong = tim file moi nhat)")
    ap.add_argument("--results-dir", default="eval/results")
    ap.add_argument("--out-dir",     default="eval/results")
    args = ap.parse_args()

    src = args.src or latest_json(args.results_dir)
    data = load(src)
    agg = aggregate_quality(data["queries"])
    lat = aggregate_latency(data["queries"], data["writes"])
    ded = aggregate_dedup(data["writes"])

    out_dir = Path(args.out_dir)
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    plot_quality(agg,  img_dir / "quality_by_config.png")
    plot_stale_redundancy(agg, img_dir / "stale_by_config.png")
    plot_latency(lat,  img_dir / "latency_by_config.png")
    if ded:
        plot_dedup(ded, img_dir / "dedup_accuracy.png")

    md_path = out_dir / (Path(src).stem + "_summary.md")
    md_path.write_text(build_markdown(src, agg, lat, ded, "images"), encoding="utf-8")

    print("Da sinh:")
    print(f"  - Bang tong hop: {md_path}")
    print(f"  - Bieu do: {img_dir}/")


if __name__ == "__main__":
    main()
