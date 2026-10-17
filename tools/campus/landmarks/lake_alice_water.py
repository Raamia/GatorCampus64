"""Lake Alice: the lake basin, water surface, bog islands, lily pads, bald cypress and marsh edge of the
Lake Alice stage (stages.json "lake_alice", Course 3, slot jrb).

Landmark module contract (landmarks/_common.py): LANDMARKS + build(ctx), geometry in MAP METRES, z up
(x = east, y = north, origin = Century Tower), palette names only, visual and collision parts separate.
Built only into the "lake_alice" stage ("stages": ["lake_alice"]); build() returns [] for any other stage.

SOURCES
  - OpenStreetMap multipolygon relation 1630473 "Lake Alice" (natural=water, water=lake): outer way
    45603512 (137 nodes, 87,610 m2 open water, bbox x -1981.4..-1521.1, y -873.0..-446.9) and three
    inner ways = the bog islands: 45603513 (807 m2, at (-1807, -606)), 45603514 (765 m2, (-1652, -496)),
    118249560 (177 m2, (-1723, -528)). The shoreline used here is the outer way simplified with the
    generator's own rule (stage_planner.simplify_ring, 0.25 m: 130 nodes, every OSM node within 0.25 m),
    which is exactly the lake-shaped hole the generator already cuts into the surrounding woods
    (natural=wood relation 6819273), so the woods' forest floor and this basin meet on the same ring.
    Boardwalks mapped by OSM (bridge=boardwalk, not drawn by the generator): w427713653 (Baughman Center,
    concrete) and w424512414 (north shore, wood): the shore stays at grade around their ends ("landings").
  - Wikipedia "Lake Alice (Gainesville, Florida)": surface ~20 m ASL; Baughman Center on the south-west
    bank; a boardwalk on the north side runs through woods and swamp to a viewing platform; one of the
    few places in Gainesville to see live alligators; Florida softshell turtles; bat houses nearby.
    https://en.wikipedia.org/wiki/Lake_Alice_(Gainesville,_Florida)
  - UF Facilities Services, Lake Alice Conservation Area kiosk: "an 82 acre open water/marsh system",
    a closed basin kept from flooding by drainage wells, an "undeveloped shoreline buffer", wading birds
    and alligators. https://www.facilitiesservices.ufl.edu/wp-content/uploads/2022/10/Lake-Alice-kiosk_v5.pdf
  - WUSF / WUFT "A lake named Alice" (2022): ~10 acres of open water, dark green water, laurel oaks and
    palmettos reflected on calm days; water hyacinth covered the lake shore to shore in the 1960s.
    https://www.wusf.org/environment/2022-09-03/a-lake-named-alice-blooms-and-bureaucracy-imperil-the-university-of-floridas-landmark-campus-lake
  - UF/IFAS Center for Aquatic and Invasive Plants, "Florida's floating islands": tussocks are rafts of
    herbaceous plants growing on top of one another; floating islands rise from peat and decomposing
    vegetation -> the bog islands are low peat hummocks with reeds and a few shrubs.
    https://blogs.ifas.ufl.edu/caip/2021/07/26/floridas-floating-islands/
  - No elevation / bathymetry data: depths below are a gameplay assumption (task brief: ~2.5 m basin).
    Cypress, lily pads and Spanish moss follow game_design.md section 7.4 ("marsh boardwalk, lily pads,
    Spanish moss trees"); pads and trees are enlarged to SM64 scale (real spatterdock pads ~0.3 m).

MODEL (heights relative to the generator's collision ground, z = 0)
  WATER_Z = -0.50 m (water surface, COL_WATER_BOX y = -50). BED_Z = -3.00 m (2.5 m of water) with four
  deeper holes to -4.6 .. -5.0 m (DEEP_SPOTS) and +-0.12 m of lumps. The shore is the OSM ring at grade;
  a hand-shaped bank profile runs inward: grade -> waterline (bank width a) -> shallow shelf (WATER_Z - sd
  at a + sw: wading depth, Mario walks) -> lake bed (a + sw + run). a / sw / sd / run blend between
  shore ZONES: steep wooded north shore under Museum Road, a lily-pad bay between the bogs, cypress
  shallows in the two south arms, a wide reedy marsh shelf on the east lobe (the kiosk's "Lake Alice
  Marsh" lies east), a lawn bank at the Baughman Center. Bog islands: OSM inner rings, edge 0.25 m under
  the water, rising to low peat hummocks ~0.37 m above it; their underwater skirts slope to the bed.
  The basin is one Delaunay mesh (Blender's delaunay_2d_cdt, shore and island rings as constraints)
  with vertex rings at the waterline, the shelf edge and the bed edge, so walking in / out is smooth.
  Visual = the collision mesh 4 cm lower (10 cm at the rim, to meet the woods' forest floor at -0.10).
  Materials: grass on everything that reaches above the water, brown mud (palette "bronze") on the
  shallows, dark mud ("dark_trim") where every corner is on the bed, so the shallow / deep line follows the
  bed-edge vertex ring. Water surface: the whole lake ring at WATER_Z, palette "water" (translucent layer,
  double sided), a Delaunay mesh with a WATER_CELL_M Steiner grid (~230 faces). Lily pads at the surface:
  big collision pads (the hop routes: collision top PAD_TOP_Z = 0.10 m above the water, no side walls, the
  visual leaf 2 cm under it with a thin floating rim, some with a white water lily) and small visual
  colonies; reeds / cattails along the waterline (denser where the shelf is wide) and on the bogs, bushes
  on the bogs; 16 bald cypress (buttressed trunk, knees, three drooping foliage tiers, Spanish moss) in
  the shallows with a 6-sided trunk collider (r CYPRESS_COLLIDER_R, bed -> 4.5 m above the water).
  Built with mathutils.geometry.delaunay_2d_cdt; build() takes ~0.1 s. Counts (this version): collision
  1,728 tris (basin 1,362, hop pads 174, cypress trunks 192); visual ~7,500 (basin 1,362, water 230,
  dressing ~5,900: 29 hop pads, 91 small pads, ~310 reed clumps, 16 cypress, 6 bushes).

GAMEPLAY EXPORTS (LANDMARKS[0]; copied to the build report "landmark_extras" -> "lake_alice_water")
  "spots" (map metres, z = the floor / top a player stands on, or the water surface for "_water" spots):
     lake_center_deck_site (stages.json lake centre, open water 2.5 m deep, kept free of pads / cypress
     within DECK_SITE_FREE_R = 4.5 m: a viewing deck can stand here; the last hop pad's edge is 6.3 m
     from the site, i.e. ~1.8 m from the edge of a 9 m deck),
     lily_route_start / lily_route_end, island_<n>_top / island_<n>_nest (bog island 1 = the "island nest"
     of game_design 7.4 acts 2 and 5), deep_<n>_bed, baughman_landing, north_boardwalk_landing_<w|e>,
     regatta_dock_water (shell-surf start in the water off the Baughman Center lawn).
  "markers":
     "water": {"surface_z_m", "bed_z_m", "deep_z_m", "game_y_units"} (the numbers above),
     "lily_pads": collision pads in hop order [{"route", "i", "pos_m": [x, y, z_top], "r_m"}]: routes
                north_shallows (15 pads, west bog -> deck site, act 1), east_marsh (8), south_arm (6);
                edge gaps 1.3 -> 2.4 m; BUILD_ROUTES drops a route (pads and markers) if another module
                builds that hop,
     "lily_routes": {route: {"from", "to", "pads", "note"}},
     "cypress": [{"pos_m": [x, y, z_bed], "trunk_r_m" (collider), "height_m", "pole_m",
                  "knees_m": [[x, y, z_top], ...]}] (knee tops 0.25-0.55 m above the water: act 6's
                "cypress knee" red coin),
     "poles": bhvPoleGrabbing markers on the cypress trunks, stage_pickups format
              [{"name", "base_m", "height_m"}] (the collider is thin enough for a wading Mario to grab),
     "regatta_buoys_m": 8 open-water points (>= 27 m from every shore and bog) for the act 3 shell-surf
              loop; its 7 -> 8 leg crosses the north_shallows pad line (pads have no walls: a shell
              rides over them),
     "deep_spots_m", "island_rings_m", "island_labels".
  "ground_holes_m": [the shore ring] -> the generator cuts its collision ground and base grass there.
  "water_boxes_m": SM64 water boxes (COL_WATER_BOX) covering the whole lake (see below).

GENERATOR NOTES
  - "replaces_areas": ["rel1630473"] -> stage_ground.py skips the OSM water polygon (no generic pond
    basin at -2.2 m, no pond water, no pond water box) and this module provides everything inside the ring.
  - "water_boxes_m" (contract addition, consumed by stage_ground.py -> S.water_boxes -> build_stage.py,
    which clips boxes to the play zone and writes COL_WATER_BOX): a list of
        {"name": str, "rect_m": [xmin, ymin, xmax, ymax] (map metres), "surface_z": m, "bottom_z": m}
    Here: horizontal strips (WATER_BOX_STRIP_M tall, 1 m overlap so no integer line between two boxes is
    dry: SM64 tests loX < x < hiX strictly) whose x extent covers the lake ring inside the strip + 1.5 m.
    Everything below WATER_Z inside a box is water; outside the ring the ground is at z = 0, above it.
  - Every collision floor is < 30 degrees; the rim overlaps the generator ground (which is cut 6 cm
    smaller, stage_ground.HOLE_OVERLAP_M) and the visual rim sits at the woods' forest floor (-0.10 m).
  - Budget (stages.json lake_alice rel1630473: 450 collision / 2500 visual) was a flat-bed estimate;
    this module prints its real counts (above) and DENSITY lets the integrator thin the dressing.
  - stage_ground.py also skips adding the shore ring to an OSM area that already has it as a hole (the
    woods relation 6819273), so the woods are not triangulated with the same hole twice.
  - Other Lake Alice modules: lake_alice_shore.py (bat barns, Baughman Center + footbridge, the real
    boardwalks, Museum Road edge) works with any surface between -0.6 and 0.0 m; its north boardwalk and
    footbridge ends are this module's LANDINGS (the bank stays at grade there).
Map data (c) OpenStreetMap contributors, ODbL 1.0.
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

SLUG = "lake_alice_water"
STAGE = "lake_alice"
LAKE_REL = "rel1630473"
OUTER_WAY = "w45603512"
ISLAND_WAYS = ["w45603513", "w45603514", "w118249560"]

# =================================================================== OSM geometry (map metres)
# outer way 45603512, simplified like the generator (stage_planner.simplify_ring 0.25 m, ccw, 0.01 m):
# identical to the lake hole of the woods relation 6819273 in the generator's stage data
LAKE_RING = [
    (-1869.70, -616.33), (-1893.91, -608.68), (-1911.15, -611.87), (-1922.31, -616.37), (-1919.39, -624.88),
    (-1919.39, -635.50), (-1925.36, -644.55), (-1937.71, -644.78), (-1940.89, -648.77), (-1936.12, -658.87),
    (-1940.89, -669.22), (-1945.65, -685.63), (-1947.32, -694.54), (-1959.08, -706.40), (-1972.86, -710.78),
    (-1979.03, -711.90), (-1981.40, -720.25), (-1980.37, -725.11), (-1978.03, -728.80), (-1975.30, -730.24),
    (-1970.90, -729.21), (-1970.24, -722.61), (-1968.24, -719.40), (-1964.95, -717.42), (-1946.78, -710.85),
    (-1943.89, -711.22), (-1941.99, -713.80), (-1940.39, -720.91), (-1936.25, -725.48), (-1928.57, -728.30),
    (-1920.66, -728.22), (-1901.25, -726.58), (-1877.44, -730.29), (-1864.96, -743.30), (-1871.42, -760.90),
    (-1870.01, -781.81), (-1867.21, -803.77), (-1872.66, -826.41), (-1872.70, -833.27), (-1869.09, -839.04),
    (-1861.51, -847.65), (-1848.74, -833.80), (-1838.67, -829.33), (-1812.14, -827.20), (-1793.80, -816.32),
    (-1779.24, -811.18), (-1765.40, -823.49), (-1765.18, -842.15), (-1770.18, -854.29), (-1772.30, -868.10),
    (-1764.30, -872.98), (-1738.46, -870.11), (-1716.89, -869.85), (-1701.93, -866.51), (-1687.60, -858.27),
    (-1688.40, -819.24), (-1700.35, -815.53), (-1720.38, -817.12), (-1725.30, -806.50), (-1726.10, -792.16),
    (-1720.52, -771.98), (-1730.93, -766.09), (-1746.80, -751.06), (-1742.01, -721.66), (-1725.57, -708.78),
    (-1694.77, -698.88), (-1661.25, -708.47), (-1646.84, -709.40), (-1635.52, -700.94), (-1625.15, -703.60),
    (-1615.28, -707.06), (-1600.34, -714.11), (-1582.92, -712.44), (-1559.77, -711.20), (-1554.81, -697.75),
    (-1546.62, -691.26), (-1545.58, -679.26), (-1532.73, -672.20), (-1521.11, -674.69), (-1528.16, -661.41),
    (-1537.70, -648.56), (-1544.56, -632.23), (-1540.61, -608.37), (-1556.44, -570.97), (-1565.19, -568.05),
    (-1571.04, -561.15), (-1598.74, -566.01), (-1607.41, -555.04), (-1603.70, -546.28), (-1593.61, -540.70),
    (-1589.23, -525.24), (-1584.58, -513.09), (-1580.33, -498.49), (-1584.01, -478.32), (-1585.91, -464.23),
    (-1597.06, -471.40), (-1601.84, -467.15), (-1626.27, -460.25), (-1630.52, -449.90), (-1650.85, -446.86),
    (-1669.84, -459.05), (-1680.96, -473.80), (-1684.67, -484.67), (-1681.76, -489.99), (-1685.32, -500.57),
    (-1708.21, -514.97), (-1723.19, -513.00), (-1730.71, -511.41), (-1740.44, -510.16), (-1752.65, -511.23),
    (-1753.32, -520.72), (-1773.62, -535.60), (-1792.35, -557.68), (-1803.98, -570.45), (-1817.97, -569.64),
    (-1827.88, -573.73), (-1833.89, -582.39), (-1833.97, -591.49), (-1830.43, -606.73), (-1834.35, -610.37),
    (-1840.02, -609.70), (-1843.71, -603.54), (-1842.61, -600.68), (-1845.73, -594.46), (-1848.58, -595.23),
    (-1848.39, -605.35), (-1845.92, -611.32), (-1843.19, -616.25), (-1848.76, -621.83), (-1854.87, -614.25),
]
# inner ways (the bog islands), raw OSM nodes, ccw, in relation member order
ISLANDS = [
    [(-1803.51, -589.31), (-1808.76, -596.10), (-1815.89, -603.07), (-1822.01, -604.43), (-1828.59, -611.04),
     (-1827.52, -617.10), (-1815.08, -623.39), (-1803.18, -614.42), (-1790.28, -611.90), (-1785.80, -593.95),
     (-1795.61, -589.48)],
    [(-1644.04, -511.12), (-1627.85, -505.42), (-1634.41, -491.85), (-1645.36, -494.48), (-1656.31, -486.15),
     (-1671.20, -482.65), (-1677.77, -494.48), (-1670.76, -503.23), (-1658.06, -503.23)],
    [(-1719.54, -519.79), (-1732.05, -529.31), (-1724.71, -534.89), (-1714.66, -536.11), (-1713.97, -527.00)],
]
ISLAND_LABELS = ["west bog (w45603513, the island nest)", "north-east bog (w45603514)", "small bog (w118249560)"]
# ends of the OSM boardwalks over the lake's inlets (paths w427713647 / w424512412 at the Baughman Center,
# w427713644 / w427713645 on the north shore): the bank stays at grade within r of them
LANDINGS = [  # (x, y, r, name)
    (-1966.35, -708.85, 1.8, "baughman_landing"), (-1962.91, -716.68, 1.8, "baughman_landing_s"),
    (-1847.67, -611.45, 2.2, "north_boardwalk_landing_w"), (-1838.92, -606.13, 2.2, "north_boardwalk_landing_e"),
]

# =================================================================== heights (metres, grade = 0)
WATER_Z = -0.50                 # lake surface: COL_WATER_BOX y = -50
BED_Z = -3.00                   # typical lake bed (2.5 m of water)
ISLAND_EDGE_Z = WATER_Z - 0.25  # bog island shore: 0.25 m under the surface
ISLAND_RISE = 0.62              # peat hummock above its shore (top ~0.37 m above the water)
ISLAND_SKIRT_SLOPE = 0.22       # underwater slope from a bog down to the bed (m per m, ~12 deg)
LANDING_SLOPE = 0.35            # bank below a landing (m per m)
PAD_TOP_Z = WATER_Z + 0.10      # lily-pad platform collision top
PAD_VIS_Z = WATER_Z + 0.08      # its visual top (2 cm under the collision: Mario's shadow stays visible)
DECO_PAD_Z = WATER_Z + 0.05     # small visual pads
VIS_DROP = 0.04                 # visual terrain under the collision terrain
VIS_DROP_RIM = 0.10             # ... at grade (meets the woods' forest floor at -0.10)
# deep holes in the bed: (x, y, radius m, bottom z)
DEEP_SPOTS = [(-1700.0, -605.0, 24.0, -5.0), (-1792.0, -680.0, 20.0, -4.6),
              (-1630.0, -640.0, 22.0, -4.8), (-1880.0, -680.0, 16.0, -4.6)]

# shore character (blended by distance): (x, y, radius m, bank a, shelf sw, shelf depth sd, run, name)
#   a   = grade -> waterline (m)          sw  = waterline -> shelf edge (m, wading depth WATER_Z - sd)
#   run = shelf edge -> lake bed (m)
ZONE_DEFAULT = (2.0, 5.0, 0.45, 8.0)
ZONES = [
    (-1745.0, -520.0, 40.0, 1.3, 1.5, 0.35, 5.0, "north shore under Museum Road (steep, wooded)"),
    (-1615.0, -462.0, 40.0, 1.6, 3.0, 0.40, 6.0, "north-east lobe under Museum Road"),
    (-1790.0, -575.0, 55.0, 2.2, 9.0, 0.50, 10.0, "lily-pad bay between the west bog and the north shore"),
    (-1846.0, -606.0, 22.0, 2.0, 5.0, 0.45, 7.0, "north boardwalk inlet"),
    (-1930.0, -665.0, 45.0, 2.4, 6.0, 0.45, 9.0, "west lobe"),
    (-1962.0, -717.0, 26.0, 3.0, 3.0, 0.40, 6.0, "Baughman Center lawn bank"),
    (-1862.0, -790.0, 55.0, 2.6, 12.0, 0.55, 9.0, "south-west arm (cypress shallows)"),
    (-1730.0, -845.0, 50.0, 2.6, 12.0, 0.55, 9.0, "south arm (cypress shallows)"),
    (-1665.0, -705.0, 45.0, 2.0, 6.0, 0.45, 8.0, "south shore of the main basin"),
    (-1565.0, -640.0, 70.0, 3.5, 18.0, 0.40, 10.0, "east marsh lobe (wide reedy shelf)"),
    (-1600.0, -540.0, 40.0, 2.4, 8.0, 0.45, 8.0, "north-east marsh"),
]
ZONE_BASE_WEIGHT = 0.25

# dressing density (1.0 = as designed; the integrator may thin it for the render budget)
DENSITY = {"reeds": 1.0, "deco_pads": 1.0, "cypress": 1.0}
WATER_CELL_M = 36.0             # water surface Steiner grid (faces stay under ~10 repeats of 6 m)
WATER_BOX_STRIP_M = 54.0        # water box strip height (map y)
WATER_BOX_MARGIN_M = 1.5
WATER_BOX_BOTTOM_Z = -7.0


# =================================================================== small geometry helpers (pure Python)
def _pip(pt, poly):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _seg_d2(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx - px, ay + t * dy - py
    return qx * qx + qy * qy


class _Rings:
    """Distance queries against a set of closed rings (segments binned on a 16 m grid)."""

    def __init__(self, rings, cell=16.0):
        self.cell = cell
        self.segs = []
        for r in rings:
            for a, b in zip(r, r[1:] + r[:1]):
                self.segs.append((a[0], a[1], b[0], b[1]))
        self.grid = {}
        for k, (ax, ay, bx, by) in enumerate(self.segs):
            i0, i1 = int(math.floor(min(ax, bx) / cell)), int(math.floor(max(ax, bx) / cell))
            j0, j1 = int(math.floor(min(ay, by) / cell)), int(math.floor(max(ay, by) / cell))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.grid.setdefault((i, j), []).append(k)

    def dist(self, x, y, cap=80.0):
        """Distance to the nearest segment, exact up to `cap` (returns cap beyond it)."""
        c = self.cell
        ci, cj = int(math.floor(x / c)), int(math.floor(y / c))
        best = cap * cap
        rr = 0
        seen = set()
        while True:
            for i in range(ci - rr, ci + rr + 1):
                for j in range(cj - rr, cj + rr + 1):
                    if max(abs(i - ci), abs(j - cj)) != rr:
                        continue
                    for k in self.grid.get((i, j), ()):
                        if k in seen:
                            continue
                        seen.add(k)
                        d2 = _seg_d2(x, y, *self.segs[k])
                        if d2 < best:
                            best = d2
            # every unvisited segment is at least rr * c away
            if (rr * c) ** 2 >= best or rr * c > cap:
                break
            rr += 1
        return math.sqrt(best)


_OUTER = _Rings([LAKE_RING])
_ISLE = [_Rings([r]) for r in ISLANDS]
_ISLE_BB = [(min(p[0] for p in r), min(p[1] for p in r), max(p[0] for p in r), max(p[1] for p in r)) for r in ISLANDS]
_LAKE_BB = (min(p[0] for p in LAKE_RING), min(p[1] for p in LAKE_RING),
            max(p[0] for p in LAKE_RING), max(p[1] for p in LAKE_RING))


def in_lake(x, y):
    b = _LAKE_BB
    return b[0] <= x <= b[2] and b[1] <= y <= b[3] and _pip((x, y), LAKE_RING)


def island_at(x, y):
    """Index of the bog island containing (x, y), or None."""
    for k, (r, b) in enumerate(zip(ISLANDS, _ISLE_BB)):
        if b[0] <= x <= b[2] and b[1] <= y <= b[3] and _pip((x, y), r):
            return k
    return None


def shore_dist(x, y, cap=80.0):
    return _OUTER.dist(x, y, cap)


def island_dist(x, y, cap=80.0):
    """(distance, index) of the nearest bog island shore."""
    best, bi = cap, None
    for k, R in enumerate(_ISLE):
        b = _ISLE_BB[k]
        if x < b[0] - cap or x > b[2] + cap or y < b[1] - cap or y > b[3] + cap:
            continue
        d = R.dist(x, y, cap)
        if d < best:
            best, bi = d, k
    return best, bi


def zone_params(x, y):
    """Blended bank parameters (a, sw, sd, run) at (x, y)."""
    w0 = ZONE_BASE_WEIGHT
    acc = [w0 * v for v in ZONE_DEFAULT]
    wsum = w0
    for zx, zy, zr, a, sw, sd, run, _ in ZONES:
        d2 = ((x - zx) ** 2 + (y - zy) ** 2) / (zr * zr)
        if d2 > 9.0:
            continue
        w = math.exp(-d2)
        wsum += w
        for i, v in enumerate((a, sw, sd, run)):
            acc[i] += w * v
    return tuple(v / wsum for v in acc)


def bank_profile(d, P):
    """Height of the shore bank at distance d (m) inside the shore, bank parameters P = (a, sw, sd, run).
    Piecewise linear: 0 at the shore, WATER_Z at a, WATER_Z - sd at a + sw, BED_Z at a + sw + run, and
    the same slope further down (the bed function takes over there)."""
    a, sw, sd, run = P
    if d <= 0.0:
        return 0.0
    if d <= a:
        return WATER_Z * d / a
    if d <= a + sw:
        return WATER_Z - sd * (d - a) / sw
    shelf = WATER_Z - sd
    return shelf + (BED_Z - shelf) * (d - a - sw) / run


def bed_z(x, y):
    """Lake bed away from the shores: BED_Z with soft lumps and the DEEP_SPOTS."""
    z = BED_Z + 0.07 * math.sin(x / 23.0 + 1.3) * math.cos(y / 31.0 - 0.4) + 0.05 * math.sin((x + y) / 17.0)
    for dx, dy, r, zb in DEEP_SPOTS:
        q = ((x - dx) ** 2 + (y - dy) ** 2) / (r * r)
        if q < 9.0:
            z += (zb - BED_Z) * math.exp(-q * 1.6)
    return z


def landing_z(x, y):
    best = -99.0
    for lx, ly, r, _ in LANDINGS:
        d = math.hypot(x - lx, y - ly)
        best = max(best, -max(0.0, d - r) * LANDING_SLOPE)
    return best


def island_top_z(x, y, k):
    d = _ISLE[k].dist(x, y, 40.0)
    t = min(1.0, d / 3.5)
    t = t * t * (3.0 - 2.0 * t)
    hum = 0.05 * math.sin(x * 0.9 + k) * math.cos(y * 0.7 - k) + 0.03 * math.sin((x - y) * 0.45)
    return ISLAND_EDGE_Z + ISLAND_RISE * t + hum * t


def terrain_z(x, y, where=None):
    """Collision height of the basin at (x, y) (map metres). where = "shore" / ("island", k) forces the
    exact ring value for a vertex that lies on a ring."""
    if where == "shore":
        return 0.0
    if isinstance(where, tuple):
        return max(ISLAND_EDGE_Z, bank_profile(shore_dist(x, y), zone_params(x, y)))
    k = island_at(x, y)
    if k is not None:
        return island_top_z(x, y, k)
    d_o = shore_dist(x, y)
    z = bank_profile(d_o, zone_params(x, y))
    d_i, _ = island_dist(x, y, 40.0)
    z = max(z, ISLAND_EDGE_Z - ISLAND_SKIRT_SLOPE * d_i, bed_z(x, y), landing_z(x, y))
    return min(z, 0.0)


def water_depth(x, y):
    """Water depth (m) at (x, y); <= 0 on dry bank / island."""
    return WATER_Z - terrain_z(x, y)


# =================================================================== layout (pure Python, at import)
def _h01(*k):
    """Deterministic 0..1 hash."""
    h = 2166136261
    for c in repr(k).encode():
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


def densify_ring(ring, step):
    """Closed ring -> points no more than `step` apart (the original vertices kept)."""
    out = []
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        k = max(1, math.ceil(math.dist(a, b) / step))
        for j in range(k):
            t = j / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def ring_normals(pts):
    """Unit normals to the LEFT of travel (= into a ccw ring) at every vertex of a closed ring."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        nx = ny = 0.0
        for a, b in ((p0, p1), (p1, p2)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1.0
            nx += -dy / L
            ny += dx / L
        L = math.hypot(nx, ny) or 1.0
        out.append((nx / L, ny / L))
    return out


# lily-pad hop routes: pads along `path` (map m), radii[i] and the edge-to-edge gap BEFORE pad i (m);
# pads alternate `zig` m left / right of the path. All pads float at the surface (collision top PAD_TOP_Z).
LILY_ROUTES = [
    {"name": "north_shallows",
     "from": "the west bog's east tip (north boardwalk -> wade onto the west bog -> walk it east)",
     "to": "lake_center_deck_site",
     "path": [(-1784.2, -603.4), (-1769.0, -609.5), (-1757.0, -622.0), (-1748.0, -636.0), (-1734.1, -655.3)],
     "radii": [1.7, 1.5, 1.5, 1.4, 1.4, 2.3, 1.3, 1.3, 1.3, 1.2, 1.2, 1.3, 1.3, 1.2, 3.0],
     "gaps": [0.0, 1.3, 1.4, 1.6, 1.7, 1.6, 1.7, 1.9, 2.0, 2.1, 2.2, 2.3, 2.3, 2.4, 2.4],
     "zig": 0.8,
     "note": "game_design 7.4 act 1 Boardwalk Welcome: 15 pads over 2-2.5 m of water from the west bog to "
             "the open centre (a rest pad half way, a big end pad); edge gaps widen from 1.3 to 2.4 m "
             "(run-up hops); a miss = swim to a pad and climb on (pads have no side walls)"},
    {"name": "east_marsh",
     "from": "the east marsh shelf (wading depth)", "to": "deep_3_bed (east basin)",
     "path": [(-1559.0, -606.0), (-1586.0, -619.0), (-1612.0, -635.0)],
     "radii": [1.7, 1.5, 1.4, 1.4, 1.3, 1.3, 1.2, 1.8],
     "gaps": [0.0, 1.5, 1.7, 1.9, 2.1, 2.3, 2.4, 2.2],
     "zig": 1.1,
     "note": "marsh pads from wading depth out over the east basin's deep hole"},
    {"name": "south_arm",
     "from": "the south-west arm's cypress shallows", "to": "the arm's open water",
     "path": [(-1849.0, -770.0), (-1846.0, -793.0), (-1833.0, -812.0)],
     "radii": [1.5, 1.4, 1.4, 1.3, 1.5, 1.6],
     "gaps": [0.0, 1.6, 1.8, 2.0, 1.8, 1.6],
     "zig": 1.0,
     "note": "pads between the bald cypress of the south-west arm (red coins, a cypress knee)"},
]
# routes whose pads are built and exported (drop a name if another module builds that hop itself)
BUILD_ROUTES = ("north_shallows", "east_marsh", "south_arm")
LAKE_CENTER_DECK_SITE = (-1734.1, -655.3)   # stages.json lake_alice landmark centre: open water, ~2.5 m deep
DECK_SITE_FREE_R = 4.5                       # no pad / cypress / buoy within this radius of the site
# cypress trunk collider radius: small enough that a wading Mario (wall radius 0.5 m) still reaches a
# bhvPoleGrabbing hitbox (0.8 m + his 0.37 m) on the trunk axis, so markers["poles"] make them climbable
CYPRESS_COLLIDER_R = 0.45
REGATTA_BUOYS = [(-1905.0, -672.0), (-1836.0, -752.0), (-1790.0, -706.0), (-1700.0, -672.0),
                 (-1588.0, -666.0), (-1640.0, -585.0), (-1716.0, -575.0), (-1820.0, -650.0)]
REGATTA_DOCK = (-1941.0, -700.5)             # shell-surf start in the water off the Baughman lawn (~0.9 m deep)


def _along(path, s):
    """Point and unit direction at arc length s along a polyline (clamped)."""
    for a, b in zip(path, path[1:]):
        L = math.dist(a, b)
        if s <= L or b == path[-1]:
            t = min(1.0, s / L) if L > 0 else 0.0
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), d
        s -= L
    return path[-1], (1.0, 0.0)


