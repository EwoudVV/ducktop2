#!/usr/bin/env python3
"""
Fix placement-level pad collisions on the Ducktop2 mainboard.

Strategy (conservative):
  - Only small passives (<= 4 pads, e.g. R/C/L/diodes) are auto-moved.
  - Moves are minimal, on the 1.27 mm placement grid, axis-aligned.
  - Every candidate position must clear ALL cross-footprint pad overlaps
    AND keep a >= 0.25 mm pad-to-pad gap to every other footprint.
  - The board is 0% routed, so no track geometry is at risk; zones are
    untouched here (refill only in a copied project, per project practice).
  - Everything else (connectors, ICs, big-part overlaps) is reported for
    manual placement.

Produces a candidate board file plus a JSON move log; never edits in place.

Usage:
  python3 gen/fix_placement_collisions.py \
      --input ducktop2.kicad_pcb --output /tmp/candidate.kicad_pcb
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

from analyze_placement_collisions import parse_board

GRID = 1.27
MIN_GAP = 0.25
MAX_STEPS = 4
MAX_ITERATIONS = 40
CELL = 5.0


def pad_abs(pad: dict, fp: dict) -> tuple[float, float]:
    fx, fy, fr = fp["at"][0], fp["at"][1], (fp["at"][2] if len(fp["at"]) > 2 else 0.0)
    px, py = pad["at"][0], pad["at"][1]
    if fr:
        r = math.radians(fr)
        px, py = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
    return fx + px, fy + py


def pad_box(pad: dict, fp: dict) -> tuple[float, float, float, float]:
    cx, cy = pad_abs(pad, fp)
    w = pad["size"][0] if pad["size"] else 0.5
    h = pad["size"][1] if pad["size"] else 0.5
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def boxes_overlap(a: tuple, b: tuple, gap: float = 0.0) -> bool:
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def fp_bbox(fps: dict, ref: str) -> tuple[float, float, float, float]:
    boxes = [pad_box(p, fps[ref]) for p in fps[ref]["pads"]]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


class Grid:
    """Uniform spatial grid over pad boxes for fast neighborhood queries."""

    def __init__(self, fps: dict):
        self.fps = fps
        self.cells: dict[tuple[int, int], set[str]] = {}
        self.ref_boxes: dict[str, tuple] = {}
        for ref in fps:
            if not fps[ref]["pads"]:
                continue
            box = fp_bbox(fps, ref)
            self.ref_boxes[ref] = box
            for cx in range(int(box[0] // CELL) - 1, int(box[2] // CELL) + 2):
                for cy in range(int(box[1] // CELL) - 1, int(box[3] // CELL) + 2):
                    self.cells.setdefault((cx, cy), set()).add(ref)

    def neighbors(self, ref: str) -> set[str]:
        box = self.ref_boxes.get(ref)
        if box is None:
            return set()
        out = set()
        for cx in range(int(box[0] // CELL) - 1, int(box[2] // CELL) + 2):
            for cy in range(int(box[1] // CELL) - 1, int(box[3] // CELL) + 2):
                out |= self.cells.get((cx, cy), set())
        out.discard(ref)
        return out

    def pad_collides(self, ref: str, other: str, gap: float) -> bool:
        for p in self.fps[ref]["pads"]:
            pb = pad_box(p, self.fps[ref])
            for op in self.fps[other]["pads"]:
                if boxes_overlap(pb, pad_box(op, self.fps[other]), gap):
                    return True
        return False

    def refresh_ref(self, ref: str) -> None:
        box = fp_bbox(self.fps, ref)
        self.ref_boxes[ref] = box
        # simple approach: rebuild the whole grid (fast enough)
        self.cells = {}
        for r, b in self.ref_boxes.items():
            for cx in range(int(b[0] // CELL) - 1, int(b[2] // CELL) + 2):
                for cy in range(int(b[1] // CELL) - 1, int(b[3] // CELL) + 2):
                    self.cells.setdefault((cx, cy), set()).add(r)

    def collisions(self) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        out = []
        for ref in self.fps:
            for other in self.neighbors(ref):
                pair = tuple(sorted((ref, other)))
                if pair in seen:
                    continue
                seen.add(pair)
                if self.pad_collides(ref, other, 0.0):
                    out.append(pair)
        return out


def move_fp(board_text: str, fp: dict, dx: float, dy: float) -> str:
    old = fp["at"]
    new_x = old[0] + dx
    new_y = old[1] + dy
    rotation = f" {old[2]}" if len(old) > 2 else ""
    new_at = f"(at {new_x:.4f} {new_y:.4f}{rotation})"
    start, end = fp["at_span"]
    return board_text[:start] + new_at + board_text[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    board = args.input
    if board == args.output:
        raise SystemExit("input and output must differ")
    text = board.read_text(encoding="utf-8")
    if re.search(r"\n\t\(segment ", text):
        raise SystemExit("board has routed segments; refusing (placement-only)")

    start = time.time()
    fps = parse_board(text)
    small = {r for r, fp in fps.items() if len(fp["pads"]) <= 4 and fp.get("at") and "at_span" in fp}
    all_refs = set(fps)
    grid = Grid(fps)

    collisions = grid.collisions()
    print(f"pad collisions found: {len(collisions)} ({(time.time() - start):.1f}s)")

    move_log: list[dict] = []
    accumulated: dict[str, list[float]] = {}
    for iteration in range(MAX_ITERATIONS):
        collisions = grid.collisions()
        if not collisions:
            break
        if iteration % 5 == 0:
            print(f"iteration {iteration}: {len(collisions)} collisions remaining")

        incident: Counter = Counter()
        for ra, rb in collisions:
            incident[ra] += 1
            incident[rb] += 1

        progressed = False
        for ra, rb in sorted(collisions, key=lambda p: (incident[p[0]] + incident[p[1]],)):
            if len(fps[ra]["pads"]) > len(fps[rb]["pads"]):
                ra, rb = rb, ra
            if incident[ra] > incident[rb]:
                ra, rb = rb, ra
            if ra not in small:
                continue

            moved = False
            for radius in range(1, MAX_STEPS + 1):
                for dxs, dys in (
                    (radius, 0), (-radius, 0), (0, radius), (0, -radius),
                    (radius, radius), (radius, -radius), (-radius, radius), (-radius, -radius),
                ):
                    dx, dy = dxs * GRID, dys * GRID
                    old_at = fps[ra]["at"]
                    fps[ra]["at"] = (old_at[0] + dx, old_at[1] + dy,
                                     old_at[2] if len(old_at) > 2 else 0.0)
                    ok = all(
                        not grid.pad_collides(ra, other, MIN_GAP)
                        for other in grid.neighbors(ra)
                    )
                    if ok:
                        grid.refresh_ref(ra)
                        acc = accumulated.setdefault(ra, [0.0, 0.0])
                        acc[0] += dx
                        acc[1] += dy
                        move_log.append({
                            "ref": ra, "from": list(old_at[:2]),
                            "to": [old_at[0] + dx, old_at[1] + dy],
                            "delta": [dx, dy], "collided_with": rb,
                        })
                        progressed = True
                        moved = True
                        break
                    fps[ra]["at"] = old_at
                if moved:
                    break
        if not progressed:
            print("no further automatic moves possible")
            break

    # Apply accumulated per-ref moves to the original text in descending span
    # order so earlier offsets are unaffected by later edits.
    for ref, (dx, dy) in sorted(accumulated.items(), key=lambda kv: -kv[1][0] * 0 + -fps[kv[0]]["at_span"][0]):
        text = move_fp(text, fps[ref], dx, dy)

    args.output.write_text(text, encoding="utf-8")
    log_path = args.output.with_suffix(".moves.json")
    log_path.write_text(json.dumps(move_log, indent=2) + "\n", encoding="utf-8")
    print(f"moved {len(move_log)} small parts; wrote {args.output} and {log_path.name}")

    # Report what remains (big parts only by construction).
    fps2 = parse_board(text)
    grid2 = Grid(fps2)
    remaining = grid2.collisions()
    big = sorted(set(r for pair in remaining for r in pair) - small)
    print(f"remaining pad collisions: {len(remaining)}; manual-review refs: {len(big)}")
    for ref in big[:40]:
        print(f"  MANUAL: {ref}")
    print(f"total runtime {(time.time() - start):.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
