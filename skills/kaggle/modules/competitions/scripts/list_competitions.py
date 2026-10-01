"""Fetch recent Kaggle competitions across all categories.

Usage:
    python list_competitions.py [--lookback-days 30] [--output json]
"""

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from utils import (  # noqa: E402
    KaggleAuthError,
    attr,
    call_quiet,
    get_api,
    rate_limit,
    unwrap_response,
)

from shared import untrusted  # noqa: E402

SOURCE = "kaggle-api"
TOOL = "competitions.list"


# Categories to query from the Kaggle API
CATEGORIES = ["featured", "research", "playground", "gettingStarted", "recruitment", "masters"]


def extract_slug(ref: str) -> str:
    """Extract competition slug from ref URL or string."""
    # ref is typically just the slug, e.g. "titanic" or "playground-series-s4e12"
    return str(ref).strip("/").split("/")[-1]


def normalize_reward(value) -> str:
    """Upper-case a trailing currency code: the API returns ``50,000 Usd``."""
    text = str(value or "")
    return re.sub(r"\b([A-Za-z]{3})$", lambda m: m.group(1).upper(), text)


def competition_to_dict(comp) -> dict:
    """Convert a Kaggle competition object to a serializable dict."""
    deadline = attr(comp, "deadline")
    date_created = attr(comp, "enabled_date", "enabledDate", "date_created", "dateCreated")

    # Normalize datetimes to strings
    def to_iso(dt):
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        try:
            return dt.isoformat()
        except Exception:
            return str(dt)

    slug = extract_slug(attr(comp, "ref", default=""))

    # Extract tags
    tags = []
    raw_tags = attr(comp, "tags", default=[])
    if raw_tags:
        for t in raw_tags:
            if isinstance(t, str):
                tags.append(t)
            elif hasattr(t, "name"):
                tags.append(t.name)
            elif hasattr(t, "ref"):
                tags.append(t.ref)

    return {
        "slug": slug,
        "title": attr(comp, "title", default=""),
        "description": attr(comp, "description", default=""),
        "category": attr(comp, "category", default=""),
        "evaluation_metric": attr(comp, "evaluation_metric", "evaluationMetric", default=""),
        "reward": normalize_reward(attr(comp, "reward", default="")),
        "team_count": attr(comp, "team_count", "teamCount", default=0),
        "deadline": to_iso(deadline),
        "date_created": to_iso(date_created),
        "tags": tags,
        "is_kernels_submissions_only": bool(
            attr(comp, "is_kernels_submissions_only", "isKernelsSubmissionsOnly", default=False)
        ),
        "max_daily_submissions": attr(comp, "max_daily_submissions", "maxDailySubmissions"),
        "max_team_size": attr(comp, "max_team_size", "maxTeamSize"),
        "user_has_entered": bool(attr(comp, "user_has_entered", "userHasEntered", default=False)),
        "url": f"https://www.kaggle.com/competitions/{slug}",
    }


def is_hackathon(comp_dict: dict) -> bool:
    """Check if a competition is a hackathon (judge-evaluated, no leaderboard)."""
    tags = [t.lower() for t in comp_dict.get("tags", [])]
    return "hackathon" in tags


def classify_status(comp_dict: dict) -> str:
    """Determine if a competition is active or completed.

    Hackathons are considered active until winners are announced, even if the
    submission deadline has passed, because there is no leaderboard — results
    only appear on the Winners tab after judging completes (often weeks/months
    after the deadline).
    """
    # Hackathons stay active until winners are announced; the script cannot
    # detect this automatically, so they remain "active" past their deadline.
    if is_hackathon(comp_dict):
        return "active"

    deadline_str = comp_dict.get("deadline")
    if not deadline_str:
        return "active"
    try:
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return "completed" if deadline < now else "active"
    except Exception:
        return "active"


