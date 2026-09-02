# DUCKTOP2 SECOND-OPINION AUDIT — COMPLETE FINDINGS
**Auditor:** independent second-opinion audit (fresh reviewer)
**Repo:** `/Users/ellievanvooren/Documents/kicad/ducktop2` @ d920eaa (clean) · **Date:** 2026-08-31
**Method:** 5 parallel subagent deep-dives (power/BMS, consistency, placement/DRC, connectors/footprints, generators) + independent spot-verification of every headline claim by the integrator. Read-only audit; the repo was not modified by the audit itself.
**Evidence copies:** /tmp/audit_ducktop2/, /tmp/erc_*.rpt, /tmp/drc_*.rpt, /tmp/nlx_*.xml, /tmp/paddiff_*.txt

Unrouted nets are excluded per the brief, except where the *count itself* was misclaimed.
Findings are tagged: **[V]** = independently verified by integrator (direct file/command evidence), **[A]** = agent-verified with detailed evidence, **[A?]** = agent-reported, spot-check inconclusive or contradicted (see adjudication section).

---

## TIER A — WILL-BRICK / WILL-NOT-WORK

### A1. The center board's entire FPC boundary is electrically severed by net-name shadowing **[V]**
Every FPC power/signal pad on `ducktop2-center.kicad_pcb` carries a **bare** contract name while the center's real circuit nets kept the monolithic sheet-prefix. Measured directly:
- `"VSYS"` ×2 (only FPC102 pins 1/2) vs `"/VSYS"` ×39 pads
- `"PACK_POS_FUSED"` ×2 (only FPC105 pins 1/2) vs `"/Power & Battery/PACK_POS_FUSED"` ×3 (Q25.5, R704.1, TP2.1)
- `"MCU_3V3"` ×3 (FPC102.9, FPC103.11, FPC105.8) vs `"/MCU_3V3"` ×100
- Same pattern for `SYS_5V`, `SYS_3V3`, `PCIE_3V3`, `USB_PD_SELECTED`, `PACK_FAULT_N` (FPC105.5 vs U44.10), `PACK_RETRY_PULSE` (FPC105.6 vs U44.13), `FG_VSS` (FPC105.7 vs RS1/U10.8), `PD1/PD2_VBUS_RAW`, `AUX_DC_RAW`, and all `USBC*/HUB_*/GBE_*/TCP0_*` pairs — ~60 bare/prefixed duplicate pairs, 67+ orphan connector pads.

The schematic netlist merges these correctly — it is purely a board-side defect.
**Consequence: battery never reaches the charger; the EC never reaches the BMS; the USB/GbE/HDMI seams are dead.**
Root cause: `gen/generate_split_boards.py:1168` (`assign_connector_pad_nets`, fed at :1658–1665) writes bare `fpc_contract.py` names onto a board cut from the monolith (prefixed nets); `CENTER_RENAME` (fpc_contract.py:81) handles only `PACK_NEG_RAW→GND`; no gate compares **board** pad nets to the contract (`check_fpc_connectors` at verify_design_contracts.py:3144 checks only the netlist XML). The repo contains three naming schemes for the same nodes: board-monolithic prefixed, board-bare, schematic-split prefixed.

### A2. All three FFC cables are mirrored end-to-end — pin N reaches pin N_max+1−N **[V]** (rotations verified by integrator; rule verified by two agents independently)
Mechanical rule (both connectors bottom-contact, top-mounted, standard Type-A untwisted FFC): **equal rotations ⇔ straight; rotations differing 180° ⇔ reversal.** The repo's own `KEYBOARD_FFC_ASSEMBLY_CONTRACT_2026-07-15.md` encodes exactly this (J310 rot−90 / J320 rot+90 → n↔31−n).

| Pair | Rotations (from board files) | Schematic wiring | Physical result |
|---|---|---|---|
| FPC101 (left, 90°) ↔ FPC102 (center, 270°) | opposite | straight | pin N ↔ 69−N |
| FPC103 (center, 90°) ↔ FPC104 (right, 270°) | opposite | straight | pin N ↔ 69−N |
| FPC105 (center, 180°) ↔ FPC106 (bms, 0°) | opposite | straight | pin N ↔ 31−N |

Consequences:
- **FPC-3: PACK_POS_FUSED (pins 1/2) lands on pins 30/29 = GND → battery direct short through the cable.**
- FPC-1: FPC101 pin 1 VSYS → FPC102 pin 68 GND → rail shorted; USB_PORT_5V (4/5 ↔ 65/64) shorted; every USB3/USB2/HDMI pair P↔N swapped.
- FPC-2: SYS_5V(1/2) ↔ GND(68/67).
- No passive cable can fix it: Type-A gives the reversal; a Type-D (reversed) cable cannot insert into same-type bottom-contact connectors at both ends.

