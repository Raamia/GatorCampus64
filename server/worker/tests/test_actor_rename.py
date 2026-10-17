import os
import re
import sys

import pytest

import actor_rename
import schema_gen


def _validate():
    sys.path.insert(0, schema_gen.blender_tools())
    try:
        import validate_export
    finally:
        sys.path.pop(0)
    return validate_export


def test_rename_real_export_validates(tmp_path):
    src = os.path.join(schema_gen.repo_root(), "mods", "sgl64", "actors", "daniel")
    out = actor_rename.rename_actor(src, str(tmp_path), "guest_3")
    assert out == os.path.join(str(tmp_path), "guest_3")
    report, _ = _validate().validate(out, "guest_3")
    assert report["ok"], report["errors"]
    text = open(os.path.join(out, "geo.inc.c")).read()
    assert "guest_3_geo[]" in text
    assert not re.search(r"daniel", open(os.path.join(out, "model.inc.c")).read())
    assert "mat_guest_3_Skin__SKIN_" in open(os.path.join(out, "model.inc.c")).read()
    # and back through the neutral build id
    back = actor_rename.rename_actor(out, str(tmp_path / "b"), actor_rename.BUILD_ID)
    report, _ = _validate().validate(back, actor_rename.BUILD_ID)
    assert report["ok"], report["errors"]


def test_rename_source_tokens():
    s = "const GeoLayout sglguest_geo[]; mat_sglguest_Skin; mat_revert_sglguest_X; xsglguest_y; sglguestx"
    assert actor_rename.rename_source(s, "sglguest", "guest_1") == (
        "const GeoLayout guest_1_geo[]; mat_guest_1_Skin; mat_revert_guest_1_X; xsglguest_y; sglguestx")


def test_rename_rejects_bad_ids(tmp_path):
    src = tmp_path / "sglguest"
    src.mkdir()
    with pytest.raises(ValueError):
        actor_rename.rename_actor(str(src), str(tmp_path), "Guest-1")
    with pytest.raises(ValueError):
        actor_rename.rename_actor(str(src), str(tmp_path), "sglguest_2")