def within_lookback(comp_dict: dict, lookback_days: int) -> bool:
    """Check if competition is within the lookback window."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)

    for field in ["deadline", "date_created"]:
        val = comp_dict.get(field)
        if not val:
            continue
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                return True
        except Exception:
            continue
    return False


class AllQueriesFailed(RuntimeError):
    """Every listing request failed, so an empty result would be misleading."""

    def __init__(self, failures: list[str]):
        super().__init__(f"all {len(failures)} competition queries failed")
        self.failures = failures


def fetch_competitions(lookback_days: int = 30) -> list[dict]:
    """Fetch competitions across all categories and deduplicate.

    Raises AllQueriesFailed when no query succeeded. A single failed query is
    reported on standard error and the rest are still used.
    """
    api = get_api()
    seen_slugs = set()
    all_comps = []

    # Every category, then no filter, then the community group, which the
    # default ("general") group leaves out.
    queries: list[dict] = [{"category": cat} for cat in CATEGORIES]
    queries += [{}, {"group": "community"}]
    failures: list[str] = []
    succeeded = 0

    for query in queries:
        label = query.get("category") or query.get("group") or "all"
        for page in range(1, 3):  # pages 1 and 2
            try:
                result = call_quiet(
                    api.competitions_list, page=page, sort_by="recentlyCreated", **query
                )
            except Exception as e:  # noqa: BLE001 - one failed query must not stop the report
                failures.append(f"{label} page {page}: {type(e).__name__}: {e}"[:200])
                break
            succeeded += 1
            comps = unwrap_response(result, "competitions")
            if not comps:
                break
            for comp in comps:
                d = competition_to_dict(comp)
                slug = d["slug"]
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                # Use the queried category when the API gave none
                if query.get("category") and not d["category"]:
                    d["category"] = query["category"]
                all_comps.append(d)
            rate_limit()

    if failures:
        if not succeeded:
            raise AllQueriesFailed(failures)
        print(f"warning: {len(failures)} competition queries failed:", file=sys.stderr)
        # The text of a failure comes from the server.
        untrusted.emit_text("\n".join(failures), source=SOURCE, tool=TOOL, file=sys.stderr)

    # Filter by lookback window and classify status
    filtered = []
    for comp in all_comps:
        if within_lookback(comp, lookback_days):
            comp["status"] = classify_status(comp)
            filtered.append(comp)

    # Sort: active first, then by deadline
    filtered.sort(key=lambda c: (0 if c["status"] == "active" else 1, c.get("deadline") or ""))

    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="List recent Kaggle competitions")
    parser.add_argument(
        "--lookback-days", type=int, default=30, help="Days to look back (default: 30)"
    )
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")
    args = parser.parse_args()

    try:
        comps = fetch_competitions(args.lookback_days)
    except KaggleAuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except AllQueriesFailed as exc:
        print(
            f"error: {exc}; the credential may be revoked, or Kaggle unreachable", file=sys.stderr
        )
        untrusted.emit_text("\n".join(exc.failures), source=SOURCE, tool=TOOL, file=sys.stderr)
        return 1

    # Titles, descriptions and tags are host-authored: one untrusted block.
    with untrusted.Block(source=SOURCE, tool=TOOL, lookback_days=args.lookback_days) as block:
        if args.output == "json":
            block.write_json(comps, indent=2)
        else:
            active = [c for c in comps if c["status"] == "active"]
            completed = [c for c in comps if c["status"] == "completed"]
            block.write(
                f"Found {len(comps)} competitions "
                f"({len(active)} active, {len(completed)} completed)\n"
            )
            for comp in comps:
                status_icon = "ACTIVE" if comp["status"] == "active" else "DONE"
                block.write(f"  [{status_icon}] {comp['title']}")
                block.write(
                    f"         slug: {comp['slug']}, category: {comp['category']}, "
                    f"deadline: {comp['deadline']}"
                )
                if comp.get("reward"):
                    block.write(f"         reward: {comp['reward']}, teams: {comp['team_count']}")
                block.write("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
