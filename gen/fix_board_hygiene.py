#!/usr/bin/env python3
"""Post-build board hygiene sweep (ducktop2 board split, Phase 4 deep audit).

Runs AFTER generate_split_boards.py on the four final boards.  Uses the
FINAL board file text as the geometry oracle (parse_pad_bboxes) so the
collision checks always match what the DRC sees:
  - move parts whose pads overlap another part's pads (>= 0.25 margin)
  - move parts whose pads sit inside the hinge cutouts / edge slots
  - never move mounting holes or the FPC connectors
Every moved part is verified against the updated real pad set, the region
edges and the forbidden zones; residuals are reported (not silently
dropped).  Text-side (at ...) rewrites -- no pcbnew mutation.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_ducktop2 import PROJDIR
import generate_split_boards as g

BOARDS = [
    ("left_io/left_io.kicad_pcb", "L", g.REGIONS["L"], g.FORBIDDEN["L"]),
    ("right_io/right_io.kicad_pcb", "R", g.REGIONS["R"], g.FORBIDDEN["R"]),
    ("bms/bms.kicad_pcb", "B", g.REGIONS["B"], g.FORBIDDEN["B"]),
    ("ducktop2-center.kicad_pcb", "C", g.REGIONS["C"], g.FORBIDDEN["C"]),
]

MARGIN = 0.3          # target pad-to-pad separation
EDGE = 0.6            # keep pads this far from board edges
FIXED = re.compile(r"^(FPC|H)\d")


def is_fixed(ref):
    return bool(FIXED.match(ref))


def in_zone_clear(cand, region, forbidden):
    x0, y0, x1, y1 = region
    for (px, py, hw, hh) in cand:
        if px - hw < x0 + EDGE or px + hw > x1 - EDGE \
           or py - hh < y0 + EDGE or py + hh > y1 - EDGE:
            return False
        for (fx0, fy0, fx1, fy1) in forbidden:
            if not (px + hw <= fx0 or fx1 <= px - hw
                    or py + hh <= fy0 or fy1 <= py - hh):
                return False
    return True


def sweep(path, board_key, region, forbidden):
    txt = open(path).read()
    parsed, pads = g.parse_pad_bboxes(path)
    # ref -> (at x, y, rot) from the file
    anchors = {}
    for m in re.finditer(r'\t\(footprint "([^"]+)"\n', txt):
        s = m.start()
        depth = 0
        j = s
        while j < len(txt):
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = txt[s:j + 1]
        refm = re.search(r'\(property "Reference" "([^"]+)"', block)
        am = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)\n', block)
        if refm and am:
            anchors[refm.group(1)] = (
                float(am.group(1)), float(am.group(2)),
                float(am.group(3) or 0))
    moved = {}
    for _pass in range(8):
        refs = sorted(pads)
        conflicts = set()
        pairs = []
        for i, a in enumerate(refs):
            if is_fixed(a):
                continue
            for b in refs[i + 1:]:
                if is_fixed(b):
                    continue
                if g.pads_overlap(pads[a], pads[b], margin=MARGIN):
                    pairs.append((a, b))
        for r, pl in pads.items():
            if is_fixed(r):
                continue
            for (px, py, hw, hh) in pl:
                for (fx0, fy0, fx1, fy1) in forbidden:
                    if not (px + hw <= fx0 or fx1 <= px - hw
                            or py + hh <= fy0 or fy1 <= py - hh):
                        pairs.append((r, None))
                        break
                if pairs and pairs[-1] == (r, None):
                    break
        if not pairs:
            break
        for (a, b) in pairs:
            if b is None:
                mover = a
            else:
                area_a = sum((2 * hw) * (2 * hh) for (_, _, hw, hh) in pads[a])
                area_b = sum((2 * hw) * (2 * hh) for (_, _, hw, hh) in pads[b])
                mover = a if area_a <= area_b else b
                if is_fixed(mover):
                    mover = b if mover == a else a
                if is_fixed(mover):
                    print(f"    HYGIENE WARN: {mover} fixed, cannot move for "
                          f"{a}<->{b}")
                    continue
            cur = pads[mover]
            ax = sum(p[0] for p in cur) / len(cur)
            ay = sum(p[1] for p in cur) / len(cur)
            found = None
            candidates = [(i * 0.5 - 20, j * 0.5 - 20)
                          for i in range(81) for j in range(81)
                          if abs(i * 0.5 - 20) > 1.5 or abs(j * 0.5 - 20) > 1.5]
            for (dx, dy) in candidates:
                cand = [(px + dx, py + dy, hw, hh) for (px, py, hw, hh) in cur]
                if not in_zone_clear(cand, region, forbidden):
                    continue
                bad = False
                for o, op in pads.items():
                    if o == mover:
                        continue
                    if g.pads_overlap(cand, op, margin=MARGIN):
                        bad = True
                        break
                if not bad:
                    found = (ax + dx, ay + dy)
                    break
            if found is None:
                print(f"    HYGIENE WARN: no spot for {mover} "
                      f"({'zone' if b is None else b})")
                continue
            moved[mover] = (found[0], found[1])
            pads[mover] = [(px + found[0] - ax, py + found[1] - ay, hw, hh)
                           for (px, py, hw, hh) in cur]
            conflicts.add(mover)
    if moved:
        # rewrite (at ...) text-side
        out = []
        pos = 0
        while True:
            m = re.search(r'\t\(footprint "([^"]+)"\n', txt[pos:])
            if not m:
                out.append(txt[pos:])
                break
            start = pos + m.start()
            depth = 0
            j = start
            while j < len(txt):
                if txt[j] == "(":
                    depth += 1
                elif txt[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = txt[start:j + 1]
            refm = re.search(r'\(property "Reference" "([^"]+)"', block)
            if refm and refm.group(1) in moved:
                nx, ny = moved[refm.group(1)]
                block = re.sub(r'\n\t\t\(at [-\d.]+ [-\d.]+( [-\d.]+)?\)\n',
                               f"\n\t\t(at {nx:g} {ny:g})\n", block, count=1)
            out.append(txt[pos:start])
            out.append(block)
            pos = j + 1
        open(path, "w").write("".join(out))
    print(f"[{board_key}] hygiene: {len(moved)} parts moved, "
          f"{len(pairs)} conflicts resolved")
    for r in sorted(moved):
        print(f"    hygiene {r}: -> ({moved[r][0]:.1f}, {moved[r][1]:.1f})")


def main():
    for path, key, region, forbidden in BOARDS:
        sweep(os.path.join(PROJDIR, path), key, region, forbidden)


if __name__ == "__main__":
    main()