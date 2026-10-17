"""Independent spec check for Vignesh's final face textures (shares no code
with make_textures.py).  Run:

    tools/.venv/bin/python -I verify_textures.py

Exits non-zero and prints FAIL lines if anything is off.
"""
import json
import os
import sys
import numpy as np
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(D, '..', 'character.json')))['colors']


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


SKIN = rgb(SPEC['skin'])
HAIR = rgb(SPEC['hair'])
LASH = (0x2A, 0x1E, 0x1C)
ALLOWED = {  # spec colours + the eye / mouth inks
    SPEC['skin'].upper(), SPEC['skin_shadow'].upper(), SPEC['hair'].upper(), SPEC['stubble'].upper(),
    '#2A1E1C', '#3A2620', '#120C0C', '#FFFFFF', '#F2EEE6',     # lash, iris, pupil, glint, sclera
    '#8E4C46', '#B8676A', '#5A2224', '#FFFDF2'}                # upper lip, lower lip, mouth dark, teeth
FORBIDDEN = {SPEC['glasses_top'].upper(), SPEC['glasses_rim'].upper()}  # glasses are geometry
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
BROW_ROWS = range(0, 12)     # brows live above row 12; the eyes in rows 12-20
FILES = [n + '.png' for n in EYES] + ['mouth_grin.png', 'preview_sheet.png',
                                       'preview_face.png', 'make_textures.py']
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


def hexc(c):
    return '#%02X%02X%02X' % tuple(int(v) for v in c[:3])


# 1. files present
for f in FILES:
    ok(os.path.isfile(os.path.join(D, f)), f'missing {f}')

# 2. per-texture format checks
arr = {}
allcols = set()
print(f'{"texture":12s} {"mode":4s} {"size":>6s} {"alpha":>5s} {"border":>6s} {"cols":>4s}  content bbox (x0,y0,x1,y1)')
for n in EYES + ['mouth_grin']:
    p = os.path.join(D, n + '.png')
    if not os.path.isfile(p):
        continue
    im = Image.open(p)
    exp = (32, 16) if n == 'mouth_grin' else (64, 32)
    a = np.array(im.convert('RGBA'))
    arr[n] = a
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bad_border = int((~((border[:, :3] == SKIN).all(1) & (border[:, 3] == 255))).sum())
    cols = {hexc(c) for c in a.reshape(-1, 4)}
    allcols |= cols
    m = (a[..., :3] != SKIN).any(-1)
    ys, xs = np.where(m)
    bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    ok(im.mode == 'RGBA', f'{n}: mode {im.mode}')
    ok(im.size == exp, f'{n}: size {im.size} != {exp}')
    ok(int(a[..., 3].min()) == 255, f'{n}: alpha < 255 present')
    ok(bad_border == 0, f'{n}: {bad_border} border pixels not skin')
    ok((m == m[:, ::-1]).all(), f'{n}: left/right halves not mirror shapes')
    # background really is the skin colour (most texels)
    ok(m.mean() < 0.5, f'{n}: background is not mostly skin')
    print(f'{n:12s} {im.mode:4s} {im.size[0]:>2d}x{im.size[1]:<3d} {int(a[..., 3].min()):>5d} '
          f'{bad_border:>6d} {len(cols):>4d}  {bb}')

# 3. palette + RGBA16 (5-bit) distinctness, no glasses colours
ok(allcols <= ALLOWED, f'off-palette colours: {sorted(allcols - ALLOWED)}')
ok(not (allcols & FORBIDDEN), 'glasses colours drawn in a texture (glasses are geometry)')
q = {tuple(int(h[i:i + 2], 16) >> 3 for i in (1, 3, 5)) for h in allcols}
ok(len(q) == len(allcols), 'some colours merge after RGBA16 quantisation')
print(f'colours used ({len(allcols)}): {" ".join(sorted(allcols))}; distinct in RGBA16: {len(q) == len(allcols)}')

