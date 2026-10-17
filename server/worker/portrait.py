"""64x64 character-select portrait from the builder's preview renders.

Matches mods/sgl64/textures/sgl_portrait_<id>.png: opaque RGBA 64x64, the head (hair top to
just below the chin, a bit of shoulders) filling the frame, on a saturated card colour with a
soft radial vignette (charselect.lua CARD_COLORS are those backgrounds).

Source: previews/head.png (the builder's head close-up, already framed like the portraits);
falls back to a crop of previews/front.png (a square of 0.56x the figure's height from its top).
The flat grey render background (sgl_preview, #6B7078) is keyed out with a soft edge and
replaced by the card colour.
"""
import hashlib
import os

import numpy as np
from PIL import Image

SIZE = 64
# charselect.lua CARD_COLORS (same saturation family); pick_card_color avoids the hair/top hues
CARD_COLORS = [(232, 88, 56), (240, 112, 176), (250, 140, 32), (64, 172, 236), (72, 196, 112),
               (152, 100, 224), (240, 200, 40), (56, 96, 208), (216, 40, 64), (40, 188, 188)]
KEY_NEAR, KEY_FAR = 10.0, 40.0  # RGB distance from the background: <= near -> bg, >= far -> figure


def _rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def pick_card_color(seed, avoid=()):
    """A CARD_COLORS entry, deterministic per seed, far from the colours in avoid (hex)."""
    avoid = [_rgb(a) for a in avoid if a]
    start = int(hashlib.sha1(str(seed).encode()).hexdigest(), 16) % len(CARD_COLORS)
    order = CARD_COLORS[start:] + CARD_COLORS[:start]
    if not avoid:
        return order[0]
    best = max(order, key=lambda c: min(np.linalg.norm(np.array(c) - a) for a in avoid))
    # keep the hash choice when it is already clearly distinct
    first_ok = min(np.linalg.norm(np.array(order[0]) - a) for a in avoid) > 120
    return order[0] if first_ok else best


def background_color(arr):
    corners = np.concatenate([arr[:4, :4].reshape(-1, 3), arr[:4, -4:].reshape(-1, 3),
                              arr[-4:, :4].reshape(-1, 3), arr[-4:, -4:].reshape(-1, 3)])
    return np.median(corners, axis=0)


def figure_mask(arr, bg):
    """Soft alpha 0..1 of the figure against the flat background."""
    d = np.linalg.norm(arr.astype(np.float64) - bg[None, None], axis=-1)
    return np.clip((d - KEY_NEAR) / (KEY_FAR - KEY_NEAR), 0.0, 1.0)


def head_box_from_front(arr, bg):
    """Square crop (x0, y0, side) around the head in a full-body front render."""
    m = figure_mask(arr, bg) > 0.5
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        h, w = arr.shape[:2]
        return 0, 0, min(h, w)
    top, bottom = ys.min(), ys.max()
    fig_h = bottom - top
    band = m[top:int(top + 0.3 * fig_h)]  # hair + face only (no arms)
    cols = np.nonzero(band.any(axis=0))[0]
    cx = (cols.min() + cols.max()) / 2 if len(cols) else (xs.min() + xs.max()) / 2
    side = int(0.56 * fig_h)  # head plus a little shoulder, like head.png
    y0 = int(top - 0.04 * side)
    return int(cx - side / 2), y0, side


def _card_background(color, size):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    r = np.hypot(xx - size / 2 + 0.5, yy - size * 0.45) / (size * 0.75)
    shade = 1.08 - 0.38 * np.clip(r, 0, 1) ** 1.5  # brighter centre, darker corners
    return np.clip(np.array(color, dtype=np.float64)[None, None] * shade[..., None], 0, 255)


def _square_crop(img, x0, y0, side, fill):
    canvas = Image.new("RGB", (side, side), tuple(int(c) for c in fill))
    canvas.paste(img.crop((max(0, x0), max(0, y0), x0 + side, y0 + side)), (max(0, -x0), max(0, -y0)))
    return canvas


def make_portrait(previews_dir, out_path, card_color=(232, 88, 56)):
    """Write the 64x64 portrait; returns {"source", "card_color"}."""
    head = os.path.join(previews_dir, "head.png")
    front = os.path.join(previews_dir, "front.png")
    if os.path.isfile(head):
        img = Image.open(head).convert("RGB")
        arr = np.asarray(img)
        bg = background_color(arr)
        w, h = img.size
        side = int(min(w, h) * 0.96)  # a little tighter, hair near the top edge as in the friends' cards
        img = _square_crop(img, (w - side) // 2, int((h - side) * 0.25), side, bg)
        source = "head.png"
    elif os.path.isfile(front):
        img = Image.open(front).convert("RGB")
        arr = np.asarray(img)
        bg = background_color(arr)
        x0, y0, side = head_box_from_front(arr, bg)
        img = _square_crop(img, x0, y0, side, bg)
        source = "front.png"
    else:
        raise FileNotFoundError(f"no head.png or front.png in {previews_dir}")
    small = np.asarray(img.resize((SIZE, SIZE), Image.LANCZOS)).astype(np.float64)
    alpha = figure_mask(small, bg)[..., None]
    out = small * alpha + _card_background(card_color, SIZE) * (1 - alpha)
    rgba = np.concatenate([np.clip(np.round(out), 0, 255), np.full((SIZE, SIZE, 1), 255.0)], axis=-1)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    Image.fromarray(rgba.astype(np.uint8), "RGBA").save(out_path)
    return {"source": source, "card_color": list(card_color)}
