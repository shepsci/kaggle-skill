#!/usr/bin/env python3
"""A competition's leaderboard: the top, your row, the medal lines, what moved.

    competition_leaderboard.py rsna-knee-abnormality-detection
    competition_leaderboard.py titanic --top 20 --no-save

Prints the top rows, your team's rank and score with the gap to the leader,
and, when the competition awards medals, the score at each medal line. Each
run saves a snapshot under ./.kaggle-skill/leaderboard/<competition>/ and
compares with the one before, so the second run onwards says what moved.

Needs a credential: an API token or `kaggle auth login`. The public
leaderboard is not the final one: the private leaderboard decides. After the
deadline, --private prints the private one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, mcp_client, script, text, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = competition.LEADERBOARD_TOOL
DEFAULT_MAX_ROWS = 2000
MEDALS = ("gold", "silver", "bronze")


def snapshot_dir(slug: str) -> Path:
    return script.state_dir() / "leaderboard" / slug


def latest_snapshot(slug: str, board: str = "public") -> dict | None:
    """The newest saved snapshot of this board, or None."""
    try:
        files = sorted(snapshot_dir(slug).glob("*.json"))
    except OSError:
        return None
    for file in reversed(files):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("rows") and data.get("board", "public") == board:
            return data
    return None


def save_snapshot(slug: str, snapshot: dict) -> Path:
    name = snapshot["time"].replace(":", "").replace("-", "") + ".json"
    return script.write_state(snapshot_dir(slug) / name, json.dumps(snapshot, ensure_ascii=False))


def find_team(rows: list[dict], team: str, near_rank: int | None) -> dict | None:
    """Your row. Team names are not unique, so the rank Kaggle reports comes first.

    The row at that rank when its name is yours; else the row with your name
    nearest that rank; else the row at that rank.
    """
    at_rank = rows[near_rank - 1] if near_rank and 0 < near_rank <= len(rows) else None
    if team:
        if at_rank is not None and at_rank["team"] == team:
            return at_rank
        named = [row for row in rows if row["team"] == team]
        if named:
            return min(named, key=lambda row: abs(row["rank"] - (near_rank or row["rank"])))
    return at_rank


def gap(mine: str | None, other: str | None, higher: bool | None) -> float | None:
    """How far ``mine`` is behind ``other``: positive means behind."""
    a, b = competition.score_value(mine), competition.score_value(other)
    if a is None or b is None or higher is None:
        return None
    return (b - a) if higher else (a - b)


def build(
    slug: str, token: str, top: int, max_rows: int, private: bool = False
) -> tuple[dict | None, mcp_client.Result | int]:
    """The snapshot, or None with the failed result (or an exit code)."""
    facts_result = competition.fetch_facts(slug, token)
    if not facts_result.ok or not isinstance(facts_result.data, dict):
        return None, facts_result
    info = competition.facts(slug, facts_result.data)
    deadline = text.parse_time(info.get("deadline"))
    ended = deadline is not None and deadline < text.now_utc()
    if private and not ended:
        return None, script.fail(
            "the private leaderboard is shown only after the deadline", script.EXIT_USAGE
        )
    team_count = int(info.get("team_count") or 0)
    medal_ranks = competition.medal_ranks(team_count) if info["awards_points"] else {}

    wanted = max([top, int(info.get("user_rank") or 0), *medal_ranks.values()])
    rows, more, board_result = competition.fetch_leaderboard(
        slug, token, min(wanted, max_rows), public=not private
    )
    if not board_result.ok:
        return None, board_result

    # The team name is on your own submissions, not on the competition's facts.
    mine_name = ""
    if info["user_has_entered"]:
        own, _ = competition.fetch_submissions(slug, token, limit=1)
        mine_name = own[0]["team_name"] if own else ""
    # After the deadline Kaggle's rank is the private one: on the public board
    # the row at that rank is another team's, so only the name finds yours.
    rank_here = info.get("user_rank") if (private or not ended) else None
    mine = find_team(rows, mine_name, rank_here) if info["user_has_entered"] else None

    higher = competition.higher_is_better(rows)
    lines = {}
    for medal, rank in medal_ranks.items():
        if 0 < rank <= len(rows):
            lines[medal] = {"rank": rank, "score": rows[rank - 1]["score"]}
        elif rank > 0:
            lines[medal] = {"rank": rank, "score": None}
    snapshot = {
        "time": text.now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "competition": slug,
        "board": "private" if private else "public",
        "ended": ended,
        "title": info["title"],
        "team_count": team_count,
        "higher_is_better": higher,
        "awards_medals": info["awards_points"],
        "user_rank": info.get("user_rank"),
        "mine": mine,
        "medal_lines": lines,
        "rows": rows,
        "more_rows": more,
    }
    return snapshot, board_result


def movement(before: dict, now: dict) -> list[str]:
    """What changed between two snapshots, as short phrases."""
    changes = []
    old_mine, new_mine = before.get("mine") or {}, now.get("mine") or {}
    if old_mine.get("rank") and new_mine.get("rank") and old_mine["rank"] != new_mine["rank"]:
        changes.append(f"your rank {old_mine['rank']} → {new_mine['rank']}")
    if old_mine.get("score") and new_mine.get("score") and old_mine["score"] != new_mine["score"]:
        changes.append(f"your score {old_mine['score']} → {new_mine['score']}")
    old_top = (before.get("rows") or [{}])[0].get("score")
    new_top = (now.get("rows") or [{}])[0].get("score")
    if old_top and new_top and old_top != new_top:
        changes.append(f"leader {old_top} → {new_top}")
    for medal in MEDALS:
        old_line = (before.get("medal_lines") or {}).get(medal) or {}
        new_line = (now.get("medal_lines") or {}).get(medal) or {}
        if old_line.get("score") and new_line.get("score"):
            if old_line["score"] != new_line["score"]:
                changes.append(f"{medal} line {old_line['score']} → {new_line['score']}")
    if before.get("team_count") != now.get("team_count"):
        changes.append(f"teams {before.get('team_count'):,} → {now.get('team_count'):,}")
    return changes


def text_lines(snapshot: dict, top: int, previous: dict | None) -> list[str]:
    higher = snapshot["higher_is_better"]
    direction = {True: "higher is better", False: "lower is better", None: "direction not shown"}
    board = snapshot.get("board", "public")
    lines = [
        f"{board.capitalize()} leaderboard of {snapshot['competition']}: "
        f"{snapshot['team_count']:,} teams, {direction[higher]}",
        f"  {'rank':>5}  {'score':<12}  team",
    ]
    for row in snapshot["rows"][:top]:
        lines.append(f"  {row['rank']:>5}  {row['score']:<12}  {text.shorten(row['team'], 50)}")

    mine = snapshot["mine"]
    leader = snapshot["rows"][0]["score"] if snapshot["rows"] else None
    if mine:
        behind = gap(mine["score"], leader, higher)
        tail = f"; {behind:.5g} behind the leader" if behind else ""
        lines.append(f"  you: rank {mine['rank']}, score {mine['score']} ({mine['team']}){tail}")
    elif snapshot.get("user_rank") and snapshot.get("ended") and board == "public":
        lines.append(
            f"  you: rank {snapshot['user_rank']} on the private leaderboard; "
            "your team's row was not found on this one"
        )
    elif snapshot.get("user_rank"):
        lines.append(
            f"  you: rank {snapshot['user_rank']}; your row is past the "
            f"{len(snapshot['rows']):,} rows that were read"
        )
    else:
        lines.append("  you: not on this leaderboard")

    if snapshot["awards_medals"] and snapshot["medal_lines"]:
        if snapshot.get("ended"):
            lines.append("  medal lines at the final team count:")
        else:
            lines.append("  medal lines at today's team count (they move as teams join):")
        for medal in MEDALS:
            line = snapshot["medal_lines"].get(medal)
            if not line:
                continue
            if line["score"] is None:
                lines.append(f"    {medal:<6}  rank {line['rank']:>5}  (not read)")
                continue
            note = ""
            if mine:
                behind = gap(mine["score"], line["score"], higher)
                ranks = mine["rank"] - line["rank"]
                if ranks <= 0:
                    note = "  you are inside"
                elif behind:
                    note = f"  you are {behind:.5g} and {ranks} ranks behind"
                elif higher is None:
                    note = f"  you are {ranks} ranks behind"
                else:
                    note = f"  you are level on score, {ranks} ranks behind"
            lines.append(f"    {medal:<6}  rank {line['rank']:>5}  score {line['score']}{note}")
    elif not snapshot["awards_medals"]:
        lines.append("  medals: this competition awards none")

    if previous:
        changes = movement(previous, snapshot)
        since = text.when(previous.get("time"), text.parse_time(snapshot["time"]))
        lines.append(f"  since {since}: " + ("; ".join(changes) if changes else "nothing moved"))
    return lines


def ended_note(snapshot: dict) -> str | None:
    """After the deadline, where the final ranks are."""
    if snapshot.get("ended") and snapshot.get("board", "public") == "public":
        return (
            "The competition has ended: the private leaderboard decides the final ranks. "
            "Add --private to see it."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="A competition's leaderboard: the top, your row, the medal lines, what moved.",
        epilog="Needs a Kaggle credential: an API token or `kaggle auth login`.",
    )
    script.add_competition(parser)
    parser.add_argument(
        "--top", type=script.positive_int, default=10, metavar="N", help="Rows to print"
    )
    parser.add_argument(
        "--max-rows",
        type=script.positive_int,
        default=DEFAULT_MAX_ROWS,
        metavar="N",
        help=f"Read at most N rows to find your row and the medal lines "
        f"(default: {DEFAULT_MAX_ROWS})",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="The private leaderboard, which decides the final ranks (after the deadline only)",
    )
    parser.add_argument(
        "--no-save", action="store_true", help="Do not save a snapshot for the next comparison"
    )
    script.add_json(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
    if not token:
        return script.no_credential("the leaderboard")

    snapshot, result = build(slug, token, args.top, args.max_rows, private=args.private)
    if snapshot is None:
        return result if isinstance(result, int) else result.fail(competition=slug)
    previous = latest_snapshot(slug, snapshot["board"])

    attrs = {"source": SOURCE, "tool": TOOL, "competition": slug}
    if args.json:
        document = {**snapshot, "rows": snapshot["rows"][: args.top]}
        document["changes"] = movement(previous, snapshot) if previous else None
        untrusted.emit_json(document, indent=2 if args.pretty else None, **attrs)
    else:
        # Team names are written by participants.
        with untrusted.Block(**attrs) as block:
            for line in text_lines(snapshot, args.top, previous):
                block.write(line)
        note = ended_note(snapshot)
        if note:
            print(note)
    if not args.no_save:
        try:
            print(f"Snapshot saved: {save_snapshot(slug, snapshot)}")
        except OSError as exc:
            script.warn(f"the snapshot was not saved: {exc}")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
