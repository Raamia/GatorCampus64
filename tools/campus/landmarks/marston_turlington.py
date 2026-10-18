"""HUB stage landmarks: Marston Science Library, Turlington Hall and "The Potato" (Turlington rock).

Landmark module (contract: tools/campus/landmarks/_common.py). Geometry is in MAP METRES, z up
(x = east, y = north, origin = Century Tower), read from the OSM footprints in data/uf/campus.json
so every model sits on the footprint it replaces:

  Marston Science Library  w150860048 (+ w859919297, the roof over the Marston/CSE court)
                           2,589 m2, 5 floors, towers 22.5 m, wings 16.8 m   budget 250 col / 900 vis
  Turlington Hall          w150684197   5,278 m2, crown 20.0 m               budget 300 col / 1000 vis
  The Potato               n4741925737 (+ w859919293, the round concrete bench)  budget 40 col / 200 vis

References used (read-only)
  - OSM ways/nodes above (tags: Turlington building:levels=5, start 1977, brick, colour #B73239;
    Marston levels=5, start 1987, brick; Potato height=3, weight=10 t, support=pedestal, 1984;
    bench ring material=concrete, colour=white, seats=30; tunnel=building_passage footways and
    entrance nodes through Turlington; covered footway + "roof" over the Marston/CSE court).
  - Wikimedia Commons photos, viewed for massing and materials:
      UF-MarstonScienceLibrary.jpg (2011), Marston_Library.jpg (2005), UF_CSEandMSL_2.jpg (2009),
      CSE_and_Marston.JPG, UF_Marston_Science_Library_Brick_Red..._(4662102094).jpg,
      University_of_Florida_Marston_Science_Library.jpg ("Center of Marston", 2022),
      MarstonLibraryWithSun.jpg, Dsg_UF_Turlington_Hall.jpg, Gville_UF_Turlington_Hall01/02.jpg,
      Gville_UF_GPA_rock01.jpg  (https://commons.wikimedia.org/wiki/Category:Marston_Science_Library)
  - en.wikipedia.org/wiki/University_of_Florida_Marston_Science_Library (1987, next to Turlington,
    the Auditorium and Century Tower); UF CLAS page (Turlington = "General Purpose Building A",
    completed 1977-78); roadsideamerica.com/tip/47260 and UF ELI newsletter (the Potato: ~10 t rock
    donated 1984, potato-shaped).
  - Heights: data/uf/stages.json landmark_heights (Marston 22.5 m, Turlington 20.0 m).

What the photos show and how it is modelled
  Marston (VOA Associates, 1987): red-brick blocks with chamfered corners, blank brick towers with
    dark bronze bands, recessed ribbon windows under deep dark fascias, bronze-clad piers at the
    ground floor, a sloped glass atrium roof in the middle, and a tall court between Marston and
    CSE (the "French Fries" court) covered by a roof structure at the top.
    -> wings/main block 16.8 m (4 floors x 4.2 m) with 3 ribbon-window bands; 4 towers to 22.5 m
       (NE corner, both sides of the CSE court, SW corner; outer corners chamfered down to the
       ground) with bronze bands at 10.8 m and the coping; the north wing facing the
       plaza steps back 1.2 m per floor (ledges at 4.2 / 8.4 / 12.6 m = the "stepped" massing and
       a single-jump climbing face); west colonnade with bronze piers facing Marston Courtyard;
       hipped glass skylight 16.8 -> 21.3 m (27 deg, walkable); court roof slab 15.0-16.2 m that
       replaces the generic 4 m canopy of w859919297; two brick planters in the entry plaza.
  Turlington (1977): two-storey brick podium with porthole windows and a recessed arcade on brick
    piers along the plaza, upper floors set back behind a terrace with ribbon windows, and a big
    dark standing-seam metal "crown" on top that cantilevers over the terrace; an open breezeway
    runs east-west through the ground floor (OSM tunnel=building_passage).
    -> podium 9.0 m on the simplified OSM outline; arcade 4.2 m high x 3 m deep along the diagonal
       plaza facade with 4 piers; breezeway 5.4 m wide x 4.2 m high (walk/run through it);
       terrace ring at 9.0 m; upper floors 9-13 m (inset 3 m); crown 13-20 m over the north block
       (inset 1 m, so it overhangs the terrace by 2 m); low service annex 5.0 m at the NW;
       exterior concrete stair on the north face up to the 9 m terrace; porthole decals.
  The Potato: pale, lumpy, bowling-pin-shaped rock (~2.9 m) with a side lobe on a low round
    pedestal, in a gravel circle ringed by a white concrete bench (OSM w859919293, 7.6 m across).

Traversal (SM64 moves; single jump ~2.2 m apex, ledge grab ~2.4 m above the feet)
  Potato: hop onto the bench ring (0.45 m, steps up), jump to the lobe (1.75 m), then the head
    (2.9 m); a double jump reaches the head directly.
  Turlington: north stair -> 9 m terrace ring (walk all the way around under the crown overhang)
    -> jump-grab the 13 m south-block roof -> triple jump / wall kick to the 20 m crown roof.
    Alternative: double-jump the 5 m annex at the NW, then jump-grab the terrace. Run through the
    breezeway and the arcade.
  Marston: planter (0.9 m) -> north-wing ledges 4.2 / 8.4 / 12.6 m (jump + ledge grab each) ->
    16.8 m roof -> double-jump the 22.5 m towers; slide down the glass skylight; step down onto
    the court roof (16.2 m) toward CSE.

Collision vs visual: both come from the same boolean massing (Blender Exact boolean, evaluated and
  removed again inside build()), so walls line up exactly; the visual mesh only adds horizontal
  material bands, decals (portholes, door), chunky stair steps and the organic rock. Collision is
  closed where Mario can touch it, normals out, no slopes between 10 and 38 degrees except the
  walkable stair ramp and skylight; big roofs are cut into <= 21 m cells and no floor edge is longer
  than 30 m. UVs: "UVMap" (1.0 = one texture repeat of the palette tile_m, every face under ~11
  repeats; ribbon-window bands start on a window_dark pane row; the crown's roof_dark is turned 90
  degrees so its rows read as vertical standing seams). Vertex colours "Col" carry soft AO (ground
  line, soffits, arcade, breezeway). The meshes come without material slots: face material indices
  follow "material_slots" (do not call mesh.materials.clear(), Blender zeroes the indices).

Doors (contract field "doors"): Marston main door (stage 3 interior) on the north wing, facing the
  entry plaza. Extra field "markers" (not part of the contract, safe to ignore): Turlington steps
  (Tabling Gauntlet start), Marston entry plaza (TA Office Hours #2).
"""
import math

import bmesh
import bpy
from mathutils import Vector

try:  # the generator imports this module as part of the `landmarks` package
    from . import _common as _C
except Exception:  # pragma: no cover - standalone import
    try:
        import _common as _C  # type: ignore
    except Exception:
        _C = None

_TILE_FALLBACK = {
    "brick_red": 2.0, "brick_dark": 2.0, "limestone": 2.0, "roof_tile_red": 2.0, "roof_dark": 2.0,
    "copper_green": 2.0, "window_dark": 2.0, "window_glass": 3.0, "door_wood": 2.0, "concrete": 2.0,
    "metal_gray": 2.0, "plaza_brick": 2.0, "grass": 4.0, "path": 3.0, "water": 6.0, "dark_trim": 2.0,
    "white_trim": 2.0, "rock": 3.0,
}


def _tile(mat):
    if _C is not None and mat in _C.PALETTE:
        return float(_C.PALETTE[mat].get("tile_m", 2.0))
    return _TILE_FALLBACK.get(mat, 2.0)


# ---------------------------------------------------------------------------------------------
# landmark table
# ---------------------------------------------------------------------------------------------
POTATO_XY = (-44.31, 26.92)      # OSM node n4741925737
MARSTON_BASE_Z = 1.20  # raised entrance level, photo-based metres
MARSTON_DOOR = (-58.5, -69.0)    # left of the westbound approach from Newell Drive

