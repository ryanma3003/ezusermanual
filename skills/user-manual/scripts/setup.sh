#!/usr/bin/env bash
# One-time setup for the user-manual skill. Safe to re-run.
# Installs Python packages + Chromium into a private environment and checks for LibreOffice.
# Environment location: $USER_MANUAL_SKILL_HOME (default ~/.local/share/user-manual-skill)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${USER_MANUAL_SKILL_HOME:-$HOME/.local/share/user-manual-skill}"
VENV="$DATA/venv"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  echo "error: Python 3.9 or newer is required (https://www.python.org/downloads/)" >&2
  exit 1
fi

mkdir -p "$DATA"
if [ ! -x "$VENV/bin/python" ] && [ ! -x "$VENV/Scripts/python.exe" ]; then
  echo "Creating Python environment in $VENV"
  "$PY" -m venv "$VENV"
fi
VPY="$VENV/bin/python"
[ -x "$VPY" ] || VPY="$VENV/Scripts/python.exe"

echo "Installing Python packages"
"$VPY" -m pip install --quiet --disable-pip-version-check --upgrade pip
"$VPY" -m pip install --quiet --disable-pip-version-check -r "$HERE/requirements.txt"

echo "Installing Chromium for web screenshots"
"$VPY" -m playwright install chromium
cp "$HERE/requirements.txt" "$DATA/requirements.installed"

find_soffice() {
  for c in "${SOFFICE:-}" "$(command -v soffice || true)" "$(command -v libreoffice || true)" \
           "/Applications/LibreOffice.app/Contents/MacOS/soffice" \
           "/c/Program Files/LibreOffice/program/soffice.exe"; do
    if [ -n "$c" ] && [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

if SOFFICE_BIN="$(find_soffice)"; then
  echo "LibreOffice: $("$SOFFICE_BIN" --version 2>/dev/null | head -n 1)"
  echo "Setup complete."
else
  cat >&2 <<'EOF'
LibreOffice is missing. It is needed to create page numbers and the PDF. Install it with one of:
  macOS:          brew install --cask libreoffice
  Ubuntu/Debian:  sudo apt-get install -y libreoffice-writer
  Fedora:         sudo dnf install -y libreoffice-writer
  Windows:        winget install TheDocumentFoundation.LibreOffice
Or point to an existing install: export SOFFICE=/path/to/soffice
EOF
  exit 3
fi
