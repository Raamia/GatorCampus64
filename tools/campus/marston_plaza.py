"""Reference-led Marston / CSE / Turlington landscape, in map metres.

The campus survey omits these pedestrian areas. Author paving explicitly instead
of treating the gaps between buildings as lawn. Heights are a gameplay-scale
approximation from photos, not surveyed elevations. Marston rises with its entrance landing.
All new raised features contribute their real treads, risers and walls to collision.
"""
import math
import stage_geom as G
from ground_surfaces import subtract, halfplane

# Keep Newell Drive and its existing sidewalk, and all existing buildings.
# Follow the podium's south/east outline with a small overlap under its walls;
# the old coarse outline left strips of the base grass visible at every setback.
PLAZA = [(-134, -26), (-134, -18), (-118.0, -14.8),
         (-102.4, -13.9), (-102.4, -7.2), (-91, -8.9),
         (-75.8, -3.0), (-73.3, 1.5), (-73.3, 11.3),
         (-67.0, 11.3), (-61.4, 17.0), (-64.5, 26.0),
         (-34.0, 59.3), (-29.0, 57.0), (-19, 56), (-19, -132),
         (-33, -132), (-33, -87), (-42, -87), (-42, -79), (-40, -79),
         (-40, -67), (-70, -67), (-70, -71), (-92, -89), (-95, -86),
         (-134, -86)]
COURT_ID = 'w588044235'
HEIGHT = 1.20


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _triangles(poly):
    return G.triangulate([G.ccw(poly)])


def _intersection(poly, cover):
    out = [tuple(p) + (0, 0, 0) for p in poly]
    for a, b in zip(cover, cover[1:] + cover[:1]):
        out = halfplane(out, a, b)
        if not out:
            break
    return [p[:2] for p in out]


def _erase(acc, regions, height=None):
    """Cut only near-ground visual faces; preserve original UVs outside the plaza."""
    covers = [t for region in regions for t in _triangles(region)]
    boxes = [G.bbox(t) for t in covers]
    out = []
    for pts, mat, uvs in acc.polys:
        # Street paving and markings survive landscape replacement; the shared
        # ground partition then clips plaza panels against their full footprint.
        if height is None and mat in {'asphalt', 'road_paint', 'crosswalk'}:
            out.append((pts, mat, uvs))
            continue
        if not all((-0.125 <= p[2] <= -0.009) if height is None else abs(p[2] - height) < 1e-5 for p in pts):
            out.append((pts, mat, uvs))
            continue
        bb = G.bbox(pts)
        candidates = [t for t, b in zip(covers, boxes)
                      if min(bb[2], b[2]) > max(bb[0], b[0]) and min(bb[3], b[3]) > max(bb[1], b[1])]
        if not candidates:
            out.append((pts, mat, uvs))
            continue
        data = {tuple(p[:2]): tuple(p) + tuple(uv) for p, uv in zip(pts, uvs)}
        pieces = [[data[tuple(p)] for p in t] for t in _triangles([p[:2] for p in pts])]
        for t in candidates:
            pieces = [q for piece in pieces for q in subtract(piece, t)]
        out.extend(([p[:3] for p in q], mat, [p[3:] for p in q]) for q in pieces)
    acc.polys = out


