"""Guard against broken (single-frame) GIF renders of the demo casts.

Every docs/demo/*.cast must have a matching docs/demo/media/<stem>.gif, and
that GIF must actually be animated. A previous release shipped GIFs that had
been re-rendered into effectively static 1-frame images; this test catches
that class of regression by checking frame counts with Pillow.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "docs" / "demo"
MEDIA_DIR = DEMO_DIR / "media"

CASTS = sorted(DEMO_DIR.glob("*.cast"))


def _output_event_count(cast: Path) -> int:
    lines = cast.read_text(encoding="utf-8").splitlines()
    count = 0
    for line in lines[1:]:
        event = json.loads(line)
        if event[1] == "o":
            count += 1
    return count


@pytest.mark.parametrize("cast", CASTS, ids=lambda p: p.stem)
def test_every_cast_has_a_gif(cast: Path):
    gif = MEDIA_DIR / f"{cast.stem}.gif"
    assert gif.exists() and gif.stat().st_size > 0, f"missing or empty GIF for {cast.name}"


@pytest.mark.parametrize("cast", CASTS, ids=lambda p: p.stem)
def test_gif_is_animated(cast: Path):
    pytest.importorskip("PIL")
    from PIL import Image

    gif = MEDIA_DIR / f"{cast.stem}.gif"
    if not gif.exists():
        pytest.skip(f"{gif.name} not present; covered by test_every_cast_has_a_gif")

    with Image.open(gif) as im:
        n_frames = getattr(im, "n_frames", 1)

    assert n_frames >= 2, (
        f"{gif.relative_to(REPO_ROOT)} has only {n_frames} frame(s); "
        "this is the broken 1-frame-render regression"
    )

    output_events = _output_event_count(cast)
    if output_events >= 4:
        assert n_frames >= 3, (
            f"{gif.relative_to(REPO_ROOT)} has {n_frames} frame(s) but its source cast "
            f"{cast.name} has {output_events} output events; expected a richer render"
        )
