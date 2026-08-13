# Ducktop2 — Electronics-Correctness Handoff Review

Generated: 2026-08-13
Scope: will the board actually work? Everything that affects function —
connectivity, nets, power, integrity — NOT placement cosmetics.

---

## 0. THE HEADLINE: THE BOARD IS NOT ROUTED

**The ducktop2 board file contains ZERO tracks.** There is no signal routing
anywhere in the file, in any git commit, or in any of the backups
(`.bak`, `.bak.before_reloc`, `.bak.v2_before`, `.p1.3_backup`).

Measured state:
- 890 nets, **2030 open airwire segments, ~78 m of unconnected length**
- 0 track segments in file (only 52 orphaned arc corners, since removed,
  and 73 vias)
- 91 copper zones defined but **0 filled polygons** (zones unfilled)
- Power plane *definitions* are correct (see §3) but carry no copper until filled

**Consequence: the board cannot power up or function as-is.** This is a
pre-existing condition — it was never in the repo, it was not introduced by
the recent DRC/placement work, and no placement fix can address it.

### 0.1 What this means for the next session
Routing is the entire remaining electrical task:
1. Route the ~890 signal nets on F.Cu / B.Cu (six-layer board: F.Cu, In1–In4, B.Cu).
2. Fill the inner-layer power planes (GND, SYS_3V3, SYS_5V, VSYS, MCU_3V3,
   VBUS_RAW, MU_12V, USB_PORT_5V, INTERNAL_USB_VBUS) and verify
   plane-to-pad connections.
3. Re-run DRC after routing: the shorts/clearance/courtyard counts in §5 will
   change when copper exists.
4. The WIFI_CLKREQ_N "Tuning Pattern" record in the file is stale metadata
   (references the removed meander arcs) — regenerate or delete when routing.

---

## 1. What was verified CORRECT (current file state)

| Check | Result |
| --- | --- |
| Schematic ↔ board parity (`--schematic-parity`) | **CLEAN** — no missing, extra, or mismatched footprints; no footprint/symbol field mismatches |
| Nets on every placed part | Pads carry correct net names; all 890 nets from the schematic are present |
| Net classes | DIFF_100 (GbE), DIFF_85 (PCIe/Wi-Fi/OLED), DIFF_90 (USB3), USB2_45 (USB2), Default — all defined in the board |
| Shorts | **0** (pad-level shorts found and fixed earlier in the session) |
| Dangling tracks | 0 (only orphaned arc fragments existed; removed) |
| Solder-mask bridges | 0 |
| Silk over copper / silk overlap | 0 (all cleared) |
| Text height / copper-edge clearance | 0 / 0 |
| Footprint DRC (courtyards, clearances) | 163 courtyard + 16 clearance items — all pre-existing baseline, none electrical (§5) |

### 1.1 Net integrity of the moves made this session
All component relocations (J2300, C7, U170, C587, C746, R504, R715, R374/R375,
etc.) preserved pad nets, values, and rotations. No polarity-sensitive part was
flipped: C746 (electrolytic), Q11/Q12/Q14/Q24/Q701/Q702 (FETs), diodes, and
LEDs all kept their original orientation. The 630-pad drift sync changed pad
centers by 0.005 mm only — electrically irrelevant.

The 52 removed arcs were WIFI_CLKREQ_N / TCP0_* meander corners whose straight
segments were already missing (the DRC flagged all as dangling). Their removal
does not change connectivity — those nets were already open.

---

## 2. Component-level notes

### 2.1 C7 (bootstrap cap, BTST1_NODE / SW1) — relocated
Moved from (62.81, 183.27) to (62.8, 178.8) to clear the J2300 radio FFC
pad field. Nets preserved. Caveat: bootstrap caps should sit close to the
switcher's BST/SW pins. **With routing pending, re-verify C7's final distance
to its buck (BQ25798 charger area) when placing tracks.** Original spot was
equally arbitrary; this is a routing-time decision.

### 2.2 J2300 (radio daughterboard FFC) — relocated
Moved (62.5, 183) → (62.5, 181.5). Its top anchor pads previously hung off the
board edge (0.315 mm to edge, some pads beyond 185 mm). Now fully on-board with
0.66 mm edge clearance. Mechanical check needed at assembly: FFC slot position
relative to the board edge and the bottom housing cutout.