def _pad_at(R, s, i, n):
    (x, y), (dx, dy) = _along(R["path"], s)
    side = 0.0 if i in (0, n - 1) else R["zig"] * (1 if i % 2 else -1)
    return x - dy * side, y + dx * side


def lily_pads():
    """Collision lily pads in hop order: [{"route", "i", "pos_m": (x, y, top z), "r_m"}]. Pad i sits on the
    route path (zig-zagging) so that its EDGE gap to pad i - 1 is exactly gaps[i]."""
    out = []
    for R in LILY_ROUTES:
        if R["name"] not in BUILD_ROUTES:
            continue
        radii, gaps = R["radii"], R["gaps"]
        n = len(radii)
        s = 0.0
        prev = _pad_at(R, 0.0, 0, n)
        pts = [prev]
        for i in range(1, n):
            want = radii[i - 1] + gaps[i] + radii[i]
            lo, hi = s, s + want * 2.0
            for _ in range(40):           # arc length whose pad is `want` metres from the previous pad
                mid = (lo + hi) / 2
                if math.dist(_pad_at(R, mid, i, n), prev) < want:
                    lo = mid
                else:
                    hi = mid
            s = hi
            prev = _pad_at(R, s, i, n)
            pts.append(prev)
        for i, ((x, y), r) in enumerate(zip(pts, radii)):
            out.append({"route": R["name"], "i": i, "pos_m": (round(x, 2), round(y, 2), PAD_TOP_Z), "r_m": r})
    return out


