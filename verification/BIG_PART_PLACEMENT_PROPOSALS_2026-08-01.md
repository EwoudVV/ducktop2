# Big-Part Placement Proposals — 2026-08-01

After the automatic passes (190 + 59 passive moves committed, shorts 199 → 54),
the remaining pad collisions involve **intent-sensitive parts**. These are
PROPOSALS for review — nothing below is applied. All moves are minimal
1.27 mm-grid, axis-aligned, and clear the proposed part of ALL pad collisions
(gap ≥ 0.2 mm) as computed against the current board.

| Ref | Part | Position | Shorts | Proposed move | Sensitivity |
| --- | --- | --- | --- | --- | --- |
| U170 | VSSOP-8 (2.3×2 mm) | (228.5, 163.05) rot 180 | 4 (with U46) | (0, +2.54) | low — two SOT/VSOP ICs overlapping is clearly a misplacement |
| U46 | SOT-23-5 | (231.5, 163.05) | 4 (with U170) | (+1.27, 0) | low — alternative to moving U170; pick one |
| U4 | LQFP-100 (14×14 mm) | (303.0, 108.5) | 4 (with R708) | (0, +1.27) | HIGH — large MCU; fanout and decoupling intent |
| U11 | MSOP-10 (3×3 mm) | (58.5, 146.5) | 3 (with RS10, Q11) | (−2.54, +2.54) | medium — charger area; RS10 is a 2512 sense resistor |
| J11 | USB-C receptacle | (353.48, 30.0) | 10 (C1764/65, C2063, R153) | (+1.27, 0) | HIGH — chassis-aligned edge connector |
| J23 | USB-C receptacle | (4.53, 66.0) | 2 (C1724) | (+1.27, 0) | HIGH — chassis-aligned edge connector |
| J500 | JXD1-1022NL magjack | (337.22, 104.0) | 2 (C28) | no single move clears | HIGH — needs multi-step or cap-side fix |
| Y500 | 3225 crystal | (324.35, 102.5) | 3 (R2343/44) | (+3.81, −3.81) | medium — crystal position near U501 |
| Q11 | CSD18540Q5B FET | (66.0, 151.0) | 1 (RS10) | (0, +1.27) | low |
| U2303 | TSSOP-10 (3×3 mm) | (329.1, 105.8) | 1 | (−3.81, +3.81) | medium |
| A1 | **LattePanda Mu module** | (105.2, 143.75) rot 90 | 4 (C441 etc.) | (+3.81, 0) | **VERY HIGH — module/mechanical alignment; prefer moving the adjacent caps instead** |
| MK430 | IM68A130 mic | (40.0, 110.0) | 1 (U410) | see note | HIGH — acoustic port; see MECHANICAL_INTEGRATION |

## Recommendations

1. **U170 + U46** — apply as a pair (move U46 +1.27 x; keeps the 180°-rotated U170
   fixed). Low risk.
2. **A1 (Mu module)** — do NOT move. The A1-adjacent collisions are caps
   (C441 at (85.8, 182.0) etc.) near the module perimeter; move THOSE caps
   further out instead of the module. Needs a manual pass in the editor
   (the auto-fixer could not find clearance for them in place).
3. **J11/J23 (USB-C)** — verify against the chassis/enclosure before moving;
   if the 1.27 mm shift is unacceptable, the nearby caps should move instead
   (same manual pass as item 2).
4. **U4 (LQFP-100)** — confirm R708's intended location; moving the MCU is
   last resort.
5. **J500 (magjack)** — resolve together with the ethernet cap cluster
   (C500/C501/C508 area is already a known release hold from the Mu-guide
   review).
6. **MK430/U410** — keep the mic fixed (acoustic channel); move U410-side
   passives; see MECHANICAL_INTEGRATION_2026-08-01.md.

## Stuck small-part pairs (fixer exhausted)

R13/R170, C11/C701, C766/R757, C768/C932, R1750/R2015, C2054/R2049,
C23/C38, C1782/C2017, C701/C710, C1763/R2045, C902/R764, C187/C2306,
C762/C768, C750/C758, C45/C766 — dense clusters; resolve visually in the
editor as part of the placement review.

## Next

- Apply the agreed big-part moves (script `gen/fix_placement_collisions.py`
  pattern) or nudge in the GUI.
- Then the manual cap-dispersion pass around A1/J11/J23/J500.
- Then re-run DRC: shorts should reach ~0 before zone design (next step).
