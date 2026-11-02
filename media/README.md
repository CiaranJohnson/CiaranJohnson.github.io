# Video assets

Clips referenced by `ForestYear3D/index.html`, `ROWCAST/index.html` and
`ALFRED/index.html` live here; the ROWCAST clips are described in the two
ROWCAST sections and the ALFRED clips in the last section, except the ALFRED
page's one phone clip, which is published with the ROWCAST stage clips and
described there. Each `<video>` block on
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
On the page it plays like a GIF: started while it is on screen, paused by a
click or Enter, through the same orbit script as the ROWCAST and ALFRED loops.
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
| `alfred_payload_study.mp4` | `alfred_payload_study.mp4` | ALFRED page, strut-frame section | phone held landscape, as shot, 848 px |

All are published 720 px wide (1280 px for the screen recordings), 30 fps,
CRF 26, silent, 1-14 MB each. The phone clips beside a paragraph (Commission,
Scout) are cropped to 4:5 like the protocol clips on the ForestYear3D page,
with the crop window chosen per clip so the robot and markers stay in frame.
The two Execute clips keep the whole 9:16 frame because they sit in a row with
the YouTube Short, which is 9:16.

The last row is not a ROWCAST clip. It is the one phone clip on the ALFRED
page, closing the strut-frame section beneath the still of the same
configuration: Christopher Quail's concurrent payload study in the field,
the robot driving a cone-marked route with the weight cage in place of the
manipulator while weights are added to it as it goes. It goes through this
script because it is phone footage with the same needs. The source is the
VLC export `vlc-record-2026-11-02-12h51m49s-VIDEO-2026-11-02-00-45-49.mp4-.mp4`
(848x478, 120 fps, 26.5 s, 28 MB; an earlier export of the same recording,
`...12h29m35s...`, sits beside it unused), moved into `media/stages_source/`
under the published name because the script's table splits on spaces. It
was held landscape and carries no rotation matrix, so the `landscape` kind
publishes it the way round it is, at its own 848 px rather than scaled up,
and its poster is taken at 15 s (`poster=15`), when the robot is nearest the
camera. It is shown with controls and `preload="metadata"`, so it downloads
only when played.

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

## ALFRED page stills

`ALFRED/index.html` (the preprint page) uses video for the four figures in its
Reach section, the robot turntables, the usable-workspace orbits and the two
LiDAR visibility sweeps, described in the next section. Its stills, `img/alfred_*`, are the
manuscript's own figures rendered for the web by
`scripts/render_alfred_figures.py`, which takes the `Figures/` directory of the
arXiv source archive (arXiv:2610.01477; kept outside the repository) and writes
photographs and plots as progressive JPEGs and the two flat diagrams
(requirements matrix, network topology) as PNGs. The table at the top of the
script maps each source figure to its output file, so a changed figure is
re-rendered by running the script again. The four end-effector CAD renders
(`img/alfred_cad_*.jpg`, the paper's Figure 10) were dropped from the frame
section on 1 November 2026, along with their entries in the script, so that the
section stays on the strut frame; they are in git history. The page also reuses `front_view.jpeg`,
`top_down.jpeg`, `alfred2_front.jpg` and `alfred2_side.jpg` from the home and
ROWCAST pages.


## ALFRED page clips

The Reach section of `ALFRED/index.html` shows four figures made of GIF-style
loops: the robot descriptions as turntables, in place of the paper's rendered
stills (Figure 15); the usable-workspace bubble clouds, in place of the paper's
six-view plot (Figure 19); the frame-mounted LiDAR visibility as one six-panel
beam-by-beam sweep, in place of the paper's six-row polar grid (Figure 17);
and, not in the preprint, visibility across every usable arm pose as a
three-panel beam-by-beam sweep. The section sits second on the page, straight
after the overview. All play through the orbit script at the foot of the page,
shared with `ROWCAST/index.html`; a click or Enter on a tile pauses and
resumes it.

Their sources are not in this repo; `scripts/compress_alfred_clips.sh` encodes
them from the PhD tree, with `SRC_TURN=<dir>`, `SRC_REACH=<dir>`,
`SRC_VIS=<dir>` and `SRC_VIS_ALL=<dir>` to point it elsewhere:

- Turntables: `hunter_z1_description/scripts/render_robot_turntable.py`
  renders one 8 s orbit per URDF, arm in the zero posture, at 1080x1080 on the
  dark RViz background, into `Hunter/Hunter_Z1/shared_figures/robot_turntables/`.
  Published at 720 px, CRF 28, about 1 MB each.
- Usable workspace: `reachability_experiments/make_reachability_rotation_video.py`
  with `--shape-only` and a larger sphere scale renders one 6 s orbit per
  build at 600x600, into
  `Hunter/Hunter_Z1/reachability_downloads/full_grid_20260901T195332Z_full/figures/individual_shapes/larger_spheres/`.
  Published at the render's own 600 px, CRF 28, about 0.3 MB each.
- Visibility: `reachability_experiments/make_lidar_visibility_video.py`
  animates the saved zero- and drive-posture raycasts into one 12.8 s clip,
  `lidar_visibility_zero_drive.mp4`: six panels, builds across and posture
  down, stepping through the 32 beams together, lowest to highest, 0.4 s
  each, at 1680x1200 with the titles, one beam readout and a legend drawn in,
  into
  `Hunter/Hunter_Z1/reachability_downloads/lidar_fov_os1_32_fixed_zero_drive/videos_20261101/`.
  Published at the render's own size, CRF 24 because of the small text, about
  0.6 MB. It is one clip rather than the script's six per-panel clips (also in
  that folder, unused) so that the panels can never fall out of step: separate
  loops start as each scrolls into view and pause one at a time. The column
  titles say "Prototype v1" where the page says Prototype 1; that is baked
  into the render.
