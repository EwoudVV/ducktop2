# Ducktop2 — Full Project Handoff

Generated: 2026-08-01

This document transfers complete project context so a new AI session can
continue without prior conversation history.

---

## 1. Project Overview

**Ducktop2** is a custom 16-inch x86 Linux laptop built around the LattePanda Mu
compute module (Intel N305, LPDDR5, 64 GB eMMC). It targets the flexibility and
exposed hardware of a cyberdeck without giving up the shape, portability, or
everyday usability of a normal laptop. The second iteration replaces Ducktop1's
Raspberry Pi 500+ with a purpose-built six-layer motherboard, direct eDP display,
and Cherry MX Ultra Low Profile keyboard.

### Key Hardware

| Subsystem | Implementation |
| --- | --- |
| Compute | LattePanda Mu — Intel N305, LPDDR5, 64 GB eMMC (recovery/hibernate only) |
| Display | AUO B160QAN03.K, 2560×1600 at 120 Hz, direct eDP from Mu |
| Storage | 2 TB NVMe (M.2 M-key 2280 PCIe Gen3 x4) |
| Networking | RTL8111H gigabit Ethernet, AX210-class Wi-Fi/BT (M.2 E-key 2230) |
| USB-C | 5 ports — 2 rear PD data/charge (TPS25751A, 15 V), 3 source-only data |
| Video | HDMI-A from Mu TCP0 via PS8822 redriver |
| Battery | 3S lithium-ion, BQ77915 protection, LTC4368 whole-pack, BQ25798 NVDC charger, BQ34Z100 fuel gauge |
| Charging | 2 USB-C PD ports + AUX/DC input (6–22 V nominal, 3 A fuse, TPS26630 eFuse) |
| EC | STM32F407VGT6 — power sequencing, charging, fan, keyboard scan, OLEDs, radios, lid switch, audio amp enable |
| Maker | RP2350A — independent USB device, protected GPIO, cannot touch EC or laptop systems |
| Keyboard | 65-key compact, Cherry MX Ultra Low Profile, 5×14 matrix, 30-pin FFC (REV-ALREADY FABRICATED — layout locked) |
| Trackpad | USB via J58 direct-solder (GND/D-/D+/VBUS), like normal laptop |
| Speakers | PCM2900C USB codec → TPA2012D2 Class-D amp → 2 speakers |
| Headphone | **DONE (fae06d4).** Rear 3.5 mm J422 SJ1-3535NG + U425 TPA6130A2RTJR I2C amp (sheet 15); plug-detect (HP_DETECT on U44 spare input) auto-mutes speakers via U421 AND gate. EC firmware (I2C unmute/volume, read HP_DETECT, drive AUDIO_AMP_EC_EN) remains |
| Mic | Onboard digital mic (IM68A130), works like any laptop mic |
| OLEDs | 2× SSD1306 on I2C behind TCA9548A mux (battery, source, temps, fan, radio, EC version) |
| Ham radio | DRA818V (2 m) + DRA818U (70 cm) on removable daughterboard |
| GNSS | u-blox MAX-M10S on radio daughterboard |
| Fan | STM32-controlled blower (FAN_PWM on PE9/TIM1_CH1, FAN_TACH on PC5) |

### User Context

**Ellie** is the hardware developer. Communicates in plain language. Expects
normal laptop behavior from all user-facing features. Don't ask unnecessary
questions — ask only when genuinely needed. Prefer proposed defaults over
open-ended questions. Always update the todo list, commit as work completes,
and push to origin every 5–10 commits.

---

## 2. How the AI Should Work

### Project Rules (from AGENTS.md — re-read after any compaction)

This is a very high stakes project. Everything matters.

- **Always know the roadmap.** Understand the full context, architecture, and goals before acting. Infer what you can; only ask if you truly can't proceed.
- **Plan before executing.** Think through each step, consider alternatives and edge cases, then execute deliberately. Never rush.
- **Be autonomous.** Don't ask for confirmation on obvious steps, small decisions, or routine things. Just do them. If you're reasonably confident about what to do, do it and show the result. Save questions for when you genuinely can't proceed without input.
- **Work carefully and thoroughly.** Check your work. Verify assumptions. Don't cut corners.
- **Take as much time as you need.** There is no time pressure. Doing it right is the only priority.

### User's Workflow Rules

1. **Always update the todo list** when starting/completing work items.
2. **Commit as work completes** — atomic commits with clear messages.
3. **Push to origin every 5–10 commits** — don't let local history diverge too far.
4. **Keep documentation current** — update design-status.md, verification records, README.md as things change.
5. **Don't touch `radio_daughterboard/radio_daughterboard.kicad_pcb`** — it has pre-existing unrelated uncommitted changes. Leave it alone.

### Communication Style

