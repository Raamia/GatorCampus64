"""Validate a Fast64 character export for coopdx (pure Python, no Blender needed).

Usage: python3 validate_export.py <actor_dir> [actor_name]
Checks:
  - geo.inc.c defines <actor>_geo[] and it is the only root GeoLayout (DynOS
    compiles every unreferenced GeoLayout into its own .bin)
  - switch nodes: geo_switch_mario_eyes with 8 cases, cap on/off, hands,
    cap effect (normal/metal/vanish), stand/run LoD
  - player colour / mirror GEO_ASM commands present, no CUSTOM_CMD()
  - no leftover Mario-only materials or textures in model.inc.c
  - every texture of every material (each render tile, e.g. both tiles of the
    two-texture Metal material) matches its load: gsDPSetTileSize and the S/T masks
    equal the size implied by gsDPLoadBlock + the tile line width (a 64x32 eye
    texture must export (252, 124) with masks 6/5, a 32x16 mouth (124, 60) with
    masks 5/4), and the u8 texture array has width*height texels
  - face textures (RGBA5551): skin background alpha 0, no opaque edge texels
  - eye switches: case k draws exactly the k-th eye material (Open, Half Closed,
    Closed, Left, Right, Up, Down, Dead) and every case still draws the Mouth
  - Skin, every eye material and the Mouth share identical Lights1 (a different
    light would tint the keyed texels / seam the face)
Prints a report with triangle counts and exits non-zero on failure.
"""
import os
import re
import sys

# tokens of Mario-only materials/textures (Fast64 lowercases nothing, so match case-insensitively)
LEFTOVERS = ["mustache", "sideburn", "logo", "emblem", "buttons__pants", "overalls_button", "mario_eyes",
             "innn"]


def parse_switches(geo_text):
    """Return list of (func, n_cases, layout_name) for every GEO_SWITCH_CASE."""
    out = []
    layout = None
    lines = [l.strip() for l in geo_text.splitlines()]
    for n, line in enumerate(lines):
        m = re.match(r"const GeoLayout (\w+)\[\]", line)
        if m:
            layout = m.group(1)
        m = re.match(r"GEO_SWITCH_CASE\(\s*(\d+)\s*,\s*(\w+)\s*\)", line)
        if not m:
            continue
        func = m.group(2)
        # children are the commands at depth 1 inside the following OPEN/CLOSE pair
        depth = 0
        cases = 0
        for l2 in lines[n + 1:]:
            if l2.startswith("GEO_OPEN_NODE"):
                depth += 1
                continue
            if l2.startswith("GEO_CLOSE_NODE"):
                depth -= 1
                if depth == 0:
                    break
                continue
            if depth == 0:
                break  # switch without children
            if depth == 1 and l2.startswith("GEO_"):
                cases += 1
        out.append((func, cases, layout))
    return out


def count_tris_per_dl(model_text):
    tris = {}
    cur = None
    for line in model_text.splitlines():
        m = re.match(r"Gfx (\w+)\[\]", line)
        if m:
            cur = m.group(1)
            tris[cur] = 0
            continue
        if cur is None:
            continue
        tris[cur] += line.count("gsSP1Triangle(") + 2 * line.count("gsSP2Triangles(")
    return tris


BYTES_PER_TEXEL = {"G_IM_SIZ_4b": 0.5, "G_IM_SIZ_8b": 1, "G_IM_SIZ_16b": 2, "G_IM_SIZ_32b": 4}
# expected (width, height) of the character face textures, by texture name suffix
FACE_TEXTURE_SIZES = {"eyes_": (64, 32), "mouth_": (32, 16)}


def _args(call):
    return [a.strip() for a in call.split(",")]


