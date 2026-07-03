#!/usr/bin/env bash
# Publish private datasets to Kaggle using kaggle-cli.
#
# kaggle-cli supports:
#   kaggle datasets create   — create a new private dataset
#   kaggle datasets version  — create a new version of an existing dataset
#   kaggle datasets init     — generate dataset-metadata.json template
# For notebooks, use modules/notebooks/scripts/cli_publish.sh.
# For models, use modules/models/scripts/cli_publish.sh.
#
# Prerequisites:
#   pip install kaggle
#   Credentials configured in ~/.kaggle/kaggle.json
#
# Usage:
#   bash scripts/cli_publish.sh <data-dir>

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: cli_publish.sh <data-dir>"
    exit 0
fi

DIR="${1:?Usage: cli_publish.sh <data-dir>}"

echo "============================================================"
echo "Publish a Private Dataset"
echo "============================================================"

echo "--- Ensure dataset-metadata.json exists ---"
if [ ! -f "${DIR}/dataset-metadata.json" ]; then
    echo "Initializing metadata..."
    kaggle datasets init -p "${DIR}"
    echo "Edit ${DIR}/dataset-metadata.json before continuing."
    exit 1
fi

echo "--- Creating dataset ---"
kaggle datasets create \
    -p "${DIR}" \
    --dir-mode zip

echo "Dataset created! It is private by default."
