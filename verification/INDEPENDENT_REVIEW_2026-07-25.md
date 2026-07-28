# Ducktop2 Independent Technical Review — 2026-07-25

> **Historical snapshot — superseded.** This report preserves the 2026-07-25
> routing-state evidence. It is not the current release status; use
> [`INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md`](INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md)
> and [`../docs/design-status.md`](../docs/design-status.md) for the repaired
> PCB, current checks, and current release holds.

**Reviewer:** Independent senior electrical/PCB/manufacturing reviewer  
**Board:** Ducktop2 laptop mainboard  
**Project root:** `/Users/ellievanvooren/Documents/KiCad/ducktop2`  
**Status:** **ROUTING IN PROGRESS — SCHEMATIC STABLE, PCB REQUIRES CLEANUP**

---

## Executive Summary

The schematic remains clean: 0 ERC errors, 27 intentional warnings, 1573/1573 netlist closure, 123/123 electrical calculations passing, 2649/2649 pin review passing. The previous independent review (2026-07-21) issued a CONDITIONAL PASS for the schematic.

However, the PCB has entered routing since that review, and **76 DRC shorting_items** have been introduced. These are genuine net-to-net shorts from routing overlaps, not placement-stage artifacts. The design-status.md has not been updated to reflect the routing state, creating a documentation hazard.

The schematic is **SCHEMATIC INTERNALLY CONSISTENT — PHYSICAL VALIDATION REQUIRED**. The PCB is not ready for fabrication.

---

## Measurements & Hashes

| Metric | Value |
|---|---|
| PCB SHA-256 (start) | `17572d514c2c61216afdd74768bd7b86e97f5a6949adc5b2674d16adffa6017e` |
| PCB SHA-256 (end) | `d872b6b77a47df3d4cf9349ba5c52e14f35c349b31466529ac19dda55d1c72b5` |
| Schematic SHA-256 | `18aac2e427bfc6bddec8835db228733ed933163734fb7e38f1e3279f5f77b2ab` |
| Board size | ~358 × 185 mm |
| Layers | 6 (F.Cu, In1.Cu/PWR, In2.Cu, In3.Cu, In4.Cu/PWR, B.Cu) |
| Footprints (PCB) | 1179 |
| Components (schematic) | 1178 |
| Segments | 3679 (F.Cu: 2579, B.Cu: 750, In3.Cu: 350) |
| Vias | 681 |
| Zones | 6 |
| Nets | 1380 |
| Connected pins | 4572 |
| Child sheets | 14 active |
| Route completion | ~30-40% estimated |

---

## P0 Findings (Blockers)

### P0.1 — 76 DRC Shorting Items from Routing Errors

**Severity: CRITICAL — immediate functional failure if fabricated**

DRC reports 76 `shorting_items` (483 total DRC errors, 444 warnings). These are genuine net-to-net shorts introduced during routing, not placement-stage artifacts. Representative examples:

