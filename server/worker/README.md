# Gatorize Me GPU worker

Claims `queued` jobs from Postgres (`FOR UPDATE SKIP LOCKED`, one job at a time) and runs the
character pipeline of `docs/web_platform_spec.md` §5.1 steps 2-6:

| state (`jobs.state`) | what runs | module |
|---|---|---|
| `spec` | download `photos/<job>/`, vision model → JSON, schema check + repair, k-means colour cross-check | `spec_ai.py`, `photo_colors.py`, `schema_gen.py` |
| `face` | `tools/blender/sgl_face_gen.py` → `art/sglguest/textures/` in the job dir | `pipeline.py` |
| `build` → `export` → `validate` → `preview` | `run_blender.sh build_character.py -- sglguest --art-dir … --build-dir … --actors-dir …` (10 min cap, process group killed on timeout). Its stdout markers (`SGL saved`, `SGL validation`, `SGL_PREVIEW`) move the state. `SGL_BUILD_REPORT` is parsed, then `validate_export.py` runs again outside Blender, also on a copy renamed to `guest_8` | `pipeline.py` |
| `preview` (step `store`) | 64×64 portrait, upload to `builds/<job>/`, delete `photos/<job>/` (on success or failure) | `portrait.py`, `storage.py` |
| `ready` / `failed` | ready: `jobs.artifacts` + `characters.spec` written, then `sgl_assign_slot()` gives the character a slot and queues its deploy. failed: `step` = the failing step, `jobs.error` = one line, `jobs.log` = the last 8000 characters | `db.py`, `worker.py` |

`characters.state` / `characters.step` mirror the job's state / step at every update (same
transaction), so the API's per-user "in progress" limit and `/me` see the real step.

## Actor id and guest slots

The API assigns slots only when a character is ready, and an evicted character can later be
redeployed into a different slot. Because of that, the worker can't know `guest_<n>` at build time.
Every job is built under one **neutral actor id, `sglguest`**, and the deploy step renames it:

```
python3 server/worker/actor_rename.py <builds/<job>/actors/sglguest> <mod>/actors guest_3
cp builds/<job>/portrait.png <mod>/textures/sgl_portrait_guest_3.png
```

Fast64 builds every symbol from the actor name: `<id>_geo` (the root that DynOS looks up),
`<id>_<node>…`, `mat_<id>_…`, `mat_revert_<id>_…` and the face textures `<id>_eyes_open_rgba16`.
In the daniel export, every occurrence is an identifier that starts with `<id>_` at a word boundary
or after `mat_`/`mat_revert_`, so a token rewrite is exact. `actor_rename.py` is stdlib-only and
fails if any old-id token is left. The tests rename the real `mods/sgl64/actors/daniel` export to
`guest_3` and back, and `validate_export` passes on both. The worker also validates each build
renamed to `guest_8` before it marks the build ready. `character.json` in `builds/<job>/` keeps
`"id": "sglguest"`, so the deploy rewrites `id` along with the files.

## Stored artifacts (`builds/<job>/`)

`manifest.json` (index: preview keys, portrait, actor dir, card colour, tris, spec repair notes,
photo colour samples), `character.json`, `build_report.json`, `previews/{front,back,left,three_quarter,head,head_side,eye_states,…}.png`,
`portrait.png` (opaque RGBA 64×64, made from `head.png` and falling back to a crop of `front.png`, on a
`charselect.lua`-style card colour), `face_sheet.png`, `actors/sglguest/{geo_header.h,geo.inc.c,model.inc.c}`, `log.txt`.

`jobs.artifacts` (written on success, so the API never lists the bucket) holds the keys:
`{"build_id": "sglguest", "prefix": "builds/<job>/", "manifest", "character_json", "portrait",
"previews": [...], "actor_dir": "builds/<job>/actors/sglguest/", "files": [every key]}`.
`GET /deploys/pending` turns it into the bridge's `files[]`; `GET /jobs/{id}` and the gallery
presign `previews` and `portrait`.

## Database contract

The schema is `server/api/schema.sql`; its header is the worker contract and `db.py` holds all of
the worker's SQL for it (the tests run against that file):

- **Claim**: oldest `queued` job, `FOR UPDATE OF c SKIP LOCKED`, then job lock; both rows go to
  `spec`/`spec`, `attempts + 1`, `error` cleared. The photos are exactly the keys in `jobs.photos`
  (`photos/<job>/<i>.jpg`, written by the API).
