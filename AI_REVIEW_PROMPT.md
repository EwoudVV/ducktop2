# Prompt For Fresh Schematic Review

You are reviewing the KiCad 10 project `ducktop2` with fresh eyes.

Project path:

```text
/Users/ellievanvooren/Documents/KiCad/ducktop2
```

Please do a critical electrical review of the generated schematic. Do not edit
files unless explicitly asked. Produce findings first, ordered by severity, with
file/line or sheet/reference evidence and a concrete fix suggestion.

Important constraints:

- Keep `ducktop2.kicad_pcb` blank. It should remain exactly 79 bytes.
- The schematic is generated; review `gen/*.py` as the source of truth and the
  generated `*.kicad_sch` files as the KiCad output.
- Read `PRE_LAYOUT_FREEZE.md` and `LAYOUT_READINESS.md`; they document the
  current physical assumptions, edge map, measurement checklist, and starter
  KiCad net classes for the first floorplan.
- Run `python3 gen/check_schematic.py` before drawing conclusions. It
  regenerates sheets, checks duplicate refs/root sheets/symbol-footprint pad
  matching/blank PCB, runs KiCad ERC, and exports a netlist.
- KiCad CLI fontconfig warnings on macOS are expected and not themselves a bug.
- DNP-valued optional parts should emit real KiCad `dnp yes` / `in_bom no`
  metadata; flag any DNP text that still generates as populated.
- Do not trust ERC alone for symbol/footprint integrity. Also look for
  symbol pin numbers that do not match footprint pads, dropped unit-0/common
  pins, 4-pad crystal pinout mistakes, and hidden ground/thermal pads that
  are not represented in the generated schematic.
- Do not recommend replacing the LattePanda Mu architecture unless you find a
  specific electrical impossibility. The goal is to refine this design.

Current feature intent:

- Compute: LattePanda Mu x86 module, powered from `VSYS`.
- Display: retained Intehill 16 inch 2560x1600 120 Hz portable monitor
  controller path over Mu DDIB HDMI 2.0, with internal USB-C power/touch feed.
- External display: user-accessible HDMI-A jack from Mu `TCP0`.
- Storage/radio: NVMe M-key x1, M.2 E-key AX210-class Wi-Fi/Bluetooth.
- USB: VL822 hub with two downstream USB-C data ports, plus internal USB2 links.
- Power: 3S Li-ion protected pack, BQ25798 charger/NVDC path, three CH224K
  USB-C PD sink inputs, shared AUX/SOLAR screw terminal with population options
  for random DC or DNP solar MPPT path. The protected-pack default separates
  `PACK_POS_RAW`, `PACK_POS_FUSED`, `PACK_NEG_RAW`, sense-only `CELL*_BAL`
  balance taps, and system `GND`; the main positive lead uses a blade-fuse
  footprint and the main negative lead returns through the low-side shunt.
  The bq76920 bare-cell AFE/balance-tap network is DNP by default.
- BQ25798 detail: no external input mux is used; `VAC1`/`VAC2` tie to
  `VBUS_COMBINED`, `ACDRV1`/`ACDRV2` go to `GND`, and unused `SDRV` has a
  1 nF capacitor to ground.
- Generator/library hygiene: project-local numbered NMOS symbols are used for
  the SOT-23 fan PWM sink and TO-252/DPAK optional power FET placeholders;
  4-pad 3225 crystals use `Crystal_GND24`; TPD4E02B04DQA common ground pad 3
  is explicitly tied to `GND`; the latest footprint audit checked 476 generated
  footprint groups with zero symbol/pad mismatches.
- Optional DNP MOSFET candidates: Q1/Q2 bare-cell battery protection FETs are
  Infineon IPD90N04S4L-04; Q3/Q4 optional BQ24650 solar buck FETs are Infineon
  IPD50N04S4L-08. Both are 40 V DPAK parts matching 1=G, 2=D/tab, 3=S. Review
  thermal copper and gate-drive losses before ever populating these DNP options.
- EC: STM32F407 EC controls keyboard, power buttons, fan, thermistors,
  backlight/display enables, OLEDs, GNSS, radios, and exposes USB HID/telemetry
  to the x86 host over Mu USB2_P3.
