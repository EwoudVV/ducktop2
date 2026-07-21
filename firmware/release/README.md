# Ducktop2 firmware release contract

Version: `0.3.0-policy`

This directory defines the evidence required to turn the host-tested policy
cores into production firmware. It does not claim that an STM32F407 or RP2350
image exists or that any physical motherboard has passed qualification.

## Target integration order

Before STM32 execution, PD1 and PD2 depend on the released TPS25751A boot
configuration and hardware fail-off controls. The target must not treat a
default 5 V attachment as a qualified laptop-power contract.

The STM32 target port must use this startup and recovery order:

1. Configure critical MCU pins as inputs and keep hardware source-manager and
   service-mux resets asserted.
2. Initialize the watchdog and brownout/reset-cause logging without enabling a
   source or load.
3. Call `ec_commit_force_safe()` through bounded target-driver operations and
   verify both PD paths, charging, `MU_12V`, and optional loads are off.
4. Release the source-manager and service-mux resets, recover the I2C bus, and
   confirm that all PD paths remain off.
5. Read each TPS25751A on its own service-mux channel, then read charger,
   battery, VSYS, power-good, and motherboard thermal telemetry with explicit
   validity flags. A timeout, bus error, stale value, or failed readback must
   remain invalid. Use 7-bit target addresses `0x20` for PD1 and `0x21` for
   PD2, not shifted bus bytes. Read `Active PDO Contract` (`0x31`), `Active RDO
   Contract` (`0x32`), and `PD Status` (`0x35`); reject a contract unless the
   live status, PDO voltage/current, and RDO agree. The EC does not provide
   pack-temperature telemetry. Interpret BQ34Z100 Current() as positive while
   charging and negative while discharging. TimeToEmpty() and TimeToFull() are
   minutes; reject `0xffff` and use
   `ec_telemetry_bq34z100_minutes_to_seconds()` before publishing seconds.
6. Run `ec_controller_step()` and apply its output only through
   `ec_commit_apply()`. For a battery-absent PD cold start, first commit the one
   qualified PD path with charging and every load off, wait for path-good and
   BQ25798 I2C availability, then program/read back IINDPM. The target adapter
   may acknowledge IINDPM or host power limits only after a successful
   transaction and readback where available.
7. AUX has no negotiated current contract. Start its BQ25798 input-current
   qualification at 500 mA, command and read back 250 mA IINDPM, then use ICO
   and VINDPM behavior to discover a higher safe limit. Publish a higher
   `qualified_input_current_ma` only after reading the resulting charger limit
   and deriving `available_power_mw` from that limit and measured AUX voltage.
   A stale or failed measurement remains invalid and disables AUX.
8. Feed the watchdog only after policy evaluation, ordered commit, telemetry,
   and deadline checks all complete.

The radio daughterboard is not a startup dependency. Its presence input must be
read as active low with the released pull-up, and its power output must remain
off through reset. An absent board, asserted fault, failed power-good startup,
or later power-good loss disables only the daughterboard rail. Target code must
not convert those conditions into a laptop source-manager fault.

The target OLED task may render only fields whose validity bits are set in the
snapshot built by `ec_telemetry_build_snapshot()`. PD1 and PD2 contracts are
read through their service-mux channels. Invalid fields must be shown as
unavailable rather than retaining an older value.

The maker target must leave `MAKER_PWR_EN` off and all 26 exported I/O signals
high impedance through RUN reset and BOOTSEL. User rails and I/O require
separate authorization plus a hardware-interlock observation.

## Provisional low-pack envelope

The host policy uses a 15 W Mu-plus-eDP ceiling at low SOC. It also computes a
source-aware ceiling from qualified available input power, an 85 percent
conversion model, a 6 W platform reserve, and measured auxiliary demand. The
lower ceiling wins. Charging and optional loads are shed in low-pack mode.
Low-pack limiting follows an active PACK source plus valid low-pack telemetry;
it cannot be bypassed by a separate `pack_only` indication. External-source
charging is capped by the power remaining after the platform reserve, measured
auxiliary demand, and estimated Mu/eDP demand, and is disabled below the 2.5 W
minimum useful charge budget.

The 15 W value is a provisional engineering ceiling, not a measured product
rating. It must be replaced or confirmed using the released cells, BMS, fuse,
harness, PCB, converter, display brightness, BIOS PL1/PL2 control, and thermal
system. Until the HIL low-pack rows pass, the firmware and motherboard remain
blocked from production.

## Programming and recovery

Production release requires reproducible target builds, pinned toolchains,
linker maps, `.elf`/`.bin` for the EC, `.elf`/`.uf2` for the maker controller,
SHA-256 manifests, blank-board programming logs, readback verification where
supported, and documented recovery over SWD/BOOTSEL. None of those target
artifacts is present in version `0.3.0-policy`.

## Evidence rule

`hil_matrix.csv` is the firmware-side qualification checklist. A row may move
from `NOT_RUN` to `PASS` only when its evidence path and SHA-256 are recorded
and the evidence file exists. `tools/verify_release_contract.py` enforces this
rule and validates the host policy constants, required regression vectors, and
version consistency.
