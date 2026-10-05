#!/usr/bin/env python3
"""Check a BQ76922 profile and captured readback. No device I/O or OTP writes."""
import argparse
import copy
import json
import struct
from pathlib import Path

class ProfileError(ValueError):
    pass

INTERFACE = {
    0x9236: [0x0D], 0x9237: [0x00], 0x9239: [0x11], 0x923A: [0x10],
    0x92FA: [0x02], 0x92FB: [0x02], 0x92FC: [0x8A], 0x92FD: [0], 0x92FE: [0],
    0x9263: [0x60], 0x926B: [0x60], 0x9271: [0x60],
    0x930E: [0x00], 0x9262: [0x40], 0x9266: [0x40], 0x926A: [0x40],
    0x9270: [0x40], 0x92A3: [75], 0x92A4: [0], 0x92A5: [65],
    0x9303: [0x05], 0x9304: [0x13, 0], 0x926D: [0x00, 0x00], 0x9343: [0x50, 0],
}

REQUIRED = {0x9234, 0x9261, 0x9262, 0x9263, 0x9265, 0x9266, 0x9267,
            0x9269, 0x926A, 0x926B, 0x92C0, 0x92C1, 0x92C2, 0x92C3,
            0x9308, 0x9309, 0x930A, 0x930C, 0x930E, 0x930F, 0x9275, 0x9276, 0x927B,
            0x9278, 0x9279, 0x927C, 0x9280, 0x9281, 0x9282, 0x9283,
            0x9284, 0x9285, 0x9286, 0x9287, 0x91A8, 0x91AC, 0x9180,
            0x9182, 0x9188, 0x91B0, 0x91D4, 0x91D6}

def address(row):
    return int(row['address'], 0)

def check_profile(profile, require_complete=True):
    if profile.get('part') != 'BQ76922RSNR' or profile.get('cell_inputs') != [1, 2, 5]:
        raise ProfileError('wrong part or cell-input mapping')
    if profile.get('recovery_charging_enabled') is not False:
        raise ProfileError('recovery charging is disabled until cell limits are established')
    if profile.get('i2c_address_7bit') != 8 or profile.get('i2c_bus_hz') != 100000:
        raise ProfileError('wrong I2C address or bus rate')
    for key, expected in {'charge_voltage_mv':12120, 'charge_cell_max_mv':4100,
                          'charge_spread_max_mv':30, 'cell_voltage_error_mv':15}.items():
        if profile.get('admission', {}).get(key) != expected:
            raise ProfileError('charge admission mismatch: ' + key)
    host = {'taper_current_upper_ma':200, 'taper_cell_min_mv':3980,
            'taper_cell_sum_min_mv':12000, 'taper_hold_ms':30000,
            'recharge_cell_max_mv':3950, 'recharge_hold_ms':5000, 'cv_dwell_max_ms':7200000}
    if any(profile.get('host_charge', {}).get(k) != v for k,v in host.items()):
        raise ProfileError('host charge criteria mismatch')
    for key in ('cell_voltage_qualified','charge_voltage_qualified','termination_qualified'):
        if profile.get(key) is not False:
            raise ProfileError('prototype charge qualification remains false: ' + key)
    entries = profile.get('rows', [])
    rows = {address(row): row for row in entries}
    if any(addr < 0x9000 or addr > 0xFFFF for addr in rows):
        raise ProfileError('profile rows must be data-memory addresses')
    if len(rows) != len(entries):
        raise ProfileError('duplicate data-memory address')
    for addr, expected in INTERFACE.items():
        if addr not in rows or rows[addr].get('bytes') != expected:
            raise ProfileError(f'interface mismatch at {addr:#06x}')
    if not REQUIRED.issubset(rows):
        raise ProfileError('missing protection or calibration address')
    missing = []
    for row in entries:
        count = row.get('length')
        values = row.get('bytes')
        if not isinstance(count, int) or not 1 <= count <= 4:
            raise ProfileError('invalid row size')
        if values is None:
            missing.append(row['name'])
        elif len(values) != count or any(type(x) is not int or not 0 <= x <= 255 for x in values):
            raise ProfileError('invalid data-memory byte')
    for key in ('discharge_cell_min_mv', 'normal_charge_cell_min_mv', 'cell_max_mv',
                'pack_min_mv', 'current_gain_min_permille', 'current_offset_ma', 'dynamic_reserve_ma'):
        if profile.get('admission', {}).get(key) is None:
            missing.append(key)
    if require_complete and missing:
        raise ProfileError('unresolved values: ' + ', '.join(missing))
    return missing

