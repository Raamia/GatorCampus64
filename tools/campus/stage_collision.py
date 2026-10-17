"""Seam repair of an exported DynOS collision (area_N/collision.inc.c), on the INTEGER data the game loads.

Why: the export rounds every vertex to whole units. Where two floor meshes meet along a line with
different intermediate vertices (a T-junction: one long edge on one side, several short ones on the
other, typical where a landmark module's floors meet each other or the generator's), the rounded edges
no longer coincide and leave hairline slivers. find_floor() truncates Mario's position to s16, so at
the integer points inside such a sliver it finds no floor and the step code treats that as a wall:
Mario can stop dead on a seam (and stays stuck while the stick and speed do not change).

repair(path): 1) splits every floor triangle (normal.y > 0.01) whose edge passes within TJ_UNITS of
another floor vertex (XZ, and within TJ_Y_UNITS in height) at that vertex, so both sides share the
same integer vertices and the seam is watertight; 2) welds vertices closer than WELD_UNITS (keeps the
first), dropping triangles that collapse; 3) splits again for T-junctions the weld created. Walls and
ceilings are only welded. Triangle order, surface groups (COL_TRI_INIT type), special params and water
boxes are kept. Pure Python (no bpy).
Split BEFORE weld (integration pass, Oct 2026): welding first collapses 1-unit sliver triangles whose
far edge is still a straight edge of the neighbour across the seam (the far vertex is then > TJ_UNITS
away and never split), which opened new cracks, e.g. a 9 m line along a hub roof ridge. Splitting
first makes the neighbour share the sliver's vertices, so the weld closes the seam instead. Measured
on the hub (boundary-edge crack scan, integer points with no floor at the floors' height between two
walkable floors): 21,426 crack points unrepaired, 5,700 weld-first, 2,575 split-first (what is left
is modelling gaps, not rounding); The Swamp: 1,940 either way.
"""
import math
import re

WELD_UNITS = 1.5
TJ_UNITS = 1.0
TJ_Y_UNITS = 3.0
MIN_PIECE_UNITS = 1.0       # never split closer than this to an edge end
CELL = 256


def _parse(src):
    lines = src.split("\n")
    verts = []
    groups = []        # [type, [(a, b, c, special or None)]]
    head, tail = [], []
    state = "head"
    for ln in lines:
        s = ln.strip()
        if state == "head":
            head.append(ln)
            if s.startswith("COL_VERTEX_INIT("):
                state = "verts"
            continue
        if state == "verts":
            m = re.match(r"COL_VERTEX\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\),?", s)
            if m:
                verts.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
                continue
            state = "tris"
        if state == "tris":
            m = re.match(r"COL_TRI_INIT\(\s*(\w+)\s*,\s*\d+\s*\),?", s)
            if m:
                groups.append([m.group(1), []])
                continue
            m = re.match(r"COL_TRI(_SPECIAL)?\(\s*(\d+),\s*(\d+),\s*(\d+)\s*(?:,\s*([^)]+))?\),?", s)
            if m:
                groups[-1][1].append((int(m.group(2)), int(m.group(3)), int(m.group(4)),
                                      m.group(5).strip() if m.group(1) else None))
                continue
            if s == "" and not groups:
                continue
            state = "tail"
        tail.append(ln)
    return head, verts, groups, tail


def _write(head, verts, groups, tail):
    out = []
    for ln in head:
        if ln.strip().startswith("COL_VERTEX_INIT("):
            ind = ln[:len(ln) - len(ln.lstrip())]
            out.append(f"{ind}COL_VERTEX_INIT({len(verts)}),")
        else:
            out.append(ln)
    for x, y, z in verts:
        out.append(f"\tCOL_VERTEX({x}, {y}, {z}),")
    for typ, tris in groups:
        if not tris:
            continue
        out.append(f"\tCOL_TRI_INIT({typ}, {len(tris)}),")
        for a, b, c, sp in tris:
            out.append(f"\tCOL_TRI_SPECIAL({a}, {b}, {c}, {sp})," if sp is not None else f"\tCOL_TRI({a}, {b}, {c}),")
    return "\n".join(out + tail)


def _normal_y(v, t):
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = v[t[0]], v[t[1]], v[t[2]]
    nx = (y2 - y1) * (z3 - z2) - (z2 - z1) * (y3 - y2)
    ny = (z2 - z1) * (x3 - x2) - (x2 - x1) * (z3 - z2)
    nz = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
    m = math.sqrt(nx * nx + ny * ny + nz * nz)
    return 0.0 if m == 0 else ny / m


