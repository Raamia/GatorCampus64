"""Body surgery on the template's "Mario Mesh": outfit recolour/remap driven by
character.json, shoe soles, and outfit accessories built as small low-poly
pieces rigidly weighted to existing bones (so every Mario animation still works).
"""
import json
import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import sgl_characters
import sgl_materials as smat
from sgl_heads import BoneFrame, Geo, emit
from sgl_preview import PREVIEW_ACTION

REST_ACTION = "REST POSE (EXPORT WITH THIS)"
ARMS = ("Left", "Right")


def dominant_groups(obj):
    me = obj.data
    names = {g.index: g.name for g in obj.vertex_groups}
    vg = []
    for v in me.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        vg.append(names.get(best.group) if best else None)
    out = []
    for p in me.polygons:
        counts = {}
        for i in p.vertices:
            counts[vg[i]] = counts.get(vg[i], 0) + 1
        out.append(max(counts, key=counts.get))
    return out


def remap_body(obj, spec, mats):
    """Outfit material remap on the body mesh (Mario Mesh)."""
    build = spec.get("build", {})
    sleeves = build.get("sleeves", "long")
    legwear = build.get("legwear", "long_pants")
    me = obj.data
    groups = dominant_groups(obj)
    slot = {}

    def idx(role):
        if role not in slot:
            slot[role] = smat.ensure_slot(obj, mats[role])
        return slot[role]

    changed = {}
    for p, g in zip(me.polygons, groups):
        m = me.materials[p.material_index].name if me.materials[p.material_index] else ""
        role = None
        if g == "Torso" and m in ("Pants (PANTS)", "Buttons (PANTS)", "Shirt (SHIRT)"):
            role = "top"  # the top covers the whole torso (no overall bib/buttons)
        elif m == "Buttons (PANTS)":
            role = "pants"
        elif g and g.endswith("Forearm") and m == "Shirt (SHIRT)" and sleeves == "short":
            role = "skin"
        elif g and g.endswith("Leg") and m == "Pants (PANTS)" and legwear == "shorts":
            role = "skin"
        elif m == "Logo (EMBLEM)":
            role = "cap"
        if role is not None:
            p.material_index = idx(role)
            changed[f"{g}:{m}->{role}"] = changed.get(f"{g}:{m}->{role}", 0) + 1
    return changed


