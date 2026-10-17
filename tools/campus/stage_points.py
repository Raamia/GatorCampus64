"""Mission anchor points of a built stage, ray-cast against the stage's real collision (inside Blender,
called by build_stage.py after the meshes and the spawn exist).

The Swamp (swamp_points): spawn, the level-script stars, the press box top + the Kickoff climb, the
field (centre, the four end-zone corners, both goalposts with their crossbars, field-goal tees), the
concourse race (start / finish + checkpoints around the stadium's cross-aisle at grade, checked for a
continuous floor), the apron race and stair sprint, act spots (spirit pads, usher, cannon, Wing Cap,
flyover rings, poles), secret spots and the stadium gates, written to data/uf/swamp_points.json
(build_stage.py; a --report-dir test build writes it next to the report instead).

Every ground point is re-measured: the floor is ray-cast straight down from STAND_FROM_M above the
module's design height, so the stored height is the collision Mario will stand on. A point whose floor
is more than TOL_M off its design height, or that has less than MIN_CLEAR_M of room around it, is
flagged ("check": ...). Air points (flyover rings) store the floor under them instead.

Coordinates: map metres (x = east, y = north, z = height above grade, origin = Century Tower) and game
units of the stage: X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 (stages.json centre).
Game yaw: 0 faces +Z (south), 0x4000 +X (east), 0x8000 north, 0xC000 west.
"""
import importlib
import json
import math
import time

STAND_FROM_M = 1.5       # ray start above the design height (below any tunnel roof / canopy)
TOL_M = 0.6              # floor vs design height tolerance
MIN_CLEAR_M = 0.9        # horizontal room around a standing point (0.6 m above the floor)
RACE_STEP_M = 1.0        # concourse path sampling


def game_units(S, x, y, z):
    return [int(round((x - S.cx) * 100)) + 0, int(round(z * 100)) + 0, int(round(-(y - S.cy) * 100)) + 0]


def r2(v):
    return round(float(v), 2) + 0.0          # + 0.0: no "-0.0" in the JSON


def game_yaw(facing_deg):
    """Compass facing (0 = north, 90 = east) -> SM64 yaw (0 = +Z = south)."""
    return int(round(((180.0 - facing_deg) % 360.0) / 360.0 * 65536)) & 0xFFFF


