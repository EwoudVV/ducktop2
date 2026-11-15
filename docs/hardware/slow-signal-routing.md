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

## reroute with fan-outs first (13 november)

i went in to move the parts in front of the walled-in pins, but checking
each pocket showed that placement was rarely the real problem:

- most pins were walled in by routing order. nets that happened to route
  first took the escape room next to U4, U901 and the fpc connectors, and
  the pins routed later had nowhere left to go.
- the pins on FPC102 and FPC103 already had a short stub and a via each
  from earlier work, but the router only started from pads, and the pads
  themselves are boxed in by their neighbours.
- six of U4's bottom pins open into a closed triangle inside the QFP,
  formed by two ec routes and two vias, with the inner layers under it
  full.

so instead of moving parts, i ripped up the 105 slow nets that had copper
near the dense parts and routed them again in a better order:

- fan-out first: every slow pin on those parts that is still on its own,
  with its partner more than 4 mm away, gets a stub and a via before
  anything else routes there. on a QFP like the ec the via may go under
  the body. 74 found a spot; the 43 the router didn't end up using were
  removed again.
- a net can now start from the vias already wired to its pads, not only
  from the pads.
- via spots within 1.5 mm of a net's own pads are checked exactly instead
  of with the grid allowance.
- every special-attention pad that lost its last via spot against the
  board before this pass got that spot reserved, and the nets in the way
  were rerouted. 116 spots are reserved in total.
- the board outline's arcs (the BMS cutout corners) are now followed
  properly; before, one route came too close to a curved corner.

| | before | after |
| --- | ---: | ---: |
| open slow connections | 102 | 62 |
| slow nets fully connected | 134 of 232 | 171 of 232 |
| native unconnected items | 700 | 660 |

![slow signals, rerouted with fan-outs first](../images/journal/2026-11-13-slow-reroute-overview.png)

![FPC103: the routes start from the vias beside the pins](../images/journal/2026-11-13-slow-reroute-fpc103.png)

![around the ec, with fan-outs under the QFP body](../images/journal/2026-11-13-slow-reroute-ec.png)

## clean reroute (13 november, second pass)

the routes above connected, but they looked messy: staircases, long runs
on the outer layers, routes hopping between layers, and nets wandering
around instead of running in neat lanes. the older routing on these nets
had the same problem. so i took all of it out and routed the slow group
again with a different method, written up in
[how the slow lines get routed](routing-method.md). in short:

- everything the router had put down since the ec pass came out, ground
  fan-out included. the older slow runs from before the power routing
  stayed but got straightened in place, and the hand fixes for the boxed-in
  ec pads stayed as they were.
- fan-out vias sit on a 0.5 mm grid and only where they have free lanes out
  on the inner layers. older escape vias next to boxed-in pins (FPC102,
  FPC103) get a short inner stub to the nearest free lane.
- long runs go on In2 east to west and In5 north to south on that grid, so
  they line up as buses. nets share lanes at a rising price for 20 rounds
  before the rest is settled one at a time.
- what the grid can't do goes to the fine router, with the outer layers
  four times the price away from the pads and bends and vias costed.
- the 48 worst nets by a cleanliness score got routed again with strict
  costs, in groups that don't overlap; a net only kept the new route if it
  connected as much and was clearly cleaner. two more fill passes then went
  after the connections that were still open.
- every run between two fixed points is replaced by the simplest 45 degree
  shape that clears the rules, or a version with fewer bends found in a
  narrow corridor around it. dead ends, unused fan-outs and 47 exact
  duplicate track pieces (some on GND, VSYS, CHG_SRN and CHG_BIAS_OR, left
  over from earlier work) are gone.
- via room next to special-attention pads is kept free the whole way: 231
  reserved escape spots (pads, stubs and via spots) are keep-out areas for
  every step, and a repair loop reserves and clears any pad that still lost
  its last spot. the first try skipped this and took the last via spot of
  64 special pads, including the usb pairs on FPC102, which is why it
  didn't go in.
- no new vias in outer-layer pours of other nets. one ground via split the
  small SEL_STAGE2 pour on the back in two; the check caught it.

