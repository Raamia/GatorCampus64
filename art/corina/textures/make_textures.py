"""Corina face textures (GatorCampus 64) - FINAL set.

Same conventions as Daniel's approved set (art/daniel/textures/): 64x32 eye
states + 32x16 mouth, flat skin background (keyed to alpha 0 by the builder),
ASCII-grid pixel art, mirrored left/right, small RGBA16-safe palette, eye
placement identical across states.  Drawn from her photos
(reference/friends/corina/ - photo1 portrait, photo3/4 smiles):

  brows (rows 6-9, IDENTICAL in all 8 states so they never flicker on a blink)
  * full dark brows with a soft arch: 2-px body, peak over the iris, full head
    over the inner eye corner, thin tail dropping out past the outer corner.
    Same 18-px span as the eye (x 6-23 / 40-57).  Drawn in the spec hair colour.
    Her curly bangs reach the brows: the brows show when the fringe edge stays
    at or above texture row 5 (2 skin rows of forehead); a lower fringe simply
    hides them.
  eyes (rows 12-19, exactly centred like Daniel's)
  * open: smiling almond - 2-px upper lash line arched to a peak over the iris,
    level corners (no cat-eye tilt), lower lid pushed up flat by the cheek with
    a skin-shadow crease under it.  Her "defined lashes": two short 2-px lashes
    at the outer corner, one straight up and one flicking out (no long eyeliner
    wing - it read as make-up in the first draft).  Every stroke is edge-connected:
    corner-only (diagonal) texels render as detached specks in game.  Opening 16 px (x 7-22),
    5 rows; eye block x 5-23 / 40-58 (corners x 6 / 23), 16 px between the eyes.
  * iris 10x7, very dark brown with a near-black 4x3 pupil and a 2x2 white
    catchlight (the strong studio catchlights of photo1), same image side in both
    eyes; it fills the opening top to bottom, so at game size the eye reads as a
    dark crescent with small white corner wedges - how her smiling eyes read in
    every photo.  left/right/up shift the iris 3 px, down 2 px; all five gaze
    states share exactly the same lid pixels and footprint.
  * half: lash line (with its ticks) lowered 2 rows, skin-shadow crease where it
    was.  closed: 2-px happy arc on the same corners, two lashes hanging down at
    the outer end.  dead: Daniel's 14x9 "X" (3-px strokes, single 4-px crossing)
    in lash ink, rows 12-20, under the unchanged brows.
  mouth (mouth_grin.png)
  * her big bright smile: thin flat rose upper lip whose corner tips turn up,
    5-row upper-teeth band whose lower edge follows the smile curve, dark mouth
    corners, 1-row dark bite line (lower teeth dropped: as a grey band they read
    as a stripe at game size), and a fuller 3-row rose lower lip (rosier than
    Daniel's - her lips are clearly pink-red against the skin in all photos).
    The mouth uses the full 30 usable texels: her smile is wider than the
    distance between her pupils.

Every pixel comes from the ASCII grids / tables below - no antialiasing, no
gradients, no photo pixels.  Palette: 11 colours, spec skin / skin_shadow / hair
exact, all distinct after RGBA16 quantising.  Run:

    tools/.venv/bin/python -I make_textures.py [OUT_DIR]

Writes (next to this script unless OUT_DIR is given) eyes_{open,half,closed,
left,right,up,down,dead}.png (64x32 RGBA), mouth_grin.png (32x16 RGBA),
preview_sheet.png and preview_face.png, then runs the spec checks (raises on any
violation).  verify_textures.py is an independent re-check of the written files.
"""
import json
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ------------------------------------------------------------------ palette
# spec colours are read from art/corina/character.json, so the brows follow the
# spec hair colour when it changes (it was darkened to #17110F in review round 2)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'character.json')) as _fh:
    SPEC = json.load(_fh)['colors']

