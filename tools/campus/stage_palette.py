"""Material table of the campus stage generator (pure Python: used by make_textures.py under the
tools venv and by build_stage.py inside Blender).

Every material is an F3D fog material with one RGBA16 texture from art/levels/textures/.
kind: "opaque" (layer 1), "cutout" (layer 4, 1-bit alpha), "water" (layer 5, translucent).
tile_m: metres per texture repeat for projected UVs (walls with window bays use explicit UVs).
The landmark palette (landmarks/_common.PALETTE) is merged in with the same fields.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from landmarks._common import PALETTE  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TEXTURE_DIR = os.path.join(PROJECT_ROOT, "art", "levels", "textures")

GENERATOR_MATERIALS = {
    # ground
    "ground_grass":   {"tex": "ground_grass.png",   "tile_m": 4.0, "color": "#5A8C3C"},
    "lawn":           {"tex": "lawn.png",           "tile_m": 4.0, "color": "#6AA346"},
    "forest_floor":   {"tex": "forest_floor.png",   "tile_m": 4.0, "color": "#4E6E34"},
    "mulch":          {"tex": "mulch.png",          "tile_m": 2.0, "color": "#6E4A30"},
    "asphalt":        {"tex": "asphalt.png",        "tile_m": 4.0, "color": "#4C4C50"},
    "parking":        {"tex": "parking.png",        "tile_m": 4.0, "color": "#5A5A5E"},
    "road_paint":     {"tex": "road_paint.png",     "tile_m": 2.0, "color": "#E2BE3C"},
    "crosswalk":      {"tex": "crosswalk.png",      "tile_m": 2.0, "color": "#9A9A98"},
    "sidewalk":       {"tex": "sidewalk.png",       "tile_m": 3.0, "color": "#C8C2B4"},
    "steps":          {"tex": "steps.png",          "tile_m": 1.0, "color": "#B4AEA2"},
    "pond_bed":       {"tex": "pond_bed.png",       "tile_m": 4.0, "color": "#3E4A30"},
    "pond_water":     {"tex": "pond_water.png",     "tile_m": 6.0, "color": "#3A72A8", "kind": "water", "alpha": 0.72},
    # buildings
    "facade_gothic":  {"tex": "facade_gothic.png",  "tile_m": 4.0, "color": "#9C5038"},
    "facade_brick":   {"tex": "facade_brick.png",   "tile_m": 4.0, "color": "#9A5340"},
    "facade_band":    {"tex": "facade_band.png",    "tile_m": 4.0, "color": "#8A5446"},
    "facade_glass":   {"tex": "facade_glass.png",   "tile_m": 4.0, "color": "#5E8098"},
    "facade_service": {"tex": "facade_service.png", "tile_m": 4.0, "color": "#A0583E"},
    "roof_gravel":    {"tex": "roof_gravel.png",    "tile_m": 4.0, "color": "#7C7A76"},
    "door_marker":    {"tex": "door_marker.png",    "tile_m": 1.0, "color": "#FA4616"},
    # set dressing: UF orange / blue lamp-post banners and tabling-table cloths
    "banner_orange":  {"tex": "banner_orange.png",  "tile_m": 1.0, "color": "#F05A28"},
    "banner_blue":    {"tex": "banner_blue.png",    "tile_m": 1.0, "color": "#1E3A9C"},
    # vegetation
    "leaves_oak":     {"tex": "leaves_oak.png",     "tile_m": 4.0, "color": "#3E6E2E"},
    "leaves_oak2":    {"tex": "leaves_oak2.png",    "tile_m": 4.0, "color": "#4A6A2C"},
    "leaves_pine":    {"tex": "leaves_pine.png",    "tile_m": 4.0, "color": "#365C3A"},
    "palm_frond":     {"tex": "palm_frond.png",     "tile_m": 2.0, "color": "#5A9440"},
    "bark":           {"tex": "bark.png",           "tile_m": 2.0, "color": "#5A4632"},
    "palm_trunk":     {"tex": "palm_trunk.png",     "tile_m": 2.0, "color": "#8A7A62"},
    "treeline":       {"tex": "treeline.png",       "tile_m": 24.0, "color": "#3A5E32", "kind": "cutout"},
    "forest_wall":    {"tex": "forest_wall.png",    "tile_m": 8.0, "color": "#33502C"},
}

MATERIALS = {}
for _name, _m in PALETTE.items():
    MATERIALS[_name] = dict(_m, kind=_m.get("kind", "water" if _name == "water" else "opaque"))
for _name, _m in GENERATOR_MATERIALS.items():
    MATERIALS[_name] = dict(_m, kind=_m.get("kind", "opaque"))
MATERIALS["water"].setdefault("alpha", 0.72)

# ------------------------------------------------------------------ interior kit materials (opt-in)
# The int_* materials of tools/campus/interior_kit.py (Course 4 Marston Science Library; later Library
# West and the Century Tower interior). Deliberately NOT merged into MATERIALS: make_materials() / tiles()
# and every outdoor stage build stay exactly as they were. An interior build adds them with
# stage_materials.make_interior_materials() + interior_tiles(); make_textures.py writes their PNGs into
# art/levels/textures/ next to the others (build_interior()).
# Extra fields:
#   "lit": "vertex"  baked lighting: G_LIGHTING off, the shade is the mesh's "Col" vertex colour (the kit
#                    bakes ambient, AO and the ceiling lights into it); "normal" = shaded like the campus.
#   "map": "tile"    projected UVs, one repeat per tile_m metres; "once" = the kit maps the whole texture
#                    (or an atlas cell) onto one panel: signs, screens, doors, the window view.
#   kind "water" here means any translucent sheet (layer 5, prim alpha "alpha"): glass partitions.
INTERIOR_MATERIALS = {
    # floors / walls / ceilings
    "int_carpet":            {"tex": "int_carpet.png",            "tile_m": 2.0, "color": "#46597A"},
    "int_carpet_accent":     {"tex": "int_carpet_accent.png",     "tile_m": 2.0, "color": "#B4532E"},
    "int_floor_tile":        {"tex": "int_floor_tile.png",        "tile_m": 1.2, "color": "#CAC4B4"},
    "int_stone":             {"tex": "int_stone.png",             "tile_m": 1.0, "color": "#B0AAA2"},
    "int_drywall":           {"tex": "int_drywall.png",           "tile_m": 2.0, "color": "#E4DED0"},
    "int_wall_blue":         {"tex": "int_wall_blue.png",         "tile_m": 2.0, "color": "#2C4A8E"},
    "int_ceiling":           {"tex": "int_ceiling.png",           "tile_m": 1.2, "color": "#E2E0D8"},
    "int_light":             {"tex": "int_light.png",             "tile_m": 0.6, "color": "#F2F2EC", "map": "once"},
    # stacks: books are 64 x 32 = 2 m x 0.8 m (two shelf rows; the kit maps v to whole rows)
    "int_books":             {"tex": "int_books.png",             "tile_m": 2.0, "color": "#6A4A3E", "map": "once"},
    "int_books_b":           {"tex": "int_books_b.png",           "tile_m": 2.0, "color": "#3E3E4A", "map": "once"},
    "int_shelf_steel":       {"tex": "int_shelf_steel.png",       "tile_m": 1.0, "color": "#C8C0AA"},
    # furniture
    "int_wood":              {"tex": "int_wood.png",              "tile_m": 1.0, "color": "#B88A58"},
    "int_wood_dark":         {"tex": "int_wood_dark.png",         "tile_m": 1.0, "color": "#6A4A32"},
    "int_glass":             {"tex": "int_glass.png",             "tile_m": 2.0, "color": "#9CC4D8", "kind": "water",
                              "alpha": 0.42},
    "int_rail_bars":         {"tex": "int_rail_bars.png",         "tile_m": 1.0, "color": "#4E5256", "kind": "cutout"},
    "int_metal":             {"tex": "int_metal.png",             "tile_m": 1.0, "color": "#A8ACB0"},
    "int_plastic":           {"tex": "int_plastic.png",           "tile_m": 1.0, "color": "#2E3034"},
    "int_fabric_orange":     {"tex": "int_fabric_orange.png",     "tile_m": 0.5, "color": "#E2642C"},
    "int_fabric_blue":       {"tex": "int_fabric_blue.png",       "tile_m": 0.5, "color": "#2E4C9A"},
    "int_fabric_green":      {"tex": "int_fabric_green.png",      "tile_m": 0.5, "color": "#4E8A5A"},
    # panels mapped once
    "int_whiteboard":        {"tex": "int_whiteboard.png",        "tile_m": 2.4, "color": "#E4E6E6", "map": "once"},
    "int_monitor":           {"tex": "int_monitor.png",           "tile_m": 0.5, "color": "#2A4E96", "map": "once"},
    "int_kiosk":             {"tex": "int_kiosk.png",             "tile_m": 0.5, "color": "#9AAAC8", "map": "once"},
    "int_elevator":          {"tex": "int_elevator.png",          "tile_m": 2.0, "color": "#A4AAAE", "map": "once"},
    "int_stair":             {"tex": "int_stair.png",             "tile_m": 1.0, "color": "#8E8A84"},
    "int_window":            {"tex": "int_window.png",            "tile_m": 3.0, "color": "#7EA0B8", "map": "once"},
    "int_posters":           {"tex": "int_posters.png",           "tile_m": 1.2, "color": "#7A5A5A", "map": "once"},
    "int_sign_quiet":        {"tex": "int_sign_quiet.png",        "tile_m": 1.2, "color": "#4A5EB8", "map": "once"},
    "int_sign_out_of_order": {"tex": "int_sign_out_of_order.png", "tile_m": 1.2, "color": "#C8A030", "map": "once"},
    "int_sign_study":        {"tex": "int_sign_study.png",        "tile_m": 1.2, "color": "#4A4EA8", "map": "once"},
    "int_sign_help":         {"tex": "int_sign_help.png",         "tile_m": 1.2, "color": "#F07040", "map": "once"},
    "int_sign_cafe":         {"tex": "int_sign_cafe.png",         "tile_m": 1.2, "color": "#4A564A", "map": "once"},
    "int_sign_marston":      {"tex": "int_sign_marston.png",      "tile_m": 1.2, "color": "#3A50B4", "map": "once"},
    "int_sign_floors":       {"tex": "int_sign_floors.png",       "tile_m": 0.6, "color": "#2A3AA8", "map": "once"},
}
for _m in INTERIOR_MATERIALS.values():
    _m.setdefault("kind", "opaque")
    _m.setdefault("lit", "vertex")
    _m.setdefault("map", "tile")
INTERIOR_NAMES = tuple(INTERIOR_MATERIALS)


def material(name):
    """Palette entry of an outdoor (MATERIALS) or interior kit (INTERIOR_MATERIALS) material."""
    m = MATERIALS.get(name)
    return m if m is not None else INTERIOR_MATERIALS[name]


def all_materials():
    """MATERIALS + INTERIOR_MATERIALS (a new dict; MATERIALS itself is unchanged)."""
    out = dict(MATERIALS)
    out.update(INTERIOR_MATERIALS)
    return out


def texture_path(name):
    return os.path.join(TEXTURE_DIR, material(name)["tex"])
