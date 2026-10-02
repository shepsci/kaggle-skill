#!/usr/bin/env python3
"""Run the Kaggle CLI the same way everywhere.

Four things every command in this skill needs:

1. A scrubbed environment. The Kaggle CLI prints full request headers,
   including the bearer token, when ``VERBOSE`` or ``VERBOSE_OUTPUT`` is set,
   and ``KAGGLE_API_ENVIRONMENT`` points it at a non-production host.
2. Honest exit codes. Several write commands print an error and still exit 0
   (``Kernel push error: ...``, ``Dataset creation error: ...``), and a
   missing credential or a denial exits 1 like everything else.
3. Output marked as untrusted, because file names, titles and error text come
   from Kaggle.
4. A dry run before any command not known to be a read, and a refusal
   for the one that prints the token.

The scripts import this module. Run as a file, it runs any ``kaggle`` command
that way; the entry point's ``cli`` command does this::

    python3 shared/kaggle_cli.py --tool cli -- datasets files owner/name
    python3 shared/kaggle_cli.py --yes -- datasets version -p ./data -m notes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import script, untrusted  # noqa: E402

SCRUBBED_ENV_VARS = ("VERBOSE", "VERBOSE_OUTPUT", "KAGGLE_API_ENVIRONMENT")

# Lines the CLI prints when a command failed but the process still exits 0.
FAILURE_RE = re.compile(
    r"^\s*("
    r"Kernel push error"
    r"|Dataset creation error"
    r"|Dataset version creation error"
    r"|Model creation error"
    r"|Model update error"
    r"|Model deletion error"
    r"|Model instance creation error"
    r"|Model instance deletion error"
    r"|Model instance version creation error"
    r"|Model instance version deletion error"
    r"|Could not submit to competition"
    r"|Could not find competition"
    r"|Upload unsuccessful"
    r").*$",
    re.MULTILINE,
)

NOT_FOUND_EXIT = 127

# Every command of the Kaggle CLI, by what it does. Each leaf command of
# kaggle 2.2.4 is in exactly one of the four sets; tests/unit/test_kaggle_cli.py
# checks them against the CLI's own help (tests/fixtures/cli_help_snapshot.json).
#
# Commands that only read, or write files into a folder you name.
READS = frozenset(
    {
        ("benchmarks", "leaderboard"),
        ("benchmarks", "tasks", "download"),
        ("benchmarks", "tasks", "list"),
        ("benchmarks", "tasks", "log"),
        ("benchmarks", "tasks", "models"),
        ("benchmarks", "tasks", "status"),
        ("benchmarks", "topics", "list"),
        ("benchmarks", "topics", "show"),
        ("competitions", "download"),
        ("competitions", "episodes"),
        ("competitions", "files"),
        ("competitions", "hosts"),
        ("competitions", "init"),
        ("competitions", "leaderboard"),
        ("competitions", "list"),
        ("competitions", "logs"),
        ("competitions", "pages", "list"),
        ("competitions", "replay"),
        ("competitions", "settings", "get"),
        ("competitions", "solution", "status"),
        ("competitions", "submission-limits"),
        ("competitions", "submissions"),
        ("competitions", "team-submissions"),
        ("competitions", "topic-messages"),
        ("competitions", "topics", "list"),
        ("competitions", "topics", "show"),
        ("config", "view"),
        ("datasets", "download"),
        ("datasets", "files"),
        ("datasets", "init"),
        ("datasets", "list"),
        ("datasets", "metadata"),  # with --update it changes the account; see kind()
        ("datasets", "status"),
        ("datasets", "topics", "list"),
        ("datasets", "topics", "show"),
        ("forums", "list"),
        ("forums", "topics", "list"),
        ("forums", "topics", "show"),
        ("kernels", "files"),
        ("kernels", "init"),
        ("kernels", "list"),
        ("kernels", "logs"),
        ("kernels", "output"),
        ("kernels", "pull"),
        ("kernels", "status"),
        ("kernels", "topics", "list"),
        ("kernels", "topics", "show"),
        ("models", "get"),
        ("models", "init"),
        ("models", "instances", "files"),
        ("models", "instances", "get"),
        ("models", "instances", "init"),
        ("models", "instances", "list"),
        ("models", "instances", "versions", "download"),
        ("models", "instances", "versions", "files"),
        ("models", "instances", "versions", "list"),
        ("models", "list"),
        ("models", "topics", "list"),
        ("models", "topics", "show"),
        ("quota",),
    }
)
# Commands that change the Kaggle account. `benchmarks auth` and `benchmarks
# init` create a model-proxy token on it.
ACCOUNT_CHANGING = frozenset(
    {
        ("auth", "revoke"),
        ("benchmarks", "auth"),
        ("benchmarks", "init"),
        ("benchmarks", "tasks", "delete"),
        ("benchmarks", "tasks", "publish"),
        ("benchmarks", "tasks", "push"),
        ("benchmarks", "tasks", "run"),
        ("competitions", "create"),
        ("competitions", "data", "update"),
        ("competitions", "launch"),
        ("competitions", "pages", "create"),
        ("competitions", "pages", "delete"),
        ("competitions", "pages", "update"),
        ("competitions", "settings", "update"),
        ("competitions", "solution", "create"),
        ("competitions", "submit"),
        ("datasets", "create"),
        ("datasets", "delete"),
        ("datasets", "version"),
        ("files", "upload"),
        ("kernels", "delete"),
        ("kernels", "push"),
        ("models", "create"),
        ("models", "delete"),
        ("models", "update"),
        ("models", "instances", "create"),
        ("models", "instances", "delete"),
        ("models", "instances", "update"),
        ("models", "instances", "versions", "create"),
        ("models", "instances", "versions", "delete"),
    }
)
# Commands that change this machine's Kaggle settings or stored credential:
# `config set proxy` would send every request, token included, through a proxy.
LOCAL_CHANGING = frozenset({("auth", "login"), ("config", "set"), ("config", "unset")})
# Commands the runner never runs: this one prints the access token.
REFUSED = frozenset({("auth", "print-access-token")})

LEAVES = READS | ACCOUNT_CHANGING | LOCAL_CHANGING | REFUSED
# Every command path, groups included: ("competitions",), ("competitions", "pages"), ...
_PATHS = frozenset(leaf[:n] for leaf in LEAVES for n in range(1, len(leaf) + 1))
# The CLI's other names for commands, as its help lists them.
ALIASES = {
    "b": "benchmarks",
    "benchmarks t": "benchmarks tasks",
    "benchmarks tasks logs": "benchmarks tasks log",
    "c": "competitions",
    "d": "datasets",
    "f": "forums",
    "k": "kernels",
    "kernels get": "kernels pull",
    "kernels update": "kernels push",
    "m": "models",
    "models i": "models instances",
    "models instances v": "models instances versions",
    "models v": "models instances",
    "models variations": "models instances",
}
NEXT_TOKEN_RE = re.compile(r"^Next [Pp]age [Tt]oken\s*[=:]\s*(\S+)\s*$")


def kaggle_bin() -> str:
    """Path of the Kaggle CLI: ``KAGGLE_CLI_BIN``, then ``PATH``."""
    return os.environ.get("KAGGLE_CLI_BIN") or shutil.which("kaggle") or "kaggle"


def installed() -> bool:
    """True when the Kaggle CLI can be found."""
    return shutil.which(os.environ.get("KAGGLE_CLI_BIN") or "kaggle") is not None


def scrubbed_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Copy of the environment without the variables that leak or redirect."""
    env = dict(os.environ if base is None else base)
    for name in SCRUBBED_ENV_VARS:
        env.pop(name, None)
    return env


