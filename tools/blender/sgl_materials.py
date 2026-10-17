"""Material recolouring / creation for character template surgery.

Colours come from character.json (sRGB hex). Fast64 stores light colours as
LINEAR RGBA; the exported ambient is half of the diffuse colour in sRGB (what
the template and vanilla Mario use), so both are set explicitly here.
"""
import bpy

from sgl_util import hex_to_srgb, linear_to_srgb, mix_hex, shade_hex, srgb_to_linear

EYE_MATERIALS = {
    "open": "Open Eyes (SKIN)",
    "half": "Half Closed Eyes (SKIN)",
    "closed": "Closed Eyes (SKIN)",
    "left": "Left Eyes (SKIN)",
    "right": "Right Eyes (SKIN)",
    "up": "Up Eyes (SKIN)",
    "down": "Down Eyes (SKIN)",
    "dead": "Dead Eyes (SKIN)",
}

# Mario-only materials that must not survive in the export.
REMOVED_MATERIALS = ("Mustache Vanilla (SKIN)", "Sideburns (HAIR)", "Logo (EMBLEM)", "Buttons (PANTS)",
                     "Mustache (Recoloring Optional)", "Button (Optional Recoloring)")


def set_f3d_color(mat, hex_color):
    f = mat.f3d_mat
    srgb = hex_to_srgb(hex_color)
    lin = tuple(srgb_to_linear(c) for c in srgb)
    amb = tuple(srgb_to_linear(c * 0.5) for c in srgb)
    if hasattr(f, "set_ambient_from_light"):
        f.set_ambient_from_light = False
    f.default_light_color = (*lin, 1.0)
    f.ambient_light_color = (*amb, 1.0)
    mat.diffuse_color = (*lin, 1.0)  # viewport / workbench colour


def f3d_color_hex(mat):
    lin = mat.f3d_mat.default_light_color[:3]
    return "#%02X%02X%02X" % tuple(round(linear_to_srgb(c) * 255) for c in lin)


def copy_material(src_name, new_name):
    mat = bpy.data.materials.get(new_name)
    if mat is not None:
        return mat
    mat = bpy.data.materials[src_name].copy()
    mat.name = new_name
    return mat


def _log2_exact(n):
    k = int(n).bit_length() - 1
    if n <= 0 or (1 << k) != n:
        raise ValueError(f"texture dimension {n} is not a power of two")
    return k


def set_tile_fields(field, pixels, clamp):
    """Tile S or T settings for a texture `pixels` texels long (what Fast64's
    setAutoProp does). Fast64 only refreshes these from its update callbacks,
    which return early in --background (no context material) and do not fire
    when autoprop was already True, so a texture swapped in from a script would
    otherwise export the template's 32x32 tile (gsDPSetTileSize/masks)."""
    field.clamp = clamp
    field.mirror = False
    field.low = 0.0
    field.high = float(pixels - 1)
    field.mask = _log2_exact(pixels)
    field.shift = 0


def set_f3d_texture(mat, image, clamp=True):
    f = mat.f3d_mat
    t = f.tex0
    t.tex = image
    try:
        t.tex_set = True
    except Exception:
        pass
    t.tex_format = "RGBA16"
    w, h = image.size
    t.autoprop = True
    set_tile_fields(t.S, w, clamp)
    set_tile_fields(t.T, h, clamp)
    check_f3d_texture(mat)


def check_f3d_texture(mat):
    """Raise if tex0's tile settings do not match its image size."""
    t = mat.f3d_mat.tex0
    w, h = t.tex.size
    got = (round(t.S.high) + 1, round(t.T.high) + 1, t.S.mask, t.T.mask, t.S.low, t.T.low)
    want = (w, h, _log2_exact(w), _log2_exact(h), 0.0, 0.0)
    if got != want:
        raise RuntimeError(f"{mat.name}: tile (w, h, maskS, maskT, lowS, lowT) {got} != {want}")
    return got


# Very dark hair renders as a flat black shape under SM64 lighting (ambient is half the
# light colour, so #1E1A20 ends up #0F0D10 on the shaded side and the facets vanish).
# Hair darker than this is lifted unless build.keep_exact_hair is set. The lift ADDS the
# same amount to every channel: scaling (the first version) also scaled the small channel
# differences of near-black, so a faint tint (#1E1A20) became a visible plum (#29242C).
HAIR_FLOOR = 0x2C


def lift_dark(hex_color, floor=HAIR_FLOOR):
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    m = max(r, g, b)
    if m >= floor:
        return hex_color
    d = floor - m
    return "#%02X%02X%02X" % tuple(min(255, x + d) for x in (r, g, b))


