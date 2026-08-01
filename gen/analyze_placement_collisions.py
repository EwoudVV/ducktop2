#!/usr/bin/env python3
"""
Analyze placement-level collisions on the Ducktop2 mainboard.

Reads a kicad-cli DRC report (JSON) and the board file, then for every
shorting/courtyard/mask-bridge pair computes the pad geometry and the minimal
translation that clears the collision.  Used to plan placement fixes before
high-speed routing (review next-steps item 9).

Usage:
  kicad-cli pcb drc --output drc.json --format json board.kicad_pcb
  python3 gen/analyze_placement_collisions.py --drc drc.json --board board.kicad_pcb
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


PAD_RE = re.compile(r"^Pad ")
FOOTPRINT_RE = re.compile(r"^Footprint ")


def parse_board(board_text: str) -> dict[str, dict]:
    """Return ref -> {at, uuid, pads: [ {at, size} ]} (F.Cu pads only)."""
    footprints: dict[str, dict] = {}
    depth = 0
    i = 0
    n = len(board_text)
    current = None
    pad_depth = 0
    while i < n:
        c = board_text[i]
        if c == '"':
            i += 1
            while i < n and board_text[i] != '"':
                i += 2 if board_text[i] == "\\" else 1
            i += 1
            continue
        if c == "(":
            depth += 1
            m = re.match(r"\(([A-Za-z0-9_.]+)", board_text[i:])
            token = m.group(1) if m else "?"
            if depth == 2 and token == "footprint":
                current = {"pads": []}
            elif depth == 3 and current is not None:
                if token == "at":
                    nums = re.match(r"\(at\s+([-0-9.eE]+)\s+([-0-9.eE]+)(?:\s+([-0-9.eE]+))?", board_text[i:])
                    if nums:
                        current["at"] = tuple(float(x) for x in nums.groups() if x is not None)
                        end = re.search(r"\)", board_text[i:]).end()
                        current["at_span"] = (i, i + end)
                elif token == "property":
                    pm = re.match(r'\(property\s+"Reference"\s+"([^"]+)"', board_text[i:])
                    if pm:
                        current["ref"] = pm.group(1)
                elif token == "pad":
                    pad = {"at": None, "size": None}
                    current["pads"].append(pad)
                    pad_depth = depth
            elif depth == 4 and current is not None and current["pads"]:
                pad = current["pads"][-1]
                if token == "at":
                    nums = re.match(r"\(at\s+([-0-9.eE]+)\s+([-0-9.eE]+)(?:\s+([-0-9.eE]+))?", board_text[i:])
                    if nums:
                        pad["at"] = tuple(float(x) for x in nums.groups() if x is not None)
                elif token == "size":
                    nums = re.match(r"\(size\s+([-0-9.eE]+)\s+([-0-9.eE]+)", board_text[i:])
                    if nums:
                        pad["size"] = (float(nums.group(1)), float(nums.group(2)))
                elif token == "net":
                    nm = re.match(r'\(net\s+"([^"]+)"', board_text[i:])
                    if nm:
                        pad["net"] = nm.group(1)
            i += len(m.group(0)) if m else 1
        elif c == ")":
            depth -= 1
            if depth == 1 and current is not None:
                if "ref" in current and current.get("at"):
                    footprints[current["ref"]] = current
                current = None
            i += 1
        else:
            i += 1
    return footprints


def pad_abs(pad: dict, fp: dict) -> tuple[float, float]:
    fx, fy, fr = fp["at"][0], fp["at"][1], (fp["at"][2] if len(fp["at"]) > 2 else 0.0)
    px, py = pad["at"][0], pad["at"][1]
    if fr:
        r = math.radians(fr)
        px, py = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
    return fx + px, fy + py


def ref_of(description: str) -> str | None:
    m = re.search(r"of ([A-Za-z0-9]+)", description)
    return m.group(1) if m else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drc", type=Path, required=True)
    parser.add_argument("--board", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.drc.read_text(encoding="utf-8"))
    board_text = args.board.read_text(encoding="utf-8")
    fps = parse_board(board_text)

    print(f"footprints parsed: {len(fps)}")
    for vtype in ("shorting_items", "courtyards_overlap", "solder_mask_bridge"):
        items = [v for v in report.get("violations", []) if v["type"] == vtype]
        print(f"\n== {vtype}: {len(items)}")
        by_ref: Counter = Counter()
        details = []
        for v in items:
            refs = [ref_of(i["description"]) for i in v.get("items", []) if ref_of(i["description"])]
            for r in refs:
                by_ref[r] += 1
            details.append(refs)
        for r, c in by_ref.most_common(10):
            print(f"    {r}: {c}")
        # collisions where both refs are small passives (candidates for auto-move)
        passive_candidates = 0
        for refs in details:
            if len(refs) == 2:
                a, b = fps.get(refs[0]), fps.get(refs[1])
                if a and b:
                    s = max(len(a["pads"]), len(b["pads"]))
                    if s <= 4:
                        passive_candidates += 1
        print(f"    two-ref collisions involving small parts (<=4 pads): {passive_candidates}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
