"""Geometry helpers for the campus stage generator (inside Blender).

All coordinates here are STAGE metres: Blender X = east, Y = north, Z = up, origin = the stage
centre (map x - cx, map y - cy). Fast64's scale is 100, so 1 m = 100 SM64 units after export.
"""
import math

import bmesh
import bpy

UV_SPAN_MAX = 12.0  # max texture repeats across one face (N64 s10.5 texture coords: <1024 texels)


# ------------------------------------------------------------------ 2D polygon helpers
def signed_area(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def ccw(pts):
    pts = [tuple(p[:2]) for p in pts]
    return pts if signed_area(pts) >= 0 else pts[::-1]


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def seg_dist(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L = dx * dx + dy * dy
    if L == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def dedupe(pts, eps=0.05, collinear=True, closed=True):
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) > eps:
            out.append(tuple(p))
    while closed and len(out) > 2 and math.dist(out[0], out[-1]) <= eps:
        out.pop()
    if not collinear:
        return out
    # drop collinear points
    i = 0
    while len(out) > 3 and i < len(out):
        a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-4 * max(1.0, math.dist(a, c)):
            out.pop(i)
        else:
            i += 1
    return out


def _segments_intersect(p1, p2, p3, p4):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def self_intersects(poly):
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if _segments_intersect(a, b, poly[j], poly[(j + 1) % n]):
                return True
    return False


def inset(poly, d):
    """Offset a CCW polygon inward by d (mitred). Returns the inset polygon (same vertex count,
    vertex i belongs to vertex i of poly) or None if the offset collapses / self-intersects."""
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return None
        nx, ny = -dy / L, dx / L  # left normal = inward for CCW
        lines.append(((a[0] + nx * d, a[1] + ny * d), (dx / L, dy / L)))
    out = []
    for i in range(n):
        (p0, d0), (p1, d1) = lines[i - 1], lines[i]
        den = d0[0] * d1[1] - d0[1] * d1[0]
        if abs(den) < 1e-9:  # parallel edges: use the shared offset point
            out.append(p1)
            continue
        t = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / den
        q = (p0[0] + d0[0] * t, p0[1] + d0[1] * t)
        if math.dist(q, poly[i]) > 6 * abs(d) + 0.5:  # extreme miter on a sharp spike
            return None
        out.append(q)
    # every inset edge must keep its direction and the polygon must stay simple + CCW
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia, ib = out[i], out[(i + 1) % n]
        if (b[0] - a[0]) * (ib[0] - ia[0]) + (b[1] - a[1]) * (ib[1] - ia[1]) <= 0:
            return None
    if signed_area(out) <= 0 or (d > 0 and signed_area(out) >= signed_area(poly)) or self_intersects(out):
        return None
    return out


def triangulate(rings):
    """Triangulate a polygon given as [outer, hole, hole, ...] (2D). Returns [(p, q, r), ...]
    counter-clockwise (normal up)."""
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    clean = [dedupe(r) for r in rings]
    clean = [r for r in clean if len(r) >= 3]
    if not clean:
        return []
    flat = [p for r in clean for p in r]
    tris = tessellate_polygon([[Vector((p[0], p[1], 0.0)) for p in r] for r in clean])
    out = []
    for i, j, k in tris:
        a, b, c = flat[i], flat[j], flat[k]
        ar = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(ar) < 1e-6:
            continue
        out.append((a, b, c) if ar > 0 else (a, c, b))
    return out


def clip_convex(poly, xmin, ymin, xmax, ymax):
    """Sutherland-Hodgman clip of a convex (or any) polygon to a box."""
    def clip(pts, inside, inter):
        res = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    res.append(inter(prev, cur))
                res.append(cur)
            elif inside(prev):
                res.append(inter(prev, cur))
        return res

    def ix(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def iy(y):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)
    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= xmin, ix(xmin)), (lambda p: p[0] <= xmax, ix(xmax)),
                          (lambda p: p[1] >= ymin, iy(ymin)), (lambda p: p[1] <= ymax, iy(ymax))):
        if not pts:
            break
        pts = clip(pts, inside, inter)
    return dedupe(pts, 1e-4) if len(pts) >= 3 else []


