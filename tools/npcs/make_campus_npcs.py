"""Campus NPCs: a fixed crowd of random students built by the Gatorize Me pipeline, without the GPU.

The web pipeline (server/worker/pipeline.py) is photos -> vision model (GPU) -> spec -> face textures ->
Blender build/export/validate. Only the vision model needs the GPU. Here a seeded random generator plays
its part: it writes a "model answer" (appearance profiles, colours, outfit, traits), and everything after
that is the worker's own code, unchanged:

  spec_ai.repair       the same schema repair/validation every web upload goes through
  pipeline.step_face   tools/blender/sgl_face_gen.py (procedural eyes + mouth)
  pipeline.step_build  tools/blender/run_blender.sh build_character.py (Blender on the CPU)
  pipeline.step_validate  validate_export.py outside Blender (also renamed to guest_8)
  actor_rename         sglguest -> npc_<nn> into mods/sgl64/actors/

The roster is predetermined: SEED fixes every NPC, art/npcs/<id>/character.json keeps each spec (the
build reads those, so editing one and rebuilding it works), and art/npcs/<id>/front.png is its render (256 px).
sgl_campus_npcs.lua walks them around the hub.

Usage (from the repo root; needs Blender 4.5.3, Fast64 and the coopdx template, see tools/likeness/README.md):
  tools/.venv/bin/python -I tools/npcs/make_campus_npcs.py specs            # (re)write the 40 specs
  tools/.venv/bin/python -I tools/npcs/make_campus_npcs.py build [--jobs 4] [--only npc_03 npc_07]
Env: BLENDER (default tools/vendor/blender/Blender.app/Contents/MacOS/Blender).
"""
import argparse
import json
import os
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "worker"))
os.environ.setdefault("SGL_REPO", ROOT)

import actor_rename  # noqa: E402
import pipeline  # noqa: E402
import schema_gen  # noqa: E402
import spec_ai  # noqa: E402

SEED = 64_2026
COUNT = 40
SYNCED = 24   # npc_01..24 walk the same routes on every client; npc_25..40 are the local crowd around the player
ART = os.path.join(ROOT, "art", "npcs")
ACTORS = os.path.join(ROOT, "mods", "sgl64", "actors")
DEFAULT_BLENDER = os.path.join(ROOT, "tools", "vendor", "blender", "Blender.app", "Contents", "MacOS", "Blender")


def npc_id(i):
    return f"npc_{i:02d}"


# ------------------------------------------------------------------ the random "model answer"
SKIN = ["#F3D3BD", "#EBC0A1", "#E0AC88", "#D69B78", "#C68863", "#B27352", "#9C6244", "#87533A",
        "#6E4430", "#5A3726", "#F0C8A8", "#C99A7A"]
HAIR_NATURAL = ["#16110F", "#1E1A1B", "#2A1F1A", "#3B2A20", "#4E3626", "#6B4A30", "#8A6440",
                "#B48A58", "#D2B27A", "#7A3B22"]
HAIR_RARE = ["#9A9A9E", "#3C5CC8", "#C8508C", "#E07A30"]
EYES = ["#3B2117", "#4A2C1A", "#2A1A12", "#6B4A2A", "#5C6B3A", "#3E6E8C", "#6E7F8C"]
TOPS = {  # colour: words for the outfit text
    "#FA4616": "UF orange", "#0021A5": "UF blue", "#F2F2F2": "white", "#1E1E22": "black",
    "#8C9096": "heather gray", "#22304F": "navy", "#6E1F2B": "maroon", "#2F5D3A": "forest green",
    "#7FB3E0": "sky blue", "#F2C94C": "yellow", "#E8A0B8": "pink", "#C8B28C": "tan",
    "#5B3F8C": "purple", "#2E7D7A": "teal",
}
PANTS = {"#3B4E6E": "blue jeans", "#1F2A3D": "dark denim", "#1C1C1E": "black", "#B9A27A": "khaki",
         "#6A6E73": "gray", "#4E5634": "olive"}
SHORTS = {"#3B4E6E": "denim shorts", "#B9A27A": "khaki shorts", "#1C1C1E": "black athletic shorts",
          "#22304F": "navy shorts", "#6A6E73": "gray shorts"}
