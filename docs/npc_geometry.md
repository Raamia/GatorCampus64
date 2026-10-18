# NPC placement follows map geometry

Mascot posts are generated from named map anchors; students use collision-derived
walking graphs. Both check loaded collision before spawning and moving. A missing
floor, unsafe step, body obstruction, ceiling, or authored exclusion stops motion.
An NPC whose current position is unsafe disappears and is retried later. Mascot
chat commands remain available while its prop cannot be placed.

## Editing a map

`data/uf/npc_anchors.json` assigns each mascot post a named point in the existing
mission/map JSON, or the hub's exported arrival, plus an intentional offset. The
generator resolves the preferred post against final collision, checks its full
stroll area and nearby level objects, and searches within 3 m if necessary. An
unresolvable required post is a build failure. All 18 existing posts retain their
positions in the initial migration.

`data/uf/npc_navigation.json` contains:

- Explicit outdoor elevation bands in **game units**, selecting intended ground
  rather than guessing from roofs. Within those bands, floor heights and gentle
  slopes come from collision. Ambiguous overlapping floors are rejected. Expand
  or split the policy deliberately when a terrain change exceeds its band.
- Minimum connected coverage for Plaza of the Americas, Turlington, and
  Malachowsky Campus Green, plus minimum outdoor link counts. These are regression
  gates, not guarantees that every sidewalk remains connected.
- Optional exclusion boxes for visual-only scenery. Each has `slot`, `area`,
  `min: [x,y,z]`, and `max: [x,y,z]`, in the level's game coordinates. NPC body
  bounds must clear these boxes. Empty by default; add boxes for new props that
  should block NPCs but intentionally have no game collision.

Interior graphs retain authored floor elevations so stacked rooms remain
separate. Update that floor list in `tools/npcs/area_routes.py` when changing an
interior floor layout. Mascot stroll areas currently require nearly level ground;
the runtime can follow a gentle slope but generation deliberately rejects an
unsafe or uneven mission-guide post.

The generators share the collision queries in `tools/npcs/geometry.py` and policy
in `navigation.py`. Exact triangle/box clipping avoids treating the bounding box
of a large sloped floor as an overhead obstacle.

## Regeneration and release checks

Normal exports through `build_stage.py` and `build_interior.py` regenerate NPC
data after writing map/mission points. Scratch exports using a separate level or
report directory do not overwrite the committed navigation data.

```sh
python3 -I tools/npcs/rebuild.py
python3 -I tools/npcs/rebuild.py --check
tools/luatest/run.sh
```

Commit these outputs together with their map sources:

- `mods/sgl64/sgl_ambient_data.lua` — mascot posts and exclusions.
- `mods/sgl64/sgl_campus_npc_routes.lua` — hub routes.
- `mods/sgl64/sgl_campus_npc_areas.lua` — stage/interior routes.

Each output records a SHA-256 of its relevant collision, scripts, map/config
inputs, and generator implementation. `--check` actually regenerates and compares
the output; the receipt alone is not considered proof of geometry correctness.
The host release command checks NPC data from an archive of the **candidate
commit**, independent of the operator's working copy, before transferring source
or restarting anything. Legacy commits predating generated placements retain
their existing release behavior.

Existing mission JSON points are shared inputs, not duplicated absolute mascot
coordinates. Mission Lua still has its established point tables and geometry
checks: when a map moves those gameplay anchors, update its Lua consumers and
run the relevant `tools/luatest/check_*_points.py` checks. This change does not
silently reposition objectives, doors, or player spawns.

## Runtime diagnostics and limits

`/npcdebug` toggles a local HUD displaying mascot anchor markers/heights and the
count/latest reason for rejected geometry queries. It does not change gameplay
or send administrative commands to other players.

Runtime checks sample body support and clearance, including short swept movement;
they are bounded collision probes, not a full navigation-mesh planner. A blocked
mascot waits for another wander target, while repeatedly blocked students are
recycled. They may differ locally around moving obstacles, like the existing
client-local scenery. Generated posts and alternative placement order are
deterministic.

Validate actual traversal and performance in the engine after substantial map
changes. Offline synthetic tests cover slopes, cliffs, missing floors, thin walls,
low ceilings, wrong-floor snapping, moved/blocked anchors, exclusion volumes,
stale inputs, and coverage loss; they cannot prove frame rate or visual quality
on the production clients.
