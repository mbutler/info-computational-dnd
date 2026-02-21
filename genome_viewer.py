import argparse
import json
import os
from collections import Counter, defaultdict
from glob import glob
from typing import Dict, List

from analyze_metrics import detect_phase_signals, load_rows


def read_snapshots(snapshot_dir: str) -> List[Dict[str, object]]:
    paths = sorted(glob(os.path.join(snapshot_dir, "*.json")))
    snapshots: List[Dict[str, object]] = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            snapshots.append(json.load(f))
    return snapshots


def read_events(events_path: str) -> List[Dict[str, object]]:
    if not os.path.exists(events_path):
        return []
    events = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def build_story(
    metrics_rows: List[Dict[str, float]],
    snapshots: List[Dict[str, object]],
    events: List[Dict[str, object]],
) -> Dict[str, object]:
    if not metrics_rows:
        return {"highlights": ["No metrics rows available."], "timeline": []}

    baseline_points = max(3, min(20, len(metrics_rows)))
    phase = detect_phase_signals(
        rows=metrics_rows,
        baseline_points=baseline_points,
        sustain_points=3,
        zip_drop_frac=0.10,
        ops_spike_frac=0.20,
        coop_lift_abs=0.05,
        merge_lift_abs=0.0005,
    )

    def at(idx: int, key: str) -> float:
        if idx is None:
            return -1.0
        return metrics_rows[idx].get(key, -1.0)

    timeline: List[str] = []
    for name, idx_key in [
        ("Zip-drop begins", "zip_idx"),
        ("Ops density spike begins", "ops_idx"),
        ("Cooperation wave begins", "coop_idx"),
        ("Merge wave begins", "merge_idx"),
    ]:
        idx = phase[idx_key]
        if idx is not None:
            timeline.append(f"{name} near interaction {int(at(idx, 'interaction')):,}.")

    peak_ops = max(metrics_rows, key=lambda r: r.get("ops_per_interaction", 0.0))
    peak_merge = max(metrics_rows, key=lambda r: r.get("merge_rate", 0.0))
    peak_coop = max(metrics_rows, key=lambda r: r.get("cooperation_index", 0.0))
    peak_signal = max(metrics_rows, key=lambda r: r.get("signal_convention_strength", 0.0))
    min_zip = min(metrics_rows, key=lambda r: r.get("zip_size", float("inf")))

    event_counts = Counter(event.get("event_type", "unknown") for event in events)
    replicator_parents = Counter()
    merge_parents = Counter()
    for event in events:
        if event.get("event_type") == "replicate":
            replicator_parents[int(event.get("parent_id", -1))] += 1
        elif event.get("event_type") == "merge":
            merge_parents[int(event.get("parent_a_id", -1))] += 1
            merge_parents[int(event.get("parent_b_id", -1))] += 1

    motif_first_seen = {}
    motif_peak_count = defaultdict(int)
    role_dominance_shifts = []
    last_top_role = None
    for snap in snapshots:
        interaction = int(snap.get("interaction", 0))
        summary = snap.get("population_summary", {})
        role_counts = summary.get("role_counts", {})
        if role_counts:
            top_role = max(role_counts, key=role_counts.get)
            if last_top_role is not None and top_role != last_top_role:
                role_dominance_shifts.append((interaction, last_top_role, top_role))
            last_top_role = top_role
        motifs = summary.get("top_sampled_motifs", {})
        for motif_name, count in motifs.items():
            if count > 0 and motif_name not in motif_first_seen:
                motif_first_seen[motif_name] = interaction
            motif_peak_count[motif_name] = max(motif_peak_count[motif_name], int(count))

    highlights: List[str] = []
    highlights.append(
        f"Biggest compression (zip-drop floor) reached {int(min_zip.get('zip_size', 0))} at "
        f"interaction {int(min_zip.get('interaction', 0)):,}."
    )
    highlights.append(
        f"Peak computational density reached {peak_ops.get('ops_per_interaction', 0.0):.2f} "
        f"ops/interaction around {int(peak_ops.get('interaction', 0)):,}."
    )
    highlights.append(
        f"Peak cooperation index hit {peak_coop.get('cooperation_index', 0.0):.3f} "
        f"around {int(peak_coop.get('interaction', 0)):,}."
    )
    highlights.append(
        f"Peak merge rate hit {peak_merge.get('merge_rate', 0.0):.5f} "
        f"around {int(peak_merge.get('interaction', 0)):,}."
    )
    if peak_signal.get("signal_convention_strength", 0.0) > 0.2:
        highlights.append(
            "Signal convention emerged: a shared byte became common enough to suggest social coordination."
        )

    if role_dominance_shifts:
        first_shift = role_dominance_shifts[0]
        highlights.append(
            f"Role ecology shift detected near {first_shift[0]:,}: "
            f"{first_shift[1]} -> {first_shift[2]} dominance."
        )

    motif_map = {
        "unkillable_loop_signature": "Potential unkillable-loop genomes",
        "parasitic_signature": "Parasitic replicator candidates",
        "signal_convention_signature": "Signal-language-like genomes",
        "orchestrator_signature": "Leader/orchestrator genomes",
        "fortress_signature": "Defensive fortress genomes",
        "burst_predator_signature": "Burst predator genomes",
        "merge_ready_signature": "Merge-ready symbiogenesis genomes",
    }
    for motif, label in motif_map.items():
        if motif in motif_first_seen:
            highlights.append(
                f"{label} first appeared near interaction {motif_first_seen[motif]:,} "
                f"(peak sampled count {motif_peak_count[motif]})."
            )

    top_replicators = replicator_parents.most_common(5)
    top_mergers = merge_parents.most_common(5)
    if top_replicators:
        highlights.append(
            "Top replicator parents: "
            + ", ".join(f"#{entity_id} ({count})" for entity_id, count in top_replicators)
        )
    if top_mergers:
        highlights.append(
            "Top merge-participating genomes: "
            + ", ".join(f"#{entity_id} ({count})" for entity_id, count in top_mergers)
        )

    latest_snapshot_entities = []
    if snapshots:
        latest = snapshots[-1]
        selected = latest.get("selected_entities", [])
        for entity in selected[:10]:
            motifs = [k for k, v in entity.get("motifs", {}).items() if v]
            latest_snapshot_entities.append(
                {
                    "entity_id": entity.get("entity_id"),
                    "role": entity.get("role"),
                    "score": entity.get("score"),
                    "motifs": motifs,
                    "dna_tokens_preview": entity.get("dna_tokens", [])[:12],
                }
            )

    return {
        "highlights": highlights,
        "timeline": timeline,
        "event_counts": dict(event_counts),
        "latest_entities": latest_snapshot_entities,
    }


