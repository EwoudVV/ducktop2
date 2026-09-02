# DUCKTOP2 AUDIT + REMEDIATION REPORT — 2026-08-31

Companion documents: `AUDIT_2026-08-31_SECOND_OPINION.md` (full audit findings),
`FIX_PLAN_2026-08-31.md` (per-item plans + status tracker + remaining work),
`docs/REBUILD_PIPELINE.md` (the sanctioned rebuild procedure).

---

## PART 1 — WHAT THE AUDIT FOUND

Method: five parallel deep-dive investigations (power/BMS, schematic↔netlist↔board
consistency, placement/DRC forensics, connector/footprint datasheet verification,
generator code review), followed by independent spot-verification of every headline
claim. Findings were severity-ordered: A = will-brick/will-not-work, B = will-fail-
verification, C = risk/design smell, D = cosmetic.

### A-tier — board-killers (one-shot build dead or hazardous)

| ID | Defect | Mechanism |
|----|--------|-----------|
| A1 | Center board's entire FPC boundary electrically severed | Connector pads carried bare contract net names (`VSYS`, `PACK_POS_FUSED`, `MCU_3V3`…) while the board's circuit nets kept monolithic sheet prefixes (`/VSYS` ×39 pads, `/Power & Battery/PACK_POS_FUSED`, `/MCU_3V3` ×100). ~60 shadow-net pairs, 67+ orphan connector pads. Battery never reaches the charger; the EC never reaches the BMS. |
| A2 | All three FFC cables mirrored end-to-end | Connectors mounted with opposite rotations while schematics wired straight-through. Physics of bottom-contact Type-A FFC: opposite rotations ⇒ pin N reaches pin N_max+1−N. FPC-3's fused pack positive (pins 1/2) would land on GND pins 30/29 → **battery direct short through the cable**. |
| A3 | All six FPC connectors face the wrong way | Cable exits point away from their mating connector (Hirose front = contact side = local −Y). Root cause: PHASE4A doc stated "the FH12's FPC enters from the +y side" — inverted. |
| A4 | FH41-68S footprint shield row wrong | 14 SH pads at ±1.25+2.5k (linear ×2 extrapolation from the 30-pin part). Datasheet: G = 13 ground contacts, odd count → centered at x = 0, ±2.5…±15.0. Every pad 1.25 mm off; shield return unsolderable. |
| A5 | BQ77915 protector bypassed by design | `CENTER_RENAME` tied FPC-3 pins 3/4 (pack negative, pre-protector) to system GND — a parallel return around the low-side protector FETs. OCD/short trips would do nothing. |
| A6 | Fuel gauge dead as built | Gauge shunt RS1 bypassed by A5's bond, and divider top R180 left on a stale single-pad net (`BAT_PROT_VIN`). |
| A7 | Right USB-C can never charge | PD2's gated VBUS dead-ended on the right board; the selector's V2 input was stranded on the left with no cable conductor. |
| A8 | FPC-3 pack conductors ~4× overloaded | 2 pins/rail × 0.5 A = 1 A vs ≈4.4 A charge current; protection ordering inverted (cable 1 A < breaker 4.5 A < fuse 10 A). |
| A9 | FPC-1/-2 power pins overloaded | PD1_VBUS_RAW, USB_PD_SELECTED, PD2_VBUS_RAW, AUX_DC_RAW all single-pin for multi-amp rails; AUX source-side segment unfused. |
| A10 | Placement board-killers | C750 electrolytic 1.14 mm over screw hole H22; ten passives inside FH41 connector bodies; U51 inside the HDMI body; U12 inside the radio-DB connector; two fan connectors occupying the same space; the OLED display connector buried under the Mu socket. |

### B-tier — will-fail-verification / serious risk

