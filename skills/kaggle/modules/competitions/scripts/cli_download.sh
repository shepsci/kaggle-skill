#!/usr/bin/env bash
# Download a competition's data files with the kaggle CLI.
#
# Usage:
#   bash cli_download.sh <competition> [download-dir] [--unzip]
#
# You must have accepted the competition rules on kaggle.com first; there is
# no CLI command for that. --unzip extracts the archive with a path check
# (kaggle 2.2.4 has no --unzip for competition downloads).

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_download.sh <competition> [download-dir] [--unzip]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

UNZIP=0
ARGS=()
for arg in "$@"; do
    if [[ "${arg}" == "--unzip" ]]; then
        UNZIP=1
    else
        ARGS+=("${arg}")
    fi
done
if [[ ${#ARGS[@]} -lt 1 ]]; then
    usage >&2
    exit 2
fi

COMPETITION="${ARGS[0]}"
if [[ ! "${COMPETITION}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo "[FAIL] competition slug is not in the expected form" >&2
    exit 2
fi
DOWNLOAD_DIR="${ARGS[1]:-./downloads/${COMPETITION}}"

echo "--- Files in ${COMPETITION} ---"
kaggle_run competitions.files competitions files "${COMPETITION}"

echo "--- Downloading to ${DOWNLOAD_DIR} ---"
mkdir -p "${DOWNLOAD_DIR}"
kaggle_run competitions.download competitions download "${COMPETITION}" \
    --path "${DOWNLOAD_DIR}" --quiet

if [[ "${UNZIP}" -eq 1 ]]; then
    for archive in "${DOWNLOAD_DIR}"/*.zip; do
        [ -e "${archive}" ] || continue
        python3 "${SKILL_ROOT}/shared/safe_extract.py" "${archive}" "${DOWNLOAD_DIR}"
    done
fi

echo "Competition data is in ${DOWNLOAD_DIR}"
wrap_local ls ls -la "${DOWNLOAD_DIR}/"