- Status displays: two SSD1306 I2C OLED headers on EC I2C, default addresses
  `0x3C` and `0x3D`.
- Keyboard: separate Pi 500+ keycap-compatible low-profile mechanical
  daughterboard, Gateron KS-33 target, 8x16 matrix plus EC I2C/backlight power
  over a 30-pin connector. EC scans it and enumerates as USB HID. Raspberry Pi
  documents Pi 500+ as an 84/85/88-key mechanical layout depending on regional
  variant; this design should match the user's exact keycap set. The desired
  feel is quiet/creamy, so KS-33 Silent 2.0 tactile/linear is preferred over
  the stock clicky switch type.
- Maker MCU: separate Arduino/Pico-class sandbox controller on Mu USB2_P7,
  fused 5 V, module 3.3 V, boot/reset/SWD, exposed 3.3 V GPIO.
- Radios: dual DRA818/SA818-class VHF/UHF ham modules with LPF placeholders,
  RF switch options, shared PCM2902 USB audio codec, GNSS for APRS/location.
  Default RF switch state should select the internal/PCB antenna-feed path;
  rear external SMA/u.FL connectors are the high-performance path. Treat a true
  printed 2 m PCB antenna as unrealistic unless a loaded antenna is explicitly
  selected and tested.
- Cooling: conventional copper spreader/heatpipe or vapor chamber plus quiet
  5 V PWM blower. Fan rail is fused, tach uses EC 3.3 V pull-up, PWM is an
  open-drain sink. Separate skin and Mu-heatsink NTCs go to ADC-capable EC pins.
  Peltier/TEC is intentionally excluded.

Specific review questions:

1. Are any power paths electrically unsafe or logically incomplete?
   Focus on `VSYS`, `SYS_5V`, `SYS_3V3`, charger input OR-ing, USB-C PD sink
   paths, AUX/SOLAR shared input, fuse/current limits, and PWR_FLAG usage.
2. Are the LattePanda Mu pin assignments plausible and non-conflicting?
   Check USB2_P3/P4/P5/P7, HSIO, DDIB/TCP0 HDMI, E-key, NVMe, and no-connects.
3. Are the display paths likely to support 2560x1600 at 120 Hz?
   Look for HDMI 2.0-capable parts/notes, AC coupling, DDC/HPD, ESD, and obvious
   lane/polarity omissions.
4. Are USB-C and USB hub port-control nets sane?
   Check CC handling, VBUS enable/fault, USB2/USB3 pair naming, ESD, and hub
   PE/OC wiring.
5. Are EC pin assignments electrically valid?
   Verify USB, ADC pins, open-drain-ish control needs, fan PWM/tach levels,
   thermistors, keyboard matrix count, and GPIO reuse.
6. Is the keyboard architecture good enough before the separate keyboard PCB?
   Review 8x16 matrix capacity, connector pinout, diode note, I2C/backlight
   utility pins, Pi 500+ keycap/KS-33 assumptions, and whether extra signals are
   missing.
7. Is the cooling schematic sufficient?
   Review fan fuse/current, PWM open-drain topology, tach pull-up voltage,
   thermistor dividers/filters, and whether any EC ADC nets are misassigned.
8. Are radio/GNSS/audio sections directionally safe?
   Focus on RF connector strategy, LPF placeholders, audio levels needing bench
   tuning, PTT/control polarity, RF switch truth table/default state, and GNSS
   antenna bias options.
9. Are any parts missing required pull-ups, decoupling, enable straps, reset
   defaults, crystal load values, address straps, or boot straps?
10. Are there project-generation issues?
    Check duplicate refs, local vs hierarchical labels, library tables, custom
    symbols/footprints, generated sheet list, unit-0/common pins, symbol pin
    numbers vs footprint pads, and whether edits should happen in generators
    instead of generated schematics.

Expected output format:

```text
Findings
- [P0/P1/P2/P3] file:line or sheet/ref: issue, impact, suggested fix.

Open Questions
- Only questions that block a safe schematic/layout decision.

Verification
- Commands run and result.

Overall Readiness
- One short paragraph on whether the schematic is ready for layout planning,
  and what must be fixed first.
```
