"""Interior kit: parametric low-poly interior props for the SGL64 interior stages (Course 4 Marston Science
Library first; Library West and the Century Tower interior later). Everything is in MAP METRES, z up
(x = east, y = north), true 1:1 real-world defaults, sized for SM64 movement, with N64-style textures
(the int_* materials) and lighting baked into vertex colours.

Overview
--------
  textures   tools/campus/make_textures.py build_interior() -> art/levels/textures/int_*.png (34 RGBA16
             textures, 32 x 32 or 64 x 32: carpet, floor tile, stone, drywall, blue paint, acoustic ceiling,
             troffer light, two book-spine sets, shelf steel, two woods, glass, cut-out railing bars, metal,
             plastic, three fabrics, whiteboard, monitor, kiosk, elevator doors, stair tread, the window
             view of campus, posters, six signs and a floor-number atlas).
  palette    tools/campus/stage_palette.py INTERIOR_MATERIALS (tile_m, colour, kind, "lit": "vertex",
             "map": "tile" | "once"). Opt-in: NOT part of stage_palette.MATERIALS, so outdoor stage builds
             do not change.
  materials  tools/campus/stage_materials.py make_interior_materials() + interior_tiles(): Fast64 fog
             materials with G_LIGHTING off (the vertex colour is the shade) plus 'COL notslip'
             (SURFACE_NOT_SLIPPERY, stair ramps) and 'COL hangable' (SURFACE_HANGABLE, the light ring).
  geometry   this module. Pure Python (no bpy) until you ask for Blender meshes, so props can be built,
             measured and tested with tools/.venv/bin/python -I tools/campus/interior_kit.py --selftest.
  demo       tools/campus/interior_kit_demo.py (Blender): a sample two-level room with every prop ->
             art/levels/marston/kit_*.png previews, and optionally a Fast64 test export to a scratch dir.

Integration with the stage generator (build_stage.py)
-----------------------------------------------------
  1. Materials: the interior stage's build adds the kit materials to the stage dict
         mats = stage_materials.make_materials(); mats.update(stage_materials.make_interior_materials())
         tiles = stage_materials.tiles(); tiles.update(stage_materials.interior_tiles())
     (stage_landmarks.add_part refuses a part whose material_slots name an unknown material.)
  2. Geometry goes through the landmark contract (landmarks/_common.py): a module such as
     landmarks/marston_interior.py with LANDMARKS entries listing "stages": ["marston"] builds a Kit and
     returns kit.parts("marston_interior", landmark="marston_interior") from build(ctx). Parts are
     {"name", "mesh", "material_slots", "collision", "visual"} (+ "landmark"); visual meshes carry
     "UVMap" (1.0 = one texture repeat) and the baked "Col" / "Alpha" colour attributes (FLOAT_COLOR,
     CORNER), which add_part keeps; collision parts use the COL materials (or palette names).
  3. Anchors: kit.anchors() -> {"<tag>.<name>": (x, y, z, facing_deg)} in map metres: door gaps, kiosk
     punch spots, elevator doors, stair tops, shelf tops, the light ring... for data/uf/<stage>_points.json.
  4. Lighting is baked when parts are built: Kit.parts(..., lighting=Lighting(...)); every ceiling_light /
     light_ring / light_grid prop adds its Light, so the default Lighting(kit.lights()) is usually right.
  5. The level stays inside s16: map metres are shifted by the stage centre in add_part; keep the interior
     within +-300 m of it (validate_level / export_hygiene check max_abs_vertex).

Conventions
-----------
  * Every builder returns a Prop in LOCAL coordinates: origin at the base centre on the floor (z = 0)
    unless the builder says otherwise (room_shell / slab / light_grid / window_band: corner or wall-plane
    origin); the prop's FRONT faces local +y (the side you approach / use it from).
  * Place it with kit.add(prop, x, y, z, facing_deg=compass) (0 = front faces north, 90 = east), or
    prop.placed(x, y, z, facing_deg) for a transformed copy. Local +x is the prop's right-hand side.
  * Materials are palette names: the int_* kit materials (vertex-lit), any stage_palette.MATERIALS name
    (normal-lit campus materials, e.g. "treeline" for a backdrop) and the collision materials
    'COL default', 'COL nocam' (camera passes through: the kit's default for furniture, so the gameplay
    camera floats through stacks and glass instead of snapping in front of Mario), 'COL notslip',
    'COL hangable'.
  * Collision is separate, low-poly and closed where Mario can touch it (boxes / wedges, open only at the
    floor they stand on, normals out). Visual meshes are free to be detailed and unclosed.
  * "once" materials (signs, screens, doors, windows) get explicit UVs; "tile" materials get world-aligned
    projected UVs at bake time (floors top-down, walls along the wall), so carpet and drywall run
    continuously across props.

SM64 numbers the defaults are sized against (game units / 100; see the constants below)
  Mario is 1.6 m tall with a 0.5 m wall radius: a top he can stand on next to a taller wall must be
  >= ~0.55 m deep; ceilings must clear 1.6 m. A single jump apexes ~2.2 m standing (~3.1 m running),
  ledge grabs reach ~2.4 m, double ~3.4 m, backflip / side flip / wall kick ~4.8 m. Floors steeper than
  38 deg slide (SURFACE_DEFAULT); the kit keeps stair ramps <= 30 deg on 'COL notslip'. Real stairs
  (7" riser, 11" tread = 32.5 deg) are close to that, so stairs stay 1:1-ish.
  Camera: the gameplay camera sits ~5-8 m behind Mario and 2-3 m up; real 2.7-3 m dropped ceilings
  and 0.9-1.1 m stack aisles are too tight. Use open atria / exposed slabs (ceiling = floor-to-floor),
  CAMERA_CEILING_M and AISLE_M, and record any deviation from 1:1 in the stage's notes.

API (all lengths in metres; every builder -> Prop)
---------------------------------------------------
  Core
    KitMesh()                 .poly(pts, mat, uvs=None, ao=None, tint=None, glow=False, normal_hint=None)
                              .box(x0, y0, z0, x1, y1, z1, mat, faces="+x-x+y-y+z", mats={face: mat},
                                   uvs={face: [(u, v) x 4]}), .wall(a2, b2, z0, z1, mat), .tris()
    Prop(kind)                .visual / .collision (KitMesh), .anchors, .lights, .info,
                              .placed(x, y, z, facing_deg), .merge(other, x, y, z, facing_deg, prefix),
                              .tris() -> {"visual", "collision"}, .parts(name, lighting, landmark)  [bpy]
    Kit()                     .add(prop, x, y, z, facing_deg, tag, group) -> placed Prop,
                              .lights(), .anchors(), .report(), .merged(group),
                              .parts(prefix, lighting=None, landmark=None, groups=None)  [bpy]
    Light(pos, radius, strength, color)    Lighting(lights, sky, ground, key, key_strength, gain)
    front_quad / back_quad / uv_rect / ONCE   correctly wound panels for "once" textures
    col_box / col_prism                       closed collision blocks (open bottom when standing)
  Architecture
    room_shell(width, depth, height, floor, wall, ceiling, openings=[{"wall": "n|e|s|w", "at": m,
               "w": m, "z0": m, "h": m, "kind": "door|gap|window|glass"}], ...)   corner origin
    slab(width, depth, thickness, holes=[(x0, y0, x1, y1)], top, bottom, edge)    corner origin, top z=0
    column(size, height, round=True)          window_band(length, sill, head, bay, view="painted|glass")
    stair_flight(rise, width, solid, lip, lip_visual)   stair_steps(rise) -> (risers, riser, tread)
    landing(width, depth)                     door_frame(width, height)
    switchback_stair(rise, width, gap, landing_depth)     straight_stair(rise, width, landing_depth)
    railing(points, height, infill="bars|glass|solid")    elevator(floors, width, depth, ...)
  Furniture
    bookshelf(length, height, depth, double, end_caps)    stack_range(rows, length, aisle, heights)
    study_table(length, width, chairs_per_side)           chair()   stool()   kick_stool()
    carrel_row(n)             computer_row(n, double)     study_room(width, depth, height, door_w)
    help_desk(length)         cafe_counter(length)        couch(length)        beanbag()
    book_cart()               kiosk()                     whiteboard(width, height)       monitor()
  Signs and lights
    poster(which)             sign(material, width, height, z, mount="wall|hanging|post")
    floor_sign(label)         ceiling_light()             light_grid(width, depth, spacing)
    light_ring(radius)        (the atrium fixture: walkable top, hangable underside)
  Blender (bpy imported lazily)
    to_bpy_mesh(kitmesh, name, lighting, collision)   link_parts(parts, mats, parent)
    preview_material(name)  (texture x baked vertex colour, emission; for previews without Fast64)
  Checks (pure Python)
    all_props() -> {label: Prop}   collision_issues(kitmesh, base_z)   uv_span_issues(kitmesh)
    selftest(): python -I tools/campus/interior_kit.py --selftest (materials, closed outward collision,
    UV spans, stair / shelf / door-gap / ring sizing against the SM64 numbers below)
  Every prop's info has its key sizes (top_z, door_gap, hole, rest_z = planes it stands on, ...).
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from stage_palette import INTERIOR_MATERIALS, MATERIALS  # noqa: E402

# ------------------------------------------------------------------ SM64 movement (metres)
MARIO_HEIGHT_M = 1.60      # hitbox height (160 units): every walkable floor needs this much headroom
MARIO_WALL_R_M = 0.50      # wall push radius 0.6 m above the feet (0.24 m at 0.3 m)
STEP_PROBE_M = 0.30        # the lower wall probe: a riser below 0.3 m is not a wall (stairs still get ramps)
JUMP_M = 2.2               # single jump apex standing (42 u/frame up, gravity 4); ~3.1 m at full run
LEDGE_GRAB_M = 2.4         # top of a wall a standing single jump still grabs
DOUBLE_JUMP_M = 3.4        # standing; ~4.5 m running
BACKFLIP_M = 4.8           # also side flip and wall kick apex
SLIDE_DEG = 38.0           # SURFACE_DEFAULT floors steeper than this slide (normal.y < 0.788)
STAIR_MAX_DEG = 30.0       # kit default for stair ramps ('COL notslip')
CAMERA_CEILING_M = 5.0     # recommended clear height where the gameplay camera follows Mario
AISLE_M = 1.8              # recommended stack aisle for the camera (real: 0.91 m ADA minimum, ~1.0-1.1 m)
S16_LIMIT_M = 327.67       # max |coordinate| after the stage-centre shift

# ------------------------------------------------------------------ real-world defaults (1:1)
REAL = {
    "stack_full_h": 2.29,      # 90" double-faced steel library shelving (7 shelves)
    "stack_mid_h": 1.68,       # 66"
    "stack_counter_h": 1.07,   # 42" counter-height range
    "stack_depth": 0.61,       # double-faced, 2 x 12" shelves
    "stack_section_w": 0.915,  # 36" sections
    "table_h": 0.76, "table_w": 0.91, "table_l": 1.83,
    "seat_h": 0.46, "counter_h": 1.07, "carrel_panel_h": 1.37, "carrel_w": 0.91,
    "riser_max": 0.178, "tread_min": 0.279, "stair_w": 1.52,
    "guard_h": 1.07,           # 42" guard rail (atria, landings)
    "door_w": 0.91, "door_h": 2.13, "elevator_door_w": 1.07, "elevator_door_h": 2.13,
    "floor_to_floor": 4.2,     # Marston (4 floors x 4.2 m = 16.8 m wings; towers to 22.5 m)
}

COL = "COL default"
COL_NOCAM = "COL nocam"
COL_NOTSLIP = "COL notslip"
COL_HANG = "COL hangable"
COL_NAMES = (COL, COL_NOCAM, COL_NOTSLIP, COL_HANG)

# automatic ambient occlusion (vertex colour multiplier) of KitMesh.poly when no ao is given
AO_STRENGTH = 0.30         # darkening at the floor contact line
AO_HEIGHT = 0.70           # ... fading out this far above it
AO_UNDERSIDE = 0.72        # faces looking down (table / shelf / slab undersides)

UV_SPAN_MAX = 12.0         # stage_geom.UV_SPAN_MAX: max texture repeats across one face


def known_material(name):
    return name in INTERIOR_MATERIALS or name in MATERIALS or name in COL_NAMES


def palette_entry(name):
    if name in INTERIOR_MATERIALS:
        return INTERIOR_MATERIALS[name]
    if name in MATERIALS:
        return MATERIALS[name]
    return {"tile_m": 1.0, "color": "#FF00FF", "kind": "opaque", "lit": "vertex", "map": "tile"}


# ------------------------------------------------------------------ small vector helpers
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    n = _len(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 1.0)


def newell(pts):
    """Newell normal of a planar polygon (area-weighted, not normalised)."""
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(pts, pts[1:] + pts[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def unit_normal(pts):
    return _unit(newell(pts))


def project_uv(pts, tile_m, n=None):
    """World-aligned planar UVs (landmarks/_common.project_uv): floors / ceilings top-down, walls u along the
    wall and v = z (texture upright), one repeat per tile_m, shifted by whole repeats to start near 0."""
    nx, ny, nz = n or newell(pts)
    t = max(tile_m, 1e-6)
    if abs(nz) >= max(abs(nx), abs(ny)) * 1.0001:
        uvs = [(p[0] / t, p[1] / t) for p in pts]
    else:
        L = math.hypot(nx, ny) or 1.0
        hx, hy = -ny / L, nx / L
        uvs = [((p[0] * hx + p[1] * hy) / t, p[2] / t) for p in pts]
    du = math.floor(min(u for u, _ in uvs) + 1e-9)
    dv = math.floor(min(v for _, v in uvs) + 1e-9)
    return [(u - du, v - dv) for u, v in uvs]


def uv_rect(u0, v0, u1, v1):
    """UVs for a quad given bottom-left, bottom-right, top-right, top-left (the kit's side-face order)."""
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


ONCE = uv_rect(0.0, 0.0, 1.0, 1.0)


def front_quad(x0, x1, y, z0, z1):
    """Vertical quad in the plane y facing +y, starting bottom-left as seen from +y (x1 is on the viewer's
    left): pair it with uv_rect / ONCE for an upright, unmirrored texture."""
    return [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)]


def back_quad(x0, x1, y, z0, z1):
    """Vertical quad in the plane y facing -y (bottom-left as seen from -y)."""
    return [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]


def _xform(facing_deg, ox, oy, oz):
    """Local -> map: local +y turns to compass facing_deg, local +x to its right, then translate."""
    f = math.radians(facing_deg)
    s, c = math.sin(f), math.cos(f)

    def tf(p):
        x, y, z = p
        return (ox + x * c + y * s, oy - x * s + y * c, oz + z)
    return tf


# ------------------------------------------------------------------ meshes
class Poly:
    __slots__ = ("pts", "mat", "uvs", "ao", "tint", "glow")

    def __init__(self, pts, mat, uvs, ao, tint, glow):
        self.pts, self.mat, self.uvs, self.ao, self.tint, self.glow = pts, mat, uvs, ao, tint, glow


def _auto_ao(pts, n, floor_z):
    if n[2] < -0.5:
        return [AO_UNDERSIDE] * len(pts)
    out = []
    for p in pts:
        h = p[2] - floor_z
        if n[2] > 0.5 and h < 0.02:
            out.append(1.0)                       # the floor itself
        else:
            out.append(1.0 - AO_STRENGTH * max(0.0, min(1.0, 1.0 - h / AO_HEIGHT)))
    return out


BOX_ALL = ("+x", "-x", "+y", "-y", "+z", "-z")


def _faces_arg(faces):
    if faces is None:
        return ("+x", "-x", "+y", "-y", "+z")
    if isinstance(faces, str):
        return tuple(faces[i:i + 2] for i in range(0, len(faces), 2))
    return tuple(faces)


