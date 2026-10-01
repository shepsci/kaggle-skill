#!/usr/bin/env python3
"""Probe the read-only tools of Kaggle's MCP server and report who may call them.

    python3 tools/probe_mcp.py --probe            # anonymous, and with the configured token
    python3 tools/probe_mcp.py --probe --oauth    # also with the token from `kaggle auth login`
    python3 tools/probe_mcp.py --probe --simulation-submission 12345678
    python3 tools/probe_mcp.py --render           # rewrite the tool table in mcp-reference.md

Maintainer tool. It is not part of the skill and nothing runs it automatically.
`--probe` calls the server and saves one status word per call in
tests/fixtures/mcp_probe_results.json. `--render` is offline: it rebuilds the
tool table in modules/references/mcp-reference.md from that file and from the
tool snapshot, so the table always matches what was measured.

`--simulation-submission` takes the id of one of your own submissions to a
simulation competition, so the two episode tools can be probed with a real
episode. The id is used for the calls and is not saved.

Only tools that read are called. Tools that create, update, upload, submit or
start something are listed as not tested. No token and no response body is
printed or saved.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared import credentials, kaggle_cli, untrusted  # noqa: E402
from shared.mcp_client import (  # noqa: E402
    classify_result,
    extract_json,
    mcp_call,
    mcp_list_tools,
)

HACKATHON = "kaggle-measuring-agi"
PAUSE_SECONDS = 0.3

# Tools that change something on Kaggle. They are never called from here.
WRITE_TOOLS = {
    "cancel_notebook_session",
    "create_benchmark_task_from_prompt",
    "create_code_competition_submission",
    "create_model",
    "create_notebook_session",
    "save_notebook",
    "start_competition_submission_upload",
    "submit_to_competition",
    "update_dataset_metadata",
    "update_model",
    "update_model_variation",
    "upload_dataset_file",
}

# Not called: `authorize` starts a sign-in flow for the calling client.
NOT_PROBED = {"authorize": "starts a sign-in flow"}

Args = dict[str, Any]


def _request(**fields: Any) -> Args:
    return {"request": fields}


# Tool name -> arguments, or a function of the lookup context that returns
# arguments (None when the context has no usable id).
STATIC_PROBES: dict[str, Args] = {
    "search_competitions": _request(search="titanic", pageSize=2),
    "get_competition": _request(competitionName="titanic"),
    "get_competition_data_files_summary": _request(competitionName="titanic"),
    "get_competition_leaderboard": _request(competitionName="titanic", pageSize=2),
    "list_competition_data_files": _request(competitionName="titanic", pageSize=3),
    "list_competition_data_tree_files": _request(competitionName="titanic", pageSize=3),
    "list_competition_pages": _request(competitionName="titanic"),
    "list_competition_topics": _request(competitionName="titanic"),
    "download_competition_data_file": _request(competitionName="titanic", fileName="train.csv"),
    "download_competition_data_files": _request(competitionName="titanic"),
    "download_competition_leaderboard": _request(competitionName="titanic"),
    "search_competition_submissions": _request(competitionName="titanic", pageSize=2),
    "search_datasets": _request(search="titanic", pageSize=2),
    "get_dataset_info": _request(ownerSlug="heptapod", datasetSlug="titanic"),
    "get_dataset_metadata": _request(ownerSlug="heptapod", datasetSlug="titanic"),
    "get_dataset_files_summary": _request(ownerSlug="heptapod", datasetSlug="titanic"),
    "list_dataset_files": _request(ownerSlug="heptapod", datasetSlug="titanic", pageSize=3),
    "list_dataset_tree_files": _request(ownerSlug="heptapod", datasetSlug="titanic", pageSize=3),
    "download_dataset": _request(ownerSlug="heptapod", datasetSlug="titanic"),
    "search_notebooks": _request(search="titanic", pageSize=2),
    "get_notebook_info": _request(userName="alexisbcook", kernelSlug="titanic-tutorial"),
    "list_notebook_files": _request(
        userName="alexisbcook", kernelSlug="titanic-tutorial", pageSize=3
    ),
    "get_notebook_session_status": _request(userName="alexisbcook", kernelSlug="titanic-tutorial"),
    "list_notebook_session_output": _request(
        userName="alexisbcook", kernelSlug="titanic-tutorial", pageSize=3
    ),
    "download_notebook_output": _request(ownerSlug="alexisbcook", kernelSlug="titanic-tutorial"),
    "list_models": _request(pageSize=2),
    "get_model": _request(ownerSlug="google", modelSlug="gemma"),
    "list_model_variations": _request(ownerSlug="google", modelSlug="gemma", pageSize=2),
    "get_model_variation": _request(
        ownerSlug="google", modelSlug="gemma", framework="transformers", instanceSlug="2b-it"
    ),
    "list_model_variation_versions": _request(
        ownerSlug="google",
        modelSlug="gemma",
        framework="transformers",
        instanceSlug="2b-it",
        pageSize=2,
    ),
    "list_model_variation_version_files": _request(
        ownerSlug="google",
        modelSlug="gemma",
        framework="transformers",
        instanceSlug="2b-it",
        versionNumber=1,
        pageSize=2,
    ),
    "download_model_variation_version": _request(
        ownerSlug="google",
        modelSlug="gemma",
        framework="transformers",
        instanceSlug="2b-it",
        versionNumber=1,
        path="config.json",
    ),
    "list_forums": _request(),
    "get_forum": _request(forumSlug="getting-started"),
    "list_forum_topics": _request(searchQuery="titanic"),
    "search_content": _request(filters={"query": "titanic"}, maxPageSize=2),
    "get_user_profile": _request(userName="alexisbcook"),
    "get_accelerator_quota": _request(),
    "get_benchmark_leaderboard": _request(ownerSlug="kaggle", benchmarkSlug="icml-2025-experts"),
    "get_hackathon_overview": _request(competitionName=HACKATHON),
    "list_hackathon_tracks": _request(competitionName=HACKATHON),
    "list_hackathon_write_ups": _request(competitionName=HACKATHON, pageSize=2, winner=True),
    "download_hackathon_write_ups": _request(competitionName=HACKATHON),
}

DYNAMIC_PROBES: dict[str, Callable[[dict], Args | None]] = {
    "get_hackathon_write_up": lambda c: (
        c.get("row_id") and _request(competitionName=HACKATHON, hackathonWriteUpId=c["row_id"])
    ),
    "get_writeup": lambda c: c.get("writeup_id") and _request(writeUpId=c["writeup_id"]),
    "get_resolved_writeup_links": lambda c: (
        c.get("writeup_id") and _request(writeUpId=c["writeup_id"])
    ),
    "get_writeup_by_slug": lambda c: (
        c.get("writeup_slug") and _request(competitionName=HACKATHON, slug=c["writeup_slug"])
    ),
    "get_writeup_by_topic": lambda c: c.get("topic_id") and _request(forumTopicId=c["topic_id"]),
    "get_forum_topic": lambda c: c.get("topic_id") and _request(forumTopicId=c["topic_id"]),
    "list_topic_messages": lambda c: (
        c.get("competition_topic_id")
        and _request(competitionName="titanic", topicId=c["competition_topic_id"], pageSize=2)
    ),
    "get_dataset_status": lambda c: (
        c.get("own_dataset")
        and _request(ownerSlug=c["own_dataset"][0], datasetSlug=c["own_dataset"][1])
    ),
    "get_competition_submission": lambda c: (
        c.get("submission_ref") and _request(ref=c["submission_ref"])
    ),
    "download_competition_submission": lambda c: (
        c.get("submission_ref") and _request(submissionId=c["submission_ref"])
    ),
    "list_submission_episodes": lambda c: (
        (c.get("simulation_submission") or c.get("submission_ref"))
        and _request(submissionId=c.get("simulation_submission") or c["submission_ref"])
    ),
    "get_episode_replay": lambda c: c.get("episode_id") and _request(episodeId=c["episode_id"]),
    "get_episode_agent_logs": lambda c: (
        c.get("episode_id") and _request(episodeId=c["episode_id"], agentIndex=0)
    ),
    "list_team_public_submissions": lambda c: c.get("team_id") and _request(teamId=c["team_id"]),
}

# Read tools that need an id this script has no safe way to find.
NO_ARGUMENTS = {
    "download_notebook_output_zip": "needs a notebook session id",
}


RESULTS = REPO_ROOT / "tests" / "fixtures" / "mcp_probe_results.json"
SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "mcp_tools_snapshot.json"
REFERENCE = REPO_ROOT / "skills" / "kaggle" / "modules" / "references" / "mcp-reference.md"
TABLE_START, TABLE_END = "<!-- mcp-tools:start -->", "<!-- mcp-tools:end -->"

GROUPS: dict[str, list[str]] = {
    "Competitions": [
        "search_competitions",
        "get_competition",
        "list_competition_pages",
        "get_competition_data_files_summary",
        "list_competition_data_files",
        "list_competition_data_tree_files",
        "download_competition_data_file",
        "download_competition_data_files",
        "get_competition_leaderboard",
        "download_competition_leaderboard",
        "list_competition_topics",
        "list_topic_messages",
        "search_competition_submissions",
        "get_competition_submission",
        "download_competition_submission",
        "list_team_public_submissions",
        "start_competition_submission_upload",
        "submit_to_competition",
        "create_code_competition_submission",
    ],
    "Datasets": [
        "search_datasets",
        "get_dataset_info",
        "get_dataset_metadata",
        "get_dataset_files_summary",
        "get_dataset_status",
        "list_dataset_files",
        "list_dataset_tree_files",
        "download_dataset",
        "update_dataset_metadata",
        "upload_dataset_file",
    ],
    "Notebooks": [
        "search_notebooks",
        "get_notebook_info",
        "list_notebook_files",
        "get_notebook_session_status",
        "list_notebook_session_output",
        "download_notebook_output",
        "download_notebook_output_zip",
        "save_notebook",
        "create_notebook_session",
        "cancel_notebook_session",
    ],
    "Models": [
        "list_models",
        "get_model",
        "list_model_variations",
        "get_model_variation",
        "list_model_variation_versions",
        "list_model_variation_version_files",
        "download_model_variation_version",
        "create_model",
        "update_model",
        "update_model_variation",
    ],
    "Forums": ["list_forums", "get_forum", "list_forum_topics", "get_forum_topic"],
    "Hackathons and writeups": [
        "get_hackathon_overview",
        "list_hackathon_tracks",
        "list_hackathon_write_ups",
        "get_hackathon_write_up",
        "download_hackathon_write_ups",
        "get_writeup",
        "get_writeup_by_slug",
        "get_writeup_by_topic",
        "get_resolved_writeup_links",
    ],
    "Benchmarks": ["get_benchmark_leaderboard", "create_benchmark_task_from_prompt"],
    "Simulation episodes": [
        "list_submission_episodes",
        "get_episode_replay",
        "get_episode_agent_logs",
    ],
    "Account and search": [
        "authorize",
        "get_user_profile",
        "get_accelerator_quota",
        "search_content",
    ],
}

# Notes are written by hand. Server text is never copied into the table.
NOTES: dict[str, str] = {
    "authorize": "Starts sign-in for clients that support it. Takes no `request` object.",
    "list_competition_pages": "Rules, evaluation, data description, and the other host pages.",
    "search_competition_submissions": "Your own submissions.",
    "get_competition_submission": "Takes `ref`, the submission id.",
    "download_competition_submission": "Returns a link to the file of one of your submissions.",
    "list_team_public_submissions": "Takes the `team_id` from the leaderboard.",
    "get_dataset_status": "Answers for datasets you own. For others it says not found.",
    "get_accelerator_quota": "Weekly GPU and TPU use for the whole account.",
    "search_content": '`filters` is required: `{"filters": {"query": "..."}}`.',
    "list_hackathon_write_ups": "Hosts, judges, and teammates only. `winner: true` keeps "
    "winners; `winnerStatus` is ignored.",
    "get_hackathon_write_up": "Takes the roster row `id` plus `competitionName`, not the "
    "writeup id.",
    "download_hackathon_write_ups": "Hosts only.",
    "get_writeup": "Takes the writeup id (`write_up.id` in a roster row).",
    "get_resolved_writeup_links": "Hosts, judges, and admins only.",
    "list_submission_episodes": "Takes a submission id from a simulation competition.",
    "get_episode_replay": "Takes an episode `id` from `list_submission_episodes`.",
    "get_episode_agent_logs": "`agentIndex` counts from 0.",
}


def _call(tool: str, args: Args, token: str) -> dict:
    """Call a tool, retrying the server's generic transient failure twice."""
    response: dict = {}
    for attempt in range(3):
        time.sleep(PAUSE_SECONDS if attempt == 0 else 2.0)
        response = mcp_call(tool, args, token=token, timeout=60)
        if not classify_result(response).startswith("error: An error occurred invoking"):
            break
    return response


