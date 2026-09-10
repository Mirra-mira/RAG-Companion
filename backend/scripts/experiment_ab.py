"""A/B experiment cho muc 4.5 doc chuong 4.

So sanh chat luong hoi thoai giua 2 che do:
  A (baseline) : ENABLE_MEMORY=false -> LLM tra loi khong facts, khong summary,
                 khong recent turns.
  B (de xuat)  : ENABLE_MEMORY=true  -> pipeline day du (RAG + short-term memory).

Cach chay:
    cd backend
    ./venv/Scripts/python.exe -X utf8 scripts/experiment_ab.py

Output: experiment_results.md o project root (canh doc.txt).

Metric tu dong (khong can nguoi cham):
  - Latency e2e trung binh va p95 tren tung mode
  - Recall hit rate: cac turn co keyword ky vong -> response co chua keyword
    day khong (bang chung so LLM "nho" duoc thong tin)

Metric thu cong (tac gia dien vao file MD sau khi doc):
  - Coherence 1-5 cho tung scenario o tung mode
"""
import sys
import time
import os
from pathlib import Path
from datetime import datetime

# Them backend/ vao sys.path de import 'app' khi chay script tu thu muc bat ky
_BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_DIR))

# Bat buoc set truoc khi import app: config.py load env luc import.
os.environ["ENABLE_MEMORY"] = "true"  # default; se override tung mode ben duoi

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.db import get_conn


# ----- KICH BAN THU NGHIEM -----
# Moi turn: msg = cau nguoi dung gui, expect = list keyword ky vong xuat hien
# trong response (dung de do recall hit tu dong). None = khong do (turn cung cap
# thong tin, khong phai turn kiem tra).
SCENARIOS = [
    {
        "name": "P1_memory_recall",
        "desc": "Nhac lai thong tin da cung cap 4-5 turn truoc",
        "turns": [
            {"msg": "Xin chao, minh ten la Chinh, minh 22 tuoi, dang la sinh vien nam cuoi.", "expect": None},
            {"msg": "Mon an minh thich nhat la pho bo Ha Noi.", "expect": None},
            {"msg": "So thich cua minh la choi guitar va doc sach vao cuoi tuan.", "expect": None},
            {"msg": "Hom nay troi kha dep phai khong nhi?", "expect": None},
            {"msg": "Ban co nho minh ten gi khong?", "expect": ["chinh"]},
            {"msg": "The minh bao nhieu tuoi thi ban con nho khong?", "expect": ["22", "hai muoi hai"]},
            {"msg": "Mon an yeu thich cua minh la gi ban con nho khong?", "expect": ["pho"]},
        ],
    },
    {
        "name": "P2_naming_inheritance",
        "desc": "Dat ten cho AI, sau do goi bang ten hoac dai tu -> AI co hieu la chinh no khong",
        "turns": [
            {"msg": "Tu bay gio minh se dat ten cho ban la Yu nhe, ban dong y khong?", "expect": None},
            {"msg": "Minh dang cang thang vi deadline khoa luan cuoi ky.", "expect": None},
            {"msg": "Yu oi, giup minh do cang thang di.", "expect": ["yu", "minh", "toi"]},
            {"msg": "Cam on co ay da giup minh nhe.", "expect": ["yu", "minh", "toi"]},
        ],
    },
    {
        "name": "P3_topic_switch",
        "desc": "Nhieu chu de xen ke, sau do quay lai chu de dau tien -> AI co nho ngu canh cu khong",
        "turns": [
            {"msg": "Minh rat thich Nhat Ban, dac biet la Kyoto co nhung ngoi den co kinh.", "expect": None},
            {"msg": "Ngoai ra minh cung dang hoc lap trinh Python de lam khoa luan.", "expect": None},
            {"msg": "Cuoi tuan minh thuong xem anime, gan day dang cay Frieren.", "expect": None},
            {"msg": "Quay lai chuyen Kyoto minh vua noi luc dau, ban co goi y noi nao nen tham khong?", "expect": ["kyoto", "den", "chua", "gion", "arashiyama", "kiyomizu"]},
        ],
    },
]


def truncate_db():
    with get_conn() as conn:
        conn.execute("TRUNCATE facts, users, conversations CASCADE")
        conn.commit()


def create_user(client: TestClient, name: str) -> str:
    res = client.post("/dev/create-user", json={"username": name})
    assert res.status_code == 200, f"create-user failed: {res.status_code} {res.text}"
    return res.json()["user_id"]


