"""Offline checks of the generated Albert actor: python3 -m unittest discover -s tools/actors"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_albert  # noqa: E402


class AlbertActorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.geo, cls.header, cls.ntris = make_albert.build()

    def test_committed_files_are_up_to_date(self):
        for name, text in (("model.inc.c", self.model), ("geo.inc.c", self.geo), ("geo_header.h", self.header)):
            path = os.path.join(make_albert.OUT, name)
            with open(path) as f:
                self.assertEqual(f.read(), text, "%s is stale: run python3 -I tools/actors/make_albert.py" % name)

    def test_vertex_loads_and_triangles(self):
        sizes = {m.group(1): int(m.group(2)) for m in re.finditer(r"Vtx (\w+)\[(\d+)\] = \{", self.model)}
        for m in re.finditer(r"Vtx (\w+)\[(\d+)\] = \{(.*?)\n\};", self.model, re.S):
            rows = re.findall(r"\{\{\{(-?\d+), (-?\d+), (-?\d+)\}", m.group(3))
            self.assertEqual(len(rows), int(m.group(2)), m.group(1))
            for row in rows:
                for c in row:
                    self.assertTrue(-32768 <= int(c) <= 32767)
        for m in re.finditer(r"Gfx (\w+_tri_\d+)\[\] = \{(.*?)\};", self.model, re.S):
            body = m.group(2)
            load = re.search(r"gsSPVertex\((\w+) \+ 0, (\d+), 0\)", body)
            n = int(load.group(2))
            self.assertLessEqual(n, make_albert.MAX_LOAD)
            self.assertEqual(n, sizes[load.group(1)])
            for t in re.findall(r"gsSP1Triangle\((\d+), (\d+), (\d+), 0\)", body):
                self.assertTrue(all(int(i) < n for i in t), m.group(1))

    def test_every_reference_is_defined(self):
        defined = set(re.findall(r"^(?:Gfx|Vtx|Lights1) (\w+)", self.model, re.M))
        used = set(re.findall(r"gsSPDisplayList\((\w+)\)", self.model))
        used |= set(re.findall(r"gsSPSetLights1\((\w+)\)", self.model))
        used |= set(re.findall(r"GEO_DISPLAY_LIST\(LAYER_\w+, (\w+)\)", self.geo))
        self.assertEqual(used - defined, set())
        self.assertIn("const GeoLayout albert_geo[]", self.geo)
        self.assertIn("GEO_SWITCH_CASE(2, geo_switch_anim_state)", self.geo)
        self.assertEqual(self.geo.count("GEO_OPEN_NODE()"), self.geo.count("GEO_CLOSE_NODE()"))

    def test_size_is_sane(self):
        self.assertTrue(500 < self.ntris < 4000, self.ntris)
        ys = [int(y) for y in re.findall(r"\{\{\{-?\d+, (-?\d+), -?\d+\}", self.model)]
        self.assertTrue(min(ys) >= -1 and 170 <= max(ys) <= 200, (min(ys), max(ys)))   # ~1.9 m, feet on y = 0


if __name__ == "__main__":
    unittest.main()
