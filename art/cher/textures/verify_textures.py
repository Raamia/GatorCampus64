"""Independent spec check for Cher's final face textures (shares no code
with make_textures.py; adapted from art/daniel/textures/verify_textures.py).
Run:

    tools/.venv/bin/python -I verify_textures.py

Exits non-zero and prints FAIL lines if anything is off.
"""
import json
import os
import sys
import numpy as np
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(D, '..', 'character.json')) as fh:
    SPEC = json.load(fh)['colors']


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


SKIN = rgb(SPEC['skin'])
SHADOW = rgb(SPEC['skin_shadow'])
BROW = (0x4E, 0x36, 0x31)
LASH = (0x22, 0x18, 0x19)
PALETTE = {  # the set's exact palette (skin + skin_shadow from the spec)
    '#%02X%02X%02X' % SKIN, '#%02X%02X%02X' % SHADOW,
    '#4E3631', '#221819', '#46291F', '#120C0C', '#FFFFFF', '#EEE7DF',
    '#B8606A', '#D97C88', '#5E2430', '#FFFDF2'}
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
AXES = (13.5, 49.5)          # eye centre columns (corners x 5..22 / 41..58)
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

# 4. eye placement consistency across the 8 states
if all(n in arr for n in EYES):
    ref = arr['eyes_open'][..., :3]
    ref_brow = (ref == BROW).all(-1)
    ref_eye = (ref != SKIN).any(-1) & ~ref_brow
    ref_lid = (ref == LASH).all(-1)
    by, bx = np.where(ref_brow)
    ok(len(by) > 0, 'eyes_open: no brows')
    print(f'\nbrows: rows {by.min()}-{by.max()}, left brow x {bx[bx < 32].min()}..{bx[bx < 32].max()}')
    print('state        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / eye px / brow px')
    spans = {}
    for n in EYES:
        a = arr[n][..., :3]
        brow = (a == BROW).all(-1)
        eye = (a != SKIN).any(-1) & ~brow
        row = []
        for x0, x1 in ((0, 32), (32, 64)):
            ys, xs = np.where(eye[:, x0:x1])
            xs = xs + x0
            row.append(((xs.min(), ys.min(), xs.max(), ys.max()),
                        ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)))
        lid_d = int(((a == LASH).all(-1) != ref_lid).sum())
        eye_d = int((eye != ref_eye).sum())
        brow_d = int((brow != ref_brow).sum())
        (lb, lc), (rb, rc) = row
        spans[n] = (lb[0], lb[2])
        print(f'{n:12s} {str(tuple(map(int, lb))):17s} {str(tuple(map(int, rb))):17s} '
              f'({lc[0]:4.1f},{lc[1]:4.1f}) ({rc[0]:4.1f},{rc[1]:4.1f})   {lid_d:4d} / {eye_d:4d} / {brow_d:4d}')
        # every state is centred on the same eye axes
        ok(abs(lc[0] - AXES[0]) <= 0.5 and abs(rc[0] - AXES[1]) <= 0.5, f'{n}: eye not on the eye axis')
        # eye content stays in the eye band (rows 11-19), clear of the brows
        ok(lb[1] >= 11 and lb[3] <= 19, f'{n}: eye rows {lb[1]}-{lb[3]} outside 11-19')
        ok(lb[1] - by.max() >= 3, f'{n}: eye ink closer than 3 rows to the brows')
        # brows identical in every state (they must not jump during a blink)
        ok(brow_d == 0, f'{n}: brows differ from eyes_open')
        if n in GAZE:
            ok(lid_d == 0 and eye_d == 0, f'{n}: lids/footprint differ from eyes_open')
    # half / closed span the open eye's full corner-to-corner width
    for n in ('eyes_half', 'eyes_closed'):
        ok(spans[n] == spans['eyes_open'], f'{n}: span x {spans[n]} != open {spans["eyes_open"]}')
    ys = np.where(ref_eye.any(1))[0]
    lx = np.where(ref_eye[:, :32].any(0))[0]
    w = lx.max() - lx.min() + 1
    gap = 62 - 2 * lx.max()
    ok(abs(gap - w) <= 2, f'eye gap {gap} px is not about one eye-width ({w} px)')
    print(f'\neyes_open eye rows {ys.min()}-{ys.max()}; left eye x {lx.min()}..{lx.max()} ({w} wide), '
          f'gap between eyes x {lx.max() + 1}..{62 - lx.max()} ({gap} px)')

# 5. mouth: lips, teeth and corners present, inside the texture with a margin
if 'mouth_grin' in arr:
    a = arr['mouth_grin'][..., :3]
    m = (a != SKIN).any(-1)
    ys, xs = np.where(m)
    for c, what in (('#FFFDF2', 'teeth'), ('#D97C88', 'lower lip'), ('#B8606A', 'upper lip'), ('#5E2430', 'corners')):
        ok((a == rgb(c)).all(-1).any(), f'mouth_grin: no {what}')
    print(f'mouth_grin: x {xs.min()}..{xs.max()} ({xs.max() - xs.min() + 1} wide), rows {ys.min()}-{ys.max()}')

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
