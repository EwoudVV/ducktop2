"""Match reviewed layout advisories to exact saved objects and libraries."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

import sync_main_pcb_from_netlist as pcb_text

ROOT = Path(__file__).resolve().parents[1]
REVIEW_TYPES = {'lib_footprint_mismatch', 'footprint_type_mismatch', 'footprint_filters_mismatch'}
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')
NUMBER = re.compile(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?')


@dataclass(frozen=True)
class SavedFootprint:
    ref: str
    footprint: str
    text: str


def placed_footprints(text):
    for start, end in pcb_text.top_level_child_spans(text, 'footprint'):
        block = text[start:end]
        yield SavedFootprint(
            pcb_text.extract(r'\(property\s+"Reference"\s+"([^"]*)"', block),
            pcb_text.extract(r'^\(footprint\s+"([^"]+)"', block), block)


def fingerprint(text):
    tokens = []
    for token in TOKEN.findall(text):
        if NUMBER.fullmatch(token):
            value = Decimal(token)
            token = '0' if not value else format(value.normalize(), 'f')
        tokens.append(token)
    return hashlib.sha256('\x1f'.join(tokens).encode()).hexdigest()


def footprint_uuid(footprint):
    span = pcb_text.top_level_child_span(footprint.text, 'uuid')
    if span is None:
        return ''
    return pcb_text.extract(r'\(uuid\s+"([^"]+)"\)', footprint.text[span[0]:span[1]])


def library_file(library_id, root=ROOT):
    library, name = library_id.split(':', 1)
    if any(Path(value).name != value or value in {'.', '..'} for value in (library, name)):
        raise ValueError('invalid footprint library identifier')
    locations = [root]
    locations += [Path(value) for value in
                  (os.environ.get('KICAD10_FOOTPRINT_DIR'), os.environ.get('KICAD_FOOTPRINT_DIR')) if value]
    locations += [Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'),
                  Path('/usr/share/kicad/footprints'), Path('/usr/local/share/kicad/footprints')]
    for location in locations:
        path = location / (library + '.pretty') / (name + '.kicad_mod')
        if path.is_file():
            return path
    raise FileNotFoundError(library_id)


def reviewed_violations(board_name, pcb, section, violations, *, root=ROOT,
                        stage='fabrication', routing_complete_required=True):
    database = root / 'verification/layout-reviews.json'
    result = {'accepted': [], 'stale': []}
    if not database.exists():
        return result
    data = json.loads(database.read_text())
    if data.get('version') != 1 or not isinstance(data.get('reviews'), list):
        raise ValueError('invalid footprint review record')
    records = [row for row in data['reviews'] if row['board'] == board_name and row['section'] == section]
    text = Path(pcb).read_text()
    footprints = defaultdict(list)
    for footprint in placed_footprints(text):
        footprints[footprint_uuid(footprint)].append(footprint)
    vias = defaultdict(list)
    for start, end in pcb_text.top_level_child_spans(text, 'via'):
        block = text[start:end]
        uuid = pcb_text.extract(r'\(uuid\s+"([^"]+)"\)', block)
        vias[uuid].append(block)
    for violation in violations:
        items = violation.get('items', [])
        pending_via = (violation.get('type') == 'via_dangling' and section == 'drc'
                       and stage == 'routing' and not routing_complete_required)
        if violation.get('severity') != 'warning' or len(items) != 1 \
                or (violation.get('type') not in REVIEW_TYPES and not pending_via):
            continue
        matches = [row for row in records if row['type'] == violation['type']
                   and row['severity'] == violation['severity']
                   and row['description'] == violation['description']
                   and row['item_uuid'] == items[0].get('uuid')]
        if len(matches) != 1:
            continue
        record = matches[0]
        if pending_via:
            candidates = vias.get(record['item_uuid'], [])
            if record.get('kind') == 'via' and record.get('stage') == 'routing' \
                    and len(candidates) == 1 and fingerprint(candidates[0]) == record['item_sha256'] \
                    and items[0].get('description') == record['item_description']:
                result['accepted'].append(violation)
            else:
                result['stale'].append(record['item_uuid'] + ': unfinished via changed')
            continue
        if record.get('kind') != 'footprint':
            continue
        candidates = footprints.get(record['item_uuid'], [])
        if len(candidates) != 1:
            result['stale'].append(record['reference'] + ': footprint identity changed')
            continue
        footprint = candidates[0]
        if footprint.ref != record['reference'] or footprint.footprint != record['footprint_id'] \
                or items[0].get('description') != 'Footprint ' + footprint.ref \
                or fingerprint(footprint.text) != record['item_sha256']:
            result['stale'].append(record['reference'] + ': placed definition changed')
            continue
        try:
            digest = hashlib.sha256(library_file(footprint.footprint, root).read_bytes()).hexdigest()
        except (OSError, ValueError):
            digest = None
        if digest != record['library_sha256']:
            result['stale'].append(record['reference'] + ': library changed or unavailable')
            continue
        result['accepted'].append(violation)
    return result