def _texture_loads(body):
    """Texture loads of one material DL in command order: one dict per render tile
    {tex, siz, texels, tile (SetTile args), size (SetTileSize args)}; None when a
    texture image is set without the LoadBlock / SetTile / SetTileSize sequence."""
    loads, cur = [], None
    for cmd, args in re.findall(r"(gsDP\w+)\(([^)]*)\)", body):
        a = _args(args)
        if cmd == "gsDPSetTextureImage":
            cur = {"tex": a[-1], "siz": a[1].replace("_LOAD_BLOCK", ""), "texels": None,
                   "load_tile": None, "tile": None, "size": None}
            loads.append(cur)
        elif cur is None:
            continue
        elif cmd == "gsDPLoadBlock":
            cur["load_tile"] = a[0]
            cur["texels"] = int(a[3]) + 1
        elif cmd == "gsDPSetTile" and a[4] != cur["load_tile"] and cur["texels"] is not None:
            cur["tile"] = a
        elif cmd == "gsDPSetTileSize" and cur["tile"] is not None and a[0] == cur["tile"][4]:
            cur["size"] = a
    if any(ld["texels"] is None or ld["tile"] is None or ld["size"] is None for ld in loads):
        return None
    return loads


def check_textures(model_text):
    """Per material DL and per render tile: compare the loaded texture size with
    SetTile/SetTileSize. Returns (errors, rows) where rows describe every texture."""
    errors, rows = [], []
    arrays, data = {}, {}
    for m in re.finditer(r"u8 (\w+)\[\] = \{([^}]*)\}", model_text):
        vals = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", m.group(2))]
        arrays[m.group(1)] = len(vals)
        data[m.group(1)] = vals
    for m in re.finditer(r"Gfx (mat_\w+)\[\] = \{(.*?)\n\};", model_text, re.S):
        name, body = m.group(1), m.group(2)
        if name.startswith("mat_revert_") or "gsDPSetTextureImage" not in body:
            continue
        loads = _texture_loads(body)
        if loads is None:
            errors.append(f"{name}: unrecognised texture load sequence (no LoadBlock/SetTile/SetTileSize)")
            continue
        for ld in loads:
            _check_load(name, ld, arrays, data, errors, rows)
    return errors, rows


def _check_load(name, ld, arrays, data, errors, rows):
    tex, siz, texels = ld["tex"], ld["siz"], ld["texels"]
    bpt = BYTES_PER_TEXEL.get(siz)
    if bpt is None:
        errors.append(f"{name}: unknown texel size {siz} for {tex}")
        return
    if siz == "G_IM_SIZ_4b":
        texels *= 4  # 4b textures are loaded as 16b blocks
    t = ld["tile"]  # fmt, siz, line, tmem, tile, pal, cmt, maskt, shiftt, cms, masks, shifts
    line_words = int(t[2])
    width = int(round(line_words * 8 / bpt))
    height = texels // width if width else 0
    maskt, masks = int(t[7]), int(t[10])
    ts = ld["size"]  # tile, uls, ult, lrs, lrt (10.2 fixed point)
    tw, th = int(ts[3]) // 4 + 1, int(ts[4]) // 4 + 1
    row = {"material": name, "texture": tex, "render_tile": int(t[4]), "loaded": (width, height),
           "tile": (tw, th), "masks": (masks, maskt), "clamp": ("G_TX_CLAMP" in t[6], "G_TX_CLAMP" in t[9])}
    rows.append(row)
    where = f"{name} (tile {t[4]})"
    if width * height != texels:
        errors.append(f"{where}: LoadBlock {texels} texels is not a multiple of the line width {width}")
    if (tw, th) != (width, height):
        errors.append(f"{where}: gsDPSetTileSize is {tw}x{th} but {tex} is loaded as {width}x{height}")
    want_masks = ((width - 1).bit_length(), (height - 1).bit_length())
    if (masks, maskt) != want_masks:
        errors.append(f"{where}: masks S/T {masks}/{maskt}, expected {want_masks[0]}/{want_masks[1]} "
                      f"for {width}x{height}")
    if tex in arrays:
        want_bytes = int(width * height * bpt)
        if arrays[tex] != want_bytes:
            errors.append(f"{where}: {tex}[] has {arrays[tex]} bytes, expected {want_bytes}")
    for key, wh in FACE_TEXTURE_SIZES.items():
        if key in tex and (width, height) != wh:
            errors.append(f"{where}: face texture {tex} is {width}x{height}, expected {wh[0]}x{wh[1]}")
        if key in tex and siz == "G_IM_SIZ_16b" and tex in data and arrays[tex] == width * height * 2:
            # RGBA5551: the skin background must be alpha 0 (an opaque texel renders unlit),
            # and with G_TX_CLAMP the edge texels are repeated outside the texture
            v = data[tex]
            alpha = [v[2 * i + 1] & 1 for i in range(width * height)]
            opaque = sum(alpha)
            edge = [alpha[y * width + x] for y in range(height) for x in range(width)
                    if x in (0, width - 1) or y in (0, height - 1)]
            row["opaque_texels"] = opaque
            if opaque == 0:
                errors.append(f"{where}: {tex} has no opaque texels")
            if opaque > width * height * 0.6:
                errors.append(f"{where}: {tex} is {opaque}/{width * height} opaque (skin background not keyed?)")
            if any(edge):
                errors.append(f"{where}: {tex} has {sum(edge)} opaque edge texels (clamp smears them)")


