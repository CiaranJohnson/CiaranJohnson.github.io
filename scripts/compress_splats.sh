#!/usr/bin/env bash
# Compress the splat renders shown on ROWCAST/index.html into web-ready clips.
#
#   media/splats_source/*.mp4      full-resolution renders               -- gitignored source
#         |
#         v
#   media/<published>.mp4          720p flythroughs, 540 px orbits       -- committed to git
#   media/<published>_poster.jpg   poster frame at the clip's resolution
#
# Two kinds of clip, told apart by the published stem:
#   <scene>__flythrough   camera flythrough of a full scene, 16:9. Shown with
#                         controls, so it is only downloaded when played.
#   <scene>__<plant>      orbit round one cut-out plant, square. Shown as a
#                         silent autoplaying loop (GIF-style), so it is encoded
#                         small enough to load alongside the page.
#
# Usage:
#   scripts/compress_splats.sh              # every entry in MAP
#   scripts/compress_splats.sh biggreen     # only entries whose source or published stem contains "biggreen"
#
# Tunables (environment):
#   FLY_SCALE=1280:-2 FLY_CRF=27 ORBIT_SCALE=540:-2 ORBIT_CRF=28
#   FLY_POSTER_AT=0.6   the flythroughs fade in from black, so their poster is
#                       grabbed this many seconds in rather than at frame 0.

set -euo pipefail
cd "$(dirname "$0")/.."

SRC=media/splats_source
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

FLY_SCALE="${FLY_SCALE:-1280:-2}";    FLY_CRF="${FLY_CRF:-27}"
ORBIT_SCALE="${ORBIT_SCALE:-540:-2}"; ORBIT_CRF="${ORBIT_CRF:-28}"
FLY_POSTER_AT="${FLY_POSTER_AT:-0.6}"

# source stem -> published stem used by ROWCAST/index.html. Plant clips are
# published under the plant's name rather than the render's working name, so
# the <scene>__<plant> convention carries through to the page.
# Plants the page does not name yet keep their working names; give them a
# published name here (and in the page) once known.
MAP="
stationary_big_plants__flythrough:stationary_big_plants__flythrough
stationary_small_plants__flythrough:stationary_small_plants__flythrough
stationary_big_plants__canopyball:stationary_big_plants__indian_laurel_fig
stationary_big_plants__biggreen:stationary_big_plants__fiddle_leaf_fig
stationary_big_plants__red:stationary_big_plants__red
stationary_big_plants__white:stationary_big_plants__white
stationary_big_plants__greenwhite:stationary_big_plants__greenwhite
stationary_big_plants__mediumgreen:stationary_big_plants__mediumgreen
stationary_small_plants__small_1:stationary_small_plants__small_1
stationary_small_plants__small_2:stationary_small_plants__small_2
stationary_small_plants__small_3:stationary_small_plants__small_3
stationary_small_plants__small_4:stationary_small_plants__small_4
stationary_small_plants__small_5:stationary_small_plants__small_5
stationary_small_plants__small_6:stationary_small_plants__small_6
"

matched=0
for pair in $MAP; do
  src_stem="${pair%%:*}"
  dst_stem="${pair##*:}"
  src="$SRC/$src_stem.mp4"
  dst="$OUT/$dst_stem.mp4"
  poster="$OUT/${dst_stem}_poster.jpg"

  if [ -n "$ONLY" ] && [[ "$src_stem" != *"$ONLY"* && "$dst_stem" != *"$ONLY"* ]]; then continue; fi
  matched=$((matched + 1))
  if [ ! -f "$src" ]; then
    echo "SKIP  $src (not found)"
    continue
  fi

  # The page's layout depends on the published name, so that decides the kind.
  case "$dst_stem" in
    *__flythrough) kind=flythrough; scale="$FLY_SCALE";   crf="$FLY_CRF";   poster_at="$FLY_POSTER_AT" ;;
    *)             kind=orbit;      scale="$ORBIT_SCALE"; crf="$ORBIT_CRF"; poster_at=0 ;;
  esac
  vf="scale=${scale}:flags=lanczos"

  # -movflags +faststart puts the index at the front so playback can start
  # before the whole file arrives. -an drops audio: the renders are silent.
  "$FFMPEG" -nostdin -y -loglevel error -i "$src" \
    -vf "$vf" \
    -c:v libx264 -profile:v high -pix_fmt yuv420p \
    -crf "$crf" -preset slow \
    -movflags +faststart -an \
    "$dst"

  "$FFMPEG" -nostdin -y -loglevel error -ss "$poster_at" -i "$src" \
    -vf "$vf" -frames:v 1 -q:v 4 \
    "$poster"

  before=$(du -m "$src" | cut -f1)
  after=$(du -k "$dst" | cut -f1)
  printf "OK    %-48s %-10s %4s MB -> %6s KB   (crf %s, scale %s)\n" "$dst_stem.mp4" "$kind" "$before" "$after" "$crf" "$scale"
done

if [ -n "$ONLY" ] && [ "$matched" -eq 0 ]; then
  echo "WARN  nothing in MAP matches '$ONLY'" >&2
fi

# Renders dropped into the source folder that have no MAP entry yet.
for f in "$SRC"/*.mp4; do
  [ -e "$f" ] || continue
  stem=$(basename "$f" .mp4)
  case "$MAP" in
    *$'\n'"$stem:"*) ;;
    *) echo "UNMAPPED $f  (add a source:published line to MAP in $0)" ;;
  esac
done

# Published clips that no MAP entry produces any more, e.g. after a rename:
# they would otherwise stay in git and on the live site unnoticed.
for f in "$OUT"/stationary_*.mp4; do
  [ -e "$f" ] || continue
  stem=$(basename "$f" .mp4)
  case "$MAP" in
    *":$stem"$'\n'*) ;;
    *) echo "STALE    $f and ${f%.mp4}_poster.jpg  (no MAP entry publishes this name: git rm them and drop the <figure> from ROWCAST/index.html)" ;;
  esac
done

echo
echo "Total published video size:"
du -ch "$OUT"/*.mp4 2>/dev/null | tail -1
