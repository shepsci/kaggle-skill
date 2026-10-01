#!/usr/bin/env python3
"""Safe wrappers around Kaggle CLI forums and resource topic commands.

Every flag accepted here is forwarded to the CLI, and a flag the CLI does not
support for a subcommand is rejected instead of being dropped. Output is
printed inside an untrusted-content block, because topic titles and comments
are written by Kaggle users.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import kaggle_cli, untrusted  # noqa: E402

RESOURCE_GROUPS = ("competitions", "datasets", "kernels", "models", "benchmarks")
SORT_CHOICES = ("hot", "top", "new", "recent", "active", "relevance")
FORUM_CATEGORIES = (
    "all",
    "forums",
    "competitions",
    "datasets",
    "competition_write_ups",
    "models",
    "benchmarks",
)
FORUM_GROUPS = ("all", "owned", "upvoted", "bookmarked", "my_activity", "drafts")
SOURCE = "kaggle-cli"

# table, csv or json, optionally with a field projection: json(title,votes)
_FORMAT_RE = re.compile(r"^(table|csv|json)(\([A-Za-z0-9_]+(,[A-Za-z0-9_]+)*\))?$")
_NEXT_TOKEN_RE = re.compile(r"^Next [Pp]age [Tt]oken\s*[=:]\s*(\S+)\s*$")


def _format_arg(value: str) -> str:
    if not _FORMAT_RE.match(value):
        raise argparse.ArgumentTypeError(
            "use table, csv or json, optionally with fields: json(title,votes)"
        )
    return value


def _format_flags(args: argparse.Namespace) -> list[str]:
    if getattr(args, "csv", False):
        return ["--csv"]
    fmt = getattr(args, "format", None)
    return ["--format", fmt] if fmt else []


def _pagination_flags(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if getattr(args, "page_size", None):
        flags.extend(["--page-size", str(args.page_size)])
    if getattr(args, "page_token", None):
        flags.extend(["--page-token", args.page_token])
    return flags


def _quiet_flag(args: argparse.Namespace) -> list[str]:
    return ["--quiet"] if args.quiet else []


def build_command(args: argparse.Namespace) -> tuple[list[str], str]:
    """Build a shell-free Kaggle CLI argv from parsed arguments."""
    cmd = ["kaggle"]

    if args.command == "forums":
        cmd.extend(["forums", "list"])
        cmd.extend(_format_flags(args))
        cmd.extend(_quiet_flag(args))
        return cmd, "forums"

    if args.command == "forum-topics":
        cmd.extend(["forums", "topics", "list"])
        if args.forum:
            cmd.append(args.forum)
        if args.sort_by:
            cmd.extend(["--sort-by", args.sort_by])
        if args.search:
            cmd.extend(["--search", args.search])
        if args.category:
            cmd.extend(["--category", args.category])
        if args.group:
            cmd.extend(["--group", args.group])
        cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        cmd.extend(_quiet_flag(args))
        return cmd, "forums.topics.list"

    if args.command == "forum-topic":
        cmd.extend(["forums", "topics", "show", args.topic_ref])
        if args.topic_id:
            cmd.append(args.topic_id)
        cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        cmd.extend(_quiet_flag(args))
        return cmd, "forums.topics.show"

    if args.command == "resource-topics":
        is_competition = args.resource == "competitions"
        if is_competition and args.search:
            raise ValueError("`competitions topics list` has no --search option")
        if is_competition and (args.page_size or args.page_token):
            # The CLI accepts these for competitions, prints a warning, and ignores them.
            raise ValueError(
                "`competitions topics list` pages with --page; "
                "--page-size and --page-token are ignored by the CLI"
            )
        if not is_competition and args.page:
            raise ValueError(f"`{args.resource} topics list` pages with --page-token, not --page")
        cmd.extend([args.resource, "topics", "list", args.resource_ref])
        if args.sort_by:
            cmd.extend(["--sort-by", args.sort_by])
        if args.search:
            cmd.extend(["--search", args.search])
        if args.page:
            cmd.extend(["--page", str(args.page)])
        cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        cmd.extend(_quiet_flag(args))
        return cmd, f"{args.resource}.topics.list"

    if args.command == "resource-topic":
        cmd.extend([args.resource, "topics", "show", args.topic_ref])
        if args.topic_id:
            cmd.append(args.topic_id)
        cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        cmd.extend(_quiet_flag(args))
        return cmd, f"{args.resource}.topics.show"

    raise ValueError(f"unknown command: {args.command}")


def split_next_page_token(stdout: str) -> tuple[str, str | None]:
    """Separate the CLI's trailing ``Next page token`` line from its output.

    The CLI prints that line after the data, so JSON output would otherwise
    not parse.
    """
    lines = stdout.splitlines()
    token: str | None = None
    kept: list[str] = []
    for line in lines:
        match = _NEXT_TOKEN_RE.match(line.strip())
        if match:
            token = match.group(1)
        else:
            kept.append(line)
    body = "\n".join(kept)
    return (body + "\n" if body else ""), token


def run_wrapped(cmd: list[str], tool: str) -> int:
    """Run Kaggle CLI and wrap stdout so agents treat Kaggle text as data."""
    result = kaggle_cli.run(cmd[1:])
    body, next_token = split_next_page_token(result.stdout)
    with untrusted.Block(source=SOURCE, tool=tool, command=" ".join(cmd)) as block:
        if body:
            block.write(body)
    extra = result.stderr
    if next_token:
        extra = f"next page token: {next_token}\n" + extra
    if extra.strip():
        with untrusted.Block(source=SOURCE, tool=tool, stream="stderr", file=sys.stderr) as block:
            block.write(extra)
    if result.returncode != 0:
        print(f"kaggle exited with status {result.returncode}", file=sys.stderr)
    return result.returncode


def _add_common_output_flags(
    parser: argparse.ArgumentParser, *, default_format: str = "json"
) -> None:
    parser.add_argument(
        "--format",
        type=_format_arg,
        default=default_format,
        help="table, csv or json; add fields as json(title,votes)",
    )
    parser.add_argument("--csv", action="store_true", help="Use legacy --csv instead of --format")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress verbose CLI output")


def _add_paging(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--page-token")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    forums = sub.add_parser("forums", help="List Kaggle discussion forums")
    _add_common_output_flags(forums)

    forum_topics = sub.add_parser("forum-topics", help="List topics in all forums or one forum")
    forum_topics.add_argument("forum", nargs="?", help="Forum slug, e.g. getting-started")
    forum_topics.add_argument("--sort-by", choices=SORT_CHOICES)
    forum_topics.add_argument("-s", "--search")
    forum_topics.add_argument("--category", choices=FORUM_CATEGORIES)
    forum_topics.add_argument("--group", choices=FORUM_GROUPS)
    _add_paging(forum_topics)
    _add_common_output_flags(forum_topics)

    forum_topic = sub.add_parser("forum-topic", help="Show one forum topic and comments")
    forum_topic.add_argument("topic_ref", help="topic id, forum/id, or forum slug")
    forum_topic.add_argument("topic_id", nargs="?", help="topic id when topic_ref is only forum")
    _add_paging(forum_topic)
    _add_common_output_flags(forum_topic)

    resource_topics = sub.add_parser(
        "resource-topics",
        help="List topics for a competition, dataset, kernel, model, or benchmark",
    )
    resource_topics.add_argument("resource", choices=RESOURCE_GROUPS)
    resource_topics.add_argument("resource_ref")
    resource_topics.add_argument("--sort-by", choices=SORT_CHOICES)
    resource_topics.add_argument("-s", "--search", help="Not available for competitions")
    resource_topics.add_argument("-p", "--page", type=int, help="Competitions only")
    _add_paging(resource_topics)  # not for competitions, which page with --page
    _add_common_output_flags(resource_topics)

    resource_topic = sub.add_parser("resource-topic", help="Show one resource topic and comments")
    resource_topic.add_argument("resource", choices=RESOURCE_GROUPS)
    resource_topic.add_argument("topic_ref")
    resource_topic.add_argument("topic_id", nargs="?")
    _add_paging(resource_topic)
    _add_common_output_flags(resource_topic)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        cmd, tool = build_command(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return run_wrapped(cmd, tool)


if __name__ == "__main__":
    sys.exit(main())
