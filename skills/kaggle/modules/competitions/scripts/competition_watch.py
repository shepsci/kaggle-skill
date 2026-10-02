#!/usr/bin/env python3
"""Wait until Kaggle has scored a submission, then report and record the score.

    competition_watch.py titanic                    the newest submission
    competition_watch.py titanic --ref 53336045     a specific one
    competition_watch.py titanic --timeout 3600 --interval 60

Reads the submission every --interval seconds until Kaggle has scored it or
reported an error, or --timeout seconds have passed. The score goes into
./.kaggle-skill/ledger.jsonl. When the submit command recorded a score you
expected, the gap to it is printed.

Needs a credential: an API token or `kaggle auth login`. It only reads.

Exit status: 0 scored, 1 the submission failed or was not found, 124 still
pending at the timeout, 4 the submission could not be read.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, ledger, mcp_client, script, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = competition.SUBMISSIONS_TOOL
MAX_FAILED_READS = 5
FINISHED = ("COMPLETE", "ERROR")


def read(slug: str, token: str, ref: int | None):
    """The submission with this id, or your newest. Returns ``(row or None, result)``."""
    if ref is not None:
        return competition.fetch_submission(ref, token)
    rows, result = competition.fetch_submissions(slug, token, limit=1)
    return (rows[0] if rows else None), result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wait until Kaggle has scored a submission, then report and record the score.",
        epilog="Needs a Kaggle credential: an API token or `kaggle auth login`.",
    )
    script.add_competition(parser)
    parser.add_argument("--ref", type=int, help="The submission id (default: your newest)")
    parser.add_argument(
        "--interval",
        type=script.positive_int,
        default=30,
        metavar="SECONDS",
        help="Time between checks (default: 30)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        metavar="SECONDS",
        help="Stop waiting after this long; 0 checks once (default: 1800)",
    )
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
    if not token:
        return script.no_credential("watching a submission")

    waited = 0
    failed_reads = 0
    while True:
        row, result = read(slug, token, args.ref)
        if not result.ok:
            failed_reads += 1
            # A denial for --ref means the submission is someone else's: no use waiting.
            if result.status == "unauthenticated" or result.denied:
                return result.fail(competition=slug)
            if failed_reads >= MAX_FAILED_READS:
                result.fail(competition=slug)
                return script.EXIT_UNAVAILABLE
        else:
            failed_reads = 0
            if row is None:
                what = f"submission {args.ref}" if args.ref else "any submission of yours"
                return script.fail(f"{what} was not found in {slug}", script.EXIT_FAILED)
            if row["status"] in FINISHED:
                break
            print(f"[{time.strftime('%H:%M:%S')}] submission {row['ref']}: still being scored")
        if waited >= args.timeout:
            if failed_reads:
                # The last read failed, so whether it is still pending is not known.
                result.fail(competition=slug)
                return script.EXIT_UNAVAILABLE
            print(
                f"Still pending after {waited}s. Run this again to keep waiting.", file=sys.stderr
            )
            return script.EXIT_TIMEOUT
        time.sleep(args.interval)
        waited += args.interval

    score = row["public_score"]
    expected = ledger.expected_for(row["ref"])
    # The description and any error text were written by the user or by Kaggle.
    with untrusted.Block(source=SOURCE, tool=TOOL, competition=slug) as block:
        block.write(f"submission {row['ref']}: {row['status']}")
        block.write(f"  public score: {score or 'none'}")
        block.write(f"  sent:         {row['date']}")
        block.write(f"  message:      {row['description']}")
        if row["error"]:
            block.write(f"  error:        {row['error']}")
    value = competition.score_value(score)
    if expected is not None and value is not None:
        print(f"Expected {expected:g}, got {value:g}: a difference of {value - expected:+.5g}.")
    if not ledger.has_score(row["ref"]):
        record = {
            "event": "score",
            "competition": slug,
            "ref": row["ref"],
            "status": row["status"],
            "public_score": score,
        }
        try:
            print(f"Recorded in {ledger.append(record)}.")
        except OSError as exc:
            script.warn(f"the score was not recorded in the ledger: {exc}")
    return script.EXIT_OK if row["status"] == "COMPLETE" else script.EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
