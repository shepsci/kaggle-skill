#!/usr/bin/env python3
"""Read the overview pages of a Kaggle hackathon: rules, requirements, judging.

    hackathon_overview.py kaggle-measuring-agi                    list the pages
    hackathon_overview.py kaggle-measuring-agi --page evaluation  print one page
    hackathon_overview.py kaggle-measuring-agi --all              print every page

Calls `get_hackathon_overview`. The overview is public: no credential is
needed. A token, when one is configured, is sent as well. The options are the
same as competition_pages.py, which reads any competition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, script  # noqa: E402

TOOL = "get_hackathon_overview"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read the overview pages of a Kaggle hackathon: rules, requirements, judging.",
        epilog="No credential is needed.",
    )
    script.add_competition(parser)
    competition.add_page_arguments(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    result = competition.fetch_pages(slug, tool=TOOL)
    if not result.ok:
        return result.fail(competition=slug, indent=2 if args.pretty else None)
    return competition.print_pages(args, slug, result, tool=TOOL)


if __name__ == "__main__":
    sys.exit(main())
