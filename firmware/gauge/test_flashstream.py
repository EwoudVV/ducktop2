import unittest
from flashstream import parse, execute
class Bus:
    def __init__(self):self.data=b'';self.writes=0
    def write(self,address,reg,data):self.data=data;self.writes+=1
    def read(self,address,reg,length):return self.data
class FlashTests(unittest.TestCase):
    def test_literal_ti_address(self):
        steps=parse('; comment\nW: AA 3E 02 00\nX: 10\nC: AA 3E 02 00')
        self.assertEqual(steps[0][1],0x55)
        bus=Bus();execute(steps,bus,lambda _:None);self.assertEqual(bus.writes,1)
    def test_fail_stops_following_write(self):
        steps=parse('W: AA 40 01\nC: AA 40 02\nW: AA 40 03')
        bus=Bus()
        with self.assertRaises(ValueError):execute(steps,bus)
        self.assertEqual(bus.writes,1)
    def test_malformed(self):
        for text in ('W: AA 01 02','C: 55 01 02','C: AA 01 GG','X: -1\nC: AA 01 00'):
            with self.assertRaises(ValueError):parse(text)
if __name__=='__main__':unittest.main()
