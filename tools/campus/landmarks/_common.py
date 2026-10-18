"""Shared palette and helpers for hub landmark modules (owned by the campus generator,
tools/campus/build_stage.py; landmark modules may import it, nothing else in the project).

Import it from a landmark module as
    from landmarks import _common as C        # the generator imports modules as package `landmarks`
or  from . import _common as C

LANDMARK MODULE CONTRACT (tools/campus/landmarks/<slug>.py)
  LANDMARKS = [{"slug": str, "name": str, "osm_ids": ["w150860043", ...],   # campus.json buildings it REPLACES
                "center_m": (x, y),
                "doors": [{"name": str, "pos_m": (x, y, z), "facing_deg": deg}]}]   # optional
      facing_deg: compass direction the door faces (0 = north, 90 = east), i.e. the way a player
      walking OUT of the door looks. Optional "primary": True marks the stage door (it gets the
      signpost); without it the first door does.
  Optional entry keys the generator also honours (OSM ids from campus.json / the raw tiles):
      "stages":         [stage keys] the stages.json stages this landmark is built into ("hub", "swamp",
                                     "reitz_eng", "lake_alice", ...). Missing key = ["hub"].
                                     build_stage.py <key> only builds entries whose "stages" contain <key>:
                                     when none of a module's entries list <key>, its build() is not
                                     called at all (module skipped); in a module with mixed entries the parts of the
                                     other entries are dropped (parts are matched to entries by their
                                     "landmark" key, else by the slug their name starts with). ctx gains
                                     "stage_key" (the stage being built) so a module can also branch itself.
      "replaces_ways":  [way ids]   roads / walkways / walls you draw yourself (generator skips them)
      "replaces_areas": [area ids]  lawn / plaza / parking polygons you draw yourself
      "removes_points": [node ids]  trees or props that must not be generated
  Ground you draw must stay at or below z = 0 (the generator's collision floor; its own layers are
  at -0.12 .. -0.03 m): anything above it hides Mario's shadow, which is drawn at the floor.
  A visual-only part flagged "decal": True (walk ribbons, paving) is moved down by the generator so
  its top sits 1.5 cm under the collision floor (still above every generator ground layer).
  Generator behaviour for the other optional keys (build_stage.py / stage_landmarks.py):
      door "primary": True       -> the stage door (gets the signpost) unless stage_landmarks.DOOR_DEFAULTS
                                    names another door of the landmark ("door": "DOOR_<slug>_<n>");
                                    the other doors are listed in the build report with stage None
      entry "osm_area_ids"       -> counted for the stages.json budget (e.g. the plaza)
      entry "spots" / "climb_route_m" / "top_platform" / "markers" / "height_m"
                                 -> copied to art/levels/<stage>/sgl_<stage>_build.json "landmark_extras"
      part "landmark": slug      -> per-landmark budget report (else the slug the part name starts with)
  The generator also drops its own OSM trees / props / walls that end up under your roofs, slabs or
  terraces (stage_landmarks.resolve_conflicts) and shrinks tree crowns to clear your walls.
  Palette additions (generator round 3): "bronze" (statues: the Library West gator) and
  "sign_the_hub" (The Hub's name sign; map the whole 64 x 32 texture once onto a 2:1 panel).
  def build(ctx) -> [{"name": str, "mesh": bpy.types.Mesh, "material_slots": [palette names in
                      face material-index order], "collision": bool, "visual": bool}, ...]
  Geometry in MAP METRES, z up (x = east, y = north, origin = Century Tower); the generator moves it
  into the stage frame. ctx = {"campus": campus.json dict, "stage": the stages.json entry of the stage
  being built, "stage_key": its key ("hub", "swamp", ...), "ground_z": f(x, y) -> 0.0,
  "buildings": {osm_id: campus.json building}, "palette": PALETTE}.
  Doors (hub only): a door may also give "width_m" (door opening width); the hub door trigger
  (mods/sgl64/levels.lua id_bhvSglDoor) uses width / 2 + 0.6 m as its half width. See docs/flow.md.

UVs: optional. A mesh without a UV layer gets planar UVs from the generator (project_uv below:
  floors/roofs top-down, walls along the wall, one texture repeat per PALETTE[name]["tile_m"]
  metres). A mesh with a UV layer keeps it (1.0 = one texture repeat; the generator only shifts
  each face by whole repeats to keep N64 texture coordinates small). Keep a single face under
  ~12 repeats across.
Normals: faces are exported flat-shaded unless you mark them smooth. Make collision meshes closed
  where Mario can touch them, normals pointing out of the solid. Collision faces steeper than ~38
  degrees from horizontal make Mario slide; vertical faces are walls.
Budgets: stages.json stages[hub].landmarks[].collision_tris / visual_tris per landmark.
"""
import math

