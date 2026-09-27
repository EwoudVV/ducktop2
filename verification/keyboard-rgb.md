# keyboard RGB checks

checked 27 september 2026 with KiCad 10.0.4. the LED connections now follow
the physical rows. this is a routing checkpoint, not an order release.

| check | result |
| --- | --- |
| schematic ERC | 0 errors, 0 warnings |
| schematic / PCB parity | 0 differences; 1,096 physical pads checked |
| PCB physical DRC | 4 existing starved-thermal errors; no new errors |
| remaining ground errors | C320 pad 2, C321 pad 2, J320 pads 1 and 30 |
| routing | 1,208 tracks and arcs, 264 vias, 1 ground zone |
| unconnected count after refill | 298, confirmed by native connectivity and DRC |
| board | 4 copper layers, 0.8 mm, original 273.5 x 80 mm outline |
| placement | all 221 footprint positions and pad geometries preserved |
| local LED anode joins | all 65 preserved |
| other routing | switch-matrix, power and I2C copper unchanged |
| switch copper exclusions | all 65 preserved on all four layers |
| driver mapping | 195 unique colour channels; registers 196..198 remain off |
| firmware checks | RGB startup, mapping, updates, fault latch and timer wrap pass |
| row-map checks | four checks pass for row grouping, bank capacity, channel uniqueness and local anodes |

the starting point was the live editor, including unsaved routing. the map
change was applied as one undoable KiCad edit, then refilled and saved.
50 old bank-link segments were removed and 101 were trimmed to retain local
LED and driver wiring. one retained section needed a separate track item.
no vias were removed, moved or added. no new routing was added beyond those
retained portions of the existing tracks.

the old banks linked six neighbouring keys along the rows. the new banks
follow nearby columns, so those old links could join different new nets.
the anode joins at each LED stay connected; the feeds between banks need
routing again. 55 keys use five row-aligned RGB sink groups. the ten extra
keys use the sixth group. the [wiring map](../keyboard/images/rgb-routing-map.png)
and [CSV](../keyboard/rgb-key-map.csv) show the assignments.

all LED positions, switch offsets, pad sizes, 3D models and ground-zone
settings were retained. the filled ground copper was recalculated. the
four ground thermal errors were present before this change and still need
repair. remaining track-end warnings include the retained LED stubs.

the placement checker still verifies the CHERRY component area and copper
exclusions. nominal pad margin is 0.075 mm. the maximum LED body height plus
solder allowance is 0.50 mm against the 0.8 mm drawing limit. the selected
LED, driver, current resistor and power circuit are unchanged.

`gen/check_keyboard_rgb.py` compares the saved board with a fresh XML netlist
and the firmware table. `gen/test_keyboard_rgb_mapping.py` checks the row and
bank structure. `gen/draw_keyboard_rgb_map.py` redraws the wiring reference
from the saved PCB and requires its LED nets to match the source map.
the [machine-readable record](keyboard-rgb.json) contains source hashes and
the current preservation and DRC results.

after routing, rerun DRC and schematic parity, check the exported copper
against the CHERRY exclusions, and prepare the assembly package. physical
LED/switch fit, colour order, full-white current, temperature and I2C checks
still need an assembled board.
