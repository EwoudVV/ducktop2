# power revision

16 october 2026, input and standby: added three local selector bypasses,
aligned the three charge-pump capacitors and moved the gauge filter resistor
closer. [placement and checks](source-standby-placement.md) cover the saved
changes. the center now has 867 footprints and 1,792 native unconnected
items, including the six new capacitor pads. no tracks or vias changed.
there are zero physical DRC errors, 342 existing warnings and no new
findings. all 496 power-wiring checks and 173 electrical calculations pass.

16 october 2026, placement: the [charger and Mu supply pass](converter-placement.md)
moves the input shunt closer, adjusts two local capacitors and opens the
Mu switching corridor. seven footprints changed; no routing changed.
the native unconnected count and all physical DRC findings are unchanged.

16 october 2026: fixed the [Mu power-good circuit](mu-power-good.md).
removed the conflicting MCU pull-downs, derived PG from the actual 12 V
rail and replaced the host-active gate with a Schmitt-input part. R2671
is added beside the existing filter. no existing footprint moved and no
routing changed. the center now has 1,786 native unconnected items;
all 173 electrical calculations and 47 firmware host tests pass.

15 october 2026: the [AUX fuse revision](aux-input.md) replaces F190/F195
with low-profile Bel 0678H5000-02 parts and adds a 3 A firmware source-budget
ceiling. the 500 mA initial setting stays unchanged. its separate record
covers the new PCB hashes, unchanged DRC findings and local case fit.
the 5 october table below remains the earlier full-power checkpoint.

updated 5 october 2026. the BMS is routed. the 100 W main boards still need
routing, the complete case fit and hardware tests before ordering.

## current main-board check

all three schematics have zero ERC errors. their numbered pads, nets,
footprints, values and population attributes match the saved PCBs. KiCad's
own schematic comparison also passes after correcting the hidden connector
fields. the short looms specify Alpha 6715, 18 AWG, and the direct USB5 loom
specifies Alpha 6716, 16 AWG, in both the schematics and boards.

| board | footprints | numbered pads checked | native unconnected items |
| --- | ---: | ---: | ---: |
| center | 863 | 3,359 | 1,783 |
| left | 333 | 1,474 | 948 |
| right | 173 | 746 | 331 |

these counts use copied boards after a native refill. the center and left
CLI reports stop at 499 unconnected items, so those report lengths are not
the totals. there were no track/via net changes inferred during native load.

remaining findings after refill:

- center: 174 dangling vias, 83 dangling tracks, 27 silkscreen overlaps and
  60 silkscreen-over-copper findings.
- left: 16 footprint-library warnings.
- right: 3 dangling tracks, 8 dangling vias, 1 silkscreen edge-clearance
  finding and 26 footprint-library warnings.

the separate pad/drill comparison covers all 1,369 main-board footprints
and matches their reference libraries. library warnings still need their
other footprint details and saved review records resolved before release.
some project checks are disabled, including center library warnings; the
machine-readable checkpoint lists those settings. no DRC exclusions were
used. these results are not a fabrication approval.

ERC warnings remain: 404 center, 106 left and 65 right. all are covered by
the [symbol and grounded-pin checks](erc-warnings.md); electrical errors
and unexplained warnings fail. the power check also passes
478 power-wiring assertions and 167 numerical design checks. the updated
battery-shunt calculation uses 8 A, giving 0.7236 W at its upper resistance
corner. it passes the 1.4 W derated component limit used by the calculation.

the [complete center battery-path check](battery-path.md) adds the gauge
shunt, Q25, wire loss and the shared startup bank. R2600 was loading the
charger's gate pump too heavily at 100 kohms. it is now 1 Mohm in the same
footprint, with regression coverage in both the path check and the main
calculation report. Q25 still needs the specified heat-spreading copper
and an installed temperature measurement.

## firmware

the BQ76922 board profile now enables the shared battery-current check during
startup and operation. previously only the older guarded 8 A profile enabled
that check; the BQ76922's own monitor check was already present. regression
tests now use both real profile selections and cover overcurrent, invalid
current, stale samples and an absent limit.

all 46 CMake host tests pass, as does the shell test runner. the BQ76922
revision builds for the EC, with its register definitions, dependency hashes
and 98 interrupt-vector entries checked. charging, startup and transfer
qualification flags remain off. no hardware was programmed or tested.

the source policy reserves standby power and includes shunt, gain and offset
bounds before accepting a charger current. it checks applied limits before
admitting loads. a small adapter can supplement a qualified running battery
load, and charging uses only the remaining external power. tests cover that
behavior and the charger losing or reloading its settings.

## board and case work

the ISL9241 charger, TPS552882 Mu supply, input protection and always-on
circuits are saved in the main-board schematics and placement. the broader
MCU, audio and port placement pass is also saved. this work corrected hidden
connector fields and R2600's value/part number. all main-board positions, copper, zones, holes and
outlines are unchanged. the old and new file hashes are in the checkpoint
so a mechanical export can distinguish these field changes from movement.

the BMS uses a BQ76922, independent current and temperature guards, and a
limited startup path. its targets are 8 A discharge and up to 3 A charging.
the 80 mm board fits the widened center cutout with the existing 1.5 mm gaps.
its [layout and assembly report](../../verification/bms-layout.md) covers the
routed board. the first assembly keeps R870, R871 and R872 unpopulated for
fixture testing; its operating profile is not armed.

the current power links use WAGO 2060 terminals and the separate XT30 USB5
loom. the raw pack uses a two-pole WAGO plus separate JST GH cell taps.
the pack fuse is the 10 A Schurter HCF 3-101-051. finished pack dimensions,
lead exits, strain relief and the complete closed assembly still need to
agree with the case. the old 35 mm study does not establish the final height.

next is the [power routing order](power-routing.md), once the electrical
interfaces and required component/cable envelopes are settled. it covers
the switching loops, Kelvin pickups, ground returns and
checks for each stage. full-load temperatures, voltage drop, stability,
source transitions and the actual cells remain hardware tests.

[checkpoint data](../../verification/power-revision-checkpoint.json)
