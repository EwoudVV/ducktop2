# bring-up plan

updated 4 september 2026. this is the preparation and test order. the exact
power fixtures, limits, connections, and acceptance values still need a
review against the corrected boards before this becomes a bench procedure.

the first prerequisites are the BMS fuse-net/layer fixes, completed routing,
and trustworthy per-board verification. see [current status](design-status.md).

## fixture requirements

- The BMS fixture must provide defined simulated voltages at all three cell
  inputs and taps. provide a separate MCU_3V3/control interface where needed.
- Keep raw pack negative, BMS protected return, and system ground distinct.
  measurement equipment must not bridge the protector or gauge shunt.
- Match input fixtures to the actual qualification windows and source paths.
  the PD selector's nominal window is 13.1-17.1 V; AUX enters at left J190.
- Define fault injection using controlled sources and loads. specify levels,
  timing, recovery, and probe references before applying power.

## records for every stage

record board revision and serial, assembly population, firmware version,
fixture diagram, instruments, source/load limits, probe references, expected
values, measurements, and a pass/fail result. retain evidence in the project.
do not advance through a failed or unexplained result.

## stage 0: bare boards and cables

inspect outlines, drills, mask, pad registration, and connector footprints.
obtain the fabricator's electrical test result against the released netlist.
regenerate IPC-D-356 from the final board files; the existing pre-routing
exports are historical and can have obsolete pad positions.

use unpowered continuity/isolation checks to investigate suspect nets and
interfaces. a few DMM spot checks are not equivalent to a full flying-probe
test. verify both the cable's conductor map and the expected board nets
with it seated in the intended orientation.

## stage 1: assembled, unpowered

inspect IC orientation, FET footprints/pin assignments, fuse clips, shunts,
connector seating, solder joints, and DNP population. measure resistance and
diode behavior in both polarities between the specified rails/references.
record the readings and investigate unexplained low resistance.

the BMS test-point table is:

| Point | Net | Point | Net |
| --- | --- | --- | --- |
| TPB1 | PACK_POS_RAW | TPB9 | MCU_3V3 |
| TPB2 | BAT_PROT_VIN | TPB10 | BMS_AVDD |
| TPB3 | PACK_POS_FUSED | TPB11 | BMS_VDD |
| TPB4 | BAT_PROT_FET_COMMON | TPB12 | BMS_SRP |
| TPB5 | BAT_PROT_GATE | TPB13 | BMS_SRN |
| TPB6 | BAT_PROT_CGATE | TPB14 | BMS_PRES |
| TPB7 | PACK_FAULT_N | TPB15 | BMS_LD |
| TPB8 | PACK_RETRY_PULSE | TPB16 | FG_VSS |

choose the correct reference for each measurement. TPB16 is the protected
return, not a universal ground for every BMS node. define equivalent test
maps for the center and I/O boards before assembling them.

## stage 2: isolated low-energy power tests

prepare board-specific supply fixtures and reviewed current limits before
powering anything. keep the Mu, real cells, and optional loads disconnected
until the relevant tests permit them.

| Board | What the fixture must provide | What to establish |
| --- | --- | --- |
| BMS | Simulated series cells and taps; a separately defined MCU_3V3/control interface if needed | Internal supplies, primary/secondary FET behavior, fault/retry, balancing, thresholds, and recovery |
| Center | A defined qualified input or fixture injection point, with the missing sideboard paths accounted for | AON/reset behavior, converters, charger communication, sequencing, and default-off loads |
| Left | Its required supply rails and control inputs | Hub rails/reset, input protection, port switches, PD1, AUX, and interface behavior |
| Right | Its required rails and control inputs | PD2, port switches, Ethernet/HDMI support rails, and interfaces |
| Keyboard | EC or a dedicated matrix fixture | Every switch/diode, scan direction, debounce, and key mapping |
| Radio | Controlled power and interface fixture | Presence/fault behavior, local rails, GNSS/control/audio; RF tests are a separate setup |

write separate fault-injection tests for cell OV/UV, current faults, open
tap, invalid source, reset, and failed/stale telemetry. use the IC datasheets
and firmware HIL rows to set levels and timing. do not improvise a short
across a real pack to test a protector.

## stage 3: firmware and gradual integration

establish programming, readback, recovery, reset defaults, and watchdog
behavior. confirm actual applied limits before enabling charging or Mu power.
host test success does not prove those target transactions.

connect boards only with power removed. add one reviewed interface at a
time, checking rails, current, faults, and communication. follow the actual
power dependencies; do not power both ends independently unless the test
fixture specifically accounts for it.

use a controlled pack substitute during early integration. the real cells
come after protection, charging, balancing, and reference-ground behavior
have passed the relevant tests.

## stage 4: complete laptop tests

- All charging inputs and source transfers, at startup and under load.
- Battery current, gauge calibration, balancing, trip/recovery, and energy use.
- Mu boot, NVMe, Wi-Fi/Bluetooth, USB, HDMI, and Ethernet.
- Internal display on the final harness, brightness, lid behavior, and hinge cycling.
- Keyboard, trackpad, OLEDs, speakers/headphones, microphone, and maker GPIO.
- Cooling, component/skin/cell temperatures, and sustained load.
- Optional radio behavior, RF filters/antennas, emissions, and coexistence.
- Power-off leakage, reset/recovery, cable strain relief, and service access.

set ripple, overshoot, thermal, signal, and timing limits from the relevant
component and system requirements. a generic percentage or visible USB
activity on a scope does not validate every rail or a high-speed channel.

the result records feed [firmware HIL](../firmware/release/README.md) and
`verification/hardware_validation_release.json`. both stay incomplete until
the measurements exist.