def grid_pieces(poly, cell, ox=0.0, oy=0.0):
    """Split a convex polygon into pieces along a grid of `cell` metres (lines at ox + k*cell)."""
    x0, y0, x1, y1 = bbox(poly)
    i0, i1 = math.floor((x0 - ox) / cell), math.floor((x1 - ox) / cell)
    j0, j1 = math.floor((y0 - oy) / cell), math.floor((y1 - oy) / cell)
    if i0 == i1 and j0 == j1:
        return [list(poly)]
    out = []
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            p = clip_convex(poly, ox + i * cell, oy + j * cell, ox + (i + 1) * cell, oy + (j + 1) * cell)
            if len(p) >= 3 and abs(signed_area(p)) > 1e-4:
                out.append(p)
    return out


def ribbon(pts, width, extend=None):
    """Quads of a mitred strip along a polyline. Returns [(quad[4 2D pts CCW], s0, s1)] with s =
    distance along the line at the quad's start/end (for along-the-path UVs)."""
    pts = dedupe([tuple(p) for p in pts], 0.05, collinear=False, closed=False)
    if len(pts) < 2:
        return []
    hw = width / 2.0
    ext = hw if extend is None else extend
    # extend the ends so joints at shared nodes are covered
    d0 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    L0 = math.hypot(*d0)
    dn = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
    Ln = math.hypot(*dn)
    e0, en = min(ext, 0.45 * L0), min(ext, 0.45 * Ln)
    pts = [(pts[0][0] - d0[0] / L0 * e0, pts[0][1] - d0[1] / L0 * e0)] + pts[1:-1] + \
          [(pts[-1][0] + dn[0] / Ln * en, pts[-1][1] + dn[1] / Ln * en)]
    n = len(pts)
    left, right = [], []
    for i in range(n):
        if i == 0:
            dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
            L = math.hypot(dx, dy)
            mx, my, k = -dy / L, dx / L, 1.0
        elif i == n - 1:
            dx, dy = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
            L = math.hypot(dx, dy)
            mx, my, k = -dy / L, dx / L, 1.0
        else:
            ax, ay = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
            bx, by = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
            La, Lb = math.hypot(ax, ay), math.hypot(bx, by)
            n0 = (-ay / La, ax / La)
            n1 = (-by / Lb, bx / Lb)
            mx, my = n0[0] + n1[0], n0[1] + n1[1]
            Lm = math.hypot(mx, my)
            if Lm < 1e-6:
                mx, my, k = n0[0], n0[1], 1.0
            else:
                mx, my = mx / Lm, my / Lm
                k = 1.0 / max(mx * n0[0] + my * n0[1], 0.5)
        left.append((pts[i][0] + mx * hw * k, pts[i][1] + my * hw * k))
        right.append((pts[i][0] - mx * hw * k, pts[i][1] - my * hw * k))
    out = []
    s = 0.0
    for i in range(n - 1):
        seg = math.dist(pts[i], pts[i + 1])
        quad = [right[i], right[i + 1], left[i + 1], left[i]]
        if signed_area(quad) > 1e-4:
            out.append((quad, s, s + seg))
        s += seg
    return out


