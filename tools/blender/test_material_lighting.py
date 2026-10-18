import tempfile
import unittest
from pathlib import Path
from fix_material_lighting import check_source, fix_level

class Lighting(unittest.TestCase):
    def test_repair_and_idempotence(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'model.inc.c'
            p.write_text('Gfx mat_test[] = {\n\tgsSPEndDisplayList(),\n};\n')
            (Path(folder) / 'header.inc.h').write_text('')
            self.assertEqual(fix_level(folder), 1)
            result = p.read_text()
            check_source(result)
            self.assertEqual(fix_level(folder), 0)
            self.assertEqual(p.read_text(), result)
    def test_vertex_lit_and_existing_lights_preserved(self):
        source = ('Lights1 warm = gdSPDefLights1(1,2,3,4,5,6,7,8,9);\n'
                  'Gfx mat_warm[] = {\n\tgsSPSetLights1(warm),\n};\n'
                  'Gfx mat_vertex[] = {\n\tgsSPClearGeometryMode(G_LIGHTING),\n};\n')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'model.inc.c';p.write_text(source)
            self.assertEqual(fix_level(folder),0)
            self.assertEqual(p.read_text(),source)
    def test_missing_duplicate_and_dangling_rejected(self):
        for source in ['Gfx mat_a[] = {\n};\n', 'Gfx a[] = {};\nGfx a[] = {};\n',
                       'Gfx mat_a[] = {\n gsSPSetLights1(missing),\n};\n']:
            with self.assertRaises(ValueError):check_source(source)

if __name__ == '__main__':unittest.main()
