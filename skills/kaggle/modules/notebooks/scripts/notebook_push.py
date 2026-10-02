#!/usr/bin/env python3
"""Push a notebook to Kaggle, which also runs it. A dry run unless --yes is given.

    notebook_push.py ./notebook-dir          dry run: what would be pushed
    notebook_push.py ./notebook-dir --yes    push

The folder holds the notebook and its kernel-metadata.json. Pushing creates a
new version and starts a run on Kaggle: with an accelerator switched on, that
run uses the account's weekly GPU hours. Get the user's go-ahead before --yes.

Everything in the folder is uploaded, so the folder is checked for credential
files first (exit status 5). To wait for the run and fetch its output, use
notebook_run.py or notebook_wait.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli, notebook, preflight, script  # noqa: E402


def plan(folder: Path) -> tuple[str, list[tuple[str, str]], str] | int:
    """What a push of ``folder`` would do: ``(notebook id, details, cost)``, or an exit code."""
    metadata = notebook.read_metadata(folder)
    if metadata is None:
        return script.fail(
            f"{folder / notebook.METADATA_FILE} is missing or unreadable. Write a template "
            f"with: kaggle kernels init -p {folder}",
            script.EXIT_USAGE,
        )
    slug = str(metadata.get("id") or "")
    if not script.is_handle(slug, 2):
        return script.fail(
            f"the id in {notebook.METADATA_FILE} is not owner/name", script.EXIT_USAGE
        )
    status = preflight.check(folder)
    if status:
        return status

    def flag(name: str, default: bool) -> bool:
        value = metadata.get(name, default)
        return value if isinstance(value, bool) else str(value).lower() == "true"

    gpu = flag("enable_gpu", False)
    sources = metadata.get("competition_sources") or []
    details = [
        ("notebook", slug),
        ("folder", preflight.describe(folder)),
        ("code file", str(metadata.get("code_file") or "(not set)")),
        ("visibility", "private" if flag("is_private", True) else "PUBLIC"),
        ("accelerator", "GPU" if gpu else "none"),
        ("internet", "on" if flag("enable_internet", True) else "off"),
    ]
    if sources:
        details.append(("competition", ", ".join(str(s) for s in sources)))
    cost = "starts a run on Kaggle" + ("; uses the weekly GPU hours" if gpu else "")
    return slug, details, cost


def push(folder: Path) -> int:
    """Run ``kaggle kernels push``. The caller has confirmed."""
    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "pushing a notebook")
    if credentials.resolve() is None:
        return script.no_credential("pushing a notebook")
    return kaggle_cli.run_wrapped(["kernels", "push", "-p", str(folder)], tool="kernels.push")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Push a notebook to Kaggle, which also runs it. A dry run unless --yes "
        "is given.",
        epilog="Starts a run on Kaggle. Needs the Kaggle CLI and a credential.",
    )
    parser.add_argument("dir", help="Folder with the notebook and its kernel-metadata.json")
    script.add_yes(parser)
    args = parser.parse_args(argv)
    folder = Path(args.dir)

    planned = plan(folder)
    if isinstance(planned, int):
        return planned
    slug, details, cost = planned
    gate = script.write_gate(
        args.yes, action="push a notebook version and run it", details=details, cost=cost
    )
    if gate is not None:
        return gate

    credentials.load_configured_env_file()
    status = push(folder)
    if status != 0:
        return status
    print(f"Pushed {slug}. It is running on Kaggle; wait for it with notebook_wait.py {slug}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
