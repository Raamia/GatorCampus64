"""REITZ UNION + ENGINEERING stage (course 2, slot wf, stages.json key "reitz_eng") landmarks: the J. Wayne
Reitz Union, plus its South Terrace, the Reitz Union Amphitheater and the Liberty Pond fountain,
hand-modelled for Super Gatorlator 64.

Landmark module (contract: tools/campus/landmarks/_common.py). Every LANDMARKS entry has
"stages": ["reitz_eng"], so only `build_stage.py reitz_eng` builds it. Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower). Footprints are the OSM ones in data/uf/campus.json:

  J. Wayne Reitz Union w863211313 9,580 m2 tower 27.0 m budget 500 collision / 1800 visual
  Reitz Union Amphitheater w863211344 442 m2 (area) budget 150 collision / 500 visual
    + South Terrace w863456041 (pedestrian area between the curved facade and the seats)

build(ctx) returns one visual mesh and one closed low-poly collision mesh per landmark. Each part
dict has "landmark": <slug>. Collision walls face out of the solids. Every floor Mario walks on is
flat, except the amphitheater seats, which are an 11-degree ramp.

WHAT THE SOURCES SAY (reviewed)
  - Opened 1 May 1967 (groundbreaking 9 May 1964), 267,000 sq ft, $5.7 M. Architects: Barrett, Daffin
    & Bishop (Tallahassee) with Moore & May (Gainesville). "Eight levels including the Lower
    Level/plaza". Hotel guest rooms are on Levels 5 and 6. The Game Room (bowling alley, pool
    tables) is on the Ground Level and the food court on Level 1. (Wikipedia; union.ufl.edu/about)
  - Game Room, Ground Level: 14 bowling lanes, 9 billiards tables, a snooker table, esports
    (union.ufl.edu/gameroom).
  - 1991: 10,000 sq ft of meeting rooms built over the Colonnade. 1995/1998: food court and a new
    wing. 2002: Grand Ballroom and new Amphitheater seating. 2013-16 ($70.7 M, reopened 1 Feb 2016;
    CannonDesign with Walker Architects, Skanska): the colonnade building was demolished and about
    126,000 sq ft built in its place, between two existing adjoining buildings, with an atrium and a
    new game room. CannonDesign describes exterior design elements inspired by the patterns, colours
    and textures of a gator's scales, tail and underbelly. (union.ufl.edu/about; ENR; CSE magazine;
    UF News 2016-02)
  - South Terrace by Liberty Pond: "terrace grass areas and seating around the pond", "water jets
    and fountain", "concrete steps", and "seven veteran memorial monuments and the railing"
    (UF Lakes, Vegetation & Landscape Committee minutes, 2019-12-12, project MP04860).
  - OSM: building:material brick, roof grey, 8 levels. Entrances: Level 0 on the north facade
    (toward the North Lawn; Museum Road runs south of the Bookstore) at x -470 / -485, a Level 1
    bridge entry at x -456, Level 0/1 doors on the south-east facade by the Amphitheater, Level 0 on
    the east facade. A
    covered walkway (layer 1) runs along the north facade, another follows the curved SE facade.
    The food court (Level 1; Starbucks, Panda Express, Sonic, Baba's Pizza, The Halal Shack) sits
    behind the curved facade. The hotel node is at (-433, -264).
  - stages.json: 27.0 m overall (6 floors x 4.2 m + 2 m). Planner note: "Enterable ground floor +
    food court; roof terraces".
  No source gives the massing in detail. The block heights below are a reading of "8 levels + hotel
  on 5-6" and of the OSM indoor plan. The facade styles (1967 brick + concrete bands, a 2002
  ballroom wing, the 2016 glass wing with a gator-scale panel field) are interpretations.

MODELLED AS (blocks share the exact OSM outline: W + P + C + S + E = w863211313; collinear nodes and
the <= 15 cm wiggles of the east wall are dropped)
  W Grand Ballroom wing (west) 13.2 m brick, limestone base + cornice, tall Level 2 windows
  P west stair bump 15.6 m stair penthouse 2.4 m above the W roof
  C 1967 core 17.6 m brick with concrete floor bands and window ribbons;
                                                the north entrance recess (OSM Level 1 bridge entry)
  T hotel / office tower on C 27.0 m 40 x 22 m, brick + concrete fins, REITZ UNION band; roof
                                                deck 26.4 m inside a 0.6 m parapet, elevator penthouse to
                                                28.8 m, window-washer davit + rails on the west face
  E 2016 wing (east) 16.0 m glass curtain wall, white fins, gator-scale panels
                                                on the north face, green roof, atrium skylight
  S food court wing (south) 11.5 m brick + the curved glass facade toward the
                                                Amphitheater (the generic Bookstore next door is 13 m)
  North colonnade: concrete canopy (4.4 m) on five brick piers along the north facade, where the
  OSM covered walkway runs.
  SE arcade: a cantilevered canopy (5.6 m) along the curved facade and the E wing's south face.
  ENTERABLE FOOD COURT: Level 1 hall (floor 2.0 m = South Terrace level, ceiling 6.6 m) behind the
  curved glass. The door is at the OSM entrance node on the E wing's south face (x -376). Inside:
  serving counter with five vendor fronts (generic, no brand marks), two communal tables.

GAMEPLAY (SM64: a standing jump reaches ~2.2 m, a running jump ~3 m; every step below is <= 2.4 m)
  Act 1 "Rooftop of the Reitz" (design 7.2: ravine-side terraces -> awnings -> window-washer lift ->
  roof star), climb_route_m:
    ravine-side brick terraces against the W wing's south wall (1.5 / 3.0 / 4.5 m) -> three metal
    sunshade awnings (6.7 / 8.9 / 11.1) -> ballroom roof (13.2) -> rooftop AC unit (15.4) -> podium
    roof terrace (17.6) -> either the WINDOW-WASHER LIFT on the tower's west face (mission object;
    markers["window_washer_lift"]), its climbable cable (a 9 m pole, markers["poles"]), or the four
    concrete sunshade ledges on the tower's east face (19.8 / 21.6 / 23.4 / 25.2) -> tower parapet
    (27.0) / roof deck (26.4) -> elevator penthouse (28.8) = roof star spot (spots['roof_star']).
  Amphitheater-side route (markers["climb_route_south_m"]): South Terrace (2.0) -> SE canopy (5.6,
    double jump / backflip) -> two light shelves on the curved glass (7.8 / 10.0) -> food court roof
    (11.5) -> AC unit (13.8) -> green roof of the E wing (16.0) -> podium (17.6).
  North colonnade canopy (4.4): climb the lamp post at its west end (markers["poles"]).
  Liberty Pond fountain float (design 7.2 act 5 "the Liberty Pond fountain" token).
  Doors: north entrance (primary), food court (enterable), Game Room / bowling (door marker on the
  north facade, OSM Level 0 entrance x -485), east door. None of them is a stage door.

AMPHITHEATER + SOUTH TERRACE (entry "reitz_amphitheater")
  The site's slope is flattened (the generator ground is z = 0 everywhere). The South Terrace is a
  2.0 m deck on the OSM pedestrian area, at food court level. The OSM amphitheater band (concentric
  with Liberty Pond: seats from r 31 to r 41 m) steps down from the deck to the lawn by the pond:
  five grass tiers with concrete risers (collision: one 11-degree ramp). Seven granite memorial
  plinths stand on the lawn between the seats and the pond railing (the railing is the generator's
  OSM fence w1006236438). In the pond: a round fountain float with a water jet. Its collision top is
  0.3 m above grade, 0.6 m above the water. The real jets were proposed in 2019 and their status is
  unknown; the float is a game fixture for the act 5 token.

Sources
  - Wikipedia, "J. Wayne Reitz Union":https://en.wikipedia.org/wiki/J._Wayne_Reitz_Union
  - Reitz Union history: https://union.ufl.edu/about
  - Reitz Union Game Room: https://union.ufl.edu/gameroom
  - ENR, Higher Education Best Project, Reitz Union expansion:
    https://www.enr.com/articles/40792-higher-education-best-project---univ-of-florida-j-wayne-reitz-union-student-center-expansion-and-renovation
  - CSE magazine, IMEG/KJWW/TTG Reitz Union: https://www.csemag.com/imeg-kjww-ttg-university-of-florida-reitz-union/
  - UF News 2016-02, renovation complete:
    https://archive.news.ufl.edu/articles/2016/02/reitz-union-renovation-expansion-now-complete-1.html
  - UF LVLC minutes 2019-12-12 (South Terrace, Liberty Pond, memorials):
    https://pdc.ufl.edu/wp-content/uploads/nox/pdc/resources/documents/lvl/2019-12-12/vp-response-1588252518.pdf
  - UF Foundation, Dave Kratzer South Terrace and Liberty Pond fund: https://giving.uff.ufl.edu/?p=6556
  - OpenStreetMap ways 863211313, 863211344, 863456041, 150821686, 1006236438, 1215462333,
    1215462325, 1315821081; entrance nodes 11261533463, 11246964266, 4431967751, 8041384373,
    11261533459, 11261533458. Map data (c) OpenStreetMap contributors, ODbL 1.0.
"""
import math
import os
import sys

try:
    from landmarks import _common as C
except ImportError:  # imported as a top-level module: make the `landmarks` package importable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from landmarks import _common as C

STAGES = ["reitz_eng"]
EPS = 1e-6
VIS_MAX_LEN = 24.0     # 2 m textures repeat <= 12x across one visual wall face
DECAL = 0.05           # window ribbons, bands and signs stand this far proud of the wall

RU_ID = "w863211313"           # J. Wayne Reitz Union
AMPHI_ID = "w863211344"        # Reitz Union Amphitheater (grass seats)
TERRACE_ID = "w863456041"      # South Terrace (pedestrian area along the curved facade)
POND_ID = "w150821686"         # Liberty Pond (the generator builds the basin + water)

# ------------------------------------------------------------------ heights (m above grade)
Z_W, Z_P, Z_C, Z_E, Z_S = 13.2, 15.6, 17.6, 16.0, 11.5
Z_T, Z_PH = 27.0, 28.8          # tower parapet top (stages.json 27 m), elevator penthouse roof (star spot)
Z_TD, PAR_T = 26.4, 0.4         # tower roof deck inside a 0.6 m parapet (0.4 m thick)
DECK_Z = 2.0                    # South Terrace + food court floor (Level 1)
CEIL_Z = 6.6                    # food court ceiling
DOOR_TOP = 5.0                  # food court door head
WALL_T = 0.35                   # food court wall thickness (inner collision faces)

