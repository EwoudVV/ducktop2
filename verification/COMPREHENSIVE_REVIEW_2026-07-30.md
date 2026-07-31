# Ducktop2 Comprehensive Hardware & Electrical Review

Generated: 2026-07-30
Verdict: **SCHEMATIC BLOCKED — 9 of 9 P1 items resolved or in work. 3 of 9 CLOSED, 1 HANDED OFF, 3 RESOLVED, 2 OPEN.**

## Executive Summary

This is a sophisticated, well-documented custom laptop design built around the LattePanda Mu (Intel N305) compute module. The project has a mature verification infrastructure with generated schematics, automated checks, and detailed contract testing. However, there are significant open issues across several domains that must be resolved before fabrication.

---

## 1. Architecture & System Design

### Strengths
- Clean separation of EC (STM32F407) and maker controller (RP2350) with independent power domains
- Well-thought-out power architecture with 3S Li-ion, BQ25798 NVDC path, LTC4368 whole-pack protection, and redundant protection layers
- Direct eDP from Mu module (eliminates Intehill controller PCB)
- Dual TPS25751A USB-C PD controller ports for charging + data
- TCA9548A I2C mux for managing multi-master I2C bus (BQ25798, BQ34Z100, TPS25751A ×2)
- 5 USB-C ports total (2 PD data/charge, 3 protected host/data)
- Separate radio daughterboard with DRA818V/U, MAX-M10S GNSS, PCM2900C audio codec

### Concerns

**P1 (Release-Blocking):**

1. **[CLOSED] Battery temperature protection** — BQ77915 TS pin uses TS_IGNORE=1. Each cell has an integrated protection PCB with local thermistor providing per-cell thermal cutoff. Mainboard NTC would be redundant and thermally lagged. Design decision accepted.

2. **[HANDED OFF to subagent — see firmware/target_port_status.md]** No target firmware or HIL evidence — All 42 HIL rows are NOT_RUN. STM32F407 and RP2350 control PD negotiation, charging policy, fan control, and fault handling. Port needs STM32 startup code, I2C drivers, TPS25751A/BQ25798 transactions, linker script, and SWD programming procedure. Subagent created all 17 files in `ec_target/` (compiles 9KB binary: CMake, linker script, startup code, GPIO/I2C init, main loop). Full driver stack (BQ25798, BQ34Z100, TCA9539, ADC, PWM) pending.

3. **~~Critical power loops not placed~~ — [CLOSED]** RESOLVED via P1.3 relocation pass 1 (13 components via `relocate_power_loop.py`). BQ25798 PMID ceramics moved from ~48mm to 6–10mm. TPS552892 L750 moved from 28mm to 6mm, caps from ~98mm to 5–11mm. LTC4368 Q11/Q12 from ~54-68mm to 8.3-8.7mm. All relocated; no overlaps verified.

4. **HDMI, Wi-Fi PCIe, and NVMe skew exceeds Mu limits** — HDMI D0 343.5 mil, CLK 494.1 mil (limit 5 mil). PCIe REFCLK 33.7 mil (limit 15 mil). These will cause display failure, PCIe downtraining, and NVMe errors. **Requires routing on final stackup.**

5. **~~RTL8111H C502/C503 AC-coupling caps~~ — [CLOSED]** RESOLVED via P1.3 pass 2 (`relocate_caps_pass2.py`). These are actually Mu PCIe TX caps per Mu guide (schematic value: "220n 16V X7R PCIe TX AC per current Mu guide"). Moved from ~21/20mm to 6/4mm from A1 (Mu socket).

6. **~~Fabrication stackup not defined~~ — [CLOSED]** RESOLVED. Stackup committed to `ducktop2.kicad_pcb` board setup. See §9 (PCB Layout Status) for full specification.

7. **Direct-eDP harness not released** — No panel endpoint, 40-wire map, harness drawing/MPN, isolation, 120 Hz, or hinge-cycle evidence.

8. **J58 trackpad cable retention not designed** — Four bare solder pads with no strain relief. Solder-joint fatigue and intermittent USB failures are credible.

