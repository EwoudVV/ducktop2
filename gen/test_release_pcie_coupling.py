"""The release gate must bind a complete coupling proof to its selected board."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import check_release_candidate as release


CHECKER_FIXTURE = '''import argparse, hashlib, json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--pcb', type=Path)
p.add_argument('--limits', type=Path)
p.add_argument('--output', type=Path)
a = p.parse_args()
mode = MODE
if mode == 'no_output':
    raise SystemExit(0)
if mode == 'dependency_error':
    raise ModuleNotFoundError('numpy')
if mode == 'bad_json':
    a.output.write_text('not json')
    raise SystemExit(0)
limits = json.loads(a.limits.read_text())
scopes = limits['suites']
bad_board = 'BAD' in a.pcb.read_text()
result = {
    'status': 'failed' if bad_board else 'passed',
    'candidate_sha256': hashlib.sha256(a.pcb.read_bytes()).hexdigest(),
    'limits_sha256': hashlib.sha256(a.limits.read_bytes()).hexdigest(),
    'exact_pcb_path': str(a.pcb.resolve()),
    'suites': [dict(scope=s['scope'], status='passed', blocking_findings=[]) for s in scopes],
}
if limits.get('signal_paths') and mode != 'missing_paths':
    result['suites'].append(dict(scope='complete PCIe signal paths', status='passed', blocking_findings=[]))
if mode == 'wrong_board':
    result['candidate_sha256'] = '0' * 64
elif mode == 'wrong_limits':
    result['limits_sha256'] = '0' * 64
elif mode == 'wrong_path':
    result['exact_pcb_path'] = str(a.pcb.parent / 'canonical.kicad_pcb')
elif mode == 'empty_suites':
    result['suites'] = []
elif mode == 'partial_suites':
    result['suites'] = result['suites'][:1]
elif mode == 'failed_suite':
    result['suites'][0]['status'] = 'failed'
elif mode == 'hidden_finding':
    result['suites'][0]['blocking_findings'] = [{'kind': 'minimum_gap'}]
elif mode == 'missing_findings':
    del result['suites'][0]['blocking_findings']
elif mode == 'mutate_board':
    a.pcb.write_text(a.pcb.read_text() + 'changed')
a.output.write_text(json.dumps(result))
raise SystemExit(1 if bad_board else 0)
'''


class ReleasePcieCoupling(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(release, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.pcb = self.root / 'candidate/selected.kicad_pcb'
        self.staged = self.root / 'staged/selected.kicad_pcb'
        self.reports = self.root / 'reports'
        for path in (self.pcb, self.staged):
            path.parent.mkdir()
            path.write_text('(kicad_pcb (zone (name "nvme connector fanout")))')
        self.canonical = self.root / 'ducktop2-center.kicad_pcb'
        self.canonical.write_text('(kicad_pcb)')
        self.checker = self.root / 'gen/check_center_pcie_coupling.py'
        self.checker.parent.mkdir()
        self.limits = self.root / 'manufacturing/center_pcie_layout_limits.json'
        self.limits.parent.mkdir()
        self.limits.write_text(json.dumps({'schema_version': 1,
                                          'suites': [{'scope': 'data'}, {'scope': 'clock'}]}))
        self.checker_mode('pass')

    def checker_mode(self, mode):
        self.checker.write_text(CHECKER_FIXTURE.replace('MODE', repr(mode)))

    def run_gate(self, stage='routing'):
        with redirect_stdout(io.StringIO()):
            return release.run_center_pcie_coupling(self.pcb, self.staged, self.reports, stage)

    def test_complete_proof_uses_the_selected_staged_board(self):
        self.assertEqual(self.run_gate(), 0)
        proof = json.loads((self.reports / 'center-pcie-coupling.json').read_text())
        execution = json.loads((self.reports / 'center-pcie-coupling-execution.json').read_text())
        self.assertEqual(proof['candidate_sha256'], release.sha256(self.pcb))
        self.assertNotEqual(proof['candidate_sha256'], release.sha256(self.canonical))
        self.assertEqual(execution['checked_pcb'], str(self.staged.resolve()))
        self.assertEqual(execution['suites_checked'], 2)
        self.assertEqual(self.pcb.read_bytes(), self.staged.read_bytes())

    def test_bad_explicit_candidate_cannot_pass_using_good_canonical_board(self):
        self.pcb.write_text(self.pcb.read_text() + ' BAD')
        self.staged.write_bytes(self.pcb.read_bytes())
        self.assertEqual(self.run_gate(), 1)
        proof = json.loads((self.reports / 'center-pcie-coupling.json').read_text())
        self.assertEqual(proof['candidate_sha256'], release.sha256(self.pcb))
        self.assertEqual(proof['status'], 'failed')
        self.assertEqual(self.canonical.read_text(), '(kicad_pcb)')

    def test_wrong_staged_copy_is_rejected_before_running_checker(self):
        self.staged.write_bytes(self.canonical.read_bytes())
        self.assertEqual(self.run_gate(), 1)
        self.assertFalse((self.reports / 'center-pcie-coupling.json').exists())

    def test_stale_passing_report_is_removed_before_running_checker(self):
        self.assertEqual(self.run_gate(), 0)
        self.checker_mode('no_output')
        self.assertEqual(self.run_gate(), 1)
        self.assertFalse((self.reports / 'center-pcie-coupling.json').exists())

    def test_zero_exit_does_not_excuse_invalid_or_incomplete_proof(self):
        for mode in ('bad_json', 'wrong_board', 'wrong_limits', 'wrong_path', 'empty_suites',
                     'partial_suites', 'failed_suite', 'hidden_finding', 'missing_findings'):
            with self.subTest(mode=mode):
                self.checker_mode(mode)
                self.assertEqual(self.run_gate(), 1)

    def test_missing_checker_limits_or_dependency_blocks_the_gate(self):
        self.checker.unlink()
        self.assertEqual(self.run_gate(), 1)
        self.checker_mode('dependency_error')
        self.assertEqual(self.run_gate(), 1)
        self.checker_mode('pass')
        self.limits.unlink()
        self.assertEqual(self.run_gate(), 1)

    def test_checker_must_leave_the_staged_board_unchanged(self):
        self.checker_mode('mutate_board')
        self.assertEqual(self.run_gate(), 1)
        self.assertNotEqual(self.pcb.read_bytes(), self.staged.read_bytes())

    def test_configured_signal_paths_require_their_own_complete_result(self):
        limits = json.loads(self.limits.read_text())
        limits['signal_paths'] = [{'name': 'NVMe RX0'}]
        self.limits.write_text(json.dumps(limits))
        self.assertEqual(self.run_gate(), 0)
        self.checker_mode('missing_paths')
        self.assertEqual(self.run_gate(), 1)

    def test_center_contract_requires_a_check_without_area_markers(self):
        self.pcb = self.canonical
        self.staged.write_bytes(self.pcb.read_bytes())
        self.checker.unlink()
        for stage in ('routing', 'fabrication', 'production'):
            with self.subTest(stage=stage):
                self.assertEqual(self.run_gate(stage), 1)

    def test_rules_alone_require_a_check_on_explicit_candidates(self):
        self.pcb.write_text('(kicad_pcb)')
        self.staged.write_bytes(self.pcb.read_bytes())
        self.checker.unlink()
        for prefix in ('nvme ', 'wifi pcie ', 'center pcie '):
            with self.subTest(prefix=prefix):
                self.pcb.with_suffix('.kicad_dru').write_text(
                    '(version 1)\n(rule "' + prefix + 'connector gap")')
                self.assertEqual(self.run_gate(), 1)

    def test_unrelated_board_and_schematic_stage_do_not_require_dependencies(self):
        self.checker.unlink()
        self.limits.unlink()
        self.assertEqual(self.run_gate('schematic'), 0)
        self.pcb.write_text('(kicad_pcb)')
        self.staged.write_bytes(self.pcb.read_bytes())
        self.assertEqual(self.run_gate(), 0)

    def test_physical_release_gate_counts_coupling_failure(self):
        self.staged.with_suffix('.kicad_pro').write_text(
            json.dumps({'board': {'design_settings': {}}}))
        schematic = self.pcb.with_suffix('.kicad_sch')
        schematic.write_text('schematic')
        def drc(command, cwd, label):
            output = Path(command[command.index('--output') + 1])
            output.write_text(json.dumps({'violations': [], 'schematic_parity': [],
                                          'unconnected_items': []}))
            return 'Found 0 schematic parity issues\n'
        with patch.object(release, 'stage_pcb_project', return_value=self.staged), \
             patch.object(release, 'run_center_pcie_coupling', return_value=1) as coupling, \
             patch.object(release, 'run_command', side_effect=drc), \
             patch.object(release, 'native_board_stats', return_value={'native_airwires': 0, 'copper_layers': 8}), \
             patch.object(release, 'offboard_footprint_anchors', return_value=[]), \
             redirect_stdout(io.StringIO()):
            result = release.run_pcb_checks('fixture-cli', self.pcb, self.root,
                                           schematic, self.reports, stage='routing')
        self.assertEqual(result, 1)
        coupling.assert_called_once_with(self.pcb, self.staged, self.reports, 'routing')


if __name__ == '__main__':
    unittest.main()
