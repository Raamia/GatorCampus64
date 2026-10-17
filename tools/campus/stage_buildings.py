"""Generic campus buildings: simplified OSM footprints extruded to their real height.

  flat roof  facade walls (window bays, one texture row per floor) up to the roof, a 1 m parapet
             with coping you can walk on, gravel roof inside (Mario can land on every roof)
  hip roof   historic-core collegiate gothic: facade walls + red clay tile roof made by insetting the
             footprint (33 degree slopes: walkable) with a flat crest
  canopy     roof slab on posts (posts visual only)
Backdrop shells (outside the play zone) are visual only. Collision uses the same outline with one
quad per wall and is a separate collision-only mesh.

Climb routes (CLIMB_ROUTES): the generic buildings around the Plaza get an entrance canopy (a
jump-through slab, top 3 m: running single jump or double jump) on the facade that faces the Plaza,
then staggered limestone ledges every 3 m (1.1 m deep, 1.2 m thick: the side / front faces are tall
enough for SM64's ledge grab, which needs the ledge 1.0-1.6 m above Mario's feet while a wall still
covers his feet + 0.3 m) up to the eave, so every one of those roofs can be reached on foot.
"""
import math

import stage_geom as G
from stage_ground import TILE, TILE_OFF

PARAPET_T = 0.35
ROOF_PITCH = math.radians(33.0)
WALL_FOOT = -0.15                     # walls go a little below the visual ground (no gaps)
PARAPET_MAT = {"gothic": "limestone", "brick": "brick_red", "service": "brick_red", "band": "concrete",
               "glass": "metal_gray"}
PLAIN_WALL = {"gothic": "brick_red", "brick": "brick_red", "service": "brick_red", "band": "brick_red",
              "glass": "metal_gray"}
COPING = {"gothic": "limestone", "brick": "limestone", "service": "concrete", "band": "concrete",
          "glass": "metal_gray"}


def floor_height(b):
    return 3.4 if b.get("type") in ("dormitory", "apartments", "residential") else 4.0


