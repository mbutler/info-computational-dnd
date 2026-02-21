#!/usr/bin/env bash
set -euo pipefail

INTERACTIONS=10000000
CHECKPOINT_EVERY=100000
HEARTBEAT_SECONDS=15
SOUP_SIZE=1024
SEEDS_CSV="42,1337,2026"
OUT_DIR=""

BASELINE_POINTS=20
SUSTAIN_POINTS=3
ZIP_DROP_FRAC=0.10
OPS_SPIKE_FRAC=0.20
COOP_LIFT_ABS=0.05
MERGE_LIFT_ABS=0.0005
SORT_BY="phase_interaction"
DESCENDING=0

usage() {
  cat <<'EOF'
Usage:
  ./run_e3_batch.sh [options]

Runs end-to-end E3 experiments:
  1) main.py for each seed (writes run_seed<seed>.csv)
  2) analyze_metrics.py for each run (writes analysis_seed<seed>.txt)
  3) genome_viewer.py for each run (writes seed<seed>/genome_report_seed<seed>.md)
  4) sweep_emergence.py across all runs (writes leaderboard.txt + leaderboard.csv)

Options:
  --seeds <csv>                 Comma-separated seeds (default: 42,1337,2026)
  --interactions <n>            Interactions per seed (default: 10000000)
  --checkpoint-every <n>        Checkpoint cadence (default: 100000)
  --heartbeat-seconds <n>       Status heartbeat cadence (default: 15, 0 disables)
  --soup-size <n>               Population size (default: 1024)
  --out-dir <path>              Output directory (default: ./runs/<timestamp>)
  --baseline-points <n>         Analyzer baseline checkpoints (default: 20)
  --sustain-points <n>          Analyzer sustained checkpoints (default: 3)
  --zip-drop-frac <f>           Analyzer zip-drop threshold (default: 0.10)
  --ops-spike-frac <f>          Analyzer ops-spike threshold (default: 0.20)
  --coop-lift-abs <f>           Analyzer cooperation lift (default: 0.05)
  --merge-lift-abs <f>          Analyzer merge lift (default: 0.0005)
  --sort-by <key>               Leaderboard sort key (default: phase_interaction)
                                Keys: phase_interaction, best_cooperation_index,
                                      best_merge_rate, best_role_entropy,
                                      max_ops_density, max_genotype_diversity
  --descending                  Sort leaderboard descending
  --help                        Show this help

Examples:
  ./run_e3_batch.sh
  ./run_e3_batch.sh --seeds 1,2,3,4 --interactions 2000000
  ./run_e3_batch.sh --out-dir runs/test1 --sort-by best_cooperation_index --descending
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seeds) SEEDS_CSV="$2"; shift 2 ;;
    --interactions) INTERACTIONS="$2"; shift 2 ;;
    --checkpoint-every) CHECKPOINT_EVERY="$2"; shift 2 ;;
    --heartbeat-seconds) HEARTBEAT_SECONDS="$2"; shift 2 ;;
    --soup-size) SOUP_SIZE="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --baseline-points) BASELINE_POINTS="$2"; shift 2 ;;
    --sustain-points) SUSTAIN_POINTS="$2"; shift 2 ;;
    --zip-drop-frac) ZIP_DROP_FRAC="$2"; shift 2 ;;
    --ops-spike-frac) OPS_SPIKE_FRAC="$2"; shift 2 ;;
    --coop-lift-abs) COOP_LIFT_ABS="$2"; shift 2 ;;
    --merge-lift-abs) MERGE_LIFT_ABS="$2"; shift 2 ;;
    --sort-by) SORT_BY="$2"; shift 2 ;;
    --descending) DESCENDING=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1"
      echo
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_PY="$SCRIPT_DIR/main.py"
ANALYZE_PY="$SCRIPT_DIR/analyze_metrics.py"
SWEEP_PY="$SCRIPT_DIR/sweep_emergence.py"
GENOME_VIEWER_PY="$SCRIPT_DIR/genome_viewer.py"

if [[ ! -f "$MAIN_PY" || ! -f "$ANALYZE_PY" || ! -f "$SWEEP_PY" || ! -f "$GENOME_VIEWER_PY" ]]; then
  echo "Required scripts not found in $SCRIPT_DIR"
  echo "Expected: main.py, analyze_metrics.py, sweep_emergence.py, genome_viewer.py"
  exit 1
fi

