#!/usr/bin/env python3
"""Repair duplicate footprint-child IDs without replacing unique object IDs."""

from __future__ import annotations

import re
import sys
import uuid
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync_main_pcb_from_netlist as sync

UUID_RE = re.compile(r'\(uuid\s+"([^"]+)"\)')


def repair_duplicate_ids(text: str) -> tuple[str, list[dict]]:
    values = UUID_RE.findall(text)
    for value in values:
        uuid.UUID(value)
    duplicates = {value for value, count in Counter(values).items() if count > 1}
    if not duplicates:
        return text, []
    spans = sync.top_level_child_spans(text, 'footprint')
    outside = text
    for start, end in reversed(spans):
        outside = outside[:start] + outside[end:]
    if any('"' + value + '"' in outside for value in duplicates):
        raise ValueError('duplicate ID has a board-level object or ambiguous group reference')
    seen = set()
    changes = []
    replacements = []
    occupied = set(values)
    for start, end in spans:
        block = text[start:end]
        ref = sync.extract(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        own_span = sync.top_level_child_span(block, 'uuid')
        if not ref or own_span is None:
            raise ValueError('footprint needs a reference and its own UUID')
        own = UUID_RE.search(block[own_span[0]:own_span[1]]).group(1)
        ids = UUID_RE.findall(block)
        if own in duplicates or len(ids) != len(set(ids)):
            raise ValueError(ref + ': ambiguous duplicate inside one footprint')
        mapping = {}
        for value in ids:
            if value in seen:
                new_id = sync.stable_uuid(f'repair-child:{own}:{value}')
                if new_id in occupied:
                    raise ValueError(ref + ': replacement UUID collision')
                occupied.add(new_id)
                mapping[value] = new_id
                changes.append({'reference':ref,'old_uuid':value,'new_uuid':new_id})
            seen.add(value)
        if mapping:
            updated = re.sub(r'"([0-9a-fA-F-]{36})"',
                lambda m: '"' + mapping.get(m.group(1),m.group(1)) + '"', block)
            replacements.append((start,end,updated))
    for start,end,updated in reversed(replacements):
        text = text[:start] + updated + text[end:]
    assert len(UUID_RE.findall(text)) == len(set(UUID_RE.findall(text)))
    return text, changes


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        raise SystemExit("usage: heal_footprint_uuids.py BOARD")
    board = Path(argv[0])
    text = board.read_text(encoding="utf-8")

    rewritten, changes = repair_duplicate_ids(text)
    if changes:
        board.write_text(rewritten, encoding="utf-8")
    print(f"repaired {len(changes)} duplicate child UUIDs in {board.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