# ------------------------------------------------------------------ OSM outline w863211313, split into blocks
# (counter-clockwise; shared edges are exact reverses of each other)
W_POLY = [(-462.0, -242.81), (-521.03, -242.41), (-521.35, -262.37), (-521.19, -267.54), (-521.34, -280.18),
          (-461.96, -280.92)]
P_POLY = [(-521.35, -262.37), (-523.31, -262.35), (-523.2, -267.61), (-521.19, -267.54)]
C_POLY = [(-410.37, -242.04), (-454.36, -241.68), (-454.38, -244.01), (-457.92, -244.04), (-457.96, -242.84),
          (-462.0, -242.81), (-461.96, -280.92), (-410.4, -280.92), (-410.41, -243.45)]
E_POLY = [(-410.41, -243.45), (-410.4, -280.92), (-410.4, -288.7), (-388.39, -288.65), (-360.05, -289.04),
          (-359.63, -242.94), (-370.51, -242.84), (-370.87, -241.85), (-378.72, -241.73), (-378.94, -242.84),
          (-383.3, -242.73), (-383.91, -243.66), (-399.5, -243.54)]
# curved SE facade of the food court (OSM nodes 30..38), south -> north-east
CURVE = [(-406.88, -305.51), (-406.37, -302.4), (-405.65, -300.52), (-404.36, -298.31), (-402.28, -295.19),
         (-398.97, -292.09), (-395.47, -289.55), (-392.54, -288.72), (-388.39, -288.65)]
S_POLY = [(-461.96, -280.92), (-464.62, -336.2), (-449.94, -336.83), (-416.49, -336.72), (-416.16, -318.04),
          (-407.67, -317.58)] + CURVE + [(-410.4, -288.7), (-410.4, -280.92)]
TOWER = (-456.0, -416.0, -274.0, -252.0)            # x0, x1, y0, y1 (on C)
PENTHOUSE = (-440.0, -433.0, -266.0, -260.0)        # on the tower roof
FLOORS = {   # (floor z, sill, head) for window ribbons
    "W": [(0.0, 1.1, 3.4), (4.4, 1.1, 3.4), (8.8, 0.8, 3.5)],
    "P": [],
    "C": [(0.0, 1.2, 3.4), (4.4, 1.2, 3.4), (8.8, 1.2, 3.4), (13.2, 1.2, 3.4)],
    "E": [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (8.0, 0.0, 0.0), (12.0, 0.0, 0.0)],
    "S": [(0.0, 0.0, 0.0), (DECK_Z, 1.0, 3.4), (CEIL_Z, 1.0, 3.4)],
    "T": [(Z_C, 0.6, 2.1), (Z_C + 3.13, 0.6, 2.1), (Z_C + 6.27, 0.6, 2.1)],
}
BLOCKS = {
    "W": {"poly": W_POLY, "top": Z_W, "style": "ballroom"},
    "P": {"poly": P_POLY, "top": Z_P, "style": "stair"},
    "C": {"poly": C_POLY, "top": Z_C, "style": "core"},
    "E": {"poly": E_POLY, "top": Z_E, "style": "glass"},
    "S": {"poly": S_POLY, "top": Z_S, "style": "food"},
}
STYLE = {
    "ballroom": {"body": "brick_red", "base": "limestone", "cornice": "limestone", "corn_h": 0.7,
                 "win": "window_dark", "band": None},
    "stair": {"body": "brick_dark", "base": "concrete", "cornice": "white_trim", "corn_h": 0.6, "win": None,
              "band": None},
    "core": {"body": "brick_red", "base": "concrete", "cornice": "white_trim", "corn_h": 0.8,
             "win": "window_dark", "band": "white_trim"},
    "tower": {"body": "brick_red", "base": None, "cornice": "white_trim", "corn_h": 0.6, "win": "window_dark",
              "band": "white_trim"},
    "glass": {"body": "window_glass", "base": "dark_trim", "cornice": "white_trim", "corn_h": 0.9, "win": None,
              "band": "metal_gray", "fins": 6.0},
    "food": {"body": "brick_red", "base": "concrete", "cornice": "white_trim", "corn_h": 0.7,
             "win": "window_dark", "band": None},
    "curve": {"body": "window_glass", "base": "concrete", "cornice": "white_trim", "corn_h": 0.7, "win": None,
              "band": "metal_gray"},
}

# ------------------------------------------------------------------ gameplay pieces
SW_WALL = ((-521.34, -280.18), (-461.96, -280.92))   # W wing south wall (ravine side), faces south
TERRACES = [(6.0, 24.0, 4.8, 0.0, 1.5), (6.0, 16.0, 3.2, 1.5, 3.0), (6.0, 11.0, 1.8, 3.0, 4.5)]  # t0 t1 depth z0 z1
AWNINGS = [(12.5, 18.0, 6.7), (19.5, 25.0, 8.9), (26.5, 32.0, 11.1)]        # t0 t1 top
AWN_D, AWN_T = 1.8, 0.3
HVAC_W = (-468.6, -464.2, -264.0, -258.0, Z_W, 15.4)      # rooftop AC unit, ballroom roof
HVAC_S = (-407.0, -402.5, -293.5, -290.2, Z_S, 13.8)      # rooftop AC unit, food court roof
LEDGES = [(-272.0, -269.0, 19.8), (-268.0, -265.0, 21.6), (-264.0, -261.0, 23.4), (-260.0, -257.0, 25.2)]
LEDGE_D, LEDGE_T = 1.7, 0.35                              # on the tower's east face x = TOWER[1]
PLANTERS = [(-376.0, -371.5, -262.0, -258.0), (-394.0, -389.5, -251.0, -247.5)]
PLANTER_H = 0.9
SKYLIGHT = (-402.0, -388.0, -277.0, -263.0, Z_E + 0.9)
LIFT_XY = (-457.3, -262.0)                                # window-washer platform track (mission object): the
                                                          # 1.2 m half-wide deck stops 0.1 m short of the west face
CABLE = (-457.0, -266.6, Z_C, 9.0)                        # climbable BMU cable: base x, y, z, height
LAMP = (-461.2, -237.2, 0.0, 5.0)                         # north colonnade lamp post (pole)
# north colonnade (OSM covered walkway w1215462333 along the north facade)
CANOPY_N = [(-459.0, -242.0), (-410.4, -242.0), (-410.4, -243.45), (-401.0, -243.45), (-401.0, -237.6),
            (-459.0, -237.6)]
CANOPY_N_Z = (4.1, 4.4)
PIERS_X = (-457.6, -444.0, -430.4, -416.8, -403.2)
PIER_Y = (-238.35, -237.65)
PIER_W = 0.7
# SE arcade canopy along the curved facade + the E wing south face
CAN_SE = [(-407.67, -317.58)] + CURVE + [(-369.0, -288.92)]
CAN_SE_COL = [(-407.67, -317.58), (-406.88, -305.51), (-405.65, -300.52), (-402.28, -295.19), (-395.47, -289.55),
              (-388.39, -288.65), (-369.0, -288.92)]
CAN_SE_D, CAN_SE_Z = 3.0, (5.3, 5.6)
SHADES = [((-405.65, -300.52), (-402.28, -295.19), 0.4, 5.4, 7.8),     # chord a, c, t0, t1, top
          ((-402.28, -295.19), (-395.47, -289.55), 0.8, 5.8, 10.0)]
SHADE_D, SHADE_T = 1.4, 0.25
# food court (Level 1) behind the curved glass
ROOM = [(-428.0, -318.06), (-416.16, -318.04), (-407.67, -317.58), (-406.88, -305.51), (-405.65, -300.52),
        (-402.28, -295.19), (-395.47, -289.55), (-388.39, -288.65), (-372.0, -288.88), (-372.0, -283.0),
        (-428.0, -283.0)]
ROOM_GLASS = {2, 3, 4, 5, 6, 7}        # room edges i -> i+1 that are the curved / east glass facade
ROOM_DOOR_EDGE = 7                     # (-388.39, -288.65) -> (-372.0, -288.88): door wall (inside)
E_DOOR_EDGE = 3                        # E_POLY edge (-388.39, -288.65) -> (-360.05, -289.04)
DOOR_X, DOOR_W = -376.06, 3.2          # OSM entrance node 11261533459
COUNTER = (-427.65, -426.35, -316.5, -285.0, DECK_Z + 1.1)
TABLES = [(-416.0, -411.5, -304.0, -302.8), (-416.0, -411.5, -296.0, -294.8)]
TABLE_H = 0.85
VENDORS = [  # (wall: "W" west / "N" north, t0, t1 along the inside face, sign colour)
    ("W", 2.0, 7.0, "dark_trim"), ("W", 8.0, 13.0, "brick_red"), ("W", 14.0, 19.0, "copper_green"),
    ("W", 20.0, 25.0, "brick_dark"), ("N", 4.0, 10.0, "bronze"),
]

# ------------------------------------------------------------------ amphitheater + South Terrace + fountain
# OSM w863211344, west -> east (concentric with Liberty Pond: r 40.1-41.5 and 30.3-31.2)
OUTER_ARC = [(-404.56, -316.53), (-404.14, -315.63), (-402.04, -311.91), (-400.41, -309.54), (-398.83, -307.74),
             (-397.0, -305.91), (-395.54, -304.59), (-394.33, -303.61), (-392.6, -302.29), (-390.81, -301.02),
             (-389.1, -299.93), (-387.39, -298.98), (-385.0, -297.8), (-382.65, -296.89), (-380.35, -296.22),
             (-377.49, -295.48), (-375.24, -295.0), (-372.71, -294.69), (-370.11, -294.5), (-367.49, -294.5),
             (-364.81, -294.66), (-362.28, -294.96)]
INNER_ARC = [(-395.84, -321.11), (-395.09, -319.52), (-393.88, -317.45), (-392.71, -315.77), (-390.5, -313.33),
             (-388.37, -311.52), (-386.01, -309.73), (-383.53, -308.25), (-381.03, -306.99), (-378.25, -305.95),
             (-375.7, -305.34), (-373.37, -304.86), (-371.11, -304.64), (-369.03, -304.61), (-366.81, -304.76),
             (-364.56, -305.05)]
