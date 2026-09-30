# i/o power looms and ground bounds

30 september 2026. these are the loom and return-current limits for the
100 W power revision. the calculation passes with the conditions below;
the assembled harnesses and operating profiles have not been qualified.
[power revision status](power-revision.md) records the board checkpoint.

power uses two short WAGO looms and one direct left-to-right XT30 loom.
positive supply rails stay off the 41/51-contact signal cables.
[usb_power_contract.py](../../gen/usb_power_contract.py) defines the pin maps,
parts and assembly limits. [calculate_io_power.py](../../gen/calculate_io_power.py)
reproduces the current and voltage screen.

| loom | board terminals | construction |
| --- | --- | --- |
| center to left | J2430/J2431 and J2450/J2451: WAGO 2060-453/998-404; J2460/J2461 return: 2060-451/998-404 | six positive rail wires and one return, Alpha 6715 18 AWG, 20..100 mm |
| center to right | J2432/J2433 and J2452/J2453: WAGO 2060-453/998-404; J2462/J2463 return: 2060-451/998-404 | six positive rail wires and one return, Alpha 6715 18 AWG, 20..100 mm |
| left to right USB5 | J2434/J2435: AMASS XT30PW-F30.G.Y, with two XT30U-M.G.Y plugs | one positive wire and one return, Alpha 6716 16 AWG, 400..420 mm |

