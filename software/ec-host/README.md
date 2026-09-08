# ducktop2 Linux controls

this directory contains the Mu-side half of the EC interface. nothing here
has been installed or run against a real EC. the Python protocol and power
limit functions are tested with temporary files. the kernel module builds
and loads on Linux 6.12.108 in a disposable aarch64 QEMU guest. its synthetic
UHID test passes battery units/status, lid events, malformed-report rejection
and stale-data expiry. the intended Fedora kernel and physical Mu still
need their own installation and runtime tests.

`linux/ducktop2_ec.c` binds only to the EC vendor HID collection. keyboard
and consumer interfaces stay on the normal HID path. it exposes a battery
through the Linux power-supply class and an `SW_LID` input device. values
without validity flags return unavailable. after 2 s without reports the
battery data expires. the userspace agent can still use hidraw.

`host_agent.py` reads EC reports, applies both RAPL package constraints,
checks their readback, bounds display brightness, and uses `bl_power` for
lid blanking. it sends a matching budget-generation acknowledgement only
after those operations pass. the reported estimate is the entire admitted
ceiling. the profile must include measured non-package Mu demand and the
worst display demand; RAPL alone is not a Mu-plus-display limit.

`board-profile.example.json` deliberately has `qualified: false` and zero
budgets. fill it from measured, reviewed evidence. setting that flag alone
does not produce the evidence. the EC has its own compile-time qualification
switches, which the host cannot override.

on a disposable Fedora test system, build the module with `make -C linux`
after installing the matching kernel-devel package. installation into the
real Mu should follow the kernel-module and HIL review. copy the supplied
udev rule, systemd service and logind snippet into their normal locations,
and install the agent at `/usr/local/libexec/ducktop2-ec-host`. the service
expects `/etc/ducktop2/board-profile.json`. secure-boot module signing is a
target-specific installation step. do not enable the service with an
unqualified profile.

the logind snippet keeps lid closure from suspending the Mu. the agent blanks
the backlight; reopening restores it without a Mu power cycle. Fn brightness
and volume use the existing consumer HID reports. display controls and
headphone switching still need real-device validation.

## wire format

all reports are 64 bytes, have no HID report ID, and use little-endian fields.
interface 2 has a vendor usage page and EP3 IN. feature transfers use a
leading zero report-ID byte in the Linux ioctl buffer.

| input offset | value |
| --- | --- |
| 0 | `DT2` followed by version byte 1 |
| 4 | budget generation, u32 |
| 8 | telemetry validity mask, u16 |
| 10 | presence/lid/fan/headphone/external/boot/charge/host flags, u16 |
| 12, 13 | SOC and battery state, u8 each |
| 14, 16 | pack mV u16 and signed mA i32 |
| 20, 24 | remaining and full mAh, u32 each |
| 28, 32 | time-to-empty and time-to-full seconds, u32 each |
| 36, 40 | requested budget mW and acknowledged generation, u32 each |
| 44, 46, 48 | policy fault u16, fresh fan RPM u16, EC milliseconds u32 |
| 52, 53 | applied and denied USB port masks, u8 each |
| 54 | USB phase in low nibble and fault in high nibble |
| 55 | one nibble per PD controller: valid, connected, source, VCONN bits |
| 56, 58 | conservative USB current upper bound in mA and rail mV, u16 each |
| 60 | USB input-power reservation in mW, u32 |

feature replies carry the same magic and generation, then applied Mu/display
budget at 8, conservative Mu/display estimate at 12, auxiliary estimate at
16, request flags at 20 and lease milliseconds at 24. byte 28 is the USB
permission mask; bytes 29..63 must be zero. the EC accepts 250..5000 ms leases; the agent uses 1500 ms.

USB mask bits 0..6 select J21, J11, J22, J23, J12, J24 and J25. the
agent defaults to no USB permissions. `--usb-ports 0x7f` requests all seven;
the EC can deny ports to keep its qualified current and input-power budgets.
`--clear-usb-fault` sends one clear-request edge. the hardware latch stays off
until the current is quiet and fresh; repeatedly setting the flag does not
keep clearing the fault. request bit 7 carries this clear request.

request bits 0..6 are power off, charging, speaker/headphone audio,
microphone, radio, keyboard lighting and a deliberate BMS retry. use a
released load profile before enabling optional requests. BMS retry needs
an external source, loads and charging off, and a qualified pack. it produces
one bounded pulse per request edge. physical recovery remains untested.

```sh
python3 software/ec-host/test_host_agent.py
# inside the disposable Linux guest, with the module and uhid loaded:
python3 software/ec-host/test_linux_uhid.py
python3 software/os-theme/tests/test_resume_config.py
```

protocol references: Linux [hidraw](https://docs.kernel.org/hid/hidraw.html),
[powercap](https://docs.kernel.org/power/powercap/powercap.html), and
[power-supply class](https://docs.kernel.org/power/power_supply_class.html).

`aux_worst_case_mw` covers other auxiliary loads. the EC separately adds
its complete USB reservation before applying charger and Mu budgets. a still
valid lower host limit can survive an increase in the requested limit, but
its acknowledged generation remains the original one until a new reply is
received. the kernel battery/lid fields are unchanged.
