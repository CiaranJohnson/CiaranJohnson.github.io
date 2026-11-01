# Video assets

Clips referenced by `ForestYear3D/index.html` and `ROWCAST/index.html` live here;
the ROWCAST clips are described in the last two sections. Each `<video>` block on
the ForestYear3D page is commented out next to a dashed placeholder; to publish a clip, drop
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
H.264 encode; point-cloud noise compresses badly, so it takes CRF 32 to keep
it to 25 MB. The dense June foliage in the intro is the most expensive part. `--preview` renders a handful of key frames
instead of the full 58 s if you want to retune the camera or the colour ramp.

The video opens with an 8 s flight through the June 2025 cloud, starting about
halfway down the corridor on the same line the closing flight takes through
May 2026. Over the last 6 s the camera pans round to look back down the
corridor and, in the last 3 s, climbs out onto the orbit. The climb and the pan
end on the orbit's first pose with its speed and pan rate, so there is no cut.
`--turn` and `--lift` set those two windows; `--intro 0` renders without it.

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

## ROWCAST splat clips

`ROWCAST/index.html` embeds splat renders of the ROWCAST plants. The
full-resolution renders live in `media/splats_source/` (gitignored, like
`media/final_protocols/`) and `scripts/compress_splats.sh` writes the web
versions and their posters into this folder:

| Published file | Source render | Caption on the page |
| --- | --- | --- |
| `stationary_big_plants__flythrough.mp4` | same name | Large cohort, flythrough |
| `stationary_small_plants__flythrough.mp4` | same name | Small cohort, flythrough |
| `stationary_big_plants__indian_laurel_fig.mp4` | `stationary_big_plants__canopyball.mp4` | Indian laurel fig |
| `stationary_big_plants__fiddle_leaf_fig.mp4` | `stationary_big_plants__biggreen.mp4` | Fiddle-leaf fig |
| `stationary_big_plants__red.mp4` | same name | Red poinsettia |
| `stationary_big_plants__white.mp4` | same name | White poinsettia |
| `stationary_big_plants__greenwhite.mp4` | same name | Ivy gourd |
| `stationary_big_plants__mediumgreen.mp4` | same name | Split-leaf philodendron |
| `stationary_small_plants__small_1.mp4` | same name | P1 |
| `stationary_small_plants__small_2.mp4` | same name | P2 |
| `stationary_small_plants__small_3.mp4` | same name | P3 |
| `stationary_small_plants__small_4.mp4` | same name | P4 |
| `stationary_small_plants__small_5.mp4` | same name | P6 |
| `stationary_small_plants__small_6.mp4` | same name | P5 |