# name: texture (art/levels/textures/<file>, generated by tools/campus/make_textures.py),
#       tile_m (metres per texture repeat for projected UVs), color (average sRGB, used for previews
#       and the material light tint), surface (collision type when the part has collision)
PALETTE = {
    "brick_red":     {"tex": "brick_red.png",     "tile_m": 2.0, "color": "#A9533A"},
    "brick_dark":    {"tex": "brick_dark.png",    "tile_m": 2.0, "color": "#7A3828"},
    "limestone":     {"tex": "limestone.png",     "tile_m": 2.0, "color": "#D6C8A4"},
    "roof_tile_red": {"tex": "roof_tile_red.png", "tile_m": 2.0, "color": "#B0532F"},
    "roof_dark":     {"tex": "roof_dark.png",     "tile_m": 2.0, "color": "#4C4C52"},
    "copper_green":  {"tex": "copper_green.png",  "tile_m": 2.0, "color": "#5E9C88"},
    "window_dark":   {"tex": "window_dark.png",   "tile_m": 2.0, "color": "#2E3A48"},
    "window_glass":  {"tex": "window_glass.png",  "tile_m": 3.0, "color": "#6E94B4"},
    "door_wood":     {"tex": "door_wood.png",     "tile_m": 2.0, "color": "#6B4226"},
    "concrete":      {"tex": "concrete.png",      "tile_m": 2.0, "color": "#B8B4AA"},
    "metal_gray":    {"tex": "metal_gray.png",    "tile_m": 2.0, "color": "#8A8E92"},
    "plaza_brick":   {"tex": "plaza_brick.png",   "tile_m": 2.0, "color": "#A65A42"},
    "grass":         {"tex": "grass.png",         "tile_m": 4.0, "color": "#5F9A3F"},
    "path":          {"tex": "path.png",          "tile_m": 3.0, "color": "#C6C0B2"},
    "water":         {"tex": "water.png",         "tile_m": 6.0, "color": "#3C78B4"},
    "dark_trim":     {"tex": "dark_trim.png",     "tile_m": 2.0, "color": "#3A3430"},
    "white_trim":    {"tex": "white_trim.png",    "tile_m": 2.0, "color": "#E6E2D8"},
    "rock":          {"tex": "rock.png",          "tile_m": 3.0, "color": "#C2B79F"},   # pale (The Potato)
    "bronze":        {"tex": "bronze.png",        "tile_m": 1.0, "color": "#5E4630"},   # statues (the gator)
    "leaves_oak":    {"tex": "leaves_oak.png",    "tile_m": 4.0, "color": "#3E6E2E"},   # plaza shrubs
    "leaves_oak2":   {"tex": "leaves_oak2.png",   "tile_m": 4.0, "color": "#4A6A2C"},
    # name sign of The Hub: 64 x 32, white "THE HUB" on UF blue with an orange rule; map the whole
    # texture once (UV 0..1) onto a 2:1 panel
    "sign_the_hub":  {"tex": "sign_the_hub.png",  "tile_m": 6.0, "color": "#2A40A8"},
}
PALETTE_NAMES = tuple(PALETTE)

FLOOR_H_M = 4.0      # typical UF academic floor-to-floor height
GROUND_Z = 0.0       # the campus is flat; the collision ground is at z = 0


# ------------------------------------------------------------------ data helpers (pure Python)
def building(ctx, osm_id):
    """campus.json building dict for osm_id (KeyError if it is not in the data)."""
    b = ctx.get("buildings")
    if b is not None:
        return b[osm_id]
    for x in ctx["campus"]["buildings"]:
        if x["id"] == osm_id:
            return x
    raise KeyError(osm_id)


def footprint(ctx, osm_id):
    """Raw OSM footprint of a building, counter-clockwise, [(x, y), ...] in map metres."""
    return ccw([tuple(p) for p in building(ctx, osm_id)["pts"]])


