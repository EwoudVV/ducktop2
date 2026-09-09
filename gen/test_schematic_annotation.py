from pathlib import Path
import tempfile
import unittest
from check_schematic_annotation import check_annotation


def symbol(reference,unit=1):
    return f'(symbol\n(unit {unit})\n(property "Reference" "{reference}"))'


class AnnotationTests(unittest.TestCase):
    def project(self,first,second):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name)
        (root/'root.kicad_sch').write_text('(kicad_sch '+first+' (sheet\n(property "Sheetfile" "child.kicad_sch")))')
        (root/'child.kicad_sch').write_text('(kicad_sch '+second+')')
        return root/'root.kicad_sch'

    def test_duplicate_power_references_are_checked_across_sheets(self):
        issues=check_annotation(self.project(symbol('#PWR001'),symbol('#PWR001')))
        self.assertEqual(len(issues),1)
        self.assertIn('duplicate #PWR1',issues[0])

    def test_reference_suffix_must_include_a_number(self):
        self.assertIn('invalid reference U15B',check_annotation(self.project(symbol('U15B'),symbol('U16')))[0])

    def test_distinct_units_and_power_ranges_remain_valid(self):
        self.assertEqual(check_annotation(self.project(symbol('U170',1)+symbol('#PWR001'),symbol('U170',2)+symbol('#PWR3301'))),[])

    def test_leading_zeroes_do_not_hide_duplicate_numbers(self):
        self.assertIn('duplicate R1',check_annotation(self.project(symbol('R01'),symbol('R1')))[0])


if __name__=='__main__':unittest.main()
