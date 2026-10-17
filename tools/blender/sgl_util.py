# Small dependency-free helpers shared by the character builder modules
# (colour conversion and a minimal PNG writer). Safe to import outside Blender.
import json
import os
import struct
import zlib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEMPLATE_BLEND = os.path.join(PROJECT_ROOT, "tools", "vendor", "template", "Mario Coop Model Template.blend")


def art_root():
    """Directory holding the per-character art folders (<root>/<id>/character.json):
    the repo's art/ unless SGL_ART_DIR points somewhere else (e.g. the web worker's
    per-job temp dir; build_character.py --art-dir sets it)."""
    return os.path.abspath(os.environ.get("SGL_ART_DIR") or os.path.join(PROJECT_ROOT, "art"))


def art_dir(char_id):
    return os.path.join(art_root(), char_id)


def build_dir(char_id):
    return os.path.join(art_dir(char_id), "build")


def actors_dir():
    return os.path.join(PROJECT_ROOT, "mods", "sgl64", "actors")


def load_spec(char_id):
    path = os.path.join(art_dir(char_id), "character.json")
    with open(path) as f:
        spec = json.load(f)
    if spec.get("id", char_id) != char_id:
        raise ValueError(f"{path}: id {spec.get('id')!r} does not match {char_id!r}")
    spec.setdefault("id", char_id)
    spec.setdefault("build", {})
    spec.setdefault("colors", {})
    return spec


# ------------------------------------------------------------------ colours
def hex_to_rgb8(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_srgb(h):
    return tuple(c / 255.0 for c in hex_to_rgb8(h))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_linear(h):
    return tuple(srgb_to_linear(c) for c in hex_to_srgb(h))


def shade_hex(h, factor):
    """Multiply an sRGB hex colour by factor (in sRGB space) and return hex."""
    r, g, b = hex_to_rgb8(h)
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c * factor))) for c in (r, g, b))


def mix_hex(a, b, t):
    ra, ga, ba = hex_to_rgb8(a)
    rb, gb, bb = hex_to_rgb8(b)
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in ((ra, rb), (ga, gb), (ba, bb)))


# ------------------------------------------------------------------ PNG
def write_png(path, rows):
    """rows: list (top to bottom) of lists of (r, g, b, a) 0-255 tuples."""
    h = len(rows)
    w = len(rows[0])
    raw = bytearray()
    for row in rows:
        if len(row) != w:
            raise ValueError("ragged image rows")
        raw.append(0)
        for px in row:
            raw.extend(bytes(px))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def upscale(rows, k):
    out = []
    for row in rows:
        big = []
        for px in row:
            big.extend([px] * k)
        for _ in range(k):
            out.append(list(big))
    return out