- All-pose visibility: computed after the October 2026 preprint, in the
  `lidar_all_reachable_20261101T182521Z` run under
  `Hunter/Hunter_Z1/reachability_downloads/`. `code/all_reachable_lidar_visibility.py`
  casts the 32-beam scan for every accepted pose of the
  `full_grid_20260912T080840Z_full` reachability sweep (8,524, 14,974 and
  16,494 poses, the Usable column of the page's table) and
  `code/plot_all_reachable_lidar_visibility_reverse_log_green.py`, run with
  `--colour-scale reverse-log --palette green --percent-only`, animates each
  cell's share of poses in which the ray is still free into
  `figures/free_percent_reverse_log_green.mp4`: three panels, builds across,
  32 beams at 0.4 s each, 12.8 s, 1800x648, with the titles, a beam readout
  and a colour bar that is logarithmic at the high end (ticks 0, 50, 80, 90,
  95, 99, 100 %) drawn in. Published at the render's own size, CRF 24, about
  0.4 MB. The same folder holds the figure as a PDF and PNG with three fixed
  beams; the page uses the clip. The render's middle title reads
  "ALFRED (hunter_z1)"; the publish step paints that title white and lays the
  word ALFRED back over it, re-centred, with coordinates measured on frame 0
  of the render (`ALL_POSES_TITLE_FIX` in the script; re-measure if the render
  changes). "Prototype v1" is left as rendered.

| Published file | Source | Build in the archive | Caption |
| --- | --- | --- | --- |
| `turntable_prototype_1.mp4` | `prototype_v1_turntable.mp4` | `prototype_v1` | Prototype 1 |
| `turntable_alfred.mp4` | `hunter_z1_turntable.mp4` | `hunter_z1` | ALFRED |
| `turntable_alfred_2_0.mp4` | `alfred_turntable.mp4` | `alfred` | ALFRED 2.0 |
| `reachability_prototype_1.mp4` | `prototype_1.mp4` | `prototype_v1` | Prototype 1 |
| `reachability_alfred.mp4` | `alfred.mp4` | `prototype_v2_hunter_z1_robot` | ALFRED |
| `reachability_alfred_2_0.mp4` | `alfred_2_0.mp4` | `prototype_v3_alfred_robot` | ALFRED 2.0 |
| `visibility_zero_drive.mp4` | `lidar_visibility_zero_drive.mp4` | all three | six-panel sweep, no per-tile caption |
| `visibility_all_poses.mp4` | `free_percent_reverse_log_green.mp4` | all three | three-panel sweep, no per-tile caption |

The turntable archive keeps the pre-publication build names, so there
`hunter_z1` is what the page calls ALFRED and `alfred` is ALFRED 2.0; the bubble
clouds were exported under the page's names and the visibility sweeps carry
their own panel titles. The bubble clouds are the same data as the
paper's six-view figure, cropped to the region any build reaches and drawn on
one size and colour scale (0 to 290 usable orientations), so the three stay
directly comparable; axes and labels are left off, so the page's captions
carry the build names and the scale. Posters are frame 0 at the published
size. The stills they replaced, `img/alfred_model_*.jpg`,
`img/alfred_reachability.jpg` and `img/alfred_lidar_visibility.jpg`, were
removed along with their entries in
`scripts/render_alfred_figures.py`; they are in git history if ever wanted
again.

Outside the Reach section, the strut-frame section closes with one phone
clip, `alfred_payload_study.mp4` (Christopher Quail's payload study in the
field: the robot drives a route with the weight cage fitted while weights
are added to it). It is published by `scripts/compress_stage_clips.sh` with
the ROWCAST stage clips and described in that section above.

The short table beneath the all-pose sweep, the arm's share of the blockage,
is page text rather than media. Its figures are the `accepted_target` block of
the same run's `arm_occlusion_link00/<model>/summary.json` files, rounded to
two decimals, written by `code/audit_arm_subtree_occlusion.py`: it reuses the
saved ray categories and counts, per pose, the rays the complete robot stops
that the robot without its `link00` arm subtree (the arm, its mounts, the
arm-mounted LiDAR and, on the ALFRED builds, the RGB-D cameras) does not. The
sibling `arm_occlusion/` folder is an earlier variant that keeps `link00` in
the fixed body; the page does not use it.