def box_faces(x0, y0, z0, x1, y1, z1):
    """The six faces of an axis-aligned box, outward normals; side faces start bottom-left as seen from
    outside (so uv_rect / ONCE maps a texture upright and unmirrored on every side)."""
    return {
        "+z": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        "-z": [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
        "-y": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        "+y": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        "+x": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        "-x": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
    }


class KitMesh:
    """Polygons with palette material names, explicit or projected UVs and per-vertex AO / tint."""

    def __init__(self, floor_z=0.0, auto_ao=True):
        self.polys = []
        self.floor_z = floor_z
        self.auto_ao = auto_ao

    def poly(self, pts, mat, uvs=None, ao=None, tint=None, glow=False, normal_hint=None):
        if not known_material(mat):
            raise ValueError(f"unknown kit material {mat!r}")
        pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
        if len(pts) < 3:
            return None
        if uvs is not None:
            uvs = [(float(u), float(v)) for u, v in uvs]
        if isinstance(ao, (int, float)):
            ao = [float(ao)] * len(pts)
        if normal_hint is not None:
            n = newell(pts)
            if _dot(n, normal_hint) < 0:
                pts.reverse()
                uvs = list(reversed(uvs)) if uvs is not None else None
                ao = list(reversed(ao)) if ao is not None else None
        if _len(newell(pts)) < 1e-10:
            return None                            # degenerate
        if ao is None:
            ao = _auto_ao(pts, unit_normal(pts), self.floor_z) if self.auto_ao else [1.0] * len(pts)
        p = Poly(pts, mat, uvs, list(ao), tuple(tint) if tint is not None else None, bool(glow))
        self.polys.append(p)
        return p

    def quad(self, a, b, c, d, mat, **kw):
        return self.poly([a, b, c, d], mat, **kw)

    def box(self, x0, y0, z0, x1, y1, z1, mat, faces=None, mats=None, uvs=None, **kw):
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        fs = box_faces(x0, y0, z0, x1, y1, z1)
        for key in _faces_arg(faces):
            m = (mats or {}).get(key, mat)
            if m is None:
                continue
            self.poly(fs[key], m, uvs=(uvs or {}).get(key), **kw)

    def wall(self, a, b, z0, z1, mat, uvs=None, **kw):
        """Vertical quad from 2D point a to b; its normal points to the right of a -> b."""
        return self.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat, uvs=uvs, **kw)

    def prism(self, pts2, z0, z1, mat, top=None, bottom=None, **kw):
        """Extrude a counter-clockwise footprint: outward walls, optional caps."""
        if _signed_area(pts2) < 0:
            pts2 = list(reversed(pts2))
        for a, b in zip(pts2, pts2[1:] + pts2[:1]):
            self.wall(a, b, z0, z1, mat, **kw)
        if top:
            self.poly([(x, y, z1) for x, y in pts2], top, **kw)
        if bottom:
            self.poly([(x, y, z0) for x, y in reversed(pts2)], bottom, **kw)

    def extend(self, other):
        self.polys.extend(other.polys)
        return self

    def transformed(self, facing_deg=0.0, ox=0.0, oy=0.0, oz=0.0):
        tf = _xform(facing_deg, ox, oy, oz)
        out = KitMesh(self.floor_z + oz, self.auto_ao)
        for p in self.polys:
            out.polys.append(Poly([tf(v) for v in p.pts], p.mat, p.uvs, p.ao, p.tint, p.glow))
        return out

    def tris(self):
        return sum(len(p.pts) - 2 for p in self.polys)

    def materials(self):
        out = []
        for p in self.polys:
            if p.mat not in out:
                out.append(p.mat)
        return out

    def bounds(self):
        pts = [v for p in self.polys for v in p.pts]
        if not pts:
            return None
        return (tuple(min(v[i] for v in pts) for i in range(3)), tuple(max(v[i] for v in pts) for i in range(3)))


def _glow_last(km, n, mat):
    """Mark the faces of material `mat` among the last n polygons as glowing (screens, sign faces)."""
    for p in km.polys[-n:]:
        if p.mat == mat:
            p.glow = True


def _signed_area(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def col_box(km, x0, y0, z0, x1, y1, z1, mat=COL, bottom=False):
    """Closed collision box (no bottom face when it stands on a floor)."""
    km.box(x0, y0, z0, x1, y1, z1, mat, faces=BOX_ALL if bottom else None)


def col_prism(km, pts2, z0, z1, mat=COL, bottom=False):
    km.prism(pts2, z0, z1, mat, top=mat, bottom=mat if bottom else None)


# ------------------------------------------------------------------ lights
class Light:
    """Point light for the vertex-colour bake: adds strength * colour * max(0, n.L) * (1 - (d/radius)^2)^2."""

    def __init__(self, pos, radius=7.0, strength=0.38, color=(1.0, 0.97, 0.90)):
        self.pos = tuple(float(c) for c in pos)
        self.radius = float(radius)
        self.strength = float(strength)
        self.color = tuple(float(c) for c in color)

    def moved(self, tf):
        return Light(tf(self.pos), self.radius, self.strength, self.color)


class Lighting:
    """Vertex-colour bake: hemisphere ambient (sky above / ground below) + a soft key direction (so the
    four wall orientations read differently) + point lights, times the per-vertex AO and tint.
    Values are the N64 shade (sRGB, 0..1) that multiplies the texel."""

    def __init__(self, lights=(), sky=(0.70, 0.70, 0.72), ground=(0.50, 0.49, 0.48), key=(0.45, 0.62, 0.64),
                 key_strength=0.12, gain=1.0):
        self.lights = list(lights)
        self.sky, self.ground = tuple(sky), tuple(ground)
        self.key = _unit(key)
        self.key_strength = key_strength
        self.gain = gain
        self.cell = max([L.radius for L in self.lights] + [1.0])
        self.grid = {}
        for L in self.lights:
            k = (int(math.floor(L.pos[0] / self.cell)), int(math.floor(L.pos[1] / self.cell)),
                 int(math.floor(L.pos[2] / self.cell)))
            self.grid.setdefault(k, []).append(L)

    def _near(self, p):
        cx, cy, cz = (int(math.floor(p[i] / self.cell)) for i in range(3))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    yield from self.grid.get((cx + dx, cy + dy, cz + dz), ())

    def shade(self, p, n, ao=1.0, tint=None, glow=False):
        if glow:
            c = tint or (1.0, 1.0, 1.0)
            return tuple(max(0.0, min(1.0, x)) for x in c)
        t = 0.5 + 0.5 * n[2]
        c = [g + (s - g) * t for s, g in zip(self.sky, self.ground)]
        k = max(0.0, _dot(n, self.key)) * self.key_strength
        c = [x + k for x in c]
        for L in self._near(p):
            d = _sub(L.pos, p)
            dist = _len(d)
            if dist >= L.radius:
                continue
            ndl = 1.0 if dist < 1e-6 else _dot(n, d) / dist
            if ndl <= 0.0:
                continue
            fall = (1.0 - (dist / L.radius) ** 2) ** 2
            c = [x + L.strength * lc * ndl * fall for x, lc in zip(c, L.color)]
        c = [x * ao * self.gain for x in c]
        if tint:
            c = [x * tt for x, tt in zip(c, tint)]
        return tuple(max(0.0, min(1.0, x)) for x in c)


# ------------------------------------------------------------------ props and the kit
class Prop:
    """A built prop: visual + collision KitMesh, anchors {name: (x, y, z, facing_deg)}, lights, info."""

    def __init__(self, kind, **info):
        self.kind = kind
        self.visual = KitMesh()
        self.collision = KitMesh(auto_ao=False)
        self.anchors = {}
        self.lights = []
        self.info = dict(info)

    def anchor(self, name, x, y, z, facing_deg=0.0):
        self.anchors[name] = (float(x), float(y), float(z), float(facing_deg) % 360.0)

    def placed(self, x=0.0, y=0.0, z=0.0, facing_deg=0.0):
        tf = _xform(facing_deg, x, y, z)
        out = Prop(self.kind, **self.info)
        out.visual = self.visual.transformed(facing_deg, x, y, z)
        out.collision = self.collision.transformed(facing_deg, x, y, z)
        for k, (ax, ay, az, af) in self.anchors.items():
            px, py, pz = tf((ax, ay, az))
            out.anchors[k] = (px, py, pz, (af + facing_deg) % 360.0)
        out.lights = [L.moved(tf) for L in self.lights]
        out.info["placed"] = (float(x), float(y), float(z), float(facing_deg) % 360.0)
        return out

    def merge(self, other, x=0.0, y=0.0, z=0.0, facing_deg=0.0, prefix=None):
        """Add another prop (placed at x, y, z, facing_deg in THIS prop's frame); its anchors get prefix."""
        o = other.placed(x, y, z, facing_deg)
        self.visual.polys.extend(o.visual.polys)
        self.collision.polys.extend(o.collision.polys)
        for k, v in o.anchors.items():
            self.anchors[f"{prefix}.{k}" if prefix else k] = v
        self.lights.extend(o.lights)
        return self

    def tris(self):
        return {"visual": self.visual.tris(), "collision": self.collision.tris()}

    def parts(self, name, lighting=None, landmark=None):
        """Landmark-contract parts (needs bpy): [visual part, collision part] (empty meshes are skipped)."""
        lighting = lighting or Lighting(self.lights)
        out = []
        if self.visual.polys:
            me, slots = to_bpy_mesh(self.visual, f"{name} visual", lighting)
            out.append(_part(f"{name} visual", me, slots, False, True, landmark))
        if self.collision.polys:
            me, slots = to_bpy_mesh(self.collision, f"{name} collision", None, collision=True)
            out.append(_part(f"{name} collision", me, slots, True, False, landmark))
        return out


def _part(name, mesh, slots, collision, visual, landmark):
    p = {"name": name, "mesh": mesh, "material_slots": list(slots), "collision": bool(collision),
         "visual": bool(visual)}
    if landmark:
        p["landmark"] = landmark
    return p


class Kit:
    """A scene of placed props (map metres). kit.add(...) -> the placed prop; kit.parts(...) -> one visual and
    one collision part per group with the lighting baked."""

    def __init__(self):
        self.items = []          # (tag, group, placed prop)
        self.extra_lights = []

    def add(self, prop, x=0.0, y=0.0, z=0.0, facing_deg=0.0, tag=None, group="main"):
        p = prop.placed(x, y, z, facing_deg)
        if tag is None:
            n = sum(1 for t, _, q in self.items if q.kind == prop.kind)
            tag = f"{prop.kind}_{n + 1}"
        if any(t == tag for t, _, _ in self.items):
            raise ValueError(f"duplicate kit tag {tag!r}")
        self.items.append((tag, group, p))
        return p

    def light(self, light):
        self.extra_lights.append(light)

    def lights(self):
        return [L for _, _, p in self.items for L in p.lights] + list(self.extra_lights)

    def anchors(self):
        return {f"{t}.{k}": v for t, _, p in self.items for k, v in p.anchors.items()}

    def groups(self):
        out = []
        for _, g, _ in self.items:
            if g not in out:
                out.append(g)
        return out

    def merged(self, group=None):
        m = Prop("kit")
        for t, g, p in self.items:
            if group is None or g == group:
                m.visual.polys.extend(p.visual.polys)
                m.collision.polys.extend(p.collision.polys)
                m.lights.extend(p.lights)
                for k, v in p.anchors.items():
                    m.anchors[f"{t}.{k}"] = v
        return m

    def report(self):
        rows = []
        for t, g, p in self.items:
            rows.append({"tag": t, "kind": p.kind, "group": g, **p.tris()})
        tot = {"visual": sum(r["visual"] for r in rows), "collision": sum(r["collision"] for r in rows)}
        return {"items": rows, "total": tot}

    def parts(self, prefix, lighting=None, landmark=None, groups=None):
        lighting = lighting or Lighting(self.lights())
        out = []
        for g in (groups or self.groups()):
            out.extend(self.merged(g).parts(f"{prefix} {g}", lighting, landmark))
        return out


# ================================================================== architecture
def _grid_lines(a, b, step, extra=()):
    """Sorted cut positions from a to b: multiples of step (from a) plus extra cuts inside (a, b)."""
    xs = {round(a, 5), round(b, 5)}
    if step and step > 0:
        k = 1
        while a + k * step < b - 1e-6:
            xs.add(round(a + k * step, 5))
            k += 1
    for e in extra:
        if a + 1e-6 < e < b - 1e-6:
            xs.add(round(e, 5))
    return sorted(xs)


def room_shell(width, depth, height, floor="int_carpet", wall="int_drywall", ceiling="int_ceiling",
               openings=(), walls="nesw", floor_on=True, ceiling_on=True, base="int_plastic", base_h=0.10,
               wall_t=0.25, light_grid=3.0, cell=20.48, col_floor=True, col_walls=True, col_ceiling=True,
               wall_mats=None, window_frame="int_metal", window_bay=1.5):
    """Rectangular room seen from inside. CORNER origin: x 0..width, y 0..depth, floor z = 0, ceiling z =
    height. Walls face inward: "s" (y = 0), "n" (y = depth), "w" (x = 0), "e" (x = width).
    openings: [{"wall": "s", "at": centre along the wall (x for n / s, y for e / w), "w": width,
                "z0": sill (0 for doors), "h": opening height, "kind": "door" | "gap" | "window" | "glass"}]
      door / gap  : a hole in the wall and its collision (jamb returns wall_t deep);
      window      : painted view of campus (int_window) recessed wall_t, collision stays closed;
      glass       : translucent int_glass pane (the level's skybox shows through), collision closed.
    Visual floors / ceilings / walls are subdivided every light_grid m so the baked lights and corner AO
    read; collision uses <= cell m pieces on a shared grid (no T-junctions inside one surface).
    wall_mats: {"n": "int_wall_blue", ...} per-wall material."""
    P = Prop("room_shell", width=width, depth=depth, height=height, col_closed=False)
    V, C = P.visual, P.collision
    W, D, H = float(width), float(depth), float(height)
    sides = {
        "s": ((0.0, 0.0), (W, 0.0)),        # walking a -> b keeps the inside (normal) on the right?
        "e": ((W, 0.0), (W, D)),
        "n": ((W, D), (0.0, D)),
        "w": ((0.0, D), (0.0, 0.0)),
    }
    # inward normals need the room on the RIGHT of a -> b: reverse the CCW outline
    sides = {k: (b, a) for k, (a, b) in sides.items()}
    for key in "nesw":
        if key not in walls:
            continue
        a, b = sides[key]
        L = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        ops = []
        for o in openings:
            if o.get("wall") != key:
                continue
            along = float(o["at"])
            # "at" is measured as x (n / s) or y (e / w); convert to distance from a
            s_pos = (along - a[0]) * ux if key in "ns" else (along - a[1]) * uy
            ops.append(dict(o, s0=s_pos - o["w"] / 2.0, s1=s_pos + o["w"] / 2.0, z0=float(o.get("z0", 0.0)),
                            z1=float(o.get("z0", 0.0)) + float(o["h"])))
        mat = (wall_mats or {}).get(key, wall)

        def at(s, a=a, ux=ux, uy=uy):
            return (a[0] + ux * s, a[1] + uy * s)
        # ---- visual: grid cells, skipping opening rectangles
        us = _grid_lines(0.0, L, light_grid, [v for o in ops for v in (o["s0"], o["s1"])])
        zs = _grid_lines(0.0, H, light_grid, [base_h, min(H, 0.8)] + [v for o in ops for v in (o["z0"], o["z1"])])
        for i in range(len(us) - 1):
            for j in range(len(zs) - 1):
                s0, s1, z0, z1 = us[i], us[i + 1], zs[j], zs[j + 1]
                sm, zm = (s0 + s1) / 2, (z0 + z1) / 2
                if any(o["s0"] < sm < o["s1"] and o["z0"] < zm < o["z1"] for o in ops):
                    continue
                m = base if (base and z1 <= base_h + 1e-6) else mat

                def ao(s, z):
                    k = 1.0 - 0.30 * max(0.0, 1.0 - z / 0.9)            # floor line
                    k *= 1.0 - 0.10 * max(0.0, 1.0 - (H - z) / 0.8)      # ceiling line
                    k *= 1.0 - 0.12 * max(0.0, 1.0 - min(s, L - s) / 0.9)  # corners
                    return k
                V.wall(at(s0), at(s1), z0, z1, m, ao=[ao(s0, z0), ao(s1, z0), ao(s1, z1), ao(s0, z1)])
        # ---- openings: jamb returns + window panes
        nx, ny = uy, -ux                                    # inward normal (right of a -> b) ... outward = -n
        for o in ops:
            out_x, out_y = -nx * wall_t, -ny * wall_t        # recess goes outward
            p0, p1 = at(o["s0"]), at(o["s1"])
            q0, q1 = (p0[0] + out_x, p0[1] + out_y), (p1[0] + out_x, p1[1] + out_y)
            jm = mat if o["kind"] in ("door", "gap") else (window_frame or mat)
            V.wall(p0, q0, o["z0"], o["z1"], jm, ao=0.85)                     # jamb at s0 (faces +u)
            V.wall(q1, p1, o["z0"], o["z1"], jm, ao=0.85)                     # jamb at s1 (faces -u)
            V.poly([(q0[0], q0[1], o["z1"]), (p0[0], p0[1], o["z1"]), (p1[0], p1[1], o["z1"]),
                    (q1[0], q1[1], o["z1"])], jm, ao=0.8, normal_hint=(0, 0, -1))   # head
            if o["z0"] > 0.01:
                V.poly([(p0[0], p0[1], o["z0"]), (q0[0], q0[1], o["z0"]), (q1[0], q1[1], o["z0"]),
                        (p1[0], p1[1], o["z0"])], window_frame or mat, normal_hint=(0, 0, 1))   # sill
            if o["kind"] in ("window", "glass"):
                span = o["s1"] - o["s0"]
                n_bays = max(1, int(round(span / window_bay)))
                for k in range(n_bays):
                    b0 = (q0[0] + (q1[0] - q0[0]) * k / n_bays, q0[1] + (q1[1] - q0[1]) * k / n_bays)
                    b1 = (q0[0] + (q1[0] - q0[0]) * (k + 1) / n_bays, q0[1] + (q1[1] - q0[1]) * (k + 1) / n_bays)
                    if o["kind"] == "window":
                        V.wall(b0, b1, o["z0"], o["z1"], "int_window", uvs=ONCE, ao=1.0)
                    else:
                        V.wall(b0, b1, o["z0"], o["z1"], "int_glass", ao=1.0)
                    if k:                                                      # mullion
                        mx, my = b0
                        tx, ty = ux * 0.04, uy * 0.04
                        ix, iy = nx * 0.05, ny * 0.05
                        V.wall((mx - tx + ix, my - ty + iy), (mx + tx + ix, my + ty + iy), o["z0"], o["z1"],
                               window_frame or mat, ao=0.9)
        # ---- collision: inward wall pieces, door / gap holes only
        if col_walls:
            holes = [o for o in ops if o["kind"] in ("door", "gap")]
            cus = _grid_lines(0.0, L, cell, [v for o in holes for v in (o["s0"], o["s1"])])
            czs = _grid_lines(0.0, H, 0.0, [o["z1"] for o in holes] + [o["z0"] for o in holes])
            for i in range(len(cus) - 1):
                for j in range(len(czs) - 1):
                    s0, s1, z0, z1 = cus[i], cus[i + 1], czs[j], czs[j + 1]
                    sm, zm = (s0 + s1) / 2, (z0 + z1) / 2
                    if any(o["s0"] < sm < o["s1"] and o["z0"] < zm < o["z1"] for o in holes):
                        continue
                    C.wall(at(s0), at(s1), z0, z1, COL)
            for o in holes:                                                    # jamb returns
                p0, p1 = at(o["s0"]), at(o["s1"])
                out_x, out_y = -nx * wall_t, -ny * wall_t
                q0, q1 = (p0[0] + out_x, p0[1] + out_y), (p1[0] + out_x, p1[1] + out_y)
                C.wall(p0, q0, o["z0"], o["z1"], COL)
                C.wall(q1, p1, o["z0"], o["z1"], COL)
                if o["z1"] < H - 1e-3:
                    C.poly([(q0[0], q0[1], o["z1"]), (p0[0], p0[1], o["z1"]), (p1[0], p1[1], o["z1"]),
                            (q1[0], q1[1], o["z1"])], COL, normal_hint=(0, 0, -1))
                if o["z0"] > 1e-3:
                    C.poly([(p0[0], p0[1], o["z0"]), (q0[0], q0[1], o["z0"]), (q1[0], q1[1], o["z0"]),
                            (p1[0], p1[1], o["z0"])], COL, normal_hint=(0, 0, 1))
    # ---- floor and ceiling
    xs, ys = _grid_lines(0.0, W, light_grid), _grid_lines(0.0, D, light_grid)

    def edge_ao(x, y, k):
        d = min(x, W - x, y, D - y)
        return 1.0 - k * max(0.0, 1.0 - d / 1.0)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            if floor_on and floor:
                V.poly([(x, y, 0.0) for x, y in corners], floor, ao=[edge_ao(x, y, 0.18) for x, y in corners])
            if ceiling_on and ceiling:
                rc = list(reversed(corners))
                V.poly([(x, y, H) for x, y in rc], ceiling, ao=[0.92 * edge_ao(x, y, 0.15) for x, y in rc])
    cxs, cys = _grid_lines(0.0, W, cell), _grid_lines(0.0, D, cell)
    for i in range(len(cxs) - 1):
        for j in range(len(cys) - 1):
            x0, x1, y0, y1 = cxs[i], cxs[i + 1], cys[j], cys[j + 1]
            if floor_on and col_floor:
                C.poly([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)], COL)
            if ceiling_on and col_ceiling:
                C.poly([(x0, y0, H), (x0, y1, H), (x1, y1, H), (x1, y0, H)], COL)
    P.anchor("centre", W / 2, D / 2, 0.0)
    for o in openings:
        if o.get("kind") in ("door", "gap"):
            k = o["wall"]
            at_ = float(o["at"])
            pos = {"s": (at_, 0.0, 180.0), "n": (at_, D, 0.0), "w": (0.0, at_, 270.0), "e": (W, at_, 90.0)}[k]
            P.anchor(f"opening_{k}_{at_:g}", pos[0], pos[1], float(o.get("z0", 0.0)), pos[2])
    return P