def send_chat(client: TestClient, user_id: str, message: str) -> dict:
    """Gui 1 message, tra ve dict {response, retrieved_facts, latency_ms}."""
    t0 = time.time()
    res = client.post("/chat", json={"user_id": user_id, "message": message})
    latency_ms = (time.time() - t0) * 1000
    assert res.status_code == 200, f"chat failed: {res.status_code} {res.text}"
    data = res.json()
    return {
        "response": data["response"],
        "retrieved_facts": data["retrieved_facts"],
        "latency_ms": latency_ms,
    }


def check_recall(response: str, expect: list[str] | None) -> bool | None:
    """None neu turn khong co ky vong (khong tinh vao recall rate).
    True neu response chua it nhat 1 keyword ky vong (case-insensitive)."""
    if expect is None:
        return None
    lower = response.lower()
    return any(kw.lower() in lower for kw in expect)


def run_scenario(client: TestClient, scenario: dict, mode: str) -> dict:
    """Chay 1 scenario o 1 mode. Tra ve dict co results per-turn + aggregate."""
    user_id = create_user(client, f"exp_{scenario['name']}_{mode}")
    print(f"  [{mode}] {scenario['name']} (user={user_id[:8]}...):")

    turn_results = []
    for i, turn in enumerate(scenario["turns"], start=1):
        result = send_chat(client, user_id, turn["msg"])
        recall = check_recall(result["response"], turn["expect"])
        turn_results.append({
            "turn": i,
            "msg": turn["msg"],
            "expect": turn["expect"],
            "response": result["response"],
            "latency_ms": result["latency_ms"],
            "retrieved_count": len(result["retrieved_facts"]),
            "retrieved_facts": [(f["content"], round(f.get("score", 0), 3)) for f in result["retrieved_facts"]],
            "recall": recall,
        })
        marker = "" if recall is None else (" ✓" if recall else " ✗")
        print(f"    turn {i}: {result['latency_ms']:.0f}ms retrieved={len(result['retrieved_facts'])}{marker}")
        # Cho background write_path (extract + dedup + summarize) chay xong
        time.sleep(2.5)

    latencies = [t["latency_ms"] for t in turn_results]
    recalls = [t["recall"] for t in turn_results if t["recall"] is not None]
    return {
        "scenario": scenario["name"],
        "desc": scenario["desc"],
        "mode": mode,
        "turns": turn_results,
        "avg_latency_ms": sum(latencies) / len(latencies),
        "max_latency_ms": max(latencies),
        "recall_total": len(recalls),
        "recall_hits": sum(1 for r in recalls if r),
    }