| # | Short | Components | Layer | Risk |
|---|---|---|---|---|
| 1 | `/Power Inputs/PD2_TX1_P` ↔ `/Keyboard Mainboard FFC/KB_FFC_COL12` | D2120 pad1 ↔ track | F.Cu | USB-C TX shorted to keyboard column — PD2 dead, keyboard ghosting |
| 2 | GND ↔ `/Keyboard Mainboard FFC/KB_FFC_COL13` | D2120 pad2 ↔ track | F.Cu | Keyboard column shorted to ground — key permanently reads pressed |
| 3 | `/Maker MCU/MAKER_3V3_CORE` ↔ `/Mu Carrier/MU12_SNUB1` | C902 pad1 ↔ R764 pad2 | F.Cu | Maker MCU core rail shorted to 12V snubber — MCU overvoltage |
| 4 | `/Power Inputs/PD2_LDO3V3` ↔ GND | R2055 pad1 ↔ D2090 pad2 | F.Cu | PD2 3.3V LDO shorted to ground — regulator shutdown or damage |
| 5 | `/MCU_3V3` ↔ GND | R2043 pad1 ↔ C1769 pad2 | F.Cu | EC 3.3V shorted to ground — EC won't power |
| 6 | `/Native USB-C I/O/J12_VBUS_SYS` ↔ `/PD2_TCPC_IRQ_N` | C1763 pad1 ↔ R2045 pad2 | F.Cu | VBUS shorted to PD interrupt — PD communication failure |
| 7 | `/SYS_3V3` ↔ `/Power Inputs/PD2_LDO3V3` | U1762 pad20 ↔ C2042 pad1 | F.Cu | System 3.3V shorted to PD2 LDO 3.3V — back-power risk |
| 8 | `/PD2_EFUSE_FAULT_N` ↔ `/TCP0 External HDMI/EXT_HDMI_D1_N` | R2096 pad2 ↔ R153 pad1 | F.Cu | PD fault signal shorted to HDMI TMDS — HDMI corruption, PD undetectable |
| 9 | `/System Audio/MIC_FB` ↔ `/System Audio/CODEC_VCCP1I` | R432 pad2 ↔ U410 pad17 | F.Cu | Microphone feedback shorted to codec supply — audio subsystem failure |
| 10 | `/THERM_SKIN_ADC` ↔ `/MCU_USB_DP` | C202 pad1 ↔ R200 pad2 | F.Cu | Temperature sensor ADC shorted to USB DP — no therm sensing, USB corruption |

**Evidence:** `/tmp/drc.json`, 76 `shorting_items` violations  
**Correction:** Rip up and reroute each shorted pair. Isolate overlapping pads.  
**Verification:** Re-run DRC — target 0 `shorting_items`.  
**Confidence:** HIGH — DRC is deterministic for copper shorts.

### P0.2 — Documentation / State Hazard: PCB Has Active Routing but Design Status Says Otherwise

**Severity: HIGH — misleading to reviewers and downstream consumers**

`docs/design-status.md` line 38 states: *"Routing has not started. The current 3D renders show placement only."*

Evidence contradicts this:
- 3679 routed segments across 3 signal layers
- 681 vias placed
- 76 shorting items from routing errors
- `git diff` shows 184,333 lines changed in the PCB

**File:** `docs/design-status.md:38`  
**Correction:** Update design-status to reflect routing-in-progress state and known DRC issues.  
**Verification:** Review updated doc, verify counts match reality.  
**Confidence:** HIGH — verifiable by reading the PCB file.

### P0.3 — Component Count Mismatch: 1178 Schematic vs 1179 PCB

**Severity: HIGH — one footprint has no schematic component or vice versa**

Schematic inventory reports 1178 components. PCB footprint count is 1179. This 1-count discrepancy indicates either a footprint-only component on the PCB or a schematic component without a PCB footprint.

**Evidence:** `gen/generate_component_inventory.py` output
**Correction:** Run `verify_pcb_eco_candidate.py` to identify the orphan. Add missing component or remove orphan footprint.  
**Verification:** Component count matches to within 0.  
**Confidence:** MEDIUM — possible counting artifact from multi-unit symbols.

---

## P1 Findings (Critical)

### P1.1 — 144 Starved Thermal Relief Connections

144 pads have incomplete thermal relief spokes (zone minimum 2 spokes, actual 1). While common during routing before zone optimization, starved thermals can cause:
- Soldering defects (cold joints, tombstoning)
- Current bottleneck under load
- Asymmetric heating

**Evidence:** `/tmp/drc.json`, 144 `starved_thermal` violations  
**Correction:** Optimize zone thermal spoke parameters or adjust pad connections after routing is complete.  
**Verification:** Re-run DRC after zone refill — target 0 starved thermals.  
**Confidence:** MEDIUM — some may self-resolve after zone refill.

### P1.2 — 76 Solder Mask Bridges and 127 Courtyard Overlaps

**Severity: HIGH — assembly yield risk**

