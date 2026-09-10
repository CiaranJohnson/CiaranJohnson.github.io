# Video assets

Clips referenced by `ForestYear3D/index.html` live here. Each `<video>` block on
that page is commented out next to a dashed placeholder; to publish a clip, drop
the file in this folder, delete the placeholder `<div class="video-pending">`,
and uncomment the `<video>` element below it.

Filenames the page already expects:

| File | Section |
| --- | --- |
| `pointcloud_year.mp4` | Point clouds across the seasons — published |
| `base_arm_merged.mp4` | Base / arm / merged comparison — published |
| `protocols_overview.mp4` | Robot protocols — wide hero |
| `protocol_fixed.mp4` / `protocol_random.mp4` / `protocol_1.mp4` / `protocol_2.mp4` / `protocol_3.mp4` | Robot protocols — per-strategy grid |

Optional poster frames use the same stem with a `_poster.jpg` suffix.

The "ALFRED on the trail, summer to spring" section takes no local files: it
embeds a single YouTube video (`OTpon_Deb2Q`) via an `<iframe>`.

`pointcloud_year.mp4` is generated, not hand-edited. Re-run

```bash
scripts/render_pointcloud_flythrough.sh
```

to rebuild it and its poster from the 16 aligned planning clouds in the
ForestYear3D data tree. The script renders 1600x900 frames and publishes a 720p
H.264 encode; point-cloud noise compresses badly, so CRF 32 is what keeps it
around 15 MB rather than 55 MB. `--preview` renders a handful of key frames
instead of the full 50 s if you want to retune the camera or the colour ramp.

## Base / arm / merged comparison

`base_arm_merged.mp4` is a 12 s silent loop. Base and arm sit side by side on
the top row with the merged result full width beneath, all sharing one camera,
turning through a full 360 degrees at a high angle looking down on the corridor.
Rebuild with:

```bash
scripts/render_pointcloud_triptych.sh            # full render
scripts/render_pointcloud_triptych.sh --preview  # key frames only
```

Worth knowing before changing it:

- **Full resolution, no downsampling.** 0.64M base points and 4.84M arm points
  go straight to the renderer. Nothing is voxel-reduced -- it is an offline
  render, so there is no reason to.
- **Merged is the literal union** of the other two panels, which is what the
  released `merged_raw.pcd` is (the point counts add up exactly).
- **Both clouds are pushed into the temporal reference frame** with
  `forest_alignment_transform.csv` first. The raw base cloud and
  `aligned_arm.pcd` ship in the base LiDAR frame, so without that the panels
  would not line up.
- **The orbit is fixed, not fitted per frame.** The radius depends only on
  azimuth (`R_ALONG` 62 end-on, `R_ACROSS` 54 broadside), so the apparent size
  changes smoothly as it turns. Solving the radius per frame to fit the cloud
  exactly was tried and reverted: it kept the cloud a constant size but the
  constant rescaling read as the camera pumping in and out.
- **Room for the turn comes from the field of view, not the camera distance.**
  `vfov` is derived from the panel height so that the HORIZONTAL field matches
  what it was at `BASE_PANEL_H`, which leaves the left/right framing alone and
  adds the extra space vertically. Note a taller panel on its own would achieve
  nothing: with a fixed vertical field of view, extra pixels of height just
  scale the cloud up by the same factor.
- **The look-at sits at ground level**, not mid-height. Aiming higher left the
  cloud low in frame, wasting the top while the near end ran off the bottom.
- Clearances were checked by measuring rendered content against every panel
  edge across eight azimuths; the current settings clear by 34px at the
  tightest point.
- **The two-row layout is what makes a full 360 fit.** Three panels side by side
  left each one too narrow to hold the corridor broadside.
- **One renderer, not three.** Open3D's Filament backend cannot share geometry
  across two `OffscreenRenderer` instances in a process, so everything is drawn
  by a single full-width renderer and the half-width panels are its centre crop,
  which is exactly equivalent at the same vertical field of view.
- **The background is the page background** (`#fbfaf8`, `--bg` in style.css),
  so the panels sit flush in the article. Getting there needs two steps:
  Open3D's default post-processing clamps whites around 235, so tone mapping is
  switched off, and even then a colour-space conversion shifts the value, so
  `calibrate_background()` bisects for the input that renders as the exact
  target. The turbo height ramp is darkened and the strongest returns darkened
  further so the colours hold up against the light ground.

The scan is 2025-09-22-13-26-37, picked from
`corridor_island_cleanup_summary.csv` as the acquisition with the fewest
high-intensity points removed of all 528 -- that pass is what strips the
operator's reflective clothing, so this scan has the least ghosting.

Notes:
- H.264 MP4 is the safe format for GitHub Pages; add a WebM `<source>` first if
  you want it.
- GitHub blocks pushes over 100 MB per file and warns above 50 MB. Keep clips
  short and compressed, or host them externally and swap the `<video>` for an
  `<iframe>` — `.video-slot iframe` is already styled for that.