def shore_samples(step=6.0):
    """Points along the shore ring with inward normals and blended bank parameters."""
    pts = densify_ring(LAKE_RING, step)
    return [(p, n, zone_params(*p)) for p, n in zip(pts, ring_normals(pts))]


def cypress_sites(pads):
    """Bald cypress in the shallows: on the shelf of the marshy zones (sw >= 7 m), 0.2-0.9 m of water,
    >= 22 m apart, clear of lily pads, landings and the deck site. Deterministic."""
    cands = []
    for k, ((x, y), (nx, ny), P) in enumerate(shore_samples(5.0)):
        a, sw, sd, run = P
        if sw < 7.0:
            continue
        f = 0.35 + 0.4 * _h01("cyf", k)
        cx, cy = x + nx * (a + sw * f), y + ny * (a + sw * f)
        if not in_lake(cx, cy) or island_at(cx, cy) is not None:
            continue
        dep = water_depth(cx, cy)
        if not 0.2 <= dep <= 0.9 or shore_dist(cx, cy) < 3.0:
            continue
        cands.append((_h01("cy", k), cx, cy))
    # postcard trees: the lawn bank at the Baughman Center and the north boardwalk inlet
    extra = [(-1949.0, -706.0), (-1925.0, -724.5), (-1852.0, -617.5)]
    out = []
    for x, y in extra + [(cx, cy) for _, cx, cy in sorted(cands)]:
        if len(out) >= int(round(16 * DENSITY["cypress"])):
            break
        if any(math.dist((x, y), (q[0], q[1])) < 22.0 for q in out):
            continue
        if any(math.dist((x, y), p["pos_m"][:2]) < p["r_m"] + 3.0 for p in pads):
            continue
        if any(math.dist((x, y), (lx, ly)) < lr + 2.5 for lx, ly, lr, _ in LANDINGS):
            continue
        if math.dist((x, y), LAKE_CENTER_DECK_SITE) < 30.0:
            continue
        out.append((round(x, 2), round(y, 2)))
    trees = []
    for k, (x, y) in enumerate(out):
        zb = terrain_z(x, y)
        h = 13.0 + 5.0 * _h01("cyh", k)
        knees = []
        for j in range(3):
            ang = 2 * math.pi * (j / 3 + 0.2 * _h01("kn", k, j))
            rr = 1.6 + 1.0 * _h01("knr", k, j)
            kx, ky = x + math.cos(ang) * rr, y + math.sin(ang) * rr
            kz = max(WATER_Z, terrain_z(kx, ky)) + 0.25 + 0.3 * _h01("knh", k, j)   # pokes out of water / mud
            knees.append((round(kx, 2), round(ky, 2), round(kz, 2)))
        trees.append({"pos_m": (x, y, round(zb, 2)), "trunk_r_m": CYPRESS_COLLIDER_R, "height_m": round(h, 1),
                      "pole_m": round(min(12.0, 0.5 * h), 1), "knees_m": knees})
    return trees


