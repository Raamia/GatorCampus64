"""Prepare everything build_stage.py needs for one stage window from the OSM extract, using the
stage planner's rules (heights, footprint simplification, area styles).

Usage: tools/.venv/bin/python -I tools/campus/stage_data.py <stage_key> <out.json>
Reads data/uf/campus.json, data/uf/stages.json and the raw tiles in data/uf/tiles (multipolygon
relations: water / grass / parking). Output is in MAP METRES (x = east, y = north, origin =
Century Tower). Map data (c) OpenStreetMap contributors, ODbL 1.0.

Extents (s16 vertex limit = +-327.67 m around the stage centre):
  window   stages.json bounds_m        (580 m: the stage)
  play     stages.json play_bounds_m   (480 m: collision + invisible boundary walls)
  extent   centre +- EXTENT_HALF_M      (visual ground, far building shells, tree line ring)
"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stage_planner as sp  # noqa: E402

EXTENT_HALF_M = 324.0

# Collegiate Gothic / historic-core buildings with red clay tile hip or gable roofs (UF Historic
# District + newer buildings built in that style). Everything else gets a flat roof + parapet.
TILE_ROOF_NAMES = {
    "Anderson Hall", "Peabody Hall", "Keene-Flint Hall", "Smathers Library", "Thomas Hall",
    "Buckman Hall", "Sledd Hall", "Fletcher Hall", "Murphree Hall", "Newell Hall", "Griffin-Floyd Hall",
    "Rolfs Hall", "Dauer Hall", "Walker Hall", "Leigh Hall", "Matherly Hall", "Pugh Hall", "Stuzin Hall",
    "Student Infirmary", "University Auditorium", "Bryan Hall", "Tigert Hall", "Floyd Hall", "Flint Hall",
    "Grove Hall", "Ustler Hall", "Norman Hall", "Yon Hall",
}
# facade style by name (default: modern brick with punched windows)
GOTHIC_FACADE = TILE_ROOF_NAMES | {"Carleton Auditorium", "Farrior Hall", "Women's Gym", "Infirmary"}
GLASS_FACADE = {"The Hub", "Ramos Collaboratory", "Antevy Hall", "Little Hall Express", "Malachowsky Hall"}
BAND_FACADE = {"Turlington Hall", "Library West", "Music Building", "Grinter Hall", "Marston Science Library",
               "Chemistry Laboratory", "Sisler Hall", "Bryant Space Science Center", "Criser Hall",
               "Steinbrenner Band Hall", "Scott Family Hall"}
SERVICE_TYPES = {"service", "garage", "garages", "shed", "industrial", "warehouse", "yes"}

ROAD_WIDTH = {"motorway": 14, "trunk": 14, "primary": 14, "secondary": 11, "tertiary": 9, "unclassified": 7,
              "residential": 7, "living_street": 6, "service": 4.5, "primary_link": 7, "secondary_link": 7,
              "tertiary_link": 6, "trunk_link": 7}
PATH_WIDTH = {"footway": 2.0, "path": 1.6, "cycleway": 2.5, "pedestrian": 4.0, "steps": 2.0, "bridleway": 2.0,
              "track": 3.0}


def h01(s):
    """Deterministic 0..1 hash of a string."""
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def fnum(v, default=None):
    try:
        return float(str(v).replace("m", "").strip())
    except (TypeError, ValueError):
        return default


def bbox_overlap(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def ccw(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return list(pts) if a >= 0 else list(reversed(pts))


def clip_polyline(pts, bnd):
    """Clip a polyline to a box; returns a list of polylines."""
    out, cur = [], []
    for a, b in zip(pts, pts[1:]):
        c = sp.clip_segment(a, b, *bnd)
        if not c:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
            continue
        p, q = c
        if cur and math.dist(cur[-1], p) < 1e-6:
            cur.append(q)
        else:
            if len(cur) >= 2:
                out.append(cur)
            cur = [p, q]
        if math.dist(q, b) > 1e-6:  # left the box
            out.append(cur)
            cur = []
    if len(cur) >= 2:
        out.append(cur)
    return out


def r2(p):
    return [round(p[0], 2), round(p[1], 2)]


def ground_class(tags):
    """Ground layer of an OSM area (None = leave the base ground)."""
    nat, lu, le, am = tags.get("natural"), tags.get("landuse"), tags.get("leisure"), tags.get("amenity")
    surf = tags.get("surface", "")
    if nat == "water" or tags.get("water") or le == "swimming_pool":
        return "water"
    if am == "fountain":
        return "fountain"
    if nat == "wood" or lu == "forest":
        return "forest"
    if surf == "woodchips" or nat == "scrub":
        return "mulch"
    if am in ("parking", "motorcycle_parking") or tags.get("parking"):
        return "parking"
    paved = surf in ("paving_stones", "brick", "sett", "concrete", "paved", "pebblestone", "concrete:plates", "asphalt")
    if lu == "grass" or le in ("garden", "park", "dog_park", "playground", "village_green") or nat in ("grass", "heath"):
        return "lawn"
    if le == "common":
        return "plaza" if paved else "lawn"
    if tags.get("highway") in ("pedestrian", "footway") or tags.get("man_made") == "courtyard" \
            or tags.get("place") == "square" or le in ("outdoor_seating", "yes") and paved \
            or am == "bicycle_parking":
        return "plaza"
    return None


def plaza_material(tags):
    surf = tags.get("surface", "")
    if surf in ("paving_stones", "brick", "sett"):
        return "plaza_brick"
    return "concrete"


def path_material(tags):
    surf = tags.get("surface", "")
    if surf in ("paving_stones", "brick", "sett"):
        return "plaza_brick"
    if surf == "asphalt":
        return "parking"
    if surf in ("ground", "dirt", "woodchips", "unpaved", "grass", "mulch", "compacted", "gravel"):
        return "mulch"
    return "sidewalk"


def tree_kind(p):
    t = p["tags"]
    lt = t.get("leaf_type")
    if lt == "palm":
        return "palm"
    if lt == "needleleaved" or t.get("genus", "").lower() == "pinus":
        return "pine"
    # untagged trees on the central campus are mostly southern live oaks
    return "oak"


def dist_point_seg(p, a, b):
    return sp._seg_dist(p, a, b)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: stage_data.py <stage_key> <out.json>")
    key, out_path = sys.argv[1], sys.argv[2]
    stages = json.load(open(os.path.join(sp.DATA, "stages.json")))
    st = next((s for s in stages["stages"] if s["key"] == key), None)
    if st is None:
        sys.exit(f"stage {key!r} not in stages.json")
    cx, cy = st["center_m"]
    wb = st["bounds_m"]
    pb = st["play_bounds_m"]
    win = (wb["xmin"], wb["ymin"], wb["xmax"], wb["ymax"])
    play = (pb["xmin"], pb["ymin"], pb["xmax"], pb["ymax"])
    ext = (cx - EXTENT_HALF_M, cy - EXTENT_HALF_M, cx + EXTENT_HALF_M, cy + EXTENT_HALF_M)

    campus, areas, _stadium = sp.load()

    # ------------------------------------------------------------------ buildings
    buildings = []
    footprints_for_trees = []
    for b in campus["buildings"]:
        if b.get("part"):
            continue
        bb = sp.bbox(b["pts"])
        if not bbox_overlap(bb, ext):
            continue
        m = sp.building_model(b)
        if m["cls"] == "skip" or m["area"] < 15:
            continue
        name = m["name"] or ""
        in_window = sp.inside(m["c"], win)
        collide = in_window and bbox_overlap(bb, (play[0] - 1, play[1] - 1, play[2] + 1, play[3] + 1))
        if in_window:
            pts = ccw(m["pts"])
        else:
            pts = ccw(sp.decimate(b["pts"], 1.5, 8)) if len(b["pts"]) > 4 else ccw(b["pts"])
        clipped = sp.clip_poly(pts, *ext)
        if len(clipped) < 3 or sp.poly_area(clipped) < 10:
            continue
        if len(clipped) != len(pts) or any(math.dist(a, c) > 1e-6 for a, c in zip(pts, clipped)):
            pts = ccw(clipped)
        btype = m["type"]
        if m["cls"] == "canopy":
            style = "canopy"
        elif name in GLASS_FACADE:
            style = "glass"
        elif name in BAND_FACADE:
            style = "band"
        elif name in GOTHIC_FACADE:
            style = "gothic"
        elif btype in SERVICE_TYPES and m["area"] < 400:
            style = "service"
        else:
            style = "brick"
        roof = "flat"
        if m["cls"] != "canopy" and (name in TILE_ROOF_NAMES or b["tags"].get("roof:shape") in ("hipped", "gabled")):
            roof = "hip"
        buildings.append({
            "id": m["id"], "name": m["name"], "type": btype, "cls": m["cls"], "pts": [r2(p) for p in pts],
            "area": round(m["area"], 1), "h": round(m["h"], 2), "h_src": m["src"], "roof": roof, "style": style,
            "levels": fnum(b["tags"].get("building:levels")), "in_window": in_window, "collide": bool(collide),
            "historic": bool(b["tags"].get("historic")), "c": r2(m["c"]),
            "raw_pts": [r2(p) for p in b["pts"]] if in_window else None,
        })
        footprints_for_trees.append(pts)

    # ------------------------------------------------------------------ ground areas
    out_areas, waters, fountains = [], [], []
    for a in areas:
        cls = ground_class(a["tags"])
        if cls is None:
            continue
        rings = []
        for r in a["rings"]:
            if not bbox_overlap(sp.bbox(r), ext):
                continue
            c = sp.clip_poly(r, *ext)
            if len(c) >= 3 and sp.poly_area(c) >= 4:
                rings.append(c)
        if not rings:
            continue
        holes = [sp.clip_poly(h, *ext) for h in a["holes"] if bbox_overlap(sp.bbox(h), ext)]
        holes = [h for h in holes if len(h) >= 3 and sp.poly_area(h) >= 2]
        if cls == "water":
            for r in rings:
                ring = ccw(sp.decimate(r, 0.6, 28))
                waters.append({"id": a["id"], "name": a["tags"].get("name"), "ring": [r2(p) for p in ring],
                               "bbox": [round(v, 2) for v in sp.bbox(ring)], "area": round(sp.poly_area(ring), 1)})
            continue
        if cls == "fountain":
            for r in rings:
                fountains.append({"id": a["id"], "ring": [r2(p) for p in ccw(sp.decimate(r, 0.3, 12))]})
            continue
        mat = {"lawn": "lawn", "forest": "forest_floor", "mulch": "mulch", "parking": "parking",
               "plaza": plaza_material(a["tags"])}[cls]
        for r in rings:
            ring = ccw(sp.simplify_ring(r, 0.25)) if len(r) > 6 else ccw(r)
            if len(ring) < 3:
                continue
            hs = [list(reversed(ccw(sp.simplify_ring(h, 0.25) if len(h) > 6 else h))) for h in holes
                  if sp.point_in_poly(sp.centroid(h), r)]
            out_areas.append({"id": a["id"], "cls": cls, "mat": mat, "ring": [r2(p) for p in ring],
                              "holes": [[r2(p) for p in h] for h in hs], "area": round(sp.poly_area(ring), 1)})

    # ------------------------------------------------------------------ roads, paths, barriers
    roads, paths, barriers = [], [], []
    for w in campus["ways"]:
        t = w["tags"]
        hw = t.get("highway")
        if not bbox_overlap(sp.bbox(w["pts"]), ext):
            continue
        if t.get("indoor") == "yes" or t.get("tunnel") in ("yes", "building_passage") or t.get("bridge") == "yes":
            continue
        if t.get("level") not in (None, "", "0") or t.get("layer") not in (None, "", "0"):
            continue
        if t.get("area") == "yes":
            continue
        pts = sp.rdp(w["pts"], 0.25) if len(w["pts"]) > 2 else w["pts"]
        if hw in ROAD_WIDTH:
            width = fnum(t.get("width")) or ROAD_WIDTH[hw]
            if hw == "service" and t.get("service") == "parking_aisle" and not t.get("width"):
                width = 6.0
            if hw == "service" and t.get("service") == "driveway" and not t.get("width"):
                width = 3.5
            two_way = t.get("oneway") not in ("yes", "1", "-1") and hw not in ("service",) and width >= 6
            for seg in clip_polyline(pts, ext):
                roads.append({"id": w["id"], "cls": hw, "name": t.get("name"), "width": round(width, 2),
                              "center_line": two_way, "pts": [r2(p) for p in seg]})
        elif hw in PATH_WIDTH:
            fw = t.get("footway", "")
            kind = "crossing" if fw == "crossing" or t.get("path") == "crossing" else ("steps" if hw == "steps" else "path")
            width = fnum(t.get("width")) or (3.0 if kind == "crossing" else PATH_WIDTH[hw])
            width = max(1.2, min(width, 8.0))
            mat = {"crossing": "crosswalk", "steps": "steps"}.get(kind) or path_material(t)
            for seg in clip_polyline(pts, ext):
                paths.append({"id": w["id"], "kind": kind, "mat": mat, "width": round(width, 2),
                              "pts": [r2(p) for p in seg]})
        elif t.get("barrier") in ("wall", "retaining_wall", "fence", "hedge"):
            hgt = fnum(t.get("height")) or {"wall": 1.2, "retaining_wall": 1.0, "fence": 1.5, "hedge": 1.2}[t["barrier"]]
            for seg in clip_polyline(pts, ext):
                barriers.append({"id": w["id"], "kind": t["barrier"], "height": hgt, "pts": [r2(p) for p in seg]})

    # ------------------------------------------------------------------ trees
    bldg_boxes = [(sp.bbox(p), p) for p in footprints_for_trees]

    def clearance(pt):
        best = 99.0
        for bb, poly in bldg_boxes:
            if pt[0] < bb[0] - 10 or pt[0] > bb[2] + 10 or pt[1] < bb[1] - 10 or pt[1] > bb[3] + 10:
                continue
            if sp.point_in_poly(pt, poly):
                return -1.0
            for a, b in zip(poly, poly[1:] + poly[:1]):
                best = min(best, dist_point_seg(pt, a, b))
        return best

    def in_water(pt):
        return any(sp.point_in_poly(pt, w["ring"]) for w in waters)

    trees = []
    for p in campus["points"]:
        if p["tags"].get("natural") != "tree":
            continue
        pt = tuple(p["pt"])
        if not sp.inside(pt, (ext[0] + 4, ext[1] + 4, ext[2] - 4, ext[3] - 4)):
            continue
        cl = clearance(pt)
        if cl < 0.8 or in_water(pt):
            continue
        trees.append({"id": p["id"], "pt": r2(pt), "kind": tree_kind(p), "clear": round(cl, 2),
                      "crown": fnum(p["tags"].get("diameter_crown"))})
    # scatter in mapped woods: ~1 tree per 80 m2, at least 5 m apart
    for a in out_areas:
        if a["cls"] != "forest":
            continue
        ring = a["ring"]
        x0, y0, x1, y1 = sp.bbox(ring)
        n_target = int(a["area"] / 80)
        placed = []
        k = 0
        while len(placed) < n_target and k < n_target * 40:
            k += 1
            u, v = h01(f"{a['id']}:{k}:u"), h01(f"{a['id']}:{k}:v")
            pt = (x0 + u * (x1 - x0), y0 + v * (y1 - y0))
            if not sp.point_in_poly(pt, ring) or any(math.dist(pt, q) < 5.0 for q in placed):
                continue
            if any(math.dist(pt, tuple(t["pt"])) < 4.0 for t in trees):
                continue
            cl = clearance(pt)
            if cl < 2.0:
                continue
            placed.append(pt)
            trees.append({"id": f"{a['id']}#{k}", "pt": r2(pt), "kind": "oak" if h01(f"k{k}") < 0.6 else "pine",
                          "clear": round(cl, 2), "crown": None})

    # ------------------------------------------------------------------ points of interest
    pois = {}
    for p in campus["points"]:
        # hand-modelled hub props (stage_landmarks.props): only when they stand in this stage's play zone
        if p["id"] in ("n4741925737", "n1637323042", "n8045866345", "n5145535993", "n5623470779") \
                and sp.inside(p["pt"], play):
            pois[p["id"]] = {"pt": r2(p["pt"]), "name": p["tags"].get("name"), "height": fnum(p["tags"].get("height"))}

    data = {
        "key": key, "name": st["name"], "center": [cx, cy], "window": list(win), "play": list(play),
        "extent": [round(v, 2) for v in ext], "extent_half_m": EXTENT_HALF_M,
        "stage": st, "buildings": buildings, "areas": out_areas, "water": waters, "fountains": fountains,
        "roads": roads, "paths": paths, "barriers": barriers, "trees": trees, "pois": pois,
        "attribution": "Map data (c) OpenStreetMap contributors, ODbL 1.0",
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f)
    print(f"stage_data {key}: {len(buildings)} buildings ({sum(b['collide'] for b in buildings)} with collision), "
          f"{len(out_areas)} areas, {len(waters)} water, {len(roads)} road + {len(paths)} path polylines, "
          f"{len(barriers)} barriers, {len(trees)} trees -> {out_path}")


if __name__ == "__main__":
    main()
