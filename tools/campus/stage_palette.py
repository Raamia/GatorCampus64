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


def texture_path(name):
    return os.path.join(TEXTURE_DIR, MATERIALS[name]["tex"])
