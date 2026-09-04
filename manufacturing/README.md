# manufacturing

the current boards are still in layout and review. [project status](../docs/design-status.md)
lists the issues that remain before an order package can be prepared.

## separate board packages

| Board | Source PCB | Current stackup basis |
| --- | --- | --- |
| Center | `ducktop2-center.kicad_pcb` | Eight-layer NextPCB record |
| Left I/O | `left_io/left_io.kicad_pcb` | Eight-layer layout; confirm the actual order against the approved stackup |
| Right I/O | `right_io/right_io.kicad_pcb` | Eight-layer layout; confirm the actual order against the approved stackup |
| BMS | `bms/bms.kicad_pcb` | Four-layer intent conflicts with eight enabled layers; unresolved |
| Radio | `radio_daughterboard/radio_daughterboard.kicad_pcb` | Four-layer placement board; fabrication details still to finalize |
| Keyboard | `12_keyboard_daughterboard.kicad_pcb` | Existing separate two-layer rev A package |

the old monolith and the older quote package are reference material. do not
use them as a substitute for packages from the current split-board files.

## first-article package

for each board, retain:

1. The reviewed schematic, PCB, project rules, libraries, and source revision,
   including any working-tree changes used to generate the package.
2. Fresh schematic-to-board comparison, DRC with reviewed exceptions, and
   a check of refilled zones and final output geometry.
3. Confirmed layer count, stackup, copper weights, finish, thickness,
   impedance requirements, drills, and outline tolerances.
4. Gerbers, drills, IPC-D-356 netlist, BOM, CPL, assembly drawings, and DNP/
   hand-assembly notes that all come from that same revision.
5. Connector/cable compatibility, component sourcing/substitutions, mechanical
   support, test access, and programming/recovery provisions.
6. Fabricator/assembler DFM feedback and the current quote/order selections.
7. A reviewed first-power plan with the fixtures needed to test the prototype.

inspect the generated layers and drill files. check pad orientation and
placement rotations against the assembler's interpretation. regenerate the
IPC-D-356 file after routing/placement changes; the earlier exports are not
the final bare-board test set.

hardware validation follows on the first articles. a later production release
needs the recorded HIL, thermal, interface, display, and other system tests.
those results cannot be claimed from schematic checks or required as already
measured before the first prototype exists.

## stackup and rule records

[`mainboard_stackup_release.json`](mainboard_stackup_release.json) holds
the approved eight-layer geometry, including the 24/25 August NextPCB
field-solver results. use `approved_trace_geometries`, not the older
candidate values. confirm the stackup applies to the exact board and order.

the release checker still has board-selection/path defects recorded in the
project status. fix those before relying on its fabrication stage to cover
every board. an explicit one-board check does not cover the whole laptop.

## existing keyboard package

[`keyboard_revA_jlcpcb/README_JLCPCB.md`](keyboard_revA_jlcpcb/README_JLCPCB.md)
describes the package that was prepared for the separate keyboard revision.
keep its reference hashes and assembly notes with it. it is not regenerated
as part of this documentation update.

## cost and retained evidence

quotes and sourcing assumptions belong in [parts and cost](../docs/bom-and-cost.md).
store final packages and their manifests in this project, with board-specific
names. keep a separate record for each first article and its test results.


## rule exceptions

| Area | What to check |
| --- | --- |
| Fine-pitch package pads | The exact footprint and manufacturer drawing; keep the exception local to the intended part/pad pair. |
| Mu standoffs | Locating hole, solder land, mask opening, module support, and actual assembly clearance. |
| Microphone | Acoustic opening, ground ring, copper/hole spacing, and the finished acoustic channel. |
| Connector/chassis edges | Intended exposed geometry versus an accidental copper-edge violation. |
| Track, PTH, NPTH, and via spacing | Active constraints for the actual item pair and the chosen fabrication process. |
| Courtyards | Physical part bodies, component height, assembly/rework access, and the correct board. |
| Shunts and power parts | Actual pads/current paths and sensing layout, not an old explanatory label. |

an exception in the rule file explains why a finding may be suppressed. it
does not prove a vendor approved it or that the physical assembly fits.
retain the drawing, measured geometry, and fabricator/assembler disposition
for each exception used in the final package.