# 4. eye placement consistency across the 8 states
if all(n in arr for n in EYES):
    ref = arr['eyes_open'][..., :3]
    ref_foot = (ref != SKIN).any(-1)
    ref_lid = (ref == LASH).all(-1)
    ref_brow = ref_foot[list(BROW_ROWS)]
    ok(ref_brow.any(), 'no brows above the eyes')
    ok(((ref[list(BROW_ROWS)] == HAIR).all(-1) == ref_brow).all(), 'brow rows contain non-hair colours')
    print('\nstate        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / footprint px / brow px')
    for n in EYES:
        a = arr[n][..., :3]
        foot = (a != SKIN).any(-1)
        eye = foot.copy()
        eye[list(BROW_ROWS)] = False
        row = []
        for x0, x1 in ((0, 32), (32, 64)):
            ys, xs = np.where(eye[:, x0:x1])
            xs = xs + x0
            row.append(((xs.min(), ys.min(), xs.max(), ys.max()),
                        ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)))
        lid_d = int(((a == LASH).all(-1) != ref_lid).sum())
        foot_d = int((foot != ref_foot).sum())
        brow_d = int((foot[list(BROW_ROWS)] != ref_brow).sum())
        (lb, lc), (rb, rc) = row
        print(f'{n:12s} {str(tuple(map(int, lb))):17s} {str(tuple(map(int, rb))):17s} '
              f'({lc[0]:4.1f},{lc[1]:4.1f}) ({rc[0]:4.1f},{rc[1]:4.1f})   {lid_d:4d} / {foot_d:4d} / {brow_d:3d}')
        # every state is centred on the same eye axes (x 14.5 / 48.5)
        ok(abs(lc[0] - 14.5) <= 0.5 and abs(rc[0] - 48.5) <= 0.5, f'{n}: eye not on the eye axis')
        # eye content stays within rows 12-20 (dead may use row 20)
        ok(lb[1] >= 12 and lb[3] <= 20, f'{n}: eye rows {lb[1]}-{lb[3]} outside 12-20')
        # brows identical in every state
        ok(brow_d == 0, f'{n}: brows differ from eyes_open')
        if n in GAZE:
            ok(lid_d == 0 and foot_d == 0, f'{n}: lids/footprint differ from eyes_open')
    # half / closed keep the open eye's corner inks (outer corner + inner corner)
    for n in ('eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((5, 17), (6, 17), (23, 17), (58, 17), (57, 17), (40, 17)):
            ok((a[y, x] == LASH).all(), f'{n}: corner ink missing at ({x},{y})')
    # open eye block (without brows) vertically centred in the 32 rows, eyes ~1 eye-width apart
    eye = ref_foot.copy()
    eye[list(BROW_ROWS)] = False
    ys = np.where(eye.any(1))[0]
    lx = np.where(eye[:, :32].any(0))[0]
    width, gap = lx.max() - lx.min() + 1, 62 - 2 * lx.max()
    ok((ys.min() + ys.max()) / 2 == 15.5, f'eyes_open eye rows {ys.min()}-{ys.max()} not centred')
    ok(0.75 <= gap / width <= 1.1, f'eye gap {gap} not about one eye width ({width})')
    by = np.where(ref_brow.any(1))[0]
    print(f'\neyes_open eye rows {ys.min()}-{ys.max()} (centre {(ys.min() + ys.max()) / 2}, '
          f'texture centre 15.5); left eye x {lx.min()}..{lx.max()} ({width} wide), '
          f'gap between eyes x {lx.max() + 1}..{62 - lx.max()} ({gap} px); brow rows {by.min()}-{by.max()}')

# 5. mouth: teeth present and the grin spans most of the width
if 'mouth_grin' in arr:
    a = arr['mouth_grin'][..., :3]
    teeth = (a == (0xFF, 0xFD, 0xF2)).all(-1)
    xs = np.where((a != SKIN).any(-1).any(0))[0]
    ok(teeth.sum() >= 100, f'mouth: only {int(teeth.sum())} teeth texels')
    ok(xs.max() - xs.min() + 1 >= 28, 'mouth: grin narrower than 28 texels')
    print(f'mouth_grin: {int(teeth.sum())} teeth texels, spans x {xs.min()}..{xs.max()}')

# 6. previews readable
for f in ('preview_sheet.png', 'preview_face.png'):
    p = os.path.join(D, f)
    if os.path.isfile(p):
        im = Image.open(p)
        print(f'{f}: {im.size[0]}x{im.size[1]} {im.mode}')

print()
if fails:
    for f in fails:
        print('FAIL:', f)
    sys.exit(1)
print('ALL CHECKS PASSED')