# deck (South Terrace) after the outer arc: east end, along the E wing's south face, back down the curve
DECK_TAIL = [(-360.05, -294.9), (-360.05, -289.04)] + list(reversed(CURVE)) + [(-407.67, -317.58)]
N_COL, N_VIS = 6, 10                   # amphitheater segments (collision / visual)
N_TIERS = 5
POND_C = (-369.37, -335.81)            # Liberty Pond centroid (OSM w150821686, r 23.4-26.2 m)
FOUNTAIN_R, FOUNTAIN_TOP = 1.6, 0.3
POND_FLOOR = -2.2                      # stage_ground.POND_FLOOR
MEMORIAL_R = 28.0
MEMORIAL_ANG = [100.0 + 6.0 * k for k in range(7)]   # degrees about the pond centre
MEMORIAL_SIZE = (1.0, 0.35, 1.3)       # tangential, radial, height (granite tablets)


# =================================================================== small helpers (pure Python)
def _cuts(t0, t1, max_len):
    n = max(1, int(math.ceil((t1 - t0) / max_len - 1e-9)))
    return [t0 + (t1 - t0) * i / n for i in range(n + 1)]


def _r(p, nd=2):
    return tuple(round(float(c), nd) for c in p)


def _edges(poly):
    return list(zip(poly, poly[1:] + poly[:1]))


def _unit(dx, dy):
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def _lerp(a, c, f):
    return (a[0] + (c[0] - a[0]) * f, a[1] + (c[1] - a[1]) * f)


def _resample(pl, n):
    """Arc-length resampling of a polyline into n segments (n + 1 points)."""
    acc = [0.0]
    for a, c in zip(pl, pl[1:]):
        acc.append(acc[-1] + math.dist(a, c))
    total = acc[-1]
    out = []
    j = 0
    for k in range(n + 1):
        s = total * k / n
        while j < len(pl) - 2 and acc[j + 1] < s:
            j += 1
        seg = acc[j + 1] - acc[j]
        f = 0.0 if seg < EPS else min(1.0, max(0.0, (s - acc[j]) / seg))
        out.append(_lerp(pl[j], pl[j + 1], f))
    return out


def _miter(p0, p1, p2, d):
    """Vertex p1 of a polyline moved d to the LEFT of both adjacent edges (mitered)."""
    u1 = _unit(p1[0] - p0[0], p1[1] - p0[1])
    u2 = _unit(p2[0] - p1[0], p2[1] - p1[1])
    a = (p1[0] - u1[1] * d, p1[1] + u1[0] * d)
    b = (p1[0] - u2[1] * d, p1[1] + u2[0] * d)
    den = u1[0] * u2[1] - u1[1] * u2[0]
    if abs(den) < 1e-6:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    t = ((b[0] - a[0]) * u2[1] - (b[1] - a[1]) * u2[0]) / den
    return (a[0] + u1[0] * t, a[1] + u1[1] * t)


def _offset_closed(poly, d):
    """Closed CCW polygon offset inward by d (every edge moved d to its left)."""
    n = len(poly)
    return [_miter(poly[i - 1], poly[i], poly[(i + 1) % n], d) for i in range(n)]


def _offset_open(pl, d):
    """Open polyline offset d to its RIGHT (outward of a CCW outline); ends square."""
    out = []
    n = len(pl)
    for i in range(n):
        if i == 0:
            u = _unit(pl[1][0] - pl[0][0], pl[1][1] - pl[0][1])
            out.append((pl[0][0] + u[1] * d, pl[0][1] - u[0] * d))
        elif i == n - 1:
            u = _unit(pl[-1][0] - pl[-2][0], pl[-1][1] - pl[-2][1])
            out.append((pl[-1][0] + u[1] * d, pl[-1][1] - u[0] * d))
        else:
            out.append(_miter(pl[i - 1], pl[i], pl[i + 1], -d))
    return out


def _inside(pt, poly):
    x, y = pt
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _y_on(a, c, x):
    return a[1] + (c[1] - a[1]) * (x - a[0]) / (c[0] - a[0])


class Edge:
    """Vertical wall plane over the outline edge a -> c (counter-clockwise outline: outside on the
    right). Wall coordinates: t (0..L along a -> c), z up, off (+ = outward)."""

    def __init__(self, a, c):
        self.a = (float(a[0]), float(a[1]))
        self.c = (float(c[0]), float(c[1]))
        dx, dy = self.c[0] - self.a[0], self.c[1] - self.a[1]
        self.L = math.hypot(dx, dy)
        self.d = (dx / self.L, dy / self.L)
        self.n = (self.d[1], -self.d[0])

    def p(self, t, z, off=0.0):
        return (self.a[0] + self.d[0] * t + self.n[0] * off, self.a[1] + self.d[1] * t + self.n[1] * off, z)

    def xy(self, t, off=0.0):
        return self.p(t, 0.0, off)[:2]

    def t_of(self, pt):
        return (pt[0] - self.a[0]) * self.d[0] + (pt[1] - self.a[1]) * self.d[1]

    def quad(self, b, t0, t1, z0, z1, mat, off=0.0, inward=False, max_len=None):
        if t1 - t0 < 1e-4 or z1 - z0 < 1e-4:
            return
        s = -1.0 if inward else 1.0
        cuts = [t0, t1] if not max_len else _cuts(t0, t1, max_len)
        for ta, tb in zip(cuts, cuts[1:]):
            b.poly([self.p(ta, z0, off), self.p(tb, z0, off), self.p(tb, z1, off), self.p(ta, z1, off)], mat,
                   normal_hint=(s * self.n[0], s * self.n[1], 0.0))

    def bearing(self):
        return math.degrees(math.atan2(self.n[0], self.n[1])) % 360.0


def _box(b, x0, x1, y0, y1, z0, z1, mat, faces="tnsew", mats=None):
    """Axis-aligned box; `faces` picks t(op) b(ottom) n s e w."""
    mats = mats or {}
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    q = {
        "t": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        "b": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
        "s": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
        "n": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
        "e": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
        "w": ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
    }
    for f in faces:
        pts, h = q[f]
        b.poly(pts, mats.get(f, mat), normal_hint=h)


def _ebox(b, E, t0, t1, o0, o1, z0, z1, mat, faces="tflr", mats=None):
    """Box in the frame of wall E: t along the wall, o outward. Faces: t(op) b(ottom) f(ront, o1)
    k (back, o0) l (t0 end) r (t1 end)."""
    mats = mats or {}
    P = E.p
    n = (E.n[0], E.n[1], 0.0)
    d = (E.d[0], E.d[1], 0.0)
    q = {
        "t": ([P(t0, z1, o0), P(t1, z1, o0), P(t1, z1, o1), P(t0, z1, o1)], (0, 0, 1)),
        "b": ([P(t0, z0, o0), P(t1, z0, o0), P(t1, z0, o1), P(t0, z0, o1)], (0, 0, -1)),
        "f": ([P(t0, z0, o1), P(t1, z0, o1), P(t1, z1, o1), P(t0, z1, o1)], n),
        "k": ([P(t0, z0, o0), P(t1, z0, o0), P(t1, z1, o0), P(t0, z1, o0)], (-n[0], -n[1], 0.0)),
        "l": ([P(t0, z0, o0), P(t0, z0, o1), P(t0, z1, o1), P(t0, z1, o0)], (-d[0], -d[1], 0.0)),
        "r": ([P(t1, z0, o0), P(t1, z0, o1), P(t1, z1, o1), P(t1, z1, o0)], d),
    }
    for f in faces:
        pts, h = q[f]
        b.poly(pts, mats.get(f, mat), normal_hint=h)


def _tess(loops):
    """Triangles [(x, y), ...] filling the first loop minus the others (mathutils, Blender only)."""
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    vl = [[Vector((x, y, 0.0)) for x, y in L] for L in loops]
    flat = [p for L in loops for p in L]
    return [[flat[i] for i in tri] for tri in tessellate_polygon(vl)]


def _slab(b, loops, z, mat, up=True, uv_tile=None):
    for tri in _tess(loops):
        pts = [(x, y, z) for x, y in tri]
        uvs = C.project_uv(pts, uv_tile, normal=(0, 0, 1)) if uv_tile else None
        b.poly(pts, mat, uvs=uvs, normal_hint=(0, 0, 1 if up else -1))


def _ngon(b, pts2, z, mat, up=True, uv_tile=None):
    pts = [(x, y, z) for x, y in pts2]
    uvs = C.project_uv(pts, uv_tile, normal=(0, 0, 1)) if uv_tile else None
    b.poly(pts, mat, uvs=uvs, normal_hint=(0, 0, 1 if up else -1))


def _vquad(b, a, c, z0, z1, mat, hint):
    b.poly([(a[0], a[1], z0), (c[0], c[1], z0), (c[0], c[1], z1), (a[0], a[1], z1)], mat, normal_hint=hint)


def _prism_post(b, x, y, r, z0, z1, mat, sides=4, top=None):
    """Thin vertical post (visual): `sides`-gon of radius r."""
    pts = [(x + r * math.cos(2 * math.pi * (k + 0.5) / sides), y + r * math.sin(2 * math.pi * (k + 0.5) / sides))
           for k in range(sides)]
    for a, c in _edges(pts):
        mx, my = (a[0] + c[0]) / 2 - x, (a[1] + c[1]) / 2 - y
        _vquad(b, a, c, z0, z1, mat, (mx, my, 0.0))
    if top:
        _ngon(b, pts, z1, top)


