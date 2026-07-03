"""Fetch recent Kaggle competitions across all categories.

Usage:
    python list_competitions.py [--lookback-days 30] [--output json]
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta

from utils import get_api, rate_limit, unwrap_response


# Categories to query from the Kaggle API
CATEGORIES = ["featured", "research", "playground", "gettingStarted", "recruitment", "masters"]


def extract_slug(ref: str) -> str:
    """Extract competition slug from ref URL or string."""
    # ref is typically just the slug, e.g. "titanic" or "playground-series-s4e12"
    return str(ref).strip("/").split("/")[-1]


def competition_to_dict(comp) -> dict:
    """Convert a Kaggle competition object to a serializable dict."""
    # The API returns objects with attributes
    deadline = getattr(comp, "deadline", None)
    date_created = getattr(comp, "enabledDate", None) or getattr(comp, "dateCreated", None)

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

    slug = extract_slug(getattr(comp, "ref", ""))

    # Extract tags
    tags = []
    raw_tags = getattr(comp, "tags", [])
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
        "title": getattr(comp, "title", ""),
        "description": getattr(comp, "description", ""),
        "category": getattr(comp, "category", ""),
        "evaluation_metric": getattr(comp, "evaluationMetric", ""),
        "reward": getattr(comp, "reward", ""),
        "team_count": getattr(comp, "teamCount", 0),
        "deadline": to_iso(deadline),
        "date_created": to_iso(date_created),
        "tags": tags,
        "is_kernels_submissions_only": getattr(comp, "isKernelsSubmissionsOnly", False),
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


def fetch_competitions(lookback_days: int = 30) -> list[dict]:
    """Fetch competitions across all categories and deduplicate."""
    api = get_api()
    seen_slugs = set()
    all_comps = []

    # Query each specific category + "all" for uncategorized types
    categories_to_query = CATEGORIES + [""]  # empty string = all categories

    for cat in categories_to_query:
        for page in range(1, 3):  # pages 1 and 2
            try:
                kwargs = {"page": page, "sort_by": "recentlyCreated"}
                if cat:
                    kwargs["category"] = cat
                result = api.competitions_list(**kwargs)
                comps = unwrap_response(result, "competitions")
                if not comps:
                    break
                for comp in comps:
                    d = competition_to_dict(comp)
                    slug = d["slug"]
                    if slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)
                    # Override category with the queried one if it's specific
                    if cat and not d["category"]:
                        d["category"] = cat
                    all_comps.append(d)
                rate_limit()
            except Exception as e:
                print(f"  Warning: Failed to fetch category='{cat}' page={page}: {e}", file=sys.stderr)
                break

    # Filter by lookback window and classify status
    filtered = []
    for comp in all_comps:
        if within_lookback(comp, lookback_days):
            comp["status"] = classify_status(comp)
            filtered.append(comp)

    # Sort: active first, then by deadline
    filtered.sort(key=lambda c: (0 if c["status"] == "active" else 1, c.get("deadline") or ""))

    return filtered


def main():
    parser = argparse.ArgumentParser(description="List recent Kaggle competitions")
    parser.add_argument("--lookback-days", type=int, default=30, help="Days to look back (default: 30)")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")
    args = parser.parse_args()

    comps = fetch_competitions(args.lookback_days)

    if args.output == "json":
        print(json.dumps(comps, indent=2))
    else:
        active = [c for c in comps if c["status"] == "active"]
        completed = [c for c in comps if c["status"] == "completed"]
        print(f"Found {len(comps)} competitions ({len(active)} active, {len(completed)} completed)")
        print()
        for comp in comps:
            status_icon = "ACTIVE" if comp["status"] == "active" else "DONE"
            print(f"  [{status_icon}] {comp['title']}")
            print(f"         slug: {comp['slug']}, category: {comp['category']}, deadline: {comp['deadline']}")
            if comp.get("reward"):
                print(f"         reward: {comp['reward']}, teams: {comp['team_count']}")
            print()


if __name__ == "__main__":
    main()
