#!/usr/bin/env bash
# Register for a competition and make a submission using kaggle-cli.
#
# kaggle-cli supports:
#   kaggle competitions list       — list active competitions
#   kaggle competitions files      — list files in a competition
#   kaggle competitions download   — download competition data
#   kaggle competitions submit     — submit predictions
#   kaggle competitions submissions — list your submissions
#   kaggle competitions leaderboard — view the leaderboard
#
# NOTE: There is no dedicated CLI command to "join" or "register for" a competition.
#       You must accept the competition rules via the Kaggle website first.
#       After that, all submission operations work via CLI.
#
# Prerequisites:
#   pip install kaggle
#   Credentials configured in ~/.kaggle/kaggle.json
#
# Usage:
#   bash scripts/cli_competition.sh <competition> <submission-file> [download-dir]
#
# Arguments:
#   competition      — competition slug, e.g., "titanic"
#   submission-file  — path to CSV submission file
#   download-dir     — directory to save competition data (default: ./downloads/competition-data)

set -euo pipefail

COMPETITION="${1:?Usage: cli_competition.sh <competition> <submission-file> [download-dir]}"
SUBMISSION_FILE="${2:?Usage: cli_competition.sh <competition> <submission-file> [download-dir]}"
DOWNLOAD_DIR="${3:-./downloads/competition-data}"

echo "============================================================"
echo "Step 1: List available competitions"
echo "============================================================"

kaggle competitions list --sort-by latestDeadline

echo ""
echo "============================================================"
echo "Step 2: Accept competition rules (MUST be done via UI)"
echo "============================================================"
echo ""
echo "IMPORTANT: Before your first submission, you must accept the"
echo "competition rules at:"
echo "  https://www.kaggle.com/c/${COMPETITION}/rules"
echo ""
echo "Click 'I Understand and Accept' on that page."
echo "This is a one-time step per competition."
echo ""

echo "============================================================"
echo "Step 3: Download competition data"
echo "============================================================"

# List competition files
echo "--- Competition files ---"
kaggle competitions files "${COMPETITION}"

# Download all competition data
echo "--- Downloading competition data ---"
mkdir -p "${DOWNLOAD_DIR}"
kaggle competitions download "${COMPETITION}" \
    --path "${DOWNLOAD_DIR}"

echo "Competition data downloaded to ${DOWNLOAD_DIR}/"
ls -la "${DOWNLOAD_DIR}/"

echo ""
echo "============================================================"
echo "Step 4: Make a submission"
echo "============================================================"

# Submit predictions
kaggle competitions submit \
    -c "${COMPETITION}" \
    -f "${SUBMISSION_FILE}" \
    -m "Kaggle workflow CLI submission"

echo "Submission uploaded successfully!"

echo ""
echo "============================================================"
echo "Step 5: Check submission status"
echo "============================================================"

# List your submissions
kaggle competitions submissions "${COMPETITION}"

echo ""
echo "============================================================"
echo "Step 6: View the leaderboard"
echo "============================================================"

# View the leaderboard (top entries)
kaggle competitions leaderboard "${COMPETITION}" --show
