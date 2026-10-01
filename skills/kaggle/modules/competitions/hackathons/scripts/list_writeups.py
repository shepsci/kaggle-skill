#!/usr/bin/env python3
"""Enumerate writeup submissions for a Kaggle hackathon.

Calls `list_hackathon_write_ups` paginated, then `list_hackathon_tracks` once
to resolve numeric track and prize ids to titles. Prints one JSON object per
writeup row (or a single JSON object with --array), inside one
untrusted-content block.

Each row has `writeup_id` and `slug`, the two identifiers fetch_writeup.py
takes. Roster rows do not include a forum topic id, so `topic_id` is null.

The roster needs a credential and is role-gated: the server answers only for
hosts, judges and teammates of the hackathon. A denial is reported as a denial
(exit 3), never as an empty roster. Use fetch_writeup.py for full writeup
bodies; published writeups are public.
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

DEFAULT_PAGE_SIZE = 50
KAGGLE_BASE = "https://www.kaggle.com"
SOURCE = "kaggle-mcp"
TOOL = "list_hackathon_write_ups"


def fetch_track_list(competition: str, token: str = "") -> list[dict]:
    """Tracks of a hackathon, with their prizes. Empty when the call fails."""
    resp = mcp_call(
        "list_hackathon_tracks",
        {"request": {"competitionName": competition}},
        token=token,
    )
    if classify_result(resp) != "ok":
        return []
    payload = extract_json(resp) or {}
    return [t for t in payload.get("tracks") or [] if isinstance(t, dict)]


def track_titles_by_id(tracks: list[dict]) -> dict[int, str]:
    return {t.get("id"): t.get("title", "") for t in tracks if t.get("id") is not None}


def prize_titles_by_id(tracks: list[dict]) -> dict[int, str]:
    """Map a prize id to ``"<track title>: <prize title>"``."""
    prizes: dict[int, str] = {}
    for track in tracks:
        for prize in track.get("prizes") or []:
            if isinstance(prize, dict) and prize.get("id") is not None:
                prizes[prize["id"]] = f"{track.get('title', '')}: {prize.get('title', '')}"
    return prizes


def fetch_tracks(competition: str, token: str = "") -> dict[int, str]:
    return track_titles_by_id(fetch_track_list(competition, token))


def fetch_writeups_page(
    competition: str,
    token: str,
    page_size: int,
    page_token: str | None,
    winner_only: bool,
) -> tuple[list[dict], str | None, int | None, dict | None]:
    """Fetch one page. Returns ``(rows, next_token, total, failed_response)``.

    ``failed_response`` is the raw server response when the call did not
    succeed, and None otherwise.
    """
    request: dict = {"competitionName": competition, "pageSize": page_size}
    if page_token:
        request["pageToken"] = page_token
    if winner_only:
        request["winner"] = True
    resp = mcp_call(TOOL, {"request": request}, token=token)
    if classify_result(resp) != "ok":
        return [], None, None, resp
    payload = extract_json(resp) or {}
    rows = payload.get("hackathon_write_ups") or []
    next_token = payload.get("next_page_token")
    total = payload.get("total_count")
    return rows, next_token, total, None


def _slug_from_url(url: str) -> str | None:
    """Roster rows carry the writeup URL, not its slug. The slug is the last segment."""
    if "/writeups/" not in url:
        return None
    return url.rstrip("/").rsplit("/", 1)[-1] or None


def normalize_row(
    row: dict, track_titles: dict[int, str], prize_titles: dict[int, str] | None = None
) -> dict:
    write_up = row.get("write_up") or {}
    team = row.get("team") or {}
    track_ids = row.get("hackathon_track_ids") or []
    prize_ids = row.get("awarded_hackathon_track_prize_ids") or []
    prize_titles = prize_titles or {}
    url = write_up.get("url") or ""
    return {
        "row_id": row.get("id"),
        "writeup_id": write_up.get("id"),
        "topic_id": write_up.get("topic_id"),
        "slug": write_up.get("slug") or _slug_from_url(url),
        "url": f"{KAGGLE_BASE}{url}" if url.startswith("/") else (url or None),
        "title": write_up.get("title"),
        "subtitle": write_up.get("subtitle"),
        "authors": write_up.get("authors"),
        "team_name": team.get("team_name"),
        "collaborators": write_up.get("collaborators") or [],
        "track_ids": track_ids,
        "track_titles": [track_titles.get(tid, str(tid)) for tid in track_ids],
        "awarded_prize_ids": prize_ids,
        "awarded_prizes": [prize_titles.get(pid, str(pid)) for pid in prize_ids],
        "template": bool(row.get("template")),
        "competition_id": row.get("competition_id"),
        "owner_host_user_id": row.get("owner_host_user_id"),
        "owner_judge_user_id": row.get("owner_judge_user_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--competition", required=True)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument(
        "--winner-only", action="store_true", help="Only writeups marked as winners"
    )
    parser.add_argument(
        "--array",
        action="store_true",
        help="Emit a single JSON object with a rows array instead of one object per line",
    )
    args = parser.parse_args()

    credentials.load_configured_env_file()
    token = resolve_token()

    tracks = fetch_track_list(args.competition, token)
    track_titles = track_titles_by_id(tracks)
    prize_titles = prize_titles_by_id(tracks)

    all_rows: list[dict] = []
    page_token: str | None = None
    total: int | None = None
    pages_fetched = 0
    failed: dict | None = None
    while True:
        rows, next_token, page_total, failed = fetch_writeups_page(
            args.competition,
            token,
            args.page_size,
            page_token,
            args.winner_only,
        )
        if failed is not None:
            break
        if page_total is not None:
            total = page_total
        for r in rows:
            all_rows.append(normalize_row(r, track_titles, prize_titles))
        pages_fetched += 1
        if not next_token or pages_fetched >= args.max_pages:
            break
        page_token = next_token

    if failed is not None and not all_rows:
        # Nothing was retrieved: report the denial or error, not an empty roster.
        return print_failure(failed, tool=TOOL, had_token=bool(token), competition=args.competition)

    truncated = failed is not None or (total is not None and len(all_rows) < total)

    # Writeup titles, subtitles, and collaborator names are participant-supplied
    # text: they stay inside one untrusted block.
    with untrusted.Block(source=SOURCE, tool=TOOL, competition=args.competition) as block:
        if args.array:
            block.write_json(
                {
                    "competition": args.competition,
                    "total_count": total,
                    "fetched": len(all_rows),
                    "truncated": truncated,
                    "rows": all_rows,
                },
                indent=2,
            )
        else:
            for row in all_rows:
                block.write_json(row)

    print(f"# fetched {len(all_rows)} writeups (total_count={total})", file=sys.stderr)
    if failed is not None:
        print_failure(failed, tool=TOOL, had_token=bool(token), competition=args.competition)
        print(
            f"error: stopped after {pages_fetched} page(s); the roster is incomplete",
            file=sys.stderr,
        )
        return 1
    if truncated:
        print(
            f"warning: roster is incomplete; raise --max-pages (now {args.max_pages})",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
