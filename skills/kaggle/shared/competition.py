"""Competition facts and pages, read from the Kaggle MCP server.

``get_competition`` answers without a credential and holds what people ask
first: the metric, the deadline, the prize, the team size and the submission
limits. ``list_competition_pages`` holds the long text. Both are host-written,
so callers print what comes from here inside an untrusted-content block.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any

from shared import kaggle_cli, mcp_client, script, text, untrusted

KAGGLE_BASE = "https://www.kaggle.com"
SOURCE = "kaggle-mcp"
FACTS_TOOL = "get_competition"
PAGES_TOOL = "list_competition_pages"
# A rules page runs to 37,000 characters, most of it standard terms that
# follow the competition-specific ones.
DEFAULT_MAX_CHARS = 12000

_CURRENCY_RE = re.compile(r"\b([A-Za-z]{3})$")


def money(value: Any) -> str:
    """Upper-case a trailing currency code: Kaggle returns ``50,000 Usd``."""
    return _CURRENCY_RE.sub(lambda m: m.group(1).upper(), str(value or "")).strip()


def url(slug: str) -> str:
    return f"{KAGGLE_BASE}/competitions/{slug}"


# -- facts ------------------------------------------------------------------


def fetch_facts(slug: str, token: str | None = None) -> mcp_client.Result:
    return mcp_client.request(FACTS_TOOL, {"competitionName": slug}, token=token)


def facts(slug: str, data: dict[str, Any]) -> dict[str, Any]:
    """The server's answer reduced to the fields a participant needs.

    The server leaves a field out when it is false or empty, so a missing
    flag reads as False here.
    """
    tags = [
        str(tag.get("name") or tag.get("ref") or "")
        for tag in data.get("tags") or []
        if isinstance(tag, dict)
    ]
    return {
        "slug": slug,
        "title": data.get("title") or slug,
        "description": data.get("description") or "",
        "url": data.get("url") or url(slug),
        "host": data.get("organization_name") or data.get("host_name") or "",
        "category": data.get("category") or "",
        "metric": data.get("evaluation_metric") or "",
        "reward": money(data.get("reward")),
        "deadline": data.get("deadline"),
        "entry_deadline": data.get("new_entrant_deadline"),
        "team_merger_deadline": data.get("merger_deadline"),
        "start": data.get("enabled_date"),
        "team_count": data.get("team_count"),
        "max_team_size": data.get("max_team_size"),
        "max_daily_submissions": data.get("max_daily_submissions"),
        "notebook_only": bool(data.get("is_kernels_submissions_only")),
        "awards_points": bool(data.get("awards_points")),
        "submissions_disabled": bool(data.get("submissions_disabled")),
        "tags": [tag for tag in tags if tag],
        "user_has_entered": bool(data.get("user_has_entered")),
        "user_rank": data.get("user_rank"),
    }


def _count(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "not given"


def fact_lines(info: dict[str, Any], now: datetime | None = None, signed_in: bool = False) -> list:
    """The facts as aligned ``label: value`` lines, most asked first."""
    now = now or text.now_utc()
    deadline = text.parse_time(info.get("deadline"))
    rows: list[tuple[str, str]] = [
        ("url", info["url"]),
        ("host", info["host"] or "not given"),
        ("category", info["category"] or "not given"),
        ("metric", info["metric"] or "not given (read the evaluation page)"),
        ("prize", info["reward"] or "not given"),
        ("deadline", text.when(info.get("deadline"), now)),
    ]
    if info.get("entry_deadline"):
        rows.append(("entry closes", text.when(info["entry_deadline"], now)))
    if info.get("team_merger_deadline"):
        rows.append(("team merger", text.when(info["team_merger_deadline"], now)))
    rows.append(("teams", _count(info.get("team_count"))))
    if info.get("max_team_size"):
        rows.append(("team size", f"up to {info['max_team_size']}"))
    if info["submissions_disabled"]:
        rows.append(("submissions", "closed"))
    elif info.get("max_daily_submissions"):
        rows.append(("submissions", f"{info['max_daily_submissions']} a day"))
    rows.append(
        ("submit with", "a notebook (code competition)" if info["notebook_only"] else "a file")
    )
    rows.append(("medals", "awards medals and points" if info["awards_points"] else "none"))
    if info["tags"]:
        rows.append(("tags", ", ".join(info["tags"][:8])))
    if signed_in:
        if info["user_has_entered"]:
            rank = info.get("user_rank")
            rows.append(("you", f"entered, rank {rank}" if rank else "entered"))
        else:
            rows.append(("you", "not entered"))
    if deadline is not None and deadline < now:
        rows.append(("state", "ended"))
    width = max(len(label) for label, _ in rows) + 1
    return [f"  {label + ':':<{width}} {value}" for label, value in rows]


# -- pages ------------------------------------------------------------------


def fetch_pages(slug: str, token: str | None = None, tool: str = PAGES_TOOL) -> mcp_client.Result:
    return mcp_client.request(tool, {"competitionName": slug}, token=token)


def pages_of(data: Any) -> list[dict[str, Any]]:
    pages = (data or {}).get("pages") if isinstance(data, dict) else None
    return [page for page in pages or [] if isinstance(page, dict)]


def find_page(pages: list[dict] | None, *needles: str) -> dict | None:
    """The page whose name is one of ``needles``, or else contains one. Case is ignored."""
    wanted = [needle.lower() for needle in needles if needle]
    named = [((page.get("name") or "").lower(), page) for page in pages or []]
    for name, page in named:
        if name in wanted:
            return page
    for name, page in named:
        if any(needle in name for needle in wanted):
            return page
    return None


def page_listing(pages: list[dict]) -> list[str]:
    """One line per page: its name, its length, and how it starts."""
    width = min(max([len(str(page.get("name") or "")) for page in pages] + [4]), 32)
    lines = []
    for page in pages:
        name = str(page.get("name") or "(unnamed)")
        content = page.get("content") or ""
        preview = text.shorten(text.collapse(text.to_text(content[:400])), 60)
        lines.append(f"  {name:<{width}}  {len(content):>7,} chars  {preview}")
    return lines


def page_text(page: dict, *, raw: bool = False, max_chars: int = 0) -> tuple[str, int]:
    """A page as text. Returns ``(text, characters left out)``."""
    content = page.get("content") or ""
    body = content if raw else text.to_text(content)
    if max_chars and len(body) > max_chars:
        return body[:max_chars].rstrip(), len(body) - max_chars
    return body, 0


def add_page_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--page",
        metavar="NAME",
        help='Print this page as text. Part of the name is enough, such as "eval"',
    )
    parser.add_argument("--all", action="store_true", help="Print every page as text")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print page content as Kaggle stores it (HTML or Markdown), not converted to text",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        metavar="N",
        help=f"Cut a page after N characters; 0 for no limit "
        f"(default: {DEFAULT_MAX_CHARS} with --page, no limit with --all)",
    )
    script.add_json(parser)
    script.add_full(parser)
    # The older name for the default listing.
    parser.add_argument("--summary", action="store_true", help=argparse.SUPPRESS)


def print_pages(
    args: argparse.Namespace, slug: str, result: mcp_client.Result, *, tool: str
) -> int:
    """Print the listing, one page, or every page of a pages answer."""
    pages = pages_of(result.data)
    indent = 2 if args.pretty else None
    attrs = {"source": SOURCE, "tool": tool, "competition": slug}

    if args.full:
        untrusted.emit_json(
            {"status": "ok", "competition": slug, "data": result.data}, indent=indent, **attrs
        )
        return script.EXIT_OK

    if args.page:
        page = find_page(pages, args.page)
        if page is None:
            print("error: no page matched the --page value. The pages are:", file=sys.stderr)
            names = "\n".join(str(p.get("name")) for p in pages) or "(none)"
            untrusted.emit_text(names, file=sys.stderr, stream="stderr", **attrs)
            return script.EXIT_FAILED
        selected = [page]
        max_chars = DEFAULT_MAX_CHARS if args.max_chars is None else args.max_chars
    elif args.all:
        selected = pages
        max_chars = args.max_chars or 0
    else:
        selected = []
        max_chars = 0

    if not selected:
        if args.json:
            listing = [{"name": p.get("name"), "chars": len(p.get("content") or "")} for p in pages]
            untrusted.emit_json({"competition": slug, "pages": listing}, indent=indent, **attrs)
            return script.EXIT_OK
        with untrusted.Block(**attrs) as block:
            block.write(f"Pages of {slug} ({len(pages)}):")
            for line in page_listing(pages):
                block.write(line)
        if pages:
            print("Read one with --page NAME; part of the name is enough.")
        return script.EXIT_OK

    texts = [page_text(p, raw=args.raw, max_chars=max_chars) for p in selected]
    if args.json:
        document = {
            "competition": slug,
            "pages": [
                {
                    "name": page.get("name"),
                    "chars": len(page.get("content") or ""),
                    "text": body,
                    "cut": cut,
                }
                for page, (body, cut) in zip(selected, texts)
            ],
        }
        untrusted.emit_json(document, indent=indent, **attrs)
        return script.EXIT_OK
    with untrusted.Block(**attrs) as block:
        for index, (page, (body, _)) in enumerate(zip(selected, texts)):
            block.write(("\n" if index else "") + f"## {page.get('name')}\n\n")
            block.write(body)
    for page, (body, cut) in zip(selected, texts):
        if cut:
            print(
                f"Cut '{page.get('name')}' at {len(body):,} of {len(body) + cut:,} characters. "
                "Add --max-chars 0 for the whole page."
            )
    return script.EXIT_OK


# -- submissions, leaderboard, medals -----------------------------------------

SUBMISSIONS_TOOL = "search_competition_submissions"
LEADERBOARD_TOOL = "get_competition_leaderboard"
LEADERBOARD_PAGE = 200  # the most rows the server returns in one call


def score_value(value: Any) -> float | None:
    """A score as a number, or None when it is empty or not a number."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def submission_row(raw: dict[str, Any]) -> dict[str, Any]:
    """One of your submissions as the server returned it, reduced to plain fields."""
    return {
        "ref": raw.get("ref"),
        "date": raw.get("date"),
        # The CLI spells the state "SubmissionStatus.COMPLETE"; the server "COMPLETE".
        "status": str(raw.get("status") or "").rsplit(".", 1)[-1].upper() or "UNKNOWN",
        "public_score": str(raw.get("public_score") or ""),
        "private_score": str(raw.get("private_score") or ""),
        "description": raw.get("description") or "",
        "file_name": raw.get("file_name") or "",
        "team_name": raw.get("team_name") or "",
        "submitted_by": raw.get("submitted_by") or "",
        "error": raw.get("error_description") or "",
    }


