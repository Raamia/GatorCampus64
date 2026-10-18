# GatorCampus 64 - campus map renders, stage windows and geometry budgets.
#
# Reads data/uf/campus.json (+ the raw OSM tiles for multipolygon relations such as
# Lake Alice and the stadium bowl, which campus.json does not carry) and writes:
#   art/campus/map_overview.png      whole extracted area
#   art/campus/map_stages.png        the four stage windows
#   art/campus/stage_<key>.png       one zoomed map + budget panel per stage
#   data/uf/stages.json              windows, landmarks, height + simplification rules, budgets
#
# Map data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
#
# Usage: tools/.venv/bin/python -I tools/campus/stage_planner.py
import datetime
import glob
import json
import math
import os
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "uf")
ART = os.path.join(ROOT, "art", "campus")
M_PER_DEG_LAT = 111_320.0

# ----------------------------------------------------------------------------------------------
# Engine facts (sm64coopdx v1.5.1, EXTENDED_BOUNDS_MODE 3)
# ----------------------------------------------------------------------------------------------
UNITS_PER_M = 100            # Mario ~161 units ~ 1.6 m
LEVEL_MAX = 32767
CELL_UNITS = 0x400           # CELL_SIZE in mode 3
NUM_CELLS = 64               # 2 * 0x8000 / 0x400
SURFACE_POOL = 0x4000        # design cap (see notes in stages.json)
RESERVE_OBJECTS = 4000       # left for objects, players, dynamic platforms
GROUND_PATCH_M = 4 * CELL_UNITS / UNITS_PER_M   # 40.96 m collision ground patches (4x4 cells)
PLAY_MARGIN_M = 50           # outer band of every window = visual-only backdrop

# ----------------------------------------------------------------------------------------------
# Stage windows (map meters, x = east, y = north, origin = Century Tower)
# ----------------------------------------------------------------------------------------------
STAGES = [
    {
        "key": "hub", "name": "Hub - Plaza of the Americas + Century Tower",
        "center": (-45, 98), "size": 580, "color": (42, 120, 214),
        "entrance": "Game start; Century Tower is the 'castle'. Building doors act as paintings.",
        "landmarks": [
            ("w150860043", "Century Tower", "hero", 450, 1600,
             "Climbable exterior (buttress ledges, belfry arches); door -> Century Tower interior stage; "
             "finale arena sits on top (47.9 m = 4790 units)."),
            ("w154223635", "University Auditorium", "detailed", 300, 1200, "Collegiate Gothic, pitched roof + front arcade."),
            ("r12122775/196848215", "Library West", "detailed", 250, 900, "Door -> Library West interior stage."),
            ("w154223625", "Smathers Library", "detailed", 300, 1000, "Library East; faces the Plaza."),
            ("w150860048", "Marston Science Library", "detailed", 250, 900, "Door -> Marston interior stage."),
            ("w150684197", "Turlington Hall", "detailed", 300, 1000, "Plaza + courtyard; Turlington rock in front."),
            ("w150926632", "The Hub", "detailed", 200, 700, "Door -> Reitz + Engineering (it faces south-west, toward Reitz)."),
            ("w150926630", "Newell Hall", "detailed", 150, 600, "Door -> The Swamp (west side, toward the stadium)."),
            ("w264182367", "Plaza of the Americas", "terrain", 120, 900,
             "Lawn + diagonal walks; live oaks as climbable tree objects (0 static tris)."),
            ("n4741925737", "Turlington rock ('The Potato')", "prop", 40, 200, "3 m boulder; 1984 marker; hide-and-seek spot."),
        ],
    },
    {
        "key": "swamp", "name": "The Swamp - Ben Hill Griffin Stadium district",
        "center": (-580, 160), "size": 600, "color": (74, 58, 167), "play_margin": 40,
        "entrance": "Hub: Newell Hall door (west side, toward the stadium).",
        "landmarks": [
            ("r1640985/45719890", "Ben Hill Griffin Stadium", "hero", 2600, 9000,
             "Bowl from OSM outer + inner rings; field sunk 10 m (~30 rows below grade); "
             "lower bowl 8 terraces + upper decks 6 terraces, west skybox tower; tunnels."),
            ("w45719889", "Exactech Arena (O'Connell Center)", "detailed", 350, 1200, "Low dome; roof is a race checkpoint."),
            ("w45719891", "Florida Gym", "detailed", 200, 700, ""),
            ("w668261582", "Roberts' Stadium Club", "backdrop", 0, 500, "Across University Ave; straddles the play edge -> visual only."),
            ("w857391716", "Heisman Plaza", "terrain", 60, 600, "Heisman statues as objects."),
            ("n7984819939", "Bull Gator statue", "prop", 60, 400, "Object."),
            ("n7994037191", "Gatorade birthplace marker", "prop", 20, 100, "Object."),
        ],
    },
    {
        "key": "reitz_eng", "name": "Reitz Union + Engineering quad",
        "center": (-470, -293), "size": 600, "color": (200, 60, 120), "play_margin": 30,
        "entrance": "Hub: The Hub door (south-west side).",
        "landmarks": [
            ("w863211313", "J. Wayne Reitz Union", "hero", 500, 1800, "Enterable ground floor + food court; roof terraces."),
            ("w863211344", "Reitz Union Amphitheater", "terrain", 150, 500, "Terraced seating ring."),
            ("w445808709", "Weil Hall", "detailed", 300, 1000, ""),
            ("w481256532", "Engineering Clock Tower", "detailed", 60, 300, "8 m tower on Engineering Plaza."),
            ("w1094502850", "Malachowsky Hall", "detailed", 300, 1200, "Glass atrium; newest building (2023)."),
            ("w150928196", "Reitz Ravine Woods", "terrain", 300, 1500, "Ravine dip + boardwalk; only real relief in the stage."),
            ("w294203169", "Reitz Union North Lawn", "terrain", 40, 300, "Open lawn, race start/finish."),
        ],
    },
    {
        "key": "lake_alice", "name": "Lake Alice",
        "center": (-1760, -660), "size": 600, "color": (21, 140, 98),
        "entrance": "Hub: Turlington Hall door (west side; Lake Alice is the farthest west).",
        "landmarks": [
            ("rel1630473", "Lake Alice (water)", "terrain", 450, 2500,
             "Basin: lake bed + banks from the OSM outer ring (decimated to 64 verts) + 3 bog islands; "
             "one water box (env region) over the lake bbox."),
            ("w424512419", "Bat House", "detailed", 60, 400, "Bat houses on the north side of Museum Road."),
            ("w196848221", "Bat House", "detailed", 60, 400, ""),
            ("w866087250", "Bat House", "detailed", 60, 400, "OSM maps 3; UF says 2 are active now - check photos."),
            ("w1493433580", "Bat House Gardens", "terrain", 20, 200, ""),
            ("w425690658", "Baughman Center", "detailed", 150, 600, "Lakeside pavilion/chapel (2000), steep gable roof."),
        ],
    },
]

INTERIOR_STAGES = [
    {"key": "century_tower_interior", "osm_id": "w150860043", "name": "Century Tower interior",
     "floors": None, "notes": "Vertical stage: 194 steps to the carillon; 61 bells (Wikipedia). Ends at the "
                              "belfry -> finale 'the Final Exam' on top."},
    {"key": "marston_interior", "osm_id": "w150860048", "name": "Marston Science Library interior",
     "floors": 5, "notes": "5 floors (UF ULC minutes 2026 / Wikipedia); aquarium on 3rd floor; Makerspace on 1st."},
    {"key": "library_west_interior", "osm_id": "r12122775/196848215", "name": "Library West interior",
     "floors": 6, "notes": "6 floors after the 2006 renovation (R-BARC architect page); 6th floor = grad study."},
]

