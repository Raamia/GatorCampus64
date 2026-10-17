"""Ground of a campus stage: base grass, mapped lawns / plazas / parking, roads with centre lines,
walkways, crossings, steps, pond basins with water, low walls and fences, and the flat collision
ground (20.48 m tiles offset half a collision cell, with holes for the ponds).

Visual ground layers sit just BELOW the collision floor (z = 0) so Mario's shadow and feet are
never hidden by a decal layer; each layer is 1-2 cm above the one under it:

Ground holes (landmark contract key "ground_holes_m", e.g. the Swamp stadium's sunken bowl): cut out
of the collision ground (HOLE_OVERLAP_M smaller: see there) and the base grass like the ponds (one
cut-out rectangle per group of holes / ponds whose tile rectangles overlap, so no tile is covered
twice); mapped areas, roads, centre lines, walkways, barriers and fountains drop the pieces whose
centre lies in a hole. Inside a hole the landmark module provides every floor. S.ground_holes keeps
them (stage coordinates). A landmark ground hole that an OSM area already has as one of its own holes
(the Lake Alice shore = the lake hole of the surrounding woods) is not added to that area a second time.

Landmark lakes (Lake Alice, landmarks/lake_alice_water.py): an OSM water polygon whose id a landmark
entry lists in "replaces_areas" (or "osm_ids") gets no generic pond (basin, water, water box); the
landmark builds the basin itself and lists its SM64 water boxes in "water_boxes_m":
    [{"name": str, "rect_m": [xmin, ymin, xmax, ymax] (map metres), "surface_z": m, "bottom_z": m}, ...]
which go into S.water_boxes after the ponds' boxes (build_stage.py clips them to the play zone).
Stages without such entries build exactly as before.
"""
import math

import stage_geom as G

TILE = 20.48          # collision / UV tile (2 x 2 SM64 collision cells)
TILE_OFF = 5.12       # half a cell: tile edges never sit on cell edges
Z = {"base": -0.12, "lawn": -0.10, "forest": -0.10, "area": -0.08, "road": -0.06, "paint": -0.05,
     "crossing": -0.04, "path": -0.03}
POND_FLOOR = -2.2
POND_SURFACE = -0.3
# landmark ground holes are cut this much SMALLER in the collision ground, so the ground and the
# landmark's own floors at the rim (coplanar at z = 0) overlap instead of abutting: after the export
# rounds every vertex to whole units, two abutting edges with different intermediate vertices leave
# hairline slivers with no floor at some integer points, and find_floor (which truncates Mario's
# position to s16) returns NULL there = an invisible wall that can stop Mario dead on the seam
HOLE_OVERLAP_M = 0.06


def densify(pts, max_len):
    out = [tuple(pts[0])]
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        n = max(1, math.ceil(L / max_len))
        for k in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    return out


def tiles_covering(xmin, ymin, xmax, ymax):
    i0 = math.floor((xmin - TILE_OFF) / TILE)
    i1 = math.ceil((xmax - TILE_OFF) / TILE)
    j0 = math.floor((ymin - TILE_OFF) / TILE)
    j1 = math.ceil((ymax - TILE_OFF) / TILE)
    return i0, i1, j0, j1


def tile_rect(i, j):
    x0, y0 = TILE_OFF + i * TILE, TILE_OFF + j * TILE
    return x0, y0, x0 + TILE, y0 + TILE


def hole_groups(ponds):
    """Tile rectangles to cut out: [(hole indices, (i0, i1, j0, j1))], one per group of holes whose
    tile rectangles overlap (merged into their bounding rectangle). Non-overlapping holes keep their
    own rectangle, in index order."""
    groups = []
    for pi, p in enumerate(ponds):
        px0, py0, px1, py1 = G.bbox(p)
        groups.append(([pi], list(tiles_covering(px0, py0, px1, py1))))
    merged = True
    while merged:
        merged = False
        for x in range(len(groups)):
            for y in range(x + 1, len(groups)):
                A, B = groups[x][1], groups[y][1]
                if A[0] < B[1] and B[0] < A[1] and A[2] < B[3] and B[2] < A[3]:
                    groups[x] = (groups[x][0] + groups[y][0],
                                 [min(A[0], B[0]), max(A[1], B[1]), min(A[2], B[2]), max(A[3], B[3])])
                    del groups[y]
                    merged = True
                    break
            if merged:
                break
    return [(idx, tuple(r)) for idx, r in groups]


