"""Versioned Qwen selections, deterministic repair, and legacy compatibility."""
import copy
import itertools

import jsonschema
import pytest

import schema_gen
import spec_ai
from test_spec_ai import GOOD, synthetic_photo


def model_answer(**appearance):
    raw = copy.deepcopy(GOOD)
    raw["appearance"] = {"face": "square", "hair": "curls", "body": "broad", "outfit": "hoodie", **appearance}
    raw["build"] = {"legwear": "long_pants", "accessories": ["crossbody_strap"]}
    return raw


def test_vlm_contract_accepts_approved_selection_and_unknowns():
    catalog = schema_gen.appearance_catalog()
    for field, descriptions in catalog.PROFILE_DESCRIPTIONS.items():
        assert schema_gen.appearance_schema(True)["properties"][field]["enum"] == [*descriptions, "unknown"]
    jsonschema.validate(model_answer(), schema_gen.vlm_schema())
    jsonschema.validate(model_answer(body="unknown", face="unknown"), schema_gen.vlm_schema())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(model_answer(hair="mohawk"), schema_gen.vlm_schema())


@pytest.mark.parametrize("outfit,sleeves,accessory", [
    ("tee", "short", None), ("polo", "short", "shirt_collar"),
    ("hoodie", "long", "hood_down"), ("overshirt", "long", "shirt_collar"),
])
def test_selected_garment_controls_geometry_and_preserves_color(outfit, sleeves, accessory):
    raw = model_answer(outfit=outfit)
    raw["build"].update(sleeves="short", hair_style="malicious.py",
                        accessories=["shirt_collar", "hood_down", "crossbody_strap", "rolled_cuffs"])
    original = copy.deepcopy(raw)
    spec, notes = spec_ai.repair(raw, "sglguest", "Pat")
    assert raw == original
    assert spec["appearance"] == {"version": 1, "face": "square", "hair": "curls", "body": "broad", "outfit": outfit}
    assert spec["build"]["sleeves"] == sleeves
    assert ("rolled_cuffs" in spec["build"]["accessories"]) == (sleeves == "short")
    assert set(spec["build"]["accessories"]) & {"shirt_collar", "hood_down"} == ({accessory} if accessory else set())
    assert "crossbody_strap" in spec["build"]["accessories"]
    assert spec["colors"]["top"] == GOOD["colors"]["top"]
    assert schema_gen.appearance_catalog().resolve_spec(spec) == spec
    jsonschema.validate(spec, schema_gen.character_schema())


@pytest.mark.parametrize("appearance", [None, [], "oval", {},
    {"face": "unknown", "hair": "unknown", "body": "unknown", "outfit": "unknown"},
    {"face": ["oval"], "hair": {"module": "evil"}, "body": float("inf"), "outfit": "unsupported"}])
def test_uncertain_or_malformed_selections_have_documented_defaults(appearance):
    raw = model_answer()
    raw["appearance"] = appearance
    spec, notes = spec_ai.repair(raw, "sglguest", "Pat")
    assert spec["appearance"] == {"version": 1, **schema_gen.appearance_catalog().DEFAULTS}
    assert any("appearance.body" in note for note in notes)
    jsonschema.validate(spec, schema_gen.character_schema())


def test_model_cannot_set_version_or_load_code_and_profiles_are_independent():
    raw = model_answer(face="Long", hair="BOB", body="neutral", outfit="tee")
    raw["appearance"].update(version=9000, module="characters/daniel.py")
    spec, _ = spec_ai.repair(raw, "sglguest", "Pat")
    assert spec["appearance"] == {"version": 1, "face": "long", "hair": "bob", "body": "neutral", "outfit": "tee"}


def test_legacy_specs_do_not_gain_appearance_or_change_build_values():
    spec, notes = spec_ai.repair(GOOD, "sglguest", "Daniel")
    assert "appearance" not in spec
    assert spec["build"] == GOOD["build"]
    assert notes == []
    assert schema_gen.appearance_catalog().resolve_spec(spec) is spec


@pytest.mark.parametrize("version", [None, True, 0, 2, "1"])
def test_authored_unsupported_versions_fail_explicitly(version):
    catalog = schema_gen.appearance_catalog()
    spec = {"appearance": {"version": version, **catalog.DEFAULTS}}
    with pytest.raises(ValueError, match="appearance.version"):
        catalog.resolve_spec(spec)


def test_catalog_contains_only_implemented_profiles_and_resolves_all_combinations():
    catalog = schema_gen.appearance_catalog()
    assert set(catalog.PROFILE_DESCRIPTIONS["face"]) == set(catalog.FACE_PROFILES)
    assert set(catalog.PROFILE_DESCRIPTIONS["hair"]) == set(catalog.HAIR_PROFILES)
    assert set(catalog.PROFILE_DESCRIPTIONS["body"]) == set(catalog.BODY_PROFILES)
    assert set(catalog.PROFILE_DESCRIPTIONS["outfit"]) == set(catalog.OUTFITS)
    for choices in itertools.product(*catalog.PROFILE_DESCRIPTIONS.values()):
        profile = dict(zip(catalog.PROFILE_DESCRIPTIONS, choices), version=1)
        spec = catalog.resolve_spec({"appearance": profile, "build": {"accessories": ["crossbody_strap"]}})
        assert spec["appearance"] == profile
        assert set(spec["build"]["accessories"]) <= set(schema_gen.accessories())


def test_qwen_request_and_repair_preserve_the_appearance_contract():
    backend = spec_ai.StaticBackend(model_answer(body="unknown"))
    spec, info = spec_ai.generate_spec([synthetic_photo()], "sglguest", "Pat", backend,
                                      use_cv=False, require_model=True, log=lambda _: None)
    messages, schema = backend.calls[0]
    assert "appearance" in schema["required"]
    assert "headshot or a loose coat" in messages[0]["content"]
    assert 'appearance.body MUST be "unknown"' in messages[0]["content"]
    assert "obscured or cropped" not in schema_gen.appearance_catalog().PROFILE_DESCRIPTIONS["body"]["neutral"]
    assert spec["appearance"]["body"] == "neutral"
    assert spec["appearance"]["hair"] == "curls"
    assert spec["build"]["accessories"] == ["crossbody_strap", "hood_down"]
    assert any("appearance.body" in note for note in info["notes"])
