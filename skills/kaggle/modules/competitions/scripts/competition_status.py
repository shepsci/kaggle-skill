#!/usr/bin/env python3
"""Where you stand in a Kaggle competition: time left, submissions left, scores, quota.

    competition_status.py rsna-knee-abnormality-detection
    competition_status.py titanic --json

Facts only. It reads the deadline, your rank, how many submissions are left
today, the submissions still being scored, your best and latest scores, and
this week's GPU and TPU hours. It changes nothing.

Needs a credential: an API token or `kaggle auth login`. The count of
submissions left comes from the Kaggle CLI when it is installed; without it
the count is worked out from your submission list and marked as an estimate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import competition, credentials, mcp_client, script, text, untrusted  # noqa: E402

SOURCE = "kaggle-mcp"
TOOL = "competition_status"
BEST_OF = 100  # submissions read to find your best public score: one page


def submission_counts(info: dict, submissions: list[dict], limits: dict | None, now) -> dict:
    """How many submissions were made today and how many are left."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = [
        row
        for row in submissions
        if (text.parse_time(row["date"]) or midnight.replace(year=1970)) >= midnight
    ]
    daily = info.get("max_daily_submissions")
    counts = {"today": len(today), "daily_limit": daily, "left": None, "source": None}
    if limits is not None:
        # Kaggle's own counts: the list above holds only the latest submissions.
        counts["today"] = limits["numToday"]
        counts["left"] = limits["numAllowedNow"]
        counts["lifetime"] = limits["numTotal"]
        counts["source"] = "kaggle-cli"
    elif daily:
        counts["left"] = max(int(daily) - len(today), 0)
        counts["source"] = "estimate"
    return counts


def quota_lines(quota: dict, now) -> list[str]:
    lines = []
    refresh = text.when(quota.get("quota_refresh_time"), now)
    for label, key in (("GPU this week", "gpu_quota"), ("TPU this week", "tpu_quota")):
        part = quota.get(key) if isinstance(quota.get(key), dict) else {}
        used = competition.seconds(part.get("time_used"))
        allowed = competition.seconds(part.get("total_time_allowed"))
        if used is None or allowed is None:
            continue
        lines.append(f"{label}: {used / 3600:.1f} h used of {allowed / 3600:.1f} h")
    if lines:
        lines.append(f"quota resets: {refresh}")
    return lines


