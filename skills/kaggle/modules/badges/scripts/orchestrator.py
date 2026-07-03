#!/usr/bin/env python3
"""Badge Collector orchestrator — main entry point.

Usage:
    python orchestrator.py --phase 1          # Run phase 1 only
    python orchestrator.py --phase all        # Run all phases (1-5)
    python orchestrator.py --status           # Show progress table
    python orchestrator.py --resume           # Resume from where you left off
    python orchestrator.py --dry-run          # Show planned actions without executing
    python orchestrator.py --dry-run --phase 2  # Dry-run for a specific phase
"""

import argparse
import sys
import traceback
from pathlib import Path

# Add scripts dir to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from badge_registry import get_badges_by_phase, get_automatable_badges
from badge_tracker import print_status_table, load_progress, should_attempt
from utils import check_credentials, get_username


def dry_run(phases: list[int]) -> None:
    """Show what would be done without executing."""
    print("\n[DRY RUN] Planned actions:\n")
    total = 0
    for phase in phases:
        badges = get_badges_by_phase(phase)
        actionable = [b for b in badges if should_attempt(b.id)]
        if not actionable:
            continue
        print(f"  Phase {phase}: {len(actionable)} badge(s)")
        for badge in actionable:
            print(f"    - {badge.name}: {badge.description}")
            total += 1
    print(f"\n  Total: {total} badge(s) would be attempted\n")


def run_phase(phase: int, username: str) -> tuple[int, int]:
    """Run a single phase. Returns (attempted, succeeded)."""
    badges = get_badges_by_phase(phase)
    actionable = [b for b in badges if should_attempt(b.id)]

    if not actionable:
        print(f"\n  Phase {phase}: No badges to attempt (all earned/skipped)")
        return 0, 0

    print(f"\n{'='*60}")
    print(f"  Phase {phase}: Attempting {len(actionable)} badge(s)")
    print(f"{'='*60}\n")

    # Import the phase module (explicit imports for security auditability)
    if phase == 1:
        from phase_1_instant_api import run as phase_run
    elif phase == 2:
        from phase_2_competition import run as phase_run
    elif phase == 3:
        from phase_3_pipeline import run as phase_run
    elif phase == 4:
        from phase_4_browser import run as phase_run
    elif phase == 5:
        from phase_5_streaks import run as phase_run
    else:
        print(f"  Unknown phase: {phase}")
        return 0, 0

    attempted, succeeded = phase_run(username)
    print(f"\n  Phase {phase} complete: {succeeded}/{attempted} badges earned\n")
    return attempted, succeeded


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaggle Badge Collector")
    parser.add_argument("--phase", type=str, default=None,
                        help="Phase to run: 1-5, or 'all'")
    parser.add_argument("--status", action="store_true",
                        help="Show badge progress table")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last state (skip earned badges)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show planned actions without executing")

    args = parser.parse_args()

    # --status: just show progress
    if args.status:
        print_status_table()
        return

    # Determine which phases to run
    if args.phase is None and not args.status:
        parser.print_help()
        return

    if args.phase == "all":
        phases = [1, 2, 3, 4, 5]
    else:
        try:
            phases = [int(args.phase)]
        except (ValueError, TypeError):
            print(f"Invalid phase: {args.phase}. Use 1-5 or 'all'.")
            sys.exit(1)

    # --dry-run: show what would be done
    if args.dry_run:
        dry_run(phases)
        return

    # Check credentials
    print("Checking Kaggle credentials...")
    if not check_credentials():
        print("\n[ERROR] Kaggle credentials not configured.")
        print("Set KAGGLE_USERNAME + KAGGLE_KEY, or create ~/.kaggle/kaggle.json")
        sys.exit(1)

    username = get_username()
    if not username:
        print("\n[ERROR] Could not determine Kaggle username.")
        sys.exit(1)

    print(f"  Username: {username}")
    print(f"  Phases: {phases}")
    print(f"  Resume mode: {args.resume}")

    # Initialize progress file
    load_progress()

    # Run phases
    total_attempted = 0
    total_succeeded = 0

    for phase in phases:
        try:
            attempted, succeeded = run_phase(phase, username)
            total_attempted += attempted
            total_succeeded += succeeded
        except Exception as e:
            print(f"\n  [ERROR] Phase {phase} failed: {e}")
            traceback.print_exc()
            continue

    # Final summary
    print(f"\n{'='*60}")
    print(f"  COMPLETE: {total_succeeded}/{total_attempted} badges earned")
    print(f"{'='*60}")
    print_status_table()


if __name__ == "__main__":
    main()
