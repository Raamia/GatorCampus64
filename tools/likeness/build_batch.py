#!/usr/bin/env python3
"""Build the review gallery locally. No production services or Qwen calls.

python3 tools/likeness/build_batch.py [--only f01 h01] [--jobs 2]
python3 -m http.server 5174 --bind 127.0.0.1 --directory dist/likeness-round-01
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shutil
import subprocess

from catalog import entries

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--output", type=Path, default=ROOT / "dist/likeness-round-01")
    ap.add_argument("--blender", default=str(ROOT / "tools/vendor/blender/blender"))
    ap.add_argument("--integrated", action="store_true", help="Build through the versioned production appearance path")
    ap.add_argument("--gallery-only", action="store_true", help="Refresh gallery files from existing models without rebuilding")
    args = ap.parse_args()
    out = args.output.resolve()
    (out / "logs").mkdir(parents=True, exist_ok=True)
    requested = [e for e in entries() if not args.only or e["id"] in args.only]
    if args.only and set(args.only) - {e["id"] for e in requested}:
        ap.error("unknown specimen ID")
    if args.gallery_only:
        requested = []
    env = dict(os.environ, BLENDER_USER_SCRIPTS=str(ROOT / "tools/blender-scripts"),
               PYTHONDONTWRITEBYTECODE="1")

    def build(entry):
        code = entry["id"]
        cmd = [args.blender, "--background", "--factory-startup", "--threads", "4",
               "--python-exit-code", "1", "--python", str(HERE / "build_one.py"), "--", code, str(out)]
        if args.integrated:
            cmd.append("--integrated")
        with (out / "logs" / f"{code}.log").open("w") as log:
            proc = subprocess.run(cmd, env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        if proc.returncode:
            raise RuntimeError(f"{code}: Blender exited {proc.returncode}; see {out / 'logs' / (code + '.log')}")
        print(f"Built {code}: {entry['label']}", flush=True)

    failures = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        for future in as_completed([executor.submit(build, entry) for entry in requested]):
            try:
                future.result()
            except Exception as error:
                failures.append(str(error))
                print(error, flush=True)
    records = []
    for entry in entries():
        p = out / "models" / entry["id"] / "review.json"
        if p.exists():
            record = json.loads(p.read_text())
            if args.integrated:
                record["integrated"] = True
                if entry["group"] == "Bodies":
                    record["note"] = "Same height, head and T-shirt. Compare shoulder, waist, hip and limb proportions."
            records.append(record)
    (out / "catalog.json").write_text(json.dumps(records, indent=2) + "\n")
    for name in ("index.html", "gallery.js", "gallery.css"):
        shutil.copyfile(HERE / name, out / name)
    if args.integrated:
        index = out / "index.html"
        index.write_text(index.read_text().replace('<body>', '<body data-batch="integrated-v1">')
                         .replace('ROUND 01 <i></i> READY FOR REVIEW', 'APPROVED SET <i></i> INTEGRATED')
                         .replace('A first look.', 'The approved set.')
                         .replace('Round 01 · Synthetic shape studies; no reference photos used.',
                                  'Integrated set · Synthetic shape studies; no reference photos used.')
                         .replace('Body and garment animation fitting is pending.',
                                  'Joint fitting checked; in-game review pending.'))
    viewer = ROOT / "companion/app/node_modules/@google/model-viewer/dist/model-viewer.min.js"
    shutil.copyfile(viewer, out / "model-viewer.min.js")
    from contact_sheet import make_sheet
    make_sheet(out)
    print(f"Gallery: {out} ({len(records)} models)", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
