"""Face textures: find the best available source set, key the skin background to
alpha 0, darken the crease lines, bleed the ink colours into the transparent texels
(no light halo around eyes/mouth, see bleed_transparent), write processed copies to
art/<id>/build/tex/ and load them into Blender.

Source priority:
  1. art/<id>/textures/          (approved final art)
  2. art/<id>/candidates/<name>/ (most complete set, newest wins ties)
  3. generated placeholder       (sgl_face_gen, written to build/tex/generated/)
Sources are never modified.
"""
import glob
import os

import bpy
import numpy as np

import sgl_face_gen
from sgl_util import art_dir, build_dir, hex_to_rgb8, write_png

EYE_FILES = {
    "open": "eyes_open",
    "half": "eyes_half",
    "closed": "eyes_closed",
    "left": "eyes_left",
    "right": "eyes_right",
    "up": "eyes_up",
    "down": "eyes_down",
    "dead": "eyes_dead",
}
MOUTH_FILE = "mouth_grin"
REQUIRED = list(EYE_FILES.values()) + [MOUTH_FILE]
EYE_SIZE = (64, 32)
MOUTH_SIZE = (32, 16)

# Opaque face texels render UNLIT (combiner (TEXEL0-SHADE)*TEXEL0_ALPHA+SHADE), while the
# skin around them is vertex-shaded down to the ambient level (half the skin colour).
# Crease lines drawn in colors.skin_shadow (about 90% of the skin) therefore read as PALE
# lines whenever the face is shaded (top-down camera, head turned from the light).
# build.face_crease picks what the processed copy does with those texels:
#   "darken" (default): CREASE_REL x the skin colour, about the skin's shade at N.L 0.2,
#            so a crease is darker than the skin around it in nearly every light
#   "key":   alpha 0 (no creases)        "keep": as drawn
CREASE_REL = 0.70


def _complete(d):
    return sum(os.path.isfile(os.path.join(d, n + ".png")) for n in REQUIRED)


def find_source(char_id, spec, out_root=None):
    final = os.path.join(art_dir(char_id), "textures")
    if os.path.isdir(final) and _complete(final) == len(REQUIRED):
        return final, "final"
    # characters "based_on" another (e.g. Josh -> Anh) share its face art; the flat
    # border colour is keyed to alpha 0 even when it is the base character's skin
    from sgl_util import load_spec
    base, seen = spec.get("based_on"), {char_id}
    while base and base not in seen:
        seen.add(base)
        base_final = os.path.join(art_dir(base), "textures")
        if os.path.isdir(base_final) and _complete(base_final) == len(REQUIRED):
            return base_final, f"final:{base}"
        base = load_spec(base).get("based_on")
    cands = [d for d in glob.glob(os.path.join(art_dir(char_id), "candidates", "*")) if os.path.isdir(d)]
    cands = [d for d in cands if _complete(d) == len(REQUIRED)]
    if cands:
        cands.sort(key=lambda d: max(os.path.getmtime(os.path.join(d, n + ".png")) for n in REQUIRED), reverse=True)
        return cands[0], "candidate:" + os.path.basename(cands[0])
    gen = os.path.join(out_root or build_dir(char_id), "tex", "generated")
    sgl_face_gen.generate(spec, gen)
    return gen, "generated"


