import struct
import unittest
from maker_tool import control,transaction,result
class ProtocolTests(unittest.TestCase):
    def test_literal_wire(self):
        p=transaction(7,'i2c',b'\x10\x20',2,100000,80,0x55)
        self.assertEqual(p[:12],b'MB2\1\x07\0\0\0\x02\0\x02\x02')
        self.assertEqual(p[12:19],b'\xa0\x86\x01\0\x50\0\x55')
        self.assertEqual(p[32:34],b'\x10\x20')
        self.assertEqual(len(p),64)
        self.assertEqual(control(1,False)[8:36],bytes(28))
    def test_invalid_requests(self):
        cases=[dict(kind='i2c',address=0,tx=b'a'),dict(kind='uart',tx=bytes(33)),
               dict(kind='spi',tx=b'ab',read=1),dict(kind='spi',read=1,timeout=101),dict(kind='uart',read=1,rate=1)]
        for args in cases:
            with self.assertRaises(ValueError):transaction(1,**args)
    def test_response_errors_and_partial_data(self):
        p=bytearray(64);p[:4]=b'MR2\1';struct.pack_into('<I',p,4,8);p[8]=4;p[10]=1;p[32]=0xaa
        self.assertEqual(result(p,8)['status'],'timeout');self.assertEqual(result(p,8)['received'],'aa')
        with self.assertRaises(ValueError):result(p,9)
if __name__=='__main__':unittest.main()
