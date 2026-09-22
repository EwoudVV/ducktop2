# keyboard

the RGB revision is ready for routing. it is still two layers and 0.8 mm
thick, with the same 273.5 x 80 mm outline, 65 key positions, diodes and
J320 connector position. the previous tracks, vias and pours are cleared.
the switches, LEDs and cable connector are locked so they do not move by
accident while routing.

open `12_keyboard_daughterboard.kicad_pro` in this folder. the schematic,
PCB, rules and library tables beside it are the current files.

## LEDs and power

i picked Everlight `19-337/R6GHBHC-C02/2T` LEDs, LCSC `C409504`. each is
1.6 x 1.6 x 0.35 mm and has separate connections for all three colours.
the IS31FL3743A driver, U320, handles all 65 keys over I2C at address
`0x2f`. there is no daisy-chained data connection between the LEDs.

each LED sits 2.8 mm above its switch centre in the top view, inside
CHERRY's auxiliary component area. the maximum LED body height is
0.45 mm; allowing 0.05 mm of solder gives 0.50 mm against CHERRY's
0.8 mm limit. the copper pads fit the allowed area too, with a minimum
nominal edge margin of 0.075 mm. check the first assembled LED and switch
before fitting the rest. the LEDs have to go on before the switches.

R320 is 33.2k, 1%. using the driver's published maximum current at its
stated 3.6 V / 25 C test condition and the resistor's low tolerance gives
11.23 mA per active sink. only 18 sinks run at once, so the total is about
0.202 A before logic and pull-ups. the 5 V feed has a 0.25 A design budget,
below U310's roughly 0.4 A nominal limit and J320's 0.5 A contact rating.
this is a design calculation; measure current and driver temperature at
full white on the first assembled board. the scan duty also means the
average current per colour is about 1 mA at full brightness.

the keyboard gets switched 5 V on J320 pin 29. its 3.3 V buffer supply is
pin 2, through the now-populated R387 on the center board. **keep R386
unpopulated**, since it bypasses the current-limited switch. U321 is a
TCA9517A: its A side faces the 5 V driver and its B side faces the 3.3 V
EC bus. this arrangement uses TI's October 2025 datasheet and keeps the
unpowered driver isolated. do not swap its sides or put 5 V pull-ups on
the EC side.

## routing order

1. start with U320's exposed ground pad, supply pins and decoupling.
   keep C322/C323 close to VCC, C324/C325 close to PVCC, and C320 beside
   U321's 3.3 V pin. give the exposed pad a short, broad ground connection
   and a return to bottom ground copper. keep ordinary open vias out of
   the exposed paste area; agree any filled or capped thermal vias with
   the assembler. R320 should have a quiet return to U320's ground.
2. route the 5 V feed and ground returns with at least the selected
   0.5 mm width where space allows. use short neckdowns at fine-pitch pads.
   add ground copper on both layers and enough stitching to keep the
   return continuous around matrix routing. preserve the switch keepouts.
3. route the RGB scan banks. `RGB_SW01` through `RGB_SW11` are common
   anodes, with up to six nearby keys on each bank. `RGB_CS` nets are
   shared colour sinks. red channels pass through R330-R335 and become
   `RGB_RED` nets. the [key map](rgb-key-map.csv) lists every connection.
   the selected widths are 0.4 mm for bank feeds and 0.2 mm for sinks.
4. route the keyboard matrix and I2C at 0.2 mm. there is no controlled
   impedance requirement here. keep I2C away from long parallel LED power
   runs, and keep the driver-side pull-ups local. do not add extra EC-side
   pull-ups. the matrix diode direction is already set in the schematic.
5. add ground stitching, refill, and run DRC with schematic parity.
   check the full native unconnected count: the CLI report stops at 499.
   the untouched placement starts at **960 unconnected items**.

the minimum clearance and track width are 0.15 mm, with 0.5/0.2 mm vias.
these are routing settings, not a factory approval. confirm the final
0.8 mm stackup and manufacturing limits when ordering.

the 65 CHERRY copper-free rectangles apply on **both layers**. do not
put tracks, vias, pads or pours in them. the custom courtyard rules allow
only each LED to sit under its matching switch. every other courtyard
check stays active. those exceptions depend on the checked LED offset
and body height, so leave the locked LED positions alone.

## firmware and checks

the EC now initialises the driver, loads all channels before enabling
light, and cuts RGB power on an I2C failure or the power-switch fault
signal. the existing host enable command turns on white at 64/255
brightness. per-key RGB and brightness functions are available in the
firmware; a desktop colour picker and animation controls are still to do.
updates happen one bank per main-loop call, so this is a static backlight
driver, not a high-frame-rate effects engine.

the [placement checks](../verification/keyboard-rgb.md) record the current
results. this revision has no fabrication package yet. after routing,
recheck the switch exclusions against the actual exported copper, then
prepare a new BOM, placement file and assembly sequence for the LEDs,
support parts and switches. the old passive-keyboard exporter refuses
this revision until its assembly contract is updated.

part drawings used here: [Everlight LED](https://www.endrich.com/Datenbl%C3%A4tter/Lichtl%C3%B6sungen/Everlight/RGB%20LED/19-337R6GHBHC-C022T.pdf),
[Lumissil driver](https://www.lumissil.com/assets/pdf/core/IS31FL3743A_DS.pdf),
[TI buffer](https://www.ti.com/lit/ds/symlink/tca9517a.pdf), and CHERRY's
VS-10107 revision 03 / PCB-MX-ULP sample drawings.
