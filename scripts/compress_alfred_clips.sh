#!/usr/bin/env bash
# Publish the clips in the Reach section of ALFRED/index.html: the robot
# turntables, the usable-workspace (reachability) orbits and the LiDAR
# visibility sweeps.
#
#   $SRC_TURN/<build>_turntable.mp4     1080 px turntable renders      -- PhD tree, not this repo
#   $SRC_REACH/<build>.mp4              600 px bubble-cloud orbits     -- PhD tree, not this repo
#   $SRC_VIS/lidar_visibility_zero_drive.mp4  1680x1200 six-panel sweep  -- PhD tree, not this repo
#         |
#         v
#   media/turntable_<build>.mp4             720 px square loops   -- committed to git
#   media/reachability_<build>.mp4          600 px square loops   -- committed to git
#   media/visibility_zero_drive.mp4         1680x1200 loop        -- committed to git
#   media/<published>_poster.jpg            frame 0 at the published size
#
# Sources:
#   turntables    hunter_z1_description/scripts/render_robot_turntable.py: one
#                 8 s orbit per URDF, arm in the zero posture, 1080x1080 at
#                 30 fps on the dark RViz background.
#   reachability  reachability_experiments/make_reachability_rotation_video.py
#                 with --shape-only and a larger sphere scale: one 6 s orbit per
#                 build, 600x600.
#   visibility    reachability_experiments/make_lidar_visibility_video.py: one
#                 12.8 s clip with six panels (builds across, arm at zero and
#                 drive posture down) that step through the 32 beams together,
#                 lowest to highest, 0.4 s each, 1680x1200, titles, one beam
#                 readout and a legend drawn in. One clip rather than the
#                 script's per-panel ones so the panels can never fall out of
#                 step with each other.
# All are shown GIF-style (silent, looping, playing while on screen), so they
# are encoded small. Turntables are scaled to 720 px, which is what a tile
# three across on the 1400 px column needs on a 2x display; the other two kinds
# are kept at their own size. CRF 28 takes about 80% off the turntables and 40%
# off the bubble clouds at no visible cost; the visibility plot carries small
# text, so it gets CRF 24.
#
# Usage:
#   scripts/compress_alfred_clips.sh               # all seven
#   scripts/compress_alfred_clips.sh visibility    # only published stems containing "visibility"
#   scripts/compress_alfred_clips.sh alfred_2      # every ALFRED 2.0 clip
#
# Tunables (environment):
#   SRC_TURN=<dir>  SRC_REACH=<dir>  SRC_VIS=<dir>  CRF=28  VIS_CRF=24  TURN_SCALE=720

set -euo pipefail
cd "$(dirname "$0")/.."

PHD="$HOME/Coding/PhD/Hunter/Hunter_Z1"
SRC_TURN="${SRC_TURN:-$PHD/shared_figures/robot_turntables}"
SRC_REACH="${SRC_REACH:-$PHD/reachability_downloads/full_grid_20260901T195332Z_full/figures/individual_shapes/larger_spheres}"
SRC_VIS="${SRC_VIS:-$PHD/reachability_downloads/lidar_fov_os1_32_fixed_zero_drive/videos_20261101}"
OUT=media
CRF="${CRF:-28}"
VIS_CRF="${VIS_CRF:-24}"
TURN_SCALE="${TURN_SCALE:-720}"
ONLY="${1:-}"

# Prefer a system ffmpeg; otherwise fall back to the binary that the
# imageio-ffmpeg PyPI package ships (installs without root).
if command -v ffmpeg >/dev/null 2>&1; then
  FFMPEG=ffmpeg
elif FFMPEG=$(python3 -c "import imageio_ffmpeg,sys; sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())" 2>/dev/null) \
     && [ -x "$FFMPEG" ]; then
  :
else
  echo "ERROR: no ffmpeg found. Install it with either:" >&2
  echo "  sudo apt update && sudo apt install -y ffmpeg" >&2
  echo "  pip install --user imageio-ffmpeg" >&2
  exit 1
fi
echo "Using ffmpeg: $FFMPEG"

# kind:source stem:published stem. The turntable archive keeps the
# pre-publication build names (prototype_v1 is Prototype 1, hunter_z1 is
# ALFRED, alfred is ALFRED 2.0); the bubble clouds were exported under the
# page's names, and the visibility sweep carries its own panel titles.
MAP="
turntable:prototype_v1_turntable:turntable_prototype_1
turntable:hunter_z1_turntable:turntable_alfred
turntable:alfred_turntable:turntable_alfred_2_0
reach:prototype_1:reachability_prototype_1
reach:alfred:reachability_alfred
reach:alfred_2_0:reachability_alfred_2_0
visibility:lidar_visibility_zero_drive:visibility_zero_drive
"

matched=0
for entry in $MAP; do
  IFS=: read -r kind src_stem dst_stem <<< "$entry"
  case "$kind" in
    turntable)  src="$SRC_TURN/$src_stem.mp4";  vf=(-vf "scale=${TURN_SCALE}:-2:flags=lanczos"); crf="$CRF" ;;
    reach)      src="$SRC_REACH/$src_stem.mp4"; vf=(); crf="$CRF" ;;
    visibility) src="$SRC_VIS/$src_stem.mp4";   vf=(); crf="$VIS_CRF" ;;
  esac
  dst="$OUT/$dst_stem.mp4"
  poster="$OUT/${dst_stem}_poster.jpg"

  if [ -n "$ONLY" ] && [[ "$src_stem" != *"$ONLY"* && "$dst_stem" != *"$ONLY"* ]]; then continue; fi
  matched=$((matched + 1))
  if [ ! -f "$src" ]; then
    echo "SKIP  $src (not found)"
    continue
  fi

  # -movflags +faststart puts the index at the front so playback can start
  # before the whole file arrives; -an drops any audio track (they are silent).
  "$FFMPEG" -nostdin -y -loglevel error -i "$src" \
    "${vf[@]}" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p \
    -crf "$crf" -preset slow \
    -movflags +faststart -an \
    "$dst"

  "$FFMPEG" -nostdin -y -loglevel error -i "$src" \
    "${vf[@]}" -frames:v 1 -q:v 4 \
    "$poster"

  before=$(du -k "$src" | cut -f1)
  after=$(du -k "$dst" | cut -f1)
  printf "OK    %-36s %-11s %5s KB -> %5s KB   (crf %s)\n" "$dst_stem.mp4" "$kind" "$before" "$after" "$crf"
done

if [ -n "$ONLY" ] && [ "$matched" -eq 0 ]; then
  echo "WARN  nothing in MAP matches '$ONLY'" >&2
fi

echo
echo "Published ALFRED clips:"
du -ch "$OUT"/turntable_*.mp4 "$OUT"/reachability_*.mp4 "$OUT"/visibility_*.mp4 2>/dev/null | tail -1