**Fix:** rotate one connector per pair by 180° (FPC102 270→90, FPC104 270→90, FPC105 180→0) — restores straight-through AND aligns mouths for a single-fold cable across each seam; flipped FPC102/104 put contact pads 0.38 mm from the seam edges — anchors need a ~0.2 mm nudge. Alternatively encode n↔(N_max+1−n) in the nets (keyboard-contract style).

### A3. All six FPC connectors face the wrong way — cable exits point away from their mating connectors **[A]**
Hirose convention verified: cable enters/exits the **front = contact-pad side = local −Y** (contacts protrude past the front face; front silk open = slot; FH12 "Actuator method: Front"; FH41-68S "Front, Front Flip Shield").
- FPC101 (rot90 @65.6,92.5): contacts x62.6 → exit **−x**, away from the x70 seam ✗
- FPC102 (rot−90 @73.5,92.5): contacts x76.5 → exit **+x**, board interior ✗
- FPC103 (rot90 @294.6,92.5): exit −x interior ✗ · FPC104 (rot−90 @303.6,92.5): exit +x interior ✗
- FPC105 (rot180 @123.5,6.5): contacts y8.35 → exit **+y = interior**, not the y=0 seam ✗
- FPC106 (rot0 @30,54): exit −y, away from the BMS top edge ✗

Each seam pair's exits point *away from each other* — physically impossible for a straight FFC. Root cause: `verification/PHASE4A_FPC_WIRING_2026-08-30.md:100` states "the FH12's FPC enters from the +y side" — **inverted**; the Phase-4a "fix" rotated a correct FPC105/FPC106 pair into a wrong one. In-repo cross-check: the radio-daughterboard reference pair is correctly mated (carrier J2300 rot0 exit −y ↔ radio_daughterboard.kicad_pcb J1 rot180 @(80,86) exit +y).

### A4. FH41-68S footprint: all 14 SH (shield/ground) pads are in the wrong places, and the count is wrong **[V]** (pads read directly; datasheet via agent, Hirose catalog D31607_en, 68-position row)
`ducktop2.pretty/Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal.kicad_mod`:
- **Actual:** 14 SH pads at x = ±1.25, ±3.75, ±6.25, ±8.75, ±11.25, ±13.75, ±16.25 (y=+2.7, 0.3×1.2).
- **Datasheet:** ground contacts **G = 13** at 2.5 mm pitch, span **E = 30.0 mm**; odd count → center-symmetric: **x = 0, ±2.5, ±5.0, ±7.5, ±10.0, ±12.5, ±15.0**.
- **Delta:** every SH pad 1.25 mm off; **no pad at x=0**; the two outermost real terminals (±15.0) have no land → shield return unsolderable/open, bridge risk.
- Root cause: `gen/generate_fh41_68s_footprint.py:31` — `SCALE = 2.0` linear extrapolation from the FH41-30S (G=6, even → offset pattern correct only for even counts); parity never switched for odd G=13.
- **Fix:** 13 SH pads at x = 0, ±2.5·k (k=0…6), y=2.7, 0.3×1.2.
- Everything else correct: signal pads 1…68 at −16.75+0.5(n−1), y=−2.975, 0.30×0.65 (span 33.5 = catalog D ✓); MP ×2 at ±18.0, +2.275, 0.40×1.55 (span 36 = catalog J ✓); fab body ±19.0 (=38 mm ✓ catalog C); courtyard ±20.0×±3.8; pad-1 mark ✓.

### A5. BQ77915 protector is shorted out by design (FPC-3 pins 3/4 → center GND) **[V]** (rename + board nets verified; circuit analysis by agent)
BMS circuit per-datasheet: PACK_NEG_RAW → RS11 8 mΩ shunt → Q703 (DSG) → Q704 (CHG) back-to-back common-drain → FG_VSS → FPC106.7; SRP/SRN across the shunt; symbol `Q_NMOS_123S_4G_5678D` (1-3 S / 4 G / 5-8 D) matches CSD18540Q5B; 3S strapping correct. **But** `CENTER_RENAME = {"PACK_NEG_RAW": "GND"}` (fpc_contract.py:81) ties FPC-3 pins 3/4 to center GND (confirmed on boards: FPC105.3/4 = GND; FPC106.3/4 = PACK_NEG_RAW) — a parallel return that **bypasses the protector FET chain**: during an OCD/short trip, fault current keeps flowing via pins 3/4. Architecture self-contradictory: the LTC4368 ground reference (cable pins 9–30 → center GND) *requires* that same bond. One topology must change.