# ------------------------------------------------------------------ mesh accumulation
def face_normal(pts3):
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(pts3, pts3[1:] + pts3[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def planar_uvs(pts3, tile):
    """Top-down for floors, along-the-wall for walls (texture upright), in repeats."""
    nx, ny, nz = face_normal(pts3)
    t = max(tile, 1e-6)
    if abs(nz) >= max(abs(nx), abs(ny)) * 1.0001:
        return [(p[0] / t, p[1] / t) for p in pts3]
    L = math.hypot(nx, ny) or 1.0
    hx, hy = -ny / L, nx / L
    return [((p[0] * hx + p[1] * hy) / t, p[2] / t) for p in pts3]


def shift_uvs(uvs):
    du = math.floor(min(u for u, _ in uvs) + 1e-6)
    dv = math.floor(min(v for _, v in uvs) + 1e-6)
    return [(u - du, v - dv) for u, v in uvs]


def split_for_uv(pts3, uvs, cell):
    """Cut a planar polygon whose UVs (linear on its plane) span too many repeats into pieces of at
    most `cell` repeats: triangulate in UV space, clip each triangle to a UV grid, map back to 3D."""
    out = []
    uv2 = [tuple(u) for u in uvs]
    flip = signed_area(uv2) < 0  # face is clockwise in UV space: keep its 3D winding
    tris = triangulate([uv2]) if len(uv2) > 3 else [tuple(uv2) if not flip else tuple(uv2[::-1])]
    lookup = {tuple(u): p for u, p in zip(uv2, pts3)}
    for t in tris:
        A, B, C = (lookup.get(tuple(t[i])) for i in range(3))
        if A is None or B is None or C is None:
            continue
        (ax, ay), (bx, by), (cx, cy) = t
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        for piece in grid_pieces(list(t), cell):
            p3 = []
            for (x, y) in piece:
                w1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
                w2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
                w3 = 1.0 - w1 - w2
                p3.append(tuple(A[i] * w1 + B[i] * w2 + C[i] * w3 for i in range(3)))
            if len(p3) >= 3:
                out.append(p3[::-1] if flip else p3)
    return out


class MeshAcc:
    """Collects polygons (each: 3D points, material name, UVs in texture repeats) and builds one
    Blender mesh object with F3D materials. Faces keep their own vertices (unshared), so UVs are
    per face; Fast64 merges equal vertices again on export."""

    def __init__(self, name, tiles):
        self.name = name
        self.tiles = tiles      # material name -> tile_m (for planar UVs)
        self.polys = []
        self.max_uv_span = 0.0

    def poly(self, pts3, mat, uvs=None):
        if len(pts3) < 3:
            return
        tile = self.tiles.get(mat, 2.0)
        if tile <= 0:
            uvs = [(0.0, 0.0)] * len(pts3)
        elif uvs is None:
            uvs = planar_uvs(pts3, tile)
            us, vs = [u for u, _ in uvs], [v for _, v in uvs]
            if max(max(us) - min(us), max(vs) - min(vs)) > UV_SPAN_MAX - 1:
                for piece in split_for_uv(pts3, uvs, UV_SPAN_MAX / 2):
                    self.poly(piece, mat)
                return
        uvs = shift_uvs(uvs)
        span = max(max(u, v) for u, v in uvs)
        if span > self.max_uv_span:
            self.max_uv_span = span
            self.max_uv_where = (mat, tuple(round(c, 1) for c in pts3[0]))
        self.polys.append(([tuple(map(float, p)) for p in pts3], mat, uvs))

    def wall(self, a, b, z0, z1, mat, uvs=None):
        """Vertical quad a->b (2D), normal on the right of a->b (outward for a CCW footprint).
        Long walls with projected UVs are split so no face spans more than ~10 texture repeats."""
        tile = self.tiles.get(mat, 2.0)
        if uvs is None and tile > 0:
            n = max(1, math.ceil(math.dist(a, b) / (tile * 10.0)))
            m = max(1, math.ceil(abs(z1 - z0) / (tile * 10.0)))
            if n > 1 or m > 1:
                for i in range(n):
                    p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                    q = (a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n)
                    for k in range(m):
                        za, zb = z0 + (z1 - z0) * k / m, z0 + (z1 - z0) * (k + 1) / m
                        self.poly([(p[0], p[1], za), (q[0], q[1], za), (q[0], q[1], zb), (p[0], p[1], zb)], mat)
                return
        self.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat, uvs)

    def flat(self, pts2, z, mat, down=False):
        pts3 = [(p[0], p[1], z) for p in pts2]
        if down:
            pts3.reverse()
        self.poly(pts3, mat)

    def flat_tris(self, tris, z, mat, cell=None, ox=0.0, oy=0.0):
        """Up-facing triangles at height z, optionally split along a grid (for UV range / size)."""
        for t in tris:
            pieces = grid_pieces(t, cell, ox, oy) if cell else [t]
            for p in pieces:
                self.flat(p, z, mat)

    def tri_count(self):
        return sum(len(p[0]) - 2 for p in self.polys)

    def build(self, materials, parent=None, collision=True, render=True, smooth=False):
        if not self.polys:
            return None
        mats = []
        for _, m, _ in self.polys:
            if m not in mats:
                mats.append(m)
        me = bpy.data.meshes.new(self.name)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        vcache = {}
        for pts3, m, uvs in self.polys:
            vs = []
            for p in pts3:
                v = bm.verts.new(p)
                vs.append(v)
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            f.material_index = mats.index(m)
            f.smooth = smooth
            for loop, uv in zip(f.loops, uvs):
                loop[uvl].uv = uv
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3],
                              quad_method="BEAUTY", ngon_method="EAR_CLIP")
        bm.to_mesh(me)
        bm.free()
        del vcache
        obj = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(obj)
        for m in mats:
            me.materials.append(materials[m])
        from fast64.fast64_internal.f3d.f3d_material import addColorAttributesToModel
        addColorAttributesToModel(obj)
        obj.ignore_collision = not collision
        obj.ignore_render = not render
        if parent is not None:
            obj.parent = parent
        return obj


def tris_of(obj):
    me = obj.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)
