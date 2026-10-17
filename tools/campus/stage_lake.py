"""Course 3, Lake Alice (stages.json "lake_alice", slot jrb, door 3 = Newell Hall): the stage-specific parts
of the campus generator, called from the shared stage_* modules (inside Blender unless noted):

  reserve(S)              stage_dressing.reserve: before the trees are built. Thins the generated woods
                          (TREE_KEEP: the Lake Alice woods relation 6819273 alone scatters ~2,700 trees;
                          unthinned the stage had ~110k tree triangles and 7,100 trunk-collider triangles,
                          over the static collision budget), keeps every trunk off the roads / walks /
                          trails (TREE_WAY_CLEAR_M) and opens the arrival vista (spawn -> the lake).
  build_dressing(S, ..)   stage_dressing.build: the lake-centre observation deck (design 7.4 act 1's goal,
                          on lake_alice_water.py's reserved deck site, where its north_shallows lily-pad
                          route ends), the gator nest mound on the small bog (acts 2 and 5; the bog
                          the Course 3 missions use as the nest, uf_lake_missions.lua) and six rigid
                          basking alligators on the bogs and banks (BASKING_GATORS, every act).
  lake_pickups(S, probe)  stage_pickups.lake_pickups: coins (~160, the 100-coin star needs 100), hearts,
                          1-ups, Goombas and the landmark poles (bat-cam poles, Museum Road lights, cypress).
  lake_points(...)        stage_points.lake_points: data/uf/lake_points.json, the mission anchors of every
                          design act (game_design.md 7.4) measured on the built collision.
  lake_views(S)           stage_preview.default_views: the preview cameras.

Gameplay additions that are not real Lake Alice features (game_design.md 7.4 asks for them): the
observation deck at the lake centre (Lake Alice is a no-boating wildlife sanctuary with no dock or pier,
see landmarks/lake_alice_shore.py) and the gator nest mound. The moving alligators are mission objects (Lua,
SM64 enemy stand-ins; this file exports where they go); the basking ones are original static meshes here.

Coordinates: map metres (x = east, y = north, z = up, origin Century Tower); stage coordinates =
map - stages.json centre (-1760, -660). Game units: X = (x + 1760) * 100, Y = z * 100,
Z = -(y + 660) * 100. Lake surface WATER_Z = -0.5 m (game Y -50), from landmarks/lake_alice_water.py.
Map data (c) OpenStreetMap contributors, ODbL 1.0.
"""
import hashlib
import importlib
import math
import time

STAGE = "lake_alice"

# ------------------------------------------------------------------ trees (reserve)
# keep fraction of the generated trees by zone (deterministic hash per tree id): inside the play zone,
# within TREE_SHORE_BAND_M of the lake shore (the wooded shore seen from the water), and outside the play
# zone (the visual-only margin behind the boundary walls, where the tree line hides the edge)
TREE_KEEP = {"play": 0.5, "shore": 0.7, "margin": 0.3}
TREE_SHORE_BAND_M = 25.0
TREE_WAY_CLEAR_M = {"road": 1.3, "path": 1.0}     # + half the way's width: no trunk collider on a walk
# arrival vista: trees cleared in a wedge from the spawn along its facing (length m, half width at the
# spawn, half width at the far end): Lakitu's first view shows the lake through the shore woods
SPAWN_VISTA = (95.0, 5.0, 17.0)

# ------------------------------------------------------------------ observation deck (act 1 goal)
DECK_R_IN = 4.5            # octagon inradius: the north_shallows end pad's edge is 6.3 m from the site
DECK_TOP = 0.20            # collision top (0.70 m above the water, 0.60 above the lily pads: one hop)
DECK_VIS_DROP = 0.02       # visual planks 2 cm under the collision (Mario's shadow stays visible)
DECK_SKIRT_Z0 = -3.8       # skirt walls reach below the lake bed (no swimming under the deck)
RAIL_H = 1.0               # railings on edges 2, 3, 5, 6; open: 0 (faces the pad route), 1 (the gator route
RAILED_EDGES = (2, 3, 5, 6)  # west to the bog), 4 (south-east) and 7 (north): water-jump on from a swim
PAV_POST = 1.5             # pavilion: posts at +-PAV_POST in the deck frame (sides face the pad route, so
PAV_ROOF = 2.3             # the hop from the last pad lands between two posts), hip roof over +-PAV_ROOF
PAV_EAVE = 2.8             # eave above the deck top (a double jump from the deck)
PAV_RISE = 1.0             # apex above the eave (23.5 degrees: walkable)
PAV_FASCIA = 0.18
# act 1's star (deck frame: u = towards the last lily pad): on the far side of the deck (the open edge 4),
# 1.0 m clear of the pavilion roof's eave (+-PAV_ROOF), so neither the star's arc in nor its final 2.1 m rise
# (vanilla bhvStarSpawnCoordinates) passes through the roof; it arcs in from over the open water beyond
STAR_U_M = -3.3
STAR_UP_M = 1.2            # over the deck floor (the Swamp's STAR_UP_M)
STAR_FROM_U_M = -9.5       # star_from: over the water 5 m out from edge 4 ...
STAR_FROM_Z_M = 3.0        # ... 3 m up
# ------------------------------------------------------------------ gator nest (acts 2 and 5)
# the small bog (OSM w118249560, lake_alice_water island 3): the missions' gator nest. The mound stands 2.6 m
# west of the module's island_3_top spot, so that spot (the missions' nest probe / star) stays the bog floor and
# the gator line arriving at the bog's south shore stays clear
NEST_SPOT = (-1723.0, -529.3)
NEST_ISLAND = 2                                 # lake_alice_water.ISLANDS index (0-based)
NEST_R0, NEST_R1, NEST_H = 1.4, 0.7, 0.32       # mound: base radius, top radius, height above the bog

# ------------------------------------------------------------------ mission anchors
# act 2's snapping big gators: their 18 m lunge (uf_lake_missions.lua SGL_LAKE_GATOR.LUNGE) round these homes
# covers gators 3-16 of the line, so a fall anywhere past the first two hops can cost a bite
BIG_GATOR_SPOTS = [((-1714.0, -556.0), "open water south of the small bog (between it and the deep hole deep_1): "
                                       "covers the last gators before the nest"),
                   ((-1732.1, -616.9), "7 m west of the gator line by gators 3-7 (the line's first leg, north of "
                                       "the lily-pad end)"),
                   ((-1704.0, -590.0), "east of the line's bend, on the north-west rim of the deep hole deep_1: "
                                       "covers gators 8-11")]
# act 1's lurking big gators: beside the middle of the north_shallows pad line, on alternate sides
# (pad index 0-based, side +1 = left of the route), LURK_OFFSETS_M out from that pad, in open water at least
# LURK_MIN_DEPTH_M deep and LURK_PAD_CLEAR_M from every lily pad's edge (their Lua patrol circle is 3 m)
ACT1_LURK = ((4, 1), (10, -1))
LURK_OFFSETS_M = (10.0, 11.0, 12.0, 9.0, 13.0, 14.0)
LURK_MIN_DEPTH_M = 1.6
LURK_PAD_CLEAR_M = 6.0
LURK_DECK_CLEAR_M = 12.0
NEST_BANK = (-1724.0, -507.0)   # the north bank above the small bog (end of the act 5 carry walk, a throw spot)
# design act 6 red coins (8, game_design 7.4 act 6): pads, bat-house roofs, the garden trellis, a cypress
# knee, the boardwalk underside. No yellow coin is placed on these spots (stage pickups skip them).
RED_COIN_PADS = [("north_shallows", 5), ("east_marsh", 7), ("south_arm", 4)]
RED_COIN_KNEE_NEAR = (-1846.0, -793.0)   # the knee of the cypress nearest this (the south_arm pads, south-west arm)
SHORE_CHECKPOINTS = 16     # shoreline checkpoints all round the lake (on the bank, 4 m out of the water)
BASK_ISLAND_1 = (-1812.0, -607.0, -0.1)   # west bog basking spot (its top spot carries a coin line)
# ------------------------------------------------------------------ basking gators (every act, level geometry)
# Rigid, original low-poly alligators lying still on the bogs and the banks (Lake Alice's gators bask for hours):
# level geometry, so every act and free roam has them; a low collision body you can walk onto. The moving gators
# of acts 1 and 2 are Lua stand-ins (uf_lake_missions.lua). (map xy, snout heading (compass deg), length m,
# note); a waterline spot (gator_spots.basking_waterline) is pulled BASK_BANK_BACK_M up the bank so the snout
# rests at the water's edge.
BASKING_GATORS = [((-1812.0, -607.0), 120.0, 3.0, "west bog (act 1's route), snout to the lake centre", False),
                  ((-1660.0, -497.0), 200.0, 3.4, "north-east bog, east of its coin ring", False),
                  ((-1781.26, -552.33), 130.3, 2.8, "north shore waterline (bask_gator_14)", True),
                  ((-1648.53, -703.17), 323.2, 3.2, "south-east shore waterline (bask_gator_08)", True),
                  ((-1914.03, -722.64), 355.2, 2.9, "south-west shore by the Baughman lawn (bask_gator_02)", True),
                  ((-1620.37, -465.03), 195.8, 3.0, "north-east cove waterline (bask_gator_12)", True)]
BASK_BANK_BACK_M = 1.0
# body profile of a 3.2 m gator (scaled to its length): (u = metres forward of the middle, half width, height)
GATOR_PROFILE = [(1.62, 0.07, 0.09), (1.35, 0.13, 0.12), (1.05, 0.19, 0.17), (0.80, 0.22, 0.20),
                 (0.50, 0.33, 0.27), (0.05, 0.37, 0.31), (-0.45, 0.31, 0.28), (-0.80, 0.21, 0.22),
                 (-1.20, 0.13, 0.16), (-1.58, 0.04, 0.08)]
GATOR_COL_STATIONS = (0, 2, 4, 6, 8)     # profile rows of the collision body (snout tip .. mid tail)
GATOR_TAIL_CURL = 0.22                   # the tail tip's sideways curl (m at 3.2 m)


def _W():
    return importlib.import_module("landmarks.lake_alice_water")


def _h01(*k):
    s = ":".join(str(v) for v in k)
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def _seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L = dx * dx + dy * dy
    if L == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def _pip(pt, poly):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _extras(S, slug):
    return next((e for e in S.landmark_entries if e.get("slug") == slug), None) or {}


def bearing(a, b):
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def vista_poly(spawn):
    """Arrival vista wedge (map metres) from spawn {"pos", "facing"}."""
    L, w0, w1 = SPAWN_VISTA
    (x, y), f = spawn["pos"], math.radians(spawn["facing"])
    fx, fy = math.sin(f), math.cos(f)
    sx, sy = fy, -fx
    return [(x + sx * w0, y + sy * w0), (x + fx * L + sx * w1, y + fy * L + sy * w1),
            (x + fx * L - sx * w1, y + fy * L - sy * w1), (x - sx * w0, y - sy * w0)]