def facade_walls(acc, pts, z_top, style, fh):
    """Window-bay walls from the ground to z_top around a CCW footprint."""
    mat = "facade_" + style
    for a, b in zip(pts, pts[1:] + pts[:1]):
        L = math.dist(a, b)
        if L < 2.5:
            acc.wall(a, b, WALL_FOOT, z_top, PLAIN_WALL[style])
            continue
        bays = max(1, round(L / 4.0))
        chunks = math.ceil(bays / 8)
        v0, v1 = WALL_FOOT / fh, z_top / fh
        for k in range(chunks):
            t0, t1 = k / chunks, (k + 1) / chunks
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            u0, u1 = bays * t0, bays * t1
            acc.wall(p0, p1, WALL_FOOT, z_top, mat, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def hip_inset(pts, d_max):
    d = d_max
    while d >= 1.2:
        inn = G.inset(pts, d)
        if inn is not None:
            return inn, d
        d *= 0.75
    return None, 0.0


def roof_slopes(acc, pts, inn, z0, z1, mat, tile):
    """Sloped quads from the eave ring (z0) to the inset ring (z1), UVs along the eave / up the slope."""
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ia, ib = inn[i], inn[(i + 1) % n]
        L = math.dist(a, b)
        ex, ey = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        k = max(1, math.ceil(L / 20.0))
        for j in range(k):
            t0, t1 = j / k, (j + 1) / k
            q = [(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0, z0),
                 (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1, z0),
                 (ia[0] + (ib[0] - ia[0]) * t1, ia[1] + (ib[1] - ia[1]) * t1, z1),
                 (ia[0] + (ib[0] - ia[0]) * t0, ia[1] + (ib[1] - ia[1]) * t0, z1)]
            if acc is None:
                continue
            if tile <= 0:
                acc.poly(q, mat)
                continue
            # v: distance up the slope from the eave line
            nx, ny = ey, -ex  # outward normal of the eave edge
            run = abs((q[2][0] - q[1][0]) * nx + (q[2][1] - q[1][1]) * ny)
            slope = math.hypot(run, z1 - z0)
            uvs = []
            for p in q:
                u = ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / tile
                v = (slope if p[2] > z0 + 1e-6 else 0.0) / tile
                uvs.append((u, v))
            acc.poly(q, mat, uvs)


def build_one(S, b, vis, col):
    pts = G.dedupe(G.ccw([S.T(p) for p in b["pts"]]), 0.2)
    if len(pts) < 3 or abs(G.signed_area(pts)) < 8:
        return None
    style = b["style"]
    h = float(b["h"])
    info = {"id": b["id"], "name": b.get("name"), "h": h, "style": style, "roof": b["roof"]}

    if b["cls"] == "canopy" or style == "canopy":
        z1, z0 = h, h - 0.35
        for a, c in zip(pts, pts[1:] + pts[:1]):
            vis.wall(a, c, z0, z1, "concrete")
        tris = G.triangulate([pts])
        vis.flat_tris(tris, z1, "roof_gravel", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        for t in tris:
            vis.flat(t, z0, "concrete", down=True)
        posts = G.inset(pts, 0.5) if len(pts) <= 8 else None
        for p in (posts or []):
            x, y = p
            for a, c in zip([(x - .15, y - .15), (x + .15, y - .15), (x + .15, y + .15), (x - .15, y + .15)],
                            [(x + .15, y - .15), (x + .15, y + .15), (x - .15, y + .15), (x - .15, y - .15)]):
                vis.wall(a, c, WALL_FOOT, z0, "metal_gray")
        if col is not None:
            for a, c in zip(pts, pts[1:] + pts[:1]):
                col.wall(a, c, z0, z1, "COL default")
            col.flat_tris(tris, z1, "COL default")
            for t in tris:
                col.flat(t, z0, "COL default", down=True)
        info["kind"] = "canopy"
        return info

    fh_target = floor_height(b)
    if b["roof"] == "hip":
        e_guess = h * 0.8 if b.get("h_src") == "landmark" else max(3.0, h - 1.0)
        inn, d = hip_inset(pts, min(4.5, 0.45 * e_guess))
        if inn is not None:
            rise = d * math.tan(ROOF_PITCH)
            eave = h - rise if b.get("h_src") == "landmark" else e_guess
            top = eave + rise
            floors = max(1, round(eave / fh_target))
            facade_walls(vis, pts, eave, style, eave / floors)
            roof_slopes(vis, pts, inn, eave, top, "roof_tile_red", S.tiles["roof_tile_red"])
            vis.flat_tris(G.triangulate([inn]), top, "roof_tile_red", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
            if col is not None:
                for a, c in zip(pts, pts[1:] + pts[:1]):
                    col.wall(a, c, 0.0, eave, "COL default")
                roof_slopes(col, pts, inn, eave, top, "COL default", 0.0)
                col.flat_tris(G.triangulate([inn]), top, "COL default", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
            info.update(kind="hip", eave=round(eave, 2), top=round(top, 2), floors=floors)
            if b["id"] in CLIMB_ROUTES and col is not None:
                info["climb_route"] = climb_route(S, b, pts, eave, False, style, vis, col)
            return info
        # inset failed: fall through to a flat roof

    par = 1.0 if h >= 6.0 else 0.6
    inn = G.inset(pts, PARAPET_T) or G.inset(pts, 0.2)
    eave = h - par if inn is not None else h
    floors = max(1, round(eave / fh_target))
    facade_walls(vis, pts, eave, style, eave / floors)
    if inn is not None:
        for a, c in zip(pts, pts[1:] + pts[:1]):
            vis.wall(a, c, eave, h, PARAPET_MAT[style])
        n = len(pts)
        for i in range(n):
            a, c = pts[i], pts[(i + 1) % n]
            ia, ic = inn[i], inn[(i + 1) % n]
            vis.wall(ic, ia, eave, h, "brick_red" if style != "glass" else "metal_gray")
            vis.poly([(a[0], a[1], h), (c[0], c[1], h), (ic[0], ic[1], h), (ia[0], ia[1], h)], COPING[style])
        roof_ring = inn
    else:
        roof_ring = pts
    tris = G.triangulate([roof_ring])
    vis.flat_tris(tris, eave, "roof_gravel", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
    if col is not None:
        n = len(pts)
        for a, c in zip(pts, pts[1:] + pts[:1]):
            col.wall(a, c, 0.0, h, "COL default")
        if inn is not None:
            # parapet: inner walls keep Mario on the roof (jump over it to leave); the 35 cm coping
            # has no floor (too narrow to stand on anyway), which saves 2 tris per edge
            for i in range(n):
                ia, ic = inn[i], inn[(i + 1) % n]
                col.wall(ic, ia, eave, h, "COL default")
        col.flat_tris(tris, eave, "COL default")
    info.update(kind="flat", eave=round(eave, 2), top=round(h, 2), floors=floors)
    if b["id"] in CLIMB_ROUTES and col is not None:
        info["climb_route"] = climb_route(S, b, pts, eave, True, style, vis, col)
    return info


# osm id -> facade to climb: compass facing of the facade, optional map point the route should be
# nearest to (else the facade's middle). Plaza-facing generic buildings (docs/game_design.md 5).
CLIMB_ROUTES = {
    "w196848214": {"name": "Peabody Hall", "facing": 270.0},
    "w196848217": {"name": "Criser Hall", "facing": 270.0, "near": (148.0, 172.0)},  # roof: red coins
    "w154223690": {"name": "Griffin-Floyd Hall", "facing": 90.0},
    "w154223807": {"name": "Anderson Hall", "facing": 210.0},
    "r2075617/154223654": {"name": "Leigh Hall", "facing": 90.0},
}
CANOPY_TOP, CANOPY_W, CANOPY_D, CANOPY_T = 3.0, 4.4, 2.0, 0.3
LEDGE_STEP, LEDGE_W, LEDGE_D, LEDGE_T, LEDGE_GAP = 3.0, 3.0, 1.1, 1.2, 0.8


def climb_route(S, b, pts, eave, flat, style, vis, col):
    """Entrance canopy + zigzag ledges on the facade edge of pts (stage coords, CCW) that best faces
    CLIMB_ROUTES[id]["facing"]. Returns a report dict or None."""
    cfg = CLIMB_ROUTES[b["id"]]
    fx, fy = math.sin(math.radians(cfg["facing"])), math.cos(math.radians(cfg["facing"]))
    near = S.T(cfg["near"]) if cfg.get("near") else None
    best = None
    for a, c in zip(pts, pts[1:] + pts[:1]):
        L = math.dist(a, c)
        if L < 12.0:
            continue
        nx, ny = (c[1] - a[1]) / L, -(c[0] - a[0]) / L  # outward
        mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        score = (nx * fx + ny * fy) * 2.0 + min(L, 40.0) / 40.0
        if near is not None:
            score -= G.seg_dist(near, a, c) / 15.0
        if best is None or score > best[0]:
            best = (score, a, c, L, (nx, ny), mid)
    if best is None:
        return None
    _, a, c, L, (nx, ny), mid = best
    ux, uy = (c[0] - a[0]) / L, (c[1] - a[1]) / L
    if near is not None:
        sc = (near[0] - a[0]) * ux + (near[1] - a[1]) * uy
    else:
        sc = L / 2
    span = (CANOPY_W / 2 + LEDGE_GAP + LEDGE_W)       # canopy left half .. right ledge column
    sc = max(CANOPY_W / 2 + 1.0, min(sc - (LEDGE_GAP + LEDGE_W) / 2, L - span - 1.0))
    mat = "limestone" if style in ("gothic", "brick", "service") else "concrete"
    top_limit = eave if not flat else eave + 0.2      # flat: the parapet top is eave + ~1 m

    def P(s, d):
        return (a[0] + ux * s + nx * d, a[1] + uy * s + ny * d)

    def slab(s0, s1, d, z0, z1, m, col_faces):
        # n is on the right of u (outward), so out-then-along-u turns left: CCW seen from above
        q = [P(s0, 0.0), P(s0, d), P(s1, d), P(s1, 0.0)]
        walls = [(q[0], q[1]), (q[1], q[2]), (q[2], q[3])]       # s0 end, front, s1 end (outward)
        for a_, b_ in walls:
            vis.wall(a_, b_, z0, z1, m)
        vis.flat(q, z1, m)
        vis.flat(q, z0, m, down=True)
        if col is None:
            return
        col.flat(q, z1, "COL default")
        if "front" in col_faces:
            for a_, b_ in walls:
                col.wall(a_, b_, z0, z1, "COL default")

    # entrance: door under a jump-through canopy (collision: top only)
    door_mark(vis, P(sc, 0.0), (nx, ny), (ux, uy), style)
    slab(sc - CANOPY_W / 2, sc + CANOPY_W / 2, CANOPY_D, CANOPY_TOP - CANOPY_T, CANOPY_TOP, "concrete", ())
    ledges = []
    k = 2
    while LEDGE_STEP * k <= top_limit + 1e-6:
        z1 = LEDGE_STEP * k
        if k % 2 == 0:   # right column, beside the canopy
            s0 = sc + CANOPY_W / 2 + LEDGE_GAP
        else:            # left column, over the canopy (6 m of headroom above it)
            s0 = sc + CANOPY_W / 2 - LEDGE_W
        slab(s0, s0 + LEDGE_W, LEDGE_D, z1 - LEDGE_T, z1, mat, ("front",))
        ledges.append(round(z1, 2))
        k += 1
    return {"facade_mid_m": [round(mid[0] + S.cx, 1), round(mid[1] + S.cy, 1)],
            "canopy_m": [round(P(sc, 1.0)[0] + S.cx, 2), round(P(sc, 1.0)[1] + S.cy, 2), CANOPY_TOP],
            "ledge_tops_m": ledges, "roof_m": round(eave, 2), "facing_deg": round(
                math.degrees(math.atan2(nx, ny)) % 360, 1)}


def door_mark(acc, p, n, u, style, width=2.2, height=2.7):
    """Plain entrance door (visual decal 5 cm proud of the wall)."""
    off = 0.05
    cx, cy = p[0] + n[0] * off, p[1] + n[1] * off
    hw = width / 2
    a = (cx - u[0] * hw, cy - u[1] * hw)
    b = (cx + u[0] * hw, cy + u[1] * hw)
    m = "window_glass" if style in ("band", "glass") else "door_wood"
    acc.wall(a, b, 0.0, height, m, [(0, 0), (1.1, 0), (1.1, 1.35), (0, 1.35)])


def build(S):
    vis = S.acc("Buildings visual", collision=False)
    back = S.acc("Backdrop buildings", collision=False)
    col = S.acc("Buildings collision", render=False)
    built = []
    for b in S.data["buildings"]:
        if b["id"] in S.replaced_ids or b["id"] in S.fallback_ids:
            continue
        if b["collide"]:
            info = build_one(S, b, vis, col)
        else:
            info = build_one(S, b, vis if b["in_window"] else back, None)
        if info:
            info["collision"] = bool(b["collide"])
            built.append(info)
    S.stats["buildings"] = built
    return built


# ------------------------------------------------------------------ door markers (fallback)
def door_on_footprint(S, osm_id, facing_deg):
    """Midpoint of the footprint edge facing closest to facing_deg (compass, 0 = north), prefer long
    edges. Returns (stage x, y, outward unit normal) or None."""
    b = next((x for x in S.data["buildings"] if x["id"] == osm_id), None)
    if b is None:
        return None
    pts = G.ccw([S.T(p) for p in b["pts"]])
    fx, fy = math.sin(math.radians(facing_deg)), math.cos(math.radians(facing_deg))
    best = None
    for a, c in zip(pts, pts[1:] + pts[:1]):
        L = math.dist(a, c)
        if L < 3.0:
            continue
        nx, ny = (c[1] - a[1]) / L, -(c[0] - a[0]) / L  # outward (right of a->c)
        score = (nx * fx + ny * fy) * 2.0 + min(L, 40.0) / 40.0
        if best is None or score > best[0]:
            best = (score, ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2), (nx, ny))
    if best is None:
        return None
    return best[1][0], best[1][1], best[2]


def door_marker(S, x, y, n, width=2.4, height=3.2):
    """Wooden double door with a UF orange + blue frame, 6 cm proud of the wall (visual only)."""
    acc = S.acc("Door markers", collision=False)
    nx, ny = n
    tx, ty = -ny, nx  # along the wall (left when facing the wall from outside -> right-handed)
    off = 0.06
    cx, cy = x + nx * off, y + ny * off
    hw = width / 2
    a = (cx + tx * hw, cy + ty * hw)
    b = (cx - tx * hw, cy - ty * hw)
    # door leaf (faces outward): wall(a -> b) has its normal on the right of a->b
    acc.wall(b, a, 0.0, height, "door_wood", [(0, 0), (1.2, 0), (1.2, 1.6), (0, 1.6)])
    f = 0.25
    fa = (cx + tx * (hw + f) + nx * 0.02, cy + ty * (hw + f) + ny * 0.02)
    fb = (cx - tx * (hw + f) + nx * 0.02, cy - ty * (hw + f) + ny * 0.02)
    a2 = (a[0] + nx * 0.02, a[1] + ny * 0.02)
    b2 = (b[0] + nx * 0.02, b[1] + ny * 0.02)
    acc.wall(a2, fa, 0.0, height + f, "door_marker")      # left jamb
    acc.wall(fb, b2, 0.0, height + f, "door_marker")      # right jamb
    acc.wall(fb, fa, height, height + f, "door_marker")    # lintel