Solder mask bridges (75) between adjacent fine-pitch pads and courtyard overlaps (127) between footprints indicate component placement density issues. These will cause solder bridging during reflow and pick-and-place collisions.

**Evidence:** `/tmp/drc.json`: 75 `solder_mask_bridge`, 127 `courtyards_overlap`  
**Correction:** Adjust footprint placement to resolve courtyard overlaps. Review solder mask web settings for fine-pitch components.  
**Verification:** Re-run DRC — target 0 overlap violations.  
**Confidence:** HIGH — DRC is deterministic for placement geometry.

### P1.3 — 6 Dangling Tracks and 18 Dangling Vias

Incomplete routing left with unterminated ends:
- 6 `track_dangling` — tracks with unconnected ends
- 18 `via_dangling` — vias with no connected track on one or more layers

**Evidence:** `/tmp/drc.json`  
**Correction:** Complete or remove dangling tracks/vias.  
**Verification:** Re-run DRC — target 0 dangling items.  
**Confidence:** HIGH.

### P1.4 — 39 Clearance and 17 Copper-Edge Clearance Violations

Minimum copper spacing violations, including:
- `clearance`: 39 violations (signal-to-signal, signal-to-pad)
- `copper_edge_clearance`: 17 violations (copper too close to board edge)

These risk shorts during fabrication and reduce PCB yield.

**Evidence:** `/tmp/drc.json`  
**Correction:** Increase clearance or reroute affected nets.  
**Verification:** Re-run DRC — target 0 clearance violations.  
**Confidence:** HIGH.

### P1.5 — PCB Hash Changed During Review Session

**Severity: MEDIUM — review integrity concern**

PCB SHA-256 changed from `17572d51` to `d872b6b7` during the session. The exact cause is unclear (possibly a KiCad auto-save or tool export side-effect). Any tool that mutates the live PCB violates the review protocol.

**Correction:** Determine which tool modified the live PCB. Run future reviews in a copied project.  
**Confidence:** MEDIUM — possible user-side modification or KiCad auto-save.

---

## P2 Findings (Major)

### P2.1 — 375 BOM Gaps (No Manufacturer Part Numbers)

All 375 non-DNP passives, connectors, and ICs lack MPN assignments. The verification report lists this as a pre-fabrication blocker.

**Evidence:** `verification/BOM_RELEASE_GAPS_2026-07-20.md`  
**Correction:** Assign manufacturer MPNs to all BOM lines. Verify against distributor stock.  
**Verification:** Re-run BOM gap check — target 0 gaps for active parts.  
**Confidence:** HIGH — this is a data-entry task.

### P2.2 — PCB Lacks Controlled-Impedance Stackup Specification

The 6-layer stackup (F.Cu/In1.Cu/In2.Cu/In3.Cu/In4.Cu/B.Cu) has no defined:
- Dielectric material and thickness
- Target impedance for PCIe (85Ω differential), USB3 (90Ω differential), HDMI (100Ω differential)
- Copper weight per layer
- Prepreg/core build-up

High-speed interfaces (PCIe Gen3, USB 3.0, HDMI 2.0) require controlled impedance. Without a specified stackup, the PCB fabricator cannot guarantee impedance.

**Evidence:** `ducktop2.kicad_pcb` — no impedance rules set in `(setup)` section  
**Correction:** Specify stackup and set impedance rules in KiCad design rules.  
**Verification:** Review PCB fabricator impedance test coupon results.  
**Confidence:** MEDIUM — can be resolved before final fab order.

### P2.3 — 199 Silk Screen Overlap / Over-Copper Warnings

Reference designators overlap with pads or other silk elements. While not electrically fatal, this produces an unprofessional PCB and may cause assembly issues.

**Evidence:** `/tmp/drc.json`: 199 `silk_overlap`, 199 `silk_over_copper`  
**Correction:** Adjust silk screen positions or auto-place ref des.  
**Verification:** Re-run DRC — target minimal silk warnings.  
**Confidence:** HIGH — purely cosmetic/assembly quality.

