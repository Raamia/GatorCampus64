"""Set dressing for a campus stage (inside Blender, after the main meshes exist): UF lamp posts with
orange / blue banners (climbable: build_stage.py puts a vanilla bhvPoleGrabbing object on each one),
benches, Turlington Plaza's raised tree planters, the tabling tables that set up the Tabling
Gauntlet star (docs/game_design.md 5) and hammocks slung between climbable plaza oaks. Every item is checked against the stage's real collision
(build_stage.CollisionProbe) and roads before it is placed; blocked items move up to 1.5 m or are
skipped (listed in the build report).

Coordinates in the tables are MAP metres (x = east, y = north, origin Century Tower).
"""
import math

import stage_geom as G
from stage_nature import oak, trunk

# (x, y): Auditorium lawn walks (first view from the spawn), the porch approach, Turlington Plaza
# (the strip east of Turlington's diagonal facade, around The Potato) and the paved plaza between
# Turlington's podium (OSM outline down to y = -16) and Marston (north face y = -67)
LAMPS = [
    (26.8, 96.5), (49.6, 96.5), (14.0, 88.6), (62.0, 88.6), (2.0, 88.6), (74.0, 88.6),
    (31.0, 68.4), (45.8, 68.4),
    (-48.0, 12.0), (-48.0, -14.0), (-75.0, -16.0), (-102.0, -18.0), (-120.0, -22.0), (-40.0, 40.0),
]
LAMP_POLE_M = 4.3          # pole hitbox (lantern bottom); bhvPoleGrabbing bparam2 = height / 10 cm
# (x, y, facing): the seat faces `facing` (compass)
BENCHES = [
    (20.0, 89.0, 0.0), (56.0, 89.0, 0.0), (20.0, 93.6, 180.0), (56.0, 93.6, 180.0),
    (-60.0, -3.0, 90.0), (-88.0, -33.0, 0.0), (-38.0, 34.0, 225.0),
]
PLANTERS = [(-78.0, -15.5), (-56.0, -38.0), (-38.0, -48.0)]     # 5 x 5 m, 0.7 m, live oak
# tabling tables by the breezeway's east mouth (Turlington steps, the Tabling Gauntlet start)
TABLES = [(-50.0, 17.0), (-50.0, 10.0), (-42.0, 14.0)]
NUDGES = [(0.0, 0.0), (1.5, 0.0), (-1.5, 0.0), (0.0, 1.5), (0.0, -1.5), (1.5, 1.5), (-1.5, -1.5),
          (1.5, -1.5), (-1.5, 1.5), (3.0, 0.0), (-3.0, 0.0), (0.0, 3.0), (0.0, -3.0)]


def _on_road(S, x, y, pad):
    for r in S.data["roads"]:
        hw = r["width"] / 2 + pad
        pts = [S.T(p) for p in r["pts"]]
        for a, b in zip(pts, pts[1:]):
            if G.seg_dist((x, y), a, b) < hw:
                return True
    return False


def _on_walk(S, x, y, pad):
    for p in S.data["paths"]:
        if p["id"] in S.replaced_ways:
            continue
        hw = p["width"] / 2 + pad
        pts = [S.T(q) for q in p["pts"]]
        for a, b in zip(pts, pts[1:]):
            if G.seg_dist((x, y), a, b) < hw:
                return True
    return False


def _place(S, probe, taken, mx, my, radius, walk_pad=None):
    """First nudge of map point (mx, my) with ground floor (z ~ 0), no collision within radius at
    0.6 m and 2.0 m, off roads (and walks when walk_pad is set) and away from items already placed.
    Returns stage (x, y) or None."""
    x0, y0 = S.T((mx, my))
    for dx, dy in NUDGES:
        x, y = x0 + dx, y0 + dy
        fz = probe.floor(x, y, 3.0)
        if fz is None or abs(fz) > 0.05 or probe.inside(x, y, 0.6):
            continue
        roof = probe.floor(x, y, 150.0)      # open sky above (no roof, overhang or canopy)
        if roof is not None and roof > 0.3:
            continue
        if _on_road(S, x, y, 0.6 + radius * 0.5):
            continue
        if walk_pad is not None and _on_walk(S, x, y, walk_pad):
            continue
        if any(math.dist((x, y), (tx, ty)) < radius + tr for tx, ty, tr in taken):
            continue
        if min(probe.clearance(x, y, 0.6, radius + 0.5), probe.clearance(x, y, 2.0, radius + 0.5)) < radius:
            continue
        return x, y
    return None


