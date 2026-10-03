#!/usr/bin/env python3
"""The facts about a Kaggle competition on one screen.

    competition_brief.py titanic
    competition_brief.py https://www.kaggle.com/competitions/titanic --json
    competition_brief.py titanic spaceship-titanic       several, one block each

Prints the metric and how the evaluation page starts, the deadline with the
time left, the host's timeline, the prize, the team size, the daily submission
limit, whether it is a code competition, and the names of its pages. A few hundred tokens, no
credential for a public competition. With a credential it also says whether
you have entered and your rank.

Read a page next with the pages command: pages <competition> --page NAME.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, mcp_client, script, text, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = competition.FACTS_TOOL


def data_facts(slug: str) -> dict | None:
    """How much data the competition has, or None when Kaggle does not say."""
    result = mcp_client.request(
        "get_competition_data_files_summary", {"competitionName": slug}, token=""
    )
    summary = result.data.get("file_summary_info") if isinstance(result.data, dict) else None
    if not result.ok or not isinstance(summary, dict):
        return None
    try:
        types = [
            {
                "extension": str(kind.get("extension") or ""),
                "files": int(kind.get("file_count") or 0),
                "bytes": int(kind.get("total_size") or 0),
            }
            for kind in summary.get("file_types") or []
        ]
        files = int(summary.get("total_file_count") or 0)
    except (TypeError, ValueError, AttributeError):
        return None
    types.sort(key=lambda kind: kind["bytes"], reverse=True)
    return {"files": files, "bytes": sum(kind["bytes"] for kind in types), "types": types}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The facts about Kaggle competitions on one screen each.",
        epilog="No credential is needed for a public competition.",
    )
    script.add_competition(parser)
    parser.add_argument(
        "more", nargs="*", metavar="competition", help="More competitions, one block each"
    )
    script.add_json(parser)
    script.add_full(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)
    slugs = [slug]
    for value in args.more:
        try:
            slugs.append(script.competition_slug(value))
        except ValueError as exc:
            parser.error(f"{exc}: {value}")

    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
    worst = script.EXIT_OK
    for name in dict.fromkeys(slugs):
        code = brief(name, token, args)
        worst = worst or code
    return worst


def brief(slug: str, token: str, args: argparse.Namespace) -> int:
    """Print one competition's brief. Returns its exit code."""
    result = competition.fetch_facts(slug, token)
    if not result.ok or not isinstance(result.data, dict):
        return result.fail(competition=slug)

    indent = 2 if args.pretty else None
    attrs = {"source": SOURCE, "tool": TOOL, "competition": slug}
    if args.full:
        untrusted.emit_json(result.data, indent=indent, **attrs)
        return script.EXIT_OK

    info = competition.facts(slug, result.data)
    # The page names tell the reader what there is to read next. A failure
    # here is not worth failing the brief for.
    pages = competition.pages_of(competition.fetch_pages(slug, token).data)
    info["pages"] = [{"name": p.get("name"), "chars": len(p.get("content") or "")} for p in pages]
    # "What is the metric?" usually needs a sentence more than the metric's name.
    info["evaluation"] = competition.page_summary(competition.find_page(pages, "evaluation"))
    # The host's own dates: entry, team merger and final submission deadlines.
    info["timeline"] = competition.timeline_summary(competition.find_page(pages, "timeline"))
    info["data"] = data_facts(slug)

    if script.hide_account():
        info = {**info, "user_has_entered": None, "user_rank": None}
    if args.json:
        untrusted.emit_json(info, indent=indent, **attrs)
        return script.EXIT_OK

    extra: list[tuple[str, str]] = []
    if info["data"]:
        kinds = ", ".join(
            f"{k['extension'] or 'other'} {text.human_size(k['bytes'])}"
            for k in info["data"]["types"][:4]
        )
        extra.append(
            (
                "data",
                f"{info['data']['files']:,} files, {text.human_size(info['data']['bytes'])} "
                f"({kinds})",
            )
        )
    if info["pages"]:
        first, *rest = info["pages"]
        names = [f"{first['name']} ({first['chars']:,} characters)"]
        names += [f"{p['name']} ({p['chars']:,})" for p in rest]
        extra.append(("pages", ", ".join(names)))

    with untrusted.Block(**attrs) as block:
        block.write(info["title"])
        if info["description"]:
            block.write(info["description"])
        signed_in = bool(token) and not script.hide_account()
        for line in competition.fact_lines(info, signed_in=signed_in, extra=extra):
            block.write(line)
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
