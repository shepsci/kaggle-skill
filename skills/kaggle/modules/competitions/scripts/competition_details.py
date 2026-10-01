"""Get structured details for a specific Kaggle competition.

Usage:
    python competition_details.py --slug SLUG [--top-n 5]

Prints one JSON document with the file list, the top of the leaderboard and
the most-voted notebooks. Team names and notebook titles are written by
participants, so the document is printed inside an untrusted-content block.
"""

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from utils import (  # noqa: E402
    KaggleAuthError,
    attr,
    call_quiet,
    get_api,
    rate_limit,
    unwrap_response,
)

from shared import untrusted  # noqa: E402

SOURCE = "kaggle-api"
TOOL = "competition_details"

# Patterns to identify solution writeup kernels
WRITEUP_PATTERNS = [
    re.compile(r"\b1st\s+place\b", re.IGNORECASE),
    re.compile(r"\b2nd\s+place\b", re.IGNORECASE),
    re.compile(r"\b3rd\s+place\b", re.IGNORECASE),
    re.compile(r"\b\d+(st|nd|rd|th)\s+place\b", re.IGNORECASE),
    re.compile(r"\bwinning\s+solution\b", re.IGNORECASE),
    re.compile(r"\bgold\s+(medal\s+)?solution\b", re.IGNORECASE),
    re.compile(r"\btop\s+\d+%?\s+solution\b", re.IGNORECASE),
    re.compile(r"\bwinner'?s?\s+writeup\b", re.IGNORECASE),
    re.compile(r"\bsolution\s+writeup\b", re.IGNORECASE),
]


def is_writeup_kernel(title: str) -> bool:
    """Check if a kernel title looks like a solution writeup."""
    return any(p.search(title) for p in WRITEUP_PATTERNS)


# The API pages its listings at 20 by default. Ask for more, and say so when
# there is still more than was asked for.
MAX_FILES = 200
MAX_LEADERBOARD_ROWS = 200


def get_competition_files(api, slug: str) -> list[dict]:
    """Get file listing for a competition, up to MAX_FILES entries.

    When the competition has more files, the last entry is a marker:
    ``{"name": "...", "truncated": True}``.
    """
    raw = call_quiet(api.competition_list_files, slug, page_size=MAX_FILES)
    files = unwrap_response(raw, "files")
    listing = [
        {
            "name": attr(f, "name", default=str(f)),
            "size": attr(f, "total_bytes", "totalBytes", "size", default=0),
        }
        for f in files
    ]
    if attr(raw, "next_page_token", "nextPageToken"):
        listing.append({"name": "...", "truncated": True})
    return listing


def get_leaderboard(api, slug: str, top_n: int = 5) -> list[dict]:
    """Get top N leaderboard entries (at most MAX_LEADERBOARD_ROWS)."""
    wanted = max(1, min(top_n, MAX_LEADERBOARD_ROWS))
    raw = call_quiet(api.competition_leaderboard_view, slug, page_size=wanted)
    lb = unwrap_response(raw, "submissions")
    if not lb:
        lb = unwrap_response(raw, "leaderboard")
    entries = []
    for i, entry in enumerate(lb[:wanted]):
        team = attr(entry, "team_name", "teamName", "team_id", "teamId", default="")
        entries.append(
            {
                "rank": i + 1,
                "team": team,
                "score": attr(entry, "score", default=""),
            }
        )
    return entries


def get_top_kernels(api, slug: str, page_size: int = 10) -> list[dict]:
    """Get top kernels sorted by votes."""
    raw = call_quiet(api.kernels_list, competition=slug, sort_by="voteCount", page_size=page_size)
    kernels = unwrap_response(raw, "kernels")
    result = []
    for k in kernels:
        title = attr(k, "title", default="")
        ref = attr(k, "ref", default="")
        result.append(
            {
                "title": title,
                "ref": ref,
                "votes": attr(k, "total_votes", "totalVotes", default=0),
                "url": f"https://www.kaggle.com/code/{ref}" if ref else "",
                "is_writeup": is_writeup_kernel(title),
            }
        )
    return result


def _section(errors: dict, name: str, fn, *args) -> list[dict]:
    """Run one lookup. A failure is recorded under ``errors`` instead of raised."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - any API failure is reported, not fatal
        errors[name] = f"{type(exc).__name__}: {exc}"[:200]
        return []


def get_details(slug: str, top_n: int = 5) -> dict:
    """Get all structured details for a competition."""
    api = get_api()
    errors: dict[str, str] = {}

    files = _section(errors, "files", get_competition_files, api, slug)
    rate_limit()
    leaderboard = _section(errors, "leaderboard_top", get_leaderboard, api, slug, top_n)
    rate_limit()
    kernels = _section(errors, "top_kernels", get_top_kernels, api, slug)

    details = {
        "slug": slug,
        "url": f"https://www.kaggle.com/competitions/{slug}",
        "files": files,
        "leaderboard_top": leaderboard,
        "top_kernels": kernels,
        "writeup_kernels": [k for k in kernels if k.get("is_writeup")],
    }
    if errors:
        details["errors"] = errors
    return details


def main() -> int:
    parser = argparse.ArgumentParser(description="Get details for a Kaggle competition")
    parser.add_argument("--slug", required=True, help="Competition slug")
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help=f"Top N leaderboard entries (default: 5, at most {MAX_LEADERBOARD_ROWS})",
    )
    args = parser.parse_args()

    try:
        details = get_details(args.slug, args.top_n)
    except KaggleAuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    untrusted.emit_json(details, source=SOURCE, tool=TOOL, competition=args.slug, indent=2)

    errors = details.get("errors") or {}
    if len(errors) == 3:
        print("error: every lookup failed; see the errors field", file=sys.stderr)
        return 1
    if errors:
        print(f"warning: {len(errors)} of 3 lookups failed; see the errors field", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
