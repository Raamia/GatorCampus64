"""REITZ UNION + ENGINEERING stage: the Museum Rd / Center Dr / McCarty Dr / Reitz Union Dr streetscape
between Malachowsky Hall and the Reitz Union (street view references reference/streetview/reitz_20261017).

Landmark module (contract: tools/campus/landmarks/_common.py). One LANDMARKS entry, "stages": ["reitz_eng"],
replaces nothing (osm_ids []). Everything is placed on the real OSM ways of data/uf/campus.json, found by
name, and sits on stage_terrain.height_m("reitz_eng", x, y) when that module exists (else z = 0).

  1. road paint: double yellow centre lines (two-way roads), white bike-lane / edge lines, zebra crosswalks
     on junction legs that have no OSM crossing (the generator already draws the OSM ones) - thin quads
     1.5 cm above the road ribbon (stage_ground Z road -0.02 -> -0.005 m), visual only, never coplanar
     with the generator's dashes (-0.01) or crossings (+0.01).
  2. the black bollard + hanging chain row on the lawn side of the Malachowsky lawn sidewalk (w864376868),
     with gaps where walks join it; visual only (Mario can hop it anyway).
  3. black ornamental lamp posts every ~30 m along those roads (visual only).
  4. two bus shelters on McCarty Dr (pitched dark metal roof on posts, a bench each); roof, bench and
     posts collide.
  5. palms along Reitz Union Dr (the theatre already has OSM palms on its east side).
Not done: "BUS ONLY" text and the yellow hatched median islands (no lettering / hatch texture).
Disable: delete this file (the generator also skips a module that raises, see stage_landmarks.load_modules).
Self-test (no Blender): python3 tools/campus/landmarks/reitz_streetscape.py
"""
import math
import os
import sys

try:
    from . import _common as C
except ImportError:  # run as a script (self-test)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

STAGE = "reitz_eng"
SLUG = "reitz_streetscape"
LANDMARKS = [{"slug": SLUG, "name": "Reitz streetscape", "osm_ids": [], "center_m": (-430.0, -420.0),
              "stages": [STAGE]}]

ROADS = ("Museum Road", "Center Drive", "McCarty Drive", "Reitz Union Drive")
DEFAULT_W = {"Museum Road": 8.0, "Center Drive": 7.0, "McCarty Drive": 6.0, "Reitz Union Drive": 6.0}
REGION = (-560.0, -563.0, -205.0, -330.0)        # xmin, ymin, xmax, ymax (Malachowsky .. Reitz Union)
SIDEWALK_ID = "w864376868"                        # Malachowsky lawn sidewalk along Museum Rd (south side)
SHELTER_WAY = "w10246967"                         # McCarty Drive (the curve under the oaks)
PALM_WAY = "w1205038960"                          # Reitz Union Drive (Museum Rd -> the union)
Z_PAINT = -0.005                                  # road ribbon -0.02, generator dashes -0.01
PIECE_M = 8.0
# generator materials the landmark palette lacks (they exist in stage_palette.GENERATOR_MATERIALS)
EXTRA_TILE = {"road_paint": 2.0, "palm_trunk": 2.0, "palm_frond": 2.0, "mulch": 2.0, "leaves_pine": 4.0, "leaves_oak2": 4.0}
BLACK, WHITE, YELLOW = "dark_trim", "white_trim", "road_paint"


# ------------------------------------------------------------------ terrain (owned by another module)
def _height_fn():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import stage_terrain
        f = stage_terrain.height_m
    except Exception:  # noqa: BLE001 - terrain is optional
        return lambda x, y: 0.0

    def h(x, y):
        try:
            v = float(f(STAGE, x, y))
            return v if math.isfinite(v) else 0.0
        except Exception:  # noqa: BLE001
            return 0.0
    return h