# ----------------------------------------------------------------------------------------------
# Heights
# ----------------------------------------------------------------------------------------------
LANDMARK_HEIGHTS = [
    # osm_id, name, height_m, floors, basis, source_title, url, confidence
    ("w150860043", "Century Tower", 47.9, None, "published height 157 ft",
     "Century Tower (University of Florida) - Wikipedia", "https://en.wikipedia.org/wiki/Century_Tower_(University_of_Florida)", "high"),
    ("r12122775/196848215", "Library West", 26.0, 6, "6 floors x 4.0 m + 2 m parapet/roof (OSM says 5 levels)",
     "R-BARC: University of Florida Library West", "https://r-barc.com/work/university-of-florida-library-west", "medium"),
    ("w150860048", "Marston Science Library", 22.5, 5, "5 floors x 4.2 m + 1.5 m",
     "Wikipedia: UF Marston Science Library; UF ULC minutes 2026-02-26",
     "https://en.wikipedia.org/wiki/University_of_Florida_Marston_Science_Library", "medium"),
    ("w150684197", "Turlington Hall", 20.0, 5, "OSM building:levels=5 x 3.8 m + 1 m; floor count not confirmed by a public source",
     "OpenStreetMap way 150684197", "https://www.openstreetmap.org/way/150684197", "low"),
    ("w154223635", "University Auditorium", 18.0, None, "Collegiate Gothic hall; ridge estimate from OSM levels=3 + pitched roof",
     "Wikipedia: University Auditorium (Gainesville, Florida)",
     "https://en.wikipedia.org/wiki/University_Auditorium_(Gainesville,_Florida)", "low"),
    ("w863211313", "J. Wayne Reitz Union", 27.0, 6, "hotel occupies 5th + 6th floors -> 6 floors x 4.2 m + 2 m; OSM says 8 levels",
     "UF conference accommodations page (Reitz Union Hotel, 5th and 6th floors)",
     "https://conference.ifas.ufl.edu/waterinstitute/past/waterinstitute20/accommodations.html", "medium"),
    ("w445808709", "Weil Hall", 24.0, 6, "6 levels x 3.8 m + 1 m",
     "UF Herbert Wertheim College of Engineering building directory: Joseph Weil Hall",
     "https://www.eng.ufl.edu/facilities/hwcoe-buildings-information/hwcoe-building-directory/name/joseph-weil-hall", "medium"),
    ("w1094502850", "Malachowsky Hall", 33.0, 7, "7 stories x 4.5 m (lab floors) + 1.5 m; 263,440 sq ft",
     "UF News 2020-12: UF to begin construction on Malachowsky Hall", "https://news.ufl.edu/2020/12/malachowsky-hall-/", "medium"),
    ("w154223625", "Smathers Library", 18.0, 4, "OSM levels=4 x 3.8 m + pitched roof",
     "OpenStreetMap way 154223625", "https://www.openstreetmap.org/way/154223625", "low"),
    ("r1640985/45719890", "Ben Hill Griffin Stadium", 24.0, None,
     "main east/west stands top at 24 m above street grade (OSM building:part); field at -10 m; skybox tower to 66 m",
     "OpenStreetMap relation 1640985 + building:part ways; Wikipedia (~30 rows below grade)",
     "https://en.wikipedia.org/wiki/Ben_Hill_Griffin_Stadium", "medium"),
    ("w425690658", "Baughman Center", 12.0, 1, "estimate: tall gable 'cathedral' roof pavilion, 1,500 sq ft, built 2000; no published height",
     "Wikipedia: Baughman Center", "https://en.wikipedia.org/wiki/Baughman_Center", "low"),
    ("w45719889", "Exactech Arena (O'Connell Center)", 28.0, None, "estimate for the dome crown; no public height found",
     "estimate", "", "low"),
    ("w45719891", "Florida Gym", 14.0, None, "estimate (1949 gym hall); no public height found", "estimate", "", "low"),
    ("w196848221", "Bat House", 10.7, None, "original UF bat house ~35 ft tall x 16 ft across (OSM: 9 m)",
     "UF bat houses page", "https://bats.ufl.edu/?p=2291", "medium"),
    ("w424512419", "Bat House", 9.0, None, "OSM height=9", "OpenStreetMap", "https://www.openstreetmap.org/way/424512419", "low"),
    ("w866087250", "Bat House", 9.0, None, "OSM height=9", "OpenStreetMap", "https://www.openstreetmap.org/way/866087250", "low"),
]
STADIUM_FACTS = {
    "osm_relation": 1640985, "name": "Ben Hill Griffin Stadium (Steve Spurrier-Florida Field)",
    "capacity": 88548, "field_elevation_m": -10.0,
    "rows_below_grade": "approximately 30 rows of seating are below the surrounding grade (Wikipedia)",
    "osm_part_heights_m": {
        "east/west main stands (w859154006, w859154007)": [0, 24],
        "east upper deck (w858341225)": [24, 44],
        "Sunshine Seats, north upper deck (w857391718)": [24, 46],
        "Touchdown Terrace (w858341226)": [16, 24],
        "Bull Gator Deck (w858341222)": [44, 52],
        "West Skybox Tower (w857391715, 7 levels)": [52, 66],
        "south ramp (w858341236)": [-10, 12],
    },
    "sources": [
        ["Wikipedia: Ben Hill Griffin Stadium", "https://en.wikipedia.org/wiki/Ben_Hill_Griffin_Stadium"],
        ["D.H. Griffin: press box tower renovation (7-story structure)",
         "https://www.dhgriffin.com/projects/demolition/university-florida-press-box-tower-renovation.aspx"],
        ["OpenStreetMap building:part ways around relation 1640985 (mapper heights, unverified)",
         "https://www.openstreetmap.org/relation/1640985"],
    ],
    "gameplay_simplification": "3 tiers: lower bowl 0..-10 m (field) to +8 m in 8 terraces (1.0 m rise, 2.2 m tread), "
                               "upper decks +24..+44 m in 6 terraces, skybox tower block to +66 m. "
                               "Real rows (~0.45 m rise) are too fine for Mario (single jump ~1.2 m).",
}
LAKE_FACTS = {
    "osm_relation": 1630473, "surface_elevation_m": 20.0,
    "open_water_area_osm_ha": None,  # filled in at runtime
    "uf_figure": "UF kiosk: lake ~82 acres of open water + marsh; conservation area ~129.5 acres",
    "sources": [
        ["Wikipedia: Lake Alice (Gainesville, Florida)", "https://en.wikipedia.org/wiki/Lake_Alice_(Gainesville,_Florida)"],
        ["UF Facilities Services Lake Alice kiosk", "https://www.facilitiesservices.ufl.edu/wp-content/uploads/2022/10/Lake-Alice-kiosk_v5.pdf"],
        ["UF bat houses", "https://bats.ufl.edu/"],
    ],
}

FLOOR_H = {
    "university": 4.0, "college": 4.0, "school": 4.0, "office": 3.8, "commercial": 3.8, "retail": 4.5,
    "hospital": 4.2, "civic": 4.0, "public": 4.0, "government": 4.0,
    "apartments": 3.1, "residential": 3.0, "house": 3.0, "detached": 3.0, "dormitory": 3.1, "hotel": 3.3,
    "industrial": 5.0, "warehouse": 5.5, "service": 4.0, "garage": 3.0, "garages": 3.0, "parking": 3.2,
    "greenhouse": 4.0, "farm_auxiliary": 4.5, "barn": 4.5, "shed": 3.0, "church": 5.0, "chapel": 5.0,
    "stadium": 6.0, "grandstand": 4.0, "pavilion": 4.0, "yes": 3.6,
}
HIP_TYPES = {"house", "detached", "residential", "church", "chapel", "barn", "farm_auxiliary", "shed"}
CANOPY_TYPES = {"roof", "pavilion", "carport", "shelter"}
SKIP_TYPES = {"construction", "no", "corridor", "ruins", "bridge"}


def default_levels(btype, area):
    if btype in ("university", "college", "school", "office", "commercial", "civic", "public", "government", "library"):
        return 1 if area < 150 else 2 if area < 1500 else 3 if area < 5000 else 4
    if btype == "hospital":
        return 5
    if btype == "apartments":
        return 2 if area < 800 else 3
    if btype == "dormitory":
        return 4
    if btype == "hotel":
        return 5
    if btype == "residential":
        return 1 if area < 150 else 2
    if btype == "parking":
        return 4
    if btype in ("house", "detached", "industrial", "warehouse", "service", "garage", "garages", "barn",
                 "farm_auxiliary", "greenhouse", "shed", "church", "chapel", "retail", "grandstand", "pavilion"):
        return 1
    # generic building=yes
    return 1 if area < 400 else 2 if area < 2000 else 3


def roof_shape(btype, tags, n):
    rs = tags.get("roof:shape")
    if rs in ("hipped", "gabled", "pyramidal"):
        return "hip"
    if btype in HIP_TYPES and n <= 8:
        return "hip"
    return "flat"


