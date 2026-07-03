#!/usr/bin/env python3
"""Fetch the content pages for any Kaggle competition.

Wraps the `list_competition_pages` MCP endpoint. Returns the rules,
description, evaluation, data-description, FAQ, timeline, prizes, and any
other host-authored pages — works for both regular competitions
(`titanic`, `playground-series-s6e2`) and hackathons (`kaggle-measuring-agi`).

For hackathon-specific overview content (with judge/track metadata), prefer
the hackathon module's `hackathon_overview.py` which calls
`get_hackathon_overview` instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared.mcp_client import (  # noqa: E402
    classify_result,
    extract_json,
    load_dotenv,
    mcp_call,
    resolve_token,
)


def fetch_pages(competition: str, token: str) -> dict:
    resp = mcp_call(
        "list_competition_pages",
        {"request": {"competitionName": competition}},
        token=token,
    )
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
        "--summary", action="store_true",
        help="Print one line per page instead of full JSON",
    )
    parser.add_argument(
        "--page", help="Print only the named page's content (case-insensitive substring match)",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env", Path.home() / ".env")
    token = resolve_token()
    if not token:
        print("error: no Kaggle token found", file=sys.stderr)
        return 2

    result = fetch_pages(args.competition, token)
    if result["status"] != "ok":
        print(json.dumps(result, indent=2 if args.pretty else None), file=sys.stderr)
        return 1

    pages = (result.get("data") or {}).get("pages") or []

    # All page content is host-authored markdown — wrap to prevent prompt
    # injection from a hostile competition description.
    print(f'<untrusted-content source="kaggle-mcp" tool="list_competition_pages" '
          f'competition="{args.competition}">')

    if args.page:
        match = find_page(pages, args.page)
        if not match:
            print(f"# no page matched {args.page!r}", file=sys.stderr)
            print("</untrusted-content>")
            return 1
        print(f"## {match.get('name')}\n")
        print(match.get("content") or "")
    elif args.summary:
        print(f"competition: {args.competition}")
        print(f"page count: {len(pages)}")
        for p in pages:
            name = p.get("name", "<unnamed>")
            content = p.get("content") or ""
            preview = content[:80].replace("\n", " ")
            print(f"  - {name}: {preview}")
        rules = find_page(pages, "rule", "official")
        evaluation = find_page(pages, "evaluation", "rubric", "judging")
        data_desc = find_page(pages, "data-description", "data description")
        timeline = find_page(pages, "timeline")
        print("\nKey pages:")
        print(f"  rules:            {'found' if rules else 'MISSING'}")
        print(f"  evaluation:       {'found' if evaluation else 'MISSING'}")
        print(f"  data-description: {'found' if data_desc else 'MISSING'}")
        print(f"  timeline:         {'found' if timeline else 'MISSING'}")
    else:
        print(json.dumps(result, indent=2 if args.pretty else None))

    print("</untrusted-content>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
