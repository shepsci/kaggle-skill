#!/usr/bin/env python3
"""Find the solution writeups of a Kaggle competition, by leaderboard rank.

    leaderboard_writeups.py titanic
    leaderboard_writeups.py https://www.kaggle.com/competitions/titanic --top 10 --preview
    leaderboard_writeups.py arc-prize-2025 --fallback-search --preview

Teams can link a solution writeup to their leaderboard row. This script reads
the public leaderboard from kaggle.com and lists those links in rank order.
--preview adds the title and the first lines of each writeup page. When the
leaderboard holds no links, --fallback-search looks for writeup-like
discussion topics instead.

No credential and no Python package are needed for a public leaderboard. A
token, when one is configured, is sent to www.kaggle.com only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

KAGGLE_BASE = "https://www.kaggle.com"
MAX_PREVIEW_REDIRECTS = 3
SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, net, script, untrusted  # noqa: E402
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
    return script.competition_slug(value)


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


class KaggleRequestFailed(RuntimeError):
    """kaggle.com did not give a usable answer. ``detail`` is safe to print."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def is_kaggle_https_url(url: str) -> bool:
    """True only for an https URL whose destination is kaggle.com."""
    return net.is_kaggle_url(url)


def _get(url: str, *, headers: dict[str, str] | None = None, opener: Any = None) -> net.Response:
    """GET a kaggle.com URL. Redirects are followed by hand, so every hop is checked.

    Raises ValueError when a hop leaves kaggle.com or there are too many.
    """
    for _ in range(MAX_PREVIEW_REDIRECTS + 1):
        response = net.request(
            "GET", net.kaggle_url(url), headers=headers, opener=opener, timeout=30
        )
        if not response.location:
            return response
        url = response.location
    raise ValueError("too many redirects")


_WRITEUP_PATH_RE = re.compile(r"/competitions/([^/?#]+)/writeups/([^/?#]+)")


def writeup_body_preview(url: str, max_chars: int = 360) -> dict[str, str] | None:
    """A preview from the writeup itself, read from the MCP server with no credential.

    A writeup page shows little before its scripts run (often only the title),
    so the body is read where it is kept. None when the URL is not a writeup
    address or the server has no body for it.
    """
    match = _WRITEUP_PATH_RE.search(url)
    if not match or not net.is_kaggle_url(url):
        return None
    resp = mcp_call(
        "get_writeup_by_slug",
        {"request": {"competitionName": match.group(1), "slug": match.group(2)}},
        token="",
    )
    try:
        payload = json.loads(mcp_extract_text(resp) or "")
    except (TypeError, ValueError):
        return None
    message = payload.get("message") if isinstance(payload, dict) else None
    body = message.get("raw_markdown") if isinstance(message, dict) else None
    if not body:
        return None
    title = _collapse_text(str(payload.get("title") or ""))
    subtitle = _collapse_text(str(payload.get("subtitle") or ""))
    return {
        "title": f"{title}: {subtitle}" if title and subtitle else title or "Kaggle writeup",
        "excerpt": competition.page_summary({"content": body}, limit=max_chars),
    }


def fetch_writeup_preview(url: str, max_chars: int = 360) -> dict[str, str]:
    """Preview one Kaggle writeup without credentials: its body, else its page."""
    from_body = writeup_body_preview(url, max_chars=max_chars)
    if from_body and from_body["excerpt"]:
        return from_body
    response = _get(url, headers={"Accept": "text/html,application/xhtml+xml"})
    if response.status != 200:
        raise KaggleRequestFailed(f"HTTP {response.status}")
    return extract_writeup_preview(response.text, max_chars=max_chars)


def add_writeup_previews(
    rows: list[dict[str, Any]],
    token: str | None = None,
    max_chars: int = 360,
) -> list[dict[str, Any]]:
    """Attach compact page previews to leaderboard writeup links.

    ``token`` is accepted for backward compatibility and is not used: the
    preview requests carry no Authorization header.
    """
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
                item["preview"] = fetch_writeup_preview(url, max_chars=max_chars)
            except ValueError as exc:
                item["preview_skipped"] = str(exc)
            except KaggleRequestFailed as exc:
                item["preview_error"] = exc.detail
            except net.RequestError as exc:
                item["preview_error"] = exc.detail or exc.kind
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
    answer = mcp_extract_text(resp)
    try:
        payload = json.loads(answer)
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


def _post_json(opener: Any, path: str, body: dict[str, Any], headers: dict) -> dict[str, Any]:
    response = net.request(
        "POST",
        f"{KAGGLE_BASE}{path}",
        headers=headers,
        data=json.dumps(body).encode("utf-8"),
        opener=opener,
        timeout=60,
    )
    if response.status != 200:
        raise KaggleRequestFailed(f"HTTP {response.status}")
    try:
        payload = response.json()
    except ValueError:
        raise KaggleRequestFailed("the answer was not JSON") from None
    if not isinstance(payload, dict):
        raise KaggleRequestFailed("the answer was not a JSON object")
    return payload


