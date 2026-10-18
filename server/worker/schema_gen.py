"""character.json JSON Schema, generated from the builder's code so the enums can't drift.

The registries live in Blender-only modules (sgl_heads / sgl_body import bpy), so they are
read with `ast` instead of imported:
  - build.hair_style: keys of sgl_heads.HAIR_STYLES (default sgl_heads.DEFAULT_STYLE);
    a preset whose source line says "untested" is reported as such (the prompt prefers
    the reviewed ones)
  - build.accessories: entries of sgl_body.ACCESSORIES whose value is not a `_todo(...)` stub

Run `python3 schema_gen.py` to print the full schema.
"""
import ast
import functools
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def repo_root():
    """The Super Gatorlator 64 checkout with tools/blender/ (SGL_REPO, else this repo)."""
    return os.path.abspath(os.environ.get("SGL_REPO") or os.path.join(HERE, "..", ".."))


def blender_tools():
    return os.path.join(repo_root(), "tools", "blender")


@functools.lru_cache(maxsize=None)
def _appearance_catalog(root):
    path = os.path.join(root, "tools", "blender", "sgl_appearance.py")
    module_spec = importlib.util.spec_from_file_location("sgl_appearance_contract", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def appearance_catalog():
    """The builder's pure-Python catalog; no Blender dependency or duplicated enums."""
    return _appearance_catalog(repo_root())


def appearance_schema(for_model=False):
    catalog = appearance_catalog()
    properties = {}
    if not for_model:
        properties["version"] = {"type": "integer", "const": catalog.VERSION}
    for field, choices in catalog.PROFILE_DESCRIPTIONS.items():
        properties[field] = {"type": "string", "enum": [*choices, *(["unknown"] if for_model else [])],
                             "description": "; ".join(f"{key}: {description}" for key, description in choices.items())}
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


SLEEVES = ["long", "short"]
LEGWEAR = ["long_pants", "shorts"]
DEFAULT_SLEEVES = "long"        # sgl_body.remap_body defaults
DEFAULT_LEGWEAR = "long_pants"
TEXT_MAX = 200
MAX_TRAITS = 6
HEX_PATTERN = r"^#[0-9A-Fa-f]{6}$"
ID_PATTERN = r"^[a-z][a-z0-9_]{0,31}$"
# colour roles a generated spec may set (sgl_materials.build_palette + sgl_face_gen)
COLOR_KEYS = ["skin", "skin_shadow", "hair", "eyes", "eyebrows", "top", "top_detail", "pants", "shoes",
              "shoe_soles"]
REQUIRED_COLORS = ["skin"]
OUTFIT_KEYS = ["top", "pants", "shoes", "accessory", "headwear"]


def _module_ast(name):
    path = os.path.join(blender_tools(), name)
    with open(path) as f:
        src = f.read()
    return src, ast.parse(src, filename=path)


def _top_assign(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise LookupError(f"no top-level assignment {name} found")


@functools.lru_cache(maxsize=None)
def _hair_info(root):
    src, tree = _module_ast("sgl_heads.py")
    lines = src.splitlines()
    d = _top_assign(tree, "HAIR_STYLES")
    if not isinstance(d, ast.Dict):
        raise TypeError("sgl_heads.HAIR_STYLES is not a dict literal")
    styles = {}
    for k in d.keys:
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            raise TypeError("sgl_heads.HAIR_STYLES has a non-string key")
        styles[k.value] = "untested" not in lines[k.lineno - 1].lower()
    default = _top_assign(tree, "DEFAULT_STYLE")
    return styles, default.value


def hair_styles():
    """Every hair_style the builder knows, in source order."""
    return list(_hair_info(repo_root())[0])


def reviewed_hair_styles():
    styles = _hair_info(repo_root())[0]
    return [k for k, ok in styles.items() if ok]


def default_hair_style():
    return _hair_info(repo_root())[1]


def _is_todo(value):
    return (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "_todo")


@functools.lru_cache(maxsize=None)
def _accessories(root):
    _src, tree = _module_ast("sgl_body.py")
    d = _top_assign(tree, "ACCESSORIES")
    if not isinstance(d, ast.Dict):
        raise TypeError("sgl_body.ACCESSORIES is not a dict literal")
    return [k.value for k, v in zip(d.keys, d.values) if not _is_todo(v)]


def accessories():
    """Implemented (non-_todo) accessories, in source order."""
    return list(_accessories(repo_root()))


def _text(desc=None):
    s = {"type": "string", "maxLength": TEXT_MAX}
    if desc:
        s["description"] = desc
    return s


def _color(desc=None):
    s = {"type": "string", "pattern": HEX_PATTERN}
    if desc:
        s["description"] = desc
    return s


def build_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sleeves", "legwear", "hair_style", "accessories"],
        "properties": {
            "sleeves": {"type": "string", "enum": SLEEVES},
            "legwear": {"type": "string", "enum": LEGWEAR},
            "hair_style": {"type": "string", "enum": hair_styles()},
            "accessories": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": accessories()}},
        },
    }


def character_schema():
    """Schema of a character.json the worker hands to the builder (after repair)."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Super Gatorlator 64 character.json (generated subset)",
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "name", "colors", "outfit", "signature_traits", "build"],
        "properties": {
            "id": {"type": "string", "pattern": ID_PATTERN},
            "name": {"type": "string", "minLength": 1, "maxLength": 32},
            "colors": {
                "type": "object",
                "additionalProperties": False,
                "required": REQUIRED_COLORS,
                "properties": {k: _color() for k in COLOR_KEYS},
            },
            "outfit": {
                "type": "object",
                "additionalProperties": False,
                "properties": {k: _text() for k in OUTFIT_KEYS},
            },
            "signature_traits": {"type": "array", "maxItems": MAX_TRAITS, "items": _text()},
            "notes": _text(),
            "build": build_schema(),
            "appearance": appearance_schema(),
        },
    }


# colours the vision model is asked for (skin_shadow / shoe_soles / eyebrows are derived)
VLM_COLORS = {
    "skin": "face skin tone in even light",
    "hair": "main hair colour (not the highlights)",
    "eyes": "iris colour",
    "top": "main colour of the shirt / hoodie / jacket",
    "top_detail": "trim, collar or hood lining colour of the top (a darker shade of top if none)",
    "pants": "trousers / shorts / skirt colour",
    "shoes": "shoe colour (#F2F2F2 if not visible)",
}


def vlm_schema():
    """The structured-output schema sent to the vision model: no id/name (set by the server),
    every property required and additionalProperties false (OpenAI strict mode compatible)."""
    build = build_schema()
    # Hair and sleeves are owned by the selected appearance profiles in v1.
    # Keep the legacy builder fields only in the stored character schema.
    for field in ("hair_style", "sleeves"):
        del build["properties"][field]
        build["required"].remove(field)
    return {
        "type": "object",
        "additionalProperties": False,
        # vLLM's guided decoder follows property order. Live reference-photo
        # checks selected face/body more accurately before generating colors
        # and descriptive prose. This changes ordering, not the stored contract.
        "required": ["appearance", "colors", "outfit", "signature_traits", "build"],
        "properties": {
            "appearance": appearance_schema(for_model=True),
            "colors": {
                "type": "object",
                "additionalProperties": False,
                "required": list(VLM_COLORS),
                "properties": {k: _color(d) for k, d in VLM_COLORS.items()},
            },
            "outfit": {
                "type": "object",
                "additionalProperties": False,
                "required": OUTFIT_KEYS,
                "properties": {k: _text() for k in OUTFIT_KEYS},
            },
            "signature_traits": {"type": "array", "maxItems": MAX_TRAITS, "items": _text()},
            "build": build,
        },
    }


def is_hex(value):
    return isinstance(value, str) and re.fullmatch(HEX_PATTERN, value) is not None


if __name__ == "__main__":
    print(json.dumps(character_schema(), indent=2))
