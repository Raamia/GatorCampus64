"""Approved Gatorize appearance catalog and version-one contract.

Pure Python: shared by Qwen schema generation, repair, Blender, and review tools.
Specs without ``appearance`` continue through the legacy builder unchanged.
"""
import copy

VERSION = 1

FACE_PROFILES = {
    "oval": {"label": "Oval", "widths": [0.30, 0.48, 0.51, 0.47, 0.33], "heights": [0.14, 0.39, 0.72, 0.98, 1.15], "powers": [2.0, 2.1, 2.1, 2.0, 2.0], "nose": [0.055, 0.065]},
    "round": {"label": "Round", "widths": [0.37, 0.56, 0.58, 0.49, 0.33], "heights": [0.18, 0.42, 0.71, 0.94, 1.08], "powers": [2.0, 2.0, 2.0, 2.0, 2.0], "nose": [0.065, 0.045]},
    "square": {"label": "Square", "widths": [0.43, 0.55, 0.55, 0.49, 0.33], "heights": [0.16, 0.40, 0.73, 0.98, 1.12], "powers": [3.1, 2.8, 2.4, 2.2, 2.0], "nose": [0.075, 0.075]},
    "long": {"label": "Long", "widths": [0.28, 0.43, 0.47, 0.44, 0.31], "heights": [0.08, 0.35, 0.74, 1.04, 1.23], "powers": [2.2, 2.2, 2.2, 2.1, 2.0], "nose": [0.045, 0.095]},
    "heart": {"label": "Heart", "widths": [0.22, 0.44, 0.56, 0.52, 0.35], "heights": [0.12, 0.38, 0.74, 1.00, 1.15], "powers": [2.0, 2.2, 2.2, 2.0, 2.0], "nose": [0.045, 0.055]},
    "broad": {"label": "Broad jaw", "widths": [0.43, 0.58, 0.57, 0.51, 0.35], "heights": [0.13, 0.38, 0.72, 0.98, 1.13], "powers": [2.6, 2.5, 2.3, 2.1, 2.0], "nose": [0.09, 0.055]},
}

HAIR_PROFILES = {
    "buzz": "Close crop",
    "sidepart": "Side part",
    "fringe": "Straight fringe",
    "waves": "Wavy crop",
    "curls": "Curly fade",
    "coils": "Rounded coils",
    "bob": "Straight bob",
    "long": "Long / side part",
}

BODY_PROFILES = {
    # shoulder, waist, hip, depth; preserve height and the head silhouette.
    "neutral": (1.0, 1.0, 1.0, 1.0),
    "slender": (0.88, 0.78, 0.85, 0.86),
    "broad": (1.22, 0.90, 0.96, 1.03),
    "stocky": (1.14, 1.15, 1.12, 1.16),
    "fuller": (1.06, 1.25, 1.20, 1.22),
}

OUTFITS = {
    "tee": {"label": "T-shirt", "sleeves": "short", "accessories": []},
    "polo": {"label": "Polo / collar", "sleeves": "short", "accessories": ["shirt_collar"]},
    "hoodie": {"label": "Hoodie", "sleeves": "long", "accessories": ["hood_down"]},
    "overshirt": {"label": "Boxy overshirt", "sleeves": "long", "accessories": ["shirt_collar"]},
}

PROFILE_DESCRIPTIONS = {
    "face": {
        "oval": "balanced oval face with a softly tapered jaw",
        "round": "rounded cheeks and a short, rounded jaw",
        "square": "angular jaw and similar cheek and jaw widths",
        "long": "longer, narrower face and chin",
        "heart": "wider upper face tapering to a small chin",
        "broad": "wide cheeks and a broad, rounded jaw",
    },
    "hair": {
        "buzz": "very short close crop with little volume",
        "sidepart": "short straight hair swept to one side",
        "fringe": "straight, heavier fringe across the forehead",
        "waves": "short wavy hair with loose raised waves",
        "curls": "short curly top with closely cropped sides",
        "coils": "rounded, fuller tight curls around the top and sides",
        "bob": "straight hair ending around the jaw",
        "long": "long straight hair past the shoulders with a side part",
    },
    "body": {
        "neutral": "visible body with balanced shoulder, waist and hip proportions",
        "slender": "narrower visible torso and limbs",
        "broad": "broader shoulders relative to the waist",
        "stocky": "broad, compact torso and limbs",
        "fuller": "fuller waist and hips",
    },
    "outfit": {
        "tee": "short-sleeved, collarless T-shirt",
        "polo": "short-sleeved collared shirt",
        "hoodie": "long sleeves with a hood resting behind the neck",
        "overshirt": "long-sleeved collared shirt with a looser body",
    },
}

DEFAULTS = {"face": "oval", "hair": "buzz", "body": "neutral", "outfit": "tee"}


def validate(appearance):
    """Fail explicitly for malformed authored specs; model output is repaired upstream."""
    if not isinstance(appearance, dict) or type(appearance.get("version")) is not int or appearance["version"] != VERSION:
        raise ValueError(f"appearance.version must be {VERSION}")
    if set(appearance) != {"version", *PROFILE_DESCRIPTIONS}:
        raise ValueError("appearance requires exactly version, face, hair, body and outfit")
    for field, choices in PROFILE_DESCRIPTIONS.items():
        if not isinstance(appearance[field], str) or appearance[field] not in choices:
            raise ValueError(f"unsupported appearance.{field}: {appearance[field]!r}")
    return appearance


def resolve_spec(spec):
    """Selected garment owns its sleeve/accessory geometry; colors remain independent.

    Return a copy for versioned specs so caller data and catalog entries are never
    modified. Legacy specs return untouched, preserving handcrafted characters.
    """
    if "appearance" not in spec:
        return spec
    appearance = validate(spec["appearance"])
    resolved = copy.deepcopy(spec)
    build = resolved.setdefault("build", {})
    outfit = OUTFITS[appearance["outfit"]]
    build["sleeves"] = outfit["sleeves"]
    accessories = [a for a in build.get("accessories", []) if a not in ("shirt_collar", "hood_down")]
    if outfit["sleeves"] != "short":
        accessories = [a for a in accessories if a != "rolled_cuffs"]
    build["accessories"] = list(dict.fromkeys([*accessories, *outfit["accessories"]]))
    return resolved
