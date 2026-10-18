"""Partition outdoor paving by purpose, instead of stacking almost coplanar faces.

Clipping interpolates the original UVs (including oriented crossing stripes). Only
flat, opaque visual ground is eligible; collision, ponds and raised geometry stay
with their original builders. No optional geometry dependencies are required.
"""
import math

GROUND_Z = -0.03  # below the collision/shadow floor; all visible pieces meet here
PRIORITY = {
    'ground_grass': 0, 'grass': 5, 'lawn': 10, 'forest_floor': 11,
    'mulch': 12, 'parking': 20, 'plaza_brick': 30,
    'concrete': 31, 'path': 31, 'sidewalk': 31, 'steps': 32,
    'asphalt': 40, 'road_paint': 50, 'crosswalk': 60,
}
EPS = 1e-8
CELL = 16.0


def area(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def halfplane(poly, a, b, left=True):
    """Clip vertices (x,y,z,u,v) and interpolate all attributes at new edges."""
    def side(p):
        d = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        return d if left else -d
    out = []
    for p, q in zip(poly[-1:] + poly[:-1], poly):
        sp, sq = side(p), side(q)
        if (sp >= 0) != (sq >= 0):
            t = sp / (sp - sq)
            out.append(tuple(p[i] + t * (q[i] - p[i]) for i in range(len(p))))
        if sq >= 0:
            out.append(q)
    clean = []
    for p in out:
        if not clean or math.dist(p[:2], clean[-1][:2]) > EPS:
            clean.append(p)
    if len(clean) > 1 and math.dist(clean[0][:2], clean[-1][:2]) <= EPS:
        clean.pop()
    return clean if len(clean) >= 3 and area(clean) > EPS else []


def subtract(poly, cover):
    # Avoid splitting a disjoint polygon by the cover's extended edge lines.
    overlap = poly
    for a, b in zip(cover, cover[1:] + cover[:1]):
        overlap = halfplane(overlap, a, b)
        if not overlap:
            return [poly]
    rest, out = poly, []
    for a, b in zip(cover, cover[1:] + cover[:1]):
        if not rest:
            break
        outside = halfplane(rest, a, b, False)
        if outside:
            out.append(outside)
        rest = halfplane(rest, a, b)
    return out


def bounds(poly):
    return min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)


def cells(bb):
    for x in range(math.floor(bb[0] / CELL), math.floor(bb[2] / CELL) + 1):
        for y in range(math.floor(bb[1] / CELL), math.floor(bb[3] / CELL) + 1):
            yield x, y


def partition(surfaces):
    """(owner, points, material, UVs, priority) -> disjoint faces with original owners.

    Inputs are convex faces, split into triangles by the caller when necessary.
    Equal priorities use stable input order. Higher-priority *original* faces
    cover lower ones even when another face has already cut that cover itself.
    """
    grid, covers, result = {}, [], []
    ordered = sorted(enumerate(surfaces), key=lambda it: (it[1][4], it[0]), reverse=True)
    for _, (owner, pts, mat, uvs, priority) in ordered:
        poly = [(*p, *uv) for p, uv in zip(pts, uvs)]
        signed = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
        if signed < 0:
            poly.reverse()
        bb = bounds(poly)
        candidates = sorted({i for c in cells(bb) for i in grid.get(c, ())})
        pieces = [poly]
        for i in candidates:
            cover, cb = covers[i]
            if min(bb[2], cb[2]) - max(bb[0], cb[0]) <= EPS or min(bb[3], cb[3]) - max(bb[1], cb[1]) <= EPS:
                continue
            pieces = [q for p in pieces for q in subtract(p, cover)]
            if not pieces:
                break
        for p in pieces:
            result.append((owner, [(v[0], v[1], GROUND_Z) for v in p], mat, [(v[3], v[4]) for v in p]))
        index = len(covers)
        covers.append((poly, bb))
        for c in cells(bb):
            grid.setdefault(c, []).append(index)
    return result


def apply(S):
    """Resolve generic ground and eligible landmark paving together before export."""
    import bpy
    import stage_geom as G
    from stage_palette import MATERIALS

    surfaces, owners = [], {}

    def collect(owner, polys):
        retained, count = [], 0
        for pts, mat, uvs in polys:
            zs = [p[2] for p in pts]
            eligible = (mat in PRIORITY and MATERIALS[mat]['kind'] == 'opaque'
                        and max(zs) - min(zs) < 1e-5 and -0.125 <= min(zs) <= -0.009)
            if not eligible:
                retained.append((pts, mat, uvs))
                continue
            # Triangles guarantee convex inputs even for a bent ribbon / ngon.
            for tri in G.triangulate([[p[:2] for p in pts]]):
                lookup = {tuple(p[:2]): (p, uv) for p, uv in zip(pts, uvs)}
                data = [lookup[tuple(p)] for p in tri]
                surfaces.append((owner, [d[0] for d in data], mat, [d[1] for d in data], PRIORITY[mat]))
            count += 1
        if count:
            owners[owner] = retained

    for name in ('Ground visual', 'Roads and paths visual'):
        acc, collision, render = S.accs[name]
        assert not collision and render
        collect(name, acc.polys)
    objects = {}
    for obj in S.landmark_objects:
        if obj.ignore_render or not obj.ignore_collision or obj.type != 'MESH':
            continue
        me = obj.data
        uv = me.uv_layers.active
        polys = []
        for face in me.polygons:
            mat = me.materials[face.material_index].get('sgl_name')
            pts = [tuple(me.vertices[i].co) for i in face.vertices]
            uvs = [tuple(uv.data[i].uv) for i in face.loop_indices]
            polys.append((pts, mat, uvs))
        # Filter non-upward faces independently (the eligibility test checks z).
        # An underside can be flat too: retain it outside the clipping pass.
        upward = [p for p, f in zip(polys, me.polygons) if f.normal.z > 0.99]
        collect(obj.name, upward)
        if obj.name in owners:
            owners[obj.name].extend(p for p, f in zip(polys, me.polygons) if f.normal.z <= 0.99)
            objects[obj.name] = obj
    output = partition(surfaces)
    for owner, pts, mat, uvs in output:
        owners[owner].append((pts, mat, uvs))
    for name, polys in owners.items():
        if name in objects:
            acc = G.MeshAcc(name + ' partitioned', S.tiles)
            acc.polys = polys
            replacement = acc.build(S.mats, parent=S.area, collision=False)
            obj = objects[name]
            if replacement is not None:
                obj.data = replacement.data
                bpy.data.objects.remove(replacement, do_unlink=True)
            else:
                obj.data.clear_geometry()
        else:
            S.accs[name][0].polys = polys
    S.stats['ground_surface_partition'] = {
        'input_triangles': len(surfaces), 'output_faces': len(output),
        'overlap_removed_m2': round(sum(area(p) for _, p, _, _, _ in surfaces)
                                   - sum(area(p) for _, p, _, _ in output), 2),
        'meshes': sorted(owners), 'surface_z_m': GROUND_Z,
        'priority': PRIORITY,
    }
    print('SGL: ground surface partition:', S.stats['ground_surface_partition'])
