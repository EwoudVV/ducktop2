#!/usr/bin/env python3
"""Pin maps for the monitor's current, startup and isolated control circuits."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEVICES = {
    'INA381A3DGS': ('Package_SO:MSOP-10_3x3mm_P0.5mm', 'ina381', {
        1: ('IN+', 'input'), 2: ('VS', 'power_in'), 3: ('ALERT_N', 'open_collector'),
        4: ('RESET', 'input'), 5: ('GND', 'power_in'), 6: ('NC', 'passive'),
        7: ('CMPREF', 'input'), 8: ('CMPIN', 'input'), 9: ('VOUT', 'output'), 10: ('IN-', 'input')}),
    'INA381A4DGS': ('Package_SO:MSOP-10_3x3mm_P0.5mm', 'ina381', {
        1: ('IN+', 'input'), 2: ('VS', 'power_in'), 3: ('ALERT_N', 'open_collector'),
        4: ('RESET', 'input'), 5: ('GND', 'power_in'), 6: ('NC', 'passive'),
        7: ('CMPREF', 'input'), 8: ('CMPIN', 'input'), 9: ('VOUT', 'output'), 10: ('IN-', 'input')}),
    'REF3425DBV': ('Package_TO_SOT_SMD:SOT-23-6', 'ref34', {
        1: ('GND_F', 'power_in'), 2: ('GND_S', 'power_in'), 3: ('EN', 'input'),
        4: ('IN', 'power_in'), 5: ('OUT_S', 'input'), 6: ('OUT_F', 'power_out')}),
    'TPS3808G30DBV': ('Package_TO_SOT_SMD:SOT-23-6', 'tps3808', {
        1: ('RESET_N', 'open_collector'), 2: ('GND', 'power_in'), 3: ('MR_N', 'input'),
        4: ('CT', 'passive'), 5: ('SENSE', 'input'), 6: ('VDD', 'power_in')}),
    'TPS26600PWP': ('ducktop2:HTSSOP16_EP_ThermalVias', 'tps2660', {
        1: ('IN', 'power_in'), 2: ('IN', 'power_in'), 3: ('UVLO', 'input'),
        4: ('NC', 'passive'), 5: ('OVP', 'input'), 6: ('MODE', 'input'),
        7: ('SHDN', 'input'), 8: ('RTN', 'power_in'), 9: ('GND', 'power_in'),
        10: ('IMON', 'output'), 11: ('ILIM', 'passive'), 12: ('DV_DT', 'passive'),
        13: ('NC', 'passive'), 14: ('FLT_N', 'open_collector'),
        15: ('OUT', 'power_out'), 16: ('OUT', 'passive'), 17: ('EP_RTN', 'power_in')}),
    'ISO1640BD': ('Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 'iso1640', {
        1: ('VCC1', 'power_in'), 2: ('SDA1', 'bidirectional'), 3: ('SCL1', 'bidirectional'),
        4: ('GND1', 'power_in'), 5: ('GND2', 'power_in'), 6: ('SCL2', 'bidirectional'),
        7: ('SDA2', 'bidirectional'), 8: ('VCC2', 'power_in')}),
    'TPS22941DCK': ('Package_TO_SOT_SMD:SOT-353_SC-70-5', 'tps22942', {
        1: ('VOUT', 'power_out'), 2: ('GND', 'power_in'), 3: ('OC_N', 'open_collector'),
        4: ('ON_N', 'input'), 5: ('VIN', 'power_in')}),
    # QOD connects to VOUT as shown in TI's pin table. It sinks only while
    # the series switch is off, so the tie is not an active-output conflict.
    'TPS22810DBV': ('Package_TO_SOT_SMD:SOT-23-6', 'tps22810', {
        1: ('VIN', 'power_in'), 2: ('GND', 'power_in'), 3: ('EN_UVLO', 'input'),
        4: ('CT', 'passive'), 5: ('QOD', 'passive'), 6: ('VOUT', 'power_out')}),
}


def library():
    text = ['(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor")']
    for name, (footprint, source, pins) in DEVICES.items():
        half = (len(pins)+1)//2
        height = max(5.08, (half-1)*1.27+2.54)
        text.append(f'  (symbol "{name}" (exclude_from_sim no) (in_bom yes) (on_board yes)')
        for key, value, y, hidden in [
            ('Reference', 'U', height+2.54, False), ('Value', name, -height-2.54, False),
            ('Footprint', footprint, 0, True),
            ('Datasheet', f'https://www.ti.com/lit/ds/symlink/{source}.pdf', 0, True),
        ]:
            text.append(f'    (property "{key}" "{value}" (at 0 {y} 0) '
                        f'{"(hide yes) " if hidden else ""}(effects (font (size 1.27 1.27))))')
        text += [f'    (symbol "{name}_0_1"',
                 f'      (rectangle (start -7.62 {height}) (end 7.62 {-height}) '
                 '(stroke (width 0.254) (type default)) (fill (type background))))',
                 f'    (symbol "{name}_1_1"']
        for index, (number, (pin_name, kind)) in enumerate(pins.items()):
            left = index < half
            row = index if left else index-half
            x, angle = (-10.16, 0) if left else (10.16, 180)
            y = height-2.54-row*2.54
            text.append(f'      (pin {kind} line (at {x} {y} {angle}) (length 2.54) '
                        f'(name "{pin_name}" (effects (font (size 1 1)))) '
                        f'(number "{number}" (effects (font (size 1 1)))))')
        text += ['    )', '  )']
    return '\n'.join(text+[')', ''])


if __name__ == '__main__':
    (ROOT/'gen/BMS_Support.kicad_sym').write_text(library())
