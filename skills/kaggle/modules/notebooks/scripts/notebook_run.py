#!/usr/bin/env python3
"""Push a notebook, wait for its run, and download the output. A dry run unless --yes.

    notebook_run.py ./notebook-dir                       dry run
    notebook_run.py ./notebook-dir --yes
    notebook_run.py ./notebook-dir --out ./output --timeout 7200 --yes

The notebook's name is read from the folder's kernel-metadata.json, so the
run that is watched is the one that was pushed. Pushing starts a run on
Kaggle; with an accelerator switched on it uses the weekly GPU hours. Get the
user's go-ahead before --yes.

When the run fails, the end of its log is printed. When it is still running
at the timeout, keep waiting with the notebook-wait command.

Exit status: 0 output downloaded, 1 the push or the run failed, 2 wrong
arguments or no credential, 4 the status or the output listing could not be
read, 5 refused (a code file outside the folder or named like a credential
file, or an output file name that would escape the output folder), 124 still
running at the timeout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import notebook_push  # noqa: E402
import notebook_wait  # noqa: E402

from shared import credentials, script  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Push a notebook, wait for its run, and download the output. A dry run "
        "unless --yes.",
        epilog="Starts a run on Kaggle. Needs the Kaggle CLI and a credential.",
    )
    parser.add_argument("dir", help="Folder with the notebook and its kernel-metadata.json")
    # The older form named the notebook as well. It must be the one in the metadata.
    parser.add_argument("notebook", nargs="?", help=argparse.SUPPRESS)
    notebook_wait.add_wait_arguments(parser)
    script.add_yes(parser)
    args = parser.parse_args(argv)
    folder = Path(args.dir)

    planned = notebook_push.plan(folder)
    if isinstance(planned, int):
        return planned
    slug, details, cost = planned
    if args.notebook and args.notebook != slug:
        return script.fail(
            "the notebook you named is not the one in kernel-metadata.json; the id there "
            "decides what is pushed",
            script.EXIT_USAGE,
        )
    details.append(("then", f"wait up to {args.timeout}s and download the output"))
    gate = script.write_gate(
        args.yes, action="push a notebook version and run it", details=details, cost=cost
    )
    if gate is not None:
        return gate

    credentials.load_configured_env_file()
    status = notebook_push.push(folder)
    if status != 0:
        return status
    return notebook_wait.wait_and_fetch(slug, args)


if __name__ == "__main__":
    sys.exit(main())
