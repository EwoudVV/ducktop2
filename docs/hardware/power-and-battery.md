# power and battery

updated 5 september 2026. the four-layer BMS routing is finished. the saved
board has zero DRC errors, warnings, or unconnected items, and schematic
ERC is clean. the power and sense routing checks are complete. assembled
hardware still needs the protection, load, and thermal tests below.

## cells and board responsibilities

the pack target is three 10 Ah pouch cells in series, or 111 Wh at
3 x 3.7 V nominal. exact cell identity, ratings, thickness, tab geometry,
and thermal behavior still need to be part of the pack's build record.

J2 on the BMS brings in two pack-positive contacts, two pack-negative
contacts, `CELL1_TAP`, and `CELL2_TAP`.

| Job | Part / location |
| --- | --- |
| Per-cell voltage/current protection and passive balancing | U719 BQ7791500, BMS |
| Primary disconnect FETs | Q703/Q704, BMS return path |
| Secondary whole-pack protection | U11 LTC4368-1, Q11/Q12, RS10 on BMS positive path |
| Pack fuse | F1, BMS |
| Pack charging and NVDC power path | U2 BQ25798, center |
| Fuel gauge | U10 BQ34Z100-G1, center |
| Gauge current shunt | RS1, center |
| Ship FET | Q25 CSD17575Q3, center |

## positive path

the schematic's connection order is:

```text
J2 PACK_POS_RAW
  -> F1
  -> BAT_PROT_VIN
  -> Q11
  -> BAT_PROT_FET_COMMON
  -> Q12
  -> BAT_PROT_SENSE
  -> RS10, 11 milliohms
  -> PACK_POS_FUSED
  -> FPC106 / FPC105
  -> center ship FET and charger battery path
```

`BAT_PROT_FET_COMMON` belongs to the LTC4368 stage. `BAT_PROT_SENSE` is
also part of the main current path, despite its name.

both F1 pads numbered 2 connect to `BAT_PROT_VIN`. the old fuse-to-output
bypass is gone. the input, FET interconnect, shunt input, and protected
output use wider routes, parallel copper, and multiple vias at their
main transitions. the protected output no longer takes the long edge detour.

U11 SENSE and VOUT each run directly to their RS10 pad. neither trace joins
the load copper before reaching the shunt. the physical copper check includes
zone fills, so a same-net pour cannot silently bypass the separate pickup.

the twelve positive FPC contacts are fed from both ends of their pin group,
with a three-layer bus and a front copper spreader. the fifteen return
contacts use `FG_VSS`. the FET pin-one markers and test-point outlines now
clear the exposed pads.

source: [LTC4368 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4368.pdf),
layout considerations.

## return path and reference grounds

the intended connection order from cell negative towards system ground is:

```text
J2 PACK_NEG_RAW
  -> RS11, 8 milliohms
  -> BMS_SENSE_N
  -> Q703
  -> BMS_FET_COMMON
  -> Q704
  -> FG_VSS
  -> FPC106 / FPC105
  -> center FG_VSS
  -> RS1, 5 milliohms
  -> system GND
```

the BQ77915 itself uses `PACK_NEG_RAW` as its VSS reference. `FG_VSS` is
the protected external return on the BMS. the center uses `/FG_VSS` for
the same cable connection, on the pack side of the gauge shunt.

the quiet `PACK_NEG_RAW` copper joins the battery return at J2 pin 4.
it stays separate from the high-current run to RS11. R845 and R846 have
separate pickups at the two RS11 pads. R844 senses the top cell at J2 pin 1;
R840 and R844 exchanged positions to make room for that connection.
R850 now sits beside Q704, with a short gate-to-source branch.

raw pack negative does not cross FPC-3. an extra bond from raw negative to
system ground would bypass the primary return protection and gauge path.
test equipment grounds also need to respect these separate nodes.

## balancing

the cell taps stop at the BMS because balancing happens there. the center
charger supplies pack-level current; it does not need cell-tap wires in FPC-3.

U719's CBI pin is tied to its VSS reference, enabling autonomous balancing.
R841-R844 are 75 ohm input/balance resistors, with the 1 uF cell-filter
network. the three-cell configuration ties the unused upper cell inputs to
the top-cell sensing node.

