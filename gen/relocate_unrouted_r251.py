#!/usr/bin/env python3
"""Create a candidate that separates the unrouted trackpad USB series resistors.

The reviewed 2026-07-27 board places R250 and R251 so that R250.1
(/TRACKPAD_USB_DP) overlaps R251.2 (/Internal Services/TPAD_CONN_DM).  This
helper is deliberately hash-locked to that board.  It moves only R251 from
(179.3, 88.6) to (180.3, 90.3), after proving that neither old R251 pad has a
track endpoint.  Run a zone refill only in a copied project after this helper;
the resulting refilled zones must be merged back with merge_refilled_zone_blocks.py.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from sync_main_pcb_from_netlist import at_tuple, footprints, top_level_child_spans


EXPECTED_INPUT_SHA256 = "e1b4f590c8ee18abc3f8849530292c0c808833ee830b017f976ba5acd1a70dc9"
REFERENCE = "R251"
OLD_AT = (179.3, 88.6, 0.0)
NEW_AT = (180.3, 90.3, 0.0)
OLD_PAD_CENTERS = ((178.475, 88.6), (180.125, 88.6))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close_enough(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return all(abs(a - b) < 0.0001 for a, b in zip(left, right))


def has_track_endpoint(board_text: str, point: tuple[float, float]) -> bool:
    endpoint_re = re.compile(
        r"\((?:start|end)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)"
    )
    for start, end in top_level_child_spans(board_text, "segment"):
        for x_text, y_text in endpoint_re.findall(board_text[start:end]):
            if close_enough((float(x_text), float(y_text)), point):
                return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="immutable reviewed PCB")
    parser.add_argument("--output", type=Path, required=True, help="new candidate PCB")
    args = parser.parse_args(argv)

    source = args.input.resolve()
    output = args.output.resolve()
    if source == output:
        raise RuntimeError("input and output must be different files")
    if output.exists():
        raise FileExistsError(output)
    if sha256(source) != EXPECTED_INPUT_SHA256:
        raise RuntimeError("input PCB hash does not match the reviewed R251 baseline")

    board_text = source.read_text(encoding="utf-8")
    candidates = [item for item in footprints(board_text) if item.ref == REFERENCE]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one {REFERENCE} footprint, found {len(candidates)}")
    footprint = candidates[0]
    if not close_enough(at_tuple(footprint.text), OLD_AT):
        raise RuntimeError(f"{REFERENCE} is not at the reviewed source location")
    attached = [point for point in OLD_PAD_CENTERS if has_track_endpoint(board_text, point)]
    if attached:
        raise RuntimeError(f"{REFERENCE} has routing attached at {attached}; do not move it")

    moved = re.sub(
        r"^\s*\(at\s+179\.3\s+88\.6\)",
        "\t\t(at 180.3 90.3)",
        footprint.text,
        count=1,
        flags=re.MULTILINE,
    )
    if moved == footprint.text:
        raise RuntimeError(f"could not update {REFERENCE} top-level placement")
    candidate = board_text[:footprint.start] + moved + board_text[footprint.end:]
    output.write_text(candidate, encoding="utf-8")
    print(f"wrote {output}")
    print(f"moved {REFERENCE}: {OLD_AT} -> {NEW_AT}")
    print("attached segment endpoints: 0")
    print(f"output_sha256={sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
