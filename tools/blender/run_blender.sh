#!/bin/sh
# Run a headless Blender script with the project's Fast64, retrying when Blender
# crashes (exit code >= 128, e.g. 139 = SIGSEGV). Fast64's upgrade of the
# template's materials (setup_fast64 -> upgrade_f3d_version_all_meshes) segfaults
# intermittently (about 1 in 14 loads); a plain re-run succeeds. Script errors
# (exit code 1 from --python-exit-code) are NOT retried.
#
# Usage: tools/blender/run_blender.sh [<file.blend>] <script.py> [-- args...]
#   e.g. tools/blender/run_blender.sh tools/blender/build_character.py -- daniel
# Env: BLENDER (path to the Blender binary), SGL_RETRIES (default 3).
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
BLENDER="${BLENDER:-$(command -v blender || printf '%s' /Applications/Blender.app/Contents/MacOS/Blender)}"
TEMPLATE="$ROOT/tools/vendor/template/Mario Coop Model Template.blend"
case "$1" in
  *.blend) BLEND="$1"; shift ;;
  *) BLEND="$TEMPLATE" ;;
esac
SCRIPT="$1"; shift
tries="${SGL_RETRIES:-3}"
n=1
while :; do
  BLENDER_USER_SCRIPTS="$ROOT/tools/blender-scripts" "$BLENDER" --background --factory-startup "$BLEND" \
    --python-exit-code 1 --python "$SCRIPT" "$@"
  rc=$?
  if [ "$rc" -lt 128 ] || [ "$n" -ge "$tries" ]; then
    exit "$rc"
  fi
  echo "run_blender.sh: Blender crashed (exit $rc), retrying ($n/$tries)" >&2
  n=$((n + 1))
done
