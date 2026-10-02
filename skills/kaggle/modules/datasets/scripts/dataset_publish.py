#!/usr/bin/env python3
"""Publish a dataset, or a new version of one. A dry run unless --yes is given.

    dataset_publish.py owner/name ./data --notes "what changed"          dry run
    dataset_publish.py owner/name ./data --notes "what changed" --yes    upload
    dataset_publish.py owner/name ./data --via cli --yes                 with the Kaggle CLI

By default kagglehub uploads: it creates the dataset when it does not exist
(private) and adds a version when it does.

--via cli uses the Kaggle CLI and the folder's dataset-metadata.json, which
gives control over the title, the licence and the visibility. Without --notes
it creates the dataset; with --notes it adds a version to an existing one. The
`id` in the metadata must be the dataset you name.

Everything in the folder is uploaded, so the folder is checked for credential
files first (exit status 5). Get the user's go-ahead before --yes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, hub, kaggle_cli, preflight, script  # noqa: E402

METADATA_FILE = "dataset-metadata.json"
DEFAULT_NOTES = "Upload via kagglehub"


def publish_with_kagglehub(handle: str, folder: str, notes: str = DEFAULT_NOTES) -> None:
    """Upload ``folder`` as ``handle``. kagglehub returns nothing on success."""
    kagglehub = hub.load()
    kagglehub.dataset_upload(handle=handle, local_dataset_dir=folder, version_notes=notes)


def metadata_id(folder: Path) -> str | None:
    """The ``id`` in the folder's dataset-metadata.json, or None."""
    try:
        data = json.loads((folder / METADATA_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return str(data.get("id") or "") if isinstance(data, dict) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish a dataset, or a new version of one. A dry run unless --yes is given.",
        epilog="Uploads everything in the folder. New datasets are private.",
    )
    parser.add_argument("handle", help="The dataset: owner/name")
    parser.add_argument("dir", help="The folder to upload")
    parser.add_argument("notes_pos", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--notes", help="Version notes")
    parser.add_argument(
        "--via",
        choices=("kagglehub", "cli"),
        default="kagglehub",
        help="The tool that uploads (default: kagglehub)",
    )
    script.add_yes(parser)
    args = script.parse(parser, argv)
    notes = args.notes or args.notes_pos
    folder = Path(args.dir)

    if not script.is_handle(args.handle, 2):
        parser.error("the dataset is owner/name: letters, digits, '.', '_' and '-'")
    status = preflight.check(folder)
    if status:
        return status

    details = [("dataset", args.handle), ("folder", preflight.describe(folder))]
    if args.via == "cli":
        found = metadata_id(folder)
        if found is None:
            return script.fail(
                f"{folder / METADATA_FILE} is missing or unreadable. Write a template with: "
                f"kaggle datasets init -p {folder}",
                script.EXIT_USAGE,
            )
        if found != args.handle:
            return script.fail(
                f"{METADATA_FILE} names another dataset than the one you gave; fix its id",
                script.EXIT_USAGE,
            )
        action = "add a dataset version" if notes else "create a dataset"
        details.append(("with", f"the Kaggle CLI and {METADATA_FILE}"))
    else:
        action = "create the dataset, or add a version if it exists"
        details.append(("with", "kagglehub"))
    details.append(("notes", notes or ("(none)" if args.via == "cli" else DEFAULT_NOTES)))
    details.append(("visibility", "private when new, unless the metadata says otherwise"))

    gate = script.write_gate(args.yes, action=action, details=details)
    if gate is not None:
        return gate

    credentials.load_configured_env_file()
    if credentials.resolve() is None:
        return script.no_credential("publishing a dataset")
    if args.via == "kagglehub" and not credentials.kagglehub_ready():
        return script.fail(
            "kagglehub does not use an OAuth login. Add --via cli, or create an API "
            'token with "Generate New Token" at https://www.kaggle.com/settings',
            script.EXIT_NO_CREDENTIAL,
        )
    if args.via == "cli":
        if not kaggle_cli.installed():
            return script.missing_package("kaggle", "--via cli")
        # --message=VALUE keeps notes that start with "-" from being read as an option.
        # --dir-mode zip uploads subfolders too; the default skips them.
        if notes:
            cli_args = ["datasets", "version", "-p", str(folder), f"--message={notes}"]
        else:
            cli_args = ["datasets", "create", "-p", str(folder)]
        status = kaggle_cli.run_wrapped(
            [*cli_args, "--dir-mode", "zip"], tool="datasets." + cli_args[1]
        )
        if status != 0:
            return status
    else:
        try:
            publish_with_kagglehub(args.handle, str(folder), notes or DEFAULT_NOTES)
        except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
            return hub.fail("dataset_upload", exc)
    print(f"Dataset uploaded: https://www.kaggle.com/datasets/{args.handle}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
