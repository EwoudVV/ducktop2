# TPS25751A port configuration

J21 uses `ducktop2_pd1_config.json`: host-only USB 3.2 Gen 2x1. J11 uses
`ducktop2_pd2_config.json`: host-only USB 2 through USB7206 downstream port 1.
the two EEPROM images are different. neither port provides a USB device,
USB4, DisplayPort alternate mode, or audio accessory data path.

both ports use dual-role power, fixed 5/9/15 V sink PDOs at 3 A and a
20 V / 5 A sink PDO. the source side stays at 5 V / 900 mA, with default
Rp and no BC1.2 advertisement. the EC controls the charger and separate
PP5V permissions. 5 A operation needs a suitable cable and a valid contract.
lower-power contracts stay connected so the EC can budget their actual power.

these 100 W profiles belong to the ISL9241 power revision. that circuit's
schematic and PCB integration is still pending. do not program these images
onto the old power design. all hardware qualification gates remain off.

these are exact raw JSON exports from 29 september 2026, using TI Application Customization Tool
2.0.0 with `FB09.17.02__RC5.bin`. `release_manifest.json` binds each source,
original export archive, binary, C array, original VIF and reviewed VIF.
local TI output is under ignored `generated/PD1/` and `generated/PD2/`.
the superseded combined image must not be used for either port.

```sh
python3 firmware/tps25751a/verify_config.py --require-generated
python3 firmware/tests/test_tps25751_config.py
```

the checker compares complete critical register-write records, the two
low-region copies in each full-flash image, GPIO roles, data rate, swaps,
VCONN/path settings and every active PDO. target admission also reads the
controller's profile and fails off if it belongs to the wrong physical port.

TI's original VIFs are retained unchanged. its left VIF reports host speed
as N/A, and its right VIF defaults to a port outside a hub. the public VIFs
are clearly marked project review drafts with each correction recorded in
the manifest. the left speed is Gen 2x1; the right is USB 2 on hub port 1.
TI documents that system fields need review after export in
[SLVAFZ1](https://www.ti.com/lit/an/slvafz1/slvafz1.pdf), sections 2.2 and 4.
the numeric Gen 2x1 value and hub-field mapping are also checked against the
[Chromium EC VIF implementation](https://chromium.googlesource.com/chromiumos/platform/ec/+/d1e7a27efbc80e282b3917d1bef7a9a944c00eeb/util/genvif.c).

these drafts are not certification submissions. product identification,
battery/status message support and the complete USB-IF review remain open.
programming and per-port readback remain `NOT_RUN`, each bound to its own
full-flash hash. no controller was programmed during export.

[power allowance](power-envelope.md) separates the input margin from
source tolerance, current regulation and always-on draw.
[physical testing](../release/README.md) still has to establish negotiation,
role changes, current limits, USB signaling and source-path sequencing.
all charging, boot and USB load qualification gates remain off.

the grounded unused GPIOs follow the TI pin guidance. the configuration checker
also verifies their initial levels, pull settings and event mappings, so a
future profile cannot quietly drive one of those pins high.