PAL = {
    '.': hx(SPEC['skin']),          # skin (texture background, exact)
    's': hx(SPEC['skin_shadow']),   # skin shadow - creases
    'B': hx(SPEC['hair']),          # eyebrows (spec colors.hair)
    'L': hx('1A1012'),   # lash / lid line, dead-X ink (darkest)
    'I': hx('3A2219'),   # iris (very dark brown)
    'P': hx('0E0809'),   # pupil
    'h': hx('FFFFFF'),   # catchlight
    'W': hx('F2EEE6'),   # sclera
    'p': hx('C8646A'),   # lips (rose)
    'm': hx('6E2A2A'),   # mouth corners / bite line
    'T': hx('FFFDF2'),   # teeth
}
SKIN = PAL['.']


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# ===================================================================== EYES
# The LEFT eye (image-left) is drawn as ASCII in a window of texture columns
# x = EX0 .. EX0+23.  Outer corner on the left, inner corner (next to the nose)
# on the right.  The right eye is the exact mirror x -> 63 - x.
#   'W' eye opening (sclera; the iris is stamped into it)  'L' lash / lid ink
#   's' skin shadow  'B' brow
EX0 = 4
BROW_Y0 = 6
#          x = 4         1         2
#              4567890123456789012345678
BROW = [
    ".....BBBBBBBBBB.........",   # 6  arch, peak over the iris
    "...BBBBBBBBBBBBBBBBB....",   # 7
    "..BBB.........BBBBBB....",   # 8  full head over the inner corner
    "..BB....................",   # 9  tail drops out past the outer corner
]
EY0 = 10
LIDS = {
    'open': [
        "........................",   # 10
        "........................",   # 11
        "...L....LLLLLL..........",   # 12  lash 1 (2 px, straight up) + lash peak
        "...L..LLLLLLLLLL........",   # 13
        "...LLLLLWWWWWWLLLL......",   # 14
        ".LLLLLWWWWWWWWWWLLL.....",   # 15  lash 2: 2-px flick out of the corner
        "...LWWWWWWWWWWWWWWL.....",   # 16
        "..LWWWWWWWWWWWWWWWWL....",   # 17  corners level (outer point x 6, inner x 23)
        "...LWWWWWWWWWWWWWWWL....",   # 18  flat lower lid pushed up by the cheek
        ".....ssssssssssssss.....",   # 19  cheek crease
        "........................",   # 20
        "........................",   # 21
    ],
    'half': [
        "........................",   # 10
        "........................",   # 11
        "........ssssss..........",   # 12  crease where the open lash was
        "......ss......ss........",   # 13
        "...L....LLLLLL..........",   # 14  lash line + lashes lowered 2 rows
        "...L..LLLLLLLLLL........",   # 15
        "...LLLLLWWWWWWLLLL......",   # 16
        ".LLLLLWWWWWWWWWWLLLL....",   # 17
        "...LWWWWWWWWWWWWWWWL....",   # 18
        ".....ssssssssssssss.....",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'closed': [
        "........................",   # 10
        "........................",   # 11
        "........................",   # 12
        "........................",   # 13
        ".......LLLLLLLL.........",   # 14  happy arc, 2 px thick
        ".....LLLLLLLLLLLL.......",   # 15
        "...LLLL........LLLL.....",   # 16
        "..LLL............LLL....",   # 17  same corners as open
        ".LLL..............LL....",   # 18
        ".L.L.ssssssssssssss.....",   # 19  two lashes hanging at the outer end
        "........................",   # 20
        "........................",   # 21
    ],
}

IRIS = [  # 10 x 7 (top and bottom rows sit under the lids by default)
    "..IIIIII..",
    ".IIIIIIII.",
    "IIIPPPPIII",
    "IIIPPPPIII",
    "IIIPPPPIII",
    "IIIIIIIIII",
    ".IIIIIIII.",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 10          # left eye: iris columns 10..19, centred on the opening 7..22
IRIS_Y = 13          # rows 13..19
GLINT = [(3, 2), (4, 2), (3, 3), (4, 3)]   # 2x2 catchlight, upper-left of the pupil
GAZE_X = 3
GAZE_UP = 3       # up: 2 rows of white under the iris, catchlight stays
GAZE_DOWN = 2     # down: a row of white over the iris (3 would read as an eye roll)

DEAD_X = [  # 14 x 9 knocked-out X, columns 8..21, rows 12..20 (left eye)
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
DEAD_X0, DEAD_Y0 = 8, 12


def stamp(g, tpl, x0, y0):
    for j, row in enumerate(tpl):
        assert len(row) == 24, (j, row)
        for i, ch in enumerate(row):
            if ch != '.':
                g[y0 + j][x0 + i] = ch
                g[y0 + j][63 - (x0 + i)] = ch


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    stamp(g, BROW, EX0, BROW_Y0)
    if state == 'dead':
        for j, row in enumerate(DEAD_X):
            for i, ch in enumerate(row):
                if ch != '.':
                    g[DEAD_Y0 + j][DEAD_X0 + i] = ch
                    g[DEAD_Y0 + j][63 - (DEAD_X0 + i)] = ch
        return g
    stamp(g, LIDS[state if state in ('half', 'closed') else 'open'], EX0, EY0)
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
        # catchlight: keep it on the top visible iris rows so it never vanishes
        top = min(y for _, y in vis)
        dy0 = max(0, top - (oy + min(d for _, d in GLINT)))
        for dx, dy in GLINT:
            x, y = ox + dx, oy + dy + dy0
            if g[y][x] in 'IP':
                g[y][x] = 'h'
    return g


# ==================================================================== MOUTH
# Left half (x = 0..15) of the 32x16 smile; the right half is its mirror.
#   m dark mouth corners / bite line   T upper teeth   p lips
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    "................",  # 2
    ".m.ppppppppppppp",  # 3  thin flat upper lip; corner tip turns up 1 px
    ".mmmTTTTTTTTTTTT",  # 4  dark corner, big upper teeth
    ".mmmTTTTTTTTTTTT",  # 5
    "..mmmTTTTTTTTTTT",  # 6
    "...mmmTTTTTTTTTT",  # 7
    ".....mmmTTTTTTTT",  # 8  teeth: 5 rows in the middle, edge follows the smile
    "......pmmmmmmmmm",  # 9  dark bite line
    "......pppppppppp",  # 10 full rose lower lip, 3 rows in the middle
    "........pppppppp",  # 11
    "...........ppppp",  # 12
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
HAIR = hx(SPEC['hair'])         # spec colors.hair
TIPS = hx(SPEC['hair_tips'])    # spec colors.hair_tips (caramel curl ends)
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
    d.text((24, 12), 'Corina face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
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
    # broad forehead (the head is squarish from the front, so the brow tails stay
    # on the face), full cheeks, softly rounded chin
    t = np.where(yy < 33, (yy - 33) / 33.0, (yy - 33) / 30.0)
    half_w = np.where(yy < 33, 29.0 * np.cbrt(np.clip(1.0 - np.abs(t) ** 3, 0.0, 1.0)),
                      29.0 * np.sqrt(np.clip(1.0 - t * t, 0.0, 1.0)))
    face = np.abs(xx - cx) <= half_w
    a[face] = SKIN

    def paste(im, x0, y0):
        tt = np.array(im.convert('RGB'))
        h, w = tt.shape[:2]
        reg = a[y0:y0 + h, x0:x0 + w]
        m = face[y0:y0 + h, x0:x0 + w]
        reg[m] = tt[m]

    paste(eye_im, 0, EYE_Y)
    paste(mouth_im, MOUTH_X, MOUTH_Y)
    # nose hint (the nose is geometry): tip shadow + nostrils
    for x, y in [(30, 36), (31, 36), (32, 36), (33, 36), (29, 35), (34, 35)]:
        a[y, x] = SHAD
    # hair: rounded crown, curly bangs whose curl tips stop two skin rows above
    # the brows (eye texture row 3), long curly side curtains that frame the face
    # beside the outer eye corners and fall past the chin, caramel curl ends
    crown = ((xx - cx) / 34.0) ** 2 + ((yy - 21) / 22.0) ** 2 <= 1.0
    fb = EYE_Y + 1                                    # bang base (texture row 1)
    hair = crown & (yy <= fb)
    for k, x0 in enumerate(range(1, MW, 5)):          # curl tips, alternating depth
        r = 2.6 if k % 2 else 2.2
        hair |= crown & (((xx - x0) ** 2 + (yy - (fb + (1.2 if k % 2 else 0.6))) ** 2) <= r * r)
    d = np.abs(xx - cx)
    inner = np.where(yy < EYE_Y + 22, 26.8, 26.8 - (yy - (EYE_Y + 22)) * 0.25)
    inner = inner - 0.9 * ((yy // 3) % 2)             # stacked curls on the inner edge
    hair |= (yy >= fb) & (d >= inner)
    a[hair] = HAIR
    ends = hair & (yy >= 50) & (d >= 24) & ((((xx + 1) // 2 + yy // 2) % 3) == 0)
    a[ends] = TIPS
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
    # every inked texel touches another inked texel edge-on: texels linked only
    # at a corner are filtered into detached specks in game (seen in the 3D
    # preview of the first draft: diagonal lash ticks and the brow tail)
    for name, im in tex.items():
        m = (np.array(im)[..., :3] != skin).any(-1)
        p = np.pad(m, 1)
        nb = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        assert not (m & ~nb).any(), f'{name}: isolated / corner-only texels {np.argwhere(m & ~nb).tolist()}'
    # brows: identical pixels in all 8 eye states, nothing else above row 12
    ref = np.array(tex['eyes_open'])[..., :3]
    brow = (ref == PAL['B']).all(-1)
    assert brow.any() and not brow[10:].any(), 'brows missing or below row 9'
    for n in ORDER[:8]:
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['B']).all(-1) == brow).all(), f'{n}: brows differ from eyes_open'
        foot = (b != skin).any(-1)
        assert not (foot[:12] & ~brow[:12]).any(), f'{n}: eye content above row 12 (fringe zone)'
    # every open-gaze state shares the exact lid pixels and footprint of open
    lid = (ref == PAL['L']).all(-1)
    foot = (ref != skin).any(-1)
    for n in ('eyes_left', 'eyes_right', 'eyes_up', 'eyes_down'):
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['L']).all(-1) == lid).all(), f'{n}: lids differ from eyes_open'
        assert ((b != skin).any(-1) == foot).all(), f'{n}: footprint differs from eyes_open'
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