SHOES = {"#F2F2F2": "white sneakers", "#1C1C1E": "black sneakers", "#8C9096": "gray running shoes",
         "#B03030": "red sneakers", "#22304F": "navy canvas shoes", "#C8B28C": "tan boots"}
NAMES = {"she": ["Maya", "Priya", "Sofia", "Aaliyah", "Hannah", "Grace", "Isabel", "Nina", "Chloe", "Lena",
                 "Zoe", "Amara", "Jasmine", "Mei", "Paige", "Elena", "Tara", "Imani"],
         "he": ["Jordan", "Marcus", "Ethan", "Diego", "Kevin", "Malik", "Tyler", "Omar", "Andre", "Ryan",
                "Victor", "Caleb", "Leo", "Darius", "Sam", "Hiro", "Mateo", "Noah"]}
# more names once a pool runs out (its own generator, so the main sequence and npc_01..24 stay as they were)
MORE_NAMES = {"she": ["Ava", "Layla", "Keisha", "Rosa", "Hana", "Leah", "Brianna", "Fatima", "Olivia", "Yuna"],
              "he": ["Jamal", "Lucas", "Arjun", "Carlos", "Ben", "Kenji", "Isaiah", "Owen", "Rafael", "Tariq"]}
HAIR_BY_LOOK = {"she": ["long", "long", "bob", "bob", "waves", "curls", "coils", "fringe", "sidepart"],
                "he": ["buzz", "buzz", "sidepart", "sidepart", "fringe", "waves", "curls", "coils"]}
OUTFIT_WORDS = {"tee": "T-shirt", "polo": "polo shirt", "hoodie": "hoodie, hood down", "overshirt": "overshirt"}
SMILES = ["a wide toothy grin", "a small closed-mouth smile", "a friendly smile showing teeth",
          "a calm closed smile"]


def raw_answer(rng):
    """What the vision model would have answered for one made-up student (schema_gen.vlm_schema shape)."""
    look = rng.choice(["she", "he"])
    catalog = schema_gen.appearance_catalog()
    appearance = {
        "face": rng.choice(list(catalog.FACE_PROFILES)),
        "hair": rng.choice(HAIR_BY_LOOK[look]),
        "body": rng.choice(["neutral", "neutral", "slender", "slender", "broad", "stocky", "fuller"]),
        "outfit": rng.choice(["tee", "tee", "tee", "polo", "hoodie", "hoodie", "overshirt"]),
    }
    hair = rng.choice(HAIR_RARE) if rng.random() < 0.08 else rng.choice(HAIR_NATURAL)
    top, top_words = rng.choice(list(TOPS.items()))
    short_sleeves = catalog.OUTFITS[appearance["outfit"]]["sleeves"] == "short"
    shorts = short_sleeves and rng.random() < 0.4
    pants, pants_words = rng.choice(list((SHORTS if shorts else PANTS).items()))
    shoes, shoes_words = rng.choice(list(SHOES.items()))
    accessories = ["crossbody_strap"] if rng.random() < 0.35 else []
    smile = rng.choice(SMILES)
    traits = [f"{look} has {catalog.PROFILE_DESCRIPTIONS['hair'][appearance['hair']]}",
              f"{look} has {smile}"]
    if "teeth" not in smile and "toothy" not in smile:
        traits.append("closed lips")
    if rng.random() < 0.25:
        traits.append("eyes that crinkle when smiling")
    return look, {
        "appearance": appearance,
        "colors": {"skin": rng.choice(SKIN), "hair": hair, "eyes": rng.choice(EYES), "top": top,
                   "pants": pants, "shoes": shoes},
        "outfit": {"top": f"{top_words} {OUTFIT_WORDS[appearance['outfit']]}", "pants": pants_words,
                   "shoes": shoes_words,
                   "accessory": "a backpack strap across the chest" if accessories else "none",
                   "headwear": "none"},
        "signature_traits": traits,
        "build": {"legwear": "shorts" if shorts else "long_pants", "accessories": accessories},
    }