def _weld(verts, groups):
    grid = {}
    remap = list(range(len(verts)))
    r2 = WELD_UNITS * WELD_UNITS
    for i, (x, y, z) in enumerate(verts):
        k = (x // 4, y // 4, z // 4)
        hit = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        a = verts[j]
                        if (a[0] - x) ** 2 + (a[1] - y) ** 2 + (a[2] - z) ** 2 <= r2:
                            hit = j
                            break
                    if hit is not None:
                        break
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is not None:
            remap[i] = hit
        else:
            grid.setdefault(k, []).append(i)
    merged = sum(1 for i, j in enumerate(remap) if i != j)
    dropped = 0
    for g in groups:
        keep = []
        for a, b, c, sp in g[1]:
            a, b, c = remap[a], remap[b], remap[c]
            if a == b or b == c or a == c:
                dropped += 1
                continue
            keep.append((a, b, c, sp))
        g[1] = keep
    # compact the vertex list (welded duplicates are unused now)
    used = sorted({i for g in groups for t in g[1] for i in t[:3]})
    new_index = {old: k for k, old in enumerate(used)}
    nverts = [verts[i] for i in used]
    for g in groups:
        g[1] = [(new_index[a], new_index[b], new_index[c], sp) for a, b, c, sp in g[1]]
    return nverts, merged, dropped


def _tjunctions(verts, groups):
    floor_vs = set()
    for _, tris in groups:
        for t in tris:
            if _normal_y(verts, t) > 0.01:
                floor_vs.update(t[:3])
    grid = {}
    for i in floor_vs:
        x, _, z = verts[i]
        grid.setdefault((x // CELL, z // CELL), []).append(i)

    def on_edge(ia, ib, exclude):
        ax, ay, az = verts[ia]
        bx, by, bz = verts[ib]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        if L2 < 4:
            return []
        L = math.sqrt(L2)
        found = []
        for cx in range((min(ax, bx) - 2) // CELL, (max(ax, bx) + 2) // CELL + 1):
            for cz in range((min(az, bz) - 2) // CELL, (max(az, bz) + 2) // CELL + 1):
                for v in grid.get((cx, cz), ()):
                    if v in exclude:
                        continue
                    vx, vy, vz = verts[v]
                    t = ((vx - ax) * dx + (vz - az) * dz) / L2
                    if t * L < MIN_PIECE_UNITS or (1 - t) * L < MIN_PIECE_UNITS:
                        continue
                    if abs((vx - ax) * dz - (vz - az) * dx) / L > TJ_UNITS:
                        continue
                    if abs(vy - (ay + (by - ay) * t)) > TJ_Y_UNITS:
                        continue
                    found.append((t, v))
        found.sort()
        return [v for _, v in found]

    splits = 0
    for g in groups:
        out = []
        for t in g[1]:
            if _normal_y(verts, t) <= 0.01:
                out.append(t)
                continue
            work = [(t, 0)]
            while work:
                tri, depth = work.pop()
                a, b, c, sp = tri
                done = False
                if depth < 6:
                    for (p, q, r) in ((a, b, c), (b, c, a), (c, a, b)):
                        mids = on_edge(p, q, {a, b, c})
                        if mids:
                            chain = [p] + mids + [q]
                            for u, w in zip(chain, chain[1:]):
                                work.append(((u, w, r, sp), depth + 1))
                            splits += len(mids)
                            done = True
                            break
                if not done:
                    out.append(tri)
        g[1] = out
    return splits


def repair(path):
    """Weld + T-junction split in place. Returns a report dict."""
    src = open(path).read()
    head, verts, groups, tail = _parse(src)
    n_tris0 = sum(len(g[1]) for g in groups)
    n_v0 = len(verts)
    splits = _tjunctions(verts, groups)
    verts, merged, dropped = _weld(verts, groups)
    splits += _tjunctions(verts, groups)
    open(path, "w").write(_write(head, verts, groups, tail))
    n_tris1 = sum(len(g[1]) for g in groups)
    return {"vertices": [n_v0, len(verts)], "welded_vertices": merged, "collapsed_tris": dropped,
            "tjunction_splits": splits, "triangles": [n_tris0, n_tris1]}


if __name__ == "__main__":
    import sys
    print(repair(sys.argv[1]))
