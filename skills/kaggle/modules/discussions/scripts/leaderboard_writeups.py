#!/usr/bin/env python3
"""Discover leaderboard solution writeup links for a Kaggle competition."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from urllib3.util import parse_url

KAGGLE_BASE = "https://www.kaggle.com"
KAGGLE_HOSTS = {"www.kaggle.com", "kaggle.com"}
MAX_PREVIEW_REDIRECTS = 3
SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, untrusted  # noqa: E402
from shared.mcp_client import extract_text as mcp_extract_text  # noqa: E402
from shared.mcp_client import mcp_call  # noqa: E402

HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE | re.DOTALL)
GENERIC_META_PREFIXES = ("Discover what actually works in AI.",)
BLOCK_BREAK_RE = re.compile(
    r"<\s*(br|/p|/div|/li|/h[1-6]|/article|/section)\b[^>]*>",
    re.IGNORECASE,
)


def resolve_token() -> str | None:
    """Bearer token from the shared resolver, or None for anonymous use."""
    return credentials.bearer_token() or None


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


def _score_value(row: dict[str, Any]) -> Any:
    return _first_present(row, ("score", "displayScore", "privateScore", "publicScore"))


def _absolute_kaggle_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{KAGGLE_BASE}{url}"
    return f"{KAGGLE_BASE}/{url}"


def extract_writeup_links(
    payload: dict[str, Any], top_k: int | None = None
) -> list[dict[str, Any]]:
    """Extract and rank solution writeup links from a Kaggle leaderboard payload."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    leaderboard_rows = payload.get("privateLeaderboard") or payload.get("publicLeaderboard") or []
    leaderboard_by_team = {
        item.get("teamId"): item
        for item in leaderboard_rows
        if isinstance(item, dict) and item.get("teamId") is not None
    }
    for team in payload.get("teams", []):
        if not isinstance(team, dict):
            continue
        url = _first_present(
            team,
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
        leaderboard_row = leaderboard_by_team.get(team.get("teamId"), {})
        rows.append(
            {
                "rank": _rank_value(leaderboard_row) or _rank_value(team),
                "team_name": _first_present(team, ("teamName", "team_name", "name", "displayName")),
                "team_id": _first_present(team, ("teamId", "team_id", "id")),
                "score": _score_value(leaderboard_row) or _score_value(team),
                "writeup_url": absolute_url,
            }
        )

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
                "score": _score_value(item),
                "writeup_url": absolute_url,
            }
        )
    rows.sort(
        key=lambda row: (row["rank"] is None, row["rank"] if row["rank"] is not None else 999999)
    )
    return rows[:top_k] if top_k else rows


def extract_ranked_teams(payload: dict[str, Any], top_k: int | None = None) -> list[dict[str, Any]]:
    """Extract top leaderboard rows even when Kaggle exposes no writeup URLs."""
    teams_by_id: dict[Any, dict[str, Any]] = {}
    for team in payload.get("teams", []):
        if isinstance(team, dict) and "teamId" in team:
            teams_by_id[team["teamId"]] = team

    rows: list[dict[str, Any]] = []
    leaderboard_rows = payload.get("privateLeaderboard") or payload.get("publicLeaderboard") or []
    for row in leaderboard_rows:
        if not isinstance(row, dict):
            continue
        team = teams_by_id.get(row.get("teamId"), {})
        rows.append(
            {
                "rank": _rank_value(row),
                "team_name": _first_present(team, ("teamName", "displayName", "name")),
                "team_id": row.get("teamId"),
                "score": _first_present(
                    row, ("displayScore", "score", "privateScore", "publicScore")
                ),
                "submission_id": row.get("submissionId"),
            }
        )
    rows.sort(
        key=lambda row: (row["rank"] is None, row["rank"] if row["rank"] is not None else 999999)
    )
    return rows[:top_k] if top_k else rows


def _extract_competition_id(payload: dict[str, Any]) -> int:
    for item in _iter_dicts(payload):
        if "competitionId" in item:
            return int(item["competitionId"])
        if "id" in item and "competitionName" in item:
            return int(item["id"])
        if "competition" in item and isinstance(item["competition"], dict):
            comp = item["competition"]
            if "id" in comp:
                return int(comp["id"])
    raise ValueError("could not find competition id in Kaggle response")


def _collapse_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _strip_html(value: str) -> str:
    without_scripts = SCRIPT_STYLE_RE.sub(" ", value)
    with_breaks = BLOCK_BREAK_RE.sub("\n", without_scripts)
    return _collapse_text(HTML_TAG_RE.sub(" ", with_breaks))


