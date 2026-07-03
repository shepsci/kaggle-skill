#!/usr/bin/env bash
# Publish private models to Kaggle using kaggle-cli.
#
# Usage:
#   bash cli_publish.sh <model-dir> <model-handle>

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: cli_publish.sh <model-dir> <model-handle>"
    exit 0
fi

DIR="${1:?Usage: cli_publish.sh <model-dir> <model-handle>}"
MODEL_HANDLE="${2:?Usage: cli_publish.sh <model-dir> <model-handle>}"

echo "============================================================"
echo "Publish a Private Model"
echo "============================================================"

echo "--- Ensure model-metadata.json exists ---"
if [ ! -f "${DIR}/model-metadata.json" ]; then
    echo "Initializing metadata..."
    kaggle models init -p "${DIR}"
    echo "Edit ${DIR}/model-metadata.json before continuing."
    exit 1
fi

echo "--- Creating model container ---"
kaggle models create -p "${DIR}"
echo "Model container created."

echo "--- Uploading model files ---"
kaggle models instances versions create \
    "${MODEL_HANDLE}" \
    -p "${DIR}" \
    -n "Upload via kaggle-cli"
echo "Model files uploaded."