def slab(width, depth, thickness=0.30, holes=(), top="int_carpet", bottom="int_ceiling", edge="int_drywall",
         light_grid=3.0, cell=20.48, outer_edges=True, col_bottom=True, col_edges=True, ao_sides="", ao_k=0.18):
    """Floor plate with rectangular holes (atria, stairwells, shafts). CORNER origin x 0..width,
    y 0..depth; TOP at z = 0 (place it at the floor height), bottom at -thickness (the ceiling below).
    holes: [(x0, y0, x1, y1)] local. Pieces sit on one rectilinear grid (cell lines + hole edges), so
    neighbouring collision pieces share whole edges. Hole edges get vertical faces (visual + collision).
    bottom / edge None: no visual underside / edges (a floor laid on the ground: also pass col_bottom /
    col_edges False). ao_sides: the outline sides ("n" y = depth, "e" x = width, "s", "w") that meet a
    wall: the top darkens ao_k toward them (the corner AO room_shell gives its own floor)."""
    P = Prop("slab", width=width, depth=depth, thickness=thickness, holes=[tuple(h) for h in holes],
             col_closed=False)
    V, C = P.visual, P.collision
    W, D, T = float(width), float(depth), float(thickness)
    hx = [v for h in holes for v in (h[0], h[2])]
    hy = [v for h in holes for v in (h[1], h[3])]

    def solid(x, y):
        if not (0.0 < x < W and 0.0 < y < D):
            return False
        return not any(h[0] < x < h[2] and h[1] < y < h[3] for h in holes)
    cxs, cys = _grid_lines(0.0, W, cell, hx), _grid_lines(0.0, D, cell, hy)

    def wall_ao(x, y):
        d = min([v for k, v in (("w", x), ("e", W - x), ("s", y), ("n", D - y)) if k in ao_sides] + [9.0])
        return 1.0 - ao_k * max(0.0, 1.0 - d / 1.0)
    fxs = sorted(set(cxs) | set(_grid_lines(0.0, W, light_grid)))
    fys = sorted(set(cys) | set(_grid_lines(0.0, D, light_grid)))
    for i in range(len(fxs) - 1):
        for j in range(len(fys) - 1):
            x0, x1, y0, y1 = fxs[i], fxs[i + 1], fys[j], fys[j + 1]
            if not solid((x0 + x1) / 2, (y0 + y1) / 2):
                continue
            corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            V.poly([(x, y, 0.0) for x, y in corners], top, ao=[wall_ao(x, y) for x, y in corners])
            if bottom:
                V.poly([(x0, y0, -T), (x0, y1, -T), (x1, y1, -T), (x1, y0, -T)], bottom, ao=0.9)
    for i in range(len(cxs) - 1):
        for j in range(len(cys) - 1):
            x0, x1, y0, y1 = cxs[i], cxs[i + 1], cys[j], cys[j + 1]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            if not solid(mx, my):
                continue
            C.poly([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)], COL)
            if col_bottom:
                C.poly([(x0, y0, -T), (x0, y1, -T), (x1, y1, -T), (x1, y0, -T)], COL)
            # edges toward non-solid neighbours (holes; the outline when outer_edges)
            for (ax, ay, bx, by, px, py) in ((x0, y0, x1, y0, mx, y0 - 1e-3), (x1, y0, x1, y1, x1 + 1e-3, my),
                                             (x1, y1, x0, y1, mx, y1 + 1e-3), (x0, y1, x0, y0, x0 - 1e-3, my)):
                if solid(px, py):
                    continue
                outside = not (0.0 < px < W and 0.0 < py < D)
                if outside and not outer_edges:
                    continue
                if edge:
                    V.wall((ax, ay), (bx, by), -T, 0.0, edge, ao=0.9)
                if col_edges:
                    C.wall((ax, ay), (bx, by), -T, 0.0, COL)
    for k, h in enumerate(holes):
        P.anchor(f"hole_{k}", (h[0] + h[2]) / 2, (h[1] + h[3]) / 2, 0.0)
    return P


def column(size=0.6, height=4.2, round_=True, segments=8, mat="int_drywall", base_mat="int_plastic",
           base_h=0.10, cam=True):
    """Free-standing column, base centre origin. Round (n-gon) or square; collision is the same prism."""
    P = Prop("column", size=size, height=height)
    r = size / 2.0
    if round_:
        pts = [(r * math.cos(2 * math.pi * (k + 0.5) / segments), r * math.sin(2 * math.pi * (k + 0.5) / segments))
               for k in range(segments)]
    else:
        pts = [(-r, -r), (r, -r), (r, r), (-r, r)]
    P.visual.prism(pts, 0.0, base_h, base_mat)
    P.visual.prism([(x * 0.985, y * 0.985) for x, y in pts], base_h, height, mat)
    col_prism(P.collision, pts, 0.0, height, COL if cam else COL_NOCAM)
    return P


def window_band(length, sill=0.9, head=2.7, bay=1.5, depth=0.2, view="painted", frame="int_metal",
                stool=True, col=False):
    """Ribbon window set into a wall. Local: the wall plane is y = 0, the room is +y, the band runs
    x 0..length, z sill..head; the pane sits depth m behind the wall plane. view "painted" = int_window
    (a painted campus view, one texture per bay), "glass" = translucent int_glass (skybox behind).
    stool: a 0.2 m sill ledge inside. col: also a collision wall over the band (room_shell already has one)."""
    P = Prop("window_band", length=length, sill=sill, head=head, col_closed=False)
    V = P.visual
    n = max(1, int(round(length / bay)))
    for k in range(n):
        x0, x1 = length * k / n, length * (k + 1) / n
        if view == "painted":
            V.poly(front_quad(x0, x1, -depth, sill, head), "int_window", uvs=ONCE, ao=1.0)
        else:
            V.poly(front_quad(x0, x1, -depth, sill, head), "int_glass", ao=1.0)
        if k:
            V.box(x0 - 0.04, -depth, sill, x0 + 0.04, -depth + 0.05, head, frame, faces="+y+x-x", ao=0.9)
    V.poly([(0, 0, sill), (0, -depth, sill), (0, -depth, head), (0, 0, head)], frame, normal_hint=(1, 0, 0), ao=0.85)
    V.poly([(length, -depth, sill), (length, 0, sill), (length, 0, head), (length, -depth, head)], frame,
           normal_hint=(-1, 0, 0), ao=0.85)
    V.poly([(0, -depth, head), (length, -depth, head), (length, 0, head), (0, 0, head)], frame,
           normal_hint=(0, 0, -1), ao=0.8)
    V.poly([(0, -depth, sill), (length, -depth, sill), (length, 0, sill), (0, 0, sill)], frame,
           normal_hint=(0, 0, 1))
    if stool:
        V.box(-0.05, 0.0, sill - 0.04, length + 0.05, 0.2, sill, "int_stone", faces="+y+z-z+x-x")
    if col:
        P.collision.wall((length, 0.0), (0.0, 0.0), sill, head, COL)
    return P


def door_frame(width=REAL["door_w"], height=REAL["door_h"], depth=0.25, trim=0.08, mat="int_wood_dark"):
    """Trim around a door opening. Local: the opening is x -width/2..width/2, z 0..height in the wall plane
    y = 0; trim stands 2 cm proud on the room side (+y). Visual only."""
    P = Prop("door_frame", width=width, height=height)
    hw = width / 2.0
    for sx in (-1, 1):
        x0, x1 = (hw, hw + trim) if sx > 0 else (-hw - trim, -hw)
        P.visual.box(x0, -0.02, 0.0, x1, 0.02, height + trim, mat, faces="+y+x-x+z")
    P.visual.box(-hw - trim, -0.02, height, hw + trim, 0.02, height + trim, mat, faces="+y+z-z")
    P.anchor("opening", 0.0, 0.0, 0.0)
    return P


# ------------------------------------------------------------------ stairs
def stair_steps(rise, max_deg=STAIR_MAX_DEG, riser_max=REAL["riser_max"], tread_min=REAL["tread_min"]):
    """(n risers, riser m, tread m) for a flight: risers <= riser_max, and the collision ramp from half a
    tread before the first riser to the last nosing no steeper than max_deg."""
    n = max(1, int(math.ceil(rise / riser_max - 1e-9)))
    r = rise / n
    t = max(tread_min, rise / ((n - 0.5) * math.tan(math.radians(max_deg))))
    return n, r, t