def tree_plan(data, removed, replaced_ways, spawn):
    """Pure Python (no Blender): -> ({tree id: reason}, counts) for the trees to remove. reason "trail" /
    "vista" / "thinned"; trees in the lake are left to stage_nature (it drops everything in the lake's
    ground hole)."""
    W = _W()
    px0, py0, px1, py1 = data["play"]
    G = 20.0
    grid = {}

    def add_way(pts, hw):
        for a, b in zip(pts, pts[1:]):
            x0, x1 = sorted((a[0], b[0]))
            y0, y1 = sorted((a[1], b[1]))
            for i in range(int(math.floor((x0 - hw) / G)), int(math.floor((x1 + hw) / G)) + 1):
                for j in range(int(math.floor((y0 - hw) / G)), int(math.floor((y1 + hw) / G)) + 1):
                    grid.setdefault((i, j), []).append((tuple(a), tuple(b), hw))
    for r in data["roads"]:
        if r["id"] not in replaced_ways:
            add_way(r["pts"], r["width"] / 2 + TREE_WAY_CLEAR_M["road"])
    for p in data["paths"]:
        if p["id"] not in replaced_ways:
            add_way(p["pts"], p["width"] / 2 + TREE_WAY_CLEAR_M["path"])
    vista = vista_poly(spawn) if spawn else None
    out, counts = {}, {"in_lake": 0, "trail": 0, "vista": 0, "thinned": 0, "kept_play": 0, "kept_shore": 0,
                       "kept_margin": 0}
    for t in data["trees"]:
        tid = t["id"]
        if tid in removed:
            continue
        x, y = t["pt"]
        if W.in_lake(x, y):
            counts["in_lake"] += 1
            continue
        segs = grid.get((int(math.floor(x / G)), int(math.floor(y / G))), ())
        if any(_seg_dist((x, y), a, b) < hw for a, b, hw in segs):
            out[tid] = "trail"
            counts["trail"] += 1
            continue
        if vista and _pip((x, y), vista):
            out[tid] = "vista"
            counts["vista"] += 1
            continue
        if not (px0 < x < px1 and py0 < y < py1):
            zone = "margin"
        elif W.shore_dist(x, y, TREE_SHORE_BAND_M + 1.0) < TREE_SHORE_BAND_M:
            zone = "shore"
        else:
            zone = "play"
        if _h01("lake_thin", tid) < TREE_KEEP[zone]:
            counts["kept_" + zone] += 1
        else:
            out[tid] = "thinned"
            counts["thinned"] += 1
    return out, counts


def reserve(S):
    """stage_dressing.reserve for Lake Alice: thin the woods, clear the trails and the arrival vista.
    -> the tree ids removed (also added to S.removed_points)."""
    plan, counts = tree_plan(S.data, S.removed_points | S.replaced_ids, S.replaced_ways | S.replaced_ids,
                             getattr(S, "spawn", None))
    S.removed_points.update(plan)
    S.stats["lake_tree_plan"] = dict(counts, keep_fraction=TREE_KEEP, shore_band_m=TREE_SHORE_BAND_M,
                                     vista=SPAWN_VISTA)
    print(f"SGL: lake trees: {counts}")
    return sorted(plan)


# ------------------------------------------------------------------ geometry helpers (Blender)
def _prism(acc, ring, z0, z1, side, top=None, bottom=None):
    """Closed prism over a CCW ring (stage metres): outward walls, optional top / bottom caps."""
    for a, b in zip(ring, ring[1:] + ring[:1]):
        acc.wall(a, b, z0, z1, side)
    if top:
        acc.flat(ring, z1, top)
    if bottom:
        acc.flat(ring, z0, bottom, down=True)


def _ngon(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n))
            for k in range(n)]


def deck_frame():
    """(centre map xy, theta0): theta0 = maths angle of edge 0's outward normal = towards the last
    north_shallows lily pad (the hop onto the deck)."""
    W = _W()
    c = W.LAKE_CENTER_DECK_SITE
    end = W.LANDMARKS[0]["spots"].get("lily_route_end", (c[0] - 5.4, c[1] + 7.5))
    return c, math.atan2(end[1] - c[1], end[0] - c[0])


def deck_octagon_map():
    """Deck octagon (map metres, CCW); edge k has its outward normal at theta0 + k * 45 degrees."""
    (cx, cy), t0 = deck_frame()
    rc = DECK_R_IN / math.cos(math.pi / 8)
    return [(cx + rc * math.cos(t0 - math.pi / 8 + k * math.pi / 4), cy + rc * math.sin(t0 - math.pi / 8 + k * math.pi / 4))
            for k in range(8)]


def deck_point(u, v=0.0):
    """Map metres of the point (u, v) in the deck frame (u towards the last lily pad, v to its left)."""
    (cx, cy), t0 = deck_frame()
    return (cx + u * math.cos(t0) - v * math.sin(t0), cy + u * math.sin(t0) + v * math.cos(t0))


def act1_lurk_spots():
    """Pure Python (no Blender; tools/luatest/check_lake_points.py uses it too): act 1's lurking big gators'
    homes -> [((x, y) map metres, note)] (ACT1_LURK, LURK_OFFSETS_M, the first offset that is open water
    >= LURK_MIN_DEPTH_M deep, off every bog, LURK_PAD_CLEAR_M from every lily pad's edge and
    LURK_DECK_CLEAR_M from the deck site)."""
    W = _W()
    pads_all = W.LANDMARKS[0]["markers"]["lily_pads"]
    route = sorted((p for p in pads_all if p["route"] == "north_shallows"), key=lambda p: p["i"])
    deck = W.LAKE_CENTER_DECK_SITE
    out = []
    for i, side in ACT1_LURK:
        a, b = route[max(0, i - 1)]["pos_m"], route[min(len(route) - 1, i + 1)]["pos_m"]
        L = math.dist(a[:2], b[:2])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        lx, ly = -uy, ux                                   # left of the route
        p0 = route[i]["pos_m"]
        found = None
        for off in LURK_OFFSETS_M:
            q = (p0[0] + side * lx * off, p0[1] + side * ly * off)
            if W.water_depth(*q) < LURK_MIN_DEPTH_M or W.island_at(*q) is not None:
                continue
            if any(math.dist(q, p["pos_m"][:2]) - p["r_m"] < LURK_PAD_CLEAR_M for p in pads_all):
                continue
            if math.dist(q, deck) < LURK_DECK_CLEAR_M:
                continue
            found = (q, off)
            break
        if found is None:
            raise ValueError(f"act 1 lurk gator by pad {i}: no open water spot at {LURK_OFFSETS_M} m")
        (q, off) = found
        out.append(((round(q[0], 2), round(q[1], 2)),
                    f"lurking big gator home, {off:.0f} m to the {'left' if side > 0 else 'right'} of north_shallows "
                    f"pad {i} (open water; the pads are the safe way)"))
    return out


def _deck(S, probe, vis, col):
    """Lake-centre observation deck (map site from lake_alice_water.LAKE_CENTER_DECK_SITE)."""
    (mcx, mcy), t0 = deck_frame()
    cx, cy = S.T((mcx, mcy))
    oct_ = [S.T(p) for p in deck_octagon_map()]
    bed = probe.floor(cx, cy, 0.0)
    bed = -3.1 if bed is None else bed
    # collision: solid block from below the bed to the deck top
    _prism(col, oct_, DECK_SKIRT_Z0, DECK_TOP, "COL default", top="COL default")
    # visual: planks, fascia, piles
    vis.flat(oct_, DECK_TOP - DECK_VIS_DROP, "door_wood")
    for a, b in zip(oct_, oct_[1:] + oct_[:1]):
        vis.wall(a, b, DECK_TOP - 0.32, DECK_TOP - DECK_VIS_DROP, "dark_trim")
    rc = DECK_R_IN / math.cos(math.pi / 8)
    from stage_nature import trunk
    for k in range(8):
        a = t0 - math.pi / 8 + k * math.pi / 4
        px, py = cx + (rc - 0.35) * math.cos(a), cy + (rc - 0.35) * math.sin(a)
        trunk(vis, px, py, 0.16, bed - 0.3, DECK_TOP - 0.3, 5, "dark_trim", f"deckpile{k}")
    # railings (collision: a thin solid rail you can also balance on)
    rails = []
    for k in RAILED_EDGES:
        a, b = oct_[k], oct_[(k + 1) % 8]
        L = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = uy, -ux                                   # outward (CCW ring: right of a->b)
        inset = 0.10
        a2 = (a[0] - nx * inset + ux * 0.05, a[1] - ny * inset + uy * 0.05)
        b2 = (b[0] - nx * inset - ux * 0.05, b[1] - ny * inset - uy * 0.05)
        th = 0.06
        ring = [(a2[0] + nx * th, a2[1] + ny * th), (b2[0] + nx * th, b2[1] + ny * th),
                (b2[0] - nx * th, b2[1] - ny * th), (a2[0] - nx * th, a2[1] - ny * th)]
        _prism(col, ring, DECK_TOP, DECK_TOP + RAIL_H, "COL default", top="COL default")
        for zr0, zr1 in ((DECK_TOP + RAIL_H - 0.08, DECK_TOP + RAIL_H), (DECK_TOP + 0.45, DECK_TOP + 0.52)):
            _prism(vis, ring, zr0, zr1, "door_wood", top="door_wood", bottom="door_wood")
        for p in (a2, b2, ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)):
            _prism(vis, _ngon(p[0], p[1], 0.07, 4, math.atan2(uy, ux) + math.pi / 4), DECK_TOP - 0.05,
                   DECK_TOP + RAIL_H - 0.08, "door_wood")
        rails.append(k)
    # pavilion: four posts, a hip roof (walkable 23.5 degree slopes, a ceiling underneath); frame u = t0
    c, s = math.cos(t0), math.sin(t0)

    def P(u, v):
        return (cx + c * u - s * v, cy + s * u + c * v)
    ze = DECK_TOP + PAV_EAVE
    for su, sv in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        q = [P(su * PAV_POST - 0.11, sv * PAV_POST - 0.11), P(su * PAV_POST + 0.11, sv * PAV_POST - 0.11),
             P(su * PAV_POST + 0.11, sv * PAV_POST + 0.11), P(su * PAV_POST - 0.11, sv * PAV_POST + 0.11)]
        _prism(col, q, DECK_TOP, ze - PAV_FASCIA, "COL default")
        _prism(vis, q, DECK_TOP - 0.05, ze - PAV_FASCIA, "door_wood")
    eave = [P(PAV_ROOF, -PAV_ROOF), P(PAV_ROOF, PAV_ROOF), P(-PAV_ROOF, PAV_ROOF), P(-PAV_ROOF, -PAV_ROOF)]
    apex = (cx, cy, ze + PAV_RISE)
    for acc, mat, fas in ((col, "COL default", "COL default"), (vis, "roof_dark", "white_trim")):
        for a, b in zip(eave, eave[1:] + eave[:1]):
            acc.poly([(a[0], a[1], ze), (b[0], b[1], ze), apex], mat)
            acc.wall(a, b, ze - PAV_FASCIA, ze, fas)
        acc.flat(eave, ze - PAV_FASCIA, fas if acc is vis else "COL default", down=True)
    return {"map_m": [round(mcx, 2), round(mcy, 2)], "top_m": DECK_TOP, "inradius_m": DECK_R_IN,
            "edge0_bearing_deg": round((90.0 - math.degrees(t0)) % 360.0, 1), "railed_edges": rails,
            "open_edges": [k for k in range(8) if k not in RAILED_EDGES], "bed_m": round(bed, 2),
            "pavilion": {"eave_m": round(ze, 2), "apex_m": round(ze + PAV_RISE, 2), "roof_half_m": PAV_ROOF,
                         "post_half_m": PAV_POST},
            "octagon_m": [[round(x, 2), round(y, 2)] for x, y in deck_octagon_map()]}


