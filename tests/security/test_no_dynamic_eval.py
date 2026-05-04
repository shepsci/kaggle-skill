"""Security: no eval/exec/compile in skill code (matches stated security claims)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "tests"}
BANNED_NAMES = {"eval", "exec", "compile", "__import__"}


def _python_files() -> list[Path]:
    files = []
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _is_safe_compile(node: ast.Call) -> bool:
    """re.compile() and similar attribute-access compilers are not code execution."""
    if isinstance(node.func, ast.Attribute) and node.func.attr == "compile":
        return True
    return False


@pytest.mark.parametrize("py_file", _python_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_dynamic_eval(py_file: Path):
    tree = ast.parse(py_file.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name not in BANNED_NAMES:
            continue
        # Allow re.compile, struct.compile, etc. — only bare-name calls are dangerous.
        if name == "compile" and _is_safe_compile(node):
            continue
        if name == "compile" and isinstance(func, ast.Name):
            offenders.append((node.lineno, name))
        elif name in BANNED_NAMES - {"compile"}:
            offenders.append((node.lineno, name))
    assert not offenders, (
        f"{py_file.relative_to(REPO_ROOT)}: dynamic execution calls found at "
        f"lines {offenders} — banned by security policy"
    )
