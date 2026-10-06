#!/usr/bin/env python3
"""Explain only verified ERC warnings; every error and unknown warning fails."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import genlib
from check_release_candidate import top_level_blocks
from verify_electrical_calculations import component_values
from verify_layout_reviews import fingerprint

ROOT = Path(__file__).resolve().parents[1]
QUOTED = r'"(?:[^"\\]|\\.)*"'
GROUNDED_PD_PINS = {'5', '6', '7', '13', '19', '27'}


def property_value(block, name):
    m = re.search(r'\(property\s+' + re.escape(json.dumps(name)) + r'\s+(' + QUOTED + ')', block)
    return json.loads(m[1]) if m else None


def object_uuid(block):
    value = next(top_level_blocks(block, '(uuid'), '')
    m = re.fullmatch(r'\(uuid\s+"?([^"\s)]+)"?\)', value)
    return m[1] if m else None


class SchematicIndex:
    def __init__(self, schematic):
        self.symbols = {}
        self.pins = {}
        self.files = {}
        self._read(Path(schematic).resolve(), set())

    def _read(self, path, seen):
        if path in seen:
            raise ValueError('repeated schematic hierarchy: ' + path.name)
        seen.add(path)
        text = path.read_text()
        self.files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = next(top_level_blocks(text, '(lib_symbols'), '')
        templates = {json.loads(re.match(r'\(symbol\s+(' + QUOTED + ')', b)[1]): b
                     for b in top_level_blocks(cached, '(symbol')}
        for block in top_level_blocks(text, '(symbol'):
            m = re.search(r'\(lib_id\s+(' + QUOTED + r')\)', block)
            if not m:
                continue
            ident = object_uuid(block)
            lib_id = json.loads(m[1])
            row = {'ref': property_value(block, 'Reference'), 'lib_id': lib_id,
                   'template': templates[lib_id], 'file': path.name}
            if not ident or ident in self.symbols:
                raise ValueError('missing or duplicate symbol UUID')
            self.symbols[ident] = row
            for pin in top_level_blocks(block, '(pin'):
                pm = re.match(r'\(pin\s+(' + QUOTED + ')', pin)
                if pm:
                    pin_id = object_uuid(pin)
                    if not pin_id or pin_id in self.pins:
                        raise ValueError('missing or duplicate pin UUID')
                    self.pins[pin_id] = (row, json.loads(pm[1]))
        for sheet in top_level_blocks(text, '(sheet'):
            if not re.match(r'\(sheet\s', sheet):
                continue
            filename = property_value(sheet, 'Sheetfile')
            if filename is None:
                filename = property_value(sheet, 'Sheet file')
            if filename is None:
                raise ValueError('sheet has no source file')
            self._read((path.parent / filename).resolve(), seen)


def pd_configuration_valid():
    source = ROOT / 'firmware/tps25751a/verify_config.py'
    spec = importlib.util.spec_from_file_location('ducktop2_pd_erc_check', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return not module.verify_release(require_generated=True)


def classify(items, index, values, board, records=None, pd_check=pd_configuration_valid):
    if board not in ('center', 'left', 'right'):
        raise ValueError('unknown board')
    if records is None:
        records = json.loads((ROOT / 'verification/erc-symbols.json').read_text())['symbols']
    accepted, unexpected = [], []
    references = {}
    pd_ok = None

    def library_warning(item):
        children = item.get('items', [])
        if len(children) != 1:
            return None
        row = index.symbols.get(children[0].get('uuid'))
        if row is None or row['lib_id'] not in records:
            return None
        lib, name = row['lib_id'].split(':', 1)
        if item['description'] != f"Symbol '{name}' doesn't match copy in library '{lib}'" or \
                children[0]['description'] != f"Symbol {row['ref']} [{name}]":
            return None
        if row['lib_id'] not in references:
            record = records[row['lib_id']]
            library = Path(genlib.symbol_file_for(lib, name))
            fresh = genlib.load_renamed_symbol(name)[1]
            good = (hashlib.sha256(library.read_bytes()).hexdigest() == record['stock_library_sha256'] and
                    fingerprint(fresh) == record['generated_symbol_sha256'])
            references[row['lib_id']] = fingerprint(fresh) if good else None
        if references[row['lib_id']] != fingerprint(row['template']):
            return None
        return {'kind': 'verified_symbol_template', 'ref': row['ref'],
                'symbol': row['lib_id'], 'reason': records[row['lib_id']]['reason']}

    def ground_warning(item):
        nonlocal pd_ok
        if item.get('description') != 'Pins of type Bidirectional and Power output are connected':
            return None
        children = item.get('items', [])
        if len(children) != 2:
            return None
        resolved = []
        for child in children:
            pin = index.pins.get(child.get('uuid'))
            m = re.match(r'Symbol (\S+) Pin (\S+) \[', child.get('description', ''))
            if pin is None or not m or (pin[0]['ref'], pin[1]) != (m[1], m[2]):
                return None
            resolved.append(pin)
        flags = [r for r in resolved if r[0]['lib_id'] == 'power:PWR_FLAG' and r[1] == '1']
        targets = [r for r in resolved if r not in flags]
        if len(flags) != 1 or len(targets) != 1:
            return None
        if genlib.parse_pins(flags[0][0]['template']).get('1', {}).get('type') != 'power_out':
            return None
        symbol, pin = targets[0]
        ref = symbol['ref']
        if (values.pins.get(ref, {}).get(pin) != 'GND' or
                genlib.parse_pins(symbol['template']).get(pin, {}).get('type') != 'bidirectional'):
            return None
        expected_pd = {'left': 'U41', 'right': 'U42'}.get(board)
        if (ref == expected_pd and pin in GROUNDED_PD_PINS and values.mpn(ref) == 'TPS25751ADREFR'
                and symbol['lib_id'] == 'TPS25751AD:TPS25751AD'):
            if pd_ok is None:
                pd_ok = bool(pd_check())
            if pd_ok:
                return {'kind': 'unused_pd_gpio_ground', 'ref': ref, 'pin': pin,
                        'reason': 'TI ground recommendation and exact exported GPIO configuration checked'}
        if (board == 'left' and ref == 'U2000' and pin == '22' and values.mpn(ref) == 'TUSB1142IRNQR'
                and symbol['lib_id'] == 'TUSB1142:TUSB1142'):
            mode = '/PD1 Dual-Role/PD1_MUX_MODE'
            if (values.pins[ref].get('17') == mode and
                    values.pins.get('R2008') == {'1': mode, '2': 'GND'} and
                    values.mpn('R2008') == 'RC0603FR-071KL' and values.number('R2008') == 1000):
                return {'kind': 'redriver_aeq_ground_strap', 'ref': ref, 'pin': pin,
                        'reason': '1k MODE low selects pin-strap mode; AEQENZ low enables adaptive equalization'}
        return None

    for item in items:
        # Never turn an electrical error into a warning through an allowlist.
        reason = None
        if item.get('severity') == 'warning':
            if item.get('type') == 'lib_symbol_mismatch':
                reason = library_warning(item)
            elif item.get('type') == 'pin_to_pin':
                reason = ground_warning(item)
        if reason is None:
            unexpected.append(item)
        else:
            accepted.append(reason)
    return {'passed': not unexpected, 'accepted': accepted, 'unexpected': unexpected,
            'counts': dict(Counter(r['kind'] for r in accepted))}


def report_items(path):
    report = json.loads(Path(path).read_text())
    return [item for sheet in report['sheets'] for item in sheet['violations']]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', choices=('center', 'left', 'right'), required=True)
    ap.add_argument('--schematic', type=Path, required=True)
    ap.add_argument('--netlist', type=Path, required=True)
    ap.add_argument('--erc', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    index = SchematicIndex(args.schematic)
    result = classify(report_items(args.erc), index, component_values(args.netlist), args.board)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'board': args.board, 'passed': result['passed'],
                      'classified': result['counts'], 'unexpected': len(result['unexpected'])}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