def fetch_leaderboard_payload(slug: str, token: str | None = None) -> dict[str, Any]:
    """Fetch leaderboard JSON from Kaggle's web API.

    Public leaderboards answer without credentials. The token, when there is
    one, goes only to www.kaggle.com.
    """
    opener = net.make_opener(cookies=True)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # The first request collects the cookie that the two calls below must echo.
    home = _get(KAGGLE_BASE, headers=headers, opener=opener)
    if home.status != 200:
        raise KaggleRequestFailed(f"HTTP {home.status}")
    post_headers = {**headers, "Content-Type": "application/json"}
    xsrf = net.cookie(opener, "XSRF-TOKEN")
    if xsrf:
        post_headers["X-XSRF-TOKEN"] = unquote(xsrf)

    competition_payload = _post_json(
        opener,
        "/api/i/competitions.CompetitionService/GetCompetition",
        {"competitionName": slug},
        post_headers,
    )
    competition_id = _extract_competition_id(competition_payload)
    leaderboard = _post_json(
        opener,
        "/api/i/competitions.LeaderboardService/GetLeaderboard",
        {"competitionId": competition_id},
        post_headers,
    )
    leaderboard["_competition_id"] = competition_id
    return leaderboard


def text_lines(result: dict[str, Any]) -> list[str]:
    """The result as a few lines per team."""
    slug = result["competition"]
    writeups = result["writeups"]
    lines: list[str] = []
    if writeups and result["source"] == "leaderboard":
        lines.append(f"{len(writeups)} solution writeups linked from the {slug} leaderboard:")
    elif writeups:
        lines.append(
            f"The {slug} leaderboard links no writeups. "
            f"{len(writeups)} discussion topics that look like writeups, found by search:"
        )
    elif result["source"] == "content-search-fallback":
        lines.append(
            f"The {slug} leaderboard links no solution writeups, and a search of its "
            "discussions found none."
        )
    else:
        lines.append(f"The {slug} leaderboard links no solution writeups.")
    for row in writeups:
        rank = f"#{row['rank']}" if row.get("rank") else "-"
        score = f" · score {row['score']}" if row.get("score") not in (None, "") else ""
        lines.append(f"  {rank:>5}  {row.get('team_name') or '(no team name)'}{score}")
        lines.append(f"         {row['writeup_url']}")
        preview = row.get("preview")
        if isinstance(preview, dict):
            title, excerpt = preview.get("title", ""), preview.get("excerpt", "")
            # A page that shows nothing before its scripts run gives only its title.
            shown = title if excerpt in ("", title) else f"{title}: {excerpt}"
            lines.append(f"         {shown}")
        elif row.get("preview_error") or row.get("preview_skipped"):
            reason = row.get("preview_error") or row.get("preview_skipped")
            lines.append(f"         (no preview: {reason})")
    top = result.get("leaderboard_top") or []
    if top and not writeups:
        lines.append(f"Top of the leaderboard ({len(top)} rows):")
        for row in top:
            rank = f"#{row['rank']}" if row.get("rank") else "-"
            lines.append(f"  {rank:>5}  {row.get('team_name') or ''} · {row.get('score') or ''}")
    return lines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find the solution writeups of a Kaggle competition, by leaderboard rank.",
        epilog="No credential is needed for a public leaderboard.",
    )
    script.add_competition(parser)
    parser.add_argument(
        "--top",
        "--top-k",
        dest="top_k",
        type=script.positive_int,
        default=20,
        metavar="N",
        help="Print at most N writeups (default: 20)",
    )
    parser.add_argument(
        "--preview", action="store_true", help="Add the title and first lines of each writeup"
    )
    parser.add_argument(
        "--preview-chars", type=int, default=360, help="Longest preview, in characters"
    )
    parser.add_argument(
        "--fallback-search",
        action="store_true",
        help="When the leaderboard links no writeups, search public discussions for them",
    )
    script.add_json(parser)
    # Older releases printed bare JSON here; it now means --json, inside a block.
    parser.add_argument("--raw-json", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    (args.competition,) = script.positionals(parser, args)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    slug = args.competition
    credentials.load_configured_env_file()
    token = resolve_token()

    try:
        payload = fetch_leaderboard_payload(slug, token)
    except net.RequestError as exc:
        # Only the kind of failure is printed: a library message can quote a header.
        print(f"error: the request to Kaggle failed ({exc.detail or exc.kind})", file=sys.stderr)
        if exc.kind == "certificate":
            print(net.CERTIFICATE_HINT, file=sys.stderr)
        return 1
    except KaggleRequestFailed as exc:
        print(f"error: the request to Kaggle failed ({exc.detail})", file=sys.stderr)
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
        result["leaderboard_top"] = extract_ranked_teams(payload, top_k=min(args.top_k, 10))
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
    attrs = {"source": "kaggle-web", "tool": "leaderboard_writeups", "competition": slug}
    if args.json or args.raw_json:
        untrusted.emit_json(result, indent=indent, sort_keys=args.pretty, **attrs)
    else:
        with untrusted.Block(**attrs) as block:
            for line in text_lines(result):
                block.write(line)
        if not result["writeups"] and not args.fallback_search:
            print("Add --fallback-search to look for writeups among the discussion topics.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
