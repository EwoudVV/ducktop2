import re
import unittest

import heal_footprint_uuids as heal
import sync_main_pcb_from_netlist as sync

FIRST = '11111111-1111-4111-8111-111111111111'
SECOND = '22222222-2222-4222-8222-222222222222'
CHILD = '33333333-3333-4333-8333-333333333333'
OTHER = '44444444-4444-4444-8444-444444444444'


def footprint(ref, own, child):
    return f'''(footprint "example:pad" (uuid "{own}") (at 12 34 90)
    (property "Reference" "{ref}")
    (pad "1" smd rect (at 0 0) (size 1 2) (layers "F.Cu")
         (net "GND") (uuid "{child}")))'''


class FootprintIds(unittest.TestCase):
    def test_copied_library_children_and_local_links_are_distinct(self):
        raw = footprint('REF**',FIRST,CHILD)[:-1] + f'(group "local" (uuid "{OTHER}") (members "{CHILD}")))'
        a = sync.scope_library_uuids(raw,'J1')
        b = sync.scope_library_uuids(raw,'J2')
        self.assertFalse(set(heal.UUID_RE.findall(a)) & set(heal.UUID_RE.findall(b)))
        for text in (a,b):
            target = re.search(r'\(members "([^"]+)"',text).group(1)
            self.assertIn(target,heal.UUID_RE.findall(text))
        self.assertEqual(a,sync.scope_library_uuids(raw,'J1'))

    def test_bad_library_with_duplicate_objects_is_rejected(self):
        with self.assertRaises(ValueError):
            sync.scope_library_uuids(footprint('REF**',CHILD,CHILD),'J1')

    def test_repair_changes_only_excess_ids(self):
        first = footprint('J1',FIRST,CHILD)
        text = '(kicad_pcb ' + first + footprint('J2',SECOND,CHILD) + ')'
        fixed,changes = heal.repair_duplicate_ids(text)
        self.assertEqual(len(changes),1)
        self.assertIn(first,fixed)
        self.assertEqual(changes[0]['reference'],'J2')
        self.assertEqual(text.replace(CHILD,OTHER),fixed.replace(CHILD,OTHER).replace(changes[0]['new_uuid'],OTHER))
        self.assertEqual((fixed,[]),heal.repair_duplicate_ids(fixed))

    def test_unique_ids_and_geometry_are_untouched(self):
        text = '(kicad_pcb ' + footprint('J1',FIRST,CHILD) + footprint('J2',SECOND,OTHER) + ')'
        self.assertEqual((text,[]),heal.repair_duplicate_ids(text))

    def test_duplicate_footprint_identity_is_rejected(self):
        text = '(kicad_pcb ' + footprint('J1',FIRST,CHILD) + footprint('J2',FIRST,OTHER) + ')'
        with self.assertRaises(ValueError):heal.repair_duplicate_ids(text)

    def test_duplicate_within_one_footprint_is_rejected(self):
        text = '(kicad_pcb ' + footprint('J1',FIRST,CHILD)[:-1] + f'(fp_text user "x" (uuid "{CHILD}"))))'
        with self.assertRaises(ValueError):heal.repair_duplicate_ids(text)

    def test_ambiguous_board_group_is_rejected(self):
        text = '(kicad_pcb ' + footprint('J1',FIRST,CHILD) + footprint('J2',SECOND,CHILD) + f'(group "x" (members "{CHILD}")))'
        with self.assertRaises(ValueError):heal.repair_duplicate_ids(text)


if __name__ == '__main__':
    unittest.main()