each three-pole WAGO group reverses its numbered positions at the center
board. join matching rail names using the full
[pin table](cables-and-connectors.md#power-between-the-main-boards), then
check continuity, polarity and isolation before power. USB5 uses pad 1 for
GND and pad 2 for USB_PORT_5V at both ends. fit both Alpha 1230 ground
braids across each seam; they are part of the electrical design.

the WAGO terminals accept bare stranded wire. strip 7..9 mm, hold the
release button for insertion or removal, and do not solder-tin the ends.
use Alpha 6715 RD005/BK005 for the short looms. the wire is 18 AWG,
16/30 tinned copper with mPPE insulation, rated −40..105 °C. its maximum
outside diameter is 1.7526 mm and its 5D minimum bend radius is 8.763 mm.
[Alpha 6715 specification](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6715).

the WAGO current screen is 9 A per terminal. the model retains a 45 mΩ
maximum for each complete hot/aged wire termination and 30 mΩ/m for wire.
these are assembly acceptance limits, not claimed catalogue contact
resistances. a 100 mm positive conductor is therefore at most 93 mΩ.
the separate return wire must measure at least 0.12 mΩ at its cold corner.
that lower bound and the remaining braid's upper bound establish the
terminal-current limit below; equal current sharing is not assumed.

the direct loom uses Alpha 6716 RD005/BK005: 16 AWG, 26/30 tinned copper
with mPPE insulation. its maximum diameter is 2.1082 mm and minimum bend
radius is 10.541 mm. keep each mated and soldered termination at or below
5 mΩ after assembly, temperature and life tests, and wire at or below
30 mΩ/m. the published wire DCR is nominal and does not establish that
hot bound. [Alpha 6716 specification](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6716).

[AMASS 2025V0](https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf)
specifies 20 A at up to 85 K rise, 1.2 mΩ contact resistance, 100 mating
cycles and −20..120 °C. the project's direct-return design bound is 10 A.
qualify the complete loom at or below 80 °C, including solder joints and
connector bodies. the catalogue contact value does not prove the assembled
hot/aged resistance or temperature.

the WAGO bodies are 4.5 mm high. reserve release-tool access and wire
bends separately. the XT30 mated envelope is at most 23.10 × 13.60 mm,
with a conservative 5.75 mm above-board height; the case reserves 6 mm.
insulate the solder cups, keep retention lands isolated, strain-relieve
the wires independently, and mate only while unpowered.

use the reviewed [harness paths](power-harness-fit.md) for wire exits,
cut-length allowances, clamps and service access. 20..100 mm and
400..420 mm are electrical bounds, not finished cut lists. 420 mm remains
the nominal direct-loom cut target. the complete installed route still
needs a fit check after power placement; a flat plan view does not prove
case clearance. protected BMS power uses its separate WAGO 2060-452 link,
and the raw pack uses the four-contact Molex 43045-0400 map in the
[cable document](cables-and-connectors.md#bms-wiring).

## voltage and input power

USB5 is 5.160784 V nominal. the frozen initial, temperature, endurance and soldering DC screen is 5.102994..5.218866 V;
the ±20 mV ripple allocation leaves the upper corner below the fixed 5 V
PD limit of 5.25 V. the lower corner after negative ripple is 5.082994 V. the final feedback parts and their stress allowances are bound
in the electrical calculation record.
with a 22.6 mΩ direct positive loom, 20 mΩ total board-copper allowance,
2.015 A right-side reservation and 20 mV total ground difference:

- right PP5V after its TPS22992S gate is at least 4.960131 V;
- J12 VBUS is at least 4.784530 V, including its switch chain and a separate
  40 mV hot TPD1S514 loss allowance.

the hot TPD1S514 bound and all cable/board losses require physical checks.
raising the rail further would consume the fixed-PDO upper-voltage margin.
USB 2, Type-C and PD limits must all hold at their specified measurement
points. the reviewed primary sources are USB PD R3.2 V1.2, section 7.1,
and USB Type-C R2.5, chapter 4; the official downloads and agreement record
are retained privately with the project.

at the largest permitted startup load, solve the converter's constant-power
input including the positive loom and board resistance:

```
I × (8.7 V − 0.010 V − 0.108 Ω × I) = 5.238866 V × 5.6 A / 0.85
I = 4.189980 A
U1703 VIN = 8.237482 V
```

the 85% converter efficiency is a qualification floor over the complete
accepted operating range. it is not read from a typical efficiency graph.
this corner gives 80.481% efficiency from center VSYS to USB5, including
the loom. the EC's whole-path input reservation must use at least 80%
qualified efficiency, with the actual validated minimum used if lower
than a proposed profile. a profile below the 80% design floor is rejected.

true center VSYS must remain at least 8.7 V during this high-power USB5
state. the ISL9241 VSYS ADC has a 96 mV step; that resolution does not
establish absolute accuracy. the driver decodes this register in 96 mV
steps. there is no independent STM32 VSYS channel: PA6 senses AUX input,
PA7 skin temperature, and PB0 Mu temperature. AUX voltage is upstream of
the charger and cannot establish this floor.
[ISL9241 datasheet, ADC table](https://www.renesas.com/en/document/dst/isl9241-datasheet).

`DUCKTOP2_VSYS_SENSE_QUALIFIED`, `DUCKTOP2_VSYS_MAX_OVERESTIMATE_MV` and
`DUCKTOP2_VSYS_MAX_FALL_MV` remain zero. qualify the maximum positive
measurement error, including quantization, gain, offset, temperature and aging.
the fall allowance must cover the ADC conversion/poll cycle, the full
reported observation age and the time to remove the load. a register read
alone does not prove that a new conversion has finished. USB admission
requires measured VSYS minus both qualified margins to remain at least
8.7 V; reported samples older than 250 ms fail off.

this 8.7 V limit belongs to the USB5 path. it does not replace the Mu
converter's 10 V minimum for its full 5.5 A operating screen. all rail
reservations must also fit the whole-system source budget. the USB profile
allows at most 5.5 A steady admission and 5.6 A during qualified startup,
with one branch enabled per new measured conversion. source changes,
transfer, stale measurements or loss of the host lease remove admission.

## system 5 V startup and brownout

U6 starts from MU_HOST_ACTIVE. its 880 µF / 1.9 ms startup screen is a
rail-rise transient, so high USB5 admission requires actual SYS5 power-good.
U2412 combines U6 PG and U771's downstream VBUS supervisor onto the existing
INTERNAL_USB_VBUS_VALID boundary. left U2413 combines that signal with raw
INA overcurrent status and drives both the USB fault-latch preset and the
direct converter-enable veto. unused expander P1.6 observes the same signal.

cold start leaves a latched USB inhibit. a brief SYS5 brownout also latches
USB off even with a retained host lease. recovery requires an explicit
fault-clear request after PG, actual VBUS and a fresh quiet-current sample
are valid. no timer stands in for rail readiness. loss during clear remains
blocked by the direct hardware veto and failed readback requests EC reset.
other SYS5 branch startup stays inside the converter's separate complete
bank/inrush envelope and auxiliary source reservation.

## actual load inventory and qualification ceilings

| branch | connected load basis | required upper bound |
| --- | --- | ---: |
| left SYS_3V3 | USB7206C, TPS62823 hub core supply, Y1700 ASDMB, two HD3SS6126 switches, TUSB1142, TPS25810 auxiliary supplies and local logic | 2.000 A |
| right SYS_3V3 | TPS22975, PCA9306, SN74LVC1G17, Type-C auxiliary supply and control logic | 0.025 A |
| MCU_3V3 per I/O board | one TPS25751 plus local control/monitor logic | 0.100 A each |
| right SYS_5V | TPS22948-limited HDMI 5 V and its quiescent current | 0.351 A |
| right PCIE_3V3 | RTL8111H GbE endpoint and its regulators | 0.400 A |
| endpoint startup allowance | conservatively assign the entire shared startup allowance to the right cut | 0.400 A |
| right USB_PORT_5V | J11 and J12 VBUS, VCONN, bleeds and full common allowance | 2.015 A |
| signed DC signals per seam | USB2, HCSL reference clock, DDC/HPD and control/pull currents | 0.100 A each |
| selected main input | one selected PD/AUX input path | 5.000 A aggregate |
| raw AON inputs | all simultaneously active raw-port AON feeds | 2.000 A aggregate |

these are conservative loom bounds, not permission to draw 7 A from a
5 A USB source. the target reserves 6.5 W for raw standby before allocating
charger current. its ISL9241 command and available-power calculations also
include shunt, gain and offset envelopes. the charger-current, USB power,
VSYS measurement, harness, inrush and complete auxiliary-load qualification
conditions must all hold before a live profile is released. their hardware
qualification flags remain off.

the hub's current table gives typical 25 °C values, not guaranteed maxima.
its actual enabled inventory is three SuperSpeedPlus and three USB2
port paths, including the upstream link. that table gives about 950 mA
at VCORE and 96.5 mA at VDD33. at 80% core conversion and 3.0 V input,
this is about 552 mA from SYS_3V3. TUSB1142 lists 275 mW typical active
Gen 2 power, about 92 mA at 3.0 V. both HD3SS6126 devices add 6 mA maximum;
Y1700's 3.3 V current table specifies up to 15 mA at 25 °C with no output
load. these facts support the chosen 2 A test ceiling, but they do not turn
it into an all-temperature manufacturer guarantee. startup and actual
maximum traffic must be measured against the ceiling.

right HDMI has passive TMDS coupling/termination, no active TMDS redriver.
its external 5 V is independently limited by TPS22948. DDC/HPD pull currents
and local logic are included in the 25 mA SYS3 allowance. AC-coupled TMDS,
USB SuperSpeed and PCIe data pairs add no steady DC supply current through
the signal conductors. USB2, HCSL and control paths remain in the signed
signal allowance. validate that allowance using active traffic and static
states, including back-powered peripherals.

the corrected U7 divider gives a 3.259000 V DC floor. at 2 A, 93 mΩ loom,
10 mΩ board copper, 10 mV ground difference and 20 mV ripple, the left
SYS3 floor is 3.023000 V. verify it at the actual device pins. endpoint
limits remain 5 A total, 5.4 A startup, with 3.5 A NVMe, 1.0 A Wi-Fi and
0.4 A GbE branches. use the current WAGO rail map and installed wire paths.

## signed return proof

let positive `gL` and `gR` mean current injected into the left and right
local grounds. sum the positive incoming rail currents, subtract outgoing
positive rail currents, and retain signed DC signal current:

```
gL = I_VSYS + I_SYS3L + I_MCU3L − I_USB5LR
     − I_PD1_SELECTED − I_AUX_RAW − I_PD1_RAW_AON + dL
gR = I_USB5LR + I_SYS5R + I_SYS3R + I_PCIE3R + I_MCU3R
     − I_PD2_SELECTED − I_PD2_RAW_AON + dR
```

only one main source is selected; raw AON feeds may coexist. their combined
limits are used once in the combined cut. `I_USB5LR` cancels in `gL+gR`.
for the passive three-node return network, every edge is bounded by
`max(|gL|, |gR|, |gL+gR|)`. the complete worst-case intervals are:

| cut | most positive | largest negative magnitude |
| --- | ---: | ---: |
| left | 6.389980 A | 9.115 A |
| right | 3.391 A | 7.100 A |
| left plus right | 7.765980 A | 7.200 A |

the largest edge is 9.115 A, below the 10 A continuous design bound.
this includes the entire endpoint startup allowance. resistance ratios
can move the load between return paths, so no equal split is assumed.
install two independent Alpha 1230 braids per seam, each complete bond
at most 1 mΩ including joints and board connections. the model covers
one open braid; it does not cover losing both.

with one braid remaining and at least 0.12 mΩ in the return wire, the
WAGO terminal-current bound is:

```
I_terminal <= I_cut / (1 + R_wire_min / R_braid_max)
           <= 9.115 A / (1 + 0.12 mΩ / 1 mΩ)
           <= 8.138393 A
```

at the full 10 A design bound this becomes 8.928571 A, still below 9 A.
no credit is taken for the signal cable or equal sharing. measure the
cold minimum return-wire resistance and the hot/aged maximum resistance
of each complete braid separately before using this result.

a remaining 1 mΩ braid uses at most 9.115 mV at the calculated worst
cut, leaving only 0.885 mV for additional plane gradients within the
10 mV seam allowance. at 10 A there is no unused voltage allowance.
check the difference between the actual ground lands under load; do not
substitute a cable-only resistance measurement. the FFC guard and shell
constraints remain separate in
[signal_interconnect_contract.py](../../gen/signal_interconnect_contract.py).

externally imposed ground-loop current, ESD and electrical faults are
outside this normal-load sum. the current pack fuse is the 5 A Schurter
HCF, not an instantaneous 5 A clamp. use the actual source fault current,
fuse clearing-time and total-energy bounds, capacitor discharge, background
load and temperature when checking braid and small-conductor pulses.
that fault-energy and ESD qualification remains open.