def _cone(b, x, y, r, z0, z1, mat, sides=6):
    pts = [(x + r * math.cos(2 * math.pi * k / sides), y + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    for a, c in _edges(pts):
        mx, my = (a[0] + c[0]) / 2 - x, (a[1] + c[1]) / 2 - y
        b.poly([(a[0], a[1], z0), (c[0], c[1], z0), (x, y, z1)], mat, normal_hint=(mx, my, r * 0.3))


# =================================================================== layout (pure Python)
def _shared_tops():
    """(block, edge index) -> top of the block on the other side of that edge (exact reversed edge)."""
    out = {}
    for k, B in BLOCKS.items():
        for i, (a, c) in enumerate(_edges(B["poly"])):
            for k2, B2 in BLOCKS.items():
                if k2 == k:
                    continue
                for a2, c2 in _edges(B2["poly"]):
                    if math.dist(a, c2) < 0.02 and math.dist(c, a2) < 0.02:
                        out[(k, i)] = B2["top"]
    return out


def _layout():
    E_SW = Edge(*SW_WALL)
    tx0, tx1, ty0, ty1 = TOWER
    px0, px1, py0, py1 = PENTHOUSE
    # ---- act 1 climb (ravine side -> roof star)
    route = []
    for k, (t0, t1, dep, z0, z1) in enumerate(TERRACES, 1):
        tm = t1 - 2.0 if k == 1 else (t0 + t1) / 2
        route.append((f"ravine_terrace_{k}", (*E_SW.xy(tm, dep - 1.0), z1)))
    for k, (t0, t1, z) in enumerate(AWNINGS, 1):
        route.append((f"awning_{k}", (*E_SW.xy((t0 + t1) / 2, AWN_D / 2), z)))
    route += [
        ("ballroom_roof", (*E_SW.xy(AWNINGS[-1][1] - 1.5, -2.5), Z_W)),
        ("ballroom_ac_unit", ((HVAC_W[0] + HVAC_W[1]) / 2, (HVAC_W[2] + HVAC_W[3]) / 2, HVAC_W[5])),
        ("podium_roof_west", (-460.0, -261.0, Z_C)),
        ("podium_roof_north", (-436.0, -247.0, Z_C)),
        ("podium_roof_east", (-413.2, -274.5, Z_C)),
    ]
    for k, (y0, y1, z) in enumerate(LEDGES, 1):
        route.append((f"tower_ledge_{k}", (tx1 + LEDGE_D / 2, (y0 + y1) / 2, z)))
    route += [("tower_roof", (tx1 - 2.0, LEDGES[-1][1] + 1.0, Z_TD)),
              ("penthouse_top", ((px0 + px1) / 2, (py0 + py1) / 2, Z_PH))]
    # ---- amphitheater-side route
    can_in = CAN_SE_COL
    can_out = _offset_open(can_in, CAN_SE_D)
    c_i = 3
    can_pt = _lerp(_lerp(can_in[c_i], can_in[c_i - 1], 0.5), _lerp(can_out[c_i], can_out[c_i - 1], 0.5), 0.6)
    south = [("south_terrace", (-392.0, -297.5, DECK_Z)), ("se_canopy", (*can_pt, CAN_SE_Z[1]))]
    for k, (a, c, t0, t1, z) in enumerate(SHADES, 1):
        Eh = Edge(a, c)
        south.append((f"light_shelf_{k}", (*Eh.xy((t0 + t1) / 2, SHADE_D / 2), z)))
    south += [("food_court_roof", (-401.5, -291.0, Z_S)),
              ("food_court_ac_unit", ((HVAC_S[0] + HVAC_S[1]) / 2, (HVAC_S[2] + HVAC_S[3]) / 2, HVAC_S[5])),
              ("green_roof", (-404.75, -286.0, Z_E)), ("podium_roof_east", (-412.0, -278.0, Z_C))]
    # ---- doors (map metres; z = sill)
    Es = Edge(E_POLY[E_DOOR_EDGE], E_POLY[E_DOOR_EDGE + 1])
    t_door = Es.t_of((DOOR_X, -288.8))
    Wn = Edge(W_POLY[0], W_POLY[1])
    Ee = Edge(E_POLY[4], E_POLY[5])
    t_east = Ee.t_of((-359.83, -248.61))
    doors = [
        {"name": "DOOR_reitz_union_1", "pos_m": (-456.15, -244.03, 0.0), "facing_deg": 0.0, "primary": True,
         "width_m": 3.4, "height_m": 3.2, "recess_m": 1.8,
         "note": "north entrance (OSM 11261533463, the Level 1 bridge entry from the North Lawn), glass doors at "
                 "the back of the recess under the colonnade canopy; not a stage door"},
        {"name": "DOOR_reitz_union_2", "pos_m": _r((*Es.xy(t_door), DECK_Z)), "facing_deg": round(Es.bearing(), 1),
         "width_m": DOOR_W, "height_m": DOOR_TOP - DECK_Z, "enterable": True,
         "note": "Food Court entrance from the South Terrace (OSM 11261533459): an open doorway into the "
                 "enterable Level 1 food court (floor 2.0 m); not a stage door"},
        {"name": "DOOR_reitz_union_3", "pos_m": _r((*Wn.xy(Wn.t_of((-485.22, -242.73))), 0.0)),
         "facing_deg": round(Wn.bearing(), 1), "width_m": 2.4, "height_m": 2.8,
         "note": "Game Room door marker (Ground Level: 14 bowling lanes, billiards; union.ufl.edu/gameroom) at "
                 "the OSM Level 0 entrance 11246964266; glass doors + bowling sign panel, not enterable"},
        {"name": "DOOR_reitz_union_4", "pos_m": _r((*Ee.xy(t_east), 0.0)), "facing_deg": round(Ee.bearing(), 1),
         "width_m": 2.4, "height_m": 2.8, "note": "east door (OSM 8041384373, Level 0); visual panel"},
    ]
    can_mid = _lerp(can_in[2], can_out[2], 0.5)
    spots = {
        "north_entrance": (-456.15, -240.6, 0.0),
        "north_colonnade_top": (-430.0, -239.8, CANOPY_N_Z[1]),
        "game_room_door": _r((*Wn.xy(Wn.t_of((-485.22, -242.73)), 1.6), 0.0)),
        "stair_penthouse_top": (-522.25, -264.98, Z_P),
        "ballroom_roof_center": (-492.0, -261.0, Z_W),
        "podium_roof_north": (-436.0, -247.0, Z_C),
        "podium_roof_south": (-436.0, -277.5, Z_C),
        "window_washer_lift_bottom": (*LIFT_XY, Z_C),
        "window_washer_lift_top": (*LIFT_XY, Z_T),
        "tower_roof_center": ((tx0 + tx1) / 2, ty1 - 4.0, Z_TD),
        "tower_parapet_east": (tx1 - PAR_T / 2, LEDGES[-1][1] + 1.5, Z_T),
        "roof_star": ((px0 + px1) / 2, (py0 + py1) / 2, Z_PH),
        "green_roof_center": (-380.0, -266.0, Z_E),
        "skylight_top": ((SKYLIGHT[0] + SKYLIGHT[1]) / 2, (SKYLIGHT[2] + SKYLIGHT[3]) / 2, SKYLIGHT[4]),
        "food_court_roof": (-440.0, -305.0, Z_S),
        "food_court_center": (-412.0, -305.0, DECK_Z),
        "food_court_door_inside": _r((*Es.xy(t_door, -1.8), DECK_Z)),
        "food_court_door_outside": _r((*Es.xy(t_door, 1.8), DECK_Z)),
        "food_court_counter_top": (-427.0, -300.0, COUNTER[4]),
        "food_court_table": ((TABLES[0][0] + TABLES[0][1]) / 2, (TABLES[0][2] + TABLES[0][3]) / 2,
                             DECK_Z + TABLE_H),
        "se_canopy_top": _r((*can_mid, CAN_SE_Z[1])),
        # North Lawn walk ~20 m north of the colonnade; face south (180 deg) at the north facade + tower
        "suggested_stage_spawn": (-430.0, -222.0, 0.0),
    }
    for name, p in route + south:
        spots.setdefault(name, _r(p))
    markers = {
        "poles": [
            {"name": "window_washer_cable", "base_m": (CABLE[0], CABLE[1], CABLE[2]), "height_m": CABLE[3],
             "note": "the window-washer's cable on the tower's west face: podium (17.6) -> 26.6, hop east "
                     "onto the tower roof"},
            {"name": "north_colonnade_lamp", "base_m": (LAMP[0], LAMP[1], LAMP[2]), "height_m": LAMP[3],
             "note": "lamp post at the colonnade's west end; jump east onto the canopy (4.4)"},
        ],
        "window_washer_lift": {"bottom_m": (*LIFT_XY, Z_C), "top_m": (*LIFT_XY, Z_T), "travel_m": round(Z_T - Z_C, 2),
                               "platform_half_m": (1.2, 1.6), "facing_deg": 270.0,
                               "note": "design 7.2 act 1 window-washer lift (moving platform object, e.g. "
                                       "bhvPlatformOnTrack or a custom lift): a vertical track 1.3 m off the "
                                       "tower's west face (platform edge 0.1 m from it, so at the top the rider "
                                       "steps across onto the parapet), from the podium roof (17.6) to the "
                                       "parapet top (27.0); rails + davit are drawn by this module"},
        "climb_route_south_m": [_r(p) for _, p in south],
        "levels_m": {"ballroom_roof": Z_W, "stair_penthouse": Z_P, "podium_roof": Z_C, "e_wing_green_roof": Z_E,
                     "food_court_roof": Z_S, "tower_roof": Z_TD, "tower_parapet": Z_T, "penthouse": Z_PH,
                     "food_court_floor": DECK_Z,
                     "food_court_ceiling": CEIL_Z, "north_colonnade": CANOPY_N_Z[1], "se_canopy": CAN_SE_Z[1]},
    }
    return {"route": route, "south": south, "doors": doors, "spots": spots, "markers": markers,
            "t_door": t_door}


def _amphi_layout():
    O_c, I_c = _resample(OUTER_ARC, N_COL), _resample(INNER_ARC, N_COL)
    O_v, I_v = _resample(OUTER_ARC, N_VIS), _resample(INNER_ARC, N_VIS)
    plinths = []
    for ang in MEMORIAL_ANG:
        a = math.radians(ang)
        plinths.append((POND_C[0] + MEMORIAL_R * math.cos(a), POND_C[1] + MEMORIAL_R * math.sin(a), a))
    mid = N_VIS // 2
    spots = {
        "south_terrace_west": _r((-404.3, -309.0, DECK_Z)),
        "south_terrace_center": _r((-392.0, -297.5, DECK_Z)),
        "south_terrace_east": _r((-366.0, -292.0, DECK_Z)),
        "amphitheater_top_row": _r((*_lerp(I_v[mid], O_v[mid], 0.9), DECK_Z - 0.2)),
        "amphitheater_bottom": _r((*_lerp(I_v[mid], POND_C, 0.12), 0.0)),
        "veterans_memorial": _r((*_lerp(plinths[3][:2], POND_C, -0.06), 0.0)),
        "liberty_pond_fountain": _r((POND_C[0], POND_C[1], FOUNTAIN_TOP)),
    }
    return {"O_c": O_c, "I_c": I_c, "O_v": O_v, "I_v": I_v, "plinths": plinths, "spots": spots}


# =================================================================== builders (need bpy / mathutils)
def _facade(vis, E, t0, t1, z_lo, top, style, floors):
    """Visual wall t0..t1 of E from z_lo to top: base course, body, cornice, window ribbons, floor
    bands and (glass) fins."""
    s = STYLE[style]
    corn = s["corn_h"]
    zb = -0.15 if z_lo < 0.01 else z_lo
    for ta, tb in zip(_cuts(t0, t1, VIS_MAX_LEN), _cuts(t0, t1, VIS_MAX_LEN)[1:]):
        z0 = zb
        if z_lo < 0.01 and s["base"]:
            E.quad(vis, ta, tb, zb, 0.6, s["base"])
            z0 = 0.6
        E.quad(vis, ta, tb, z0, top - corn, s["body"])
        E.quad(vis, ta, tb, top - corn, top, s["cornice"])
        if tb - ta < 1.8:
            continue
        for f, sill, head in floors:
            if s["win"] and head > sill:
                zs, zh = f + sill, f + head
                if zs >= z_lo + 0.3 - EPS and zh <= top - corn - 0.15 + EPS:
                    E.quad(vis, ta + 0.6, tb - 0.6, zs, zh, s["win"], off=DECAL)
            if s["band"] and z_lo + 0.3 < f < top - corn - 0.3:
                E.quad(vis, ta, tb, f - 0.2, f + 0.2, s["band"], off=DECAL)
    if s.get("fins") and t1 - t0 > 4.0:
        n = max(1, int((t1 - t0) // s["fins"]))
        step = (t1 - t0) / n
        for k in range(1, n):
            tf = t0 + step * k
            E.quad(vis, tf - 0.15, tf + 0.15, max(z_lo, 0.5), top - corn, "white_trim", off=0.15)


def _glass_doors(vis, E, tc, w, h, z0=0.0, frame="dark_trim", off=DECAL):
    E.quad(vis, tc - w / 2 - 0.2, tc + w / 2 + 0.2, z0, z0 + h + 0.25, frame, off=off)
    E.quad(vis, tc - w / 2, tc + w / 2, z0, z0 + h, "window_glass", off=off + 0.03)
    E.quad(vis, tc - 0.05, tc + 0.05, z0, z0 + h, frame, off=off + 0.05)


def _gator_scales(vis, E, t0, t1, z0, rows, w=2.4, h=2.8, off=0.12):
    """CannonDesign's gator-scale motif: staggered diamond panels (copper / bronze)."""
    mats = ("copper_green", "bronze", "copper_green", "dark_trim")
    for r in range(rows):
        zc = z0 + h / 2 + r * h * 0.62
        shift = (w / 2) if r % 2 else 0.0
        n = int((t1 - t0 - shift) // w)
        for k in range(n):
            tc = t0 + shift + w * (k + 0.5)
            pts = [E.p(tc, zc - h / 2, off), E.p(tc + w / 2 - 0.08, zc, off), E.p(tc, zc + h / 2, off),
                   E.p(tc - w / 2 + 0.08, zc, off)]
            vis.poly(pts, mats[(k + r) % len(mats)], normal_hint=(E.n[0], E.n[1], 0.0))


def _build_union(ctx, lay):
    vis, col = C.Builder(), C.Builder()
    shared = _shared_tops()
    tx0, tx1, ty0, ty1 = TOWER

    # ---------------------------------------------------------------- block shells
    for key, B in BLOCKS.items():
        poly, top = B["poly"], B["top"]
        for i, (a, c) in enumerate(_edges(poly)):
            nb = shared.get((key, i))
            z_lo = nb if nb is not None else 0.0
            if z_lo >= top - EPS:
                continue
            E = Edge(a, c)
            style = B["style"]
            if key == "S" and (a in CURVE and c in CURVE or (a == (-407.67, -317.58) and c == CURVE[0])):
                style = "curve"
            if key == "E" and i == E_DOOR_EDGE:
                td, hw = lay["t_door"], DOOR_W / 2
                # collision: either side full height, lintel over the doorway (below the sill is the deck)
                E.quad(col, 0.0, td - hw, 0.0, top, "concrete")
                E.quad(col, td + hw, E.L, 0.0, top, "concrete")
                E.quad(col, td - hw, td + hw, DOOR_TOP, top, "concrete")
                _facade(vis, E, 0.0, td - hw, 0.0, top, style, FLOORS[key])
                _facade(vis, E, td + hw, E.L, 0.0, top, style, FLOORS[key])
                E.quad(vis, td - hw, td + hw, DOOR_TOP, DOOR_TOP + 0.6, "white_trim")
                E.quad(vis, td - hw, td + hw, DOOR_TOP + 0.6, top - STYLE[style]["corn_h"], "window_glass")
                E.quad(vis, td - hw, td + hw, top - STYLE[style]["corn_h"], top, "white_trim")
                # dark door frame around the opening (jambs + head, on the facade)
                E.quad(vis, td - hw - 0.3, td - hw, DECK_Z, DOOR_TOP + 0.3, "dark_trim", off=2 * DECAL)
                E.quad(vis, td + hw, td + hw + 0.3, DECK_Z, DOOR_TOP + 0.3, "dark_trim", off=2 * DECAL)
                E.quad(vis, td - hw, td + hw, DOOR_TOP, DOOR_TOP + 0.3, "dark_trim", off=DECAL)
                # FOOD COURT sign hanging under the arcade canopy's front edge (visual, above head height)
                for sgn, mat in ((1.0, "white_trim"), (-1.0, "white_trim")):
                    q = [E.p(td - 1.8, 4.55, CAN_SE_D - 0.3), E.p(td + 1.8, 4.55, CAN_SE_D - 0.3),
                         E.p(td + 1.8, CAN_SE_Z[0], CAN_SE_D - 0.3), E.p(td - 1.8, CAN_SE_Z[0], CAN_SE_D - 0.3)]
                    vis.poly(q, mat, normal_hint=(sgn * E.n[0], sgn * E.n[1], 0.0))
                E.quad(vis, td - 1.5, td + 1.5, 4.75, 5.05, "dark_trim", off=CAN_SE_D - 0.3 + DECAL)
                continue
            E.quad(col, 0.0, E.L, z_lo, top, "brick_red" if style not in ("glass", "curve") else "window_glass")
            _facade(vis, E, 0.0, E.L, z_lo, top, style, FLOORS[key])
        # roofs
        if key == "C":
            hole = [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)]
            _slab(col, [poly, hole], top, "concrete")
            _slab(vis, [poly, hole], top, "path", uv_tile=5.0)
        elif key == "E":
            _ngon(col, poly, top, "grass")
            _ngon(vis, poly, top, "grass", uv_tile=8.0)
        else:
            _ngon(col, poly, top, "concrete")
            _ngon(vis, poly, top, "concrete", uv_tile=6.0)

    # ---------------------------------------------------------------- tower (hotel floors) + penthouse
    trect = [(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1)]
    for a, c in _edges(trect):
        E = Edge(a, c)
        E.quad(col, 0.0, E.L, Z_C, Z_T, "brick_red")
        _facade(vis, E, 0.0, E.L, Z_C, Z_T, "tower", FLOORS["T"])
        if E.L > 30.0:   # concrete fins on the long faces
            for tf in _cuts(0.0, E.L, 5.0)[1:-1]:
                E.quad(vis, tf - 0.2, tf + 0.2, Z_C, Z_T - 0.6, "white_trim", off=0.18)
    # roof deck inside a 0.6 m parapet (inner faces + cap): keeps Mario on the 27 m roof
    irect = [(tx0 + PAR_T, ty0 + PAR_T), (tx1 - PAR_T, ty0 + PAR_T), (tx1 - PAR_T, ty1 - PAR_T), (tx0 + PAR_T, ty1 - PAR_T)]
    _ngon(col, irect, Z_TD, "concrete")
    _ngon(vis, irect, Z_TD, "roof_dark", uv_tile=6.0)
    for (a, c), (ia, ic) in zip(_edges(trect), _edges(irect)):
        Ei = Edge(ia, ic)
        Ei.quad(col, 0.0, Ei.L, Z_TD, Z_T, "concrete", inward=True)
        Ei.quad(vis, 0.0, Ei.L, Z_TD, Z_T, "concrete", inward=True, max_len=VIS_MAX_LEN)
        cap = [(a[0], a[1], Z_T), (c[0], c[1], Z_T), (ic[0], ic[1], Z_T), (ia[0], ia[1], Z_T)]
        col.poly(cap, "concrete", normal_hint=(0, 0, 1))
        vis.poly(cap, "white_trim", uvs=C.project_uv(cap, 6.0, normal=(0, 0, 1)), normal_hint=(0, 0, 1))
    # REITZ UNION band at the top of the north face (white panel, dark lettering strip)
    En = Edge((tx1, ty1), (tx0, ty1))
    En.quad(vis, 10.0, 30.0, Z_T - 2.35, Z_T - 0.95, "white_trim", off=0.22)
    En.quad(vis, 11.0, 29.0, Z_T - 1.9, Z_T - 1.4, "dark_trim", off=0.25)
    px0, px1, py0, py1 = PENTHOUSE
    for b in (col, vis):
        _box(b, px0, px1, py0, py1, Z_TD, Z_PH, "concrete", faces="tnsew")
    _box(vis, px0 + 2.5, px1 - 2.5, py0 - DECAL, py0 - DECAL, Z_TD, Z_TD + 2.0, "metal_gray", faces="s")   # door
    for k in range(3):   # louvres
        _box(vis, px1 + DECAL, px1 + DECAL, py0 + 1.0 + 1.4 * k, py0 + 2.0 + 1.4 * k, Z_TD + 0.6, Z_TD + 1.6,
             "dark_trim", faces="e")
    # window-washer davit (BMU) + rails on the west face (visual)
    lx, ly = LIFT_XY
    _box(vis, tx0 + 0.6, tx0 + 1.1, ly - 0.25, ly + 0.25, Z_TD, Z_T + 1.6, "metal_gray", faces="nsew")
    _box(vis, lx - 0.4, tx0 + 1.1, ly - 0.2, ly + 0.2, Z_T + 1.6, Z_T + 2.0, "metal_gray", faces="tbnsew")
    for yy in (ly - 1.0, ly + 1.0):
        _box(vis, tx0 - 0.12, tx0 - 0.12, yy - 0.08, yy + 0.08, Z_C, Z_T - 0.1, "metal_gray", faces="w")
    # the hanging cable (pole object) as two crossed thin strips
    cx, cy, cz, ch = CABLE
    for dx, dy in ((0.06, 0.0), (0.0, 0.06)):
        for s in (1, -1):
            vis.poly([(cx - dx, cy - dy, cz), (cx + dx, cy + dy, cz), (cx + dx, cy + dy, cz + ch),
                      (cx - dx, cy - dy, cz + ch)], "dark_trim", uvs=[(0, 0), (0.1, 0), (0.1, 4), (0, 4)],
                     normal_hint=(s * dy, s * dx, 0.0))
    _box(vis, cx - 0.5, tx0, cy - 0.15, cy + 0.15, Z_T + 1.2, Z_T + 1.5, "metal_gray", faces="tbnsw")

    # ---------------------------------------------------------------- tower east ledges (concrete sunshades)
    for y0, y1, z in LEDGES:
        _box(col, tx1, tx1 + LEDGE_D, y0, y1, z - LEDGE_T, z, "concrete", faces="tens")
        _box(vis, tx1, tx1 + LEDGE_D, y0, y1, z - LEDGE_T, z, "white_trim", faces="tbens")

    # ---------------------------------------------------------------- stair penthouse slit window
    Ep = Edge(P_POLY[1], P_POLY[2])
    Ep.quad(vis, 1.8, 3.4, 1.0, Z_P - 1.6, "window_dark", off=DECAL)

    # ---------------------------------------------------------------- ravine-side terraces + awnings (W south wall)
    E_SW = Edge(*SW_WALL)
    for t0, t1, dep, z0, z1 in TERRACES:
        _ebox(col, E_SW, t0, t1, 0.0, dep, z0, z1, "brick_red", faces="tflr", mats={"t": "grass"})
        _ebox(vis, E_SW, t0, t1, 0.0, dep, z0 if z0 > 0 else -0.15, z1, "brick_red", faces="flr")
        _ebox(vis, E_SW, t0, t1, 0.0, dep - 0.4, z1, z1, "grass", faces="t")
        _ebox(vis, E_SW, t0, t1, dep - 0.4, dep, z1, z1, "limestone", faces="t")   # coping
    for t0, t1, z in AWNINGS:
        _ebox(col, E_SW, t0, t1, 0.0, AWN_D, z - AWN_T, z, "metal_gray", faces="tflr")
        _ebox(vis, E_SW, t0, t1, 0.0, AWN_D, z - AWN_T, z, "metal_gray", faces="tblr",
              mats={"t": "copper_green", "b": "white_trim"})
        _ebox(vis, E_SW, t0, t1, 0.0, AWN_D, z - AWN_T, z, "dark_trim", faces="f")
        for tt in (t0 + 0.4, t1 - 0.4):   # diagonal tie rods (visual)
            vis.poly([E_SW.p(tt - 0.05, z - AWN_T, AWN_D - 0.2), E_SW.p(tt + 0.05, z - AWN_T, AWN_D - 0.2),
                      E_SW.p(tt + 0.05, z + 1.4, 0.0), E_SW.p(tt - 0.05, z + 1.4, 0.0)], "dark_trim",
                     normal_hint=(E_SW.n[0], E_SW.n[1], 1.0))

    # ---------------------------------------------------------------- rooftop AC units
    for x0, x1, y0, y1, z0, z1 in (HVAC_W, HVAC_S):
        _box(col, x0, x1, y0, y1, z0, z1, "metal_gray", faces="tnsew")
        _box(vis, x0, x1, y0, y1, z0, z1, "metal_gray", faces="nsew")
        _box(vis, x0 + 0.5, x1 - 0.5, y0 - DECAL, y0 - DECAL, z0 + 0.4, z1 - 0.4, "dark_trim", faces="s")   # grilles
        _box(vis, x0 + 0.5, x1 - 0.5, y1 + DECAL, y1 + DECAL, z0 + 0.4, z1 - 0.4, "dark_trim", faces="n")
        # top: fan grille in the middle, metal frame around it (one layer: no decal over Mario's shadow)
        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
        fx0, fx1, fy0, fy1 = cxm - 1.0, cxm + 1.0, cym - 1.0, cym + 1.0
        _box(vis, fx0, fx1, fy0, fy1, z1, z1, "dark_trim", faces="t")
        for xa, xb, ya, yb in ((x0, x1, y0, fy0), (x0, x1, fy1, y1), (x0, fx0, fy0, fy1), (fx1, x1, fy0, fy1)):
            _box(vis, xa, xb, ya, yb, z1, z1, "metal_gray", faces="t")

    # ---------------------------------------------------------------- E wing: skylight, planters, gator scales
    sx0, sx1, sy0, sy1, sz = SKYLIGHT
    _box(col, sx0, sx1, sy0, sy1, Z_E, sz, "window_glass", faces="tnsew")
    _box(vis, sx0, sx1, sy0, sy1, Z_E, sz, "metal_gray", faces="nsew")
    _box(vis, sx0, sx1, sy0, sy1, sz, sz, "window_glass", faces="t")
    for x0, x1, y0, y1 in PLANTERS:
        _box(col, x0, x1, y0, y1, Z_E, Z_E + PLANTER_H, "brick_red", faces="tnsew", mats={"t": "grass"})
        _box(vis, x0, x1, y0, y1, Z_E, Z_E + PLANTER_H, "brick_red", faces="nsew")
        _box(vis, x0 + 0.25, x1 - 0.25, y0 + 0.25, y1 - 0.25, Z_E + PLANTER_H, Z_E + PLANTER_H, "grass", faces="t")
        for xa, xb, ya, yb in ((x0, x1, y0, y0 + 0.25), (x0, x1, y1 - 0.25, y1), (x0, x0 + 0.25, y0 + 0.25, y1 - 0.25),
                               (x1 - 0.25, x1, y0 + 0.25, y1 - 0.25)):
            _box(vis, xa, xb, ya, yb, Z_E + PLANTER_H, Z_E + PLANTER_H, "limestone", faces="t")
        _prism_post(vis, (x0 + x1) / 2, (y0 + y1) / 2, 0.25, Z_E + PLANTER_H, Z_E + PLANTER_H + 1.6, "door_wood", 4)
        _cone(vis, (x0 + x1) / 2, (y0 + y1) / 2, 1.7, Z_E + PLANTER_H + 1.3, Z_E + PLANTER_H + 3.0, "copper_green", 6)
    for i in (12, 7):   # E north face segments (-399.5 -> -410.41) and (-359.63 -> -370.51)
        a, c = E_POLY[i], E_POLY[(i + 1) % len(E_POLY)]
        Eg = Edge(a, c)
        _gator_scales(vis, Eg, 0.8, Eg.L - 0.8, 4.6, 3 if Eg.L > 10.5 else 2)
    Eg = Edge(E_POLY[11], E_POLY[12])    # (-383.91 -> -399.5): the longest north segment
    _gator_scales(vis, Eg, 0.8, Eg.L - 0.8, 4.6, 3)

    # ---------------------------------------------------------------- north colonnade + entrance + signs
    z0n, z1n = CANOPY_N_Z
    _ngon(col, CANOPY_N, z1n, "concrete")
    _ngon(vis, CANOPY_N, z1n, "concrete", uv_tile=6.0)
    _ngon(vis, CANOPY_N, z0n, "white_trim", up=False, uv_tile=6.0)
    for i in (3, 4, 5):   # free edges: east end, north front, west end
        a, c = CANOPY_N[i], CANOPY_N[(i + 1) % len(CANOPY_N)]
        Ec = Edge(a, c)
        Ec.quad(col, 0.0, Ec.L, z0n, z1n, "concrete")
        Ec.quad(vis, 0.0, Ec.L, z0n - 0.15, z1n + 0.05, "white_trim", max_len=VIS_MAX_LEN)
    for xp in PIERS_X:
        y0p, y1p = PIER_Y
        _box(col, xp - PIER_W / 2, xp + PIER_W / 2, y0p, y1p, 0.0, z0n, "brick_red", faces="nsew")
        _box(vis, xp - PIER_W / 2, xp + PIER_W / 2, y0p, y1p, 0.5, z0n - 0.4, "brick_red", faces="nsew")
        _box(vis, xp - PIER_W / 2 - 0.08, xp + PIER_W / 2 + 0.08, y0p - 0.08, y1p + 0.08, -0.15, 0.5, "limestone",
             faces="tnsew")
        _box(vis, xp - PIER_W / 2 - 0.08, xp + PIER_W / 2 + 0.08, y0p - 0.08, y1p + 0.08, z0n - 0.4, z0n, "limestone",
             faces="nsew")
    # lamp post (pole object) at the colonnade's west end
    lxp, lyp, lzp, lh = LAMP
    _prism_post(vis, lxp, lyp, 0.12, lzp, lzp + lh, "dark_trim", 4)
    _box(vis, lxp - 0.35, lxp + 0.35, lyp - 0.35, lyp + 0.35, lh - 0.1, lh + 0.25, "dark_trim", faces="tnsewb",
         mats={"b": "white_trim"})
    # REITZ UNION sign band on the C north face above the canopy
    Ecn = Edge(C_POLY[0], C_POLY[1])
    Ecn.quad(vis, 6.0, 38.0, 5.0, 6.6, "white_trim", off=0.08, max_len=VIS_MAX_LEN)
    Ecn.quad(vis, 7.0, 37.0, 5.55, 6.05, "dark_trim", off=0.11, max_len=VIS_MAX_LEN)
    # north entrance recess: glass doors at the back, transom
    Erb = Edge(C_POLY[2], C_POLY[3])
    _glass_doors(vis, Erb, Erb.L / 2, 2.6, 3.0)
    Erb.quad(vis, 0.2, Erb.L - 0.2, 3.3, 4.0, "window_glass", off=DECAL)
    # Game Room (bowling) door + sign, and the second Level 0 north door (OSM 4431967751)
    Wn = Edge(W_POLY[0], W_POLY[1])
    tg = Wn.t_of((-485.22, -242.73))
    _glass_doors(vis, Wn, tg, 2.4, 2.8)
    Wn.quad(vis, tg - 1.7, tg + 1.7, 3.1, 4.2, "white_trim", off=0.08)
    for zz in (3.35, 3.75):   # bowling-pin neck stripes
        Wn.quad(vis, tg - 1.5, tg + 1.5, zz, zz + 0.14, "brick_red", off=0.11)
    Wn.quad(vis, tg + 0.9, tg + 1.4, 3.3, 4.0, "dark_trim", off=0.12)    # the ball
    _glass_doors(vis, Wn, Wn.t_of((-470.07, -242.75)), 2.2, 2.8)
    Ee = Edge(E_POLY[4], E_POLY[5])
    _glass_doors(vis, Ee, Ee.t_of((-359.83, -248.61)), 2.4, 2.8, off=0.18)

    # ---------------------------------------------------------------- SE arcade canopy + light shelves
    zc0, zc1 = CAN_SE_Z
    out_c = _offset_open(CAN_SE_COL, CAN_SE_D)
    for i in range(len(CAN_SE_COL) - 1):
        a, c, a2, c2 = CAN_SE_COL[i], CAN_SE_COL[i + 1], out_c[i], out_c[i + 1]
        col.poly([(a[0], a[1], zc1), (c[0], c[1], zc1), (c2[0], c2[1], zc1), (a2[0], a2[1], zc1)], "metal_gray",
                 normal_hint=(0, 0, 1))
        Ef = Edge(a2, c2)
        Ef.quad(col, 0.0, Ef.L, zc0, zc1, "metal_gray")
    for a, a2, nxt in ((CAN_SE_COL[0], out_c[0], CAN_SE_COL[1]), (CAN_SE_COL[-1], out_c[-1], CAN_SE_COL[-2])):
        hint = (a[0] - nxt[0], a[1] - nxt[1], 0.0)    # end caps face away from the canopy
        _vquad(col, a, a2, zc0, zc1, "metal_gray", hint)
        _vquad(vis, a, a2, zc0 - 0.05, zc1 + 0.05, "white_trim", hint)
    out_v = _offset_open(CAN_SE, CAN_SE_D)
    for i in range(len(CAN_SE) - 1):
        a, c, a2, c2 = CAN_SE[i], CAN_SE[i + 1], out_v[i], out_v[i + 1]
        vis.poly([(a[0], a[1], zc1), (c[0], c[1], zc1), (c2[0], c2[1], zc1), (a2[0], a2[1], zc1)], "metal_gray",
                 normal_hint=(0, 0, 1))
        vis.poly([(a[0], a[1], zc0), (c[0], c[1], zc0), (c2[0], c2[1], zc0), (a2[0], a2[1], zc0)], "white_trim",
                 normal_hint=(0, 0, -1))
        Ef = Edge(a2, c2)
        Ef.quad(vis, 0.0, Ef.L, zc0 - 0.05, zc1 + 0.05, "white_trim")
    for a, c, t0, t1, z in SHADES:
        Eh = Edge(a, c)
        _ebox(col, Eh, t0, t1, 0.0, SHADE_D, z - SHADE_T, z, "concrete", faces="tflr")
        _ebox(vis, Eh, t0, t1, 0.0, SHADE_D, z - SHADE_T, z, "white_trim", faces="tbflr")

    # ---------------------------------------------------------------- enterable food court (Level 1)
    _build_food_court(vis, col, lay)
    return vis, col


def _build_food_court(vis, col, lay):
    inner = _offset_closed(ROOM, WALL_T)
    n = len(ROOM)
    Es = Edge(E_POLY[E_DOOR_EDGE], E_POLY[E_DOOR_EDGE + 1])
    td, hw = lay["t_door"], DOOR_W / 2
    door_x = (Es.xy(td - hw)[0], Es.xy(td + hw)[0])
    # floor + ceiling (the room outline reaches the outer wall line; the inner walls keep Mario out)
    _ngon(col, ROOM, DECK_Z, "concrete")
    _ngon(vis, ROOM, DECK_Z, "path", uv_tile=6.0)
    _ngon(col, ROOM, CEIL_Z, "white_trim", up=False)
    _ngon(vis, ROOM, CEIL_Z, "white_trim", up=False, uv_tile=6.0)
    # threshold: a floor strip across the doorway overlapping the deck and the room floor
    th_in, th_out = Es.xy(td, -WALL_T - 0.6), Es.xy(td, 0.6)
    _box(col, door_x[0] - 0.2, door_x[1] + 0.2, th_out[1], th_in[1], DECK_Z, DECK_Z, "concrete", faces="t")
    # inner wall faces (facing into the room)
    for i in range(n):
        a, c = inner[i], inner[(i + 1) % n]
        Ei = Edge(a, c)
        mat = "window_glass" if i in ROOM_GLASS else "white_trim"
        if i == ROOM_DOOR_EDGE:
            t0 = Ei.t_of((door_x[0], _y_on(a, c, door_x[0])))
            t1 = Ei.t_of((door_x[1], _y_on(a, c, door_x[1])))
            Ei.quad(col, 0.0, t0, DECK_Z, CEIL_Z, "white_trim", inward=True)
            Ei.quad(col, t1, Ei.L, DECK_Z, CEIL_Z, "white_trim", inward=True)
            Ei.quad(col, t0, t1, DOOR_TOP, CEIL_Z, "white_trim", inward=True)
            Ei.quad(vis, 0.0, t0, DECK_Z, CEIL_Z, "window_glass", inward=True)
            Ei.quad(vis, t1, Ei.L, DECK_Z, CEIL_Z, "window_glass", inward=True)
            Ei.quad(vis, t0, t1, DOOR_TOP, CEIL_Z, "white_trim", inward=True)
            # reveals + soffit between the outer and the inner face
            for x, s in ((door_x[0], 1.0), (door_x[1], -1.0)):
                po = (x, _y_on(Es.a, Es.c, x))
                pi = (x, _y_on(a, c, x))
                for b, m in ((col, "concrete"), (vis, "concrete")):
                    _vquad(b, po, pi, DECK_Z, DOOR_TOP, m, (s * Es.d[0], s * Es.d[1], 0.0))
            q = [(door_x[0], _y_on(Es.a, Es.c, door_x[0]), DOOR_TOP), (door_x[1], _y_on(Es.a, Es.c, door_x[1]), DOOR_TOP),
                 (door_x[1], _y_on(a, c, door_x[1]), DOOR_TOP), (door_x[0], _y_on(a, c, door_x[0]), DOOR_TOP)]
            col.poly(q, "concrete", normal_hint=(0, 0, -1))
            vis.poly(q, "concrete", normal_hint=(0, 0, -1))
            continue
        Ei.quad(col, 0.0, Ei.L, DECK_Z, CEIL_Z, mat, inward=True)
        if mat == "window_glass":
            Ei.quad(vis, 0.0, Ei.L, DECK_Z, DECK_Z + 0.4, "metal_gray", inward=True)
            Ei.quad(vis, 0.0, Ei.L, DECK_Z + 0.4, CEIL_Z, "window_glass", inward=True)
        else:
            Ei.quad(vis, 0.0, Ei.L, DECK_Z, DECK_Z + 1.0, "concrete", inward=True, max_len=VIS_MAX_LEN)
            Ei.quad(vis, 0.0, Ei.L, DECK_Z + 1.0, CEIL_Z, "white_trim", inward=True, max_len=VIS_MAX_LEN)
    # vendor fronts (west / north inside faces): back panel, menu board, sign band (decals)
    Ew = Edge(inner[n - 1], inner[0])          # west wall, runs south (t from the NW corner)
    En = Edge(inner[n - 2], inner[n - 1])      # north wall, runs west (t from the NE corner)
    for wall, t0, t1, mcol in VENDORS:
        Ev = Ew if wall == "W" else En
        if wall == "N":
            t0, t1 = Ev.L - t1, Ev.L - t0
        Ev.quad(vis, t0, t1, DECK_Z + 1.0, DECK_Z + 3.4, "door_wood", off=-DECAL, inward=True)
        Ev.quad(vis, t0 + 0.4, t1 - 0.4, DECK_Z + 2.0, DECK_Z + 3.0, "dark_trim", off=-2 * DECAL, inward=True)
        Ev.quad(vis, t0, t1, DECK_Z + 3.4, DECK_Z + 4.2, mcol, off=-DECAL, inward=True)
        Ev.quad(vis, t0 + 0.6, t1 - 0.6, DECK_Z + 3.65, DECK_Z + 3.95, "white_trim", off=-2 * DECAL, inward=True)
    # serving counter along the west wall + communal tables
    x0, x1, y0, y1, zt = COUNTER
    _box(col, x0, x1, y0, y1, DECK_Z, zt, "metal_gray", faces="tens")
    ym = (y0 + y1) / 2
    for ya, yb in ((y0, ym), (ym, y1)):    # two halves: <= 12 texture repeats per face
        _box(vis, x0, x1, ya, yb, DECK_Z, zt, "metal_gray", faces="e")
        _box(vis, x0, x1 + 0.1, ya, yb, zt, zt + 0.05, "white_trim", faces="te")
    _box(vis, x0, x1, y0, y1, DECK_Z, zt, "metal_gray", faces="ns")
    _box(vis, x0, x1 + 0.1, y0, y1, zt, zt + 0.05, "white_trim", faces="ns")
    for x0, x1, y0, y1 in TABLES:
        _box(col, x0, x1, y0, y1, DECK_Z, DECK_Z + TABLE_H, "door_wood", faces="tnsew")
        _box(vis, x0, x1, y0, y1, DECK_Z + TABLE_H - 0.08, DECK_Z + TABLE_H, "white_trim", faces="tnsew")
        _box(vis, x0 + 0.3, x1 - 0.3, y0 + 0.2, y1 - 0.2, DECK_Z, DECK_Z + TABLE_H - 0.08, "door_wood", faces="nsew")
        for yy in (y0 - 0.45, y1 + 0.45):   # benches (visual)
            _box(vis, x0 + 0.2, x1 - 0.2, yy - 0.2, yy + 0.2, DECK_Z, DECK_Z + 0.45, "door_wood", faces="tnsew")


def _build_amphi(ctx, al):
    vis, col = C.Builder(), C.Builder()
    O_c, I_c, O_v, I_v = al["O_c"], al["I_c"], al["O_v"], al["I_v"]
    # ---------------------------------------------------------------- South Terrace deck (2.0 m)
    deck_c = O_c + DECK_TAIL
    deck_v = O_v + DECK_TAIL
    _ngon(col, deck_c, DECK_Z, "concrete")
    _ngon(vis, deck_v, DECK_Z, "path", uv_tile=4.0)
    free = [(DECK_TAIL[-1], O_c[0]), (O_c[-1], DECK_TAIL[0]), (DECK_TAIL[0], DECK_TAIL[1])]
    for a, c in free:
        E = Edge(a, c)
        E.quad(col, 0.0, E.L, 0.0, DECK_Z, "concrete")
        E.quad(vis, 0.0, E.L, -0.15, DECK_Z - 0.25, "concrete")
        E.quad(vis, 0.0, E.L, DECK_Z - 0.25, DECK_Z, "white_trim")
    # ---------------------------------------------------------------- amphitheater: collision ramp
    for i in range(N_COL):
        q = [(O_c[i][0], O_c[i][1], DECK_Z), (O_c[i + 1][0], O_c[i + 1][1], DECK_Z),
             (I_c[i + 1][0], I_c[i + 1][1], 0.0), (I_c[i][0], I_c[i][1], 0.0)]
        col.poly(q, "grass", normal_hint=(0, 0, 1))
    for (o, i_, o2, i2) in ((O_c[0], I_c[0], O_c[1], I_c[1]), (O_c[-1], I_c[-1], O_c[-2], I_c[-2])):
        mid_in = _lerp(o2, i2, 0.5)
        mid = _lerp(o, i_, 0.5)
        col.poly([(i_[0], i_[1], 0.0), (o[0], o[1], 0.0), (o[0], o[1], DECK_Z)], "concrete",
                 normal_hint=(mid[0] - mid_in[0], mid[1] - mid_in[1], 0.0))
    # ---------------------------------------------------------------- amphitheater: visual tiers
    fk = [k / N_TIERS for k in range(N_TIERS + 1)]
    zk = [0.0] + [DECK_Z * k / N_TIERS - DECK_Z / (2 * N_TIERS) for k in range(1, N_TIERS + 1)]
    rows = [[_lerp(I_v[i], O_v[i], f) for i in range(N_VIS + 1)] for f in fk]
    for k in range(1, N_TIERS + 1):
        A, B = rows[k - 1], rows[k]
        for i in range(N_VIS):
            vis.poly([(A[i][0], A[i][1], zk[k]), (A[i + 1][0], A[i + 1][1], zk[k]), (B[i + 1][0], B[i + 1][1], zk[k]),
                      (B[i][0], B[i][1], zk[k])], "grass", normal_hint=(0, 0, 1))
            zlo = -0.15 if k == 1 else zk[k - 1]
            ctr = _lerp(B[i], B[i + 1], 0.5)
            mid = _lerp(A[i], A[i + 1], 0.5)
            vis.poly([(A[i][0], A[i][1], zlo), (A[i + 1][0], A[i + 1][1], zlo), (A[i + 1][0], A[i + 1][1], zk[k]),
                      (A[i][0], A[i][1], zk[k])], "concrete", normal_hint=(mid[0] - ctr[0], mid[1] - ctr[1], 0.0))
    for i in range(N_VIS):   # riser from the top tier up to the deck at the outer arc
        A = rows[-1]
        ctr = _lerp(I_v[i], I_v[i + 1], 0.5)
        mid = _lerp(A[i], A[i + 1], 0.5)
        vis.poly([(A[i][0], A[i][1], zk[-1]), (A[i + 1][0], A[i + 1][1], zk[-1]), (A[i + 1][0], A[i + 1][1], DECK_Z),
                  (A[i][0], A[i][1], DECK_Z)], "white_trim", normal_hint=(ctr[0] - mid[0], ctr[1] - mid[1], 0.0))
    # stepped cheeks at both ends
    for j, j2 in ((0, 1), (N_VIS, N_VIS - 1)):
        prof = [(rows[0][j], -0.15), (rows[-1][j], -0.15)]
        for k in range(N_TIERS, 0, -1):
            prof.append((rows[k][j], zk[k]))
            prof.append((rows[k - 1][j], zk[k]))
        pts = []
        for p, z in prof:
            if not pts or math.dist(pts[-1][:2], p) > 1e-6 or abs(pts[-1][2] - z) > 1e-6:
                pts.append((p[0], p[1], z))
        inside = _lerp(rows[2][j2], rows[3][j2], 0.5)
        here = _lerp(rows[2][j], rows[3][j], 0.5)
        vis.poly(pts, "concrete", normal_hint=(here[0] - inside[0], here[1] - inside[1], 0.0))
    # ---------------------------------------------------------------- veterans memorial plinths
    tw, rd, hh = MEMORIAL_SIZE
    for x, y, a in al["plinths"]:
        ur = (math.cos(a), math.sin(a))          # radial (away from the pond)
        ut = (-ur[1], ur[0])
        corners = [(x + ut[0] * sx * tw / 2 + ur[0] * sy * rd / 2, y + ut[1] * sx * tw / 2 + ur[1] * sy * rd / 2)
                   for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        poly = C.ccw(corners)
        for b in (col, vis):
            for p, q in _edges(poly):
                mx, my = (p[0] + q[0]) / 2 - x, (p[1] + q[1]) / 2 - y
                _vquad(b, p, q, 0.0 if b is col else -0.15, hh, "rock", (mx, my, 0.0))
            _ngon(b, poly, hh, "rock")
        # bronze plaque on the face toward the seats
        f0 = (x + ur[0] * (rd / 2 + 0.02), y + ur[1] * (rd / 2 + 0.02))
        pa = (f0[0] - ut[0] * 0.3, f0[1] - ut[1] * 0.3)
        pc = (f0[0] + ut[0] * 0.3, f0[1] + ut[1] * 0.3)
        _vquad(vis, pa, pc, 0.55, 1.05, "bronze", (ur[0], ur[1], 0.0))
    # ---------------------------------------------------------------- Liberty Pond fountain float + jet
    cx, cy = POND_C
    hexa = [(cx + FOUNTAIN_R * math.cos(math.pi * k / 3), cy + FOUNTAIN_R * math.sin(math.pi * k / 3)) for k in range(6)]
    inner = [(cx + (FOUNTAIN_R - 0.45) * math.cos(math.pi * k / 3), cy + (FOUNTAIN_R - 0.45) * math.sin(math.pi * k / 3))
             for k in range(6)]
    for p, q in _edges(hexa):
        mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy
        _vquad(col, p, q, POND_FLOOR, FOUNTAIN_TOP, "concrete", (mx, my, 0.0))
        _vquad(vis, p, q, POND_FLOOR - 0.1, FOUNTAIN_TOP, "concrete", (mx, my, 0.0))
    _ngon(col, hexa, FOUNTAIN_TOP, "concrete")
    for (p, q), (ip, iq) in zip(_edges(hexa), _edges(inner)):
        vis.poly([(p[0], p[1], FOUNTAIN_TOP), (q[0], q[1], FOUNTAIN_TOP), (iq[0], iq[1], FOUNTAIN_TOP),
                  (ip[0], ip[1], FOUNTAIN_TOP)], "white_trim", normal_hint=(0, 0, 1))
    _ngon(vis, inner, FOUNTAIN_TOP, "water")
    _cone(vis, cx, cy, 0.3, FOUNTAIN_TOP, 5.5, "water", 6)
    _cone(vis, cx, cy, 1.0, FOUNTAIN_TOP, 2.4, "water", 6)
    return vis, col


# =================================================================== contract
_LAY = _layout()
_AL = _amphi_layout()

LANDMARKS = [
    {
        "slug": "reitz_union",
        "name": "J. Wayne Reitz Union",
        "osm_ids": [RU_ID],
        "stages": list(STAGES),
        "center_m": (-436.84, -277.13),     # OSM footprint centroid
        "height_m": Z_T,
        "doors": _LAY["doors"],
        "spots": _LAY["spots"],
        "climb_route_m": [_r(p) for _, p in _LAY["route"]],
        "markers": _LAY["markers"],
        "top_platform": {"z_m": Z_PH, "center_m": _r(((PENTHOUSE[0] + PENTHOUSE[1]) / 2, (PENTHOUSE[2] + PENTHOUSE[3]) / 2)),
                         "half_m": [round((PENTHOUSE[1] - PENTHOUSE[0]) / 2, 2), round((PENTHOUSE[3] - PENTHOUSE[2]) / 2, 2)],
                         "note": "elevator penthouse (7 x 6 m) on the 40 x 22 m tower roof (deck 26.4 m inside a "
                                 "0.6 m parapet, top 27.0 m); act 1 roof star spot = spots['roof_star']"},
    },
    {
        "slug": "reitz_amphitheater",
        "name": "Reitz Union Amphitheater, South Terrace and Liberty Pond fountain",
        "osm_ids": [],
        "osm_area_ids": [AMPHI_ID],
        "replaces_areas": [AMPHI_ID, TERRACE_ID],
        "replaces_ways": ["w863456040"],     # OSM steps along the seats' west end (the ramp is drawn here)
        "stages": list(STAGES),
        "center_m": (-383.9, -305.1),       # OSM amphitheater centroid (stages.json)
        "height_m": DECK_Z,
        "doors": [],
        "spots": _AL["spots"],
        "markers": {"memorial_plinths_m": [_r((x, y, 0.0)) for x, y, _ in _AL["plinths"]],
                    "fountain_m": _r((POND_C[0], POND_C[1], FOUNTAIN_TOP)),
                    "levels_m": {"south_terrace": DECK_Z, "amphitheater_bottom": 0.0, "fountain_float": FOUNTAIN_TOP,
                                 "pond_water": -0.3}},
    },
]


def _check(ctx):
    """Warn if the OSM data this module was built on has changed."""
    try:
        fp = C.footprint(ctx, RU_ID)
    except KeyError:
        print(f"reitz_reitz_union: WARNING {RU_ID} not in campus.json")
        return
    ref = [(-410.41, -243.45), (-521.03, -242.41), (-523.31, -262.35), (-464.62, -336.2), (-388.39, -288.65),
           (-359.63, -242.94)]
    if not all(any(math.dist(p, q) < 0.05 for q in fp) for p in ref):
        print("reitz_reitz_union: WARNING Reitz Union footprint changed in campus.json")
    areas = {a["id"]: a for a in ctx.get("campus", {}).get("areas", [])}
    am = areas.get(AMPHI_ID)
    if am is None or not all(any(math.dist(p, q) < 0.05 for q in am["pts"]) for p in (OUTER_ARC[0], INNER_ARC[-1])):
        print("reitz_reitz_union: WARNING amphitheater area changed in campus.json")


def build(ctx):
    """-> [{"name", "mesh", "material_slots", "collision", "visual", "landmark"}, ...] (map metres, z up)."""
    key = ctx.get("stage_key")
    if key is not None and key not in STAGES:
        return []
    _check(ctx)
    parts = []
    u_vis, u_col = _build_union(ctx, _LAY)
    a_vis, a_col = _build_amphi(ctx, _AL)
    for slug, vis, col in (("reitz_union", u_vis, u_col), ("reitz_amphitheater", a_vis, a_col)):
        me, slots = vis.build(f"{slug} visual")
        p = C.part(f"{slug} visual", me, slots, collision=False, visual=True)
        p["landmark"] = slug
        parts.append(p)
        me, slots = col.build(f"{slug} collision")
        p = C.part(f"{slug} collision", me, slots, collision=True, visual=False)
        p["landmark"] = slug
        parts.append(p)
        print(f"reitz_reitz_union: {slug}: visual {vis.tri_count()} tris, collision {col.tri_count()} tris")
    return parts