class _B(C.Builder):
    """Builder that also accepts the generator's road_paint / palm materials (explicit projected UVs)."""

    def poly(self, pts3, material, uvs=None, normal_hint=None, smooth=False):
        if material not in C.PALETTE and material not in EXTRA_TILE:
            raise ValueError(f"unknown material {material!r}")
        pts3 = [tuple(float(c) for c in p) for p in pts3]
        if len(pts3) < 3:
            return
        if uvs is None:
            tile = C.PALETTE[material]["tile_m"] if material in C.PALETTE else EXTRA_TILE[material]
            uvs = C.project_uv(pts3, tile)
        self.polys.append((pts3, material, uvs, smooth))


# ------------------------------------------------------------------ data helpers (pure Python)
def _f(v, d):
    try:
        return float(str(v).split()[0])
    except (TypeError, ValueError, IndexError):
        return d


def _in_box(p, box, pad=0.0):
    return box[0] - pad <= p[0] <= box[2] + pad and box[1] - pad <= p[1] <= box[3] + pad


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _poly_dist(p, pts):
    return min(_seg_dist(p, a, b) for a, b in zip(pts, pts[1:])) if len(pts) > 1 else 1e9


def _inside(p, poly):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


class Site:
    """The OSM data this module needs, from ctx["campus"]."""

    def __init__(self, campus):
        ways = campus.get("ways", [])
        self.roads = []      # (id, name, width, oneway, pts)
        self.paths = []      # (id, tags, pts)
        self.by_id = {}
        for w in ways:
            t = w.get("tags", {})
            pts = [tuple(p) for p in w.get("pts", [])]
            self.by_id[w["id"]] = (t, pts)
            hw = t.get("highway")
            if hw in ("footway", "path", "cycleway", "steps", "pedestrian"):
                self.paths.append((w["id"], t, pts))
            elif t.get("name") in ROADS and hw and len(pts) > 1:
                n = t["name"]
                width = _f(t.get("width"), 0.0) or (_f(t.get("lanes"), 0.0) * 3.3) or DEFAULT_W[n]
                self.roads.append((w["id"], n, max(4.0, min(width, 12.0)), t.get("oneway") == "yes", pts))
        self.buildings = []
        for b in campus.get("buildings", []):
            pts = [tuple(p) for p in b.get("pts", [])]
            if len(pts) < 3:
                continue
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            bb = (min(xs), min(ys), max(xs), max(ys))
            if bb[2] > REGION[0] - 40 and bb[0] < REGION[2] + 40 and bb[3] > REGION[1] - 40 and bb[1] < REGION[3] + 40:
                self.buildings.append((bb, pts))
        self.crossings = [pts for _i, t, pts in self.paths if t.get("footway") == "crossing"]
        self.junctions = self._junctions()

    def _junctions(self):
        """Points where roads of different names meet: (pt, max half width there)."""
        out = []
        for i, (_ia, na, wa, _oa, pa) in enumerate(self.roads):
            for _ib, nb, wb, _ob, pb in self.roads[i + 1:]:
                if na == nb:
                    continue
                for p in (pa[0], pa[-1]):
                    for q in pb:
                        if math.dist(p, q) < 1.5 and _in_box(p, REGION, 10):
                            if not any(math.dist(p, j) < 6 for j, _ in out):
                                out.append((p, max(wa, wb) / 2))
                for q in (pb[0], pb[-1]):
                    for p in pa:
                        if math.dist(p, q) < 1.5 and _in_box(q, REGION, 10):
                            if not any(math.dist(q, j) < 6 for j, _ in out):
                                out.append((q, max(wa, wb) / 2))
        return out

    def near_junction(self, p, extra=0.0):
        return any(math.dist(p, j) < r + 4.0 + extra for j, r in self.junctions)

    def in_building(self, p, pad=0.0):
        for bb, pts in self.buildings:
            if bb[0] - pad <= p[0] <= bb[2] + pad and bb[1] - pad <= p[1] <= bb[3] + pad:
                if _inside(p, pts) or (pad > 0 and _poly_dist(p, pts + pts[:1]) < pad):
                    return True
        return False

    def on_road(self, p, pad=0.5):
        return any(_poly_dist(p, pts) < w / 2 + pad for _i, _n, w, _o, pts in self.roads)


