#!/usr/bin/env python3
"""List recent and running Kaggle competitions: two short lines each, with the metric.

    list_competitions.py                         the last 30 days
    list_competitions.py --days 90 --category featured,research
    list_competitions.py --mine                  the competitions you have entered
    list_competitions.py --search "llm" --json

Reads `search_competitions` on the Kaggle MCP server, which needs a credential
(an API token or `kaggle auth login`). No Python package is needed.

Each competition's first line is its deadline and title, with the last day
to join (or "submissions closed"); the second its slug, category, teams,
prize and metric.

Community competitions with fewer than ten teams are left out unless
--min-teams says otherwise: most are class exercises. With
KAGGLE_SKILL_HIDE_ACCOUNT=1 the competitions you have entered are not marked.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, mcp_client, script, text, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = "search_competitions"

# The values `search_competitions` takes for `category`.
CATEGORIES = {
    "featured": "featured",
    "research": "research",
    "playground": "playground",
    "getting-started": "gettingStarted",
    "recruitment": "recruitment",
    "masters": "masters",
    "community": "community",
}
PAGE_SIZE = 20  # fixed by the server
PAGES_PER_QUERY = 2
MAX_PAGES_MINE = 10
COMMUNITY_MIN_TEAMS = 10
CALL_DELAY = 0.2


def extract_slug(ref: str) -> str:
    """The slug from the ``ref`` field, which is the competition URL."""
    return str(ref).strip("/").split("/")[-1]


def to_row(comp: dict) -> dict:
    """One competition as the server returned it, reduced to plain fields."""
    slug = extract_slug(comp.get("ref") or comp.get("url") or "")
    tags = [str(t.get("name") or t.get("ref") or "") for t in comp.get("tags") or [] if t]
    return {
        "slug": slug,
        "title": comp.get("title") or "",
        "description": comp.get("description") or "",
        "category": comp.get("category") or "",
        "evaluation_metric": comp.get("evaluation_metric") or "",
        "reward": competition.money(comp.get("reward")),
        "team_count": int(comp.get("team_count") or 0),
        "deadline": comp.get("deadline"),
        "entry_deadline": comp.get("new_entrant_deadline"),
        "submissions_disabled": bool(comp.get("submissions_disabled")),
        "date_created": comp.get("enabled_date") or comp.get("date_created"),
        "tags": [tag for tag in tags if tag],
        "is_kernels_submissions_only": bool(comp.get("is_kernels_submissions_only")),
        "awards_points": bool(comp.get("awards_points")),
        "max_daily_submissions": comp.get("max_daily_submissions"),
        "max_team_size": comp.get("max_team_size"),
        "user_has_entered": bool(comp.get("user_has_entered")),
        "user_rank": comp.get("user_rank"),
        "url": competition.url(slug),
    }


def is_hackathon(row: dict) -> bool:
    """A hackathon is judged, not scored: it has no leaderboard."""
    return "hackathon" in [tag.lower() for tag in row.get("tags", [])]


def classify_status(row: dict, now=None) -> str:
    """``active`` or ``completed``.

    A hackathon stays active after its deadline: the result appears only when
    the judges announce winners, which the listing cannot see.
    """
    if is_hackathon(row):
        return "active"
    deadline = text.parse_time(row.get("deadline"))
    if deadline is None:
        return "active"
    return "completed" if deadline < (now or text.now_utc()) else "active"


def within_lookback(row: dict, days: int, now=None) -> bool:
    """True when the competition was created, or ends, inside the window."""
    cutoff = (now or text.now_utc()) - timedelta(days=days)
    for field in ("deadline", "date_created"):
        moment = text.parse_time(row.get(field))
        if moment is not None and moment >= cutoff:
            return True
    return False


def build_queries(categories: list[str], mine: bool, search: str | None) -> list[dict]:
    if mine:
        return [{"group": "entered"}]
    base: dict = {"sortBy": "recentlyCreated"}
    if search:
        base = {"search": search}
    if categories:
        queries = [{**base, "category": CATEGORIES[name]} for name in categories]
    elif search:
        queries = [base, {**base, "group": "community"}]
    else:
        # Every category, then no filter, then the community group, which the
        # default ("general") group leaves out.
        queries = [{**base, "category": value} for value in CATEGORIES.values()]
        queries = [q for q in queries if q["category"] != "community"]
        queries += [base, {**base, "group": "community"}]
    return queries


def fetch(queries: list[dict], token: str, max_pages: int) -> tuple[list[dict], list, int]:
    """Run the queries. Returns ``(rows, failed results, successful calls)``."""
    seen: set[str] = set()
    rows: list[dict] = []
    failures: list[mcp_client.Result] = []
    succeeded = 0
    first = True
    for query in queries:
        for page in range(1, max_pages + 1):
            if not first:
                time.sleep(CALL_DELAY)
            first = False
            result = mcp_client.request(TOOL, {**query, "page": page}, token=token)
            if not result.ok or not isinstance(result.data, dict):
                # An empty answer is the end of a listing, not a failure.
                if result.status != "empty":
                    failures.append(result)
                break
            succeeded += 1
            found = [c for c in result.data.get("competitions") or [] if isinstance(c, dict)]
            for comp in found:
                row = to_row(comp)
                if row["slug"] and row["slug"] not in seen:
                    seen.add(row["slug"])
                    rows.append(row)
            if len(found) < PAGE_SIZE:
                break
    return rows, failures, succeeded


def compact(row: dict) -> dict:
    hide = script.hide_account()
    return {
        "slug": row["slug"],
        "title": row["title"],
        "category": row["category"],
        "status": row["status"],
        "deadline": row["deadline"],
        "team_count": row["team_count"],
        "reward": row["reward"],
        "metric": row["evaluation_metric"],
        "code_competition": row["is_kernels_submissions_only"],
        "entry_deadline": row["entry_deadline"],
        "submissions_closed": row["submissions_disabled"],
        "entered": None if hide else row["user_has_entered"],
        "url": row["url"],
    }


def entry_note(row: dict, now=None) -> str:
    """Whether a newcomer can still take part: ``join by <day>``, or why not."""
    if row["status"] == "completed":
        return ""
    if row["submissions_disabled"]:
        return "submissions closed"
    closes = text.parse_time(row.get("entry_deadline"))
    if closes is None:
        return ""
    if closes < (now or text.now_utc()):
        return "entry closed"
    if text.day(row["entry_deadline"]) == text.day(row["deadline"]):
        return ""  # open until the end: the deadline already says it
    return f"join by {text.day(row['entry_deadline'])}"


def text_lines(rows: list[dict]) -> list[str]:
    """Two lines per competition: the deadline and the title, then the facts and the metric."""
    hide = script.hide_account()
    lines = []
    for row in rows:
        marks = [
            mark
            for mark, on in (
                ("ended", row["status"] == "completed"),
                ("code competition", row["is_kernels_submissions_only"]),
                ("entered", row["user_has_entered"] and not hide),
            )
            if on
        ]
        facts = [
            row["category"] or "?",
            f"{row['team_count']:,} teams",
            text.shorten(row["reward"], 16) or "no prize",
            f"metric: {row['evaluation_metric'] or 'not given'}",
            *marks,
        ]
        note = entry_note(row)
        lines.append(
            f"  {text.day(row['deadline'])}  {text.shorten(row['title'], 70)}"
            + (f" · {note}" if note else "")
        )
        lines.append(f"              {row['slug']} · {' · '.join(facts)}")
    return lines


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List recent and running Kaggle competitions: two lines each, with the metric.",
        epilog="Needs a Kaggle credential: an API token or `kaggle auth login`.",
    )
    parser.add_argument(
        "--days",
        "--lookback-days",
        dest="days",
        type=script.positive_int,
        default=30,
        help="Competitions created, or ending, in the last N days (default: 30)",
    )
    parser.add_argument(
        "--category",
        metavar="NAMES",
        help="Only these categories, comma-separated: " + ", ".join(CATEGORIES),
    )
    parser.add_argument(
        "--min-teams",
        type=int,
        default=None,
        metavar="N",
        help="Leave out competitions with fewer than N teams. By default only community "
        f"competitions with fewer than {COMMUNITY_MIN_TEAMS} are left out",
    )
    parser.add_argument(
        "--status",
        choices=("active", "ended", "all"),
        default="all",
        help="Which competitions to list (default: all, active first)",
    )
    parser.add_argument("--mine", action="store_true", help="The competitions you have entered")
    parser.add_argument("--search", metavar="TEXT", help="Search by text; --days is not applied")
    script.add_limit(parser, 40, "competitions")
    script.add_json(parser)
    script.add_full(parser)
    # The older way to ask for JSON or text.
    parser.add_argument("--output", choices=("json", "text"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.categories = []
    if args.category:
        args.categories = [name.strip().lower() for name in args.category.split(",") if name]
        unknown = [name for name in args.categories if name not in CATEGORIES]
        if unknown:
            parser.error(f"unknown category {unknown[0]!r}; choose from {', '.join(CATEGORIES)}")
    if args.output == "json":
        args.full = True
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
    if not token:
        return script.no_credential("listing competitions")

    queries = build_queries(args.categories, args.mine, args.search)
    max_pages = MAX_PAGES_MINE if args.mine else PAGES_PER_QUERY
    rows, failures, succeeded = fetch(queries, token, max_pages)
    if failures and not succeeded:
        print(f"error: all {len(failures)} competition queries failed", file=sys.stderr)
        return failures[0].fail()
    if failures:
        script.warn(f"{len(failures)} of {len(failures) + succeeded} competition queries failed")

    now = text.now_utc()
    for row in rows:
        row["status"] = classify_status(row, now)
    if not (args.mine or args.search):
        rows = [row for row in rows if within_lookback(row, args.days, now)]
    if args.status != "all":
        wanted = "active" if args.status == "active" else "completed"
        rows = [row for row in rows if row["status"] == wanted]

    hidden_small = 0
    if args.min_teams is None:
        small = [
            row
            for row in rows
            if row["category"].lower() == "community" and row["team_count"] < COMMUNITY_MIN_TEAMS
        ]
        hidden_small = len(small)
        rows = [row for row in rows if row not in small]
    else:
        rows = [row for row in rows if row["team_count"] >= args.min_teams]

    # Active first, then by deadline.
    rows.sort(key=lambda r: (0 if r["status"] == "active" else 1, r.get("deadline") or ""))
    total = len(rows)
    active = sum(1 for row in rows if row["status"] == "active")
    shown = rows[: args.limit]

    indent = 2 if (args.pretty or args.output == "json") else None
    attrs = {"source": SOURCE, "tool": TOOL}
    if not (args.mine or args.search):
        attrs["lookback_days"] = args.days
    # Titles, descriptions and tags are written by hosts: one untrusted block.
    with untrusted.Block(**attrs) as block:
        if args.full:
            block.write_json(shown, indent=indent)
        elif args.json:
            block.write_json([compact(row) for row in shown], indent=indent)
        else:
            if args.mine:
                scope = "you have entered"
            elif args.search:
                scope = "matching the search"
            else:
                scope = f"running or ended in the last {args.days} days"
            block.write(f"{total} competitions {scope}: {active} active, {total - active} ended.")
            if shown:
                for line in text_lines(shown):
                    block.write(line)
    if total > len(shown):
        print(f"Showing {len(shown)} of {total}. Add --limit {total} for all of them.")
    if hidden_small:
        print(
            f"{hidden_small} community competitions with fewer than {COMMUNITY_MIN_TEAMS} teams "
            "are not shown. Add --min-teams 0 to list them."
        )
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
