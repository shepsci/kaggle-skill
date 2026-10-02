"""Every script in the skill answers --help with exit status 0 and a usage line.

Offline: only argument parsing runs. A script that is added without being
listed here fails the completeness test, so the documented surface and the
real one stay the same.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = "skills/kaggle"

PYTHON_ENTRY_POINTS = [
    f"{SKILL}/modules/badges/scripts/orchestrator.py",
    f"{SKILL}/modules/competitions/hackathons/scripts/fetch_writeup.py",
    f"{SKILL}/modules/competitions/hackathons/scripts/hackathon_overview.py",
    f"{SKILL}/modules/competitions/hackathons/scripts/list_writeups.py",
    f"{SKILL}/modules/competitions/scripts/competition_details.py",
    f"{SKILL}/modules/competitions/scripts/competition_pages.py",
    f"{SKILL}/modules/competitions/scripts/list_competitions.py",
    f"{SKILL}/modules/datasets/scripts/kagglehub_download.py",
    f"{SKILL}/modules/datasets/scripts/kagglehub_publish.py",
    f"{SKILL}/modules/discussions/scripts/forums.py",
    f"{SKILL}/modules/discussions/scripts/leaderboard_writeups.py",
    f"{SKILL}/modules/models/scripts/kagglehub_download.py",
    f"{SKILL}/modules/models/scripts/kagglehub_publish.py",
    f"{SKILL}/modules/setup/scripts/check_all_credentials.py",
    f"{SKILL}/shared/kaggle_cli.py",
    f"{SKILL}/shared/preflight.py",
    f"{SKILL}/shared/safe_extract.py",
    f"{SKILL}/shared/untrusted.py",
]

SHELL_ENTRY_POINTS = [
    f"{SKILL}/modules/competitions/scripts/cli_download.sh",
    f"{SKILL}/modules/competitions/scripts/cli_submit.sh",
    f"{SKILL}/modules/datasets/scripts/cli_download.sh",
    f"{SKILL}/modules/datasets/scripts/cli_publish.sh",
    f"{SKILL}/modules/models/scripts/cli_download.sh",
    f"{SKILL}/modules/models/scripts/cli_publish.sh",
    f"{SKILL}/modules/notebooks/scripts/cli_execute.sh",
    f"{SKILL}/modules/notebooks/scripts/cli_publish.sh",
    f"{SKILL}/modules/notebooks/scripts/poll_kernel.sh",
]

# Run without arguments by design; they take no --help.
NO_HELP = {
    f"{SKILL}/modules/setup/scripts/network_check.sh",
    f"{SKILL}/modules/setup/scripts/setup_env.sh",
}

# Imported by the entry points; not run directly.
LIBRARIES = {
    f"{SKILL}/shared/__init__.py",
    f"{SKILL}/shared/credentials.py",
    f"{SKILL}/shared/hub.py",
    f"{SKILL}/shared/mcp_client.py",
    f"{SKILL}/shared/lib.sh",
    f"{SKILL}/modules/competitions/scripts/utils.py",
    f"{SKILL}/modules/badges/scripts/utils.py",
    f"{SKILL}/modules/badges/scripts/badge_registry.py",
    f"{SKILL}/modules/badges/scripts/badge_tracker.py",
    f"{SKILL}/modules/badges/scripts/phase_1_instant_api.py",
    f"{SKILL}/modules/badges/scripts/phase_2_competition.py",
    f"{SKILL}/modules/badges/scripts/phase_3_pipeline.py",
    f"{SKILL}/modules/badges/scripts/phase_4_browser.py",
    f"{SKILL}/modules/badges/scripts/phase_5_streaks.py",
}


def _tracked_scripts() -> set[str]:
    root = REPO_ROOT / SKILL
    return {
        str(path.relative_to(REPO_ROOT))
        for path in root.rglob("*")
        if path.suffix in {".py", ".sh"}
        and "__pycache__" not in path.parts
        and "templates" not in path.parts
        and path.name != "daily_streak.sh"
    }


def test_every_script_is_accounted_for():
    listed = set(PYTHON_ENTRY_POINTS) | set(SHELL_ENTRY_POINTS) | NO_HELP | LIBRARIES
    found = _tracked_scripts()
    assert found - listed == set(), f"scripts with no --help test: {sorted(found - listed)}"
    assert listed - found == set(), f"listed scripts that do not exist: {sorted(listed - found)}"


@pytest.mark.parametrize(
    "script", PYTHON_ENTRY_POINTS + SHELL_ENTRY_POINTS, ids=lambda p: p.removeprefix(f"{SKILL}/")
)
def test_help_exits_zero_and_prints_usage(script, run_script, kaggle_calls):
    calls = kaggle_calls()
    result = run_script(script, "--help", timeout=30)
    assert result.returncode == 0, (
        f"{script} --help exited {result.returncode}: {result.stderr[:300]}"
    )
    assert "usage" in (result.stdout + result.stderr).lower()
    assert calls() == [], "--help must not call kaggle"


@pytest.mark.parametrize("script", PYTHON_ENTRY_POINTS, ids=lambda p: p.removeprefix(f"{SKILL}/"))
def test_python_entry_points_have_a_shebang_or_docstring(script):
    text = (REPO_ROOT / script).read_text()
    assert text.startswith(("#!/usr/bin/env python3", '"""')), f"{script} has no header"
