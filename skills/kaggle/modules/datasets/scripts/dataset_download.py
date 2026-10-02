#!/usr/bin/env python3
"""Download a Kaggle dataset.

    dataset_download.py owner/name                     into the kagglehub cache
    dataset_download.py owner/name ./data              into a new or empty folder
    dataset_download.py owner/name --file train.csv
    dataset_download.py owner/name ./data --via cli    with the Kaggle CLI

By default kagglehub does the download: a public dataset needs no credential,
the files are cached under ~/.cache/kagglehub, and a version can be named as
owner/name/versions/3. The folder you give must be new or empty, because
kagglehub deletes what is in a folder before it downloads into it.

--via cli uses the Kaggle CLI, which needs a credential, downloads into
./downloads/<owner>-<name> unless a folder is given, and unpacks the archive.

Exit status: 0 downloaded, 1 the download failed, 2 wrong arguments or no
credential, 5 refused because the folder is not empty, 127 the tool is not
installed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, hub, kaggle_cli, script  # noqa: E402


def download_with_kagglehub(
    handle: str, file: str | None = None, folder: str | None = None, force: bool = False
) -> str:
    """Download a dataset, or one file of it. Returns the local path."""
    kagglehub = hub.load()
    kwargs: dict = {"force_download": force}
    if file:
        kwargs["path"] = file
    if folder:
        kwargs["output_dir"] = folder
    return kagglehub.dataset_download(handle, **kwargs)


def download_with_cli(
    handle: str, file: str | None, folder: str | None, force: bool = False
) -> int:
    if not script.is_handle(handle, 2):
        return script.fail(
            "with --via cli the dataset is owner/name: letters, digits, '.', '_' and '-'",
            script.EXIT_USAGE,
        )
    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "--via cli")
    if credentials.resolve() is None:
        return script.no_credential("the Kaggle CLI")
    target = Path(folder or Path("downloads") / handle.replace("/", "-"))
    target.mkdir(parents=True, exist_ok=True)
    cli_args = ["datasets", "download", handle, "--path", str(target), "--unzip", "--quiet"]
    if file:
        cli_args += ["--file", file]
    if force:
        cli_args.append("--force")
    status = kaggle_cli.run_wrapped(cli_args, tool="datasets.download")
    if status != 0:
        return status
    kaggle_cli.print_folder(target)
    return script.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download a Kaggle dataset.",
        epilog="A public dataset needs no credential with kagglehub, the default.",
    )
    parser.add_argument("handle", help="owner/name, or owner/name/versions/N with kagglehub")
    parser.add_argument("dir", nargs="?", help="Folder to download into")
    parser.add_argument("--output-dir", dest="dir_opt", help=argparse.SUPPRESS)
    parser.add_argument("--file", "--path", dest="file", metavar="NAME", help="Only this file")
    parser.add_argument("--force", action="store_true", help="Download again even if cached")
    parser.add_argument(
        "--via",
        choices=("kagglehub", "cli"),
        default="kagglehub",
        help="The tool that downloads (default: kagglehub)",
    )
    args = script.parse(parser, argv)
    folder = args.dir or args.dir_opt

    credentials.load_configured_env_file()
    if args.via == "cli":
        return download_with_cli(args.handle, args.file, folder, args.force)

    status = hub.check_output_dir(folder, args.file, args.force)
    if status:
        return status
    try:
        local_path = download_with_kagglehub(args.handle, args.file, folder, args.force)
    except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
        return hub.fail("dataset_download", exc)
    print(f"Dataset downloaded to: {local_path}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
