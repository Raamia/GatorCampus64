"""Rewrite Fast64 material geometry modes as differences from the SM64 engine state (pure Python).

Why: Fast64 writes each material's geometry mode relative to the scene world's rdp_defaults. The headless
outdoor builds (build_stage.py: hub, Swamp, Reitz, Lake Alice) never had a world, so every material was
exported in "full" form: gsSPSetGeometryMode(G_CULL_BACK | G_FOG | G_LIGHTING | G_SHADE | G_SHADING_SMOOTH |
G_ZBUFFER), and its revert cleared all of those, G_ZBUFFER included. The geo renderer turns G_ZBUFFER on once
per master list and object display lists rely on it (and on lighting / shading / back-face culling being on),
so every object drawn after the level's last revert (Mario, NPCs, Goombas, signs) skipped the depth test and
showed through trees and walls. Marston and Library West (build_interior.py pins the world) export the diff
form and never had the bug.

The engine state between display lists is ENGINE_DEFAULT (G_ZBUFFER | G_SHADE | G_SHADING_SMOOTH |
G_CULL_BACK | G_LIGHTING). For each mat_<x> whose geometry-mode commands are in full form (they set G_ZBUFFER),
the mode the material wants, F, is simulated from an empty state; then
  mat_<x>:        gsSPSetGeometryMode(F - D), gsSPClearGeometryMode(D - F)
  mat_revert_<x>: gsSPClearGeometryMode(F - D), gsSPSetGeometryMode(D - F)
(empty commands are dropped), which is what Fast64 writes with SM64 world defaults. Display lists already in
diff form are left alone, so running it twice changes nothing.

Usage: python3 fix_geometry_modes.py <level_dir> [<level_dir> ...]   (edits <level_dir>/model.inc.c in place)
"""
import os
import re
import sys

ENGINE_DEFAULT = {"G_ZBUFFER", "G_SHADE", "G_SHADING_SMOOTH", "G_CULL_BACK", "G_LIGHTING"}
# the order Fast64 writes the flags in
FLAG_ORDER = ["G_ZBUFFER", "G_SHADE", "G_CULL_FRONT", "G_CULL_BACK", "G_CULL_BOTH", "G_FOG", "G_LIGHTING",
              "G_TEXTURE_GEN", "G_TEXTURE_GEN_LINEAR", "G_LOD", "G_SHADING_SMOOTH", "G_CLIPPING"]

DL_RE = re.compile(r"^Gfx (mat_(?:revert_)?\w+)\[\] = \{\n(.*?)^\};\n", re.S | re.M)
GM_RE = re.compile(r"^\tgs(SP(?:Set|Clear)GeometryMode)\(([^)]*)\),\n", re.M)


def _flags(text):
    return {f.strip() for f in text.split("|") if f.strip() and f.strip() != "0"}


def _fmt(flags):
    known = [f for f in FLAG_ORDER if f in flags]
    other = sorted(f for f in flags if f not in FLAG_ORDER)
    return " | ".join(sorted(known, key=lambda f: FLAG_ORDER.index(f)) + other)


def _commands(pairs):
    return "".join(f"\tgs{cmd}({_fmt(fl)}),\n" for cmd, fl in pairs if fl)


def fix_source(src):
    """-> (new source, number of material/revert pairs rewritten)."""
    dls = {m.group(1): m for m in DL_RE.finditer(src)}
    edits = {}   # name -> new body
    n = 0
    for name, m in dls.items():
        if name.startswith("mat_revert_"):
            continue
        body = m.group(2)
        cmds = [(g.group(1), _flags(g.group(2))) for g in GM_RE.finditer(body)]
        if not any(cmd == "SPSetGeometryMode" and "G_ZBUFFER" in fl for cmd, fl in cmds):
            continue   # already diff form (or no geometry mode at all)
        want = set()
        for cmd, fl in cmds:
            want = (want | fl) if cmd == "SPSetGeometryMode" else (want - fl)
        on, off = want - ENGINE_DEFAULT, ENGINE_DEFAULT - want
        first = True

        def mat_sub(g):
            nonlocal first
            if not first:
                return ""
            first = False
            return _commands([("SPSetGeometryMode", on), ("SPClearGeometryMode", off)])
        edits[name] = GM_RE.sub(mat_sub, body)
        rev = "mat_revert_" + name[len("mat_"):]
        if rev in dls:
            rbody = dls[rev].group(2)
            rfirst = [True]

            def rev_sub(g):
                if not rfirst[0]:
                    return ""
                rfirst[0] = False
                return _commands([("SPClearGeometryMode", on), ("SPSetGeometryMode", off)])
            new_rbody = GM_RE.sub(rev_sub, rbody)
            if rfirst[0]:   # the revert had no geometry-mode command: put the restore first
                new_rbody = _commands([("SPClearGeometryMode", on), ("SPSetGeometryMode", off)]) + rbody
            edits[rev] = new_rbody
        n += 1
    if not edits:
        return src, 0
    out, pos = [], 0
    for m in DL_RE.finditer(src):
        name = m.group(1)
        if name in edits:
            out.append(src[pos:m.start(2)])
            out.append(edits[name])
            pos = m.end(2)
    out.append(src[pos:])
    return "".join(out), n


def fix_level(level_dir):
    path = os.path.join(level_dir, "model.inc.c")
    src = open(path).read()
    new, n = fix_source(src)
    if n:
        open(path, "w").write(new)
    return n


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        print(f"{d}: {fix_level(d)} material(s) rewritten to diff form")
