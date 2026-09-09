#!/usr/bin/env bash
# Compress the full-resolution protocol captures into web-ready clips.
#
#   media/final_protocols/*.mp4   (~470 MB total, ~30 Mb/s)  -- gitignored source
#         |
#         v
#   media/protocol_*.mp4          (~20-40 MB total)          -- committed to git
#   media/protocol_*_poster.jpg   first-frame poster images
#
# Usage:
#   scripts/compress_videos.sh          # 1080x1920, CRF 26  (higher quality)
#   QUALITY=small scripts/compress_videos.sh   # 720x1280, CRF 28 (smallest)

set -euo pipefail
cd "$(dirname "$0")/.."

SRC=media/final_protocols
OUT=media

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

if [ "${QUALITY:-}" = "small" ]; then
  SCALE="720:-2"; CRF=28
else
  SCALE="1080:-2"; CRF=26
fi

# The source clips are 1080x1920 (9:16), which reads as very tall and thin on
# the page and is mostly empty canopy above / empty path below. Crop to 4:5.
#
# CROP_AR_W:CROP_AR_H  target aspect ratio (4:5)
# CROP_TOP             where the crop window starts, as a fraction of height
#
# Chosen by inspecting the first and last frame of all five clips. The framing
# follows the robot BODY, and the arm is allowed to leave the top of frame when
# the robot is closest at the end of a traverse. 0.15 centres the distant robot
# in the opening frame -- which is also what the poster thumbnail shows -- and
# trims the empty foreground path that dominated a lower crop window.
CROP_AR_W="${CROP_AR_W:-4}"
CROP_AR_H="${CROP_AR_H:-5}"
CROP_TOP="${CROP_TOP:-0.15}"
CROP="crop=iw:trunc(iw*${CROP_AR_H}/${CROP_AR_W}/2)*2:0:trunc(ih*${CROP_TOP}/2)*2"
VF="${CROP},scale=${SCALE}:flags=lanczos"

echo "Crop: ${CROP_AR_W}:${CROP_AR_H} starting ${CROP_TOP} down from the top"
echo "Encoding at width ${SCALE%%:*}px, CRF ${CRF}"
echo

# source stem -> published name used by ForestYear3D/index.html
MAP="
angle_scan_final:protocol_fixed
final_random:protocol_random
final_protocol_1:protocol_1
final_protocol_2:protocol_2
final_protocol_3:protocol_3
"

for pair in $MAP; do
  src_stem="${pair%%:*}"
  dst_stem="${pair##*:}"
  src="$SRC/$src_stem.mp4"
  dst="$OUT/$dst_stem.mp4"

  if [ ! -f "$src" ]; then
    echo "SKIP  $src (not found)"
    continue
  fi

  # -movflags +faststart puts the index at the front so the browser can
  # start playing before the whole file arrives.
  # -an drops audio: every <video> on the page is muted anyway.
  "$FFMPEG" -nostdin -y -loglevel error -i "$src" \
    -vf "$VF" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p \
    -crf "$CRF" -preset slow \
    -movflags +faststart -an \
    "$dst"

  "$FFMPEG" -nostdin -y -loglevel error -i "$src" \
    -vf "$VF" -frames:v 1 -q:v 4 \
    "$OUT/${dst_stem}_poster.jpg"

  before=$(du -m "$src" | cut -f1)
  after=$(du -m "$dst"  | cut -f1)
  printf "OK    %-28s %5s MB -> %4s MB\n" "$dst_stem.mp4" "$before" "$after"
done

echo
echo "Total published video size:"
du -ch "$OUT"/*.mp4 2>/dev/null | tail -1
