"""Landmark modules (tools/campus/landmarks/<slug>.py, see landmarks/_common.py for the contract),
fallback models used when no module replaces a landmark (Century Tower, the Turlington rock, small
plaza props), and the stage-door markers."""
import glob
import importlib
import math
import os
import sys
import traceback

import bpy
from mathutils import Matrix

import stage_buildings as SB
import stage_geom as G
from stage_nature import blob, ring, trunk

HERE = os.path.dirname(os.path.abspath(__file__))

# Stage doors (docs/game_design.md section 2.1). facing = compass direction the door faces.
# "door": pick this door of the landmark module by name instead of the module's primary door.
DOOR_DEFAULTS = [
    {"slug": "university_auditorium", "osm_id": "w154223635", "facing": 0, "label": "UNIVERSITY AUDITORIUM",
     "stage": "THE SWAMP", "stars": 0},
    {"slug": "the_hub", "osm_id": "w150926632", "facing": 225, "label": "THE HUB",
     "stage": "REITZ UNION + ENGINEERING", "stars": 2},
    {"slug": "marston", "osm_id": "w150860048", "facing": 90, "label": "MARSTON SCIENCE LIBRARY",
     "stage": "MARSTON (INSIDE)", "stars": 5},
    # the module's primary (west) door is a made-up door 4 m from the back of the UF Information
    # building (w858697956); the real, historic main entry on the east facade faces the open lawn
    {"slug": "newell_hall", "osm_id": "w150926630", "facing": 90, "label": "NEWELL HALL",
     "stage": "LAKE ALICE", "stars": 8, "door": "DOOR_newell_hall_1"},
    {"slug": "library_west", "osm_id": "r12122775/196848215", "facing": 180, "label": "LIBRARY WEST",
     "stage": "LIBRARY WEST AFTER DARK", "stars": 14},
    {"slug": "century_tower", "osm_id": "w150860043", "facing": 0, "label": "CENTURY TOWER",
     "stage": "CENTURY TOWER (INSIDE)", "stars": 20},
    {"slug": "smathers", "osm_id": "w154223625", "facing": 270, "label": "SMATHERS LIBRARY",
     "stage": "SMATHERS STACKS SLIDE", "stars": 3},
    # second stage door of a landmark (game_design.md 4.x: star-door-style FINAL EXAM door at the
    # Century Tower base -> Finals Week Ascent); only used when the module provides that door
    {"slug": "final_exam", "osm_id": "w150860043", "facing": 270, "label": "FINAL EXAM",
     "stage": "FINALS WEEK ASCENT", "stars": 30, "door": "DOOR_century_tower_2", "module_only": True},
]

DECAL_BELOW_M = 0.015  # decal parts (walk ribbons) end up 1.5 cm under the collision floor
POI_IDS = ("n4741925737", "n1637323042", "n8045866345", "n5145535993", "n5623470779")


# ------------------------------------------------------------------ landmark modules
def entry_stages(e):
    """Stage keys a LANDMARKS entry is built into (contract key "stages", default ["hub"])."""
    st = e.get("stages", ["hub"])
    if isinstance(st, str):
        st = [st]
    return [str(s) for s in st]


