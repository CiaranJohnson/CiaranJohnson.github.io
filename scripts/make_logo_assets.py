#!/usr/bin/env python3
# Make the browser-tab icons from the full-resolution CMJ logo.
#
#   media/CMJ Two-Leaf Agricultural Robotics Logo.png   1254x1254 RGB   -- gitignored source
#         |
#         v
#   favicon.ico                16, 32 and 48 px frames, at the site root  -- committed to git
#   img/favicon-32.png         32 px PNG, the <link rel="icon"> most browsers pick
#   img/apple-touch-icon.png   180 px, the iOS home-screen icon
#
# The tab icons are cropped tighter than the original so "CMJ" still reads at
# 16 px. The touch icon keeps the margin the logo was drawn with.
#
# Usage:
#   scripts/make_logo_assets.py
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media" / "CMJ Two-Leaf Agricultural Robotics Logo.png"

im = Image.open(SRC).convert("RGB")
bg = im.getpixel((4, 4))

# Bounding box of the artwork: anything that differs from the background.
mask = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L")
bbox = mask.point(lambda v: 255 if v > 40 else 0).getbbox()


def square_crop(img, box, margin_frac):
    """Crop to `box` plus a margin, padded out to a centred square of bg."""
    l, t, r, b = box
    m = int(max(r - l, b - t) * margin_frac)
    l, t, r, b = l - m, t - m, r + m, b + m
    side = max(r - l, b - t)
    x0, y0 = (l + r) // 2 - side // 2, (t + b) // 2 - side // 2
    out = Image.new("RGB", (side, side), bg)
    out.paste(img.crop((x0, y0, x0 + side, y0 + side)), (0, 0))
    return out


def small(img, size, colors=None):
    s = img.resize((size, size), Image.Resampling.LANCZOS)
    if colors:
        s = s.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return s


tight = square_crop(im, bbox, 0.05)
(ROOT / "img").mkdir(exist_ok=True)

# Pillow drops any ICO frame larger than the base image, so the 48 px frame
# goes first and the smaller ones are appended.
f16, f32, f48 = (small(tight, s) for s in (16, 32, 48))
f48.save(ROOT / "favicon.ico", format="ICO",
         sizes=[(16, 16), (32, 32), (48, 48)], append_images=[f16, f32])

small(tight, 32, colors=128).save(ROOT / "img" / "favicon-32.png", optimize=True)
small(im, 180, colors=128).save(ROOT / "img" / "apple-touch-icon.png", optimize=True)

for p in ("favicon.ico", "img/favicon-32.png", "img/apple-touch-icon.png"):
    print(f"{p:26s} {(ROOT / p).stat().st_size:6d} bytes")
