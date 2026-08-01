# Current Design Status

Updated: 2026-08-01

## Release Boundary

**Verdict: SCHEMATIC BLOCKED.** The generated schematic is internally
consistent under the checks in this repository. That does not establish a
fabrication-ready PCB, safe battery system, released enclosure, or working
target firmware. The 2026-07-27 independent review and its post-fix audit are
the current release record: [`full review`](../verification/INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md)
and [`post-fix audit`](../verification/INDEPENDENT_REVIEW_2026-07-27_postfix.md).
User-facing behavior intent is recorded in
[`USER_FACING_BEHAVIOR_2026-07-31.md`](../verification/USER_FACING_BEHAVIOR_2026-07-31.md).

The relocated direct-solder trackpad lands `J58` no longer overlap stale GND
zone fill, the three duplicate physical PCB references `U170`, `U2004`, and
`U2014` were removed with their duplicate-only copper, and R251 was moved clear
of R250 to remove a physical D+/D- short. Those fixes close the corresponding
P0 and P1 findings. They do not waive the remaining routing,
signal-integrity, battery, mechanical, or HIL holds below. Procurement
identity is complete (0 gaps, stamped at generation time).

## Schematic

The active motherboard hierarchy contains 14 generated child sheets, 1,184
components, 1,372 nets, and 4,566 connected pins. The retired Intehill
controller, VL822 hub, carrier-eDP, and USB-C video sheets are not part of the
root design.

The current copied-project schematic gate reports:

| Check | Result |
| --- | --- |
| KiCad ERC | 0 errors; 27 intentional warnings (13 library-copy + 14 grounded-pin ties) |
| Generated schematic self-check | Pass |
| Schematic design contracts | Pass |
| Independent netlist closure | 1,580 pass, 0 fail |
| Bounded electrical calculations | 123 pass, 0 fail |
| Pin review | 2,603 pass, 0 fail, 0 review |
| Mainboard duplicate physical references | 0 |
| User-facing behavior checklist | 25 of 25 rows have schematic evidence; firmware/ACPI items held |
| BOM procurement gaps | 0 |
| Host firmware policy tests | Pass on host; 42 HIL rows remain `NOT_RUN` |

The remaining pin-review rows are broad Mu, M.2, MCU, spare, NC, and ground-pin
classifications that require human context; they are not detected electrical
failures. The ERC warning allowlist is tied to exact references and pins. It
covers 13 flattened KiCad symbol copies and 14 required GPIO/strap ties that
KiCad sees sharing the global ground power flag.

Sheet 15 now carries the rear 3.5 mm headphone jack the user-verified behavior
required (row 12): J422 CUI SJ1-3535NG driven by U425 TPA6130A2RTJR DirectPath
I2C headphone amp (fixed address 0x60) from the PCM2900C line-out. Plug-detect
is the jack ring-normalling contact (RN = HP_DETECT) read by the EC on U44 pin
6 (a recovered source-manager spare input) with R782 100k pull-up; on plug-in
the EC drives AUDIO_AMP_EC_EN low so the existing U421 AND gate mutes the
TPA2012D2 speaker amp, and I2C-unmutes U425. /SD is tied to MU_HOST_ACTIVE
(S0-only, 0.4 uA in S3) and the amp powers up muted with outputs disabled
(fail-safe OFF). ERC stays 0 errors / 27 intentional warnings and closure rose
to 1,580 nets. U425/J422 carry their MPN properties; the 9 new small caps were
stamped through the generation-time catalog, so BOM procurement gaps are now 0.