def water_boxes():
    """SM64 water boxes over the lake: horizontal strips (map y), each covering the ring inside it."""
    x0, y0, x1, y1 = _LAKE_BB
    n = max(1, math.ceil((y1 - y0) / WATER_BOX_STRIP_M))
    h = (y1 - y0) / n
    out = []
    for k in range(n):
        sy0 = y0 + k * h - (WATER_BOX_MARGIN_M if k == 0 else 0.5)
        sy1 = y0 + (k + 1) * h + (WATER_BOX_MARGIN_M if k == n - 1 else 0.5)
        xs = []
        for a, b in zip(LAKE_RING, LAKE_RING[1:] + LAKE_RING[:1]):
            for p in (a, b):
                if sy0 <= p[1] <= sy1:
                    xs.append(p[0])
            for yy in (sy0, sy1):
                if (a[1] - yy) * (b[1] - yy) < 0:
                    xs.append(a[0] + (b[0] - a[0]) * (yy - a[1]) / (b[1] - a[1]))
        if not xs:
            continue
        out.append({"name": f"Lake Alice {k + 1}",
                    "rect_m": [round(min(xs) - WATER_BOX_MARGIN_M, 2), round(sy0, 2),
                               round(max(xs) + WATER_BOX_MARGIN_M, 2), round(sy1, 2)],
                    "surface_z": WATER_Z, "bottom_z": WATER_BOX_BOTTOM_Z})
    return out