def build_context(token: str, simulation_submission: int | None = None) -> dict:
    """Look up real ids for the tools that need one. Uses read calls only."""
    context: dict = {}
    if simulation_submission and token:
        context["simulation_submission"] = simulation_submission
        episodes = (
            extract_json(
                _call(
                    "list_submission_episodes", _request(submissionId=simulation_submission), token
                )
            )
            or {}
        )
        if episodes.get("episodes"):
            context["episode_id"] = episodes["episodes"][0].get("id")

    roster = (
        extract_json(
            _call("list_hackathon_write_ups", STATIC_PROBES["list_hackathon_write_ups"], token)
        )
        or {}
    )
    rows = roster.get("hackathon_write_ups") or []
    if rows:
        write_up = rows[0].get("write_up") or {}
        context["row_id"] = rows[0].get("id")
        context["writeup_id"] = write_up.get("id")
        url = write_up.get("url") or ""
        context["writeup_slug"] = url.rstrip("/").rsplit("/", 1)[-1] if url else None

    if context.get("writeup_id"):
        full = (
            extract_json(_call("get_writeup", _request(writeUpId=context["writeup_id"]), "")) or {}
        )
        context["topic_id"] = full.get("topic_id")

    topics = (
        extract_json(_call("list_competition_topics", STATIC_PROBES["list_competition_topics"], ""))
        or {}
    )
    for key in ("topics", "forum_topics"):
        if topics.get(key):
            context["competition_topic_id"] = topics[key][0].get("id")
            break

    if token:
        board = (
            extract_json(
                _call(
                    "get_competition_leaderboard",
                    STATIC_PROBES["get_competition_leaderboard"],
                    token,
                )
            )
            or {}
        )
        for rows in board.values():
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                context["team_id"] = rows[0].get("team_id") or rows[0].get("teamId")
                break

        mine = (
            extract_json(
                _call(
                    "search_competition_submissions",
                    STATIC_PROBES["search_competition_submissions"],
                    token,
                )
            )
            or {}
        )
        if mine.get("submissions"):
            context["submission_ref"] = mine["submissions"][0].get("ref")

        listing = kaggle_cli.run(
            ["datasets", "list", "--mine", "--format", "json", "--page-size", "1"], timeout=60
        )
        rows, _ = kaggle_cli.json_rows(listing.stdout)
        if listing.returncode == 0 and rows and isinstance(rows[0], dict) and rows[0].get("ref"):
            context["own_dataset"] = tuple(str(rows[0]["ref"]).split("/")[-2:])
    return context


