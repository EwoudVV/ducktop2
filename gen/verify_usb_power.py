#!/usr/bin/env python3
"""Check USB permission, reset and power loom wiring in native XML netlists."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

class ContractError(ValueError):pass

class Netlist:
    def __init__(self,path):
        self.path=Path(path);root=ET.parse(path).getroot()
        self.parts={p.attrib['ref']:p for p in root.findall('./components/comp')}
        self.pins={}
        for net in root.findall('./nets/net'):
            for node in net.findall('node'):
                key=(node.attrib['ref'],node.attrib['pin'])
                if key in self.pins:raise ContractError('duplicate pin '+str(key))
                self.pins[key]=net.attrib['name']
    def net(self,ref,pin):
        try:return self.pins[(ref,str(pin))]
        except KeyError:raise ContractError(f'{self.path.name}: missing {ref}.{pin}') from None
    def expect(self,ref,pin,name):
        actual=self.net(ref,pin)
        if actual.rsplit('/',1)[-1]!=name:raise ContractError(f'{ref}.{pin}: {actual} != {name}')
    def joined(self,*pins):
        values={self.net(*pin) for pin in pins}
        if len(values)!=1:raise ContractError(f'split required net {pins}: {values}')
    def field(self,ref,name):
        part=self.parts[ref]
        if name=='Footprint':return part.findtext('footprint')
        return next((f.text for f in part.findall('./fields/field') if f.attrib['name']==name),None)


def check(center,left,right):
    for n,net in enumerate(['USB5_PERMIT','USB_J21_PERMIT','USB_J11_PERMIT','USB_J22_PERMIT',
                             'USB_J23_PERMIT','USB_J12_PERMIT','USB_J24_PERMIT','USB_J25_PERMIT'],4):
        left.expect('U2400',n,net)
    for pin,net in {2:'MCU_3V3',3:'SERVICE_MUX_RESET_N',21:'GND',22:'PD1_I2C_SCL',23:'PD1_I2C_SDA',
                    13:'USB5_FAULT_CLEAR_N',14:'USB5_FAULT_N',15:'USB5_OC_N',16:'USB5_PG',
                    17:'PD1_SOURCE_PG',18:'PD2_SOURCE_PG',19:'INTERNAL_USB_VBUS_VALID'}.items():left.expect('U2400',pin,net)
    left.joined(('U2400',3),('FPC101',35),('R2420',1))
    center.joined(('FPC102',7),('U46',4))
    for lp,cp,rp,rcp,net in [(38,4,42,10,'USB_J11_PERMIT'),(39,3,43,9,'USB_J12_PERMIT'),
                              (36,6,41,11,'PD2_SOURCE_PG')]:
        left.expect('FPC101',lp,net);center.expect('FPC102',cp,net)
        center.joined(('FPC102',cp),('FPC103',rcp));right.expect('FPC104',rp,net)
    left.joined(('U2401',10),('RS1860',1),('RS1861',1))
    left.joined(('U2401',9),('U2401',8),('RS1860',2),('RS1861',2),('U2403',2))
    left.joined(('U2401',3),('U2413',1))
    left.joined(('U2413',4),('U2402',7),('U2411',2),('R2429',1))
    left.joined(('U2413',2),('U2400',19),('FPC101',41))
    center.joined(('U6',7),('U2412',1))
    center.joined(('U771',4),('R775',2),('U2412',2))
    center.joined(('U2412',4),('R2428',1),('FPC102',1))
    center.expect('U2412',5,'MCU_3V3')
    left.joined(('U2402',3),('U2410',3))
    left.joined(('U2410',4),('U2411',1))
    left.joined(('U2411',4),('R2400',1),('R1710',1))
    left.expect('R2400',2,'GND')
    for board,gate,tcpc,base,net in [(left,'U2403','U41',2000,'PD1_PP5V_GATED'),
                                    (right,'U2404','U42',2040,'PD2_PP5V_GATED')]:
        board.expect(gate,6,net)
        board.joined((gate,6),(gate,5),(tcpc,34),('C'+str(base+25),1),
                     ('C'+str(base+26),1),('C'+str(base+27),1))
    for board,base,port,gate,ctl in [(left,1780,'J22','U2405','HUB_PRT_CTL2'),
        (left,1740,'J23','U2406','HUB_PRT_CTL3'),(right,1760,'J12','U2409','HUB_PRT_CTL4')]:
        board.joined((gate,4),('U'+str(base),3),('U'+str(base+1),6))
        board.expect('U'+str(base),4,ctl);board.expect('U'+str(base+1),1,ctl)
        if board.field('R'+str(base),'MPN')!='RC0603FR-0719K1L':raise ContractError('source ILIM order code')
    for port,gate,switch in [('J24','U2407','U1800'),('J25','U2408','U1803')]:
        left.joined((gate,4),(switch,3));left.expect(gate,2,'INTERNAL_USB_VBUS_VALID')
    looms=[(center,'J2430',left,'J2431',['VSYS','PD1_VBUS_RAW','USB_PD_SELECTED','AUX_DC_RAW','SYS_3V3','MCU_3V3']+['GND']*6,'43045-1212'),
           (center,'J2432',right,'J2433',['PD2_VBUS_GATED','PD2_VBUS_RAW','SYS_5V','SYS_3V3','PCIE_3V3','MCU_3V3']+['GND']*4,'43045-1012'),
           (left,'J2434',right,'J2435',['GND','USB_PORT_5V'],'XT30PW-F30.G.Y')]
    for a,ar,b,br,nets,mpn in looms:
        for index,net in enumerate(nets,1):a.expect(ar,index,net);b.expect(br,index,net)
        if a.field(ar,'MPN')!=mpn or b.field(br,'MPN')!=mpn:raise ContractError('loom connector identity')
    for board,ref,count,mpn in [(left,'FPC101',41,'5039084120'),(center,'FPC102',41,'5039084120'),
                               (right,'FPC104',51,'5039085120'),(center,'FPC103',51,'5039085120')]:
        numbered={int(pin) for r,pin in board.pins if r==ref and pin.isdigit()}
        if numbered!=set(range(1,count+1)) or board.field(ref,'MPN')!=mpn:
            raise ContractError('signal connector count or exact identity drifted: '+ref)
    for board,ref in [(left,'J2434'),(right,'J2435')]:
        if board.field(ref,'Footprint')!='ducktop2:AMASS_XT30PW-F30_G_Y':
            raise ContractError('XT30 current drawing/finished-hole footprint is required')
    power={'VSYS','SYS_5V','SYS_3V3','MCU_3V3','PCIE_3V3','USB_PORT_5V','PD1_VBUS_RAW',
           'PD2_VBUS_RAW','PD2_VBUS_GATED','USB_PD_SELECTED','AUX_DC_RAW'}
    for board,refs in [(center,('FPC102','FPC103')),(left,('FPC101',)),(right,('FPC104',))]:
        for (ref,pin),net in board.pins.items():
            if ref in refs and net.rsplit('/',1)[-1] in power:raise ContractError('power remains on signal cable')
    if any(n.rsplit('/',1)[-1]=='USB_PORT_5V' for n in center.pins.values()):
        raise ContractError('USB5 still crosses center instead of direct loom')
    return {'status':'PASS','boundary':'source wiring only; no PCB routing or physical qualification',
            'netlists':{p.path.name:hashlib.sha256(p.path.read_bytes()).hexdigest() for p in (center,left,right)}}


def main():
    parser=argparse.ArgumentParser()
    for name in ('center','left','right'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:result=check(Netlist(args.center),Netlist(args.left),Netlist(args.right))
    except (ContractError,KeyError) as error:raise SystemExit(str(error)) from None
    text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')

if __name__=='__main__':main()
