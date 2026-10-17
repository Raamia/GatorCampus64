"""Ground of a campus stage: base grass, mapped lawns / plazas / parking, roads with centre lines,
walkways, crossings, steps, pond basins with water, low walls and fences, and the flat collision
ground (20.48 m tiles offset half a collision cell, with holes for the ponds).

Visual ground layers sit just BELOW the collision floor (z = 0) so Mario's shadow and feet are
never hidden by a decal layer; each layer is 1-2 cm above the one under it:
"""
import math

import stage_geom as G

TILE = 20.48          # collision / UV tile (2 x 2 SM64 collision cells)
TILE_OFF = 5.12       # half a cell: tile edges never sit on cell edges
Z = {"base": -0.12, "lawn": -0.10, "forest": -0.10, "area": -0.08, "road": -0.06, "paint": -0.05,
     "crossing": -0.04, "path": -0.03}
POND_FLOOR = -2.2
POND_SURFACE = -0.3


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


def ground_sheet(acc, bounds, z, mat, ponds, down_holes=True):
    """Tiles over bounds (clipped to it) at height z, with holes where the ponds are.
    Returns the number of polygons written."""
    xmin, ymin, xmax, ymax = bounds
    i0, i1, j0, j1 = tiles_covering(xmin, ymin, xmax, ymax)
    holed = {}
    for pi, p in enumerate(ponds):
        px0, py0, px1, py1 = G.bbox(p)
        a0, a1, b0, b1 = tiles_covering(px0, py0, px1, py1)
        for i in range(a0, a1):
            for j in range(b0, b1):
                holed.setdefault(pi, set()).add((i, j))
    skip = set()
    for s in holed.values():
        skip |= s
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
    for pi, cells in holed.items():
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        x0, y0, _, _ = tile_rect(min(xs), min(ys))
        _, _, x1, y1 = tile_rect(max(xs), max(ys))
        rect = G.clip_convex([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], xmin, ymin, xmax, ymax)
        if len(rect) < 3:
            continue
        hole = [p for p in ponds[pi]]
        tris = G.triangulate([rect, hole[::-1]])
        acc.flat_tris(tris, z, mat, cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        n += len(tris)
    return n


def build(S):
    d = S.data
    T = S.T
    ext = S.ext_local          # visual extent, stage coords
    col_bounds = S.col_bounds  # collision ground extent, stage coords

    vis = S.acc("Ground visual", collision=False)
    roads_acc = S.acc("Roads and paths visual", collision=False)
    col = S.acc("Ground collision", render=False)

    ponds = [[T(p) for p in w["ring"]] for w in d["water"]]
    ponds = [G.ccw(p) for p in ponds if len(p) >= 3]

    # ---- base grass + collision ground
    ground_sheet(vis, ext, Z["base"], "ground_grass", ponds)
    ground_sheet(col, col_bounds, 0.0, "COL default", ponds)

    def in_pond(pt):
        return any(G.point_in_poly(pt, p) for p in ponds)

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
        # ponds inside a park polygon become holes, or the lawn would cover the water
        for p in ponds:
            if all(G.point_in_poly(q, ring) for q in p):
                holes.append(p[::-1])
        tris = G.triangulate([ring] + holes)
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
            if q:
                roads_acc.flat(q, Z["road"], "asphalt")
        if r.get("center_line"):
            _center_dashes(roads_acc, [T(p) for p in r["pts"]], near_junction)

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
                if not q:
                    continue
                uvs = [(0.0, s0 / tile), (0.0, s1 / tile), (w / tile, s1 / tile), (w / tile, s0 / tile)]
                roads_acc.poly([(x, y, z) for x, y in q], mat, uvs if whole else None)
        else:
            for quad, _s0, _s1 in G.ribbon(pts, w):
                q, _ = clip_ext(quad)
                if q:
                    roads_acc.flat(q, Z["path"], p["mat"])

    # ---- ponds: basin (visual + collision), translucent water surface, water box
    basin_v = S.acc("Pond basins visual", collision=False)
    basin_c = S.acc("Pond basins collision", render=False)
    water_v = S.acc("Pond water", collision=False)
    for w, ring in zip(d["water"], ponds):
        tris = G.triangulate([ring])
        basin_v.flat_tris(tris, POND_FLOOR, "pond_bed", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        basin_c.flat_tris(tris, POND_FLOOR, "COL default", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        water_v.flat_tris(tris, POND_SURFACE, "pond_water", cell=TILE, ox=TILE_OFF, oy=TILE_OFF)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            basin_v.wall(b, a, POND_FLOOR, Z["base"], "pond_bed")   # faces the water
            basin_c.wall(b, a, POND_FLOOR, 0.0, "COL default")
        x0, y0, x1, y1 = G.bbox(ring)
        S.water_boxes.append((x0, y0, x1, y1, POND_SURFACE, POND_FLOOR - 0.4, w.get("name") or w["id"]))

    # ---- fountain(s): low limestone basin with water on top (solid; you can stand on the rim)
    for f in d.get("fountains", []):
        if f["id"] in skip_areas:
            continue
        ring = G.ccw([T(p) for p in f["ring"]])
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
