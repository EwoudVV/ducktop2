# controller firmware

ducktop2 has two controllers. the STM32F407 is the laptop EC. the RP2350 is
the separate maker controller. their policy code is C11 and can be tested
on a host before it is connected to board drivers.

Version: `0.3.0-policy`

the dated test results are in
[project status](../docs/design-status.md). the STM32 target port exists,
but normal charging and Mu power-budget integration are unfinished.
[target details](README.md#stm32-target)

## code layout

| Directory | Contents |
| --- | --- |
| `ec/src`, `ec/include` | EC policies, commit ordering, telemetry, keyboard, fan, OLED content, lid, and battery state |
| `ec_target` | STM32 startup, linker file, board drivers, matrix scan, USB HID, and application glue |
| `maker/src`, `maker/include` | RP2350 maker policy |
| `tests` | Host tests, mocked device transactions, and policy vectors |
| `tps25751a` | USB-PD controller configuration and export manifest |
| `release` | Target release record and HIL matrix |

## EC policy

the EC starts with controlled paths and loads off. source handling uses
OFF, VALIDATING, ACTIVE, and FAULT states, with a 20 ms all-off interval
when changing sources. timeouts, invalid telemetry, and failed commits
return to a passive state or latch a fault for deliberate recovery.

PD1 and PD2 need valid live status, PDO, and RDO readings. a qualified PD
path can first power the otherwise-unpowered charger with charging and
loads off. after path-good, the target writes and reads back IINDPM before
the policy can trust an applied input-current limit.

AUX is not a negotiated PD source. its starting qualification is conservative,
and raising it needs measured charger/input evidence. power budgets account
for the platform, Mu/display, auxiliary loads, and charging. low-pack policy
uses a provisional 15 W Mu-plus-display ceiling and sheds optional loads.
that ceiling still needs hardware validation.

the commit adapter checks ordering and output combinations. an acknowledgement
means a command really took effect, with readback where supported. it must
not be set just because code attempted a write.

## laptop functions

- `ec_keymap` turns the 5 x 14 keyboard matrix into boot-keyboard and consumer
  reports, including the agreed Fn layer.
- `ec_fan` uses skin and Mu temperatures, hysteresis, and a ramp to full fan.
  invalid temperatures request full fan; thermal behavior still needs measurement.
- `ec_oled` composes two displays' text. invalid data is shown as unavailable.
- `ec_lid` debounces lid state without directly power-cycling the Mu.
- `ec_battery` produces a stable charging/discharging/full/present report
  from validated telemetry. host transport to the OS is still required.
- optional radio presence/fault handling keeps the radio separate from the
  laptop's core power and boot requirements.

the target has some of these drivers and data paths, but not every policy
module is integrated into the target main loop. use the target status page
for the remaining work.

## maker policy

the maker rails start off and all 26 user I/O signals start high impedance.
rail and I/O requests need the corresponding authorization and hardware
interlock. reset, watchdog, interlock loss, or a power fault removes them.
the full RP2350 target and its hardware tests remain to be completed.

## host checks

from the repository root:

```sh
sh firmware/tools/run_host_tests.sh
```

the script compiles the suites with strict C11 warnings, runs them, and checks
the release contract. tests include policy ordering, keyboard/fan/battery
behavior, mocked BQ/TCA9539 transactions, matrix debounce, and USB descriptors.
they do not exercise real USB hardware, analogue behavior, or a programmed MCU.

the CMake host build is another option:

```sh
(
  cd firmware || exit
  cmake --preset host-debug
  cmake --build --preset host-debug
  ctest --preset host-debug
)
```

## next work

finish real charge and Mu/eDP budget application, normal operating requests,
remaining displays/controls, and the OS telemetry transport. build and program
the targets through a recorded recovery path, then run the HIL matrix.

[release requirements](release/README.md) and [laptop behavior](../docs/hardware.md#expected-behavior)
describe the result those implementations need to support.


## STM32 target

### what's present

| Area | Source | What exists |
| --- | --- | --- |
| STM32 foundation | `startup_stm32f407vgtx.s`, `system_stm32f4xx.c`, linker script | Startup, clock setup, SysTick, and memory layout |
| GPIO and thermal/fan hardware | `gpio.c`, `fan_math.c` | Safe pin initialization, ADC reads, PWM/tach support, and fan math |
| I2C and service mux | `i2c.c`, `i2c.h` | Bounded bus operations and TCA9548A selection |
| Source-manager expander | `tca9539.c` | Initialization, input reads, and controlled outputs |
| Charger | `bq25798.c` | Probe, configuration, current/voltage setters, readback, faults, and ADC telemetry |
| Fuel gauge | `bq34z100.c` | Gauge reads and control/data operations |
| PD contract reads | `main.c` | PD status, active PDO/RDO, and qualification input assembly |
| Keyboard scan | `matrix_scan.c`, `matrix_debounce.c` | Matrix scanning and debounce |
| USB keyboard | `usb_hid.c`, `usb_hid_desc.c` | OTG_FS device stack and keyboard/consumer descriptors |
| Application glue | `ec_app.c`, `ec_app_math.c`, `main.c` | Some policy inputs, charger commits, telemetry, and fan integration |

existence here means code is present. host-tested pieces are covered by
`tools/run_host_tests.sh`; real peripheral and end-to-end behavior still
need target tests. [dated results](../docs/design-status.md)

### what still stops normal operation

`commit_write()` in `ec_target/main.c` returns false for
`EC_COMMIT_CHARGE_BUDGET_MW` and `EC_COMMIT_MU_EDP_BUDGET_MW`. this avoids
claiming a power limit was applied when no complete target path applied it.

the input builder also leaves `request_charger`, `request_mu_12v`, and
`power_limits_applied` false, with normal requested charge power at zero.
estimated Mu/eDP and auxiliary power validity are also false. these are
unfinished integration points, not proof that the power system is ready.

remaining work includes:

- converting policy budgets to real charger and host/display limits, with
  applied-state feedback and failure handling;
- normal power-button/operating requests and a checked startup/transfer path;
- end-to-end battery/telemetry validity and transport to the Mu OS;
- target integration for OLED rendering, lid events, headphone/speaker
  behavior, and other controls not connected through the current main loop;
- a complete RP2350 target, programming, and recovery path;
- clean, reproducible build artifacts tied to the release record;
- SWD/BOOTSEL recovery, blank-board programming, readback, and HIL evidence.

do not replace the false returns with unconditional success. implement the
actual command and verify the result first.

### reference points in the current code

these help locate the implementation. check the schematic generator and
pin definitions together before changing an assignment.

| Function | Current target assignment |
| --- | --- |
| I2C1 | PB6 SCL, PB7 SDA |
| USB OTG FS | PA11 DM, PA12 DP |
| AUX voltage ADC | PA6 |
| Skin and Mu thermal ADCs | PA7 and PB0 |
| Keyboard rows | PE0-PE4, read with pull-ups |
| Keyboard columns | PD0-PD13, driven during scan |
| Fan PWM | PE9, TIM1_CH1 |
| Lid input | PE10 |
| SWD | PA13 and PA14 |

the intended clock setup is an 8 MHz HSE with a 168 MHz core and 48 MHz USB
clock. the scan uses columns as driven outputs and rows as inputs. older
notes saying to drive the rows are superseded.

`i2c.h` uses 7-bit addresses: TCA9548A `0x70`, TCA9539 `0x74`, PD1 `0x20`,
and PD2 `0x21`. the PD reads select service-mux channels 2 and 3 respectively.
use the device headers and schematic for the full bus map and other addresses.
