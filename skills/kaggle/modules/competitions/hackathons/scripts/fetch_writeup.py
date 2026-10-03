#!/usr/bin/env python3
"""Read Kaggle writeups: title, authors, the body, and its links.

    fetch_writeup.py 123456
    fetch_writeup.py https://www.kaggle.com/competitions/<competition>/writeups/<slug>
    fetch_writeup.py <url> <url> <url>              several, one block each
    fetch_writeup.py --topic-id 654321
    fetch_writeup.py --competition <competition> --slug <slug>

The identifiers are tried in this order and the first that answers wins:
`get_writeup` (writeup id), `get_writeup_by_topic` (forum topic id),
`get_writeup_by_slug` (competition and slug). Published writeups are public:
no credential is needed.

The body is printed once, as Markdown, and cut after 8,000 characters with a
note (--max-chars 0 prints it all). --json gives the same fields as JSON and
--full the server's whole answer, which holds the body twice (Markdown and
HTML) and the authors' profile data.

`get_hackathon_write_up` is not used: it takes the roster row id (`row_id`
from list_writeups.py), not the writeup id, and needs the competition name.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, script, text, untrusted  # noqa: E402

DEFAULT_MAX_CHARS = 8000
from shared.mcp_client import (  # noqa: E402
    EXIT_DENIED,
    EXIT_FAILED,
    EXIT_NO_CREDENTIAL,
    classify_result,
    extract_json,
    is_denied,
    mcp_call,
    resolve_token,
)

SOURCE = "kaggle-mcp"


def fetch_by_id(writeup_id: int, token: str = "") -> tuple[str, dict]:
    resp = mcp_call("get_writeup", {"request": {"writeUpId": writeup_id}}, token=token)
    return classify_result(resp), resp


def fetch_by_topic(topic_id: int, token: str = "") -> tuple[str, dict]:
    resp = mcp_call(
        "get_writeup_by_topic",
        {"request": {"forumTopicId": topic_id}},
        token=token,
    )
    return classify_result(resp), resp


def fetch_by_slug(competition: str, slug: str, token: str = "") -> tuple[str, dict]:
    resp = mcp_call(
        "get_writeup_by_slug",
        {"request": {"competitionName": competition, "slug": slug}},
        token=token,
    )
    return classify_result(resp), resp


def is_role_gated(resp: dict) -> bool:
    """True if the response is a permission/role denial rather than not-found."""
    return is_denied(resp)


_WRITEUP_URL_RE = re.compile(r"/competitions/([^/?#]+)/writeups/([^/?#]+)")
_TOPIC_URL_RE = re.compile(r"/discussions?/(?:[^/?#]+/)?(\d+)")


def parse_target(target: str) -> dict:
    """Read a writeup id, a writeup URL or a discussion URL into identifiers."""
    target = target.strip()
    if target.isdigit():
        return {"writeup_id": int(target)}
    match = _WRITEUP_URL_RE.search(target)
    if match:
        return {"competition": match.group(1), "slug": match.group(2)}
    match = _TOPIC_URL_RE.search(target)
    if match:
        return {"topic_id": int(match.group(1))}
    raise ValueError("give a writeup id, a writeup URL or a discussion URL")


def summarize(endpoint: str, payload: dict) -> dict:
    """The writeup reduced to what a reader needs. The body appears once."""
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    # `content` is the same body rendered as HTML.
    body = message.get("raw_markdown") or text.html_to_text(message.get("content") or "")
    votes = message.get("votes") if isinstance(message.get("votes"), dict) else {}
    links = []
    for link in payload.get("write_up_links") or []:
        if isinstance(link, dict) and link.get("url"):
            links.append(
                {"title": link.get("title") or link.get("description") or "", "url": link["url"]}
            )
    return {
        "endpoint": endpoint,
        "writeup_id": payload.get("id"),
        "topic_id": payload.get("topic_id"),
        "slug": payload.get("slug"),
        "title": payload.get("title") or "",
        "subtitle": payload.get("subtitle") or "",
        "authors": payload.get("authors") or "",
        "url": text.absolute_url(payload.get("url")),
        "published": payload.get("publish_time") or payload.get("create_time"),
        "votes": votes.get("total_votes"),
        "license": (payload.get("license") or {}).get("name")
        if isinstance(payload.get("license"), dict)
        else None,
        "body": body,
        "links": links,
    }


def text_lines(summary: dict, max_chars: int = 0) -> tuple[list[str], int]:
    """The writeup as text. Returns ``(lines, characters of the body left out)``."""
    lines = [f"# {summary['title']}"]
    if summary["subtitle"]:
        lines.append(summary["subtitle"])
    facts = [f"by {summary['authors']}"] if summary["authors"] else []
    if summary["published"]:
        facts.append(f"published {text.day(summary['published'])}")
    if summary["votes"] is not None:
        facts.append(f"{summary['votes']} votes")
    if facts:
        lines.append(" · ".join(facts))
    if summary["url"]:
        lines.append(summary["url"])
    body = summary["body"]
    cut = 0
    if max_chars and len(body) > max_chars:
        cut = len(body) - max_chars
        body = body[:max_chars].rstrip()
    lines += ["", body]
    if summary["links"]:
        lines += ["", "Links:"]
        lines += [
            f"- {link['title'] + ': ' if link['title'] else ''}{link['url']}"
            for link in summary["links"]
        ]
    return lines, cut


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read Kaggle writeups: title, authors, the body, and its links.",
        epilog="No credential is needed for a published writeup.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="target",
        help="Writeup ids, writeup URLs, or discussion URLs; each is printed in its own block",
    )
    parser.add_argument("--writeup-id", type=int, help="The writeup id (get_writeup)")
    parser.add_argument("--topic-id", type=int, help="The forum topic id (get_writeup_by_topic)")
    parser.add_argument("--competition", help="With --slug: the competition (get_writeup_by_slug)")
    parser.add_argument("--slug", help="With --competition: the writeup slug")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        metavar="N",
        help=f"Cut each body after N characters; 0 for no limit (default: {DEFAULT_MAX_CHARS})",
    )
    script.add_json(parser)
    script.add_full(parser)
    args = parser.parse_args(argv)

    wanted: list[dict] = []
    for target in args.targets:
        try:
            wanted.append(parse_target(target))
        except ValueError as exc:
            parser.error(f"{exc}: {target}")
    named = {
        "writeup_id": args.writeup_id,
        "topic_id": args.topic_id,
        "competition": args.competition,
        "slug": args.slug,
    }
    if any(value is not None for value in named.values()):
        if len(wanted) > 1:
            parser.error("--writeup-id, --topic-id and --slug name one writeup; give no targets")
        # The options fill in what a single target left out.
        first = wanted[0] if wanted else {}
        wanted = [{**{k: v for k, v in named.items() if v is not None}, **first}]
    if not wanted or not all(
        ids.get("writeup_id") or ids.get("topic_id") or (ids.get("competition") and ids.get("slug"))
        for ids in wanted
    ):
        parser.error("give a writeup id or URL, --topic-id, or --competition with --slug")

    credentials.load_configured_env_file()
    token = resolve_token()
    worst = 0
    for ids in wanted:
        code = read_one(ids, token, args)
        worst = worst or code
    return worst


def read_one(ids: dict, token: str, args: argparse.Namespace) -> int:
    """Print one writeup. Returns the exit code for it."""
    indent = 2 if args.pretty else None
    plan: list[tuple[str, object]] = []
    if ids.get("writeup_id"):
        plan.append(("get_writeup", lambda: fetch_by_id(ids["writeup_id"], token)))
    if ids.get("topic_id"):
        plan.append(("get_writeup_by_topic", lambda: fetch_by_topic(ids["topic_id"], token)))
    if ids.get("competition") and ids.get("slug"):
        plan.append(
            ("get_writeup_by_slug", lambda: fetch_by_slug(ids["competition"], ids["slug"], token))
        )

    attempts: list[tuple[str, str, dict]] = []
    for endpoint, fetch in plan:
        status, resp = fetch()
        attempts.append((endpoint, status, resp))
        if status != "ok":
            continue
        payload = extract_json(resp)
        if not isinstance(payload, dict):
            # A success with no JSON body is not a writeup. Try the next path.
            attempts[-1] = (endpoint, "empty", resp)
            continue
        attrs = {"source": SOURCE, "tool": endpoint}
        if args.full:
            untrusted.emit_json({"endpoint": endpoint, "data": payload}, indent=indent, **attrs)
            return 0
        summary = summarize(endpoint, payload)
        if args.json:
            untrusted.emit_json(summary, indent=indent, **attrs)
            return 0
        lines, cut = text_lines(summary, args.max_chars)
        with untrusted.Block(**attrs) as block:
            for line in lines:
                block.write(line)
        if cut:
            print(
                f"The body was cut: {cut:,} more characters. Add --max-chars 0 to read all of it."
            )
        return 0

    last_resp = attempts[-1][2]
    gated = any(is_role_gated(resp) for _, _, resp in attempts)
    unauthenticated = any(status == "unauthenticated" for _, status, _ in attempts)
    untrusted.emit_json(
        {
            "status": "all_attempts_failed",
            "role_gated": gated,
            "attempts": [
                {"endpoint": ep, "status": status, "raw": resp} for ep, status, resp in attempts
            ],
        },
        source=SOURCE,
        tool="fetch_writeup",
        stream="stderr",
        indent=indent,
        file=sys.stderr,
    )
    if unauthenticated:
        if token:
            print("error: the configured Kaggle credential was not accepted", file=sys.stderr)
        else:
            print(
                "error: this writeup needs Kaggle credentials and none were found", file=sys.stderr
            )
        return EXIT_NO_CREDENTIAL
    if gated or is_role_gated(last_resp):
        print("error: permission denied for this account or role", file=sys.stderr)
        return EXIT_DENIED
    print("error: no writeup found by the identifiers given", file=sys.stderr)
    return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