def _meta_description(html_text: str) -> str:
    for tag_match in META_TAG_RE.finditer(html_text):
        tag = tag_match.group(0)
        attrs = {
            key.lower(): value
            for key, _quote, value in re.findall(r'([A-Za-z:-]+)=(["\'])(.*?)\2', tag, re.DOTALL)
        }
        kind = (attrs.get("name") or attrs.get("property") or "").lower()
        if kind in {"description", "og:description", "twitter:description"} and attrs.get(
            "content"
        ):
            return _collapse_text(attrs["content"])
    return ""


def extract_writeup_preview(html_text: str, max_chars: int = 360) -> dict[str, str]:
    """Extract a small preview from a Kaggle writeup page.

    Returned text is data from Kaggle and must stay inside the caller's
    untrusted-content boundary.
    """
    title_match = TITLE_RE.search(html_text)
    raw_title = _strip_html(title_match.group(1)) if title_match else "Kaggle writeup"
    title = raw_title
    if title.endswith(" | Kaggle"):
        title = title.removesuffix(" | Kaggle")
    meta_description = _meta_description(html_text)
    body = _strip_html(html_text)
    excerpt = meta_description or body
    if not meta_description:
        # Strip leading page-title copies (including any " | Kaggle" suffix) so
        # the generic-boilerplate check below sees the true start of the body.
        stripped = True
        while stripped:
            stripped = False
            for known_prefix in (raw_title, title):
                if known_prefix and excerpt.startswith(known_prefix):
                    excerpt = excerpt[len(known_prefix) :].strip(" -|")
                    stripped = True
                    break
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "…"
    if not excerpt or any(excerpt.startswith(prefix) for prefix in GENERIC_META_PREFIXES):
        excerpt = title
    return {"title": title, "excerpt": excerpt}


def is_kaggle_https_url(url: str) -> bool:
    """True only for an https URL whose real destination is kaggle.com.

    The check runs on the URL as requests will send it, because
    ``urllib.parse`` and requests disagree about inputs such as
    ``https://evil.example\\@www.kaggle.com/x``.
    """
    if "\\" in url:
        return False
    try:
        prepared = requests.Request("GET", url).prepare().url or ""
        parts = parse_url(prepared)
    except (requests.RequestException, ValueError):
        return False
    host = (parts.host or "").lower()
    return parts.scheme == "https" and parts.auth is None and host in KAGGLE_HOSTS