def write_specs():
    rng = random.Random(SEED)
    names = {look: rng.sample(pool, len(pool)) for look, pool in NAMES.items()}
    more_rng = random.Random(SEED + 1)
    more = {look: more_rng.sample(pool, len(pool)) for look, pool in MORE_NAMES.items()}
    for i in range(1, COUNT + 1):
        cid = npc_id(i)
        look, raw = raw_answer(rng)
        spec, notes = spec_ai.repair(raw, cid, (names[look] or more[look]).pop())  # the worker's no-photo repair path
        spec["notes"] = "Campus NPC (random spec, tools/npcs/make_campus_npcs.py)"
        d = os.path.join(ART, cid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "character.json"), "w") as f:
            json.dump(spec, f, indent=2)
            f.write("\n")
        a = spec["appearance"]
        print(f"{cid} {spec['name']:<8} {a['face']:<6} {a['hair']:<8} {a['body']:<8} {a['outfit']:<9} "
              f"{spec['build']['legwear']:<10} {' '.join(spec['build']['accessories'])}"
              + (f"  [repair: {'; '.join(notes)}]" if notes else ""))


# ------------------------------------------------------------------ build (the worker's steps)
def build_one(cid, cfg):
    t0 = time.monotonic()
    work = tempfile.mkdtemp(prefix=f"{cid}_", dir=cfg.work_root)
    jlog = pipeline.JobLog()
    try:
        char_dir = os.path.join(work, "art", pipeline.BUILD_ID)
        os.makedirs(char_dir)
        with open(os.path.join(ART, cid, "character.json")) as f:
            spec = json.load(f)
        spec["id"] = pipeline.BUILD_ID  # built under the neutral id, renamed below like a guest deploy
        with open(os.path.join(char_dir, "character.json"), "w") as f:
            json.dump(spec, f, indent=2)
        pipeline.step_face(cfg, work, jlog)
        report = pipeline.step_build(cfg, work, jlog)
        pipeline.step_validate(cfg, work, jlog)
        dst = os.path.join(ACTORS, cid)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        actor_rename.rename_actor(os.path.join(work, "actors", pipeline.BUILD_ID), ACTORS, cid)
        front = os.path.join(work, "build", "previews", "front.png")
        if os.path.isfile(front):
            from PIL import Image
            Image.open(front).resize((256, 256), Image.LANCZOS).save(os.path.join(ART, cid, "front.png"),
                                                                     optimize=True)
        tris = (report.get("tris") or {}).get("Mario Mesh")
        return f"{cid}: ok in {time.monotonic() - t0:.0f} s ({tris} tris)"
    except Exception as e:
        log = os.path.join(cfg.work_root, f"{cid}.log")
        with open(log, "w") as f:
            f.write(jlog.text())
        raise RuntimeError(f"{cid}: {e} (log: {log})") from e
    finally:
        shutil.rmtree(work, ignore_errors=True)


def build(ids, jobs):
    blender = os.environ.get("BLENDER", DEFAULT_BLENDER)
    if not os.path.isfile(blender):
        sys.exit(f"Blender not found at {blender} (set BLENDER)")
    work_root = os.path.join(tempfile.gettempdir(), "sgl_npc_build")
    os.makedirs(work_root, exist_ok=True)
    cfg = pipeline.Config(repo=ROOT, blender=blender, work_root=work_root, python=sys.executable)
    failed = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(build_one, cid, cfg): cid for cid in ids}
        for fut in as_completed(futs):
            try:
                print(fut.result(), flush=True)
            except Exception as e:  # noqa: BLE001 - report every failure, then exit 1
                print(f"FAILED {e}", flush=True)
                failed.append(futs[fut])
    if failed:
        sys.exit(f"{len(failed)} failed: {' '.join(sorted(failed))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("specs")
    b = sub.add_parser("build")
    b.add_argument("--jobs", type=int, default=4)
    b.add_argument("--only", nargs="*")
    args = ap.parse_args()
    if args.cmd == "specs":
        write_specs()
    else:
        build(args.only or [npc_id(i) for i in range(1, COUNT + 1)], args.jobs)


if __name__ == "__main__":
    main()
