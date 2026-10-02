#!/usr/bin/env python3
"""Read the pages of a Kaggle competition: rules, evaluation, data, timeline.

    competition_pages.py titanic                     list the pages and their sizes
    competition_pages.py titanic --page evaluation   print one page as text
    competition_pages.py titanic --all               print every page

The pages are long: a rules page alone is 6,000 to 9,000 tokens. Start with the
list, then read the page that answers the question. For the metric, the
deadline and the limits, competition_brief.py is one short call.

Public competitions need no credential. A token, when one is configured, is
sent so that competitions you have joined privately also resolve. Works for
hackathons too; hackathon_overview.py adds the track and judging pages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, script  # noqa: E402

TOOL = competition.PAGES_TOOL


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read the pages of a Kaggle competition: rules, evaluation, data, timeline.",
        epilog="No credential is needed for a public competition.",
    )
    script.add_competition(parser)
    competition.add_page_arguments(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    result = competition.fetch_pages(slug)
    if not result.ok:
        return result.fail(competition=slug, indent=2 if args.pretty else None)
    return competition.print_pages(args, slug, result, tool=TOOL)


if __name__ == "__main__":
    sys.exit(main())