LANDMARKS = [
    {
        "slug": "marston",
        "name": "Marston Science Library",
        "osm_ids": ["w150860048", "w859919297"],
        "center_m": (-59.6, -98.9),
        "height_m": 22.5,
        "doors": [
            {"name": "DOOR_marston_1", "pos_m": (MARSTON_DOOR[0], MARSTON_DOOR[1], MARSTON_BASE_Z),
             "facing_deg": 0.0, "stage": "Marston Science Library (interior), course 3",
             "note": "north-facing entrance, on the left after the westbound brick stair approach", "primary": True},
        ],
        "markers": [
            {"name": "marston_entry_plaza", "pos_m": (-58.5, -65.0, MARSTON_BASE_Z), "facing_deg": 180.0,
             "note": "upper courtyard approach beside the covered entrance"},
        ],
    },
    {
        "slug": "turlington",
        "name": "Turlington Hall",
        "osm_ids": ["w150684197"],
        "center_m": (-75.9, 40.7),
        "height_m": 20.0,
        "doors": [],
        "markers": [
            {"name": "turlington_steps", "pos_m": (-57.0, 24.7, 0.0), "facing_deg": 90.0,
             "note": "east mouth of the breezeway onto Turlington Plaza (Tabling Gauntlet start)"},
            {"name": "turlington_stair_top", "pos_m": (-66.0, 87.0, 9.0), "facing_deg": 180.0,
             "note": "top of the exterior stair, on the 9 m terrace ring"},
        ],
    },
    {
        "slug": "turlington_potato",
        "name": "Turlington rock ('The Potato')",
        "osm_ids": ["n4741925737", "w859919293"],
        "center_m": POTATO_XY,
        "height_m": 2.95,
        "doors": [],
    },
]


# ---------------------------------------------------------------------------------------------
# 2D helpers (pure Python)
# ---------------------------------------------------------------------------------------------
def _area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2.0


def _ccw(p):
    p = [(float(x), float(y)) for x, y in p]
    return p if _area(p) >= 0 else list(reversed(p))


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _dp_open(pts, tol):
    if len(pts) < 3:
        return list(pts)
    a, b = pts[0], pts[-1]
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        d = _seg_dist(pts[i], a, b)
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [a, b]
    return _dp_open(pts[:idx + 1], tol)[:-1] + _dp_open(pts[idx:], tol)


def _dp_closed(pts, tol):
    n = len(pts)
    j0 = max(range(n), key=lambda j: math.dist(pts[0], pts[j]))
    i0 = max(range(n), key=lambda j: math.dist(pts[j0], pts[j]))
    i, j = sorted((i0, j0))
    return _dp_open(pts[i:j + 1], tol)[:-1] + _dp_open(pts[j:] + pts[:i + 1], tol)[:-1]


def _offset(p, d):
    """Offset a CCW polygon inward by d metres (negative d = outward); mitred corners."""
    n = len(p)
    out = []
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        l1 = math.dist(a, b) or 1e-9
        l2 = math.dist(b, c) or 1e-9
        d1 = ((b[0] - a[0]) / l1, (b[1] - a[1]) / l1)
        d2 = ((c[0] - b[0]) / l2, (c[1] - b[1]) / l2)
        p1 = (a[0] - d1[1] * d, a[1] + d1[0] * d)
        p2 = (b[0] - d2[1] * d, b[1] + d2[0] * d)
        cr = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cr) < 1e-4:
            out.append((b[0] - d1[1] * d, b[1] + d1[0] * d))
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / cr
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def _pip(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _along(a, b, s, off=0.0):
    """Point at distance s from a toward b, shifted `off` metres to the LEFT of a->b."""
    L = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    return (a[0] + ux * s - uy * off, a[1] + uy * s + ux * off)


def _strip(a, b, s0, s1, left, right):
    """Quad along segment a->b from s0 to s1, `left` metres to the left and `right` to the right."""
    return _ccw([_along(a, b, s0, -right), _along(a, b, s1, -right), _along(a, b, s1, left),
                 _along(a, b, s0, left)])


def _footprint(ctx, osm_id, fallback=None):
    b = None
    if ctx is not None:
        bl = ctx.get("buildings")
        if bl is not None and osm_id in bl:
            b = bl[osm_id]
        elif ctx.get("campus") is not None:
            for x in ctx["campus"].get("buildings", ()):
                if x.get("id") == osm_id:
                    b = x
                    break
    if b is None:
        if fallback is None:
            raise KeyError(osm_id)
        print(f"marston_turlington: {osm_id} not in campus data, using the built-in outline")
        return [tuple(p) for p in fallback]
    return [tuple(p) for p in b["pts"]]


def _area_pts(ctx, osm_id, fallback):
    if ctx is not None and ctx.get("campus") is not None:
        for a in ctx["campus"].get("areas", ()):
            if a.get("id") == osm_id:
                return [tuple(p) for p in a["pts"]]
    return [tuple(p) for p in fallback]


# ---------------------------------------------------------------------------------------------
# boolean massing (Blender Exact boolean via an evaluated modifier stack)
# ---------------------------------------------------------------------------------------------
class _Solid:
    """Union of prisms, minus cut prisms, plus a second union pass, evaluated with Blender's Exact
    boolean. Prisms are (2D polygon, z0, z1, tag); every face of the result keeps the tag of the
    operand it came from (via the material index, INDEX mode), stored in the int face layer "tag".
    The tags tell the painters which part a face belongs to, and keep coplanar faces of different
    parts (a tower face flush with a wing face) from being merged into one."""

    MAX_TAGS = 8

    def __init__(self, name):
        self.name = name
        self.adds, self.subs, self.adds2 = [], [], []

    def add(self, pts, z0, z1, tag=0):
        self.adds.append((_ccw(pts), z0, z1, tag))

    def sub(self, pts, z0, z1, tag=0):
        self.subs.append((_ccw(pts), z0, z1, tag))

    def add2(self, pts, z0, z1, tag=0):
        self.adds2.append((_ccw(pts), z0, z1, tag))

    @staticmethod
    def _prism_bm(bm, pts, z0, z1, tag=0):
        bot = [bm.verts.new((x, y, z0)) for x, y in pts]
        top = [bm.verts.new((x, y, z1)) for x, y in pts]
        faces = [bm.faces.new(list(reversed(bot))), bm.faces.new(top)]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new([bot[i], bot[j], top[j], top[i]]))
        for f in faces:
            f.material_index = tag
        return faces

    def _obj(self, label, prism, coll, mat):
        pts, z0, z1, tag = prism
        me = bpy.data.meshes.new(f"_sgltmp_{self.name}_{label}")
        bm = bmesh.new()
        self._prism_bm(bm, pts, z0, z1, tag)
        bm.to_mesh(me)
        bm.free()
        for _ in range(self.MAX_TAGS):
            me.materials.append(mat)
        ob = bpy.data.objects.new(me.name, me)
        coll.objects.link(ob)
        return ob

    def evaluate(self):
        """-> bmesh of the closed boolean result with the "tag" face layer (caller frees it)."""
        scene = bpy.context.scene
        coll = bpy.data.collections.new(f"_sgltmp_{self.name}")
        scene.collection.children.link(coll)
        mat = bpy.data.materials.new(f"_sgltmp_{self.name}")
        objs = []
        try:
            base = self._obj("base", self.adds[0], coll, mat)
            objs.append(base)
            stack = [("UNION", t) for t in self.adds[1:]] + [("DIFFERENCE", t) for t in self.subs] + \
                    [("UNION", t) for t in self.adds2]
            for k, (op, t) in enumerate(stack):
                ob = self._obj(f"op{k}", t, coll, mat)
                ob.hide_render = True
                objs.append(ob)
                mod = base.modifiers.new(f"b{k}", "BOOLEAN")
                mod.operation = op
                mod.operand_type = "OBJECT"
                mod.object = ob
                mod.solver = "EXACT"
                if hasattr(mod, "material_mode"):
                    mod.material_mode = "INDEX"
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            ev = base.evaluated_get(dg)
            me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
            bm = bmesh.new()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
            if len(bm.faces) == 0:
                raise RuntimeError("empty boolean result")
        except Exception as e:  # never break the stage build: fall back to plain prisms
            print(f"marston_turlington: boolean massing for {self.name} failed ({e}); using raw prisms")
            bm = bmesh.new()
            for t in self.adds + self.adds2:
                self._prism_bm(bm, *t)
        finally:
            for ob in objs:
                me = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if me.users == 0:
                    bpy.data.meshes.remove(me)
            bpy.data.collections.remove(coll)
            bpy.data.materials.remove(mat)
        layer = bm.faces.layers.int.get("tag") or bm.faces.layers.int.new("tag")
        for f in bm.faces:
            f[layer] = f.material_index
        return bm