def _nest(S, probe, vis, col):
    """Gator nest mound on the small bog (NEST_SPOT)."""
    mx, my = NEST_SPOT
    x, y = S.T((mx, my))
    fz = probe.floor(x, y, 2.0)
    fz = -0.06 if fz is None else fz
    n = 8
    r0 = _ngon(x, y, NEST_R0, n, 0.2)
    r1 = _ngon(x, y, NEST_R1, n, 0.2)
    z0, z1, zc = fz - 0.06, fz + NEST_H, fz + NEST_H + 0.08
    for acc, side, top in ((col, "COL default", "COL default"), (vis, "bronze", "door_wood")):
        dz = 0.0 if acc is col else -0.02
        for i in range(n):
            j = (i + 1) % n
            acc.poly([(r0[i][0], r0[i][1], z0 + dz), (r0[j][0], r0[j][1], z0 + dz), (r1[j][0], r1[j][1], z1 + dz),
                      (r1[i][0], r1[i][1], z1 + dz)], side)
            acc.poly([(r1[i][0], r1[i][1], z1 + dz), (r1[j][0], r1[j][1], z1 + dz), (x, y, zc + dz)], top)
    # three eggs in the hollow (visual)
    for k in range(3):
        a = 0.6 + k * 2 * math.pi / 3
        ex, ey = x + 0.32 * math.cos(a), y + 0.32 * math.sin(a)
        ring = _ngon(ex, ey, 0.11, 6, a)
        _prism(vis, ring, zc - 0.05, zc + 0.12, "white_trim", top="white_trim")
    # a ring of sticks round the rim (visual)
    for k in range(10):
        a = k * 2 * math.pi / 10 + 0.15
        p0 = (x + (NEST_R1 + 0.05) * math.cos(a), y + (NEST_R1 + 0.05) * math.sin(a))
        p1 = (x + (NEST_R0 - 0.2) * math.cos(a + 0.45), y + (NEST_R0 - 0.2) * math.sin(a + 0.45))
        zz0 = fz + NEST_H - 0.02
        zz1 = fz + 0.05
        w = 0.05
        stick = [(p0[0], p0[1], zz0 + w), (p1[0], p1[1], zz1 + w), (p1[0], p1[1], zz1 + 2 * w), (p0[0], p0[1], zz0 + 2 * w)]
        vis.poly(stick, "door_wood")
        vis.poly(stick[::-1], "door_wood")
    return {"map_m": [round(mx, 2), round(my, 2)], "bog_floor_m": round(fz, 2), "top_m": round(zc, 2),
            "radius_m": NEST_R0, "island": "small bog (w118249560)",
            "note": "gator nest mound (mud + sticks, three eggs) on the small bog: the \"island nest\" of design "
                    "acts 2 and 5 (the bog uf_lake_missions.lua uses); the mother gator goes beside it"}


def _gator(S, probe, vis, col, mpos, heading, length, name, waterline):
    """One basking alligator (original rigid low-poly design): a lofted body that follows the ground under it
    (head, eyes, a jaw line of teeth, four splayed legs, a curled tail); collision: a low body you can walk
    onto. -> report dict, or None (no floor / something in the way)."""
    sc = length / 3.2
    h = math.radians(heading)
    fx, fy = math.sin(h), math.cos(h)          # snout direction (map)
    lx, ly = -fy, fx                           # left
    mx, my = mpos
    if waterline:                              # up the bank: the snout rests at the water's edge
        mx, my = mx - fx * BASK_BANK_BACK_M, my - fy * BASK_BANK_BACK_M
    x0, y0 = S.T((mx, my))

    def curl(u):
        t = max(0.0, (-0.45 - u) / 1.13)
        return GATOR_TAIL_CURL * t * t

    def centre(u):
        return x0 + fx * u * sc + lx * curl(u) * sc, y0 + fy * u * sc + ly * curl(u) * sc
    bases = []
    for u, hw, hh in GATOR_PROFILE:
        cx, cy = centre(u)
        fz = probe.floor(cx, cy, 1.0)
        if fz is None:
            return None
        bases.append(fz)
    # nothing in the way along the body (a trunk collider, a fence, a wall), and no step under it
    if max(bases) - min(bases) > 0.8 * sc:
        return None
    tx, ty = centre(GATOR_PROFILE[-1][0])
    hit = probe.ray(tx, ty, max(bases) + 0.2, fx, fy, length)
    if hit is not None and hit < length - 0.05:
        return None

    def P(i, v, z):
        u, hw, hh = GATOR_PROFILE[i]
        cx, cy = centre(u)
        return (cx + lx * v * sc, cy + ly * v * sc, bases[i] + z * sc - 0.03)

    def face(acc, pts, mat, ref):
        """Polygon with its normal pointing away from ref (outside the body)."""
        (ax, ay, az), (bx, by, bz), (cx_, cy_, cz) = pts[0], pts[1], pts[2]
        n = ((by - ay) * (cz - az) - (bz - az) * (cy_ - ay), (bz - az) * (cx_ - ax) - (bx - ax) * (cz - az),
             (bx - ax) * (cy_ - ay) - (by - ay) * (cx_ - ax))
        m = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        if n[0] * (m[0] - ref[0]) + n[1] * (m[1] - ref[1]) + n[2] * (m[2] - ref[2]) < 0:
            pts = pts[::-1]
        acc.poly(pts, mat)

    def axis(i):
        u, hw, hh = GATOR_PROFILE[i]
        cx, cy = centre(u)
        return (cx, cy, bases[i] + hh * sc * 0.45)
    # ---- visual body: six-point cross-sections; the back band dark, the flanks olive
    sec = lambda hw, hh: [(-0.75 * hw, 0.0), (-hw, 0.45 * hh), (-0.5 * hw, hh), (0.5 * hw, hh), (hw, 0.45 * hh),
                          (0.75 * hw, 0.0)]
    n = len(GATOR_PROFILE)
    for i in range(n - 1):
        A = [P(i, v, z) for v, z in sec(GATOR_PROFILE[i][1], GATOR_PROFILE[i][2])]
        B = [P(i + 1, v, z) for v, z in sec(GATOR_PROFILE[i + 1][1], GATOR_PROFILE[i + 1][2])]
        ref = tuple((a + b) / 2 for a, b in zip(axis(i), axis(i + 1)))
        for k in range(5):
            face(vis, [A[k], A[k + 1], B[k + 1], B[k]], "dark_trim" if k == 2 else "pond_bed", ref)
    for i, d in ((0, 1.0), (n - 1, -1.0)):                          # snout and tail-tip caps
        ring = [P(i, v, z) for v, z in sec(GATOR_PROFILE[i][1], GATOR_PROFILE[i][2])]
        a = axis(i)
        face(vis, ring, "pond_bed", (a[0] - fx * d, a[1] - fy * d, a[2]))
    # ---- eyes (yellow bumps) and the jaw's teeth
    ui = 2
    u, hw, hh = GATOR_PROFILE[ui]
    for sd in (1, -1):
        cx, cy = centre(u)
        ex, ey = cx + lx * sd * 0.6 * hw * sc, cy + ly * sd * 0.6 * hw * sc
        ez = bases[ui] + hh * sc - 0.04
        r = 0.045 * sc
        sq = [(ex + fx * r, ey + fy * r, ez), (ex + lx * r, ey + ly * r, ez), (ex - fx * r, ey - fy * r, ez),
              (ex - lx * r, ey - ly * r, ez)]
        apex = (ex, ey, ez + 0.07 * sc)
        for a, b in zip(sq, sq[1:] + sq[:1]):
            face(vis, [a, b, apex], "road_paint", (ex, ey, ez - 0.05))
    for sd in (1, -1):
        for k in range(4):
            ua = 1.12 + k * 0.11
            hwu = 0.19 + (ua - 1.05) / (1.35 - 1.05) * (0.13 - 0.19)
            hhu = 0.17 + (ua - 1.05) / (1.35 - 1.05) * (0.12 - 0.17)
            ba = bases[2] + (bases[1] - bases[2]) * (ua - 1.05) / 0.30
            cx, cy = x0 + fx * ua * sc, y0 + fy * ua * sc
            v = sd * (hwu * 1.01) * sc
            z1 = ba + 0.45 * hhu * sc - 0.03
            t = [(cx + lx * v, cy + ly * v, z1), (cx + fx * 0.07 * sc + lx * v, cy + fy * 0.07 * sc + ly * v, z1),
                 (cx + fx * 0.035 * sc + lx * v, cy + fy * 0.035 * sc + ly * v, z1 - 0.05 * sc)]
            face(vis, t, "white_trim", (cx, cy, z1))
    # ---- legs: low splayed boxes, the feet forward
    for ul, fwd in ((0.45, 0.10), (-0.42, -0.04)):
        i = min(range(n), key=lambda j: abs(GATOR_PROFILE[j][0] - ul))
        hw = GATOR_PROFILE[i][1]
        for sd in (1, -1):
            cx, cy = centre(ul)
            r0, r1 = 0.8 * hw, hw + 0.30
            q = [(r0, -0.07), (r1, fwd - 0.08), (r1, fwd + 0.08), (r0, 0.07)]
            ring = [(cx + lx * sd * a * sc + fx * b * sc, cy + ly * sd * a * sc + fy * b * sc) for a, b in q]
            area = sum(p[0] * q2[1] - q2[0] * p[1] for p, q2 in zip(ring, ring[1:] + ring[:1]))
            if area < 0:
                ring.reverse()
            zb = bases[i] - 0.03
            _prism(vis, ring, zb, zb + 0.10 * sc, "pond_bed", top="pond_bed")
    # ---- collision: a low body (vertical flanks, the back on top), sunk 0.1 m into the ground
    cs = GATOR_COL_STATIONS
    for i, j in zip(cs, cs[1:]):
        (ui_, hwi, hhi), (uj, hwj, hhj) = GATOR_PROFILE[i], GATOR_PROFILE[j]
        A = [P(i, -hwi, -0.10 / sc), P(i, -hwi, hhi - 0.04 / sc), P(i, hwi, hhi - 0.04 / sc), P(i, hwi, -0.10 / sc)]
        B = [P(j, -hwj, -0.10 / sc), P(j, -hwj, hhj - 0.04 / sc), P(j, hwj, hhj - 0.04 / sc), P(j, hwj, -0.10 / sc)]
        ref = tuple((a + b) / 2 for a, b in zip(axis(i), axis(j)))
        for k in range(3):
            face(col, [A[k], A[k + 1], B[k + 1], B[k]], "COL default", ref)
    for i, d in ((cs[0], 1.0), (cs[-1], -1.0)):
        u, hw, hh = GATOR_PROFILE[i]
        ring = [P(i, -hw, -0.10 / sc), P(i, -hw, hh - 0.04 / sc), P(i, hw, hh - 0.04 / sc), P(i, hw, -0.10 / sc)]
        a = axis(i)
        face(col, ring, "COL default", (a[0] - fx * d, a[1] - fy * d, a[2]))
    top = max(b + hh * sc for b, (_, _, hh) in zip(bases, GATOR_PROFILE))
    return {"name": name, "map_m": [round(mx, 2), round(my, 2)], "heading_deg": heading, "length_m": length,
            "floor_m": [round(min(bases), 2), round(max(bases), 2)], "top_m": round(top, 2), "waterline": waterline}