- **States**: `jobs.state` = `characters.state` ∈ queued, spec, face, build, export, validate,
  preview, ready, failed. `step` uses the same names plus `store` (under state `preview`); on
  success it is `ready` and on failure the step that failed. Check constraints enforce both sets.
- **Slots**: the worker never picks one. Its ready transaction takes the slot lock, marks the
  job and the character ready and calls `sgl_assign_slot()`: a free slot first, else the least
  recently played unpinned slot whose character is finished. If nothing is free (everything is
  pinned), the character stays ready without a slot and `sgl_sync_deploys()` slots it on a later
  bridge poll. Failure calls `sgl_release_slot()`.
- **Deleted character**: the owner can delete it, and its job by cascade, at any time. A job
  UPDATE that affects 0 rows raises `db.JobGone`, and the pipeline stops (`JobCancelled`, which
  kills Blender's process group). Then `photos/<job>/` and `builds/<job>/` are deleted.
- **Leases**: every claim gets a fresh UUID token and a 120-second expiry. A dedicated
  connection renews every 30 seconds, including during quiet model/Blender calls. Progress,
  renewal, and completion require the same unexpired token and matching character. Lost
  leases cancel the pipeline; a silent Blender child is checked every second and killed.
- **Recovery**: before every claim/poll, any worker can atomically fail expired jobs from
  any host, retaining their last step and a retry message. It then attempts photo/build cleanup.
  Hostnames are diagnostic only. Pre-upgrade active jobs with NULL leases are also expired.
  Jobs are never automatically requeued because their photos may already be deleted.
  A new user submission gets a new job ID and follows normal generation quotas.
  Recovery requires at least one worker to reach its poll loop; if all workers are down,
  a replacement performs recovery when it starts. See [rollout](../../docs/backend_leases_heartbeats.md).

## Environment

| Var | Default | |
|---|---|---|
| `DATABASE_URL` | – | libpq URL (`sslmode=require` for Vultr Managed PostgreSQL) |
| `WORKER_NAME` | hostname | written to `jobs.worker` for diagnostics; not an ownership key |
| `POLL_SECONDS` | 3 | |
| `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | – | Vultr Object Storage; `STORAGE_DIR=<dir>` uses a local dir instead |
| `VLM_BASE_URL`, `VLM_API_KEY`, `VLM_MODEL`, `VLM_TIMEOUT` | –, –, –, 120 | OpenAI-compatible endpoint with image input. Unset means no model (photo colours + defaults) |
| `VLM_REQUIRED` | 0 | 1: a model failure fails the job (default: fall back) |
| `SGL_REPO` | this checkout | repo with `tools/blender`, `tools/vendor`, `tools/blender-scripts` |
| `BLENDER` | `/opt/blender-4.5.3/blender` | |
| `WORK_ROOT` | `/tmp/sglwork` | per-job temp dirs, deleted after each job |
| `BUILD_TIMEOUT` | 600 | seconds, covers `run_blender.sh` crash retries too |
| `SGL_RETRIES` | 3 | `run_blender.sh` retries on Blender crashes |
| `USE_OPENCV` | 1 | Haar face boxes when cv2 is installed |
| `KEEP_WORKDIR` / `KEEP_FAILED` | 0 | keep job dirs for debugging |

## Run on sgl-gpu

`/opt/sgl64` must contain this branch: `tools/blender/build_character.py --art-dir` and
`sgl_util.SGL_ART_DIR` are part of it. Re-run `server/deploy/provision_gpu.sh` after merging.

```
# bare (fastest to debug)
python3 -m venv /opt/sgl-worker-venv && /opt/sgl-worker-venv/bin/pip install -r /opt/sgl64/server/worker/requirements.txt
cd /opt/sgl64/server/worker && set -a && . ./.env && set +a && /opt/sgl-worker-venv/bin/python worker.py --once

# docker (the image holds only Python deps + Blender's libs; Blender and the repo are mounted read-only)
cd /opt/sgl64/server/worker && cp .env.example .env && $EDITOR .env
docker compose up -d --build                  # Vultr Serverless Inference, or no model
docker compose --profile vllm up -d --build   # + local Qwen2.5-VL-7B-Instruct-AWQ (VLM_BASE_URL=http://vllm:8000/v1)
```

After the model finishes downloading, run the dependency-free readiness probe
from the worker container (it makes no inference request):

```bash
docker compose exec worker /venv/bin/python /opt/sgl64/server/worker/vlm_probe.py
```

It checks `/health` and `/v1/models`, and verifies that `VLM_MODEL` is
advertised. A failed probe means the worker will use its configured fallback
unless `VLM_REQUIRED=1`.

The docker setup needs the NVIDIA container toolkit with the `graphics` capability, because
Blender renders its previews through EGL. `docker-compose.yml` documents the VRAM budget: vLLM is
capped at 60% of the 16 GB A16 (about 9.6 GB: 6.7 GB weights plus KV cache for 2×8k tokens),
Blender peaks around 1-2 GB, and that leaves about 4 GB of headroom.

## Tests

```
uv venv /tmp/sglw && VIRTUAL_ENV=/tmp/sglw uv pip install -r server/worker/requirements-dev.txt
/tmp/sglw/bin/python -m pytest server/worker/tests
```

The Postgres tests (`test_db.py`, `test_integration_api.py`) apply `server/api/schema.sql` to
`$TEST_DATABASE_URL` if it is set, else to a throwaway `postgres:16-alpine` container started with
docker. Without either, they are skipped. `test_integration_api.py` runs the real API (FastAPI,
moto S3) and the real worker (`db.py`, `worker.handle`, the pipeline with the fake Blender) on one
database and bucket: upload, claim, build, ready plus slot, then `GET /jobs/{id}` and
`GET /deploys/pending`.

`tests/fake_blender.py` stands in for `run_blender.sh`. It "exports" the real daniel actor renamed
to `sglguest` and copies daniel's previews, so the real face generator, `validate_export`, the
portrait and the storage code all run without Blender.

## Approved likeness catalog

Qwen now selects independent face, hair, body and outfit profiles from
`tools/blender/sgl_appearance.py`. The worker stores `appearance.version = 1` and
normalizes sleeve length and collar/hood accessories from the outfit. Unknown
features receive logged defaults; colors still come from model output and photo
sampling. Specs without `appearance` retain the legacy path. `VLM_REQUIRED=1`
fails when no backend is configured as well as when inference fails.

The structured response requests appearance before colors and prose; live Qwen
checks found this improved selections with the three supplied reference views.
Single-view and input-order sensitivity remain documented limitations. Skin/hair
samples from heuristic-only crops no longer override valid model colors; they
remain fallbacks when a model color is missing. Detected-face samples still
support the usual color cross-check.

See [the likeness contract](../../docs/gatorize_likeness.md) and
[the local model workshop](../../tools/likeness/README.md) for profile IDs,
validation scope and headless browser review instructions.

### Per-job GPU evidence

`manifest.json.gpu_telemetry` contains UTC-timestamped snapshots at `spec.before`,
`spec.after`, `build.before`, and `build.after`. Each sample records `available` and
`gpus` (one entry per local GPU: `name`, `utilization_gpu_pct`, `memory_used_mib`,
`memory_total_mib`). Unsupported metrics are null, not zero. The same JSON samples
appear as `GPU telemetry:` lines in the job log, including on failed steps (subject
to the existing database log-tail limit). Successful jobs also store `log.txt`.
The existing `jobs.artifacts` object-key contract is unchanged.

The worker runs `nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,name
--format=csv,noheader` with a two-second timeout per snapshot. Missing drivers,
missing binaries, timeouts, and invalid output produce an `available: false`
sample with a clear `GPU telemetry unavailable` note and do not fail the job.
These are reproducible host-wide observations for auditing the Vultr worker,
not per-process attribution or peak utilization: idle snapshots can be zero,
Blender may use the CPU, and a remotely hosted vision model is not measured by
the worker's local GPU query. No inference, Blender, or deployment settings change.

### Public step timing

The shared API schema records up to 64 actual state/step intervals in
`jobs.step_history` via a database trigger. Existing worker progress, retry, and
terminal writes supply the boundaries; repeated progress/log writes and lease
renewals do not reset them. The API's public `/pipeline/status` projects only
anonymous operational fields from these records for the companion `/pipeline`
page. Older jobs without recorded transitions show timings as unavailable.
