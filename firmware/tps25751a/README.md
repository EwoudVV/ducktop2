# TPS25751A port configuration

J21 on the left and J11 on the right are the two PD/data ports. their
controllers use the source configuration in `ducktop2_dual_role_config.json`.
the fresh official TI export includes fixed 5 V, 9 V, 15 V and 20 V sink
PDOs at 3 A. the source configuration is the raw JSON normalized by that
export; the manifest binds its binaries and per-port pending readback.
J12 is a source-only USB port and does not use this charging policy.

the recorded export used TI's USB-C/PD Application Customization Tool 2.0.0
and base firmware `FB09.17.02__RC5.bin`. the export filenames and hashes
are in `release_manifest.json`; generated output is kept under `generated/`
and is ignored by git.

## configured policy

- dual-role power, with EC-controlled BQ25798 integration outside the PD controller;
- 5 V, 9 V, 15 V and 20 V sink PDOs, up to 3 A;
- a 5 V / 900 mA source PDO;
- one private EEPROM per controller.

advertising a sink PDO does not mean that voltage can run the laptop. the
recorded AON UVLO and selector windows require a qualified usable input,
and the EC must verify the live contract before enabling the sink path.
[power architecture](../../docs/hardware/power-and-battery.md)

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


## export and pending device readback

the inactive 20 V / 5 A sink slot was replaced with 20 V / 3 A before the
valid-PDO count was increased. source output remains 5 V / 900 mA. the
verifier checks every active sink PDO and rejects the old three-PDO export.
`--require-generated` verifies the six fresh exports against the source and
manifest. the low-region image is present twice in the full-flash image, and
the critical register payloads must match both. PD1 and PD2 programming and
readback fields remain NOT_RUN, bound to the expected full-flash SHA-256.

the official 2.0.0 application generated the files after the two separate
TI tool and commercial firmware agreements were explicitly approved. its
normalization dropped legacy register 0x27 and empty 0x73, resized reserved
padding at 0x28, 0x29, 0x78 and 0x98, and preserved every shared register
value. no physical controller or EEPROM was programmed.

[power allowance](power-envelope.md) separates nominal 0.50 A from actual
current-regulation and source-tolerance bounds. none of these source changes
approves real-cell charging, a boot envelope or a completed EEPROM readback.