### A6. Gauge shunt bypassed; fuel gauge dead as-built **[A]** + one verified contributor **[V]**
U10 BQ34Z100-G1 wired per datasheet (VSS = FG_VSS; RS1 5 mΩ to GND; divider R180 220k / R181 16.5k / R182 100 Ω from the protected PACK_POS_FUSED — correct rail; 53 µA; 0.575–0.884 V at BAT — sane for 3S). Killers:
- A5's pack−↔GND bond bypasses RS1 → coulomb counting fiction.
- **[V]** `R180.1` on the center board is wired to `/Power & Battery/BAT_PROT_VIN` — a net with **exactly 1 pad on the whole board** (stale pre-split name; schematic says R180.1 = `/PACK_POS_FUSED`). The divider measures nothing. `BAT_PROT_VIN` is the only stale board net on the center board.
- The gauge also dies in ship mode / system-off (REGIN + CE from MCU_3V3).

### A7. Right USB-C port can never charge **[A]**
Right board U721 (TPS26630) OUT (pins 17/18) = PD2_VBUS_GATED = {C2091, D2090} — dead end; the left board's selector U14 V2 (pin 16) is fed by a *local* net with no conductor from the right board (FPC-2 carries only PD2_VBUS_RAW, which on center goes only to OR-diode D713 → EC-AON). Only the left port (U41 PPHV → U720 → U14 V1 → Q15/Q16 → FPC101.15 → center U15 → Q21/Q22 → VBUS_COMBINED → U2) and the AUX input can charge.

### A8. FPC-3 pack conductors ~4× overloaded when charging **[A]** (arithmetic from schematic values)
FH12-30S = 0.5 A/pin. Pack = 2 pins/rail = **1 A**. Charger input limit: R17 47k / R190 100k from REGN → V_ILIM = 3.401 V → IINDPM = 3.00 A → pack current ≈ **4.1–4.4 A** (20 V PDO → 3S). Discharge side: LTC4368 breaker 4.545 A (50 mV / 11 mΩ ✓) and 10 A pack fuse F1 — both >4× the cable. Protection ordering inverted — cable (1 A) < breaker (4.5 A) < fuse (10 A) — nothing protects the cable. (Positive: pack fuse F1 is physically on the BMS before the connector — "PACK_POS_FUSED" is truthful on the BMS side **[A]**.)

### A9. FPC-1/FPC-2 power pins overloaded **[V]** (pin counts read from contract/boards)
- PD1_VBUS_RAW = **1 pin** (FPC101.11) for a 3–5 A PD input.
- USB_PD_SELECTED = **1 pin** (FPC101.15) carrying the whole charge input (~3 A).
- PD2_VBUS_RAW = **1 pin** (FPC104.13).
- AUX_DC_RAW = **1 pin** (FPC101.13) whose only fuse (F190 3 A) is on the center side — source-side segment unfused.
- VSYS = 2 pins (1 A) feeding the left board's 6 A-class USB farm (U1703 + USB7206C + 2×TPS25810 + 4×TPS2553-1.3 A).
- USB_PORT_5V = 2 pins (1 A) vs a 1.3 A branch (U1760); PCIE_3V3 = 1 pin for the RTL8111H.

### A10. Placement board-killers (center unless noted)
- **C750 vs H22** **[V]**: 8×10 mm electrolytic at (121.075,72.94) vs H22 M2.5 hole at (119.8,76.95): 4.21 mm centers vs can r4.0 + hole r1.35 → **1.14 mm of the screw hole under the can**; M2.5 head (Ø4.5) reaches 2.0 mm inside the can radius. Pre-existing on the monolith — hygiene sweep missed it.
- **Ten 0402/0603 passives inside FH41-68S bodies** (2.5 mm tall, sit on board) **[A]**: FPC103 body (x291.95–297.4, y73.5–111.5) contains R35 (295,91), C922 (294.81,74.5), C925 (296.63,77.55), R37 (293.8,108.6), R780 (293.9,104.8), C292 (297,92.5, half-in); FPC102 body (x71.1–76.15) contains R415 (74.5,97), L420 (74.5,100), C416 (74.5,103), R705 (74.5,106). All were clear on the monolithic board — the split's packer pushed them in.
- **U51 inside J30 (HDMI)** **[A]**: SSOP-8 moved (353,83.4)→(352.85,72.15); HDMI body x348.2–360.3 × y64.5–79.5; 18.2 mm² overlap.
- **U12 inside J2300** **[V]** (position verified (183,6,180)): VQFN-24 moved (28.4,100.1)→(183,6); J2300 body x178.95–197.05 × y2.8–8.4; 26.5 mm² overlap.
- **J420 × J421** **[A]**: two JST-GH SM02B at (229,4)/(232,4); fab bodies overlap **2.75 × 4.05 mm**.
- **J41 (OLED display connector) misplaced** **[V]** (position verified (218,2,90)): monolithic board and floorplan_revD both place it at (310,155) next to J45 (280,155, which still matches). Now at (218,2): courtyard overlaps the A1 module shadow **604 mm²**, H25, J420/J421 (44.5 mm² each), J901 (26.3 mm²), J310 (101–167 mm²), R391.
- **J422 (3.5 mm jack) vs SW900** **[A]**: jack THT pins at (252,8.1)/(254,9.9) inside the switch's body/pad area (60.7 mm² court overlap; `pth_inside_courtyard` ×3). C435 (3.3 mm²) and R2340 (2.2 mm²) graze the jack body.

