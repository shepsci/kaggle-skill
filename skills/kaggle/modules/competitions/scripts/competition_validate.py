#!/usr/bin/env python3
"""Check a submission file against the sample submission, before it uses a slot.

    competition_validate.py titanic ./submission.csv
    competition_validate.py titanic ./submission.csv --sample ./data/sample_submission.csv

Checks the shape of a CSV submission: the columns and their order, the number
of rows, the ids in the first column (missing, extra, duplicated), empty
values, and values that are not finite numbers in a column that is numeric in
the sample. An empty value fails in a numeric column; in a text column that
is never empty in the sample it is a warning, because some competitions take
an empty prediction. It says nothing about how good the predictions are, and
it cannot check a format rule that only the evaluation page states.

The sample is the file given with --sample. Without it the script looks for a
file named like sample_submission next to the submission and in ./data,
./input and ./downloads/<competition>, and then downloads it from Kaggle,
which needs the Kaggle CLI, a credential and the accepted rules. In a data
folder, and in Kaggle's file list, the only CSV with "submission" in its name
also counts: Titanic's sample is gender_submission.csv.

Exit status: 0 every check passed (warnings allowed), 1 a check failed, 2 the
file is missing or is not a CSV, 4 no sample submission could be found.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import (  # noqa: E402
    credentials,
    kaggle_cli,
    mcp_client,
    safe_extract,
    script,
    untrusted,
)

SAMPLE_NAME_RE = re.compile(r"sample.*submission|submission.*sample", re.IGNORECASE)
MAX_EXAMPLES = 3
MAX_LISTING_PAGES = 50  # 200 file names a page
# Prediction strings can be far longer than the csv module's default field limit.
csv.field_size_limit(2**31 - 1)


def pick_sample(names: list[str], *, loose: bool) -> str | None:
    """The sample submission among file names, or None.

    A name like sample_submission.csv wins. With ``loose``, for a folder of
    downloaded data or Kaggle's file list, the only CSV with "submission" in
    its name counts too. Not next to the submission: your own earlier
    submissions sit there.
    """
    csvs = [name for name in names if name.lower().endswith(".csv")]
    named = [name for name in csvs if SAMPLE_NAME_RE.search(Path(name).name)]
    if named:
        return min(named, key=len)
    loose_named = [name for name in csvs if "submission" in Path(name).name.lower()]
    return loose_named[0] if loose and len(loose_named) == 1 else None


def find_local_sample(slug: str, submission: Path) -> Path | None:
    """A sample submission in the usual places, or None."""
    folders = [
        (submission.parent, False),
        (Path("."), False),
        (Path("data"), True),
        (Path("input"), True),
        (Path("downloads") / slug, True),
        (Path(slug), True),
    ]
    own = submission.parent.resolve()
    for folder, loose in folders:
        try:
            names = sorted(
                p.name
                for p in folder.iterdir()
                if p.is_file() and p.resolve() != submission.resolve()
            )
        except OSError:
            continue
        # The submission's own folder holds earlier submissions, even when it is ./data.
        found = pick_sample(names, loose=loose and folder.resolve() != own)
        if found:
            return folder / found
    return None


def download_sample(slug: str, folder: Path) -> tuple[Path | None, str]:
    """Fetch the sample submission from Kaggle. Returns ``(path, why not)``."""
    token = mcp_client.resolve_token()
    if not token:
        return None, "no credential to list the competition's files with"
    names: list[str] = []
    request = {"competitionName": slug, "pageSize": 200}
    for _ in range(MAX_LISTING_PAGES):
        listing = mcp_client.request("list_competition_data_files", request, token=token)
        if not listing.ok or not isinstance(listing.data, dict):
            return None, "the competition's file list could not be read (are the rules accepted?)"
        files = listing.data.get("files") or []
        names += [str(f.get("name", "")) for f in files if isinstance(f, dict)]
        page_token = listing.data.get("next_page_token")
        if not files or not page_token:
            break
        request = {**request, "pageToken": page_token}
    name = pick_sample(names, loose=True)
    if not name:
        return None, "the competition has no file named like sample_submission.csv"
    if "/" in name or "\\" in name or name.startswith("."):
        return None, "the sample submission is inside a folder; download it and pass --sample"
    if not kaggle_cli.installed():
        return None, "the Kaggle CLI is not installed, so the sample cannot be downloaded"
    result = kaggle_cli.run(
        ["competitions", "download", slug, "--file", name, "--path", str(folder), "--quiet"],
        timeout=300,
    )
    if result.returncode != 0:
        return None, "the download of the sample submission failed"
    target = folder / name
    archive = folder / f"{name}.zip"
    if not target.exists() and archive.exists():
        try:
            safe_extract.safe_extract(archive, folder)
        except (ValueError, OSError):
            return None, "the downloaded sample archive could not be extracted safely"
    return (target, "") if target.exists() else (None, "the sample submission was not downloaded")


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Header and rows of a CSV file. Blank lines at the end are ignored."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    while rows and not any(cell.strip() for cell in rows[-1]):
        rows.pop()
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _examples(items: list) -> str:
    shown = ", ".join(str(item) for item in items[:MAX_EXAMPLES])
    return shown + (", ..." if len(items) > MAX_EXAMPLES else "")


def compare(submission: Path, sample: Path) -> list[tuple[bool | None, str]]:
    """Run the checks. Returns ``(passed, message)`` for each; None is a warning."""
    sub_header, sub_rows = read_csv(submission)
    ref_header, ref_rows = read_csv(sample)
    checks: list[tuple[bool | None, str]] = []

    if sub_header == ref_header:
        checks.append((True, f"columns: {', '.join(ref_header)}"))
    elif sorted(sub_header) == sorted(ref_header):
        checks.append((False, f"columns are in another order: expected {', '.join(ref_header)}"))
    else:
        checks.append(
            (
                False,
                f"columns: expected [{', '.join(ref_header)}], found [{', '.join(sub_header)}]",
            )
        )

    if len(sub_rows) == len(ref_rows):
        checks.append((True, f"rows: {len(ref_rows):,}"))
    else:
        checks.append((False, f"rows: expected {len(ref_rows):,}, found {len(sub_rows):,}"))

    ragged = [n for n, row in enumerate(sub_rows, start=2) if len(row) != len(sub_header)]
    if ragged:
        checks.append(
            (False, f"{len(ragged):,} rows do not have {len(sub_header)} values (line {ragged[0]})")
        )

    if sub_header and ref_header:
        name = ref_header[0]
        sub_ids = [row[0] for row in sub_rows if row]
        ref_ids = [row[0] for row in ref_rows if row]
        seen: set[str] = set()
        duplicated = [i for i in sub_ids if i in seen or seen.add(i)]  # type: ignore[func-returns-value]
        wanted = set(ref_ids)
        missing = [i for i in ref_ids if i not in seen]
        extra = [i for i in sub_ids if i not in wanted]
        problems = []
        if missing:
            problems.append(f"{len(missing):,} missing ({_examples(missing)})")
        if extra:
            problems.append(f"{len(extra):,} not in the sample ({_examples(extra)})")
        if duplicated:
            problems.append(f"{len(duplicated):,} duplicated ({_examples(duplicated)})")
        if problems:
            checks.append((False, f"ids in column {name}: " + "; ".join(problems)))
        else:
            checks.append((True, f"ids in column {name}: all {len(ref_ids):,} match"))

    # A column is numeric when every value in the sample is a number.
    numeric = [
        col
        for col in range(1, len(ref_header))
        if ref_rows and all(len(r) > col and _is_number(r[col]) for r in ref_rows)
    ]
    # A column that is empty somewhere in the sample may be empty in a submission.
    may_be_empty = {
        col
        for col in range(len(ref_header))
        if any(len(r) > col and not r[col].strip() for r in ref_rows)
    }
    empty: dict[int, list[int]] = {}
    for line, row in enumerate(sub_rows, start=2):
        for col, cell in enumerate(row):
            if not cell.strip() and col not in may_be_empty:
                empty.setdefault(col, []).append(line)

    def column(col: int) -> str:
        return sub_header[col] if col < len(sub_header) else f"column {col + 1}"

    hard = {col: lines for col, lines in empty.items() if col == 0 or col in numeric}
    soft = {col: lines for col, lines in empty.items() if col not in hard}
    for col, lines in hard.items():
        checks.append((False, f"{len(lines):,} empty values in {column(col)} (line {lines[0]})"))
    for col, lines in soft.items():
        checks.append(
            (
                None,
                f"{len(lines):,} empty values in {column(col)} (line {lines[0]}); the sample "
                "has none there. Check that the evaluation page allows an empty prediction",
            )
        )
    if not empty:
        allowed = ", ".join(column(col) for col in sorted(may_be_empty))
        note = f" (empty allowed in {allowed}, as in the sample)" if allowed else ""
        checks.append((True, f"no empty values{note}"))
    bad: list[tuple[int, str, str]] = []
    for line, row in enumerate(sub_rows, start=2):
        for col in numeric:
            if col >= len(row) or not row[col].strip():
                continue
            value = row[col]
            if not _is_number(value) or not math.isfinite(float(value)):
                bad.append((line, ref_header[col], value))
    if bad:
        line, column, value = bad[0]
        checks.append(
            (False, f"{len(bad):,} values are not finite numbers (line {line}, {column}: {value})")
        )
    elif numeric:
        names = ", ".join(ref_header[col] for col in numeric)
        checks.append((True, f"numbers are finite in: {names}"))
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a submission file against the sample submission, before it uses a slot.",
        epilog="Checks the shape of the file, not the quality of the predictions.",
    )
    script.add_competition(parser, "file")
    parser.add_argument("--sample", metavar="PATH", help="The sample submission to compare with")
    args = script.parse(parser, argv)
    slug, file_name = script.positionals(parser, args, "file")

    submission = Path(file_name)
    if not submission.is_file():
        return script.fail(f"the submission file was not found: {file_name}", script.EXIT_USAGE)
    if submission.suffix.lower() != ".csv":
        return script.fail("only CSV submissions can be checked", script.EXIT_USAGE)

    credentials.load_configured_env_file()
    with tempfile.TemporaryDirectory() as scratch:
        if args.sample:
            sample = Path(args.sample)
            if not sample.is_file():
                return script.fail(f"the sample file was not found: {args.sample}", 2)
        else:
            sample = find_local_sample(slug, submission)
            if sample is None:
                sample, why = download_sample(slug, Path(scratch))
                if sample is None:
                    print(f"error: no sample submission to compare with: {why}.", file=sys.stderr)
                    print("       Download it and pass --sample PATH.", file=sys.stderr)
                    return script.EXIT_UNAVAILABLE
        try:
            checks = compare(submission, sample)
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            return script.fail(f"a file could not be read as CSV ({type(exc).__name__})", 1)
        sample_name = sample.name

    failed = sum(1 for passed, _ in checks if passed is False)
    warned = sum(1 for passed, _ in checks if passed is None)
    labels = {True: "PASS", False: "FAIL", None: "WARN"}
    # Column names and ids come from the files, and the sample comes from Kaggle.
    with untrusted.Block(source="local", tool="validate", competition=slug) as block:
        block.write(f"Checked {file_name} against the sample {sample_name}")
        for passed, message in checks:
            block.write(f"  {labels[passed]}  {message}")
    if failed:
        print(f"{failed} of {len(checks)} checks failed. Fix the file before submitting.")
        return script.EXIT_FAILED
    if warned:
        print(f"No check failed, with {warned} warning(s) to look at before submitting.")
        return script.EXIT_OK
    print("Every check passed. The shape is right; this does not score the predictions.")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
