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
    REPO_ROOT / "skills" / "kaggle" / "SKILL.md",
    REPO_ROOT / ".claude-plugin" / "plugin.json",
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


# ── plugin.json description == marketplace.json description ─────────────────

def test_plugin_json_description_matches_marketplace_listing():
    """The plugin description in our local .claude-plugin/plugin.json must
    match the description published in shepsci/claude-marketplace. Drift means
    one of them is stale.

    Skipped in three cases:
      - sibling shepsci/claude-marketplace not cloned
      - marketplace lists an older version (drift handled by the marketplace PR)
      - local plugin lists an older version (test won't pin a downgrade)
    Once both versions match, this test enforces description parity going
    forward."""
    plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    local_desc = plugin.get("description", "")
    local_version = plugin.get("version", "")
    marketplace_path = REPO_ROOT.parent / "claude-marketplace" / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        pytest.skip("sibling shepsci/claude-marketplace not cloned; skipping cross-check")
    marketplace = json.loads(marketplace_path.read_text())
    kaggle_entries = [p for p in marketplace.get("plugins", []) if p.get("name") == "kaggle-skill"]
    assert kaggle_entries, "kaggle-skill missing from marketplace.json"
    if kaggle_entries[0].get("version") != local_version:
        pytest.skip(
            f"marketplace.json at version {kaggle_entries[0].get('version')!r}, "
            f"local plugin.json at {local_version!r} — version drift first; "
            "the marketplace PR fixes this."
        )
    market_desc = kaggle_entries[0].get("description", "")
    assert market_desc == local_desc, (
        f"description drift:\n  local plugin.json: {local_desc!r}\n  marketplace.json:  {market_desc!r}"
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


# ── README script-path examples must point at files that exist ──────────────

def test_readme_script_paths_exist():
    """Every `python3 skills/kaggle/...` invocation in the README must reference
    a real file. Catches the kind of bug we saw with `python3 shared/check_all_credentials.py`
    (relative path from wrong CWD)."""
    readme = (REPO_ROOT / "README.md").read_text()
    pattern = re.compile(r"python3\s+(skills/kaggle/[a-zA-Z0-9_./-]+\.(?:py|sh))")
    referenced = set(pattern.findall(readme))
    missing = [p for p in referenced if not (REPO_ROOT / p).exists()]
    assert not missing, f"README references missing scripts: {missing}"


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
    # The table format is `| **Platform Name** ... | Tested |`.
    pattern = re.compile(r"^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*Tested\s*\|", re.MULTILINE)
    tested_platforms = [m.group(1).strip() for m in pattern.finditer(readme)]
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