def stair_flight(rise=2.1, width=REAL["stair_w"], max_deg=STAIR_MAX_DEG, lip=0.30, lip_visual=True, solid=True,
                 thickness=0.22, tread_mat="int_stair", side_mat="int_drywall", soffit_mat="int_drywall",
                 col_mat=COL_NOTSLIP, rails=(), rail_kw=None):
    """One straight flight. Local: x -width/2..width/2, the first riser at y = 0, rising toward +y (front =
    the way up); z 0..rise. Visual: real risers and treads (<= 0.178 m x >= 0.279 m). Collision: one ramp
    from half a tread before the first riser to the last nosing (<= max_deg, 'COL notslip'), a flat lip
    lip m past the last nosing (overlap it with the landing / floor above), closed sides and back.
    solid=True: a wedge down to z = 0; False: a slab of `thickness` with a soffit (walk under it).
    rails: ("l", "r") railings along those sides. lip_visual: how far the VISUAL top tread runs past the
    last nosing (True = lip, False = 0 when a landing / slab provides the arrival floor, or metres)."""
    n, r, t = stair_steps(rise, max_deg)
    P = Prop("stair_flight", rise=rise, width=width, risers=n, riser=r, tread=t,
             ramp_deg=math.degrees(math.atan2(rise, (n - 0.5) * t)), col_closed=True)
    V, C = P.visual, P.collision
    hw = width / 2.0
    Y1 = (n - 1) * t                  # last nosing (arrival)
    Ytop = Y1 + lip
    lv = lip if lip_visual is True else (0.0 if lip_visual is False else float(lip_visual))
    Yv = Y1 + min(lv, lip)            # where the visual flight ends
    s = rise / (Y1 + t / 2.0)         # ramp slope
    Tv = thickness * math.sqrt(1 + s * s)

    def soffit_z(y):
        if solid:
            return 0.0
        return min(rise - Tv, max(0.0, rise * (y + t / 2.0) / (Y1 + t / 2.0) - Tv))
    for k in range(1, n + 1):
        y0, z0, z1 = (k - 1) * t, (k - 1) * r, k * r
        V.poly([(-hw, y0, z0), (hw, y0, z0), (hw, y0, z1), (-hw, y0, z1)], tread_mat,
               uvs=[(0, 0.15), (width, 0.15), (width, 0.75), (0, 0.75)])
        y1 = k * t if k < n else Yv
        if y1 - y0 > 1e-4:
            vb = 1.0 - (y1 - y0) / t if k < n else 0.1
            V.poly([(-hw, y0, z1), (hw, y0, z1), (hw, y1, z1), (-hw, y1, z1)], tread_mat,
                   uvs=[(0, 1.0), (width, 1.0), (width, max(vb, 0.0)), (0, max(vb, 0.0))], ao=1.0)
            for sx in (-1, 1):
                pts = [(sx * hw, y0, soffit_z(y0)), (sx * hw, y1, soffit_z(y1)), (sx * hw, y1, z1), (sx * hw, y0, z1)]
                V.poly(pts, side_mat, normal_hint=(sx, 0, 0))
    if not solid:
        ya = max(0.0, -t / 2.0 + Tv / s)
        V.poly([(-hw, ya, 0.0), (-hw, Y1, rise - Tv), (hw, Y1, rise - Tv), (hw, ya, 0.0)], soffit_mat,
               normal_hint=(0, 0, -1))
        if ya > 1e-4:     # flat underside from the first riser to where the soffit leaves the floor line
            V.poly([(-hw, 0.0, 0.0), (-hw, ya, 0.0), (hw, ya, 0.0), (hw, 0.0, 0.0)], soffit_mat,
                   normal_hint=(0, 0, -1))
        if Yv > Y1 + 1e-4:
            V.poly([(-hw, Y1, rise - Tv), (-hw, Yv, rise - Tv), (hw, Yv, rise - Tv), (hw, Y1, rise - Tv)], soffit_mat,
                   normal_hint=(0, 0, -1))
    V.poly([(hw, Yv, soffit_z(Yv)), (-hw, Yv, soffit_z(Yv)), (-hw, Yv, rise), (hw, Yv, rise)],
           side_mat, normal_hint=(0, 1, 0))
    # ---- collision
    y_start = -t / 2.0
    C.poly([(-hw, y_start, 0.0), (hw, y_start, 0.0), (hw, Y1, rise), (-hw, Y1, rise)], col_mat, normal_hint=(0, -1, 1))
    C.poly([(-hw, Y1, rise), (hw, Y1, rise), (hw, Ytop, rise), (-hw, Ytop, rise)], col_mat, normal_hint=(0, 0, 1))
    if solid:
        for sx in (-1, 1):
            C.poly([(sx * hw, y_start, 0.0), (sx * hw, Ytop, 0.0), (sx * hw, Ytop, rise), (sx * hw, Y1, rise)], COL,
                   normal_hint=(sx, 0, 0))
        C.poly([(hw, Ytop, 0.0), (-hw, Ytop, 0.0), (-hw, Ytop, rise), (hw, Ytop, rise)], COL, normal_hint=(0, 1, 0))
    else:
        ya = -t / 2.0 + Tv / s
        bot = [(ya, 0.0), (Y1, rise - Tv), (Ytop, rise - Tv)]
        C.poly([(-hw, ya, 0.0), (-hw, Y1, rise - Tv), (hw, Y1, rise - Tv), (hw, ya, 0.0)], COL, normal_hint=(0, 0, -1))
        if ya > 1e-4:     # closes the bottom past the first riser (a flight hanging off a landing edge);
            # before it (y < 0) the flight rests on the landing: no ceiling coplanar with that floor
            C.poly([(-hw, 0.0, 0.0), (-hw, ya, 0.0), (hw, ya, 0.0), (hw, 0.0, 0.0)], COL, normal_hint=(0, 0, -1))
        C.poly([(-hw, Y1, rise - Tv), (-hw, Ytop, rise - Tv), (hw, Ytop, rise - Tv), (hw, Y1, rise - Tv)], COL,
               normal_hint=(0, 0, -1))
        for sx in (-1, 1):
            C.poly([(sx * hw, y_start, 0.0)] + ([(sx * hw, 0.0, 0.0)] if ya > 1e-4 else []) +
                   [(sx * hw, y, z) for y, z in bot] +
                   [(sx * hw, Ytop, rise), (sx * hw, Y1, rise)], COL, normal_hint=(sx, 0, 0))
        C.poly([(hw, Ytop, rise - Tv), (-hw, Ytop, rise - Tv), (-hw, Ytop, rise), (hw, Ytop, rise)], COL,
               normal_hint=(0, 1, 0))
        P.info["col_closed"] = True
    for side in rails:
        sx = -1 if side == "l" else 1
        x = sx * (hw - 0.05)
        rp = railing([(x, -t / 2.0, 0.0), (x, Y1, rise), (x, Ytop, rise)], **(rail_kw or {}))
        P.merge(rp)
    P.anchor("bottom", 0.0, -0.8, 0.0, 0.0)
    P.anchor("top", 0.0, Ytop, rise, 0.0)
    P.info.update(run=Ytop, top_nosing_y=Y1)
    return P


def landing(width, depth, thickness=0.22, top="int_stair", edge="int_drywall", bottom="int_drywall", col=COL):
    """Stair landing / small platform. Local: x -width/2..width/2, y 0..depth, TOP at z = 0 (place it at
    its height); a closed box down to -thickness."""
    P = Prop("landing", width=width, depth=depth, col_closed=True)
    hw = width / 2.0
    P.visual.box(-hw, 0.0, -thickness, hw, depth, 0.0, edge, faces=BOX_ALL,
                 mats={"+z": top, "-z": bottom},
                 uvs={"+z": [(0, 0.1), (width, 0.1), (width, 0.6), (0, 0.6)]} if top == "int_stair" else None)
    col_box(P.collision, -hw, 0.0, -thickness, hw, depth, 0.0, col, bottom=True)
    P.anchor("centre", 0.0, depth / 2.0, 0.0)
    return P


def switchback_stair(rise=REAL["floor_to_floor"], width=REAL["stair_w"], gap=0.20, landing_depth=None,
                     max_deg=STAIR_MAX_DEG, solid_first=True, rails=True, rail_kw=None):
    """Two flights and a half landing (U stair). Local: flight 1 on the west (x < 0) starts at y = 0 rising
    north to rise / 2; the landing spans the full width at the far end; flight 2 on the east comes back
    south and arrives at y ~ 0, z = rise (walk out southward: the upper floor must be at y < 0 there).
    info["hole"]: the (x0, y0, x1, y1) opening the upper slab needs over the stair: it starts 0.3 m south
    of the arrival nosing, where flight 2's visual lip ends (its collision lip runs 0.3 m further, under
    the slab, so the two decks overlap)."""
    W = 2 * width + gap
    ld = landing_depth or max(width, 1.2)
    f1 = stair_flight(rise / 2.0, width, max_deg, lip=0.3, lip_visual=False, solid=solid_first)
    Y1 = f1.info["top_nosing_y"]
    P = Prop("switchback_stair", rise=rise, width=W, length=Y1 + ld, col_closed=True)
    x1c, x2c = -W / 2 + width / 2, W / 2 - width / 2
    P.merge(f1, x1c, 0.0, 0.0, 0.0, prefix="flight1")
    P.merge(landing(W, ld), 0.0, Y1, rise / 2.0, 0.0, prefix="landing")
    f2 = stair_flight(rise / 2.0, width, max_deg, lip=0.6, lip_visual=0.3, solid=False)
    P.merge(f2, x2c, Y1, rise / 2.0, 180.0, prefix="flight2")
    if rails:
        kw = dict(rail_kw or {})
        n, r, t = stair_steps(rise / 2.0, max_deg)
        xi1, xi2 = x1c + width / 2 - 0.05, x2c - width / 2 + 0.05
        P.merge(railing([(xi1, -t / 2, 0.0), (xi1, Y1, rise / 2.0)], **kw))
        P.merge(railing([(xi2, Y1, rise / 2.0), (xi2, 0.0, rise)], **kw))
    P.anchor("bottom", x1c, -0.8, 0.0, 0.0)
    P.anchor("landing", 0.0, Y1 + ld / 2.0, rise / 2.0, 0.0)
    P.anchor("top", x2c, -0.8, rise, 180.0)
    P.info["hole"] = (-W / 2, -0.3, W / 2, Y1 + ld)
    P.info["rest_z"] = [rise / 2.0]          # flight 2 stands on the landing (open bottom there)
    return P


def straight_stair(rise=REAL["floor_to_floor"], width=REAL["stair_w"], landing_depth=1.5, max_deg=STAIR_MAX_DEG,
                   rails=("l", "r"), solid=True, rail_kw=None, top_lip_visual=True):
    """Two flights in line with a mid landing. Local: starts at y = 0 rising north; the last nosing is at
    y = info["run"], z = rise: start the upper floor there (the collision lip overlaps it 0.3 m; pass
    top_lip_visual=False, or a few cm, when that floor's own surface should show)."""
    f1 = stair_flight(rise / 2.0, width, max_deg, lip=0.3, lip_visual=False, solid=solid, rails=rails,
                      rail_kw=rail_kw)
    Y1 = f1.info["top_nosing_y"]
    f2 = stair_flight(rise / 2.0, width, max_deg, lip=0.3, lip_visual=top_lip_visual, solid=solid, rails=rails,
                      rail_kw=rail_kw)
    P = Prop("straight_stair", rise=rise, width=width, col_closed=True)
    P.merge(f1, 0.0, 0.0, 0.0, 0.0, prefix="flight1")
    if solid:
        lp = Prop("landing_block", col_closed=True)
        hw = width / 2.0
        lp.visual.box(-hw, 0.0, 0.0, hw, landing_depth, rise / 2.0, "int_drywall",
                      mats={"+z": "int_stair"}, uvs={"+z": [(0, 0.1), (width, 0.1), (width, 0.6), (0, 0.6)]})
        col_box(lp.collision, -hw, 0.0, 0.0, hw, landing_depth, rise / 2.0, COL_NOTSLIP)
        P.merge(lp, 0.0, Y1, 0.0, 0.0, prefix="landing")
    else:
        P.merge(landing(width, landing_depth), 0.0, Y1, rise / 2.0, 0.0, prefix="landing")
    y2 = Y1 + landing_depth
    P.merge(f2, 0.0, y2, rise / 2.0, 0.0, prefix="flight2")
    run = y2 + f2.info["run"]
    P.anchor("bottom", 0.0, -0.8, 0.0, 0.0)
    P.anchor("landing", 0.0, Y1 + landing_depth / 2, rise / 2.0, 0.0)
    P.anchor("top", 0.0, run + 0.5, rise, 0.0)
    P.info.update(run=y2 + f2.info["top_nosing_y"], arrival_y=run, rest_z=[rise / 2.0])
    return P


