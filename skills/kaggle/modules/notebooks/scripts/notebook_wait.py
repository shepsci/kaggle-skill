#!/usr/bin/env python3
"""Wait for a Kaggle notebook run to finish, then download its output.

    notebook_wait.py owner/notebook
    notebook_wait.py owner/notebook --out ./output --timeout 7200 --interval 60

Checks the run every --interval seconds for at most --timeout seconds. When
the run completes, its output goes to --out (default
./downloads/<notebook>-output) after the file names are checked. When the run
fails, the end of its log is printed. It only reads.

Exit status: 0 output downloaded, 1 the run failed or was cancelled, 4 the
status or the output listing could not be read, 5 refused because an output
file name would escape the folder, 124 still running at the timeout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli, notebook, script  # noqa: E402

DEFAULT_TIMEOUT = 3600
DEFAULT_INTERVAL = 30
LOG_LINES = 40


def add_wait_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--out", metavar="DIR", help="Where the output goes (default: ./downloads/<name>-output)"
    )
    parser.add_argument(
        "--timeout",
        type=script.positive_int,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"Longest wait (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--interval",
        type=script.positive_int,
        default=DEFAULT_INTERVAL,
        metavar="SECONDS",
        help=f"Time between checks (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--no-output", action="store_true", help="Wait only; do not download the output"
    )


def wait_and_fetch(slug: str, args: argparse.Namespace) -> int:
    """Wait for the run, then download its output or print the end of its log."""
    print(f"Waiting for {slug}: a check every {args.interval}s, for up to {args.timeout}s.")
    outcome = notebook.wait(slug, args.interval, args.timeout)
    if outcome == script.EXIT_FAILED:
        print("The run failed or was cancelled.", file=sys.stderr)
        notebook.print_log_tail(slug, LOG_LINES)
        return outcome
    if outcome == script.EXIT_TIMEOUT:
        print(
            f"Still running after {args.timeout}s. Keep waiting with: notebook_wait.py {slug}",
            file=sys.stderr,
        )
        return outcome
    if outcome != script.EXIT_OK:
        print("The run's status could not be read.", file=sys.stderr)
        return outcome
    if args.no_output:
        print("The run is complete.")
        return script.EXIT_OK

    target = Path(args.out or Path("downloads") / f"{slug.split('/')[-1]}-output")
    print(f"The run is complete. Downloading its output to {target}.")
    status = notebook.download_output(slug, target)
    if status != 0:
        return status
    kaggle_cli.print_folder(target)
    return script.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wait for a Kaggle notebook run to finish, then download its output.",
        epilog="Needs the Kaggle CLI and a credential. It only reads.",
    )
    parser.add_argument("notebook", help="owner/name")
    add_wait_arguments(parser)
    args = parser.parse_args(argv)
    if not script.is_handle(args.notebook, 2):
        parser.error("the notebook is owner/name")

    credentials.load_configured_env_file()
    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "watching a notebook run")
    if credentials.resolve() is None:
        return script.no_credential("watching a notebook run")
    return wait_and_fetch(args.notebook, args)


if __name__ == "__main__":
    sys.exit(main())
