# Gatorize model workshop — round 01

23 synthetic, independently selectable shape studies: 6 face profiles, 8 hair
models, 5 body silhouettes, and 4 outfits. Each study uses the coopdx character
template, with consistent colors within each category. Qwen remains the image
model; this review batch uses fixed specs and makes no inference requests.

## Open the gallery

On Zion, from the repo root:

```sh
python3 -m http.server 5174 --bind 127.0.0.1 --directory dist/likeness-round-01
```

On your laptop, keep this SSH tunnel open, then visit http://localhost:5174:

```sh
ssh -N -L 5174:127.0.0.1:5174 zion
```

The integrated production set is available at http://localhost:5174/integrated/
through the same tunnel (the original gallery contains a symlink to the integrated
batch). Feedback is stored separately for each set. Pose sheets for the fuller
body and hoodie are at `integrated/models/b05/poses.png` and
`integrated/models/c03/poses.png`; left to right: template frames 0, 30, 60,
then synthetic 60-degree limb bends around local Y and Z.

Pick a category, select comparison slot A or B, then click a study. Front,
three-quarter, side, and back controls apply to both models at the same scale.
Switch between face detail and full body, or drag either model to orbit.
Notes are saved in browser local storage under each study's ID. Download
feedback to share the JSON file. GLBs can also be downloaded individually.
The viewer library is served locally; no CDN or account login is needed.

The current batch is also served by the user service
`sgl-likeness-review.service` on port 5174. While it is running, no separate
Python server is needed. Inspect or stop it with
`systemctl --user status sgl-likeness-review` or
`systemctl --user stop sgl-likeness-review`. It is not enabled at boot.

## Rebuild

Dependencies are the versions pinned in `server/deploy/provision_gpu.sh`:

- Blender 4.5.3 LTS (local binary: `tools/vendor/blender/blender`).
- Fast64-Gart `9384477f2ccdc8b6e05a96b52241f98808feb90b` in
  `tools/blender-scripts/addons/fast64`.
- coopdx character-template `58149f1b58cef75c7f90c19f6d3cadb66bd5b915`, with
  the Mario template at `tools/vendor/template/Mario Coop Model Template.blend`.
- Existing `companion/app/node_modules/@google/model-viewer` for the browser.

```sh
python3 tools/likeness/build_batch.py --jobs 2
# Rebuild particular studies
python3 tools/likeness/build_batch.py --only f01 h05 --jobs 2
# Verify all delivered artifacts (requires Pillow)
python3 tools/likeness/verify_batch.py
# Exercise the running gallery in Chromium (uses the app's Playwright package)
node tools/likeness/check_gallery.mjs
```

Builds and renders run headlessly. Posters use CPU Cycles, so Zion needs neither
a desktop nor a working GPU driver. Each model has a saved `.blend`, validated
Fast64 actor export, GLB, front and three-quarter PNGs, spec, and build report.
Generated assets and downloaded dependencies live in ignored directories.

`catalog.py` draws the studies from the shared `tools/blender/sgl_appearance.py`
catalog. Default builds retain the round-one experiment in `shapes.py` through
batch-local character extensions. Integrated builds use the production appearance
contract, independent face/hair fitting and bone-local body fitting:

```sh
python3 tools/likeness/build_batch.py --integrated --output dist/likeness-integrated --jobs 2
python3 tools/likeness/verify_batch.py dist/likeness-integrated
tools/vendor/blender/blender --background --factory-startup --threads 4 \
  --python-exit-code 1 --python tools/likeness/check_fitting.py -- dist/likeness-integrated
```

The fitting check exercises 48 heads and 20 body/outfit combinations across the
90-frame template example animation plus nine joint sweeps. It checks finite
geometry, unchanged skeleton and protected vertex positions, not general clipping
or the game's complete animation library.

## Public character showcase

The companion's `/showcase` page publishes the approved integrated batch without
sign-in, uploads or inference. Its 23 self-contained GLBs and 23 WebP previews
total about 1.34 MiB; 3D loads only after the visitor requests it. The checked-in
assets are sufficient for deployment: the worker and private review gallery are
not needed to serve this page.

To refresh assets after rebuilding and validating the integrated batch:

