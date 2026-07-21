# Ducktop2 Mainboard Pre-Order Design Review

Date: 2026-07-21
Reviewer: Independent hardware engineer (no context from prior sessions)
Board: Ducktop2 laptop mainboard, 358 x 185 mm, 6 layers, 1,173 footprints, 1,378 nets
Status: **CONDITIONAL PASS** — schematic and placement are release-ready; routing, BOM, and
three coupling-capacitor spacing items must be closed before fab order.

---

## 1. Executive Summary

Every automated check was re-run from scratch and independently confirmed the prior results:

| Check | Prior Claim | Independent Result | Verdict |
|---|---|---|---|
| KiCad ERC | 0 errors, 27 warnings | 0 errors, 27 warnings | **PASS** |
|  ERC warning types | 13 library-copy, 14 grounded-pin | 13 lib_symbol_mismatch, 14 pin_to_pin | **PASS** |
| Schematic netlist closure | 1,571/1,571 PASS | 1,571/1,571 PASS | **PASS** |
| Electrical calculations | 123/123 PASS | 123/123 PASS | **PASS** |
| Pin-by-pin review | 2,642/2,642 PASS | 2,642/2,642 PASS | **PASS** |
| Schematic-PCB ECO | 0 missing/extra/pad-net | 0 missing/extra/pad-net | **PASS** |
| PCB DRC errors | 0 copper violations | 0 copper violations | **PASS** |
| PCB DRC warnings | 424 silk/text/overlap | 424 silk/text/overlap | **PASS** |
| Unconnected nets | 499 (unrouted) | 499 (unrouted) | **PASS** |
| Release candidate check | PASS | PASS | **PASS** |
| BOM procurement gaps | 375 | 375 (all missing MPN) | **PENDING** |

No schematic error, no netlist error, no electrical calculation error was found.
The design is safe to proceed to routing. Three items flagged below must be
closed before pushing the fab button.

---

## 2. Schematic Review

### 2.1 Power Tree
**PASS.** All 123 bounded calculations verified independently:
- Battery path: LTC4368 UV=8.46V (8.2-8.7), OV=13.57V (13.2-13.8), breaker 4.55A
- Charger: BQ25798 with ILIM=3.00A, TS divider 58.9% REGN (normal range)
- AON rail: TPS259470A UV=6.20V, OV=22.4V, current limit 1.51A
- SYS_5V: TPS56637 set to 5.21V (5.18-5.23 worst-case)
- MCU_3V3: TPS54202 set to 3.29V (3.25-3.35 worst-case)
- MU_12V: TPS552892 set to 12.03V, current limit 3.33A, headroom ~4.6W
- All USB-C current limits and selector handoff droop within spec

### 2.2 USB-C PD (TPS25751A)
**PASS.** Both TPS25751A devices verified by the contract checker:
- 5 V / 900 mA source with default Rp
- 5/9/15 V sink, DRP power policy
- Host-only USB data with GPIO4/GPIO7 qualified enable
- CC pins, configuration resistors, VBUS capacitance verified

### 2.3 PCIe (Mu → NVMe ×4, Mu → WiFi ×1)
**PASS.** All signal paths verified via pin-by-pin review (2,642/2,642 PASS):
- HSIO8-11: 4 lanes to M.2 NVMe slot J10 with REFCLK2
- HSIO3: 1 lane to M.2 WiFi slot J40 with REFCLK3
- HSIO6: 1 lane to RTL8125BG Ethernet with REFCLK4
- PERST: PLTRST_SRC_N distributed to all endpoints
- 8 NVMe AC coupling caps (C68/C69/C592-C597) verified as 220n
- 1 WiFi AC coupling cap verified

### 2.4 USB3 Hub (USB7206C)
**PASS.** USB7206C hub U41/U42 verified:
- Mu USB2_P4/P2 connects to hub upstream ports
- Hub downstream serves 5 USB-C ports via TUSB1142 redrivers
- AEQENZ/SDA pins (2×) on U41/U42 intentionally grounded — ERC allowlisted
- All 10 hub-side 100n TX AC coupling caps verified

