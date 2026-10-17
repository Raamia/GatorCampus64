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
    # crowns reach up to ~10.5 m from the trunk: a tree closer than that to the s16 vertex limit
    # (327.67 m from the stage centre) would wrap around; out there it is behind the tree line anyway
    lim = 327.0 - 10.5
    counts["beyond_s16"] = 0
    holes = getattr(S, "ground_holes", None) or []     # landmark ground holes (no ground to stand on)
    counts["in_ground_hole"] = 0
    for t in d["trees"]:
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