- **Plain language.** Ellie communicates in plain English, not engineering jargon. Match that style.
- **Don't over-ask.** Only ask questions when you genuinely can't proceed. Prefer proposed defaults over open-ended questions.
- **Show, don't tell.** Do the work, show the result, commit. Don't explain what you're going to do — just do it.
- **Ask first when resuming.** If you're unsure whether you remember context from a previous session, ask before acting. Ellie said: "ask first because i dont know if you remember."
- **Update docs as you go.** Don't batch documentation at the end — keep design-status.md, verification records, and README.md current throughout.

### Compaction Survival

After conversation compaction, you will receive a summary instead of the full history. To counteract this:
1. Re-read AGENTS.md (re-injected after compaction).
2. Assume the summary is incomplete. If unsure about context, **ask the user** — but only after exhausting what you can infer.
3. Do not get sloppy. Compaction is when mistakes happen. Double-check every assumption.
4. Re-establish the roadmap before taking any action after a compaction boundary.

---

## 3. User-Facing Behavior (VERIFIED 2026-07-31)

Full record: `verification/USER_FACING_BEHAVIOR_2026-07-31.md` (25 rows, all confirmed).

### Confirmed Decisions

| # | Behavior | Decision |
| --- | --- | --- |
| 1 | Lid close | Display off, Mu keeps running (NOT sleep/S3), instant resume on open. EC reads `LID_CLOSED_N` from J53 (hall/reed, R209 10k pull-up) on EC pin 41. |
| 2 | USB-C ports | All 5 are data-capable. 2 rear PD ports charge. 3 source-only don't. No USB-A. |
| 3 | Charging | Charges from PD ports AND AUX connector (6–22 V nominal). Charges when laptop is off (NVDC path). |
| 4 | Power button | Boots to desktop fast. |
| 5 | Battery | Trusted OS percentage + OLED status. BQ34Z100 gauge. State machine host-tested DONE (`ec_battery`, f223750). |
| 6 | Fan | STM32-controlled, quiet at idle, performance-biased under load, never throttles. Policy core host-tested DONE (`ec_fan`, d1396d0). |
| 7 | OLEDs | All system component status (battery %, source, temps, fan %, radio state, EC version). Content composer host-tested DONE (`ec_oled`, d95d9f2). |
| 8 | Keyboard | 65-key compact, NO F-row, NO `~ key, split spacebar. Fn layers handle F1–F10/`~/brightness/volume. **BOARD IS ALREADY FABRICATED — layout locked.** Fn keymap host-tested DONE (`ec_keymap`, d0991b3). |
| 9 | Trackpad | USB via J58 direct-solder, like normal laptop. |
| 10 | Speakers | PCM2900C → TPA2012D2 → 2 speakers. |
| 11 | Headphone jack | **DONE (2026-07-31, fae06d4).** Rear 3.5mm CUI SJ1-3535NG + TPA6130A2RTJR DirectPath I2C headphone amp; plug-detect (RN) mutes speakers via existing AUDIO_AMP_EC_EN/U421 AND gate. See `HANDOFF_HEADPHONE_JACK.md` Status. Firmware (I2C unmute/volume, read HP_DETECT) is the remaining work. |
| 12 | Onboard mic | Works like any laptop mic. |
| 13 | eMMC | 64 GB = recovery/rescue OS + hibernation image. NOT usable as RAM. Primary = 2 TB NVMe. Design + setup tooling DONE (e2c594f); execute at Mu bring-up. |
| 14 | Ethernet | RTL8111H gigabit, like normal laptop. |
| 15 | HDMI | Mu TCP0 → HDMI-A. |
| 16 | Wi-Fi/BT | AX210-class, rear antennas. |
| 17 | Ham radio | DRA818V 2 m + DRA818U 70 cm. |
| 18 | GNSS | MAX-M10S for position/APRS. |
| 19 | Maker controller | RP2350, protected GPIO, can't hurt the laptop. |
| 20 | EC updates | Dedicated USB port (SW2 BOOT0 + J70 rear USB-C). |
| 21 | Daughterboard absent | Laptop fully works without it. |

---

## 4. Current Git State

### Unpushed Commits (1 ahead of origin/main)

```
e2c594f Add eMMC recovery/hibernate setup design and tooling
```

### Dirty Files

```
 M radio_daughterboard/radio_daughterboard.kicad_pcb
```

**This is a pre-existing unrelated change. DO NOT TOUCH it.**

### Recent History (last 20)