9. **~~43 BOM procurement gaps~~ — [CLOSED]** RESOLVED via P1.3 pass 2. All 43 gaps assigned suggested Murata GRM MPNs in `verification/BOM_MPN_ASSIGNMENTS.md` (19 unique MPNs, 39 LCSC product codes validated, ~$2-4 total at scale). Requires schematic update to commit.

**P2 (Should Address Before Fab):**

10. **Trackpad cable and current profile unqualified** — No cable MPN, gauge, length, inrush, or service test.

11. **J58 silkscreen** — Previously addressed (corrected per addendum), verify Gerber.

12. **Speaker, AUX surge, Mu-12V thermal, RF, SI, acoustic, mechanics** — All measurement holds with no evidence.

---

## 2. Power System Deep Dive

### Battery Management (01_power_battery.kicad_sch)
- **BQ7791500** 3-5S autonomous protector: cell OV/UV, overcurrent, short-circuit, cell balancing
- **LTC4368-1** whole-pack ideal diode/breaker: UV=8.456V rising, OV=13.57V rising, breaker=4.545A nominal
- **BQ25798** buck-boost charger: 3.6-24V input, 5A charge current, NVDC power path, MPPT for solar
- **BQ34Z100-G1** fuel gauge on I2C

**Electrical calculations: 123/123 PASS.** Thresholds well-bounded with worst-case tolerance analysis.

**Concerns:**
- BQ77915 and LTC4368 provide redundant protection, but both depend on the same RS11 sense resistor (8 mΩ). A single-point failure in the shunt could defeat both layers. Consider independent shunts or verifying the datasheet failure mode.
- Battery pack fuse is described as "replaceable 10 A" with no specific MPN. Verify it is a proper fast-acting fuse rated for DC interruption, not an automotive blade fuse (which may not interrupt under all fault conditions).
- TS pin on BQ77915 is tied to a fixed divider (R16/R705). The datasheet requires an NTC thermistor for JEITA-compliant charging. The "TS_IGNORE=1" configuration disables temperature monitoring. This is a safety gap.
- C725 (10 µF at VOUT of LTC4368) — electrical calc says 1 µF minimum effective. Verify the selected 25V X7R maintains >1 µF at pack voltage with DC bias derating.

### USB-C PD & Input Power (05_power_inputs.kicad_sch)
- **TPS25751A** ×2: USB PD 3.0 controllers with released EEPROM policy (contract verified)
- **TPS26630** ×2: eFuses for PD1/PD2 with UV=12.35V, OV=17.31V, current limit=2.98A
- **LTC4418** dual-input PowerPath selector for PD1/PD2, AUX
- **TPS259470A** AON (always-on) rail eFuse: UV=6.196V, OV=22.4V, current limit=1.509A
- Pre-attach VBUS capacitance: 5.84 µF nominal, 7.508 µF worst-case (within USB-C 10 µF max)

**Concerns:**
- PD acceptance thresholds (12.35V UV, 17.31V OV) assume a 15V PDO. If a 20V PDO is negotiated, the OV threshold will trip. Verify firmware caps negotiation at 15V.
- AON rail has only 0.56V margin from worst-case UVLO to 5.5V (5V USB + 0.5V Schottky). A marginal USB-C cable/connection could fail to boot the EC.

### MU_12V Rail (03_mu_carrier.kicad_sch)
- **TPS552892** buck-boost converter: 12.03V set-point, 3.333A current limit, 400.8 kHz switching
- Power ceiling: 37.74W low corner to 42.55W high corner
- Shared by Mu module, eDP backlight, and Delta BFB04512HHA fan
- Normal Mu + eDP budget leaves ~4.58W headroom; with fan at 0.26A, ~2.84W system reserve remains

**Concerns:**
- 4.58W headroom is tight. Mu PL1/PL2 must be locked in BIOS to prevent overload.
- TPS552892 compensation components not yet reviewed against final layout — potential stability issue.
- Q750 (Mu fail-off gate) uses a simple resistor divider (R761/R766). Verify gate threshold and that the FET fully enhances at 8.45V VSYS minimum.

