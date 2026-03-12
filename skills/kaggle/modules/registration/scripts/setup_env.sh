#!/usr/bin/env bash
# Set up Kaggle credentials from available environment variables.
#
# Credential priority:
#   1. ~/.kaggle/access_token (new style, preferred)
#   2. KAGGLE_API_TOKEN env var (new style)
#   3. KAGGLE_KEY / KAGGLE_TOKEN env vars (legacy)
#   4. ~/.kaggle/kaggle.json (legacy)
#
# Creates ~/.kaggle/access_token (preferred) and/or ~/.kaggle/kaggle.json
# so both kagglehub and kaggle-cli work.
#
# Usage:
#   bash scripts/setup_env.sh
#   OR: source scripts/setup_env.sh  (also exports env vars in current shell)

set -euo pipefail

# Load .env if present
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

KAGGLE_DIR="${HOME}/.kaggle"
ACCESS_TOKEN_FILE="${KAGGLE_DIR}/access_token"
KAGGLE_JSON="${KAGGLE_DIR}/kaggle.json"

# Check if access_token file already exists
if [ -f "$ACCESS_TOKEN_FILE" ]; then
    echo "[OK] access_token already exists at ${ACCESS_TOKEN_FILE}"
    exit 0
fi

# Resolve API token
API_TOKEN="${KAGGLE_API_TOKEN:-}"

# Resolve username
USERNAME="${KAGGLE_USERNAME:-}"

# Resolve legacy key
KEY="${KAGGLE_KEY:-${KAGGLE_TOKEN:-}}"

# Create access_token file if we have an API token
if [ -n "$API_TOKEN" ]; then
    mkdir -p "$KAGGLE_DIR"
    echo -n "$API_TOKEN" > "$ACCESS_TOKEN_FILE"
    chmod 600 "$ACCESS_TOKEN_FILE"
    echo "[OK] Created ${ACCESS_TOKEN_FILE} from KAGGLE_API_TOKEN"

# Fall back to legacy key
elif [ -n "$KEY" ]; then
    export KAGGLE_KEY="$KEY"
    if [ -n "$USERNAME" ]; then
        export KAGGLE_USERNAME="$USERNAME"
    fi

    # Create kaggle.json for legacy CLI compatibility
    if [ ! -f "$KAGGLE_JSON" ]; then
        mkdir -p "$KAGGLE_DIR"
        if [ -n "$USERNAME" ]; then
            echo "{\"username\":\"${USERNAME}\",\"key\":\"${KEY}\"}" > "$KAGGLE_JSON"
        else
            echo "{\"key\":\"${KEY}\"}" > "$KAGGLE_JSON"
        fi
        chmod 600 "$KAGGLE_JSON"
        echo "[OK] Created ${KAGGLE_JSON}"
    else
        echo "[OK] ${KAGGLE_JSON} already exists"
    fi

else
    if [ -f "$KAGGLE_JSON" ]; then
        echo "[OK] kaggle.json already exists at ${KAGGLE_JSON}"
    else
        # Silent exit — not an error during SessionStart
        exit 0
    fi
fi

echo "[OK] Kaggle environment ready"