```
e2c594f Add eMMC recovery/hibernate setup design and tooling
f223750 Add host-tested battery state machine (ec_battery)
22a966d Add host-tested lid switch debouncer (ec_lid)
d95d9f2 Add host-tested OLED status content composer (ec_oled)
d1396d0 Add host-tested EC fan policy core (ec_fan)
d0991b3 Add host-tested keyboard Fn-layer keymap (ec_keymap)
70811a2 Document headphone jack completion (verification, design-status, handoffs)
fae06d4 Add rear 3.5mm headphone jack with plug-detect speaker mute (sheet 15)
c329f95 Regenerate child schematics to sync with current generators
5a8d9c9 Add AI behavior rules to project handoff
90f3521 Full project handoff for next session
6fe853f Handoff: headphone jack implementation plan for next session
2ff5b2b Lock keyboard layout (board already fabricated), record headphone jack design
db86159 Record user-confirmed behavior expectations
fbc8981 P1.6: Add user-facing behavior verification checklist
744f320 Fix ERC + annotation issues in EC DFU programming section (08)
dc893b5 P1.5: Add EC DFU programming path: BOOT0 button + rear USB-C prog port
ab1ab99 P1.2: Add STM32F407 EC target firmware port
5fe84ee P1.3: Add power loop relocation scripts and BOM MPN assignments
cbbc6c9 Fix 3D model paths and update PCB format to KiCad 10.0
```

---

## 5. What's Done

### Schematic (14 generated child sheets, 1,184 components, 1,372 nets, 4,566 pins)

| Check | Result |
| --- | --- |
| KiCad ERC | 0 errors; 27 intentional warnings (13 library-copy + 14 grounded-pin ties) |
| Generated schematic self-check | Pass |
| Schematic design contracts | Pass |
| Independent netlist closure | 1,580 pass, 0 fail |
| Bounded electrical calculations | 123 pass, 0 fail |
| Pin review | 2,603 pass, 0 fail, 0 review |
| Mainboard duplicate references | 0 |
| User-facing behavior checklist | 25/25 rows have schematic evidence; firmware cores for rows 1/5/6/7/8/12/15 host-tested DONE |
| BOM procurement gaps | 0 |
| Host firmware policy tests | Pass on host (9 suites); 42 HIL rows NOT_RUN |

### Completed Work Items

- **08_internal_services ERC cleanup:** 7 stranded GND labels moved, #PWR2ac409aa repositioned, power symbols renamed to digit-terminated refs (#PWR2302–2308), property/instances references aligned, PWR_FLAG #FLG071 added on EC_PROG_VBUS. Commit `744f320`.
- **User-facing behavior verification:** `verification/USER_FACING_BEHAVIOR_2026-07-31.md` created with 25 rows, all confirmed. Commits `fbc8981`, `db86159`.
- **Keyboard layout locked:** Board already fabricated, layout documented, Fn layer design recorded. Commit `2ff5b2b`.
- **Headphone jack design handoff:** `HANDOFF_HEADPHONE_JACK.md` written with full implementation plan. Commit `6fe853f`.
- **EC DFU programming path:** BOOT0 button (SW2) + rear-edge USB-C prog port (J70/U70/U71/D70) added to sheet 08. Commit `dc893b5`.
- **EC target firmware port:** 17 files in `ec_target/`, compiles to 9 KB binary. Commit `ab1ab99`.
- **Power loop relocation:** BQ25798 PMID, TPS552892, LTC4368 caps/FETs moved to valid distances. Commit `5fe84ee`.
- **BOM MPN assignments:** 327 MPNs assigned (370→43 gaps). Commit `57008c8`.
- **Generation-time BOM catalog (2026-08-01):** `gen/bom_catalog.py` inverts the reviewed assignments + 2026-07-30 Murata GRM hold suggestions + MCP-verified LCSC alternates into a spec-keyed catalog stamped by `Sheet.place()`; all 378 gap refs (204 R + 174 C, incl. the 9 headphone-jack caps) now carry Manufacturer/MPN at generation time, regeneration cannot lose them again, and the release BOM gate is PASS with 0 gaps. Coverage self-test: `python3 gen/bom_catalog.py`.
- **6-layer stackup:** Committed to `ducktop2.kicad_pcb`. Commit `dc019f9`.
- **Trackpad USB fix:** J58 lands relocated, R250/R251 physical short removed, duplicate refs (U170, U2004, U2014) removed. Commit `66c243f`.
- **Rear 3.5mm headphone jack:** J422 CUI SJ1-3535NG + U425 TPA6130A2RTJR DirectPath I2C headphone amp on sheet 15, plug-detect (HP_DETECT on recovered U44 spare input) auto-mutes speakers via the existing U421 AND gate; new TPA6130A2 symbol + LIBMAP + sym-lib-table, contracts updated SOURCE_MGR_SPARE1->HP_DETECT, System Audio root block enlarged to fit new hier pins. Commits `c329f95` (stale-MPN schematic sync) + `fae06d4`.
- **Host-tested EC firmware cores (2026-07-31/08-01):** keyboard Fn layer `ec_keymap` (`d0991b3`, 22 tests), fan policy `ec_fan` (`d1396d0`, 16 tests), OLED content composer `ec_oled` (`d95d9f2`, 16 tests), lid debouncer `ec_lid` (`22a966d`, 12 tests), battery state machine `ec_battery` (`f223750`, 18 tests). All wired into `run_host_tests.sh` + `CMakeLists.txt`; all 9 host suites and the release contract pass. Target-side drivers (matrix scan, USB HID, NTC ADC, TIM1 PWM, SSD1306 I2C, PE10 ACPI events, BQ34Z100 I2C, report transport) remain.
- **eMMC recovery/hibernate design + tooling (`e2c594f`):** `software/os-theme/docs/emmc-recovery.md` (GPT layout, sizing math, boot flow, hibernate config, recovery procedures) + guarded installer `software/os-theme/install/emmc-recovery-setup.sh` (`--check`/`--dry-run`, refuses non-eMMC/mounted/running-root devices; `--configure-hibernate`). Execute at Mu bring-up.

