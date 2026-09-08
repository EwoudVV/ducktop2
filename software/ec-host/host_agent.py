#!/usr/bin/env python3
"""Apply measured board-profile limits, then acknowledge them to the EC."""
import argparse
import fcntl
import json
from pathlib import Path
import select
import struct
import time

MAGIC = b'DT2\x01'
SIZE = 64

def decode_report(data):
    if len(data) != SIZE or data[:4] != MAGIC:
        raise ValueError('invalid EC report')
    return {'generation': struct.unpack_from('<I', data, 4)[0],
            'valid': struct.unpack_from('<H', data, 8)[0],
            'flags': struct.unpack_from('<H', data, 10)[0],
            'budget_mw': struct.unpack_from('<I', data, 36)[0],
            'acknowledged_generation': struct.unpack_from('<I', data, 40)[0],
            'usb_applied_mask': data[52], 'usb_denied_mask': data[53],
            'usb_phase': data[54], 'pd_roles': data[55],
            'usb_current_upper_ma': struct.unpack_from('<H', data, 56)[0],
            'usb_voltage_mv': struct.unpack_from('<H', data, 58)[0],
            'usb_reservation_mw': struct.unpack_from('<I', data, 60)[0]}

def encode_ack(report, applied_mw, aux_mw, requests, usb_ports=0):
    if not 0 <= requests <= 255 or not 0 <= usb_ports <= 127:
        raise ValueError('unknown request or USB port bit')
    if not 0 < applied_mw <= report['budget_mw'] or not 0 <= aux_mw <= 100000:
        raise ValueError('acknowledgement exceeds EC budget')
    packet = bytearray(SIZE)
    packet[:4] = MAGIC
    # Conservatively report the full applied ceiling, not CPU-only energy.
    struct.pack_into('<6I', packet, 4, report['generation'], applied_mw,
                     applied_mw, aux_mw, requests, 1500)
    packet[28] = usb_ports
    return packet

def write_verify(path, value, exact=False):
    path = Path(path)
    path.write_text(str(value))
    observed = int(path.read_text().strip())
    if observed < 0 or observed > value or (exact and observed != value):
        raise RuntimeError(f'{path}: limit readback {observed} exceeds {value}')
    return observed

def apply_limits(profile, requested_mw, lid_closed):
    if not profile.get('qualified') or not profile.get('evidence'):
        raise ValueError('board power profile has not been qualified')
    reserve = profile['mu_non_package_mw'] + profile['display_max_mw']
    package_mw = min(profile['package_max_mw'], requested_mw - reserve)
    if package_mw < profile['package_min_mw']:
        raise ValueError('source cannot support the qualified minimum')
    powercap = Path(profile['powercap_path'])
    constraints = {}
    for name in powercap.glob('constraint_*_name'):
        constraints[name.read_text().strip()] = name.name.removesuffix('_name')
    if not {'long_term', 'short_term'} <= constraints.keys():
        raise ValueError('both RAPL package constraints are required')
    for kind in ('short_term', 'long_term'):
        prefix = constraints[kind]
        write_verify(powercap / (prefix + '_power_limit_uw'), package_mw * 1000)
    write_verify(powercap / 'enabled', 1, exact=True)
    if int((powercap / 'enabled').read_text()) != 1:
        raise RuntimeError('RAPL was not enabled')
    # Profile includes worst-case display demand even while its backlight is off.
    backlight = Path(profile['backlight_path'])
    maximum = int((backlight / 'max_brightness').read_text())
    ceiling = min(maximum, profile['brightness_ceiling'])
    current = int((backlight / 'brightness').read_text())
    if current > ceiling:
        write_verify(backlight / 'brightness', ceiling)
    if (backlight / 'bl_power').exists():
        write_verify(backlight / 'bl_power', 4 if lid_closed else 0, exact=True)
    else:
        raise ValueError('backlight has no bl_power control; lid policy cannot be applied')
    return package_mw + reserve

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hidraw', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--requests', type=lambda x: int(x, 0), default=0)
    parser.add_argument('--usb-ports', type=lambda x: int(x, 0), default=0,
                        help='permission mask: J21 J11 J22 J23 J12 J24 J25, bits 0 to 6')
    parser.add_argument('--clear-usb-fault', action='store_true')
    args = parser.parse_args()
    profile = json.loads(Path(args.profile).read_text())
    if not profile.get('qualified'):
        raise SystemExit('profile is unqualified; no power acknowledgement sent')
    if args.requests & ~127 or not 0 <= args.usb_ports <= 127:
        raise SystemExit('unknown request bit')
    clear_pending = args.clear_usb_fault
    with open(args.hidraw, 'r+b', buffering=0) as device:
        while True:
            if not select.select([device], [], [], 1)[0]:
                continue
            report = decode_report(device.read(SIZE))
            try:
                applied = apply_limits(profile, report['budget_mw'], bool(report['flags'] & 2))
                packet = encode_ack(report, applied, profile['aux_worst_case_mw'],
                                    args.requests | (128 if clear_pending else 0), args.usb_ports)
                # HIDIOCSFEATURE(65): unnumbered report ID byte precedes payload.
                fcntl.ioctl(device, 0xC0000000 | (65 << 16) | (ord('H') << 8) | 0x06,
                            b'\x00' + packet)
                clear_pending = False
            except (OSError, ValueError, RuntimeError) as error:
                print(f'power acknowledgement withheld: {error}', flush=True)
            time.sleep(0.1)

if __name__ == '__main__':
    main()
