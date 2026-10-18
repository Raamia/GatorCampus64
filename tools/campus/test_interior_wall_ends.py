"""Visual closure regressions for the reported Marston and Library West seams.

Run: python3 -m unittest discover -s tools/campus -p test_interior_wall_ends.py
"""
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


def load_interior(name):
    spec = importlib.util.spec_from_file_location(name, HERE / 'interiors' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def partitions(module, floor):
    cls = module.Marston if module.KEY == 'marston' else module.LibWest
    model = cls(module.load_layout())
    if hasattr(module, 'LAYOUT_CACHE'):
        module.LAYOUT_CACHE.clear()
        module.LAYOUT_CACHE.update(model.layout)
    for fid in module.FLOORS:
        model.regions[fid] = module.regions_of(model, fid)
    module.plan_doors(model)
    prop = module.K.Prop('partition_test')
    module.build_partitions(model, floor, prop)
    return prop


def opaque_face_at(module, mesh, point, normal):
    """An outward-facing opaque rectangle covers the point, including its depth."""
    for poly in mesh.polys:
        if poly.mat not in ('int_plastic', 'int_ms_wall', 'int_drywall'):
            continue
        n = module.K.unit_normal(poly.pts)
        if sum(a * b for a, b in zip(n, normal)) < 0.99:
            continue
        lo = [min(p[i] for p in poly.pts) for i in range(3)]
        hi = [max(p[i] for p in poly.pts) for i in range(3)]
        if all(lo[i] - 1e-6 <= point[i] <= hi[i] + 1e-6 for i in range(3)):
            return True
    return False


class InteriorWallEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.marston = load_interior('marston')
        cls.libwest = load_interior('libwest')
        cls.ms = partitions(cls.marston, 'F2')
        cls.lw = partitions(cls.libwest, 'F1')

    def test_marston_entrance_corner_is_closed_on_both_outer_faces(self):
        # The old flat end-cap at y=-81.5 missed the west-facing slit, and
        # left the south face recessed from the adjoining horizontal wall.
        for inset in (0.025, 0.05, 0.075):
            for z in (0.05, 1.6, self.marston.CLEAR - 0.05):
                with self.subTest(inset=inset, z=z):
                    self.assertTrue(opaque_face_at(
                        self.marston, self.ms.visual,
                        (-65.3, -81.5 - inset, z), (-1, 0, 0)))
                    self.assertTrue(opaque_face_at(
                        self.marston, self.ms.visual,
                        (-65.2 - inset, -81.6, z), (0, -1, 0)))

    def test_corner_join_works_in_every_orientation_without_changing_collision(self):
        m = self.marston
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            with self.subTest(sx=sx, sy=sy):
                p = m.K.Prop('corner')
                for q in ((2 * sx, 0), (0, 2 * sy)):
                    m.thin_partition(p.visual, p.collision, (0, 0), q, 0, 3, 'solid')
                collision = repr(p.collision.polys)
                self.assertEqual(m.join_partition_corners(p.visual), 1)
                self.assertEqual(repr(p.collision.polys), collision)
                self.assertTrue(opaque_face_at(m, p.visual, (-0.1 * sx, -0.05 * sy, 1.5), (-sx, 0, 0)))
                self.assertTrue(opaque_face_at(m, p.visual, (-0.05 * sx, -0.1 * sy, 1.5), (0, -sy, 0)))
                before = len(p.visual.polys)
                self.assertEqual(m.join_partition_corners(p.visual), 0)
                self.assertEqual(len(p.visual.polys), before)

    def test_door_glass_and_t_junctions_are_not_filled(self):
        m = self.marston
        for mode in ('door', 'glass', 'tee', 'straight'):
            with self.subTest(mode=mode):
                p = m.K.Prop(mode)
                m.thin_partition(p.visual, p.collision, (0, 0), (2, 0), 0, 3, 'solid')
                q = (-2, 0) if mode == 'straight' else (0, 2)
                m.thin_partition(p.visual, p.collision, (0, 0), q, 0, 3,
                                 'glass' if mode == 'glass' else 'solid',
                                 doors=[(0, 1, 2.5)] if mode == 'door' else [])
                if mode == 'tee':
                    m.thin_partition(p.visual, p.collision, (-1, 0), (1, 0), 0, 3, 'solid')
                before = len(p.visual.polys)
                self.assertEqual(m.join_partition_corners(p.visual), 0)
                self.assertEqual(len(p.visual.polys), before)

    def test_libwest_elevator_junction_is_opaque_across_exposed_strip(self):
        for y in (271.11, 271.15, 271.19):
            for z in (0.05, 1.6, self.libwest.CLEAR - 0.05):
                with self.subTest(y=y, z=z):
                    self.assertTrue(opaque_face_at(
                        self.libwest, self.lw.visual, (45.4, y, z), (-1, 0, 0)))

    def test_libwest_cap_does_not_overlap_elevator_face(self):
        self.assertFalse(opaque_face_at(
            self.libwest, self.lw.visual, (45.4, 271.25, 1.6), (-1, 0, 0)))

    def test_marston_entrance_remains_open(self):
        # Centre of the four-metre vestibule doorway, below its transom.
        for mesh in (self.ms.visual, self.ms.collision):
            for p in mesh.polys:
                if all(abs(q[1] + 78.8) < 1e-6 for q in p.pts):
                    inside_x = min(q[0] for q in p.pts) < -67.2 < max(q[0] for q in p.pts)
                    inside_z = min(q[2] for q in p.pts) < 1.6 < max(q[2] for q in p.pts)
                    self.assertFalse(inside_x and inside_z, 'entrance must remain passable')


if __name__ == '__main__':
    unittest.main()
