"""Screen one point-in-time candidate factor against a frozen chronological baseline.

CSV columns: province,target_date,issued_at,feature_available_at,label_available_at,
factor,label. Optional scenario groups results. Dates/times use ISO-8601 strings in one timezone.
The label is a numeric price change or load quantity, not an executed P&L.
"""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def _pearson(pairs):
    if len(pairs) < 3:
        return None
    xs, ys = zip(*pairs)
    ax, ay = sum(xs) / len(xs), sum(ys) / len(ys)
    xx = sum((x - ax) ** 2 for x in xs)
    yy = sum((y - ay) ** 2 for y in ys)
    return sum((x - ax) * (y - ay) for x, y in pairs) / math.sqrt(xx * yy) if xx and yy else None


def _fit(rows):
    xs = [r["factor"] for r in rows]
    ys = [r["label"] for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    xx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / xx if xx else 0.0
    return my, my - slope * mx, slope


def screen(records, test_start):
    clean, rejected = [], defaultdict(int)
    seen = set()
    provinces = {r["province"].strip() for r in records}
    if len(provinces) != 1:
        raise ValueError("one province per run; do not pool different markets")
    for r in records:
        key = (r["province"], r["target_date"], r["issued_at"])
        if key in seen:
            rejected["duplicate_key"] += 1
            continue
        seen.add(key)
        if r["feature_available_at"] > r["issued_at"]:
            rejected["future_feature"] += 1
            continue
        if r["label_available_at"] <= r["issued_at"]:
            rejected["label_not_future"] += 1
            continue
        try:
            factor, label = float(r["factor"]), float(r["label"])
        except (TypeError, ValueError):
            rejected["non_numeric"] += 1
            continue
        if not math.isfinite(factor) or not math.isfinite(label):
            rejected["non_finite"] += 1
            continue
        clean.append({**r, "factor": factor, "label": label})
    train = [r for r in clean if r["issued_at"][:10] < test_start and r["label_available_at"][:10] < test_start]
    test = [r for r in clean if r["issued_at"][:10] >= test_start]
    rejected["training_label_after_cutoff"] = sum(r["issued_at"][:10] < test_start and r["label_available_at"][:10] >= test_start for r in clean)
    if len(train) < 3 or len(test) < 3:
        raise ValueError("need at least three eligible rows in each chronological split")
    if {r["target_date"] for r in train} & {r["target_date"] for r in test}:
        raise ValueError("same target date crosses train/test boundary; move the cutoff")
    baseline, intercept, slope = _fit(train)
    baseline_mae = sum(abs(r["label"] - baseline) for r in test) / len(test)
    model_mae = sum(abs(r["label"] - intercept - slope * r["factor"]) for r in test) / len(test)
    grouped = defaultdict(list)
    for r in test:
        grouped[r.get("scenario") or "all"].append(r)
    return {"province": next(iter(provinces)), "test_start": test_start,
            "train_rows": len(train), "test_rows": len(test), "rejected": dict(rejected),
            "train_pearson": _pearson([(r["factor"], r["label"]) for r in train]),
            "test_pearson": _pearson([(r["factor"], r["label"]) for r in test]),
            "frozen_intercept": intercept, "frozen_slope": slope,
            "baseline_test_mae": baseline_mae, "factor_test_mae": model_mae,
            "mae_improvement": baseline_mae - model_mae,
            "scenario_test_mae": {name: sum(abs(r["label"] - intercept - slope * r["factor"]) for r in rows) / len(rows)
                                  for name, rows in grouped.items()},
            "warning": "Exploratory screen only; no transaction costs, cross-validation, or causal claim."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv_file", type=Path)
    p.add_argument("--test-start", required=True, help="First issued date in the untouched test period, YYYY-MM-DD")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    with a.csv_file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"province", "target_date", "issued_at", "feature_available_at", "label_available_at", "factor", "label"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit("missing required CSV columns")
    result = screen(rows, a.test_start)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        a.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()

