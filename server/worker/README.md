# Gatorize Me GPU worker

Claims `queued` jobs from Postgres (`FOR UPDATE SKIP LOCKED`, one job at a time) and runs the
character pipeline of `docs/web_platform_spec.md` §5.1 steps 2-6:

| state (`jobs.state`) | what runs | module |
|---|---|---|
| `spec` | download `photos/<job>/`, vision model → JSON, schema check + repair, k-means colour cross-check | `spec_ai.py`, `photo_colors.py`, `schema_gen.py` |
| `face` | `tools/blender/sgl_face_gen.py` → `art/sglguest/textures/` in the job dir | `pipeline.py` |
| `build` → `export` → `validate` → `preview` | `run_blender.sh build_character.py -- sglguest --art-dir … --build-dir … --actors-dir …` (10 min cap, process group killed on timeout). Its stdout markers (`SGL saved`, `SGL validation`, `SGL_PREVIEW`) move the state. `SGL_BUILD_REPORT` is parsed, then `validate_export.py` runs again outside Blender, also on a copy renamed to `guest_8` | `pipeline.py` |
| `preview` (step `store`) | 64×64 portrait, upload to `builds/<job>/`, delete `photos/<job>/` (on success or failure) | `portrait.py`, `storage.py` |
| `ready` / `failed` | `characters.state` = `ready` (+ `spec`) or `failed`; `jobs.step` holds the failing step, and `jobs.log` the last 8000 characters of the log | `db.py`, `worker.py` |

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

## Assumed database schema (reconcile with `server/api/schema.sql`)

All SQL lives in `db.py`:

```
jobs(id uuid, character_id uuid, state text, step text, log text, started timestamptz,
     finished timestamptz, worker text, created timestamptz)
characters(id uuid, owner_sub text, name text, slot int null, state text, spec jsonb,
           created timestamptz, deployed_at timestamptz)
```

The worker writes `characters.state` ∈ {`building`, `ready`, `failed`} (constants in `db.py`). It
never touches `slot` or `deployed_at`. On startup it fails any job it had claimed but not finished
(by `WORKER_NAME`) and deletes that job's photos.

## Environment

| Var | Default | |
|---|---|---|
| `DATABASE_URL` | – | libpq URL (`sslmode=require` for Vultr Managed PostgreSQL) |
| `WORKER_NAME` | hostname | written to `jobs.worker`, used for orphan recovery |
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

The docker setup needs the NVIDIA container toolkit with the `graphics` capability, because
Blender renders its previews through EGL. `docker-compose.yml` documents the VRAM budget: vLLM is
capped at 60% of the 16 GB A16 (about 9.6 GB: 6.7 GB weights plus KV cache for 2×8k tokens),
Blender peaks around 1-2 GB, and that leaves about 4 GB of headroom.

## Tests

```
uv venv /tmp/sglw && VIRTUAL_ENV=/tmp/sglw uv pip install -r server/worker/requirements-dev.txt
/tmp/sglw/bin/python -m pytest server/worker/tests
# + the Postgres tests:
docker run -d --rm --name sglw-pg -e POSTGRES_PASSWORD=pw -p 55432:5432 postgres:16-alpine
TEST_DATABASE_URL=postgresql://postgres:pw@localhost:55432/postgres /tmp/sglw/bin/python -m pytest server/worker/tests
```

`tests/fake_blender.py` stands in for `run_blender.sh`. It "exports" the real daniel actor renamed
to `sglguest` and copies daniel's previews, so the real face generator, `validate_export`, the
portrait and the storage code all run without Blender.