def build_dressing(S, probe, avoid=()):
    """stage_dressing.build for Lake Alice: the observation deck and the nest. Sets S.lake_dressing;
    returns [] (no lamp poles: the Museum Road lights are landmark poles, placed by lake_pickups)."""
    vis = S.acc("Dressing visual", collision=False)
    col = S.acc("Dressing collision", render=False)
    rep = {"observation_deck": _deck(S, probe, vis, col), "nest": _nest(S, probe, vis, col)}
    gators, skipped = [], []
    for k, (pos, heading, length, note, waterline) in enumerate(BASKING_GATORS):
        g = _gator(S, probe, vis, col, pos, heading, length, f"basking_gator_{k}", waterline)
        if g is None:
            skipped.append({"name": f"basking_gator_{k}", "map_m": list(pos), "why": "no floor or blocked"})
            print(f"SGL: lake dressing: basking gator {k} at {pos} skipped (no floor or something in the way)")
        else:
            gators.append(dict(g, note=note))
    rep["basking_gators"] = gators
    rep["basking_gators_skipped"] = skipped
    S.stats["dressing"] = rep
    S.lake_dressing = rep
    print(f"SGL: lake dressing: observation deck at {rep['observation_deck']['map_m']} (top "
          f"{DECK_TOP} m, bed {rep['observation_deck']['bed_m']} m), nest on the small bog at {rep['nest']['map_m']}, "
          f"{len(gators)} basking gators ({len(skipped)} skipped)")
    return []


# ------------------------------------------------------------------ pickups
def red_coin_cypress(S):
    """Index of the bald cypress whose first knee carries act 6's red coin (nearest RED_COIN_KNEE_NEAR)."""
    W = _W()
    cyp = (_extras(S, "lake_alice_water").get("markers", {}) or W.LANDMARKS[0]["markers"]).get("cypress", [])
    cands = [(math.dist(t["pos_m"][:2], RED_COIN_KNEE_NEAR), i) for i, t in enumerate(cyp) if t["knees_m"]]
    return min(cands)[1] if cands else None


def red_coin_spots(S):
    """The 8 design act 6 red-coin spots (map metres, z = the floor / surface): [(name, (x, y, z), note)]."""
    W = _W()
    wm = _extras(S, "lake_alice_water").get("markers", {}) or W.LANDMARKS[0]["markers"]
    bats = _extras(S, "bat_barns").get("spots", {})
    field = _extras(S, "bat_house_field").get("spots", {})
    bw = _extras(S, "lake_boardwalks").get("spots", {})
    out = []
    pads = {(p["route"], p["i"]): p for p in wm.get("lily_pads", [])}
    for route, i in RED_COIN_PADS:
        p = pads.get((route, i))
        if p:
            out.append((f"rc_lily_pad_{route}_{i}", tuple(p["pos_m"]), f"lily pad {i} of the {route} hop route "
                                                                       f"(r {p['r_m']} m)"))
    for k, note in (("barn2010_roof_peak", "2010 Bat Barn cross-gable peak (9 m): bat-cam pole -> roof"),
                    ("barn2017_roof_apex", "2017 bat barn hip-roof apex (9 m)")):
        if k in bats:
            out.append(("rc_" + k, tuple(bats[k]), note))
    if "garden_arbor_top" in field:
        out.append(("rc_garden_trellis", tuple(field["garden_arbor_top"]), "Bat House Gardens arbor top (2.6 m)"))
    ci = red_coin_cypress(S)
    if ci is not None:
        out.append(("rc_cypress_knee", tuple(wm["cypress"][ci]["knees_m"][0]),
                    f"top of a knee of bald cypress {ci + 1} (visual knee poking out of the wading shallows; the "
                    "coin floats there, the floor is the shallow bed)"))
    if "boardwalk_underside" in bw:
        out.append(("rc_boardwalk_underside", tuple(bw["boardwalk_underside"]),
                    "at the water surface under the north boardwalk (swim under the deck)"))
    return out


