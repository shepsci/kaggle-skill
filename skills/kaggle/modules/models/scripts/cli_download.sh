#!/usr/bin/env bash
# Download a Kaggle model variation version using kaggle-cli.
#
# Usage:
#   bash cli_download.sh <model-handle> [output-dir]
#
# Example:
#   bash cli_download.sh google/gemma/transformers/2b ./downloads/gemma-2b

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: cli_download.sh <model-handle> [output-dir]"
    exit 0
fi

MODEL_HANDLE="${1:?Usage: cli_download.sh <model-handle> [output-dir]}"
OUTPUT_DIR="${2:-./downloads/$(echo "$MODEL_HANDLE" | tr '/' '-')}"

echo "============================================================"
echo "kaggle-cli: Download Model"
echo "============================================================"

mkdir -p "${OUTPUT_DIR}"
kaggle models instances versions download "${MODEL_HANDLE}" \
    --path "${OUTPUT_DIR}"

echo "Model downloaded to ${OUTPUT_DIR}"
ls -la "${OUTPUT_DIR}/"
