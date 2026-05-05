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

# Load .env only from the directory containing this script (the plugin/skill
# root), never from the current working directory. Sourcing $CWD/.env from a
# SessionStart hook would let any directory the user opens Claude Code in
# inject arbitrary env vars into the session.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
if [ -f "${PLUGIN_ROOT}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${PLUGIN_ROOT}/.env"
    set +a
fi

KAGGLE_DIR="${HOME}/.kaggle"
ACCESS_TOKEN_FILE="${KAGGLE_DIR}/access_token"
KAGGLE_JSON="${KAGGLE_DIR}/kaggle.json"

# Check if access_token file already exists
if [ -f "$ACCESS_TOKEN_FILE" ]; then
    echo "[OK] access_token already exists at ${ACCESS_TOKEN_FILE}"
    # Surface install instructions but never auto-install on SessionStart —
    # silently mutating the user's Python environment without consent is a
    # security smell. The user explicitly runs the install command if they
    # want it.
    if ! python3 -c "import kagglehub" 2>/dev/null; then
        echo "[INFO] kagglehub not installed. Run:  pip install --user kagglehub kaggle"
    fi
    echo "[OK] Kaggle environment ready"
    exit 0
fi

# Resolve API token: prefer KAGGLE_API_TOKEN
API_TOKEN="${KAGGLE_API_TOKEN:-}"

# Resolve username
USERNAME="${KAGGLE_USERNAME:-}"

# Resolve legacy key: prefer KAGGLE_KEY, then KAGGLE_TOKEN
KEY="${KAGGLE_KEY:-${KAGGLE_TOKEN:-}}"

# Create access_token file if we have an API token
if [ -n "$API_TOKEN" ]; then
    mkdir -p "$KAGGLE_DIR"
    echo -n "$API_TOKEN" > "$ACCESS_TOKEN_FILE"
    chmod 600 "$ACCESS_TOKEN_FILE"
    echo "[OK] Created ${ACCESS_TOKEN_FILE} from KAGGLE_API_TOKEN"

    # Export for current shell session
    export KAGGLE_API_TOKEN="$API_TOKEN"
    if [ -n "$KEY" ]; then
        export KAGGLE_KEY="$KEY"
    fi

# Fall back to legacy key
elif [ -n "$KEY" ]; then
    # Export the correct env var names (only effective if script is sourced)
    export KAGGLE_KEY="$KEY"
    export KAGGLE_API_TOKEN="$KEY"
    if [ -n "$USERNAME" ]; then
        export KAGGLE_USERNAME="$USERNAME"
    fi

    # Create kaggle.json for legacy CLI compatibility
    if [ ! -f "$KAGGLE_JSON" ]; then
        mkdir -p "$KAGGLE_DIR"
        if [ -n "$USERNAME" ]; then
            printf '{"username":"%s","key":"%s"}\n' "$USERNAME" "$KEY" > "$KAGGLE_JSON"
        else
            printf '{"key":"%s"}\n' "$KEY" > "$KAGGLE_JSON"
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
        echo "[INFO] No Kaggle credentials found in environment."
        echo "       Generate a token at: https://www.kaggle.com/settings"
        echo "       → API Tokens (Recommended) → Generate New Token"
    fi
fi

# Surface install instructions but never auto-install on SessionStart.
if ! python3 -c "import kagglehub" 2>/dev/null; then
    echo "[INFO] kagglehub not installed. Run:  pip install --user kagglehub kaggle"
fi

echo "[OK] Kaggle environment ready"
