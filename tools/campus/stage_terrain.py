"""Stage terrain heights from USGS 3DEP (real ground relief for the generated stages).

Runtime API (pure Python, safe inside Blender and in landmark modules):

    height_m(stage_key, x_m, y_m) -> float

map metres in (x = east, y = north, origin = Century Tower, as data/uf/campus.json), metres above the
stage's ground datum out. 0.0 for a stage without a heightfield (every stage except reitz_eng) and
outside the data.

The heightfield (data/uf/elevation_<stage>.json) is a node grid aligned with stage_ground's 20.48 m
collision/UV tiles (lines at center + 5.12 + k * 20.48), piecewise planar over two triangles per tile
(split on the tile's south-west -> north-east diagonal). build_stage.apply_terrain cuts the draped meshes
on the tile lines and those diagonals, so the ground, its collision and the road ribbons lie exactly on it.

Builder (needs numpy + Pillow, run with tools/.venv/bin/python -I):

    tools/.venv/bin/python -I tools/campus/stage_terrain.py build reitz_eng

reads the raw 3DEP export saved under data/uf/tiles/ (gitignored) and writes data/uf/elevation_reitz_eng.json:
relative relief = smoothed DEM minus a smooth local reference (normalised convolution of the DEM over the
protected zones), forced to 0 in the protected zones (Reitz Union footprint + 25 m, every reitz_points
anchor + 8 m, spawn + 10 m, the Reitz ravine, ponds, the landmark buildings, the play-zone edge) with a
~20 m blend, slopes clamped so Mario can walk (18 degrees), relief clamped to +-RELIEF_MAX_M.
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data", "uf")
TILE = 20.48          # stage_ground.TILE
TILE_OFF = 5.12       # stage_ground.TILE_OFF
TERRAIN_STAGES = ("reitz_eng",)

_cache = {}


def _load(stage_key):
    if stage_key in _cache:
        return _cache[stage_key]
    hf = None
    if stage_key in TERRAIN_STAGES:
        path = os.path.join(DATA, f"elevation_{stage_key}.json")
        try:
            with open(path) as f:
                d = json.load(f)
            g = d["grid"]
            hf = (float(g["x0_m"]), float(g["y0_m"]), float(g["step_m"]), int(g["nx"]), int(g["ny"]),
                  g["heights_cm"])
        except (OSError, KeyError, ValueError):
            hf = None
    _cache[stage_key] = hf
    return hf


def has_terrain(stage_key):
    return _load(stage_key) is not None


def height_m(stage_key, x_m, y_m):
    """Map metres in -> metres above the stage's ground datum (0.0 = flat / no data)."""
    hf = _load(stage_key)
    if hf is None:
        return 0.0
    x0, y0, step, nx, ny, rows = hf
    fx = (x_m - x0) / step
    fy = (y_m - y0) / step
    if not (0.0 <= fx <= nx - 1 and 0.0 <= fy <= ny - 1):
        return 0.0
    i = min(int(fx), nx - 2)
    j = min(int(fy), ny - 2)
    tx, ty = fx - i, fy - j
    r0, r1 = rows[j], rows[j + 1]
    # piecewise planar: each tile is two triangles split on its (0,0)-(1,1) diagonal (x - y = const), so a mesh
    # cut on the tile lines + these diagonals and draped at its vertices lies exactly on height_m
    if tx >= ty:
        h = r0[i] + (r0[i + 1] - r0[i]) * tx + (r1[i + 1] - r0[i + 1]) * ty
    else:
        h = r0[i] + (r1[i] - r0[i]) * ty + (r1[i + 1] - r1[i]) * tx
    return h / 100.0


