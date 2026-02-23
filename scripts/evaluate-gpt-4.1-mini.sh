#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   chmod +x scripts/evaluate.sh
#   ./scripts/evaluate.sh
#
# Optional overrides:
#   DATASET_PATH=... OUTPUT_FILE=... BASE_MODEL=... AGENT_TYPE=... NUM_WORKER=... ./scripts/evaluate.sh

MODEL_NAME="gpt-4.1-mini"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DATASET_PATH="hung20gg/financial-forecast"
OUTPUT_FILE="${OUTPUT_FILE:-${PROJECT_ROOT}/data/eval_results_${MODEL_NAME}.jsonl}"
BASE_MODEL=${MODEL_NAME}
AGENT_TYPE="${AGENT_TYPE:-react}"
NUM_WORKER="${NUM_WORKER:-2}"

mkdir -p "$(dirname "${OUTPUT_FILE}")"

python "${PROJECT_ROOT}/scripts/run/run_evaluation.py" \
  --dataset_path "${DATASET_PATH}" \
  --output_file "${OUTPUT_FILE}" \
  --agent_type "${AGENT_TYPE}" \
  --base_model "${BASE_MODEL}" \
  --num_worker "${NUM_WORKER}"
