# Mu Connector (A1) Fan-out Feasibility — 8L

Verified 2026-08-13 against `Module_LattePanda.pretty/LattePanda_Module_H8.0mm_Horizontal.kicad_mod`
and the board placement of A1 (181.3, 45, rot 90).

## Geometry facts

- 260 signal pads in two rows of 130, plus 2 mounting pads (2 x 3.5 mm) and
  2 NPTH (1.1 mm).
- Pitch **0.5 mm** (128 consecutive deltas of exactly 0.5 mm).
- Pad size **0.3 x 1.75 mm**, oriented with the long axis outward.
- Board-space: rows at X 177.2 and X 185.4, spanning Y 11.6-78.4.

## Fan-out plan (feasible, no via-in-pad)

- Inter-pad gap is 0.2 mm; a 0.1 mm trace + 0.15/0.15 clearance needs
  0.4 mm, so **nothing routes between pads**. All escapes run straight
  outward from the 1.75 mm pad ends (no dog-bone needed).
- On-pitch outward escape works: 0.15 mm trace + 0.15/0.15 clearance =
  0.45 mm < 0.5 mm pitch.
- 130 pads per side fan out to via farms outside the rows:
  - West side (board X < 177.2): strip X 172-176 is free of components
    (nearest parts stop at X ~171). 130 vias in 3 staggered columns over
    66 mm of Y = 1.5 mm column pitch — comfortable.
  - East side (board X > 185.4): occupied by C586/C587/R1708/R1730/R1731
    (~6 parts at X 186.9-193.4). The via farm fits X 186-190 by nudging
    C586/C587/R1708 ~2 mm east during routing (they are the USBC2 AC caps;
    keep their pad-to-A1-pad clearance >= 0.15 mm when nudging).
- Layer budget: escape traces spread over L1, L3, L6 (~44 traces per layer
  per side), with L2/L4/L7 GND planes providing the return references.
- Via spec: 0.45/0.2 mm (pad/drill) class, 3 columns per side, GND
  stitching vias interleaved every ~5 signal vias.

## Constraints on the routing order

1. Fan the Mu out BEFORE routing anything else in X 150-200, Y 10-80; the
   escape patterns on all three signal layers must be registered to each
   other to avoid via-collision dead ends.
2. Keep the west strip X 172-176 clear during placement tweaks (no new
   components there).
3. GND planes (L2/L4/L7) must be poured with the via farms' anti-pads
   respected; no split in L2/L4 under the connector region.

## Conclusion

Feasible with the 8-layer stackup and standard through-vias. No via-in-pad,
no HDI, no blind/buried vias required.
