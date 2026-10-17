"""Stands in for tools/blender/run_blender.sh in the pipeline tests (no Blender here).

Behaves like `run_blender.sh build_character.py -- <id> --art-dir A --build-dir B --actors-dir C`:
checks the spec + face textures the worker prepared, "exports" the real daniel actor renamed to
<id>, copies daniel's preview renders and prints the builder's stdout markers.
FAKE_BLENDER_MODE: ok (default) | bad_validation | hang | crash | no_previews
"""
import json
import os
import shutil
import sys
import time

WORKER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKER)
import actor_rename  # noqa: E402

REAL_REPO = os.path.abspath(os.path.join(WORKER, "..", ".."))


def arg(argv, name):
    return argv[argv.index(name) + 1]


def main():
    mode = os.environ.get("FAKE_BLENDER_MODE", "ok")
    argv = sys.argv[sys.argv.index("--") + 1:]
    char_id = argv[0]
    art, build, actors = arg(argv, "--art-dir"), arg(argv, "--build-dir"), arg(argv, "--actors-dir")
    with open(os.path.join(art, char_id, "character.json")) as f:
        spec = json.load(f)
    assert spec["id"] == char_id
    assert os.path.isfile(os.path.join(art, char_id, "textures", "eyes_open.png"))
    assert os.environ.get("BLENDER"), "BLENDER not passed"
    print("EGL_BAD_MATCH: blah (harmless)", flush=True)
    if mode == "crash":
        print("run_blender.sh: Blender crashed (exit 139), retrying (1/3)", file=sys.stderr, flush=True)
        sys.exit(139)
    if mode == "hang":
        time.sleep(60)
    os.makedirs(build, exist_ok=True)
    print(f"SGL saved {build}/{char_id}.blend", flush=True)
    actor_rename.rename_actor(os.path.join(REAL_REPO, "mods", "sgl64", "actors", "daniel"), actors, char_id)
    ok = mode != "bad_validation"
    errors = [] if ok else ["geo.inc.c: no guest_geo"]
    print("SGL validation", "OK" if ok else "FAILED", errors, flush=True)
    previews = []
    if mode != "no_previews":
        src = os.path.join(REAL_REPO, "art", "daniel", "build", "previews")
        os.makedirs(os.path.join(build, "previews"), exist_ok=True)
        for f in sorted(os.listdir(src)):
            shutil.copy(os.path.join(src, f), os.path.join(build, "previews", f))
            previews.append(os.path.join(build, "previews", f))
            print("SGL_PREVIEW", previews[-1], flush=True)
    report = {"id": char_id, "name": spec["name"], "validation": {"ok": ok, "errors": errors},
              "tris": {"Mario Mesh": 1234}, "previews": previews, "seconds": 1.0}
    with open(os.path.join(build, "build_report.json"), "w") as f:
        json.dump(report, f)
    print("SGL_BUILD_REPORT", json.dumps(report), flush=True)
    sys.exit(0 if ok else 1)


main()
