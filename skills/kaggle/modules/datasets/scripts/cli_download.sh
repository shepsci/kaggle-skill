#!/usr/bin/env bash
# Download a Kaggle dataset with the kaggle CLI.
#
# Usage:
#   bash cli_download.sh <owner/dataset> [output-dir]
#
# Example:
#   bash cli_download.sh heptapod/titanic ./downloads/titanic
#
# Public datasets need no credentials. File names and descriptions come from
# the dataset owner, so the listing is printed as untrusted content.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_download.sh <owner/dataset> [output-dir]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 1 ]]; then
    usage >&2
    exit 2
fi

DATASET="$1"

# Kaggle slugs are owner/name in ASCII. Each part must start with a letter or
# digit, which rules out `..`, option-looking values and anything with spaces,
# newlines or shell metacharacters.
if [[ ! "${DATASET}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo "[FAIL] dataset slug is not in the expected owner/name form" >&2
    echo "       allowed: letters, digits, '.', '_' and '-', with exactly one '/'" >&2
    exit 2
fi

OUTPUT_DIR="${2:-./downloads/${DATASET//\//-}}"

echo "--- Files in ${DATASET} ---"
kaggle_run datasets.files datasets files "${DATASET}"

echo "--- Downloading to ${OUTPUT_DIR} ---"
mkdir -p "${OUTPUT_DIR}"
kaggle_run datasets.download datasets download "${DATASET}" \
    --path "${OUTPUT_DIR}" --unzip --quiet

echo "Dataset downloaded to ${OUTPUT_DIR}"
wrap_local ls ls -la "${OUTPUT_DIR}/"
