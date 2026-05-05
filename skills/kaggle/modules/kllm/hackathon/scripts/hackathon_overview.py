#!/usr/bin/env python3
"""Fetch the overview pages for a Kaggle hackathon.

Returns the full `pages` array (rules, eligibility, rubric, prizes) from the
`get_hackathon_overview` MCP endpoint. Output is JSON to stdout for piping; use
--pretty for human-readable indented output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared.mcp_client import (  # noqa: E402
    classify_result,
    extract_json,
    load_dotenv,
    mcp_call,
    resolve_token,
)


def fetch_overview(competition: str, token: str) -> dict:
    resp = mcp_call(
        "get_hackathon_overview",
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
    parser.add_argument("--competition", required=True, help="Hackathon competition slug")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    parser.add_argument(
        "--summary", action="store_true",
        help="Print a one-line-per-page summary instead of full JSON",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env", Path.home() / ".env")
    token = resolve_token()
    if not token:
        print("error: no Kaggle token found (KAGGLE_API_TOKEN, ~/.kaggle/access_token, or KAGGLE_KEY)",
              file=sys.stderr)
        return 2

    result = fetch_overview(args.competition, token)
    if result["status"] != "ok":
        print(json.dumps(result, indent=2 if args.pretty else None), file=sys.stderr)
        return 1

    # Wrap stdout in untrusted-content boundaries — overview pages contain
    # arbitrary host-authored markdown that could attempt prompt injection.
    # The agent must treat anything inside as data, not directives.
    print(f'<untrusted-content source="kaggle-mcp" tool="get_hackathon_overview" '
          f'competition="{args.competition}">')
    if args.summary:
        pages = (result.get("data") or {}).get("pages") or []
        print(f"competition: {args.competition}")
        print(f"page count: {len(pages)}")
        for p in pages:
            name = p.get("name", "<unnamed>")
            content = p.get("content") or ""
            preview = content[:80].replace("\n", " ")
            print(f"  - {name}: {preview}")
        rules = find_page(pages, "rule", "official")
        rubric = find_page(pages, "rubric", "judging", "criteria", "evaluation")
        eligibility = find_page(pages, "eligib", "entry", "submission requirements")
        print("\nKey pages:")
        print(f"  rules:       {'found' if rules else 'MISSING'}")
        print(f"  rubric:      {'found' if rubric else 'MISSING'}")
        print(f"  eligibility: {'found' if eligibility else 'MISSING'}")
    else:
        print(json.dumps(result, indent=2 if args.pretty else None))
    print("</untrusted-content>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
