"""Evaluation must distinguish actual model selections from repaired defaults."""
import importlib.util
from pathlib import Path

import spec_ai
from test_appearance import model_answer

path = Path(__file__).resolve().parents[3] / "tools/likeness/validate_qwen.py"
module_spec = importlib.util.spec_from_file_location("qwen_validation", path)
evaluation = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(evaluation)


def test_invalid_raw_response_cannot_pass_via_repaired_defaults():
    raw = model_answer(face="not-a-face")
    repaired, _ = spec_ai.repair(raw, "sglguest", "Evaluation")
    assert repaired["appearance"]["face"] == "oval"
    result = evaluation.assess(raw, {"face": ["oval"]})
    assert not result["raw_schema_ok"]
    assert result["matches"] == {"face": False}


def test_unknown_is_valid_but_does_not_match_a_visible_target():
    raw = model_answer(body="unknown", hair="unknown")
    result = evaluation.assess(raw, {"body": ["unknown"], "hair": ["curls", "coils"]})
    assert result["raw_schema_ok"]
    assert result["matches"] == {"body": True, "hair": False}


def test_unlabeled_photo_has_no_invented_accuracy_score():
    result = evaluation.assess(model_answer(), {})
    assert result["raw_schema_ok"] and result["matches"] == {}
    summary = evaluation.summarize([{**result, "seconds": 2.5}])
    assert summary["selection_matches"] == {}
    assert summary["raw_schema_valid"] == 1
