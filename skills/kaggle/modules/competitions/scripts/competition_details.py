#!/usr/bin/env python3
"""The data files, the top of the leaderboard and the most-voted notebooks of a competition.

    competition_details.py titanic
    competition_details.py titanic --top 20 --json

Three reads on the Kaggle MCP server. They need a credential (an API token or
`kaggle auth login`), and the file list also needs the competition's rules to
be accepted. A lookup that fails is reported and the others are still printed.

Team names and notebook titles are written by participants, so the output is
inside an untrusted-content block.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, mcp_client, script, text, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = "competition_details"

# Notebook titles that look like a solution writeup.
WRITEUP_PATTERNS = [
    re.compile(r"\b\d+(st|nd|rd|th)\s+place\b", re.IGNORECASE),
    re.compile(r"\bwinning\s+solution\b", re.IGNORECASE),
    re.compile(r"\bgold\s+(medal\s+)?solution\b", re.IGNORECASE),
    re.compile(r"\btop\s+\d+%?\s+solution\b", re.IGNORECASE),
    re.compile(r"\bwinner'?s?\s+writeup\b", re.IGNORECASE),
    re.compile(r"\bsolution\s+writeup\b", re.IGNORECASE),
]

# The server pages its listings. Ask for this many, and say so when there are more.
MAX_FILES = 200
MAX_LEADERBOARD_ROWS = 200
TOP_NOTEBOOKS = 10


def is_writeup_kernel(title: str) -> bool:
    """True when a notebook title looks like a solution writeup."""
    return any(pattern.search(title) for pattern in WRITEUP_PATTERNS)


class LookupFailed(RuntimeError):
    def __init__(self, result: mcp_client.Result) -> None:
        super().__init__(result.status)
        self.result = result


def _data(tool: str, request: dict, token: str) -> dict:
    result = mcp_client.request(tool, request, token=token)
    if not result.ok or not isinstance(result.data, dict):
        raise LookupFailed(result)
    return result.data


def get_competition_files(slug: str, token: str) -> list[dict]:
    """The data files, up to MAX_FILES. A last entry marks a longer listing."""
    data = _data(
        "list_competition_data_files", {"competitionName": slug, "pageSize": MAX_FILES}, token
    )
    listing = [
        {"name": str(f.get("name", "")), "size": int(f.get("total_bytes") or 0)}
        for f in data.get("files") or []
        if isinstance(f, dict)
    ]
    if data.get("next_page_token"):
        listing.append({"name": "...", "truncated": True})
    return listing


def get_leaderboard(slug: str, token: str, top: int = 5) -> list[dict]:
    """The first ``top`` leaderboard rows (at most MAX_LEADERBOARD_ROWS)."""
    wanted = max(1, min(top, MAX_LEADERBOARD_ROWS))
    data = _data(
        "get_competition_leaderboard", {"competitionName": slug, "pageSize": wanted}, token
    )
    rows = [row for row in data.get("submissions") or [] if isinstance(row, dict)]
    return [
        {"rank": rank, "team": row.get("team_name") or "", "score": row.get("score") or ""}
        for rank, row in enumerate(rows[:wanted], start=1)
    ]


def get_top_kernels(slug: str, token: str, count: int = TOP_NOTEBOOKS) -> list[dict]:
    """The most-voted notebooks of the competition."""
    data = _data(
        "search_notebooks", {"competition": slug, "sortBy": "voteCount", "pageSize": count}, token
    )
    notebooks = []
    for kernel in data.get("kernels") or []:
        if not isinstance(kernel, dict):
            continue
        ref = str(kernel.get("ref") or "")
        title = str(kernel.get("title") or "")
        notebooks.append(
            {
                "title": title,
                "ref": ref,
                "author": kernel.get("author") or "",
                "votes": int(kernel.get("total_votes") or 0),
                "url": f"{competition.KAGGLE_BASE}/code/{ref}" if ref else "",
                "is_writeup": is_writeup_kernel(title),
            }
        )
    return notebooks


def get_details(slug: str, token: str, top: int = 5) -> tuple[dict, dict]:
    """Run the three lookups. Returns ``(details, failures by section)``."""
    failures: dict[str, mcp_client.Result] = {}

    def section(name: str, fn, *args) -> list[dict]:
        try:
            return fn(*args)
        except LookupFailed as exc:
            failures[name] = exc.result
            return []

    files = section("files", get_competition_files, slug, token)
    leaderboard = section("leaderboard_top", get_leaderboard, slug, token, top)
    kernels = section("top_kernels", get_top_kernels, slug, token)
    details = {
        "slug": slug,
        "url": competition.url(slug),
        "files": files,
        "leaderboard_top": leaderboard,
        "top_kernels": kernels,
        "writeup_kernels": [k for k in kernels if k.get("is_writeup")],
    }
    if failures:
        details["errors"] = {
            name: mcp_client.error_message(result.response)[:200] or result.status
            for name, result in failures.items()
        }
    return details, failures


def text_lines(details: dict) -> list[str]:
    errors = details.get("errors") or {}
    lines: list[str] = []

    files = [f for f in details["files"] if not f.get("truncated")]
    more = " (the first 200; there are more)" if len(files) != len(details["files"]) else ""
    if "files" in errors:
        lines.append(f"Data files: not available ({errors['files']})")
    else:
        total = text.human_size(sum(f["size"] for f in files))
        lines.append(f"Data files: {len(files)}, {total} in all{more}")
        for item in files[:15]:
            lines.append(f"  {text.human_size(item['size']):>9}  {item['name']}")
        if len(files) > 15:
            lines.append(f"  ... and {len(files) - 15} more")

    lines.append("")
    if "leaderboard_top" in errors:
        lines.append(f"Leaderboard: not available ({errors['leaderboard_top']})")
    else:
        lines.append(f"Leaderboard, top {len(details['leaderboard_top'])}:")
        for row in details["leaderboard_top"]:
            lines.append(f"  {row['rank']:>3}  {str(row['score']):<12}  {row['team']}")

    lines.append("")
    if "top_kernels" in errors:
        lines.append(f"Most-voted notebooks: not available ({errors['top_kernels']})")
    else:
        lines.append("Most-voted notebooks:")
        for kernel in details["top_kernels"]:
            mark = "  [solution writeup]" if kernel["is_writeup"] else ""
            lines.append(
                f"  {kernel['votes']:>7,}  {text.shorten(kernel['title'], 60)}{mark}\n"
                f"           {kernel['url']}"
            )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The data files, the top of the leaderboard and the most-voted notebooks "
        "of a competition.",
        epilog="Needs a Kaggle credential: an API token or `kaggle auth login`.",
    )
    script.add_competition(parser)
    parser.add_argument(
        "--top",
        "--top-n",
        dest="top",
        type=script.positive_int,
        default=5,
        metavar="N",
        help=f"Leaderboard rows to print (default: 5, at most {MAX_LEADERBOARD_ROWS})",
    )
    script.add_json(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
    if not token:
        return script.no_credential("the file list, the leaderboard and the notebook search")

    details, failures = get_details(slug, token, args.top)
    if len(failures) == 3:
        print("error: every lookup failed", file=sys.stderr)
        return next(iter(failures.values())).fail(competition=slug)

    attrs = {"source": SOURCE, "tool": TOOL, "competition": slug}
    if args.json:
        untrusted.emit_json(details, indent=2, **attrs)
    else:
        with untrusted.Block(**attrs) as block:
            for line in text_lines(details):
                block.write(line)
    if failures:
        # Kaggle's reason is inside the block: it is the server's text.
        script.warn(f"{len(failures)} of 3 lookups failed: {', '.join(failures)}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
