"""The generated enums must match the builder's registries. Imports the real Blender
modules with bpy/bmesh/mathutils stubbed, an independent path from schema_gen's ast parse."""
import json
import os
import sys
from unittest import mock

import jsonschema
import pytest

import schema_gen

BLENDER_MODULES = ["bpy", "bmesh", "mathutils", "mathutils.bvhtree", "mathutils.geometry"]


@pytest.fixture(scope="module")
def real_modules():
    tools = schema_gen.blender_tools()
    stubs = {name: mock.MagicMock(name=name) for name in BLENDER_MODULES}
    saved_path = list(sys.path)
    with mock.patch.dict(sys.modules, stubs):
        sys.path.insert(0, tools)
        try:
            import sgl_body
            import sgl_heads
            yield sgl_heads, sgl_body
        finally:
            sys.path[:] = saved_path
            for name in [n for n in sys.modules if n.startswith("sgl_")]:
                del sys.modules[name]


def test_hair_styles_match_code(real_modules):
    sgl_heads, _ = real_modules
    assert schema_gen.hair_styles() == list(sgl_heads.HAIR_STYLES)
    assert schema_gen.default_hair_style() == sgl_heads.DEFAULT_STYLE
    assert schema_gen.default_hair_style() in schema_gen.hair_styles()


def test_accessories_are_the_implemented_ones(real_modules):
    _, sgl_body = real_modules
    todo_code = sgl_body._todo("x").__code__
    implemented = [k for k, fn in sgl_body.ACCESSORIES.items() if fn.__code__ is not todo_code]
    assert schema_gen.accessories() == implemented
    assert implemented  # the registry was found


def test_spec_documented_enums():
    # web_platform_spec.md §5.1 as of 2026-10-16; update both together
    assert set(schema_gen.accessories()) == {"shirt_collar", "rolled_cuffs", "hood_down", "crossbody_strap"}
    assert len(schema_gen.hair_styles()) >= 6
    assert {"straight_fringe_medium", "long_straight_past_shoulders"} <= set(schema_gen.reviewed_hair_styles())


def test_enums_in_schema():
    s = schema_gen.character_schema()
    b = s["properties"]["build"]["properties"]
    assert b["hair_style"]["enum"] == schema_gen.hair_styles()
    assert b["accessories"]["items"]["enum"] == schema_gen.accessories()
    assert b["sleeves"]["enum"] == ["long", "short"]
    assert b["legwear"]["enum"] == ["long_pants", "shorts"]
    jsonschema.Draft202012Validator.check_schema(s)
    jsonschema.Draft202012Validator.check_schema(schema_gen.vlm_schema())


def test_daniel_spec_validates():
    with open(os.path.join(schema_gen.repo_root(), "art", "daniel", "character.json")) as f:
        spec = json.load(f)
    spec.pop("reference_photos")
    jsonschema.validate(spec, schema_gen.character_schema())


def test_vlm_schema_is_strict_compatible():
    def walk(node):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert sorted(node["required"]) == sorted(node["properties"])
            for child in node["properties"].values():
                walk(child)
        if node.get("type") == "array":
            walk(node["items"])
    walk(schema_gen.vlm_schema())
