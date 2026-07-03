"""Documentation freshness guards for public project docs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
    REPO_ROOT / "tests" / "e2e" / "INSTALL_CHECKLIST.md",
    REPO_ROOT / "skills" / "kaggle" / "SKILL.md",
]

STALE_STRINGS = [
    "PLACEHOLDER",
    "v2.1.0",
    "kaggle-skill@shepsci",
    "66 tools",
    "currently 2.2.0",
]

SECRET_PATTERNS = [
    re.compile(r"KGAT_[A-Za-z0-9_\-]{8,}"),
    re.compile(r"KAGGLE_API_TOKEN\s*="),
    re.compile(r"access_token\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"access_token"),
    re.compile(r"kaggle\.json"),
    re.compile(r'"key"\s*:\s*"[^"]+"'),
    re.compile(r'"username"\s*:\s*"[^"]+"'),
]

MARKDOWN_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
ASCIINEMA_RE = re.compile(r"https://asciinema\.org/a/[A-Za-z0-9]+(?:\.svg)?")
OLD_CLAUDE_MARKETPLACE_COMMAND = "plugin marketplace add shepsci/claude-marketplace"
DIRECT_CLAUDE_MARKETPLACE_COMMAND = "plugin marketplace add shepsci/kaggle-skill"


def _iter_text_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            yield path
            continue
        for child in path.rglob("*"):
            if child.is_file() and child.suffix in {".md", ".sh", ".tape"}:
                yield child


@pytest.mark.parametrize("stale", STALE_STRINGS)
def test_public_docs_do_not_contain_stale_strings(stale: str):
    offenders: list[str] = []
    for path in _iter_text_files(DOC_PATHS):
        text = path.read_text(encoding="utf-8")
        if stale in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"{stale!r} appears in stale public docs: {offenders}"


def test_readme_demo_embed_matches_committed_cast_state():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    cast = REPO_ROOT / "docs" / "demo" / "install-and-demo.cast"
    urls = ASCIINEMA_RE.findall(readme)

    if cast.exists():
        assert urls, "README must embed the asciinema demo once the cast is committed"
        assert any(url.endswith(".svg") for url in urls), "README demo needs an asciinema badge image"
        assert any(not url.endswith(".svg") for url in urls), "README demo needs a clickable cast link"
    else:
        assert not urls, "README must not link to asciinema before the cast is committed"


def test_claude_install_docs_prefer_direct_repo_marketplace():
    primary_docs = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "README.md",
        REPO_ROOT / "docs" / "demo" / "demo-script.md",
        REPO_ROOT / "tests" / "e2e" / "INSTALL_CHECKLIST.md",
    ]
    for path in primary_docs:
        text = path.read_text(encoding="utf-8")
        assert DIRECT_CLAUDE_MARKETPLACE_COMMAND in text
        assert OLD_CLAUDE_MARKETPLACE_COMMAND not in text


@pytest.mark.parametrize("cast", sorted((REPO_ROOT / "docs" / "demo").glob("*.cast")))
def test_committed_asciinema_cast_contains_no_credentials(cast: Path):
    if not cast.exists():
        pytest.skip("no README demo casts have been recorded yet")

    text = cast.read_text(encoding="utf-8")
    offenders = [pattern.pattern for pattern in SECRET_PATTERNS if pattern.search(text)]
    assert not offenders, f"credential-looking material found in cast: {offenders}"


@pytest.mark.parametrize("doc", list(_iter_text_files([REPO_ROOT / "README.md", REPO_ROOT / "docs"])))
def test_relative_markdown_links_resolve(doc: Path):
    text = doc.read_text(encoding="utf-8")
    missing: list[str] = []

    for raw_target in MARKDOWN_LINK_RE.findall(text):
        target = raw_target.strip().split()[0].strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        if not (doc.parent / path_part).resolve().exists():
            missing.append(target)

    assert not missing, f"{doc.relative_to(REPO_ROOT)} has broken relative links: {missing}"