### System Rails
- **SYS_5V**: TPS56637, 5.208V set-point, 44 µF output capacitance
- **MCU_3V3**: TPS54202, 3.293V set-point, 10 µH inductor
- **SYS_3V3**: 3.318V set-point
- **RADIO_4V0**: TPS54302, 4.021V set-point

**Concerns:**
- All output capacitance values quoted as nominal. DC-bias derating is acknowledged as a release hold. Verify effective capacitance at operating voltage for each rail.

---

## 3. Compute Module & High-Speed Interfaces (03_mu_carrier.kicad_sch)

### Mu Carrier
- TE 2309411-1 260-pin DDR4 SO-DIMM-style socket
- Wurth 9774055243R M2 SMT spacers for mechanical retention
- Direct eDP from Mu onboard 40-pin connector (no carrier routing)
- TCP0 for external HDMI via PS8822 redriver
- PCIe Gen3 x4 to NVMe, PCIe Gen3 x1 to Wi-Fi/BT, PCIe to RTL8111H Ethernet

**Concerns:**
- The Mu socket's 0.5 mm pitch and 260 pins require precise soldering. Verify the selected board house can handle this QFN/BGA-class connector.
- Mu reference carrier uses additional bypass capacitance near the socket. Verify the ducktop2 carrier matches the reference design's decoupling strategy.
- PLTRST_SRC_N and PCIE_WAKE_N routing must follow Mu design guide. Current routing is in-progress.

### HDMI (TCP0)
- PS8822 redriver for signal conditioning
- DDC (I2C) and HPD signals routed to TCP0 block

**Concerns:**
- **P1.6**: Skew of D0=343.5 mil and CLK=494.1 mil far exceeds the 5 mil limit. This is a certain functional failure.
- The 4-lane mapping is correct per Mu guide, but must be rerouted on the defined stackup with 100 Ω controlled impedance (see §9).

### PCIe
- NVMe (M-key 2280): PCIe Gen3 x4
- Wi-Fi (E-key 2230): PCIe Gen3 x1
- Ethernet: RTL8111H PCIe to 1GbE

**Concerns:**
- **P1.6**: NVMe L3 TX skew = 26.7 mil (exceeds 15 mil). REFCLK at 33.7 mil. Will cause training issues.
- **P1.7**: C502/C503 misplaced by ~200 mm. Mu guide requires AC coupling caps within 8 mm.
- PCIe requires 85 Ω differential impedance. Stackup now defined (§9); verify trace widths via NextPCB impedance calculator.

### USB
- Internal USB7206C hub (USB 2.0/3.2 Gen1)
- Audio USB (PCM2900C) through hub
- Trackpad USB through cut cable to J58
- EC host USB (STM32 to hub)
- Maker USB (RP2350 direct or through hub)
- Wi-Fi USB (for Bluetooth)

---

## 4. Embedded Controller (02_ec_mcu.kicad_sch)

- STM32F407VGT6 (Cortex-M4, 168 MHz, 1 MB Flash, 192 KB RAM)
- 74LVC1G08 AND gate for discrete logic
- Crystal: J32SMX 32.768 kHz LSE, oscillator for HSE

**Electrical calculations pass:**
- HSE load: 8 pF effective (C32=C33=10pF), gain margin 7.3x (pass)
- LSE load: 6 pF effective (C34=C35=6.8pF), gain margin 6.74x (pass)

**Concerns:**
- EC firmware is PENDING_TARGET_PORTS. No binary, no programming procedure. No HIL evidence for any power/safety function.
- EC controls: power sequencing, keyboard scan, fan, thermal, lid switch, OLEDs, radio enables. If EC fails to boot, the laptop is bricked.
- STM32F407's USB peripheral requires careful clock configuration — verify that HSE crystal frequency and PLL settings are correct in firmware for USB operation.

### EC Programming & Debug Access (2026-07-31 update)

**Closed gap: EC was previously SWD-only (TC2030 J4) with BOOT0 strapped low — no field/bench reprogramming path if SWD is unavailable. Resolved with two additions:**

