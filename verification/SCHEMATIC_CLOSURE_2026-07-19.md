# Ducktop2 Motherboard Schematic Closure - 2026-07-19

## Conclusion

All confirmed active motherboard schematic and electrical defects reported in the
2026-07-17 through 2026-07-19 independent reviews are closed in the canonical
generated design. Four additional, non-overlapping manual subsystem reviews found
no remaining active P0 or P1 schematic/electrical defect.

This conclusion covers the motherboard circuit design, its generated KiCad
hierarchy, current firmware safety contracts, and the component-level assumptions
that can be checked from available manufacturer documentation. It does not turn
unknown physical endpoint details into guessed schematic facts; those are listed
separately below.

## Closed Review Findings

### Findings first reported on 2026-07-17

- AUX-input `PGOOD` threshold wiring was corrected.
- TPS25810 input and connector-side bulk capacitance placement was corrected.
- HDMI +5 V delivery margin was corrected and host-active gating was added.
- PE42820 control voltage was brought within its absolute-maximum rating.
- Powered-off DRA818 UART/PTT injection paths were removed.
- Low-pack operating headroom is now bounded and checked.
- Firmware-owned charger, source-path, load, and reset-state contracts are explicit.
- Mu, M.2, and mainboard mechanical retention identities are explicit.

### Findings first reported on 2026-07-18

- CH224A I2C low-level margin was corrected.
- STM32 reset now forces all PD source paths off.
- RTL8111H/Mu PCIe coupling uses the current 220 nF contract.
- The service-mux reset path is explicit and fail-safe.
- Internal USB attachment uses physical VBUS-valid sensing.
- PCIe endpoint power and powered-off isolation are explicit.
- External HDMI protection and exact connector mapping are explicit.
- Exposed maker I/O has the intended isolation and protection.

### Findings first reported on 2026-07-19

- U770 TPS2553D pin 5 is `ILIM`; pin 6 is protected `OUT`.
- C725 supplies the required LTC4368 output capacitance on the protected side.
- Raw unattached USB-C VBUS capacitance is within the intended sink contract.
- BQ25798 `QON` has a defined hard-off state.
- Adapter-only startup negotiates 15 V autonomously before firmware-dependent
  charger setup; 5 V-only USB-C cannot start the machine.
- AON UVLO/OVLO thresholds use the exact 0.1% divider contract and have checked
  component-corner margins.
- HDMI, AX210, radio, and other switched domains do not receive unsafe signal
  injection while powered off.
- Radio PTT is hardware-interlocked and the RF output paths retain their external
  filtering contracts.

### Battery protection closure requested on 2026-07-19

- The motherboard now contains an autonomous BQ7791500PWR 3S protector rather
  than relying on the cell-attached thermal cutoff boards for electrical safety.
- Every cell tap is monitored through 75 ohm input resistors with 1 uF
  internal-balancing filter capacitors.
- Fixed per-cell thresholds are 4.20 V overvoltage and 2.90 V undervoltage.
- Internal cell balancing uses 75 ohm VC resistors and TI's 1 uF internal-
  balancing filter capacitors. Nominal balance current is approximately 26 mA,
  with the checked worst case remaining below 30 mA and TI's 50 mA maximum.
- An 8 mOhm, 1%, 2 W shunt sets nominal 7.5 A overcurrent and 15 A short-circuit
  detection; the checked worst-case windows are 5.94-9.09 A and 11.88-18.18 A.
- Back-to-back CSD18540Q5B MOSFETs independently interrupt charge and discharge
  current. The separate LTC4368-1, 11 mOhm shunt and 10 A fuse remain as
  whole-pack protection layers.
- Battery thermistors `NTC2` and `NTC4` were removed from the motherboard. The
  BQ25798 TS input uses a fixed in-range divider with firmware `TS_IGNORE=1`, and
  the BQ34Z100 temperature input is fixed to local VSS with `TEMPS=0`.
- The six-wire battery connector carries two positive contacts, two negative
  contacts, `CELL1_TAP`, and `CELL2_TAP`; it does not add another internal cable.

## Exact Added Contracts

- Fan: Delta `BFB04512HHA-CZ0T`, 12 V four-wire blower, fused from `MU_12V`;
  open-drain 25 kHz PWM defaults to full speed when control is absent, and FG is
  conditioned for the EC.
- USB-C cold start: each CH224A requests the 15 V PDO autonomously with a 56 kOhm
  CFG1 resistor before the EC is available.
- AON input qualification: 301 kOhm / 52.3 kOhm / 20.0 kOhm, all 0.1%, gives a
  nominal 6.20 V UVLO and 22.40 V OVLO; checked UVLO corners are approximately
  6.06 V to 6.36 V.
- Mu retention: the connector plus exact `M2XC4X2.5+C2.7X1.5` retention hardware
  is represented in the mechanical contract.

## Verification Evidence

- KiCad ERC: **0 errors**. The 13 warnings are individually classified
  `lib_symbol_mismatch` notices caused by self-contained flattened copies of
  KiCad `extends` symbols; none is an electrical warning.
- Generated schematic self-check: **PASS**.
- Schematic design contracts: **PASS**.
- Independent exported-netlist closure audit: **386 PASS, 0 FAIL**.
- Deliberately corrupted U770 negative fixture: correctly rejected by the
  independent closure checker.
- Bounded electrical calculations: **129 PASS, 0 FAIL**.
- Pin review: **2,410 PASS, 0 FAIL, 351 REVIEW**. The REVIEW rows are broad
  Mu/M.2/MCU ground, NC, spare, and general-purpose pin classifications rather
  than detected failures.
- Firmware host policy, commit, maker policy, and release-contract tests: **PASS**.
- Generated-source identity: **PASS**.
- Strict isolated schematic release check: **PASS**.
- Four independent manual reviews found no active P0/P1 defect in:
  1. power, charging, USB-C source/sink, and reset behavior;
  2. Mu, eDP, PCIe, M.2, HDMI, Ethernet, and high-speed USB;
  3. STM32, RP2350, audio, radios, GNSS, OLED, keyboard, trackpad, and external
     interface boundaries;
  4. the exact fan and autonomous PD/AON cold-start path.
- The live PCB was intentionally synchronized after the schematic ECO and every
  affected footprint was placed. It now contains 997/997 matching references
  with zero footprint or pad-net drift. SHA-256:
  `6ab264499318c5b1fe7ca8073817320621f595804ef6c7088e7db556420874a7`,
  4,376,917 bytes.

## Physical Endpoint Facts Still To Record

These are measurements or purchased-part identities, not unresolved motherboard
circuit defects. They should be entered when the exact physical parts are in hand:

- Exact cell manufacturer/model and chemistry, cell-board thermal cutoff
  threshold/delay, harness pin order, wire gauge, and cell-proximate wiring
  protection for the final 3S pack.
- Exact panel-side eDP connector identity, cable pin-one orientation, cable length,
  lane count, and panel power/backlight requirements for the purchased panel.
- Exact speaker impedance/power rating and microphone acoustic/mechanical details.
- Final trackpad and SSD1306 module connector orientation/pin-one confirmation.

No additional motherboard schematic edit is currently justified by the evidence
available in the project or by the four independent subsystem reviews.
