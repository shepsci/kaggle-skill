"""Shared setup for the scripts that call kagglehub.

kagglehub is a library, so the checks the shell wrappers get from
``kaggle_cli.py`` are done here: the environment is cleaned, the library's
log lines (which carry file names from the server) are switched off, an
output folder is never emptied by accident, and a failure is reported without
a traceback.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import credentials, kaggle_cli, script, untrusted  # noqa: E402

EXIT_FAILED = script.EXIT_FAILED
EXIT_REFUSED = script.EXIT_REFUSED


def load() -> Any:
    """Import kagglehub with a clean environment.

    Exits with status 127 and the install command when it is not installed.
    """
    credentials.load_configured_env_file()
    kaggle_cli.scrub_process_env()
    # At its default level kagglehub logs "Downloading to <path>" on standard
    # output, with file names chosen by the uploader.
    os.environ.setdefault("KAGGLEHUB_VERBOSITY", "error")
    try:
        import kagglehub  # type: ignore
    except ModuleNotFoundError:
        script.missing_package("kagglehub", "this command; or add --via cli to use the Kaggle CLI")
        raise SystemExit(script.EXIT_NOT_INSTALLED) from None
    return kagglehub


def check_output_dir(output_dir: str | None, path: str | None, force: bool) -> int:
    """Refuse a download that would delete files in ``output_dir``.

    kagglehub empties a non-empty output folder when it is asked to download
    again, so ``--output-dir . --force`` would wipe the working directory.
    Returns 0 when the download may go ahead.
    """
    if not output_dir:
        return 0
    target = Path(output_dir)
    if target.is_file():
        print("error: --output-dir points to a file, not a folder", file=sys.stderr)
        return 2
    if path:
        # One file: kagglehub replaces only that file, and only with --force.
        if (target / path).exists() and not force:
            print(
                "error: that file is already in --output-dir; pass --force to replace it",
                file=sys.stderr,
            )
            return EXIT_FAILED
        return 0
    if target.is_dir() and any(target.iterdir()):
        print(
            "error: --output-dir is not empty. kagglehub would delete what is in it, so the\n"
            "       download was not started. Choose a new or empty folder.",
            file=sys.stderr,
        )
        return EXIT_REFUSED
    return 0


def fail(action: str, exc: BaseException) -> int:
    """Report a kagglehub failure. The message can quote the server, so it is wrapped."""
    print(f"error: {action} failed ({type(exc).__name__})", file=sys.stderr)
    untrusted.emit_text(
        str(exc) or "(no message)", source="kagglehub", tool=action, file=sys.stderr
    )
    return EXIT_FAILED
