#!/usr/bin/env python3
"""Inject test points onto a built ducktop2 board.

The schematics carry the test points (Connector:TestPoint, one per probed
net); the boards get them here -- placed on a probe-friendly strip, net
names resolved to the board's exact names, and any collisions resolved by
moving only the injected points.  Run AFTER generate_split_boards.py and
fix_board_hygiene.py.

Usage: KICAD_PYTHON=... python3 gen/add_test_points.py bms
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import generate_split_boards as g

PROJDIR = g.PROJDIR
PCB = g.PCB
FP_LIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/TestPoint.pretty"
FP_NAME = "TestPoint_Pad_1.5x1.5mm"

# Per-board test point tables: (ref, contract net name, seed x, seed y).
# Nets are basename-resolved against each board's actual net names.
TEST_POINTS = {
    "bms": [
        ("TPB1", "PACK_POS_RAW", 47.5, 12.0), ("TPB2", "BAT_PROT_VIN", 53.5, 12.0),
        ("TPB3", "PACK_POS_FUSED", 47.5, 18.5), ("TPB4", "BAT_PROT_FET_COMMON", 53.5, 18.5),
        ("TPB5", "BAT_PROT_GATE", 47.5, 25.0), ("TPB6", "BAT_PROT_CGATE", 53.5, 25.0),
        ("TPB7", "PACK_FAULT_N", 47.5, 31.5), ("TPB8", "PACK_RETRY_PULSE", 53.5, 31.5),
        ("TPB9", "MCU_3V3", 47.5, 38.0), ("TPB10", "BMS_AVDD", 53.5, 38.0),
        ("TPB11", "BMS_VDD", 47.5, 44.5), ("TPB12", "BMS_SRP", 53.5, 44.5),
        ("TPB13", "BMS_SRN", 47.5, 51.0), ("TPB14", "BMS_PRES", 53.5, 51.0),
        ("TPB15", "BMS_LD", 47.5, 57.0), ("TPB16", "FG_VSS", 53.5, 57.0),
    ],
}


def resolve_net(name, board_nets_by_base):
    if name == "GND":
        return "GND"
    cands = board_nets_by_base.get(name)
    if not cands:
        raise SystemExit(f"test-point net {name!r} not found on board")
    if len(cands) > 1:
        raise SystemExit(f"test-point net {name!r} ambiguous: {cands}")
    return next(iter(cands))


def main(board):
    rows = TEST_POINTS[board]
    if board == "center":
        out = os.path.join(PROJDIR, "ducktop2-center.kicad_pcb")
    else:
        out = os.path.join(PROJDIR, board, f"{board}.kicad_pcb")
    t = open(out).read()
    import re as _re
    board_nets = set(_re.findall(r'\(net "([^"]+)"\)', t))
    by_base = {}
    for n in board_nets:
        by_base.setdefault(n.split("/")[-1], set()).add(n)
    # refs already present -> idempotent skip
    have = {m for m in _re.findall(
        r'\(property "Reference" "([^"]+)"\n', t)}
    missing = [(r, n, x, y) for (r, n, x, y) in rows if r not in have]
    todo = rows  # the refill always runs
    if not missing:
        print(f"{board}: test points already present")
        return 0
    # the board is dense: search for genuinely free spots near each seed
    # instead of trusting the seeds (the overlap fixer stays silent when
    # no legal spot exists nearby)
    _, file_pads0 = g.parse_pad_bboxes(out)
    occupied = []
    for pads in file_pads0.values():
        for (px, py, pw, ph) in pads:
            occupied.append((px - pw, py - ph, px + pw, py + ph))
    PAD = 1.5 / 2 + 0.5  # pad half + probe clearance
    def free(cx, cy):
        for (x0, y0, x1, y1) in occupied:
            if cx - PAD < x1 and cx + PAD > x0 and cy - PAD < y1 and cy + PAD > y0:
                return False
        return True
    def find_free(sx, sy, lo=1.5, hi=58.5):
        # spiral out from the seed on a 0.5 mm grid; keep it on-board
        best = None
        for r in range(0, 120):
            rstep = r * 0.5
            for dx in range(-r, r + 1):
                for dy in (-r, r):
                    cx, cy = sx + dx * 0.5, sy + dy * 0.5
                    if lo + PAD < cx < hi - PAD and lo + PAD < cy < hi - PAD and free(cx, cy):
                        return (cx, cy)
            for dy in range(-r + 1, r):
                for dx in (-r, r):
                    cx, cy = sx + dx * 0.5, sy + dy * 0.5
                    if lo + PAD < cx < hi - PAD and lo + PAD < cy < hi - PAD and free(cx, cy):
                        return (cx, cy)
        return None
    placed = []
    for ref, net, sx, sy in missing:
        spot = find_free(sx, sy)
        if spot is None:
            raise SystemExit(f"{board}: no free spot found for {ref} near ({sx},{sy})")
        cx, cy = spot
        bname = resolve_net(net, by_base)
        placed.append((ref, FP_LIB, FP_NAME, (cx, cy), 0.0, {"1": bname}))
        # reserve the spot for the next search
        occupied.append((cx - PAD, cy - PAD, cx + PAD, cy + PAD))
        print(f"    {ref} ({net}) -> free spot ({cx:.1f}, {cy:.1f})")
    todo = rows
    extra = placed
    missing = []  # injection uses `extra` below; skip the stale path
    if not extra:
        raise SystemExit(f"{board}: nothing to inject")
    # one subprocess adds every test point (same machinery as the
    # connector add: never mutates existing footprints, no SWIG rot)
    code = f"""
import pcbnew
b = pcbnew.LoadBoard({out!r})
for ref, fplibdir, fpname, pos, rot, padnets in {extra!r}:
    fp = pcbnew.FootprintLoad(fplibdir, fpname)
    fp.SetReference(ref)
    fp.SetValue(padnets.get("1", ""))
    fp.SetPosition(pcbnew.VECTOR2I(int(pos[0]*1e6), int(pos[1]*1e6)))
    fp.SetOrientationDegrees(rot)
    fp.SetLayer(pcbnew.F_Cu)
    for pad in fp.Pads():
        net = padnets.get(pad.GetNumber()) or padnets.get(str(pad.GetNumber()), "")
        if net:
            item = b.FindNet(net)
            if item is None:
                item = pcbnew.NETINFO_ITEM(b, net)
                b.Add(item)
            pad.SetNet(item)
    b.Add(fp)
pcbnew.SaveBoard({out!r}, b)
"""
    r = subprocess.run([PCB, "-c", code], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit("test point injection failed")
    print(f"{board}: injected {len(extra)} test points")
    g.refill_zones(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