# ------------------------------------------------------------------ limb bands
def cut_faces(obj, face_ids, planes, snap=1e-5):
    """Bisect the faces face_ids of obj with planes [(co, no)] (mesh-local). Pieces of
    a cut face stay tagged; returns the indices of every tagged face afterwards.
    Vertices within `snap` of a plane count as on it (no sliver cut next to them)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tag = bm.faces.layers.int.new("sgl_cut")
    for i in face_ids:
        bm.faces[i][tag] = 1
    for co, no in planes:
        faces = [f for f in bm.faces if f[tag]]
        edges = list({e for f in faces for e in f.edges})
        verts = list({v for f in faces for v in f.verts})
        bmesh.ops.bisect_plane(bm, geom=faces + edges + verts, plane_co=co, plane_no=no, dist=snap)
    bm.faces.index_update()
    out = [f.index for f in bm.faces if f[tag]]
    bm.faces.layers.int.remove(tag)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return out


def tri_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def limb_axis(obj, arm, bone_a, bone_b):
    """Mesh-local points of two bone heads (the limb segment from joint a to joint b)."""
    M = obj.matrix_world.inverted() @ arm.matrix_world
    return M @ arm.data.bones[bone_a].head_local, M @ arm.data.bones[bone_b].head_local


def recolour_limb_bands(obj, arm, group, bone_a, bone_b, bands, tag="limb"):
    """Cut the faces of `group` across the limb and recolour bands of it. The limb runs
    along the joint axis bone_a -> bone_b; bands are [(frac_from, frac_to, material)] as
    fractions of the group's extent along that axis (0 = the bone_a end). Returns the
    number of triangles the cuts added."""
    me = obj.data
    groups = dominant_groups(obj)
    ids = [p.index for p, gname in zip(me.polygons, groups) if gname == group]
    if not ids:
        print(f"SGL WARNING: {tag}: no faces in {group}")
        return 0
    a, b = limb_axis(obj, arm, bone_a, bone_b)
    axis = (b - a)
    if axis.length < 1e-6:
        print(f"SGL WARNING: {tag}: zero-length axis {bone_a} -> {bone_b}")
        return 0
    axis.normalize()
    vs = {v for i in ids for v in me.polygons[i].vertices}
    proj = [(me.vertices[i].co - a).dot(axis) for i in vs]
    lo, hi = min(proj), max(proj)
    cuts = sorted({f for f0, f1, _m in bands for f in (f0, f1) if 0.0 < f < 1.0})
    before = tri_count(obj)
    ids = cut_faces(obj, ids, [(a + axis * (lo + (hi - lo) * f), axis) for f in cuts])
    counts = {}
    for i in ids:
        p = me.polygons[i]
        c = sum((me.vertices[v].co for v in p.vertices), Vector()) / len(p.vertices)
        frac = ((c - a).dot(axis) - lo) / (hi - lo)
        for f0, f1, mat in bands:
            if f0 <= frac < f1 or (f1 >= 1.0 and frac >= f0):
                p.material_index = smat.ensure_slot(obj, mat)
                counts[mat.name] = counts.get(mat.name, 0) + 1
                break
    added = tri_count(obj) - before
    print(f"SGL {tag}: {group}: {counts} (cuts {cuts}, +{added} tris)")
    return added


# Short sleeves. The sleeve is Mario's upper arm ("<side> Arm Color"), whose tapered end
# cap reaches past the elbow joint into the top of the forearm: with a bare forearm
# (remap_body) the cap is a shirt-coloured piece INSIDE the skin, and it pokes through
# the forearm as shards whenever the elbow bends (running, punching). The sleeve is cut
# across the upper arm at SLEEVE_END (fraction of the upper arm's extent, shoulder ->
# elbow) and everything past the cut, end cap included, becomes skin: what pokes through
# the forearm is then skin on skin, and the tee sleeve has a real T-shirt length instead
# of reaching the elbow (the length Josh's/Donald's tee was reviewed with; longer cuts,
# 0.75 and 0.82, still let shirt slivers through the forearm at extreme bends).
# A character module overrides it with SHORT_SLEEVE_END (a fraction), or sets it to None
# when it builds its own sleeve end (Anh's jersey cuff band, Cher's rolled cuffs).
SLEEVE_END = 0.66


def short_sleeve_ends(spec, mats, obj, arm):
    if spec.get("build", {}).get("sleeves", "long") != "short":
        return None
    frac = sgl_characters.get(spec, "SHORT_SLEEVE_END", SLEEVE_END)
    if frac is None:
        return "built by the character module"
    tris = 0
    for side in ARMS:
        grp = f"{side} Arm Color"
        if grp not in obj.vertex_groups or f"{side} Forearm" not in arm.data.bones:
            continue
        tris += recolour_limb_bands(obj, arm, grp, grp, f"{side} Forearm", [(frac, 1.0, mats["skin"])],
                                    tag="short sleeve end")
    return {"sleeve_end": frac, "tris_added": tris}


def strip_cap_logos(mats):
    """The M logo on held/thrown caps becomes plain cap colour."""
    logo = bpy.data.materials.get("Logo (EMBLEM)")
    n = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or logo is None or logo.name not in o.data.materials:
            continue
        li = list(o.data.materials).index(logo)
        ci = smat.ensure_slot(o, mats["cap"])
        for p in o.data.polygons:
            if p.material_index == li:
                p.material_index = ci
                n += 1
        smat.compact_material_slots(o)
    return n


def set_action(arm, name):
    act = bpy.data.actions.get(name)
    if act is None:
        return
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    bpy.context.scene.frame_set(0)


def shoe_soles(obj, arm, mats):
    """Faces of the shoes that point down in the standing preview pose -> sole colour."""
    groups = dominant_groups(obj)
    set_action(arm, PREVIEW_ACTION)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    em = ev.to_mesh()
    rot = obj.matrix_world.to_3x3()
    soles = []
    for p, pe, g in zip(obj.data.polygons, em.polygons, groups):
        if g in ("Left Shoe", "Right Shoe DL") and (rot @ pe.normal).normalized().z < -0.55:
            soles.append(p.index)
    ev.to_mesh_clear()
    set_action(arm, REST_ACTION)
    si = smat.ensure_slot(obj, mats["shoe_soles"])
    for i in soles:
        obj.data.polygons[i].material_index = si
    return len(soles)


# ------------------------------------------------------------------ surface sampling
def bone_bvh(obj, arm, bone, groups, exclude_materials=()):
    """BVH of the faces of `groups` in `bone` space (l, f, u)."""
    frame = BoneFrame(obj, arm, bone)
    me = obj.data
    gidx = {obj.vertex_groups[n].index for n in groups if n in obj.vertex_groups}
    keep = {v.index for v in me.vertices if any(g.group in gidx and g.weight > 0.4 for g in v.groups)}
    verts = [frame.from_local(v.co) for v in me.vertices]
    skip = {i for i, m in enumerate(me.materials) if m is not None and m.name in exclude_materials}
    polys = [list(p.vertices) for p in me.polygons
             if p.material_index not in skip and all(i in keep for i in p.vertices)]
    return BVHTree.FromPolygons(verts, polys), frame


def hit_from(bvh, origin, direction, dist=3.0):
    """First hit; the normal is returned facing the ray origin (BVH normals in
    the left-handed bone space come out inverted, so never trust their sign)."""
    d = direction.normalized()
    loc, nor, _i, _d = bvh.ray_cast(origin, d, dist)
    if loc is None:
        return None, None
    if nor.dot(d) > 0:
        nor = -nor
    return loc, nor


def front_hit(bvh, l, u):
    """Torso front surface at (l, u), cast from the front."""
    return hit_from(bvh, Vector((l, 2.0, u)), Vector((0, -1, 0)))


def radial_hit(bvh, theta, u, f0=0.0):
    t = math.radians(theta)
    d = Vector((math.sin(t), math.cos(t), 0))
    return hit_from(bvh, Vector((0, f0, u)) + d * 2.0, -d)


# ------------------------------------------------------------------ accessories
def add_shirt_collar(ctx):
    """Collared button-up shirt: two pointed collar flaps on the upper chest, a
    stand-up band around the neck, a placket strip with buttons."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso"])
    g = Geo()
    # torso top (neck line) height: highest front hit on the centre line
    u_top = None
    for k in range(60):
        u = 0.30 + k * 0.004
        loc, _n = front_hit(bvh, 0.0, u)
        if loc is not None:
            u_top = u
    if u_top is None:
        print("SGL WARNING: shirt_collar: torso surface not found")
        return 0
    detail = "top_detail" if ctx["spec"]["colors"].get("top_detail") else "top"

    def on(l, u, off):
        loc, n = front_hit(bvh, l, u)
        if loc is None:
            return None
        return loc + n * off

    tris = 0
    # collar flaps
    for side in (-1, 1):
        pts = {
            "neck": (0.035 * side, u_top - 0.01),
            "outer": (0.19 * side, u_top - 0.035),
            "low": (0.17 * side, u_top - 0.11),
            "tip": (0.03 * side, u_top - 0.155),
        }
        outer_ring = []
        inner_ring = []
        for key in ("neck", "outer", "low", "tip"):
            l, u = pts[key]
            o = on(l, u, 0.035)
            i = on(l, u, -0.004)
            if o is None or i is None:
                break
            outer_ring.append(g.v(o))
            inner_ring.append(g.v(i))
        if len(outer_ring) != 4:
            continue
        g.face(outer_ring, "top", Vector((0, 1, 0.2)))
        for a in range(4):
            b = (a + 1) % 4
            quad = [outer_ring[a], outer_ring[b], inner_ring[b], inner_ring[a]]
            mid = (g.verts[outer_ring[a]] + g.verts[outer_ring[b]]) / 2
            cen = sum((g.verts[x] for x in outer_ring), Vector()) / 4
            g.face(quad, "top", (mid - cen) + Vector((0, 0.3, 0)))
    # neck band: arc around the sides/back of the neck rising above the torso top
    arc = [35, 70, 110, 150, 180, 210, 250, 290, 325]
    low_ids, top_ids = [], []
    for t in arc:
        loc, n = radial_hit(bvh, t, u_top - 0.03)
        if loc is None:
            low_ids = []
            break
        rad = Vector((loc.x, loc.y, 0))
        inward = -rad.normalized()
        low_ids.append(g.v(loc + n * 0.015))
        top_ids.append(g.v(loc + inward * 0.03 + Vector((0, 0, 0.08))))
    # inner side of the band on its own vertices (a reversed face on the same vertices
    # would be refused by bmesh): with backface culling the band is seen from inside
    # when looking down into the collar
    in_low = [g.v(g.verts[i] - Vector((g.verts[i].x, g.verts[i].y, 0)).normalized() * 0.008) for i in low_ids]
    in_top = [g.v(g.verts[i] - Vector((g.verts[i].x, g.verts[i].y, 0)).normalized() * 0.008) for i in top_ids]
    for a in range(len(low_ids) - 1):
        quad = [low_ids[a], low_ids[a + 1], top_ids[a + 1], top_ids[a]]
        mid = (g.verts[low_ids[a]] + g.verts[low_ids[a + 1]]) / 2
        g.face(quad, "top", Vector((mid.x, mid.y, 0)))
        g.face([in_low[a], in_low[a + 1], in_top[a + 1], in_top[a]], "top", -Vector((mid.x, mid.y, 0)))
        # closed top rim
        g.face([top_ids[a], top_ids[a + 1], in_top[a + 1], in_top[a]], "top", Vector((0, 0, 1)))
    # placket + buttons
    u_hi = u_top - 0.16
    u_lo = u_hi - 0.62
    rows = 5
    left, right = [], []
    for r in range(rows + 1):
        u = u_hi + (u_lo - u_hi) * r / rows
        a = on(-0.03, u, 0.012)
        b = on(0.03, u, 0.012)
        if a is None or b is None:
            break
        left.append(g.v(a))
        right.append(g.v(b))
    for r in range(len(left) - 1):
        g.face([left[r], right[r], right[r + 1], left[r + 1]], detail, Vector((0, 1, 0)))
    for k in range(3):
        u = u_hi - 0.08 - k * 0.19
        s = 0.022
        quad = [on(-s, u + s, 0.02), on(s, u + s, 0.02), on(s, u - s, 0.02), on(-s, u - s, 0.02)]
        if any(q is None for q in quad):
            continue
        g.face([g.v(q) for q in quad], "button", Vector((0, 1, 0)))
    roles = {r: mats[r] for r in ("top", "top_detail", "button")}
    emit(g, obj, "Torso", frame, roles)
    return g.tri_count()


