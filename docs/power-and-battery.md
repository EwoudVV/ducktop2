# power and battery

updated 4 september 2026. this page describes the intended connections.
BMS-01 and BMS-02 in [current status](design-status.md) must be resolved
before treating the routed BMS as matching that design.

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

on the reviewed board, both F1 pads numbered 2 are instead assigned to
`PACK_POS_FUSED`. that joins the fuse directly to the output and bypasses
the intended secondary stage. the same assignment is present in the
pre-routing commit. changing the documentation has not corrected the board.

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
and Mu/eDP budget commands unfinished. see [target status](../firmware/README.md#stm32-target).

the recorded pack design omits a battery thermistor harness. the charger
and protector use their documented unused-temperature arrangements, with
cell-local cutoff boards intended to provide thermal cutoff. this is a
design decision to preserve in reviews; the actual cell assemblies and
their cutoff behavior still need verification.

## remaining review

resolve the F1 net mismatch and BMS layer conflict first. then check the full
current paths, shunt connections, gate routing, sensing branches, via
capacity, FFC current sharing, and fuse/protection tolerances. choose copper
weights from that review. there is no blanket trace width or temperature-rise
number that signs off every segment.

the gauge also needs configuration and calibration for the actual pack.
protection trip/recovery, charging, balancing, power transfer, and thermal
behavior all belong in the [bring-up work](BRINGUP_TEST_PLAN.md).
