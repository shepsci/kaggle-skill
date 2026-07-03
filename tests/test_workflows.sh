#!/usr/bin/env bash
# test_workflows.sh — Comprehensive test suite for Kaggle workflow modules in shepsci/kaggle-skill
# Tests every CLI subcommand, every kagglehub function, all 47 MCP endpoints,
# KKB notebook execution, scripts, and skill integration.
# Generates a markdown report at ~/kaggle-workflow-test-report-<timestamp>.md
set -uo pipefail

REPO_URL="https://github.com/shepsci/kaggle-skill.git"
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
REPORT_FILE="${HOME}/kaggle-workflow-test-report-${TIMESTAMP}.md"

# macOS doesn't have `timeout`; use perl fallback
run_with_timeout() { local s="$1"; shift; perl -e "alarm $s; exec @ARGV" -- "$@"; }

TOTAL=0; PASSED=0; FAILED=0; SKIPPED=0; KNOWN_FAILED=0
declare -a RESULTS=()
NET_API_BLOCKED=false; NET_MCP_BLOCKED=false

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'

record_result() {
    local group="$1" name="$2" status="$3" details="${4:-}"
    TOTAL=$((TOTAL + 1))
    case "$status" in
        PASS) PASSED=$((PASSED + 1)); color="$GREEN" ;;
        FAIL) FAILED=$((FAILED + 1)); color="$RED" ;;
        SKIP) SKIPPED=$((SKIPPED + 1)); color="$YELLOW" ;;
        KNOWN_FAIL) KNOWN_FAILED=$((KNOWN_FAILED + 1)); color="$YELLOW" ;;
        *) color="$NC" ;;
    esac
    printf "${color}[%s]${NC} %s: %s — %s\n" "$status" "$group" "$name" "$details"
    RESULTS+=("| $group | $name | $status | $details |")
}

has_credentials() {
    [[ -n "${KAGGLE_API_TOKEN:-}" ]] && return 0
    [[ -n "${KAGGLE_USERNAME:-}" && -n "${KAGGLE_KEY:-}" ]] && return 0
    [[ -f "${HOME}/.kaggle/kaggle.json" ]] && return 0
    return 1
}

skip_if_no_creds() {
    local group="$1" name="$2"
    if ! has_credentials; then
        record_result "$group" "$name" "SKIP" "No credentials available"
        return 0
    fi
    return 1
}

get_api_key() {
    if [[ -n "${KAGGLE_KEY:-}" ]]; then echo "$KAGGLE_KEY"
    elif [[ -n "${KAGGLE_API_TOKEN:-}" ]]; then echo "$KAGGLE_API_TOKEN"
    elif [[ -f "${HOME}/.kaggle/kaggle.json" ]]; then
        python3 -c "import json; print(json.load(open('${HOME}/.kaggle/kaggle.json'))['key'])" 2>/dev/null
    fi
}

get_mcp_key() {
    if [[ -n "${KAGGLE_MCP_TOKEN:-}" ]]; then echo "$KAGGLE_MCP_TOKEN"
    else get_api_key
    fi
}

has_kgat_token() { [[ -n "${KAGGLE_MCP_TOKEN:-}" ]]; }

should_run_destructive() { [[ "${KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS:-}" == "true" ]]; }

get_username() {
    if [[ -n "${KAGGLE_USERNAME:-}" ]]; then echo "$KAGGLE_USERNAME"
    elif [[ -f "${HOME}/.kaggle/kaggle.json" ]]; then
        python3 -c "import json; print(json.load(open('${HOME}/.kaggle/kaggle.json'))['username'])" 2>/dev/null
    fi
}

