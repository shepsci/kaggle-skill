#!/usr/bin/env bash
# Save Kaggle credentials from environment variables to ~/.kaggle, so the
# Kaggle CLI and kagglehub find them in every shell.
#
# Run it on purpose, when you want the credential stored on disk. Nothing runs
# it automatically, and it never overwrites a file that already exists.
#
#   KAGGLE_API_TOKEN               -> ~/.kaggle/access_token
#   KAGGLE_USERNAME + KAGGLE_KEY   -> ~/.kaggle/kaggle.json (legacy)
#
# Usage:
#   bash modules/setup/scripts/setup_env.sh
#
# Run it with bash. Do not source it.

if (return 0 2>/dev/null); then
    echo "Run this script with bash; do not source it." >&2
    return 1
fi

set -euo pipefail
umask 077

# The only .env file read is the one named by KAGGLE_ENV_FILE, and only its
# KAGGLE_API_TOKEN, KAGGLE_USERNAME and KAGGLE_KEY lines are used. The file is
# parsed, never executed.
if [ -n "${KAGGLE_ENV_FILE:-}" ] && [ -f "${KAGGLE_ENV_FILE}" ]; then
    while IFS= read -r line || [ -n "${line}" ]; do
        line="${line%$'\r'}" # a file saved with Windows line ends
        line="${line#export }"
        case "${line}" in
            KAGGLE_API_TOKEN=* | KAGGLE_USERNAME=* | KAGGLE_KEY=*) ;;
            *) continue ;;
        esac
        name="${line%%=*}"
        value="${line#*=}"
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        if [ -z "${!name:-}" ]; then
            export "${name}=${value}"
        fi
    done <"${KAGGLE_ENV_FILE}"
fi

KAGGLE_DIR="${HOME}/.kaggle"
ACCESS_TOKEN_FILE="${KAGGLE_DIR}/access_token"
KAGGLE_JSON="${KAGGLE_DIR}/kaggle.json"

API_TOKEN="${KAGGLE_API_TOKEN:-}"
USERNAME="${KAGGLE_USERNAME:-}"
KEY="${KAGGLE_KEY:-}"

if [ -f "${ACCESS_TOKEN_FILE}" ]; then
    echo "[OK] ${ACCESS_TOKEN_FILE} already exists; left unchanged"
elif [ -n "${API_TOKEN}" ] && [ -f "${API_TOKEN}" ]; then
    # The Kaggle CLI also accepts the path of a token file in this variable.
    echo "[OK] KAGGLE_API_TOKEN names a token file; nothing to save"
elif [ -n "${API_TOKEN}" ]; then
    mkdir -p "${KAGGLE_DIR}"
    printf '%s' "${API_TOKEN}" >"${ACCESS_TOKEN_FILE}"
    echo "[OK] Created ${ACCESS_TOKEN_FILE} from KAGGLE_API_TOKEN (mode 600)"
elif [ -f "${KAGGLE_JSON}" ]; then
    echo "[OK] ${KAGGLE_JSON} already exists; left unchanged"
elif [ -n "${USERNAME}" ] && [ -n "${KEY}" ]; then
    case "${USERNAME}${KEY}" in
        *\"* | *\\*)
            echo "[ERROR] KAGGLE_USERNAME or KAGGLE_KEY contains a quote or backslash" >&2
            exit 1
            ;;
    esac
    mkdir -p "${KAGGLE_DIR}"
    printf '{"username":"%s","key":"%s"}\n' "${USERNAME}" "${KEY}" >"${KAGGLE_JSON}"
    echo "[OK] Created ${KAGGLE_JSON} from KAGGLE_USERNAME + KAGGLE_KEY (mode 600)"
elif [ -f "${KAGGLE_DIR}/credentials.json" ]; then
    echo "[OK] OAuth login found (${KAGGLE_DIR}/credentials.json); nothing to save"
else
    echo "[INFO] No Kaggle credentials in the environment."
    echo "       Sign in with: kaggle auth login"
    echo "       or generate a token at https://www.kaggle.com/settings and set KAGGLE_API_TOKEN"
fi

if ! command -v kaggle >/dev/null 2>&1; then
    echo "[INFO] kaggle CLI not found. Install it with:"
    echo "       python3 -m pip install 'kaggle>=2.2.4' 'kagglehub>=1.0.2'"
fi
