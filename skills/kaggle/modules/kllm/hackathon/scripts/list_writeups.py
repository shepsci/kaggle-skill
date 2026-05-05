#!/usr/bin/env python3
"""Enumerate writeup submissions for a Kaggle hackathon.

Calls `list_hackathon_write_ups` paginated, then `list_hackathon_tracks` once
to resolve numeric track ids to titles. Outputs one JSON object per writeup
row to stdout (or a single JSON array with --array).

Does NOT call `get_hackathon_write_up` — it's known-broken (see
references/hackathon-endpoints.md). Use fetch_writeup.py for full-body fetches.
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

DEFAULT_PAGE_SIZE = 50


def fetch_tracks(competition: str, token: str) -> dict[int, str]:
    resp = mcp_call(
        "list_hackathon_tracks",
        {"request": {"competitionName": competition}},
        token=token,
    )
    if classify_result(resp) != "ok":
        return {}
    payload = extract_json(resp) or {}
    tracks = payload.get("tracks") or []
    return {t.get("id"): t.get("title", "") for t in tracks if t.get("id") is not None}


def fetch_writeups_page(
    competition: str,
    token: str,
    page_size: int,
    page_token: str | None,
    winner_only: bool,
) -> tuple[list[dict], str | None, int | None]:
    request = {"competitionName": competition, "pageSize": page_size}
    if page_token:
        request["pageToken"] = page_token
    if winner_only:
        request["winnerStatus"] = "WINNER"
    resp = mcp_call("list_hackathon_write_ups", {"request": request}, token=token)
    if classify_result(resp) != "ok":
        return [], None, None
    payload = extract_json(resp) or {}
    rows = payload.get("hackathon_write_ups") or []
    next_token = payload.get("next_page_token")
    total = payload.get("total_count")
    return rows, next_token, total


def normalize_row(row: dict, track_titles: dict[int, str]) -> dict:
    write_up = row.get("write_up") or {}
    track_ids = row.get("hackathon_track_ids") or []
    return {
        "row_id": row.get("id"),
        "writeup_id": write_up.get("id"),
        "topic_id": write_up.get("topic_id"),
        "slug": write_up.get("slug"),
        "title": write_up.get("title"),
        "subtitle": write_up.get("subtitle"),
        "collaborators": write_up.get("collaborators") or [],
        "track_ids": track_ids,
        "track_titles": [track_titles.get(tid, str(tid)) for tid in track_ids],
        "competition_id": row.get("competition_id"),
        "owner_host_user_id": row.get("owner_host_user_id"),
        "owner_judge_user_id": row.get("owner_judge_user_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--competition", required=True)
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--winner-only", action="store_true")
    parser.add_argument("--array", action="store_true",
                        help="Emit a single JSON array instead of one object per line")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env", Path.home() / ".env")
    token = resolve_token()
    if not token:
        print("error: no Kaggle token found", file=sys.stderr)
        return 2

    track_titles = fetch_tracks(args.competition, token)

    all_rows: list[dict] = []
    page_token: str | None = None
    total: int | None = None
    pages_fetched = 0
    while True:
        rows, next_token, page_total = fetch_writeups_page(
            args.competition, token, args.page_size, page_token, args.winner_only,
        )
        if page_total is not None:
            total = page_total
        for r in rows:
            all_rows.append(normalize_row(r, track_titles))
        pages_fetched += 1
        if not next_token or pages_fetched >= args.max_pages:
            break
        page_token = next_token

    # Writeup titles, subtitles, and collaborator names are participant-supplied
    # text — treat as untrusted to prevent prompt injection from row contents.
    print(f'<untrusted-content source="kaggle-mcp" tool="list_hackathon_write_ups" '
          f'competition="{args.competition}">')
    if args.array:
        print(json.dumps({
            "competition": args.competition,
            "total_count": total,
            "rows": all_rows,
        }, indent=2))
    else:
        for row in all_rows:
            print(json.dumps(row))
        print(f"# fetched {len(all_rows)} writeups (total_count={total})", file=sys.stderr)
    print("</untrusted-content>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