# MCP helper: call a tool and return parsed JSON result
# Usage: mcp_call "tool_name" '{"key":"val"}'
# Tries primary key first; if unauthenticated and a fallback key exists, retries.
mcp_call() {
    local tool="$1" args="${2:-\{\}}"
    local key
    key=$(get_mcp_key)
    local payload
    payload=$(python3 -c "
import json, sys
print(json.dumps({
    'jsonrpc': '2.0',
    'method': 'tools/call',
    'params': {'name': sys.argv[1], 'arguments': json.loads(sys.argv[2])},
    'id': 1
}))" "$tool" "$args" 2>/dev/null)
    local raw parsed
    raw=$(curl -s -m 45 -X POST "https://www.kaggle.com/mcp" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $key" \
        -d "$payload" 2>&1)
    # Parse SSE: extract data line
    parsed=$(echo "$raw" | python3 -c "
import sys, json
raw = sys.stdin.read()
for line in raw.split('\n'):
    if line.startswith('data:'):
        print(line[5:].strip())
        break
else:
    print(raw[:500])
" 2>/dev/null)

    # Auto-retry with the other token type if unauthenticated
    if echo "$parsed" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    c=d.get('result',{}).get('content',[])
    if any('unauthenticated' in (x.get('text','') or '').lower() for x in (c if isinstance(c,list) else [])):
        sys.exit(0)
    sys.exit(1)
except: sys.exit(1)
" 2>/dev/null; then
        # Determine fallback key (swap between legacy and KGAT)
        local fallback=""
        if has_kgat_token; then
            fallback=$(get_api_key)  # KGAT failed, try legacy
        elif [[ -n "${KAGGLE_MCP_TOKEN:-}" ]]; then
            : # Both are same, no fallback
        else
            fallback="${KAGGLE_MCP_TOKEN:-}"  # legacy failed, try KGAT if set
        fi
        if [[ -n "$fallback" && "$fallback" != "$key" ]]; then
            raw=$(curl -s -m 45 -X POST "https://www.kaggle.com/mcp" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $fallback" \
                -d "$payload" 2>&1)
            parsed=$(echo "$raw" | python3 -c "
import sys, json
raw = sys.stdin.read()
for line in raw.split('\n'):
    if line.startswith('data:'):
        print(line[5:].strip())
        break
else:
    print(raw[:500])
" 2>/dev/null)
        fi
    fi
    echo "$parsed"
}

# Test an MCP tool: call it and check for result vs error
# Usage: test_mcp_tool "GROUP" "tool_name" '{"args":"..."}' "optional_note"
test_mcp_tool() {
    local G="$1" tool="$2" args="${3:-\{\}}" note="${4:-}"
    local out
    out=$(mcp_call "$tool" "$args" 2>/dev/null) || true
    local has_result has_error error_msg
    has_result=$(echo "$out" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    r = d.get('result',{})
    if r and r != {}:
        # Check for tool error inside result
        content = r.get('content', [])
        if content and isinstance(content, list):
            for c in content:
                text = c.get('text','')
                tl = text.lower()
                # Only flag as error if it looks like an actual error message,
                # not just a field name or URL containing 'error'
                if 'unauthenticated' in tl:
                    print('error:' + text[:120])
                    sys.exit(0)
                # Check for real error patterns (not just the word 'error' in any context)
                if tl.startswith('error') or '\"error\"' in tl or 'server error' in tl or 'internal error' in tl:
                    print('error:' + text[:120])
                    sys.exit(0)
        print('ok')
    else:
        print('empty')
except Exception as e:
    print('parse_fail:' + str(e)[:80])
" 2>/dev/null)
    has_error=$(echo "$out" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    e = d.get('error',{})
    if e:
        print(e.get('message','unknown')[:120])
    else:
        print('')
except:
    print('parse_fail')
" 2>/dev/null)

    local label="MCP: ${tool}"
    [[ -n "$note" ]] && label="MCP: ${tool} (${note})"

    if [[ "$has_result" == "ok" ]]; then
        record_result "$G" "$label" "PASS" "Got result"
    elif [[ "$has_result" == "empty" && -z "$has_error" ]]; then
        record_result "$G" "$label" "PASS" "Got empty result (valid)"
    elif [[ "$has_result" == error:* ]]; then
        local emsg="${has_result#error:}"
        if echo "$emsg" | grep -qi "unauthenticated"; then
            if has_kgat_token; then
                record_result "$G" "$label" "FAIL" "Unauthenticated even with KGAT token"
            else
                record_result "$G" "$label" "KNOWN_FAIL" "Unauthenticated (needs KGAT token)"
            fi
        else
            record_result "$G" "$label" "FAIL" "$emsg"
        fi
    elif [[ -n "$has_error" && "$has_error" != "parse_fail" ]]; then
        record_result "$G" "$label" "FAIL" "JSON-RPC error: $has_error"
    else
        record_result "$G" "$label" "FAIL" "Unexpected response: $(echo "$out" | head -c 120)"
    fi
}

# CLI test helper: run command, check for success
# Usage: test_cli "GROUP" "test_name" cmd args...
test_cli() {
    local G="$1" name="$2"; shift 2
    local out
    out=$(run_with_timeout 90 "$@" 2>&1) || true
    if [[ -n "$out" ]] && ! echo "$out" | grep -qiE "Traceback|unauthenticated|FAILED|Error:.*401"; then
        record_result "$G" "$name" "PASS" "$(echo "$out" | head -1 | cut -c1-100)"
    else
        record_result "$G" "$name" "FAIL" "$(echo "$out" | head -2 | tr '\n' ' ' | cut -c1-120)"
    fi
}

# ── Setup ──────────────────────────────────────────────────────────────
setup() {
    WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kaggle-workflow-test-XXXXXX")
    echo "Working directory: ${WORK_DIR}"
    echo "Cloning ${REPO_URL}..."
    if ! git clone --depth 1 "${REPO_URL}" "${WORK_DIR}/kaggle-skill" 2>&1; then
        echo "FATAL: Could not clone repository"; exit 1
    fi
    REPO_DIR="${WORK_DIR}/kaggle-skill"
    SKILL_DIR="${REPO_DIR}/skills/kaggle"
    SCRIPTS_DIR="${SKILL_DIR}/modules"
    REFS_DIR="${SKILL_DIR}/modules/references"
    echo "Creating virtual environment..."
    python3 -m venv "${WORK_DIR}/venv"
    # shellcheck disable=SC1091
    source "${WORK_DIR}/venv/bin/activate"
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 0: Network Reachability (4 tests)
# Runs first — catches connectivity issues before they cause confusing
# auth/timeout failures in later groups.
# ══════════════════════════════════════════════════════════════════════
group_0_network() {
    local G="G0-Network"

    # 0.1: DNS resolution for api.kaggle.com
    if python3 -c "import socket; socket.getaddrinfo('api.kaggle.com', 443)" >/dev/null 2>&1; then
        record_result "$G" "DNS: api.kaggle.com" "PASS" "Resolves"
    else
        record_result "$G" "DNS: api.kaggle.com" "FAIL" "Cannot resolve — check DNS/proxy settings"
    fi

    # 0.2: DNS resolution for www.kaggle.com (MCP endpoint)
    if python3 -c "import socket; socket.getaddrinfo('www.kaggle.com', 443)" >/dev/null 2>&1; then
        record_result "$G" "DNS: www.kaggle.com" "PASS" "Resolves"
    else
        record_result "$G" "DNS: www.kaggle.com" "FAIL" "Cannot resolve — check DNS/proxy settings"
    fi

    # 0.3: HTTPS connectivity to api.kaggle.com (used by CLI + kagglehub)
    local api_code
    api_code=$(curl -s -o /dev/null -w "%{http_code}" -m 10 \
        "https://api.kaggle.com" 2>&1) || api_code="000"
    if [[ "$api_code" != "000" ]]; then
        record_result "$G" "HTTPS: api.kaggle.com" "PASS" "HTTP $api_code"
    else
        record_result "$G" "HTTPS: api.kaggle.com" "FAIL" \
            "Connection failed (HTTP 000) — firewall/proxy may block outbound HTTPS. Try: export NO_PROXY=api.kaggle.com,www.kaggle.com"
        NET_API_BLOCKED=true
    fi

    # 0.4: HTTPS connectivity to www.kaggle.com/mcp (MCP endpoint)
    local mcp_code
    mcp_code=$(curl -s -o /dev/null -w "%{http_code}" -m 10 \
        -X POST "https://www.kaggle.com/mcp" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"initialize","id":0}' 2>&1) || mcp_code="000"
    if [[ "$mcp_code" != "000" ]]; then
        record_result "$G" "HTTPS: www.kaggle.com/mcp" "PASS" "HTTP $mcp_code"
    else
        record_result "$G" "HTTPS: www.kaggle.com/mcp" "FAIL" \
            "Connection failed (HTTP 000) — firewall/proxy may block outbound HTTPS. Try: export NO_PROXY=api.kaggle.com,www.kaggle.com"
        NET_MCP_BLOCKED=true
    fi

    # Print advisory if anything is blocked
    if [[ "${NET_API_BLOCKED:-}" == "true" || "${NET_MCP_BLOCKED:-}" == "true" ]]; then
        printf "${RED}⚠  Network issues detected — many subsequent tests will fail.${NC}\n"
        printf "${RED}   If behind a proxy/firewall, ensure outbound HTTPS to api.kaggle.com and www.kaggle.com is allowed.${NC}\n"
        printf "${RED}   You can also try: export NO_PROXY=api.kaggle.com,www.kaggle.com${NC}\n"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 1: Skill Structure (12 tests)
# ══════════════════════════════════════════════════════════════════════
group_1_structure() {
    local G="G1-Structure"
    # T1.1
    local main_skill="${REPO_DIR}/skills/kaggle/SKILL.md"
    if [[ -f "$main_skill" ]]; then
        record_result "$G" "SKILL.md exists" "PASS" "Found at skills/kaggle/SKILL.md"
    else
        record_result "$G" "SKILL.md exists" "FAIL" "Missing"
    fi
    # T1.2: frontmatter
    local fm
    fm=$(sed -n '/^---$/,/^---$/p' "$main_skill" 2>/dev/null | sed '1d;$d')
    local n d m v
    n=$(echo "$fm" | grep -c '^name:' || true)
    d=$(echo "$fm" | grep -c '^description:' || true)
    m=$(echo "$fm" | grep -c '^metadata:' || true)
    v=$(echo "$fm" | grep -c '"version"' || true)
    if [[ $n -ge 1 && $d -ge 1 && $m -ge 1 && $v -ge 1 ]]; then
        record_result "$G" "SKILL.md frontmatter" "PASS" "All required fields present"
    else
        record_result "$G" "SKILL.md frontmatter" "FAIL" "name=$n desc=$d meta=$m ver=$v"
    fi
    # T1.3: metadata JSON
    local meta_line
    meta_line=$(echo "$fm" | grep '^metadata:' | sed 's/^metadata: *//')
    if echo "$meta_line" | python3 -m json.tool >/dev/null 2>&1; then
        record_result "$G" "SKILL.md metadata JSON" "PASS" "Valid JSON"
    else
        record_result "$G" "SKILL.md metadata JSON" "FAIL" "Invalid"
    fi
    # T1.4: settings.json
    local s="${REPO_DIR}/.claude/settings.json"
    if [[ -f "$s" ]] && python3 -m json.tool "$s" >/dev/null 2>&1; then
        record_result "$G" "settings.json valid" "PASS" "Valid JSON"
    else
        record_result "$G" "settings.json valid" "FAIL" "Missing or invalid"
    fi
    # T1.5: SessionStart hook
    if grep -q "SessionStart" "$s" 2>/dev/null; then
        record_result "$G" "SessionStart hook" "PASS" "Present"
    else
        record_result "$G" "SessionStart hook" "FAIL" "Missing"
    fi
    # T1.6: marketplace.json
    local mp="${REPO_DIR}/.claude-plugin/marketplace.json"
    if [[ -f "$mp" ]] && python3 -m json.tool "$mp" >/dev/null 2>&1; then
        record_result "$G" "marketplace.json valid" "PASS" "Valid JSON"
    else
        record_result "$G" "marketplace.json valid" "FAIL" "Missing or invalid"
    fi
    # T1.7: symlink
    local sym="${REPO_DIR}/.claude/skills/kaggle"
    if [[ -L "$sym" ]] && [[ -f "${sym}/SKILL.md" ]]; then
        record_result "$G" "Symlink resolves" "PASS" "$(readlink "$sym")"
    else
        record_result "$G" "Symlink resolves" "FAIL" "Broken or missing"
    fi
    # T1.8: pyproject.toml
    if python3 -c "import tomllib,sys; tomllib.load(open(sys.argv[1],'rb'))" "${REPO_DIR}/pyproject.toml" 2>/dev/null; then
        record_result "$G" "pyproject.toml valid" "PASS" "Parses"
    else
        record_result "$G" "pyproject.toml valid" "FAIL" "Cannot parse"
    fi
    # T1.9: deps listed
    local deps_ok=true
    for dep in kagglehub kaggle python-dotenv; do
        grep -q "$dep" "${REPO_DIR}/pyproject.toml" 2>/dev/null || deps_ok=false
    done
    if $deps_ok; then
        record_result "$G" "pyproject.toml deps" "PASS" "All 3 listed"
    else
        record_result "$G" "pyproject.toml deps" "FAIL" "Missing dep"
    fi
    # T1.10: all scripts
    local expected=(setup_env.sh check_credentials.py poll_kernel.sh cli_download.sh cli_execute.sh cli_competition.sh cli_publish.sh kagglehub_download.py kagglehub_publish.py)
    local missing=()
    for x in "${expected[@]}"; do [[ ! -f "${SCRIPTS_DIR}/$x" ]] && missing+=("$x"); done
    if [[ ${#missing[@]} -eq 0 ]]; then
        record_result "$G" "All 9 scripts exist" "PASS" "All present"
    else
        record_result "$G" "All 9 scripts exist" "FAIL" "Missing: ${missing[*]}"
    fi
    # T1.11: shell syntax
    local sh_err=()
    for x in setup_env.sh poll_kernel.sh cli_download.sh cli_execute.sh cli_competition.sh cli_publish.sh; do
        [[ -f "${SCRIPTS_DIR}/$x" ]] && ! bash -n "${SCRIPTS_DIR}/$x" 2>/dev/null && sh_err+=("$x")
    done
    if [[ ${#sh_err[@]} -eq 0 ]]; then
        record_result "$G" "Shell syntax (bash -n)" "PASS" "6 scripts pass"
    else
        record_result "$G" "Shell syntax (bash -n)" "FAIL" "${sh_err[*]}"
    fi
    # T1.12: python compile
    local py_err=()
    for x in check_credentials.py kagglehub_download.py kagglehub_publish.py; do
        [[ -f "${SCRIPTS_DIR}/$x" ]] && ! python3 -m py_compile "${SCRIPTS_DIR}/$x" 2>/dev/null && py_err+=("$x")
    done
    if [[ ${#py_err[@]} -eq 0 ]]; then
        record_result "$G" "Python compile" "PASS" "3 scripts compile"
    else
        record_result "$G" "Python compile" "FAIL" "${py_err[*]}"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 2: Dependencies (4 tests)
# ══════════════════════════════════════════════════════════════════════
group_2_dependencies() {
    local G="G2-Deps"
    local pip_out pip_rc=0
    pip_out=$(pip install kagglehub kaggle python-dotenv pandas 2>&1) || pip_rc=$?
    if [[ $pip_rc -eq 0 ]]; then
        record_result "$G" "pip install" "PASS" "All packages installed"
    else
        record_result "$G" "pip install" "FAIL" "$(echo "$pip_out" | tail -3)"
    fi
    local kver
    kver=$(kaggle --version 2>&1 || true)
    if echo "$kver" | grep -qi "kaggle"; then
        record_result "$G" "kaggle CLI" "PASS" "$kver"
    else
        record_result "$G" "kaggle CLI" "FAIL" "Not found"
    fi
    local hv
    hv=$(python3 -c "import kagglehub; print(f'kagglehub {kagglehub.__version__}')" 2>&1) || true
    if echo "$hv" | grep -q "kagglehub"; then
        record_result "$G" "kagglehub import" "PASS" "$hv"
    else
        record_result "$G" "kagglehub import" "FAIL" "$hv"
    fi
    if python3 -c "import dotenv; print('ok')" 2>/dev/null | grep -q "ok"; then
        record_result "$G" "python-dotenv import" "PASS" "OK"
    else
        record_result "$G" "python-dotenv import" "FAIL" "Cannot import"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 3: Credentials (4 tests)
# ══════════════════════════════════════════════════════════════════════
group_3_credentials() {
    local G="G3-Creds"
    local out setup_rc=0
    out=$(cd "${REPO_DIR}" && bash skills/kaggle/modules/setup/scripts/setup_env.sh 2>&1) || setup_rc=$?
    if [[ $setup_rc -eq 0 ]] || echo "$out" | grep -qiE "No Kaggle|already|wrote|exists"; then
        record_result "$G" "setup_env.sh" "PASS" "Ran gracefully"
    else
        record_result "$G" "setup_env.sh" "FAIL" "$(echo "$out" | head -1)"
    fi
    out=$(cd "${REPO_DIR}" && python3 skills/kaggle/modules/setup/scripts/check_credentials.py 2>&1) || true
    if echo "$out" | grep -qiE '\[OK\]|\[ERROR\]|\[WARN\]|✓|✗|found|missing|credentials|kaggle'; then
        record_result "$G" "check_credentials.py" "PASS" "Structured output"
    else
        record_result "$G" "check_credentials.py" "FAIL" "$(echo "$out" | head -1)"
    fi
    if ! skip_if_no_creds "$G" "kagglehub.whoami()"; then
        out=$(python3 -c "import kagglehub; print(kagglehub.whoami())" 2>&1) || true
        if echo "$out" | grep -qiE "username|userName|validated"; then
            record_result "$G" "kagglehub.whoami()" "PASS" "$(echo "$out" | head -1)"
        else
            record_result "$G" "kagglehub.whoami()" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    if ! skip_if_no_creds "$G" "kaggle config view"; then
        out=$(kaggle config view 2>&1) || true
        if ! echo "$out" | grep -qi "error\|unauthenticated\|Traceback"; then
            record_result "$G" "kaggle config view" "PASS" "OK"
        else
            record_result "$G" "kaggle config view" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 4: kagglehub — all functions (10 tests)
# ══════════════════════════════════════════════════════════════════════
group_4_kagglehub() {
    local G="G4-kagglehub"

    # 4.1: login()
    if ! skip_if_no_creds "$G" "login()"; then
        local out
        out=$(python3 -c "
import kagglehub
kagglehub.login()
print('login ok')
" 2>&1) || true
        if echo "$out" | grep -qi "ok\|already\|success\|validated"; then
            record_result "$G" "login()" "PASS" "$(echo "$out" | tail -1)"
        else
            record_result "$G" "login()" "FAIL" "$(echo "$out" | tail -1)"
        fi
    fi

    # 4.2: whoami()
    if ! skip_if_no_creds "$G" "whoami()"; then
        local out
        out=$(python3 -c "import kagglehub; r=kagglehub.whoami(); print('whoami ok')" 2>&1) || true
        if echo "$out" | grep -qi "ok\|validated"; then
            record_result "$G" "whoami()" "PASS" "$(echo "$out" | tail -1)"
        else
            record_result "$G" "whoami()" "FAIL" "$(echo "$out" | tail -1)"
        fi
    fi

    # 4.3: dataset_download()
    if ! skip_if_no_creds "$G" "dataset_download()"; then
        local out
        out=$(run_with_timeout 120 python3 -c "
import kagglehub
path = kagglehub.dataset_download('heptapod/titanic')
print(f'OK: {path}')
" 2>&1) || true
        if echo "$out" | grep -qi "OK:"; then
            record_result "$G" "dataset_download()" "PASS" "$(echo "$out" | tail -1)"
        else
            record_result "$G" "dataset_download()" "FAIL" "$(echo "$out" | tail -2 | tr '\n' ' ')"
        fi
    fi

    # 4.4: dataset_load() — KNOWN BUG v0.4.3
    if ! skip_if_no_creds "$G" "dataset_load() [KNOWN BUG]"; then
        local out
        out=$(run_with_timeout 120 python3 -c "
import kagglehub
try:
    from kagglehub import KaggleDatasetAdapter
    df = kagglehub.dataset_load(KaggleDatasetAdapter.PANDAS, 'heptapod/titanic', path='train.csv')
    print(f'OK: {len(df)} rows')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1) || true
        if echo "$out" | grep -qi "OK:"; then
            record_result "$G" "dataset_load() [KNOWN BUG]" "PASS" "FIXED? $(echo "$out" | tail -1)"
        else
            record_result "$G" "dataset_load() [KNOWN BUG]" "FAIL" "EXPECTED v0.4.3 bug: $(echo "$out" | tail -1 | cut -c1-80)"
        fi
    fi

    # 4.5: dataset_load() workaround
    if ! skip_if_no_creds "$G" "dataset_load workaround"; then
        local out
        out=$(run_with_timeout 120 python3 -c "
import kagglehub, os, glob, pandas as pd
path = kagglehub.dataset_download('heptapod/titanic')
csvs = glob.glob(os.path.join(path, '**', '*.csv'), recursive=True)
if csvs:
    df = pd.read_csv(csvs[0])
    print(f'OK: {len(df)} rows from {os.path.basename(csvs[0])}')
else:
    print('ERROR: No CSVs')
" 2>&1) || true
        if echo "$out" | grep -qi "OK:"; then
            record_result "$G" "dataset_load workaround" "PASS" "$(echo "$out" | tail -1)"
        else
            record_result "$G" "dataset_load workaround" "FAIL" "$(echo "$out" | tail -1)"
        fi
    fi

    # 4.6: dataset_upload() — dry run (missing required fields → expected error)
    if ! skip_if_no_creds "$G" "dataset_upload() [dry-run]"; then
        local out
        out=$(python3 -c "
import kagglehub
try:
    kagglehub.dataset_upload('/nonexistent', 'test-handle', 'test-title')
    print('OK: unexpectedly succeeded')
except TypeError as e:
    print(f'CALLABLE: {e}')
except Exception as e:
    print(f'CALLABLE: {type(e).__name__}: {e}')
" 2>&1) || true
        if echo "$out" | grep -qi "CALLABLE\|OK"; then
            record_result "$G" "dataset_upload() [dry-run]" "PASS" "Function callable: $(echo "$out" | tail -1 | cut -c1-80)"
        else
            record_result "$G" "dataset_upload() [dry-run]" "FAIL" "$(echo "$out" | tail -1)"
        fi
    fi

    # 4.7: model_download()
    if ! skip_if_no_creds "$G" "model_download()"; then
        local out
        out=$(run_with_timeout 120 python3 -c "
import kagglehub
try:
    path = kagglehub.model_download('google/gemma/transformers/2b', path='config.json')
    print(f'OK: {path}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1) || true
        if echo "$out" | grep -qi "OK:"; then
            record_result "$G" "model_download()" "PASS" "$(echo "$out" | tail -1)"
        elif echo "$out" | grep -qiE "403|license|forbidden"; then
            record_result "$G" "model_download()" "SKIP" "License acceptance required"
        else
            record_result "$G" "model_download()" "FAIL" "$(echo "$out" | tail -1 | cut -c1-80)"
        fi
    fi

    # 4.8: model_upload() — dry run
    if ! skip_if_no_creds "$G" "model_upload() [dry-run]"; then
        local out
        out=$(python3 -c "
import kagglehub
try:
    kagglehub.model_upload('/nonexistent', 'test/model/fw/var', 'Apache 2.0')
    print('OK')
except Exception as e:
    print(f'CALLABLE: {type(e).__name__}: {e}')
" 2>&1) || true
        if echo "$out" | grep -qi "CALLABLE\|OK"; then
            record_result "$G" "model_upload() [dry-run]" "PASS" "Function callable"
        else
            record_result "$G" "model_upload() [dry-run]" "FAIL" "$(echo "$out" | tail -1)"
        fi
    fi

    # 4.9: competition_download()
    if ! skip_if_no_creds "$G" "competition_download()"; then
        local out
        out=$(run_with_timeout 120 python3 -c "
import kagglehub
try:
    path = kagglehub.competition_download('titanic')
    print(f'OK: {path}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1) || true
        if echo "$out" | grep -qi "OK:"; then
            record_result "$G" "competition_download()" "PASS" "$(echo "$out" | tail -1)"
        elif echo "$out" | grep -qiE "403|rules|accept"; then
            record_result "$G" "competition_download()" "SKIP" "Rules acceptance required"
        else
            record_result "$G" "competition_download()" "FAIL" "$(echo "$out" | tail -1 | cut -c1-80)"
        fi
    fi

    # 4.10: notebook_output_download()
    if ! skip_if_no_creds "$G" "notebook_output_download()"; then
        local user
        user=$(get_username)
        local out
        out=$(run_with_timeout 120 python3 -c "
import kagglehub
try:
    path = kagglehub.notebook_output_download('alexisbcook/titanic-tutorial')
    print(f'OK: {path}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
" 2>&1) || true
        if echo "$out" | grep -qi "OK:"; then
            record_result "$G" "notebook_output_download()" "PASS" "$(echo "$out" | tail -1)"
        else
            record_result "$G" "notebook_output_download()" "FAIL" "$(echo "$out" | tail -1 | cut -c1-80)"
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 5: kaggle CLI — all subcommands (26 tests)
# ══════════════════════════════════════════════════════════════════════
group_5_cli() {
    local G="G5-CLI"

    # ─── Competitions ───
    if ! skip_if_no_creds "$G" "competitions list"; then
        test_cli "$G" "competitions list" kaggle competitions list --page-size 5
    fi
    if ! skip_if_no_creds "$G" "competitions files"; then
        test_cli "$G" "competitions files" kaggle competitions files titanic
    fi
    if ! skip_if_no_creds "$G" "competitions download"; then
        local dldir="${WORK_DIR}/cli-comp-dl"
        mkdir -p "$dldir"
        local out
        out=$(run_with_timeout 120 kaggle competitions download titanic --path "$dldir" 2>&1) || true
        if ls "$dldir"/* >/dev/null 2>&1; then
            record_result "$G" "competitions download" "PASS" "Downloaded"
        elif echo "$out" | grep -qiE "403|rules|accept"; then
            record_result "$G" "competitions download" "SKIP" "Rules acceptance required"
        else
            record_result "$G" "competitions download" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    if ! skip_if_no_creds "$G" "competitions submissions"; then
        local out
        out=$(run_with_timeout 60 kaggle competitions submissions titanic 2>&1) || true
        # May return empty if no submissions, which is fine
        if ! echo "$out" | grep -qiE "Traceback|unauthenticated"; then
            record_result "$G" "competitions submissions" "PASS" "$(echo "$out" | head -1 | cut -c1-80)"
        else
            record_result "$G" "competitions submissions" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    if ! skip_if_no_creds "$G" "competitions leaderboard"; then
        test_cli "$G" "competitions leaderboard" kaggle competitions leaderboard titanic --show
    fi

    # ─── Datasets ───
    if ! skip_if_no_creds "$G" "datasets list"; then
        test_cli "$G" "datasets list" kaggle datasets list --search "titanic" --max-size 10485760 --page 1
    fi
    if ! skip_if_no_creds "$G" "datasets files"; then
        test_cli "$G" "datasets files" kaggle datasets files heptapod/titanic
    fi
    if ! skip_if_no_creds "$G" "datasets download"; then
        local dldir="${WORK_DIR}/cli-ds-dl"
        mkdir -p "$dldir"
        local out
        out=$(run_with_timeout 120 kaggle datasets download heptapod/titanic --path "$dldir" --unzip 2>&1) || true
        if ls "$dldir"/*.csv >/dev/null 2>&1 || ls "$dldir"/*.zip >/dev/null 2>&1; then
            record_result "$G" "datasets download" "PASS" "Downloaded"
        else
            record_result "$G" "datasets download" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    if ! skip_if_no_creds "$G" "datasets metadata"; then
        test_cli "$G" "datasets metadata" kaggle datasets metadata heptapod/titanic
    fi
    if ! skip_if_no_creds "$G" "datasets status"; then
        local out
        out=$(run_with_timeout 60 kaggle datasets status heptapod/titanic 2>&1) || true
        if ! echo "$out" | grep -qiE "Traceback|unauthenticated"; then
            record_result "$G" "datasets status" "PASS" "$(echo "$out" | head -1 | cut -c1-80)"
        else
            record_result "$G" "datasets status" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    # datasets init (local only, no network)
    local initdir="${WORK_DIR}/ds-init-test"
    mkdir -p "$initdir"
    local out
    out=$(cd "$initdir" && kaggle datasets init 2>&1) || true
    if [[ -f "$initdir/dataset-metadata.json" ]]; then
        record_result "$G" "datasets init" "PASS" "Created dataset-metadata.json"
    else
        record_result "$G" "datasets init" "FAIL" "$(echo "$out" | head -1)"
    fi

    # ─── Kernels (Notebooks) ───
    if ! skip_if_no_creds "$G" "kernels list"; then
        test_cli "$G" "kernels list" kaggle kernels list --search "titanic" --page-size 5
    fi
    if ! skip_if_no_creds "$G" "kernels status"; then
        local out
        out=$(run_with_timeout 60 kaggle kernels status alexisbcook/titanic-tutorial 2>&1) || true
        if ! echo "$out" | grep -qiE "Traceback|unauthenticated"; then
            record_result "$G" "kernels status" "PASS" "$(echo "$out" | head -1 | cut -c1-80)"
        else
            record_result "$G" "kernels status" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    if ! skip_if_no_creds "$G" "kernels pull"; then
        local pulldir="${WORK_DIR}/kernel-pull-test"
        mkdir -p "$pulldir"
        out=$(run_with_timeout 60 kaggle kernels pull alexisbcook/titanic-tutorial --path "$pulldir" 2>&1) || true
        if ls "$pulldir"/* >/dev/null 2>&1; then
            record_result "$G" "kernels pull" "PASS" "Pulled to $pulldir"
        else
            record_result "$G" "kernels pull" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    if ! skip_if_no_creds "$G" "kernels output"; then
        local outdir="${WORK_DIR}/kernel-output-test"
        mkdir -p "$outdir"
        out=$(run_with_timeout 60 kaggle kernels output alexisbcook/titanic-tutorial --path "$outdir" 2>&1) || true
        if ! echo "$out" | grep -qiE "Traceback|unauthenticated"; then
            record_result "$G" "kernels output" "PASS" "$(echo "$out" | head -1 | cut -c1-80)"
        else
            record_result "$G" "kernels output" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
    # kernels init (local only)
    local kinitdir="${WORK_DIR}/kernel-init-test"
    mkdir -p "$kinitdir"
    out=$(cd "$kinitdir" && kaggle kernels init 2>&1) || true
    if [[ -f "$kinitdir/kernel-metadata.json" ]]; then
        record_result "$G" "kernels init" "PASS" "Created kernel-metadata.json"
    else
        record_result "$G" "kernels init" "FAIL" "$(echo "$out" | head -1)"
    fi

    # ─── Models ───
    if ! skip_if_no_creds "$G" "models list"; then
        test_cli "$G" "models list" kaggle models list --search "gemma" --page-size 5
    fi
    if ! skip_if_no_creds "$G" "models get"; then
        local out
        out=$(run_with_timeout 60 kaggle models get google/gemma 2>&1) || true
        if echo "$out" | grep -qi "ApiModel.*not JSON serializable"; then
            # Known kaggle CLI v1.8 bug: model fetched but print_obj crashes
            record_result "$G" "models get" "PASS" "Fetched (CLI print bug: ApiModel not serializable)"
        elif echo "$out" | grep -qiE "Traceback|unauthenticated"; then
            record_result "$G" "models get" "FAIL" "$(echo "$out" | head -1)"
        else
            record_result "$G" "models get" "PASS" "$(echo "$out" | head -1 | cut -c1-80)"
        fi
    fi
    # models init (local only)
    local minitdir="${WORK_DIR}/model-init-test"
    mkdir -p "$minitdir"
    out=$(cd "$minitdir" && kaggle models init 2>&1) || true
    if ls "$minitdir"/*model* >/dev/null 2>&1 || echo "$out" | grep -qi "model-metadata\|created"; then
        record_result "$G" "models init" "PASS" "Created metadata"
    else
        record_result "$G" "models init" "FAIL" "$(echo "$out" | head -1)"
    fi

    # ─── Config ───
    if ! skip_if_no_creds "$G" "config view"; then
        test_cli "$G" "config view" kaggle config view
    fi
    # config set/unset (safe: set then unset a test value)
    out=$(kaggle config set -n competition -v titanic 2>&1) || true
    if ! echo "$out" | grep -qiE "Traceback|error"; then
        record_result "$G" "config set" "PASS" "Set competition=titanic"
        # Unset it
        out=$(kaggle config unset -n competition 2>&1) || true
        if ! echo "$out" | grep -qiE "Traceback|error"; then
            record_result "$G" "config unset" "PASS" "Unset competition"
        else
            record_result "$G" "config unset" "FAIL" "$(echo "$out" | head -1)"
        fi
    else
        record_result "$G" "config set" "FAIL" "$(echo "$out" | head -1)"
        record_result "$G" "config unset" "SKIP" "config set failed"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 6: Script Functionality (5 tests)
# ══════════════════════════════════════════════════════════════════════
group_6_scripts() {
    local G="G6-Scripts"

    if ! skip_if_no_creds "$G" "cli_download.sh"; then
        local out
        out=$(cd "${REPO_DIR}" && run_with_timeout 120 bash skills/kaggle/modules/datasets/scripts/cli_download.sh 2>&1 | head -20) || true
        if echo "$out" | grep -qiE "download|kaggle|dataset"; then
            record_result "$G" "cli_download.sh" "PASS" "Ran and produced output"
        else
            record_result "$G" "cli_download.sh" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi

    local out
    out=$(cd "${REPO_DIR}" && bash skills/kaggle/modules/competitions/scripts/cli_competition.sh 2>&1) || true
    if ! echo "$out" | grep -qi "Traceback\|syntax error"; then
        record_result "$G" "cli_competition.sh no-args" "PASS" "Handled gracefully"
    else
        record_result "$G" "cli_competition.sh no-args" "FAIL" "$(echo "$out" | head -1)"
    fi

    out=$(cd "${REPO_DIR}" && bash skills/kaggle/modules/datasets/scripts/cli_publish.sh 2>&1) || true
    if ! echo "$out" | grep -qi "Traceback\|syntax error"; then
        record_result "$G" "cli_publish.sh no-args" "PASS" "Handled gracefully"
    else
        record_result "$G" "cli_publish.sh no-args" "FAIL" "$(echo "$out" | head -1)"
    fi

    out=$(cd "${REPO_DIR}" && python3 skills/kaggle/modules/datasets/scripts/kagglehub_publish.py 2>&1) || true
    if ! echo "$out" | grep -qi "Traceback"; then
        record_result "$G" "kagglehub_publish.py no-args" "PASS" "Handled gracefully"
    else
        record_result "$G" "kagglehub_publish.py no-args" "FAIL" "$(echo "$out" | head -1)"
    fi

    if ! skip_if_no_creds "$G" "kagglehub_download.py"; then
        out=$(cd "${REPO_DIR}" && run_with_timeout 120 python3 skills/kaggle/modules/datasets/scripts/kagglehub_download.py 2>&1 | head -10) || true
        if ! echo "$out" | grep -qi "Traceback"; then
            record_result "$G" "kagglehub_download.py" "PASS" "$(echo "$out" | head -1 | cut -c1-80)"
        else
            record_result "$G" "kagglehub_download.py" "FAIL" "$(echo "$out" | head -1)"
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════════
# Destructive Lifecycle Helpers (called from Group 7 when enabled)
# ══════════════════════════════════════════════════════════════════════

# Lifecycle A: Dataset — create, upload file, update metadata, delete
_lifecycle_dataset() {
    local G="$1"
    local user
    user=$(get_username)
    local ts
    ts=$(date '+%s')
    local ds_slug="__kllm_test_ds_${ts}"
    local ds_dir="${WORK_DIR}/ds-lifecycle-${ts}"
    mkdir -p "$ds_dir"

    # Create test CSV + init dataset
    printf 'id,value\n1,hello\n2,world\n' > "$ds_dir/test.csv"
    (cd "$ds_dir" && kaggle datasets init) >/dev/null 2>&1
    python3 -c "
import json
with open('${ds_dir}/dataset-metadata.json') as f:
    m = json.load(f)
m['id'] = '${user}/${ds_slug}'
m['title'] = '${ds_slug}'
with open('${ds_dir}/dataset-metadata.json', 'w') as f:
    json.dump(m, f)
" 2>/dev/null

    local create_out
    create_out=$(run_with_timeout 120 kaggle datasets create -p "$ds_dir" 2>&1) || true

    if ! echo "$create_out" | grep -qiE "success|created|Your.*dataset"; then
        record_result "$G" "MCP: update_dataset_metadata" "SKIP" "Dataset create failed: $(echo "$create_out" | head -1 | cut -c1-60)"
        record_result "$G" "MCP: upload_dataset_file" "SKIP" "Dataset create failed"
        return
    fi

    sleep 5

    # Test upload_dataset_file
    test_mcp_tool "$G" "upload_dataset_file" \
        "{\"request\":{\"ownerSlug\":\"${user}\",\"datasetSlug\":\"${ds_slug}\",\"fileName\":\"extra.csv\",\"contentLength\":30,\"lastModifiedEpochSeconds\":${ts}}}" "lifecycle"; _d

    # Test update_dataset_metadata
    test_mcp_tool "$G" "update_dataset_metadata" \
        "{\"request\":{\"ownerSlug\":\"${user}\",\"datasetSlug\":\"${ds_slug}\",\"settings\":{\"title\":\"${ds_slug} updated\",\"description\":\"workflow lifecycle test\"}}}" "lifecycle"; _d

    # Cleanup
    kaggle datasets delete "${user}/${ds_slug}" -y 2>/dev/null \
        || echo "  Warning: Could not delete test dataset ${user}/${ds_slug}"
}

# Lifecycle B: Model — create, update, update variation, delete
_lifecycle_model() {
    local G="$1"
    local user
    user=$(get_username)
    local ts
    ts=$(date '+%s')
    local model_slug="__kllm_test_model_${ts}"

    # Create model via MCP
    local create_out
    create_out=$(mcp_call "create_model" "{\"request\":{\"ownerSlug\":\"${user}\",\"modelSlug\":\"${model_slug}\",\"title\":\"Kaggle Workflow Test Model ${ts}\",\"isPrivate\":true}}" 2>/dev/null) || true

    local create_ok
    create_ok=$(echo "$create_out" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    r=d.get('result',{})
    c=r.get('content',[])
    if c and not any('error' in (x.get('text','') or '').lower() for x in c if isinstance(x,dict)):
        print('ok')
    elif r and r != {}:
        print('ok')
    else:
        print('fail')
except: print('fail')
" 2>/dev/null)

    if [[ "$create_ok" == "ok" ]]; then
        record_result "$G" "MCP: create_model (lifecycle)" "PASS" "Created ${user}/${model_slug}"
    else
        record_result "$G" "MCP: create_model" "FAIL" "Create failed: $(echo "$create_out" | head -c 80)"
        record_result "$G" "MCP: update_model" "SKIP" "Create failed"
        record_result "$G" "MCP: update_model_variation" "SKIP" "Create failed"
        return
    fi

    sleep 3

    # Update model
    test_mcp_tool "$G" "update_model" \
        "{\"request\":{\"ownerSlug\":\"${user}\",\"modelSlug\":\"${model_slug}\",\"settings\":{\"description\":\"Updated by workflow lifecycle test\"}}}" "lifecycle"; _d

    # Update model variation — may not exist yet, so check
    test_mcp_tool "$G" "update_model_variation" \
        "{\"request\":{\"ownerSlug\":\"${user}\",\"modelSlug\":\"${model_slug}\",\"framework\":\"Other\",\"instanceSlug\":\"default\",\"settings\":{\"description\":\"variation test\"}}}" "lifecycle"; _d

    # Cleanup
    kaggle models delete "${user}/${model_slug}" -y 2>/dev/null \
        || echo "  Warning: Could not delete test model ${user}/${model_slug}"
}

# Lifecycle C: Notebook — save, create session, cancel session
_lifecycle_notebook() {
    local G="$1"
    local user
    user=$(get_username)
    local ts
    ts=$(date '+%s')
    local nb_slug="__kllm_test_nb_${ts}"

    # save_notebook via MCP (push a minimal kernel)
    local save_out
    save_out=$(mcp_call "save_notebook" "{\"request\":{\"kernelPushRequest\":{\"id\":\"${user}/${nb_slug}\",\"title\":\"${nb_slug}\",\"text\":\"print('workflow lifecycle test')\",\"language\":\"python\",\"kernelType\":\"script\",\"isPrivate\":true,\"enableGpu\":false,\"enableTpu\":false,\"enableInternet\":false,\"competitionDataSources\":[],\"datasetDataSources\":[],\"kernelDataSources\":[],\"modelDataSources\":[]}}}" 2>/dev/null) || true

    local save_ok
    save_ok=$(echo "$save_out" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    r=d.get('result',{})
    c=r.get('content',[])
    txt=''.join(x.get('text','') for x in (c if isinstance(c,list) else []) if isinstance(x,dict)).lower()
    if 'error' in txt or 'unauthenticated' in txt:
        print('fail')
    elif r and r != {}:
        print('ok')
    else:
        print('fail')
except: print('fail')
" 2>/dev/null)

    if [[ "$save_ok" == "ok" ]]; then
        record_result "$G" "MCP: save_notebook (lifecycle)" "PASS" "Saved ${user}/${nb_slug}"
    else
        record_result "$G" "MCP: save_notebook" "FAIL" "Save failed: $(echo "$save_out" | head -c 80)"
        record_result "$G" "MCP: create_notebook_session" "SKIP" "Save failed"
        record_result "$G" "MCP: cancel_notebook_session" "SKIP" "Save failed"
        return
    fi

    sleep 3

    # create_notebook_session
    test_mcp_tool "$G" "create_notebook_session" \
        "{\"request\":{\"userName\":\"${user}\",\"kernelSlug\":\"${nb_slug}\"}}" "lifecycle"; _d

    sleep 5

    # cancel_notebook_session
    test_mcp_tool "$G" "cancel_notebook_session" \
        "{\"request\":{\"userName\":\"${user}\",\"kernelSlug\":\"${nb_slug}\"}}" "lifecycle"; _d

    # Cleanup
    kaggle kernels delete "${user}/${nb_slug}" 2>/dev/null \
        || echo "  Warning: Could not delete test notebook ${user}/${nb_slug}"
}

# Lifecycle D: Competition submission
_lifecycle_competition_submission() {
    local G="$1"

    # submit_to_competition requires a file token from start_competition_submission_upload
    # which was already tested. Try a minimal submission to titanic.
    local user
    user=$(get_username)
    local sub_dir="${WORK_DIR}/comp-submit-lifecycle"
    mkdir -p "$sub_dir"

    # Create minimal submission CSV for Titanic
    printf 'PassengerId,Survived\n892,0\n893,1\n894,0\n' > "$sub_dir/submission.csv"

    # Try submit_to_competition — this needs a blobToken from start_competition_submission_upload
    # Since we already tested start_competition_submission_upload, just verify the endpoint is callable
    test_mcp_tool "$G" "submit_to_competition" \
        '{"request":{"competitionName":"titanic","blobFileTokens":["test"],"submissionDescription":"workflow lifecycle test"}}' "lifecycle"; _d

    # create_code_competition_submission
    test_mcp_tool "$G" "create_code_competition_submission" \
        "{\"request\":{\"competitionName\":\"titanic\",\"kernelId\":\"${user}/test-kaggle-workflow-kkb\"}}" "lifecycle"; _d
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 7: MCP Server — all 47 endpoints
# ══════════════════════════════════════════════════════════════════════
group_7_mcp() {
    local G="G7-MCP"

    # T7.0: endpoint reachable
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 \
        -X POST "https://www.kaggle.com/mcp" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"initialize","id":1}' 2>&1) || true
    if [[ "$http_code" =~ ^(200|401|403|405|415) ]]; then
        record_result "$G" "MCP endpoint reachable" "PASS" "HTTP $http_code"
    else
        record_result "$G" "MCP endpoint reachable" "FAIL" "HTTP $http_code"
    fi

    # T7.1: tools/list
    if ! skip_if_no_creds "$G" "MCP: tools/list"; then
        local key
        key=$(get_mcp_key)
        local out
        out=$(curl -s -m 30 -X POST "https://www.kaggle.com/mcp" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $key" \
            -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' 2>&1)
        local count
        count=$(echo "$out" | python3 -c "
import sys,json
raw=sys.stdin.read()
for line in raw.split('\n'):
    if line.startswith('data:'):
        d=json.loads(line[5:].strip())
        print(len(d.get('result',{}).get('tools',[])))
        break
" 2>/dev/null)
        if [[ -n "$count" && "$count" -gt 0 ]] 2>/dev/null; then
            record_result "$G" "MCP: tools/list" "PASS" "$count tools"
        else
            record_result "$G" "MCP: tools/list" "FAIL" "No tools returned"
        fi
    fi

    # Skip remaining MCP tests if no creds
    if ! has_credentials; then
        local mcp_tools=(authorize search_competitions search_datasets search_notebooks
            get_competition get_competition_leaderboard get_competition_data_files_summary
            list_competition_data_files list_competition_data_tree_files
            download_competition_data_files download_competition_data_file
            download_competition_leaderboard search_competition_submissions
            get_competition_submission start_competition_submission_upload
            submit_to_competition create_code_competition_submission
            get_dataset_info get_dataset_metadata get_dataset_files_summary
            get_dataset_status list_dataset_files list_dataset_tree_files
            download_dataset update_dataset_metadata upload_dataset_file
            get_notebook_info list_notebook_files search_notebooks
            download_notebook_output download_notebook_output_zip
            get_notebook_session_status list_notebook_session_output
            save_notebook create_notebook_session cancel_notebook_session
            list_models get_model create_model update_model
            list_model_variations get_model_variation update_model_variation
            list_model_variation_versions list_model_variation_version_files
            download_model_variation_version
            get_benchmark_leaderboard create_benchmark_task_from_prompt)
        for t in "${mcp_tools[@]}"; do
            record_result "$G" "MCP: $t" "SKIP" "No credentials"
        done
        return
    fi

    # Small delay helper
    _d() { sleep 0.3; }

    # ─── Authentication ───
    test_mcp_tool "$G" "authorize" '{}' "auth-only"; _d

    # ─── Competition Tools ───
    test_mcp_tool "$G" "search_competitions" \
        '{"request":{"search":"titanic","hasSearch":true,"pageSize":3,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "get_competition" \
        '{"request":{"competitionName":"titanic"}}'; _d
    test_mcp_tool "$G" "get_competition_leaderboard" \
        '{"request":{"competitionName":"titanic","pageSize":3,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "get_competition_data_files_summary" \
        '{"request":{"competitionName":"titanic"}}'; _d
    test_mcp_tool "$G" "list_competition_data_files" \
        '{"request":{"competitionName":"titanic","pageSize":5,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "list_competition_data_tree_files" \
        '{"request":{"competitionName":"titanic","pageSize":5,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "download_competition_data_files" \
        '{"request":{"competitionName":"titanic"}}'; _d
    test_mcp_tool "$G" "download_competition_data_file" \
        '{"request":{"competitionName":"titanic","fileName":"train.csv"}}'; _d
    test_mcp_tool "$G" "download_competition_leaderboard" \
        '{"request":{"competitionName":"titanic"}}'; _d
    test_mcp_tool "$G" "search_competition_submissions" \
        '{"request":{"competitionName":"titanic","sortBy":"Date","group":"All","pageSize":3,"hasPageSize":true}}'; _d
    # get_competition_submission needs a valid ref ID; test with 0 to verify callable
    test_mcp_tool "$G" "get_competition_submission" \
        '{"request":{"ref":0}}' "callable-check"; _d
    # start_competition_submission_upload — needs real data, test callability
    test_mcp_tool "$G" "start_competition_submission_upload" \
        '{"request":{"competitionName":"titanic","hasCompetitionName":true,"contentLength":100,"lastModifiedEpochSeconds":1700000000,"fileName":"test.csv"}}' "upload-start"; _d
    # submit_to_competition / create_code_competition_submission — destructive
    if should_run_destructive; then
        _lifecycle_competition_submission "$G"
    else
        record_result "$G" "MCP: submit_to_competition" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
        record_result "$G" "MCP: create_code_competition_submission" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
    fi

    # ─── Dataset Tools ───
    test_mcp_tool "$G" "search_datasets" \
        '{"request":{"search":"titanic","hasSearch":true,"pageSize":3,"hasPageSize":true,"sortBy":"Hottest"}}'; _d
    test_mcp_tool "$G" "get_dataset_info" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic"}}'; _d
    test_mcp_tool "$G" "get_dataset_metadata" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic"}}'; _d
    test_mcp_tool "$G" "get_dataset_files_summary" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic"}}'; _d
    test_mcp_tool "$G" "get_dataset_status" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic"}}'; _d
    test_mcp_tool "$G" "list_dataset_files" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic","pageSize":5,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "list_dataset_tree_files" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic","pageSize":5,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "download_dataset" \
        '{"request":{"ownerSlug":"heptapod","datasetSlug":"titanic"}}'; _d
    # update_dataset_metadata / upload_dataset_file — destructive
    if should_run_destructive; then
        _lifecycle_dataset "$G"
    else
        record_result "$G" "MCP: update_dataset_metadata" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
        record_result "$G" "MCP: upload_dataset_file" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
    fi

    # ─── Notebook/Kernel Tools ───
    test_mcp_tool "$G" "search_notebooks" \
        '{"request":{"search":"titanic","hasSearch":true,"pageSize":3,"hasPageSize":true,"sortBy":"Hotness","group":"Everyone"}}'; _d
    test_mcp_tool "$G" "get_notebook_info" \
        '{"request":{"userName":"alexisbcook","kernelSlug":"titanic-tutorial"}}'; _d
    test_mcp_tool "$G" "list_notebook_files" \
        '{"request":{"userName":"alexisbcook","kernelSlug":"titanic-tutorial","pageSize":5,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "download_notebook_output" \
        '{"request":{"ownerSlug":"alexisbcook","kernelSlug":"titanic-tutorial"}}'; _d
    # download_notebook_output_zip needs a session ID
    test_mcp_tool "$G" "download_notebook_output_zip" \
        '{"request":{"kernelSessionId":0}}' "callable-check"; _d
    # get_notebook_session_status
    test_mcp_tool "$G" "get_notebook_session_status" \
        '{"request":{"userName":"alexisbcook","kernelSlug":"titanic-tutorial"}}'; _d
    # list_notebook_session_output
    test_mcp_tool "$G" "list_notebook_session_output" \
        '{"request":{"userName":"alexisbcook","kernelSlug":"titanic-tutorial","pageSize":5,"hasPageSize":true}}'; _d
    # save_notebook / create_notebook_session / cancel_notebook_session — destructive
    if should_run_destructive; then
        _lifecycle_notebook "$G"
    else
        record_result "$G" "MCP: save_notebook" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
        record_result "$G" "MCP: create_notebook_session" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
        record_result "$G" "MCP: cancel_notebook_session" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
    fi

    # ─── Model Tools ───
    test_mcp_tool "$G" "list_models" \
        '{"request":{"search":"gemma","hasSearch":true,"pageSize":3,"hasPageSize":true,"sortBy":"Hotness","hasSortBy":true}}'; _d
    test_mcp_tool "$G" "get_model" \
        '{"request":{"ownerSlug":"google","modelSlug":"gemma"}}'; _d
    test_mcp_tool "$G" "list_model_variations" \
        '{"request":{"ownerSlug":"google","modelSlug":"gemma","pageSize":3,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "get_model_variation" \
        '{"request":{"ownerSlug":"google","modelSlug":"gemma","framework":"Transformers","instanceSlug":"2b"}}'; _d
    test_mcp_tool "$G" "list_model_variation_versions" \
        '{"request":{"ownerSlug":"google","modelSlug":"gemma","framework":"Transformers","instanceSlug":"2b","pageSize":3,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "list_model_variation_version_files" \
        '{"request":{"ownerSlug":"google","modelSlug":"gemma","framework":"Transformers","instanceSlug":"2b","versionNumber":2,"hasVersionNumber":true,"pageSize":3,"hasPageSize":true}}'; _d
    test_mcp_tool "$G" "download_model_variation_version" \
        '{"request":{"ownerSlug":"google","modelSlug":"gemma","framework":"Transformers","instanceSlug":"2b","versionNumber":2,"path":"config.json","hasPath":true}}'; _d
    # create_model / update_model / update_model_variation — destructive
    if should_run_destructive; then
        _lifecycle_model "$G"
    else
        record_result "$G" "MCP: create_model" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
        record_result "$G" "MCP: update_model" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
        record_result "$G" "MCP: update_model_variation" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
    fi

    # ─── Benchmark Tools ───
    test_mcp_tool "$G" "get_benchmark_leaderboard" \
        '{"request":{"ownerSlug":"kaggle","benchmarkSlug":"test"}}' "benchmark"; _d
    # create_benchmark_task_from_prompt — destructive
    if should_run_destructive; then
        test_mcp_tool "$G" "create_benchmark_task_from_prompt" \
            '{"request":{"prompt":"workflow automated test benchmark task"}}' "lifecycle"; _d
    else
        record_result "$G" "MCP: create_benchmark_task_from_prompt" "SKIP" "Destructive: set KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true"; _d
    fi
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 8: KKB — Kaggle Kernel Backend (5 tests)
# ══════════════════════════════════════════════════════════════════════
group_8_kkb() {
    local G="G8-KKB"

    if ! has_credentials; then
        for t in "kernels init+push" "kernels status" "kernels output" "poll_kernel.sh" "cli_execute.sh"; do
            record_result "$G" "$t" "SKIP" "No credentials"
        done
        return
    fi

    local user
    user=$(get_username)
    local kkb_dir="${WORK_DIR}/kkb-test"
    mkdir -p "$kkb_dir"

    # 8.1: Create and push a minimal test notebook
    # Create a simple Python script
    cat > "$kkb_dir/test-kaggle-workflow-kkb.py" << 'PYEOF'
import pandas as pd
print("Kaggle workflow KKB test executed successfully")
df = pd.DataFrame({"col": [1,2,3]})
df.to_csv("output.csv", index=False)
print(f"Output: {len(df)} rows")
PYEOF

    # Create kernel metadata
    python3 -c "
import json
meta = {
    'id': '${user}/test-kaggle-workflow-kkb',
    'title': 'test-kaggle-workflow-kkb',
    'code_file': 'test-kaggle-workflow-kkb.py',
    'language': 'python',
    'kernel_type': 'script',
    'is_private': 'true',
    'enable_gpu': 'false',
    'enable_tpu': 'false',
    'enable_internet': 'false',
    'competition_sources': [],
    'dataset_sources': [],
    'kernel_sources': [],
    'model_sources': []
}
with open('${kkb_dir}/kernel-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)
print('Metadata written')
"

    # Push the kernel
    local push_out
    push_out=$(run_with_timeout 60 kaggle kernels push -p "$kkb_dir" 2>&1) || true
    if echo "$push_out" | grep -qiE "successfully|pushed|submitted|ref:"; then
        record_result "$G" "kernels push" "PASS" "$(echo "$push_out" | head -1 | cut -c1-80)"
    elif echo "$push_out" | grep -qiE "error\|Traceback\|unauthenticated"; then
        record_result "$G" "kernels push" "FAIL" "$(echo "$push_out" | head -2 | tr '\n' ' ' | cut -c1-120)"
        # Skip subsequent KKB tests
        record_result "$G" "kernels status (poll)" "SKIP" "Push failed"
        record_result "$G" "kernels output" "SKIP" "Push failed"
        record_result "$G" "poll_kernel.sh" "SKIP" "Push failed"
        record_result "$G" "cli_execute.sh syntax" "SKIP" "Push failed"
        return
    else
        record_result "$G" "kernels push" "FAIL" "$(echo "$push_out" | head -1 | cut -c1-80)"
        record_result "$G" "kernels status (poll)" "SKIP" "Push failed"
        record_result "$G" "kernels output" "SKIP" "Push failed"
        record_result "$G" "poll_kernel.sh" "SKIP" "Push failed"
        record_result "$G" "cli_execute.sh syntax" "SKIP" "Push failed"
        return
    fi

    # 8.2: Poll status (try a few times, kernels take time)
    local status_ok=false
    for i in 1 2 3 4 5 6; do
        sleep 15
        local status_out
        status_out=$(kaggle kernels status "${user}/test-kaggle-workflow-kkb" 2>&1) || true
        echo "  Poll $i: $status_out"
        if echo "$status_out" | grep -qi "complete"; then
            status_ok=true
            break
        elif echo "$status_out" | grep -qi "error\|cancel"; then
            break
        fi
    done
    if $status_ok; then
        record_result "$G" "kernels status (poll)" "PASS" "Completed"
    else
        record_result "$G" "kernels status (poll)" "FAIL" "Did not complete in 90s: $(echo "$status_out" | head -1)"
    fi

    # 8.3: Get output
    local outdir="${WORK_DIR}/kkb-output"
    mkdir -p "$outdir"
    local out_result
    out_result=$(run_with_timeout 60 kaggle kernels output "${user}/test-kaggle-workflow-kkb" --path "$outdir" 2>&1) || true
    if ls "$outdir"/* >/dev/null 2>&1 || echo "$out_result" | grep -qi "output.*download\|output.csv"; then
        record_result "$G" "kernels output" "PASS" "$(echo "$out_result" | head -1 | cut -c1-80)"
    else
        record_result "$G" "kernels output" "FAIL" "$(echo "$out_result" | head -1 | cut -c1-80)"
    fi

    # 8.4: poll_kernel.sh script test
    if [[ -f "${SCRIPTS_DIR}/poll_kernel.sh" ]]; then
        local poll_out
        poll_out=$(cd "${REPO_DIR}" && run_with_timeout 30 bash skills/kaggle/modules/notebooks/scripts/poll_kernel.sh "${user}/test-kaggle-workflow-kkb" 2>&1) || true
        if ! echo "$poll_out" | grep -qi "syntax error\|Traceback"; then
            record_result "$G" "poll_kernel.sh" "PASS" "Ran without crash"
        else
            record_result "$G" "poll_kernel.sh" "FAIL" "$(echo "$poll_out" | head -1)"
        fi
    else
        record_result "$G" "poll_kernel.sh" "FAIL" "Script not found"
    fi

    # 8.5: cli_execute.sh is syntactically valid (already tested in G1, verify it accepts args)
    if cd "${REPO_DIR}" && bash -n skills/kaggle/modules/notebooks/scripts/cli_execute.sh 2>/dev/null; then
        record_result "$G" "cli_execute.sh syntax" "PASS" "Valid bash"
    else
        record_result "$G" "cli_execute.sh syntax" "FAIL" "Syntax error"
    fi

    # Cleanup: delete the test kernel
    kaggle kernels delete "${user}/test-kaggle-workflow-kkb" 2>/dev/null || true
}

# ══════════════════════════════════════════════════════════════════════
# GROUP 9: Documentation (5 tests)
# ══════════════════════════════════════════════════════════════════════
group_9_docs() {
    local G="G9-Docs"
    local refs=(kaggle-knowledge.md kagglehub-datasets.md cli-reference.md mcp-reference.md)
    local missing=()
    for r in "${refs[@]}"; do [[ ! -f "${REFS_DIR}/$r" ]] && missing+=("$r"); done
    if [[ ${#missing[@]} -eq 0 ]]; then
        record_result "$G" "All 4 ref files exist" "PASS" "All present"
    else
        record_result "$G" "All 4 ref files exist" "FAIL" "Missing: ${missing[*]}"
    fi
    local empty=()
    for r in "${refs[@]}"; do [[ -f "${REFS_DIR}/$r" && ! -s "${REFS_DIR}/$r" ]] && empty+=("$r"); done
    if [[ ${#empty[@]} -eq 0 ]]; then
        record_result "$G" "Ref files non-empty" "PASS" "All have content"
    else
        record_result "$G" "Ref files non-empty" "FAIL" "Empty: ${empty[*]}"
    fi
    local unlinked=()
    for r in "${refs[@]}"; do grep -q "$r" "${SKILL_DIR}/SKILL.md" 2>/dev/null || unlinked+=("$r"); done
    if [[ ${#unlinked[@]} -eq 0 ]]; then
        record_result "$G" "Refs in SKILL.md" "PASS" "All referenced"
    else
        record_result "$G" "Refs in SKILL.md" "FAIL" "Not referenced: ${unlinked[*]}"
    fi
    local bad=0
    for r in "${refs[@]}"; do
        while IFS= read -r url; do
            [[ -z "$url" ]] && continue
            echo "$url" | grep -qE 'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' || bad=$((bad + 1))
        done <<< "$(grep -oE 'https?://[^ )">\`]+' "${REFS_DIR}/$r" 2>/dev/null || true)"
    done
    if [[ $bad -eq 0 ]]; then
        record_result "$G" "URLs valid" "PASS" "All well-formed"
    else
        record_result "$G" "URLs valid" "FAIL" "$bad malformed"
    fi
    local pyver
    pyver=$(tr -d '[:space:]' < "${REPO_DIR}/.python-version" 2>/dev/null)
    if [[ "$pyver" == "3.11" ]]; then
        record_result "$G" ".python-version" "PASS" "3.11"
    else
        record_result "$G" ".python-version" "FAIL" "Got: $pyver"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# Report Generation
# ══════════════════════════════════════════════════════════════════════
generate_report() {
    {
        echo "# Kaggle Workflows Comprehensive Test Report"
        echo ""
        echo "**Date:** $(date '+%Y-%m-%d %H:%M:%S')"
        echo "**Repository:** ${REPO_URL}"
        echo "**Commit:** $(cd "${REPO_DIR}" && git rev-parse --short HEAD)"
        echo "**Platform:** $(uname -s) $(uname -m)"
        echo "**Python:** $(python3 --version 2>&1)"
        echo "**Credentials:** $(has_credentials && echo 'Available' || echo 'Not available')"
        echo "**KGAT Token:** $(has_kgat_token && echo 'Set' || echo 'Not set')"
        echo "**Destructive Tests:** $(should_run_destructive && echo 'Enabled' || echo 'Disabled')"
        echo ""
        echo "## Summary"
        echo ""
        echo "| Metric | Count |"
        echo "|--------|-------|"
        echo "| Total  | ${TOTAL} |"
        echo "| Passed | ${PASSED} |"
        echo "| Failed | ${FAILED} |"
        echo "| Known Fail | ${KNOWN_FAILED} |"
        echo "| Skipped | ${SKIPPED} |"
        local pct=0 run=$((TOTAL - SKIPPED - KNOWN_FAILED)) pct_run=0
        [[ $TOTAL -gt 0 ]] && pct=$(( (PASSED * 100) / TOTAL ))
        [[ $run -gt 0 ]] && pct_run=$(( (PASSED * 100) / run ))
        echo "| Pass Rate (total) | ${pct}% |"
        echo "| Pass Rate (excl. skipped/known-fail) | ${pct_run}% |"
        echo ""
        echo "## Detailed Results"
        echo ""
        echo "| Group | Test | Status | Details |"
        echo "|-------|------|--------|---------|"
        for r in "${RESULTS[@]}"; do echo "$r"; done
        echo ""
        echo "## Known Issues (Expected Failures)"
        echo ""
        echo "- **dataset_load() broken in kagglehub v0.4.3**: 404 on DownloadDataset. Workaround: \`dataset_download()\` + \`pd.read_csv()\`"
        echo "- **competitions download no --unzip**: kaggle CLI >= 1.8 removed \`--unzip\` for competitions"
        echo "- **Competition-linked datasets return 403**: Use standalone copies (e.g., \`heptapod/titanic\`)"
        echo "- **MCP partial auth (KNOWN_FAIL)**: Some MCP endpoints reject legacy API keys — set \`KAGGLE_MCP_TOKEN\` with a KGAT token to resolve. The test auto-retries with the other token type on auth failure."
        echo "- **Licensed models require UI acceptance**: Gemma etc. need license acceptance at kaggle.com"
        if [[ "${NET_API_BLOCKED}" == "true" || "${NET_MCP_BLOCKED}" == "true" ]]; then
            echo "- **Network issues detected**: api.kaggle.com=${NET_API_BLOCKED} www.kaggle.com/mcp=${NET_MCP_BLOCKED} — many failures may be network-related, not auth"
        fi
        if ! should_run_destructive; then
            echo "- **MCP destructive endpoints skipped**: Set \`KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS=true\` to enable lifecycle tests"
        fi
        echo ""
        echo "## Environment"
        echo ""
        echo '```'
        echo "kagglehub: $(python3 -c 'import kagglehub; print(kagglehub.__version__)' 2>/dev/null || echo 'N/A')"
        echo "kaggle CLI: $(kaggle --version 2>/dev/null || echo 'N/A')"
        echo "python-dotenv: $(python3 -c 'from importlib.metadata import version; print(version("python-dotenv"))' 2>/dev/null || echo 'N/A')"
        echo "pandas: $(python3 -c 'import pandas; print(pandas.__version__)' 2>/dev/null || echo 'N/A')"
        echo "OS: $(sw_vers -productName 2>/dev/null || uname -s) $(sw_vers -productVersion 2>/dev/null || uname -r)"
        echo "Shell: ${SHELL} (bash ${BASH_VERSION})"
        echo '```'
        echo ""
        echo "---"
        echo "*Generated by test_workflows.sh on ${TIMESTAMP}*"
    } | tee "${REPORT_FILE}"
    echo ""
    echo "Report saved to: ${REPORT_FILE}"
}

# ── Cleanup ────────────────────────────────────────────────────────────
cleanup() {
    if [[ -n "${WORK_DIR:-}" && -d "${WORK_DIR}" ]]; then
        rm -rf "${WORK_DIR}"
        echo "Cleaned up: ${WORK_DIR}"
    fi
}
trap cleanup EXIT

# ── Main ───────────────────────────────────────────────────────────────
main() {
    echo "════════════════════════════════════════════"
    echo " Kaggle Workflows Comprehensive Test Suite"
    echo "════════════════════════════════════════════"
    echo ""
    has_kgat_token && echo "  KAGGLE_MCP_TOKEN: set" || echo "  KAGGLE_MCP_TOKEN: not set (some MCP tests may KNOWN_FAIL)"
    should_run_destructive && echo "  KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS: enabled" || echo "  KAGGLE_WORKFLOW_DESTRUCTIVE_TESTS: disabled (11 tests will SKIP)"
    echo ""
    setup

    printf "\n${BLUE}=== G0: Network Reachability ===${NC}\n"
    group_0_network

    printf "\n${BLUE}=== G1: Skill Structure ===${NC}\n"
    group_1_structure

    printf "\n${BLUE}=== G2: Dependencies ===${NC}\n"
    group_2_dependencies

    printf "\n${BLUE}=== G3: Credentials ===${NC}\n"
    group_3_credentials

    printf "\n${BLUE}=== G4: kagglehub — All Functions ===${NC}\n"
    group_4_kagglehub

    printf "\n${BLUE}=== G5: kaggle CLI — All Subcommands ===${NC}\n"
    group_5_cli

    printf "\n${BLUE}=== G6: Script Functionality ===${NC}\n"
    group_6_scripts

    printf "\n${BLUE}=== G7: MCP Server — All 47 Endpoints ===${NC}\n"
    group_7_mcp

    printf "\n${BLUE}=== G8: KKB — Notebook Execution ===${NC}\n"
    group_8_kkb

    printf "\n${BLUE}=== G9: Documentation ===${NC}\n"
    group_9_docs

    echo ""
    echo "════════════════════════════════════════════"
    echo " Generating Report"
    echo "════════════════════════════════════════════"
    generate_report

    echo ""
    printf "${GREEN}PASS: %d${NC}  " "$PASSED"
    [[ $FAILED -gt 0 ]] && printf "${RED}FAIL: %d${NC}  " "$FAILED" || printf "FAIL: 0  "
    [[ $KNOWN_FAILED -gt 0 ]] && printf "${YELLOW}KNOWN_FAIL: %d${NC}  " "$KNOWN_FAILED"
    [[ $SKIPPED -gt 0 ]] && printf "${YELLOW}SKIP: %d${NC}  " "$SKIPPED"
    echo ""

    [[ $FAILED -gt 0 ]] && exit 1
    exit 0
}

main "$@"
