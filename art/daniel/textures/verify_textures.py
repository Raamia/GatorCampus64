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
        # every state is centred on the same eye axes (x 14.5 / 48.5)
        ok(abs(lc[0] - 14.5) <= 0.5 and abs(rc[0] - 48.5) <= 0.5, f'{n}: eye not on the eye axis')
        # content stays within the open eye's vertical band (+1 row for dead)
        ok(lb[1] >= 12 and lb[3] <= 20, f'{n}: content rows {lb[1]}-{lb[3]} outside 12-20')
        if n in GAZE:
            ok(lid_d == 0 and foot_d == 0, f'{n}: lids/footprint differ from eyes_open')
    # half / closed keep the open eye's corner inks (outer tail + corners)
    for n in ('eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((5, 18), (6, 18), (23, 18), (58, 18), (57, 18), (40, 18)):
            ok((a[y, x] == LASH).all(), f'{n}: corner ink missing at ({x},{y})')
    # open eye block vertically centred in the 32 rows
    ys = np.where(ref_foot.any(1))[0]
    lx = np.where(ref_foot[:, :32].any(0))[0]
    ok((ys.min() + ys.max()) / 2 == 15.5, f'eyes_open content rows {ys.min()}-{ys.max()} not centred')
    print(f'\neyes_open content rows {ys.min()}-{ys.max()} (centre {(ys.min() + ys.max()) / 2}, '
          f'texture centre 15.5); left eye x {lx.min()}..{lx.max()} ({lx.max() - lx.min() + 1} wide), '
          f'gap between eyes x {lx.max() + 1}..{62 - lx.max()} ({62 - 2 * lx.max()} px)')

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
