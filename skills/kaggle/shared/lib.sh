# shellcheck shell=bash
# Helpers for the shell wrappers. Source this file; do not run it.
#
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/shared/lib.sh"
#
# Every kaggle call goes through shared/kaggle_cli.py, which scrubs the
# environment, turns the CLI's exit-0 failures into real failures, and prints
# Kaggle's output inside untrusted-content blocks.

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# kaggle_run <label> <kaggle args...>   run and print wrapped output
kaggle_run() {
    local tool="$1"
    shift
    python3 "${SKILL_ROOT}/shared/kaggle_cli.py" --tool "${tool}" -- "$@"
}

# kaggle_raw <kaggle args...>   run and print raw stdout, for parsing only
kaggle_raw() {
    python3 "${SKILL_ROOT}/shared/kaggle_cli.py" --raw -- "$@"
}

# wrap_local <label> <command...>   wrap a local command's output
wrap_local() {
    local tool="$1"
    shift
    python3 "${SKILL_ROOT}/shared/untrusted.py" --source local --tool "${tool}" -- "$@"
}

# preflight_upload <folder>   refuse folders that contain credential files (exit 5)
preflight_upload() {
    python3 "${SKILL_ROOT}/shared/preflight.py" "$1"
}

# kernel_status <owner/kernel>   print the bare status word, e.g. COMPLETE
kernel_status() {
    local out status
    out="$(kaggle_raw kernels status "$1")" || return 1
    status="$(printf '%s\n' "${out}" \
        | sed -n 's/.* has status "\([A-Za-z_.]*\)".*/\1/p' | tail -n 1)"
    status="${status##*.}"
    printf '%s\n' "${status}" | tr '[:lower:]' '[:upper:]'
}

# kernel_wait <owner/kernel> [poll-seconds] [max-wait-seconds]
# Returns 0 complete, 1 failed or cancelled, 124 timed out, 4 status unavailable.
kernel_wait() {
    local slug="$1" interval="${2:-30}" max_wait="${3:-3600}"
    local elapsed=0 failures=0 status
    while :; do
        if status="$(kernel_status "${slug}")"; then
            failures=0
            echo "[$(date '+%H:%M:%S')] status: ${status:-UNKNOWN}"
            case "${status}" in
                COMPLETE) return 0 ;;
                ERROR | CANCEL_REQUESTED | CANCEL_ACKNOWLEDGED) return 1 ;;
            esac
        else
            failures=$((failures + 1))
            echo "[$(date '+%H:%M:%S')] status check failed (${failures} in a row)" >&2
            if [ "${failures}" -ge 5 ]; then
                return 4
            fi
        fi
        if [ "${elapsed}" -ge "${max_wait}" ]; then
            return 124
        fi
        sleep "${interval}"
        elapsed=$((elapsed + interval))
    done
}

# kernel_output <owner/kernel> <dir>   download output after a name check
# Returns 5 when a file name would escape <dir>, 4 when the names cannot be listed.
kernel_output() {
    local slug="$1" dir="$2"
    python3 "${SKILL_ROOT}/shared/kaggle_cli.py" --check-kernel-output "${slug}" || return $?
    mkdir -p "${dir}"
    kaggle_run kernels.output kernels output "${slug}" --path "${dir}" --quiet
}

# is_slug <value>   true for owner/name made of letters, digits, ".", "_" and "-"
is_slug() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
}

# is_positive_int <value>
# A leading zero is refused: bash arithmetic would read 08 or 09 as bad octal.
is_positive_int() {
    case "$1" in
        '' | *[!0-9]* | 0*) return 1 ;;
        *) return 0 ;;
    esac
}