def fetch_writeup_preview(
    session: requests.Session,
    url: str,
    max_chars: int = 360,
) -> dict[str, str]:
    """Fetch and preview one Kaggle writeup page.

    Previews are fetched without credentials and only from kaggle.com.
    Redirects are followed by hand so every hop gets the same check.
    """
    for _ in range(MAX_PREVIEW_REDIRECTS + 1):
        if not is_kaggle_https_url(url):
            raise ValueError("not an https kaggle.com URL")
        resp = session.get(url, timeout=30, allow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            url = requests.compat.urljoin(url, resp.headers["Location"])
            continue
        resp.raise_for_status()
        return extract_writeup_preview(resp.text, max_chars=max_chars)
    raise ValueError("too many redirects")


def add_writeup_previews(
    rows: list[dict[str, Any]],
    token: str | None = None,
    max_chars: int = 360,
) -> list[dict[str, Any]]:
    """Attach compact page previews to leaderboard writeup links.

    ``token`` is accepted for backward compatibility and is not used: the
    preview requests carry no Authorization header.
    """
    session = requests.Session()
    session.headers.update({"Accept": "text/html,application/xhtml+xml"})
    previewed: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        existing_preview = item.get("preview")
        if isinstance(existing_preview, dict) and existing_preview.get("excerpt"):
            previewed.append(item)
            continue
        url = item.get("writeup_url")
        if isinstance(url, str) and url:
            try:
                item["preview"] = fetch_writeup_preview(session, url, max_chars=max_chars)
            except ValueError as exc:
                item["preview_skipped"] = str(exc)
            except requests.RequestException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                item["preview_error"] = f"HTTP {status}" if status else type(exc).__name__
        previewed.append(item)
    return previewed


def _preview_from_search_document(doc: dict[str, Any], max_chars: int) -> dict[str, str]:
    discussion = doc.get("discussion_document") or {}
    message = discussion.get("message_stripped") or discussion.get("message_markdown") or ""
    excerpt = _collapse_text(str(message))
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "…"
    return {
        "title": _collapse_text(str(doc.get("title") or "Kaggle discussion")),
        "excerpt": excerpt,
    }


def _writeup_search_query(slug: str) -> str:
    if "arc-agi-3" in slug.lower():
        return "ARC-AGI-3 solution"
    return f"{slug.replace('-', ' ')} solution writeup"


def search_public_writeup_topics(
    slug: str,
    competition_id: int,
    token: str,
    top_k: int,
    max_chars: int = 360,
) -> list[dict[str, Any]]:
    """Search Kaggle for public writeup-like discussion topics for a competition.

    Public content search answers without credentials, so ``token`` may be empty.
    """
    query = _writeup_search_query(slug)
    resp = mcp_call(
        "search_content",
        {
            "request": {
                "maxPageSize": max(10, top_k * 4),
                "filters": {
                    "query": query,
                    "documentTypes": ["Topic", "Comment"],
                    "documentTypesSetter": ["Topic", "Comment"],
                    "competitionIds": [competition_id],
                    "competitionIdsSetter": [competition_id],
                    "privacy": "Public",
                    "listType": "LandingList",
                    "ownerType": "Unspecified",
                },
                "canonicalOrderByNullable": "DateUpdated",
                "discussionsOrderByNullable": "LastTopicCommentDate",
            }
        },
        token=token,
        timeout=30,
    )
    text = mcp_extract_text(resp)
    try:
        payload = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return []

    documents = [doc for doc in payload.get("documents", []) if isinstance(doc, dict)]
    documents.sort(
        key=lambda doc: (
            doc.get("document_type") != "TOPIC",
            "writeup" not in str(doc.get("title", "")).lower()
            and "write-up" not in str(doc.get("title", "")).lower(),
        )
    )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in documents:
        url = (doc.get("enriched_info") or {}).get("url")
        if not isinstance(url, str) or "/discussion/" not in url:
            continue
        absolute_url = _absolute_kaggle_url(url)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        owner = doc.get("owner_user") or {}
        rows.append(
            {
                "rank": None,
                "team_name": owner.get("display_name"),
                "source": "content-search",
                "writeup_url": absolute_url,
                "preview": _preview_from_search_document(doc, max_chars=max_chars),
            }
        )
        if len(rows) >= top_k:
            break
    return rows


def _post_json(session: requests.Session, path: str, body: dict[str, Any]) -> dict[str, Any]:
    resp = session.post(f"{KAGGLE_BASE}{path}", json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_leaderboard_payload(slug: str, token: str | None = None) -> dict[str, Any]:
    """Fetch leaderboard JSON from Kaggle's web API.

    Public leaderboards answer without credentials. The token, when there is
    one, goes only to www.kaggle.com.
    """
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
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
    leaderboard = _post_json(
        session,
        "/api/i/competitions.LeaderboardService/GetLeaderboard",
        {"competitionId": competition_id},
    )
    leaderboard["_competition_id"] = competition_id
    return leaderboard


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("competition", help="Competition slug or Kaggle competition URL")
    parser.add_argument("--top-k", type=int, default=20, help="Return only the first K links")
    parser.add_argument("--preview", action="store_true", help="Fetch title/excerpt previews")
    parser.add_argument(
        "--preview-chars", type=int, default=360, help="Maximum preview excerpt length"
    )
    parser.add_argument(
        "--fallback-search",
        action="store_true",
        help="Search public Kaggle discussions when the leaderboard exposes no writeup URLs",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Emit bare JSON for a program to parse. The values are still Kaggle-supplied data",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    slug = competition_slug(args.competition)
    credentials.load_configured_env_file()
    token = resolve_token()

    try:
        payload = fetch_leaderboard_payload(slug, token)
    except requests.RequestException as exc:
        # The exception text is not printed: for a malformed header it quotes the header.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        detail = f"HTTP {status}" if status else type(exc).__name__
        print(f"error: the request to Kaggle failed ({detail})", file=sys.stderr)
        return 1
    except ValueError:
        print("error: Kaggle's answer did not contain the competition", file=sys.stderr)
        return 1

    writeups = extract_writeup_links(payload, top_k=args.top_k)
    result: dict[str, Any] = {
        "competition": slug,
        "source": "leaderboard",
        "writeups": writeups,
    }
    if not writeups:
        result["leaderboard_top"] = extract_ranked_teams(payload, top_k=args.top_k)
    if args.fallback_search and not writeups and isinstance(payload.get("_competition_id"), int):
        result["source"] = "content-search-fallback"
        result["note"] = (
            "Kaggle's leaderboard response did not expose solutionWriteUpUrl fields; "
            "public writeup-like discussion topics were retrieved by content search."
        )
        result["writeups"] = search_public_writeup_topics(
            slug,
            payload["_competition_id"],
            token or "",
            top_k=args.top_k,
            max_chars=args.preview_chars,
        )
    if args.preview:
        result["writeups"] = add_writeup_previews(
            result["writeups"],
            token,
            max_chars=args.preview_chars,
        )
    indent = 2 if args.pretty else None
    if args.raw_json:
        print(untrusted.dumps(result, indent=indent, sort_keys=args.pretty))
    else:
        untrusted.emit_json(
            result,
            source="kaggle-web",
            tool="leaderboard_writeups",
            competition=slug,
            indent=indent,
            sort_keys=args.pretty,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