| | committed board | now |
| --- | ---: | ---: |
| native unconnected items | 660 | 649 |
| open slow connections | 62 | 68 |
| slow nets fully connected | 187 of 248 | 182 of 248 |
| open ground connections | 48 | 31 |
| slow-net track | 17.9 m | 20.2 m |
| bends per 100 mm of track | 23.3 | 15.9 |
| track on the outer layers | 15% | 13% |
| track pieces under 0.3 mm | 1,120 | 512 |
| vias per 100 mm of track | 5.7 | 6.2 |
| special pads with no via spot left | | 5 |

the slow group ended up six connections short of the committed board, but
the board as a whole has eleven fewer open items, mostly ground, and every
special pad but five still has the via room it had on the committed board.
the extra vias per length mostly come from the lane grid changing layer
at its turns.

![slow-net copper on the committed board](../images/journal/2026-11-13-clean-reroute-before.png)

![slow-net copper after the clean reroute](../images/journal/2026-11-13-clean-reroute-after.png)

![around the ec, before](../images/journal/2026-11-13-clean-reroute-ec-before.png)

![around the ec, after](../images/journal/2026-11-13-clean-reroute-ec-after.png)

![the maker mcu, before](../images/journal/2026-11-13-clean-reroute-maker-before.png)

![the maker mcu, after](../images/journal/2026-11-13-clean-reroute-maker-after.png)

## closing the gap (14 november)

the clean reroute left the slow group six connections behind the board from
before it. those connections had been made there, so a way through existed.

- for each of the 31 nets that was connected before and isn't now, the old
  route near the open pin shows where its escape has to go. the slow nets
  whose new copper sits within 4 mm of that pin, on that old path, were
  ripped (39 nets), the open pins routed first, then the ripped nets.
- that alone fixed 21 nets but broke more among the ripped ones, so
  two fill passes followed: one with the usual costs and one in the
  router's negotiated mode, where all open nets route together and push
  each other aside. after those, no net was worse than before the rip.
- a second round of this got stuck for hours on one net and was stopped.
- the five keyboard nets with the most vias were redone on their own; that
  took a few vias off, but the via-room repair afterwards put most of them
  back.
- 9 of the 10 pieces still clearly off 45 or 90 degrees got squared into a
  straight leg and a 45 degree leg.
- every new step keeps the escape reservations; the repair loop ran again
  at the end and only 3 special pads are short of via room now.

two cleanups came out of the checks:

- the module and connector shells (A1, J16, J53, J54, J420, J2073) and the
  switches (SW1, SW2, SW3, SW901) have several pads with the same name. the
  ground step couldn't tell which one was loose, so every repair round
  stacked another stub and via on the first one, up to eleven on a pad. 95
  of those stacked stubs are gone, one stays where it lands on the plane,
  and pads that share a name are now skipped and left for hand work.
- 153 short pieces of slow-net track lay entirely inside their own pad,
  left over from older stubs, and are gone. they didn't connect anything.

| | before the clean reroute | after it | now |
| --- | ---: | ---: | ---: |
| native unconnected items | 660 | 649 | 646 |
| open slow connections | 62 | 68 | 61 |
| slow nets fully connected | 187 of 248 | 182 | 187 |
| open ground connections | 48 | 31 | 31 |
| bends per 100 mm of track | 23.3 | 15.9 | 14.8 |
| track pieces under 0.3 mm | 1,120 | 512 | 417 |
| track on the outer layers | 15% | 13% | 13% |
| vias per 100 mm of track | 5.7 | 6.2 | 6.4 |
| pieces clearly off 45/90 degrees | 1 | 13 | 1 |
| special pads with no via spot left | | 5 | 3 |

![slow-net copper after closing the gap](../images/journal/2026-11-14-gap-closed-overview.png)

![around the ec](../images/journal/2026-11-14-gap-closed-ec.png)

![FPC103](../images/journal/2026-11-14-gap-closed-fpc103.png)

## surface routes and the rest (14 november, later)

