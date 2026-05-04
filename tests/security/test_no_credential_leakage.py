"""Security: scripts must not echo credential values."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "tests"}

# Patterns that suggest a script is echoing/printing the actual credential value
# rather than just referencing the env var name.
LEAK_PATTERNS = [
    # echo "$KAGGLE_API_TOKEN" or echo $KAGGLE_KEY
    re.compile(r'echo\s+["\']?\$\{?KAGGLE_(API_TOKEN|KEY|MCP_TOKEN)\}?["\']?'),
    # printf "%s" "$KAGGLE_KEY"
    re.compile(r'printf\s+[^\n]*\$\{?KAGGLE_(API_TOKEN|KEY|MCP_TOKEN)\}?'),
    # print(token) or print(KAGGLE_API_TOKEN) directly
    re.compile(r'print\s*\(\s*KAGGLE_(API_TOKEN|KEY|MCP_TOKEN)\s*\)'),
]


def _candidate_files() -> list[Path]:
    files = []
    for ext in ("*.sh", "*.py"):
        for path in REPO_ROOT.rglob(ext):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


@pytest.mark.parametrize("path", _candidate_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_credential_echo_in_script(path: Path):
    text = path.read_text(errors="ignore")
    offenders = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pat in LEAK_PATTERNS:
            if pat.search(line):
                offenders.append((line_no, line.strip()))
    assert not offenders, (
        f"{path.relative_to(REPO_ROOT)}: potential credential echo at: {offenders}"
    )