def ground_sheet(acc, bounds, z, mat, ponds, down_holes=True):
    """Tiles over bounds (clipped to it) at height z, with holes where the ponds (and landmark ground
    holes) are. Returns the number of polygons written."""
    xmin, ymin, xmax, ymax = bounds
    i0, i1, j0, j1 = tiles_covering(xmin, ymin, xmax, ymax)
    groups = hole_groups(ponds)
    skip = set()
    for _, (a0, a1, b0, b1) in groups:
        skip.update((i, j) for i in range(a0, a1) for j in range(b0, b1))
    n = 0
    for i in range(i0, i1):
        for j in range(j0, j1):
            if (i, j) in skip:
                continue
            x0, y0, x1, y1 = tile_rect(i, j)
            r = G.clip_convex([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], xmin, ymin, xmax, ymax)
            if len(r) >= 3:
                acc.flat(r, z, mat)
                n += 1
    for idx, (a0, a1, b0, b1) in groups:
        x0, y0, _, _ = tile_rect(a0, b0)
        _, _, x1, y1 = tile_rect(a1 - 1, b1 - 1)
        rect = G.clip_convex([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], xmin, ymin, xmax, ymax)
        if len(rect) < 3:
            continue
        tris = G.triangulate([rect] + [list(ponds[pi])[::-1] for pi in idx])
        acc.flat_tris(tris, z, mat, cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        n += len(tris)
    return n


def landmark_ground_holes(S):
    """Landmark "ground_holes_m" rings (map metres) -> stage coordinates, counter-clockwise."""
    out = []
    for e in S.landmark_entries:
        for h in e.get("ground_holes_m", []) or []:
            ring = G.ccw([S.T(p) for p in h])
            if len(ring) >= 3 and abs(G.signed_area(ring)) > 1.0:
                out.append(ring)
    return out


def landmark_water_boxes(S):
    """Landmark "water_boxes_m" (map metres) -> S.water_boxes tuples (stage coordinates)."""
    out = []
    for e in S.landmark_entries:
        for b in e.get("water_boxes_m", []) or []:
            x0, y0, x1, y1 = b["rect_m"]
            (ax, ay), (bx, by) = S.T((x0, y0)), S.T((x1, y1))
            surf = float(b["surface_z"])
            out.append((min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), surf,
                        float(b.get("bottom_z", surf - 6.0)), b.get("name") or e["slug"]))
    return out


def _same_hole(p, q, tol=0.5):
    """Two rings with the same bounding box (within tol m) and the same area (within 2 %)."""
    bp, bq = G.bbox(p), G.bbox(q)
    if any(abs(a - b) > tol for a, b in zip(bp, bq)):
        return False
    ap, aq = abs(G.signed_area(p)), abs(G.signed_area(q))
    return abs(ap - aq) <= 0.02 * max(ap, aq, 1e-6)