the open ec pins are all slow digital lines: enables, interrupts, uart and
i2c. running those on the front is fine electrically, because the front
sits right over the In1 ground plane and the router still keeps away from
the high-speed tracks, the ec crystal and usb pins and the reserved
escapes. so the front is allowed now, without the extra cost away from the
pads.

- **local rip-up:** every slow copper piece within 2.5 mm of an open pin,
  and in the whole ec pin ring, came out (137 nets touched). everything it
  cut was routed again together in the router's negotiated mode, followed
  by two fill passes. that took the open slow connections from 61 to 51.
  a second round on the ten nets it broke on the way only reshuffled
  things (54), so i kept the first.
- **ground:** the ground escape can now also strap a pad to a nearby ground
  pad or an existing ground via, and picks shared-name pads by position.
  19 of the 24 loose ground pads are connected now, including the maker mcu
  decoupling caps under U901, which strap to the back of its exposed pad
  (that pad already has nine thermal vias).
- **vias:** the 32 two- and three-pin nets with the most vias were redone
  together. that saved 97 vias but left 3 more connections open, so i put
  back the fully connected version and only swapped in the two nets whose
  cleaner route fit (7 vias saved).
- **checks:** the via room repair ran again and a long dead-end branch on
  KB_ROW6 was pruned.
- **U906.8:** it doesn't need a via of its own. the maker usb pair runs
  from the Mu module on the front to U900 and U906, both on the back, so it
  changes layer once near U900, whose pins still have room.

| | committed before | now |
| --- | ---: | ---: |
| native unconnected items | 646 | 623 |
| open slow connections | 61 | 51 |
| slow nets fully connected | 187 of 248 | 197 |
| open ground connections | 31 | 13 |
| bends per 100 mm of track | 14.8 | 15.2 |
| track on the outer layers | 13% | 15% |
| track pieces under 0.3 mm | 417 | 492 |
| vias per 100 mm of track | 6.4 | 6.5 |

the extra connections cost a little tidiness: more track on the front
around the ec and a few more vias from the negotiated pass.

![slow-net copper with surface routes allowed](../images/journal/2026-11-14-surface-ec-overview.png)

![around the ec](../images/journal/2026-11-14-surface-ec-u4.png)

![the maker mcu](../images/journal/2026-11-14-surface-ec-maker.png)

## thinner tracks, ground islands and hops (15 november)

- **0.15 mm tracks:** the fills on the open slow lines now lay 0.15 mm
  track instead of 0.2 mm. these are slow digital lines carrying a few
  milliamps, so the width doesn't matter electrically, and 0.15 mm is a
  normal width for any fab. it lets a route squeeze between pins and
  vias where 0.2 mm didn't fit. the router's raster allowance went from
  0.03 mm to 0.01 mm as well; that only changes how close the search
  dares to go, every piece is still checked against the real board rules.
  that took the slow group from 51 open to 39. 280 pieces are 0.15 mm
  now, the rest stays 0.2 mm.
- **ground islands:** five groups of ground pads were tied to each other
  by copper but never reached the planes: U773's exposed pad and pins,
  the A1 ground pins, the caps on U901 pin 47, C905/C935 and C778/R776.
  each one now gets a single via or a strap to a pad that is on the
  planes. ground went from 13 open to 8.
- **hops:** a net routed early along a layer makes every later net that
  crosses it on that layer drop through two vias to get past it. a new
  cleanup pass finds those hops, takes them out so the crossing nets run
  straight, and sends the one blocking track round on another layer
  instead. it's kept only where it saves vias with no net worse. this
  board has few of them because the lanes keep In2 east-west and In5
  north-south, so it saved 7 vias here.
- **C914:** the strap for the C905/C935 island took the last via spot of
  C914.1 (the maker 1V1 cap), so the island is strapped from C935 instead
  and C914.1 has its room back.

![a hop group before and after](../images/journal/2026-11-15-hop-cleanup.png)

