#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/envs/rekv/bin/python}"
BASE_DIR="${BASE_DIR:-/home/vispec_repro}"

mkdir -p "$BASE_DIR/outputs/benchmark_dashboard"
mkdir -p "$BASE_DIR/fonts"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python not found at $PYTHON_BIN"
  echo "Set PYTHON_BIN=/path/to/python and rerun this script."
  exit 1
fi

"$PYTHON_BIN" -m pip install -q -r requirements.txt

echo "Environment ready."
echo "Python: $PYTHON_BIN"
echo "Output root: $BASE_DIR/outputs/benchmark_dashboard"
echo
echo "Optional Chinese font:"
echo "  If PNG labels show as boxes, upload simhei.ttf or msyh.ttc to $BASE_DIR/fonts/"