---

## TIER B — WILL-FAIL-VERIFICATION / SERIOUS RISK

### B1. Center board zone fills are stale — copper exists outside the board **[V]**
8 of 14 `filled_polygon` blocks have points outside x∈[70,300]: In1.Cu/In3.Cu/In6.Cu **GND planes** span x0.5–357.5 (4177 pts each); In4.Cu pours: PD2_VBUS_RAW (x315–357, entirely outside), PD1_VBUS_RAW (x1–75), VSYS (x54–119), MAKER_3V3_CORE (x247–308), MCU_3V3 (x270–306). 5 of the 11 "isolated zone islands" are these boundary-crossing stale fills. Root cause: `generate_split_boards.py:1670-1672` refills *before* `inject_outline_text` swaps in the 70–300 outline. Fab gerbers would contain pour copper past the board edge / over hinge cutouts.

### B2. The net-class system is non-functional on left/right/bms (and partially on center) **[V]**
`net_settings.netclass_patterns` in every daughter `.kicad_pro` holds **prefixed** patterns (left_io 19, right_io 13, bms 3: `/VSYS`, `/PD1_VBUS_RAW`, `/PACK_POS_FUSED`…) while the boards' actual nets are **bare** (`VSYS` ×10…) → **0 of the inherited patterns match any real board net** — the router gets Default (0.09/0.09) for every controlled-impedance/power net on all three daughterboards. (The patterns *do* match the netlist names — the mismatch is board-side only, exactly where it matters.) Additionally: the 8 TMDS pairs (`TCP0_TX0/TX1/TXRX0/TXRX1_*`) have a DIFF_100 pattern on **neither** center nor right_io; center has ~79 stale monolith patterns among its 175 and every A1 orphan net falls to Default 0.2 mm; commit 82cd50e is cosmetically true and functionally void; d920eaa also set daughter `min_hole_to_hole=0.2` vs main/center 0.3.

