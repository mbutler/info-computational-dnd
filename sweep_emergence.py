import argparse
import csv
import os
from typing import Dict, List, Optional

from analyze_metrics import detect_phase_signals, load_rows


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_seed_from_filename(path: str) -> Optional[int]:
    name = os.path.basename(path)
    for token in name.replace("-", "_").split("_"):
        if token.startswith("seed"):
            suffix = token[4:]
            if suffix.isdigit():
                return int(suffix)
    return None


def summarize_seed(
    csv_path: str,
    baseline_points: int,
    sustain_points: int,
    zip_drop_frac: float,
    ops_spike_frac: float,
    coop_lift_abs: float,
    merge_lift_abs: float,
) -> Dict[str, float]:
    rows = load_rows(csv_path)
    if not rows:
        raise ValueError(f"No rows in CSV: {csv_path}")

    b_points = max(3, min(baseline_points, len(rows)))
    signals = detect_phase_signals(
        rows=rows,
        baseline_points=b_points,
        sustain_points=max(1, sustain_points),
        zip_drop_frac=max(0.0, zip_drop_frac),
        ops_spike_frac=max(0.0, ops_spike_frac),
        coop_lift_abs=max(0.0, coop_lift_abs),
        merge_lift_abs=max(0.0, merge_lift_abs),
    )

    def _idx_to_interaction(idx_key: str) -> float:
        idx = signals[idx_key]
        if idx is None:
            return -1.0
        return rows[idx].get("interaction", -1.0)

    phase_indices = [signals[k] for k in ("zip_idx", "ops_idx", "coop_idx", "merge_idx")]
    if all(i is not None for i in phase_indices):
        phase_idx = max(phase_indices)
        phase_interaction = rows[phase_idx].get("interaction", -1.0)
    else:
        phase_interaction = -1.0

    best_role_entropy = max(r.get("role_entropy", 0.0) for r in rows)
    best_cooperation_index = max(r.get("cooperation_index", 0.0) for r in rows)
    best_merge_rate = max(r.get("merge_rate", 0.0) for r in rows)
    min_zip_size = min(r.get("zip_size", 0.0) for r in rows)
    max_ops_density = max(r.get("ops_per_interaction", 0.0) for r in rows)
    max_genotype_diversity = max(r.get("genotype_diversity", 0.0) for r in rows)

    top_role = "unknown"
    best_signal_strength = -1.0
    for r in rows:
        signal = r.get("signal_convention_strength", 0.0)
        if signal > best_signal_strength:
            best_signal_strength = signal
            role_scores = {
                "striker": r.get("striker_frac", 0.0),
                "defender": r.get("defender_frac", 0.0),
                "leader": r.get("leader_frac", 0.0),
                "hybrid": r.get("hybrid_frac", 0.0),
            }
            top_role = max(role_scores, key=role_scores.get)

    return {
        "seed": float(_parse_seed_from_filename(csv_path) or -1),
        "rows": float(len(rows)),
        "phase_interaction": phase_interaction,
        "zip_onset_interaction": _idx_to_interaction("zip_idx"),
        "ops_onset_interaction": _idx_to_interaction("ops_idx"),
        "coop_onset_interaction": _idx_to_interaction("coop_idx"),
        "merge_onset_interaction": _idx_to_interaction("merge_idx"),
        "best_role_entropy": best_role_entropy,
        "best_cooperation_index": best_cooperation_index,
        "best_merge_rate": best_merge_rate,
        "min_zip_size": min_zip_size,
        "max_ops_density": max_ops_density,
        "max_genotype_diversity": max_genotype_diversity,
        "peak_signal_convention_strength": max(0.0, best_signal_strength),
        "top_role_at_peak_signal": top_role,
        "source_csv": csv_path,
    }


def _format_interaction(value: float) -> str:
    if value < 0:
        return "n/a"
    return f"{int(value):,}"


