#!/usr/bin/env python3
"""Submit to a Kaggle competition: a dry run first, and a record of what was sent.

    competition_submit.py titanic ./submission.csv -m "baseline"           dry run
    competition_submit.py titanic ./submission.csv -m "baseline" --yes     submit
    competition_submit.py <competition> --notebook me/my-notebook --version 12 -m "v12" --yes

Without --yes nothing is submitted. The dry run prints what would be sent, how
many submissions are left today, and whether this exact file was sent before.
Check the file itself with the validate command.

A submission uses one of the day's slots, and on some competitions a
submission that errors still uses it. Get the user's go-ahead first.

A real submission adds one line to ./.kaggle-skill/ledger.jsonl: the time, the
file's size and SHA-256 (or the notebook and its version), the message, and
the score you expect if you give --expect. The watch command adds the score
Kaggle reports. The ledger is a local file; nothing in it is sent anywhere.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import competition_validate  # noqa: E402

from shared import (  # noqa: E402
    competition,
    credentials,
    kaggle_cli,
    ledger,
    mcp_client,
    script,
    text,
)

DEFAULT_MESSAGE = "Submitted with kaggle-skill"


def already_sent(slug: str, sha256: str) -> dict | None:
    """The ledger's record of this exact file for this competition, if any."""
    for row in reversed(ledger.submissions(slug)):
        if row.get("sha256") == sha256:
            return row
    return None


def file_check(slug: str, path: Path, sample: str | None) -> tuple[str, str]:
    """Run validate's checks for the dry run. Returns ``(detail line, state)``.

    The checks themselves are printed in a block: they quote column names and
    ids. The detail line is the skill's own words only.
    """
    checks, sample_name, why = competition_validate.check_against_sample(slug, path, sample)
    if checks is None:
        return f"not run: {why}. Add --sample PATH to check against a file", "not run"
    competition_validate.print_checks(slug, str(path), sample_name, checks)
    failed = sum(1 for passed, _ in checks if passed is False)
    warned = sum(1 for passed, _ in checks if passed is None)
    if failed:
        return f"{failed} of {len(checks)} FAILED (above): Kaggle may reject the file", "failed"
    if warned:
        return f"passed, with {warned} warning(s) to read above", "warned"
    return f"all {len(checks)} passed", "passed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Submit to a Kaggle competition: a dry run first, and a record of what "
        "was sent.",
        epilog="Uses a daily submission slot. Needs the Kaggle CLI and a credential to submit.",
    )
    script.add_competition(parser, "file?", "message?")
    parser.add_argument("-m", "--message", dest="message_opt", help="What this submission is")
    parser.add_argument(
        "--notebook",
        metavar="OWNER/NAME",
        help="Code competition: submit this notebook's output instead of a local file",
    )
    parser.add_argument("--version", type=script.positive_int, help="With --notebook: its version")
    parser.add_argument(
        "--expect",
        type=float,
        metavar="SCORE",
        help="The score you expect, for the ledger. The watch command reports the gap",
    )
    parser.add_argument(
        "--sample",
        metavar="PATH",
        help="The sample submission to check the file against (default: found or downloaded)",
    )
    script.add_yes(parser)
    args = script.parse(parser, argv)
    slug, file_name, message = script.positionals(parser, args, "file?", "message?")
    message = args.message_opt or message or DEFAULT_MESSAGE

    details: list[tuple[str, str]] = [("competition", slug)]
    record: dict = {"event": "submit", "competition": slug, "message": message}
    if args.notebook:
        if not script.is_handle(args.notebook, 2):
            parser.error("--notebook takes owner/name")
        if not args.version:
            parser.error("--notebook needs --version: the notebook version to submit")
        file_name = file_name or "submission.csv"
        record.update(notebook=args.notebook, version=args.version, file=file_name)
        details += [
            ("notebook", f"{args.notebook}, version {args.version}"),
            ("output file", file_name),
        ]
        cli_args = ["--file", file_name, "--kernel", args.notebook, "--version", str(args.version)]
    else:
        if not file_name:
            parser.error("give the submission file, or --notebook with --version")
        path = Path(file_name)
        if not path.is_file():
            return script.fail(f"the submission file was not found: {file_name}", script.EXIT_USAGE)
        facts = ledger.file_facts(path)
        record.update(facts)
        details += [
            ("file", f"{file_name} ({text.human_size(facts['bytes'])})"),
            ("sha256", facts["sha256"][:16]),
        ]
        cli_args = ["--file", file_name]
    details.append(("message", message))
    if args.expect is not None:
        record["expected"] = args.expect
        details.append(("expected", f"{args.expect:g}"))

    credentials.load_configured_env_file()
    checked = ""
    if not args.notebook and Path(file_name).suffix.lower() == ".csv":
        # The same checks as validate, so one command shows the file and the plan.
        line, checked = file_check(slug, Path(file_name), args.sample)
        details.append(("file check", line))
        record["file_check"] = checked
    # What the competition takes. The call is public; a failure only skips the checks.
    facts_result = competition.fetch_facts(slug, token="")
    info = (
        competition.facts(slug, facts_result.data)
        if facts_result.ok and isinstance(facts_result.data, dict)
        else None
    )
    blockers: list[str] = []
    if info:
        if info["submissions_disabled"]:
            blockers.append("submissions to this competition are closed")
        if info["notebook_only"] and not args.notebook:
            blockers.append(
                "this is a code competition: it takes a notebook version "
                "(--notebook OWNER/NAME --version N), not a local file"
            )
        deadline = text.parse_time(info.get("deadline"))
        if deadline is not None and deadline < text.now_utc():
            script.warn(f"the deadline passed: {text.when(info['deadline'])}")

    limits = competition.submission_limits(slug) if credentials.resolve() else None
    if limits is not None:
        cost = f"1 of the {limits['numAllowedNow']} submissions left today"
        if int(limits["numAllowedNow"]) <= 0:
            script.warn("Kaggle reports no submissions left today")
    elif info and info.get("max_daily_submissions"):
        cost = f"1 of {info['max_daily_submissions']} submissions a day"
    else:
        cost = "one daily submission slot"

    earlier = already_sent(slug, record["sha256"]) if "sha256" in record else None
    if earlier:
        script.warn(
            f"this exact file was already submitted on {earlier.get('time')} "
            f"(score: {earlier.get('public_score') or 'not recorded'})"
        )
    for blocker in blockers:
        print(f"error: {blocker}", file=sys.stderr)

    gate = script.write_gate(
        args.yes,
        action="submit to a competition",
        details=details,
        cost=cost,
        blocked=bool(blockers),
    )
    if gate is not None:
        if blockers:
            return script.EXIT_USAGE
        return gate

    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "submitting")
    if credentials.resolve() is None:
        return script.no_credential("submitting")

    # --message=VALUE keeps a message that starts with "-" from being read as an option.
    status = kaggle_cli.run_wrapped(
        ["competitions", "submit", slug, *cli_args, f"--message={message}"],
        tool="competitions.submit",
    )
    if status != 0:
        return status

    # The newest submission is the one just made. Its id ties the score to this record.
    rows, _ = competition.fetch_submissions(slug, mcp_client.resolve_token(), limit=1)
    if rows:
        record["ref"] = rows[0]["ref"]
    ref = f" as submission {record['ref']}" if "ref" in record else ""
    try:
        print(f"Submitted{ref}. Recorded in {ledger.append(record)}.")
    except OSError as exc:
        # The submission went through; only the local record is missing.
        print(f"Submitted{ref}.")
        script.warn(f"the submission was not recorded in the ledger: {exc}")
    print(f"Wait for the score with: watch {slug}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
