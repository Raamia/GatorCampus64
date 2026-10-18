"""Offline checks of the generated mini bull (the Goomba replacement): python3 -m unittest discover -s tools/actors"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_minibull  # noqa: E402

# the vanilla Goomba skeleton (sm64coopdx actors/goomba/geo.inc.c): its walk animation drives these parts, so the
# replacement must keep the same animated parts, in the same order, at the same translations
VANILLA_PARTS = [(0, 0, 0), (0, 0, 0), (48, 0, 0), (48, 0, 0), (-60, -16, 45), (0, 0, 0), (-60, -16, -45), (0, 0, 0)]


class MiniBullTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.geo, cls.header, cls.ntris = make_minibull.build()

    def test_committed_files_are_up_to_date(self):
        for name, text in (("model.inc.c", self.model), ("geo.inc.c", self.geo), ("geo_header.h", self.header)):
            with open(os.path.join(make_minibull.OUT, name)) as f:
                self.assertEqual(f.read(), text, "goomba/%s is stale: run python3 -I tools/actors/make_minibull.py" % name)

    def test_replaces_the_goomba_with_its_skeleton(self):
        self.assertIn("const GeoLayout goomba_geo[]", self.geo)
        self.assertIn("GEO_SCALE(0x00, 16384)", self.geo)
        self.assertIn("GEO_SWITCH_CASE(2, geo_switch_anim_state)", self.geo)   # the blink
        parts = [tuple(int(v) for v in m) for m in
                 re.findall(r"GEO_ANIMATED_PART\(LAYER_OPAQUE, (-?\d+), (-?\d+), (-?\d+), \w+\)", self.geo)]
        self.assertEqual(parts, VANILLA_PARTS)
        self.assertEqual(self.geo.count("GEO_OPEN_NODE()"), self.geo.count("GEO_CLOSE_NODE()"))

    def test_every_reference_is_defined_and_loads_fit(self):
        defined = set(re.findall(r"^(?:Gfx|Vtx|Lights1) (\w+)", self.model, re.M))
        used = set(re.findall(r"gsSPDisplayList\((\w+)\)", self.model)) | set(re.findall(r"gsSPSetLights1\((\w+)\)", self.model))
        used |= set(re.findall(r"GEO_ANIMATED_PART\(LAYER_OPAQUE, -?\d+, -?\d+, -?\d+, (\w+)\)", self.geo)) - {"NULL"}
        self.assertEqual(used - defined, set())
        sizes = {m.group(1): int(m.group(2)) for m in re.finditer(r"Vtx (\w+)\[(\d+)\] = \{", self.model)}
        for m in re.finditer(r"gsSPVertex\((\w+) \+ 0, (\d+), 0\)", self.model):
            self.assertLessEqual(int(m.group(2)), 32)
            self.assertEqual(int(m.group(2)), sizes[m.group(1)])
        for v in re.findall(r"\{\{\{(-?\d+), (-?\d+), (-?\d+)\}", self.model):
            self.assertTrue(all(-32768 <= int(c) <= 32767 for c in v))

    def test_standing_on_the_ground_goomba_sized(self):
        W = make_minibull.rest_world()
        owner = {"body": "body", "eyes": "eyes", "eyes_blink": "eyes", "foot_l": "foot_l", "foot_r": "foot_r"}
        ys = []
        for part, mesh in make_minibull.build_parts().items():
            for tris in mesh.tris.values():
                for tri, _ in tris:
                    ys += [make_minibull.apply(p, W[owner[part]])[1] for p in tri]
        self.assertTrue(-3 < min(ys) < 8, min(ys))       # hooves on the ground
        self.assertTrue(45 < max(ys) < 70, max(ys))      # horn tips: about a Goomba's height (x1.5 in game)


if __name__ == "__main__":
    unittest.main()
