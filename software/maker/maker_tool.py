#!/usr/bin/env python3
"""One bounded maker UART/I2C/SPI transaction, with explicit user authorization."""
import argparse
import fcntl
import json
import select
import struct
import time

SIZE=64
KINDS={'uart':1,'i2c':2,'spi':3}
def next_sequence(value):return ((value+1)&0xffffffff) or 1
ERRORS=['ok','invalid request','lease unavailable','pin conflict','timeout','I/O error','replayed sequence','busy']
def control(sequence,authorized,rails=False,modes=None):
    modes=[0]*26 if modes is None else modes
    if not 0<sequence<=0xffffffff or len(modes)!=26 or any(not 0<=mode<=4 for mode in modes):
        raise ValueError('invalid control request')
    p=bytearray(64);p[:4]=b'MK2\1';struct.pack_into('<I',p,4,sequence)
    p[8]=bool(rails);p[9]=bool(authorized);p[10:36]=bytes(modes);return p

def transaction(sequence,kind,tx=b'',read=0,rate=None,timeout=100,address=0,mode=0):
    if kind not in KINDS or not 0<sequence<=0xffffffff:raise ValueError('invalid transaction kind or sequence')
    if not 0<=len(tx)<=32 or not 0<=read<=32 or not len(tx)+read or not 1<=timeout<=100:
        raise ValueError('transactions need 1..32 bytes per direction and a 1..100 ms timeout')
    if rate is None:rate={'uart':115200,'i2c':100000,'spi':1000000}[kind]
    if kind=='uart' and (not 300<=rate<=115200 or address or mode):raise ValueError('UART is 8N1, 300..115200 baud')
    if kind=='i2c' and (not 10000<=rate<=100000 or not 8<=address<=0x77 or mode):raise ValueError('invalid I2C address or clock')
    if kind=='spi' and (not 10000<=rate<=1000000 or address or not 0<=mode<=3 or (tx and read and len(tx)!=read)):
        raise ValueError('SPI read/write lengths must match; clock is 10 kHz..1 MHz')
    p=bytearray(64);p[:4]=b'MB2\1';struct.pack_into('<I',p,4,sequence)
    p[8:12]=bytes([KINDS[kind],mode,len(tx),read]);struct.pack_into('<IH',p,12,rate,timeout)
    p[18]=address;p[32:32+len(tx)]=tx;return p

def result(packet,sequence):
    if len(packet)!=64 or packet[:4]!=b'MR2\1' or struct.unpack_from('<I',packet,4)[0]!=sequence:
        raise ValueError('unexpected maker response')
    if packet[8]>=len(ERRORS) or packet[10]>32:raise ValueError('malformed maker response')
    return {'sequence':sequence,'status':ERRORS[packet[8]],'received':packet[32:32+packet[10]].hex(),
            'actual_rate':struct.unpack_from('<I',packet,12)[0], 'elapsed_ms':struct.unpack_from('<H',packet,16)[0]}

def send(device,packet):
    fcntl.ioctl(device,0xC0000000 | (65<<16) | (ord('H')<<8) | 0x06,b'\0'+packet)
def receive(device,predicate,timeout=1):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if not select.select([device],[],[],max(0,deadline-time.monotonic()))[0]:break
        packet=device.read(64)
        if len(packet)==64 and predicate(packet):return packet
    raise TimeoutError('maker did not return the expected report; no transaction was retried')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hidraw',required=True);p.add_argument('--authorize',action='store_true')
    p.add_argument('--rails',action='store_true');p.add_argument('--settle-ms',type=int,default=100)
    p.add_argument('kind',choices=KINDS);p.add_argument('--tx',default='');p.add_argument('--read',type=int,default=0)
    p.add_argument('--rate',type=int);p.add_argument('--timeout-ms',type=int,default=100)
    p.add_argument('--address',type=lambda value:int(value,0),default=0);p.add_argument('--mode',type=int,default=0)
    a=p.parse_args()
    if not a.authorize:raise SystemExit('--authorize is required before driving the maker header')
    if not 0<=a.settle_ms<=500:raise SystemExit('settle time must be 0..500 ms')
    # Validate every field before opening hardware or applying rail power.
    transaction(1,a.kind,bytes.fromhex(a.tx),a.read,a.rate,a.timeout_ms,a.address,a.mode)
    with open(a.hidraw,'r+b',buffering=0) as device:
        state=receive(device,lambda report:report[:4]==b'MK2\1' and report[47]==1)
        sequence=next_sequence(struct.unpack_from('<I',state,4)[0])
        bus_sequence=next_sequence(struct.unpack_from('<I',state,48)[0])
        try:
            # Deliberate all-off request clears a removed fault before authorization.
            send(device,control(sequence,False));sequence=next_sequence(sequence)
            send(device,control(sequence,True,a.rails))
            receive(device,lambda report:report[:4]==b'MK2\1' and struct.unpack_from('<I',report,4)[0]==sequence and report[10]==1)
            time.sleep(a.settle_ms/1000)
            sequence=next_sequence(sequence);send(device,control(sequence,True,a.rails))
            send(device,transaction(bus_sequence,a.kind,bytes.fromhex(a.tx),a.read,a.rate,a.timeout_ms,a.address,a.mode))
            response=receive(device,lambda report:report[:4]==b'MR2\1' and struct.unpack_from('<I',report,4)[0]==bus_sequence)
            outcome=result(response,bus_sequence);print(json.dumps(outcome))
            if outcome['status']!='ok':raise SystemExit(1)
        finally:
            send(device,control(next_sequence(sequence),False))
if __name__=='__main__':main()
