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
# Course 4 photo-reference pass (Marston Science Library, tools/campus/interiors/marston.py): its own int_ms_*
# materials, from the reference photos (reference/interiors/marston/). Additive: entries no other stage uses, so
# Library West / outdoor builds export exactly as before (Fast64 only writes the materials a mesh uses).
INTERIOR_MATERIALS.update({
    # floors / ceilings
    "int_ms_carpet":          {"tex": "int_ms_carpet.png",          "tile_m": 1.2, "color": "#4E4842"},
    "int_ms_carpet_f1":       {"tex": "int_ms_carpet_f1.png",       "tile_m": 1.2, "color": "#4A4A6C"},
    "int_ms_vinyl":           {"tex": "int_ms_vinyl.png",           "tile_m": 1.2, "color": "#86A4B8"},
    "int_ms_plank":           {"tex": "int_ms_plank.png",           "tile_m": 1.2, "color": "#9A8670"},
    "int_ms_mat":             {"tex": "int_ms_mat.png",             "tile_m": 1.0, "color": "#3E3E40"},
    "int_ms_coffer":          {"tex": "int_ms_coffer.png",          "tile_m": 1.5, "color": "#DCD6CA"},
    "int_ms_lay_in":          {"tex": "int_ms_lay_in.png",          "tile_m": 0.6, "color": "#F6F6F0", "map": "once"},
    "int_ms_louver":          {"tex": "int_ms_louver.png",          "tile_m": 1.2, "color": "#E8E8E4", "map": "once"},
    "int_ms_diffuser":        {"tex": "int_ms_diffuser.png",        "tile_m": 0.6, "color": "#C8C6C0", "map": "once"},
    "int_ms_led":             {"tex": "int_ms_led.png",             "tile_m": 1.0, "color": "#FFFFFF", "map": "once"},
    # walls / cladding / millwork
    "int_ms_brick":           {"tex": "int_ms_brick.png",           "tile_m": 0.84, "color": "#A85640"},
    "int_ms_copper":          {"tex": "int_ms_copper.png",          "tile_m": 1.2, "color": "#A8704C"},
    "int_ms_veneer":          {"tex": "int_ms_veneer.png",          "tile_m": 1.0, "color": "#B0683A"},
    "int_ms_perf":            {"tex": "int_ms_perf.png",            "tile_m": 0.5, "color": "#D2D2CE"},
    "int_ms_maple":           {"tex": "int_ms_maple.png",           "tile_m": 1.0, "color": "#E4CEA4"},
    "int_ms_slats":           {"tex": "int_ms_slats.png",           "tile_m": 0.8, "color": "#C8782C"},
    "int_ms_pegboard":        {"tex": "int_ms_pegboard.png",        "tile_m": 1.0, "color": "#E6E6E2"},
    "int_ms_butcher":         {"tex": "int_ms_butcher.png",         "tile_m": 0.8, "color": "#C89C64"},
    # upholstery
    "int_ms_leather":         {"tex": "int_ms_leather.png",         "tile_m": 0.6, "color": "#EEE8E0"},
    "int_ms_fab_geo":         {"tex": "int_ms_fab_geo.png",         "tile_m": 0.5, "color": "#A8AAA6"},
    "int_ms_fab_dark":        {"tex": "int_ms_fab_dark.png",        "tile_m": 0.5, "color": "#3C3C40"},
    "int_ms_fab_multi":       {"tex": "int_ms_fab_multi.png",       "tile_m": 0.5, "color": "#DAD2C2"},
    "int_ms_felt":            {"tex": "int_ms_felt.png",            "tile_m": 0.6, "color": "#5E605E"},
    "int_ms_mesh":            {"tex": "int_ms_mesh.png",            "tile_m": 0.3, "color": "#5C5E62"},
    # collections (64 x 32 = 2 m x two shelf rows, mapped like int_books)
    "int_ms_bound":           {"tex": "int_ms_bound.png",           "tile_m": 2.0, "color": "#6A4A44", "map": "once"},
    "int_ms_theses":          {"tex": "int_ms_theses.png",          "tile_m": 2.0, "color": "#2C3236", "map": "once"},
    "int_ms_stacks":          {"tex": "int_ms_stacks.png",          "tile_m": 2.0, "color": "#6A5A54", "map": "once"},
    # signs, screens, decals (mapped once)
    "int_ms_sign_service":    {"tex": "int_ms_sign_service.png",    "tile_m": 1.2, "color": "#F2C430", "map": "once"},
    "int_ms_sign_highlights": {"tex": "int_ms_sign_highlights.png", "tile_m": 1.2, "color": "#F2F2EE", "map": "once"},
    "int_ms_sign_newbooks":   {"tex": "int_ms_sign_newbooks.png",   "tile_m": 1.2, "color": "#F2F2EE", "map": "once"},
    "int_ms_neon_maker":      {"tex": "int_ms_neon_maker.png",      "tile_m": 1.2, "color": "#E8C030", "map": "once",
                               "kind": "cutout"},
    "int_ms_neon_open":       {"tex": "int_ms_neon_open.png",       "tile_m": 1.0, "color": "#FFD84A", "map": "once",
                               "kind": "cutout"},
    # iteration 4 (fidelity-2, #51): the makerspace west door's red OPEN sign (white letters)
    "int_ms_open_sign":       {"tex": "int_ms_open_sign.png",       "tile_m": 0.4, "color": "#D42A20", "map": "once"},
    "int_ms_glass_444":       {"tex": "int_ms_glass_444.png",       "tile_m": 1.2, "color": "#F4F4F0", "map": "once",
                               "kind": "cutout"},
    "int_ms_sign_rest":       {"tex": "int_ms_sign_rest.png",       "tile_m": 1.2, "color": "#2E2C2C", "map": "once"},
    "int_ms_wc_plaques":      {"tex": "int_ms_wc_plaques.png",      "tile_m": 1.2, "color": "#3A3C40", "map": "once"},
    "int_ms_names":           {"tex": "int_ms_names.png",           "tile_m": 1.2, "color": "#3A3C40", "map": "once"},
    "int_ms_names_b":         {"tex": "int_ms_names_b.png",         "tile_m": 1.2, "color": "#3A3C40", "map": "once"},
    "int_ms_exit":            {"tex": "int_ms_exit.png",            "tile_m": 0.4, "color": "#EEEDE8", "map": "once"},
    "int_ms_order":           {"tex": "int_ms_order.png",           "tile_m": 0.8, "color": "#1E8A72", "map": "once"},
    "int_ms_cafe_decal":      {"tex": "int_ms_cafe_decal.png",      "tile_m": 1.0, "color": "#1E6A4A", "map": "once",
                               "kind": "cutout"},
    "int_ms_projector":       {"tex": "int_ms_projector.png",       "tile_m": 2.0, "color": "#88AEF8", "map": "once"},
    "int_ms_directory":       {"tex": "int_ms_directory.png",       "tile_m": 0.8, "color": "#34363A", "map": "once"},
    "int_ms_aquarium":        {"tex": "int_ms_aquarium.png",        "tile_m": 1.8, "color": "#0C1812", "map": "once"},
    "int_ms_vending":         {"tex": "int_ms_vending.png",         "tile_m": 1.0, "color": "#6A4E9A", "map": "once"},
    "int_ms_vend_graphic":    {"tex": "int_ms_vend_graphic.png",    "tile_m": 0.8, "color": "#B05A6A", "map": "once"},
    "int_ms_tv":              {"tex": "int_ms_tv.png",              "tile_m": 1.2, "color": "#18191C", "map": "once"},
    "int_ms_logo":            {"tex": "int_ms_logo.png",            "tile_m": 1.2, "color": "#E6E6E4", "map": "once"},
    "int_ms_tile":            {"tex": "int_ms_tile.png",            "tile_m": 1.2, "color": "#ECEAE4"},
    "int_ms_bins":            {"tex": "int_ms_bins.png",            "tile_m": 1.2, "color": "#9AA0A6", "map": "once"},
    "int_ms_wall":            {"tex": "int_ms_wall.png",            "tile_m": 1.2, "color": "#EEEBE3"},
    "int_ms_print_poster":    {"tex": "int_ms_print_poster.png",    "tile_m": 1.2, "color": "#C8CCD8", "map": "once"},
    "int_ms_exit_door":       {"tex": "int_ms_exit_door.png",       "tile_m": 1.0, "color": "#6E7884", "map": "once"},
    # fidelity-1: study-room names lettered on the F1 bulkheads (cut-out), clear study-room front glass
    "int_ms_bnames_0":        {"tex": "int_ms_bnames_0.png",        "tile_m": 1.2, "color": "#45474C", "map": "once",
                               "kind": "cutout"},
    "int_ms_bnames_1":        {"tex": "int_ms_bnames_1.png",        "tile_m": 1.2, "color": "#45474C", "map": "once",
                               "kind": "cutout"},
    "int_ms_bnames_2":        {"tex": "int_ms_bnames_2.png",        "tile_m": 1.2, "color": "#45474C", "map": "once",
                               "kind": "cutout"},
    "int_ms_bnames_3":        {"tex": "int_ms_bnames_3.png",        "tile_m": 1.2, "color": "#45474C", "map": "once",
                               "kind": "cutout"},
    "int_ms_glass_clear":     {"tex": "int_ms_glass_clear.png",     "tile_m": 2.0, "color": "#E4ECEE", "kind": "water",
                               "alpha": 0.30},
    "int_ms_roomnum_0":       {"tex": "int_ms_roomnum_0.png",       "tile_m": 1.2, "color": "#3A3C40", "map": "once"},
    "int_ms_roomnum_1":       {"tex": "int_ms_roomnum_1.png",       "tile_m": 1.2, "color": "#3A3C40", "map": "once"},
    "int_ms_roomnum_2":       {"tex": "int_ms_roomnum_2.png",       "tile_m": 1.2, "color": "#3A3C40", "map": "once"},
    # fidelity-2: the labs' blue-wallpaper monitors (#61 #63) and the makerspace's 2' x 4' lay-in tile (#54 #56)
    "int_ms_monitor":         {"tex": "int_ms_monitor.png",         "tile_m": 1.0, "color": "#2A6CC0", "map": "once"},
    "int_ms_tile24":          {"tex": "int_ms_tile24.png",          "tile_m": 1.2, "color": "#ECEAE4"},
    # iteration 4 (design r3 #6): galvanised sheet steel inside the F1 vent duct (27 texels/m, two-pixel seams)
    "int_ms_duct":            {"tex": "int_ms_duct.png",            "tile_m": 1.2, "color": "#B4BAC0"},
    # fidelity-3: the porch's near-black storefront glass (#2), the F2 science fiction stacks' spines and end sign,
    # the entrance door vinyl (#1)
    "int_ms_glass_black":     {"tex": "int_ms_glass_black.png",     "tile_m": 1.2, "color": "#1E2226", "map": "once"},
    "int_ms_fiction":         {"tex": "int_ms_fiction.png",         "tile_m": 2.0, "color": "#3A3434", "map": "once"},
    "int_ms_sign_scifi":      {"tex": "int_ms_sign_scifi.png",      "tile_m": 1.2, "color": "#F2F2EE", "map": "once"},
    "int_ms_door_vinyl":      {"tex": "int_ms_door_vinyl.png",      "tile_m": 1.2, "color": "#F2F2EE", "map": "once",
                               "kind": "cutout"},
    "int_ms_sign_stairs":     {"tex": "int_ms_sign_stairs.png",     "tile_m": 1.6, "color": "#2E3440", "map": "once"},
    # fix round 2: the L136 visualization wall's GIS aerial imagery (#48), mapped once over the 3 x 2 display grid
    "int_ms_gis_map":         {"tex": "int_ms_gis_map.png",         "tile_m": 3.0, "color": "#6A9050", "map": "once"},
    # fix round 2: the F1 east study rooms' daylit exterior glass onto the sunken court (#38 4272, #44)
    "int_ms_glass_day":       {"tex": "int_ms_glass_day.png",       "tile_m": 2.0, "color": "#E8F0F4", "kind": "water",
                               "alpha": 0.55},
    # fidelity-2 fix 2: the labs' / benching's pale frosted divider glass (#61 #63 #64), the makerspace TV's lit
    # light-blue slide (#56), the wellness room's patterned blue rug (#74 #75)
    "int_ms_glass_frost":     {"tex": "int_ms_glass_frost.png",     "tile_m": 1.2, "color": "#E6EAEC", "kind": "water",
                               "alpha": 0.72},
    "int_ms_tv_maker":        {"tex": "int_ms_tv_maker.png",        "tile_m": 1.8, "color": "#8CCAF0", "map": "once"},
    "int_ms_rug_blue":        {"tex": "int_ms_rug_blue.png",        "tile_m": 2.0, "color": "#2E5A9A", "map": "once"},
    # design fix round 2: Marston's walkable roof deck, a grey single-ply membrane with lap seams on a 2 m tile
    "int_ms_roof_membrane":   {"tex": "int_ms_roof_membrane.png",   "tile_m": 2.0, "color": "#A2A29E"},
    # iteration 5 (fidelity-1, #69 #37): the floor-1 core's rosier, lighter face brick with pale mortar
    "int_ms_brick_f1":        {"tex": "int_ms_brick_f1.png",        "tile_m": 0.84, "color": "#C48890"},
    # iteration 5 (fidelity-4, #98): the sandy ground under the plaza oaks (Marston backdrop)
    "int_ms_sand":            {"tex": "int_ms_sand.png",            "tile_m": 4.0, "color": "#C8B48E"},
    # iteration 6 (fidelity-3 blocking, #1): the porch bay east of the doors, dark tinted glass with the lit lobby
    "int_ms_glass_lobby":     {"tex": "int_ms_glass_lobby.png",     "tile_m": 1.2, "color": "#3A3834", "map": "once"},
    # iteration 6 (fidelity-3, #35): the Starbucks pickup window, the lit back-of-house kitchen seen through it
    "int_ms_kitchen":         {"tex": "int_ms_kitchen.png",         "tile_m": 1.0, "color": "#D8C8A8", "map": "once"},
})
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