# eye switch case order (geo_switch_mario_eyes) -> eye material name stem
EYE_CASE_MATERIALS = ["Open_Eyes", "Half_Closed_Eyes", "Closed_Eyes", "Left_Eyes", "Right_Eyes", "Up_Eyes",
                      "Down_Eyes", "Dead_Eyes"]


def _geo_layouts(geo_text):
    """{layout name: [stripped lines]}"""
    out, cur = {}, None
    for line in geo_text.splitlines():
        line = line.strip()
        m = re.match(r"const GeoLayout (\w+)\[\]", line)
        if m:
            cur = out.setdefault(m.group(1), [])
            continue
        if cur is not None:
            cur.append(line)
    return out


def _dls_in(lines, layouts, seen=None):
    """Display lists drawn by these geo lines, following GEO_BRANCH into layouts."""
    seen = set() if seen is None else seen
    dls = []
    for line in lines:
        m = re.match(r"GEO_(?:DISPLAY_LIST|ANIMATED_PART|TRANSLATE_ROTATE_WITH_DL|TRANSLATE_NODE_WITH_DL|"
                     r"ROTATION_NODE_WITH_DL|SCALE_WITH_DL|DISPLAY_LIST_WITH_OFFSET)\((.*)\)", line)
        if m:
            arg = _args(m.group(1))[-1]
            if arg not in ("NULL", "0"):
                dls.append(arg)
            continue
        m = re.match(r"GEO_BRANCH\(\s*\d+\s*,\s*(\w+)\s*\)", line)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            dls += _dls_in(layouts.get(m.group(1), []), layouts, seen)
    return dls


def _eye_switch_cases(geo_text):
    """For every geo_switch_mario_eyes: list of cases, each a list of geo lines."""
    lines = [l.strip() for l in geo_text.splitlines()]
    switches = []
    for n, line in enumerate(lines):
        if not re.match(r"GEO_SWITCH_CASE\(\s*\d+\s*,\s*geo_switch_mario_eyes\s*\)", line):
            continue
        cases, depth, cur = [], 0, None
        for l2 in lines[n + 1:]:
            if l2.startswith("GEO_OPEN_NODE"):
                depth += 1
                if cur is not None and depth > 1:
                    cur.append(l2)
                continue
            if l2.startswith("GEO_CLOSE_NODE"):
                depth -= 1
                if depth == 0:
                    break
                if cur is not None:
                    cur.append(l2)
                continue
            if depth == 1 and l2.startswith("GEO_"):
                cur = [l2]
                cases.append(cur)
            elif cur is not None:
                cur.append(l2)
        switches.append(cases)
    return switches


