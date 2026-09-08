#!/usr/bin/env python3
"""Build the maker target from pinned SDK commits and retain artifact hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def run(args):return subprocess.check_output(list(map(str,args)),text=True).strip()
def uf2(binary):
    if not binary or len(binary)>4*1024*1024:raise ValueError('invalid maker flash image size')
    count=(len(binary)+255)//256;blocks=[]
    for index in range(count):
        part=binary[index*256:(index+1)*256].ljust(256,b'\0')
        header=struct.pack('<8I',0x0a324655,0x9e5d5157,0x2000,0x10000000+index*256,256,index,count,0xe48bff59)
        blocks.append(header+part+bytes(220)+struct.pack('<I',0x0ab16f30))
    result=b''.join(blocks)
    reconstructed=b''.join(result[i+32:i+288] for i in range(0,len(result),512))[:len(binary)]
    if reconstructed!=binary:raise ValueError('UF2 payload does not match the binary')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True)
    p.add_argument('--toolchain',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();dep=json.loads((ROOT/'maker_target/dependencies.json').read_text())
    for folder,expected in ((a.sdk,dep['pico_sdk']['commit']),
                            (a.sdk/'lib/tinyusb',dep['tinyusb']['commit'])):
        if run(['git','-C',folder,'rev-parse','HEAD'])!=expected:raise ValueError('SDK dependency commit mismatch')
        if run(['git','-C',folder,'diff','--name-only']):raise ValueError('modified SDK dependency')
    compiler=a.toolchain/'bin/arm-none-eabi-gcc'
    version=run([compiler,'--version']).splitlines()[0]
    if '13.3.Rel1' not in version:raise ValueError('this record requires Arm GNU 13.3.Rel1')
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
    subprocess.run(['cmake','-S',str(ROOT/'maker_target'),'-B',str(output),
                    '-DPICO_SDK_PATH='+str(a.sdk.resolve()),'-DPICO_TOOLCHAIN_PATH='+str(a.toolchain.resolve()),
                    '-DCMAKE_BUILD_TYPE=Release'],check=True)
    subprocess.run(['cmake','--build',str(output),'--parallel','4'],check=True)
    binary=output/'ducktop2_maker.bin';(output/'ducktop2_maker.uf2').write_bytes(uf2(binary.read_bytes()))
    artifacts={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
               for name in ('ducktop2_maker.elf','ducktop2_maker.bin','ducktop2_maker.uf2')}
    record={'toolchain':version,'dependencies':dep,'artifacts':artifacts,
            'uf2_family':'0xe48bff59 RP2350 ARM secure','uf2_payload':'matches binary',
            'hardware_execution':'not performed'}
    (output/'build-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
if __name__=='__main__':main()