def scrub_process_env() -> None:
    """Drop the same variables from this process, for in-process library use."""
    for name in SCRUBBED_ENV_VARS:
        os.environ.pop(name, None)


def find_failure(output: str) -> str | None:
    """Return the CLI's failure line if the output reports one."""
    match = FAILURE_RE.search(output or "")
    return match.group(0).strip() if match else None


def command(args: list[str]) -> tuple[str, ...] | None:
    """The command ``kaggle <args>`` runs, in the CLI's own names.

    None when the words alone cannot tell: an option or ``--`` before the
    command is complete, a word the CLI does not list, or a group with no
    subcommand. The CLI accepts options in those places, and a later word
    can still pick the subcommand (``kaggle competitions pages -q delete``).
    """
    path: tuple[str, ...] = ()
    for arg in args:
        if path in LEAVES:
            break
        name = " ".join((*path, arg))
        name = ALIASES.get(name, name)
        if tuple(name.split()) not in _PATHS:
            return None
        path = tuple(name.split())
    return path if path in LEAVES else None


def kind(args: list[str]) -> str:
    """What ``kaggle <args>`` does: ``read``, ``account``, ``local``, ``refused`` or ``unknown``.

    ``account`` changes the Kaggle account and ``local`` this machine's Kaggle
    settings. ``unknown`` is anything :func:`command` cannot name; the runner
    treats it like a change.
    """
    path = command(args)
    if path is None:
        return "unknown"
    if path in REFUSED:
        return "refused"
    if path in ACCOUNT_CHANGING:
        return "account"
    if path in LOCAL_CHANGING:
        return "local"
    # argparse takes any prefix of a long option: --upd is --update.
    if path == ("datasets", "metadata") and any(arg.startswith("--u") for arg in args):
        return "account"
    return "read"


