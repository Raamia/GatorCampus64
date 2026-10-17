#!/bin/bash
# Copies every mod in ./mods into sm64coopdx's mods folder.
# Run this after editing a mod, then restart the game (or re-host) to load the changes.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/mods"
DEST="$HOME/Library/Application Support/sm64coopdx/mods"

mkdir -p "$DEST"
for mod in "$SRC"/*/; do
    name="$(basename "$mod")"
    # DynOS generates compiled level and actor files in the installed mod directory.
    # Keep them across source installs; they are ignored in git and absent from ./mods.
    rsync -a --delete --exclude='/levels/*.lvl' --exclude='/actors/*.bin' "$mod" "$DEST/$name/"
    echo "Installed $name"
done