def _walk(pts, step, start=0.0):
    """[(point, unit dir, s)] every `step` metres along a polyline, from `start`."""
    out = []
    s0 = 0.0
    s = start
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        while s <= s0 + L:
            t = s - s0
            out.append(((a[0] + d[0] * t, a[1] + d[1] * t), d, s))
            s += step
        s0 += L
    return out


def _pieces(pts, piece=PIECE_M):
    """Split a polyline into straight pieces of at most `piece` metres: [(a, b, dir)]."""
    out = []
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if L < 0.05:
            continue
        n = max(1, int(math.ceil(L / piece)))
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        for k in range(n):
            p0 = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            p1 = (a[0] + (b[0] - a[0]) * (k + 1) / n, a[1] + (b[1] - a[1]) * (k + 1) / n)
            out.append((p0, p1, d))
    return out


# ------------------------------------------------------------------ placement (pure Python)
def layout(site):
    """-> dict of placements (map metres): lines, zebras, bollards, lamps, shelters, palms."""
    L = {"lines": [], "zebras": [], "bollards": [], "chains": [], "lamps": [], "shelters": [], "palms": [], "beds": []}
    # 1. road lines: (p0, p1, offset, half width, material)
    for _id, name, w, oneway, pts in site.roads:
        offs = []
        if not oneway:
            offs += [(0.2, 0.07, YELLOW), (-0.2, 0.07, YELLOW)]
        edge = w / 2 - (1.5 if name == "Museum Road" and w >= 7.5 else 0.35)
        offs += [(edge, 0.08, WHITE), (-edge, 0.08, WHITE)]
        for p0, p1, d in _pieces(pts):
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            if not _in_box(mid, REGION) or site.near_junction(mid, 1.0):
                continue
            if any(_poly_dist(mid, c) < 3.0 for c in site.crossings):
                continue
            for off, hw, mat in offs:
                L["lines"].append((p0, p1, d, off, hw, mat))
    # 1b. zebra crosswalks on junction legs without an OSM crossing
    for j, r in site.junctions:
        for _id, _name, w, _o, pts in site.roads:
            for end, nxt in ((pts[0], pts[1:]), (pts[-1], list(reversed(pts[:-1])))):
                if math.dist(end, j) > 1.5 or not nxt:
                    continue
                far = next((q for q in nxt if math.dist(q, j) > 4.0), None)
                if far is None:
                    continue
                dl = math.dist(far, j)
                d = ((far[0] - j[0]) / dl, (far[1] - j[1]) / dl)
                c = (j[0] + d[0] * (r + 2.5), j[1] + d[1] * (r + 2.5))
                if not _in_box(c, REGION) or any(_poly_dist(c, cr) < 6.0 for cr in site.crossings):
                    continue
                L["zebras"].append((c, d, w))
    # 2. bollards + chains on the lawn side of the Malachowsky sidewalk
    sw = site.by_id.get(SIDEWALK_ID)
    if sw:
        t, spts = sw
        off = _f(t.get("width"), 2.0) / 2 + 0.35
        gaps = []
        for pid, _t, pts in site.paths:
            if pid == SIDEWALK_ID or len(pts) < 2:
                continue
            for e in (pts[0], pts[-1]):
                if _poly_dist(e, spts) < 4.0:
                    gaps.append(e)
        prev = None
        for p, d, s in _walk(spts, 2.4, 1.0):
            q = (p[0] + d[1] * off, p[1] - d[0] * off)        # right of the walk = the lawn (south)
            if any(math.dist(q, g) < 2.6 for g in gaps) or site.in_building(q, 0.5):
                prev = None
                continue
            L["bollards"].append(q)
            if prev is not None and math.dist(prev, q) < 3.0:
                L["chains"].append((prev, q))
            prev = q
        # 2b. planting beds (user photos of Malachowsky Hall): a mulch bed with ornamental grass and low
        # shrubs behind the bollard row, and beds on both sides of the walks from this sidewalk to the hall
        # keep every bed (and its plants) off every walk and road: centre-line distance must exceed the
        # walk's half width + the bed's reach + a margin (the drawn walks run a little wider than OSM's)
        near = [(pts, _f(t.get("width"), 2.0) / 2) for _pid, t, pts in site.paths if len(pts) >= 2]
        near += [(pts, w / 2) for _i, _n, w, _o, pts in site.roads]

        def clear(c, reach):
            return all(_poly_dist(c, pts) >= hw_ + reach + 0.45 for pts, hw_ in near)

        for p, d, s_ in _walk(spts, 2.4, 1.0):
            c = (p[0] + d[1] * (off + 1.9), p[1] - d[0] * (off + 1.9))
            if any(math.dist(c, g) < 3.2 for g in gaps) or site.in_building(c, 1.5) or not clear(c, 1.5):
                continue
            L["beds"].append((c, d, 1.15, 1.2))
        for pid, t, pts in site.paths:
            if pid == SIDEWALK_ID or len(pts) < 2 or t.get("footway") == "crossing":
                continue
            if min(_poly_dist(pts[0], spts), _poly_dist(pts[-1], spts)) > 4.0:
                continue
            pw = _f(t.get("width"), 2.0) / 2 + 0.45 + 0.7
            for p, d, s_ in _walk(pts, 2.4, 3.0):
                for side in (1, -1):
                    c = (p[0] + d[1] * pw * side, p[1] - d[0] * pw * side)
                    if site.in_building(c, 1.5) or not _in_box(c, REGION) or not clear(c, 0.69):
                        continue
                    L["beds"].append((c, d, 1.15, 0.7))
    # 3. lamp posts every ~30 m along the roads, sidewalk side(s)
    for _id, name, w, _o, pts in site.roads:
        sides = (1, -1) if name == "Museum Road" else (1,)
        for p, d, _s in _walk(pts, 30.0, 12.0):
            for sd in sides:
                off = (w / 2 + 1.0) * sd
                q = (p[0] - d[1] * off, p[1] + d[0] * off)
                if not _in_box(q, REGION) or site.near_junction(q, 3.0) or site.in_building(q, 1.0):
                    continue
                if site.on_road(q, 0.4) or any(math.dist(q, o) < 12.0 for o in L["lamps"]):
                    continue
                if any(_poly_dist(q, c) < 2.0 for c in site.crossings):
                    continue
                L["lamps"].append(q)
    # 4. two bus shelters on McCarty Dr: first clear spots right of traffic (north side), else south
    mc = site.by_id.get(SHELTER_WAY)
    if mc:
        t, mpts = mc
        w = _f(t.get("width"), 6.0)
        for sd in (1, -1):
            found = []
            for p, d, _s in _walk(mpts, 3.0, 100.0):
                if len(found) == 2:
                    break
                off = (w / 2 + 1.4) * sd
                base = (p[0] - d[1] * off, p[1] + d[0] * off)
                back = (-d[1] * sd, d[0] * sd)                  # away from the road
                if not _in_box(base, REGION, -2) or site.near_junction(base, 6.0):
                    continue
                if found and math.dist(found[-1][0], base) < 9.0:
                    continue
                corners = [(base[0] + d[0] * u + back[0] * v, base[1] + d[1] * u + back[1] * v)
                           for u in (-3.6, 0.0, 3.6) for v in (-0.2, 1.2, 2.6)]
                if any(site.in_building(c, 0.8) for c in corners) or any(site.on_road(c, 0.3) for c in corners):
                    continue
                if any(_poly_dist(c, pp) < 0.8 for _i, _t, pp in site.paths for c in corners[3:]
                       if _i != SHELTER_WAY and _t.get("footway") == "crossing"):
                    continue
                found.append((base, d, back))
            if len(found) == 2:
                L["shelters"] = found
                break
    # 5. palms on the west lawn of Reitz Union Dr
    rd = site.by_id.get(PALM_WAY)
    if rd:
        t, rpts = rd
        w = _f(t.get("width"), 8.0)
        for p, d, _s in _walk(rpts, 11.0, 10.0):
            for sd in (1, -1):
                off = (w / 2 + 3.0) * sd
                q = (p[0] - d[1] * off, p[1] + d[0] * off)
                if not _in_box(q, REGION, 30) or site.near_junction(q, 2.0) or site.in_building(q, 2.0):
                    continue
                if site.on_road(q, 1.5) or any(_poly_dist(q, pp) < 1.0 for _i, _t, pp in site.paths):
                    continue
                L["palms"].append(q)
    return L


