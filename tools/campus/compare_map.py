"""Side-by-side + overlay of the planner's stage map and the top-down preview render, cropped to the
same stage window, to check alignment.

Usage: tools/.venv/bin/python -I tools/campus/compare_map.py <stage_key> <topdown.png> <out.png>
The top-down render covers the stage centre +- extent_half_m (stage_data.EXTENT_HALF_M); the
planner's stage map (art/campus/stage_<key>.png) covers the window + 30 m at 1900 px wide.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from stage_data import EXTENT_HALF_M  # noqa: E402


def main():
    key, top_path, out_path = sys.argv[1:4]
    stages = json.load(open(os.path.join(ROOT, "data", "uf", "stages.json")))
    st = next(s for s in stages["stages"] if s["key"] == key)
    b = st["bounds_m"]
    cx, cy = st["center_m"]
    # planner map: Canvas(xmin - 30, ymin - 30, xmax + 30, ymax + 30, 1900 px) (+ legend panel on the right)
    m = Image.open(os.path.join(ROOT, "art", "campus", f"stage_{key}.png")).convert("RGB")
    s = 1900 / (b["xmax"] - b["xmin"] + 60)
    map_crop = m.crop((round(30 * s), round(30 * s), round((b["xmax"] - b["xmin"] + 30) * s),
                       round((b["ymax"] - b["ymin"] + 30) * s)))
    t = Image.open(top_path).convert("RGB")
    k = t.width / (2 * EXTENT_HALF_M)
    x0 = (b["xmin"] - (cx - EXTENT_HALF_M)) * k
    y0 = ((cy + EXTENT_HALF_M) - b["ymax"]) * k
    x1 = (b["xmax"] - (cx - EXTENT_HALF_M)) * k
    y1 = ((cy + EXTENT_HALF_M) - b["ymin"]) * k
    top_crop = t.crop((round(x0), round(y0), round(x1), round(y1)))
    size = 900
    a = map_crop.resize((size, size), Image.LANCZOS)
    c = top_crop.resize((size, size), Image.LANCZOS)
    blend = Image.blend(a, c, 0.5)
    out = Image.new("RGB", (size * 3 + 40, size + 40), (30, 30, 30))
    for i, (im, label) in enumerate(((a, "OSM stage map (planner)"), (c, "generated level, top-down"),
                                     (blend, "50 % overlay"))):
        out.paste(im, (10 + i * (size + 10), 30))
        ImageDraw.Draw(out).text((14 + i * (size + 10), 8), label, fill=(235, 235, 235))
    # play-zone outline on all three
    d = ImageDraw.Draw(out)
    pb = st["play_bounds_m"]
    sc = size / (b["xmax"] - b["xmin"])
    for i in range(3):
        ox = 10 + i * (size + 10)
        d.rectangle([ox + (pb["xmin"] - b["xmin"]) * sc, 30 + (b["ymax"] - pb["ymax"]) * sc,
                     ox + (pb["xmax"] - b["xmin"]) * sc, 30 + (b["ymax"] - pb["ymin"]) * sc], outline=(255, 60, 60))
    out.save(out_path)
    print("compare_map:", out_path)


if __name__ == "__main__":
    main()
