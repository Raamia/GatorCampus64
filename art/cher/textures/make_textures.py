"""Cher face textures (Super Gatorlator 64) - FINAL set.

Drawn from her only reference photo (reference/friends/cher/photo1.png, a front
portrait) in the same style, sizes and conventions as Daniel's approved set
(art/daniel/textures/), and checked on the real procedural head with scratch
builds.  What makes her read at tiny size: dark warm eyes under a heavy upper
lash with only small white corner wedges, soft brows well above the eyes, the
crinkled "smiling" lower lid, and a gentle pink-lipped smile showing the upper
teeth.

  eyes (left eye drawn as ASCII, the right eye is its exact mirror x -> 63 - x)
  * corners: outer x 5 / inner x 22 (right eye 41 / 58), 18 px corner to corner,
    18 px between the eyes (about one eye-width, like the photo: 42 px eyes,
    45 px apart).  Eye content rows 12-17 (open), the X of dead 11-19.
  * open (fix round 2: narrower, as in the photo): soft almond under a heavy
    2-row upper lash with a 1-px flick past the outer corner, a 3-row
    opening whose bottom row is cut in by the lower lid (her cheeks push the
    lower lid up when she smiles), and a skin-shadow smile crinkle right
    under it.  The 10x5 iris (4x3 pupil, 2-px white glint upper-right of the
    pupil, same image side in both eyes, as in the photo) fills the opening
    top to bottom, so only small white wedges show at the corners - at game
    size a narrow dark warm eye that crinkles, not a wide white stare.  (The
    first final set had a 4-row opening: the review found it too wide.)
  * lower lid / crinkle: skin shadow; the builder darkens skin-shadow texels
    to 0.70 x skin, so in game it is a soft brown crease.
  * left/right move the iris 3 px, up 2 (a row of white under it), down 1
    (a white sliver over it).  All five open-gaze states share exactly the
    same lid pixels and footprint - only the iris moves.
  * half: lash lowered 2 rows onto the lower lid, one row of iris showing,
    skin-shadow crease where the open lash was.
  * closed: 2-px happy arc spanning the same corner-to-corner width (her
    eyes crinkle shut when she smiles), on the open eye's rows, same crinkle.
  * dead: Daniel's 14x9 X (3-px strokes, single 4-px crossing), rows 11-19,
    centred on the eye axis.
  * brows: her brows show (side part, open forehead) - soft dark brown, 2 rows
    thick over most of their length (1-row parts foreshorten to hairlines on the
    sloping forehead), tail and inner head dipping 1 row; rows 5-7, x 5..23,
    identical in all 8 states so they never jump during a blink.  Keep the hair
    fringe edge above texture row 5 (default face_layout: u ~0.72).
  mouth (32x16, left half drawn, mirrored; file name kept as mouth_grin.png)
  * gentle smile (fix round 2: lips mostly closed, as in the photo), 26 px
    wide (x 3..28): upper lip (darker rose) 1 row at the corners, 2 rows in
    the middle; small dark corner wedges turned up 1 px; a 2-row band of
    upper teeth, narrower than the mouth, resting on a full 3-row pink lower
    lip.  No lower teeth, no tongue, no bite line.  (The first final set had
    a 4-row teeth band - an open grin.)

Every pixel comes from the ASCII grids / tables below - no antialiasing, no
gradients, no photo pixels.  Palette: 12 colours, all distinct in RGBA16; the
background is exactly the spec skin #E8B596 (fully opaque, keyed to alpha 0 by
the builder) and creases use exactly the spec skin_shadow #D09C7E.  Run:

    tools/.venv/bin/python -I make_textures.py

Writes next to this script: eyes_{open,half,closed,left,right,up,down,dead}.png
(64x32 RGBA), mouth_grin.png (32x16 RGBA), preview_sheet.png and
preview_face.png, then runs the spec checks (raises on any violation).
verify_textures.py is an independent re-check of the written files.
"""
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(OUT, '..', 'character.json')


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ------------------------------------------------------------------ palette
PAL = {
    '.': hx('E8B596'),   # skin (texture background - exact spec colours.skin)
    's': hx('D09C7E'),   # skin shadow (exact spec colours.skin_shadow): creases
    'B': hx('4E3631'),   # eyebrow (soft dark brown, lighter than the hair)
    'L': hx('221819'),   # lash / lid line / X
    'I': hx('46291F'),   # iris (warm dark brown)
    'P': hx('120C0C'),   # pupil
    'h': hx('FFFFFF'),   # eye glint
    'W': hx('EEE7DF'),   # sclera (a touch warmer than pure white)
    'u': hx('B8606A'),   # upper lip (darker rose)
    'p': hx('D97C88'),   # lower lip (pink)
    'm': hx('5E2430'),   # mouth corners
    'T': hx('FFFDF2'),   # teeth
}
SKIN = PAL['.']
HAIR = hx('1A1517')      # spec colours.hair (preview mock only)


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# ===================================================================== EYES
# The LEFT eye (image-left) is drawn as ASCII in a window of texture columns
# x = EX0 .. EX0+23.  Outer corner on the left, inner corner (next to the nose)
# on the right.  The right eye is the exact mirror x -> 63 - x.  'W' marks the
# eye opening (sclera; the iris is stamped into it), 'L' lash / lid ink,
# 's' skin shadow, 'B' brow.
EX0 = 4
BROW_Y0 = 4
#            x = 4         1         2
#                456789012345678901234567
BROW = [
    "........................",   # 4
    "....BBBBBBBBBBBBB.......",   # 5  x 8..20
    "..BBBBBBBBBBBBBBBBBB....",   # 6  x 6..23
    ".BB...............BB....",   # 7  tail x 5-6, inner head x 22-23
    "........................",   # 8
]
LID_Y0 = 10
LIDS = {
    'open': [
        "........................",   # 10
        "........................",   # 11
        "....LLLLLLLLLLL.........",   # 12  lash x 8..18
        "..LLLLLLLLLLLLLLL.......",   # 13  x 6..20
        ".LLLWWWWWWWWWWWLLL......",   # 14  outer corner + flick x 5..7
        "..LsWWWWWWWWWWWWWLL.....",   # 15  inner corner x 22
        "....ssWWWWWWWWWWss......",   # 16  lower lid pushed up by the smile
        "......ssssssssss........",   # 17  smile crinkle under the eye
        "........................",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'half': [
        "........................",   # 10
        "........................",   # 11
        "....sssssssssss.........",   # 12  crease where the open lash was
        "........................",   # 13
        "....LLLLLLLLLLL.........",   # 14  lash lowered 2 rows
        ".LLLLLLLLLLLLLLLLLL.....",   # 15  x 5..22
        "....ssWWWWWWWWWWss......",   # 16
        "......ssssssssss........",   # 17
        "........................",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'closed': [
        "........................",   # 10
        "........................",   # 11
        "........................",   # 12
        ".....LLLLLLLLL..........",   # 13  happy arc, 2 px thick
        "...LLLLLLLLLLLLLL.......",   # 14
        ".LLLL.........LLLLL.....",   # 15
        "..L...............L.....",   # 16  same corner-to-corner span as open
        "......ssssssssss........",   # 17  smile crinkle (as open)
        "........................",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
}

IRIS = [  # 10 x 5: fills the 3-row opening, leaving small white corner wedges
    ".IIIIIIII.",
    "IIIPPPPIII",
    "IIIPPPPIII",
    "IIIIPPIIII",
    ".IIIIIIII.",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 9           # left eye: iris columns 9..18
IRIS_Y = 13          # rows 13..17 (top and bottom rows sit under the lids)
GLINT = [(6, 1), (5, 1)]   # upper right of the pupil, same image side in both eyes
GAZE_X = 3
GAZE_UP = 2          # a row of white under the iris
GAZE_DOWN = 1        # a white sliver over it

DEAD_X = [  # 14 x 9, columns 7..20, rows 11..19 (left eye)
    "LLL........LLL",
    ".LLL......LLL.",
    "..LLL....LLL..",
    "...LLL..LLL...",
    ".....LLLL.....",
    "...LLL..LLL...",
    "..LLL....LLL..",
    ".LLL......LLL.",
    "LLL........LLL",
]
DEAD_X0, DEAD_Y0 = 7, 11


def stamp(g, tpl, y0):
    for j, row in enumerate(tpl):
        assert len(row) == 24, (y0 + j, row)
        for i, ch in enumerate(row):
            if ch != '.':
                g[y0 + j][EX0 + i] = ch
                g[y0 + j][63 - (EX0 + i)] = ch


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    stamp(g, BROW, BROW_Y0)          # brows: identical in every state
    if state == 'dead':
        for j, row in enumerate(DEAD_X):
            for i, ch in enumerate(row):
                if ch != '.':
                    g[DEAD_Y0 + j][DEAD_X0 + i] = ch
                    g[DEAD_Y0 + j][63 - (DEAD_X0 + i)] = ch
        return g
    stamp(g, LIDS['half' if state == 'half' else 'closed' if state == 'closed' else 'open'], LID_Y0)
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
        # glint: keep it on the top visible iris row so it never vanishes
        top = min(y for _, y in vis)
        dy0 = max(0, top - (oy + min(d for _, d in GLINT)))
        for dx, dy in GLINT:
            x, y = ox + dx, oy + dy + dy0
            if g[y][x] in 'IP':
                g[y][x] = 'h'
    return g


# ==================================================================== MOUTH
# Left half (x = 0..15) of the 32x16 smile; the right half is its mirror.
#   u upper lip   p lower lip   m dark mouth corners   T upper teeth
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    "................",  # 2
    "................",  # 3
    "................",  # 4
    ".........uuuuuuu",  # 5  upper lip, 2 rows in the middle
    "...muuuuuuuuuuuu",  # 6  corner tip turned up 1 px
    "...mmmTTTTTTTTTT",  # 7  upper teeth: 2 rows, narrower than the mouth
    "....mmmTTTTTTTTT",  # 8
    "......pppppppppp",  # 9  full pink lower lip right under the teeth
    ".......ppppppppp",  # 10
    ".........ppppppp",  # 11
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


def build():
    grids = {
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
    return {k: to_img(grids[k]) for k in ORDER}


# ================================================================= PREVIEWS
BG = (36, 38, 48)
TXT = (235, 235, 235)
MOCK_BG = (104, 110, 124)   # mid grey (like the Blender previews) under the chin
SHAD = PAL['s']


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def preview_sheet(tex):
    S = 8
    f = font(20)
    cols = 3
    cw, ch = 64 * S + 32, 32 * S + 52
    rows = (len(ORDER) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw + 24, rows * ch + 56), BG)
    d = ImageDraw.Draw(sheet)
    d.text((24, 12), 'Cher face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
           fill=TXT, font=f)
    for i, name in enumerate(ORDER):
        x, y = 24 + (i % cols) * cw, 48 + (i // cols) * ch
        im = tex[name]
        d.text((x, y), f'{name}.png  ({im.width}x{im.height})', fill=TXT, font=f)
        sheet.paste(up(im, S).convert('RGB'), (x, y + 28))
    return sheet


# Face mock, 80x72, 1 texel = 1 px (same density the textures are drawn at); the
# 64-px eye texture spans the round face at cheekbone width (x 8..71).  Hair,
# nose and face outline are rough stand-ins for the real geometry.
MW, MH = 80, 72
FX = 8             # eye texture left column on the mock
EYE_Y = 8          # eye texture top row on the mock (brows rows 13-15, lash top row 20)
MOUTH_X, MOUTH_Y = FX + 16, 39


def face_mock(eye_im, mouth_im):
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = MOCK_BG
    cx = (MW - 1) / 2
    yy, xx = np.mgrid[0:MH, 0:MW]
    # soft round face: widest (64 px) at row 32, full round cheeks and chin
    t = np.where(yy < 32, (yy - 32) / 32.0, (yy - 32) / 33.0)
    half_w = 32.5 * np.clip(1.0 - np.abs(t) ** 2.4, 0.0, 1.0) ** 0.5
    face = np.abs(xx - cx) <= half_w
    a[face] = SKIN

    def paste(im, x0, y0):
        t = np.array(im.convert('RGB'))
        h, w = t.shape[:2]
        reg = a[y0:y0 + h, x0:x0 + w]
        m = face[y0:y0 + h, x0:x0 + w]
        reg[m] = t[m]

    paste(eye_im, FX, EYE_Y)
    paste(mouth_im, MOUTH_X, MOUTH_Y)
    # nose hint (the nose is geometry): tip shadow + nostrils
    for x, y in [(38, 35), (39, 35), (40, 35), (41, 35), (37, 34), (42, 34)]:
        a[y, x] = SHAD
    # hair: side part at x 33 (her right of centre); the hairline curves down to
    # each temple, the bigger sweep falls to her left (image right); long straight
    # curtains hang down both sides past the chin
    edge_x, edge_y = np.array([33, 28, 20, 14, 10, 8.5]), np.array([0, 2, 5, 9, 15, 26])
    redge_x, redge_y = np.array([33, 40, 50, 60, 67, 70, 71]), np.array([0, 3, 7, 10, 13, 20, 26])
    hair = np.zeros_like(face)
    for y in range(MH):
        if y <= 26:
            lx, rx = np.interp(y, edge_y, edge_x), np.interp(y, redge_y, redge_x)
        else:
            lx, rx = 8.5 + 0.06 * (y - 26), 71 - 0.06 * (y - 26)
        hair[y] = (xx[y] < lx) | (xx[y] > rx)
    hair |= ~face & ((yy < 30) | (np.abs(xx - cx) > 22))   # crown and curtains behind
    hair &= ~((yy > 26) & face & (np.abs(xx - cx) < half_w - 1.0))
    a[hair] = HAIR
    # wispy face-framing strands over the cheek edges
    for x0, y0, y1 in [(10, 24, 44), (69, 24, 44)]:
        for y in range(y0, y1):
            a[y, x0 + (1 if x0 > 40 else -1) * ((y - y0) // 14)] = HAIR
    return Image.fromarray(a, 'RGB')


def rgba16(im):
    a = np.array(im.convert('RGB')).astype(np.int32) >> 3
    return Image.fromarray(((a << 3) | (a >> 2)).astype(np.uint8), 'RGB')


def ingame(im):
    """The builder's default build.face_crease 'darken': skin-shadow texels -> 0.70 x skin."""
    a = np.array(im.convert('RGBA'))
    hit = (a[..., :3] == np.array(PAL['s'])).all(-1)
    a[hit, :3] = np.round(np.array(SKIN) * 0.70).astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def preview_face(tex):
    S = 8
    f = font(20)
    fo = face_mock(tex['eyes_open'], tex['mouth_grin'])
    fc = face_mock(tex['eyes_closed'], tex['mouth_grin'])
    gap = 6
    native = Image.new('RGB', (MW * 2 + gap, MH), BG)
    native.paste(fo, (0, 0))
    native.paste(fc, (MW + gap, 0))
    big = Image.new('RGB', (MW * S * 2 + 24, MH * S), BG)
    big.paste(up(fo, S), (0, 0))
    big.paste(up(fc, S), (MW * S + 24, 0))
    # in-game simulation: creases darkened as the builder does, RGBA16 quantised,
    # box-filtered so the face (64 rows) is 15/20/25 px tall
    states = ORDER[:8]
    sims = []
    for th in (15, 20, 25):
        sz = (round(MW * th / 64), round(MH * th / 64))
        row = [up(rgba16(face_mock(ingame(tex[s]), ingame(tex['mouth_grin']))).resize(sz, Image.BOX), S)
               for s in states]
        sims.append((th, row))
    sim_w = sum(r.width + 12 for r in sims[-1][1])
    W_ = max(big.width, sim_w) + 48
    H_ = (16 + 28 + MH + 24 + 28 + big.height + 24
          + sum(28 + r[0].height + 20 for _, r in sims) + 8)
    pf = Image.new('RGB', (W_, H_), BG)
    d = ImageDraw.Draw(pf)
    y = 16
    d.text((24, y), f'native 1x, {MW}x{MH} each: eyes_open + mouth_grin  |  eyes_closed (blink) + mouth_grin',
           fill=TXT, font=f)
    y += 28
    pf.paste(native, (24, y))
    y += MH + 24
    d.text((24, y), '8x nearest neighbour  (hair, nose and face shape are stand-ins for the geometry)',
           fill=TXT, font=f)
    y += 28
    pf.paste(big, (24, y))
    y += big.height + 24
    for th, row in sims:
        d.text((24, y), f'in-game sim, face {th}px tall (creases darkened, RGBA16 + box filter, shown 8x): '
                        'open half closed left right up down dead', fill=TXT, font=f)
        y += 28
        x = 24
        for r in row:
            pf.paste(r, (x, y))
            x += r.width + 12
        y += row[0].height + 20
    return pf


# =================================================================== CHECKS
def check(tex):
    """Spec checks; raises AssertionError on any violation."""
    with open(SPEC) as fh:
        colors = json.load(fh)['colors']
    assert PAL['.'] == hx(colors['skin']), 'background is not the spec skin colour'
    assert PAL['s'] == hx(colors['skin_shadow']), 'crease is not the spec skin_shadow colour'
    skin = np.array(SKIN, np.uint8)
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
    lid = (ref == PAL['L']).all(-1)
    foot = (ref != skin).any(-1)
    for n in ('eyes_left', 'eyes_right', 'eyes_up', 'eyes_down'):
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['L']).all(-1) == lid).all(), f'{n}: lids differ from eyes_open'
        assert ((b != skin).any(-1) == foot).all(), f'{n}: footprint differs from eyes_open'
    # brows identical in all 8 eye states, and only brows in rows 0..8
    brow = (ref == PAL['B']).all(-1)
    for n in ORDER[:8]:
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['B']).all(-1) == brow).all(), f'{n}: brows differ from eyes_open'
        assert not ((b != skin).any(-1) & ~(b == PAL['B']).all(-1))[:9].any(), f'{n}: eye ink in brow rows'
    # colours: palette only, all distinct after 5-bit (RGBA16) quantising
    cols = set()
    for im in tex.values():
        cols |= set(map(tuple, np.array(im)[..., :3].reshape(-1, 3)))
    assert cols <= set(PAL.values()), 'off-palette colour'
    q = {(r >> 3, g >> 3, b >> 3) for r, g, b in cols}
    assert len(q) == len(cols), 'colours merge in RGBA16'
    return sorted('#%02X%02X%02X' % c for c in cols)


def main():
    tex = build()
    cols = check(tex)
    for name, im in tex.items():
        im.save(os.path.join(OUT, name + '.png'))
    preview_sheet(tex).save(os.path.join(OUT, 'preview_sheet.png'))
    preview_face(tex).save(os.path.join(OUT, 'preview_face.png'))
    print('ok:', len(tex), 'textures;', len(cols), 'colours:', ' '.join(cols))


if __name__ == '__main__':
    main()
