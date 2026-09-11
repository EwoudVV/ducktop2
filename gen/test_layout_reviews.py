"""Reviewed advisories must not hide changed geometry or unfinished fabrication."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import verify_layout_reviews as review

FP_ID = '11111111-1111-4111-8111-111111111111'
VIA_ID = '22222222-2222-4222-8222-222222222222'
FP = f'''(footprint "demo:part"
 (layer "F.Cu") (uuid "{FP_ID}") (at 10 20)
 (property "Reference" "R1") (property "Value" "10k")
 (pad "1" smd rect (at 0 0) (size 1 2) (layers "F.Cu" "F.Mask")))'''
VIA = f'''(via (at 4 5) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu")
 (net "CONTROL") (uuid "{VIA_ID}"))'''


class LayoutReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'verification').mkdir()
        (self.root / 'demo.pretty').mkdir()
        self.library = self.root / 'demo.pretty/part.kicad_mod'
        self.library.write_text('(footprint "part")')
        self.pcb = self.root / 'board.kicad_pcb'
        self.pcb.write_text('(kicad_pcb\n' + FP + '\n' + VIA + '\n)')
        self.violation = {'type': 'lib_footprint_mismatch', 'severity': 'warning',
                          'description': 'reviewed marking differs',
                          'items': [{'uuid': FP_ID, 'description': 'Footprint R1'}]}
        self.record = {'board': 'center', 'section': 'drc', 'kind': 'footprint',
                       'type': self.violation['type'], 'severity': 'warning',
                       'description': self.violation['description'], 'item_uuid': FP_ID,
                       'reference': 'R1', 'footprint_id': 'demo:part',
                       'item_sha256': review.fingerprint(FP),
                       'library_sha256': hashlib.sha256(self.library.read_bytes()).hexdigest()}

    def tearDown(self):
        self.temp.cleanup()

    def check(self, *, stage='routing', complete=False, board='center'):
        (self.root / 'verification/layout-reviews.json').write_text(
            json.dumps({'version': 1, 'reviews': [self.record]}))
        return review.reviewed_violations(board, self.pcb, 'drc', [self.violation], root=self.root,
                                          stage=stage, routing_complete_required=complete)['accepted']

    def test_exact_review_is_accepted(self):
        self.assertEqual(self.check(), [self.violation])

    def test_pad_geometry_change_revokes_review(self):
        self.pcb.write_text(self.pcb.read_text().replace('(size 1 2)', '(size 1.1 2)'))
        self.assertEqual(self.check(), [])

    def test_library_change_revokes_review(self):
        self.library.write_text('(footprint "part" (pad "2" smd rect))')
        self.assertEqual(self.check(), [])

    def test_error_severity_cannot_use_warning_review(self):
        self.violation['severity'] = 'error'
        self.assertEqual(self.check(), [])

    def test_clearance_cannot_be_waived_even_by_a_matching_record(self):
        self.record['type'] = self.violation['type'] = 'clearance'
        self.assertEqual(self.check(), [])

    def test_other_board_cannot_reuse_review(self):
        self.assertEqual(self.check(board='right_io'), [])

    def test_duplicate_object_identity_is_rejected(self):
        self.pcb.write_text('(kicad_pcb\n' + FP + '\n' + FP + '\n)')
        self.assertEqual(self.check(), [])

    def test_numeric_serialization_does_not_change_fingerprint(self):
        self.assertEqual(review.fingerprint(FP), review.fingerprint(FP.replace('(at 10 20)', '(at 10.0 20.000)')))

    def test_unfinished_via_only_passes_routing_preparation(self):
        self.violation = {'type': 'via_dangling', 'severity': 'warning', 'description': 'unfinished control via',
                          'items': [{'uuid': VIA_ID, 'description': 'Via on CONTROL'}]}
        self.record = {'board': 'center', 'section': 'drc', 'kind': 'via', 'stage': 'routing',
                       'type': 'via_dangling', 'severity': 'warning', 'description': 'unfinished control via',
                       'item_uuid': VIA_ID, 'item_description': 'Via on CONTROL',
                       'item_sha256': review.fingerprint(VIA)}
        self.assertEqual(self.check(), [self.violation])
        self.assertEqual(self.check(stage='fabrication'), [])
        self.assertEqual(self.check(complete=True), [])
        self.pcb.write_text(self.pcb.read_text().replace('(drill 0.3)', '(drill 0.4)'))
        self.assertEqual(self.check(), [])

    def test_existing_open_track_cannot_pass_fabrication_or_complete_board_gate(self):
        track = f'''(segment (start 1 2) (end 4 2) (width 0.15)
        (layer "F.Cu") (net "CONTROL") (uuid "{VIA_ID}"))'''
        self.pcb.write_text('(kicad_pcb\n' + FP + '\n' + track + '\n)')
        self.violation = {'type': 'track_dangling', 'severity': 'warning', 'description': 'open route end',
                          'items': [{'uuid': VIA_ID, 'description': 'Track on CONTROL'}]}
        self.record = {'board': 'center', 'section': 'drc', 'kind': 'track', 'stage': 'routing',
                       'type': 'track_dangling', 'severity': 'warning', 'description': 'open route end',
                       'item_uuid': VIA_ID, 'item_description': 'Track on CONTROL',
                       'item_sha256': review.fingerprint(track)}
        self.assertEqual(self.check(), [self.violation])
        self.assertEqual(self.check(stage='fabrication'), [])
        self.assertEqual(self.check(complete=True), [])
        self.record['kind'] = 'via'
        self.assertEqual(self.check(), [])
        self.record['kind'] = 'track'
        self.pcb.write_text(self.pcb.read_text().replace('(end 4 2)', '(end 5 2)'))
        self.assertEqual(self.check(), [])


if __name__ == '__main__':
    unittest.main()
