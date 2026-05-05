"""All scripts that print Kaggle-supplied content must wrap it in untrusted-content markers.

Prompt-injection guard: writeup bodies, competition descriptions, page content,
and any other host- or participant-supplied text could attempt to manipulate
the agent. SKILL.md documents this as a security guarantee — these tests
enforce it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Scripts that emit Kaggle-supplied text content to stdout. Each MUST wrap
# its output in <untrusted-content>...</untrusted-content> boundary markers.
WRAPPED_SCRIPTS = [
    "skills/kaggle/modules/kllm/hackathon/scripts/hackathon_overview.py",
    "skills/kaggle/modules/kllm/hackathon/scripts/list_writeups.py",
    "skills/kaggle/modules/kllm/hackathon/scripts/fetch_writeup.py",
    "skills/kaggle/modules/kllm/scripts/list_competition_pages.py",
]


@pytest.mark.parametrize("script", WRAPPED_SCRIPTS, ids=lambda p: Path(p).name)
def test_script_emits_untrusted_content_open_marker(script: str):
    text = (REPO_ROOT / script).read_text()
    assert "<untrusted-content" in text, (
        f"{script}: missing <untrusted-content ...> opening marker. "
        "All Kaggle-supplied text content must be wrapped."
    )


@pytest.mark.parametrize("script", WRAPPED_SCRIPTS, ids=lambda p: Path(p).name)
def test_script_emits_untrusted_content_close_marker(script: str):
    text = (REPO_ROOT / script).read_text()
    assert "</untrusted-content>" in text, (
        f"{script}: missing </untrusted-content> closing marker. "
        "Open without close leaves the agent reading attacker-supplied text as directives."
    )


@pytest.mark.parametrize("script", WRAPPED_SCRIPTS, ids=lambda p: Path(p).name)
def test_untrusted_content_marker_includes_source_attribution(script: str):
    text = (REPO_ROOT / script).read_text()
    assert 'source="kaggle-mcp"' in text, (
        f"{script}: <untrusted-content> marker should include source=\"kaggle-mcp\" "
        "so the agent can reason about provenance."
    )
