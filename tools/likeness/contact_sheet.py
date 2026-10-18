"""Make a labeled PNG index of the entire batch for quick visual feedback."""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


def make_sheet(batch):
    records = json.loads((batch / "catalog.json").read_text())
    groups = ["Faces", "Hair", "Bodies", "Clothes"]
    width, margin, tile, row = 1680, 40, 200, 292
    sheet = Image.new("RGB", (width, 150 + len(groups) * row), "#f3f0e7")
    draw = ImageDraw.Draw(sheet)
    try:
        title = ImageFont.truetype("DejaVuSans.ttf", 35)
        text = ImageFont.truetype("DejaVuSans.ttf", 16)
        small = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        title = ImageFont.load_default(size=35)
        text = ImageFont.load_default(size=16)
        small = ImageFont.load_default(size=13)
    integrated = records and all(r.get("integrated") for r in records)
    draw.text((margin, 30), "GATORIZE / " + ("INTEGRATED SET" if integrated else "ROUND 01"), font=title, fill="#254638")
    status = "joint fitting checked · in-game review pending" if integrated else "body / garment animation fitting pending"
    draw.text((margin, 83), f"{len(records)} shape studies · use each ID when giving feedback · {status}", font=text, fill="#697561")
    for group_index, group in enumerate(groups):
        y = 140 + group_index * row
        draw.text((margin, y), group.upper(), font=text, fill="#a4492d")
        for i, record in enumerate(r for r in records if r["group"] == group):
            x = margin + i * tile
            with Image.open(batch / record["poster"]) as source:
                image = source.convert("RGB").resize((188, 188), Image.Resampling.LANCZOS)
            sheet.paste(image, (x, y + 33))
            draw.text((x, y + 229), record["id"].upper() + "  " + record["label"], font=small, fill="#254638")
    sheet.save(batch / "overview.png")


if __name__ == "__main__":
    make_sheet(Path(sys.argv[1] if len(sys.argv) > 1 else "dist/likeness-round-01"))
