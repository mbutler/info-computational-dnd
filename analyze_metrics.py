import argparse
import csv
import statistics
from typing import Dict, List, Optional


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_rows(path: str) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: _to_float(v) for k, v in row.items()})
    return rows


def baseline_stats(rows: List[Dict[str, float]], key: str, count: int) -> Dict[str, float]:
    sample = [r[key] for r in rows[:count] if key in r]
    if not sample:
        return {"mean": 0.0, "median": 0.0}
    return {
        "mean": statistics.fmean(sample),
        "median": statistics.median(sample),
    }


def first_sustained_index(
    rows: List[Dict[str, float]],
    predicate,
    sustain_points: int,
) -> Optional[int]:
    if sustain_points <= 1:
        for i, row in enumerate(rows):
            if predicate(row):
                return i
        return None

    run = 0
    start = None
    for i, row in enumerate(rows):
        if predicate(row):
            run += 1
            if start is None:
                start = i
            if run >= sustain_points:
                return start
        else:
            run = 0
            start = None
    return None


def fmt_interaction(row: Dict[str, float]) -> str:
    return f"{int(row.get('interaction', 0)):,}"


def detect_phase_signals(
    rows: List[Dict[str, float]],
    baseline_points: int,
    sustain_points: int,
    zip_drop_frac: float,
    ops_spike_frac: float,
    coop_lift_abs: float,
    merge_lift_abs: float,
) -> Dict[str, Optional[int]]:
    stats = {
        "zip_size": baseline_stats(rows, "zip_size", baseline_points),
        "ops_per_interaction": baseline_stats(rows, "ops_per_interaction", baseline_points),
        "cooperation_index": baseline_stats(rows, "cooperation_index", baseline_points),
        "merge_rate": baseline_stats(rows, "merge_rate", baseline_points),
    }

    zip_threshold = stats["zip_size"]["median"] * (1.0 - zip_drop_frac)
    ops_threshold = stats["ops_per_interaction"]["median"] * (1.0 + ops_spike_frac)
    coop_threshold = stats["cooperation_index"]["median"] + coop_lift_abs
    merge_threshold = stats["merge_rate"]["median"] + merge_lift_abs

    zip_idx = first_sustained_index(
        rows,
        lambda r: r.get("zip_size", 0.0) <= zip_threshold,
        sustain_points=sustain_points,
    )
    ops_idx = first_sustained_index(
        rows,
        lambda r: r.get("ops_per_interaction", 0.0) >= ops_threshold,
        sustain_points=sustain_points,
    )
    coop_idx = first_sustained_index(
        rows,
        lambda r: r.get("cooperation_index", 0.0) >= coop_threshold,
        sustain_points=sustain_points,
    )
    merge_idx = first_sustained_index(
        rows,
        lambda r: r.get("merge_rate", 0.0) >= merge_threshold,
        sustain_points=sustain_points,
    )

    return {
        "zip_idx": zip_idx,
        "ops_idx": ops_idx,
        "coop_idx": coop_idx,
        "merge_idx": merge_idx,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze E3 metrics CSV for emergence signatures.")
    parser.add_argument("metrics_csv", type=str, help="Path to metrics CSV emitted by main.py")
    parser.add_argument(
        "--baseline-points",
        type=int,
        default=20,
        help="Number of early checkpoints used as baseline (default: 20).",
    )
    parser.add_argument(
        "--sustain-points",
        type=int,
        default=3,
        help="Consecutive checkpoints needed to confirm a signal (default: 3).",
    )
    parser.add_argument(
        "--zip-drop-frac",
        type=float,
        default=0.10,
        help="Fractional drop from baseline median zip_size (default: 0.10).",
    )
    parser.add_argument(
        "--ops-spike-frac",
        type=float,
        default=0.20,
        help="Fractional increase from baseline median ops_per_interaction (default: 0.20).",
    )
    parser.add_argument(
        "--coop-lift-abs",
        type=float,
        default=0.05,
        help="Absolute lift over baseline cooperation_index median (default: 0.05).",
    )
    parser.add_argument(
        "--merge-lift-abs",
        type=float,
        default=0.0005,
        help="Absolute lift over baseline merge_rate median (default: 0.0005).",
    )
    args = parser.parse_args()

    rows = load_rows(args.metrics_csv)
    if not rows:
        raise SystemExit("No rows found in metrics CSV.")

    baseline_points = max(3, min(args.baseline_points, len(rows)))
    signals = detect_phase_signals(
        rows=rows,
        baseline_points=baseline_points,
        sustain_points=max(1, args.sustain_points),
        zip_drop_frac=max(0.0, args.zip_drop_frac),
        ops_spike_frac=max(0.0, args.ops_spike_frac),
        coop_lift_abs=max(0.0, args.coop_lift_abs),
        merge_lift_abs=max(0.0, args.merge_lift_abs),
    )

    print(f"Rows analyzed: {len(rows)}")
    print(f"Baseline points: {baseline_points}")
    print()

    for label, idx_key in [
        ("Zip-drop onset", "zip_idx"),
        ("Ops spike onset", "ops_idx"),
        ("Cooperation lift onset", "coop_idx"),
        ("Merge lift onset", "merge_idx"),
    ]:
        idx = signals[idx_key]
        if idx is None:
            print(f"{label}: not detected")
        else:
            row = rows[idx]
            print(f"{label}: interaction {fmt_interaction(row)} (checkpoint row {idx})")

    print()
    if all(signals[k] is not None for k in ("zip_idx", "ops_idx", "coop_idx", "merge_idx")):
        phase_start_idx = max(signals["zip_idx"], signals["ops_idx"], signals["coop_idx"], signals["merge_idx"])
        phase_row = rows[phase_start_idx]
        print(f"Likely phase-transition window: interaction {fmt_interaction(phase_row)} onward.")
    else:
        print("No combined phase-transition window detected with current thresholds.")
        print("Tip: relax thresholds if emergence appears late (e.g., lower --ops-spike-frac or --merge-lift-abs).")


if __name__ == "__main__":
    main()
