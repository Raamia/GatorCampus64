"""Make the 8 placeholder guest actors + portraits for mods/sgl64 (web platform spec §5.2).

actors/guest_<n>/: a copy of actors/donald (the plainest friend: no accessories, the smallest export)
with every symbol prefix donald_ -> guest_<n>_ (root GeoLayout guest_<n>_geo) and grey hair, so a
placeholder is recognisably "not Donald". textures/sgl_portrait_guest_<n>.png: a 64x64 neutral card
with a "?" gator silhouette, plus the DynOS .tex beside it (u8 type 2, u8 name length, name, s32 PNG
size, PNG bytes: dynos_bin_tex.cpp DynOS_Tex_WriteBinary), like the friends' portraits. Also checks
that every committed .tex in textures/ is exactly that wrapping of its .png.

Usage: python3 tools/web/make_guest_placeholders.py [mods/sgl64]      (needs Pillow)
Then: python3 tools/blender/validate_export.py mods/sgl64/actors/guest_<n> guest_<n>
"""
import io
import os
import re
import struct
import sys

from PIL import Image, ImageDraw

MOD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mods", "sgl64")
SRC = "donald"
ACT = os.path.join(MOD, "actors")
TEX = os.path.join(MOD, "textures")

HAIR_OLD = re.compile(r"(Lights1 %s_Hair__HAIR__lights = gdSPDefLights1\(\n)\t[^\n]*\n\t[^\n]*\);" % SRC)
HAIR_NEW = "\\g<1>\t0x3C, 0x3C, 0x40,\n\t0x78, 0x78, 0x80, 0x28, 0x28, 0x28);"

for n in range(1, 9):
    gid = "guest_%d" % n
    out = os.path.join(ACT, gid)
    os.makedirs(out, exist_ok=True)
    for name in ("geo_header.h", "geo.inc.c", "model.inc.c"):
        text = open(os.path.join(ACT, SRC, name)).read()
        if name == "model.inc.c":
            text, k = HAIR_OLD.subn(HAIR_NEW, text)
            assert k == 1, "hair lights not found"
        text = text.replace(SRC + "_", gid + "_")
        assert SRC not in text.lower(), name
        open(os.path.join(out, name), "w").write(text)


def portrait(n):
    s = 4  # draw at 256 and downscale for smooth edges
    im = Image.new("RGB", (64 * s, 64 * s), (128, 128, 150))
    d = ImageDraw.Draw(im)
    # soft stripes like the coloured fallback card
    for k in range(5):
        d.rectangle([0, (k * 13 + 4) * s, 64 * s, (k * 13 + 7) * s], fill=(146, 146, 166))
    # gator head silhouette (snout to the right), dark slate
    body = (58, 74, 70)
    d.ellipse([10 * s, 18 * s, 40 * s, 50 * s], fill=body)                 # head
    d.rounded_rectangle([28 * s, 30 * s, 58 * s, 46 * s], 6 * s, fill=body)  # snout
    d.ellipse([18 * s, 12 * s, 28 * s, 24 * s], fill=body)                 # eye bump
    d.ellipse([20 * s, 15 * s, 25 * s, 20 * s], fill=(235, 235, 235))
    for x in range(32, 56, 6):                                             # teeth
        d.polygon([(x * s, 38 * s), ((x + 3) * s, 38 * s), ((x + 1.5) * s, 42 * s)], fill=(235, 235, 235))
    # big "?" badge
    d.ellipse([38 * s, 4 * s, 60 * s, 26 * s], fill=(250, 110, 30))
    d.arc([43 * s, 7 * s, 55 * s, 17 * s], 180, 30, fill=(255, 255, 255), width=3 * s)
    d.line([(49 * s, 16 * s), (49 * s, 19 * s)], fill=(255, 255, 255), width=3 * s)
    d.ellipse([47.5 * s, 21 * s, 50.5 * s, 24 * s], fill=(255, 255, 255))
    # slot number, bottom-left
    d.rectangle([3 * s, 52 * s, 15 * s, 62 * s], fill=(10, 22, 70))
    digits = {
        1: ["010", "110", "010", "010", "111"], 2: ["111", "001", "111", "100", "111"],
        3: ["111", "001", "111", "001", "111"], 4: ["101", "101", "111", "001", "001"],
        5: ["111", "100", "111", "001", "111"], 6: ["111", "100", "111", "101", "111"],
        7: ["111", "001", "010", "010", "010"], 8: ["111", "101", "111", "101", "111"],
    }
    for r, row in enumerate(digits[n]):
        for c, ch in enumerate(row):
            if ch == "1":
                d.rectangle([(6 + c * 2) * s, (53 + r * 2 - 0.5) * s, (8 + c * 2) * s - 1, (55 + r * 2 - 0.5) * s - 1],
                            fill=(255, 214, 40))
    return im.resize((64, 64), Image.LANCZOS)


for n in range(1, 9):
    name = "sgl_portrait_guest_%d" % n
    buf = io.BytesIO()
    portrait(n).save(buf, "PNG", optimize=True)
    png = buf.getvalue()
    open(os.path.join(TEX, name + ".png"), "wb").write(png)
    tex = bytes([2, len(name)]) + name.encode() + struct.pack("<i", len(png)) + png
    open(os.path.join(TEX, name + ".tex"), "wb").write(tex)

# the .tex layout matches the committed friends' portraits
for f in os.listdir(TEX):
    if f.endswith(".tex"):
        t = open(os.path.join(TEX, f), "rb").read()
        nm = f[:-4]
        p = open(os.path.join(TEX, nm + ".png"), "rb").read()
        assert t == bytes([2, len(nm)]) + nm.encode() + struct.pack("<i", len(p)) + p, f
print("ok")
