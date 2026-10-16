# input selection and standby placement

16 october 2026. added three local bypass capacitors, moved four existing
parts and corrected two stale power-sheet notes. the center board stays
eight layers. tracks, vias, connectors, mounting holes and outlines are
unchanged.

## selector bypasses

U16 had no bypass on its V1 input or VS1 common-source node. C2686 and
C2687 now cover those connections. C2688 adds a small local VOUT bypass
at U15 alongside the existing output capacitance. all three use Murata
GRM188R71H104KA93D, 100 nF, 50 V, X7R, in 0603 footprints on the back.

| ref | connection to GND | board X, Y in mm | rotation |
| --- | --- | --- | --- |
| C2686 | U16 V1, PD2_VBUS_GATED | 181.7, 156.3 | 180 degrees |
| C2687 | U16 VS1, ST2_USB_FET_COMMON | 186.3, 152.7 | 90 degrees |
| C2688 | U15 VOUT, VBUS_COMBINED | 130.4, 182.0 | 0 degrees |

C747's value label now identifies U15 VS2 correctly. its connection to
ST2_MAIN_FET_COMMON did not change.

keep the new connections short, with nearby layer transitions and ground
returns. the capacitors sit on the opposite side from the controllers, so
their XY spacing does not include the vias or board thickness. the
[LTC4418 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4418.pdf)
shows the input and common-source bypasses in its application circuits and
discusses input/output bypassing for transients. final transfer waveforms
still need checking on hardware.

## charge pumps and battery measurement

C2620, C2621 and C2650 are now centered above their LM74700 controllers
and rotated 180 degrees. each bridges VCAP and ANODE with a balanced
placement. the sum of the two straight pad-center distances drops from
6.37 to 3.77 mm. the VCAP leg itself is slightly longer; the ANODE leg is
substantially shorter. these are placement distances, not routed lengths.
the [LM74700 layout guidance](https://www.ti.com/lit/ds/symlink/lm74700-q1.pdf)
calls for the charge-pump capacitor close to those pins.

R183 moves to 201.160001, 180.1 mm on the front, still at 90 degrees.
its filtered pad is now 1.475 mm from C181's matching pad, down from
3.296 mm. route the gauge sense connections as dedicated pickups from
RS1 and keep the filter local to U10. FG_VSS must reach GND through RS1.

the U718 voltage protector, U2660 current limiter and U5 standby buck keep
their placements. use dedicated sense pickups at RS2660/R2662, balanced
load connections and a short gate path. keep U5's input switching loop
local and its feedback return clear of switching copper.

## saved checks

- zero physical DRC errors, 342 existing warnings and no new findings;
  two previous silkscreen findings are resolved.
- zero native schematic-parity findings; all 3,366 numbered pad records
  match the 867-footprint center board.
- zero ERC errors; all 406 warnings match the checked library templates.
- 496 power-wiring checks, 173 electrical calculations and 2,073 pin
  contract rows pass. the standby and battery-path calculations also pass
  their static limits.
- 17 power regression tests, nine battery-path tests and two headless-tool
  tests pass.
- 1,792 native unconnected items remain. the six-item increase comes from
  the three new unrouted capacitors. the 4,481 track/arc items and 722 vias
  are unchanged.

the complete component export now contains 1,373 parts. the older selected
power-group export contains 209 parts and does not include every selector
capacitor. use the complete export for mechanical coverage.

the three new capacitors have a 0.9 mm maximum body-height entry and a
0.3 mm underside assembly allowance. the current case datum leaves 1.5 mm
to the floor locally. this is a height comparison; the full case model
still uses its earlier PCB snapshot.

[saved source hashes and results](../../verification/source-standby-placement.json)
identify this pass. main-board routing, startup and source-transfer tests,
installed temperatures and complete mechanical fit remain unfinished.
