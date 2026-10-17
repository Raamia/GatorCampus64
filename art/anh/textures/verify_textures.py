"""Independent spec check for Anh's final face textures (shares no code with
make_textures.py; adapted from art/daniel/textures/verify_textures.py).  Run:

    tools/.venv/bin/python -I verify_textures.py
    ... verify_textures.py <dir> --spec <character.json>   (a re-skinned copy, e.g. Josh)

Exits non-zero and prints FAIL lines if anything is off.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('dir', nargs='?', default=HERE)
ap.add_argument('--spec', default=os.path.join(HERE, '..', 'character.json'))
args = ap.parse_args()
D = args.dir
with open(args.spec) as fh:
    COLORS = json.load(fh)['colors']


def rgb(h):
    h = h.lstrip('#').upper()
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


SKIN = rgb(COLORS['skin'])
SHADOW = rgb(COLORS['skin_shadow'])
HAIR = rgb(COLORS['hair'])
LASH = (0x2B, 0x1D, 0x1A)
GLINT = (0xFF, 0xFF, 0xFF)
SCLERA = (0xF4, 0xF0, 0xEA)
EYE_FIXED = {'#2B1D1A', '#3D2A22', '#110B0B', '#FFFFFF', '#F4F0EA'}   # lash iris pupil glint sclera
ANH_LIPS = {'#D08A7A', '#D47E72', '#84403A'}                          # upper lip, lower lip, lip line
IS_ANH = COLORS['skin'].upper() == '#E4AE8E'
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
FILES = [n + '.png' for n in EYES] + ['mouth_grin.png', 'preview_sheet.png', 'preview_face.png']
if D == HERE:
    FILES.append('make_textures.py')
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


def hexc(c):
    return '#%02X%02X%02X' % tuple(int(v) for v in c[:3])


def q5(c):
    return tuple(int(v) >> 3 for v in c[:3])


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
    # nothing within 2 texels of the edge (filtering + clamp safety margin)
    ok(bb[0] >= 2 and bb[1] >= 2 and bb[2] <= exp[0] - 3 and bb[3] <= exp[1] - 3, f'{n}: content too close to the edge')
    print(f'{n:12s} {im.mode:4s} {im.size[0]:>2d}x{im.size[1]:<3d} {int(a[..., 3].min()):>5d} '
          f'{bad_border:>6d} {len(cols):>4d}  {bb}')

# 3. palette + RGBA16 (5-bit) distinctness
spec_cols = {hexc(SKIN), hexc(SHADOW), hexc(HAIR)}
if IS_ANH:
    ok(allcols <= spec_cols | EYE_FIXED | ANH_LIPS, f'off-palette colours: {sorted(allcols - spec_cols - EYE_FIXED - ANH_LIPS)}')
else:  # re-skinned copy: spec colours + fixed eye colours + 3 skin-relative lip colours
    extra = allcols - spec_cols - EYE_FIXED
    ok(len(extra) <= 3, f'unexpected colours: {sorted(extra)}')
ok(len(allcols) <= 11, f'{len(allcols)} colours (palette should stay small, <= 11)')
q = {q5(rgb(h)) for h in allcols}
ok(len(q) == len(allcols), 'some colours merge after RGBA16 quantisation')
# the builder darkens skin_shadow texels to 0.70 x skin: that must stay distinct too
crease = tuple(int(round(v * 0.70)) for v in SKIN)
others = {q5(rgb(h)) for h in allcols if rgb(h) != SHADOW}
ok(q5(crease) not in others, 'darkened crease merges with another colour in RGBA16')
print(f'colours used ({len(allcols)}): {" ".join(sorted(allcols))}; distinct in RGBA16: {len(q) == len(allcols)}')

# 4. eye placement consistency across the 8 states
if all(n in arr for n in EYES):
    ref = arr['eyes_open'][..., :3]
    ref_foot = (ref != SKIN).any(-1)
    ref_lid = (ref == LASH).all(-1)
    print('\nstate        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / footprint px  glint px')
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
        glint = int((a == GLINT).all(-1).sum())
        (lb, lc), (rb, rc) = row
        print(f'{n:12s} {str(tuple(map(int, lb))):17s} {str(tuple(map(int, rb))):17s} '
              f'({lc[0]:4.1f},{lc[1]:4.1f}) ({rc[0]:4.1f},{rc[1]:4.1f})   {lid_d:4d} / {foot_d:4d}          {glint}')
        # every state sits on the same eye axes (x 14.5 / 48.5, like Daniel's)
        ok(abs(lc[0] - 14.5) <= 0.5 and abs(rc[0] - 48.5) <= 0.5, f'{n}: eye not on the eye axis')
        # content stays within the dead-X band (rows 11-19); open eye rows 12-18
        ok(lb[1] >= 11 and lb[3] <= 19, f'{n}: content rows {lb[1]}-{lb[3]} outside 11-19')
        if n in GAZE:
            ok(lid_d == 0 and foot_d == 0, f'{n}: lids/footprint differ from eyes_open')
        if n in GAZE + ['eyes_half']:
            ok(glint == 4, f'{n}: {glint} glint texels (want 2 per eye)')
            ok(int((a == SCLERA).all(-1).sum()) >= (4 if n == 'eyes_half' else 16), f'{n}: too little sclera')
        # the glint is on the same IMAGE side of the pupil in both eyes (mirror would flip it)
        if glint:
            gx = np.where((a == GLINT).all(-1))[1]
            px = np.where((a == (0x11, 0x0B, 0x0B)).all(-1))[1]
            for lo, hi in ((0, 32), (32, 64)):
                g_ = gx[(gx >= lo) & (gx < hi)]
                p_ = px[(px >= lo) & (px < hi)]
                if len(g_) and len(p_):
                    ok(g_.mean() < p_.mean(), f'{n}: glint not on the upper-left of the pupil')
    # open eye: sclera visible on BOTH sides of the iris (left eye, row 15)
    r = ref[15, :32]
    iris_x = [x for x in range(32) if tuple(r[x]) in ((0x3D, 0x2A, 0x22), (0x11, 0x0B, 0x0B), GLINT)]
    ok(iris_x and (r[iris_x[0] - 1] == SCLERA).all() and (r[iris_x[-1] + 1] == SCLERA).all(),
       'eyes_open: sclera not visible on both sides of the iris')
    # half / closed keep the open eye's corner inks (outer + inner corner, row 15)
    for n in ('eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((6, 15), (23, 15), (57, 15), (40, 15)):
            ok((a[y, x] == LASH).all(), f'{n}: corner ink missing at ({x},{y})')
    ys = np.where(ref_foot.any(1))[0]
    lx = np.where(ref_foot[:, :32].any(0))[0]
    ok((ys.min(), ys.max()) == (12, 18), f'eyes_open content rows {ys.min()}-{ys.max()} != 12-18')
    print(f'\neyes_open content rows {ys.min()}-{ys.max()} (centre {(ys.min() + ys.max()) / 2}); '
          f'left eye x {lx.min()}..{lx.max()} ({lx.max() - lx.min() + 1} wide), '
          f'gap between eyes x {lx.max() + 1}..{62 - lx.max()} ({62 - 2 * lx.max()} px)')

# 5. mouth: closed (no teeth / sclera colours), centred
if 'mouth_grin' in arr:
    a = arr['mouth_grin'][..., :3]
    ok(not (a == SCLERA).all(-1).any() and not (a == GLINT).all(-1).any(), 'mouth: white texels (should be closed)')
    m = (a != SKIN).any(-1)
    ys, xs = np.where(m)
    print(f'mouth content x {xs.min()}..{xs.max()} ({xs.max() - xs.min() + 1} wide), rows {ys.min()}..{ys.max()}')

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
