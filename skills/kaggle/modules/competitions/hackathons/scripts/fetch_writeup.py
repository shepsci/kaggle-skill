#!/usr/bin/env python3
"""Fetch a full writeup body from Kaggle's MCP server.

Fallback chain:
    1. get_writeup          (--writeup-id)
    2. get_writeup_by_topic (--topic-id)
    3. get_writeup_by_slug  (--competition + --slug)

At least one identifier path must be supplied. If multiple are given, they are
tried in the order above and the first success wins. Prints the writeup as
JSON inside one untrusted-content block.

`get_hackathon_write_up` is not part of the chain: it takes the roster row id
(`row_id` from list_writeups.py), not the writeup id, and needs the
competition name as well.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, untrusted  # noqa: E402
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--writeup-id", type=int, help="Try get_writeup first")
    parser.add_argument("--topic-id", type=int, help="Try get_writeup_by_topic")
    parser.add_argument("--competition", help="Used with --slug for get_writeup_by_slug")
    parser.add_argument("--slug", help="Used with --competition for get_writeup_by_slug")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    if not (args.writeup_id or args.topic_id or (args.competition and args.slug)):
        parser.error("supply --writeup-id, --topic-id, or --competition+--slug")

    credentials.load_configured_env_file()
    token = resolve_token()
    indent = 2 if args.pretty else None

    plan: list[tuple[str, object]] = []
    if args.writeup_id:
        plan.append(("get_writeup", lambda: fetch_by_id(args.writeup_id, token)))
    if args.topic_id:
        plan.append(("get_writeup_by_topic", lambda: fetch_by_topic(args.topic_id, token)))
    if args.competition and args.slug:
        plan.append(
            ("get_writeup_by_slug", lambda: fetch_by_slug(args.competition, args.slug, token))
        )

    attempts: list[tuple[str, str, dict]] = []
    for endpoint, fetch in plan:
        status, resp = fetch()
        attempts.append((endpoint, status, resp))
        if status != "ok":
            continue
        payload = extract_json(resp)
        if payload is None:
            # A success with no JSON body is not a writeup. Try the next path.
            attempts[-1] = (endpoint, "empty", resp)
            continue
        untrusted.emit_json(
            {"endpoint": endpoint, "data": payload}, source=SOURCE, tool=endpoint, indent=indent
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
