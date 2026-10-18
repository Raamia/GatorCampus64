# Gatorize likeness integration

Branch: `feat/gatorize-likeness`.

Qwen remains the image model. It reads reference photos and selects independent
appearance profiles; Blender builds the playable geometry. The 23 approved
round-one studies are implemented in a shared, versioned catalog at
`tools/blender/sgl_appearance.py`.

## Implemented catalog

| Field | Choices |
| --- | --- |
| Face | `oval`, `round`, `square`, `long`, `heart`, `broad` |
| Hair | `buzz`, `sidepart`, `fringe`, `waves`, `curls`, `coils`, `bob`, `long` |
| Body | `neutral`, `slender`, `broad`, `stocky`, `fuller` |
| Outfit | `tee`, `polo`, `hoodie`, `overshirt` |

Face profiles change skull, jaw, cheek, nose and ear geometry and face texture
placement. Fringe heights, locks and curl clumps adapt to the selected face.
Body profiles adjust cross-sections in each bone's frame, preserving shared
seams, joint caps, hands, shoes, head and the existing skeleton. Garment volume
is applied before collar, hood and strap geometry is fitted to the body.

Legwear remains `long_pants` or `shorts`. Colors remain independent of geometry.
The face textures are the existing procedural eyes and mouth. Glasses, facial
hair, tied-back hair and other unlisted geometry are not implemented by this set.

## Stored contract and Qwen behavior

New generated specs contain:

```json
"appearance": {
  "version": 1,
  "face": "square",
  "hair": "curls",
  "body": "broad",
  "outfit": "hoodie"
}
```

Qwen's schema requires the four selections and permits `unknown` for each.
The server assigns version 1. Repair logs unsupported, missing or unknown values
and resolves them to `oval`, `buzz`, `neutral`, and `tee`, respectively. The
prompt instructs Qwen to use unknown for obscured features and cropped bodies,
and never infer body shape from a face. Authored specs with unsupported versions
or profile IDs fail explicitly in the builder.

The outfit owns sleeve length and collar/hood geometry. Repair removes conflicting
collars and hoods, supplies the selected garment's accessory, and excludes rolled
cuffs with long sleeves. Independent crossbody straps remain available. Color
repair uses detected-face samples for cross-checking; heuristic-only crops can
fill missing colors but cannot override valid model colors.

Specs without `appearance` retain the legacy head/body path and handcrafted
extensions. Older model responses without this object also retain that path.
Legacy `build.hair_style` stays in stored specs for existing consumers; for a
versioned spec, `appearance.hair` controls the geometry. Stored manifests include
`appearance` so consumers can display the actual selections.

Qwen's endpoint and model configuration are unchanged. Required-model mode now
fails immediately if the backend is absent, as it already does on inference
failure, instead of silently producing a default character.

## Validation and review

The workshop and reproducible commands are in `tools/likeness/README.md`.
`dist/likeness-round-01` preserves the approved review artifacts;
`dist/likeness-integrated` builds the same studies through the production path.
Both directories are ignored build outputs.

Validation covers:

- Schema, prompt, repair, all 960 profile combinations, legacy compatibility,
  required-model failure, artifact persistence and photo cleanup.
- Real Blender/Fast64 builds of the 23 studies, including eye, cap and metal
  variants; finite and distinct browser geometry; face/skin texture continuity.
- All 48 face/hair combinations and 20 body/outfit fits. `check_fitting.py` tests
  unchanged protected boundaries across 90 frames of the template example
  animation and nine synthetic joint sweeps; it also checks the skeleton remains
  unchanged. Its report is `fitting_checks.json` in the integrated batch.
- A local worker smoke job with a fixed model response, a synthetic image, real
  Blender, actor renaming to `guest_8`, previews, portrait, local storage and cleanup.
  CPU Cycles previews replace EEVEE for this headless test only.

These checks do not establish general real-photo likeness or full in-game
animation quality. Live photo evaluation is recorded below; in-game checks are
left to the merge/deployment owner. No live services or model weights are changed
by this branch.

## Live Qwen diagnostic

The existing GPU service advertises `qwen2.5-vl-7b`, backed by
`Qwen/Qwen2.5-VL-7B-Instruct-AWQ`. The branch's prompt and schema were exercised
through an SSH local forward; the deployed worker was not replaced or restarted.

All 23 synthetic render requests returned valid raw structured responses on the
first `json_schema` attempt, with zero inference failures and median latency
9.104 seconds. Exact agreement with the varied study labels was:

| Diagnostic | Matches |
| --- | --- |
| Face profile | 1/6 |
| Hairstyle | 5/8 |
| Visible body profile | 1/5 |
| Outfit | 2/4 |
| Unknown body on head crops | 0/14 |

Qwen selected `round` for every face and `neutral` for every body. It confused
fringe with buzz, waves/coils with curls, and collared garments with T-shirts.
These are diagnostic label agreements on stylized renders, not measured accuracy
on people. This synthetic run preceded the reference-photo evaluation below.

The initial three-image smoke run exposed conflicting instructions: the neutral
body description suggested it for cropped bodies. That description now requires
visible balanced proportions, and the prompt explicitly requires unknown when
waist/hips are outside the frame. The full run above used this correction; it did
**not** solve the synthetic cropped-body misses. Do not treat schema compliance
or deterministic repair as evidence of correct visual selection.

The reproducible runner is `tools/likeness/validate_qwen.py`. Local raw responses,
repair notes, image hashes, transport attempts, timings and a Markdown report are
in `dist/qwen-validation/synthetic-v1/`; the initial smoke is preserved separately
in `synthetic-baseline-smoke/`. No reference photos were used in these runs.

## Supplied reference photos

