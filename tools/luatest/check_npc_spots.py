"""Check the mascots' spots and posts in mods/sgl64/sgl_npc.lua (SGL_NPC_SPOTS, SGL_NPC_POSTS).

Every spot must stand on the built level's floor at its y, with flat floor and no static geometry from the floor
up to 2.6 m within its stroll radius (+ a margin), and no level-script object (coins, signs, trees, Goombas) within
the radius + 1.2 m. Posts: both mascots stand on the hub, and every stage has exactly one mascot for each of its
acts 1-6 (at the mission's start).
Usage (from anywhere): python3 -I tools/luatest/check_npc_spots.py   (exit 1 on a problem)
"""
import math
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "sgl_npc.lua")
LEVELS = os.path.join(ROOT, "mods", "sgl64", "levels")
SLOTS = {"SGL_HUB_LEVEL": "castle_grounds", "LEVEL_BOB": "bob", "LEVEL_WF": "wf", "LEVEL_JRB": "jrb",
         "LEVEL_CCM": "ccm", "LEVEL_BBH": "bbh"}
MARGIN = 60          # clear ground beyond the stroll radius (Albert is ~0.5 m wide)
OBJ_GAP = 120        # level-script objects stay this far beyond the stroll radius
MIN_CLEAR = 70       # a standing-only spot (radius 0) still needs this much room (boardwalks, decks, libraries)


