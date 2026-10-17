"""Raami face textures (Super Gatorlator 64) - FINAL set.

Same conventions as Daniel's approved set (art/daniel/textures/): every pixel
comes from the ASCII grids / tables below - no antialiasing, no gradients, no
photo pixels; the background is the exact, opaque spec skin colour (the
builder keys it to alpha 0); left/right halves are mirror shapes; the eyes sit
on the same axes (x 14.5 / 48.5, footprint x 5..23 / 40..58) in every state,
about one eye-width apart (16-px gap, like Daniel).

Likeness (photo 2 = face reference, photos 3/4 for the open-eye look):
  brows (rows 5-8, x 2..23 / 40..61, drawn in EVERY state incl. dead, in the
    spec eyebrow colour so they never merge with the lash ink): thick, dark,
    nearly straight - a low hump over the iris, straight lower edge, the inner
    end blunt (3 rows), the middle 4 rows, the outer end tapering down-out a
    little past the eye corner.  Two skin rows (9) + the lid crease (10)
    separate them from the lash.  The curls should end at or just above row 5.
  eyes: big open almond (not Daniel's squint): flat, calm 2-row upper lash
    (rows 11-12, no surprised arch) that gets heavier toward the outer corner
    and closes it (no detached eyeliner flick), opening rows 13-18 / x 7..22,
    lower lid rising to both corners, under-eye shadow row 19, upper-lid crease
    row 10 (his deep-set lids; skin_shadow, which the builder darkens).
    Big, nearly black-brown 12x10 iris (review round 2: photos 2/4 show large,
    very dark, heavy-lidded eyes with little white) with a 4x4 pupil and a 3-px
    glint; the lash hides its top two rows and the lower lid its bottom one, so
    it fills the opening from lid to lid and leaves only small whites on BOTH
    sides (2 px at the widest row).  Sclera a touch greyer than Daniel's,
    because unlit whites pop on a shaded face.
    left/right move the iris 3 px, up 2, down 2; all five open-gaze states
    share exactly the same lid pixels and footprint - only the iris moves.
    half: lash lowered 2 rows onto the iris, same crease and corners.
    closed: relaxed "u" lid line on the same corners (calm blink, not a grin).
    dead: 13x9 "X" (3-px strokes), rows 11-19, under the unchanged brows.
  mouth (file name mouth_grin.png is the engine slot; the expression is his
    calm closed-mouth smile, no teeth): thin darker upper lip with a small
    cupid's bow and philtrum dip, a 2-row faint mustache shadow above it
    (review round 2: the 1-row version vanished in every render): a darker
    'M' row hugging the upper lip at the sides and a skin_shadow row above
    it with a lighter philtrum gap in the middle (dithered bands read as
    stubble dots), a dark lip line whose corners sit 1 px up (the slight
    smile), a fuller pinker lower lip and a short shadow under it.
    Content x 3..28, rows 5-12.

Palette: 12 colours, distinct after RGBA16 quantising (checked below).  Run:

    tools/.venv/bin/python -I make_textures.py

Writes next to this script: eyes_{open,half,closed,left,right,up,down,dead}.png
(64x32 RGBA), mouth_grin.png (32x16 RGBA), preview_sheet.png and
preview_face.png (the face mock shows skin_shadow as the builder ships it,
0.70 x skin), then runs the spec checks (raises on any violation).
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
    '.': hx('D8A07E'),   # skin (spec colors.skin; texture background - exact)
    's': hx('C08766'),   # skin shadow (spec colors.skin_shadow; builder darkens it to 0.70 x skin)
    'B': hx('2A1D1B'),   # eyebrows (spec colors.eyebrows)
    'L': hx('1B171A'),   # lash / lid ink, dead X (spec colors.hair)
    'I': hx('36211A'),   # iris: very dark brown (photos 2/4: nearly black-brown)
    'M': hx('8A6450'),   # mustache shadow next to the upper lip (not the crease colour,
                         #   so the builder ships it as drawn, a little darker than a crease)
    'P': hx('140D0E'),   # pupil
    'h': hx('FFFFFF'),   # eye highlight
    'W': hx('E9E3DA'),   # sclera (a touch below Daniel's: unlit whites pop)
    'u': hx('AA695B'),   # upper lip (darker, in shadow)
    'p': hx('C07D6F'),   # lower lip (fuller, pinker)
    'm': hx('6B3132'),   # lip line / mouth corners
}
SKIN = PAL['.']


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# ===================================================================== EYES
# The LEFT eye (image-left) is drawn as ASCII in a window of texture columns
# x = EX0 .. EX0+23 and rows y = EY0 .. EY0+len-1.  Outer corner on the left,
# inner corner (next to the nose) on the right.  The right eye is the exact
# mirror x -> 63 - x.  'W' marks the eye opening (sclera; the iris is stamped
# into it), 'L' lash / lid ink, 's' skin shadow.
EX0, EY0 = 3, 10
#              x = 3 ...................... 26
LIDS = {
    'open': [
        ".......ssssssssss.......",   # 10  upper-lid crease (his deep-set lids)
        ".......LLLLLLLLLL.......",   # 11  lash top: flat, calm (no surprised arch)
        ".....LLLLLLLLLLLLLL.....",   # 12
        "...LLLLWWWWWWWWWWLLL....",   # 13  heavier ink toward the outer corner
        "..LLLWWWWWWWWWWWWWWLL...",   # 14
        "..LLWWWWWWWWWWWWWWWWL...",   # 15  widest row of the opening (x 7..22)
        "...LLWWWWWWWWWWWWWWWs...",   # 16  outer corner closed by the lash
        ".....sWWWWWWWWWWWWs.....",   # 17  almond: the lower lid rises to both corners
        "......ssWWWWWWWWss......",   # 18
        "........ssssssss........",   # 19  under-eye shadow
        "........................",   # 20
        "........................",   # 21
    ],
    'half': [
        ".......ssssssssss.......",   # 10  same lid crease as open (no jump while blinking)
        "........................",   # 11
        "........................",   # 12
        "...LLLLLLLLLLLLLLLLL....",   # 13  lash lowered 2 rows
        "..LLLLLLLLLLLLLLLLLLL...",   # 14
        "..LLWWWWWWWWWWWWWWWWL...",   # 15
        "...LLWWWWWWWWWWWWWWWs...",   # 16
        ".....sWWWWWWWWWWWWs.....",   # 17
        "......ssWWWWWWWWss......",   # 18
        "........ssssssss........",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'closed': [
        ".......ssssssssss.......",   # 10  same lid crease as open
        "........................",   # 11
        "........................",   # 12
        "........................",   # 13
        "........................",   # 14
        "..LLL..............LL...",   # 15  same outer/inner corners as open
        "...LLLL..........LLLL...",   # 16  relaxed closed lid: gentle "u" arc
        ".....LLLLLLLLLLLLLL.....",   # 17
        ".......LLLLLLLLLL.......",   # 18
        "........ssssssss........",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
}

IRIS = [  # 12 x 10: big and very dark, it fills the opening from lash to lower lid
    "...IIIIII...",
    "..IIIIIIII..",
    ".IIIIIIIIII.",
    "IIIIPPPPIIII",
    "IIIIPPPPIIII",
    "IIIIPPPPIIII",
    "IIIIPPPPIIII",
    ".IIIIIIIIII.",
    "..IIIIIIII..",
    "...IIIIII...",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 9           # left eye: iris columns 9..20, centred on the opening 7..22 (x 14.5)
IRIS_Y = 11          # rows 11..20 (top two rows under the lash, bottom under the lower lid)
GLINT = [(4, 3), (5, 3), (4, 4)]   # upper-left of the pupil, same side both eyes
GAZE_X = 3
GAZE_UP = 2
GAZE_DOWN = 2

DEAD_X = [  # 13 x 9 knocked-out X (left eye)
    "LLL.......LLL",
    ".LLL.....LLL.",
    "..LLL...LLL..",
    "...LLL.LLL...",
    ".....LLL.....",
    "...LLL.LLL...",
    "..LLL...LLL..",
    ".LLL.....LLL.",
    "LLL.......LLL",
]
DEAD_X0, DEAD_Y0 = 8, 11

# brows: drawn in every state, LEFT brow (image-left), mirrored for the right
BX0, BY0 = 1, 5
#              x = 1 ...................... 24
BROW = [
    ".......BBBBBBBBBB.......",   # 5  low hump over the iris
    "....BBBBBBBBBBBBBBBBBBB.",   # 6  inner end blunt, 3 rows
    "..BBBBBBBBBBBBBBBBBBBBB.",   # 7
    ".BBBBBBBBBBBBBBBBBBBBB..",   # 8  straight lower edge; outer end tapers down-out
]


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    for j, row in enumerate(BROW):
        assert len(row) == 24, ('brow', j)
        for i, ch in enumerate(row):
            if ch != '.':
                g[BY0 + j][BX0 + i] = ch
                g[BY0 + j][63 - (BX0 + i)] = ch
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
            if ch != '.':
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
        # glint: keep it on the top visible iris row so it never vanishes
        top = min(y for _, y in vis)
        dy0 = max(0, top - (oy + min(d for _, d in GLINT)))
        for dx, dy in GLINT:
            x, y = ox + dx, oy + dy + dy0
            if g[y][x] in 'IP':
                g[y][x] = 'h'
    return g


# ==================================================================== MOUTH
# Left half (x = 0..15) of the 32x16 mouth; the right half is its mirror.
#   m lip line / corners   u upper lip   p lower lip   s skin shadow
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    "................",  # 2
    "................",  # 3
    "................",  # 4
    ".....ssssssssss.",  # 5  faint mustache shadow, upper row (a crease colour: the builder
                         #    darkens it to 0.70 x skin), lighter philtrum in the middle
    "....MMMMMuuuuuss",  # 6  darker row hugging the upper lip at the sides, cupid's
                         #    bow peaks, philtrum dip in the middle
    "...muuuuuuuuuuuu",  # 7  thin upper lip; the corner sits 1 px up (slight smile)
    "....mmmmmmmmmmmm",  # 8  lip line
    ".....ppppppppppp",  # 9  full lower lip
    "......pppppppppp",  # 10
    "........pppppppp",  # 11
    "..........ssssss",  # 12 shadow under the lower lip
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
HAIR = hx('1B171A')       # spec colors.hair
HAIR_HI = hx('3B3136')    # stand-in curl highlight (preview only)
SHAD = PAL['s']
CREASE_REL = 0.70         # sgl_textures.CREASE_REL: the builder darkens skin_shadow texels


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
    d.text((24, 12), 'Raami face textures   (8x nearest neighbour, 1 block = 1 texel)',
           fill=TXT, font=f)
    for i, name in enumerate(ORDER):
        x, y = 24 + (i % cols) * cw, 48 + (i // cols) * ch
        im = tex[name]
        d.text((x, y), f'{name}.png  ({im.width}x{im.height})', fill=TXT, font=f)
        sheet.paste(up(im, S).convert('RGB'), (x, y + 28))
    return sheet


def game_colours(im):
    """What the builder ships: skin_shadow texels darkened to CREASE_REL x skin."""
    a = np.array(im.convert('RGB'))
    hit = (a == np.array(SHAD, np.uint8)).all(-1)
    a[hit] = np.round(np.array(SKIN, np.float32) * CREASE_REL).astype(np.uint8)
    return Image.fromarray(a, 'RGB')


# Face mock: 64x64 face (1 texel = 1 px, the density the textures are drawn at)
# on a wider canvas so the curls can stand out past the head.  Hair, nose and
# face outline are rough stand-ins for the real geometry.
PADX, PADY = 14, 14
FW = FH = 64
MW, MH = FW + 2 * PADX, FH + PADY + 2
EYE_Y = 8          # eye texture top row on the face (brow top -> face row 13)
MOUTH_X, MOUTH_Y = 16, 38


def face_mock(eye_im, mouth_im, game=False):
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = BG
    yy, xx = np.mgrid[0:MH, 0:MW]
    fx, fy = xx - PADX, yy - PADY       # face coordinates
    cx = (FW - 1) / 2
    # long oval face, widest at the cheekbones (face row 28), long jaw to a
    # rounded chin
    t_up = np.clip((fy - 28) / 30.0, -1, 0)
    t_dn = np.clip((fy - 28) / 36.0, 0, 1)
    half_w = np.where(fy < 28, 31.5 * np.sqrt(1.0 - t_up ** 2),
                      31.5 * np.clip(1.0 - t_dn ** 2, 0.0, 1.0) ** 0.75)
    face = (np.abs(fx - cx) <= half_w) & (fy >= 0) & (fy < FH)
    a[face] = SKIN
    eye_rgb = game_colours(eye_im) if game else eye_im.convert('RGB')
    mouth_rgb = game_colours(mouth_im) if game else mouth_im.convert('RGB')

    def paste(im, x0, y0):
        t_ = np.array(im)
        h, w = t_.shape[:2]
        reg = a[PADY + y0:PADY + y0 + h, PADX + x0:PADX + x0 + w]
        m = face[PADY + y0:PADY + y0 + h, PADX + x0:PADX + x0 + w]
        reg[m] = t_[m]

    paste(eye_rgb, 0, EYE_Y)
    paste(mouth_rgb, MOUTH_X, MOUTH_Y)
    # nose hint (the nose is geometry): broad tip shadow + nostrils
    sh = tuple(int(round(c * CREASE_REL)) for c in SKIN) if game else SHAD
    for x, y in [(29, 35), (30, 35), (31, 35), (32, 35), (33, 35), (34, 35), (27, 34), (36, 34)]:
        a[PADY + y, PADX + x] = sh
    # hair: a big round mass of tight curls, wider than the head, a curly
    # fringe ending just above the brows (a few curl tips touch them), side
    # volume down past the ears
    hx_ = fx - cx
    mass = ((hx_ / 41.0) ** 2 + ((fy - 14) / 27.0) ** 2 <= 1.0) & (fy <= EYE_Y + 2)
    side = ((hx_ / 41.0) ** 2 + ((fy - 14) / 27.0) ** 2 <= 1.0) & (np.abs(hx_) >= 27.5) & \
           (fy <= EYE_Y + 24 - (41 - np.abs(hx_)) * 0.6)
    hair = mass | side
    # bumpy curl silhouette: discs along the outline and down the side volume
    for ang in np.linspace(0, np.pi, 15):
        bx, by = cx + 40 * np.cos(ang), 14 - 26 * np.sin(ang)
        hair |= ((fx - bx) ** 2 + (fy - by) ** 2 <= 16) & (fy <= EYE_Y + 20)
    for sgn in (-1, 1):
        for k, by in enumerate(range(EYE_Y + 4, EYE_Y + 22, 4)):
            bx = cx + sgn * (29.5 + (k % 2))
            hair |= ((fx - bx) ** 2 + (fy - by) ** 2 <= 9)
    # curl lobes hanging below the fringe line: they reach the top of the brows
    # (texture row 5) in a few places and leave most of the brow showing
    for bx, r in [(5, 2.6), (12, 2.2), (19.5, 2.4), (26.5, 2.0), (31.5, 2.6), (36.5, 2.0),
                  (43.5, 2.4), (51, 2.2), (58, 2.6)]:
        hair |= ((fx - bx) ** 2 + (fy - (EYE_Y + 2)) ** 2 <= r * r)
    a[hair] = HAIR
    # curl highlights (stand-in texture so the mass reads as curls)
    rng = np.random.RandomState(7)
    hy, hxs = np.where(hair)
    for _ in range(70):
        k = rng.randint(len(hy))
        y0, x0 = hy[k], hxs[k]
        for dx, dy in ((0, 0), (1, 0), (1, 1)):
            if 0 <= y0 + dy < MH and 0 <= x0 + dx < MW and hair[y0 + dy, x0 + dx] \
                    and not (fy[y0 + dy, x0 + dx] > EYE_Y + 1 and abs(hx_[y0 + dy, x0 + dx]) < 27):
                a[y0 + dy, x0 + dx] = HAIR_HI
    return Image.fromarray(a, 'RGB')


def rgba16(im):
    a = np.array(im.convert('RGB')).astype(np.int32) >> 3
    return Image.fromarray(((a << 3) | (a >> 2)).astype(np.uint8), 'RGB')


def preview_face(tex):
    S = 8
    f = font(20)
    fo = face_mock(tex['eyes_open'], tex['mouth_grin'], game=True)
    fc = face_mock(tex['eyes_closed'], tex['mouth_grin'], game=True)
    gap = 6
    native = Image.new('RGB', (MW * 2 + gap, MH), BG)
    native.paste(fo, (0, 0))
    native.paste(fc, (MW + gap, 0))
    big = Image.new('RGB', (MW * S * 2 + 24, MH * S), BG)
    big.paste(up(fo, S), (0, 0))
    big.paste(up(fc, S), (MW * S + 24, 0))
    # in-game simulation: crease darkening, RGBA16 quantised, box-filtered so the
    # FACE is 15/20/25 px tall
    states = ORDER[:8]
    sims = []
    for th in (15, 20, 25):
        sz = (round(MW * th / FH), round(MH * th / FH))
        row = [up(rgba16(face_mock(tex[s], tex['mouth_grin'], game=True)).resize(sz, Image.BOX), S)
               for s in states]
        sims.append((th, row))
    sim_w = sum(r.width + 12 for r in sims[-1][1])
    W_ = max(big.width, sim_w) + 48
    H_ = (16 + 28 + MH + 24 + 28 + big.height + 24
          + sum(28 + r[0].height + 20 for _, r in sims) + 8)
    pf = Image.new('RGB', (W_, H_), BG)
    d = ImageDraw.Draw(pf)
    y = 16
    d.text((24, y), 'native 1x (face 64x64): eyes_open + mouth_grin  |  eyes_closed (blink) + mouth_grin',
           fill=TXT, font=f)
    y += 28
    pf.paste(native, (24, y))
    y += MH + 24
    d.text((24, y), '8x nearest, skin_shadow shown as the builder ships it (0.70 x skin); '
                    'hair, nose and face shape are stand-ins', fill=TXT, font=f)
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
    # brows identical in every eye state
    ref = np.array(tex['eyes_open'])[..., :3]
    brow = (ref == PAL['B']).all(-1)
    assert brow.any()
    for n in ORDER[:8]:
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['B']).all(-1) == brow).all(), f'{n}: brows differ from eyes_open'
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
    for name, im in tex.items():
        im.save(os.path.join(OUT, name + '.png'))
    preview_sheet(tex).save(os.path.join(OUT, 'preview_sheet.png'))
    preview_face(tex).save(os.path.join(OUT, 'preview_face.png'))
    print('ok:', len(tex), 'textures;', len(cols), 'colours:', ' '.join(cols))


if __name__ == '__main__':
    main()
