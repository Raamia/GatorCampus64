"""Reitz Union interior kit: the J. Wayne Reitz Union's own materials, N64-style textures, plan geometry
helpers and photo-matched props, for tools/campus/interiors/reitz.py (Course 2 area 2, the Reitz Union
interior of levels/wf). It builds on tools/campus/interior_kit.py (imported, never changed here: the Marston
stage owns it).

    tools/.venv/bin/python -I tools/campus/interior_kit_reitz.py --textures   write art/levels/textures/int_ru_*.png
    tools/.venv/bin/python -I tools/campus/interior_kit_reitz.py --selftest   geometry + prop checks (no Blender)
    tools/.venv/bin/python -I tools/campus/interior_kit_reitz.py --sheet PNG  texture contact sheet

Materials (RU_MATERIALS, "int_ru_*"): additive. register() merges them into stage_palette.INTERIOR_MATERIALS at
import time of THIS module only, so no other stage (outdoor or interior) sees them and every other build exports
exactly as before. The textures come from the reference photos (reference/interiors/reitz/index.json; the photo
each one was sampled from is in its recipe's docstring) and are 32 x 32, 64 x 32 or 32 x 64 RGBA16 (each fits
the 4 KB TMEM, like every other SGL64 texture). Brand marks are not reproduced: the food court storefronts get
generic signs (BURGERS, PIZZA, ...) in the colours of the real counters.

Geometry helpers (pure Python, map metres): polygon cleaning, point-in-polygon, ear-clipping triangulation
(with holes), convex clipping, grid splitting for the vertex-colour bake, polygon offset. Props (pure Python,
interior_kit.Prop in local coordinates, front = local +y, as the kit's convention): bowling lane sets,
billiards, booths, arcade cabinets, esports stations, the atrium lounge set, UF letters, the Swamp Boss gator
head, food court storefronts, theatre chair rows (cut-out row textures), auditorium seating, senate desks,
hotel furniture, ...
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import stage_palette  # noqa: E402

# ================================================================== materials
# name: tex size (w, h), tile_m, colour (sRGB average: previews + Fast64 diffuse), kind, map
# kind: opaque | cutout (1-bit alpha, layer 4) | water (translucent, layer 5); map: tile | once
RU_MATERIALS = {
    # ---- floors
    "int_ru_terrazzo":     {"size": (32, 32), "tile_m": 1.5, "color": "#EAE7E0"},
    "int_ru_carpet_atrium": {"size": (64, 32), "tile_m": 3.0, "color": "#1E2858"},
    "int_ru_gator_track":  {"size": (32, 32), "tile_m": 0.6, "color": "#1E2A5A", "kind": "cutout", "map": "once"},
    "int_ru_lane":         {"size": (32, 32), "tile_m": 1.06, "color": "#D8B07A"},
    "int_ru_lane_arrows":  {"size": (32, 64), "tile_m": 1.06, "color": "#D2A874", "map": "once"},
    "int_ru_plank":        {"size": (64, 32), "tile_m": 2.4, "color": "#8E8C8A"},
    "int_ru_carpet_billiards": {"size": (64, 32), "tile_m": 2.0, "color": "#686C7A"},
    "int_ru_fc_checker":   {"size": (32, 32), "tile_m": 1.7, "color": "#9A7E5E"},
    "int_ru_fc_tile":      {"size": (32, 32), "tile_m": 1.2, "color": "#E0DEDA"},
    "int_ru_carpet_meeting": {"size": (64, 32), "tile_m": 2.4, "color": "#56688E"},
    "int_ru_carpet_ballroom": {"size": (64, 32), "tile_m": 2.6, "color": "#3A72C4"},   # fidelity-4 pass: was 3.6
    "int_ru_maple":        {"size": (64, 32), "tile_m": 1.6, "color": "#CC9C66"},
    "int_ru_dance":        {"size": (32, 32), "tile_m": 2.0, "color": "#2C2C30"},
    "int_ru_carpet_olive": {"size": (32, 32), "tile_m": 1.2, "color": "#5C5838"},
    "int_ru_carpet_grey":  {"size": (32, 32), "tile_m": 1.2, "color": "#9C9A96"},
    "int_ru_carpet_hotel": {"size": (32, 32), "tile_m": 1.2, "color": "#5C6688"},
    "int_ru_carpet_aud":   {"size": (32, 32), "tile_m": 1.6, "color": "#434A5C"},
    "int_ru_concrete_dark": {"size": (32, 32), "tile_m": 2.0, "color": "#5E4E44"},   # fix round 5: was #5C5C5E
    "int_ru_paving":       {"size": (32, 32), "tile_m": 3.0, "color": "#C2BEB4"},
    # ---- walls
    "int_ru_wall":         {"size": (32, 32), "tile_m": 2.0, "color": "#EDEBE6"},
    "int_ru_wall_greyblue": {"size": (32, 32), "tile_m": 2.0, "color": "#CFCCC6"},
    "int_ru_wall_royal":   {"size": (32, 32), "tile_m": 2.0, "color": "#1E3CA0"},
    "int_ru_wall_navy":    {"size": (32, 32), "tile_m": 2.0, "color": "#22283A"},
    "int_ru_wall_grey":    {"size": (32, 32), "tile_m": 2.0, "color": "#B2B4B6"},
    # fix round 4 (fidelity-4 pass; ru_os_auditorium_1..3): the auditorium's mid-grey fabric wall panels
    "int_ru_wall_aud":     {"size": (32, 32), "tile_m": 2.0, "color": "#5E6064"},   # fix round 5: darker (was #86888A)
    # fix round 4 (fidelity-4 pass; ru_os_2345_2350): the boardroom's pale maple laminate table top
    "int_ru_maple_light":  {"size": (32, 32), "tile_m": 1.2, "color": "#DCC8A8"},
    "int_ru_wall_slate":   {"size": (32, 32), "tile_m": 2.0, "color": "#80848A"},
    "int_ru_wall_cream":   {"size": (32, 32), "tile_m": 2.0, "color": "#E8E0CC"},
    "int_ru_hex":          {"size": (32, 32), "tile_m": 1.2, "color": "#15161C"},
    "int_ru_hex_neon":     {"size": (64, 32), "tile_m": 1.6, "color": "#AAC8FF", "kind": "cutout", "map": "once"},
    "int_ru_gator_skin":   {"size": (32, 32), "tile_m": 1.0, "color": "#DEDAD2"},   # fix round 5: 1 m tile, 0.33 m plates
    "int_ru_acoustic":     {"size": (32, 32), "tile_m": 1.2, "color": "#E2E2E0"},
    "int_ru_cherry":       {"size": (32, 32), "tile_m": 1.2, "color": "#8C4026"},
    "int_ru_chevron":      {"size": (64, 32), "tile_m": 9.0, "color": "#B0643C", "map": "once"},
    "int_ru_cedar":        {"size": (32, 32), "tile_m": 1.6, "color": "#C27846"},   # design r2: was 0.8 (crawl)
    "int_ru_brick":        {"size": (32, 32), "tile_m": 2.0, "color": "#A2533C"},
    "int_ru_wood_panel":   {"size": (32, 32), "tile_m": 1.2, "color": "#B07A44"},
    "int_ru_slat_dark":    {"size": (32, 32), "tile_m": 1.2, "color": "#4C3628"},
    "int_ru_mirror":       {"size": (32, 32), "tile_m": 2.0, "color": "#B6C6CE"},
    "int_ru_paint_lime":   {"size": (32, 32), "tile_m": 2.0, "color": "#B6D034"},
    "int_ru_paint_sky":    {"size": (32, 32), "tile_m": 2.0, "color": "#90CADC"},
    "int_ru_counter_front": {"size": (32, 32), "tile_m": 1.0, "color": "#A6D2DE"},
    "int_ru_soffit":       {"size": (32, 32), "tile_m": 2.0, "color": "#ECE6D6"},
    "int_ru_white":        {"size": (32, 32), "tile_m": 2.0, "color": "#F4F4F2"},
    "int_ru_black":        {"size": (32, 32), "tile_m": 1.0, "color": "#1E1F22"},
    "int_ru_steel":        {"size": (32, 32), "tile_m": 1.0, "color": "#B4B8BC"},
    "int_ru_orange":       {"size": (32, 32), "tile_m": 1.0, "color": "#F0561E"},
    "int_ru_uf_blue":      {"size": (32, 32), "tile_m": 1.0, "color": "#1E3C9E"},
    "int_ru_red":          {"size": (32, 32), "tile_m": 1.0, "color": "#C42A26"},
    # ---- ceilings + light
    "int_ru_coffer":       {"size": (32, 32), "tile_m": 1.2, "color": "#F2F2EE"},
    "int_ru_led":          {"size": (32, 32), "tile_m": 1.0, "color": "#FFFFFF"},
    "int_ru_tile_ceiling": {"size": (32, 32), "tile_m": 1.2, "color": "#E4E2DC"},
    # ---- upholstery, felt, plastics
    "int_ru_felt":         {"size": (32, 32), "tile_m": 1.0, "color": "#1E5ACC"},
    "int_ru_leather_navy": {"size": (32, 32), "tile_m": 0.8, "color": "#28366E"},
    "int_ru_leather_grey": {"size": (32, 32), "tile_m": 0.8, "color": "#8E8C8A"},
    "int_ru_fabric_taupe": {"size": (32, 32), "tile_m": 0.6, "color": "#9C8C6E"},
    "int_ru_fabric_navy":  {"size": (32, 32), "tile_m": 0.6, "color": "#232E54"},
    # fix round 2 (fidelity, ru_atrium_enr_lounge): the lounge's dark plum / maroon-brown club chairs
    "int_ru_fabric_plum":  {"size": (32, 32), "tile_m": 0.6, "color": "#5A383E"},
    "int_ru_fabric_char":  {"size": (32, 32), "tile_m": 0.6, "color": "#3A3C40"},
    "int_ru_gator_green":  {"size": (32, 32), "tile_m": 0.5, "color": "#4E6E32"},
    "int_ru_bed":          {"size": (32, 32), "tile_m": 1.0, "color": "#F0F0EC"},
    "int_ru_drape":        {"size": (32, 32), "tile_m": 1.2, "color": "#1C1C22"},
    "int_ru_tablecloth":   {"size": (32, 32), "tile_m": 1.0, "color": "#1C2A5E"},
    # ---- glass (translucent)
    "int_ru_glass":        {"size": (32, 32), "tile_m": 3.0, "color": "#A8CCE0", "kind": "water", "alpha": 0.30},
    "int_ru_glass_blue":   {"size": (32, 32), "tile_m": 3.0, "color": "#5A8CB8", "kind": "water", "alpha": 0.50},
    # ---- railings (cut-out)
    "int_ru_picket":       {"size": (32, 32), "tile_m": 1.1, "color": "#9A9EA2", "kind": "cutout"},
    # ---- chair rows (cut-out, mapped once per 4-chair panel)
    "int_ru_row_navy":     {"size": (64, 32), "tile_m": 2.0, "color": "#26346A", "kind": "cutout", "map": "once"},
    "int_ru_row_black":    {"size": (64, 32), "tile_m": 2.0, "color": "#2A2A2E", "kind": "cutout", "map": "once"},
    "int_ru_row_aud":      {"size": (64, 32), "tile_m": 1.8, "color": "#2A3A6A", "kind": "cutout", "map": "once"},
    "int_ru_row_wood":     {"size": (64, 32), "tile_m": 1.8, "color": "#8A5A30", "kind": "cutout", "map": "once"},
    # fix round 4 (fidelity-4 pass): Rion banquet chairs, dark navy backs in cherry frames (ru_os_rion_ballroom)
    "int_ru_row_rion":     {"size": (64, 32), "tile_m": 2.0, "color": "#1E2442", "kind": "cutout", "map": "once"},
    # ---- doors (32 x 64, one leaf, mapped once)
    "int_ru_door":         {"size": (32, 64), "tile_m": 2.2, "color": "#B07A40", "map": "once"},
    "int_ru_door_walnut":  {"size": (32, 64), "tile_m": 2.4, "color": "#5E3C24", "map": "once"},
    "int_ru_door_glass":   {"size": (32, 64), "tile_m": 2.4, "color": "#4A6478", "map": "once"},
    "int_ru_door_steel":   {"size": (32, 64), "tile_m": 2.2, "color": "#A8ACB0", "map": "once"},
    # ---- screens, signs, art (mapped once)
    "int_ru_video_wall":   {"size": (64, 32), "tile_m": 4.0, "color": "#2850B8", "map": "once"},
    "int_ru_masking":      {"size": (64, 32), "tile_m": 4.0, "color": "#1E2E66", "map": "once"},
    "int_ru_score_tv":     {"size": (32, 32), "tile_m": 1.0, "color": "#2A4AA0", "map": "once"},
    "int_ru_game_screen":  {"size": (32, 32), "tile_m": 1.0, "color": "#4A70A8", "map": "once"},
    "int_ru_arcade":       {"size": (32, 64), "tile_m": 1.8, "color": "#6A3A8A", "map": "once"},
    "int_ru_proj_screen":  {"size": (32, 32), "tile_m": 2.0, "color": "#F2F2F0", "map": "once"},
    "int_ru_sign_gameroom": {"size": (64, 32), "tile_m": 3.0, "color": "#1E2C6A", "map": "once"},
    "int_ru_sign_esports": {"size": (64, 32), "tile_m": 4.0, "color": "#E8F0FF", "kind": "cutout", "map": "once"},
    "int_ru_sign_union":   {"size": (64, 32), "tile_m": 4.0, "color": "#D8D8D8", "kind": "cutout", "map": "once"},
    "int_ru_sign_wayfind": {"size": (64, 32), "tile_m": 1.6, "color": "#1E3C9E", "map": "once"},
    "int_ru_sign_rooms":   {"size": (64, 32), "tile_m": 1.6, "color": "#E8E8E4", "map": "once"},
    "int_ru_sign_ballroom": {"size": (64, 32), "tile_m": 2.4, "color": "#2A2E3A", "map": "once"},
    "int_ru_sign_hotel":   {"size": (64, 32), "tile_m": 2.4, "color": "#1E3C9E", "map": "once"},
    "int_ru_sign_info":    {"size": (64, 32), "tile_m": 2.0, "color": "#1E3C9E", "map": "once"},
    "int_ru_banner_welcome": {"size": (64, 16), "tile_m": 4.0, "color": "#1A2246", "map": "once"},
    "int_ru_sign_foodcourt": {"size": (64, 32), "tile_m": 3.0, "color": "#F05A1E", "map": "once"},
    "int_ru_floor_atlas":  {"size": (64, 32), "tile_m": 0.6, "color": "#1E3C9E", "map": "once"},
    "int_ru_vend_burger":  {"size": (64, 32), "tile_m": 3.0, "color": "#1C2A5E", "map": "once"},
    "int_ru_vend_pizza":   {"size": (64, 32), "tile_m": 3.0, "color": "#2C6A3A", "map": "once"},
    "int_ru_vend_wok":     {"size": (64, 32), "tile_m": 3.0, "color": "#B02420", "map": "once"},
    "int_ru_vend_halal":   {"size": (64, 32), "tile_m": 3.0, "color": "#1E1E22", "map": "once"},
    "int_ru_vend_coffee":  {"size": (64, 32), "tile_m": 3.0, "color": "#1E5A3E", "map": "once"},
    "int_ru_vend_smoothie": {"size": (64, 32), "tile_m": 3.0, "color": "#6A3A8E", "map": "once"},
    "int_ru_vend_mac":     {"size": (64, 32), "tile_m": 3.0, "color": "#E8B020", "map": "once"},
    "int_ru_vend_taco":    {"size": (64, 32), "tile_m": 3.0, "color": "#1E8A86", "map": "once"},
    "int_ru_menu":         {"size": (64, 32), "tile_m": 2.0, "color": "#22262E", "map": "once"},
    "int_ru_art":          {"size": (64, 32), "tile_m": 3.0, "color": "#8A7A6A", "map": "once"},
    "int_ru_photos":       {"size": (64, 32), "tile_m": 3.0, "color": "#D8D0BC", "map": "once"},
    "int_ru_mural_acc":    {"size": (32, 32), "tile_m": 2.4, "color": "#D27A4A", "map": "once"},
    "int_ru_flags":        {"size": (64, 32), "tile_m": 2.0, "color": "#8A5A6A", "map": "once"},
    "int_ru_exit":         {"size": (32, 32), "tile_m": 0.4, "color": "#3A1A1A", "map": "once"},
    "int_ru_dais":         {"size": (64, 32), "tile_m": 2.0, "color": "#9A5A3A", "map": "once"},
    "int_ru_window_view":  {"size": (64, 32), "tile_m": 3.0, "color": "#86A6BC", "map": "once"},
    "int_ru_books":        {"size": (64, 32), "tile_m": 2.0, "color": "#7A5A4A", "map": "once"},
    "int_ru_tv_hotel":     {"size": (32, 32), "tile_m": 1.0, "color": "#26323E", "map": "once"},
    "int_ru_pins":         {"size": (32, 32), "tile_m": 1.0, "color": "#EEEEEA", "map": "once"},
    # ---- food court vendor finishes (fidelity pass 2: each storefront its own front, as in the photos)
    "int_ru_counter_navy": {"size": (32, 32), "tile_m": 1.0, "color": "#0C3A74"},
    "int_ru_counter_red":  {"size": (32, 32), "tile_m": 1.0, "color": "#A82420"},
    "int_ru_mosaic":       {"size": (32, 32), "tile_m": 0.8, "color": "#C89A62"},
    "int_ru_chalkboard":   {"size": (64, 32), "tile_m": 2.0, "color": "#26282A", "map": "once"},
    "int_ru_neon_swirl":   {"size": (32, 32), "tile_m": 1.6, "color": "#1E2652", "map": "once"},
    "int_ru_menu_blue":    {"size": (64, 32), "tile_m": 3.0, "color": "#2A5AA8", "map": "once"},
    # ---- fidelity pass 3 (Ground: meeting rooms, Senate Chamber, esports)
    "int_ru_carpet_chamber": {"size": (32, 32), "tile_m": 1.6, "color": "#1E2648"},
    "int_ru_stone_grey":   {"size": (32, 32), "tile_m": 1.2, "color": "#A4A4A2"},
    "int_ru_wainscot":     {"size": (32, 32), "tile_m": 1.0, "color": "#ECEBE6", "map": "once"},
    "int_ru_prints":       {"size": (64, 32), "tile_m": 1.0, "color": "#B8B0A0", "map": "once"},
    "int_ru_wood_lvt":     {"size": (32, 32), "tile_m": 1.6, "color": "#6E5440"},
    # ---- fidelity pass 4 (ballrooms, upstairs meeting rooms, hotel, elevators, Level 4)
    "int_ru_wall_slateblue": {"size": (32, 32), "tile_m": 2.0, "color": "#8E95A8"},   # fidelity-4 r2: +15 % value
    "int_ru_door_elev":    {"size": (32, 64), "tile_m": 2.2, "color": "#B4B8BC", "map": "once"},
    "int_ru_door_hotel":   {"size": (32, 64), "tile_m": 2.2, "color": "#7A4A2C", "map": "once"},
    "int_ru_call_button":  {"size": (16, 32), "tile_m": 0.4, "color": "#B4B8BC", "map": "once"},
    "int_ru_stone_clad":   {"size": (32, 32), "tile_m": 1.2, "color": "#B8AE9C"},
    "int_ru_shade":        {"size": (32, 32), "tile_m": 1.0, "color": "#C8C6C0", "map": "once"},
    # ---- design pass (wayfinding): one hanging two-face sign per Blue elevator lobby (int_ru_wayfind_<floor> = the
    # north face, _s = the south face; L5 / L6 have no arrows: one texture), UF blue, white caps, an orange rule
    "int_ru_wayfind_LL": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_LL_s": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_G": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_G_s": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L1": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L1_s": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L2": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L2_s": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L3": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L3_s": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L4": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L4_s": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L5": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    "int_ru_wayfind_L6": {"size": (64, 32), "tile_m": 2.4, "color": "#E2E4E6", "map": "once"},
    # fix round 2, fidelity-2 (food court): Sonic-style glow letters, landscape menu screens, a tall neon swirl,
    # vertical-grain maple panels (Starbucks), orange booth upholstery, lay-in troffers, a pastry case, letter-only
    # vendor names (cutout, mounted straight on the fascia)
    "int_ru_sign_burger_glow": {"size": (64, 16), "tile_m": 4.4, "color": "#FF6A3A", "kind": "cutout", "map": "once"},
    "int_ru_menu_screen":  {"size": (32, 16), "tile_m": 0.9, "color": "#1E4E9E", "map": "once"},
    "int_ru_neon_swirl_tall": {"size": (32, 64), "tile_m": 2.4, "color": "#E01E3A", "kind": "cutout", "map": "once"},
    "int_ru_maple_panel":  {"size": (32, 64), "tile_m": 1.2, "color": "#D2A26A"},
    "int_ru_leather_orange": {"size": (32, 32), "tile_m": 0.8, "color": "#D0642A"},
    "int_ru_troffer":      {"size": (16, 32), "tile_m": 1.2, "color": "#F4F6F8", "map": "once"},
    "int_ru_pastry":       {"size": (32, 16), "tile_m": 1.0, "color": "#C89A5A", "map": "once"},
    "int_ru_vletters_wok": {"size": (64, 16), "tile_m": 3.2, "color": "#C8281E", "kind": "cutout", "map": "once"},
    "int_ru_vletters_halal": {"size": (64, 16), "tile_m": 3.2, "color": "#F0A030", "kind": "cutout", "map": "once"},
    "int_ru_vletters_mac": {"size": (64, 16), "tile_m": 3.2, "color": "#1E3C9E", "kind": "cutout", "map": "once"},
    "int_ru_vletters_shakes": {"size": (64, 16), "tile_m": 3.2, "color": "#8A4AB8", "kind": "cutout", "map": "once"},
    "int_ru_vletters_tacos": {"size": (64, 16), "tile_m": 3.2, "color": "#1E8A86", "kind": "cutout", "map": "once"},
    "int_ru_vletters_coffee": {"size": (64, 16), "tile_m": 3.2, "color": "#1E6A46", "kind": "cutout", "map": "once"},
    "int_ru_sign_esports_b": {"size": (64, 32), "tile_m": 4.0, "color": "#E8F0FF", "kind": "cutout", "map": "once"},
    "int_ru_wall_charcoal": {"size": (32, 32), "tile_m": 2.0, "color": "#3A3C42"},
    "int_ru_aed":          {"size": (32, 32), "tile_m": 0.6, "color": "#E8E8E4", "map": "once"},
    # fidelity-4 (round 2): hotel suite, Arredondo Cafe, Rion Ballroom
    "int_ru_leather_tan":  {"size": (32, 32), "tile_m": 0.8, "color": "#D8A25A"},
    "int_ru_seat_tan":     {"size": (32, 32), "tile_m": 0.6, "color": "#C07238"},
    "int_ru_mahogany":     {"size": (32, 32), "tile_m": 0.8, "color": "#6A2C1E"},
    "int_ru_drape_gold":   {"size": (32, 32), "tile_m": 1.0, "color": "#B8925E"},
    "int_ru_valance_navy": {"size": (32, 32), "tile_m": 0.6, "color": "#26305C"},
    "int_ru_print_suite":  {"size": (64, 32), "tile_m": 2.0, "color": "#5A9AB0", "map": "once"},
    "int_ru_door_meeting": {"size": (32, 64), "tile_m": 2.4, "color": "#5E3C24", "map": "once"},
    # fix round 2 (design pass): clear vestibule glass, corridor plaques / boards, the Bookstore link sign
    # fix round 4 (design pass, improvement 5): the fixed vestibule panes have collision but read as nothing: alpha
    # 0.14 -> 0.22 and two soft 2-texel diagonal sheen streaks per 3 m tile (tx_glass_sheen)
    "int_ru_glass_clear":  {"size": (32, 32), "tile_m": 3.0, "color": "#DCE6EA", "kind": "water", "alpha": 0.22},
    # fix round 5 (design pass, improvement 3): the north entrance's door leaves + inner vestibule bank stack two
    # glass layers in front of the 10 m follow camera on arrival (Mario a red smudge in a white veil): a faint glass,
    # alpha 0.08 and no sheen, for those (two layers ~15% white); the fixed panes with collision keep the sheen glass
    "int_ru_glass_faint":  {"size": (32, 32), "tile_m": 3.0, "color": "#E4ECEF", "kind": "water", "alpha": 0.08},
    # fix round 5 (design pass, improvement 4): the ACC's student artwork band + the pottery wheels' clay
    "int_ru_student_art":  {"size": (64, 32), "tile_m": 1.0, "color": "#C8A070", "map": "once"},
    "int_ru_clay":         {"size": (32, 32), "tile_m": 0.5, "color": "#B0603A"},
    "int_ru_room_plaque":  {"size": (16, 32), "tile_m": 0.3, "color": "#1E2A5C", "map": "once"},
    "int_ru_bulletin":     {"size": (32, 32), "tile_m": 1.2, "color": "#B88A58", "map": "once"},
    "int_ru_sign_bookstore": {"size": (64, 32), "tile_m": 3.0, "color": "#1E2A5C", "map": "once"},
    # fix round 4 (fidelity-3 blocking): G315's pale blue-grey accent, the billiards hall's warm charcoal panel, the
    # Esports storefront's dark smoked glass
    "int_ru_wall_paleblue": {"size": (32, 32), "tile_m": 2.0, "color": "#BCC4D0"},
    "int_ru_wall_billiards": {"size": (32, 32), "tile_m": 2.0, "color": "#2E3036"},
    # fix round 5 (fidelity-3; ru_es_oelrich_8951): alpha 0.62 -> 0.52, the blue-lit arena glows through from the Game Room
    "int_ru_glass_smoke":  {"size": (32, 32), "tile_m": 3.0, "color": "#1C2234", "kind": "water", "alpha": 0.52},
    # fix round 4 (fidelity-1 blocking): the atrium's east bulkhead, silver grid-seamed metal panels
    "int_ru_metal_panel":  {"size": (32, 32), "tile_m": 1.5, "color": "#B4B8BE"},
    # fix round 4 (fidelity-1 improvements): the UF letters' bright orange (ru_atrium_uf_letters_wall (241,119,17)),
    # the gator tracks' bright stainless strip (ru_floor_gator_tracks), the lounge's tan wood tables / chair arms and
    # bright orange club chairs (ru_atrium_enr_lounge)
    "int_ru_orange_uf":    {"size": (32, 32), "tile_m": 1.0, "color": "#FA8A1E"},
    "int_ru_steel_bright": {"size": (32, 32), "tile_m": 1.0, "color": "#E6EAEE"},
    "int_ru_wood_tan":     {"size": (32, 32), "tile_m": 1.2, "color": "#C9A06A"},
    "int_ru_fabric_orange": {"size": (32, 32), "tile_m": 0.6, "color": "#EE6A22"},
    "int_ru_fabric_mustard": {"size": (32, 32), "tile_m": 0.6, "color": "#D8A030"},   # ACC chairs (ru_acc_studio)
    # fix round 5 (fidelity-1, ru_atrium_enr_lounge right third): the Orange & Brew glazed bays on the lounge's south
    # side (a warm-lit cafe interior seen through glass, one 1.25 x 2.0 m bay per texture) and its fascia sign
    "int_ru_cafe_bay":     {"size": (32, 64), "tile_m": 2.0, "color": "#D8B07A", "map": "once"},
    "int_ru_sign_ob":      {"size": (64, 32), "tile_m": 2.4, "color": "#F2F0EC", "map": "once"},
    # ... the glass office fronts on the atrium void's east end at Levels 2 / 3 (ru_atrium_enr_vertical)
    "int_ru_office_bay":   {"size": (32, 64), "tile_m": 2.6, "color": "#C8D2D8", "map": "once"},
    # fix round 5 (fidelity-3): the billiards tables' near-black espresso mahogany (ru_gr_billiards_room: aprons and
    # legs (36,15,13)..(13,6,4); int_ru_cherry read bright orange), the billiards-wall graphic GAME ROOM / THE
    # UNIVERSITY OF FLORIDA (ru_gr_wall_graphic_billiards; it reused the desk's REITZ UNION GAME ROOM) and G325's
    # royal bay lit by a row of wall-washers (ru_os_g325)
    "int_ru_espresso":     {"size": (32, 32), "tile_m": 1.2, "color": "#3A1E16"},
    "int_ru_sign_gameroom_uf": {"size": (64, 32), "tile_m": 3.0, "color": "#1E2C6A", "map": "once"},
    "int_ru_wall_royal_wash": {"size": (64, 32), "tile_m": 6.0, "color": "#1E3CA0", "map": "once"},
    # fix round 5 (fidelity-4; ru_os_2355_2365): four colourful landscape canvases (no mat, no frame line)
    "int_ru_canvas":       {"size": (64, 32), "tile_m": 1.2, "color": "#C89A4A", "map": "once"},
    # fix round 5 (fidelity-4; meeting-room chair rows): black stacking-chair seats, 4 per repeat, 6 cm gaps
    "int_ru_seatrow_black": {"size": (64, 32), "tile_m": 2.0, "color": "#1E1E22", "map": "once"},
    # iteration 7 (fidelity-1 improvement 3; ru_ribbon_cutting_doors): the OUTER north door leaves get a light
    # cyan-grey tint (alpha 0.13; the faint 0.08 glass read as empty white frames); the inner vestibule bank stays faint
    "int_ru_glass_door":   {"size": (32, 32), "tile_m": 3.0, "color": "#C6DCE4", "kind": "water", "alpha": 0.13},
    # iteration 7 (fidelity-1 improvement 5; ru_atrium_hdr_flickr, ru_atrium_construction_2015): the east bulkhead
    # drum is bright polished silver with a vertical highlight, not the matte grey int_ru_metal_panel (kept for the
    # drum's soffit and the wall behind it)
    "int_ru_drum_panel":   {"size": (32, 32), "tile_m": 1.5, "color": "#CDD0D6"},
    # iteration 9 (fidelity-4 improvement 5; ru_hotel_room, ru_hotel_suite): the guest rooms' warm light grey-taupe
    # patterned carpet (photo ~178, 160, 153); the navy int_ru_carpet_hotel stays on the L5 / L6 corridors
    "int_ru_carpet_hotelroom": {"size": (32, 32), "tile_m": 1.2, "color": "#A89A92"},
    # iteration 9 (fidelity-4 improvement 9; ru_the_gallery / ru_os_gallery): the Gallery's large discrete pieces, one
    # per ~3 x 1.6 m board (mapped once): (a) the large deep-blue canvas, (b) a tall multicolour piece between a grid of
    # small photos and a row of small landscapes
    "int_ru_art_gal_a":    {"size": (64, 32), "tile_m": 3.0, "color": "#5A6AA8", "map": "once"},
    "int_ru_art_gal_b":    {"size": (64, 32), "tile_m": 3.0, "color": "#B8A48C", "map": "once"},
    # iteration 9 (fidelity-4 improvement 8; ru_os_3305 / ru_os_3310: ~174, 159, 139): a warmer cream than
    # int_ru_wall_cream (which bakes near-white under the meeting rooms' cool linear lights)
    "int_ru_wall_warm":    {"size": (32, 32), "tile_m": 2.0, "color": "#EAD8BC"},
    # ==== user-photo pass (the user's own photos: atrium core)
    "int_ru_tower_glass":  {"size": (32, 64), "tile_m": 3.0, "color": "#14161B", "map": "once"},
    "int_ru_tower_car":    {"size": (32, 64), "tile_m": 3.0, "color": "#E8CC9C", "map": "once"},
    "int_ru_sign_gators":  {"size": (64, 32), "tile_m": 4.2, "color": "#F47A1E", "kind": "cutout", "map": "once"},
    "int_ru_band_blue":    {"size": (64, 16), "tile_m": 12.0, "color": "#E8E8E8", "map": "once"},
    "int_ru_word_blue":    {"size": (64, 16), "tile_m": 7.5, "color": "#2A5CE0", "kind": "cutout", "map": "once"},
    "int_ru_band_orange":  {"size": (64, 16), "tile_m": 13.5, "color": "#E8E2DA", "map": "once"},
    "int_ru_word_orange":  {"size": (64, 16), "tile_m": 10.5, "color": "#F05A1E", "kind": "cutout", "map": "once"},
    "int_ru_bronze_black": {"size": (32, 32), "tile_m": 0.8, "color": "#24262A"},
    "int_ru_carpet_tri":   {"size": (64, 32), "tile_m": 3.0, "color": "#2442A4"},
    "int_ru_banner_welcome2": {"size": (64, 16), "tile_m": 5.0, "color": "#1E3CA0", "map": "once"},
    "int_ru_banner_welcome3": {"size": (64, 16), "tile_m": 5.0, "color": "#1E3CA0", "map": "once"},
    "int_ru_word_senate":  {"size": (64, 8), "tile_m": 3.0, "color": "#8A8D92", "kind": "cutout", "map": "once"},
    "int_ru_picket2":      {"size": (32, 32), "tile_m": 1.1, "color": "#9EA2A6", "kind": "cutout"},
    "int_ru_leather_char": {"size": (32, 32), "tile_m": 0.8, "color": "#2E3034"},
    "int_ru_gator_claw":   {"size": (32, 32), "tile_m": 0.45, "color": "#1E2A5C", "kind": "cutout", "map": "once"},
    "int_ru_gator_skin_grey": {"size": (32, 32), "tile_m": 1.0, "color": "#D2D3D4"},
    "int_ru_word_cabo":    {"size": (64, 16), "tile_m": 3.2, "color": "#F57A1E", "kind": "cutout", "map": "once"},
    "int_ru_word_mexgrill": {"size": (64, 8), "tile_m": 2.4, "color": "#FFFFFF", "kind": "cutout", "map": "once"},
    "int_ru_snake_plant":  {"size": (16, 32), "tile_m": 0.9, "color": "#3C6E34", "kind": "cutout", "map": "once"},
    # ==== user-photo pass (the user's own photos: the L1 food court, user_18-20, B01-B03)
    "int_ru_vletters_sbux": {"size": (64, 16), "tile_m": 3.0, "color": "#F0EFEA", "kind": "cutout", "map": "once"},
    "int_ru_badge_green":  {"size": (32, 32), "tile_m": 0.7, "color": "#1E6A44", "kind": "cutout", "map": "once"},
    "int_ru_cafe_shelves": {"size": (64, 32), "tile_m": 2.0, "color": "#4A2E1E"},
    "int_ru_slat_walnut":  {"size": (32, 32), "tile_m": 0.5, "color": "#5A3A24"},
    "int_ru_mural_coffea": {"size": (64, 32), "tile_m": 3.3, "color": "#1E2021", "map": "once"},
    "int_ru_brick_rustic": {"size": (32, 32), "tile_m": 1.0, "color": "#B8683C"},
    "int_ru_vletters_babas": {"size": (128, 16), "tile_m": 3.8, "color": "#F2EEE4", "kind": "cutout", "map": "once"},
    "int_ru_badge_black":  {"size": (32, 32), "tile_m": 1.0, "color": "#141414", "kind": "cutout", "map": "once"},
    "int_ru_badge_gold":   {"size": (32, 32), "tile_m": 0.9, "color": "#D4A23A", "kind": "cutout", "map": "once"},
    "int_ru_vletters_halal2": {"size": (128, 16), "tile_m": 3.0, "color": "#6A3E1A", "kind": "cutout", "map": "once"},
    "int_ru_tile_lattice": {"size": (32, 32), "tile_m": 0.5, "color": "#F2F2EE"},
    "int_ru_vletters_panda": {"size": (64, 16), "tile_m": 2.0, "color": "#FFFFFF", "kind": "cutout", "map": "once"},
    "int_ru_badge_red":    {"size": (32, 32), "tile_m": 0.7, "color": "#C8202A", "kind": "cutout", "map": "once"},
    "int_ru_vletters_smart": {"size": (128, 16), "tile_m": 2.6, "color": "#C8202A", "kind": "cutout", "map": "once"},
    "int_ru_fc_queue":     {"size": (32, 32), "tile_m": 1.2, "color": "#4E4945"},
    "int_ru_vinyl_grey":   {"size": (32, 32), "tile_m": 1.2, "color": "#A8A59F"},
    "int_ru_troffer_sq":   {"size": (16, 16), "tile_m": 0.6, "color": "#F4F6F8", "map": "once"},
    "int_ru_vent_sq":      {"size": (16, 16), "tile_m": 0.6, "color": "#9A9EA4", "map": "once"},
    "int_ru_sign_bk_gators": {"size": (64, 16), "tile_m": 6.1, "color": "#2F6BFF", "kind": "cutout", "map": "once"},
    "int_ru_sign_bk_store": {"size": (64, 16), "tile_m": 5.7, "color": "#2F6BFF", "kind": "cutout", "map": "once"},
    "int_ru_badge_gator":  {"size": (32, 32), "tile_m": 1.4, "color": "#1E3CA0", "kind": "cutout", "map": "once"},
    "int_ru_grille":       {"size": (32, 32), "tile_m": 0.6, "color": "#AEB2B8", "kind": "cutout"},
    "int_ru_jersey":       {"size": (32, 16), "tile_m": 1.0, "color": "#F4F4F4", "map": "once"},
    "int_ru_laminate_mauve": {"size": (32, 32), "tile_m": 0.9, "color": "#B98A96"},
    "int_ru_order_here":   {"size": (64, 8), "tile_m": 0.4, "color": "#FFFFFF", "kind": "cutout", "map": "once"},
    "int_ru_paint_cranberry": {"size": (32, 32), "tile_m": 2.0, "color": "#8A1C20"},
    # ==== user-photo pass, Ground floor (user_01, user_03, user_04, B12-B20)
    "int_ru_tile_ceiling_dark": {"size": (32, 32), "tile_m": 1.2, "color": "#4E5468"},
    "int_ru_scale_led":    {"size": (64, 32), "tile_m": 2.0, "color": "#2B2BD8"},
    "int_ru_inlay_reitz":  {"size": (64, 32), "tile_m": 2.45, "color": "#E6E1D4", "map": "once"},
    "int_ru_granite_black": {"size": (32, 32), "tile_m": 0.8, "color": "#1C1C20"},
    "int_ru_brass":        {"size": (32, 32), "tile_m": 1.0, "color": "#C8A04A"},
    "int_ru_wayfind_G_w_a": {"size": (64, 32), "tile_m": 2.0, "color": "#F2F1EC", "map": "once"},
    "int_ru_wayfind_G_w_b": {"size": (64, 32), "tile_m": 2.0, "color": "#F2F1EC", "map": "once"},
    "int_ru_wayfind_G_w_c": {"size": (64, 32), "tile_m": 2.0, "color": "#F2F1EC", "map": "once"},
    "int_ru_arrow_navy":   {"size": (16, 16), "tile_m": 0.4, "color": "#1E3C9E", "map": "once"},
    "int_ru_terrazzo_grey": {"size": (32, 32), "tile_m": 1.5, "color": "#A5A39C"},
    "int_ru_terrazzo_orange": {"size": (32, 32), "tile_m": 1.5, "color": "#D9782F"},
    "int_ru_sign_gr_transom": {"size": (64, 16), "tile_m": 2.4, "color": "#FFFFFF", "kind": "cutout", "map": "once"},
    "int_ru_barber_pole":  {"size": (16, 32), "tile_m": 0.6, "color": "#F4F4F4"},
    "int_ru_sign_barber":  {"size": (64, 32), "tile_m": 2.8, "color": "#F6F6F4", "map": "once"},
    "int_ru_photo_bw":     {"size": (64, 32), "tile_m": 1.1, "color": "#B4B4B0"},
    "int_ru_dir_G":        {"size": (32, 64), "tile_m": 1.6, "color": "#1E3C9E", "map": "once"},
    "int_ru_sign_arena":   {"size": (64, 16), "tile_m": 2.6, "color": "#FF8A2A", "kind": "cutout", "map": "once"},
    "int_ru_subway_green": {"size": (32, 32), "tile_m": 2.0, "color": "#0F7A35"},
    "int_ru_sign_subway":  {"size": (64, 16), "tile_m": 2.3, "color": "#FFC20E", "kind": "cutout", "map": "once"},
    "int_ru_arcade_gamepod": {"size": (32, 64), "tile_m": 1.85, "color": "#1A1A1E", "map": "once"},
    "int_ru_sign_nosh":    {"size": (64, 16), "tile_m": 2.2, "color": "#FFFFFF", "kind": "cutout", "map": "once"},
    "int_ru_sign_market":  {"size": (32, 32), "tile_m": 0.7, "color": "#1E2A5C", "kind": "cutout", "map": "once"},
    # ==== user-photo pass, L1-L3 corridors + Rion (user_06-user_17, C03, C04, C07, C08, C11-C16)
    "int_ru_ccc_screen":   {"size": (64, 32), "tile_m": 3.4, "color": "#1F4DB0", "map": "once"},
    "int_ru_marble":       {"size": (32, 32), "tile_m": 1.2, "color": "#E9E9EB"},
    "int_ru_timeline":     {"size": (64, 32), "tile_m": 2.4, "color": "#E3672B"},
    "int_ru_timeline_head": {"size": (128, 16), "tile_m": 4.8, "color": "#E3672B", "map": "once"},
    "int_ru_timeline_head2": {"size": (128, 16), "tile_m": 4.8, "color": "#E3672B", "map": "once"},
    "int_ru_sign_rion":    {"size": (128, 16), "tile_m": 4.6, "color": "#EDEBE6", "map": "once"},
    "int_ru_sign_rion_east": {"size": (128, 16), "tile_m": 4.6, "color": "#EDEBE6", "map": "once"},
    "int_ru_hang_pass_a":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_hang_pass_b":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_hang_pass_c":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_hang_blue_a":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_hang_blue_b":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_hang_blue_c":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_hang_blue_d":  {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_oils":         {"size": (64, 32), "tile_m": 1.8, "color": "#5E4626", "map": "once"},
    "int_ru_sign_gatorwell": {"size": (64, 16), "tile_m": 2.2, "color": "#E8742A", "kind": "cutout", "map": "once"},
    "int_ru_slate_floor":  {"size": (32, 32), "tile_m": 1.2, "color": "#555A62"},
    "int_ru_partition":    {"size": (32, 32), "tile_m": 1.2, "color": "#8C9095"},
    "int_ru_door_meeting_honey": {"size": (32, 64), "tile_m": 2.4, "color": "#B8823E", "map": "once"},
    "int_ru_maple_pale":   {"size": (64, 32), "tile_m": 1.6, "color": "#D8BC90"},
    "int_ru_word_wall_a":  {"size": (64, 32), "tile_m": 2.9, "color": "#5E5048", "map": "once"},
    "int_ru_word_wall_b":  {"size": (64, 32), "tile_m": 2.9, "color": "#5E5048", "map": "once"},
    "int_ru_hang_meet":    {"size": (64, 32), "tile_m": 2.0, "color": "#E2E4E6", "map": "once"},
    "int_ru_frit":         {"size": (64, 8), "tile_m": 1.2, "color": "#F4F6F8", "kind": "cutout"},
    "int_ru_rion_case":    {"size": (32, 64), "tile_m": 2.0, "color": "#1E2A44", "map": "once"},
    # design + leftovers pass (user_06, C04, B05): the dark grey terrazzo inlay band of the L1-L3 corridors
    "int_ru_terrazzo_dark": {"size": (32, 32), "tile_m": 1.5, "color": "#5E6062"},
}
for _m in RU_MATERIALS.values():
    _m["tex"] = None
for _n, _m in RU_MATERIALS.items():
    _m["tex"] = _n + ".png"
    _m.setdefault("kind", "opaque")
    _m.setdefault("map", "tile")
    _m.setdefault("lit", "vertex")


def register():
    """Merge the int_ru_* materials into stage_palette.INTERIOR_MATERIALS (in place: interior_kit and
    stage_materials read the same dict). Idempotent; only Reitz builds import this module."""
    for name, m in RU_MATERIALS.items():
        if name not in stage_palette.INTERIOR_MATERIALS:
            stage_palette.INTERIOR_MATERIALS[name] = {k: v for k, v in m.items() if k != "size"}
    return list(RU_MATERIALS)


register()

import interior_kit as K  # noqa: E402  (after register(): the kit's known_material() sees int_ru_*)


# ================================================================== textures (Pillow, tools venv)
def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def q5(c):
    v = max(0, min(255, int(round(c))))
    v5 = (v * 31 + 127) // 255
    return (v5 << 3) | (v5 >> 2)


def shade(c, k):
    return tuple(max(0, min(255, int(round(x * k)))) for x in c)


def mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Tex:
    """Pixel buffer (rows top to bottom) -> RGBA16-quantised PIL image (make_textures.Tex, copied so this
    module does not depend on that shared script's state)."""

    def __init__(self, w, h, color, seed, alpha=255):
        self.w, self.h = w, h
        self.r = random.Random(seed)
        self.px = [[tuple(color[:3]) + (alpha,) for _ in range(w)] for _ in range(h)]

    def set(self, x, y, c, a=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = tuple(int(v) for v in c[:3]) + (a,)

    def get(self, x, y):
        return self.px[y % self.h][x % self.w]

    def rect(self, x0, y0, x1, y1, c, a=255):
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            for x in range(max(0, x0), min(self.w - 1, x1) + 1):
                self.set(x, y, c, a)

    def noise(self, amp, mono=True):
        for y in range(self.h):
            for x in range(self.w):
                r, g, b, a = self.px[y][x]
                if a < 128:
                    continue
                if mono:
                    d = self.r.uniform(-amp, amp)
                    self.px[y][x] = (r + d, g + d, b + d, a)
                else:
                    self.px[y][x] = (r + self.r.uniform(-amp, amp), g + self.r.uniform(-amp, amp),
                                     b + self.r.uniform(-amp, amp), a)

    def speckle(self, n, colors):
        for _ in range(n):
            self.set(self.r.randrange(self.w), self.r.randrange(self.h), self.r.choice(colors))

    def frame(self, c, x0=0, y0=0, x1=None, y1=None):
        x1 = self.w - 1 if x1 is None else x1
        y1 = self.h - 1 if y1 is None else y1
        for x in range(x0, x1 + 1):
            self.set(x, y0, c)
            self.set(x, y1, c)
        for y in range(y0, y1 + 1):
            self.set(x0, y, c)
            self.set(x1, y, c)

    def line(self, x0, y0, x1, y1, c, a=255):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / max(1, n)
            self.set(int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), c, a)

    def disc(self, cx, cy, r, c, a=255):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.set(x, y, c, a)

    def image(self):
        from PIL import Image
        im = Image.new("RGBA", (self.w, self.h))
        im.putdata([tuple(q5(c) for c in p[:3]) + (255 if p[3] >= 128 else 0,) for row in self.px for p in row])
        return im


FONT5 = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ">": ["#....", ".#...", "..#..", "...#.", "..#..", ".#...", "#...."],
    "<": ["....#", "...#.", "..#..", ".#...", "..#..", "...#.", "....#"],
    "^": ["..#..", ".###.", "#.#.#", "..#..", "..#..", "..#..", "..#.."],
    "v": ["..#..", "..#..", "..#..", "..#..", "#.#.#", ".###.", "..#.."],
    "'": ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."],
}
# 3 x 5 font for small labels (room plates, menu lines)
FONT3 = {
    "A": ["###", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"], "P": ["###", "#.#", "###", "#..", "#.."],
    "R": ["###", "#.#", "##.", "#.#", "#.#"], "S": ["###", "#..", "###", "..#", "###"],
    "T": ["###", ".#.", ".#.", ".#.", ".#."], "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."], "W": ["#.#", "#.#", "###", "###", "#.#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"], "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    # fix round 2 (blocking): Z and Q were missing, so "REITZ UNION" printed as "REIT UNION"
    "Z": ["###", "..#", ".#.", "#..", "###"], "Q": ["###", "#.#", "#.#", "##.", ".##"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", "..#", "..#", "..#"],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
    "-": ["...", "...", "###", "...", "..."], "$": [".#.", "###", "##.", ".##", "###"],
    ">": ["#..", ".#.", "..#", ".#.", "#.."], "<": ["..#", ".#.", "#..", ".#.", "..#"],
}


def font_text(t, text, x, y, color, scale=1, spacing=1, font=FONT5, a=255):
    gw = len(next(iter(font.values()))[0])
    for ch in text:
        g = font.get(ch)
        if g is not None:
            for gy, row in enumerate(g):
                for gx, c in enumerate(row):
                    if c == "#":
                        t.rect(x + gx * scale, y + gy * scale, x + gx * scale + scale - 1, y + gy * scale + scale - 1,
                               color, a)
        x += (gw + spacing) * scale


def font_width(text, scale=1, spacing=1, font=FONT5):
    gw = len(next(iter(font.values()))[0])
    n = len(text)
    return n * gw * scale + max(0, n - 1) * spacing * scale if n else 0


def font_center(t, text, y, color, scale=1, spacing=1, x0=0, x1=None, font=FONT5, a=255):
    x1 = t.w - 1 if x1 is None else x1
    w = font_width(text, scale, spacing, font)
    font_text(t, text, x0 + (x1 - x0 + 1 - w) // 2, y, color, scale, spacing, font, a)


# ---------------------------------------------------------------- recipes
def _flat(hx, seed, amp=4, w=32, h=32):
    t = Tex(w, h, hexc(hx), seed)
    t.noise(amp)
    return t


def tx_glass_sheen(seed):
    """fix round 4 (design pass): clear vestibule glass with two soft diagonal sheen streaks (2 texels each, ~19 cm at
    3 m / 32 px; seamless: the diagonal wraps on the 32 x 32 tile)."""
    t = _flat("#DCE6EA", seed, 1)
    for y in range(32):
        for x in range(32):
            d = (x + y) % 32
            if d in (5, 6):
                t.set(x, y, hexc("#FFFFFF"))
            elif d in (11, 12):
                t.set(x, y, hexc("#F0F5F8"))
    return t


def tx_student_art(seed):
    """fix round 5 (design pass, improvement 4; ru_acc_studio shows student work everywhere): four student paintings
    pinned on kraft paper, one per 16 x 32 cell (a panel maps one cell over ~0.8 x 1.1 m): a sun over hills, colour
    blocks, a target swirl and a gator on orange. Every edge >= 2 texels (no 1-texel high-contrast lines)."""
    t = Tex(64, 32, hexc("#C8A070"), seed)
    t.noise(3)
    # cell 0: blue sky, orange sun, green hills
    t.rect(2, 2, 13, 29, hexc("#5AA8E0")); t.rect(2, 18, 13, 29, hexc("#4AA048")); t.rect(6, 15, 13, 21, hexc("#3A8A3A"))
    t.disc(9, 8, 3, hexc("#F29A2A"))
    # cell 1: bright colour blocks (soft dark-blue 2-texel dividers)
    t.rect(18, 2, 29, 29, hexc("#22306A"))
    t.rect(18, 2, 25, 13, hexc("#E83A3A")); t.rect(28, 2, 29, 13, hexc("#F4D03A")); t.rect(18, 16, 21, 29, hexc("#F4D03A"))
    t.rect(24, 16, 29, 23, hexc("#2E7AC8")); t.rect(24, 26, 29, 29, hexc("#F2F2EE"))
    # cell 2: a purple / teal target swirl
    t.rect(34, 2, 45, 29, hexc("#F2EEDC"))
    for r_, c_ in ((6, "#7A3AB0"), (4, "#2AA8A0"), (2, "#F27A3A")):
        t.disc(39, 15, r_, hexc(c_))
    # cell 3: a green gator on orange
    t.rect(50, 2, 61, 29, hexc("#F2862A"))
    t.rect(52, 12, 59, 19, hexc("#2E7A3A")); t.rect(52, 8, 55, 12, hexc("#2E7A3A")); t.rect(54, 19, 57, 27, hexc("#2E7A3A"))
    t.rect(52, 9, 53, 10, hexc("#F2F2EE"))
    return t


def tx_metal_panel(seed):
    """fix round 4: silver metal panels with soft 2-texel seams (low contrast: no 1-texel shimmer lines)."""
    t = _flat("#B4B8BE", seed, 3)
    t.rect(0, 0, 31, 1, hexc("#A2A6AC"))
    t.rect(0, 0, 1, 31, hexc("#A2A6AC"))
    t.rect(2, 2, 31, 2, hexc("#BEC2C6"))
    return t


def tx_drum_panel(seed):
    """iteration 7 (fidelity-1 improvement 5): the east bulkhead drum's polished silver panels, (205,208,214), each
    panel with a soft vertical highlight (a 5-step column gradient, steps of 8 so RGBA16 keeps them) and soft 2-texel
    seams of low contrast (no 1-texel lines: no mipmaps)."""
    t = _flat("#CDD0D6", seed, 2)
    ramp = {9: 8, 10: 16, 11: 24, 12: 24, 13: 16, 14: 8, 22: -8, 23: -8}
    for x, dv in ramp.items():
        for y in range(2, 32):
            c = (min(255, 205 + dv), min(255, 208 + dv), min(255, 214 + dv))
            t.set(x, y, c)
    t.rect(0, 0, 31, 1, hexc("#BABEC5"))
    t.rect(0, 0, 1, 31, hexc("#BABEC5"))
    return t


def tx_terrazzo(seed):
    """White terrazzo with grey / black / warm chips (ru_floor_gator_tracks, ru_atrium_uf_letters_wall): poured
    seamless (no joint lines: the atrium and Level 1 floors read as one white sheet, ru_atrium_enr_lounge)."""
    t = Tex(32, 32, hexc("#F1EEE8"), seed)
    t.noise(2)
    t.speckle(55, [hexc("#D6D1C8"), hexc("#DDD8CE"), hexc("#CCC6BC"), hexc("#E0D7C6")])
    t.speckle(9, [hexc("#A29E96"), hexc("#AEA89C")])
    return t


def tx_carpet_atrium(seed):
    """Atrium lounge carpet (ru_atrium_enr_lounge): a large dark-navy field in slightly varied navy blocks with
    light-blue squiggle lines (the photo's carpet is far darker than UF royal blue)."""
    t = Tex(64, 32, hexc("#1C2654"), seed)
    for by in range(2):
        for bx in range(4):
            c = [hexc("#1C2654"), hexc("#161E44"), hexc("#24336A"), hexc("#1A2450")][(bx * 3 + by * 2) % 4]
            t.rect(bx * 16, by * 16, bx * 16 + 15, by * 16 + 15, c)
    t.noise(4)
    for k in range(5):
        ph = t.r.uniform(0, 6.28)
        y0 = 3 + k * 6
        for x in range(64):
            y = int(round(y0 + 2.2 * math.sin(x / 5.0 + ph)))
            for dy_ in (0, 1):                      # design r2: 2-texel lines (no mipmaps: 1-px lines crawl)
                t.set(x, (y + dy_) % 32, hexc("#6E96CC") if k % 2 else hexc("#4F74B4"))
    t.speckle(30, [hexc("#3A5294"), hexc("#10183A")])
    return t


def tx_gator_track(seed):
    """One navy gator footprint on clear (ru_floor_gator_tracks): palm + four toes."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    navy = hexc("#1E2A5C")
    # design r2: a bigger print in the same 32 px (the palm + toes now fill ~85% of the tile, so a 0.4 m quad
    # reads as a footprint from the follow camera, not a speck)
    t.disc(16, 21, 8.0, navy)
    for dx, dy in ((-11, -5), (-5, -14), (5, -14), (11, -5)):
        for ox in (-1, 0, 1):
            t.line(16 + ox, 19, 16 + ox + dx, 19 + dy, navy)
        t.disc(16 + dx, 19 + dy, 2.8, navy)
    return t


def tx_lane(seed):
    """Maple lane boards (ru_gr_lane_screens): 39 boards across a 1.06 m lane -> thin light / honey strips."""
    t = Tex(32, 32, hexc("#DCB47C"), seed)
    for x in range(32):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        for y in range(32):
            t.set(x, y, shade(hexc("#DCB47C"), k * (0.93 if x % 4 == 3 else 1.0)))
    t.noise(3)
    for _ in range(6):
        y = t.r.randrange(32)
        x = t.r.randrange(32)
        t.set(x, y, hexc("#E8C894"))
    return t


def tx_lane_arrows(seed):
    """Lane segment with the targeting arrows (32 x 64: the lane width x ~2.1 m), mapped once."""
    t = Tex(32, 64, hexc("#D8B07A"), seed)
    for x in range(32):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        for y in range(64):
            t.set(x, y, shade(hexc("#D8B07A"), k * (0.93 if x % 4 == 3 else 1.0)))
    dark = hexc("#4A2E1E")
    for i, xc in enumerate((4, 9, 13, 16, 19, 23, 28)):
        yc = 30 + abs(i - 3) * 5
        for d in range(4):
            t.set(xc - d // 2, yc + d, dark)
            t.set(xc + d // 2, yc + d, dark)
    for xc in (6, 11, 16, 21, 26):
        t.rect(xc, 8, xc, 9, dark)
    return t


def tx_plank(seed):
    """Grey wood-look plank flooring (ru_gr_booth_detail, ru_es_oelrich_9188): 20 cm x 1.2 m planks."""
    base = hexc("#8E8C8A")
    t = Tex(64, 32, base, seed)
    for row in range(8):
        off = (row * 23) % 64
        k = 1.0 + t.r.uniform(-0.08, 0.08)
        for y in range(row * 4, row * 4 + 4):
            for x in range(64):
                xs = (x + off) % 64
                c = shade(base, k * (0.86 if (y % 4 == 3 or xs % 32 == 0) else 1.0))
                if t.r.random() < 0.06:
                    c = shade(c, 1.08)
                t.set(x, y, c)
    t.noise(3)
    return t


def tx_carpet_billiards(seed):
    """Game Room billiards carpet (ru_gr_billiards_room, ru_es_oelrich_8951). Fidelity-3 (round 2): the photos measure
    a LIGHTER, desaturated grey-blue field (mean ~(80-170, 106-175, 127-191), saturation 0.1-0.4; the old one was
    (38,52,110), 0.65) with the gator-scale look: irregular croc scales (a toroidal Voronoi of 42 cells, ~0.2 m, stretched
    along x) outlined in pale blue-grey, a few in tan, each scale a slightly different tone and lighter at its rim.
    The regular sine / checker grid read as rows of blobs at gameplay distance."""
    t = Tex(64, 32, hexc("#545762"), seed)
    r = t.r
    pts = [(r.uniform(0, 64), r.uniform(0, 32)) for _ in range(42)]
    tone = [r.uniform(0.86, 1.1) for _ in pts]
    base = hexc("#3D4A6A")    # user-photo pass (user_04, B20): a bluer field, orange + black accent scales
    for y in range(32):
        for x in range(64):
            ds = []
            for i, (px, py) in enumerate(pts):
                dx = abs(x + 0.5 - px)
                dx = min(dx, 64 - dx) * 0.62
                dy = abs(y + 0.5 - py)
                dy = min(dy, 32 - dy)
                ds.append((dx * dx + dy * dy, i))
            ds.sort()
            d1, i1 = math.sqrt(ds[0][0]), ds[0][1]
            d2 = math.sqrt(ds[1][0])
            # fix round 4 (design pass, improvement 8): with nearest filtering and no mips the 1-texel bright outlines
            # (21% of the texels) sparkled at 10-20 m: softer outline tones (contrast vs the field roughly halved),
            # no 1-in-6 highlight dither inside them, a softer mid band; the scale pattern and the photo's neutral
            # field (79,78,84) stay
            if d2 - d1 < 0.45:
                c = hexc("#B86A2E") if i1 % 6 == 0 else hexc("#7C92C0")
            elif d2 - d1 < 0.95:
                c = mix(shade(base, tone[i1]), hexc("#6A7CA6"), 0.4)
            elif i1 % 7 == 3:
                c = shade(hexc("#202228"), tone[i1])
            else:
                c = shade(base, tone[i1] * (0.9 + 0.12 * min(1.0, d1 / 4.0)))
            t.set(x, y, c)
    t.noise(3)
    return t


def tx_fc_checker(seed):
    """Food court queue ring (ru_food_court_counter_2023): a regular diamond checkerboard laid at 45 degrees, light
    tan alternating with dark brown and grey-brown tiles (~0.3 m tiles at 1.7 m per repeat)."""
    t = Tex(32, 32, hexc("#C8AE82"), seed)
    light, dark, grey = hexc("#CDB287"), hexc("#664A32"), hexc("#7C746A")
    for y in range(32):
        for x in range(32):
            i, j = (x + y) // 8, (x - y) // 8
            if (i + j) % 2 == 0:
                c = light
            else:
                c = dark if (i - j) % 4 == 1 else grey
            u, v = (x + y) % 8, (x - y) % 8
            if u in (0, 7) or v in (0, 7):
                c = shade(c, 0.93)
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_fc_tile(seed):
    """Food court hall tile (ru_food_court_counter_2023, ru_dining_windows): large-format white / very light grey
    60 cm porcelain squares (2 x 2 per 1.2 m repeat) with a faint grout line."""
    base = hexc("#E2E0DC")
    t = Tex(32, 32, base, seed)
    for ty in range(2):
        for tx in range(2):
            k = 1.0 + t.r.uniform(-0.025, 0.025)
            for y in range(16):
                for x in range(16):
                    c = shade(base, k)
                    if x == 15 or y == 15:
                        c = hexc("#CCCAC4")
                    t.set(tx * 16 + x, ty * 16 + y, c)
    t.noise(2)
    return t


def tx_counter_navy(seed):
    """Burger drive-in counter front + fascia (ru_food_court_sonic_2025): dark navy panels with faint vertical reveals."""
    # fix round 4 (fidelity-2): the photo's saturated royal navy (~0, 40, 82; was 26, 34, 72)
    # fix round 5 (fidelity-2): ~30% lighter (#062A56 rendered ~4, 28, 60 against the photo's lit 30, 54, 88: it read
    # as near-black); the reveals follow
    t = Tex(32, 32, hexc("#0C3A74"), seed)
    t.noise(2)
    for y in range(32):
        t.set(15, y, hexc("#0A3266"))
        t.set(31, y, hexc("#0A3266"))
    return t


def tx_counter_red(seed):
    """Wok counter front: lacquer-red panels over a black base band with thin black reveals."""
    t = Tex(32, 32, hexc("#A82420"), seed)
    t.noise(2)
    for y in range(32):
        t.set(0, y, hexc("#2A1414"))
    t.rect(0, 0, 31, 2, hexc("#1E1F22"))
    t.rect(0, 24, 31, 31, hexc("#1E1F22"))
    return t


def tx_mosaic(seed):
    """Coffee bar backsplash (ru_starbucks_2017): a small-square glass mosaic in orange, olive green, cream and
    caramel, 4-texel squares (~10 cm), colour only (no 1-texel grout lines that would shimmer)."""
    t = Tex(32, 32, hexc("#C89A62"), seed)
    cols = [hexc("#D8742A"), hexc("#E89A3A"), hexc("#7A8A3A"), hexc("#5E7A34"), hexc("#EADBB8"), hexc("#C8A06A"),
            hexc("#B8642A"), hexc("#F0E4C8")]
    for by in range(8):
        for bx in range(8):
            c = t.r.choice(cols)
            t.rect(bx * 4, by * 4, bx * 4 + 3, by * 4 + 3, c)
    t.noise(3, mono=False)
    return t


def tx_chalkboard(seed):
    """Coffee bar menu boards (ru_starbucks_2017): three black chalkboards in thin dark frames, chalk lines."""
    t = Tex(64, 32, hexc("#2C2A26"), seed)
    for p in range(3):
        x0 = 1 + p * 21
        t.rect(x0, 1, x0 + 19, 30, hexc("#1C1E1E"))
        t.rect(x0 + 3, 3, x0 + 16, 4, hexc("#E8E4D8"))
        for r in range(5):
            y = 8 + r * 4
            t.rect(x0 + 2, y, x0 + 3 + (5 + (r * 7 + p * 3) % 7), y, hexc("#C8C4BA"))
            t.rect(x0 + 15, y, x0 + 17, y, hexc("#D8C878"))
        t.disc(x0 + 14, 26, 2, [hexc("#3A8A5A"), hexc("#C86A3A"), hexc("#D8D0B8")][p])
    t.noise(2)
    return t


def tx_neon_swirl(seed):
    """Red / blue neon swirl on a navy wall (ru_food_court_sonic_2025, left of the burger counter)."""
    t = Tex(32, 32, hexc("#1E2652"), seed)
    t.noise(2)
    for i in range(160):
        a = i / 160.0 * math.pi * 3.2
        r = 3.0 + i / 160.0 * 11.0
        x, y = 16 + r * math.cos(a), 16 + r * math.sin(a) * 0.9
        t.disc(int(round(x)), int(round(y)), 1, hexc("#F03A3A") if i < 110 else hexc("#3A8AF0"))
    for i in range(18):
        t.set(4 + i, 28, hexc("#3AA0F8"))
    return t


def tx_menu_blue(seed):
    """Digital menu boards (ru_food_court_sonic_2025): a row of four blue-lit screens with food tiles."""
    t = Tex(64, 32, hexc("#E8ECF0"), seed)
    for p in range(4):
        x0 = 1 + p * 16
        t.rect(x0, 2, x0 + 14, 29, hexc("#16181E"))
        t.rect(x0 + 1, 3, x0 + 13, 28, hexc("#1E5AC0"))
        t.rect(x0 + 2, 5, x0 + 7, 12, [hexc("#D8902A"), hexc("#C8402A"), hexc("#E8C040"), hexc("#B8602A")][p])
        t.rect(x0 + 8, 5, x0 + 12, 12, [hexc("#E8E0C8"), hexc("#D86A2A"), hexc("#F0F0F0"), hexc("#C8A040")][p])
        for r in range(4):
            y = 15 + r * 3
            t.rect(x0 + 2, y, x0 + 9, y, hexc("#E8F0FF"))
            t.rect(x0 + 11, y, x0 + 12, y, hexc("#F0D040"))
    return t


def tx_carpet_meeting(seed):
    """Meeting room carpet tile (ru_os_g310_g320, ru_os_2315_2330): blue / grey patchwork with linear weave."""
    t = Tex(64, 32, hexc("#56688E"), seed)
    cols = [hexc("#4E6290"), hexc("#62708E"), hexc("#465EA0"), hexc("#6A7290"), hexc("#566A98")]
    for by in range(2):
        for bx in range(4):
            c = cols[(bx * 2 + by * 3 + bx * by) % 5]
            for y in range(by * 16, by * 16 + 16):
                for x in range(bx * 16, bx * 16 + 16):
                    k = 1.08 if ((x if (bx + by) % 2 else y) % 3 == 0) else 0.97
                    t.set(x, y, shade(c, k))
    t.noise(4)
    return t


def tx_carpet_ballroom(seed):
    """Grand Ballroom carpet (ru_os_grand_ballroom_1..4): royal blue with many thin, crisp white and light-blue
    flowing lines that meander lengthwise (v, north-south: toward the stage wall) and cross now and then. 64 x 32 at
    3.6 m: ~5.6 cm texels across the lines; each line is drawn by its true distance (about 5 cm wide, anti-aliased
    over one texel), so it reads as a thin line instead of a chain of 1-px dashes (fidelity-4)."""
    # iteration 9 (fidelity-4 improvement 11; photo ~45, 108, 170 vs the baked render ~21, 58, 136): base ~30 %
    # lighter (was #2152B2; speckles #173E92 / #3466C6)
    t = Tex(64, 32, hexc("#3A72C4"), seed)
    t.noise(3)
    # fix round 4 (fidelity-4 pass, improvement 7): the tile shrinks 3.6 -> 2.6 m, so the 2-texel minimum line is
    # ~8 cm instead of ~11 cm (thinner, crisper lines up close; the same share of white over the floor)
    sx, sy = 2.6 / 64, 2.6 / 32                     # metres per texel (u, v)
    white, pale = hexc("#F2F5FB"), hexc("#9CC4EE")
    # (centre px, amplitude px, cycles per repeat, phase, colour, width m)
    # fix round 5 (fidelity-4, improvement 7; ru_os_grand_ballroom_3/4): close to the camera the nine lines per
    # 2.6 m (three of them two-cycle wiggles) read as a dense short-wave net; the photo has long sparse sweeps.
    # Now four gentle one-cycle sweeps per tile (one about every 0.65 m), one of them crossing its neighbours
    # (near-parallel meanders, so they flow side by side instead of crossing into a diamond net)
    specs = [(5.0, 6.5, 1, 0.3, white, 0.045), (21.0, 7.0, 1, 0.9, white, 0.042), (37.0, 6.0, 1, 1.4, pale, 0.040),
             (52.0, 7.0, 1, 0.6, white, 0.045), (29.0, 10.0, 1, 3.6, white, 0.038)]
    for xc, amp, cyc, ph, col, wm in specs:
        wm = max(wm, 2.0 * sx)                      # design r2: every line >= 2 texels wide (no mipmaps)
        for y in range(32):
            yy = y + 0.5
            x_ = xc + amp * math.sin(2 * math.pi * cyc * yy / 32.0 + ph)
            slope = amp * 2 * math.pi * cyc / 32.0 * math.cos(2 * math.pi * cyc * yy / 32.0 + ph)   # px per px
            k = 1.0 / math.sqrt(1.0 + (slope * sx / sy) ** 2)
            for dxp in range(-3, 4):
                px = int(math.floor(x_)) + dxp
                d = abs(px + 0.5 - x_) * sx * k      # metres, perpendicular to the line
                cov = max(0.0, min(1.0, (wm / 2 + sx / 2 - d) / sx))
                if cov <= 0.02:
                    continue
                c = t.get(px % 64, y)
                a = min(1.0, cov * 1.15)
                t.set(px % 64, y, tuple(int(c[i] * (1 - a) + col[i] * a) for i in range(3)))
    t.speckle(16, [hexc("#2C5CAC"), hexc("#4A82D2")])
    return t


def tx_maple(seed):
    """Rion Ballroom maple floor (ru_os_rion_ballroom): 6 cm strips, staggered joints."""
    base = hexc("#D4A46C")
    t = Tex(64, 32, base, seed)
    for row in range(16):
        off = t.r.randrange(64)
        k = 1.0 + t.r.uniform(-0.09, 0.09)
        for y in range(row * 2, row * 2 + 2):
            for x in range(64):
                c = shade(base, k * (0.9 if y % 2 == 1 else 1.0))
                if (x + off) % 40 == 0:
                    c = shade(c, 0.85)
                t.set(x, y, c)
    t.noise(3)
    return t


def tx_maple_light(seed):
    """Pale maple laminate (boardroom table top, ru_os_2345_2350; fix round 4, fidelity-4 pass): a warm cream base
    with soft, wide grain bands along u (low contrast, >= 2 texels: no shimmer)."""
    base = hexc("#DCC8A8")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        k = 1.0 + 0.035 * math.sin(y * 0.55 + 0.8 * math.sin(y * 0.17)) + t.r.uniform(-0.01, 0.01)
        for x in range(32):
            t.set(x, y, shade(base, k + 0.01 * math.sin(x * 0.4 + y)))
    t.noise(2)
    return t


def tx_carpet_pattern(base_hx, line_hx, seed, kind="loop"):
    t = Tex(32, 32, hexc(base_hx), seed)
    t.noise(5)
    if kind == "loop":
        for cy in (8, 24):
            for cx in (8, 24):
                for a in range(24):
                    ang = a * 2 * math.pi / 24
                    t.set(int(cx + 5 * math.cos(ang)), int(cy + 5 * math.sin(ang)), hexc(line_hx))
    elif kind == "tri":
        for y in range(32):
            for x in range(32):
                if (x + y) % 16 == 0 or (x - y) % 16 == 0:
                    t.set(x, y, hexc(line_hx))
    elif kind == "diamond":
        for y in range(32):
            for x in range(32):
                if abs((x % 16) - 8) + abs((y % 16) - 8) == 7:
                    t.set(x, y, hexc(line_hx))
    t.speckle(20, [shade(hexc(base_hx), 1.2), shade(hexc(base_hx), 0.8)])
    return t


def tx_paving(seed):
    t = Tex(32, 32, hexc("#C2BEB4"), seed)
    t.noise(5)
    for i in range(32):
        t.set(i, 0, hexc("#9C988E"))
        t.set(0, i, hexc("#9C988E"))
        t.set(i, 16, hexc("#AAA69C"))
    t.speckle(20, [hexc("#A8A49A"), hexc("#D2CEC4")])
    return t


def tx_hex(seed):
    """Esports wall (ru_es_overview): near-black hexagon relief with faint blue-lit edges (fidelity-3: the grey
    relief read as cinder block)."""
    # fidelity-3 (round 2): ru_es_overview / ru_es_oelrich_9352 show FLAT matte black walls (the hex shapes are only the
    # lit neon clusters, int_ru_hex_neon); the 8-texel hex relief read as brick courses. A faint soft mottle only.
    t = Tex(32, 32, hexc("#15161C"), seed)
    for y in range(32):
        for x in range(32):
            k = 1.0 + 0.05 * math.sin(x * 0.37 + y * 0.21) * math.cos(y * 0.29 - x * 0.11)
            t.set(x, y, shade(hexc("#15161C"), k))
    t.noise(1)
    return t


def tx_hex_neon(seed):
    """Lit hex neon panel cluster (ru_es_overview, ru_es_pods): white-blue outlines on clear."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    glow = hexc("#DCE8FF")
    edge = hexc("#6A9CFF")
    cells = [(10, 9), (22, 9), (34, 9), (16, 20), (28, 20), (40, 20), (52, 20), (46, 9)]
    for cx, cy in cells:
        pts = [(cx + 6 * math.cos(math.radians(30 + 60 * k)), cy + 6 * math.sin(math.radians(30 + 60 * k)))
               for k in range(6)]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            t.line(a[0], a[1], b[0], b[1], glow)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            t.line(a[0] + 0.6, a[1] + 0.6, b[0] + 0.6, b[1] + 0.6, edge)
    return t


def tx_gator_skin(seed):
    """Gator-skin wall behind the UF letters (ru_atrium_uf_letters_flickr): large irregular rounded plates in white,
    cream and light grey with dark grout (a periodic Voronoi of ~13 jittered sites; ~0.28 m plates at 1.0 m/tile,
    the photo's plate size: about 9 plates across a 2.5 m letter)."""
    # fix round 2 (fidelity, ru_atrium_uf_letters_flickr): light white / cream plates with thin, only slightly
    # darker seams (the grout was a dark (118,118,122) 1-2 px line that read as grey cobblestone)
    # fix round 5 (fidelity-1, ru_atrium_uf_letters_flickr zoom): the figure / ground was inverted (pale plates on a
    # connected grey grout). The photo: soft light-grey / taupe rounded, slightly elongated plates (~0.3-0.4 m) on a
    # connected WHITE / cream network (~30 % of the area). Now: 3 x 3 jittered periodic Voronoi sites per 32 px tile
    # (the panel maps the tile over 1.0 m: ~0.33 m plates), anisotropic metric (plates longer than tall), taupe
    # plates #C9C4BB..#D6D2CA, a cream network #F3F1EC about 2 texels wide (6 cm) with a soft 1-texel blend (no
    # 1-texel high-contrast line: no mipmaps), plates a touch lighter toward their rim (rounded).
    net = hexc("#F3F1EC")
    t = Tex(32, 32, net, seed)
    pal = [hexc("#CCC7BF"), hexc("#D6D2CA"), hexc("#D1CCC4"), hexc("#C9C4BB"), hexc("#D4CFC6"), hexc("#CFCAC1")]
    sites = []
    cell = 32.0 / 3.0
    for gy in range(3):
        for gx in range(3):
            sites.append((gx * cell + cell / 2 + t.r.uniform(-2.4, 2.4), gy * cell + cell / 2 + t.r.uniform(-2.2, 2.2),
                          pal[(gx * 2 + gy * 4) % len(pal)], 1.0 + t.r.uniform(-0.02, 0.02)))
    for y in range(32):
        for x in range(32):
            ds = []
            for sx, sy, c, k in sites:
                dx = min(abs(x + 0.5 - sx), 32 - abs(x + 0.5 - sx))
                dy = min(abs(y + 0.5 - sy), 32 - abs(y + 0.5 - sy))
                ds.append((math.hypot(dx * 0.85, dy * 1.1), c, k))
            ds.sort(key=lambda q: q[0])
            d1, c, k = ds[0]
            gap = ds[1][0] - d1
            if gap < 1.5:
                t.set(x, y, net)
            elif gap < 2.6:
                t.set(x, y, mix(net, shade(c, k), 0.45 + 0.5 * (gap - 1.5) / 1.1))
            else:
                t.set(x, y, shade(c, k * (1.0 + 0.025 * max(0.0, 1.0 - (gap - 2.6) / 2.5))))
    t.noise(1)
    return t


def tx_cafe_bay(seed):
    """fix round 5 (fidelity-1, ru_atrium_enr_lounge): one Orange & Brew glazed bay, 32 x 64 over 1.25 x 2.0 m (row 0
    = the top): a warm-lit cafe seen through the glass (amber back wall, a lit pendant, an orange Orange & Brew poster,
    a dark wood counter with a white top), with a soft 2-texel diagonal sheen. No 1-texel high-contrast lines."""
    base = hexc("#E2BE88")
    t = Tex(32, 64, base, seed)
    for y in range(64):
        k = 1.05 - 0.13 * (y / 63.0)          # brighter toward the top (the lights)
        for x in range(32):
            t.set(x, y, shade(base, k))
    t.rect(22, 16, 29, 47, hexc("#8A5E3A"))           # a darker doorway / back room at the right
    t.rect(0, 38, 31, 39, hexc("#9A6A40"))            # back-wall shelf band
    t.rect(4, 20, 16, 35, hexc("#E8661A"))            # the poster: orange with a cream roundel and a text bar
    t.disc(10.5, 25.5, 3.2, hexc("#F6E8D0"))
    t.rect(6, 31, 14, 32, hexc("#F6E8D0"))
    t.rect(15, 0, 16, 9, hexc("#6A4A34"))             # a pendant lamp: 2 px cord and a bright shade
    t.disc(16.0, 12.0, 3.0, hexc("#FFF0C4"))
    t.rect(0, 46, 31, 47, hexc("#F4F2EE"))            # counter: white top, dark wood front
    t.rect(0, 48, 31, 63, hexc("#6E4A2E"))
    for x in range(1, 32, 8):
        t.rect(x, 50, x + 1, 63, hexc("#5E3E26"))
    for y in range(64):                               # glass sheen: a soft 2-texel diagonal streak
        for x in range(32):
            if (x + y // 2) % 32 in (6, 7):
                t.set(x, y, mix(t.get(x, y)[:3], hexc("#FFFFFF"), 0.35))
    t.noise(1)
    return t


def tx_office_bay(seed):
    """fix round 5 (fidelity-1, ru_atrium_enr_vertical): one glass office-front bay, 32 x 64 over ~1.25 x 2.6 m (row
    0 = the top): a pale lit office behind blue-grey glass (a ceiling light band, a UF-blue pinboard, a desk with a
    monitor and a navy chair), a frosted privacy band at eye height and a soft diagonal sheen. Edges >= 2 texels."""
    base = hexc("#C8D2D8")
    t = Tex(32, 64, base, seed)
    for y in range(64):
        k = 1.06 - 0.12 * (y / 63.0)
        for x in range(32):
            t.set(x, y, shade(base, k))
    t.rect(0, 2, 31, 3, hexc("#F2F4F0"))              # ceiling light band
    t.rect(4, 14, 13, 24, hexc("#3A5A9A"))            # UF-blue pinboard with two notes
    t.rect(6, 16, 8, 18, hexc("#F0E6C8"))
    t.rect(10, 19, 11, 21, hexc("#E8661A"))
    for y in range(28, 31):                           # frosted privacy band
        for x in range(32):
            t.set(x, y, mix(t.get(x, y)[:3], hexc("#F4F6F6"), 0.55))
    t.rect(18, 34, 26, 42, hexc("#2A2C32"))           # monitor (blue screen inside)
    t.rect(19, 35, 25, 40, hexc("#6A8EC0"))
    t.rect(21, 43, 22, 44, hexc("#2A2C32"))
    t.rect(0, 45, 31, 46, hexc("#9A7A56"))            # desk top and dark front
    t.rect(14, 47, 31, 63, hexc("#5A5E66"))
    t.rect(4, 44, 11, 58, hexc("#26304E"))            # navy chair
    for y in range(64):                               # glass sheen
        for x in range(32):
            if (x + y // 2) % 32 in (20, 21):
                t.set(x, y, mix(t.get(x, y)[:3], hexc("#FFFFFF"), 0.3))
    t.noise(1)
    return t


def tx_sign_ob(seed):
    """fix round 5 (fidelity-1): the Orange & Brew fascia sign over its glazed bays (64 x 32: ORANGE & / BREW in
    the 5 px font, orange on the white fascia, with a soft orange rule under it)."""
    bg = hexc("#F2F0EC")
    t = Tex(64, 32, bg, seed)
    t.noise(1)
    org = hexc("#E2601A")
    font_center(t, "ORANGE &", 6, org, font=FONT5)
    font_center(t, "BREW", 16, org, font=FONT5)
    t.rect(10, 26, 54, 28, mix(bg, org, 0.8))
    return t


def tx_acoustic(seed):
    """White 3-D triangular acoustic panels (ru_os_grand_ballroom_1): lit / shaded facets."""
    t = Tex(32, 32, hexc("#E6E6E4"), seed)
    for y in range(32):
        for x in range(32):
            cx, cy = x % 16, y % 16
            up = cy < 8
            k = 1.0
            if up:
                k = 1.04 if cx < 8 else 0.88
            else:
                k = 0.95 if cx < 8 else 0.80
            if (cx == 0) or (cy == 0):
                k = 0.75
            t.set(x, y, shade(hexc("#E6E6E4"), k))
    return t


def tx_wood(base_hx, seed, stripe=4, gap_k=0.7, vertical=True):
    base = hexc(base_hx)
    t = Tex(32, 32, base, seed)
    for i in range(32):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        for j in range(32):
            x, y = (i, j) if vertical else (j, i)
            c = shade(base, k * (gap_k if i % stripe == stripe - 1 else 1.0))
            if t.r.random() < 0.04:
                c = shade(c, 0.9)
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_chevron(seed):
    """Senate Chamber dais wall (ru_os_chamber): ONE 9 m cherry feature wall, mapped once (fidelity-3, round 2: the
    0.6 m zigzag read like a rug). Large cherry panels in three courses split by horizontal joints, and a few broad
    diagonal reveals forming one big shallow chevron across the whole wall; each panel a slightly different tone
    (the photo's veneer panels), a faint vertical grain."""
    base = hexc("#B4663C")
    t = Tex(64, 32, base, seed)
    joints = (11, 22)

    def chev(x):                                    # the big chevron: down from the left, up to the right
        return 5.0 + 12.0 * x / 38.0 if x <= 38 else 17.0 - 9.0 * (x - 38) / 25.0

    def chev2(x):                                   # a second, parallel reveal under it (the photo's pair of lines)
        return chev(x) + 10.0

    tones = (1.0, 0.9, 1.07, 0.94, 1.11, 0.86, 1.03, 0.95)
    for y in range(32):
        for x in range(64):
            cid = (y > joints[0]) + (y > joints[1]) * 2 + (y > chev(x)) * 4 + (x > 38) * 1
            k = tones[cid % len(tones)] * (1.0 + 0.035 * math.sin(x * 1.9 + (x % 7)) + 0.02 * math.sin(y * 0.7))
            t.set(x, y, shade(base, k))
    rev, hi = hexc("#4A2214"), hexc("#D89064")
    for y in joints:
        for x in range(64):
            t.set(x, y, rev)
            t.set(x, y + 1, mix(t.get(x, y + 1)[:3], hi, 0.35))
    for fn in (chev, chev2):
        for x in range(64):
            yy = fn(x)
            y0 = int(math.floor(yy))
            f = yy - y0
            if 0 <= y0 < 32:
                t.set(x, y0, mix(t.get(x, y0)[:3], rev, 1.0 - 0.5 * f))
            if 0 <= y0 + 1 < 32:
                t.set(x, y0 + 1, mix(t.get(x, y0 + 1)[:3], rev, 0.5 * f + 0.25))
            if 0 <= y0 + 2 < 32:
                t.set(x, y0 + 2, mix(t.get(x, y0 + 2)[:3], hi, 0.3))
    t.noise(2)
    return t


def tx_brick(seed):
    base, mortar = hexc("#A2533C"), hexc("#C2B29A")
    t = Tex(32, 32, base, seed)
    for y in range(32):
        course = y // 4
        for x in range(32):
            xs = x + (4 if course % 2 else 0)
            if y % 4 == 3 or xs % 8 == 7:
                t.set(x, y, mortar)
            else:
                t.set(x, y, shade(base, 1.0 + ((course * 7 + xs // 8 * 3) % 5 - 2) * 0.04))
    t.noise(5)
    return t


def tx_mirror(seed):
    """Dance studio mirror wall (ru_os_dance_1): the room reflected: pale wall band over a dark floor band."""
    t = Tex(32, 32, hexc("#B6C6CE"), seed)
    for y in range(32):
        for x in range(32):
            d = (x - y * 0.5) % 16
            k = 1.18 if d < 2 else 1.0
            base = hexc("#C8D2D8") if y < 22 else hexc("#4A4E56")
            t.set(x, y, shade(base, k * (0.92 + 0.08 * y / 31)))
    for y in range(32):
        t.set(15, y, hexc("#8A969C"))
    return t


def tx_counter_front(seed):
    """Food court counter front (ru_food_court_counter_2023): light-blue horizontal siding in white frames."""
    t = Tex(32, 32, hexc("#A6D2DE"), seed)
    for y in range(32):
        for x in range(32):
            c = hexc("#A6D2DE")
            if y % 4 == 3:
                c = hexc("#86B2C0")
            if x in (0, 1) or y in (0, 31):
                c = hexc("#F0EEE6")
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_ceiling(seed, base="#E4E2DC"):
    """2 x 2 ft acoustic tile with a light grid (every Reitz room photo)."""
    t = Tex(32, 32, hexc(base), seed)
    t.noise(3)
    t.speckle(60, [shade(hexc(base), 0.86), shade(hexc(base), 0.92)])
    for i in range(32):
        t.set(i, 0, hexc("#F4F4F2"))
        t.set(i, 16, hexc("#F4F4F2"))
        t.set(0, i, hexc("#F4F4F2"))
        t.set(16, i, hexc("#F4F4F2"))
    return t


def tx_coffer(seed):
    """Grand Ballroom coffer field (ru_os_grand_ballroom_2): white luminous field crossed by gently waving slats."""
    t = Tex(32, 32, hexc("#FAFAF6"), seed)
    for x in range(32):
        for k in range(4):
            y = k * 8 + 2.0 * math.sin(2 * math.pi * x / 32.0 + k * 0.9)
            yi = int(math.floor(y)) % 32
            t.set(x, yi, hexc("#C8CACE"))
            t.set(x, (yi + 1) % 32, hexc("#E2E4E6"))
    return t


def tx_led(seed):
    return _flat("#FFFFFF", seed, amp=1)


def tx_felt(seed):
    t = Tex(32, 32, hexc("#1E5ACC"), seed)
    t.noise(4)
    return t


def tx_leather(hx, seed):
    """Booth upholstery (ru_gr_booth_row): channel tufting."""
    t = Tex(32, 32, hexc(hx), seed)
    for y in range(32):
        for x in range(32):
            k = 1.0 - 0.18 * (1.0 - abs((x % 8) - 3.5) / 3.5) ** 0.5 * (0.5 if x % 8 else 1.0)
            k = 0.82 if x % 8 == 0 else 1.0 + 0.06 * math.cos((x % 8 - 4) / 4.0)
            t.set(x, y, shade(hexc(hx), k))
    t.noise(3)
    return t


def tx_fabric(hx, seed):
    t = Tex(32, 32, hexc(hx), seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, shade(hexc(hx), 1.06 if (x + y) % 2 else 0.95))
    t.noise(4)
    return t


def tx_gator_green(seed):
    t = Tex(32, 32, hexc("#4E6E32"), seed)
    for y in range(32):
        for x in range(32):
            xs = (x + (4 if (y // 4) % 2 else 0)) % 8
            k = 0.7 if (y % 4 == 0 or xs == 0) else 1.0 + 0.1 * math.sin(x + y)
            t.set(x, y, shade(hexc("#4E6E32"), k))
    t.noise(4)
    return t


def tx_picket(seed):
    """Atrium railing infill (ru_atrium_hdr_flickr): silver pickets every 11 cm, top + bottom rails, with the
    small gator cut-out the Alligator reported in the panel between two pickets."""
    metal = hexc("#A4A8AC")
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    for y in range(32):
        for x in range(32):
            if y <= 1 or y >= 30 or x % 3 == 1 or y in (14, 15):
                t.set(x, y, shade(metal, 1.12 if y in (0, 30, 14) else 1.0))
    # gator silhouette on the mid rail (head left, tail right)
    for x in range(4, 28):
        t.set(x, 13, metal)
        t.set(x, 16, metal)
    for x in range(3, 9):
        t.set(x, 12, metal)
    return t


def tx_row(kind, seed):
    """Cut-out row of 4 chairs seen from behind / the side (64 x 32 = 4 seats x 0.5 m wide, ~1.0 m tall)."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    if kind == "navy":       # banquet chairs (ballrooms): navy padded back, dark frame
        back, frame = hexc("#26346A"), hexc("#18181C")
        for i in range(4):
            x0 = i * 16 + 2
            t.rect(x0, 2, x0 + 11, 17, back)
            t.frame(frame, x0, 2, x0 + 11, 17)
            t.rect(x0, 18, x0 + 11, 20, shade(back, 0.8))
            t.rect(x0 + 1, 21, x0 + 1, 31, frame)
            t.rect(x0 + 10, 21, x0 + 10, 31, frame)
    elif kind == "rion":     # fix round 4 (fidelity-4 pass; ru_os_rion_ballroom): dark navy pad, cherry frame + legs
        # iteration 9 (fidelity-4 improvement 13; ru_os_rion_ballroom): near-black plum frame + back (~15, 3, 5;
        # were navy pad / cherry frame), the royal-blue seat edge kept
        back, frame, seat = hexc("#24100F"), hexc("#160608"), hexc("#2A3C96")
        for i in range(4):
            x0 = i * 16 + 2
            t.rect(x0, 2, x0 + 11, 17, frame)
            t.rect(x0 + 2, 4, x0 + 9, 16, back)
            t.rect(x0, 18, x0 + 11, 20, seat)
            t.rect(x0 + 1, 21, x0 + 2, 31, frame)
            t.rect(x0 + 9, 21, x0 + 10, 31, frame)
    elif kind == "black":    # stacking chairs (meeting rooms): black shell, chrome legs
        shell, leg = hexc("#2A2A2E"), hexc("#9EA2A6")
        for i in range(4):
            x0 = i * 16 + 2
            for y in range(3, 18):
                w = 11 - (1 if y < 5 else 0)
                t.rect(x0 + (11 - w) // 2, y, x0 + (11 + w) // 2, y, shade(shell, 1.0 + 0.1 * (y < 6)))
            t.rect(x0, 18, x0 + 11, 20, shell)
            t.line(x0 + 1, 21, x0, 31, leg)
            t.line(x0 + 10, 21, x0 + 11, 31, leg)
    elif kind == "aud":      # auditorium seats (ru_os_auditorium_1): navy fabric, honey wood arm caps
        fab, wood = hexc("#2A3A6A"), hexc("#B07A40")
        for i in range(4):
            x0 = i * 16 + 1
            t.rect(x0 + 1, 1, x0 + 13, 20, fab)
            t.rect(x0 + 1, 1, x0 + 13, 2, shade(fab, 1.2))
            t.rect(x0 - 1, 14, x0 + 0, 31, wood)
            t.rect(x0 + 1, 21, x0 + 13, 26, shade(fab, 0.8))
    elif kind == "wood":     # auditorium seats from the front: wood backs (ru_os_auditorium_3)
        # fix round 4 (fidelity-4 pass): darker red-brown, as the backs read in ru_os_auditorium_2/3 (was #9A6434)
        wood, fab = hexc("#7A4A2C"), hexc("#2A3A6A")
        for i in range(4):
            x0 = i * 16 + 1
            t.rect(x0 + 1, 1, x0 + 13, 20, wood)
            t.rect(x0 + 1, 1, x0 + 13, 1, shade(wood, 1.25))
            t.rect(x0 + 1, 21, x0 + 13, 25, fab)
            t.rect(x0 - 1, 14, x0, 31, shade(wood, 0.8))
    t.noise(2)
    return t


def tx_door(kind, seed):
    """One door leaf, 32 x 64 (~1.0 x 2.2 m incl. a 4 px frame)."""
    if kind == "honey":       # meeting rooms (ru_os_2345_2350): honey wood, narrow vision panel, lever
        t = Tex(32, 64, hexc("#B07A40"), seed)
        for x in range(32):
            k = 1.0 + 0.06 * math.sin(x * 0.9) + t.r.uniform(-0.03, 0.03)
            for y in range(64):
                t.set(x, y, shade(hexc("#B07A40"), k))
        t.rect(20, 10, 24, 34, hexc("#2E3A44"))
        t.frame(hexc("#8C8E90"), 19, 9, 25, 35)
        t.rect(4, 33, 9, 34, hexc("#C8CACC"))
        t.frame(hexc("#6A6C6E"), 0, 0, 31, 63)
    elif kind == "walnut":    # Grand Ballroom (ru_os_grand_ballroom_1): walnut leaf, tall pull
        t = Tex(32, 64, hexc("#5E3C24"), seed)
        for x in range(32):
            k = 1.0 + 0.08 * math.sin(x * 1.3) + t.r.uniform(-0.04, 0.04)
            for y in range(64):
                t.set(x, y, shade(hexc("#5E3C24"), k))
        t.rect(25, 20, 26, 40, hexc("#D0D2D4"))
        t.frame(hexc("#3A2616"), 0, 0, 31, 63)
    elif kind == "glass":     # aluminium storefront door
        t = Tex(32, 64, hexc("#4A6478"), seed)
        for y in range(64):
            for x in range(32):
                d = (x - y * 0.4) % 20
                t.set(x, y, shade(hexc("#4A6478"), 1.25 if d < 3 else 1.0))
        t.rect(0, 0, 31, 3, hexc("#B4B8BC"))
        t.rect(0, 58, 31, 63, hexc("#B4B8BC"))
        t.rect(0, 0, 3, 63, hexc("#B4B8BC"))
        t.rect(28, 0, 31, 63, hexc("#B4B8BC"))
        t.rect(4, 30, 27, 31, hexc("#9A9EA2"))
    else:                     # steel service / stair door
        t = Tex(32, 64, hexc("#A8ACB0"), seed)
        t.noise(3)
        t.rect(4, 32, 9, 33, hexc("#4A4C50"))
        t.rect(20, 8, 26, 22, hexc("#3A4650"))
        t.frame(hexc("#6A6C70"), 0, 0, 31, 63)
    return t


def tx_video_wall(seed):
    """Bowling video wall above the pins (ru_gr_lane_screens, ru_gr_lanes_crowd_tvs): ONE continuous broadcast
    image across all 14 lanes; this tile wraps seamlessly left-right (a TV studio: deep blue set, light beams, two
    presenters at a desk, a red / white lower-third band) and is repeated along the wall."""
    t = Tex(64, 32, hexc("#14286A"), seed)
    for y in range(32):
        for x in range(64):
            c = mix(hexc("#2C5CC8"), hexc("#0C1A4C"), y / 31)
            # soft periodic light beams (period 32 px: seamless)
            k = 0.5 + 0.5 * math.cos((x - 0.6 * y) * 2 * math.pi / 32)
            t.set(x, y, mix(c, hexc("#7AA6F0"), 0.28 * k ** 4))
    # studio set: a city-light backdrop band, a pale screen behind the desk, presenters' desk + two figures
    for x in range(64):
        for y in range(6, 15):
            if (x * 7 + y * 3) % 11 == 0:
                t.set(x, y, hexc("#C8D8FF"))
    t.rect(22, 5, 44, 15, hexc("#5A8AE0"))
    t.rect(23, 6, 43, 14, hexc("#E8EEFA"))
    t.rect(16, 19, 50, 20, hexc("#E8ECF4"))
    t.rect(16, 21, 50, 24, hexc("#1E3C9E"))
    t.rect(30, 22, 36, 23, hexc("#F06A1E"))
    for fx, suit, skin in ((26, "#1A1C24", "#C08A64"), (40, "#8A1E28", "#7A5038")):
        t.rect(fx - 2, 13, fx + 2, 18, hexc(suit))
        t.rect(fx - 1, 10, fx + 1, 12, hexc(skin))
        t.rect(fx - 1, 9, fx + 1, 9, hexc("#2A1A12"))
    # lower third: red band + white ticker (full width: seamless)
    t.rect(0, 26, 63, 28, hexc("#C42A2A"))
    t.rect(0, 29, 63, 31, hexc("#F4F4F2"))
    for x in range(2, 64, 5):
        t.rect(x, 30, x + 2, 30, hexc("#3A3A44"))
    return t


def tx_masking(seed):
    """Masking fascia over the pin decks (ru_gr_lane_screens): dark navy under the video wall with a thin blue LED
    line on top (the gator mural of ru_gr_kosmic_lanes is the blacklight show only, not the house look)."""
    t = Tex(64, 32, hexc("#141C3C"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#1A2450"), hexc("#0C1230"), y / 31))
    t.rect(0, 0, 63, 1, hexc("#4A7CF0"))
    for x in range(0, 64, 16):
        t.rect(x, 2, x, 31, hexc("#0A0E24"))
    t.noise(2)
    return t


def tx_score_tv(seed):
    """Overhead scoring monitor (ru_gr_lanes_monitors): blue frame grid with names and scores."""
    t = Tex(32, 32, hexc("#1E3C9E"), seed)
    t.rect(1, 1, 30, 30, hexc("#2A4AB0"))
    for r in range(4):
        y = 4 + r * 7
        t.rect(2, y, 29, y + 5, hexc("#F0F0F0") if r % 2 == 0 else hexc("#DCE4F4"))
        for c in range(6):
            t.set(10 + c * 3, y + 1, hexc("#222222"))
            t.set(10 + c * 3, y + 3, hexc("#CC2222"))
        t.rect(3, y + 1, 7, y + 3, hexc("#F06A1E"))
    t.frame(hexc("#0A0A0C"))
    return t


def tx_game_screen(seed):
    """A game on a screen (esports stations, arcade, lounge TVs): sky, track, characters."""
    t = Tex(32, 32, hexc("#4A70A8"), seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, mix(hexc("#6AA0E8"), hexc("#B8D8F8"), y / 18) if y < 18 else
                  mix(hexc("#3A8A3A"), hexc("#285A28"), (y - 18) / 13))
    for x in range(32):
        t.set(x, 18 + abs(x - 16) // 6, hexc("#E8E0C8"))
    t.rect(8, 20, 11, 24, hexc("#D82020"))
    t.rect(20, 21, 23, 25, hexc("#2030D8"))
    t.disc(25, 6, 3, hexc("#FFF0A0"))
    t.frame(hexc("#0C0C10"))
    return t


def tx_arcade(seed):
    """Arcade cabinet side art (ru_gr_arcade): purple / magenta panel with a lit marquee + screen."""
    t = Tex(32, 64, hexc("#5A2A86"), seed)
    for y in range(64):
        for x in range(32):
            t.set(x, y, mix(hexc("#7A3AB0"), hexc("#2A1048"), y / 63))
    t.rect(2, 2, 29, 9, hexc("#F0C030"))
    font_center(t, "PLAY", 3, hexc("#C02020"), font=FONT3)
    t.rect(4, 13, 27, 30, hexc("#101014"))
    t.rect(6, 15, 25, 28, hexc("#3A80D0"))
    t.rect(8, 22, 12, 26, hexc("#E04040"))
    t.rect(18, 20, 22, 24, hexc("#40E060"))
    t.rect(3, 34, 28, 40, hexc("#222228"))
    for x in (8, 13, 18, 23):
        t.disc(x, 37, 1.6, [hexc("#E02020"), hexc("#20A0E0"), hexc("#F0D020"), hexc("#20E040")][(x // 5) % 4])
    for y in range(42, 64, 6):
        t.line(0, y, 31, y - 8, hexc("#E040C0"))
    return t


def tx_proj_screen(seed):
    t = Tex(32, 32, hexc("#F2F2F0"), seed)
    t.noise(1)
    t.frame(hexc("#1A1A1C"))
    t.rect(0, 0, 31, 1, hexc("#1A1A1C"))
    return t


def tx_sign(lines, bg_hx, seed, frame_hx=None, w=64, h=32):
    t = Tex(w, h, hexc(bg_hx), seed)
    t.noise(2)
    for text, y, scale, col, font in lines:
        font_center(t, text, y, hexc(col), scale=scale, font=font)
    if frame_hx:
        t.frame(hexc(frame_hx))
    return t


def tx_sign_gameroom(seed):
    """REITZ UNION GAME ROOM wall graphic (ru_gr_entry_graphic, ru_gr_wall_graphic_billiards): navy space scene,
    planets and a bowling ball, white and orange lettering."""
    t = Tex(64, 32, hexc("#1A2660"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#22307A"), hexc("#10163E"), y / 31))
    t.speckle(26, [hexc("#E8ECFF"), hexc("#8CA4FF")])
    t.disc(52, 22, 7, hexc("#F06A1E"))
    t.disc(50, 20, 2, hexc("#F4A060"))
    for x in range(42, 62):
        t.set(x, 22 + (x - 52) // 4, hexc("#F0D8A0"))
    t.disc(8, 26, 4, hexc("#2848C0"))
    t.disc(7, 25, 1, hexc("#101010"))
    font_text(t, "REITZ UNION", 3, 3, hexc("#DCE0EC"), font=FONT3)
    font_text(t, "GAME", 3, 10, hexc("#FFFFFF"), scale=1)
    font_text(t, "ROOM", 3, 19, hexc("#FFFFFF"), scale=1)     # fix round 4 (fidelity-3): white, as GAME (ru_gr_entry_graphic)
    return t


def tx_sign_gameroom_uf(seed):
    """fix round 5 (fidelity-3; ru_gr_wall_graphic_billiards): the billiards-wall graphic, its own variant of the
    navy space scene: GAME ROOM in big white letters over THE UNIVERSITY / OF FLORIDA (orange), a blue planet top
    right, the big orange planet with its ring bottom right and a bowling ball beside it."""
    t = Tex(64, 32, hexc("#1A2660"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#10163E"), hexc("#22307A"), y / 31))
    t.speckle(22, [hexc("#E8ECFF"), hexc("#8CA4FF")])
    t.disc(60, 4, 3, hexc("#2C5CD8"))
    t.disc(59, 3, 1, hexc("#6C94F0"))
    t.disc(55, 25, 6, hexc("#F06A1E"))
    t.disc(53, 23, 2, hexc("#F4A060"))
    for x in range(46, 64):
        t.set(x, 25 + (x - 55) // 4, hexc("#F0D8A0"))
    t.disc(45, 28, 3, hexc("#203890"))
    t.set(44, 27, hexc("#0C0C14"))
    t.set(46, 27, hexc("#0C0C14"))
    font_text(t, "GAME ROOM", 2, 4, hexc("#FFFFFF"))
    font_text(t, "THE UNIVERSITY", 2, 14, hexc("#DCE0EC"), font=FONT3)
    font_text(t, "OF FLORIDA", 2, 20, hexc("#F27A2A"), font=FONT3)
    return t


def tx_wall_royal_wash(seed):
    """fix round 5 (fidelity-3; ru_os_g325): G325's royal-blue bay lit from the top by a row of three wall-washer
    downlights: soft lighter scallops fading down the wall (smooth ramps, no hard 1-texel edges: no mipmaps).
    64 x 32 once over the bay (row 0 = the top)."""
    base, hi = hexc("#1C38A0"), hexc("#7C9CF4")
    t = Tex(64, 32, base, seed)
    for y in range(32):
        for x in range(64):
            k = 0.0
            for cx in (10.5, 31.5, 52.5):
                dx = (x - cx) / 8.5
                k = max(k, 1.0 - dx * dx - (y - 2) / 15.0)
            t.set(x, y, mix(base, hi, max(0.0, min(1.0, k)) ** 1.5 * 0.95))
    t.noise(2)
    return t


def tx_sign_esports(seed):
    """GATOR ESPORTS CENTER lit letters on clear (ru_es_overview): ONE long line of big white letters. The line is
    128 px wide: its left half is rows 0-15, its right half rows 16-31 (the sign is two quads side by side, see
    esports() in interiors/reitz.py)."""
    return tx_sign_esports_part(seed, 0)


def tx_sign_esports_part(seed, part):
    """fidelity-3 (round 2; ru_es_overview): the sign is BOLD ITALIC white letters with a blue glow that fill the
    bulkhead band (the 1-texel 5x7 line read as a small plaque). The line is 256 x 16 px: FONT5 at 2x (10 x 14 px
    glyphs), strokes thickened one texel, sheared ~3 px for the italic, a 1-texel blue halo. It is cut in four
    64 x 16 strips: int_ru_sign_esports holds strips 0 (rows 0-15) and 1 (rows 16-31), int_ru_sign_esports_b
    strips 2 and 3 (esports() in interiors/reitz.py draws four quads)."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    text = "GATOR ESPORTS CENTER"
    W_, H_ = 256, 16
    on = [[False] * W_ for _ in range(H_)]
    pitch = 12
    x0 = (W_ - (len(text) * pitch - 2 + 1 + 3)) // 2
    for i, ch in enumerate(text):
        g = FONT5.get(ch)
        if g is None:
            continue
        for gy, row in enumerate(g):
            for gx, c in enumerate(row):
                if c != "#":
                    continue
                for sy in range(2):
                    py = 1 + gy * 2 + sy
                    shear = (13 - (py - 1)) // 5                      # italic: the top leans right
                    for sx in range(3):                               # 2 px + 1 bold
                        px = x0 + i * pitch + gx * 2 + sx + shear
                        if 0 <= px < W_ and 0 <= py < H_:
                            on[py][px] = True
    white, halo = hexc("#F4F7FF"), hexc("#3C64F0")
    for y in range(H_):
        for x in range(W_):
            if on[y][x]:
                c = white
            elif any(on[yy][xx] for yy in range(max(0, y - 1), min(H_, y + 2))
                     for xx in range(max(0, x - 1), min(W_, x + 2))):
                c = halo
            else:
                continue
            strip = x // 64
            if strip // 2 != part:
                continue
            t.set(x % 64, y + (16 if strip % 2 else 0), c)
    return t


def tx_sign_union(seed):
    """J. WAYNE REITZ UNION letters (ru_south_ground_entrance; the north soffit, ru_north_entrance_hotelsite)."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    font_center(t, "J. WAYNE", 4, hexc("#E8E8E8"))
    font_center(t, "REITZ UNION", 16, hexc("#E8E8E8"), font=FONT5, spacing=0)
    return t


def tx_banner_welcome(seed):
    """WELCOME TO THE REITZ UNION banner on the Level 1 rail over the UF letters (ru_atrium_uf_letters_flickr)."""
    t = Tex(64, 16, hexc("#1A2246"), seed)
    t.noise(2)
    font_center(t, "WELCOME TO THE", 1, hexc("#FFFFFF"), font=FONT3)
    font_center(t, "REITZ UNION", 8, hexc("#F06A1E"), font=FONT5, spacing=0)
    return t


def tx_floor_atlas(seed):
    """Elevator floor labels: 8 cells of 16 x 16 (4 x 2): LL G 1 2 / 3 4 5 6, white on UF blue, an orange rule."""
    t = Tex(64, 32, hexc("#1E3C9E"), seed)
    labels = ["LL", "G", "1", "2", "3", "4", "5", "6"]
    for i, lab in enumerate(labels):
        cx, cy = (i % 4) * 16, (i // 4) * 16
        t.frame(hexc("#F06A1E"), cx, cy, cx + 15, cy + 15)
        font_center(t, lab, cy + 4 if len(lab) == 1 else cy + 5, hexc("#FFFFFF"), x0=cx, x1=cx + 15, spacing=1,
                    font=FONT5 if len(lab) == 1 else FONT3)
    return t


# design pass (wayfinding): the destinations named on each floor's Blue elevator lobby sign, with the compass side
# they lie on as seen from the lobby centre (-444.8, -271.0) (interiors/reitz.py wayfinding()); None = no arrow
WAYFIND = {
    "LL": [("DANCE STUDIOS", "E"), ("CRAFT CENTER", "N")],
    "G": [("GAME ROOM", "S"), ("ESPORTS", "S"), ("ATRIUM", "E"), ("HOTEL DESK", "W")],
    "L1": [("FOOD COURT", "S"), ("ATRIUM", "E"), ("NORTH EXIT", "E")],
    "L2": [("GRAND BALLROOM", "W"), ("AUDITORIUM", "N"), ("MEETING ROOMS", "S")],
    "L3": [("RION BALLROOM", "S"), ("MEETING ROOMS", "N")],
    "L4": [("ARREDONDO CAFE", "E"), ("MATTHEWS SUITE", "S")],
    "L5": [("REITZ UNION", None), ("HOTEL", None), ("ROOMS 501-520", None)],
    "L6": [("REITZ UNION", None), ("HOTEL", None), ("ROOMS 601-620", None)],
}
# the arrow a viewer reads for a compass side, per sign face ("N" face: normal +y, read looking south)
WAYFIND_ARROW = {"N": {"E": "<", "W": ">", "S": "^", "N": "v"}, "S": {"E": ">", "W": "<", "N": "^", "S": "v"}}
FONT3X = dict(FONT3, **{"^": [".#.", "###", ".#.", ".#.", ".#."], "v": [".#.", ".#.", ".#.", "###", ".#."]})


def tx_wayfind(fid, face, seed):
    """One face ("N": normal +y, "S": normal -y) of floor fid's elevator-lobby wayfinding sign: UF blue, white caps
    with the arrows that face's reader needs, an orange rule along the bottom (64 x 32: the 4 KB RGBA16 limit).
    design + leftovers pass (user_03, user_11, C08: every real Reitz hanging sign is light grey with navy
    caps): light grey field, navy caps (was UF blue with white caps), the orange + navy rules kept."""
    t = Tex(64, 32, hexc("#E2E4E6"), seed)
    t.noise(2)
    lines = WAYFIND[fid]
    n = len(lines)
    y = max(1, (27 - (n * 7 - 2)) // 2)
    for name, side in lines:
        if side is None:
            txt = name
        else:
            a = WAYFIND_ARROW[face][side]
            txt = f"{name} >" if a == ">" else f"{a} {name}"
        font_center(t, txt, y, hexc("#1E2A5C"), font=FONT3X)
        y += 7
    t.rect(0, 28, 63, 29, hexc("#F06A1E"))
    t.rect(0, 30, 63, 31, hexc("#162C78"))
    return t


def tx_vendor(name, bg, fg, accent, seed, sub=None):
    t = Tex(64, 32, hexc(bg), seed)
    t.noise(2)
    font_center(t, name, 5 if sub else 9, hexc(fg), scale=1 if len(name) > 6 else 2 if len(name) <= 5 else 1,
                spacing=1)
    if sub:
        font_center(t, sub, 20, hexc(accent), font=FONT3)
    t.rect(0, 29, 63, 31, hexc(accent))
    return t


def tx_menu(seed):
    """Menu boards over a counter (ru_food_court_sonic_2025): dark screens with photo tiles and price lines."""
    t = Tex(64, 32, hexc("#22262E"), seed)
    for p in range(3):
        x0 = 1 + p * 21
        t.rect(x0, 1, x0 + 19, 30, hexc("#1A1C22"))
        t.rect(x0 + 2, 3, x0 + 17, 12, [hexc("#C86A2A"), hexc("#D8A030"), hexc("#B83A2A")][p])
        for r in range(4):
            y = 15 + r * 4
            t.rect(x0 + 2, y, x0 + 12, y + 1, hexc("#E8E8E8"))
            t.rect(x0 + 15, y, x0 + 17, y + 1, hexc("#F0C030"))
    return t


def tx_art(seed):
    """Framed art on a white wall (ru_the_gallery, ru_os_g315): three frames."""
    t = Tex(64, 32, hexc("#F0EEE8"), seed)
    frames = [(2, 6, 18, 26, "#1E3C9E"), (23, 4, 41, 28, "#C84A2A"), (46, 8, 61, 24, "#3A8A5A")]
    for x0, y0, x1, y1, c in frames:
        t.rect(x0, y0, x1, y1, hexc("#2A2420"))
        t.rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, hexc("#F4F2EC"))
        t.rect(x0 + 3, y0 + 3, x1 - 3, y1 - 3, hexc(c))
        for k in range(6):
            t.line(x0 + 3 + t.r.randrange(x1 - x0 - 6), y0 + 3, x0 + 3 + t.r.randrange(x1 - x0 - 6), y1 - 3,
                   shade(hexc(c), 1.4))
    return t


def tx_photos(seed):
    """Framed historic documents (ru_os_matthews_1/2; fix round 4, fidelity-4 pass): two variants, one per 32 x 32
    half (mapped once per frame, u 0-0.5 / 0.5-1): a dark walnut frame (2 px), a wide cream mat and a pale parchment
    print with soft brown drawing lines (low contrast: no 1-texel shimmer at range)."""
    t = Tex(64, 32, hexc("#ECE6D6"), seed)
    for k in range(2):
        x0 = k * 32
        t.rect(x0, 0, x0 + 31, 31, hexc("#4A2E20"))
        t.rect(x0 + 2, 2, x0 + 29, 29, hexc("#EEE8D8"))
        t.rect(x0 + 7, 7, x0 + 24, 24, hexc("#D8CCB0"))
        ink = hexc("#A8987A")
        if k == 0:              # a building elevation: roof line, columns
            t.rect(x0 + 9, 11, x0 + 22, 12, ink)
            for cx in range(x0 + 10, x0 + 22, 3):
                t.rect(cx, 13, cx, 21, ink)
            t.rect(x0 + 9, 21, x0 + 22, 22, ink)
        else:                   # a plan / certificate: title bar + text lines
            t.rect(x0 + 10, 9, x0 + 21, 10, hexc("#8E7E62"))
            for yy in range(13, 23, 3):
                t.rect(x0 + 9, yy, x0 + 22, yy, ink)
    t.noise(2)
    return t


def tx_mural_acc(seed):
    """Arts & Crafts Center mural (ru_acc_entrance_mural): colour burst around a navy roundel."""
    t = Tex(32, 32, hexc("#F4F2EE"), seed)
    cols = [hexc("#E8402A"), hexc("#F0C020"), hexc("#2A8AD8"), hexc("#3AB060"), hexc("#E86AA8"), hexc("#7AD0E8")]
    for k in range(40):
        a = k * 2 * math.pi / 40
        r1 = 15 if k % 2 else 12
        t.line(16, 16, 16 + r1 * math.cos(a), 16 + r1 * math.sin(a), cols[k % len(cols)])
    t.disc(16, 16, 7, hexc("#1E2450"))
    font_center(t, "ACC", 13, hexc("#FFFFFF"), font=FONT3)
    return t


def tx_flags(seed):
    """US (left) and Florida (right) flags, for the Senate Chamber dais (ru_os_chamber)."""
    t = Tex(64, 32, hexc("#F4F4F4"), seed)
    for y in range(32):
        for x in range(30):
            t.set(x, y, hexc("#C22A2A") if (y // 3) % 2 == 0 else hexc("#F4F4F4"))
    t.rect(0, 0, 13, 16, hexc("#2A3A8A"))
    for y in range(2, 16, 3):
        for x in range(1, 13, 3):
            t.set(x, y, hexc("#FFFFFF"))
    t.rect(30, 0, 33, 31, hexc("#C8B070"))
    t.rect(34, 0, 63, 31, hexc("#F4F4F4"))
    t.line(34, 0, 63, 31, hexc("#C22A2A"))
    t.line(35, 0, 63, 30, hexc("#C22A2A"))
    t.line(63, 0, 34, 31, hexc("#C22A2A"))
    t.line(62, 0, 34, 30, hexc("#C22A2A"))
    t.disc(48, 15, 4, hexc("#3A6AA8"))
    return t


def tx_exit(seed):
    t = Tex(32, 32, hexc("#2A1A1A"), seed)
    t.rect(1, 9, 30, 22, hexc("#F4F2EC"))
    font_center(t, "EXIT", 12, hexc("#D81E1E"), font=FONT5, spacing=1)
    return t


def tx_aed(seed):
    """AED wall cabinet (fidelity-3 round 2, Ground north-door corridor): a green 'AED' header (rows 0-11: the sign
    over the cabinet uses v 0.62-1) over a white door with a red heart + lightning bolt."""
    t = Tex(32, 32, hexc("#ECECE8"), seed)
    t.rect(0, 0, 31, 11, hexc("#1E8A4A"))
    font_center(t, "AED", 2, hexc("#FFFFFF"))
    t.disc(13, 19, 3, hexc("#D21E1E"))
    t.disc(19, 19, 3, hexc("#D21E1E"))
    for y in range(19, 27):
        w = 26 - y
        t.rect(16 - w - 1, y, 16 + w, y, hexc("#D21E1E"))
    t.line(17, 16, 14, 21, hexc("#FFFFFF"))
    t.line(14, 21, 18, 21, hexc("#FFFFFF"))
    t.line(18, 21, 15, 26, hexc("#FFFFFF"))
    t.frame(hexc("#9A9A98"), 0, 12, 31, 31)
    return t


def tx_dais(seed):
    """Podium / dais front (ru_os_chamber, fidelity-3 round 2): a plain cherry front with the photo's SMALL navy
    'UF FLORIDA' plaque (texels x 10-53, y 8-18; the Senate dais crops just the plaque with UVs) instead of the big
    UF roundel."""
    t = Tex(64, 32, hexc("#A85A34"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, shade(hexc("#A85A34"), 1.0 + 0.04 * math.sin(x * 1.7 + (x % 5)) + (0.04 if x in (0, 63) else 0)))
    t.noise(2)
    t.rect(10, 8, 53, 18, hexc("#1E2A5E"))
    t.frame(hexc("#D8DCE6"), 10, 8, 53, 18)
    font_text(t, "UF", 13, 10, hexc("#F2F4F8"))
    t.rect(25, 10, 25, 16, hexc("#F06A1E"))
    font_text(t, "FLORIDA", 27, 12, hexc("#F2F4F8"), font=FONT3)
    return t


def tx_window_view(seed):
    """Painted window view (hotel rooms, high windows): sky, campus canopy, brick buildings."""
    t = Tex(64, 32, hexc("#86A6BC"), seed)
    for y in range(32):
        for x in range(64):
            t.set(x, y, mix(hexc("#5E92D6"), hexc("#BCD6EE"), y / 20) if y < 20 else hexc("#4A6A3A"))
    for b in range(4):
        x0 = t.r.randrange(56)
        h = t.r.randrange(4, 10)
        t.rect(x0, 20 - h, x0 + 8, 21, hexc("#A2583E"))
        for x in range(x0 + 1, x0 + 8, 2):
            t.set(x, 20 - h + 2, hexc("#2E3A48"))
    for x in range(0, 64, 3):
        t.disc(x + t.r.uniform(-1, 1), 20 + t.r.uniform(-1, 1), 2.5, shade(hexc("#3E6A30"), t.r.uniform(0.8, 1.2)))
    t.rect(31, 0, 32, 31, hexc("#D8D8D4"))
    t.rect(0, 15, 63, 15, hexc("#D8D8D4"))
    return t


def tx_books(seed):
    """Free-library shelf (atrium): book spines on two shelves."""
    t = Tex(64, 32, hexc("#6A4A32"), seed)
    cols = ["#A83A2A", "#2A4A8A", "#D8B040", "#3A7A4A", "#E8E0D0", "#6A2A5A", "#E87A30"]
    for row in range(2):
        y0 = row * 16 + 2
        x = 1
        while x < 62:
            w = t.r.randrange(2, 5)
            h = t.r.randrange(9, 13)
            c = hexc(t.r.choice(cols))
            t.rect(x, y0 + 13 - h, min(62, x + w - 1), y0 + 12, c)
            t.set(x, y0 + 14 - h, shade(c, 1.3))
            x += w
        t.rect(0, y0 + 13, 63, y0 + 14, hexc("#4A3222"))
    return t


def tx_tv_hotel(seed):
    t = Tex(32, 32, hexc("#26323E"), seed)
    for y in range(32):
        for x in range(32):
            t.set(x, y, mix(hexc("#2A3A4A"), hexc("#141A20"), (x + y) / 62))
    t.line(4, 6, 12, 2, hexc("#4A5A6A"))
    t.frame(hexc("#0A0A0C"))
    return t


def tx_pins(seed):
    """Bowling pin face: white with two red neck stripes (mapped on the pin quads)."""
    t = Tex(32, 32, hexc("#F2F2EE"), seed)
    t.rect(0, 6, 31, 7, hexc("#C82222"))
    t.rect(0, 10, 31, 11, hexc("#C82222"))
    for y in range(32):
        for x in range(32):
            k = 0.86 + 0.14 * math.cos((x - 16) / 16.0 * 1.4)
            r, g, b, a = t.px[y][x]
            t.set(x, y, shade((r, g, b), k))
    return t


def tx_stone_grey(seed):
    """Senate Chamber desk tops (ru_os_chamber): light grey stone-look laminate, mottled with darker flecks."""
    t = Tex(32, 32, hexc("#A4A4A2"), seed)
    t.noise(6)
    for _ in range(28):
        x, y = t.r.randrange(32), t.r.randrange(32)
        c = t.r.choice([hexc("#868684"), hexc("#BEBEBA"), hexc("#7A7C7E")])
        t.set(x, y, c)
        t.set(x + 1, y, c)
    return t


def tx_wainscot(seed):
    """White raised-panel wainscot under the chair rail (ru_os_g310_g320): one 1.0 m panel per tile, mapped with
    explicit u (repeats along the wall)."""
    t = Tex(32, 32, hexc("#ECEBE6"), seed)
    hi, lo, field = hexc("#FAFAF8"), hexc("#C4C2BC"), hexc("#E6E4DE")
    t.rect(4, 5, 27, 26, field)
    for x in range(4, 28):
        t.set(x, 5, lo)
        t.set(x, 26, hi)
    for y in range(5, 27):
        t.set(4, y, lo)
        t.set(27, y, hi)
    for x in range(6, 26):
        t.set(x, 7, hi)
        t.set(x, 24, lo)
    for y in range(7, 25):
        t.set(6, y, hi)
        t.set(25, y, lo)
    t.rect(0, 0, 31, 0, hexc("#D8D6D0"))
    t.noise(1)
    return t


def tx_canvas(seed):
    """fix round 5 (fidelity-4; ru_os_2355_2365): four colourful gallery-wrapped landscape canvases, one per 32 x 16
    cell (2 x 2; a panel maps one cell over ~1.2 x 0.8 m): a sky / field split, soft colour blocks and a sun / tree
    blob in each. No frame or mat line (the wall edge is the canvas edge: no 1-texel high-contrast line)."""
    t = Tex(64, 32, hexc("#C89A4A"), seed)
    pal = [("#F2C23A", "#2E7AC8", "#E0582A", "#3A9A4A"),     # yellow sky, blue water, red sun, green shore
           ("#5AB4D8", "#E8A030", "#C83A3A", "#2A5AA8"),     # pale-blue sky, orange field, red roofs, blue hills
           ("#E86A3A", "#F4D04A", "#3A6AC0", "#6AB04A"),     # sunset orange, yellow band, blue, green
           ("#3A9AB0", "#8AC04A", "#F2E06A", "#B03A6A")]     # teal sky, lime hills, yellow sun, magenta flowers
    for k, (sky, field, sun, acc) in enumerate(pal):
        x0, y0 = (k % 2) * 32, (k // 2) * 16
        hz = y0 + 6 + (k % 3)
        for y in range(y0, y0 + 16):
            for x in range(x0, x0 + 32):
                band = mix(hexc(sky), hexc(field), 0.0 if y < hz else 1.0)
                t.set(x, y, shade(band, 1.0 + 0.06 * (((x + 2 * y + k) % 5) - 2) / 2))
        # soft colour blocks across the field (2-4 texels: no single-texel lines)
        for j in range(5):
            bx = x0 + 2 + t.r.randrange(24)
            by = hz + 1 + t.r.randrange(max(1, y0 + 13 - hz))
            t.rect(bx, by, min(x0 + 31, bx + 3 + t.r.randrange(4)), min(y0 + 15, by + 1 + t.r.randrange(2)),
                   mix(hexc(acc), hexc(field), 0.25 * (j % 3)))
        t.disc(x0 + 8 + 14 * (k % 2), y0 + 3 + (k % 2), 2, hexc(sun))
        t.rect(x0 + 20 - 10 * (k % 2), hz - 3, x0 + 23 - 10 * (k % 2), hz + 2, mix(hexc(acc), hexc("#203020"), 0.4))
    t.noise(3)
    return t


def tx_seatrow_black(seed):
    """fix round 5 (fidelity-4, improvement 6): the seat strip of a row of black stacking chairs, 4 seats per 64 px
    (0.5 m = 16 px each): a black padded seat with a soft lighter front roll, and a 2-texel (6 cm) blue-grey gap
    between seats (the carpet showing through), so the row reads as separate chairs, not one long black bench."""
    t = Tex(64, 32, hexc("#1E1E22"), seed)
    for k in range(4):
        x0 = k * 16
        t.rect(x0 + 1, 22, x0 + 13, 31, hexc("#2A2A30"))
        t.rect(x0 + 14, 0, x0 + 15, 31, hexc("#46526E"))
    t.noise(2)
    return t


def tx_prints(seed):
    """Eight small framed prints (2 rows x 4, 16 px each: dark frame, white mat, an image) for the row of art on
    the meeting rooms' long white walls (ru_os_g310_g320, ru_os_g330)."""
    t = Tex(64, 32, hexc("#F0EEE8"), seed)
    pal = [("#5A86B8", "#3A6A3A"), ("#C8A060", "#7A4A2A"), ("#2A3A6A", "#E8E0C8"), ("#8AA4C0", "#F06A1E"),
           ("#6A8A4A", "#C8D8E8"), ("#B04A3A", "#F0D8A0"), ("#3A4A5A", "#B0B8C0"), ("#D8C8A0", "#4A6A8A")]
    for k, (a, b) in enumerate(pal):
        x0, y0 = (k % 4) * 16, (k // 4) * 16
        t.rect(x0, y0, x0 + 15, y0 + 15, hexc("#2A2420"))
        t.rect(x0 + 1, y0 + 1, x0 + 14, y0 + 14, hexc("#F6F4EE"))
        for y in range(y0 + 4, y0 + 12):
            for x in range(x0 + 3, x0 + 13):
                horizon = y0 + 7 + (k % 3)
                t.set(x, y, mix(hexc(a), hexc(b), 0.0 if y < horizon else 0.8))
        t.line(x0 + 3, y0 + 9, x0 + 12, y0 + 7 + (k % 2) * 3, shade(hexc(b), 0.7))
    t.noise(2)
    return t


def tx_door_elev(seed):
    """Brushed-steel elevator doors (no public photo: the house finishes): two sliding leaves meeting at a centre
    seam, fine vertical brushing, a darker sill line; once-mapped across the whole opening."""
    t = Tex(32, 64, hexc("#B4B8BC"), seed)
    for x in range(32):
        k = 1.0 + 0.05 * math.sin(x * 2.3) + t.r.uniform(-0.03, 0.03)
        for y in range(64):
            t.set(x, y, shade(hexc("#B4B8BC"), k + t.r.uniform(-0.015, 0.015)))
    t.rect(15, 0, 16, 63, hexc("#5A5E62"))
    t.frame(hexc("#7A7E82"), 0, 0, 31, 63)
    t.rect(1, 61, 30, 62, hexc("#4A4E52"))
    return t


def tx_door_meeting(seed):
    """L2 / L3 meeting room door (fidelity-4 round 2; ru_os_2315_2330, ru_os_2345_2350): walnut leaf, a narrow
    vertical vision lite (dark glass, steel bead) on the latch side, a steel lever."""
    t = Tex(32, 64, hexc("#5E3C24"), seed)
    for x in range(32):
        k = 1.0 + 0.08 * math.sin(x * 1.3) + t.r.uniform(-0.04, 0.04)
        for y in range(64):
            t.set(x, y, shade(hexc("#5E3C24"), k))
    t.rect(20, 8, 24, 36, hexc("#2A3640"))
    for y in range(9, 36):
        if (y // 3) % 3 == 0:
            t.set(21, y, hexc("#5A6A78"))
    t.frame(hexc("#9A9C9E"), 19, 7, 25, 37)
    t.rect(3, 33, 9, 34, hexc("#C8CACC"))
    t.rect(3, 32, 4, 35, hexc("#A8AAAC"))
    t.frame(hexc("#3A2616"), 0, 0, 31, 63)
    return t


def tx_drape_gold(seed):
    """Suite drapes (ru_hotel_suite): gold / tan stripes of varied width with soft fold shading."""
    t = Tex(32, 32, hexc("#B8925E"), seed)
    cols = [hexc("#C8A470"), hexc("#A07A4A"), hexc("#D4B484"), hexc("#8E6A40")]
    x = 0
    while x < 32:
        w = t.r.choice((2, 3, 4, 5))
        c = t.r.choice(cols)
        for xx in range(x, min(32, x + w)):
            k = 0.9 + 0.12 * math.sin((xx % 8) / 8.0 * 2 * math.pi)
            for y in range(32):
                t.set(xx, y, shade(c, k))
        x += w
    t.noise(3)
    return t


def tx_valance_navy(seed):
    """Navy valance (ru_hotel_suite): small lighter diamond pattern on navy."""
    t = Tex(32, 32, hexc("#26305C"), seed)
    for y in range(32):
        for x in range(32):
            d = abs((x % 8) - 4) + abs((y % 8) - 4)
            if d == 3:
                t.set(x, y, hexc("#4A5A8E"))
            elif d == 0:
                t.set(x, y, hexc("#8A92B8"))
    t.noise(2)
    return t


def tx_print_suite(seed):
    """The suite's two framed prints (ru_hotel_suite), mapped by halves: left = palm trees against a blue sky,
    right = an aqua / lime abstract; 2 px dark frame + 1 px white mat."""
    t = Tex(64, 32, hexc("#2A2420"), seed)
    for y in range(2, 30):
        for x in range(2, 30):
            k = y / 30.0
            t.set(x, y, mix(hexc("#5AA8E0"), hexc("#D8ECF4"), k * 0.8))
        for x in range(34, 62):
            u = (x - 34) / 28.0
            t.set(x, y, mix(hexc("#2E9A8E"), hexc("#B8E05A"), 0.5 + 0.5 * math.sin(u * 5.0 + y * 0.25)))
    t.rect(2, 26, 29, 29, hexc("#D8C8A0"))
    for tx_, top in ((8, 6), (17, 9), (24, 5)):
        for y in range(top, 27):
            t.set(tx_ + (1 if y < (top + 27) // 2 else 0), y, hexc("#5A4630"))
        for k in range(-5, 6):
            t.set(tx_ + k, top + abs(k) // 2, hexc("#2E7A3A"))
            t.set(tx_ + k, top + abs(k) // 2 + 1, hexc("#3E9448"))
    for x in range(36, 60, 3):
        t.line(x, 4 + (x % 5), x + 4, 27 - (x % 7), hexc("#E8F4C8"))
    t.frame(hexc("#F0EEE8"), 1, 1, 30, 30)
    t.frame(hexc("#F0EEE8"), 33, 1, 62, 30)
    t.noise(2)
    return t


def tx_door_hotel(seed):
    """Hotel guest-room door (no public photo: the house cherry): a cherry leaf with a brass room-number plate at
    eye height and a card-lock lever, in a dark frame."""
    t = Tex(32, 64, hexc("#7A4A2C"), seed)
    for x in range(32):
        k = 1.0 + 0.07 * math.sin(x * 1.1) + t.r.uniform(-0.03, 0.03)
        for y in range(64):
            t.set(x, y, shade(hexc("#7A4A2C"), k))
    t.rect(10, 14, 21, 19, hexc("#C8A65A"))                   # brass number plate
    for x0 in (12, 15, 18):                                    # "5 x x" numerals (dark ticks)
        t.rect(x0, 15, x0 + 1, 18, hexc("#3A2A14"))
    t.rect(4, 32, 9, 33, hexc("#C8CACC"))                      # lever
    t.rect(4, 28, 6, 31, hexc("#2A2A2C"))                      # card lock
    t.frame(hexc("#3E2616"), 0, 0, 31, 63)
    return t


def tx_call_button(seed):
    """Elevator call-button plate: brushed steel with an up and a down button (lit rings)."""
    t = Tex(16, 32, hexc("#B4B8BC"), seed)
    t.noise(3)
    t.frame(hexc("#7A7E82"), 0, 0, 15, 31)
    for y0 in (9, 18):
        t.rect(5, y0, 10, y0 + 4, hexc("#E8EAEC"))
        t.frame(hexc("#F0D070"), 5, y0, 10, y0 + 4)
    return t


def tx_stone_clad(seed):
    """Arredondo Cafe column cladding (ru_os_arredondo_cafe): warm grey-beige stone in stacked courses."""
    t = Tex(32, 32, hexc("#B8AE9C"), seed)
    t.noise(5)
    for row in range(4):
        k = 1.0 + t.r.uniform(-0.07, 0.07)
        off = t.r.randrange(32)
        for y in range(row * 8, row * 8 + 8):
            for x in range(32):
                c = shade(t.get(x, y), k)
                if y % 8 == 7 or (x + off) % 16 == 0:
                    c = shade(c, 0.8)
                t.set(x, y, c)
    return t


def tx_shade(seed):
    """Roller shade (ru_os_arredondo_cafe): light grey screen fabric, faint weave, a dark hem bar at the bottom."""
    t = Tex(32, 32, hexc("#C8C6C0"), seed)
    t.noise(3)
    for y in range(32):
        for x in range(32):
            if (x + y) % 4 == 0:
                t.set(x, y, shade(t.get(x, y), 0.95))
    t.rect(0, 29, 31, 31, hexc("#4A4A4C"))
    return t


# ---- fix round 2, fidelity-2 (food court) recipes
def tx_glow_letters(text, hx, core_hx, seed, max_w=None, h=16):
    """Letters only on a transparent 64 x h card (cutout): FONT5 glyphs stretched to fill the height, so a quad
    mounted on a fascia reads as individual channel letters, not a boxed panel (ru_food_court_sonic_2025).
    core_hx: a lighter upper half (neon glow)."""
    t = Tex(64, h, (0, 0, 0), seed, alpha=0)
    n = len(text)
    gw = max(4, min(max_w or 99, (t.w + 1) // n - 1))
    gh = h - 2
    total = n * gw + (n - 1)
    x = (t.w - total) // 2
    col, core = hexc(hx), hexc(core_hx) if core_hx else None
    for ch in text:
        g = FONT5.get(ch)
        if g is not None:
            for py in range(gh):
                for px in range(gw):
                    if g[py * 7 // gh][px * 5 // gw] == "#":
                        c = col
                        if core is not None and py < gh * 0.45:
                            c = mix(col, core, 0.35)
                        t.set(x + px, 1 + py, c)
                        if gw >= 7 and px + 1 < gw:        # bold: 2-texel strokes (no 1-texel shimmer)
                            t.set(x + px + 1, 1 + py, c)
        x += gw + 1
    return t


def tx_menu_screen(seed):
    """One landscape digital menu screen (ru_food_court_sonic_2025: four of them over the counter)."""
    t = Tex(32, 16, hexc("#101216"), seed)
    t.rect(1, 1, 30, 14, hexc("#1E50B0"))
    t.rect(2, 2, 29, 3, hexc("#E83A2A"))
    for k, c in enumerate(("#D8902A", "#E8C040", "#C8402A")):
        t.rect(3 + k * 9, 5, 9 + k * 9, 9, hexc(c))
        t.rect(4 + k * 9, 6, 8 + k * 9, 7, shade(hexc(c), 1.15))
        t.rect(3 + k * 9, 11, 8 + k * 9, 11, hexc("#E8F0FF"))
        t.rect(9 + k * 9 - 1, 12, 9 + k * 9, 12, hexc("#F0D040"))
    return t


def tx_neon_swirl_tall(seed):
    """The tall red / pink and blue tube neon left of the burger opening (ru_food_court_sonic_2025). fix round 4
    (fidelity-2): a CUTOUT straight on the navy wall (was a 32 x 64 navy card with two blue edge lines that read
    as a dim framed poster): thick tubes (a ~3-texel coloured halo round a pale hot core), a big red / pink swirl
    over a blue S-tube tail, no background, no frame."""
    t = Tex(32, 64, (0, 0, 0), seed, alpha=0)
    # fix round 5 (fidelity-2): the layout was upside down (a ~0.8 m swirl at the top on a thin blue stem read as a
    # lollipop). The photo's big red / pink loop sits LOW (counter to head height, ~1.2 m across: texel row 0 is the
    # top, the decal spans 0.95-3.45 m, so rows 34-63 are ~1.0-2.1 m) inside a broken blue ring, and the blue
    # strokes sweep up above it (a tall S-tube plus a short hook), with sky-blue cores.
    cy = 48.5
    red = [(16 + (3.0 + 8.5 * i / 240.0) * math.cos(i / 240.0 * math.pi * 3.6 + 2.0),
            cy + (3.0 + 8.5 * i / 240.0) * math.sin(i / 240.0 * math.pi * 3.6 + 2.0)) for i in range(241)]
    blue = [(15 + 8.5 * math.sin((32.5 - y) / 27.0 * math.pi * 1.25), y) for y in [5.0 + k * 0.25 for k in range(111)]]
    blue += [(24.0 + 4.0 * math.cos(a_ * math.pi / 30), 10.5 + 4.0 * math.sin(a_ * math.pi / 30))
             for a_ in range(25, 61)]
    ring = [(16 + 14.0 * math.cos(a_ * math.pi / 60), cy + 14.0 * math.sin(a_ * math.pi / 60)) for a_ in range(0, 121)
            if not 75 < a_ < 100]
    for pts, halo in ((red, "#E01E3A"), (blue + ring, "#2A62E8")):
        for x, y in pts:
            t.disc(x, y, 1.7, hexc(halo))
    for pts, core in ((red, "#FFB4C0"), (blue + ring, "#B4E0FF")):
        for x, y in pts:
            t.disc(x, y, 0.75, hexc(core))
    return t


def tx_maple_panel(seed):
    """Smooth vertical-grain maple veneer panels (ru_starbucks_2017 side walls + counter): long vertical grain,
    one soft panel joint per tile."""
    base = hexc("#D2A26A")
    t = Tex(32, 64, base, seed)
    ks = [1.0 + t.r.uniform(-0.05, 0.05) for _ in range(32)]
    for x in range(32):
        k = (ks[x] + ks[(x + 1) % 32] + ks[x - 1]) / 3.0
        for y in range(64):
            c = shade(base, k * (1.0 + 0.025 * math.sin(y * 0.35 + x * 0.9)))
            if x == 0:
                c = shade(c, 0.9)
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_troffer(seed):
    """2 x 4 lay-in troffer (ru_food_court_counter_2023: rows of them over the seating hall)."""
    t = Tex(16, 32, hexc("#DCDEE2"), seed)
    t.rect(2, 2, 13, 29, hexc("#FFFFFF"))
    for y in range(4, 29, 4):
        t.rect(3, y, 12, y, hexc("#E6EAF0"))
    t.rect(7, 2, 8, 29, hexc("#E6EAF0"))
    return t


def tx_pastry(seed):
    """Lit pastry case shelves (ru_starbucks_2017 / ru_old_starbucks_commons): two rows of baked goods."""
    t = Tex(32, 16, hexc("#F4E6C8"), seed)
    for y0 in (6, 14):
        t.rect(0, y0, 31, y0 + 1, hexc("#5A4A3A"))
        for k in range(5):
            c = t.r.choice(("#B8783A", "#D8A860", "#8A5230", "#E8C890", "#C86A7A"))
            t.rect(1 + k * 6, y0 - 3, 5 + k * 6, y0 - 1, hexc(c))
            t.set(2 + k * 6, y0 - 4, shade(hexc(c), 1.1))
            t.set(4 + k * 6, y0 - 4, shade(hexc(c), 1.1))
    return t


TEXTURES = {
    "int_ru_terrazzo": tx_terrazzo,
    "int_ru_carpet_atrium": tx_carpet_atrium,
    "int_ru_gator_track": tx_gator_track,
    "int_ru_lane": tx_lane,
    "int_ru_lane_arrows": tx_lane_arrows,
    "int_ru_plank": tx_plank,
    "int_ru_carpet_billiards": tx_carpet_billiards,
    "int_ru_fc_checker": tx_fc_checker,
    "int_ru_fc_tile": tx_fc_tile,
    "int_ru_carpet_meeting": tx_carpet_meeting,
    "int_ru_carpet_ballroom": tx_carpet_ballroom,
    "int_ru_maple": tx_maple,
    "int_ru_dance": lambda s: _flat("#2C2C30", s, 3),
    "int_ru_carpet_olive": lambda s: tx_carpet_pattern("#5C5838", "#6E6A44", s, "diamond"),
    "int_ru_carpet_grey": lambda s: tx_carpet_pattern("#9C9A96", "#B4B2AE", s, "loop"),
    "int_ru_carpet_hotel": lambda s: tx_carpet_pattern("#5C6688", "#8A7A5A", s, "diamond"),
    # iteration 9 (fidelity-4 improvement 6b/6d; ru_os_auditorium_1..3): a darker, less saturated slate (the room
    # measured about twice as bright as the photos; was #46567E / #5E6E96)
    "int_ru_carpet_aud": lambda s: tx_carpet_pattern("#434A5C", "#555D70", s, "tri"),
    # fix round 5 (fidelity-4, improvement 9d; ru_the_gallery): dark polished concrete (the mid-grey read matte)
    # iteration 9 (fidelity-4 improvement 9; ru_os_gallery): warm dark-brown polished concrete (was cool #424448)
    "int_ru_concrete_dark": lambda s: _flat("#5E4E44", s, 4),
    "int_ru_paving": tx_paving,
    "int_ru_wall": lambda s: _flat("#EDEBE6", s, 2),
    # iteration 9 (fidelity-4 improvement 3; ru_os_matthews_1/3/4): light warm grey (the #A6B2C4 read periwinkle)
    "int_ru_wall_greyblue": lambda s: _flat("#CFCCC6", s, 2),
    "int_ru_wall_royal": lambda s: _flat("#1E3CA0", s, 3),
    "int_ru_wall_navy": lambda s: _flat("#22283A", s, 3),
    "int_ru_wall_grey": lambda s: _flat("#B2B4B6", s, 2),
    "int_ru_wall_slate": lambda s: _flat("#80848A", s, 2),
    "int_ru_wall_cream": lambda s: _flat("#E8E0CC", s, 2),
    "int_ru_hex": tx_hex,
    "int_ru_hex_neon": tx_hex_neon,
    "int_ru_gator_skin": tx_gator_skin,
    "int_ru_acoustic": tx_acoustic,
    "int_ru_cherry": lambda s: tx_wood("#8C4026", s, stripe=8, gap_k=0.8),
    "int_ru_chevron": tx_chevron,
    "int_ru_cedar": lambda s: tx_cedar_soft(s),                         # fix round 2 design: soft 2-texel slats
    "int_ru_brick": tx_brick,
    "int_ru_wood_panel": lambda s: tx_wood("#B07A44", s, stripe=8, gap_k=0.7),
    "int_ru_slat_dark": lambda s: tx_wood("#4C3628", s, stripe=4, gap_k=0.5, vertical=False),
    "int_ru_mirror": tx_mirror,
    "int_ru_paint_lime": lambda s: _flat("#B6D034", s, 2),
    "int_ru_paint_sky": lambda s: _flat("#90CADC", s, 2),
    "int_ru_counter_front": tx_counter_front,
    "int_ru_soffit": lambda s: _flat("#ECE6D6", s, 2),
    "int_ru_white": lambda s: _flat("#F4F4F2", s, 1),
    "int_ru_black": lambda s: _flat("#1E1F22", s, 3),
    "int_ru_steel": lambda s: tx_wood("#B4B8BC", s, stripe=32, gap_k=1.0),
    "int_ru_orange": lambda s: _flat("#F0561E", s, 3),
    "int_ru_uf_blue": lambda s: _flat("#1E3C9E", s, 3),
    "int_ru_red": lambda s: _flat("#C42A26", s, 3),
    "int_ru_coffer": tx_coffer,
    "int_ru_led": tx_led,
    "int_ru_tile_ceiling": tx_ceiling,
    "int_ru_felt": tx_felt,
    "int_ru_leather_navy": lambda s: tx_leather("#28366E", s),
    "int_ru_leather_grey": lambda s: tx_leather("#8E8C8A", s),
    "int_ru_fabric_taupe": lambda s: tx_fabric("#9C8C6E", s),
    "int_ru_fabric_navy": lambda s: tx_fabric("#232E54", s),
    "int_ru_fabric_char": lambda s: tx_fabric("#3A3C40", s),
    "int_ru_gator_green": tx_gator_green,
    "int_ru_bed": lambda s: _flat("#F0F0EC", s, 2),
    "int_ru_drape": lambda s: tx_wood("#1C1C22", s, stripe=3, gap_k=0.7),
    "int_ru_tablecloth": lambda s: tx_fabric("#1C2A5E", s),
    "int_ru_glass": lambda s: _flat("#A8CCE0", s, 2),
    "int_ru_glass_blue": lambda s: _flat("#5A8CB8", s, 3),
    "int_ru_picket": tx_picket,
    "int_ru_row_navy": lambda s: tx_row("navy", s),
    "int_ru_row_black": lambda s: tx_row("black", s),
    "int_ru_row_aud": lambda s: tx_row("aud", s),
    "int_ru_row_wood": lambda s: tx_row("wood", s),
    "int_ru_door": lambda s: tx_door("honey", s),
    "int_ru_door_walnut": lambda s: tx_door("walnut", s),
    "int_ru_door_glass": lambda s: tx_door("glass", s),
    "int_ru_door_steel": lambda s: tx_door("steel", s),
    "int_ru_video_wall": tx_video_wall,
    "int_ru_masking": tx_masking,
    "int_ru_score_tv": tx_score_tv,
    "int_ru_game_screen": tx_game_screen,
    "int_ru_arcade": tx_arcade,
    "int_ru_proj_screen": tx_proj_screen,
    "int_ru_sign_gameroom": tx_sign_gameroom,
    "int_ru_sign_esports": tx_sign_esports,
    "int_ru_sign_union": tx_sign_union,
    "int_ru_sign_wayfind": lambda s: tx_sign([("GAME ROOM >", 4, 1, "#FFFFFF", FONT3),
                                              ("< FOOD COURT", 12, 1, "#FFFFFF", FONT3),
                                              ("< ATRIUM", 20, 1, "#FFFFFF", FONT3),
                                              ("ELEVATORS >", 26, 1, "#F0A060", FONT3)], "#1E3C9E", s, "#F06A1E"),
    "int_ru_sign_rooms": lambda s: tx_sign([("MEETING", 3, 1, "#1E3C9E", FONT5), ("ROOMS", 12, 1, "#1E3C9E", FONT5),
                                            ("2315-2365 >", 23, 1, "#3A3A3A", FONT3)], "#E8E8E4", s, "#8C8E90"),
    "int_ru_sign_ballroom": lambda s: tx_sign([("GRAND", 5, 1, "#E8E8E8", FONT5), ("BALLROOM", 16, 1, "#E8E8E8", FONT5)],
                                              "#2A2E3A", s, "#8A7A5A"),
    "int_ru_sign_hotel": lambda s: tx_sign([("REITZ UNION", 6, 1, "#FFFFFF", FONT3), ("HOTEL", 15, 1, "#F06A1E", FONT5)],
                                           "#1E3C9E", s, "#F06A1E"),
    "int_ru_sign_info": lambda s: tx_sign([("INFORMATION", 7, 1, "#FFFFFF", FONT3), ("DESK", 16, 1, "#F06A1E", FONT5)],
                                          "#1E3C9E", s),
    "int_ru_sign_foodcourt": lambda s: tx_sign([("FOOD", 4, 2, "#FFFFFF", FONT5), ("COURT", 21, 1, "#1E3C9E", FONT5)],
                                               "#F05A1E", s),
    "int_ru_floor_atlas": tx_floor_atlas,
    "int_ru_vend_burger": lambda s: tx_vendor("BURGERS", "#1C2A5E", "#F04A3A", "#F0C030", s, "DRIVE-IN"),
    "int_ru_vend_pizza": lambda s: tx_vendor("PIZZA", "#2C6A3A", "#F4F0E0", "#D8302A", s),
    "int_ru_vend_wok": lambda s: tx_vendor("WOK", "#B02420", "#F8E8C0", "#2A2A2A", s, "EXPRESS"),
    "int_ru_vend_halal": lambda s: tx_vendor("HALAL", "#1E1E22", "#F0A030", "#F0A030", s, "GRILL"),
    "int_ru_vend_coffee": lambda s: tx_vendor("COFFEE", "#1E5A3E", "#F4F0E4", "#C8A060", s, "BAR"),
    "int_ru_vend_smoothie": lambda s: tx_vendor("SHAKES", "#6A3A8E", "#C8F040", "#C8F040", s, "SMOOTHIES"),
    "int_ru_vend_mac": lambda s: tx_vendor("MAC", "#E8B020", "#1E2A5E", "#1E2A5E", s, "AND CHEESE"),
    "int_ru_vend_taco": lambda s: tx_vendor("TACOS", "#1E8A86", "#F8F0D8", "#F06A3A", s),
    "int_ru_menu": tx_menu,
    "int_ru_art": tx_art,
    "int_ru_photos": tx_photos,
    "int_ru_mural_acc": tx_mural_acc,
    "int_ru_flags": tx_flags,
    "int_ru_exit": tx_exit,
    "int_ru_dais": tx_dais,
    "int_ru_window_view": tx_window_view,
    "int_ru_books": tx_books,
    "int_ru_tv_hotel": tx_tv_hotel,
    "int_ru_pins": tx_pins,
    "int_ru_banner_welcome": tx_banner_welcome,
    "int_ru_counter_navy": tx_counter_navy,
    "int_ru_counter_red": tx_counter_red,
    "int_ru_mosaic": tx_mosaic,
    "int_ru_chalkboard": tx_chalkboard,
    "int_ru_neon_swirl": tx_neon_swirl,
    "int_ru_menu_blue": tx_menu_blue,
    "int_ru_carpet_chamber": lambda s: tx_carpet_pattern("#1E2648", "#2A3462", s, "tri"),
    "int_ru_stone_grey": tx_stone_grey,
    "int_ru_wainscot": tx_wainscot,
    "int_ru_prints": tx_prints,
    "int_ru_wood_lvt": lambda s: tx_wood("#6E5440", s, stripe=4, gap_k=0.72, vertical=False),
    # iteration 9 (fidelity-4 improvement 10; ru_os_2315..2360): muted grey-lavender (#7F90AC was too saturated)
    "int_ru_wall_slateblue": lambda s: _flat("#8E95A8", s, 2),      # fidelity-4 r2 (was #6E7D96)
    "int_ru_door_elev": tx_door_elev,
    "int_ru_door_hotel": tx_door_hotel,
    "int_ru_call_button": tx_call_button,
    "int_ru_stone_clad": tx_stone_clad,
    "int_ru_shade": tx_shade,
    "int_ru_wayfind_LL": lambda s: tx_wayfind("LL", "N", s),
    "int_ru_wayfind_LL_s": lambda s: tx_wayfind("LL", "S", s),
    "int_ru_wayfind_G": lambda s: tx_wayfind("G", "N", s),
    "int_ru_wayfind_G_s": lambda s: tx_wayfind("G", "S", s),
    "int_ru_wayfind_L1": lambda s: tx_wayfind("L1", "N", s),
    "int_ru_wayfind_L1_s": lambda s: tx_wayfind("L1", "S", s),
    "int_ru_wayfind_L2": lambda s: tx_wayfind("L2", "N", s),
    "int_ru_wayfind_L2_s": lambda s: tx_wayfind("L2", "S", s),
    "int_ru_wayfind_L3": lambda s: tx_wayfind("L3", "N", s),
    "int_ru_wayfind_L3_s": lambda s: tx_wayfind("L3", "S", s),
    "int_ru_wayfind_L4": lambda s: tx_wayfind("L4", "N", s),
    "int_ru_wayfind_L4_s": lambda s: tx_wayfind("L4", "S", s),
    "int_ru_wayfind_L5": lambda s: tx_wayfind("L5", "N", s),
    "int_ru_wayfind_L6": lambda s: tx_wayfind("L6", "N", s),
    "int_ru_fabric_plum": lambda s: tx_fabric("#5A383E", s),
    "int_ru_sign_burger_glow": lambda s: tx_glow_letters("BURGERS", "#FF6A3A", "#FFC0A0", s),
    "int_ru_menu_screen": tx_menu_screen,
    "int_ru_neon_swirl_tall": tx_neon_swirl_tall,
    "int_ru_maple_panel": tx_maple_panel,
    "int_ru_leather_orange": lambda s: tx_leather("#D0642A", s),
    "int_ru_troffer": tx_troffer,
    "int_ru_pastry": tx_pastry,
    "int_ru_vletters_wok": lambda s: tx_glow_letters("WOK", "#D02A20", None, s, max_w=9),
    "int_ru_vletters_halal": lambda s: tx_glow_letters("HALAL", "#F0A030", None, s, max_w=9),
    "int_ru_vletters_mac": lambda s: tx_glow_letters("MAC&CHEESE", "#1E3C9E", None, s),
    "int_ru_vletters_shakes": lambda s: tx_glow_letters("SHAKES", "#B070E0", None, s),
    "int_ru_vletters_tacos": lambda s: tx_glow_letters("TACOS", "#2AB0A8", None, s, max_w=9),
    "int_ru_vletters_coffee": lambda s: tx_glow_letters("COFFEE", "#1E7A4E", None, s),
    "int_ru_sign_esports_b": lambda s: tx_sign_esports_part(s, 1),     # fidelity-3 round 2
    "int_ru_wall_charcoal": lambda s: _flat("#3A3C42", s, 2),           # game room window dado
    "int_ru_aed": tx_aed,                                               # north-door corridor AED cabinet
    "int_ru_leather_tan": lambda s: _flat("#D8A25A", s, 3),             # fidelity-4 r2: suite loveseats
    "int_ru_seat_tan": lambda s: tx_fabric("#C07238", s),               # ... Arredondo chair seats
    "int_ru_mahogany": lambda s: tx_wood("#6A2C1E", s, stripe=4, gap_k=0.72, vertical=False),   # ... Rion beams
    "int_ru_drape_gold": tx_drape_gold,                                 # ... suite drapes
    "int_ru_valance_navy": tx_valance_navy,                             # ... suite valance
    "int_ru_print_suite": tx_print_suite,                               # ... suite prints (palms | aqua)
    "int_ru_door_meeting": tx_door_meeting,                             # ... L2 / L3 meeting room doors
    "int_ru_glass_clear": lambda s: tx_glass_sheen(s),                  # fix round 2 design: vestibule glass (r4 sheen)
    "int_ru_room_plaque": lambda s: tx_room_plaque(s),                  # ... room-number plaques by the doors
    "int_ru_bulletin": lambda s: tx_bulletin(s),                        # ... corridor bulletin boards
    "int_ru_sign_bookstore": lambda s: tx_sign_bookstore(s),            # ... the Bookstore link sign (L1 south hall)
    "int_ru_wall_paleblue": lambda s: _flat("#BCC4D0", s, 2),           # fix round 4: G315 accent (ru_os_g315)
    "int_ru_wall_billiards": lambda s: _flat("#2E3036", s, 3),     # user-photo pass (user_04): neutral black-navy          # ... billiards hall walls (ru_gr_billiards_room)
    "int_ru_glass_smoke": lambda s: _flat("#1C2234", s, 1),             # ... Esports storefront glass (ru_es_oelrich_8951)
    "int_ru_metal_panel": lambda s: tx_metal_panel(s),                  # ... atrium east bulkhead (ru_atrium_enr_vertical)
    "int_ru_orange_uf": lambda s: _flat("#FA8A1E", s, 3),               # fix round 4 fidelity-1: UF letters
    "int_ru_steel_bright": lambda s: _flat("#E6EAEE", s, 2),            # ... gator-track stainless strip
    "int_ru_wood_tan": lambda s: tx_wood("#C9A06A", s, stripe=16, gap_k=0.92),  # ... lounge tables / chair arms
    "int_ru_fabric_orange": lambda s: tx_fabric("#EE6A22", s),          # ... lounge orange club chairs
    # last: texture seeds go by position in this dict (append only)
    # fix round 4 (fidelity-4 pass): appended last so the seeds of every earlier recipe stay the same
    "int_ru_row_rion": lambda s: tx_row("rion", s),
    # iteration 9 (fidelity-4 improvement 6b; ru_os_auditorium_1..3 median ~16-29 vs render ~48-54): darker again
    "int_ru_wall_aud": lambda s: _flat("#5E6064", s, 3),
    "int_ru_maple_light": tx_maple_light,
    # fix round 5 (fidelity-1): appended last (every earlier recipe keeps its seed)
    "int_ru_cafe_bay": tx_cafe_bay,                                     # Orange & Brew glazed bays
    "int_ru_sign_ob": tx_sign_ob,                                       # ... and its fascia sign
    "int_ru_office_bay": tx_office_bay,                                 # ... void east-end office fronts (L2 / L3)
    # fix round 5 (fidelity-3): appended last (every earlier recipe keeps its seed)
    "int_ru_espresso": lambda s: tx_wood("#3A1E16", s, stripe=8, gap_k=0.82),   # billiards tables
    "int_ru_sign_gameroom_uf": lambda s: tx_sign_gameroom_uf(s),        # billiards-wall graphic
    "int_ru_wall_royal_wash": lambda s: tx_wall_royal_wash(s),          # G325 royal bay + wall-washer scallops
    # fix round 5 (fidelity-4): appended last (every earlier recipe keeps its seed)
    "int_ru_canvas": tx_canvas,                                         # 2355 / 2365 landscape canvases
    "int_ru_seatrow_black": tx_seatrow_black,                           # meeting-room chair-row seats
    "int_ru_glass_faint": lambda s: _flat("#E4ECEF", s, 1),             # fix round 5 design: north door leaves / bank
    "int_ru_student_art": lambda s: tx_student_art(s),                  # ... ACC student artwork band
    "int_ru_clay": lambda s: _flat("#B0603A", s, 4),                    # ... terracotta clay on the pottery wheels
    # fix iteration 6 (appended LAST: the recipe seed is 1000 + 7 * its index, earlier textures keep theirs)
    "int_ru_fabric_mustard": lambda s: tx_fabric("#D8A030", s),         # the ACC's mustard-yellow chairs
    # iteration 7 (appended LAST: earlier recipes keep their seeds)
    "int_ru_glass_door": lambda s: _flat("#C6DCE4", s, 1),              # the outer north door leaves (tinted)
    "int_ru_drum_panel": lambda s: tx_drum_panel(s),                    # the atrium's polished-silver east drum
    # iteration 9 (appended LAST: earlier recipes keep their seeds): guest-room taupe carpet, a soft low-contrast
    # diamond (the line only ~8 % lighter than the base: no shimmer at 3.75 cm texels)
    "int_ru_carpet_hotelroom": lambda s: tx_carpet_pattern("#A89A92", "#B9ACA3", s, "diamond"),
    "int_ru_art_gal_a": lambda s: tx_art_gallery("a", s),               # the Gallery: large blue canvas
    "int_ru_art_gal_b": lambda s: tx_art_gallery("b", s),               # ... tall multicolour + photo grid + landscapes
    "int_ru_wall_warm": lambda s: _flat("#EAD8BC", s, 2),               # 3305 / 3310 warm cream walls
    # ==== user-photo pass (atrium core; appended LAST: earlier recipes keep their seeds)
    "int_ru_tower_glass": lambda s: tx_tower_glass(s),                  # Gators tower: black-glass shaft bays
    "int_ru_tower_car": lambda s: tx_tower_car(s),                      # ... its two lit glass cars
    "int_ru_sign_gators": lambda s: tx_sign_gators(s),                  # ... the orange 'Gators' script
    "int_ru_band_blue": lambda s: tx_band_word("blue", s),              # clerestory BLUE band graphics (C09)
    "int_ru_word_blue": lambda s: tx_glow_letters("BLUE", "#2A5CE0", "#8FB0FF", s),
    "int_ru_band_orange": lambda s: tx_band_word("orange", s),          # clerestory ORANGE band graphics (C10)
    "int_ru_word_orange": lambda s: tx_glow_letters("ORANGE", "#F05A1E", "#FFB070", s),
    "int_ru_bronze_black": lambda s: _flat("#24262A", s, 2),            # the black Swamp Boss head (B08, C01)
    "int_ru_carpet_tri": lambda s: tx_carpet_tri(s),                    # lounge triangle carpet (B08, B09)
    "int_ru_banner_welcome2": lambda s: tx_banner_welcome2(s, 0),       # WELCOME banner, left half (B09)
    "int_ru_banner_welcome3": lambda s: tx_banner_welcome2(s, 1),       # ... right half (multilingual)
    "int_ru_word_senate": lambda s: tx_word_small("SENATE CHAMBER", "#8A8D92", s),
    "int_ru_picket2": lambda s: tx_picket2(s),                          # plain grey pickets (user_02, B05)
    "int_ru_leather_char": lambda s: tx_leather("#2E3034", s),          # charcoal leather sofas (B09, C01)
    "int_ru_gator_claw": lambda s: tx_gator_claw(s),                    # three-claw gator footprints (B05)
    "int_ru_gator_skin_grey": lambda s: tx_gator_skin_grey(s),          # grey plates on white (B09)
    "int_ru_word_cabo": lambda s: tx_glow_letters("CABO", "#F57A1E", "#FFC080", s),
    "int_ru_word_mexgrill": lambda s: tx_word_small("MEXICAN GRILL", "#FFFFFF", s),
    "int_ru_snake_plant": lambda s: tx_snake_plant(s),                  # CABO snake plants (B10)
    # ==== user-photo pass (food court; appended LAST: earlier recipes keep their seeds)
    "int_ru_vletters_sbux": lambda s: tx_glow_letters("STARBUCKS", "#F0EFEA", None, s),       # user_18 frieze
    "int_ru_badge_green": lambda s: tx_badge_round("#1E6A44", "#F4F4F0", s, bars=None),       # ... round badge
    "int_ru_cafe_shelves": lambda s: tx_cafe_shelves(s),                                     # ... lit back shelves
    "int_ru_slat_walnut": lambda s: tx_slat_v("#5A3A24", s),                                 # ... slat pilasters
    "int_ru_mural_coffea": lambda s: tx_mural_coffea(s),                                     # COFFEA ARABICA (user_18)
    "int_ru_brick_rustic": lambda s: tx_brick_rustic(s),                                     # Baba's Pizza (B01)
    "int_ru_vletters_babas": lambda s: tx_letters_distressed("BABA'S PIZZA", "#F2EEE4", s),
    "int_ru_badge_black": lambda s: tx_badge_round("#141414", "#F2F2F2", s, bars="#F2F2F2"),
    "int_ru_badge_gold": lambda s: tx_badge_round("#D4A23A", "#4A2A14", s, bars="#4A2A14"),  # Halal Shack (B01, u20)
    "int_ru_vletters_halal2": lambda s: tx_letters_wide("HALAL SHACK", "#6A3E1A", s),
    "int_ru_tile_lattice": lambda s: tx_tile_lattice(s),                                     # Panda counter (user_19)
    "int_ru_vletters_panda": lambda s: tx_glow_letters("PANDA", "#FFFFFF", None, s),
    "int_ru_badge_red": lambda s: tx_badge_round("#C8202A", "#FFFFFF", s, bars=None),
    "int_ru_vletters_smart": lambda s: tx_letters_wide("SHAKE SMART", "#C8202A", s),
    "int_ru_fc_queue": lambda s: tx_speckle_floor("#4E4945", ("#857C73", "#2C2826"), s, 70),  # queue band (user_19)
    "int_ru_vinyl_grey": lambda s: tx_speckle_floor("#A8A59F", ("#B2AFA9", "#9E9B95"), s, 50),  # south hall (u20)
    "int_ru_troffer_sq": lambda s: tx_troffer_sq(s),                                         # 2 x 2 troffers
    "int_ru_vent_sq": lambda s: tx_vent_sq(s),                                               # ... return grilles
    "int_ru_sign_bk_gators": lambda s: tx_sign_bk_gators(s),                                 # Bookstore (user_20)
    "int_ru_sign_bk_store": lambda s: tx_glow_letters("BOOKSTORE", "#2F6BFF", "#A8C4FF", s),
    "int_ru_badge_gator": lambda s: tx_badge_gator(s),
    "int_ru_grille": lambda s: tx_grille(s),                                                 # rolling grilles
    "int_ru_jersey": lambda s: tx_jersey(s),                                                 # Nike window #0 / #7
    "int_ru_laminate_mauve": lambda s: tx_speckle_floor("#B98A96", ("#C29AA4", "#AE7E8A"), s, 40),  # B03 tables
    "int_ru_order_here": lambda s: tx_word_small("ORDER HERE", "#FFFFFF", s),               # B02 kiosks
    "int_ru_paint_cranberry": lambda s: _flat("#8A1C20", s, 3),                               # Panda walls (u19)
    # ==== user-photo pass, Ground floor (appended LAST: earlier recipes keep their seeds)
    "int_ru_tile_ceiling_dark": lambda s: tx_ceiling_dark(s),                               # Game Room (user_04)
    "int_ru_scale_led": lambda s: tx_scale_led(s),                                           # Esports frieze (B15)
    "int_ru_inlay_reitz": lambda s: tx_inlay_reitz(s),                                       # floor inlay (B17)
    "int_ru_granite_black": lambda s: tx_granite_black(s),                                   # hotel desk top (B17)
    "int_ru_brass": lambda s: _flat("#C8A04A", s, 3),                                        # gold pendant (B17)
    "int_ru_wayfind_G_w_a": lambda s: tx_wayfind_g_white(0),                                 # white sign (user_03)
    "int_ru_wayfind_G_w_b": lambda s: tx_wayfind_g_white(1),
    "int_ru_wayfind_G_w_c": lambda s: tx_wayfind_g_white(2),
    "int_ru_arrow_navy": lambda s: tx_arrow_navy(s),
    "int_ru_terrazzo_grey": lambda s: tx_speckle_floor("#A5A39C", ("#8E8C86", "#B8B5AE", "#7E7C78"), s, 60),
    "int_ru_terrazzo_orange": lambda s: tx_speckle_floor("#D9782F", ("#C4682A", "#E8955A", "#B05A22"), s, 60),
    "int_ru_sign_gr_transom": lambda s: tx_glow_letters("GAME ROOM", "#FFFFFF", None, s),   # B16 transom
    "int_ru_barber_pole": lambda s: tx_barber_pole(s),                                       # B12, B14
    "int_ru_sign_barber": lambda s: tx_sign_barber(s),                                       # B14
    "int_ru_photo_bw": lambda s: tx_photo_bw(s),                                             # B13 frieze
    "int_ru_dir_G": lambda s: tx_dir_g(s),                                                   # B13 directory
    "int_ru_sign_arena": lambda s: tx_glow_letters("ARENA", "#FF8A2A", "#FFC890", s),       # B19
    "int_ru_subway_green": lambda s: _flat("#0F7A35", s, 3),                                 # user_03
    "int_ru_sign_subway": lambda s: tx_sign_subway(s),                                       # user_03
    "int_ru_arcade_gamepod": lambda s: tx_arcade_gamepod(s),                                 # B15 cabinets
    "int_ru_sign_nosh": lambda s: tx_sign_nosh(s),                                           # user_03 Market
    "int_ru_sign_market": lambda s: tx_badge_market(s),                                      # ... round blade
    # ==== user-photo pass, L1-L3 corridors + Rion (appended LAST: earlier recipes keep their seeds)
    "int_ru_ccc_screen": lambda s: tx_ccc_screen(s),                                         # user_14, user_15
    "int_ru_marble": lambda s: tx_marble(s),                                                 # CCC desk (user_14)
    "int_ru_timeline": lambda s: tx_timeline(s),                                             # user_07, user_08
    "int_ru_timeline_head": lambda s: tx_timeline_head("UF STUDENT UNION HISTORY", "AND TIMELINE", s),
    "int_ru_timeline_head2": lambda s: tx_timeline_head("THROUGH THE YEARS", None, s),
    "int_ru_sign_rion": lambda s: tx_sign_rion("RION BALLROOM", s),                         # C12, C13
    "int_ru_sign_rion_east": lambda s: tx_sign_rion("RION BALLROOM EAST", s),               # C03
    "int_ru_hang_pass_a": lambda s: tx_hang("pass_up", 0),                                  # user_07
    "int_ru_hang_pass_b": lambda s: tx_hang("pass_up", 1),
    "int_ru_hang_pass_c": lambda s: tx_hang("pass_lo", 0),
    "int_ru_hang_blue_a": lambda s: tx_hang("blue_up", 0),                                  # user_11
    "int_ru_hang_blue_b": lambda s: tx_hang("blue_up", 1),
    "int_ru_hang_blue_c": lambda s: tx_hang("blue_lo", 0),
    "int_ru_hang_blue_d": lambda s: tx_hang("blue_lo", 1),
    "int_ru_oils": lambda s: tx_oils(s),                                                     # user_06, C11
    "int_ru_sign_gatorwell": lambda s: tx_glow_letters("GATORWELL", "#E8742A", None, s),    # user_10
    "int_ru_slate_floor": lambda s: tx_slate_floor(s),                                       # user_14-16
    "int_ru_partition": lambda s: tx_partition(s),                                           # C08
    "int_ru_door_meeting_honey": lambda s: tx_door_meeting_honey(s),                         # C03, C08, C12
    "int_ru_maple_pale": lambda s: _retone(tx_maple(s), (1.06, 1.21, 1.41)),                # Rion floor (C14-C16)
    "int_ru_word_wall_a": lambda s: tx_word_wall(0, s),                                      # CCC word wall (user_16)
    "int_ru_word_wall_b": lambda s: tx_word_wall(1, s),
    "int_ru_hang_meet": lambda s: tx_hang("meet", 0),                                       # C08
    "int_ru_frit": lambda s: tx_frit(s),                                                     # C04 dotted frit band
    "int_ru_rion_case": lambda s: tx_rion_case(s),                                           # C12, C13
    "int_ru_terrazzo_dark": lambda s: tx_speckle_floor("#5E6062", ("#4E5052", "#707274", "#46484A"), s, 60),  # user_06
}


# ==== user-photo pass: food court recipes (user_18-20, B01-B03). No reproduced logo art: plain names
# in the photographed colours and generic round badges.
def tx_badge_round(hx, ring_hx, seed, bars=None):
    """A round sign: a disc with a 2-texel ring, optional two short text bars (no logo art)."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    t.disc(16, 16, 15.5, hexc(ring_hx))
    t.disc(16, 16, 13.0, hexc(hx))
    if bars:
        t.rect(9, 12, 22, 13, hexc(bars))
        t.rect(7, 16, 24, 18, hexc(bars))
        t.rect(10, 21, 21, 22, hexc(bars))
    else:
        t.disc(16, 16, 7.0, hexc(ring_hx))
        t.disc(16, 16, 5.0, hexc(hx))
    return t


def tx_cafe_shelves(seed):
    """Warm-lit walnut shelving behind the coffee bar: 3 shelves of white cups, kraft bags and tins."""
    t = Tex(64, 32, hexc("#4A2E1E"), seed)
    t.noise(4)
    for y0 in (9, 19, 29):
        t.rect(0, y0, 63, y0 + 1, hexc("#E8C890"))
        x = 1
        while x < 60:
            c = t.r.choice(("#F4F2EC", "#F4F2EC", "#C8A070", "#2E6A48", "#E8E4DA", "#9A6A3A"))
            w = t.r.choice((2, 3, 4))
            hh = t.r.choice((3, 4, 5))
            t.rect(x, y0 - hh, x + w - 1, y0 - 1, hexc(c))
            x += w + t.r.choice((1, 2))
    return t


def tx_slat_v(hx, seed):
    """Vertical wood slats, 4 texels wide with 2-texel dark reveals."""
    t = Tex(32, 32, hexc(hx), seed)
    for x in range(32):
        if x % 6 in (4, 5):
            for y in range(32):
                t.set(x, y, shade(hexc(hx), 0.55))
        else:
            k = 1.0 + ((x // 6) % 3 - 1) * 0.05
            for y in range(32):
                t.set(x, y, shade(hexc(hx), k))
    t.noise(4)
    return t


def tx_mural_coffea(seed):
    """COFFEA ARABICA chalk mural (user_18): black wall, 2-texel off-white branches with leaf pairs and berries,
    a small text block top right (grey anti-aliased edges, no 1-texel lines)."""
    t = Tex(64, 32, hexc("#1E2021"), seed)
    chalk, soft = hexc("#E8E6DE"), hexc("#7A7A76")

    def thick(x0, y0, x1, y1):
        t.line(x0, y0, x1, y1, chalk)
        t.line(x0 + 1, y0, x1 + 1, y1, chalk)
    thick(4, 31, 14, 6)
    thick(9, 18, 22, 10)
    thick(26, 31, 30, 14)
    thick(29, 20, 40, 24)
    for (cx, cy) in ((8, 22), (12, 12), (17, 12), (21, 9), (28, 18), (33, 21), (38, 23), (6, 27)):
        t.disc(cx + 0.5, cy + 0.5, 2.2, soft)
        t.disc(cx + 0.5, cy + 0.5, 1.5, chalk)
    for (cx, cy) in ((15, 16), (31, 26), (11, 25)):
        t.disc(cx + 0.5, cy + 0.5, 1.6, hexc("#B84A3A"))
    font_center_x = 50
    for row, word in ((4, "COFFEA"), (11, "ARABICA")):
        x = font_center_x - (len(word) * 4) // 2
        for ch in word:
            g = FONT3.get(ch) if "FONT3" in globals() else None
            if g:
                for py, line_ in enumerate(g):
                    for px, c_ in enumerate(line_):
                        if c_ == "#":
                            t.set(x + px, row + py, chalk)
            x += 4
    t.rect(42, 18, 58, 18, soft)
    t.rect(44, 21, 56, 21, soft)
    return t


def tx_brick_rustic(seed):
    """Rustic running-bond brick tile (B01): small bricks in mixed tan / orange / brown, warm-grey mortar."""
    mortar = hexc("#9C9286")
    cols = [hexc(c) for c in ("#C89A6A", "#B8683C", "#7A4A30", "#A85A36", "#C8845A")]
    t = Tex(32, 32, mortar, seed)
    for course in range(8):
        y0 = course * 4
        off = 4 if course % 2 else 0
        for b in range(5):
            x0 = b * 8 - off
            c = t.r.choice(cols)
            for y in range(y0, y0 + 3):
                for x in range(x0, x0 + 7):
                    t.set(x % 32, y, shade(c, t.r.uniform(0.94, 1.05)))
    return t


def tx_letters_wide(text, hx, seed, h=16):
    """tx_glow_letters on a 128 x 16 card (names of 10-12 letters stay 9 texels wide, bold 2-texel strokes)."""
    t = Tex(128, h, (0, 0, 0), seed, alpha=0)
    n = len(text)
    gw = max(4, (t.w + 1) // n - 1)
    gh = h - 2
    x = (t.w - (n * gw + (n - 1))) // 2
    col = hexc(hx)
    for ch in text:
        g = FONT5.get(ch)
        if g is not None:
            for py in range(gh):
                for px in range(gw):
                    if g[py * 7 // gh][px * 5 // gw] == "#":
                        t.set(x + px, 1 + py, col)
                        if px + 1 < gw:
                            t.set(x + px + 1, 1 + py, col)
        x += gw + 1
    return t


def tx_letters_distressed(text, hx, seed):
    """Big painted letters with a few dropped texels (B01: BABA'S PIZZA on the brick counter)."""
    t = tx_letters_wide(text, hx, seed)
    for _ in range(30):
        x, y = t.r.randrange(128), t.r.randrange(16)
        r, g, b, a = t.px[y][x]
        if a >= 128:
            t.px[y][x] = (r, g, b, 0)
    return t


def tx_tile_lattice(seed):
    """White counter-base tile with light-grey diamond lines (user_19, Panda), 2-texel lines."""
    t = Tex(32, 32, hexc("#F2F2EE"), seed)
    g = hexc("#C4C6C8")
    for y in range(32):
        for x in range(32):
            if (x + y) % 16 in (0, 1) or (x - y) % 16 in (0, 1):
                t.set(x, y, g)
    t.noise(2)
    return t


def tx_speckle_floor(hx, specks, seed, n):
    """A low-contrast speckled floor / laminate (no grout lines)."""
    t = Tex(32, 32, hexc(hx), seed)
    t.noise(3)
    for _ in range(n):
        x, y = t.r.randrange(32), t.r.randrange(32)
        c = hexc(t.r.choice(specks))
        t.set(x, y, c)
        t.set(x + 1, y, c)
    return t


def tx_troffer_sq(seed):
    """2 x 2 lay-in troffer (user_18-20, B02): a 2-texel frame, white lens, a soft cross baffle."""
    t = Tex(16, 16, hexc("#EEF0F2"), seed)
    t.rect(2, 2, 13, 13, hexc("#FFFFFF"))
    t.rect(7, 2, 8, 13, hexc("#E2E6EC"))
    t.rect(2, 7, 13, 8, hexc("#E2E6EC"))
    return t


def tx_vent_sq(seed):
    """Square return-air grille: mid-grey, 2-texel slots."""
    t = Tex(16, 16, hexc("#C8CACC"), seed)
    t.rect(2, 2, 13, 13, hexc("#9A9EA4"))
    for y in range(3, 13, 4):
        t.rect(3, y, 12, y + 1, hexc("#5E6268"))
    return t


def tx_sign_bk_gators(seed):
    """Bookstore fascia (user_20): small 'HOME OF THE' stacked left of a big 'GATORS', blue LED with a pale core."""
    t = Tex(64, 16, (0, 0, 0), seed, alpha=0)
    col, core = hexc("#2F6BFF"), hexc("#A8C4FF")
    x = 23                         # GATORS: FONT5 glyphs 6 texels wide (2-texel strokes), 1-texel gaps
    for ch in "GATORS":
        g = FONT5.get(ch)
        for py in range(14):
            for px in range(6):
                if g[py * 7 // 14][px * 5 // 6] == "#":
                    c = mix(col, core, 0.35) if py < 6 else col
                    t.set(x + px, 1 + py, c)
                    if px + 1 < 6:
                        t.set(x + px + 1, 1 + py, c)
        x += 7
    for row, word in ((2, "HOME"), (8, "OF THE")):
        x = 1
        for ch in word:
            g = FONT3.get(ch) if "FONT3" in globals() else None
            if g:
                for py, line_ in enumerate(g):
                    for px, c_ in enumerate(line_):
                        if c_ == "#":
                            t.set(x + px, row + py, mix(col, core, 0.3))
            x += 2 if ch == " " else 4
    return t


def tx_badge_gator(seed):
    """Round Bookstore badge (user_20): royal-blue disc, white rim, a simple orange / green gator-head silhouette."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    t.disc(16, 16, 15.5, hexc("#FFFFFF"))
    t.disc(16, 16, 13.5, hexc("#1E3CA0"))
    t.rect(7, 13, 24, 18, hexc("#3A9A4A"))
    t.rect(7, 13, 12, 15, hexc("#F47A1E"))
    t.rect(19, 11, 22, 13, hexc("#3A9A4A"))
    t.rect(20, 11, 21, 12, hexc("#FFFFFF"))
    t.rect(8, 17, 22, 18, hexc("#F47A1E"))
    return t


def tx_grille(seed):
    """Rolling security grille (user_20): 2-texel horizontal rods with 2-texel gaps, staggered 2-texel links."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    rod, link = hexc("#AEB2B8"), hexc("#8E9298")
    for y in range(32):
        if y % 4 in (0, 1):
            for x in range(32):
                t.set(x, y, rod)
        else:
            row = y // 4
            for x in range(32):
                if (x + (4 if row % 2 else 0)) % 8 in (0, 1):
                    t.set(x, y, link)
    return t


def tx_jersey(seed):
    """Football jerseys for the Nike window (user_20): left half white with an orange 0, right half royal blue with
    an orange 7 (2-texel strokes)."""
    t = Tex(32, 16, hexc("#F4F4F4"), seed)
    t.rect(16, 0, 31, 15, hexc("#1E3CA0"))
    o = hexc("#F47A1E")
    t.rect(4, 3, 11, 4, o)
    t.rect(4, 11, 11, 12, o)
    t.rect(4, 3, 5, 12, o)
    t.rect(10, 3, 11, 12, o)
    t.rect(19, 3, 27, 4, o)
    t.line(26, 5, 22, 12, o)
    t.line(27, 5, 23, 12, o)
    return t



def tx_art_gallery(kind, seed):
    """iteration 9 (fidelity-4 improvement 9; ru_the_gallery): one large piece per board on the white wall, 64 x 32
    over ~3 x 1.6 m (~5 cm texels; every edge and gap >= 2 texels). a: the big deep-blue canvas with a few pale flecks;
    b: a tall multicolour abstract in the middle, a 3 x 3 grid of small photos left, a column of small landscapes right."""
    t = Tex(64, 32, hexc("#F0EEE8"), seed)
    if kind == "a":
        t.rect(9, 3, 54, 28, hexc("#14247A"))
        t.rect(11, 5, 52, 26, hexc("#1A2E8E"))
        for x_, y_ in ((20, 12), (21, 12), (38, 19), (39, 19), (30, 8), (44, 14)):
            t.set(x_, y_, hexc("#5A70C0"))
    else:
        cols = ["#D8402A", "#F0B030", "#2A8AC8", "#3AA05A", "#8A3AA0", "#E87AA0", "#F4E2A0"]
        t.rect(25, 1, 38, 30, hexc("#2A2420"))
        for y in range(2, 30):
            for x in range(26, 38):
                k = int((x * 0.55 + y * 0.35 + 2.0 * math.sin(y * 0.4)) / 2.2) % len(cols)
                t.set(x, y, hexc(cols[k]))
        for gy in range(3):
            for gx in range(3):
                x0_, y0_ = 3 + gx * 7, 6 + gy * 7
                t.rect(x0_, y0_, x0_ + 4, y0_ + 4, hexc("#2A2420"))
                t.rect(x0_ + 1, y0_ + 1, x0_ + 3, y0_ + 3, shade(hexc(("#8A8478", "#6A7A8A", "#A89070")[(gx + gy) % 3]), 1.0))
        for j in range(3):
            y0_ = 5 + j * 8
            t.rect(44, y0_, 59, y0_ + 5, hexc("#2A2420"))
            t.rect(45, y0_ + 1, 58, y0_ + 2, hexc("#8AB4D8"))
            t.rect(45, y0_ + 3, 58, y0_ + 4, hexc("#5A8A4A"))
    t.noise(2)
    return t


def tx_cedar_soft(seed):
    """Cedar slat ceiling (fix round 2, design: the old 1-texel dark gaps every 4 texels at 2.5 cm/texel crawled
    with no mipmaps from 20-25 m below): 32 px over 1.6 m, slats 4 texels (20 cm) wide in a soft two-tone (2 texels
    light, 2 texels 12% darker), each slat its own tone, a faint grain."""
    base = hexc("#C87C48")
    t = Tex(32, 32, base, seed)
    for i in range(32):
        if i % 4 == 0:
            k = 1.0 + t.r.uniform(-0.08, 0.08)
        for j in range(32):
            c = shade(base, k * (0.88 if i % 4 >= 2 else 1.0))
            if t.r.random() < 0.03:
                c = shade(c, 0.95)
            t.set(j, i, c)
    t.noise(2)
    return t


def tx_room_plaque(seed):
    """Room-number plaque (16 x 32 over 0.15 x 0.3 m, mapped once): a navy plate, a white room number band at the
    top (block digits, readable as a number at N64 scale), a thin white rule, a raised braille row under it. Every
    feature is >= 2 texels (no mipmaps)."""
    t = Tex(16, 32, hexc("#1E2A5C"), seed)
    t.noise(2)
    wht = hexc("#F2F4F8")
    for k, x0 in enumerate((2, 6, 10)):              # three digits: 3 px wide, 7 px tall, 1 px gap
        shape = (("###", "#.#", "#.#", "#.#", "###"), ("##.", ".#.", ".#.", ".#.", "###"),
                 ("###", "..#", "###", "#..", "###"))[(seed // 7 + k) % 3]
        for r, row in enumerate(shape):
            for c, ch in enumerate(row):
                if ch == "#":
                    t.rect(x0 + c, 3 + r * 2, x0 + c, 4 + r * 2, wht)
    t.rect(2, 16, 13, 17, hexc("#9AA8C8"))
    for x in (4, 7, 10):
        t.rect(x, 21, x + 1, 22, hexc("#5A6A9A"))
    t.frame(hexc("#3A4A7A"))
    return t


def tx_bulletin(seed):
    """Corridor bulletin board (ru_os corridors: cork boards with event flyers): a dark frame, cork, and seven
    pinned flyers in UF orange / blue / white / lime, each >= 5 x 6 px with a 2 px title band."""
    t = Tex(32, 32, hexc("#B88A58"), seed)
    t.noise(5)
    t.speckle(40, [hexc("#9A6E40"), hexc("#CCA070")])
    pal = [("#F6F4EE", "#F06A1E"), ("#F06A1E", "#FFFFFF"), ("#2A4AA0", "#FFFFFF"), ("#F6F4EE", "#2A4AA0"),
           ("#C8E070", "#1E2A5C"), ("#FFFFFF", "#B04A3A"), ("#F0D070", "#1E2A5C")]
    spots = [(3, 3, 9, 11), (12, 2, 19, 10), (22, 4, 28, 12), (4, 15, 11, 24), (14, 13, 20, 21), (22, 16, 28, 26),
             (13, 23, 19, 29)]
    for (x0, y0, x1, y1), (bg, ink) in zip(spots, pal):
        t.rect(x0, y0, x1, y1, hexc(bg))
        t.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 2, hexc(ink))
        for yy in range(y0 + 4, y1, 2):
            t.rect(x0 + 1, yy, x1 - 2, yy, shade(hexc(bg), 0.72))
    t.frame(hexc("#4A3424"))
    t.frame(hexc("#5A4030"), 1, 1, 30, 30)
    return t


def tx_sign_bookstore(seed):
    """L1 south hall: the Bookstore storefront sign over the link doors (ru_bookstore_entrance: glowing white
    'University of Florida / Bookstore' letters with a blue halo on a dark fascia band). 64 x 32: UNIVERSITY OF /
    FLORIDA in the 3 px font, BOOKSTORE in the 5 px font, a 1 px blue halo round every letter pixel."""
    bg = hexc("#16181E")
    t = Tex(64, 32, bg, seed)
    t.noise(1)
    white = hexc("#F4F8FF")
    font_center(t, "UNIVERSITY OF", 4, white, font=FONT3)
    font_center(t, "FLORIDA", 11, white, font=FONT3)
    font_center(t, "BOOKSTORE", 19, white, font=FONT5)
    lit = {(x, y) for y in range(32) for x in range(64) if t.get(x, y)[:3] == white}
    halo = hexc("#4A6AD0")
    for (x, y) in lit:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if 0 <= q[0] < 64 and 0 <= q[1] < 32 and q not in lit:
                t.set(q[0], q[1], mix(bg, halo, 0.7))
    return t


# ==== user-photo pass (the user's own photos: atrium core). Appended LAST in TEXTURES (seeds kept).
def tx_tower_glass(seed):
    """The Gators elevator tower's black-glass shaft bay (user_05, B10, C02, C06): near-black #14161B with a soft
    diagonal sheen and two faint guide-rail lines, 32 x 64 per bay (no 1-texel high-contrast line)."""
    base = hexc("#14161B")
    t = Tex(32, 64, base, seed)
    for y in range(64):
        for x in range(32):
            c = shade(base, 1.0 + 0.12 * (1.0 - y / 63.0))
            d = (x + y // 2) % 32
            if d in (5, 6, 7, 8):
                c = mix(c, hexc("#56607A"), 0.30 if d in (6, 7) else 0.14)
            t.set(x, y, c)
    for x in (3, 4, 27, 28):
        for y in range(64):
            t.set(x, y, mix(t.get(x, y)[:3], hexc("#2C3038"), 0.55))
    t.noise(1)
    return t


def tx_tower_car(seed):
    """A lit glass elevator car seen through the tower glass (B10: two visible cars): warm cab, steel frame and
    centre mullion, a handrail line, dark roof / floor bands, two riders. 32 x 64, glows."""
    warm = hexc("#F2D8A8")
    t = Tex(32, 64, warm, seed)
    for y in range(64):
        for x in range(32):
            t.set(x, y, shade(warm, 1.06 - 0.16 * (y / 63.0)))
    steel = hexc("#8C9096")
    t.rect(0, 0, 31, 5, hexc("#3A3E44"))
    t.rect(0, 58, 31, 63, hexc("#3A3E44"))
    t.rect(0, 6, 1, 57, steel)
    t.rect(30, 6, 31, 57, steel)
    t.rect(15, 6, 16, 57, steel)
    t.rect(2, 7, 29, 8, hexc("#FFF6DC"))
    for cx, body in ((8, "#4A5A7A"), (23, "#7A4A3A")):
        t.disc(cx, 31, 2.6, hexc("#5A4A40"))
        t.rect(cx - 3, 34, cx + 3, 57, hexc(body))
    t.rect(0, 41, 31, 42, hexc("#C8CCD0"))
    t.noise(1)
    return t


def tx_sign_gators(seed):
    """The tower's orange 'Gators' script near the top (user_05, B10): slanted letters with a thin white outline and
    a swash underline, on clear (64 x 32 cutout)."""
    t = Tex(64, 32, (0, 0, 0), seed, alpha=0)
    org, wht = hexc("#F47A1E"), hexc("#FFFFFF")
    text = "GATORS"
    gw, gh = 8, 17
    x = (64 - (len(text) * (gw + 1) - 1)) // 2 - 2
    pix = set()
    for ch in text:
        g = FONT5[ch]
        for py in range(gh):
            for px in range(gw):
                if g[py * 7 // gh][px * 5 // gw] == "#":
                    pix.add((x + px + (gh - py) // 4, 5 + py))
        x += gw + 1
    for xx in range(8, 58):
        yy = 25 + int(round(1.4 * math.sin((xx - 8) / 50.0 * math.pi)))
        pix.add((xx, yy))
        pix.add((xx, yy + 1))
    for (px, py) in pix:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (px + dx, py + dy) not in pix:
                    t.set(px + dx, py + dy, wht)
    for (px, py) in pix:
        t.set(px, py, org)
    return t


def tx_band_word(kind, seed):
    """The clerestory word band behind the giant BLUE / ORANGE letters (C09, C10): a white field with two sweeping
    grey diagonal stripes and small grey word echoes; ORANGE's band also carries an orange gator-skin block."""
    t = Tex(64, 16, hexc("#F2F2F0"), seed)
    grey, grey2 = hexc("#BEC1C5"), hexc("#9EA2A7")
    for y in range(16):
        for x in range(64):
            d = (x - 2 * y) % 48
            if 6 <= d <= 9 or 16 <= d <= 17:
                t.set(x, y, grey)
    word = "BLUE" if kind == "blue" else "ORANGE"
    font_text(t, word + " " + word if kind == "blue" else word, 2, 2, grey2, font=FONT3)
    font_text(t, word, 62 - font_width(word, font=FONT3), 9, grey2, font=FONT3)
    if kind == "orange":
        sk = tx_gator_skin(seed + 1)
        for y in range(16):
            for x in range(40, 54):
                c = sk.get(x, y + 8)[:3]
                lum = sum(c) / 765.0
                t.set(x, y, mix(hexc("#E8601C"), hexc("#FFA868"), max(0.0, min(1.0, (lum - 0.80) * 6.0))))
    t.noise(1)
    return t


def tx_carpet_tri(seed):
    """Ground lounge carpet (B08, B09, user_02): a royal-blue triangle geometric, 8 px triangles in royal / navy /
    mid-blue, softened toward royal so the field does not shimmer (64 x 32 over 3 m)."""
    royal, navy, mid = hexc("#2348B4"), hexc("#1B2A66"), hexc("#3A64C8")
    pal = [royal, mix(royal, navy, 0.6), mid, royal, mix(royal, mid, 0.5)]
    t = Tex(64, 32, royal, seed)
    for y in range(32):
        for x in range(64):
            cx, cy, fx, fy = x // 8, y // 8, x % 8, y % 8
            up = 1 if fx > fy else 0
            h = (cx * 7 + cy * 13 + up * 2 + (cx * cy) % 3) % len(pal)
            t.set(x, y, pal[h])
    t.noise(2)
    return t


def tx_banner_welcome2(seed, half):
    """WELCOME banner on the L1 rail over the UF letters (B09): royal blue #1E3CA0 with orange #F06A1E end panels;
    half 0 = WELCOME TO THE / REITZ UNION in white, half 1 = the multilingual welcome in light blue."""
    t = Tex(64, 16, hexc("#1E3CA0"), seed)
    t.noise(1)
    org, wht, lb = hexc("#F06A1E"), hexc("#FFFFFF"), hexc("#A8C4FF")
    if half == 0:
        t.rect(0, 0, 4, 15, org)
        font_center(t, "WELCOME TO THE", 1, wht, font=FONT3, x0=5)
        font_center(t, "REITZ UNION", 8, wht, font=FONT5, spacing=0, x0=5)
    else:
        t.rect(59, 0, 63, 15, org)
        font_center(t, "BIENVENIDOS", 2, lb, font=FONT3, x1=59)
        font_center(t, "WILLKOMMEN", 9, lb, font=FONT3, x1=59)
    return t


def tx_word_small(text, hx, seed, w=64, h=8, font=None, bg=None):
    """Small dimensional letters on clear (or on a bg colour): SENATE CHAMBER (B09), MEXICAN GRILL (B11)."""
    t = Tex(w, h, hexc(bg) if bg else (0, 0, 0), seed, alpha=255 if bg else 0)
    font_center(t, text, (h - 5) // 2, hexc(hx), font=font or FONT3)
    return t


def tx_picket2(seed):
    """Atrium railing infill as photographed (user_02, B05, C05): plain grey vertical pickets every 3 texels
    (~10 cm) between a top and a bottom rail; no mid rail."""
    metal = hexc("#9EA2A6")
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    for y in range(32):
        for x in range(32):
            if y <= 1 or y >= 30 or x % 3 == 1:
                t.set(x, y, shade(metal, 1.1 if y in (0, 30) else 1.0))
    return t


def tx_gator_claw(seed):
    """Navy gator footprint (B05, B06): a tapered heel wedge and three long pointed claw toes spread about +-20 deg
    in the world (the 32 px square maps onto a 0.25 x 0.45 m quad, toes toward row 0)."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    navy = hexc("#1E2A5C")
    for y in range(17, 31):
        w = 2.0 + (y - 17) * 0.5
        for x in range(32):
            if abs(x + 0.5 - 16) <= w and y < 30:
                t.set(x, y, navy)
    t.disc(16, 18, 5.0, navy)
    for ang in (-33.0, 0.0, 33.0):
        a = math.radians(ang)
        for k in range(17):
            px, py = 16 + math.sin(a) * k, 15 - math.cos(a) * k
            t.disc(px, py, max(0.6, 2.3 * (1.0 - k / 17.0)), navy)
    return t


def tx_gator_skin_grey(seed):
    """B09: the gator-skin wall's GREY irregular rounded plates (#B4B6B9..#C4C6C8) on a white #F4F4F2 network, the
    same 2-texel soft network and 3 x 3 plates per 1.0 m tile as int_ru_gator_skin."""
    sk = tx_gator_skin(seed)
    net = hexc("#F3F1EC")
    t = Tex(32, 32, hexc("#F4F4F2"), seed)
    pal = [hexc("#B4B6B9"), hexc("#BCBEC1"), hexc("#C4C6C8")]
    for y in range(32):
        for x in range(32):
            c = sk.get(x, y)[:3]
            lum = sum(c) / 3.0
            k = max(0.0, min(1.0, (lum - 200.0) / (243.0 - 200.0)))   # 0 = plate, 1 = network
            p = pal[((x // 11) + (y // 11) * 2) % 3]
            t.set(x, y, mix(p, hexc("#F4F4F2"), k))
    t.noise(1)
    return t


def tx_snake_plant(seed):
    """CABO's potted snake plants (B10): dark-green spiky upright leaves with yellow edges on clear (16 x 32)."""
    t = Tex(16, 32, (0, 0, 0), seed, alpha=0)
    for x0, top, lean in ((3, 4, -1), (6, 0, 0), (9, 2, 1), (12, 7, 1), (5, 9, -1), (10, 10, 0)):
        for y in range(top, 32):
            f = (y - top) / max(1.0, 31.0 - top)
            w = 0.6 + 1.4 * min(1.0, f * 2.0)
            cx = x0 + lean * (1.0 - f) * 1.5
            for x in range(16):
                dx = abs(x + 0.5 - cx)
                if dx <= w:
                    t.set(x, y, hexc("#C8C060") if dx > w - 0.7 and w > 1.2 else
                          (hexc("#2E5A2C") if (y // 3) % 2 else hexc("#3C6E34")))
    return t



# ==== user-photo pass, Ground floor (user_01, user_03, user_04, B12-B20): appended recipes
def _cond_text(t, text, x, y, col, gw=4, gh=7, sp=1):
    """FONT5 glyphs resampled to gw x gh texels (condensed sign lettering), drawn at (x, y)."""
    for ch in text:
        g = FONT5.get(ch)
        if g is not None:
            for py in range(gh):
                for px in range(gw):
                    if g[py * 7 // gh][px * 5 // gw] == "#":
                        t.set(x + px, y + py, col)
        x += gw + sp
    return x


def _strip_tex(line, j):
    """Texture j of a W x 16 line packed as 64 x 16 strips: strip 2j in rows 0-15, strip 2j+1 in rows 16-31."""
    t = Tex(64, 32, (0, 0, 0), 1)
    for s_ in (0, 1):
        k = 2 * j + s_
        for y in range(16):
            for x in range(64):
                xx = 64 * k + x
                if xx < line.w:
                    t.px[16 * s_ + y][x] = line.px[y][xx]
    return t


def tx_ceiling_dark(seed):
    """Game Room dark lay-in ceiling (user_04 lit tiles ~#656B7A, user_01 black): slate field, a low-contrast grid."""
    t = Tex(32, 32, hexc("#50566A"), seed)
    t.noise(2)
    t.speckle(40, [hexc("#4A5064"), hexc("#565C70")])
    for i in range(32):
        for (x, y) in ((i, 0), (i, 16), (0, i), (16, i)):
            t.set(x, y, hexc("#454B5D"))
    return t


def tx_scale_led(seed):
    """Glowing blue LED gator-scale panel (user_01, B15, B18): irregular croc scales (~0.35 m at tile 2.0), deep
    blue-violet field, brighter scale faces, soft 2-texel periwinkle rims (no 1-texel white lines)."""
    t = Tex(64, 32, hexc("#1A1690"), seed)
    r = t.r
    pts = []
    for gy in range(3):
        for gx in range(6):
            pts.append(((gx + 0.5 + r.uniform(-0.3, 0.3)) * 64 / 6, (gy + 0.5 + r.uniform(-0.3, 0.3)) * 32 / 3))
    tone = [r.uniform(0.85, 1.12) for _ in pts]
    for y in range(32):
        for x in range(64):
            ds = []
            for i, (px, py) in enumerate(pts):
                dx = abs(x + 0.5 - px)
                dx = min(dx, 64 - dx)
                dy = abs(y + 0.5 - py)
                dy = min(dy, 32 - dy)
                ds.append((math.hypot(dx, dy), i))
            ds.sort()
            d1, i1 = ds[0]
            d2 = ds[1][0]
            if d2 - d1 < 1.6:
                c = hexc("#5A6CFF")
            elif d2 - d1 < 3.0:
                c = mix(hexc("#2B2BD8"), hexc("#4250F0"), 0.5)
            else:
                c = mix(shade(hexc("#2B2BD8"), tone[i1]), hexc("#1A1690"), min(0.7, d1 / 9.0))
            t.set(x, y, c)
    t.noise(2)
    return t


def tx_inlay_reitz(seed):
    """'J. WAYNE REITZ UNION' inlaid in the terrazzo by the hotel entrance (B17): charcoal caps on a cream band with
    a grey frame. One 128 x 16 line in two 64 x 16 strips (rows 0-15 = left half, 16-31 = right half)."""
    line = Tex(128, 16, hexc("#E6E1D4"), seed)
    line.noise(2)
    line.frame(hexc("#9A968C"), 0, 1, 127, 14)
    font_center(line, "J. WAYNE REITZ UNION", 5, hexc("#3C3C40"))
    t = _strip_tex(line, 0)
    t.r = random.Random(seed)
    return t


def tx_granite_black(seed):
    t = Tex(32, 32, hexc("#1C1C20"), seed)
    t.noise(2)
    t.speckle(26, [hexc("#3A3A40"), hexc("#2C2C32")])
    return t


def _wayfind_white_line(text, w):
    line = Tex(w, 16, hexc("#F2F1EC"), 7)
    line.rect(0, 0, w - 1, 0, hexc("#C9CCD2"))
    line.rect(0, 15, w - 1, 15, hexc("#C9CCD2"))
    return line


def tx_wayfind_g_white(part):
    """The white Ground hanging sign (user_03, B17): dark caps on off-white, two tiers. Upper line (256 x 16, parts
    0 / 1): ATRIUM | MEETING ROOMS G310-G330 | SENATE CHAMBER; lower line (128 x 16, part 2): HOTEL RECEPTION."""
    ink = hexc("#2B3242")
    if part < 2:
        line = _wayfind_white_line("", 256)
        words = ["ATRIUM", "MEETING ROOMS G310-G330", "SENATE CHAMBER"]
        n = sum(len(w_) for w_ in words)
        width = n * 5 - 1 + 2 * 9
        x = (256 - width) // 2
        for i, w_ in enumerate(words):
            x = _cond_text(line, w_, x, 4, ink)
            if i < 2:
                line.rect(x + 3, 3, x + 4, 12, hexc("#9AA0AC"))
                x += 9
        return _strip_tex(line, part)
    line = _wayfind_white_line("", 128)
    font_center(line, "HOTEL RECEPTION", 4, ink)
    return _strip_tex(line, 0)


def tx_arrow_navy(seed):
    """Navy arrow tile of the white hanging sign: a white chevron arrow pointing +u (mirror the u for '<')."""
    t = Tex(16, 16, hexc("#1E3C9E"), seed)
    t.frame(hexc("#C9CCD2"))
    w = hexc("#FFFFFF")
    t.rect(3, 7, 10, 8, w)
    for i in range(5):
        t.rect(8 + i - 2, 3 + i, 9 + i - 2, 3 + i, w)
        t.rect(8 + i - 2, 12 - i, 9 + i - 2, 12 - i, w)
    return t


def tx_barber_pole(seed):
    """Lit barber pole sleeve (B12, B14): diagonal red / white / blue stripes, wraps once round the 8-gon."""
    t = Tex(16, 32, hexc("#FFFFFF"), seed)
    for y in range(32):
        for x in range(16):
            k = ((x + y) // 4) % 4
            t.set(x, y, hexc(("#D0202A", "#F4F4F4", "#1E3C9E", "#F4F4F4")[k]))
    return t


def tx_sign_barber(seed):
    """BARBERSHOP (B14): navy caps on white inside a 2-texel red / white / blue diagonal-stripe border (128 x 16 line
    in two 64 x 16 strips)."""
    line = Tex(128, 16, hexc("#F6F6F4"), seed)
    cols = ("#D0202A", "#F6F6F4", "#1E3C9E", "#F6F6F4")
    for y in range(16):
        for x in range(128):
            if y < 2 or y > 13 or x < 2 or x > 125:
                line.set(x, y, hexc(cols[((x + y) // 2) % 4]))
    font_center(line, "BARBERSHOP", 4, hexc("#1E2A5C"), spacing=2)
    return _strip_tex(line, 0)


def tx_photo_bw(seed):
    """Historic B&W photo frieze (B13): three greyscale prints with mid-grey frames on the white wall (no 1-texel
    pure black / white)."""
    t = Tex(64, 32, hexc("#ECEBE8"), seed)
    r = t.r
    for k in range(3):
        x0 = 2 + k * 21
        t.rect(x0, 3, x0 + 18, 28, hexc("#7C7C7C"))
        t.rect(x0 + 2, 5, x0 + 16, 26, hexc("#B4B4B0"))
        # a few soft blocks: sky, buildings / figures
        t.rect(x0 + 2, 5, x0 + 16, 12, hexc("#C8C8C4"))
        for _ in range(5):
            bx, by = r.randrange(x0 + 2, x0 + 14), r.randrange(10, 24)
            g = r.choice(("#5A5A58", "#6E6E6C", "#8C8C8A", "#4A4A48"))
            t.rect(bx, by, bx + r.randrange(1, 4), min(26, by + r.randrange(2, 8)), hexc(g))
        t.rect(x0 + 2, 23, x0 + 16, 26, hexc("#7A7A78"))
    t.noise(3)
    return t


def tx_dir_g(seed):
    """Royal-blue Ground floor directory (B13): a big white G, six white text lines, an orange rule (32 x 64)."""
    t = Tex(32, 64, hexc("#1E3C9E"), seed)
    t.noise(2)
    font_text(t, "G", 9, 4, hexc("#FFFFFF"), scale=2)
    t.rect(4, 22, 27, 23, hexc("#F06A1E"))
    for i in range(6):
        y = 28 + i * 5
        t.rect(4, y, 4 + 14 + (i * 7) % 10, y + 1, hexc("#E8ECF6"))
    t.rect(0, 62, 31, 63, hexc("#162C78"))
    return t


def tx_sign_subway(seed):
    """SUBWAY fascia letters (user_03): yellow SUB, white WAY on clear (64 x 16 cutout)."""
    t = tx_glow_letters("SUBWAY", "#FFC20E", None, seed)
    for y in range(16):
        for x in range(32, 64):
            if t.px[y][x][3] >= 128:
                t.set(x, y, hexc("#FFFFFF"))
    return t


def tx_arcade_gamepod(seed):
    """Gamepod Classic cabinet side (B15): black body, a vertical rainbow band of six 2-texel stripes, a lit
    GAMEPOD marquee panel at the top, the blue screen bay."""
    t = Tex(32, 64, hexc("#1A1A1E"), seed)
    t.noise(2)
    for i, hx in enumerate(("#E8303A", "#F28A1E", "#F2D21E", "#3CC24A", "#2E7CE8", "#8A44D8")):
        t.rect(18 + 2 * i, 12, 19 + 2 * i, 63, hexc(hx))
    t.rect(1, 1, 30, 9, hexc("#2A2A30"))
    font_center(t, "GAMEPOD", 3, hexc("#8CC8FF"), font=FONT3)
    t.rect(3, 14, 15, 28, hexc("#1E50C8"))
    t.rect(5, 16, 13, 26, hexc("#3A80E8"))
    return t


def tx_sign_nosh(seed):
    """NOSH SPOT (user_03, the Market's black fascia): white caps, the O in orange."""
    t = tx_glow_letters("NOSH SPOT", "#FFFFFF", None, seed)
    gw = (64 + 1) // 9 - 1
    x0 = (64 - (9 * gw + 8)) // 2 + (gw + 1)
    for y in range(16):
        for x in range(x0, x0 + gw + 1):
            if t.px[y][x][3] >= 128:
                t.set(x, y, hexc("#F28A1E"))
    return t


def tx_badge_market(seed):
    """The round navy MARKET blade sign (user_03): a navy disc, a white ring, MARKET in white caps."""
    t = Tex(32, 32, (0, 0, 0), seed, alpha=0)
    t.disc(16, 16, 15.5, hexc("#F4F4F2"))
    t.disc(16, 16, 14.0, hexc("#1E2A5C"))
    font_center(t, "MARKET", 13, hexc("#FFFFFF"), font=FONT3)
    return t

# ---------------------------------------------------------------- user-photo pass, L1-L3 corridors + Rion
def _bold_letters(t, text, col, x0, x1, y0, gh, gap=1, shadow=None, sdx=1, sdy=1):
    """FONT5 glyphs stretched to (x1 - x0) width and gh texels high, 2-texel strokes when wide enough; an optional
    drop shadow (sdx, sdy texels) drawn first."""
    n = len(text)
    gw = max(4, min(10, (x1 - x0 + gap) // max(1, n) - gap))
    total = n * gw + (n - 1) * gap
    xs = x0 + (x1 - x0 - total) // 2
    for pas, c, ox, oy in ((0, shadow, sdx, sdy), (1, col, 0, 0)):
        if c is None:
            continue
        x = xs
        for ch in text:
            g = FONT5.get(ch)
            if g is not None:
                for py in range(gh):
                    for px in range(gw):
                        if g[py * 7 // gh][px * 5 // gw] == "#":
                            for bx in ((0, 1) if gw >= 7 else (0,)):
                                xx, yy = x + px + bx + ox, y0 + py + oy
                                if 0 <= xx < t.w and 0 <= yy < t.h:
                                    t.set(xx, yy, c)
            x += gw + gap


def tx_ccc_screen(seed):
    """Career Connections Center video wall (user_14, user_15; the blue screen at the corridor end in user_06):
    royal field, white CAREER / CONNECTIONS / CENTER, an orange rule."""
    t = Tex(64, 32, hexc("#1F4DB0"), seed)
    t.noise(2)
    t.rect(0, 0, 63, 1, hexc("#2C5CC2"))
    w = hexc("#F2F5FB")
    _bold_letters(t, "CAREER", w, 8, 56, 3, 7)
    font_center(t, "CONNECTIONS", 13, w, font=FONT3)
    _bold_letters(t, "CENTER", w, 8, 56, 21, 7)
    t.rect(22, 29, 41, 30, hexc("#F08A3A"))
    return t


def tx_marble(seed):
    """White marble (CCC desk, user_14): #E9E9EB with soft 2-texel grey veins (seamless on 32 x 32)."""
    t = _flat("#E9E9EB", seed, 2)
    v1, v2 = hexc("#D9D9DD"), hexc("#E0E0E3")
    # two soft wandering veins (a slow drift, not straight diagonals: those read as a big X on a desk face)
    for k, (x0, amp) in enumerate(((6, 3), (21, 2))):
        for y in range(32):
            x = (x0 + int(round(amp * math.sin((y + 7 * k) * 0.39))) + y // 8) % 32
            t.set(x, y, v1 if k == 0 else v2)
            t.set((x + 1) % 32, y, v2)
    return t


def tx_timeline(seed):
    """UF Student Union history timeline field (user_07, user_08): vertical panels in orange / royal / white / navy,
    each with a photo block and 2-texel text lines (2.4 m repeat)."""
    t = Tex(64, 32, hexc("#F2F1EC"), seed)
    cols = ("#E3672B", "#1F4DA5", "#F2F1EC", "#1B2A4E")
    ink = ("#F7CDB2", "#B9C8EA", "#8C8E94", "#AEB6CC")
    r = t.r
    for k in range(4):
        x0 = k * 16
        t.rect(x0, 0, x0 + 15, 31, hexc(cols[k]))
        # a photo block (greyscale print) and caption lines
        py = 3 if k % 2 == 0 else 15
        t.rect(x0 + 2, py, x0 + 13, py + 9, hexc("#6E6E6C"))
        t.rect(x0 + 3, py + 1, x0 + 12, py + 8, hexc("#A8A8A4"))
        t.rect(x0 + 3, py + 1, x0 + 12, py + 3, hexc("#C4C4C0"))
        t.rect(x0 + 5, py + 4, x0 + 7, py + 8, hexc("#858583"))
        ty = 16 if k % 2 == 0 else 3
        for j in range(3):
            ln = r.randrange(7, 12)
            t.rect(x0 + 2, ty + j * 4, x0 + 2 + ln, ty + j * 4 + 1, hexc(ink[k]))
        # year numerals block (2 texels)
        t.rect(x0 + 2, 28, x0 + 8, 29, hexc(ink[k]))
    return t


def tx_timeline_head(text1, text2, seed):
    """The orange header of the timeline wall (user_07): white caps on UF orange, 128 x 16 (one or two lines)."""
    t = Tex(128, 16, hexc("#E3672B"), seed)
    t.noise(1)
    w = hexc("#FBF4EE")
    if text2:
        font_center(t, text1, 2, w, font=FONT3)
        font_center(t, text2, 9, w, font=FONT3)
    else:
        _bold_letters(t, text1, w, 4, 124, 4, 8)
    return t


def tx_sign_rion(text, seed):
    """Grey dimensional letters (C03, C12, C13): #8A8D92 letters with a #5C5F64 shadow on the #EDEBE6 wall, 128 x 16."""
    t = Tex(128, 16, hexc("#EDEBE6"), seed)
    _bold_letters(t, text, hexc("#8A8D92"), 3, 123, 2, 11, gap=2 if len(text) < 15 else 1, shadow=hexc("#5C5F64"),
                  sdx=1, sdy=1)
    return t


def _cond4(t, text, x, y, col):
    """FONT5 glyphs condensed to 4 x 7 texels keeping both outer columns (the centre column folds into the second),
    so O / D / U / N keep their right edge (returns the x after the text, 1-texel gaps)."""
    for ch in text:
        g = FONT5.get(ch)
        if g is not None:
            for py in range(7):
                row = g[py]
                cells = (row[0] == "#", row[1] == "#" or row[2] == "#", row[3] == "#", row[4] == "#")
                for px, on in enumerate(cells):
                    if on:
                        t.set(x + px, y + py, col)
        x += 5
    return x - 1


def _hang_line(words, w, arrow=None):
    """A light-grey hanging-sign line (user_07, user_11): navy condensed caps, grey '|' separators, w x 16."""
    line = Tex(w, 16, hexc("#E2E4E6"), 5)
    line.rect(0, 0, w - 1, 0, hexc("#C4C7CC"))
    line.rect(0, 15, w - 1, 15, hexc("#C4C7CC"))
    ink = hexc("#1C2B4F")
    n = sum(len(w_) for w_ in words)
    width = n * 5 - 1 + 9 * (len(words) - 1)
    x = (w - width) // 2
    for i, w_ in enumerate(words):
        x = _cond4(line, w_, x, 4, ink)
        if i < len(words) - 1:
            line.rect(x + 3, 3, x + 4, 12, hexc("#8E94A0"))
            x += 9
    return line


HANG_LINES = {
    "pass_up": (["FOOD COURT", "GATOR ONE", "UF BOOKSTORE", "WELCOME CENTER"], 256),
    "pass_lo": (["CONSTANS THEATRE"], 128),
    "blue_up": (["CATERING", "CONSTANS THEATRE", "EVENT SERVICES"], 256),
    "blue_lo": (["CAREER CONNECTIONS CENTER", "GATORWELL"], 256),
    "meet": (["MEETING ROOMS 2315-2365"], 128),
}


def tx_hang(key, j):
    words, w = HANG_LINES[key]
    return _strip_tex(_hang_line(words, w), j)


def tx_oils(seed):
    """Two dark landscape oils in gilt frames (user_06, C11), one per 32 x 32 cell."""
    t = Tex(64, 32, hexc("#7A5A30"), seed)
    for k in range(2):
        x0 = k * 32
        t.rect(x0, 0, x0 + 31, 31, hexc("#8C6A36"))
        t.rect(x0 + 2, 2, x0 + 29, 29, hexc("#5E4626"))
        t.rect(x0 + 3, 3, x0 + 28, 28, hexc("#3E4A4C" if k == 0 else "#4A4438"))
        t.rect(x0 + 3, 3, x0 + 28, 12, hexc("#6A7A78" if k == 0 else "#8A7454"))
        t.rect(x0 + 3, 18, x0 + 28, 28, hexc("#2E3A26" if k == 0 else "#3A4250"))
        t.disc(x0 + (10 if k == 0 else 21), 15, 5, hexc("#283420"))
        t.rect(x0 + 3, 21, x0 + 28, 22, hexc("#4E5A3A" if k == 0 else "#56607A"))
    t.noise(3)
    return t


def tx_slate_floor(seed):
    """CCC slate floor (user_14-16): 0.6 m tiles in two slate greys, staggered rows, 2-texel #3B3E44 grout
    (32 texels = 1.2 m)."""
    t = Tex(32, 32, hexc("#474B52"), seed)
    g = hexc("#3B3E44")
    for row in range(2):
        y0 = row * 16
        off = 8 if row else 0
        for c in range(2):
            col = hexc("#6B7078" if (row + c) % 2 else "#4E525A")
            for y in range(y0, y0 + 16):
                for x in range(16):
                    t.set((c * 16 + off + x) % 32, y, col)
        t.rect(0, y0, 31, y0 + 1, g)
        for c in range(2):
            x = (c * 16 + off) % 32
            t.rect(x, y0, x + 1, y0 + 15, g)
    t.noise(3)
    return t


def tx_word_wall(k, seed):
    """CCC cut-out word wall (user_16): blocky light-grey words on a dark warm-grey field, three lines per panel."""
    t = Tex(64, 32, hexc("#5E5048"), seed)
    t.noise(2)
    lines = (("DESIGN", "YOUR LIFE", "BRIDGE"), ("NEVER TOO", "LATE", "CREATE"))[k]
    for i, w_ in enumerate(lines):
        _bold_letters(t, w_, hexc("#CACCCE"), 2, 62, 2 + i * 10, 8, gap=1)
    return t


def tx_frit(seed):
    """Dotted glass frit band (C04): 2-texel white dots on clear (cutout), rows offset, 64 x 8 = 1.2 m."""
    t = Tex(64, 8, (244, 246, 248), seed, alpha=0)
    for row, y in enumerate((1, 5)):
        for x in range(0 if row == 0 else 2, 64, 4):
            t.rect(x, y, x + 1, y + 1, hexc("#F4F6F8"))
    return t


def tx_rion_case(seed):
    """William E. (Bill) Rion memorial display case (C12, C13): navy backing, a framed B&W portrait, a cream text
    plaque with 2-texel lines, a brass name plate (32 x 64, top = v 1)."""
    t = Tex(32, 64, hexc("#1E2A44"), seed)
    t.noise(2)
    t.rect(7, 6, 24, 29, hexc("#8C6A36"))
    t.rect(9, 8, 22, 27, hexc("#9A9A96"))
    t.rect(9, 8, 22, 13, hexc("#B8B8B4"))
    t.disc(15, 16, 4, hexc("#D2CCC4"))
    t.rect(11, 21, 20, 27, hexc("#3C3C40"))
    t.rect(5, 34, 26, 52, hexc("#EDE6D6"))
    for j in range(4):
        t.rect(8, 37 + j * 4, 23 - (j % 2) * 4, 38 + j * 4, hexc("#8A8478"))
    t.rect(9, 56, 22, 59, hexc("#C8A04A"))
    return t


def _retone(t, f):
    """Scale every texel's RGB by f (clamped): a lighter / warmer copy of an existing recipe."""
    for y in range(t.h):
        for x in range(t.w):
            c = t.get(x, y)
            t.set(x, y, tuple(min(240, int(c[k] * f[k])) for k in range(3)))
    return t


def tx_door_meeting_honey(seed):
    """The L2 / L3 meeting-room and Rion door in honey wood (C03, C08, C12, C13): the walnut recipe re-toned."""
    t = tx_door_meeting(seed)
    f = (1.96, 2.17, 1.72)
    for y in range(t.h):
        for x in range(t.w):
            c = t.get(x, y)
            if c[0] - c[2] > 18:
                t.set(x, y, tuple(min(235, int(c[k] * f[k])) for k in range(3)))
    return t


def tx_partition(seed):
    """Operable-partition panels (C08): #8C9095 with 2-texel #6E7277 joints every 0.6 m (32 = 1.2 m)."""
    t = _flat("#8C9095", seed, 2)
    for x in (0, 16):
        t.rect(x, 0, x + 1, 31, hexc("#6E7277"))
    return t


def write_textures(out_dir=None, sheet=None):
    from PIL import Image
    out_dir = out_dir or stage_palette.TEXTURE_DIR
    os.makedirs(out_dir, exist_ok=True)
    written = []
    missing = [n for n in RU_MATERIALS if n not in TEXTURES]
    if missing:
        raise SystemExit(f"no texture recipe for {missing}")
    for i, (name, fn) in enumerate(TEXTURES.items()):
        t = fn(1000 + i * 7)
        want = RU_MATERIALS[name]["size"]
        if (t.w, t.h) != tuple(want):
            raise SystemExit(f"{name}: recipe makes {t.w}x{t.h}, palette says {want}")
        path = os.path.join(out_dir, name + ".png")
        im = t.image()
        if os.path.exists(path):
            try:
                old = Image.open(path).convert("RGBA")
                if old.size == im.size and old.tobytes() == im.tobytes():
                    written.append(path)
                    continue
            except Exception:  # noqa: BLE001
                pass
        im.save(path)
        written.append(path)
    if sheet:
        cols = 10
        cell = 136
        rows = (len(TEXTURES) + cols - 1) // cols
        from PIL import ImageDraw
        sh = Image.new("RGB", (cols * cell, rows * (cell + 14)), (36, 36, 40))
        d = ImageDraw.Draw(sh)
        for i, name in enumerate(TEXTURES):
            im = Image.open(os.path.join(out_dir, name + ".png")).convert("RGBA")
            k = 128 // max(im.size)
            im2 = im.resize((im.width * k * 2 if im.width < 64 and im.height < 64 and False else im.width * k,
                             im.height * k), Image.NEAREST)
            bg = Image.new("RGBA", im2.size, (90, 90, 96, 255))
            bg.alpha_composite(im2)
            x, y = (i % cols) * cell, (i // cols) * (cell + 14)
            sh.paste(bg.convert("RGB"), (x + 4, y + 4))
            d.text((x + 4, y + cell - 2), name[7:], fill=(230, 230, 230))
        sh.save(sheet)
    return written


# ================================================================== plan geometry (pure Python, map metres)
EPS = 1e-9


def signed_area(p):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]):
        a += x1 * y2 - x2 * y1
    return a / 2.0


def ccw(p):
    p = [(float(x), float(y)) for x, y in p]
    return p if signed_area(p) >= 0 else list(reversed(p))


def cw(p):
    return list(reversed(ccw(p)))


def bbox(p):
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return (min(xs), min(ys), max(xs), max(ys))


def centroid(p):
    a = signed_area(p)
    if abs(a) < 1e-9:
        return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))
    cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]):
        c = x1 * y2 - x2 * y1
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    return (cx / (6 * a), cy / (6 * a))


def pip(pt, poly):
    """Point in polygon (even-odd)."""
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                inside = not inside
        j = i
    return inside


def seg_point_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def poly_dist(pt, poly):
    return min(seg_point_dist(pt, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def edges(poly):
    return list(zip(poly, poly[1:] + poly[:1]))


def clean(poly, eps=0.02, collinear=0.004):
    """Drop repeated points (< eps apart) and points on a straight line (|sin| < collinear)."""
    p = []
    for q in poly:
        q = (float(q[0]), float(q[1]))
        if not p or math.dist(p[-1], q) > eps:
            p.append(q)
    if len(p) > 1 and math.dist(p[0], p[-1]) <= eps:
        p.pop()
    changed = True
    while changed and len(p) > 3:
        changed = False
        for i in range(len(p)):
            a, b, c = p[i - 1], p[i], p[(i + 1) % len(p)]
            l1, l2 = math.dist(a, b), math.dist(b, c)
            if l1 < eps or l2 < eps:
                p.pop(i)
                changed = True
                break
            cr = ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) / (l1 * l2)
            dt = ((b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]))
            if abs(cr) < collinear and dt > 0:
                p.pop(i)
                changed = True
                break
    return p


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _in_tri(p, a, b, c):
    d1, d2, d3 = _cross(a, b, p), _cross(b, c, p), _cross(c, a, p)
    neg = (d1 < -1e-12) or (d2 < -1e-12) or (d3 < -1e-12)
    pos = (d1 > 1e-12) or (d2 > 1e-12) or (d3 > 1e-12)
    return not (neg and pos)


def earclip(poly):
    """Triangulate a simple polygon (any winding; may contain hole bridges = repeated points).
    -> [(a, b, c)] counter-clockwise point triples."""
    P = ccw(poly)
    n = len(P)
    if n < 3:
        return []
    idx = list(range(n))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 4 * n * n + 100:
        guard += 1
        m = len(idx)
        clipped = False
        for k in range(m):
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = P[ia], P[ib], P[ic]
            if _cross(a, b, c) <= 1e-10:
                continue
            ok = True
            for j in idx:
                if j in (ia, ib, ic):
                    continue
                q = P[j]
                if q == a or q == b or q == c:
                    continue
                if _in_tri(q, a, b, c):
                    ok = False
                    break
            if ok:
                tris.append((a, b, c))
                idx.pop(k)
                clipped = True
                break
        if not clipped:
            # degenerate (collinear or a self-touching bridge): drop the flattest vertex
            best, bk = None, 0
            for k in range(m):
                a, b, c = P[idx[k - 1]], P[idx[k]], P[idx[(k + 1) % m]]
                v = abs(_cross(a, b, c))
                if best is None or v < best:
                    best, bk = v, k
            idx.pop(bk)
    if len(idx) == 3:
        a, b, c = (P[i] for i in idx)
        if _cross(a, b, c) > 1e-10:
            tris.append((a, b, c))
    return tris


def _ray_hit(M, poly):
    """Nearest intersection of the +x ray from M with poly's edges: (x, edge index) or None."""
    best = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > M[1]) == (b[1] > M[1]):
            if abs(a[1] - M[1]) < 1e-12 and a[0] >= M[0]:
                if best is None or a[0] < best[0]:
                    best = (a[0], i)
            continue
        x = a[0] + (M[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if x >= M[0] - 1e-12 and (best is None or x < best[0]):
            best = (x, i)
    return best


def bridge_holes(outer, holes):
    """One polygon (with zero-width bridges) from a CCW outer ring and holes inside it (Eberly)."""
    poly = ccw(outer)
    hs = [cw(h) for h in holes if len(h) >= 3]
    hs.sort(key=lambda h: -max(p[0] for p in h))
    for h in hs:
        mi = max(range(len(h)), key=lambda i: (h[i][0], -h[i][1]))
        M = h[mi]
        hit = _ray_hit(M, poly)
        if hit is None:
            continue
        xI, ei = hit
        a, b = poly[ei], poly[(ei + 1) % len(poly)]
        I = (xI, M[1])
        pi = ei if a[0] > b[0] else (ei + 1) % len(poly)
        P = poly[pi]
        if math.dist(I, a) < 1e-9:
            pi = ei
        elif math.dist(I, b) < 1e-9:
            pi = (ei + 1) % len(poly)
        else:
            # reflex vertices inside triangle M I P: take the one with the smallest angle to the ray
            cand = []
            for j, q in enumerate(poly):
                if j == pi:
                    continue
                pr, nx_ = poly[j - 1], poly[(j + 1) % len(poly)]
                if _cross(pr, q, nx_) < 0 and _in_tri(q, M, I, P) and q[0] >= M[0]:
                    ang = abs(math.atan2(q[1] - M[1], q[0] - M[0]))
                    cand.append((ang, math.dist(q, M), j))
            if cand:
                pi = min(cand)[2]
        P = poly[pi]
        ring = h[mi:] + h[:mi] + [h[mi]]
        poly = poly[:pi + 1] + ring + [P] + poly[pi + 1:]
    return poly


def triangulate(outer, holes=()):
    outer = clean(outer)
    holes = [clean(h) for h in holes]
    holes = [h for h in holes if len(h) >= 3]
    if len(outer) < 3:
        return []
    poly = bridge_holes(outer, holes) if holes else ccw(outer)
    return earclip(poly)


def clip_convex(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a CONVEX polygon by a rectangle -> convex polygon (may be empty)."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            ci, pv = inside(cur), inside(prev)
            if ci:
                if not pv:
                    out.append(inter(prev, cur))
                out.append(cur)
            elif pv:
                out.append(inter(prev, cur))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))

    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / (b[1] - a[1]), yv)
    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            return []
        pts = clip(pts, inside, inter)
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    return out if len(out) >= 3 and abs(signed_area(out)) > 1e-6 else []


def clip_halfplane(poly, a, b, keep_left=True):
    """Clip a convex polygon by the line a -> b, keeping the left (or right) side."""
    def side(p):
        v = _cross(a, b, p)
        return v if keep_left else -v
    out = []
    n = len(poly)
    for i in range(n):
        cur, prev = poly[i], poly[i - 1]
        sc, sp = side(cur), side(prev)
        if sc >= 0:
            if sp < 0:
                t = sp / (sp - sc)
                out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
            out.append(cur)
        elif sp >= 0:
            t = sp / (sp - sc)
            out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
    clean_ = []
    for q in out:
        if not clean_ or math.dist(q, clean_[-1]) > 1e-7:
            clean_.append(q)
    if len(clean_) > 1 and math.dist(clean_[0], clean_[-1]) < 1e-7:
        clean_.pop()
    return clean_ if len(clean_) >= 3 and abs(signed_area(clean_)) > 1e-7 else []


def convex_minus(piece, hole):
    """Convex piece minus a CONVEX hole -> disjoint convex pieces."""
    hole = ccw(hole)
    rest = ccw(piece)
    out = []
    for a, b in edges(hole):
        if not rest:
            break
        outside = clip_halfplane(rest, a, b, keep_left=False)
        if outside:
            out.append(outside)
        rest = clip_halfplane(rest, a, b, keep_left=True)
    return out


def rect_cover(polys, step, avoid=(), ox=0.0, oy=0.0):
    """Cells of the global `step` grid touched by polygons, merged into maximal rectangles; cells touching an
    `avoid` polygon are returned separately as exact convex pieces (polys clipped to the cell minus avoid, holes
    triangulated). -> (rects [(x0, y0, x1, y1)], pieces [convex polygons])."""
    tris = [list(t) for p in polys for t in triangulate(p)]
    cells = {}
    for tri in tris:
        x0, y0, x1, y1 = bbox(tri)
        for i in range(math.floor((x0 - ox) / step), math.ceil((x1 - ox) / step)):
            for j in range(math.floor((y0 - oy) / step), math.ceil((y1 - oy) / step)):
                pc = clip_convex(tri, ox + i * step, oy + j * step, ox + (i + 1) * step, oy + (j + 1) * step)
                if pc:
                    cells.setdefault((i, j), []).append(pc)
    av = [(bbox(a), a) for a in avoid]
    avoid_cvx = []
    for a in avoid:          # convex holes as they are, others as triangles
        a = ccw(a)
        convex = all(_cross(a[k - 1], a[k], a[(k + 1) % len(a)]) >= -1e-9 for k in range(len(a)))
        avoid_cvx.extend([a] if convex else [list(t) for t in triangulate(a)])
    exact, full = [], set()
    for (i, j), pcs in cells.items():
        cx0, cy0 = ox + i * step, oy + j * step
        cx1, cy1 = cx0 + step, cy0 + step
        touch = any(not (b[0] >= cx1 or b[2] <= cx0 or b[1] >= cy1 or b[3] <= cy0) for b, _ in av)
        if touch:
            # the whole cell (spilling past walls into closed rooms is harmless) minus the holes
            exact.extend(subtract([[(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)]], avoid_cvx))
        else:
            full.add((i, j))
    rects = []
    done = set()
    for (i, j) in sorted(full, key=lambda k: (k[1], k[0])):
        if (i, j) in done:
            continue
        i2 = i
        while (i2 + 1, j) in full and (i2 + 1, j) not in done:
            i2 += 1
        j2 = j
        while all((ii, j2 + 1) in full and (ii, j2 + 1) not in done for ii in range(i, i2 + 1)):
            j2 += 1
        for ii in range(i, i2 + 1):
            for jj in range(j, j2 + 1):
                done.add((ii, jj))
        rects.append((ox + i * step, oy + j * step, ox + (i2 + 1) * step, oy + (j2 + 1) * step))
    return rects, exact


def subtract(pieces, holes):
    """Convex pieces minus convex holes (bounding boxes first)."""
    hb = [(bbox(h), h) for h in holes]
    out = []
    for pc in pieces:
        cur = [pc]
        b = bbox(pc)
        for (x0, y0, x1, y1), h in hb:
            if x0 >= b[2] or x1 <= b[0] or y0 >= b[3] or y1 <= b[1]:
                continue
            nxt = []
            for q in cur:
                nxt.extend(convex_minus(q, h))
            cur = nxt
        out.extend(cur)
    return out


def grid_pieces(tris, step, ox=0.0, oy=0.0):
    """Split triangles on a global grid (cell = step m, lines at ox + k step) -> convex CCW polygons, so the
    vertex-colour bake has samples every ~step metres."""
    out = []
    for tri in tris:
        x0, y0, x1, y1 = bbox(tri)
        i0, i1 = math.floor((x0 - ox) / step), math.ceil((x1 - ox) / step)
        j0, j1 = math.floor((y0 - oy) / step), math.ceil((y1 - oy) / step)
        if i1 - i0 <= 1 and j1 - j0 <= 1:
            out.append(list(tri))
            continue
        for i in range(i0, i1):
            for j in range(j0, j1):
                pc = clip_convex(list(tri), ox + i * step, oy + j * step, ox + (i + 1) * step, oy + (j + 1) * step)
                if pc:
                    out.append(ccw(pc))
    return out


def offset_poly(poly, d):
    """Offset a polygon outward by d (CCW in, mitred corners clamped to 3 d)."""
    poly = ccw(poly)
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        L = math.dist(a, b) or 1.0
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
        lines.append(((a[0] + nx * d, a[1] + ny * d), (b[0] + nx * d, b[1] + ny * d)))
    out = []
    for i in range(n):
        (p1, p2), (p3, p4) = lines[i - 1], lines[i]
        d1 = (p2[0] - p1[0], p2[1] - p1[1])
        d2 = (p4[0] - p3[0], p4[1] - p3[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            out.append(p3)
            continue
        t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
        q = (p1[0] + d1[0] * t, p1[1] + d1[1] * t)
        o = poly[i]
        if math.dist(q, o) > 3 * abs(d):
            k = 3 * abs(d) / math.dist(q, o)
            q = (o[0] + (q[0] - o[0]) * k, o[1] + (q[1] - o[1]) * k)
        out.append(q)
    return out


def convex_hull(pts):
    pts = sorted(set((round(p[0], 4), round(p[1], 4)) for p in pts))
    if len(pts) <= 2:
        return pts
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def shrink(poly, d):
    return offset_poly(poly, -d)


def resample_arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def polyline_len(pl):
    return sum(math.dist(a, b) for a, b in zip(pl, pl[1:]))


def along(pl, s):
    """Point + unit direction at distance s along a polyline."""
    acc = 0.0
    for a, b in zip(pl, pl[1:]):
        L = math.dist(a, b)
        if acc + L >= s or (a, b) == (pl[-2], pl[-1]):
            t = 0.0 if L < 1e-9 else max(0.0, min(1.0, (s - acc) / L))
            d = ((b[0] - a[0]) / (L or 1), (b[1] - a[1]) / (L or 1))
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), d
        acc += L
    return pl[-1], (1.0, 0.0)


# ================================================================== mesh helpers on KitMesh
def add_raw(km, pts, mat, normal_hint=None):
    """A collision polygon with a material the kit does not know (instant-warp floors): appended directly."""
    pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
    if normal_hint is not None and K._dot(K.newell(pts), normal_hint) < 0:
        pts.reverse()
    km.polys.append(K.Poly(pts, mat, None, [1.0] * len(pts), None, False))


def floor_poly(V, poly, z, mat, step=3.0, holes=(), tint=None, ao=1.0, down=False, uvs_fn=None, cut=()):
    """Visual floor (or ceiling with down=True) over a polygon, split on the global step grid; cut = convex holes
    subtracted exactly."""
    tris = triangulate(poly, holes)
    pcs = grid_pieces(tris, step)
    if cut:
        pcs = subtract(pcs, cut)
    for pc in pcs:
        pts = [(x, y, z) for x, y in (reversed(pc) if down else pc)]
        V.poly(pts, mat, ao=ao, tint=tint, uvs=uvs_fn(pts) if uvs_fn else None)


def col_floor(C, poly, z, mat=K.COL, holes=(), down=False, raw=False, cut=()):
    """Collision floor / ceiling polygon (triangulated, no grid); cut = convex holes subtracted exactly."""
    pcs = [list(t) for t in triangulate(poly, holes)]
    if cut:
        pcs = subtract(pcs, cut)
    for pc in pcs:
        pts = [(p[0], p[1], z) for p in ccw(pc)]
        if down:
            pts.reverse()
        if raw:
            add_raw(C, pts, mat)
        else:
            C.poly(pts, mat)


def quad_wall(V, a, b, z0, z1, mat, uvs=None, ao=None, tint=None, glow=False):
    """Vertical quad a -> b (2D), normal on the RIGHT of a -> b."""
    return V.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat, uvs=uvs, ao=ao,
                  tint=tint, glow=glow)


def panel(V, a, b, z0, z1, mat, off=0.0, glow=False, tint=None, u0=0.0, u1=1.0, v0=0.0, v1=1.0, ao=1.0):
    """A once-mapped panel on the wall line a -> b, facing RIGHT of a -> b, pushed off metres along that normal.
    The texture reads upright and unmirrored from the front."""
    L = math.dist(a, b)
    if L < 1e-6:
        return
    nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    pa = (a[0] + nx * off, a[1] + ny * off)
    pb = (b[0] + nx * off, b[1] + ny * off)
    # walking a -> b with the normal on the right: a viewer facing the panel has a on the LEFT, b on the right
    V.poly([(pb[0], pb[1], z0), (pa[0], pa[1], z0), (pa[0], pa[1], z1), (pb[0], pb[1], z1)], mat,
           uvs=[(u1, v0), (u0, v0), (u0, v1), (u1, v1)], glow=glow, tint=tint, ao=ao, normal_hint=(nx, ny, 0.0))


def seg_box(V, a, b, half_t, z0, z1, mat, faces="sideends_top", mats=None, tint=None, ao=None):
    """Box around segment a-b (half thickness half_t), visual: the two long sides, the two ends, the top."""
    L = math.dist(a, b)
    if L < 1e-6:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = dy, -dx
    p0 = (a[0] + nx * half_t, a[1] + ny * half_t)
    p1 = (b[0] + nx * half_t, b[1] + ny * half_t)
    q0 = (a[0] - nx * half_t, a[1] - ny * half_t)
    q1 = (b[0] - nx * half_t, b[1] - ny * half_t)
    m = mats or {}
    if "side" in faces:
        quad_wall(V, p0, p1, z0, z1, m.get("r", mat), tint=tint, ao=ao)     # right side (normal +n)
        quad_wall(V, q1, q0, z0, z1, m.get("l", mat), tint=tint, ao=ao)     # left side
    if "ends" in faces:
        quad_wall(V, q0, p0, z0, z1, m.get("e", mat), tint=tint, ao=ao)
        quad_wall(V, p1, q1, z0, z1, m.get("e", mat), tint=tint, ao=ao)
    if "top" in faces:
        V.poly([(p0[0], p0[1], z1), (p1[0], p1[1], z1), (q1[0], q1[1], z1), (q0[0], q0[1], z1)], m.get("t", mat),
               normal_hint=(0, 0, 1), tint=tint, ao=ao)
    if "bot" in faces:
        V.poly([(p0[0], p0[1], z0), (q0[0], q0[1], z0), (q1[0], q1[1], z0), (p1[0], p1[1], z0)], m.get("b", mat),
               normal_hint=(0, 0, -1), tint=tint, ao=ao)


def col_seg(C, a, b, half_t, z0, z1, mat=K.COL, top=True, bottom=False):
    """Closed collision block around segment a-b."""
    L = math.dist(a, b)
    if L < 1e-4:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    foot = ccw([(a[0] + nx * half_t, a[1] + ny * half_t), (b[0] + nx * half_t, b[1] + ny * half_t),
                (b[0] - nx * half_t, b[1] - ny * half_t), (a[0] - nx * half_t, a[1] - ny * half_t)])
    C.prism(foot, z0, z1, mat, top=mat if top else None, bottom=mat if bottom else None)


def cyl(V, x, y, r, z0, z1, mat, n=8, top=True, bottom=False, tint=None, ao=None):
    pts = [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for a, b in edges(pts):
        quad_wall(V, a, b, z0, z1, mat, tint=tint, ao=ao)
    if top:
        V.poly([(p[0], p[1], z1) for p in pts], mat, tint=tint)
    if bottom:
        V.poly([(p[0], p[1], z0) for p in reversed(pts)], mat, tint=tint)


def prism(V, foot, z0, z1, mat, top=None, bottom=None, tint=None, ao=None):
    foot = ccw(foot)
    for a, b in edges(foot):
        quad_wall(V, a, b, z0, z1, mat, tint=tint, ao=ao)
    if top:
        floor_poly(V, foot, z1, top, step=99.0, tint=tint)
    if bottom:
        floor_poly(V, foot, z0, bottom, step=99.0, down=True, tint=tint)


# ================================================================== props (local frame: front = +y, origin base centre)
def _p(kind, **info):
    return K.Prop(kind, **info)


def bowling_lane_set(n_lanes=14, lane_len=18.29, approach=4.6, pin_deck=0.9, pit=1.2, seed=0):
    """The Game Room's 14 lanes (ru_gr_lanes_overview_1/2, ru_gr_lane_screens, ru_gr_kosmic_lanes), local frame:
    x across the lanes (centred), y = 0 at the foul line, lanes run toward -y (the pins), approach toward +y.
    Per lane 1.066 m bed + 2 x 0.24 m gutters; a 0.15 m capping between lanes; Brunswick ball returns between
    pairs; white round columns between pairs; masking unit + video wall over the pit; overhead truss with
    score monitors above the foul line. Collision: one flat floor (lane beds are floor), the pin deck, the
    masking front (a wall), ball-return blocks, columns."""
    P = _p("bowling_lanes", n=n_lanes)
    V, C = P.visual, P.collision
    bed, gut, cap = 1.066, 0.235, 0.11
    pitch = bed + 2 * gut + cap
    W = n_lanes * pitch + cap
    x0 = -W / 2
    yp = -lane_len - pin_deck           # back of the pin deck
    ypit = yp - pit
    pins = [(0, 0)]
    for row in range(1, 4):
        for k in range(row + 1):
            pins.append(((k - row / 2) * 0.305, -row * 0.264))
    for i in range(n_lanes):
        lx = x0 + cap + i * pitch + gut + bed / 2
        # lane bed: lanes + arrows segment
        V.poly([(lx - bed / 2, -lane_len, 0.0), (lx + bed / 2, -lane_len, 0.0), (lx + bed / 2, -6.0, 0.0),
                (lx - bed / 2, -6.0, 0.0)], "int_ru_lane", ao=1.0)
        V.poly([(lx - bed / 2, -6.0, 0.0), (lx + bed / 2, -6.0, 0.0), (lx + bed / 2, -2.0, 0.0),
                (lx - bed / 2, -2.0, 0.0)], "int_ru_lane_arrows", uvs=K.uv_rect(0, 0, 1, 1), ao=1.0)
        V.poly([(lx - bed / 2, -2.0, 0.0), (lx + bed / 2, -2.0, 0.0), (lx + bed / 2, 0.0, 0.0),
                (lx - bed / 2, 0.0, 0.0)], "int_ru_lane", ao=1.0)
        # foul line
        V.poly([(lx - bed / 2, -0.02, 0.003), (lx + bed / 2, -0.02, 0.003), (lx + bed / 2, 0.02, 0.003),
                (lx - bed / 2, 0.02, 0.003)], "int_ru_black", ao=1.0)
        # gutters (dark channels, 6 cm deep)
        for gx in (lx - bed / 2 - gut, lx + bed / 2):
            V.poly([(gx, yp, -0.06), (gx + gut, yp, -0.06), (gx + gut, 0.0, -0.06), (gx, 0.0, -0.06)],
                   "int_ru_black", ao=0.8)
            quad_wall(V, (gx, 0.0), (gx, yp), -0.06, 0.0, "int_ru_black", ao=0.7)
            quad_wall(V, (gx + gut, yp), (gx + gut, 0.0), -0.06, 0.0, "int_ru_black", ao=0.7)
        # pin deck
        V.poly([(lx - bed / 2, yp, 0.0), (lx + bed / 2, yp, 0.0), (lx + bed / 2, -lane_len, 0.0),
                (lx - bed / 2, -lane_len, 0.0)], "int_ru_lane", ao=0.95)
        # pins: low-poly white prisms with red neck stripes (pin face texture)
        for px, py in pins:
            cx, cy = lx + px, -lane_len - 0.3 + py
            for k in range(4):
                a0, a1 = k * math.pi / 2 + math.pi / 4, (k + 1) * math.pi / 2 + math.pi / 4
                pa = (cx + 0.06 * math.cos(a0), cy + 0.06 * math.sin(a0))
                pb = (cx + 0.06 * math.cos(a1), cy + 0.06 * math.sin(a1))
                quad_wall(V, pa, pb, 0.0, 0.38, "int_ru_pins", uvs=K.uv_rect(0, 0, 0.25, 1), ao=1.0)
        # dark pit + the lane's lit hood glow
        V.poly([(lx - bed / 2 - gut, ypit, -0.3), (lx + bed / 2 + gut, ypit, -0.3), (lx + bed / 2 + gut, yp, -0.3),
                (lx - bed / 2 - gut, yp, -0.3)], "int_ru_black", ao=0.4)
    # cappings between lanes + outer kickbacks (low black strips)
    for i in range(n_lanes + 1):
        cx0 = x0 + i * pitch
        V.box(cx0, yp, 0.0, cx0 + cap, 0.0, 0.05, "int_ru_black", faces="+x-x+z")
        if i in (0, n_lanes):
            V.box(cx0, yp, 0.0, cx0 + cap, -lane_len + 1.0, 1.1, "int_ru_wall_navy", faces="+x-x+z")
    # pin-deck front of the pit wall and the masking units (one long fascia across all lanes) + video wall
    V.box(x0, ypit - 0.3, -0.3, x0 + W, ypit, 1.4, "int_ru_black", faces="+y")
    zm0, zm1 = 1.25, 1.9            # (fidelity-3: a short masking fascia under a tall video wall, ru_gr_lane_screens)
    V.poly([(x0 + W, yp + 0.2, zm0), (x0, yp + 0.2, zm0), (x0, yp + 0.2, zm1), (x0 + W, yp + 0.2, zm1)],
           "int_ru_masking", uvs=[(0, 0), (W / 4.0, 0), (W / 4.0, 1), (0, 1)], normal_hint=(0, 1, 0), ao=1.0)
    V.poly([(x0, yp + 0.2, zm0), (x0 + W, yp + 0.2, zm0), (x0 + W, yp - 0.6, zm0), (x0, yp - 0.6, zm0)],
           "int_ru_black", normal_hint=(0, 0, -1), ao=0.6)
    # video wall above the masking (ru_gr_lane_screens): ONE continuous broadcast wall across all the lanes (the
    # seamless broadcast tile shows 3 times across the wall; a thin black bezel on the backing all round)
    V.poly([(x0 + W - 0.12, yp + 0.25, zm1 + 0.1), (x0 + 0.12, yp + 0.25, zm1 + 0.1), (x0 + 0.12, yp + 0.25, zm1 + 3.0),
            (x0 + W - 0.12, yp + 0.25, zm1 + 3.0)], "int_ru_video_wall", uvs=[(0, 0), (3.0, 0), (3.0, 1), (0, 1)],
           glow=True, normal_hint=(0, 1, 0))
    V.poly([(x0 + W, yp + 0.2, zm1), (x0, yp + 0.2, zm1), (x0, yp + 0.2, 5.4), (x0 + W, yp + 0.2, 5.4)],
           "int_ru_black", normal_hint=(0, 1, 0), ao=0.9)
    # collision: masking front wall above the pins (Mario can walk to the pins), pit floor. It runs 2.7 m past both
    # lane-block ends (into the room's side walls) so the strip behind it is sealed; black returns close the ends
    C.wall((x0 + W + 2.7, yp + 0.2), (x0 - 2.7, yp + 0.2), -0.3, 5.6, K.COL)
    for xa_, xb_ in ((x0 - 2.45, x0), (x0 + W, x0 + W + 2.45)):
        V.poly([(xb_, yp + 0.2, 0.0), (xa_, yp + 0.2, 0.0), (xa_, yp + 0.2, 5.4), (xb_, yp + 0.2, 5.4)],
               "int_ru_black", normal_hint=(0, 1, 0), ao=0.8)
    # approaches (ru_gr_lanes_overview_1, ru_gr_lane_screens): light maple from the foul line back to the step
    V.poly([(x0, 0.0, 0.0), (x0 + W, 0.0, 0.0), (x0 + W, approach, 0.0), (x0, approach, 0.0)], "int_ru_maple",
           ao=1.0)
    # ball returns between pairs (ru_gr_lanes_overview_1): the rounded black Brunswick hood at the front, a low
    # black base with two steel rails behind it, low-poly (8-sided) balls on the rails
    hood = [(-0.36, 0.0), (-0.36, 0.52), (-0.31, 0.76), (-0.18, 0.90), (0.0, 0.95), (0.18, 0.90), (0.31, 0.76),
            (0.36, 0.52), (0.36, 0.0)]
    for p in range(n_lanes // 2):
        bx = x0 + cap + (2 * p + 1) * pitch - cap / 2
        hy0, hy1 = 0.5, 1.25
        for (ua, va), (ub, vb) in zip(hood, hood[1:]):
            # the hood's shell strip a -> b (profile runs -x -> +x over the top: the outward normal is on the left
            # of the profile walked from y1 to y0)
            V.poly([(bx + ua, hy0, va), (bx + ub, hy0, vb), (bx + ub, hy1, vb), (bx + ua, hy1, va)], "int_ru_black",
                   normal_hint=(-(vb - va), 0.0, (ub - ua)))
        V.poly([(bx + u, hy0, v) for u, v in hood], "int_ru_black", normal_hint=(0, -1, 0))
        V.poly([(bx + u, hy1, v) for u, v in reversed(hood)], "int_ru_black", normal_hint=(0, 1, 0))
        V.box(bx - 0.30, hy0 - 0.01, 0.62, bx + 0.30, hy0 + 0.0, 0.70, "int_ru_steel", faces="-y")
        V.box(bx - 0.22, hy1, 0.0, bx + 0.22, 2.4, 0.36, "int_ru_black", faces="+x-x+y+z")
        for rx in (-0.08, 0.08):
            V.box(bx + rx - 0.015, hy1, 0.36, bx + rx + 0.015, 2.4, 0.40, "int_ru_steel", faces="+x-x+y+z")
        K.col_box(C, bx - 0.36, 0.5, 0.0, bx + 0.36, 2.4, 0.95, K.COL_NOCAM)
        for k, col in enumerate(("int_ru_uf_blue", "int_ru_red", "int_ru_orange", "int_ru_gator_green")):
            _ball(V, bx, hy1 + 0.16 + 0.24 * k, 0.40 + 0.108, 0.108, col)
        # scorer pedestal (tablet on a post)
        V.box(bx - 0.05, 2.9, 0.0, bx + 0.05, 3.0, 1.05, "int_ru_black", faces="+x-x+y-y")
        V.poly([(bx - 0.18, 2.86, 1.05), (bx + 0.18, 2.86, 1.05), (bx + 0.18, 2.98, 1.30), (bx - 0.18, 2.98, 1.30)],
               "int_ru_score_tv", uvs=K.ONCE, glow=True, normal_hint=(0, 1, 1))
        # square white column between the pairs, behind the approach (ru_gr_lanes_overview_2)
        V.box(bx - 0.3, 3.3, 0.0, bx + 0.3, 3.9, 6.0, "int_ru_white", faces="+x-x+y-y")
        K.col_box(C, bx - 0.3, 3.3, 0.0, bx + 0.3, 3.9, 5.4, K.COL)
    # overhead truss with monitors over the foul line (ru_gr_lanes_truss)
    zt = 4.7                 # fix round 2 (design): raised 0.4 m (the monitors hid Mario on the approaches)
    for yy in (0.4, 1.1):
        V.box(x0, yy - 0.06, zt, x0 + W, yy + 0.06, zt + 0.12, "int_ru_black", faces="+y-y-z+z")
    for k in range(int(W / 1.2)):
        xx = x0 + 0.6 + k * 1.2
        V.box(xx - 0.03, 0.4, zt, xx + 0.03, 1.1, zt + 0.06, "int_ru_black", faces="-z+z")
    for i in range(n_lanes // 2):
        mx = x0 + cap + (2 * i + 1) * pitch - cap / 2
        # big score monitors (ru_gr_lanes_crowd_tvs): ~1.9 m wide, both faces
        V.box(mx - 1.0, 0.70, zt - 1.2, mx + 1.0, 0.80, zt - 0.05, "int_ru_black", faces="+y-y+x-x-z")
        V.poly([(mx - 0.95, 0.81, zt - 1.15), (mx + 0.95, 0.81, zt - 1.15), (mx + 0.95, 0.81, zt - 0.1),
                (mx - 0.95, 0.81, zt - 0.1)], "int_ru_score_tv", uvs=K.uv_rect(1, 0, 0, 1), glow=True,
               normal_hint=(0, 1, 0))
        V.poly([(mx + 0.95, 0.69, zt - 1.15), (mx - 0.95, 0.69, zt - 1.15), (mx - 0.95, 0.69, zt - 0.1),
                (mx + 0.95, 0.69, zt - 0.1)], "int_ru_score_tv", uvs=K.uv_rect(1, 0, 0, 1), glow=True,
               normal_hint=(0, -1, 0))
    P.info.update(width=W, pitch=pitch, pin_y=-lane_len - 0.3, back_y=ypit, lanes_x0=x0)
    for i in range(n_lanes):
        P.anchor(f"lane_{i + 1}_foul", x0 + cap + i * pitch + gut + bed / 2, 0.0, 0.0, 180.0)
        P.anchor(f"lane_{i + 1}_pins", x0 + cap + i * pitch + gut + bed / 2, -lane_len - 0.3, 0.0, 0.0)
    return P


def _ball(V, x, y, z, r, mat, n=8):
    """A low-poly bowling ball: an 8-sided lathe of two rings + the poles (32 triangles)."""
    rings = [(-r, 0.0), (-0.5 * r, 0.866 * r), (0.5 * r, 0.866 * r), (r, 0.0)]
    for (za, ra), (zb, rb) in zip(rings, rings[1:]):
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            pts = [(x + ra * math.cos(a0), y + ra * math.sin(a0), z + za), (x + ra * math.cos(a1), y + ra * math.sin(a1), z + za),
                   (x + rb * math.cos(a1), y + rb * math.sin(a1), z + zb), (x + rb * math.cos(a0), y + rb * math.sin(a0), z + zb)]
            if ra < 1e-9:
                pts = pts[1:]
            elif rb < 1e-9:
                pts = pts[:3]
            am = (a0 + a1) / 2
            V.poly(pts, mat, normal_hint=(math.cos(am), math.sin(am), (za + zb) / (2 * r)))


def booth(length=3.0, depth=0.8, seat_h=0.45, back_h=1.1, curve=True, mat="int_ru_leather_navy", table=True):
    """Navy curved lounge booth (ru_gr_booth_row, ru_gr_booths_bowler): a C-shaped bench with a low back and a
    round low table; front = +y."""
    P = _p("booth")
    V, C = P.visual, P.collision
    n = 7 if curve else 1
    R = length / 2
    pts_in, pts_out = [], []
    for k in range(n + 1):
        a = math.pi + math.pi * k / n if curve else 0
        if curve:
            pts_out.append((R * math.cos(a), 0.6 + R * 0.55 * math.sin(a) * 0.9 + 0.0))
            pts_in.append(((R - depth) * math.cos(a), 0.6 + (R - depth) * 0.55 * math.sin(a) * 0.9))
    if not curve:
        pts_out = [(-R, 0.0), (R, 0.0)]
        pts_in = [(-R, depth), (R, depth)]
    for (a, b), (c, d) in zip(zip(pts_out, pts_out[1:]), zip(pts_in, pts_in[1:])):
        # seat top
        V.poly([(a[0], a[1], seat_h), (b[0], b[1], seat_h), (d[0], d[1], seat_h), (c[0], c[1], seat_h)], mat,
               normal_hint=(0, 0, 1))
        quad_wall(V, d, c, 0.0, seat_h, "int_ru_black")                 # seat front (dark base)
        # back: outer edge, thin
        quad_wall(V, b, a, seat_h, back_h, mat)                         # back face toward the seat
        quad_wall(V, a, b, 0.12, back_h, mat)                           # outside (navy, ru_gr_lanes_overview_2)
        quad_wall(V, a, b, 0.0, 0.12, "int_ru_black")
        V.poly([(a[0], a[1], back_h), (b[0], b[1], back_h), (b[0] + (d[0] - b[0]) * 0.18, b[1] + (d[1] - b[1]) * 0.18,
                back_h), (a[0] + (c[0] - a[0]) * 0.18, a[1] + (c[1] - a[1]) * 0.18, back_h)], mat,
               normal_hint=(0, 0, 1))
    xs = [p[0] for p in pts_out + pts_in]
    ys = [p[1] for p in pts_out + pts_in]
    K.col_box(C, min(xs), min(ys), 0.0, max(xs), max(ys), seat_h, K.COL_NOCAM)
    if table:
        ty = 0.6 + 0.2 if curve else depth + 0.7
        cyl(V, 0.0, ty, 0.45, 0.38, 0.44, "int_ru_leather_grey", n=8)
        cyl(V, 0.0, ty, 0.12, 0.0, 0.38, "int_ru_black", n=6, top=False)
    P.info["top_z"] = seat_h
    return P


def ball_rack(L=1.2, front_only=False):
    """Black ball rack with two shelves of coloured house balls (ru_gr_ball_rack, ru_gr_lanes_overview_2).
    front_only: collision is only the -y face and the top (design pass: the racks stand in the 0.39 m gaps between
    the booth pits, whose own boxes already block their sides and backs; saves 6 tris a rack)."""
    P = _p("ball_rack")
    V, C = P.visual, P.collision
    # fidelity-3 (round 2; ru_gr_ball_rack, ru_gr_lanes_overview_2): an OPEN frame (black end panels, a plinth and
    # two dished shelves on rails, open long sides) holding two rows of round 8-sided balls (_ball), so both shelves
    # show; the closed box hid the lower row and the 0.22 m cubes read as toy blocks
    for ye in (-L / 2, L / 2 - 0.04):
        V.box(-0.25, ye, 0.0, 0.25, ye + 0.04, 0.9, "int_ru_black", faces="+x-x+y-y+z")
    V.box(-0.25, -L / 2 + 0.04, 0.0, 0.25, L / 2 - 0.04, 0.1, "int_ru_black", faces="+x-x+z")
    cols = ("int_ru_red", "int_ru_uf_blue", "int_ru_orange", "int_ru_gator_green", "int_ru_fabric_plum", "int_ru_white")
    r_ = 0.108
    for shelf, zb in enumerate((0.36, 0.8)):
        for sx in (-0.12, 0.12):                              # the two rails of each shelf
            V.box(sx - 0.015, -L / 2 + 0.04, zb - 0.03, sx + 0.015, L / 2 - 0.04, zb, "int_ru_steel", faces="+x-x+z")
        for k in range(4):
            y = -L / 2 + 0.18 + k * (L - 0.36) / 3
            _ball(V, 0.0, y, zb + r_ - 0.02, r_, cols[(k + shelf * 3) % len(cols)])
    if front_only:
        C.poly([(-0.25, -L / 2, 0.0), (0.25, -L / 2, 0.0), (0.25, -L / 2, 0.9), (-0.25, -L / 2, 0.9)], K.COL_NOCAM,
               normal_hint=(0, -1, 0))
        C.poly([(-0.25, -L / 2, 0.9), (0.25, -L / 2, 0.9), (0.25, L / 2, 0.9), (-0.25, L / 2, 0.9)], K.COL_NOCAM,
               normal_hint=(0, 0, 1))
    else:
        K.col_box(C, -0.25, -L / 2, 0.0, 0.25, L / 2, 0.9, K.COL_NOCAM)
    return P


def cue_rack():
    """Wall cue rack (ru_gr_billiards_room): a row of pale cue sticks on a wood rail."""
    P = _p("cue_rack")
    V = P.visual
    V.box(-0.45, 0.0, 1.30, 0.45, 0.06, 1.38, "int_ru_wood_panel", faces="+x-x+y+z")
    for k in range(9):
        x = -0.4 + k * 0.1
        V.box(x - 0.012, 0.03, 0.15, x + 0.012, 0.06, 1.55, "int_wood", faces="+y+x-x")
    return P


def billiard_table(L=2.84, W=1.57, h=0.79, base="int_ru_espresso"):
    """9-ft table (ru_gr_billiards_room): blue felt, near-black espresso mahogany rails / apron / heavy legs (fix round
    5, fidelity-3: int_ru_cherry read bright orange against the photo's (36,15,13)); long axis = local x."""
    P = _p("billiards")
    V, C = P.visual, P.collision
    rw = 0.16
    V.box(-L / 2 + rw, -W / 2 + rw, h - 0.02, L / 2 - rw, W / 2 - rw, h, "int_ru_felt", faces="+z")
    for (x0, y0, x1, y1) in ((-L / 2, -W / 2, L / 2, -W / 2 + rw), (-L / 2, W / 2 - rw, L / 2, W / 2),
                             (-L / 2, -W / 2 + rw, -L / 2 + rw, W / 2 - rw), (L / 2 - rw, -W / 2 + rw, L / 2, W / 2 - rw)):
        V.box(x0, y0, h - 0.12, x1, y1, h + 0.04, "int_ru_espresso", faces="+x-x+y-y+z")
    V.box(-L / 2 + 0.1, -W / 2 + 0.1, h - 0.32, L / 2 - 0.1, W / 2 - 0.1, h - 0.12, base,
          faces="+x-x+y-y-z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * L * 0.38 - 0.11, sy * W * 0.3 - 0.11, 0.0, sx * L * 0.38 + 0.11, sy * W * 0.3 + 0.11, h - 0.32,
                  base, faces="+x-x+y-y")
    # balls (a triangle rack + cue ball)
    for k, (bx, by) in enumerate([(0.6, 0), (0.66, 0.035), (0.66, -0.035), (0.72, 0.07), (0.72, 0), (0.72, -0.07),
                                  (-0.6, 0.0)]):
        col = ["int_ru_orange", "int_ru_uf_blue", "int_ru_red", "int_ru_gator_green", "int_ru_black",
               "int_ru_orange", "int_ru_white"][k]
        V.box(bx - 0.028, by - 0.028, h, bx + 0.028, by + 0.028, h + 0.056, col, faces="+x-x+y-y+z")
    K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h + 0.04, K.COL_NOCAM)
    P.info["top_z"] = h + 0.04
    return P


def led_frame(w, d, z, t=0.08):
    """Square LED ring light frame over a billiards table (ru_gr_billiards_room): white glowing bar."""
    P = _p("led_frame")
    V = P.visual
    for (x0, y0, x1, y1) in ((-w / 2, -d / 2, w / 2, -d / 2 + t), (-w / 2, d / 2 - t, w / 2, d / 2),
                             (-w / 2, -d / 2, -w / 2 + t, d / 2), (w / 2 - t, -d / 2, w / 2, d / 2)):
        V.box(x0, y0, z - 0.06, x1, y1, z, "int_ru_led", faces="-z+x-x+y-y", glow=True)
    P.lights.append(K.Light((0.0, 0.0, z - 0.3), radius=4.0, strength=0.30, color=(0.96, 0.98, 1.0)))
    return P


def arcade_cabinet(side="int_ru_arcade", marquee=(1.0, 0.85, 0.4)):
    P = _p("arcade")
    V, C = P.visual, P.collision
    w, d, h = 0.72, 0.85, 1.85
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_ru_black", faces="+y-y+z")
    for sx in (-1, 1):
        x = sx * w / 2
        pts = [(x, -d / 2, 0.0), (x, d / 2, 0.0), (x, d / 2, h), (x, -d / 2, h)]
        if sx < 0:
            pts = list(reversed(pts))
        V.poly(pts, side, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if sx > 0 else [(1, 1), (1, 0), (0, 0), (0, 1)][::-1],
               normal_hint=(sx, 0, 0))
    # screen IN FRONT of the cabinet's +y face, leaning back (bottom 14 cm out, top 3 cm out)
    V.poly([(-w / 2 + 0.06, d / 2 + 0.14, 1.05), (w / 2 - 0.06, d / 2 + 0.14, 1.05), (w / 2 - 0.06, d / 2 + 0.03, 1.55),
            (-w / 2 + 0.06, d / 2 + 0.03, 1.55)], "int_ru_game_screen", uvs=K.uv_rect(1, 0, 0, 1), glow=True,
           normal_hint=(0, 1, 0.22))
    V.box(-w / 2, d / 2, 0.85, w / 2, d / 2 + 0.25, 0.95, "int_ru_black", faces="+y+z+x-x")
    V.poly([(-w / 2 + 0.04, d / 2 + 0.03, 1.62), (w / 2 - 0.04, d / 2 + 0.03, 1.62), (w / 2 - 0.04, d / 2 + 0.03, 1.80),
            (-w / 2 + 0.04, d / 2 + 0.03, 1.80)], "int_ru_led", glow=True, tint=marquee, normal_hint=(0, 1, 0))
    K.col_box(C, -w / 2, -d / 2, 0.0, w / 2, d / 2 + 0.25, h, K.COL_NOCAM)
    return P


def ping_pong():
    """Table tennis table (ru_gr_ping_pong). fix round 4 (design pass, improvement 6): from 15 m the plain blue slab
    read as a rug on the floor: a white 5 cm edge frame and a 4 cm centre line (2 cm proud of the blue top, no
    coplanar faces), a dark net 15 cm tall with a white headband and its posts past the sides, a dark apron."""
    P = _p("ping_pong")
    V, C = P.visual, P.collision
    L, W, h = 2.74, 1.525, 0.76
    e, dz = 0.05, 0.02
    V.box(-W / 2, -L / 2, h - 0.04, W / 2, L / 2, h, "int_ru_uf_blue", faces="+z")
    V.box(-W / 2, -L / 2, h - 0.04, W / 2, L / 2, h + dz, "int_ru_black", faces="+x-x+y-y")
    # white edge frame + centre line (raised dz over the blue)
    V.box(-W / 2, -L / 2, h, -W / 2 + e, L / 2, h + dz, "int_ru_white", faces="+z")
    V.box(W / 2 - e, -L / 2, h, W / 2, L / 2, h + dz, "int_ru_white", faces="+z")
    V.box(-W / 2 + e, -L / 2, h, W / 2 - e, -L / 2 + e, h + dz, "int_ru_white", faces="+z")
    V.box(-W / 2 + e, L / 2 - e, h, W / 2 - e, L / 2, h + dz, "int_ru_white", faces="+z")
    V.box(-0.02, -L / 2 + e, h, 0.02, L / 2 - e, h + dz, "int_ru_white", faces="+z")
    # net: dark mesh band with a white headband, posts 15 cm past each side
    V.box(-W / 2 - 0.15, -0.006, h + dz, W / 2 + 0.15, 0.006, h + 0.13, "int_ru_black", faces="+y-y")
    V.box(-W / 2 - 0.15, -0.008, h + 0.13, W / 2 + 0.15, 0.008, h + 0.1525, "int_ru_white", faces="+y-y+z")
    for sx in (-1, 1):
        x = sx * (W / 2 + 0.15)
        V.box(x - 0.015, -0.03, h - 0.04, x + 0.015, 0.03, h + 0.16, "int_ru_steel", faces="+x-x+y-y+z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * W * 0.4 - 0.03, sy * L * 0.4 - 0.03, 0.0, sx * W * 0.4 + 0.03, sy * L * 0.4 + 0.03, h - 0.04,
                  "int_ru_steel", faces="+x-x+y-y")
    K.col_box(C, -W / 2, -L / 2, 0.0, W / 2, L / 2, h, K.COL_NOCAM)
    return P


def air_hockey():
    """fix round 4 (design pass, improvement 6): the centre line was coplanar with the blue playfield (z-fight) and the
    black rim had no top: a raised black rail frame (3 cm) around the blue field, a white centre line and the two
    face-off bars 2 cm proud, dark goal slots in the end rails."""
    P = _p("air_hockey")
    V, C = P.visual, P.collision
    L, W, h = 2.3, 1.2, 0.8
    r, dz = 0.08, 0.02
    V.box(-W / 2, -L / 2, 0.0, W / 2, L / 2, h + 0.03, "int_ru_black", faces="+x-x+y-y")
    V.box(-W / 2 + r, -L / 2 + r, h - 0.02, W / 2 - r, L / 2 - r, h, "int_ru_uf_blue", faces="+z")
    # rails (tops at h + 0.03; their inner faces drop to the field)
    V.box(-W / 2, -L / 2, h, -W / 2 + r, L / 2, h + 0.03, "int_ru_black", faces="+z+x")
    V.box(W / 2 - r, -L / 2, h, W / 2, L / 2, h + 0.03, "int_ru_black", faces="+z-x")
    for sy in (-1, 1):
        y0, y1 = (-L / 2, -L / 2 + r) if sy < 0 else (L / 2 - r, L / 2)
        V.box(-W / 2 + r, y0, h, W / 2 - r, y1, h + 0.03, "int_ru_black", faces="+z" + ("+y" if sy < 0 else "-y"))
        V.box(-0.2, y0 + 0.02, h + 0.03, 0.2, y1 - 0.02, h + 0.03 + dz, "int_ru_steel", faces="+z")    # goal slot lip
    V.box(-W / 2 + r, -0.02, h, W / 2 - r, 0.02, h + dz, "int_ru_white", faces="+z")       # centre line
    for sy in (-1, 1):
        y = sy * (L / 2 - r - 0.45)
        V.box(-0.25, y - 0.015, h, 0.25, y + 0.015, h + dz, "int_ru_white", faces="+z")
    K.col_box(C, -W / 2, -L / 2, 0.0, W / 2, L / 2, h, K.COL_NOCAM)
    return P


def foosball():
    P = _p("foosball")
    V, C = P.visual, P.collision
    L, W, h = 1.4, 0.75, 0.9
    V.box(-L / 2, -W / 2, 0.55, L / 2, W / 2, h, "int_ru_white", faces="+x-x+y-y")
    V.box(-L / 2 + 0.05, -W / 2 + 0.05, 0.6, L / 2 - 0.05, W / 2 - 0.05, 0.62, "int_ru_gator_green", faces="+z")
    for k in range(8):
        x = -L / 2 + 0.15 + k * (L - 0.3) / 7
        V.box(x - 0.012, -W / 2 - 0.15, 0.82, x + 0.012, W / 2 + 0.15, 0.845, "int_ru_steel", faces="+z+y-y")
        V.box(x - 0.03, -0.1, 0.66, x + 0.03, 0.1, 0.82, "int_ru_orange" if k % 2 else "int_ru_uf_blue",
              faces="+x-x+y-y")
    for sx in (-1, 1):
        V.box(sx * L * 0.42 - 0.05, -W * 0.4, 0.0, sx * L * 0.42 + 0.05, W * 0.4, 0.55, "int_ru_black", faces="+x-x+y-y")
    K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def esports_row(n=6, seat_w=0.95, depth=0.75, h=0.75, double=True):
    """Gator Esports Center PC row (ru_es_oelrich_9050/9352, ru_es_pods): black desks with blue edge light,
    monitor per seat, black gaming chairs; double = back to back with a centre screen divider."""
    P = _p("esports_row", n=n)
    V, C = P.visual, P.collision
    L = n * seat_w
    sides = (1, -1) if double else (1,)
    for s in sides:
        y0, y1 = (0.05, depth) if s > 0 else (-depth, -0.05)
        V.box(-L / 2, y0, h - 0.04, L / 2, y1, h, "int_ru_black", faces="+z+x-x" + ("+y" if s > 0 else "-y"))
        ye = y1 if s > 0 else y0
        V.box(-L / 2, ye - 0.01, h - 0.06, L / 2, ye + 0.01, h - 0.02, "int_ru_led", faces="+y" if s > 0 else "-y",
              glow=True, tint=(0.35, 0.55, 1.0))
        V.box(-L / 2, min(y0, y1) + 0.1, 0.0, -L / 2 + 0.04, max(y0, y1) - 0.1, h - 0.04, "int_ru_black", faces="+x-x")
        V.box(L / 2 - 0.04, min(y0, y1) + 0.1, 0.0, L / 2, max(y0, y1) - 0.1, h - 0.04, "int_ru_black", faces="+x-x")
        for k in range(n):
            x = -L / 2 + seat_w * (k + 0.5)
            yy = 0.22 if s > 0 else -0.22
            # monitor facing the seat
            mpts = [(x - 0.32, yy, h + 0.12), (x + 0.32, yy, h + 0.12), (x + 0.32, yy, h + 0.52), (x - 0.32, yy, h + 0.52)]
            if s < 0:
                mpts = [mpts[1], mpts[0], mpts[3], mpts[2]]
            V.poly(mpts, "int_ru_game_screen", uvs=K.uv_rect(0, 0, 1, 1), glow=True, normal_hint=(0, s, 0))
            V.box(x - 0.34, yy - 0.04 * s if s > 0 else yy, h + 0.10, x + 0.34, yy if s > 0 else yy + 0.04, h + 0.54,
                  "int_ru_black", faces="-y" if s > 0 else "+y")
            # chair
            cy = (depth + 0.45) * s
            V.box(x - 0.26, cy - 0.25, 0.42, x + 0.26, cy + 0.25, 0.50, "int_ru_black", faces="+z+x-x+y-y")
            by = cy + 0.25 * s
            V.box(x - 0.24, min(by, by + 0.08 * s), 0.5, x + 0.24, max(by, by + 0.08 * s), 1.25, "int_ru_black",
                  faces="+x-x+y-y+z")
            # fidelity-3 (round 2; ru_es_overview, ru_es_oelrich_9352): all-black gaming chairs (the red back panel
            # is gone); a dark-grey headrest band keeps the back readable against the black desks
            V.box(x - 0.2, by + (0.081 * s if s > 0 else -0.001), 1.08, x + 0.2,
                  by + (0.082 * s if s > 0 else 0.0), 1.2, "int_ru_fabric_char", faces="+y" if s > 0 else "-y")
            V.box(x - 0.03, cy - 0.03, 0.0, x + 0.03, cy + 0.03, 0.42, "int_ru_steel", faces="+x-x+y-y")
    if double:
        V.box(-L / 2, -0.05, 0.0, L / 2, 0.05, h + 0.6, "int_ru_black", faces="+x-x+y-y+z")
    K.col_box(C, -L / 2, -depth if double else 0.05, 0.0, L / 2, depth, h, K.COL_NOCAM)
    return P


def lounge_chair(mat="int_ru_fabric_navy", seat="int_ru_fabric_taupe", w=0.85, d=0.85, swivel=False, col=True, arm=None,
                 back=None, cap=None):
    """Atrium club chair (ru_atrium_enr_lounge): navy shell / taupe cushion, or the orange swivel tub chair.
    arm: a material for the side panels (fix round 4: the photo's chairs have tan wood side panels)."""
    P = _p("lounge_chair")
    V, C = P.visual, P.collision
    if swivel:
        cyl(V, 0.0, 0.0, 0.42, 0.25, 0.48, mat, n=8)
        pts = [(0.44 * math.cos(math.radians(a)), 0.44 * math.sin(math.radians(a))) for a in range(200, 341, 28)]
        for a, b in zip(pts, pts[1:]):
            quad_wall(V, b, a, 0.48, 0.85, mat)
            quad_wall(V, a, b, 0.25, 0.85, mat)
        cyl(V, 0.0, 0.0, 0.08, 0.0, 0.25, "int_ru_steel", n=6, top=False)
        if col:
            K.col_box(C, -0.42, -0.42, 0.0, 0.42, 0.42, 0.48, K.COL_NOCAM)
        return P
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, 0.42, mat, faces="+x-x+y-y")
    V.box(-w / 2 + 0.16, -d / 2 + 0.2, 0.42, w / 2 - 0.16, d / 2, 0.48, seat, faces="+z+y")
    V.box(-w / 2, -d / 2, 0.42, w / 2, -d / 2 + 0.2, 0.82, back or mat, faces="+x-x+y-y+z")
    for sx in (-1, 1):
        V.box(sx * w / 2 - (0.16 if sx > 0 else 0), -d / 2 + 0.2, 0.42, sx * w / 2 + (0 if sx > 0 else 0.16), d / 2,
              0.64, arm or mat, faces="+x-x+y" + ("" if cap else "+z"))
        if cap:     # user-photo pass (user_06, B08): maple arm caps
            V.box(sx * w / 2 - (0.17 if sx > 0 else -0.01), -d / 2 + 0.2, 0.64, sx * w / 2 + (-0.01 if sx > 0 else 0.17),
                  d / 2 + 0.01, 0.675, cap, faces="+x-x+y+z")
    if col:
        K.col_box(C, -w / 2, -d / 2, 0.0, w / 2, d / 2, 0.48, K.COL_NOCAM)
    P.info["top_z"] = 0.48
    return P


def lounge_sofa(L=1.75, mat="int_ru_fabric_navy", seat="int_ru_leather_navy", arm="int_ru_wood_tan", d=0.85,
                col=False):
    """fix round 4 (fidelity-1, ru_atrium_enr_lounge): the lounge's 2-3 seat navy sofa: navy base and back, navy
    seat cushions (one per seat, a shade lighter), tan wood side panels. Local: front = +y, the back along -y."""
    P = _p("lounge_sofa")
    V, C = P.visual, P.collision
    a = 0.14                                   # wood side panel thickness
    V.box(-L / 2 + a, -d / 2, 0.0, L / 2 - a, d / 2, 0.40, mat, faces="+y-y")
    V.box(-L / 2 + a, -d / 2, 0.40, L / 2 - a, -d / 2 + 0.22, 0.84, mat, faces="+y-y+z")
    n = 2 if L < 2.1 else 3
    cw = (L - 2 * a) / n
    for i in range(n):
        x0 = -L / 2 + a + i * cw
        V.box(x0 + 0.015, -d / 2 + 0.22, 0.40, x0 + cw - 0.015, d / 2 - 0.02, 0.50, seat, faces="+z+y+x-x")
    for sx in (-1, 1):
        x0, x1 = (L / 2 - a, L / 2) if sx > 0 else (-L / 2, -L / 2 + a)
        V.box(x0, -d / 2, 0.0, x1, d / 2, 0.64, arm, faces="+x-x+y-y+z")
    if col:
        K.col_box(C, -L / 2, -d / 2, 0.0, L / 2, d / 2, 0.5, K.COL_NOCAM)
    P.info["top_z"] = 0.5
    return P


def swivel_highback(col=False):
    """user-photo pass (B08, B09, C01): the lounge's orange high-back swivel chair: a 5-arm chrome star base,
    a post, a seat disc with a royal-blue cushion and a 5-facet orange shell rising from 0.40 m to 1.15 m at the back
    (lower at the sides). Front = +y."""
    P = _p("swivel_highback")
    V, C = P.visual, P.collision
    for k in range(5):
        a = math.radians(90.0 + 72.0 * k)
        seg_box(V, (0.0, 0.0), (0.3 * math.cos(a), 0.3 * math.sin(a)), 0.025, 0.02, 0.06, "int_ru_steel_bright",
                faces="sidetop")
    cyl(V, 0.0, 0.0, 0.035, 0.06, 0.38, "int_ru_steel_bright", n=4, top=False)
    cyl(V, 0.0, 0.0, 0.32, 0.38, 0.44, "int_ru_fabric_orange", n=8, top=False)
    cyl(V, 0.0, 0.02, 0.28, 0.44, 0.48, "int_ru_uf_blue", n=8, top=True)
    angs = [190.0 + 32.0 * k for k in range(6)]
    pts = [(0.34 * math.cos(math.radians(a)), 0.34 * math.sin(math.radians(a))) for a in angs]
    tops = [0.40 + 0.75 * (0.55 + 0.45 * math.sin(math.radians(-a))) for a in angs]
    for (a, za), (b, zb) in zip(zip(pts, tops), zip(pts[1:], tops[1:])):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        L_ = math.hypot(mx, my)
        V.poly([(a[0], a[1], 0.40), (b[0], b[1], 0.40), (b[0], b[1], zb), (a[0], a[1], za)], "int_ru_fabric_orange",
               normal_hint=(mx / L_, my / L_, 0.0))
        V.poly([(b[0], b[1], 0.40), (a[0], a[1], 0.40), (a[0], a[1], za), (b[0], b[1], zb)], "int_ru_fabric_orange",
               normal_hint=(-mx / L_, -my / L_, 0.0), ao=0.85)
    if col:
        K.col_box(C, -0.36, -0.36, 0.0, 0.36, 0.36, 0.48, K.COL_NOCAM)
    P.info["top_z"] = 0.48
    return P


def rocking_chair(mat="int_ru_white"):
    """user-photo pass (B05, B06, C01): a white wooden rocking chair (the four in front of the L1 north
    curtain wall): two 4-segment arc rockers 0.9 m long, legs, a seat at 0.42 m, arms at 0.62 m, two back posts and four
    spindles up to 1.05 m. Front = +y. Visual only."""
    P = _p("rocking_chair")
    V = P.visual
    for sx in (-0.25, 0.25):
        prev = None
        for k in range(5):
            u = -0.45 + 0.9 * k / 4.0
            z_ = 0.03 + 0.09 * (u / 0.45) ** 2
            cur = (sx, u, z_)
            if prev is not None:
                for sg in (1, -1):
                    q = [(sx, prev[1], prev[2]), (sx, cur[1], cur[2]), (sx, cur[1], cur[2] + 0.05),
                         (sx, prev[1], prev[2] + 0.05)]
                    V.poly(q if sg > 0 else list(reversed(q)), mat, normal_hint=(sg, 0.0, 0.0))
            prev = cur
        for uy in (-0.2, 0.2):
            cyl(V, sx, uy, 0.025, 0.06, 0.42, mat, n=3, top=False)
    V.box(-0.27, -0.24, 0.40, 0.27, 0.24, 0.44, mat, faces="+x-x+y-y+z")
    for sx in (-1, 1):
        seg_box(V, (sx * 0.28, -0.22), (sx * 0.28, 0.24), 0.03, 0.60, 0.64, mat, faces="sidetop")
        cyl(V, sx * 0.25, -0.22, 0.03, 0.44, 1.05, mat, n=3, top=True)
    V.box(-0.27, -0.25, 0.97, 0.27, -0.19, 1.07, mat, faces="+x-x+y-y+z")
    for k in range(4):
        x_ = -0.15 + 0.1 * k
        for sg in (1, -1):
            q = [(x_ - 0.012, -0.22, 0.44), (x_ + 0.012, -0.22, 0.44), (x_ + 0.012, -0.22, 0.97), (x_ - 0.012, -0.22, 0.97)]
            V.poly(q if sg > 0 else list(reversed(q)), mat, normal_hint=(0.0, -sg, 0.0))
    return P


def coffee_table(L=1.2, W=0.7, h=0.42, mat="int_ru_fabric_taupe", col=True, top="int_ru_leather_grey"):
    P = _p("coffee_table")
    V, C = P.visual, P.collision
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, mat, faces="+x-x+y-y+z", mats={"+z": top})
    if col:
        K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def round_table(r=0.9, h=0.75, top="int_ru_tablecloth", chairs=8, chair_mat="int_ru_fabric_navy", seats=True,
                pedestal=False, leg_mat="int_ru_steel"):
    """Banquet round table (ru_os_grand_ballroom_3/4, ru_os_matthews_1) with chairs around it.
    fix round 5 (fidelity-4; ru_os_matthews_1/2): pedestal=True is a bare white top on a pedestal (no floor-length
    drum) with banquet chairs that have a 5 cm thick padded back and four silver legs (the zero-thickness backs read
    as scattered navy cards at the gameplay camera). The default (Grand Ballroom: black-draped drums) is unchanged."""
    P = _p("round_table")
    V, C = P.visual, P.collision
    if pedestal:
        cyl(V, 0.0, 0.0, r, h - 0.04, h, top, n=10, bottom=True)
        cyl(V, 0.0, 0.0, 0.06, 0.05, h - 0.04, leg_mat, n=6, top=False)
        cyl(V, 0.0, 0.0, 0.32, 0.0, 0.05, leg_mat, n=8)
    else:
        cyl(V, 0.0, 0.0, r, h - 0.3, h, top, n=10)
        cyl(V, 0.0, 0.0, r * 0.95, 0.0, h - 0.3, top, n=10, top=False)
    if seats and pedestal:
        for k in range(chairs):
            a = 2 * math.pi * k / chairs
            cx, cy = (r + 0.4) * math.cos(a), (r + 0.4) * math.sin(a)
            fx, fy = -math.cos(a), -math.sin(a)
            tx, ty = -fy, fx

            def at(u, v, cx=cx, cy=cy, fx=fx, fy=fy, tx=tx, ty=ty):
                return (cx + tx * u + fx * v, cy + ty * u + fy * v)
            seat = [at(0.22, -0.22), at(-0.22, -0.22), at(-0.22, 0.22), at(0.22, 0.22)]
            prism(V, seat, 0.40, 0.47, chair_mat, top=chair_mat)
            back = [at(0.21, -0.22), at(-0.21, -0.22), at(-0.21, -0.17), at(0.21, -0.17)]
            prism(V, back, 0.47, 1.0, chair_mat, top=chair_mat)
            for u_, v_ in ((0.19, -0.19), (-0.19, -0.19), (-0.19, 0.19), (0.19, 0.19)):
                p_ = at(u_, v_)
                cyl(V, p_[0], p_[1], 0.016, 0.0, 0.40, leg_mat, n=4, top=False)
    elif seats:
        for k in range(chairs):
            a = 2 * math.pi * k / chairs
            cx, cy = (r + 0.4) * math.cos(a), (r + 0.4) * math.sin(a)
            fx, fy = -math.cos(a), -math.sin(a)
            tx, ty = -fy, fx
            s = [(cx + tx * 0.22 - fx * 0.22, cy + ty * 0.22 - fy * 0.22), (cx - tx * 0.22 - fx * 0.22, cy - ty * 0.22 - fy * 0.22),
                 (cx - tx * 0.22 + fx * 0.22, cy - ty * 0.22 + fy * 0.22), (cx + tx * 0.22 + fx * 0.22, cy + ty * 0.22 + fy * 0.22)]
            V.poly([(p[0], p[1], 0.46) for p in s], chair_mat, normal_hint=(0, 0, 1))
            b0, b1 = s[0], s[1]
            quad_wall(V, b1, b0, 0.0, 0.46, "int_ru_black")
            # back panel (both faces)
            V.poly([(b0[0], b0[1], 0.46), (b1[0], b1[1], 0.46), (b1[0], b1[1], 1.0), (b0[0], b0[1], 1.0)], chair_mat,
                   normal_hint=(-fx, -fy, 0))
            V.poly([(b1[0], b1[1], 0.46), (b0[0], b0[1], 0.46), (b0[0], b0[1], 1.0), (b1[0], b1[1], 1.0)], chair_mat,
                   normal_hint=(fx, fy, 0))
    K.col_box(C, -r, -r, 0.0, r, r, h, K.COL_NOCAM)
    P.info["top_z"] = h
    return P


def chair_rows(rows, per_row, pitch=0.95, seat_w=0.5, aisle_every=0, aisle_w=1.2, kind="navy", seat_h=0.46,
               col_blocks=False):
    """Theatre-style chair rows (ballrooms, meeting rooms): each row = a seat strip + a cut-out back panel of
    chairs (int_ru_row_*: 4 chairs per texture repeat). Local: rows go toward -y (row 0 at y = 0, facing +y),
    centred in x. Collision: one low box over all the rows (no-cam); col_blocks=True: one box per seat block, so
    the aisles between the blocks stay walkable floor (design pass: the Grand Ballroom's aisles to the stage)."""
    P = _p("chair_rows", rows=rows, per_row=per_row)
    V, C = P.visual, P.collision
    mat = {"navy": "int_ru_row_navy", "black": "int_ru_row_black", "aud": "int_ru_row_aud",
           "wood": "int_ru_row_wood", "rion": "int_ru_row_rion"}[kind]
    # the auditorium's seats have honey-wood shells: seen from behind they read as wood (ru_os_auditorium_3)
    rear = "int_ru_row_wood" if kind == "aud" else mat
    seat_mat = {"navy": "int_ru_fabric_navy", "black": "int_ru_black", "aud": "int_ru_fabric_navy",
                "wood": "int_ru_fabric_navy", "rion": "int_ru_fabric_navy"}[kind]
    blocks = []
    if aisle_every:
        n_blocks = int(math.ceil(per_row / aisle_every))
        for b in range(n_blocks):
            blocks.append(min(aisle_every, per_row - b * aisle_every))
    else:
        blocks = [per_row]
    W = sum(blocks) * seat_w + (len(blocks) - 1) * aisle_w
    for r in range(rows):
        y = -r * pitch
        x = -W / 2
        for nb in blocks:
            w = nb * seat_w
            # seat strip
            if kind == "black":
                # fix round 5 (fidelity-4, improvement 6): per-seat gaps in the texture (no extra triangles)
                V.poly([(x, y - 0.45, seat_h), (x + w, y - 0.45, seat_h), (x + w, y, seat_h), (x, y, seat_h)],
                       "int_ru_seatrow_black", uvs=[(0, 0), (nb / 4.0, 0), (nb / 4.0, 0.7), (0, 0.7)],
                       normal_hint=(0, 0, 1))
                V.poly([(x + w, y, seat_h - 0.06), (x, y, seat_h - 0.06), (x, y, seat_h), (x + w, y, seat_h)],
                       "int_ru_seatrow_black", uvs=[(nb / 4.0, 0.7), (0, 0.7), (0, 1.0), (nb / 4.0, 1.0)],
                       normal_hint=(0, 1, 0))
            else:
                V.box(x, y - 0.45, seat_h - 0.06, x + w, y, seat_h, seat_mat, faces="+z+y")
            # back panel at the rear edge (seen from the back: rear face; from the front: the front face)
            yb = y - 0.45
            V.poly([(x, yb, 0.0), (x + w, yb, 0.0), (x + w, yb, 1.0), (x, yb, 1.0)], rear,
                   uvs=[(0, 0), (nb / 4.0, 0), (nb / 4.0, 1), (0, 1)], normal_hint=(0, -1, 0))
            V.poly([(x + w, yb + 0.02, 0.0), (x, yb + 0.02, 0.0), (x, yb + 0.02, 1.0), (x + w, yb + 0.02, 1.0)], mat,
                   uvs=[(0, 0), (nb / 4.0, 0), (nb / 4.0, 1), (0, 1)], normal_hint=(0, 1, 0))
            x += w + aisle_w
    if col_blocks and len(blocks) > 1:
        x = -W / 2
        for nb in blocks:
            K.col_box(C, x, -(rows - 1) * pitch - 0.45, 0.0, x + nb * seat_w, 0.0, seat_h, K.COL_NOCAM)
            x += nb * seat_w + aisle_w
    else:
        K.col_box(C, -W / 2, -(rows - 1) * pitch - 0.45, 0.0, W / 2, 0.0, seat_h, K.COL_NOCAM)
    P.info.update(width=W, depth=(rows - 1) * pitch + 0.45)
    return P


def draped_table(L=1.8, W=0.75, h=0.76, mat="int_ru_tablecloth"):
    P = _p("draped_table")
    V, C = P.visual, P.collision
    V.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, h, mat, faces="+x-x+y-y+z")
    return P


def office_chair(V, x, y, back="int_ru_fabric_char"):
    """Black high-back mesh office chair on casters (ru_os_3305, ru_os_3310, ru_os_2345_2350; fidelity-4 round 2),
    seat centre (x, y), facing +y: a cross caster base, a gas column, a padded seat, armrests and a tall mesh back
    on a black frame. Visual only (~70 triangles)."""
    for ax, ay in ((0.27, 0.035), (0.035, 0.27)):
        V.box(x - ax, y - ay, 0.0, x + ax, y + ay, 0.07, "int_ru_black", faces="+x-x+y-y+z")
    V.box(x - 0.03, y - 0.03, 0.07, x + 0.03, y + 0.03, 0.40, "int_ru_steel", faces="+x-x+y-y")
    V.box(x - 0.25, y - 0.23, 0.40, x + 0.25, y + 0.25, 0.48, "int_ru_black", faces="+x-x+y-y+z")
    for sx in (-1, 1):
        ax = x + sx * 0.28
        V.box(ax - 0.025, y - 0.06, 0.48, ax + 0.025, y - 0.02, 0.64, "int_ru_black", faces="+x-x")
        V.box(ax - 0.03, y - 0.20, 0.64, ax + 0.03, y + 0.12, 0.68, "int_ru_black", faces="+x-x+z")
    # back: black spine, mesh panel (front) on a black rear face, a little wider at the top (high-back)
    V.box(x - 0.04, y - 0.33, 0.40, x + 0.04, y - 0.27, 0.60, "int_ru_black", faces="-y+x-x")
    yb = y - 0.30
    V.poly([(x - 0.22, yb, 0.56), (x + 0.22, yb, 0.56), (x + 0.24, yb - 0.04, 1.18), (x - 0.24, yb - 0.04, 1.18)],
           back, normal_hint=(0, 1, 0))
    V.poly([(x + 0.22, yb - 0.01, 0.56), (x - 0.22, yb - 0.01, 0.56), (x - 0.24, yb - 0.05, 1.18),
            (x + 0.24, yb - 0.05, 1.18)], "int_ru_black", normal_hint=(0, -1, 0))
    V.box(x - 0.25, yb - 0.07, 1.15, x + 0.25, yb + 0.01, 1.21, "int_ru_black", faces="+y-y+z")


def folding_table(L=1.8, W=0.6, h=0.74, top="int_ru_wall_cream", chairs=3, chair="stack", chair_mat="int_ru_black"):
    """Classroom training table (ru_os_g325, ru_os_3305): light top, chrome legs, black chairs behind.
    chair="office": black high-back mesh office chairs on casters instead of stacking chairs (fidelity-4 round 2:
    the 3305 U, the 3310 hollow square and the 2345 / 2350 boardroom tables)."""
    P = _p("folding_table")
    V, C = P.visual, P.collision
    # fix round 4 (fidelity-3; ru_os_g325): a thin 3 cm top on four slim chrome posts (the full-width end panels
    # read as solid white benches); visual only, the merged collision box below is unchanged
    V.box(-L / 2, -W / 2, h - 0.03, L / 2, W / 2, h, top, faces="+x-x+y-y+z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            px_, py_ = sx * (L / 2 - 0.1), sy * (W / 2 - 0.07)
            V.box(px_ - 0.02, py_ - 0.02, 0.0, px_ + 0.02, py_ + 0.02, h - 0.03, "int_ru_steel", faces="+x-x+y-y")
    for k in range(chairs):
        x = -L / 2 + L * (k + 0.5) / chairs
        if chair == "office":
            office_chair(V, x, -W / 2 - 0.36)
            continue
        V.box(x - 0.23, -W / 2 - 0.55, 0.42, x + 0.23, -W / 2 - 0.1, 0.47, chair_mat, faces="+z+y-y+x-x")
        V.box(x - 0.22, -W / 2 - 0.6, 0.47, x + 0.22, -W / 2 - 0.54, 0.95, chair_mat, faces="+x-x+y-y+z")
    K.col_box(C, -L / 2, -W / 2, 0.0, L / 2, W / 2, h, K.COL_NOCAM)
    return P


def extrude_x(V, prof, x0, x1, mat, caps=True):
    """Extrude a convex (y, z) profile (CCW seen from +x) along x from x0 to x1: side quads + both end caps."""
    n = len(prof)
    for k in range(n):
        (ya, za), (yb, zb) = prof[k], prof[(k + 1) % n]
        ny_, nz_ = (zb - za), -(yb - ya)
        V.poly([(x0, ya, za), (x0, yb, zb), (x1, yb, zb), (x1, ya, za)], mat, normal_hint=(0, ny_, nz_))
    if caps:
        V.poly([(x1, y_, z_) for y_, z_ in prof], mat, normal_hint=(1, 0, 0))
        V.poly([(x0, y_, z_) for y_, z_ in reversed(prof)], mat, normal_hint=(-1, 0, 0))


def extrude_y(V, prof, y0, y1, mat, caps=True):
    """Extrude a convex (x, z) profile (CCW seen from -y) along y from y0 to y1."""
    n = len(prof)
    for k in range(n):
        (xa, za), (xb, zb) = prof[k], prof[(k + 1) % n]
        nx_, nz_ = (zb - za), -(xb - xa)
        V.poly([(xa, y1, za), (xb, y1, zb), (xb, y0, zb), (xa, y0, za)], mat, normal_hint=(nx_, 0, nz_))
    if caps:
        V.poly([(x_, y0, z_) for x_, z_ in prof], mat, normal_hint=(0, -1, 0))
        V.poly([(x_, y1, z_) for x_, z_ in reversed(prof)], mat, normal_hint=(0, 1, 0))


def loveseat_round(L=1.45, D=0.88, mat="int_ru_leather_tan"):
    """Rounded leather loveseat (ru_hotel_suite: the two butterscotch loveseats): a low seat block, a back with a
    rolled top and flared rolled arms. Local: the back at y = 0, the seat toward +y (facing +y)."""
    P = _p("loveseat_round")
    V, C = P.visual, P.collision
    ai = L / 2 - 0.2
    V.box(-ai, 0.18, 0.0, ai, D - 0.02, 0.44, mat, faces="+y+z")
    # iteration 9 (fidelity-4 improvement 7): the black toe strip stands 1.5 cm proud of the seat front (it lay in
    # the seat's +y face plane and z-fought, 0.13 m2 in the suite)
    V.box(-ai, D - 0.06, 0.0, ai, D - 0.005, 0.06, "int_ru_black", faces="+y")
    # back: rolled top (profile in y, z; CCW seen from +x)
    back = [(0.0, 0.05), (0.26, 0.05), (0.30, 0.62), (0.24, 0.80), (0.12, 0.86), (0.02, 0.80)]
    extrude_x(V, back, -ai, ai, mat, caps=False)
    # arms: flared rolls (profile in x, z, outward to the left for the left arm; mirrored for the right)
    for sx in (-1, 1):
        o = sx * L / 2
        i_ = sx * ai
        prof = [(i_, 0.0), (o, 0.0), (o + sx * 0.06, 0.52), (o + sx * 0.02, 0.64), (o - sx * 0.08, 0.68),
                (i_ - sx * 0.0, 0.62)]
        if sx < 0:
            prof = [(x_, z_) for x_, z_ in reversed(prof)]          # CCW in (x, z) for both arms
        extrude_y(V, prof, 0.02, D, mat)
    K.col_box(C, -L / 2, 0.0, 0.0, L / 2, D, 0.45, K.COL_NOCAM)
    P.info["top_z"] = 0.45
    return P


def lamp_table(w=0.55, h=0.6, mat="int_ru_cherry"):
    """End table with a table lamp (ru_hotel_suite: either side of the sofa): cherry cube, lower shelf, a lamp with
    a white drum shade and a warm light."""
    P = _p("lamp_table")
    V, C = P.visual, P.collision
    t = w / 2
    V.box(-t, -t, h - 0.05, t, t, h, mat, faces="+x-x+y-y+z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            V.box(sx * t - (0.05 if sx > 0 else 0) , sy * t - (0.05 if sy > 0 else 0), 0.0,
                  sx * t + (0 if sx > 0 else 0.05), sy * t + (0 if sy > 0 else 0.05), h - 0.05, mat, faces="+x-x+y-y")
    V.box(-t + 0.05, -t + 0.05, 0.12, t - 0.05, t - 0.05, 0.15, mat, faces="+z")
    cyl(V, 0.0, 0.0, 0.08, h, h + 0.05, "int_ru_steel", n=6)
    cyl(V, 0.0, 0.0, 0.02, h + 0.05, h + 0.42, "int_ru_steel", n=4, top=False)
    cyl(V, 0.0, 0.0, 0.17, h + 0.38, h + 0.7, "int_ru_bed", n=8, top=False)
    P.lights.append(K.Light((0.0, 0.0, h + 0.55), radius=3.2, strength=0.28, color=(1.0, 0.86, 0.62)))
    K.col_box(C, -t, -t, 0.0, t, t, h, K.COL_NOCAM)
    P.info["top_z"] = h
    return P


class _NullMesh:
    def poly(self, *a, **k):
        return None


def _xz_prism(V, C, quad, d, mat, col_mat=None):
    """A convex polygon in the x-z plane extruded over y in [-d/2, d/2]: front (+y), back (-y) and side faces,
    each wound by its outward normal (visual + optional collision)."""
    cx = sum(p[0] for p in quad) / len(quad)
    cz = sum(p[1] for p in quad) / len(quad)
    y0, y1 = -d / 2, d / 2
    faces = [([(x, y1, z) for x, z in quad], (0.0, 1.0, 0.0)), ([(x, y0, z) for x, z in quad], (0.0, -1.0, 0.0))]
    n = len(quad)
    for i in range(n):
        (xa, za), (xb, zb) = quad[i], quad[(i + 1) % n]
        ex, ez = xb - xa, zb - za
        L = math.hypot(ex, ez)
        if L < 1e-5:
            continue
        nx, nz = ez / L, -ex / L
        if (xa + xb) / 2 * 0 + ((xa + xb) / 2 - cx) * nx + ((za + zb) / 2 - cz) * nz < 0:
            nx, nz = -nx, -nz
        faces.append(([(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)], (nx, 0.0, nz)))
    for pts, nh in faces:
        V.poly(pts, mat, normal_hint=nh)
        if col_mat is not None:
            C.poly(pts, col_mat, normal_hint=nh)


def uf_letters(height=2.6, depth=0.7, base=True, mat="int_ru_orange_uf"):
    """The giant orange UF letters of the atrium (ru_atrium_uf_letters_flickr / _wall): thick extruded letters
    (~0.5 m strokes) with a smooth round U bowl you can sit in (a UF-blue cushion in it); a UF-blue plinth.
    Local: letters stand on y = 0, front = +y, centred in x. fix round 4 (fidelity-1): mat = the brighter
    letters orange (ru_atrium_uf_letters_wall (241,119,17); int_ru_orange rendered a brick red under the soffit)."""
    P = _p("uf_letters")
    V, C = P.visual, P.collision
    Wl, gap, st = 1.95, 0.35, 0.5          # letter width, gap, stroke
    z0 = 0.35 if base else 0.0
    zt = z0 + height
    total_w = 2 * Wl + gap
    col = K.COL_NOCAM
    # text reads from the prop's +x side (a viewer facing the front has the prop's right-hand side on their left)
    ox = total_w / 2                       # U spans [ox - Wl, ox]
    ro = Wl / 2
    ri = ro - st
    ucx, ucz = ox - ro, z0 + ro
    # U stems (walkable tops) down to the bowl's centre line
    for xa in (ox - st, ox - Wl):
        _xz_prism(V, C, [(xa, ucz), (xa + st, ucz), (xa + st, zt), (xa, zt)], depth, mat, col)
    # U bowl: half ring under the centre line, 10 segments
    nseg = 10
    for k in range(nseg):
        a0 = math.pi + math.pi * k / nseg
        a1 = math.pi + math.pi * (k + 1) / nseg
        q = [(ucx + ri * math.cos(a0), ucz + ri * math.sin(a0)), (ucx + ro * math.cos(a0), ucz + ro * math.sin(a0)),
             (ucx + ro * math.cos(a1), ucz + ro * math.sin(a1)), (ucx + ri * math.cos(a1), ucz + ri * math.sin(a1))]
        _xz_prism(V, C, q, depth, mat, None)
    # bowl collision: 4 coarser segments (the collision budget), same ring
    for k in range(4):
        a0 = math.pi + math.pi * k / 4
        a1 = math.pi + math.pi * (k + 1) / 4
        q = [(ucx + ri * math.cos(a0), ucz + ri * math.sin(a0)), (ucx + ro * math.cos(a0), ucz + ro * math.sin(a0)),
             (ucx + ro * math.cos(a1), ucz + ro * math.sin(a1)), (ucx + ri * math.cos(a1), ucz + ri * math.sin(a1))]
        _xz_prism(_NullMesh(), C, q, depth, mat, col)
    # the blue cushion in the bowl (students sit in the U)
    V.box(ucx - 0.3, -depth / 2 + 0.06, z0 + st - 0.03, ucx + 0.3, depth / 2 - 0.06, z0 + st + 0.12, "int_ru_uf_blue",
          faces="+x-x+y-y+z")
    # F: stem, top arm, middle arm
    fx1 = ox - Wl - gap
    fx0 = fx1 - Wl
    _xz_prism(V, C, [(fx1 - st, z0), (fx1, z0), (fx1, zt), (fx1 - st, zt)], depth, mat, col)
    _xz_prism(V, C, [(fx0, zt - st), (fx1 - st, zt - st), (fx1 - st, zt), (fx0, zt)], depth, mat, col)
    zm = z0 + height * 0.48
    _xz_prism(V, C, [(fx0 + 0.3, zm), (fx1 - st, zm), (fx1 - st, zm + st), (fx0 + 0.3, zm + st)], depth,
              mat, col)
    if base:
        V.box(-total_w / 2 - 0.4, -depth / 2 - 0.25, 0.0, total_w / 2 + 0.4, depth / 2 + 0.25, z0, "int_ru_uf_blue",
              faces="+x-x+y-y+z")
    if base:        # design + leftovers pass (B09: the letters stand on the floor): no 10 cm plinth step without it
        K.col_box(C, -total_w / 2 - 0.4, -depth / 2 - 0.25, 0.0, total_w / 2 + 0.4, depth / 2 + 0.25, z0 + 0.1,
                  K.COL_NOCAM)
    P.anchor("u_stem_top", ox - st / 2, 0.0, zt, 0.0)
    P.info.update(width=total_w + 0.8, top_z=zt)
    return P


def gator_head(scale=1.0):
    """'Swamp Boss' gator-head statue (wayfinding name; no photo found: a low-poly green gator head on a plinth,
    inferred). Front = +y (snout). fix round 4 (fidelity-1): it read as a black box with a green block; now a UF-blue
    plinth with an orange band and a long, low gator head: broad skull with raised eye bumps, a tapered flat snout
    with nostril bumps, an open lower jaw and white teeth along both sides (same 1.2 m plinth collision, the 1-up on
    top at 0.9 m)."""
    P = _p("gator_head")
    V, C = P.visual, P.collision
    s = scale
    # user-photo pass (B08, C01: the real Swamp Boss): a BLACK gator head on a ROUND honey-wood drum
    # with a black top disc (was a green head on a UF-blue box plinth with an orange band). Same 1.2 m collision box.
    cyl(V, 0.0, 0.0, 0.55 * s, 0.0, 0.86 * s, "int_ru_maple", n=12, top=False)
    cyl(V, 0.0, 0.0, 0.58 * s, 0.86 * s, 0.9 * s, "int_ru_black", n=12, top=True)
    g = "int_ru_bronze_black"
    z = 0.9 * s

    def slab(foot, z0, z1, ztop_front=None):
        # a prism over `foot` (ccw plan quad, local); its top may slope down toward +y (the snout)
        for a_, b_ in edges(foot):
            quad_wall(V, a_, b_, z0, z1 if ztop_front is None or (a_[1] < 0.5 * s and b_[1] < 0.5 * s) else ztop_front, g)
        top = [(q[0], q[1], (ztop_front if (ztop_front is not None and q[1] > 0.5 * s) else z1)) for q in foot]
        V.poly(top, g, normal_hint=(0, 0, 1))
    # skull: broad and low over the plinth's back half
    slab([(-0.42 * s, -0.55 * s), (0.42 * s, -0.55 * s), (0.36 * s, 0.15 * s), (-0.36 * s, 0.15 * s)], z, z + 0.42 * s)
    # upper jaw / snout: long, flat and tapered, sloping from 0.36 to 0.24 m high at the tip
    sn = [(-0.34 * s, 0.1 * s), (0.34 * s, 0.1 * s), (0.2 * s, 1.35 * s), (-0.2 * s, 1.35 * s)]
    for a_, b_ in edges(sn):
        quad_wall(V, a_, b_, z + 0.16 * s, z + (0.36 if a_[1] < 0.5 * s and b_[1] < 0.5 * s else 0.26) * s, g)
    V.poly([(q[0], q[1], z + (0.36 if q[1] < 0.5 * s else 0.26) * s) for q in sn], g, normal_hint=(0, 0, 1))
    V.poly([(q[0], q[1], z + 0.16 * s) for q in reversed(sn)], "int_ru_black", normal_hint=(0, 0, -1))
    # lower jaw: open, a thinner wedge resting on the plinth top
    lj = [(-0.3 * s, 0.1 * s), (0.3 * s, 0.1 * s), (0.17 * s, 1.2 * s), (-0.17 * s, 1.2 * s)]
    for a_, b_ in edges(lj):
        quad_wall(V, a_, b_, z, z + 0.08 * s, g)
    V.poly([(q[0], q[1], z + 0.08 * s) for q in lj], "int_ru_black", normal_hint=(0, 0, 1))   # the mouth's inside
    # eye bumps with orange eyes, nostril bumps at the tip
    for sx in (-1, 1):
        V.box(sx * 0.26 * s - 0.1 * s, -0.3 * s, z + 0.42 * s, sx * 0.26 * s + 0.1 * s, -0.06 * s, z + 0.6 * s, g,
              faces="+x-x+y-y+z")
        V.box(sx * 0.26 * s - 0.06 * s, -0.05 * s, z + 0.46 * s, sx * 0.26 * s + 0.06 * s, -0.04 * s, z + 0.56 * s,
              "int_ru_leather_char", faces="+y")
        V.box(sx * 0.09 * s - 0.05 * s, 1.12 * s, z + 0.26 * s, sx * 0.09 * s + 0.05 * s, 1.26 * s, z + 0.32 * s, g,
              faces="+x-x+y-y+z")
    # fix round 4 (design pass, improvement 9): from behind / the stair side it read as a green cube with orange
    # specks: a dark brow ridge over each eye bump (proud on the top and sides) and a row of dark scutes down the
    # skull's back (the gator's silhouette from the stairs)
    for sx in (-1, 1):
        V.box(sx * 0.26 * s - 0.12 * s, -0.33 * s, z + 0.6 * s, sx * 0.26 * s + 0.12 * s, -0.03 * s, z + 0.66 * s,
              "int_ru_black", faces="+x-x+y-y+z")
    for k in range(4):
        y0_ = -0.52 * s + k * 0.17 * s
        for sx in (-1, 1):
            V.box(sx * 0.12 * s - 0.05 * s, y0_, z + 0.42 * s, sx * 0.12 * s + 0.05 * s, y0_ + 0.11 * s, z + 0.5 * s,
                  "int_ru_black", faces="+x-x+y-y+z")
    # teeth: white zigzags down from the upper jaw and up from the lower jaw, both sides
    for k in range(7):
        y = 0.2 * s + k * 0.15 * s
        for sx in (-1, 1):
            xo = sx * (0.335 - 0.13 * (y / s - 0.1) / 1.25) * s + sx * 0.005
            V.poly([(xo, y, z + 0.16 * s), (xo, y + 0.09 * s, z + 0.16 * s), (xo, y + 0.045 * s, z + 0.08 * s)],
                   "int_ru_leather_grey", tint=(0.55, 0.56, 0.58), normal_hint=(sx, 0, 0))
    # iteration 7 (fidelity-1 improvement 7; no photo, inferred): snout-on (from the lounge) it read as a green block
    # with two eyes. Front teeth across both jaw tips (1 cm proud of the tip faces), a pale cream under-jaw band
    # (2 cm proud of the lower jaw's sides), black nostrils on the nostril bumps, a black slit pupil on each eye
    # (both 1.5 cm proud)
    for k in range(4):
        x_ = (-0.15 + 0.1 * k) * s
        V.poly([(x_ - 0.04 * s, 1.36 * s, z + 0.16 * s), (x_ + 0.04 * s, 1.36 * s, z + 0.16 * s),
                (x_, 1.36 * s, z + 0.09 * s)], "int_ru_leather_grey", tint=(0.55, 0.56, 0.58), normal_hint=(0, 1, 0))
    for k in range(3):
        x_ = (-0.09 + 0.09 * k) * s
        V.poly([(x_ - 0.035 * s, 1.21 * s, z + 0.08 * s), (x_, 1.21 * s, z + 0.14 * s),
                (x_ + 0.035 * s, 1.21 * s, z + 0.08 * s)], "int_ru_leather_grey", tint=(0.55, 0.56, 0.58), normal_hint=(0, 1, 0))
    for a_, b_ in edges([(-0.32 * s, 0.1 * s), (0.32 * s, 0.1 * s), (0.19 * s, 1.22 * s), (-0.19 * s, 1.22 * s)]):
        if a_[1] > 0.5 * s or b_[1] > 0.5 * s:
            quad_wall(V, a_, b_, z + 0.01 * s, z + 0.05 * s, "int_ru_leather_char")
    for sx in (-1, 1):
        V.box(sx * 0.09 * s - 0.025 * s, 1.17 * s, z + 0.325 * s, sx * 0.09 * s + 0.025 * s, 1.21 * s, z + 0.335 * s,
              "int_ru_black", faces="+z")
        V.box(sx * 0.26 * s - 0.012 * s, -0.035 * s, z + 0.47 * s, sx * 0.26 * s + 0.012 * s, -0.025 * s,
              z + 0.55 * s, "int_ru_black", faces="+y")
    K.col_box(C, -0.6 * s, -0.6 * s, 0.0, 0.6 * s, 0.6 * s, 0.9 * s, K.COL_NOCAM)
    return P


def _kitchen_line(V, xr, xl, depth, oh):
    """fidelity-2: a bright, busy kitchen behind the opening (ru_food_court_sonic_2025; the white tile back wall is
    the style's "back"): a steel pass shelf with heat lamps over the counter, a reach-in fridge, a fryer / grill block with a dark top,
    steel wall shelves and a ticket rail."""
    W0 = xl - xr
    # pass shelf + heat lamp hood just behind the counter
    V.box(xr + 0.25, -0.35, 1.45, xl - 0.25, 0.05, 1.5, "int_ru_steel", faces="+z-z+y+x-x")
    for k in range(3):
        u = xr + 0.25 + (W0 - 0.5) * (k + 0.5) / 3
        V.box(u - 0.02, -0.33, 1.06, u + 0.02, -0.29, 1.45, "int_ru_steel", faces="+y+x-x")
    V.box(xr + 0.3, -0.4, 1.9, xl - 0.3, -0.05, 1.98, "int_ru_steel", faces="+y-z")
    # fix round 5 (fidelity-2): the LED strip hangs 1 cm under the shelf (at 1.899 it exported to the same game unit
    # as the steel underside: a coplanar pair seen from below)
    V.poly([(xl - 0.35, -0.06, 1.89), (xr + 0.35, -0.06, 1.89), (xr + 0.35, -0.39, 1.89), (xl - 0.35, -0.39, 1.89)],
           "int_ru_led", glow=True, normal_hint=(0, 0, -1))
    # reach-in fridge at the right (viewer's right = local -x) end, a fryer / grill block at the left
    V.box(xr + 0.25, -depth, 0.0, xr + 1.0, -depth + 0.75, 2.05, "int_ru_steel", faces="+y+x+z")
    V.box(xr + 0.6, -depth + 0.755, 0.15, xr + 0.62, -depth + 0.77, 1.9, "int_ru_black", faces="+y")
    V.box(xl - 1.6, -depth + 0.0, 0.0, xl - 0.3, -depth + 0.8, 0.95, "int_ru_steel", faces="+y+x-x")
    V.box(xl - 1.6, -depth + 0.0, 0.95, xl - 0.3, -depth + 0.8, 0.98, "int_ru_black", faces="+z+y")
    V.box(xl - 1.5, -depth + 0.1, 0.98, xl - 1.0, -depth + 0.6, 1.25, "int_ru_steel", faces="+y+x-x+z")
    # two steel wall shelves with boxes
    for zz in (1.55, 1.95):
        V.box(xr + 1.2, -depth, zz, xl - 1.8, -depth + 0.3, zz + 0.03, "int_ru_steel", faces="+y+z-z")
    for k in range(int(max(0, W0 - 3.2) / 0.5)):
        u = xr + 1.3 + k * 0.5
        V.box(u, -depth + 0.02, 1.58, u + 0.32, -depth + 0.24, 1.8, "int_ru_counter_red" if k % 3 == 0 else
              "int_ru_wall_cream", faces="+y+z")


def _coffee_bar(V, xr, xl):
    """fidelity-2: the Starbucks counter top (ru_starbucks_2017): two black espresso machines with steel heads, a
    register, a lit pastry case with a glass sneeze guard at the viewer's left end."""
    W0 = xl - xr
    for k, u in enumerate((xr + 0.55, xr + 1.45)):
        V.box(u - 0.35, 0.12, 1.06, u + 0.35, 0.52, 1.5, "int_ru_black", faces="+y-y+x-x+z")
        V.box(u - 0.3, 0.1, 1.34, u + 0.3, 0.12, 1.42, "int_ru_steel", faces="+y")
        for gx in (-0.15, 0.15):
            V.box(u + gx - 0.04, 0.02, 1.2, u + gx + 0.04, 0.12, 1.3, "int_ru_steel", faces="+y-y+x-x")
        V.box(u - 0.33, 0.14, 1.5, u + 0.33, 0.5, 1.56, "int_ru_steel", faces="+z+y")
    if W0 > 3.0:
        u = xr + 2.35       # register
        V.box(u - 0.2, 0.2, 1.06, u + 0.2, 0.55, 1.14, "int_ru_black", faces="+y-y+x-x+z")
        V.poly([(u + 0.16, 0.6, 1.16), (u - 0.16, 0.6, 1.16), (u - 0.16, 0.5, 1.42), (u + 0.16, 0.5, 1.42)],
               "int_ru_menu_screen", uvs=K.uv_rect(0, 0, 1, 1), glow=True)
        V.box(u - 0.03, 0.45, 1.14, u + 0.03, 0.5, 1.3, "int_ru_black", faces="+y+x-x")
    # pastry case (glass box on the counter, lit shelves inside) + sneeze guard
    x0, x1 = xl - 1.4, xl - 0.2
    V.poly([(x1, 0.66, 1.08), (x0, 0.66, 1.08), (x0, 0.66, 1.5), (x1, 0.66, 1.5)], "int_ru_pastry",
           uvs=K.uv_rect(0, 0, 1, 1), glow=True, normal_hint=(0, 1, 0))
    V.box(x0, 0.02, 1.06, x1, 0.7, 1.08, "int_ru_steel", faces="+z")
    V.box(x0, 0.02, 1.5, x1, 0.74, 1.54, "int_ru_steel", faces="+z-z+y")
    V.poly([(x1, 0.72, 1.08), (x0, 0.72, 1.08), (x0, 0.72, 1.5), (x1, 0.72, 1.5)], "int_ru_glass",
           normal_hint=(0, 1, 0))
    V.poly([(x1, 0.74, 1.54), (x0, 0.74, 1.54), (x0, 0.5, 1.78), (x1, 0.5, 1.78)], "int_ru_glass",
           normal_hint=(0, 0.7, 0.7))


def storefront(width, sign_mat, wall_mat="int_ru_paint_lime", side_mat="int_ru_paint_sky", counter=True, h=4.2,
               soffit=True, menu=True, open_counter=True, depth=1.8, style=None):
    """Food court vendor front (ru_food_court_counter_2023, ru_food_court_sonic_2025, ru_starbucks_2017): a serving
    counter, the vendor's back wall, menu boards, sign; local: the storefront line is y = 0, the counter in front
    (+y), the kitchen behind (-y). Width along x. A viewer facing the front has local +x on the LEFT.
    style (dict, all optional): counter / top (counter front + top materials), back (back-wall material),
    menu (material) + menu_glow + menu_w + menu_z, hood (stainless hood band, default True), fascia (True: the
    sign sits on a full-width fascia of that material from open_h up to h, ru_food_court_sonic_2025), open_h,
    frame (material of a frame round the opening), left_panel / right_panel ((material, width[, decal])): solid
    facade panels at the viewer's left / right end of the slot."""
    st = style or {}
    P = _p("storefront", width=width)
    V, C = P.visual, P.collision
    W = width
    back = st.get("back", wall_mat)
    oh = st.get("open_h", h) if st.get("fascia") else h
    lp, rp = st.get("left_panel"), st.get("right_panel")
    xl = W / 2 - (lp[1] if lp else 0.0)       # opening: local x from xr to xl
    xr = -W / 2 + (rp[1] if rp else 0.0)
    # back wall (inside the servery) + side returns
    V.poly([(W / 2, -depth, 0.0), (-W / 2, -depth, 0.0), (-W / 2, -depth, h), (W / 2, -depth, h)], back,
           normal_hint=(0, 1, 0), ao=0.9)
    for sx in (-1, 1):
        a, b = (sx * W / 2, -depth), (sx * W / 2, 0.0)
        if sx > 0:
            a, b = b, a
        quad_wall(V, a, b, 0.0, h, st.get("side", side_mat), ao=0.85)
    V.poly([(-W / 2, -depth, h), (W / 2, -depth, h), (W / 2, 0.0, h), (-W / 2, 0.0, h)], "int_ru_soffit",
           normal_hint=(0, 0, -1), ao=0.9)
    V.poly([(-W / 2, -depth, 0.0), (W / 2, -depth, 0.0), (W / 2, 0.0, 0.0), (-W / 2, 0.0, 0.0)], "int_ru_steel",
           normal_hint=(0, 0, 1), ao=0.8)
    # kitchen line (back counter + hood)
    V.box(-W / 2 + 0.2, -depth, 0.0, W / 2 - 0.2, -depth + 0.65, 0.92, st.get("back_counter", "int_ru_steel"),
          faces="+y+z")
    if st.get("hood", True):
        V.box(-W / 2 + 0.4, -depth, 2.3, W / 2 - 0.4, -depth + 0.8, 2.9, "int_ru_steel", faces="+y-z")
    if st.get("kitchen"):
        _kitchen_line(V, xr, xl, depth, oh)
    if menu and not st.get("no_menu"):
        mw = min(xl - xr - 0.8, st.get("menu_w", 3.6))
        mz0, mz1 = st.get("menu_z", (1.8, 2.75))
        mm = st.get("menu", "int_ru_menu")
        n = st.get("menu_n") or max(1, int(round(mw / 2.4)))
        gap = st.get("menu_gap", 0.0)
        my = st.get("menu_y", -depth + 0.02)
        cx0 = (xl + xr) / 2
        for k in range(n):
            u0 = cx0 - mw / 2 + mw * k / n + gap / 2
            u1 = u0 + mw / n - gap
            V.poly([(u1, my, mz0), (u0, my, mz0), (u0, my, mz1), (u1, my, mz1)], mm, uvs=K.uv_rect(0, 0, 1, 1),
                   glow=st.get("menu_glow", True), normal_hint=(0, 1, 0))
            if st.get("menu_y") is not None:     # screens hung in the opening: a dark back + a drop rod each
                V.poly([(u0, my - 0.04, mz0), (u1, my - 0.04, mz0), (u1, my - 0.04, mz1), (u0, my - 0.04, mz1)],
                       "int_ru_black", normal_hint=(0, -1, 0))
                cm_ = (u0 + u1) / 2
                V.box(cm_ - 0.02, my - 0.04, mz1, cm_ + 0.02, my, oh, "int_ru_black", faces="+y-y+x-x")
    if st.get("coffee_bar"):
        _coffee_bar(V, xr, xl)
    if counter:
        cm, tm = st.get("counter", "int_ru_counter_front"), st.get("top", "int_ru_wall_cream")
        V.box(xr + 0.1, 0.0, 0.0, xl - 0.1, 0.65, 1.0, cm, faces="+y+x-x", uvs=None)
        V.box(xr + 0.05, -0.05, 1.0, xl - 0.05, 0.72, 1.06, tm, faces="+x-x+y-y+z")
        K.col_box(C, xr, 0.0, 0.0, xl, 0.72, 1.06, K.COL)
    # facade panels at the ends of the slot (solid: they close part of the wall opening)
    for pan, x0, x1 in ((lp, xl, W / 2), (rp, -W / 2, xr)):
        if not pan:
            continue
        V.box(x0, 0.0, 0.0, x1, 0.08, oh, pan[0], faces="+y+x-x")   # visual only: the servery wall collides
        if len(pan) > 3:      # a full-height post at the opening edge of the panel (ru_food_court_counter_2023)
            px0, px1 = (x0, x0 + 0.3) if pan is lp else (x1 - 0.3, x1)
            V.box(px0, 0.0, 0.0, px1, 0.25, h, pan[3], faces="+y+x-x")
        if len(pan) > 2 and pan[2] and st.get("panel_decal_full"):
            # fidelity-2: the neon fills the panel's height (ru_food_court_sonic_2025)
            cx, d = (x0 + x1) / 2, st.get("panel_decal_w", (x1 - x0) - 0.24)
            za, zb = st.get("panel_decal_z", (0.35, oh - 0.12))
            dy = st.get("panel_decal_y", 0.09)     # fix round 4: proud of the fascia (0.1) when it runs up over it
            V.poly([(cx + d / 2, dy, za), (cx - d / 2, dy, za), (cx - d / 2, dy, zb), (cx + d / 2, dy, zb)],
                   pan[2], uvs=K.uv_rect(0, 0, 1, 1), glow=True, normal_hint=(0, 1, 0))
        elif len(pan) > 2 and pan[2]:
            d = min(x1 - x0 - 0.2, 1.5)
            cx = (x0 + x1) / 2
            V.poly([(cx + d / 2, 0.09, 0.9), (cx - d / 2, 0.09, 0.9), (cx - d / 2, 0.09, 0.9 + d),
                    (cx + d / 2, 0.09, 0.9 + d)], pan[2], uvs=K.uv_rect(0, 0, 1, 1), glow=True, normal_hint=(0, 1, 0))
    if st.get("frame"):
        fm = st["frame"]
        V.box(xl - 0.16, 0.0, 0.0, xl, 0.12, oh, fm, faces="+y+x-x")
        V.box(xr, 0.0, 0.0, xr + 0.16, 0.12, oh, fm, faces="+y+x-x")
        V.box(xr, 0.0, oh - 0.16, xl, 0.12, oh, fm, faces="+y-z")
    if st.get("fascia"):
        # full-width fascia over the opening with the (neon) name centred on it
        V.box(-W / 2, 0.0, oh, W / 2, 0.1, h, st["fascia"], faces="+y+x-x-z")
        fh = h - oh - 0.1
        if st.get("letters"):
            # fidelity-2: channel letters straight on the fascia (cutout card, no panel behind them)
            lw, lh = st.get("letters_w", min(W - 0.6, 4.4)), st.get("letters_h", min(fh - 0.1, 1.0))
            lz = oh + (h - oh - lh) / 2
            lx = st.get("letters_x", 0.0)      # user-photo pass: letters off centre (STARBUCKS, PANDA)
            V.poly([(lx + lw / 2, 0.12, lz), (lx - lw / 2, 0.12, lz), (lx - lw / 2, 0.12, lz + lh),
                    (lx + lw / 2, 0.12, lz + lh)],
                   st["letters"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], glow=True, normal_hint=(0, 1, 0))
        elif sign_mat:
            sw = min(W - 0.6, fh * 3.6)
            V.poly([(sw / 2, 0.11, oh + 0.05), (-sw / 2, 0.11, oh + 0.05), (-sw / 2, 0.11, oh + 0.05 + fh),
                    (sw / 2, 0.11, oh + 0.05 + fh)], sign_mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], glow=True,
                   normal_hint=(0, 1, 0))
    elif not sign_mat:
        pass
    else:
        # sign band above the opening
        sw = min(W - 0.4, 3.2)
        V.poly([(sw / 2, 0.06, h - 1.2), (-sw / 2, 0.06, h - 1.2), (-sw / 2, 0.06, h - 0.15), (sw / 2, 0.06, h - 0.15)],
               sign_mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], glow=True, normal_hint=(0, 1, 0))
    # user-photo pass (food court): extra once-mapped decals in the local frame (round badges, the
    # painted name on a counter front): (material, x0, x1, z0, z1, y, glow); x0 > x1 reads left to right
    for (dm, dx0, dx1, dz0, dz1, dy, dg) in st.get("decals", ()):
        V.poly([(dx1, dy, dz0), (dx0, dy, dz0), (dx0, dy, dz1), (dx1, dy, dz1)], dm,
               uvs=[(1, 0), (0, 0), (0, 1), (1, 1)], glow=dg, normal_hint=(0, 1, 0))
    # ... black dome pendants over the counter (B01, Baba's Pizza): a dome, a lit disc under it, a thin cord
    for px_ in st.get("pendants", ()):
        cyl(V, px_, 1.0, 0.28, 2.45, 2.67, "int_ru_black", n=8, top=True)
        V.poly([(px_ + 0.24 * math.cos(2 * math.pi * k / 8), 1.0 + 0.24 * math.sin(2 * math.pi * k / 8), 2.44)
                for k in reversed(range(8))], "int_ru_led", glow=True)
        V.box(px_ - 0.01, 0.99, 2.67, px_ + 0.01, 1.01, h - 0.01, "int_ru_black", faces="+x-x+y-y")
    P.lights.append(K.Light((0.0, -0.6, h - 0.4), radius=5.0, strength=st.get("light", 0.35), color=(1.0, 0.95, 0.85)))
    return P


def senate_tiers(rows=7, r0=6.0, dr=1.15, a0=-50.0, a1=50.0, rise=0.15, seg=8, half_w=None):
    """Senate Chamber seating (ru_os_chamber): curved rows of long continuous grey stone-look desk counters with
    dense, low navy high-back chairs behind them, facing the dais at the local origin (+y side = audience). Each
    row steps up `rise`; half_w clamps each row's arc to that half width (the room's side walls).
    Collision per row: the desk band (inner + outer faces, top, two ends) and the row's floor (risers <= 0.18 m
    need no walls: Mario steps up them)."""
    P = _p("senate_tiers")
    V, C = P.visual, P.collision

    def arc(Rr, aa, bb):
        return [(Rr * math.sin(math.radians(aa + (bb - aa) * k / seg)), Rr * math.cos(math.radians(aa + (bb - aa) * k / seg)))
                for k in range(seg + 1)]
    for r in range(rows):
        R = r0 + r * dr
        z = r * rise
        aa, bb = a0, a1
        if half_w is not None:
            lim = math.degrees(math.asin(min(1.0, half_w / (R + dr))))
            aa, bb = max(a0, -lim), min(a1, lim)
        arc_out = arc(R, aa, bb)
        arc_in = arc(R - 0.55, aa, bb)
        arc_back = arc(R + dr - 0.05, aa, bb)
        for k in range(seg):
            if r > 0:
                q = [arc_in[k], arc_in[k + 1], arc_back[k + 1], arc_back[k]]
                V.poly([(p[0], p[1], z) for p in q], "int_ru_carpet_chamber", normal_hint=(0, 0, 1))
                V.poly([(arc_in[k][0], arc_in[k][1], z - rise), (arc_in[k + 1][0], arc_in[k + 1][1], z - rise),
                        (arc_in[k + 1][0], arc_in[k + 1][1], z), (arc_in[k][0], arc_in[k][1], z)],
                       "int_ru_wall_grey", normal_hint=(-arc_in[k][0], -arc_in[k][1], 0))
            # desk: grey stone-look counter top (thick edge) + a grey modesty panel facing the dais
            V.poly([(arc_in[k][0], arc_in[k][1], z + 0.76), (arc_in[k + 1][0], arc_in[k + 1][1], z + 0.76),
                    (arc_out[k + 1][0], arc_out[k + 1][1], z + 0.76), (arc_out[k][0], arc_out[k][1], z + 0.76)],
                   "int_ru_stone_grey", normal_hint=(0, 0, 1))
            V.poly([(arc_out[k + 1][0], arc_out[k + 1][1], z + 0.66), (arc_out[k][0], arc_out[k][1], z + 0.66),
                    (arc_out[k][0], arc_out[k][1], z + 0.76), (arc_out[k + 1][0], arc_out[k + 1][1], z + 0.76)],
                   "int_ru_stone_grey", normal_hint=(arc_out[k][0], arc_out[k][1], 0))
            V.poly([(arc_in[k][0], arc_in[k][1], z), (arc_in[k + 1][0], arc_in[k + 1][1], z),
                    (arc_in[k + 1][0], arc_in[k + 1][1], z + 0.76), (arc_in[k][0], arc_in[k][1], z + 0.76)],
                   "int_ru_wall_grey", normal_hint=(-arc_in[k][0], -arc_in[k][1], 0))
        for e, sg in ((0, -1), (seg, 1)):        # desk end caps + the row platform's end face (down to the floor)
            ea, eb = (arc_in[e], arc_out[e]) if sg > 0 else (arc_out[e], arc_in[e])
            quad_wall(V, ea, eb, z, z + 0.76, "int_ru_wall_grey")
            if r > 0:
                pa_, pb_ = (arc_in[e], arc_back[e]) if sg > 0 else (arc_back[e], arc_in[e])
                quad_wall(V, pa_, pb_, 0.0, z, "int_ru_wall_grey")
                if z >= 0.55:
                    # high rows: a wall at the platform's end (Mario's wall checks at 0.3 / 0.6 m would otherwise
                    # let him pop up 0.6-0.9 m from the side aisle)
                    C.wall(pa_, pb_, 0.0, z, K.COL)
        # chairs: dense (0.72 m) low navy high-backs behind the counter
        Rc = R + 0.42
        span = math.radians(bb - aa) * Rc
        n = max(2, int(span / 0.72))
        for j in range(n):
            a = math.radians(aa + (bb - aa) * (j + 0.5) / n)
            cx, cy = Rc * math.sin(a), Rc * math.cos(a)
            tx, ty = math.cos(a), -math.sin(a)
            nx, ny = math.sin(a), math.cos(a)
            # fix round 4 (fidelity-3; ru_os_chamber): black high-back executive chairs, the backs rising to 1.25 m
            # (~0.5 m over the 0.76 m desks; they were 1.05 m navy blocks): a 6 cm thick back with a top cap
            zb0, zb1 = z + 0.45, z + 1.25
            b0 = (cx - tx * 0.24 + nx * 0.19, cy - ty * 0.24 + ny * 0.19)
            b1 = (cx + tx * 0.24 + nx * 0.19, cy + ty * 0.24 + ny * 0.19)
            q0 = (cx - tx * 0.24 + nx * 0.25, cy - ty * 0.24 + ny * 0.25)
            q1 = (cx + tx * 0.24 + nx * 0.25, cy + ty * 0.24 + ny * 0.25)
            V.poly([(b0[0], b0[1], zb0), (b1[0], b1[1], zb0), (b1[0], b1[1], zb1), (b0[0], b0[1], zb1)],
                   "int_ru_fabric_char", normal_hint=(-nx, -ny, 0))
            V.poly([(q1[0], q1[1], zb0), (q0[0], q0[1], zb0), (q0[0], q0[1], zb1), (q1[0], q1[1], zb1)],
                   "int_ru_black", normal_hint=(nx, ny, 0))
            V.poly([(b0[0], b0[1], zb1), (b1[0], b1[1], zb1), (q1[0], q1[1], zb1), (q0[0], q0[1], zb1)],
                   "int_ru_black", normal_hint=(0, 0, 1))
            for (fa_, ra_, sg_) in ((b0, q0, -1), (b1, q1, 1)):
                V.poly([(fa_[0], fa_[1], zb0), (ra_[0], ra_[1], zb0), (ra_[0], ra_[1], zb1), (fa_[0], fa_[1], zb1)],
                       "int_ru_black", normal_hint=(tx * sg_, ty * sg_, 0))
            s0 = (cx - tx * 0.24 - nx * 0.22, cy - ty * 0.24 - ny * 0.22)
            s1 = (cx + tx * 0.24 - nx * 0.22, cy + ty * 0.24 - ny * 0.22)
            V.poly([(s0[0], s0[1], z + 0.45), (s1[0], s1[1], z + 0.45), (b1[0], b1[1], z + 0.45), (b0[0], b0[1], z + 0.45)],
                   "int_ru_fabric_char", normal_hint=(0, 0, 1))
            V.poly([(s1[0], s1[1], z + 0.05), (s0[0], s0[1], z + 0.05), (s0[0], s0[1], z + 0.45), (s1[0], s1[1], z + 0.45)],
                   "int_ru_black", normal_hint=(-nx, -ny, 0))
        # collision: the desk band per 2 segments (faces in and out + top), one end cap per side; the row floor
        for k in range(0, seg, 2):
            k2 = min(seg, k + 2)
            C.wall(arc_in[k], arc_in[k2], z, z + 0.76, K.COL_NOCAM)
            C.wall(arc_out[k2], arc_out[k], z, z + 0.76, K.COL_NOCAM)
            C.poly([(arc_in[k][0], arc_in[k][1], z + 0.76), (arc_in[k2][0], arc_in[k2][1], z + 0.76),
                    (arc_out[k2][0], arc_out[k2][1], z + 0.76), (arc_out[k][0], arc_out[k][1], z + 0.76)],
                   K.COL_NOCAM, normal_hint=(0, 0, 1))
            if r > 0:
                C.poly([(arc_in[k][0], arc_in[k][1], z), (arc_in[k2][0], arc_in[k2][1], z),
                        (arc_back[k2][0], arc_back[k2][1], z), (arc_back[k][0], arc_back[k][1], z)],
                       K.COL, normal_hint=(0, 0, 1))
        C.wall(arc_out[0], arc_in[0], z, z + 0.76, K.COL_NOCAM)
        C.wall(arc_in[seg], arc_out[seg], z, z + 0.76, K.COL_NOCAM)
    P.info.update(back_r=r0 + rows * dr, top_z=(rows - 1) * rise)
    return P


def bed_set(w=1.6, L=2.1):
    """Hotel room (ru_hotel_room): queen bed (white duvet, royal-blue skirt), cherry headboard + nightstands with
    lamps. Local: headboard against the wall at y = 0, bed toward +y."""
    P = _p("hotel_bed")
    V, C = P.visual, P.collision
    V.box(-w / 2, 0.0, 0.0, w / 2, L, 0.35, "int_ru_uf_blue", faces="+x-x+y")
    V.box(-w / 2, 0.0, 0.35, w / 2, L, 0.62, "int_ru_bed", faces="+x-x+y+z")
    V.box(-w / 2 + 0.1, 0.1, 0.62, -0.05, 0.6, 0.78, "int_ru_bed", faces="+x-x+y-y+z")
    V.box(0.05, 0.1, 0.62, w / 2 - 0.1, 0.6, 0.78, "int_ru_bed", faces="+x-x+y-y+z")
    V.box(-w / 2 - 0.05, -0.06, 0.0, w / 2 + 0.05, 0.04, 1.35, "int_ru_cherry", faces="+x-x+y+z")
    for sx in (-1, 1):
        x = sx * (w / 2 + 0.35)
        V.box(x - 0.28, 0.0, 0.0, x + 0.28, 0.45, 0.62, "int_ru_cherry", faces="+x-x+y+z")
        cyl(V, x, 0.22, 0.06, 0.62, 0.95, "int_ru_steel", n=5, top=False)
        cyl(V, x, 0.22, 0.17, 0.95, 1.25, "int_ru_bed", n=6, top=False)
        P.lights.append(K.Light((x, 0.3, 1.1), radius=3.0, strength=0.25, color=(1.0, 0.86, 0.62)))
    K.col_box(C, -w / 2, 0.0, 0.0, w / 2, L, 0.62, K.COL_NOCAM)
    P.info["top_z"] = 0.62
    return P


def dresser_tv(L=1.6):
    P = _p("dresser_tv")
    V, C = P.visual, P.collision
    V.box(-L / 2, 0.0, 0.0, L / 2, 0.5, 0.8, "int_ru_cherry", faces="+x-x+y+z")
    V.poly([(-0.55, 0.03, 1.2), (0.55, 0.03, 1.2), (0.55, 0.03, 1.85), (-0.55, 0.03, 1.85)], "int_ru_tv_hotel",
           uvs=K.ONCE, normal_hint=(0, 1, 0))
    K.col_box(C, -L / 2, 0.0, 0.0, L / 2, 0.5, 0.8, K.COL_NOCAM)
    return P


def sofa(L=2.0, mat="int_ru_uf_blue"):
    P = _p("sofa")
    V, C = P.visual, P.collision
    V.box(-L / 2, 0.0, 0.0, L / 2, 0.9, 0.42, mat, faces="+x-x+y+z")
    V.box(-L / 2, 0.0, 0.42, L / 2, 0.22, 0.9, mat, faces="+x-x+y+z")
    for sx in (-1, 1):
        V.box(sx * L / 2 - (0.18 if sx > 0 else 0), 0.22, 0.42, sx * L / 2 + (0 if sx > 0 else 0.18), 0.9, 0.62, mat,
              faces="+x-x+y+z")
    K.col_box(C, -L / 2, 0.0, 0.0, L / 2, 0.9, 0.45, K.COL_NOCAM)
    return P


def cafe_table_set(table_w=0.75, h=0.75, chairs=4, chair_mat="int_ru_fabric_navy", top="int_wood", frame="int_ru_wood_panel",
                   seat_box=False, round_top=False):
    """Square cafe table with 2-4 wood/navy chairs (food court, Arredondo Cafe). seat_box: padded seat cushions
    with sides and a taller wood back (the Arredondo chairs, fidelity-4 round 2)."""
    P = _p("cafe_table")
    V, C = P.visual, P.collision
    t = table_w / 2
    if round_top:      # user-photo pass (B03): round laminate tops by the Starbucks
        cyl(V, 0.0, 0.0, 0.42, h - 0.04, h, top, n=8, top=True)
    else:
        V.box(-t, -t, h - 0.04, t, t, h, top, faces="+x-x+y-y+z")
    V.box(-0.04, -0.04, 0.0, 0.04, 0.04, h - 0.04, "int_ru_black", faces="+x-x+y-y")
    for k in range(chairs):
        a = math.pi / 2 * k
        cx, cy = 0.62 * math.cos(a), 0.62 * math.sin(a)
        fx, fy = -math.cos(a), -math.sin(a)
        tx, ty = -fy, fx
        V.box(cx - 0.2, cy - 0.2, 0.42 if seat_box else 0.44, cx + 0.2, cy + 0.2, 0.49 if seat_box else 0.48, chair_mat,
              faces="+z+x-x+y-y" if seat_box else "+z")
        b0 = (cx - fx * 0.2 + tx * 0.2, cy - fy * 0.2 + ty * 0.2)
        b1 = (cx - fx * 0.2 - tx * 0.2, cy - fy * 0.2 - ty * 0.2)
        # iteration 9 (fidelity-4 improvement 7): with seat_box the black leg panel stops at the cushion's underside
        # (0.42; to 0.44 it lay in the cushion's back face plane and z-fought, 0.90 m2 in Arredondo)
        for (za, zb_, m) in ((0.0, 0.42 if seat_box else 0.44, "int_ru_black"),
                             (0.56 if seat_box else 0.62, 0.95 if seat_box else 0.88, frame)):
            V.poly([(b0[0], b0[1], za), (b1[0], b1[1], za), (b1[0], b1[1], zb_), (b0[0], b0[1], zb_)], m,
                   normal_hint=(fx, fy, 0))
            V.poly([(b1[0], b1[1], za), (b0[0], b0[1], za), (b0[0], b0[1], zb_), (b1[0], b1[1], zb_)], m,
                   normal_hint=(-fx, -fy, 0))
    K.col_box(C, -t, -t, 0.0, t, t, h, K.COL_NOCAM)
    P.info["top_z"] = h
    return P


def diner_booth(L=1.25, seat="int_ru_leather_orange", top="int_ru_black", seat_h=0.45, back_h=1.15):
    """Food court booth (ru_food_court_booths_2016, fidelity-2): two orange-upholstered benches facing each other
    across a dark table, the table end against the wall. Local: the wall at x = 0, the booth runs to x = L; the
    table at y in [-0.38, 0.38], benches to y = +-1.05. Visual only (the caller adds one collision box per run)."""
    P = _p("diner_booth")
    V = P.visual
    V.box(0.0, -0.38, 0.72, L - 0.05, 0.38, 0.76, top, faces="+x-x+y-y+z")
    V.box(L * 0.5 - 0.05, -0.05, 0.0, L * 0.5 + 0.05, 0.05, 0.72, "int_ru_black", faces="+x-x+y-y")
    for sy in (-1, 1):
        y0, y1 = sorted((sy * 0.42, sy * 0.92))
        V.box(0.0, y0, 0.0, L, y1, seat_h - 0.08, "int_ru_black", faces="+x-x+y-y")
        V.box(0.0, y0, seat_h - 0.08, L, y1, seat_h, seat, faces="+x+y-y+z")
        b0, b1 = sorted((sy * 0.92, sy * 1.05))
        V.box(0.0, b0, 0.0, L, b1, back_h, seat, faces="+x+y-y+z")
    P.info["top_z"] = 0.76
    return P


def _obox(V, cx, cy, ux, uy, hu, hv, z0, z1, mat, top=True):
    """A thin box centred at (cx, cy), half-extents hu along the unit vector (ux, uy) and hv across it."""
    vx, vy = -uy, ux
    foot = [(cx + sx * hu * ux + sy * hv * vx, cy + sx * hu * uy + sy * hv * vy)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    foot = ccw(foot)
    for a, b in edges(foot):
        quad_wall(V, a, b, z0, z1, mat)
    if top:
        V.poly([(p[0], p[1], z1) for p in foot], mat)


def high_top(h=1.05, r=0.35, stools=3, backs=True):
    """High-top table with bar chairs by the dining windows (ru_dining_windows). fix round 4 (fidelity-2): the photo's
    chairs are tall black metal bar chairs with backrests (back to ~1.1 m) on four black legs, not backless steel
    pucks; the back stands on the chair's far side from the table."""
    P = _p("high_top")
    V, C = P.visual, P.collision
    cyl(V, 0.0, 0.0, r, h - 0.04, h, "int_ru_black", n=8)
    cyl(V, 0.0, 0.0, 0.04, 0.0, h - 0.04, "int_ru_steel", n=5, top=False)
    for k in range(stools):
        a = 2 * math.pi * k / stools + 0.35
        ux, uy = math.cos(a), math.sin(a)
        cx, cy = 0.62 * ux, 0.62 * uy
        cyl(V, cx, cy, 0.18, 0.72, 0.77, "int_ru_black", n=6)
        if not backs:
            cyl(V, cx, cy, 0.025, 0.0, 0.72, "int_ru_steel", n=4, top=False)
            continue
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):        # four black legs under the seat
            lx = cx + su * 0.12 * ux - sv * 0.12 * uy
            ly = cy + su * 0.12 * uy + sv * 0.12 * ux
            _obox(V, lx, ly, ux, uy, 0.016, 0.016, 0.0, 0.72, "int_ru_black", top=False)
        bx, by = cx + 0.16 * ux, cy + 0.16 * uy                     # the backrest: two posts + a 20 cm top band
        for sv in (-1, 1):
            _obox(V, bx - sv * 0.14 * uy, by + sv * 0.14 * ux, ux, uy, 0.016, 0.016, 0.77, 0.92, "int_ru_black",
                  top=False)
        _obox(V, bx, by, ux, uy, 0.018, 0.17, 0.92, 1.1, "int_ru_black")
    K.col_box(C, -r, -r, 0.0, r, r, h, K.COL_NOCAM)
    return P


def patio_table(r=0.42, h=0.74, seats=4, rot=0.0):
    """fix round 5 (fidelity-2; ru_south_terrace_seating): a black metal patio table for the Level 1 outdoor dining
    terrace: a round black top on a centre post with a cross foot, and `seats` attached swing-out seats on curved
    black arms (round seat pads, a small rectangular back on the far side). One NO_CAM block for the top; the seats
    are visual only (as the food court's table sets)."""
    P = _p("patio_table")
    V, C = P.visual, P.collision
    cyl(V, 0.0, 0.0, r, h - 0.035, h, "int_ru_black", n=10)
    cyl(V, 0.0, 0.0, 0.035, 0.03, h - 0.035, "int_ru_black", n=5, top=False)
    for k in range(seats):
        a = 2 * math.pi * k / seats + rot + math.pi / seats
        ux, uy = math.cos(a), math.sin(a)
        # cross foot (top only: nothing lies on the floor plane)
        _obox(V, 0.29 * ux, 0.29 * uy, ux, uy, 0.25, 0.025, 0.0, 0.03, "int_ru_black", top=True)
        a = 2 * math.pi * k / seats + rot
        ux, uy = math.cos(a), math.sin(a)
        cx, cy = 0.66 * ux, 0.66 * uy
        # the arm from the post to under the seat, the seat pad, the back on the outer edge
        _obox(V, 0.35 * ux, 0.35 * uy, ux, uy, 0.31, 0.02, 0.24, 0.27, "int_ru_black", top=True)
        cyl(V, cx, cy, 0.025, 0.27, 0.43, "int_ru_black", n=4, top=False)
        cyl(V, cx, cy, 0.2, 0.43, 0.46, "int_ru_black", n=8, bottom=True)
        bx, by = cx + 0.2 * ux, cy + 0.2 * uy
        _obox(V, bx, by, ux, uy, 0.015, 0.16, 0.46, 0.84, "int_ru_black")
    K.col_box(C, -r, -r, 0.0, r, r, h, K.COL_NOCAM)
    return P


def podium(w=0.6, d=0.5, h=1.15):
    P = _p("podium")
    V, C = P.visual, P.collision
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, "int_ru_cherry", faces="+x-x+y-y+z")
    V.box(-w / 2 + 0.05, d / 2, 0.3, w / 2 - 0.05, d / 2 + 0.01, 0.8, "int_ru_dais", uvs=None, faces="+y")
    K.col_box(C, -w / 2, -d / 2, 0.0, w / 2, d / 2, h, K.COL_NOCAM)
    return P


def stage_platform(w, d, h=0.6, mat="int_ru_black", drape_h=3.0, drape=True):
    """Portable stage (ru_os_grand_ballroom_2) with a black skirt and a black pipe-and-drape behind: walkable."""
    P = _p("stage_platform")
    V, C = P.visual, P.collision
    V.box(-w / 2, -d / 2, 0.0, w / 2, d / 2, h, mat, faces="+x-x+y-y+z", mats={"+z": "int_ru_concrete_dark"})
    if drape:
        V.poly([(w / 2 + 1.0, -d / 2 - 0.3, 0.0), (-w / 2 - 1.0, -d / 2 - 0.3, 0.0), (-w / 2 - 1.0, -d / 2 - 0.3, drape_h),
                (w / 2 + 1.0, -d / 2 - 0.3, drape_h)], "int_ru_drape", normal_hint=(0, 1, 0))
    C.prism([(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)], 0.0, h, K.COL, top=K.COL)
    P.info["top_z"] = h
    return P


def free_library(w=1.2, h=1.6):
    """The atrium free library (wayfinding name): a small bookcase."""
    P = _p("free_library")
    V, C = P.visual, P.collision
    V.box(-w / 2, -0.2, 0.0, w / 2, 0.2, h, "int_ru_wood_panel", faces="+x-x-y+z")
    V.poly([(-w / 2 + 0.05, 0.19, 0.2), (w / 2 - 0.05, 0.19, 0.2), (w / 2 - 0.05, 0.19, h - 0.1), (-w / 2 + 0.05, 0.19, h - 0.1)],
           "int_ru_books", uvs=[(1, 0), (0, 0), (0, 1), (1, 1)][::-1][::-1], normal_hint=(0, 1, 0))
    K.col_box(C, -w / 2, -0.2, 0.0, w / 2, 0.2, h, K.COL_NOCAM)
    return P


def info_desk(L=3.6, d=0.8, h=1.07, front="int_ru_uf_blue", stripe=None, monitors=0):
    """Information desk (no photo found: a curved white counter with a navy front and UF-blue sign, inferred).
    Footprint: 0.866 L wide, 0.3 + d deep (local +y is the curved front).
    iteration 7 (fidelity-1 improvement 7): the white top covers every segment (it was one segment's quad, laid twice:
    the rest of the counter was open from above); optional `stripe` (a material: a band round the curved front 1.5 cm
    proud, under the lip) and `monitors` (that many staff screens on the top, their dark backs to the visitors)."""
    P = _p("info_desk")
    V, C = P.visual, P.collision
    n = 6
    pts = [(L / 2 * math.sin(math.radians(-60 + 120 * k / n)) * 1.0, 0.6 * math.cos(math.radians(-60 + 120 * k / n)) - 0.3)
           for k in range(n + 1)]
    for a, b in zip(pts, pts[1:]):
        quad_wall(V, b, a, 0.12, h, front)
        quad_wall(V, b, a, 0.0, 0.12, "int_ru_black")
        # white top lip proud of the front
        quad_wall(V, (b[0] * 1.02, b[1] + 0.04), (a[0] * 1.02, a[1] + 0.04), h - 0.06, h + 0.02, "int_ru_white")
        if stripe:
            quad_wall(V, (b[0] * 1.012, b[1] + 0.015), (a[0] * 1.012, a[1] + 0.015), h - 0.22, h - 0.14, stripe)
        a2 = (a[0] * 0.8, a[1] - d)
        b2 = (b[0] * 0.8, b[1] - d)
        V.poly([(a[0], a[1], h), (b[0], b[1], h), (b2[0], b2[1], h), (a2[0], a2[1], h)], "int_ru_white",
               normal_hint=(0, 0, 1))
    for e in (pts[0], pts[-1]):          # end panels, facing out sideways (normal on the right of a -> b)
        if e[0] > 0:
            quad_wall(V, (e[0] * 0.8, e[1] - d), (e[0], e[1]), 0.0, h, front)
        else:
            quad_wall(V, (e[0], e[1]), (e[0] * 0.8, e[1] - d), 0.0, h, front)
    for k in range(monitors):
        mx = (k + 0.5 - monitors / 2) * min(0.9, 0.8 * L / max(1, monitors))
        V.box(mx - 0.27, -0.2, h + 0.1, mx + 0.27, -0.16, h + 0.42, "int_ru_black", faces="+x-x+y-y+z")
        V.box(mx - 0.25, -0.215, h + 0.12, mx + 0.25, -0.21, h + 0.4, "int_ru_led", faces="-y", glow=True)
        V.box(mx - 0.03, -0.16, h + 0.005, mx + 0.03, -0.1, h + 0.1, "int_ru_black", faces="+x-x+y-y")
        V.box(mx - 0.12, -0.22, h + 0.005, mx + 0.12, -0.04, h + 0.015, "int_ru_black", faces="+x-x+y-y+z")
    xs = [p[0] for p in pts]
    K.col_box(C, min(xs), min(p[1] for p in pts) - d, 0.0, max(xs), max(p[1] for p in pts), h, K.COL_NOCAM)
    return P


def picnic_table():
    """Breezeway picnic table (ru_breezeway_night_commons, ru_breezeway_piers_1): concrete top + benches."""
    P = _p("picnic_table")
    V, C = P.visual, P.collision
    V.box(-0.9, -0.38, 0.72, 0.9, 0.38, 0.78, "concrete", faces="+x-x+y-y+z")
    V.box(-0.15, -0.15, 0.0, 0.15, 0.15, 0.72, "concrete", faces="+x-x+y-y")
    for sy in (-1, 1):
        V.box(-0.9, sy * 0.75 - 0.15, 0.42, 0.9, sy * 0.75 + 0.15, 0.47, "concrete", faces="+x-x+y-y+z")
        V.box(-0.1, sy * 0.75 - 0.1, 0.0, 0.1, sy * 0.75 + 0.1, 0.42, "concrete", faces="+x-x+y-y")
    K.col_box(C, -0.9, -0.9, 0.0, 0.9, 0.9, 0.78, K.COL_NOCAM)
    return P


def all_props():
    return {"lanes": bowling_lane_set(4), "booth": booth(), "billiards": billiard_table(), "arcade": arcade_cabinet(),
            "esports": esports_row(4), "lounge": lounge_chair(), "swivel": lounge_chair("int_fabric_orange", swivel=True),
            "uf_letters": uf_letters(), "gator_head": gator_head(), "storefront": storefront(5.0, "int_ru_vend_burger"),
            "senate": senate_tiers(2), "bed": bed_set(), "rows": chair_rows(3, 8, aisle_every=4),
            "round_table": round_table(), "cafe": cafe_table_set(), "ping_pong": ping_pong(), "air_hockey": air_hockey(),
            "foosball": foosball(), "podium": podium(), "stage": stage_platform(6, 3), "info_desk": info_desk(),
            "picnic": picnic_table(), "folding": folding_table(), "sofa": sofa(), "dresser": dresser_tv(),
            "led": led_frame(3.4, 2.2, 3.0), "library": free_library(), "high_top": high_top(),
            "draped": draped_table(), "coffee": coffee_table()}


def selftest(verbose=True):
    problems = []
    # triangulation: L shape, square with a hole, collinear points
    L = [(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)]
    a = sum(abs(signed_area(t)) for t in triangulate(L))
    if abs(a - 6.0) > 1e-6:
        problems.append(f"L-shape area {a}")
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(3, 3), (6, 3), (6, 7), (3, 7)]
    a = sum(abs(signed_area(t)) for t in triangulate(sq, [hole]))
    if abs(a - 88.0) > 1e-6:
        problems.append(f"square-with-hole area {a}")
    a = sum(abs(signed_area(t)) for t in triangulate([(0, 0), (2, 0), (4, 0), (4, 4), (0, 4)]))
    if abs(a - 16.0) > 1e-6:
        problems.append(f"collinear area {a}")
    pcs = grid_pieces(triangulate(sq), 3.0)
    a = sum(abs(signed_area(p)) for p in pcs)
    if abs(a - 100.0) > 1e-6:
        problems.append(f"grid pieces area {a}")
    for name, P in all_props().items():
        for p in P.visual.polys + P.collision.polys:
            if not K.known_material(p.mat):
                problems.append(f"{name}: unknown material {p.mat}")
        t = P.tris()
        if verbose:
            print(f"  {name:12s} visual {t['visual']:5d}  collision {t['collision']:4d}")
    for n, m in RU_MATERIALS.items():
        if m["size"][0] * m["size"][1] > 2048:
            problems.append(f"{n}: {m['size']} exceeds 4 KB RGBA16")
    print("selftest:", "OK" if not problems else problems)
    return problems


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--textures" in args or "--sheet" in args:
        out = None
        if "--out" in args:
            out = args[args.index("--out") + 1]
        sheet = args[args.index("--sheet") + 1] if "--sheet" in args else None
        w = write_textures(out, sheet)
        print(f"interior_kit_reitz: {len(w)} textures in {out or stage_palette.TEXTURE_DIR}")
    if "--selftest" in args:
        sys.exit(1 if selftest() else 0)


# ================================================================== stairs
def stair_flight(V, C, a, b, z0, z1, width, steps=None, tread_mat="int_ru_terrazzo", side_mat="int_ru_white",
                 soffit=True, rails=True, rail_h=1.07, col_mat="COL notslip", stringer=0.35, rail_outer_head=None,
                 rail_cap_foot=False, rail_skirt=None):
    """Open stair flight from a (bottom, z0) to b (top, z1) in plan, `width` wide (photos: white stringers and
    soffit, terrazzo treads, silver picket railings). Collision: one ramp (no-slip) + the two railings.
    rail_outer_head: None = each railing is a closed 14 cm slab (inner + outer face) along the whole flight; a length
    in metres = the outer (void-side) face only over that last stretch below the top end (iteration 6 blocking fix:
    a 14 cm two-faced rail is thinner than Mario's 50 u wall radius, so wherever a junction push left him > 43 u off
    the flight axis toward a rail, the outer face pushed him THROUGH it onto the open side - the L1 SE flight foot
    walk-off, falls_fast 19 / 1,056. The inner face alone holds him on the treads; the short outer piece at the top
    keeps the upper slab's side of the rail end closed)."""
    L = math.dist(a, b)
    if L < 0.2:
        return
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -dy, dx
    h = z1 - z0
    n = steps or max(3, int(round(h / 0.19)))
    rise, run = h / n, L / n
    w2 = width / 2

    def P(s, off, z):
        return (a[0] + dx * s + nx * off, a[1] + dy * s + ny * off, z)
    for k in range(n):
        s0, s1 = k * run, (k + 1) * run
        zt = z0 + (k + 1) * rise
        V.poly([P(s0, -w2, zt), P(s1, -w2, zt), P(s1, w2, zt), P(s0, w2, zt)], tread_mat, normal_hint=(0, 0, 1),
               ao=1.0)
        V.poly([P(s0, w2, zt - rise), P(s0, -w2, zt - rise), P(s0, -w2, zt), P(s0, w2, zt)], side_mat,
               normal_hint=(-dx, -dy, 0), ao=0.85)
    # stringers (white side plates following the slope) + soffit
    for off in (-w2, w2):
        sgn = 1 if off > 0 else -1
        q = [P(0, off, z0 - stringer), P(L, off, z1 - stringer), P(L, off, z1 + 0.12), P(0, off, z0 + 0.12)]
        V.poly(q, side_mat, normal_hint=(nx * sgn, ny * sgn, 0), ao=0.95)
        V.poly(list(reversed(q)), side_mat, normal_hint=(-nx * sgn, -ny * sgn, 0), ao=0.9)
    if soffit:
        V.poly([P(0, w2, z0 - stringer), P(L, w2, z1 - stringer), P(L, -w2, z1 - stringer), P(0, -w2, z0 - stringer)],
               side_mat, normal_hint=(0, 0, -1), ao=0.9)
    if rails:
        for off in (-w2 + 0.05, w2 - 0.05):
            pa, pb = P(0, off, z0), P(L, off, z1)
            V.poly([pa, pb, (pb[0], pb[1], pb[2] + rail_h), (pa[0], pa[1], pa[2] + rail_h)], "int_ru_picket2",
                   uvs=[(0, 0), (L / 1.1, 0), (L / 1.1, 1), (0, 1)], ao=1.0)
            # user-photo pass (user_02, C01, C05): a honey-wood handrail on the grey pickets (was a steel cap)
            V.poly([(pa[0], pa[1], pa[2] + rail_h), (pb[0], pb[1], pb[2] + rail_h), (pb[0], pb[1], pb[2] + rail_h + 0.06),
                    (pa[0], pa[1], pa[2] + rail_h + 0.06)], "int_ru_maple", ao=1.0)
            V.poly([(pb[0], pb[1], pb[2] + rail_h), (pa[0], pa[1], pa[2] + rail_h), (pa[0], pa[1], pa[2] + rail_h + 0.06),
                    (pb[0], pb[1], pb[2] + rail_h + 0.06)], "int_ru_maple", ao=1.0)
    # collision: ramp + railing blocks
    if C is not None:
        ramp = [P(0, -w2, z0), P(L, -w2, z1), P(L, w2, z1), P(0, w2, z0)]
        add_raw(C, ramp, col_mat, normal_hint=(0, 0, 1))
        if rails:
            for off in (-w2 + 0.05, w2 - 0.05):
                pa, pb = P(0, off, z0), P(L, off, z1)
                for sgn in (1, -1):
                    o = 0.07 * sgn
                    qa = pa
                    # iteration 7: rail_outer_head may be a pair (-n side, +n side), each None (full) or a length
                    roh = rail_outer_head
                    if isinstance(roh, (tuple, list)):
                        roh = roh[1] if off > 0 else roh[0]
                    if roh is not None and (sgn > 0) == (off > 0):     # the outer (void-side) face
                        if roh <= 0:
                            continue
                        qa = P(max(0.0, L - roh), off, z1 - h * min(1.0, roh / L))
                    q = [(qa[0] + nx * o, qa[1] + ny * o, qa[2] - 0.3), (pb[0] + nx * o, pb[1] + ny * o, pb[2] - 0.3),
                         (pb[0] + nx * o, pb[1] + ny * o, pb[2] + rail_h), (qa[0] + nx * o, qa[1] + ny * o, qa[2] + rail_h)]
                    C.poly(q, K.COL_NOCAM, normal_hint=(nx * sgn, ny * sgn, 0))
                # iteration 7: a rail closed on both faces from its foot gets a foot end cap across its 14 cm (walking
                # in along the rail line from the floor beside the foot, Mario entered the open slab end and both faces
                # held him inside it up the ramp, onto the balcony block top: spotfall_r L2 SE foot 1 walk)
                roh_ = rail_outer_head[1] if isinstance(rail_outer_head, (tuple, list)) and off > 0 else \
                    (rail_outer_head[0] if isinstance(rail_outer_head, (tuple, list)) else rail_outer_head)
                if roh_ is None and rail_cap_foot:
                    cq = [(pa[0] - nx * 0.07, pa[1] - ny * 0.07, pa[2] - 0.3), (pa[0] + nx * 0.07, pa[1] + ny * 0.07, pa[2] - 0.3),
                          (pa[0] + nx * 0.07, pa[1] + ny * 0.07, pa[2] + rail_h), (pa[0] - nx * 0.07, pa[1] - ny * 0.07, pa[2] + rail_h)]
                    C.poly(cq, K.COL_NOCAM, normal_hint=(-dx, -dy, 0))
        # iteration 8 (technical improvement 2): rail_skirt = a height in m above z0. Over the flight's lower
        # stretch (ramp below z0 + rail_skirt) each rail's outer face comes down to the storey floor as one NOCAM
        # triangle under the band's lower edge, and a cross cap closes the pocket under the treads at that point:
        # from the floor beside the Ground flight Mario walked under the band (its lower edge above his +60 wall
        # check beyond s ~ 1.55 m) into the space under the treads and stepped up through them (railside7c 88)
        if rails and rail_skirt:
            s1 = L * min(1.0, rail_skirt / h)
            sa = L * min(1.0, 0.25 / h)
            zb = z0 - 0.05
            zs1 = z0 + h * s1 / L - 0.3
            if s1 > sa + 0.2:
                for off in (-w2 + 0.05, w2 - 0.05):
                    sgn = 1 if off > 0 else -1
                    o = off + 0.07 * sgn
                    if sgn > 0:
                        tri = [P(sa, o, zb), P(s1, o, zb), P(s1, o, zs1)]
                    else:
                        tri = [P(s1, o, zb), P(sa, o, zb), P(s1, o, zs1)]
                    C.poly(tri, K.COL_NOCAM, normal_hint=(nx * sgn, ny * sgn, 0))
                cap = [P(s1, -w2 - 0.02, zb), P(s1, w2 + 0.02, zb), P(s1, w2 + 0.02, zs1), P(s1, -w2 - 0.02, zs1)]
                C.poly(cap, K.COL_NOCAM, normal_hint=(dx, dy, 0))
                # rendered too (no invisible wall): a white side panel under each stringer down to the floor (its
                # top on the stringer's lower edge, 2 cm outside the stringer plane) and the cap's face
                sv = L * min(1.0, (stringer - 0.05) / h)
                zv1 = z0 + h * s1 / L - stringer
                if s1 > sv + 0.2:
                    for off in (-w2 + 0.05, w2 - 0.05):
                        sgn = 1 if off > 0 else -1
                        o = off + 0.07 * sgn
                        V.poly([P(sv, o, zb), P(s1, o, zb), P(s1, o, zv1)], side_mat,
                               normal_hint=(nx * sgn, ny * sgn, 0), ao=0.85)
                    V.poly([P(s1 + 0.01, -w2 - 0.02, zb), P(s1 + 0.01, w2 + 0.02, zb), P(s1 + 0.01, w2 + 0.02, zv1),
                            P(s1 + 0.01, -w2 - 0.02, zv1)], side_mat, normal_hint=(dx, dy, 0), ao=0.7)
    return {"len": L, "angle_deg": math.degrees(math.atan2(h, L)), "steps": n}


def seg_intersect(p, d, poly):
    """Smallest t >= 0 where the ray p + t d crosses an edge of poly (or None)."""
    best = None
    for a, b in edges(poly):
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
        u = ((a[0] - p[0]) * d[1] - (a[1] - p[1]) * d[0]) / den
        if t >= 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return best
