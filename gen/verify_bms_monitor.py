#!/usr/bin/env python3
"""Check the saved monitor netlist, including the paths ERC cannot infer."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET


class ContractError(ValueError):
    pass


def read_netlist(path):
    root = ET.parse(path).getroot()
    parts = {}
    for c in root.findall('./components/comp'):
        parts[c.get('ref')] = {
            'value': c.findtext('value') or '', 'footprint': c.findtext('footprint') or '',
            'fields': {f.get('name'): f.text or '' for f in c.findall('./fields/field')},
            'attributes': {p.get('name') for p in c.findall('property') if p.get('value') is None},
            'pins': {},
        }
    for node in root.findall('./nets/net'):
        name = node.get('name')
        for pin in node.findall('node'):
            parts[pin.get('ref')]['pins'][pin.get('pin')] = name
    return parts


def verify(parts):
    def require(ok, message):
        if not ok:
            raise ContractError(message)
    def pin(ref, number):
        require(ref in parts, f'missing {ref}')
        return parts[ref]['pins'].get(str(number))
    def expect(ref, pins):
        for number, name in pins.items():
            require(pin(ref, number) == name, f'{ref}.{number}: expected {name}, got {pin(ref, number)}')
    def nodes(ref, a, b):
        require({pin(ref, 1), pin(ref, 2)} == {a, b}, f'{ref} wrong endpoints')
    def mpn(ref, name):
        require(parts[ref]['fields'].get('MPN') == name, f'{ref} wrong part identity')

    raw, fg, ctrl = '/PACK_NEG_RAW', '/FG_VSS', '/CTRL_GND'
    vin, out, common, reg = '/BAT_PROT_VIN', '/PACK_POS_FUSED', '/BAT_PROT_FET_COMMON', '/BQ_REG1'
    expect('J2', {1: raw, 2: '/PACK_POS_RAW'})
    expect('J2072', {1: out, 2: fg})
    expect('J2201', {1: '/CELL1_TAP', 2: '/CELL2_TAP', 'MP': raw})
    nodes('F1', '/PACK_POS_RAW', vin)
    mpn('F1', '3-101-051')
    mpn('U719', 'BQ76922RSNR')
    expect('U719', {1: '/BQ_BAT', 2: '/BQ_VC5', 3: '/BQ_VC2', 4: '/BQ_VC2',
        5: '/BQ_VC2', 6: '/BQ_VC2', 7: '/BQ_VC2', 8: '/BQ_VC1', 9: '/BQ_VC0',
        10: raw, 11: '/BMS_SRP', 12: '/BMS_SRN', 15: '/BQ_REG18', 16: '/BQ_ALERT_AWAKE',
        17: '/BMS_RAW_SCL', 18: '/BMS_RAW_SDA', 19: '/BMS_CFETOFF', 20: '/BMS_DFETOFF',
        22: reg, 23: '/BQ_REGIN', 24: '/BQ_REGIN', 26: '/BQ_PDSG', 28: '/BQ_LD',
        29: '/BQ_PACK', 30: '/BQ_DSG', 31: '/BQ_CHG', 32: '/BQ_CP1', 33: raw})
    for ref, source, gate in [('Q11', vin, '/CHG_GATE'), ('Q12', out, '/DSG_GATE')]:
        mpn(ref, 'CSD18540Q5B')
        expect(ref, {1: source, 2: source, 3: source, 4: gate, 5: common})
    expect('RS11', {1: raw, 2: fg, 3: '/BMS_RAW_KELVIN', 4: '/BMS_FG_KELVIN'})
    mpn('RS11', 'CSS4J-4026K-2L00F')
    nodes('R845', '/BMS_RAW_KELVIN', '/BMS_SRP')
    nodes('R846', '/BMS_FG_KELVIN', '/BMS_SRN')

    rtn = '/PDSG_RTN'
    expect('U2218', {1: vin, 2: vin, 3: '/PDSG_UVLO', 5: rtn, 6: '/PDSG_MODE',
        7: '/PDSG_SHDN', 8: rtn, 9: raw, 11: '/PDSG_ILIM', 12: '/PDSG_DVDT',
        14: '/PDSG_FLT_N', 15: out, 16: out, 17: rtn})
    mpn('U2218', 'TPS26600PWPR')
    expect('Q2211', {1: '/PDSG_CTRL_GATE', 2: '/BQ_BAT', 3: '/PDSG_CTRL_HIGH'})
    nodes('R891', '/PDSG_CTRL_GATE', '/BQ_BAT')
    expect('Q2212', {1: '/PDSG_PERMIT_GATE', 2: '/PDSG_SHDN', 3: '/PDSG_SHDN_DRIVE'})
    nodes('R894', '/THERM_DSG_GATE', '/PDSG_PERMIT_GATE')
    nodes('R893', '/PDSG_SHDN', rtn)
    for ref, before, after in [('R870', '/BQ_CHG', '/CHG_DRV_RELEASED'),
                               ('R871', '/BQ_DSG', '/DSG_DRV_RELEASED'),
                               ('R872', '/PDSG_CTRL_HIGH', '/PDSG_CTRL_RELEASED')]:
        nodes(ref, before, after)
        require('dnp' in parts[ref]['attributes'] and 'exclude_from_bom' in parts[ref]['attributes'],
                f'{ref} must be an unpopulated assembly release link')

    for ref, kind, plus, minus, identity in [
        ('U2210', 'DSG', '/BMS_FG_KELVIN', '/BMS_RAW_KELVIN', 'INA381A3IDGSR'),
        ('U2211', 'CHG', '/BMS_RAW_KELVIN', '/BMS_FG_KELVIN', 'INA381A4IDGSR')]:
        mpn(ref, identity)
        expect(ref, {1: f'/BMS_OC_{kind}_IN_P', 2: reg, 3: f'/THERM_{kind}_HEALTH',
            4: '/CURRENT_READY', 5: raw, 7: f'/BMS_OC_{kind}_LIMIT',
            8: f'/BMS_OC_{kind}_OUT', 9: f'/BMS_OC_{kind}_OUT', 10: f'/BMS_OC_{kind}_IN_N'})
        base = 2280 if kind == 'DSG' else 2282
        nodes(f'R{base}', plus, f'/BMS_OC_{kind}_IN_P')
        nodes(f'R{base+1}', minus, f'/BMS_OC_{kind}_IN_N')
    expect('U2213', {1: raw, 2: raw, 3: reg, 4: reg, 5: '/BMS_CURRENT_REF', 6: '/BMS_CURRENT_REF'})
    mpn('U2213', 'REF3425IDBVR')
    expect('U2214', {1: '/CURRENT_READY', 2: raw, 3: '/CURRENT_CLR_N',
                    4: '/CURRENT_DELAY', 5: reg, 6: reg})
    mpn('U2214', 'TPS3808G30DBVR')
    nodes('R2277', reg, '/CURRENT_DELAY')
    expect('U2215', {1: '/THERM_READY', 2: '/CURRENT_READY', 3: raw,
                    4: '/BMS_PERMIT_READY', 5: '/THERM_3V3'})
    # DCU output numbering is crossed: 1A pin2 drives1Y pin6.
    expect('U2205', {1: '/BMS_PERMIT_READY', 2: '/THERM_CHG_HEALTH', 3: '/THERM_DSG_PERMIT',
                    4: raw, 5: '/THERM_DSG_HEALTH', 6: '/THERM_CHG_PERMIT',
                    7: '/BMS_PERMIT_READY', 8: '/THERM_3V3'})
    for ref, kind, off in [('Q2200', 'CHG', '/BMS_CFETOFF'), ('Q2201', 'DSG', '/BMS_DFETOFF')]:
        expect(ref, {1: f'/THERM_{kind}_GATE', 2: raw, 3: off})
    nodes('R2236', '/BMS_OFF_BIAS', '/BMS_CFETOFF')
    nodes('R2239', '/BMS_OFF_BIAS', '/BMS_DFETOFF')
    expect('D2220', {1: '/BMS_OFF_BIAS', 2: '/THERM_3V3'})
    expect('D2221', {1: '/BMS_OFF_BIAS', 2: reg})

    expect('J2074', {1: '/PACK_MONITOR_READY', 2: '/PACK_I2C_SCL', 3: '/MCU_3V3',
                     4: '/PACK_I2C_SDA', 5: ctrl, 'MP': ctrl})
    expect('U2206', {1: '/CTRL_3V3', 2: '/ISO_CTRL_SDA', 3: '/ISO_CTRL_SCL', 4: ctrl,
                    5: raw, 6: '/BMS_RAW_SCL', 7: '/BMS_RAW_SDA', 8: reg})
    mpn('U2206', 'ISO1640BDR')
    expect('U2207', {1: '/CTRL_3V3', 2: '/ISO_CTRL_SCL', 3: '/ISO_CTRL_SDA', 4: ctrl,
                    5: '/CTRL_3V3', 6: '/PACK_I2C_SDA', 7: '/PACK_I2C_SCL', 8: '/CTRL_3V3'})
    expect('U2209', {1: reg, 3: '/BMS_MONITOR_READY_RAW', 4: raw, 5: ctrl,
                    6: '/CTRL_MONITOR_READY', 7: ctrl, 8: '/CTRL_3V3'})
    mpn('U2209', 'ISO7021FDR')
    expect('U2216', {1: '/CTRL_3V3', 2: ctrl, 3: '/PACK_MONITOR_READY', 4: ctrl, 5: '/MCU_3V3'})
    mpn('U2216', 'TPS22941DCKR')
    expect('U2217', {1: '/THERM_RAW_PRE', 2: raw, 3: '/BQ_ALERT_AWAKE',
                    5: '/THERM_RAW_IN', 6: '/THERM_RAW_IN'})
    mpn('U2217', 'TPS22810DBVR')
    nodes('R2200', '/PACK_POS_RAW', '/THERM_RAW_PRE')
    nodes('R2290', '/BQ_ALERT_AWAKE', raw)
    mpn('R2290', 'RC0603FR-07390KL')
    nodes('C2281', '/THERM_RAW_PRE', raw)
    mpn('C2281', 'GRM21BR71H105KA12L')
    expect('U2208', {2: '/THERM_READY', 3: raw, 4: '/BMS_MONITOR_READY_RAW', 5: reg})
    mpn('U2208', 'SN74LVC1G17DBVR')
    require('R2250' not in parts, 'REG1 must not back-power the awake output')

    # There is no resistor, test fixture or ground symbol across a return barrier.
    blocked = [{raw, fg}, {raw, ctrl}, {fg, ctrl}, {rtn, raw}, {rtn, fg}, {rtn, ctrl}]
    for ref, p in parts.items():
        if ref == 'RS11' or not p['footprint'].startswith('Resistor_SMD:'):
            continue
        pair = set(p['pins'].values())
        require(pair not in blocked, f'{ref} bypasses a current shunt or return domain')
    return {'status': 'PASS', 'components': len(parts), 'controller': 'BQ76922RSNR',
            'independent_guards': True, 'hardware_release_links_DNP': True,
            'native_pin_parity': True, 'operating_qualification': False}


def verify_main_interface(parts):
    def expect(ref, number, name):
        if parts[ref]['pins'].get(str(number)) != name:
            raise ContractError(f'{ref}.{number} must be {name}')
    for number, name in {1:'/PACK_MONITOR_READY', 2:'/I2C_SCL', 3:'/MCU_3V3',
                         4:'/I2C_SDA', 5:'GND', 'MP':'GND'}.items():
        expect('J2073', number, name)
    expect('U44', 10, '/PACK_MONITOR_READY')
    for ref, number in [('U44', 13), ('U2635', 3)]:
        name = parts[ref]['pins'].get(str(number), '')
        if name and not name.startswith('unconnected-'):
            raise ContractError(f'{ref}.{number} must not drive the repurposed I2C bus')
    expect('Q702', 1, '/CHG_ENABLE')
    if {parts['R2262']['pins'].get('1'), parts['R2262']['pins'].get('2')} != {'/CHG_ENABLE','GND'}:
        raise ContractError('charge request must default low independently of SDA')
    if {parts['R2263']['pins'].get('1'), parts['R2263']['pins'].get('2')} != {'/PACK_MONITOR_READY','GND'}:
        raise ContractError('alarm health must default low')
    for ref in ['U2210','R2260','R2261','C2260','R719']:
        if ref in parts:
            raise ContractError(f'obsolete charger temperature-bus connection {ref}')
    return {'status':'PASS','five_wire_bus':'I2C1 plus isolated monitor readiness',
            'SDA_cannot_gate_charger':True,'old_retry_output_disconnected':True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('netlist', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--main-interface', action='store_true')
    args = parser.parse_args()
    report = (verify_main_interface if args.main_interface else verify)(read_netlist(args.netlist))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