The captions use the plant names from the manuscript (its Figure 13). The
large plants were matched to the renders by appearance; the small-plant
mapping was confirmed by the author (note that `small_5` is P6 and `small_6`
is P5). The
published file names were left as they are: two carry the plant name (the
`MAP` in the script renames them from the render's working name), the rest
keep their working names.

The page also carries stills from the manuscript PDF, in `img/`:
`rowcast_field.jpg` (Figure 1, extracted with `pdfimages` and downscaled) and
the twelve plant tiles `rowcast_plant_*.jpg`, which are the panels of
Figure 13 cut out one by one by `scripts/cut_plant_tiles.py` (it renders the
page at 600 dpi, finds each photograph under its label and saves it; the names
are set as page text). Four earlier stills are no longer on the page and stay
in `img/` unused: `rowcast_plants.jpg` (Figure 13 as one image, replaced by the
tiles), `rowcast_markers.jpg` (Figure 4), `rowcast_commissioning_map.jpg`
(Figure 3) and `rowcast_protocol_views.jpg` (Figure 22), after the author took
the stills out of the Commission and Execute sections.

Flythroughs are published at 1280x720 and shown with controls, so they are only
downloaded when played. Plant orbits are published at 540x540 and play on their
own, GIF-style, while on screen, so keep them small: about 0.4-0.7 MB each for
a clean render at the default CRF 28 (a noisy render such as `small_4`, whose
reverse views are mostly artefacts, comes out at about 1.6 MB). To add a plant:
drop the render in `media/splats_source/`, add its `source:published` line to
`MAP` in the script, run `scripts/compress_splats.sh <part-of-the-name>` to
encode just that clip, and copy a `<figure class="video-item">` block on the
page. To rename one: edit its `MAP` line, re-run, `git rm` the old
`media/<old>.mp4` and `<old>_poster.jpg`, and update the figure's two paths.
The script lists renders in the source folder with no `MAP` entry (`UNMAPPED`)
and published clips that no `MAP` entry produces any more (`STALE`).

The flythroughs fade in from black, so their posters are grabbed 0.6 s in
(`FLY_POSTER_AT`) rather than at frame 0.

The YouTube Short in the Execute section (`D7hwxlzGvhw`) takes no local
file; it is an `<iframe>` like the reel on the ForestYear3D page. In the
Phenotype section, `canopyball_reconstruction_1080p.mp4` (the RGB-D
phenotyping explainer) is published as delivered, 1920x1080 at 2.3 Mb/s,
because its small text overlays would blur at 720p; it only downloads when
played. Its poster is frame 0:

```bash
ffmpeg -i media/canopyball_reconstruction_1080p.mp4 -frames:v 1 -q:v 4 media/canopyball_reconstruction_1080p_poster.jpg
```

## ROWCAST workflow-stage clips

The ROWCAST page has one section per stage of the workflow, and the clips of
the trial sit in the stage they belong to. The originals (phone footage and
RViz screen recordings, 16-273 MB each, re-muxed with VLC) live in
`media/stages_source/` (gitignored) and `scripts/compress_stage_clips.sh`
writes the web versions and their posters into this folder:

| Published file | Source | Section | Shape |
| --- | --- | --- | --- |
| `rowcast_commission_field.mp4` | `comissioning_field.mp4` | Commission | phone, turned clockwise, 4:5 crop from 15% down |
| `rowcast_commission_map.mp4` | `comissioning_rviz.mp4` | Commission | RViz, cropped to the live window, 16:9 |
| `rowcast_scout.mp4` | `scout.mp4` | Scout | phone, turned clockwise, 4:5 crop from 15% down |
| `rowcast_plan.mp4` | `planning.mp4` | Plan | RViz, black bar cropped off, 16:9 |
| `rowcast_execute_fixed.mp4` | `fixed.mp4` | Execute | phone, turned clockwise, full 9:16 |
| `rowcast_execute_random.mp4` | `random.mp4` | Execute | phone, turned clockwise, full 9:16 |

All are published 720 px wide (1280 px for the screen recordings), 30 fps,
CRF 26, silent, 1-14 MB each. The phone clips beside a paragraph (Commission,
Scout) are cropped to 4:5 like the protocol clips on the ForestYear3D page,
with the crop window chosen per clip so the robot and markers stay in frame.
The two Execute clips keep the whole 9:16 frame because they sit in a row with
the YouTube Short, which is 9:16.

Orientation is set per clip, not read from the file. The phone clips were
re-encoded with VLC, which wrote a track matrix that is a transpose (a quarter
turn plus a mirror) on three of them and no matrix on `fixed.mp4`; ffmpeg's
autorotate follows such a matrix literally and mirrored the three, which the
author spotted on the page. The script therefore tells ffmpeg the rotation is
zero (`-display_rotation 0`, which also keeps the matrix out of the output) and
applies `turn=cw`, a quarter turn clockwise, to every phone clip, `fixed.mp4`
included: all four come from the same phone held the same way, and in both
Execute clips the robot drives away from the camera with the row of pots on
its right. The per-clip settings are the `CLIPS` table in the script;
`scripts/compress_stage_clips.sh scout` re-encodes one clip.

Notes:
- H.264 MP4 is the safe format for GitHub Pages; add a WebM `<source>` first if
  you want it.
- GitHub blocks pushes over 100 MB per file and warns above 50 MB. Keep clips
  short and compressed, or host them externally and swap the `<video>` for an
  `<iframe>` — `.video-slot iframe` is already styled for that.
- To preview locally, run `python3 -m http.server 8000` from the repo root and
  open http://localhost:8000/ROWCAST/ (or another page). Python's server
  ignores byte-range requests, so seeking is limited and Safari/iOS will not
  play the clips from it; GitHub Pages serves ranges, so the live site is fine.