# ------------------------------------------------------------------ geometry
def _pole(b, x, y, z0, z1, r0, r1, mat, top=True):
    c0 = [(x - r0, y - r0), (x + r0, y - r0), (x + r0, y + r0), (x - r0, y + r0)]
    c1 = [(x - r1, y - r1), (x + r1, y - r1), (x + r1, y + r1), (x - r1, y + r1)]
    for i in range(4):
        a0, b0, a1, b1 = c0[i], c0[(i + 1) % 4], c1[i], c1[(i + 1) % 4]
        b.poly([(a0[0], a0[1], z0), (b0[0], b0[1], z0), (b1[0], b1[1], z1), (a1[0], a1[1], z1)], mat)
    if top:
        b.poly([(px, py, z1) for px, py in c1], mat)


def _ribbon_v(b, p, q, z0, z1, hz, mat):
    """Thin vertical double-sided strip from p (top z0) to q (top z1), hz tall."""
    pts = [(p[0], p[1], z0 - hz), (q[0], q[1], z1 - hz), (q[0], q[1], z1), (p[0], p[1], z0)]
    b.poly(pts, mat)
    b.poly(list(reversed(pts)), mat)


def build_geometry(site, L, h):
    vis, col = _B(), _B()
    # road lines (per-vertex terrain height, 1.5 cm above the road ribbon)
    for p0, p1, d, off, hw, mat in L["lines"]:
        nx, ny = -d[1], d[0]
        q = [(p0[0] + nx * (off - hw), p0[1] + ny * (off - hw)), (p1[0] + nx * (off - hw), p1[1] + ny * (off - hw)),
             (p1[0] + nx * (off + hw), p1[1] + ny * (off + hw)), (p0[0] + nx * (off + hw), p0[1] + ny * (off + hw))]
        vis.poly([(x, y, h(x, y) + Z_PAINT) for x, y in q], mat, normal_hint=(0, 0, 1))
    for c, d, w in L["zebras"]:
        nx, ny = -d[1], d[0]
        n = max(2, int((w - 0.6) / 1.0))
        for k in range(n):
            v = -((n - 1) * 1.0) / 2 + k * 1.0
            q = []
            for du, dv in ((-1.5, v - 0.25), (1.5, v - 0.25), (1.5, v + 0.25), (-1.5, v + 0.25)):
                x, y = c[0] + d[0] * du + nx * dv, c[1] + d[1] * du + ny * dv
                q.append((x, y, h(x, y) + Z_PAINT))
            vis.poly(q, WHITE, normal_hint=(0, 0, 1))
    # bollards + chains
    for x, y in L["bollards"]:
        z = h(x, y)
        _pole(vis, x, y, z - 0.05, z + 0.8, 0.08, 0.07, BLACK)
    for p, q in L["chains"]:
        zp, zq = h(*p) + 0.62, h(*q) + 0.62
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        zm = (zp + zq) / 2 - 0.2
        _ribbon_v(vis, p, m, zp, zm, 0.035, BLACK)
        _ribbon_v(vis, m, q, zm, zq, 0.035, BLACK)
    # lamp posts: plinth, fluted pole, lantern (lit panes), pyramid cap
    for x, y in L["lamps"]:
        z = h(x, y)
        _pole(vis, x, y, z - 0.05, z + 0.6, 0.2, 0.16, BLACK)
        _pole(vis, x, y, z + 0.6, z + 4.0, 0.07, 0.06, BLACK, top=False)
        _pole(vis, x, y, z + 4.0, z + 4.15, 0.08, 0.16, BLACK, top=False)
        _pole(vis, x, y, z + 4.15, z + 4.7, 0.16, 0.22, WHITE, top=False)
        cap = [(x - 0.26, y - 0.26), (x + 0.26, y - 0.26), (x + 0.26, y + 0.26), (x - 0.26, y + 0.26)]
        for i in range(4):
            a, c = cap[i], cap[(i + 1) % 4]
            vis.poly([(a[0], a[1], z + 4.7), (c[0], c[1], z + 4.7), (x, y, z + 5.05)], BLACK)
        vis.poly([(px, py, z + 4.7) for px, py in reversed(cap)], BLACK)
    # bus shelters: posts, pitched roof (ridge along the road), bench
    for base, d, back in L["shelters"]:
        z = h(*base)

        def P(u, v, zz):
            return (base[0] + d[0] * u + back[0] * v, base[1] + d[1] * u + back[1] * v, z + zz)
        HL, D = 3.2, 2.4
        for u in (-HL + 0.2, HL - 0.2):
            for v in (0.25, D - 0.25):
                c = P(u, v, 0)
                _pole(vis, c[0], c[1], z - 0.05, z + 2.6, 0.06, 0.06, "metal_gray", top=False)
                _pole(col, c[0], c[1], z - 0.05, z + 2.5, 0.08, 0.08, "metal_gray", top=False)
        e0, e1, rz, ez = -0.3, D + 0.3, 3.15, 2.55
        front = [P(-HL, e0, ez), P(HL, e0, ez), P(HL, D / 2, rz), P(-HL, D / 2, rz)]
        rear = [P(HL, e1, ez), P(-HL, e1, ez), P(-HL, D / 2, rz), P(HL, D / 2, rz)]
        for f in (front, rear):
            vis.poly(f, "roof_dark", normal_hint=(0, 0, 1))
            vis.poly([(px, py, pz - 0.08) for px, py, pz in reversed(f)], "roof_dark", normal_hint=(0, 0, -1))
            col.poly(f, "roof_dark", normal_hint=(0, 0, 1))
        for u in (-HL, HL):
            g = [P(u, e0, ez - 0.08), P(u, e1, ez - 0.08), P(u, D / 2, rz)]
            vis.poly(g, "roof_dark")
            vis.poly(list(reversed(g)), "roof_dark")
        # bench (seat + back) along the rear posts
        seat = [P(-HL + 0.6, D - 0.85, 0), P(HL - 0.6, D - 0.85, 0), P(HL - 0.6, D - 0.4, 0), P(-HL + 0.6, D - 0.4, 0)]
        for bb in (vis, col):
            for i in range(4):
                a, c = seat[i], seat[(i + 1) % 4]
                bb.poly([(a[0], a[1], z - 0.05), (c[0], c[1], z - 0.05), (c[0], c[1], z + 0.45),
                         (a[0], a[1], z + 0.45)], "metal_gray")
            bb.poly([(px, py, z + 0.45) for px, py, _ in seat], "metal_gray", normal_hint=(0, 0, 1))
        bk = [P(-HL + 0.6, D - 0.4, 0.45), P(HL - 0.6, D - 0.4, 0.45), P(HL - 0.6, D - 0.36, 1.0),
              P(-HL + 0.6, D - 0.36, 1.0)]
        vis.poly(bk, "metal_gray")
        vis.poly(list(reversed(bk)), "metal_gray")
    # palms: tapered trunk + 7 drooping two-sided fronds
    for k, (x, y) in enumerate(L["palms"]):
        z = h(x, y)
        top = z + 7.0 + (k % 3) * 0.8
        _pole(vis, x, y, z - 0.1, top, 0.2, 0.13, "palm_trunk", top=False)
        for i in range(7):
            a = (i + 0.3 * (k % 2)) * 2 * math.pi / 7
            ca, sa = math.cos(a), math.sin(a)
            px, py = -sa, ca
            mid = (x + ca * 1.3, y + sa * 1.3)
            fr = [(x, y, top + 0.1), (mid[0] + px * 0.4, mid[1] + py * 0.4, top + 0.35),
                  (x + ca * 2.8, y + sa * 2.8, top - 1.0), (mid[0] - px * 0.4, mid[1] - py * 0.4, top + 0.35)]
            vis.poly(fr, "palm_frond")
            vis.poly(list(reversed(fr)), "palm_frond")
    # planting beds: mulch slab just under the collision floor, two ornamental-grass clumps and a shrub
    for k, (c, d, hl, hw) in enumerate(L["beds"]):
        nx, ny = -d[1], d[0]
        q = []
        for du, dv in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)):
            x, y = c[0] + d[0] * du + nx * dv, c[1] + d[1] * du + ny * dv
            q.append((x, y, h(x, y) - 0.008))
        vis.poly(q, "mulch", normal_hint=(0, 0, 1))
        for j, (du, dv) in enumerate(((-0.55, 0.1 * (1 if k % 2 else -1)), (0.5, -0.1 * (1 if k % 2 else -1)))):
            gx, gy = c[0] + d[0] * du + nx * dv, c[1] + d[1] * du + ny * dv
            gz = h(gx, gy) - 0.01
            ht = 0.75 + 0.15 * ((k + j) % 3)
            for a in (0.0, math.pi / 2):
                ca, sa = math.cos(a + 0.4 * j), math.sin(a + 0.4 * j)
                blade = [(gx - ca * 0.3, gy - sa * 0.3, gz), (gx + ca * 0.3, gy + sa * 0.3, gz),
                         (gx + ca * 0.45, gy + sa * 0.45, gz + ht), (gx - ca * 0.45, gy - sa * 0.45, gz + ht)]
                vis.poly(blade, "leaves_pine")
                vis.poly(list(reversed(blade)), "leaves_pine")
        if k % 2 == 0:
            sx, sy = c[0], c[1]
            sz = h(sx, sy) - 0.01
            vis.box(sx - 0.3, sy - 0.3, sz, sx + 0.3, sy + 0.3, sz + 0.45, "leaves_oak2")
    return vis, col


