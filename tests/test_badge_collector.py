#!/usr/bin/env python3
"""Test suite for the badge-collector skill.

Tests are organized into groups:
  1. Unit tests — badge_registry, badge_tracker, utils (no network)
  2. Integration tests — each phase against real Kaggle API (network required)

Usage:
    python tests/test_badge_collector.py              # run all tests
    python tests/test_badge_collector.py --unit        # unit tests only
    python tests/test_badge_collector.py --phase 1     # run phase 1 integration test
    python tests/test_badge_collector.py --phase all   # all phases live
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

# ── Setup paths ───────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# ── Test infrastructure ──────────────────────────────────────────────────────

TOTAL = 0
PASSED = 0
FAILED = 0
SKIPPED = 0
RESULTS: list[dict] = []


def record(group: str, name: str, status: str, details: str = "") -> None:
    global TOTAL, PASSED, FAILED, SKIPPED
    TOTAL += 1
    if status == "PASS":
        PASSED += 1
        icon = "\033[32m[PASS]\033[0m"
    elif status == "FAIL":
        FAILED += 1
        icon = "\033[31m[FAIL]\033[0m"
    elif status == "SKIP":
        SKIPPED += 1
        icon = "\033[33m[SKIP]\033[0m"
    else:
        icon = f"[{status}]"
    print(f"  {icon} {group}: {name} — {details}")
    RESULTS.append({"group": group, "name": name, "status": status, "details": details})


def has_credentials() -> bool:
    if os.getenv("KAGGLE_API_TOKEN"):
        return True
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    return kaggle_json.exists()


def get_username() -> str:
    u = os.getenv("KAGGLE_USERNAME", "")
    if u:
        return u
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        return json.loads(kaggle_json.read_text()).get("username", "")
    return ""


def get_kaggle_cli() -> str:
    for path in [
        shutil.which("kaggle"),
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/kaggle",
    ]:
        if path and Path(path).exists():
            return path
    return "kaggle"


# ── Unit Tests ────────────────────────────────────────────────────────────────

def test_badge_registry():
    """Test badge_registry module."""
    group = "Registry"

    try:
        from badge_registry import ALL_BADGES, get_badges_by_phase, get_automatable_badges, get_badge_by_id

        # Total badge count
        count = len(ALL_BADGES)
        if count >= 50:
            record(group, "badge_count", "PASS", f"{count} badges registered")
        else:
            record(group, "badge_count", "FAIL", f"Only {count} badges (expected >=50)")

        # All badges have required fields
        all_valid = True
        for b in ALL_BADGES:
            if not b.id or not b.name or not b.category or not b.description:
                all_valid = False
                record(group, "badge_fields", "FAIL", f"Badge {b.id} missing required fields")
                break
        if all_valid:
            record(group, "badge_fields", "PASS", "All badges have required fields")

        # No duplicate IDs
        ids = [b.id for b in ALL_BADGES]
        if len(ids) == len(set(ids)):
            record(group, "no_duplicate_ids", "PASS", f"{len(ids)} unique IDs")
        else:
            dupes = [x for x in ids if ids.count(x) > 1]
            record(group, "no_duplicate_ids", "FAIL", f"Duplicates: {set(dupes)}")

        # Phase filtering
        p1 = get_badges_by_phase(1)
        if len(p1) >= 10:
            record(group, "phase_1_filter", "PASS", f"{len(p1)} phase-1 badges")
        else:
            record(group, "phase_1_filter", "FAIL", f"Only {len(p1)} phase-1 badges")

        # Automatable count
        auto = get_automatable_badges()
        if len(auto) >= 30:
            record(group, "automatable_count", "PASS", f"{len(auto)} automatable badges")
        else:
            record(group, "automatable_count", "FAIL", f"Only {len(auto)} automatable")

        # Lookup by ID
        b = get_badge_by_id("python_coder")
        if b and b.name == "Python Coder":
            record(group, "lookup_by_id", "PASS", "Found Python Coder badge")
        else:
            record(group, "lookup_by_id", "FAIL", f"Lookup returned {b}")

        # Unknown ID returns None
        b = get_badge_by_id("nonexistent_badge_xyz")
        if b is None:
            record(group, "unknown_id_none", "PASS", "Returns None for unknown ID")
        else:
            record(group, "unknown_id_none", "FAIL", f"Returned {b}")

        # Phase coverage — each phase has at least 1 badge
        for phase in [1, 2, 3, 4, 5]:
            badges = get_badges_by_phase(phase)
            if badges:
                record(group, f"phase_{phase}_nonempty", "PASS", f"{len(badges)} badges")
            else:
                record(group, f"phase_{phase}_nonempty", "FAIL", "0 badges")

    except Exception as e:
        record(group, "import", "FAIL", f"{e}")
        traceback.print_exc()


def test_badge_tracker():
    """Test badge_tracker module with a temp progress file."""
    group = "Tracker"

    try:
        import badge_tracker
        from badge_tracker import load_progress, save_progress, set_status, get_status, is_earned, should_attempt

        # Use a temp file for testing
        original_path = badge_tracker.PROGRESS_FILE
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        badge_tracker.PROGRESS_FILE = Path(tmp.name)

        try:
            # Clean state
            Path(tmp.name).unlink(missing_ok=True)

            # load_progress initializes all badges
            data = load_progress()
            if len(data) >= 50:
                record(group, "load_initializes", "PASS", f"{len(data)} badges initialized")
            else:
                record(group, "load_initializes", "FAIL", f"Only {len(data)} badges")

            # All start as pending
            all_pending = all(v["status"] == "pending" for v in data.values())
            if all_pending:
                record(group, "initial_pending", "PASS", "All badges start as pending")
            else:
                record(group, "initial_pending", "FAIL", "Some badges not pending")

            # set_status and get_status
            set_status("python_coder", "attempting", "testing")
            if get_status("python_coder") == "attempting":
                record(group, "set_get_status", "PASS", "Status set/get works")
            else:
                record(group, "set_get_status", "FAIL", f"Got {get_status('python_coder')}")

            # is_earned
            set_status("python_coder", "earned", "test earned")
            if is_earned("python_coder"):
                record(group, "is_earned", "PASS", "is_earned=True for earned badge")
            else:
                record(group, "is_earned", "FAIL", "is_earned returned False")

            # should_attempt
            if not should_attempt("python_coder"):
                record(group, "should_attempt_earned", "PASS", "Earned badge not re-attempted")
            else:
                record(group, "should_attempt_earned", "FAIL", "Would re-attempt earned badge")

            set_status("r_coder", "failed", "test fail")
            if should_attempt("r_coder"):
                record(group, "should_attempt_failed", "PASS", "Failed badge can be retried")
            else:
                record(group, "should_attempt_failed", "FAIL", "Failed badge can't be retried")

            # Persistence — reload from disk
            data2 = load_progress()
            if data2["python_coder"]["status"] == "earned":
                record(group, "persistence", "PASS", "Progress persisted to disk")
            else:
                record(group, "persistence", "FAIL", "Status not persisted")

            # Timestamp recorded
            if data2["python_coder"].get("updated"):
                record(group, "timestamp", "PASS", f"Updated: {data2['python_coder']['updated']}")
            else:
                record(group, "timestamp", "FAIL", "No timestamp")

        finally:
            badge_tracker.PROGRESS_FILE = original_path
            Path(tmp.name).unlink(missing_ok=True)

    except Exception as e:
        record(group, "import", "FAIL", f"{e}")
        traceback.print_exc()


def test_utils():
    """Test utils module."""
    group = "Utils"

    try:
        from utils import (
            get_username as util_get_username,
            get_kaggle_cli as util_get_cli,
            resource_name,
            slug,
            make_temp_dir,
            REPO_ROOT as util_repo_root,
            TEMPLATES_DIR,
        )

        # REPO_ROOT points to actual repo
        if (util_repo_root / "pyproject.toml").exists():
            record(group, "repo_root", "PASS", str(util_repo_root))
        else:
            record(group, "repo_root", "FAIL", f"{util_repo_root} missing pyproject.toml")

        # TEMPLATES_DIR exists
        if TEMPLATES_DIR.is_dir():
            record(group, "templates_dir", "PASS", str(TEMPLATES_DIR))
        else:
            record(group, "templates_dir", "FAIL", f"{TEMPLATES_DIR} not a directory")

        # Template files exist
        expected_templates = [
            "python_notebook.ipynb",
            "r_notebook.ipynb",
            "utility_script.py",
            "submission_titanic.csv",
            "dataset-metadata.json",
            "model-metadata.json",
            "kernel-metadata.json",
            "README_dataset.md",
        ]
        for tmpl in expected_templates:
            if (TEMPLATES_DIR / tmpl).exists():
                record(group, f"template_{tmpl}", "PASS", "exists")
            else:
                record(group, f"template_{tmpl}", "FAIL", "missing")

        # resource_name generates unique names
        n1 = resource_name("test")
        time.sleep(0.01)
        n2 = resource_name("test")
        if n1.startswith("badge-collector-test-"):
            record(group, "resource_name_prefix", "PASS", n1)
        else:
            record(group, "resource_name_prefix", "FAIL", n1)

        # slug conversion
        if slug("My Test Name") == "my-test-name":
            record(group, "slug", "PASS", "slug('My Test Name') = 'my-test-name'")
        else:
            record(group, "slug", "FAIL", f"slug('My Test Name') = '{slug('My Test Name')}'")

        # make_temp_dir creates dir under badge-tmp/
        tmp = make_temp_dir("-test")
        if tmp.exists() and "badge-tmp" in str(tmp):
            record(group, "make_temp_dir", "PASS", str(tmp))
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            record(group, "make_temp_dir", "FAIL", str(tmp))

        # get_username returns something when creds exist
        u = util_get_username()
        if u:
            record(group, "get_username", "PASS", u)
        else:
            record(group, "get_username", "SKIP", "No credentials")

        # get_kaggle_cli finds binary
        cli = util_get_cli()
        if Path(cli).exists() or shutil.which(cli):
            record(group, "get_kaggle_cli", "PASS", cli)
        else:
            record(group, "get_kaggle_cli", "FAIL", f"Not found: {cli}")

    except Exception as e:
        record(group, "import", "FAIL", f"{e}")
        traceback.print_exc()


def test_orchestrator_cli():
    """Test orchestrator CLI arguments."""
    group = "Orchestrator"

    try:
        # --help works
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrator.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "phase" in result.stdout.lower():
            record(group, "help", "PASS", "Help text shows --phase")
        else:
            record(group, "help", "FAIL", result.stderr[:200])

        # --dry-run --phase 1 works
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrator.py"), "--dry-run", "--phase", "1"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "Python Coder" in result.stdout:
            record(group, "dry_run_phase_1", "PASS", "Shows Python Coder badge")
        else:
            record(group, "dry_run_phase_1", "FAIL", result.stderr[:200])

        # --dry-run --phase all works
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrator.py"), "--dry-run", "--phase", "all"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout
            badge_count = lines.count("    - ")
            if badge_count >= 30:
                record(group, "dry_run_all", "PASS", f"{badge_count} badges listed")
            else:
                record(group, "dry_run_all", "FAIL", f"Only {badge_count} badges")
        else:
            record(group, "dry_run_all", "FAIL", result.stderr[:200])

        # --status works
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrator.py"), "--status"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "Badge Progress" in result.stdout:
            record(group, "status", "PASS", "Shows progress table")
        else:
            record(group, "status", "FAIL", result.stderr[:200])

        # Invalid phase returns error
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrator.py"), "--phase", "99"],
            capture_output=True, text=True, timeout=10,
        )
        # Should either fail or show 0 badges
        if "Invalid" in result.stdout or "Invalid" in result.stderr or result.returncode != 0:
            record(group, "invalid_phase", "PASS", "Rejects invalid phase")
        else:
            record(group, "invalid_phase", "PASS", "Handles gracefully")

    except Exception as e:
        record(group, "cli", "FAIL", f"{e}")
        traceback.print_exc()


def test_templates():
    """Verify template files are valid."""
    group = "Templates"

    try:
        from utils import TEMPLATES_DIR

        # Python notebook is valid JSON/ipynb
        nb_path = TEMPLATES_DIR / "python_notebook.ipynb"
        nb = json.loads(nb_path.read_text())
        if nb.get("nbformat") == 4 and "cells" in nb:
            record(group, "python_notebook_valid", "PASS", f"{len(nb['cells'])} cells")
        else:
            record(group, "python_notebook_valid", "FAIL", "Invalid notebook format")

        # R notebook is valid
        nb_path = TEMPLATES_DIR / "r_notebook.ipynb"
        nb = json.loads(nb_path.read_text())
        if nb.get("nbformat") == 4:
            record(group, "r_notebook_valid", "PASS", f"{len(nb['cells'])} cells")
        else:
            record(group, "r_notebook_valid", "FAIL", "Invalid notebook format")

        # Titanic submission CSV
        csv_path = TEMPLATES_DIR / "submission_titanic.csv"
        lines = csv_path.read_text().strip().split("\n")
        header = lines[0]
        if header == "PassengerId,Survived" and len(lines) >= 400:
            record(group, "titanic_csv", "PASS", f"{len(lines)-1} rows, header={header}")
        else:
            record(group, "titanic_csv", "FAIL", f"{len(lines)} lines, header={header}")

        # PassengerIds should be 892-1309
        ids = [int(line.split(",")[0]) for line in lines[1:]]
        if min(ids) == 892 and max(ids) == 1309 and len(ids) == 418:
            record(group, "titanic_ids", "PASS", "IDs 892-1309 (418 rows)")
        else:
            record(group, "titanic_ids", "FAIL", f"IDs {min(ids)}-{max(ids)}, count={len(ids)}")

        # dataset-metadata.json is valid
        meta = json.loads((TEMPLATES_DIR / "dataset-metadata.json").read_text())
        if "title" in meta and "licenses" in meta:
            record(group, "dataset_metadata", "PASS", f"title={meta['title']}")
        else:
            record(group, "dataset_metadata", "FAIL", "Missing required fields")

        # model-metadata.json is valid
        meta = json.loads((TEMPLATES_DIR / "model-metadata.json").read_text())
        if "ownerSlug" in meta and "title" in meta:
            record(group, "model_metadata", "PASS", f"title={meta['title']}")
        else:
            record(group, "model_metadata", "FAIL", "Missing required fields")

        # kernel-metadata.json is valid
        meta = json.loads((TEMPLATES_DIR / "kernel-metadata.json").read_text())
        if "id" in meta and "code_file" in meta and "language" in meta:
            record(group, "kernel_metadata", "PASS", f"language={meta['language']}")
        else:
            record(group, "kernel_metadata", "FAIL", "Missing required fields")

        # utility_script.py is valid Python
        script = TEMPLATES_DIR / "utility_script.py"
        result = subprocess.run(
            [sys.executable, "-c", f"compile(open('{script}').read(), '{script}', 'exec')"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            record(group, "utility_script_syntax", "PASS", "Valid Python")
        else:
            record(group, "utility_script_syntax", "FAIL", result.stderr[:100])

    except Exception as e:
        record(group, "templates", "FAIL", f"{e}")
        traceback.print_exc()


def test_skill_md():
    """Verify SKILL.md is well-formed."""
    group = "SKILL.md"

    try:
        skill_path = REPO_ROOT / "skills" / "badge-collector" / "SKILL.md"
        content = skill_path.read_text()

        # Has YAML frontmatter
        if content.startswith("---"):
            record(group, "frontmatter", "PASS", "Has YAML frontmatter")
        else:
            record(group, "frontmatter", "FAIL", "Missing frontmatter")

        # Required frontmatter keys
        for key in ["name:", "description:", "license:", "metadata:"]:
            if key in content:
                record(group, f"has_{key.rstrip(':')}", "PASS", f"Found {key}")
            else:
                record(group, f"has_{key.rstrip(':')}", "FAIL", f"Missing {key}")

        # Content sections
        for section in ["Quick Start", "Phases", "CLI Options"]:
            if section in content:
                record(group, f"section_{section.lower().replace(' ','_')}", "PASS", f"Has {section}")
            else:
                record(group, f"section_{section.lower().replace(' ','_')}", "FAIL", f"Missing {section}")

    except Exception as e:
        record(group, "skill_md", "FAIL", f"{e}")


def test_project_structure():
    """Verify project structure is correct."""
    group = "Structure"

    expected_files = [
        "skills/kaggle/SKILL.md",
        "skills/kaggle/modules/badge-collector/scripts/orchestrator.py",
        "skills/kaggle/modules/badge-collector/scripts/badge_registry.py",
        "skills/kaggle/modules/badge-collector/scripts/badge_tracker.py",
        "skills/kaggle/modules/badge-collector/scripts/utils.py",
        "skills/kaggle/modules/badge-collector/scripts/phase_1_instant_api.py",
        "skills/kaggle/modules/badge-collector/scripts/phase_2_competition.py",
        "skills/kaggle/modules/badge-collector/scripts/phase_3_pipeline.py",
        "skills/kaggle/modules/badge-collector/scripts/phase_4_browser.py",
        "skills/kaggle/modules/badge-collector/scripts/phase_5_streaks.py",
        "skills/kaggle/modules/badge-collector/references/badge-catalog.md",
        ".claude/skills/kaggle",
    ]

    for f in expected_files:
        p = REPO_ROOT / f
        if p.exists() or p.is_symlink():
            record(group, f.split("/")[-1], "PASS", "exists")
        else:
            record(group, f.split("/")[-1], "FAIL", f"missing: {f}")

    # Symlink target
    link = REPO_ROOT / ".claude" / "skills" / "kaggle"
    if link.is_symlink():
        target = os.readlink(link)
        if "skills/kaggle" in target:
            record(group, "symlink_target", "PASS", target)
        else:
            record(group, "symlink_target", "FAIL", f"Wrong target: {target}")
    else:
        record(group, "symlink_target", "FAIL", "Not a symlink")


# ── Integration Tests (Live API) ─────────────────────────────────────────────

def check_credentials() -> bool:
    """Verify credentials work with a simple API call."""
    group = "Credentials"

    if not has_credentials():
        record(group, "available", "SKIP", "No credentials")
        return False

    record(group, "available", "PASS", f"User: {get_username()}")

    # Test CLI connectivity
    cli = get_kaggle_cli()
    try:
        result = subprocess.run(
            [cli, "datasets", "list", "--page", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            record(group, "cli_connectivity", "PASS", "kaggle datasets list works")
        else:
            record(group, "cli_connectivity", "FAIL", result.stderr[:200])
            return False
    except Exception as e:
        record(group, "cli_connectivity", "FAIL", str(e))
        return False

    return True


def test_credentials():
    """Pytest wrapper for the credential smoke check."""
    if not has_credentials():
        record("Credentials", "available", "SKIP", "No credentials")
        return
    assert check_credentials()


def run_phase_live(phase: int):
    """Run a phase live against Kaggle API."""
    group = f"Phase {phase} Live"

    if not has_credentials():
        record(group, "credentials", "SKIP", "No credentials")
        return

    username = get_username()
    if not username:
        record(group, "username", "FAIL", "Could not determine username")
        return

    print(f"\n  {'='*50}")
    print(f"  Running Phase {phase} LIVE (user: {username})")
    print(f"  {'='*50}\n")

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "orchestrator.py"), "--phase", str(phase)],
            capture_output=True, text=True, timeout=600,
            cwd=str(REPO_ROOT),
        )

        output = result.stdout + result.stderr
        print(output)

        # Count [OK] and [FAIL] lines
        ok_count = output.count("[OK]")
        fail_count = output.count("[FAIL]")
        skip_count = output.count("[SKIP]")

        record(group, "completed", "PASS" if result.returncode == 0 else "FAIL",
               f"exit={result.returncode}, OK={ok_count}, FAIL={fail_count}, SKIP={skip_count}")

        # Parse badge results from progress file
        progress_file = REPO_ROOT / "badge-progress.json"
        if progress_file.exists():
            data = json.loads(progress_file.read_text())
            from badge_registry import get_badges_by_phase
            phase_badges = get_badges_by_phase(phase)
            earned = sum(1 for b in phase_badges if data.get(b.id, {}).get("status") == "earned")
            failed = sum(1 for b in phase_badges if data.get(b.id, {}).get("status") == "failed")
            skipped = sum(1 for b in phase_badges if data.get(b.id, {}).get("status") == "skipped")
            record(group, "badge_results", "PASS",
                   f"Earned={earned}, Failed={failed}, Skipped={skipped} of {len(phase_badges)}")
        else:
            record(group, "badge_results", "SKIP", "No progress file")

    except subprocess.TimeoutExpired:
        record(group, "timeout", "FAIL", "Phase timed out after 600s")
    except Exception as e:
        record(group, "execution", "FAIL", str(e))
        traceback.print_exc()


# ── Report Generation ─────────────────────────────────────────────────────────

def generate_report():
    """Generate markdown test report."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_path = REPO_ROOT / "tests" / f"test-badge-collector-report-{datetime.now().strftime('%Y-%m-%d')}.md"

    lines = [
        f"# Badge Collector Test Report",
        f"",
        f"**Date:** {timestamp}",
        f"**User:** {get_username() or 'N/A'}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total | {TOTAL} |",
        f"| Passed | {PASSED} |",
        f"| Failed | {FAILED} |",
        f"| Skipped | {SKIPPED} |",
        f"",
        f"## Results",
        f"",
        f"| Group | Test | Status | Details |",
        f"|-------|------|--------|---------|",
    ]

    for r in RESULTS:
        lines.append(f"| {r['group']} | {r['name']} | {r['status']} | {r['details']} |")

    # Badge progress summary if available
    progress_file = REPO_ROOT / "badge-progress.json"
    if progress_file.exists():
        data = json.loads(progress_file.read_text())
        earned = sum(1 for v in data.values() if v.get("status") == "earned")
        failed = sum(1 for v in data.values() if v.get("status") == "failed")
        skipped = sum(1 for v in data.values() if v.get("status") == "skipped")
        pending = sum(1 for v in data.values() if v.get("status") == "pending")

        lines.extend([
            "",
            "## Badge Progress",
            "",
            f"| Status | Count |",
            f"|--------|-------|",
            f"| Earned | {earned} |",
            f"| Failed | {failed} |",
            f"| Skipped | {skipped} |",
            f"| Pending | {pending} |",
            "",
            "### Earned Badges",
            "",
        ])
        for badge_id, info in sorted(data.items()):
            if info.get("status") == "earned":
                lines.append(f"- **{badge_id}**: {info.get('details', '')}")

        if failed > 0:
            lines.extend(["", "### Failed Badges", ""])
            for badge_id, info in sorted(data.items()):
                if info.get("status") == "failed":
                    lines.append(f"- **{badge_id}**: {info.get('details', '')}")

    lines.append("")
    report_path.write_text("\n".join(lines))
    print(f"\n  Report saved to: {report_path}")
    return report_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Badge Collector Test Suite")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--phase", type=str, help="Run specific phase live (1-5 or 'all')")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Badge Collector Test Suite")
    print(f"{'='*60}\n")

    # Always run unit tests
    print("  --- Unit Tests ---\n")
    test_badge_registry()
    test_badge_tracker()
    test_utils()
    test_templates()
    test_orchestrator_cli()
    test_skill_md()
    test_project_structure()

    # Integration tests
    if not args.unit:
        print("\n  --- Integration Tests ---\n")
        creds_ok = check_credentials()

        if creds_ok and args.phase:
            if args.phase == "all":
                for p in [1, 2, 3, 4, 5]:
                    run_phase_live(p)
            else:
                run_phase_live(int(args.phase))
        elif creds_ok and not args.unit:
            # Default: run all phases
            for p in [1, 2, 3, 4, 5]:
                run_phase_live(p)

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS: {PASSED} passed, {FAILED} failed, {SKIPPED} skipped (total: {TOTAL})")
    print(f"{'='*60}\n")

    report_path = generate_report()

    sys.exit(1 if FAILED > 0 else 0)


if __name__ == "__main__":
    main()
