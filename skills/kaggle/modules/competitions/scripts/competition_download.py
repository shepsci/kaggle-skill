#!/usr/bin/env python3
"""Download the data of a Kaggle competition.

    competition_download.py titanic                    into ./downloads/titanic
    competition_download.py titanic ./data --unzip
    competition_download.py titanic --file train.csv

Uses the Kaggle CLI, so it needs the CLI and a credential, and the
competition's rules must have been accepted on kaggle.com: there is no command
for that.

Before a full download the total size is read from Kaggle. Data above
--max-gb (default 20) is not downloaded: some competitions hold hundreds of
gigabytes. Fetch single files with --file, or raise the limit on purpose.

--unzip extracts the archives with a path check (the CLI has no --unzip for
competition downloads). File names come from the host, so the listing is
printed as untrusted content.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import (  # noqa: E402
    competition,
    credentials,
    kaggle_cli,
    mcp_client,
    safe_extract,
    script,
    text,
    untrusted,
)

DEFAULT_MAX_GB = 20.0


def data_size(slug: str) -> tuple[int, int] | None:
    """``(files, bytes)`` of the competition's data, or None when Kaggle does not say."""
    result = mcp_client.request(
        "get_competition_data_files_summary", {"competitionName": slug}, token=""
    )
    info = result.data.get("file_summary_info") if isinstance(result.data, dict) else None
    if not result.ok or not isinstance(info, dict):
        return None
    try:
        total = sum(int(t.get("total_size") or 0) for t in info.get("file_types") or [])
        return int(info.get("total_file_count") or 0), total
    except (TypeError, ValueError, AttributeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download the data of a Kaggle competition.",
        epilog="Needs the Kaggle CLI, a credential, and the competition's rules accepted.",
    )
    script.add_competition(parser, "dir?")
    parser.add_argument("--file", metavar="NAME", help="Download only this file")
    parser.add_argument(
        "--unzip", action="store_true", help="Extract downloaded archives, with a path check"
    )
    parser.add_argument(
        "--max-gb",
        type=float,
        default=DEFAULT_MAX_GB,
        metavar="N",
        help=f"Refuse a full download above N gigabytes (default: {DEFAULT_MAX_GB:g})",
    )
    args = parser.parse_args(argv)
    slug, folder = script.positionals(parser, args, "dir?")
    target = Path(folder or Path("downloads") / slug)

    credentials.load_configured_env_file()
    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "downloading competition data")
    if credentials.resolve() is None:
        return script.no_credential("downloading competition data")

    if not args.file:
        size = data_size(slug)
        if size is None:
            script.warn("Kaggle did not report the size of the data; downloading without a check")
        else:
            files, total = size
            print(f"The data of {slug}: {files:,} files, {text.human_size(total)}.")
            if total > args.max_gb * 1e9:
                print(
                    f"error: that is above the {args.max_gb:g} GB limit, so nothing was "
                    "downloaded.\n"
                    "       Download one file with --file NAME, or raise the limit with "
                    f"--max-gb {total / 1e9 + 1:.0f}.",
                    file=sys.stderr,
                )
                return script.EXIT_REFUSED

    target.mkdir(parents=True, exist_ok=True)
    cli_args = ["competitions", "download", slug, "--path", str(target), "--quiet"]
    if args.file:
        cli_args += ["--file", args.file]
    status = kaggle_cli.run_wrapped(cli_args, tool="competitions.download")
    if status != 0:
        if status == script.EXIT_DENIED:
            print(
                f"Kaggle refused. Accept the rules first: {competition.url(slug)}/rules",
                file=sys.stderr,
            )
        return status

    if args.unzip:
        for archive in sorted(target.glob("*.zip")):
            try:
                names = safe_extract.safe_extract(archive, target)
            except safe_extract.UnsafeArchiveError as exc:
                print(f"error: refusing to extract: {exc.reason}:", file=sys.stderr)
                untrusted.emit_text(
                    exc.member, source="local", tool="safe_extract", file=sys.stderr
                )
                return script.EXIT_REFUSED
            except (zipfile.BadZipFile, OSError) as exc:
                return script.fail(f"could not extract an archive ({type(exc).__name__})")
            print(f"Extracted {len(names)} file(s) from {archive.name}.")

    kaggle_cli.print_folder(target)
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