def _centre(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def build(S):
    d = S.data
    T = S.T
    ext = S.ext_local          # visual extent, stage coords
    col_bounds = S.col_bounds  # collision ground extent, stage coords

    vis = S.acc("Ground visual", collision=False)
    roads_acc = S.acc("Roads and paths visual", collision=False)
    col = S.acc("Ground collision", render=False)

    # OSM water a landmark draws itself (Lake Alice): no generic pond
    replaced_water = S.replaced_areas | S.replaced_ids
    waters = [w for w in d["water"] if w["id"] not in replaced_water]
    if len(waters) != len(d["water"]):
        S.stats["water_replaced_by_landmarks"] = sorted(w["id"] for w in d["water"] if w["id"] in replaced_water)
    ponds = [[T(p) for p in w["ring"]] for w in waters]
    ponds = [G.ccw(p) for p in ponds if len(p) >= 3]
    holes = landmark_ground_holes(S)          # landmark ground holes (the stadium bowl)
    S.ground_holes = holes
    hole_bbs = [G.bbox(h) for h in holes]

    # ---- base grass + collision ground
    ground_sheet(vis, ext, Z["base"], "ground_grass", ponds + holes)
    col_holes = [G.inset(h, HOLE_OVERLAP_M) or h for h in holes]
    ground_sheet(col, col_bounds, 0.0, "COL default", ponds + col_holes)
    if holes:
        S.stats["ground_holes"] = [{"vertices": len(h), "area_m2": round(G.signed_area(h), 1),
                                    "bbox_stage_m": [round(v, 1) for v in G.bbox(h)]} for h in holes]

    def in_pond(pt):
        return any(G.point_in_poly(pt, p) for p in ponds)

    def in_hole(pt):
        return any(b[0] <= pt[0] <= b[2] and b[1] <= pt[1] <= b[3] and G.point_in_poly(pt, h)
                   for h, b in zip(holes, hole_bbs))

    def piece_in_hole(pts):
        return bool(holes) and in_hole(_centre(pts))

    def clip_ext(quad):
        """Road / path quads end at the visual extent (mitres and end caps would otherwise reach
        past it, beyond the s16 vertex range). -> (polygon or None, whole quad kept?)"""
        x0, y0, x1, y1 = ext
        if all(x0 <= q[0] <= x1 and y0 <= q[1] <= y1 for q in quad):
            return quad, True
        c = G.clip_convex(quad, x0, y0, x1, y1)
        return (c if len(c) >= 3 and abs(G.signed_area(c)) > 1e-3 else None), False

    # ---- mapped areas
    skip_areas = S.replaced_areas | S.replaced_ids
    skip_ways = S.replaced_ways | S.replaced_ids
    for a in d["areas"]:
        if a["id"] in skip_areas:
            continue
        ring = [T(p) for p in a["ring"]]
        holes = [[T(p) for p in h] for h in a.get("holes", [])]
        if in_pond(G.bbox(ring)[:2]) and in_pond(G.bbox(ring)[2:]):
            continue
        z = Z["lawn"] if a["cls"] in ("lawn", "forest") else Z["area"]
        # ponds (and landmark ground holes) inside a park polygon become holes, or the lawn would
        # cover the water / the sunken bowl (a landmark hole the area already has is not added twice)
        own_holes = list(holes)
        for p in ponds + S.ground_holes:
            if all(G.point_in_poly(q, ring) for q in p):
                if own_holes and any(p is h for h in S.ground_holes) and any(_same_hole(p, h) for h in own_holes):
                    continue
                holes.append(p[::-1])
        tris = G.triangulate([ring] + holes)
        if S.ground_holes:   # partial overlaps: drop the triangles whose centre is in a ground hole
            tris = [t for t in tris if not piece_in_hole(t)]
        vis.flat_tris(tris, z, a["mat"], cell=TILE, ox=TILE_OFF, oy=TILE_OFF)

    # ---- roads
    junctions = {}
    for r in d["roads"]:
        for p in (r["pts"][0], r["pts"][-1]):
            k = (round(p[0] / 2), round(p[1] / 2))
            junctions[k] = junctions.get(k, 0) + 1
    node_count = {}
    for r in d["roads"]:
        for p in r["pts"]:
            k = (round(p[0] / 2), round(p[1] / 2))
            node_count[k] = node_count.get(k, 0) + 1
    hot = [T((k[0] * 2, k[1] * 2)) for k, c in node_count.items() if c >= 2]
    hot_grid = {}
    for p in hot:
        hot_grid.setdefault((int(p[0] // 20), int(p[1] // 20)), []).append(p)

    def near_junction(p, rad=9.0):
        gx, gy = int(p[0] // 20), int(p[1] // 20)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in hot_grid.get((gx + dx, gy + dy), ()):
                    if math.dist(p, q) < rad:
                        return True
        return False

    for r in sorted(d["roads"], key=lambda r: r["width"]):
        if r["id"] in skip_ways:
            continue
        pts = densify([T(p) for p in r["pts"]], 18.0)
        if all(in_pond(p) for p in pts):
            continue
        for quad, _s0, _s1 in G.ribbon(pts, r["width"]):
            q, _ = clip_ext(quad)
            if q and not piece_in_hole(q):
                roads_acc.flat(q, Z["road"], "asphalt")
        if r.get("center_line"):
            _center_dashes(roads_acc, [T(p) for p in r["pts"]],
                           (lambda m: near_junction(m) or in_hole(m)) if holes else near_junction)

    # ---- walkways, crossings, steps
    for p in d["paths"]:
        if p["id"] in skip_ways:
            continue
        pts = densify([T(q) for q in p["pts"]], 9.0 if p["kind"] == "steps" else 18.0)
        if sum(1 for q in pts if in_pond(q)) > len(pts) / 2:
            continue
        w = p["width"]
        if p["kind"] in ("crossing", "steps"):
            mat = p["mat"]
            tile = S.tiles[mat]
            z = Z["crossing"] if p["kind"] == "crossing" else Z["path"]
            for quad, s0, s1 in G.ribbon(pts, w, extend=0.3 if p["kind"] == "crossing" else None):
                q, whole = clip_ext(quad)
                if not q or piece_in_hole(q):
                    continue
                uvs = [(0.0, s0 / tile), (0.0, s1 / tile), (w / tile, s1 / tile), (w / tile, s0 / tile)]
                roads_acc.poly([(x, y, z) for x, y in q], mat, uvs if whole else None)
        else:
            for quad, _s0, _s1 in G.ribbon(pts, w):
                q, _ = clip_ext(quad)
                if q and not piece_in_hole(q):
                    roads_acc.flat(q, Z["path"], p["mat"])

    # ---- ponds: basin (visual + collision), translucent water surface, water box
    basin_v = S.acc("Pond basins visual", collision=False)
    basin_c = S.acc("Pond basins collision", render=False)
    water_v = S.acc("Pond water", collision=False)
    for w, ring in zip(waters, ponds):
        tris = G.triangulate([ring])
        basin_v.flat_tris(tris, POND_FLOOR, "pond_bed", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        basin_c.flat_tris(tris, POND_FLOOR, "COL default", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        water_v.flat_tris(tris, POND_SURFACE, "pond_water", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            basin_v.wall(b, a, POND_FLOOR, Z["base"], "pond_bed")   # faces the water
            basin_c.wall(b, a, POND_FLOOR, 0.0, "COL default")
        x0, y0, x1, y1 = G.bbox(ring)
        S.water_boxes.append((x0, y0, x1, y1, POND_SURFACE, POND_FLOOR - 0.4, w.get("name") or w["id"]))
    # ---- landmark lakes: their own water boxes (contract key "water_boxes_m")
    S.water_boxes.extend(landmark_water_boxes(S))

    # ---- fountain(s): low limestone basin with water on top (solid; you can stand on the rim)
    for f in d.get("fountains", []):
        if f["id"] in skip_areas:
            continue
        ring = G.ccw([T(p) for p in f["ring"]])
        if piece_in_hole(ring):
            continue
        fv = S.acc("Props visual", collision=False)
        fc = S.acc("Props collision", render=False)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            fv.wall(a, b, -0.15, 0.55, "limestone")
            fc.wall(a, b, 0.0, 0.55, "COL default")
        inner = G.inset(ring, 0.25) or ring
        for (a, b), (ia, ib) in zip(zip(ring, ring[1:] + ring[:1]), zip(inner, inner[1:] + inner[:1])):
            fv.poly([(a[0], a[1], 0.55), (b[0], b[1], 0.55), (ib[0], ib[1], 0.55), (ia[0], ia[1], 0.55)], "limestone")
        fv.flat(inner, 0.45, "water")
        fc.flat(ring, 0.55, "COL default")

    # ---- barriers: brick garden walls, fences, hedges (thin boxes, solid)
    bv = S.acc("Props visual", collision=False)
    bc = S.acc("Props collision", render=False)
    for b in d["barriers"]:
        if b["id"] in skip_ways:
            continue
        pts = [T(p) for p in b["pts"]]
        kind = b["kind"]
        width = {"hedge": 0.8, "fence": 0.12}.get(kind, 0.35)
        mat = {"hedge": "leaves_oak", "fence": "metal_gray"}.get(kind, "brick_red")
        top = {"hedge": "leaves_oak", "fence": "metal_gray"}.get(kind, "limestone")
        h = b["height"]
        for quad, _s0, _s1 in G.ribbon(pts, width, extend=0.0):
            if piece_in_hole(quad):
                continue
            for a, c in zip(quad, quad[1:] + quad[:1]):
                bv.wall(a, c, -0.15, h, mat)
                bc.wall(a, c, 0.0, h, "COL default")
            bv.flat(quad, h, top)
            bc.flat(quad, h, "COL default")


def _center_dashes(acc, pts, near_junction, dash=3.0, gap=6.0, hw=0.12):
    s_total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    if s_total < 20:
        return
    s = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = -uy, ux
        t = (-(s % (dash + gap))) % (dash + gap)  # first dash start inside this segment
        while t + dash <= L:
            p0 = (a[0] + ux * t, a[1] + uy * t)
            p1 = (a[0] + ux * (t + dash), a[1] + uy * (t + dash))
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            if 6.0 < s + t < s_total - 6.0 and not near_junction(mid):
                quad = [(p0[0] - nx * hw, p0[1] - ny * hw), (p1[0] - nx * hw, p1[1] - ny * hw),
                        (p1[0] + nx * hw, p1[1] + ny * hw), (p0[0] + nx * hw, p0[1] + ny * hw)]
                acc.flat(quad, Z["paint"], "road_paint")
            t += dash + gap
        s += L