def check_face_materials(geo_text, model_text, actor):
    """Eye switch case -> eye material order, Mouth in every case, shared face lights."""
    errors, notes = [], []
    layouts = _geo_layouts(geo_text)
    dl_mats = {}
    for m in re.finditer(r"Gfx (\w+)\[\] = \{(.*?)\n\};", model_text, re.S):
        dl_mats[m.group(1)] = [x for x in re.findall(r"gsSPDisplayList\((mat_\w+)\)", m.group(2))
                               if not x.startswith("mat_revert_")]
    mouth = f"mat_{actor}_Mouth__SKIN_"
    has_mouth = mouth in dl_mats
    for sn, cases in enumerate(_eye_switch_cases(geo_text)):
        got = []
        for k, case in enumerate(cases):
            dls = _dls_in(case, layouts)
            mats = [mm for d in dls for mm in dl_mats.get(d, [])]
            eyes = sorted({mm for mm in mats if "_Eyes__" in mm})
            got.append(",".join(e.replace(f"mat_{actor}_", "").replace("__SKIN_", "") for e in eyes) or "-")
            want = f"mat_{actor}_{EYE_CASE_MATERIALS[k]}__SKIN_" if k < len(EYE_CASE_MATERIALS) else None
            if not dls:
                errors.append(f"eye switch {sn} case {k}: draws no display list")
                continue
            if eyes != [want]:
                errors.append(f"eye switch {sn} case {k} ({', '.join(dls)}): eye materials {eyes}, expected [{want}]")
            if has_mouth and mouth not in mats:
                errors.append(f"eye switch {sn} case {k} ({', '.join(dls)}): does not draw {mouth}")
        notes.append(f"eye switch {sn}: {' | '.join(got)}")
    if not has_mouth:
        errors.append(f"{mouth} not found in model.inc.c")
    # shared face lights
    lights = {n: re.sub(r"\s+", "", v) for n, v in
              re.findall(r"Lights1 (\w+) = gdSPDefLights1\(\s*([^;]*)\);", model_text, re.S)}
    face = {}
    for m in re.finditer(r"Gfx (mat_\w+)\[\] = \{(.*?)\n\};", model_text, re.S):
        name = m.group(1)
        if name.startswith("mat_revert_"):
            continue
        if name in (f"mat_{actor}_Skin__SKIN_", mouth) or (name.endswith("_Eyes__SKIN_")):
            lm = re.search(r"gsSPSetLights1\((\w+)\)", m.group(2))
            face[name] = lights.get(lm.group(1)) if lm else None
    vals = set(face.values())
    if len(vals) != 1 or None in vals:
        errors.append(f"skin / eye / mouth materials do not share one Lights1: "
                      f"{ {k.replace(f'mat_{actor}_', ''): v for k, v in face.items()} }")
    else:
        notes.append(f"face lights shared by {len(face)} materials: {vals.pop()}")
    return errors, notes


