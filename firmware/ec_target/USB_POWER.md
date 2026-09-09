# usb power control

USB power permission remains off in the default build. the new target path
has host tests and a native schematic-netlist check. it has not run on a
physical board. the gate, monitor, loom and ground-bond layout still need
placement, routing and qualification before a powered release.

## hardware and reset

U2400 is a TCA9539 at 0x76 on the left PD1 I2C channel, alongside U2401
INA226 at 0x40 and the PD1 controller at 0x20. the EC explicitly selects mux
channel 2 for every permission transaction. the existing service-reset gate
combines EC NRST and firmware's mux-reset request. its line reaches U2400
with a local pulldown. reset, missing reset wiring and loss of MCU power
leave the global and all seven port permissions off.

P0 bit 0 enables the global rail. bits 1 through 7 permit J21, J11, J22,
J23, J12, J24 and J25 in that order. P1 bit 0 is active-low fault clear;
it defaults high and is never tied to NRST. bits 1 through 5 read the fault
latch, raw INA alert, converter PG, PD1 gate PG and PD2 gate PG. both PD gate
PG inputs use dividers that stay below MCU_3V3 and above the expander's VIH.
P1 bit 6 observes the existing INTERNAL_USB_VBUS_VALID signal.

U2402 retains the INA alert independently. reading the INA Mask Enable
register clears its internal alert flag, so that register alone cannot be
the hardware interlock. U2412 on center ANDs U6 SYS_5V_PG with U771's actual downstream VBUS
supervisor. its result uses the existing INTERNAL_USB_VBUS_VALID seam
signal. U2413 on left ANDs that signal with the raw INA alert. this
combined result drives both U2402 preset and U2411's direct enable veto.
raw overcurrent or SYS5 loss therefore blocks power even while preset and
clear are asserted together.
R2400 pulls the converter enable output low during partial power loss.

a SYS5 brownout is retained in the independent latch even if the host lease
survives and the rail recovers before the next poll. cold start likewise
holds USB5 off until SYS5 PG and actual internal VBUS are valid, current is
fresh and quiet, and the host sends an explicit clear. rail recovery alone
never clears the latch. a failed clear readback, including PG loss during
the pulse, enters the EC reset path. no extra seam conductor is used.


J22, J23 and J12 retain their hub control and fault connections. their new
AND gates add the EC veto. J24 and J25 retain the existing host-active
condition. J21 and J11 have separate TPS22992S PP5V gates, with their PP5V
reservoirs behind the gates. the TPS25751 PP5V path provides the required
VBUS reverse blocking; the added gate alone does not.

## current reservations

| port | VBUS ceiling | reserved VCONN | other branch allowance | reservation |
| --- | ---: | ---: | ---: | ---: |
| J21, J11, each | 900 mA | 315 mA | common allowance | 1215 mA |
| J22, J23, each | 900 mA | 250 mA | 25 mA | 1175 mA |
| J12 | 500 mA | 250 mA | 25 mA | 775 mA |
| J24 | 900 mA | none | common allowance | 900 mA |
| J25 | 500 mA | none | common allowance | 500 mA |

there is also a 25 mA common allowance. all seven reservations total
6.980 A, so all seven ports cannot be admitted together under the current
5.5 A admission ceiling. the right harness reservation includes that full
common allowance conservatively, giving 2.015 A for both right ports.
retained ports have priority; additional ports must fit both the current
limits and the available input power after the host and other loads.

both TPS25751 controllers are read with length-prefixed, repeated snapshots.
the target observes connection, power/data roles, PP5V, external input path
and VCONN switch state. it also verifies one fixed 5 V / 900 mA source PDO,
default Type-C current, no BC charging advertisement, PP5V as the source path
and the external path as sink only. a higher advertisement or inconsistent
snapshot cannot obtain a port permission. sink power role does not imply
VCONN is off and does not release the possible 900 mA source reservation.
the current EEPROM defaults to DRP; reset is not claimed to establish
sink-only operation. changing Type-C mode can disconnect the port, so the
target does not change a live input merely to reduce its reservation.

