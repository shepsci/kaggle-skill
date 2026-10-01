#!/usr/bin/env bash
# Push a notebook to Kaggle, wait for the run, and download its output.
#
# Usage:
#   bash cli_execute.sh <notebook-dir> <owner/kernel> [output-dir] [max-wait-seconds]
#
# <notebook-dir> holds the notebook and its kernel-metadata.json, whose "id"
# must be the same <owner/kernel>. Defaults: ./downloads/notebook-output and
# 3600 seconds.
#
# Exit status: 0 output downloaded, 1 the push or the run failed,
# 4 the status or the output listing could not be read, 5 refused (credential
# files in the notebook folder, or an output file name that would escape the
# output folder), 124 timed out while running.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_execute.sh <notebook-dir> <owner/kernel> [output-dir] [max-wait-seconds]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 2 ]]; then
    usage >&2
    exit 2
fi

NOTEBOOK_DIR="$1"
KERNEL_SLUG="$2"
OUTPUT_DIR="${3:-./downloads/notebook-output}"
MAX_WAIT="${4:-3600}"

if ! is_slug "${KERNEL_SLUG}"; then
    echo "[FAIL] notebook is not in the expected owner/name form" >&2
    exit 2
fi
if ! is_positive_int "${MAX_WAIT}"; then
    echo "[FAIL] max-wait-seconds must be a positive integer" >&2
    exit 2
fi
if [ ! -f "${NOTEBOOK_DIR}/kernel-metadata.json" ]; then
    echo "[FAIL] ${NOTEBOOK_DIR}/kernel-metadata.json not found" >&2
    echo "       create one with: kaggle kernels init -p ${NOTEBOOK_DIR}" >&2
    exit 2
fi

preflight_upload "${NOTEBOOK_DIR}"

echo "--- Step 1: push (this starts a run on Kaggle) ---"
kaggle_run kernels.push kernels push -p "${NOTEBOOK_DIR}"

echo "--- Step 2: wait for the run ---"
rc=0
kernel_wait "${KERNEL_SLUG}" 30 "${MAX_WAIT}" || rc=$?
case "${rc}" in
    0) ;;
    1)
        echo "The run failed or was cancelled. Log:" >&2
        kaggle_run kernels.logs kernels logs "${KERNEL_SLUG}" >&2 || true
        exit 1
        ;;
    124)
        echo "Still running after ${MAX_WAIT}s. Keep waiting with poll_kernel.sh ${KERNEL_SLUG}." >&2
        exit 124
        ;;
    *) echo "Could not read the run status." >&2; exit 4 ;;
esac

echo "--- Step 3: download output to ${OUTPUT_DIR} ---"
kernel_output "${KERNEL_SLUG}" "${OUTPUT_DIR}"
wrap_local ls ls -la "${OUTPUT_DIR}/"
