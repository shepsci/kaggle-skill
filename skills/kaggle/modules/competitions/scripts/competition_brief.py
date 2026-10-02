#!/usr/bin/env python3
"""The facts about a Kaggle competition on one screen.

    competition_brief.py titanic
    competition_brief.py https://www.kaggle.com/competitions/titanic --json

Prints the metric, the deadline with the time left, the prize, the team size,
the daily submission limit, whether it is a code competition, and the names of
its pages. One call, a few hundred tokens, no credential for a public
competition. With a credential it also says whether you have entered and your
rank.

Read a page next with competition_pages.py --page NAME.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, mcp_client, script, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = competition.FACTS_TOOL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The facts about a Kaggle competition on one screen.",
        epilog="No credential is needed for a public competition.",
    )
    script.add_competition(parser)
    script.add_json(parser)
    script.add_full(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
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

    if args.json:
        untrusted.emit_json(info, indent=indent, **attrs)
        return script.EXIT_OK

    with untrusted.Block(**attrs) as block:
        block.write(info["title"])
        if info["description"]:
            block.write(info["description"])
        for line in competition.fact_lines(info, signed_in=bool(token)):
            block.write(line)
        if info["pages"]:
            names = ", ".join(f"{p['name']} ({p['chars']:,})" for p in info["pages"])
            block.write(f"  pages (characters): {names}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
