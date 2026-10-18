"""Pickups, enemies and poles a stage build places in its level script (inside Blender, called by
build_stage.py once the meshes exist, with the CollisionProbe of the real collision).

Ambient Mario yellow coins and coin formations are disabled across the campus maps. Mission-specific red-token
objectives remain separate. Recovery hearts, 1-ups, poles, and other mission props are still placed. Goombas are
back on the outdoor stages as UF's rivals (mods/sgl64/sgl_rivals.lua dresses them as USF Bulls and FSU Seminoles);
the interiors (build_interior.py: Placer(..., rivals=False)) stay free of them, for the stealth and hide-and-seek
missions.

The Swamp (swamp_pickups):
  * recovery hearts at the foot of the climb (west rim), on the Bull Gator Deck and half way up the
    camera decks; 1-ups on the hardest secret spots;
  * the stadium module's poles (markers["poles"]): goalposts, the 22.5 m pole from the Bull Gator Deck
    to the press box roof (an alternative to the 10 camera-deck hops), the south board leg and the
    hanging east light-mast poles.
Course 2, Reitz Union & Engineering (reitz_pickups): hearts, 1-ups, Bob-ombs on the act 1 climb, Koopa shells,
and the Reitz Union's and Weil
Hall's poles (see the function docstring).
Every active pickup position is checked against the collision. Failing items are skipped with a "SGL WARNING"
(and listed in the report).

Engine notes (SM64 / coopdx v1.5.1):
  bhvCoinFormation (MODEL_NONE) bparam2 = shape: 0 = line of 5 along the object's facing (1.6 m apart),
  2 = horizontal ring of 8 (r 3 m); each coin drops onto the floor below (searched from 3 m above the
  object). bhvYellowCoin (MODEL_YELLOW_COIN) floats where it is placed. MODEL_HEART, MODEL_GOOMBA,
  MODEL_BLACK_BOBOMB and MODEL_KOOPA_SHELL are common0 models: the level script needs
  JUMP_LINK(script_func_global_1) (build_stage.py STAGE_COMMON0_MODELS adds it). bhvPoleGrabbing: bparam2 =
  pole height in 10 cm. bhvBobomb (bparams 0) patrols / chases and respawns after exploding; bhvKoopaShell
  spins in place until ridden.
Coordinates: map metres (x east, y north, z up, origin Century Tower); the stage-local position for
L.add_object is (x - cx, y - cy, z).
"""
import importlib
import math

TOL_M = 0.6            # coin floor vs design height
COIN_UP_M = 0.6        # single coins float this high over their floor (Mario standing there touches them)
HEART_UP_M = 1.0
ONEUP_UP_M = 0.6
LINE_STEP_M = 1.6      # coin formation line spacing (160 units)
RING_R_M = 3.0         # coin formation ring radius (300 units)
FORMATION_SEARCH_M = 3.0
MIN_ROOM_M = 0.5       # a formation coin needs this much room around it (not inside a wall)
DISABLED_WORLD_PICKUPS = frozenset({"coin", "coin_line", "coin_ring"})


def _module(name):
    try:
        return importlib.import_module(name)
    except Exception:  # noqa: BLE001
        return None


def _extras(S, slug):
    return next((e for e in S.landmark_entries if e.get("slug") == slug), None) or {}


