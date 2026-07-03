"""Regression tests pinning the truthfulness claims surfaced in the 2026-05-05 audit.

If any of these tests fail, a public-facing claim has drifted out of sync with
what the code actually does. Either fix the code or fix the docs — don't fix
the test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "kaggle"


# ── Badge count ─────────────────────────────────────────────────────────────

BADGE_REGISTRY = REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "scripts" / "badge_registry.py"


def _actual_badge_count() -> int:
    """Count `Badge(...)` constructor calls in the registry."""
    text = BADGE_REGISTRY.read_text()
    return len(re.findall(r"^\s{4}Badge\(", text, re.MULTILINE))


def test_badge_registry_count_matches_documented_count():
    """Every doc that mentions a numeric badge count must match the registry."""
    actual = _actual_badge_count()
    docs_to_check = [
        REPO_ROOT / "skills" / "kaggle" / "SKILL.md",
        REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "README.md",
        REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "references" / "badge-catalog.md",
        REPO_ROOT / "skills" / "kaggle" / "modules" / "badge-collector" / "scripts" / "badge_registry.py",
    ]
    pattern = re.compile(r"\b(\d{2,3})[ -](badges?|badge|badge definitions|Kaggle badges)\b")
    for doc in docs_to_check:
        if not doc.exists():
            continue
        for line_no, line in enumerate(doc.read_text().splitlines(), start=1):
            for match in pattern.finditer(line):
                claimed = int(match.group(1))
                # Only validate counts that look like total-catalog claims (>= 30).
                # Phase counts like "16 badges" are fine — they're per-phase.
                if claimed < 40:
                    continue
                assert claimed == actual, (
                    f"{doc.relative_to(REPO_ROOT)}:{line_no} claims '{claimed} {match.group(2)}' "
                    f"but the registry has {actual} Badge() entries. Update the doc or the registry."
                )


# ── No "and grading" claim in public-facing surfaces ─────────────────────────

PUBLIC_CLAIM_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "README.md",
    REPO_ROOT / "docs" / "demo" / "demo-script.md",
    REPO_ROOT / "skills" / "kaggle" / "SKILL.md",
    REPO_ROOT / ".claude-plugin" / "plugin.json",
    REPO_ROOT / ".codex-plugin" / "plugin.json",
    REPO_ROOT / "pyproject.toml",
]


@pytest.mark.parametrize("doc", PUBLIC_CLAIM_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_grading_claim_in_public_surface(doc: Path):
    """The skill does not grade and we don't talk about grading in public surfaces.

    Per maintainer policy (2026-05-05): no mentions of 'grading', 'grade', or
    'grader' in the README, SKILL.md, plugin.json, or pyproject.toml. The agent
    grades; the skill retrieves. Public copy should describe what the skill
    does, not what the agent does with the skill's output.
    """
    text = doc.read_text().lower()
    # Word-boundary matches on stem 'grad' would also catch 'upgrade' / 'gradient',
    # so use the explicit forbidden surface forms.
    forbidden_substrings = [
        "grading",
        "grader",
        "grade only",
        "grade against",
        "writeup retrieval and grading",
        "retrieval and grading",
        "grading and retrieval",
        "role-aware grading bundles",
        "grading bundle",
        "grading-ready bundle",
        "grading-bundle preparation",
    ]
    for phrase in forbidden_substrings:
        assert phrase not in text, (
            f"{doc.relative_to(REPO_ROOT)}: contains forbidden claim {phrase!r}. "
            "Public surfaces must not mention grading — the skill retrieves, "
            "the agent grades. Use neutral language like 'retrieval' or "
            "'evaluation-input preparation'."
        )


# ── plugin.json version == pyproject.toml version == SKILL.md frontmatter ───

def test_version_consistency_across_manifests():
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    plugin_version = plugin["version"]

    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    pyproject_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert pyproject_match, "pyproject.toml has no version field"
    pyproject_version = pyproject_match.group(1)

    skill_md = (REPO_ROOT / "skills" / "kaggle" / "SKILL.md").read_text()
    skill_match = re.search(r'"version":\s*"([^"]+)"', skill_md)
    assert skill_match, "SKILL.md frontmatter has no version field"
    skill_version = skill_match.group(1)

    assert plugin_version == pyproject_version == skill_version, (
        f"version drift:\n"
        f"  .claude-plugin/plugin.json:  {plugin_version}\n"
        f"  pyproject.toml:              {pyproject_version}\n"
        f"  skills/kaggle/SKILL.md:      {skill_version}\n"
        "All three must match."
    )


# ── Documented script-path examples must point at files that exist ──────────

def _public_markdown_files() -> list[Path]:
    docs = [REPO_ROOT / "README.md", SKILL_ROOT / "SKILL.md"]
    docs.extend(sorted((REPO_ROOT / "docs").rglob("*.md")))
    docs.extend(sorted(SKILL_ROOT.rglob("*.md")))
    return sorted(set(docs))


def _candidate_script_paths(doc: Path, raw_target: str) -> list[Path]:
    target = raw_target.strip("`'\"")
    if "$" in target or target.startswith(("http://", "https://")):
        return []
    candidates = [REPO_ROOT / target]
    if target.startswith(("modules/", "shared/")):
        candidates.append(SKILL_ROOT / target)
    if target.startswith(("scripts/", "./", "../")):
        candidates.append(doc.parent / target)
    return candidates


@pytest.mark.parametrize("doc", _public_markdown_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_documented_script_paths_exist_and_use_matching_interpreter(doc: Path):
    """Every documented `python3`/`bash` invocation must reference a real local
    script in the context where that doc is meant to be read.

    Public README/docs examples resolve from the repository root. Installed
    skill docs intentionally use `modules/...` and `shared/...` paths relative
    to `skills/kaggle/`, and module READMEs may use local `scripts/...` paths.
    """
    text = doc.read_text(encoding="utf-8")
    pattern = re.compile(r"\b(python3|bash)\s+([^\s\\]+?\.(?:py|sh))")
    missing: list[str] = []
    wrong_interpreter: list[str] = []

    for interpreter, raw_target in pattern.findall(text):
        target = raw_target.strip("`'\"")
        if not _candidate_script_paths(doc, target):
            continue
        candidates = _candidate_script_paths(doc, target)
        if not candidates:
            continue
        if not any(path.exists() for path in candidates):
            missing.append(target)
        if target.endswith(".sh") and interpreter != "bash":
            wrong_interpreter.append(f"{interpreter} {target}")
        if target.endswith(".py") and interpreter != "python3":
            wrong_interpreter.append(f"{interpreter} {target}")

    assert not missing, f"{doc.relative_to(REPO_ROOT)} references missing scripts: {missing}"
    assert not wrong_interpreter, (
        f"{doc.relative_to(REPO_ROOT)} uses the wrong interpreter: {wrong_interpreter}"
    )


# ── Hackathon module lives under kllm ───────────────────────────────────────

def test_hackathon_is_under_kllm_not_top_level_module():
    """v2.3.0 moved hackathon under kllm. Top-level modules/hackathon must not exist."""
    top_level = REPO_ROOT / "skills" / "kaggle" / "modules" / "hackathon"
    nested = REPO_ROOT / "skills" / "kaggle" / "modules" / "kllm" / "hackathon"
    assert not top_level.exists(), f"old hackathon dir still present at {top_level}"
    assert nested.exists(), f"hackathon submodule missing from {nested}"
    assert (nested / "README.md").exists()
    assert (nested / "scripts" / "list_writeups.py").exists()
    assert (nested / "scripts" / "fetch_writeup.py").exists()
    assert (nested / "scripts" / "hackathon_overview.py").exists()


# ── OpenClaw status in compatibility table ───────────────────────────────────

def test_platform_tested_status_is_attested():
    """Every platform marked 'Tested' in the README compatibility table must
    appear in tests/e2e/INSTALL_CHECKLIST.md as either an automated section or
    a maintainer-attestation entry.

    'Tested' without anything backing it is the kind of overclaim the
    truthfulness audit was designed to catch. Maintainer attestation
    (running the install on a separate machine each release) is acceptable
    evidence as long as it's documented in the checklist."""
    readme = (REPO_ROOT / "README.md").read_text()
    checklist = (REPO_ROOT / "tests" / "e2e" / "INSTALL_CHECKLIST.md").read_text()

    # Pull every platform name in the compatibility table that's marked Tested.
    pattern = re.compile(r"^\|\s*([^|\n]+?)\s*\|\s*Tested\s*\|", re.MULTILINE)
    tested_platforms = [
        re.sub(r"[*`]", "", m.group(1)).strip()
        for m in pattern.finditer(readme)
        if "platform" not in m.group(1).lower()
    ]
    if not tested_platforms:
        pytest.skip("no platforms marked Tested; nothing to attest")

    checklist_lower = checklist.lower()
    missing = []
    for platform in tested_platforms:
        # Strip parenthetical clarifiers ("(CLI, VS Code, ...)") — match on the bare name.
        bare_name = re.sub(r"\s*\(.*\)$", "", platform).strip().lower()
        if bare_name not in checklist_lower:
            missing.append(platform)
    assert not missing, (
        f"README compatibility table marks {missing!r} as Tested but those platforms "
        f"are not mentioned in tests/e2e/INSTALL_CHECKLIST.md. Add a row to the "
        f"'Cross-platform testing (maintainer attestation)' section, or demote "
        f"the README claim to 'Compatible'."
    )
