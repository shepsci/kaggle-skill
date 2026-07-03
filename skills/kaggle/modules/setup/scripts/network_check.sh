#!/usr/bin/env bash
# Quick network diagnostic for Kaggle API reachability.
#
# Checks both api.kaggle.com (CLI/kagglehub) and www.kaggle.com (MCP).
# Uses curl for portability (works on macOS which lacks `timeout`).
#
# Usage:
#   bash modules/setup/scripts/network_check.sh
#
# Exits:
#   0 if both hosts are reachable
#   1 if either is unreachable

set -euo pipefail

HOSTS=("api.kaggle.com" "www.kaggle.com")
TIMEOUT=10
failures=0

for host in "${HOSTS[@]}"; do
    echo "[INFO] Checking HTTPS reachability: ${host}:443"

    # DNS check first
    if ! python3 -c "import socket; socket.getaddrinfo('${host}', 443)" >/dev/null 2>&1; then
        echo "[ERROR] DNS resolution failed for ${host}"
        failures=$((failures + 1))
        continue
    fi

    # HTTPS connectivity
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -m "${TIMEOUT}" "https://${host}" 2>&1) || http_code="000"
    if [[ "$http_code" != "000" ]]; then
        echo "[OK] HTTPS connection to ${host} succeeded (HTTP ${http_code})"
    else
        echo "[ERROR] Cannot reach ${host}:443 (HTTP 000 — connection timeout/refused)"
        failures=$((failures + 1))
    fi
done

echo ""
if [[ $failures -eq 0 ]]; then
    echo "[OK] All Kaggle endpoints reachable"
    exit 0
fi

echo "[ERROR] ${failures} host(s) unreachable"
echo ""
echo "Troubleshooting:"
echo "  - If behind a proxy/firewall, allow outbound HTTPS to api.kaggle.com and www.kaggle.com"
echo "  - Try: export NO_PROXY=api.kaggle.com,www.kaggle.com"
echo "  - Try: export no_proxy=api.kaggle.com,www.kaggle.com"
echo "  - Check: curl -v https://api.kaggle.com 2>&1 | head -20"
exit 1
