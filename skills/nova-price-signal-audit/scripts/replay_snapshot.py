"""Read-only replay of a saved Guangxi weather price-signal snapshot.

Input is a JSON export containing as_of, weather_heatmap, weather_signal.reference,
threshold.value, marker_probability, calibration_d1, calibration_d3, and signals.
No production database or FactorLibrary file is modified.
"""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path


def replay(snapshot):
    origin = date.fromisoformat(snapshot["as_of"])
    heat = {r["date"]: r["values"] for r in snapshot["weather_heatmap"]}
    reference = snapshot["weather_signal"]["reference"]
    threshold = float(snapshot["threshold"]["value"])
    gate = float(snapshot.get("marker_probability", 0.6))
    if gate > 1:
        gate /= 100
    results = []
    for lead in (1, 3, 4, 5, 6, 7):
        artifact = snapshot["calibration_d1" if lead == 1 else "calibration_d3"]
        if str(artifact["label_cutoff"]) >= origin.isoformat():
            raise ValueError(f"D+{lead}: calibration labels reach forecast origin")
        target = (origin + timedelta(days=lead)).isoformat()
        base = origin.isoformat() if lead == 1 else (origin + timedelta(days=lead - 3)).isoformat()
        if target not in heat or base not in heat:
            results.append({"lead": lead, "target": target, "status": "missing_weather"})
            continue
        terms = {}
        for field, coef in artifact["coefficients"].items():
            std = float(reference[field]["std"])
            if std <= 0:
                raise ValueError(f"D+{lead}: non-positive standard deviation for {field}")
            terms[field] = float(coef) * (
                float(heat[target][field]["value"]) - float(heat[base][field]["value"])
            ) / std
        mu = float(artifact["intercept"]) + sum(terms.values())
        residuals = [float(x) for x in artifact["calibration_residuals"]]
        if not residuals:
            raise ValueError(f"D+{lead}: empty residual distribution")
        up = (sum(mu + e > threshold for e in residuals) + 0.5) / (len(residuals) + 1.5)
        down = (sum(mu + e < -threshold for e in residuals) + 0.5) / (len(residuals) + 1.5)
        marker = "up" if up >= gate and mu >= threshold else "down" if down >= gate and mu <= -threshold else None
        original = next((r for r in snapshot.get("signals", []) if r.get("lead") == lead and r.get("date") == target), None)
        differences = {}
        if original:
            for key, actual in (("formula_delta", mu), ("up_probability", up), ("down_probability", down)):
                if key in original and abs(float(original[key]) - actual) > 1e-8:
                    differences[key] = {"saved": original[key], "replayed": actual}
            if original.get("marker") != marker:
                differences["marker"] = {"saved": original.get("marker"), "replayed": marker}
        results.append({"lead": lead, "target": target, "base": base, "version": artifact["version"],
                        "terms": terms, "formula_delta": mu, "up_probability": up,
                        "down_probability": down, "marker": marker, "saved_signal_found": bool(original),
                        "differences": differences})
    return {"as_of": origin.isoformat(), "threshold_yuan_per_mwh": threshold,
            "probability_gate": gate, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="JSON snapshot with frozen calibration and weather")
    parser.add_argument("--out", type=Path, help="Write JSON report; otherwise print to stdout")
    args = parser.parse_args()
    report = replay(json.loads(args.snapshot.read_text(encoding="utf-8")))
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if any(r.get("differences") for r in report["results"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