---

## 6. What's NOT Done

### High Priority (Next Session) — all five items are now DONE (host-tested cores; target-side work remains)

1. **Headphone jack — DONE (fae06d4).** Schematic on sheet 15 (J422 SJ1-3535NG + U425 TPA6130A2RTJR + HP_DETECT on U44 spare input); EC firmware (I2C enable/unmute/volume, read HP_DETECT, drive AUDIO_AMP_EC_EN) is the remaining work. See `HANDOFF_HEADPHONE_JACK.md` Status section.
2. **Keyboard Fn-layer firmware — DONE (d0991b3).** Host-tested `ec_keymap` core (F1–F10, `~, Delete, brightness, volume; 22 tests). Target-side matrix scan + USB HID remain.
3. **Fan curve firmware — DONE (d1396d0).** Host-tested `ec_fan` core (quiet idle, performance-biased, never throttles; 16 tests). Target-side NTC ADC + PWM write remain.
4. **OLED content firmware — DONE (d95d9f2).** Host-tested `ec_oled` content composer (2×8 lines, all system component status; 16 tests). Target-side SSD1306 I2C + glyph rasterisation remain.
5. **Lid behavior firmware/ACPI — DONE (22a966d).** Host-tested `ec_lid` debouncer (30 ms, one-shot ACPI edges; 12 tests). Target-side PE10 read + ACPI event forwarding remain.

### Medium Priority

- Battery reporting firmware/ACPI — **DONE (f223750)** host-tested `ec_battery` state machine (UNKNOWN/NOT_PRESENT/DISCHARGING/CHARGING/FULL with hysteresis, 18 tests); target-side BQ34Z100 I2C + report transport to Mu OS `power_supply` remains
- eMMC role: recovery/rescue OS + hibernation image setup — **DONE (e2c594f)** design + guarded setup script (`software/os-theme/docs/emmc-recovery.md`, `install/emmc-recovery-setup.sh`); execute at Mu bring-up
- Documentation updates — **DONE (2026-08-01)** full sweep: README, design-status, handoff, verification summary, firmware README/status, dated records
- Complete BOM/orderable BOM (0 gaps; generator-stamped, see gen/bom_catalog.py)

### Lower Priority / Blocked

- HDMI/PCIe/NVMe high-speed routing and SI on final stackup (routing not done)
- eDP harness (cable, panel endpoint, 40-wire map)
- Keyboard FFC cable retention
- J58 trackpad cable retention
- RF/antenna tuning
- Speaker/AUX acoustic measurements
- Thermal modeling
- Enclosure/mechanical integration
- Host firmware policy tests (42 HIL rows NOT_RUN)
- Clean DRC on mainboard (1,404 violations baseline)

---

## 7. Key Architecture Decisions

- **EC owns everything:** power sequencing, charging, fan, keyboard scan, OLEDs, radio enables, lid switch, audio amp enable. The EC is the single source of truth for laptop behavior.
- **RP2350 is separate:** maker controller, protected GPIO, can't touch EC or laptop systems. It appears as its own USB device.
- **Hardware defaults OFF:** sources/loads OFF until firmware runs (fail-safe OFF philosophy). EC commit_force_safe() is the first meaningful I2C transaction.
- **AMP_ENABLE = DAC_SSPND AND AUDIO_AMP_EC_EN:** EC already controls speaker amp via pin 43. The AND gate (U421) gates on both codec suspend and EC enable.
- **EC pin map:** pins 1–85 are assigned. Pins 86–100 are free (HP_DETECT will use one). See `gen/generate_ec_mcu_sheet.py` lines 26–67.
- **Generated schematics:** all 14 child sheets are Python-generated from `gen/`. Never edit `.kicad_sch` files directly — always change the generator.
- **Schematic is SCHEMATIC BLOCKED:** internally consistent under checks, but not fab-ready (routing, SI, battery, mechanical, procurement, HIL all still block).

---

## 8. Project Structure

```
/Users/ellievanvooren/Documents/kicad/ducktop2/
├── ducktop2.kicad_pro              # KiCad 10 project
├── ducktop2.kicad_sch              # Root schematic (hierarchical, 14 children)
├── ducktop2.kicad_pcb              # Mainboard PCB (6-layer, 358×185mm, routing in progress)
├── 01_power_battery.kicad_sch      # (generated) BQ77915, LTC4368, BQ25798, BQ34Z100
├── 02_ec_mcu.kicad_sch             # (generated) STM32F407 + crystals + SWD + DFU
├── 03_mu_carrier.kicad_sch         # (generated) LattePanda Mu, eDP, HDMI, NVMe, Wi-Fi, Ethernet
├── 04_usb_c_io.kicad_sch           # (generated) 5 USB-C ports, USB7206C hub
├── 05_power_inputs.kicad_sch       # (generated) TPS25751A PD, AUX/DC, eFuses, source selection
├── 06_tcp0_external_hdmi.kicad_sch # (generated) Mu TCP0 → HDMI-A via PS8822
├── 07_keyboard_interface.kicad_sch # (generated) FFC connector, keyboard matrix
├── 08_internal_services.kicad_sch  # (generated) EC DFU prog port (J70), always-on rail, source manager
├── 09_ham_radio.kicad_sch          # (generated) DRA818V/U, LPF, RF switch
├── 10_gnss_daughterboard.kicad_sch # (generated) MAX-M10S, antenna
├── 12_keyboard_daughterboard.kicad_sch  # (generated) 65-key matrix
├── 13_radio_daughterboard_core.kicad_sch    # (generated) radio DB core
├── 14_maker_mcu.kicad_sch          # (generated) RP2350A
├── 15_system_audio.kicad_sch       # (generated) USB2512B, PCM2900C, TPA2012D2, mic — HEADPHONE JACK GOES HERE
├── 16_gigabit_ethernet.kicad_sch   # (generated) RTL8111H
├── 12_keyboard_daughterboard.kicad_pcb  # Keyboard PCB (separate project, REV-ALREADY FABRICATED)
├── radio_daughterboard/            # Removable VHF/UHF + GNSS + radio audio board
│   ├── radio_daughterboard.kicad_pcb    # (has unrelated uncommitted changes — DO NOT TOUCH)
│   └── README.md
├── gen/                            # Schematic generators + local symbols
│   ├── generate_mu_carrier_sheet.py     # MAIN BUILD ENTRY POINT (regenerates all child sheets)
│   ├── generate_system_audio_sheet.py   # WHERE HEADPHONE JACK GOES
│   ├── generate_ec_mcu_sheet.py         # EC pin map (pins 1-85 assigned, 86-100 free)
│   ├── build_ducktop2.py                # Sheet class, lib_symbols embedding
│   ├── genlib.py                        # LIBMAP + load_renamed_symbol
│   ├── check_release_candidate.py       # Staged schematic release check
│   ├── verify_*.py                      # Various verification scripts
│   ├── *.kicad_sym                      # Local custom symbols (TPA2012D2, PCM2900C, etc.)
│   └── [50+ generator/verifier scripts]
├── firmware/                       # EC and maker-controller firmware
│   ├── ec/                         # Policy core (host-tested, complete)
│   ├── ec_target/                  # STM32 target port (17 files, compiles to 9KB)
│   ├── maker/                      # RP2350 maker policy
│   ├── tests/                      # Host tests + HIL matrix
│   └── target_port_status.md       # Full target port roadmap and status
├── docs/                           # Architecture, status, renders
│   ├── hardware.md                 # Full hardware architecture
│   ├── design-status.md            # Current design status (updated 2026-08-01)
│   ├── build-and-verify.md         # Build/verification commands
│   ├── review-prompt.md            # Independent review prompt
│   ├── display-direct-edp.md       # eDP panel/cable work
│   ├── mechanical.md               # Mechanical measurements
│   ├── ducktop1.md                 # Background on v1
│   ├── exports/                    # Schematic PDFs
│   └── images/                     # PCB renders, architecture diagram
├── verification/                   # Checks and evidence
│   ├── USER_FACING_BEHAVIOR_2026-07-31.md  # 25-row behavior checklist (VERIFIED)
│   ├── COMPREHENSIVE_REVIEW_2026-07-30.md  # Full hardware review
│   ├── INDEPENDENT_REVIEW_2026-07-27_*.md  # Post-fix audits
│   ├── SCHEMATIC_CLOSURE_*.md      # Netlist closure evidence
│   ├── PIN_BY_PIN_REVIEW_*.md      # Pin classification
│   ├── ELECTRICAL_CALCULATIONS_*.md # Bounded calculations
│   ├── BOM_MPN_ASSIGNMENTS.md      # 327 assigned MPNs
│   └── [40+ verification files]
├── mechanical/                     # Dimensions, floorplans, retention
├── manufacturing/                  # Keyboard rev-A production package
├── software/                       # OS theme work
├── HANDOFF_HEADPHONE_JACK.md       # Headphone jack implementation plan
├── HANDOFF_PROJECT.md              # THIS FILE
└── README.md                       # Project overview
```

### Key Generator Relationships

```
gen/generate_mu_carrier_sheet.py    ← MAIN ENTRY POINT (regenerates all)
  ├── generate_power_sheet.py           (01_power_battery)
  ├── generate_ec_mcu_sheet.py          (02_ec_mcu)
  ├── generate_mu_carrier.py            (03_mu_carrier)
  ├── generate_usb_c_io_sheet.py        (04_usb_c_io)
  ├── generate_power_inputs_sheet.py    (05_power_inputs)
  ├── generate_tcp0_external_hdmi_sheet.py (06_tcp0)
  ├── generate_keyboard_interface_sheet.py (07_keyboard_interface)
  ├── generate_internal_services_sheet.py  (08_internal_services)
  ├── generate_ham_radio_sheet.py       (09_ham_radio)
  ├── generate_gnss_daughterboard_sheet.py (10_gnss)
  ├── generate_keyboard_daughterboard_sheet.py (12_keyboard)
  ├── generate_radio_daughterboard_core_sheet.py (13_radio_db_core)
  ├── generate_maker_mcu_sheet.py       (14_maker_mcu)
  ├── generate_system_audio_sheet.py    (15_system_audio) ← HEADPHONE JACK TARGET
  └── generate_ethernet_sheet.py        (16_gigabit_ethernet)
```

---

## 9. How to Run Checks

### Regenerate Schematics

```sh
python3 gen/generate_mu_carrier_sheet.py
```

### Release Candidate Check (preferred)

```sh
python3 gen/check_release_candidate.py --stage schematic
```

### KiCad ERC

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc \
  --format json --severity-all --output /tmp/erc.json ducktop2.kicad_sch
```

(fontconfig noise in stderr is harmless)

### Netlist Export

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist \
  --output /tmp/net.xml ducktop2.kicad_sch
```

### Firmware Policy Tests

```sh
sh firmware/tools/run_host_tests.sh
```

### Compile-Check Generators

```sh
python3 -m compileall -q gen
```

### PCB DRC

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc \
  --format json --output /tmp/ducktop2-drc.json ducktop2.kicad_pcb
```

### PCB Render

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb render \
  -o docs/images/ducktop2-pcb-top.png \
  -w 2400 -h 1500 --side top --background opaque \
  --quality basic --zoom 1.28 ducktop2.kicad_pcb
```

---

## 10. EC Pin Map (STM32F407VGTx LQFP-100)

Full assignment in `gen/generate_ec_mcu_sheet.py` lines 26–67 and
`firmware/target_port_status.md`.

### Assigned Pins (1–85, 89–100)

| Pin Range | Function |
| --- | --- |
| 1–5 | KB_ROW2–KB_ROW6 |
| 6 | MCU_3V3 (power) |
| 7 | SOURCE_MGR_INT_N |
| 8–9 | LSE_IN/OUT (32.768 kHz) |
| 10 | GND |
| 11 | MCU_3V3 |
| 12–13 | HSE_IN/OUT (8 MHz) |
| 14 | NRST |
| 15–16 | KB_RGB_PWR_EN, KB_RGB_FAULT_N |
| 17–18 | RADIO_VHF/UHF_RF_SEL |
| 19–22 | MCU_3V3 |
| 23 | MU_PWRBTN_N |
| 24–26 | BQ_ALERT, CHG_INT_N, PMIC_QON_ASSERT |
| 27–28 | GND, MCU_3V3 |
| 29 | CHG_ENABLE |
| 30 | MU_RSTBTN_N |
| 31–32 | AUX_DC_ADC, THERM_SKIN_ADC |
| 33 | PD1_VALID_N |
| 34 | FAN_TACH |
| 35 | THERM_MU_ADC |
| 36 | TRACKPAD_FAULT_N |
| 37 | PD2_VALID_N |
| 38 | KB_ROW7 |
| 39 | PD1_TCPC_IRQ_N |
| 40 | FAN_PWM |
| 41 | LID_CLOSED_N |
| 42–43 | AUDIO_MIC_EN, AUDIO_AMP_EC_EN |
| 44–46 | MU_12V_ENABLE, MU_S0_HIGH, MU_12V_PG |
| 47–48 | RADIO_VHF_UART_TX/RX |
| 49 | VCAP1 |
| 50 | MCU_3V3 |
| 51 | SERVICE_MUX_RESET_REQ_N |
| 52–53 | GNSS_RESET_N, GNSS_PPS |
| 54 | RADIO_VHF_PTT_N |
| 55–61 | KB_COL8–KB_COL14 |
| 62 | KB_RGB_DATA_3V3 |
| 63–64 | RADIO_UHF_UART_TX/RX |
| 65–66 | RADIO_UHF_PTT_N, RADIO_VHF_PD_N |
| 67 | WIFI_W_DISABLE1_N_EC |
| 68–69 | GNSS_UART_TX/RX |
| 70–71 | MCU_USB_DM/DP |
| 72–73 | SWDIO, VCAP2 |
| 74–75 | GND, MCU_3V3 |
| 76 | SWCLK |
| 77 | WIFI_W_DISABLE2_N_EC |
| 78 | RADIO_UHF_PD_N |
| 79–80 | RADIO_VHF/UHF_SQL |
| 81–85 | KB_COL0–KB_COL4 |

### Assigned Pins (89–100)

| Pin | Signal |
| --- | --- |
| 89 | INTERNAL_USB_VBUS_FAULT_N |
| 90 | PD2_TCPC_IRQ_N |
| 91 | RADIO_DB_PWR_EN |
| 92–93 | I2C_SCL, I2C_SDA |
| 94 | BOOT0_NET |
| 95 | GNSS_EXTINT |
| 96 | PD_PROTECT_FAULT_N |
| 97–98 | KB_ROW0, KB_ROW1 |
| 99 | GND |
| 100 | MCU_3V3 |

### Free Pins (available for HP_DETECT and future use)

Pins **86–88** are currently assigned to KB_COL5–KB_COL7. However, the EC
pin map generator shows these are keyboard columns. The truly free GPIO pins
must be identified from the STM32F407VGTx LQFP-100 pinout — check which
physical pins correspond to unused GPIO ports. The `HANDOFF_HEADPHONE_JACK.md`
suggests pin 86+ range, but verify against the actual STM32F407 pin/port
mapping before assigning HP_DETECT.

---

## 11. Headphone Jack — DONE (schematic); EC firmware remains

Full handoff: `HANDOFF_HEADPHONE_JACK.md`

### Summary

- **DONE (2026-07-31, fae06d4):** rear 3.5 mm stereo jack (CUI SJ1-3535NG) on
  the rear edge + TPA6130A2RTJR headphone amp + plug-detect on sheet 15
- **Where:** `gen/generate_system_audio_sheet.py` (sheet 15)
- **Detect:** RN ring-normal contact + 100k pullup to MCU_3V3 → HP_DETECT → EC U44 spare input
- **Mute:** EC firmware drives AUDIO_AMP_EC_EN low → existing AND gate (U421) mutes speakers
- **Amp:** TPA6130A2RTJR from PCM2900C line-out via 1µF coupling, capless output to jack T/R; /SD tied to MU_HOST_ACTIVE (S0-only)
- **Remaining:** EC firmware — I2C unmute/volume, read HP_DETECT, drive AUDIO_AMP_EC_EN

### Implementation Steps (from handoff doc) — steps 1–8 complete

- TPA6130A2 and TPA2012D2 share DAC_VOUT_L/R — avoid doubling the load
- Pin review table and verify_design_contracts.py reference TPA2012D2 hardcoded nets — may need updating
- Power symbol refs start at 1500 on sheet 15 — don't collide
- Audio ground is local per sheet

---

## 12. Schematic Generator Architecture

All child sheets are generated by Python scripts in `gen/`. The key files:

### `gen/build_ducktop2.py`

- Defines the `Sheet` class that generates KiCad schematic s-expressions
- `Sheet._use_symbol()` → `genlib.load_renamed_symbol()` → checks `gen/{name}.kicad_sym` first, then stock libs
- `lib_symbols` are embedded per sheet (line ~371)
- Defines `FOOTPRINTS` dict mapping logical names to KiCad footprint paths

### `gen/genlib.py`

- `LIBMAP` dict: maps symbol name → KiCad stock library name (lines 16–100+)
- `STOCK_SYMBOL_DIRS`: searches KICAD10_SYMBOL_DIR, KICAD_SYMBOL_DIR, KiCad.app paths
- `load_renamed_symbol()`: loads a symbol, renames it, embeds it

### `gen/generate_mu_carrier_sheet.py`

- **MAIN BUILD ENTRY POINT** — regenerates all 14 child sheets
- Call: `python3 gen/generate_mu_carrier_sheet.py`
- After regeneration, inspect `git diff` before updating PCB

### `gen/check_release_candidate.py`

- Copies project to temp dir, runs generators + ERC + checks
- Verifies live source didn't change
- Call: `python3 gen/check_release_candidate.py --stage schematic`

---

## 13. Documentation Index

### docs/

| File | Contents |
| --- | --- |
| `hardware.md` | Full hardware architecture (compute, power, I/O, controllers, audio, radio) |
| `design-status.md` | Current design status, release boundary, work-in-progress (updated 2026-08-01) |
| `build-and-verify.md` | Build commands, ERC, netlist, firmware tests, PCB checks |
| `review-prompt.md` | Independent review prompt (4-reviewer framework) |
| `display-direct-edp.md` | Direct eDP panel and cable work |
| `mechanical.md` | Mechanical measurements |
| `ducktop1.md` | Background on v1 |
| `exports/` | Schematic PDFs |
| `images/` | PCB renders, architecture diagram |

### verification/

| File | Contents |
| --- | --- |
| `USER_FACING_BEHAVIOR_2026-07-31.md` | 25-row behavior checklist (VERIFIED) |
| `COMPREHENSIVE_REVIEW_2026-07-30.md` | Full hardware review (9 P1 items: 3 closed, 1 handed off, 3 resolved, 2 open) |
| `INDEPENDENT_REVIEW_2026-07-27_*.md` | Post-fix audits |
| `SCHEMATIC_CLOSURE_*.md` | Netlist closure evidence |
| `PIN_BY_PIN_REVIEW_*.md` | Pin classification |
| `ELECTRICAL_CALCULATIONS_*.md` | Bounded threshold/current/power/timing calculations |
| `BOM_MPN_ASSIGNMENTS.md` | 2026-07-30 hold suggestions; superseded by the generation-time catalog `gen/bom_catalog.py` (378 refs, 0 gaps) |
| `INVENTORY_MANIFEST_*.md` | Component inventory |
| `SCHEMATIC_TO_PCB_ECO_*.md` | Reference/footprint/net parity |
| `KEYBOARD_FFC_ASSEMBLY_CONTRACT_*.md` | Keyboard cable orientation |
| `MECHANICAL_RETENTION_VALIDATION_*.md` | Mu, M.2, mainboard retention |

### firmware/

| File | Contents |
| --- | --- |
| `target_port_status.md` | Full target port roadmap, 15-step plan, file inventory |
| `ec/` | Policy core (host-tested, complete) |
| `ec_target/` | STM32 target port (17 files, compiles to 9 KB) |
| `maker/` | RP2350 maker policy |

---

## 14. Open Design Questions

1. ~~**Headphone jack mute:** EC-driven firmware mute vs hardware-only?~~ **RESOLVED (fae06d4):** firmware — EC drives AUDIO_AMP_EC_EN low via the existing U421 AND gate.
2. **TPA6130A2 gain setting:** Check datasheet G0/G1 pin configuration. Must match PCM2900C line-out level. (Gain pins landed per datasheet default; audible level check is first-article work.)
3. ~~**TPA6130A2 SHUTDOWN pin:** Tie always-on or EC-controlled?~~ **RESOLVED (fae06d4):** /SD tied to MU_HOST_ACTIVE (S0-only, ~0.4 uA in S3); amp powers up muted with outputs disabled.
4. ~~**eMMC use:** Recovery/rescue OS + hibernation image (64 GB can hold 32 GB RAM hibernate).~~ **RESOLVED (e2c594f):** GPT layout with auto-sized hibernate swap; design + guarded setup script in `software/os-theme/`.
5. ~~**F-key layout:** Standard 65% Fn layers.~~ **RESOLVED:** user confirmed; implemented host-tested in `ec_keymap` (d0991b3). Board is fabricated.
6. ~~**OLED content:** Exact fields.~~ **RESOLVED (d95d9f2):** spec implemented in `ec_oled` (left power/battery, right thermal/fan/system, dashes on invalid).
7. ~~**Fan curve thresholds.**~~ **RESOLVED (d1396d0):** 40/45C hysteresis, 45→70C linear 30→100%, 100% ≥70C, throttle_imminent at 80C; thermal model remains a first-article refinement.
8. **BQ25798/BQ34Z100 I2C bus:** Verify if on EC I2C1 or separate bus. Needs PCB netlist verification.
9. **FAN_TACH (PC5):** Not a timer input on STM32F407. Consider timer capture pin if RPM measurement needed.
10. **Mu PL1/PL2:** Must be locked in BIOS. TPS552892 12V rail has only 4.58W headroom.

---

## 15. Critical Warnings

1. **DO NOT edit generated `.kicad_sch` files directly.** Always change the generator in `gen/` and regenerate.
2. **DO NOT touch `radio_daughterboard/radio_daughterboard.kicad_pcb`** — pre-existing unrelated changes.
3. **The keyboard PCB is already fabricated.** Layout is locked. No physical changes possible — only firmware Fn-layer assignments.
4. **KiCad 10.0.4** is the reference version. Open `ducktop2.kicad_pro`.
5. **The mainboard is NOT ready for fabrication.** SCHEMATIC BLOCKED verdict. Routing, SI, battery, mechanical, procurement, and HIL all still block.
6. **Lithium-ion packs, USB-C power paths, RF transmitters, and high-current rails** can damage hardware or cause injury when assembled incorrectly.
7. **After regenerating schematics**, always inspect `git diff` before committing.
8. **Zone refills** must run in a copied board first; merge only reviewed diffs into the live PCB.