def prepare_unit_profile(profile, factory):
    """Apply captured unit factory trims; every release stays false."""
    check_profile(profile)
    if factory.get('part') != profile['part'] or factory.get('before_any_ram_or_otp_write') is not True:
        raise ProfileError('unmodified unit factory capture is required')
    entries = factory.get('rows', [])
    captured = {address(row): row for row in entries}
    if len(captured) != len(entries):
        raise ProfileError('duplicate factory capture address')
    result = copy.deepcopy(profile)
    output = {address(row): row for row in result['rows']}
    for addr in (0x9180, 0x9182, 0x9188, 0x91B0, 0x91A8):
        row = captured.get(addr)
        if not row or not (row.get('crc_verified') is True or row.get('bytes_repeat') == row.get('bytes')) or \
            row.get('length') != len(row['bytes']) + 4 or \
            row.get('checksum') != transfer_checksum(addr, row['bytes']):
            raise ProfileError(f'factory trim capture invalid at {addr:#06x}')
        if len(row['bytes']) != output[addr]['length']:
            raise ProfileError('factory trim size mismatch')
        if addr != 0x91A8:
            output[addr]['bytes'] = row['bytes']
    factory_gain = struct.unpack('<f', bytes(captured[0x91A8]['bytes']))[0]
    if not 0.01 <= factory_gain <= 1000:
        raise ProfileError('invalid factory CC Gain')
    # TI factory nominal is a1mOhm current scale. Preserve its gain trim
    # while selecting the nominal2mOhm assembly; bench current calibration
    # and drift qualification remain separate requirements.
    new_gain = factory_gain / (result['shunt']['nominal_ohm'] * 1000)
    output[0x91A8]['bytes'] = list(struct.pack('<f', new_gain))
    output[0x91AC]['bytes'] = list(struct.pack('<f', new_gain * 298261.6178))
    result['unit_factory_trim_capture_applied'] = True
    result['released_for_ram_test'] = result['released_for_otp'] = result['released_for_assembly'] = False
    result['calibration_qualified'] = False
    result['cell_voltage_qualified'] = result['charge_voltage_qualified'] = result['termination_qualified'] = False
    result['qualification'] = {key: False for key in result['qualification']}
    check_profile(result)
    return result

def transfer_checksum(addr, data):
    return (~((addr & 255) + (addr >> 8) + sum(data))) & 255

def c_profile(profile):
    check_profile(profile)
    if not profile.get('unit_factory_trim_capture_applied'):
        raise ProfileError('per-unit factory trim capture is required')
    lines = ['#include "bq76922_profile.h"', '',
             '/* Unit readback profile. Every operating qualification remains disabled. */',
             'static const bq76922_config_row_t unit_rows[] = {']
    for row in profile['rows']:
        label = row['name'].replace('*/', '* /').replace('\n', ' ')
        data = ', '.join(f'0x{x:02x}u' for x in row['bytes'])
        lines.append(f'    {{0x{address(row):04x}u, {row["length"]}, {{{data}}}}}, /* {label} */')
    lines += ['};', '', 'const bq76922_profile_t ducktop2_bq76922_profile = {',
              '    .rows = unit_rows,',
              '    .row_count = sizeof(unit_rows) / sizeof(unit_rows[0]),',
              '    .complete = true,', '    .qualified = false,']
    lines += ['    .cell_voltage_qualified = false,', '    .charge_voltage_qualified = false,',
              '    .termination_qualified = false,']
    for key in ('charge_voltage_mv','charge_cell_max_mv','charge_spread_max_mv','cell_voltage_error_mv',
                'charge_max_rise_mv','discharge_cell_min_mv', 'normal_charge_cell_min_mv', 'cell_max_mv', 'pack_min_mv',
                'current_gain_min_permille', 'current_offset_ma', 'dynamic_reserve_ma',
                'discharge_limit_ma', 'charge_limit_ma'):
        value = profile['admission'][key]
        if type(value) is not int or not 0 <= value <= 65535:
            raise ProfileError('invalid C admission field')
        lines.append(f'    .{key} = {value},')
    lines += ['    .current_lsb_ma = 1,', '    .sample_max_age_ms = 200,',
              '    .config_max_age_ms = 10000', '};', '']
    return '\n'.join(lines)

