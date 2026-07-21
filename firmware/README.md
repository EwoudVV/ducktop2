# Ducktop2 controller firmware policy

Version: `0.3.0-policy`

This tree contains deterministic, allocation-free C11 policy cores for the
Ducktop2 STM32F407 embedded controller and integrated RP2350 maker controller.
It is intentionally separated from target startup code and vendor SDKs so the
safety transitions can be reviewed and tested on a host compiler first.

## What is implemented

- EC outputs start passive: both `PDx_PATH_EN` controls, `CHG_ENABLE`,
  `MU_12V_ENABLE`, keyboard RGB, the radio daughterboard rail, and audio requests
  are off.
- PACK, AUX, PD1, and PD2 use one mutually exclusive source-state model with
  `OFF`, `VALIDATING`, `ACTIVE`, and `FAULT` states.
- PD1 and PD2 use TPS25751A controllers on separate service-mux channels. A PD
  path cannot be enabled until its negotiated voltage/current contract is valid.
  Their target addresses are the 7-bit values `0x20` for PD1 and `0x21` for
  PD2; target drivers must not store the shifted 8-bit bus bytes as addresses.
  Contract telemetry comes from `Active PDO Contract` (`0x31`), `Active RDO
  Contract` (`0x32`), and `PD Status` (`0x35`). A valid sink contract must be
  confirmed from those live registers before its current limit is used.
  The qualified path first powers the otherwise-unpowered BQ25798 while the
  charger, Mu, and optional loads remain off. After path-good,
  charger IINDPM is set to `min(PDO current - 250 mA, 2750 mA)` and must be
  acknowledged exactly before charging or downstream loads can start. A
  missing or mismatched acknowledgement turns the path back off and latches a
  fault.
- Reset-domain release, an all-paths-off observation, service-bus health,
  charger fault state, thermal validity, and source telemetry are qualified
  before activation. PACK, AUX, PD1, and PD2 share one one-hot state model.
- AUX current is never described as negotiated. Target firmware must begin with
  a conservative 500 mA qualification, command the resulting 250 mA IINDPM,
  and verify the charger readback before AUX becomes active. It may raise that
  qualification only from BQ25798 ICO/VINDPM results and a measured input-power
  limit; a missing, stale, or invalid result fails the source off.
- Transfers impose a 20 ms all-off deadtime. Validation, path-good, and
  `MU_12V_PG` timeouts fail safe and latch a fault.
- Low-SOC pack operation limits the Mu plus eDP request to 15 W and
  sheds keyboard RGB, radio, audio, and charging requests. `MU_12V` remains off
  until the target adapter confirms an applied host/eDP power limit no greater
  than the calculated source envelope. The limit applies whenever PACK is the
  active source and low-pack telemetry is asserted; it does not depend on a
  separate pack-only mode flag.
- Charge power is source-aware: the policy subtracts the platform reserve,
  measured auxiliary demand, and estimated Mu/eDP demand, caps the remainder,
  and disables charging when less than 2.5 W remains.
- Reset and watchdog paths remove every controlled load. Fault recovery always
  returns to `OFF` and requires deliberate source revalidation.
- The radio/GNSS/audio daughterboard is optional. Its active-low presence and
  fault inputs default safe when the connector is empty. An absent, faulted, or
  timed-out board keeps only `RADIO_DB_PWR_EN` low and does not block the Mu,
  display, keyboard, trackpad, system audio, Ethernet, Wi-Fi, maker controller,
  OLEDs, charging, or source selection. Rejected requests are not queued.
- `ec_telemetry_build_snapshot()` prepares bounded, validity-qualified data for
  the two SSD1306 displays: SOC, pack voltage/current, charge or discharge
  power, time remaining, capacity, cycle count, health, active input, and both
  TPS25751A negotiated contracts. BQ34Z100 current is positive while charging
  and negative while discharging. BQ34Z100 time values are minutes on the bus;
  `ec_telemetry_bq34z100_minutes_to_seconds()` rejects `0xffff` and converts
  valid values before they enter the OLED snapshot. Cell protection handles
  pack temperature, so the OLED model has no pack-temperature field.
- The host-tested EC commit adapter rejects impossible output combinations and
  direct source-to-source changes, forces a passive state before source
  changes, requires a separate path-only bootstrap commit, writes current and
  power limits before charger/load enables, commits optional loads last, and
  attempts a full safe-state rollback after any driver error.
- Maker user rails start off and require an explicit request, independent
  authorization, and a hardware-interlock observation. All 26 exported RP2350
  user I/O signals separately require I/O authorization; they start high
  impedance and return high impedance on reset, watchdog, authorization loss,
  interlock loss, or power fault. Requests made before their interlock and
  authorization fault off and are not queued for later activation.

## Host build

With CMake 3.20 or newer:

```sh
cmake --preset host-debug
cmake --build --preset host-debug
ctest --preset host-debug
```

On a machine without CMake, the same strict C11 tests can be run without
creating repository build artifacts:

```sh
firmware/tools/run_host_tests.sh
```

The runner also executes `tools/verify_release_contract.py`, which checks
version consistency, required safety constants and vectors, and the evidence
rules for `release/hil_matrix.csv`.

The implementation has no network dependencies and uses only the C standard
library in host tests.

The `*_applied` inputs are target-adapter acknowledgements, not optimistic
write attempts. Target code must assert them only after a successful bounded
transaction and readback (where the device supports readback), and must clear
them before starting a new command.

## Deliberate boundary

This is not a production firmware release. It does not yet include STM32 or
RP2350 startup files, linker scripts, board pin initialization, ADC/I2C/USB
drivers, BQ25798/TPS25751A transactions, USB descriptors, OLED rendering,
target watchdog setup,
thermal characterization, signed images, or factory `.elf`, `.bin`, and `.uf2`
artifacts. Those items remain blocked until target integration and the HIL
matrix in `release/hil_matrix.csv` is completed with recorded evidence. See
`release/README.md` for the required startup, programming, and recovery order.
