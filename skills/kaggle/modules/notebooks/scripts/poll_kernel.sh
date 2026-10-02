#!/usr/bin/env bash
# Wait for a Kaggle notebook run to finish, then download its output.
#
# Usage:
#   bash poll_kernel.sh <owner/kernel> [output-dir] [poll-seconds] [max-wait-seconds]
#
# Defaults: ./kernel-output, 30 seconds between checks, 3600 seconds in total.
#
# Exit status: 0 output downloaded, 1 the run failed or was cancelled,
# 4 the status or the output listing could not be read, 5 output refused
# (a file name would escape the output folder), 124 timed out while running.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: poll_kernel.sh <owner/kernel> [output-dir] [poll-seconds] [max-wait-seconds]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if [[ $# -lt 1 ]]; then
    usage >&2
    exit 2
fi

KERNEL_SLUG="$1"
OUTPUT_DIR="${2:-./kernel-output}"
POLL_INTERVAL="${3:-30}"
MAX_WAIT="${4:-3600}"

if ! is_slug "${KERNEL_SLUG}"; then
    echo "[FAIL] notebook is not in the expected owner/name form" >&2
    exit 2
fi
if ! is_positive_int "${POLL_INTERVAL}" || ! is_positive_int "${MAX_WAIT}"; then
    echo "[FAIL] poll-seconds and max-wait-seconds must be positive integers" >&2
    exit 2
fi

echo "Polling ${KERNEL_SLUG} every ${POLL_INTERVAL}s for up to ${MAX_WAIT}s"

rc=0
kernel_wait "${KERNEL_SLUG}" "${POLL_INTERVAL}" "${MAX_WAIT}" || rc=$?
case "${rc}" in
    0) ;;
    1) echo "The run failed or was cancelled." >&2; exit 1 ;;
    124) echo "Still running after ${MAX_WAIT}s. Run this script again to keep waiting." >&2; exit 124 ;;
    *) echo "Could not read the run status." >&2; exit 4 ;;
esac

echo "Run complete. Downloading output to ${OUTPUT_DIR}"
kernel_output "${KERNEL_SLUG}" "${OUTPUT_DIR}"
wrap_local ls ls -la "${OUTPUT_DIR}/"
