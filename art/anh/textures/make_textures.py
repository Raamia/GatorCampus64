"""Anh face textures (Super Gatorlator 64) - FINAL set.

Same conventions as Daniel's (art/daniel/textures/make_textures.py): every pixel
comes from the ASCII grids / tables below (no antialiasing, no gradients, no
photo pixels), 64x32 eye states + a 32x16 mouth on a flat, fully opaque skin
background (the builder keys it to alpha 0), left/right halves mirror shapes,
eye positions identical across states, palette small and RGBA16-safe.

Drawn from reference/friends/anh/photo2 (close-up, main face reference) and
photo1/photo3 (smiling / three-quarter), then checked on the real head in a
scratch build (the in-engine look decided two of the changes noted below):

  eyes
  * open: calm almond eye, NOT Daniel's happy squint.  Flat, slightly hooded
    2-px upper lash; corners LEVEL (x 6 / x 23, mirror x 57 / x 40) with NO
    wings or tails (with tails, plus the unlit whites, the eyes read as
    eyeliner / mascara on the real head); curved lower lid drawn as a
    skin-shadow line (his lower lashes are faint), so small sclera wedges show
    under the iris on both sides, as in photo2.  16x4 opening, eye axis x 14.5
    / 48.5 (Daniel's), 16 px between the eyes, content rows 12-18 (centre row
    15.0, half a texel above Daniel's 15.5).
  * iris 10x7 with a 4x3 black pupil (Daniel's): top clipped by the lash, bottom
    row on the lower lid; 1-3 px of sclera on each side.  A narrower 8-px iris
    (more white, truer to the photo) was tried and dropped: unlit sclera texels
    pop against the shaded skin and made the eyes look wide and doe-like.
    2-px white glint on the top-left of the VISIBLE pupil (same image side in
    both eyes), so it survives every gaze and the half lid.
  * left/right move the iris 3 px, up 2, down 2; all five open-gaze states
    share exactly the same lid pixels and footprint - only the iris moves.
  * half: lash lowered over the top of the iris (2-px dark band), skin-shadow
    crease where the open lash top was, same lower lid.
  * closed: relaxed closed lid - a gentle "u" lash line on the same corners
    (his blink is calm, not Daniel's laughing "^"), lower-lid shadow kept for
    weight at game size; no crease above it (the builder darkens creases to
    0.70 x skin, which shows as a pale stray line on shaded skin).
  * dead: bold 3-px-stroke "X" (Daniel's), rows 11-19, centred on the eye axis.
  * no under-eye fold (tried: it made him look tired and merged into the eye
    at game size), no eyebrows (in every photo the fringe and the top rim of
    the glasses hide them), no glasses (they are 3D geometry).
  mouth (file name stays mouth_grin.png)
  * small closed-mouth slight smile, 16 px wide (x 8-23), rows 7-11: dark lip
    line whose corners turn up 2 px, a 1-row upper lip just off the skin tone
    in the middle, a fuller 2-row soft-pink lower lip (his most visible mouth
    feature in photo2).  No teeth.  Saturated two-tone rose lips were tried and
    dropped: unlit, they read as lipstick on the real head.

Colours: skin, skin_shadow and hair come from the spec (art/<id>/character.json);
lips and lip line are stored for Anh's skin and scaled per channel to another
skin tone, eye colours are fixed.  So the same art can be re-skinned for a
character "based_on" Anh (Josh: "regenerate Anh's face textures with this skin
value"):

    tools/.venv/bin/python -I make_textures.py
        -> Anh, writes next to this script
    ... make_textures.py --spec ../../josh/character.json --out <dir>
        -> same art on Josh's skin (written only where --out says)

Writes eyes_{open,half,closed,left,right,up,down,dead}.png (64x32 RGBA),
mouth_grin.png (32x16 RGBA), preview_sheet.png and preview_face.png, then runs
the spec checks (raises on any violation).  verify_textures.py is an
independent re-check of the written files.
"""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SPEC = os.path.join(HERE, '..', 'character.json')


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ------------------------------------------------------------------ palette
ANH_SKIN = hx('E4AE8E')        # the skin the skin-relative colours were picked on
FIXED = {
    'L': hx('2B1D1A'),   # eyelid / lash line
    'I': hx('3D2A22'),   # iris (very dark brown in the photos)
    'P': hx('110B0B'),   # pupil
    'h': hx('FFFFFF'),   # eye highlight
    'W': hx('F4F0EA'),   # sclera
}
SKIN_RELATIVE = {        # picked on Anh's skin, scaled per channel for other skins
    'q': hx('D08A7A'),   # upper lip (just off the skin)
    'p': hx('D47E72'),   # lower lip (soft pink)
    'm': hx('84403A'),   # lip line / mouth corners
}


