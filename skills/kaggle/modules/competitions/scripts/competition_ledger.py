#!/usr/bin/env python3
"""Show the local record of your submissions and their scores.

    competition_ledger.py
    competition_ledger.py titanic --json

Reads ./.kaggle-skill/ledger.jsonl, which competition_submit.py and
competition_watch.py write. Nothing is sent or changed. The record holds only
what was submitted through this skill.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import ledger, script, text, untrusted  # noqa: E402


def text_lines(rows: list[dict]) -> list[str]:
    lines = [
        f"  {'sent (UTC)':<16}  {'competition':<28}  {'score':<10}  {'expected':<9}  what",
    ]
    for row in rows:
        moment = text.parse_time(row.get("time"))
        sent = moment.strftime("%Y-%m-%d %H:%M") if moment else "-"
        if row.get("notebook"):
            what = f"{row['notebook']} v{row.get('version')}"
        elif row.get("event") == "score":
            what = f"submission {row.get('ref')}, not sent through this skill"
        else:
            what = f"{Path(str(row.get('file') or '')).name} {str(row.get('sha256') or '')[:8]}"
        expected = row.get("expected")
        lines.append(
            f"  {sent:<16}  {text.shorten(str(row.get('competition') or ''), 28):<28}  "
            f"{str(row.get('public_score') or 'pending'):<10}  "
            f"{(f'{expected:g}' if isinstance(expected, (int, float)) else '-'):<9}  "
            f"{what} · {text.shorten(text.collapse(str(row.get('message') or '')), 50)}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show the local record of your submissions and their scores.",
        epilog="The record is ./.kaggle-skill/ledger.jsonl. It is only read here.",
    )
    parser.add_argument("competition", nargs="?", help="Only this competition (slug or URL)")
    script.add_limit(parser, 20, "submissions, newest first")
    script.add_json(parser)
    args = parser.parse_args(argv)
    slug = None
    if args.competition:
        try:
            slug = script.competition_slug(args.competition)
        except ValueError as exc:
            parser.error(str(exc))

    rows = list(reversed(ledger.submissions(slug)))[: args.limit]
    # Messages and file names were typed by the user or an agent: data, not instructions.
    attrs = {"source": "local", "tool": "ledger"}
    if args.json:
        untrusted.emit_json(rows, indent=2 if args.pretty else None, **attrs)
        return script.EXIT_OK
    if not rows:
        print(f"No submissions recorded in {ledger.path()}.")
        return script.EXIT_OK
    with untrusted.Block(**attrs) as block:
        block.write(f"{len(rows)} submissions recorded in {ledger.path()}:")
        for line in text_lines(rows):
            block.write(line)
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