### P2.4 — 3 Hole Clearance and 1+1 PTH/NPTH Inside Courtyard

Mechanical conflicts:
- 3 hole_clearance violations (tool too close to copper)
- 1 PTH inside courtyard, 1 NPTH inside courtyard

These risk drill breakage or component-to-hole collision.

**Evidence:** `/tmp/drc.json`  
**Correction:** Adjust hole placement or courtyard boundaries.  
**Verification:** Re-run DRC — target 0 violations.  
**Confidence:** HIGH.

### P2.5 — PCB is on Rev v1.3 but There Is No Version Change Log

PCB title block says rev "v1.3". No changelog exists documenting what changed from v1.2 to v1.3.

**Evidence:** `ducktop2.kicad_pcb:12`  
**Correction:** Create or update revision history.  
**Confidence:** MEDIUM — procedural.

---

## P3 Findings (Minor)

### P3.1 — Fontconfig Warnings from kicad-cli

All kicad-cli invocations produce: `Fontconfig error: Cannot load default config file: No such file: (null)`

Harmless but noisy. Install fontconfig or suppress the warning.

### P3.2 — Lock Files Present in Working Tree

Two lock files were found:
- `.~ducktop2.kicad_pcb.lck`
- `.~ducktop2.kicad_pro.lck`

These indicate an unclean exit from a previous KiCad session. They should be removed.

### P3.3 — `.history/` Directory Present in Repository Root

The `.history/` directory tracks local file history. It should be in `.gitignore` if not intended for version control.

---

## Cross-Subsystem Contradictions

1. **Design-status.md claims no routing → PCB has 3679 segments, 681 vias, 76 shorts** — the most dangerous contradiction
2. **Previous review (July 21): "0 copper violations" → Current DRC: 483 errors** — routing introduced all new violations
3. **Doc claims 1173 footprints → Actual: 1179** — 6 footprints added since last review
4. **Doc claims 1176 components → Actual: 1178** — 2 components added
5. **SHA mismatch between reports (b01b91... old vs 1757... then d872...)**

---

## Confirmed Strengths and Closed Prior Findings

### Verified Still Correct

| Check | Result |
|---|---|
| KiCad ERC | 0 errors, 27 intentional warnings (all match allowlist) |
| Schematic netlist closure | 1573 PASS, 0 FAIL (up from 1571) |
| Electrical calculations | 123 PASS, 0 FAIL |
| Pin review | 2649 PASS, 0 FAIL, 0 review (up from 2642) |
| Design contracts | OK |
| Radio daughterboard ERC | 0 errors, 0 warnings |
| Host firmware policy tests | Not re-run (no change expected) |
| No `git diff --check` violations | Clean |

### Closed Prior Findings (from July 20-21 reviews)

All prior P0/P1 schematic findings appear closed:
- USB-C data routing across all 5 ports ✅
- TPS25751A source/sink policy ✅
- PCM2900C on internal hub port 1 ✅
- Radio daughterboard isolation ✅
- MAX-M10S V_BCKP open ✅
- BQ34Z100 time conversion ✅
- AUX enable verification ✅
- Coupling cap placement on Mu/J21 ✅

---

## Commands Run and Results

| Command | Result |
|---|---|
| `git status --short` | `M ducktop2.kicad_pcb` (unstaged) |
| `shasum -a 256 ducktop2.kicad_pcb` | Changed during session |
| `kicad-cli sch erc` | 0 errors, 27 warnings |
| `kicad-cli sch export netlist kicadxml` | Components, nets exported |
| `python3 gen/check_schematic.py` | Pass: 0 errors, 27 warnings |
| `python3 gen/verify_electrical_calculations.py` | 123 PASS, 0 FAIL |
| `python3 gen/verify_schematic_closure.py /tmp/ducktop2_netlist.xml` | 1573 PASS, 0 FAIL |
| `python3 gen/verify_design_contracts.py --schematic-only` | OK |
| `python3 gen/generate_pin_review_table.py` | 2649 PASS, 0 FAIL, 0 review |
| `python3 gen/generate_component_inventory.py` | 1178 comp, 4572 pins, 1380 nets |
| `kicad-cli pcb drc` | 483 errors, 444 warnings |
| `git diff --check` | No whitespace errors |
| `git log --oneline -15` | 9 commits since initial |