def assemble(ctx):
    site = Site(ctx["campus"])
    L = layout(site)
    vis, col = build_geometry(site, L, _height_fn())
    return site, L, vis, col


def build(ctx):
    _site, _L, vis, col = assemble(ctx)
    parts = []
    if vis.polys:
        me, slots = vis.build("reitz_streetscape visual")
        p = C.part("reitz_streetscape visual", me, slots, collision=False, visual=True)
        p["landmark"] = SLUG
        parts.append(p)
    if col.polys:
        me, slots = col.build("reitz_streetscape collision")
        p = C.part("reitz_streetscape collision", me, slots, collision=True, visual=False)
        p["landmark"] = SLUG
        parts.append(p)
    return parts


# ------------------------------------------------------------------ self-test (no Blender)
if __name__ == "__main__":
    import json
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
    campus = json.load(open(os.path.join(root, "data", "uf", "campus.json")))
    site, L, vis, col = assemble({"campus": campus, "stage_key": STAGE})
    print({k: len(v) for k, v in L.items()})
    print("roads:", sorted({r[1] for r in site.roads if any(_in_box(p, REGION) for p in r[4])}))
    print("junctions:", [tuple(round(c, 1) for c in j) for j, _ in site.junctions])
    print("shelters:", [tuple(round(c, 1) for c in s[0]) for s in L["shelters"]])
    print("palms:", [tuple(round(c, 1) for c in p) for p in L["palms"]])
    print("tris visual", vis.tri_count(), "collision", col.tri_count())
    named = [r[4] for r in site.roads]
    for q in L["lamps"] + L["palms"]:
        assert min(_poly_dist(q, pts) for pts in named) < 12.0, q
        assert not site.in_building(q), q
    for q in L["bollards"]:
        assert _poly_dist(q, site.by_id[SIDEWALK_ID][1]) < 2.0, q
    assert vis.tri_count() < 9000 and col.tri_count() <= 150
    assert len(L["shelters"]) == 2
    print("SELFTEST OK")