def railing(points, height=REAL["guard_h"], infill="bars", post_every=1.5, rail_mat="int_metal", col=True,
            col_height=None, cam=False, col_t=0.10):
    """Guard rail along a polyline of (x, y) or (x, y, z) points (z follows stairs). Top rail, posts and an
    infill: "bars" (cut-out int_rail_bars, 12.5 cm balusters), "glass" (int_glass) or "solid" (a half
    wall). Collision: a thin wall per segment, col_height tall (default = height; raise it to keep players
    from vaulting into an atrium). cam=False: 'COL nocam'."""
    P = Prop("railing", height=height, col_closed=True)
    V, C = P.visual, P.collision
    pts = [(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in points]
    ch = col_height or height
    cm = COL if cam else COL_NOCAM

    def post(x, y, z):
        V.box(x - 0.03, y - 0.03, z, x + 0.03, y + 0.03, z + height, rail_mat, faces="+x-x+y-y+z")
    post(*pts[0])
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-4:
            continue
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        sx, sy = -dy, dx
        npost = max(1, int(math.ceil(L / post_every)))
        for k in range(1, npost + 1):
            f = k / npost
            post(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)
        hw = 0.035
        za, zb = a[2] + height, b[2] + height
        A = [(a[0] + sx * hw, a[1] + sy * hw), (a[0] - sx * hw, a[1] - sy * hw)]
        B = [(b[0] + sx * hw, b[1] + sy * hw), (b[0] - sx * hw, b[1] - sy * hw)]
        V.poly([(A[0][0], A[0][1], za), (A[1][0], A[1][1], za), (B[1][0], B[1][1], zb), (B[0][0], B[0][1], zb)],
               rail_mat, normal_hint=(0, 0, 1))
        for i, sgn in ((0, 1), (1, -1)):
            V.poly([(A[i][0], A[i][1], za - 0.05), (B[i][0], B[i][1], zb - 0.05), (B[i][0], B[i][1], zb),
                    (A[i][0], A[i][1], za)], rail_mat, normal_hint=(sx * sgn, sy * sgn, 0))
        V.poly([(A[0][0], A[0][1], za - 0.05), (A[1][0], A[1][1], za - 0.05), (B[1][0], B[1][1], zb - 0.05),
                (B[0][0], B[0][1], zb - 0.05)], rail_mat, normal_hint=(0, 0, -1))
        lo, hi = 0.05, height - 0.05
        quad = [(a[0], a[1], a[2] + lo), (b[0], b[1], b[2] + lo), (b[0], b[1], b[2] + hi), (a[0], a[1], a[2] + hi)]
        if infill == "bars":
            V.poly(quad, "int_rail_bars", uvs=[(0, 0.0), (L, 0.0), (L, hi - lo), (0, hi - lo)], ao=1.0)
        elif infill == "glass":
            V.poly(quad, "int_glass", ao=1.0)
        elif infill == "solid":
            for sgn in (1, -1):
                o = 0.06 * sgn
                V.poly([(a[0] + sx * o, a[1] + sy * o, a[2]), (b[0] + sx * o, b[1] + sy * o, b[2]),
                        (b[0] + sx * o, b[1] + sy * o, b[2] + hi), (a[0] + sx * o, a[1] + sy * o, a[2] + hi)],
                       "int_drywall", normal_hint=(sx * sgn, sy * sgn, 0))
        if col:
            t2 = col_t / 2.0
            a0, a1 = (a[0] + sx * t2, a[1] + sy * t2), (a[0] - sx * t2, a[1] - sy * t2)
            b0, b1 = (b[0] + sx * t2, b[1] + sy * t2), (b[0] - sx * t2, b[1] - sy * t2)
            C.poly([(a0[0], a0[1], a[2]), (b0[0], b0[1], b[2]), (b0[0], b0[1], b[2] + ch), (a0[0], a0[1], a[2] + ch)],
                   cm, normal_hint=(sx, sy, 0))
            C.poly([(a1[0], a1[1], a[2]), (b1[0], b1[1], b[2]), (b1[0], b1[1], b[2] + ch), (a1[0], a1[1], a[2] + ch)],
                   cm, normal_hint=(-sx, -sy, 0))
            C.poly([(a0[0], a0[1], a[2] + ch), (b0[0], b0[1], b[2] + ch), (b1[0], b1[1], b[2] + ch),
                    (a1[0], a1[1], a[2] + ch)], cm, normal_hint=(0, 0, 1))
            C.poly([(a0[0], a0[1], a[2]), (a1[0], a1[1], a[2]), (a1[0], a1[1], a[2] + ch), (a0[0], a0[1], a[2] + ch)],
                   cm, normal_hint=(-dx, -dy, 0))
            C.poly([(b0[0], b0[1], b[2]), (b1[0], b1[1], b[2]), (b1[0], b1[1], b[2] + ch), (b0[0], b0[1], b[2] + ch)],
                   cm, normal_hint=(dx, dy, 0))
            if abs(a[2]) > 1e-6 or abs(b[2]) > 1e-6:      # not standing on the local floor: close the bottom
                C.poly([(a0[0], a0[1], a[2]), (a1[0], a1[1], a[2]), (b1[0], b1[1], b[2]), (b0[0], b0[1], b[2])], cm,
                       normal_hint=(0, 0, -1))
    return P


def elevator(floors=(0.0, 4.2), width=2.4, depth=2.4, door_w=REAL["elevator_door_w"], door_h=REAL["elevator_door_h"],
             wall_t=0.20, top=None, open_floors=(), out_of_order=(0,), labels=None, hollow=True,
             front_mat="int_stone", wall_mat="int_drywall", frame_mat="int_metal"):
    """Elevator shaft with a door on every floor. Local: the front (door) face is the plane y = 0 facing +y,
    the shaft goes back to y = -depth, x -width/2..width/2; floors = the floor heights served; top = shaft
    roof (default last floor + 3.6). Closed doors are brushed-steel panels; open_floors leave the opening
    (the shaft behind is dark). out_of_order: floor indices that get the OUT OF ORDER sign. labels: floor
    numbers for the indicators (default 1, 2, ...). hollow=True: the shaft has thick walls with inner faces
    and a pit floor (a wall-kick shaft if a door is open); False: one solid block."""
    floors = [float(z) for z in floors]
    top = float(top if top is not None else floors[-1] + 3.6)
    P = Prop("elevator", floors=floors, width=width, depth=depth, top=top, col_closed=True)
    V, C = P.visual, P.collision
    hw, hd = width / 2.0, door_w / 2.0
    labels = labels or [str(i + 1) for i in range(len(floors))]
    zs = floors + [top]
    for i, z0 in enumerate(floors):
        z1 = zs[i + 1]
        dz1 = z0 + door_h
        # front wall pieces (visual: outer face + top edge)
        for (x0, x1) in ((-hw, -hd), (hd, hw)):
            V.box(x0, -wall_t, z0, x1, 0.0, z1, front_mat, faces="+y")
        V.box(-hd, -wall_t, dz1, hd, 0.0, z1, front_mat, faces="+y")
        # frame trim
        V.box(-hd - 0.08, 0.0, z0, -hd, 0.04, dz1 + 0.08, frame_mat, faces="+y+x-x+z")
        V.box(hd, 0.0, z0, hd + 0.08, 0.04, dz1 + 0.08, frame_mat, faces="+y+x-x+z")
        V.box(-hd, 0.0, dz1, hd, 0.04, dz1 + 0.08, frame_mat, faces="+y+z-z")
        # jambs (the wall thickness inside the opening)
        V.poly([(-hd, 0.0, z0), (-hd, -wall_t, z0), (-hd, -wall_t, dz1), (-hd, 0.0, dz1)], frame_mat,
               normal_hint=(1, 0, 0), ao=0.85)
        V.poly([(hd, -wall_t, z0), (hd, 0.0, z0), (hd, 0.0, dz1), (hd, -wall_t, dz1)], frame_mat,
               normal_hint=(-1, 0, 0), ao=0.85)
        V.poly([(-hd, -wall_t, dz1), (hd, -wall_t, dz1), (hd, 0.0, dz1), (-hd, 0.0, dz1)], frame_mat,
               normal_hint=(0, 0, -1), ao=0.8)
        opened = i in open_floors
        if not opened:
            V.poly(front_quad(-hd, hd, -0.06, z0, dz1), "int_elevator", uvs=ONCE, ao=1.0)
            if hollow:
                C.box(-hd, -wall_t, z0, hd, -0.06, dz1, COL, faces="+y-y")
        if i in out_of_order and not opened:
            V.poly(front_quad(-0.36, 0.36, -0.05, z0 + 1.15, z0 + 1.51), "int_sign_out_of_order", uvs=ONCE, ao=1.0)
        # floor indicator above the door + call button
        lab = labels[i]
        cell = FLOOR_SIGN_CELLS.get(lab, -1)
        if cell >= 0:
            u0, v0 = (cell % 4) / 4.0, 0.5 if cell < 4 else 0.0
            V.poly(front_quad(-0.16, 0.16, 0.012, dz1 + 0.16, dz1 + 0.48), "int_sign_floors",
                   uvs=uv_rect(u0, v0, u0 + 0.25, v0 + 0.5), glow=True)
        V.box(hd + 0.25, 0.0, z0 + 0.95, hd + 0.37, 0.03, z0 + 1.2, frame_mat, faces="+y+x-x+z-z")
        V.poly(front_quad(hd + 0.28, hd + 0.34, 0.031, z0 + 1.0, z0 + 1.06), "int_plastic", glow=True,
               tint=(1.0, 0.55, 0.2))
        P.anchor(f"door_{i}", 0.0, 0.0, z0, 0.0)
        # collision of the front wall
        if hollow:
            col_box(C, -hw, -wall_t, z0, -hd, 0.0, z1, COL, bottom=i > 0)
            col_box(C, hd, -wall_t, z0, hw, 0.0, z1, COL, bottom=i > 0)
            C.box(-hd, -wall_t, dz1, hd, 0.0, z1, COL, faces=BOX_ALL)
    # side / back walls
    zb = floors[0]
    for x0, x1 in ((-hw, -hw + wall_t), (hw - wall_t, hw)):
        V.box(x0, -depth, zb, x1, 0.0, top, wall_mat, faces="+x" if x0 > 0 else "-x")
    V.box(-hw, -depth, zb, hw, -depth + wall_t, top, wall_mat, faces="-y")
    V.box(-hw, -depth, top - 0.3, hw, 0.0, top, wall_mat, faces="+z")
    if hollow:
        dark = (0.45, 0.45, 0.5)
        V.poly([(-hw + wall_t, -depth + wall_t, zb), (hw - wall_t, -depth + wall_t, zb), (hw - wall_t, -depth + wall_t, top),
                (-hw + wall_t, -depth + wall_t, top)], "int_metal", tint=dark, normal_hint=(0, 1, 0))
        V.poly([(-hw + wall_t, -wall_t, zb), (-hw + wall_t, -depth + wall_t, zb), (-hw + wall_t, -depth + wall_t, top),
                (-hw + wall_t, -wall_t, top)], "int_metal", tint=dark, normal_hint=(1, 0, 0))
        V.poly([(hw - wall_t, -depth + wall_t, zb), (hw - wall_t, -wall_t, zb), (hw - wall_t, -wall_t, top),
                (hw - wall_t, -depth + wall_t, top)], "int_metal", tint=dark, normal_hint=(-1, 0, 0))
        V.poly([(-hw + wall_t, -depth + wall_t, zb + 0.01), (-hw + wall_t, -wall_t, zb + 0.01),
                (hw - wall_t, -wall_t, zb + 0.01), (hw - wall_t, -depth + wall_t, zb + 0.01)], "int_plastic",
               normal_hint=(0, 0, 1))
        V.poly([(-hw + wall_t, -wall_t, top - 0.3), (-hw + wall_t, -depth + wall_t, top - 0.3),
                (hw - wall_t, -depth + wall_t, top - 0.3), (hw - wall_t, -wall_t, top - 0.3)], "int_metal",
               tint=dark, normal_hint=(0, 0, -1))
        col_box(C, -hw, -depth, zb, -hw + wall_t, -wall_t, top, COL)
        col_box(C, hw - wall_t, -depth, zb, hw, -wall_t, top, COL)
        col_box(C, -hw, -depth, zb, hw, -depth + wall_t, top, COL)
        C.box(-hw + wall_t, -depth + wall_t, top - 0.3, hw - wall_t, -wall_t, top, COL, faces=BOX_ALL)
        C.poly([(-hw + wall_t, -depth + wall_t, zb), (-hw + wall_t, -wall_t, zb), (hw - wall_t, -wall_t, zb),
                (hw - wall_t, -depth + wall_t, zb)], COL, normal_hint=(0, 0, 1))
        P.info["col_closed"] = False       # pit floor / door panels are single-sided pieces
    else:
        col_box(C, -hw, -depth, zb, hw, 0.0, top, COL)
    P.anchor("shaft_bottom", 0.0, -depth / 2.0, zb, 0.0)
    P.anchor("shaft_ceiling", 0.0, -depth / 2.0, top - 0.3, 0.0)
    P.anchor("roof", 0.0, -depth / 2.0, top, 0.0)
    return P


# ================================================================== furniture
def bookshelf(length=3 * REAL["stack_section_w"], height=REAL["stack_full_h"], depth=REAL["stack_depth"],
              double=True, books=("int_books", "int_books_b"), carcass="int_shelf_steel", end_panel="int_wood_dark",
              base_h=0.10, cap=0.03, end_caps=(), step_h=REAL["stack_counter_h"], step_len=0.9, seed=0, cam=False):
    """A library stack range. Local: x -length/2..length/2 (sections of ~0.915 m), y -depth/2..depth/2, z
    0..height, books on the front (+y) and, if double, the back. The flat steel top (depth 0.61 m) is
    walkable; end_caps ("+x" / "-x") adds an end-cap display step step_h tall and step_len long at that end
    (a ledge: floor -> 1.07 m -> 2.29 m, each a single jump). Collision: one box (+ the steps), 'COL nocam'
    unless cam. Standard heights: REAL stack_counter_h 1.07 / stack_mid_h 1.68 / stack_full_h 2.29."""
    rng = random.Random(seed)
    P = Prop("bookshelf", length=length, height=height, depth=depth, top_z=height, walkable_top=depth >= 0.5,
             col_closed=True)
    V, C = P.visual, P.collision
    hl, hd = length / 2.0, depth / 2.0
    et = 0.03
    for sx in (-1, 1):                                   # end panels
        x0, x1 = (hl - et, hl) if sx > 0 else (-hl, -hl + et)
        V.box(x0, -hd - 0.01, 0.0, x1, hd + 0.01, height, end_panel, faces=("+x" if sx > 0 else "-x") + "+y-y+z")
    V.box(-hl + et, -hd, height - cap, hl - et, hd, height, carcass, faces="+z+y-y")
    V.box(-hl + et, -hd + 0.03, 0.0, hl - et, hd - 0.03, base_h, carcass, faces="+y-y", tint=(0.72, 0.72, 0.72))
    zone = height - cap - base_h
    nrows = max(1, int(round(zone / 0.40)))
    nsec = max(1, int(round(length / REAL["stack_section_w"])))
    sw = (length - 2 * et) / nsec
    faces = (1, -1) if double else (1,)
    for sgn in faces:
        y = sgn * (hd - 0.03)
        for k in range(nsec):
            x0 = -hl + et + k * sw
            x1 = x0 + sw
            mat = books[rng.randrange(len(books))] if books else carcass
            u0 = rng.randrange(8) / 8.0
            quad = front_quad if sgn > 0 else back_quad
            V.poly(quad(x0, x1, y, base_h, height - cap), mat, uvs=uv_rect(u0, 0.0, u0 + sw / 2.0, nrows / 2.0))
            if k:                                         # section upright, 1.5 cm proud of the books
                yu = sgn * (hd - 0.015)
                V.poly([(x0 - 0.02, yu, base_h), (x0 + 0.02, yu, base_h), (x0 + 0.02, yu, height - cap),
                        (x0 - 0.02, yu, height - cap)], carcass, normal_hint=(0, sgn, 0))
    cm = COL if cam else COL_NOCAM
    col_box(C, -hl, -hd, 0.0, hl, hd, height, cm)
    P.anchor("top", 0.0, 0.0, height)
    for end in end_caps:
        sx = 1 if end == "+x" else -1
        xa, xb = (hl, hl + step_len) if sx > 0 else (-hl - step_len, -hl)
        V.box(xa, -hd, 0.0, xb, hd, step_h, "int_wood_dark", mats={"+z": "int_wood"})
        for j in range(2):                                # two face-out books on the display
            bx = xa + step_len * (0.3 + 0.4 * j)
            V.box(bx - 0.1, -0.02, step_h, bx + 0.1, 0.02, step_h + 0.28, "int_fabric_" + ("orange", "green")[j],
                  faces="+y-y+x-x+z")
        col_box(C, xa, -hd, 0.0, xb, hd, step_h, cm)
        P.anchor(f"step{end}", (xa + xb) / 2.0, 0.0, step_h)
        P.info.setdefault("ledges", []).append(step_h)
    return P


def stack_range(rows=4, length=4 * REAL["stack_section_w"], aisle=AISLE_M, heights=None, depth=REAL["stack_depth"],
                end_caps=None, seed=0, cam=False):
    """Parallel stack ranges along x, row i centred at y = i * (depth + aisle). heights: per-row list
    (cycled), e.g. (1.07, 1.68, 2.29) for a climbing staircase of stacks; end_caps: per-row tuples."""
    heights = list(heights or [REAL["stack_full_h"]])
    P = Prop("stack_range", rows=rows, length=length, aisle=aisle, pitch=depth + aisle, col_closed=True)
    for i in range(rows):
        ec = end_caps[i % len(end_caps)] if end_caps else ()
        P.merge(bookshelf(length, heights[i % len(heights)], depth, end_caps=ec, seed=seed * 31 + i, cam=cam),
                0.0, i * (depth + aisle), 0.0, 0.0, prefix=f"row{i}")
    return P


def chair(seat_h=REAL["seat_h"], width=0.48, depth=0.50, back_h=0.86, fabric="int_fabric_blue",
          frame="int_metal", collision=True, cam=False):
    """Stacking chair, seat centre origin; the sitter faces +y (the back is at -y). Collision: the seat
    block 0..seat_h (a step: needs a jump, 0.46 m > the 0.3 m probe)."""
    P = Prop("chair", seat_h=seat_h, col_closed=True)
    V = P.visual
    hw, hd = width / 2.0, depth / 2.0
    V.box(-hw, -hd, seat_h - 0.07, hw, hd, seat_h, fabric, faces=BOX_ALL)
    V.box(-hw, -hd, seat_h + 0.06, hw, -hd + 0.05, back_h, fabric, faces=BOX_ALL[:5])
    for sx in (-1, 1):                               # two sled frames (cheaper than four legs)
        x = sx * (hw - 0.03)
        V.box(x - 0.012, -hd + 0.02, 0.0, x + 0.012, hd - 0.02, seat_h - 0.07, frame, faces="+x-x+y-y")
        V.box(x - 0.012, -hd, seat_h, x + 0.012, -hd + 0.03, seat_h + 0.06, frame, faces="+x-x")
    if collision:
        col_box(P.collision, -hw, -hd, 0.0, hw, hd, seat_h, COL if cam else COL_NOCAM)
    P.anchor("seat", 0.0, 0.0, seat_h)
    return P


def stool(height=0.76, radius=0.19, fabric="int_fabric_orange", frame="int_metal", segments=8, collision=True):
    """Bar stool (cafe / counters), base centre origin."""
    P = Prop("stool", height=height, col_closed=True)
    pts = [(radius * math.cos(2 * math.pi * (k + 0.5) / segments), radius * math.sin(2 * math.pi * (k + 0.5) / segments))
           for k in range(segments)]
    P.visual.prism(pts, height - 0.07, height, fabric, top=fabric, bottom=fabric)
    P.visual.box(-0.03, -0.03, 0.03, 0.03, 0.03, height - 0.07, frame, faces="+x-x+y-y")
    P.visual.box(-0.2, -0.2, 0.0, 0.2, 0.2, 0.03, frame, faces="+x-x+y-y+z")
    P.visual.box(-0.17, -0.17, 0.28, 0.17, 0.17, 0.30, frame, faces="+x-x+y-y+z-z")
    if collision:
        col_box(P.collision, -radius * 0.9, -radius * 0.9, 0.0, radius * 0.9, radius * 0.9, height, COL_NOCAM)
    P.anchor("seat", 0.0, 0.0, height)
    return P


def kick_stool(radius=0.21, height=0.38, mat="int_shelf_steel"):
    """Library kick step (rolling step stool), 0.38 m: a little step up to the counter-height stacks."""
    P = Prop("kick_stool", height=height, col_closed=True)
    n = 8
    lo = [(radius * math.cos(2 * math.pi * (k + 0.5) / n), radius * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
    P.visual.prism(lo, 0.0, height, mat)
    P.visual.poly([(x, y, height) for x, y in lo], "int_plastic", normal_hint=(0, 0, 1))
    col_prism(P.collision, lo, 0.0, height, COL_NOCAM)
    P.anchor("top", 0.0, 0.0, height)
    return P


def study_table(length=REAL["table_l"], width=REAL["table_w"], height=REAL["table_h"], chairs_per_side=2,
                top="int_wood", frame="int_metal", seat="int_fabric_blue", chair_collision=True, cam=False):
    """Library study table with chairs on both long sides. Local: centred, long axis x. Collision: one
    block 0..height (jump onto it: 0.76 m) + the chair seats."""
    P = Prop("study_table", length=length, width=width, height=height, top_z=height, col_closed=True)
    V = P.visual
    hl, hw = length / 2.0, width / 2.0
    V.box(-hl, -hw, height - 0.04, hl, hw, height, top, faces=BOX_ALL)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hl - 0.07), sy * (hw - 0.07)
            V.box(x - 0.025, y - 0.025, 0.0, x + 0.025, y + 0.025, height - 0.04, frame, faces="+x-x+y-y")
    V.box(-hl + 0.07, -0.02, height - 0.16, hl - 0.07, 0.02, height - 0.04, frame, faces="+y-y-z")
    col_box(P.collision, -hl, -hw, 0.0, hl, hw, height, COL if cam else COL_NOCAM)
    n = chairs_per_side
    for i in range(n):
        x = -hl + (i + 0.5) * length / n
        for sgn, f in ((1, 180.0), (-1, 0.0)):
            P.merge(chair(fabric=seat, collision=chair_collision, cam=cam), x, sgn * (hw + 0.22), 0.0, f,
                    prefix=f"chair_{'n' if sgn > 0 else 's'}{i}")
    P.anchor("top", 0.0, 0.0, height)
    return P


def carrel_row(n=3, width=REAL["carrel_w"], depth=0.76, desk_h=REAL["table_h"], panel_h=REAL["carrel_panel_h"],
               panel="int_fabric_blue", top="int_wood", chairs=True, hutch=True, cam=False):
    """Row of n study carrels sharing panels. Local: desks along x, users sit on the +y side facing -y
    toward the back panel. Hutch: a small book shelf and a task light (glows) above each desk."""
    P = Prop("carrel_row", n=n, width=width, top_z=desk_h, col_closed=True)
    V, C = P.visual, P.collision
    L = n * width
    hl, hd = L / 2.0, depth / 2.0
    cm = COL if cam else COL_NOCAM
    V.box(-hl, -hd, desk_h - 0.03, hl, hd, desk_h, top, faces=BOX_ALL)
    V.box(-hl, -hd, 0.0, hl, -hd + 0.05, panel_h, panel, mats={"+z": "int_metal"}, faces=BOX_ALL[:5])
    for i in range(n + 1):
        x = -hl + i * width
        V.box(x - 0.02, -hd + 0.05, 0.0, x + 0.02, hd, panel_h, panel, mats={"+z": "int_metal"})
    for i in range(n):
        cx = -hl + (i + 0.5) * width
        if hutch:
            zs = panel_h - 0.34
            V.box(cx - width / 2 + 0.02, -hd + 0.05, zs - 0.02, cx + width / 2 - 0.02, -hd + 0.33, zs, "int_wood",
                  faces=BOX_ALL)
            V.poly(front_quad(cx - width / 2 + 0.03, cx + width / 2 - 0.03, -hd + 0.06, zs, zs + 0.3), "int_books",
                   uvs=uv_rect(i * 0.25, 0.0, i * 0.25 + (width - 0.06) / 2.0, 0.375))
            V.poly([(cx - 0.3, -hd + 0.2, zs - 0.021), (cx - 0.3, -hd + 0.08, zs - 0.021), (cx + 0.3, -hd + 0.08, zs - 0.021),
                    (cx + 0.3, -hd + 0.2, zs - 0.021)], "int_light", uvs=ONCE, glow=True, normal_hint=(0, 0, -1))
            P.lights.append(Light((cx, -hd + 0.3, desk_h + 0.3), radius=1.4, strength=0.25))
        if chairs:
            P.merge(chair(collision=True, cam=cam), cx, hd + 0.22, 0.0, 180.0, prefix=f"chair{i}")
        P.anchor(f"seat{i}", cx, hd + 0.22, REAL["seat_h"], 180.0)
    col_box(C, -hl, -hd, 0.0, hl, hd, desk_h, cm)
    col_box(C, -hl, -hd, desk_h, hl, -hd + 0.05, panel_h, cm, bottom=True)
    for i in range(n + 1):
        x = -hl + i * width
        col_box(C, x - 0.02, -hd + 0.05, desk_h, x + 0.02, hd, panel_h, cm, bottom=True)
    return P


def monitor(screen_w=0.56, screen_h=0.34, z=0.12, collision=False, face="+y"):
    """Desktop monitor on a stand (base centre origin at the desk surface); the screen faces +y and glows."""
    P = Prop("monitor", col_closed=True)
    V = P.visual
    hw = screen_w / 2.0
    V.box(-0.12, -0.1, 0.0, 0.12, 0.08, 0.015, "int_plastic", faces="+x-x+y-y+z")
    V.box(-0.03, -0.06, 0.015, 0.03, -0.03, z + 0.08, "int_plastic", faces="+x-x+y-y")
    V.box(-hw, -0.03, z, hw, 0.0, z + screen_h, "int_plastic", faces=BOX_ALL, mats={"+y": "int_monitor"},
          uvs={"+y": ONCE})
    _glow_last(V, 6, "int_monitor")
    if collision:
        col_box(P.collision, -hw, -0.06, 0.0, hw, 0.0, z + screen_h, COL_NOCAM)
    return P


def computer_row(n=4, seat_w=0.9, depth=0.76, desk_h=REAL["table_h"], double=False, chairs=True, monitor_col=True,
                 cam=False):
    """Computer workstations. Local: desk along x, users on +y facing -y (and on -y facing +y if double)."""
    P = Prop("computer_row", n=n, top_z=desk_h, col_closed=True, rest_z=[desk_h])
    V, C = P.visual, P.collision
    L = n * seat_w
    hl = L / 2.0
    y0 = -depth if double else -depth / 2.0
    y1 = depth if double else depth / 2.0
    V.box(-hl, y0, desk_h - 0.04, hl, y1, desk_h, "int_wood", faces=BOX_ALL)
    V.box(-hl, y0 + 0.02, 0.05, hl, y1 - 0.02, desk_h - 0.04, "int_plastic", faces="+x-x+y-y",
          tint=(0.9, 0.9, 0.9))
    if double:
        V.box(-hl, -0.02, desk_h, hl, 0.02, desk_h + 0.45, "int_fabric_blue", faces=BOX_ALL[:5])
    col_box(C, -hl, y0, 0.0, hl, y1, desk_h, COL if cam else COL_NOCAM)
    sides = (1, -1) if double else (1,)
    for sgn in sides:
        for i in range(n):
            cx = -hl + (i + 0.5) * seat_w
            yb = sgn * (0.12 if double else -depth / 2.0 + 0.2)
            P.merge(monitor(collision=monitor_col), cx, yb, desk_h, 0.0 if sgn > 0 else 180.0)
            yk = sgn * ((depth if double else depth / 2.0) - 0.22)
            V.box(cx - 0.22, yk - 0.08, desk_h, cx + 0.22, yk + 0.08, desk_h + 0.02, "int_plastic", faces="+x-x+y-y+z")
            ys = sgn * ((depth if double else depth / 2.0) + 0.24)
            if chairs:
                P.merge(chair(fabric="int_fabric_blue" if i % 2 else "int_fabric_orange", cam=cam), cx, ys, 0.0,
                        180.0 if sgn > 0 else 0.0, prefix=f"chair{'b' if sgn < 0 else ''}{i}")
            P.anchor(f"seat{'b' if sgn < 0 else ''}{i}", cx, ys, REAL["seat_h"], 180.0 if sgn > 0 else 0.0)
    return P


def study_room(width=4.0, depth=3.6, height=2.75, door_w=0.95, door_h=REAL["door_h"], door_x=None, sides_glass=True,
               back="int_drywall", roof=True, roof_t=0.15, table=True, whiteboard_=True, sign_=True, post_every=1.4,
               cam=False):
    """Glass-walled group study room with a DOOR GAP (no door: the co-op act puts a Lua glass-door object
    there). Local: centred, the glass front with the gap faces +y, solid back wall (with a whiteboard
    inside) at -y. roof: a walkable roof slab (climb on top from a shelf / the mezzanine). Anchors: "door"
    (gap centre at the front plane, facing out), "inside", "table_top", "roof". info["door_gap"]: centre,
    width, height (size of the glass door object)."""
    P = Prop("study_room", width=width, depth=depth, height=height, col_closed=True)
    V, C = P.visual, P.collision
    hw, hd = width / 2.0, depth / 2.0
    dx = door_x if door_x is not None else hw - door_w / 2.0 - 0.45
    d0, d1 = dx - door_w / 2.0, dx + door_w / 2.0
    gt = 0.08                                        # glass wall thickness (frame / collision)
    cm = COL if cam else COL_NOCAM
    frame = "int_metal"

    def glass(a, b, z0, z1):
        V.wall(a, b, z0, z1, "int_glass", ao=1.0)
    # front (+y): glass both sides of the gap + transom
    yf = hd
    glass((-hw, yf), (d0, yf), 0.1, height)
    glass((d1, yf), (hw, yf), 0.1, height)
    glass((d0, yf), (d1, yf), door_h + 0.06, height)
    if sides_glass:
        glass((hw, yf), (hw, -hd + 0.12), 0.1, height)
        glass((-hw, -hd + 0.12), (-hw, yf), 0.1, height)
    else:
        V.box(hw - gt, -hd, 0.0, hw, hd, height, back, faces="+x-x")
        V.box(-hw, -hd, 0.0, -hw + gt, hd, height, back, faces="+x-x")
    # back wall
    V.box(-hw, -hd, 0.0, hw, -hd + 0.12, height, back, faces="+y-y+x-x")
    # frame: base rail (both faces), posts, head rail
    runs = [((-hw, yf), (d0, yf)), ((d1, yf), (hw, yf))]
    if sides_glass:
        runs += [((hw, yf), (hw, -hd + 0.12)), ((-hw, -hd + 0.12), (-hw, yf))]
    for (a, b) in runs:
        L = math.dist(a, b)
        if L < 1e-3:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, ny = uy, -ux                                 # right of a -> b
        o = gt / 2
        V.wall((a[0] + nx * o, a[1] + ny * o), (b[0] + nx * o, b[1] + ny * o), 0.0, 0.1, frame)
        V.wall((b[0] - nx * o, b[1] - ny * o), (a[0] - nx * o, a[1] - ny * o), 0.0, 0.1, frame)
        V.poly([(a[0] + nx * o, a[1] + ny * o, 0.1), (b[0] + nx * o, b[1] + ny * o, 0.1),
                (b[0] - nx * o, b[1] - ny * o, 0.1), (a[0] - nx * o, a[1] - ny * o, 0.1)], frame, normal_hint=(0, 0, 1))
        k = max(1, int(math.ceil(L / post_every)))
        for j in range(k + 1):
            px, py = a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k
            V.box(px - 0.03, py - 0.04, 0.0, px + 0.03, py + 0.04, height, frame, faces="+x-x+y-y")
    V.box(d0 - 0.03, yf - 0.04, door_h, d1 + 0.03, yf + 0.04, door_h + 0.06, frame, faces="+y-y-z")
    for x in (d0, d1):
        V.box(x - 0.03, yf - 0.05, 0.0, x + 0.03, yf + 0.05, door_h, frame, faces="+x-x+y-y")
    if roof:
        V.box(-hw - 0.02, -hd, height, hw + 0.02, hd + 0.02, height + roof_t, "int_drywall",
              faces=BOX_ALL, mats={"-z": "int_ceiling", "+z": "int_shelf_steel"})
        col_box(C, -hw, -hd, height, hw, hd, height + roof_t, cm, bottom=True)
        P.anchor("roof", 0.0, 0.0, height + roof_t)
    # collision: glass walls as thin boxes with the gap
    t2 = gt / 2.0
    col_box(C, -hw, yf - t2, 0.0, d0, yf + t2, height, cm)
    col_box(C, d1, yf - t2, 0.0, hw, yf + t2, height, cm)
    col_box(C, d0, yf - t2, door_h, d1, yf + t2, height, cm, bottom=True)
    col_box(C, hw - t2, -hd, 0.0, hw + t2, yf - t2, height, cm)
    col_box(C, -hw - t2, -hd, 0.0, -hw + t2, yf - t2, height, cm)
    col_box(C, -hw + t2, -hd, 0.0, hw - t2, -hd + 0.12, height, cm)
    # furniture
    if table:
        P.merge(study_table(min(1.83, width - 1.4), 0.91, chairs_per_side=2, seat="int_fabric_green", cam=cam),
                0.0, -0.15, 0.0, 0.0, prefix="table")
        P.anchor("table_top", 0.0, -0.15, REAL["table_h"])
    if whiteboard_:
        P.merge(whiteboard(min(2.4, width - 0.8), 1.2, 0.9), 0.0, -hd + 0.12, 0.0, 0.0, prefix="whiteboard")
    if sign_:
        sh = min(0.42, height - door_h - 0.16)
        P.merge(sign("int_sign_study", 2 * sh, sh, door_h + 0.1, mount="wall"), dx, yf + 0.045, 0.0, 0.0,
                prefix="sign")
    P.anchor("door", dx, yf, 0.0, 0.0)
    P.anchor("inside", 0.0, hd - 0.9, 0.0, 180.0)
    P.anchor("outside", dx, yf + 1.2, 0.0, 180.0)
    P.info["door_gap"] = {"centre": (dx, yf), "width": door_w, "height": door_h, "wall_t": gt}
    return P


def help_desk(length=3.6, depth=0.9, height=REAL["counter_h"], work_h=REAL["table_h"], return_len=1.6,
              monitors=2, front_sign=True, hanging_sign=True, hang_z=2.5, hang_top=3.6, cam=False):
    """Library help / circulation desk. Local: the patron side is +y; a counter height top in front, the
    staff work surface behind at work_h, an L return at +x going back. front_sign: HELP DESK panel on the
    front; hanging_sign: a double-sided HELP DESK sign at hang_z on rods up to hang_top (set it to the
    ceiling). Collision: counter block (1.07 m, single jump) + work surface + return."""
    P = Prop("help_desk", length=length, top_z=height, col_closed=True)
    V, C = P.visual, P.collision
    hl, hd = length / 2.0, depth / 2.0
    cm = COL if cam else COL_NOCAM
    yc = hd - 0.32
    V.box(-hl, yc, 0.0, hl, hd, height - 0.04, "int_wood_dark", faces="+y-y+x-x")
    V.box(-hl - 0.03, yc - 0.03, height - 0.04, hl + 0.03, hd + 0.05, height, "int_stone", faces=BOX_ALL)
    V.box(-hl, -hd, work_h - 0.04, hl, yc, work_h, "int_wood", faces="+z-z-y-x")
    V.box(-hl, -hd, 0.0, -hl + 0.04, yc, work_h - 0.04, "int_wood_dark", faces="+x-x-y")
    col_box(C, -hl, yc, 0.0, hl, hd + 0.05, height, cm)
    col_box(C, -hl, -hd, 0.0, hl, yc, work_h, cm)
    if return_len > 0:
        V.box(hl - 0.6, -hd - return_len, work_h - 0.04, hl, -hd, work_h, "int_wood", faces="+z-z-y-x+x")
        V.box(hl - 0.04, -hd - return_len, 0.0, hl, -hd, work_h - 0.04, "int_wood_dark", faces="+x-x-y")
        col_box(C, hl - 0.6, -hd - return_len, 0.0, hl, -hd, work_h, cm)
    for i in range(monitors):
        x = -hl + (i + 0.5) * length / max(1, monitors)
        P.merge(monitor(), x, yc - 0.1, work_h, 180.0)
    if front_sign:
        P.merge(sign("int_sign_help", 0.9, 0.45, 0.42, mount="wall"), 0.0, hd, 0.0, 0.0, prefix="front_sign")
    if hanging_sign:
        P.merge(sign("int_sign_help", 1.2, 0.6, hang_z, mount="hanging", hang_top=hang_top), 0.0, yc, 0.0, 0.0,
                prefix="hanging_sign")
    P.anchor("counter_top", 0.0, (yc + hd) / 2.0, height)
    P.anchor("staff", 0.0, -hd - 0.6, 0.0, 0.0)
    P.anchor("patron", 0.0, hd + 0.8, 0.0, 180.0)
    return P


def cafe_counter(length=4.8, depth=0.75, height=REAL["counter_h"], case=True, machine=True, menu=True, stools=3,
                 menu_z=2.2, cam=False):
    """Library cafe counter. Local: customers on +y. A glass pastry case (walkable top 1.52 m) and an espresso
    machine on the counter, a chalkboard menu on two posts behind, bar stools in front."""
    P = Prop("cafe_counter", length=length, top_z=height, col_closed=True)
    V, C = P.visual, P.collision
    hl, hd = length / 2.0, depth / 2.0
    cm = COL if cam else COL_NOCAM
    V.box(-hl, -hd, 0.0, hl, hd, height - 0.04, "int_wood_dark", faces="+y-y+x-x")
    V.box(-hl - 0.03, -hd - 0.03, height - 0.04, hl + 0.03, hd + 0.05, height, "int_stone", faces=BOX_ALL)
    col_box(C, -hl, -hd, 0.0, hl, hd + 0.05, height, cm)
    if case:
        cx = -hl / 2.0
        V.box(cx - 0.6, -0.25, height, cx + 0.6, 0.25, height + 0.45, "int_glass", faces="+x-x+y-y+z", ao=1.0)
        V.box(cx - 0.6, -0.25, height + 0.45, cx + 0.6, 0.25, height + 0.47, "int_metal", faces=BOX_ALL)
        for j, tint in enumerate(((1.0, 0.7, 0.45), (0.85, 0.55, 0.35), (1.0, 0.85, 0.6))):
            px = cx - 0.35 + j * 0.35
            V.box(px - 0.1, -0.08, height, px + 0.1, 0.08, height + 0.07, "int_wood", faces=BOX_ALL[:5], tint=tint)
        col_box(C, cx - 0.6, -0.25, height, cx + 0.6, 0.25, height + 0.47, cm, bottom=True)
        P.anchor("case_top", cx, 0.0, height + 0.47)
    if machine:
        mx = hl / 2.0
        V.box(mx - 0.3, -0.3, height, mx + 0.3, 0.15, height + 0.5, "int_metal", faces=BOX_ALL[:5])
        V.poly([(mx - 0.2, 0.151, height + 0.3), (mx + 0.2, 0.151, height + 0.3), (mx + 0.2, 0.151, height + 0.42),
                (mx - 0.2, 0.151, height + 0.42)], "int_plastic", glow=True, tint=(1.0, 0.45, 0.15))
        col_box(C, mx - 0.3, -0.3, height, mx + 0.3, 0.15, height + 0.5, cm, bottom=True)
    if menu:
        ym = -hd - 0.6
        for x in (-0.85, 0.85):
            V.box(x - 0.03, ym - 0.03, 0.0, x + 0.03, ym + 0.03, menu_z + 0.85, "int_metal", faces="+x-x+y-y+z")
        V.box(-0.82, ym - 0.02, menu_z, 0.82, ym + 0.02, menu_z + 0.82, "int_wood_dark", faces=BOX_ALL,
              mats={"+y": "int_sign_cafe"}, uvs={"+y": ONCE})
        P.anchor("menu", 0.0, ym, menu_z)
    for i in range(stools):
        x = -hl + (i + 0.5) * length / max(1, stools)
        P.merge(stool(), x, hd + 0.45, 0.0, 180.0, prefix=f"stool{i}")
    P.anchor("counter_top", 0.0, 0.0, height)
    P.anchor("barista", 0.0, -hd - 0.3, 0.0, 0.0)
    return P


def couch(length=2.0, depth=0.9, seat_h=0.45, back_h=0.85, arm_w=0.18, arm_h=0.62, fabric="int_fabric_blue", cam=False):
    """Lounge sofa, base centre origin, the sitter faces +y. Collision: seat block + back + arms (steps)."""
    P = Prop("couch", length=length, col_closed=True)
    V, C = P.visual, P.collision
    hl, hd = length / 2.0, depth / 2.0
    cm = COL if cam else COL_NOCAM
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hl - 0.08), sy * (hd - 0.08)
            V.box(x - 0.03, y - 0.03, 0.0, x + 0.03, y + 0.03, 0.08, "int_plastic", faces="+x-x+y-y")
    V.box(-hl, -hd, 0.08, hl, hd, seat_h - 0.12, fabric, faces=BOX_ALL, tint=(0.8, 0.8, 0.8))
    V.box(-hl + arm_w, -hd + 0.2, seat_h - 0.12, hl - arm_w, hd, seat_h, fabric, faces=BOX_ALL[:5])
    V.box(-hl, -hd, seat_h - 0.12, hl, -hd + 0.2, back_h, fabric, faces=BOX_ALL[:5])
    for sx in (-1, 1):
        x0, x1 = (hl - arm_w, hl) if sx > 0 else (-hl, -hl + arm_w)
        V.box(x0, -hd + 0.2, seat_h - 0.12, x1, hd, arm_h, fabric, faces=BOX_ALL[:5])
    col_box(C, -hl, -hd + 0.2, 0.0, hl, hd, seat_h, cm)
    col_box(C, -hl, -hd, 0.0, hl, -hd + 0.2, back_h, cm)
    for sx in (-1, 1):
        x0, x1 = (hl - arm_w, hl) if sx > 0 else (-hl, -hl + arm_w)
        col_box(C, x0, -hd + 0.2, seat_h, x1, hd, arm_h, cm, bottom=True)
    P.anchor("seat", 0.0, 0.1, seat_h)
    return P


def beanbag(radius=0.45, height=0.55, fabric="int_fabric_orange", segments=8):
    """Bean bag: a squashed low-poly blob. Collision: a soft block 0.8 x radius square, 0.6 x height."""
    P = Prop("beanbag", col_closed=True)
    V = P.visual
    rings = [(0.0, 0.88), (0.30, 1.0), (0.70, 0.80), (1.0, 0.30)]

    def ring(fz, fr):
        return [(radius * fr * math.cos(2 * math.pi * (k + 0.5) / segments),
                 radius * fr * math.sin(2 * math.pi * (k + 0.5) / segments) * 0.92, height * fz) for k in range(segments)]
    rs = [ring(fz, fr) for fz, fr in rings]
    for lo, hi in zip(rs, rs[1:]):
        for k in range(segments):
            k2 = (k + 1) % segments
            q = [lo[k], lo[k2], hi[k2], hi[k]]
            c = tuple(sum(v[i] for v in q) / 4.0 for i in range(3))
            V.poly(q, fabric, normal_hint=(c[0], c[1], c[2] - height * 0.35))
    V.poly(rs[-1], fabric, normal_hint=(0, 0, 1))
    s = radius * 0.8
    col_box(P.collision, -s, -s * 0.92, 0.0, s, s * 0.92, height * 0.6, COL_NOCAM)
    P.anchor("top", 0.0, 0.0, height * 0.6)
    return P


def book_cart(length=0.9, width=0.45, height=1.0, seed=0):
    """Library book truck: three metal shelves with sloped book rows, casters. Collision: one block (a Lua
    moving-cart object can reuse the geometry: export it as a separate model)."""
    rng = random.Random(seed)
    P = Prop("book_cart", top_z=height, col_closed=True)
    V = P.visual
    hl, hw = length / 2.0, width / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (hl - 0.02), sy * (hw - 0.02)
            V.box(x - 0.02, y - 0.02, 0.06, x + 0.02, y + 0.02, height, "int_metal", faces="+x-x+y-y+z")
            V.box(x - 0.03, y - 0.03, 0.0, x + 0.03, y + 0.03, 0.06, "int_plastic", faces="+x-x+y-y")
    for z in (0.22, 0.58, height - 0.02):
        V.box(-hl, -hw, z, hl, hw, z + 0.02, "int_metal", faces=BOX_ALL)
    for z in (0.24, 0.60):
        for sgn in (1, -1):
            y = sgn * 0.08
            u0 = rng.randrange(8) / 8.0
            x0, x1 = -hl + 0.03, hl - 0.03
            if sgn > 0:      # leaning outward: bottom-left as seen from that side (front_quad / back_quad order)
                pts = [(x1, y, z), (x0, y, z), (x0, y + 0.06, z + 0.3), (x1, y + 0.06, z + 0.3)]
            else:
                pts = [(x0, y, z), (x1, y, z), (x1, y - 0.06, z + 0.3), (x0, y - 0.06, z + 0.3)]
            V.poly(pts, "int_books", uvs=uv_rect(u0, 0.05, u0 + (length - 0.06) / 2.0, 0.42))
    col_box(P.collision, -hl, -hw, 0.0, hl, hw, height, COL_NOCAM)
    P.anchor("top", 0.0, 0.0, height)
    return P


def kiosk(height=1.0, screen_tilt=30.0, cam=False):
    """Room-booking kiosk (Act 3 co-op): pedestal + tilted touch screen (int_kiosk, glows). The player
    stands at anchor "punch" and punches it. Collision: the pedestal block."""
    P = Prop("kiosk", col_closed=True)
    V = P.visual
    V.box(-0.3, -0.25, 0.0, 0.3, 0.25, 0.04, "int_plastic", faces="+x-x+y-y+z")
    V.box(-0.17, -0.14, 0.04, 0.17, 0.14, height, "int_metal", faces="+x-x+y-y")
    a = math.radians(screen_tilt)
    w, h, t = 0.25, 0.19, 0.05
    cz, cy = height + 0.12, 0.0
    up = (0.0, -math.sin(a), math.cos(a))           # screen "up" tilts back
    nrm = (0.0, math.cos(a), math.sin(a))           # screen normal faces the user (+y) and up

    def pt(u, v, d):
        return (u, cy + up[1] * v + nrm[1] * d, cz + up[2] * v + nrm[2] * d)
    centre = pt(0.0, 0.0, -t / 2.0)
    # screen: bottom-left as seen from the user (+y side) is +x, as in front_quad
    V.poly([pt(w, -h, 0), pt(-w, -h, 0), pt(-w, h, 0), pt(w, h, 0)], "int_kiosk", uvs=ONCE, glow=True, normal_hint=nrm)
    V.poly([pt(w, -h, -t), pt(-w, -h, -t), pt(-w, h, -t), pt(w, h, -t)], "int_plastic",
           normal_hint=tuple(-c for c in nrm))
    for (p0, p1) in (((-w, -h), (-w, h)), ((w, h), (w, -h)), ((-w, h), (w, h)), ((w, -h), (-w, -h))):
        f = [pt(p0[0], p0[1], 0), pt(p0[0], p0[1], -t), pt(p1[0], p1[1], -t), pt(p1[0], p1[1], 0)]
        fc = tuple(sum(v[i] for v in f) / 4.0 for i in range(3))
        V.poly(f, "int_plastic", normal_hint=_sub(fc, centre))
    col_box(P.collision, -0.25, -0.22, 0.0, 0.25, 0.22, height, COL if cam else COL_NOCAM)
    P.anchor("screen", 0.0, 0.0, cz)
    P.anchor("punch", 0.0, 0.62, 0.0, 180.0)
    return P


def whiteboard(width=2.4, height=1.2, z=0.9, tray=True):
    """Wall-mounted whiteboard: local wall plane y = 0, the board faces +y. Visual only."""
    P = Prop("whiteboard", col_closed=True)
    hw = width / 2.0
    P.visual.box(-hw, 0.0, z, hw, 0.025, z + height, "int_metal", faces="+y+x-x+z-z", mats={"+y": "int_whiteboard"},
                 uvs={"+y": ONCE})
    if tray:
        P.visual.box(-hw + 0.1, 0.025, z - 0.03, hw - 0.1, 0.09, z, "int_metal", faces="+y+z-z+x-x")
    return P


# ================================================================== signs and lights
def poster(width=0.6, height=0.9, which=0, z=1.2):
    """Poster on a wall (local wall plane y = 0, faces +y): which 0 = DNA, 1 = READ MORE."""
    P = Prop("poster", col_closed=True)
    hw = width / 2.0
    u0 = 0.5 * (which % 2)
    P.visual.poly(front_quad(-hw, hw, 0.006, z, z + height), "int_posters", uvs=uv_rect(u0, 0.0, u0 + 0.5, 1.0), ao=1.0)
    return P


def sign(material, width=1.2, height=0.6, z=2.4, mount="wall", glow=False, uvs=None, hang_top=None, depth=0.03):
    """Sign panel. mount "wall": on a wall (plane y = 0, faces +y); "hanging": a double-sided panel on two
    rods up to hang_top (default z + height + 0.6); "post": on a pole from the floor. uvs: the panel UVs
    (default the whole texture, ONCE)."""
    P = Prop("sign", col_closed=True)
    V = P.visual
    hw = width / 2.0
    uv = uvs or ONCE
    if mount == "wall":
        V.box(-hw, 0.0, z, hw, depth, z + height, "int_plastic", faces="+y+x-x+z-z", mats={"+y": material},
              uvs={"+y": uv})
        if glow:
            _glow_last(V, 5, material)
    else:
        V.box(-hw, -depth / 2, z, hw, depth / 2, z + height, "int_plastic", faces=BOX_ALL,
              mats={"+y": material, "-y": material}, uvs={"+y": uv, "-y": uv})
        if glow:
            _glow_last(V, 6, material)
        if mount == "hanging":
            top = hang_top if hang_top is not None else z + height + 0.6
            for x in (-hw * 0.7, hw * 0.7):
                V.box(x - 0.008, -0.008, z + height, x + 0.008, 0.008, top, "int_metal", faces="+x-x+y-y")
        elif mount == "post":
            V.box(-0.03, -0.03, 0.0, 0.03, 0.03, z, "int_metal", faces="+x-x+y-y")
            V.box(-0.2, -0.2, 0.0, 0.2, 0.2, 0.03, "int_metal", faces="+x-x+y-y+z")
            col_box(P.collision, -0.05, -0.05, 0.0, 0.05, 0.05, z + height, COL_NOCAM)
    return P


FLOOR_SIGN_CELLS = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "up": 6, "down": 7}