- **B1** Center zone fills computed against the pre-split 358 mm outline — pour copper outside the board edge on 6 layers.
- **B2** Net-class system non-functional: inherited patterns prefixed (`/VSYS`) vs bare board nets (`VSYS`) → 0 matches; router gets Default rules everywhere on the daughterboards.
- **B3** ERC: genuine errors on all four projects (floating enable on the PD2 path, hub downstream port 4 wired to nothing, undriven power inputs), contradicting the "no genuine errors" claim.
- **B4** Fabrication gate pointed at the retired monolithic board; schematic-parity failed wholesale; bms unrouted = 132, not "499/board".
- **B5** DRC blockers understated as "pre-existing/inherent" — most were fixable regressions of the split.
- **B6** `fix_board_hygiene.py` dropped the rotation of every part it moved (and, found while fixing it, wrote pad-centroid instead of anchor — corrupting asymmetric parts).
- **B7** FH41-68S symbol had no SH pin — re-sync silently strips the shield ground.
- **B8** No battery temperature sensing (later adjudicated: documented design — see Part 3).
- **B9** Mounting holes/probe headers desynced between schematics and boards — a re-sync would corrupt hole placement.
- **B10** Code-less net convention breaks schematic-parity tooling.
- **B11** BOM gaps on the three cable-critical connectors.
- **B12** FH41-68S 3D model reference dangling.
- **B13** "Never F8 the center board" trap undocumented.
- **B14** Seam-edge clearance violations; two parts straddling cut lines missed by the sweep.
- **B15** Q25 ship FET value (CSD17575Q3) vs footprint (CSD19537Q3_DQG) mismatch.

### C-tier — risks, design smells, false economy (24 items)

Including: no cell-OV protection while A5 stood; LTC4418 window doubts (later resolved); AON eFuse UV policy; FAULT pull-up reference; SYS_5V at 5.21 V (zero USB margin); FPC-1 SuperSpeed pairs "with no home" (refuted); Wi-Fi socket without PCIe (documented choice); 0201/UDFN intra-footprint clearances failing the gate while the project already had the exemption mechanism; generator failure paths that only printed; the net-renaming sync as an undocumented black box.

### D-tier — cosmetic/process (13 items)

Silk counts, 13 lib_symbol_mismatch warnings, duplicated bms labels, gitignored netlists, seven orphaned sheet files, dead code (`or True:`), the broken segment-count regex, stale docstrings ("01x100", "75 signals"), docs containing the inverted FPC premise and FH12-100S remnants, missing electrical-calculation rows.

### What the audit got WRONG (adjudicated)

1. "Center FPC102/FPC103 pin maps swapped" — an extraction error; boards matched the contract.
2. The J40/J10/A1/U10 "board wires different nets than schematic" list — false positives; both sides agree (the residues are design questions, not sync defects).
3. "BMS U719.15/19/21 shorted into BMS_PRES" — false; board, schematic and gate agree (pins unconnected).
4. "Netclass patterns match 100%" vs "0 match" — reconciled: matched netlists, not boards.
5. "Rotate all six connectors" vs "one per pair" — reconciled: one per pair cures both mapping and exit geometry.
6. "Mounting holes moved by design" — false; all 15 holes identical to the monolith.
7. **C2 refuted**: the AUX path already had a back-to-back FET pair (Q23+Q24) — the agent missed Q23.
8. **C4 documented-intentional**: AON UVLO 6.2 V deliberately blocks 5 V-only sources ("A 5 V-only USB-C source leaves the laptop off" — recorded design policy).

### NEW A-level defect found during remediation (the audit missed it)

**The LTC4418IUF symbol had pins 6–10 transcribed from the wrong datasheet column.**
Real UF20 pinout: 6 = VALID1, 7 = VALID2 (open-drain), 8 = GND, 9 = CAS, 10 = INTVCC.
The board wired real GND(8) to the INTVCC bypass node and real INTVCC(10) to a
3V3-pulled logic net — **both selectors (U14, U15) could never have functioned.**
The footprint is standard-numbered, so the symbol was the fault. Corrected and now
gate-asserted pin-by-pin.

---

## PART 2 — WHAT WAS FIXED

### Architecture decisions (recorded in FIX_PLAN, applied everywhere)

- **R1 Cable geometry law**: opposite rotations + mirrored pin maps ("reversed"
  transform), mouths facing across each seam; anchors resized so the z-fold fits
  (gaps 5.55 mm seam-70, 4.95 mm seam-300); fold-band keepouts.
