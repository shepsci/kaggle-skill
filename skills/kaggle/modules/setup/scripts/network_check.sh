#!/usr/bin/env bash
# Quick network diagnostic for Kaggle reachability.
#
# Checks the three hosts the skill talks to: api.kaggle.com (CLI and
# kagglehub), www.kaggle.com (MCP and web) and storage.googleapis.com
# (file downloads). Uses curl only, so it works where `timeout` is missing.
#
# Usage:
#   bash modules/setup/scripts/network_check.sh
#
# Exits:
#   0 if every host is reachable
#   1 if any is unreachable

set -euo pipefail

HOSTS=("api.kaggle.com" "www.kaggle.com" "storage.googleapis.com")
TIMEOUT=10
failures=0

if ! command -v curl >/dev/null 2>&1; then
    echo "[ERROR] curl is not installed; cannot check connectivity"
    exit 1
fi

for host in "${HOSTS[@]}"; do
    echo "[INFO] Checking HTTPS reachability: ${host}:443"

    # curl exit codes: 6 = could not resolve host, 7 = could not connect,
    # 28 = timed out. Any HTTP status at all means the host is reachable.
    rc=0
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -m "${TIMEOUT}" "https://${host}") || rc=$?
    if [[ "${rc}" -eq 0 && "${http_code}" != "000" ]]; then
        echo "[OK] HTTPS connection to ${host} succeeded (HTTP ${http_code})"
    elif [[ "${rc}" -eq 6 ]]; then
        echo "[ERROR] DNS resolution failed for ${host}"
        failures=$((failures + 1))
    else
        echo "[ERROR] Cannot reach ${host}:443 (curl exit ${rc})"
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
echo "  - If behind a proxy/firewall, allow outbound HTTPS to the hosts above"
echo "  - Try: export NO_PROXY=api.kaggle.com,www.kaggle.com,storage.googleapis.com"
echo "  - Check: curl -v https://api.kaggle.com 2>&1 | head -20"
exit 1
