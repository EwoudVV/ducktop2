#!/usr/bin/env python3
"""Exact single-unit pin maps for the raw-pack thermal monitor.

Primary pin tables: TI TLV1864 table 4-3, TPS709 table 5-1 (TPS709 DBV),
SN74AUP2G126 DCU top view, ISO7041 section 6 and SN74LVC1G07 DCK.
The connector's MP pin represents both stock JST SH hold-down lands.
"""
from pathlib import Path

HERE=Path(__file__).resolve().parent
LIBRARY=HERE/'BMS_Thermal.kicad_sym'
SYMBOLS={
    'TLV1864PW':{
        'footprint':'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
        'url':'https://www.ti.com/lit/ds/symlink/tlv1864.pdf',
        'pins':[(1,'OUT1','open_collector'),(2,'IN1-','input'),(3,'IN1+','input'),
                (4,'V+','power_in'),(5,'IN2+','input'),(6,'IN2-','input'),
                (7,'OUT2','open_collector'),(8,'OUT3','open_collector'),
                (9,'IN3-','input'),(10,'IN3+','input'),(11,'V-','power_in'),
                (12,'IN4+','input'),(13,'IN4-','input'),(14,'OUT4','open_collector')]},
    'TPS70933DBV':{
        'footprint':'Package_TO_SOT_SMD:SOT-23-5',
        'url':'https://www.ti.com/lit/ds/symlink/tps709.pdf',
        'pins':[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),
                (4,'NC','no_connect'),(5,'OUT','power_out')]},
    'SN74AUP2G126DCU':{
        'footprint':'ducktop2:TI_DCU0008A_VSSOP8',
        'url':'https://www.ti.com/lit/ds/symlink/sn74aup2g126.pdf',
        'pins':[(1,'1OE','input'),(2,'1A','input'),(3,'2Y','tri_state'),
                (4,'GND','power_in'),(5,'2A','input'),(6,'1Y','tri_state'),
                (7,'2OE','input'),(8,'VCC','power_in')]},
    'ISO7041FDBQ':{
        'footprint':'Package_SO:QSOP-16_3.9x4.9mm_P0.635mm',
        'url':'https://www.ti.com/lit/ds/symlink/iso7041.pdf',
        'pins':[(1,'VCC1','power_in'),(2,'GND1','power_in'),(3,'INA','input'),
                (4,'INB','input'),(5,'INC','input'),(6,'OUTD','output'),
                (7,'EN1','input'),(8,'GND1','power_in'),(9,'GND2','power_in'),
                (10,'EN2','input'),(11,'IND','input'),(12,'OUTC','output'),
                (13,'OUTB','output'),(14,'OUTA','output'),(15,'GND2','power_in'),
                (16,'VCC2','power_in')]},
    'ISO7021FD':{
        'footprint':'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
        'url':'https://www.ti.com/lit/ds/symlink/iso7021.pdf',
        'pins':[(1,'VCC1','power_in'),(2,'OUTA','output'),(3,'INB','input'),
                (4,'GND1','power_in'),(5,'GND2','power_in'),(6,'OUTB','output'),
                (7,'INA','input'),(8,'VCC2','power_in')]},
    'SN74LVC2G07DCK':{
        'footprint':'Package_TO_SOT_SMD:SOT-363_SC-70-6',
        'url':'https://www.ti.com/lit/ds/symlink/sn74lvc2g07.pdf',
        'pins':[(1,'1A','input'),(2,'GND','power_in'),(3,'2A','input'),
                (4,'2Y','open_collector'),(5,'VCC','power_in'),(6,'1Y','open_collector')]},
    'SN74AUP2G07DCK':{
        'footprint':'Package_TO_SOT_SMD:SOT-363_SC-70-6',
        'url':'https://www.ti.com/lit/ds/symlink/sn74aup2g07.pdf',
        'pins':[(1,'1A','input'),(2,'GND','power_in'),(3,'2A','input'),
                (4,'2Y','open_collector'),(5,'VCC','power_in'),(6,'1Y','open_collector')]},
    'BAT54S_AKC':{
        'footprint':'Package_TO_SOT_SMD:SOT-23',
        'url':'https://www.diodes.com/datasheet/download/BAT54.pdf','reference':'D',
        'pins':[(1,'A1','passive'),(2,'K2','passive'),(3,'K1_A2','passive')]},
    'SN74LVC1G07DCK':{
        'footprint':'Package_TO_SOT_SMD:SOT-353_SC-70-5',
        'url':'https://www.ti.com/lit/ds/symlink/sn74lvc1g07.pdf',
        'pins':[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),
                (4,'Y','open_collector'),(5,'VCC','power_in')]},
    'Conn_01x06_Thermal_MP':{
        'footprint':'Connector_JST:JST_SH_SM06B-SRSS-TB_1x06-1MP_P1.00mm_Horizontal',
        'url':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf','reference':'J',
        'pins':[(n,f'Pin_{n}','passive') for n in range(1,7)]+[('MP','MP','passive')]},
}


def symbol_text(name,spec):
    pins=spec['pins']; half=(len(pins)+1)//2
    top=(half-1)*1.27; height=top+2.54
    rows=[f'(symbol "{name}" (exclude_from_sim no) (in_bom yes) (on_board yes)',
          f'(property "Reference" "{spec.get("reference","U")}" (at 0 {height+2.54} 0) (effects (font (size 1.27 1.27))))',
          f'(property "Value" "{name}" (at 0 {-height-2.54} 0) (effects (font (size 1.27 1.27))))',
          f'(property "Footprint" "{spec["footprint"]}" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))',
          f'(property "Datasheet" "{spec["url"]}" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))',
          f'(symbol "{name}_0_1" (rectangle (start -7.62 {height}) (end 7.62 {-height}) (stroke (width 0.254) (type default)) (fill (type background))))',
          f'(symbol "{name}_1_1"']
    for index,(number,label,kind) in enumerate(pins):
        side=index>=half;x=10.16 if side else -10.16
        y=top-2.54*(index%half);angle=180 if side else 0
        rows.append(f'(pin {kind} line (at {x} {y:.2f} {angle}) (length 2.54) (name "{label}" (effects (font (size 1 1)))) (number "{number}" (effects (font (size 1 1)))))')
    return '\n'.join(rows+[')',')'])


def library_text():
    return '(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor")\n'+\
        '\n'.join(symbol_text(name,spec) for name,spec in SYMBOLS.items())+'\n)\n'


if __name__=='__main__':
    LIBRARY.write_text(library_text())
    print(LIBRARY)
