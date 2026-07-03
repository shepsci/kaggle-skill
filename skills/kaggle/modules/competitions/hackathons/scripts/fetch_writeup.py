#!/usr/bin/env python3
"""Fetch a full writeup body from Kaggle's MCP server.

Fallback chain (never calls the known-broken `get_hackathon_write_up`):
    1. get_writeup       (--writeup-id)
    2. get_writeup_by_topic (--topic-id)
    3. get_writeup_by_slug  (--competition + --slug)

At least one identifier path must be supplied. If multiple are given, they are
tried in the order above and the first success wins. Outputs the parsed
writeup as JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared.mcp_client import (  # noqa: E402
    classify_result,
    extract_json,
    load_dotenv,
    mcp_call,
    resolve_token,
)


def fetch_by_id(writeup_id: int, token: str) -> tuple[str, dict]:
    resp = mcp_call("get_writeup", {"request": {"writeUpId": writeup_id}}, token=token)
    return classify_result(resp), resp


def fetch_by_topic(topic_id: int, token: str) -> tuple[str, dict]:
    resp = mcp_call(
        "get_writeup_by_topic",
        {"request": {"forumTopicId": topic_id}},
        token=token,
    )
    return classify_result(resp), resp


def fetch_by_slug(competition: str, slug: str, token: str) -> tuple[str, dict]:
    resp = mcp_call(
        "get_writeup_by_slug",
        {"request": {"competitionName": competition, "slug": slug}},
        token=token,
    )
    return classify_result(resp), resp


def is_role_gated(resp: dict) -> bool:
    """True if the response is a permission/role denial rather than not-found."""
    err = resp.get("error", {}) or {}
    msg = (err.get("message") or "").lower()
    if "permission" in msg or "denied" in msg or "host" in msg or "judge" in msg:
        return True
    result = resp.get("result", {}) or {}
    content = result.get("content")
    text = ""
    if isinstance(content, str):
        text = content.lower()
    elif isinstance(content, list):
        for c in content:
            if isinstance(c, dict):
                text += (c.get("text") or "").lower()
    return any(token in text for token in ("permission", "denied", "host", "judge", "role"))


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

    load_dotenv(REPO_ROOT / ".env", Path.home() / ".env")
    token = resolve_token()
    if not token:
        print("error: no Kaggle token found", file=sys.stderr)
        return 2

    attempts: list[tuple[str, dict]] = []

    if args.writeup_id:
        status, resp = fetch_by_id(args.writeup_id, token)
        attempts.append(("get_writeup", resp))
        if status == "ok":
            payload = extract_json(resp) or {}
            print('<untrusted-content source="kaggle-mcp" tool="get_writeup">')
            print(json.dumps({"endpoint": "get_writeup", "data": payload},
                             indent=2 if args.pretty else None))
            print("</untrusted-content>")
            return 0

    if args.topic_id:
        status, resp = fetch_by_topic(args.topic_id, token)
        attempts.append(("get_writeup_by_topic", resp))
        if status == "ok":
            payload = extract_json(resp) or {}
            print('<untrusted-content source="kaggle-mcp" tool="get_writeup_by_topic">')
            print(json.dumps({"endpoint": "get_writeup_by_topic", "data": payload},
                             indent=2 if args.pretty else None))
            print("</untrusted-content>")
            return 0

    if args.competition and args.slug:
        status, resp = fetch_by_slug(args.competition, args.slug, token)
        attempts.append(("get_writeup_by_slug", resp))
        if status == "ok":
            payload = extract_json(resp) or {}
            print('<untrusted-content source="kaggle-mcp" tool="get_writeup_by_slug">')
            print(json.dumps({"endpoint": "get_writeup_by_slug", "data": payload},
                             indent=2 if args.pretty else None))
            print("</untrusted-content>")
            return 0

    last_endpoint, last_resp = attempts[-1]
    gated = is_role_gated(last_resp)
    print(json.dumps({
        "status": "all_attempts_failed",
        "role_gated": gated,
        "attempts": [{"endpoint": ep, "raw": resp} for ep, resp in attempts],
    }, indent=2 if args.pretty else None), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
