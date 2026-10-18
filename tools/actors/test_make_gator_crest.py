"""Checks the generated Gator Crest replacement for MODEL_STAR."""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_gator_crest  # noqa: E402


class GatorCrestActorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.geo, cls.header, cls.ntris, cls.mesh = make_gator_crest.build()

    def test_committed_files_match_generator(self):
        for filename, expected in (("model.inc.c", self.model), ("geo.inc.c", self.geo),
                                   ("geo_header.h", self.header)):
            path = os.path.join(make_gator_crest.OUT, filename)
            with open(path) as f:
                self.assertEqual(f.read(), expected, "%s stale: run tools/actors/make_gator_crest.py" % filename)

    def test_replaces_star_appearance_and_keeps_pickup_contract(self):
        self.assertIn('"MODEL_STAR"', Path(make_gator_crest.ROOT,
                                             "tools/blender/dynos_symbols_v1.5.1.json").read_text())
        self.assertIn('"star_geo"', Path(make_gator_crest.ROOT,
                                           "tools/blender/dynos_symbols_v1.5.1.json").read_text())
        self.assertIn("const GeoLayout star_geo[]", self.geo)
        self.assertIn("sgl_crest_crest_mesh_layer_1", self.geo)
        self.assertIn("bhvStar", self.geo + self.header + self.model)  # documented on the generated root
        levels = Path(make_gator_crest.ROOT, "mods/sgl64/levels").rglob("script.c")
        self.assertTrue(any("MODEL_STAR" in p.read_text() and "bhvStar" in p.read_text() for p in levels))

    def test_all_model_references_and_vertex_loads_are_valid(self):
        defined = set(re.findall(r"^(?:Gfx|Vtx|Lights1) (\w+)", self.model, re.M))
        used = set(re.findall(r"gsSPDisplayList\((\w+)\)", self.model))
        used |= set(re.findall(r"gsSPSetLights1\((\w+)\)", self.model))
        used |= set(re.findall(r"GEO_DISPLAY_LIST\(LAYER_\w+, (\w+)\)", self.geo))
        self.assertEqual(used - defined, set())
        sizes = {m.group(1): int(m.group(2)) for m in re.finditer(r"Vtx (\w+)\[(\d+)\] = \{", self.model)}
        for m in re.finditer(r"gsSPVertex\((\w+) \+ 0, (\d+), 0\)", self.model):
            self.assertLessEqual(int(m.group(2)), make_gator_crest.G.MAX_LOAD)
            self.assertEqual(int(m.group(2)), sizes[m.group(1)])
        for vertex in re.findall(r"\{\{\{(-?\d+), (-?\d+), (-?\d+)\}", self.model):
            self.assertTrue(all(-32768 <= int(c) <= 32767 for c in vertex))
        self.assertLess(self.ntris, 1500)

    def test_crest_fits_the_star_pickup_scale(self):
        vertices = [p for tris in self.mesh.tris.values() for tri, _ in tris for p in tri]
        self.assertGreaterEqual(min(p[1] for p in vertices), -1)
        self.assertGreater(max(p[1] for p in vertices), 80)
        self.assertLess(max(abs(p[0]) for p in vertices), 50)
        self.assertGreater(max(p[2] for p in vertices), 15)
        self.assertLess(min(p[2] for p in vertices), -15)


if __name__ == "__main__":
    unittest.main()
