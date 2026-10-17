"""Independent spec check for Jaime's final face textures (shares no code
with make_textures.py).  Run:

    tools/.venv/bin/python -I verify_textures.py

Exits non-zero and prints FAIL lines if anything is off.
"""
import os
import sys
import numpy as np
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__))
SKIN = (0xDC, 0xA5, 0x88)          # art/jaime/character.json colors.skin
SKIN_SHADOW = (0xC4, 0x8C, 0x70)   # colors.skin_shadow
BROW = (0x24, 0x1A, 0x17)          # colors.eyebrows
LASH = (0x2A, 0x1E, 0x1C)
PALETTE = {  # the set's exact palette
    '#DCA588', '#C48C70', '#241A17', '#2A1E1C', '#3E2820', '#120C0C', '#FFFFFF',
    '#F2EEE6', '#C9716C', '#6E2A2A', '#FFFDF2'}
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
FILES = [n + '.png' for n in EYES] + ['mouth_grin.png', 'preview_sheet.png',
                                       'preview_face.png', 'make_textures.py']
BROW_ROWS = range(6, 11)    # first rendered row with Daniel's face_layout is 6
EYE_ROWS = range(12, 21)    # eyes (incl. the dead X) stay in this band
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
print(f'{"texture":12s} {"mode":4s} {"size":>6s} {"alpha":>5s} {"border":>6s} {"cols":>4s} {"mirror":>6s}  content bbox (x0,y0,x1,y1)')
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
    asym = int((m != m[:, ::-1]).sum())
    ok(im.mode == 'RGBA', f'{n}: mode {im.mode}')
    ok(im.size == exp, f'{n}: size {im.size} != {exp}')
    ok(int(a[..., 3].min()) == 255, f'{n}: alpha < 255 present')
    ok(bad_border == 0, f'{n}: {bad_border} border pixels not skin')
    if n != 'mouth_grin':   # the mouth's smirk is lopsided on purpose
        ok(asym == 0, f'{n}: left/right halves not mirror shapes')
    print(f'{n:12s} {im.mode:4s} {im.size[0]:>2d}x{im.size[1]:<3d} {int(a[..., 3].min()):>5d} '
          f'{bad_border:>6d} {len(cols):>4d} {asym:>6d}  {bb}')

# 3. palette + RGBA16 (5-bit) distinctness
ok(allcols <= PALETTE, f'off-palette colours: {sorted(allcols - PALETTE)}')
q = {tuple(int(h[i:i + 2], 16) >> 3 for i in (1, 3, 5)) for h in allcols}
ok(len(q) == len(allcols), 'some colours merge after RGBA16 quantisation')
print(f'colours used ({len(allcols)}): {" ".join(sorted(allcols))}; distinct in RGBA16: {len(q) == len(allcols)}')

# 4. brows and eye placement across the 8 states
if all(n in arr for n in EYES):
    ref = arr['eyes_open'][..., :3]
    ref_brow = (ref == BROW).all(-1)
    brow_rows = sorted(set(np.where(ref_brow.any(1))[0].tolist()))
    ok(brow_rows and set(brow_rows) <= set(BROW_ROWS), f'brow rows {brow_rows} outside 6-10')
    bys, bxs = np.where(ref_brow[:, :32])
    print(f'\nbrows: rows {brow_rows[0]}-{brow_rows[-1]}, left brow x {bxs.min()}..{bxs.max()} '
          f'({bxs.max() - bxs.min() + 1} wide), gap between brows x {bxs.max() + 1}..{62 - bxs.max()} '
          f'({62 - 2 * bxs.max()} px), {int(ref_brow.sum())} px')
    ref_eye = (ref != SKIN).any(-1) & ~ref_brow
    ref_lid = (ref == LASH).all(-1)
    print('state        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / eye px / brow px')
    for n in EYES:
        a = arr[n][..., :3]
        brow = (a == BROW).all(-1)
        eye = (a != SKIN).any(-1)
        eye[:11] = False                        # eye content = everything below the brows
        row = []
        for x0, x1 in ((0, 32), (32, 64)):
            ys, xs = np.where(eye[:, x0:x1])
            xs = xs + x0
            row.append(((xs.min(), ys.min(), xs.max(), ys.max()),
                        ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)))
        lid_d = int(((a == LASH).all(-1) != ref_lid).sum())
        eye_d = int((eye != ref_eye).sum())
        brow_d = int(((a[:11] != ref[:11]).any(-1)).sum())
        (lb, lc), (rb, rc) = row
        print(f'{n:12s} {str(tuple(map(int, lb))):17s} {str(tuple(map(int, rb))):17s} '
              f'({lc[0]:4.1f},{lc[1]:4.1f}) ({rc[0]:4.1f},{rc[1]:4.1f})   {lid_d:4d} / {eye_d:4d} / {brow_d:4d}')
        # brows (rows 0-10) identical in every state, nothing else up there
        ok(brow_d == 0, f'{n}: rows 0-10 differ from eyes_open (brows must not move)')
        ok(not ((a[:11] != SKIN).any(-1) & ~brow[:11]).any(), f'{n}: non-brow pixels in rows 0-10')
        # every state is centred on the same eye axes (x 14.5 / 48.5)
        ok(abs(lc[0] - 14.5) <= 0.5 and abs(rc[0] - 48.5) <= 0.5, f'{n}: eye not on the eye axis')
        ok(lb[1] >= EYE_ROWS[0] and lb[3] <= EYE_ROWS[-1], f'{n}: eye rows {lb[1]}-{lb[3]} outside 12-20')
        ok(not (a[11] != SKIN).any(), f'{n}: row 11 (brow/eye gap) not empty')
        if n in GAZE:
            ok(lid_d == 0 and eye_d == 0, f'{n}: lids/footprint differ from eyes_open')
            ok((a == (255, 255, 255)).all(-1).sum() == 6, f'{n}: glints missing')
    # half / closed keep the open eye's corner inks
    for n in ('eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((5, 17), (23, 17), (58, 17), (40, 17)):
            ok((a[y, x] == LASH).all(), f'{n}: corner ink missing at ({x},{y})')
    ys = np.where(ref_eye.any(1))[0]
    lx = np.where(ref_eye[:, :32].any(0))[0]
    print(f'\neyes_open eye rows {ys.min()}-{ys.max()}; left eye x {lx.min()}..{lx.max()} '
          f'({lx.max() - lx.min() + 1} wide), gap between eyes x {lx.max() + 1}..{62 - lx.max()} '
          f'({62 - 2 * lx.max()} px)')

# 5. mouth placement
if 'mouth_grin' in arr:
    a = arr['mouth_grin'][..., :3]
    m = (a != SKIN).any(-1)
    ys, xs = np.where(m)
    ok(ys.min() >= 2 and ys.max() <= 12, f'mouth rows {ys.min()}-{ys.max()} outside 2-12')
    ok(abs((xs.min() + xs.max()) / 2 - 15.5) <= 1.5, 'mouth not centred')
    teeth = int((a == (0xFF, 0xFD, 0xF2)).all(-1).sum())
    print(f'mouth: x {xs.min()}..{xs.max()} ({xs.max() - xs.min() + 1} wide), rows {ys.min()}-{ys.max()}, '
          f'{teeth} teeth px, {int((m != m[:, ::-1]).sum())} px asymmetric (smirk)')

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
