"""Kaggle notebook runs: the status, the wait, the output and the log.

Everything goes through ``shared/kaggle_cli.py``, so the environment is
cleaned and Kaggle's text is printed as untrusted content.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

from shared import kaggle_cli, script, untrusted

METADATA_FILE = "kernel-metadata.json"
_STATUS_RE = re.compile(r'has status "([A-Za-z_.]*)"')
FAILED_STATES = frozenset({"ERROR", "CANCEL_REQUESTED", "CANCEL_ACKNOWLEDGED"})
MAX_FAILED_CHECKS = 5


def read_metadata(folder: Path) -> dict | None:
    """The folder's ``kernel-metadata.json``, or None when it is missing or unreadable."""
    try:
        data = json.loads((folder / METADATA_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def status(slug: str) -> str | None:
    """The run's state as one upper-case word, ``""`` when the CLI's answer has
    none, or None when the status call failed."""
    result = kaggle_cli.run(["kernels", "status", slug], timeout=120)
    if result.returncode != 0:
        return None
    found = _STATUS_RE.findall(result.stdout)
    # The CLI prints `KernelWorkerStatus.COMPLETE` in some versions.
    return found[-1].rsplit(".", 1)[-1].upper() if found else ""


def wait(
    slug: str,
    interval: int = 30,
    max_wait: int = 3600,
    *,
    sleep: Callable[[float], None] | None = None,
) -> int:
    """Wait for a run to finish.

    Returns 0 complete, 1 failed or cancelled, 124 still running after
    ``max_wait`` seconds, 4 the status could not be read five times in a row.
    """
    elapsed = 0
    failures = 0
    while True:
        state = status(slug)
        stamp = time.strftime("%H:%M:%S")
        if state is None:
            failures += 1
            print(f"[{stamp}] status check failed ({failures} in a row)", file=sys.stderr)
            if failures >= MAX_FAILED_CHECKS:
                return script.EXIT_UNAVAILABLE
        else:
            failures = 0
            print(f"[{stamp}] status: {state or 'UNKNOWN'}")
            if state == "COMPLETE":
                return script.EXIT_OK
            if state in FAILED_STATES:
                return script.EXIT_FAILED
        if elapsed >= max_wait:
            return script.EXIT_TIMEOUT
        (sleep or time.sleep)(interval)
        elapsed += interval


def download_output(slug: str, folder: Path) -> int:
    """Download a run's output after checking its file names.

    Returns 5 when a name would escape ``folder`` and 4 when the names cannot
    be listed. Nothing is downloaded in either case.
    """
    bad = kaggle_cli.unsafe_kernel_output_names(slug)
    if bad is None:
        return script.fail(
            "could not list the notebook's output files to check their names; "
            "nothing was downloaded",
            script.EXIT_UNAVAILABLE,
        )
    if bad:
        print(
            "error: refusing to download; output file names escape the target folder:",
            file=sys.stderr,
        )
        untrusted.emit_text(
            "\n".join(bad),
            source="kaggle-cli",
            tool="kernels.files",
            stream="stderr",
            file=sys.stderr,
        )
        return script.EXIT_REFUSED
    folder.mkdir(parents=True, exist_ok=True)
    return kaggle_cli.run_wrapped(
        ["kernels", "output", slug, "--path", str(folder), "--quiet"], tool="kernels.output"
    )


def print_log_tail(slug: str, lines: int = 40) -> None:
    """Print the end of a run's log on standard error. A notebook log can be very long."""
    result = kaggle_cli.run(["kernels", "logs", slug], timeout=300)
    log = (result.stdout or result.stderr).strip()
    if not log:
        print("The log is empty or could not be read.", file=sys.stderr)
        return
    rows = log.splitlines()
    shown = rows[-lines:]
    print(f"The last {len(shown)} of {len(rows)} log lines:", file=sys.stderr)
    untrusted.emit_text("\n".join(shown), source="kaggle-cli", tool="kernels.logs", file=sys.stderr)
