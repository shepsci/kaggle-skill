#!/usr/bin/env bash
# Publish a private Kaggle notebook with the kaggle CLI.
#
# Usage:
#   bash cli_publish.sh <notebook-dir>
#
# Pushing a notebook also runs it on Kaggle. The folder must contain
# kernel-metadata.json; without it the script writes a template and stops.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_publish.sh <notebook-dir>"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 1 ]]; then
    usage >&2
    exit 2
fi

DIR="$1"

if [ ! -f "${DIR}/kernel-metadata.json" ]; then
    echo "No kernel-metadata.json in ${DIR}; writing a template."
    kaggle_run kernels.init kernels init -p "${DIR}"
    echo "Edit ${DIR}/kernel-metadata.json, then run this script again."
    exit 1
fi

preflight_upload "${DIR}"

echo "--- Pushing notebook ---"
kaggle_run kernels.push kernels push -p "${DIR}"

echo "Notebook pushed. It is private unless its metadata says otherwise, and it is now running on Kaggle."
