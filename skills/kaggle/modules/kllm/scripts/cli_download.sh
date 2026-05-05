#!/usr/bin/env bash
# Download datasets and models from Kaggle using the kaggle-cli.
#
# Usage:
#   bash cli_download.sh                          # runs examples with defaults
#   bash cli_download.sh <dataset> [output-dir]   # download a specific dataset
#
# Examples:
#   bash cli_download.sh kaggle/meta-kaggle ./downloads/meta-kaggle
#   bash cli_download.sh heptapod/titanic ./downloads/titanic
#
# Prerequisites:
#   uv pip install kaggle
#   Credentials configured in ~/.kaggle/kaggle.json or env vars

set -euo pipefail

DATASET="${1:-kaggle/meta-kaggle}"

# Validate the slug — Kaggle slugs are owner/dataset, ASCII-safe characters
# only. Reject anything that could traverse the filesystem when used in
# OUTPUT_DIR or the kaggle-cli `--unzip` step.
if ! printf '%s' "$DATASET" | grep -qE '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$'; then
    echo "[FAIL] dataset slug '$DATASET' is not in the expected owner/name form" >&2
    echo "       allowed chars: A-Z a-z 0-9 . _ - and exactly one '/'" >&2
    exit 2
fi

OUTPUT_DIR="${2:-./downloads/$(echo "$DATASET" | tr '/' '-')}"

echo "============================================================"
echo "kaggle-cli: Download Dataset"
echo "============================================================"

# List files in the dataset
echo "--- Listing dataset files for ${DATASET} ---"
kaggle datasets files "${DATASET}"

# Download the dataset
echo "--- Downloading dataset to ${OUTPUT_DIR} ---"
mkdir -p "${OUTPUT_DIR}"
kaggle datasets download "${DATASET}" \
    --path "${OUTPUT_DIR}" \
    --unzip

echo "Dataset downloaded to ${OUTPUT_DIR}"
ls -la "${OUTPUT_DIR}/"
