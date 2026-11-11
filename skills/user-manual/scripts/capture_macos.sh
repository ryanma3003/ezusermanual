#!/usr/bin/env bash
# Screenshot a macOS desktop application for the user manual.
#
#   capture_macos.sh window "App Name" out.png   bring the app to the front, capture its front window
#   capture_macos.sh pick out.png                the user clicks the window to capture
#   capture_macos.sh screen out.png              the whole main screen
#
# Needs: Screen Recording permission for your terminal app (System Settings > Privacy & Security),
# plus Accessibility permission for "window" mode (it reads the window position via System Events).
set -euo pipefail

usage() { sed -n '2,9p' "$0" >&2; exit 2; }
[ "$(uname)" = "Darwin" ] || { echo "error: macOS only" >&2; exit 1; }
[ $# -ge 2 ] || usage
no_permission() {
  echo "error: no screenshot was saved. Give your terminal app Screen Recording permission" >&2
  echo "(System Settings > Privacy & Security > Screen Recording), then restart the terminal." >&2
  exit 1
}
mode="$1"; shift

case "$mode" in
  window)
    [ $# -eq 2 ] || usage
    app="$1"; out="$2"
    osascript -e "tell application \"$app\" to activate" >/dev/null
    sleep 1
    if ! bounds="$(osascript -e 'tell application "System Events" to tell (first process whose frontmost is true) to get {position, size} of front window' 2>&1)"; then
      echo "error: cannot read the window position: $bounds" >&2
      echo "Give your terminal app Accessibility permission (System Settings > Privacy & Security > Accessibility)." >&2
      exit 1
    fi
    IFS=', ' read -r x y w h <<<"$bounds"
    mkdir -p "$(dirname "$out")"
    screencapture -x -o -R"$x,$y,$w,$h" "$out" || no_permission
    ;;
  pick)
    out="$1"; mkdir -p "$(dirname "$out")"
    echo "Click the window you want to capture." >&2
    screencapture -x -o -w "$out" || no_permission
    ;;
  screen)
    out="$1"; mkdir -p "$(dirname "$out")"
    screencapture -x -m "$out" || no_permission
    ;;
  *) usage ;;
esac

[ -s "$out" ] || no_permission
echo "saved $out"
