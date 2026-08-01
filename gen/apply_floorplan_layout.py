#!/usr/bin/env python3
"""
Apply a mechanical_layout_planner.html floorplan export to the mainboard.

The planner (mechanical_layout_planner.html) exports its state JSON.  This
script maps the floorplan part ids onto mainboard footprints, converts the
base-plane coordinates (base y = board y + 63; board front edge at base
y = 63) back to board coordinates, and moves those footprints into a
candidate board.  Only parts with an explicit mapping are applied; anything
else (battery cells, keyboard, trackpad, chassis parts) is ignored.

Usage:
  python3 gen/apply_floorplan_layout.py --floorplan floorplan.json \
      --input ducktop2.kicad_pcb --output /tmp/layout.kicad_pcb
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from analyze_placement_collisions import parse_board

BOARD_OFFSET_Y = 63.0   # base-plane y of the mainboard front edge

# Floorplan part id -> (footprint ref, board x offset, board y offset)
# Offsets place the floorplan part rectangle center on the footprint anchor.
MAPPING: dict[str, tuple[str, float, float]] = {
    "mu-module":           ("A1", 0.0, 0.0),
    "ethernet-jack":       ("J500", 0.0, 0.0),
    "usb-c-right":         ("J11", 0.0, 0.0),
    "usb-c-left-1":        ("J22", 0.0, 0.0),
    "usb-c-left-2":        ("J23", 0.0, 0.0),
    "headphone-jack":      ("J422", 0.0, 0.0),
    "battery-connector":   ("J2", 0.0, 0.0),
    "fan-connector":       ("J52", 0.0, 0.0),
    "keyboard-ffc":        ("J310", 0.0, 0.0),
    "speaker-connector":   ("J420", 0.0, 0.0),
    "trackpad-lands":      ("J58", 0.0, 0.0),
    "microphone":          ("MK430", 0.0, 0.0),
    "m2-nvme":             ("J10", 0.0, 0.0),
    "m2-wifi":             ("J40", 0.0, 0.0),
    "radio-daughterboard": ("J2300", 0.0, 0.0),
}


def move_footprint(text: str, fps: dict, ref: str, x: float, y: float) -> str:
    fp = fps[ref]
    span = fp["at_span"]
    rotation = f" {fp['at'][2]}" if len(fp["at"]) > 2 else ""
    new_at = f"(at {x:.4f} {y:.4f}{rotation})"
    return text[:span[0]] + new_at + text[span[1]:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--floorplan", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.floorplan.read_text(encoding="utf-8"))
    parts = {p["id"]: p for p in plan.get("parts", [])}

    text = args.input.read_text(encoding="utf-8")
    fps = parse_board(text)

    moves: list[dict] = []
    for pid, (ref, ox, oy) in MAPPING.items():
        part = parts.get(pid)
        if part is None or part.get("zone") != "base":
            continue
        if ref not in fps:
            print(f"note: {pid} -> {ref} not on the board; skipped")
            continue
        board_x = part["x"] + ox
        board_y = part["y"] - BOARD_OFFSET_Y + oy
        old = fps[ref]["at"]
        moves.append({
            "part": pid, "ref": ref, "span": fps[ref]["at_span"],
            "from": [old[0], old[1]], "to": [board_x, board_y],
            "rotation": old[2] if len(old) > 2 else 0.0,
        })

    if not moves:
        print("no mapped parts moved; nothing written")
        return 1

    # Apply in descending span order so earlier offsets are unaffected.
    for m in sorted(moves, key=lambda m: -m["span"][0]):
        span = m.pop("span")
        rotation = f" {m['rotation']}" if m["rotation"] else ""
        new_at = f"(at {m['to'][0]:.4f} {m['to'][1]:.4f}{rotation})"
        text = text[:span[0]] + new_at + text[span[1]:]

    args.output.write_text(text, encoding="utf-8")
    print(f"moved {len(moves)} footprints to {args.output}:")
    for m in moves:
        print(f"  {m['part']:20s} {m['ref']:6s} ({m['from'][0]:.1f}, {m['from'][1]:.1f}) -> "
              f"({m['to'][0]:.1f}, {m['to'][1]:.1f})")
    print("run kicad-cli drc on the candidate and review before merging.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
