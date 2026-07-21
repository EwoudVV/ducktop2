# TPS25751A port policy

The two rear USB-C ports use the same TPS25751A configuration. They accept
USB-PD power for the laptop and act as USB hosts when they are supplying power.

The tracked source file is `ducktop2_dual_role_config.json`. It was exported
from TI's USB-C/PD Application Customization Tool 2.0.0 with base firmware
`FB09.17.02__RC5.bin`.

Current policy:

- DRP power role, no BQ25798 integration inside the TPS25751A
- 5 V, 9 V, and 15 V sink PDOs at up to 3 A
- one 5 V / 900 mA source PDO with default Rp
- USB host data only; the laptop never exposes itself as a USB device here
- GPIO4: inverted `UFP_DFP` event, high only while the port is DFP
- GPIO6: cable orientation
- GPIO7: `Dp_Dm_Mux_Enable`, high only while the USB data path is attached

GPIO4 and GPIO7 are ANDed in hardware before either USB2 or SuperSpeed is
enabled. Both data paths therefore stay disconnected during reset, detach, and
sink-only operation.

To regenerate the EEPROM files:

1. Open TI's USB-C/PD Application Customization Tool 2.0.0.
2. Select TPS25751A and base firmware `FB09.17.02__RC5.bin`.
3. Import `ducktop2_dual_role_config.json` with advanced configuration enabled.
4. Export all files using the name `ducktop2_dual_role`.
5. Put the raw JSON, VIF, low-region binary, and full-flash binary in
   `generated/` using the names recorded in `release_manifest.json`.
6. Run `python3 firmware/tps25751a/verify_config.py --require-generated`.

The generated images are ignored by Git because TI's firmware license does not
allow us to redistribute them. `release_manifest.json` records their expected
hashes so the exact production images can still be checked locally.
