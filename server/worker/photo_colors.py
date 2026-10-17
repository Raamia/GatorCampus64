"""Colour samples from the uploaded photos, used to sanity-check the vision model's colours.

For each photo: find the face (OpenCV Haar cascade when cv2 is installed, else a centre /
upper-third heuristic for a selfie or portrait), take three crops relative to the face box
  skin: the cheeks / nose band inside the face box
  hair: a band over the top of the face box (forehead line and above)
  top:  below the chin (the shirt)
and run k-means (k=3, numpy) on each crop. The skin is the biggest cluster of the skin crop,
the hair the biggest cluster of the hair crop that is not skin-coloured, the top the biggest
cluster of the top crop. Per-photo samples are combined with a per-channel median.
"""
import io

import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 512  # sampling resolution (plenty for averages; keeps k-means fast)


# ------------------------------------------------------------------ colour maths
def hex_to_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def rgb_to_hex(rgb):
    r, g, b = (int(round(min(255, max(0, float(c))))) for c in rgb)
    return "#%02X%02X%02X" % (r, g, b)


def rgb_to_lab(rgb):
    """sRGB 0-255 (..., 3) -> CIE L*a*b* (D65)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e(hex_a, hex_b):
    """CIE76 colour difference of two #RRGGBB colours (about 2.3 = just noticeable)."""
    return float(np.linalg.norm(rgb_to_lab(hex_to_rgb(hex_a)) - rgb_to_lab(hex_to_rgb(hex_b))))


# ------------------------------------------------------------------ k-means
def kmeans(pixels, k=3, iters=25, seed=0):
    """Plain k-means (k-means++ init, fixed seed). pixels (N, 3) -> (centers (k, 3), counts (k,)),
    sorted by count, biggest cluster first. Fewer centers when there are fewer distinct pixels."""
    x = np.asarray(pixels, dtype=np.float64).reshape(-1, 3)
    if len(x) == 0:
        raise ValueError("no pixels")
    rng = np.random.default_rng(seed)
    if len(x) > 20000:
        x = x[rng.choice(len(x), 20000, replace=False)]
    k = min(k, len(np.unique(x, axis=0)))
    centers = [x[rng.integers(len(x))]]
    for _ in range(1, k):
        d2 = np.min(((x[:, None, :] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        centers.append(x[rng.choice(len(x), p=d2 / d2.sum())] if d2.sum() > 0 else x[rng.integers(len(x))])
    centers = np.array(centers)
    for _ in range(iters):
        labels = np.argmin(((x[:, None, :] - centers[None]) ** 2).sum(-1), axis=1)
        new = np.array([x[labels == i].mean(0) if np.any(labels == i) else centers[i] for i in range(k)])
        if np.allclose(new, centers, atol=0.1):
            centers = new
            break
        centers = new
    labels = np.argmin(((x[:, None, :] - centers[None]) ** 2).sum(-1), axis=1)
    counts = np.bincount(labels, minlength=k)
    order = np.argsort(-counts, kind="stable")
    return centers[order], counts[order]


# ------------------------------------------------------------------ face box + crops
def load_rgb(data):
    """bytes or path -> (H, W, 3) uint8, EXIF-rotated, longest side <= MAX_SIDE."""
    im = Image.open(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data)
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    return np.asarray(im)


def _haar_face(arr):
    try:
        import cv2
    except ImportError:
        return None
    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    det = cv2.CascadeClassifier(path)
    if det.empty():
        return None
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    faces = det.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                 minSize=(max(24, arr.shape[1] // 12),) * 2)
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return int(x), int(y), int(w), int(h)


def heuristic_face(arr):
    """Face box (x, y, w, h) for a selfie / portrait: centred, in the upper part of the frame."""
    h, w = arr.shape[:2]
    side = 0.42 * min(w, h)
    cx, cy = 0.5 * w, 0.40 * h
    return int(cx - side / 2), int(cy - side / 2), int(side), int(side)


def face_box(arr, use_cv=True):
    box = _haar_face(arr) if use_cv else None
    return (box, "haar") if box else (heuristic_face(arr), "heuristic")


def _crop(arr, x0, y0, x1, y1):
    h, w = arr.shape[:2]
    x0, x1 = int(max(0, min(w, x0))), int(max(0, min(w, x1)))
    y0, y1 = int(max(0, min(h, y0))), int(max(0, min(h, y1)))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return arr[y0:y1, x0:x1]


def crops(arr, box):
    x, y, w, h = box
    return {
        "skin": _crop(arr, x + 0.25 * w, y + 0.40 * h, x + 0.75 * w, y + 0.80 * h),
        "hair": _crop(arr, x + 0.05 * w, y - 0.30 * h, x + 0.95 * w, y + 0.12 * h),
        "top": _crop(arr, x - 0.25 * w, y + 1.45 * h, x + 1.25 * w, y + 2.3 * h),
    }


def sample_photo(arr, use_cv=True):
    """{role: hex} for one photo (roles whose crop falls outside the frame are missing)."""
    box, how = face_box(arr, use_cv)
    c = crops(arr, box)
    out = {"_face": how}
    if c["skin"] is not None:
        centers, _ = kmeans(c["skin"].reshape(-1, 3))
        out["skin"] = rgb_to_hex(centers[0])
    if c["hair"] is not None:
        centers, _ = kmeans(c["hair"].reshape(-1, 3))
        pick = centers[0]
        if "skin" in out:
            skin = hex_to_rgb(out["skin"])
            far = [cc for cc in centers if delta_e(rgb_to_hex(cc), rgb_to_hex(skin)) > 15]
            if far:
                pick = far[0]
        out["hair"] = rgb_to_hex(pick)
    if c["top"] is not None:
        centers, _ = kmeans(c["top"].reshape(-1, 3))
        out["top"] = rgb_to_hex(centers[0])
    return out


def sample_photos(images, use_cv=True):
    """images: list of bytes / paths / (H, W, 3) arrays -> {"skin", "hair", "top": hex} medians
    over the photos (missing roles omitted) plus "_faces": how each face box was found."""
    per = []
    for im in images:
        arr = im if isinstance(im, np.ndarray) else load_rgb(im)
        per.append(sample_photo(arr, use_cv))
    out = {"_faces": [p["_face"] for p in per]}
    for role in ("skin", "hair", "top"):
        vals = [hex_to_rgb(p[role]) for p in per if role in p]
        if vals:
            out[role] = rgb_to_hex(np.median(np.array(vals), axis=0))
    return out
