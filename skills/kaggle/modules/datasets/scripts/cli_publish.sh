#!/usr/bin/env bash
# Publish a private dataset with the kaggle CLI.
#
# Usage:
#   bash cli_publish.sh <data-dir>              # create a new dataset
#   bash cli_publish.sh <data-dir> "<notes>"    # add a version to an existing one
#
# The folder must contain dataset-metadata.json. If it does not, the script
# writes a template and stops so you can fill it in.
#
# For notebooks use modules/notebooks/scripts/cli_publish.sh, and for models
# modules/models/scripts/cli_publish.sh.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_publish.sh <data-dir> [version-notes]"
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
NOTES="${2:-}"

if [ ! -f "${DIR}/dataset-metadata.json" ]; then
    echo "No dataset-metadata.json in ${DIR}; writing a template."
    kaggle_run datasets.init datasets init -p "${DIR}"
    echo "Edit ${DIR}/dataset-metadata.json, then run this script again."
    exit 1
fi

preflight_upload "${DIR}"

if [ -n "${NOTES}" ]; then
    echo "--- Creating a new dataset version ---"
    # --message=VALUE keeps notes that start with "-" from being read as an option.
    kaggle_run datasets.version datasets version -p "${DIR}" "--message=${NOTES}" --dir-mode zip
    echo "Dataset version submitted."
else
    echo "--- Creating dataset ---"
    kaggle_run datasets.create datasets create -p "${DIR}" --dir-mode zip
    echo "Dataset created. It is private by default."
fi