def json_rows(stdout: str) -> tuple[list | None, str | None]:
    """Read a ``--format json`` listing. Returns ``(rows, next page token)``.

    The CLI prints other lines around the JSON: warnings before it and a
    ``Next page token`` line after it. Only the array is parsed. ``rows`` is
    None when the output holds no JSON array.
    """
    token: str | None = None
    body: list[str] = []
    started = False
    for line in stdout.splitlines():
        match = NEXT_TOKEN_RE.match(line.strip())
        if match:
            token = match.group(1)
            continue
        if not started and not line.lstrip().startswith("["):
            continue
        started = True
        body.append(line)
    if not body:
        return None, token
    try:
        rows = json.loads("\n".join(body))
    except ValueError:
        return None, token
    return (rows if isinstance(rows, list) else None), token


def _load_env_file() -> None:
    """Load the file named by KAGGLE_ENV_FILE, so the CLI sees what the checker sees."""
    from shared import credentials  # imported here: credentials imports this module

    credentials.load_configured_env_file()


def run(args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run ``kaggle <args>`` and return the completed process.

    Output is captured as text. For any command but a known read, a failure
    the CLI reported with exit status 0 is turned into return code 1. Reads
    are left alone: a forum post can quote "Kernel push error", and a data
    file can be named "Upload unsuccessful.csv". A missing executable gives
    return code 127.
    """
    _load_env_file()
    cmd = [kaggle_bin(), *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=scrubbed_env(),
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            cmd,
            NOT_FOUND_EXIT,
            "",
            "kaggle executable not found; install kaggle>=2.2.4\n",
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        return subprocess.CompletedProcess(cmd, 124, stdout, f"timed out after {timeout}s\n")
    if (
        result.returncode == 0
        and kind(args) != "read"
        and find_failure(result.stdout + "\n" + result.stderr)
    ):
        result.returncode = 1
    return result


# What the CLI prints when it has no credential, or the server rejects the one it has.
_NO_CREDENTIAL_RE = re.compile(
    r"Authentication required|401 Client Error|Unauthenticated|Could not find kaggle\.json",
    re.IGNORECASE,
)
_DENIED_RE = re.compile(r"403 Client Error|Forbidden|Permission .* denied", re.IGNORECASE)


def exit_code(result: subprocess.CompletedProcess) -> int:
    """The exit code a script should return for a finished CLI call.

    The CLI exits 1 for nearly every failure. This reads its message, so that
    a missing or rejected credential is 2 and a denial is 3, as in SKILL.md.
    """
    if result.returncode in (0, NOT_FOUND_EXIT, 124):
        return result.returncode
    output = f"{result.stdout}\n{result.stderr}"
    if _NO_CREDENTIAL_RE.search(output):
        return 2
    if _DENIED_RE.search(output):
        return 3
    return result.returncode


def run_wrapped(
    args: list[str], *, tool: str, source: str = "kaggle-cli", timeout: float | None = None
) -> int:
    """Run ``kaggle <args>`` and print its output inside untrusted-content blocks."""
    result = run(args, timeout=timeout)
    command = " ".join(["kaggle", *args])
    with untrusted.Block(source=source, tool=tool, command=command) as block:
        if result.stdout:
            block.write(result.stdout)
    if result.stderr.strip():
        with untrusted.Block(source=source, tool=tool, stream="stderr", file=sys.stderr) as block:
            block.write(result.stderr)
    if result.returncode != 0:
        print(f"kaggle exited with status {result.returncode}", file=sys.stderr)
    return exit_code(result)


def print_folder(folder: Path, *, limit: int = 40) -> None:
    """List what is in ``folder``, as untrusted content: Kaggle chose the file names."""
    try:
        files = sorted(p for p in Path(folder).rglob("*") if p.is_file())
    except OSError:
        return
    total = sum(p.stat().st_size for p in files)
    with untrusted.Block(source="local", tool="ls", folder=str(folder)) as block:
        block.write(f"{len(files)} files, {_size(total)} in {folder}:")
        for path in files[:limit]:
            block.write(f"  {_size(path.stat().st_size):>10}  {path.relative_to(folder)}")
        if len(files) > limit:
            block.write(f"  ... and {len(files) - limit} more")


def _size(count: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if count < 1000:
            return f"{count:.0f} {unit}" if unit == "B" else f"{count:.1f} {unit}"
        count /= 1000
    return f"{count:.1f} TB"


def unsafe_kernel_output_names(kernel: str, *, max_pages: int = 20) -> list[str] | None:
    """Output file names of a kernel that would escape the download folder.

    kaggle 2.2.4 and earlier join the server-supplied name to the target path
    without a containment check. Returns the offending names, an empty list
    when all are safe, or None when the listing could not be read in full.
    """
    bad: list[str] = []
    page_token: str | None = None
    for _ in range(max_pages):
        args = ["kernels", "files", kernel, "--format", "json", "--page-size", "200"]
        if page_token:
            args += ["--page-token", page_token]
        result = run(args, timeout=120)
        if result.returncode != 0:
            return None
        rows, page_token = json_rows(result.stdout)
        if rows is None:
            # The CLI prints this line, not an empty array, for a run with no output.
            return bad if "No files found" in result.stdout else None
        for row in rows:
            name = str(row.get("name", "")) if isinstance(row, dict) else ""
            parts = name.replace("\\", "/").split("/")
            if name.startswith(("/", "\\")) or ".." in parts or re.match(r"^[A-Za-z]:", name):
                bad.append(name)
        if not page_token:
            return bad
    # More pages than the limit: the unread names are unknown, so not "safe".
    return bad or None


_GATE_ACTIONS = {
    "account": "run a Kaggle CLI command that changes your Kaggle account",
    "local": "run a Kaggle CLI command that changes this machine's Kaggle settings or credential",
    "unknown": "run a Kaggle CLI command the skill cannot confirm only reads",
}


def _output_kernel(rest: list[str]) -> str | None:
    """The notebook named in the arguments of ``kaggle kernels output``."""
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("kernel", nargs="?")
    for names in (("-p", "--path"), ("--file-pattern",), ("--page-size",), ("--page-token",)):
        parser.add_argument(*names)
    for names in (("-w", "--wp"), ("-o", "--force"), ("-q", "--quiet"), ("-h", "--help")):
        parser.add_argument(*names, action="store_true")
    try:
        found, _ = parser.parse_known_args(rest)
    except (argparse.ArgumentError, SystemExit):
        return None
    return found.kernel


def check_kernel_output(kernel: str | None) -> int:
    """0 when the notebook's output file names stay in the download folder, else 4 or 5."""
    bad = unsafe_kernel_output_names(kernel) if kernel else None
    if bad is None:
        print(
            "error: could not list the notebook's output files to check their names; "
            "nothing was downloaded",
            file=sys.stderr,
        )
        return script.EXIT_UNAVAILABLE
    if bad:
        print(
            "error: refusing to download; output file names escape the target folder:",
            file=sys.stderr,
        )
        with untrusted.Block(
            source="kaggle-cli", tool="kernels.files", stream="stderr", file=sys.stderr
        ) as block:
            block.write("\n".join(bad))
        return script.EXIT_REFUSED
    return script.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Kaggle CLI with a scrubbed environment and wrapped output.",
        epilog="Only a command known to read runs at once. Anything else is a dry run "
        "until --yes comes before the --.",
    )
    parser.add_argument("--tool", default="kaggle", help="Label for the untrusted-content block")
    script.add_yes(parser)
    parser.add_argument("--timeout", type=float, default=None, help="Seconds before giving up")
    parser.add_argument(
        "--check-kernel-output",
        metavar="OWNER/KERNEL",
        help="Exit 5 if the kernel's output file names would escape the download folder, "
        "4 if they cannot be listed",
    )
    parser.add_argument(
        "args", nargs=argparse.REMAINDER, help="-- followed by the kaggle arguments"
    )
    ns = parser.parse_args(argv)

    if ns.check_kernel_output:
        return check_kernel_output(ns.check_kernel_output)

    args = ns.args[1:] if ns.args[:1] == ["--"] else ns.args
    if not args:
        parser.error("no kaggle arguments given")
    what = kind(args)
    if what == "refused":
        return script.fail(
            "the skill never runs `kaggle auth print-access-token`: it prints your token. "
            "`doctor` checks the credential without showing it.",
            script.EXIT_REFUSED,
        )
    if what != "read":
        details = [("command", " ".join(["kaggle", *args]))]
        if what == "unknown":
            details.append(
                (
                    "why",
                    "an option or a word before the command is complete; "
                    "put options after the command words",
                )
            )
        gate = script.write_gate(ns.yes, action=_GATE_ACTIONS[what], details=details)
        if gate is not None:
            return gate
    if not installed():
        return script.missing_package("kaggle", "the Kaggle CLI")
    if command(args) == ("kernels", "output"):
        code = check_kernel_output(_output_kernel(args[2:]))
        if code:
            return code
    return run_wrapped(args, tool=ns.tool, timeout=ns.timeout)


if __name__ == "__main__":
    sys.exit(main())