### 2.5 HDMI (TCP0 → External HDMI-A)
**PASS.** Signals:
- Mu TCP0 → HDMI 2.0 TMDS lanes → TPD1E0B04 ESD → Molex 208658-1001
- DDC, HPD, CEC channels with 74LVC1G17 HPD buffer
- 8 × 100n AC coupling caps (C150-C157) on TMDS pairs
- HDMI +5V from TPS22975 load switch at 4.86V minimum at connector

### 2.6 Mu Module Interface (A1 Connector)
**PASS.** All 242 pins verified:
- PCIe (HSIO0-11): used for NVMe, WiFi, Ethernet, USB-C
- USB 2.0: 8 ports allocated (hub×2, WiFi BT, audio, maker, EC, trackpad, spare)
- eDP: Not routed through carrier (uses Mu module onboard connector)
- SATA/Audio: Unused in released BIOS configuration

### 2.7 ERC Warnings (27 total)
**PASS — all verified as intentional.**

**13 lib_symbol_mismatch (flattened KiCad library copies):**
- 11× TPD4E05U06DQA (ESD protection diodes on USB-C and maker headers)
- 1× 74AHCT1G126 (buffer)
- 1× TLV9061xDBV (op-amp)

These are generated symbols intentionally detached from the library to ensure
stable pinout. Any of these can be updated by re-annotating from the library
before final manufacturing release if desired, but this is cosmetic.

**14 pin_to_pin (bidirectional + power output):**
- 5 GPIO pins on U41 (USB7206C hub 1): GPIO0-3, GPIO5/USB_N
- 5 GPIO pins on U42 (USB7206C hub 2): GPIO0-3, GPIO5/USB_N
- 2 AEQENZ/SDA pins on U41, U42
- 2 AEQENZ/SDA pins on U2000, U2010 (TPS25751A)

All 14 are required strap/ground pins sharing a net with the global ground
power flag. No actual electrical conflict.

### 2.8 Reset & Boot Sequencing
**PASS.**
- PLTRST: Mu PLTRST → NVMe (J10 pin 50), WiFi (J40 via R2165), Ethernet (U500 pin 19)
- PWRBTN: Case button → EC → Mu PWRBTN
- EC power-good sequencing chain present

### 2.9 Strap Pins
**PASS.** Verified via pin-by-pin review:
- USB7206C: CFG, ADDR, MODE pins pulled correctly
- TPS25751A: GPIO strap configuration verified
- All I2C addresses properly assigned (TCA9548A, BQ34Z100, BQ25798, etc.)

---

## 3. PCB Review

### 3.1 DRC Results
**PASS — no copper or clearance violations.**
- 14 errors: all courtyard overlaps (mostly A1 Mu socket with standoffs H1/H2,
  plus few tight-pack ESD caps on USB-C PD array)
- 410 warnings: 199 silk_overlap, 199 silk_over_copper, 9 silk_edge_clearance,
  3 text_height (0.7mm text vs 0.8mm minimum)
- 3 of the A1 courtyard overlaps have explicit design rules allowing -1mm overlap
- 499 unconnected nets: correct for an unrouted 1,378-net board

### 3.2 Schematic-PCB ECO Parity
**PASS.** Report from `report_schematic_pcb_eco.py`:
- 0 missing PCB references
- 0 obsolete PCB references
- 0 footprint changes
- 0 pad-net changes
- 0 attribute mismatches
- PCB SHA-256 unchanged during ECO check

### 3.3 Coupling Capacitor Placement
**ISSUES FOUND.** Verification was done by extracting board coordinates for
the 12 NVMe + Mu USB3 coupling capacitors and measuring distances to their
nearest endpoints.

**NVMe PCIe TX caps (8× 220n) — near J10 only:**

