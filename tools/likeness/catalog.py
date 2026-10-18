"""Review specimens drawn from the shared approved appearance catalog."""
import copy

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "blender"))
from sgl_appearance import FACE_PROFILES, HAIR_PROFILES, BODY_PROFILES, OUTFITS


def entries():
    out = []
    def add(code, group, label, note, **profile):
        out.append({"id": code, "group": group, "label": label, "note": note,
                    "profile": {"face": "oval", "hair": "buzz", "body": "neutral", "outfit": "tee", **profile}})
    for n, (key, face) in enumerate(FACE_PROFILES.items(), 1):
        add(f"f{n:02}", "Faces", face["label"], "Same crop, outfit and body. Compare jaw, cheeks, forehead and nose.", face=key)
    for n, (key, label) in enumerate(HAIR_PROFILES.items(), 1):
        add(f"h{n:02}", "Hair", label, "Same oval face and body. Compare the silhouette from the front and side.", hair=key)
    for n, key in enumerate(BODY_PROFILES, 1):
        add(f"b{n:02}", "Bodies", key.title(), "Same height, head and T-shirt. These are silhouette studies; animation fitting comes next.", body=key)
    for n, (key, outfit) in enumerate(OUTFITS.items(), 1):
        add(f"c{n:02}", "Clothes", outfit["label"], "Same body and palette. Compare sleeve, collar, hood and garment volume.", outfit=key)
    return out


def spec_for(entry):
    profile = copy.deepcopy(entry["profile"])
    outfit = OUTFITS[profile["outfit"]]
    return {"id": entry["id"], "name": entry["label"], "likeness_review": profile,
            "colors": {"skin": "#C99171", "skin_shadow": "#B47F62", "hair": "#292323",
                       "eyes": "#503C2D", "top": "#CF603E", "top_detail": "#863C2B",
                       "pants": "#344C5A", "shoes": "#EEE4D2", "shoe_soles": "#BFB8A8"},
            "signature_traits": ["relaxed closed smile"], "outfit": {},
            "build": {"hair_style": "short_wavy_curly", "sleeves": outfit["sleeves"],
                      "legwear": "long_pants", "accessories": outfit["accessories"]}}
