"""Get structured details for a specific Kaggle competition.

Usage:
    python competition_details.py --slug SLUG [--top-n 5]
"""

import argparse
import json
import re
import sys

from utils import get_api, rate_limit, unwrap_response


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


def get_competition_files(api, slug: str) -> list[dict]:
    """Get file listing for a competition."""
    try:
        raw = api.competition_list_files(slug)
        files = unwrap_response(raw, "files")
        result = []
        for f in files:
            result.append({
                "name": getattr(f, "name", str(f)),
                "size": getattr(f, "totalBytes", getattr(f, "size", 0)),
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


def get_leaderboard(api, slug: str, top_n: int = 5) -> list[dict]:
    """Get top N leaderboard entries."""
    try:
        raw = api.competition_leaderboard_view(slug)
        lb = unwrap_response(raw, "submissions")
        if not lb:
            lb = unwrap_response(raw, "leaderboard")
        entries = []
        for i, entry in enumerate(lb[:top_n]):
            team = (getattr(entry, "team_name", None)
                    or getattr(entry, "teamName", None)
                    or getattr(entry, "team_id", None)
                    or getattr(entry, "teamId", ""))
            entries.append({
                "rank": i + 1,
                "team": team or "",
                "score": getattr(entry, "score", ""),
            })
        return entries
    except Exception as e:
        return [{"error": str(e)}]


def get_top_kernels(api, slug: str, page_size: int = 10) -> list[dict]:
    """Get top kernels sorted by votes."""
    try:
        raw = api.kernels_list(competition=slug, sort_by="voteCount", page_size=page_size)
        kernels = unwrap_response(raw, "kernels")
        result = []
        for k in kernels:
            title = getattr(k, "title", "")
            ref = getattr(k, "ref", "")
            result.append({
                "title": title,
                "ref": ref,
                "votes": getattr(k, "totalVotes", 0),
                "url": f"https://www.kaggle.com/code/{ref}" if ref else "",
                "is_writeup": is_writeup_kernel(title),
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


def get_details(slug: str, top_n: int = 5) -> dict:
    """Get all structured details for a competition."""
    api = get_api()

    # Files
    files = get_competition_files(api, slug)
    rate_limit()

    # Leaderboard
    leaderboard = get_leaderboard(api, slug, top_n)
    rate_limit()

    # Top kernels
    kernels = get_top_kernels(api, slug)

    # Identify writeup kernels
    writeup_kernels = [k for k in kernels if k.get("is_writeup")]

    return {
        "slug": slug,
        "url": f"https://www.kaggle.com/competitions/{slug}",
        "files": files,
        "leaderboard_top": leaderboard,
        "top_kernels": kernels,
        "writeup_kernels": writeup_kernels,
    }


def main():
    parser = argparse.ArgumentParser(description="Get details for a Kaggle competition")
    parser.add_argument("--slug", required=True, help="Competition slug")
    parser.add_argument("--top-n", type=int, default=5, help="Top N leaderboard entries (default: 5)")
    args = parser.parse_args()

    details = get_details(args.slug, args.top_n)
    print(json.dumps(details, indent=2, default=str))


if __name__ == "__main__":
    main()
