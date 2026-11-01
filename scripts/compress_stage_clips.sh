#!/usr/bin/env bash
# Compress the workflow-stage clips shown on ROWCAST/index.html into web-ready clips.
#
#   media/stages_source/*.mp4        phone footage and screen recordings   -- gitignored source
#         |
#         v
#   media/rowcast_<stage>*.mp4       720 px wide, 30 fps, silent           -- committed to git
#   media/rowcast_<stage>*_poster.jpg poster frame at the clip's resolution
#
# Two kinds of clip, set per entry in CLIPS below:
#   phone    portrait phone footage of the robot, stored landscape
#            (1920x1080) the way the phone's sensor saw it. With top=<fraction>
#            the clip is cropped to 4:5 like the protocol clips on the
#            ForestYear3D page (the full frame is mostly sky and gravel), the
#            window starting that fraction of the way down. With full the
#            whole 9:16 frame is kept: the Execute clips sit in a row beside
#            the YouTube Short, which is 9:16, so they match it.
#   screen   landscape screen recordings (RViz). crop= cuts the recording down
#            to the live part of the window, as 16:9.
#
# Orientation. The phone clips were re-encoded with VLC, which did not keep
# the phone's rotation flag intact: on three of them it wrote a track matrix
# that is a transpose (a quarter turn plus a mirror) and on fixed.mp4 it wrote
# none. ffmpeg's autorotate follows the matrix literally, so it mirrored those
# three. The script therefore tells ffmpeg the file's rotation is zero
# (-display_rotation 0, which also stops the matrix being copied into the
# output, as -noautorotate would do) and turns each clip explicitly with
# turn=cw, a quarter turn clockwise, which is what every clip from this phone
# needs; a mirror option exists but none of the clips uses it. Checked against
# the field by the author: the robot drives away from the camera with the row
# of pots on its right in both Execute clips.
#
# Usage:
#   scripts/compress_stage_clips.sh            # every entry in CLIPS
#   scripts/compress_stage_clips.sh scout      # only entries whose source or published stem contains "scout"
#
# Tunables (environment):
#   PHONE_SCALE=720:-2 PHONE_CRF=26 SCREEN_SCALE=1280:-2 SCREEN_CRF=26 FPS=30 POSTER_AT=0.5

set -euo pipefail
cd "$(dirname "$0")/.."

SRC=media/stages_source
OUT=media
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

PHONE_SCALE="${PHONE_SCALE:-720:-2}";   PHONE_CRF="${PHONE_CRF:-26}"
SCREEN_SCALE="${SCREEN_SCALE:-1280:-2}"; SCREEN_CRF="${SCREEN_CRF:-26}"
FPS="${FPS:-30}"
POSTER_AT="${POSTER_AT:-0.5}"

# source stem | published stem | kind | options (comma-separated)
#   phone:  turn=cw|ccw   mirror   top=<fraction> | full
#   screen: crop=w:h:x:y
CLIPS="
comissioning_field  rowcast_commission_field  phone   turn=cw,top=0.15
comissioning_rviz   rowcast_commission_map    screen  crop=1484:835:0:52
scout               rowcast_scout             phone   turn=cw,top=0.15
planning            rowcast_plan              screen  crop=1704:958:108:0
fixed               rowcast_execute_fixed     phone   turn=cw,full
random              rowcast_execute_random    phone   turn=cw,full
"

matched=0
while read -r src_stem dst_stem kind opts; do
  [ -n "$src_stem" ] || continue
  src="$SRC/$src_stem.mp4"
  dst="$OUT/$dst_stem.mp4"
  poster="$OUT/${dst_stem}_poster.jpg"

  if [ -n "$ONLY" ] && [[ "$src_stem" != *"$ONLY"* && "$dst_stem" != *"$ONLY"* ]]; then continue; fi
  matched=$((matched + 1))
  if [ ! -f "$src" ]; then
    echo "SKIP  $src (not found)"
    continue
  fi

  turn=""; mirror=""; top=""; full=""; crop=""
  IFS=, read -ra kv <<< "$opts"
  for o in "${kv[@]}"; do
    case "$o" in
      turn=*)   turn="${o#turn=}" ;;
      mirror)   mirror=1 ;;
      top=*)    top="${o#top=}" ;;
      full)     full=1 ;;
      crop=*)   crop="${o#crop=}" ;;
      *) echo "ERROR: unknown option '$o' for $src_stem" >&2; exit 1 ;;
    esac
  done

  filters=()
  case "$kind" in
    phone)
      case "$turn" in
        cw)  filters+=("transpose=1") ;;
        ccw) filters+=("transpose=2") ;;
        "")  ;;
        *) echo "ERROR: turn must be cw or ccw ($src_stem)" >&2; exit 1 ;;
      esac
      [ -n "$mirror" ] && filters+=("hflip")
      if [ -z "$full" ]; then
        filters+=("crop=iw:trunc(iw*5/4/2)*2:0:trunc(ih*${top:-0.15}/2)*2")
      fi
      filters+=("scale=${PHONE_SCALE}:flags=lanczos")
      crf="$PHONE_CRF" ;;
    screen)
      [ -n "$crop" ] && filters+=("crop=$crop")
      filters+=("scale=${SCREEN_SCALE}:flags=lanczos")
      crf="$SCREEN_CRF" ;;
    *) echo "ERROR: unknown kind '$kind' for $src_stem" >&2; exit 1 ;;
  esac
  vf=$(IFS=,; echo "${filters[*]}")

  # -display_rotation 0: the orientation comes from CLIPS, not the file (see above).
  # -movflags +faststart puts the index at the front so playback can start
  # before the whole file arrives. -an drops audio: every <video> on the page
  # is muted. fps= first, so the sources' 45-240 fps are not filtered in full.
  "$FFMPEG" -nostdin -y -loglevel error -display_rotation 0 -i "$src" \
    -vf "fps=${FPS},${vf}" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p \
    -crf "$crf" -preset slow \
    -movflags +faststart -an \
    "$dst"

  "$FFMPEG" -nostdin -y -loglevel error -display_rotation 0 -ss "$POSTER_AT" -i "$src" \
    -vf "$vf" -frames:v 1 -q:v 4 \
    "$poster"

  before=$(du -m "$src" | cut -f1)
  after=$(du -k "$dst" | cut -f1)
  printf "OK    %-30s %-7s %4s MB -> %6s KB   (crf %s, vf %s)\n" "$dst_stem.mp4" "$kind" "$before" "$after" "$crf" "$vf"
done <<< "$CLIPS"

if [ -n "$ONLY" ] && [ "$matched" -eq 0 ]; then
  echo "WARN  nothing in CLIPS matches '$ONLY'" >&2
fi

# Clips dropped into the source folder that have no CLIPS entry yet.
for f in "$SRC"/*.mp4; do
  [ -e "$f" ] || continue
  stem=$(basename "$f" .mp4)
  case "$CLIPS" in
    *$'\n'"$stem "*) ;;
    *) echo "UNMAPPED $f  (add a line to CLIPS in $0)" ;;
  esac
done

echo
echo "Total published video size:"
du -ch "$OUT"/*.mp4 2>/dev/null | tail -1
