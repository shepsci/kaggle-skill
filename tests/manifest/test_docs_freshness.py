"""Documentation freshness guards for public project docs."""

from __future__ import annotations

import json
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
    "shepsci/" + "claude-" + "marketplace",
    "<claude-" + "marketplace-root>",
    "66 tools",
    "currently 2.2.0",
]

SECRET_PATTERNS = [
    re.compile(r"KGAT_"),
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
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
REMOVED_CATALOG_COMMAND = "plugin marketplace add shepsci/" + "claude-" + "marketplace"
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


def test_readme_demo_links_to_committed_cast_source():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    cast = REPO_ROOT / "docs" / "demo" / "install-and-demo.cast"
    gif = REPO_ROOT / "docs" / "demo" / "media" / "install-and-demo.gif"

    assert cast.exists(), "README demo source cast must be committed"
    assert "docs/demo/install-and-demo.cast" in readme
    assert "docs/demo/media/install-and-demo.gif" in readme
    assert gif.exists() and gif.stat().st_size > 0
    assert not ASCIINEMA_RE.findall(readme), (
        "README must not link to public asciinema uploads unless the committed "
        "cast has been freshly uploaded and visually verified"
    )


def test_readme_first_embedded_image_is_vesuvius_demo():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    images = [
        image for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
        if image.startswith("docs/demo/")
    ]
    assert images, "README should embed at least one demo image"
    assert images[0] == "docs/demo/media/vesuvius-top-writeups.gif"


def test_vesuvius_demo_has_readme_gif_preview_and_cast_source():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    cast = REPO_ROOT / "docs" / "demo" / "vesuvius-top-writeups.cast"
    gif = REPO_ROOT / "docs" / "demo" / "media" / "vesuvius-top-writeups.gif"

    assert cast.exists(), "Vesuvius demo source cast must be committed"
    assert "docs/demo/vesuvius-top-writeups.cast" in readme
    assert "docs/demo/media/vesuvius-top-writeups.gif" in readme
    assert gif.exists() and gif.stat().st_size > 0


def test_claude_install_docs_use_kaggle_skill_marketplace():
    primary_docs = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "README.md",
        REPO_ROOT / "docs" / "demo" / "demo-script.md",
        REPO_ROOT / "tests" / "e2e" / "INSTALL_CHECKLIST.md",
    ]
    for path in primary_docs:
        text = path.read_text(encoding="utf-8")
        assert DIRECT_CLAUDE_MARKETPLACE_COMMAND in text
        assert REMOVED_CATALOG_COMMAND not in text


@pytest.mark.parametrize("cast", sorted((REPO_ROOT / "docs" / "demo").glob("*.cast")))
def test_committed_asciinema_cast_contains_no_credentials(cast: Path):
    if not cast.exists():
        pytest.skip("no README demo casts have been recorded yet")

    text = cast.read_text(encoding="utf-8")
    offenders = [pattern.pattern for pattern in SECRET_PATTERNS if pattern.search(text)]
    assert not offenders, f"credential-looking material found in cast: {offenders}"


@pytest.mark.parametrize("cast", sorted((REPO_ROOT / "docs" / "demo").glob("*.cast")))
def test_committed_asciinema_cast_is_clean_and_watchable(cast: Path):
    lines = cast.read_text(encoding="utf-8").splitlines()
    assert lines, f"{cast.relative_to(REPO_ROOT)} is empty"

    header = json.loads(lines[0])
    assert header["version"] == 2
    assert header["width"] >= 80
    assert header["height"] >= 20

    previous_time = -1.0
    duration = 0.0
    event_count = 0
    for line_number, line in enumerate(lines[1:], start=2):
        event = json.loads(line)
        assert isinstance(event, list) and len(event) == 3, (
            f"{cast.relative_to(REPO_ROOT)}:{line_number} must be an asciinema v2 event"
        )
        timestamp, stream, data = event
        assert stream in {"o", "i"}
        assert timestamp >= previous_time
        previous_time = timestamp
        duration = timestamp
        event_count += 1

        assert "\x1b" not in data
        assert not ANSI_ESCAPE_RE.search(data)
        bad_controls = [
            char for char in data if ord(char) < 32 and char not in {"\r", "\n", "\t"}
        ]
        assert not bad_controls, (
            f"{cast.relative_to(REPO_ROOT)}:{line_number} contains terminal control characters"
        )

    assert event_count > 0
    assert 4.0 <= duration <= 90.0, (
        f"{cast.relative_to(REPO_ROOT)} duration should be readable and under 90 seconds"
    )


@pytest.mark.parametrize("cast", sorted((REPO_ROOT / "docs" / "demo").glob("*.cast")))
def test_committed_asciinema_cast_uses_current_module_paths(cast: Path):
    text = cast.read_text(encoding="utf-8")
    forbidden = [
        "modules/kllm",
        "modules/comp-report",
        "modules/badge-collector",
        "modules/registration",
    ]
    offenders = [term for term in forbidden if term in text]
    assert not offenders, f"{cast.relative_to(REPO_ROOT)} contains old module paths: {offenders}"


@pytest.mark.parametrize("cast", sorted((REPO_ROOT / "docs" / "demo").glob("*.cast")))
def test_committed_asciinema_cast_has_no_placeholders_or_refusal_language(cast: Path):
    text = cast.read_text(encoding="utf-8").lower()
    forbidden = [
        "discussion/...",
        "placeholder",
        "returned only the links",
        "user-generated content",
        "too dangerous",
        "cannot retrieve",
        "can't access that",
        "couldn't do that",
        "could not retrieve",
    ]
    offenders = [term for term in forbidden if term in text]
    assert not offenders, f"{cast.relative_to(REPO_ROOT)} contains weak demo text: {offenders}"


def test_vesuvius_cast_demonstrates_top_three_writeup_previews():
    cast = REPO_ROOT / "docs" / "demo" / "vesuvius-top-writeups.cast"
    lines = cast.read_text(encoding="utf-8").splitlines()
    text = "".join(json.loads(line)[2] for line in lines[1:])
    required = [
        "vesuvius-challenge-surface-detection",
        "--top-k 3",
        "--preview",
        '"rank": 1',
        '"rank": 2',
        '"rank": 3',
        '"preview"',
        '"excerpt"',
        "<untrusted-content",
        "</untrusted-content>",
    ]
    missing = [term for term in required if term not in text]
    assert not missing, f"Vesuvius demo is missing expected proof points: {missing}"


@pytest.mark.parametrize("cast", sorted((REPO_ROOT / "docs" / "demo").glob("*.cast")))
def test_committed_asciinema_cast_has_gif_preview(cast: Path):
    gif = REPO_ROOT / "docs" / "demo" / "media" / f"{cast.stem}.gif"
    demo_readme = (REPO_ROOT / "docs" / "demo" / "README.md").read_text(encoding="utf-8")

    assert gif.exists() and gif.stat().st_size > 0, f"missing GIF preview for {cast.name}"
    assert f"media/{cast.stem}.gif" in demo_readme, f"demo README does not embed {gif.name}"


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
