#!/usr/bin/env python3
"""Compare Kaggle's MCP tool list with the committed snapshot.

    python3 tools/mcp_snapshot.py --check     # exit 1 and list the changes if it differs
    python3 tools/mcp_snapshot.py --update    # rewrite the snapshot from the live server

`tools/list` needs no credentials, so this runs anywhere. The snapshot keeps
each tool's name and argument names; that is what the reference docs and the
scripts depend on.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared import untrusted  # noqa: E402
from shared.mcp_client import MCP_ENDPOINT, mcp_list_tools  # noqa: E402

SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "mcp_tools_snapshot.json"


def snapshot_from_tools(tools: list[dict]) -> dict[str, dict]:
    """Reduce a `tools/list` result to ``{name: {wrapper, fields}}``.

    ``wrapper`` is true when the arguments go inside a ``request`` object,
    which is every tool except ``authorize``.
    """
    snapshot: dict[str, dict] = {}
    for tool in sorted(tools, key=lambda t: t.get("name", "")):
        properties = (tool.get("inputSchema") or {}).get("properties") or {}
        if "request" in properties:
            fields = sorted((properties["request"].get("properties") or {}).keys())
            snapshot[tool["name"]] = {"wrapper": True, "fields": fields}
        else:
            snapshot[tool["name"]] = {"wrapper": False, "fields": sorted(properties.keys())}
    return snapshot


def diff(old: dict[str, dict], new: dict[str, dict]) -> list[str]:
    """Human-readable differences between two snapshots. Empty when they match."""
    changes: list[str] = []
    for name in sorted(set(new) - set(old)):
        changes.append(f"added tool: {name}")
    for name in sorted(set(old) - set(new)):
        changes.append(f"removed tool: {name}")
    for name in sorted(set(old) & set(new)):
        before, after = old[name], new[name]
        if before.get("wrapper") != after.get("wrapper"):
            changes.append(f"{name}: request wrapper changed to {after.get('wrapper')}")
        added = sorted(set(after["fields"]) - set(before["fields"]))
        removed = sorted(set(before["fields"]) - set(after["fields"]))
        if added:
            changes.append(f"{name}: new fields {', '.join(added)}")
        if removed:
            changes.append(f"{name}: removed fields {', '.join(removed)}")
    return changes


def fetch_live() -> dict[str, dict]:
    response = mcp_list_tools(timeout=60)
    tools = (response.get("result") or {}).get("tools") or []
    if not tools:
        raise RuntimeError("the server returned no tools")
    return snapshot_from_tools(tools)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Compare; exit 1 on any difference")
    mode.add_argument("--update", action="store_true", help="Rewrite the snapshot")
    args = parser.parse_args(argv)

    try:
        live = fetch_live()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.update:
        SNAPSHOT.write_text(
            json.dumps(
                {
                    "endpoint": MCP_ENDPOINT,
                    "captured": datetime.date.today().isoformat(),
                    "count": len(live),
                    "tools": live,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {SNAPSHOT.relative_to(REPO_ROOT)} ({len(live)} tools)")
        return 0

    committed = json.loads(SNAPSHOT.read_text())
    changes = diff(committed["tools"], live)
    if not changes:
        print(f"MCP tool list matches the snapshot ({len(live)} tools)")
        return 0
    print(f"MCP tool list changed since {committed.get('captured')}:")
    # Tool and field names come from the server.
    untrusted.emit_text("\n".join(changes), source="kaggle-mcp", tool="tools/list")
    return 1


if __name__ == "__main__":
    sys.exit(main())
