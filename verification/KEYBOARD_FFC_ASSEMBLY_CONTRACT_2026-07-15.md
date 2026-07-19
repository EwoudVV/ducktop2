# Keyboard FFC Assembly Contract

Date: 2026-07-15

This is a release requirement for the cable between motherboard J310 and
keyboard J320. It is not optional bring-up advice.

## Locked Parts

- J310 and J320: Hirose `FH12-30S-0.5SH(55)`, 30 positions, 0.5 mm pitch,
  bottom-contact ZIF, mounted on the top side of each PCB.
- Cable: Molex `0150200315`, 30 positions, 0.5 mm pitch, nominal 30 mm length,
  Type A with contacts on the same side.
- Do not substitute a Type D/opposite-side FFC or a top-contact connector without
  regenerating the pin map and repeating this complete procedure.

Manufacturer references:

- Hirose FH12-30S-0.5SH(55): https://www.hirose.com/product/p/CL0586-0525-1-55
- Molex Premo-Flex contact-layout guide: https://www.molex.com/content/dam/molex/molex-dot-com/en_us/pdf/solutions-guide/987652-1121.pdf

## Intended Physical Mapping

With the two top-mounted bottom-contact connectors oriented as released and the
Type-A cable installed without a twist, motherboard physical pin `n` reaches
keyboard physical pin `31-n`. The generated schematics encode that reversal.

Critical examples:

| Motherboard J310 | Keyboard J320 | Function |
|---:|---:|---|
| 1 | 30 | GND |
| 2 | 29 | protected keyboard 5 V |
| 27 | 4 | I2C SDA |
| 28 | 3 | I2C SCL |
| 29 | 2 | keyboard 3.3 V |
| 30 | 1 | GND |

The row/column contacts follow the same `n -> 31-n` rule. The production pin map
in `gen/generate_keyboard_interface_sheet.py` and
`gen/generate_keyboard_daughterboard_sheet.py` remains the electrical source of
truth.

## Mandatory Unpowered Inspection

1. Verify both connector labels and suffixes under magnification.
2. Verify both connectors are bottom-contact and record a clear photo showing
   PCB pin 1, actuator, cable contact face, and cable exit direction.
3. Inspect for solder bridges, lifted contacts, damaged actuator locks, skewed
   cable insertion, and exposed conductors touching shields or chassis metal.
4. Keep the battery, USB, debug probes, and all other power sources disconnected.

## Mandatory Continuity Test

Use a current-limited continuity meter or ohmmeter. Probe PCB pads or dedicated
test points rather than forcing meter tips into the ZIF contacts.

1. Verify every J310 pin has continuity only to the expected J320 pin according
   to `n -> 31-n`; record all 30 results.
2. Verify J310 pins 1 and 30 reach only keyboard ground contacts.
3. Verify J310 pin 2 reaches only the keyboard 5 V input contact.
4. Verify J310 pin 29 reaches only the keyboard 3.3 V contact.
5. Verify no power contact is shorted to ground, I2C, any row, or any column.
6. Verify adjacent-pin isolation across all 30 contacts. Any unexpected
   continuity is a hard stop.

## First Powered Test

1. Power the motherboard from a bench supply with the battery absent and the
   keyboard disconnected. Confirm J310 ground continuity. For the released
   rev-A build, J310 pin 29 (3.3 V option through DNP R387) must remain
   high-impedance/unpowered, and J310 pin 2 (future RGB 5 V through U310) must
   remain off until the EC deliberately asserts `KB_RGB_PWR_EN`, the active
   enable net at U310 pin 3.
2. Remove power, attach the verified cable and keyboard, then repower with a
   conservative current limit.
3. Confirm neither connector, cable, protection part, nor keyboard component
   heats. Confirm the rev-A keyboard receives no unintended power on its DNP
   3.3 V/5 V option contacts. A future RGB build requires a separately released
   assembly variant, current budget, and powered-test procedure.
4. Only after the power checks pass, test I2C and the complete key matrix.

Any connector, footprint, cable, board-orientation, or pin-map change invalidates
this contract until the mapping is redrawn and all continuity tests are repeated.