def fetch_submissions(
    slug: str, token: str | None = None, limit: int = 20
) -> tuple[list[dict[str, Any]], mcp_client.Result]:
    """Your latest submissions, newest first. Returns ``(rows, last result)``."""
    rows: list[dict[str, Any]] = []
    page_token = None
    result = mcp_client.request(
        SUBMISSIONS_TOOL, {"competitionName": slug, "pageSize": min(limit, 100)}, token=token
    )
    while result.ok and isinstance(result.data, dict):
        found = [r for r in result.data.get("submissions") or [] if isinstance(r, dict)]
        rows += [submission_row(r) for r in found]
        page_token = result.data.get("next_page_token")
        if not found or not page_token or len(rows) >= limit:
            break
        result = mcp_client.request(
            SUBMISSIONS_TOOL,
            {"competitionName": slug, "pageSize": min(limit, 100), "pageToken": page_token},
            token=token,
        )
    return rows[:limit], result


def fetch_leaderboard(
    slug: str, token: str | None = None, rows_wanted: int = LEADERBOARD_PAGE
) -> tuple[list[dict[str, Any]], bool, mcp_client.Result]:
    """The public leaderboard from the top. Returns ``(rows, more exist, last result)``.

    The server gives no rank, only the order: the rank is the position.
    """
    rows: list[dict[str, Any]] = []
    request: dict[str, Any] = {"competitionName": slug, "pageSize": LEADERBOARD_PAGE}
    result = mcp_client.request(LEADERBOARD_TOOL, request, token=token)
    more = False
    while result.ok and isinstance(result.data, dict):
        found = [r for r in result.data.get("submissions") or [] if isinstance(r, dict)]
        for row in found:
            rows.append(
                {
                    "rank": len(rows) + 1,
                    "team_id": row.get("team_id"),
                    "team": row.get("team_name") or "",
                    "score": str(row.get("score") or ""),
                    "date": row.get("submission_date"),
                }
            )
        page_token = result.data.get("next_page_token")
        more = bool(page_token)
        if not found or not page_token or len(rows) >= rows_wanted:
            break
        result = mcp_client.request(
            LEADERBOARD_TOOL, {**request, "pageToken": page_token}, token=token
        )
    return rows, more, result


