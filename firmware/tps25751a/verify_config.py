#!/usr/bin/env python3
"""Check each port's exact TI source, images and separately reviewed VIF."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'release_manifest.json'
GENERATED=ROOT/'generated'
NS='http://usb.org/VendorInfoFile.xsd'
# Complete records actually present in both official FB09.17.02 exports.
BINARY_REGISTERS=(0x16,0x27,0x28,0x29,0x32,0x33,0x37,0x42,0x5c,0x70,0x77,0x78,0x7e)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool,message: str,errors: list[str]) -> None:
    if not condition:errors.append(message)


def register_map(document: dict) -> dict[int,list[int]]:
    entries=document['configuration']['data']['selected_ace']
    result={entry['register']:entry['data'] for entry in entries}
    if len(result)!=len(entries):raise ValueError('duplicate register in TI source')
    if any(not data or len(data)>64 or any(type(b) is not int or not 0<=b<=255 for b in data)
           for data in result.values()):raise ValueError('invalid register bytes')
    return result


def verify_policy(document: dict,label: str,errors: list[str],port: str='PD1') -> None:
    answers=document['questionnaire']['answers'];regs=register_map(document)
    speed=2 if port=='PD1' else 0
    require(port in ('PD1','PD2'),f'{label}: unknown physical port',errors)
    require(answers[1]==1 and answers[3]==3 and answers[6]==1,
            f'{label}: expected DRP/no-BQ, 60 W sink and host-only questionnaire',errors)
    require(answers[5]==(3 if port=='PD1' else 1),f'{label}: data-speed questionnaire differs from physical port',errors)
    require(regs.get(0x27)==[1,129,2,0,28,3,0,0,0,0,0,0,0,0,0],
            f'{label}: VCONN limit or PP1-source/PP3-sink global configuration drifted',errors)
    expected_cfg=[2,0x48 if speed==2 else 8,46,1,0,0,0,0,0,0,0,0,112,252,255,3,1,0]
    require(regs.get(0x28)==expected_cfg,f'{label}: physical port speed, DRP or port configuration drifted',errors)
    require(regs.get(0x29)==[112,193,129,0,0],
            f'{label}: host-only swaps, default Rp or disabled BC1.2 drifted',errors)
    source=regs.get(0x32,[])
    # The first three bytes are the register header, not a PDO. Only one slot
    # is active. The PDO's dual-role-data flag must stay clear for this host.
    require(len(source)==63 and source[:7]==[1,168,42,0x5a,0x90,1,4],
            f'{label}: source must be one PP5V fixed 5 V / 900 mA PDO without dual-role-data',errors)
    sink=regs.get(0x33,[]);decoded=[]
    if len(sink)==53 and (sink[0]&7)==4:
        for index in range(4):
            word=int.from_bytes(bytes(sink[1+4*index:5+4*index]),'little')
            decoded.append(((word>>30)&3,((word>>10)&0x3ff)*50,(word&0x3ff)*10))
    require(decoded==[(0,5000,3000),(0,9000,3000),(0,15000,3000),(0,20000,3000)]
            and not any(sink[17:]),f'{label}: four fixed 3 A sink PDOs and no inactive 5 A slot required',errors)
    require(regs.get(0x7e,[None]*11)[8:11]==[45,45,60],
            f'{label}: minimum/operational/maximum sink PDP must be 45/45/60 W',errors)
    io=regs.get(0x5c,[])
    require(len(io)>43 and (io[0],io[32],io[40],io[42],io[43])==(219,16,29,3,61),
            f'{label}: GPIO enable/inversion/DFP/orientation/data-mux events drifted',errors)
    require(regs.get(0x77,[None]*14)[13]==5 and regs.get(0x78,[None]*3)[2]==5,
            f'{label}: encoded 5 W source information drifted',errors)


def xml_value(root: ET.Element,tag: str) -> ET.Element | None:
    return root.find(f'.//{{{NS}}}{tag}')


def verify_vif(path: Path,errors: list[str],port: str='PD1',reviewed: bool=True) -> None:
    root=ET.parse(path).getroot();label=f'{port} {path.name}'
    expected={'PD_Port_Type':'4','RP_Value':'0','Type_C_Can_Act_As_Host':'true',
        'Type_C_Can_Act_As_Device':'false','Host_Supports_USB_Data':'true','Device_Supports_USB_Data':'false',
        'Data_Capable_As_USB_Host_SOP':'true','Data_Capable_As_USB_Device_SOP':'false',
        'DR_Swap_To_DFP_Supported':'true','DR_Swap_To_UFP_Supported':'false',
        'USB4_Supported':'false','Type_C_Is_Alt_Mode_Controller':'false',
        'Type_C_Is_Alt_Mode_Adapter':'false','Modal_Operation_Supported_SOP':'false',
        'Num_SVIDs_Min_SOP':'0','Num_SVIDs_Max_SOP':'0','PD_Power_As_Source':'4500',
        'Num_Src_PDOs':'1','Src_PDO_Voltage':'100','Src_PDO_Max_Current':'90',
        'Num_Snk_PDOs':'4','PD_Power_As_Sink':'60000','BC_1_2_Support':'0',
        'Enter_USB_Supported':'true' if port=='PD1' else 'false',
        'Host_Speed':('2' if reviewed else '5') if port=='PD1' else '0',
        'Type_C_Port_On_Hub':'true' if reviewed and port=='PD2' else 'false',
        'Is_DFP_On_Hub':'true' if reviewed and port=='PD2' else 'false'}
    if reviewed and port=='PD2':expected['Hub_Port_Number']='1'
    for tag,value in expected.items():
        element=xml_value(root,tag)
        require(element is not None and element.get('value')==value,
                f'{label}: {tag} must be {value}',errors)
    for tag,want,scale in [('Snk_PDO_Voltage',[5000,9000,15000,20000],50),
                           ('Snk_PDO_Op_Current',[3000]*4,10)]:
        actual=[int(e.get('value','-1'))*scale for e in root.iter() if e.tag==f'{{{NS}}}{tag}']
        require(actual==want,f'{label}: active sink list {tag} differs',errors)


def verify_binary_registers(path: Path,document: dict,errors: list[str]) -> None:
    image=path.read_bytes();regs=register_map(document)
    for reg in BINARY_REGISTERS:
        data=bytes(regs[reg]);record=bytes((0x0f,reg,0,len(data)-1))+data
        expected=2 if 'fullFlash' in path.name else 1
        require(image.count(record)==expected,
                f'{path.name}: register {reg:#x} complete record absent or duplicated',errors)


def verify_c_array(path: Path,binary: Path,errors: list[str]) -> None:
    arrays=re.findall(r'=\s*\{([^}]*)\}',path.read_text())
    if len(arrays)!=1 or not re.fullmatch(r'[\s,0-9a-fAxX]+',arrays[0]):
        errors.append(f'{path.name}: expected one literal byte array');return
    tokens=[s.strip() for s in arrays[0].split(',') if s.strip()]
    if any(not re.fullmatch(r'0x[0-9a-fA-F]{2}',s) for s in tokens):
        errors.append(f'{path.name}: non-byte literal in array');return
    require(bytes(int(s,16) for s in tokens)==binary.read_bytes(),
            f'{path.name}: C array differs from binary',errors)


def check_file(metadata: dict,errors: list[str],base: Path=ROOT) -> Path:
    path=base/metadata['path']
    require(path.is_file(),f'missing artifact {metadata["path"]}',errors)
    if path.is_file():
        require(sha256(path)==metadata['sha256'],f'hash mismatch {metadata["path"]}',errors)
        require(path.stat().st_size==metadata['bytes'],f'size mismatch {metadata["path"]}',errors)
    return path


def verify_release(require_generated: bool=False) -> list[str]:
    errors=[];manifest=json.loads(MANIFEST.read_text())
    require(manifest.get('schema_version')==2 and set(manifest.get('ports',{}))=={'PD1','PD2'},
            'distinct physical-port manifests are required',errors)
    require(manifest.get('status')=='GENERATED_PENDING_HIL','export status is inconsistent',errors)
    for port,metadata in manifest['ports'].items():
        source=check_file(metadata['source'],errors)
        document=json.loads(source.read_text());verify_policy(document,port,errors,port)
        reviewed=check_file(metadata['reviewed_vif'],errors);verify_vif(reviewed,errors,port)
        require(metadata['programming_and_readback']['status']=='NOT_RUN',
                f'{port}: this source checkpoint has no programming/readback evidence',errors)
        if not require_generated:continue
        paths={name:check_file(value,errors) for name,value in metadata['generated'].items()}
        for name,path in paths.items():
            if path.is_file() and name.endswith('.bin'):verify_binary_registers(path,document,errors)
        for name,path in paths.items():
            if name.endswith('.c') and path.is_file() and path.with_suffix('.bin').is_file():
                verify_c_array(path,path.with_suffix('.bin'),errors)
        archive=paths['official-export.zip']
        if archive.is_file():
            with zipfile.ZipFile(archive) as z:
                members={Path(n).name:n for n in z.namelist() if not n.endswith('/')}
                expected=set(paths)-{'official-export.zip'}
                require(set(members)==expected,f'{port}: original archive member set differs',errors)
                for name in expected & set(members):
                    if paths[name].is_file():
                        require(z.read(members[name])==paths[name].read_bytes(),
                                f'{port}: retained {name} differs from original archive',errors)
        raw=next(path for name,path in paths.items() if name.endswith('_raw.json'))
        if raw.is_file():
            require(register_map(json.loads(raw.read_text()))==register_map(document),
                    f'{port}: tracked register map differs from untouched TI export',errors)
        original=check_file(metadata['original_vif'],errors)
        if original.is_file():verify_vif(original,errors,port,False)
        low=next(path for name,path in paths.items() if name.endswith('_lowRegion.bin'))
        full=next(path for name,path in paths.items() if name.endswith('_fullFlash.bin'))
        if low.is_file() and full.is_file():
            require(full.read_bytes().count(low.read_bytes())==2,f'{port}: full flash must contain two complete low images',errors)
            require(sha256(full)==metadata['programming_and_readback']['expected_full_flash_sha256'],
                    f'{port}: pending readback is bound to another image',errors)
    return errors


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--require-generated',action='store_true')
    args=parser.parse_args()
    try:errors=verify_release(args.require_generated)
    except (ValueError,KeyError,IndexError,OSError,ET.ParseError,StopIteration,zipfile.BadZipFile) as exc:errors=[str(exc)]
    if errors:
        print('TPS25751A CONFIGURATION FAILED')
        for error in errors:print('- '+error)
        return 1
    print('TPS25751A: PASS (PD1 Gen 2x1 host, PD2 USB2 hub host; 5 V / 900 mA source; 5/9/15/20 V at 3 A sink)')
    print('official originals retained; reviewed VIF metadata is a draft; programming and HIL NOT_RUN')
    return 0

if __name__=='__main__':sys.exit(main())
