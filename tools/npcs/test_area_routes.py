"""Geometry regressions for indoor crowd routes; no Blender or live engine needed."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import area_routes


def collision(quads):
    lines = []
    for corners in quads:
        for x, y, z in corners:
            lines.append(f'COL_VERTEX({x}, {y}, {z}),')
    for i in range(len(quads)):
        a = i * 4
        lines.extend([f'COL_TRI({a}, {a+1}, {a+2}),', f'COL_TRI({a}, {a+2}, {a+3}),'])
    return '\n'.join(lines)


def floor(y, x0=0, x1=1000):
    return [(x0,y,0), (x0,y,1000), (x1,y,1000), (x1,y,0)]


class AreaRoutesTest(unittest.TestCase):
    def build(self, quads, heights=(0,), objects=''):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'mods/sgl64/levels/ccm'
            (base / 'area_1').mkdir(parents=True)
            (base / 'area_1/collision.inc.c').write_text(collision(quads))
            (base / 'script.c').write_text('AREA(1, test),\n' + objects + '\nEND_AREA(),')
            with patch.object(area_routes, 'ROOT', root):
                return area_routes.build('ccm', 1, heights, 200)

    def test_wall_splits_rooms_and_floors_never_connect(self):
        wall = [(500,0,0), (500,0,1000), (500,250,1000), (500,250,0)]
        nodes, links = self.build([floor(0), floor(600), wall], (0,600))
        self.assertTrue(links)
        self.assertTrue(any(x < 500 and y == 0 for x,y,z in nodes))
        self.assertTrue(any(x > 500 and y == 0 for x,y,z in nodes))
        for i,j in links:
            a,b = nodes[i-1], nodes[j-1]
            self.assertEqual(a[1], b[1])
            if a[1] == 0:
                self.assertFalse(min(a[0],b[0]) < 500 < max(a[0],b[0]))

    def test_missing_floor_and_low_ceiling_reject_paths(self):
        ceiling = list(reversed(floor(150)))
        self.assertEqual(self.build([floor(0), ceiling]), ([], []))
        nodes, links = self.build([floor(0, 0, 450), floor(0, 550, 1000)])
        self.assertTrue(links)
        for i,j in links:
            a,b = nodes[i-1], nodes[j-1]
            self.assertFalse(min(a[0],b[0]) < 500 < max(a[0],b[0]))

    def test_static_objects_keep_clearance(self):
        nodes, links = self.build([floor(0)], objects='OBJECT(MODEL_TREE, 400, 0, 400, 0, 0, 0, 0, bhvTree),')
        self.assertTrue(links)
        self.assertNotIn((400,0,400), nodes)
        for i,j in links:
            a,b = nodes[i-1], nodes[j-1]
            for k in range(11):
                x = a[0] + (b[0]-a[0])*k/10
                z = a[2] + (b[2]-a[2])*k/10
                self.assertGreaterEqual((x-400)**2 + (z-400)**2, 160**2)


if __name__ == '__main__':
    unittest.main()
