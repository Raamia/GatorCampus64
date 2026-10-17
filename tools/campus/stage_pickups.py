"""Pickups, enemies and poles a stage build places in its level script (inside Blender, called by
build_stage.py once the meshes exist, with the CollisionProbe of the real collision).

The Swamp (swamp_pickups), from the fix round's fun review:
  * coins: enough for the vanilla 100-coin star (id 6) with room to spare (~140), laid out as route
    breadcrumbs: one coin over every ledge and camera deck of the act 1 climb (in SM64 every coin also
    heals one health wedge), lines on the act 2 stair sprint's long flat rim run, the concourse
    (cross-aisle) toward the West Skybox Tower, the field (midfield ring, apron lines), the Courtyard
    of Champions in front of the spawn, and rings on the secret roof tops (board tops, gatehouse);
  * recovery hearts at the foot of the climb (west rim), on the Bull Gator Deck and half way up the
    camera decks; 1-ups on the hardest secret spots;
  * Goombas ("rowdy fans") on the concourse, in the Courtyard and two on the sprint's rim run (a hazard
    on the flat part of the race);
  * the stadium module's poles (markers["poles"]): goalposts, the 22.5 m pole from the Bull Gator Deck
    to the press box roof (an alternative to the 10 camera-deck hops), the south board leg and the
    hanging east light-mast poles.
Every position is checked against the collision: a coin (or every coin of a formation) must have its
floor within TOL_M of the design height, a Goomba needs room around it. Failing items are skipped with
a "SGL WARNING" (and listed in the report).

Engine notes (SM64 / coopdx v1.5.1):
  bhvCoinFormation (MODEL_NONE) bparam2 = shape: 0 = line of 5 along the object's facing (1.6 m apart),
  2 = horizontal ring of 8 (r 3 m); each coin drops onto the floor below (searched from 3 m above the
  object). bhvYellowCoin (MODEL_YELLOW_COIN) floats where it is placed. MODEL_HEART and MODEL_GOOMBA are
  common0 models: the level script needs JUMP_LINK(script_func_global_1) (build_stage.py
  STAGE_COMMON0_MODELS adds it). bhvPoleGrabbing: bparam2 = pole height in 10 cm.
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
    def __init__(self, S, probe):
        self.S, self.probe = S, probe
        self.items = []
        self.skipped = []

    def _floor(self, x, y, z_from):
        return self.probe.floor(x - self.S.cx, y - self.S.cy, z_from)

    def _skip(self, name, why):
        self.skipped.append({"name": name, "why": why})
        print(f"SGL WARNING: pickup {name}: {why}; skipped")

    def _add(self, kind, name, x, y, z, behavior, model, bparams="0x00000000", facing=0.0, coins=0, acts=None):
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

    def coin(self, name, p, up=COIN_UP_M, quiet=False):
        fz = self.floor_at(name, p) if not quiet else self._floor(p[0], p[1], (p[2] if len(p) > 2 else 0.0) + 1.5)
        if fz is not None:
            self._add("coin", name, p[0], p[1], fz + up, "bhvYellowCoin", "MODEL_YELLOW_COIN", coins=1)
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