class Points:
    def __init__(self, S, probe):
        self.S, self.probe = S, probe
        self.flags = []

    def ground(self, name, p, note=None, facing=None, tol=TOL_M, clear=MIN_CLEAR_M, from_m=STAND_FROM_M,
               source=None):
        """Standing point at map (x, y) near design height z: ray-cast floor, clearance, headroom."""
        S, pr = self.S, self.probe
        x, y = p[0], p[1]
        zd = float(p[2]) if len(p) > 2 else 0.0
        sx, sy = x - S.cx, y - S.cy
        fz = pr.floor(sx, sy, zd + from_m)
        rec = {"name": name}
        if fz is None:
            rec.update(map_m=[r2(x), r2(y), r2(zd)], game=game_units(S, x, y, zd), floor_m=None,
                       check="no collision floor under this point")
            self.flags.append(f"{name}: no floor")
        else:
            cl = pr.clearance(sx, sy, fz + 0.6, 3.0)
            ceil = pr.ceiling(sx, sy, fz + 0.05, 30.0)
            rec.update(map_m=[r2(x), r2(y), r2(fz)], game=game_units(S, x, y, fz),
                       floor_m=r2(fz), clearance_m=r2(cl),
                       headroom_m=None if ceil is None else r2(ceil - fz))
            if abs(fz - zd) > tol:
                rec["check"] = f"floor {fz:.2f} m, design height {zd:.2f} m"
                self.flags.append(f"{name}: floor {fz:.2f} vs design {zd:.2f}")
            elif cl < clear:
                rec["check"] = f"only {cl:.2f} m of room around it"
                self.flags.append(f"{name}: clearance {cl:.2f}")
        if facing is not None:
            rec["facing_deg"] = round(facing, 1)
            rec["game_yaw"] = "0x%04X" % game_yaw(facing)
        if note:
            rec["note"] = note
        if source:
            rec["source"] = source
        return rec

    def air(self, name, p, note=None):
        """Point in the air (rings): stored as given, plus the floor under it."""
        S, pr = self.S, self.probe
        x, y, z = p
        fz = pr.floor(x - S.cx, y - S.cy, z - 0.5)
        rec = {"name": name, "map_m": [r2(x), r2(y), r2(z)], "game": game_units(S, x, y, z),
               "air": True, "floor_below_m": None if fz is None else r2(fz),
               "height_above_floor_m": None if fz is None else r2(z - fz)}
        if note:
            rec["note"] = note
        return rec

    def path(self, name, pts, z_design=None, closed=False, note=None, step=RACE_STEP_M, tol=0.35):
        """Walkable polyline (map metres, z = design floor height per vertex): samples the floor every
        `step` metres and checks for gaps, steps and walls across the way."""
        S, pr = self.S, self.probe
        seq = list(pts) + ([pts[0]] if closed else [])
        samples = []
        worst_dz, gaps, walls, length = 0.0, [], [], 0.0
        for a, b in zip(seq, seq[1:]):
            L = math.dist(a[:2], b[:2])
            n = max(1, math.ceil(L / step))
            dx, dy = (b[0] - a[0]) / max(L, 1e-9), (b[1] - a[1]) / max(L, 1e-9)
            for k in range(n):
                t = k / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                za = (a[2] if len(a) > 2 else 0.0)
                zb = (b[2] if len(b) > 2 else 0.0)
                zd = za + (zb - za) * t if z_design is None else z_design
                fz = pr.floor(x - S.cx, y - S.cy, zd + STAND_FROM_M)
                if fz is None:
                    gaps.append([round(x, 1), round(y, 1)])
                    continue
                samples.append(fz)
                worst_dz = max(worst_dz, abs(fz - zd))
                hit = min((pr.ray(x - S.cx, y - S.cy, fz + h, dx, dy, step) or 9.9) for h in (0.4, 1.2))
                if hit < step * 0.999:
                    walls.append([round(x, 1), round(y, 1), round(fz, 2)])
            length += L
        rec = {"name": name, "length_m": round(length, 1), "closed": closed, "samples": len(samples),
               "floor_range_m": [r2(min(samples)), r2(max(samples))] if samples else None,
               "max_floor_deviation_m": r2(worst_dz), "gaps": gaps[:20], "walls_across": walls[:20]}
        if gaps or walls or (z_design is not None and worst_dz > tol):
            rec["check"] = f"{len(gaps)} samples without floor, {len(walls)} with a wall across the way, " \
                           f"max floor deviation {worst_dz:.2f} m"
            self.flags.append(f"{name}: {rec['check']}")
        if note:
            rec["note"] = note
        return rec


def _module(name):
    try:
        return importlib.import_module(name)
    except Exception:  # noqa: BLE001
        return None


def _extras(S, slug):
    e = next((e for e in S.landmark_entries if e.get("slug") == slug), None)
    return e or {}


def concourse_loop(SS, d=None, start_seg="N"):
    """The stadium cross-aisle (at grade, between the lower bowl's last riser and the main band) as a
    closed loop of map points, starting at the middle of segment start_seg (the north gate) and running
    counter-clockwise seen from above (N -> NW -> W -> SW -> S -> SE -> E -> NE)."""
    if d is None:
        d = (SS.D_AISLE0 + SS.D_AISLE1) / 2
    r = SS.ring(d)
    i = SS.SI[start_seg]
    mid = ((r[i][0] + r[(i + 1) % 12][0]) / 2, (r[i][1] + r[(i + 1) % 12][1]) / 2)
    order = [mid] + [r[(i + 1 + k) % 12] for k in range(12)]   # mid -> end of N -> ... -> start of N
    return [(*SS.to_map(u, v), 0.0) for u, v in order]


