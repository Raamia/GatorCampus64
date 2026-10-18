"""Checks the generated ride gator that replaces MODEL_KOOPA_SHELL."""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_ride_gator  # noqa: E402


class RideGatorActorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.geo, cls.header, cls.ntris, cls.mesh = make_ride_gator.build()

    def test_committed_files_match_generator(self):
        for filename, expected in (("model.inc.c", self.model), ("geo.inc.c", self.geo),
                                   ("geo_header.h", self.header)):
            path = os.path.join(make_ride_gator.OUT, filename)
            with open(path) as f:
                self.assertEqual(f.read(), expected, "%s stale: run tools/actors/make_ride_gator.py" % filename)

    def test_replaces_the_koopa_shell_and_keeps_the_ride(self):
        symbols = Path(make_ride_gator.ROOT, "tools/blender/dynos_symbols_v1.5.1.json").read_text()
        self.assertIn('"koopa_shell_geo"', symbols)
        self.assertIn('"bhv_koopa_shell_loop"', symbols)
        self.assertIn("const GeoLayout koopa_shell_geo[]", self.geo)
        self.assertIn("sgl_ride_gator_gator_mesh_layer_1", self.geo)
        self.assertEqual(os.path.basename(make_ride_gator.OUT), "koopa_shell")
        levels = Path(make_ride_gator.ROOT, "mods/sgl64/levels").rglob("script.c")
        self.assertTrue(any("MODEL_KOOPA_SHELL" in p.read_text() and "bhvKoopaShell" in p.read_text()
                            for p in levels))
        lua = Path(make_ride_gator.ROOT, "mods/sgl64/sgl_ride_gator.lua").read_text()
        self.assertIn("hook_behavior(id_bhvKoopaShell, OBJ_LIST_LEVEL, false", lua)

    def test_all_model_references_and_vertex_loads_are_valid(self):
        defined = set(re.findall(r"^(?:Gfx|Vtx|Lights1) (\w+)", self.model, re.M))
        used = set(re.findall(r"gsSPDisplayList\((\w+)\)", self.model))
        used |= set(re.findall(r"gsSPSetLights1\((\w+)\)", self.model))
        used |= set(re.findall(r"GEO_DISPLAY_LIST\(LAYER_\w+, (\w+)\)", self.geo))
        self.assertEqual(used - defined, set())
        sizes = {m.group(1): int(m.group(2)) for m in re.finditer(r"Vtx (\w+)\[(\d+)\] = \{", self.model)}
        for m in re.finditer(r"gsSPVertex\((\w+) \+ 0, (\d+), 0\)", self.model):
            self.assertLessEqual(int(m.group(2)), make_ride_gator.G.MAX_LOAD)
            self.assertEqual(int(m.group(2)), sizes[m.group(1)])
        for vertex in re.findall(r"\{\{\{(-?\d+), (-?\d+), (-?\d+)\}", self.model):
            self.assertTrue(all(-32768 <= int(c) <= 32767 for c in vertex))
        self.assertLess(self.ntris, 2000)

    def test_gator_fits_under_the_rider(self):
        vertices = [p for tris in self.mesh.tris.values() for tri, _ in tris for p in tri]
        # sits on the ground, snout toward +Z (the rider's heading), tail toward -Z
        self.assertGreaterEqual(min(p[1] for p in vertices), -0.5)
        self.assertGreater(max(p[2] for p in vertices), 80)
        self.assertLess(min(p[2] for p in vertices), -100)
        self.assertLess(max(abs(p[0]) for p in vertices), 45)
        # the back under the rider's feet (over the shell's 50-unit hitbox) stays near the shell's height
        under_rider = [p[1] for p in vertices if abs(p[0]) < 15 and abs(p[2]) < 15]
        self.assertTrue(30 < max(under_rider) < 45, max(under_rider))


if __name__ == "__main__":
    unittest.main()
