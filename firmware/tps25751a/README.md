# TPS25751A port configuration

J21 on the left and J11 on the right are the two PD/data ports. their
controllers use the source configuration in `ducktop2_dual_role_config.json`.
J12 is a source-only USB port and does not use this charging policy.

the recorded export used TI's USB-C/PD Application Customization Tool 2.0.0
and base firmware `FB09.17.02__RC5.bin`. the export filenames and hashes
are in `release_manifest.json`; generated output is kept under `generated/`
and is ignored by git.

## configured policy

- dual-role power, with EC-controlled BQ25798 integration outside the PD controller;
- 5 V, 9 V, and 15 V sink PDOs, up to 3 A;
- a 5 V / 900 mA source PDO;
- one private EEPROM per controller.

advertising a sink PDO does not mean that voltage can run the laptop. the
recorded AON UVLO and selector windows require a qualified usable input,
and the EC must verify the live contract before enabling the sink path.
[power architecture](../../docs/power-and-battery.md)

## verify and use the export

```sh
python3 firmware/tps25751a/verify_config.py
```

run from the repository root. review the configuration and manifest against
the actual generated files before programming the EEPROMs. keep tool version,
source hash, export hash, programmed device/board, and readback evidence.

the configuration export and host tests do not prove physical negotiation,
role swaps, source-path sequencing, or current-limit behavior. those belong
in the [HIL work](../release/README.md).