def _tag(bm):
    return bm.faces.layers.int.get("tag")


# ---------------------------------------------------------------------------------------------
# bmesh post-processing
# ---------------------------------------------------------------------------------------------
def _fz(f):
    zs = [v.co.z for v in f.verts]
    return min(zs), max(zs)


def _is_wall(f):
    return abs(f.normal.z) < 0.3


def _cleanup(bm):
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.003)
    bm.normal_update()
    kill = [f for f in bm.faces if f.normal.z < -0.99 and _fz(f)[1] < 0.02]
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:], delimit={"MATERIAL"})
    bmesh.ops.dissolve_degenerate(bm, dist=0.003, edges=bm.edges[:])
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.normal_update()


def _bisect(bm, faces_pred, co, no):
    """Cut the faces selected by faces_pred(face) with the plane (co, no)."""
    co = Vector(co)
    no = Vector(no).normalized()
    faces = []
    for f in bm.faces:
        if not faces_pred(f):
            continue
        ds = [(v.co - co).dot(no) for v in f.verts]
        if min(ds) < -0.02 and max(ds) > 0.02:
            faces.append(f)
    if not faces:
        return
    edges = {e for f in faces for e in f.edges}
    verts = {v for f in faces for v in f.verts}
    bmesh.ops.bisect_plane(bm, geom=list(faces) + list(edges) + list(verts), dist=0.0005,
                           plane_co=co, plane_no=no)


def _retag_coplanar(bm, polys, newtag):
    """Give `newtag` to every wall piece lying in the plane of one of the polygons' edges and within
    that edge (the boolean keeps only one operand's face where two are coplanar, so a tower face
    flush with a wing face may come back with the wing's tag). Pieces are split at the edge ends
    first, then same-tag neighbours are merged again."""
    lay = _tag(bm)
    if lay is None:
        return
    for poly in polys:
        poly = _ccw(poly)
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            L = math.dist(a, b)
            if L < 0.05:
                continue
            t = Vector(((b[0] - a[0]) / L, (b[1] - a[1]) / L, 0.0))
            n = Vector((t.y, -t.x, 0.0))
            off = a[0] * n.x + a[1] * n.y

            def sel(f, n=n, off=off):
                return _is_wall(f) and f.normal.dot(n) > 0.999 and abs(f.verts[0].co.dot(n) - off) < 0.03

            _bisect(bm, sel, (a[0], a[1], 0.0), t)
            _bisect(bm, sel, (b[0], b[1], 0.0), t)
            for f in bm.faces:
                if sel(f):
                    sc = (f.calc_center_median() - Vector((a[0], a[1], 0.0))).dot(t)
                    if 0.0 < sc < L:
                        f[lay] = newtag
                        f.material_index = newtag
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.01)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), use_dissolve_boundaries=False,
                             verts=bm.verts[:], edges=bm.edges[:], delimit={"MATERIAL"})
    bm.normal_update()


def _bisect_z(bm, pred, zs):
    for z in zs:
        _bisect(bm, lambda f: _is_wall(f) and pred(f), (0, 0, z), (0, 0, 1))


def _wall_axis(f):
    n = f.normal
    L = math.hypot(n.x, n.y) or 1.0
    return Vector((-n.y / L, n.x / L, 0.0))


def _split_long_walls(bm, max_len):
    """Vertical cuts so no wall face is wider than max_len (UV range limit)."""
    todo = []
    for f in bm.faces:
        if not _is_wall(f):
            continue
        t = _wall_axis(f)
        s = [v.co.dot(t) for v in f.verts]
        w = max(s) - min(s)
        if w > max_len:
            k = int(math.ceil(w / max_len))
            n = f.normal.copy()
            n.z = 0
            n.normalize()
            off = f.verts[0].co.dot(n)
            base = min(s)
            for i in range(1, k):
                todo.append((n.copy(), off, t.copy(), base + w * i / k))
    for n, off, t, sval in todo:
        co = t * sval
        _bisect(bm, lambda f, n=n, off=off: _is_wall(f) and f.normal.dot(n) > 0.999
                and abs(f.verts[0].co.dot(n) - off) < 0.01, co, t)


def _refine_floors(bm, max_len, detach=False, floors_only=False):
    """Split floor (and ceiling) triangles until no edge of such a face is longer than max_len."""
    def horiz(f):
        return f.normal.z > 0.7 if floors_only else abs(f.normal.z) > 0.7
    if detach:
        seam = [e for e in bm.edges if any(horiz(f) for f in e.link_faces) and
                any(not horiz(f) for f in e.link_faces)]
        if seam:
            bmesh.ops.split_edges(bm, edges=seam)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if horiz(f) and len(f.verts) > 3],
                          quad_method="BEAUTY", ngon_method="BEAUTY")
    for _ in range(12):
        long_e = [e for e in bm.edges if e.calc_length() > max_len and any(horiz(f) for f in e.link_faces)]
        if not long_e:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=False)
        bm.normal_update()
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if horiz(f) and len(f.verts) > 3],
                              quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.normal_update()


def _grid_floors(bm, spacing, compact_only, include_ceilings=False):
    """Cut big horizontal faces into cells of at most ~spacing x spacing (keeps UV ranges small and
    floor triangles short without the triangle blow-up of edge bisection). compact_only skips thin
    faces (terrace rings), which the edge refinement handles more cheaply."""
    bm.normal_update()
    jobs = []
    for f in bm.faces:
        nz = f.normal.z
        if not (nz > 0.7 or (include_ceilings and nz < -0.7)):
            continue
        zs = [v.co.z for v in f.verts]
        if max(zs) - min(zs) > 0.02:
            continue
        xs = [v.co.x for v in f.verts]
        ys = [v.co.y for v in f.verts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if max(w, h) <= spacing * 1.05:
            continue
        if compact_only and f.calc_area() / max(f.calc_perimeter(), 1e-6) < 3.0:
            continue
        nx = max(0, int(math.ceil(w / spacing)) - 1)
        ny = max(0, int(math.ceil(h / spacing)) - 1)
        jobs.append((zs[0], nz > 0, (min(xs), min(ys), max(xs), max(ys)),
                     [min(xs) + w * (i + 1) / (nx + 1) for i in range(nx)],
                     [min(ys) + h * (j + 1) / (ny + 1) for j in range(ny)]))
    for z, up, bb, xcuts, ycuts in jobs:
        def pred(g, z=z, up=up, bb=bb):
            if (g.normal.z > 0.7) != up or abs(g.normal.z) < 0.7 or abs(g.verts[0].co.z - z) > 0.02:
                return False
            c = g.calc_center_median()
            return bb[0] - 0.05 <= c.x <= bb[2] + 0.05 and bb[1] - 0.05 <= c.y <= bb[3] + 0.05
        for x in xcuts:
            _bisect(bm, pred, (x, 0, 0), (1, 0, 0))
        for y in ycuts:
            _bisect(bm, pred, (0, y, 0), (0, 1, 0))
    bm.normal_update()


def _detach_horizontal(bm):
    """Split the edges between horizontal faces and walls, so cutting a roof does not add vertices
    to the walls below it (the roof vertices land exactly on the straight wall top edge)."""
    bm.normal_update()
    seam = [e for e in bm.edges if any(abs(f.normal.z) > 0.7 for f in e.link_faces) and
            any(abs(f.normal.z) <= 0.7 for f in e.link_faces)]
    if seam:
        bmesh.ops.split_edges(bm, edges=seam)


def _prep_collision(bm):
    """Detach floors from walls, split big roofs into <= 21 m cells, then bisect any floor edge
    longer than 30 m (floor triangles stay within ~2-3 collision cells)."""
    _detach_horizontal(bm)
    _grid_floors(bm, 21.0, compact_only=True)
    _refine_floors(bm, 30.0, floors_only=True)


def _prep_visual(bm):
    """Keep every face under ~11 texture repeats: vertical cuts on long walls, grid cuts on big
    roofs/soffits."""
    _split_long_walls(bm, 22.0)
    _detach_horizontal(bm)
    _grid_floors(bm, 21.0, compact_only=False, include_ceilings=True)


class _Paint:
    """Material slots + UV + vertex colour writer for one output mesh."""

    def __init__(self, bm):
        self.bm = bm
        self.slots = []
        self.uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
        self.col = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")

    def idx(self, mat):
        if mat not in self.slots:
            self.slots.append(mat)
        return self.slots.index(mat)

    def face(self, f, mat, v0=None, shade=1.0, uvs=None, rot90=False):
        """Assign palette material `mat`, planar UVs (1.0 = one repeat of tile_m metres; walls: u
        along the wall, v up from v0 so ribbon-window bands start on a pane row; rot90 turns the
        texture a quarter turn, e.g. vertical standing seams from the roof_dark rows) and soft AO."""
        f.material_index = self.idx(mat)
        t = _tile(mat)
        n = f.normal
        if uvs is None:
            if abs(n.z) >= 0.7 or (abs(n.z) > 0.45 and abs(n.z) >= max(abs(n.x), abs(n.y))):
                uvs = [(l.vert.co.x / t, l.vert.co.y / t) for l in f.loops]
            else:
                ax = _wall_axis(f)
                zb = 0.0 if v0 is None else v0
                uvs = [(l.vert.co.dot(ax) / t, (l.vert.co.z - zb) / t) for l in f.loops]
                if rot90:
                    uvs = [(v, -u) for u, v in uvs]
                    v0 = None
            du = math.floor(min(u for u, _ in uvs) + 1e-6)
            dv = 0 if v0 is not None else math.floor(min(v for _, v in uvs) + 1e-6)
            uvs = [(u - du, v - dv) for u, v in uvs]
        for l, (u, v) in zip(f.loops, uvs):
            l[self.uv].uv = (u, v)
            k = shade
            if l.vert.co.z < 0.05:
                k *= 0.8
            k = max(0.0, min(1.0, k))
            l[self.col] = (k, k, k, 1.0)

    def poly(self, pts3, mat, uvs=None, shade=1.0, v0=None, hint=None):
        """New face; `hint` = rough outward direction (the winding is flipped to match it)."""
        verts = [self.bm.verts.new(p) for p in pts3]
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            for v in verts:
                self.bm.verts.remove(v)
            return None
        f.normal_update()
        if hint is not None and f.normal.dot(Vector(hint)) < 0:
            f.normal_flip()
            f.normal_update()
        if uvs is not None:
            by_vert = dict(zip(verts, uvs))
            uvs = [by_vert[l.vert] for l in f.loops]
        self.face(f, mat, v0=v0, shade=shade, uvs=uvs)
        return f

    def quad_wall(self, a, b, z0, z1, mat, shade=1.0, v0=None):
        """Wall from 2D a to b, outward normal on the RIGHT of a->b (CCW footprint)."""
        return self.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)],
                         mat, shade=shade, v0=v0)


