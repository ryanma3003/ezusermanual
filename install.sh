#!/usr/bin/env bash
# Install the "user-manual" skill for AI coding agents.
#
#   ./install.sh                     detect installed agents, link the skill, install dependencies
#   ./install.sh --target all        install for every supported agent
#   ./install.sh --target claude,omp only these targets
#   ./install.sh --copy              copy instead of symlink (default: symlink, so `git pull` updates it)
#   ./install.sh --no-deps           skip Python/Chromium/LibreOffice setup
#   ./install.sh --uninstall         remove the skill from all targets and delete its Python environment
#
# Targets:
#   claude    ~/.claude/skills            Claude Code (OpenCode also reads it)
#   agents    ~/.agents/skills            Codex, Gemini CLI, Cursor, OpenCode, other Agent Skills tools
#   omp       ~/.omp/agent/skills         oh-my-pi
#   hermes    ~/.hermes/skills            Hermes Agent
#   opencode  ~/.config/opencode/skills   OpenCode (only needed if neither claude nor agents is installed)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="user-manual"
SRC="$REPO/skills/$NAME"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA="${USER_MANUAL_SKILL_HOME:-$HOME/.local/share/user-manual-skill}"
ALL_TARGETS="claude agents omp hermes opencode"

target_dir() {
  case "$1" in
    claude)   echo "$HOME/.claude/skills" ;;
    agents)   echo "$HOME/.agents/skills" ;;
    omp)      echo "$HOME/.omp/agent/skills" ;;
    hermes)   echo "$HOME/.hermes/skills" ;;
    opencode) echo "$CONFIG/opencode/skills" ;;
    *) echo "error: unknown target '$1' (choose from: $ALL_TARGETS, all)" >&2; exit 2 ;;
  esac
}

has() { command -v "$1" >/dev/null 2>&1; }

detect_targets() {
  local found=""
  { [ -d "$HOME/.claude" ] || has claude; } && found="$found claude"
  { [ -d "$HOME/.agents" ] || [ -d "$HOME/.codex" ] || [ -d "$HOME/.gemini" ] || [ -d "$HOME/.cursor" ] \
    || [ -d "$CONFIG/opencode" ] || has codex || has gemini || has cursor-agent || has opencode; } && found="$found agents"
  { [ -d "$HOME/.omp" ] || has omp; } && found="$found omp"
  { [ -d "$HOME/.hermes" ] || has hermes; } && found="$found hermes"
  echo "${found:- agents}"   # nothing detected: use the shared standard location
}

usage() { sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

targets="" copy=0 deps=1 uninstall=0
while [ $# -gt 0 ]; do
  case "$1" in
    --target|--targets) [ $# -ge 2 ] || usage 2; targets="$2"; shift ;;
    --target=*|--targets=*) targets="${1#*=}" ;;
    --copy) copy=1 ;;
    --no-deps) deps=0 ;;
    --uninstall) uninstall=1 ;;
    -h|--help) usage ;;
    *) echo "error: unknown option $1" >&2; usage 2 ;;
  esac
  shift
done

if [ -z "$targets" ]; then
  if [ $uninstall -eq 1 ]; then targets="$ALL_TARGETS"; else targets="$(detect_targets)"; fi
elif [ "$targets" = "all" ]; then
  targets="$ALL_TARGETS"
else
  targets="${targets//,/ }"
fi
for t in $targets; do target_dir "$t" >/dev/null; done   # validate names before touching anything

[ -f "$SRC/SKILL.md" ] || { echo "error: $SRC/SKILL.md not found; run this script from the cloned repository" >&2; exit 1; }

is_ours() {  # true if $1 is our symlink or a copy of this skill
  [ -L "$1" ] && return 0
  [ -f "$1/SKILL.md" ] && grep -q "^name: $NAME\$" "$1/SKILL.md"
}

if [ $uninstall -eq 1 ]; then
  for t in $targets; do
    dest="$(target_dir "$t")/$NAME"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
      if is_ours "$dest"; then rm -rf "$dest"; echo "removed  $t: $dest"; else echo "skipped  $t: $dest is not this skill"; fi
    fi
  done
  rm -rf "$DATA" && echo "removed  Python environment: $DATA"
  exit 0
fi

for t in $targets; do
  dir="$(target_dir "$t")"
  dest="$dir/$NAME"
  mkdir -p "$dir"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if ! is_ours "$dest"; then
      echo "skipped  $t: $dest exists and is a different skill" >&2
      continue
    fi
    rm -rf "$dest"
  fi
  if [ $copy -eq 1 ]; then
    cp -R "$SRC" "$dest"
    echo "copied   $t: $dest"
  else
    ln -s "$SRC" "$dest"
    echo "linked   $t: $dest -> $SRC"
  fi
done

if [ $deps -eq 1 ]; then
  echo "Installing dependencies (Python packages, Chromium, LibreOffice check)…"
  status=0
  "$SRC/scripts/setup.sh" || status=$?
  if [ $status -eq 3 ]; then
    echo "The skill is installed. Install LibreOffice (see above) before building a manual."
  elif [ $status -ne 0 ]; then
    exit $status
  fi
fi

echo
echo "Done. Restart your agent, then ask: \"Create a user manual for <your app>\"."
