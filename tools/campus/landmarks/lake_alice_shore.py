"""LAKE ALICE stage (course 3, slot jrb, stages.json key "lake_alice") shore landmarks: the UF bat barns,
the Baughman Center, the real boardwalks / overlook, the Museum Road lake edge and the bat-house field
(the stage's landing zone) with the Bat House Gardens. Hand-modelled for Super Gatorlator 64.

Landmark module (contract: tools/campus/landmarks/_common.py). Every LANDMARKS entry carries
"stages": ["lake_alice"], so only `build_stage.py lake_alice` builds it. Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower), placed on the OSM geometry in data/uf/campus.json (the
coordinates below are copied from it and re-checked against it at build time, warning on > 5 cm drift).
build(ctx) returns, per landmark, one visual mesh and one separate low-poly collision mesh (each part
carries "landmark": <slug>). Collision walls face out of their solids; every floor Mario is meant to walk
on is under 34 degrees; the Baughman nave roof (61 degrees) is a deliberate slide.

Not in this module (other Lake Alice tasks): the lake basin / water boxes / bog islands / cypress / lily
pads (lake_alice_water.py), a lake-centre observation deck for design act 1, the missions, lighting.
Lake surface: WATER_Z = -0.5 m, as lake_alice_water.py (whose bank stays at grade around the OSM ends of
the north boardwalk and the footbridge, its LANDINGS). Every deck here is >= 0.5 m above grade (1.0 m
above the water), every pile reaches 2.6 m below the water; any surface between -0.6 and 0.0 works.

1. BAT BARNS (slug "bat_barns"; replaces OSM w196848221, w424512419, w866087250)
  What the sources say (reviewed):
    - bats.ufl.edu: "The two bat houses and informational signage" are on the north side of Museum Road
      across from Lake Alice (Field & Fork Farm and Gardens); the colony (~450-500k Brazilian free-tailed
      bats) is the largest occupied bat-house colony in the world. A wooden fence marks the observation
      area; benches line the fence along Museum Road and stand across the street by the lake.
    - Florida Museum bat history (bats.ufl.edu/?p=2217): original Bat House built March 1991; bat barn
      built March 2010 (occupied Aug 2011); a second bat barn finished Feb 2017; Sept 2022 the bats were
      moved out of the original house ahead of Hurricane Ian and it was demolished. The museum's model
      page: the house was 35 ft tall x 16 ft across, on utility poles, open mesh-covered bottom
      (entrance), louvered vents, plywood roosting baffles.
    - Guinness World Records (2014): the house "consists of a single gabled roof, the base of which is
      situated twenty feet above the ground on five wood poles", 18 ft square, exterior plywood.
    - UF News 2011 (bat-cams): the barn has "a different roof style" (more flying room inside), better
      insulation; three bat-cams in and around the structures.
    - UF News 2022-08: three raised structures; the 2017 barn's slats were to be roughened, landing pads
      added, its exterior painted a darker colour, four smaller houses attached to its outside. WUFT
      2022-10-31: the oldest house torn down; the colony moved into the new barn. UF/IFAS Escambia blog
      2024: the oldest house removed before Ian, bats relocated to the other two, a rebuild "in the works".
    - OSM history: in 2020 a mapper named w424512419 "Bat House 1" (ref BAT1) and w196848221 "Bat House
      2" (UF ref 0084), then added w866087250 with its own fence (w866087251). All three carry
      colour=white, roof:colour=grey, material wood, support=pillar, height 9 (one tag set copied to all).
  Reading: w424512419 (6.0 x 6.9 m: an 18 ft body under a single gable whose ends overhang 0.7 m) is the
  1991 house, now GONE: its fenced plot is left empty. w196848221 is the 2010 Bat Barn: its 12-node
  cross-shaped outline is the plan of two intersecting gables (5.7 x 5.8 m body, each gable end
  overhangs ~0.65 m) - a CROSS-GABLED roof, the "different roof style" with a tall attic. w866087250
  (5.8 m square, traced as a plain square) is the 2017 barn: modelled with a hip roof over a 5.2 m body,
  painted darker (brown), with the four small add-on bat houses on its walls.
  Modelled as (both current barns, OSM height 9 m):
    - utility-pole legs (6 / 4, 0.34 m) with X bracing; body bottom 4.2 m (open, mesh-covered: dark),
      walls to the eave 7.1 / 7.2 m with a louvered vent band, ridge / apex 9.0 m (33 / 32 degrees,
      walkable); white walls + grey roof (2010), brown walls + galvanized roof (2017)
    - a bat-cam pole by each barn (metal pole, camera head), the black 2 m chain-link fences on their OSM
      rings (posts + rails; solid 0.3 m collision walls you can balance on), a gate in fence 1
  Gameplay:
    - climb a bat-cam pole (markers["poles"], 8.3 m) and jump from its top onto the roof (0.8 m away,
      1.2 m above the eave) -> red-coin / star spots on the roof peaks (spots barn2010_roof_peak,
      barn2017_roof_apex); the 2010 cross-gable has 4 gable arms to run round, the 2017 hip roof 4 faces
    - the open bottoms (spots *_bat_exit, 4.2 m) are where design act 4's Swoopers stream out at dusk
    - the 2 m fence tops are walkable (single wide rail), a double jump clears them

2. BAUGHMAN CENTER (slug "baughman_center"; replaces w425690658; draws the footbridge w427713653)
  What the sources say:
    - Wikipedia "Baughman Center"; UF News 2012-03; zonaarchitecture.com; Flickr "Baughman Center - Lake
      Alice Morning"; UF Performing Arts venue page: completed 2000, architect John Zona (contractor A.D.
      Morgan); nondenominational meditation pavilion, 96 fixed seats, ~1,500-2,000 sq ft, plus a 1,000
      sq ft admin building; inspired by E. Fay Jones's Thorncrown Chapel; "cathedral design with special
      steel and glass structure"; exterior walls of natural Florida cypress, stained and grooved
      vertically "to represent individual tree trunks"; roof of tongue-and-groove yellow pine and copper
      (medieval-cathedral materials); travertine floor, hardwood ceiling, soaring / floor-to-ceiling
      windows; a platform in front of a large picture window; layout "resembles medieval basilican
      cathedrals"; dominant axis on the summer-solstice sunrise / sunset ("a rising sun on the front and
      the setting sun on the back"); a bridge at the site. stages.json: steep gable roof, 12 m.
    - OSM w425690658 (25 nodes): long axis 71 degrees (ENE; solstice sunrise here ~63 degrees); a 10.3 m
      wide hall, a 6.3 m wide projection 2 m further east (chancel with chamfered corners), a stepped
      vestibule + entry porch on the west (main entrance node at the porch's west face), side doors on
      both long walls. It sits on the south bank of Lake Alice's western arm; the concrete footbridge
      w427713653 (2 m, lit, layer 1) spans that arm exactly between the lake ring's banks.
  Modelled as (basilica): a tall nave (6.36 m) running from the vestibule to the chancel under a steep
  copper (aged, bronze-brown) gable roof, eave 6.2 m, ridge 12.0 m (61 degrees); clerestory glass band
  (4.6-6.2 m) above lean-to aisle roofs (eave 3.4 m, 31 degrees); stained-cypress walls with
  floor-to-ceiling window bays; the east gable (the picture window behind the platform) and the west
  gable are glass with timber Gothic tracery (lancets inside a great pointed arch); flat-roofed vestibule
  (3.7 m) and a gabled entry porch (eave 2.9, ridge 3.95) with the main door; footbridge: concrete deck
  0.55 m (1.05 m over the water), ramps, dark timber railings, two lanterns. The interior is not modelled
  (closed). Seven generator wood-scatter trees that stood against its walls, in front of the picture
  window, on the footbridge ramp and on the lawn between the bridge and the chapel are removed
  ("removes_points"; the real chapel sits on an open lawn bank).
  Gameplay: entry-porch eave (2.9, double jump) -> up the porch roof (30 degrees) -> vestibule roof (3.7)
  -> either aisle roof (walk up to 4.6) -> run the aisle roofs to the lake-side east end (spot
  baughman_aisle_ne); the copper nave roof is a slide back down. The footbridge is a regatta launch
  candidate.

3. BOARDWALKS AND OVERLOOK (slug "lake_boardwalks"; draws w424512414 and w427905290)
    - North-shore boardwalk w424512414 (wood, layer 1, 10.2 m): on the informal lakeshore loop trail
      (w427713644/45) off Museum Road it crosses the mouth of a small inlet (the raw lake ring puts water
      under it). Modelled: 1.8 m deck at 0.5 m on piles, kick rails, ramps onto the trail, and a 3 x 1.6 m
      railed viewing bay on the lake side (spot census_boardwalk, regatta_launch_boardwalk,
      boardwalk_underside for act 6's red coin at the water under the deck).
    - East overlook: Wikipedia ("on the lake's northern side, a boardwalk runs through the woods and swamp
      to a viewing platform"); OSM boardwalk w427905290 (wood, "smoothness bad") from the University
      Gardens and viewpoint node n4270696932 37.5 m past its end. Modelled: the boardwalk continued to a
      5 x 5 m railed platform at the viewpoint (0.6 m) with steps down to the marsh; the boardwalk beyond
      the play zone (x > -1510) is visual only, clipped at the visual extent. Two scatter trees whose
      trunks stood 0.4 m from that boardwalk are removed.
    - No dock or pier exists on Lake Alice (a wildlife sanctuary: no fishing / boating); none is invented.

4. MUSEUM ROAD LAKE EDGE (slug "museum_road_edge")
    - Museum Road (w413487817, lit) runs along the lake's north-west shore with sidewalks both sides. On
      the lake side: 8 street lights (positions assumed, every 45 m; climbable poles), 4 "DANGER
      ALLIGATORS / wildlife sanctuary / no fishing / unlawful to feed alligators" signs (wording from the
      UF Facilities Lake Alice kiosk photo), 2 benches facing the lake (bats.ufl.edu), and the Lake Alice
      Conservation Area information kiosk at the lakeshore trail head (the UF kiosk exists; its "you are
      here" star is at the north-west shore; exact spot assumed; a scatter tree on that spot is removed).
      The RTS "UF Bat Houses" stop sign (n10726656195) by the bat-house parking.

5. BAT HOUSE FIELD + GARDENS (slug "bat_house_field"; landing zone)
    - "a field across from Lake Alice on Museum Road" (UF News 2011): the open lawn between the north
      sidewalk and the barn fences is the stage's landing zone (markers landing_zone_m, spots
      spawn_field / spawn_bus_stop). Dressing: the wooden observation fence (split rail, 1.1 m, a gap at
      the footway w866087252), the two OSM benches (n8072617244/5, facing 330) and the OSM wooden
      "Bat House" wildlife board (n4269007201, faces 225/45).
    - Bat House Gardens (w1493433580, educational garden): a timber arbor at its west entrance (top 2.6 m:
      design act 6's "garden trellis" red coin) and three raised beds (0.45 m) - gameplay additions in
      the garden's style, not mapped features.
    - Design act 4 census stations (spots census_houses / census_gardens / census_boardwalk) are 64, 95
      and 131 m apart, so one player cannot staff two.

Collision budget (stages.json): bat houses 3 x 60, Baughman 150, gardens 20 = 350 (+10 % = 385 before the
generator warns); the boardwalks, the road edge and the field dressing had no budget line, so the barns
and the chapel are kept lean. Measured (scratch build of lake_alice): collision 380 tris
(bat_barns 160, baughman_center 98, lake_boardwalks 62, museum_road_edge 16, bat_house_field 44), visual
~6,250 (1,650 / 1,060 / 1,680 / 830 / 1,040); validate_level jrb: 0 errors, 0 warnings; SM64 find_floor
probes of the exported collision: every spot, deck, ramp seam and roof floored.

Sources (reviewed)
  -https://bats.ufl.edu/ and https://bats.ufl.edu/?p=2291 (visiting), https://bats.ufl.edu/?p=2217 (history)
  - https://www.guinnessworldrecords.com/world-records/341449-most-populated-artificial-bat-roost
  - https://archive.news.ufl.edu/articles/2011/10/view-uf-bats-online-this-halloween-with-new-fla-museum-video-cameras.html
  - https://news.ufl.edu/2022/08/bat-house-renovation/
  - https://www.wuft.org/news/2022/10/31/bats-are-on-the-move-on-the-uf-campus/
  - https://blogs.ifas.ufl.edu/escambiaco/2024/07/31/weekly-what-is-it-uf-bat-houses/
  - https://en.wikipedia.org/wiki/Baughman_Center ; https://www.zonaarchitecture.com/thebaughmancenter
  - https://archive.news.ufl.edu/articles/2012/03/four-uf-buildings-nominated-for-no-1-building-in-florida-contest.html
  - https://www.flickr.com/photos/10326501@N02/2184640505/ ; https://performingarts.ufl.edu/venues/baughman-center/
  - https://en.wikipedia.org/wiki/Lake_Alice_(Gainesville,_Florida)
  - UF Facilities Services, Lake Alice kiosk (PDF):
    https://www.facilitiesservices.ufl.edu/wp-content/uploads/2022/10/Lake-Alice-kiosk_v5.pdf
  - OpenStreetMap (ODbL): ways 196848221, 424512419, 866087250 (+ histories), 424512410, 866087251,
    425690658, 427713653, 424512414, 427905290, 413487817, 427713658, 866087242, 866087252, 1493433580,
    relation 1630473 (outer way 45603512), nodes 4270696932, 4269007201, 8072617244, 8072617245, 10726656195
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

STAGES = ["lake_alice"]
WATER_Z = -0.5          # lake surface, as lake_alice_water.py WATER_Z (see the docstring)
PILE_Z = WATER_Z - 2.6  # piles / abutments reach this deep (visual)


# =================================================================== small helpers
def _r(p, nd=2):
    return tuple(round(float(c), nd) for c in p)


def _unit3(a):
    L = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return (a[0] / L, a[1] / L, a[2] / L)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _ngon(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n))
            for k in range(n)]


def _inside(pt, poly):
    x, y = pt
    ins = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            ins = not ins
    return ins


def _seg_dist(p, a, c):
    dx, dy = c[0] - a[0], c[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _poly_dist(p, pl):
    return min(_seg_dist(p, a, c) for a, c in zip(pl, pl[1:]))


class Frame:
    """Local frame: u along ang_deg (from east, counter-clockwise), v 90 degrees left of it."""

    def __init__(self, origin, ang_deg):
        self.o = (float(origin[0]), float(origin[1]))
        a = math.radians(ang_deg)
        self.u = (math.cos(a), math.sin(a))
        self.v = (-math.sin(a), math.cos(a))

    def p(self, u, v):
        return (self.o[0] + self.u[0] * u + self.v[0] * v, self.o[1] + self.u[1] * u + self.v[1] * v)

    def p3(self, u, v, z):
        x, y = self.p(u, v)
        return (x, y, z)

    def loc(self, x, y):
        dx, dy = x - self.o[0], y - self.o[1]
        return (dx * self.u[0] + dy * self.u[1], dx * self.v[0] + dy * self.v[1])


class Edge:
    """Vertical wall plane over a -> c; outward normal on the right (counter-clockwise footprints).
    Wall coordinates: t (0..L along a -> c), z up, off (+ = outward)."""

    def __init__(self, a, c):
        self.a = (float(a[0]), float(a[1]))
        self.c = (float(c[0]), float(c[1]))
        dx, dy = self.c[0] - self.a[0], self.c[1] - self.a[1]
        self.L = math.hypot(dx, dy)
        self.d = (dx / self.L, dy / self.L)
        self.n = (self.d[1], -self.d[0])

    def xy(self, t, off=0.0):
        return (self.a[0] + self.d[0] * t + self.n[0] * off, self.a[1] + self.d[1] * t + self.n[1] * off)

    def p(self, t, z, off=0.0):
        x, y = self.xy(t, off)
        return (x, y, z)

    def nh(self):
        return (self.n[0], self.n[1], 0.0)

    def panel(self, b, t0, t1, z0, z1, mat, off=0.03, uvs=None):
        if t1 - t0 < 1e-3 or z1 - z0 < 1e-3:
            return
        b.poly([self.p(t0, z0, off), self.p(t1, z0, off), self.p(t1, z1, off), self.p(t0, z1, off)], mat,
               uvs=uvs, normal_hint=self.nh())

    def strip(self, b, t0, z0, t1, z1, w, mat, off=0.05):
        """Thin strip in the wall plane from (t0, z0) to (t1, z1), width w (tracery, mullions)."""
        dt, dz = t1 - t0, z1 - z0
        L = math.hypot(dt, dz)
        if L < 1e-3:
            return
        pt, pz = -dz / L * w / 2, dt / L * w / 2
        q = [(t0 + pt, z0 + pz), (t0 - pt, z0 - pz), (t1 - pt, z1 - pz), (t1 + pt, z1 + pz)]
        b.poly([self.p(t, z, off) for t, z in q], mat, normal_hint=self.nh())

    def wall_to(self, b, z0, zf, mat, kinks=(), t0=0.0, t1=None, off=0.0):
        """Vertical face from z0 up to zf(x, y), piecewise linear between the kink parameters."""
        t1 = self.L if t1 is None else t1
        ts = [t0] + sorted(k for k in kinks if t0 + 1e-3 < k < t1 - 1e-3) + [t1]
        top = [self.p(t, zf(*self.xy(t)), off) for t in reversed(ts)]
        b.poly([self.p(t0, z0, off), self.p(t1, z0, off)] + top, mat, normal_hint=self.nh())


def _post(b, x, y, r, z0, z1, mat, n=6, top=None, rot=0.0):
    b.prism(_ngon(x, y, r, n, rot), z0, z1, mat, top=top)


def _beam(b, p0, p1, w, h, mat, caps=False):
    """Rectangular beam (w wide, h deep) from p0 to p1 (3D); 4 sides (+ end caps)."""
    d = _unit3((p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]))
    ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    s = _unit3(_cross(d, ref))
    t = _cross(s, d)
    sig = ((1, 1), (-1, 1), (-1, -1), (1, -1))

    def c(p, k):
        a, bb = sig[k]
        return tuple(p[i] + s[i] * a * w / 2 + t[i] * bb * h / 2 for i in range(3))

    for k in range(4):
        j = (k + 1) % 4
        nh = tuple(s[i] * (sig[k][0] + sig[j][0]) + t[i] * (sig[k][1] + sig[j][1]) for i in range(3))
        b.poly([c(p0, k), c(p1, k), c(p1, j), c(p0, j)], mat, normal_hint=nh)
    if caps:
        b.poly([c(p0, k) for k in range(4)], mat, normal_hint=(-d[0], -d[1], -d[2]))
        b.poly([c(p1, k) for k in range(4)], mat, normal_hint=d)


def _beam_split(b, p0, p1, w, h, mat, max_len=10.0):
    """_beam in pieces of at most max_len (keeps texture repeats per face low)."""
    L = math.dist(p0, p1)
    n = max(1, int(math.ceil(L / max_len)))
    for k in range(n):
        a = tuple(p0[i] + (p1[i] - p0[i]) * k / n for i in range(3))
        c = tuple(p0[i] + (p1[i] - p0[i]) * (k + 1) / n for i in range(3))
        _beam(b, a, c, w, h, mat)


def _roof_uvs(quad, tile=3.0):
    """UVs for a roof quad [ridge a, ridge b, eave b, eave a]: one repeat per `tile` metres along the ridge
    and down the slope (projected UVs would repeat the 1 m bronze texture 20x across the nave roof)."""
    L = math.dist(quad[0], quad[1]) / tile
    S = math.dist(quad[0], quad[3]) / tile
    return [(0.0, S), (L, S), (L, 0.0), (0.0, 0.0)]


def _flat(b, ring, z, mat, up=True, uvs=None):
    pts = C.ccw(list(ring))
    if not up:
        pts = list(reversed(pts))
    b.poly([(x, y, z) for x, y in pts], mat, uvs=uvs, normal_hint=(0.0, 0.0, 1.0 if up else -1.0))


def _line_box(b, a, c, w, z0, z1, mat, top=None, end_a=True, end_c=True, ext=0.0):
    """Solid strip along a -> c (fence / rail / board): w thick, z0..z1, outward walls; ext lengthens
    the ends (a number, or (ext_a, ext_c)); chained / closed strips overlap at their corners, so only
    free ends need end walls."""
    E = Edge(a, c)
    hw = w / 2
    ext_a, ext_c = ext if isinstance(ext, tuple) else (ext, ext)
    t0, t1 = -ext_a, E.L + ext_c
    Ra, Rc, La, Lc = E.xy(t0, hw), E.xy(t1, hw), E.xy(t0, -hw), E.xy(t1, -hw)
    b.quad_wall(Ra, Rc, z0, z1, mat)          # right side (outward +n)
    b.quad_wall(Lc, La, z0, z1, mat)          # left side (outward -n)
    if end_c:
        b.quad_wall(Rc, Lc, z0, z1, mat)      # faces +d
    if end_a:
        b.quad_wall(La, Ra, z0, z1, mat)      # faces -d
    if top:
        _flat(b, [Ra, Rc, Lc, La], z1, top)


def _offset_polyline(pts, off):
    """Offset an open polyline sideways (off > 0 = right of travel), mitred corners."""
    out = []
    n = len(pts)
    for i in range(n):
        if i == 0:
            E = Edge(pts[0], pts[1])
            out.append(E.xy(0.0, off))
            continue
        if i == n - 1:
            E = Edge(pts[-2], pts[-1])
            out.append(E.xy(E.L, off))
            continue
        E0, E1 = Edge(pts[i - 1], pts[i]), Edge(pts[i], pts[i + 1])
        mx, my = E0.n[0] + E1.n[0], E0.n[1] + E1.n[1]
        m = math.hypot(mx, my)
        mx, my = mx / m, my / m
        cosh = mx * E0.n[0] + my * E0.n[1]
        k = off / max(cosh, 0.3)
        out.append((pts[i][0] + mx * k, pts[i][1] + my * k))
    return out


def _cum(pts):
    s = [0.0]
    for a, c in zip(pts, pts[1:]):
        s.append(s[-1] + math.dist(a, c))
    return s


def _at(pts, s):
    """(point, unit tangent) at arc length s along a polyline."""
    cs = _cum(pts)
    s = max(0.0, min(cs[-1], s))
    for i in range(len(pts) - 1):
        if s <= cs[i + 1] + 1e-9:
            L = cs[i + 1] - cs[i]
            t = 0.0 if L < 1e-9 else (s - cs[i]) / L
            a, c = pts[i], pts[i + 1]
            return (a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t), ((c[0] - a[0]) / L, (c[1] - a[1]) / L)
    a, c = pts[-2], pts[-1]
    L = math.dist(a, c)
    return c, ((c[0] - a[0]) / L, (c[1] - a[1]) / L)


def _sub(pts, s0, s1):
    """Sub-polyline between arc lengths s0 < s1."""
    cs = _cum(pts)
    out = [_at(pts, s0)[0]]
    for p, s in zip(pts, cs):
        if s0 + 1e-6 < s < s1 - 1e-6:
            out.append(p)
    out.append(_at(pts, s1)[0])
    return out


def _bench(vis, col, x, y, facing_deg, length=1.8):
    """Park bench, wooden slats on dark legs; seat 0.46 m. Collision: the seat top only (a walk-up
    step: SM64's find_floor reaches 78 units above Mario)."""
    f = math.radians(facing_deg)
    fx, fy = math.sin(f), math.cos(f)              # facing direction (compass)
    F = Frame((x, y), math.degrees(math.atan2(fy, fx)) - 90.0)   # u along the bench, v = facing
    hl = length / 2
    vis.prism([F.p(-hl, -0.22), F.p(hl, -0.22), F.p(hl, 0.24), F.p(-hl, 0.24)], 0.40, 0.46, "door_wood",
              top="door_wood", bottom="door_wood")
    vis.prism([F.p(-hl, -0.30), F.p(hl, -0.30), F.p(hl, -0.24), F.p(-hl, -0.24)], 0.55, 0.90, "door_wood",
              top="door_wood")
    for u in (-hl + 0.12, hl - 0.12):
        vis.prism([F.p(u - 0.04, -0.26), F.p(u + 0.04, -0.26), F.p(u + 0.04, 0.2), F.p(u - 0.04, 0.2)], 0.0, 0.40,
                  "dark_trim")
        vis.prism([F.p(u - 0.04, -0.30), F.p(u + 0.04, -0.30), F.p(u + 0.04, -0.24), F.p(u - 0.04, -0.24)], 0.40,
                  0.90, "dark_trim")
    _flat(col, [F.p(-hl, -0.24), F.p(hl, -0.24), F.p(hl, 0.24), F.p(-hl, 0.24)], 0.46, "door_wood")
    return F.p3(0.0, 0.0, 0.46)


# =================================================================== OSM data (copied from campus.json)
BARN10_ID = "w196848221"      # 2010 Bat Barn ("Bat House 2", UF ref 0084)
OLD_HOUSE_ID = "w424512419"   # original 1991 Bat House ("Bat House 1", BAT1): demolished Sept 2022
BARN17_ID = "w866087250"      # 2017 Bat Barn
FENCE1_ID, FENCE2_ID = "w424512410", "w866087251"
BAUGHMAN_ID = "w425690658"
GARDEN_ID = "w1493433580"
BRIDGE_ID, BW_NORTH_ID, BW_EAST_ID = "w427713653", "w424512414", "w427905290"

BARN10_OSM = [(-1886.18, -507.79), (-1885.9, -513.65), (-1885.26, -513.61), (-1885.23, -514.25), (-1879.48, -513.98),
              (-1879.51, -513.36), (-1878.96, -513.34), (-1879.22, -507.61), (-1879.87, -507.65), (-1879.91, -506.88),
              (-1885.51, -507.14), (-1885.48, -507.76)]
OLD_HOUSE_OSM = [(-1898.99, -508.19), (-1898.6, -515.11), (-1892.62, -514.77), (-1893.02, -507.86)]
BARN17_OSM = [(-1911.97, -500.01), (-1911.62, -505.76), (-1905.84, -505.41), (-1906.19, -499.67)]
FENCE1 = [(-1900.29, -505.93), (-1877.97, -504.73), (-1877.19, -514.97), (-1899.51, -516.15)]
FENCE2 = [(-1913.96, -497.21), (-1901.14, -496.42), (-1900.29, -505.93), (-1913.25, -507.05)]
BAUGHMAN_OSM = [(-1951.65, -726.21), (-1951.23, -727.66), (-1949.91, -727.38), (-1949.27, -727.79), (-1947.56, -732.45),
                (-1947.99, -733.17), (-1949.2, -733.69), (-1948.69, -734.89), (-1948.99, -735.58), (-1953.95, -737.18),
                (-1965.89, -741.46), (-1966.63, -739.87), (-1967.18, -740.07), (-1968.59, -739.88), (-1968.91, -738.98),
                (-1970.04, -739.32), (-1970.62, -737.6), (-1971.19, -735.97), (-1969.87, -735.54), (-1970.15, -734.36),
                (-1969.4, -733.26), (-1968.65, -733.08), (-1969.13, -731.53), (-1957.14, -727.74), (-1952.51, -725.97)]
GARDEN = [(-1862.09, -467.78), (-1817.02, -466.94), (-1816.57, -491.16), (-1861.63, -492.01)]
BRIDGE = [(-1966.35, -708.85), (-1962.91, -716.68)]                 # OSM order: north -> south
BW_NORTH = [(-1847.67, -611.45), (-1838.92, -606.13)]
BW_EAST = [(-1412.68, -557.9), (-1434.63, -569.43), (-1446.4, -576.68), (-1460.2, -584.83), (-1470.86, -588.15),
           (-1485.96, -600.43)]
VIEWPOINT = (-1512.74, -626.7)                                     # n4270696932 tourism=viewpoint
MUSEUM_RD = [(-1702.79, -445.53), (-1727.96, -458.99), (-1738.23, -465.37), (-1749.15, -472.8), (-1792.71, -503.31),
             (-1795.47, -505.3), (-1848.73, -543.72), (-1879.37, -564.92), (-1882.91, -567.36), (-1897.65, -577.8),
             (-1922.51, -595.17), (-1929.44, -599.98), (-1935.31, -604.53), (-1943.97, -611.84), (-1949.59, -616.88),
             (-1955.65, -622.84), (-1961.56, -629.09), (-1967.52, -635.91), (-1975.24, -645.24), (-1979.95, -651.74),
             (-1984.84, -658.84), (-1988.12, -664.16), (-1991.97, -670.72), (-1995.38, -677.12)]
SIDEWALK_LAKE = [(-1747.36, -484.98), (-1835.79, -548.26), (-1873.18, -573.98), (-1880.74, -577.28),
                 (-1892.49, -585.27), (-1905.53, -594.14), (-1913.36, -601.52), (-1922.1, -607.45),
                 (-1927.74, -611.5), (-1933.93, -616.08), (-1942.02, -622.57), (-1949.04, -629.42),
                 (-1958.75, -639.02), (-1964.94, -644.65), (-1970.91, -653.11), (-1978.63, -665.58),
                 (-1984.52, -673.98), (-1989.52, -681.39), (-2002.41, -705.72)]
SIDEWALK_NORTH = [(-1799.09, -500.21), (-1839.86, -529.17), (-1864.26, -546.52), (-1871.36, -549.43),
                  (-1885.51, -555.23), (-1927.1, -582.79)]
TRAIL_HEAD = [(-1892.49, -585.27), (-1881.48, -587.41)]            # first leg of trail w427713645
INFO_BOARD = (-1881.14, -555.52)                                  # n4269007201, wooden, faces 225;45
BENCHES_OSM = [(-1886.48, -557.71), (-1888.29, -558.96)]          # n8072617244/5, facing 330
BUS_STOP = (-1970.6, -627.88)                                     # n10726656195 "UF Bat Houses" (RTS 0801)
FOOTWAY_FIELD = (-1871.36, -549.43)                               # w866087252 start (into the field)
PLAY_XMAX = -1510.0                                               # stages.json play_bounds_m
# generator wood-scatter trees (stage_data ids "<wood relation>#<k>", woods relation 6819273 round the lake)
# that would stand on / against this module's geometry (measured on a scratch build)
CLEAR_TREES_BC = ["rel6819273#596",     # 1.4 m in front of the Baughman picture window
                  "rel6819273#1350", "rel6819273#2233", "rel6819273#4130",   # < 4 m from its walls
                  "rel6819273#89",      # on the footbridge's north ramp
                  "rel6819273#4028", "rel6819273#165"]   # on the lawn between the footbridge and the chapel
CLEAR_TREES_BW = ["rel6819273#2800", "rel6819273#4076"]   # trunks 0.4 m from the east overlook boardwalk
CLEAR_TREES_ROAD = ["rel6819273#303"]                       # inside the lakeshore kiosk
VIS_XMAX = -1760.0 + 323.0                                        # visual extent (centre + 324 m, less margin)


# =================================================================== 1. bat barns
SLUG_BATS = "bat_barns"
B10 = {"o": (-1882.565, -510.563), "ang": 2.707, "hu": 2.84, "hv": 2.89, "UA": 3.475, "VB": 3.557,
       "zb": 4.2, "ze": 7.1, "zr": 9.0}
B17 = {"o": (-1908.905, -502.711), "ang": 3.451, "ru": 2.897, "rv": 2.88, "hb": 2.6,
       "zb": 4.2, "ze": 7.2, "zr": 9.0}
OLD_HOUSE_C = (-1895.806, -511.481)
CAM_H = 8.3                                       # bat-cam pole height (pole object)
CAM10_UV = (3.55, -3.62)                          # outside the 2010 barn's SE notch
CAM17_UV = (3.55, 1.6)                            # east of the 2017 barn, clear of the add-on box
ADDON_Z = (4.5, 5.4, 5.48)                        # 2017 add-on bat houses: bottom, top, cap top
FENCE_H = 2.0
FENCE_COL_W = 0.3


def _b10_frame():
    return Frame(B10["o"], B10["ang"])


def _b17_frame():
    return Frame(B17["o"], B17["ang"])


def _b10_zA(v):
    return B10["zr"] - (B10["zr"] - B10["ze"]) * abs(v) / B10["hv"]


def _b10_zB(u):
    return B10["zr"] - (B10["zr"] - B10["ze"]) * abs(u) / B10["hu"]


def _b17_roof(u, v):
    k = (B17["zr"] - B17["ze"])
    return B17["zr"] - k * max(abs(u) / B17["ru"], abs(v) / B17["rv"])


def _legs(vis, col, F, posts, zb, r=0.17):
    for u, v in posts:
        x, y = F.p(u, v)
        _post(vis, x, y, r, -0.1, zb + 0.05, "dark_trim", n=8)
        _post(col, x, y, r * 1.6, 0.0, zb, "dark_trim", n=3, rot=math.radians(B10["ang"]) + 0.5)
    # X bracing between the outer posts on all four sides of the leg frame
    us = sorted({u for u, _ in posts})
    vs = sorted({v for _, v in posts})
    z0, z1 = 0.9, zb - 0.35
    for v in (vs[0], vs[-1]):
        off = -0.2 if v < 0 else 0.2
        for ua, ub in zip(us, us[1:]):
            _beam(vis, F.p3(ua, v + off, z0), F.p3(ub, v + off, z1), 0.06, 0.16, "door_wood")
            _beam(vis, F.p3(ua, v + off * 1.5, z1), F.p3(ub, v + off * 1.5, z0), 0.06, 0.16, "door_wood")
    for u in (us[0], us[-1]):
        off = -0.2 if u < 0 else 0.2
        _beam(vis, F.p3(u + off, vs[0], z0), F.p3(u + off, vs[-1], z1), 0.06, 0.16, "door_wood")
        _beam(vis, F.p3(u + off * 1.5, vs[0], z1), F.p3(u + off * 1.5, vs[-1], z0), 0.06, 0.16, "door_wood")


def _bat_cam(vis, F, uv, target_uv):
    x, y = F.p(*uv)
    _post(vis, x, y, 0.09, -0.1, CAM_H, "metal_gray", n=6, top="metal_gray")
    tx, ty = F.p(*target_uv)
    d = math.atan2(ty - y, tx - x)
    G = Frame((x, y), math.degrees(d))
    vis.prism([G.p(-0.05, -0.13), G.p(0.42, -0.13), G.p(0.42, 0.13), G.p(-0.05, 0.13)], CAM_H - 0.55, CAM_H - 0.25,
              "dark_trim", top="dark_trim", bottom="dark_trim")       # camera housing
    vis.prism([G.p(0.42, -0.09), G.p(0.48, -0.09), G.p(0.48, 0.09), G.p(0.42, 0.09)], CAM_H - 0.5, CAM_H - 0.3,
              "window_dark", top="dark_trim")                         # lens
    vis.prism([G.p(-0.02, -0.18), G.p(0.22, -0.18), G.p(0.22, 0.18), G.p(-0.02, 0.18)], CAM_H - 0.85, CAM_H - 0.62,
              "white_trim", top="white_trim", bottom="white_trim")    # IR lamp
    return (x, y)


def _louvers(vis, E, ze, wall_mat):
    """Vent band under the eave: dark band with two light slat lines."""
    E.panel(vis, 0.35, E.L - 0.35, ze - 0.75, ze - 0.2, "dark_trim", off=0.03)
    for z in (ze - 0.6, ze - 0.4):
        E.panel(vis, 0.35, E.L - 0.35, z, z + 0.05, wall_mat, off=0.045)


def _build_barn10(vis, col):
    F = _b10_frame()
    hu, hv, UA, VB, zb, ze, zr = (B10[k] for k in ("hu", "hv", "UA", "VB", "zb", "ze", "zr"))
    body = [F.p(-hu, -hv), F.p(hu, -hv), F.p(hu, hv), F.p(-hu, hv)]      # counter-clockwise

    def zroof(x, y):
        u, v = F.loc(x, y)
        return max(_b10_zA(v), _b10_zB(u))

    for i in range(4):
        E = Edge(body[i], body[(i + 1) % 4])
        E.wall_to(vis, zb, zroof, "white_trim", kinks=(E.L / 2,))
        E.wall_to(col, zb, zroof, "white_trim", kinks=(E.L / 2,))
        E.panel(vis, 0.0, E.L, zb, zb + 0.25, "dark_trim", off=0.03)          # skirt board
        for t in (0.0, E.L):                                                   # corner boards
            E.panel(vis, max(0.0, t - 0.12), min(E.L, t + 0.12), zb + 0.25, ze, "white_trim", off=0.05)
        _louvers(vis, E, ze, "white_trim")
        E.panel(vis, E.L / 2 - 0.35, E.L / 2 + 0.35, ze + 0.25, ze + 0.85, "dark_trim", off=0.03)  # gable vent
    # open, mesh-covered bottom (the bats' entrance)
    _flat(vis, body, zb, "window_dark", up=False)
    _flat(col, body, zb, "white_trim", up=False)
    # cross-gabled roof: 8 planar quads (roof A ridge along u, roof B ridge along v), drawn twice:
    # top (roof_dark) and a soffit 0.12 m lower facing down for the overhanging gable arms
    quads = []
    for su in (1, -1):
        for sv in (1, -1):
            quads.append([(0, 0, zr), (su * UA, 0, zr), (su * UA, sv * hv, ze), (su * hu, sv * hv, ze)])   # roof A
            quads.append([(0, 0, zr), (su * hu, sv * hv, ze), (su * hu, sv * VB, ze), (0, sv * VB, zr)])   # roof B
    for q in quads:
        pts = [F.p3(u, v, z) for u, v, z in q]
        vis.poly(pts, "roof_dark", normal_hint=(0.0, 0.0, 1.0))
        col.poly(pts, "roof_dark", normal_hint=(0.0, 0.0, 1.0))
    # soffits under the four overhanging gable arms (outside the body: roof A beyond |u| = hu, roof B
    # beyond |v| = hv), 0.12 m under the roof, facing down
    for su in (1, -1):
        for sv in (1, -1):
            arm_a = [(su * hu, 0, zr), (su * UA, 0, zr), (su * UA, sv * hv, ze), (su * hu, sv * hv, ze)]
            arm_b = [(0, sv * hv, zr), (su * hu, sv * hv, ze), (su * hu, sv * VB, ze), (0, sv * VB, zr)]
            for arm in (arm_a, arm_b):
                vis.poly([F.p3(u, v, z - 0.12) for u, v, z in arm], "white_trim", normal_hint=(0.0, 0.0, -1.0))
    # bargeboards along the four gable ends (rakes) + eave fascia on the arms
    for su in (1, -1):
        for sv in (1, -1):
            _beam(vis, F.p3(su * UA, 0, zr - 0.03), F.p3(su * UA, sv * hv, ze - 0.03), 0.06, 0.24, "white_trim")
            _beam(vis, F.p3(0, sv * VB, zr - 0.03), F.p3(su * hu, sv * VB, ze - 0.03), 0.06, 0.24, "white_trim")
    _beam(vis, F.p3(-UA, 0, zr + 0.04), F.p3(UA, 0, zr + 0.04), 0.18, 0.1, "dark_trim")       # ridge caps
    _beam(vis, F.p3(0, -VB, zr + 0.03), F.p3(0, VB, zr + 0.03), 0.18, 0.1, "dark_trim")
    posts = [(u, v) for u in (-2.45, 0.0, 2.45) for v in (-2.5, 2.5)]
    _legs(vis, col, F, posts, zb)
    cam = _bat_cam(vis, F, CAM10_UV, (0.0, 0.0))
    return F, cam


def _build_barn17(vis, col):
    F = _b17_frame()
    ru, rv, hb, zb, ze, zr = (B17[k] for k in ("ru", "rv", "hb", "zb", "ze", "zr"))
    body = [F.p(-hb, -hb), F.p(hb, -hb), F.p(hb, hb), F.p(-hb, hb)]
    ztop = _b17_roof(hb, 0.0)
    for i in range(4):
        E = Edge(body[i], body[(i + 1) % 4])
        E.wall_to(vis, zb, lambda x, y: ztop, "door_wood")
        E.wall_to(col, zb, lambda x, y: ztop, "door_wood")
        E.panel(vis, 0.0, E.L, zb, zb + 0.25, "dark_trim", off=0.03)
        _louvers(vis, E, ztop - 0.1, "white_trim")
        # one of the four small add-on bat houses (UF News 2022) on each wall: 0.7 x 0.3 x 0.9 m
        t0, t1 = E.L / 2 - 0.35, E.L / 2 + 0.35
        box = [E.xy(t0, 0.0), E.xy(t1, 0.0), E.xy(t1, 0.3), E.xy(t0, 0.3)]
        vis.prism(box, ADDON_Z[0], ADDON_Z[1], "white_trim", bottom="dark_trim")
        cap = [E.xy(t0 - 0.06, -0.02), E.xy(t1 + 0.06, -0.02), E.xy(t1 + 0.06, 0.38), E.xy(t0 - 0.06, 0.38)]
        vis.prism(cap, ADDON_Z[1], ADDON_Z[2], "roof_dark", top="roof_dark", bottom="roof_dark")
        _flat(col, cap, ADDON_Z[2], "roof_dark")
        # landing pad (2022): a dark board under the opening
    _flat(vis, body, zb, "window_dark", up=False)
    _flat(col, body, zb, "door_wood", up=False)
    for pad in ((-1.4, -0.6), (0.6, 1.4)):
        vis.poly([F.p3(pad[0], -1.8, zb - 0.02), F.p3(pad[1], -1.8, zb - 0.02), F.p3(pad[1], -1.4, zb - 0.9),
                  F.p3(pad[0], -1.4, zb - 0.9)], "dark_trim", normal_hint=(0.0, -0.6, -0.8))
        vis.poly([F.p3(pad[0], -1.4, zb - 0.9), F.p3(pad[1], -1.4, zb - 0.9), F.p3(pad[1], -1.8, zb - 0.02),
                  F.p3(pad[0], -1.8, zb - 0.02)], "dark_trim", normal_hint=(0.0, 0.6, 0.8))
    # hip roof (4 triangles to the apex) + soffit ring
    eave = [(-ru, -rv), (ru, -rv), (ru, rv), (-ru, rv)]
    for i in range(4):
        (u0, v0), (u1, v1) = eave[i], eave[(i + 1) % 4]
        tri = [F.p3(u0, v0, ze), F.p3(u1, v1, ze), F.p3(0.0, 0.0, zr)]
        vis.poly(tri, "metal_gray", normal_hint=(0.0, 0.0, 1.0))
        col.poly(tri, "metal_gray", normal_hint=(0.0, 0.0, 1.0))
        a, c = F.p(u0, v0), F.p(u1, v1)
        Ea = Edge(a, c)
        Ea.panel(vis, 0.0, Ea.L, ze - 0.2, ze, "white_trim", off=0.0)              # fascia
        sof = [F.p3(u0, v0, ze - 0.02), F.p3(u1, v1, ze - 0.02),
               F.p3(u1 * hb / ru, v1 * hb / rv, ztop - 0.02), F.p3(u0 * hb / ru, v0 * hb / rv, ztop - 0.02)]
        vis.poly(sof, "white_trim", normal_hint=(0.0, 0.0, -1.0))
    for u, v in eave:                                                                  # hip caps
        _beam(vis, F.p3(u, v, ze + 0.05), F.p3(0.0, 0.0, zr + 0.05), 0.14, 0.08, "dark_trim")
    posts = [(u, v) for u in (-2.2, 2.2) for v in (-2.2, 2.2)]
    _legs(vis, col, F, posts, zb)
    cam = _bat_cam(vis, F, CAM17_UV, (0.0, 0.0))
    return F, cam


def _chainlink(vis, col, ring, gate=None):
    """Black chain-link fence (OSM height 2 m) on a closed ring: posts, top / bottom rails; collision: a
    0.3 m solid wall per side (thick enough that a fast Mario cannot pass through) with a walkable top."""
    n = len(ring)
    for i in range(n):
        a, c = ring[i], ring[(i + 1) % n]
        E = Edge(a, c)
        k = max(1, int(math.ceil(E.L / 3.0)))
        for j in range(k + 1):
            x, y = E.xy(E.L * j / k)
            _post(vis, x, y, 0.045, -0.1, FENCE_H + 0.05, "dark_trim", n=4, rot=math.pi / 4)
        for z, w in ((FENCE_H - 0.02, 0.06), (0.12, 0.04), (1.05, 0.025)):
            _beam_split(vis, (a[0], a[1], z), (c[0], c[1], z), w, w, "dark_trim")
        _line_box(col, a, c, FENCE_COL_W, 0.0, FENCE_H, "dark_trim", top="dark_trim", end_a=False, end_c=False,
                  ext=FENCE_COL_W / 2)
    if gate:
        a, c, t0, t1 = gate
        E = Edge(a, c)
        for t in (t0, (t0 + t1) / 2, t1):
            x, y = E.xy(t)
            _post(vis, x, y, 0.06, -0.1, FENCE_H + 0.1, "dark_trim", n=4, rot=math.pi / 4)
        for ta, tb in ((t0, (t0 + t1) / 2), ((t0 + t1) / 2, t1)):
            _beam(vis, E.p(ta + 0.08, 0.25, 0.06), E.p(tb - 0.08, FENCE_H - 0.2, 0.06), 0.04, 0.04, "dark_trim")
            _beam(vis, E.p(ta + 0.08, FENCE_H - 0.2, 0.06), E.p(tb - 0.08, FENCE_H - 0.2, 0.06), 0.05, 0.05,
                  "dark_trim")
            _beam(vis, E.p(ta + 0.08, 0.25, 0.06), E.p(tb - 0.08, 0.25, 0.06), 0.05, 0.05, "dark_trim")


def _bats_layout():
    F10, F17 = _b10_frame(), _b17_frame()
    peak10 = F10.p3(0.0, 0.0, B10["zr"])
    spots = {
        "barn2010_roof_peak": _r(peak10),
        "barn2010_roof_east_arm": _r(F10.p3(3.0, 1.2, _b10_zA(1.2))),
        "barn2010_roof_south_arm": _r(F10.p3(-1.2, -3.1, _b10_zB(-1.2))),
        "barn2010_bat_exit": _r(F10.p3(0.0, 0.0, B10["zb"] - 0.05)),
        "barn2010_batcam_top": _r(F10.p3(*CAM10_UV, CAM_H)),
        "barn2017_roof_apex": _r(F17.p3(0.0, 0.0, B17["zr"])),
        "barn2017_roof_east": _r(F17.p3(1.8, 0.0, _b17_roof(1.8, 0.0))),
        "barn2017_bat_exit": _r(F17.p3(0.0, 0.0, B17["zb"] - 0.05)),
        "barn2017_batcam_top": _r(F17.p3(*CAM17_UV, CAM_H)),
        "barn2017_addon_box_east": _r((*Edge(F17.p(B17["hb"], -B17["hb"]), F17.p(B17["hb"], B17["hb"])).xy(
            B17["hb"], 0.15), ADDON_Z[2])),
        "old_house_site": _r((*OLD_HOUSE_C, 0.0)),
        "fence1_top_south": _r((*Edge(FENCE1[2], FENCE1[3]).xy(6.0), FENCE_H)),
    }
    cam10, cam17 = F10.p(*CAM10_UV), F17.p(*CAM17_UV)
    markers = {
        "poles": [
            {"name": "bat_cam_2010", "base_m": _r((*cam10, 0.0)), "height_m": CAM_H,
             "note": "bat-cam pole outside the 2010 barn's south-east notch (inside fence 1): climb to 8.3, "
                     "jump north-west onto the cross-gable roof (eave 7.1, peak 9.0)"},
            {"name": "bat_cam_2017", "base_m": _r((*cam17, 0.0)), "height_m": CAM_H,
             "note": "bat-cam pole 0.65 m east of the 2017 barn's eave (inside fence 2): climb, jump west "
                     "onto the hip roof (eave 7.2, apex 9.0); the east add-on box (5.48) is a perch below"},
        ],
        "bat_exits_m": [_r(F10.p3(0.0, 0.0, B10["zb"])), _r(F17.p3(0.0, 0.0, B17["zb"]))],
        "barns": {
            "barn_2010": {"osm_id": BARN10_ID, "built": 2010, "body_bottom_m": B10["zb"], "eave_m": B10["ze"],
                          "ridge_m": B10["zr"], "roof": "cross-gable, 33 deg", "center_m": _r(B10["o"])},
            "barn_2017": {"osm_id": BARN17_ID, "built": 2017, "body_bottom_m": B17["zb"], "eave_m": B17["ze"],
                          "ridge_m": B17["zr"], "roof": "hip, 32 deg", "center_m": _r(B17["o"])},
            "house_1991": {"osm_id": OLD_HOUSE_ID, "built": 1991, "demolished": "2022-09",
                           "center_m": _r(OLD_HOUSE_C), "note": "not built: empty fenced plot"},
        },
        "fences_m": {"fence1": [_r(p) for p in FENCE1], "fence2": [_r(p) for p in FENCE2], "height_m": FENCE_H},
    }
    return {"spots": spots, "markers": markers}


def _build_bats(ctx):
    vis, col = C.Builder(), C.Builder()
    _build_barn10(vis, col)
    _build_barn17(vis, col)
    _chainlink(vis, col, FENCE1, gate=(FENCE1[2], FENCE1[3], 8.0, 11.0))
    _chainlink(vis, col, FENCE2)
    return _parts(SLUG_BATS, vis, col)


# =================================================================== 2. Baughman Center
SLUG_BC = "baughman_center"
BF = Frame((-1960.1736, -734.0252), 18.7554)       # u: long axis (71.2 deg compass, ENE), v: NNW
BC_VC = -0.03                                      # nave centre line (v)
BC_NHW = 3.18                                      # nave half width
BC_U0, BC_U1 = -8.55, 12.45                        # nave west gable / chancel east face
Z_AISLE, Z_CLR, Z_EAVE, Z_RIDGE = 3.4, 4.6, 6.2, 12.0
Z_VEST, Z_PORCH_E, Z_PORCH_R = 3.7, 2.9, 3.95
K_NAVE = (Z_RIDGE - Z_EAVE) / BC_NHW
K_AISLE = 0.6                                      # aisle roof slope (31 deg)
BC_L = [BF.loc(*p) for p in BAUGHMAN_OSM]          # OSM nodes in the local frame
BC_PORCH_VC = (BC_L[17][1] + BC_L[14][1]) / 2
BR_DECK_Z = 0.55


def _bc_nave_z(u, v):
    return Z_RIDGE - K_NAVE * abs(v - BC_VC)


def _bc_aisle_z(u, v):
    return min(Z_CLR, Z_CLR - K_AISLE * (abs(v - BC_VC) - BC_NHW))


def _bc_fn(f):
    return lambda x, y: f(*BF.loc(x, y))


def _bc_ridge_kink(E):
    """Wall parameter where the edge crosses the nave ridge line (v = BC_VC), if any."""
    (u0, v0), (u1, v1) = BF.loc(*E.a), BF.loc(*E.c)
    if (v0 - BC_VC) * (v1 - BC_VC) < 0:
        return [E.L * (BC_VC - v0) / (v1 - v0)]
    return []


def _bc_glass_tracery(vis, E, t0, t1, z0, ztop, t_ridge):
    """Timber Gothic tracery on a glass gable face (wall plane E, t0..t1, sill z0, top profile ztop(t),
    apex at t_ridge): frame, a great pointed arch, two lancets under it, an oculus, mullions, transom.
    Decal strips; the arches are fitted (springing lowered, then apex lowered) until every point stays
    0.2 m under the gable line."""
    w = 0.16
    zr = ztop(t_ridge)
    E.strip(vis, t0, z0, t1, z0, w, "door_wood")
    E.strip(vis, t0, z0, t0, ztop(t0), w, "door_wood")
    E.strip(vis, t1, z0, t1, ztop(t1), w, "door_wood")
    E.strip(vis, t0, ztop(t0), t_ridge, zr, w, "door_wood")
    E.strip(vis, t_ridge, zr, t1, ztop(t1), w, "door_wood")

    def bez(p0, p1, p2, n):
        return [((1 - k / n) ** 2 * p0[0] + 2 * (1 - k / n) * (k / n) * p1[0] + (k / n) ** 2 * p2[0],
                 (1 - k / n) ** 2 * p0[1] + 2 * (1 - k / n) * (k / n) * p1[1] + (k / n) ** 2 * p2[1])
                for k in range(n + 1)]

    def pointed(a, b, zs, zap, n=5):
        m = (a + b) / 2
        h = zap - zs
        return [bez((a, zs), (a, zs + 0.62 * h), (m, zap), n), bez((b, zs), (b, zs + 0.62 * h), (m, zap), n)]

    def fits(pls, margin=0.2):
        return all(z <= ztop(t) - margin for pl in pls for t, z in pl)

    def draw(pls, ww):
        for pl in pls:
            for (ta, za), (tb, zb) in zip(pl, pl[1:]):
                E.strip(vis, ta, za, tb, zb, ww, "door_wood")

    a, b = t0 + 0.12, t1 - 0.12
    tm = (a + b) / 2
    # great arch: start springing at the lower corner of the gable line, apex 0.5 m under the ridge
    zap = zr - 0.5
    zs = min(ztop(a), ztop(b)) - 0.35
    big = pointed(a, b, zs, zap)
    while not fits(big) and zs > z0 + 1.2:
        zs -= 0.15
        big = pointed(a, b, zs, zap)
    while not fits(big) and zap > zs + 1.0:
        zap -= 0.15
        big = pointed(a, b, zs, zap)
    if not fits(big):
        return
    draw(big, w * 0.9)
    # lancets: two pointed arches between the jambs and the central mullion, under the great arch
    lz = max(z0 + 0.6, zs - 0.15 - 0.55 * (b - a) / 2)
    lap = min(zs + 0.45 * (zap - zs), lz + 1.6 * (b - a) / 2)
    lancets = pointed(a, tm - 0.04, lz, lap, 4) + pointed(tm + 0.04, b, lz, lap, 4)
    while not fits(lancets) and lap > lz + 0.4:
        lap -= 0.15
        lancets = pointed(a, tm - 0.04, lz, lap, 4) + pointed(tm + 0.04, b, lz, lap, 4)
    if fits(lancets):
        draw(lancets, w * 0.75)
    E.strip(vis, tm, z0, tm, lap, w * 0.8, "door_wood")
    for tt in (a + (tm - a) / 2, tm + (b - tm) / 2):
        E.strip(vis, tt, z0, tt, lz + 0.35 * (lap - lz), w * 0.6, "door_wood")
    zt = z0 + min(2.6, 0.5 * (lz - z0))
    E.strip(vis, t0, zt, t1, zt, w * 0.8, "door_wood")
    # oculus (octagon) between the lancet tips and the great arch apex
    oz = (lap + zap) / 2
    orad = min(0.42 * (zap - lap), 0.3 * (b - a))
    if orad > 0.25:
        ring = [(tm + orad * math.cos(2 * math.pi * k / 8), oz + orad * math.sin(2 * math.pi * k / 8))
                for k in range(9)]
        if fits([ring]):
            draw([ring], w * 0.6)


def _bc_window_bays(vis, E, n, z0=0.45, z1=3.05, margin=0.6, skip=()):
    """Floor-to-ceiling window bays between cypress piers on a hall wall."""
    if E.L < 2 * margin + 0.8:
        return
    pitch = (E.L - 2 * margin) / n
    for k in range(n):
        if k in skip:
            continue
        a = margin + pitch * k + 0.22
        b = margin + pitch * (k + 1) - 0.22
        E.panel(vis, a, b, z0, z1, "window_glass", off=0.03)
        E.strip(vis, (a + b) / 2, z0, (a + b) / 2, z1, 0.07, "door_wood", off=0.05)
        E.strip(vis, a, z0 + 2.05, b, z0 + 2.05, 0.07, "door_wood", off=0.05)


def _build_bc(ctx):
    vis, col = C.Builder(), C.Builder()
    L = BC_L
    P = [BF.p(u, v) for u, v in L]
    aisle = _bc_fn(_bc_aisle_z)
    nave = _bc_fn(_bc_nave_z)

    # ---- hall (aisles): the OSM ring is clockwise, so each chain of OSM indices (in OSM order) becomes
    # reversed Edges (outward normals)
    def ccw_edges(idx):
        """OSM index chain in OSM (clockwise) order -> counter-clockwise Edges, outward on the right."""
        return [Edge(P[j], P[i]) for i, j in zip(idx, idx[1:])]

    north_idx = [20, 21, 22, 23, 24, 0, 1]          # north aisle outline (OSM order: west -> east)
    south_idx = [6, 7, 8, 9, 10, 11, 12]            # south aisle outline (OSM order: east -> west)
    hall_edges = ccw_edges(north_idx) + ccw_edges(south_idx)
    for E in hall_edges:
        E.wall_to(vis, -0.1, aisle, "door_wood")
    # collision: the same outline without the two sub-metre jogs at the vestibule (21, 11; < 0.1 m off)
    for E in ccw_edges([20, 22, 23, 24, 0, 1]) + ccw_edges([6, 7, 8, 9, 10, 12]):
        E.wall_to(col, 0.0, aisle, "door_wood")
    # window bays (north long wall 22 -> 23 is index pair (23, 22) in ccw_edges order)
    for E in hall_edges:
        if E.L > 4.0:
            n = max(2, int(E.L // 1.9))
            door_skip = ()
            # side doors at OSM nodes 23 / 9 (secondary entrances): leave the bay next to them as a door
            for di in (23, 9):
                for k in range(n):
                    pitch = (E.L - 1.2) / n
                    mid = E.xy(0.6 + pitch * (k + 0.5))
                    if math.dist(mid, P[di]) < pitch * 0.75:
                        door_skip = door_skip + (k,)
            _bc_window_bays(vis, E, n, skip=door_skip)
    for di in (23, 9):                                   # side doors (cypress-framed glass doors)
        best = min(hall_edges, key=lambda E: _seg_dist(P[di], E.a, E.c))
        t = (P[di][0] - best.a[0]) * best.d[0] + (P[di][1] - best.a[1]) * best.d[1]
        t = max(0.9, min(best.L - 0.9, t))
        best.panel(vis, t - 0.75, t + 0.75, 0.0, 2.5, "window_dark", off=0.03)
        best.strip(vis, t, 0.0, t, 2.5, 0.08, "door_wood", off=0.05)
        best.strip(vis, t - 0.8, 2.55, t + 0.8, 2.55, 0.14, "door_wood", off=0.05)
    # ---- aisle roofs (lean-to, 31 deg, copper) over the hall: rectangles with eave overhang
    for sgn in (1, -1):
        v_in = BC_VC + sgn * BC_NHW
        v_out = BC_VC + sgn * (BC_NHW + 2.37)
        z_out = Z_CLR - K_AISLE * 2.37
        quad = [BF.p3(-8.6, v_in, Z_CLR), BF.p3(10.9, v_in, Z_CLR), BF.p3(10.9, v_out, z_out),
                BF.p3(-8.6, v_out, z_out)]
        vis.poly(quad, "bronze", uvs=_roof_uvs(quad), normal_hint=(0.0, 0.0, 1.0))
        col.poly(quad, "bronze", normal_hint=(0.0, 0.0, 1.0))
        vis.poly([(x, y, z - 0.15) for x, y, z in quad], "door_wood", normal_hint=(0.0, 0.0, -1.0))   # soffit
        _beam_split(vis, BF.p3(-8.6, v_out, z_out - 0.08), BF.p3(10.9, v_out, z_out - 0.08), 0.1, 0.22, "door_wood")
        # aisle-roof west end above the vestibule roof (the strip |v| = 3.18 .. 3.72 over the vestibule)
        v_lim = BC_VC + sgn * 3.72
        Ew = Edge(BF.p(-8.6, v_lim), BF.p(-8.6, v_in)) if sgn > 0 else Edge(BF.p(-8.6, v_in), BF.p(-8.6, v_lim))
        Ew.wall_to(vis, Z_VEST - 0.05, lambda x, y: _bc_aisle_z(*BF.loc(x, y)) - 0.02, "door_wood")
        Ew.wall_to(col, Z_VEST, lambda x, y: _bc_aisle_z(*BF.loc(x, y)), "door_wood")
        Ee = Edge(BF.p(10.9, v_in), BF.p(10.9, v_out)) if sgn > 0 else Edge(BF.p(10.9, v_out), BF.p(10.9, v_in))
        Ee.panel(vis, 0.0, Ee.L, z_out - 0.15, z_out + 0.02, "door_wood", off=0.0)

    # ---- nave: clerestory walls, chancel walls, west gable (glass + tracery), steep copper roof
    for sgn in (1, -1):
        v = BC_VC + sgn * BC_NHW
        w_pt, e_pt = BF.p(BC_U0, v), BF.p(L[1][0] if sgn > 0 else L[6][0], v)
        E = Edge(e_pt, w_pt) if sgn > 0 else Edge(w_pt, e_pt)      # outward +v (north) / -v (south)
        E.wall_to(vis, Z_CLR - 0.3, lambda x, y: Z_EAVE, "door_wood")
        E.wall_to(col, Z_CLR - 0.3, lambda x, y: Z_EAVE, "door_wood")
        E.panel(vis, 0.3, E.L - 0.3, Z_CLR + 0.12, Z_EAVE - 0.18, "window_glass", off=0.03)
        k = int(E.L // 1.6)
        for j in range(1, k):
            t = E.L * j / k
            E.strip(vis, t, Z_CLR + 0.1, t, Z_EAVE - 0.15, 0.1, "door_wood", off=0.05)
    chancel = ccw_edges([1, 2, 3, 4, 5, 6])            # north side -> chamfer -> east face -> chamfer -> south
    for E in chancel:
        kinks = _bc_ridge_kink(E)
        E.wall_to(vis, -0.1, nave, "window_glass", kinks=kinks)
        E.wall_to(col, 0.0, nave, "window_glass", kinks=kinks)
    east = max(chancel, key=lambda E: E.L)              # the picture-window face (OSM 3 -> 4)
    _bc_glass_tracery(vis, east, 0.08, east.L - 0.08, 0.5, lambda t: nave(*east.xy(t)) - 0.25,
                      _bc_ridge_kink(east)[0])
    for E in chancel:
        if E is not east:
            E.strip(vis, 0.06, 0.0, 0.06, nave(*E.xy(0.06)) - 0.2, 0.14, "door_wood")
            E.strip(vis, E.L - 0.06, 0.0, E.L - 0.06, nave(*E.xy(E.L - 0.06)) - 0.2, 0.14, "door_wood")
            E.strip(vis, 0.0, 3.05, E.L, 3.05, 0.12, "door_wood")
            E.strip(vis, 0.0, 0.25, E.L, 0.25, 0.3, "door_wood")
    wg = Edge(BF.p(BC_U0, BC_VC + BC_NHW), BF.p(BC_U0, BC_VC - BC_NHW))     # west gable (faces WSW)
    wg.wall_to(vis, Z_VEST - 0.05, nave, "window_glass", kinks=(wg.L / 2,))
    wg.wall_to(col, Z_VEST, nave, "window_glass", kinks=(wg.L / 2,))
    _bc_glass_tracery(vis, wg, 0.1, wg.L - 0.1, Z_VEST + 0.05, lambda t: nave(*wg.xy(t)) - 0.25, wg.L / 2)
    # roof: two planes, 0.3 m overhang at the eaves and gables; soffit; ridge cap; bargeboards
    ov = 0.3
    v_e = BC_NHW + ov
    z_e = Z_EAVE - K_NAVE * ov
    ua, ub = BC_U0 - ov, BC_U1 + ov
    for sgn in (1, -1):
        quad = [BF.p3(ua, BC_VC, Z_RIDGE), BF.p3(ub, BC_VC, Z_RIDGE), BF.p3(ub, BC_VC + sgn * v_e, z_e),
                BF.p3(ua, BC_VC + sgn * v_e, z_e)]
        vis.poly(quad, "bronze", uvs=_roof_uvs(quad), normal_hint=(0.0, 0.0, 1.0))
        col.poly(quad, "bronze", normal_hint=(0.0, 0.0, 1.0))
        vis.poly([(x, y, z - 0.18) for x, y, z in quad], "door_wood", normal_hint=(0.0, 0.0, -1.0))
        for uu in (ua, ub):
            _beam(vis, BF.p3(uu, BC_VC, Z_RIDGE - 0.05), BF.p3(uu, BC_VC + sgn * v_e, z_e - 0.05), 0.12, 0.3,
                  "door_wood")
        _beam_split(vis, BF.p3(ua, BC_VC + sgn * v_e, z_e - 0.1), BF.p3(ub, BC_VC + sgn * v_e, z_e - 0.1), 0.12,
                    0.22, "bronze", max_len=7.5)                                     # copper gutter
    _beam_split(vis, BF.p3(ua - 0.05, BC_VC, Z_RIDGE + 0.08), BF.p3(ub + 0.05, BC_VC, Z_RIDGE + 0.08), 0.28, 0.16,
                "bronze", max_len=7.5)                                                # ridge cap

    # ---- vestibule (flat copper roof 3.7) and entry porch (gable, main door)
    vest_edges = ccw_edges([18, 19, 20]) + ccw_edges([12, 13, 14])
    for E in vest_edges:
        E.wall_to(vis, -0.1, lambda x, y: Z_VEST, "door_wood")
        E.wall_to(col, 0.0, lambda x, y: Z_VEST, "door_wood")
        if E.L > 1.0:
            E.panel(vis, 0.2, E.L - 0.2, 0.45, Z_VEST - 0.45, "window_glass", off=0.03)
            E.strip(vis, E.L / 2, 0.45, E.L / 2, Z_VEST - 0.45, 0.08, "door_wood")
    vest_ring = [P[12], P[13], P[14], P[18], P[19], P[20]]
    _flat(vis, vest_ring, Z_VEST, "bronze")
    _flat(col, vest_ring, Z_VEST, "bronze")
    for E in vest_edges:                                # copper coping
        E.panel(vis, -0.05, E.L + 0.05, Z_VEST - 0.18, Z_VEST + 0.04, "bronze", off=0.04)
    porch_edges = ccw_edges([14, 15, 16, 17, 18])
    for E in porch_edges:
        kinks = []
        (u0, v0), (u1, v1) = BF.loc(*E.a), BF.loc(*E.c)
        if (v0 - BC_PORCH_VC) * (v1 - BC_PORCH_VC) < 0:
            kinks = [E.L * (BC_PORCH_VC - v0) / (v1 - v0)]
        E.wall_to(vis, -0.1, lambda x, y: _porch_z(*BF.loc(x, y)), "door_wood", kinks=kinks)
    for E in ccw_edges([14, 15, 17, 18]):               # collision: the west face as one plane (15 -> 17)
        kinks = []
        (u0, v0), (u1, v1) = BF.loc(*E.a), BF.loc(*E.c)
        if (v0 - BC_PORCH_VC) * (v1 - BC_PORCH_VC) < 0:
            kinks = [E.L * (BC_PORCH_VC - v0) / (v1 - v0)]
        E.wall_to(col, 0.0, lambda x, y: _porch_z(*BF.loc(x, y)), "door_wood", kinks=kinks)
    # porch roof: ridge along u, from 0.3 m beyond the west face to the vestibule
    pw = max(abs(L[17][1] - BC_PORCH_VC), abs(L[15][1] - BC_PORCH_VC)) + 0.3
    kp = (Z_PORCH_R - Z_PORCH_E) / (pw - 0.3)
    pu0, pu1 = L[16][0] - 0.3, L[18][0] + 0.05
    for sgn in (1, -1):
        quad = [BF.p3(pu0, BC_PORCH_VC, Z_PORCH_R), BF.p3(pu1, BC_PORCH_VC, Z_PORCH_R),
                BF.p3(pu1, BC_PORCH_VC + sgn * pw, Z_PORCH_R - kp * pw),
                BF.p3(pu0, BC_PORCH_VC + sgn * pw, Z_PORCH_R - kp * pw)]
        vis.poly(quad, "bronze", uvs=_roof_uvs(quad), normal_hint=(0.0, 0.0, 1.0))
        col.poly(quad, "bronze", normal_hint=(0.0, 0.0, 1.0))
        vis.poly([(x, y, z - 0.12) for x, y, z in quad], "door_wood", normal_hint=(0.0, 0.0, -1.0))
        _beam(vis, BF.p3(pu0, BC_PORCH_VC, Z_PORCH_R - 0.04),
              BF.p3(pu0, BC_PORCH_VC + sgn * pw, Z_PORCH_R - kp * pw - 0.04), 0.1, 0.22, "door_wood")
    # porch gable end above the vestibule roof (east end of the porch ridge: a small triangle)
    hwg = (Z_PORCH_R - Z_VEST) / kp
    tri = [BF.p3(pu1, BC_PORCH_VC - hwg, Z_VEST), BF.p3(pu1, BC_PORCH_VC + hwg, Z_VEST),
           BF.p3(pu1, BC_PORCH_VC, Z_PORCH_R)]
    vis.poly(tri, "door_wood", normal_hint=(BF.u[0], BF.u[1], 0.0))
    col.poly(tri, "door_wood", normal_hint=(BF.u[0], BF.u[1], 0.0))
    # the vestibule's west face behind the porch (closes the shell between the porch roof and 3.7 m)
    vw = Edge(P[18], P[14])                                                          # faces -u (west)
    vw.wall_to(vis, Z_PORCH_E - 0.3, lambda x, y: Z_VEST, "door_wood")
    vw.wall_to(col, Z_PORCH_E - 0.3, lambda x, y: Z_VEST, "door_wood")
    # main door (maple with cherry Gothic inlays: a pointed-arch door) on the porch's west face 17 -> 15
    west = Edge(P[17], P[15])
    tm = max(1.0, min(west.L - 1.0, math.dist(P[17], P[16])))
    west.panel(vis, tm - 0.85, tm + 0.85, 0.0, 2.3, "door_wood", off=0.04)
    west.strip(vis, tm, 0.0, tm, 2.3, 0.06, "dark_trim", off=0.06)
    west.panel(vis, tm - 0.7, tm + 0.7, 2.35, 2.62, "window_glass", off=0.04)
    west.strip(vis, tm - 0.95, 2.3, tm, 2.85, 0.16, "dark_trim", off=0.06)
    west.strip(vis, tm, 2.85, tm + 0.95, 2.3, 0.16, "dark_trim", off=0.06)
    west.strip(vis, tm - 0.95, 0.0, tm - 0.95, 2.3, 0.16, "dark_trim", off=0.06)
    west.strip(vis, tm + 0.95, 0.0, tm + 0.95, 2.3, 0.16, "dark_trim", off=0.06)

    # ---- plinth (travertine-coloured base course)
    for E in hall_edges + chancel + vest_edges + porch_edges:
        E.panel(vis, 0.0, E.L, -0.1, 0.32, "limestone", off=0.06)

    # ---- footbridge over the western arm (w427713653): concrete deck, ramps, timber railings
    _build_bridge(vis, col)
    return _parts(SLUG_BC, vis, col)


def _porch_z(u, v):
    pw = max(abs(BC_L[17][1] - BC_PORCH_VC), abs(BC_L[15][1] - BC_PORCH_VC)) + 0.3
    kp = (Z_PORCH_R - Z_PORCH_E) / (pw - 0.3)
    return Z_PORCH_R - kp * abs(v - BC_PORCH_VC)


def _bridge_edge():
    """Bridge axis south -> north (t = 0 at the south OSM node)."""
    return Edge(BRIDGE[1], BRIDGE[0])


BR_T0 = -1.0                   # deck from 1 m before the south node to 1.5 m past the north node
BR_RAMP = 2.5
BR_HW = 1.0


def _bridge_span():
    E = _bridge_edge()
    return E, BR_T0, E.L + 1.5


def _build_bridge(vis, col):
    E, t0, t1 = _bridge_span()
    z = BR_DECK_Z
    hw = BR_HW

    def q(ta, tb, za, zb, w):
        return [(*E.xy(ta, w), za), (*E.xy(tb, w), zb), (*E.xy(tb, -w), zb), (*E.xy(ta, -w), za)]

    deck = q(t0, t1, z, z, hw)
    vis.poly(deck, "concrete", normal_hint=(0, 0, 1))
    # collision deck reaches 0.15 m over each ramp top (the deck, 2-4 cm higher there, wins find_floor:
    # no crack at the seam after the export rounds the vertices)
    col.poly(q(t0 - 0.15, t1 + 0.15, z, z, hw), "concrete", normal_hint=(0, 0, 1))
    vis.poly([(x, y, zz - 0.32) for x, y, zz in reversed(deck)], "concrete", normal_hint=(0, 0, -1))
    for ta, tb, za, zb in ((t0 - BR_RAMP, t0, -0.06, z), (t1, t1 + BR_RAMP, z, -0.06)):
        ramp = q(ta, tb, za, zb, hw)
        vis.poly(ramp, "concrete", normal_hint=(0, 0, 1))
        col.poly(ramp, "concrete", normal_hint=(0, 0, 1))
    for side in (1, -1):
        w = side * hw
        vis.poly([(*E.xy(t0, w), z - 0.32), (*E.xy(t1, w), z - 0.32), (*E.xy(t1, w), z), (*E.xy(t0, w), z)],
                 "concrete", normal_hint=(E.n[0] * side, E.n[1] * side, 0.0))
        # ramp side faces
        for ta, tb, za, zb in ((t0 - BR_RAMP, t0, -0.06, z), (t1, t1 + BR_RAMP, z, -0.06)):
            tri = [(*E.xy(ta, w), -0.3), (*E.xy(tb, w), -0.3), (*E.xy(tb, w), zb), (*E.xy(ta, w), za)]
            vis.poly(tri, "concrete", normal_hint=(E.n[0] * side, E.n[1] * side, 0.0))
        # railing: posts every ~1.5 m, top and mid rails (dark timber); collision: a 0.3 m wall + top
        k = max(2, int(math.ceil((t1 - t0) / 1.5)))
        for j in range(k + 1):
            x, y = E.xy(t0 + (t1 - t0) * j / k, side * (hw - 0.08))
            _post(vis, x, y, 0.07, z, z + 1.08, "door_wood", n=4, top="door_wood",
                  rot=math.atan2(E.d[1], E.d[0]) + math.pi / 4)
        for zz, ww in ((z + 1.05, 0.12), (z + 0.55, 0.07)):
            _beam_split(vis, (*E.xy(t0, side * (hw - 0.08)), zz), (*E.xy(t1, side * (hw - 0.08)), zz), ww, ww,
                        "door_wood")
        _line_box(col, E.xy(t0, side * (hw - 0.15)), E.xy(t1, side * (hw - 0.15)), 0.3, z, z + 1.05, "door_wood")
    # abutments + a mid pier pair (visual), lanterns at the south end (lit=yes)
    for t in (0.0, E.L):
        ring = [E.xy(t - 0.4, hw + 0.1), E.xy(t + 0.4, hw + 0.1), E.xy(t + 0.4, -hw - 0.1), E.xy(t - 0.4, -hw - 0.1)]
        vis.prism(ring, PILE_Z, z - 0.32, "concrete")
    for side in (1, -1):
        x, y = E.xy(E.L / 2, side * (hw - 0.3))
        _post(vis, x, y, 0.22, PILE_Z, z - 0.3, "concrete", n=6)
    for side in (1, -1):
        x, y = E.xy(t0 - BR_RAMP - 0.4, side * (hw + 0.35))
        _post(vis, x, y, 0.08, -0.05, 1.1, "dark_trim", n=6, top="dark_trim")
        vis.prism(_ngon(x, y, 0.16, 6), 1.1, 1.45, "white_trim", top="dark_trim")


# =================================================================== 3. boardwalks + overlook
SLUG_BW = "lake_boardwalks"
BW_Z = 0.5
BW_HW = 0.9
BW_BAY = (3.6, 6.6, 1.6)          # t0, t1 along the boardwalk, depth on the lake (right) side
OV_Z = 0.6
OV_S = (-0.5, 4.5)                # platform extent along the boardwalk direction from the viewpoint
OV_HW = 2.5


def _bw_north_edge():
    return Edge(BW_NORTH[0], BW_NORTH[1])        # west -> east; right side = lake (south-east)


def _ov_edge():
    """From the end of OSM way w427905290 to the viewpoint and on (t = 0 at the viewpoint)."""
    E = Edge(BW_EAST[-1], VIEWPOINT)
    return E


def _deck_quad(E, ta, tb, w0, w1, za, zb=None):
    zb = za if zb is None else zb
    return [(*E.xy(ta, w1), za), (*E.xy(tb, w1), zb), (*E.xy(tb, w0), zb), (*E.xy(ta, w0), za)]


def _deck(vis, col, E, ta, tb, w0, w1, z, piles=True, edge_mat="dark_trim", thick=0.25, pile_z=PILE_Z, pile_n=6,
          pile_step=2.4):
    """Timber deck on E between ta..tb and w0..w1 (right-hand offsets), top at z. Visual in pieces of
    <= 12 m (texture repeats); collision: the top only (one quad). Piles down to pile_z."""
    if col is not None:
        col.poly(_deck_quad(E, ta, tb, w0, w1, z), "door_wood", normal_hint=(0, 0, 1))
    n = max(1, int(math.ceil((tb - ta) / 12.0)))
    for k in range(n):
        pa, pb = ta + (tb - ta) * k / n, ta + (tb - ta) * (k + 1) / n
        top = _deck_quad(E, pa, pb, w0, w1, z)
        vis.poly(top, "door_wood", normal_hint=(0, 0, 1))
        vis.poly([(x, y, zz - thick) for x, y, zz in reversed(top)], "dark_trim", normal_hint=(0, 0, -1))
        for w, sgn in ((w1, 1), (w0, -1)):                                  # long side faces
            face = [(*E.xy(pa, w), z - thick), (*E.xy(pb, w), z - thick), (*E.xy(pb, w), z), (*E.xy(pa, w), z)]
            vis.poly(face, edge_mat, normal_hint=(E.n[0] * sgn, E.n[1] * sgn, 0.0))
    for t, sgn in ((ta, -1), (tb, 1)):                                      # end faces
        face = [(*E.xy(t, w0), z - thick), (*E.xy(t, w1), z - thick), (*E.xy(t, w1), z), (*E.xy(t, w0), z)]
        vis.poly(face, edge_mat, normal_hint=(E.d[0] * sgn, E.d[1] * sgn, 0.0))
    if piles:
        k = max(1, int(math.ceil((tb - ta) / pile_step)))
        for j in range(k + 1):
            t = ta + (tb - ta) * j / k
            for w in (w0 + 0.15, w1 - 0.15):
                x, y = E.xy(t, w)
                _post(vis, x, y, 0.11, pile_z, z - thick, "door_wood", n=pile_n)


def _ramp(vis, col, E, ta, tb, za, zb, hw):
    q = _deck_quad(E, ta, tb, -hw, hw, za, zb)
    vis.poly(q, "door_wood", normal_hint=(0, 0, 1))
    col.poly(q, "door_wood", normal_hint=(0, 0, 1))
    for side in (1, -1):
        w = side * hw
        face = [(*E.xy(ta, w), min(za, zb) - 0.2), (*E.xy(tb, w), min(za, zb) - 0.2), (*E.xy(tb, w), zb),
                (*E.xy(ta, w), za)]
        vis.poly(face, "dark_trim", normal_hint=(E.n[0] * side, E.n[1] * side, 0.0))


def _railing(vis, col, pts, z, h=1.0):
    """Timber railing along a polyline on a deck at z: posts every <= 1.6 m, top + mid rails. Collision:
    one 0.3 m wall strip per leg, overlapping at the corners, closed only at the two free ends (no top:
    the rail is not a walkway)."""
    last = len(pts) - 2
    for i, (a, c) in enumerate(zip(pts, pts[1:])):
        E = Edge(a, c)
        k = max(1, int(math.ceil(E.L / 1.6)))
        for j in range(k + 1):
            x, y = E.xy(E.L * j / k)
            _post(vis, x, y, 0.065, z, z + h + 0.03, "door_wood", n=4, top="door_wood",
                  rot=math.atan2(E.d[1], E.d[0]) + math.pi / 4)
        for zz, ww in ((z + h, 0.12), (z + h * 0.5, 0.07)):
            _beam_split(vis, (a[0], a[1], zz), (c[0], c[1], zz), ww, ww, "door_wood")
        if col is not None:
            _line_box(col, a, c, 0.3, z, z + h, "door_wood", end_a=(i == 0), end_c=(i == last),
                      ext=(0.0 if i == 0 else 0.15, 0.0 if i == last else 0.15))


def _build_bw(ctx):
    vis, col = C.Builder(), C.Builder()
    # ---- north-shore boardwalk across the inlet mouth
    E = _bw_north_edge()
    t0, t1 = -0.8, E.L + 0.8
    _deck(vis, col, E, t0, t1, -BW_HW, BW_HW, BW_Z)
    b0, b1, bd = BW_BAY
    _deck(vis, col, E, b0, b1, BW_HW - 0.05, BW_HW + bd, BW_Z)          # viewing bay (lake side)
    _ramp(vis, col, E, t0 - 2.2, t0 + 0.15, -0.06, BW_Z, BW_HW)
    _ramp(vis, col, E, t1 - 0.15, t1 + 2.2, BW_Z, -0.06, BW_HW)
    # kick rails + low posts along the open deck (visual), a real railing round the bay (collision)
    for side, spans in ((-1, ((t0, t1),)), (1, ((t0, b0), (b1, t1)))):
        w = side * (BW_HW - 0.06)
        for ta, tb in spans:
            _beam(vis, (*E.xy(ta, w), BW_Z + 0.08), (*E.xy(tb, w), BW_Z + 0.08), 0.1, 0.16, "door_wood")
            k = max(1, int(math.ceil((tb - ta) / 2.0)))
            for j in range(k + 1):
                x, y = E.xy(ta + (tb - ta) * j / k, w)
                _post(vis, x, y, 0.06, BW_Z, BW_Z + 0.45, "door_wood", n=4, top="door_wood")
    bay = [E.xy(b0, BW_HW - 0.02), E.xy(b0, BW_HW + bd - 0.1), E.xy(b1, BW_HW + bd - 0.1), E.xy(b1, BW_HW - 0.02)]
    _railing(vis, col, bay, BW_Z)

    # ---- east overlook: platform at the viewpoint, the boardwalk back to OSM w427905290 (visual past
    # the play zone), steps down to the marsh
    O = _ov_edge()
    tv = O.L                                           # viewpoint parameter on O
    s0, s1 = OV_S
    plat = (tv + s0, tv + s1)
    _deck(vis, col, O, plat[0], plat[1], -OV_HW, OV_HW, OV_Z, pile_z=-0.3)
    # boardwalk from the platform back to the end of the OSM way: collision only inside the play zone
    tin = None
    for k in range(200):
        t = tv + s0 - 0.25 * k
        if O.xy(t, 0.0)[0] > PLAY_XMAX - 0.5 or any(O.xy(t, w)[0] > PLAY_XMAX - 0.4 for w in (-BW_HW, BW_HW)):
            tin = t
            break
    tin = tv + s0 if tin is None else tin
    land = {"pile_z": -0.3, "pile_n": 4, "pile_step": 3.0}                 # the overlook stands in the marsh
    if tin < tv + s0 - 0.05:
        _deck(vis, col, O, tin, tv + s0 + 0.15, -BW_HW, BW_HW, OV_Z, **land)
    _deck(vis, None, O, 0.0, tin + 0.05, -BW_HW, BW_HW, OV_Z, **land)
    # the rest of the OSM boardwalk (visual only, clipped at the visual extent)
    pts = [p for p in reversed(BW_EAST)]
    for a, c in zip(pts, pts[1:]):
        if a[0] >= VIS_XMAX:
            break
        Ee = Edge(a, c)
        tb = Ee.L
        if c[0] > VIS_XMAX:
            tb = Ee.L * (VIS_XMAX - a[0]) / (c[0] - a[0])
        _deck(vis, None, Ee, -0.1, tb, -BW_HW, BW_HW, OV_Z, **land)
    # platform railings (3 sides; the south-west side has a 1.8 m gap for the steps)
    pa, pb = plat
    c1, c2 = O.xy(pa, -OV_HW + 0.08), O.xy(pb, -OV_HW + 0.08)
    c3, c4 = O.xy(pb, OV_HW - 0.08), O.xy(pa, OV_HW - 0.08)
    _railing(vis, col, [O.xy(pa, -BW_HW - 0.05), c1, c2, O.xy(pb, -0.9)], OV_Z)
    _railing(vis, col, [O.xy(pb, 0.9), c3, c4, O.xy(pa, BW_HW + 0.05)], OV_Z)
    _ramp(vis, col, O, pb - 0.15, pb + 2.3, OV_Z, -0.06, 0.88)
    return _parts(SLUG_BW, vis, col)


def _bw_layout():
    E = _bw_north_edge()
    b0, b1, bd = BW_BAY
    tm = (b0 + b1) / 2
    O = _ov_edge()
    tv = O.L
    spots = {
        "north_boardwalk_mid": _r((*E.xy(E.L / 2), BW_Z)),
        "census_boardwalk": _r((*E.xy(tm, BW_HW + bd / 2), BW_Z)),
        "regatta_launch_boardwalk": _r((*E.xy(tm, BW_HW + bd - 0.6), BW_Z)),
        "boardwalk_underside": _r((*E.xy(E.L / 2 - 1.0), WATER_Z)),
        "north_boardwalk_west_end": _r((*E.xy(-2.8), 0.0)),
        "north_boardwalk_east_end": _r((*E.xy(E.L + 2.8), 0.0)),
        "east_overlook_platform": _r((*O.xy(tv + sum(OV_S) / 2), OV_Z)),
        "east_overlook_steps_foot": _r((*O.xy(tv + OV_S[1] + 2.6), 0.0)),
    }
    markers = {
        "decks_m": {"north_boardwalk": BW_Z, "east_overlook": OV_Z, "water_assumed": WATER_Z},
        "north_boardwalk_axis_m": [_r(p) for p in BW_NORTH],
        "east_overlook_note": "platform at OSM viewpoint n4270696932; the boardwalk east of x = -1510 "
                              "(play-zone wall) is visual only",
    }
    return {"spots": spots, "markers": markers}


# =================================================================== 4. Museum Road lake edge
SLUG_ROAD = "museum_road_edge"
LAMP_S = (15.0, 60.0, 105.0, 150.0, 195.0, 240.0, 285.0, 330.0)     # arc length along SIDEWALK_LAKE
LAMP_OFF = 1.7
LAMP_H = 7.2
SIGN_S = (40.0, 135.0, 228.0, 300.0)
LAKE_BENCH_S = (183.0, 199.0)


def _lake_side(p, d):
    """Unit normal at sidewalk point p (tangent d) pointing away from Museum Road (toward the lake)."""
    n = (d[1], -d[0])
    a = (p[0] + n[0], p[1] + n[1])
    b = (p[0] - n[0], p[1] - n[1])
    return n if _poly_dist(a, MUSEUM_RD) > _poly_dist(b, MUSEUM_RD) else (-n[0], -n[1])


def _lamp(vis, x, y, toward):
    """Museum Road street light: dark pole, arm toward the road, flat luminaire."""
    _post(vis, x, y, 0.11, -0.1, LAMP_H, "dark_trim", n=8, top="dark_trim")
    _post(vis, x, y, 0.17, -0.1, 0.7, "dark_trim", n=8, top="dark_trim")
    hx, hy = x + toward[0] * 1.7, y + toward[1] * 1.7
    _beam(vis, (x, y, LAMP_H - 0.3), (hx, hy, LAMP_H + 0.05), 0.08, 0.08, "dark_trim")
    G = Frame((hx, hy), math.degrees(math.atan2(toward[1], toward[0])))
    vis.prism([G.p(-0.25, -0.18), G.p(0.35, -0.18), G.p(0.35, 0.18), G.p(-0.25, 0.18)], LAMP_H - 0.12, LAMP_H + 0.08,
              "dark_trim", top="dark_trim", bottom="white_trim")


def _gator_sign(vis, x, y, face):
    """DANGER ALLIGATORS sign: white panel, red header band, two metal posts (visual only)."""
    G = Frame((x, y), math.degrees(math.atan2(face[1], face[0])) - 90.0)    # v = facing
    for u in (-0.38, 0.38):
        px, py = G.p(u, -0.03)
        _post(vis, px, py, 0.035, -0.1, 1.95, "metal_gray", n=4, top="metal_gray")
    pan = [G.p(-0.48, 0.0), G.p(0.48, 0.0)]
    E = Edge(pan[0], pan[1])          # outward normal = -v (the back); draw the face on the reverse edge
    Ef = Edge(pan[1], pan[0])
    Ef.panel(vis, 0.0, Ef.L, 1.15, 1.72, "white_trim", off=0.0)
    Ef.panel(vis, 0.0, Ef.L, 1.72, 1.92, "brick_red", off=0.0)
    for z in (1.33, 1.45, 1.57):                                   # text lines
        Ef.panel(vis, 0.14, Ef.L - 0.14, z, z + 0.04, "dark_trim", off=0.01)
    E.panel(vis, 0.0, E.L, 1.15, 1.92, "metal_gray", off=0.0)


def _kiosk(vis, col, x, y, face_deg):
    """Lake Alice Conservation Area information kiosk: timber posts, a 2.4 m board, a shallow roof."""
    f = math.radians(face_deg)
    fx, fy = math.sin(f), math.cos(f)
    G = Frame((x, y), math.degrees(math.atan2(fy, fx)) - 90.0)              # v = facing
    for u in (-1.35, 1.35):
        px, py = G.p(u, 0.0)
        _post(vis, px, py, 0.1, -0.1, 2.75, "door_wood", n=4, top="door_wood", rot=f + math.pi / 4)
    vis.prism([G.p(-1.25, -0.1), G.p(1.25, -0.1), G.p(1.25, 0.1), G.p(-1.25, 0.1)], 0.7, 2.15, "door_wood",
              top="door_wood", bottom="door_wood")
    E = Edge(G.p(1.2, 0.11), G.p(-1.2, 0.11))
    E.panel(vis, 0.08, E.L - 0.08, 0.8, 2.05, "dark_trim", off=0.0)
    for k in range(3):                                                       # three poster panels
        a = 0.15 + k * (E.L - 0.3) / 3 + 0.05
        b = 0.15 + (k + 1) * (E.L - 0.3) / 3 - 0.05
        E.panel(vis, a, b, 0.9, 1.75, "white_trim", off=0.01)
        E.panel(vis, a, b, 1.78, 1.95, "brick_red" if k != 1 else "copper_green", off=0.01)
    rz0, rz1 = 2.65, 2.95
    for sgn in (1, -1):
        q = [(*G.p(-1.6, 0.0), rz1), (*G.p(1.6, 0.0), rz1), (*G.p(1.6, sgn * 0.75), rz0), (*G.p(-1.6, sgn * 0.75), rz0)]
        vis.poly(q, "roof_dark", normal_hint=(0, 0, 1))
        col.poly(q, "roof_dark", normal_hint=(0, 0, 1))
        vis.poly([(px, py, pz - 0.06) for px, py, pz in q], "door_wood", normal_hint=(0, 0, -1))
    vis.poly([(*G.p(-1.6, 0.75), rz0), (*G.p(-1.6, -0.75), rz0), (*G.p(-1.6, 0.0), rz1)], "door_wood",
             normal_hint=(-G.u[0], -G.u[1], 0.0))
    vis.poly([(*G.p(1.6, -0.75), rz0), (*G.p(1.6, 0.75), rz0), (*G.p(1.6, 0.0), rz1)], "door_wood",
             normal_hint=(G.u[0], G.u[1], 0.0))
    _line_box(col, G.p(-1.35, 0.0), G.p(1.35, 0.0), 0.3, 0.0, 2.15, "door_wood")
    return G.p3(0.0, 0.0, rz1)


def _road_layout():
    lamps, signs, benches = [], [], []
    for s in LAMP_S:
        p, d = _at(SIDEWALK_LAKE, s)
        n = _lake_side(p, d)
        lamps.append(((p[0] + n[0] * LAMP_OFF, p[1] + n[1] * LAMP_OFF), (-n[0], -n[1])))
    for s in SIGN_S:
        p, d = _at(SIDEWALK_LAKE, s)
        n = _lake_side(p, d)
        signs.append(((p[0] + n[0] * 3.2, p[1] + n[1] * 3.2), (-n[0], -n[1])))
    for s in LAKE_BENCH_S:
        p, d = _at(SIDEWALK_LAKE, s)
        n = _lake_side(p, d)
        benches.append(((p[0] + n[0] * 4.2, p[1] + n[1] * 4.2), math.degrees(math.atan2(n[0], n[1])) % 360))
    # kiosk at the lakeshore trail head (2.5 m along the trail, 2 m to its lake side), facing the trail
    E = Edge(*TRAIL_HEAD)
    kx, ky = E.xy(2.6, 2.3)
    kface = math.degrees(math.atan2(-E.n[0], -E.n[1])) % 360
    spots = {
        "kiosk_roof": _r((kx, ky, 2.95)),
        "lake_bench_1": _r((*benches[0][0], 0.46)),
        "lake_bench_2": _r((*benches[1][0], 0.46)),
        "hatchling_museum_road": _r((-1905.0, -583.0, 0.0)),
        "bus_stop": _r((*BUS_STOP, 0.0)),
    }
    for i, ((x, y), _) in enumerate(lamps):
        spots[f"street_light_{i}_top"] = _r((x, y, LAMP_H))
    markers = {
        "poles": [{"name": f"museum_road_light_{i}", "base_m": _r((x, y, 0.0)), "height_m": LAMP_H,
                   "note": "Museum Road street light on the lake side (climbable; the arm points at the road)"}
                  for i, ((x, y), _) in enumerate(lamps)],
        "gator_signs_m": [_r(p) for p, _ in signs],
        "kiosk_m": _r((kx, ky)),
    }
    return {"lamps": lamps, "signs": signs, "benches": benches, "kiosk": ((kx, ky), kface),
            "spots": spots, "markers": markers}


def _build_road(ctx):
    vis, col = C.Builder(), C.Builder()
    for (x, y), toward in _RL["lamps"]:
        _lamp(vis, x, y, toward)
    for (x, y), face in _RL["signs"]:
        _gator_sign(vis, x, y, face)
    for (x, y), facing in _RL["benches"]:
        _bench(vis, col, x, y, facing)
    (kx, ky), kface = _RL["kiosk"]
    _kiosk(vis, col, kx, ky, kface)
    # RTS "UF Bat Houses" bus stop sign (n10726656195)
    x, y = BUS_STOP
    _post(vis, x, y, 0.05, -0.1, 3.0, "metal_gray", n=6, top="metal_gray")
    G = Frame((x, y), 30.0)
    vis.prism([G.p(0.05, -0.02), G.p(0.6, -0.02), G.p(0.6, 0.02), G.p(0.05, 0.02)], 2.2, 2.9, "white_trim",
              top="white_trim", bottom="white_trim")
    Eb = Edge(G.p(0.05, 0.025), G.p(0.6, 0.025))
    Eb.panel(vis, 0.0, Eb.L, 2.62, 2.84, "copper_green", off=0.005)   # route band (RTS green)
    return _parts(SLUG_ROAD, vis, col)


# =================================================================== 5. bat-house field + gardens
SLUG_FIELD = "bat_house_field"
RAIL_OFF = 2.3                     # split-rail fence offset from the north sidewalk, field side
RAIL_H = 1.1
GF = Frame(((GARDEN[0][0] + GARDEN[3][0]) / 2, (GARDEN[0][1] + GARDEN[3][1]) / 2), 1.07)   # garden, west edge
ARBOR = (1.3, 2.7, 1.25, 2.6)      # u0, u1 (into the garden), half width, top
BEDS_U = (8.0, 13.5, 19.0)
BED = (0.6, 1.8, 0.45)             # half u, half v, height
LANDING_ZONE = [(-1919.0, -572.0), (-1868.5, -542.0), (-1866.0, -526.0), (-1875.0, -519.5), (-1914.0, -521.5)]


def _field_side_rail():
    """Split-rail fence polyline (field side of the north sidewalk) as two runs either side of the
    footway gap at w866087252."""
    pts = SIDEWALK_NORTH
    cs = _cum(pts)
    s_gap = cs[pts.index(FOOTWAY_FIELD)]
    side = 1.0
    p, d = _at(pts, 30.0)
    n = (d[1], -d[0])
    if _poly_dist((p[0] + n[0], p[1] + n[1]), MUSEUM_RD) < _poly_dist((p[0] - n[0], p[1] - n[1]), MUSEUM_RD):
        side = -1.0
    runs = []
    for s0, s1 in ((cs[1] + 10.0, s_gap - 2.4), (s_gap + 2.4, cs[-1] - 4.5)):
        sub = _sub(pts, s0, s1)
        runs.append(_offset_polyline(sub, side * RAIL_OFF))
    return runs


def _split_rail(vis, col, run):
    last = len(run) - 2
    for i, (a, c) in enumerate(zip(run, run[1:])):
        E = Edge(a, c)
        k = max(1, int(math.ceil(E.L / 2.6)))
        for j in range(k + 1):
            x, y = E.xy(E.L * j / k)
            _post(vis, x, y, 0.08, -0.1, RAIL_H, "door_wood", n=4, top="door_wood",
                  rot=math.atan2(E.d[1], E.d[0]) + math.pi / 4)
        for z in (0.5, 0.95):
            _beam_split(vis, (a[0], a[1], z), (c[0], c[1], z), 0.09, 0.12, "door_wood", max_len=8.0)
        _line_box(col, a, c, 0.3, 0.0, RAIL_H, "door_wood", end_a=(i == 0), end_c=(i == last),
                  ext=(0.0 if i == 0 else 0.15, 0.0 if i == last else 0.15))


def _info_board(vis, col):
    """OSM wooden "Bat House" wildlife board (two-sided: faces 225 and 45 degrees)."""
    x, y = INFO_BOARD
    G = Frame((x, y), -45.0)          # u: compass 135 (the board runs NW-SE), v: compass 45 (+v face)
    for u in (-0.95, 0.95):
        px, py = G.p(u, 0.0)
        _post(vis, px, py, 0.08, -0.1, 2.3, "door_wood", n=4, top="door_wood")
    vis.prism([G.p(-0.85, -0.07), G.p(0.85, -0.07), G.p(0.85, 0.07), G.p(-0.85, 0.07)], 0.85, 1.85, "door_wood",
              top="door_wood", bottom="door_wood")
    for sgn in (1, -1):
        # +v face: walk -u (outward on the right = +v); -v face: walk +u
        E = Edge(G.p(0.8, 0.075), G.p(-0.8, 0.075)) if sgn > 0 else Edge(G.p(-0.8, -0.075), G.p(0.8, -0.075))
        E.panel(vis, 0.06, E.L - 0.06, 0.95, 1.6, "dark_trim", off=0.0)
        E.panel(vis, 0.06, E.L - 0.06, 1.6, 1.78, "white_trim", off=0.0)
        E.panel(vis, 0.2, 0.75, 1.05, 1.5, "white_trim", off=0.01)               # bat photo panel
    for sgn in (1, -1):
        q = [(*G.p(-1.15, 0.0), 2.45), (*G.p(1.15, 0.0), 2.45), (*G.p(1.15, sgn * 0.45), 2.25),
             (*G.p(-1.15, sgn * 0.45), 2.25)]
        vis.poly(q, "roof_dark", normal_hint=(0, 0, 1))
        vis.poly([(px, py, pz - 0.05) for px, py, pz in q], "door_wood", normal_hint=(0, 0, -1))
    _line_box(col, G.p(-0.95, 0.0), G.p(0.95, 0.0), 0.3, 0.0, 1.85, "door_wood")


def _garden(vis, col):
    u0, u1, hw, zt = ARBOR
    for u in (u0, u1):
        for v in (-hw, hw):
            x, y = GF.p(u, v)
            _post(vis, x, y, 0.08, -0.1, zt - 0.12, "door_wood", n=4, top="door_wood", rot=math.radians(46.07))
    for v in (-hw, hw):                                      # side beams + lattice
        _beam(vis, GF.p3(u0 - 0.35, v, zt - 0.2), GF.p3(u1 + 0.35, v, zt - 0.2), 0.1, 0.2, "door_wood")
        for z in (0.9, 1.5):
            _beam(vis, GF.p3(u0, v, z), GF.p3(u1, v, z), 0.04, 0.06, "door_wood")
        _beam(vis, GF.p3(u0, v, 0.35), GF.p3(u1, v, zt - 0.35), 0.04, 0.06, "door_wood")
    k = 6
    for j in range(k):                                       # top slats (the trellis)
        u = u0 - 0.2 + (u1 - u0 + 0.4) * (j + 0.5) / k
        _beam(vis, GF.p3(u, -hw - 0.3, zt - 0.05), GF.p3(u, hw + 0.3, zt - 0.05), 0.08, 0.1, "door_wood")
    _flat(col, [GF.p(u0 - 0.2, -hw - 0.3), GF.p(u1 + 0.2, -hw - 0.3), GF.p(u1 + 0.2, hw + 0.3),
                GF.p(u0 - 0.2, hw + 0.3)], zt, "door_wood")
    bu, bv, bh = BED
    for uc in BEDS_U:
        ring = [GF.p(uc - bu, -bv), GF.p(uc + bu, -bv), GF.p(uc + bu, bv), GF.p(uc - bu, bv)]
        vis.prism(ring, -0.05, bh, "door_wood")
        inner = [GF.p(uc - bu + 0.08, -bv + 0.08), GF.p(uc + bu - 0.08, -bv + 0.08), GF.p(uc + bu - 0.08, bv - 0.08),
                 GF.p(uc - bu + 0.08, bv - 0.08)]
        _flat(vis, [GF.p(uc - bu, -bv), GF.p(uc + bu, -bv), GF.p(uc + bu, bv), GF.p(uc - bu, bv)], bh, "door_wood")
        _flat(vis, inner, bh + 0.01, "grass")
        for k2 in range(3):                                  # a few low plants (green blobs)
            px, py = GF.p(uc, -bv + 0.6 + k2 * (2 * bv - 1.2) / 2)
            vis.prism(_ngon(px, py, 0.28, 5, 0.3 * k2), bh, bh + 0.35, "grass", top="grass")
        _flat(col, ring, bh, "door_wood")


def _field_layout():
    runs = _field_side_rail()
    gx, gy = GF.p(12.0, 5.2)
    spots = {
        "spawn_field": (-1893.0, -541.0, 0.0),
        "spawn_bus_stop": _r((BUS_STOP[0] + 2.0, BUS_STOP[1] + 1.5, 0.0)),
        "census_houses": (-1890.0, -528.0, 0.0),
        "census_gardens": _r((gx, gy, 0.0)),
        "garden_arbor_top": _r(GF.p3((ARBOR[0] + ARBOR[1]) / 2, 0.0, ARBOR[3])),
        "bat_info_board": _r((INFO_BOARD[0] - 1.2, INFO_BOARD[1] - 1.2, 0.0)),
        "bat_bench_1": _r((*BENCHES_OSM[0], 0.46)),
    }
    for i, uc in enumerate(BEDS_U):
        spots[f"garden_bed_{i}_top"] = _r(GF.p3(uc, 0.0, BED[2]))
    markers = {
        "landing_zone_m": [_r(p) for p in LANDING_ZONE],
        "spawn_suggestions": [
            {"name": "spawn_field", "pos_m": (-1893.0, -541.0), "facing_deg": 150.0,
             "note": "landing zone: the bat-house field; facing SSE over the observation fence, Museum Road "
                     "and the lake (the barns behind). facing 330 shows the barns instead"},
            {"name": "spawn_bus_stop", "pos_m": _r((BUS_STOP[0] + 2.0, BUS_STOP[1] + 1.5)), "facing_deg": 120.0,
             "note": "RTS 'UF Bat Houses' stop: arrive by bus, facing the lake's western arm"},
        ],
        "census_stations_m": {"houses": (-1890.0, -528.0), "gardens": _r((gx, gy)),
                              "boardwalk": _BW["spots"]["census_boardwalk"][:2]},
        "observation_fence_m": [[_r(p) for p in run] for run in runs],
    }
    return {"runs": runs, "spots": spots, "markers": markers}


def _build_field(ctx):
    vis, col = C.Builder(), C.Builder()
    for run in _FL["runs"]:
        _split_rail(vis, col, run)
    for x, y in BENCHES_OSM:
        _bench(vis, col, x, y, 330.0)
    _info_board(vis, col)
    _garden(vis, col)
    return _parts(SLUG_FIELD, vis, col)


# =================================================================== Baughman layout
def _bc_layout():
    E, t0, t1 = _bridge_span()
    v_n = BC_VC + BC_NHW + 1.0
    spots = {
        "baughman_vestibule_roof": _r(BF.p3(-9.1, BC_VC, Z_VEST)),
        "baughman_aisle_ne": _r(BF.p3(9.8, v_n, _bc_aisle_z(9.8, v_n))),
        "baughman_aisle_nw": _r(BF.p3(-7.0, v_n, _bc_aisle_z(-7.0, v_n))),
        "baughman_aisle_se": _r(BF.p3(9.8, -v_n + 2 * BC_VC, _bc_aisle_z(9.8, -v_n + 2 * BC_VC))),
        "baughman_ridge": _r(BF.p3(2.0, BC_VC, Z_RIDGE)),
        "baughman_main_door": _r(BF.p3(BC_L[16][0] - 2.0, BC_L[16][1], 0.0)),
        "baughman_lakeside_lawn": _r(BF.p3(13.5, 4.0, 0.0)),
        "baughman_bridge_mid": _r((*E.xy((t0 + t1) / 2), BR_DECK_Z)),
        "regatta_launch_bridge": _r((*E.xy(E.L * 0.6), BR_DECK_Z)),
        "baughman_bridge_south_foot": _r((*E.xy(t0 - BR_RAMP - 0.3), 0.0)),
        "baughman_bridge_north_foot": _r((*E.xy(t1 + BR_RAMP + 0.3), 0.0)),
    }
    markers = {
        "levels_m": {"aisle_eave": Z_AISLE, "clerestory_base": Z_CLR, "nave_eave": Z_EAVE, "ridge": Z_RIDGE,
                     "vestibule_roof": Z_VEST, "porch_ridge": Z_PORCH_R, "bridge_deck": BR_DECK_Z},
        "climb_note": "lawn -> entry porch eave 2.9 (double jump) -> walk up the porch roof (30 deg) -> "
                      "vestibule roof 3.7 -> north / south aisle roof (31 deg, up to 4.6) -> east end over the "
                      "lake; the nave roof (61 deg) is a slide",
        "axis_deg": 71.24,
        "bridge_axis_m": [_r(p) for p in BRIDGE],
    }
    return {"spots": spots, "markers": markers}


# =================================================================== parts, checks, LANDMARKS
def _parts(slug, vis, col):
    parts = []
    for name, b, collision, visual in ((f"{slug} visual", vis, False, True), (f"{slug} collision", col, True, False)):
        if not b.polys:
            continue
        me, slots = b.build(name)
        p = C.part(name, me, slots, collision=collision, visual=visual)
        p["landmark"] = slug
        parts.append(p)
    print(f"lake_alice_shore: {slug}: visual {vis.tri_count()} tris, collision {col.tri_count()} tris")
    return parts


def _check_osm(ctx):
    """Warn when the embedded OSM coordinates drift from data/uf/campus.json (> 5 cm)."""
    camp = ctx.get("campus") or {}
    by = {}
    for key in ("buildings", "areas", "ways"):
        for e in camp.get(key, []) or []:
            by.setdefault(e["id"], e.get("pts"))
    for oid, ours in ((BARN10_ID, BARN10_OSM), (OLD_HOUSE_ID, OLD_HOUSE_OSM), (BARN17_ID, BARN17_OSM),
                      (FENCE1_ID, FENCE1), (FENCE2_ID, FENCE2), (BAUGHMAN_ID, BAUGHMAN_OSM), (GARDEN_ID, GARDEN),
                      (BRIDGE_ID, BRIDGE), (BW_NORTH_ID, BW_NORTH), (BW_EAST_ID, BW_EAST)):
        pts = by.get(oid)
        if not pts:
            print(f"lake_alice_shore WARNING: OSM {oid} not in campus.json")
            continue
        dev = max(min(math.dist(p, q) for q in pts) for p in ours)
        if dev > 0.05:
            print(f"lake_alice_shore WARNING: OSM {oid} moved {dev:.2f} m from the module's copy")


_BATS = _bats_layout()
_BC = _bc_layout()
_BW = _bw_layout()
_RL = _road_layout()
_FL = _field_layout()

LANDMARKS = [
    {
        "slug": SLUG_BATS,
        "name": "UF Bat Barns (2010 and 2017; the 1991 Bat House site)",
        "osm_ids": [BARN10_ID, OLD_HOUSE_ID, BARN17_ID],
        "stages": list(STAGES),
        "center_m": (-1895.5, -508.5),
        "height_m": 9.0,
        "replaces_areas": [FENCE1_ID, FENCE2_ID],
        "spots": _BATS["spots"],
        "markers": _BATS["markers"],
    },
    {
        "slug": SLUG_BC,
        "name": "Baughman Center",
        "osm_ids": [BAUGHMAN_ID],
        "stages": list(STAGES),
        "center_m": _r(C.centroid(C.ccw(BAUGHMAN_OSM))),
        "height_m": Z_RIDGE,
        "replaces_ways": [BRIDGE_ID],
        "removes_points": list(CLEAR_TREES_BC),
        "spots": _BC["spots"],
        "markers": _BC["markers"],
    },
    {
        "slug": SLUG_BW,
        "name": "Lake Alice boardwalk and east overlook",
        "osm_ids": [],
        "stages": list(STAGES),
        "center_m": _r(((BW_NORTH[0][0] + BW_NORTH[1][0]) / 2, (BW_NORTH[0][1] + BW_NORTH[1][1]) / 2)),
        "replaces_ways": [BW_NORTH_ID, BW_EAST_ID],
        "removes_points": list(CLEAR_TREES_BW),
        "spots": _BW["spots"],
        "markers": _BW["markers"],
    },
    {
        "slug": SLUG_ROAD,
        "name": "Museum Road lake edge",
        "osm_ids": [],
        "stages": list(STAGES),
        "center_m": (-1890.0, -588.0),
        "removes_points": list(CLEAR_TREES_ROAD),
        "spots": _RL["spots"],
        "markers": _RL["markers"],
    },
    {
        "slug": SLUG_FIELD,
        "name": "Bat House field (landing zone) and Bat House Gardens",
        "osm_ids": [],
        "osm_area_ids": [GARDEN_ID],
        "stages": list(STAGES),
        "center_m": (-1893.0, -541.0),
        "spots": _FL["spots"],
        "markers": _FL["markers"],
    },
]


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual", "landmark"}, ...] (map metres)."""
    key = ctx.get("stage_key")
    if key is not None and key not in STAGES:
        return []
    _check_osm(ctx)
    parts = []
    parts += _build_bats(ctx)
    parts += _build_bc(ctx)
    parts += _build_bw(ctx)
    parts += _build_road(ctx)
    parts += _build_field(ctx)
    return parts