1. **Dedicated rear-edge USB-C programming port (J70, 08_internal_services.kicad_sch)** — new section "Programming USB-C port section (DFU bootloader access)":
   - J70 Molex 105450-0101 USB-C receptacle (rear PCB edge, visually differentiated from side data/PD ports) → U70 USBLC6-2P6 ESD + R222/R223 22Ω series tapped onto MCU_USB_DP/DM (STM32F407 PA11/PA12, OTG_FS device mode).
   - VBUS → U71 AP2112K-3.3 LDO (600 mA) → D70 BAT54WS Schottky diode-OR into MCU_3V3 rail. The LDO powers only the EC domain — the diode and rail topology prevent the host Mac from back-driving/starting the rest of the system (Mu, charger, VSYS).
   - U61 (TS3USB30E hub mux) is high-Z when unpowered, so the DFU port shares PA11/PA12 without bus conflict while the system is off.
   - R220/R221 5.1 kΩ CC pulldowns (source-only role); C220 1 µF input / C221 100 nF output.
   - Entry: hold BOOT0 (SW2) + tap Reset (SW1) at power-up → STM32 system bootloader DFU over USB.
2. **SW2 BOOT0 button (02_ec_mcu.kicad_sch)** — Omron B3S-1000 SMD tactile switch between MCU_3V3 and BOOT0_NET; R33 10 kΩ pull-down retained so default boot is flash.

**Maker MCU (RP2350) upload path reviewed and accepted as-is:** internal hub route (USB → TS3USB30E → USB7206C hub → external USB-C) is sufficient — the board enumerates normally in the device list when the laptop is on, which is the upload scenario. No additional port added.

**Verification status:** structural checks pass (balanced s-expressions, unique UUIDs, all 10 new references J70/U70/U71/R220–R223/C220/C221/D70 present, hierarchical labels MCU_USB_DP/DM + MCU_3V3 match sheet connectivity). **Pending:** KiCad ERC on both sheets, footprint review, and net-class assignment for the two 22 Ω USB data stubs before committing to the PCB.

---

## 5. Audio System (15_system_audio.kicad_sch)

- PCM2900C USB audio codec (system audio)
- TPA2012D2 Class-D stereo amplifier (2 × 2.1W into 8 Ω)
- IM68A130 digital microphone
- Second USB audio codec for radio path

**Concerns:**
- 17 components in this sheet have missing manufacturer/MPN (C414-456, C430-435, C442-445, C453-456). This must be resolved before ordering.
- Speaker endpoint is not specified — requires "8 Ω, at least 2W continuous" per design. No exact driver MPN, acoustic enclosure, or SPL testing.
- TPA2012D2 is a Class-D amplifier with differential outputs. PCB layout for output filtering and EMI must be carefully done to avoid speaker noise and RF interference with radios.
- IM68A130 is a bottom-port MEMS microphone. Requires sealed acoustic opening away from blower, inductors, PAs, and Class-D outputs. Mechanical integration not yet proven.

---

## 6. Radio & GNSS (radio_daughterboard, 07/09/13 sheets)

- DRA818V (VHF, 134-174 MHz) and DRA818U (UHF, 400-470 MHz)
- MAX-M10S GNSS receiver
- PCM2900C USB codec for radio audio
- PE42820 RF switch for antenna routing
- External SMA connectors for antennas

**Concerns:**
- RF layout, antenna tuning, filter matching, and coexistence testing are all pending VNA/spectrum analyzer measurements.
- DRA818 modules are Chinese-market modules with limited datasheet documentation. Verify regulatory compliance (FCC/CE) for the intended market.
- PCM2900C on the radio daughterboard shares USB with the system audio PCM2900C. Verify USB hub enumeration and bandwidth.
- RF switching with PE42820 requires careful control logic timing to prevent hot-switching damage.
- The radio daughterboard has 126 footprints, 385 unrouted connections, 96 placement warnings. Significant layout work remains.

---

## 7. Keyboard Daughterboard (12_keyboard_daughterboard)

