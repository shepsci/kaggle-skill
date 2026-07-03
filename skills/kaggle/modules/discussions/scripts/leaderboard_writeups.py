#!/usr/bin/env python3
"""Discover leaderboard solution writeup links for a Kaggle competition."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

KAGGLE_BASE = "https://www.kaggle.com"


def resolve_token() -> str | None:
    token = os.environ.get("KAGGLE_API_TOKEN")
    if token:
        return token.strip()
    token_path = Path.home() / ".kaggle" / "access_token"
    if token_path.exists():
        return token_path.read_text(encoding="utf-8").strip()
    return None


def competition_slug(value: str) -> str:
    """Normalize a competition slug or URL to the plain competition slug."""
    text = value.strip()
    parsed = urlparse(text)
    path = parsed.path if parsed.scheme else text
    parts = [part for part in path.split("/") if part]
    if "competitions" in parts:
        idx = parts.index("competitions")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if "c" in parts:
        idx = parts.index("c")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return parts[-1] if parts else text


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _rank_value(row: dict[str, Any]) -> int | None:
    raw = _first_present(
        row,
        (
            "privateLeaderboardRank",
            "publicLeaderboardRank",
            "rank",
            "teamRank",
            "privateRank",
            "publicRank",
        ),
    )
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _absolute_kaggle_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{KAGGLE_BASE}{url}"
    return f"{KAGGLE_BASE}/{url}"


def extract_writeup_links(payload: dict[str, Any], top_k: int | None = None) -> list[dict[str, Any]]:
    """Extract and rank solution writeup links from a Kaggle leaderboard payload."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _iter_dicts(payload):
        url = _first_present(
            item,
            (
                "solutionWriteUpUrl",
                "solutionWriteupUrl",
                "solution_write_up_url",
                "solutionUrl",
                "writeupUrl",
            ),
        )
        if not isinstance(url, str) or not url.strip():
            continue
        absolute_url = _absolute_kaggle_url(url.strip())
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        rank = _rank_value(item)
        rows.append(
            {
                "rank": rank,
                "team_name": _first_present(item, ("teamName", "team_name", "name", "displayName")),
                "team_id": _first_present(item, ("teamId", "team_id", "id")),
                "score": _first_present(item, ("score", "privateScore", "publicScore")),
                "writeup_url": absolute_url,
            }
        )
    rows.sort(key=lambda row: (row["rank"] is None, row["rank"] if row["rank"] is not None else 999999))
    return rows[:top_k] if top_k else rows


def _extract_competition_id(payload: dict[str, Any]) -> int:
    for item in _iter_dicts(payload):
        if "competitionId" in item:
            return int(item["competitionId"])
        if "competition" in item and isinstance(item["competition"], dict):
            comp = item["competition"]
            if "id" in comp:
                return int(comp["id"])
    raise ValueError("could not find competition id in Kaggle response")


def _post_json(session: requests.Session, path: str, body: dict[str, Any]) -> dict[str, Any]:
    resp = session.post(f"{KAGGLE_BASE}{path}", json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_leaderboard_payload(slug: str, token: str) -> dict[str, Any]:
    """Fetch leaderboard JSON using Kaggle's authenticated web API."""
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    home = session.get(KAGGLE_BASE, timeout=30)
    home.raise_for_status()
    xsrf = session.cookies.get("XSRF-TOKEN")
    if xsrf:
        session.headers["X-XSRF-TOKEN"] = unquote(xsrf)

    competition_payload = _post_json(
        session,
        "/api/i/competitions.CompetitionService/GetCompetition",
        {"competitionName": slug},
    )
    competition_id = _extract_competition_id(competition_payload)
    return _post_json(
        session,
        "/api/i/competitions.LeaderboardService/GetLeaderboard",
        {"competitionId": competition_id},
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("competition", help="Competition slug or Kaggle competition URL")
    parser.add_argument("--top-k", type=int, default=20, help="Return only the first K links")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Emit bare JSON for pipelines instead of untrusted-content wrapping",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    slug = competition_slug(args.competition)
    token = resolve_token()
    if not token:
        print("error: no Kaggle token found", file=sys.stderr)
        return 2

    try:
        payload = fetch_leaderboard_payload(slug, token)
    except requests.RequestException as exc:
        print(f"error: Kaggle request failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = {
        "competition": slug,
        "source": "leaderboard",
        "writeups": extract_writeup_links(payload, top_k=args.top_k),
    }
    text = json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty)
    if args.raw_json:
        print(text)
    else:
        marker_slug = html.escape(slug, quote=True)
        print(
            '<untrusted-content source="kaggle-web" '
            f'tool="leaderboard_writeups" competition="{marker_slug}">'
        )
        print(text)
        print("</untrusted-content>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