def collect(slug: str, token: str, limit: int) -> tuple[dict | None, mcp_client.Result]:
    """Gather everything. Returns ``(report, the facts result)``; report is None on failure."""
    facts_result = competition.fetch_facts(slug, token)
    if not facts_result.ok or not isinstance(facts_result.data, dict):
        return None, facts_result
    now = text.now_utc()
    info = competition.facts(slug, facts_result.data)

    unavailable: dict[str, str] = {}
    read_limit = max(limit, BEST_OF)
    submissions, sub_result = competition.fetch_submissions(slug, token, limit=read_limit)
    if not sub_result.ok:
        unavailable["submissions"] = mcp_client.error_message(sub_result.response)[:200]

    board, _, board_result = competition.fetch_leaderboard(slug, token)
    if not board_result.ok:
        unavailable["leaderboard"] = mcp_client.error_message(board_result.response)[:200]
    higher = competition.higher_is_better(board)

    quota_result = mcp_client.request("get_accelerator_quota", {}, token=token)
    quota = quota_result.data if quota_result.ok and isinstance(quota_result.data, dict) else {}
    if not quota:
        unavailable["quota"] = mcp_client.error_message(quota_result.response)[:200]

    report = {
        "competition": info,
        "direction": None if higher is None else ("higher" if higher else "lower"),
        "leader_score": board[0]["score"] if board else None,
        "counts": submission_counts(info, submissions, competition.submission_limits(slug), now),
        "pending": [row for row in submissions if row["status"] == "PENDING"],
        "best": competition.best_submission(submissions, higher),
        # The best of the submissions read; older ones may exist when the read was full.
        "best_of": len(submissions) if len(submissions) >= read_limit else None,
        "latest": submissions[:limit],
        "quota": quota,
        "unavailable": unavailable,
        "checked": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return report, facts_result


def text_lines(report: dict) -> list[str]:
    info = report["competition"]
    now = text.parse_time(report["checked"])
    missing = report["unavailable"]
    direction = {
        "higher": "higher is better",
        "lower": "lower is better",
        None: "direction not shown by the leaderboard",
    }[report["direction"]]
    rows: list[tuple[str, str]] = [("deadline", text.when(info.get("deadline"), now))]
    if info.get("entry_deadline"):
        rows.append(("entry closes", text.when(info["entry_deadline"], now)))
    rows.append(("metric", f"{info['metric'] or 'not given'} ({direction})"))
    rows.append(
        ("submit with", "a notebook (code competition)" if info["notebook_only"] else "a file")
    )
    teams = f"{int(info['team_count']):,}" if info.get("team_count") else "?"
    if info["user_has_entered"]:
        rank = info.get("user_rank")
        rows.append(("your rank", f"{rank} of {teams} teams" if rank else f"no rank yet ({teams})"))
    else:
        rows.append(("your rank", "you have not entered this competition"))

    counts = report["counts"]
    if info["submissions_disabled"]:
        rows.append(("submissions", "closed"))
    elif "submissions" in missing:
        rows.append(("submissions", f"not available ({missing['submissions']})"))
    else:
        daily = f" of {counts['daily_limit']} a day" if counts["daily_limit"] else ""
        if counts["source"] == "kaggle-cli":
            left = f"{counts['left']} left{daily} (Kaggle's count)"
        elif counts["source"] == "estimate":
            left = f"about {counts['left']} left{daily} (estimated; counted since 00:00 UTC)"
        else:
            left = "the daily limit is not given"
        rows.append(("submissions", f"{counts['today']} today, {left}"))

    for row in report["pending"]:
        rows.append(("being scored", f"submission {row['ref']}, sent {_stamp(row['date'])}"))

    best = report["best"]
    if best:
        leader = f"; the leader has {report['leader_score']}" if report["leader_score"] else ""
        label = f"best of latest {report['best_of']}" if report.get("best_of") else "best public"
        rows.append(
            (
                label,
                f"{best['public_score']} on {text.day(best['date'])} (submission {best['ref']})"
                f"{leader}",
            )
        )
    width = max(len(label) for label, _ in rows) + 1
    lines = [info["title"]] + [f"  {label + ':':<{width}} {value}" for label, value in rows]

    if report["latest"]:
        lines.append("  latest submissions:")
        for row in report["latest"]:
            score = row["public_score"] or "-"
            lines.append(
                f"    {_stamp(row['date'])}  {row['status']:<8}  {score:<10}  "
                f"{text.shorten(text.collapse(row['description']), 60)}  [{row['ref']}]"
            )
    elif "submissions" not in missing:
        lines.append("  latest submissions: none yet")

    if "quota" in missing:
        lines.append(f"  quota: not available ({missing['quota']})")
    lines += [f"  {line}" for line in quota_lines(report["quota"], now)]
    return lines


def _stamp(value: object) -> str:
    moment = text.parse_time(value)
    return moment.strftime("%Y-%m-%d %H:%M") if moment else "-"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Where you stand in a Kaggle competition: time left, submissions left, "
        "scores, quota.",
        epilog="Needs a Kaggle credential: an API token or `kaggle auth login`.",
    )
    script.add_competition(parser)
    script.add_limit(parser, 5, "of your latest submissions")
    script.add_json(parser)
    args = parser.parse_args(argv)
    (slug,) = script.positionals(parser, args)

    credentials.load_configured_env_file()
    token = mcp_client.resolve_token()
    if not token:
        return script.no_credential("your status in a competition")

    report, facts_result = collect(slug, token, args.limit)
    if report is None:
        return facts_result.fail(competition=slug)

    attrs = {"source": SOURCE, "tool": TOOL, "competition": slug}
    if args.json:
        untrusted.emit_json(report, indent=2 if args.pretty else None, **attrs)
    else:
        # The title, the submission messages and Kaggle's error text are data.
        with untrusted.Block(**attrs) as block:
            for line in text_lines(report):
                block.write(line)
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
