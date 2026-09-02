# FPC cable spec — 2026-09-02 (supersedes FPC_CABLE_SPEC_2026-08-30)

The single source of truth for pin assignments is `gen/fpc_contract.py`.
This document describes the PHYSICAL cables: what to buy, which way the
conductors run, and how the shield lands. Phase 5 geometry: connector
mouths (FFC entry = footprint-local +Y, opposite the solder pins) face
each other across every seam; the cables lie flat, no fold.

## Cable geometry law (why the maps look mirrored)

Each pair's connectors are mounted 180 deg apart. A straight Type-A FFC
between 180-deg-mounted connectors lands conductor N on side-A pad N and
side-B pad (N_max+1-N) — the cable mirrors the pin order. The contract
encodes this: side-B maps = `reversed_map(side A)`. The CABLE itself is
a straight-through Type-A FFC (same-side contacts, both ends). Do NOT
order a "reversed"/Type-B cable.

## Connector positions (board frame, KiCad CCW)

| ref  | board  | part                | anchor         | rot | mouth faces |
|------|--------|---------------------|----------------|-----|-------------|
| FPC101 | left_io  | FH41-68S-0.5SH(05) | (65.6, 92.5)  |  90 | +X (seam x=70) |
| FPC102 | center   | FH41-68S-0.5SH(05) | (73.5, 92.5)  | 270 | -X (seam x=70) |
| FPC103 | center   | FH41-68S-0.5SH(05) | (294.6, 92.5) |  90 | +X (seam x=300) |
| FPC104 | right_io | FH41-68S-0.5SH(05) | (303.6, 92.5) | 270 | -X (seam x=300) |
| FPC105 | center   | FH12-30S-0.5SH(55) | (123.5, 6.5)  | 180 | -Y (center bottom edge) |
| FPC106 | bms      | FH12-30S-0.5SH(55) | (30, 54)      |   0 | +Y (BMS top edge) |

Mouth-to-mouth exposed spans: FPC-1 = 2.3 mm across x=70; FPC-2 = 3.4 mm
across x=300; FPC-3 = ~7 mm across the center-bottom/BMS-top seam, plus a
~93 mm lateral jog (FPC105 x=123.5 vs FPC106 x=30) — the FFC routes the
jog flat against the boards.

## The three cables

### FPC-1: left_io <-> center — 68P shielded FFC
- Connector: Hirose FH41-68S-0.5SH(05) x2 (DigiKey FH41-68S-0.5SH(28)-ND)
- Cable: 68P, 0.5 mm pitch, 1.0 mm thick, shielded, Type-A (same-side
  contacts both ends). Length 40 mm (2.3 mm span + assembly slack).
- Conductors: conductor N = FPC1_PINMAP[N] on the left board; lands on
  center pad 69-N (reversed map, handled by the PCB, not the cable).
- Shield: the FFC shield drains contact the connector SH pads at BOTH
  ends; SH + MP pads are GND on both boards.

### FPC-2: center <-> right_io — 68P shielded FFC
- Same connector and cable type as FPC-1. Length 40 mm (3.4 mm span).
- Conductor N = FPC2_PINMAP[N] on the right board; center lands 69-N.
- Shield as FPC-1.

### FPC-3: center <-> bms — 30P FFC
- Connector: Hirose FH12-30S-0.5SH(55) x2 (DigiKey FH12-30S-0.5SH(55)-ND)
- Cable: 30P, 0.5 mm pitch, 1.0 mm thick, standard (unshielded) FFC,
  Type-A. Length 130 mm (~7 mm span + the 93 mm lateral jog + slack).
- Conductor N = FPC3_PINMAP[N] on the BMS; center lands 31-N.
- Note: PACK_POS_FUSED (12 pins) and FG_VSS return (15 pins) dominate this
  cable — verify the FFC current rating: 0.5 A/pin derated 0.4 A gives
  4.8 A on the pack positive, >= the 4.55 A charge breaker.

## Purchasing list
- 4x Hirose FH41-68S-0.5SH(05)  (suffix (05) = 2.5 mm height; confirm
  against the chassis before ordering)
- 2x Hirose FH12-30S-0.5SH(55)
- 2x shielded FFC 68P 0.5 mm Type-A, 40 mm
- 1x FFC 30P 0.5 mm Type-A, 130 mm