The host-tested EC firmware gained a keyboard Fn-layer keymap module
(`firmware/ec/src/ec_keymap.c` + `ec_keymap.h`) — pure C that translates the
fabricated 5×14 MX ULP matrix state into a USB HID boot-6KRO report plus a
4-slot consumer report, applying the user-confirmed Fn layer (Fn+1..0=F1..F10,
Fn+Esc=`~, Fn+Bksp=Delete, Fn+Up/Down=brightness, Fn+Left/Right=volume). 22
host tests pass in `tests/test_ec_keymap.c`, wired into `run_host_tests.sh` and
`CMakeLists.txt` as `ducktop2_ec_keymap` / `ec_keymap_tests`. The target-side
matrix scan (drive rows, read columns per the diode orientation in
`generate_keyboard_daughterboard_sheet.py`) and the USB HID interface remain;
the keymap logic itself is host-verified.

The host-tested fan policy core (`firmware/ec/src/ec_fan.c` + `ec_fan.h`)
implements the user-verified fan behaviour (quiet idle, performance-biased,
never throttles): control temp = max(skin, Mu coldplate) in decidegrees C;
hysteresis at 40/45C; 2s anti-cycling; linear 30%→100% ramp across 45→70C;
100% duty at/above 70C (25-35C below the Mu throttle point); throttle_imminent
flag at 80C for PL1 reduction; fail-safe 100% on invalid temps. 16 host tests
pass (`tests/test_ec_fan.c`), wired as `ducktop2_ec_fan` / `ec_fan_tests`. The
target side (NTC ADC→decidegrees + TIM1_CH1 PWM duty write) remains.

The host-tested OLED content composer (`firmware/ec/src/ec_oled.c` + `ec_oled.h`)
implements the user-verified "all system component status" spec (row 7/15) as
two 8-line text buffers: left = power/battery (source+V, SOC+state, pack V/I/P,
TTE/TTF, capacity, cycles+health), right = thermal/fan/system (fan duty+state,
skin/Mu temps, throttle flag, radio DB state, maker, EC version, EC fault).
Invalid data renders as dashes (no misleading zero/stale). 16 host tests pass
(`tests/test_ec_oled.c`), wired as `ducktop2_ec_oled` / `ec_oled_tests`. The
target side (SSD1306 I2C behind TCA9548A ch0/ch1 + 5x8 glyph rasterisation
into the 128x64 1bpp page buffers) remains.

The host-tested lid switch debouncer (`firmware/ec/src/ec_lid.c` + `ec_lid.h`)
implements the user-verified lid behavior (row 1): 30 ms debounce of the
LID_CLOSED_N hall/reed input (J53 + R209 10k pull-up, PE10) with one-shot edge
flags (just_closed/just_opened) for ACPI lid events. Bounce cancels and
restarts the timer; fail-safe reads "open" on sensor disconnect (R209 pull-up).
The EC never sequences Mu power on lid events — display-off is an OS-side ACPI
policy (HandleLidSwitch=lock or ignore in systemd-logind, NOT suspend). 12
host tests pass (`tests/test_ec_lid.c`), wired as `ducktop2_ec_lid` /
`ec_lid_tests`. The target side (reading PE10 + forwarding the edge as an
ACPI lid switch input to the Mu OS) remains.

The host-tested battery state machine (`firmware/ec/src/ec_battery.c` +
`ec_battery.h`) implements the "trusted OS percentage" half of row 5/7: a
hysteresis state machine (UNKNOWN/NOT_PRESENT/DISCHARGING/CHARGING/FULL) that
consumes the telemetry snapshot + pack_present + charger_enable and outputs
an `ec_battery_report_t` the target forwards to the Mu OS as
`/sys/class/power_supply/BAT0/`. Hysteresis (charge > 50 mA, discharge < -50 mA,
full < 30 mA + SOC ≥ 95% with a 2 s confirmation timer) prevents the near-zero
flicker that ad-hoc current-sign inference cannot avoid. NOT_PRESENT overrides
all when the BQ34Z100 probe fails. 18 host tests pass (`tests/test_ec_battery.c`),
wired as `ducktop2_ec_battery` / `ec_battery_tests`. The target side (BQ34Z100
I2C driver + the USB/I2C-target transport to the Mu OS) remains.

## PCB

The reviewed PCB SHA-256 is
`25d06e11208187f597514f593d12ef28a139f637f6f02362e2592c7d4c6f4501`.
The mainboard is six layers and measures 358 x 185 mm, including the fin-stack
notch. It now contains 1,170 physical footprints, 4,527 routed segments, 52
arcs, 855 vias, and five top-level zones. Routing is in progress; these numbers
are a snapshot, not a release claim.

The final all-track PCB DRC baseline contains 1,404 violations (948 errors and
456 warnings), 499 unconnected items, and 199 schematic-parity observations.
The principal categories are 203 solder-mask bridges, 199 shorting-item
findings, 199 courtyard overlaps, 156 clearance violations, 153 starved
thermals, and 38 dangling track/via objects. Those findings need individual
classification and correction as routing continues. They are not accepted
fabrication waivers. The duplicate-removal candidate introduced no new dangling
track or via objects, but it does not make the existing routing clean.

R251 had no attached routing, so it was moved from `(179.3, 88.6)` to
`(180.3, 90.3)` without disturbing routed copper. That removed its overlap with
R250, which had shorted `/TRACKPAD_USB_DP` to
`/Internal Services/TPAD_CONN_DM`; only the five top-level zone blocks were
refilled in a copied candidate before installation. The final DRC contains no
entry matching `TPAD_CONN`, `TRACKPAD_USB`, `J58`, or `C1720`. This closes that
local defect only, not the remaining board-wide DRC baseline.

The direct trackpad connection is now four `J58` through-hole solder lands:
pin 1 GND, pin 2 D-, pin 3 D+, and pin 4 VBUS. It uses a cut USB 2.0
Standard-A-to-USB-C cable, not an internal USB-C receptacle. Cable gauge,
length, bend path, retention hardware, and pull/strain testing are still
unreleased.

The PCB is not ready for fabrication. In particular, it still requires
high-speed routing and SI constraints; power-loop, thermal, and back-power
review; a complete orderable BOM; a clean final DRC/parity result; and physical
validation. ~~A reviewed controlled-impedance stackup~~ was needed —
**COMPLETED via P1.4** (committed to `ducktop2.kicad_pcb`). Candidate trace
geometries for 50/85/90/100 Ω were computed 2026-08-01
(`verification/IMPEDANCE_VERIFICATION_2026-08-01.md`,
`gen/compute_impedance.py`) and are pending the NextPCB engineering review
before routing starts.

The removable radio/GNSS/audio daughterboard has 126 placed footprints. Its
schematic passes ERC with no warnings, and its mainboard interface defaults off
so the laptop, system audio, microphone, charging, and boot path do not depend
on the daughterboard being installed.

## Mechanical

Confirmed plan-view measurements:

- panel: 352 x 227 mm
- provisional lid/base: 358 x 248 mm
- three cells: 100 x 60 mm each
- keyboard PCB: 273.5 x 80.0 mm
- trackpad: 140 x 105 mm
- speakers: 38 x 18 mm each

The battery, trackpad, cooling, and hinge stack still need a physical Z-height
model. The J58 cable has no released clamp, tie point, service loop, adhesive
specification, cable part number, or pull-test result. The floorplan cable
corridors are therefore explicitly provisional, not a released mechanical
route.

## Firmware

The repository contains deterministic C11 policy cores and host tests for the
STM32 EC and RP2350 maker controller. It does not yet contain target startup,
USB descriptors, board drivers, vendor SDK integration, final binaries, or HIL
results. The hardware defaults were designed so reset removes source-path and
load enables before firmware runs, but target behavior must still be proved on
the first article.

## Software

The 64 GB eMMC recovery/hibernate design and setup tooling are done:
`software/os-theme/docs/emmc-recovery.md` (GPT layout, sizing math, boot flow,
hibernate resume config, recovery procedures) plus the guarded installer
`software/os-theme/install/emmc-recovery-setup.sh` (`--check`/`--dry-run`
preview modes; refuses non-eMMC devices, mounted partitions, and the running
root). Execution happens at Mu bring-up, which is not possible before the
hardware exists.

## Work in Progress

1. ✅ Correct the J58 stored-zone failure without moving unrelated routing.
2. ✅ Remove duplicate physical `U170`, `U2004`, and `U2014` footprints and
   duplicate-only copper; add a release-gate uniqueness check.
3. ✅ Move unconnected R251 clear of R250, verify the trackpad D+/D- physical
   short and local solder-mask bridge are absent, and preserve existing routing.
4. ✅ Add the rear 3.5 mm headphone jack with plug-detect speaker mute to the
   system audio sheet per the user-facing behavior checklist (`fae06d4`).
5. ✅ Complete and host-test the firmware policy cores: keyboard Fn layer,
   fan policy, OLED content, lid debounce, battery state machine
   (`d0991b3`/`d1396d0`/`d95d9f2`/`22a966d`/`f223750`).
6. ✅ eMMC recovery/hibernation design and setup tooling
   (`software/os-theme/docs/emmc-recovery.md` + `install/emmc-recovery-setup.sh`).
7. Classify and resolve all remaining PCB DRC, unconnected, and parity findings.
8. ~~Freeze the six-layer stackup and controlled-impedance geometries.~~ — COMPLETED via P1.4.
9. ✅ Complete manufacturer part numbers, ratings, assembly constraints, and
   alternate sourcing for the remaining BOM gaps. — COMPLETED. All 378 gap
   refs (204 resistors + 174 capacitors) now stamp Manufacturer/MPN at
   generation time from `gen/bom_catalog.py` (inverted from the reviewed
   `apply_bom_catalog.py` assignments + the 2026-07-30 Murata GRM hold
   suggestions + MCP-verified LCSC alternates); regeneration can no longer
   lose procurement identity. BOM release gate PASS, 0 gaps.
10. Finish reviewed power, PCIe, USB, HDMI, Ethernet, audio, and control routing.
11. Refill zones only in a copied board, clean silkscreen, run full DRC, and
    review every exception.
12. Complete eDP harness, battery-pack, trackpad-cable retention, thermal, RF,
    and enclosure measurements.
13. Build target firmware and run the hardware-in-the-loop bring-up matrix.

The repository is useful for review now, but the mainboard files are not an
ordering package.