def add_rolled_cuffs(ctx):
    """Short rolled sleeves: a turned-up cuff band at the end of each upper arm."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    tris = 0
    for side in ARMS:
        grp = f"{side} Arm Color"
        if grp not in obj.vertex_groups:
            continue
        bvh, frame = bone_bvh(obj, arm, grp, [grp])
        fore = arm.data.bones.get(f"{side} Forearm")
        b = arm.data.bones[grp]
        length = (fore.head_local - b.head_local).length if fore else 0.3
        g = Geo()
        n = 8
        rings = []
        for u, push in ((length * 0.62, 0.028), (length * 0.97, 0.03)):
            ring = []
            for k in range(n):
                t = 360.0 * k / n
                loc, nor = radial_hit(bvh, t, u)
                if loc is None:
                    ring = []
                    break
                rad = Vector((loc.x, loc.y, 0)).normalized()
                ring.append(g.v(loc + rad * push))
            if not ring:
                break
            rings.append(ring)
        if len(rings) != 2:
            print(f"SGL WARNING: cuff on {grp}: arm surface not found")
            continue
        lo, hi = rings
        # inner lip (tucks back into the arm) at both ends
        lip_lo = [g.v(g.verts[i] * Vector((0.86, 0.86, 1.0))) for i in lo]
        lip_hi = [g.v(g.verts[i] * Vector((0.86, 0.86, 1.0)) + Vector((0, 0, 0.0))) for i in hi]
        for k in range(n):
            j = (k + 1) % n
            mid = (g.verts[lo[k]] + g.verts[lo[j]]) / 2
            out = Vector((mid.x, mid.y, 0))
            g.face([lo[k], lo[j], hi[j], hi[k]], "top_detail", out)
            g.face([hi[k], hi[j], lip_hi[j], lip_hi[k]], "top_detail", Vector((0, 0, 1)) + out * 0.2)
            g.face([lo[j], lo[k], lip_lo[k], lip_lo[j]], "top_detail", Vector((0, 0, -1)) + out * 0.2)
        emit(g, obj, grp, frame, {"top_detail": mats["top_detail"]})
        tris += g.tri_count()
    return tris


def _ring_hit(bvh, theta, u, f0=0.0):
    """Torso surface point + outward horizontal normal at angle theta (0 = front,
    90 = character's left) and height u."""
    loc, _n = radial_hit(bvh, theta, u, f0)
    if loc is None:
        return None, None
    rad = Vector((loc.x, loc.y - f0, 0.0))
    return loc, rad.normalized()


def _prism(g, path, radius, role, sides=3, cap_end=True):
    """Thin cord along a polyline (list of Vectors): a `sides`-gon tube, end capped."""
    rings = []
    for k, p in enumerate(path):
        d = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a).normalized()
        rings.append([g.v(p + (a * math.cos(2 * math.pi * j / sides) + b * math.sin(2 * math.pi * j / sides))
                          * radius) for j in range(sides)])
    for r0, r1, p0, p1 in zip(rings, rings[1:], path, path[1:]):
        mid = (p0 + p1) / 2
        for j in range(sides):
            jn = (j + 1) % sides
            out = (g.verts[r0[j]] + g.verts[r0[jn]]) / 2 - p0
            g.face([r0[j], r0[jn], r1[jn], r1[j]], role, out)
    if cap_end:
        g.face(list(rings[-1]), role, path[-1] - path[-2])