def build(S):
    if S.key != 'hub':
        return
    import json
    from pathlib import Path
    from stage_nature import oak, trunk
    campus = json.loads((Path(S.root) / 'data/uf/campus.json').read_text())
    court = G.ccw(next(a['pts'] for a in campus['areas'] if a['id'] == COURT_ID))
    regions = [G.ccw(PLAZA), court, rect(-72, -135, -22, -124)]
    # Pave only the covered Turlington passage, using the same bounds as the
    # building cutout and clipping to its podium so adjacent lawns stay intact.
    from landmarks.marston_turlington import T_PODIUM, T_TUNNEL_X, T_TUNNEL_Y
    # Tuck paving 12 cm beneath the side walls to hide the ground-to-wall seam.
    tunnel = rect(T_TUNNEL_X[0], T_TUNNEL_Y[0] - .12,
                  T_TUNNEL_X[1], T_TUNNEL_Y[1] + .12)
    passage = [q for t in _triangles(T_PODIUM)
               if len(q := _intersection(tunnel, t)) >= 3]
    local_regions = [[S.T(p) for p in r] for r in regions + passage]
    vis = S.acc('Ground visual', collision=False)
    col = S.acc('Marston plaza collision', render=False)
    for name in ('Ground visual', 'Roads and paths visual'):
        _erase(S.accs[name][0], local_regions)

    def flat(poly, z, mat, collision=False):
        # Split paving and collision into modest cells for UV and engine limits.
        for t in _triangles(poly):
            for q in G.grid_pieces(t, 8):
                pts = [(*S.T(p), z - 0.02 if z > 0 else -0.03) for p in q]
                vis.poly(pts, mat)
                if collision:
                    col.poly([(*S.T(p), z) for p in q], 'COL default')

    def wall(a, b, z0, z1, mat='brick_red', collision=True):
        vis.wall(S.T(a), S.T(b), z0 - 0.02, z1 - 0.02, mat)
        if collision:
            col.wall(S.T(a), S.T(b), max(0, z0), z1, 'COL default')

    # Material panels are disjoint, not stacked. Concrete borders define a large
    # plaza grid; no old narrow walk ribbons remain inside the authored outline.
    def panels(region, base, band, spacing, z=0, collision=False):
        x0, y0, x1, y1 = G.bbox(region)
        triangles = _triangles(region)
        for x in range(math.floor(x0 / spacing), math.ceil(x1 / spacing)):
            for y in range(math.floor(y0 / spacing), math.ceil(y1 / spacing)):
                a, b = x * spacing, y * spacing
                for r, m in ((rect(a, b, a + spacing - .22, b + spacing - .22), base),
                             (rect(a + spacing - .22, b, a + spacing, b + spacing), band),
                             (rect(a, b + spacing - .22, a + spacing - .22, b + spacing), band)):
                    for t in triangles:
                        q = _intersection(r, t)
                        if len(q) >= 3:
                            flat(q, z, m, collision)
    panels(regions[0], 'plaza_brick', 'concrete', 6)
    grove = rect(-70, -67, -19, -28)
    # Brick is the dominant field throughout the court; gray defines narrow joints.
    _erase(vis, [[S.T(p) for p in grove]])
    panels(grove, 'plaza_brick', 'concrete', 6)
    apron = rect(-42, -86, -19, -67)
    _erase(vis, [[S.T(p) for p in apron]])
    panels(apron, 'plaza_brick', 'concrete', 8)
    panels(court, 'plaza_brick', 'concrete', 8)
    panels(regions[2], 'plaza_brick', 'concrete', 6)
    for piece in passage:
        panels(piece, 'plaza_brick', 'concrete', 6)

    # Connected terrain surfaces. Every boundary derives its retaining face from
    # its neighbour's height, including stair mouths and ramp ends.
    terrain = []
    stair_rails = []
    def surface(poly, z, mat='plaza_brick', patterned=False):
        poly = G.ccw(poly)
        height = z if callable(z) else lambda x, y, level=z: level
        terrain.append((poly, height))
        if callable(z):
            vis.poly([(*S.T(p), height(*p) - .02) for p in poly], mat)
        elif patterned:
            panels(poly, mat, 'concrete', 8, z)
        else:
            flat(poly, z, mat)
        # Collision follows geometry, not each decorative material band.
        for tri in _triangles(poly):
            for q in G.grid_pieces(tri, 8):
                col.poly([(*S.T(p), height(*p)) for p in q], 'COL default')
    grove_z = HEIGHT
    # One shared upper level joins the door apron and tree court. In particular,
    # y=-63..-61 used to be an unfilled channel between independent platforms.
    surface(rect(-70, -63, -30.4, -31), grove_z, patterned=True)
    # Close the narrow lower channel against CSE's stepped east facade. The
    # infill shares the court level and meets the existing entrance apron.
    wall_x = -72.71 + .20 * ((-63 + 48.83) / (-67.58 + 48.83))
    surface([(-70, -63), (-70, -31), (-70.91, -31),
             (-70.91, -36.25), (-71.16, -47.66), (-72.71, -48.83),
             (wall_x, -63)], grove_z, patterned=True)
    surface([(-70, -63), (wall_x, -63), (-72.51, -67.58),
             (-74.02, -67.62)], grove_z, patterned=True)
    # Street-facing corner anchors the main entry axis at y=-65. The landing
    # meets the door apron at x=-40 without an internal drop or second stair.
    surface(rect(-40, -68, -30.4, -63), grove_z, patterned=True)
    # Clear the mapped palm from the corrected stair approach.
    S.removed_points.add('n9283821144')
    upper = [(-74.02, -67.62), (-70.97, -70.51), (-69, -69),
             (-40, -69), (-40, -63), (-70, -63)]
    surface(upper, HEIGHT, patterned=True)
    # The connector's end is stepped back from the straight apron edge. Fill
    # that small polygon so the two raised floors meet without a sunken notch.
    surface([(-74.02, -67.62), (-74.07, -68.60), (-73.17, -69.57),
             (-72.13, -70.56), (-70.97, -70.51)], HEIGHT, patterned=True)
    # The floor under the connector joins both open ends at the same height.
    covered = next(b['pts'] for b in campus['buildings'] if b['id'] == 'w859919297')
    surface(covered, HEIGHT, patterned=True)
    west = [(-124, -94), (-124, -103), (-118, -116), (-108, -121),
            (-98, -121), (-98, -100), (-90, -96), (-89.33, -87.38),
            (-87.94, -87.36), (-90.83, -84.36), (-90.85, -86.03),
            (-101.68, -86.22), (-105.72, -90.65)]
    surface(west, HEIGHT, patterned=True)
    surface(rect(-92.5, -107.3, -86.9, -93.7), HEIGHT, patterned=True)
    # Three street flights and two western approaches reach the shared court level.
    mouths = [(-67, -61), (-49, -45), (-39, -35)]
    for low, high in mouths:
        for k in range(12):
            x = -25.6 - k * .4
            surface(rect(x - .4, low, x, high), (k + 1) * .1, 'plaza_brick')
        stair_rails += [((-25.6, y), (-30.4, y), 0, grove_z) for y in (low + .12, high - .12)]
    # Side access from the lower apron beside Marston's tower, and directly
    # from Turlington. Each top tread meets the existing court boundary exactly.
    for k in range(12):
        south_y = -72.8 + k * .4
        surface(rect(-39, south_y, -32, south_y + .4), (k + 1) * .1)

    stair_rails += [((x, -72.8), (x, -68), 0, HEIGHT) for x in (-38.85, -32.15)]
    # Four north-facing flights distribute access along the retaining wall.
    # The western flight replaces the former long ramp.
    north_mouths = [(-68, -62), (-60, -56), (-51, -47), (-40, -36)]
    for left, right in north_mouths:
        for k in range(12):
            y = -26.2 - k * .4
            surface(rect(left, y - .4, right, y), (k + 1) * .1)
        stair_rails += [((x, -26.2), (x, -31), 0, HEIGHT)
                        for x in (left + .15, right - .15)]
    # Once up the outer stairs, all paths converge at the entrance level.
    for k in range(10):
        x = -128 + k * .4
        surface(rect(x, -102, x + .4, -96), (k + 1) * .12, 'plaza_brick')
        y = -125 + k * .4
        surface(rect(-108, y, -102, y + .4), (k + 1) * .12, 'plaza_brick')
    stair_rails += [((-128, y), (-124, y), 0, HEIGHT) for y in (-101.85, -96.15)]

    def inside(p, poly):
        # Boundary is deliberately accepted: adjacent surfaces meet exactly.
        x, y = p; hit = False
        for a, b in zip(poly, poly[1:] + poly[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            if abs(dx * (y - a[1]) - dy * (x - a[0])) < 1e-7 and min(a[0], b[0]) - 1e-7 <= x <= max(a[0], b[0]) + 1e-7 and min(a[1], b[1]) - 1e-7 <= y <= max(a[1], b[1]) + 1e-7:
                return True
            if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * dx / dy:
                hit = not hit
        return hit
    def level(p):
        return max([0] + [h(*p) for poly, h in terrain if inside(p, poly)])
    edge_checks = []
    for poly, height in terrain:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]; length = math.hypot(dx, dy)
            ts = [0, 1]
            for other, _ in terrain:
                for c, d in zip(other, other[1:] + other[:1]):
                    ex, ey = d[0] - c[0], d[1] - c[1]
                    den = dx * ey - dy * ex
                    if abs(den) > 1e-8:
                        t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den
                        u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den
                        if 0 < t < 1 and -1e-7 <= u <= 1 + 1e-7: ts.append(t)
                    elif abs(dx * (c[1] - a[1]) - dy * (c[0] - a[0])) < 1e-7:
                        for p in (c, d):
                            t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length ** 2
                            if 0 < t < 1: ts.append(t)
            ts = sorted(set(round(t, 9) for t in ts))
            for lo, hi in zip(ts, ts[1:]):
                if hi - lo < 1e-7: continue
                A = (a[0] + lo * dx, a[1] + lo * dy)
                B = (a[0] + hi * dx, a[1] + hi * dy)
                offset = (dy / length * .001, -dx / length * .001)
                mid = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
                bottom = level((mid[0] + offset[0], mid[1] + offset[1]))
                if height(*mid) <= bottom + 1e-5: continue
                za, zb = height(*A), height(*B)
                pts = [(*S.T(A), bottom - .02), (*S.T(B), bottom - .02),
                       (*S.T(B), zb - .02), (*S.T(A), za - .02)]
                vis.poly(pts, 'brick_red')
                col.poly([(x, y, z + .02) for x, y, z in pts], 'COL default')
                edge_checks.append({'a': A, 'b': B, 'bottom': bottom, 'top': [za, zb]})
    S.stats['marston_retaining_edges'] = edge_checks

    # Narrow gray rings are cut into the brick field without layered surfaces.
    for cx, cy, radius, z in [(-111, -104, 5.5, HEIGHT), (-111, -104, 10, HEIGHT),
                               (-45, -46, 8.5, grove_z)]:
        rings = []
        for k in range(32):
            a, b = k * math.tau / 32, (k + 1) * math.tau / 32
            q = [(cx + r * math.cos(t), cy + r * math.sin(t))
                 for r, t in [(radius, a), (radius, b), (radius - .24, b), (radius - .24, a)]]
            for poly, h in terrain:
                if abs(h(cx, cy) - z) > 1e-5: continue
                for tri in _triangles(poly):
                    cut = _intersection(q, tri)
                    if len(cut) >= 3: rings.append(cut)
        _erase(vis, [[S.T(p) for p in r] for r in rings], height=z - .02)
        for r in rings: flat(r, z, 'concrete')

    def planter(cx, cy, hx=2.0, hy=1.6, tree=True, base=0):
        # Rounded brick beds with a narrow brick coping and clipped hedge surface.
        def rounded(inset):
            r = .65 - inset
            return [(cx + sx * (hx - .65) + r * math.cos(a + k * math.pi / 8),
                     cy + sy * (hy - .65) + r * math.sin(a + k * math.pi / 8))
                    for sx, sy, a in [(1, 1, 0), (-1, 1, math.pi / 2),
                                      (-1, -1, math.pi), (1, -1, 3 * math.pi / 2)] for k in range(5)]
        vstart, cstart = len(vis.polys), len(col.polys)
        outer, inner = rounded(0), rounded(.22)
        for i, a in enumerate(outer):
            j = (i + 1) % len(outer); b = outer[j]
            wall(a, b, 0, .62)
            vis.poly([(*S.T(p), .60) for p in (a, b, inner[j], inner[i])], 'brick_red')
        flat(inner, .59, 'mulch')
        # Solid bed top and trunk stop clipping through the vegetation.
        # Eight tangent points approximate the rounded bed for collision;
        # the finer visual curve does not need twenty collision corners.
        corners = (0, 4, 5, 9, 10, 14, 15, 19)
        col.flat([S.T(outer[i]) for i in corners], .62, 'COL default')
        flat(rounded(.33), .85, 'leaves_oak2')
        col.flat([S.T(rounded(.33)[i]) for i in corners], .85, 'COL default')
        hedge = rounded(.33)
        for a, b in zip(hedge, hedge[1:] + hedge[:1]):
            wall(a, b, .59, .85, 'leaves_oak2', False)
        x, y = S.T((cx, cy))
        if tree:
            tree_start = len(vis.polys)
            oak(vis, x, y, f'marston-court-{cx}-{cy}', 2.6, crown=5.5)
            # Scale only the ring tree, keeping its bed and the campus trees intact.
            scale = .65
            vis.polys[tree_start:] = [
                ([(x + (px - x) * scale, y + (py - y) * scale, .62 + pz * scale)
                  for px, py, pz in pts], mat, uv)
                for pts, mat, uv in vis.polys[tree_start:]]
            trunk(col, x, y, .35 * scale, .62, .62 + 5.5 * scale, 6, 'COL default', 'plaza')
        for acc, start in ((vis, vstart), (col, cstart)):
            acc.polys[start:] = [([(x, y, z + base) for x, y, z in pts], mat, uv)
                                 for pts, mat, uv in acc.polys[start:]]
    for x, y, base in [(-129, -94, 0), (-127, -109, 0), (-113, -123, 0), (-112, -96, HEIGHT), (-103, -113, HEIGHT)]:
        planter(x, y, base=base)
    # Fewer, spaced beds with varied lengths, following the ground references.
    # Keep the north stair's x=-58.5 approach and westbound door apron open.
    beds = [(-65, -57, 2.0, 1.6), (-65, -46, 2.4, 1.8), (-65, -35, 2.0, 1.6),
            (-54, -56, 2.6, 1.7), (-53, -43, 3.2, 1.9), (-54, -35, 1.6, 1.5),
            (-44, -57, 2.0, 1.6), (-43, -46, 3.0, 1.8), (-44, -35, 2.0, 1.6),
            (-33.5, -56, 1.6, 1.5), (-33.5, -45, 1.6, 1.5), (-33.5, -35, 1.6, 1.5)]
    for x, y, hx, hy in beds:
        planter(x, y, hx, hy, base=grove_z)
    # Long low planting beds frame the lower gathering space toward Turlington.
    for x in (-51, -38):
        planter(x, -22, 4.0, 1.5, tree=False)

    from stage_dressing import _obox
    def box(mx, my, hx, hy, z0, z1, side, top=None):
        x, y = S.T((mx, my))
        _obox(vis, x, y, 0, hx, hy, z0, z1, side, top or side, side)
        _obox(col, x, y, 0, hx, hy, z0, z1, 'COL default', 'COL default', 'COL default')

    # Low brick seating ledges alongside the planting, clear of through routes.
    for x in (-51, -38):
        box(x, -19.9, 3.6, .3, 0, .42, 'brick_red')
        box(x, -19.9, 3.7, .4, .42, .50, 'concrete')

    # Turlington gathering area: keep the central tabling route and Potato open,
    # and put planted seating and slab tables along the quieter perimeter.
    turlington_beds = [(-69, -10, 4.0, 1.8), (-32, 3, 4.0, 1.8),
                       (-29, 20, 1.8, 4.5), (-25, 43, 1.7, 5.0)]
    for x, y, hx, hy in turlington_beds:
        planter(x, y, hx, hy)
    for x, y, hx, hy in [(-69, -12.4, 3.7, .35), (-32, .6, 3.7, .35),
                          (-31.4, 20, .35, 4.2), (-27.3, 43, .35, 4.7)]:
        box(x, y, hx, hy, 0, .42, 'brick_red')
        box(x, y, hx + .10, hy + .10, .42, .50, 'concrete')
    for x, y in [(-67, -2), (-33, 12)]:
        box(x, y, .55, .55, 0, .72, 'brick_red')
        box(x, y, 1.25, .80, .72, .86, 'concrete')
        for offset in (-1.5, 1.5):
            box(x, y + offset, 1.1, .28, 0, .40, 'brick_red')
            box(x, y + offset, 1.2, .36, .40, .48, 'concrete')

    # Sheltered threshold: dark piers and fascia under the first existing ledge.
    # The doorway stays at its established position and the central route is clear.
    for x in (-64, -53):
        box(x, -66.1, .28, .28, HEIGHT, 2.1, 'brick_red')
        box(x, -66.1, .23, .23, 2.1, 5.15, 'dark_trim')
    box(-58.5, -67.35, 6.0, 1.65, 5.15, 5.4, 'dark_trim')

    # Square courtyard lanterns visible in the approach photos.
    for mx, my, base in [(-62, -55, HEIGHT), (-47, -52, HEIGHT),
                         (-38, -40, HEIGHT), (-52, -20, 0), (-39, -20, 0)]:
        box(mx, my, .09, .09, base, base + 3.5, 'dark_trim')
        box(mx, my, .34, .34, base + 3.5, base + 4.0, 'white_trim')
        box(mx, my, .39, .39, base + 4.0, base + 4.1, 'dark_trim')
        for dx in (-.30, 0, .30):
            box(mx + dx, my, .035, .35, base + 3.5, base + 4, 'dark_trim')

    # Slim railings make the street stair entrances legible. Posts live on the
    # outer edge of each 4m flight, leaving the full central walking width.
    def rail(a, b, z0, z1):
        ax, ay = S.T(a); bx, by = S.T(b)
        length = math.dist(a, b)
        nx, ny = -(b[1] - a[1]) / length * .045, (b[0] - a[0]) / length * .045
        for x, y, z in [(ax, ay, z0), (bx, by, z1)]:
            trunk(vis, x, y, .045, z, z + .9, 5, 'metal_gray', 'rail')
        p = [(ax + nx, ay + ny, z0 + .9), (bx + nx, by + ny, z1 + .9),
             (bx - nx, by - ny, z1 + .9), (ax - nx, ay - ny, z0 + .9)]
        vis.poly(p, 'metal_gray')
        vis.poly([(x, y, z - .075) for x, y, z in p[::-1]], 'metal_gray')
        for u, v in zip(p, p[1:] + p[:1]):
            vis.poly([u, v, (v[0], v[1], v[2] - .075), (u[0], u[1], u[2] - .075)], 'metal_gray')
    for a, b, z0, z1 in stair_rails:
        rail(a, b, z0, z1)

    # Courtyard lanterns: dark posts and simple pale globes, without banners.
    for mx, my in [(-24.3, -52), (-24.3, -42), (-116, -104), (-104, -116),
                   (-29, -6), (-26, 29), (-34, 39), (-65, 3)]:
        x, y = S.T((mx, my))
        trunk(vis, x, y, .16, 0, .35, 6, 'dark_trim', 'lamp-base')
        trunk(vis, x, y, .065, .35, 3.5, 6, 'dark_trim', 'lamp-post')
        trunk(col, x, y, .13, 0, 3.7, 6, 'COL default', 'lamp-post')
        r = [(x + .24 * math.cos(k * math.pi / 4), y + .24 * math.sin(k * math.pi / 4)) for k in range(8)]
        for a, b in zip(r, r[1:] + r[:1]):
            vis.wall(a, b, 3.5, 3.9, 'white_trim')
            vis.poly([(*a, 3.9), (*b, 3.9), (x, y, 4.04)], 'dark_trim')
        vis.flat(r, 3.5, 'dark_trim', down=True)

    S.stats['marston_plaza'] = {
        'references': ['UF campus map layout', 'UF_TurlingtonPlaza.jpg', 'user courtyard ground photos',
                       'https://ufosc.org/blog/where-is-cseA101/'],
        'elevation_note': 'Approximate: shared Marston sill/courtyard/grove 1.20m; twelve-riser street flights, ten-riser western approaches and four north-facing stair flights.',
        'collision_triangles': col.tri_count(),
        'planters': 23, 'grove_trees': len(beds), 'stairs': 10, 'door_threshold_m': HEIGHT,
        'ring_tree_scale': .65, 'seat_ledges': 6, 'brick_tables': 2, 'courtyard_lanterns': 5,
        'turlington_globe_lamps': 4,
    }
    print('SGL: Marston plaza:', col.tri_count(), 'new collision triangles')
