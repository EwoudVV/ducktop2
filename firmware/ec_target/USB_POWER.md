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

U2402 retains the INA alert independently. reading the INA Mask Enable
register clears its internal alert flag, so that register alone cannot be
the hardware interlock. U2411 also gates on the raw alert: an asserted fault
still blocks the converter if clear and fault are asserted together.
R2400 pulls the converter enable output low during partial power loss.

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
the effective sense envelope is 4.757261 to 5.243261 mΩ, including the
specified layout allowance. each controller gets its own Kelvin pair from
the inner pad edges of RS1860. power-branch resistance mismatch must be
at most 20 µΩ; shared copper stays outside the sense pickup.

INA calibration is 2048 for a 0.5 mA current LSB. the alert limit is raw
0x2ffc, calculated from the low shunt corner, 0.6% ADC gain error and
25 µV offset/layout allowance. its maximum actual trip is below 6.5 A;
the opposite corner trips at about 5.817 A. the current target therefore
caps steady reservations at 5.5 A and the startup screen at 5.7 A.
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

`gen/usb_power_contract.py` defines the straight-numbered looms. J2430/J2431
use 43045-1200 headers and 43025-1200 housings for left power. J2432/J2433
use the 10-contact versions for right power. J2434/J2435 use the 8-contact
versions for direct left-right USB5, with four positive and four return
conductors. every terminal is 43030-0038, tin, 18 AWG. different circuit
counts prevent interchanging these three looms.

wire is Alpha 3253 UL1061, 18 AWG, 7/26 tinned copper: red 3253 RD005 and
black 3253 BK005. maximum OD is 1.778 mm, below the terminal's 1.85 mm
limit. wire temperature is limited to 80 °C, and the minimum bend radius
is 17.78 mm. cut lengths between crimp barrels are 90 to 100 mm for the
seams and 280 to 300 mm for USB5. the Micro-Fit mated height is 10.29 mm;
wire exit and latch access need additional space. see
[Alpha 3253](https://www.alphawire.com/products/wire/hook-up-wire/premium/3253)
and the [Molex drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43045/430451000_sd.pdf).

use the conservative 12-circuit, 18 AWG, 5.5 A reference screen for every
contact, not the 2-circuit headline rating. the
[Molex specification](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/430/43045/PS-43045-001.pdf?inline=)
requires an assembled temperature-rise evaluation. our acceptance limits
are 45 mΩ per hot/aged mated-and-crimp termination and 30 mΩ/m for hot
wire. neither is claimed as a measured result. individual cold return
resistance must be at least 2 mΩ for a seam and 4 mΩ for direct USB5.
with at most 10 mV per seam and 20 mV left-right GND difference, each
return is bounded to 5 A even with unequal sharing. the ground limits must
include every signed return path, including the signal shields.

four positive conductors at their maximum resistance bound the USB5 bank
at 24.75 mΩ. with 20 mΩ board copper allowance, 2.015 A right load and
the 20 mV total ground limit, the right PP5V floor is about 4.956 V.
J12's VBUS floor is about 4.781 V after its switches and a separate 40 mV
hot TPD1S514 allowance. the ground-bond geometry, this hot switch bound,
wire temperatures and every assembled resistance remain qualification
conditions. no equal current split or ideal ground is assumed.

run `gen/verify_usb_power.py` against fresh native center, left and right
XML exports. it checks source wiring, not PCB routing or fabrication approval.