# --------------------------------------------------------------------------------------------- builder
M_PER_DEG_LAT = 111_320.0          # osm_extract.to_local (equirectangular about origin_latlon)
SMOOTH_SIGMA_M = 5.0               # DEM de-noise before sampling the nodes
REF_SIGMA_M = 70.0                 # local reference: normalised convolution over the protected zones
BLEND_M = 20.0
RELIEF_MAX_M = 6.0
MAX_SLOPE_DEG = 18.0
TWIST_MAX_M = 0.8                # caps the crease along a tile's diagonal
RAW_NAME = "3dep_reitz_eng.tif"
SOURCE_URL_FILE = "3dep_reitz_eng.url"
ZONES = {   # osm ids / anchors of the reitz_eng protected zones (margin metres)
    "reitz_union": ("w863211313", 25.0),
    "malachowsky": ("w1094502850", 10.0),
    "weil": ("w445808709", 10.0),
    "clock_tower": ("w481256532", 10.0),
    "ravine_trail": ("w428102720", 30.0),
}
ANCHOR_MARGIN_M = 8.0
SPAWN = (-398.0, -200.0)           # build_stage.SPAWN["reitz_eng"]
SPAWN_MARGIN_M = 10.0
WATER_MARGIN_M = 10.0
EDGE_MARGIN_M = 15.0               # inside the play bounds: fade back to 0 (boundary walls, backdrop)


def _seg_dist(np, X, Y, pts, closed):
    d = np.full(X.shape, np.inf)
    n = len(pts)
    m = n if closed else n - 1
    for k in range(m):
        ax, ay = pts[k]
        bx, by = pts[(k + 1) % n]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy or 1e-9
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0.0, 1.0)
        d = np.minimum(d, np.hypot(X - (ax + t * vx), Y - (ay + t * vy)))
    return d


def _inside(np, X, Y, pts):
    ins = np.zeros(X.shape, bool)
    n = len(pts)
    for k in range(n):
        ax, ay = pts[k]
        bx, by = pts[(k + 1) % n]
        if ay == by:
            continue
        cond = (Y >= min(ay, by)) & (Y < max(ay, by))
        xc = ax + (Y - ay) * (bx - ax) / (by - ay)
        ins ^= cond & (X < xc)
    return ins


def _poly_sd(np, X, Y, pts):
    """signed distance (negative inside) to a closed polygon"""
    d = _seg_dist(np, X, Y, pts, True)
    return np.where(_inside(np, X, Y, pts), -d, d)


def _gauss(np, a, sigma_px):
    r = max(1, int(3 * sigma_px))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_px) ** 2)
    k /= k.sum()
    pad = np.pad(a, r, mode="edge")
    tmp = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, pad)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, tmp)


def _anchors(points):
    out = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "map_m" and isinstance(v, list) and len(v) >= 2 \
                        and all(isinstance(t, (int, float)) for t in v[:2]):
                    out.append((path, float(v[0]), float(v[1])))
                else:
                    walk(v, path + "/" + k)
        elif isinstance(o, list):
            for v in o:
                walk(v, path)
    walk(points, "")
    return [(x, y) for p, x, y in out if not p.startswith("/interior_area_2")]


