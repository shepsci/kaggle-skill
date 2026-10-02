#!/usr/bin/env python3
"""Fetch the content pages for any Kaggle competition.

Wraps the `list_competition_pages` MCP endpoint. Returns the rules,
description, evaluation, data-description, FAQ, timeline, prizes, and any
other host-authored pages — works for both regular competitions
(`titanic`, `playground-series-s6e2`) and hackathons (`kaggle-measuring-agi`).

Public competitions need no credentials. A token, when one is configured, is
sent so that competitions you have joined privately also resolve.

For hackathon-specific overview content (with judge/track metadata), prefer
the hackathon module's `hackathon_overview.py` which calls
`get_hackathon_overview` instead.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, untrusted  # noqa: E402
from shared.mcp_client import (  # noqa: E402
    classify_result,
    extract_json,
    mcp_call,
    print_failure,
    resolve_token,
)

SOURCE = "kaggle-mcp"
TOOL = "list_competition_pages"


def fetch_pages(competition: str, token: str = "") -> dict:
    resp = mcp_call(TOOL, {"request": {"competitionName": competition}}, token=token)
    status = classify_result(resp)
    if status != "ok":
        return {"status": status, "raw": resp}
    payload = extract_json(resp) or {}
    return {"status": "ok", "competition": competition, "data": payload}


def find_page(pages: list[dict], *needles: str) -> dict | None:
    """Return the first page whose `name` contains any of the needles (case-insensitive)."""
    for page in pages or []:
        name = (page.get("name") or "").lower()
        if any(n.lower() in name for n in needles):
            return page
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--competition", required=True, help="Competition slug (e.g., titanic)")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print one line per page instead of full JSON",
    )
    parser.add_argument(
        "--page",
        help="Print only the named page's content (case-insensitive substring match)",
    )
    args = parser.parse_args()

    credentials.load_configured_env_file()
    token = resolve_token()

    result = fetch_pages(args.competition, token)
    if result["status"] != "ok":
        return print_failure(
            result["raw"],
            tool=TOOL,
            had_token=bool(token),
            competition=args.competition,
            indent=2 if args.pretty else None,
        )

    pages = (result.get("data") or {}).get("pages") or []

    # All page content is host-authored: it stays inside one untrusted block.
    exit_code = 0
    with untrusted.Block(source=SOURCE, tool=TOOL, competition=args.competition) as block:
        if args.page:
            match = find_page(pages, args.page)
            if match:
                block.write(f"## {match.get('name')}\n\n")
                block.write(match.get("content") or "")
            else:
                exit_code = 1
        elif args.summary:
            block.write(f"competition: {args.competition}")
            block.write(f"page count: {len(pages)}")
            for p in pages:
                name = p.get("name", "<unnamed>")
                content = p.get("content") or ""
                preview = content[:80].replace("\n", " ")
                block.write(f"  - {name}: {preview}")
            rules = find_page(pages, "rule", "official")
            evaluation = find_page(pages, "evaluation", "rubric", "judging")
            data_desc = find_page(pages, "data-description", "data description")
            timeline = find_page(pages, "timeline")
            block.write("\nKey pages:")
            block.write(f"  rules:            {'found' if rules else 'MISSING'}")
            block.write(f"  evaluation:       {'found' if evaluation else 'MISSING'}")
            block.write(f"  data-description: {'found' if data_desc else 'MISSING'}")
            block.write(f"  timeline:         {'found' if timeline else 'MISSING'}")
        else:
            block.write_json(result, indent=2 if args.pretty else None)

    if exit_code:
        print("error: no page matched the --page value", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
