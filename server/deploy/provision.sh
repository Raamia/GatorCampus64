#!/bin/sh
# Provision sgl-host (Debian 13 / Ubuntu 24.04): coopdx v1.5.1 headless + the sgl64 mod.
# Run from the repo root on your machine:  server/deploy/provision.sh root@<host>
# Idempotent. The ROM is NOT handled here: copy your own US dump by hand (see docs/web_platform_spec.md §6.1):
#   scp baserom.us.z64 root@<host>:/srv/sgl/ && ssh root@<host> 'chown sgl:sgl /srv/sgl/*.z64; chmod 600 /srv/sgl/*.z64'
set -eu
HOST="${1:?usage: server/deploy/provision.sh root@<host>}"
COOPDX_VERSION="v1.5.1"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

ssh "$HOST" "COOPDX_VERSION=$COOPDX_VERSION sh -s" <<'EOF'
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq unzip curl ca-certificates rsync python3 python3-venv \
    libsdl2-2.0-0 libgl1 libglew2.2 >/dev/null
id sgl >/dev/null 2>&1 || useradd --system --create-home --home-dir /srv/sgl --shell /usr/sbin/nologin sgl
mkdir -p /opt/sm64coopdx /srv/sgl/mods
cd /opt/sm64coopdx
if [ ! -f ".version-$COOPDX_VERSION" ]; then
    curl -sSL -o sm64coopdx_Linux.zip \
        "https://github.com/coop-deluxe/sm64coopdx/releases/download/$COOPDX_VERSION/sm64coopdx_Linux.zip"
    unzip -oq sm64coopdx_Linux.zip
    touch ".version-$COOPDX_VERSION"
fi
EOF

# The mod (DynOS-compiled .bin/.lvl are rebuilt by the game on first load)
rsync -az --delete --exclude '*.bin' --exclude '*.lvl' "$ROOT/mods/sgl64/" "$HOST:/srv/sgl/mods/sgl64/"
scp -q "$HERE/sgl-game.service" "$HOST:/etc/systemd/system/sgl-game.service"
ssh "$HOST" 'chown -R sgl:sgl /srv/sgl && systemctl daemon-reload &&
    if command -v ufw >/dev/null; then ufw allow 7777/udp; ufw allow 80/tcp; ufw allow 443/tcp; fi >/dev/null &&
    if ls /srv/sgl/*.z64 >/dev/null 2>&1; then systemctl enable --now sgl-game && systemctl restart sgl-game;
    else echo "provision: no ROM in /srv/sgl yet, sgl-game not started"; fi'
