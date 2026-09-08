"""All six saved boards must remain visible at every check stage."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_release_candidate as release
from board_release_contract import BOARD_PROJECTS
from report_schematic_pcb_eco import PROJECTS


class Coverage(unittest.TestCase):
    def test_skipped_native_parity_is_not_an_empty_pass(self):
        output = ("Failed to fetch schematic netlist for parity tests.\n"
                  "Schematic parity tests require a fully annotated schematic.\n"
                  "Found 0 violations\nFound 499 unconnected items\n")
        self.assertFalse(release.native_parity_completed(output, {'schematic_parity': []}))
        self.assertFalse(release.native_parity_completed('', {'schematic_parity': []}))
        self.assertTrue(release.native_parity_completed(
            'Found 0 violations\nFound 0 schematic parity issues\n', {'schematic_parity': []}))
        self.assertFalse(release.native_parity_completed(
            'Found 1 schematic parity issue\n', {'schematic_parity': []}))

    def test_all_stages_default_to_six_real_projects(self):
        expected=[release.ROOT/item['pcb'] for item in BOARD_PROJECTS.values()]
        self.assertEqual(len(expected),6)
        for stage in ('schematic','routing','fabrication','production'):
            self.assertEqual(release.select_pcbs(stage,None),expected)
        self.assertEqual(set(PROJECTS),set(BOARD_PROJECTS))
        self.assertEqual([item['copper_layers'] for item in BOARD_PROJECTS.values()],[8,8,8,4,2,4])
        for item in BOARD_PROJECTS.values():
            self.assertEqual(release.schematic_for_board(release.ROOT/item['pcb']),release.ROOT/item['schematic'])

    def test_schematic_coverage_cannot_claim_fabrication(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pcb=root/'explicit.kicad_pcb';sch=pcb.with_suffix('.kicad_sch')
            pcb.write_text('board');sch.write_text('schematic')
            with patch.object(release,'native_board_stats',return_value={'native_airwires':812,'copper_layers':8}):
                result=release.selection_coverage([pcb],'schematic')
            self.assertFalse(result['all_six_selected'])
            self.assertEqual(result['boards'][0]['native']['native_airwires'],812)
            self.assertFalse(result['boards'][0]['manufacturing']['fabrication_files_checked'])
            self.assertEqual(result['boards'][0]['physical_validation'],'NOT_RUN')

    def test_unverified_manufacturing_directory_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'manufacturing/center').mkdir(parents=True)
            (root/'manufacturing/center/manifest.json').write_text('{"status":"APPROVED"}')
            with patch.object(release,'ROOT',root):
                self.assertFalse(release.manufacturing_coverage('center')['fabrication_files_checked'])
                self.assertEqual(release.manufacturing_coverage('radio')['status'],'MISSING')


if __name__=='__main__':unittest.main()
