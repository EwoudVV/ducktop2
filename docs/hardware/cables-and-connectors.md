# cables and connectors

updated 10 september 2026. the I/O signal cables, power looms, and BMS
control cable are separate connections. the old 68-pin I/O cables and
30-pin BMS power cable are no longer part of this design.

## signal cables between the main boards

| cable | board connectors | cable part | contents |
| --- | --- | --- | --- |
| left to center | FPC101/FPC102, Molex 5039084120 | Molex 150230241, 41 contacts | USB pairs, PD control, and ground guards |
| right to center | FPC104/FPC103, Molex 5039085120 | Molex 150230251, 51 contacts | HDMI, Ethernet PCIe/clock, USB pairs, control, and ground guards |

both cable parts are 51 +/-2 mm long. use the specified shielded 100 ohm
assemblies and check their exact part numbers and contact construction.
positive supply rails use the separate power wiring.

both ends have contacts on the same side. the connectors face each other,
so numbered contacts reverse between boards: left pin N reaches center
pin 42-N, and right pin N reaches center pin 52-N. the complete signal map
is in [signal_interconnect_contract.py](../../gen/signal_interconnect_contract.py),
with the center reversal in [fpc_contract.py](../../gen/fpc_contract.py).
check the actual cable alone, then check it again seated in both boards.

numbered ground contacts connect to their local board ground. each
connector's shell connects through two parallel 0.33 ohm resistors. two
separate Alpha Wire 1230 ground braids also cross each seam, using the four
pairs of J2440 through J2447 solder lands. each braid starts from a 20 mm
cut length and must measure at most 1 milliohm as a complete connection,
including its joints and board connection. fit and strain-relieve both
braids before attaching the signal cable.

the resistance and temperature bounds for the shared returns still need
assembly tests. the signal cable ground conductors can carry DC return
current alongside the power wiring and braids. see
[I/O power qualification](io-power-qualification.md) for those limits.

keep the exact cable and connector transitions in the signal-integrity
review. the cable's nominal impedance alone does not qualify the complete
USB, HDMI, or PCIe channel. final checks include the routed boards, vias,
switches, protection parts, and external connector/cable allowance.

## power between the main boards

| loom | board connectors | cable housing | wire |
| --- | --- | --- | --- |
| center to left | J2430/J2431, Molex 43045-1212 | 43025-1200 with 43030-0038 contacts | 12 separate 18 AWG conductors, 90..100 mm |
| center to right | J2432/J2433, Molex 43045-1012 | 43025-1000 with 43030-0038 contacts | 10 separate 18 AWG conductors, 90..100 mm |
| USB5, left to right | J2434/J2435, AMASS XT30PW-F30.G.Y | XT30U-M.G.Y | two 18 AWG conductors, 400..420 mm |

the Micro-Fit looms use Alpha 3253 wire and connect pin N to pin N. their
pin maps and exact supply names are in
[usb_power_contract.py](../../gen/usb_power_contract.py). the different
contact counts distinguish the left and right looms.

the direct USB5 loom uses Alpha 5857 wire. pin 1 is GND and pin 2 is
USB_PORT_5V at both ends. insulate the solder terminations and add strain
relief. the board connector's retention lands are isolated.

the Micro-Fit connector body is 17.64 mm high when mated. the current
individual-wire bend model reaches roughly 55 mm above the PCB. that
still excludes a proven arrangement for the whole wire bundle, its clamp,
and the cover. do not use connector body height as the case-height limit.
current lengths, bend radii, voltage-drop limits, and remaining fit work are
recorded in [I/O power qualification](io-power-qualification.md).

## BMS wiring

| connection | ends | construction |
| --- | --- | --- |
| protected pack power | center J2071 to BMS J2072 | Molex 43650-0224 headers, 43645-0200 housings, 43030-0038 contacts, 18 AWG; 75 mm wire budget |
| isolated control | center J2073 to BMS J2074 | JST SM05B-SRSS-TB headers, SHR-05V-S housings, SSH-003T-P0.2-H contacts; five wires |
| cell temperature probes | BMS J2200 to three insulated probes | JST SM06B-SRSS-TB header; three separate wire pairs to SEMITEC 104JT-025 probes |

