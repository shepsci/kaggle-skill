"""Security: no dynamic code execution and no shell interpretation in skill code."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "tests", "__pycache__"}
BANNED_NAMES = {"eval", "exec", "compile", "__import__"}
BANNED_ATTRIBUTE_CALLS = {
    ("os", "system"),
    ("os", "popen"),
    ("pickle", "loads"),
    ("pickle", "load"),
}


def _files(pattern: str) -> list[Path]:
    """Repository files matching ``pattern``. Skipped folders are judged by the path
    inside the repository, so a checkout under a folder named ``tests`` is still scanned."""
    return sorted(
        path
        for path in REPO_ROOT.rglob(pattern)
        if not any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts)
    )


PYTHON_FILES = _files("*.py")
SHELL_FILES = _files("*.sh")


def test_the_scan_finds_the_skill_code():
    names = {p.name for p in PYTHON_FILES}
    assert {"mcp_client.py", "untrusted.py", "orchestrator.py", "forums.py"} <= names
    assert {p.name for p in SHELL_FILES} >= {"lib.sh", "setup_env.sh", "cli_submit.sh"}


@pytest.mark.parametrize("py_file", PYTHON_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_dynamic_eval(py_file: Path):
    tree = ast.parse(py_file.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in BANNED_NAMES:
            offenders.append((node.lineno, func.id))
        elif isinstance(func, ast.Attribute):
            # re.compile and similar are fine; a bare compile() is not.
            if func.attr in BANNED_NAMES - {"compile"}:
                offenders.append((node.lineno, func.attr))
            owner = func.value.id if isinstance(func.value, ast.Name) else ""
            if (owner, func.attr) in BANNED_ATTRIBUTE_CALLS:
                offenders.append((node.lineno, f"{owner}.{func.attr}"))
    assert not offenders, (
        f"{py_file.relative_to(REPO_ROOT)}: dynamic execution calls at {offenders}"
    )


@pytest.mark.parametrize("py_file", PYTHON_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_subprocess_goes_through_a_shell(py_file: Path):
    tree = ast.parse(py_file.read_text())
    offenders = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "shell"
        and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
    ]
    assert not offenders, f"{py_file.relative_to(REPO_ROOT)}: shell=True at lines {offenders}"


@pytest.mark.parametrize("sh_file", SHELL_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_shell_scripts_do_not_eval_or_run_inline_python(sh_file: Path):
    """`eval` runs data as code; `python3 -c` imports from the working directory, so a
    file named like a module there would be executed."""
    offenders = []
    for number, line in enumerate(sh_file.read_text().splitlines(), start=1):
        code = line.split("#", 1)[0]
        if re.search(r"(^|[;&|]\s*|\s)eval\s", code) or re.search(r"python3?\s+-c\b", code):
            offenders.append((number, line.strip()))
        if re.search(r"(^|\s)(source|\.)\s+[\"']?\$\{?KAGGLE_ENV_FILE", code):
            offenders.append((number, line.strip()))
    assert not offenders, f"{sh_file.relative_to(REPO_ROOT)}: {offenders}"