def hoodie_hem(ctx, rib_rows=1):
    """Hip-length hoodie: the pelvis (Butt) faces become top colour, so the hoodie
    hangs over the hips and the jeans start at the thighs; the lowest band of the
    pelvis becomes the darker ribbed hem (top_detail)."""
    obj, mats = ctx["obj"], ctx["mats"]
    me = obj.data
    groups = dominant_groups(obj)
    frame = BoneFrame(obj, ctx["arm"], "Torso")
    butt = [p for p, g in zip(me.polygons, groups) if g == "Butt"]
    if not butt:
        return 0
    zs = {p.index: sum(frame.from_local(me.vertices[i].co).z for i in p.vertices) / len(p.vertices) for p in butt}
    levels = sorted({round(z, 3) for z in zs.values()})
    lo = min(zs.values())
    hi = max(zs.values())
    rib_top = lo + (hi - lo) * 0.28 * rib_rows
    ti = smat.ensure_slot(obj, mats["top"])
    di = smat.ensure_slot(obj, mats["top_detail"])
    n_top = n_rib = 0
    for p in butt:
        if zs[p.index] <= rib_top:
            p.material_index = di
            n_rib += 1
        else:
            p.material_index = ti
            n_top += 1
    print(f"SGL hoodie hem: {n_top} pelvis faces -> top, {n_rib} -> rib (levels {levels[:6]}...)")
    return n_top + n_rib


# default toggles / strap buckle: near-black plastic (photos: #232329 on the buckle), so the
# toggles read as black against a black hoodie and the buckle as a faint rim on the strap
DARK_HARDWARE = "#26252B"


