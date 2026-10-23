"""Ham tinh chi so thuan (khong phu thuoc DB/LLM) — de test don vi duoc."""
import math

ACTIONS = ["ADD", "REINFORCE", "CONFLICT", "NOOP"]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def std(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pct(xs, p):
    """Percentile noi suy tuyen tinh (p trong 0..100)."""
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = (len(xs) - 1) * p / 100
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def score_query(q: dict, keys: list[str]) -> dict:
    """keys = gold key chuan cua tung row tra ve, theo thu tu hang.

    - Query co `relevant`: precision, recall, mrr (+ stale, redundancy)
    - Query no_relevant (relevant rong): fp = 1 neu tra ve bat ky row nao
    Quy uoc: khong tra ve row nao -> precision = 0 (khi co relevant).
    """
    R, S = set(q.get("relevant", [])), set(q.get("stale", []))
    n = len(keys)
    m = {
        "n_returned": n,
        "stale": (sum(k in S for k in keys) / n) if n else 0.0,
        "redundancy": (1 - len(set(keys)) / n) if n else 0.0,
    }
    if R:
        m["precision"] = (sum(k in R for k in keys) / n) if n else 0.0
        m["recall"] = len(R & set(keys)) / len(R)
        rr = 0.0
        for i, k in enumerate(keys, 1):
            if k in R:
                rr = 1 / i
                break
        m["mrr"] = rr
    else:
        m["fp"] = 1.0 if n else 0.0
    return m


def confusion(pairs):
    """pairs = [(gold, pred), ...] -> (ma tran dict[gold][pred], accuracy)."""
    mat = {g: {p: 0 for p in ACTIONS} for g in ACTIONS}
    ok = 0
    for g, p in pairs:
        mat[g][p] += 1
        ok += g == p
    return mat, (ok / len(pairs) if pairs else float("nan"))
