# keyboard RGB placement checks

checked 22 september 2026 with KiCad 10.0.4. this is the starting point for
routing, not an order release. the saved project is in `keyboard/`.

| check | result |
| --- | --- |
| schematic ERC | 0 errors, 0 warnings |
| PCB physical DRC | 0 errors, 0 warnings, no disabled PCB checks |
| schematic / PCB parity | 0 differences; 1,096 physical pads checked |
| routing | 0 tracks, 0 vias, 0 copper pours |
| native unconnected count | 960; the CLI's list stops at 499 |
| board | 4 copper layers, 0.8 mm, original 273.5 x 80 mm outline |
| original placement | all 65 switches, 65 diodes and J320 preserved |
| RGB placement | all 65 LEDs at the checked switch-relative offset |
| switch copper exclusions | all 65 extended to all four copper layers |
| driver mapping | 195 unique colour channels, 3 unused channels kept off |
| part identities | 215 populated components have manufacturer and MPN; 6 test pads excluded |
| EC target build | ARM build passed |
| firmware host checks | 30 tests passed, including RGB startup, mapping, updates and fault shutdown |

the courtyard rules allow each LED beneath its matching switch. the
placement checker separately checks the allowed CHERRY component area,
pad envelope, orientation and offset. no other component pair gets that
exception. the LED's maximum body height plus the solder allowance is
0.50 mm against the drawing's 0.8 mm limit.

the driver pinout and exposed-pad land came from Lumissil's IS31FL3743A
revision C drawing. LED pins and lands came from Everlight's C02 revision
4 drawing, not the different A01 part. the buffer supply arrangement uses
TI's TCA9517A revision E datasheet. CHERRY's VS-10107 revision 03 and
PCB-MX-ULP DXF set the switch-local LED position and copper-free area.
the source links and routing order are in [keyboard notes](../keyboard/README.md).

the center-board change fits R387 as a 0 ohm link for the buffer's 3.3 V
supply. its pads, position and nets are unchanged. R386 remains DNP.

`gen/check_keyboard_rgb.py` checks the saved board against a fresh XML
netlist using KiCad's Python. it also checks the firmware colour map,
connector contacts, LED positions and keepouts. use `--expect-unrouted`
only for this starting placement; omit it once routing begins.
the [machine-readable record](keyboard-rgb.json) includes source hashes.

after routing, rerun native DRC, refill and save, check the exported copper
against the CHERRY exclusions, and prepare the revised assembly package.
on the first board, check LED/switch fit, all key positions, colour order,
full-white current, driver temperature and I2C behaviour with RGB power
off. those physical checks have not happened yet.
