#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  STEM::EXTRACT  ·  Linux / macOS launcher
# ─────────────────────────────────────────────────────────

set -e

PORT=${1:-5000}
VENV_DIR="venv"

echo ""
echo "  ╔══ STEM::EXTRACT ══════════════════════════════╗"
echo "  ║   Audio Source Separation — Demucs Engine     ║"
echo "  ╚════════════════════════════════════════════════╝"
echo ""

# Create virtualenv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "  → Creating virtual environment…"
  python3 -m venv "$VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

# Install / upgrade dependencies
echo "  → Checking dependencies…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
  echo ""
  echo "  ⚠  WARNING: ffmpeg not found."
  echo "     Install with:  brew install ffmpeg   (macOS)"
  echo "                    sudo apt install ffmpeg  (Debian/Ubuntu)"
  echo ""
fi

echo ""
echo "  → Starting server on http://localhost:$PORT"
echo "  → Press Ctrl+C to stop"
echo ""

python app.py "$PORT"