def build_palette(spec):
    """Return {role: hex} for every colour role the builder uses, with fallbacks."""
    c = spec["colors"]
    skin = c["skin"]
    top = c.get("top", "#808080")
    hair = c.get("hair", "#1E1A1B")
    if not spec.get("build", {}).get("keep_exact_hair"):
        hair = lift_dark(hair)
    pal = {
        "skin": skin,
        "hair": hair,
        "top": top,
        "top_detail": c.get("top_detail", shade_hex(top, 0.8)),
        "pants": c.get("pants", "#3B4E6E"),
        "shoes": c.get("shoes", "#F2F2F2"),
        "shoe_soles": c.get("shoe_soles", shade_hex(c.get("shoes", "#F2F2F2"), 0.85)),
        "hands": c.get("gloves", skin),
        "button": c.get("buttons", mix_hex(top, "#FFFFFF", 0.75)),
    }
    pal["cap"] = c.get("cap", top)
    pal["cap_inside"] = c.get("cap_inside", shade_hex(pal["cap"], 0.6))
    # extra named colours (tie, glasses, socks...) are passed through for accessories
    for k, v in c.items():
        pal.setdefault(k, v)
    return pal


def setup_materials(spec):
    """Recolour the template materials and create the extra ones.
    Returns {role: bpy.types.Material}."""
    pal = build_palette(spec)
    M = bpy.data.materials
    mats = {
        "skin": M["Skin (SKIN)"],
        "hair": M["Hair (HAIR)"],
        "top": M["Shirt (SHIRT)"],
        "pants": M["Pants (PANTS)"],
        "shoes": M["Shoes (SHOES)"],
        "hands": M["Gloves (GLOVES)"],
        "cap": M["Cap (CAP)"],
        "cap_inside": M["Cap Inside (CAP)"],
        "metal": M["Metal (METAL)"],
        "wing_base": M["Wing Base"],
        "wing_tip": M["Wing Tip"],
        "metal_wing_base": M["Metal Wing Base (METAL)"],
        "metal_wing_tip": M["Metal Wing Tip (METAL)"],
    }
    for role in ("skin", "hair", "top", "pants", "shoes", "hands", "cap", "cap_inside"):
        set_f3d_color(mats[role], pal[role])
    # new solid-colour materials, copied from template F3D materials so every
    # Fast64 setting (lighting, combiner, draw layer) matches
    for role, src, name in (
        ("top_detail", "Shirt (SHIRT)", "Shirt Detail (SHIRT)"),
        ("shoe_soles", "Shoes (SHOES)", "Shoe Soles (SHOES)"),
        ("button", "Shirt (SHIRT)", "Shirt Buttons (SHIRT)"),
    ):
        mats[role] = copy_material(src, name)
        set_f3d_color(mats[role], pal[role])
    for state, name in EYE_MATERIALS.items():
        mats["eyes_" + state] = M[name]
        set_f3d_color(M[name], pal["skin"])
    mats["mouth"] = copy_material("Open Eyes (SKIN)", "Mouth (SKIN)")
    set_f3d_color(mats["mouth"], pal["skin"])
    mats["_palette"] = pal
    return mats


def accessory_material(mats, role, hex_color, base="Shirt (SHIRT)"):
    """Get/create a solid accessory material (e.g. 'tie')."""
    key = role
    if key in mats:
        return mats[key]
    name = f"{role.replace('_', ' ').title()} (ACC)"
    mat = copy_material(base, name)
    set_f3d_color(mat, hex_color)
    mats[key] = mat
    return mat


def ensure_slot(obj, mat):
    me = obj.data
    for i, m in enumerate(me.materials):
        if m == mat:
            return i
    me.materials.append(mat)
    return len(me.materials) - 1


def compact_material_slots(obj):
    """Merge slots holding the same material and drop slots no face uses."""
    me = obj.data
    first = {}
    for i, m in enumerate(me.materials):
        first.setdefault(m.name if m else None, i)
    canon = [first[m.name if m else None] for m in me.materials]
    for p in me.polygons:
        p.material_index = canon[p.material_index]
    used = sorted({p.material_index for p in me.polygons})
    if len(used) == len(me.materials):
        return
    keep = [me.materials[i] for i in used]
    remap = {old: new for new, old in enumerate(used)}
    idx = [remap[p.material_index] for p in me.polygons]
    while len(me.materials):
        me.materials.pop()
    for m in keep:
        me.materials.append(m)
    for p, i in zip(me.polygons, idx):
        p.material_index = i