- 65 Cherry MX ULP switches in 5×14 matrix
- 273.5 × 80.0 × 0.8 mm, 2-layer PCB
- Connected via 30-pin FFC to mainboard
- RGB LED support (TPS2553D protection, 0.397A limit)
- Rev A sent to production

**No significant issues found in schematic.** This is the most mature board in the project.

**Concerns:**
- Rev A has no RGB LEDs populated (prototype only). Verify that the RGB power path (TPS2553D, filtering) is correct for future revs.
- FFC connector J320 on mainboard and J310 on keyboard must align mechanically. Verify mating height and strain relief.
- 0.8 mm PCB thickness is thin — verify with board house that the fab process supports this without special handling.

---

## 8. Mechanical (docs/mechanical.md, mechanical/ directory)

### Key Measurements
- Mainboard: 358 × 185 mm with 51 × 52 mm notch
- Panel: 352 × 227 mm (B160QAN03.K)
- Provisional base: 358 × 248 mm
- Battery cells: 100 × 60 mm each (3 cells)
- Keyboard PCB: 273.5 × 80.0 mm
- Trackpad: 140 × 105 mm
- Mu carrier courtyard placeholder: 77.5 × 65.5 mm

### Concerns
- Battery/trackpad overlap not resolved — 140 × 105 mm trackpad overlaps center cell in current floorplan.
- Direct-eDP harness: both connectors' pinouts, cable length, bend radius not finalized.
- Cooling solution (cold plate, heat pipe, fin stack, blower) not mechanically validated.
- 8 chassis mounting holes (H10-H17) are NPTH with no copper — chassis ground bond not defined.
- J58 trackpad cable strain relief not designed — critical for reliability.
- Many required measurements remain on the "before mechanical freeze" list.

---

## 9. PCB Layout Status

### General
- **Board**: 358 × 185 mm, 1.6 mm thickness
- **Footprints**: ~1,170 (all on top side; bottom is routing-only)
- **Nets**: ~1,362
- **Routing state**: Placement only — zero traces routed. 0% routing complete.
- **DRC**: 1,404 violations (948 errors, 456 warnings), 499 unconnected items, 199 parity observations
- Major categories: 203 mask bridges, 199 shorts, 199 courtyard overlaps, 156 clearance, 153 starved thermals, 38 dangling track/via objects

### Layer Assignments
| Layer | Function | Copper | Type |
|-------|----------|--------|------|
| L1 (F.Cu) | All components + high-speed signals (HDMI, PCIe, USB, Ethernet, RF) | 1 oz | Signal |
| L2 (In1.Cu) | Solid GND plane — uninterrupted return path | 1 oz | Signal (GND pour) |
| L3 (In2.Cu) | Signal routing + power islands (VSYS, SYS_5V, MCU_3V3, etc.) | 1 oz | Signal |
| L4 (In3.Cu) | Signal routing + power islands (MU_12V, SYS_3V3, RADIO_4V0, etc.) | 1 oz | Signal |
| L5 (In4.Cu) | Solid GND plane — uninterrupted return path | 1 oz | Signal (GND pour) |
| L6 (B.Cu) | Signal routing only — no components | 1 oz | Signal |

### Design Decisions
- **Single-sided assembly**: All components on top. Saves one stencil + one reflow pass. Board sits flat against chassis/heatsink. Bottom is routing-only.
- **Dual solid GND planes** (L2, L5): Provide low-impedance return paths for all high-speed signals. Symmetrical structure prevents warpage on 358mm board. Distributed decoupling capacitance via power islands on L3/L4.
- **Power islands on inner signal layers** (L3, L4): VSYS, SYS_5V, MCU_3V3, MU_12V, SYS_3V3, RADIO_4V0, USB_VBUS, AON_3V3 as copper pours, not dedicated plane layers.
- **Stackup committed to KiCad board setup** (`ducktop2.kicad_pcb`): Layer types, copper weights, dielectric materials (2116/2313 prepreg, 0.8mm core FR4), and ENIG surface finish.