if [[ -z "$OUT_DIR" ]]; then
  OUT_DIR="$SCRIPT_DIR/runs/$(date +"%Y%m%d-%H%M%S")"
fi
mkdir -p "$OUT_DIR"

IFS=',' read -r -a SEEDS <<< "$SEEDS_CSV"
if [[ ${#SEEDS[@]} -eq 0 ]]; then
  echo "No seeds provided."
  exit 1
fi

echo "Output directory: $OUT_DIR"
echo "Seeds: $SEEDS_CSV"
echo "Interactions per seed: $INTERACTIONS"
echo "Checkpoint every: $CHECKPOINT_EVERY"
echo "Heartbeat every: $HEARTBEAT_SECONDS"
echo

METRIC_CSVS=()

for raw_seed in "${SEEDS[@]}"; do
  seed="$(echo "$raw_seed" | tr -d '[:space:]')"
  if [[ -z "$seed" ]]; then
    continue
  fi

  METRICS_CSV="$OUT_DIR/run_seed${seed}.csv"
  RUN_LOG="$OUT_DIR/run_seed${seed}.log"
  ANALYSIS_TXT="$OUT_DIR/analysis_seed${seed}.txt"
  SEED_ARTIFACT_DIR="$OUT_DIR/seed${seed}"
  GENOME_REPORT_MD="$SEED_ARTIFACT_DIR/genome_report_seed${seed}.md"
  mkdir -p "$SEED_ARTIFACT_DIR"

  echo "=== Running seed $seed ==="
  python3 -u "$MAIN_PY" \
    --seed "$seed" \
    --interactions "$INTERACTIONS" \
    --checkpoint-every "$CHECKPOINT_EVERY" \
    --heartbeat-seconds "$HEARTBEAT_SECONDS" \
    --soup-size "$SOUP_SIZE" \
    --snapshot-every "$CHECKPOINT_EVERY" \
    --artifact-dir "$SEED_ARTIFACT_DIR" \
    --metrics-csv "$METRICS_CSV" | tee "$RUN_LOG"

  echo "=== Analyzing seed $seed ==="
  python3 -u "$ANALYZE_PY" "$METRICS_CSV" \
    --baseline-points "$BASELINE_POINTS" \
    --sustain-points "$SUSTAIN_POINTS" \
    --zip-drop-frac "$ZIP_DROP_FRAC" \
    --ops-spike-frac "$OPS_SPIKE_FRAC" \
    --coop-lift-abs "$COOP_LIFT_ABS" \
    --merge-lift-abs "$MERGE_LIFT_ABS" | tee "$ANALYSIS_TXT"

  echo "=== Building genome viewer report for seed $seed ==="
  python3 -u "$GENOME_VIEWER_PY" \
    --metrics-csv "$METRICS_CSV" \
    --artifact-dir "$SEED_ARTIFACT_DIR" \
    --seed "$seed" \
    --output-md "$GENOME_REPORT_MD"

  METRIC_CSVS+=("$METRICS_CSV")
  echo
done

if [[ ${#METRIC_CSVS[@]} -eq 0 ]]; then
  echo "No valid seed runs were executed."
  exit 1
fi

LEADERBOARD_TXT="$OUT_DIR/leaderboard.txt"
LEADERBOARD_CSV="$OUT_DIR/leaderboard.csv"

echo "=== Building leaderboard ==="
SWEEP_CMD=(
  python3 -u "$SWEEP_PY"
  "${METRIC_CSVS[@]}"
  --output-csv "$LEADERBOARD_CSV"
  --sort-by "$SORT_BY"
  --baseline-points "$BASELINE_POINTS"
  --sustain-points "$SUSTAIN_POINTS"
  --zip-drop-frac "$ZIP_DROP_FRAC"
  --ops-spike-frac "$OPS_SPIKE_FRAC"
  --coop-lift-abs "$COOP_LIFT_ABS"
  --merge-lift-abs "$MERGE_LIFT_ABS"
)
if [[ "$DESCENDING" -eq 1 ]]; then
  SWEEP_CMD+=(--descending)
fi
"${SWEEP_CMD[@]}" | tee "$LEADERBOARD_TXT"

echo
echo "Complete."
echo "Artifacts:"
echo "  Runs and analyses: $OUT_DIR"
echo "  Leaderboard text:  $LEADERBOARD_TXT"
echo "  Leaderboard CSV:   $LEADERBOARD_CSV"
echo "  Genome reports:    $OUT_DIR/seed*/genome_report_seed*.md"