def swamp_points(S, probe, spawn, stars, warp_nodes, level, slot):
    """-> dict for data/uf/swamp_points.json (see the module docstring)."""
    P = Points(S, probe)
    st = _extras(S, "stadium")
    spots = st.get("spots", {})
    markers = st.get("markers", {})
    oc = _extras(S, "oconnell_center").get("spots", {})
    gym = _extras(S, "florida_gym").get("spots", {})
    SS = _module("landmarks.swamp_stadium")
    src = "swamp_stadium.py spot"

    def sp(name, key=None, **kw):
        k = key or name
        if k not in spots:
            P.flags.append(f"{name}: stadium spot {k!r} missing")
            return None
        return P.ground(name, spots[k], source=f"{src} {k}", **kw)

    out = {
        "schema": "sgl64.swamp_points/1",
        "generated_by": "tools/campus/build_stage.py swamp (stage_points.swamp_points)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
        "stage": "swamp", "level": level, "slot": slot, "level_const": "LEVEL_BOB", "course": "COURSE_BOB",
        "center_m": list(S.data["center"]),
        "coordinates": {
            "map_m": "x = east, y = north, z = metres above grade (the field is 10 m below grade); origin = Century "
                     "Tower",
            "game": "X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 with (cx, cy) = center_m; Y is the "
                    "ray-cast collision floor (Mario's feet). Objects that hover (stars, coins) add their own offset.",
            "game_yaw": "0 = faces +Z (south), 0x4000 = east, 0x8000 = north, 0xC000 = west",
            "floor_m": "collision floor measured by ray-casting the built level (STAND_FROM_M above the design "
                       "height, straight down)"},
        "note": "Anchor points for the mission author (docs/game_design.md 7.1). Re-generated on every "
                "`build_stage.py -- swamp` from the built collision. Points with a 'check' key did not "
                "measure as designed. 'actN_' keys use the design doc's act numbers; the course acts "
                "(course.lua, docs/flow.md 5) are: 1 Kickoff = design 1, 2 Stair Sprint = design 5, "
                "3 Chomp Chorus = design 3, 4-6 coming soon (design 2 Mascot, 4 Tailgate, 6 Flyover).",
    }
    # ---- spawn + exits
    sx, sy = spawn["map_m"]
    out["spawn"] = dict(P.ground("spawn_0x0A", (sx, sy, 0.0), facing=spawn["facing_deg"],
                                 note="stage entry spawn (bhvSpinAirborneWarp, MARIO_POS); the object hovers "
                                      "1 m above this floor"),
                        node="0x0A", spawn_object_game=spawn["game_units"])
    out["warp_nodes"] = warp_nodes
    out["stars"] = stars
    # ---- press box / West Skybox Tower (act 1)
    top = st.get("top_platform", {})
    pb = []
    if top:
        c = top["center_m"]
        pb.append(P.ground("press_box_roof_center", (c[0], c[1], top["z_m"]), note=top.get("note")))
    for name, key in (("press_box_roof_star_spot", "press_box_roof_star"), ("light_frame_top", None),
                      ("bull_gator_deck", None), ("west_rim_climb_start", "west_rim")):
        r = sp(name, key)
        if r:
            pb.append(r)
    climb = [P.ground(f"kickoff_climb_{i:02d}", p, clear=0.3) for i, p in enumerate(st.get("climb_route_m", []))]
    out["press_box"] = {"points": pb, "kickoff_climb_route": climb,
                        "note": "Act 1 route: west rim (20 m) -> 11 ledges on the tower's south bay -> Bull Gator "
                                "Deck (44 m) -> 10 camera decks -> press box roof (66 m) -> light frames (71 m)"}
    # ---- field
    fld = []
    for name, key in (("field_center", None), ("endzone_corner_NW", "endzone_button_NW"),
                      ("endzone_corner_NE", "endzone_button_NE"), ("endzone_corner_SW", "endzone_button_SW"),
                      ("endzone_corner_SE", "endzone_button_SE"), ("goalpost_north_base", None),
                      ("goalpost_south_base", None), ("fg_tee_north_20yd", None), ("fg_tee_north_30yd", None),
                      ("fg_tee_south_20yd", None), ("field_tunnel_mouth", "tunnel_field_tunnel_mouth")):
        r = sp(name, key, clear=0.0 if "goalpost" in name else MIN_CLEAR_M,
               note="foot of the goalpost (the post is collision)" if "goalpost" in name else None)
        if r:
            fld.append(r)
    for name, key in (("goalpost_north_crossbar", "fg_crossbar_north"),
                      ("goalpost_south_crossbar", "fg_crossbar_south")):
        r = sp(name, key, clear=0.0, from_m=0.6,
               note="top of the crossbar (10 ft, standable collision); the uprights rise 9.1 m above it")
        if r:
            fld.append(r)
    out["field"] = {"points": fld, "level_m": markers.get("levels_m", {}).get("field"),
                    "note": "end-zone corners: 1 m inside the end line / sideline corner (clear field-level spots, "
                            "e.g. for the corner buttons)"}
    # ---- races
    races = {}
    if SS is not None:
        loop = concourse_loop(SS)
        cps = [P.ground("concourse_start_finish", loop[0], facing=270.0,
                        note="on the cross-aisle in front of the north gate (gate_N), running west (counter-"
                             "clockwise seen from above)")]
        names = ["N_side_west_end", "NW_corner", "W_side_north_end", "W_side_south_end", "SW_corner",
                 "S_side_west_end", "S_side_east_end", "SE_corner", "E_side_south_end", "E_side_north_end",
                 "NE_corner", "N_side_east_end"]
        for k, p in enumerate(loop[1:]):
            q = loop[(k + 2) % len(loop)] if k + 2 < len(loop) else loop[0]
            heading = math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360.0
            cps.append(P.ground(f"concourse_cp_{k + 1:02d}_{names[k]}", p, facing=heading,
                                note="facing = running direction to the next checkpoint"))
        races["concourse_loop"] = {
            "start_finish": cps[0], "checkpoints": cps[1:],
            "path_check": P.path("concourse_loop_path", loop, z_design=0.0, closed=True),
            "game_path": [c["game"] for c in cps] + [cps[0]["game"]],
            "note": "cross-aisle at grade (2.5 m wide) all the way round the bowl, between the lower bowl's "
                    "top riser and the main stands; checkpoints at the 12 ring vertices (corner chords). "
                    "Every gate (N, NE, E x2, SE, SW, W, NW) opens onto it."}
    for key, name, note in (("race_loop_m", "apron_loop", "field-level apron loop 3.5 m outside the sidelines"),
                            ("stair_sprint_m", "stair_sprint", "Course act 2 STADIUM STAIR SPRINT (design act 5): "
                                                                "north end zone -> east stands -> east rim -> "
                                                                "south ramp terrace (20 m)")):
        pts = markers.get(key)
        if not pts:
            continue
        wps = [P.ground(f"{name}_{i:02d}", p, clear=0.5) for i, p in enumerate(pts)]
        rec = {"waypoints": wps, "game_path": [w["game"] for w in wps], "note": note}
        if key == "race_loop_m":
            rec["path_check"] = P.path(f"{name}_path", pts, closed=True)
        races[name] = rec
    out["races"] = races
    # ---- act spots
    acts = {}
    acts["act2_mascot_arena"] = sp("midfield_mascot_arena")
    acts["act3_spirit_pads"] = [r for r in (sp(f"spirit_pad_{k}") for k in range(1, 5)) if r]
    acts["act1_usher_npc"] = sp("usher_npc")
    acts["act1_cannon_north_endzone"] = sp("cannon_north_endzone")
    acts["act6_wing_cap_box"] = sp("wing_cap_box", "south_board_top", note="Wing Cap box on top of the south "
                                   "video board (stand point; put the box ~1.5 m up)")
    acts["act6_south_board_climb"] = [P.ground(f"south_board_climb_{i:02d}", p, clear=0.3)
                                      for i, p in enumerate(markers.get("scoreboard_climb_m", []))]
    acts["act6_flyover_rings"] = [P.air(f"flyover_ring_{i + 1}", tuple(p)) for i, p in
                                  enumerate(markers.get("flyover_rings_m", []))]
    poles = []
    for q in markers.get("poles", []):
        # a pole stands on a floor (goalposts, the Bull Gator Deck) or hangs at its design base (the east
        # light masts start at the parapet top, 21 m, outside the rim: grab them from the rim)
        g = P.ground(f"pole_{q['name']}", q["base_m"], clear=0.0)
        if "check" in g and q["base_m"][2] > 0.5:
            P.flags = [f for f in P.flags if not f.startswith(f"pole_{q['name']}:")]
            g = P.air(f"pole_{q['name']}", tuple(q["base_m"]),
                      note="hanging pole: its base is in the air at the design height (no floor under it)")
        poles.append(dict(g, height_m=q["height_m"], behavior="bhvPoleGrabbing",
                          bparams="0x00%02X0000" % int(round(q["height_m"] * 10))))
    acts["poles"] = poles
    acts["act4_red_coin_candidates"] = [r for r in (
        sp("rc_south_ramp_terrace", "south_ramp_terrace"),
        sp("rc_south_board_catwalk", "south_board_catwalk", clear=0.5),
        sp("rc_field_tunnel", "field_tunnel_mid"),
        sp("rc_under_sunshine_seats", "under_sunshine_promenade"),
        sp("rc_gatehouse_roof", "gatehouse_roof"),
        P.ground("rc_exactech_arena_entry", oc["entry_niche"], source="swamp_oconnell_gym.py entry_niche")
        if "entry_niche" in oc else None,
    ) if r]
    dres = getattr(S, "swamp_dressing", None) or {}
    for k, t in enumerate(dres.get("tents", [])):
        acts["act4_red_coin_candidates"].append(
            P.ground(f"rc_tailgate_tent_{k:02d}", (t["map_m"][0], t["map_m"][1] + 0.3, t["peak_m"]), clear=0.0,
                     source="stage_dressing.py tailgate tent",
                     note="peak of a tailgate canopy roof (18 degree pyramid; the floor is the roof)"))
    for st_ in dres.get("statues", []):
        acts["act4_red_coin_candidates"].append(
            P.ground("rc_" + st_["name"].lower().replace(" ", "_").replace("(", "").replace(")", "") + "_plinth",
                     (st_["map_m"][0], st_["map_m"][1], st_["back_m"]), clear=0.0, source="stage_dressing.py statue"))
    out["act_spots"] = acts
    # ---- secret spots (off the main routes)
    sec = [sp(n, k, clear=0.3) for n, k in (("secret_gatehouse_roof", "gatehouse_roof"),
                                 ("secret_north_board_top", "north_board_top"),
                                 ("secret_south_board_top", "south_board_top"),
                                 ("secret_light_frame_top", "light_frame_top"),
                                 ("secret_east_light_catwalk", "east_light_catwalk_center"),
                                 ("secret_sunshine_top_row", "sunshine_top_row"))]
    for name, d_, key in (("secret_exactech_crown_hatch", oc, "crown_hatch"),
                          ("secret_exactech_marquee_top", oc, "marquee_top"),
                          ("secret_florida_gym_tower_deck", gym, "tower_deck"),
                          ("secret_florida_gym_ridge_north", gym, "ridge_north")):
        if key in d_:
            sec.append(P.ground(name, d_[key], source=f"swamp_oconnell_gym.py {key}", clear=0.5))
    for g in getattr(S, "swamp_secrets", []):
        sec.append(P.ground(g["name"], g["map_m"], note=g.get("note"), source="stage_dressing.py"))
    out["secret_spots"] = [r for r in sec if r]
    # ---- landmarks' other routes + gates
    out["exactech_arena"] = {"climb_route": [P.ground(f"exactech_climb_{i:02d}", p, clear=0.3) for i, p in
                                             enumerate(_extras(S, "oconnell_center").get("climb_route_m", []))],
                             "spots": {k: P.ground(f"exactech_{k}", v, clear=0.3, tol=1.5) for k, v in oc.items()},
                             "note": "spot heights are measured on the collision (the dome cap spots sit ~1.2 m "
                                     "below the module's nominal 29.5 m)"}
    out["florida_gym"] = {"climb_route": [P.ground(f"gym_climb_{i:02d}", p, clear=0.3) for i, p in
                                          enumerate(_extras(S, "florida_gym").get("climb_route_m", []))],
                          "spots": {k: P.ground(f"gym_{k}", v, clear=0.3) for k, v in gym.items()}}
    gates = []
    for g in markers.get("gates", []):
        # the module's tunnel_<name>_mouth / _exit spots sit 0.5 m inside the mouth and 1.5 m past the
        # exit (the gate's own mouth / exit lines are exactly on the seams between floors)
        m = spots.get(f"tunnel_{g['name']}_mouth", g["mouth_m"])
        x = spots.get(f"tunnel_{g['name']}_exit", g["exit_m"])
        gates.append(dict(P.ground(f"{g['name']}_mouth", m, clear=0.5),
                          exit=P.ground(f"{g['name']}_exit", x, clear=0.5), kind=g["kind"],
                          width_m=g["width_m"], clear_height_m=g["clear_height_m"],
                          exit_facing_deg=g["exit_facing_deg"]))
    out["stadium_gates"] = gates
    out["dressing"] = getattr(S, "swamp_dressing", None)
    # coins / hearts / 1-ups / Goombas / poles placed in the level script (stage_pickups.py, measured there)
    out["pickups"] = getattr(S, "stage_pickups", None)
    out["checks"] = P.flags
    return out


def write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