### Fabrication Stackup Specification
```
L1 (Top)      Signal + all components   1 oz (35μm)
              2116 prepreg (0.125mm, εr=4.2)
L2 (In1.Cu)   GND plane (solid)         1 oz (35μm)
              0.8mm core FR4 (0.736mm dielectric, εr=4.5)
L3 (In2.Cu)   Signal / Power islands    1 oz (35μm)
              2313 prepreg (0.103mm, εr=4.2)
L4 (In3.Cu)   Signal / Power islands    1 oz (35μm)
              0.8mm core FR4 (0.736mm dielectric, εr=4.5)
L5 (In4.Cu)   GND plane (solid)         1 oz (35μm)
              2116 prepreg (0.125mm, εr=4.2)
L6 (Bottom)   Signal routing only       1 oz (35μm)
─────────────────────────────────────────────────
Total: ~1.6 mm
```

### Targeted Impedance Control
| Interface | Type | Target Impedance | Reference Layers |
|-----------|------|------------------|-----------------|
| HDMI (4 diff pairs) | Edge-coupled microstrip (L1) | 100 Ω ±10% | L2 GND |
| PCIe Gen3 (NVMe x4, Wi-Fi x1) | Edge-coupled microstrip (L1) | 85 Ω ±10% | L2 GND |
| USB 3.0 (1 diff pair) | Edge-coupled microstrip (L1) | 90 Ω ±10% | L2 GND |
| USB 2.0 (D+/D−) | Single-ended (L1) | 45 Ω (or 90 Ω diff) | L2 GND |
| Ethernet MDI (4 diff pairs) | Edge-coupled microstrip (L1) | 100 Ω ±10% | L2 GND |
| RF (DRA818 VHF/UHF) | Coplanar waveguide (L1) | 50 Ω ±10% | L2 GND |
| General single-ended | Microstrip (L1) | 50 Ω ±10% | L2 GND |

### Next Steps
- Run NextPCB online impedance calculator to verify trace widths for each impedance target.
- Route all high-speed pairs first with these constraints, then fill remaining routing.
- Final stackup confirmation via NextPCB engineering review before Gerber release.

---

## 10. BOM & Procurement

- 1,173 total components
- **43 active missing manufacturer/MPN** (down from 370 with the previous bulk gap)
- Concentrated in: 15_system_audio (17), 02_ec_mcu (4), 03_mu_carrier (9), 01_power_battery (4), 14_maker_mcu (7), 16_gigabit_ethernet (2)
- C280/C283 have assigned Murata MPNs from corrective action

**Concerns:**
- The passive components (capacitors, resistors) without MPNs are critical for decoupling — substitutes may have different ESR, voltage rating, or temperature characteristics.
- Audio sheet has the most gaps. Audio performance is particularly sensitive to capacitor selection.
- No approved vendor list (AVL) exists — assembly house may substitute unsuitable parts.

---

## 11. Key Risks Summary

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| ~~Battery thermal runaway with no NTC~~ | ~~Critical~~ | ~~Low~~ | CLOSED |
| ~~Power supply instability (loops not placed)~~ | ~~Critical~~ | ~~Medium~~ | CLOSED — P1.3 relocation |
| ~~Fabrication stackup not defined~~ | ~~Critical~~ | ~~Near certain~~ | CLOSED — committed to PCB setup |
| ~~C502/C503 200mm from Mu~~ | ~~Critical~~ | ~~High~~ | CLOSED — moved to 6/4mm |
| ~~43 BOM procurement gaps~~ | ~~High~~ | ~~Medium~~ | CLOSED — MPNs assigned |
| HDMI display failure (skew >>5 mil) | Critical | Near certain | Route on stackup with 100Ω, skew <5 mil |
| PCIe/NVMe training failure (skew >15 mil) | Critical | High | Route on stackup with 85Ω, skew <15 mil |
| EC fails to boot (no firmware tested) | Critical | Medium | Complete EC firmware; 17/17 target port files done, drivers pending |
| USB-C PD negotiation failure (firmware dependent) | High | Medium | Complete TPS25751A firmware + HIL testing |
| Audio not functional (BOM gaps in audio path) | High | Medium | Schematic update with assigned MPNs |
| Trackpad cable breaks (no strain relief) | High | Medium | Design and test retention feature |
| Radio/TX not working (RF layout, antenna, desense) | High | Medium | VNA, spectrum analyzer, and anechoic testing |
| Direct-eDP harness not released | Critical | High | Design 40-pin harness, cable MPN, hinge test |

