#!/usr/bin/env python
"""Render the base / arm / merged comparison as a looping rotation video.

Base and arm sit side by side on the top row, with the merged result on a full
width row beneath. All three share one camera, turning through a full 360
degrees so the clip loops seamlessly:

    Base LiDAR      raw base-mounted cloud
    Arm LiDAR       end-effector cloud, registered into the base frame
    Merged          both together -- exactly what the dataset ships

The clouds are drawn at full resolution: no voxel downsampling at all. The
merged panel is the literal union of the other two, which is what the released
`merged_raw.pcd` is.

Both inputs are released in the base LiDAR frame, so each is pushed through
`forest_alignment_transform.csv` into the temporal reference frame first.

White background, with the turbo height ramp darkened to hold contrast against
it and laser intensity darkening the strongest returns.

Requires the `forestyear3d` conda env. From the repo root:

    scripts/render_pointcloud_triptych.sh --preview   # key frames only
    scripts/render_pointcloud_triptych.sh             # full render
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

TRIALS = "/home/robot/Coding/ForestYear3D/data/field_trials"

# 22 September 2025: fewest high-intensity points removed by the cleanup stage
# of all 528 scans, i.e. the least operator ghosting. Pre-thinning.
DEFAULT_SCAN = "2025-09-22-13-26-37"

CROP = dict(xmin=-4.0, xmax=54.0, ymin=-9.0, ymax=9.0, zmin=-1.2, zmax=13.0)
Z_LO, Z_HI = -1.0, 11.5

# The page background, so the panels sit flush in the article rather than as a
# grey block. Open3D will not reproduce this value directly: with its default
# post-processing the output saturates around 235, and even with post-processing
# disabled a colour-space conversion shifts it. The value actually passed to the
# renderer is solved for at startup by calibrate_background().
SITE_BG = (251, 250, 248)  # #fbfaf8, --bg in style.css

CENTRE_XY = (25.0, 0.0)
# The look-at point projects to the centre of frame. Aiming at the cloud's
# mid-height left it sitting low, wasting ~95px at the top while the near end of
# the corridor ran off the bottom, so the camera aims at ground level instead.
CENTRE_Z = 0.0
# Looking down from a high angle, what has to fit on screen is the corridor's
# ~58 x 18 m footprint. Seen from above the footprint just rotates in plane, so
# a constant radius frames it consistently -- the elliptical radius that a
# low-elevation orbit needs would only make the framing pump in and out here.
ELEVATION = 45.0

# Reference panel height and vertical field of view that vfov is scaled from.
BASE_PANEL_H = 520
BASE_VFOV = 50.0

# Full turn, so the radius has to vary with azimuth to keep the ~58 x 18 m
# corridor a consistent size on screen.
#
# Note the ellipse runs the opposite way to what a ground-level orbit needs.
# Looking down from 45 degrees, the corridor's length projects onto the panel's
# SHORT axis when the camera is end-on, and onto its long axis when broadside --
# so end-on is the tight case here and needs the greater standoff.
# Fixed orbit: the radius depends only on azimuth, never on the frame, so the
# apparent size stays steady instead of pumping in and out as it turns.
# Everything the corridor needs vertically is found by widening the field of
# view (see vfov below) rather than by backing the camera off.
R_ALONG, R_ACROSS = 62.0, 54.0

PANELS = [
    ("base", "Base LiDAR", "fixed to the mobile base"),
    ("arm", "Arm LiDAR", "carried on the manipulator"),
    ("merged", "Merged", "what the dataset ships"),
]


def find_scan_dir(scan: str) -> str:
    day = datetime.strptime(scan, "%Y-%m-%d-%H-%M-%S").strftime("%d_%m_%Y")
    path = os.path.join(TRIALS, day, "pcd")
    if not os.path.isdir(path):
        hits = glob.glob(os.path.join(TRIALS, "*", "pcd", "merged", scan))
        if not hits:
            raise SystemExit(f"no field trial directory for {scan}")
        path = os.path.dirname(os.path.dirname(hits[0]))
    return path


def load(path: str, transform: np.ndarray):
    import open3d as o3d

    pc = o3d.t.io.read_point_cloud(path)
    attrs = dict(pc.point.items())
    pos = attrs["positions"].numpy().astype(np.float64)
    inten = attrs["intensity"].numpy().ravel().astype(np.float32)

    pos = (transform[:3, :3] @ pos.T).T + transform[:3, 3]
    m = (
        (pos[:, 0] > CROP["xmin"]) & (pos[:, 0] < CROP["xmax"])
        & (pos[:, 1] > CROP["ymin"]) & (pos[:, 1] < CROP["ymax"])
        & (pos[:, 2] > CROP["zmin"]) & (pos[:, 2] < CROP["zmax"])
    )
    return pos[m], inten[m]


def colourise(pos, inten, i_lo, i_hi, darken):
    """Turbo by height, darkened for a white background; intensity darkens more."""
    import matplotlib

    zt = np.clip((pos[:, 2] - Z_LO) / (Z_HI - Z_LO), 0.0, 1.0)
    rgb = matplotlib.colormaps["turbo"](zt)[:, :3]

    li = np.log1p(inten)
    inorm = np.clip((li - i_lo) / max(i_hi - i_lo, 1e-6), 0.0, 1.0)
    # On white, a stronger return should read as darker, not brighter.
    return np.clip(rgb * (darken - 0.22 * inorm)[:, None], 0.0, 1.0)


def orbit_eye(az_deg: float, el_deg: float, r_along: float,
              r_across: float, centre: np.ndarray,
              exp: float = 1.0) -> np.ndarray:
    az, el = np.radians(az_deg), np.radians(el_deg)
    # Superellipse rather than a plain ellipse. With exponent 2 (a true
    # ellipse) the diagonals sit closest in, but the diagonals are exactly where
    # the corridor needs the most standoff, so the cardinal views had to be
    # pushed way out to compensate. Exponent 1 bulges the radius at the
    # diagonals instead, letting end-on and broadside sit much closer.
    r = (abs(r_along * np.cos(az)) ** exp
         + abs(r_across * np.sin(az)) ** exp) ** (1.0 / exp)
    return centre + np.array([
        r * np.cos(el) * np.cos(az),
        r * np.cos(el) * np.sin(az),
        r * np.sin(el),
    ])


def calibrate_background(renderer, target, iters=18):
    """Solve for the background value that renders as `target` (0-255 RGB).

    Open3D applies a colour transform between the value handed to
    set_background() and the pixels that come out, so matching the page
    background exactly means inverting it. A per-channel bisection is version
    proof and costs a handful of empty renders.
    """
    lo = np.zeros(3)
    hi = np.ones(3)
    val = np.array(target, dtype=float) / 255.0
    for _ in range(iters):
        renderer.scene.set_background([val[0], val[1], val[2], 1.0])
        out = np.asarray(renderer.render_to_image())[0, 0][:3].astype(float)
        for c in range(3):
            if out[c] < target[c]:
                lo[c] = val[c]
            else:
                hi[c] = val[c]
        val = (lo + hi) / 2.0
    # `hi` is the end of the bracket known to render at or above the target,
    # whereas the final midpoint can land a quantisation step below it.
    renderer.scene.set_background([hi[0], hi[1], hi[2], 1.0])
    out = np.asarray(renderer.render_to_image())[0, 0][:3]
    return hi, tuple(int(v) for v in out)


def font(size: int, bold: bool = False):
    from PIL import ImageFont
    import matplotlib

    d = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(os.path.join(d, name), size)
    except OSError:
        return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", default=DEFAULT_SCAN)
    ap.add_argument("--out", default="media/base_arm_merged.mp4")
    ap.add_argument("--frames-dir", default=None)
    ap.add_argument("--panel-width", type=int, default=860)
    ap.add_argument("--panel-height", type=int, default=640)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--point-size", type=float, default=1.5)
    ap.add_argument("--darken", type=float, default=0.86)
    ap.add_argument("--scale-width", type=int, default=1440,
                    help="downscale on encode; 0 keeps the render size")
    ap.add_argument("--crf", type=int, default=33)
    ap.add_argument("--elevation", type=float, default=ELEVATION)
    ap.add_argument("--r-along", type=float, default=R_ALONG)
    ap.add_argument("--r-across", type=float, default=R_ACROSS)
    ap.add_argument("--centre-z", type=float, default=CENTRE_Z,
                    help="look-at height; lowering it lifts the cloud in frame")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--preview-az", default="0,45,90,135")
    args = ap.parse_args()

    centre = np.array([CENTRE_XY[0], CENTRE_XY[1], args.centre_z])

    pcd_dir = find_scan_dir(args.scan)
    merged_dir = os.path.join(pcd_dir, "merged", args.scan)
    base_pcd = os.path.join(pcd_dir, "raw", "base_pcd", f"{args.scan}.pcd")
    arm_pcd = os.path.join(merged_dir, "aligned_arm.pcd")
    tf_csv = os.path.join(merged_dir, "forest_alignment_transform.csv")
    for p in (base_pcd, arm_pcd, tf_csv):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}")

    import open3d as o3d
    from PIL import Image, ImageDraw

    T = np.loadtxt(tf_csv, delimiter=",")
    t0 = time.time()
    base_pos, base_i = load(base_pcd, T)
    arm_pos, arm_i = load(arm_pcd, T)
    print(f"scan {args.scan}")
    print(f"  base {len(base_pos) / 1e3:7.0f}k points (full resolution)")
    print(f"  arm  {len(arm_pos) / 1e6:7.2f}M points (full resolution)")
    print(f"  loaded in {time.time() - t0:.0f}s")

    li = np.log1p(np.concatenate([base_i, arm_i]))
    i_lo, i_hi = np.percentile(li, [2, 98])

    W, H = args.panel_width, args.panel_height
    HEADER = 68

    # Open3D's Filament backend cannot share geometry across two
    # OffscreenRenderers in one process, so everything is drawn by a single
    # full-width renderer. Cropping its centre W columns is exactly equivalent
    # to rendering at width W with the same vertical field of view -- the
    # camera looks at the scene centre, so only horizontal margin is trimmed.
    renderer = o3d.visualization.rendering.OffscreenRenderer(W * 2, H)
    # Post-processing (tone mapping) clamps whites around 235, well short of the
    # page background, so it is switched off before calibrating.
    renderer.scene.view.set_post_processing(False)
    bg_val, bg_actual = calibrate_background(renderer, SITE_BG)
    print(f"  background {SITE_BG} -> rendered {bg_actual}")

    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultUnlit"
    mat.point_size = args.point_size

    for name, pos, inten in (("base", base_pos, base_i), ("arm", arm_pos, arm_i)):
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pos)
        pcd.colors = o3d.utility.Vector3dVector(
            colourise(pos, inten, i_lo, i_hi, args.darken))
        renderer.scene.add_geometry(name, pcd, mat)
        renderer.scene.show_geometry(name, False)

    sheet_bg = bg_actual

    counts = {
        "base": len(base_pos),
        "arm": len(arm_pos),
        "merged": len(base_pos) + len(arm_pos),
    }

    total_w = W * 2
    total_h = (HEADER + H) * 2

    # Taller panels are only useful if the camera actually shows more: the
    # vertical field of view is what decides how much of the scene fits, so it
    # is scaled with the panel height. Derived so the HORIZONTAL field stays
    # exactly as it was at the reference height, which keeps the left/right
    # framing of the corridor unchanged and adds the extra room vertically.
    vfov = 2.0 * np.degrees(np.arctan(
        np.tan(np.radians(BASE_VFOV / 2.0)) * H / BASE_PANEL_H))
    print(f"  panel {W}x{H}, vertical fov {vfov:.1f} deg")

    # (key, title, subtitle, x, y, full_width)
    LAYOUT = [
        ("base", "Base LiDAR", "fixed to the mobile base", 0, 0, False),
        ("arm", "Arm LiDAR", "carried on the manipulator", W, 0, False),
        ("merged", "Merged", "what the dataset ships", 0, HEADER + H, True),
    ]

    def render_panel(key, eye, full_width):
        renderer.scene.show_geometry("base", key in ("base", "merged"))
        renderer.scene.show_geometry("arm", key in ("arm", "merged"))
        renderer.setup_camera(vfov, centre.tolist(), eye.tolist(), [0, 0, 1])
        img = Image.fromarray(np.asarray(renderer.render_to_image()))
        return img if full_width else img.crop((W // 2, 0, W // 2 + W, H))

    def frame(az: float) -> Image.Image:
        eye = orbit_eye(az, args.elevation, args.r_along, args.r_across,
                        centre, 2.0)
        sheet = Image.new("RGB", (total_w, total_h), sheet_bg)
        for key, title, sub, x, y, fw in LAYOUT:
            sheet.paste(render_panel(key, eye, fw), (x, y + HEADER))

        d = ImageDraw.Draw(sheet)
        s = W / 860.0
        for key, title, sub, x, y, fw in LAYOUT:
            d.text((x + int(30 * s), y + int(14 * s)), title,
                   font=font(int(27 * s), True), fill=(26, 30, 28))
            d.text((x + int(30 * s), y + int(46 * s)),
                   f"{sub} · {counts[key] / 1e6:.2f}M points",
                   font=font(int(18 * s)), fill=(122, 128, 124))
        rule = (226, 224, 218)
        d.line([(W, int(12 * s)), (W, HEADER + H - int(12 * s))], fill=rule, width=1)
        d.line([(int(30 * s), HEADER + H), (total_w - int(30 * s), HEADER + H)],
               fill=rule, width=1)
        return sheet

    n_frames = int(args.seconds * args.fps)

    if args.preview:
        out_dir = args.frames_dir or "preview_frames"
        os.makedirs(out_dir, exist_ok=True)
        for az in (float(v) for v in args.preview_az.split(",")):
            frame(az).save(os.path.join(out_dir, f"az{az:+07.1f}.png"))
            print("  preview az", az)
        print(f"preview frames in {out_dir}/")
        return 0

    frames_dir = args.frames_dir or os.path.expanduser(
        "~/.cache/forestyear3d_triptych/frames")
    os.makedirs(frames_dir, exist_ok=True)
    for old in glob.glob(os.path.join(frames_dir, "f*.png")):
        os.remove(old)

    t0 = time.time()
    for k in range(n_frames):
        az = 360.0 * k / n_frames
        frame(az).save(os.path.join(frames_dir, f"f{k:05d}.png"))
        if k % 20 == 0 or k == n_frames - 1:
            el = time.time() - t0
            rate = (k + 1) / max(el, 1e-6)
            print(f"  frame {k + 1}/{n_frames}  {rate:.2f} fps  "
                  f"eta {(n_frames - k - 1) / max(rate, 1e-6):.0f}s", flush=True)

    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg = "ffmpeg"

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    cmd = [ffmpeg, "-nostdin", "-y", "-loglevel", "error",
           "-framerate", str(args.fps),
           "-i", os.path.join(frames_dir, "f%05d.png")]
    if args.scale_width:
        h = int(round(total_h * args.scale_width / total_w)) // 2 * 2
        cmd += ["-vf", f"scale={args.scale_width}:{h}:flags=lanczos"]
    cmd += ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-crf", str(args.crf), "-preset", "slow",
            "-movflags", "+faststart", "-an", args.out]
    subprocess.run(cmd, check=True)

    poster = os.path.splitext(args.out)[0] + "_poster.jpg"
    subprocess.run([ffmpeg, "-nostdin", "-y", "-loglevel", "error",
                    "-i", args.out, "-frames:v", "1", "-q:v", "4", poster],
                   check=True)

    print(f"\n{args.out}  {os.path.getsize(args.out) / 1e6:.1f} MB "
          f"({args.seconds:.0f}s loop)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