def verify_readback(profile, capture):
    check_profile(profile)
    if capture.get('part') != profile['part']:
        raise ProfileError('wrong captured device')
    if capture.get('security_state') != 'UNSEALED':
        raise ProfileError('full readback requires UNSEALED mode')
    if capture.get('manufacturing_status') != 0x50:
        raise ProfileError('autonomous FET/PF mode not verified')
    entries = capture.get('rows', [])
    captured = {address(row): row for row in entries}
    if len(entries) != len(captured):
        raise ProfileError('duplicate captured address')
    for row in profile['rows']:
        addr = address(row)
        actual = captured.get(addr)
        if not actual or actual.get('bytes') != row['bytes']:
            raise ProfileError(f'readback mismatch at {addr:#06x}')
        if actual.get('length') != len(actual['bytes']) + 4:
            raise ProfileError(f'readback length mismatch at {addr:#06x}')
        if actual.get('checksum') != transfer_checksum(addr, actual['bytes']):
            raise ProfileError(f'readback checksum mismatch at {addr:#06x}')
        if actual.get('crc_verified') is not True:
            raise ProfileError(f'wire CRC not verified at {addr:#06x}')
    if capture.get('cold_cycle_readback') is not True:
        raise ProfileError('cold-cycle readback is required')
    return True

def ram_plan(profile):
    check_profile(profile)
    if profile.get('released_for_ram_test') is not True:
        raise ProfileError('RAM test profile has not been released')
    if profile.get('unit_factory_trim_capture_required') and not profile.get('unit_factory_trim_capture_applied'):
        raise ProfileError('per-unit factory trim capture is required')
    rows = []
    for row in profile['rows']:
        addr, data = address(row), row['bytes']
        rows.append({'address': row['address'], 'bytes': data,
                     'transfer_checksum': transfer_checksum(addr, data),
                     'transfer_length': len(data) + 4})
    return {'mode': 'reviewable RAM-only write plan; no device I/O',
            'enter_config_update': '0x0090', 'exit_config_update': '0x0092',
            'rows': rows,
            'fet_enable': 'manual bench step only after complete readback and measured safe simulator conditions',
            'otp_write': False}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile', type=Path, default=Path(__file__).with_name('profile.json'))
    ap.add_argument('--readback', type=Path)
    ap.add_argument('--ram-plan', type=Path)
    ap.add_argument('--factory-capture', type=Path)
    ap.add_argument('--unit-profile', type=Path)
    ap.add_argument('--c-profile', type=Path)
    args = ap.parse_args()
    profile = json.loads(args.profile.read_text())
    try:
        check_profile(profile)
        if args.factory_capture:
            if not args.unit_profile:
                raise ProfileError('--unit-profile is required with --factory-capture')
            profile = prepare_unit_profile(profile, json.loads(args.factory_capture.read_text()))
            args.unit_profile.write_text(json.dumps(profile, indent=2) + '\n')
        if args.readback:
            verify_readback(profile, json.loads(args.readback.read_text()))
        if args.ram_plan:
            args.ram_plan.write_text(json.dumps(ram_plan(profile), indent=2) + '\n')
        if args.c_profile:
            args.c_profile.write_text(c_profile(profile))
    except ProfileError as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc), 'device_writes': 0}))
        return 2
    print(json.dumps({'status': 'checked', 'device_writes': 0}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
