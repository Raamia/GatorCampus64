"""Mission anchor points of a built stage, ray-cast against the stage's real collision (inside Blender,
called by build_stage.py after the meshes and the spawn exist).

The Swamp (swamp_points): spawn, the level-script stars, the press box top + the Kickoff climb, the
field (centre, the four end-zone corners, both goalposts with their crossbars, field-goal tees), the
concourse race (start / finish + checkpoints around the stadium's cross-aisle at grade, checked for a
continuous floor), the apron race and stair sprint, act spots (spirit pads, usher, cannon, Wing Cap,
flyover rings, poles), secret spots and the stadium gates, written to data/uf/swamp_points.json
(build_stage.py; a --report-dir test build writes it next to the report instead).

Course 2, Reitz Union & Engineering (reitz_points): spawn, the anchors of every design act of
docs/game_design.md 7.2 (act1_rooftop climb + lift + star target, act2_robotics_lab atrium / crane shaft /
L7 ledge, act3_wind_tunnel vent / button / column, act4_robot_roundup lawn / release points / dock,
act5_meal_swipe_tokens 8 red coins + star, act6_packet_relay start / finish / an A*-found ground route /
cannon), every landmark spot, poles, secrets and the pickups, written to data/uf/reitz_points.json.

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


# ------------------------------------------------------------------ Course 2: Reitz Union & Engineering
REITZ_LAWN_HUBS = [(-385.0, -191.0), (-311.0, -154.0), (-268.0, -212.0)]   # North Lawn radial-walk hubs
NORTH_LAWN_AREA = "w294203169"
REITZ_ROUTE_STEP_M = 2.0


def _game_box(S, x0, x1, y0, y1, z0=None, z1=None):
    """Map-metre box -> game-unit box {x0, x1, z0, z1[, y0, y1]} (Z flips: north = -Z)."""
    gx = sorted((int(round((x0 - S.cx) * 100)), int(round((x1 - S.cx) * 100))))
    gz = sorted((int(round(-(y0 - S.cy) * 100)), int(round(-(y1 - S.cy) * 100))))
    out = {"x0": gx[0], "x1": gx[1], "z0": gz[0], "z1": gz[1]}
    if z0 is not None:
        out.update(y0=int(round(z0 * 100)), y1=int(round(z1 * 100)))
    return out


def _walkable(S, pr, x, y):
    """Ground cell test for the relay route (map metres): grade floor and 0.7 m of room."""
    sx, sy = x - S.cx, y - S.cy
    fz = pr.floor(sx, sy, 1.5)
    if fz is None or abs(fz) > 0.3:
        return False
    return pr.clearance(sx, sy, fz + 0.6, 1.0) >= 0.7


def ground_route(S, pr, start, goal, box, step=REITZ_ROUTE_STEP_M):
    """Shortest ground-level walk (map metres) from start to goal inside box (x0, y0, x1, y1): A* on a
    step-metre grid; a cell must have a grade floor and room (_walkable), a move must not cross a wall
    (rays at 0.4 / 1.2 m), cells with < 1.5 m of room cost more (keeps to the middle of walks). The path
    is then cut to straight legs that stay walkable (sampled every metre). -> [(x, y, 0.0), ...] or None."""
    import heapq
    x0, y0, x1, y1 = box
    nx_, ny_ = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    cache = {}

    def P_(i, j):
        return (x0 + i * step, y0 + j * step)

    def ok(c):
        if c not in cache:
            i, j = c
            cache[c] = 0 <= i < nx_ and 0 <= j < ny_ and _walkable(S, pr, *P_(i, j))
        return cache[c]

    def snap(p):
        best = None
        for di in range(-4, 5):
            for dj in range(-4, 5):
                c = (int(round((p[0] - x0) / step)) + di, int(round((p[1] - y0) / step)) + dj)
                if ok(c):
                    d = math.dist(P_(*c), p[:2])
                    if best is None or d < best[0]:
                        best = (d, c)
        return None if best is None else best[1]

    s, g = snap(start), snap(goal)
    if s is None or g is None:
        return None
    gp = P_(*g)
    openh = [(math.dist(P_(*s), gp), 0.0, s)]
    came, cost = {s: None}, {s: 0.0}
    room = {}
    while openh:
        _, c0, c = heapq.heappop(openh)
        if c == g:
            break
        if c0 > cost.get(c, 1e18):
            continue
        px, py = P_(*c)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == dj == 0:
                    continue
                n = (c[0] + di, c[1] + dj)
                if not ok(n):
                    continue
                qx, qy = P_(*n)
                d = math.dist((px, py), (qx, qy))
                dx, dy = (qx - px) / d, (qy - py) / d
                blocked = any((pr.ray(px - S.cx, py - S.cy, h, dx, dy, d) or 99.0) < d for h in (0.4, 1.2))
                if blocked:
                    continue
                mz = pr.floor((px + qx) / 2 - S.cx, (py + qy) / 2 - S.cy, 1.5)     # stay on grade between cells
                if mz is None or abs(mz) > 0.3:
                    continue
                if n not in room:
                    room[n] = pr.clearance(qx - S.cx, qy - S.cy, 0.6, 1.5)
                nc = c0 + d * (1.0 if room[n] >= 1.5 else 1.6)
                if nc < cost.get(n, 1e18):
                    cost[n] = nc
                    came[n] = c
                    heapq.heappush(openh, (nc + math.dist((qx, qy), gp), nc, n))
    if g not in came:
        return None
    cells = []
    c = g
    while c is not None:
        cells.append(P_(*c))
        c = came[c]
    cells.reverse()
    pts = [tuple(start[:2])] + cells + [tuple(goal[:2])]

    def clear_leg(a, b):
        L = math.dist(a, b)
        if L < 1e-6:
            return True
        n = max(1, math.ceil(L))
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        for k in range(n + 1):
            x, y = a[0] + dx * L * k / n, a[1] + dy * L * k / n
            fz = pr.floor(x - S.cx, y - S.cy, 1.5)
            if fz is None or abs(fz) > 0.3:
                return False
            if pr.clearance(x - S.cx, y - S.cy, 0.6, 0.6) < 0.6:
                return False
        return all((pr.ray(a[0] - S.cx, a[1] - S.cy, h, dx, dy, L) or 99.0) >= L for h in (0.4, 1.2))

    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not clear_leg(pts[i], pts[j]):
            j -= 1
        out.append(pts[j])
        i = j
    return [(x, y, 0.0) for x, y in out]


def reitz_token_spots(S):
    """The eight MEAL SWIPE TOKENS (design 7.2 act 5 = course act 2) in design order, as (point name, map point
    (x, y, z = floor), note). Shared by reitz_points (measured into act5_meal_swipe_tokens.red_coins) and
    stage_pickups.reitz_pickups (no level coin on a token spot in the token act). Fix round (fun review):
    Weil Hall's token moved from its courtyard (grade) up the roof run to the 24 m ridge, Malachowsky's from
    the 4.3 m entrance canopy to the 12 m glass box of its stepped glass stair, so the hunt climbs the stage's
    two best routes."""
    weil = _extras(S, "weil_hall")
    mal = _extras(S, "malachowsky_hall")
    plaza = _extras(S, "engineering_plaza").get("spots", {})
    asp = _extras(S, "reitz_amphitheater").get("spots", {})
    dres = getattr(S, "reitz_dressing", None) or {}
    bstats = {b.get("id"): b for b in S.stats.get("buildings", [])}
    out = []
    tables = dres.get("tables", [])
    if tables:
        out.append(("token_gator_corner_patio", tuple(tables[0]),
                    "top of a patio table south-east of Gator Corner Dining Center (0.76 m)"))
    if "sculpture_top" in plaza:
        out.append(("token_engineering_plaza_sculpture", tuple(plaza["sculpture_top"]),
                    "the steel sculpture's top girder (4.0 m; step plates on its west column)"))
    if "liberty_pond_fountain" in asp:
        out.append(("token_liberty_pond_fountain", tuple(asp["liberty_pond_fountain"]),
                    "the hexagonal fountain float in the middle of Liberty Pond (top 0.3 m over the water)"))
    book = bstats.get("w150821701")
    if book and book.get("climb_route"):
        out.append(("token_bookstore_awning", tuple(book["climb_route"]["canopy_m"]),
                    "the UF Bookstore's east entrance canopy (3.0 m), facing Liberty Pond"))
    bw = dres.get("boardwalk", [])
    if bw:
        best = max(bw, key=lambda r: r["length_m"])
        out.append(("token_ravine_boardwalk", tuple(best["mid_m"]), "the middle of the Reitz Ravine boardwalk (deck 0.45 m)"))
    wroute = weil.get("climb_route_m", [])
    ridge = [p for p in wroute[:-1] if len(p) > 2 and p[2] >= 23.9]
    if ridge:
        out.append(("token_weil_roof_ridge", tuple(ridge[-1]),
                    "Weil Hall's 24 m ridge at the end of the roof run (courtyard downspout -> addition roof -> "
                    "roof stair -> ridge), before the tower deck"))
    mroute = mal.get("climb_route_m", [])
    box = next((p for p in mroute if len(p) > 2 and p[2] >= 11.9), None)
    if box:
        out.append(("token_malachowsky_glass_stair", tuple(box),
                    "the 12 m glass box of Malachowsky's stepped glass stair (canopy -> boxes -> roof)"))
    cool = bstats.get("w150858524")
    bb = next((x for x in S.data["buildings"] if x["id"] == "w150858524"), None)
    if cool and bb:
        out.append(("token_cooling_tower_catwalk", (bb["c"][0], bb["c"][1] - 12.0, cool.get("eave", 10.0)),
                    "the cooling towers' roof deck (catwalk), south half (climb route on the east face)"))
    return out


def reitz_points(S, probe, spawn, stars, warp_nodes, level, slot):
    """-> dict for data/uf/reitz_points.json: anchor points of Course 2 (docs/game_design.md 7.2) measured
    on the built collision, grouped by the design's acts (design numbering; course.lua decides the act
    order, docs/flow.md 5.1), plus every landmark spot, the North Lawn and the pickups."""
    P = Points(S, probe)
    ru = _extras(S, "reitz_union")
    rs = ru.get("spots", {})
    rmk = ru.get("markers", {})
    amph = _extras(S, "reitz_amphitheater")
    asp = amph.get("spots", {})
    weil = _extras(S, "weil_hall")
    ws = weil.get("spots", {})
    clock = _extras(S, "engineering_clock_tower").get("spots", {})
    plaza = _extras(S, "engineering_plaza").get("spots", {})
    mal = _extras(S, "malachowsky_hall")
    ms = mal.get("spots", {})
    mmk = mal.get("markers", {})
    dres = getattr(S, "reitz_dressing", None) or {}
    bstats = {b.get("id"): b for b in S.stats.get("buildings", [])}

    def spot(d, k, name=None, src="", **kw):
        if k not in d:
            P.flags.append(f"{name or k}: spot {k!r} missing ({src})")
            return None
        return P.ground(name or k, d[k], source=f"{src} {k}".strip(), **kw)

    out = {
        "schema": "sgl64.reitz_points/1",
        "generated_by": "tools/campus/build_stage.py reitz_eng (stage_points.reitz_points)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
        "stage": "reitz_eng", "level": level, "slot": slot, "level_const": "LEVEL_WF", "course": "COURSE_WF",
        "center_m": list(S.data["center"]),
        "coordinates": {
            "map_m": "x = east, y = north, z = metres above grade (the whole stage is flat at grade 0); origin = "
                     "Century Tower",
            "game": "X = (x - cx) * 100, Y = z * 100, Z = -(y - cy) * 100 with (cx, cy) = center_m = (-470, -293); "
                    "Y is the ray-cast collision floor (Mario's feet). Objects that hover (stars, coins) add their "
                    "own offset.",
            "game_box": "{x0, x1, z0, z1[, y0, y1]} in game units (x0 < x1, z0 < z1)",
            "game_yaw": "0 = faces +Z (south), 0x4000 = east, 0x8000 = north, 0xC000 = west",
            "floor_m": "collision floor measured by ray-casting the built level (STAND_FROM_M above the design "
                       "height, straight down)"},
        "note": "Anchor points for the Course 2 mission author (docs/game_design.md 7.2, Reitz Union & Engineering "
                "Quad, slot wf / LEVEL_WF, door 2 = The Hub). Re-generated on every `build_stage.py -- reitz_eng` "
                "from the built collision. Points with a 'check' key did not measure as designed. 'actN_' keys use "
                "the DESIGN act numbers (1 Rooftop of the Reitz, 2 Remote Robotics Lab (2P), 3 Weil Wind Tunnel, "
                "4 Rogue Robot Roundup, 5 Meal Swipe Tokens, 6 Data Packet Relay); the course acts are numbered by "
                "course.lua (playable acts 1..n, solo first, docs/flow.md 5.1). The level script has NO "
                "level-script star (stars = []): every mission spawns its own (spawn_default_star from the "
                "controller loop, star id = course act - 1), or build_stage.py STAGE_STARS gets the act 1 entry.",
    }
    sx, sy = spawn["map_m"]
    out["spawn"] = dict(P.ground("spawn_0x0A", (sx, sy, 0.0), facing=spawn["facing_deg"],
                                 note="stage entry spawn (bhvSpinAirborneWarp, MARIO_POS) on the North Lawn strip off "
                                      "the Reitz Union's north colonnade, facing the lawn's radial walks; the object "
                                      "hovers 1 m above this floor"),
                        node="0x0A", spawn_object_game=spawn["game_units"])
    out["warp_nodes"] = warp_nodes
    out["stars"] = stars

    # ---- design act 1: Rooftop of the Reitz
    src = "reitz_reitz_union.py spot"
    a1 = {"note": "Climb the Reitz Union from the ravine side: brick terraces 1.5 / 3.0 / 4.5 -> copper awnings "
                  "6.7 / 8.9 / 11.1 -> ballroom roof 13.2 -> AC unit 15.4 -> podium roof 17.6 -> (window-washer "
                  "lift, its 9 m cable pole, or the four east sunshade ledges 19.8-25.2) -> tower roof 26.4 / "
                  "parapet 27.0 -> elevator penthouse 28.8 (star). Second route from the South Terrace "
                  "(2.0 -> canopy 5.6 -> light shelves 7.8 / 10.0 -> food court roof 11.5 -> AC 13.8 -> green roof "
                  "16.0 -> podium 17.6). Every rise is <= 2.4 m except the 3.6 m double jump onto the canopy."}
    a1["climb_route"] = [P.ground(f"rooftop_climb_{i:02d}", p, clear=0.3)
                         for i, p in enumerate(ru.get("climb_route_m", []))]
    a1["south_route"] = [P.ground(f"rooftop_south_{i:02d}", p, clear=0.3)
                         for i, p in enumerate(rmk.get("climb_route_south_m", []))]
    a1["points"] = [r for r in (
        spot(rs, "roof_star", "rooftop_goal_penthouse", src, clear=0.5,
             note="top of the elevator penthouse (7 x 6 m) on the tower roof: the goal / star spot"),
        spot(rs, "tower_roof_center", "rooftop_tower_roof_center", src),
        spot(rs, "tower_roof", "rooftop_tower_roof_east", src),
        spot(rs, "podium_roof_west", "rooftop_podium_west", src),
        spot(rs, "podium_roof_north", "rooftop_podium_north", src),
        spot(rs, "podium_roof_south", "rooftop_podium_south", src),
        spot(rs, "podium_roof_east", "rooftop_podium_east", src),
        spot(rs, "ballroom_roof_center", "rooftop_ballroom_roof", src),
        spot(rs, "ravine_terrace_1", "rooftop_start_ravine_terrace", src, clear=0.3,
             note="first brick terrace (1.5 m) on the W wing's south wall, by the Reitz Union Drive loop: CLIMB HERE"),
        spot(rs, "green_roof_center", "rooftop_green_roof", src),
        spot(rs, "food_court_roof", "rooftop_food_court_roof", src),
    ) if r]
    star_spot = rs.get("roof_star")
    if star_spot:
        g = P.ground("rooftop_star_target", star_spot, clear=0.5)
        if g.get("floor_m") is not None:
            g = dict(g, map_m=[g["map_m"][0], g["map_m"][1], r2(g["floor_m"] + 1.2)],
                     game=game_units(S, star_spot[0], star_spot[1], g["floor_m"] + 1.2),
                     note="star position (1.2 m over the penthouse floor, the Swamp's STAR_UP_M)")
        a1["star_target"] = g
    lift = rmk.get("window_washer_lift")
    if lift:
        b, t = lift["bottom_m"], lift["top_m"]
        a1["window_washer_lift"] = {
            "bottom": P.ground("rooftop_lift_bottom", b, clear=0.0,
                               note="foot of the lift track on the podium roof (the platform's floor height here)"),
            "top": P.air("rooftop_lift_top", tuple(t),
                         note="top of the track = the tower parapet top (27.0); step east onto the tower roof"),
            "travel_m": lift.get("travel_m"), "platform_half_m": lift.get("platform_half_m"),
            "facing_deg": lift.get("facing_deg"), "note": lift.get("note")}
    a1["climb_zone"] = dict(_game_box(S, -523.5, -359.5, -337.0, -241.5),
                            note="the Reitz Union footprint bbox (OSM w863211313), game units")
    a1["milestones_m"] = {"ballroom_roof": 13.2, "podium_roof": 17.6, "tower_roof": 26.4, "penthouse": 28.8}
    out["act1_rooftop"] = a1

    # ---- design act 2: Remote Robotics Lab (2P) in Malachowsky Hall's atrium
    src = "reitz_malachowsky.py spot"
    a2 = {"note": "Malachowsky's 7-storey vertical commons (atrium 26 x 17 m, 32.2 m tall) through the 6 m north "
                  "door. The operator console and the crane platform are mission objects; the L7 star ledge (28.0 m, "
                  "3.5 m deep along the south wall) cannot be reached on foot (no stair is modelled)."}
    a2["points"] = [r for r in (
        spot(ms, "atrium_console", "robotics_console", src, note="operator console spot (atrium floor, west of the entry)"),
        spot(ms, "crane_start", "robotics_crane_start", src, note="crane platform start (atrium floor)"),
        spot(ms, "atrium_floor", "robotics_atrium_center", src),
        spot(ms, "atrium_entry", "robotics_atrium_entry", src),
        spot(ms, "north_entrance", "robotics_north_entrance", src),
        spot(ms, "star_ledge", "robotics_star_ledge", src, clear=0.3, from_m=1.0,
             note="L7 ledge, floor 28.0 m (underside 27.4)"),
        spot(ms, "server_room_dock", "robotics_server_alcove", src, clear=0.5),
    ) if r]
    ab = mmk.get("atrium_box_m")
    if ab:
        a2["atrium_box"] = dict(_game_box(S, ab["x"][0], ab["x"][1], ab["y"][0], ab["y"][1], ab["z"][0], ab["z"][1]),
                                note=ab.get("note"))
        # the floor of the whole atrium, every 2 m (the platform / players' area)
        n_ok, misses = 0, []
        x = ab["x"][0] + 1.0
        while x <= ab["x"][1] - 1.0:
            y = ab["y"][0] + 1.0
            while y <= ab["y"][1] - 1.0:
                fz = probe.floor(x - S.cx, y - S.cy, 1.5)
                if fz is not None and abs(fz) <= 0.05:
                    n_ok += 1
                else:
                    misses.append([round(x, 1), round(y, 1), fz])
                y += 2.0
            x += 2.0
        a2["atrium_floor_check"] = {"samples_ok": n_ok, "misses": misses[:20]}
        if misses:
            P.flags.append(f"robotics atrium floor: {len(misses)} samples off grade")
    sl = mmk.get("star_ledge_m")
    if sl:
        a2["star_ledge_box"] = dict(_game_box(S, sl["x"][0], sl["x"][1], sl["y"][0], sl["y"][1], sl["z"], sl["z"]),
                                    note=sl.get("note"))
    if "crane_start" in ms and "star_ledge" in ms:
        c, l = ms["crane_start"], ms["star_ledge"]
        shaft = []
        for z in (3.0, 7.0, 11.0, 15.0, 19.0, 23.0, 27.0, 29.0):
            r = P.air(f"robotics_crane_shaft_{int(z):02d}m", (c[0], c[1], z))
            r["clearance_m"] = r2(probe.clearance(c[0] - S.cx, c[1] - S.cy, z, 3.0))
            shaft.append(r)
        ceil = probe.ceiling(c[0] - S.cx, c[1] - S.cy, 0.1, 40.0)
        a2["crane_shaft"] = {"column": shaft, "ceiling_m": None if ceil is None else r2(ceil),
                             "to_ledge_m": r2(math.dist(c[:2], l[:2])),
                             "note": "air points straight above crane_start (clearance = room around the column at "
                                     "that height); the ledge edge is to_ledge_m south"}
        g = P.ground("robotics_star_target", l, clear=0.3, from_m=1.0)
        if g.get("floor_m") is not None:
            g = dict(g, map_m=[g["map_m"][0], g["map_m"][1], r2(g["floor_m"] + 1.2)],
                     game=game_units(S, l[0], l[1], g["floor_m"] + 1.2), note="star 1.2 m over the L7 ledge")
        a2["star_target"] = g
    sr = mmk.get("server_room_m")
    if sr:
        a2["server_room_box"] = _game_box(S, sr["x"][0], sr["x"][1], sr["y"][0], sr["y"][1], sr["z"][0], sr["z"][1])
    a2["glass_stair_climb"] = [P.ground(f"malachowsky_climb_{i:02d}", p, clear=0.3)
                               for i, p in enumerate(mal.get("climb_route_m", []))]
    out["act2_robotics_lab"] = a2

    # ---- design act 3: Weil Wind Tunnel (vent beside the Weil Cooling Towers)
    a3 = {"note": "The wind-tunnel floor vent (stage dressing: a steel grate on a 0.4 m curb, r 2.6 m) east of the "
                  "Weil Cooling Towers (11 m, roof deck 10.0 inside a 1 m parapet). Mission: a big floor button "
                  "(button) turns on a vertical-wind column over the vent (SURFACE_VERTICAL_WIND object, "
                  "ACT_VERTICAL_WIND) that lifts riders past the towers' roof to the star; someone holds the button "
                  "or the fan spins down. The towers' east face has the generator's climb route (entrance canopy "
                  "3 m + ledges 6 / 9 m) up to the roof = the cooling-tower catwalk."}
    vent = dres.get("wind_vent")
    if vent:
        vx, vy = vent["map_m"]
        a3["vent"] = P.ground("wind_vent_grate", (vx, vy, vent["grate_m"]), clear=0.0,
                              note=f"centre of the vent grate (radius {vent['radius_m']} m)")
        col_pts = []
        for z in (2.0, 5.0, 8.0, 11.0, 14.0, 17.0, 20.0, 24.0):
            r = P.air(f"wind_column_{int(z):02d}m", (vx, vy, z))
            r["clearance_m"] = r2(probe.clearance(vx - S.cx, vy - S.cy, z, 6.0))
            col_pts.append(r)
        ceil = probe.ceiling(vx - S.cx, vy - S.cy, vent["grate_m"] + 0.1, 60.0)
        a3["column"] = {"points": col_pts, "open_sky": ceil is None,
                        "note": "air points over the vent; clearance = room around the column (the towers' east wall "
                                "is the nearest surface)"}
        a3["star_target"] = P.air("wind_star_above_cooling_towers", (vx, vy, 17.0),
                                  note="over the vent, 6 m above the cooling towers' parapet (11 m): the top of the "
                                       "column")
        # the button: open grade north of the vent (same courtyard), away from the column
        for dy_ in (22.0, 20.0, 18.0, 24.0, 16.0):
            b = P.ground("wind_button", (vx, vy + dy_, 0.0), clear=2.0)
            if "check" not in b:
                break
            P.flags = [f for f in P.flags if not f.startswith("wind_button:")]
        if "check" in b:
            P.flags.append(f"wind_button: {b['check']}")
        a3["button"] = dict(b, note="big floor button spot (open grade north of the vent; ~20 m apart, so one "
                                    "player holds it while another rides)")
    cool = bstats.get("w150858524")
    bb = next((x for x in S.data["buildings"] if x["id"] == "w150858524"), None)
    if cool and bb:
        a3["cooling_tower_roof"] = P.ground("cooling_tower_roof", (bb["c"][0], bb["c"][1], cool.get("eave", 10.0)),
                                            note="Weil Cooling Towers roof deck (OSM w150858524, generic flat roof)")
        if cool.get("climb_route"):
            cr = cool["climb_route"]
            a3["cooling_tower_climb"] = dict(cr, canopy=P.ground("cooling_tower_canopy", tuple(cr["canopy_m"]),
                                                                  clear=0.3))
    out["act3_wind_tunnel"] = a3

    # ---- design act 4: Rogue Robot Roundup (North Lawn) + the charging dock by Liberty Pond
    a4 = {"note": "Robots flee across the Reitz North Lawn (OSM w294203169, the open radial-walk lawn); carry them to "
                  "the charging dock (stage dressing, a 0.25 m concrete pad) on the lawn south-east of Liberty Pond."}
    lawn = next((a for a in S.data["areas"] if a["id"] == NORTH_LAWN_AREA), None)
    px0, py0, px1, py1 = S.data["play"]
    if lawn:
        ring = [(min(max(x, px0), px1), min(max(y, py0), py1)) for x, y in lawn["ring"]]
        a4["lawn_polygon_game"] = [[int(round((x - S.cx) * 100)), int(round(-(y - S.cy) * 100))] for x, y in ring]
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        a4["lawn_box"] = _game_box(S, min(xs), max(xs), min(ys), max(ys))
        # robot release points: open lawn (>= 3 m of room), spread out
        from stage_geom import point_in_poly
        cands = []
        for gx in range(int(min(xs)) + 4, int(max(xs)) - 3, 6):
            for gy in range(int(min(ys)) + 4, int(max(ys)) - 3, 6):
                if not point_in_poly((gx, gy), ring):
                    continue
                fz = probe.floor(gx - S.cx, gy - S.cy, 1.5)
                if fz is None or abs(fz) > 0.05:
                    continue
                if probe.clearance(gx - S.cx, gy - S.cy, 0.6, 3.0) < 3.0:
                    continue
                cands.append((gx, gy))
        picked = []
        hubc = (-330.0, -190.0)
        for c in sorted(cands, key=lambda c: math.dist(c, hubc)):
            if all(math.dist(c, q) >= 22.0 for q in picked):
                picked.append(c)
            if len(picked) >= 8:
                break
        a4["robot_release_points"] = [P.ground(f"robot_release_{k}", (x, y, 0.0), clear=3.0)
                                      for k, (x, y) in enumerate(picked)]
    dock = dres.get("charging_dock")
    if dock:
        a4["charging_dock"] = P.ground("robot_charging_dock", (dock["map_m"][0], dock["map_m"][1], dock["pad_m"]),
                                       clear=0.0, note="top of the dock pad (3 x 2.4 m, 0.25 m); post on its north edge")
    a4["lawn_hubs"] = [P.ground(f"north_lawn_hub_{k}", (x, y, 0.0), clear=1.5,
                                note="centre of a radial-walk hub of the North Lawn") for k, (x, y) in
                       enumerate(REITZ_LAWN_HUBS)]
    out["act4_robot_roundup"] = a4

    # ---- design act 5: Meal Swipe Tokens (8 red coins), from reitz_token_spots (shared with stage_pickups)
    rc = [P.ground(name, pt, clear=0.0, note=note) for name, pt, note in reitz_token_spots(S)]
    book = bstats.get("w150821701")
    out["act5_meal_swipe_tokens"] = {
        "red_coins": [r for r in rc if r],
        "star_spot": P.ground("token_star_north_lawn", (REITZ_LAWN_HUBS[0][0], REITZ_LAWN_HUBS[0][1], 0.0), clear=1.5,
                              note="fallback star spot (the North Lawn hub next to Wertheim): the course act 2 mission "
                                   "drops its star 1.5 m over the token found last (wf_reitz_missions.lua starAt)"),
        "note": "design 7.2 act 5 locations, in its order (Weil's and Malachowsky's moved up their climbs in the fix "
                "round); coin heights are the floor, add the coin's hover"}

    # ---- design act 6: Data Packet Relay (Weil server closet -> Malachowsky server room)
    a6 = {"note": "Carry the packet from Weil Hall's server closet (the lower-floor lab niche on the north facade) to "
                  "Malachowsky's server alcove (inside the atrium, west side) in 75 s. The route is the shortest "
                  "ground-level walk on the built collision (A* on a 2 m grid, then straight legs), checked every "
                  "metre."}
    st_ = ws.get("server_closet")
    fin = ms.get("server_room_dock")
    if st_ and fin:
        a6["start"] = spot(ws, "server_closet", "relay_start_weil_server_closet", "reitz_weil_eng_clocktower.py",
                           clear=0.5)
        a6["finish"] = spot(ms, "server_room_dock", "relay_finish_malachowsky_server_room", "reitz_malachowsky.py",
                            clear=0.5)
        route = ground_route(S, probe, st_, fin, (-600.0, -560.0, -330.0, -25.0))
        if route is None:
            P.flags.append("relay route: no ground route found")
        else:
            wps = [P.ground(f"relay_wp_{i:02d}", p, clear=0.5) for i, p in enumerate(route)]
            a6["route"] = {"waypoints": wps, "game_path": [w["game"] for w in wps],
                           "length_m": round(sum(math.dist(a[:2], b[:2]) for a, b in zip(route, route[1:])), 1),
                           "straight_line_m": round(math.dist(st_[:2], fin[:2]), 1),
                           "path_check": P.path("relay_path", route, z_design=0.0, tol=0.5),
                           "note": "ground level all the way; steps up to 0.5 m (a curb, the boardwalk deck) are "
                                   "walk-ups in SM64 (find_floor reaches 78 units up)"}
    a6["cannon"] = {
        "spot": P.ground("relay_cannon_north_lawn", (-497.0, -224.0, 0.0), clear=2.0,
                         note="North Lawn cannon (west end of the lawn strip, by Reitz Union Drive)"),
        "aim_target": P.ground("relay_cannon_target", (-536.0, -312.0, 0.0), clear=1.5,
                               note="landing hint: the Reitz Union Drive loop south-west of the Reitz, ~96 m away (a "
                                    "vanilla cannon shot flies ~100 m at 45 degrees, apex ~25 m: it cannot clear the "
                                    "27 m tower, so it goes round the ravine side)")}
    out["act6_packet_relay"] = a6

    # ---- every landmark spot, measured (secondary routes, secrets, doors)
    lm = {}
    for slug, d in (("reitz_union", rs), ("reitz_amphitheater", asp), ("weil_hall", ws), ("engineering_clock_tower", clock),
                    ("engineering_plaza", plaza), ("malachowsky_hall", ms)):
        rec = {}
        for k, v in d.items():
            if k in ("window_washer_lift_top", "clock_tower_apex"):
                rec[k] = P.air(f"{slug}_{k}", tuple(v), note="not a floor (the lift's top / the tower's roof ridge)")
                continue
            if k in ("suggested_stage_spawn",):
                continue
            g = P.ground(f"{slug}_{k}", v, clear=0.0, tol=0.6)
            rec[k] = g
        lm[slug] = rec
    lm["weil_hall_roof_run"] = [P.ground(f"weil_roof_run_{i:02d}", p, clear=0.3, tol=0.6)
                                for i, p in enumerate(weil.get("climb_route_m", []))]
    # the courtyard downspout's top is a pole handstand, not a floor (the module says so)
    for r in lm["weil_hall_roof_run"]:
        if r["name"] == "weil_roof_run_01" and "check" in r:
            P.flags = [f for f in P.flags if not f.startswith("weil_roof_run_01:")]
            r["note"] = "top of the courtyard downspout pole (handstand 13.8 m), not a floor"
            r.pop("check", None)
    out["landmark_spots"] = lm
    poles = []
    for q in rmk.get("poles", []) + weil.get("markers", {}).get("poles", []):
        g = P.ground(f"pole_{q['name']}", q["base_m"], clear=0.0)
        poles.append(dict(g, height_m=q["height_m"], behavior="bhvPoleGrabbing",
                          bparams="0x00%02X0000" % int(round(q["height_m"] * 10)), note=q.get("note")))
    out["poles"] = poles
    out["secret_spots"] = [r for r in (
        P.ground("secret_malachowsky_penthouse", tuple(mal["top_platform"]["center_m"]) +
                 (mal["top_platform"]["z_m"],), clear=0.5) if mal.get("top_platform") else None,
        spot(ws, "tower_deck", "secret_weil_tower_deck", "reitz_weil_eng_clocktower.py", clear=0.5),
        spot(rs, "stair_penthouse_top", "secret_reitz_stair_penthouse", "reitz_reitz_union.py", clear=0.3),
        spot(ms, "rooftop_terrace", "secret_malachowsky_rooftop_terrace", "reitz_malachowsky.py", clear=0.5),
        spot(rs, "north_colonnade_top", "secret_reitz_colonnade_top", "reitz_reitz_union.py", clear=0.3),
        P.ground("secret_bookstore_roof", (book["climb_route"]["facade_mid_m"][0] - 15.0,
                                           book["climb_route"]["facade_mid_m"][1], book["climb_route"]["roof_m"]),
                 clear=0.5) if book and book.get("climb_route") else None,
    ) if r]
    out["north_lawn"] = {"hubs": a4["lawn_hubs"], "area": NORTH_LAWN_AREA}
    out["dressing"] = dres
    out["climb_routes_generic"] = {b.get("name"): b["climb_route"] for b in S.stats.get("buildings", [])
                                   if b.get("climb_route")}
    out["pickups"] = getattr(S, "stage_pickups", None)
    out["checks"] = P.flags
    return out