def _pier_walls(paint, polys, z1, mat, shade=1.0):
    """Free-standing piers under a soffit: four walls each (their tops touch the soffit, their feet
    the ground), kept out of the boolean so the soffit stays one simple face."""
    for poly in polys:
        poly = _ccw(poly)
        for i in range(len(poly)):
            paint.quad_wall(poly[i], poly[(i + 1) % len(poly)], 0.0, z1, mat, shade=shade)


def _to_mesh(bm, paint, name):
    lay = _tag(bm)
    if lay is not None:
        bm.faces.layers.int.remove(lay)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3],
                          quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    me.update()
    return me, list(paint.slots)


def _part(name, mesh, slots, collision, visual):
    if _C is not None and hasattr(_C, "part"):
        return _C.part(name, mesh, slots, collision, visual)
    return {"name": name, "mesh": mesh, "material_slots": list(slots), "collision": bool(collision),
            "visual": bool(visual)}


def _copy_bm(bm):
    me = bpy.data.meshes.new("_sgltmp_copy")
    bm.to_mesh(me)
    out = bmesh.new()
    out.from_mesh(me)
    bpy.data.meshes.remove(me)
    return out


def _tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


# ---------------------------------------------------------------------------------------------
# Turlington Hall
# ---------------------------------------------------------------------------------------------
T_ARC = 4.2      # arcade / breezeway soffit
T_POD = 9.0      # podium (2 floors) = terrace ring
T_UP = 13.0      # upper floor roof (south block) = crown soffit
T_CROWN = 20.0   # crown roof
T_ANNEX = 5.0

T_TUNNEL_Y = (22.0, 27.4)          # breezeway band (OSM passage at y ~24.5)
T_TUNNEL_X = (-117.0, -55.0)
T_DIAG = ((-60.65, 24.86), (-30.44, 55.43))   # plaza facade (OSM vertices), SW -> NE
T_ARC_S = (-1.0, 40.0)             # arcade extent along the diagonal (m from the SW end)
T_ARC_DEPTH = 3.0
T_PIERS_S = (8.5, 16.0, 23.5, 31.0)
T_PIER = 1.2

# north block (crown) outline, OSM vertices; its south side follows the breezeway
T_NORTH = [(-94.45, 78.6), (-83.05, 78.7), (-73.49, 88.31), (-42.03, 88.2), (-30.6, 76.76),
           (-30.44, 55.43), (-60.65, 24.86), (-94.45, 24.86)]
# podium outline: 23 vertices picked from the OSM way (all but the squared NW corner lie on the OSM
# outline); the curve and four small nooks are bridged (SW entrance notch, west seating nook, south
# passage notch, west door pocket) to stay inside the collision budget
T_PODIUM = [(-94.47, 78.62), (-83.05, 78.7), (-73.49, 88.31), (-42.03, 88.2),
            (-30.6, 76.76), (-30.44, 55.43), (-60.65, 24.86), (-60.56, 16.61), (-66.63, 10.46),
            (-72.55, 10.42), (-72.58, 1.26), (-75.11, -3.82), (-91.13, -9.79), (-101.65, -8.09),
            (-101.72, -14.77), (-118.39, -15.73), (-124.25, -7.6), (-125.15, 4.0), (-116.98, 5.34),
            (-114.64, 10.69), (-113.44, 21.43), (-103.33, 31.2), (-94.42, 31.15)]
T_STAIR = {"x_lo": -65.5, "x_hi": -47.0, "y0": 88.25, "w": 2.6}   # rises westward to the terrace

T_FALLBACK = [(-94.5, 76.66), (-92.31, 78.62), (-83.05, 78.7), (-73.49, 88.31), (-42.03, 88.2),
              (-30.6, 76.76), (-30.44, 55.43), (-52.9, 32.71), (-60.65, 24.86), (-60.56, 16.61),
              (-66.63, 10.46), (-75.39, 10.37), (-75.38, 8.48), (-75.38, 7.15), (-72.51, 7.2),
              (-72.58, 1.26), (-75.11, -3.82), (-79.51, -6.5), (-91.13, -9.79), (-101.65, -8.09),
              (-101.72, -14.77), (-111.77, -14.65), (-113.65, -13.64), (-114.05, -14.38),
              (-114.48, -16.35), (-115.4, -15.87), (-115.8, -16.34), (-117.82, -15.16),
              (-118.39, -15.73), (-119.38, -14.83), (-120.33, -13.93), (-121.46, -12.73),
              (-122.45, -11.29), (-123.47, -9.49), (-124.25, -7.6), (-124.85, -5.72),
              (-123.57, -5.09), (-124.26, -2.23), (-124.75, 0.68), (-125.15, 4.0), (-116.98, 5.34),
              (-116.42, 2.32), (-113.4, 2.93), (-114.64, 10.69), (-114.36, 15.71), (-113.44, 21.43),
              (-110.49, 24.45), (-103.33, 31.2), (-96.48, 31.11), (-96.52, 28.19), (-94.39, 28.14),
              (-94.43, 65.2), (-96.06, 65.23), (-96.09, 66.71), (-99.02, 68.68), (-106.41, 68.46),
              (-106.41, 75.68), (-99.16, 75.55), (-97.48, 74.04), (-94.51, 74.04)]


