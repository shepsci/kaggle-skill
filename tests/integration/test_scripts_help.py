"""Every script in the skill answers --help with exit status 0 and a usage line.

Offline: only argument parsing runs, and --help must do nothing else: no call
to Kaggle, no file written. A script that is added without being listed here
fails the completeness test, so the documented surface and the real one stay
the same.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = "skills/kaggle"

PYTHON_ENTRY_POINTS = [
    f"{SKILL}/scripts/kaggle_skill.py",
    f"{SKILL}/modules/badges/scripts/orchestrator.py",
    f"{SKILL}/modules/competitions/hackathons/scripts/fetch_writeup.py",
    f"{SKILL}/modules/competitions/hackathons/scripts/hackathon_overview.py",
    f"{SKILL}/modules/competitions/hackathons/scripts/list_writeups.py",
    f"{SKILL}/modules/competitions/scripts/competition_brief.py",
    f"{SKILL}/modules/competitions/scripts/competition_details.py",
    f"{SKILL}/modules/competitions/scripts/competition_download.py",
    f"{SKILL}/modules/competitions/scripts/competition_episodes.py",
    f"{SKILL}/modules/competitions/scripts/competition_leaderboard.py",
    f"{SKILL}/modules/competitions/scripts/competition_ledger.py",
    f"{SKILL}/modules/competitions/scripts/competition_pages.py",
    f"{SKILL}/modules/competitions/scripts/competition_status.py",
    f"{SKILL}/modules/competitions/scripts/competition_submit.py",
    f"{SKILL}/modules/competitions/scripts/competition_validate.py",
    f"{SKILL}/modules/competitions/scripts/competition_watch.py",
    f"{SKILL}/modules/competitions/scripts/list_competitions.py",
    f"{SKILL}/modules/datasets/scripts/dataset_download.py",
    f"{SKILL}/modules/datasets/scripts/dataset_publish.py",
    f"{SKILL}/modules/discussions/scripts/forums.py",
    f"{SKILL}/modules/discussions/scripts/leaderboard_writeups.py",
    f"{SKILL}/modules/models/scripts/model_download.py",
    f"{SKILL}/modules/models/scripts/model_publish.py",
    f"{SKILL}/modules/notebooks/scripts/notebook_push.py",
    f"{SKILL}/modules/notebooks/scripts/notebook_run.py",
    f"{SKILL}/modules/notebooks/scripts/notebook_wait.py",
    f"{SKILL}/modules/setup/scripts/check_all_credentials.py",
    f"{SKILL}/modules/setup/scripts/doctor.py",
    f"{SKILL}/modules/setup/scripts/save_credentials.py",
    f"{SKILL}/shared/kaggle_cli.py",
    f"{SKILL}/shared/preflight.py",
    f"{SKILL}/shared/safe_extract.py",
]

# Imported by the entry points; not run directly.
LIBRARIES = {
    f"{SKILL}/shared/__init__.py",
    f"{SKILL}/shared/competition.py",
    f"{SKILL}/shared/credentials.py",
    f"{SKILL}/shared/hub.py",
    f"{SKILL}/shared/ledger.py",
    f"{SKILL}/shared/mcp_client.py",
    f"{SKILL}/shared/net.py",
    f"{SKILL}/shared/notebook.py",
    f"{SKILL}/shared/script.py",
    f"{SKILL}/shared/text.py",
    f"{SKILL}/shared/untrusted.py",
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
        # Folders that git ignores: leftovers of older layouts on a maintainer's disk.
        and not {"badge-collector", "comp-report", "kllm", "downloads"} & set(path.parts)
    }


def test_every_script_is_accounted_for():
    listed = set(PYTHON_ENTRY_POINTS) | LIBRARIES
    found = _tracked_scripts()
    assert found - listed == set(), f"scripts with no --help test: {sorted(found - listed)}"
    assert listed - found == set(), f"listed scripts that do not exist: {sorted(listed - found)}"


def test_the_skill_has_no_shell_scripts_of_its_own():
    """One language, one argument style. The badge module's streak helper is generated."""
    shell = [p for p in (REPO_ROOT / SKILL).rglob("*.sh") if "__pycache__" not in p.parts]
    assert shell == []


@pytest.mark.parametrize("script", PYTHON_ENTRY_POINTS, ids=lambda p: p.removeprefix(f"{SKILL}/"))
def test_help_exits_zero_prints_usage_and_does_nothing_else(script, run_script, kaggle_calls):
    calls = kaggle_calls()
    home_before = sorted(str(p) for p in Path.home().rglob("*"))
    result = run_script(script, "--help", env={"KAGGLE_API_TOKEN": "KGAT_test"}, timeout=30)
    assert result.returncode == 0, (
        f"{script} --help exited {result.returncode}: {result.stderr[:300]}"
    )
    assert "usage" in (result.stdout + result.stderr).lower()
    assert calls() == [], "--help must not call kaggle"
    assert sorted(str(p) for p in Path.home().rglob("*")) == home_before, "--help wrote a file"
    assert not Path(".kaggle-skill").exists() and not Path("downloads").exists()


@pytest.mark.parametrize("script", PYTHON_ENTRY_POINTS, ids=lambda p: p.removeprefix(f"{SKILL}/"))
def test_python_entry_points_have_a_shebang_or_docstring(script):
    text = (REPO_ROOT / script).read_text()
    assert text.startswith(("#!/usr/bin/env python3", '"""')), f"{script} has no header"


@pytest.mark.parametrize(
    "script",
    [s for s in PYTHON_ENTRY_POINTS if "/badges/" not in s and "/shared/" not in s],
    ids=lambda p: p.removeprefix(f"{SKILL}/"),
)
def test_every_option_has_help_text(script, run_script):
    """An agent chooses options from --help, so no option may be listed without a line."""
    if script.endswith("forums.py"):
        outputs = [run_script(script, sub, "--help").stdout for sub in ("topics", "topic")]
    else:
        outputs = [run_script(script, "--help").stdout]
    for output in outputs:
        options = output.split("options:", 1)[-1] if "options:" in output else ""
        lines = options.splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            has_text = "  " in stripped or (
                index + 1 < len(lines) and lines[index + 1].startswith(" " * 20)
            )
            assert has_text, f"{script}: option without help: {stripped}"
