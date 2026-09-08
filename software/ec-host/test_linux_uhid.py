#!/usr/bin/env python3
"""Exercise the loaded kernel bridge with a synthetic EC, never real hardware."""
import fcntl
import json
import os
from pathlib import Path
import struct
import time

DESCRIPTOR=bytes.fromhex('06 00 ff 09 01 a1 01 15 00 26 ff 00 75 08 95 40 09 01 81 02 09 02 b1 02 c0')
def main():
    if not Path('/dev/uhid').exists(): raise SystemExit('load uhid and ducktop2_ec in a disposable Linux guest first')
    fd=os.open('/dev/uhid',os.O_RDWR|os.O_NONBLOCK)
    packet=bytearray(64);packet[:4]=b'DT2\1'
    struct.pack_into('<IHHBBHiII',packet,4,1,199,3,55,2,12000,-900,5500,10000)
    create=struct.pack('<I128s64s64sHHIIII',11,b'Ducktop2 EC synthetic',b'ducktop2-test',b'fixture',len(DESCRIPTOR),3,0x1209,0x2328,0x0100,0)+DESCRIPTOR
    def pump():
        while True:
            try:event=os.read(fd,8192)
            except BlockingIOError:return
            if len(event)<4:return
            kind=struct.unpack_from('<I',event)[0]
            if kind==9:
                ident=struct.unpack_from('<I',event,4)[0]
                os.write(fd,struct.pack('<IIHH',10,ident,0,64)+packet)
            elif kind==13:
                ident=struct.unpack_from('<I',event,4)[0]
                os.write(fd,struct.pack('<IIH',14,ident,0))
    try:
        os.write(fd,create)
        deadline=time.monotonic()+10; battery=None
        while time.monotonic()<deadline:
            pump()
            batteries=list(Path('/sys/class/power_supply').glob('ducktop2-*'))
            if batteries:battery=batteries[0];break
            time.sleep(.02)
        assert battery is not None,'kernel bridge did not bind'
        os.write(fd,struct.pack('<IH',12,64)+packet);time.sleep(.1);pump()
        expected={'present':'1','status':'Discharging','capacity':'55','voltage_now':'12000000',
                  'current_now':'-900000','charge_now':'5500000','charge_full':'10000000'}
        actual={name:(battery/name).read_text().strip() for name in expected}
        assert actual==expected,(actual,expected)
        events=[event for event in Path('/sys/class/input').glob('event*')
                if (event/'device/name').read_text().strip()=='Ducktop2 lid']
        assert len(events)==1,'lid device missing'
        with open('/dev/input/'+events[0].name,'rb',buffering=0) as device:
            switches=bytearray(8);fcntl.ioctl(device,0x8008451b,switches,True)
            assert switches[0]&1,'lid closure not forwarded'
        bad=bytearray(packet);struct.pack_into('<i',bad,16,2147483647);bad[12]=99
        os.write(fd,struct.pack('<IH',12,64)+bad);time.sleep(.1)
        assert (battery/'capacity').read_text().strip()=='55','malformed packet accepted'
        time.sleep(2.2)
        assert (battery/'status').read_text().strip()=='Unknown'
        try:(battery/'capacity').read_text()
        except OSError:pass
        else:raise AssertionError('stale capacity was exposed as valid')
        print(json.dumps({'synthetic_hid':'PASS','battery_units_and_status':'PASS','lid_switch':'PASS',
                          'malformed_packet_rejected':'PASS','stale_telemetry_expires':'PASS',
                          'physical_EC':'not tested'}))
    finally:
        os.write(fd,struct.pack('<I',1));os.close(fd)
if __name__=='__main__':main()
