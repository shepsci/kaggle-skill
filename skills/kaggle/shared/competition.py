"""Competition facts and pages, read from the Kaggle MCP server.

``get_competition`` answers without a credential and holds what people ask
first: the metric, the deadline, the prize, the team size and the submission
limits. ``list_competition_pages`` holds the long text. Both are host-written,
so callers print what comes from here inside an untrusted-content block.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from typing import Any

from shared import mcp_client, script, text, untrusted

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
        help="Print this page as text. Part of the name is enough: --page eval",
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
            listing = [
                {"name": p.get("name"), "chars": len(p.get("content") or "")} for p in pages
            ]
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
