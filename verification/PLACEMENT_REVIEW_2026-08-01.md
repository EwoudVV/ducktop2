# Placement Review Checklist — 2026-08-01

Pre-routing placement cleanup state, derived from kicad-cli DRC + the
placement-collision fixer (`gen/fix_placement_collisions.py`).

## Already Fixed (candidate, review before merging)

187 passive parts auto-moved (minimal 1.27 mm grid moves, ≥0.25 mm pad gap
enforced, move log: `python3 gen/fix_placement_collisions.py --input
ducktop2.kicad_pcb --output <candidate>`):

| Metric | Before | After |
| --- | --- | --- |
| Pad shorts | 199 | 99 |
| Solder mask bridges | 202 | 103 |
| Clearance | 273 | 221 |

Largest moves (review these visually): C435, C1708, C174, C705, C411, C35,
C500, R2349, R2346, U2301 (all passives despite odd ref prefixes).

## Manual Placement (design intent required)

### 18 big refs still in pad collisions

A1 (Mu LGA socket), J11, J2 (battery connector), J500, J52, MK430 (IM68A130
mic), Q11, Q12, U11, U170, U1762, U1781, U2303, U410 (audio codec), U44, U45,
U46, U501 (Ethernet PHY).

Hotspots: J11/C1764-C1765, J2 area, MK430/U410 (mic + codec — check acoustic
port keepout), U170/U46, RS10/U11, U1781/C1722, C501/C508, C423/C441/C722.

### 27 off-board anchors remaining (after passes 2-4)

C1760, C415, C435, C506, C515, D151, D153, D154, D2127, D715, D716, F200,
J16, J53, J56, Q14, Q200, Q22, Q24, Q50, Q702, R167, R501, SW1, U2016,
U421, U62.

The fixer now enforces board bounds (pass 4, c555bf9) and recovered the
caps it had pushed off in earlier passes. These 27 remain parked outside the
outline (x up to 399.7, y up to 212.3) because their natural edge regions
are fully occupied — place them manually during the placement review.

### Courtyard overlaps (199)

199 unique pairs; hotspots at the A1 (Mu socket) periphery (A1 with C407,
C442, C444, C445, C502, C503, C1728, C1729, C2009, C2010, H1, H2, R768),
plus J11, U410, U170/U46. Electrically benign; clear visually in the PCB
editor (KiCad highlights them). ~120 were cleared and ~120 new ones created
by the fixer; a courtyard-aware pass is a follow-up.

## Notes

- All fixes must be re-validated with
  `kicad-cli pcb drc --format json --output drc.json ducktop2.kicad_pcb`.
- Zone refill only in a copied project after any placement change
  (`merge_refilled_zone_blocks.py` per project practice).
- Routing must not start until the shorts and off-board anchors are cleared.
