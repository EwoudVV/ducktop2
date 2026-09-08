# ducktop2 firmware

Version: `0.3.0-policy`

the EC and maker targets now build. they have not been programmed or tested
on assembled boards. the release record remains pending. the default EC
profile keeps unqualified pack use, charging and laptop boot disabled.

## current targets

| target | implementation |
| --- | --- |
| STM32F407 | pinned ST CMSIS and TinyUSB, correct vectors, bounded clock startup, watchdog before clock waits, SWD preserved |
| charger | BQ25798 high-byte-first registers, disabled charging at init, TS_IGNORE clear, voltage/current readback, asynchronous ADC and actual VSYS |
| power sources | TPS25751 framed reads, two coherent contract snapshots, live expander state checks, cold charger retry, ordinary removal/reselection |
| thermal | ADC conversion, 25 kHz PWM, tach freshness, spin-up grace and a latched stall response |
| laptop controls | keyboard/consumer HID, vendor status/control HID, lid debounce, battery validity, two OLED page writers, headphone mute/enable/readback |
| maker RP2350 | pinned Pico SDK target, USB HID GPIO/ADC control, user-rail gate, expiring authorization and a watchdog |

`ec_target/main.c` binds the target functions to the portable policy and
commit adapter. the software sends a desired Mu/display budget to a host
mailbox. that write acknowledges delivery only. `power_policy_confirmed`
requires a matching, fresh host reply after actual limit readback.

boot has a separate, bounded authorization because the OS cannot
apply a limit before its computer is powered. external and pack boot each require their own
qualified worst-case boot envelope in `ec_target/board_profile.h`. it never
sets `power_policy_confirmed`. without a host acknowledgement, it expires
and controlled loads turn off.

pack operation and charging require the exact pack, interconnect, thermal
protection and gauge profile to be qualified. the user reports a successful functional test of the three owned AKZYTUE
cells in series with two intermediate taps. that is useful functional
evidence; it does not establish current sharing, fault interruption or
temperature protection. keep the individual protection boards intact while
the replacement protection design is unfinished. the old 15 W low-pack policy value is
still covered as a portable-policy regression; it is not a released N305
operating point. the default target does not enable it.

## source and fault behavior

PD1 and PD2 use 7-bit addresses `0x20` and `0x21`, through service-mux channels
2 and 3. active PDO is register `0x34`, active RDO `0x35`, and PD status `0x40`.
these are register offsets, not device addresses. status, PDO, RDO and PD
status have 5-, 6-, 16- and 4-byte payloads, each preceded by its byte count.
fixed 15 V and 20 V contracts are accepted for the corrected hardware.
IINDPM is capped at 2.50 A, with a separate 0.50 A PD allowance for the raw
AON path and margin. AUX retains its own conservative allowance. accepting
a contract does not enable an unqualified boot or charge profile. other PDO
types and voltages are rejected.

all PD paths start off. a valid input can power the charger while charging
and loads stay off. the EC retries its probe, obtains fresh VSYS/status,
then writes and reads back IINDPM. U44 output and configuration registers
are checked on every input sample. an expander reset or bus failure cannot
be hidden by its cached output latch. a failed safe commit resets the EC;
U44 /RESET follows the same NRST net.

normal source removal reselects a source. supported transfers retain the Mu
rail using the real NVDC pack path, with `DUCKTOP2_PACK_BRIDGE_QUALIFIED`
required. completed charger ADC pack/SYS samples must have started at most 250 ms
ago, measured pack current
must stay within its released limit, protection and Mu PG must be healthy,
and the pack must cover the unchanged host budget plus auxiliary demand and
the platform reserve. charging and optional loads are shed during transfer.

both PD paths must be observed off before the 20 ms break interval starts.
the next path also waits for a charger ADC sample started after that
all-off observation, then needs physical path-good and a verified input-current limit.
the Mu budget mailbox stays unchanged, so a stronger source does not invalidate
an already-applied host limit. candidate loss returns to the qualified pack;
failed candidates have a bounded retry delay. stale data, excess current,
failed commits, missing pack support or an insufficient envelope fail off.
there is no capacitor hold-up assumption in this policy.

battery-only startup has its own qualified envelope. bridge, pack, gauge,
charging, boot and load qualification remain disabled pending real evidence.
continuous transfers are host-tested command sequences, not measured board
transients. physical transfer qualification remains in HIL.

fan tach uses a 250 ms freshness window. when the Mu rail is on and the fan
command is at least 30%, there is a 2 s startup grace. no valid rotation for
1 s after that latches a fault, requests full fan and removes controlled
loads. a fault needs deliberate recovery; it is not cleared by one good edge.

## build and check

from the repository root:

```sh
sh firmware/tools/run_host_tests.sh
cmake -S firmware/ec_target -B .workbench/ec-build -DCMAKE_BUILD_TYPE=Release
cmake --build .workbench/ec-build
python3 firmware/tools/verify_target_build.py \
  --elf .workbench/ec-build/ducktop2_ec \
  --output .workbench/ec-build/verification.json
```

profile fields in `board_profile.h` can be supplied as integer CMake
`-DDUCKTOP2_...=` settings. incomplete boot envelopes and unsupported charger
steps fail the build. these checks do not replace the qualification evidence.

ARM GCC is required. the EC uses the compiler's `libgcc` and a small
freestanding C support layer. the initial stack is at `0x20020000`; the linker
reserves 8 KiB and rejects data/heap overlap. compiler stack-usage reports
are retained with target objects. stack high-water measurement is still a
hardware check.

host CMake builds run the same suites. the host tests include literal PD
wire frames, BQ byte order, charger power cycling, pending ADC timeout,
expander reset, descriptor rejection, host lease expiry and fan stall.

[USB power control and loom limits](ec_target/USB_POWER.md),
[maker build and protocol](maker_target/README.md),
[Linux battery/lid and power agent](../software/ec-host/README.md), and
[gauge fixture workflow](gauge/README.md) cover the other software paths.

## what still needs physical evidence

clock/watchdog timing, reliable I2C captures, both USB orientations and USB
enumeration, fan PWM and blocked-rotor response, exact OLED module identity,
headphone detection and mute behavior, pack calibration/protection, Mu/display
power limits, and BOOTSEL/SWD recovery remain untested. all existing HIL rows
remain `NOT_RUN`. no release approval or programming record was created.