def lake_pickups(S, probe):
    """-> (items, skipped) for Lake Alice (stage_pickups.Placer, every item checked on the collision):
      coins: one over every hop lily pad except the red-coin pads (the act 1 breadcrumbs), rings in the four
        deep holes (dive for them), the observation deck's entrances, the north boardwalk and the
        footbridge, the bat-house field, the gardens' raised beds, the barn roofs (not on the red-coin
        peaks), the lakeshore trail, the Museum Road sidewalk, the bog islands, three cypress knees, the
        Baughman lawn and aisle roofs, the east overlook and the marsh shallows (~160);
      hearts: observation deck, north boardwalk, Baughman lawn, east overlook steps, north-east bog;
      1-ups: the pavilion roof apex, the bottom of the deepest hole (-5 m), the 2017 barn's east add-on box;
      Goombas on land only (bat-house field, lakeshore trail, Baughman lawn, east shore), >= 15 m from water;
      poles: the bat-cam poles, the 8 Museum Road street lights and the 16 bald cypress trunks."""
    import stage_pickups as SP
    W = _W()
    P = SP.Placer(S, probe)
    wm = _extras(S, "lake_alice_water").get("markers", {})
    ws = _extras(S, "lake_alice_water").get("spots", {})
    bats = _extras(S, "bat_barns")
    bs = bats.get("spots", {})
    bc = _extras(S, "baughman_center")
    bcs = bc.get("spots", {})
    bw = _extras(S, "lake_boardwalks").get("spots", {})
    road = _extras(S, "museum_road_edge")
    rs = road.get("spots", {})
    field = _extras(S, "bat_house_field").get("spots", {})
    dres = getattr(S, "lake_dressing", None) or {}
    red = [p for _, p, _ in red_coin_spots(S)]

    def near_red(p, r=1.2):
        return any(math.dist(p[:2], q[:2]) < r and abs((p[2] if len(p) > 2 else 0) - q[2]) < 2.0 for q in red)

    # ---- act 1 breadcrumbs: a coin over every hop pad (not the red-coin pads)
    for pad in wm.get("lily_pads", []):
        p = tuple(pad["pos_m"])
        if near_red(p):
            continue
        P.coin(f"lily pad coin {pad['route']} {pad['i']:02d}", p)
    # ---- the deep holes: a ring each on the bed; a 1-up at the bottom of the deepest
    deep = sorted(wm.get("deep_spots_m", []), key=lambda d: d[2])
    for k, d in enumerate(wm.get("deep_spots_m", [])):
        P.coin_ring(f"deep hole {k + 1} coins", (d[0] + 4.0, d[1], d[2]))
    if deep:
        P.one_up("1-up bottom of the deepest hole", tuple(deep[0]))
    # ---- observation deck: a coin at the open edges (not edge 4: act 1's star waits there), a heart, the 1-up on
    # the pavilion roof apex
    od = dres.get("observation_deck")
    if od:
        (cx, cy), t0 = deck_frame()
        for k in (0, 1, 7):
            a = t0 + k * math.pi / 4
            P.coin(f"deck coin edge {k}", (cx + 3.3 * math.cos(a), cy + 3.3 * math.sin(a), DECK_TOP))
        a = t0 + math.pi / 4
        P.heart("heart observation deck", (cx + 3.3 * math.cos(a) * 0.95, cy + 3.3 * math.sin(a) * 0.95, DECK_TOP))
        P.one_up("1-up observation deck pavilion roof", (cx, cy, od["pavilion"]["apex_m"]))
    # ---- north boardwalk + its bay, the lakeshore trail to it, the kiosk roof
    if "north_boardwalk_mid" in bw:
        axis = _extras(S, "lake_boardwalks").get("markers", {}).get("north_boardwalk_axis_m")
        f = bearing(axis[0], axis[1]) if axis else 60.0
        P.coin_line("north boardwalk coins", bw["north_boardwalk_mid"], f)
    if "north_boardwalk_west_end" in bw:
        P.heart("heart north boardwalk (west end)", bw["north_boardwalk_west_end"])
    if "kiosk_roof" in rs:
        P.coin("kiosk roof coin", rs["kiosk_roof"])
    for wid in ("w427713644", "w427713645"):
        way = next((p for p in S.data["paths"] if p["id"] == wid), None)
        if not way:
            continue
        pts = way["pts"]
        Ltot = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        for t in (0.3, 0.7) if Ltot > 30 else (0.5,):
            s, acc = t * Ltot, 0.0
            for a, b in zip(pts, pts[1:]):
                L = math.dist(a, b)
                if acc + L >= s and L > 0:
                    u = (s - acc) / L
                    P.coin_line(f"lakeshore trail coins {wid} {int(t * 100)}",
                                (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, 0.0), bearing(a, b))
                    break
                acc += L
    # ---- Museum Road lake-side sidewalk: lines between the street lights
    lights = [q["base_m"] for q in road.get("markers", {}).get("poles", [])]
    for k in (1, 3, 5):
        if k + 1 < len(lights):
            a, b = lights[k], lights[k + 1]
            P.coin_line(f"museum road coins {k}", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0), bearing(a, b))
    # ---- bat-house field (the landing zone): a line from the spawn, a ring by the barns; the gardens
    sp = getattr(S, "spawn", None)
    if sp:
        f = math.radians(sp["facing"])
        P.coin_line("field coins from the spawn", (sp["pos"][0] + math.sin(f) * 9.0, sp["pos"][1] + math.cos(f) * 9.0,
                                                   0.0), sp["facing"])
    if "census_houses" in field:
        c = field["census_houses"]
        P.coin_ring("field coins by the bat barns", (c[0] + 6.0, c[1] - 2.0, 0.0))
    for i in range(3):
        k = f"garden_bed_{i}_top"
        if k in field:
            P.coin(f"garden bed coin {i}", field[k])
    if "census_gardens" in field:
        c = field["census_gardens"]
        P.coin_line("gardens coins", (c[0] + 8.0, c[1] + 1.0, 0.0), 90.0)
    # ---- the barn roofs (the peaks are red-coin spots) and a fence top
    for k in ("barn2010_roof_east_arm", "barn2010_roof_south_arm", "barn2017_roof_east", "fence1_top_south"):
        if k in bs:
            P.coin(f"bat barns coin {k}", bs[k])
    if "barn2017_addon_box_east" in bs:
        P.one_up("1-up 2017 barn east add-on box", bs["barn2017_addon_box_east"])
    # ---- bog islands
    for k in (1, 2, 3):
        c = ws.get(f"island_{k}_top")
        if not c:
            continue
        if k == 2:
            P.coin_ring("north-east bog coins", c)
            P.heart("heart north-east bog", (c[0] - 3.5, c[1], c[2]))
        elif k == 1:
            P.coin_line("west bog coins", (c[0] - 7.0, c[1] - 9.0, c[2]), 60.0)
        else:
            P.coin("small bog coin", (c[0] + 3.0, c[1] - 1.0, c[2]))       # not under the missions' nest star
    # ---- cypress knees (visual only): a coin floating over the knee top, where the bed is wadeable;
    # every third cypress, never the red-coin one
    rci = red_coin_cypress(S)
    for ci, t in enumerate(wm.get("cypress", [])):
        if ci % 3 != 1 or ci == rci or not t["knees_m"]:
            continue
        kx, ky, kz = t["knees_m"][-1]
        fz = probe.floor(kx - S.cx, ky - S.cy, kz + 0.5)
        if fz is None or W.WATER_Z - fz > 0.95 or near_red((kx, ky, kz)):
            P.skipped.append({"name": f"cypress {ci + 1} knee coin", "why": f"bed {fz} under the knee"})
            continue
        P._add("coin", f"cypress {ci + 1} knee coin", kx, ky, kz + 0.35, "bhvYellowCoin", "MODEL_YELLOW_COIN", coins=1)
    # ---- Baughman Center: lawn ring + heart, aisle roofs, vestibule roof, footbridge
    if "baughman_lakeside_lawn" in bcs:
        c = bcs["baughman_lakeside_lawn"]
        P.coin_ring("baughman lawn coins", (c[0] + 2.0, c[1] - 6.0, 0.0))
        P.heart("heart Baughman lawn", (c[0] + 2.0, c[1] - 6.0, 0.0))
    for k in ("baughman_aisle_ne", "baughman_aisle_nw", "baughman_aisle_se", "baughman_vestibule_roof"):
        if k in bcs:
            P.coin(f"baughman coin {k}", bcs[k])
    if "baughman_bridge_mid" in bcs:
        ax = bc.get("markers", {}).get("bridge_axis_m")
        f = bearing(ax[0], ax[-1]) if ax else 340.0
        P.coin_line("footbridge coins", bcs["baughman_bridge_mid"], f, quiet=True) or \
            P.coin("footbridge coin", bcs["baughman_bridge_mid"])
    # ---- east overlook + the marsh shallows
    if "east_overlook_platform" in bw:
        P.coin("east overlook coin", bw["east_overlook_platform"])
    if "east_overlook_steps_foot" in bw:
        P.heart("heart east overlook steps", bw["east_overlook_steps_foot"])
    for k, (x, y) in enumerate(((-1556.0, -640.0), (-1585.0, -700.0), (-1850.0, -775.0), (-1720.0, -862.0))):
        fz = probe.floor(x - S.cx, y - S.cy, 0.5)
        if fz is not None and W.WATER_Z - 0.85 < fz < W.WATER_Z:
            P.coin_line(f"shallows coins {k}", (x, y, fz), 0.0 if k < 2 else 90.0)
    # ---- Goombas (land, away from the water and the spawn)
    for k, (x, y, f) in enumerate(((-1870.0, -533.0, 250.0), (-1918.0, -553.0, 60.0), (-1862.0, -582.0, 300.0),
                                   (-1940.0, -748.0, 30.0), (-1585.0, -545.0, 200.0), (-1640.0, -760.0, 0.0))):
        if W.shore_dist(x, y, 20.0) < 12.0 and not W.in_lake(x, y):
            continue
        P.goomba(f"goomba {k}", (x, y, 0.0), f)
    # ---- poles: bat-cam poles, Museum Road lights, bald cypress
    for q in bats.get("markers", {}).get("poles", []) + road.get("markers", {}).get("poles", []) + \
            wm.get("poles", []):
        P.pole(f"pole {q['name']}", q["base_m"], q["height_m"])
    return P.items, P.skipped


