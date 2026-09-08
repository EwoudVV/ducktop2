#!/usr/bin/env python3
"""TI SLUA801 FlashStream parser and bounded Linux fixture executor."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

def parse(text, addresses=(0x55, 0x0b)):
    steps=[]
    for number,line in enumerate(text.splitlines(),1):
        line=line.partition(';')[0].strip()
        if not line: continue
        match=re.fullmatch(r'([WCX]):\s*(.*)',line)
        if not match: raise ValueError(f'line {number}: unsupported command')
        kind,body=match.groups()
        if kind=='X':
            if not body.isdecimal() or not 0<=int(body)<=60000:
                raise ValueError(f'line {number}: invalid delay')
            steps.append((kind,int(body))); continue
        tokens=body.split()
        if not 3<=len(tokens)<=34 or any(not re.fullmatch('[0-9a-fA-F]{2}',x) for x in tokens):
            raise ValueError(f'line {number}: malformed bytes or more than 32 payload bytes')
        data=bytes.fromhex(body); address=data[0]>>1
        if data[0]&1 or address not in addresses:
            raise ValueError(f'line {number}: unsupported device address')
        steps.append((kind,address,data[1],data[2:]))
    if not steps or not any(step[0]=='C' for step in steps):
        raise ValueError('image contains no compare operation')
    return steps

class Bus:
    def __init__(self, number): self.number=number
    def command(self,*parts):
        completed=subprocess.run(['i2ctransfer','-y',str(self.number),*parts],
                                 check=True,capture_output=True,text=True,timeout=2)
        time.sleep(0.001)
        return completed.stdout
    def write(self,address,reg,data):
        self.command(f'w{len(data)+1}@0x{address:02x}',f'0x{reg:02x}',*[f'0x{x:02x}' for x in data])
    def read(self,address,reg,length):
        answer=self.command(f'w1@0x{address:02x}',f'0x{reg:02x}',f'r{length}')
        tokens=answer.split()
        if len(tokens)!=length or any(not re.fullmatch(r'0x[0-9a-fA-F]{2}',x) for x in tokens):
            raise ValueError('malformed I2C readback')
        return bytes(int(x,16) for x in tokens)

def execute(steps,bus,sleep=time.sleep):
    for index,step in enumerate(steps):
        if step[0]=='X': sleep(step[1]/1000); continue
        kind,address,reg,data=step
        if kind=='W': bus.write(address,reg,data)
        elif bus.read(address,reg,len(data))!=data:
            raise ValueError(f'compare failed at operation {index+1}; stopped without retry')

def main():
    p=argparse.ArgumentParser();p.add_argument('image',type=Path)
    p.add_argument('--profile',type=Path,required=True);p.add_argument('--bus',type=int)
    p.add_argument('--apply',action='store_true');p.add_argument('--pack-substitute',action='store_true')
    p.add_argument('--report',type=Path)
    a=p.parse_args();image=a.image.read_bytes();profile=json.loads(a.profile.read_text())
    digest=hashlib.sha256(image).hexdigest();steps=parse(image.decode('ascii'))
    if digest!=profile.get('image_sha256'): raise SystemExit('image hash does not match the reviewed profile')
    if not a.apply:
        print(json.dumps({'parser':'passed','operations':len(steps),'sha256':digest,'hardware':'not accessed'}));return
    if not a.pack_substitute or a.bus is None or a.bus<0 or not a.report:
        raise SystemExit('apply requires --bus, --pack-substitute and --report')
    if profile.get('status')!='QUALIFIED_IMAGE' or not profile.get('evidence'):
        raise SystemExit('image is not qualified for this exact gauge/pack configuration')
    bus=Bus(a.bus)
    bus.write(0x55,0,b'\x01\x00')
    if bus.read(0x55,0,2)!=b'\x00\x01': raise SystemExit('unexpected gauge device type')
    execute(steps,bus)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps({'image_programming':'passed','image_sha256':digest,
                                  'calibration':'not performed','real_cell_validation':'not performed'},indent=2)+'\n')
if __name__=='__main__':main()
