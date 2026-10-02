#!/usr/bin/env python3
"""Draw the plugin's icon: assets/icon.png, 1024 by 1024.

    python3 tools/build_icon.py

Three rising bars and a mark above the tallest: a leaderboard. The drawing is
this project's own and uses none of Kaggle's marks or its blue. Needs Pillow.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "assets" / "icon.png"
SIZE = 1024
SCALE = 4  # drawn larger, then reduced, for smooth edges
BACKGROUND = (15, 118, 110)  # teal, #0F766E
BAR = (255, 255, 255)
MARK = (251, 191, 36)  # amber


def draw() -> Image.Image:
    side = SIZE * SCALE
    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)

    def box(x0: float, y0: float, x1: float, y1: float) -> tuple[int, int, int, int]:
        return tuple(int(v * SCALE) for v in (x0, y0, x1, y1))  # type: ignore[return-value]

    pen.rounded_rectangle(box(0, 0, SIZE, SIZE), radius=220 * SCALE, fill=BACKGROUND)
    base = 800
    width = 150
    gap = 62
    left = (SIZE - (3 * width + 2 * gap)) // 2
    for index, height in enumerate((240, 380, 520)):
        x0 = left + index * (width + gap)
        pen.rounded_rectangle(box(x0, base - height, x0 + width, base), radius=36 * SCALE, fill=BAR)
    center = left + 2 * (width + gap) + width // 2
    pen.ellipse(box(center - 58, 138, center + 58, 254), fill=MARK)
    return image.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    draw().save(TARGET, optimize=True)
    print(f"wrote {TARGET.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