def _island_top_spot(k):
    """The point of bog island k farthest from its shore (1 m grid): the middle of its flat hummock top."""
    b = _ISLE_BB[k]
    best = None
    for i in range(int(b[0]) - 1, int(b[2]) + 2):
        for j in range(int(b[1]) - 1, int(b[3]) + 2):
            x, y = i + 0.5, j + 0.5
            if island_at(x, y) != k:
                continue
            d = _ISLE[k].dist(x, y, 40.0)
            if best is None or d > best[0]:
                best = (d, x, y)
    _, x, y = best
    return (round(x, 2), round(y, 2), round(island_top_z(x, y, k), 2))


def _layout():
    pads = lily_pads()
    trees = cypress_sites(pads)
    spots = {"lake_center_deck_site": (LAKE_CENTER_DECK_SITE[0], LAKE_CENTER_DECK_SITE[1],
                                       round(terrain_z(*LAKE_CENTER_DECK_SITE), 2)),
             "lake_center_deck_site_water": (LAKE_CENTER_DECK_SITE[0], LAKE_CENTER_DECK_SITE[1], WATER_Z)}
    hop = [p for p in pads if p["route"] == "north_shallows"]
    if hop:
        spots["lily_route_start"] = hop[0]["pos_m"]
        spots["lily_route_end"] = hop[-1]["pos_m"]
    for k in range(len(ISLANDS)):
        top = _island_top_spot(k)
        spots[f"island_{k + 1}_top"] = top
        if k == 0:
            spots["island_1_nest"] = top
    for k, (x, y, r, zb) in enumerate(DEEP_SPOTS):
        spots[f"deep_{k + 1}_bed"] = (x, y, round(terrain_z(x, y), 2))
    for x, y, r, name in LANDINGS:
        spots[name] = (x, y, 0.0)
    spots["regatta_dock_water"] = (REGATTA_DOCK[0], REGATTA_DOCK[1], WATER_Z)
    markers = {
        "water": {"surface_z_m": WATER_Z, "bed_z_m": BED_Z, "deep_z_m": min(d[3] for d in DEEP_SPOTS),
                  "game_y_units": int(round(WATER_Z * 100)),
                  "note": "SM64 water boxes = LANDMARKS water_boxes_m; Mario walks where the water is < 0.8 m "
                          "deep (the bank and shelf), swims elsewhere"},
        "lily_pads": [dict(p, pos_m=list(p["pos_m"])) for p in pads],
        "lily_routes": {R["name"]: {"from": R["from"], "to": R["to"], "pads": len(R["radii"]), "note": R["note"]}
                        for R in LILY_ROUTES},
        "cypress": [dict(t, pos_m=list(t["pos_m"]), knees_m=[list(k) for k in t["knees_m"]]) for t in trees],
        # bhvPoleGrabbing objects on the cypress trunks (stage_pickups format: base on the lake bed / bank)
        "poles": [{"name": f"cypress_{k + 1}", "base_m": list(t["pos_m"]), "height_m": t["pole_m"]}
                  for k, t in enumerate(trees)],
        "regatta_buoys_m": [[x, y, WATER_Z] for x, y in REGATTA_BUOYS],
        "deep_spots_m": [[x, y, round(terrain_z(x, y), 2)] for x, y, _, _ in DEEP_SPOTS],
        "island_rings_m": [[list(p) for p in r] for r in ISLANDS],
        "island_labels": ISLAND_LABELS,
    }
    return pads, trees, spots, markers


_PADS, _TREES, _SPOTS, _MARKERS = _layout()

LANDMARKS = [
    {
        "slug": SLUG,
        "name": "Lake Alice (basin, water, bog islands, lily pads, cypress)",
        "stages": [STAGE],
        "osm_ids": [],
        "osm_area_ids": [LAKE_REL],
        "replaces_areas": [LAKE_REL],
        "center_m": (-1734.1, -655.3),
        "doors": [],
        "ground_holes_m": [list(LAKE_RING)],
        "water_boxes_m": water_boxes(),
        "spots": _SPOTS,
        "markers": _MARKERS,
    },
]


# =================================================================== mesh building (Blender)
SHORE_STEP_M = 12.0          # shore ring vertex spacing (basin mesh)
ISLAND_STEP_M = 4.0
FILL_STEP_M = 22.0
TILE_M = {"grass": 4.0, "bronze": 4.0, "dark_trim": 4.0, "water": 6.0, "door_wood": 2.0, "concrete": 2.0,
          "copper_green": 2.0, "white_trim": 1.0}
DECO_COLONIES = [  # (x, y, radius m, weight): calm shallows where the small pads gather
    (-1785.0, -575.0, 26.0, 1.0), (-1818.0, -628.0, 14.0, 0.8), (-1850.0, -805.0, 22.0, 0.9),
    (-1745.0, -848.0, 20.0, 0.9), (-1572.0, -650.0, 30.0, 1.0), (-1622.0, -488.0, 20.0, 0.8),
    (-1928.0, -690.0, 18.0, 0.7), (-1700.0, -700.0, 16.0, 0.5), (-1740.0, -530.0, 14.0, 0.6),
]
DECO_PAD_COUNT = 90
SHRUBS = [(0, -1806.0, -604.0), (0, -1795.0, -600.0), (0, -1817.0, -613.0), (1, -1662.0, -494.0),
          (1, -1648.0, -499.0), (2, -1723.0, -528.0)]


class _Mesh:
    """Polygons with shared vertices (smooth terrain) or per-face vertices; palette materials, explicit UVs."""

    def __init__(self):
        self.faces = []          # (pts3, material, uvs, smooth)

    def add(self, pts3, mat, uvs=None, smooth=False):
        if mat not in C.PALETTE:
            raise ValueError(f"unknown palette material {mat!r}")
        if uvs is None:
            uvs = C.project_uv(pts3, TILE_M.get(mat, C.PALETTE[mat]["tile_m"]))
        self.faces.append(([tuple(float(c) for c in p) for p in pts3], mat, list(uvs), smooth))

    def tri2(self, pts3, mat, uvs=None):
        """Double-sided polygon (reed blades, moss strands)."""
        self.add(pts3, mat, uvs)
        self.add(list(reversed(pts3)), mat, list(reversed(uvs)) if uvs else None)

    def tris(self):
        return sum(len(f[0]) - 2 for f in self.faces)

    def build(self, name, share=False):
        import bmesh
        import bpy
        slots = []
        for _, m, _, _ in self.faces:
            if m not in slots:
                slots.append(m)
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        cache = {}

        def vert(p):
            if not share:
                return bm.verts.new(p)
            k = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
            v = cache.get(k)
            if v is None:
                v = cache[k] = bm.verts.new(p)
            return v
        for pts, m, uvs, smooth in self.faces:
            try:
                f = bm.faces.new([vert(p) for p in pts])
            except ValueError:
                try:   # same vertex set twice (a double-sided face): fresh vertices
                    f = bm.faces.new([bm.verts.new(p) for p in pts])
                except ValueError:
                    continue
            f.material_index = slots.index(m)
            f.smooth = smooth
            for loop, uv in zip(f.loops, uvs):
                loop[uvl].uv = uv
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bm.to_mesh(me)
        bm.free()
        return me, slots