class Collision:
    """Static collision of an exported area (COL_VERTEX / COL_TRI), SM64 floor rules."""

    def __init__(self, path):
        src = open(path).read()
        verts = [tuple(int(v) for v in m) for m in re.findall(r"COL_VERTEX\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)", src)]
        self.tris = []
        for m in re.finditer(r"COL_TRI(?:_SPECIAL)?\(\s*(\d+),\s*(\d+),\s*(\d+)", src):
            a, b, c = (verts[int(m.group(i))] for i in (1, 2, 3))
            (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = a, b, c
            nx = (y2 - y1) * (z3 - z2) - (z2 - z1) * (y3 - y2)
            ny = (z2 - z1) * (x3 - x2) - (x2 - x1) * (z3 - z2)
            nz = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
            mag = math.sqrt(nx * nx + ny * ny + nz * nz)
            if mag == 0:
                continue
            nx, ny, nz = nx / mag, ny / mag, nz / mag
            self.tris.append((a, b, c, nx, ny, nz, -(nx * x1 + ny * y1 + nz * z1)))
        self.floors = [t for t in self.tris if t[4] > 0.01]

    def find_floor(self, x, y, z):
        best = None
        for (a, b, c, nx, ny, nz, oo) in self.floors:
            (x1, _, z1), (x2, _, z2), (x3, _, z3) = a, b, c
            if (z1 - z) * (x2 - x1) - (x1 - x) * (z2 - z1) < 0:
                continue
            if (z2 - z) * (x3 - x2) - (x2 - x) * (z3 - z2) < 0:
                continue
            if (z3 - z) * (x1 - x3) - (x3 - x) * (z1 - z3) < 0:
                continue
            h = -(x * nx + nz * z + oo) / ny
            if y - (h - 78.0) >= 0 and (best is None or h > best):
                best = h
        return best

    def solid_in_box(self, x0, x1, y0, y1, z0, z1):
        n = 0
        for t in self.tris:
            xs, ys, zs = [v[0] for v in t[:3]], [v[1] for v in t[:3]], [v[2] for v in t[:3]]
            if max(xs) <= x0 or min(xs) >= x1 or max(ys) <= y0 or min(ys) >= y1 or max(zs) <= z0 or min(zs) >= z1:
                continue
            n += 1
        return n


def lua_spots():
    text = open(LUA).read()
    generated = open(os.path.join(ROOT, "mods", "sgl64", "sgl_ambient_data.lua")).read()
    body = generated[generated.index("SGL_NPC_SPOTS = {"): ]
    body = body[:body.index("\n}\n")]
    spots = {}
    for m in re.finditer(r"(\w+) = \{ level = (\w+), area = (\d+), x = (-?\d+), y = (-?\d+), z = (-?\d+), "
                         r"yaw = (-?\d+), radius = (\d+),\s*label = \"([^\"]+)\" \}", body):
        spots[m.group(1)] = {"level": m.group(2), "area": int(m.group(3)), "x": int(m.group(4)), "y": int(m.group(5)),
                             "z": int(m.group(6)), "radius": int(m.group(8)), "label": m.group(9)}
    posts = text[text.index("SGL_NPC_POSTS = {"):]
    posts = posts[:posts.index("\n}\n")]
    plist = []
    for m in re.finditer(r'\{ npc = "(\w+)", spot = "(\w+)"(?:, acts = \{([^}]*)\})? \}', posts):
        acts = [int(a) for a in re.findall(r"\d+", m.group(3))] if m.group(3) else None
        plist.append((m.group(1), m.group(2), acts))
    return spots, plist


def script_objects(slot, area):
    s = open(os.path.join(LEVELS, slot, "script.c")).read()
    a0 = s.index("AREA(%d," % area)
    a1 = s.index("END_AREA()", a0)
    return [(int(m.group(1)), int(m.group(3)))
            for m in re.finditer(r"OBJECT(?:_WITH_ACTS)?\(\s*\w+,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),", s[a0:a1])]


def main():
    spots, posts = lua_spots()
    bad = []
    if len(spots) < 18:
        bad.append("expected at least 18 spots in SGL_NPC_SPOTS, parsed %d" % len(spots))
    cols = {}
    for name, sp in sorted(spots.items()):
        slot = SLOTS.get(sp["level"])
        if slot is None:
            bad.append("%s: unknown level %s" % (name, sp["level"]))
            continue
        path = os.path.join(LEVELS, slot, "area_%d" % sp["area"], "collision.inc.c")
        if not os.path.exists(path):
            bad.append("%s: required level %s is not built" % (name, slot))
            continue
        col = cols.setdefault(path, Collision(path))
        x, y, z, r = sp["x"], sp["y"], sp["z"], sp["radius"]
        h = col.find_floor(x, y + 150, z)
        if h is None or abs(h - y) > 4:
            bad.append("%s: no floor at y %d (found %s)" % (name, y, h))
            continue
        reach = max(r + MARGIN, MIN_CLEAR)
        for dx in range(-reach, reach + 1, 40):
            for dz in range(-reach, reach + 1, 40):
                if dx * dx + dz * dz > reach * reach:
                    continue
                hh = col.find_floor(x + dx, y + 150, z + dz)
                if hh is None or abs(hh - y) > 4:
                    bad.append("%s: uneven floor at (%d, %d): %s" % (name, x + dx, z + dz, hh))
                    break
            else:
                continue
            break
        n = col.solid_in_box(x - reach, x + reach, y + 15, y + 260, z - reach, z + reach)
        if n:
            bad.append("%s: %d static triangle(s) within its stroll area" % (name, n))
        near = [math.hypot(ox - x, oz - z) for ox, oz in script_objects(slot, sp["area"])]
        if near and min(near) < r + OBJ_GAP:
            bad.append("%s: a level object only %d units away (radius %d)" % (name, min(near), r))
    # posts: both on the hub; one mascot per act 1-6 in every stage that has posts
    hub = {npc for npc, sp, acts in posts if spots.get(sp, {}).get("level") == "SGL_HUB_LEVEL" and acts is None}
    if hub != {"albert", "alberta"}:
        bad.append("both mascots must stand on the hub (got %s)" % sorted(hub))
    stages = {}
    for npc, sp, acts in posts:
        spot = spots.get(sp)
        if spot is None:
            bad.append("post %s/%s: unknown spot" % (npc, sp))
            continue
        if spot["level"] == "SGL_HUB_LEVEL":
            continue
        if not acts:
            bad.append("post %s/%s: a stage post needs its acts" % (npc, sp))
            continue
        for a in acts:
            stages.setdefault(spot["level"], {}).setdefault(a, []).append(npc)
    for level in ("LEVEL_BOB", "LEVEL_WF", "LEVEL_JRB", "LEVEL_CCM", "LEVEL_BBH"):
        for act in range(1, 7):
            who = stages.get(level, {}).get(act, [])
            if len(who) != 1:
                bad.append("%s act %d: %d mascot posts (want exactly 1)" % (level, act, len(who)))
    for b in bad:
        print("check_npc_spots: " + b)
    if bad:
        return 1
    print("check_npc_spots: OK (%d spots on flat, clear ground; both mascots on the hub and one at every act's "
          "mission in all 5 stages)" % len(spots))
    return 0


if __name__ == "__main__":
    sys.exit(main())
