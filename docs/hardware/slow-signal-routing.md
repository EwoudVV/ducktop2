# slow signals and ground fan-out

12 november 2026. two passes over the open nets on the center board:
the ground fan-out, then the rest of the slow digital lines. the
special-attention nets apart from ground are still open; they get
routed by hand.

## ground fan-out

ground had 364 open connections: pads sitting on their own, with nothing
taking them down to the ground planes. each one now gets a via right beside
the pad on a short 0.3 mm stub.

- the via has to land on the ground plane right next to the pad's side
  (In1 for the front, In6 for the back), well inside the fill.
- it's the board's usual 0.6/0.3 mm ground via where it fits, then
  0.5/0.25 and 0.45/0.2.
- it sits at least 0.15 mm off its own pad (no via in a solder pad) and
  within 0.9 mm of it (1.6 mm for four of the ec's decoupling caps).
- a ground pin right next to its chip's exposed ground pad gets a short
  stub to that pad instead of a via.
- no vias under the body of a chip with an exposed pad.
- no via inside another part's escape ring (see below). a part's own
  ground pins may have theirs there.
- the microphone MK430 is left out: its ground ring sits around the
  acoustic port, which has its own clearance rule and keep-out.
- every via and stub is checked against the board rules with exact
  geometry, including the vias placed before it.

324 pads got a via or a stub, and ground went from 365 separate pieces to
49. these 44 pads are left for hand work:

| pads | why |
| --- | --- |
| C903 to C915, C935 | maker mcu decoupling on the back under U901: the only spots are under the chip body, between the pins and the exposed pad |
| C202, C208, C209, U4.20, U4.27 | around the ec: no spot outside its escape ring within 1.6 mm |
| SW1, SW2, SW3, SW901 pin 2 | the second of two pads with the same number |
| J16, J2073, J420, J53, J54 mounting pads | through-hole or mechanical pads, left for a look by hand |
| MK430.2, MK430.4 | the microphone, by hand |
| C29, C39, C444, C445, C781, C2283, Q62, Q901, U44.21, U771.2, U2300.2, U2302.3, U2303.5, U2305.2, U901.47 | no spot that clears everything, or a keep-out in the way |

![ground fan-out: a via beside each loose ground pad](../images/journal/2026-11-12-ground-fanout.png)

## slow signals

the rest of the slow group: 232 nets with 341 open connections. the
ground vias were already in place, so the routes go around them.

new rules since the ec pass:

- escape rings: within 0.7 mm of the pads of a fine-pitch part (12 or
  more pads at 0.65 mm pitch or finer), only nets with a pin on that part
  may route or put vias. without this, other nets ran along the pin rows
  of the ec and the maker mcu and walled their pins in.
- rule areas inside footprints now count, like the shell copper
  exclusions on FPC102 and FPC103 and the via keep-outs on J4 and J902.
- no tracks inside the pin ring of a chip with an exposed pad, and no
  vias under its body. a QFP like the ec has no exposed pad, so routing
  under it stays allowed, the same as the ec pass.
- the extra costs near special-attention pads, high-speed tracks and
  switch nodes now add up instead of multiplying, and the total is
  capped at six times the plain cost. multiplying them made a couple of
  short nets loop around the whole board.
- the straight-line path between pieces of a still-split special
  signal net (pairs, sense lines, crystals, audio, rf) costs more, so
  the slow routes leave it open.
- a via inside another part's courtyard costs extra.
- afterwards, every special-attention pad that still needs routing was
  checked for via room within 1.5 mm. where the slow routes took the
  last spot, that spot was reserved and the slow nets in the way were
  rerouted around it.
- a final pass with clean costs picked up the connections that failed
  late in the congestion passes.

| | result |
| --- | ---: |
| open connections at the start | 341 |
| routed | 239 |
| nets now fully connected | 134 of 232 |
| track | about 10.7 m |
| vias | 610 (median 3 per net, most 20) |
| length against the shortest tree, median | 1.22 |

![the slow signal group, routed](../images/journal/2026-11-12-slow-group-overview.png)

![around the ec, U44 and the usb hub](../images/journal/2026-11-12-slow-group-ec.png)

![the maker header and its mcu](../images/journal/2026-11-12-slow-group-maker.png)

## not routed

102 connections are still open. almost all of them are pins walled in by
copper or parts that were there before this pass:

| part | open pins | what's in the way |
| --- | ---: | --- |
| U901 (maker mcu) | 17 | the bottom row faces R906 and R919 only 0.6 mm away; that fits one track for six pins. the rest sit behind its decoupling parts |
| U4 (ec) | 14 | the bottom and right rows face R2310, R2320, C209 and the existing tracks around them |
| FPC102, FPC103 | 15 | the shell copper exclusion and the pins' neighbours leave no way out for these |
| U44 | 6 | pins between the existing routing on both sides |
| A1, U400, others | about 50 | single pins in the same kind of pocket |

these need small placement moves (mostly resistors and capacitors right in
front of fine-pitch pins) before they can be routed. the hub straps R402
and R403 sit 0.4 mm from their U400 pins, which is too close to bridge
straight across.

## checks

| check | result |
| --- | --- |
| physical DRC | zero new findings against the board before this pass, refilled the same way |
| exact clearance | no problems, all new copper against the old and itself, arcs checked as arcs |
| native unconnected items | 1,255 before, 700 now |
| schematic parity | passes: 870 parts, 3,372 physical pads, no net, value or footprint changes |
| via nets | all 917 new vias keep their nets after refill |
| placement exports | regenerated; only the board hash changed, all 212 power rows and 1,378 component rows still match |
| case | no parts moved, so nothing new to screen |

## weak spots

- 19 special-attention pads have no via spot within 1.5 mm any more,
  mostly to the ground fan-out: the ec's crystal pins U4.12/13 and usb
  pins U4.70/71 with R200, decoupling pads C24, C30, C909, C911, C913,
  and a few others. the crystal and usb lines will likely run on the
  surface anyway, but the power pads need a look before routing them.
- 333 track pieces under 0.15 mm, mostly one-cell jogs at vias and pads.
- ground stubs run straight from the pad to the via at whatever angle
  that is, not on 45 degree lines.
- 16 slow nets are more than twice their shortest length, and some nets
  change layers a lot (up to 20 vias).
- nothing reserves room for the power feeds and the other rails yet;
  they come with the In4 power map.
