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
        self.assertEqual(self.geo.count("GEO_OPEN_NODE()"), self.geo.count("GEO_CLOSE_NODE()"))

    def test_skeleton_matches_the_lua_animations(self):
        # one GEO_ANIMATED_PART per joint, in JOINTS order (= the animation channel order of sgl_albert.lua)
        parts = re.findall(r"GEO_ANIMATED_PART\(LAYER_OPAQUE, (-?\d+), (-?\d+), (-?\d+), (\w+)\)", self.geo)
        self.assertEqual(len(parts), len(make_albert.JOINTS))
        for (name, parent, pivot), (x, y, z, dl) in zip(make_albert.JOINTS, parts):
            base = (0, 0, 0) if parent is None else make_albert.PIVOT[parent]
            self.assertEqual((int(x), int(y), int(z)), tuple(p - b for p, b in zip(pivot, base)), name)
            self.assertIn(dl, ("NULL", "albert_%s_mesh_layer_1" % name))
        lua = open(os.path.join(make_albert.ROOT, "mods", "sgl64", "sgl_albert.lua")).read()
        joints = re.search(r"ALBERT_JOINTS = \{([^}]*)\}", lua).group(1)
        self.assertEqual(re.findall(r'"(\w+)"', joints), [n for n, _, _ in make_albert.JOINTS])

    def test_size_is_sane(self):
        self.assertTrue(500 < self.ntris < 4000, self.ntris)
        parts = make_albert.build_parts()   # world coordinates at rest (the C files are relative to each joint)
        ys = [p[1] for m in parts.values() for ts in m.tris.values() for tri, _ in ts for p in tri]
        self.assertTrue(min(ys) >= -1 and 170 <= max(ys) <= 200, (min(ys), max(ys)))   # ~1.9 m, feet on y = 0


if __name__ == "__main__":
    unittest.main()
