#!/usr/bin/env bash
# Poll a Kaggle kernel for completion and download output.
#
# Usage:
#   bash scripts/poll_kernel.sh <kernel-slug> [output-dir] [poll-interval]
#
# Arguments:
#   kernel-slug    — e.g., "username/kernel-name"
#   output-dir     — directory to save output (default: ./kernel-output)
#   poll-interval  — seconds between status checks (default: 30)
#
# Example:
#   bash scripts/poll_kernel.sh myuser/my-notebook ./output 15

set -euo pipefail

KERNEL_SLUG="${1:?Usage: poll_kernel.sh <kernel-slug> [output-dir] [poll-interval]}"
OUTPUT_DIR="${2:-./kernel-output}"
POLL_INTERVAL="${3:-30}"

echo "Polling kernel: ${KERNEL_SLUG}"
echo "Output dir:     ${OUTPUT_DIR}"
echo "Poll interval:  ${POLL_INTERVAL}s"
echo ""

while true; do
    STATUS=$(kaggle kernels status "${KERNEL_SLUG}" 2>&1)
    TIMESTAMP=$(date '+%H:%M:%S')
    echo "[${TIMESTAMP}] ${STATUS}"

    if echo "${STATUS}" | grep -qi "complete"; then
        echo ""
        echo "Kernel completed successfully!"
        echo "Downloading output..."
        mkdir -p "${OUTPUT_DIR}"
        kaggle kernels output "${KERNEL_SLUG}" --path "${OUTPUT_DIR}"
        echo "Output saved to ${OUTPUT_DIR}/"
        ls -la "${OUTPUT_DIR}/"
        exit 0
    elif echo "${STATUS}" | grep -qi "error\|cancel"; then
        echo ""
        echo "Kernel execution failed or was cancelled."
        exit 1
    fi

    sleep "${POLL_INTERVAL}"
done
