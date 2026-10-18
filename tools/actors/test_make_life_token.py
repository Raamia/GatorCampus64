"""Checks the generated Gator life-token model: python3 -m unittest discover -s tools/actors"""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_life_token  # noqa: E402


class LifeTokenActorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.geo, cls.header, cls.ntris = make_life_token.build()

    def test_committed_files_match_generator(self):
        for filename, expected in (("model.inc.c", self.model), ("geo.inc.c", self.geo),
                                   ("geo_header.h", self.header)):
            path = os.path.join(make_life_token.OUT, filename)
            with open(path) as f:
                self.assertEqual(f.read(), expected, "%s stale: run tools/actors/make_life_token.py" % filename)

    def test_replaces_the_vanilla_1up_geo_symbol(self):
        self.assertIn("const GeoLayout mushroom_1up_geo[]", self.geo)
        self.assertIn("GEO_DISPLAY_LIST(LAYER_OPAQUE, sgl_life_medallion_mesh_layer_1)", self.geo)
        symbols = Path(make_life_token.ROOT, "tools/blender/dynos_symbols_v1.5.1.json").read_text()
        self.assertIn("mushroom_1up_geo", symbols)
        self.assertEqual(self.geo.count("GEO_OPEN_NODE()"), self.geo.count("GEO_CLOSE_NODE()"))

    def test_model_references_and_vertex_loads_are_valid(self):
        defined = set(re.findall(r"^(?:Gfx|Vtx|Lights1) (\w+)", self.model, re.M))
        used = set(re.findall(r"gsSPDisplayList\((\w+)\)", self.model))
        used |= set(re.findall(r"gsSPSetLights1\((\w+)\)", self.model))
        used |= set(re.findall(r"GEO_DISPLAY_LIST\(LAYER_\w+, (\w+)\)", self.geo))
        self.assertEqual(used - defined, set())
        sizes = {m.group(1): int(m.group(2)) for m in re.finditer(r"Vtx (\w+)\[(\d+)\] = \{", self.model)}
        for m in re.finditer(r"gsSPVertex\((\w+) \+ 0, (\d+), 0\)", self.model):
            self.assertLessEqual(int(m.group(2)), make_life_token.G.MAX_LOAD)
            self.assertEqual(int(m.group(2)), sizes[m.group(1)])
        self.assertLess(self.ntris, 3000)

    def test_existing_placements_keep_extra_life_behavior(self):
        levels = os.path.join(make_life_token.ROOT, "mods/sgl64/levels")
        placements = []
        for base, _, files in os.walk(levels):
            if "script.c" in files:
                text = Path(base, "script.c").read_text()
                placements += re.findall(r"OBJECT\(MODEL_1UP,[^\n]*bhv1Up\)", text)
        self.assertGreater(len(placements), 0)
        self.assertEqual(len(placements), sum("bhv1Up" in row for row in placements))


if __name__ == "__main__":
    unittest.main()
