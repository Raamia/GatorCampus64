"""Independent spec check for Alfred's final face textures (shares no code
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
SPEC = json.load(open(os.path.join(D, '..', 'character.json')))


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


SKIN = rgb(SPEC['colors']['skin'])            # texture background (keyed by the builder)
CREASE = rgb(SPEC['colors']['skin_shadow'])   # crease / under-eye shadow
BROW = rgb(SPEC['colors']['eyebrows'])        # brows
LASH = (0x2A, 0x1E, 0x1C)
PALETTE = {  # the set's palette: spec skin / skin_shadow / eyebrows + eye and mouth inks
    '#%02X%02X%02X' % SKIN, '#%02X%02X%02X' % CREASE, '#%02X%02X%02X' % BROW,
    '#2A1E1C', '#3A2620', '#120C0C', '#FFFFFF', '#F2EEE6',
    '#A85450', '#C47270', '#6E2A2A', '#FFFDF2'}
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
BROW_ROWS = (5, 10)     # brows live here (upper rows of the eye texture)
EYE_ROW0 = 11           # eye content starts below this
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
    print(f'{n:12s} {im.mode:4s} {im.size[0]:>2d}x{im.size[1]:<3d} {int(a[..., 3].min()):>5d} '
          f'{bad_border:>6d} {len(cols):>4d}  {bb}')

# 3. palette + RGBA16 (5-bit) distinctness
ok(allcols <= PALETTE, f'off-palette colours: {sorted(allcols - PALETTE)}')
q = {tuple(int(h[i:i + 2], 16) >> 3 for i in (1, 3, 5)) for h in allcols}
ok(len(q) == len(allcols), 'some colours merge after RGBA16 quantisation')
print(f'colours used ({len(allcols)}): {" ".join(sorted(allcols))}; distinct in RGBA16: {len(q) == len(allcols)}')
ok('#%02X%02X%02X' % SKIN in allcols, 'spec skin colour not used as background')

# 4. brows: spec eyebrow colour, upper rows only, identical in all 8 states
if all(n in arr for n in EYES):
    ref_brow = (arr['eyes_open'][..., :3] == BROW).all(-1)
    ys, xs = np.where(ref_brow)
    ok(ref_brow.any(), 'no brow pixels (spec eyebrows colour) in eyes_open')
    if ref_brow.any():
        lx = xs[xs < 32]
        ok(ys.min() >= BROW_ROWS[0] and ys.max() <= BROW_ROWS[1],
           f'brows rows {ys.min()}-{ys.max()} outside {BROW_ROWS}')
        print(f'\nbrows: rows {ys.min()}-{ys.max()}, left brow x {lx.min()}..{lx.max()} '
              f'({lx.max() - lx.min() + 1} wide), gap between brows x {lx.max() + 1}..{62 - lx.max()} '
              f'({62 - 2 * lx.max()} px), {int(ref_brow.sum())} texels')
    for n in EYES:
        a = arr[n][..., :3]
        b = (a == BROW).all(-1)
        ok((b == ref_brow).all(), f'{n}: brows differ from eyes_open')
        other = (a != SKIN).any(-1) & ~b
        ok(not other[:EYE_ROW0].any(), f'{n}: non-brow ink above row {EYE_ROW0}')
        ok(not b[EYE_ROW0:].any(), f'{n}: brow colour below row {EYE_ROW0 - 1}')

# 5. eye placement consistency across the 8 states (eye rows only)
if all(n in arr for n in EYES):
    ref = arr['eyes_open'][..., :3]
    ref_foot = (ref != SKIN).any(-1)
    ref_foot[:EYE_ROW0] = False
    ref_lid = (ref == LASH).all(-1)
    print('\nstate        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / footprint px')
    for n in EYES:
        a = arr[n][..., :3]
        foot = (a != SKIN).any(-1)
        foot[:EYE_ROW0] = False
        row = []
        for x0, x1 in ((0, 32), (32, 64)):
            ys, xs = np.where(foot[:, x0:x1])
            xs = xs + x0
            row.append(((xs.min(), ys.min(), xs.max(), ys.max()),
                        ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)))
        lid_d = int(((a == LASH).all(-1) != ref_lid).sum())
        foot_d = int((foot != ref_foot).sum())
        (lb, lc), (rb, rc) = row
        print(f'{n:12s} {str(tuple(map(int, lb))):17s} {str(tuple(map(int, rb))):17s} '
              f'({lc[0]:4.1f},{lc[1]:4.1f}) ({rc[0]:4.1f},{rc[1]:4.1f})   {lid_d:4d} / {foot_d:4d}')
        # every state is centred on the same eye axes (x 14.5 / 48.5, Daniel's)
        ok(abs(lc[0] - 14.5) <= 0.5 and abs(rc[0] - 48.5) <= 0.5, f'{n}: eye not on the eye axis')
        # content stays within the open eye's vertical band (+2 rows for dead)
        ok(lb[1] >= 12 and lb[3] <= 20, f'{n}: content rows {lb[1]}-{lb[3]} outside 12-20')
        if n in GAZE:
            ok(lid_d == 0 and foot_d == 0, f'{n}: lids/footprint differ from eyes_open')
        if n not in ('eyes_closed', 'eyes_dead'):
            ok(((a == (0x12, 0x0C, 0x0C)).all(-1)).any(), f'{n}: no pupil visible')
            ok(((a == (0xFF, 0xFF, 0xFF)).all(-1)).sum() >= 2, f'{n}: glints missing')
    # half / closed keep the open eye's outer-corner tail
    for n in ('eyes_open', 'eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((5, 17), (58, 17)):
            ok((a[y, x] == LASH).all(), f'{n}: corner tail missing at ({x},{y})')
    ys = np.where(ref_foot.any(1))[0]
    lx = np.where(ref_foot[:, :32].any(0))[0]
    ok(abs((ys.min() + ys.max()) / 2 - 15.5) <= 0.5, f'eyes_open eye rows {ys.min()}-{ys.max()} not centred')
    gap = 62 - 2 * lx.max()
    width = lx.max() - lx.min() + 1
    ok(0.75 * width <= gap <= 1.1 * width, f'eye gap {gap} px is not about one eye-width ({width} px)')
    print(f'\neyes_open eye rows {ys.min()}-{ys.max()} (centre {(ys.min() + ys.max()) / 2}, '
          f'texture centre 15.5); left eye x {lx.min()}..{lx.max()} ({width} wide), '
          f'gap between eyes x {lx.max() + 1}..{62 - lx.max()} ({gap} px)')

# 6. mouth: upper teeth present, dark corners, lips both tones, centred
if 'mouth_grin' in arr:
    a = arr['mouth_grin'][..., :3]
    teeth = (a == (0xFF, 0xFD, 0xF2)).all(-1)
    ty = np.where(teeth.any(1))[0]
    ok(teeth.sum() >= 40, 'mouth: too few teeth texels')
    m = (a != SKIN).any(-1)
    ys, xs = np.where(m)
    print(f'mouth_grin: content x {xs.min()}..{xs.max()}, rows {ys.min()}-{ys.max()}, '
          f'teeth rows {ty.min()}-{ty.max()} ({int(teeth.sum())} texels)')

# 7. previews readable
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
