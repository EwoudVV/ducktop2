"""Keep the metal carrier connected and its retention clear of the keyboard."""
import unittest
import check_cooler
import keyboard_mounts as k
from cad import box,cylinder
from review import intersection_volume,bbox_overlap
from cables import polygon_prism


class KeyboardMounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plate,cls.film=k.plate_and_film()
        cls.parts=k.parts()

    def test_pipe_and_switch_cuts_leave_one_plate(self):
        self.assertTrue(self.plate.isValid())
        self.assertEqual(len(self.plate.Solids()),1)
        self.assertAlmostEqual(self.plate.BoundingBox().zlen,1.2,places=5)
        self.assertTrue(self.film.isValid())
        self.assertEqual(len(self.film.Solids()),1)
        self.assertAlmostEqual(self.film.BoundingBox().zmin,21.2,places=5)
        self.assertAlmostEqual(self.film.BoundingBox().zmax,21.327,places=5)

    def test_all_clinch_sites_keep_the_required_edge_distance(self):
        for x,y,_ in k.CLIPS:
            ring=cylinder(x,y,20.4,4.8,.1).cut(cylinder(x,y,20.3,2.12,.3))
            self.assertAlmostEqual(intersection_volume(ring,self.plate),ring.Volume(),delta=1e-5)
        bars={p['name']:p for p in self.parts if p['name'].startswith('keyboard-support-bar-')}
        for i,(side,y) in enumerate(k.SUPPORTS,1):
            x=37 if side=='left' else 321
            ring=cylinder(x,y,18.8,4.8,.1).cut(cylinder(x,y,18.7,2.12,.3))
            self.assertAlmostEqual(intersection_volume(ring,bars[f'keyboard-support-bar-{i}']['shape']),ring.Volume(),delta=1e-5)

    def test_clips_clear_populated_front_courtyards(self):
        clips=[p for p in self.parts if p['name'].startswith('keyboard-edge-clip-')]
        for fp in k.INV['footprints']:
            for ring in fp['courtyards']['front']:
                shape=polygon_prism([[x+24.75,y+19.7] for x,y in ring],22.127,5)
                for clip in clips:
                    if bbox_overlap(shape,clip['shape']):
                        self.assertLess(intersection_volume(shape,clip['shape']),.01,(fp['reference'],clip['name']))

    def test_retention_keeps_nominal_board_clear(self):
        board=box(42.25,20,21.327,273.5,80,.8)
        for p in self.parts:
            if p['name'].startswith('keyboard-edge-clip-'):
                self.assertLess(intersection_volume(board,p['shape']),.01,p['name'])
        self.assertAlmostEqual(k.config()['retention']['toe_bottom_H']-(21.327+.8),.073,places=6)

    def test_fastener_envelopes_fit_their_own_hardware(self):
        for i in range(1,9):
            clip=next(p['shape'] for p in self.parts if p['name']==f'keyboard-edge-clip-{i}')
            screw=next(p['shape'] for p in self.parts if p['name']==f'keyboard-clip-screw-{i}')
            nut=next(p['shape'] for p in self.parts if p['name']==f'keyboard-clip-nut-{i}')
            self.assertLess(intersection_volume(clip,screw),.01)
            self.assertLess(intersection_volume(nut,screw),.01)
        cap=next(p['shape'] for p in self.parts if p['name']=='keyboard-center-stop-cap')
        self.assertAlmostEqual(20-cap.BoundingBox().zmax,.3,places=5)


if __name__=='__main__':unittest.main()