def oauth_token() -> str:
    """OAuth access token from `kaggle auth login`, or '' when there is none."""
    return credentials.oauth_access_token()


def probe_all(identities: dict[str, str], context: dict, tool_names: list[str]) -> dict[str, dict]:
    report: dict[str, dict] = {}
    for name in tool_names:
        if name in WRITE_TOOLS:
            report[name] = {"kind": "write", "note": "not probed: changes something on Kaggle"}
            continue
        if name in NOT_PROBED:
            report[name] = {"kind": "other", "note": f"not probed: {NOT_PROBED[name]}"}
            continue
        if name in NO_ARGUMENTS:
            report[name] = {"kind": "read", "note": f"not probed: {NO_ARGUMENTS[name]}"}
            continue
        if name in STATIC_PROBES:
            args = STATIC_PROBES[name]
        elif name in DYNAMIC_PROBES:
            args = DYNAMIC_PROBES[name](context) or None
            if args is None:
                reason = (
                    "needs a simulation episode id"
                    if name.startswith("get_episode_")
                    else "no id found for it"
                )
                report[name] = {"kind": "read", "note": f"not probed: {reason}"}
                continue
        else:
            report[name] = {"kind": "unknown", "note": "not probed: new tool, no probe written"}
            continue
        entry: dict = {"kind": "read"}
        for label, token in identities.items():
            entry[label] = classify_result(_call(name, args, token))
        report[name] = entry
    return report


