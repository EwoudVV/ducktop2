# power and battery

updated 4 october 2026. the four-layer BMS is routed and saved for stronger
battery operation. it uses a BQ76922 and an 8 A discharge target, with up to
3 A charging. the first assembly is an unarmed prototype for programming,
calibration and protection tests.
[current board status](../../README.md#build-status)

## Mu Ultra power target

the input target is 100 W over USB-C, at 20 V / 5 A. the revised circuit
uses an ISL9241 buck-boost charger, TPS25982 input switches and a TPS552882
Mu supply. both official PD profiles include 20 V / 5 A. these belong to
the revised power circuit, not the earlier BQ25798 board. see the
[revision status](power-revision.md) for integration and routing progress.

charging needs to work while the laptop is running, starting up or shut
down. smaller 5 V and 9 V chargers should work too. the laptop takes what
it needs first, then the remaining input power charges the battery. if the
charger cannot cover the load, the battery supplies the difference within
its allowed current. charging resumes when there is enough spare power.
the pack temperature limits still apply in every state.

the EC permits charging without a running OS after checking that the Mu
rail is off or reserving its qualified startup budget. the selector windows
and firmware accept 5, 9, 15 and 20 V contracts. this behavior has software
tests; source transitions and charging on the actual boards remain untested.

RS11 is a true four-terminal 2 milliohm CSS4J-4026K-2L00F shunt. separate
INA381 current guards detect discharge and charging, with nominal fault
trips around 9.1 A and 4.1 A. those are trip thresholds, not load ratings.
the BQ76922 also provides overcurrent and short-circuit protection. the
component calculations are in
[the BMS verifier](../../gen/verify_bq76922_calculations.py).

the 8 A target still needs checks with the actual cells, leads, connectors
and finished board. adapter transfers and startup need measurements too.
charging, external USB loads and the processor share the available power.

the new charging profile uses 12.12 V for the pack and stops charging if
any measured cell exceeds 4.10 V or the cells differ by more than 30 mV.
this leaves room below the protection trip. charging finishes after 30 seconds
of confirmed constant-voltage taper; a small adapter's current limit does
not count as a full battery. the two-hour timeout counts time in the
constant-voltage phase, so it does not cut off a long bulk charge.
[charging limits and tests](../../firmware/bq76922/charge-policy.md)
include the calibration needed before enabling that profile on hardware.

## cells and responsibilities

i have three AKZYTUE packs and have tested them in series with both cell
taps connected. their advertised capacity, continuous current, temperature
limits, and individual protection boards still need qualification for this
laptop. capacity on a listing is not a measured runtime or energy result.
i want to keep these cells. the proposed pack uses this common BMS, but
the cells and replacement wiring still need to meet its current limits.

| job | circuit |
| --- | --- |
| cell voltage and native current protection | U719 BQ76922RSNR, on the BMS |
| charge and discharge disconnect | high-side Q11/Q12 CSD18540Q5B |
| independent current guards | U2210/U2211 INA381 and RS11, on the BMS |
| startup current limiting | U2218 TPS26600, with an independent discharge-temperature veto |
| pack fuse | F1, 10 A Schurter HCF 3-101-051 |
| cell temperature windows | three insulated probes and the BMS comparator/control circuit |
| charging and system power path | U2 ISL9241, on the center board |
| fuel gauge and current measurement | U10 BQ34Z100-G1 and RS1, on the center board |
| NVDC battery path | Q25, on the center board; its body diode supplies VSYS during startup |

## pack paths

the positive path is:

```
J2 PACK_POS_RAW
  -> F1
  -> BAT_PROT_VIN
  -> Q11 charge FET
  -> BAT_PROT_FET_COMMON
  -> Q12 discharge FET
  -> PACK_POS_FUSED
  -> J2072 pin 1 / J2071 pin 2
  -> center Q25 and charger battery path
```

the FETs share their drains. the limited startup branch runs in parallel
with them after the fuse. its current is included in the return shunt.
R870, R871 and R872 are unpopulated drive-release links for fixture testing;
the normal power path must stay disabled until its configuration and fault
tests pass. keep the fuse, FET and connector paths wide through their
narrowest sections, including changes between layers.

the return connections are:

```
raw pack negative
  <-> RS11, 2 milliohms
  <-> FG_VSS
  <-> J2072 pin 2 / J2071 pin 1
  <-> center gauge shunt RS1
  <-> system GND
```

keep the quiet raw reference at the protector separate from load current.
the shunt's two sense terminals have separate traces to the monitor and
current guards. load current must use its force terminals. zero DRC errors
alone cannot prove those pickups or the filled power-path widths.

raw negative, FG_VSS, CTRL_GND and system GND have different jobs. their
connections are defined by the protection, isolation and gauge circuits.
extra ground bonds would bypass those circuits. PDSG_RTN is a separate
local return for the startup limiter; do not bond it to RAW, FG or CTRL.
use insulating BMS supports and isolated equipment on the raw service pads.

## temperature and control

J2200 connects three SEMITEC 104JT-025 insulated probes, one per cell.
pairs 1/2, 3/4 and 5/6 correspond to cells 1, 2 and 3. the probe interface
has its own lead-current limiting and filters. the comparator circuit has
separate charge and discharge windows and checks for open and shorted
probe connections. its raw-referenced supply works independently of the EC.

the temperature and current circuits directly veto the charge and
discharge FETs through CFETOFF and DFETOFF. their permission also gates the
limited startup branch. a TPS22810 switches the thermal supply off in deep
BMS shutdown, while keeping it on through ordinary protection faults.

the five-wire control cable carries PACK_MONITOR_READY, SCL, MCU_3V3, SDA
and CTRL_GND. readiness means the monitoring supply and thermal supervisor
are alive. fresh I2C reads provide cell voltages, current, protection flags
and FET state. it is not an all-faults-clear signal. the control return stays
separate from both pack returns. [cable pinouts](cables-and-connectors.md#bms-wiring)

the electrical window calculations include the specified probe and
resistor tolerances. probe attachment, insulation, cell-to-probe temperature
difference and response delay still need tests. the final operating limits
also depend on the actual cells. the old plan to omit cell-temperature
monitoring has been replaced.

## balancing

cell taps stop at the BMS. the center charger supplies current to the whole
pack. the BQ76922 uses physical cell inputs 1, 2 and 5 for this three-cell
stack; unused inputs share the cell-2 node. R841 through R844 are 75 ohms
with 220 nF cell filters. balancing stays disabled in the initial profile.
it needs its own cell, temperature and charging checks before use.

## charging inputs and rails

PD1 enters through left J21, PD2 through right J11, and AUX through left
J190. source selection and protection span the I/O and center boards.
the PD configurations contain 5, 9 and 15 V sink profiles at up to 3 A,
and a 20 V profile at up to 5 A.
the EC still has to qualify the negotiated source and apply the complete
input and charging budget before admitting loads.

U2 supplies the system power path. standby takes battery power from VSYS,
so its draw is included in the charger battery shunt. raw USB and AUX feeds
can also start the standby supply. the LTC4368 voltage protection and
LTC4231 current limiter operate before the EC boots. the downstream circuits provide MU_12V,
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
the 8 A target requires measured voltage drop and temperature at the
narrowest routes, connector joints, shunt and FETs. component fault-trip
calculations do not establish a safe continuous current for the cells.

the finished hardware still needs cell/cable qualification, gauge
calibration, trip and recovery tests, source transfer, thermal tests,
charging tests and the recorded firmware hardware tests. use the
[bring-up plan](../BRINGUP_TEST_PLAN.md) and keep results tied to the exact
board, firmware, cells and harnesses used.