- **R2 Charge architecture**: center-side cascade U15 (PD1 over stage-2) ← U15B
  (PD2 over AUX). Priority PD1 > PD2 > AUX. Left U14 reduced to single-input
  (V2 grounded per datasheet); stranded Q17/Q18 removed.
- **R3 Hub mapping**: J12 is served by hub DS4; DS4 DP/DM + PRT_CTL4 cross
  FPC-1/FPC-2 as pass-through (center joins by name); U1760 enable now hub-driven
  via R1841 pull-up. (The frozen spec's "DS4 feeds J11" was superseded; J11 = DS1.)
- **R4 Net unification**: `normalize_board_nets()` rewrites every board net to the
  schematic's exact name (basename-unique match, hard-fail otherwise); connector
  pads resolved through the same resolver. Verified: left board "nets normalized
  0 (already match)" after the pipeline.
- **R5 Pack return**: pack negative never crosses FPC-3; return conductors =
  FG_VSS (BQ77915 post-FET return = the BMS ground reference, 15 pins); center
  side lands on /FG_VSS behind the gauge shunt RS1. `CENTER_RENAME` deleted.

### Electrical fixes (all gate-verified)

1. **Contract rewritten** (`gen/fpc_contract.py`): new FPC-1/2/3 maps with power
   budgets at 0.4 A/pin derate (PACK_POS_FUSED ×12 = 4.8 A ≥ 4.55 A breaker;
   PD2_VBUS_GATED ×7; PD1_VBUS_RAW/USB_PD_SELECTED ×6 ≥ 2.75 A firmware ceiling;
   AUX ×6 + new source-side fuse F195), `reversed_map()` transforms,
   `FPC_ROTATIONS` + `CABLE_TRANSFORM` (build asserts mounted rotations).
2. **FH41-68S footprint regenerated**: 13 SH pads at x = 0, ±2.5·k, self-verifying
   generator (asserts count/span/symmetry); project-local 3D path; symbol gained
   the SH pin (schematics ground it — re-sync can no longer strip the shield).
3. **Center selector cascade built** (U15 + new U15B, Q26–Q29, dividers R741–746,
   locals C715/747/749/751→C715, pull-up R747): window math documented
   (VTH = 1.000 V; USB/PD2 13.1–17.1 V; AUX 5.59–23.3 V; stage-2 5.99–22.45 V).
4. **Left selector reduced** to a qualified single-input export of PD1_VBUS_GATED
   → USB_PD_SELECTED; the dead PD2 half deleted; **AUX source fuse F195 added**.
5. **J12 completed**: DS4 data + PRT_CTL4 wired hierarchically across both cables;
   its TPS2553 enable is now hub-driven instead of floating.
6. **BMS ground = FG_VSS** power symbol; FPC-3 boundary labels local (fixes 13 ERC
   errors); PACK_FAULT/RETRY/MCU_3V3 all verified; gate expectations rewritten.
7. **Q25** footprint now `ducktop2:CSD17575Q3_DQG` (value/footprint agree; same
   DQG land pattern); gate updated.
8. **SYS_5V = 5.10 V** exactly (R40 76.8k → 75.0k; 0.6 V × 8.5), gate updated.

### Board-build fixes (pipeline now deterministic and self-failing)

9. **Connector pad nets resolved** against each board's real net names
   (`resolve_board_net` — hard-fails on ambiguous/missing seam nets) and
   **normalized** to schematic-exact names (`normalize_board_nets`) — the A1
   shadowing mechanism cannot recur silently.
10. **Keepouts resized to true pad extents** (MP/SH pads extend behind the contact
    row); the packer reserves the connectors' full travel columns; netlist-only
    parts (the 18 Phase-5 additions) are injected with footprints + pad nets from
    the netlist via a fresh pcbnew subprocess, with seeds spread on a grid and a
    post-injection overlap pass that moves only injected parts.
11. **Hygiene**: rotation preserved (fixture-tested), anchor+delta correct, refill
    after moves; the build **exits non-zero** on any unresolved overlap
    (`fail()` collector) instead of print-only warnings.
12. **Zones**: outline swapped before refill; hygiene triggers a final refill so
    fills always match the final placement.
13. **Netclasses**: patterns + class definitions restored to all four projects
    (TCP0_* DIFF_100 added — the 8 TMDS pairs had no impedance class anywhere);
    rule keys inserted unconditionally (fresh MCP-created .kicad_pro files lack
    them); daughter `min_hole_to_hole` aligned with main.
14. **Gate**: `--stage fabrication` now checks all four split boards, not the
    retired monolith.

### DRC-verified end state (kicad-cli, per board project rules)

| Board | Shorts | Clearance | Drill/hole | Remaining classes |
|-------|--------|-----------|------------|-------------------|
| left_io | 0 | 0 | 0 | 18 courtyard grazes (incl. F195↔C1729), 7 copper-edge (chassis-through + notch-adjacent), silk |
| right_io | 0 | 0 | 0 | 9 courtyard grazes (C150/C153↔J30, R168↔FPC104), 9 copper-edge (chassis HDMI/GbE), silk |
| bms | — | — | — | silk only — **clean** |
| ducktop2-center | 3 shorts remain | — | — | **needs the final manual placement pass** of the 18 injected parts |

### Schematic verification end state

- Contract gates: **PASS ×4** (ducktop2, left_io, right_io, bms) — pin-by-pin FPC
  contracts incl. transforms, full U15/U15B cascade assertions, BMS pack network,
  ship FET, AUX chain, J12 remote data.
- ERC: **0 errors ×4** (residual warnings = pre-existing lib_symbol_mismatch +
  benign GND-strap pin_to_pin noise).
- SYS_5V 5.10 V, Q25 consistent, FPC BOM properties present, A2/orphan sheets
  removed, netlists version-controlled.

### Docs/process fixes

- `docs/REBUILD_PIPELINE.md` (the only sanctioned rebuild path; "never F8 the
  center" documented), FIX_PLAN tracker updated per item, verification netlists
  un-gitignored, orphaned sheet files deleted, FFC symbol description/defaults
  fixed, left_io docstring fixed, segment-count regex fixed, `KICAD_PYTHON` env
  override + lazy pcbnew import (hygiene runs under system python).

### Items closed as DOCUMENTED DESIGN (not defects)

- **B8**: the pack has no NTC conductor (J2 pins 5/6 are the cell taps); BQ25798
  TS fixed mid-window (58.9 % REGN) + firmware TS_IGNORE=1; BQ77915 TS uses TI's
  unused-function connection; TEMPS=0. Recorded on-sheet and here.
- **C4**: AON UVLO 6.2 V deliberately blocks 5 V-only sources.
- **C9**: Wi-Fi socket deliberately USB2-only (no PCIe/REFCLK wired).
- **C11/C14**: A1 moat + notch-adjacent grazes sanctioned by the project .kicad_dru.

---

## PART 3 — WHAT REMAINS (exact, no design risk beyond item 1)

1. **Center board final placement pass (the only fab blocker)**: the 18 injected
   parts sit near their grid seeds (x185–217, y92–165; J8/J50 near x150/163, y30)
   with correct pad nets; four pairs still mutually overlap (C715↔U15B,
   R745↔C747, R747↔C749) and J8 grazes R388. Move them in the KiCad GUI (or
   extend the pins), then `fix_board_hygiene.py` + DRC.
2. Left/right courtyard grazes (F195↔C1729, C1834↔H11, C150/C153↔J30,
   R168↔FPC104) — separate by a few mm.
3. Fabrication gate parity allowlist (after item 1).
4. Docs: FPC_CABLE_SPEC rewrite from the new contract; ELECTRICAL_CALCULATIONS
   rows (gauge divider, ILIM/ICHG/TS, LTC4418 windows, AON UV/OV, FB dividers,
   FPC budgets); PHASE5 note superseding PHASE4A.
5. Drop the vendor FH41-68S STEP into `ducktop2.3dshapes/`.
6. Confirmations: Q25 footprint pad-compat, purchasing suffix (05)/(55), A1
   socket STD/RVS orientation.

**Policy confirmation requested from the owner**: B8 (no pack thermistor —
firmware TS_IGNORE/TEMPS=0) and C4 (5 V-only sources leave the laptop off) are
recorded design decisions, not oversights.
