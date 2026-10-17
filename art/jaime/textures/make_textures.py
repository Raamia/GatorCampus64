"""Jaime face textures (Super Gatorlator 64) - FINAL set.

Same conventions as Daniel's set (art/daniel/textures/make_textures.py): 64x32
eye textures holding both eyes, a 32x16 mouth, opaque background of exactly
the spec skin colour (the builder keys it to alpha 0), hand-placed pixels only.

What makes Jaime read as Jaime at a few pixels tall (photos 1 and 3):

  brows (rows 6-9, identical in all 8 eye states)
  * thick, bold, near-black (spec "eyebrows" #241A17, far darker than his
    hair) and almost straight: one solid mass 4 rows thick, a low arch above
    the outer half of the iris (top row 6), a blunt inner head sitting one
    row lower (rows 7-10), the tail tapering to row 9 past the outer eye
    corner.  Steps are at least 2 px wide - 1-px stair steps turned the brow
    into a jagged "lightning bolt" on the 3D head.  Each brow runs x 2..24
    (23 px, about 1.2x the eye width, as in photo 1); 14 px between brows.
  * rows 6-10 so they still render with Daniel's face_layout (the eye material
    only covers head band 1, which starts at texture row 6 there); the fringe
    must end above row 6 at the brow columns (fringe lo_ring 2 does that).
  eyes
  * relaxed, slightly hooded almond eyes (photo 1): flat 2-row upper lash
    (rows 13-14), 4-row opening (rows 15-18), lash wings at both corners,
    skin-shadow lower lid (row 19, his under-eye shadow).  Footprint x 5..23
    / 40..58 like Daniel's (16 px between the eyes); the 3 skin rows between
    brow and lash keep brow and eye separate at in-game size.
  * large near-black brown iris 10x7 with a 4x3 pupil and a 3-px glint (same
    image side in both eyes); the lid hides its top two rows (hooded look),
    white shows at both sides.
  * left/right move the iris 3 px, up/down 2 px; lids and footprint never
    change between the five open-gaze states.
  * half: lash lowered 2 rows, skin-shadow crease where it was.
  * closed: smooth sagging lid arc (rows 16-19), 2 px thick in the middle,
    2-3 px steps, only the outer lash wing rises (risers at both ends read
    as "[___]" brackets on the head).
  * dead: 3-px stroke "X" (rows 12-20) under the unchanged brows.
  mouth (mouth_grin.png, kept as the file name)
  * his lopsided, confident smile from photo 3 (levelled): thin upper lip,
    lips parted on a 2-row band of upper teeth that is widest on the
    image-left side, an open dark mouth corner there, while the image-right
    corner (his left) is closed and turned up 1-2 px into a small skin-shadow
    smile crease - the smirk.  Full pink 2-row lower lip.  Deliberately NOT
    mirror-symmetric (the only asymmetric texture).

Palette: 11 colours, all distinct after RGBA16 (5-bit) quantising.  Run:

    tools/.venv/bin/python -I make_textures.py [out_dir]

Writes eyes_{open,half,closed,left,right,up,down,dead}.png (64x32 RGBA),
mouth_grin.png (32x16 RGBA), preview_sheet.png and preview_face.png next to
this script (or into out_dir), after running the spec checks (raises on any
violation).  verify_textures.py is an independent re-check of the files.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ------------------------------------------------------------------ palette
PAL = {
    '.': hx('DCA588'),   # skin (texture background - exact spec colour)
    's': hx('C48C70'),   # skin shadow (spec): under-eye, lid crease, smile crease
    'B': hx('241A17'),   # eyebrows (spec) - also the knocked-out "X"
    'L': hx('2A1E1C'),   # eyelid / lash line
    'I': hx('3E2820'),   # iris (dark brown)
    'P': hx('120C0C'),   # pupil
    'h': hx('FFFFFF'),   # eye highlight
    'W': hx('F2EEE6'),   # sclera
    'p': hx('C9716C'),   # lips (his pink lips, scaled to the spec skin)
    'm': hx('6E2A2A'),   # mouth interior / corners
    'T': hx('FFFDF2'),   # teeth
}
SKIN = PAL['.']


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# ===================================================================== EYES
# Grids are the LEFT HALF of the texture (absolute columns x = 0..31); the
# right half is the exact mirror x -> 63 - x.  Image-left eye: outer corner on
# the left, inner corner (next to the nose) on the right.
#              x = 0         1         2         3
#                  01234567890123456789012345678901
BROW = {  # identical in every state; one solid 4-row mass, steps >= 2 px wide
    6: ".........BBBBB..................",   # arch peak above the outer half of the iris
    7: "......BBBBBBBBBBBBBBBBBB........",
    8: "....BBBBBBBBBBBBBBBBBBBBB.......",
    9: "..BBBBBBBBBBBBBBBBBBBBBBB.......",   # tail tapers to row 9 past the outer corner
    10: "..............BBBBBBBBBBB.......",  # blunt inner head sits one row lower
}
LIDS = {
    'open': {
        13: "...........LLLLLLLL.............",   # flat, heavy upper lash
        14: "........LLLLLLLLLLLLLL..........",
        15: "......LLLLWWWWWWWWWWLLL.........",
        16: ".....LLWWWWWWWWWWWWWWWLL........",
        17: ".....LWWWWWWWWWWWWWWWWWL........",   # lash wings at both corners
        18: "........WWWWWWWWWWWWWW..........",
        19: ".......sssssssssssssss..........",   # lower lid / under-eye shadow
    },
    'half': {
        13: "...........ssssssss.............",   # crease where the open lash was
        14: ".........ss........ss...........",
        15: "...........LLLLLLLL.............",   # lash lowered 2 rows
        16: ".....LLLLLLLLLLLLLLLLLL.........",
        17: ".....LWWWWWWWWWWWWWWWWWL........",
        18: "........WWWWWWWWWWWWWW..........",
        19: ".......sssssssssssssss..........",
    },
    'closed': {   # smooth sagging arc, 2 px thick in the middle; only the outer wing rises
        16: ".....LL.........................",
        17: ".....LLLLL.........LLLLL........",
        18: "........LLLLLLLLLLLLL...........",
        19: "..........LLLLLLLLL.............",
    },
}
for _rows in [BROW] + list(LIDS.values()):
    for _y, _r in _rows.items():
        assert len(_r) == 32, (_y, _r)

IRIS = [  # 10 x 7 (the two top rows sit under the lash by default)
    "..IIIIII..",
    ".IIIIIIII.",
    "IIIPPPPIII",
    "IIIPPPPIII",
    "IIIPPPPIII",
    ".IIIIIIII.",
    "..IIIIII..",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 10          # left eye: iris columns 10..19, centred on the eye axis x 14.5
IRIS_Y = 13          # rows 13..19 (visible 15..18)
GLINT = [(3, 2), (4, 2), (3, 3)]   # upper-left of the pupil, same image side both eyes
GAZE_X = 3
GAZE_UP = 2
GAZE_DOWN = 2

DEAD_X = [  # 14 x 9, columns 8..21, rows 12..20 (left eye)
    "BBB........BBB",
    ".BBB......BBB.",
    "..BBB....BBB..",
    "...BBB..BBB...",
    ".....BBBB.....",
    "...BBB..BBB...",
    "..BBB....BBB..",
    ".BBB......BBB.",
    "BBB........BBB",
]
DEAD_X0, DEAD_Y0 = 8, 12


def stamp_half(g, rows):
    for y, row in rows.items():
        for x, ch in enumerate(row):
            if ch != '.':
                g[y][x] = ch
                g[y][63 - x] = ch


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    stamp_half(g, BROW)
    if state == 'dead':
        stamp_half(g, {DEAD_Y0 + j: '.' * DEAD_X0 + r + '.' * (32 - DEAD_X0 - len(r))
                       for j, r in enumerate(DEAD_X)})
        return g
    stamp_half(g, LIDS['half' if state == 'half' else 'closed' if state == 'closed' else 'open'])
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
        # glint: keep it on the top visible iris rows so it never vanishes
        top = min(y for _, y in vis)
        dy0 = max(0, top - (oy + min(d for _, d in GLINT)))
        for dx, dy in GLINT:
            x, y = ox + dx, oy + dy + dy0
            if g[y][x] in 'IP':
                g[y][x] = 'h'
    return g


# ==================================================================== MOUTH
# Full 32x16 grid (not mirrored: the smirk is lopsided on purpose).
#        x = 0         1         2         3
#            01234567890123456789012345678901
MOUTH = [
    "................................",  # 0
    "................................",  # 1
    "................................",  # 2
    ".........................ss.....",  # 3  smile crease above the raised corner
    "..........................mm....",  # 4  his left corner turned up (the smirk)
    "......m.ppppppppppppppppmmm.....",  # 5  thin upper lip
    ".....mmmTTTTTTTTTTTTTTTmm.......",  # 6  open dark corner (image left), upper teeth
    "......mmmTTTTTTTTTTTmmmm........",  # 7  teeth band closes toward his left
    ".......ppmmmmmmmmmmmmmp.........",  # 8  bite line (no lower teeth)
    "........pppppppppppppppp........",  # 9  full lower lip
    "..........pppppppppppp..........",  # 10
    "................................",  # 11
    "................................",  # 12
    "................................",  # 13
    "................................",  # 14
    "................................",  # 15
]
assert len(MOUTH) == 16 and all(len(r) == 32 for r in MOUTH)


def mouth_grid():
    return [list(r) for r in MOUTH]


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
HAIR = hx('4A362C')
HAIR_HI = hx('6B4E3E')
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
    d.text((24, 12), 'Jaime face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
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
EYE_Y = 8          # eye texture top row on the mock (brow top -> row 14)
MOUTH_X, MOUTH_Y = 16, 40


def face_mock(eye_im, mouth_im):
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = BG
    cx = (MW - 1) / 2
    yy, xx = np.mgrid[0:MH, 0:MW]
    # face widest at the cheekbones, tapering to a fairly narrow chin
    t = np.where(yy < 34, (yy - 34) / 34.0, (yy - 34) / 30.0)
    half_w = 31.0 * np.sqrt(np.clip(1.0 - t * t, 0.0, 1.0))
    face = np.abs(xx - cx) <= half_w
    a[face] = SKIN

    def paste(im, x0, y0):
        t_ = np.array(im.convert('RGB'))
        h, w = t_.shape[:2]
        reg = a[y0:y0 + h, x0:x0 + w]
        m = face[y0:y0 + h, x0:x0 + w]
        reg[m] = t_[m]

    paste(eye_im, 0, EYE_Y)
    paste(mouth_im, MOUTH_X, MOUTH_Y)
    # nose hint (the nose is geometry): tip shadow + nostrils
    for x, y in [(30, 36), (31, 36), (32, 36), (33, 36), (29, 35), (34, 35)]:
        a[y, x] = SHAD
    # hair: big fluffy cap; messy fringe ending one skin row above the brow
    # arch (brow top = EYE_Y + 6), side hair over the temples
    fb = EYE_Y + 4
    cap = ((xx - cx) / 36.0) ** 2 + ((yy - 20) / 21.0) ** 2 <= 1.0
    hair = cap & (yy <= fb)
    side = cap & (np.abs(xx - cx) >= 28.5) & (yy <= EYE_Y + 22)
    a[hair | side] = HAIR
    # strand tips hanging off the fringe; long wisps at the temples
    for x0, depths in [(2, (2, 3, 2)), (8, (1, 1)), (14, (1,)), (24, (1, 1)), (30, (1,)),
                       (38, (1, 1)), (49, (1,)), (54, (1, 1)), (59, (2, 3, 2))]:
        for i, dpt in enumerate(depths):
            for k in range(1, dpt + 1):
                a[fb + k, x0 + i] = HAIR
    for x, y in [(20, 4), (21, 4), (22, 5), (36, 3), (37, 3), (38, 4), (45, 6), (46, 7),
                 (12, 8), (13, 9)]:
        a[y, x] = HAIR_HI
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
        if name != 'mouth_grin':   # the smirk is deliberately lopsided
            mask = (a[..., :3] != skin).any(-1)
            assert (mask == mask[:, ::-1]).all(), f'{name}: shape not mirror-symmetric'
    eyes = [n for n in ORDER if n != 'mouth_grin']
    # brows: identical pixels in every eye state, rows 6-9 only
    brow = (np.array(tex['eyes_open'])[..., :3] == PAL['B']).all(-1)
    assert set(np.where(brow.any(1))[0]) == {6, 7, 8, 9, 10}, 'brow rows'
    for n in eyes:
        b = np.array(tex[n])[..., :3]
        assert (b[:11] == np.array(tex['eyes_open'])[:11, :, :3]).all(), f'{n}: brows differ'
        assert not (b[11:12] != skin).any(), f'{n}: content in the brow gap row 11'
    # every open-gaze state shares the exact lid pixels and footprint of open
    ref = np.array(tex['eyes_open'])[..., :3]
    lid = (ref == PAL['L']).all(-1)
    foot = (ref != skin).any(-1)
    for n in ('eyes_left', 'eyes_right', 'eyes_up', 'eyes_down'):
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['L']).all(-1) == lid).all(), f'{n}: lids differ from eyes_open'
        assert ((b != skin).any(-1) == foot).all(), f'{n}: footprint differs from eyes_open'
        assert (b == PAL['h']).all(-1).any() and (b == PAL['P']).all(-1).any(), f'{n}: glint/pupil lost'
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
    os.makedirs(OUT, exist_ok=True)
    for name, im in tex.items():
        im.save(os.path.join(OUT, name + '.png'))
    preview_sheet(tex).save(os.path.join(OUT, 'preview_sheet.png'))
    preview_face(tex).save(os.path.join(OUT, 'preview_face.png'))
    print('ok:', len(tex), 'textures;', len(cols), 'colours:', ' '.join(cols))


if __name__ == '__main__':
    main()
