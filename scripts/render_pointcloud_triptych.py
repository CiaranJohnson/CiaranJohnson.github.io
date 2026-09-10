#!/usr/bin/env python
"""Render the base / arm / merged comparison as a looping rotation video.

Three panels side by side, all sharing one camera, rotating through a full
360 degrees so the clip loops seamlessly:

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

BG = 0.972  # near-white panel background

CENTRE = np.array([25.0, 0.0, 3.2])
# Looking down from a high angle, what has to fit on screen is the corridor's
# ~58 x 18 m footprint. Seen from above the footprint just rotates in plane, so
# a constant radius frames it consistently -- the elliptical radius that a
# low-elevation orbit needs would only make the framing pump in and out here.
RADIUS = 73.0
ELEVATION = 45.0

# Rather than a full 360 spin, the camera eases back and forth across the arc
# where the corridor frames well in a tall panel. A full turn would swing round
# to broadside, where the 58 m length overflows the panel unless you pull so far
# back that the detail is lost. sin() makes the sweep periodic, so the clip
# loops with no seam and no repeated frame.
AZ_CENTRE, AZ_SWING = 12.0, 32.0

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


def orbit_eye(az_deg: float, el_deg: float, r: float) -> np.ndarray:
    az, el = np.radians(az_deg), np.radians(el_deg)
    return CENTRE + np.array([
        r * np.cos(el) * np.cos(az),
        r * np.cos(el) * np.sin(az),
        r * np.sin(el),
    ])


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
    ap.add_argument("--panel-width", type=int, default=620)
    ap.add_argument("--panel-height", type=int, default=700)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--point-size", type=float, default=1.5)
    ap.add_argument("--darken", type=float, default=0.86)
    ap.add_argument("--scale-width", type=int, default=1440,
                    help="downscale on encode; 0 keeps the render size")
    ap.add_argument("--crf", type=int, default=30)
    ap.add_argument("--elevation", type=float, default=ELEVATION)
    ap.add_argument("--radius", type=float, default=RADIUS)
    ap.add_argument("--az-centre", type=float, default=AZ_CENTRE)
    ap.add_argument("--az-swing", type=float, default=AZ_SWING)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--preview-az", default="-20,0,20,40,60")
    args = ap.parse_args()

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
    renderer = o3d.visualization.rendering.OffscreenRenderer(W, H)
    renderer.scene.set_background([BG, BG, BG, 1.0])
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

    probe = np.asarray(renderer.render_to_image())
    sheet_bg = tuple(int(v) for v in probe[0, 0][:3])

    counts = {
        "base": len(base_pos),
        "arm": len(arm_pos),
        "merged": len(base_pos) + len(arm_pos),
    }

    total_w = W * 3
    header = 74

    def frame(az: float) -> Image.Image:
        eye = orbit_eye(az, args.elevation, args.radius)
        sheet = Image.new("RGB", (total_w, H + header), sheet_bg)
        for i, (key, title, sub) in enumerate(PANELS):
            renderer.scene.show_geometry("base", key in ("base", "merged"))
            renderer.scene.show_geometry("arm", key in ("arm", "merged"))
            renderer.setup_camera(50.0, CENTRE.tolist(), eye.tolist(), [0, 0, 1])
            sheet.paste(Image.fromarray(np.asarray(renderer.render_to_image())),
                        (i * W, header))

        d = ImageDraw.Draw(sheet)
        s = W / 620.0
        for i, (key, title, sub) in enumerate(PANELS):
            cx = i * W + int(34 * s)
            d.text((cx, int(16 * s)), title, font=font(int(27 * s), True),
                   fill=(26, 30, 28))
            d.text((cx, int(48 * s)), f"{sub} · {counts[key] / 1e6:.2f}M points",
                   font=font(int(18 * s)), fill=(122, 128, 124))
            if i:
                d.line([(i * W, int(14 * s)), (i * W, H + header - int(14 * s))],
                       fill=(226, 224, 218), width=1)
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
        az = args.az_centre + args.az_swing * np.sin(2 * np.pi * k / n_frames)
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
        h = int(round((H + header) * args.scale_width / total_w)) // 2 * 2
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
