#!/usr/bin/env python3
"""Check keyboard RGB pin mapping and placement using KiCad's native Python."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from keyboard_rgb_contract import COPPER_LAYERS, DRIVER_PINS, ISET_OHMS, LED_MPN, DRIVER_MPN, BUFFER_MPN, key_assignments, led_nets
from report_schematic_pcb_eco import compare, parse_schematic

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board', type=Path, default=ROOT/'keyboard/12_keyboard_daughterboard.kicad_pcb')
    parser.add_argument('--netlist', type=Path, required=True, help='fresh KiCad XML netlist')
    parser.add_argument('--baseline', type=Path, help='optional PCB before the RGB changes')
    parser.add_argument('--expect-unrouted', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--key-map', type=Path)
    parser.add_argument('--drc', type=Path, help='fresh native DRC JSON for this board')
    parser.add_argument('--erc', type=Path, help='fresh schematic ERC JSON')
    args = parser.parse_args()
    import wx
    app = wx.App(False)
    wx.Log.EnableLogging(False)
    import pcbnew as p
    board = p.LoadBoard(str(args.board))
    board.BuildConnectivity()
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    require(len(fps) == 221, 'expected 221 footprints, including six test pads')
    require(board.GetCopperLayerCount() == COPPER_LAYERS, 'keyboard must have four copper layers')
    require(board.GetLayerType(p.In1_Cu) == p.LT_POWER, 'In1.Cu must remain the ground-plane layer')
    require(board.GetDesignSettings().GetBoardThickness() == 800000, 'keyboard must stay 0.8 mm')
    xml = ET.parse(args.netlist).getroot()
    parity = compare(args.board.read_text(), xml, standalone_root_prefix=True)
    require(parity['passed'], 'schematic and PCB differ: '+str(parity['counts']))
    components = {c['ref']: c for c in parse_schematic(xml)}
    for ref, c in components.items():
        if not ref.startswith('TPK'):
            require(c['fields'].get('MPN') and c['fields'].get('Manufacturer'), ref+' needs an orderable part')
            for field in ('MPN', 'Manufacturer'):
                require(fps[ref].GetField(field).GetText() == c['fields'][field], ref+' PCB part fields differ')

    def pose(f):
        return (f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees(), f.GetLayer())

    def nets(ref):
        return {pad.GetNumber(): pad.GetNetname() for pad in fps[ref].Pads() if pad.GetNumber()}

    def point(v):
        return (v.x/1e6, v.y/1e6)

    def edge_signature(b):
        return sorted((str(g.GetShape()), point(g.GetStart()), point(g.GetEnd()), g.GetWidth())
                      for g in b.GetDrawings() if g.GetLayer() == p.Edge_Cuts)

    if args.baseline:
        baseline = p.LoadBoard(str(args.baseline))
        require(edge_signature(board) == edge_signature(baseline), 'board outline changed')
        for old in baseline.GetFootprints():
            ref = old.GetReference()
            require(ref in fps and pose(old) == pose(fps[ref]), ref+' moved from the original layout')

    mapping = key_assignments()
    require(components['U320']['fields']['MPN'] == DRIVER_MPN and
            components['U321']['fields']['MPN'] == BUFFER_MPN, 'driver or buffer part changed')
    rows = []
    keepouts = 0
    # CHERRY VS-10107 rev 03 uses this switch-local auxiliary component area.
    cavity = (-3.6, -4.2, 3.1, -1.8)
    pad_margin = 100.0
    for index in range(65):
        sw, led = fps[f'SW{320+index}'], fps[f'LED{320+index}']
        require(components[led.GetReference()]['fields']['MPN'] == LED_MPN, 'LED fit check needs the specified Everlight part')
        sx, sy = point(sw.GetPosition())
        lx, ly = point(led.GetPosition())
        require(sw.GetOrientationDegrees() == led.GetOrientationDegrees() == 0, 'unexpected key rotation')
        require(abs(lx-sx) < 1e-6 and abs(ly-sy+2.8) < 1e-6, led.GetReference()+' is outside the light opening')
        require(sw.IsLocked() and led.IsLocked(), 'key and LED locations must be locked')
        require(led.GetLayer() == p.F_Cu, 'LED must face the switch')
        require(nets(led.GetReference()) == led_nets(index), led.GetReference()+' RGB pin mapping differs')
        # Include the LED body's stated +/-0.1 mm dimensional tolerance.
        require(cavity[0] <= -.85 and .85 <= cavity[2] and cavity[1] <= -3.65 and -1.95 <= cavity[3], 'LED body does not fit')
        for pad in led.Pads():
            x, y = point(pad.GetPosition()); w, h = point(pad.GetSize())
            margins = (x-sx-w/2-cavity[0], y-sy-h/2-cavity[1],
                       cavity[2]-(x-sx+w/2), cavity[3]-(y-sy+h/2))
            require(min(margins) >= -1e-6, led.GetReference()+' pad outside allowed area')
            pad_margin = min(pad_margin, *margins)
        zones = list(sw.Zones())
        require(len(zones) == 1, sw.GetReference()+' needs its copper keepout')
        z = zones[0]
        require(z.GetIsRuleArea() and set(z.GetLayerSet().Seq()) == {p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu}, 'keepouts must cover all four copper layers')
        require(all((z.GetDoNotAllowTracks(),z.GetDoNotAllowVias(),z.GetDoNotAllowPads(),z.GetDoNotAllowZoneFills())), 'keepout no longer blocks all copper')
        line = z.Outline().COutline(0)
        local = {(round(line.CPoint(i).x/1e6-sx,5),round(line.CPoint(i).y/1e6-sy,5)) for i in range(line.PointCount())}
        require(local == {(-5.05,2.2),(-1.25,2.2),(-1.25,4.2),(-5.05,4.2)}, sw.GetReference()+' keepout geometry changed')
        keepouts += 1
        a = mapping[index]
        rows.append({'switch':sw.GetReference(), 'led':led.GetReference(),
                     'key':sw.GetValue(), 'bank':a['bank'], 'slot':a['slot']+1,
                     'anode':led_nets(index)['1'], 'red_cathode':led_nets(index)['4'],
                     'green_cathode':led_nets(index)['6'], 'blue_cathode':led_nets(index)['2'],
                     'red_register':a['registers'][0], 'green_register':a['registers'][1],
                     'blue_register':a['registers'][2]})
    require(nets('U320') == {str(k):v or '' for k,v in DRIVER_PINS.items()}, 'driver pin mapping changed')
    require(nets('U321') == {'1':'KB_RGB_5V','2':'RGB_SCL','3':'RGB_SDA','4':'GND',
                            '5':'KB_RGB_5V','6':'I2C_SDA','7':'I2C_SCL','8':'MCU_3V3'}, 'buffer sides changed')
    connector = nets('J320')
    for pin, net in {'1':'GND','2':'MCU_3V3','3':'I2C_SCL','4':'I2C_SDA','29':'KB_RGB_5V','30':'GND',
                     '10':'','11':'','12':'','27':'','28':'','MP':''}.items():
        require(connector[pin] == net, 'J320 pin '+pin+' changed')
    for i in range(5): require(connector[str(5+i)] == f'KB_ROW{i}', 'matrix row contact changed')
    for i in range(14): require(connector[str(13+i)] == f'KB_COL{i}', 'matrix column contact changed')
    for slot in range(6):
        cs = slot*3+1
        require(nets(f'R{330+slot}') == {'1':f'RGB_CS{cs:02d}','2':f'RGB_RED{cs:02d}'}, 'red resistor mapping changed')
    require(components['R320']['fields']['MPN'] == 'RC0603FR-0733K2L', 'current-setting resistor changed')
    ep = next(pad for pad in fps['U320'].Pads() if pad.GetNumber() == '41')
    require(point(ep.GetSize()) == (3.4,3.4) and ep.GetNetname() == 'GND', 'driver exposed pad differs from the recommended land')
    registers = [r for a in mapping.values() for r in a['registers']]
    require(sorted(registers) == list(range(1,196)), 'RGB registers must cover 195 unique channels')
    header = (ROOT/'firmware/ec_target/keyboard_rgb_map.h').read_text()
    firmware_map = [[int(v) for v in m] for m in re.findall(r'\{(\d+)u, (\d+)u, (\d+)u\}', header)]
    require(firmware_map == [mapping[i]['registers'] for i in range(65)], 'firmware RGB order differs')
    tracks = len(list(board.GetTracks()))
    pours = sum(not z.GetIsRuleArea() for z in board.Zones())
    if args.expect_unrouted:
        require(tracks == pours == 0, 'placement-only board contains routing or pours')
    if args.key_map:
        with args.key_map.open('w', newline='') as f:
            writer = csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
    source_paths = (args.board, args.board.with_suffix('.kicad_pro'), args.board.with_suffix('.kicad_dru'),
                    ROOT/'keyboard/12_keyboard_daughterboard.kicad_sch', args.netlist)
    peak_ma = 36.91*10000/(ISET_OHMS*.99)
    report = {'passed':True,'stage':'placement, not fabrication',
              'footprints':len(fps),'rgb_leds':65,'copper_layers':board.GetCopperLayerCount(),'thickness_mm':.8,
              'tracks_and_vias':tracks,'copper_pours':pours,'switch_keepouts':keepouts,
              'native_unconnected':board.GetConnectivity().GetUnconnectedCount(False),
              'schematic_parity':parity['passed'],'physical_pads_checked':parity['counts']['physical_pads_checked'],
              'original_placement_and_outline_preserved':bool(args.baseline),
              'led_pad_minimum_area_margin_mm':round(pad_margin,6),
              'led_max_body_height_mm':.45,'solder_height_allowance_mm':.05,'cherry_height_limit_mm':.8,
              'sink_current_ma_at_published_corner':round(peak_ma,3),
              'eighteen_sink_total_ma_at_published_corner':round(18*peak_ma,3),
              'current_calculation_conditions':'IS31FL3743A rev C table: VCC 3.6 V, TA 25 C; 1% ISET resistor. Verify current and temperature on hardware.',
              'source_sha256':{str(x.resolve().relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in source_paths}}
    for kind, path in (('drc',args.drc),('erc',args.erc)):
        if path is None:
            continue
        checks = json.loads(path.read_text())
        violations = checks['violations'] if kind == 'drc' else [v for s in checks['sheets'] for v in s['violations']]
        require(not violations, kind.upper()+' has findings')
        report[kind+'_findings'] = len(violations)
        if kind == 'drc':
            require(not checks['schematic_parity'] and not checks['ignored_checks'], 'DRC parity findings or disabled PCB checks')
            report['drc_reported_unconnected_capped'] = len(checks['unconnected_items'])
            report['disabled_pcb_checks'] = 0
        report['source_sha256'][str(path.resolve().relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (ROOT/'gen/keyboard_rgb_contract.py',ROOT/'gen/check_keyboard_rgb.py',
                 ROOT/'gen/Keyboard_RGB.kicad_sym',ROOT/'ducktop2.pretty/LED_Everlight_19-337_1616.kicad_mod',
                 ROOT/'ducktop2.pretty/IS31FL3743A_UQFN40.kicad_mod',
                 ROOT/'firmware/ec_target/keyboard_rgb.c',ROOT/'firmware/ec_target/keyboard_rgb_map.h'):
        report['source_sha256'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))


if __name__ == '__main__':
    main()
