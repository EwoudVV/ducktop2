#!/usr/bin/env python3
"""Export top-side BMS plug and withdrawal envelopes for the case layout."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
# Bounds include the mated housing. Withdrawal is a separate 5 mm planning sweep.
PARTS = {
    'J2': ([-3.95, -6.55, 3.95, 6.55], None, 4.5, [0, -1]),
    'J2072': ([-3.95, -6.55, 3.95, 6.55], None, 4.5, [0, -1]),
    'J2074': ([-4.4, -3.28, 4.4, 4.83], [-3.25, -.675, 3.25, 9.825], 3.2, [0, 1]),
    'J2200': ([-4.9, -3.28, 4.9, 4.83], [-3.75, -.675, 3.75, 9.825], 3.2, [0, 1]),
    'J2201': ([-3.48, -3.2, 3.48, 5], [-2.125, -3.2, 2.125, 10], 4.6, [0, 1]),
}


def transform(point, position, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    u, v = point
    return [round(position[0] + c*u + s*v, 6), round(position[1] - s*u + c*v, 6)]


def rectangle(bounds, position, angle):
    x0, y0, x1, y1 = bounds
    return [transform(p, position, angle) for p in [(x0,y0), (x1,y0), (x1,y1), (x0,y1)]]


def main():
    data = json.loads((ROOT/'mechanical/board-datums.json').read_text())
    board = data['boards']['bms']
    assert hashlib.sha256((ROOT/board['file']).read_bytes()).hexdigest() == board['sha256'], 'refresh board datums'
    parts = {f['reference']: f for f in board['connectors_and_supports']}
    rows = []
    for ref, (body, sweep, height, direction) in PARTS.items():
        part = parts[ref]
        assert part['side'] == 'front', ref + ' must stay on top'
        position, angle = part['position'], part['rotation']
        rows.append(dict(reference=ref, manufacturer_part_number=part['manufacturer_part_number'],
            side='top', installed_anchor_xy_mm=position, rotation_deg=angle,
            exit_direction_xy=transform(direction, [0,0], angle),
            installed_mated_polygon_mm=rectangle(body, position, angle),
            installed_withdrawal_polygon_mm=rectangle(sweep, position, angle) if sweep else None,
            reserved_height_above_pcb_mm=height,
            service=('top access to spring buttons; separate wire clamps' if sweep is None else
                     '5 mm axial housing withdrawal; finger, latch and wire space additional')))
    out = dict(units='mm', coordinates='installed board XY, viewed from above',
        board=board['file'], board_sha256=board['sha256'], connectors=rows,
        dimensions='manufacturer reference dimensions with planning allowances; not measured plugs',
        case_fit_verified=False, clamps_fitted=False,
        notes=['remove the bridge above the BMS before releasing wires or plugs',
               'support the board independently of the cable clamps',
               'withdrawal can pass above the adjacent main board; include its parts and fasteners in the Z check',
               'the 8 mm main-board and 12 mm BMS top surfaces are study positions, not fixed case requirements'],
        sources=['https://www.jst-mfg.com/product/pdf/eng/eSH.pdf',
                 'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf',
                 'https://www.wago.com/2060-452/998-404'])
    (ROOT/'mechanical/bms-connector-access.json').write_text(json.dumps(out, indent=2)+'\n')
    print('exported five top-side BMS connector and withdrawal envelopes')


if __name__ == '__main__':
    main()