### B3. The ERC claim is false — genuine errors on every project **[V]** (independent ERC runs: center 11, left 10, right 8, bms 16)
- **center:** 1 genuine — `power_pin_not_driven` U15 pin 17 [V1]; 10 lib_symbol_mismatch warnings (U311, U914–U921, U431).
- **left_io:** 5 power-flag errors (U1703.8 VIN, U1700.26 VDD33, #PWR1701, U41.38 VIN_3V3, U14.16 V2) + **3 genuine `isolated_pin_label`: HUB_PRT_CTL4 (U1700.57), HUB_DS4_DM (U1700.35), HUB_DS4_DP (U1700.34)** — downstream port 4 has no partner anywhere; the "5-port USB-C architecture" is missing a whole port's wiring.
- **right_io:** 7 errors — **genuine `pin_not_driven`: U1760 pin 3 [EN] — floating enable on the PD2 power path** — plus 6 power-flag (U42.34/38, U54.1, U55.1, U500.11 AVDD33, #PWR081).
- **bms:** 16 errors — 13 × `pin_not_connected: Hierarchical label 'PACK_x' in root sheet cannot be connected to non-existent parent sheet` (PACK_FAULT_N ×3, PACK_RETRY_PULSE ×3, MCU_3V3 ×2, PACK_POS_FUSED ×2, PACK_NEG_RAW ×2, FG_VSS ×1) + 3 power-flag. Nets do form, but bms ERC can never pass by construction.

### B4. The fabrication gate is structurally broken **[A]** + verified anchor **[V]**
- `check_release_candidate.py:26` — `DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"`: the retired 1225-footprint monolith; the duplicate-ref check and DRC default to it; no doc/tool runs the gate with `--pcb` for the split boards.
- `--stage fabrication` runs `kicad-cli pcb drc --schematic-parity` with an **empty parity allowlist** (:698): bms **182 parity issues**, left_io **402** (199 net_conflict + 199 footprint_symbol_field_mismatch missing Manufacturer + 4 extra_footprint) — boards store bare net names while schematic nets are path-prefixed.
- The 4 split boards are outside every gate: no gate DRCs them; the per-project `--project {left_io,right_io,bms}` contract gates are manual-only; `generated_schematic_drift` (:567-579) identity-checks only root `*.kicad_sch`.
- Unrouted counts: center/left/right = 499 each but **bms = 132, not 499**.

### B5. DRC claim materially understates the blocking classes **[A]**
Beyond unrouted, blocking-severity errors: **center 155** (95 courtyards_overlap, 21 pth_inside_courtyard, 5 npth_inside_courtyard, 34 copper_edge_clearance incl. actual 0.0000 mm), **left_io 42** (24 clearance at 0.18 mm vs 0.20 min), **right_io 52** (24 clearance, min 0.15 mm), bms 0.

| Board | courtyards_overlap | clearance | copper_edge | pth_in_court | npth_in_court | isolated_copper (warn) | silk (warn) | unconnected |
|---|---|---|---|---|---|---|---|---|
| center | 95 | 0 | 34 | 21 | 5 | 11 | 198 | 499 |
| left_io | 10 | 24 | 8 | 0 | 0 | 0 | 400 | 499 |
| right_io | 9 | 24 | 25 | 0 | 0 | 0 | 200 | 499 |
| bms | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 132 |

0 shorting_items, 0 hole_clearance on all boards ✓. All 48 clearance errors intra-footprint (see C10).

### B6. `fix_board_hygiene.py` zeroes the rotation of every part it moves — latent board corruptor **[V]** (code read and confirmed)
`:140` stores only (x,y); the rewrite at `:168-169` drops the rotation token → moved parts default to 0° while candidate pads were computed at the old rotation. The `anchors` dict (:56, :71-75) captures rot and is never used — dead code confirming the oversight. Compare `generate_split_boards.rewrite_at_lines:1039-1040`, which correctly writes `{nrot:g}`.

### B7. Shield pads are invisible to the schematics — re-sync strips the shield ground **[A]**
The 68-pin symbol (`gen/Conn_01x68_FFC_MP.kicad_sym`) has 68 pins + MP only — **no SH pin**. The 14 SH pads on FPC101–FPC104 are grounded only via board text. Re-sync silently strips the shield ground. (MP fine.)

### B8. No battery temperature sensing anywhere **[A]**
BQ25798 TS = fixed fake divider (R16 5.24k / R705 7.5k); BQ77915 TS tied via R853 10k to VSS. Charging with zero thermal qualification.

### B9. Mounting holes / probe headers desynced between projects **[A]**
Center schematic carries H10–H13, H15–H17, H27 but the center board has none; the same 8 refs physically exist on left_io (H10/11/12/16) and right_io (H13/15/17/27) boards while those schematics don't contain them. Plus center schematic-only J8/J50 (DNP probe headers, netted) and A2 (DFR1149 Mu module, no footprint). Any re-sync adds 8 holes to center at stale coordinates and deletes them from the daughterboards.

### B10. Code-less net convention breaks schematic-parity tooling **[A]**
All 4 boards write `(net "NAME")` with no numeric code (center: 2662 net-name refs, 0 codes). KiCad 10 parses it, but `--schematic-parity` fails wholesale (B4) and netlist round-trips are undefined.

### B11. BOM gaps on the cable-critical connectors **[A]**
FPC102, FPC103, FPC105 missing Manufacturer + MPN (`verification/release_inventory/bom_release_gaps.csv`).

### B12. FH41-68S has no valid 3D model **[A]**
No FH41 STEP exists in the KiCad 10 install at all (not even the FH41-30S the generator docstring claims to point at). 3D views render nothing for FPC101–104.

### B13. Center board nets no longer match the center schematic — the F8 trap **[A]**
Center board: 655 nets (591 prefixed); center schematic netlist: 881 nets (`/PACK_POS_FUSED`), only 508 common. Any "Update PCB from Schematic" rewrites/flags hundreds of nets. Nothing documents "never F8 this board."

### B14. FPC102/FPC104 seam-edge clearances and cut-line stragglers **[A]**
FPC102 SH pads 0.20 mm from x=70 (×14), MP 0.45 mm (×2); FPC104 SH 0.30 mm (×14) vs 0.5 mm rule. Courtyards still cross the seams (d920eaa's "0 boundary crossings" false at courtyard level). **U913** (@296.44,19.12, unmoved): right-row pads span x298.56–**300.04** (0.04 mm past x=300, ×10 pads); **C703** (@72.12,123.42, unmoved): pad1 0.07 mm from x=70.

### B15. Q25 value/footprint mismatch **[V]** (value verified "CSD17575Q3 BQ25798 ship FET"; footprint CSD19537Q3_DQG per agent)

---

## TIER C — RISK / DESIGN SMELL

1. **With A5 unfixed there is no cell over-voltage protection at all** **[A]**: LTC4368 OV = 13.57 V = 4.52 V/cell — never trips on 3S.
2. **Center U15 AUX path has only one FET (Q24)** **[A]**: PMOS body diode backfeeds VBUS_COMBINED → AUX rails. Path 1 (Q21+Q22) correct.
3. **U15 USB window divider** **[A?]**: 1M/19.6k/63.4k gives ≈16.1–21.1 V if LTC4418 ref is 1.235 V → only 20 V PDOs accepted; docs have no row for it — verify the ref.
4. **AON eFuse UV ≈ 6.2 V** (R795/796/797) **[A]** blocks 5 V-only PD sources from booting the EC.
5. **All battery power gated by LTC4368 *and* Q25** (both need power to conduct); no hard-wired fallback. SHDN polarity verified active-low — no deadlock **[A]**.
6. **FAULT pull-up R708 fed from center MCU_3V3** **[A]** → reads low when center dark; ALERT/CE same.
7. **SYS_5V is 5.21 V** (0.6 V × 8.68), not the claimed 5.10 V **[A]** — zero USB margin; doc arithmetic wrong. (All other FB dividers verified: SYS_3V3/PCIE_3V3 3.32 ✓, MU_12V 12.03 ✓, MCU_3V3 3.29 ✓, hub core 1.146 ✓.)
8. **FPC-1 SuperSpeed pairs have no home on left_io** **[A]**: every left_io receptacle is USB2-only; the full-feature USB-C ports (J40/J10) are on center. Verify intended SS termination.
9. **Wi-Fi M.2 socket J40 has no PCIe/REFCLK/I2S wired — in the schematic** **[V]**: netlist shows `unconnected-(J40-…)`; board agrees. If the chosen Wi-Fi module needs PCIe, it's dead. Document or wire.
10. **"0201/UDFN intra-footprint clearances are inherent" is half-true** **[A]**: stock IPC-nominal footprints (0.18/0.15 mm gaps), manufacturable — but the project already has the same-ref `.kicad_dru` mechanism (used for U41/U42) and never applied it to D1800–15/D2100–7, D150–157, U501/U502. Will fail the DRC gate until a rule is added.
11. **A1 (Mu socket) moat**: 38 KiCad courtyard pairs; most genuine under-module placement < 8 mm socket height; H1/H2 standoffs sanctioned by dru rule **[A]** — but "courtyard touches" understates extents (up to 604 mm²) and doesn't cover A10's items in the same shadow. J4 (TC2030, @201.3,15.5) — jig access doubtful.
12. **J2300 body vs A1 socket molding** **[A?]**: ~1.9 mm y-overlap with the socket fab strip — needs 3D confirmation.
13. **J24 (USB-A) shell over C1850** **[A?]**: 1206 at (0.7,109.85), 10.6 mm² inside the shell rect — verify against 3D.
14. **Notch-adjacent copper** **[A]**: left 8 / right 11 pads 0.30–0.45 mm from hinge-notch edges (C1843, R1716/R1707, L1701, U1702; U2011 ×5, U2016 ×3, U2012 ×2, C1771).
15. **Generator failure paths are print-only; exit code always 0** **[A]**: generate_split_boards :524, :600, :862, :960 (then *keeps the overlapping anchor*), :1723, boundary check :1694-1710; fix_board_hygiene :112,137.
16. **Second overlap pass can park parts on relocated-connector pads** **[A]** (latent; current boards 0 overlaps): CONNECTOR_KEEPOUT hardcoded around original anchors; resolve_connectors may move ±82 mm along y; connector courtyards absent from parse_courtyards(ORIG).
17. **No zone refill after the last part-moves** **[A]**: hygiene/d920eaa moves run after the only refill → stale fills on all 4 boards.
18. **Hard interpreter/path coupling** **[A]**: generate_split_boards :35-36 hardcodes the KiCad 3.9 python; fix_board_hygiene imports pcbnew unused — system python3 cannot import hygiene (verified).
19. **Mechanical geometry duplicated as magic constants in four dicts** **[A]**: REGIONS/OUTLINES/FORBIDDEN/CONNECTOR_KEEPOUT; HOLES (:66-71) hardcoded, never validated; regen requires the monolithic ducktop2.kicad_pcb to exist forever.
20. **The net-renaming "sync" is an undocumented black box** **[A]**: MCP sync rewrote net names (189 prefixed netlist names → 0 prefixed board nets) — enabling condition for A1/B2; `inherit_netclasses` only partially compensates.
21. **Per-project gates + ERC + daughterboard drift not wired into the release gate** **[A]**: check_release_candidate :598 runs the contract gate once (default project); verify_design_contracts (a) never runs ERC, (b) never checks net completeness, (c) writes `verification/*_netlist.xml` even in read-only mode.
22. **A1 socket residual** **[A]**: confirm the key notch sits on the STD (not RVS) side for the purchased socket.
23. **`${KICAD10_3DMODEL_DIR}` version-locks** model paths to KiCad 10 **[A]**.
24. **Purchasing suffix ambiguity** **[A]**: catalog (28) vs design (05) — both exist; confirm.

---

## TIER D — COSMETIC / DOC / PROCESS

1. Silk warnings: center 198, left 400, right 200, bms 54; 3 text_height items; F1 court 1.0 mm past the BMS edge.
2. 13 lib_symbol_mismatch warnings: U311, U914–U921, U431 (center); U1785, U1745 (left); U1765 (right).
3. bms root: duplicated adjacent hierarchical labels (2.54 mm apart at x=485.14); left_io port-4 labels lack no-connect flags.
4. `verification/*.xml` gitignored (`.gitignore:42`) — currently fresh (2026-08-31 10:55), not stale.
5. Seven orphaned sheet files at repo root referenced by nothing: 04_usb_c_io, 05_power_inputs, 06_tcp0_external_hdmi, 09_ham_radio, 12_keyboard_daughterboard, 13_radio_audio_codec, 16_gigabit_ethernet.
6. Dead/deceptive code: generate_split_boards :1587-1588 `or True:`, :1052 `if False`, pads_bbox SystemExit (:118-120), resolve_connectors unused params (:866), hygiene's unused rotation; strip_tracks_and_vias counts `\n\t\(segment ` (space) — KiCad 10 writes `(segment\n` → printed counts ~0 (deletion works); hygiene's "conflicts resolved" reports only the last pass; center footprint-count print uses an empty dict → "3 footprints".
7. `inherit_netclasses` rewrites daughter .kicad_pro with json.dump(indent=2) — reformat churn; silently no-ops on missing rule keys.
8. Doc drift: generate_left_io_project.py:5 "FPC-1 (75 signals)"; symbol Description "01x100"; generate_conn100_ffc_symbol.py `FFC_PINS=100` default; build_ducktop2.py:109 maps a 100-pin symbol to the 68-pad footprint (pins 69–100 padless); footprint name "1MP_1SH" vs 2 MP + 14 SH; generate_fh41_68s_footprint.py docstring vs emitted 3D path.
9. PHASE4A doc: inverted FPC-exit premise (root cause of A3) + "zones were refilled against the final placement" claim contradicted by commit order. FPC_CABLE_SPEC: stale "100-pin" references; "FH12 is top-contact" (Hirose: Bottom).
10. ELECTRICAL_CALCULATIONS_2026-08-29: no rows for gauge divider, BQ25798 ILIM/TS, LTC4418 windows, AON UV/OV, FB dividers, FPC budgets (its 15 LTC4368/BQ77915 rows verified PASS).
11. Unconditional "edge overhang (chassis, ok)" noise (:1708-1710); daughterboards have no ratnest colors.
12. Two different USB-A receptacle vendors on left_io (XKB U231-091N vs GCT USB1046).
13. 11 isolated-copper items on In4.Cu — half are artifacts of B1, not true islands.

---

## ADJUDICATED — claims that did NOT survive verification

1. **"Center FPC102/FPC103 pin maps are swapped"** — false; an artifact of the integrator's own first extraction pass. With Reference properties properly extracted, FPC102 carries the FPC-1 map and FPC103 the FPC-2 map, matching contract and schematic. **[refuted]**
2. **"J40.70/71/73 board=WIFI_3V3 vs schematic=REFCLK; J40.59/61/65-68 board=GND vs PCIe; J40.12/14 board=GND vs I2S; U10.12 board=I2C_SCL vs HDQ; A1.163/190/192/196/198 board=GND vs SPI/CSI"** — false positives from a bbox-based parse. Direct block scans: those board pads have **no net**, and the netlist NC'd them (`unconnected-(…)`). Board and schematic agree. Residue: C9 (J40's PCIe/REFCLK/I2S deliberately unwired). **[refuted]**
3. **"bms U719.15/19/21 board-wired to PACK_NEG_RAW/BMS_PRES, shorting CBO into PRES"** — false. Netlist: 15 (LPWR), 19 (VTB), 21 (CBO) `unconnected-(…)`; board pads carry no net; 22 = BMS_PRES both sides. Board, schematic, and the gate's expectation agree. **[refuted]**
4. **"left/right/bms netclass patterns match 100%"** vs **"0 match"** — both partially right: patterns match the *netlist* names (prefixed) but not the *board pad* nets (bare). Router works from the board → effectively 0 matches (B2). **[reconciled]**
5. **"Rotate all six FPC connectors 180°" vs "rotate one per pair"** — rotating all six fixes only exit directions (relative rotations stay opposite → reversal remains). Complete fix: one connector per pair (see A2). **[reconciled]**
6. **"Mounting holes moved by design (H12/H27)"** — false: all 15 holes at identical coordinates vs the monolith (L4/C7/R4/B0). **[refuted]**

## CLAIMS VERIFIED TRUE

- Board outlines exactly 230×185 (x70–300), 70×185, 58×185 (x300–358), 60×60; seams share the global frame; hinge-notch geometry matches the split spec; no pads inside hinge notches (≤0.75 mm courtyard grazes only).
- 0 shorting_items, 0 hole/drill violations on all boards.
- Footprint counts 710/266/163/46; no duplicate refs; no unannotated refs; 0 B.Cu footprints; 8 center DNPs documented; excludes = H*/TP*/Tag-Connect/J58 only.
- All six FPC connectors match fpc_contract.py pin-for-pin on the boards; cross-board net identity per conductor; MP pads GND ×6; FPC-1 pins 1–53 / FPC-2 pins 1–61 / remainder GND; FPC-3 pins 1–8 signals, 9–30 GND; contract ↔ cable spec ↔ schematics ↔ boards consistent; FPC105 (123.5,6.5) rot180 / FPC106 (30,54) rot0 as claimed (the *relation* is the defect).
- Pack fuse F1 on the BMS before the connector; LTC4368 breaker textbook (UV/OV 8.456/13.57 V; SHDN active-low; no deadlock); BQ77915 symbol = TI TSSOP-24 pinout 1:1, per-datasheet app circuit; BQ25798 PROG 10.5 kΩ = 3S @1.5 MHz, ILIM = 3.00 A exactly, power stage present; power tree complete (no dead-end rails, no double-driven rails); all other FB dividers correct.
- Hierarchical labels ↔ sheet pins 1:1 for the FPC sheets; FPC net-direction convention (all-bidirectional) consistent.
- verification/*_netlist.xml fresh.
- verify_design_contracts --schematic-only passes ×4; check_release_candidate --stage schematic PASSES (3 non-blocking BOM gaps) — and is genuinely strict for what it looks at.
- fpc_contract.py is the genuine pin-map SSOT (every consumer imports it; no duplicated pin-map dict; assign_connector_pad_nets hard-fails on unknown pads).
- Generator determinism real (uuid5 seeds, no time/random, byte-identical re-runs); pcbnew mutation confined to fresh subprocesses.
- M.2 J10 courtyard clean (0.02 mm² roundoff); E-key/M-key sockets properly standoffed; HDMI/GbE/battery connectors plausible (Mega-Fit 7.5 A/contact; JXD1-1022NL mid-mount, magnetics local to right_io).
- Mu socket A1 footprint matches the official Mu spec; standoffs match.

## OPEN / NOT INDEPENDENTLY VERIFIED

- LTC4418 reference voltage (C3).
- J2300 molding vs A1 socket (C12) — needs 3D.
- USB-A shell over C1850 (C13) — needs 3D.
- Whether J40's PCIe-less Wi-Fi wiring is intentional (C9).
- Q25 footprint pad compatibility (B15).
- left_io U1700 pin 3/4 vs 5 discrepancy (agent parse produced false positives elsewhere; treat as unverified — the ERC isolated_pin_label findings independently confirm port-4 problems).
- The "395 BOARD-EXTRA pads" class in general: partially real (FPC SH pads confirmed); a rigorous pad-level re-diff warranted before trusting individual items.

## RECOMMENDED FIX ORDER

1. A2/A3 — rotate FPC102/FPC104/FPC105 by 180°.
2. A1 — per-project net-name mapping; board pad-net gate.
3. A4 — regenerate FH41-68S footprint (13 SH pads).
4. A5/A6 — pack−↔GND architecture; fix R180's stale board net.
5. A7/A8/A9 — route PD2 charge power; derate/repin power conductors; fuse the AUX source segment.
6. B8 — pack thermistors.
7. A10/B1/B14 — placement sweep + zone refill against the final outline.
8. B2/B6/B4 — netclass normalization; hygiene rotation; fabrication gate points at the real boards; wire per-project gates + ERC in.
9. B7/B12 — SH pin in symbol; 3D models.
10. C/D — as time permits; correct the docs.
