# cables and connectors

updated 28 september 2026. the I/O signal cables, power looms, and BMS
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

the saved main-board connector positions now leave room for the proposed
wire paths. see [harness fit](power-harness-fit.md) for coordinates, bends
and service space. no new main-board routing was added. the complete
installed harness is not qualified.

| link | center terminal | I/O terminal | center pins, in order | I/O pins, in order |
| --- | --- | --- | --- | --- |
| left | J2430 | J2431 | 1: USB_PD_SELECTED, 2: PD1_VBUS_RAW, 3: VSYS | 1: VSYS, 2: PD1_VBUS_RAW, 3: USB_PD_SELECTED |
| left | J2450 | J2451 | 1: MCU_3V3, 2: SYS_3V3, 3: AUX_DC_RAW | 1: AUX_DC_RAW, 2: SYS_3V3, 3: MCU_3V3 |
| left | J2460 | J2461 | 1: GND | 1: GND |
| right | J2432 | J2433 | 1: SYS_5V, 2: PD2_VBUS_RAW, 3: PD2_VBUS_GATED | 1: PD2_VBUS_GATED, 2: PD2_VBUS_RAW, 3: SYS_5V |
| right | J2452 | J2453 | 1: MCU_3V3, 2: PCIE_3V3, 3: SYS_3V3 | 1: SYS_3V3, 2: PCIE_3V3, 3: MCU_3V3 |
| right | J2462 | J2463 | 1: GND | 1: GND |

the three-pole parts are WAGO 2060-453/998-404. the single return terminals
are 2060-451/998-404. both are 4.5 mm high. use Alpha 6715 18 AWG,
strip 7..9 mm and hold the release button while inserting stranded wire.
do not solder-tin the stripped ends. the 20..100 mm lengths in the power
calculations are bounds, not a finished cut list. keep both ground braids.

J2434/J2435 retain the AMASS XT30PW-F30.G.Y / XT30U-M.G.Y connection.
the direct USB5 loom now specifies Alpha 6716 16 AWG, 400..420 mm.
pin 1 is GND and pin 2 is USB_PORT_5V at both ends. insulate and support
the solder joints independently. the retention lands stay isolated.

Alpha 6715 has an 8.763 mm minimum bend radius using its maximum diameter.
the corresponding limit for Alpha 6716 is 10.541 mm. final dressing, clamps,
terminal access, voltage drop, shared-return current and temperature still
need checking. see [power revision status](power-revision.md) and
[the connector contract](../../gen/usb_power_contract.py).

## BMS wiring

| connection | ends | construction |
| --- | --- | --- |
| protected pack power | center J2071 to BMS J2072 | WAGO 2060-452/998-404 terminals, Alpha 6715 18 AWG; 90 mm wire budget |
| isolated control | center J2073 to BMS J2074 | JST SM05B-SRSS-TB headers, SHR-05V-S housings, SSH-003T-P0.2-H contacts; five wires |
| cell temperature probes | BMS J2200 to three insulated probes | JST SM06B-SRSS-TB header; three separate wire pairs to SEMITEC 104JT-025 probes |

the protected power cable joins BMS pin 1 to center pin 2 for PACK_POS_FUSED,
and BMS pin 2 to center pin 1 for FG_VSS. FG_VSS reaches system ground
through the center's gauge shunt. label and continuity-check both wires.

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

J2 is now the four-contact Molex 43045-0400, with a 43025-0400 housing
and 43030-0038 tin contacts for 18 AWG wire. its new map is 1 raw negative,
2 cell 2 tap, 3 raw positive and 4 cell 1 tap. the old six-wire harness
does not match this revision. cell taps stay on the BMS. all routes need to
include the actual plugs, wire exits, bend clearance, and insulating supports.

## other internal cables

| Connection | What is fixed | What remains |
| --- | --- | --- |
| Keyboard | 30-pin interface; center J310 is at (145, 49), rotation 270 | Installed route, length, seating, and continuity against both board revisions |
| Radio | Removable 30-pin interface; saved center J2300 is at (82.25, 117.75), rotation 0 | Proposed suspended case pose and route are in `mechanical/case-prototype`; physical fit and cable length remain pending |
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
| 2 | 29 | Switched, current-limited RGB 5 V |
| 27 | 4 | I2C SDA |
| 28 | 3 | I2C SCL |
| 29 | 2 | 3.3 V through fitted R387, for the RGB I2C buffer |
| 30 | 1 | GND |

the matrix contacts follow the same reversal. the sources are
`gen/generate_keyboard_interface_sheet.py` and
`gen/generate_keyboard_daughterboard_sheet.py`.

the RGB revision uses both supply contacts. fit R387, a 0 ohm 0603 resistor,
and leave the R386 bypass unpopulated. U310 keeps 5 V off until the EC
asserts `KB_RGB_PWR_EN`; its nominal current limit is about 0.4 A. the
keyboard's IS31FL3743A uses a 33.2k current-setting resistor, with about
0.20 A of peak LED sink current at the published datasheet corner. budget
0.25 A for the RGB 5 V feed, including logic and margin, and verify it on
the first board. the contact is rated 0.5 A with the specified connector.

J320 pins 10, 11, 12, 27 and 28 are unused. pin 28's old one-wire RGB
option is not used by this I2C design. U321 isolates the switched-off LED
driver from the live EC bus. [keyboard notes](../../keyboard/README.md) have
the driver mapping and routing order. verify the installed cable's
continuity before power; this revision still needs routing and fabrication checks.

## before a cable is released

record the exact connector and cable parts/drawings, mating contact sides,
pin-1 datums, complete conductor map, contact thickness, length, bend limits,
current limits, and any shield termination. prove the map by continuity on
the real seated assembly before power. keep that result with the board revision.
