#!/usr/bin/env bash
# Publish a private Kaggle notebook using kaggle-cli.
#
# Usage:
#   bash cli_publish.sh <notebook-dir>

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: cli_publish.sh <notebook-dir>"
    exit 0
fi

DIR="${1:?Usage: cli_publish.sh <notebook-dir>}"

echo "============================================================"
echo "Publish a Private Notebook"
echo "============================================================"

echo "--- Ensure kernel-metadata.json exists ---"
if [ ! -f "${DIR}/kernel-metadata.json" ]; then
    echo "Initializing metadata..."
    kaggle kernels init -p "${DIR}"
    echo "Edit ${DIR}/kernel-metadata.json before continuing."
    exit 1
fi

echo "--- Pushing notebook ---"
kaggle kernels push -p "${DIR}"

echo "Notebook published (private) and execution triggered on KKB."
