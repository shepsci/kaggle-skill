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
4. A dry run before a command that changes the account.

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

# The commands that print one of the lines above. The check is limited to
# them, because a read can legitimately show the same words: a forum post that
# quotes "Kernel push error", or a data file named "Upload unsuccessful.csv".
_ALIASES = {
    "c": "competitions",
    "d": "datasets",
    "k": "kernels",
    "m": "models",
    "i": "instances",
    "variations": "instances",
    "v": "versions",
    "update": "push",
}
WRITE_COMMANDS = frozenset(
    {
        ("kernels", "push"),
        ("datasets", "create"),
        ("datasets", "version"),
        ("competitions", "submit"),
        ("files", "upload"),
        ("models", "create"),
        ("models", "push"),  # `models update`, after alias folding
        ("models", "delete"),
        ("models", "instances", "create"),
        ("models", "instances", "push"),
        ("models", "instances", "delete"),
        ("models", "instances", "versions", "create"),
        ("models", "instances", "versions", "delete"),
    }
)
# Every command that changes the Kaggle account. The runner below asks for
# --yes before it runs one. The words are the CLI's own names; aliases are
# folded first. `datasets metadata` changes the account only with --update.
ACCOUNT_CHANGING = frozenset(
    {
        ("auth", "revoke"),
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
_GROUP_ALIASES = {
    "b": "benchmarks",
    "c": "competitions",
    "d": "datasets",
    "f": "forums",
    "k": "kernels",
    "m": "models",
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


def is_write_command(args: list[str]) -> bool:
    """True for the subcommands that create, upload, submit or delete."""
    words: list[str] = []
    for arg in args:
        if arg.startswith("-") or len(words) == 4:
            break
        # `models v` is "variations" at the second level, "versions" at the third.
        if arg == "v" and len(words) == 1:
            arg = "instances"
        words.append(_ALIASES.get(arg, arg))
    return any(tuple(words[:n]) in WRITE_COMMANDS for n in range(2, len(words) + 1))


def command_words(args: list[str]) -> list[str]:
    """The command part of ``args`` in the CLI's own names: aliases are folded."""
    words: list[str] = []
    for arg in args:
        if arg.startswith("-") or len(words) == 4:
            break
        words.append(arg)
    if not words:
        return words
    words[0] = _GROUP_ALIASES.get(words[0], words[0])
    if len(words) > 1:
        group, second = words[0], words[1]
        if group == "models" and second in ("i", "v", "variations"):
            words[1] = "instances"
        elif group == "benchmarks" and second == "t":
            words[1] = "tasks"
        elif group == "kernels" and second == "update":
            words[1] = "push"
    if len(words) > 2 and words[:2] == ["models", "instances"] and words[2] == "v":
        words[2] = "versions"
    return words


def changes_account(args: list[str]) -> bool:
    """True when ``kaggle <args>`` creates, changes, submits, publishes or deletes."""
    words = command_words(args)
    if any(tuple(words[:n]) in ACCOUNT_CHANGING for n in range(2, len(words) + 1)):
        return True
    return words[:2] == ["datasets", "metadata"] and "--update" in args


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

    Output is captured as text. For a command that writes, a failure the CLI
    reported with exit status 0 is turned into return code 1. A missing
    executable gives return code 127.
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
        and is_write_command(args)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Kaggle CLI with a scrubbed environment and wrapped output.",
        epilog="A command that changes the account is a dry run until --yes comes before the --.",
    )
    parser.add_argument("--tool", default="kaggle", help="Label for the untrusted-content block")
    script.add_yes(parser)
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print stdout unwrapped, for a caller that parses it and never echoes it",
    )
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
        bad = unsafe_kernel_output_names(ns.check_kernel_output)
        if bad is None:
            print(
                "error: could not list the kernel's output files to check their names; "
                "nothing was downloaded",
                file=sys.stderr,
            )
            return 4
        if bad:
            print(
                "error: refusing to download; output file names escape the target folder:",
                file=sys.stderr,
            )
            with untrusted.Block(
                source="kaggle-cli", tool="kernels.files", stream="stderr", file=sys.stderr
            ) as block:
                block.write("\n".join(bad))
            return 5
        return 0

    args = ns.args[1:] if ns.args[:1] == ["--"] else ns.args
    if not args:
        parser.error("no kaggle arguments given")
    if changes_account(args):
        gate = script.write_gate(
            ns.yes,
            action="run a Kaggle CLI command that changes the account",
            details=[("command", " ".join(["kaggle", *args]))],
        )
        if gate is not None:
            return gate
    if not installed():
        return script.missing_package("kaggle", "the Kaggle CLI")

    if ns.raw:
        result = run(args, timeout=ns.timeout)
        sys.stdout.write(result.stdout)
        if result.returncode != 0 and result.stderr.strip():
            with untrusted.Block(
                source="kaggle-cli", tool=ns.tool, stream="stderr", file=sys.stderr
            ) as block:
                block.write(result.stderr)
        return exit_code(result)
    return run_wrapped(args, tool=ns.tool, timeout=ns.timeout)


if __name__ == "__main__":
    sys.exit(main())
