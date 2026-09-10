"""All six saved boards must remain visible at every check stage."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_release_candidate as release
from board_release_contract import BOARD_PROJECTS
from report_schematic_pcb_eco import PROJECTS


class Coverage(unittest.TestCase):
    def source_fixture(self, root):
        for item in BOARD_PROJECTS.values():
            for key in ('pcb', 'schematic'):
                path = root / item[key]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('saved ' + key)
                path.with_suffix('.kicad_pro').write_text('saved settings')

    def test_regeneration_covers_bms_and_retains_saved_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.source_fixture(root)
            called = []
            def generate(command, cwd, label):
                self.assertEqual(cwd, root.resolve())
                called.extend(release.SOURCE_GENERATORS[command[1]])
                for board in release.SOURCE_GENERATORS[command[1]]:
                    path = root / BOARD_PROJECTS[board]['schematic']
                    path.write_text('fresh schematic')
                    path.with_suffix('.kicad_pro').write_text('generator-only settings')
                return ''
            with patch.object(release, 'run_command', side_effect=generate):
                release.regenerate_project_sources(root)
            self.assertEqual(set(called), set(BOARD_PROJECTS))
            for item in BOARD_PROJECTS.values():
                self.assertEqual((root / item['schematic']).read_text(), 'fresh schematic')
                self.assertEqual((root / item['pcb']).read_text(), 'saved pcb')
                self.assertEqual((root / item['schematic']).with_suffix('.kicad_pro').read_text(), 'saved settings')

    def test_missing_bms_regeneration_is_rejected(self):
        generators = {k: v for k, v in release.SOURCE_GENERATORS.items() if 'bms' not in v}
        with tempfile.TemporaryDirectory() as temp, patch.object(release, 'SOURCE_GENERATORS', generators):
            with self.assertRaisesRegex(RuntimeError, 'all six boards'):
                release.regenerate_project_sources(Path(temp))

    def test_generator_must_not_replace_a_placed_board(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.source_fixture(root)
            def damage(command, cwd, label):
                (root / BOARD_PROJECTS['bms']['pcb']).write_text('recreated board')
                return ''
            with patch.object(release, 'run_command', side_effect=damage):
                with self.assertRaisesRegex(RuntimeError, 'changed PCB files: bms/bms.kicad_pcb'):
                    release.regenerate_project_sources(root)

    def test_canonical_regeneration_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'temporary project copy'):
            release.regenerate_project_sources(release.ROOT)

    def test_local_library_drift_cannot_hide_behind_same_part_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root, candidate = Path(temp) / 'saved', Path(temp) / 'candidate'
            for folder in (root, candidate):
                (folder / 'gen').mkdir(parents=True)
                (folder / 'ducktop2.pretty').mkdir()
                (folder / 'gen/power.kicad_sym').write_text('same symbol')
            (root / 'ducktop2.pretty/power.kicad_mod').write_text('saved pads')
            (candidate / 'ducktop2.pretty/power.kicad_mod').write_text('different pads')
            with patch.object(release, 'ROOT', root):
                self.assertEqual(release.generated_schematic_drift(candidate),
                                 ['ducktop2.pretty/power.kicad_mod'])

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