class _Spacer:
    """Minimum-separation test for scattered points (hash grid)."""

    def __init__(self, cell=4.0):
        self.cell = cell
        self.g = {}

    def ok(self, x, y, sep):
        c = self.cell
        r = int(math.ceil(sep / c))
        ci, cj = int(math.floor(x / c)), int(math.floor(y / c))
        for i in range(ci - r, ci + r + 1):
            for j in range(cj - r, cj + r + 1):
                for (px, py) in self.g.get((i, j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < sep * sep:
                        return False
        return True

    def add(self, x, y):
        self.g.setdefault((int(math.floor(x / self.cell)), int(math.floor(y / self.cell))), []).append((x, y))


def basin_points():
    """-> (outer ring points, island rings, interior points). The outer ring is the CDT face constraint
    (ccw), island rings are edge constraints; interior points sit on the bank profile's breakpoints
    (waterline, shelf edge, bed edge), on the bogs and their skirts, at the landings and deep holes, and on
    a coarse fill grid."""
    outer = densify_ring(LAKE_RING, SHORE_STEP_M)
    isl = [densify_ring(r, ISLAND_STEP_M) for r in ISLANDS]
    sp = _Spacer(4.0)
    for p in outer:
        sp.add(*p)
    for r in isl:
        for p in r:
            sp.add(*p)
    pts = []

    def take(x, y, sep):
        if sp.ok(x, y, sep):
            sp.add(x, y)
            pts.append((x, y))
            return True
        return False
    # bank breakpoints
    for (x, y), (nx, ny) in zip(outer, ring_normals(outer)):
        a, sw, sd, run = zone_params(x, y)
        for off, sep in ((a, 3.4), (a + sw, 5.0), (a + sw + run, 9.0)):
            qx, qy = x + nx * off, y + ny * off
            if not in_lake(qx, qy) or island_at(qx, qy) is not None:
                continue
            if island_dist(qx, qy, 10.0)[0] < 1.2 or shore_dist(qx, qy) < 0.7 * off:
                continue
            take(qx, qy, sep)
    # landings: keep the plateau's edge in the mesh
    for lx, ly, lr, _ in LANDINGS:
        for rr in (lr, lr + 2.0):
            for k in range(6):
                a = 2 * math.pi * (k + 0.5) / 6
                qx, qy = lx + math.cos(a) * rr, ly + math.sin(a) * rr
                if in_lake(qx, qy) and shore_dist(qx, qy) > 0.5 and island_at(qx, qy) is None:
                    take(qx, qy, 1.2)
    # bogs: skirt outside, rise inside, a few interior points
    for k, r in enumerate(isl):
        for (x, y), (nx, ny) in zip(r, ring_normals(r)):
            for off, sep in ((-2.5, 2.2), (-8.0, 4.5), (1.55, 1.8), (3.4, 2.4)):
                qx, qy = x + nx * off, y + ny * off
                if off < 0:
                    if not in_lake(qx, qy) or island_at(qx, qy) is not None or shore_dist(qx, qy) < 1.5:
                        continue
                    if island_dist(qx, qy, 20.0)[0] < 0.7 * -off:
                        continue
                else:
                    if island_at(qx, qy) != k or _ISLE[k].dist(qx, qy, 20.0) < 0.6 * off:
                        continue
                take(qx, qy, sep)
        b = _ISLE_BB[k]
        y = b[1] + 2.0
        while y < b[3]:
            x = b[0] + 2.0
            while x < b[2]:
                if island_at(x, y) == k and _ISLE[k].dist(x, y, 20.0) > 3.5:
                    take(x, y, 3.0)
                x += 4.0
            y += 4.0
    # deep holes
    for dx, dy, r, _ in DEEP_SPOTS:
        take(dx, dy, 4.0)
        for k in range(6):
            a = 2 * math.pi * k / 6
            take(dx + math.cos(a) * r * 0.6, dy + math.sin(a) * r * 0.6, 5.0)
    # coarse fill
    x0, y0, x1, y1 = _LAKE_BB
    j = 0
    y = y0 + FILL_STEP_M / 2
    while y < y1:
        x = x0 + FILL_STEP_M / 2
        i = 0
        while x < x1:
            jx = x + (_h01("fx", i, j) - 0.5) * 6.0
            jy = y + (_h01("fy", i, j) - 0.5) * 6.0
            if in_lake(jx, jy) and island_at(jx, jy) is None and island_dist(jx, jy, 10.0)[0] > 6.0 \
                    and shore_dist(jx, jy) > 12.0:
                take(jx, jy, 13.0)
            x += FILL_STEP_M
            i += 1
        y += FILL_STEP_M
        j += 1
    return outer, isl, pts


def basin_triangles():
    """Delaunay mesh of the basin -> (verts [(x, y, z)], tris [(i, j, k)] ccw, tags per vert)."""
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    outer, isl, inner = basin_points()
    coords, tags = [], []
    for p in outer:
        coords.append(p)
        tags.append("shore")
    edges = []
    for k, r in enumerate(isl):
        base = len(coords)
        for p in r:
            coords.append(p)
            tags.append(("island", k))
        edges += [(base + i, base + (i + 1) % len(r)) for i in range(len(r))]
    for p in inner:
        coords.append(p)
        tags.append(None)
    face = list(range(len(outer)))
    vout, _eout, fout, orig_v, _oe, _of = delaunay_2d_cdt([Vector(p) for p in coords], edges, [face], 1, 1e-5, True)
    verts, vtags = [], []
    for v, ov in zip(vout, orig_v):
        tag = tags[ov[0]] if ov else None
        x, y = float(v.x), float(v.y)
        verts.append((x, y, terrain_z(x, y, tag)))
        vtags.append(tag)
    tris = []
    for f in fout:
        if len(f) < 3:
            continue
        for k in range(1, len(f) - 1):
            a, b, c = f[0], f[k], f[k + 1]
            (ax, ay, _), (bx, by, _), (cx, cy, _) = verts[a], verts[b], verts[c]
            ar = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
            if abs(ar) < 1e-6:
                continue
            tris.append((a, b, c) if ar > 0 else (a, c, b))
    return verts, tris, vtags


def _vis_z(z):
    return z - (VIS_DROP_RIM if z > -0.02 else VIS_DROP)


def _tri_material(pts, inside_island):
    """Grass on anything that reaches above the water (no mud teeth on the banks), dark mud only where
    every corner is on the lake bed (the boundary follows the bed-edge vertex ring), brown mud between."""
    zmax = max(p[2] for p in pts)
    if inside_island:
        return "grass" if zmax > WATER_Z + 0.02 else "bronze"
    if zmax > WATER_Z + 0.08:
        return "grass"
    if zmax <= WATER_Z - 1.45:
        return "dark_trim"
    return "bronze"


def water_surface(mesh):
    """The lake surface at WATER_Z ("water": translucent, double sided): a Delaunay mesh of the shore ring
    with Steiner points on a WATER_CELL_M grid, so faces stay small enough for the N64 UV range."""
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    c = WATER_CELL_M
    pts = list(LAKE_RING)
    x0, y0, x1, y1 = _LAKE_BB
    for i in range(int(math.floor(x0 / c)), int(math.ceil(x1 / c)) + 1):
        for j in range(int(math.floor(y0 / c)), int(math.ceil(y1 / c)) + 1):
            x, y = i * c, j * c
            if in_lake(x, y) and shore_dist(x, y) > c * 0.3:
                pts.append((x, y))
    vout, _e, fout, _ov, _oe, _of = delaunay_2d_cdt([Vector(p) for p in pts], [],
                                                     [list(range(len(LAKE_RING)))], 1, 1e-5, False)
    t6 = TILE_M["water"]
    n = 0
    for f in fout:
        for k in range(1, len(f) - 1):
            t = [(float(vout[i].x), float(vout[i].y)) for i in (f[0], f[k], f[k + 1])]
            ar = (t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])
            if abs(ar) < 1e-6:
                continue
            if ar < 0:
                t = [t[0], t[2], t[1]]
            mesh.add([(x, y, WATER_Z) for x, y in t], "water", [(x / t6, y / t6) for x, y in t])
            n += 1
    return n


def _disc(x, y, r, n, a0=0.0, notch=0.0):
    """Rim points of a disc (ccw); with a notch: a lily-pad wedge cut of `notch` radians at angle a0."""
    if notch <= 0:
        return [(x + r * math.cos(a0 + 2 * math.pi * k / n), y + r * math.sin(a0 + 2 * math.pi * k / n))
                for k in range(n)]
    return [(x + r * math.cos(a0 + notch / 2 + (2 * math.pi - notch) * k / (n - 1)),
             y + r * math.sin(a0 + notch / 2 + (2 * math.pi - notch) * k / (n - 1))) for k in range(n)]


def lily_pad_visual(mesh, x, y, r, z, seed, rim=True, n=12, flower=False):
    a0 = 2 * math.pi * _h01("pad", seed)
    rim_pts = _disc(x, y, r, n, a0, notch=0.42)
    c = (x, y, z)
    tu = 1.5
    for p, q in zip(rim_pts, rim_pts[1:]):
        tri = [c, (p[0], p[1], z), (q[0], q[1], z)]
        mesh.add(tri, "grass", [(t[0] / tu, t[1] / tu) for t in tri])
    if rim:   # thin side band (outward), so the pad reads as a floating leaf from low angles
        zb = WATER_Z - 0.04
        ring = [(x, y)] + rim_pts + [(x, y)]
        for p, q in zip(ring, ring[1:]):
            L = math.dist(p, q)
            if L < 1e-3:
                continue
            mesh.add([(p[0], p[1], zb), (q[0], q[1], zb), (q[0], q[1], z), (p[0], p[1], z)], "grass",
                     [(0, 0), (L / tu, 0), (L / tu, 0.1), (0, 0.1)])
    if flower:   # a white water lily: an open cup of five petals (double sided)
        a = 2 * math.pi * _h01("fl", seed)
        fx, fy = x + 0.45 * r * math.cos(a), y + 0.45 * r * math.sin(a)
        c0 = (fx, fy, z + 0.04)
        for k in range(5):
            b = a + 2 * math.pi * k / 5
            l = (fx + 0.38 * math.cos(b - 0.33), fy + 0.38 * math.sin(b - 0.33), z + 0.2)
            rr = (fx + 0.38 * math.cos(b + 0.33), fy + 0.38 * math.sin(b + 0.33), z + 0.2)
            mesh.tri2([c0, l, rr], "white_trim", [(0.5, 0), (0, 1), (1, 1)])


def lily_pad_collision(mesh, x, y, r):
    mesh.add([(px, py, PAD_TOP_Z) for px, py in _disc(x, y, r * 0.96, 8, math.pi / 8)], "grass",
             [(0, 0)] * 8)


def deco_pads(pads, trees):
    """Small visual pads in colonies: [(x, y, r, flower)]. Deterministic."""
    out = []
    sp = _Spacer(3.0)
    blocked = [(p["pos_m"][0], p["pos_m"][1], p["r_m"] + 1.2) for p in pads]
    blocked += [(t["pos_m"][0], t["pos_m"][1], 2.5) for t in trees]
    blocked.append((LAKE_CENTER_DECK_SITE[0], LAKE_CENTER_DECK_SITE[1], DECK_SITE_FREE_R + 1.0))
    blocked += [(lx, ly, lr + 2.0) for lx, ly, lr, _ in LANDINGS]
    target = int(round(DECO_PAD_COUNT * DENSITY["deco_pads"]))
    wsum = sum(c[3] for c in DECO_COLONIES)
    k = 0
    for ci, (cx, cy, cr, w) in enumerate(DECO_COLONIES):
        want = int(round(target * w / wsum))
        got = tries = 0
        while got < want and tries < want * 30:
            tries += 1
            k += 1
            a = 2 * math.pi * _h01("dpa", ci, tries)
            rr = cr * math.sqrt(_h01("dpr", ci, tries))
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            r = 0.45 + 0.55 * _h01("dps", ci, tries)
            if not in_lake(x, y) or island_at(x, y) is not None:
                continue
            dep = water_depth(x, y)
            if not 0.35 <= dep <= 2.6 or shore_dist(x, y) < r + 0.8 or island_dist(x, y, 10.0)[0] < r + 0.4:
                continue
            if any(math.hypot(x - bx, y - by) < br + r for bx, by, br in blocked):
                continue
            if not sp.ok(x, y, 2 * r + 0.25):
                continue
            sp.add(x, y)
            out.append((x, y, r, _h01("dpf", ci, tries) < 0.16))
            got += 1
    return out


def reed_clumps(pads, trees):
    """Reed / cattail clumps along the waterline (denser where the shelf is wide) and on the bogs."""
    out = []
    sp = _Spacer(3.0)
    keep_clear = [(p["pos_m"][0], p["pos_m"][1], p["r_m"] + 1.0) for p in pads]
    keep_clear += [(lx, ly, lr + 3.5) for lx, ly, lr, _ in LANDINGS]
    keep_clear += [(t["pos_m"][0], t["pos_m"][1], 1.8) for t in trees]
    dens = DENSITY["reeds"]
    for k, ((x, y), (nx, ny), P) in enumerate(shore_samples(4.5)):
        a, sw, sd, run = P
        p = min(0.85, 0.06 + sw / 20.0) * dens
        if _h01("rd", k) > p:
            continue
        off = a * (0.75 + 0.6 * _h01("ro", k))
        qx, qy = x + nx * off + (_h01("rx", k) - 0.5), y + ny * off + (_h01("ry", k) - 0.5)
        if not in_lake(qx, qy) or island_at(qx, qy) is not None or shore_dist(qx, qy) < 0.6:
            continue
        if any(math.hypot(qx - cx, qy - cy) < cr for cx, cy, cr in keep_clear) or not sp.ok(qx, qy, 1.6):
            continue
        sp.add(qx, qy)
        out.append((qx, qy, k))
    for i, r in enumerate(ISLANDS):
        ring = densify_ring(r, 3.0)
        for k, ((x, y), (nx, ny)) in enumerate(zip(ring, ring_normals(ring))):
            if _h01("ri", i, k) > 0.6 * dens:
                continue
            off = 0.5 + 1.2 * _h01("rio", i, k)
            qx, qy = x + nx * off, y + ny * off
            if island_at(qx, qy) != i or not sp.ok(qx, qy, 1.4):
                continue
            sp.add(qx, qy)
            out.append((qx, qy, 10000 * (i + 1) + k))
        b = _ISLE_BB[i]
        j = 0
        y = b[1] + 1.0
        while y < b[3]:
            x = b[0] + 1.0
            while x < b[2]:
                j += 1
                qx, qy = x + (_h01("rgx", i, j) - 0.5) * 2.0, y + (_h01("rgy", i, j) - 0.5) * 2.0
                if island_at(qx, qy) == i and _h01("rg", i, j) < 0.45 * dens and sp.ok(qx, qy, 1.8) \
                        and all(math.hypot(qx - sx, qy - sy) > 1.8 for si, sx, sy in SHRUBS) \
                        and math.dist((qx, qy), _island_top_spot(i)[:2]) > 2.5:
                    sp.add(qx, qy)
                    out.append((qx, qy, 20000 * (i + 1) + j))
                x += 3.5
            y += 3.5
    return out


def reed_clump_visual(mesh, x, y, seed):
    zb = min(terrain_z(x, y), WATER_Z) - 0.05
    nb = 2 + int(_h01("nb", seed) < 0.6)
    cat = _h01("cat", seed) < 0.3
    for b in range(nb):
        a = 2 * math.pi * (b / nb + 0.25 * _h01("ba", seed, b))
        ox, oy = x + 0.22 * math.cos(a), y + 0.22 * math.sin(a)
        h = WATER_Z + 1.1 + 0.9 * _h01("bh", seed, b)
        lean = 0.15 + 0.3 * _h01("bl", seed, b)
        w = 0.07 + 0.04 * _h01("bw", seed, b)
        px, py = -math.sin(a) * w, math.cos(a) * w
        tip = (ox + math.cos(a) * lean, oy + math.sin(a) * lean, h)
        tri = [(ox - px, oy - py, zb), (ox + px, oy + py, zb), tip]
        mesh.tri2(tri, "grass", [(0.0, 0.0), (0.12, 0.0), (0.06, 0.6)])
        if cat and b == 0:   # cattail: a brown head on its own stalk, above the blades
            cx, cy = ox + math.cos(a) * 0.12, oy + math.sin(a) * 0.12
            hz0, hz1 = h + 0.05, h + 0.35
            mesh.tri2([(cx - px * 0.4, cy - py * 0.4, zb), (cx + px * 0.4, cy + py * 0.4, zb), (cx, cy, hz1 + 0.12)],
                      "grass", [(0.0, 0.0), (0.05, 0.0), (0.03, 0.6)])
            tri3 = _disc(cx, cy, 0.05, 3, a)
            for p, q in zip(tri3, tri3[1:] + tri3[:1]):
                mesh.add([(p[0], p[1], hz0), (q[0], q[1], hz0), (q[0], q[1], hz1), (p[0], p[1], hz1)], "bronze",
                         [(0, 0), (0.2, 0), (0.2, 0.35), (0, 0.35)])


def _frustum(mesh, x, y, z0, z1, r0, r1, n, mat, a0=0.0, tile=2.0):
    b = _disc(x, y, r0, n, a0)
    t = _disc(x, y, r1, n, a0)
    u = 0.0
    for i in range(n):
        j = (i + 1) % n
        L = math.dist(b[i], b[j])
        mesh.add([(b[i][0], b[i][1], z0), (b[j][0], b[j][1], z0), (t[j][0], t[j][1], z1), (t[i][0], t[i][1], z1)],
                 mat, [(u, z0 / tile), (u + L / tile, z0 / tile), (u + L / tile, z1 / tile), (u, z1 / tile)])
        u += L / tile


def _blob(mesh, x, y, zc, r, th_up, th_dn, n, mat, seed, droop=0.0):
    """Low-poly foliage pad: an n-gon ring (radius jittered, `droop` m lower than the centre) with an apex
    above and below."""
    ring = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.3 * _h01("bj", seed, k)) / n
        rr = r * (0.82 + 0.3 * _h01("br", seed, k))
        ring.append((x + rr * math.cos(a), y + rr * math.sin(a), zc - droop + (_h01("bz", seed, k) - 0.5) * 0.4))
    top, bot = (x, y, zc + th_up), (x, y, zc - th_dn)
    for p, q in zip(ring, ring[1:] + ring[:1]):
        mesh.add([p, q, top], mat)
        mesh.add([q, p, bot], mat)
    return ring


