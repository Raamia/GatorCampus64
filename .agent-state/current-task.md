# Current task

## Objective
Fix outdoor ground z-fighting by partitioning overlapping visual surfaces by purpose.

## User constraints
- Act autonomously; handle local rebuild/install/restart in this terminal.
- Preserve other agent’s work, collision, gameplay, doors, water and prior wall/HUD repairs.
- Script-error banner is handled separately; do not investigate it.
- Teammate handles branch review merge conflicts; do not merge it.
- No tests unless requested; export validation and visual QA performed as part of builds.

## Decisions
- Branch vishnu2/terrain-wall-fixes (created from codex/parallel-work), checkout gimmickfc-codex.
- Sibling gimmickfc is another agent; do not overwrite or blanket-install from this baseline.
- Ground priority: natural ground < paving/paths < roads < lane paint < crosswalks.
- Partition opaque ground polygons into disjoint convex pieces; preserve/interpolate UVs.
- All eligible visual ground meets at z=-0.03m, below the collision/shadow floor.
- Only near-ground flat visual faces participate; raised surfaces, water, collision excluded.
- Install only selected exported mesh definitions; preserve installed materials and other meshes.

## Relevant files
- tools/campus/ground_surfaces.py: priority, convex clipping, UV interpolation, spatial grid, stage integration.
- tools/campus/stage_ground.py: invokes partition after ground generation, before meshing.
- tools/campus/stage_data.py: explicit lawn override for four Plaza woodchip area IDs.
- tools/blender/replace_export_meshes.py: narrow visual mesh replacement, symbol checks, unchanged-declaration assertion.
- tools/campus/interiors/marston.py and libwest.py: prior shared partition-corner repair.
- tools/campus/test_interior_wall_ends.py: prior six focused regressions (not rerun for terrain task).
- docs/handoff/PROJECT_CONTEXT.md and PARALLEL_WORK.md.

## Files changed
- New ground_surfaces.py and replace_export_meshes.py; modified stage_ground.py.
- Updated model.inc.c and header.inc.h in castle_grounds, bob, wf and jrb.
- Prior pending ccm/bbh generated files and interior source repairs remain local.
- Prior website interior-count removals remain in companion/app pages and DESIGN.md.
- This handoff; fixes committed on vishnu2/terrain-wall-fixes for teammate integration; no hosted deployment.

## Work completed
- Prior library fixes: 15 Marston + 62 LibWest solid partition corners joined; door/glass/T joins excluded.
- Marston elevator/stair core returns joined on both sides across all five floors, with collision.
- User confirmed both libraries look correct.
- Reitz audit generated 1,856 wall runs across eight floors; 369 right-angle joins and 108 core runs traced.
- Six thicker-wall candidates at eye height are window/storefront bays; L1 render confirms glass.
- Malachowsky atrium/passages and Swamp tunnels use shared boundaries; no additional core gap confirmed.
- Fixed installed actor-through-wall issue by existing fix_geometry_modes.py: 454 material pairs across five levels.
- User confirmed actors now stay hidden behind walls; repo already contains fix the earlier change.
- Ground repair partitions generic terrain together with eligible landmark brick/concrete walkways.
- Built all four outdoor stages in scratch, preserving gameplay sources and installed interiors.
- Reviewed hub overview and paving renders: roads clear, path joins consistent, crossings retain UV orientation.
- Narrowly replaced selected ground/landmark visual meshes in repo and installed level files.
- Asserted all unrelated model definitions unchanged; installed Lua, collision, geo/layout and scripts byte-identical.
- Restarted sm64coopdx to rebuild local level caches.
- Corrected Plaza lawn and concrete-over-brick priority; rebuilt/validated all four levels, reviewed hub render, narrowly installed and restarted.

## Commands run and summarized results
- BLENDER=tools/vendor/blender/Blender.app/Contents/MacOS/Blender tools/blender/run_blender.sh tools/campus/build_stage.py -- <stage> --levels-dir /tmp/sgl-ground-repair/levels --report-dir <scratch> --work <scratch>.
- Stages: hub, swamp, reitz_eng (--no-interior), lake_alice; all exports succeeded.
- Validated staged installed full levels: all 0 errors. Hub has 6 existing Goomba model-load warnings; Reitz has existing collision-budget warning (collision unchanged).
- Before copying, replace_export_meshes checked every new display-list/vertex reference exists.
- Installed output exactly matched the validated staged files.
- git diff --check: passed before installation; rerun after final handoff update.
- No new tests added or run for terrain changes.

## Remaining work
- First terrain pass compiled all four native caches successfully; user confirmed improved ground.
- Latest correction: four Plaza woodchip polygons now use lawn; concrete paths outrank brick.
- User confirmed latest lawn/path corrections look better. All four native caches compiled/loaded.
- Source/generated edits packaged on vishnu2/terrain-wall-fixes; no hosted deployment.
- Teammate continues website/game integration and branch review conflicts.

## Unresolved errors or risks
- Source/installed collision and gameplay were preserved; live ground flicker acceptance still needs user review.
- New ground clipping increases visual mesh size; build timings stayed under a minute per stage.
- Sibling has newer Reitz interior/stair work; narrow mesh installation preserves it.
- Sibling also has pending plaza material changes, not installed here; do not overwrite its source.
- Blender reports small shutdown allocations; exports/renders exit successfully.

## Exact next action
Teammate fetches origin/vishnu2/terrain-wall-fixes and integrates the fix commit. Preserve newer Reitz interior/stair work; do not blanket overwrite it with generated wf files.

## Suggested first command
`git status --short --branch`

## Scratch artifacts
- /tmp/sgl-ground-repair: exports, staged levels, per-stage reports, hub.blend, previews, backups/manifest.
- /tmp/sgl-ground-game.log: first-pass restart/native compilation log.
- /tmp/sgl-ground-correction: corrected exports, preview, staged validation, pre-correction backups.
- /tmp/sgl-ground-correction-game.log: latest runtime log.
- /tmp/sgl-core-repair: prior library core repair/export/backups.
- /tmp/sgl-depth-repair/backup: installed depth-state correction backup.
