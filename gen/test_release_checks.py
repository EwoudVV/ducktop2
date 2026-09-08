"""Checks for board selection, staging, and newly introduced DRC findings."""
import json
import io
from contextlib import redirect_stdout
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_release_candidate as release


class ReleaseChecks(unittest.TestCase):
    def test_default_fabrication_checks_current_boards(self):
        expected = [release.ROOT / name for name in release.ACTIVE_BOARDS]
        self.assertEqual(release.select_pcbs('fabrication', None), expected)
        self.assertEqual(release.select_pcbs('production', None), expected)
        self.assertNotIn('monolith', str(expected))

    def test_explicit_board_and_schematic_stage(self):
        pcb = release.ROOT / 'bms/bms.kicad_pcb'
        self.assertEqual(release.select_pcbs('fabrication', pcb), [pcb])
        self.assertEqual(release.select_pcbs('schematic', None), [release.ROOT/name for name in release.ACTIVE_BOARDS])
        self.assertEqual(release.schematic_for_board(release.DEFAULT_PCB), release.DEFAULT_SCHEMATIC)
        self.assertEqual(release.schematic_for_board(pcb), pcb.with_suffix('.kicad_sch'))

    def test_staging_keeps_each_boards_own_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'fp-lib-table').write_text('${KIPRJMOD}/ducktop2.pretty')
            (root/'sym-lib-table').write_text('${KIPRJMOD}/gen/symbols.kicad_sym')
            (root/'ducktop2.kicad_sch').write_text('center schematic')
            (root/'child.kicad_sch').write_text('center child')
            (root/'ducktop2.kicad_pro').write_text('schematic project, not PCB rules')
            center = root/'ducktop2-center.kicad_pcb'
            center.write_text('center board')
            center.with_suffix('.kicad_pro').write_text('eight-layer layout rules')
            center.with_suffix('.kicad_dru').write_text('center custom rules')
            bms = root/'bms/bms.kicad_pcb'
            bms.parent.mkdir()
            bms.write_text('bms board')
            bms.with_suffix('.kicad_pro').write_text('four-layer layout rules')
            bms.with_suffix('.kicad_sch').write_text('bms schematic')
            (bms.parent/'fp-lib-table').write_text('${KIPRJMOD}/../ducktop2.pretty')
            with patch.object(release, 'ROOT', root):
                c = release.stage_pcb_project(center, root/'ducktop2.kicad_sch', root/'staged-center')
                b = release.stage_pcb_project(bms, bms.with_suffix('.kicad_sch'), root/'staged-bms')
            self.assertEqual(c.name, 'ducktop2.kicad_pcb')
            self.assertEqual(c.with_suffix('.kicad_pro').read_text(), 'eight-layer layout rules')
            self.assertEqual(c.with_suffix('.kicad_dru').read_text(), 'center custom rules')
            self.assertEqual((c.parent/'child.kicad_sch').read_text(), 'center child')
            self.assertEqual(b.with_suffix('.kicad_pro').read_text(), 'four-layer layout rules')
            self.assertEqual((b.parent/'fp-lib-table').read_text(), str((root/'bms').resolve())+'/../ducktop2.pretty')
            self.assertEqual(center.read_text(), 'center board')
            self.assertEqual(bms.read_text(), 'bms board')

    def test_staging_refuses_missing_board_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);pcb = root/'test.kicad_pcb';sch = root/'test.kicad_sch'
            pcb.write_text('board');sch.write_text('schematic')
            with self.assertRaisesRegex(RuntimeError, 'missing board settings'):
                release.stage_pcb_project(pcb, sch, root/'staged')

    def test_new_findings_in_an_existing_category_are_detected(self):
        first = {'type':'clearance', 'severity':'error', 'description':'clearance',
                 'items':[{'description':'pad A'}]}
        other = dict(first, items=[{'description':'pad B'}])
        before = {'violations':[first]};after = {'violations':[other]}
        self.assertEqual(sum(release.refill_additions(before, after, unrouted=False).values()), 1)

    def test_routed_board_does_not_ignore_new_islands(self):
        after = {'violations':[{'type':'isolated_copper','severity':'warning',
                               'description':'island','items':[]}]}
        self.assertEqual(sum(release.refill_additions({}, after, unrouted=False).values()), 1)
        self.assertEqual(sum(release.refill_additions({}, after, unrouted=True).values()), 0)

    def test_rounded_outline_and_circular_cutout(self):
        text = '(kicad_pcb (gr_rect (start 0 0) (end 10 10) (layer "Edge.Cuts")) (gr_circle (center 5 5) (end 6 5) (layer "Edge.Cuts")))'
        loops = release.edge_loops(text)
        self.assertEqual(sum(release.point_in_polygon((5,5), p) for p in loops) % 2, 0)
        self.assertEqual(sum(release.point_in_polygon((2,2), p) for p in loops) % 2, 1)
        arc = '(kicad_pcb (gr_arc (start -10 0) (mid 0 10) (end 10 0) (layer "Edge.Cuts")) (gr_line (start 10 0) (end -10 0) (layer "Edge.Cuts")))'
        polygon = release.edge_loops(arc)[0]
        self.assertTrue(release.point_in_polygon((0,5),polygon))
        self.assertFalse(release.point_in_polygon((0,-5),polygon))

    def test_open_outline_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            release.edge_loops('(kicad_pcb (gr_line (start 0 0) (end 10 0) (layer "Edge.Cuts")))')

    def test_failure_still_checks_for_design_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();pcb=root/'ducktop2-center.kicad_pcb';sch=root/'ducktop2.kicad_sch'
            pcb.write_text('(kicad_pcb)');sch.write_text('schematic')
            def fail_after_write(_):
                pcb.write_text('(kicad_pcb (changed))')
                raise RuntimeError('fixture failure')
            out=io.StringIO()
            with patch.multiple(release, ROOT=root, DEFAULT_PCB=pcb, DEFAULT_SCHEMATIC=sch), \
                 patch.object(release,'project_design_files',return_value=[pcb,sch]), \
                 patch.object(release,'find_kicad_cli',return_value='fixture-cli'), \
                 patch.object(release,'run_static_checks',side_effect=fail_after_write), \
                 patch.object(release,'selection_coverage',return_value={'boards':[]}), redirect_stdout(out):
                result=release.main(['--stage','schematic','--pcb',str(pcb),'--schematic',str(sch)])
            self.assertNotEqual(result,0)
            self.assertIn('Read-only integrity: FAIL',out.getvalue())
            self.assertIn('ducktop2-center.kicad_pcb',out.getvalue())

    def test_reporting_caps_are_identified(self):
        report = {"unconnected_items": [{"type":"unconnected_items"}]*499,
                  "schematic_parity": [{"type":"net_conflict"}]*199}
        self.assertEqual(release.report_limit_hits(report),
                         {"unconnected_items":499, "net_conflict":199})

    def test_counts_below_reporting_caps_are_not_flagged(self):
        report = {"unconnected_items": [{"type":"unconnected_items"}]*498,
                  "violations": [{"type":"clearance"}]*498,
                  "schematic_parity": [{"type":"net_conflict"}]*198}
        self.assertEqual(release.report_limit_hits(report), {})

    def test_bad_uuids_are_reported(self):
        self.assertEqual(release.pcb_uuid_audit('(uuid "broken")'), (1, [], 0))


if __name__ == '__main__':
    unittest.main()
