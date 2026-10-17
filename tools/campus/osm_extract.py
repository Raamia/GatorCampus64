# Merge the raw OpenStreetMap tiles in data/uf/tiles/*.osm into one compact JSON
# with coordinates in local meters (x = east, y = north) around Century Tower.
#
# Map data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
#
# Usage: python3 -I tools/campus/osm_extract.py   -> data/uf/campus.json
import glob
import json
import math
import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "uf")

# Origin: Century Tower (approx.); refined below if the tower is found in the data.
ORIGIN = (29.64905, -82.34262)
M_PER_DEG_LAT = 111_320.0

KEEP_WAY_KEYS = ("building", "highway", "natural", "leisure", "landuse", "amenity", "man_made",
                 "water", "barrier", "waterway", "sport", "railway", "parking")
KEEP_NODE_KEYS = ("natural", "amenity", "tourism", "historic", "leisure", "man_made")


def load_tiles():
    nodes, ways, relations = {}, {}, {}
    for path in sorted(glob.glob(os.path.join(DATA, "tiles", "*.osm"))):
        root = ET.parse(path).getroot()
        for el in root:
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            if el.tag == "node":
                nodes[el.get("id")] = (float(el.get("lat")), float(el.get("lon")), tags)
            elif el.tag == "way":
                ways[el.get("id")] = ([nd.get("ref") for nd in el.findall("nd")], tags)
            elif el.tag == "relation":
                members = [(m.get("type"), m.get("ref"), m.get("role")) for m in el.findall("member")]
                relations[el.get("id")] = (members, tags)
    return nodes, ways, relations


def to_local(lat, lon, origin):
    lat0, lon0 = origin
    x = (lon - lon0) * M_PER_DEG_LAT * math.cos(math.radians(lat0))
    y = (lat - lat0) * M_PER_DEG_LAT
    return round(x, 2), round(y, 2)


def polygon_area(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def height_of(tags):
    """Best-effort height in meters: height tag, else levels * 3.5 m."""
    h = tags.get("height") or tags.get("building:height")
    if h:
        try:
            return float(h.replace("m", "").strip()), "height"
        except ValueError:
            pass
    lv = tags.get("building:levels")
    if lv:
        try:
            return float(lv) * 3.5 + 1.0, "levels"
        except ValueError:
            pass
    return None, None


def main():
    nodes, ways, relations = load_tiles()
    origin = ORIGIN
    for lat, lon, tags in nodes.values():
        if tags.get("name", "").lower() == "century tower":
            origin = (lat, lon)
    for refs, tags in ways.values():
        if tags.get("name", "").lower() == "century tower":
            pts = [nodes[r][:2] for r in refs if r in nodes]
            origin = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    def way_points(refs):
        return [to_local(nodes[r][0], nodes[r][1], origin) for r in refs if r in nodes]

    out = {"origin_latlon": origin, "units": "meters, x=east y=north",
           "attribution": "Map data (c) OpenStreetMap contributors, ODbL 1.0",
           "buildings": [], "ways": [], "areas": [], "points": []}

    building_way_ids = set()
    for rid, (members, tags) in relations.items():
        if "building" not in tags:
            continue
        outer = [ref for typ, ref, role in members if typ == "way" and role in ("outer", "") and ref in ways]
        for ref in outer:
            building_way_ids.add(ref)
            pts = way_points(ways[ref][0])
            if len(pts) >= 4:
                h, src = height_of(tags)
                out["buildings"].append({"id": f"r{rid}/{ref}", "tags": tags, "pts": pts[:-1] if pts[0] == pts[-1] else pts,
                                         "height": h, "height_src": src})

    for wid, (refs, tags) in ways.items():
        if not tags or wid in building_way_ids:
            continue
        pts = way_points(refs)
        if len(pts) < 2:
            continue
        closed = refs[0] == refs[-1]
        if "building" in tags or "building:part" in tags:
            if closed and len(pts) >= 4:
                h, src = height_of(tags)
                out["buildings"].append({"id": f"w{wid}", "tags": tags, "pts": pts[:-1], "height": h, "height_src": src,
                                         "part": "building:part" in tags})
        elif any(k in tags for k in KEEP_WAY_KEYS):
            kind = "areas" if closed and ("highway" not in tags or tags.get("area") == "yes") else "ways"
            out[kind].append({"id": f"w{wid}", "tags": tags, "pts": pts[:-1] if kind == "areas" else pts})

    for nid, (lat, lon, tags) in nodes.items():
        if tags and any(k in tags for k in KEEP_NODE_KEYS):
            out["points"].append({"id": f"n{nid}", "tags": tags, "pt": to_local(lat, lon, origin)})

    for b in out["buildings"]:
        b["area_m2"] = round(polygon_area(b["pts"]), 1)
    path = os.path.join(DATA, "campus.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"wrote {path}: {len(out['buildings'])} buildings, {len(out['ways'])} ways, "
          f"{len(out['areas'])} areas, {len(out['points'])} points; origin {origin}")


if __name__ == "__main__":
    main()
