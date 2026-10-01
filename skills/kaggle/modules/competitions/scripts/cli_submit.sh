#!/usr/bin/env bash
# Submit a predictions file to a competition with the kaggle CLI.
#
# Usage:
#   bash cli_submit.sh <competition> <submission-file> [message]         # dry run
#   bash cli_submit.sh <competition> <submission-file> [message] --yes   # submit
#
# Without --yes nothing is submitted: the script prints how many submissions
# are left today and what it would send. A submission uses one of the day's
# slots, and on some competitions a submission that errors still uses it.

set -euo pipefail

# shellcheck source-path=SCRIPTDIR source=../../../shared/lib.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"

usage() {
    echo "Usage: cli_submit.sh <competition> <submission-file> [message] [--yes]"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

CONFIRMED=0
ARGS=()
for arg in "$@"; do
    if [[ "${arg}" == "--yes" ]]; then
        CONFIRMED=1
    else
        ARGS+=("${arg}")
    fi
done
if [[ ${#ARGS[@]} -lt 2 ]]; then
    usage >&2
    exit 2
fi

COMPETITION="${ARGS[0]}"
SUBMISSION_FILE="${ARGS[1]}"
MESSAGE="${ARGS[2]:-Submitted with kaggle-skill}"

if [[ ! "${COMPETITION}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo "[FAIL] competition slug is not in the expected form" >&2
    exit 2
fi
if [ ! -f "${SUBMISSION_FILE}" ]; then
    echo "[FAIL] submission file not found: ${SUBMISSION_FILE}" >&2
    exit 2
fi

echo "--- Submission limits for ${COMPETITION} ---"
kaggle_run competitions.submission-limits competitions submission-limits "${COMPETITION}" || true

if [[ "${CONFIRMED}" -ne 1 ]]; then
    echo ""
    echo "Dry run. Nothing was submitted."
    echo "  competition: ${COMPETITION}"
    echo "  file:        ${SUBMISSION_FILE}"
    echo "  message:     ${MESSAGE}"
    echo "Add --yes to submit."
    exit 0
fi

echo "--- Submitting ---"
# --message=VALUE keeps a message that starts with "-" from being read as an option.
kaggle_run competitions.submit competitions submit "${COMPETITION}" \
    --file "${SUBMISSION_FILE}" "--message=${MESSAGE}"

echo "--- Recent submissions ---"
kaggle_run competitions.submissions competitions submissions "${COMPETITION}" || true
