#!/bin/bash
# Copies every mod in ./mods into sm64coopdx's mods folder.
# Run this after editing a mod, then restart the game (or re-host) to load the changes.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/mods"
DEST="$HOME/Library/Application Support/sm64coopdx/mods"

mkdir -p "$DEST"
for mod in "$SRC"/*/; do
    name="$(basename "$mod")"
    rsync -a --delete "$mod" "$DEST/$name/"
    echo "Installed $name"
done
