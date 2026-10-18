"""Refresh GLBs from saved review .blend files after a browser material change.

blender --background --python tools/likeness/refresh_browser.py -- <batch-dir>
"""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/blender"))
from sgl_blender import setup_fast64
from sgl_browser_model import export_browser_model

batch = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
for record in json.loads((batch / "catalog.json").read_text()):
    folder = batch / "models" / record["id"]
    bpy.ops.wm.open_mainfile(filepath=str(folder / (record["id"] + ".blend")), load_ui=False)
    setup_fast64()
    export_browser_model(str(folder / "model.glb"))
    print("REFRESHED", record["id"], flush=True)
