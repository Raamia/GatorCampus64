"""Check that the NPCs of mods/sgl64/sgl_npc.lua (SGL_NPCS ids and names) match tools/npc_bridge/npcs.json.

The bridge skips a request for an NPC id it has no persona for, so a mismatch means an NPC that never
answers. Usage (from anywhere): python3 -I tools/luatest/check_npc_ids.py   (exit 1 on a mismatch)
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LUA = os.path.join(ROOT, "mods", "sgl64", "sgl_npc.lua")
CAST = os.path.join(ROOT, "tools", "npc_bridge", "npcs.json")


def lua_npcs():
    text = open(LUA).read()
    body = text[text.index("SGL_NPCS = {"):]
    body = body[:body.index("\n}\n")]
    return {m.group(1): m.group(2) for m in re.finditer(r'id = "([^"]+)", name = "([^"]+)"', body)}


def main():
    lua = lua_npcs()
    cast = json.load(open(CAST))["npcs"]
    bad = 0
    for npc_id, name in lua.items():
        if npc_id not in cast:
            print("NPC %r (%s) in sgl_npc.lua has no persona in npcs.json" % (npc_id, name))
            bad += 1
        elif cast[npc_id]["name"] != name:
            print("NPC %r is %r in sgl_npc.lua but %r in npcs.json" % (npc_id, name, cast[npc_id]["name"]))
            bad += 1
    for npc_id in cast:
        if npc_id not in lua:
            print("persona %r in npcs.json has no NPC in sgl_npc.lua" % npc_id)
            bad += 1
    if not lua:
        print("no NPCs found in sgl_npc.lua")
        bad += 1
    if bad:
        return 1
    print("check_npc_ids: OK (%d NPCs: %s)" % (len(lua), ", ".join(sorted(lua))))
    return 0


sys.exit(main())