def floor_sign(label="1", size=0.45, z=2.2, mount="wall", hang_top=None):
    """Floor number / arrow sign from the int_sign_floors atlas (label "1".."6", "up", "down")."""
    i = FLOOR_SIGN_CELLS[str(label)]
    u0, v0 = (i % 4) / 4.0, 0.5 if i < 4 else 0.0
    return sign("int_sign_floors", size, size, z, mount=mount, glow=True, uvs=uv_rect(u0, v0, u0 + 0.25, v0 + 0.5),
                hang_top=hang_top)


def ceiling_light(width=0.6, length=1.2, radius=7.0, strength=0.38, drop=0.0):
    """2' x 4' troffer. Local origin = the ceiling plane at the fixture centre (place it at z = ceiling);
    the glowing panel faces down 1 cm below it (or drop m lower as a pendant). Adds a Light 0.5 m below."""
    P = Prop("ceiling_light", col_closed=True)
    hw, hl = width / 2.0, length / 2.0
    z = -0.012 - drop
    P.visual.poly([(-hw, -hl, z), (-hw, hl, z), (hw, hl, z), (hw, -hl, z)], "int_light",
                  uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True)
    if drop > 0:
        P.visual.box(-hw - 0.03, -hl - 0.03, z, hw + 0.03, hl + 0.03, z + 0.08, "int_metal", faces="+x-x+y-y+z")
        for y in (-hl * 0.8, hl * 0.8):
            P.visual.box(-0.006, y - 0.006, z + 0.08, 0.006, y + 0.006, 0.0, "int_metal", faces="+x-x+y-y")
    P.lights.append(Light((0.0, 0.0, z - 0.5), radius=radius, strength=strength))
    return P


