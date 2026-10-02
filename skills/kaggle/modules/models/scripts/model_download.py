#!/usr/bin/env python3
"""Download a Kaggle model.

    model_download.py owner/model/framework/variation            the latest version
    model_download.py owner/model/framework/variation/3 ./model
    model_download.py owner/model/framework/variation/3 --via cli

By default kagglehub does the download: the four-part handle fetches the
latest version, a fifth part names one, and the files are cached under
~/.cache/kagglehub. The folder you give must be new or empty, because
kagglehub deletes what is in a folder before it downloads into it.

--via cli uses the Kaggle CLI. It needs a credential and the version number as
the fifth part, and it leaves the archive as downloaded (.tar.gz): kaggle
2.2.4 extracts tar files without a path check. List the versions with
`kaggle models variations versions list owner/model/framework/variation`.

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
    """Download a model, or one file of it. Returns the local path."""
    kagglehub = hub.load()
    kwargs: dict = {"force_download": force}
    if file:
        kwargs["path"] = file
    if folder:
        kwargs["output_dir"] = folder
    return kagglehub.model_download(handle, **kwargs)


def download_with_cli(handle: str, folder: str | None, force: bool = False) -> int:
    if script.is_handle(handle, 4):
        return script.fail(
            "with --via cli the handle needs a version: owner/model/framework/variation/3. "
            "Without --via cli the latest version is downloaded",
            script.EXIT_USAGE,
        )
    if not script.is_handle(handle, 5) or not handle.rsplit("/", 1)[-1].isdigit():
        return script.fail(
            "the handle is owner/model/framework/variation/version", script.EXIT_USAGE
        )
    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "--via cli")
    if credentials.resolve() is None:
        return script.no_credential("the Kaggle CLI")
    target = Path(folder or Path("downloads") / handle.replace("/", "-"))
    target.mkdir(parents=True, exist_ok=True)
    cli_args = ["models", "variations", "versions", "download", handle, "--path", str(target)]
    cli_args += ["--quiet", *(["--force"] if force else [])]
    status = kaggle_cli.run_wrapped(cli_args, tool="models.download")
    if status != 0:
        return status
    kaggle_cli.print_folder(target)
    return script.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download a Kaggle model.",
        epilog="A public model needs no credential with kagglehub, the default.",
    )
    parser.add_argument("handle", help="owner/model/framework/variation, optionally /version")
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
        if args.file:
            return script.fail(
                "--file works with kagglehub only; the CLI downloads the whole version",
                script.EXIT_USAGE,
            )
        return download_with_cli(args.handle, folder, args.force)

    status = hub.check_output_dir(folder, args.file, args.force)
    if status:
        return status
    try:
        local_path = download_with_kagglehub(args.handle, args.file, folder, args.force)
    except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
        return hub.fail("model_download", exc)
    print(f"Model downloaded to: {local_path}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