def signed_area(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def ccw(pts):
    return list(pts) if signed_area(pts) >= 0 else list(reversed(pts))


def centroid(pts):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    if abs(a) < 1e-9:
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return (cx / (3 * a), cy / (3 * a))


def face_normal(pts3):
    """Newell normal of a planar polygon [(x, y, z), ...] (not normalised)."""
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(pts3, pts3[1:] + pts3[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def project_uv(pts3, tile_m, normal=None):
    """Planar UVs for one face, in texture repeats, shifted by whole repeats so they start near 0.
    Floors/roofs: top-down (u = x, v = y). Walls: u along the wall, v = z (texture upright)."""
    nx, ny, nz = normal or face_normal(pts3)
    t = max(tile_m, 1e-6)
    if abs(nz) >= max(abs(nx), abs(ny)) * 1.0001:
        uvs = [(p[0] / t, p[1] / t) for p in pts3]
    else:
        L = math.hypot(nx, ny) or 1.0
        hx, hy = -ny / L, nx / L          # horizontal direction along the wall (outward normal x up)
        uvs = [((p[0] * hx + p[1] * hy) / t, p[2] / t) for p in pts3]
    du = math.floor(min(u for u, _ in uvs))
    dv = math.floor(min(v for _, v in uvs))
    return [(u - du, v - dv) for u, v in uvs]


# ------------------------------------------------------------------ mesh building (needs bpy)
class Builder:
    """Collects polygons with palette material names and builds one bpy mesh.

        b = Builder()
        b.poly([(x, y, z), ...], "brick_red")              # projected UVs
        b.poly(pts, "door_wood", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        b.prism(footprint, 0.0, 12.0, "brick_red", top="roof_dark")
        mesh, slots = b.build("Library West visual")
        return [part("Library West visual", mesh, slots, collision=False, visual=True)]
    """

    def __init__(self):
        self.polys = []  # (pts3, material name, uvs or None, smooth)

    def poly(self, pts3, material, uvs=None, normal_hint=None, smooth=False):
        if material not in PALETTE:
            raise ValueError(f"unknown palette material {material!r} (use one of {PALETTE_NAMES})")
        pts3 = [tuple(float(c) for c in p) for p in pts3]
        if len(pts3) < 3:
            return
        if normal_hint is not None:
            n = face_normal(pts3)
            if n[0] * normal_hint[0] + n[1] * normal_hint[1] + n[2] * normal_hint[2] < 0:
                pts3.reverse()
                if uvs is not None:
                    uvs = list(reversed(uvs))
        self.polys.append((pts3, material, uvs, smooth))

    def quad_wall(self, a, b, z0, z1, material, uvs=None):
        """Vertical wall from 2D point a to b (outward normal on the right when walking a -> b
        around a counter-clockwise footprint)."""
        self.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], material, uvs)

    def prism(self, pts2, z0, z1, wall, top=None, bottom=None):
        """Extrude a footprint (any winding) from z0 to z1; outward-facing walls, optional caps."""
        pts2 = ccw(pts2)
        for a, b in zip(pts2, pts2[1:] + pts2[:1]):
            self.quad_wall(a, b, z0, z1, wall)
        if top:
            self.poly([(x, y, z1) for x, y in pts2], top)
        if bottom:
            self.poly([(x, y, z0) for x, y in reversed(pts2)], bottom)

    def box(self, xmin, ymin, zmin, xmax, ymax, zmax, material, top=None, bottom=None):
        self.prism([(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)], zmin, zmax, material,
                   top=top or material, bottom=bottom)

    def tri_count(self):
        return sum(len(p[0]) - 2 for p in self.polys)

    def build(self, name):
        """-> (bpy mesh, material_slots). Non-convex polygons are triangulated by Blender."""
        import bmesh
        import bpy
        slots = []
        for _, m, _, _ in self.polys:
            if m not in slots:
                slots.append(m)
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        for pts3, m, uvs, smooth in self.polys:
            try:
                face = bm.faces.new([bm.verts.new(p) for p in pts3])
            except ValueError:
                continue
            face.material_index = slots.index(m)
            face.smooth = smooth
            if uvs is None:
                uvs = project_uv(pts3, PALETTE[m]["tile_m"])
            for loop, (u, v) in zip(face.loops, uvs):
                loop[uv].uv = (u, v)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        bm.to_mesh(me)
        bm.free()
        return me, slots


def part(name, mesh, material_slots, collision, visual):
    return {"name": name, "mesh": mesh, "material_slots": list(material_slots),
            "collision": bool(collision), "visual": bool(visual)}
