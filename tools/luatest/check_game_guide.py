"""Check that tools/npc_bridge/game_guide.md still matches the game (mods/sgl64/course.lua SGL_STAGES).

The NPCs answer game questions from the guide without asking an AI, so a stale guide gives wrong answers.
For every stage: its door entry (<key>-door, Century Tower: century-tower) names the door's building and its star
requirement ("N stars", or "open from the start" / "no star requirement" for 0). The "stages" overview lists
it with the same count, and every playable act (not COMING SOON) is covered by some entry. Also: the guide
parses and its placeholders are known.
Usage (from anywhere): python3 -I tools/luatest/check_game_guide.py   (exit 1 on a mismatch)
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
COURSE = os.path.join(ROOT, "mods", "sgl64", "course.lua")
sys.path.insert(0, os.path.join(ROOT, "tools", "npc_bridge"))
import guide  # noqa: E402

DOOR_ENTRY = {"swamp": "swamp-door", "reitz": "reitz-door", "alice": "alice-door", "marston": "marston-door",
              "libwest": "libwest-door", "tower": "century-tower"}


def stages():
    text = open(COURSE).read()
    body = text[text.index("SGL_STAGES = {"):]
    body = body[:body.index("\n}\n")]
    out = []
    for block in re.split(r"\n    \{ door = ", body)[1:]:
        st = {
            "key": re.search(r'key = "([^"]+)"', block).group(1),
            "stars": int(re.search(r"stars = (\d+)", block).group(1)),
            "name": re.search(r'name = "([^"]+)"', block).group(1),
            "building": re.search(r'building = "([^"]+)"', block).group(1),
            "acts": re.findall(r'^\s+"([^"]+)",', block, re.M),
        }
        out.append(st)
    return out


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9& ]", " ", s.lower())).strip()


def main():
    g = guide.Guide()
    bad = []
    bad += ["unknown placeholder %s in %s" % (name, eid) for eid, name in guide.check_placeholders(g.entries)]
    by_id = {e.id: e for e in g.entries}
    every = norm(" ".join(" ".join([e.title, " ".join(e.asks), e.answer]) for e in g.entries))
    overview = by_id.get("stages")
    sts = stages()
    for st in sts:
        eid = DOOR_ENTRY.get(st["key"])
        e = by_id.get(eid)
        if e is None:
            bad.append("no guide entry %r for %s" % (eid, st["name"]))
            continue
        text = norm(" ".join([e.title, " ".join(e.asks), e.answer]))
        if norm(st["building"]) not in text and norm(st["building"].replace("SCIENCE LIBRARY", "")) not in text:
            bad.append("%s: entry %s does not name the %s door" % (st["name"], eid, st["building"]))
        needs = ("open from the start", "no star requirement") if st["stars"] == 0 else ("%d stars" % st["stars"],)
        if not any(need in e.answer.lower() for need in needs):
            bad.append("%s: entry %s should say %s (course.lua)" % (st["name"], eid, " or ".join(map(repr, needs))))
        if overview is not None:
            ov = norm(overview.answer)
            if norm(st["name"]) not in ov:
                bad.append("%s is missing from the 'stages' overview" % st["name"])
            elif st["stars"] and ("%s %d stars" % (norm(st["building"]), st["stars"])) not in ov:
                bad.append("'stages' overview: %s should open at %d stars (course.lua)" % (st["name"], st["stars"]))
        for act in st["acts"]:
            if act.startswith("COMING SOON"):
                continue
            name = norm(re.sub(r"\s*-\s*2P$", "", act))
            if name not in every:
                bad.append("%s act %r is not in the guide" % (st["name"], act))
    if overview is None:
        bad.append("no 'stages' overview entry")
    for b in bad:
        print("check_game_guide: " + b)
    if bad:
        return 1
    n_acts = sum(1 for st in sts for a in st["acts"] if not a.startswith("COMING SOON"))
    print("check_game_guide: OK (%d entries; %d stages, %d playable acts match course.lua)" % (len(g.entries), len(sts), n_acts))
    return 0


sys.exit(main())
