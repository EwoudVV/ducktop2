# routing the main-board power

20 october 2026: steps 1 and 2 are routed. the [charger and Mu supply routing](charger-and-mu-routing.md)
covers both power stages, both controllers, the In4 VSYS island and the
part moves they needed. steps 3 to 6 are next.

16 october 2026. this is the routing order for the saved 100 W circuit.
the main boards are still eight layers. the BMS is a separate four-layer
board. the [current counts](power-revision.md) come from refilled copies;
the existing right CC control paths were repaired in the latest pass;
all other tracks and vias were preserved.

the [main-board power placement pass](mainboard-power-placement.md)
includes both PD controllers, the left USB source circuit, standby inputs
and the remaining rail capacitors. it also corrects the three TPD1S514
land patterns. the earlier [converter changes](converter-placement.md)
bring the charger input shunt closer and open the Mu switching corridor.
the [input and standby changes](source-standby-placement.md) cover the
selector bypasses, charge-pump capacitors and battery-gauge filter.

## before routing

settle the electrical interfaces and check the component, wire-exit and
cooler envelopes before locking placement. detailed case brackets can follow
that stable layout. keep checking the center cutout, 1.5 mm seams and
connector access as the boards change. a connector's body height alone is
not its installed height with wires and a release tool.

F190 and F195 now use low-profile SMD backup fuses. their land pattern is
saved, but the AUX routes are still open. size the copper and transitions
for the fault-clearing requirements as well as normal load. a 5 A fuse
does not provide a sharp 5 A current ceiling. [AUX limits and fault tests](aux-input.md)

confirm the finished copper thickness, hole plating and eight-layer stackup
with the board manufacturer before sizing the power pours and via banks.
the netclass width is a starting setting, not a current rating. calculate
loss through the narrowest neck, pad entry and layer change at the full
branch current, then check the filled result.

In1, In3 and In6 are ground planes. keep the existing PCIe and clock routes
and their reference planes intact. the controlled-impedance layers are
F.Cu, In2.Cu and B.Cu. avoid running sensitive feedback or sense traces
under either converter's switching nodes or inductor.

## routing order

| order | circuit | connections to settle first |
| --- | --- | --- |
| 1 | U2 charger | the two front-side FET loops, L1 and local input/output capacitors |
| 2 | U750 Mu supply | Q2610/Q2611, L750, input/output capacitors and current shunts |
| 3 | input selection and battery path | U15/U16, RS2600, Q25, RS2601 and the protected BMS pair |
| 4 | always-on supply | raw-source and VSYS feeds, U718 voltage protection, U2660 current limiter and U5 buck |
| 5 | remaining rails | U6 SYS_5V, U7 SYS_3V3, U773 endpoint rail and left U1703 USB5 |
| 6 | control and measurements | enables, power-good, fault, I2C and telemetry; keep their local filters beside the IC pins |

reserve the quiet sense and feedback corridors before filling the large
power areas. finish each local converter and refill/check it before joining
the longer distribution routes. the rows below describe the connections
that ordinary net connectivity cannot establish on its own.

## ISL9241 charger

U2 is on the back at board coordinates 207.75, 162.5 mm. Q2600 through
Q2603 and L1 are on the front. Renesas explicitly allows the controller
opposite the FETs; keep the power FETs, inductor and local power capacitors
on the same side.

- input loop: C701 through C705, Q2600 drain and Q2601 source/ground.
  use the closest capacitors for the switching return. C10 is the local
  1 uF bypass, now positioned closer to the low-side return.
- output loop: C706 through C710, Q2603 drain and Q2602 source/ground.
  C11 is the local 1 uF bypass. C706 is the nearest 10 uF ceramic;
  C2608/C2609 provide bulk storage.
- SW1 joins Q2600 source, Q2601 drain and L1 pad 1. SW2 joins Q2603 source,
  Q2602 drain and L1 pad 2. keep these areas compact while retaining enough
  copper for current and heat.
- route each high-side gate drive beside its PHASE return. take the PHASE
  connection from that FET's source pads. place the layer transitions beside
  the gate links and keep the driver loop short. C7/C8 are the bootstrap
  capacitors, not ground bypasses.
- RS2600 is 20 milliohms. take separate sense connections from its pads to
  CSIP through R2607 and to CSIN. C2603 belongs at the controller end.
  RS2600 is now at 219.8, 156.5 mm with its CHG_INPUT pad beside Q2600.
  take the Kelvin pair from the shunt itself, not from the nearby FET feed.
- RS2601 is 10 milliohms. CSOP connects to its VSYS end and CSON to CHG_SRN.
  use separate Kelvin pickups and keep C2604 local to U2. neither sense trace
  should carry the load current between Q25 and VSYS.
- Q25's source return R2600 is now 1 Mohm. retain that value and provide
  drain heat-spreading copper. the [battery-path check](battery-path.md)
  gives its gate-drive, thermal and complete-loop voltage-drop requirements.
- connect U2's exposed ground pad with at least five thermal vias, as required
  by the layout guidance. give the compensation, PROG and sense filters a
  quiet local ground return.

the corrected battery-shunt screen uses the full 8 A discharge target.
its upper resistance corner gives 0.7236 W against a 1.4 W derated limit
at 100 °C. this is a component calculation; the installed temperature and
copper voltage drop still need measurement.