def add_hood_down(ctx):
    """Hoodie with the hood down: a thick rolled collar around the neck (raised at the
    back), the hood lying flat on the upper back, two drawstrings with light toggles
    hanging from the front of the collar, and a hip-length body with a ribbed hem."""
    obj, arm, mats, spec = ctx["obj"], ctx["arm"], ctx["mats"], ctx["spec"]
    pal = mats["_palette"]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso"])
    g = Geo()
    # ---- collar roll: 16 columns around the neck
    cols = 16
    up = Vector((0, 0, 1))
    ring = []
    for k in range(cols):
        t = 360.0 * k / cols
        c = math.cos(math.radians(t))          # 1 front, -1 back
        back = (1 - c) / 2                      # 0 front .. 1 back
        u_b = 0.30 + 0.09 * back               # the neckline dips at the front (room for the chin)
        loc, n = _ring_hit(bvh, t, u_b)
        if loc is None:
            print(f"SGL WARNING: hood_down: torso not found at theta {t}")
            return 0
        thick = 0.045 + 0.06 * back             # bunched hood is bulkier behind the neck
        hgt = 0.05 + 0.09 * back
        prof = [loc - up * 0.035 + n * 0.004,
                loc + n * thick,
                loc + n * (thick * 0.75) + up * hgt,
                loc - n * (0.045 + 0.02 * back) + up * (hgt * 0.95)]
        ring.append([g.v(q) for q in prof])
    for k in range(cols):
        a, b = ring[k], ring[(k + 1) % cols]
        mid = sum((g.verts[i] for i in a + b), Vector()) / 8
        rad = Vector((mid.x, mid.y, 0)).normalized()
        g.face([a[0], b[0], b[1], a[1]], "top", rad - up * 0.4)
        g.face([a[1], b[1], b[2], a[2]], "top", rad + up * 0.4)
        g.face([a[2], b[2], b[3], a[3]], "top_detail", up + rad * 0.2)   # hood opening (lining)
        g.face([a[3], b[3], b[0], a[0]], "top_detail", -rad)             # inner side toward the neck
    # ---- hood lying on the upper back (cast from behind)
    rows = [(0.40, 0.25), (0.31, 0.25), (0.22, 0.205), (0.135, 0.13)]
    tip_u = 0.075
    across = (-1.0, -0.5, 0.0, 0.5, 1.0)
    grid = []
    base = []
    for u, hw in rows:
        row, brow = [], []
        for a in across:
            loc, nor = hit_from(bvh, Vector((a * hw, -2.0, u)), Vector((0, 1, 0)))
            if loc is None:
                print("SGL WARNING: hood_down: back surface not found")
                return 0
            bulge = 0.03 + 0.065 * (1 - abs(a) ** 2)
            row.append(g.v(loc + nor * bulge))
            brow.append(g.v(loc - nor * 0.004))
        grid.append(row)
        base.append(brow)
    loc, nor = hit_from(bvh, Vector((0, -2.0, tip_u)), Vector((0, 1, 0)))
    tip = g.v(loc + nor * 0.02)
    tip_b = g.v(loc - nor * 0.004)
    out_back = Vector((0, -1, 0))
    for r in range(len(rows) - 1):
        for c in range(len(across) - 1):
            g.face([grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]], "top", out_back + up * 0.3)
    last = grid[-1]
    for c in range(len(across) - 1):
        g.face([last[c], last[c + 1], tip], "top", out_back - up * 0.3)
    # centre seam of the hood (darker strip from the collar to the tip)
    seam = []
    for r in range(len(rows)):
        cpt, lft, rgt = (g.verts[grid[r][k]] for k in (2, 1, 3))
        seam.append((g.v(cpt.lerp(lft, 0.11) + out_back * 0.004), g.v(cpt.lerp(rgt, 0.11) + out_back * 0.004)))
    tip_p = g.verts[tip]
    for (a0, b0), (a1, b1) in zip(seam, seam[1:]):
        g.face([a0, b0, b1, a1], "top_detail", out_back)
    g.face([seam[-1][0], seam[-1][1], g.v(tip_p + out_back * 0.004)], "top_detail", out_back)
    # side walls of the hood (outer edge down to the back surface)
    for side in (0, len(across) - 1):
        sgn = -1.0 if side == 0 else 1.0
        edge = [grid[r][side] for r in range(len(rows))] + [tip]
        bed = [base[r][side] for r in range(len(rows))] + [tip_b]
        for e0, e1, b0, b1 in zip(edge, edge[1:], bed, bed[1:]):
            g.face([e0, e1, b1, b0], "top", Vector((sgn, -0.3, 0)))
    # ---- drawstrings with toggles: short dark cords hanging just below the eyelets at
    # the front of the collar (photos 3/4: about 10% of the face height, black toggles)
    for side in (-1, 1):
        l = 0.07 * side
        pts = []
        for u in (0.325, 0.29, 0.255):
            loc, nor = front_hit(bvh, l + 0.005 * side * (0.325 - u) / 0.07, u)
            if loc is None:
                break
            pts.append(loc + nor * 0.022)
        if len(pts) != 3:
            continue
        _prism(g, pts, 0.012, "drawstring", cap_end=False)
        tip_dir = (pts[-1] - pts[-2]).normalized()
        _prism(g, [pts[-1] - tip_dir * 0.005, pts[-1] + tip_dir * 0.03], 0.019, "toggle")
    roles = {"top": mats["top"], "top_detail": mats["top_detail"],
             "drawstring": smat.accessory_material(mats, "drawstring", pal.get("drawstrings", pal["top_detail"])),
             "toggle": smat.accessory_material(mats, "toggle", pal.get("toggles", DARK_HARDWARE))}
    tris = emit(g, obj, "Torso", frame, roles)
    tris += hoodie_hem(ctx)
    return tris


# crossbody bag placement in the Torso frame (l, f, u): raycast point on the right
# side (f, u), gap from the surface to the bag centre (out), half width/height/depth.
# build.bag in character.json overrides single keys. Smaller than the first version and
# higher on the hip, just behind the side seam: over all 209 Mario animations (every 3rd
# frame) fist/forearm/thigh triangles touch it in 36% of the frames and a limb vertex is
# inside it in 16% (63% / 50% for the first placement f -0.10 u -0.20, 0.34 x 0.24 x 0.11). Moving it
# further back (f -0.22) scores about the same but hides it behind the hip from the front.
BAG = {"f": -0.12, "u": -0.13, "out": 0.07, "hw": 0.13, "hh": 0.10, "hd": 0.045}