| | committed before | now |
| --- | ---: | ---: |
| native unconnected items | 623 | 606 |
| open slow connections | 51 | 39 |
| slow nets fully connected | 197 of 248 | 209 |
| open ground connections | 13 | 8 |
| vias on the board | 2,823 | 2,853 |
| bends per 100 mm of track | 15.2 | 15.4 |
| vias per 100 mm of slow track | 6.5 | 6.3 |
| track on the outer layers | 15% | 16% |
| track pieces under 0.3 mm | 492 | 526 |

tried and dropped, because they ended worse:
- redoing the whole ec area with every pin escaping first, at 0.15 mm:
  still 55 open after the fills.
- a planned fan-out per part for U901, U400, J2300, U911 and FPC103 at
  the new width: no gain on any of them.
- negotiated local rip-up rounds around the ec and the maker mcu: they
  either lost connections or left new DRC findings.
- freeing C908.2: it gets its ground via, but MAKER_SPI_MOSI can't get
  back past it.
- redoing the nets with the most vias: most of them would lose a
  connection.

![slow-net copper with 0.15 mm fills](../images/journal/2026-11-15-thin-tracks-overview.png)

![around the ec](../images/journal/2026-11-15-thin-tracks-u4.png)

![the maker mcu](../images/journal/2026-11-15-thin-tracks-maker.png)

## not routed

39 slow connections are still open:

| part | open | what's in the way |
| --- | ---: | --- |
| U4 (ec) | 16 | the slow copper of its own neighbours on the front and under the pin ring |
| U901 (maker mcu) | 7 | no free way out of the 0.4 mm pin ring on any layer |
| FPC102, FPC103 | 6 | long runs across the board that find no free path at the connector end |
| U400 (usb hub) | 3 | no free way out on any layer |
| J2300 | 3 | no free way out on any layer |
| others | 4 | maker header lines and one resistor end in tight spots |

the ec is not held up by the usb pairs under it. with only the usb pairs
taken out of the area, 4 of its 19 stuck pins could escape; with only the
slow copper taken out, 16 could. so moving the pairs wouldn't help much.
the problem is the order: the ec's pins are boxed in by the routes of
other slow nets. a full redo of the area with all pins escaping first was
tried twice and connected less, so the last ec pins are left for hand
routing.

ground has 8 open connections left: C2283 (blocked by the U773 escape
reservation), C444 and C445 (right next to the H24 mounting hole keepout),
C908 (see above), U60 (between its own usb pair), the mounting hole H2
and the microphone MK430, which stay for hand work.

## checks

| check | result |
| --- | --- |
| physical DRC | zero new findings against the board before the clean reroute, refilled the same way |
| exact clearance | no problems: all copper that wasn't on the committed board (341 track pieces, 45 vias) checked against everything, arcs checked as arcs, track to hole included |
| native unconnected items | 623 on the committed board, 606 now; no net has fewer connections than before |
| special-pad via room | the same 7 special pads as before have no via spot within 1.5 mm, all accounted for under weak spots |
| schematic parity | passes: 870 parts, 3,372 physical pads, no net, value or footprint changes |
| via nets | every new via keeps its net after refill |
| placement exports | regenerated; only the board hash changed, all 1,378 component rows still match |
| case | no parts moved, so nothing new to screen |

## weak spots

- seven special pads have no via spot within 1.5 mm:
  - C29.2, C909.2 and U4.27 are ground pads that are already connected.
  - C908.2 is one of the boxed-in ground pads.
  - U901.22 (MAKER_XOUT) goes to R906 on the front.
  - U906.8 (MAKER_USB_DN) changes layer near U900 instead.
  - C905.1 (MAKER_3V3_CORE) sits on the back right under U901.11, so
    it's meant to get a via straight up through its pad when the maker
    core supply is routed.
- the busiest multi-pin nets have a lot of vias (I2C_SCL 36, I2C_SDA 31,
  NRST_NET 28, INTERNAL_USB_VBUS_VALID 26).
- there is more track on the front around the ec than before.
- the slow routing now mixes 0.2 mm and 0.15 mm track.
- nothing reserves room for the power feeds and the other rails yet;
  they come with the In4 power map.
