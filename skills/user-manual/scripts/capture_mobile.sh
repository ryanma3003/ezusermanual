#!/usr/bin/env bash
# Screenshot a mobile app for the user manual.
#
#   capture_mobile.sh android out.png [SERIAL]   Android phone (USB debugging on) or emulator, via adb
#   capture_mobile.sh ios out.png [UDID]         iOS Simulator via Xcode (default: the booted simulator)
#   capture_mobile.sh devices                    list connected Android devices and booted simulators
#
# Android navigation from the terminal: adb shell input tap X Y | adb shell input text "hello" | adb shell input keyevent BACK
set -euo pipefail

usage() { sed -n '2,9p' "$0" >&2; exit 2; }
[ $# -ge 1 ] || usage
platform="$1"

need() { command -v "$1" >/dev/null || { echo "error: '$1' not found. $2" >&2; exit 1; }; }

case "$platform" in
  devices)
    command -v adb >/dev/null && adb devices -l || echo "adb not installed"
    xcrun simctl help >/dev/null 2>&1 && xcrun simctl list devices booted || echo "iOS Simulator not available (install Xcode)"
    exit 0
    ;;
  android)
    [ $# -ge 2 ] || usage
    need adb "Install Android platform-tools (macOS: brew install --cask android-platform-tools)."
    out="$2"; serial="${3:-}"
    mkdir -p "$(dirname "$out")"
    if [ -n "$serial" ]; then adb -s "$serial" exec-out screencap -p >"$out"; else adb exec-out screencap -p >"$out"; fi
    ;;
  ios)
    [ $# -ge 2 ] || usage
    xcrun simctl help >/dev/null 2>&1 || { echo "error: iOS Simulator not available. Install Xcode and open the Simulator app first." >&2; exit 1; }
    out="$2"; udid="${3:-booted}"
    mkdir -p "$(dirname "$out")"
    xcrun simctl io "$udid" screenshot "$out" >/dev/null
    ;;
  *) usage ;;
esac

[ -s "$out" ] || { echo "error: no screenshot was saved; is the device connected / simulator booted? (run: $0 devices)" >&2; exit 1; }
echo "saved $out"