def build(stage_key="reitz_eng"):
    import datetime
    import numpy as np
    from PIL import Image

    stages = json.load(open(os.path.join(DATA, "stages.json")))
    st = next(s for s in stages["stages"] if s["key"] == stage_key)
    lat0, lon0 = stages["coordinate_system"]["origin_latlon"]
    cx, cy = st["center_m"]
    b = st["bounds_m"]
    pb = st["play_bounds_m"]
    campus = json.load(open(os.path.join(DATA, "campus.json")))
    url = open(os.path.join(DATA, "tiles", SOURCE_URL_FILE)).read().strip()
    q = dict(kv.split("=", 1) for kv in url.split("?", 1)[1].split("&"))
    minlon, minlat, maxlon, maxlat = (float(v) for v in q["bbox"].split(","))
    raw_path = os.path.join(DATA, "tiles", RAW_NAME)
    dem = np.array(Image.open(raw_path), dtype=np.float64)        # row 0 = north
    H, W = dem.shape
    coslat = math.cos(math.radians(lat0))
    # DEM pixel centres -> map metres
    px_x = ((minlon + (np.arange(W) + 0.5) * (maxlon - minlon) / W) - lon0) * M_PER_DEG_LAT * coslat
    px_y = ((maxlat - (np.arange(H) + 0.5) * (maxlat - minlat) / H) - lat0) * M_PER_DEG_LAT
    # resample onto a 2 m map grid over the stage window (y ascending)
    step = 2.0
    gx = np.arange(b["xmin"], b["xmax"] + 1e-6, step)
    gy = np.arange(b["ymin"], b["ymax"] + 1e-6, step)
    fx = np.interp(gx, px_x, np.arange(W))
    fy = np.interp(gy, px_y[::-1], np.arange(H)[::-1])           # px_y descending
    i0 = np.clip(np.floor(fy).astype(int), 0, H - 2)
    j0 = np.clip(np.floor(fx).astype(int), 0, W - 2)
    ty = (fy - i0)[:, None]
    tx = (fx - j0)[None, :]
    a = dem[i0][:, j0]
    bb = dem[i0][:, j0 + 1]
    c = dem[i0 + 1][:, j0]
    dd = dem[i0 + 1][:, j0 + 1]
    grid = (a * (1 - tx) + bb * tx) * (1 - ty) + (c * (1 - tx) + dd * tx) * ty
    grid = _gauss(np, grid, SMOOTH_SIGMA_M / step)
    X, Y = np.meshgrid(gx, gy)

    # ---- protected zones: distance field (<= 0 inside a zone incl. its margin)
    bld = {bd["id"]: bd for bd in campus["buildings"]}
    ways = {w["id"]: w for w in campus["ways"]}
    dist = np.full(X.shape, np.inf)
    zones_out = []
    for name, (oid, margin) in ZONES.items():
        if oid in bld:
            d = _poly_sd(np, X, Y, [tuple(p) for p in bld[oid]["pts"]]) - margin
        elif oid in ways:
            d = _seg_dist(np, X, Y, [tuple(p) for p in ways[oid]["pts"]], False) - margin
        else:
            print(f"stage_terrain: WARNING zone {name} ({oid}) not in campus.json")
            continue
        dist = np.minimum(dist, d)
        zones_out.append({"name": name, "osm_id": oid, "margin_m": margin})
    points = json.load(open(os.path.join(DATA, "reitz_points.json")))
    anchors = _anchors(points)
    for (ax, ay) in anchors:
        dist = np.minimum(dist, np.hypot(X - ax, Y - ay) - ANCHOR_MARGIN_M)
    dist = np.minimum(dist, np.hypot(X - SPAWN[0], Y - SPAWN[1]) - SPAWN_MARGIN_M)
    n_water = 0
    for ar in campus["areas"]:
        t = ar.get("tags", {})
        if not (t.get("natural") == "water" or t.get("water") or t.get("leisure") == "swimming_pool"):
            continue
        pts = ar.get("pts") or []
        if len(pts) < 3:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < b["xmin"] or min(xs) > b["xmax"] or max(ys) < b["ymin"] or min(ys) > b["ymax"]:
            continue
        dist = np.minimum(dist, _poly_sd(np, X, Y, [tuple(p) for p in pts]) - WATER_MARGIN_M)
        n_water += 1
    edge = np.minimum.reduce([X - pb["xmin"], pb["xmax"] - X, Y - pb["ymin"], pb["ymax"] - Y]) - EDGE_MARGIN_M
    dist = np.minimum(dist, edge)
    s = np.clip(dist / BLEND_M, 0.0, 1.0)
    free = s * s * (3 - 2 * s)                                     # 0 in a zone, 1 beyond the blend
    prot = 1.0 - free

    # ---- local reference through the protected zones, relative relief elsewhere
    wsum = _gauss(np, prot, REF_SIGMA_M / step)
    ref = _gauss(np, prot * grid, REF_SIGMA_M / step)
    gmean = float((prot * grid).sum() / max(prot.sum(), 1e-9))
    ref = np.where(wsum > 1e-3, ref / np.maximum(wsum, 1e-9), gmean)
    rel = (grid - ref) * free
    rel = RELIEF_MAX_M * np.tanh(rel / RELIEF_MAX_M)

    # ---- node grid aligned with the ground tiles; pin nodes of every tile touching a zone
    k0 = math.floor((b["xmin"] - cx - TILE_OFF) / TILE) - 1
    k1 = math.ceil((b["xmax"] - cx - TILE_OFF) / TILE) + 1
    l0 = math.floor((b["ymin"] - cy - TILE_OFF) / TILE) - 1
    l1 = math.ceil((b["ymax"] - cy - TILE_OFF) / TILE) + 1
    nxs = cx + TILE_OFF + np.arange(k0, k1 + 1) * TILE
    nys = cy + TILE_OFF + np.arange(l0, l1 + 1) * TILE
    nx, ny = len(nxs), len(nys)

    def sample(F, xs, ys):
        fi = np.clip((ys - gy[0]) / step, 0, len(gy) - 1.0001)
        fj = np.clip((xs - gx[0]) / step, 0, len(gx) - 1.0001)
        i = fi.astype(int)
        j = fj.astype(int)
        u = fi - i
        v = fj - j
        return (F[i, j] * (1 - v) + F[i, j + 1] * v) * (1 - u) + (F[i + 1, j] * (1 - v) + F[i + 1, j + 1] * v) * u

    NX, NY = np.meshgrid(nxs, nys)
    node = sample(rel, NX.ravel(), NY.ravel()).reshape(ny, nx)
    inside_win = (NX >= b["xmin"]) & (NX <= b["xmax"]) & (NY >= b["ymin"]) & (NY <= b["ymax"])
    # a tile is protected when any 2 m sample in it lies in a zone (dist <= 0): pin its 4 corners
    pin = ~inside_win
    tile_i = np.floor((X - nxs[0]) / TILE).astype(int)
    tile_j = np.floor((Y - nys[0]) / TILE).astype(int)
    zmask = dist <= 0.0
    ti, tj = tile_i[zmask], tile_j[zmask]
    for di in (0, 1):
        for dj in (0, 1):
            ii = np.clip(tj + dj, 0, ny - 1)
            jj = np.clip(ti + di, 0, nx - 1)
            pin[ii, jj] = True
    node[pin] = 0.0
    # slope clamp (Lipschitz projection on the node grid, pinned nodes fixed)
    smax = math.tan(math.radians(MAX_SLOPE_DEG))
    for _ in range(200):
        prev = node.copy()
        for (di, dj) in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            lim = smax * TILE * math.hypot(di, dj)
            nb = np.roll(np.roll(node, di, 0), dj, 1)
            valid = np.ones_like(node, bool)
            if di == 1:
                valid[0, :] = False
            if di == -1:
                valid[-1, :] = False
            if dj == 1:
                valid[:, 0] = False
            if dj == -1:
                valid[:, -1] = False
            node = np.where(valid, np.clip(node, nb - lim, nb + lim), node)
            node[pin] = 0.0
        if np.abs(node - prev).max() < 1e-4:
            break
    # twist limit: a tile's corner twist (h00 + h11 - h10 - h01) is what separates the bilinear height_m from
    # the triangulated ground / road ribbons inside a tile (at most twist / 4); project it under TWIST_MAX_M
    free_n = (~pin).astype(float)
    for _ in range(400):
        tw = node[:-1, :-1] + node[1:, 1:] - node[1:, :-1] - node[:-1, 1:]
        ex = tw - np.clip(tw, -TWIST_MAX_M, TWIST_MAX_M)
        if np.abs(ex).max() < 0.005:
            break
        nf = free_n[:-1, :-1] + free_n[1:, 1:] + free_n[1:, :-1] + free_n[:-1, 1:]
        e = np.where(nf > 0, ex / np.maximum(nf, 1), 0.0) * 0.9
        delta = np.zeros_like(node)
        cnt = np.zeros_like(node)
        delta[:-1, :-1] -= e
        delta[1:, 1:] -= e
        delta[1:, :-1] += e
        delta[:-1, 1:] += e
        for sl in ((slice(None, -1), slice(None, -1)), (slice(1, None), slice(1, None)),
                   (slice(1, None), slice(None, -1)), (slice(None, -1), slice(1, None))):
            cnt[sl] += (ex != 0)
        node = node + np.where(cnt > 0, delta / np.maximum(cnt, 1), 0.0) * free_n
        node[pin] = 0.0
    tw = node[:-1, :-1] + node[1:, 1:] - node[1:, :-1] - node[:-1, 1:]
    twist_max = float(np.abs(tw).max())
    heights_cm = np.round(node * 100).astype(int)

    slope = 0.0
    for di, dj in ((0, 1), (1, 0)):
        dh = np.abs(np.diff(node, axis=di)) / TILE
        slope = max(slope, float(dh.max()))
    raw_in = grid
    out = {
        "schema": "sgl64.stage_elevation/1",
        "stage": stage_key,
        "generated_by": "tools/campus/stage_terrain.py build " + stage_key,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "provenance": {
            "source": "USGS 3D Elevation Program (3DEP) bare-earth DEM, 3DEPElevation ImageServer",
            "license": "Public domain (U.S. Geological Survey); no copyright restrictions",
            "url": url,
            "retrieved": "",
            "raw_file": "data/uf/tiles/" + RAW_NAME + " (gitignored; F32 GeoTIFF %dx%d, EPSG:4326)" % (W, H),
            "raw_elevation_m": [round(float(dem.min()), 2), round(float(dem.max()), 2)],
            "window_elevation_m_smoothed": [round(float(raw_in.min()), 2), round(float(raw_in.max()), 2)],
            "projection": "osm_extract.to_local: x = (lon - lon0) * 111320 * cos(lat0), y = (lat - lat0) * 111320",
        },
        "method": {
            "smooth_sigma_m": SMOOTH_SIGMA_M, "reference_sigma_m": REF_SIGMA_M, "blend_m": BLEND_M,
            "relief_max_m": RELIEF_MAX_M, "max_slope_deg": MAX_SLOPE_DEG,
            "protected": zones_out + [
                {"name": "reitz_points anchors (area 1)", "count": len(anchors), "margin_m": ANCHOR_MARGIN_M},
                {"name": "spawn / hub-door warp", "map_m": list(SPAWN), "margin_m": SPAWN_MARGIN_M},
                {"name": "ponds", "count": n_water, "margin_m": WATER_MARGIN_M},
                {"name": "play-zone edge", "margin_m": EDGE_MARGIN_M}],
            "note": "relative relief = smoothed DEM minus a normalised-convolution reference through the "
                    "protected zones; every 20.48 m ground tile touching a zone is pinned to 0",
        },
        "stats": {"min_m": round(float(node.min()), 2), "max_m": round(float(node.max()), 2),
                  "max_slope_deg": round(math.degrees(math.atan(slope)), 1),
                  "pinned_nodes": int(pin.sum()), "nodes": int(nx * ny), "max_tile_twist_m": round(twist_max, 3)},
        "grid": {"x0_m": round(float(nxs[0]), 3), "y0_m": round(float(nys[0]), 3), "step_m": TILE,
                 "nx": nx, "ny": ny, "rows": "heights_cm[j][i] at (x0 + i*step, y0 + j*step), y north",
                 "heights_cm": heights_cm.tolist()},
    }
    path = os.path.join(DATA, f"elevation_{stage_key}.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print("stage_terrain:", path, out["stats"])
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        build(sys.argv[2] if len(sys.argv) > 2 else "reitz_eng")
    else:
        print(__doc__)