The supplied set has one subject: a front portrait and two wider views. Manual
labels were recorded before inference: curly hair (`curls` or `coils` accepted),
`tee` as the closest available garment for a short-sleeved jersey, `oval` or
`long` for the front face outline, and `slender` for the visible wider views.
The portrait requires `body=unknown`. These are catalog matches, not measurements.

Six cases cover each image individually, all three together, a repeated
three-photo request, and reversed image order. Both the original request and
the revised appearance-first request returned six schema-valid responses with
zero inference errors:

| Diagnostic | Original | Appearance first |
| --- | --- | --- |
| Hair agreement | 6/6 | 6/6 |
| Garment agreement | 6/6 | 6/6 |
| Front/multiple-view face agreement | 0/4 | 3/4 |
| Visible-body agreement | 0/5 | 2/5 |
| Cropped-body unknown | 0/1 | 0/1 |
| Median request time | 10.714 s | 9.242 s |

The original response order always selected `round/curls/neutral/tee`. Asking
for `appearance` before colors and prose consistently selected
`oval/curls/slender/tee` for the portrait-first three-photo request, including
repeats. Reversed inputs still selected `neutral` body, and individual images
still missed face/body labels. The branch now requests appearance first; its
stored spec contract and Qwen model are unchanged. This is a demonstrated
improvement on one subject, not a general likeness acceptance result.

The wider photos also exposed a repair bug: when Haar face detection failed,
the heuristic crop sampled the red shirt as skin and the pale wall as hair,
then overwrote Qwen's colors. Repair now retains valid model colors when samples
have only heuristic detections. These samples remain missing-color fallbacks;
detected-face samples still support cross-checking. Replaying the recorded
responses verified that the red-skin/pale-hair overrides disappear. Some raw
Qwen color choices are still inaccurate; this fix addresses sampler trust only.

Local artifacts are in `dist/qwen-validation/photos-v1/` (original), `photos-v2/`
(updated branch), and `photos-v1/color-repair-replay.json`. The labeled manifest
and label notes are local in `dist/qwen-validation/`. Actual three-photo outputs
were built with Blender/Fast64 and rendered for comparison at
`http://localhost:5174/photo-validation/` through the existing review tunnel.
The gallery serves generated artifacts; original reference images stay in the
supplied Downloads folder. Focused regression tests: 75 passed.

Known follow-ups are single-photo visibility handling, image-order sensitivity,
evaluation across additional subjects, and in-game checks. The user accepted the
current likeness behavior and requested finishing this branch without further
photo-specific tuning. No worker deployment or model replacement was performed.

## Additional front/left/right PNG set

The supplied full-length PNGs show a graduation cap and a loose gown. Labels
were recorded separately: curls/coils accepted for visible hair, oval/long for
the front face outline, and body unknown because the gown obscures proportions.
Outfit was not scored: graduation clothing has no corresponding catalog assets.

The same six-case protocol, using the updated appearance-first request, produced
six schema-valid responses and no inference errors (median 9.978 seconds). All
six selected `round/curls/neutral/tee`: hair agreement 6/6, labeled face agreement
0/4, and unknown-body agreement 0/6. All described the headwear as a graduation
cap, but the free-text top description also said tee. This set does not reproduce
the portrait-first improvement seen with the previous references.

As a separate scale diagnostic, a padded face crop from the front PNG was added
alongside the three originals, first and then last (four images per request).
Both responses stayed round/curls/neutral; the outfit changed between hoodie
and tee. The crop therefore did not resolve the face or visibility errors, and
no automatic crop preprocessing was added to production.

Reports and frozen labels are local in `dist/qwen-validation/png-refs/`,
`png-cases.json`, `png-label-notes.md`, and `png-crop-probe/`. The actual
three-image selection was built and exported for review at
`http://localhost:5174/photo-validation/png/`. It renders the selected blue tee;
it does not implement a graduation gown or cap.

## Branch handoff

The user approved the 23 appearance studies and accepted the current Qwen
selection limits. This branch is ready for another model to handle merge and
deployment. Further photo-specific tuning is outside this handoff's scope.

The changes include the versioned appearance catalog and Blender fitting,
Qwen schema/prompt/repair integration, required-model failure handling,
heuristic-sample color protection, and browser face-texture color correction.
Legacy specs remain supported. Qwen stays the image model.

Final focused regression command (75 tests):

```sh
/tmp/sglworker_venv/bin/python -m pytest -q \
  server/worker/tests/test_spec_ai.py \
  server/worker/tests/test_schema_gen.py \
  server/worker/tests/test_appearance.py \
  server/worker/tests/test_qwen_validation.py \
  server/worker/tests/test_pipeline.py \
  server/worker/tests/test_actor_rename.py
git diff --check
```

The virtual environment and generated artifacts are local to Zion. Reproduction
instructions are in [the workshop README](../tools/likeness/README.md) and
[the worker README](../server/worker/README.md). The integrated batch and fitting
report are in `dist/likeness-integrated/`; the local pipeline smoke is in
`dist/likeness-worker-smoke/`; Qwen evaluation reports are in
`dist/qwen-validation/`. Reference photos and generated artifacts are not committed.

The existing `sgl-likeness-review.service` serves the galleries on Zion port 5174.
From the laptop, run `ssh -N -L 5174:127.0.0.1:5174 zion`, then open
`http://localhost:5174/integrated/`. Photo-result comparisons are under
`/photo-validation/` and `/photo-validation/png/`; they show generated models.

Merge and deployment were not performed. The next owner should use
[the operations guide](operations.md) for deployment and game verification,
retaining the existing Qwen endpoint/model configuration. Accepted limitations
include face/body selection bias, missed unknown-body selections, input-order
sensitivity, inaccurate raw colors, and unsupported garments such as gowns.
The geometry checks cover the template action and joint sweeps, not every game
animation or possible clothing intersection.
