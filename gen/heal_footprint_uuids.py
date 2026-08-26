#!/usr/bin/env python3
"""Heal duplicated PCB object UUIDs deterministically (2026-08-26 audit).

Library-sourced footprint children (pads, graphics, hidden properties) were
serialized with the shared library UUIDs, so hundreds of footprints carried
identical object identities; inserted properties additionally collided by
name/value.  This one-pass healer rewrites every child UUID inside each
top-level footprint to ``uuid5(UUID_NS, "fp-child:<ref>:<ordinal>")`` while
keeping the footprint's own top-level ``(uuid footprint:<ref>)`` untouched.
Positions, pads, nets, and non-footprint objects are not modified.
"""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync_main_pcb_from_netlist as sync

UUID_RE = re.compile(r'\(uuid\s+"([^"]+)"\)')


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        raise SystemExit("usage: heal_footprint_uuids.py BOARD")
    board = Path(argv[0])
    text = board.read_text(encoding="utf-8")

    rewritten = []
    last_end = 0
    changed = 0
    for start, end, block in sync.iter_blocks(text, "(footprint"):
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if ref_match is None:
            raise SystemExit("footprint without Reference property")
        reference = ref_match.group(1)

        child_index = 0
        out_parts: list[str] = []
        pos = 0
        for match in UUID_RE.finditer(block):
            span_start, span_end = match.span()
            # The first UUID line inside a footprint is its own identity,
            # already set to footprint:<ref> by the audited sync toolchain.
            if child_index == 0:
                child_index += 1
                continue
            new_id = sync.stable_uuid(f"fp-child:{reference}:{child_index}")
            child_index += 1
            out_parts.append(block[pos:span_start])
            out_parts.append(f'(uuid "{new_id}")')
            pos = span_end
        out_parts.append(block[pos:])
        new_block = "".join(out_parts)

        rewritten.append(text[last_end:start])
        rewritten.append(new_block)
        changed += child_index - 1
        last_end = end

    rewritten.append(text[last_end:])
    board.write_text("".join(rewritten), encoding="utf-8")
    print(f"healed {changed} child UUID occurrences in {board.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