def _obox(acc, cx, cy, ang, hx, hy, z0, z1, side, top, bottom=None):
    """Oriented box (centre, half sizes along / across ang), outward faces."""
    c, s = math.cos(ang), math.sin(ang)

    def P(u, v):
        return (cx + c * u - s * v, cy + s * u + c * v)
    q = [P(-hx, -hy), P(hx, -hy), P(hx, hy), P(-hx, hy)]       # CCW
    for a, b in zip(q, q[1:] + q[:1]):
        acc.wall(a, b, z0, z1, side)
    if top:
        acc.flat(q, z1, top)
    if bottom:
        acc.flat(q, z0, bottom, down=True)
    return q


def lamp(vis, x, y, key, yaw):
    """Black lamp post, white lantern, one orange and one blue banner (visual only)."""
    _obox(vis, x, y, yaw, 0.2, 0.2, -0.1, 0.45, "dark_trim", "dark_trim")
    trunk(vis, x, y, 0.08, 0.45, LAMP_POLE_M, 5, "dark_trim", key)
    _obox(vis, x, y, yaw, 0.22, 0.22, LAMP_POLE_M, LAMP_POLE_M + 0.5, "white_trim", None, "dark_trim")
    cap = [(x + 0.3 * math.cos(yaw + k * math.pi / 2 + math.pi / 4) * 1.414,
            y + 0.3 * math.sin(yaw + k * math.pi / 2 + math.pi / 4) * 1.414, LAMP_POLE_M + 0.5) for k in range(4)]
    for a, b in zip(cap, cap[1:] + cap[:1]):
        vis.poly([a, b, (x, y, LAMP_POLE_M + 0.85)], "dark_trim")
    vis.poly(cap[::-1], "dark_trim")
    for side, mat in ((1, "banner_orange"), (-1, "banner_blue")):
        ux, uy = math.cos(yaw) * side, math.sin(yaw) * side
        a = (x + ux * 0.12, y + uy * 0.12)
        b = (x + ux * 0.72, y + uy * 0.72)
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        vis.wall(a, b, 2.45, 3.75, mat, uv)                     # both faces of the banner
        vis.wall(b, a, 2.45, 3.75, mat, [(1, 0), (0, 0), (0, 1), (1, 1)])
        _obox(vis, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, yaw, 0.32, 0.03, 3.75, 3.82, "dark_trim", "dark_trim")


def bench(vis, col, x, y, facing):
    """Park bench, 1.8 m: wooden seat at 0.46 m, backrest, metal ends. Collision: the seat block."""
    f = math.radians(facing)
    fx, fy = math.sin(f), math.cos(f)            # the way a sitter looks
    ang = math.atan2(-fx, fy)                     # bench length axis (perpendicular to facing)
    _obox(vis, x, y, ang, 0.9, 0.24, 0.40, 0.48, "door_wood", "door_wood", "door_wood")
    for k in (-1, 1):
        ex, ey = x + math.cos(ang) * 0.85 * k, y + math.sin(ang) * 0.85 * k
        _obox(vis, ex, ey, ang, 0.04, 0.24, -0.05, 0.40, "metal_gray", None)
    bx, by = x - fx * 0.22, y - fy * 0.22
    _obox(vis, bx, by, ang, 0.9, 0.03, 0.55, 0.95, "door_wood", "door_wood")
    if col is not None:
        _obox(col, x, y, ang, 0.9, 0.25, 0.0, 0.48, "COL default", "COL default")


