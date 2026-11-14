# how the slow lines get routed

13 november 2026. this is the method the slow digital lines on the center
board are routed with now, and the rules any later routing pass should
keep to. the old way grew every route on a fine grid one net at a time,
which got most things connected but left staircases, long runs on the
outer layers and a lot of layer hopping. the new way splits the job in
steps, puts the long runs on a fixed lane grid, and checks the look of
every net afterwards.

## the order

1. **ground first.** every loose ground pad gets a short stub and a via
   into the plane next to its side (In1 for the front, In6 for the back).
   if there is no spot within reach of a straight stub, a small search on
   a 0.1 mm grid finds a short stub with as few bends as it can.
2. **fan-outs.** every slow pin that needs to leave its layer gets a stub
   and a via. the via sits on a 0.5 mm grid (the lane grid, below) and must
   have at least two free lanes out on the inner layers, or the long runs
   can never leave it. the stub is straight out of the pad, with at most
   one 45 degree bend. pins on the busiest parts go first. where that
   fails, the same small 0.1 mm search looks for a stub to any free grid
   spot within 6 mm, with bends priced so it stays tidy.
3. **older escape vias.** some pins already have a stub and via from
   earlier work, often because the pad itself is boxed in by its
   neighbours. those vias get a short stub on In2 or In5 to the nearest
   free lane, and the lanes around that stub are kept for its net.
4. **the lane grid.** long runs go on In2 (east to west) and In5 (north
   to south), on a 0.5 mm grid, so parallel routes sit at an even pitch
   and read as buses. a turn costs extra (a 45 degree bend like 1 mm of
   track, a 90 degree one like 2 mm), a via like 4 mm, and running the
   wrong way on a layer costs double. nets first route while sharing
   lanes at a price, and the lanes that stay contested get dearer each
   round (20 rounds), so they settle instead of the first net taking the
   best path. whatever is still fighting at the end is routed again one
   net at a time with the rest fixed.
5. **the rest.** connections the grid can't make go to the fine router.
   it may only use the outer layers near the net's own pads (beyond 3 mm
   they cost four times as much), bends cost 1.2 mm and 3 mm of track, a
   via 4 mm.
6. **gap fill.** the connections still open get another pass with a
   bigger search budget, then one in the router's negotiated mode, where
   all open nets route together and push each other out of the way.
7. **quality gate.** every net gets a score: vias per connection, outer
   layer track far from its pads, bends per 10 mm, and length against the
   shortest tree between its pads. the worst ones are ripped in groups
   that don't overlap on the board and routed again with strict costs
   (outer layers ten times the price, a via 8 mm). a net keeps the new
   route only when it connects at least as much and is clearly cleaner.
8. **cleanup.** fan-outs that nothing ended up using go. dead ends go,
   checked against KiCad's own dangling report, and so do exact duplicate
   pieces. then every run of track between two fixed points (pads, vias,
   junctions) is replaced by the simplest 45 degree shape that fits: a
   straight line, one bend, or straight, diagonal, straight. if none fits,
   a search inside a narrow corridor around the old run looks for a
   version with fewer bends. vias and junctions never move in this step.
9. **via room check.** every special-attention pad is compared with the
   committed board. a pad that lost its last via spot within 1.5 mm gets
   its best old spot reserved, only the new pieces sitting in it are cut,
   and the cut nets are routed again around it. this repeats until it
   stops finding anything.

## rules every step keeps

- the board rules: 0.15 mm track clearance, 0.18 mm via to track, 0.2 mm
  via to via, 0.3 mm to holes, 0.5 mm to the edge, arcs checked as arcs.
- the escape reservations: special-attention pads that still need routing
  (pairs, power pins, crystals, sense lines) keep a via spot within 1.5 mm
  and a clear stub to it. those spots are keep-out areas for every step.
- no new vias inside an outer-layer pour of another net. one ground via
  once split the small SEL_STAGE2 pour on the back in two.
- escape rings: near the pins of a fine-pitch part only nets with a pin on
  that part may route or put vias.
- no vias under a chip with an exposed pad, except ground vias inside the
  exposed ground pad.
- every new piece of copper is checked against the board rules with exact
  geometry before it stays, and the finished board is checked with
  KiCad's DRC against the board before the pass, refilled the same way.