def _cell(status: str | None, anonymous: bool = False) -> str:
    """One table cell from a status word. Never copies the server's text."""
    if status is None:
        return "not tested"
    if status == "ok":
        return "yes"
    if status == "unauthenticated" or anonymous:
        return "no"
    if status.startswith("error:") and re.search(
        r"permission|denied|\bonly\b.+\bcan\b", status, re.IGNORECASE
    ):
        return "role-gated"
    if status == "error: Not found":
        return "not found"
    return "error"


def _main_arguments(fields: list[str], limit: int = 6) -> str:
    """The argument names that matter. Helper variants (`hasX`, `xNullable`) are dropped."""
    kept = [
        f
        for f in fields
        if not re.match(r"has[A-Z]", f) and not f.endswith(("Nullable", "Setter", "Case"))
    ]
    shown = ", ".join(f"`{name}`" for name in kept[:limit])
    return shown + (", …" if len(kept) > limit else "")


def render_table(results: dict, snapshot: dict) -> str:
    """Markdown for the tool table, grouped by area."""
    tools = results["tools"]
    with_credential = "api_token" if "api_token" in results["identities"] else "oauth"
    lines: list[str] = []
    for group, names in GROUPS.items():
        lines += [
            f"### {group}",
            "",
            "| Tool | Kind | No credential | With a credential | Main arguments | Notes |",
            "|---|---|---|---|---|---|",
        ]
        for name in names:
            entry = tools.get(name, {"kind": "unknown", "note": "not probed"})
            kind = {"read": "read", "write": "write"}.get(entry["kind"], "other")
            if "note" in entry:
                anonymous = credentialed = "not tested"
            else:
                anonymous = _cell(entry.get("anonymous"), anonymous=True)
                credentialed = _cell(entry.get(with_credential))
            arguments = _main_arguments(snapshot["tools"][name]["fields"]) or "none"
            lines.append(
                f"| `{name}` | {kind} | {anonymous} | {credentialed} | {arguments} "
                f"| {NOTES.get(name, '')} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_into_reference() -> int:
    results = json.loads(RESULTS.read_text())
    snapshot = json.loads(SNAPSHOT.read_text())
    grouped = [name for names in GROUPS.values() for name in names]
    missing = sorted(set(snapshot["tools"]) - set(grouped))
    extra = sorted(set(grouped) - set(snapshot["tools"]))
    if missing or extra or len(grouped) != len(set(grouped)):
        print(
            f"error: GROUPS does not match the snapshot; missing {missing}, extra {extra}",
            file=sys.stderr,
        )
        return 1
    text = REFERENCE.read_text()
    if TABLE_START not in text or TABLE_END not in text:
        print(
            f"error: {REFERENCE.name} has no {TABLE_START} ... {TABLE_END} block", file=sys.stderr
        )
        return 1
    head, rest = text.split(TABLE_START, 1)
    tail = rest.split(TABLE_END, 1)[1]
    REFERENCE.write_text(
        f"{head}{TABLE_START}\n\n{render_table(results, snapshot)}\n{TABLE_END}{tail}"
    )
    print(f"rewrote the tool table in {REFERENCE.relative_to(REPO_ROOT)}")
    return 0


def probe(use_oauth: bool, out_path: Path, simulation_submission: int | None = None) -> int:
    api_token = (credentials.api_token() or credentials.Credential("", "")).secret
    identities = {"anonymous": ""}
    if use_oauth:
        token = oauth_token()
        if not token:
            print(
                "error: no OAuth login found; run `kaggle auth login` or drop --oauth",
                file=sys.stderr,
            )
            return 2
        identities["oauth"] = token
    if api_token:
        identities["api_token"] = api_token
    else:
        print("note: no API token configured", file=sys.stderr)

    listed = mcp_list_tools()
    tool_names = sorted(t["name"] for t in (listed.get("result") or {}).get("tools", []))
    if not tool_names:
        print("error: could not list the server's tools", file=sys.stderr)
        return 1

    context = build_context(api_token or identities.get("oauth", ""), simulation_submission)
    report = probe_all(identities, context, tool_names)
    out_path.write_text(
        json.dumps(
            {
                "probed": datetime.date.today().isoformat(),
                "identities": list(identities),
                "tools": report,
            },
            indent=1,
        )
        + "\n"
    )

    # Status text can quote the server, so the table is printed as untrusted content.
    labels = list(identities)
    with untrusted.Block(source="kaggle-mcp", tool="probe_mcp") as block:
        block.write(" | ".join(["tool", "kind", *labels]))
        for name, entry in report.items():
            cells = [entry.get(label, "") for label in labels]
            block.write(
                " | ".join([name, entry["kind"], *cells])
                + (f" | {entry['note']}" if "note" in entry else "")
            )
    print(
        f"{len(tool_names)} tools listed; "
        f"{sum(1 for e in report.values() if 'note' not in e)} probed; "
        f"saved to {out_path}",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true", help="Call the server and save the results")
    mode.add_argument(
        "--render", action="store_true", help="Rewrite the tool table in mcp-reference.md (offline)"
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        help="With --probe: also use the token from `kaggle auth login`",
    )
    parser.add_argument(
        "--json",
        metavar="FILE",
        type=Path,
        default=RESULTS,
        help=f"With --probe: where to save (default {RESULTS.name})",
    )
    parser.add_argument(
        "--simulation-submission",
        metavar="ID",
        type=int,
        help="With --probe: one of your simulation-competition submission ids, "
        "to probe the episode tools",
    )
    args = parser.parse_args(argv)
    if args.render:
        return render_into_reference()
    return probe(args.oauth, args.json, args.simulation_submission)


if __name__ == "__main__":
    sys.exit(main())
