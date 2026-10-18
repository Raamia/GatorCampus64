# Production operations

GitHub `main` is the source of truth. Production deployment runs from the operator's local machine; credentials live in the ignored root `.env` and `/etc/sgl` on the hosts. Never deploy an uncommitted working tree. Fetch and reconcile `origin/main` before every release; do not force-push it.

## Deployment inventory

- Game host: `sgl-host`, bridge in `/opt/sgl/server/bridge`, game data in `/srv/sgl`, API in `/opt/sgl-api`.
- GPU host: `sgl-gpu`, source in `/opt/sgl64`, worker Compose project in `/opt/sgl64/server/worker`.
- DeepSpace: `companion/app`, owned app `gator-field-board-mlh`, https://gator-field-board-mlh.app.space. Deploy with the DeepSpace CLI from this directory; do not use DeepSpace source push.
- API binds only to `127.0.0.1:8000`. Bridge uses this local endpoint. Public HTTPS routing is not yet configured.

## Before deploying

1. Record the exact Git commit, check the working tree is clean, and run relevant checks. Bridge: `python -m pytest -q server/bridge/tests`; game: `tools/luatest/run.sh`; dashboard: `npm run validate` and `npm run build` in `companion/app`.
2. Back up configuration, previous source, service units, and game saves/state. Take a database backup before schema changes. Existing bootstrap backup: `/root/sgl-backups/20261017T132054Z` on the game host; it contains configuration, game service units and `/srv/sgl`, not all application source or the database.
3. Prepare the new release from `git archive <commit>` into a staging directory. Transfer only tracked artifacts. Do not sync the whole working tree.
4. Check for connected players before restarting the bridge; stopping it also stops the game.

## Files to preserve

Never apply unrestricted `rsync --delete` to a deployed application directory. Explicitly preserve `.venv/`, `.env`, generated files, and toolchain/vendor directories. Keep `/etc/sgl`, `/srv/sgl/sav`, `/srv/sgl/bridge`, ROM files, deployed `actors/guest_*`, `textures/sgl_portrait_guest_*`, and the deployed `guests.lua` outside source replacement. `mods/sgl64` in the release is the pristine placeholder source; it is distinct from the installed, mutable mod.

Create/install dependencies before service activation. The API requires its `sgl-api` system account. Its unit sets `HOME=/tmp` to avoid libpq probing protected home directories. Run schema application once, then keep `SGL_APPLY_SCHEMA=0` for normal multi-worker startup.

## Verification and rollback

After activation, record commit and timestamp on each host, compare deployed source hashes, check service state, and inspect fresh logs. API: `/healthz` returns 200; anonymous `/me` returns 401; a bridge token can access `/deploys/pending` but cannot access user-only `/me`. Game: bridge stays active and UDP 7777 is listening. GPU: inspect Compose state, fresh worker/VLM logs, and VRAM usage; a running worker alone does not prove image inference works.

For rollback, stop the affected service, restore the previous source and matching dependencies/configuration, restore the previous service definition if changed, and start/verify again. Do not roll back game saves or database contents automatically. Database migration rollback is a separate, reviewed recovery operation.

## Remaining acceptance work

Public API TLS/routing; website upload/generation UI integration; Auth0 browser login; interactive in-game login; a consented photo generation through preview and guest deployment; verified run ingestion into DeepSpace. Teammates will perform interactive play tests. DeepSpace login and Auth0/Gator Pass are currently separate identity systems; account linking is not yet implemented.