def format_md(all_results: list[dict]) -> str:
    """Format ket qua thanh markdown de dua vao doc.txt muc 4.5.4."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = [
        "# A/B Experiment Results — Muc 4.5.4 doc chuong 4",
        "",
        f"- Ngay chay: {now}",
        "- Model: gemini-2.5-flash (paid tier)",
        "- Che do A (baseline): ENABLE_MEMORY=false, LLM chi thay cau hoi hien tai.",
        "- Che do B (de xuat) : ENABLE_MEMORY=true, day du RAG + short-term memory.",
        "",
        "## Bang tong hop (tu dong)",
        "",
        "| Scenario | Mode | Avg latency (ms) | Max latency (ms) | Recall hit / total | Recall % |",
        "|---|---|---|---|---|---|",
    ]
    for r in all_results:
        pct = f"{100 * r['recall_hits'] / r['recall_total']:.0f}%" if r["recall_total"] else "n/a"
        md.append(
            f"| {r['scenario']} | {r['mode']} | {r['avg_latency_ms']:.0f} "
            f"| {r['max_latency_ms']:.0f} | {r['recall_hits']}/{r['recall_total']} | {pct} |"
        )

    # Aggregate per mode
    md.append("")
    md.append("### Trung binh theo mode")
    md.append("")
    md.append("| Mode | Avg latency (ms) | Recall hit / total | Recall % |")
    md.append("|---|---|---|---|")
    for mode in ("A", "B"):
        subset = [r for r in all_results if r["mode"] == mode]
        avg_lat = sum(r["avg_latency_ms"] for r in subset) / len(subset)
        total_hits = sum(r["recall_hits"] for r in subset)
        total_all = sum(r["recall_total"] for r in subset)
        pct = f"{100 * total_hits / total_all:.0f}%" if total_all else "n/a"
        md.append(f"| {mode} | {avg_lat:.0f} | {total_hits}/{total_all} | {pct} |")

    md.append("")
    md.append("## Bang cham coherence thu cong (tac gia dien)")
    md.append("")
    md.append("Sau khi doc chi tiet tung scenario o phan ke duoi, cham diem 1-5 cho tung mode:")
    md.append("")
    md.append("| Scenario | Coherence A | Coherence B | Ghi chu |")
    md.append("|---|---|---|---|")
    for s in SCENARIOS:
        md.append(f"| {s['name']} | ___/5 | ___/5 | |")
    md.append("")
    md.append("Thang cham goi y:")
    md.append("- 1: khong hieu boi canh, tra loi lac de")
    md.append("- 2: hieu 1 phan, mat mach")
    md.append("- 3: tra loi duoc nhung khong dung ngu canh sau")
    md.append("- 4: nam duoc mach hoi thoai, thieu chi tiet nho")
    md.append("- 5: hieu day du, tra loi tu nhien, nho dung thong tin")

    # Chi tiet per scenario
    md.append("")
    md.append("---")
    md.append("")
    md.append("## Chi tiet tung scenario")

    # Group results by scenario
    by_scenario = {}
    for r in all_results:
        by_scenario.setdefault(r["scenario"], {})[r["mode"]] = r

    for scn in SCENARIOS:
        name = scn["name"]
        md.append("")
        md.append(f"### {name} — {scn['desc']}")
        md.append("")

        results_ab = by_scenario.get(name, {})
        for i, turn in enumerate(scn["turns"], start=1):
            expect_str = ", ".join(turn["expect"]) if turn["expect"] else "-"
            md.append(f"**Turn {i}** (expect keyword: `{expect_str}`)")
            md.append(f"> User: {turn['msg']}")
            md.append("")
            for mode in ("A", "B"):
                r = results_ab.get(mode)
                if not r:
                    continue
                t = r["turns"][i - 1]
                recall_mark = ""
                if t["recall"] is not None:
                    recall_mark = " ✓" if t["recall"] else " ✗"
                md.append(f"- **Mode {mode}** ({t['latency_ms']:.0f}ms, retrieved={t['retrieved_count']}){recall_mark}:")
                # indent response
                for line in t["response"].split("\n"):
                    md.append(f"    > {line}")
                if t["retrieved_facts"]:
                    facts_str = ", ".join(f'"{c}"({s})' for c, s in t["retrieved_facts"])
                    md.append(f"    - retrieved facts: {facts_str}")
                md.append("")

    return "\n".join(md)


def main():
    print("=" * 60)
    print("A/B Experiment — muc 4.5 doc chuong 4")
    print("=" * 60)
    print(f"USE_MOCK_LLM = {settings.USE_MOCK_LLM} (phai la False de dung Gemini that)")
    assert not settings.USE_MOCK_LLM, "Can bo USE_MOCK_LLM=true trong .env de chay real Gemini."

    print("Truncate DB truoc khi chay...")
    truncate_db()

    client = TestClient(app)
    all_results = []

    for mode in ("A", "B"):
        # Override flag runtime (do dung TestClient in-process, khong can restart)
        settings.ENABLE_MEMORY = (mode == "B")
        print(f"\n=== MODE {mode} (ENABLE_MEMORY={settings.ENABLE_MEMORY}) ===")
        for scn in SCENARIOS:
            result = run_scenario(client, scn, mode)
            all_results.append(result)

    print("\n" + "=" * 60)
    print("Ghi ket qua ra file...")

    md = format_md(all_results)
    # Ghi ra project root, canh doc.txt
    out_path = Path(__file__).resolve().parents[2] / "experiment_results.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"Da ghi: {out_path}")

    # Print quick summary
    print("\n--- Tom tat ---")
    for mode in ("A", "B"):
        subset = [r for r in all_results if r["mode"] == mode]
        avg_lat = sum(r["avg_latency_ms"] for r in subset) / len(subset)
        total_hits = sum(r["recall_hits"] for r in subset)
        total_all = sum(r["recall_total"] for r in subset)
        pct = 100 * total_hits / total_all if total_all else 0
        print(f"  Mode {mode}: avg_latency={avg_lat:.0f}ms  recall={total_hits}/{total_all} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
