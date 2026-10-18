"""Vignesh face textures (GatorCampus 64) - FINAL set.

Same conventions, sizes and file names as Daniel's approved set
(art/daniel/textures): 64x32 eyes / 32x16 mouth, flat opaque skin background
(the builder keys it to alpha 0), left/right eyes exact mirrors on the eye
axes x 14.5 / 48.5, eyes 18-19 px corner to corner with 16 px between them,
eye content rows 12-19, ASCII-grid pixel art only (no antialiasing, no
gradients, no photo pixels), a small RGBA16-safe palette.

Drawn from photo3 (front, blue glasses) with photos 1/2 for the smile:

  brows (rows 6-7, identical in all 8 states)
  * his brows show (short hair, open forehead) and sit right on top of the
    blue browline bar: dark, nearly straight, a blunt 2-row head at the inner
    end, the tail tapering to 1 row past the outer eye corner.  Rows 8-11
    are left as bare skin for the glasses' top bar (geometry): the bar
    covers rows ~8-11.5 (lower edge just above the lash at row 12; the bar
    is as thick as in photo3), so it reads brow / blue bar / eye.  Row 6 is
    the highest row the eye band shows (the band ends at u 0.68 = row 5.2).
  eyes (rows 12-19)
  * open: dark almond eye, more open than Daniel's happy squint: 2-px arched
    upper lash, outer corner reaching out 2 px, dark inner-corner cap, lower
    lid curving up 1 px at both ends of the opening, under-eye smile crease in
    skin_shadow (the builder darkens it to 0.7 x skin).
  * iris 8x7 (Daniel: 10x7) with a 4x3 pupil, so 4 px of white show on each
    side - his eyes read as dark iris between two clear white wedges.  3-px
    white glint at the pupil's upper-right (where it is in photo3), same image
    side in both eyes.
  * left/right move the iris 3 px, up 3, down 2 (same as Daniel); all five
    open-gaze states share exactly the same lid pixels and footprint.
  * half: lash lowered 2 rows + skin-shadow crease where it was.
  * closed: 2-px happy "^" arc ending on the open eye's corners (his laughing
    crescent eyes when he blinks), same under-eye crease.
  * dead: bold 14x9 "X" (3-px strokes) rows 12-20, brows kept.
  mouth (mouth_grin.png)
  * his huge toothy grin: a wide crescent (30 of 32 texels) whose TOP edge
    also curves up at the corners (Daniel's top lip is flat), 5-row upper
    teeth band, dark corner pockets the teeth recede into, deep smile curve
    with the corners turned up to a crease tip, thin darker upper lip, full
    pinkish lower lip, 1-row dark bite line (no lower teeth).
  * no stubble in the texture (STUBBLE below explains why; the stipple code
    is kept but off) - his jaw/chin stubble is geometry.

Palette: the spec's skin / skin_shadow / hair plus the eye and mouth inks
(12 colours, all distinct after RGBA16 quantising).  Run:

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
# Chin stubble stipple in the mouth texture.  OFF: opaque face texels render
# UNLIT, so in the shaded lower face (scratch build, head.png) the stubble
# texels came out PALER than the vertex-shaded skin around them and read as a
# row of light dots under the lip.  Stubble belongs in geometry (the spec's
# "stubble" accessory: a darker skin-material band that is shaded like skin).
STUBBLE = False


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ------------------------------------------------------------------ palette
PAL = {
    '.': hx('C58A68'),   # skin (texture background - exact spec colour)
    's': hx('A97152'),   # skin shadow (spec) - creases
    'B': hx('1E1817'),   # hair (spec) - brows, dead X
    'L': hx('2A1E1C'),   # eyelid / lash line
    'I': hx('3A2620'),   # iris
    'P': hx('120C0C'),   # pupil
    'h': hx('FFFFFF'),   # eye highlight
    'W': hx('F2EEE6'),   # sclera
    'u': hx('8E4C46'),   # upper lip (thin, darker)
    'p': hx('B8676A'),   # lower lip (fuller, pinker)
    'm': hx('5A2224'),   # mouth corners / bite line
    'T': hx('FFFDF2'),   # teeth
    't': hx('8C5E48'),   # stubble (spec)
}
SKIN = PAL['.']


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# ===================================================================== EYES
# The LEFT eye (image-left; his right eye) is drawn as ASCII in a window of
# texture columns x = EX0 .. EX0+23 and rows y = EY0 .. EY0+15.  Outer corner
# on the left, inner corner (next to the nose) on the right.  The right eye is
# the exact mirror x -> 63 - x.  'W' marks the eye opening (sclera; the iris is
# stamped into it), 'L' lash / lid ink, 's' skin shadow, 'B' brow.
EX0, EY0 = 4, 4
#            x = 4         1         2
#                4567890123456789012345678
BROW = [
    "........................",   # 4
    "........................",   # 5
    "......BBBBBBBBBBBBBB....",   # 6   brow: blunt 2-row head at the inner end
    "..BBBBBBBBBBBBBBBBBBB...",   # 7   (right), tail tapering to 1 row outside
    "........................",   # 8   rows 8-11: bare skin for the blue bar
    "........................",   # 9
    "........................",   # 10
    "........................",   # 11
]
LIDS = {
    'open': [
        "........LLLLLL..........",   # 12  lash top (peak)
        "......LLLLLLLLLL........",   # 13
        "....LLLLWWWWWWLLLL......",   # 14
        "...LLLWWWWWWWWWWLLL.....",   # 15
        "..LLWWWWWWWWWWWWWWLL....",   # 16
        ".LLWWWWWWWWWWWWWWWWL....",   # 17  widest; outer corner reaches out 2 px
        "....WWWWWWWWWWWWWWLL....",   # 18  lower lid curves up at both ends
        "....ssssssssssssss......",   # 19  under-eye smile crease
    ],
    'half': [
        "........ssssss..........",   # 12  crease where the open lash was
        "......ss......ss........",   # 13
        "........LLLLLL..........",   # 14  lash lowered 2 rows
        "......LLLLLLLLLL........",   # 15
        "..LLLLLLWWWWWWLLLLLL....",   # 16  lid edge meets the open corners
        ".LLWWWWWWWWWWWWWWWWL....",   # 17  = open row 17
        "....WWWWWWWWWWWWWWLL....",   # 18  = open row 18
        "....ssssssssssssss......",   # 19
    ],
    'closed': [
        "........................",   # 12
        ".......LLLLLLLL.........",   # 13  happy "^" arc, 2 px thick
        ".....LLLLLLLLLLLL.......",   # 14
        "...LLLL........LLLL.....",   # 15
        "..LLL............LLL....",   # 16
        ".LL................L....",   # 17  same corners as open
        "........................",   # 18
        "....ssssssssssssss......",   # 19
    ],
}
LID_Y0 = 12

IRIS = [  # 8 x 7 (top and bottom rows sit under the lids by default)
    ".IIIIII.",
    "IIIIIIII",
    "IIPPPPII",
    "IIPPPPII",
    "IIPPPPII",
    "IIIIIIII",
    ".IIIIII.",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 11          # left eye: iris columns 11..18, centred on the opening 7..22
IRIS_Y = 13          # rows 13..19 (visible 14..18)
GLINT = [(4, 2), (5, 2), (5, 3)]   # upper-right of the pupil, same side both eyes
GAZE_X = 3
GAZE_UP = 3
GAZE_DOWN = 2

DEAD_X = [  # 14 x 9 knocked-out X, columns 8..21, rows 12..20 (left eye)
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


def _stamp(g, rows, y0):
    for j, row in enumerate(rows):
        assert len(row) == 24, (j, row)
        for i, ch in enumerate(row):
            if ch != '.':
                g[y0 + j][EX0 + i] = ch
                g[y0 + j][63 - (EX0 + i)] = ch


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    _stamp(g, BROW, EY0)
    if state == 'dead':
        for j, row in enumerate(DEAD_X):
            for i, ch in enumerate(row):
                if ch != '.':
                    g[DEAD_Y0 + j][DEAD_X0 + i] = ch
                    g[DEAD_Y0 + j][63 - (DEAD_X0 + i)] = ch
        return g
    _stamp(g, LIDS['half' if state == 'half' else 'closed' if state == 'closed' else 'open'], LID_Y0)
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
# Left half (x = 0..15) of the 32x16 grin; the right half is its mirror.
#   m dark corners / bite line   T upper teeth   u upper lip   p lower lip
#   t stubble (stipple, only if STUBBLE)
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    ".mmuu...........",  # 2  corner crease tip (turned up) + upper lip
    "..mTTuuuu.......",  # 3  the teeth's top edge curves up toward the
    "..mTTTTTTuuuuuuu",  # 4  corners (crescent), thin darker upper lip
    "..mmTTTTTTTTTTTT",  # 5  upper teeth, 5 rows in the middle
    "...mmTTTTTTTTTTT",  # 6
    "....mmTTTTTTTTTT",  # 7
    ".....mmmTTTTTTTT",  # 8
    ".......mmmmTTTTT",  # 9
    "........ppmmmmmm",  # 10 dark bite line (no lower teeth)
    ".........ppppppp",  # 11 full lower lip
    "...........ppppp",  # 12
    "................",  # 13
    "................",  # 14
    "................",  # 15
]
STUBBLE_HALF = [  # sparse chin stipple under the lower lip (rows 13-14)
    "................",  # 13
    "...........t.t.t",  # 13
    "............t.t.",  # 14
]
STUBBLE_Y0 = 12


def mouth_grid():
    rows = []
    for r in MOUTH_HALF:
        assert len(r) == 16, r
        rows.append(list(r + r[::-1]))
    if STUBBLE:
        for j, r in enumerate(STUBBLE_HALF):
            assert len(r) == 16, r
            full = r + r[::-1]
            for x, ch in enumerate(full):
                if ch != '.' and rows[STUBBLE_Y0 + j][x] == '.':
                    rows[STUBBLE_Y0 + j][x] = ch
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
HAIR = PAL['B']
SHAD = PAL['s']
GL_TOP = hx('2F56A8')    # spec glasses_top (stand-in geometry in the mock only)
GL_RIM = hx('8A8E96')    # spec glasses_rim


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
    d.text((24, 12), 'Vignesh face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
           fill=TXT, font=f)
    for i, name in enumerate(ORDER):
        x, y = 24 + (i % cols) * cw, 48 + (i // cols) * ch
        im = tex[name]
        d.text((x, y), f'{name}.png  ({im.width}x{im.height})', fill=TXT, font=f)
        sheet.paste(up(im, S).convert('RGB'), (x, y + 28))
    return sheet


# Face mock, 64x64, 1 texel = 1 px (same density the textures are drawn at).
# Hair, glasses, nose, stubble and face outline are rough stand-ins for the
# real geometry.
MW = MH = 64
EYE_Y = 8          # eye texture top row on the mock (brows -> 14-16, lash top -> 20)
MOUTH_X, MOUTH_Y = 16, 40


def face_mock(eye_im, mouth_im, glasses=True):
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = BG
    cx = (MW - 1) / 2
    yy, xx = np.mgrid[0:MH, 0:MW]
    # oval face, widest at the cheekbones (row 30), jaw tapering to a
    # rounded chin
    t = np.where(yy < 30, (yy - 30) / 30.0, (yy - 30) / 33.5)
    half_w = 31.5 * np.clip(1.0 - np.abs(t) ** 2.3, 0.0, 1.0) ** 0.5
    face = np.abs(xx - cx) <= half_w
    a[face] = SKIN

    def paste(im, x0, y0):
        t = np.array(im.convert('RGB'))
        h, w = t.shape[:2]
        reg = a[y0:y0 + h, x0:x0 + w]
        m = face[y0:y0 + h, x0:x0 + w] & (t != np.array(SKIN, np.uint8)).any(-1)
        reg[m] = t[m]

    # light jaw / chin stubble stand-in (geometry or nothing in game)
    edge = face & ~(np.abs(xx - cx) <= half_w - 3) & (yy >= 44)
    a[edge & ((xx + yy) % 2 == 0)] = PAL['t']

    paste(eye_im, 0, EYE_Y)
    paste(mouth_im, MOUTH_X, MOUTH_Y)
    # nose hint (the nose is geometry): tip shadow + nostrils
    for x, y in [(30, 37), (31, 37), (32, 37), (33, 37), (29, 36), (34, 36)]:
        a[y, x] = SHAD
    # hair: short, curly, volume on top; hairline a few rows above the brows,
    # bumpy curl edge, short sides down to the temples
    hl = EYE_Y + 0                                    # hairline (brows at EYE_Y+6)
    cap = ((xx - cx) / 33.0) ** 2 + ((yy - 18) / 19.0) ** 2 <= 1.0
    bump = ((xx // 3) % 2) * 1 + ((xx // 5) % 2)     # 0..2 rows of curl bumps
    hair = cap & (yy <= hl + bump - (np.abs(xx - cx) < 8))
    side = (np.abs(xx - cx) >= 28.5) & (yy <= EYE_Y + 14 + ((xx // 2) % 2))
    a[hair | (side & (face | cap))] = HAIR
    if glasses:
        # browline glasses stand-in: thick blue top bar on texture rows 8-11,
        # thin silver lower rims, bridge
        for lo, hi in ((3, 28), (35, 60)):
            a[EYE_Y + 8:EYE_Y + 12, lo:hi + 1] = GL_TOP
            a[EYE_Y + 12:EYE_Y + 21, lo] = GL_RIM
            a[EYE_Y + 12:EYE_Y + 21, hi] = GL_RIM
            a[EYE_Y + 21, lo + 1:hi] = GL_RIM
        a[EYE_Y + 10, 29:35] = GL_TOP
    return Image.fromarray(a, 'RGB')


def rgba16(im):
    a = np.array(im.convert('RGB')).astype(np.int32) >> 3
    return Image.fromarray(((a << 3) | (a >> 2)).astype(np.uint8), 'RGB')


def preview_face(tex):
    S = 8
    f = font(20)
    fo = face_mock(tex['eyes_open'], tex['mouth_grin'])
    fc = face_mock(tex['eyes_closed'], tex['mouth_grin'])
    fn = face_mock(tex['eyes_open'], tex['mouth_grin'], glasses=False)
    gap = 6
    native = Image.new('RGB', (MW * 3 + gap * 2, MH), BG)
    for k, im in enumerate((fo, fc, fn)):
        native.paste(im, (k * (MW + gap), 0))
    big = Image.new('RGB', (MW * S * 2 + 24, MH * S), BG)
    big.paste(up(fo, S), (0, 0))
    big.paste(up(fn, S), (MW * S + 24, 0))
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
    d.text((24, y), 'native 1x, 64x64 each: eyes_open + mouth_grin  |  eyes_closed (blink)  |  open, no glasses',
           fill=TXT, font=f)
    y += 28
    pf.paste(native, (24, y))
    y += MH + 24
    d.text((24, y), '8x nearest neighbour, with / without glasses  (hair, glasses, nose, jaw stubble and '
                    'face shape are stand-ins for the geometry)', fill=TXT, font=f)
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
    # brows identical in all eight eye states
    brow = (ref == PAL['B']).all(-1)[:12]
    for n in ORDER[:8]:
        b = np.array(tex[n])[..., :3][:12]
        assert ((b != skin).any(-1) == brow).all(), f'{n}: brow rows differ'
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
