#!/usr/bin/env python3
"""Cut the twelve plant photographs out of Figure 13 of the ROWCAST manuscript.

The figure is a 3x4 grid of photographs with a label over each. The page is
rendered at 600 dpi, the label positions come from pdftotext, and each
photograph is found by walking outwards from a point just under its label
until the page's white margin is reached. The tiles are written to
img/rowcast_plant_<name>.jpg and shown on ROWCAST/index.html in a six-column
grid, the small cohort above the large one.

Usage:
    scripts/cut_plant_tiles.py "/path/to/ROWCAST.pdf" [page]

The page defaults to the one whose text contains "Figure 13:". Needs poppler
(pdftoppm, pdftotext) and Pillow.
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent.parent
DPI = 600
K = DPI / 72          # PDF points -> pixels
WHITE = 238           # anything lighter is page margin

# label text -> output stem, in page order (three columns, four rows)
PLANTS = [
    ("P1", "p1"), ("P2", "p2"), ("P3", "p3"),
    ("P4", "p4"), ("P5", "p5"), ("P6", "p6"),
    ("White", "white_poinsettia"), ("Red", "red_poinsettia"), ("Ivy", "ivy_gourd"),
    ("Indian", "indian_laurel_fig"), ("Fiddle-leaf", "fiddle_leaf_fig"), ("Split-leaf", "split_leaf_philodendron"),
]


def figure_page(pdf):
    text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout
    for n, page in enumerate(text.split("\f"), 1):
        if "Figure 13:" in page:
            return n
    sys.exit("no page mentions Figure 13")


def words(pdf, page, tmp):
    out = tmp / "words.html"
    subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-bbox", pdf, str(out)], check=True)
    pat = r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>'
    return [(float(a), float(b), float(c), float(d), w) for a, b, c, d, w in re.findall(pat, out.read_text())]


def main():
    pdf = sys.argv[1]
    tmp = Path(tempfile.mkdtemp(prefix="fig13_"))
    page = int(sys.argv[2]) if len(sys.argv) > 2 else figure_page(pdf)
    subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page), "-png", pdf, str(tmp / "page")], check=True)
    png = next(tmp.glob("page*.png"))
    rgb = Image.open(png).convert("RGB")
    grey = rgb.convert("L")
    W, H = grey.size
    px = grey.load()

    def col_white(x, y0, y1):
        return all(px[x, y] >= WHITE for y in range(max(0, y0), min(H, y1), 3))

    def row_white(y, x0, x1):
        return all(px[x, y] >= WHITE for x in range(max(0, x0), min(W, x1), 3))

    # The first word of each label; the large-cohort labels are the first word
    # of the name, so take the occurrence in the figure's own column band.
    wl = words(pdf, page, tmp)
    sizes = {}
    for first, stem in PLANTS:
        cands = [w for w in wl if w[4] == first and w[0] < 300]
        if not cands:
            sys.exit(f"label {first!r} not found on page {page}")
        x0, y0, x1, y1, _ = min(cands, key=lambda w: w[1])
        # seed just under the label, 22 pt right of the label's centre so it
        # lands on gravel rather than a white pot; nudge sideways if not.
        sx, sy = int((((x0 + x1) / 2) + 22) * K), int((y1 + 9) * K)
        for dx in range(0, 400, 10):
            if px[sx + dx, sy] < WHITE:
                sx += dx; break
            if px[sx - dx, sy] < WHITE:
                sx -= dx; break
        if px[sx, sy] >= WHITE:
            sys.exit(f"could not find the photograph under {first!r}")
        x = sx
        while not col_white(x, sy - 60, sy + 200): x -= 1
        left = x + 1
        x = sx
        while not col_white(x, sy - 60, sy + 200): x += 1
        right = x
        y = sy
        while not row_white(y, left + 40, right - 40): y -= 1
        top = y + 1
        y = sy
        while not row_white(y, left + 40, right - 40): y += 1
        bottom = y
        crop = rgb.crop((left, top, right, bottom))
        out = ROOT / "img" / f"rowcast_plant_{stem}.jpg"
        crop.save(out, "JPEG", quality=86, optimize=True, progressive=True)
        sizes[stem] = crop.size
        print(f"{stem:26s} {crop.size[0]}x{crop.size[1]}  {out.relative_to(ROOT)}")
    print(json.dumps(sizes))


if __name__ == "__main__":
    main()
