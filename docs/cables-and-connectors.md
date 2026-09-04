# cables and connectors

updated 4 september 2026. the signal maps live in
[`gen/fpc_contract.py`](../gen/fpc_contract.py). this page covers how those
maps relate to the physical cables and what remains to be settled.

## board-to-board cables

| Cable | Ends | Connector family | Signals |
| --- | --- | --- | --- |
| FPC-1 | Left FPC101 to center FPC102 | Hirose FH41, 68 pins, 0.5 mm pitch | Left power, USB, and control boundary |
| FPC-2 | Right FPC104 to center FPC103 | Hirose FH41, 68 pins, 0.5 mm pitch | Right power, USB, HDMI, Ethernet PCIe/clock, and controls |
| FPC-3 | BMS FPC106 to center FPC105 | Hirose FH12-30S, 30 pins, 0.5 mm pitch | Protected pack positive/return, fault, retry, MCU_3V3 |

the FH41 footprint has 68 numbered signal pads, two MP hold-down pads, and
13 SH pads. MP/SH are on system ground. the BMS FH12 hold-down pads use
`FG_VSS`, the BMS's protected return.

FPC-3 allocates 12 numbered contacts to `PACK_POS_FUSED`, 15 to `FG_VSS`,
and one each to `PACK_FAULT_N`, `PACK_RETRY_PULSE`, and `MCU_3V3`.
cell taps and raw pack negative do not cross this cable.

## mapping and installed orientation

the code defines each daughterboard as side A. center maps are reversed:
side-A pin N corresponds to center pin 69-N for FPC-1/2 and 31-N for FPC-3.
the intended physical arrangement was a straight Type-A FFC, with contacts
on the same side at both ends, between oppositely mounted connectors.

the cable's conductor mapping, connector contact side, and installed board
orientation must all agree with that arrangement. "straight" by itself is
not a complete assembly instruction. continuity-test the cable alone, then
verify the expected board nets with it seated in both connectors.

the project's footprint convention places the connector mouth on local +Y,
opposite the solder-pin row. the earlier drawing review and the current code
use this convention. confirm the exact ordered connector against its drawing.

## positions read from the boards

KiCad coordinates in mm and rotations in degrees, checked 4 september.

| Ref | Board | X | Y | Rotation |
| --- | --- | ---: | ---: | ---: |
| FPC101 | Left | 65.6 | 92.5 | 90 |
| FPC102 | Center | 73.5 | 92.5 | 270 |
| FPC103 | Center | 294.6 | 92.5 | 90 |
| FPC104 | Right | 303.6 | 92.5 | 270 |
| FPC105 | Center | 123.5 | 6.5 | 180 |
| FPC106 | BMS | 136.901 | 68.552 | 180 |

the BMS was moved and reshaped after the original cable plan. its coordinates
are not its installed chassis coordinates. FPC105 and FPC106 now both read
180 degrees in their files, so the old flat, opposite-facing installation
cannot simply be assumed. decide the installed BMS orientation and verify
the conductor mapping before buying the cable.

## cable construction and ordering

Hirose lists a 0.3 mm mating cable thickness for FH12-30S-0.5SH(55), and 0.3 mm for the
FH41-68S-0.5SH(28) product. include the specified contact-end thickness and
tolerance in the actual cable drawing, including any stiffener.

sources: [FH12-30S-0.5SH(55)](https://www.hirose.com/en/product/p/CL0586-0525-1-55),
[FH41-68S-0.5SH(28)](https://www.hirose.com/en/product/p/CL0580-2202-5-28).

the project currently names FH41-68S-0.5SH(05), while earlier purchasing
notes also mention (28). resolve the orderable suffix against the footprint,
contact construction, drawing, and supplier listing. the connector's height
is not the cable thickness. check the FH41 footprint and current 3D model
against the exact vendor drawing as part of that work.

measure mouth-to-mouth routes, insertion lengths, bends, service loops, and
installed board offsets before selecting cable lengths.

for the shielded I/O cables, verify the shield-contact construction and its
connection to the SH row. also obtain suitable current and signal-integrity
data for the actual cable. parallel contact counts alone do not establish
the rating of a complete heated cable/connector assembly.

## other internal cables

| Connection | What is fixed | What remains |
| --- | --- | --- |
| Keyboard | 30-pin interface; center J310 is at (216.5, 12.5), rotation 270 | Installed route, length, seating, and continuity against both board revisions |
| Radio | Removable 30-pin interface; center J2300 is at (188, 4), rotation 0 | Radio chassis location, supports, orientation, and cable route |
| Trackpad | J58: 1 GND, 2 D-, 3 D+, 4 VBUS; USB-C plug at trackpad | Exact cable, cut-end identification, bend path, clamp, and pull test |
| Internal display | Mu onboard eDP connection | Exact panel connector, all 40 conductors, rail limits, and hinge route |

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
