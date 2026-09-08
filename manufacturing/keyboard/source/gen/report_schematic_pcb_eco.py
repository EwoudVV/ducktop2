#!/usr/bin/env python3
"""Compare a current PCB with a fresh schematic netlist, without editing it."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from check_release_candidate import find_kicad_cli, top_level_blocks, native_board_stats

ROOT = Path(__file__).resolve().parents[1]
from board_release_contract import BOARD_PROJECTS
PROJECTS = {name:(item['pcb'],item['schematic']) for name,item in BOARD_PROJECTS.items()}
QUOTED = r'"(?:[^"\\]|\\.)*"'


def unquote(value: str) -> str:
    return json.loads(value)


def field(block: str, name: str) -> str:
    match = re.search(r'\(property\s+' + re.escape(json.dumps(name)) + r'\s+(' + QUOTED + ')', block)
    return unquote(match[1]) if match else ''


def normalize_net(name: str | None) -> str | None:
    return None if not name or name.startswith('unconnected-') else name


def parse_board(text: str) -> list[dict]:
    result = []
    for block in top_level_blocks(text, '(footprint'):
        fp = re.match(r'\(footprint\s+(' + QUOTED + ')', block)
        attributes = list(top_level_blocks(block, '(attr'))
        pads = []
        for pad in top_level_blocks(block, '(pad'):
            header = re.match(r'\(pad\s+(' + QUOTED + r')\s+(\w+)', pad)
            layers = next(top_level_blocks(pad, '(layers'), '')
            if header[2] == 'np_thru_hole' or not re.search(r'"[^" ]*\.Cu"', layers):
                continue
            net = re.search(r'\(net(?:\s+\d+)?\s+(' + QUOTED + ')', pad)
            uid = re.search(r'\(uuid\s+(' + QUOTED + ')', pad)
            raw_net = normalize_net(unquote(net[1]) if net else None)
            # KiCad escapes a slash within a sheet name; XML displays it as '/'.
            # Retain the raw name below so distinct board nets still fail as a split.
            display_net = raw_net.replace('{slash}', '/') if raw_net else None
            pads.append({'pin':unquote(header[1]), 'net':display_net, 'raw_net':raw_net,
                         'uuid':unquote(uid[1]) if uid else ''})
        result.append({'ref':field(block, 'Reference'), 'value':field(block, 'Value'),
                       'footprint':unquote(fp[1]), 'pads':pads,
                       'attributes':set(re.findall(r'\b(?:dnp|exclude_from_bom)\b', ' '.join(attributes)))})
    return result


def parse_schematic(root: ET.Element) -> list[dict]:
    pin_sets = {}
    for part in root.findall('./libparts/libpart'):
        pin_sets[(part.get('lib'), part.get('part'))] = {p.get('num') for p in part.findall('./pins/pin')}
    components = []
    for comp in root.findall('./components/comp'):
        props = {p.get('name'):p.get('value') for p in comp.findall('property')}
        if 'exclude_from_board' in props:
            continue
        source = comp.find('libsource')
        pins = pin_sets.get((source.get('lib'), source.get('part')), set()) if source is not None else set()
        components.append({'ref':comp.get('ref'), 'value':comp.findtext('value') or '',
                           'footprint':comp.findtext('footprint') or '', 'pin_nets':dict.fromkeys(pins),
                           'attributes':{p for p in ('dnp','exclude_from_bom') if p in props},
                           'fields':{f.get('name'):f.text or '' for f in comp.findall('./fields/field')}})
    by_ref = {c['ref']:c for c in components}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            if node.get('ref') in by_ref:
                by_ref[node.get('ref')]['pin_nets'][node.get('pin')] = normalize_net(net.get('name'))
    return components


def compare(board_text: str, netlist_root: ET.Element, *, standalone_root_prefix: bool = False) -> dict:
    board_rows = parse_board(board_text);sch_rows = parse_schematic(netlist_root)
    board = {c['ref']:c for c in board_rows};schematic = {c['ref']:c for c in sch_rows}
    duplicate = lambda rows: sorted(ref for ref,n in Counter(c['ref'] for c in rows).items() if n>1)
    result = {'duplicate_board_refs':duplicate(board_rows), 'duplicate_schematic_refs':duplicate(sch_rows),
              'missing_components':sorted(schematic.keys()-board.keys()),
              'extra_components':sorted(board.keys()-schematic.keys()), 'footprint_changes':[],
              'value_changes':[], 'attribute_changes':[], 'pad_net_changes':[],
              'missing_pin_pads':[], 'unexpected_pads':[], 'combined_drain_pins':[]}
    expected_to_actual = defaultdict(set);actual_to_expected = defaultdict(set);checked = 0
    for ref in sorted(board.keys() & schematic.keys()):
        actual,wanted = board[ref],schematic[ref]
        for name in ('footprint','value'):
            if actual[name] != wanted[name]:
                result[name+'_changes'].append({'ref':ref,'pcb':actual[name],'schematic':wanted[name]})
        if actual['attributes'] != wanted['attributes']:
            result['attribute_changes'].append({'ref':ref,'pcb':sorted(actual['attributes']),
                                                'schematic':sorted(wanted['attributes'])})
        physical = defaultdict(list)
        for pad in actual['pads']:physical[pad['pin']].append(pad)
        for pin,net in wanted['pin_nets'].items():
            # This TI land pattern deliberately combines the four drain leads.
            alias = '5' if (wanted['footprint']=='ducktop2:CSD18540Q5B_DNK' and pin in ('6','7','8')) else pin
            if alias != pin:
                if net != wanted['pin_nets'].get('5'):
                    result['missing_pin_pads'].append({'ref':ref,'pin':pin,'reason':'combined drain nets differ'})
                    continue
                result['combined_drain_pins'].append({'ref':ref,'pin':pin,'physical_pad':alias})
            if alias not in physical:
                result['missing_pin_pads'].append({'ref':ref,'pin':pin})
        for pad in actual['pads']:
            pin,old = pad['pin'],pad['net']
            if pin not in wanted['pin_nets']:
                if ref.startswith('FPC') and pin in ('MP','SH'):
                    new = 'FG_VSS' if ref=='FPC106' else 'GND'
                elif not pin or re.fullmatch(r'(?:MP|MH|SH|S|H|M)\d*', pin):
                    if old is not None and not pin:
                        result['unexpected_pads'].append({'ref':ref,**pad})
                    continue
                else:
                    result['unexpected_pads'].append({'ref':ref,**pad});continue
            else:new = wanted['pin_nets'][pin]
            checked += 1
            raw_new = new
            if standalone_root_prefix:
                old=old[1:] if old and old.startswith('/') else old
                new=new[1:] if new and new.startswith('/') else new
            if old != new:
                result['pad_net_changes'].append({'ref':ref,'pin':pin,'uuid':pad['uuid'],
                    'pcb':old,'schematic':new,'xml_encoding_only':bool(old and html.unescape(old)==new)})
            if old is not None and new is not None:
                expected_to_actual[raw_new].add(pad['raw_net']);actual_to_expected[pad['raw_net']].add(raw_new)
    result['split_net_names'] = {k:sorted(v) for k,v in expected_to_actual.items() if len(v)>1}
    result['merged_net_names'] = {k:sorted(v) for k,v in actual_to_expected.items() if len(v)>1}
    result['counts'] = {k:len(v) for k,v in result.items()}
    result['counts'].update(schematic_components=len(sch_rows), board_footprints=len(board_rows),
                            physical_pads_checked=checked)
    result['passed'] = not any(result[k] for k in ('duplicate_board_refs','duplicate_schematic_refs',
        'missing_components','extra_components','footprint_changes','value_changes','attribute_changes',
        'pad_net_changes','missing_pin_pads','unexpected_pads','split_net_names','merged_net_names'))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', choices=PROJECTS, default='center')
    parser.add_argument('--all', action='store_true', help='compare all six current boards')
    parser.add_argument('--pcb', type=Path)
    parser.add_argument('--schematic', type=Path)
    parser.add_argument('--netlist', type=Path, help='use this explicit netlist instead of exporting one')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.all:
        if args.pcb or args.schematic or args.netlist:
            parser.error('--all cannot be combined with individual source overrides')
        parent=(args.output_dir or ROOT/'verification/generated/board-parity').resolve()
        results={name:main(['--project',name,'--output-dir',str(parent/name)]) for name in PROJECTS}
        (parent/'six-board-summary.json').write_text(json.dumps({'all_six_compared':True,'results':results,
            'scope':'schematic assignments and identity only; not routing or fabrication approval'},indent=2)+'\n')
        return 0 if not any(results.values()) else 1
    pcb = (args.pcb or ROOT/PROJECTS[args.project][0]).resolve()
    sch = (args.schematic or ROOT/PROJECTS[args.project][1]).resolve()
    output = (args.output_dir or ROOT/'verification/generated/board-parity'/args.project).resolve()
    output.mkdir(parents=True,exist_ok=True)
    source_paths={pcb,sch,*sch.parent.glob('*.kicad_sch')}
    before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_paths)}
    netlist = args.netlist.resolve() if args.netlist else output/'netlist.xml'
    if args.netlist is None:
        subprocess.run([find_kicad_cli(),'sch','export','netlist','--format','kicadxml',
                        '--output',str(netlist),str(sch)],cwd=sch.parent,check=True)
    result = compare(pcb.read_text(),ET.parse(netlist).getroot(),standalone_root_prefix=args.project=='keyboard')
    result['board_contract']=BOARD_PROJECTS[args.project]
    result['native_inventory']=native_board_stats(pcb)
    result['fresh_netlist_export']=args.netlist is None
    result['scope']='schematic assignments and identity; no fabrication approval'
    result['sources'] = {str(p):h for p,h in before.items()}
    result['netlist_sha256'] = hashlib.sha256(netlist.read_bytes()).hexdigest()
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in before.items()), 'design changed during review'
    (output/'parity.json').write_text(json.dumps(result,indent=2)+'\n')
    with (output/'pad-net-changes.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['ref','pin','uuid','pcb','schematic','xml_encoding_only'])
        writer.writeheader();writer.writerows(result['pad_net_changes'])
    lines=['# schematic and board comparison','',f'board: `{pcb.relative_to(ROOT) if pcb.is_relative_to(ROOT) else pcb}`',
           '',f'result: {"pass" if result["passed"] else "differences need review"}', '',
           '| check | count |','| --- | ---: |']
    lines += [f'| {name.replace("_"," ")} | {value} |' for name,value in result['counts'].items()]
    lines += ['', 'the JSON and CSV contain every difference, including repeated physical pads.',
              'XML-escaped PCB names are reported as differences. they are not silently accepted.',
              'a passing comparison checks assignments and component identity, not routed continuity.',
              '', 'board and schematic files were unchanged.','']
    (output/'report.md').write_text('\n'.join(lines))
    print(json.dumps({'passed':result['passed'],**result['counts']}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
