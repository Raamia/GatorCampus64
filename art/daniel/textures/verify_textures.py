"""Independent spec check for Daniel's final face textures (shares no code
with make_textures.py).  Run:

    tools/.venv/bin/python -I verify_textures.py

Exits non-zero and prints FAIL lines if anything is off.
"""
import os
import sys
import numpy as np
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
SKIN = (0xD9, 0x9C, 0x7E)
BRIEF = {  # the brief's exact palette
    '#D99C7E', '#C4876B', '#1E1A20', '#2A1E1C', '#3A2620', '#120C0C', '#FFFFFF',
    '#F2EEE6', '#C27766', '#6E2A2A', '#FFFDF2', '#B5535A'}
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
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
ok(allcols <= BRIEF, f'off-brief colours: {sorted(allcols - BRIEF)}')
q = {tuple(int(h[i:i + 2], 16) >> 3 for i in (1, 3, 5)) for h in allcols}
ok(len(q) == len(allcols), 'some colours merge after RGBA16 quantisation')
print(f'colours used ({len(allcols)}): {" ".join(sorted(allcols))}; distinct in RGBA16: {len(q) == len(allcols)}')

# 4. eye placement consistency across the 8 states
if all(n in arr for n in EYES):
    LASH = (0x2A, 0x1E, 0x1C)
    ref = arr['eyes_open'][..., :3]
    ref_foot = (ref != SKIN).any(-1)
    ref_lid = (ref == LASH).all(-1)
    print('\nstate        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / footprint px')
    for n in EYES:
        a = arr[n][..., :3]
        foot = (a != SKIN).any(-1)
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
        # every state is centred on the same eye axes (x 13 / 50: eyes x 6-20 and 43-57)
        ok(abs(lc[0] - 13.0) <= 0.5 and abs(rc[0] - 50.0) <= 0.5, f'{n}: eye not on the eye axis')
        # content stays within the open eye's vertical band (+1 row for dead)
        ok(lb[1] >= 12 and lb[3] <= 20, f'{n}: content rows {lb[1]}-{lb[3]} outside 12-20')
        if n in GAZE:
            ok(lid_d == 0 and foot_d == 0, f'{n}: lids/footprint differ from eyes_open')
    # half / closed keep the open eye's corner inks (outer corner row 15, inner row 16)
    for n in ('eyes_open', 'eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((6, 15), (7, 15), (19, 16), (20, 16), (57, 15), (56, 15), (44, 16), (43, 16)):
            ok((a[y, x] == LASH).all(), f'{n}: corner ink missing at ({x},{y})')
    # likeness review: narrow eyes set wide apart, about 15 x 5 texels with ~22 texels
    # between the inner corners, white runs of at most 1 texel (the polish pass keeps one
    # white texel per eye, at the outer corner)
    ys = np.where(ref_foot.any(1))[0]
    lx = np.where(ref_foot[:, :32].any(0))[0]
    width, height, gap = lx.max() - lx.min() + 1, ys.max() - ys.min() + 1, 62 - 2 * lx.max()
    ok(width == 15 and height == 5, f'eyes_open eye is {width}x{height}, expected 15x5')
    ok(gap == 22, f'eyes_open gap between the inner corners is {gap}, expected 22')
    ok(abs((ys.min() + ys.max()) / 2 - 15.5) <= 0.5, f'eyes_open content rows {ys.min()}-{ys.max()} not centred')
    SCLERA = (0xF2, 0xEE, 0xE6)
    white = (ref == SCLERA).all(-1)
    for y in range(32):
        for x0, x1 in ((0, 32), (32, 64)):
            xs = np.where(white[y, x0:x1])[0]
            if len(xs):
                runs = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)
                ok(max(len(r) for r in runs) <= 1, f'eyes_open: white run longer than 1 texel in row {y}')
    print(f'\neyes_open content rows {ys.min()}-{ys.max()} (centre {(ys.min() + ys.max()) / 2}, '
          f'texture centre 15.5); left eye x {lx.min()}..{lx.max()} ({width} x {height}), '
          f'gap between eyes x {lx.max() + 1}..{62 - lx.max()} ({gap} px), '
          f'white texels per eye {int(white[:, :32].sum())}')
    # polish review: the eye must not read as a dark bar with a row of evenly spaced
    # light dots, the blink's middle frame must read, the cheek shadow stays under the
    # eye, the dead X is an X (no horizontal bar through it)
    GLINT_C = (0xFF, 0xFF, 0xFF)
    SHADOW = (0xC4, 0x87, 0x6B)
    DARK = [LASH, (0x3A, 0x26, 0x20), (0x12, 0x0C, 0x0C)]

    def dark_rows(a):
        d = np.zeros(a.shape[:2], bool)
        for c in DARK:
            d |= (a[..., :3] == c).all(-1)
        return [y for y in range(32) if d[y, :32].sum() >= 8]

    lights = white | (ref == GLINT_C).all(-1)
    lrows = sorted({int(y) for y in np.where(lights[:, :32])[0]})
    ok(len(lrows) >= 2 or lights[:, :32].sum() <= 1,
       f'eyes_open: light texels {int(lights[:, :32].sum())} all on row(s) {lrows} (a row of dots)')
    ok(int(white[:, :32].sum()) <= 1, f'eyes_open: {int(white[:, :32].sum())} white texels per eye (<= 1)')
    hb = arr['eyes_half'][..., :3]
    ok(not (hb == GLINT_C).all(-1).any(), 'eyes_half: glint visible (the lid should cover the pupil)')
    dr_open, dr_half = dark_rows(ref), dark_rows(hb)
    ok(len(dr_half) <= 2 and len(dr_half) < len(dr_open),
       f'eyes_half: {len(dr_half)} dark rows vs {len(dr_open)} open (does not read as a half blink)')
    for n in EYES:
        if n == 'eyes_dead':
            continue
        sh = (arr[n][..., :3] == SHADOW).all(-1)
        need = 5 if n == 'eyes_closed' else 9
        ok(int(sh[17, :32].sum()) >= need and int(sh[17, 32:].sum()) >= need,
           f'{n}: lower-lid cheek shadow (row 17) missing')
    db = arr['eyes_dead'][..., :3]
    hm = (db != SKIN).any(-1)
    for y in range(32):
        xs = np.where(hm[y, :32])[0]
        if len(xs):
            runs = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)
            ok(max(len(r) for r in runs) <= 3, f'eyes_dead: {max(len(r) for r in runs)}-texel bar in row {y}')
    ys_d = np.where(hm.any(1))[0]
    ok((hm[ys_d.min():ys_d.max() + 1] == hm[ys_d.min():ys_d.max() + 1][::-1]).all(),
       'eyes_dead: X not symmetric top/bottom')
    print(f'eyes_open light texels per eye on rows {lrows}; dark rows open {dr_open} / half {dr_half}; '
          f'dead X rows {ys_d.min()}-{ys_d.max()}')

# 5. previews readable
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