def planter(vis, col, x, y, key):
    """Raised brick tree planter (5 x 5 m, 0.7 m) with limestone coping and a live oak."""
    h, hw, rim = 0.7, 2.5, 0.3
    q = _obox(vis, x, y, 0.0, hw, hw, -0.1, h, "brick_red", None)
    inner = [(x - hw + rim, y - hw + rim), (x + hw - rim, y - hw + rim), (x + hw - rim, y + hw - rim),
             (x - hw + rim, y + hw - rim)]
    for (a, b), (ia, ib) in zip(zip(q, q[1:] + q[:1]), zip(inner, inner[1:] + inner[:1])):
        vis.poly([(a[0], a[1], h), (b[0], b[1], h), (ib[0], ib[1], h), (ia[0], ia[1], h)], "limestone")
        vis.wall(ib, ia, 0.55, h, "brick_red")
    vis.flat(inner, 0.55, "mulch")
    oak(vis, x, y, key, 3.0)
    if col is not None:
        _obox(col, x, y, 0.0, hw, hw, 0.0, h, "COL default", "COL default")


def table(vis, col, x, y, mat):
    """Folding table with a UF-coloured cloth (1.8 x 0.75 m, 0.76 m high)."""
    _obox(vis, x, y, 0.0, 0.9, 0.375, 0.10, 0.76, mat, "white_trim")
    _obox(vis, x, y, 0.0, 0.86, 0.34, -0.05, 0.10, "metal_gray", None)
    # a tri-fold poster on the table
    vis.poly([(x - 0.35, y + 0.05, 0.76), (x + 0.35, y + 0.05, 0.76), (x + 0.35, y + 0.0, 1.25),
              (x - 0.35, y + 0.0, 1.25)], "white_trim")
    vis.poly([(x - 0.35, y + 0.0, 1.25), (x + 0.35, y + 0.0, 1.25), (x + 0.35, y + 0.05, 0.76),
              (x - 0.35, y + 0.05, 0.76)], "banner_blue" if mat == "banner_orange" else "banner_orange",
             [(0, 1), (1, 1), (1, 0), (0, 0)])
    if col is not None:
        _obox(col, x, y, 0.0, 0.9, 0.375, 0.0, 0.76, "COL default", "COL default")


def hammock(vis, col, a, b, mats):
    """Hammock slung between two trunks (stage points a, b): a V-shaped sling 0.9 m wide from 1.5 m
    at the trunks to 0.85 m in the middle. Collision: the middle of the sling (16-20 degree slopes,
    walkable), so it is a low thing to hop onto."""
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -uy, ux
    hw = 0.45

    def P(t, side, z):
        return (a[0] + ux * L * t + nx * hw * side, a[1] + uy * L * t + ny * hw * side, z)
    t0, t1 = 0.35 / L, 1.0 - 0.35 / L
    z_end, z_mid = 1.5, 0.85
    for (ta, tb, za, zb), m in (((t0, 0.5, z_end, z_mid), mats[0]), ((0.5, t1, z_mid, z_end), mats[1])):
        q = [P(ta, -1, za), P(tb, -1, zb), P(tb, 1, zb), P(ta, 1, za)]
        vis.poly(q, m, [(0, 0), (1, 0), (1, 1), (0, 1)])
        vis.poly(q[::-1], m, [(0, 1), (1, 1), (1, 0), (0, 0)])
    for t, z in ((t0, z_end), (t1, z_end)):          # rope knots on the trunks
        c = P(t, 0, z)
        vis.poly([(c[0] - nx * 0.5, c[1] - ny * 0.5, z + 0.05), (c[0] + nx * 0.5, c[1] + ny * 0.5, z + 0.05),
                  (c[0] + nx * 0.5, c[1] + ny * 0.5, z - 0.05), (c[0] - nx * 0.5, c[1] - ny * 0.5, z - 0.05)],
                 "dark_trim")
    if col is not None:
        k0, k1 = 0.5 - (0.5 - t0) * 0.7, 0.5 + (t1 - 0.5) * 0.7
        zk = z_mid + (z_end - z_mid) * 0.7
        col.poly([P(k0, -1, zk), P(0.5, -1, z_mid), P(0.5, 1, z_mid), P(k0, 1, zk)], "COL default")
        col.poly([P(0.5, -1, z_mid), P(k1, -1, zk), P(k1, 1, zk), P(0.5, 1, z_mid)], "COL default")


