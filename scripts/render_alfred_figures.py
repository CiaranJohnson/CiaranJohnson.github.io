#!/usr/bin/env python3
"""Render the ALFRED page's stills (img/alfred_*) from the manuscript's figures.

The ALFRED preprint (arXiv:2610.01477) ships its figures as PDFs and PNGs in
the arXiv source archive. This script turns the ones the web page uses into
web-sized JPEGs and PNGs, so the page can be rebuilt if a figure changes.

Usage:
    scripts/render_alfred_figures.py /path/to/arxiv-source/Figures

Needs pdftoppm (poppler-utils) and Pillow. Photographs and rendered scenes
become progressive JPEGs; diagrams with flat colour and text stay PNG.
"""
import pathlib
import re
import subprocess
import sys
import tempfile

from PIL import Image

OUT = pathlib.Path(__file__).resolve().parent.parent / "img"

# (source under Figures/, output name, kind, target width in px)
#   photo   -> JPEG q85        cad -> JPEG q88 (CAD renders on white)
#   render  -> JPEG q88        chart -> JPEG q90 (plots with gradients)
#   diagram -> PNG             (flat colour, crisp text)
JOBS = [
    ("prototyping/first_robot.pdf",                "alfred_build_p0.jpg",        "photo",   1200),
    ("prototyping/first_prototype.pdf",            "alfred_build_p1.jpg",        "photo",   1200),
    ("prototyping/doors_closed.pdf",               "alfred_build_alfred.jpg",    "photo",   1200),
    ("prototyping/alfred_2.0_w_lidar_cropped.pdf", "alfred_build_alfred2.jpg",   "photo",   1200),
    ("prototyping/doors_open.pdf",                 "alfred_doors_open.jpg",      "photo",   1200),
    ("prototyping/aluminium_frame.pdf",            "alfred_frame.jpg",           "photo",   1200),
    ("prototyping/chris_robot.pdf",                "alfred_payload_study.jpg",   "photo",   1200),
    ("CAD/arm_interface.pdf",                      "alfred_cad_interface.jpg",   "cad",      900),
    ("CAD/lidar_arm.pdf",                          "alfred_cad_lidar.jpg",       "cad",      900),
    ("CAD/rgbd_arm.pdf",                           "alfred_cad_rgbd.jpg",        "cad",      900),
    ("CAD/lidar_rgbd_arm.pdf",                     "alfred_cad_lidar_rgbd.jpg",  "cad",      900),
    ("Additional/design_requirements.pdf",         "alfred_requirements.png",    "diagram", 1600),
    ("system_design/network_config.pdf",           "alfred_network.png",         "diagram", 1600),
    # The robot-description renders (prototyping/sim_*.pdf) are shown as
    # turntable loops instead: see scripts/compress_alfred_clips.sh.
    # The LiDAR ray-termination grid (results/lidar_fov_polar_grid_6x3.pdf) is
    # shown as six beam-by-beam loops instead: see scripts/compress_alfred_clips.sh.
    # The usable-workspace plot (results/orientation_success_by_translation_3d_
    # observed_bubbles_six_view.png) is shown as three video loops instead:
    # see scripts/compress_alfred_clips.sh and media/README.md.
]
JPEG_QUALITY = {"photo": 85, "cad": 88, "render": 88, "chart": 90}


def page_width_pt(pdf):
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    return float(re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info).group(1))


def load(src, width, tmp):
    if src.suffix.lower() == ".pdf":
        # Rasterise at the DPI that gives the target width (capped at 400 dpi).
        dpi = min(400, max(72, int(width / (page_width_pt(src) / 72)) + 1))
        stem = tmp / src.stem
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", str(src), str(stem)],
                       check=True, stderr=subprocess.DEVNULL)
        return Image.open(f"{stem}.png")
    return Image.open(src)


def flatten(im):
    """Drop transparency onto white and return RGB."""
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")


def main(figures_dir):
    figures = pathlib.Path(figures_dir)
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for rel, name, kind, width in JOBS:
            im = flatten(load(figures / rel, width, tmp))
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            out = OUT / name
            if kind == "diagram":
                im.save(out, "PNG", optimize=True)
            else:
                im.save(out, "JPEG", quality=JPEG_QUALITY[kind], optimize=True, progressive=True)
            print(f"{name:32s} {im.width}x{im.height:<5d} {out.stat().st_size // 1024:5d} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