# ------------------------------------------------------------------ mission anchor points
def lake_points(S, probe, spawn, stars, warp_nodes, level, slot):
    """-> dict for data/uf/lake_points.json (swamp_points.json format): every anchor of design 7.4 measured
    on the built collision (stage_points.Points), plus water / water-box checks and the pickups."""
    import stage_points as SPt
    W = _W()
    P = SPt.Points(S, probe)
    r2 = SPt.r2
    gu = SPt.game_units
    wx = _extras(S, "lake_alice_water")
    wsp, wm = wx.get("spots", {}), wx.get("markers", {})
    bats = _extras(S, "bat_barns")
    bsp = bats.get("spots", {})
    bc = _extras(S, "baughman_center").get("spots", {})
    bwx = _extras(S, "lake_boardwalks")
    bw = bwx.get("spots", {})
    road = _extras(S, "museum_road_edge")
    rs = road.get("spots", {})
    fx_ = _extras(S, "bat_house_field")
    field = fx_.get("spots", {})
    dres = getattr(S, "lake_dressing", None) or {}
    WZ = W.WATER_Z

    def bed(x, y, z_from=None):
        """The floor under a water point (ray from 1 m over the surface: the bank near the shore can be up to
        grade; a lily pad or the deck counts as the floor there)."""
        return probe.floor(x - S.cx, y - S.cy, WZ + 1.0 if z_from is None else z_from)

    def water(name, p, min_depth=0.0, note=None, facing=None, z_from=None):
        """A point ON the water surface (map x, y): the floor under it, the depth, room at the surface."""
        x, y = p[0], p[1]
        fz = bed(x, y, z_from)
        rec = {"name": name, "map_m": [r2(x), r2(y), r2(WZ)], "game": gu(S, x, y, WZ), "water_surface": True,
               "floor_below_m": None if fz is None else r2(fz), "depth_m": None if fz is None else r2(WZ - fz),
               "room_m": r2(probe.clearance(x - S.cx, y - S.cy, WZ + 0.3, 3.0)),
               "in_lake": W.in_lake(x, y)}
        if facing is not None:
            rec["facing_deg"] = round(facing, 1)
            rec["game_yaw"] = "0x%04X" % SPt.game_yaw(facing)
        if fz is None or WZ - fz < min_depth or not rec["in_lake"]:
            rec["check"] = f"depth {rec['depth_m']} m (want >= {min_depth})"
            P.flags.append(f"{name}: {rec['check']}")
        if note:
            rec["note"] = note
        return rec

    def sp(d, k, name=None, src="", **kw):
        if k not in d:
            P.flags.append(f"{name or k}: spot {k!r} missing ({src})")
            return None
        return P.ground(name or k, d[k], source=f"{src} {k}".strip(), **kw)

    out = {
        "schema": "sgl64.lake_points/1",
        "generated_by": "tools/campus/build_stage.py lake_alice (stage_points.lake_points -> stage_lake.lake_points)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
        "stage": STAGE, "level": level, "slot": slot, "level_const": "LEVEL_JRB", "course": "COURSE_JRB",
        "center_m": list(S.data["center"]),
        "coordinates": {
            "map_m": "x = east, y = north, z = metres above grade (the lake surface is at -0.5); origin = Century "
                     "Tower",
            "game": "X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 with (cx, cy) = center_m = (-1760, -660); "
                    "Y is the ray-cast collision floor (Mario's feet), or the water surface (-50) for "
                    "'water_surface' points. Objects that hover (stars, coins) add their own offset.",
            "game_yaw": "0 = faces +Z (south), 0x4000 = east, 0x8000 = north, 0xC000 = west",
            "floor_m": "collision floor measured by ray-casting the built level (STAND_FROM_M above the design "
                       "height, straight down)",
            "depth_m": "water depth at a water-surface point: surface -0.5 minus the floor under it. Mario wades "
                       "below 1.0 m (his feet on the floor), swims deeper (pos.y < waterLevel - 100)"},
        "note": "Anchor points for the Course 3 mission author (docs/game_design.md 7.4, Lake Alice, slot jrb / "
                "LEVEL_JRB, door 3 = Newell Hall, 8 stars). Re-generated on every `build_stage.py -- lake_alice` "
                "from the built collision; points with a 'check' key did not measure as designed. 'actN_' keys use "
                "the DESIGN act numbers (1 Boardwalk Welcome, 2 Gator Hop, 3 Shell Surf Regatta, 4 Bat Census at "
                "Dusk (2P+), 5 Lost Hatchling, 6 Lily Pad Red Coins); course.lua numbers the playable acts 1..n "
                "(solo acts first, docs/flow.md 5.1). The level script has NO level-script star (stars = []): "
                "every mission spawns its own (spawn_default_star from the controller loop, star id = course act "
                "- 1), or build_stage.py STAGE_STARS gets an entry. Alligators are mission objects (reskinned / "
                "original SM64 enemy stand-ins); this file only says where.",
    }
    sx, sy = spawn["map_m"]
    out["spawn"] = dict(P.ground("spawn_0x0A", (sx, sy, 0.0), facing=spawn["facing_deg"],
                                 note="stage entry spawn (bhvSpinAirborneWarp, MARIO_POS) in the bat-house field "
                                      "(the shore module's landing zone), the bat barns behind, facing the lake "
                                      "over Museum Road through the arrival vista; the object hovers 1 m up"),
                        node="0x0A", spawn_object_game=spawn["game_units"])
    out["warp_nodes"] = warp_nodes
    out["stars"] = stars

    # ---- water: surface, boxes, coverage
    px0, py0, px1, py1 = S.play_local
    boxes = []
    for (x0, y0, x1, y1, surf, bot, name) in S.water_boxes:
        cx0, cy0, cx1, cy1 = max(x0, px0 - 2.0), max(y0, py0 - 2.0), min(x1, px1 + 2.0), min(y1, py1 + 2.0)
        if cx1 - cx0 < 0.5 or cy1 - cy0 < 0.5:
            continue
        gx = sorted((int(round(cx0 * 100)), int(round(cx1 * 100))))
        gz = sorted((int(round(-cy0 * 100)), int(round(-cy1 * 100))))
        boxes.append({"name": name, "x0": gx[0], "x1": gx[1], "z0": gz[0], "z1": gz[1],
                      "surface_y": int(round(surf * 100)), "bottom_y": int(round(bot * 100))})

    def in_box(X, Z):
        return next((b for b in boxes if b["x0"] < X < b["x1"] and b["z0"] < Z < b["z1"]), None)
    wet = dry_in_lake = uncovered = 0
    misses = []
    lx0, ly0, lx1, ly1 = W._LAKE_BB
    y = ly0 + 1.0
    while y < ly1:
        x = lx0 + 1.0
        while x < lx1:
            if W.in_lake(x, y):
                fz = probe.floor(x - S.cx, y - S.cy, 1.0)
                if fz is not None and fz < WZ - 0.05:
                    wet += 1
                    X, Z = int(round((x - S.cx) * 100)), int(round(-(y - S.cy) * 100))
                    b = in_box(X, Z)
                    if b is None or b["surface_y"] != int(round(WZ * 100)):
                        uncovered += 1
                        misses.append([round(x, 1), round(y, 1)])
                else:
                    dry_in_lake += 1
            x += 2.0
        y += 2.0
    if uncovered:
        P.flags.append(f"water: {uncovered} wet lake points outside every water box")
    out["water"] = {
        "surface_m": WZ, "surface_game_y": int(round(WZ * 100)), "bed_m": W.BED_Z,
        "deep_m": wm.get("water", {}).get("deep_z_m"), "boxes": boxes,
        "coverage_check": {"grid_m": 2.0, "wet_points": wet, "outside_every_box": uncovered,
                           "dry_points_in_ring": dry_in_lake, "misses": misses[:20],
                           "note": "every lake point whose floor is under the surface must be inside a water box "
                                   "(SM64 tests loX < X < hiX and loZ < Z < hiZ strictly); dry points = banks, bog "
                                   "islands, lily pads, the deck"},
        "deep_spots": [P.ground(f"deep_{k + 1}_bed", tuple(d), clear=0.0, tol=0.3) for k, d in
                       enumerate(wm.get("deep_spots_m", []))],
        "note": "SM64 water boxes (COL_WATER_BOX in area_1/collision.inc.c) from lake_alice_water.py "
                "water_boxes_m, clipped to the play zone + 2 m. Swimming: water deeper than 1 m."}

    # ---- design act 1: Boardwalk Welcome (marsh boardwalk + lily pads -> the observation deck)
    a1 = {"note": "Spawn -> lakeshore trail -> the north boardwalk (deck 0.5 m) -> wade onto the west bog "
                  "-> walk it east -> the north_shallows lily pads (15, edge gaps 1.3 -> 2.4 m, a coin over "
                  "each but the red-coin rest pad 5) -> the observation deck (octagon, top 0.2 m, pavilion roof "
                  "apex 4.0 m). Skeeters / cheep-cheeps: skeeter_spots (water surface beside the pads), cheep_spots "
                  "(1 m under the surface). A miss = swim to a pad and water-jump (A + stick forward at the "
                  "surface) onto it."}
    a1["route"] = [r for r in (
        sp(bw, "north_boardwalk_west_end", "act1_boardwalk_west_end", "lake_alice_shore.py"),
        sp(bw, "north_boardwalk_mid", "act1_boardwalk_mid", "lake_alice_shore.py", clear=0.5),
        sp(bw, "north_boardwalk_east_end", "act1_boardwalk_east_end", "lake_alice_shore.py"),
        sp(wsp, "island_1_top", "act1_west_bog_top", "lake_alice_water.py", clear=0.5),
        sp(wsp, "lily_route_start", "act1_lily_route_start", "lake_alice_water.py", clear=0.0),
    ) if r]
    pads = [p for p in wm.get("lily_pads", []) if p["route"] == "north_shallows"]
    a1["lily_pads"] = [dict(P.ground(f"act1_pad_{p['i']:02d}", tuple(p["pos_m"]), clear=0.0, tol=0.15),
                            radius_m=p["r_m"]) for p in pads]
    od = dres.get("observation_deck")
    if od:
        (cx, cy), t0 = deck_frame()
        a1["deck"] = {
            "center": P.ground("act1_deck_center", (cx, cy, DECK_TOP), clear=0.0, tol=0.1),
            "landing_from_pads": P.ground("act1_deck_landing", (cx + 3.2 * math.cos(t0), cy + 3.2 * math.sin(t0),
                                                                DECK_TOP), clear=0.5, tol=0.1),
            "pavilion_roof_apex": P.ground("act1_pavilion_roof", (cx, cy, od["pavilion"]["apex_m"]), clear=0.0,
                                           tol=0.2),
            "geometry": od,
            "note": "edge 0 faces the last lily pad, edge 1 the gator route to the bog; edges 0, 1, 4, 7 are open "
                    "(water-jump on from a swim: A + stick forward at the surface), edges 2, 3, 5, 6 have 1 m railings"}
        sx_, sy_ = deck_point(STAR_U_M)
        g = P.ground("act1_star_target", (sx_, sy_, DECK_TOP), clear=0.0, tol=0.1)
        if g.get("floor_m") is not None:
            g = dict(g, map_m=[g["map_m"][0], g["map_m"][1], r2(g["floor_m"] + STAR_UP_M)],
                     game=gu(S, g["map_m"][0], g["map_m"][1], g["floor_m"] + STAR_UP_M),
                     note=f"star {STAR_UP_M} m over the deck floor on its far side (deck frame u {STAR_U_M} m, by the "
                          f"open edge 4), {abs(STAR_U_M) - PAV_ROOF:.1f} m clear of the pavilion roof's eave: the "
                          "star's arc in and its final 2.1 m rise (bhvStarSpawnCoordinates) miss the roof")
            ceil = probe.ceiling(sx_ - S.cx, sy_ - S.cy, g["floor_m"] + 0.1, 3.0)
            if ceil is not None:
                P.flags.append(f"act1_star_target: a ceiling {ceil:.2f} m over the star spot")
                g["check"] = f"ceiling at {ceil:.2f} m"
        a1["star_target"] = g
        sfx, sfy = deck_point(STAR_FROM_U_M)
        a1["star_from"] = P.air("act1_star_from", (sfx, sfy, STAR_FROM_Z_M),
                                note="where act 1's star arcs in from (over the open water beyond edge 4)")
        last = pads[-1]["pos_m"] if pads else None
        if last:
            edge = math.dist(last[:2], (cx, cy)) - pads[-1]["r_m"] - DECK_R_IN
            a1["last_pad_to_deck_gap_m"] = r2(edge)
    sk, ch = [], []
    if pads:
        for k, i in enumerate((2, 5, 8, 11, 13)):
            if i >= len(pads):
                continue
            p, q = pads[i]["pos_m"], pads[i - 1]["pos_m"]
            f = bearing(q, p)
            side = 1 if k % 2 == 0 else -1
            ox, oy = math.cos(math.radians(f)) * side, -math.sin(math.radians(f)) * side
            sk.append(water(f"act1_skeeter_{k}", (p[0] + ox * 7.0, p[1] + oy * 7.0), 1.0, facing=f,
                            note="water strider spot 7 m beside the pad line"))
            r = water(f"act1_cheep_{k}", (p[0] - ox * 5.0, p[1] - oy * 5.0), 1.6)
            r["map_m"][2] = r2(WZ - 1.0)
            r["game"] = gu(S, p[0] - ox * 5.0, p[1] - oy * 5.0, WZ - 1.0)
            r["note"] = "cheep-cheep swim spot 1 m under the surface, 5 m off the pad line"
            ch.append(r)
    a1["skeeter_spots"], a1["cheep_spots"] = sk, ch
    a1["lurk_gator_spots"] = [water(f"act1_lurk_gator_{k}", p, LURK_MIN_DEPTH_M, note=n)
                              for k, (p, n) in enumerate(act1_lurk_spots())]
    out["act1_boardwalk_welcome"] = a1

    # ---- design act 2: Gator Hop (basking gators -> the island nest on the small bog)
    nest = dres.get("nest") or {}
    W_isl = wm.get("island_rings_m", [])
    a2 = {"note": "The island nest is on the small bog (lake_alice_water island 3, OSM w118249560), the bog "
                  "uf_lake_missions.lua's gator line ends at: nest = the mound top, nest_island_top = the bog's "
                  "middle (the module's island_3_top spot, kept clear for the star), mother_spot beside the mound. "
                  "small_bog_landings: the bog's edge (0.25 m under water) at N / E / S / W, where a gator line can "
                  "end. approach_south: the water depth every 5 m due south of the bog (the deep hole deep_1 lies "
                  "there). big_gator_spots: deep water by the bog for the snapping big gators. The bog is also "
                  "reachable by wading from the north bank (NEST_BANK): a big gator there guards it."}
    if nest:
        a2["nest"] = P.ground("act2_nest_top", (nest["map_m"][0], nest["map_m"][1], nest["top_m"]), clear=0.0,
                              tol=0.2, note="top of the nest mound (mud + sticks, three eggs) on the small bog")
        a2["mother_spot"] = P.ground("act2_mother_gator", (nest["map_m"][0] - 1.0, nest["map_m"][1] + 2.4,
                                                            nest["bog_floor_m"]), clear=0.3, tol=0.3,
                                     note="beside the nest, on the bog (the mother gator of act 5; she faces the nest)")
    top = wsp.get(f"island_{NEST_ISLAND + 1}_top")
    if top:
        a2["nest_island_top"] = P.ground("act2_nest_island_top", top, clear=0.5, tol=0.3,
                                         note="the small bog's middle, 2.6 m east of the mound (a star / probe spot)")
    if len(W_isl) > NEST_ISLAND and top:
        ring = W_isl[NEST_ISLAND]
        lands = []
        for tag, (dx, dy) in (("N", (0, 1)), ("E", (1, 0)), ("S", (0, -1)), ("W", (-1, 0))):
            # walk from the bog's middle outwards to its shore ring, then 0.8 m back inside
            d = 0.0
            while d < 30.0 and _pip((top[0] + dx * d, top[1] + dy * d), [tuple(q) for q in ring]):
                d += 0.25
            q = (top[0] + dx * (d - 0.8), top[1] + dy * (d - 0.8))
            fz = probe.floor(q[0] - S.cx, q[1] - S.cy, 1.0)
            lands.append(dict(P.ground(f"act2_small_bog_edge_{tag}", (q[0], q[1], fz if fz is not None else WZ),
                                       clear=0.0, tol=0.3), shore_m=r2(d)))
        a2["small_bog_landings"] = lands
        a2["approach_south"] = [water(f"act2_south_{k * 5:02d}m", (top[0], top[1] - 9.0 - k * 5.0), -0.5)
                                for k in range(12)]
    a2["big_gator_spots"] = [water(f"act2_big_gator_{k}", p, 1.6, note=t) for k, (p, t) in enumerate(BIG_GATOR_SPOTS)]
    out["act2_gator_hop"] = a2

    # ---- design act 3: Shell Surf Regatta (8 buoys)
    buoys = wm.get("regatta_buoys_m", [])
    legs = []
    total = 0.0
    for k, (p, q) in enumerate(zip(buoys, buoys[1:] + buoys[:1])):
        L = math.dist(p[:2], q[:2])
        n = max(1, int(L / 2.0))
        shallow, blocked = [], []
        f = bearing(p, q)
        dx, dy = math.sin(math.radians(f)), math.cos(math.radians(f))
        for i in range(n + 1):
            x, y = p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n
            fz = bed(x, y)
            if fz is None or WZ - fz < 0.6:
                shallow.append([round(x, 1), round(y, 1), None if fz is None else round(fz, 2)])
        hit = probe.ray(p[0] - S.cx, p[1] - S.cy, WZ + 0.4, dx, dy, L)
        if hit is not None:
            blocked.append(round(hit, 1))
        rec = {"from": k + 1, "to": (k + 1) % len(buoys) + 1, "length_m": r2(L), "heading_deg": round(f, 1),
               "shallow_samples": shallow[:10], "obstacle_at_m": blocked}
        if shallow or blocked:
            rec["check"] = f"{len(shallow)} shallow samples, obstacle at {blocked}"
            P.flags.append(f"regatta leg {k + 1}: {rec['check']}")
        legs.append(rec)
        total += L
    a3 = {"note": "Grab a Koopa shell at the start and surf the 8 buoys in order (closed loop). Buoys are >= 27 m "
                  "from every shore and bog; every leg is open water >= 0.6 m deep with no wall 0.4 m above the "
                  "surface (pads have no walls). Start candidates: the water off the Baughman lawn "
                  "(regatta_dock_water), the north boardwalk's viewing bay, the Baughman footbridge.",
          "buoys": [water(f"act3_buoy_{k + 1}", b, 1.0) for k, b in enumerate(buoys)],
          "legs": legs, "loop_length_m": r2(total),
          "par_note": "design par 75 s; a ridden shell tops out near 64 units/frame = 19 m/s, so the loop is ~"
                      f"{total / 19.2:.0f} s flat out",
          "start": [r for r in (
              water("act3_start_water_baughman", wsp["regatta_dock_water"], 0.2,
                    note="a ridden shell floats on any water deeper than its floor") if "regatta_dock_water" in wsp else None,
              sp(bw, "regatta_launch_boardwalk", "act3_start_boardwalk_bay", "lake_alice_shore.py", clear=0.3),
              sp(bc, "regatta_launch_bridge", "act3_start_footbridge", "lake_alice_shore.py", clear=0.5),
              sp(bc, "baughman_lakeside_lawn", "act3_shell_box_lawn", "lake_alice_shore.py",
                 note="open lawn by the water for a shell box (a regatta start on land)"),
          ) if r]}
    out["act3_shell_surf_regatta"] = a3

    # ---- design act 4: Bat Census at Dusk (2P+)
    st = fx_.get("markers", {}).get("census_stations_m", {})
    stations = [r for r in (
        sp(field, "census_houses", "act4_station_houses", "lake_alice_shore.py"),
        sp(field, "census_gardens", "act4_station_gardens", "lake_alice_shore.py"),
        sp(bw, "census_boardwalk", "act4_station_boardwalk", "lake_alice_shore.py", clear=0.5),
    ) if r]
    pairs = {}
    for i in range(len(stations)):
        for j in range(i + 1, len(stations)):
            a, b = stations[i]["map_m"], stations[j]["map_m"]
            pairs[f"{stations[i]['name']}-{stations[j]['name']}"] = r2(math.dist(a[:2], b[:2]))
    exits = bats.get("markers", {}).get("bat_exits_m", [])
    a4 = {"note": "Three clipboard census stations (count only while staffed; 64-136 m apart, so one player cannot "
                  "hold two). Swoopers stream out of the barns' open mesh bottoms (4.15 m) for 90 s at dusk. The "
                  "1991 Bat House was demolished in 2022 (its fenced plot is empty): a third stream can come from "
                  "old_house_site at the same height. Dusk is a per-act Lua look (lighting / fog / skybox), the "
                  "level's base is daytime.",
          "stations": stations, "station_distances_m": pairs, "stations_shore_module": st,
          "swooper_exits": [P.air(f"act4_bat_exit_{k}", tuple(p)) for k, p in enumerate(exits)],
          "third_exit_old_house_site": P.air("act4_bat_exit_old_house", (bsp["old_house_site"][0],
                                                                         bsp["old_house_site"][1], 4.15))
          if "old_house_site" in bsp else None,
          "dusk_look_hint": {
              "skybox": "BACKGROUND_PURPLE_SKY (or BACKGROUND_FLAMING_SKY) via set_override_skybox",
              "light_color_srgb": [255, 170, 120], "ambient_srgb": [70, 60, 90], "fog_color_srgb": [96, 74, 92],
              "note": "suggested values for the act 4 Lua. coopdx v1.5.1 has set_override_skybox(bg), "
                      "set_lighting_color(ch, v), set_lighting_color_ambient(ch, v), set_lighting_dir(ch, v), "
                      "set_fog_color(ch, v), set_fog_intensity(f), set_skybox_color(ch, v), set_vertex_color(ch, v) "
                      "(ch = 0 red, 1 green, 2 blue; v = 0-255; tools/luatest/coopdx_api_v151.lua); apply them in "
                      "act 4 only and restore the defaults when the act or level ends. The level's fog colour is "
                      "baked into its display lists (gsDPSetFogColor 182, 206, 210)."}}
    out["act4_bat_census"] = a4

    # ---- design act 5: Lost Hatchling (Museum Road -> the island nest on the small bog)
    a5 = {"note": "The baby gator waits on Museum Road (shore module spot) and must be carried to its mother at the "
                  "nest on the small bog: carry_route = the shortest walk at grade on the built collision (A* on a "
                  "2 m grid, stage_points.ground_route) from the hatchling to the north bank above the bog "
                  "(NEST_BANK), then a ~10 m wade (or throw it across to a friend on the bog). throw_spots: bank "
                  "points by the bog.",
          "hatchling_start": sp(rs, "hatchling_museum_road", "act5_hatchling_start", "lake_alice_shore.py"),
          "mother": a2.get("mother_spot"), "nest": a2.get("nest")}
    if "hatchling_museum_road" in rs:
        h = rs["hatchling_museum_road"]
        route = SPt.ground_route(S, probe, h, NEST_BANK, (-1915.0, -600.0, -1695.0, -480.0))
        if route is None:
            P.flags.append("act5 carry route: no ground route found")
        else:
            wps = [P.ground(f"act5_carry_{k:02d}", p, clear=0.5) for k, p in enumerate(route)]
            a5["carry_route"] = {"waypoints": wps, "game_path": [w["game"] for w in wps],
                                 "length_m": r2(sum(math.dist(a[:2], b[:2]) for a, b in zip(route, route[1:]))),
                                 "path_check": P.path("act5_carry_path", route, z_design=0.0, tol=0.5)}
    a5["throw_spots"] = [P.ground("act5_throw_north_bank", (NEST_BANK[0], NEST_BANK[1], 0.0), clear=0.5,
                                  note="north bank above the small bog (~20 m from the nest, mostly wading water)")]
    out["act5_lost_hatchling"] = a5

    # ---- design act 6: Lily Pad Red Coins
    rc = []
    for name, p, note in red_coin_spots(S):
        if name == "rc_boardwalk_underside":
            r = water(name, p, -0.1, z_from=0.3,
                      note=note + "; the inlet under the deck is a mud flat at the waterline (0-7 cm of water) and the "
                                  "deck is top-only collision, so Mario wades in under it")
        elif name == "rc_cypress_knee":
            r = P.air(name, p, note=note)
            fz = probe.floor(p[0] - S.cx, p[1] - S.cy, p[2] + 0.5)      # the shallow bed (the knee is visual)
            r["floor_below_m"] = None if fz is None else r2(fz)
            r["height_above_floor_m"] = None if fz is None else r2(p[2] - fz)
            r["wading_depth_m"] = None if fz is None else r2(WZ - fz)
            if fz is None or WZ - fz > 0.95:
                r["check"] = f"bed {fz} under the knee (want wading depth < 0.95 m)"
                P.flags.append(f"{name}: {r['check']}")
        else:
            r = P.ground(name, p, clear=0.0, tol=0.3, note=note)
        rc.append(r)
    out["act6_red_coins"] = {
        "red_coins": rc,
        "star_spot": P.ground("act6_red_coin_star_field", (field["spawn_field"][0] + 6.0, field["spawn_field"][1] - 10.0,
                                                           0.0), clear=1.5) if "spawn_field" in field else None,
        "note": "design 7.4 act 6's 8 spots in its order (3 lily pads, 2 bat-barn roof tops, the garden trellis, a "
                "cypress knee, the boardwalk underside at the water surface); heights are the floor (or the surface), "
                "add the coin's hover. No yellow coin sits on these spots (stage_lake.lake_pickups). Red-coin star: "
                "the bat-house field, in sight of the spawn."}

    # ---- shoreline checkpoints (on the bank all round the lake) + basking gator spots at the waterline
    ring = W.LAKE_RING
    per = sum(math.dist(a, b) for a, b in zip(ring, ring[1:] + ring[:1]))
    cps, basks = [], []
    for k in range(SHORE_CHECKPOINTS):
        s = per * (k + 0.5) / SHORE_CHECKPOINTS
        acc = 0.0
        for a, b in zip(ring, ring[1:] + ring[:1]):
            L = math.dist(a, b)
            if acc + L >= s:
                u = (s - acc) / L
                px, py = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L        # right of a->b on a CCW ring = outward
                break
            acc += L
        best = None
        for out_m in (4.0, 5.5, 3.0, 7.0, 9.0):
            for side in (0.0, 2.0, -2.0, 4.0, -4.0):
                q = (px + nx * out_m - ny * side, py + ny * out_m + nx * side)
                if W.in_lake(*q):
                    continue
                fz = probe.floor(q[0] - S.cx, q[1] - S.cy, 1.5)
                if fz is None or abs(fz) > 0.3:
                    continue
                cl = probe.clearance(q[0] - S.cx, q[1] - S.cy, fz + 0.6, 3.0)
                if best is None or cl > best[1]:
                    best = (q, cl)
                if cl >= 1.5:
                    break
            if best and best[1] >= 1.5:
                break
        facing = bearing((px + nx, py + ny), (px, py))            # towards the water
        if best:
            cps.append(dict(P.ground(f"shore_cp_{k:02d}", (best[0][0], best[0][1], 0.0), facing=facing, clear=0.9),
                            water_edge_m=[r2(px), r2(py)]))
        if k % 2 == 0:
            # waterline: ~2 m inside the ring where the bank meets the water (half in the water)
            for d_in in (2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
                q = (px - nx * d_in, py - ny * d_in)
                fz = bed(*q)
                if fz is not None and WZ - 0.45 <= fz <= WZ - 0.02:
                    basks.append(water(f"bask_gator_{k:02d}", q, 0.0, facing=bearing((px, py), q),
                                       note="basking spot at the waterline (bank), facing the water"))
                    break
    out["shoreline"] = {"checkpoints": cps, "perimeter_m": r2(per),
                        "note": "16 checkpoints on the bank all round the lake (4 m out of the shore ring, clear ground; "
                                "facing = towards the water), in shore-ring order (counter-clockwise seen from above, "
                                "starting at the north-west shore under Museum Road). water_edge_m = the shore point "
                                "behind each."}
    out["gator_spots"] = {
        "basking_waterline": basks,
        "islands": [P.ground(f"bask_gator_island_{k + 1}", BASK_ISLAND_1 if k == 0 else tuple(wsp[f"island_{k + 1}_top"]),
                             clear=0.0, tol=0.4) for k in range(3) if f"island_{k + 1}_top" in wsp],
        "basking_gators": (dres.get("basking_gators") or []),
        "note": "decorative / hazard gator spots (mission objects): at the waterline round the lake and on the bog "
                "tops; act 2's platforms and big gators are under act2_gator_hop, act 1's lurking gators under "
                "act1_boardwalk_welcome.lurk_gator_spots. basking_gators: the rigid basking alligators built into "
                "the level (stage_lake.BASKING_GATORS, every act; a low collision body)"}

    # ---- every landmark spot, measured; poles; secrets. Records are named by the plain spot name (unique
    # across the two modules) so tools/luatest/check_lake_points.py can match them
    lm = {}
    for slug in ("bat_barns", "baughman_center", "lake_boardwalks", "museum_road_edge", "bat_house_field",
                 "lake_alice_water"):
        d = _extras(S, slug).get("spots", {})
        rec = {}
        for k, v in d.items():
            if k.endswith("_bat_exit") or k.endswith("_batcam_top") or k == "baughman_ridge" or \
                    k.startswith("street_light_"):
                rec[k] = P.air(k, tuple(v), note="not a floor (bat exit, pole top, slide ridge)")
                continue
            if k == "boardwalk_underside":
                rec[k] = water(k, v, -0.1, z_from=0.3, note="mud flat at the waterline under the deck")
                continue
            if k == "lake_center_deck_site_water":
                rec[k] = water(k, v, -1.0, note="the observation deck (top 0.2 m) stands here now")
                continue
            if k.endswith("_water") or k == "regatta_dock_water":
                rec[k] = water(k, v)
                continue
            if k == "lake_center_deck_site":       # the observation deck stands there now
                rec[k] = P.ground(k, (v[0], v[1], DECK_TOP), clear=0.0, tol=0.1,
                                  note="the observation deck's top (the module's spot is the lake bed under it)")
                continue
            rec[k] = P.ground(k, v, clear=0.0, tol=0.6)
        lm[slug] = rec
    out["landmark_spots"] = lm
    poles = []
    for q in bats.get("markers", {}).get("poles", []) + road.get("markers", {}).get("poles", []) + wm.get("poles", []):
        g = P.ground(f"pole_{q['name']}", q["base_m"], clear=0.0, tol=0.5)
        poles.append(dict(g, height_m=q["height_m"], behavior="bhvPoleGrabbing",
                          bparams="0x00%02X0000" % int(round(q["height_m"] * 10)), note=q.get("note")))
    out["poles"] = poles
    out["secret_spots"] = [r for r in (
        sp(bsp, "barn2017_addon_box_east", "secret_barn2017_addon_box", "lake_alice_shore.py", clear=0.0),
        sp(rs, "kiosk_roof", "secret_kiosk_roof", "lake_alice_shore.py", clear=0.0),
        sp(bc, "baughman_aisle_ne", "secret_baughman_aisle_ne", "lake_alice_shore.py", clear=0.0),
        sp(bw, "east_overlook_platform", "secret_east_overlook", "lake_alice_shore.py", clear=0.5),
        P.ground("secret_pavilion_roof", (deck_frame()[0][0], deck_frame()[0][1], od["pavilion"]["apex_m"]), clear=0.0,
                 tol=0.2) if od else None,
        P.ground("secret_deepest_hole", tuple(sorted(wm.get("deep_spots_m", [[0, 0, 0]]), key=lambda d: d[2])[0]),
                 clear=0.0, tol=0.3) if wm.get("deep_spots_m") else None,
    ) if r]
    out["dressing"] = dres
    out["trees"] = S.stats.get("lake_tree_plan")
    out["pickups"] = getattr(S, "stage_pickups", None)
    out["checks"] = P.flags
    return out


# ------------------------------------------------------------------ previews
def lake_views(S):
    """Preview cameras (map metres): the arrival (Lakitu's first view), the lake surface, the lily-pad route
    and the observation deck, the bat barns, the Baughman Center, the boardwalks, the cypress shallows,
    the nest, aerials and an edge check."""
    H = S.data["extent_half_m"]
    sp = getattr(S, "spawn", None) or {"pos": (-1893.0, -541.0), "facing": 150.0}
    f = math.radians(sp["facing"])
    fx, fy = math.sin(f), math.cos(f)
    x, y = sp["pos"]
    (dx, dy), t0 = deck_frame()
    return [
        {"name": "lake_topdown", "ortho": 2 * H, "fog": False, "px": 1600},
        {"name": "lake_arrival", "cam": (x - fx * 10.0, y - fy * 10.0, 3.4), "target": (x + fx * 70.0, y + fy * 70.0, 1.5),
         "vfov": 50.0},
        {"name": "lake_arrival_wide", "cam": (x - fx * 24.0 - fy * 6.0, y - fy * 24.0 + fx * 6.0, 12.0),
         "target": (x + fx * 80.0, y + fy * 80.0, -2.0), "vfov": 60.0},
        {"name": "lake_surface_north_shore", "cam": (-1836.0, -616.0, 0.9), "target": (-1734.0, -655.0, 0.5), "vfov": 55.0},
        {"name": "lake_surface_from_deck", "cam": (dx - 3.0, dy - 2.0, 1.9), "target": (-1640.0, -700.0, 0.0), "vfov": 60.0},
        {"name": "lake_lily_pad_route", "cam": (-1790.0, -598.0, 3.5), "target": (-1736.0, -652.0, 0.0), "vfov": 55.0},
        {"name": "lake_observation_deck", "cam": (dx + 16.0, dy + 9.0, 5.0), "target": (dx, dy, 1.5), "vfov": 50.0},
        {"name": "lake_bat_houses", "cam": (-1878.0, -538.0, 2.2), "target": (-1897.0, -506.0, 6.5), "vfov": 55.0},
        {"name": "lake_bat_barn_roof", "cam": (-1876.0, -517.0, 9.4), "target": (-1880.0, -560.0, 2.0), "vfov": 60.0},
        {"name": "lake_baughman_front", "cam": (-1990.0, -748.0, 3.0), "target": (-1958.0, -733.0, 7.0), "vfov": 55.0},
        {"name": "lake_baughman_from_lake", "cam": (-1925.0, -712.0, 1.2), "target": (-1960.0, -732.0, 6.0), "vfov": 55.0},
        {"name": "lake_north_boardwalk", "cam": (-1858.0, -598.0, 2.2), "target": (-1820.0, -612.0, 0.0), "vfov": 60.0},
        {"name": "lake_cypress_shallows", "cam": (-1825.0, -780.0, 2.0), "target": (-1860.0, -805.0, 4.0), "vfov": 60.0},
        {"name": "lake_small_bog_nest", "cam": (-1713.0, -540.0, 2.3), "target": (-1723.0, -529.3, 0.0), "vfov": 55.0},
        {"name": "lake_basking_gator", "cam": (-1806.6, -607.6, 1.4), "target": (-1812.0, -607.0, 0.0), "vfov": 50.0},
        {"name": "lake_basking_gator_shore", "cam": (-1777.4, -552.4, 0.9), "target": (-1782.0, -551.7, -0.3),
         "vfov": 50.0},
        {"name": "lake_deck_star_side", "cam": (dx - 8.0 * math.cos(t0) + 3.0 * math.sin(t0),
                                                dy - 8.0 * math.sin(t0) - 3.0 * math.cos(t0), 2.4),
         "target": (dx, dy, 1.6), "vfov": 55.0},
        {"name": "lake_east_overlook", "cam": (-1530.0, -640.0, 2.5), "target": (-1514.0, -628.0, 1.0), "vfov": 60.0},
        {"name": "lake_aerial_se", "cam": (-1560.0, -880.0, 170.0), "target": (-1760.0, -650.0, 0.0), "vfov": 52.0},
        {"name": "lake_aerial_nw", "cam": (-1990.0, -430.0, 150.0), "target": (-1740.0, -680.0, 0.0), "vfov": 52.0},
        {"name": "lake_aerial_low_north", "cam": (-1800.0, -480.0, 55.0), "target": (-1760.0, -680.0, 0.0), "vfov": 60.0},
        {"name": "lake_edge_check", "cam": (-1990.0, -890.0, 2.2), "target": (-2050.0, -950.0, 6.0)},
    ]