def _turlington_plan(ctx):
    raw = _footprint(ctx, "w150684197", T_FALLBACK)
    # split off the NW service annex (OSM vertices from (-94.43, 65.2) to (-94.51, 74.04))
    def near(p, q):
        return math.dist(p, q) < 0.3
    ia = next((i for i, p in enumerate(raw) if near(p, (-94.43, 65.2))), None)
    ib = next((i for i, p in enumerate(raw) if near(p, (-94.51, 74.04))), None)
    if ia is not None and ib is not None and ia < ib:
        main = raw[:ia + 1] + raw[ib:]
        annex = raw[ia:ib + 1]
    else:
        main, annex = raw, []
    main = _ccw(main)
    # curated outline if it still matches the OSM data (every vertex within 1.6 m of the outline,
    # the squared NW corner being the farthest), otherwise a plain Douglas-Peucker simplification
    n = len(main)
    off = max(min(_seg_dist(v, main[i], main[(i + 1) % n]) for i in range(n)) for v in T_PODIUM)
    if off <= 1.6:
        pod = _ccw(T_PODIUM)
    else:
        print(f"marston_turlington: Turlington outline moved ({off:.2f} m), using a DP simplification")
        pod = _ccw(_dp_closed(main, 1.0))
    annex = _ccw(_dp_closed(_ccw(annex), 1.2)) if len(annex) >= 3 else []
    if annex:  # push the shared side 0.4 m into the main block so the union welds cleanly
        annex = [(x + 0.4, y) if x > -94.7 else (x, y) for x, y in annex]
    # upper floors: podium inset 3 m (the terrace), lightly simplified, must stay inside
    upper = _ccw(_dp_closed(_offset(pod, 3.0), 3.0))
    if not all(_pip(v, pod) for v in upper) or min(
            _seg_dist(v, pod[i], pod[(i + 1) % len(pod)]) for v in upper for i in range(len(pod))) < 1.5:
        print("marston_turlington: upper-floor inset failed validation, using a 2 m inset")
        upper = _ccw(_offset(pod, 2.0))
    crown = _offset(_ccw(T_NORTH), 1.0)   # its south side sits on the 13 m roof of the south block
    a, b = T_DIAG
    arcade = _strip(a, b, T_ARC_S[0], T_ARC_S[1], T_ARC_DEPTH, 1.5)   # left of SW->NE = inside
    piers = []
    for s in T_PIERS_S:
        piers.append(_strip(a, b, s - T_PIER / 2, s + T_PIER / 2, T_PIER, 0.0))
    tunnel = _rect(T_TUNNEL_X[0], T_TUNNEL_Y[0], T_TUNNEL_X[1], T_TUNNEL_Y[1])
    return {"pod": pod, "annex": annex, "upper": upper, "crown": crown, "arcade": arcade,
            "piers": piers, "tunnel": tunnel}


TT_POD, TT_UP, TT_CROWN, TT_ANNEX, TT_TUNNEL, TT_ARCADE = range(6)   # boolean operand tags


def _turlington_massing(plan):
    s = _Solid("turlington")
    s.add(plan["pod"], 0.0, T_POD, TT_POD)
    s.add(plan["upper"], T_POD - 0.1, T_UP, TT_UP)
    s.add(plan["crown"], T_UP, T_CROWN, TT_CROWN)
    if plan["annex"]:
        s.add(plan["annex"], 0.0, T_ANNEX, TT_ANNEX)
    s.sub(plan["tunnel"], -1.0, T_ARC, TT_TUNNEL)
    s.sub(plan["arcade"], -1.0, T_ARC, TT_ARCADE)
    bm = s.evaluate()
    _cleanup(bm)
    return bm


def _turlington_stair_pts():
    st = T_STAIR
    return st["x_lo"], st["x_hi"], st["y0"], st["y0"] + st["w"]


def _turlington_paint(bm, plan, paint, visual):
    lay = _tag(bm)
    arc = plan["arcade"]

    def tag(f):
        return f[lay] if lay is not None else TT_POD

    def width(f):
        ax = _wall_axis(f)
        sv = [v.co.dot(ax) for v in f.verts]
        return max(sv) - min(sv)

    def above_arcade(f):
        c = f.calc_center_median()
        return _pip((c.x + f.normal.x * 0.5, c.y + f.normal.y * 0.5), arc)

    if visual:
        pod = lambda f: tag(f) == TT_POD
        _bisect_z(bm, lambda f: pod(f) and _fz(f)[0] < 0.5 and width(f) >= 6.0, (1.0, 3.0))
        _bisect_z(bm, lambda f: pod(f) and _fz(f)[0] > T_ARC - 0.1 and above_arcade(f), (T_ARC + 0.6,))
        _bisect_z(bm, pod, (T_POD - 0.4,))
        _bisect_z(bm, lambda f: tag(f) == TT_UP, (10.0, 12.0))
        _bisect_z(bm, lambda f: tag(f) == TT_CROWN, (T_UP + 0.4, T_CROWN - 0.4))
        _bisect_z(bm, lambda f: tag(f) == TT_ANNEX, (T_ANNEX - 0.4,))
        _prep_visual(bm)
    else:
        _prep_collision(bm)

    for f in bm.faces:
        lo, hi = _fz(f)
        t = tag(f)
        n = f.normal
        if n.z > 0.7:
            paint.face(f, "roof_dark" if t == TT_CROWN else "concrete")
            continue
        if n.z < -0.7:
            paint.face(f, "white_trim", shade=0.82 if hi < T_POD else 0.9)
            continue
        if t == TT_TUNNEL:
            paint.face(f, "brick_dark", shade=0.7)
        elif t == TT_ARCADE:
            paint.face(f, "window_dark" if visual else "brick_dark", v0=0.0, shade=0.75)
        elif not visual:
            paint.face(f, "roof_dark" if t == TT_CROWN else "brick_red")
        elif t == TT_ANNEX:
            paint.face(f, "dark_trim" if lo >= T_ANNEX - 0.45 else "brick_red")
        elif t == TT_POD:
            if lo >= 0.95 and hi <= 3.05:
                paint.face(f, "window_dark", v0=1.0)
            elif lo >= T_POD - 0.45:
                paint.face(f, "concrete")
            elif lo >= T_ARC - 0.05 and hi <= T_ARC + 0.65 and above_arcade(f):
                paint.face(f, "white_trim")
            else:
                paint.face(f, "brick_red")
        elif t == TT_UP:
            if lo >= 9.95 and hi <= 12.05:
                paint.face(f, "window_dark", v0=10.0)
            else:
                paint.face(f, "brick_red")
        else:                            # crown
            if hi <= T_UP + 0.45:
                paint.face(f, "white_trim")
            elif lo >= T_CROWN - 0.45:
                paint.face(f, "dark_trim")
            else:
                paint.face(f, "roof_dark", rot90=True)    # standing seams run vertically


