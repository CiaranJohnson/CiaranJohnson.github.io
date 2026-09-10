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

`base_arm_merged.mp4` is a 12 s silent loop: three panels sharing one camera,
easing back and forth across a high angle looking down on the corridor. Rebuild
with:

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
- **The sweep is a sine, not a full spin.** A full turn swings round to
  broadside, where the 58 m corridor overflows a tall panel unless you pull so
  far back the detail is lost. `sin()` is periodic, so the loop has no seam.
- **White background**, with the turbo height ramp darkened and the strongest
  returns darkened further, so the colours hold up against it. The renderer
  samples Open3D's actual background pixel to paint the label strip, because
  its tone mapping means the output is not the literal background value.

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