def add_crossbody_strap(ctx):
    """Crossbody bag: a strap looping from the character's LEFT shoulder across the
    chest and back to the RIGHT hip (a ring around the torso in a tilted plane, laid
    on the surface by raycasts), a slider buckle on the chest and a small bag at the
    right hip. Everything is rigid on the Torso bone."""
    obj, arm, mats = ctx["obj"], ctx["arm"], ctx["mats"]
    pal = mats["_palette"]
    skip = [m.name for m in obj.data.materials if m and m.name.startswith(("Drawstring", "Toggle"))]
    bvh, frame = bone_bvh(obj, arm, "Torso", ["Torso", "Butt"], exclude_materials=skip)
    g = Geo()
    shoulder = Vector((0.21, 0.0, 0.43))   # (l, u) on the left shoulder next to the neck; f unused
    hip = Vector((-0.40, 0.0, -0.22))
    d = Vector((shoulder.x - hip.x, 0.0, shoulder.z - hip.z)).normalized()   # in-plane "up"
    fwd = Vector((0, 1, 0))
    nrm = d.cross(fwd).normalized()          # plane normal (in the l-u plane)
    centre = (shoulder + hip) / 2
    width, lift = 0.085, 0.022
    steps = 28
    edges = []
    for k in range(steps):
        phi = 2 * math.pi * k / steps
        dirv = d * math.cos(phi) + fwd * math.sin(phi)
        pair = []
        for side in (-0.5, 0.5):
            o = centre + nrm * (side * width) + dirv * 2.5
            loc, nor = hit_from(bvh, o, -dirv, 3.0)
            if loc is None:
                pair = None
                break
            pair.append((loc, nor))
        edges.append(pair)
    if any(p is None for p in edges):
        print("SGL WARNING: crossbody_strap: torso not found along the strap")
    pts = []
    for pair in edges:
        if pair is None:
            pts.append(None)
            continue
        (la, na), (lb, nb) = pair
        n = (na + nb).normalized()
        pts.append((g.v(la + n * lift), g.v(lb + n * lift), g.v(la + n * 0.004), g.v(lb + n * 0.004), n))
    for k in range(steps):
        a, b = pts[k], pts[(k + 1) % steps]
        if a is None or b is None:
            continue
        n = (a[4] + b[4]).normalized()
        g.face([a[0], a[1], b[1], b[0]], "strap", n)
        g.face([a[0], b[0], b[2], a[2]], "strap", -nrm)   # edge walls
        g.face([a[1], b[1], b[3], a[3]], "strap", nrm)
    # slider buckle on the chest: a short raised plate on the front run
    k_b = round(steps * 0.17)  # front run, at armpit height (clear of the drawstrings), as in photo 3
    if pts[k_b] is not None and pts[k_b + 1] is not None:
        a, b = pts[k_b], pts[k_b + 1]
        n = (a[4] + b[4]).normalized()
        quad = [g.verts[a[0]], g.verts[a[1]], g.verts[b[1]], g.verts[b[0]]]
        cen = sum(quad, Vector()) / 4
        top = [g.v(cen + (q - cen) * 1.25 + n * 0.018) for q in quad]
        bot = [g.v(cen + (q - cen) * 1.25 + n * 0.002) for q in quad]
        g.face(top, "buckle", n)
        for i in range(4):
            j = (i + 1) % 4
            g.face([top[i], top[j], bot[j], bot[i]], "buckle", (g.verts[top[i]] + g.verts[top[j]]) / 2 - cen)
    # bag at the right hip, behind the side seam (out of the arm swing, see BAG)
    bag = dict(BAG, **ctx["spec"].get("build", {}).get("bag", {}))
    loc, nor = hit_from(bvh, Vector((-2.0, bag["f"], bag["u"])), Vector((1, 0, 0)))
    if loc is not None:
        out = Vector((nor.x, nor.y, 0)).normalized()
        along = out.cross(Vector((0, 0, 1))).normalized()
        upv = Vector((0, 0, 1))
        c = loc + out * bag["out"]
        hw, hh, hd = bag["hw"], bag["hh"], bag["hd"]
        corners = {}
        for i, sa in enumerate((-1, 1)):
            for j, sh in enumerate((-1, 1)):
                for k2, sd in enumerate((-1, 1)):
                    taper = 0.85 if sh > 0 else 1.0
                    corners[(i, j, k2)] = g.v(c + along * (sa * hw * taper) + upv * (sh * hh) + out * (sd * hd))
        V = corners
        g.face([V[0, 0, 1], V[1, 0, 1], V[1, 1, 1], V[0, 1, 1]], "bag", out)
        g.face([V[0, 0, 0], V[0, 1, 0], V[1, 1, 0], V[1, 0, 0]], "bag", -out)
        g.face([V[0, 1, 0], V[0, 1, 1], V[1, 1, 1], V[1, 1, 0]], "bag", upv)
        g.face([V[0, 0, 0], V[1, 0, 0], V[1, 0, 1], V[0, 0, 1]], "bag", -upv)
        g.face([V[0, 0, 0], V[0, 0, 1], V[0, 1, 1], V[0, 1, 0]], "bag", -along)
        g.face([V[1, 0, 0], V[1, 1, 0], V[1, 1, 1], V[1, 0, 1]], "bag", along)
        # zip line / flap seam on the outer face
        z0 = g.v(c + out * (hd + 0.006) + upv * (hh * 0.45) - along * hw * 0.8)
        z1 = g.v(c + out * (hd + 0.006) + upv * (hh * 0.45) + along * hw * 0.8)
        z2 = g.v(c + out * (hd + 0.006) + upv * (hh * 0.30) + along * hw * 0.8)
        z3 = g.v(c + out * (hd + 0.006) + upv * (hh * 0.30) - along * hw * 0.8)
        g.face([z0, z1, z2, z3], "buckle", out)
    else:
        print("SGL WARNING: crossbody_strap: hip not found for the bag")
    roles = {"strap": smat.accessory_material(mats, "strap", pal.get("strap", "#121114")),
             "buckle": smat.accessory_material(mats, "buckle", pal.get("buckle", DARK_HARDWARE)),
             "bag": smat.accessory_material(mats, "bag", pal.get("bag", "#1A191D"))}
    return emit(g, obj, "Torso", frame, roles)


def _todo(name):
    def stub(ctx):
        print(f"SGL TODO: accessory {name!r} is not implemented yet (skipped)")
        return 0
    return stub


ACCESSORIES = {
    "shirt_collar": add_shirt_collar,
    # optional: turned-up cuffs on short sleeves (fights Mario's elbow geometry, off by default)
    "rolled_cuffs": add_rolled_cuffs,
    # TODO: implement when these characters are built
    "hood_down": add_hood_down,
    "crossbody_strap": add_crossbody_strap,
    "suit_lapels_white_shirt_v": _todo("suit_lapels_white_shirt_v"),
    "red_tie": _todo("red_tie"),
    "glasses_thick_rectangular": _todo("glasses_thick_rectangular"),
    "glasses_browline_blue": _todo("glasses_browline_blue"),
    "white_socks": _todo("white_socks"),
    "jersey_stripes": _todo("jersey_stripes"),
    "jersey_number_10_back": _todo("jersey_number_10_back"),
    "thin_chain_necklace": _todo("thin_chain_necklace"),
    "headphones_around_neck": _todo("headphones_around_neck"),
    "stubble": _todo("stubble"),
}


HAND_GROUPS = ("Left Hand DL", "Right Hand DL")