def light_grid(width, depth, spacing=3.6, margin=1.2, radius=7.0, strength=0.38):
    """Troffers on a regular grid over a CORNER-origin rectangle (x 0..width, y 0..depth), at z = 0 (place
    the prop at the ceiling height)."""
    P = Prop("light_grid", col_closed=True)
    nx = max(1, int(round((width - 2 * margin) / spacing)) + 1)
    ny = max(1, int(round((depth - 2 * margin) / spacing)) + 1)
    for i in range(nx):
        for j in range(ny):
            x = width / 2.0 if nx == 1 else margin + (width - 2 * margin) * i / (nx - 1)
            y = depth / 2.0 if ny == 1 else margin + (depth - 2 * margin) * j / (ny - 1)
            P.merge(ceiling_light(radius=radius, strength=strength), x, y, 0.0, 0.0)
    return P


def light_ring(radius=3.0, ring_w=0.5, thickness=0.18, segments=8, drop=2.0, hangable=True, strength=0.45):
    """The atrium light fixture: an n-gon ring hung on four cables. Local: ring centre, z = 0 at its
    UNDERSIDE (the glowing strip), the walkable top at z = thickness, cables up to z = thickness + drop
    (place it at ceiling - thickness - drop; keep drop >= 1.8 m so Mario, 1.6 m, fits on top). Collision:
    walkable top, rim walls and a 'COL hangable' underside (jump up into it to hang and shimmy round).
    Anchors: "top_<k>" spots on the ring."""
    P = Prop("light_ring", radius=radius, col_closed=True)
    V, C = P.visual, P.collision
    ro, ri = radius + ring_w / 2.0, radius - ring_w / 2.0
    ang = [2 * math.pi * (k + 0.5) / segments for k in range(segments)]
    O = [(ro * math.cos(a), ro * math.sin(a)) for a in ang]
    I = [(ri * math.cos(a), ri * math.sin(a)) for a in ang]
    T = thickness
    for k in range(segments):
        k2 = (k + 1) % segments
        V.wall(O[k], O[k2], 0.0, T, "int_metal")
        V.wall(I[k2], I[k], 0.0, T, "int_metal")
        V.poly([(O[k][0], O[k][1], T), (O[k2][0], O[k2][1], T), (I[k2][0], I[k2][1], T), (I[k][0], I[k][1], T)],
               "int_metal", normal_hint=(0, 0, 1))
        V.poly([(O[k][0], O[k][1], 0.0), (I[k][0], I[k][1], 0.0), (I[k2][0], I[k2][1], 0.0), (O[k2][0], O[k2][1], 0.0)],
               "int_light", uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], glow=True, normal_hint=(0, 0, -1))
        C.wall(O[k], O[k2], 0.0, T, COL_NOCAM)
        C.wall(I[k2], I[k], 0.0, T, COL_NOCAM)
        C.poly([(O[k][0], O[k][1], T), (O[k2][0], O[k2][1], T), (I[k2][0], I[k2][1], T), (I[k][0], I[k][1], T)], COL,
               normal_hint=(0, 0, 1))
        C.poly([(O[k][0], O[k][1], 0.0), (I[k][0], I[k][1], 0.0), (I[k2][0], I[k2][1], 0.0), (O[k2][0], O[k2][1], 0.0)],
               COL_HANG if hangable else COL, normal_hint=(0, 0, -1))
        a = (ang[k] + ang[k2]) / 2.0 if k2 else ang[k] + math.pi / segments
        P.anchor(f"top_{k}", radius * math.cos(a), radius * math.sin(a), T)
        P.lights.append(Light((radius * math.cos(ang[k]), radius * math.sin(ang[k]), -0.6), radius=6.0,
                              strength=strength))
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        x, y = radius * math.cos(a), radius * math.sin(a)
        V.box(x - 0.01, y - 0.01, T, x + 0.01, y + 0.01, T + drop, "int_metal", faces="+x-x+y-y")
    P.info.update(top_z=T, hang_z=0.0, ring_width=ring_w)
    return P


