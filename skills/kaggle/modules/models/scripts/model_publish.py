#!/usr/bin/env python3
"""Publish a model variation, or a new version of one. A dry run unless --yes is given.

    model_publish.py owner/model/framework/variation ./model --notes "what changed"
    model_publish.py owner/model/framework/variation ./model --notes "what changed" --yes
    model_publish.py owner/model/framework/variation ./model --via cli --yes

By default kagglehub uploads: it creates the model and the variation when
they do not exist (private) and adds a version when they do. --license names
a licence Kaggle lists for models, such as "Apache 2.0".

--via cli uses the Kaggle CLI. A Kaggle model has three levels, and the CLI
creates them one at a time:

  1. the model               model-metadata.json           kaggle models create
  2. a variation of it       model-instance-metadata.json  kaggle models variations create
  3. versions of a variation                               kaggle models variations versions create

The script looks up what exists and runs only the missing steps. Creating a
variation uploads the files as its first version.

Everything in the folder is uploaded, so the folder is checked for credential
files first (exit status 5). Get the user's go-ahead before --yes.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, hub, kaggle_cli, preflight, script  # noqa: E402

DEFAULT_NOTES = "Upload via kagglehub"
MODEL_METADATA = "model-metadata.json"
VARIATION_METADATA = "model-instance-metadata.json"


def publish_with_kagglehub(
    handle: str, folder: str, notes: str = DEFAULT_NOTES, license_name: str | None = None
) -> None:
    """Upload ``folder`` as ``handle``. kagglehub returns nothing on success."""
    kagglehub = hub.load()
    kwargs: dict = {"version_notes": notes}
    if license_name:
        kwargs["license_name"] = license_name
    kagglehub.model_upload(handle=handle, local_model_dir=folder, **kwargs)


def publish_with_cli(handle: str, folder: Path, notes: str) -> int:
    """Create what is missing, in order, and upload the files."""
    model = "/".join(handle.split("/")[:2])
    # `models get` without -p prints the model and exits 0 when it exists. With -p,
    # kaggle 2.2.4 crashes while writing the metadata file of an existing model.
    if kaggle_cli.run(["models", "get", model], timeout=120).returncode == 0:
        print(f"The model {model} exists.")
    else:
        print(f"Creating the model {model}.")
        status = kaggle_cli.run_wrapped(
            ["models", "create", "-p", str(folder)], tool="models.create"
        )
        if status != 0:
            return status

    with tempfile.TemporaryDirectory() as lookup:
        found = kaggle_cli.run(["models", "variations", "get", handle, "-p", lookup], timeout=120)
    # --dir-mode zip uploads subfolders too; the default skips them.
    if found.returncode == 0:
        print("The variation exists; uploading a new version.")
        return kaggle_cli.run_wrapped(
            [
                "models",
                "variations",
                "versions",
                "create",
                handle,
                "-p",
                str(folder),
                f"--version-notes={notes}",
                "--dir-mode",
                "zip",
            ],
            tool="models.versions.create",
        )
    print(f"Creating the variation {handle}; the files become its version 1.")
    return kaggle_cli.run_wrapped(
        ["models", "variations", "create", "-p", str(folder), "--dir-mode", "zip"],
        tool="models.variations.create",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish a model variation, or a new version of one. A dry run unless "
        "--yes is given.",
        epilog="Uploads everything in the folder. New models are private.",
    )
    parser.add_argument("handle", help="owner/model/framework/variation")
    parser.add_argument("dir", help="The folder to upload")
    parser.add_argument("notes_pos", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("license_pos", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--notes", help="Version notes")
    parser.add_argument("--license", dest="license_name", help='With kagglehub: "Apache 2.0"')
    parser.add_argument(
        "--via",
        choices=("kagglehub", "cli"),
        default="kagglehub",
        help="The tool that uploads (default: kagglehub)",
    )
    script.add_yes(parser)
    args = parser.parse_args(argv)
    notes = args.notes or args.notes_pos or DEFAULT_NOTES
    license_name = args.license_name or args.license_pos
    folder = Path(args.dir)

    if not script.is_handle(args.handle, 4):
        parser.error("the handle is owner/model/framework/variation")
    status = preflight.check(folder)
    if status:
        return status

    details = [("model", args.handle), ("folder", preflight.describe(folder))]
    if args.via == "cli":
        for name, init in (
            (MODEL_METADATA, "kaggle models init"),
            (VARIATION_METADATA, "kaggle models variations init"),
        ):
            if not (folder / name).is_file():
                return script.fail(
                    f"{folder / name} is missing. Write a template with: {init} -p {folder}",
                    script.EXIT_USAGE,
                )
        details.append(("with", "the Kaggle CLI and the folder's two metadata files"))
    else:
        details.append(("with", "kagglehub"))
        if license_name:
            details.append(("licence", license_name))
    details.append(("notes", notes))
    details.append(("visibility", "private when new, unless the metadata says otherwise"))

    gate = script.write_gate(
        args.yes,
        action="create the model and the variation if missing, and upload the files",
        details=details,
    )
    if gate is not None:
        return gate

    credentials.load_configured_env_file()
    if credentials.resolve() is None:
        return script.no_credential("publishing a model")
    if args.via == "cli":
        if not kaggle_cli.installed():
            return script.missing_package("kaggle", "--via cli")
        status = publish_with_cli(args.handle, folder, notes)
        if status != 0:
            return status
    else:
        try:
            publish_with_kagglehub(args.handle, str(folder), notes, license_name)
        except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
            return hub.fail("model_upload", exc)
    model = "/".join(args.handle.split("/")[:2])
    print(f"Model uploaded: https://www.kaggle.com/models/{model}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