def bearing(a, b):
    """Compass bearing (0 = north, 90 = east) from map point a to b."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def lerp(a, b, t):
    za = a[2] if len(a) > 2 else 0.0
    zb = b[2] if len(b) > 2 else 0.0
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, za + (zb - za) * t)


class Placer:
    def __init__(self, S, probe, rivals=True):
        self.S, self.probe = S, probe
        self.rivals = rivals    # place Goombas (the rival mascots); False in the interiors
        self.items = []
        self.skipped = []

    def _floor(self, x, y, z_from):
        return self.probe.floor(x - self.S.cx, y - self.S.cy, z_from)

    def _skip(self, name, why):
        self.skipped.append({"name": name, "why": why})
        print(f"SGL WARNING: pickup {name}: {why}; skipped")

    def _add(self, kind, name, x, y, z, behavior, model, bparams="0x00000000", facing=0.0, coins=0, acts=None):
        # Keep these out at the shared placement boundary so outdoor stages and every interior builder agree,
        # including direct Placer._add callers such as Lake Alice's cypress-knee breadcrumbs.
        if kind in DISABLED_WORLD_PICKUPS or (kind == "goomba" and not self.rivals):
            return
        S = self.S
        self.items.append({
            "kind": kind, "name": name, "map_m": [round(x, 2), round(y, 2), round(z, 2)],
            "stage": (x - S.cx, y - S.cy, z), "game": [int(round((x - S.cx) * 100)), int(round(z * 100)),
                                                       int(round(-(y - S.cy) * 100))],
            "behavior": behavior, "model": model, "bparams": bparams, "facing_deg": round(facing, 1),
            "coins": coins, "acts": acts})

    def floor_at(self, name, p, tol=TOL_M, from_m=1.5):
        zd = p[2] if len(p) > 2 else 0.0
        fz = self._floor(p[0], p[1], zd + from_m)
        if fz is None or abs(fz - zd) > tol:
            self._skip(name, f"floor {fz} at design height {zd:.2f} m")
            return None
        return fz

    def coin(self, name, p, up=COIN_UP_M, quiet=False, acts=None):
        """One coin over its floor; acts = the acts it exists in (None = all: OBJECT, else OBJECT_WITH_ACTS)."""
        fz = self.floor_at(name, p) if not quiet else self._floor(p[0], p[1], (p[2] if len(p) > 2 else 0.0) + 1.5)
        if fz is not None:
            self._add("coin", name, p[0], p[1], fz + up, "bhvYellowCoin", "MODEL_YELLOW_COIN", coins=1, acts=acts)
        return fz is not None

    def _formation_ok(self, name, pts, zd, quiet=False):
        for (x, y) in pts:
            fz = self._floor(x, y, zd + FORMATION_SEARCH_M)
            room = self.probe.clearance(x - self.S.cx, y - self.S.cy, zd + 0.6, 1.0) if fz is not None else 0.0
            if fz is None or abs(fz - zd) > TOL_M or room < MIN_ROOM_M:
                if not quiet:
                    self._skip(name, f"a coin at ({x:.1f}, {y:.1f}) would drop to {fz} (design {zd:.2f} m, "
                                     f"room {room:.2f} m)")
                return False
        return True

    def coin_line(self, name, center, facing, quiet=False):
        """5 coins along `facing` through `center` (map metres; z = design floor). -> placed?"""
        fz = self.floor_at(name, center) if not quiet else self._floor(center[0], center[1], center[2] + 1.5)
        if fz is None:
            return False
        f = math.radians(facing)
        dx, dy = math.sin(f), math.cos(f)
        pts = [(center[0] + dx * LINE_STEP_M * (i - 2), center[1] + dy * LINE_STEP_M * (i - 2)) for i in range(5)]
        if self._formation_ok(name, pts, fz, quiet):
            self._add("coin_line", name, center[0], center[1], fz, "bhvCoinFormation", "MODEL_NONE", "0x00000000",
                      facing, coins=5)
            return True
        return False

    def coin_ring(self, name, center, fallback_facings=(90.0, 0.0)):
        """Ring of 8 (r 3 m); on a top too small for it, a line of 5 along one of fallback_facings, or
        one coin."""
        fz = self.floor_at(name, center)
        if fz is None:
            return
        pts = [(center[0] + RING_R_M * math.sin(k * math.pi / 4), center[1] + RING_R_M * math.cos(k * math.pi / 4))
               for k in range(8)]
        if self._formation_ok(name, pts, fz, quiet=True):
            self._add("coin_ring", name, center[0], center[1], fz, "bhvCoinFormation", "MODEL_NONE", "0x00020000",
                      0.0, coins=8)
            return
        c = (center[0], center[1], fz)
        for f in fallback_facings:
            if self.coin_line(name + " (line)", c, f, quiet=True):
                return
        self.coin(name + " (single)", c)

    def heart(self, name, p):
        fz = self.floor_at(name, p, tol=1.0)
        if fz is not None:
            self._add("heart", name, p[0], p[1], fz + HEART_UP_M, "bhvRecoveryHeart", "MODEL_HEART")

    def one_up(self, name, p):
        fz = self.floor_at(name, p, tol=1.5)
        if fz is not None:
            self._add("1up", name, p[0], p[1], fz + ONEUP_UP_M, "bhv1Up", "MODEL_1UP")

    def goomba(self, name, p, facing=0.0, room=1.2):
        fz = self.floor_at(name, p)
        if fz is None:
            return
        cl = self.probe.clearance(p[0] - self.S.cx, p[1] - self.S.cy, fz + 0.6, 3.0)
        if cl < room:
            self._skip(name, f"only {cl:.2f} m of room")
            return
        # a regular Goomba drops one coin when stomped
        self._add("goomba", name, p[0], p[1], fz, "bhvGoomba", "MODEL_GOOMBA", "0x00000000", facing, coins=1)

    def bobomb(self, name, p, facing=0.0, room=1.5):
        """A black Bob-omb (common0 MODEL_BLACK_BOBOMB): patrols, chases and explodes; vanilla respawns it."""
        fz = self.floor_at(name, p)
        if fz is None:
            return
        cl = self.probe.clearance(p[0] - self.S.cx, p[1] - self.S.cy, fz + 0.6, 3.0)
        if cl < room:
            self._skip(name, f"only {cl:.2f} m of room")
            return
        self._add("bobomb", name, p[0], p[1], fz, "bhvBobomb", "MODEL_BLACK_BOBOMB", "0x00000000", facing)

    def shell(self, name, p, room=2.0):
        """A ride gator (common0 MODEL_KOOPA_SHELL, drawn as a saddled gator by actors/koopa_shell): rests facing
        its spawn yaw until someone jumps on it (mods/sgl64/sgl_ride_gator.lua)."""
        fz = self.floor_at(name, p)
        if fz is None:
            return
        cl = self.probe.clearance(p[0] - self.S.cx, p[1] - self.S.cy, fz + 0.4, 4.0)
        if cl < room:
            self._skip(name, f"only {cl:.2f} m of room")
            return
        self._add("shell", name, p[0], p[1], fz, "bhvKoopaShell", "MODEL_KOOPA_SHELL")

    def open_ground(self, x, y):
        """Grade (z 0) at map (x, y), not under a roof or inside a building (connector coins)."""
        fz = self._floor(x, y, 1.5)
        if fz is None or abs(fz) > 0.3:
            return False
        return not self.probe.inside(x - self.S.cx, y - self.S.cy, 0.6)

    def pole(self, name, base, height_m):
        """bhvPoleGrabbing on its floor, or hanging at its design base (no floor there)."""
        zd = base[2]
        fz = self._floor(base[0], base[1], zd + 0.5)
        z = fz if (fz is not None and abs(fz - zd) <= 0.5) else zd
        tenth = int(round(height_m * 10))
        if not 1 <= tenth <= 255:
            self._skip(name, f"height {height_m} m does not fit bparam2 (10 cm units, max 25.5 m)")
            return
        self._add("pole", name, base[0], base[1], z, "bhvPoleGrabbing", "MODEL_NONE", "0x00%02X0000" % tenth)
        self.items[-1]["height_m"] = height_m
        self.items[-1]["hanging"] = z != fz


def swamp_pickups(S, probe):
    """-> (items, skipped) for the Swamp (module docstring)."""
    P = Placer(S, probe)
    st = _extras(S, "stadium")
    spots = st.get("spots", {})
    markers = st.get("markers", {})
    climb = st.get("climb_route_m", [])
    oc = _extras(S, "oconnell_center").get("spots", {})
    gym = _extras(S, "florida_gym").get("spots", {})
    SS = _module("landmarks.swamp_stadium")
    SP = _module("stage_points")

    # ---- act 1 climb: rim (0) -> ledges (1..11) -> Bull Gator Deck (12) -> decks (13..22) -> roof (23)
    for i, p in enumerate(climb):
        if 1 <= i <= 11:
            P.coin(f"climb coin ledge {i:02d}", p)
        elif 13 <= i <= 22:
            P.coin(f"climb coin deck {i - 12:02d}", p)
    if "west_rim" in spots:
        P.heart("heart west rim (climb start)", spots["west_rim"])
    if "bull_gator_deck" in spots:
        P.heart("heart Bull Gator Deck", spots["bull_gator_deck"])
    if len(climb) > 17:
        P.heart("heart camera deck 5", climb[17])

    # ---- act 2 stair sprint: the flat rim run (waypoints 5 -> 6 -> 7 -> 8): coin lines + 2 Goombas
    sprint = markers.get("stair_sprint_m", [])
    if len(sprint) >= 9:
        for a, b, tag in ((5, 6, "east rim"), (6, 7, "south-east rim"), (7, 8, "south rim")):
            pa, pb = sprint[a], sprint[b]
            f = bearing(pa, pb)
            for t in (0.25, 0.75):
                P.coin_line(f"sprint coins {tag} {int(t * 100)}", lerp(pa, pb, t), f)
        P.goomba("goomba sprint east rim", lerp(sprint[5], sprint[6], 0.5), bearing(sprint[6], sprint[5]))
        P.goomba("goomba sprint south rim", lerp(sprint[7], sprint[8], 0.5), bearing(sprint[8], sprint[7]))
        if len(sprint) > 9:
            P.heart("heart South Ramp terrace (sprint finish)", sprint[9])

    # ---- concourse (cross-aisle at grade): from the north gate west to the tower, and round the south
    if SS is not None and SP is not None:
        loop = SP.concourse_loop(SS)              # 0 = north gate, then counter-clockwise (N -> W -> S -> E)
        n = len(loop)
        for k in (0, 1, 2, 3, 5, 6, 8, 10):
            a, b = loop[k], loop[(k + 1) % n]
            P.coin_line(f"concourse coins {k:02d}", lerp(a, b, 0.5), bearing(a, b))
        P.goomba("goomba concourse north", lerp(loop[0], loop[1], 0.8), bearing(loop[1], loop[0]))
        P.goomba("goomba concourse west", lerp(loop[3], loop[4], 0.5), bearing(loop[4], loop[3]))
        P.goomba("goomba concourse east", lerp(loop[9], loop[10], 0.5), bearing(loop[10], loop[9]))

    # ---- field: midfield ring, apron lines along both sidelines
    if "field_center" in spots:
        P.coin_ring("field coins midfield ring", spots["field_center"])
    apron = markers.get("race_loop_m", [])
    if len(apron) >= 4:
        for k in range(min(len(apron), 8)):
            a, b = apron[k], apron[(k + 1) % len(apron)]
            if math.dist(a[:2], b[:2]) > 60.0:       # the long sidelines only
                for t in (0.3, 0.7):
                    P.coin_line(f"apron coins {k} {int(t * 100)}", lerp(a, b, t), bearing(a, b))

    # ---- Courtyard of Champions (spawn) -> north gate: a line to follow, two rowdy fans
    gate = spots.get("tunnel_gate_N_exit")
    court = spots.get("north_courtyard")
    if gate and court:
        P.coin_line("courtyard coins to the north gate", lerp(court, gate, 0.4), bearing(court, gate))
        side = bearing(court, gate) + 90.0
        mid = lerp(court, gate, 0.6)          # ~28 m from the spawn: not on top of arriving players
        for k, s in enumerate((-1, 1)):
            off = (mid[0] + math.sin(math.radians(side)) * 8.0 * s, mid[1] + math.cos(math.radians(side)) * 8.0 * s,
                   mid[2])
            P.goomba(f"goomba courtyard {k}", off, bearing(off, court))

    # ---- secrets: coin rings on the roof tops, 1-ups on the hardest ones
    for key in ("gatehouse_roof", "north_board_top", "south_board_top"):
        if key in spots:
            P.coin_ring(f"secret coins {key}", spots[key])
    if "light_frame_top" in spots:
        P.one_up("1-up light frame top (71 m)", spots["light_frame_top"])
    if "crown_hatch" in oc:
        P.one_up("1-up Exactech Arena crown", oc["crown_hatch"])
    if "tower_deck" in gym:
        P.one_up("1-up Florida Gym tower deck", gym["tower_deck"])

    # ---- poles (stadium module markers): climbable from their floor, or hanging (east light masts)
    for q in markers.get("poles", []):
        P.pole(f"pole {q['name']}", q["base_m"], q["height_m"])
    return P.items, P.skipped


def summary(items, skipped):
    coins = sum(i["coins"] for i in items if i["kind"] != "goomba")
    kinds = {}
    for i in items:
        kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
    return {"coins_placed": coins, "coins_with_goombas": coins + sum(i["coins"] for i in items if i["kind"] == "goomba"),
            "objects": len(items), "by_kind": kinds, "skipped": skipped,
            "items": [{k: v for k, v in i.items() if k != "stage"} for i in items]}


# ------------------------------------------------------------------ Course 2: Reitz Union & Engineering
# North Lawn: the three hubs of its radial walks (map metres, from the OSM walk network)
REITZ_LAWN_HUBS = [(-385.0, -191.0), (-311.0, -154.0), (-268.0, -212.0)]
# the course act of MEAL SWIPE TOKENS (course.lua act names; wf_reitz_missions.lua REITZ_MISSION_ACTS.tokens =
# design 7.2 act 5). Every coin (or formation) within 1.6 m of one of its token spots (stage_points.
# reitz_token_spots: the sculpture girder, the Liberty Pond fountain float, the Bookstore awning, Weil's ridge,
# Malachowsky's 12 m glass box) is left out of that act (OBJECT_WITH_ACTS, _skip_token_act at the end of
# reitz_pickups), so the mission's red-coin token is not drawn inside a yellow coin; in every other act they
# mark the spots as before. tools/luatest/test_reitz_missions.lua checks that no coin of the token act sits on
# a token.
REITZ_TOKEN_ACT = 2
REITZ_NOT_TOKEN_ACTS = [a for a in range(1, 7) if a != REITZ_TOKEN_ACT]


def reitz_pickups(S, probe):
    """-> (items, skipped) for Course 2 (docs/game_design.md 7.2), from the landmark modules' routes:
      * coins (~250, the 100-coin star needs 100): one over every step of the act 1 Reitz climb (ravine
        terraces -> awnings -> ballroom roof -> podium -> tower ledges -> tower roof) and of its south
        route (terrace -> canopy -> light shelves -> green roof), every glass box of Malachowsky's
        stepped band, Weil Hall's roof run (addition roof, roof stair, ridge, gutters, dormers); rings
        and lines on the North Lawn (a line leads from the spawn onto the lawn), the Engineering Plaza,
        the atrium, the cooling-tower and bookstore roofs and Gator Corner; singles on the Liberty Pond
        fountain, the amphitheater, the food court and the ravine boardwalk; coin lines on open grade along
        the act 2 hunt's long legs; rings on the Reitz colonnade and Malachowsky's rooftop terrace (the
        coins on token spots skip the token act, REITZ_TOKEN_ACT);
      * hearts on the Reitz podium roof and South Terrace, Weil's roof stair foot, Malachowsky's
        recess terrace; 1-ups on Malachowsky's penthouse (37.7 m, the highest point), Weil's tower deck
        and the Reitz stair penthouse;
      * Goombas on the North Lawn, the Reitz podium roof (a hazard on the act 1 climb), both plazas
        and in the ravine woods; Bob-ombs on the Reitz ballroom and tower roofs (act 1 hazards);
      * ride gators (Koopa shells) for the flat campus: by the spawn, on the Engineering Plaza, on Reitz Union Drive;
      * poles: the Reitz window-washer cable (podium -> tower roof) and colonnade lamp post, Weil Hall's
        seven copper downspouts (the only way onto its roofs from the ground)."""
    P = Placer(S, probe)
    ru = _extras(S, "reitz_union")
    rs = ru.get("spots", {})
    amph = _extras(S, "reitz_amphitheater").get("spots", {})
    weil = _extras(S, "weil_hall")
    ws = weil.get("spots", {})
    plaza = _extras(S, "engineering_plaza").get("spots", {})
    mal = _extras(S, "malachowsky_hall")
    ms = mal.get("spots", {})
    dres = getattr(S, "reitz_dressing", None) or {}

    def spot(d, k):
        return d.get(k)

    # ---- act 1: the Reitz climb (ravine side) and its south route
    climb = ru.get("climb_route_m", [])
    for i, p in enumerate(climb[:-1]):
        P.coin(f"reitz climb coin {i:02d}", p)
    south = ru.get("markers", {}).get("climb_route_south_m", [])
    for i, p in enumerate(south[1:], 1):
        P.coin(f"reitz south route coin {i:02d}", p)
    if spot(rs, "podium_roof_west"):
        P.heart("heart Reitz podium roof", rs["podium_roof_west"])
    if spot(amph, "south_terrace_center"):
        P.heart("heart Reitz South Terrace", amph["south_terrace_center"])
    if spot(rs, "stair_penthouse_top"):
        P.one_up("1-up Reitz stair penthouse", rs["stair_penthouse_top"])
    if spot(rs, "podium_roof_south"):
        P.goomba("goomba Reitz podium roof", rs["podium_roof_south"], 0.0, room=1.5)
    # food court (enterable Level 1) + South Terrace + amphitheater + the Liberty Pond fountain
    if spot(rs, "food_court_center"):
        P.coin_line("food court coins", rs["food_court_center"], 90.0)
    for k in ("south_terrace_west", "south_terrace_east", "amphitheater_top_row"):
        if spot(amph, k):
            P.coin(f"amphitheater coin {k}", amph[k])
    if spot(amph, "liberty_pond_fountain"):
        P.coin("Liberty Pond fountain coin", amph["liberty_pond_fountain"])

    # ---- Malachowsky Hall: the stepped glass band (planter -> canopy -> 11 boxes -> roof -> lantern)
    mclimb = mal.get("climb_route_m", [])
    for i, p in enumerate(mclimb[1:-1], 1):
        P.coin(f"malachowsky climb coin {i:02d}", p)
    if len(mclimb) > 2:
        P.one_up("1-up Malachowsky penthouse (37.7 m)", mclimb[-1])
    if spot(ms, "recess_terrace"):
        P.heart("heart Malachowsky recess terrace", ms["recess_terrace"])
    if spot(ms, "atrium_floor"):
        P.coin_ring("malachowsky atrium coins", ms["atrium_floor"])
    if spot(ms, "plaza_center"):
        c = ms["plaza_center"]
        P.coin_line("malachowsky plaza coins", (c[0], c[1] + 9.0, 0.0), 90.0)
        P.goomba("goomba Malachowsky plaza", (c[0] + 14.0, c[1] + 16.0, 0.0), 180.0)

    # ---- Weil Hall: the roof run (courtyard downspout -> addition roof -> roof stair -> ridge -> tower)
    wclimb = weil.get("climb_route_m", [])
    for i, p in enumerate(wclimb[2:-1], 2):
        P.coin(f"weil roof run coin {i:02d}", p)
    for k in ("ridge_mid", "ridge_west_gable", "ridge_wn_north", "ridge_pw_north", "balcony", "polygonal_bay_top",
              "north_gutter_bay_1", "north_gutter_bay_2", "north_gutter_bay_3", "north_gutter_bay_4",
              "dormer_roof_1", "dormer_roof_2", "dormer_roof_3", "dormer_roof_4", "auditorium_roof", "hvac_top"):
        if spot(ws, k):
            P.coin(f"weil coin {k}", ws[k])
    if spot(ws, "roof_stair_foot"):
        P.heart("heart Weil roof stair foot", ws["roof_stair_foot"])
    if spot(ws, "tower_deck"):
        P.one_up("1-up Weil tower deck", ws["tower_deck"])
    # Engineering Plaza (clock tower): ring, the steel sculpture's girder, the solar kiosk, a Goomba
    if spot(plaza, "plaza_center"):
        P.coin_ring("engineering plaza coins", plaza["plaza_center"])
        c = plaza["plaza_center"]
        P.goomba("goomba Engineering Plaza", (c[0] + 6.0, c[1] + 8.0, 0.0), 90.0)
    for k in ("sculpture_top", "solar_kiosk_top"):
        if spot(plaza, k):
            P.coin(f"engineering plaza coin {k}", plaza[k])

    # ---- North Lawn: a line from the spawn onto the lawn, rings on the radial hubs, lines between them
    sp = getattr(S, "spawn", None)
    if sp:
        f = math.radians(sp["facing"])
        c = (sp["pos"][0] + math.sin(f) * 14.0, sp["pos"][1] + math.cos(f) * 14.0, 0.0)
        P.coin_line("north lawn coins from the spawn", c, sp["facing"])
    hubs = [(x, y, 0.0) for x, y in REITZ_LAWN_HUBS]
    for k, h in enumerate(hubs):
        P.coin_ring(f"north lawn coins hub {k}", h)
    for k, (a, b) in enumerate(((hubs[0], hubs[1]), (hubs[1], hubs[2]), (hubs[0], hubs[2]))):
        mid = lerp(a, b, 0.5)
        f = bearing(a, b)
        side = (mid[0] + math.sin(math.radians(f + 90.0)) * 4.0, mid[1] + math.cos(math.radians(f + 90.0)) * 4.0, 0.0)
        P.coin_line(f"north lawn coins walk {k}", side, f)
    for k, (a, b, t) in enumerate(((hubs[0], hubs[1], 0.3), (hubs[1], hubs[2], 0.65), (hubs[0], hubs[2], 0.75))):
        g = lerp(a, b, t)
        P.goomba(f"goomba North Lawn {k}", (g[0] + 6.0, g[1] - 5.0, 0.0), bearing(b, a))

    # ---- generic buildings' climb routes (cooling-tower catwalk, bookstore roof) + Gator Corner patio
    for b in S.stats.get("buildings", []):
        cr = b.get("climb_route")
        if not cr or b.get("id") not in ("w150858524", "w150821701"):
            continue
        cx_, cy_ = cr["canopy_m"][:2]
        P.coin(f"{b['name']} canopy coin", (cx_, cy_, cr["canopy_m"][2]))
        bb = next((x for x in S.data["buildings"] if x["id"] == b["id"]), None)
        if bb is not None:
            c = bb["c"]
            P.coin_ring(f"{b['name']} roof coins", (c[0], c[1], cr["roof_m"]))
    tables = dres.get("tables", [])
    if tables:
        t0 = tables[0]
        P.coin_ring("gator corner patio coins", (t0[0] + 7.0, t0[1] - 6.0, 0.0))
    # ravine boardwalk: a coin every ~8 m on the deck; Goombas in the woods beside it
    for r, run in enumerate(dres.get("boardwalk", [])):
        a, b = run["from_m"], run["to_m"]
        n = max(1, int(run["length_m"] // 8.0))
        for k in range(n):
            t = (k + 0.5) / n
            P.coin(f"ravine boardwalk coin {r}.{k}", (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
                                                       run["deck_m"]), quiet=True)
    P.goomba("goomba ravine woods 0", (-575.0, -345.0, 0.0), 45.0, room=1.0)
    P.goomba("goomba ravine woods 1", (-610.0, -395.0, 0.0), 0.0, room=1.0)

    # ---- act 1 hazards on the climb (design 7.2 "Goombas / Bob-ombs"): a Bob-omb on the ballroom roof and one
    # on the tower roof (inside its parapet), besides the podium roof's Goomba
    if spot(rs, "ballroom_roof_center"):
        P.bobomb("bobomb Reitz ballroom roof", rs["ballroom_roof_center"], 90.0)
    if spot(rs, "tower_roof_center"):
        P.bobomb("bobomb Reitz tower roof", rs["tower_roof_center"], 270.0)

    # ---- ride gators (Koopa shells) for the flat campus (the act 2 hunt is ~1 km of ground): by the spawn on the North
    # Lawn, on the Engineering Plaza, and on the Reitz Union Drive loop (ravine side)
    if sp:
        f = math.radians(sp["facing"] - 90.0)
        P.shell("shell North Lawn (spawn)", (sp["pos"][0] + math.sin(f) * 6.0, sp["pos"][1] + math.cos(f) * 6.0, 0.0))
    if spot(plaza, "plaza_center"):
        c = plaza["plaza_center"]
        P.shell("shell Engineering Plaza", (c[0] - 7.0, c[1] - 6.0, 0.0))
    P.shell("shell Reitz Union Drive loop", (-536.0, -312.0, 0.0))

    # ---- breadcrumbs on the act 2 hunt's long legs (the shortest tour, spawn -> fountain -> bookstore ->
    # Malachowsky -> boardwalk -> cooling towers -> Weil -> sculpture -> Gator Corner): a coin line every
    # ~40 m on open grade along each leg over 90 m (inside a building, on water or a roof: skipped quietly)
    SPt = _module("stage_points")
    tokens = SPt.reitz_token_spots(S) if SPt is not None else []
    by = {name: pt for name, pt, _ in tokens}
    tour = [("spawn", (sp["pos"][0], sp["pos"][1], 0.0) if sp else None)] + [(n, by.get(n)) for n in (
        "token_liberty_pond_fountain", "token_bookstore_awning", "token_malachowsky_glass_stair",
        "token_ravine_boardwalk", "token_cooling_tower_catwalk", "token_weil_roof_ridge",
        "token_engineering_plaza_sculpture", "token_gator_corner_patio")]
    tour = [(n, p) for n, p in tour if p is not None]
    for (na, a_), (nb, b_) in zip(tour, tour[1:]):
        L = math.dist(a_[:2], b_[:2])
        if L < 90.0:
            continue
        f = bearing(a_, b_)
        n = int(L // 40.0)
        for k in range(1, n + 1):
            t = k / (n + 1)
            x, y = a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t
            if P.open_ground(x, y):
                P.coin_line(f"hunt coins {na[6:] if na.startswith('token_') else na} -> {nb[6:]} {k}", (x, y, 0.0), f,
                            quiet=True)

    # ---- secret roof tops without a reward so far: the Reitz north colonnade, Malachowsky's rooftop terrace
    if spot(rs, "north_colonnade_top"):
        P.coin_ring("secret coins Reitz north colonnade", rs["north_colonnade_top"], fallback_facings=(90.0, 0.0))
    if spot(ms, "rooftop_terrace"):
        P.coin_ring("secret coins Malachowsky rooftop terrace", ms["rooftop_terrace"])

    # ---- poles: the Reitz Union's (window-washer cable, colonnade lamp) and Weil Hall's downspouts
    for q in ru.get("markers", {}).get("poles", []) + weil.get("markers", {}).get("poles", []):
        P.pole(f"pole {q['name']}", q["base_m"], q["height_m"])

    # ---- the token act: no coin may be drawn inside a meal-swipe token (any coin within 1.6 m of a token spot,
    # from 1 m below to 3 m above it, exists in every act except REITZ_TOKEN_ACT)
    _skip_token_act(P.items, [pt for _, pt, _ in tokens])
    return P.items, P.skipped


def _coin_points(it):
    """Map positions of the coins an item puts in the level (formations: where each coin lands)."""
    x, y, z = it["map_m"]
    if it["kind"] == "coin":
        return [(x, y, z)]
    if it["kind"] == "coin_line":
        f = math.radians(it["facing_deg"])
        return [(x + math.sin(f) * LINE_STEP_M * (i - 2), y + math.cos(f) * LINE_STEP_M * (i - 2), z) for i in range(5)]
    if it["kind"] == "coin_ring":
        return [(x + RING_R_M * math.sin(k * math.pi / 4), y + RING_R_M * math.cos(k * math.pi / 4), z) for k in range(8)]
    return []


def _skip_token_act(items, spots, r=1.6, below=1.0, above=3.0):
    """Coins (and whole formations) on a token spot: OBJECT_WITH_ACTS for every act but REITZ_TOKEN_ACT."""
    for it in items:
        for (cx, cy, cz) in _coin_points(it):
            if any(math.dist((cx, cy), t[:2]) <= r and t[2] - below <= cz <= t[2] + above for t in spots):
                it["acts"] = list(REITZ_NOT_TOKEN_ACTS)
                it["token_act_skipped"] = True
                break
