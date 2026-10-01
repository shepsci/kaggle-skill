"""Badge progress tracker with JSON persistence.

Tracks each badge's status: pending, attempting, earned, failed, skipped.
"earned" means the action that earns the badge completed; the tracker cannot
see your Kaggle profile. Persists to badge-progress.json in the skill folder,
or in KAGGLE_BADGES_STATE_DIR when that is set.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from badge_registry import ALL_BADGES
from utils import STATE_DIR

PROGRESS_FILE = STATE_DIR / "badge-progress.json"

# With --resume, badges left as "attempting" or "skipped" are tried again too.
_RESUME = False


def set_resume(enabled: bool) -> None:
    """Turn resume mode on or off for this process."""
    global _RESUME
    _RESUME = enabled


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_progress() -> dict:
    """Load progress from disk, initializing any missing badges."""
    data: dict = {}
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text())

    # Ensure all badges are tracked
    for badge in ALL_BADGES:
        if badge.id not in data:
            data[badge.id] = {
                "status": "pending",
                "updated": None,
                "details": None,
            }
    return data


def save_progress(data: dict) -> None:
    """Save progress to disk."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def set_status(badge_id: str, status: str, details: Optional[str] = None) -> None:
    """Update a badge's status."""
    data = load_progress()
    if badge_id not in data:
        data[badge_id] = {}
    data[badge_id]["status"] = status
    data[badge_id]["updated"] = _now()
    if details:
        data[badge_id]["details"] = details
    save_progress(data)


def get_status(badge_id: str) -> str:
    """Get a badge's current status."""
    data = load_progress()
    return data.get(badge_id, {}).get("status", "pending")


def is_earned(badge_id: str) -> bool:
    """Check if a badge has been earned."""
    return get_status(badge_id) == "earned"


def should_attempt(badge_id: str) -> bool:
    """Whether to attempt a badge now.

    Pending and failed badges are always attempted. In resume mode, badges
    left as "attempting" (an interrupted run, or a streak in progress) and
    "skipped" are attempted as well. Earned badges never are.
    """
    status = get_status(badge_id)
    if status in ("pending", "failed"):
        return True
    return _RESUME and status in ("attempting", "skipped")


def print_status_table() -> None:
    """Print a formatted status table of all badges."""
    data = load_progress()

    # Count by status
    counts: dict[str, int] = {}
    for info in data.values():
        s = info.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1

    total = len(ALL_BADGES)
    earned = counts.get("earned", 0)

    print(f"\n{'=' * 60}")
    print(f"  Badge Progress: {earned}/{total} earned")
    print(f"{'=' * 60}")
    print(f"  Earned:     {counts.get('earned', 0)}")
    print(f"  Pending:    {counts.get('pending', 0)}")
    print(f"  Attempting: {counts.get('attempting', 0)}")
    print(f"  Failed:     {counts.get('failed', 0)}")
    print(f"  Skipped:    {counts.get('skipped', 0)}")
    print(f"{'=' * 60}\n")

    # Group by phase
    for phase in [1, 2, 3, 4, 5, None]:
        phase_label = f"Phase {phase}" if phase else "Not Automatable"
        phase_badges = [b for b in ALL_BADGES if b.phase == phase]
        if not phase_badges:
            continue

        print(f"  --- {phase_label} ---")
        for badge in phase_badges:
            info = data.get(badge.id, {})
            status = info.get("status", "pending")
            icon = {
                "earned": "[x]",
                "attempting": "[~]",
                "failed": "[!]",
                "skipped": "[-]",
                "pending": "[ ]",
            }.get(status, "[ ]")
            details = info.get("details", "")
            detail_str = f" ({details})" if details else ""
            print(f"    {icon} {badge.name}{detail_str}")
        print()