[Renesas ISL9241, section 9](https://www.renesas.com/en/document/dst/isl9241-datasheet)
contains the gate-loop and Kelvin pickup drawings.

## TPS552882 Mu supply

U750 is at 151.625, 117.5 mm on the front. Q2610/Q2611 form the external
buck half-bridge; the boost half-bridge is inside U750. L750 connects SW1
to SW2. the design screen is 5.5 A output with VSYS at least 10 V, including
the fan allocation. the firmware cap for the module and display is 60 W.

keep the input capacitor return beside Q2611's ground pads. keep the
boost output loop between U750's output/PGND pads and the closest output
capacitors. do not make those loops travel through a remote ground via or
the bulk capacitors first. keep both switching-node areas small.

C765/C766 are now vertical beside the north edge of U750, at 149.8/153.8,
113.65 mm. the 3.05 mm copper-pad gap between them leaves room for the
SW2 connection. this is placement space, not a specified track width or
current rating. keep each bootstrap connection and switch return together;
the returns to the IC are slightly longer than in the previous placement.

RS750 and RS2670 are parallel 16 milliohm resistors. use broad, balanced
connections to their common input and output ends. take the ISP/ISN sense
pair from those common ends, close together and clear of switching copper.
the output capacitors on MU12_PRE_SENSE remain before the shunt; C763 is
the load-side bypass.

return the AGND network at the VCC capacitor ground, following TI's layout.
keep C764/C2670 close, and route FB, COMP, ILIM and FSW through that quiet
area. add the PGND thermal vias and separate VOUT copper called out in the
datasheet. the 15k/10n/100p compensation still needs loop-response testing
with the assembled board and its actual output capacitance.

[TI TPS552882, section 10](https://www.ti.com/lit/ds/symlink/tps552882.pdf)
shows the input/output loops, sense pair and ground connection.

## inputs, standby and returns

U15/U16 select the external input before the charger. preserve the separate
raw feeds that can start the always-on supply before the EC enables a main
input. standby's battery feed comes from VSYS so it passes through the
charger battery shunt.

C2686 bypasses U16 V1, C2687 bypasses its VS1 common-source node and C2688
bypasses U15 VOUT. all three are on the back. put the transitions close to
their front-side controller pins and keep their ground returns local.
C747 belongs to U15 VS2; its old stage-two label was wrong.

C2620/C2621/C2650 now sit directly above U2620/U2621/U2650. route each
VCAP connection with its ANODE return, keeping the charge-pump loop close
to the controller. do not return these capacitors to ground. the input
and output sense connections must pick up at the corresponding FET pads.

R183 now lines up with C181 beside U10. keep both gauge sense paths away
from the switching nodes and take dedicated pickups from RS1. the ground
side of that shunt is a measurement connection as well as a load return.

U2660 uses RS2660/R2662 in parallel and Q2660 for standby current limiting.
use balanced force connections to the resistor pair, dedicated sense
pickups, a short gate path and local timer/bias returns. keep its manual
fault-reset behavior and the upstream U718 voltage protection intact.
[LTC4231 layout guidance](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4231.pdf)
shows the Kelvin connections.

center J2071 pad 2 is PACK_POS_FUSED and pad 1 is FG_VSS. those connect
to BMS J2072 pads 1 and 2 respectively. FG_VSS reaches system GND through
the center fuel-gauge shunt RS1. no extra ground pour, support, shield or
seam braid may bypass that shunt or the BMS return domains.

the short WAGO looms use Alpha 6715, 18 AWG. the direct XT30 USB5 loom
uses Alpha 6716, 16 AWG. join the WAGO rails by net name, since the numbered
three-pole groups reverse at the center. use both ground braids at each
seam and retain the separate USB5 enable, monitoring and fault circuits.
[loom and return limits](io-power-qualification.md)

## system and endpoint rails

U7's C791 input bypass now sits across the VIN and PGND side of the IC,
with C46/C790 aligned behind it. connect the capacitor ground ends back to
PGND pin 9 with a broad local path and nearby ground vias. keep the
feedback divider's quiet return to AGND separate from that switching
current until the local ground connection. keep L5's SW connection short
and wide, and give the output capacitors a direct ground return.

U6, U773 and left U1703 use LM706A0. keep their capacitor returns local to
the PGND pins and connect the exposed pads to the ground planes with
thermal vias. take separate, paired sense connections from the parallel
output shunts. route the bootstrap return to SW4; do not join that pin to
the high-current SW1/SW2/SW3 path on the PCB. keep feedback and compensation
connections away from the switching nodes.

left C1713 is now on the front beside U1703's input pins. C1711/C1712 are
aligned behind it, and the optional C1866 footprint stays DNP. the new
placement permits a same-side input loop; the tracks and ground copper
still need designing. [positions and close-ups](converter-placement.md)

[TPS56637 layout](https://www.ti.com/lit/ds/symlink/tps56637.pdf) and
[LM706x0 layout](https://www.ti.com/lit/ds/symlink/lm70660.pdf) show the
local power returns, sense pickups and thermal connections.

## after routing

refill all zones and check schematic parity, native uncapped connectivity,
clearances, dangling copper and silkscreen. inspect the filled power paths,
sense pickups and return currents separately. resolve the footprint warning
records against the final placed footprints. then export fresh assembly and
fabrication files from that same checked board.

first power-up starts with the always-on supply and inhibited high-power
loads. measure input current, each rail, charge/discharge limits, startup,
source transfers and temperature before enabling the operating profiles.
matching schematics, calculations and software tests do not replace those
measurements.
