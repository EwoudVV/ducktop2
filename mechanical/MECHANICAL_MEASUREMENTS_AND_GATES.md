# Ducktop2 Mechanical Measurements and Release Gates

This file records the mechanical facts behind the current rev-C battery-band
floorplan and the interactive layout planner.
The planner coordinates are provisional packaging guidance, not released chassis
dimensions or PCB `Edge.Cuts`.

## Confirmed Measurements

- Replacement B160QAN03.K panel outer envelope: **352 x 227 mm** (user measured).
- Three pouch cells: **100 x 60 mm each** (user measured; thickness and tabs not
  yet measured).
- Keyboard rev A PCB: **273.5 x 80.0 x 0.8 mm**.
- JOMAA USB trackpad outer envelope: **140 mm wide x 105 mm front-to-back**
  (user measured as 105 x 140 mm; thickness, USB-C datum, click travel, and
  mounting details are not yet measured).
- Front speakers: **38 x 18 mm each** in plan view.
- Intehill controller PCB: removed from the production architecture. The panel
  connects directly to the LattePanda Mu module's onboard 40-pin eDP connector.

## Provisional Envelope

- Lid and base outer plan envelope: **358 x 248 mm**.
- Panel location in lid: `(3, 10.5)`, leaving 3 mm nominal side margin and
  10.5 mm nominal front/rear margin before wall thickness, tolerance, hinge,
  and cable allowances.
- The left and right battery cells are rotated 90 degrees and the center cell is
  horizontal in the previous draft. That arrangement was based on the obsolete
  135 x 74 mm trackpad placeholder. The measured 140 x 105 mm trackpad overlaps
  the center cell when centered at the front edge, so battery and trackpad
  placement must now be redone before the envelope can be frozen.
- The main PCB outline remains intentionally unchanged until these dimensions
  are checked against physical parts and the routed board is ready for a
  controlled ECO.

## Allowed XY Overlap Only With Separate Z Planes

- Keyboard above the Mu/coldplate, heatpipe, fin/blower, and NVMe.
- Coldplate above the Mu and heatpipe contacting the coldplate/fin stack.
- Trackpad cable above a battery or PCB web only in an insulated retained chase
  with a verified bend radius.

Battery/trackpad overlap, heatpipe/blower-body overlap, and connector noses
outside the chassis envelope are not allowed.

## Measurements Required Before Mechanical Freeze

1. Panel maximum thickness, rear protrusions, corner radii, active-area offsets,
   40-pin connector datum, cable exit direction, and safe cable bend radius.
2. Hinge axis and bracket envelopes, full opening sweep, closed clearance, and
   the direct-eDP cable path through every lid angle.
3. Finished cell thickness, tab protrusions/polarity, swelling allowance,
   padding, cell thermal-cutoff boards, pack wiring, fuse access, and wire bend
   radii.
4. Full keyboard keycap/switch/plate stack, underside protrusions, support rails,
   and the J320-to-J310 FFC datum and bend envelope.
5. Trackpad thickness, click travel, USB-C position, plug body, cable exit, and
   mounts.
6. Speaker thickness, wire exit, mounting points, outlet direction, and required
   acoustic back volume.
7. Mu/module height and service clearance; coldplate/TIM/clamp stack; exact
   blower model, inlet/outlet/feet; heatpipe end geometry; fin height; and NVMe
   socket/standoff/removal sweep.
8. Every side/rear connector body, shell overhang, panel cutout, face setback,
   latch/finger clearance, and mated-cable sweep.
9. JXD1-1022NL physical sample dimensions, PCB-thickness compatibility, THR
   holes/slots, panel datum, and whether the assembly vendor supports the
   recessed through-hole jack.
10. Main PCB mounting holes, bosses, structural web widths, cutout clearances,
    component-height map, and copper-to-cutout rules.

## Known Part Envelopes To Verify Physically

- LattePanda Mu carrier courtyard placeholder: **77.5 x 65.5 mm**.
- JXD1-1022NL Ethernet jack body: **26.06 x 17.58 x 11.30 mm**, approximately
  9.39 mm above and 2.00 mm below the PCB. Suggested panel opening is
  17.98 x 9.69 mm. Confirm all datums against the physical part and vendor
  drawing before cutting metal.
- The mainboard microphone is a bottom-port IM68A130. It requires a sealed
  acoustic opening and must be kept away from blower turbulence, radio PAs,
  switching inductors, and the class-D speaker outputs.
