"""Pipeline end to end with Blender replaced by tests/fake_blender.py (real face generator,
real validate_export, real portrait; storage on a temp dir)."""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

import pipeline
import schema_gen
import spec_ai
import storage
from test_spec_ai import GOOD, synthetic_photo

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_TOOLS = schema_gen.blender_tools()
JOB = "6d1f0a2e-0000-4000-8000-000000000001"


@pytest.fixture
def fake_repo(tmp_path):
    tools = tmp_path / "repo" / "tools" / "blender"
    tools.mkdir(parents=True)
    for f in ("sgl_face_gen.py", "sgl_util.py", "validate_export.py"):
        os.symlink(os.path.join(REAL_TOOLS, f), tools / f)
    (tools / "build_character.py").write_text("raise SystemExit('the fake run_blender.sh never runs this')\n")
    runner = tools / "run_blender.sh"
    runner.write_text(f"#!/bin/sh\nexec {sys.executable} {os.path.join(HERE, 'fake_blender.py')} \"$@\"\n")
    runner.chmod(0o755)
    return str(tmp_path / "repo")


@pytest.fixture
def env(tmp_path, fake_repo):
    store = storage.LocalStorage(str(tmp_path / "bucket"))
    for i in range(2):
        p = tmp_path / f"p{i}.png"
        p.write_bytes(synthetic_photo())
        store.put_file(f"photos/{JOB}/{i}.png", str(p))
    cfg = pipeline.Config(repo=fake_repo, blender="/nonexistent/blender", work_root=str(tmp_path / "work"),
                          build_timeout=20, use_cv=False)
    return store, cfg


def progress_recorder():
    seen = []

    def progress(state, step, text):
        if not seen or seen[-1] != (state, step):
            seen.append((state, step))
    return seen, progress


def test_pipeline_ok(env):
    store, cfg = env
    seen, progress = progress_recorder()
    res = pipeline.run_job(JOB, "Pat", store, spec_ai.StaticBackend(GOOD), cfg, progress)
    states = [s for s, _ in seen]
    assert [s for i, s in enumerate(states) if i == 0 or states[i - 1] != s] == [
        "spec", "face", "build", "export", "validate", "preview"]
    assert seen[-1] == ("preview", "store")
    assert res["spec"]["id"] == "sglguest" and res["spec"]["name"] == "Pat"
    keys = store.list(f"builds/{JOB}/")
    for k in ("character.json", "portrait.png", "manifest.json", "log.txt", "build_report.json",
              "previews/front.png", "previews/head.png", "actors/sglguest/geo.inc.c", "actors/sglguest/model.inc.c",
              "actors/sglguest/geo_header.h"):
        assert f"builds/{JOB}/{k}" in keys, k
    assert store.list(f"photos/{JOB}/") == []  # photos deleted
    man = json.loads(store.get(f"builds/{JOB}/manifest.json"))
    assert man["build_id"] == "sglguest" and man["previews"]["front"] == f"builds/{JOB}/previews/front.png"
    assert set(man["files"]) == set(keys)
    im = Image.open(os.path.join(store.root, f"builds/{JOB}/portrait.png"))
    assert im.size == (64, 64) and im.mode == "RGBA"
    assert np.asarray(im)[..., 3].min() == 255
    assert "SGL validation OK" in res["log"] and "photos: deleted 2" in res["log"]
    assert not os.path.exists(os.path.join(cfg.work_root, JOB))


def test_pipeline_validation_failure(env, monkeypatch):
    store, cfg = env
    monkeypatch.setenv("FAKE_BLENDER_MODE", "bad_validation")
    with pytest.raises(pipeline.StepFailed) as ei:
        pipeline.run_job(JOB, "Pat", store, spec_ai.StaticBackend(GOOD), cfg)
    assert ei.value.step == "validate"
    assert "FAILED at validate" in ei.value.log
    assert store.list(f"photos/{JOB}/") == [] and store.list(f"builds/{JOB}/") == []


def test_pipeline_timeout_kills_blender(env, monkeypatch):
    store, cfg = env
    cfg.build_timeout = 2
    monkeypatch.setenv("FAKE_BLENDER_MODE", "hang")
    with pytest.raises(pipeline.StepFailed) as ei:
        pipeline.run_job(JOB, "Pat", store, spec_ai.StaticBackend(GOOD), cfg)
    assert ei.value.step == "build" and "timed out" in str(ei.value)
    assert store.list(f"photos/{JOB}/") == []


def test_pipeline_crash_without_report(env, monkeypatch):
    store, cfg = env
    monkeypatch.setenv("FAKE_BLENDER_MODE", "crash")
    with pytest.raises(pipeline.StepFailed) as ei:
        pipeline.run_job(JOB, "Pat", store, spec_ai.StaticBackend(GOOD), cfg)
    assert ei.value.step == "build" and "without a build report" in str(ei.value)


def test_pipeline_no_photos(env):
    store, cfg = env
    store.delete_prefix(f"photos/{JOB}/")
    with pytest.raises(pipeline.StepFailed) as ei:
        pipeline.run_job(JOB, "Pat", store, spec_ai.StaticBackend(GOOD), cfg)
    assert ei.value.step == "spec"


def test_pipeline_model_down_still_builds(env):
    store, cfg = env

    class Down:
        def complete(self, messages, schema):
            raise spec_ai.VLMError("connection refused")
    res = pipeline.run_job(JOB, "Pat", store, Down(), cfg)
    assert res["spec"]["build"]["hair_style"] == schema_gen.default_hair_style()
    assert "vision model failed" in res["log"]


def test_parse_build_report():
    lines = ["x", 'SGL_BUILD_REPORT {"a": 1}', "Blender quit", 'SGL_BUILD_REPORT {"a": 2}']
    assert pipeline.parse_build_report(lines) == {"a": 2}
    assert pipeline.parse_build_report(["nothing"]) is None


def test_run_streaming_lines_and_rc():
    out = []
    rc = pipeline.run_streaming([sys.executable, "-c", "import sys; print('a'); print('b', file=sys.stderr); "
                                                      "sys.exit(3)"], 10, out.append)
    assert rc == 3 and sorted(out) == ["a", "b"]
