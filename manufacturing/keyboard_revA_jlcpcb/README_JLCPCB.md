# Ducktop2 keyboard rev A: JLCPCB production package

## Upload these three files

1. `ducktop2_keyboard_revA_GERBERS.zip` in the PCB Gerber upload field.
2. `ducktop2_keyboard_revA_BOM.csv` in the PCBA BOM field.
3. `ducktop2_keyboard_revA_CPL.csv` in the PCBA CPL/Pick-and-Place field.

The BOM and CPL use JLCPCB's current required headers. Every designator in the
BOM appears in the CPL. All 66 JLCPCB placements are on the top side.

## PCB order selections

- 2 layers, FR-4, 1 oz copper
- Finished size: 273.5 x 80.0 mm
- PCB thickness: 0.8 mm
- Green solder mask and white silkscreen
- Economic PCBA-compatible finish: lead-free HASL
- Assembly side: top
- Remove the JLC order number, or approve its location manually

JLCPCB permits 0.8 mm Economic PCBA with green solder mask and lead-free HASL.
Because this is a long 0.8 mm board, expect a carrier/fixture charge.

## Parts

- D320-D384: JLCPCB basic part `C2128`, 1N4148WS, SOD-323.
- J320: LCSC/JLC part `C506793`, Hirose FH12-30S-0.5SH(55). Stock can change;
  pre-order/global-source it before submitting the PCBA order if requested.
- SW320-SW384: DNP for JLCPCB. Install CHERRY `MX6C-T3NB` switches separately
  using the user's stencil/paste and hot plate after receiving the boards.

Paste printed and reflowed on empty MX ULP pads can leave solder bumps that
prevent the switches from sitting flat. Copy the contents of
`PCBA_ORDER_REMARK.txt` into the order remarks and confirm the production file
does not print paste on SW320-SW384.

## Placement review

JLCPCB requires the customer to review the assembly preview. Before approval:

- Confirm every diode cathode stripe agrees with pad 1/the line on F.Fab.
- Confirm J320 is a bottom-contact connector and its FFC opening faces outward.
- Before mating the keyboard to the motherboard, follow
  `../../verification/KEYBOARD_FFC_ASSEMBLY_CONTRACT_2026-07-15.md`; the cable
  orientation and every power/ground contact must be continuity-tested unpowered.
- Confirm SW320-SW384 are absent from the placement preview.
- Confirm the board outline is 273.5 x 80.0 mm, not 300 mm wide.

The CPL coordinates deliberately retain KiCad's Gerber coordinate system,
including negative Y values. The Gerbers and CPL therefore share the same
origin and orientation.

## Fabrication archive contents

- `ducktop2_keyboard_revA-NPTH.XLN`
- `ducktop2_keyboard_revA-PTH.XLN`
- `ducktop2_keyboard_revA.GBL`
- `ducktop2_keyboard_revA.GBO`
- `ducktop2_keyboard_revA.GBS`
- `ducktop2_keyboard_revA.GM1`
- `ducktop2_keyboard_revA.GTL`
- `ducktop2_keyboard_revA.GTO`
- `ducktop2_keyboard_revA.GTS`
- `ducktop2_keyboard_revA.gbrjob`

## Reference files

The `reference` directory is not uploaded in the normal order flow. It contains
the DRC report, assembly drawing, drill map, raw placement export, board stats,
IPC-D-356 netlist, and SHA-256 checksums.

Generated with KiCad 10.0.4 on 2026-07-08.
