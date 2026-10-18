"""Daniel face textures (GatorCampus 64) - FINAL set.

Built on the "faithful" candidate (its proportions: narrow 16-px eyes with
about one eye-width between them, a wide closed-bite grin, no lower teeth),
with the judges' fixes and the best grafts from "classic" / "expressive":

  eyes (redrawn after the likeness review: narrower and wider apart; second
  pass after the polish review: less "dark bar with three white dots")
  * open: smiling slit - arched 2-px upper lash, the inner corner one row lower
    than the outer one (smile tilt), lower lid = a skin-shadow row (the cheek
    pushing the lid up, as in the first set; no ink outline under the eye).
    15 x 5 texels corner to corner (crease row included), 22 texels between
    the inner corners, left eye x 6-20 / right eye x 43-57 (exact mirror),
    rows 13-17.
  * iris 11x3 with a 3x2 pupil right under the lash (a squinting eye's upper
    lid covers the top of the iris) and a 1-px glint on the pupil's top-left
    texel (same image side in both eyes).  The iris fills the opening except
    one texel of white at the OUTER corner (iris pattern mirrored for the
    right eye), so at game size the eye is a dark slit with a sparkle (how his
    eyes read in photos) and no row of evenly spaced dots.
  * left/right move the iris 2 px, up/down 1 px (a row of white under / over
    the iris), pupil and glint stay visible.  All five open-gaze states share
    exactly the same lid pixels and footprint - only the iris moves.
  * half: the lash drops to the middle row and covers the pupil and glint;
    only a 1-row sliver of iris shows under it, with a skin-shadow lid crease
    above (where the open lash was) - two dark rows instead of four, so the
    blink's middle frame reads.
  * closed: 2-px thick happy "^" arc on the same corners (his laughing
    crescent eyes when he blinks), a short cheek shadow under its middle.
  * dead: bold 9x7 "X" (2-px diagonal strokes meeting in a single 3-px
    crossing row) centred on the eye, rows 12-18.
  mouth
  * lens-shaped grin from photos 1/3/4: flat 1-row upper lip (no centre bump),
    5-row upper-teeth band whose lower edge follows the smile curve, chunky
    dark mouth corners level with the teeth and turned up 1 px, a 1-row dark
    bite line (no lower teeth, no tongue), a wide 2-row lower lip on plain
    skin (no chin shadow - lips and skin shadow would merge in RGBA16), no
    tooth-notch shade.

Every pixel comes from the ASCII grids / tables below - no antialiasing, no
gradients, no photo pixels.  Palette: the brief's colours only (11 of 12;
tongue unused).  Run:

    tools/.venv/bin/python -I make_textures.py

Writes next to this script: eyes_{open,half,closed,left,right,up,down,dead}.png
(64x32 RGBA), mouth_grin.png (32x16 RGBA), preview_sheet.png and
preview_face.png, then runs the spec checks (raises on any violation).
verify_textures.py is an independent re-check of the written files.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ------------------------------------------------------------------ palette
PAL = {
    '.': hx('D99C7E'),   # skin (texture background - exact)
    's': hx('C4876B'),   # skin shadow
    'H': hx('1E1A20'),   # hair / darkest line
    'L': hx('2A1E1C'),   # eyelid / lash line
    'I': hx('3A2620'),   # iris
    'P': hx('120C0C'),   # pupil
    'h': hx('FFFFFF'),   # eye highlight
    'W': hx('F2EEE6'),   # sclera
    'p': hx('C27766'),   # lips
    'm': hx('6E2A2A'),   # mouth interior
    'T': hx('FFFDF2'),   # teeth
}
SKIN = PAL['.']


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# ===================================================================== EYES
# The LEFT eye (image-left) is drawn as ASCII in a window of texture columns
# x = EX0 .. EX0+14 and rows y = EY0 .. EY0+4.  Outer corner on the left,
# inner corner (next to the nose) on the right.  The right eye is the exact
# mirror x -> 63 - x.  'W' marks the eye opening (sclera; the iris is stamped
# into it), 'L' lash / lid ink, 's' skin shadow, 'H' darkest ink.
# Likeness review (photos 1-4): his eyes are narrow smiling slits set wide apart,
# about 15 x 5 texels with ~22 texels between the inner corners and almost no white
# showing (the first set was 19 x 7 with a 16-texel gap).  Left eye x 6-20, right
# eye x 43-57, gap x 21-42 (22 texels), rows 13-17.
EX0, EY0 = 6, 13
EW = 15
#            x = 6        2
#                678901234567890
LIDS = {
    'open': [
        "...LLLLLLLLL...",   # 13  arched upper lash (2 thick at the top)
        ".LLLWWWWWWWLLL.",   # 14  lash corners; the pupil sits right under the lash
        "LLWWWWWWWWWWWL.",   # 15  outer corner
        ".LWWWWWWWWWWWLL",   # 16  inner corner one row lower (smile tilt)
        "..sssssssssss..",   # 17  lower lid: the cheek pushing it up (skin shadow)
    ],
    'half': [
        "...............",   # 13
        "...sssssssss...",   # 14  lid crease where the open lash was
        "LLLLLLLLLLLLLL.",   # 15  lash lowered to the middle row (covers pupil + glint)
        ".LWWWWWWWWWWWLL",   # 16  a 1-row sliver of iris
        "..sssssssssss..",   # 17  lower lid, as open
    ],
    'closed': [
        "....LLLLLLL....",   # 13  happy "^" arc, 2 px thick, on the open eye's corners
        "..LLL.....LLL..",   # 14
        "LLL.........LL.",   # 15
        ".L...........LL",   # 16
        "....sssssss....",   # 17  short cheek shadow under the arc's middle
    ],
}

IRIS = [  # 11 x 3 (left eye; mirrored for the right eye): pupil up under the lash,
    "..IIPPPII..",   # the opening filled except one texel of white at the outer
    ".IIIPPPIIII",   # corner (middle row)
    "IIIIIIIIIII",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 8           # left eye: iris columns 8..18, centred on the opening 8..18
IRIS_Y = 14          # rows 14..16
GAZE_X = 2        # left/right: 3 texels of white on the far side, iris under the lid
GAZE_UP = 1       # up: a row of white under the iris
GAZE_DOWN = 1     # down: a row of white over the iris

DEAD_X = [  # 9 x 7 knocked-out X, columns 9..17, rows 12..18 (left eye)
    "HH.....HH",
    ".HH...HH.",
    "..HH.HH..",
    "...HHH...",
    "..HH.HH..",
    ".HH...HH.",
    "HH.....HH",
]
DEAD_X0, DEAD_Y0 = 9, 12


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
        assert len(row) == EW, (state, j)
        for i, ch in enumerate(row):
            g[EY0 + j][EX0 + i] = ch
            g[EY0 + j][63 - (EX0 + i)] = ch
    if state == 'closed':
        return g
    for side in 'LR':
        # the iris pattern is mirrored for the right eye (the white sits at the outer
        # corner of both eyes); a gaze moves both irises the same way
        iris = IRIS if side == 'L' else [r[::-1] for r in IRIS]
        ox = IRIS_X if side == 'L' else 63 - IRIS_X - (IW - 1)
        ox += gaze[0]
        oy = IRIS_Y + gaze[1]
        pupil = []
        for j, row in enumerate(iris):
            for i, ch in enumerate(row):
                x, y = ox + i, oy + j
                if ch != '.' and g[y][x] == 'W' and ((x < 32) == (side == 'L')):
                    g[y][x] = ch
                    if ch == 'P':
                        pupil.append((x, y))
        # glint: the top-left texel of the pupil's visible part (same image side in
        # both eyes); none when the lid covers the pupil (half)
        if pupil:
            top = min(y for _, y in pupil)
            g[top][min(x for x, y in pupil if y == top)] = 'h'
    return g


# ==================================================================== MOUTH
# Left half (x = 0..15) of the 32x16 grin; the right half is its mirror.
#   m dark mouth corners / bite line   T upper teeth   p lips
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    "................",  # 2
    ".m.ppppppppppppp",  # 3  flat thin upper lip; corner tip turns up 1 px
    ".mmmTTTTTTTTTTTT",  # 4  chunky dark corner, big upper teeth
    ".mmmTTTTTTTTTTTT",  # 5
    "..mmmTTTTTTTTTTT",  # 6
    "....mmmTTTTTTTTT",  # 7
    "......mmmTTTTTTT",  # 8  teeth: 5 rows in the middle, edge follows the smile
    ".....ppmmmmmmmmm",  # 9  thin dark bite line (closed bite, no lower teeth)
    ".....ppppppppppp",  # 10 full lower lip
    "........pppppppp",  # 11
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
HAIR = PAL['H']
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
    d.text((24, 12), 'Daniel face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
           fill=TXT, font=f)
    for i, name in enumerate(ORDER):
        x, y = 24 + (i % cols) * cw, 48 + (i // cols) * ch
        im = tex[name]
        d.text((x, y), f'{name}.png  ({im.width}x{im.height})', fill=TXT, font=f)
        sheet.paste(up(im, S).convert('RGB'), (x, y + 28))
    return sheet


# Face mock, 64x64, 1 texel = 1 px (same density the textures are drawn at).
# Hair, nose and face outline are rough stand-ins for the real geometry.
MW = MH = 64
EYE_Y = 8          # eye texture top row on the mock (lash top -> row 20)
MOUTH_X, MOUTH_Y = 16, 40


def face_mock(eye_im, mouth_im):
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = BG
    cx = (MW - 1) / 2
    yy, xx = np.mgrid[0:MH, 0:MW]
    # broad face, widest at the cheekbones (row 34), jaw tapering to a
    # rounded, fairly broad chin
    t = np.where(yy < 34, (yy - 34) / 34.0, (yy - 34) / 31.0)
    half_w = 32.0 * np.sqrt(np.clip(1.0 - t * t, 0.0, 1.0))
    face = np.abs(xx - cx) <= half_w
    a[face] = SKIN

    def paste(im, x0, y0):
        t = np.array(im.convert('RGB'))
        h, w = t.shape[:2]
        reg = a[y0:y0 + h, x0:x0 + w]
        m = face[y0:y0 + h, x0:x0 + w]
        reg[m] = t[m]

    paste(eye_im, 0, EYE_Y)
    paste(mouth_im, MOUTH_X, MOUTH_Y)
    # nose hint (the nose is geometry): tip shadow + nostrils
    for x, y in [(30, 36), (31, 36), (32, 36), (33, 36), (29, 35), (34, 35)]:
        a[y, x] = SHAD
    # hair: rounded cap, heavy straight fringe ending one skin row above the
    # lashes, blocky strand tips, side locks over the temples
    fb = EYE_Y + 10                       # fringe bottom row (lash top = EYE_Y+13)
    cap = ((xx - cx) / 34.0) ** 2 + ((yy - 22) / 23.0) ** 2 <= 1.0
    hair = cap & (yy <= fb)
    # side locks over the temples / ears, longest at the outer edge
    side = cap & (np.abs(xx - cx) >= 29.5) & (yy <= EYE_Y + 20 + (np.abs(xx - cx) - 29.5) * 2)
    a[hair | side] = HAIR
    # chunky strand points hanging below the fringe line; none directly over
    # the lash peaks, so the lids keep a skin gap under the hair
    for x0, depths in [(1, (2, 2, 1)), (6, (1,)), (22, (1, 1)), (25, (1, 2, 2, 1)),
                       (31, (1, 1)), (35, (1, 2, 2, 1)), (40, (1, 1)), (57, (1,)),
                       (60, (1, 2, 2))]:
        for i, dpt in enumerate(depths):
            for k in range(1, dpt + 1):
                a[fb + k, x0 + i] = HAIR
    return Image.fromarray(a, 'RGB')


def rgba16(im):
    a = np.array(im.convert('RGB')).astype(np.int32) >> 3
    return Image.fromarray(((a << 3) | (a >> 2)).astype(np.uint8), 'RGB')


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
    # in-game simulation: RGBA16 quantised, box-filtered to 15/20/25 px tall
    states = ORDER[:8]
    sims = []
    for th in (15, 20, 25):
        row = [up(rgba16(face_mock(tex[s], tex['mouth_grin'])).resize((th, th), Image.BOX), S)
               for s in states]
        sims.append((th, row))
    sim_w = sum(r.width + 12 for r in sims[-1][1])
    W_ = max(big.width, sim_w) + 48
    H_ = (16 + 28 + MH + 24 + 28 + big.height + 24
          + sum(28 + r[0].height + 20 for _, r in sims) + 8)
    pf = Image.new('RGB', (W_, H_), BG)
    d = ImageDraw.Draw(pf)
    y = 16
    d.text((24, y), 'native 1x, 64x64 each: eyes_open + mouth_grin  |  eyes_closed (blink) + mouth_grin',
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
        d.text((24, y), f'in-game sim, face {th}px tall (RGBA16 + box filter, shown 8x): '
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
    # colours: brief palette only, all distinct after 5-bit (RGBA16) quantising
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