the internal balancing path includes two input resistors plus the internal
FET resistance. TI's 75 ohm example is about 25 mA at 4.1 V. "up to 50 mA"
is the IC's capability, not the current set by these parts. balancing also
depends on the device's charging state, cell-voltage thresholds, and faults.
its performance with the actual cells still needs testing.

source: [BQ77915 datasheet](https://www.ti.com/lit/ds/symlink/bq77915.pdf),
sections 9.3.4 and 10.2.2.

## charging inputs and rails

PD1 enters on left J21, PD2 on right J11, and AUX at left J190. their
qualification, protection, and selector paths span the side and center
boards. the center U15/U15B cascade gives the intended external-input
priority PD1, then PD2, then AUX. the left U14 stage is also part of the
input path and must be included in a complete source-transfer review.

the recorded nominal selector windows are 13.1-17.1 V for the USB paths,
5.59-23.3 V for AUX, and 5.99-22.45 V for the stage-2 input. these are design
thresholds, not a complete test setup or a promise that every voltage in a
window has a usable power budget. the always-on 6.2 V UVLO deliberately
excludes a 5 V-only USB-C source from starting the laptop.

the BQ25798 feeds the NVDC system path. downstream converters provide
`MU_12V`, `SYS_5V` at a 5.10 V nominal target, system 3.3 V, endpoint power,
and the always-on EC supply. the USB hub/port supply has its own left-board
conversion. `MCU_3V3` on the BMS is supplied through FPC-3; there is no local
3.3 V regulator to test by powering J2 alone.

## firmware and temperature decisions

the EC is meant to qualify inputs, confirm applied current/power limits, and
sequence charging and loads. the present target code still leaves charge
and Mu/eDP budget commands unfinished. see [target status](../../firmware/README.md#stm32-target).

the recorded pack design omits a battery thermistor harness. the charger
and protector use their documented unused-temperature arrangements, with
cell-local cutoff boards intended to provide thermal cutoff. this is a
design decision to preserve in reviews; the actual cell assemblies and
their cutoff behavior still need verification.

## routing checks and load tests

the checked board has 62 footprints, 730 track segments, 313 vias, and four
35 um copper layers. all 187 connected physical pads match a fresh schematic
export. the FET footprint combines drain contacts 5-8 in its single pad 5.
its copper and paste geometry are unchanged by the pin-marker cleanup.

the copper loss calculation uses the actual filled geometry, 35 um copper,
and 20 um hole plating. resistance was checked on a 0.1 mm grid, with 0.05 mm
checks for the shunt pickup and connector sharing.

| copper path | estimated resistance at 20 C |
| --- | ---: |
| battery positive to fuse | 9.4 milliohms |
| fuse to Q11 | 4.0 milliohms |
| Q11 to Q12 | 6.1 milliohms |
| Q12 to RS10 | 9.5 milliohms |
| RS10 to FPC positive | 8.5 milliohms |
| battery negative to RS11 | 6.2 milliohms |
| RS11 to Q703 | 1.9 milliohms |
| Q703 to Q704 | 4.3 milliohms |
| Q704 to FPC return | 4.6 milliohms |

together, these copper paths dissipate about 0.61 W at 3 A or 2.1 W at
5.6 A with copper assumed to be at 80 C. this excludes the FETs, shunts,
fuse, connectors, and cable. 80 C is an input to the resistance calculation,
not a prediction of board temperature.

the 5.6 A review load covers the LTC4368's 60 mV upper forward threshold
with an 11 milliohm shunt at -1% tolerance. at that load, the largest
calculated positive-contact current is 0.497 A with equal 20 milliohm
external paths, or 0.479 A with equal 50 milliohm paths, using 80 C copper.
the connector rating is 0.5 A per contact. actual contact and cable
variation still needs a load test. these calculations do not establish a
continuous operating-current rating for the assembled pack.

source: [Hirose FH12 connector rating](https://www.hirose.com/en/product/p/CL0528-0019-5-98).

the small resistor and capacitor designators are on the back silkscreen.
front test-point numbers 1-16 correspond to TPB1-TPB16 in the schematic;
point 14 uses stacked digits. the assembly layer retains the full references.

the remaining work is physical bring-up: protection trip and recovery,
current sharing, voltage drop, balancing, and temperature under load. the
gauge also needs configuration and calibration for the actual pack. use the
[bring-up plan](../BRINGUP_TEST_PLAN.md) before powered integration.
