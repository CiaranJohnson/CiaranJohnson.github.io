# Video assets

Clips referenced by `ForestYear3D/index.html` live here. Each `<video>` block on
that page is commented out next to a dashed placeholder; to publish a clip, drop
the file in this folder, delete the placeholder `<div class="video-pending">`,
and uncomment the `<video>` element below it.

Filenames the page already expects:

| File | Section |
| --- | --- |
| `pointcloud_year.mp4` | Point clouds across the seasons — wide hero |
| `pointcloud_summer.mp4` / `pointcloud_autumn.mp4` / `pointcloud_winter.mp4` / `pointcloud_spring.mp4` | Point clouds — per-season grid |
| `field_year.mp4` | The robot in the field — wide hero |
| `field_summer.mp4` / `field_autumn.mp4` / `field_winter.mp4` / `field_spring.mp4` | Field footage — per-season grid |
| `protocols_overview.mp4` | Robot protocols — wide hero |
| `protocol_fixed.mp4` / `protocol_random.mp4` / `protocol_1.mp4` / `protocol_2.mp4` / `protocol_3.mp4` | Robot protocols — per-strategy grid |

Optional poster frames use the same stem with a `_poster.jpg` suffix.

Notes:
- H.264 MP4 is the safe format for GitHub Pages; add a WebM `<source>` first if
  you want it.
- GitHub blocks pushes over 100 MB per file and warns above 50 MB. Keep clips
  short and compressed, or host them externally and swap the `<video>` for an
  `<iframe>` — `.video-slot iframe` is already styled for that.