def write_markdown(
    output_path: str,
    seed: str,
    metrics_csv: str,
    artifact_dir: str,
    story: Dict[str, object],
) -> None:
    lines = []
    lines.append(f"# E3 Genome Viewer Report (seed {seed})")
    lines.append("")
    lines.append("This report translates simulation data into plain-language emergence observations.")
    lines.append("")
    lines.append("## Run Context")
    lines.append("")
    lines.append(f"- Metrics CSV: `{metrics_csv}`")
    lines.append(f"- Artifact Directory: `{artifact_dir}`")
    lines.append("")
    lines.append("## Cool Things We Saw")
    lines.append("")
    for item in story.get("highlights", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Emergence Timeline")
    lines.append("")
    timeline = story.get("timeline", [])
    if timeline:
        for item in timeline:
            lines.append(f"- {item}")
    else:
        lines.append("- No strong phase timeline detected with current thresholds.")
    lines.append("")
    lines.append("## Event Totals")
    lines.append("")
    event_counts = story.get("event_counts", {})
    if event_counts:
        for event_name, count in sorted(event_counts.items()):
            lines.append(f"- `{event_name}`: {count}")
    else:
        lines.append("- No event log data found.")
    lines.append("")
    lines.append("## Interesting Genomes (Latest Snapshot)")
    lines.append("")
    latest_entities = story.get("latest_entities", [])
    if latest_entities:
        for entity in latest_entities:
            motif_text = ", ".join(entity["motifs"]) if entity["motifs"] else "none"
            dna_preview = " | ".join(entity["dna_tokens_preview"])
            lines.append(
                f"- Entity #{entity['entity_id']} | role={entity['role']} | score={entity['score']} | motifs={motif_text}"
            )
            lines.append(f"  - DNA preview: {dna_preview}")
    else:
        lines.append("- No snapshots found yet; rerun with artifact snapshots enabled.")
    lines.append("")
    lines.append("## What To Try Next")
    lines.append("")
    lines.append("- If you want more weird behavior, lower merge/cooperation thresholds slightly and compare seeds.")
    lines.append("- If dynamics collapse into monoculture, increase random sample size in snapshots to catch minority lineages.")
    lines.append("- If social signaling seems strong, inspect events around signal-convention peaks for stable treaties.")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="User-friendly genome viewer for E3 emergence artifacts.")
    parser.add_argument("--metrics-csv", required=True, help="Metrics CSV emitted by main.py")
    parser.add_argument("--artifact-dir", required=True, help="Artifact directory containing snapshots/events")
    parser.add_argument(
        "--output-md",
        default="",
        help="Optional markdown output path (defaults to <artifact-dir>/genome_report.md)",
    )
    parser.add_argument("--seed", default="unknown", help="Optional seed label for report header")
    args = parser.parse_args()

    metrics_rows = load_rows(args.metrics_csv)
    snapshot_dir = os.path.join(args.artifact_dir, "snapshots")
    events_path = os.path.join(args.artifact_dir, "events.jsonl")
    snapshots = read_snapshots(snapshot_dir) if os.path.isdir(snapshot_dir) else []
    events = read_events(events_path)
    story = build_story(metrics_rows, snapshots, events)

    output_md = args.output_md or os.path.join(args.artifact_dir, "genome_report.md")
    write_markdown(output_md, args.seed, args.metrics_csv, args.artifact_dir, story)

    print(f"Genome report written: {output_md}")
    print("Top highlights:")
    for item in story.get("highlights", [])[:6]:
        print(f"- {item}")


if __name__ == "__main__":
    main()