def cypress_visual(mesh, t, k):
    x, y, zb = t["pos_m"]
    H = t["height_m"] + WATER_Z
    zw = WATER_Z
    # flared, buttressed base -> straight trunk
    _frustum(mesh, x, y, zb - 0.2, zw + 0.9, 1.25, 0.62, 6, "door_wood", a0=0.3 * k)
    _frustum(mesh, x, y, zw + 0.9, H - 1.0, 0.62, 0.24, 6, "door_wood", a0=0.3 * k)
    # three layered crowns of feathery foliage, leaning a little; Spanish moss hanging under each
    lean = 2 * math.pi * _h01("lean", k)
    for i, (f, r, tu, td) in enumerate(((0.55, 3.0, 1.7, 0.9), (0.72, 2.5, 1.6, 0.8), (0.88, 1.8, 1.8, 0.7))):
        zc = zw + (H - zw) * f
        ox, oy = x + math.cos(lean) * 0.5 * i, y + math.sin(lean) * 0.5 * i
        ring = _blob(mesh, ox, oy, zc, r, tu, td, 7, "grass", (k, i), droop=0.35)
        for j in (0, 2, 4):
            if _h01("moss", k, i, j) > 0.85:
                continue
            p = ring[j]
            mx, my = ox + (p[0] - ox) * 0.72, oy + (p[1] - oy) * 0.72
            L = 1.3 + 1.3 * _h01("ml", k, i, j)
            a = math.atan2(my - oy, mx - ox)
            px, py = -math.sin(a) * 0.4, math.cos(a) * 0.4
            z0 = zc - 0.55
            sway = 0.25 * (_h01("ms", k, i, j) - 0.5)
            mesh.tri2([(mx - px, my - py, z0), (mx + px, my + py, z0),
                       (mx + px * 0.25 + sway, my + py * 0.25, z0 - L), (mx - px * 0.25 + sway, my - py * 0.25, z0 - L)],
                      "concrete", [(0, 0), (0.4, 0), (0.3, 0.9), (0.1, 0.9)])
    # knees poking out of the water around the trunk
    for (kx, ky, kz) in t["knees_m"]:
        base = _disc(kx, ky, 0.2, 4, 0.4 * k)
        kb = min(terrain_z(kx, ky), WATER_Z) - 0.1
        for p, q in zip(base, base[1:] + base[:1]):
            mesh.add([(p[0], p[1], kb), (q[0], q[1], kb), (kx, ky, kz)], "door_wood")