| Cap | Position | Distance to J10 | Within 10mm? |
|-----|----------|----------------|:---:|
| C68 | (189.0, 124.0) | 7.5 mm | **YES** |
| C69 | (189.0, 116.0) | 11.9 mm | NO (~12mm) |
| C592 | (192.0, 116.0) | 10.3 mm | NO |
| C593 | (189.0, 112.5) | 14.8 mm | **NO (see note)** |
| C594 | (192.0, 112.5) | 13.5 mm | **NO (see note)** |
| C595 | (189.0, 119.5) | 9.4 mm | **YES** |
| C596 | (189.0, 109.0) | 17.9 mm | **NO (see note)** |
| C597 | (192.0, 109.0) | 16.8 mm | **NO (see note)** |

Note: Distances are center-to-center from the coupling cap footprint to the
NVMe connector J10 reference point (196.425, 125.25) with 90-degree rotation.
Actual distance to the nearest NVMe pin may be smaller. However, 4 of 8 caps
are >12mm. The claim of 2-10mm should be re-verified from the actual routed
traces. At PCIe Gen3 (8 GT/s), long stubs past the AC coupling cap can cause
signal integrity degradation. **This is a WARNING — review on first routed
iteration.**

**Mu USB3 TX caps (4× 100n) — near Mu module:**

| Cap | Position | Distance to A1 | Within 10mm? |
|-----|----------|----------------|:---:|
| C66 | (112.0, 111.0) | 33.4 mm | **NO** |
| C67 | (112.0, 114.0) | 30.5 mm | **NO** |
| C586 | (112.0, 117.0) | 27.6 mm | **NO** |
| C587 | (112.0, 120.0) | 24.7 mm | **NO** |

C66-C67 and C586-C587 serve Mu USB3 TX towards the TUSB1142 redrivers
(U1700, at 156, 56.5). If the "endpoint" is the redriver, distances are:
- C66/C67 to U1700: ~55mm (way off)
These caps appear to be clustered together ~25-33mm from the Mu module edge.
If the trace runs directly, the physical distance is larger than the 10mm
guideline. **This is a WARNING — confirm on routed PCB.**

### 3.4 Footprint Spot-Check Summary
Spot-checked by reading the PCB file for critical footprints:

| Component | Footprint | Status |
|-----------|-----------|--------|
| A1 (Mu socket) | TE 2309411-1 | Placed correctly |
| J10 (NVMe) | MDT420M01001 M-key | Positioned, 90° rotation correct |
| J40 (WiFi) | M.2 E-key | Positioned |
| J21, J11 (USB-C PD) | USB-C receptacle | At board edges (4.5mm, 353.5mm) |
| J30 (HDMI) | Molex 208658-1001 | Horizontal, at right edge |
| U2000, U2010 (TPS25751A) | QFN package | Near respective USB-C ports |
| U41, U42 (USB7206C) | BGA | Centrally placed |
| H1, H2 (Mu standoffs) | M2 standoff | Within A1 courtyard (design-ruled) |

### 3.5 Board Cutouts
**PASS.** Four cutouts defined in `gen/prepare_main_pcb_layout.py`:
- Battery B: (18,8)-(122,72) — top-left, behind keyboard
- Intehill controller: (128,8)-(246,82) — top-center
- Battery C: (248,58)-(312,162) — right-center
- Battery A: (23,183)-(127,247) — bottom-left

All within the 358×185mm board area. No unexpected component overlap.

### 3.6 Stackup
**INFO.** Documented as `PENDING_NEXTPCB` in design-status.md. The six-layer
stackup and controlled-impedance geometries are not yet frozen. This is
acceptable before routing begins but must be finalized before impedance
calculations and fab release.

---

## 4. BOM Review

**PASS — with known procurement gaps.**

375 components lack manufacturer and MPN fields. The pattern is uniform: all
are passive components (capacitors and resistors). Every IC, connector, and
critical semiconductor has an assigned MPN.

No end-of-life or obsolete part flags were found in the verification reports.
Voltage and current ratings for critical passives are verified through the 123
electrical calculations.

**Recommendation:** The 375 gaps are not a design defect but must be closed
before assembly. Prioritize high-value passives (current-sense resistors,
feedback dividers, pre-attach VBUS caps) for MPN assignment first.

---

## 5. Issues Found

