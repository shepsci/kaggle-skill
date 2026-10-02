#!/usr/bin/env python3
"""Fetch the overview pages for a Kaggle hackathon.

Returns the full `pages` array (rules, eligibility, rubric, prizes) from the
`get_hackathon_overview` MCP endpoint. Output is JSON inside one
untrusted-content block; use --pretty for indented output.

The overview is public: no credentials are needed. A token, when one is
configured, is sent as well.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[4]
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
TOOL = "get_hackathon_overview"


def fetch_overview(competition: str, token: str = "") -> dict:
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
    parser.add_argument("--competition", required=True, help="Hackathon competition slug")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a one-line-per-page summary instead of full JSON",
    )
    args = parser.parse_args()

    credentials.load_configured_env_file()
    token = resolve_token()

    result = fetch_overview(args.competition, token)
    if result["status"] != "ok":
        return print_failure(
            result["raw"],
            tool=TOOL,
            had_token=bool(token),
            competition=args.competition,
            indent=2 if args.pretty else None,
        )

    # Overview pages are host-authored markdown: everything stays inside one
    # untrusted block so the agent reads it as data.
    with untrusted.Block(source=SOURCE, tool=TOOL, competition=args.competition) as block:
        if args.summary:
            pages = (result.get("data") or {}).get("pages") or []
            block.write(f"competition: {args.competition}")
            block.write(f"page count: {len(pages)}")
            for p in pages:
                name = p.get("name", "<unnamed>")
                content = p.get("content") or ""
                preview = content[:80].replace("\n", " ")
                block.write(f"  - {name}: {preview}")
            rules = find_page(pages, "rule", "official")
            rubric = find_page(pages, "rubric", "judging", "criteria", "evaluation")
            eligibility = find_page(pages, "eligib", "entry", "submission requirements")
            block.write("\nKey pages:")
            block.write(f"  rules:       {'found' if rules else 'MISSING'}")
            block.write(f"  rubric:      {'found' if rubric else 'MISSING'}")
            block.write(f"  eligibility: {'found' if eligibility else 'MISSING'}")
        else:
            block.write_json(result, indent=2 if args.pretty else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
