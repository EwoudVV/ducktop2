# Phase 3 Verification — 4 fabricable board files (2026-08-29)

Status: layout of the 4 split boards complete and DRC-checked. Wiring is
Phase 4.

## Deliverables

| Board | File | Footprints | Region |
|---|---|---|---|
| Left I/O | `left_io/left_io.kicad_pcb` | 266 (261 sch + H10/H11/H12/H16 + FPC1_L) | x0–70, 70×185, hinge notch x12–48 |
| Right I/O | `right_io/right_io.kicad_pcb` | 163 (158 sch + H13/H15/H17/H27 + FPC2_R) | x300–358, 58×185, notches x310–346 + edge slot x352.78–358 |
| BMS | `bms/bms.kicad_pcb` | 46 (45 sch + FPC3_B) | 60×60 (free choice; 45×60 too tight for the 45-part layout) |
| Center | `ducktop2-center.kicad_pcb` | 710 (707 keep + FPC1_C/FPC2_C/FPC3_C) | x70–300, 230×185 |

All footprints verified inside their regions (pad-AABB check, 0 crossing
internal boundaries). J24/J25 on the left board overhang the chassis edge
x=0 by design (USB-A connectors through the chassis wall — same as the
original monolithic board).

## Sources of truth (IMPORTANT — differs from the handoff notes)

1. `verification/board_partition.json` is a **stale, uncommitted** scratch
   artifact. It disagrees with the committed, gate-verified schematics:
   - partition L=165 vs left_io schematic 261 (90 left_io parts sit in
     partition C, 50 in R)
   - partition R=220 vs right_io schematic 158
   - partition puts U14 in R; the frozen spec says CENTER
   - partition predates the Phase 2.0 J11/J12 USB2 conversion (still
     lists the 46 obsolete SS-lane parts)
   Board sets were taken from the four project netlists instead
   (`verification/*_netlist.xml`), which match the schematics exactly.

2. The 46 PCB-only footprints in no schematic (C1720, C1721, U2010,
   U1762, D2120–27, C2044–54, ...) are the **removed SS-lane parts** from
   Phase 2.0 (J11/J12 USB2-only). None appear on any new board.

3. Mounting holes follow their physical position: L = H10/H11/H12/H16,
   R = H13/H15/H17/H27, C = H1/H2/H3/H4/H14/H21–26. H12 (x63.8) and H27
   (x353.3) were removed from the center copy and re-added to L/R (they
   are in the center netlist, so the center board needs the deletion).

## Placement

Every part was transplanted by reference from `ducktop2.kicad_pcb`
(preserving the careful manual placement). Parts whose old position
crossed an internal cut line (x=70 / x=300 — the monolithic board was
laid out without the future cuts in mind) were re-placed deterministically:

- out-of-region parts clustered by old-board proximity (link ≤ 10mm),
  each cluster translated to the first collision-free slot inside its
  region, internal relative layout and rotation preserved
- collisions checked at PAD level (per-pad AABBs, 0.8mm margin) — hull-
  level margins under-reserve parts with uneven pad layouts
- pad geometry parsed from the board text (pcbnew SWIG by-value returns
  leak/corrupt the type table after ~500 calls; all geometry is
  text-parsed, validated against pcbnew for rotated footprints)
- legality nudge pass re-scans any offending part on a 1mm grid
- re-placed pads kept ≥0.7mm from board edges; mounting holes reserved
  during packing; FPC connector positions resolved against all final
  parts (scanned along the edge for a clear spot)

Re-placed counts: L 113, R 34, B 45, C 206.

## DRC (kicad-cli pcb drc, project rules from each board dir)

Baseline (original monolithic board): 51 shorts, 42 clearances, 199
courtyard overlaps, 24 hole_clearance, 68 mask bridges, 49 isolated
copper.

| Board | shorts | clearance | courtyard | hole_clr | mask br | edge | notes |
|---|---|---|---|---|---|---|---|
| left_io | 0 | 30 | 19 | 0 | 4 | 3 | clearances are intra-footprint pad pitches (pre-existing, also on original) |
| right_io | 0 | 25 | 14 | 0 | 0 | 10 | edge = I/O connectors at chassis edge by design |
| bms | 0 | 0 | 4 | 0 | 0 | 0 | near-clean; 4 courtyard touches |
| center | 17 | 180 | 173 | 183 | 34 | 22 | all pre-existing original-board issues; 0 shorts involve re-placed parts (original had 51) |

Unconnected-items (499/448/100/499) = unrouted nets, expected at Phase 3
(routing is Phase 4). Silk issues are cosmetic.

## Tooling notes

- Boards built with the KiCAD-MCP `kicad_create_board_from_schematic`
  (fresh sync from each project's schematic) then reworked by
  `gen/generate_split_boards.py` (pcbnew for L/R/B placement + text
  surgery for C).
- pcbnew SWIG corruption workarounds: all geometry read from file text,
  no `board.Remove` after `Set*`, center board edited text-side, outline
  injected as text, connectors added in a fresh subprocess.
- `.kicad_pro` rule sets for the daughterboards must be copied from
  `ducktop2.kicad_pro` AFTER the last MCP sync (the MCP rewrites the pro
  from its stale in-memory copy on every sync call). `left_io.kicad_dru`
  etc. were copied from `ducktop2.kicad_dru`.
- New footprint: `ducktop2.pretty/FH12-100S-0.5SH_1x100-1MP_P0.50mm_Horizontal.kicad_mod`
  (derived from the KiCad FH12-50S; 100 pads, MP tabs ±26.65). 3D model
  references the FH12-50S step as placeholder.

## Open items for Phase 4

1. FPC connectors are placed but not wired (refs FPC1_L/FPC1_C/FPC2_C/
   FPC2_R/FPC3_C/FPC3_B, values = part numbers, no nets).
2. FPC-2 single 100-pin vs 2×50 decision affects connector wiring only.
3. Center board carries the original board's WIP routing tracks; all
   other boards are unrouted. Routing from scratch per board.
4. Pre-existing DRC backlog (intra-footprint clearances, courtyard
   touches, original center shorts) to be triaged.