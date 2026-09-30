# firmware release and hardware tests

Version: `0.3.0-policy`

this directory holds the target release record and
the HIL matrix. the current STM32 implementation is described in
[target status](../README.md#current-targets).

## before enabling a load

the startup sequence needs to establish passive hardware state, watchdog
and reset handling, bounded bus access, and valid source/rail observations.
release source-manager/service-mux resets in the reviewed order and confirm
that the paths remain off until they are qualified.

apply policy outputs through `ec_commit_apply()`. the target must confirm
that limits and enable states took effect. failed communication, stale data,
missing readback, or failed power-good must remain a failure.

for battery-absent PD startup, the path-only bootstrap powers the charger
with charging and loads off. wait for path-good and charger communication,
then program/read back IINDPM before allowing loads.

PD contract reads use live status, active PDO, and active RDO. PD1/PD2 use
7-bit addresses `0x20`/`0x21` on their separate mux channels. 5, 9, 15 and 20 V fixed contracts are supported. a low-power attachment
only qualifies a path if the complete standby and charger-current budget
leaves usable input. it does not authorize laptop boot by itself.

AUX starts with the conservative qualification defined by the policy. raising
its budget needs valid measured input and charger results. it has no negotiated
current contract to copy from a PD controller.

## telemetry and optional hardware

publish only data with valid, fresh measurements. BQ34Z100 charge current is
positive and discharge current negative. reject invalid time values such as
`0xffff` before converting bus minutes into seconds. OLED and OS reports
should show unavailable fields as unavailable.

an absent or failed radio board disables the radio path and should not block
the rest of the laptop. maker rails and I/O have their own authorization and
interlocks; the RP2350 target must preserve those defaults through reset and
programming modes.

## provisional power model

the target applies source-dependent charger commands with explicit shunt,
gain and offset bounds. its power budget uses the lower current bound,
not the programmed value. charge commands also include battery-shunt and
regulation error. [current allowances](../tps25751a/power-envelope.md)
records the values and their qualification requirements.

the Mu/display ceiling is 60 W, reduced to fit the actual source and other
loads. the old 15 W low-pack value is a portable test case, not a qualified
Mu Ultra operating point. a high-power unplug cannot be assumed to fit
the 3 A pack ceiling. pack transfer requires a fresh, already-applied load
limit that fits the released pack and auxiliary-load envelope.

host budget acknowledgement requires matching readback and a fresh lease.
startup uses a separate bounded authorization before an OS can respond.
these sequences pass software tests; physical current response, the declared
measurement bounds and actual module throttling remain untested.

## build, programming, and recovery evidence

retain a reproducible build with toolchain version, flags, map, and hashes.
the release needs EC `.elf`/`.bin` and maker `.elf`/`.uf2` artifacts, recorded
blank-board programming, supported readback verification, and tested
SWD/BOOTSEL recovery. local build files alone do not approve a firmware image.

`target_release.json` records the approved artifacts and their evidence.
it retains its original `PENDING_TARGET_PORTS` state until the final release
review. both targets now build, but qualified power profiles, programming,
readback and HIL evidence are still missing. the development builds under
`.workbench/audit-fixes-2026-09-07/firmware/` are not approved release images.

## HIL rows

`hil_matrix.csv` is the test list. a row becomes PASS only when its evidence
path and SHA-256 are recorded and the evidence file exists.
`tools/verify_release_contract.py` checks those rules, versions, constants,
and required vectors. it does not perform the physical tests itself.

use the revised [bring-up plan](../../docs/BRINGUP_TEST_PLAN.md) to prepare
the board fixtures and test order. retain failed measurements as well as
passing ones, with the hardware and firmware revision for each run.
