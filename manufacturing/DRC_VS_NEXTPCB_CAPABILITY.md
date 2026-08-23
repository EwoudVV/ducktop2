# DRC Rules vs NextPCB 8-Layer Capability — Gap Table

NextPCB capability source: https://www.nextpcb.com/pcb-capabilities (fetched
2026-08-13). Board rules are the committed net-class/design values.

## Rule by rule

| Item | Our design rule | NextPCB capability | Verdict |
|---|---|---|---|
| Min trace width | 0.1 mm (fan-out class); classes 0.2-0.29 | 0.076 mm (3 mil @1oz outer) | PASS (2.5x margin) |
| Min spacing | 0.15 mm (all net classes) | 0.076 mm (3 mil) | PASS (2x margin) |
| SMD pad-to-SMD pad | 0.15 mm (via class clearance) | 0.15 mm | AT LIMIT — routing gap rule is identical to fab min; acceptable, verify at DFM |
| Via-to-via (same net) | >= 0.2 mm effective (0.6 pad / 0.15 clr configurable) | 0.2 mm (8 mil) | PASS (matches) |
| Via (0.6/0.3) annular ring | 0.15 mm | 0.09 mm (3.5 mil) | PASS |
| PTH-to-track | 0.15 mm class clearance | 0.23 mm (9 mil) | **FLAG** — any PTH pad routed closer than 0.23 mm to a track will fail their DFM. Track routing must keep >= 0.23 mm from TH pads (vias + TH component pads). Not a rule-in-file change; a routing rule. |
| Hole-to-hole (CAF) | N/A (no rule) | 0.3 mm | PASS — verified 333-TH-pad pairwise scan: min spacing 0.4+ (0 pairs < 0.4) |
| TH pad-to-TH pad | 0.15 mm class | 0.4 mm | PASS — same pairwise scan: 0 pairs under 0.4 mm |
| NPTH-to-track | 0.15 mm class | 0.2 mm | FLAG (routing rule) — keep 0.2+ from NPTH (mounting holes) |
| Trace-to-outline | edge_clearance rule (enforced at routing) | 0.2 mm | NOTE — must be enforced in DRC during routing (8 silk-edge items exist; copper is unrouted) |
| Pad-to-mask clearance | 0.05 mm (was 0, corrected 2026-08-13) | opening >= 0.04 mm | PASS after correction |
| Solder mask bridge | follows pad/copper spacing | 0.09 mm green | PASS (0.15 min copper spacing > bridge min) |
| Silk line width | 0.15 mm strokes | >= 0.12 mm | PASS |
| Silk text height | 1.0 mm | >= 0.76 mm | PASS |
| Silk to pad | silk_over_copper DRC class | >= 0.15 mm | 13-16 items pending (cosmetic cleanup) |
| Board thickness | 1.6 mm target | 1.6 +/-10% | PASS |
| Board outline | 358 x 185 + recess | max 500 x 400 (6+L) | PASS |
| Copper weights | 1 oz | outer/inner 1 oz | PASS |

## Rule changes applied today

1. pad_to_mask_clearance 0 -> 0.05 mm (mask opening tolerance).
2. (none else — every geometric rule already exceeds or matches fab min.)

## Routing-phase rules to honor (not board-file rules)

- PTH/NPTH pads: keep 0.23/0.2 mm from adjacent tracks.
- Copper >= 0.2 mm from the board edge (edge_clearance DRC).
- Th-pad fanout: 0.15 mm traces allowed (0.076 min) — the Mu SODIMM escape
  is within fabricator capability (0.5 mm pitch, 0.3 mm pads: gap 0.2 mm).

## Open decisions before the order

- Surface finish: ENIG recommended (fine-pitch QFN, 0.3 mm USB-C pads).
  Board currently says "None".
- Solder mask color (green default recommended for mask-bridge resolution).
- V-score vs CNC (single board -> CNC routing; recess corners need CNC).