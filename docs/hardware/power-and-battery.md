# power and battery

updated 10 september 2026. this describes the corrected circuit. the revised
four-layer BMS layout is still being finished and checked. the old routing
results do not cover its new thermal circuit or separate cable connections.
[current board status](../../README.md#build-status)

## cells and responsibilities

i have three AKZYTUE packs and have tested them in series with both cell
taps connected. their advertised capacity, continuous current, temperature
limits, and individual protection boards still need qualification for this
laptop. capacity on a listing is not a measured runtime or energy result.
the design keeps the existing packs under review. removing their protection
boards has not been established as a suitable change.

| job | circuit |
| --- | --- |
| cell voltage protection and balancing | U719 BQ7791500, on the BMS |
| primary return disconnect | Q703/Q704 and RS11, on the BMS |
| bidirectional pack breaker | U11 LTC4368-1, Q11/Q12 and RS10, on the BMS |
| pack fuse | F1, 10 A MINI fuse in its specified holder |
| cell temperature windows | three insulated probes and the BMS comparator/control circuit |
| charging and system power path | U2 BQ25798, on the center board |
| fuel gauge and current measurement | U10 BQ34Z100-G1 and RS1, on the center board |
| ship disconnect | Q25, on the center board |

## pack paths

the positive path is:

```
J2 PACK_POS_RAW
  -> F1
  -> BAT_PROT_VIN
  -> Q11 / Q12, controlled by LTC4368
  -> BAT_PROT_SENSE
  -> RS10, 11 milliohms
  -> PACK_POS_FUSED
  -> J2072 pin 1 / J2071 pin 1
  -> center ship FET and charger battery path
```

U11's two sense connections must reach the RS10 lands independently of the
load-current route. keep the FET, shunt and connector current paths wide,
including their transitions between layers. neither a copper pour nor a
local signal repair may bypass the fuse, FETs or shunt.

the return connections are:

```
raw pack negative
  <-> RS11, 8 milliohms
  <-> Q703 / Q704
  <-> FG_VSS
  <-> J2072 pin 2 / J2071 pin 2
  <-> center gauge shunt RS1
  <-> system GND
```

keep the quiet raw reference at the protector separate from load current.
the BMS layout checks preserve the original FET and Kelvin geometry and
the continuous filled power areas. the new dedicated FG_VSS output return
is checked separately from the thermal and control routing.

raw negative, FG_VSS, CTRL_GND and system GND have different jobs. their
connections are defined by the protection, isolation and gauge circuits.
extra ground bonds would bypass those circuits. use insulating BMS
supports and include test-equipment grounds in the connection review.

## temperature and control

J2200 connects three SEMITEC 104JT-025 insulated probes, one per cell.
pairs 1/2, 3/4 and 5/6 correspond to cells 1, 2 and 3. the probe interface
has its own lead-current limiting and filters. the comparator circuit has
separate charge and discharge windows and checks for open and shorted
probe connections. its raw-referenced supply works independently of the EC.

charge-temperature permission reaches the EC as PACK_CHG_TEMP_OK.
discharge faults also assert PACK_FAULT_N. the retry input and status
signals cross the isolated control interface. that interface uses a
separate five-wire cable, with center GND connected only to the BMS
CTRL_GND island. [cable pinouts](cables-and-connectors.md#bms-wiring)

the electrical window calculations include the specified probe and
resistor tolerances. probe attachment, insulation, cell-to-probe temperature
difference and response delay still need tests. the final operating limits
also depend on the actual cells. the old plan to omit cell-temperature
monitoring has been replaced.

## balancing

cell taps stop at the BMS. the center charger supplies current to the whole
pack, while U719 handles balancing locally. R841 through R844 are 75 ohms,
with the 1 uF cell-filter network. the unused upper cell inputs connect to
the top-cell sensing node for this three-cell arrangement.

these parts set a balancing current of roughly 26 mA in the nominal
calculation. verify balancing behavior with the actual cells, including
voltage differences, charging state and fault recovery. the protection and
balance checks are in
[verify_electrical_calculations.py](../../gen/verify_electrical_calculations.py).

## charging inputs and rails

PD1 enters through left J21, PD2 through right J11, and AUX through left
J190. source selection and protection span the I/O and center boards.
the PD configurations contain 5, 9, 15 and 20 V sink profiles, up to 3 A.
the EC still has to qualify the negotiated source and apply the complete
input and charging budget before admitting loads.

U2 supplies the system power path. the downstream circuits provide MU_12V,
SYS_5V, SYS_3V3, endpoint power and the always-on MCU supply. the left board
has a separate USB5 converter with current monitoring, a hardware fault
latch, per-port permissions and controlled startup. its right-side load
uses the direct XT30 loom.

USB5's nominal target is 5.160784 V. its allowed loads, voltage-loss budget,
startup restrictions and ground bounds are recorded in
[I/O power qualification](io-power-qualification.md). keep those checks
together with the converter and harness revisions.

the EC firmware now includes applied charger limits, source transitions,
USB permissions, fault handling and host-budget checks. the operating
qualification gates remain disabled until their hardware requirements pass.
[firmware status](../../firmware/README.md)

## checks before use

the BMS routing needs both native connectivity checks and explicit power-path
checks. zero airwires alone does not establish current capacity or a valid
Kelvin pickup. inspect the filled copper, minimum widths, via transitions,
connector joints and the separate return domains.

copper loss calculations depend on actual finished copper and hole plating.
the revised output-return review is conditional on its stated copper and
assembly limits; it has not been measured on a manufactured board. the
8 A copper/harness screen is separate from the shunt-set pack protection
thresholds and does not establish an 8 A operating mode.

the finished hardware still needs cell/cable qualification, gauge
calibration, trip and recovery tests, source transfer, thermal tests,
charging tests and the recorded firmware hardware tests. use the
[bring-up plan](../BRINGUP_TEST_PLAN.md) and keep results tied to the exact
board, firmware, cells and harnesses used.