def _read_rgba8(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    arr = np.flipud(arr)  # top-to-bottom rows
    return np.clip(np.round(arr * 255), 0, 255).astype(np.uint8)


def border_colour(arr):
    """Most common opaque RGB on the image border, and its share of the border."""
    edge = np.concatenate([arr[0], arr[-1], arr[1:-1, 0], arr[1:-1, -1]])
    edge = edge[edge[:, 3] >= 128][:, :3]
    if not len(edge):
        return None, 0.0
    cols, counts = np.unique(edge, axis=0, return_counts=True)
    k = int(np.argmax(counts))
    return tuple(int(c) for c in cols[k]), float(counts[k]) / (2 * arr.shape[1] + 2 * (arr.shape[0] - 2))


def key_skin(arr, skin_hex, extra_keys=()):
    """Pixels exactly equal to the skin colour (or to one of extra_keys, or already
    transparent) -> alpha 0 (their RGB is the skin colour until bleed_transparent
    replaces it)."""
    skin = np.array(hex_to_rgb8(skin_hex), dtype=np.uint8)
    out = arr.copy()
    clear = np.all(out[..., :3] == skin, axis=-1) | (out[..., 3] < 128)
    for rgb in extra_keys:
        clear |= np.all(out[..., :3] == np.array(rgb, dtype=np.uint8), axis=-1)
    out[clear, :3] = skin
    out[clear, 3] = 0
    out[~clear, 3] = 255
    return out, int(clear.sum())


def bleed_transparent(arr):
    """Alpha bleeding. Opaque face texels render UNLIT through the combiner
    (TEXEL0 - SHADE) * TEXEL0_ALPHA + SHADE, and coopdx filters RGB and alpha
    separately (straight alpha, bilinear): at the edge of a lash or lip the filtered
    RGB is mixed with the RGB of the transparent texel next to it. With the skin RGB
    there (key_skin), the edge blends toward UNLIT skin while the face around it is
    shaded darker, which draws a thin light outline around eyes and mouth whenever the
    face is turned from the light. Every alpha-0 texel therefore gets the RGB of the
    nearest opaque texels instead: grown ring by ring, each new texel the mean of its
    already-filled 8-neighbours (the first ring is the mean of the opaque texels it
    touches). Alpha is unchanged, so the mask and the transparent clamp edges stay as
    they are; the filtered edge then fades from the ink straight to the shaded skin.
    Returns (array, number of transparent texels recoloured)."""
    out = arr.copy()
    filled = out[..., 3] > 0
    clear = ~filled
    if not filled.any() or not clear.any():
        return out, 0
    rgb = out[..., :3].astype(np.float32)
    h, w = filled.shape
    while not filled.all():
        acc = np.zeros((h, w, 3), np.float32)
        cnt = np.zeros((h, w), np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                ys, yd = slice(max(dy, 0), h + min(dy, 0)), slice(max(-dy, 0), h + min(-dy, 0))
                xs, xd = slice(max(dx, 0), w + min(dx, 0)), slice(max(-dx, 0), w + min(-dx, 0))
                f = filled[ys, xs]
                acc[yd, xd] += rgb[ys, xs] * f[..., None]
                cnt[yd, xd] += f
        new = ~filled & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        filled = filled | new
    out[clear, :3] = np.clip(np.round(rgb[clear]), 0, 255).astype(np.uint8)
    out[clear, 3] = 0
    return out, int(clear.sum())


def source_palette(char_id, spec, kind):
    """(skin, skin_shadow) the face art was PAINTED with: the base character's colours
    for art shared through based_on (kind "final:<base>"), else this character's own.
    The background key and the crease texels are matched against these; the creases
    are then darkened relative to the skin of the character being built."""
    src = kind.split(":", 1)[1] if kind.startswith("final:") else char_id
    if src == char_id:
        colors = spec["colors"]
    else:
        from sgl_util import load_spec
        colors = load_spec(src)["colors"]
    return colors["skin"], colors.get("skin_shadow")


def treat_creases(arr, skin_hex, crease_hex, mode):
    """Apply build.face_crease to opaque texels of exactly the crease colour crease_hex
    (the art's skin_shadow, see source_palette); "darken" sets them to CREASE_REL x
    skin_hex (the built character's skin). Returns (array, number of texels changed)."""
    if not crease_hex or mode == "keep":
        return arr, 0
    out = arr.copy()
    hit = np.all(out[..., :3] == np.array(hex_to_rgb8(crease_hex), dtype=np.uint8), axis=-1) & (out[..., 3] > 0)
    skin = np.array(hex_to_rgb8(skin_hex), dtype=np.float32)
    if mode == "key":
        out[hit, :3] = skin.astype(np.uint8)
        out[hit, 3] = 0
    elif mode == "darken":
        out[hit, :3] = np.clip(np.round(skin * CREASE_REL), 0, 255).astype(np.uint8)
    else:
        raise ValueError(f"build.face_crease must be darken, key or keep, not {mode!r}")
    return out, int(hit.sum())


def process_face_textures(char_id, spec, out_root=None):
    src, kind = find_source(char_id, spec, out_root)
    out_dir = os.path.join(out_root or build_dir(char_id), "tex")
    os.makedirs(out_dir, exist_ok=True)
    skin = spec["colors"]["skin"]
    art_skin, crease = source_palette(char_id, spec, kind)
    crease_mode = spec.get("build", {}).get("face_crease", "darken")
    result = {"source": src, "kind": kind, "files": {}, "crease_mode": crease_mode, "creases": {},
              "bled": {}}
    for name in REQUIRED:
        arr = _read_rgba8(os.path.join(src, name + ".png"))
        want = MOUTH_SIZE if name == MOUTH_FILE else EYE_SIZE
        if (arr.shape[1], arr.shape[0]) != want:
            raise ValueError(f"{src}/{name}.png is {arr.shape[1]}x{arr.shape[0]}, expected {want[0]}x{want[1]}")
        # Face art is painted on a flat background that must become alpha 0 (an opaque
        # background would render as an UNLIT skin-coloured rectangle in game). The
        # background is the art's skin colour by convention; a different flat border
        # colour (art painted on another skin tone) is keyed too, with a warning.
        extra = []
        bg, share = border_colour(arr)
        if bg is not None and bg != tuple(hex_to_rgb8(art_skin)) and share > 0.5:
            print(f"SGL WARNING: {name}: background #%02X%02X%02X is not the art's skin colour {art_skin}; "
                  f"keying it to alpha 0 too" % bg)
            extra.append(bg)
        keyed, n_clear = key_skin(arr, art_skin, extra)
        keyed, n_crease = treat_creases(keyed, skin, crease, crease_mode)
        if n_crease:
            result["creases"][name] = n_crease
        keyed, result["bled"][name] = bleed_transparent(keyed)
        opaque = int((keyed[..., 3] > 0).sum())
        # clamp addressing repeats the edge texels: they must be transparent
        edge = np.concatenate([keyed[0, :, 3], keyed[-1, :, 3], keyed[:, 0, 3], keyed[:, -1, 3]])
        if edge.any():
            raise ValueError(f"{src}/{name}.png: {int((edge > 0).sum())} opaque edge texels after keying "
                             f"(G_TX_CLAMP would smear them across the face)")
        if opaque == 0:
            raise ValueError(f"{src}/{name}.png: no opaque texels left after keying")
        path = os.path.join(out_dir, name + ".png")
        write_png(path, [[tuple(int(v) for v in px) for px in row] for row in keyed])
        result["files"][name] = path
        print(f"SGL tex {name}: {opaque} opaque texels -> {path}")
    return result


def load_images(char_id, files):
    """Load processed PNGs as Blender images named <id>_<name> and pack them."""
    imgs = {}
    for name, path in files.items():
        img_name = f"{char_id}_{name}"
        old = bpy.data.images.get(img_name)
        if old is not None:
            bpy.data.images.remove(old)
        img = bpy.data.images.load(path, check_existing=False)
        img.name = img_name
        img.alpha_mode = "STRAIGHT"
        img.pack()
        imgs[name] = img
    return imgs
