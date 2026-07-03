#!/usr/bin/env python3
"""Safe wrappers around Kaggle CLI forums and resource topic commands."""

from __future__ import annotations

import argparse
import html
import shlex
import subprocess
import sys

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
FORMAT_CHOICES = ("table", "csv", "json")


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


def _competition_topics_flags(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if getattr(args, "page", None):
        flags.extend(["--page", str(args.page)])
    return flags


def build_command(args: argparse.Namespace) -> tuple[list[str], str]:
    """Build a shell-free Kaggle CLI argv from parsed arguments."""
    cmd = ["kaggle"]

    if args.command == "forums":
        cmd.extend(["forums", "list"])
        cmd.extend(_format_flags(args))
        if args.quiet:
            cmd.append("--quiet")
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
        if args.quiet:
            cmd.append("--quiet")
        return cmd, "forums.topics.list"

    if args.command == "forum-topic":
        cmd.extend(["forums", "topics", "show", args.topic_ref])
        if args.topic_id:
            cmd.append(args.topic_id)
        cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        if args.quiet:
            cmd.append("--quiet")
        return cmd, "forums.topics.show"

    if args.command == "resource-topics":
        cmd.extend([args.resource, "topics", "list", args.resource_ref])
        if args.sort_by:
            cmd.extend(["--sort-by", args.sort_by])
        if args.resource != "competitions" and args.search:
            cmd.extend(["--search", args.search])
        if args.resource == "competitions":
            cmd.extend(_competition_topics_flags(args))
        else:
            cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        if args.quiet:
            cmd.append("--quiet")
        return cmd, f"{args.resource}.topics.list"

    if args.command == "resource-topic":
        cmd.extend([args.resource, "topics", "show", args.topic_ref])
        if args.topic_id:
            cmd.append(args.topic_id)
        cmd.extend(_pagination_flags(args))
        cmd.extend(_format_flags(args))
        if args.quiet:
            cmd.append("--quiet")
        return cmd, f"{args.resource}.topics.show"

    raise ValueError(f"unknown command: {args.command}")


def run_wrapped(cmd: list[str], tool: str) -> int:
    """Run Kaggle CLI and wrap stdout so agents treat Kaggle text as data."""
    marker_command = html.escape(shlex.join(cmd), quote=True)
    print(f'<untrusted-content source="kaggle-cli" tool="{tool}" command="{marker_command}">')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=None)
    except FileNotFoundError:
        print("</untrusted-content>")
        print("error: kaggle executable not found; install kaggle>=2.2.3", file=sys.stderr)
        return 127
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    print("</untrusted-content>")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
    return result.returncode


def _add_common_output_flags(parser: argparse.ArgumentParser, *, default_format: str = "json") -> None:
    parser.add_argument("--format", choices=FORMAT_CHOICES, default=default_format)
    parser.add_argument("--csv", action="store_true", help="Use legacy --csv instead of --format")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress verbose CLI output")


def _add_topic_filters(
    parser: argparse.ArgumentParser,
    *,
    include_forum_filters: bool = False,
    include_search: bool = True,
    include_token_paging: bool = True,
    include_page: bool = False,
) -> None:
    parser.add_argument("--sort-by", choices=SORT_CHOICES)
    if include_search:
        parser.add_argument("-s", "--search")
    if include_token_paging:
        parser.add_argument("--page-size", type=int)
        parser.add_argument("--page-token")
    if include_page:
        parser.add_argument("-p", "--page", type=int)
    if include_forum_filters:
        parser.add_argument("--category", choices=FORUM_CATEGORIES)
        parser.add_argument("--group", choices=FORUM_GROUPS)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    forums = sub.add_parser("forums", help="List Kaggle discussion forums")
    _add_common_output_flags(forums)

    forum_topics = sub.add_parser("forum-topics", help="List topics in all forums or one forum")
    forum_topics.add_argument("forum", nargs="?", help="Forum slug or numeric forum id")
    _add_topic_filters(forum_topics, include_forum_filters=True)
    _add_common_output_flags(forum_topics)

    forum_topic = sub.add_parser("forum-topic", help="Show one forum topic and comments")
    forum_topic.add_argument("topic_ref", help="topic id, forum/id, or forum slug")
    forum_topic.add_argument("topic_id", nargs="?", help="topic id when topic_ref is only forum")
    _add_topic_filters(forum_topic)
    _add_common_output_flags(forum_topic)

    resource_topics = sub.add_parser(
        "resource-topics",
        help="List topics for a competition, dataset, kernel, model, or benchmark",
    )
    resource_topics.add_argument("resource", choices=RESOURCE_GROUPS)
    resource_topics.add_argument("resource_ref")
    _add_topic_filters(resource_topics, include_page=True)
    _add_common_output_flags(resource_topics)

    resource_topic = sub.add_parser("resource-topic", help="Show one resource topic and comments")
    resource_topic.add_argument("resource", choices=RESOURCE_GROUPS)
    resource_topic.add_argument("topic_ref")
    resource_topic.add_argument("topic_id", nargs="?")
    _add_topic_filters(resource_topic)
    _add_common_output_flags(resource_topic)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cmd, tool = build_command(args)
    return run_wrapped(cmd, tool)


if __name__ == "__main__":
    sys.exit(main())
