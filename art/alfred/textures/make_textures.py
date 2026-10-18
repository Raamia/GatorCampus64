"""Alfred face textures (GatorCampus 64) - FINAL set.

Same conventions, sizes and code layout as Daniel's approved set
(art/daniel/textures/make_textures.py): flat skin background (keyed to alpha 0
by the builder), hand-placed pixels only, left eye drawn as ASCII and mirrored
x -> 63 - x, eye axes x 14.5 / 48.5, eye block rows 12-18 (centre 15, texture
centre 15.5), one eye-width (16 px, Daniel's spacing) between the eyes.  Drawn from reference/friends/alfred/photo1.png
reduced to texel scale (face about 74 texels wide, like the head layout).

  brows (what makes him recognisable at game size)
  * thick, dark, nearly straight brows, rows 6-9, in the spec's eyebrow
    colour: a blunt 4-row head over the inner eye corner (x 17-26), a 3-row
    body, and a tail that tapers in even 3-px stairs (3 -> 2 -> 1 rows) past
    the outer eye corner to x 2.  10 px between the two brow heads (x 27-36).
    They sit in the EYE texture, so they are identical in all 8 states (they
    never jump when he blinks or looks around); there is no fringe over them
    (his curls stop well above the brows).
  eyes
  * open: friendly almond, narrower than Daniel's half-moon: 2-px gently
    arched upper lash, 4-row opening, the outer corner drops into a 1-px tail
    (down and out), the inner corner is a short dark point, no lower-lid ink
    (the white sits straight on skin) and a skin-shadow row under the eye for
    his under-eye shadow.  Left eye x 5-23, right eye x 40-58, rows 12-18
    (the same corner-to-corner footprint as Daniel's).
  * iris 10x6 with a 4x3 pupil and a 3-px white glint (same image side in both
    eyes); it fills the opening top to bottom, so at game size the eye is a
    dark slit with small white corner wedges (his eyes in the photo).
  * left/right move the iris 3 px, up 2 px, down 1 px; all five open-gaze
    states share exactly the same lid pixels and footprint - only the iris
    moves.
  * half: lash lowered 2 rows + a skin-shadow crease where it was.
  * closed: 2-px happy "^" arc on the same corners (he is always smiling).
  * dead: bold 14x9 "X" (3-px strokes, one 4-px crossing), rows 12-20, under
    the unchanged brows (2 skin rows between them).
  mouth (mouth_grin.png, 32x16)
  * his big friendly smile: wide crescent, a 2-row upper lip in the middle
    thinning to 1 row, 4 rows of upper teeth whose lower edge follows the
    smile curve, chunky dark corners turned up 1 px, a 1-row dark bite line
    (no lower teeth) and a fuller 2-3 row lower lip.  Two lip tones as in the
    photo: darker red upper lip (in shade), pink lower lip.

Every pixel comes from the ASCII grids / tables below - no antialiasing, no
gradients, no photo pixels.  Run:

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
# skin / skin_shadow / eyebrows are art/alfred/character.json colours; the eye
# inks are Daniel's (dark brown eyes in both photos); lips sampled from the
# photo and lifted to read against the shaded skin.
PAL = {
    '.': hx('D29C80'),   # skin (texture background - exact spec colour)
    's': hx('B98468'),   # skin shadow (spec; the builder darkens it to 0.70 x skin)
    'B': hx('221817'),   # eyebrows (spec)
    'L': hx('2A1E1C'),   # eyelid / lash line, dead X
    'I': hx('3A2620'),   # iris
    'P': hx('120C0C'),   # pupil
    'h': hx('FFFFFF'),   # eye highlight
    'W': hx('F2EEE6'),   # sclera
    'r': hx('A85450'),   # upper lip (in shade, darker red)
    'p': hx('C47270'),   # lower lip (pink)
    'm': hx('6E2A2A'),   # mouth interior / corners
    'T': hx('FFFDF2'),   # teeth
}
SKIN = PAL['.']


def to_img(grid):
    a = np.array([[(*PAL[ch], 255) for ch in row] for row in grid], np.uint8)
    return Image.fromarray(a, 'RGBA')


# =================================================================== BROWS
# Left (image-left) brow, texture columns x = 0..31, rows y = BY0..; outer
# tail on the left, blunt head (next to the nose) on the right.  Mirrored to
# the right brow.  Identical in every eye state.
BY0 = 5
#              x = 0         1         2         3
#                  01234567890123456789012345678901
BROW = [
    "................................",   # 5
    "........BBBBBBBBBBBBBBBBB.......",   # 6   top edge: even 3-px stairs
    ".....BBBBBBBBBBBBBBBBBBBBBB.....",   # 7   down to the tail
    "..BBBBBBBBBBBBBBBBBBBBBBBBB.....",   # 8   tail 1 row, body 3, head 4
    ".................BBBBBBBBB......",   # 9   4-row blunt head
    "................................",   # 10
]

# ===================================================================== EYES
# The LEFT eye (image-left) is drawn as ASCII in a window of texture columns
# x = EX0 .. EX0+23 and rows y = EY0 .. EY0+11.  Outer corner on the left,
# inner corner (next to the nose) on the right.  The right eye is the exact
# mirror x -> 63 - x.  'W' marks the eye opening (sclera; the iris is stamped
# into it), 'L' lash / lid ink, 's' skin shadow.
EX0, EY0 = 4, 10
#            x = 4         1         2
#                4567890123456789012345678
LIDS = {
    'open': [
        "........................",   # 10
        "........................",   # 11
        "........LLLLLL..........",   # 12  lash top (peak)
        ".....LLLLLLLLLLLL.......",   # 13
        "...LLLLWWWWWWWWLLLL.....",   # 14
        "..LLWWWWWWWWWWWWWWLL....",   # 15
        ".LLWWWWWWWWWWWWWWWWL....",   # 16  inner corner point at x 23
        ".L.....WWWWWWWW.........",   # 17  tail down + out; lower lid curves up
        "......ssssssssssss......",   # 18  under-eye shadow
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'half': [
        "........................",   # 10
        "........................",   # 11
        "........ssssss..........",   # 12  crease where the open lash was
        ".....sss......sss.......",   # 13
        "........LLLLLL..........",   # 14  lash lowered 2 rows
        "..LLLLLLLLLLLLLLLLLL....",   # 15
        ".LLLWWWWWWWWWWWWWWLL....",   # 16
        ".L.....WWWWWWWW.........",   # 17
        "......ssssssssssss......",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
    'closed': [
        "........................",   # 10
        "........................",   # 11
        "........................",   # 12
        "........................",   # 13
        ".......LLLLLLLL.........",   # 14  happy "^" arc, 2 px thick
        ".....LLLLLLLLLLLL.......",   # 15
        "...LLLL........LLLL.....",   # 16
        ".LLL.............LLL....",   # 17  same tail as open
        "......ssssssssssss......",   # 18
        "........................",   # 19
        "........................",   # 20
        "........................",   # 21
    ],
}

IRIS = [  # 10 x 6 (top and bottom rows sit under the lids by default)
    "..IIIIII..",
    ".IIPPPPII.",
    "IIIPPPPIII",
    "IIIPPPPIII",
    ".IIIIIIII.",
    "..IIIIII..",
]
IW, IH = len(IRIS[0]), len(IRIS)
IRIS_X = 10          # left eye: iris columns 10..19, centred on the opening 6..23
IRIS_Y = 13          # rows 13..18
GLINT = [(3, 1), (4, 1), (3, 2)]   # upper-left of the pupil, same side both eyes
GAZE_X = 3
GAZE_UP = 2
GAZE_DOWN = 1

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


def stamp_brows(g):
    for j, row in enumerate(BROW):
        assert len(row) == 32, j
        for i, ch in enumerate(row):
            if ch != '.':
                g[BY0 + j][i] = ch
                g[BY0 + j][63 - i] = ch


def eye_grid(state, gaze=(0, 0)):
    g = [['.'] * 64 for _ in range(32)]
    stamp_brows(g)
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
# Left half (x = 0..15) of the 32x16 grin; the right half is its mirror.
#   m dark mouth corners / bite line   T upper teeth   r upper lip   p lower lip
MOUTH_HALF = [
    "................",  # 0
    "................",  # 1
    "................",  # 2
    "........rrrrrrrr",  # 3  upper lip, 2 rows in the middle
    ".m..rrrrrrrrrrrr",  # 4  corner tip turns up 1 px
    ".mmmTTTTTTTTTTTT",  # 5  chunky dark corner, upper teeth
    "..mmmTTTTTTTTTTT",  # 6
    "....mmmTTTTTTTTT",  # 7
    "......mmmTTTTTTT",  # 8  teeth: 4 rows in the middle, edge follows the smile
    ".....ppmmmmmmmmm",  # 9  dark bite line (no lower teeth)
    "......pppppppppp",  # 10 fuller lower lip
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
HAIR = hx('1E1A1B')          # spec hair colour (stand-in geometry only)
FADE = hx('5A4640')          # faded sides stand-in (hair over skin)
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
    d.text((24, 12), 'Alfred face textures - final   (8x nearest neighbour, 1 block = 1 texel)',
           fill=TXT, font=f)
    for i, name in enumerate(ORDER):
        x, y = 24 + (i % cols) * cw, 48 + (i // cols) * ch
        im = tex[name]
        d.text((x, y), f'{name}.png  ({im.width}x{im.height})', fill=TXT, font=f)
        sheet.paste(up(im, S).convert('RGB'), (x, y + 28))
    return sheet


# Face mock, 64x64, 1 texel = 1 px (same density the textures are drawn at).
# Hair, nose, ears and face outline are rough stand-ins for the real geometry.
MW = MH = 64
EYE_Y = 10         # eye texture top row on the mock (brows -> rows 16-19)
MOUTH_X, MOUTH_Y = 16, 42
NOSE_Y = 38


def face_mock(eye_im, mouth_im):
    a = np.zeros((MH, MW, 3), np.uint8)
    a[:] = BG
    cx = (MW - 1) / 2
    yy, xx = np.mgrid[0:MH, 0:MW]
    # face widest at the cheekbones (row 34), jaw tapering to a rounded chin
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
    for x, y in [(30, NOSE_Y), (31, NOSE_Y), (32, NOSE_Y), (33, NOSE_Y), (29, NOSE_Y - 1), (34, NOSE_Y - 1)]:
        a[y, x] = SHAD
    # hair: curly mass piled on top, lower edge a row of round curls ending
    # 3-4 rows above the brows (one curl hangs a little lower at the centre),
    # short faded sides down the temples
    hl = EYE_Y - 3                        # hairline row between the curls
    top = ((xx - cx) / 34.0) ** 2 + ((yy - 14) / 15.0) ** 2 <= 1.0
    hair = top & (yy <= hl)
    for x0 in range(2, 62, 5):            # curl bumps under the hairline
        for dx, dpt in ((0, 1), (1, 2), (2, 2), (3, 1)):
            for k in range(1, dpt + 1):
                if 0 <= x0 + dx < MW:
                    hair[hl + k, x0 + dx] = True
    for dx, dpt in ((0, 2), (1, 3), (2, 3), (3, 2)):   # centre forehead curl
        for k in range(1, dpt + 1):
            hair[hl + k, 30 + dx] = True
    a[hair & (top | face)] = HAIR
    side = face & (np.abs(xx - cx) >= 29.5) & (yy > hl) & (yy <= EYE_Y + 18)
    a[side] = FADE
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
    # brows: identical pixels in every eye state, nothing else in the brow rows
    ref = np.array(tex['eyes_open'])[..., :3]
    brow = (ref == PAL['B']).all(-1)
    assert brow.any() and not brow[11:].any(), 'brows missing or below row 10'
    for n in ORDER[:8]:
        b = np.array(tex[n])[..., :3]
        assert ((b == PAL['B']).all(-1) == brow).all(), f'{n}: brows differ from eyes_open'
        assert not (b[:11] != skin).any(-1)[~brow[:11]].any(), f'{n}: eye ink in the brow rows'
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
