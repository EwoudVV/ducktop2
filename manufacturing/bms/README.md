# bms

this is the four-layer, 80 x 36.148 mm revision for stronger battery operation.
it uses a BQ76922, a 2 milliohm four-terminal shunt, high-side protection FETs
and separate charge and discharge current guards. the design targets 8 A
out and up to 3 A charging.

R870, R871 and R872 are left out of the first assembly. the board needs its
configuration, current measurements, startup and fault response tested before
those links go on. the battery cells and wiring also need their current ratings
confirmed. these files describe an unarmed prototype.

- [pcbway package](bms_PCBWAY.zip)
- [gerbers and drills](pcbway/bms_GERBERS.zip)
- [assembly BOM](pcbway/BOM.csv) and [SMT placements](pcbway/CPL.csv)
- [board and assembly settings](pcbway/README.md)
- [front assembly view](front-assembly.svg)
- [back assembly view](back-assembly.svg), viewed from underneath
- [test-point map](test-points.csv), in the PCB file's mm coordinates
- [front artwork](front.png) and [back artwork](back.png)

all five cable connectors are on top, facing the rear or right edge.
J2 is the raw-pack WAGO: pin 1 negative, pin 2 positive. follow the
printed polarity marks. J2201 carries
the two cell taps separately. the protected output uses J2072. keep the raw,
protected and isolated control returns separate, including mounting hardware.

there is one 0.2 mm ground via in the BQ76922 exposed pad. nominal paste
does not overlap its hole, but one paste edge has no registration margin.
the opposite face is tented. pcbway needs to confirm the tent closure,
stencil alignment and solder-wicking/voiding process, or quote filling
or plugging for that via before assembly.

compare one and two assembled boards from the same bare-board batch.
pcbway still needs to confirm the sourced parts, copper, hole plating and
assembly-panel details in its quote. no order has been placed.
