#!/bin/sh
# Provision sgl-gpu (Ubuntu 24.04 + NVIDIA): the character pipeline (Blender 4.5.3 LTS, Fast64-Gart,
# the coopdx character template) and a copy of this repo in /opt/sgl64.
# Run from the repo root on your machine: server/deploy/provision_gpu.sh root@<gpu host>
# Idempotent. Pins match the Mac that built the 10 friends (Raami).
set -eu
HOST="${1:?usage: server/deploy/provision_gpu.sh root@<gpu host>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

FAST64_URL="https://github.com/ManIsCat2/Fast64-Gart"
FAST64_SHA="9384477f2ccdc8b6e05a96b52241f98808feb90b"
TEMPLATE_URL="https://github.com/coop-deluxe/character-template"
TEMPLATE_SHA="58149f1b58cef75c7f90c19f6d3cadb66bd5b915"
BLENDER_VERSION="4.5.3"
BLENDER_URL="https://download.blender.org/release/Blender4.5/blender-${BLENDER_VERSION}-linux-x64.tar.xz"

ssh "$HOST" 'export DEBIAN_FRONTEND=noninteractive; apt-get update -qq &&
    apt-get install -y -qq git rsync xz-utils libxi6 libxxf86vm1 libxfixes3 libxrender1 \
        libxkbcommon0 libsm6 libgl1 libegl1 >/dev/null'

# The repo (vendor deps and build outputs are recreated on the host)
rsync -az --delete --exclude .git --exclude 'tools/.venv' --exclude 'tools/vendor' \
    --exclude 'tools/blender-scripts' --exclude 'art/*/build/*.blend' --exclude 'data/uf/tiles' \
    --exclude '*.pdf' "$ROOT/" "$HOST:/opt/sgl64/"

ssh "$HOST" "FAST64_URL=$FAST64_URL FAST64_SHA=$FAST64_SHA TEMPLATE_URL=$TEMPLATE_URL \
    TEMPLATE_SHA=$TEMPLATE_SHA BLENDER_VERSION=$BLENDER_VERSION BLENDER_URL=$BLENDER_URL sh -s" <<'EOF'
set -eu
cd /opt/sgl64

# fetch <dir> <url> <sha>: a shallow checkout of exactly one commit
fetch() {
    if [ "$(git -C "$1" rev-parse HEAD 2>/dev/null)" = "$3" ]; then echo "$1 @ $3 (already)"; return; fi
    rm -rf "$1"; mkdir -p "$1"
    git -C "$1" init -q
    git -C "$1" remote add origin "$2"
    git -C "$1" fetch -q --depth 1 origin "$3"
    git -C "$1" checkout -q FETCH_HEAD
    echo "$1 @ $(git -C "$1" rev-parse HEAD)"
}
fetch tools/blender-scripts/addons/fast64 "$FAST64_URL" "$FAST64_SHA"
fetch tools/vendor/character-template "$TEMPLATE_URL" "$TEMPLATE_SHA"

# sgl_util.TEMPLATE_BLEND expects tools/vendor/template/Mario Coop Model Template.blend
mkdir -p tools/vendor/template
BLEND="$(find tools/vendor/character-template -name '*.blend' | grep -i mario | head -1)"
[ -n "$BLEND" ] || { echo "no Mario .blend in character-template" >&2; exit 1; }
ln -sfn "$(pwd)/$BLEND" "tools/vendor/template/Mario Coop Model Template.blend"
echo "template -> $BLEND"
# the worker container (uid 1001) mounts the repo read-only but Fast64 writes into its add-on folder
chown -R 1001:1001 tools/blender-scripts

# Blender
DEST="/opt/blender-$BLENDER_VERSION"
if [ ! -x "$DEST/blender" ]; then
    curl -sSL "$BLENDER_URL" | tar -xJ -C /opt
    mv "/opt/blender-$BLENDER_VERSION-linux-x64" "$DEST"
fi
ln -sfn "$DEST/blender" /usr/local/bin/blender
blender --version | head -1
EOF

echo "provision_gpu: done. Test build:"
echo "  ssh $HOST 'cd /opt/sgl64 && BLENDER=/usr/local/bin/blender tools/blender/run_blender.sh tools/blender/build_character.py -- daniel --build-dir /tmp/sglbuild/daniel --actors-dir /tmp/sglbuild/actors'"
