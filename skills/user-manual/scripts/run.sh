#!/usr/bin/env bash
# Run a skill Python tool inside the skill's environment, running setup first if needed.
# Usage: run.sh <tool.py> [args...]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${USER_MANUAL_SKILL_HOME:-$HOME/.local/share/user-manual-skill}"

if [ $# -lt 1 ]; then
  echo "usage: $0 <tool.py> [args...]   tools: build_manual.py capture_web.py annotate.py" >&2
  exit 2
fi

if ! cmp -s "$HERE/requirements.txt" "$DATA/requirements.installed" 2>/dev/null; then
  "$HERE/setup.sh" >&2 || [ $? -eq 3 ]   # exit 3 = only LibreOffice missing; capture tools still work
fi

VPY="$DATA/venv/bin/python"
[ -x "$VPY" ] || VPY="$DATA/venv/Scripts/python.exe"
tool="$1"; shift
exec "$VPY" "$HERE/$tool" "$@"