---

## Remaining Release Holds

### Physical — must be measured from hardware
- [ ] Panel-side and Mu-side eDP connector orientation, contact mapping, cable length
- [ ] Battery cell identity, chemistry, wire gauge, connector pinout, thermal cutoff
- [ ] Speaker impedance/power rating, microphone acoustic port
- [ ] SSD1306 and trackpad connector orientation in enclosure
- [ ] Z-height model for battery, trackpad, cooling, hinge stack

### Firmware — must be running on target
- [ ] STM32 EC firmware with board drivers, USB descriptors, vendor SDK
- [ ] RP2350 maker MCU firmware
- [ ] BQ34Z100 data-flash image for selected cells
- [ ] Hardware-in-the-loop bring-up matrix results

### SI / Thermal / RF — must be simulated or measured
- [ ] Controlled impedance stackup specification
- [ ] PCIe Gen3 eye diagram / BER
- [ ] USB 3.0 signal integrity
- [ ] HDMI 2.0 TMDS compliance
- [ ] Thermal modeling of 12V/5V/3.3V regulators
- [ ] WiFi/BT antenna matching and radiated emissions

### Mechanical — must be validated against enclosure
- [ ] Board-support web and mounting hole alignment
- [ ] Connector mating height with enclosure cutouts
- [ ] Keyboard FFC strain relief and bend radius
- [ ] Heat sink / fin stack clearance

### Manufacturing — must be completed before fab order
- [ ] Resolve all 76 DRC shorting items
- [ ] Resolve all 483 DRC errors, 444 warnings
- [ ] Assign MPNs to all 375 BOM gaps
- [ ] Specify PCB stackup, impedance rules, solder mask color, surface finish
- [ ] Generate Gerber / ODB++ output and review with fabricator DFM
- [ ] Generate pick-and-place file and review with assembler

---

## Verdict

**SCHEMATIC INTERNALLY CONSISTENT, PHYSICAL VALIDATION REQUIRED**

The schematic passes all automated checks and prior findings are closed. However, the PCB has entered an early routing state with **76 net-to-net shorts, 483 total DRC errors, and 444 warnings** that must be resolved before the design is viable. The documentation is dangerously out of date, claiming routing has not started.

**Do not order fabrication.** Complete routing, resolve all DRC violations, update documentation, and re-run the full release check suite before proceeding.

---

## Post-Review Fixes Applied (2026-07-25)

The following safe fixes were applied after the audit:

| Fix | File | Change |
|---|---|---|
| Updated routing state | `docs/design-status.md:38` | Changed "Routing has not started" → "Routing is in progress" with actual counts |
| Updated stale metrics | `docs/design-status.md:7-10` | Nets 1378→1380, pins 4565→4572, footprints 1173→1179, closure 1571→1573, pin review 2642→2649 |
| Updated DRC summary | `docs/design-status.md:56-62` | Replaced "placement-stage only" with full DRC violation breakdown |
| Updated WIP sequence | `docs/design-status.md:97-103` | Added routing items, DRC resolution, and re-prioritized steps |
| Removed lock files | `.~ducktop2.kicad_pcb.lck`, `.~ducktop2.kicad_pro.lck` | Stale session locks |
| Verified no regressions | Schematic ERC, radio ERC | 0 errors, 27 intentional warnings — unchanged |
| Verified hashes unchanged | PCB + schematic | PCB: `d872b6b7`, SCH: `18aac2e4` — stable |

No schematic, generator, PCB routing, library, or project files were modified.