# ================================================================== Blender conversion
def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_bpy_mesh(km, name, lighting=None, collision=False):
    """KitMesh -> (bpy mesh, material_slots). Visual meshes get "UVMap" (explicit or world-projected UVs)
    and the FLOAT_COLOR CORNER attributes "Col" (the baked shade, stored linear: Fast64 gamma-corrects it
    back to sRGB) and "Alpha" (white). Collision meshes get geometry and material indices only."""
    import bmesh
    import bpy
    slots = km.materials()
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if not collision:
        lighting = lighting or Lighting()
        uvl = bm.loops.layers.uv.new("UVMap")
        coll = bm.loops.layers.float_color.new("Col")
        alpl = bm.loops.layers.float_color.new("Alpha")
    for p in km.polys:
        try:
            face = bm.faces.new([bm.verts.new(v) for v in p.pts])
        except ValueError:
            continue
        face.material_index = slots.index(p.mat)
        if collision:
            continue
        n = unit_normal(p.pts)
        uvs = p.uvs or project_uv(p.pts, palette_entry(p.mat)["tile_m"], newell(p.pts))
        for loop, v, uv, ao in zip(face.loops, p.pts, uvs, p.ao):
            loop[uvl].uv = uv
            c = lighting.shade(v, n, ao, p.tint, p.glow)
            loop[coll] = (_srgb_to_linear(c[0]), _srgb_to_linear(c[1]), _srgb_to_linear(c[2]), 1.0)
            loop[alpl] = (1.0, 1.0, 1.0, 1.0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    if collision:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(me)
    bm.free()
    return me, slots


def link_parts(parts, mats, parent=None, collection=None, prefix="KIT "):
    """Create objects for landmark-contract parts outside build_stage (demo / tests): materials from
    `mats` ({name: bpy material}) in material_slots order, ignore_render / ignore_collision when Fast64 is
    loaded, parented to `parent`. Returns the objects."""
    import bpy
    coll = collection or bpy.context.scene.collection
    out = []
    for p in parts:
        me = p["mesh"]
        idx = [poly.material_index for poly in me.polygons]
        me.materials.clear()
        for s in p["material_slots"]:
            me.materials.append(mats[s])
        me.polygons.foreach_set("material_index", idx)
        me.update()
        ob = bpy.data.objects.new(prefix + p["name"], me)
        coll.objects.link(ob)
        if hasattr(ob, "ignore_collision"):
            ob.ignore_collision = not p["collision"]
            ob.ignore_render = not p["visual"]
        if parent is not None:
            ob.parent = parent
        ob["sgl_kit_part"] = p["name"]
        ob["sgl_kit_visual"] = bool(p["visual"])
        out.append(ob)
    return out


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def preview_material(name, cull=True):
    """Plain Blender preview material (no Fast64 needed): texture (sRGB) x the baked "Col" shade (sRGB),
    multiplied in gamma space like the N64, as emission; glass blends at its alpha, cut-outs clip. COL
    materials get a flat debug colour."""
    import bpy
    from stage_palette import TEXTURE_DIR
    mname = "KITPV " + name
    m = bpy.data.materials.get(mname)
    if m:
        return m
    m = bpy.data.materials.new(mname)
    m.use_nodes = True
    m.use_backface_culling = cull
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links
    for nd in list(N):
        N.remove(nd)
    out = N.new("ShaderNodeOutputMaterial")
    emit = N.new("ShaderNodeEmission")
    if name in COL_NAMES:
        col = {COL: (0.55, 0.62, 0.75), COL_NOCAM: (0.95, 0.6, 0.25), COL_NOTSLIP: (0.35, 0.8, 0.4),
               COL_HANG: (0.85, 0.35, 0.85)}[name]
        geo = N.new("ShaderNodeNewGeometry")
        dot = N.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = (0.35, 0.55, 0.76)
        Lk.new(geo.outputs["Normal"], dot.inputs[0])
        mr = N.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = -1.0
        mr.inputs["To Min"].default_value = 0.45
        Lk.new(dot.outputs["Value"], mr.inputs["Value"])
        mul = N.new("ShaderNodeVectorMath")
        mul.operation = "SCALE"
        mul.inputs[0].default_value = tuple(_srgb_to_linear(c) for c in col)
        Lk.new(mr.outputs[0], mul.inputs["Scale"])
        Lk.new(mul.outputs[0], emit.inputs["Color"])
        Lk.new(emit.outputs[0], out.inputs["Surface"])
        return m
    ent = palette_entry(name)
    img = bpy.data.images.load(os.path.join(TEXTURE_DIR, ent["tex"]), check_existing=True)
    tex = N.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "REPEAT"
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    Lk.new(uv.outputs["UV"], tex.inputs["Vector"])
    g1 = N.new("ShaderNodeGamma")
    g1.inputs["Gamma"].default_value = 1 / 2.2
    Lk.new(tex.outputs["Color"], g1.inputs["Color"])
    attr = N.new("ShaderNodeAttribute")
    attr.attribute_name = "Col"
    g2 = N.new("ShaderNodeGamma")
    g2.inputs["Gamma"].default_value = 1 / 2.2
    Lk.new(attr.outputs["Color"], g2.inputs["Color"])
    mul = N.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    Lk.new(g1.outputs[0], mul.inputs[0])
    if ent.get("lit", "vertex") == "vertex" or name in INTERIOR_MATERIALS:
        Lk.new(g2.outputs[0], mul.inputs[1])
    else:
        mul.inputs[1].default_value = (0.85, 0.85, 0.85)
    g3 = N.new("ShaderNodeGamma")
    g3.inputs["Gamma"].default_value = 2.2
    Lk.new(mul.outputs[0], g3.inputs["Color"])
    Lk.new(g3.outputs[0], emit.inputs["Color"])
    kind = ent.get("kind", "opaque")
    if kind == "opaque":
        Lk.new(emit.outputs[0], out.inputs["Surface"])
        return m
    tr = N.new("ShaderNodeBsdfTransparent")
    ms = N.new("ShaderNodeMixShader")
    if kind == "cutout":
        gt = N.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        Lk.new(tex.outputs["Alpha"], gt.inputs[0])
        Lk.new(gt.outputs[0], ms.inputs[0])
        m.use_backface_culling = False
    else:
        ms.inputs[0].default_value = float(ent.get("alpha", 0.5))
        m.use_backface_culling = False
    Lk.new(tr.outputs[0], ms.inputs[1])
    Lk.new(emit.outputs[0], ms.inputs[2])
    Lk.new(ms.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "DITHERED" if kind == "cutout" else "BLENDED"
    except Exception:  # noqa: BLE001
        m.blend_method = "CLIP" if kind == "cutout" else "BLEND"
    return m


# ================================================================== checks (pure Python)
def collision_issues(km, base_z=None, tol=1e-4):
    """Problems of a collision mesh that should be closed: edges used by one face only (allowed on the
    planes z in base_z, a number or a list: the open bottoms of blocks standing on a floor / landing /
    desk) and a negative signed volume (normals pointing in). Returns a list of strings."""
    edges = {}

    def key(p):
        return (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    vol = 0.0
    for p in km.polys:
        pts = p.pts
        n = newell(pts)
        c = tuple(sum(v[i] for v in pts) / len(pts) for i in range(3))
        vol += _dot(c, n) / 2.0 / 3.0
        for a, b in zip(pts, pts[1:] + pts[:1]):
            ka, kb = key(a), key(b)
            if ka == kb:
                continue
            e = (ka, kb) if ka < kb else (kb, ka)
            edges[e] = edges.get(e, 0) + 1
    zs = [] if base_z is None else ([base_z] if isinstance(base_z, (int, float)) else list(base_z))
    bz = {round(z / tol) for z in zs}
    open_e = [e for e, n in edges.items() if n % 2 == 1 and not (e[0][2] in bz and e[1][2] == e[0][2])]
    out = []
    if open_e:
        out.append(f"{len(open_e)} open edges (first {open_e[0]})")
    if vol <= 0:
        out.append(f"signed volume {vol:.3f} <= 0 (normals inward?)")
    return out


def uv_span_issues(km, limit=UV_SPAN_MAX):
    out = []
    for p in km.polys:
        uvs = p.uvs or project_uv(p.pts, palette_entry(p.mat)["tile_m"])
        su = max(u for u, _ in uvs) - min(u for u, _ in uvs)
        sv = max(v for _, v in uvs) - min(v for _, v in uvs)
        if max(su, sv) > limit:
            out.append(f"{p.mat}: a face spans {max(su, sv):.1f} repeats")
    return out


def all_props():
    """Every builder with its defaults (plus a few variants): {label: Prop}. Used by --selftest and the demo."""
    return {
        "room_shell": room_shell(12.0, 9.0, 6.0, openings=[
            {"wall": "s", "at": 6.0, "w": 2.4, "h": 3.0, "kind": "door"},
            {"wall": "n", "at": 6.0, "w": 7.5, "z0": 0.9, "h": 1.8, "kind": "window"},
            {"wall": "e", "at": 4.5, "w": 4.5, "z0": 0.9, "h": 2.4, "kind": "glass"}]),
        "slab": slab(12.0, 9.0, holes=[(4.0, 3.0, 8.0, 6.0)]),
        "column": column(),
        "window_band": window_band(6.0),
        "door_frame": door_frame(),
        "stair_flight": stair_flight(2.1, rails=("l", "r")),
        "stair_flight_slab": stair_flight(2.1, solid=False),
        "landing": landing(3.2, 1.6),
        "switchback_stair": switchback_stair(),
        "straight_stair": straight_stair(),
        "railing": railing([(0, 0), (4, 0), (4, 3)]),
        "railing_glass": railing([(0, 0), (4, 0)], infill="glass"),
        "elevator": elevator((0.0, 4.2, 8.4), open_floors=(2,)),
        "bookshelf": bookshelf(end_caps=("+x",)),
        "stack_range": stack_range(3, heights=(REAL["stack_counter_h"], REAL["stack_mid_h"], REAL["stack_full_h"])),
        "study_table": study_table(),
        "chair": chair(),
        "stool": stool(),
        "kick_stool": kick_stool(),
        "carrel_row": carrel_row(),
        "computer_row": computer_row(),
        "computer_row_double": computer_row(3, double=True),
        "study_room": study_room(),
        "help_desk": help_desk(),
        "cafe_counter": cafe_counter(),
        "couch": couch(),
        "beanbag": beanbag(),
        "book_cart": book_cart(),
        "kiosk": kiosk(),
        "whiteboard": whiteboard(),
        "poster": poster(),
        "sign_wall": sign("int_sign_quiet"),
        "sign_hanging": sign("int_sign_marston", mount="hanging"),
        "sign_post": sign("int_sign_out_of_order", 0.8, 0.4, 1.2, mount="post"),
        "floor_sign": floor_sign("3"),
        "ceiling_light": ceiling_light(),
        "light_grid": light_grid(8.0, 6.0),
        "light_ring": light_ring(),
    }


def selftest(verbose=True):
    """Pure-Python checks of every builder: materials, closed outward collision, UV spans, SM64 numbers."""
    errors = []
    props = all_props()
    rows = []
    for label, P in props.items():
        for poly in P.visual.polys + P.collision.polys:
            if not known_material(poly.mat):
                errors.append(f"{label}: unknown material {poly.mat}")
            if len(poly.ao) != len(poly.pts):
                errors.append(f"{label}: ao length mismatch")
        for poly in P.collision.polys:
            if poly.mat not in COL_NAMES:
                errors.append(f"{label}: collision face uses {poly.mat} (expected a COL material)")
        if P.info.get("col_closed", True) and P.collision.polys:
            for issue in collision_issues(P.collision, base_z=[0.0] + list(P.info.get("rest_z", []))):
                errors.append(f"{label}: collision {issue}")
        for issue in uv_span_issues(P.visual):
            errors.append(f"{label}: {issue}")
        b = P.visual.bounds()
        rows.append((label, P.tris()["visual"], P.tris()["collision"], b))
    # SM64 sizing
    for rise in (2.1, 4.2, 2.8):
        n, r, t = stair_steps(rise)
        deg = math.degrees(math.atan2(rise, (n - 0.5) * t))
        if r > REAL["riser_max"] + 1e-9 or deg > STAIR_MAX_DEG + 1e-6 or deg >= SLIDE_DEG:
            errors.append(f"stair {rise} m: riser {r:.3f}, ramp {deg:.1f} deg")
    bs = props["bookshelf"]
    if bs.info["depth"] < 0.5:
        errors.append("bookshelf top too narrow to stand on")
    if bs.info["top_z"] > LEDGE_GRAB_M + 0.6:
        errors.append("bookshelf too tall to grab from the end-cap step")
    sr = props["study_room"]
    gap = sr.info["door_gap"]
    if gap["width"] < 2 * 0.37 or gap["height"] < MARIO_HEIGHT_M + 0.2:
        errors.append(f"study room door gap too small {gap}")
    ring = props["light_ring"]
    if not any(p.mat == COL_HANG for p in ring.collision.polys):
        errors.append("light ring has no hangable underside")
    # placement round trip: a placed prop keeps its tri counts and moves its anchors
    k = Kit()
    p = k.add(study_room(), 10.0, 5.0, 4.2, 90.0, tag="sr")
    ax, ay, az, af = k.anchors()["sr.door"]
    if abs(az - 4.2) > 1e-6 or abs(af - 90.0) > 1e-6:
        errors.append(f"anchor transform wrong: {(ax, ay, az, af)}")
    if p.tris() != study_room().tris():
        errors.append("placement changed the tri count")
    # lighting sanity
    L = Lighting([Light((0, 0, 3.0), radius=6.0)])
    up, down = L.shade((0, 0, 0), (0, 0, 1)), L.shade((0, 0, 3.5), (0, 0, -1))
    if not (up[0] > down[0] and max(up) <= 1.0):
        errors.append(f"lighting: floor {up} vs ceiling {down}")
    if verbose:
        print(f"{'prop':24s} {'visual':>7s} {'coll':>6s}  size (m)")
        for label, v, c, b in rows:
            size = "" if b is None else " x ".join(f"{b[1][i] - b[0][i]:.2f}" for i in range(3))
            print(f"{label:24s} {v:7d} {c:6d}  {size}")
        n, r, t = stair_steps(2.1)
        print(f"stairs (2.1 m flight): {n} risers x {r * 100:.1f} cm, treads {t * 100:.1f} cm, "
              f"ramp {math.degrees(math.atan2(2.1, (n - 0.5) * t)):.1f} deg")
        print("selftest:", "OK" if not errors else f"{len(errors)} problem(s)")
        for e in errors:
            print("  -", e)
    return errors


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    print(__doc__)