def validate(actor_dir, actor=None):
    actor = actor or os.path.basename(os.path.normpath(actor_dir))
    geo = open(os.path.join(actor_dir, "geo.inc.c")).read()
    model = open(os.path.join(actor_dir, "model.inc.c")).read()
    errors, notes = [], []

    if not re.search(rf"const GeoLayout {re.escape(actor)}_geo\[\]", geo):
        errors.append(f"{actor}_geo[] not defined in geo.inc.c")
    # DynOS compiles every root (unreferenced) GeoLayout into its own .bin
    layouts = re.findall(r"const GeoLayout (\w+)\[\]", geo)
    roots = [n for n in layouts if len(re.findall(rf"\b{n}\b", geo)) == 1]
    if roots != [f"{actor}_geo"]:
        errors.append(f"root GeoLayouts must be exactly [{actor}_geo], found {roots}")
    notes.append(f"geo layouts: {len(layouts)}, root: {roots}")
    if "CUSTOM_CMD(" in geo:
        errors.append("CUSTOM_CMD() present in geo.inc.c (Fast64 custom command migration failed)")
    for needle in ("geo_mario_set_player_colors", "geo_mirror_mario_backface_culling", "geo_mirror_mario_set_alpha",
                   "geo_mario_head_rotation", "geo_mario_tilt_torso", "geo_mario_hand_foot_scaler",
                   "geo_switch_mario_hand_grab_pos", "geo_mario_rotate_wing_cap_wings"):
        if needle not in geo:
            errors.append(f"missing {needle} in geo.inc.c")

    sw = parse_switches(geo)
    by = {}
    for func, n, layout in sw:
        by.setdefault(func, []).append((n, layout))
    # (minimum cases on every switch, cases required on the largest one)
    expect = {
        "geo_switch_mario_eyes": (8, 8),         # open, half, closed, left, right, up, down, dead
        "geo_switch_mario_cap_on_off": (2, 2),   # cap on / capless head
        "geo_switch_mario_cap_effect": (2, 4),   # normal, vanish, metal, metal+vanish
        "geo_switch_mario_hand": (2, 5),         # fists / open / peace / cap / wing cap
        "geo_switch_mario_stand_run": (1, 1),
    }
    for func, (each, largest) in expect.items():
        got = [c for c, _ in by.get(func, [])]
        if not got:
            errors.append(f"no {func} switch")
            continue
        if min(got) < each or max(got) < largest:
            errors.append(f"{func}: case counts {got}, expected every >= {each} and max >= {largest}")
        notes.append(f"{func}: {got}")
    eyes = [c for c, _ in by.get("geo_switch_mario_eyes", [])]
    if eyes and any(c != 8 for c in eyes):
        errors.append(f"eye switches must have exactly 8 cases: {eyes}")

    low = model.lower()
    for word in LEFTOVERS:
        hits = sorted(set(re.findall(rf"\b\w*{word}\w*\b", low)))
        if hits:
            errors.append(f"leftover Mario material/texture '{word}' in model.inc.c: {hits[:5]}")

    tex_errors, tex_rows = check_textures(model)
    errors.extend(tex_errors)
    face_errors, face_notes = check_face_materials(geo, model, actor)
    errors.extend(face_errors)
    notes.extend(face_notes)
    face_rows = [r for r in tex_rows if any(k in r["texture"] for k in FACE_TEXTURE_SIZES)]
    if not face_rows:
        errors.append("no eye/mouth face textures found in model.inc.c")
    for r in tex_rows:
        notes.append(f"texture {r['texture']} (tile {r['render_tile']}): loaded {r['loaded'][0]}x{r['loaded'][1]}, tile "
                     f"{r['tile'][0]}x{r['tile'][1]}, masks {r['masks'][0]}/{r['masks'][1]}, "
                     f"clamp {r['clamp'][1]}/{r['clamp'][0]} ({r['material']})")

    tris = count_tris_per_dl(model)
    total = sum(tris.values())
    lights = re.findall(r"Lights1 (\w+) = gdSPDefLights1\(\s*([^;]*)\);", model, re.S)
    textures = re.findall(r"(?:Texture|u8|u16) (\w+)\[\] = \{", model)
    report = {
        "actor": actor,
        "ok": not errors,
        "errors": errors,
        "notes": notes,
        "display_lists": len(tris),
        "total_tris_all_dls": total,
        "textures": textures,
        "lights": [n for n, _ in lights],
        "texture_tiles": tex_rows,
    }
    return report, tris


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    report, tris = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"VALIDATE {report['actor']}: {'OK' if report['ok'] else 'FAILED'}")
    for e in report["errors"]:
        print("  ERROR:", e)
    for n in report["notes"]:
        print("  ", n)
    print(f"  display lists: {report['display_lists']}, triangles in all DLs "
          f"(incl. eye-state override copies): {report['total_tris_all_dls']}")
    main_dls = {k: v for k, v in tris.items() if "_opt_" not in k and "Metal" not in k}
    print(f"  triangles in base (non-override, non-metal) DLs: {sum(main_dls.values())}")
    print(f"  textures: {report['textures']}")
    print(f"  lights: {report['lights']}")
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