def higher_is_better(rows: list[dict[str, Any]]) -> bool | None:
    """The direction of the metric, read from the order of the leaderboard.

    None when the rows do not show it: fewer than two scores, or all equal.
    """
    scores = [s for s in (score_value(row.get("score")) for row in rows) if s is not None]
    if len(scores) < 2 or scores[0] == scores[-1]:
        return None
    return scores[0] > scores[-1]


def best_submission(rows: list[dict[str, Any]], higher: bool | None) -> dict[str, Any] | None:
    """Your best scored submission, or None when the direction is unknown or nothing scored."""
    scored = [r for r in rows if score_value(r.get("public_score")) is not None]
    if not scored or higher is None:
        return None
    pick = max if higher else min
    return pick(scored, key=lambda r: score_value(r["public_score"]))


def medal_ranks(team_count: int) -> dict[str, int]:
    """The last rank that earns each medal, for a competition that awards medals.

    From https://www.kaggle.com/progression/competitions as read on 2026-10-02.
    Percentages are rounded down, and gold in a competition of 250 teams or
    more is the top 10 plus one for every 500 teams. The count that matters is
    the one at the end of the competition.
    """
    teams = max(int(team_count or 0), 0)
    if teams >= 1000:
        return {"gold": 10 + teams // 500, "silver": teams * 5 // 100, "bronze": teams // 10}
    if teams >= 250:
        return {"gold": 10 + teams // 500, "silver": 50, "bronze": 100}
    if teams >= 100:
        return {"gold": 10, "silver": teams * 20 // 100, "bronze": teams * 40 // 100}
    return {"gold": teams // 10, "silver": teams * 20 // 100, "bronze": teams * 40 // 100}


def submission_limits(slug: str) -> dict[str, Any] | None:
    """Kaggle's own count of submissions, from the Kaggle CLI.

    Returns ``{"numTotal": all so far, "numAllowedNow": left today}``, or
    None when the CLI is not installed or did not answer. The MCP server has
    no tool for this.
    """
    if not kaggle_cli.installed():
        return None
    result = kaggle_cli.run(["competitions", "submission-limits", slug, "--json"], timeout=60)
    if result.returncode != 0:
        return None
    start, end = result.stdout.find("{"), result.stdout.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        limits = json.loads(result.stdout[start : end + 1])
    except ValueError:
        return None
    return limits if isinstance(limits, dict) and "numAllowedNow" in limits else None


def seconds(value: Any) -> float | None:
    """A duration such as ``119679.779s`` as seconds."""
    try:
        return float(str(value).strip().rstrip("s"))
    except (TypeError, ValueError):
        return None
