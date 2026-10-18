"""Map and NPC integration regressions on synthetic geometry; no Blender needed."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from geometry import Collision
from navigation import supported, excluded, fingerprint, coverage
from placements import resolve, anchor_position
from test_area_routes import collision, floor
import area_routes


class NavigationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def col(self, quads):
        p = self.root/'collision.inc.c'
        p.write_text(collision(quads))
        return Collision(p)

    def test_elevations_slopes_and_wrong_floors(self):
        for y in (-150, 150):
            self.assertEqual(supported(self.col([floor(y)]), 400, 400, -200, 300), y)
        slope = [(x, round(x/5), z) for x, y, z in floor(0)]
        self.assertEqual(supported(self.col([slope]), 400, 400, -200, 300), 80)
        self.assertIsNone(supported(self.col([floor(0), floor(200)]), 400, 400, -200, 300))
        self.assertEqual(supported(self.col([floor(0), floor(600)]), 400, 400, -25, 25), 0)

    def test_walls_ceilings_cliffs_and_missing_floor(self):
        wall = [(500,0,0), (500,0,1000), (500,250,1000), (500,250,0)]
        self.assertIsNone(supported(self.col([floor(0),wall]), 480, 400, -25, 25))
        self.assertIsNone(supported(self.col([floor(0),list(reversed(floor(150)))]),400,400,-25,25))
        self.assertIsNone(supported(self.col([floor(0,0,450)]),440,400,-25,25))
        self.assertIsNone(supported(self.col([]),400,400,-25,25))

    def test_named_anchor_changes_are_followed_and_missing_fails(self):
        p = self.root/'points.json'
        p.write_text(json.dumps({'entry': {'name': 'console', 'game': [100,0,200]}}))
        source = {'file': 'points.json', 'point': 'console'}
        self.assertEqual(anchor_position(source,self.root),[100,0,200])
        p.write_text(json.dumps({'entry': {'name': 'console', 'game': [150,80,250]}}))
        self.assertEqual(anchor_position(source,self.root),[150,80,250])
        with self.assertRaises(ValueError):
            anchor_position({'file':'points.json','point':'missing'},self.root)

    def test_required_placement_relocates_deterministically_or_fails(self):
        spec = {'anchor': 'console', 'area': 1, 'height_tolerance':25,'radius':0,'search_radius':300}
        config = {'exclusions':[{'slot':'wf','area':1,'min':[450,-10,450],'max':[550,250,550]}]}
        col = self.col([floor(100)])
        p = resolve(col,spec,(500,100,500),[],config,'wf')
        self.assertNotEqual(p,(500,100,500))
        self.assertEqual(p,resolve(col,spec,(500,100,500),[],config,'wf'))
        self.assertFalse(excluded(config,'wf',1,*p,70,260))
        with self.assertRaises(ValueError):
            resolve(self.col([]),spec,(500,100,500),[],config,'wf')

    def test_source_receipt_and_coverage_fail_closed(self):
        p = self.root/'mesh'; p.write_text('one')
        before = fingerprint(['mesh'],self.root); p.write_text('two')
        self.assertNotEqual(before,fingerprint(['mesh'],self.root))
        with self.assertRaises(FileNotFoundError): fingerprint(['missing'],self.root)
        config={'coverage_regions':[{'name':'plaza','slot':'wf','area':1,'bounds':[0,0,10,10],'minimum_nodes':2}]}
        with self.assertRaises(ValueError):coverage(config,'wf',1,[(0,0,0)],[])
        self.assertTrue(coverage(config,'wf',1,[(0,0,0),(5,0,5)],[(1,2)]))

    def test_outdoor_graph_follows_slope_without_linking_across_cliff(self):
        base=self.root/'mods/sgl64/levels/ccm'; (base/'area_1').mkdir(parents=True)
        slope=[(x,round(x/5),z) for x,y,z in floor(0)]
        (base/'area_1/collision.inc.c').write_text(collision([slope]))
        (base/'script.c').write_text('AREA(1, test),\nEND_AREA(),')
        config={'exclusions':[],'outdoor_regions':{'ccm':{'height_range':[-200,300]}}}
        with patch.object(area_routes,'ROOT',self.root):
            nodes,links=area_routes.build('ccm',1,[0],200,True,config)
        self.assertTrue(links)
        self.assertTrue(any(nodes[a-1][1] != nodes[b-1][1] for a,b in links))


if __name__ == '__main__':
    unittest.main()