def _turlington_details(paint, plan):
    """Visual-only additions: porthole decals, chunky exterior stair."""
    pod = plan["pod"]
    n = len(pod)
    ty0, ty1 = T_TUNNEL_Y
    holes = 0
    for i in range(n):
        a, b = pod[i], pod[(i + 1) % n]
        L = math.dist(a, b)
        if L < 7.0:
            continue
        k = int((L - 2.0) // 5.0)
        if k <= 0:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = uy, -ux  # outward (right of a->b on a CCW outline)
        for j in range(k):
            s = (L - (k - 1) * 5.0) / 2.0 + j * 5.0
            cx, cy = a[0] + ux * s + nx * 0.04, a[1] + uy * s + ny * 0.04
            if ty0 - 1.0 < cy < ty1 + 1.0 and T_TUNNEL_X[0] < cx < T_TUNNEL_X[1] and abs(nx) > 0.5:
                continue
            if T_STAIR["x_lo"] - 1 < cx < T_STAIR["x_hi"] + 1 and cy > 87.0:
                continue  # behind the stair
            r, zc = 0.62, 6.6
            pts = []
            uvs = []
            for m in range(6):
                ang = math.pi * 2 * m / 6
                du, dz = math.cos(ang) * r, math.sin(ang) * r
                pts.append((cx + ux * du, cy + uy * du, zc + dz))
                uvs.append((0.125 + 0.11 * math.cos(ang), 0.25 + 0.22 * math.sin(ang)))
            paint.poly(pts, "window_dark", uvs=uvs)
            holes += 1
    # exterior stair on the north face: chunky 0.5 m steps (collision uses a ramp)
    x_lo, x_hi, y0, y1 = _turlington_stair_pts()
    steps = 15
    rise = T_POD / steps
    run = (x_hi - x_lo) / steps
    for i in range(steps):
        xa = x_hi - i * run
        za = i * rise
        # riser at xa, tread from xa to xa - run at height za + rise, and the step's side triangle
        paint.poly([(xa, y1, za), (xa, y0, za), (xa, y0, za + rise), (xa, y1, za + rise)], "concrete",
                   shade=0.85, hint=(1, 0, 0))
        paint.poly([(xa, y1, za + rise), (xa, y0, za + rise), (xa - run, y0, za + rise),
                    (xa - run, y1, za + rise)], "concrete", hint=(0, 0, 1))
        paint.poly([(xa, y1, za), (xa, y1, za + rise), (xa - run, y1, za + rise)], "concrete", shade=0.9,
                   hint=(0, 1, 0))
    # outer cheek wall (north side) below the nosing line
    paint.poly([(x_hi, y1, 0.0), (x_lo, y1, 0.0), (x_lo, y1, T_POD)], "concrete", shade=0.9, hint=(0, 1, 0))
    paint.quad_wall((x_lo, y1), (x_lo, y0), 0.0, T_POD, "concrete", shade=0.85)   # west end
    return holes


def _turlington_stair_collision(paint):
    """Ramp through the centres of the 15 treads (so Mario stands on each tread), a half-tread
    landing at 9 m that meets the terrace across the podium wall top, the solid north cheek and the
    west end wall. The ramp's south side touches the podium wall."""
    x_lo, x_hi, y0, y1 = _turlington_stair_pts()
    run = (x_hi - x_lo) / 15
    xa, xb, zt = x_hi + 0.6, x_lo + run / 2, T_POD
    paint.poly([(xa, y0, 0.0), (xa, y1, 0.0), (xb, y1, zt), (xb, y0, zt)], "concrete", hint=(0, 0, 1))
    paint.poly([(xb, y0, zt), (xb, y1, zt), (x_lo, y1, zt), (x_lo, y0, zt)], "concrete", hint=(0, 0, 1))
    paint.poly([(xa, y1, 0.0), (x_lo, y1, 0.0), (x_lo, y1, zt), (xb, y1, zt)], "concrete", hint=(0, 1, 0))
    paint.quad_wall((x_lo, y1), (x_lo, y0), 0.0, zt, "concrete")   # west end (solid stair)


def build_turlington(ctx):
    plan = _turlington_plan(ctx)
    base = _turlington_massing(plan)
    out = []
    # collision
    col = _copy_bm(base)
    pc = _Paint(col)
    _turlington_paint(col, plan, pc, visual=False)
    _turlington_stair_collision(pc)
    _pier_walls(pc, plan["piers"], T_ARC, "brick_red")
    me, slots = _to_mesh(col, pc, "turlington.collision")
    col.free()
    out.append(_part("turlington_collision", me, slots, collision=True, visual=False))
    # visual
    vis = base
    pv = _Paint(vis)
    _turlington_paint(vis, plan, pv, visual=True)
    _turlington_details(pv, plan)
    _pier_walls(pv, plan["piers"], T_ARC, "brick_red", shade=0.88)
    me, slots = _to_mesh(vis, pv, "turlington.visual")
    vis.free()
    out.append(_part("turlington_visual", me, slots, collision=False, visual=True))
    return out


# ---------------------------------------------------------------------------------------------
# Marston Science Library
# ---------------------------------------------------------------------------------------------
M_ROOF = 16.8       # 4 floors x 4.2 m
M_TOWER = 22.5      # 5 floors + parapet (stages.json)
M_FLOOR = 4.2
M_STEP_X = (-66.3, -50.7)
M_STEP_Y = (-70.25, -71.45, -72.65)   # floor 2 / 3 / 4 faces of the stepped north wing
M_COLONNADE = _rect(-92.5, -107.3, -86.9, -93.7)
M_PIERS = [_rect(-89.45, y - 0.5, -88.45, y + 0.5) for y in (-97.0, -100.4, -103.8)]
# towers: (outline on the OSM footprint lines, {vertex index: chamfer size}); faces shared with the
# footprint are coplanar with it so the union leaves one clean wall; chamfered corners are also cut
# out of the base so the chamfer runs to the ground
M_TOWER_SRC = [
    ([(-50.92, -67.4), (-39.8, -67.47), (-39.61, -79.02), (-51.0, -79.1)], {1: 1.8}),    # NE block
    ([(-71.03, -69.07), (-65.8, -69.05), (-65.8, -78.9), (-70.64, -78.77), (-70.97, -70.51)],
     {0: 1.2}),                                                                         # court N
    ([(-89.33, -87.38), (-82.6, -87.45), (-82.6, -93.5), (-89.38, -93.5)], {0: 1.2}),   # court S
    ([(-90.83, -107.79), (-79.46, -107.6), (-79.45, -118.91), (-90.81, -118.99)], {3: 1.8}),  # SW
]


def _chamfer(poly, corners):
    """-> (polygon with the listed corners cut by size c, [cut triangles extending past the corner])."""
    out, cuts = [], []
    n = len(poly)
    for i, p in enumerate(poly):
        c = corners.get(i)
        if not c:
            out.append(p)
            continue
        a, b = poly[i - 1], poly[(i + 1) % n]
        la, lb = math.dist(a, p), math.dist(b, p)
        p1 = (p[0] + (a[0] - p[0]) / la * c, p[1] + (a[1] - p[1]) / la * c)
        p2 = (p[0] + (b[0] - p[0]) / lb * c, p[1] + (b[1] - p[1]) / lb * c)
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        far = (p[0] + (p[0] - mx) * 3.0, p[1] + (p[1] - my) * 3.0)
        p1o = (p1[0] + (p1[0] - p2[0]) * 0.5, p1[1] + (p1[1] - p2[1]) * 0.5)
        p2o = (p2[0] + (p2[0] - p1[0]) * 0.5, p2[1] + (p2[1] - p1[1]) * 0.5)
        out += [p1, p2]
        cuts.append([p1o, p2o, far])
    return out, cuts


M_TOWERS = [_chamfer(t, c)[0] for t, c in M_TOWER_SRC]
M_TOWER_CUTS = [cut for t, c in M_TOWER_SRC for cut in _chamfer(t, c)[1]]
M_SKY = {"x": (-74.0, -50.0), "y": (-112.0, -94.0), "ridge_z": 21.3}
M_COURT_Z = (15.0, 16.2)
M_PLANTERS = []  # Landscape builder owns connected beds and entrance clearance.
M_PLANTER = (4.0, 2.6, 0.9)

M_FALLBACK = [(-39.8, -67.47), (-39.61, -79.02), (-42.58, -79.03), (-42.61, -87.11), (-33.54, -87.07),
              (-33.54, -105.0), (-33.54, -124.95), (-71.21, -125.0), (-71.21, -115.9), (-75.34, -115.92),
              (-79.46, -115.95), (-79.45, -118.91), (-88.56, -118.97), (-90.81, -118.99), (-90.83, -107.79),
              (-89.55, -106.11), (-89.46, -102.17), (-89.35, -97.86), (-89.33, -87.38), (-87.94, -87.36),
              (-79.89, -87.47), (-75.25, -83.14), (-70.64, -78.77), (-70.97, -70.51), (-71.03, -69.07),
              (-52.61, -68.98), (-50.92, -67.4)]
M_COURT_FALLBACK = [(-90.83, -84.36), (-89.89, -84.36), (-88.76, -85.44), (-87.98, -86.32), (-87.94, -87.36),
                    (-79.89, -87.47), (-75.25, -83.14), (-70.64, -78.77), (-70.97, -70.51), (-72.13, -70.56),
                    (-73.17, -69.57), (-74.07, -68.6), (-74.02, -67.62), (-82.44, -67.49), (-86.84, -71.59),
                    (-90.91, -75.9)]


def _marston_plan(ctx):
    raw = _ccw(_footprint(ctx, "w150860048", M_FALLBACK))
    fp = _dp_closed(raw, 0.6)
    court_raw = _ccw(_footprint(ctx, "w859919297", M_COURT_FALLBACK))
    court = _offset(_ccw(_dp_closed(court_raw, 1.5)), -0.3)
    return {"fp": _ccw(fp), "court": court}


MT_BASE, MT_TOWER, MT_STEP, MT_COLONNADE, MT_CHAMFER = range(5)   # boolean operand tags


def _marston_massing(plan):
    s = _Solid("marston")
    s.add(plan["fp"], 0.0, M_ROOF, MT_BASE)
    x0, x1 = M_STEP_X
    for k, y in enumerate(M_STEP_Y):
        s.sub(_rect(x0, y, x1, -55.0), M_FLOOR * (k + 1), 40.0, MT_STEP)
    s.sub(M_COLONNADE, -1.0, M_FLOOR, MT_COLONNADE)
    for cut in M_TOWER_CUTS:
        s.sub(cut, -1.0, 40.0, MT_CHAMFER)
    for t in M_TOWERS:      # clear the tower footprints, then add the towers: their faces stay theirs
        s.sub(t, -1.0, 40.0, MT_TOWER)
    for t in M_TOWERS:
        s.add2(t, 0.0, M_TOWER, MT_TOWER)
    bm = s.evaluate()
    _cleanup(bm)
    _retag_coplanar(bm, M_TOWERS, MT_TOWER)
    return bm


def _marston_paint(bm, plan, paint, visual):
    lay = _tag(bm)

    def tag(f):
        return f[lay] if lay is not None else MT_BASE

    def is_tower(f):
        return tag(f) in (MT_TOWER, MT_CHAMFER)

    def width(f):
        ax = _wall_axis(f)
        sv = [v.co.dot(ax) for v in f.verts]
        return max(sv) - min(sv)

    def north_ground(f):
        return tag(f) == MT_BASE and f.normal.y > 0.95 and _fz(f)[1] <= M_FLOOR + 0.05 and \
            M_STEP_X[0] < f.calc_center_median().x < M_STEP_X[1]

    if visual:
        main_wall = lambda f: tag(f) in (MT_BASE, MT_STEP) and width(f) >= 4.5
        _bisect_z(bm, main_wall, (5.2, 7.2, 7.8, 9.4, 11.4, 12.0, 13.6, 15.6))
        _bisect_z(bm, north_ground, (0.6, 3.6))
        _bisect_z(bm, lambda f: is_tower(f) and width(f) >= 3.0, (10.8, 11.4, M_TOWER - 0.6))
        _bisect_z(bm, lambda f: is_tower(f) and width(f) < 3.0, (M_TOWER - 0.6,))
        _prep_visual(bm)
    else:
        _prep_collision(bm)

    bands = ((5.2, 7.2, "window_dark"), (7.2, 7.8, "dark_trim"), (9.4, 11.4, "window_dark"),
             (11.4, 12.0, "dark_trim"), (13.6, 15.6, "window_dark"), (15.6, M_ROOF, "dark_trim"))
    for f in bm.faces:
        lo, hi = _fz(f)
        n = f.normal
        t = tag(f)
        if n.z > 0.7:
            paint.face(f, "concrete")
            continue
        if n.z < -0.7:
            paint.face(f, "dark_trim", shade=0.8)
            continue
        if t == MT_COLONNADE:
            paint.face(f, "window_glass", v0=0.0, shade=0.75)
        elif not visual:
            paint.face(f, "brick_red")
        elif is_tower(f):
            if (lo >= 10.75 and hi <= 11.45) or lo >= M_TOWER - 0.65:
                paint.face(f, "dark_trim")
            else:
                paint.face(f, "brick_red")
        else:
            mat, v0 = "brick_red", None
            for z0, z1, m in bands:
                if lo >= z0 - 0.05 and hi <= z1 + 0.05:
                    mat, v0 = m, (z0 if m == "window_dark" else None)
                    break
            if north_ground(f) and lo >= 0.55 and hi <= 3.65:
                mat, v0 = "window_glass", 0.6
            paint.face(f, mat, v0=v0)


def _marston_skylight(paint):
    x0, x1 = M_SKY["x"]
    y0, y1 = M_SKY["y"]
    z0, zr = M_ROOF, M_SKY["ridge_z"]
    h = (y1 - y0) / 2.0
    ym = (y0 + y1) / 2.0
    ra, rb = x0 + h, x1 - h     # ridge ends (all four slopes equal)
    A, B, C, D = (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)
    R1, R2 = (ra, ym, zr), (rb, ym, zr)
    paint.poly([A, B, R2, R1], "window_glass")      # south slope
    paint.poly([C, D, R1, R2], "window_glass")      # north slope
    paint.poly([B, C, R2], "window_glass")          # east hip
    paint.poly([D, A, R1], "window_glass")          # west hip


def _marston_court(paint, plan, visual):
    """Roof slab over the Marston/CSE court; only its two open ends show (the long sides are buried
    0.3 m in Marston and CSE)."""
    poly = plan["court"]
    z0, z1 = M_COURT_Z
    n = len(poly)
    paint.poly([(x, y, z1) for x, y in poly], "metal_gray")
    paint.poly([(x, y, z0) for x, y in reversed(poly)], "dark_trim", shade=0.75)
    # the open ends are the edges whose midpoints are not inside Marston/CSE: test against the
    # two mouth points (NE toward the plaza, SW toward Marston Courtyard)
    mouths = [(-72.5, -69.0), (-89.4, -85.9)]
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if min(math.dist(mid, m) for m in mouths) > 2.6:
            continue
        if visual:
            paint.quad_wall(a, b, z0, z0 + 0.4, "metal_gray")
            paint.quad_wall(a, b, z0 + 0.4, z1 - 0.3, "dark_trim")
            paint.quad_wall(a, b, z1 - 0.3, z1, "metal_gray")
        else:
            paint.quad_wall(a, b, z0, z1, "dark_trim")


def _marston_planters(paint, visual):
    w, d, h = M_PLANTER
    for cx, cy in M_PLANTERS:
        r = _ccw(_rect(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))
        for i in range(4):
            paint.quad_wall(r[i], r[(i + 1) % 4], 0.0, h, "brick_red")
        if visual:
            paint.poly([(x, y, h) for x, y in _offset(r, 0.25)], "grass")
            inner = _offset(r, 0.25)
            for i in range(4):  # brick cap ring
                a, b, c2, d2 = r[i], r[(i + 1) % 4], inner[(i + 1) % 4], inner[i]
                paint.poly([(a[0], a[1], h), (b[0], b[1], h), (c2[0], c2[1], h), (d2[0], d2[1], h)],
                           "brick_red")
        else:
            paint.poly([(x, y, h) for x, y in r], "grass")


def _marston_door(paint):
    # Door faces the upper courtyard, left of the approach from the street.
    x, y = MARSTON_DOOR
    f = 0.0
    nx, ny = math.sin(f), math.cos(f)
    tx, ty = ny, -nx
    def panel(half, top, offset, mat):
        pts = [(x + tx * u + nx * offset, y + ty * u + ny * offset, z)
               for u, z in [(-half, 0), (half, 0), (half, top), (-half, top)]]
        paint.poly(pts, mat, hint=(nx, ny, 0))
    panel(2.2, 3.1, .06, 'dark_trim')
    panel(2.0, 2.85, .09, 'window_glass')


def build_marston(ctx):
    plan = _marston_plan(ctx)
    base = _marston_massing(plan)
    # Extend the masonry base to ground; translate the complete building below.
    for v in base.verts:
        if abs(v.co.z) < 0.001:
            v.co.z -= MARSTON_BASE_Z
    out = []
    col = _copy_bm(base)
    pc = _Paint(col)
    _marston_paint(col, plan, pc, visual=False)
    _marston_skylight(pc)
    _marston_court(pc, plan, visual=False)
    _marston_planters(pc, visual=False)
    _pier_walls(pc, M_PIERS, M_FLOOR, "dark_trim")
    me, slots = _to_mesh(col, pc, "marston.collision")
    col.free()
    for v in me.vertices:
        v.co.z += MARSTON_BASE_Z
    out.append(_part("marston_collision", me, slots, collision=True, visual=False))
    vis = base
    pv = _Paint(vis)
    _marston_paint(vis, plan, pv, visual=True)
    _marston_skylight(pv)
    _marston_court(pv, plan, visual=True)
    _marston_planters(pv, visual=True)
    _marston_door(pv)
    _pier_walls(pv, M_PIERS, M_FLOOR, "dark_trim", shade=0.9)
    me, slots = _to_mesh(vis, pv, "marston.visual")
    vis.free()
    for v in me.vertices:
        v.co.z += MARSTON_BASE_Z
    out.append(_part("marston_visual", me, slots, collision=False, visual=True))
    return out


# ---------------------------------------------------------------------------------------------
# The Potato (Turlington rock) + its bench ring
# ---------------------------------------------------------------------------------------------
P_BENCH_R = (3.25, 3.75, 0.45)      # inner, outer radius, seat height (OSM ring ~7.6 m across)
P_BENCH_SEGS = 10
P_BENCH_GAPS = (0, 5)               # open segments: east (toward Newell Dr) and west (Turlington)
P_LOBE_DIR = math.radians(140.0)    # side lobe toward the NW
P_HEAD_Z = 2.9


def _potato_profile():
    # (z, radius, lean toward +x) rings of the bowling-pin body
    return [(0.22, 0.64, 0.0), (0.72, 0.76, 0.0), (1.45, 0.52, 0.05), (1.95, 0.63, 0.08),
            (2.45, 0.62, 0.10), (2.80, 0.42, 0.11)]


def _lathe(paint, cx, cy, rings, sides, apex_z, mat, seed, tilt=(0.0, 0.0), bottom=False):
    rows = []
    for k, (z, r, lean) in enumerate(rings):
        row = []
        for i in range(sides):
            a = 2 * math.pi * i / sides + 0.3 * k
            rr = r * (1.0 + 0.09 * math.sin(3.1 * i + 1.7 * k + seed) + 0.05 * math.cos(5.3 * i + seed))
            row.append((cx + math.cos(a) * rr + lean + tilt[0] * z, cy + math.sin(a) * rr + tilt[1] * z, z))
        rows.append(row)
    for k in range(len(rows) - 1):
        lo, hi = rows[k], rows[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            paint.poly([lo[i], lo[j], hi[j], hi[i]], mat, shade=0.9 + 0.1 * (k / max(1, len(rows) - 2)))
    top = rows[-1]
    zt, _, lean = rings[-1]
    apex = (cx + lean + tilt[0] * apex_z, cy + tilt[1] * apex_z, apex_z)
    for i in range(sides):
        paint.poly([top[i], top[(i + 1) % sides], apex], mat)
    if bottom:
        paint.poly(list(reversed(rows[0])), mat)


def _bench_segments():
    ri, ro, h = P_BENCH_R
    segs = []
    for k in range(P_BENCH_SEGS):
        if k in P_BENCH_GAPS:
            continue
        a0 = 2 * math.pi * (k - 0.5) / P_BENCH_SEGS
        a1 = 2 * math.pi * (k + 0.5) / P_BENCH_SEGS
        segs.append((a0, a1))
    return ri, ro, h, segs


def build_potato(ctx):
    cx, cy = POTATO_XY
    if ctx is not None and ctx.get("campus") is not None:
        for p in ctx["campus"].get("points", ()):
            if p.get("id") == "n4741925737":
                cx, cy = p["pt"]
                break
    ring = _area_pts(ctx, "w859919293", [])
    if ring:
        bx = sum(p[0] for p in ring) / len(ring)
        by = sum(p[1] for p in ring) / len(ring)
    else:
        bx, by = cx, cy
    out = []
    ri, ro, h, segs = _bench_segments()

    # ---- collision (<= 40 tris)
    bm = bmesh.new()
    pc = _Paint(bm)
    hexr = 0.66
    hexp = [(cx + 0.05 + hexr * math.cos(2 * math.pi * i / 6), cy + hexr * math.sin(2 * math.pi * i / 6))
            for i in range(6)]
    for i in range(6):
        pc.quad_wall(hexp[i], hexp[(i + 1) % 6], 0.0, P_HEAD_Z, "rock")
    pc.poly([(x, y, P_HEAD_Z) for x, y in hexp], "rock")
    lx, ly = cx + math.cos(P_LOBE_DIR) * 0.85, cy + math.sin(P_LOBE_DIR) * 0.85
    tri = [(lx + 0.42 * math.cos(P_LOBE_DIR + d), ly + 0.42 * math.sin(P_LOBE_DIR + d))
           for d in (0.0, 2.2, -2.2)]
    tri = _ccw(tri)
    for i in range(3):
        pc.quad_wall(tri[i], tri[(i + 1) % 3], 0.0, 1.75, "rock")
    pc.poly([(x, y, 1.75) for x, y in tri], "rock")
    for a0, a1 in segs:   # seat tops only: Mario steps up 0.45 m onto them (no wall needed)
        pc.poly([(bx + ri * math.cos(a0), by + ri * math.sin(a0), h), (bx + ro * math.cos(a0), by + ro * math.sin(a0), h),
                 (bx + ro * math.cos(a1), by + ro * math.sin(a1), h), (bx + ri * math.cos(a1), by + ri * math.sin(a1), h)],
                "concrete")
    me, slots = _to_mesh(bm, pc, "turlington_potato.collision")
    bm.free()
    out.append(_part("turlington_potato_collision", me, slots, collision=True, visual=False))

    # ---- visual (<= 200 tris)
    bm = bmesh.new()
    pv = _Paint(bm)
    # pedestal
    ped = [(cx + 0.88 * math.cos(2 * math.pi * i / 6), cy + 0.88 * math.sin(2 * math.pi * i / 6)) for i in range(6)]
    for i in range(6):
        pv.quad_wall(ped[i], ped[(i + 1) % 6], 0.0, 0.24, "concrete", shade=0.85)
    pv.poly([(x, y, 0.24) for x, y in ped], "concrete")
    # body
    _lathe(pv, cx, cy, _potato_profile(), 8, 2.97, "rock", seed=1.3)
    # side lobe ("thumb"), leaning outward
    lrings = [(0.25, 0.30, 0.0), (0.85, 0.40, 0.0), (1.45, 0.33, 0.0)]
    _lathe(pv, lx - math.cos(P_LOBE_DIR) * 0.1, ly - math.sin(P_LOBE_DIR) * 0.1, lrings, 6, 1.85, "rock",
           seed=4.1, tilt=(math.cos(P_LOBE_DIR) * 0.08, math.sin(P_LOBE_DIR) * 0.08))
    # gravel circle
    gr = ri - 0.05
    pv.poly([(bx + gr * math.cos(2 * math.pi * (i + 0.5) / 8), by + gr * math.sin(2 * math.pi * (i + 0.5) / 8), 0.02)
             for i in range(8)], "path")
    # bench ring
    for a0, a1 in segs:
        ci0, si0, ci1, si1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        pi0, pi1 = (bx + ri * ci0, by + ri * si0), (bx + ri * ci1, by + ri * si1)
        po0, po1 = (bx + ro * ci0, by + ro * si0), (bx + ro * ci1, by + ro * si1)
        pv.poly([(pi0[0], pi0[1], h), (po0[0], po0[1], h), (po1[0], po1[1], h), (pi1[0], pi1[1], h)], "white_trim")
        pv.quad_wall(po0, po1, 0.0, h, "white_trim", shade=0.85)     # outer face
        pv.quad_wall(pi1, pi0, 0.0, h, "white_trim", shade=0.8)      # inner face
    for k in range(P_BENCH_SEGS):          # end caps at the two gaps
        if k not in P_BENCH_GAPS:
            continue
        for a, sgn in ((2 * math.pi * (k - 0.5) / P_BENCH_SEGS, -1), (2 * math.pi * (k + 0.5) / P_BENCH_SEGS, 1)):
            p_in = (bx + ri * math.cos(a), by + ri * math.sin(a))
            p_out = (bx + ro * math.cos(a), by + ro * math.sin(a))
            if sgn > 0:
                pv.quad_wall(p_in, p_out, 0.0, h, "white_trim", shade=0.8)
            else:
                pv.quad_wall(p_out, p_in, 0.0, h, "white_trim", shade=0.8)
    me, slots = _to_mesh(bm, pv, "turlington_potato.visual")
    bm.free()
    out.append(_part("turlington_potato_visual", me, slots, collision=False, visual=True))
    return out


# ---------------------------------------------------------------------------------------------
def build(ctx):
    parts = []
    parts += build_marston(ctx)
    parts += build_turlington(ctx)
    parts += build_potato(ctx)
    for p in parts:
        print(f"marston_turlington: {p['name']:32s} {_tri_count(p['mesh']):5d} tris  "
              f"{'collision' if p['collision'] else 'visual'}  slots={p['material_slots']}")
    return parts