def cypress_collision(mesh, t):
    x, y, zb = t["pos_m"]
    ring = _disc(x, y, t["trunk_r_m"], 6, 0.0)
    z1 = WATER_Z + 4.5    # up into the foliage-free trunk; no cap (nothing to stand on in the bark)
    for p, q in zip(ring, ring[1:] + ring[:1]):
        mesh.add([(p[0], p[1], zb - 0.1), (q[0], q[1], zb - 0.1), (q[0], q[1], z1), (p[0], p[1], z1)], "door_wood",
                 [(0, 0)] * 4)


def shrub_visual(mesh, k, x, y):
    """Wax-myrtle / willow bush on a bog: two rings and two apexes (a rounded lump)."""
    zb = terrain_z(x, y) - 0.1
    r = 1.0 + 0.5 * _h01("sh", k)
    h = 1.5 + 0.6 * _h01("shh", k)
    n = 7
    lo = [(x + r * math.cos(2 * math.pi * (j + 0.5 * _h01("sj", k, j)) / n),
           y + r * math.sin(2 * math.pi * (j + 0.5 * _h01("sj", k, j)) / n), zb + 0.45 * h) for j in range(n)]
    hi = [(x + (p[0] - x) * 0.62, y + (p[1] - y) * 0.62, zb + 0.82 * h) for p in lo]
    ft = [(x + (p[0] - x) * 0.78, y + (p[1] - y) * 0.78, zb) for p in lo]    # sits on the peat, no stalk
    top = (x, y, zb + h)
    for j in range(n):
        a, b = lo[j], lo[(j + 1) % n]
        c, d = hi[j], hi[(j + 1) % n]
        e, f = ft[j], ft[(j + 1) % n]
        mesh.add([e, f, b, a], "grass")
        mesh.add([a, b, d, c], "grass")
        mesh.add([c, d, top], "grass")


def build(ctx):
    """-> parts (map metres): "lake_alice_water basin" (visual terrain), "lake_alice_water surface" (water),
    "lake_alice_water dressing" (pads, reeds, cypress, shrubs) and "lake_alice_water collision"."""
    if ctx.get("stage_key") not in (None, STAGE):
        return []
    verts, tris, vtags = basin_triangles()
    isl_vert = [isinstance(t, tuple) for t in vtags]
    col = _Mesh()
    basin = _Mesh()
    for a, b, c in tris:
        P = [verts[a], verts[b], verts[c]]
        col.add(P, "dark_trim", [(0, 0)] * 3)
        cx, cy = (P[0][0] + P[1][0] + P[2][0]) / 3, (P[0][1] + P[1][1] + P[2][1]) / 3
        inside = island_at(cx, cy) is not None and all(isl_vert[i] or island_at(*verts[i][:2]) is not None
                                                       for i in (a, b, c))
        mat = _tri_material(P, inside)
        t = TILE_M[mat]
        V = [(p[0], p[1], _vis_z(p[2])) for p in P]
        basin.add(V, mat, [(p[0] / t, p[1] / t) for p in V], smooth=True)
    n_basin = col.tris()
    surface = _Mesh()
    water_surface(surface)
    dress = _Mesh()
    pads, trees = _PADS, _TREES
    for p in pads:
        x, y, _ = p["pos_m"]
        big = p["r_m"] >= 2.0
        lily_pad_visual(dress, x, y, p["r_m"], PAD_VIS_Z, (p["route"], p["i"]), rim=True, n=13 if big else 9,
                        flower=big or _h01("pf", p["route"], p["i"]) < 0.25)
        lily_pad_collision(col, x, y, p["r_m"])
    n_pads = col.tris() - n_basin
    deco = deco_pads(pads, trees)
    for k, (x, y, r, fl) in enumerate(deco):
        lily_pad_visual(dress, x, y, r, DECO_PAD_Z, ("deco", k), rim=False, n=7, flower=fl)
    reeds = reed_clumps(pads, trees)
    for x, y, seed in reeds:
        reed_clump_visual(dress, x, y, seed)
    for k, t in enumerate(trees):
        cypress_visual(dress, t, k)
        cypress_collision(col, t)
    for k, (i, x, y) in enumerate(SHRUBS):
        if island_at(x, y) == i:
            shrub_visual(dress, k, x, y)
    parts = []
    for m, name, collision, visual, share in ((basin, f"{SLUG} basin", False, True, True),
                                              (surface, f"{SLUG} surface", False, True, False),
                                              (dress, f"{SLUG} dressing", False, True, False),
                                              (col, f"{SLUG} collision", True, False, True)):
        me, slots = m.build(name, share=share)
        parts.append({"name": name, "mesh": me, "material_slots": slots, "collision": collision,
                      "visual": visual, "landmark": SLUG})
    print(f"lake_alice_water: collision {col.tris()} tris (basin {n_basin}, lily pads {n_pads}, cypress "
          f"{col.tris() - n_basin - n_pads}); visual {basin.tris() + surface.tris() + dress.tris()} tris (basin "
          f"{basin.tris()}, water {surface.tris()}, dressing {dress.tris()}: {len(pads)} hop pads, {len(deco)} small "
          f"pads, {len(reeds)} reed clumps, {len(trees)} cypress); stages.json budget 450 / 2500")
    return parts
