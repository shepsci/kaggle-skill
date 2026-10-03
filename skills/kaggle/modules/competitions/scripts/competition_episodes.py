#!/usr/bin/env python3
"""The games a simulation submission has played, and one game's replay or log.

    competition_episodes.py 56699264                      list the submission's episodes
    competition_episodes.py --replay 117015562            save a replay
    competition_episodes.py --logs 117015562 --agent 0    save your agent's log, print its end

The list reads `list_submission_episodes` on the Kaggle MCP server and needs a
credential. Replays and logs are files: they are downloaded with the Kaggle
CLI into --out (default ./downloads/episodes) and are not printed in full.
A log is available only for your own agent.

Team names are written by participants, so the list is printed inside an
untrusted-content block.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli, mcp_client, script, text, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = "list_submission_episodes"
DEFAULT_OUT = "downloads/episodes"


def episode_row(episode: dict, submission_id: int) -> dict:
    """One episode from the point of view of ``submission_id``."""
    agents = [a for a in episode.get("agents") or [] if isinstance(a, dict)]
    mine = next((a for a in agents if a.get("submission_id") == submission_id), None)
    others = [a for a in agents if a is not mine]
    kind = str(episode.get("type") or "").replace("EPISODE_TYPE_", "").lower()
    return {
        "id": episode.get("id"),
        "type": kind,
        "state": str(episode.get("state") or "").lower(),
        "ended": episode.get("end_time"),
        "agent_index": int(mine.get("index") or 0) if mine else None,
        "reward": mine.get("reward") if mine else None,
        "opponents": [
            {"team": a.get("team_name") or "", "reward": a.get("reward")} for a in others
        ],
    }


def summarize(rows: list[dict]) -> dict:
    rewards = [r["reward"] for r in rows if isinstance(r["reward"], (int, float))]
    ahead = 0
    compared = 0
    for row in rows:
        theirs = [o["reward"] for o in row["opponents"] if isinstance(o["reward"], (int, float))]
        if isinstance(row["reward"], (int, float)) and theirs:
            compared += 1
            ahead += row["reward"] > max(theirs)
    return {
        "episodes": len(rows),
        "by_type": dict(Counter(row["type"] for row in rows)),
        "by_state": dict(Counter(row["state"] for row in rows)),
        "mean_reward": sum(rewards) / len(rewards) if rewards else None,
        "higher_reward_than_every_opponent": ahead,
        "compared": compared,
    }


def list_episodes(submission_id: int, args: argparse.Namespace) -> int:
    token = mcp_client.resolve_token()
    if not token:
        return script.no_credential("the episode list")
    result = mcp_client.request(TOOL, {"submissionId": submission_id}, token=token, timeout=120)
    if not result.ok or not isinstance(result.data, dict):
        return result.fail(submission=submission_id)
    episodes = [e for e in result.data.get("episodes") or [] if isinstance(e, dict)]
    rows = [episode_row(e, submission_id) for e in episodes]
    rows.sort(key=lambda r: str(r["ended"] or ""), reverse=True)
    summary = summarize(rows)
    shown = rows[: args.limit]

    attrs = {"source": SOURCE, "tool": TOOL, "submission": submission_id}
    if args.json:
        untrusted.emit_json({"summary": summary, "episodes": shown}, **attrs)
        return script.EXIT_OK
    with untrusted.Block(**attrs) as block:
        kinds = ", ".join(f"{n} {kind}" for kind, n in sorted(summary["by_type"].items()))
        states = ", ".join(f"{n} {state}" for state, n in sorted(summary["by_state"].items()))
        block.write(f"{len(rows)} episodes of submission {submission_id}: {kinds}; {states}")
        if summary["mean_reward"] is not None:
            block.write(
                f"  mean reward {summary['mean_reward']:.6g}; higher than every opponent in "
                f"{summary['higher_reward_than_every_opponent']} of {summary['compared']}"
            )
        if shown:
            block.write(f"  latest {len(shown)}:")
            block.write(
                f"  {'episode':>10}  {'ended (UTC)':<16}  {'seat':>4}  {'reward':>10}  opponents"
            )
        for row in shown:
            moment = text.parse_time(row["ended"])
            ended = moment.strftime("%Y-%m-%d %H:%M") if moment else "-"
            seat = "-" if row["agent_index"] is None else str(row["agent_index"])
            rivals = "; ".join(
                f"{text.shorten(o['team'], 30)} {o['reward']}" for o in row["opponents"]
            )
            block.write(
                f"  {row['id']:>10}  {ended:<16}  {seat:>4}  {str(row['reward']):>10}  {rivals}"
            )
    if len(rows) > len(shown):
        print(f"Showing {len(shown)} of {len(rows)}. Add --limit {len(rows)} for all of them.")
    if shown:
        first = shown[0]
        seat = first["agent_index"] if first["agent_index"] is not None else 0
        print(
            f"Save a game with --replay EPISODE, or your agent's log with --logs EPISODE "
            f"--agent SEAT (for the latest: --logs {first['id']} --agent {seat})."
        )
    return script.EXIT_OK


def download(kind: str, episode: int, agent: int, out: Path, tail: int) -> int:
    """Download a replay or a log with the Kaggle CLI and describe the file."""
    if not kaggle_cli.installed():
        return script.missing_package("kaggle", "downloading a replay or a log")
    if credentials.resolve() is None:
        return script.no_credential("downloading a replay or a log")
    out.mkdir(parents=True, exist_ok=True)
    if kind == "replay":
        cli_args = ["competitions", "replay", str(episode), "--path", str(out), "--quiet"]
        target = out / f"episode-{episode}-replay.json"
    else:
        cli_args = ["competitions", "logs", str(episode), str(agent), "--path", str(out)]
        cli_args.append("--quiet")
        target = out / f"episode-{episode}-agent-{agent}-logs.json"
    result = kaggle_cli.run(cli_args, timeout=600)
    if result.returncode != 0 or not target.is_file():
        print(f"error: the {kind} could not be downloaded", file=sys.stderr)
        if (result.stdout + result.stderr).strip():
            untrusted.emit_text(
                result.stdout + result.stderr,
                source="kaggle-cli",
                tool=f"competitions.{kind}",
                stream="stderr",
                file=sys.stderr,
            )
        return kaggle_cli.exit_code(result) or script.EXIT_FAILED

    size = target.stat().st_size
    print(f"Saved {target} ({text.human_size(size)}).")
    content = target.read_text(encoding="utf-8", errors="replace")
    if kind == "replay":
        try:
            data = json.loads(content)
        except ValueError:
            return script.EXIT_OK
        if isinstance(data, dict):
            steps = data.get("steps")
            facts = [f"{len(steps):,} steps"] if isinstance(steps, list) else []
            facts.append("keys: " + ", ".join(sorted(str(k) for k in data)[:12]))
            # Key names come from the file, which Kaggle built from the agents' moves.
            untrusted.emit_text("; ".join(facts), source="kaggle-cli", tool="competitions.replay")
    elif tail:
        lines = content.splitlines() or [content]
        shown = "\n".join(lines[-tail:])[-4000:]
        # An agent's log holds whatever the agent printed.
        untrusted.emit_text(shown, source="kaggle-cli", tool="competitions.logs", episode=episode)
    return script.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The games a simulation submission has played, and one game's replay or log.",
        epilog="Needs a Kaggle credential. Replays and logs also need the Kaggle CLI.",
    )
    parser.add_argument("submission", nargs="?", type=int, help="Submission id: list its episodes")
    parser.add_argument("--replay", type=int, metavar="EPISODE", help="Save this episode's replay")
    parser.add_argument("--logs", type=int, metavar="EPISODE", help="Save your agent's log")
    parser.add_argument(
        "--agent",
        type=int,
        default=0,
        metavar="SEAT",
        help="With --logs: your agent's seat in that game, the list's seat column (default: 0)",
    )
    parser.add_argument(
        "--out", default=DEFAULT_OUT, metavar="DIR", help=f"Where to save (default: {DEFAULT_OUT})"
    )
    parser.add_argument(
        "--tail", type=int, default=40, metavar="N", help="With --logs: print the last N lines"
    )
    script.add_limit(parser, 10, "episodes")
    script.add_json(parser)
    args = parser.parse_args(argv)

    chosen = [x for x in (args.submission, args.replay, args.logs) if x is not None]
    if len(chosen) != 1:
        parser.error("give a submission id, or --replay EPISODE, or --logs EPISODE")

    credentials.load_configured_env_file()
    if args.replay is not None:
        return download("replay", args.replay, 0, Path(args.out), 0)
    if args.logs is not None:
        return download("logs", args.logs, args.agent, Path(args.out), args.tail)
    return list_episodes(args.submission, args)


if __name__ == "__main__":
    sys.exit(main())