def print_leaderboard(rows: List[Dict[str, float]]) -> None:
    if not rows:
        print("No runs to display.")
        return

    print(
        "seed | phase_start | max_coop | max_merge | max_role_entropy | "
        "max_ops_density | max_genotype_diversity | top_role@peak_signal"
    )
    print("-" * 118)
    for row in rows:
        seed = int(row["seed"]) if row["seed"] >= 0 else "unknown"
        print(
            f"{seed} | "
            f"{_format_interaction(row['phase_interaction'])} | "
            f"{row['best_cooperation_index']:.4f} | "
            f"{row['best_merge_rate']:.5f} | "
            f"{row['best_role_entropy']:.4f} | "
            f"{row['max_ops_density']:.4f} | "
            f"{row['max_genotype_diversity']:.4f} | "
            f"{row['top_role_at_peak_signal']}"
        )


def maybe_write_csv(output_csv: str, rows: List[Dict[str, float]]) -> None:
    if not output_csv:
        return
    fieldnames = [
        "seed",
        "rows",
        "phase_interaction",
        "zip_onset_interaction",
        "ops_onset_interaction",
        "coop_onset_interaction",
        "merge_onset_interaction",
        "best_role_entropy",
        "best_cooperation_index",
        "best_merge_rate",
        "min_zip_size",
        "max_ops_density",
        "max_genotype_diversity",
        "peak_signal_convention_strength",
        "top_role_at_peak_signal",
        "source_csv",
    ]
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate multiple E3 runs into an emergence leaderboard.")
    parser.add_argument(
        "metrics_csvs",
        nargs="+",
        help="One or more metrics CSV files emitted by main.py",
    )
    parser.add_argument("--output-csv", type=str, default="", help="Optional output CSV for aggregated results.")
    parser.add_argument(
        "--sort-by",
        type=str,
        default="phase_interaction",
        choices=[
            "phase_interaction",
            "best_cooperation_index",
            "best_merge_rate",
            "best_role_entropy",
            "max_ops_density",
            "max_genotype_diversity",
        ],
        help="Leaderboard sort key.",
    )
    parser.add_argument(
        "--descending",
        action="store_true",
        help="Sort in descending order. Default sorts phase_interaction ascending and others descending.",
    )
    parser.add_argument("--baseline-points", type=int, default=20)
    parser.add_argument("--sustain-points", type=int, default=3)
    parser.add_argument("--zip-drop-frac", type=float, default=0.10)
    parser.add_argument("--ops-spike-frac", type=float, default=0.20)
    parser.add_argument("--coop-lift-abs", type=float, default=0.05)
    parser.add_argument("--merge-lift-abs", type=float, default=0.0005)
    args = parser.parse_args()

    summaries: List[Dict[str, float]] = []
    for path in args.metrics_csvs:
        try:
            summary = summarize_seed(
                csv_path=path,
                baseline_points=args.baseline_points,
                sustain_points=args.sustain_points,
                zip_drop_frac=args.zip_drop_frac,
                ops_spike_frac=args.ops_spike_frac,
                coop_lift_abs=args.coop_lift_abs,
                merge_lift_abs=args.merge_lift_abs,
            )
            summaries.append(summary)
        except Exception as exc:
            print(f"Skipping {path}: {exc}")

    if not summaries:
        raise SystemExit("No valid runs to analyze.")

    if args.sort_by == "phase_interaction":
        default_desc = False
        # Non-detections (-1) should sort to the end.
        summaries.sort(
            key=lambda r: (r["phase_interaction"] < 0, r["phase_interaction"]),
            reverse=args.descending if args.descending else default_desc,
        )
    else:
        default_desc = True
        reverse = args.descending if args.descending else default_desc
        summaries.sort(key=lambda r: r[args.sort_by], reverse=reverse)

    print_leaderboard(summaries)
    maybe_write_csv(args.output_csv, summaries)


if __name__ == "__main__":
    main()
