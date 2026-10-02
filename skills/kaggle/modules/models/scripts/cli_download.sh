#!/usr/bin/env bash
# Download one version of a Kaggle model variation with the kaggle CLI.
#
# Usage:
#   bash cli_download.sh <owner/model/framework/variation/version> [output-dir]
#
# Example:
#   bash cli_download.sh google/gemma/transformers/2b-it/3 ./downloads/gemma-2b-it
#
# The CLI needs the version number. To see which versions exist:
#   kaggle models variations versions list <owner/model/framework/variation>
# To get the latest version without naming it, use kagglehub_download.py, which
# accepts the four-part handle.
#
# The archive is left as downloaded (.tar.gz). kaggle 2.2.4 extracts tar files
# without a path check, so this script does not pass --untar.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_download.sh <owner/model/framework/variation/version> [output-dir]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 1 ]]; then
    usage >&2
    exit 2
fi

MODEL_HANDLE="$1"
PART='[A-Za-z0-9][A-Za-z0-9._-]*'

if [[ "${MODEL_HANDLE}" =~ ^${PART}/${PART}/${PART}/${PART}$ ]]; then
    echo "[FAIL] the handle has no version number" >&2
    echo "       expected owner/model/framework/variation/version" >&2
    echo "       list versions: kaggle models variations versions list <owner/model/framework/variation>" >&2
    echo "       or use kagglehub_download.py for the latest version" >&2
    exit 2
fi
if [[ ! "${MODEL_HANDLE}" =~ ^${PART}/${PART}/${PART}/${PART}/[0-9]+$ ]]; then
    echo "[FAIL] model handle is not in the expected form" >&2
    echo "       expected owner/model/framework/variation/version" >&2
    exit 2
fi

OUTPUT_DIR="${2:-./downloads/${MODEL_HANDLE//\//-}}"

mkdir -p "${OUTPUT_DIR}"
kaggle_run models.download models variations versions download "${MODEL_HANDLE}" \
    --path "${OUTPUT_DIR}" --quiet

echo "Model archive downloaded to ${OUTPUT_DIR}"
wrap_local ls ls -la "${OUTPUT_DIR}/"
