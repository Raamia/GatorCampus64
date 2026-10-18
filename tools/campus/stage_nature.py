"""Low-poly trees (live oaks, pines, sabal palms) from the OSM tree points + mapped woods, thin trunk
colliders for trees inside the play zone, and the cut-out tree-line ring at the edge of the visual
extent that hides where the ground ends.

Live oaks carry their crowns 4.5-6 m up (mature plaza oaks are 15-20 m tall), above where Lakitu
flies when Mario walks under them. Up to MAX_POLE_TREES plaza oaks near the walks and the spawn are
CLIMBABLE: they get no static collider; build_stage.py places a vanilla bhvTree object (MODEL_NONE,
a 5 m pole hitbox that also pushes Mario away like a trunk) on each one (S.pole_trees)."""
import hashlib
import math

import stage_geom as G

PLAZA_POLE_BOX = (0.0, 118.0, 112.0, 238.0)   # map metres: Plaza of the Americas (x0, y0, x1, y1)
MAX_POLE_TREES = 28
POLE_MIN_SPACING = 4.5      # m between climbable trees (bhv_pole_base_loop pushes Mario to 0.7 m)
POLE_TREE_HITBOX_M = 5.0    # bhvTree: SET_HITBOX(80, 500); Mario climbs to 4 m and handstands on top

# Hand-authored live oaks, map metres from Century Tower. The road rows frame Newell Drive while
# staying on its grass verges; the facade pair breaks up the Auditorium's west lawn wall, and the
# tower pair frames (rather than blocks) the landmark. Existing OSM trees remain untouched.
HUB_AUDITORIUM_GROVE_OAKS = [(12.0, 166.0), (1.0, 153.0), (86.0, 124.0),
                             (-2.0, 105.0), (62.0, 108.0), (5.0, 100.0), (60.0, 160.0),
                             (20.0, 125.0), (42.0, 137.0), (8.0, 83.0), (50.0, 78.0),
                             (82.0, 43.0), (78.0, 58.0), (66.0, 35.0)]
HUB_ROADSIDE_OAKS = [(-38.0, 90.0), (-40.0, 45.0), (-38.0, 25.0), (-38.0, -8.0),
                     (-8.0, 80.0), (-8.0, 60.0), (-8.0, 35.0)]
HUB_AUDITORIUM_FACADE_OAKS = [(15.0, 48.0), (15.0, 31.0)]
HUB_TOWER_FLANK_OAKS = [(-30.0, 8.0), (10.0, -10.0)]
HUB_LARGE_OAKS = set(HUB_AUDITORIUM_FACADE_OAKS + [(-30.0, 8.0)])
HUB_OAKS = (HUB_AUDITORIUM_GROVE_OAKS + HUB_ROADSIDE_OAKS +
            HUB_AUDITORIUM_FACADE_OAKS + HUB_TOWER_FLANK_OAKS)


