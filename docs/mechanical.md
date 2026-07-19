# Mechanical Plan

Ducktop2 is being packaged as a thin 16-inch laptop. The base and lid should
follow the panel outline without a gaming-laptop rear extension or wider side
walls.

## Confirmed Plan-View Measurements

| Part | Size |
| --- | --- |
| AUO B160QAN03.K panel | 352 x 227 mm |
| Provisional lid/base envelope | 358 x 248 mm |
| Main motherboard | 358 x 185 mm |
| Battery cells | 100 x 60 mm each, three cells |
| Keyboard PCB | 273.5 x 80.0 x 0.8 mm |
| JOMAA trackpad | 140 x 105 mm |
| Front speakers | 38 x 18 mm each |
| Mu cold plate envelope | 74 x 64 mm |
| Blower placeholder | 45 x 45 mm |
| Fin stack | 50 x 50 x 14 mm |

The current motherboard has a notch for the fin stack. The front battery band
is outside the motherboard outline, which leaves room for the cells and
trackpad without making the six-layer board cover the full base.

## Keyboard and Palm Rest

The Cherry MX ULP keyboard is a separate two-layer PCB. Its 30-pin FFC reaches
J310 on the motherboard without another controller board or internal USB cable.
The trackpad is a complete USB device and needs room for its USB-C plug, cable
bend, mounting lip, and click travel.

Keyboard, motherboard, and cooling parts may overlap in XY only when the final
Z stack gives each one a supported and insulated plane. Batteries and trackpad
cannot occupy the same volume.

## Cooling

The planned cooler is conventional laptop hardware:

- copper cold plate on the LattePanda Mu
- flat heatpipe to a side fin stack
- 12 V four-wire Delta blower with tach and PWM control
- side exhaust through the motherboard notch

Peltier cooling is not part of the design. The final stack still needs the exact
TIM, cold-plate clamp, heatpipe bend, duct, inlet area, and blower mounting.

## Retention

The LattePanda Mu plugs into a 260-pin SO-DIMM-style connector, but the socket
clips are not the complete structural support. Two grounded M2 soldered
standoffs carry the module at the specified height. The NVMe and E-key cards
also have dedicated M2 standoffs, and eight isolated M2.5 holes support the
long motherboard in the chassis.

The detailed hardware stack is recorded in
[`mechanical/RETENTION_AND_MOUNTING_RELEASE.md`](../mechanical/RETENTION_AND_MOUNTING_RELEASE.md).

## Measurements Still Needed

- panel thickness, connector datum, bezel offsets, hinge sweep, and cable bend
- cell thickness, tab length and polarity, swelling allowance, and final harness
- trackpad thickness, USB-C location, cable exit, mounting points, and click travel
- speaker depth, impedance, mounting points, outlet direction, and back volume
- keyboard cap/plate/support stack and underside clearances
- exact side-connector cutouts and mated-cable clearance
- full cooler and duct geometry
- aluminum wall, boss, fastener, and service-clearance dimensions

The interactive floorplan remains available in
[`mechanical_layout_planner.html`](../mechanical_layout_planner.html). Its JSON
is useful for planning, but physical measurements control the final enclosure.
