# the center board's 8 A battery path

5 october 2026. this check covers Q25, both center shunts, the protected
power pair and the input bank seen during startup. the BMS circuit and its
routing are unchanged. the main boards still need routing and bench tests.

## gate-drive fix

R2600 is now **1 Mohm, RC0603FR-071ML**, in its existing 0603 footprint.
the schematic, PCB fields and generator agree. no component moved and no
copper changed.

the old 100 kohm gate-to-source resistor drew 20 uA at 2 V before tolerances.
Renesas specifies a 15 uA minimum BGATE source current at that same test
point. including the resistor's 5% environment allowance and Q25's stated
25 °C gate leakage gives 21.15 uA with the old part and 2.21 uA with 1 Mohm.
the old value could keep the gate from reaching the intended drive voltage.

this comparison does not specify the complete gate-voltage ramp. before
allowing a sustained heavy load, measure at least 4.5 V from Q25 gate to
source through the operating temperature range. the resistor is a gate
return, not a battery disconnect. Q25's body diode still conducts from the
battery toward VSYS when its gate is off.

[ISL9241 electrical characteristics and BGATE operation](https://www.renesas.com/en/document/dst/isl9241-datasheet)

## current and heat

the forward path is J2071 pad 2, Q25 source-to-drain, RS2601, then VSYS.
the return is system GND, RS1, then J2071 pad 1 / FG_VSS. Q25 stays
CSD17575Q3; neither shunt needs a larger part for the calculated normal load.

| part or section | resistance used by this check | loss at 8 A | drop at 8 A |
| --- | ---: | ---: | ---: |
| RS1, WSLP25125L000FEA | 6.205 milliohm upper corner | 0.397 W | 49.6 mV |
| RS2601, WSLP2512R0100FEA | 11.359 milliohm upper corner | 0.727 W | 90.9 mV |
| Q25 | 6.4 milliohm hot sizing assumption | 0.410 W | 51.2 mV |
| both protected power wires | 120 mm each, 30 milliohm/metre hot acceptance limit | 0.461 W | 57.6 mV |
| total above | excludes contacts, solder and PCB copper | 1.994 W | 249.3 mV |

the shunt resistance bounds include initial tolerance, TCR through 170 °C,
and the existing endurance/soldering stress allowances. their power check
retains the conservative 2 W design labels, derated to 1.4 W for a 100 °C
local ambient. the earlier charger calculation uses a 100 °C resistance
screen; this complete-path check also includes higher element temperature.
adding the separate qualification-test drifts is a design screen, not a
guaranteed lifetime change.

Q25's 25 °C maximum is 3.2 milliohms at 4.5 V gate drive. the 2x hot factor
is a sizing allowance above the typical temperature curve, not a guaranteed
hot resistance specification. at 0.410 W and 85 °C local air, keeping the
junction below 125 °C requires an installed thermal resistance below
97.7 °C/W. TI's 160 °C/W minimum-pad example does not meet that target.
provide heat-spreading drain copper and suitable vias, then measure the
assembled result with the neighboring converters running.

[Vishay WSLP ratings and drift terms](https://www.vishay.com/docs/30122/wslp.pdf),
[TI CSD17575Q3 electrical and thermal data](https://www.ti.com/lit/ds/symlink/csd17575q3.pdf)

the two-pole WAGO terminals are rated 9 A with the specified 18 AWG wire.
that leaves only 1 A above the operating target. check each termination's
resistance and temperature at 8 A; the rating does not establish the complete
loom's voltage drop. the four wire terminations, solder joints and PCB necks
are additional losses to the table.

at the table's upper resistance corners, the protected BMS connector needs
at least 10.249 V to maintain 10.0 V VSYS at 8 A, even before those additional
losses. use the measured VSYS and the allowed load budget when deciding
whether to start or transfer the running laptop to battery.

## sensing and layout

RS1 produces at most 49.64 mV in the 8 A discharge screen and 18.61 mV at
3 A charge, within the gauge's +/-125 mV recommended differential range.
its SRP pickup belongs on the FG_VSS side, and SRN on the system-ground
side. R183/R184 and C181 filter those separate pickups. keep load current
out of the sense traces and the gauge's quiet ground connection.

RS2601 produces 90.87 mV at 8 A. that is below the ISL9241's 300 mV absolute
differential limit; it does not establish ADC accuracy. take CSOP from the
VSYS end and CSON from CHG_SRN. keep the gauge shunt and the BMS shunt in
the complete return path. no support, shield or extra ground bond may
bypass either one.

the gauge's recommended differential range is exhausted around 20.3 A at
RS1's upper resistance corner. fault peaks can exceed the normal 8 A load.
check the actual sense-pin excursions during protected short tests rather
than assuming the gauge continues to report a valid current.

[BQ34Z100-G1 sense-input limits and layout](https://www.ti.com/lit/ds/symlink/bq34z100-g1.pdf)

## startup and faults

the fresh netlists contain 32 direct input capacitors in the center, left
and BMS sections. their sum with initial tolerance is 512.252 uF. the BMS
startup model allocates 695.3585 uF and a separate 0.8 A load envelope for
standby conversion and other startup draw. temperature, disabled-rail
leakage and the complete current-versus-voltage ramp still need measurement.

with that existing allocation, the TPS26600 model gives a 14.34 ms ramp and
a 1.832 A peak screen. assuming a 1 V Q25 body-diode drop throughout that
interval gives 26.3 mJ. these are conditional estimates: the eFuse data
uses different test voltages, and the diode voltage is not guaranteed over
the whole temperature range by the single 25 °C table point.

the main-FET handoff is a separate event from the limited ramp. record its
remaining voltage difference, peak current and pulse duration. also check
hot starts, adapter removal and reinsertion, a shorted output and repeated
faults. the TPS26600 thermal latch has no guaranteed maximum fault duration,
and neither the BMS current-trip setting nor the 10 A fuse is an instantaneous
current clamp. compare measured waveforms with the component pulse limits
and fuse clearing data before enabling operation.

## reproducing the checks

`gen/verify_battery_path.py` takes fresh `--center`, `--left`, `--right` and
`--bms` KiCad XML netlists plus an `--output` JSON path. it checks the named
parts, wire pin maps, sense connections, gate load, shunt loss, sense range
and startup bank. the gate-return check also runs in the main electrical
calculation report.

`gen/test_battery_path.py` includes the old 100 kohm failure, reversed Q25
and harness connections, a misplaced gauge pickup, a shunt substitution,
extra input bulk and a different startup limiter. the corrected native
design passes all nine numerical checks, and all eight regression tests
pass. the updated center has zero ERC errors, matching schematic/PCB
connections and unchanged routing findings.

[current power checkpoint](../../verification/power-revision-checkpoint.json)
records source hashes and the remaining physical tests. operating permissions
remain disabled until those tests and the cell qualification are complete.
