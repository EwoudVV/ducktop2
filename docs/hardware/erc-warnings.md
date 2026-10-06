# remaining schematic warnings

5 october 2026. the center, left and right schematics have zero ERC errors.
their 575 warnings have been checked against the saved symbols, connections
and controller configuration. no circuit or PCB changed during this pass.

| cause | center | left | right |
| --- | ---: | ---: | ---: |
| project footprint filters on stock symbols | 394 | 97 | 57 |
| flattened stock symbol variants | 10 | 2 | 2 |
| unused PD GPIOs tied to ground | 0 | 6 | 6 |
| redriver adaptive-EQ strap | 0 | 1 | 0 |
| total | 404 | 106 | 65 |

## symbol copies

the footprint-filter warnings cover resistors, inductors, test pads,
mounting supports, connectors, the I/O expander and maker flash. their
cached pin numbers, names, types, positions and units match the stock
symbols. the added filters let those symbols use the specific project
footprints.

the other library warnings are the 74AHCT1G126, TPD4E05U06DQA and
TLV9061xDBV variants. the generator embeds their inherited geometry so the
schematic contains the complete symbol. KiCad compares that against the
shorter stock child definition.

[erc-symbols.json](../../verification/erc-symbols.json) records the checked
templates and library hashes. the checker compares every warned instance
with its exact current template. changed pins, a different library revision
or an unknown symbol must be checked again. this classification does not
waive a wrong footprint or a board connection error.

## grounded pins

U41 and U42 pins 5, 6, 7, 13, 19 and 27 are unused GPIOs. TI explicitly
recommends grounding them. the exported PD profiles keep those pins
inactive; their levels, pulls and event mappings are checked against the
source configuration, binaries and original archives. a profile change
cannot reuse this result without passing those checks.

[TPS25751 pin functions](https://www.ti.com/lit/ds/symlink/tps25751.pdf),
[TI's unused-GPIO clarification](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1571870/tps25751-clarification-on-handling-unused-gpios-in-tps25751s)

U2000 pin 22 is AEQENZ in pin-strap mode. grounding it enables adaptive
equalization. R2008 is the 1 kohm MODE pull-down that selects that mode.
the checker requires both connections and the correct resistor part.

the TUSB1142 package illustration disagrees with its pin-function table
on the second connector-facing pair. the saved circuit matches Table 4-1
and the evaluation-board schematic: CRX2 is pins 36/37 and CTX2 is pins
39/40. those connections were retained.

[TUSB1142 pin and mode tables](https://www.ti.com/lit/ds/symlink/tusb1142.pdf),
[evaluation-board schematic, page 8](https://www.ti.com/lit/pdf/sllu350)

## checker changes

the old schematic checker had 15 exceptions for undriven inputs, undriven
power inputs and dangling labels from an earlier board split. those error
exceptions are removed. every ERC error now fails the check.

warnings are matched to actual symbol and pin UUIDs, component identities,
ground connections and the required configuration. unrelated warnings fail.
the existing KiCad warnings stay visible, and no project ERC rule was
disabled to get this result.

run `gen/check_schematic.py --skip-regenerate` for the saved center design.
`gen/verify_erc_warnings.py` can also check a fresh center, left or right
ERC report with its schematic and XML netlist. all 13 regression tests pass.
the staged release checker runs this review on all three main boards.
the main boards still need their routing, physical DRC cleanup and hardware
tests before manufacture.