def palette(spec):
    c = spec['colors']
    skin = hx(c['skin'])
    pal = {'.': skin, 's': hx(c['skin_shadow']), 'H': hx(c['hair'])}
    pal.update(FIXED)
    for k, v in SKIN_RELATIVE.items():
        pal[k] = tuple(int(min(255, round(v[i] * skin[i] / ANH_SKIN[i]))) for i in range(3))
    return pal


# ===================================================================== EYES
# The LEFT eye (image-left) is drawn as ASCII in a window of texture columns
# x = EX0 .. EX0+23 and rows y = EY0 .. EY0+11.  Outer corner on the left,
# inner corner (next to the nose) on the right.  The right eye is the exact
# mirror x -> 63 - x.  'W' marks the eye opening (sclera; the iris is stamped
# into it), 'L' lash / lid ink, 's' skin shadow, 'H' darkest ink.
EX0, EY0 = 4, 10
#            x = 4         1         2
#                456789012345678901234567
LIDS = {
    'open': [
        "........................",   # 10
        "........................",   # 11
        ".......LLLLLLLL.........",   # 12  2-px upper lash, flat (slightly hooded) top
        "....LLLLLLLLLLLLLL......",   # 13
        "..LLLWWWWWWWWWWWWLLL....",   # 14
        "..LWWWWWWWWWWWWWWWWL....",   # 15  corners level (x 6 / x 23), no wings
        "...sWWWWWWWWWWWWWWs.....",   # 16  curved lower lid (faint lashes = shadow)
        "....ssWWWWWWWWWWss......",   # 17
        "......ssssssssss........",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'half': [
        "........................",   # 10
        "........................",   # 11
        ".......ssssssss.........",   # 12  crease where the open lash top was
        "........................",   # 13
        "....LLLLLLLLLLLLLL......",   # 14  lash lowered 1-2 rows
        "..LLLLLLLLLLLLLLLLLL....",   # 15
        "...sWWWWWWWWWWWWWWs.....",   # 16
        "....ssWWWWWWWWWWss......",   # 17
        "......ssssssssss........",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'closed': [
        "........................",   # 10
        "........................",   # 11
        "........................",   # 12
        "........................",   # 13
        "........................",   # 14
        "..LL..............LL....",   # 15  same corners as open
        "...LLLL........LLLL.....",   # 16  relaxed, gently curved closed lid
        ".....LLLLLLLLLLLL.......",   # 17
        "......ssssssssss........",   # 18  lower lid stays (weight at game size)
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
}

IRIS = [  # 10 x 7 (Daniel's); by default rows 0-1 sit under the lash
    "..IIIIII..",
    ".IIIIIIII.",
    "IIIPPPPIII",
    "IIIPPPPIII",
    "IIIPPPPIII",
    "IIIIIIIIII",
    ".IIIIIIII.",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 10          # left eye: iris columns 10..19, centred on the opening 7..22 (axis 14.5)
IRIS_Y = 12          # rows 12..18: top clipped by the lash, round bottom on the lower lid
GLINT_N = 2          # glint pixels: top-left of the visible pupil
GAZE_X = 3
GAZE_UP = 2
GAZE_DOWN = 2

DEAD_X = [  # 14 x 9 knocked-out X (left eye), centred on the eye axis x 14.5
    "HHH........HHH",
    ".HHH......HHH.",
    "..HHH....HHH..",
    "...HHH..HHH...",
    ".....HHHH.....",
    "...HHH..HHH...",
    "..HHH....HHH..",
    ".HHH......HHH.",
    "HHH........HHH",
]
DEAD_X0, DEAD_Y0 = 8, 11   # rows 11..19, same centre row (15) as the open eye


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    if state == 'dead':
        for j, row in enumerate(DEAD_X):
            for i, ch in enumerate(row):
                if ch != '.':
                    g[DEAD_Y0 + j][DEAD_X0 + i] = ch
                    g[DEAD_Y0 + j][63 - (DEAD_X0 + i)] = ch
        return g
    tpl = LIDS['half' if state == 'half' else 'closed' if state == 'closed' else 'open']
    for j, row in enumerate(tpl):
        assert len(row) == 24, (state, j)
        for i, ch in enumerate(row):
            g[EY0 + j][EX0 + i] = ch
            g[EY0 + j][63 - (EX0 + i)] = ch
    if state == 'closed':
        return g
    for side in 'LR':
        ox = IRIS_X if side == 'L' else 63 - IRIS_X - (IW - 1)
        ox += gaze[0]
        oy = IRIS_Y + gaze[1]
        vis = []
        for j, row in enumerate(IRIS):
            for i, ch in enumerate(row):
                x, y = ox + i, oy + j
                if ch != '.' and g[y][x] == 'W' and ((x < 32) == (side == 'L')):
                    g[y][x] = ch
                    vis.append((x, y))
        # glint: GLINT_N px on the top-left of the VISIBLE pupil (same image
        # side in both eyes), so it survives every gaze and the half lid
        pup = sorted((y, x) for x, y in vis if g[y][x] == 'P')
        for y, x in pup[:GLINT_N]:
            g[y][x] = 'h'
    return g


# ==================================================================== MOUTH
# Left half (x = 0..15) of the 32x16 mouth; the right half is its mirror.
#   m lip line / corners   q upper lip   p lower lip
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    "................",  # 2
    "................",  # 3
    "................",  # 4
    "................",  # 5
    "................",  # 6
    "........m.......",  # 7  corner tip turned up
    ".........mmqqqqq",  # 8  subtle upper lip in the middle
    "...........mmmmm",  # 9  closed lip line, corners 1-2 px higher (slight smile)
    "..........pppppp",  # 10 full lower lip (his most visible mouth feature)
    "...........ppppp",  # 11
    "................",  # 12
    "................",  # 13
    "................",  # 14
    "................",  # 15
]


def mouth_grid():
    rows = []
    for r in MOUTH_HALF:
        assert len(r) == 16, r
        rows.append(list(r + r[::-1]))
    return rows


# ================================================================= TEXTURES
ORDER = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
         'eyes_up', 'eyes_down', 'eyes_dead', 'mouth_grin']


def grids():
    return {
        'eyes_open': eye_grid('open'),
        'eyes_half': eye_grid('half'),
        'eyes_closed': eye_grid('closed'),
        'eyes_left': eye_grid('open', (-GAZE_X, 0)),    # irises toward IMAGE left
        'eyes_right': eye_grid('open', (GAZE_X, 0)),    # irises toward IMAGE right
        'eyes_up': eye_grid('open', (0, -GAZE_UP)),
        'eyes_down': eye_grid('open', (0, GAZE_DOWN)),
        'eyes_dead': eye_grid('dead'),
        'mouth_grin': mouth_grid(),
    }


def build(pal):
    def to_img(grid):
        a = np.array([[(*pal[ch], 255) for ch in row] for row in grid], np.uint8)
        return Image.fromarray(a, 'RGBA')
    g = grids()
    return {k: to_img(g[k]) for k in ORDER}


# ================================================================= PREVIEWS
BG = (36, 38, 48)
TXT = (235, 235, 235)
CREASE_REL = 0.70    # tools/blender/sgl_textures.py: skin_shadow texels -> 0.70 x skin


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def preview_sheet(tex, name):
    S = 8
    f = font(20)
    cols = 3
    cw, ch = 64 * S + 32, 32 * S + 52
    rows = (len(ORDER) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw + 24, rows * ch + 56), BG)
    d = ImageDraw.Draw(sheet)
    d.text((24, 12), f'{name} face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
           fill=TXT, font=f)
    for i, n in enumerate(ORDER):
        x, y = 24 + (i % cols) * cw, 48 + (i // cols) * ch
        im = tex[n]
        d.text((x, y), f'{n}.png  ({im.width}x{im.height})', fill=TXT, font=f)
        sheet.paste(up(im, S).convert('RGB'), (x, y + 28))
    return sheet


# Face mock, 64x64, 1 texel = 1 px (same density the textures are drawn at).
# Hair, glasses, nose and face outline are rough stand-ins for the geometry.
MW = MH = 64
EYE_Y = 6          # eye texture top row on the mock (lash top -> row 17)
MOUTH_X, MOUTH_Y = 16, 39


def builder_view(im, pal):
    """What the builder does to the art before it reaches the game: skin-shadow
    texels darkened to CREASE_REL x skin ("darken" face_crease mode)."""
    a = np.array(im.convert('RGB'))
    hit = (a == np.array(pal['s'], np.uint8)).all(-1)
    a[hit] = np.round(np.array(pal['.'], np.float32) * CREASE_REL).astype(np.uint8)
    return Image.fromarray(a, 'RGB')


def face_mock(eye_im, mouth_im, pal, glasses=True, processed=False):
    if processed:
        eye_im, mouth_im = builder_view(eye_im, pal), builder_view(mouth_im, pal)
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = BG
    cx = (MW - 1) / 2
    yy, xx = np.mgrid[0:MH, 0:MW]
    # round, youthful face: widest at the cheeks (row 30), short soft jaw,
    # rounded chin
    t = np.where(yy < 30, (yy - 30) / 30.0, (yy - 30) / 32.0)
    half_w = 31.5 * np.sqrt(np.clip(1.0 - np.abs(t) ** 2.4, 0.0, 1.0))
    face = np.abs(xx - cx) <= half_w
    a[face] = pal['.']

    def paste(im, x0, y0):
        t = np.array(im.convert('RGB'))
        h, w = t.shape[:2]
        reg = a[y0:y0 + h, x0:x0 + w]
        m = face[y0:y0 + h, x0:x0 + w]
        reg[m] = t[m]

    paste(eye_im, 0, EYE_Y)
    paste(mouth_im, MOUTH_X, MOUTH_Y)
    shad = np.round(np.array(pal['.']) * CREASE_REL).astype(np.uint8) if processed else pal['s']
    # nose hint (the nose is geometry): tip shadow + nostrils
    for x, y in [(30, 34), (31, 34), (32, 34), (33, 34), (29, 33), (34, 33)]:
        a[y, x] = shad
    hair = np.array(pal['H'], np.uint8)
    # mushroom cut: rounded cap, side-swept fringe (his parting on his right =
    # image left, the bangs sweep toward image right), heavy sides over the ears
    fb = EYE_Y + 4                        # fringe bottom (lash top = EYE_Y + 11)
    cap = ((xx - cx) / 35.0) ** 2 + ((yy - 24) / 25.0) ** 2 <= 1.0
    sweep = fb + np.clip((xx - 10) / 14.0, 0, 3).astype(int)      # lower toward image right
    hair_m = cap & (yy <= sweep)
    side = cap & (np.abs(xx - cx) >= 27.5) & (yy <= EYE_Y + 24 + (np.abs(xx - cx) - 27.5))
    a[hair_m | side] = hair
    for x0, depths in [(4, (1, 1)), (17, (1,)), (26, (1, 2, 1)), (40, (1, 1, 2)), (52, (1, 1))]:
        for i, dpt in enumerate(depths):
            top = int(sweep[0, x0 + i])
            for k in range(1, dpt + 1):
                a[top + k, x0 + i] = hair
    if glasses:
        # thick rectangular frames (geometry in game): lens x 3..27 / 36..60,
        # rows 14..27 of the mock (eye texture rows 8..21), 2-px rims, bridge
        g = np.array(pal['L'], np.uint8) * 0 + np.array((0x15, 0x16, 0x1C), np.uint8)
        for x0 in (3, 36):
            x1, y0, y1 = x0 + 24, EYE_Y + 8, EYE_Y + 22
            a[y0:y0 + 2, x0 + 1:x1] = g
            a[y1 - 1:y1 + 1, x0 + 1:x1] = g
            a[y0 + 1:y1, x0:x0 + 2] = g
            a[y0 + 1:y1, x1 - 1:x1 + 1] = g
        a[EYE_Y + 10:EYE_Y + 12, 28:36] = g
        for x in (0, 1, 2):
            a[EYE_Y + 9:EYE_Y + 11, x] = g
            a[EYE_Y + 9:EYE_Y + 11, 63 - x] = g
    return Image.fromarray(a, 'RGB')


def rgba16(im):
    a = np.array(im.convert('RGB')).astype(np.int32) >> 3
    return Image.fromarray(((a << 3) | (a >> 2)).astype(np.uint8), 'RGB')


def preview_face(tex, pal):
    S = 8
    f = font(20)
    fo = face_mock(tex['eyes_open'], tex['mouth_grin'], pal)
    fc = face_mock(tex['eyes_closed'], tex['mouth_grin'], pal)
    fn = face_mock(tex['eyes_open'], tex['mouth_grin'], pal, glasses=False)
    gap = 6
    native = Image.new('RGB', (MW * 3 + gap * 2, MH), BG)
    for i, im in enumerate((fo, fc, fn)):
        native.paste(im, (i * (MW + gap), 0))
    big = Image.new('RGB', (MW * S * 2 + 24, MH * S), BG)
    big.paste(up(fo, S), (0, 0))
    big.paste(up(fn, S), (MW * S + 24, 0))
    # in-game simulation: builder crease darkening, RGBA16 quantised,
    # box-filtered to 15/20/25 px tall
    states = ORDER[:8]
    sims = []
    for th, gl in ((15, True), (20, True), (25, True), (25, False)):
        row = [up(rgba16(face_mock(tex[s], tex['mouth_grin'], pal, gl, True)).resize((th, th), Image.BOX), S)
               for s in states]
        sims.append((th, gl, row))
    sim_w = sum(r.width + 12 for r in sims[-1][2])
    W_ = max(big.width, sim_w) + 48
    H_ = (16 + 28 + MH + 24 + 28 + big.height + 24
          + sum(28 + r[0].height + 20 for _, _, r in sims) + 8)
    pf = Image.new('RGB', (W_, H_), BG)
    d = ImageDraw.Draw(pf)
    y = 16
    d.text((24, y), 'native 1x, 64x64 each: eyes_open + mouth_grin  |  eyes_closed (blink)  |  '
                    'eyes_open without glasses', fill=TXT, font=f)
    y += 28
    pf.paste(native, (24, y))
    y += MH + 24
    d.text((24, y), '8x nearest neighbour, with / without glasses  (hair, glasses, nose and face shape '
                    'are stand-ins for the geometry)', fill=TXT, font=f)
    y += 28
    pf.paste(big, (24, y))
    y += big.height + 24
    for th, gl, row in sims:
        d.text((24, y), f'in-game sim, face {th}px tall{"" if gl else ", NO glasses"} (creases darkened '
                        'like the builder, RGBA16 + box filter, shown 8x): '
                        'open half closed left right up down dead', fill=TXT, font=f)
        y += 28
        x = 24
        for r in row:
            pf.paste(r, (x, y))
            x += r.width + 12
        y += row[0].height + 20
    return pf


# =================================================================== CHECKS
def check(tex, pal):
    """Spec checks; raises AssertionError on any violation."""
    skin = np.array(pal['.'], np.uint8)
    for name, im in tex.items():
        exp = (32, 16) if name == 'mouth_grin' else (64, 32)
        a = np.array(im)
        assert im.mode == 'RGBA', name
        assert im.size == exp, (name, im.size)
        assert (a[..., 3] == 255).all(), name
        border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])[:, :3]
        assert (border == skin).all(), f'{name}: border not skin'
        mask = (a[..., :3] != skin).any(-1)
        assert (mask == mask[:, ::-1]).all(), f'{name}: shape not mirror-symmetric'
    # every open-gaze state shares the exact lid pixels and footprint of open
    ref = np.array(tex['eyes_open'])[..., :3]
    lid = (ref == pal['L']).all(-1)
    foot = (ref != skin).any(-1)
    for n in ('eyes_left', 'eyes_right', 'eyes_up', 'eyes_down'):
        b = np.array(tex[n])[..., :3]
        assert ((b == pal['L']).all(-1) == lid).all(), f'{n}: lids differ from eyes_open'
        assert ((b != skin).any(-1) == foot).all(), f'{n}: footprint differs from eyes_open'
        assert ((b == pal['h']).all(-1)).sum() >= 4, f'{n}: glint lost'
        assert ((b == pal['W']).all(-1)).sum() >= 8, f'{n}: no sclera left'
    # colours: palette only, all distinct after 5-bit (RGBA16) quantising
    cols = set()
    for im in tex.values():
        cols |= set(map(tuple, np.array(im)[..., :3].reshape(-1, 3)))
    assert cols <= set(pal.values()), 'off-palette colour'
    q = {(r >> 3, g >> 3, b >> 3) for r, g, b in cols}
    assert len(q) == len(cols), 'colours merge in RGBA16'
    # after the builder's crease darkening the crease must stay distinct too
    dark = tuple(int(round(v * CREASE_REL)) for v in pal['.'])
    assert (dark[0] >> 3, dark[1] >> 3, dark[2] >> 3) not in q - {(c[0] >> 3, c[1] >> 3, c[2] >> 3)
                                                                   for c in [pal['s']]}, 'crease merges'
    return sorted('#%02X%02X%02X' % c for c in cols)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', default=DEFAULT_SPEC, help='character.json whose colours to use')
    ap.add_argument('--out', default=HERE, help='output directory (default: next to this script)')
    args = ap.parse_args()
    with open(args.spec) as fh:
        spec = json.load(fh)
    pal = palette(spec)
    tex = build(pal)
    cols = check(tex, pal)
    os.makedirs(args.out, exist_ok=True)
    for name, im in tex.items():
        im.save(os.path.join(args.out, name + '.png'))
    preview_sheet(tex, spec.get('name', spec.get('id', '?'))).save(os.path.join(args.out, 'preview_sheet.png'))
    preview_face(tex, pal).save(os.path.join(args.out, 'preview_face.png'))
    print(f'ok ({spec.get("id")}): {len(tex)} textures; {len(cols)} colours:', ' '.join(cols))


if __name__ == '__main__':
    main()
