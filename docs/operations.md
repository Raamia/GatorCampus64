# Production operations

GitHub `main` is the source of truth. Production deployment runs from the operator's local machine; credentials live in the ignored root `.env` and `/etc/sgl` on the hosts. Never deploy an uncommitted working tree. Fetch and reconcile `origin/main` before every release; do not force-push it.

## Deployment inventory

- Game host: `sgl-host`, bridge in `/opt/sgl/server/bridge`, game data in `/srv/sgl`, API in `/opt/sgl-api`.
- GPU host: `sgl-gpu`, source in `/opt/sgl64`, worker Compose project in `/opt/sgl64/server/worker`.
- DeepSpace: `companion/app`, owned app `gator-field-board-mlh`, https://gator-field-board-mlh.app.space. Deploy with the DeepSpace CLI from this directory; do not use DeepSpace source push.
- API binds only to `127.0.0.1:8000`; the bridge uses this local endpoint. Public HTTPS at `https://api.gatorcamp.us` was verified.

## Before deploying

1. Record the exact Git commit, check the working tree is clean, and run relevant checks. Bridge: `python -m pytest -q server/bridge/tests`; game: `tools/luatest/run.sh`; dashboard: `npm run validate` and `npm run build` in `companion/app`.
2. Back up configuration, previous source, service units, and game saves/state. Take a database backup before schema changes. Existing bootstrap backup: `/root/sgl-backups/20261017T132054Z` on the game host; it contains configuration, game service units and `/srv/sgl`, not all application source or the database.
3. Prepare the new release from `git archive <commit>` into a staging directory. Transfer only tracked artifacts. Do not sync the whole working tree.
4. Check for connected players before restarting the bridge; stopping it also stops the game.

## Files to preserve

Never apply unrestricted `rsync --delete` to a deployed application directory. Explicitly preserve `.venv/`, `.env`, generated files, and toolchain/vendor directories. Keep `/etc/sgl`, `/srv/sgl/sav`, `/srv/sgl/bridge`, ROM files, deployed `actors/guest_*`, `textures/sgl_portrait_guest_*`, and the deployed `guests.lua` outside source replacement. `mods/sgl64` in the release is the pristine placeholder source; it is distinct from the installed, mutable mod.

Create/install dependencies before service activation. The API requires its `sgl-api` system account. Its unit sets `HOME=/tmp` to avoid libpq probing protected home directories. Run schema application once, then keep `SGL_APPLY_SCHEMA=0` for normal multi-worker startup.

For worker lease and server presence upgrades, follow [the coordinated rollout](backend_leases_heartbeats.md): drain old workers, apply the additive schema, and upgrade API/bridge together. Old bridge events no longer establish online status.

For durable object cleanup and staged deploy revalidation, follow
[the cleanup/deploy rollout](backend_cleanup_deploy_safety.md), including the
new SQL triggers and matching API/bridge protocol.

## Verification and rollback

After activation, record commit and timestamp on each host, compare deployed source hashes, check service state, and inspect fresh logs. API: `/healthz` returns 200; anonymous `/me` returns 401; a bridge token can access `/deploys/pending` but cannot access user-only `/me`. Game: bridge stays active and UDP 7777 is listening. GPU: inspect Compose state, fresh worker/VLM logs, and VRAM usage; a running worker alone does not prove image inference works.

For rollback, stop the affected service, restore the previous source and matching dependencies/configuration, restore the previous service definition if changed, and start/verify again. Do not roll back game saves or database contents automatically. Database migration rollback is a separate, reviewed recovery operation.

## Remaining acceptance work

Interactive Auth0/browser and in-game login, a consented generation through guest deployment, two-account link/delete acceptance, and a real production-backup recovery drill remain deployment acceptance work. The local backend branch stack implements explicit account linking and durable deletion; the live hosts observed were still at audit release the reviewed revision.

See [operational validation and recovery](backend_operations_validation.md) for executed read-only checks, the isolated synthetic restore drill, and the post-deploy checklist. Follow the [account lifecycle](backend_account_lifecycle.md) and [identity-linking](backend_identity_linking.md) rollout notes after the lease and cleanup branches.

## Local release command

Run `python3 server/deploy/release.py` from the operator checkout. The ignored root `.env` supplies `SGL_HOST_*`, `SGL_GPU_*`, and optional `SGL_SSH_JUMP_HOST`; it is parsed as data, never sourced. SSH uses batch mode. The SSH account must have permission to write production paths and control services (currently root).

```bash
# Read-only: inspect exactly which committed source files would be installed.
python3 server/deploy/release.py plan host --ref origin/main
python3 server/deploy/release.py plan gpu --ref origin/main
# Read-only: recorded source hashes, then service/socket/API checks.
python3 server/deploy/release.py status host
python3 server/deploy/release.py verify host
python3 server/deploy/release.py verify gpu
# Mutates production; first reconcile origin/main, review plan, back up DB/config,
# and arrange a quiet game/job window. First adoption requires the extra flag.
python3 server/deploy/release.py deploy host --ref origin/main --adopt-current --allow-restart
python3 server/deploy/release.py deploy gpu --ref origin/main --adopt-current --allow-restart
# Later deployments omit --adopt-current. Recover one source release per host
python3 server/deploy/release.py rollback host --allow-restart
python3 server/deploy/release.py rollback gpu --allow-restart
```

This is an **existing-installation updater**, not a provisioning or migration command. It does not install units, Caddy configuration, system packages, secrets, Auth0 settings, or schema changes. API/bridge Python environments must already exist; changed requirements stop deployment so the operator can snapshot and prepare matching dependencies separately. Worker activation rebuilds only the worker service in the existing `worker` Compose project; it leaves vLLM and persistent volumes running. A worker restart may wait up to its configured eleven-minute grace period for a job. GPU verification proves container liveness only; use the inference probe and a consented character job to establish readiness.

Each release packages **only regular files in `git archive <commit>`**. Host mappings are API → `/opt/sgl-api`, bridge/worker/NPC/pristine mod source → `/opt/sgl`, installed mod → `/srv/sgl/mods/sgl64`; GPU source → `/opt/sgl64`. Installed `guests.lua`, guest actors/portraits, `.env`, virtualenvs, saves, ROMs, vendor checkouts, and untracked toolchains are preserved. Repository symlinks are skipped and symlink destinations are rejected. Service units are intentionally installed separately. No recursive delete is applied to application directories.

Before the first overwrite, the updater stores every affected existing file and the previous release manifest under `/var/lib/sgl-releases/<timestamp>-<commit>/`. `/var/lib/sgl-releases/current.json` records the installed commit, timestamp, and per-file SHA-256. Subsequent deployments and rollback stop on source drift. A release that removes previously managed paths also stops: inspect and archive those paths explicitly, then reconcile the manifest; the updater never silently removes old source. Plan output is safe to share; it contains paths, commit, counts and archive size, not env values.

Source files are updated in place and services then restarted; this is not an atomic blue/green release. A failed activation leaves the recovery manifest available and must be followed by inspection or `rollback`. Rollback restores overwritten files and removes only files created by that release. It does **not** restore Python dependencies, database state, credentials, service definitions, generated assets, or game saves. On first adoption rollback returns to the unmanaged baseline, so `status` will again say no managed release. Retain at least the preceding release backup until the next release passes acceptance; backup pruning is manual.
