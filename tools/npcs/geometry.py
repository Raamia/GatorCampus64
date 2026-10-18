"""Collision and placement queries shared by map-derived NPC generators."""
import math
import re


def triangle_in_box(points, bounds):
    """Clip a triangle to an AABB; bounding-box overlap alone rejects slopes."""
    polygon = list(points)
    for axis, low, high in zip(range(3), bounds[0], bounds[1]):
        for edge, sign in ((low, 1), (high, -1)):
            output = []
            if not polygon:
                return False
            for a, b in zip(polygon[-1:] + polygon[:-1], polygon):
                da, db = sign * (a[axis] - edge), sign * (b[axis] - edge)
                if (da > 0) != (db > 0):
                    t = da / (da - db)
                    output.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
                if db > 0:
                    output.append(b)
            polygon = output
    return bool(polygon)

class Collision:
    """Static collision of the exported hub with a grid index (SM64 floor rules)."""

    CELL = 512

    def __init__(self, path):
        with open(path) as source:
            src = source.read()
        verts = [tuple(int(v) for v in m) for m in
                 re.findall(r"COL_VERTEX\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)", src)]
        self.floors, self.solids = {}, {}
        for m in re.finditer(r"COL_TRI(?:_SPECIAL)?\(\s*(\d+),\s*(\d+),\s*(\d+)", src):
            a, b, c = (verts[int(m.group(i))] for i in (1, 2, 3))
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = a, b, c
            nx = (y2 - y1) * (z3 - z2) - (z2 - z1) * (y3 - y2)
            ny = (z2 - z1) * (x3 - x2) - (x2 - x1) * (z3 - z2)
            nz = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
            mag = math.sqrt(nx * nx + ny * ny + nz * nz)
            if mag == 0:
                continue
            nx, ny, nz = nx / mag, ny / mag, nz / mag
            tri = (a, b, c, nx, ny, nz, -(nx * x1 + ny * y1 + nz * z1))
            xs, zs = (x1, x2, x3), (z1, z2, z3)
            for gx in range(min(xs) // self.CELL, max(xs) // self.CELL + 1):
                for gz in range(min(zs) // self.CELL, max(zs) // self.CELL + 1):
                    (self.floors if ny > 0.01 else self.solids).setdefault((gx, gz), []).append(tri)
                    if ny > 0.01:  # floors also block above the walking height (roofs, benches, ledges)
                        self.solids.setdefault((gx, gz), []).append(tri)

    def floor(self, x, y, z):
        """(height, normal y) of the highest floor at or below y + 78, or None."""
        best = None
        for (a, b, c, nx, ny, nz, oo) in self.floors.get((int(x) // self.CELL, int(z) // self.CELL), ()):
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = a, b, c
            if (z1 - z) * (x2 - x1) - (x1 - x) * (z2 - z1) < 0:
                continue
            if (z2 - z) * (x3 - x2) - (x2 - x) * (z3 - z2) < 0:
                continue
            if (z3 - z) * (x1 - x3) - (x3 - x) * (z1 - z3) < 0:
                continue
            h = -(x * nx + nz * z + oo) / ny
            if y - (h - 78.0) >= 0 and (best is None or h > best[0]):
                best = (h, ny)
        return best

    def blocked(self, x, z, y0, y1, r):
        """Any static triangle overlapping the box x +- r, z +- r, y0..y1."""
        seen = set()
        for gx in range(int(x - r) // self.CELL, int(x + r) // self.CELL + 1):
            for gz in range(int(z - r) // self.CELL, int(z + r) // self.CELL + 1):
                for t in self.solids.get((gx, gz), ()):
                    if id(t) in seen:
                        continue
                    seen.add(id(t))
                    xs, ys, zs = [v[0] for v in t[:3]], [v[1] for v in t[:3]], [v[2] for v in t[:3]]
                    if (max(xs) > x - r and min(xs) < x + r and max(ys) > y0 and min(ys) < y1
                            and max(zs) > z - r and min(zs) < z + r):
                        return True
        return False

    def body_blocked(self, x, z, y0, y1, r):
        seen = set()
        for gx in range(math.floor((x-r) / self.CELL), math.floor((x+r) / self.CELL)+1):
            for gz in range(math.floor((z-r) / self.CELL), math.floor((z+r) / self.CELL)+1):
                for tri in self.solids.get((gx, gz), ()):
                    if id(tri) in seen:
                        continue
                    seen.add(id(tri))
                    if triangle_in_box(tri[:3], ((x-r, y0, z-r), (x+r, y1, z+r))):
                        return True
        return False