the power cable is pin 1 to pin 1 for PACK_POS_FUSED, and pin 2 to pin 2
for FG_VSS. FG_VSS reaches system ground through the center's gauge shunt.
the connector mounting pads are isolated.

the control cable is also straight-numbered:

| pin | connection |
| ---: | --- |
| 1 | PACK_FAULT_N |
| 2 | PACK_RETRY_PULSE |
| 3 | MCU_3V3 |
| 4 | PACK_CHG_TEMP_OK |
| 5 | center GND to the BMS CTRL_GND island |

CTRL_GND is isolated from FG_VSS and raw pack negative on the BMS. do not
add a ground bridge between those domains. the temperature probes and
J2200 hold-downs are raw-pack referenced; they do not get a system-ground
wire. J2200 pairs 1/2, 3/4, and 5/6 serve cells 1, 2, and 3.

the cell power and tap harness stays on the BMS's six-contact Mega-Fit J2.
cell taps do not cross to the center board. all BMS cable routes need to
include the actual plugs, wire exits, bend clearance, and insulating supports.

## other internal cables

| Connection | What is fixed | What remains |
| --- | --- | --- |
| Keyboard | 30-pin interface; center J310 is at (145, 49), rotation 270 | Installed route, length, seating, and continuity against both board revisions |
| Radio | Removable 30-pin interface; center J2300 is at (155, 67.75), rotation 0 | Radio chassis location, supports, orientation, and cable route |
| OLEDs | J41/J45 use four-wire cables: 1 GND, 2 3.3 V, 3 SCL, 4 SDA | Module mounts, cable lengths, and rise-time check with the installed harness |
| Trackpad | J58: 1 GND, 2 D-, 3 D+, 4 VBUS; USB-C plug at trackpad | Exact cable, cut-end identification, bend path, clamp, and pull test |
| Internal display | Mu onboard eDP connection | Exact panel connector, all 40 conductors, rail limits, and hinge route |

the two OLEDs mount separately in the case. J41/J45 are JST GH
`SM04B-GHS-TB` connectors, with `GHR-04V-S` cable housings and
`SSHL-002T-P0.2` contacts. use the OLED's printed signal labels when wiring
the far end; connector views can reverse the apparent pin order. keep each
harness short and check continuity before plugging it in. the display
modules need their own mounts and wire strain relief.
[JST GH drawing](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf).

## keyboard cable map

the generator maps center J310 pin N to keyboard J320 pin 31-N for the
specified top-mounted, bottom-contact connectors and same-side-contact
Type-A cable. verify all 30 conductors in the installed assembly.

| J310 | J320 | Function |
| ---: | ---: | --- |
| 1 | 30 | GND |
| 2 | 29 | Protected keyboard 5 V option |
| 27 | 4 | I2C SDA |
| 28 | 3 | I2C SCL |
| 29 | 2 | Keyboard 3.3 V option |
| 30 | 1 | GND |

the matrix contacts follow the same reversal. the sources are
`gen/generate_keyboard_interface_sheet.py` and
`gen/generate_keyboard_daughterboard_sheet.py`.

for rev A, the 3.3 V option through DNP R387 stays unpopulated, and U310's
5 V option stays off until the EC asserts `KB_RGB_PWR_EN`. this is not a
released RGB assembly. verify no unintended power reaches those contacts
before testing the passive matrix. a different cable/orientation or powered
keyboard variant needs its own mapping and current-budget review.

## before a cable is released

record the exact connector and cable parts/drawings, mating contact sides,
pin-1 datums, complete conductor map, contact thickness, length, bend limits,
current limits, and any shield termination. prove the map by continuity on
the real seated assembly before power. keep that result with the board revision.
