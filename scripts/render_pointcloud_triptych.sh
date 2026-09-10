#!/usr/bin/env bash
# Thin wrapper: run the triptych renderer in the conda env that has open3d.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${FY3D_PYTHON:-/home/robot/miniconda3/envs/forestyear3d/bin/python}"
[ -x "$PY" ] || { echo "no python at $PY (set FY3D_PYTHON)" >&2; exit 1; }
exec "$PY" scripts/render_pointcloud_triptych.py "$@"
