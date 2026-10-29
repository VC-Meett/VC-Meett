#!/usr/bin/env python3
"""Render the profile card as a self-contained PNG for reliable GitHub README display."""
from pathlib import Path
import re
import io

import cairosvg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "intro.svg"
PORTRAIT_PATH = ASSETS / "profile.png"
OUTPUT_PATH = ASSETS / "profile-banner.png"

def main() -> None:
    if not SVG_PATH.is_file():
        raise FileNotFoundError(f"Missing card SVG: {SVG_PATH}")
    if not PORTRAIT_PATH.is_file():
        raise FileNotFoundError(f"Missing portrait: {PORTRAIT_PATH}")

    # GitHub sanitizes SVGs and may not render referenced/embedded raster images.
    # Render the vector card without its SVG image element, then composite the
    # portrait into that reserved circular frame using Pillow.
    svg = SVG_PATH.read_text(encoding="utf-8")
    svg, count = re.subn(r'<image\\b[^>]*/>', '', svg, count=1)
    if count != 1:
        raise RuntimeError("Could not find the portrait <image> element in assets/intro.svg")

    base_png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=1200, output_height=420)
    canvas = Image.open(io.BytesIO(base_png)).convert("RGBA")
    portrait = Image.open(PORTRAIT_PATH).convert("RGB")

    # Crop from the supplied illustrated portrait to keep the face and upper
    # torso centered in the card's 124 px avatar aperture.
    width, height = portrait.size
    left, top, right, bottom = (round(width * 0.191), round(height * 0.112),
                                round(width * 0.813), round(height * 0.734))
    square = min(right - left, bottom - top)
    cx, cy = (left + right) / 2, (top + bottom) / 2
    left, top = round(cx - square / 2), round(cy - square / 2)
    right, bottom = left + square, top + square
    avatar = portrait.crop((left, top, right, bottom)).resize((124, 124), Image.Resampling.LANCZOS).convert("RGBA")

    mask = Image.new("L", (124, 124), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 123, 123), fill=255)
    avatar.putalpha(mask)
    canvas.alpha_composite(avatar, (83, 143))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUTPUT_PATH, format="PNG", optimize=True)
    print(f"Rendered {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
