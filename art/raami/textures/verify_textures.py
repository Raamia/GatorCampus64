"""Independent spec check for Raami's face textures (shares no code with
make_textures.py; adapted from Daniel's verify_textures.py).  Run:

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


SKIN = rgb(SPEC['colors']['skin'])
SHADOW = rgb(SPEC['colors']['skin_shadow'])
BROW = rgb(SPEC['colors']['eyebrows'])
LASH = rgb(SPEC['colors']['hair'])
ALLOWED = {  # the face palette (spec colours + eye / lip colours)
    '#D8A07E', '#C08766', '#2A1D1B', '#1B171A', '#36211A', '#140D0E', '#FFFFFF',
    '#E9E3DA', '#AA695B', '#C07D6F', '#6B3132', '#8A6450'}
EYES = ['eyes_open', 'eyes_half', 'eyes_closed', 'eyes_left', 'eyes_right',
        'eyes_up', 'eyes_down', 'eyes_dead']
GAZE = ['eyes_open', 'eyes_left', 'eyes_right', 'eyes_up', 'eyes_down']
FILES = [n + '.png' for n in EYES] + ['mouth_grin.png', 'preview_sheet.png',
                                       'preview_face.png', 'make_textures.py']
BROW_ROWS = (5, 8)        # brows live here in every state
EYE_ROWS = (10, 20)       # everything else of the eye texture lives here
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


def hexc(c):
    return '#%02X%02X%02X' % tuple(int(v) for v in c[:3])


ok(SPEC['colors']['skin'].upper() in ALLOWED and SPEC['colors']['skin_shadow'].upper() in ALLOWED
   and SPEC['colors']['eyebrows'].upper() in ALLOWED and SPEC['colors']['hair'].upper() in ALLOWED,
   'spec colours changed: update ALLOWED / redraw')

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
    # skin is the most common colour (it is the background the builder keys away)
    vals, cnt = np.unique(a[..., :3].reshape(-1, 3), axis=0, return_counts=True)
    ok(tuple(vals[np.argmax(cnt)]) == SKIN, f'{n}: background is not the skin colour')
    print(f'{n:12s} {im.mode:4s} {im.size[0]:>2d}x{im.size[1]:<3d} {int(a[..., 3].min()):>5d} '
          f'{bad_border:>6d} {len(cols):>4d}  {bb}')

# 3. palette + RGBA16 (5-bit) distinctness
ok(allcols <= ALLOWED, f'off-palette colours: {sorted(allcols - ALLOWED)}')
q = {tuple(int(h[i:i + 2], 16) >> 3 for i in (1, 3, 5)) for h in allcols}
ok(len(q) == len(allcols), 'some colours merge after RGBA16 quantisation')
print(f'colours used ({len(allcols)}): {" ".join(sorted(allcols))}; distinct in RGBA16: {len(q) == len(allcols)}')

# 4. brows + eye placement consistency across the 8 states
if all(n in arr for n in EYES):
    ref = arr['eyes_open'][..., :3]
    ref_brow = (ref == BROW).all(-1)
    eye_band = np.zeros(ref.shape[:2], bool)
    eye_band[EYE_ROWS[0]:EYE_ROWS[1] + 1] = True
    ref_foot = (ref != SKIN).any(-1) & eye_band
    ref_lid = (ref == LASH).all(-1)
    ys, xs = np.where(ref_brow)
    ok(ref_brow.any(), 'no brows drawn')
    ok(ys.min() >= BROW_ROWS[0] and ys.max() <= BROW_ROWS[1], f'brows outside rows {BROW_ROWS}')
    lb = np.where(ref_brow[:, :32].any(0))[0]
    print(f'\nbrows: rows {ys.min()}-{ys.max()}, left brow x {lb.min()}..{lb.max()}, '
          f'gap between brows x {lb.max() + 1}..{62 - lb.max()} ({62 - 2 * lb.max()} px)')
    print('state        L-eye bbox        R-eye bbox        L centre     R centre   vs open: lid px / footprint px / brow px')
    for n in EYES:
        a = arr[n][..., :3]
        brow = (a == BROW).all(-1)
        nonskin = (a != SKIN).any(-1)
        ok(not (nonskin & ~eye_band & ~brow).any(), f'{n}: ink outside the brow and eye bands')
        ok(not (brow & eye_band).any(), f'{n}: brow colour inside the eye band')
        foot = nonskin & eye_band
        row = []
        for x0, x1 in ((0, 32), (32, 64)):
            ys, xs = np.where(foot[:, x0:x1])
            xs = xs + x0
            row.append(((xs.min(), ys.min(), xs.max(), ys.max()),
                        ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)))
        lid_d = int(((a == LASH).all(-1) != ref_lid).sum())
        foot_d = int((foot != ref_foot).sum())
        brow_d = int((brow != ref_brow).sum())
        (lb_, lc), (rb, rc) = row
        print(f'{n:12s} {str(tuple(map(int, lb_))):17s} {str(tuple(map(int, rb))):17s} '
              f'({lc[0]:4.1f},{lc[1]:4.1f}) ({rc[0]:4.1f},{rc[1]:4.1f})   {lid_d:4d} / {foot_d:4d} / {brow_d:4d}')
        ok(brow_d == 0, f'{n}: brows differ from eyes_open')
        # every state is centred on the same eye axes (x 14.5 / 48.5)
        ok(abs(lc[0] - 14.5) <= 0.5 and abs(rc[0] - 48.5) <= 0.5, f'{n}: eye not on the eye axis')
        if n in GAZE:
            ok(lid_d == 0 and foot_d == 0, f'{n}: lids/footprint differ from eyes_open')
    # half / closed keep the open eye's corner inks
    for n in ('eyes_half', 'eyes_closed'):
        a = arr[n][..., :3]
        for (x, y) in ((5, 15), (6, 16), (23, 15), (58, 15), (57, 16), (40, 15)):
            ok((a[y, x] == LASH).all(), f'{n}: corner ink missing at ({x},{y})')
    # the open eye: an opening with whites on both sides of the iris
    W_ = (ref == rgb('#E9E3DA')).all(-1)
    for x0, x1, nm in ((0, 32, 'left'), (32, 64, 'right')):
        ws = np.where(W_[:, x0:x1].any(0))[0]
        ok(len(ws) and (ws.min() < 10 and ws.max() > 19), f'eyes_open {nm}: whites not on both sides')
    lx = np.where(ref_foot[:, :32].any(0))[0]
    lash_rows = np.where(ref_lid.any(1))[0]
    print(f'\neyes_open: lash rows {lash_rows.min()}-{lash_rows.max()}, left eye x {lx.min()}..{lx.max()} '
          f'({lx.max() - lx.min() + 1} wide incl. lash), gap between eyes x {lx.max() + 1}..{62 - lx.max()} '
          f'({62 - 2 * lx.max()} px)')

# 5. mouth: closed (no teeth / interior colour), lip line present, centred
if 'mouth_grin' in arr:
    a = arr['mouth_grin'][..., :3]
    line = (a == rgb('#6B3132')).all(-1)
    ok(line.any(), 'mouth: no lip line')
    ys, xs = np.where((a != SKIN).any(-1))
    ok(abs((xs.min() + xs.max()) / 2 - 15.5) < 0.01, 'mouth not centred')
    ok(not ((a == (255, 255, 255)).all(-1)).any(), 'mouth: white texels (teeth) in a closed mouth')
    print(f'mouth: content x {xs.min()}..{xs.max()} rows {ys.min()}..{ys.max()}, '
          f'lip line rows {sorted(set(np.where(line)[0].tolist()))}')

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