def rnd(key, lo=0.0, hi=1.0):
    v = int(hashlib.md5(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * v


def ring(cx, cy, r, z, n, rot, key, jitter=0.15, ry=None):
    ry = r if ry is None else ry
    out = []
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        k = 1.0 + rnd(f"{key}:{i}", -jitter, jitter)
        out.append((cx + math.cos(a) * r * k, cy + math.sin(a) * ry * k, z))
    return out


def blob(acc, rings, top, bottom, mat):
    """Closed blob from stacked rings (bottom to top), with fan caps at points `bottom` / `top`."""
    n = len(rings[0])
    if bottom is not None:
        r0 = rings[0]
        for i in range(n):
            acc.poly([bottom, r0[(i + 1) % n], r0[i]], mat)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            acc.poly([lo[i], lo[j], hi[j], hi[i]], mat)
    if top is not None:
        r1 = rings[-1]
        for i in range(n):
            acc.poly([r1[i], r1[(i + 1) % n], top], mat)


def trunk(acc, x, y, r, z0, z1, sides, mat, key, lean=(0.0, 0.0)):
    pts0 = [(x + math.cos(2 * math.pi * i / sides + 0.3) * r, y + math.sin(2 * math.pi * i / sides + 0.3) * r)
            for i in range(sides)]
    pts1 = [(px + lean[0], py + lean[1]) for px, py in pts0]
    for i in range(sides):
        j = (i + 1) % sides
        acc.poly([(pts0[i][0], pts0[i][1], z0), (pts0[j][0], pts0[j][1], z0),
                  (pts1[j][0], pts1[j][1], z1), (pts1[i][0], pts1[i][1], z1)], mat)


def oak(acc, x, y, key, clear, crown=None, pole=False):
    """Southern live oak: trunk to a crown 4.5-6 m up, wide crown; big ones get a second lobe.
    pole=True: a climbable tree (bhvTree object): a slim trunk Mario's climbing pose fits around,
    crown above the 5 m pole top so his handstand on top stays visible."""
    R = rnd(key + "R", 4.5, 7.5) if not crown else min(crown / 2, 10.0)
    R = max(2.5, min(R, clear + 1.5))
    ht = rnd(key + "ht", 5.4, 6.0) if pole else rnd(key + "ht", 4.5, 6.0)
    H = R * rnd(key + "H", 0.85, 1.2)
    rot = rnd(key + "rot", 0, math.pi)
    mat = "leaves_oak" if rnd(key + "m") < 0.6 else "leaves_oak2"
    tr = 0.3 if pole else rnd(key + "tr", 0.32, 0.5)
    trunk(acc, x, y, tr, -0.15, ht + 0.6, 5, "bark", key)
    z0 = ht
    rings = [ring(x, y, 0.55 * R, z0, 8, rot, key + "a"),
             ring(x, y, R, z0 + 0.35 * H, 8, rot + 0.2, key + "b"),
             ring(x, y, 0.72 * R, z0 + 0.78 * H, 8, rot + 0.4, key + "c")]
    blob(acc, rings, (x, y, z0 + H), (x, y, z0 - 0.2), mat)
    if R > 5.0:  # second, smaller lobe pushed out to one side and up
        a = rnd(key + "la", 0, 2 * math.pi)
        r2 = R * rnd(key + "lr", 0.45, 0.6)
        lx, ly = x + math.cos(a) * R * 0.45, y + math.sin(a) * R * 0.45
        lz = z0 + 0.45 * H
        blob(acc, [ring(lx, ly, 0.6 * r2, lz, 6, rot + 1, key + "d"),
                   ring(lx, ly, r2, lz + 0.4 * r2, 6, rot + 1.3, key + "e")],
             (lx, ly, lz + 1.1 * r2), (lx, ly, lz - 0.2), mat)
    return 0.45


def _branch(acc, a, b, r0, r1, mat, key, sides=5):
    """Low-poly tapered branch between 3D points."""
    d = [b[i] - a[i] for i in range(3)]
    length = math.sqrt(sum(v * v for v in d)) or 1.0
    axis = [v / length for v in d]
    ref = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = (axis[1] * ref[2] - axis[2] * ref[1], axis[2] * ref[0] - axis[0] * ref[2],
         axis[0] * ref[1] - axis[1] * ref[0])
    ul = math.sqrt(sum(v * v for v in u)) or 1.0
    u = tuple(v / ul for v in u)
    v = (axis[1] * u[2] - axis[2] * u[1], axis[2] * u[0] - axis[0] * u[2],
         axis[0] * u[1] - axis[1] * u[0])
    for i in range(sides):
        j = (i + 1) % sides
        def pt(c, r, k):
            ang = 2 * math.pi * k / sides + rnd(key, 0, 0.4)
            return tuple(c[q] + r * (u[q] * math.cos(ang) + v[q] * math.sin(ang)) for q in range(3))
        acc.poly([pt(a, r0, i), pt(a, r0, j), pt(b, r1, j), pt(b, r1, i)], mat)


def live_oak(acc, col, x, y, key, scale=1.0):
    """Broad, low-spreading southern live oak with a trunk-only simple collider."""
    trunk_r = 0.72 * scale
    base_z, branch_z = -0.1, 3.15 * scale
    trunk(acc, x, y, trunk_r, base_z, branch_z + 0.25, 7, "bark", key,
          lean=(rnd(key + ":leanx", -0.22, 0.22), rnd(key + ":leany", -0.18, 0.18)))
    rot = rnd(key + ":rot", 0, 2 * math.pi)
    reach = 8.0 * scale
    tips = []
    for i in range(4):
        a = rot + i * math.pi / 2 + rnd(f"{key}:branch{i}", -0.18, 0.18)
        r = reach * rnd(f"{key}:reach{i}", 0.78, 1.0)
        start = (x + math.cos(a) * 0.4, y + math.sin(a) * 0.4, branch_z)
        tip = (x + math.cos(a) * r, y + math.sin(a) * r, branch_z + rnd(f"{key}:lift{i}", 0.6, 1.1))
        _branch(acc, start, tip, 0.43 * scale, 0.18 * scale, "bark", f"{key}:limb{i}")
        tips.append((tip[0], tip[1], tip[2] + 0.5 * scale, a))
    for i, (cx, cy, cz, a) in enumerate(tips):
        R = (4.5 if i % 2 == 0 else 4.0) * scale
        H = 3.5 * scale
        mat = "leaves_oak" if i % 2 == 0 else "leaves_oak2"
        rings = [ring(cx, cy, 0.62 * R, cz, 8, rot, f"{key}:c{i}a", jitter=0.13, ry=0.78 * R),
                 ring(cx, cy, R, cz + 0.25 * H, 8, rot + 0.2, f"{key}:c{i}b", jitter=0.12, ry=0.78 * R),
                 ring(cx, cy, 0.72 * R, cz + 0.82 * H, 8, rot + 0.4, f"{key}:c{i}c", jitter=0.12, ry=0.8 * R)]
        blob(acc, rings, (cx, cy, cz + H), (cx, cy, cz - 0.45 * scale), mat)
        # A few short moss strands hang from the lower, outer canopy edge.
        if i in (0, 2):
            mx, my = cx + math.cos(a) * 1.2 * scale, cy + math.sin(a) * 1.2 * scale
            for j, side in enumerate((-1, 1)):
                xx, yy = mx + math.cos(a + math.pi / 2) * side * 0.55 * scale, my + math.sin(a + math.pi / 2) * side * 0.55 * scale
                p0, p1 = (xx, yy, cz + 0.35 * scale), (xx + 0.35 * math.cos(a), yy + 0.35 * math.sin(a), cz - 1.7 * scale)
                acc.wall(p0[:2], p1[:2], p1[2], p0[2], "spanish_moss", [(0, 0), (1, 0), (1, 1), (0, 1)])
                acc.wall(p1[:2], p0[:2], p1[2], p0[2], "spanish_moss", [(1, 0), (0, 0), (0, 1), (1, 1)])
    # Small transparent blotches (not one broad rectangle) make a readable dappled shadow.
    shade_centres = ((-4.2, -3.4), (2.5, -4.1), (5.0, 0.8), (-3.8, 3.0), (2.0, 4.3))
    for i, (ox, oy) in enumerate(shade_centres):
        cx, cy = x + ox * scale, y + oy * scale
        a = rnd(f"{key}:shade{i}", -0.45, 0.45)
        hx, hy = 3.15 * scale, 2.2 * scale
        c, s = math.cos(a), math.sin(a)
        q = [(cx + c * u - s * v, cy + s * u + c * v, -0.02)
             for u, v in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
        acc.poly(q, "oak_shadow", [(0, 0), (1, 0), (1, 1), (0, 1)])
    # Eight short wall faces form a conservative trunk collider; canopy/moss/shade stay non-colliding.
    if col is not None:
        pts = [(x + math.cos(rot + 2 * math.pi * i / 8) * trunk_r,
                y + math.sin(rot + 2 * math.pi * i / 8) * trunk_r) for i in range(8)]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            col.wall(a, b, 0.0, 3.2 * scale, "COL default")


def _path_clearance(S, p):
    best = 999.0
    for line in S.data["paths"]:
        if line["id"] in S.replaced_ways:
            continue
        pts = line["pts"]
        for a, b in zip(pts, pts[1:]):
            best = min(best, G.seg_dist(p, a, b) - line["width"] / 2)
    for line in S.data["roads"]:
        for a, b in zip(line["pts"], line["pts"][1:]):
            best = min(best, G.seg_dist(p, a, b) - line["width"] / 2)
    return best


def pine(acc, x, y, key, clear):
    ht = rnd(key + "ht", 9.0, 13.0)
    R = max(1.8, min(rnd(key + "R", 2.4, 3.4), clear + 1.0))
    H = rnd(key + "H", 4.5, 6.0)
    rot = rnd(key + "rot", 0, math.pi)
    trunk(acc, x, y, 0.28, -0.15, ht + 1.0, 5, "bark", key)
    rings = [ring(x, y, 0.8 * R, ht, 6, rot, key + "a"), ring(x, y, R, ht + 0.45 * H, 6, rot + 0.3, key + "b")]
    blob(acc, rings, (x, y, ht + H), (x, y, ht - 0.6), "leaves_pine")
    return 0.32


def palm(acc, x, y, key, clear):
    ht = rnd(key + "ht", 6.0, 9.5)
    lean = (rnd(key + "lx", -0.5, 0.5), rnd(key + "ly", -0.5, 0.5))
    trunk(acc, x, y, 0.24, -0.15, ht, 5, "palm_trunk", key, lean)
    tx, ty, tz = x + lean[0], y + lean[1], ht
    n = 7
    rot = rnd(key + "rot", 0, math.pi)
    L = max(2.2, min(rnd(key + "L", 2.8, 3.6), clear + 1.5))
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        droop = rnd(f"{key}d{i}", 0.6, 1.4)
        base = (tx, ty, tz + 0.2)
        mid = L * 0.55
        tip = (tx + ca * L, ty + sa * L, tz - droop)
        ml = (tx + ca * mid - sa * 0.55, ty + sa * mid + ca * 0.55, tz + 0.25)
        mr = (tx + ca * mid + sa * 0.55, ty + sa * mid - ca * 0.55, tz + 0.25)
        acc.poly([base, mr, tip, ml], "palm_frond")
        acc.poly([base, ml, tip, mr], "palm_frond")  # back side
    blob(acc, [ring(tx, ty, 0.5, tz - 0.4, 5, rot, key + "h")], (tx, ty, tz + 0.5), None, "palm_frond")
    return 0.26


def _walk_dist(S, pt, grid):
    gx, gy = int(pt[0] // 20), int(pt[1] // 20)
    best = 99.0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for a, b, hw in grid.get((gx + dx, gy + dy), ()):
                best = min(best, G.seg_dist(pt, a, b) - hw)
    return best


def pick_pole_trees(S, avoid=()):
    """Plaza oaks that become climbable bhvTree poles: nearest the walks and the spawn, at least
    POLE_MIN_SPACING apart, not on a walk, with room around the trunk. avoid = [(map x, y, r)]."""
    d = S.data
    grid = {}
    for p in d["paths"]:
        if p["id"] in S.replaced_ways:
            continue
        pts = [tuple(q) for q in p["pts"]]
        for a, b in zip(pts, pts[1:]):
            for k in {(int(a[0] // 20), int(a[1] // 20)), (int(b[0] // 20), int(b[1] // 20)),
                      (int((a[0] + b[0]) / 2 // 20), int((a[1] + b[1]) / 2 // 20))}:
                grid.setdefault(k, []).append((a, b, p["width"] / 2))
    x0, y0, x1, y1 = PLAZA_POLE_BOX
    spawn = avoid[0][:2] if avoid else ((x0 + x1) / 2, (y0 + y1) / 2)
    cands = []
    for t in d["trees"]:
        if t["kind"] != "oak" or t["id"] in S.removed_points or t["id"] in S.replaced_ids:
            continue
        px, py = t["pt"]
        if not (x0 < px < x1 and y0 < py < y1) or t["clear"] < 2.0:
            continue
        wd = _walk_dist(S, (px, py), grid)
        if wd < 1.0:        # trunk on (or at the edge of) a walk
            continue
        if any(math.dist((px, py), (ax, ay)) < r for ax, ay, r in avoid):
            continue
        cands.append((math.dist((px, py), spawn) + 3.0 * max(0.0, wd - 1.5), t))
    picked = []
    for _, t in sorted(cands, key=lambda c: c[0]):
        if len(picked) >= MAX_POLE_TREES:
            break
        if all(math.dist(t["pt"], q["pt"]) >= POLE_MIN_SPACING for q in picked):
            picked.append(t)
    return {t["id"] for t in picked}


def build(S, pole_avoid=()):
    d = S.data
    vis = S.acc("Trees visual", collision=False)
    col = S.acc("Trees collision", render=False)
    px0, py0, px1, py1 = S.play_local
    counts = {"oak": 0, "pine": 0, "palm": 0, "colliders": 0, "climbable": 0}
    poles = pick_pole_trees(S, pole_avoid)
    S.pole_trees = []
    curated = []
    if getattr(S, "key", "hub") == "hub":
        for i, pt in enumerate(HUB_OAKS):
            # Keep the heavy trunk off paths/roads and buildings. A nearby mapped tree is replaced
            # visually by the authored tree so this does not double the canopy at one point.
            if _path_clearance(S, pt) < 1.25:
                continue
            if any(G.point_in_poly(pt, b["pts"]) for b in d["buildings"]):
                continue
            if any(math.dist(pt, q) < 7.0 for q in curated):
                continue
            x, y = S.T(pt)
            scale = (1.28 if pt == (50.0, 78.0) else
                     (1.12 if pt in HUB_LARGE_OAKS else (1.0 if i < 2 else 0.92)))
            live_oak(vis, col, x, y, f"hub_live_oak_{i}", scale)
            curated.append(pt)
        S.hub_oak_pts = curated
        counts["hand_authored_oaks"] = len(curated)
        counts["hand_authored_positions_m"] = [[round(x, 2), round(y, 2)] for x, y in curated]
    # crowns reach up to ~10.5 m from the trunk: a tree closer than that to the s16 vertex limit
    # (327.67 m from the stage centre) would wrap around; out there it is behind the tree line anyway
    lim = 327.0 - 10.5
    counts["beyond_s16"] = 0
    holes = getattr(S, "ground_holes", None) or []     # landmark ground holes (no ground to stand on)
    counts["in_ground_hole"] = 0
    for t in d["trees"]:
        if getattr(S, "key", "hub") == "hub" and any(math.dist(t["pt"], q) < 7.5 for q in curated):
            continue
        if t["id"] in S.removed_points or t["id"] in S.replaced_ids:
            continue
        x, y = S.T(t["pt"])
        if max(abs(x), abs(y)) > lim:
            counts["beyond_s16"] += 1
            continue
        if holes and any(G.point_in_poly((x, y), h) for h in holes):
            counts["in_ground_hole"] += 1
            continue
        key = t["id"]
        kind = t["kind"]
        if kind == "palm":
            r = palm(vis, x, y, key, t["clear"])
        elif kind == "pine":
            r = pine(vis, x, y, key, t["clear"])
        else:
            r = oak(vis, x, y, key, t["clear"], t.get("crown"), pole=key in poles)
        counts[kind] += 1
        if key in poles:
            S.pole_trees.append({"id": key, "map_m": tuple(t["pt"]), "stage": (x, y)})
            counts["climbable"] += 1
            continue
        if px0 + 1 < x < px1 - 1 and py0 + 1 < y < py1 - 1:
            tri = [(x + math.cos(a) * (r + 0.12), y + math.sin(a) * (r + 0.12))
                   for a in (0.5, 0.5 + 2 * math.pi / 3, 0.5 + 4 * math.pi / 3)]
            for a, b in zip(tri, tri[1:] + tri[:1]):
                col.wall(a, b, 0.0, 3.0, "COL nocam")
            counts["colliders"] += 1
    S.stats["trees"] = counts
    treeline(S)


def treeline(S):
    """Two staggered rows of cut-out tree crowns + a solid green wall at the edge of the visual
    extent, so no camera position inside the play zone sees the ground end."""
    acc = S.acc("Tree line", collision=False)
    H = S.data["extent_half_m"]
    rows = [(H - 18.0, 15.0, 0.0, "treeline"), (H - 8.0, 19.0, 0.37, "treeline")]
    for half, height, phase, mat in rows:
        corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            L = math.dist(a, b)
            nseg = math.ceil(L / 24.0)
            for k in range(nseg):
                t0, t1 = k / nseg, (k + 1) / nseg
                p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
                p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
                hh = height * rnd(f"tl{half}:{a}:{k}", 0.8, 1.2)
                u0 = phase + rnd(f"tlu{half}:{a}:{k}", 0, 1)
                u1 = u0 + math.dist(p0, p1) / 24.0
                # faces inward (towards the stage centre)
                acc.wall(p1, p0, -0.2, hh, mat, [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)])
    half = H - 0.5
    corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        L = math.dist(a, b)
        nseg = math.ceil(L / 40.0)
        for k in range(nseg):
            p0 = (a[0] + (b[0] - a[0]) * k / nseg, a[1] + (b[1] - a[1]) * k / nseg)
            p1 = (a[0] + (b[0] - a[0]) * (k + 1) / nseg, a[1] + (b[1] - a[1]) * (k + 1) / nseg)
            acc.wall(p1, p0, -0.2, 10.0, "forest_wall")
