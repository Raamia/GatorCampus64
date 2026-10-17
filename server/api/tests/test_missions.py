"""sgl_api/missions.py must match what tools/gen_api_missions.py derives from the Lua sources."""
import importlib.util
from pathlib import Path

import pytest

from sgl_api import missions

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "tools/gen_api_missions.py"


def _gen():
    if not GEN.exists() or not (ROOT / "mods/sgl64").is_dir():
        pytest.skip("not in a full checkout (tools/ and mods/ are needed)")
    spec = importlib.util.spec_from_file_location("gen_api_missions", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_module_is_in_sync():
    gen = _gen()
    assert Path(missions.__file__).read_text(encoding="utf-8") == gen.render(), \
        "run: python3 tools/gen_api_missions.py"


def test_floors():
    m = missions.MISSIONS
    assert m["swamp_sprint"]["floor_frames"] == 675  # gold 45 s / 2 = 22.5 s at 30 fps
    assert m["libwest_coffee"]["floor_rule"] == "gold/2"
    assert m["lake_bat_census"]["floor_frames"] == 60 * 30
    assert all(v["floor_frames"] >= 300 for v in m.values())
    assert all(v["title"] for v in m.values())


def test_companion_catalog_ids_are_known():
    import json
    cat = ROOT / "companion/app/src/data/mission-catalog.json"
    if not cat.exists():
        pytest.skip("companion app not in this checkout")
    ids = {e["id"] for e in json.loads(cat.read_text())["missions"]}
    assert ids <= set(missions.MISSIONS)
