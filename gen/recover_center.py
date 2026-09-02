#!/usr/bin/env python3
"""Phase 5 recovery: restore the committed center board (git) and apply the
Phase-5 additive steps only: reposition/remove+add the FPC connectors at the
contract anchors/rotations, inject the 18 netlist-only parts with pad nets,
assign FPC pad nets, normalize net names.  No destructive text surgery."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import generate_split_boards as g
import fpc_contract as fpc

OUT = os.path.join(g.PROJDIR, "ducktop2-center.kicad_pcb")

# 0) restore the committed center base (the Phase-4 verified board)
os.system(f"git -C {g.PROJDIR} show HEAD:ducktop2-center.kicad_pcb > {OUT}")
lines = open(OUT).read().splitlines()
n_fp = sum(1 for l in lines if l.startswith('\t(footprint '))
print(f"base restored: {n_fp} footprints")

# 1) resolve connector anchors/rotations against the board's own parts
old = g.parse_old_placements(OUT)
refs = set(old) | set(g.netlist_refs(g.NETLISTS["C"]))
all_bb, padlists = g.parse_pad_bboxes(OUT)
for r in sorted(refs):
    if r not in old:
        old[r] = (185.0, 92.5, 0.0, False)
final_pads = []
moves = {}
for r, pads in padlists.items():
    final_pads.extend(pads)
connectors = []
for (ref, lib, name, pos, rot) in g.CONNECTORS["C"]:
    want = fpc.FPC_ROTATIONS[ref]
    connectors.append((ref, lib, name, pos, want))
    print(f"  {ref}: anchor {pos} rot {want} (contract)")

# 1b) apply the Phase-5 pinned placements (chosen for the NEW FPC anchors)
old2 = g.parse_old_placements(OUT)
pins = {r: (x, y, old2[r][2] if r in old2 else 0.0)
        for r, (x, y) in g.PINNED.get("C", {}).items() if r in old2}
_txt = open(OUT).read()
open(OUT, "w").write(g.rewrite_at_lines(_txt, pins))
print(f"  pinned {len(pins)} placements applied")

# 2) netlist-only parts to inject (not physically on the committed board)
nl = g.netlist_parts(g.NETLISTS["C"])
extra = []
for r in sorted(refs):
    if r in old or r.startswith("FPC") or r not in nl:
        continue
    fp_lib, fp_name = nl[r][0].split(":", 1)
    fplibdir = os.path.dirname(g.find_footprint_path(fp_lib, fp_name))
    extra.append((r, fplibdir, fp_name, old[r][:2], 0.0, nl[r][1]))
    print(f"  inject {r} ({fp_name})")

# 3) subprocess: remove old FPC blocks, add connectors + injected parts
import subprocess
code = f"""
import pcbnew
b = pcbnew.LoadBoard({OUT!r})
drop = [f for f in b.GetFootprints() if f.GetReference() in {{'FPC102','FPC103','FPC105'}}]
for f in drop:
    b.Remove(f)
for ref, lib, name, pos, rot in {connectors!r}:
    fp = pcbnew.FootprintLoad({g.LIB_DIRS['ducktop2']!r} if lib == 'ducktop2' else {g.LIB_DIRS['Connector_FFC-FPC']!r}, name)
    fp.SetReference(ref); fp.SetValue(name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetPosition(pcbnew.VECTOR2I(int(pos[0]*1e6), int(pos[1]*1e6)))
    fp.SetOrientationDegrees(rot)
    fp.SetLayer(pcbnew.F_Cu)
    b.Add(fp)
for ref, fplibdir, fpname, pos, rot, padnets in {extra!r}:
    fp = pcbnew.FootprintLoad(fplibdir, fpname)
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(int(pos[0]*1e6), int(pos[1]*1e6)))
    fp.SetOrientationDegrees(rot)
    fp.SetLayer(pcbnew.F_Cu)
    for pad in fp.Pads():
        num = pad.GetNumber()
        net = padnets.get(num) or padnets.get(str(num), "")
        if net:
            netitem = b.FindNet(net)
            if netitem is None:
                netitem = pcbnew.NETINFO_ITEM(b, net)
                b.Add(netitem)
            pad.SetNet(netitem)
    b.Add(fp)
pcbnew.SaveBoard({OUT!r}, b)
print('connectors + parts ok')
"""
r = subprocess.run([g.PCB, "-c", code], capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-1500:]); raise SystemExit("recovery subprocess failed")
print(r.stdout.strip().splitlines()[-1])

# 4) FPC pad nets + normalize (text-side, validated).
# Fallback names = every schematic net: pass-through boundary nets
# (HUB_DS1_DP/DM etc.) exist only in the schematic, never on the base board.
import re as _re
_nl = open(g.NETLISTS["C"]).read()
fallback = frozenset(_re.findall(r'<net [^>]*name="([^"]*)"', _nl))
import html as _html
fallback = frozenset(_html.unescape(n) for n in fallback)
for ref, _lib, _name, _pos, _rot in connectors:
    pinmap = {"FPC102": fpc.FPC102_PINMAP, "FPC103": fpc.FPC103_PINMAP,
              "FPC105": fpc.FPC105_PINMAP}[ref]
    n = g.assign_connector_pad_nets(OUT, ref, pinmap, ground_net="GND",
                                    fallback_names=fallback)
    print(f"  {ref}: {n} pad nets assigned")
g.normalize_board_nets(OUT, g.NETLISTS["C"])

# 5) strip the committed board's WIP routing (it shorts the re-placed
# parts; routing is manual Phase 4b) and refill zones
g.strip_tracks_and_vias(OUT)
g.refill_zones(OUT)
print("center recovery complete")