def scale_hands(spec):
    """Bare hands: Mario's glove-sized fists shrunk around the wrist pivot.
    build.hand_scale overrides (1.0 keeps Mario's size)."""
    build = spec.get("build", {})
    gloves = "gloves" in spec.get("colors", {})
    k = float(build.get("hand_scale", 1.0 if gloves else 0.82))
    if abs(k - 1.0) < 1e-6:
        return {}
    done = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent is None or o.parent.type != "ARMATURE":
            continue
        arm = o.parent
        groups = [g for g in HAND_GROUPS if g in o.vertex_groups]
        if not groups and "Hand" in o.name:
            # hand switch-option meshes: scale everything around the option bone
            bone = next((b.name for b in arm.data.bones if b.name in o.vertex_groups), None)
            if bone is None:
                continue
            fr = BoneFrame(o, arm, bone)
            for v in o.data.vertices:
                v.co = fr.to_local(fr.from_local(v.co) * k)
            done[o.name] = len(o.data.vertices)
            continue
        for gname in groups:
            gi = o.vertex_groups[gname].index
            fr = BoneFrame(o, arm, gname)
            n = 0
            for v in o.data.vertices:
                if any(g.group == gi and g.weight > 0.4 for g in v.groups):
                    v.co = fr.to_local(fr.from_local(v.co) * k)
                    n += 1
            done[f"{o.name}:{gname}"] = n
    return done


CUFF_U = 0.06  # glove faces nearer the wrist than this (hand bone frame) form Mario's glove cuff
CUFF_TAPER = 0.8


def sleeve_cuffs(spec, mats):
    """Long sleeves + bare hands: Mario's flared glove cuff would read as a big
    skin-coloured wrist. Its faces become the sleeve's cuff instead (top_detail if
    the spec has one, else top) in every hand mesh and hand switch option, so the
    sleeve ends in a cuff and the bare fist looks smaller. The metal hand switch
    options ("Metal <option>") get the same vertex moves (they stay all Metal), so a
    metal hand keeps its shape when the hand switch changes; the metal body is rebuilt
    from the finished body later (rebuild_metal)."""
    build = spec.get("build", {})
    colors = spec.get("colors", {})
    if build.get("sleeves", "long") != "long" or "gloves" in colors or build.get("cuffs") is False:
        return {}
    cuff = mats["top_detail"] if colors.get("top_detail") else mats["top"]
    gloves = bpy.data.materials["Gloves (GLOVES)"]
    done = {}
    moves = {}  # mesh name -> {bone: [(old bone-frame position, new position)]}
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent is None or o.parent.type != "ARMATURE" or gloves.name not in o.data.materials:
            continue
        arm = o.parent
        me = o.data
        gl = [i for i, m in enumerate(me.materials) if m == gloves]
        hand_groups = [g.name for g in o.vertex_groups if "Hand" in g.name and g.name in arm.data.bones]
        n = 0
        ci = None
        for gname in hand_groups:
            gi = o.vertex_groups[gname].index
            fr = BoneFrame(o, arm, gname)
            vs = {v.index for v in me.vertices if any(g.group == gi and g.weight > 0.4 for g in v.groups)}
            cuff_faces = []
            for p in me.polygons:
                if p.material_index not in gl or not all(i in vs for i in p.vertices):
                    continue
                u = sum(fr.from_local(me.vertices[i].co).z for i in p.vertices) / len(p.vertices)
                if u < CUFF_U:
                    cuff_faces.append(p)
            if not cuff_faces:
                continue
            if ci is None:
                ci = smat.ensure_slot(o, cuff)
            for p in cuff_faces:
                p.material_index = ci
            n += len(cuff_faces)
            # Mario's glove cuff flares out like a funnel; pull the vertices that only
            # the cuff uses toward the wrist axis so it reads as a sleeve cuff
            other = {i for p in me.polygons if p.material_index != ci and all(j in vs for j in p.vertices)
                     for i in p.vertices}
            for i in {i for p in cuff_faces for i in p.vertices} - other:
                q = fr.from_local(me.vertices[i].co)
                nq = Vector((q.x * CUFF_TAPER, q.y * CUFF_TAPER, q.z))
                me.vertices[i].co = fr.to_local(nq)
                moves.setdefault(o.name, {}).setdefault(gname, []).append((q, nq))
        if n:
            done[o.name] = n
    for name, by_bone in moves.items():
        metal = bpy.data.objects.get("Metal " + name)
        if metal is None or metal.type != "MESH" or name == "Mario Mesh":
            continue
        n = _apply_moves(metal, by_bone)
        if n:
            done[metal.name + " (geometry only)"] = n
    return done


def _apply_moves(obj, by_bone, tol=1e-4):
    """Move the vertices of obj that sit at a recorded old position (bone frame of the
    same-named bone of obj's own armature) to the recorded new position."""
    arm = obj.parent
    n = 0
    for bone, pairs in by_bone.items():
        if bone not in arm.data.bones or bone not in obj.vertex_groups:
            continue
        fr = BoneFrame(obj, arm, bone)
        gi = obj.vertex_groups[bone].index
        for v in obj.data.vertices:
            if not any(g.group == gi and g.weight > 0.4 for g in v.groups):
                continue
            q = fr.from_local(v.co)
            hit = next((nq for oq, nq in pairs if (oq - q).length < tol), None)
            if hit is not None:
                v.co = fr.to_local(hit)
                n += 1
    return n


