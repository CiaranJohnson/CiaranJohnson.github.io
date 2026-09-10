#!/usr/bin/env python
"""Render the seasonal point-cloud flythrough for the ForestYear3D page.

Reads the 16 per-survey-window planning clouds, colours them by height with a
secondary intensity modulation, and renders a single camera move over them in
chronological order (June 2025 -> May 2026):

    1. orbit   -- an elliptical orbit around the outside of the corridor
    2. rise    -- lift and pitch over to a top-down view
    3. topdown -- hold overhead while the seasons replay
    4. fly     -- descend into the corridor and travel along it

Each phase advances through the clouds so every survey window is on screen at
some point, and phases 1 and 3 each cover the full year.

Requires the `forestyear3d` conda env (open3d + matplotlib) and the ffmpeg that
imageio-ffmpeg ships. Run from the repo root:

    scripts/render_pointcloud_flythrough.sh                # full render
    scripts/render_pointcloud_flythrough.sh --preview      # key frames only

Point clouds are cached as .npz after the first load, since decoding and
voxel-downsampling 16 x 4.5M points takes about a minute.
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time
from datetime import datetime

import numpy as np

SRC_DEFAULT = "/home/robot/Coding/ForestYear3D/data/selected_pcds/planning"
CACHE_DEFAULT = os.path.expanduser("~/.cache/forestyear3d_flythrough")

# Crop box, in the aligned map frame. Keeps the corridor and the forest either
# side of it, and drops the sparse long-range returns that would otherwise pull
# the camera framing out to nothing. Shared by every cloud so the seasonal
# comparison is like for like.
CROP = dict(xmin=-4.0, xmax=54.0, ymin=-9.0, ymax=9.0, zmin=-1.2, zmax=13.0)

# Height ramp bounds, metres. Ground sits near -1.0; canopy tops out around 12.
Z_LO, Z_HI = -1.0, 11.5


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def survey_label(path: str) -> tuple[str, str]:
    """('2025-06-10-15-30-21_planning.pcd') -> ('June 2025', '10 June 2025')."""
    stem = os.path.basename(path).split("_")[0]
    dt = datetime.strptime(stem, "%Y-%m-%d-%H-%M-%S")
    return dt.strftime("%B %Y"), dt.strftime("%-d %B %Y")


def load_cloud(path: str, voxel: float, cache_dir: str):
    """Load, crop and voxel-downsample one cloud. Returns (xyz, intensity)."""
    os.makedirs(cache_dir, exist_ok=True)
    key = f"{os.path.basename(path)}.v{voxel:.3f}.npz"
    cache = os.path.join(cache_dir, key)
    if os.path.exists(cache):
        d = np.load(cache)
        return d["pos"], d["inten"]

    import open3d as o3d

    pc = o3d.t.io.read_point_cloud(path)
    attrs = dict(pc.point.items())
    pos = attrs["positions"].numpy().astype(np.float32)
    inten = attrs["intensity"].numpy().ravel().astype(np.float32)

    m = (
        (pos[:, 0] > CROP["xmin"]) & (pos[:, 0] < CROP["xmax"])
        & (pos[:, 1] > CROP["ymin"]) & (pos[:, 1] < CROP["ymax"])
        & (pos[:, 2] > CROP["zmin"]) & (pos[:, 2] < CROP["zmax"])
    )
    pos, inten = pos[m], inten[m]

    # Keep one point per voxel. np.unique on the quantised keys is a little
    # slower than open3d's own downsample but keeps the matching intensity.
    keys = np.floor(pos / voxel).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    pos, inten = pos[idx], inten[idx]

    np.savez_compressed(cache, pos=pos, inten=inten)
    return pos, inten


def colourise(pos: np.ndarray, inten: np.ndarray, cmap_name: str,
              i_lo: float, i_hi: float) -> np.ndarray:
    """Height ramp for hue, log-intensity for brightness."""
    import matplotlib

    zt = np.clip((pos[:, 2] - Z_LO) / (Z_HI - Z_LO), 0.0, 1.0)
    rgb = matplotlib.colormaps[cmap_name](zt)[:, :3]

    # Intensity spans ~1..1100 with a long tail, so compress it before
    # normalising or almost everything lands in the bottom decile.
    li = np.log1p(inten)
    lo, hi = np.percentile(li, [2, 98])
    inorm = np.clip((li - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return np.clip(rgb * (i_lo + (i_hi - i_lo) * inorm)[:, None], 0.0, 1.0)


# --------------------------------------------------------------------------
# Camera
# --------------------------------------------------------------------------

CENTRE = np.array([25.0, 0.0, 3.2])

# The cloud is a long thin slab (~58 x 18 x 14 m). A circular orbit would frame
# it very differently along its length than across it, so the orbit radius is
# an ellipse: close when looking down the corridor, far when looking across it.
R_ALONG, R_ACROSS = 28.0, 55.0


def smoothstep(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def orbit_eye(az_deg: float, el_deg: float, scale: float = 1.0) -> np.ndarray:
    az, el = np.radians(az_deg), np.radians(el_deg)
    r = scale * np.hypot(R_ALONG * np.cos(az), R_ACROSS * np.sin(az))
    return CENTRE + np.array([
        r * np.cos(el) * np.cos(az),
        r * np.cos(el) * np.sin(az),
        r * np.sin(el),
    ])


TOPDOWN_EYE = CENTRE + np.array([0.0, 0.0, 38.0])


def camera_at(t: float, phases: dict):
    """Return (eye, centre, up, fov) for time t in seconds."""
    a_end = phases["orbit"]
    b_end = a_end + phases["rise"]
    c_end = b_end + phases["topdown"]
    d_end = c_end + phases["fly"]

    if t < a_end:                                   # 1. orbit
        u = t / a_end
        az = 25.0 + 360.0 * u
        el = 13.0 + 11.0 * smoothstep(u)
        return orbit_eye(az, el), CENTRE, [0, 0, 1], 50.0

    if t < b_end:                                   # 2. rise to overhead
        u = smoothstep((t - a_end) / phases["rise"])
        az = 25.0 + 360.0
        el = 24.0 + (88.0 - 24.0) * u
        eye = orbit_eye(az, el, scale=1.0 - 0.28 * u)
        eye = (1.0 - u) * eye + u * TOPDOWN_EYE
        # Roll the up-vector round so the corridor ends up lying across frame.
        up = np.array([0.0, 0.0, 1.0]) * (1.0 - u) + np.array([0.0, 1.0, 0.0]) * u
        return eye, CENTRE, up.tolist(), 50.0

    if t < c_end:                                   # 3. hold overhead
        u = (t - b_end) / phases["topdown"]
        # A slow drift keeps it from looking like a still image.
        eye = TOPDOWN_EYE + np.array([3.5 * np.sin(2 * np.pi * u) - 1.5, 0.0, 1.5 * u])
        ctr = CENTRE + np.array([3.5 * np.sin(2 * np.pi * u) - 1.5, 0.0, 0.0])
        return eye, ctr, [0, 1, 0], 50.0

    if t < d_end:                                   # 4. descend and fly through
        u = (t - c_end) / phases["fly"]
        drop = smoothstep(min(u * 2.2, 1.0))
        x = -6.0 + 56.0 * smoothstep(u)
        eye = np.array([
            (1.0 - drop) * TOPDOWN_EYE[0] + drop * x,
            0.0,
            (1.0 - drop) * TOPDOWN_EYE[2] + drop * 2.3,
        ])
        ctr = np.array([
            (1.0 - drop) * CENTRE[0] + drop * (x + 15.0),
            0.0,
            (1.0 - drop) * CENTRE[2] + drop * 2.2,
        ])
        up = np.array([0.0, 1.0, 0.0]) * (1.0 - drop) + np.array([0.0, 0.0, 1.0]) * drop
        return eye, ctr, up.tolist(), 50.0 + 16.0 * drop

    return TOPDOWN_EYE, CENTRE, [0, 1, 0], 50.0


def cloud_at(t: float, phases: dict, n: int) -> tuple[int, float]:
    """Which cloud is on screen at time t, and how far through its slot."""
    a_end = phases["orbit"]
    b_end = a_end + phases["rise"]
    c_end = b_end + phases["topdown"]

    if t < a_end:                       # full year during the orbit
        u = t / a_end
    elif t < b_end:                     # hold the last one while rising
        return n - 1, 1.0
    elif t < c_end:                     # full year again from above
        u = (t - b_end) / phases["topdown"]
    else:                               # one cloud for the flythrough
        return n - 1, 1.0

    i = min(int(u * n), n - 1)
    frac = u * n - i
    return i, frac


# --------------------------------------------------------------------------
# Overlay
# --------------------------------------------------------------------------

def font(size: int):
    from PIL import ImageFont
    import matplotlib

    path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")
    bold = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans-Bold.ttf")
    try:
        return ImageFont.truetype(bold if size >= 34 else path, size)
    except OSError:
        return ImageFont.load_default()


def draw_overlay(img, label: str, phase_name: str, W: int, H: int, fade: float):
    """Date bottom-left, caption above it, subtle scale bar bottom-right."""
    from PIL import Image, ImageDraw

    d = ImageDraw.Draw(img, "RGBA")
    s = W / 1600.0
    x0, y0 = int(56 * s), H - int(104 * s)
    a = int(255 * fade)

    d.text((x0, y0), label, font=font(int(46 * s)), fill=(255, 255, 255, a))
    d.text((x0, y0 + int(56 * s)), phase_name, font=font(int(23 * s)),
           fill=(190, 205, 200, int(a * 0.75)))

    # Height key: a short vertical turbo strip so the colours mean something.
    import matplotlib

    kx, ky, kw, kh = W - int(96 * s), H - int(300 * s), int(13 * s), int(196 * s)
    for j in range(kh):
        c = matplotlib.colormaps[CMAP](1.0 - j / kh)
        d.line([(kx, ky + j), (kx + kw, ky + j)],
               fill=(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), int(a * 0.9)))
    f = font(int(19 * s))
    d.text((kx + kw + int(9 * s), ky - int(6 * s)), f"{Z_HI:.0f} m",
           font=f, fill=(210, 218, 216, int(a * 0.85)))
    d.text((kx + kw + int(9 * s), ky + kh - int(13 * s)), "ground",
           font=f, fill=(210, 218, 216, int(a * 0.85)))
    return img


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------

CMAP = "turbo"


def main() -> int:
    global CMAP

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--out", default="media/pointcloud_year.mp4")
    ap.add_argument("--frames-dir", default=None,
                    help="keep PNG frames here instead of a temp dir")
    ap.add_argument("--cache", default=CACHE_DEFAULT)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--voxel", type=float, default=0.05)
    ap.add_argument("--point-size", type=float, default=2.0)
    ap.add_argument("--cmap", default="turbo")
    ap.add_argument("--intensity-range", default="0.60,1.15",
                    help="brightness multipliers at min and max intensity")
    ap.add_argument("--orbit", type=float, default=22.0)
    ap.add_argument("--rise", type=float, default=5.0)
    ap.add_argument("--topdown", type=float, default=14.0)
    ap.add_argument("--fly", type=float, default=9.0)
    ap.add_argument("--crf", type=int, default=32)
    ap.add_argument("--scale-height", type=int, default=720,
                    help="downscale on encode; 0 keeps the render size")
    ap.add_argument("--preview", action="store_true",
                    help="render a handful of key frames as PNGs and stop")
    ap.add_argument("--limit", type=int, default=0,
                    help="only use the first N clouds (quick iteration)")
    args = ap.parse_args()

    CMAP = args.cmap
    i_lo, i_hi = (float(v) for v in args.intensity_range.split(","))
    phases = dict(orbit=args.orbit, rise=args.rise,
                  topdown=args.topdown, fly=args.fly)
    total = sum(phases.values())

    files = sorted(glob.glob(os.path.join(args.src, "*.pcd")))
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"no .pcd files under {args.src}", file=sys.stderr)
        return 1
    print(f"{len(files)} clouds, {total:.0f}s at {args.fps}fps "
          f"= {int(total * args.fps)} frames, {args.width}x{args.height}")

    import open3d as o3d
    from PIL import Image

    renderer = o3d.visualization.rendering.OffscreenRenderer(args.width, args.height)
    renderer.scene.set_background([0.030, 0.036, 0.050, 1.0])
    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultUnlit"
    mat.point_size = args.point_size

    labels = []
    t0 = time.time()
    for i, f in enumerate(files):
        pos, inten = load_cloud(f, args.voxel, args.cache)
        rgb = colourise(pos, inten, CMAP, i_lo, i_hi)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pos.astype(np.float64))
        pcd.colors = o3d.utility.Vector3dVector(rgb.astype(np.float64))
        renderer.scene.add_geometry(f"c{i}", pcd, mat)
        renderer.scene.show_geometry(f"c{i}", False)
        labels.append(survey_label(f))
        print(f"  [{i + 1:2d}/{len(files)}] {labels[-1][1]:>18s}  "
              f"{len(pos) / 1e6:.2f}M pts")
    print(f"loaded in {time.time() - t0:.0f}s")

    phase_caption = {
        "orbit": "Orbit around the corridor",
        "rise": "Rising to an overhead view",
        "topdown": "The same 48 m, seen from above",
        "fly": "Through the corridor",
    }

    def phase_of(t: float) -> str:
        if t < phases["orbit"]:
            return "orbit"
        if t < phases["orbit"] + phases["rise"]:
            return "rise"
        if t < phases["orbit"] + phases["rise"] + phases["topdown"]:
            return "topdown"
        return "fly"

    def render(t: float, shown: list):
        idx, _ = cloud_at(t, phases, len(files))
        if shown and shown[0] != idx:
            renderer.scene.show_geometry(f"c{shown[0]}", False)
        if not shown or shown[0] != idx:
            renderer.scene.show_geometry(f"c{idx}", True)
            shown[:] = [idx]
        eye, ctr, up, fov = camera_at(t, phases)
        renderer.setup_camera(fov, list(ctr), list(eye), list(up))
        img = Image.fromarray(np.asarray(renderer.render_to_image()))
        fade = min(1.0, t / 0.8, max(0.0, (total - t) / 0.8))
        return draw_overlay(img, labels[idx][0], phase_caption[phase_of(t)],
                            args.width, args.height, fade)

    if args.preview:
        out_dir = args.frames_dir or "preview_frames"
        os.makedirs(out_dir, exist_ok=True)
        shown: list = []
        marks = [0.5, args.orbit * 0.28, args.orbit * 0.55, args.orbit * 0.85,
                 args.orbit + args.rise * 0.5, args.orbit + args.rise + 0.4,
                 args.orbit + args.rise + args.topdown * 0.55,
                 args.orbit + args.rise + args.topdown + args.fly * 0.35,
                 args.orbit + args.rise + args.topdown + args.fly * 0.8]
        for t in marks:
            render(t, shown).save(os.path.join(out_dir, f"t{t:06.2f}.png"))
            print("  preview", f"t{t:06.2f}.png")
        print(f"preview frames in {out_dir}/")
        return 0

    frames_dir = args.frames_dir or os.path.join(args.cache, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    for old in glob.glob(os.path.join(frames_dir, "f*.png")):
        os.remove(old)

    n_frames = int(total * args.fps)
    shown = []
    t0 = time.time()
    for k in range(n_frames):
        render(k / args.fps, shown).save(os.path.join(frames_dir, f"f{k:05d}.png"))
        if k % 60 == 0 or k == n_frames - 1:
            el = time.time() - t0
            rate = (k + 1) / max(el, 1e-6)
            print(f"  frame {k + 1}/{n_frames}  {rate:.1f} fps  "
                  f"eta {(n_frames - k - 1) / max(rate, 1e-6):.0f}s", flush=True)

    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg = "ffmpeg"

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    cmd = [
        ffmpeg, "-nostdin", "-y", "-loglevel", "error",
        "-framerate", str(args.fps),
        "-i", os.path.join(frames_dir, "f%05d.png"),
    ]
    if args.scale_height:
        w = int(round(args.width * args.scale_height / args.height)) // 2 * 2
        cmd += ["-vf", f"scale={w}:{args.scale_height}:flags=lanczos"]
    cmd += [
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-crf", str(args.crf), "-preset", "slow",
        "-movflags", "+faststart", "-an", args.out,
    ]
    subprocess.run(cmd, check=True)

    poster = os.path.splitext(args.out)[0] + "_poster.jpg"
    subprocess.run([ffmpeg, "-nostdin", "-y", "-loglevel", "error",
                    "-i", args.out, "-frames:v", "1", "-q:v", "4", poster],
                   check=True)

    mb = os.path.getsize(args.out) / 1e6
    print(f"\n{args.out}  {mb:.1f} MB  ({total:.0f}s)")
    print(f"{poster}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