# ----------------------------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------------------------
def poly_area(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def centroid(pts):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        cr = x1 * y2 - x2 * y1
        a += cr
        cx += (x1 + x2) * cr
        cy += (y1 + y2) * cr
    if abs(a) < 1e-9:
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return (cx / (3 * a), cy / (3 * a))


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    if L == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def rdp(pts, eps):
    if len(pts) < 3:
        return list(pts)
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = _seg_dist(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def simplify_ring(pts, eps):
    if len(pts) <= 4:
        return list(pts)
    far = max(range(len(pts)), key=lambda i: math.dist(pts[0], pts[i]))
    a = rdp(pts[: far + 1], eps)
    b = rdp(pts[far:] + [pts[0]], eps)
    ring = a[:-1] + b[:-1]
    # drop near-duplicate points
    out = []
    for p in ring:
        if not out or math.dist(out[-1], p) > 0.3:
            out.append(p)
    if len(out) > 3 and math.dist(out[0], out[-1]) <= 0.3:
        out.pop()
    return out


def convex_hull(pts):
    P = sorted(set(map(tuple, pts)))
    if len(P) <= 2:
        return P

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def min_area_rect(pts):
    hull = convex_hull(pts)
    if len(hull) < 3:
        return list(pts)
    best = None
    for (x1, y1), (x2, y2) in zip(hull, hull[1:] + hull[:1]):
        ang = math.atan2(y2 - y1, x2 - x1)
        c, s = math.cos(-ang), math.sin(-ang)
        rx = [p[0] * c - p[1] * s for p in hull]
        ry = [p[0] * s + p[1] * c for p in hull]
        a = (max(rx) - min(rx)) * (max(ry) - min(ry))
        if best is None or a < best[0]:
            best = (a, ang, min(rx), max(rx), min(ry), max(ry))
    _, ang, x0, x1, y0, y1 = best
    c, s = math.cos(ang), math.sin(ang)
    return [(x * c - y * s, x * s + y * c) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]


def decimate(pts, eps, max_n):
    r = simplify_ring(pts, eps)
    while len(r) > max_n:
        eps *= 1.4
        r = simplify_ring(pts, eps)
    if len(r) < 3 or poly_area(r) < 0.6 * poly_area(pts):
        return min_area_rect(pts)
    return r


def clip_poly(pts, xmin, ymin, xmax, ymax):
    def clip(poly, inside, inter):
        out = []
        for i in range(len(poly)):
            cur, prev = poly[i], poly[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
        return out

    def ix(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def iy(y):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)
    poly = list(pts)
    for inside, inter in ((lambda p: p[0] >= xmin, ix(xmin)), (lambda p: p[0] <= xmax, ix(xmax)),
                          (lambda p: p[1] >= ymin, iy(ymin)), (lambda p: p[1] <= ymax, iy(ymax))):
        if not poly:
            break
        poly = clip(poly, inside, inter)
    return poly


def clip_segment(p, q, xmin, ymin, xmax, ymax):
    """Liang-Barsky; returns clipped (p, q) or None."""
    x0, y0 = p
    dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if pp == 0:
            if qq < 0:
                return None
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    if t0 > t1:
        return None
    return (x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


# ----------------------------------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------------------------------
def load():
    campus = json.load(open(os.path.join(DATA, "campus.json")))
    lat0, lon0 = campus["origin_latlon"]
    nodes, ways, rels = {}, {}, {}
    for path in sorted(glob.glob(os.path.join(DATA, "tiles", "*.osm"))):
        for el in ET.parse(path).getroot():
            if el.tag == "node":
                nodes[el.get("id")] = (float(el.get("lat")), float(el.get("lon")))
            elif el.tag == "way":
                ways[el.get("id")] = ([n.get("ref") for n in el.findall("nd")],
                                      {t.get("k"): t.get("v") for t in el.findall("tag")})
            elif el.tag == "relation":
                rels[el.get("id")] = ([(m.get("type"), m.get("ref"), m.get("role")) for m in el.findall("member")],
                                      {t.get("k"): t.get("v") for t in el.findall("tag")})
    kx = M_PER_DEG_LAT * math.cos(math.radians(lat0))

    def loc(ref):
        lat, lon = nodes[ref]
        return (round((lon - lon0) * kx, 2), round((lat - lat0) * M_PER_DEG_LAT, 2))

    def rings(refs_list):
        segs = [list(r) for r in refs_list if len(r) >= 2]
        out = []
        while segs:
            ring = segs.pop(0)
            changed = True
            while ring[0] != ring[-1] and changed:
                changed = False
                for i, s in enumerate(segs):
                    if s[0] == ring[-1]:
                        ring = ring + s[1:]
                    elif s[-1] == ring[-1]:
                        ring = ring + s[::-1][1:]
                    elif s[-1] == ring[0]:
                        ring = s[:-1] + ring
                    elif s[0] == ring[0]:
                        ring = s[::-1][:-1] + ring
                    else:
                        continue
                    segs.pop(i)
                    changed = True
                    break
            if ring[0] == ring[-1] and len(ring) >= 4 and all(r in nodes for r in ring):
                out.append([loc(r) for r in ring[:-1]])
        return out

    # Multipolygon relations that campus.json skips (water, woods, grass, parking ...).
    rel_areas = []
    for rid, (members, tags) in rels.items():
        if tags.get("type") != "multipolygon" or "building" in tags:
            continue
        outer = [ways[ref][0] for typ, ref, role in members if typ == "way" and role in ("outer", "") and ref in ways]
        inner = [ways[ref][0] for typ, ref, role in members if typ == "way" and role == "inner" and ref in ways]
        o = rings(outer)
        if o:
            rel_areas.append({"id": f"rel{rid}", "tags": tags, "rings": o, "holes": rings(inner)})

    # Stadium: campus.json keeps the relation tags only; take the name from the outer way and keep the bowl rings.
    stadium = {}
    if "1640985" in rels:
        members, tags = rels["1640985"]
        for typ, ref, role in members:
            if ref in ways:
                pts = [loc(r) for r in ways[ref][0][:-1] if r in nodes]
                if role == "outer":
                    stadium["outer"] = pts
                    stadium["tags"] = dict(ways[ref][1])
                else:
                    stadium.setdefault("inner", []).append(pts)

    areas = [{"id": a["id"], "tags": a["tags"], "rings": [a["pts"]], "holes": []} for a in campus["areas"]]
    areas += rel_areas
    for b in campus["buildings"]:
        if b["id"].startswith("r1640985/") and stadium:
            b["tags"] = {**stadium["tags"], **b["tags"]}
            b["holes"] = stadium.get("inner", [])
    return campus, areas, stadium


# ----------------------------------------------------------------------------------------------
# Building model
# ----------------------------------------------------------------------------------------------
LANDMARK_H = {lid: (h, basis, conf) for lid, _n, h, _f, basis, _s, _u, conf in LANDMARK_HEIGHTS}


def building_model(b):
    """Returns dict with height, source, roof, class, simplified pts."""
    tags = b["tags"]
    btype = tags.get("building") or ("part" if b.get("part") else "yes")
    area = b.get("area_m2") or poly_area(b["pts"])
    n_raw = len(b["pts"])
    m = {"id": b["id"], "type": btype, "area": area, "n_raw": n_raw, "name": tags.get("name"),
         "c": centroid(b["pts"]), "part": bool(b.get("part"))}
    min_h = 0.0
    try:
        min_h = float(str(tags.get("min_height", "0")).replace("m", ""))
    except ValueError:
        pass
    m["min_h"] = min_h
    if b["id"] in LANDMARK_H:
        m["h"], m["src"] = LANDMARK_H[b["id"]][0], "landmark"
    elif b.get("height_src") == "height" and b.get("height") is not None:
        m["h"], m["src"] = b["height"], "osm_height"
    elif tags.get("building:levels"):
        try:
            lv = float(tags["building:levels"])
            m["h"], m["src"] = lv * FLOOR_H.get(btype, 3.6) + (0 if btype in HIP_TYPES else 1.0), "osm_levels"
        except ValueError:
            m["h"] = None
    if m.get("h") is None:
        if btype in CANOPY_TYPES:
            m["h"], m["src"] = 4.0, "default"
        elif btype == "stadium":
            m["h"], m["src"] = 20.0, "default"
        elif btype == "grandstand":
            m["h"], m["src"] = 8.0, "default"
        elif btype in ("church", "chapel"):
            m["h"], m["src"] = 9.0, "default"
        elif area < 30:
            m["h"], m["src"] = 3.0, "default"
        else:
            lv = default_levels(btype, area)
            m["h"], m["src"] = lv * FLOOR_H.get(btype, 3.6) + (0 if btype in HIP_TYPES else 1.0), "default"
    # classification for simplification
    if btype in SKIP_TYPES or area < 15:
        cls = "skip"
    elif btype in CANOPY_TYPES:
        cls = "canopy"
    elif area < 60:
        cls = "tiny"
    elif area < 300:
        cls = "small"
    elif area < 3000:
        cls = "normal"
    else:
        cls = "large"
    m["cls"] = cls
    if cls == "skip":
        m["pts"] = []
    elif cls == "tiny":
        m["pts"] = min_area_rect(b["pts"])
    elif cls in ("small", "canopy"):
        m["pts"] = decimate(b["pts"], 1.0, 8)
    elif cls == "normal":
        m["pts"] = decimate(b["pts"], 0.75, 16)
    else:
        m["pts"] = decimate(b["pts"], 0.75, 24)
    n = len(m["pts"])
    m["n"] = n
    m["roof"] = roof_shape(btype, tags, n)
    return m


def tri_counts(n, roof, canopy=False):
    """(walls, roof) triangles of a simple prism with n footprint verts."""
    if n < 3:
        return 0, 0
    walls = 0 if canopy else 2 * n
    r = (3 * n - 6) if roof == "hip" else (n - 2)
    return walls, r


# ----------------------------------------------------------------------------------------------
# Collision cell accounting (vanilla add_surface semantics: bbox +-50 units margin)
# ----------------------------------------------------------------------------------------------
def _cell_lo(u):
    c = int((u + 0x8000) // CELL_UNITS)
    if (u + 0x8000) % CELL_UNITS < 50:
        c -= 1
    return max(0, min(NUM_CELLS - 1, c))


def _cell_hi(u):
    c = int((u + 0x8000) // CELL_UNITS)
    if (u + 0x8000) % CELL_UNITS > CELL_UNITS - 50:
        c += 1
    return max(0, min(NUM_CELLS - 1, c))


class CellLedger:
    def __init__(self, center):
        self.cx, self.cy = center
        self.count = Counter()
        self.nodes = 0

    def add_tri(self, pts_m, n=1):
        us = [((x - self.cx) * UNITS_PER_M, -(y - self.cy) * UNITS_PER_M) for x, y in pts_m]
        x0, x1 = min(u[0] for u in us), max(u[0] for u in us)
        z0, z1 = min(u[1] for u in us), max(u[1] for u in us)
        for cz in range(_cell_lo(z0), _cell_hi(z1) + 1):
            for cx in range(_cell_lo(x0), _cell_hi(x1) + 1):
                self.count[(cx, cz)] += n
                self.nodes += n

    def add_prism(self, pts, walls=True, roof_tris=None):
        if walls:
            for a, b in zip(pts, pts[1:] + pts[:1]):
                self.add_tri([a, b], 2)
        k = len(pts)
        rt = roof_tris if roof_tris is not None else k - 2
        if rt > 0 and k >= 3:
            # fan triangles; scale count if the roof is a hip (more, smaller tris over the same cells)
            fan = [(pts[0], pts[i], pts[i + 1]) for i in range(1, k - 1)]
            per = rt / len(fan)
            for t in fan:
                self.add_tri(t, per)

    def add_budget(self, pts, tris):
        """Spread a hand-model budget over the footprint's cells."""
        if not pts or tris <= 0:
            return
        x0, y0, x1, y1 = bbox(pts)
        cells = set()
        for cz in range(_cell_lo(-(y1 - self.cy) * 100), _cell_hi(-(y0 - self.cy) * 100) + 1):
            for cx in range(_cell_lo((x0 - self.cx) * 100), _cell_hi((x1 - self.cx) * 100) + 1):
                cells.add((cx, cz))
        per = tris * 1.6 / max(1, len(cells))     # ~1.6 cells per hand-modeled tri on average
        for c in cells:
            self.count[c] += per
        self.nodes += tris * 1.6

    def stats(self):
        vals = sorted(self.count.values())
        if not vals:
            return {"nodes": 0}
        return {"nodes_est": int(self.nodes), "occupied_cells": len(vals),
                "max_surfaces_per_cell": int(vals[-1]), "p95_surfaces_per_cell": int(vals[int(0.95 * (len(vals) - 1))]),
                "mean_surfaces_per_cell": round(sum(vals) / len(vals), 1)}


# ----------------------------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------------------------
SS = 2  # supersampling
FONT_DIR = "/System/Library/Fonts/Supplemental/"


def font(size, bold=False, italic=False):
    name = "Arial Bold.ttf" if bold else ("Arial Italic.ttf" if italic else "Arial.ttf")
    try:
        return ImageFont.truetype(FONT_DIR + name, int(size * SS))
    except OSError:
        return ImageFont.load_default(int(size * SS))


BG = (246, 244, 239)
HEIGHT_BINS = [6, 10, 15, 20, 30, 45]   # m; 7 classes
HEIGHT_RAMP = [(253, 229, 205), (250, 205, 160), (244, 172, 112), (235, 136, 70), (214, 101, 36), (172, 72, 18), (112, 44, 10)]
WATER = (166, 205, 236)
WATER_EDGE = (110, 160, 210)
ROAD_STYLE = {  # highway: (width m, min px@final, fill, casing)
    "motorway": (14, 3.0, (255, 255, 255), (170, 165, 155)), "trunk": (14, 3.0, (255, 255, 255), (170, 165, 155)),
    "primary": (13, 2.6, (255, 255, 255), (170, 165, 155)), "secondary": (11, 2.2, (255, 255, 255), (175, 170, 160)),
    "tertiary": (9, 2.0, (255, 255, 255), (180, 175, 165)), "unclassified": (7, 1.6, (255, 255, 255), (185, 180, 170)),
    "residential": (7, 1.4, (255, 255, 255), (190, 185, 175)), "living_street": (6, 1.2, (255, 255, 255), (190, 185, 175)),
    "service": (4.5, 1.0, (255, 255, 255), (195, 190, 182)),
    "primary_link": (7, 1.4, (255, 255, 255), (175, 170, 160)), "secondary_link": (7, 1.4, (255, 255, 255), (175, 170, 160)),
    "tertiary_link": (6, 1.2, (255, 255, 255), (180, 175, 165)), "trunk_link": (7, 1.4, (255, 255, 255), (175, 170, 160)),
}
PATH_STYLE = {"footway": (2.0, 0.7, (196, 160, 120)), "path": (2.0, 0.7, (170, 140, 100)),
              "cycleway": (2.5, 0.7, (120, 150, 200)), "pedestrian": (4.0, 0.9, (196, 160, 120)),
              "steps": (2.0, 1.0, (120, 90, 70)), "bridleway": (2.0, 0.7, (170, 140, 100)), "track": (3.0, 0.8, (170, 140, 100))}


def area_style(tags):
    """(z, fill, outline) or None."""
    nat, lu, le, am = tags.get("natural"), tags.get("landuse"), tags.get("leisure"), tags.get("amenity")
    if nat == "water" or "water" in tags and nat in (None, "water") and tags.get("water") not in (None, "no") \
            or tags.get("waterway") == "riverbank" or le == "swimming_pool":
        return (7, WATER, WATER_EDGE)
    if nat == "wetland":
        return (5, (196, 222, 205), (150, 190, 165))
    if nat in ("wood",) or lu == "forest":
        return (4, (164, 202, 156), (135, 180, 128))
    if nat == "scrub":
        return (4, (190, 214, 170), None)
    if nat in ("sand", "beach", "bare_rock"):
        return (6, (236, 226, 190), None)
    if le in ("pitch", "track", "stadium"):
        return (3, (186, 222, 172), (140, 185, 130))
    if lu in ("grass", "meadow", "recreation_ground", "village_green", "cemetery") or nat in ("grass", "heath") \
            or le in ("park", "garden", "common", "golf_course", "playground", "dog_park"):
        return (2, (206, 230, 190), None)
    if am == "parking" or tags.get("parking"):
        return (1, (226, 223, 216), (205, 201, 192))
    if tags.get("highway") in ("pedestrian", "footway") or tags.get("man_made") in ("courtyard", "bridge") \
            or tags.get("place") == "square":
        return (8, (236, 229, 216), (214, 205, 190))
    if lu in ("residential", "commercial", "retail", "industrial", "religious", "construction", "brownfield",
              "farmyard", "greenhouse_horticulture", "farmland", "education"):
        return (0, (239, 236, 229), None)
    return None


def height_color(h):
    for i, edge in enumerate(HEIGHT_BINS):
        if h < edge:
            return HEIGHT_RAMP[i]
    return HEIGHT_RAMP[-1]


def darker(c, k=0.72):
    return tuple(int(v * k) for v in c)


class Canvas:
    def __init__(self, xmin, ymin, xmax, ymax, width_px, extra_bottom=0, extra_right=0):
        self.xmin, self.ymin, self.xmax, self.ymax = xmin, ymin, xmax, ymax
        self.s = width_px / (xmax - xmin) * SS            # px per meter (supersampled)
        self.wm = int(round(width_px * SS))
        self.hm = int(round((ymax - ymin) * self.s))
        self.W = self.wm + int(extra_right * SS)
        self.H = self.hm + int(extra_bottom * SS)
        self.img = Image.new("RGB", (self.W, self.H), BG)
        self.d = ImageDraw.Draw(self.img)
        self.labels = []

    def P(self, p):
        return ((p[0] - self.xmin) * self.s, (self.ymax - p[1]) * self.s)

    def poly(self, pts, fill=None, outline=None, width=1):
        if len(pts) < 3:
            return
        self.d.polygon([self.P(p) for p in pts], fill=fill, outline=outline, width=int(width) if outline else 0)

    def poly_holes(self, rings, holes, fill, outline=None, width=1):
        if not holes:
            for r in rings:
                self.poly(r, fill, outline, width)
            return
        allp = [self.P(p) for r in rings for p in r]
        x0 = max(0, int(min(p[0] for p in allp)) - 2)
        y0 = max(0, int(min(p[1] for p in allp)) - 2)
        x1 = min(self.wm, int(max(p[0] for p in allp)) + 2)
        y1 = min(self.hm, int(max(p[1] for p in allp)) + 2)
        if x1 <= x0 or y1 <= y0:
            return
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        md = ImageDraw.Draw(mask)
        for r in rings:
            md.polygon([(p[0] - x0, p[1] - y0) for p in map(self.P, r)], fill=255)
        for h in holes:
            md.polygon([(p[0] - x0, p[1] - y0) for p in map(self.P, h)], fill=0)
        self.img.paste(fill, (x0, y0, x1, y1), mask)
        if outline:
            for r in rings + holes:
                self.d.line([self.P(p) for p in r + r[:1]], fill=outline, width=int(width))

    def line(self, pts, fill, width, joint="curve"):
        if len(pts) >= 2:
            self.d.line([self.P(p) for p in pts], fill=fill, width=max(1, int(round(width))), joint=joint)

    def dashed(self, pts, fill, width, dash=14, gap=9):
        dash *= SS
        gap *= SS
        P = [self.P(p) for p in pts]
        for a, b in zip(P, P[1:]):
            L = math.dist(a, b)
            t = 0.0
            while t < L:
                t2 = min(L, t + dash)
                self.d.line([(a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L),
                             (a[0] + (b[0] - a[0]) * t2 / L, a[1] + (b[1] - a[1]) * t2 / L)],
                            fill=fill, width=int(width * SS))
                t = t2 + gap

    def dot(self, p, r_px, fill):
        x, y = self.P(p)
        r = r_px
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def label(self, p, text, size=13, bold=False, italic=False, color=(30, 30, 30), force=False, offsets=None,
              halo=(255, 255, 255)):
        f = font(size, bold, italic)
        x, y = self.P(p)
        l, t, r, b = self.d.textbbox((0, 0), text, font=f, stroke_width=2 * SS)
        w, h = r - l, b - t
        cands = offsets or [(0, 0), (0, -h * 1.1), (0, h * 1.1), (w * 0.6, 0), (-w * 0.6, 0), (0, -h * 2.1), (0, h * 2.1)]
        for ox, oy in cands:
            box = (x + ox - w / 2, y + oy - h / 2, x + ox + w / 2, y + oy + h / 2)
            if box[0] < 0 or box[2] > self.wm or box[1] < 0 or box[3] > self.hm:
                continue
            if any(not (box[2] < o[0] or box[0] > o[2] or box[3] < o[1] or box[1] > o[3]) for o in self.labels):
                continue
            self.labels.append(box)
            self.d.text((box[0] - l, box[1] - t), text, font=f, fill=color, stroke_width=2 * SS, stroke_fill=halo)
            return True
        if force:
            box = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            self.labels.append(box)
            self.d.text((box[0] - l, box[1] - t), text, font=f, fill=color, stroke_width=2 * SS, stroke_fill=halo)
            return True
        return False

    def text(self, xy_px, text, size=13, bold=False, color=(30, 30, 30), anchor="la", italic=False):
        self.d.text((xy_px[0] * SS, xy_px[1] * SS), text, font=font(size, bold, italic), fill=color, anchor=anchor)

    def save(self, path):
        out = self.img.resize((self.W // SS, self.H // SS), Image.LANCZOS)
        out.save(path, optimize=True)
        return out.size


def draw_base(cv, campus, areas, models, trees, tree_r_m=3.5, show_parts=True, hatch=True):
    view = (cv.xmin - 50, cv.ymin - 50, cv.xmax + 50, cv.ymax + 50)

    def visible(pts):
        x0, y0, x1, y1 = bbox(pts)
        return not (x1 < view[0] or x0 > view[2] or y1 < view[1] or y0 > view[3])

    styled = []
    for a in areas:
        st = area_style(a["tags"])
        if st and any(visible(r) for r in a["rings"]):
            styled.append((st[0], a, st))
    styled.sort(key=lambda t: t[0])
    for _z, a, (_zz, fill, outline) in styled:
        cv.poly_holes(a["rings"], a["holes"], fill, outline, max(1, SS))
    # streams
    for w in campus["ways"]:
        if w["tags"].get("waterway") in ("stream", "ditch", "drain", "canal") and visible(w["pts"]):
            cv.line(w["pts"], WATER_EDGE, max(1.0 * SS, 2.0 * cv.s))
    # roads: casing then fill
    roads = [w for w in campus["ways"] if w["tags"].get("highway") in ROAD_STYLE and visible(w["pts"])
             and w["tags"].get("tunnel") not in ("yes",)]
    for w in roads:
        wm, mn, fill, casing = ROAD_STYLE[w["tags"]["highway"]]
        cv.line(w["pts"], casing, max(mn * SS, wm * cv.s) + 2 * SS)
    for w in roads:
        wm, mn, fill, casing = ROAD_STYLE[w["tags"]["highway"]]
        cv.line(w["pts"], fill, max(mn * SS, wm * cv.s))
    for w in campus["ways"]:
        hw = w["tags"].get("highway")
        if hw in PATH_STYLE and visible(w["pts"]) and w["tags"].get("indoor") != "yes" and w["tags"].get("level", "0") in ("0", ""):
            wm, mn, col = PATH_STYLE[hw]
            cv.line(w["pts"], col, max(mn * SS, wm * cv.s * 0.6))
        elif w["tags"].get("barrier") in ("wall", "retaining_wall", "fence") and visible(w["pts"]):
            cv.line(w["pts"], (150, 140, 130), max(0.6 * SS, 0.4 * cv.s))
    # buildings (non-parts), then parts on top
    hatch_mask = Image.new("L", (cv.W, cv.H), 0) if hatch else None
    hm = ImageDraw.Draw(hatch_mask) if hatch else None
    order = [m for m in models if not m["part"]] + ([m for m in models if m["part"]] if show_parts else [])
    for m in order:
        b = m["raw"]
        if not visible(b["pts"]) or m["area"] < 1:
            continue
        col = height_color(m["h"])
        if b.get("holes"):
            cv.poly_holes([b["pts"]], b["holes"], col)
        else:
            cv.poly(b["pts"], fill=col)
        if hatch and m["src"] == "default" and not m["part"]:
            hm.polygon([cv.P(p) for p in b["pts"]], fill=255)
    if hatch:
        pat = Image.new("L", (cv.W, cv.H), 0)
        pd = ImageDraw.Draw(pat)
        step = 6 * SS
        for k in range(-cv.H, cv.W, step):
            pd.line([(k, cv.H), (k + cv.H, 0)], fill=150, width=SS)
        cv.img.paste((255, 255, 255), (0, 0), ImageChops.multiply(hatch_mask, pat))
    for m in order:
        b = m["raw"]
        if not visible(b["pts"]) or m["area"] < 1:
            continue
        col = darker(height_color(m["h"]), 0.62)
        cv.line(b["pts"] + b["pts"][:1], col, max(1, 0.55 * SS), joint=None)
    # trees
    r = max(1.1 * SS, tree_r_m * cv.s)
    for t in trees:
        if view[0] <= t[0] <= view[2] and view[1] <= t[1] <= view[3]:
            cv.dot(t, r, (62, 122, 62))


def draw_scalebar(cv, x_px, y_px, meters, color=(40, 40, 40)):
    L = meters * cv.s / SS
    d = cv.d
    X, Y = x_px * SS, y_px * SS
    d.rectangle([X, Y, X + L * SS, Y + 6 * SS], fill=(255, 255, 255), outline=color, width=SS)
    d.rectangle([X, Y, X + L * SS / 2, Y + 6 * SS], fill=color)
    cv.text((x_px, y_px + 10), "0", 12)
    cv.text((x_px + L / 2, y_px + 10), f"{meters // 2} m", 12, anchor="ma")
    cv.text((x_px + L, y_px + 10), f"{meters} m", 12, anchor="ma")


def draw_north(cv, x_px, y_px, size=26):
    X, Y, S = x_px * SS, y_px * SS, size * SS
    cv.d.polygon([(X, Y - S), (X - S * 0.42, Y + S * 0.5), (X, Y + S * 0.2)], fill=(40, 40, 40))
    cv.d.polygon([(X, Y - S), (X + S * 0.42, Y + S * 0.5), (X, Y + S * 0.2)], fill=(150, 150, 150))
    cv.text((x_px, y_px - size - 18), "N", 14, bold=True, anchor="ma")


def draw_legend(cv, x0, y0, compact=False):
    """Legend in final px coordinates."""
    d = cv.d
    cv.text((x0, y0), "Building height (m)", 13, bold=True)
    labels = ["<6", "6-10", "10-15", "15-20", "20-30", "30-45", "45+"]
    for i, (c, lab) in enumerate(zip(HEIGHT_RAMP, labels)):
        x = x0 + i * 52
        d.rectangle([x * SS, (y0 + 20) * SS, (x + 46) * SS, (y0 + 36) * SS], fill=c, outline=darker(c, 0.62), width=SS)
        cv.text((x + 23, y0 + 40), lab, 11, anchor="ma")
    # hatch sample
    x = x0 + 7 * 52 + 14
    d.rectangle([x * SS, (y0 + 20) * SS, (x + 46) * SS, (y0 + 36) * SS], fill=HEIGHT_RAMP[2], outline=darker(HEIGHT_RAMP[2], 0.62), width=SS)
    for k in range(0, 60, 6):
        d.line([((x + k - 16) * SS, (y0 + 36) * SS), ((x + k) * SS, (y0 + 20) * SS)], fill=(255, 255, 255), width=SS)
    d.rectangle([(x - 1) * SS, (y0 + 19) * SS, (x + 47) * SS, (y0 + 37) * SS], outline=BG, width=SS * 2)
    cv.text((x + 54, y0 + 22), "hatched = height estimated", 11)
    cv.text((x + 54, y0 + 36), "by type rule (no OSM data)", 11)
    y = y0 + 64
    items = [("Water", WATER, WATER_EDGE), ("Grass / park", (206, 230, 190), None), ("Pitch / track", (186, 222, 172), (140, 185, 130)),
             ("Woods", (164, 202, 156), None), ("Wetland", (196, 222, 205), None), ("Parking", (226, 223, 216), None),
             ("Plaza / courtyard", (236, 229, 216), None)]
    for i, (lab, c, o) in enumerate(items):
        x = x0 + (i % 4) * 150
        yy = y + (i // 4) * 24
        d.rectangle([x * SS, yy * SS, (x + 22) * SS, (yy + 14) * SS], fill=c, outline=o or darker(c, 0.85), width=SS)
        cv.text((x + 28, yy), lab, 12)
    y += 54
    d.line([(x0 * SS, (y + 7) * SS), ((x0 + 26) * SS, (y + 7) * SS)], fill=(175, 170, 160), width=7 * SS)
    d.line([(x0 * SS, (y + 7) * SS), ((x0 + 26) * SS, (y + 7) * SS)], fill=(255, 255, 255), width=5 * SS)
    cv.text((x0 + 32, y), "Road", 12)
    d.line([((x0 + 150) * SS, (y + 7) * SS), ((x0 + 176) * SS, (y + 7) * SS)], fill=PATH_STYLE["footway"][2], width=2 * SS)
    cv.text((x0 + 182, y), "Footway / path", 12)
    d.ellipse([(x0 + 300 + 6) * SS, (y + 2) * SS, (x0 + 300 + 16) * SS, (y + 12) * SS], fill=(62, 122, 62))
    cv.text((x0 + 322, y), "Mapped tree", 12)


# ----------------------------------------------------------------------------------------------
# Stage statistics + budgets
# ----------------------------------------------------------------------------------------------
ROAD_CLASSES = set(ROAD_STYLE)
PATH_CLASSES = {"footway", "path", "cycleway", "pedestrian", "bridleway", "track"}


def pm(st):
    return st.get("play_margin", PLAY_MARGIN_M)


def stage_bounds(st, margin=0):
    cx, cy = st["center"]
    h = st["size"] / 2 - margin
    return (cx - h, cy - h, cx + h, cy + h)


def inside(p, bnd):
    return bnd[0] <= p[0] <= bnd[2] and bnd[1] <= p[1] <= bnd[3]


def find_feature(fid, campus, areas, models_by_id):
    if fid in models_by_id:
        m = models_by_id[fid]
        return m["raw"]["pts"], m["c"]
    for a in areas:
        if a["id"] == fid:
            return a["rings"][0], centroid(a["rings"][0])
    for p in campus["points"]:
        if p["id"] == fid:
            return [], tuple(p["pt"])
    for m in models_by_id.values():
        if m["name"] == fid and not m["part"]:
            return m["raw"]["pts"], m["c"]
    return [], None


def compute_stage(st, campus, areas, models, models_by_id, trees, woods, waters, stadium):
    bnd = stage_bounds(st)
    play = stage_bounds(st, pm(st))
    cx, cy = st["center"]
    ledger = CellLedger(st["center"])
    landmark_ids = set()
    lm_out = []
    for fid, name, treat, ctris, vtris, notes in st["landmarks"]:
        pts, c = find_feature(fid, campus, areas, models_by_id)
        if c is None:
            print("WARN landmark not found", fid)
            continue
        real_id = fid
        if fid not in models_by_id and not fid.startswith(("w", "n", "rel", "r")):
            for m in models_by_id.values():
                if m["name"] == fid and not m["part"]:
                    real_id = m["id"]
        landmark_ids.add(real_id)
        m = models_by_id.get(real_id)
        h = m["h"] if m else None
        ledger.add_budget(pts if pts else [(c[0] - 3, c[1] - 3), (c[0] + 3, c[1] + 3)], ctris)
        entry = {"name": name, "osm_id": real_id, "treatment": treat,
                 "center_m": [round(c[0], 1), round(c[1], 1)],
                 "game_xz": [round((c[0] - cx) * UNITS_PER_M), round(-(c[1] - cy) * UNITS_PER_M)],
                 "in_play_zone": inside(c, play),
                 "edge_clearance_m": round(min(c[0] - bnd[0], bnd[2] - c[0], c[1] - bnd[1], bnd[3] - c[1]), 1),
                 "collision_tris": ctris, "visual_tris": vtris, "notes": notes}
        if pts:
            x0, y0, x1, y1 = bbox(pts)
            entry["footprint_bbox_m"] = [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]
            entry["footprint_area_m2"] = round(poly_area(pts), 1)
            entry["fully_inside_window"] = inside((x0, y0), bnd) and inside((x1, y1), bnd)
            entry["play_zone_clearance_m"] = round(min(x0 - play[0], play[2] - x1, y0 - play[1], play[3] - y1), 1)
        if h is not None:
            entry["height_m"] = round(h, 1)
            entry["height_source"] = m["src"]
        lm_out.append(entry)

    # ---- buildings ----
    cnt = Counter()
    raw_tris = 0
    plan = Counter()
    vis = Counter()
    footprint = 0.0
    src = Counter()
    by_cls = Counter()
    n_raw_total = n_simpl_total = 0
    shared_edges = 0
    edge_owner = {}
    for m in models:
        if m["part"] or not inside(m["c"], bnd) or m["area"] < 1:
            continue
        cnt["buildings"] += 1
        footprint += m["area"]
        src[m["src"]] += 1
        by_cls[m["cls"]] += 1
        w_raw, r_raw = tri_counts(m["n_raw"], "flat")
        raw_tris += w_raw + r_raw
        n_raw_total += m["n_raw"]
        pts_raw = m["raw"]["pts"]
        for a, b in zip(pts_raw, pts_raw[1:] + pts_raw[:1]):
            k = (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
            rk = (k[2], k[3], k[0], k[1])
            if rk in edge_owner and edge_owner[rk] != m["id"]:
                shared_edges += 1
            edge_owner[k] = m["id"]
        if m["id"] in landmark_ids:
            continue
        if m["cls"] == "skip":
            continue
        n_simpl_total += m["n"]
        w, r = tri_counts(m["n"], m["roof"], canopy=m["cls"] == "canopy")
        if inside(m["c"], play):
            plan["generic_buildings"] += w + r
            vis["generic_buildings"] += int((w + r) * 1.3) + (8 if m["cls"] != "canopy" else 0)
            ledger.add_prism(m["pts"], walls=m["cls"] != "canopy", roof_tris=r)
        else:
            # backdrop shell: <= 8 verts, flat, visual only
            nb = min(m["n"], 8)
            vis["backdrop_shells"] += 2 * nb + nb - 2
            cnt["backdrop_buildings"] += 1
    cnt["landmarks"] = len(lm_out)
    plan["landmarks_hand_modeled"] = sum(e["collision_tris"] for e in lm_out)
    vis["landmarks_hand_modeled"] = sum(e["visual_tris"] for e in lm_out)

    # ---- ways ----
    segs = Counter()
    seg_len = Counter()
    for w in campus["ways"]:
        t = w["tags"]
        hw = t.get("highway")
        kind = ("road" if hw in ROAD_CLASSES else "path" if hw in PATH_CLASSES else "steps" if hw == "steps"
                else "barrier" if t.get("barrier") in ("wall", "retaining_wall", "fence", "hedge") else
                "stream" if t.get("waterway") else None)
        if not kind or t.get("indoor") == "yes" or hw == "corridor":
            continue
        pts = w["pts"]
        simp = rdp(pts, 0.5) if len(pts) > 2 else pts
        for a, b in zip(pts, pts[1:]):
            c = clip_segment(a, b, *bnd)
            if c:
                segs[kind] += 1
                seg_len[kind] += math.dist(*c)
        for a, b in zip(simp, simp[1:]):
            c = clip_segment(a, b, *bnd)
            if not c:
                continue
            segs[kind + "_simplified"] += 1
            inplay = clip_segment(a, b, *play)
            if kind == "barrier" and inplay:
                plan["barriers_walls_fences"] += 4
                ledger.add_tri(list(inplay), 4)
            elif kind == "steps" and inplay:
                plan["steps_as_ramps"] += 4
                ledger.add_tri(list(inplay), 4)
            if kind in ("road", "path", "steps"):
                vis["path_ribbons"] += 2
    # ---- trees, woods, water ----
    n_trees = sum(1 for p in trees if inside(p, bnd))
    wood_area = sum(poly_area(clip_poly(r, *bnd)) for r in woods if len(clip_poly(r, *bnd)) >= 3)
    water_area = 0.0
    water_polys = []
    for a in waters:
        for r in a["rings"]:
            cp = clip_poly(r, *bnd)
            if len(cp) >= 3:
                ar = poly_area(cp) - sum(poly_area(clip_poly(h, *bnd)) for h in a["holes"] if len(clip_poly(h, *bnd)) >= 3)
                water_area += ar
                water_polys.append((a, r, ar))
    scatter = int(wood_area / 80)
    vis["trees_osm_lowpoly"] = n_trees * 12
    vis["trees_wood_scatter_billboards"] = scatter * 4
    # ponds / lakes (non-landmark): basin bed + bank ring from a decimated outline
    for a, r, ar in water_polys:
        if a["id"] in landmark_ids or ar < 30 or a["tags"].get("leisure") == "swimming_pool":
            continue
        n = len(decimate(r, 1.0, 24))
        plan["pond_basins"] += (n - 2) + 2 * n
        vis["pond_basins"] += (n - 2) + 2 * n + (n - 2)
    # ---- ground + boundary ----
    side = st["size"]
    n_patch = math.ceil(side / GROUND_PATCH_M)
    plan["ground_grid"] = n_patch * n_patch * 2
    x0, y0 = cx - n_patch * GROUND_PATCH_M / 2, cy - n_patch * GROUND_PATCH_M / 2
    for i in range(n_patch):
        for j in range(n_patch):
            a = (x0 + i * GROUND_PATCH_M + 5.12, y0 + j * GROUND_PATCH_M + 5.12)
            b = (a[0] + GROUND_PATCH_M, a[1] + GROUND_PATCH_M)
            ledger.add_tri([a, b], 2)
    psize = side - 2 * pm(st)
    nb = math.ceil(psize / GROUND_PATCH_M)
    plan["boundary_walls"] = 4 * nb * 2
    vis["ground_visual_grid_10m"] = math.ceil(side / 10.24) ** 2 * 2
    plan["props_allowance"] = 300
    static_total = sum(plan.values())
    budget = {"items": dict(plan), "static_total": static_total, "reserve_objects_players": RESERVE_OBJECTS,
              "total": static_total + RESERVE_OBJECTS, "cap": SURFACE_POOL,
              "headroom": SURFACE_POOL - static_total - RESERVE_OBJECTS,
              "static_cap": SURFACE_POOL - RESERVE_OBJECTS}
    naive = raw_tris + (segs["road"] + segs["path"] + segs["steps"]) * 2 + n_trees * 6 + \
        math.ceil(side / 10.24) ** 2 * 2 + segs["barrier"] * 4
    stats = {
        "buildings": cnt["buildings"], "buildings_in_play_zone": cnt["buildings"] - cnt["backdrop_buildings"],
        "backdrop_buildings": cnt["backdrop_buildings"],
        "building_classes": dict(by_cls), "height_sources": dict(src),
        "footprint_area_m2": round(footprint), "footprint_area_share": round(footprint / side ** 2, 3),
        "footprint_vertices_raw": n_raw_total, "footprint_vertices_simplified_generic": n_simpl_total,
        "shared_wall_edges": shared_edges,
        "raw_prism_tris_flat_roofs": raw_tris,
        "segments": {k: v for k, v in segs.items()},
        "length_m": {k: round(v) for k, v in seg_len.items()},
        "trees_osm": n_trees, "wood_area_m2": round(wood_area), "wood_scatter_trees_est": scatter,
        "water_area_m2": round(water_area),
        "naive_collision_tris": naive,
    }
    vis_total = sum(vis.values())
    return {"stats": stats, "budget": budget, "visual": {"items": dict(vis), "total": vis_total},
            "cells": ledger.stats(), "landmarks": lm_out}


# ----------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------
KEY_LABELS = [  # (feature id or point, label, priority size)
    ("w150860043", "Century Tower", 13), ("w154223635", "Auditorium", 11), ("w150684197", "Turlington", 11),
    ("w150860048", "Marston", 11), ("w264182367", "Plaza of the Americas", 12), ("r12122775/196848215", "Library West", 11),
    ("w154223625", "Smathers", 11), ("w150926632", "The Hub", 11), ("w150926630", "Newell", 11),
    ("r1640985/45719890", "Ben Hill Griffin Stadium", 13), ("w45719889", "O'Connell Center", 11),
    ("w45719891", "Florida Gym", 11), ("w863211313", "Reitz Union", 12), ("w445808709", "Weil Hall", 11),
    ("w1094502850", "Malachowsky Hall", 11), ("rel1630473", "Lake Alice", 14), ("w424512419", "Bat Houses", 11),
    ("w668261582", "Stadium Club", 10), ("w425690658", "Baughman Center", 10),
    ("UF Health Shands Hospital and UF Health Shands Children's Hospital", "Shands Hospital", 11),
    ("Southwest Recreation Center", "SW Rec Center", 10), ("Florida Museum of Natural History", "Florida Museum", 10),
    ("Steinmetz Hall", "Steinmetz Hall", 10), ("Norman Hall", "Norman Hall", 10), ("w150928196", "Reitz Ravine", 10),
    ("n4741925737", "Turlington rock", 9),
]
ROAD_LABELS = ["West University Avenue", "Southwest 13th Street", "Museum Road", "Archer Road", "Hull Road",
               "Stadium Road", "Newell Drive", "Gale Lemerand Drive", "Southwest 2nd Avenue", "Southwest 16th Avenue"]


def place_road_labels(cv, campus, names, size=10):
    for nm in names:
        best = None
        for w in campus["ways"]:
            if w["tags"].get("name") != nm or w["tags"].get("highway") not in ROAD_CLASSES:
                continue
            for a, b in zip(w["pts"], w["pts"][1:]):
                L = math.dist(a, b)
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                if cv.xmin + 80 < mid[0] < cv.xmax - 80 and cv.ymin + 80 < mid[1] < cv.ymax - 80:
                    d = math.dist(mid, ((cv.xmin + cv.xmax) / 2, (cv.ymin + cv.ymax) / 2))
                    score = L - d * 0.02
                    if best is None or score > best[0]:
                        best = (score, mid)
        if best:
            short = nm.replace("Southwest", "SW").replace("Northwest", "NW").replace("West ", "W ").replace("Avenue", "Ave") \
                .replace("Street", "St").replace("Road", "Rd").replace("Drive", "Dr")
            cv.label(best[1], short, size, italic=True, color=(105, 100, 95))


def label_features(cv, campus, areas, models_by_id, items, scale=1.0, color=(25, 25, 25)):
    for fid, text, size in items:
        pts, c = find_feature(fid, campus, areas, models_by_id)
        if c is None:
            continue
        if cv.xmin <= c[0] <= cv.xmax and cv.ymin <= c[1] <= cv.ymax:
            cv.label(c, text, size * scale, bold=size >= 12, color=color, force=size >= 12)


def extract_bbox_m(campus):
    """The download bbox from data/uf/SOURCE.txt in local meters (ways run past it; crop to it)."""
    lat0, lon0 = campus["origin_latlon"]
    kx = M_PER_DEG_LAT * math.cos(math.radians(lat0))
    try:
        txt = open(os.path.join(DATA, "SOURCE.txt")).read()
        w, sth, e, n = map(float, txt.split("bbox ")[1].split(")")[0].split(","))
    except (OSError, IndexError, ValueError):
        w, sth, e, n = -82.372, 29.630, -82.336, 29.656
    return ((w - lon0) * kx, (sth - lat0) * M_PER_DEG_LAT, (e - lon0) * kx, (n - lat0) * M_PER_DEG_LAT)


def main():
    os.makedirs(ART, exist_ok=True)
    campus, areas, stadium = load()
    models = []
    for b in campus["buildings"]:
        m = building_model(b)
        m["raw"] = b
        models.append(m)
    models_by_id = {m["id"]: m for m in models}
    trees = [tuple(p["pt"]) for p in campus["points"] if p["tags"].get("natural") == "tree"]
    woods = [r for a in areas if a["tags"].get("natural") == "wood" or a["tags"].get("landuse") == "forest" for r in a["rings"]]
    waters = [a for a in areas if area_style(a["tags"]) and area_style(a["tags"])[1] == WATER]
    lake = next(a for a in areas if a["id"] == "rel1630473")
    lake_area = poly_area(lake["rings"][0]) - sum(poly_area(h) for h in lake["holes"])
    LAKE_FACTS["open_water_area_osm_ha"] = round(lake_area / 1e4, 2)

    # ------------------------------------------------------------------ overview map
    X0, Y0, X1, Y1 = extract_bbox_m(campus)
    cv = Canvas(X0, Y0, X1, Y1, 2400, extra_bottom=236)
    draw_base(cv, campus, areas, models, trees, tree_r_m=3.0)
    # nature reserve outline
    for a in areas:
        if a["tags"].get("leisure") == "nature_reserve":
            cv.dashed(a["rings"][0] + a["rings"][0][:1], (60, 120, 70), 1.4, 8, 6)
    label_features(cv, campus, areas, models_by_id, [(f, t, s) for f, t, s in KEY_LABELS if s >= 12])
    label_features(cv, campus, areas, models_by_id, [(f, t, s) for f, t, s in KEY_LABELS if s < 12])
    place_road_labels(cv, campus, ROAD_LABELS)
    top = cv.hm // SS
    cv.d.rectangle([0, cv.hm, cv.W, cv.H], fill=(255, 255, 255))
    cv.d.line([(0, cv.hm), (cv.W, cv.hm)], fill=(200, 196, 188), width=SS)
    cv.text((24, top + 16), "GatorCampus 64 - UF campus extract (top-down, true scale)", 18, bold=True)
    cv.text((24, top + 42), f"{X1 - X0:.0f} m x {Y1 - Y0:.0f} m around Century Tower (0,0); x = east, y = north. "
                            f"{len(campus['buildings'])} building polygons, {len(trees)} mapped trees.", 12, color=(80, 80, 80))
    draw_legend(cv, 24, top + 70)
    draw_scalebar(cv, 1700, top + 90, 500)
    draw_north(cv, 2330, top + 110)
    cv.text((2376, top + 214), "Map data (c) OpenStreetMap contributors, ODbL 1.0", 11, color=(90, 90, 90), anchor="ra")
    size_overview = cv.save(os.path.join(ART, "map_overview.png"))

    # ------------------------------------------------------------------ stage results
    results = {}
    for st in STAGES:
        results[st["key"]] = compute_stage(st, campus, areas, models, models_by_id, trees, woods, waters, stadium)

    # ------------------------------------------------------------------ stages map
    sx0, sx1, sy0, sy1 = -2140, 420, -1080, 600
    cv = Canvas(sx0, sy0, sx1, sy1, 2400, extra_bottom=240)
    draw_base(cv, campus, areas, models, trees, tree_r_m=3.5)
    for st in STAGES:
        b = stage_bounds(st)
        p = stage_bounds(st, pm(st))
        ov = Image.new("RGBA", cv.img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rectangle([cv.P((b[0], b[3])), cv.P((b[2], b[1]))], fill=st["color"] + (26,))
        cv.img.paste(ov, (0, 0), ov)
        cv.d.rectangle([cv.P((b[0], b[3])), cv.P((b[2], b[1]))], outline=st["color"], width=4 * SS)
        cv.dashed([(p[0], p[1]), (p[2], p[1]), (p[2], p[3]), (p[0], p[3]), (p[0], p[1])], st["color"], 1.6, 10, 7)
    label_features(cv, campus, areas, models_by_id, [(f, t, s) for f, t, s in KEY_LABELS if s >= 11])
    for st in STAGES:
        b = stage_bounds(st)
        f = font(15, bold=True)
        txt = f"{st['name'].split(' - ')[0].upper()}  {st['size']} m"
        x, y = cv.P((b[0], b[3]))
        l, t, r, bb = cv.d.textbbox((0, 0), txt, font=f)
        cv.d.rectangle([x, y - (bb - t) - 14 * SS, x + (r - l) + 16 * SS, y], fill=st["color"])
        cv.d.text((x + 8 * SS - l, y - (bb - t) - 7 * SS - t), txt, font=f, fill=(255, 255, 255))
    place_road_labels(cv, campus, ROAD_LABELS)
    top = cv.hm // SS
    cv.d.rectangle([0, cv.hm, cv.W, cv.H], fill=(255, 255, 255))
    cv.d.line([(0, cv.hm), (cv.W, cv.hm)], fill=(200, 196, 188), width=SS)
    cv.text((24, top + 14), "Stage windows (true 1:1 scale; 1 m = 100 game units; each window <= 600 m = +-30000 units)", 17, bold=True)
    cv.text((24, top + 38), f"Solid square = level window (visual extent). Dashed = play zone with collision; the outer "
                            f"band (50 m; 40 m Swamp; 30 m Reitz) is a visual-only backdrop.", 12, color=(80, 80, 80))
    y = top + 64
    for i, st in enumerate(STAGES):
        r = results[st["key"]]
        x = 24 + (i % 2) * 760
        yy = y + (i // 2) * 44
        cv.d.rectangle([x * SS, yy * SS, (x + 18) * SS, (yy + 18) * SS], fill=st["color"])
        bud = r["budget"]
        cv.text((x + 26, yy), f"{st['name']}", 13, bold=True)
        cv.text((x + 26, yy + 18), f"center ({st['center'][0]}, {st['center'][1]}) m, {st['size']} m; "
                                   f"{r['stats']['buildings']} bldgs; static collision ~{bud['static_total']} + "
                                   f"{RESERVE_OBJECTS} reserve = {bud['total']} / {SURFACE_POOL}", 12, color=(70, 70, 70))
    draw_legend(cv, 1560, top + 40)
    draw_scalebar(cv, 1560, top + 186, 400)
    draw_north(cv, 2340, top + 120)
    cv.text((2376, top + 214), "Map data (c) OpenStreetMap contributors, ODbL 1.0", 11, color=(90, 90, 90), anchor="ra")
    size_stages = cv.save(os.path.join(ART, "map_stages.png"))

    # ------------------------------------------------------------------ per-stage zoom maps
    stage_imgs = {}
    for st in STAGES:
        r = results[st["key"]]
        b = stage_bounds(st)
        p = stage_bounds(st, pm(st))
        pad = 30
        cv = Canvas(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad, 1900, extra_right=760)
        draw_base(cv, campus, areas, models, trees, tree_r_m=4.0)
        # dim outside window
        ov = Image.new("RGBA", cv.img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        X0p, Y0p = cv.P((b[0], b[3]))
        X1p, Y1p = cv.P((b[2], b[1]))
        od.rectangle([0, 0, cv.wm, Y0p], fill=(255, 255, 255, 150))
        od.rectangle([0, Y1p, cv.wm, cv.hm], fill=(255, 255, 255, 150))
        od.rectangle([0, Y0p, X0p, Y1p], fill=(255, 255, 255, 150))
        od.rectangle([X1p, Y0p, cv.wm, Y1p], fill=(255, 255, 255, 150))
        cv.img.paste(ov, (0, 0), ov)
        # 50 m grid with game-unit ticks
        cx, cy = st["center"]
        for k in range(-6, 7):
            gx = cx + k * 50
            gy = cy + k * 50
            if b[0] <= gx <= b[2]:
                cv.d.line([cv.P((gx, b[1])), cv.P((gx, b[3]))], fill=(120, 120, 120), width=1)
                cv.label((gx, b[1] + 6), f"{k * 5000:+d}" if k else "0", 9, color=(90, 90, 90), force=True, offsets=[(0, 0)])
            if b[1] <= gy <= b[3]:
                cv.d.line([cv.P((b[0], gy)), cv.P((b[2], gy))], fill=(120, 120, 120), width=1)
                cv.label((b[0] + 9, gy), f"{-k * 5000:+d}" if k else "0", 9, color=(90, 90, 90), force=True, offsets=[(0, 0)])
        cv.d.rectangle([cv.P((b[0], b[3])), cv.P((b[2], b[1]))], outline=st["color"], width=4 * SS)
        cv.dashed([(p[0], p[1]), (p[2], p[1]), (p[2], p[3]), (p[0], p[3]), (p[0], p[1])], st["color"], 2.0, 12, 8)
        # landmark outlines
        for lm in r["landmarks"]:
            pts, c = find_feature(lm["osm_id"], campus, areas, models_by_id)
            if pts:
                cv.line(pts + pts[:1], st["color"], 3 * SS)
            else:
                cv.d.ellipse([cv.P((c[0] - 4, c[1] + 4)), cv.P((c[0] + 4, c[1] - 4))], outline=st["color"], width=3 * SS)
        for lm in r["landmarks"]:
            cv.label(tuple(lm["center_m"]), lm["name"], 13, bold=True, color=(20, 20, 20), force=True)
        # other named buildings
        for m in sorted(models, key=lambda m: -m["area"]):
            if m["part"] or not m["name"] or m["id"] in {lm["osm_id"] for lm in r["landmarks"]}:
                continue
            if inside(m["c"], b) and m["area"] > 700:
                cv.label(m["c"], m["name"][:34], 10, color=(60, 60, 60))
        place_road_labels(cv, campus, ROAD_LABELS, 11)
        # side panel
        X = cv.wm // SS + 20
        cv.d.rectangle([cv.wm, 0, cv.W, cv.H], fill=(255, 255, 255))
        cv.d.line([(cv.wm, 0), (cv.wm, cv.H)], fill=(200, 196, 188), width=SS)
        cv.d.rectangle([X * SS, 22 * SS, (X + 14) * SS, 52 * SS], fill=st["color"])
        cv.text((X + 24, 20), st["name"].split(" - ")[0], 22, bold=True)
        sub = st["name"].split(" - ")[1] if " - " in st["name"] else ""
        cv.text((X + 24, 50), sub, 13, color=(80, 80, 80))
        s = r["stats"]
        bud = r["budget"]
        lines = [
            ("Window", None),
            (f"center ({cx}, {cy}) m from Century Tower; {st['size']} x {st['size']} m", 0),
            (f"x {b[0]:.0f}..{b[2]:.0f}  y {b[1]:.0f}..{b[3]:.0f} m; game +-{st['size'] * 50:.0f} units", 0),
            (f"play zone {st['size'] - 2 * pm(st)} m (dashed, {pm(st)} m backdrop band); grid 50 m = 5000 units", 0),
            ("Contents", None),
            (f"{s['buildings']} buildings ({s['buildings_in_play_zone']} in play zone, {s['backdrop_buildings']} backdrop)", 0),
            (f"footprint {s['footprint_area_m2']:,} m2 ({s['footprint_area_share'] * 100:.1f}% of window)", 0),
            (f"footprint verts {s['footprint_vertices_raw']:,} raw -> {s['footprint_vertices_simplified_generic']:,} simplified", 0),
            (f"heights: " + ", ".join(f"{k} {v}" for k, v in sorted(s["height_sources"].items())), 0),
            (f"road segs {s['segments'].get('road', 0)}, path segs {s['segments'].get('path', 0)}, "
             f"steps {s['segments'].get('steps', 0)}", 0),
            (f"trees {s['trees_osm']} mapped + ~{s['wood_scatter_trees_est']} in woods; water {s['water_area_m2']:,} m2", 0),
            ("Collision triangles (static)", None),
        ]
        for k, v in sorted(bud["items"].items(), key=lambda kv: -kv[1]):
            lines.append((f"{k.replace('_', ' ')}: {v:,}", 1))
        lines += [
            (f"static total {bud['static_total']:,} + reserve {RESERVE_OBJECTS:,} = {bud['total']:,} / {SURFACE_POOL:,}", 2),
            (f"headroom {bud['headroom']:,}   (naive extrusion: {s['naive_collision_tris']:,})", 0),
            (f"cells: max {r['cells'].get('max_surfaces_per_cell')} / p95 {r['cells'].get('p95_surfaces_per_cell')} "
             f"surfaces per 10.24 m cell", 0),
            ("Visual triangles (est.)", None),
            (f"{r['visual']['total']:,} total", 0),
            ("Landmarks (outlined)", None),
        ]
        for lm in r["landmarks"]:
            hh = f", {lm['height_m']} m" if "height_m" in lm else ""
            lines.append((f"{lm['name']} [{lm['treatment']}{hh}] {lm['collision_tris']} col", 1))
        y = 88
        for txt, kind in lines:
            if kind is None:
                y += 10
                cv.text((X, y), txt, 15, bold=True, color=st["color"])
                y += 24
            else:
                cv.text((X + (14 if kind == 1 else 0), y), txt, 12, bold=kind == 2, color=(35, 35, 35))
                y += 19
        draw_legend(cv, X, max(y + 24, cv.hm // SS - 236))
        draw_scalebar(cv, X, cv.hm // SS - 64, 100)
        cv.text((X, cv.hm // SS - 26), "Map data (c) OpenStreetMap contributors, ODbL 1.0", 10, color=(90, 90, 90))
        path = os.path.join(ART, f"stage_{st['key']}.png")
        stage_imgs[st["key"]] = (path, cv.save(path))

    # ------------------------------------------------------------------ feature geometry for stages.json
    def ring_out(pts, eps, n):
        return [[round(x, 1), round(y, 1)] for x, y in decimate(pts, eps, n)]
    field = next(a for a in areas if a["id"] == "w119378491")
    plaza = next(a for a in areas if a["id"] == "w264182367")
    bats = [models_by_id[i] for i in ("w196848221", "w424512419", "w866087250")]
    rock = next(p for p in campus["points"] if p["id"] == "n4741925737")
    features = {
        "ben_hill_griffin_stadium": {
            **STADIUM_FACTS,
            "outer_ring_m": ring_out(stadium["outer"], 0.75, 48),
            "bowl_opening_ring_m": ring_out(stadium["inner"][0], 0.5, 32) if stadium.get("inner") else None,
            "field_ring_m": [[round(x, 1), round(y, 1)] for x, y in field["rings"][0]],
            "field_center_m": [round(c, 1) for c in centroid(field["rings"][0])],
            "outer_bbox_m": [round(v, 1) for v in bbox(stadium["outer"])],
            "parts": [{"osm_id": m["id"], "name": m["name"], "min_height_m": m["min_h"], "height_m": m["h"],
                       "area_m2": round(m["area"])} for m in models if m["part"] and inside(m["c"], bbox(stadium["outer"]))],
        },
        "lake_alice": {
            **LAKE_FACTS,
            "outer_ring_m": ring_out(lake["rings"][0], 1.0, 64),
            "islands_m": [ring_out(h, 0.5, 10) for h in lake["holes"]],
            "bbox_m": [round(v, 1) for v in bbox(lake["rings"][0])],
            "water_box_suggestion": "one env region over bbox_m at water level y=0; lake bed -2.5 m, banks +0.5 m",
        },
        "plaza_of_the_americas": {"osm_id": "w264182367", "ring_m": ring_out(plaza["rings"][0], 0.5, 32),
                                  "bbox_m": [round(v, 1) for v in bbox(plaza["rings"][0])],
                                  "area_m2": round(poly_area(plaza["rings"][0]))},
        "bat_houses": [{"osm_id": m["id"], "center_m": [round(m["c"][0], 1), round(m["c"][1], 1)],
                        "area_m2": round(m["area"], 1), "height_m": m["h"]} for m in bats],
        "turlington_rock": {"osm_id": rock["id"], "name": rock["tags"].get("name"), "center_m": rock["pt"],
                            "height_m": 3.0, "notes": "OSM historic=stone, height=3; 'Turlington Rock, 1984' marker (HMdb)",
                            "source": "https://www.hmdb.org/m.asp?m=151249"},
    }

    interiors = []
    for it in INTERIOR_STAGES:
        m = models_by_id[it["osm_id"]]
        pts = m["raw"]["pts"]
        rect = min_area_rect(pts)
        sides = sorted(math.dist(rect[i], rect[(i + 1) % 4]) for i in range(2))
        interiors.append({**it, "footprint_area_m2": round(m["area"], 1), "footprint_dims_m": [round(s, 1) for s in sides],
                          "height_m": m["h"], "center_m": [round(m["c"][0], 1), round(m["c"][1], 1)],
                          "window_m": round(max(sides) + 20), "collision_budget_hint": 4000 if "tower" in it["key"] else 7000})

    out = {
        "schema": "sgl64.stages/1",
        "generated_by": "tools/campus/stage_planner.py",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "source": {"campus_json": "data/uf/campus.json", "raw_tiles": "data/uf/tiles/*.osm",
                   "attribution": "Map data (c) OpenStreetMap contributors, ODbL 1.0"},
        "images": {"overview": "art/campus/map_overview.png", "stages": "art/campus/map_stages.png",
                   **{k: os.path.relpath(v[0], ROOT) for k, v in stage_imgs.items()}},
        "coordinate_system": {
            "map": "meters; x = east, y = north; origin = Century Tower centroid",
            "origin_latlon": campus["origin_latlon"],
            "game_units_per_meter": UNITS_PER_M,
            "map_to_game": "X = round((x - center_x) * 100); Z = round(-(y - center_y) * 100); Y = round(height_m * 100)",
            "level_bounds_units": [-32768, 32767],
            "note": "SM64 is Y-up and +Z points south, hence the minus sign on Z. Windows are axis-aligned (north up).",
        },
        "engine_budget": {
            "surface_pool_design_cap": SURFACE_POOL,
            "reserve_for_objects_players": RESERVE_OBJECTS,
            "static_cap": SURFACE_POOL - RESERVE_OBJECTS,
            "cell_size_units": CELL_UNITS, "num_cells_per_axis": NUM_CELLS,
            "ground_patch_m": GROUND_PATCH_M, "default_play_margin_m": PLAY_MARGIN_M,
            "notes": [
                "In the v1.5.1 source, src/engine/surface_load.c allocates surfaces and nodes from GrowingArrays "
                "that double on demand, and nothing in that file reads SURFACE_POOL_SIZE. So 16384 works as a "
                "performance/design cap, not as a crash limit. Per-cell density (surfaces per 10.24 m cell) is "
                "what find_floor/find_wall pay for each player and object every frame.",
                "DynOS COL_VERTEX/COL_TRI args are s16: <= 32767 verts per collision; coords fit +-32767 (window <= 655 m).",
                "Object (non-level) collision models are capped at 4095 vertices.",
                "Environment (water) regions are capped at 20 per area.",
                "GEO_CAMERA_FRUSTUM far plane is s16: max draw distance ~32767 units (327 m). Use fog and keep backdrop "
                "shells cheap.",
            ],
        },
        "height_rules": {
            "priority": ["landmark_heights (hand-set below)", "OSM height / building:height",
                         "OSM building:levels x floor_height[type] + 1 m parapet (flat roofs)",
                         "default levels by type + footprint area (rule below)"],
            "floor_height_m": FLOOR_H,
            "default_levels": {
                "university/college/school/office/commercial/civic": "1 if area<150 m2, 2 if <1500, 3 if <5000, else 4",
                "hospital": 5, "dormitory": 4, "hotel": 5, "apartments": "2 if area<800 else 3",
                "residential": "1 if area<150 else 2", "parking (structure)": 4,
                "house/detached/industrial/warehouse/service/garage/barn/greenhouse/shed/retail/grandstand": 1,
                "yes (unknown)": "1 if area<400, 2 if <2000, else 3; any building <30 m2 -> 3.0 m",
                "roof/pavilion/carport/shelter": "canopy slab at 4.0 m, no walls",
                "stadium (other)": "20 m", "church/chapel": "9 m + steep roof",
            },
            "parapet_m": 1.0,
            "roof": "hip for house/detached/residential/church/chapel/barn/shed with <= 8 verts or roof:shape hipped/gabled; "
                    "otherwise flat. Hip ridge = min(0.25 x short side, 4 m). Collision may use flat roofs everywhere.",
            "coverage": dict(Counter(m["src"] for m in models if not m["part"])),
        },
        "landmark_heights": [
            {"osm_id": i, "name": n, "height_m": h, "floors": f, "basis": basis, "source": s, "url": u, "confidence": c}
            for i, n, h, f, basis, s, u, c in LANDMARK_HEIGHTS],
        "simplification_rules": {
            "skip": "area < 15 m2, or building in construction/no/corridor/ruins/bridge -> not built",
            "tiny": "15-60 m2 -> minimum-area bounding rectangle (4 verts): 8 wall + 2 roof tris",
            "small": "60-300 m2 -> Douglas-Peucker 1.0 m, max 8 verts",
            "normal": "300-3000 m2 -> Douglas-Peucker 0.75 m, max 16 verts",
            "large": "> 3000 m2 -> Douglas-Peucker 0.75 m, max 24 verts (tolerance x1.4 until it fits); "
                     "fallback to min-area rectangle if area drops > 40%",
            "canopy": "roof/pavilion/shelter -> roof slab only (max 8 verts), posts visual-only",
            "building_parts": "OSM building:part ways are used only to guide hand-modeled landmarks (the stadium tiers)",
            "shared_walls": "adjacent buildings that share edges: cull the hidden wall of the lower building (both are in OSM as separate ways)",
            "backdrop": f"buildings whose centroid lies in the outer backdrop band (stages[].play_margin_m): visual-only shells (<= 8 verts, flat), no collision",
            "trees": "mapped trees are visual low-poly (12 tris); woods are scattered billboards (1 per 80 m2); "
                     "only gameplay trees become climbable tree objects (0 static tris, use object slots)",
            "paths_roads": "painted into the ground texture / visual ribbons only; no collision. Curbs are not modeled.",
            "steps": "each simplified steps segment -> ramp + 2 cheek walls (4 tris)",
            "barriers": "walls/fences -> double-sided thin wall, 4 tris per simplified segment",
            "ground": f"{GROUND_PATCH_M} m collision patches (4x4 cells, offset half a cell); 10.24 m visual grid for vertex color",
            "landmarks": "hand-modeled in Blender with the per-landmark collision budgets in stages[].landmarks",
        },
        "features": features,
        "stages": [],
        "interior_stages": interiors,
        "finale": {"name": "The Final Exam", "where": "top of Century Tower (hub)", "top_height_m": 47.9,
                   "notes": "Build as its own small level: an arena floating at belfry height with the hub as backdrop "
                            "(baked low-poly skybox ring), so the hub level doesn't need boss collision."},
    }
    def overlaps(st):
        a = stage_bounds(st)
        res = []
        for o in STAGES:
            if o is st:
                continue
            b = stage_bounds(o)
            w = min(a[2], b[2]) - max(a[0], b[0])
            h = min(a[3], b[3]) - max(a[1], b[1])
            if w > 0 and h > 0:
                shared = [lm["name"] for lm in results[o["key"]]["landmarks"] if inside(tuple(lm["center_m"]), a)]
                res.append({"stage": o["key"], "area_m2": round(w * h), "landmarks_of_other_stage_inside": shared})
        return res

    for st in STAGES:
        r = results[st["key"]]
        b = stage_bounds(st)
        p = stage_bounds(st, pm(st))
        cx, cy = st["center"]
        out["stages"].append({
            "key": st["key"], "name": st["name"], "suggested_hub_entrance": st["entrance"],
            "center_m": list(st["center"]), "size_m": st["size"],
            "bounds_m": {"xmin": b[0], "ymin": b[1], "xmax": b[2], "ymax": b[3]},
            "play_margin_m": pm(st),
            "play_bounds_m": {"xmin": p[0], "ymin": p[1], "xmax": p[2], "ymax": p[3]},
            "game_bounds_units": {"x": [-st["size"] * 50, st["size"] * 50], "z": [-st["size"] * 50, st["size"] * 50]},
            "map_color": "#%02x%02x%02x" % st["color"],
            "landmarks": r["landmarks"], "stats": r["stats"], "collision_budget": r["budget"],
            "visual_estimate": r["visual"], "collision_cells": r["cells"],
            "overlaps": overlaps(st),
        })
    with open(os.path.join(DATA, "stages.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("overview", size_overview, "stages", size_stages)
    for st in STAGES:
        r = results[st["key"]]
        print(st["key"], json.dumps(r["stats"]["segments"]), "trees", r["stats"]["trees_osm"])
        print("   bldgs", r["stats"]["buildings"], "fp", r["stats"]["footprint_area_m2"], "raw", r["stats"]["raw_prism_tris_flat_roofs"],
              "naive", r["stats"]["naive_collision_tris"], "budget", r["budget"]["items"], "static", r["budget"]["static_total"],
              "total", r["budget"]["total"], "vis", r["visual"]["total"], r["cells"])
        for lm in r["landmarks"]:
            print("     ", lm["name"], lm.get("fully_inside_window"), lm["edge_clearance_m"], lm["in_play_zone"], lm.get("play_zone_clearance_m"))


if __name__ == "__main__":
    main()