```sh
python3 tools/likeness/export_showcase.py
```

The exporter requires Pillow, allows only the 23 approved study IDs, and records
model hashes in `companion/app/public/showcase/provenance.json`. Do not copy whole
evaluation folders into the public directory; private references and model
responses about real subjects stay local.

Build and validate from `companion/app` with `npm run build` and
`npm run validate`. For a local browser check, run these from the repo root in
separate terminals:

```sh
python3 -m http.server 5175 --bind 127.0.0.1 --directory companion/app/dist/client
node tools/likeness/check_showcase.mjs
```

The check uses the app's Playwright installation and `/usr/bin/chromium`
(`CHROMIUM` overrides it). It maps the clean route to `showcase.html` for Python's
server, which lacks the production asset layer's HTML URL resolution. It checks
lazy loading, actual GLBs in every category, camera reset, mobile overflow,
absence of API/WebSocket traffic, and image fallback after a failed GLB request.
Screenshots are written to `/tmp/sgl-showcase-{desktop,mobile}.png`.

Handoff: `feat/public-character-showcase` is based on
`docs/integrations-and-track-review`; include that documentation commit
when merging. Build, TypeScript validation, all 52 app tests and the browser check
passed; desktop/mobile screenshots were inspected. Merge/deployment
belong to the deployment owner, who should verify `/showcase` on the deployed
domain. No production deployment is performed by these checks.

## What to judge

- F01–F06: jaw, chin, cheeks, forehead and nose; haircut and clothing are fixed.
- H01–H08: hairline, fringe, volume, length and the side/back silhouette; face is fixed.
- B01–B05: relative shoulder, waist, hip and limb silhouette at one height.
- C01–C04: T-shirt, collar, hood and overshirt volume on the neutral body.

The user approved all 23 round-one studies. The face textures remain procedural.
Production body fitting preserves the original joint caps and fits garment details
after changing the body silhouette. Live Qwen evaluation with supplied photos is
complete for this branch; the user accepted the current limitations and requested
no further photo-specific tuning. Results and the merge/deployment handoff are in
[the likeness document](../../docs/gatorize_likeness.md). In-game verification is
left to the deployment owner. Export and boundary validation alone do not
establish animation quality or resemblance to a person.

## Validate actual Qwen responses

`validate_qwen.py` calls the configured OpenAI-compatible endpoint using the
worker's current prompt, structured schema, color sampling and required-model
repair path. Set `VLM_BASE_URL`, `VLM_MODEL`, and `VLM_API_KEY` in your environment.
For the existing GPU service, an SSH local forward can expose its loopback port
8000 without changing the running worker.

```sh
/tmp/sglworker_venv/bin/python tools/likeness/validate_qwen.py \
  --synthetic dist/likeness-integrated --output dist/qwen-validation/synthetic
```

Use `--only f01 h05 c03` for a small smoke run. The full synthetic set checks the
varied field in each study and expects `body=unknown` for head crops. These are
label-agreement diagnostics, not a real-photo likeness benchmark. Synthetic
stylization can itself make face and body labels ambiguous to the vision model.

For reference photos, create a local manifest with 1–4 images per case (paths
relative to the manifest). Only add expected selections after independently
labeling the visible features; allow multiple reasonable choices when ambiguous:

```json
[
  {"id": "subject01-head", "images": ["reference/subject01/head.jpg"],
   "expected": {"body": ["unknown"], "hair": ["curls", "coils"]}},
  {"id": "subject01-multiple", "images": ["reference/subject01/head.jpg", "reference/subject01/full.jpg"]}
]
```

```sh
/tmp/sglworker_venv/bin/python tools/likeness/validate_qwen.py \
  --manifest dist/qwen-validation/cases.json --output dist/qwen-validation/photos
```

Each run saves the prompt, schema, input hashes, complete raw responses, repaired
specs, repair notes, transport attempts and timings in an ignored output folder.
It also writes a Markdown report. It does not copy photos, write to production
storage, create jobs or deploy characters. Keep photo reports local; they contain
the model's descriptions of the subjects. Exit 1 indicates an inference failure,
raw schema failure or labeled selection mismatch; repaired defaults cannot turn
an incorrect model answer into a passing selection.
