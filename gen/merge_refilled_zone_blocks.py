#!/usr/bin/env python3
"""Merge refilled KiCad zone blocks into an otherwise untouched PCB candidate.

KiCad's refill/save command can reserialize unrelated footprint blocks.  This
candidate-only helper accepts that output only as a source of refilled top-level
zone blocks, then inserts those blocks into the exact pre-refill board text. It
refuses an overwrite and proves the result has no non-zone text changes.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import sync_main_pcb_from_netlist as sync


def zone_blocks(text: str) -> list[tuple[int, int, str]]:
    return list(sync.iter_blocks(text, "\n\t(zone"))


def signature(block: str) -> tuple[str, str, str]:
    net = sync.extract(r'\(net(?:\s+\d+)?\s+"([^"]*)"\)', block)
    layers = sync.extract(r'\(layers?\s+([^\)]*)\)', block)
    item_uuid = sync.extract(r'\(uuid\s+"([^"]+)"\)', block)
    if net is None or not layers or not item_uuid:
        raise RuntimeError("zone block has no net, layer, or UUID declaration")
    kind = "keepout" if "(keepout " in block else "copper"
    return kind, item_uuid, layers


def without_zones(text: str) -> str:
    result = text
    for start, end, _block in reversed(zone_blocks(result)):
        result = result[:start] + result[end:]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--refilled", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    before_path = args.before.resolve()
    refilled_path = args.refilled.resolve()
    output_path = args.output.resolve()
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {output_path}")

    before = before_path.read_text(encoding="utf-8")
    refilled = refilled_path.read_text(encoding="utf-8")
    before_zones = zone_blocks(before)
    refilled_zones = zone_blocks(refilled)
    if len(before_zones) != len(refilled_zones):
        raise RuntimeError(
            f"zone count changed: {len(before_zones)} -> {len(refilled_zones)}"
        )
    before_signatures = [signature(block) for _start, _end, block in before_zones]
    refilled_signatures = [signature(block) for _start, _end, block in refilled_zones]
    if before_signatures != refilled_signatures:
        raise RuntimeError("zone identity or ordering changed during refill")

    merged = before
    for (start, end, _old), (_refill_start, _refill_end, new) in zip(
        reversed(before_zones), reversed(refilled_zones)
    ):
        merged = merged[:start] + new + merged[end:]
    if without_zones(merged) != without_zones(before):
        raise RuntimeError("zone merge changed non-zone PCB text")
    output_path.write_text(merged, encoding="utf-8")
    print(f"Merged {len(before_zones)} zone blocks into {output_path}")
    print("Non-zone PCB text: byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