def load_modules(S, strict=False):
    """Import every landmarks/<slug>.py (not starting with '_') and run build(ctx). Successful
    modules' osm_ids are added to S.replaced_ids; a failing module is reported and skipped (its
    buildings fall back to generic extrusions) unless strict.
    Per-stage filtering (contract key "stages", default ["hub"]): only entries listing the stage being
    built (S.key) count; a module with no such entry is skipped without calling build(), and the parts
    of a mixed module's other entries are dropped."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    lm_dir = os.path.join(HERE, "landmarks")
    import json
    campus = json.load(open(os.path.join(S.root, "data", "uf", "campus.json")))
    from landmarks._common import PALETTE
    stage_key = getattr(S, "key", None) or S.data["stage"].get("key", "hub")
    ctx = {"campus": campus, "stage": S.data["stage"], "stage_key": stage_key, "ground_z": lambda x, y: 0.0,
           "buildings": {b["id"]: b for b in campus["buildings"]}, "palette": PALETTE}
    S.landmark_report = []
    for path in sorted(glob.glob(os.path.join(lm_dir, "*.py"))):
        base = os.path.basename(path)[:-3]
        if base.startswith("_"):
            continue
        rep = {"module": base, "ok": False}
        S.landmark_report.append(rep)
        try:
            modname = "landmarks." + base
            if modname in sys.modules:
                mod = importlib.reload(sys.modules[modname])
            else:
                mod = importlib.import_module(modname)
            all_entries = list(getattr(mod, "LANDMARKS"))
            for e in all_entries:
                for k in ("slug", "name", "osm_ids", "center_m"):
                    if k not in e:
                        raise ValueError(f"LANDMARKS entry {e.get('slug')!r} has no {k!r}")
            entries = [e for e in all_entries if stage_key in entry_stages(e)]
            other = {e["slug"] for e in all_entries if stage_key not in entry_stages(e)}
            if not entries:
                rep.update(ok=True, skipped=True, slugs=[], parts=0,
                           reason=f"no LANDMARKS entry lists stage {stage_key!r} "
                                  f"(stages: {sorted({s for e in all_entries for s in entry_stages(e)})})")
                print(f"SGL: landmark module {base}: skipped for stage {stage_key!r} ({rep['reason']})")
                continue
            parts = mod.build(ctx)
            slugs = sorted((e["slug"] for e in all_entries), key=len, reverse=True)
            if other:
                kept = [p for p in parts if part_slug(p, slugs) not in other]
                rep["parts_dropped_other_stages"] = len(parts) - len(kept)
                print(f"SGL: landmark module {base}: {len(parts) - len(kept)} parts of {sorted(other)} "
                      f"dropped (not for stage {stage_key!r})")
                parts = kept
            objs = [add_part(S, base, p, part_slug(p, slugs)) for p in parts]
        except Exception as ex:  # noqa: BLE001 - report and fall back
            rep["error"] = f"{type(ex).__name__}: {ex}"
            print(f"SGL WARNING: landmark module {base} failed, using generic buildings instead:\n"
                  + traceback.format_exc())
            if strict:
                raise
            # remove anything it managed to add
            S.landmark_objects = [o for o in S.landmark_objects if o.get("sgl_landmark") != base]
            for o in [o for o in bpy.data.objects if o.get("sgl_landmark") == base]:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        rep.update(ok=True, slugs=[e["slug"] for e in entries], parts=len(objs),
                   collision_tris=sum(G.tris_of(o) for o in objs if not o.ignore_collision),
                   visual_tris=sum(G.tris_of(o) for o in objs if not o.ignore_render))
        for e in entries:
            S.replaced_ids.update(e["osm_ids"])
            S.replaced_ways.update(e.get("replaces_ways", []))
            S.replaced_areas.update(e.get("replaces_areas", []))
            S.removed_points.update(e.get("removes_points", []))
            S.landmark_entries.append(dict(e, module=base))
        budget = {lm["osm_id"]: lm for lm in S.data["stage"].get("landmarks", [])}
        ids = [i for e in entries for i in list(e["osm_ids"]) + list(e.get("osm_area_ids", []))]
        allowed = sum(budget[i]["collision_tris"] for i in ids if i in budget)
        allowed_v = sum(budget[i]["visual_tris"] for i in ids if i in budget)
        if allowed and rep["collision_tris"] > allowed * 1.1:
            print(f"SGL WARNING: landmark module {base}: {rep['collision_tris']} collision tris > budget {allowed}")
        # per landmark (slug): built tris vs the stages.json budget of the OSM ids it replaces
        per = {}
        for o in objs:
            r = per.setdefault(o["sgl_slug"], {"collision_tris": 0, "visual_tris": 0})
            r["collision_tris" if not o.ignore_collision else "visual_tris"] += G.tris_of(o)
        for e in entries:
            r = per.setdefault(e["slug"], {"collision_tris": 0, "visual_tris": 0})
            ids = list(e["osm_ids"]) + list(e.get("osm_area_ids", []))
            r["budget_collision"] = sum(budget[i]["collision_tris"] for i in ids if i in budget) or None
            r["budget_visual"] = sum(budget[i]["visual_tris"] for i in ids if i in budget) or None
        rep.update(budget_collision=allowed or None, budget_visual=allowed_v or None, per_landmark=per)
        print(f"SGL: landmark module {base}: {len(objs)} parts, {rep['collision_tris']} collision / "
              f"{rep['visual_tris']} visual tris (budget {allowed} / {allowed_v}), "
              f"replaces {sorted(i for e in entries for i in e['osm_ids'])}")


def part_slug(part, slugs):
    """Landmark slug a part belongs to: its "landmark" key, else the longest slug its name starts with."""
    if part.get("landmark") in slugs:
        return part["landmark"]
    n = part["name"].lower().replace(" ", "_").replace(".", "_")
    return next((s for s in slugs if n.startswith(s)), slugs[-1] if len(slugs) == 1 else "?")


def add_part(S, module, part, slug="?"):
    me = part["mesh"]
    slots = list(part["material_slots"])
    for s in slots:
        if s not in S.mats:
            raise ValueError(f"part {part['name']!r}: unknown material {s!r}")
    me.transform(Matrix.Translation((-S.cx, -S.cy, 0.0)))
    if part.get("decal") and not part["collision"]:
        # decal layers (walk ribbons, paving) authored just ABOVE the ground would hide Mario's shadow
        # (drawn at the collision floor, z = 0): move them just under it, still above every
        # generator ground layer (stage_ground.Z, top -0.03 m)
        zs = [v.co.z for v in me.vertices]
        if zs and max(zs) > -DECAL_BELOW_M and max(zs) < 0.25:
            dz = -DECAL_BELOW_M - max(zs)
            me.transform(Matrix.Translation((0.0, 0.0, dz)))
            print(f"SGL: {part['name']}: decal part moved {dz * 100:+.1f} cm to sit under the collision floor")
    if part["visual"]:
        # thin ground pads a few cm ABOVE the floor (e.g. paving inside a bench ring) also hide the
        # shadow: snap the vertices of such up-facing faces to just under the collision floor
        snap = set()
        for p in me.polygons:
            zs = [me.vertices[i].co.z for i in p.vertices]
            if p.normal.z > 0.9 and 0.004 < max(zs) <= 0.06 and min(zs) > -0.004:
                snap.update(p.vertices)
        for i in snap:
            me.vertices[i].co.z = -DECAL_BELOW_M
        if snap:
            me.update()
            print(f"SGL: {part['name']}: {len(snap)} ground-pad vertices moved under the collision floor")
    if not part["visual"]:
        # collision-only: UVs are never drawn, and splitting faces would only add collision triangles
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        idx = [p.material_index for p in me.polygons]
        me.materials.clear()
        for s in slots:
            me.materials.append(S.mats[s])
        me.polygons.foreach_set("material_index", idx)
        me.update()
        return _link_part(S, module, part, me, slug)
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers[0].data
        for poly in me.polygons:
            pts = [tuple(me.vertices[me.loops[li].vertex_index].co) for li in poly.loop_indices]
            mat = slots[poly.material_index] if poly.material_index < len(slots) else slots[0]
            uvs = G.planar_uvs(pts, S.tiles.get(mat, 2.0))
            for li, uv in zip(poly.loop_indices, G.shift_uvs(uvs)):
                uvl[li].uv = uv
    else:
        uvl = me.uv_layers.active.data
        for poly in me.polygons:
            uvs = G.shift_uvs([tuple(uvl[li].uv) for li in poly.loop_indices])
            for li, uv in zip(poly.loop_indices, uvs):
                uvl[li].uv = uv
    split_big_uv_faces(me, [S.mats[s_] for s_ in slots])
    idx = [p.material_index for p in me.polygons]  # materials.clear() resets every face to slot 0
    me.materials.clear()
    for s in slots:
        me.materials.append(S.mats[s])
    me.polygons.foreach_set("material_index", idx)
    me.update()
    return _link_part(S, module, part, me, slug)


def _link_part(S, module, part, me, slug):
    obj = bpy.data.objects.new(f"LM {part['name']}", me)
    bpy.context.scene.collection.objects.link(obj)
    from fast64.fast64_internal.f3d.f3d_material import addColorAttributesToModel
    addColorAttributesToModel(obj)
    obj.ignore_collision = not part["collision"]
    obj.ignore_render = not part["visual"]
    obj.parent = S.area
    obj["sgl_landmark"] = module
    obj["sgl_slug"] = slug
    S.landmark_objects.append(obj)
    return obj


def uv_limit(mat):
    """Max texture repeats across one face for this material: N64 texture coordinates are s10.5,
    so u * width and v * height must stay under ~1000 texels."""
    try:
        w, h = mat.f3d_mat.tex0.tex.size
    except Exception:  # noqa: BLE001
        w = h = 32
    return 1000.0 / max(w, 1) - 1, 1000.0 / max(h, 1) - 1


def split_big_uv_faces(me, mats, passes=8):
    """Safety net for landmark meshes: bisect faces whose UVs span more repeats than the N64 can
    address (bmesh.bisect_plane interpolates the UVs), then shift each face's UVs near 0."""
    import bmesh
    if not me.uv_layers:
        return 0
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active
    limits = [uv_limit(m) for m in mats] or [(30.0, 30.0)]
    cuts = 0
    for _ in range(passes):
        bad = []
        for f in bm.faces:
            us = [l[uvl].uv for l in f.loops]
            lu, lv = limits[min(f.material_index, len(limits) - 1)]
            if max(u.x for u in us) - min(u.x for u in us) > lu or max(u.y for u in us) - min(u.y for u in us) > lv:
                bad.append(f)
        if not bad:
            break
        for f in bad:
            if not f.is_valid:
                continue
            e = max(f.edges, key=lambda e: e.calc_length())
            d = (e.verts[1].co - e.verts[0].co).normalized()
            c = f.calc_center_median()
            bmesh.ops.bisect_plane(bm, geom=list(f.verts) + list(f.edges) + [f], plane_co=c, plane_no=d)
            cuts += 1
    for f in bm.faces:
        uvs = G.shift_uvs([tuple(l[uvl].uv) for l in f.loops])
        for l, uv in zip(f.loops, uvs):
            l[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    if cuts:
        print(f"SGL: {me.name}: split {cuts} landmark faces whose UVs spanned too many texture repeats")
    return cuts


# ------------------------------------------------------------------ fallbacks
def century_tower(S, b):
    """Correct-height fallback: brick shaft, limestone bands, dark belfry openings, clock faces and a
    copper pyramid spire to 47.9 m."""
    pts = G.ccw([S.T(p) for p in b["pts"]])
    pts = G.dedupe(pts, 0.3)
    H = float(b["h"])
    vis = S.acc("Century Tower (fallback)", collision=False)
    col = S.acc("Buildings collision", render=False)
    z_band, z_bel0, z_bel1, z_corn = H * 0.69, H * 0.71, H * 0.845, H * 0.86
    for a, c in zip(pts, pts[1:] + pts[:1]):
        vis.wall(a, c, -0.15, z_band, "brick_red")
        vis.wall(a, c, z_band, z_bel0, "limestone")
        vis.wall(a, c, z_bel1, z_corn, "limestone")
        col.wall(a, c, 0.0, z_corn, "COL default")
    # belfry: dark arched openings, recessed 0.4 m between limestone piers
    inn = G.inset(pts, 0.4) or pts
    n = len(pts)
    for i in range(n):
        a, c = pts[i], pts[(i + 1) % n]
        ia, ic = inn[i], inn[(i + 1) % n]
        L = math.dist(a, c)
        pier = min(1.2, L * 0.15)
        t = pier / L
        a1 = (a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t)
        c1 = (c[0] - (c[0] - a[0]) * t, c[1] - (c[1] - a[1]) * t)
        ia1 = (ia[0] + (ic[0] - ia[0]) * t, ia[1] + (ic[1] - ia[1]) * t)
        ic1 = (ic[0] - (ic[0] - ia[0]) * t, ic[1] - (ic[1] - ia[1]) * t)
        vis.wall(a, a1, z_bel0, z_bel1, "limestone")
        vis.wall(c1, c, z_bel0, z_bel1, "limestone")
        vis.wall(ia1, ic1, z_bel0, z_bel1, "window_dark", [(0, 0), (2, 0), (2, 3), (0, 3)])
        vis.wall(a1, ia1, z_bel0, z_bel1, "limestone")
        vis.wall(ic1, c1, z_bel0, z_bel1, "limestone")
        vis.poly([(a1[0], a1[1], z_bel0), (c1[0], c1[1], z_bel0), (ic1[0], ic1[1], z_bel0), (ia1[0], ia1[1], z_bel0)],
                 "limestone")
        # clock face (white disc as an octagon, 0.05 m proud) at ~60 % height
        mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        nx, ny = (c[1] - a[1]) / L, -(c[0] - a[0]) / L
        tx, ty = -ny, nx
        zc, rc = H * 0.6, min(1.6, L * 0.2)
        face = []
        for k in range(8):
            ang = 2 * math.pi * k / 8 + math.pi / 8
            face.append((mx + nx * 0.05 + tx * math.cos(ang) * rc, my + ny * 0.05 + ty * math.cos(ang) * rc,
                         zc + math.sin(ang) * rc))
        vis.poly(face, "white_trim")
        vis.poly([(mx + nx * 0.08, my + ny * 0.08, zc), (mx + nx * 0.08 + tx * 0.08, my + ny * 0.08 + ty * 0.08, zc),
                  (mx + nx * 0.08, my + ny * 0.08, zc + rc * 0.8)], "dark_trim")
    # cornice (outset 0.3 m) and the pyramid spire
    out = G.inset(pts, -0.3) or pts
    for a, c in zip(out, out[1:] + out[:1]):
        vis.wall(a, c, z_corn, z_corn + 0.6, "limestone")
    for (a, c), (oa, oc) in zip(zip(pts, pts[1:] + pts[:1]), zip(out, out[1:] + out[:1])):
        vis.poly([(oa[0], oa[1], z_corn), (a[0], a[1], z_corn), (c[0], c[1], z_corn), (oc[0], oc[1], z_corn)],
                 "limestone")  # cornice underside (faces down)
    top = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    zt = z_corn + 0.6
    for a, c in zip(out, out[1:] + out[:1]):
        vis.poly([(a[0], a[1], zt), (c[0], c[1], zt), (top[0], top[1], H - 0.8)], "copper_green")
    for a, c in zip(pts, pts[1:] + pts[:1]):
        col.poly([(a[0], a[1], z_corn), (c[0], c[1], z_corn), (top[0], top[1], H - 0.8)], "COL default")
    trunk(vis, top[0], top[1], 0.12, H - 1.0, H, 4, "copper_green", "finial")
    return {"id": b["id"], "name": "Century Tower", "h": H, "kind": "fallback_tower"}


def potato(S, pt):
    x, y = S.T(pt)
    v = S.acc("Props visual", collision=False)
    c = S.acc("Props collision", render=False)
    rings = [ring(x, y, 1.7, -0.2, 7, 0.4, "potato0", 0.12, ry=1.25),
             ring(x, y, 1.9, 1.1, 7, 0.7, "potato1", 0.18, ry=1.4),
             ring(x, y, 1.2, 2.3, 7, 1.0, "potato2", 0.2, ry=0.9)]
    blob(v, rings, (x + 0.2, y, 2.9), None, "rock")
    blob(c, rings, (x + 0.2, y, 2.9), None, "COL default")


def props(S):
    pois = S.data.get("pois", {})
    v = S.acc("Props visual", collision=False)
    c = S.acc("Props collision", render=False)
    made = []
    gone = S.replaced_ids | S.removed_points
    if "n4741925737" in pois and "n4741925737" not in gone:
        potato(S, pois["n4741925737"]["pt"])
        made.append("The Potato (Turlington rock)")
    p = pois.get("n8045866345")
    if p and "n8045866345" not in gone:  # flagpole north of the Auditorium
        x, y = S.T(p["pt"])
        hgt = p.get("height") or 10.0
        trunk(v, x, y, 0.09, -0.1, hgt, 4, "metal_gray", "flag")
        flag = [(x, y, hgt - 0.3), (x + 1.8, y, hgt - 0.3), (x + 1.8, y, hgt - 1.5), (x, y, hgt - 1.5)]
        v.poly(flag[::-1], "door_marker", [(0, 1), (1, 1), (1, 0), (0, 0)][::-1])  # both sides
        v.poly(flag, "door_marker", [(0, 1), (1, 1), (1, 0), (0, 0)])
        tri = [(x + 0.2 * math.cos(a), y + 0.2 * math.sin(a)) for a in (0, 2.1, 4.2)]
        for a, b in zip(tri, tri[1:] + tri[:1]):
            c.wall(a, b, 0.0, hgt, "COL nocam")
        made.append("flagpole")
    p = pois.get("n1637323042")
    if p and "n1637323042" not in gone:  # "The French Fries" sculpture near Marston
        x, y = S.T(p["pt"])
        hmax = p.get("height") or 9.75
        offs = [(-1.0, -0.6, 1.0), (0.1, -0.9, 0.82), (1.0, -0.3, 0.68), (-0.6, 0.6, 0.9), (0.6, 0.8, 0.75),
                (-1.5, 0.4, 0.6)]
        for k, (dx, dy, f) in enumerate(offs):
            hh = hmax * f
            sq = [(x + dx - .3, y + dy - .3), (x + dx + .3, y + dy - .3), (x + dx + .3, y + dy + .3),
                  (x + dx - .3, y + dy + .3)]
            for a, b in zip(sq, sq[1:] + sq[:1]):
                v.wall(a, b, -0.1, hh, "white_trim")
                c.wall(a, b, 0.0, hh, "COL default")
            v.flat(sq, hh, "door_marker")
            c.flat(sq, hh, "COL default")
        made.append("The French Fries")
    for pid, label, kind in (("n5145535993", "Murphree statue", "statue"), ("n5623470779", "well-head", "well")):
        p = pois.get(pid)
        if not p or pid in gone:
            continue
        x, y = S.T(p["pt"])
        if kind == "statue":
            sq = [(x - .8, y - .8), (x + .8, y - .8), (x + .8, y + .8), (x - .8, y + .8)]
            for a, b in zip(sq, sq[1:] + sq[:1]):
                v.wall(a, b, -0.1, 1.6, "limestone")
                c.wall(a, b, 0.0, 1.6, "COL default")
            v.flat(sq, 1.6, "limestone")
            c.flat(sq, 1.6, "COL default")
            blob(v, [ring(x, y, 0.35, 1.6, 6, 0, "st0", 0.05), ring(x, y, 0.42, 2.6, 6, 0.3, "st1", 0.05),
                     ring(x, y, 0.2, 3.4, 6, 0.1, "st2", 0.05)], (x, y, 3.75), None, "copper_green")
        else:
            oc = [(x + 0.9 * math.cos(2 * math.pi * k / 8), y + 0.9 * math.sin(2 * math.pi * k / 8)) for k in range(8)]
            for a, b in zip(oc, oc[1:] + oc[:1]):
                v.wall(a, b, -0.1, 1.0, "limestone")
                c.wall(a, b, 0.0, 1.0, "COL default")
            v.flat(oc, 1.0, "dark_trim")
            c.flat(oc, 1.0, "COL default")
        made.append(label)
    S.stats["props"] = made


# ------------------------------------------------------------------ doors
def doors(S):
    """Collect the stage doors (DOOR_DEFAULTS: the landmark module's door named by "door", else its
    primary door, else a DOOR_DEFAULTS door placed on the OSM footprint with a door marker on the
    generic / fallback building) plus every other door a module lists (no stage, no sign)."""
    by_osm = {}
    for e in S.landmark_entries:
        for i in e["osm_ids"]:
            by_osm[i] = e
    out = []
    used = set()
    for dd in DOOR_DEFAULTS:
        e = by_osm.get(dd["osm_id"])
        if e and e.get("doors"):
            door = None
            if dd.get("door"):
                door = next((d for d in e["doors"] if d.get("name") == dd["door"]), None)
                if door is None:
                    print(f"SGL WARNING: door {dd['slug']}: module {e['module']} has no door {dd['door']!r}")
            if door is None and dd.get("module_only"):
                continue
            if door is None or id(door) in used:
                door = next((d for d in e["doors"] if d.get("primary") and id(d) not in used), None) \
                    or next((d for d in e["doors"] if id(d) not in used), None)
            if door is not None:
                used.add(id(door))
                x, y, z = door["pos_m"]
                f = float(door.get("facing_deg", dd["facing"]))
                r = float(door.get("recess_m") or 0.0)
                if r:  # pos_m is a recessed door plane: report the door on the facade (collision) plane
                    x += math.sin(math.radians(f)) * r
                    y += math.cos(math.radians(f)) * r
                picked = "door named in DOOR_DEFAULTS" if dd.get("door") == door.get("name") else \
                    ("module primary door" if door.get("primary") else "module's first door")
                note = door.get("note")
                if r:
                    note = f"{note or ''} [generator: moved {r} m out of the recess onto the facade plane]".strip()
                out.append(dict(dd, name=door.get("name") or f"DOOR_{dd['slug']}", map_pos=(x, y, z), facing=f,
                                source=f"landmark module {e['module']} ({picked})", marker=False, sign=True,
                                note=note, module_primary=bool(door.get("primary")),
                                width_m=door.get("width_m")))
                continue
        if dd.get("module_only"):
            continue
        hit = SB.door_on_footprint(S, dd["osm_id"], dd["facing"])
        if hit is None:
            print(f"SGL WARNING: door {dd['slug']}: building {dd['osm_id']} not found")
            continue
        sx, sy, nrm = hit
        facing = math.degrees(math.atan2(nrm[0], nrm[1])) % 360
        marker = dd["osm_id"] not in S.replaced_ids
        if marker:
            SB.door_marker(S, sx, sy, nrm)
        elif e:
            print(f"SGL WARNING: landmark {e['slug']} replaces {dd['osm_id']} but lists no doors; "
                  "using the OSM footprint edge for the door sign")
        out.append(dict(dd, name=f"DOOR_{dd['slug']}", map_pos=(sx + S.cx, sy + S.cy, 0.0),
                        facing=round(facing, 1),
                        source="generator (OSM footprint edge)" if marker else "generator (no door in module)",
                        marker=marker, sign=True, width_m=2.4))
    # the modules' other doors: listed for later (decorative / future), no stage and no sign
    for e in S.landmark_entries:
        for door in e.get("doors", []):
            if id(door) in used:
                continue
            used.add(id(door))
            x, y, z = door["pos_m"]
            out.append({"slug": e["slug"], "osm_id": (e["osm_ids"] or [None])[0], "label": e["name"].upper(),
                        "stage": None, "stars": None, "name": door.get("name") or f"DOOR_{e['slug']}",
                        "map_pos": (x, y, z), "facing": float(door.get("facing_deg", 0.0)),
                        "source": f"landmark module {e['module']} (not a stage door)", "marker": False,
                        "sign": False, "note": door.get("note"), "module_primary": bool(door.get("primary"))})
    S.doors = out
    return out


# ------------------------------------------------------------------ landmark vs generator content
def resolve_conflicts(S):
    """Drop / shrink generator content that a landmark module's own geometry covers (modules may
    build outside their OSM footprints: arcades, terraces, colonnades, porches):
      - OSM trees whose trunk stands under a landmark roof / slab (> 1.2 m), or < 0.8 m from a wall
      - other trees: crown radius limited by the distance to landmark walls (as for OSM footprints)
      - props (POIs) and fountains with landmark geometry over them (the module models them)
      - walls / fences / hedges that run under a landmark roof (an arcade, a breezeway)
    Generic buildings overlapped by landmark geometry are only reported."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    rep = {"trees_removed": [], "trees_shrunk": 0, "pois_removed": [], "barriers_removed": [],
           "fountains_removed": [], "buildings_overlapped": []}
    if not S.landmark_objects:
        return rep
    bpy.context.view_layer.update()
    verts, polys = [], []
    for o in S.landmark_objects:
        mw = o.matrix_world
        base = len(verts)
        verts.extend(mw @ v.co for v in o.data.vertices)
        polys.extend([base + i for i in p.vertices] for p in o.data.polygons)
    bvh = BVHTree.FromPolygons(verts, polys)
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    box = (min(xs) - 14, min(ys) - 14, max(xs) + 14, max(ys) + 14)
    down = Vector((0.0, 0.0, -1.0))

    def top(x, y):
        hit = bvh.ray_cast(Vector((x, y, 150.0)), down, 300.0)
        return None if hit[0] is None else hit[0].z

    def covered(x, y, zmin, r=0.0):
        pts = [(x, y)] + ([(x + r, y), (x - r, y), (x, y + r), (x, y - r)] if r else [])
        return any((top(px, py) or -1.0) > zmin for px, py in pts)

    def wall_dist(x, y, zs, reach=12.0):
        best = reach
        for z in zs:
            for k in range(12):
                a = k * math.pi / 6
                hit = bvh.ray_cast(Vector((x, y, z)), Vector((math.cos(a), math.sin(a), 0.0)), reach)
                if hit[0] is not None:
                    best = min(best, hit[3])
        return best

    def near(x, y):
        return box[0] < x < box[2] and box[1] < y < box[3]

    for t in S.data["trees"]:
        if t["id"] in S.removed_points or t["id"] in S.replaced_ids:
            continue
        x, y = S.T(t["pt"])
        if not near(x, y):
            continue
        if covered(x, y, 1.2, 0.4):
            S.removed_points.add(t["id"])
            rep["trees_removed"].append(t["id"])
            continue
        if wall_dist(x, y, (0.8, 2.0), 1.0) < 0.8:   # trunk against a landmark wall
            S.removed_points.add(t["id"])
            rep["trees_removed"].append(t["id"])
            continue
        d = wall_dist(x, y, (5.0, 8.0, 11.0))         # crown height (4.5-6 m up): only buildings matter
        if d < t["clear"] and d < 9.0:                # (crown radius is at most ~7.5 m + 1.5 m)
            t["clear"] = round(d, 2)
            rep["trees_shrunk"] += 1
    for pid, p in S.data.get("pois", {}).items():
        if pid in S.replaced_ids or pid in S.removed_points:
            continue
        x, y = S.T(p["pt"])
        if near(x, y) and covered(x, y, 0.3, 0.3):
            S.removed_points.add(pid)
            rep["pois_removed"].append(pid)
    for b in S.data["barriers"]:
        if b["id"] in S.replaced_ways:
            continue
        pts = [S.T(q) for q in b["pts"]]
        hit = False
        for a, c in zip(pts, pts[1:]):
            n = max(1, math.ceil(math.dist(a, c) / 1.5))
            for k in range(n + 1):
                px, py = a[0] + (c[0] - a[0]) * k / n, a[1] + (c[1] - a[1]) * k / n
                if near(px, py) and covered(px, py, 1.6):
                    hit = True
                    break
            if hit:
                break
        if hit:
            S.replaced_ways.add(b["id"])
            rep["barriers_removed"].append(b["id"])
    for f in S.data.get("fountains", []):
        ring = [S.T(q) for q in f["ring"]]
        cx = sum(q[0] for q in ring) / len(ring)
        cy = sum(q[1] for q in ring) / len(ring)
        if near(cx, cy) and covered(cx, cy, 0.3):
            S.replaced_areas.add(f["id"])
            rep["fountains_removed"].append(f["id"])
    for b in S.data["buildings"]:
        if b["id"] in S.replaced_ids or not b.get("in_window"):
            continue
        pts = [S.T(q) for q in b["pts"]]
        inn = G.inset(G.ccw(pts), 0.6)
        if not inn:
            continue
        hits = sum(1 for (px, py) in inn if near(px, py) and covered(px, py, 1.2))
        if hits:
            rep["buildings_overlapped"].append({"id": b["id"], "name": b.get("name"), "corners_under_landmark": hits,
                                                "corners": len(inn)})
    # visual floors a few cm above the collision floor hide Mario's shadow (see _common.py)
    rep["shadow_hiding_faces"] = {}
    for o in S.landmark_objects:
        if o.ignore_render:
            continue
        n = sum(1 for p in o.data.polygons if p.normal.z > 0.9 and
                0.004 < max(o.data.vertices[i].co.z for i in p.vertices) < 0.12)
        if n:
            rep["shadow_hiding_faces"][o.name] = n
    if rep["shadow_hiding_faces"]:
        print(f"SGL WARNING: landmark floors 0.4-12 cm above the collision floor (Mario's shadow hides under "
              f"them): {rep['shadow_hiding_faces']}")
    print(f"SGL: landmark conflicts: {len(rep['trees_removed'])} trees removed, {rep['trees_shrunk']} crowns "
          f"shrunk, props removed {rep['pois_removed']}, barriers removed {rep['barriers_removed']}, "
          f"fountains removed {rep['fountains_removed']}, generic buildings under landmark geometry "
          f"{[(o['id'], o['name']) for o in rep['buildings_overlapped']]}")
    S.stats["landmark_conflicts"] = rep
    return rep
