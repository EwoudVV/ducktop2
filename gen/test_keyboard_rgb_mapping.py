"""Physical row grouping and channel limits for the keyboard LEDs."""
import unittest
from collections import Counter, defaultdict
from keyboard_rgb_contract import ROW_COUNTS, key_assignments, led_nets


class KeyboardRgbMappingTests(unittest.TestCase):
    def test_every_colour_has_its_own_channel(self):
        values=[reg for key in key_assignments().values() for reg in key['registers']]
        self.assertEqual(sorted(values),list(range(1,196)))

    def test_rows_keep_their_own_sink_groups(self):
        assignments=key_assignments(); offset=0
        for row,count in enumerate(ROW_COUNTS):
            slots=Counter(assignments[i]['slot'] for i in range(offset,offset+count))
            self.assertEqual(slots[row],11)
            self.assertEqual(slots[5],count-11)
            self.assertEqual(set(slots)-{row,5},set())
            offset+=count

    def test_each_bank_has_one_key_from_every_row(self):
        assignments=key_assignments(); rows=defaultdict(Counter); offset=0
        for row,count in enumerate(ROW_COUNTS):
            for i in range(offset,offset+count):rows[assignments[i]['bank']][row]+=1
            offset+=count
        self.assertEqual(set(rows),set(range(1,12)))
        for bank,counts in rows.items():
            self.assertEqual(set(counts),set(range(5)))
            self.assertEqual(sum(counts.values()),5 if bank==11 else 6)
            self.assertLessEqual(max(counts.values()),2)

    def test_local_anodes_still_share_one_bank(self):
        for i in range(65):
            nets=led_nets(i)
            self.assertEqual(len({nets[p] for p in ['1','3','5']}),1)
            self.assertEqual(len({nets[p] for p in ['2','4','6']}),3)
            self.assertTrue(nets['4'].startswith('RGB_RED'))


if __name__=='__main__':unittest.main()
