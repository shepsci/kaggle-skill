#!/usr/bin/env python3
"""Read Kaggle discussions: forums, topic lists, and one topic with its comments.

    forums.py forums
    forums.py topics                                 every forum, hottest first
    forums.py topics getting-started --sort new
    forums.py topics --competition titanic --sort top
    forums.py topics --search "data leak"
    forums.py topic 429948                           the post and its first comments
    forums.py topic https://www.kaggle.com/competitions/titanic/discussion/429948

These three read the Kaggle MCP server. Public discussions need no credential.

Three more subcommands go through the Kaggle CLI and need a credential:

    forums.py resource-topics datasets owner/name    topics of a dataset, notebook, model, benchmark
    forums.py resource-topic datasets <topic id>
    forums.py forum-topics --category competition_write_ups --group owned

For those, every flag is forwarded to the CLI, and a flag the CLI does not
support for a subcommand is rejected instead of being dropped.

Topic titles, posts and comments are written by Kaggle users, so everything
is printed inside an untrusted-content block.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli, mcp_client, script, text, untrusted  # noqa: E402

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
MCP_SOURCE = "kaggle-mcp"
# What `list_forum_topics` and `list_competition_topics` take for `sortBy`.
MCP_SORTS = ("hot", "new", "recent", "top", "active", "relevance")
DEFAULT_COMMENTS = 10
DEFAULT_REPLIES = 3
DEFAULT_MESSAGE_CHARS = 1500
_TOPIC_URL_RE = re.compile(r"/discussions?/(?:[A-Za-z0-9_-]+/)?(\d+)")

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


# -- readers that use the MCP server -----------------------------------------


def _count(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def topic_id_from(value: str) -> int:
    """A topic id from the id itself or from a discussion URL."""
    value = value.strip()
    if value.isdigit():
        return int(value)
    match = _TOPIC_URL_RE.search(value)
    if match:
        return int(match.group(1))
    raise ValueError("give a topic id or a discussion URL")


def list_forums(args: argparse.Namespace) -> int:
    result = mcp_client.request("list_forums", {})
    if not result.ok or not isinstance(result.data, dict):
        return result.fail()
    forums = [f for f in result.data.get("forums") or [] if isinstance(f, dict)]
    attrs = {"source": MCP_SOURCE, "tool": "list_forums"}
    if args.json:
        rows = [
            {
                "id": _count(f.get("id")),
                "name": f.get("name"),
                "slug": str(f.get("url") or "").rstrip("/").rsplit("/", 1)[-1],
                "subtitle": f.get("subtitle"),
                "url": text.absolute_url(f.get("url")),
            }
            for f in forums
        ]
        untrusted.emit_json(rows, **attrs)
        return script.EXIT_OK
    with untrusted.Block(**attrs) as block:
        block.write(f"{len(forums)} forums:")
        for forum in forums:
            slug = str(forum.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
            block.write(f"  {slug:<22}  {forum.get('name')}: {forum.get('subtitle') or ''}")
    print("List a forum's topics with: topics <slug>")
    return script.EXIT_OK


def _topic_row(topic: dict) -> dict:
    author = topic.get("author_user") if isinstance(topic.get("author_user"), dict) else {}
    return {
        "id": _count(topic.get("id")),
        "title": text.collapse(str(topic.get("title") or "")),
        "votes": _count(topic.get("votes")),
        "comments": _count(topic.get("comment_count")),
        "posted": topic.get("post_date"),
        "last_comment": topic.get("last_comment_post_date"),
        "author": author.get("display_name") or "",
        "where": topic.get("parent_name") or "",
        "pinned": str(topic.get("is_sticky")).lower() == "true",
        "url": text.absolute_url(topic.get("topic_url")),
    }


def list_topics(args: argparse.Namespace) -> int:
    request: dict = {"page": args.page}
    if args.sort:
        request["sortBy"] = args.sort
    if args.competition:
        if args.forum or args.search:
            return script.fail(
                "--competition cannot be combined with a forum or --search", script.EXIT_USAGE
            )
        try:
            slug = script.competition_slug(args.competition)
        except ValueError as exc:
            return script.fail(str(exc), script.EXIT_USAGE)
        tool = "list_competition_topics"
        request["competitionName"] = slug
        scope = f"in the {slug} competition"
    else:
        tool = "list_forum_topics"
        scope = "across the forums"
        if args.forum:
            found = mcp_client.request("get_forum", {"forumSlug": args.forum})
            forum = (found.data or {}).get("forum") if isinstance(found.data, dict) else None
            if not found.ok or not isinstance(forum, dict) or not forum.get("id"):
                print("error: no forum with that slug; list them with: forums", file=sys.stderr)
                return found.fail() if not found.ok else script.EXIT_FAILED
            request["forumId"] = _count(forum["id"])
            scope = f"in the {args.forum} forum"
        if args.search:
            request["searchQuery"] = args.search
            scope += " matching the search"

    result = mcp_client.request(tool, request)
    if not result.ok or not isinstance(result.data, dict):
        return result.fail()
    rows = [_topic_row(t) for t in result.data.get("topics") or [] if isinstance(t, dict)]
    total = _count(result.data.get("count") or result.data.get("total_count"))
    shown = rows[: args.limit]

    attrs = {"source": MCP_SOURCE, "tool": tool}
    if args.json:
        untrusted.emit_json({"page": args.page, "total": total, "topics": shown}, **attrs)
        return script.EXIT_OK
    with untrusted.Block(**attrs) as block:
        of_total = f" of {total:,}" if total else ""
        block.write(f"{len(shown)} topics{of_total} {scope}, page {args.page}:")
        if shown:
            block.write(f"  {'id':>8}  {'votes':>5}  {'replies':>7}  {'posted':<10}  title")
        for row in shown:
            where = f" — {row['where']}" if row["where"] else ""
            pinned = " [pinned]" if row["pinned"] else ""
            block.write(
                f"  {row['id']:>8}  {row['votes']:>5}  {row['comments']:>7}  "
                f"{text.day(row['posted']):<10}  {text.shorten(row['title'], 80)}{where}{pinned}"
            )
    if shown:
        print(f"Read one with: topic <id>. Next page: --page {args.page + 1}.")
    return script.EXIT_OK


def _message(message: dict, max_chars: int) -> dict:
    """A post, comment or reply reduced to author, date, votes and text."""
    author = message.get("author") if isinstance(message.get("author"), dict) else {}
    votes = message.get("votes") if isinstance(message.get("votes"), dict) else {}
    body = message.get("raw_markdown") or text.html_to_text(message.get("content") or "")
    cut = max(len(body) - max_chars, 0) if max_chars else 0
    return {
        "author": author.get("display_name") or "",
        "posted": message.get("post_date"),
        "votes": _count(votes.get("total_votes")),
        "body": body[:max_chars].rstrip() if cut else body,
        "cut": cut,
    }


def summarize_topic(topic: dict, comments: int, replies: int, max_chars: int) -> dict:
    """The topic with its post and at most ``comments`` comments."""
    first = topic.get("first_message") if isinstance(topic.get("first_message"), dict) else {}
    all_comments = [c for c in topic.get("comments") or [] if isinstance(c, dict)]
    shown = []
    for comment in all_comments[:comments]:
        item = _message(comment, max_chars)
        nested = [r for r in comment.get("replies") or [] if isinstance(r, dict)]
        item["replies"] = [_message(r, max_chars) for r in nested[:replies]]
        item["more_replies"] = max(len(nested) - replies, 0)
        shown.append(item)
    post = _message(first, 0)
    return {
        "id": topic.get("id"),
        "title": text.collapse(str(topic.get("name") or "")),
        "url": text.absolute_url(topic.get("url")),
        "where": topic.get("forum_name") or topic.get("parent_name") or "",
        "author": topic.get("author_user_display_name") or post["author"],
        "posted": topic.get("post_date") or post["posted"],
        "votes": _count(topic.get("total_votes")),
        "total_messages": _count(topic.get("total_messages")),
        "body": post["body"],
        "comments": shown,
        "comment_count": len(all_comments),
    }


def _note(count: int) -> str:
    return f"\n[cut: {count:,} more characters]" if count else ""


def topic_lines(summary: dict) -> list[str]:
    lines = [f"# {summary['title']}"]
    facts = [f"by {summary['author']}"] if summary["author"] else []
    facts.append(text.day(summary["posted"]))
    facts.append(f"{summary['votes']} votes")
    facts.append(f"{summary['total_messages']} messages")
    if summary["where"]:
        facts.append(f"in {summary['where']}")
    lines.append(" · ".join(facts))
    if summary["url"]:
        lines.append(summary["url"])
    lines += ["", summary["body"] or "(the post has no text)"]
    shown = summary["comments"]
    if shown:
        lines += ["", f"--- Comments: {len(shown)} of {summary['comment_count']} ---"]
    for number, comment in enumerate(shown, start=1):
        lines.append("")
        lines.append(
            f"[{number}] {comment['author']} · {text.day(comment['posted'])} · "
            f"{comment['votes']} votes"
        )
        lines.append(comment["body"] + _note(comment["cut"]))
        for reply in comment["replies"]:
            lines.append(f"    > {reply['author']} · {text.day(reply['posted'])}:")
            body = reply["body"] + _note(reply["cut"])
            lines += [f"    > {line}" for line in body.splitlines()]
        if comment["more_replies"]:
            lines.append(f"    > ... and {comment['more_replies']} more replies")
    return lines


def show_topic(args: argparse.Namespace) -> int:
    try:
        topic_id = topic_id_from(args.topic)
    except ValueError as exc:
        return script.fail(str(exc), script.EXIT_USAGE)
    result = mcp_client.request(
        "get_forum_topic", {"forumTopicId": topic_id, "includeComments": True}
    )
    topic = result.data.get("forum_topic") if isinstance(result.data, dict) else None
    if not result.ok or not isinstance(topic, dict):
        return result.fail(topic=topic_id)
    attrs = {"source": MCP_SOURCE, "tool": "get_forum_topic", "topic": topic_id}
    if args.full:
        untrusted.emit_json(result.data, **attrs)
        return script.EXIT_OK
    summary = summarize_topic(topic, args.comments, args.replies, args.max_chars)
    if args.json:
        untrusted.emit_json(summary, **attrs)
        return script.EXIT_OK
    with untrusted.Block(**attrs) as block:
        for line in topic_lines(summary):
            block.write(line)
    left = summary["comment_count"] - len(summary["comments"])
    if left > 0:
        print(f"{left} more comments. Add --comments N to read more of them.")
    return script.EXIT_OK


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
    parser = argparse.ArgumentParser(
        description="Read Kaggle discussions: forums, topic lists, and one topic with its "
        "comments.",
        epilog="forums, topics and topic need no credential for public discussions. "
        "The other subcommands use the Kaggle CLI and need one.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    forums = sub.add_parser("forums", help="List the discussion forums")
    script.add_json(forums)

    topics = sub.add_parser("topics", help="List topics: every forum, one forum, or a competition")
    topics.add_argument("forum", nargs="?", help="Forum slug, for example getting-started")
    topics.add_argument("-c", "--competition", help="Topics of this competition (slug or URL)")
    topics.add_argument("-s", "--search", help="Only topics that match this text")
    topics.add_argument("--sort", choices=MCP_SORTS, help="Order (default: hot)")
    topics.add_argument("--page", type=script.positive_int, default=1, help="Page of 20 topics")
    script.add_limit(topics, 20, "topics")
    script.add_json(topics)

    topic = sub.add_parser("topic", help="Read one topic: the post and its first comments")
    topic.add_argument("topic", help="Topic id, or the URL of the discussion")
    topic.add_argument(
        "--comments",
        type=int,
        default=DEFAULT_COMMENTS,
        metavar="N",
        help=f"Comments to print, hottest first (default: {DEFAULT_COMMENTS})",
    )
    topic.add_argument(
        "--replies",
        type=int,
        default=DEFAULT_REPLIES,
        metavar="N",
        help=f"Replies to print under each comment (default: {DEFAULT_REPLIES})",
    )
    topic.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MESSAGE_CHARS,
        metavar="N",
        help=f"Cut each comment after N characters; 0 for no limit "
        f"(default: {DEFAULT_MESSAGE_CHARS}). The post is never cut",
    )
    script.add_json(topic)
    script.add_full(topic)

    forum_topics = sub.add_parser(
        "forum-topics", help="List forum topics through the Kaggle CLI (needs a credential)"
    )
    forum_topics.add_argument("forum", nargs="?", help="Forum slug, e.g. getting-started")
    forum_topics.add_argument("--sort-by", choices=SORT_CHOICES)
    forum_topics.add_argument("-s", "--search")
    forum_topics.add_argument("--category", choices=FORUM_CATEGORIES)
    forum_topics.add_argument("--group", choices=FORUM_GROUPS)
    _add_paging(forum_topics)
    _add_common_output_flags(forum_topics)

    forum_topic = sub.add_parser(
        "forum-topic", help="Show one topic through the Kaggle CLI (needs a credential)"
    )
    forum_topic.add_argument("topic_ref", help="topic id, forum/id, or forum slug")
    forum_topic.add_argument("topic_id", nargs="?", help="topic id when topic_ref is only forum")
    _add_paging(forum_topic)
    # The CLI's JSON output of a topic holds the comments and not the post.
    _add_common_output_flags(forum_topic, default_format="table")

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
    _add_common_output_flags(resource_topic, default_format="table")

    return parser.parse_args(argv)


MCP_COMMANDS = {"forums": list_forums, "topics": list_topics, "topic": show_topic}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    credentials.load_configured_env_file()
    if args.command in MCP_COMMANDS:
        return MCP_COMMANDS[args.command](args)
    try:
        cmd, tool = build_command(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if credentials.resolve() is None:
        return script.no_credential(f"`{args.command}` goes through the Kaggle CLI, which")
    return run_wrapped(cmd, tool)


if __name__ == "__main__":
    sys.exit(main())