def pick_hammocks(S, probe, n=3):
    """Pairs of climbable plaza oaks 3.6-5.5 m apart with an open, walk-free span between them."""
    trees = [t["stage"] for t in S.pole_trees]
    others = [S.T(t["pt"]) for t in S.data["trees"] if t["id"] not in S.removed_points]
    pairs = []
    for i in range(len(trees)):
        for j in range(i + 1, len(trees)):
            a, b = trees[i], trees[j]
            d = math.dist(a, b)
            if not 3.6 <= d <= 5.5:
                continue
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if _on_walk(S, mid[0], mid[1], 0.6) or _on_road(S, mid[0], mid[1], 1.0):
                continue
            if any(G.seg_dist(o, a, b) < 0.9 and math.dist(o, a) > 0.5 and math.dist(o, b) > 0.5 for o in others):
                continue
            if probe.clearance(mid[0], mid[1], 0.9, 2.0) < 1.5:
                continue
            pairs.append((math.dist(mid, trees[0]), a, b))
    out, used = [], set()
    for _, a, b in sorted(pairs):
        if a in used or b in used:
            continue
        out.append((a, b))
        used.update((a, b))
        if len(out) >= n:
            break
    return out


def build(S, probe, avoid=()):
    """Place the dressing; returns pole objects [{name, stage (x, y), z, height_m}] for build_stage.
    avoid = [(stage x, y, radius)] kept clear (spawn, signs, climbable trees)."""
    vis = S.acc("Dressing visual", collision=False)
    col = S.acc("Dressing collision", render=False)
    taken = list(avoid)
    rep = {"lamps": [], "benches": [], "planters": [], "tables": [], "skipped": []}
    poles = []
    for i, (mx, my) in enumerate(PLANTERS):
        p = _place(S, probe, taken, mx, my, 3.6, walk_pad=0.2)
        if p is None:
            rep["skipped"].append(("planter", mx, my))
            continue
        planter(vis, col, p[0], p[1], f"planter{i}")
        taken.append((p[0], p[1], 3.6))
        rep["planters"].append([round(p[0] + S.cx, 1), round(p[1] + S.cy, 1)])
    for i, (mx, my) in enumerate(TABLES):
        p = _place(S, probe, taken, mx, my, 1.3)
        if p is None:
            rep["skipped"].append(("table", mx, my))
            continue
        table(vis, col, p[0], p[1], "banner_orange" if i % 2 == 0 else "banner_blue")
        taken.append((p[0], p[1], 1.3))
        rep["tables"].append([round(p[0] + S.cx, 1), round(p[1] + S.cy, 1)])
    for i, (mx, my, facing) in enumerate(BENCHES):
        p = _place(S, probe, taken, mx, my, 1.1, walk_pad=0.15)
        if p is None:
            rep["skipped"].append(("bench", mx, my))
            continue
        bench(vis, col, p[0], p[1], facing)
        taken.append((p[0], p[1], 1.1))
        rep["benches"].append([round(p[0] + S.cx, 1), round(p[1] + S.cy, 1)])
    for i, (mx, my) in enumerate(LAMPS):
        p = _place(S, probe, taken, mx, my, 1.4, walk_pad=0.3)
        if p is None:
            rep["skipped"].append(("lamp", mx, my))
            continue
        yaw = 0.0 if i % 2 == 0 else math.pi / 2
        lamp(vis, p[0], p[1], f"lamp{i}", yaw)
        taken.append((p[0], p[1], 1.4))
        poles.append({"name": f"Lamp post {i:02d}", "stage": p, "z": 0.0, "height_m": LAMP_POLE_M})
        rep["lamps"].append([round(p[0] + S.cx, 1), round(p[1] + S.cy, 1)])
    rep["hammocks"] = []
    for k, (a, b) in enumerate(pick_hammocks(S, probe)):
        mats = ("banner_orange", "banner_blue") if k % 2 == 0 else ("banner_blue", "banner_orange")
        hammock(vis, col, a, b, mats)
        rep["hammocks"].append([[round(a[0] + S.cx, 1), round(a[1] + S.cy, 1)],
                                [round(b[0] + S.cx, 1), round(b[1] + S.cy, 1)]])
    S.stats["dressing"] = rep
    print(f"SGL: dressing: {len(rep['lamps'])} lamp posts, {len(rep['benches'])} benches, "
          f"{len(rep['planters'])} planters, {len(rep['tables'])} tables, {len(rep['hammocks'])} hammocks; "
          f"skipped {rep['skipped']}")
    return poles