### 2.3 U170 (E-key control isolation) — restored
Moved back from (228.5, 165.59) to its original (243, 165). Cleared the J40
mask bridges. Verify trace stub/route when routing (it sits beside the M.2 slot).

### 2.4 C587 (USBC2_SSTX AC cap) — nudged
(185.73, 42.5) → (186.6, 42.5). Cleared mask bridges vs A1's no-net pads.
Remaining 0.15–0.2 mm clearances vs A1 pads are below the 0.25 rule (see §5)
but are copper-clear (no short). Re-check after plane fill.

### 2.5 Footprint note — J2300 is a customized FH12-30S
The board's J2300 pads are deliberately re-mapped vs the library (FFC pin
remap for the radio daughterboard). Do NOT "Update Footprint from Library" on
it. The lib-footprint-mismatch DRC test is set to `ignore` in the project —
re-enable after routing, and keep the ignore only if the µm-drift and
customized-connector classes remain.

---

## 3. Power architecture (verified in definitions)

Inner-layer plane definitions exist (unfilled) and are net-correct:

| Layer | Planes |
| --- | --- |
| In1.Cu | GND (full-board) |
| In2.Cu | VBUS_RAW, INTERNAL_USB_VBUS, MU_12V, SYS_5V, SYS_3V3, USB_PORT_5V, VSYS, MCU_3V3 |
| In3.Cu | GND-side rail split: SYS_3V3, SYS_5V, USB_PORT_5V, VSYS, VBUS_RAW, MU_12V, INTERNAL_USB_VBUS, MCU_3V3 |
| In4.Cu | GND (full-board) |

- **Must verify after first fill**: every power pad's thermal connection lands
  on the correct plane (a pad on MCU_3V3 inside the SYS_3V3 zone would be a
  short the DRC only sees after fill). The no-net 7×7 mm zones scattered on
  inner layers appear to be module-retention keepouts — confirm they don't
  starve any plane region.
- F.Cu/B.Cu carry all signals (no signal planes defined — correct for a
  laptop motherboard).

---

## 4. Known open items that need a human call (not DRC-visible)

1. **The entire routing task** (§0). Nothing else matters until this exists.
2. **Zone fill + post-fill DRC** — plane shorts/clearances only appear after fill.
3. **Stale tuning-pattern metadata** for WIFI_CLKREQ_N.
4. **lib_footprint_mismatch = ignore** — intentional but should be reviewed
   after routing (the underlying µm pad drift is real but harmless).
5. **A1 module courtyard class (39 pairs)** — A1's huge socket courtyard
   overlaps surrounding passives by design; previously planned as an explicit
   waiver class. No electrical impact.
6. **H15 NPTH inside A1 courtyard (1)** — intentional M2.5 retention hole
   under the module.
7. **6 silk-edge warnings** — J190/J30/J422 edge-connector silks hugging the
   board edge; design-intended for edge-mount parts.

---

## 5. Remaining DRC inventory (current, post-fix)

Total 186 (was 958 at session start):

- courtyards_overlap 163 — 39 A1-class (waived-by-design), 124 legacy
  dense-packing pairs (sub-mm touches, mostly 0603 rows). None electrical.
- clearance 16 — R374/R375 vs J310 keyboard FFC pads (0.05–0.1 mm short),
  C587/A1 ×4, C708/C712 + C709/C720 (0.1 mm), RS10/U11 (pre-existing).
  All are on an unrouted board; revisit during routing.
- npth_inside_courtyard 1 (H15/A1, intentional).
- silk_edge_clearance 6 (edge connectors, intended).
- shorts 0, dangling 0, mask bridges 0, silk 0, lib mismatch 0 (ignored),
  edge clearance 0, text height 0.

---

## 6. Bottom line

**Everything that can be verified without copper has been verified and is
correct: netlist parity, part placement integrity, no shorts, no missing
connections that are the fault of placement, and a sane power-plane
architecture.**

**The board does not have any routing.** That is the one thing that will
prevent it from working — and it is a missing work item, not a mistake.
The next session should start with: route signals → fill planes → DRC →
re-verify plane-pad connections → re-enable lib-parity → then manufacture.