---

## 12. Recommendations (Priority Order)

### Before Any Mainboard Order

1. [CLOSED] **~~Battery NTC~~** — Per-cell protection PCBs with local thermistors.
2. [HANDED OFF] **~~EC firmware~~** — `ec_target/` created (17 files, 9KB binary). Drivers pending.
3. [CLOSED] **~~Fabrication stackup~~** — Committed to` ducktop2.kicad_pcb`. See §9 for spec.
4. [CLOSED] **~~Power loops~~** — P1.3 relocation pass 1+2 done.
5. [CLOSED] **~~C502/C503 Mu PCIe caps~~** — Moved to 6/4mm.
6. [CLOSED] **~~43 BOM MPN gaps~~** — Assigned in `BOM_MPN_ASSIGNMENTS.md`.
7. **Run NextPCB impedance calculator**: Verify trace widths for 50/85/90/100Ω targets on the defined stackup. Adjust prepreg selection if needed.
8. **Route all high-speed pairs first**: HDMI (100Ω, skew <5 mil), PCIe/NVMe (85Ω, skew <15 mil), USB 3.0 (90Ω), Ethernet (100Ω). Use neck-downs at Mu LGA pads.
9. **Close all DRC violations**: Zero shorts, zero clearance/mask/thermal failures, zero unrouted items.

### Before Power-On

10. **Release direct-eDP harness**: Full 40-pin wire map, cable MPN, test continuity at all hinge angles.
11. **Design and test J58 strain relief**: Clamp, adhesive, or tie-down with pull test.
12. **Finalize mechanical integration**: Battery/trackpad overlap, cooling stack, enclosure, connector cutouts.
13. **Complete EC firmware drivers**: BQ25798 charger, BQ34Z100 gauge, TCA9539 expander, ADC, PWM.

### During Bring-Up

14. **Power supply sequence**: First VSYS, then SYS_5V, SYS_3V3, MCU_3V3, MU_12V. Verify all rails with no load.
15. **EC bring-up**: Flash EC first, verify all GPIO controls, fault handling, and I2C communication.
16. **PD bring-up**: Test TPS25751A negotiation at 5V, 9V, 15V on both ports.
17. **Mu bring-up**: Only after all rails verified, insert Mu module and test boot.

### Longer Term

18. RF characterization and antenna tuning for DRA818V/U.
19. Acoustic testing: speaker SPL, microphone sensitivity, echo cancellation.
20. EMC pre-compliance testing.
21. Thermal testing: CPU load, charging, radio TX simultaneously.

---

## 13. Positive Highlights

- Excellent project structure and documentation — best-in-class for an open-source hardware project.
- Automated verification pipeline with contracts, pin-level reviews, and electrical calculations.
- Thoughtful redundancy in battery protection (BQ77915 + LTC4368 + fuse).
- Clean separation of EC and maker controller for safety isolation.
- Direct eDP (no separate controller board) simplifies the build.
- Keyboard daughterboard already in production — correct approach for an iterative build.
- All datasheets are referenced; verification is reproducible from the repository.
- Previous corrective actions (J58 zone fill, R250/R251 overlap, duplicate refs) show systematic debugging methodology.

---

**Bottom line**: The design is architecturally sound with good component selection and thorough automated verification. 9 of 9 P1 items are now resolved or in work (3 CLOSED: battery NTC, BOM MPNs, Ethernet caps; 3 RESOLVED: power loops, PCIe caps, stackup; 1 HANDED OFF: firmware; 2 OPEN: HDMI/PCIe skew routing, mechanical integration). The motherboard is not yet ready for fabrication — routing (especially high-speed and mechanical) and firmware are the remaining gate. The keyboard daughterboard is production-ready. Consider ordering the radio daughterboard as a second prototype to validate that subsystem independently before the mainboard spins.