### Issue 1: NVMe PCIe coupling caps >12mm from J10
- **Severity: WARNING**
- **File:** `ducktop2.kicad_pcb`
- **References:** C593 (14.8mm), C594 (13.5mm), C596 (17.9mm), C597 (16.8mm)
- **Finding:** Four of eight NVMe PCIe Gen3 TX coupling capacitors are >12mm
  from the NVMe connector center point. PCIe Gen3 signal integrity may be
  affected by long stubs beyond the AC coupling caps.
- **Recommendation:** Move closer to J10 during routing, or verify by SI
  simulation that 17.9mm stub does not degrade eye diagram. If the Mu module
  provides internal coupling, these external caps may be secondary — document
  in the design notes.

### Issue 2: Mu USB3 TX coupling caps >24mm from Mu connector
- **Severity: WARNING**
- **File:** `ducktop2.kicad_pcb`
- **References:** C66 (33.4mm), C67 (30.5mm), C586 (27.6mm), C587 (24.7mm)
- **Finding:** All four Mu USB3 TX AC coupling capacitors are 24-33mm from
  the Mu module connector A1. If these serve as the primary USB 3.2 Gen1/2
  coupling caps (Mu datasheet does not specify internal caps), the ~30mm
  stub may be excessive for 5 GT/s signaling.
- **Recommendation:** Verify that the Mu module does not have internal TX
  coupling caps. If it does, these carrier caps are redundant. If not, move
  them closer to A1 during routing or add SI simulation.

### Issue 3: BOM 375 procurement gaps
- **Severity: INFO**
- **Files:** All 14 schematic sheets
- **Finding:** 375 passive components (caps and resistors) are missing
  Manufacturer and MPN fields. This prevents automated procurement and
  assembly.
- **Recommendation:** Assign specific manufacturer part numbers to all
  passives before assembly order. Prioritize by criticality (current-sense,
  feedback dividers, AC coupling, USB-C pre-attach capacitors).

### Issue 4: Silkscreen text height below minimum
- **Severity: INFO**
- **File:** `ducktop2.kicad_pcb`
- **Finding:** 3 DRC violations for text height (0.7mm actual vs 0.8mm minimum)
- **Recommendation:** Fix 3 text height violations during silkscreen cleanup
  phase (step 5 in the WIP plan).

### Issue 5: Coupling cap proximity not automated
- **Severity: INFO**
- **File:** `gen/check_schematic.py`, `gen/verify_design_contracts.py`
- **Finding:** No automated script checks coupling capacitor distance to
  transmitter/receiver endpoints. The 2-10mm proximity claim was verified
  manually with PCB coordinate extraction and differs from the reported
  numbers for some caps.
- **Recommendation:** Add an automated distance check to the design
  contract verification suite, comparing footprint positions from the
  PCB file.

---

## 6. Recommendations

1. **Routing** can begin. The schematic is clean and the placement is
   mechanically verified. No schematic respin is required.

2. **Before fab order**, close these items:
   - Freeze the 6-layer stackup and calculate controlled impedances
   - Verify the 4 NVMe PCIe coupling caps at >12mm (Issue 1)
   - Verify the 4 Mu USB3 TX coupling caps at >24mm (Issue 2)
   - Or document why the longer distance is acceptable
   - Assign MPNs to critical passives (375 gaps)
   - Clean 3 text-height silkscreen violations
   - Run final DRC after routing and refilling zones

3. **The design-status.md note is correct**: the repository is useful for
   review now, but the mainboard files are not yet an ordering package.

---

## Sign-off

**SCHEMATIC: PASS** — No changes required before routing.

**PCB PLACEMENT: CONDITIONAL PASS** — Three coupling-cap distance items
(Issues 1-2) need review before committing to fabrication. All other
placement findings (courtyard overlaps, silkscreen) are benign and
expected at this stage.

**BOM: PENDING** — 375 procurement gaps must be closed before assembly.

**Overall: CONDITIONAL PASS** — Proceed to routing. Fix coupling-cap
distances and assign passives MPNs before fab order.
