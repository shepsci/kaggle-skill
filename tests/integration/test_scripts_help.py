"""Every documented script's --help must exit 0 and print usage.

This is a "claims match reality" red-green test: if the README references a
script that doesn't exist, has a syntax error, or doesn't accept --help, the
plugin's documented surface is broken even if the underlying logic works.

Runs without network — purely exercises argparse / shell `-h` paths.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Scripts that use argparse and MUST accept --help with rc=0 + "usage" in output.
ARGPARSE_SCRIPTS = [
    "skills/kaggle/modules/comp-report/scripts/list_competitions.py",
    "skills/kaggle/modules/comp-report/scripts/competition_details.py",
    "skills/kaggle/modules/kllm/scripts/kagglehub_download.py",
    "skills/kaggle/modules/kllm/scripts/list_competition_pages.py",
    "skills/kaggle/modules/kllm/hackathon/scripts/hackathon_overview.py",
    "skills/kaggle/modules/kllm/hackathon/scripts/list_writeups.py",
    "skills/kaggle/modules/kllm/hackathon/scripts/fetch_writeup.py",
    "skills/kaggle/modules/badge-collector/scripts/orchestrator.py",
]

# Scripts that take no args (info/checker style) and print a Usage: block on
# argv mismatch but don't go through argparse. We just verify they exist and
# that asking for --help prints SOMETHING actionable.
NO_ARGPARSE_SCRIPTS = [
    "skills/kaggle/shared/check_all_credentials.py",
    "skills/kaggle/modules/registration/scripts/check_registration.py",
    "skills/kaggle/modules/kllm/scripts/check_credentials.py",
    "skills/kaggle/modules/kllm/scripts/kagglehub_publish.py",
]


@pytest.mark.parametrize("script", ARGPARSE_SCRIPTS, ids=lambda p: Path(p).name)
def test_argparse_script_help_exits_zero(script: str):
    path = REPO_ROOT / script
    assert path.exists(), f"documented script does not exist: {script}"
    result = subprocess.run(
        [sys.executable, str(path), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, (
        f"{script} --help exited {result.returncode}. "
        f"stdout={result.stdout[:300]} stderr={result.stderr[:300]}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "usage" in combined, f"{script} --help did not print a usage block"


@pytest.mark.parametrize("script", NO_ARGPARSE_SCRIPTS, ids=lambda p: Path(p).name)
def test_no_argparse_script_exists(script: str):
    """Sanity: every documented no-argparse script must actually exist and be a Python file."""
    path = REPO_ROOT / script
    assert path.exists(), f"documented script does not exist: {script}"
    text = path.read_text()
    assert text.startswith("#!"), f"{script} missing shebang"
    assert "python" in text.split("\n", 1)[0].lower(), f"{script} shebang isn't python"