TPS25810 exposes no direct VCONN state or I2C register. its full 250 mA
capability is reserved whenever its branch is enabled. its VCONN short
limit is 300 to 410 mA. TPS25751's two VCONN short-limit settings span
350 to 470 mA and 540 to 660 mA. these are fault limits, not additional
continuous budget. both kinds of controller retain their local protection.
see [TPS25810](https://www.ti.com/lit/ds/symlink/tps25810.pdf) and
[TPS25751A](https://www.ti.com/lit/ds/symlink/tps25751a.pdf).

R1780, R1740 and R1760 are 19.1 kΩ. the
[TPS2553 equation](https://www.ti.com/lit/ds/symlink/tps2553.pdf), page 15,
uses resistance in kΩ: minimum mA = 25230 / R^1.016 and maximum mA =
22980 / R^0.94. a conservative 5% total resistance envelope gives
1.199110 to 1.507018 A. this covers initial tolerance, full-category TCR,
endurance and assembly change. the old 20 kΩ low corner is 1.144307 A.

## monitor and target sequence

RS1860 and RS1861 are two ERJ8CWFR010V 10 mΩ resistors in parallel.
the effective sense envelope is 4.69483 to 5.30583 mΩ, including the
rounded 6% component allowance for initial tolerance, full-category TCR,
endurance and soldering, plus the separate 0.11% layout allowance. each controller gets its own Kelvin pair from
the inner pad edges of RS1860. power-branch resistance mismatch must be
at most 20 µΩ; shared copper stays outside the sense pickup.

INA calibration is 2048 for a 0.5 mA current LSB. the alert limit is raw
0x2f5a, calculated from the low shunt corner, 0.6% ADC gain error and
25 µV offset/layout allowance and one full ADC code for quantization. its maximum actual trip is below 6.5 A;
the opposite corner trips at about 5.673 A. the current target therefore
caps steady reservations at 5.5 A and the startup screen at 5.6 A.
64 averages with 140 µs bus/shunt conversions give a datasheet maximum
conversion window of 19.712 ms. physical total shutoff latency and fault
energy still need measurement. see the
[INA226 tables](https://www.ti.com/lit/ds/symlink/ina226.pdf).

USB input-power reservations are added to other auxiliary demand before
the charger allocation is applied. the target waits for that committed
reservation, then enables the global rail and waits for fresh measured
voltage and PG. it grants one new port per subsequent conversion. both the
full retained reservation and measured current must leave room for the
qualified inrush bound. a timer only limits the wait; it does not stand in
for measured rail readiness or physical hold-up.

lease expiry, thermal or bus failure, source transfer, rail loss and stale
measurements remove permissions. source-transfer inhibition happens before
the source-path commit. a write that cannot be verified requires EC reset,
which also resets the permission expander. fault clear needs an explicit
host request edge, all outputs off and fresh near-zero current. it never
runs as a repeated automatic recovery.

`DUCKTOP2_USB_POWER_QUALIFIED` remains 0. qualification also needs the right
harness current, complete USB-path minimum efficiency, measured PD-gate
inrush and measured branch inrush. the last four values default to zero.
`DUCKTOP2_AUX_WORST_CASE_MW` covers other loads; the target separately adds
USB demand. the host cannot turn on any qualification switch.

## separate power looms

J2430/J2431 use the 12-contact Micro-Fit loom; J2432/J2433 use the
10-contact loom. J2434/J2435 use XT30PW-F30.G.Y with XT30U-M.G.Y plugs
and one 18 AWG Alpha 5857 conductor per polarity. pad 1 is ground and
pad 2 is USB5. the direct USB loom has a conservative 8 A return design
bound and a 2.015 A maximum positive reservation.

the complete pin maps, dimensions, hot/aged resistance conditions, actual
load inventory, voltage budgets and signed ground proof are in
[I/O power qualification](../../docs/hardware/io-power-qualification.md).
`gen/calculate_io_power.py` reproduces the 7.845353 A worst normal cut
including startup and converter/loom losses. every accepted profile must
meet those branch ceilings and maintain true center VSYS at least 8.7 V.

BQ25798's 1 mV ADC resolution is not an absolute accuracy guarantee.
USB qualification therefore also requires measured worst-case VSYS
overestimate and rail-fall margins, including observation/shutoff latency.
`DUCKTOP2_VSYS_SENSE_QUALIFIED` and both margins default to zero.
readings older than 250 ms, an unqualified measurement, or a lower bound
below 8.7 V remove all USB permissions. target initialization rejects a
whole-path efficiency below 80% or an absent voltage margin.

run `gen/verify_usb_power.py` against fresh native center, left and right
XML exports. it checks source wiring, not PCB routing or fabrication approval.