def build_body(spec, mats):
    obj = bpy.data.objects["Mario Mesh"]
    arm = bpy.data.objects["Mario"]
    set_action(arm, REST_ACTION)
    report = {"remap": remap_body(obj, spec, mats)}
    report["sleeve_ends"] = short_sleeve_ends(spec, mats, obj, arm)
    report["soles"] = shoe_soles(obj, arm, mats)
    report["cap_logos"] = strip_cap_logos(mats)
    report["sleeve_cuffs"] = sleeve_cuffs(spec, mats)   # before scaling: CUFF_U is in Mario's hand size
    report["hands_scaled"] = scale_hands(spec)
    ctx = {"obj": obj, "arm": arm, "mats": mats, "spec": spec}
    acc = {}
    build = spec.get("build", {})
    custom = sgl_characters.get(spec, "ACCESSORIES", {})
    for name in build.get("accessories", []):
        fn = custom.get(name) or ACCESSORIES.get(name, _todo(name))
        acc[name] = fn(ctx)
    report["accessories"] = acc
    return report


# ------------------------------------------------------------------ wing-cap wings
# The wing-cap wings (Mario Mesh groups "Left/Right Wing DL") sit at the sides of Mario's
# cap. Big hair buries their roots, so a character module can move them out with
# WING_SHIFT = (l, f, u) in head space (mirrored for the right wing); build_character
# applies it after post_build. The wing BONES move by the same amount, so in the export
# the wing vertices stay where the template has them relative to their bone (root edge on
# the bone's X axis) and geo_mario_rotate_wing_cap_wings still flaps them about their
# root; only the GEO_TRANSLATE_ROTATE offset of the wing node changes.
WING_SIDES = (("Left", 1.0), ("Right", -1.0))
# Mario Mesh custom property: JSON {"<side> Wing DL": {"parent": bone, "delta": armature-space
# move}} written by move_wings, read by sgl_preview.frame_bbox
WING_SHIFT_PROP = "sgl_wing_shift"
WING_ARMATURES = ("Mario", "Metal Mario")  # the metal body is rebuilt from Mario Mesh later


def _wing_bones(side):
    return (f"{side} Wing", f"0 {side} Wing Rotation Function", f"1 {side} Wing Rotation", f"{side} Wing DL")


def _translate_bones(arm, moves):
    """Translate edit bones {name: armature-space vector}. Needs edit mode."""
    if not moves:
        return 0
    vl = bpy.context.view_layer
    prev = vl.objects.active
    hidden, hide_vp = arm.hide_get(), arm.hide_viewport
    arm.hide_viewport = False
    arm.hide_set(False)
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    vl.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        eb = arm.data.edit_bones
        for name, d in moves.items():
            eb[name].translate(d)
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        arm.hide_viewport = hide_vp
        arm.hide_set(hidden)
        vl.objects.active = prev
    return len(moves)


def move_wings(shift):
    """Move both wing-cap wings (vertices + bones) by shift = (l, f, u) in head space,
    mirrored for the right wing."""
    shift = Vector(shift)
    obj, arm = bpy.data.objects["Mario Mesh"], bpy.data.objects["Mario"]
    frame = BoneFrame(obj, arm, "Head DL")
    moved = 0
    shifts = {}
    for side, sgn in WING_SIDES:
        vg = obj.vertex_groups.get(f"{side} Wing DL")
        if vg is None:
            continue
        d = Vector((shift.x * sgn, shift.y, shift.z))
        shifts[side] = d
        for v in obj.data.vertices:
            if any(g.group == vg.index and g.weight > 0.4 for g in v.groups):
                v.co = frame.to_local(frame.from_local(v.co) + d)
                moved += 1
    bones = {}
    frame_info = {}
    for arm_name in WING_ARMATURES:
        a = bpy.data.objects.get(arm_name)
        if a is None or a.type != "ARMATURE" or "Head DL" not in a.data.bones:
            continue
        head3 = a.data.bones["Head DL"].matrix_local.to_3x3()  # bone-local axes = (u, f, l)
        moves = {}
        for side, d in shifts.items():
            dd = head3 @ Vector((d.z, d.y, d.x))
            moves.update({n: dd for n in _wing_bones(side) if n in a.data.bones})
            top = a.data.bones.get(f"{side} Wing")
            if arm_name == "Mario" and top is not None and top.parent is not None:
                frame_info[f"{side} Wing DL"] = {"parent": top.parent.name, "delta": [round(c, 6) for c in dd]}
        bones[arm_name] = _translate_bones(a, moves)
    if moved and bones.get("Mario", 0) != 8:
        raise RuntimeError(f"move_wings: moved {moved} wing vertices but bones {bones} (expected 8 per armature)")
    # the standard previews frame the body as if the (hidden) wings had not moved, so
    # a WING_SHIFT does not change the preview scale (sgl_preview.frame_bbox)
    obj[WING_SHIFT_PROP] = json.dumps(frame_info)
    return {"shift": tuple(round(c, 4) for c in shift), "vertices": moved, "bones": bones}


def rebuild_metal(mats):
    """Metal Mario = the finished body+head geometry with metal materials;
    Metal Capless Head = the finished capless head in metal."""
    pairs = [("Mario Mesh", "Metal Mario Mesh"), ("Capless Head Mesh", "Metal Capless Head Mesh")]
    wing = {mats["wing_base"].name: mats["metal_wing_base"], mats["wing_tip"].name: mats["metal_wing_tip"]}
    for src_name, dst_name in pairs:
        src = bpy.data.objects[src_name]
        dst = bpy.data.objects[dst_name]
        old = dst.data
        new = src.data.copy()
        new.name = dst_name + " Data"
        dst.data = new
        for i, m in enumerate(new.materials):
            new.materials[i] = wing.get(m.name if m else "", mats["metal"])
        src_groups = [g.name for g in src.vertex_groups]
        if [g.name for g in dst.vertex_groups] != src_groups:
            dst.vertex_groups.clear()
            for n in src_groups:
                dst.vertex_groups.new(name=n)
        smat.compact_material_slots(dst)
        if old.users == 0:
            bpy.data.meshes.remove(old)
