# I/O power looms and ground bounds

power uses two short Micro-Fit looms and one direct left-to-right XT30 loom.
all positive supply rails are removed from the 41/51-contact signal cables.
`gen/usb_power_contract.py` is the pin and assembly contract.
`gen/calculate_io_power.py` reproduces the current and voltage screen below.
these are routing and qualification limits. the assembled harnesses and
operating profiles have not been qualified.

| loom | board headers | mating cable parts | construction |
| --- | --- | --- | --- |
| center to left | J2430/J2431, Molex 43045-1212 | 43025-1200, 43030-0038 tin contacts | 12 contacts, Alpha 3253 18 AWG, 90..100 mm |
| center to right | J2432/J2433, Molex 43045-1012 | 43025-1000, 43030-0038 tin contacts | 10 contacts, Alpha 3253 18 AWG, 90..100 mm |
| left to right USB5 | J2434/J2435, AMASS XT30PW-F30.G.Y | two XT30U-M.G.Y gold plugs | two Alpha 5857 18 AWG wires, 400..420 mm |

lengths include manufacturing tolerance, measured between wire termination
ends. Micro-Fit uses one signal/power conductor per numbered position,
straight number to number. USB5 uses pad 1 for GND and pad 2 for positive
USB_PORT_5V. verify continuity, polarity and isolation before power.
raw BMS power remains on its separate Mega-Fit connector.

the vertical headers avoid the facing cable-housing conflict at the narrow
coplanar seams. the exact 10/12-contact parts have a 17.64 mm mated body;
this excludes the wire loop. Alpha 3253 requires a 17.78 mm minimum bend
radius, so even a single 90-degree turn needs more height. the complete
90..100 mm loop must be checked at the installed board poses before the
case height is frozen. both harnesses retain their original electrical map.

Micro-Fit contact screening uses the 12-circuit / 18 AWG / 5.5 A row in
[Molex PS-43045 revision R](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/430/43045/PS-43045-001.pdf).
Alpha 3253 is 7/26 tinned copper, 1.778 mm maximum OD, with an 80 °C wire
limit and 17.78 mm minimum bend radius. each hot/aged termination must be
at most 45 mΩ and wire at most 30 mΩ/m. a 100 mm positive leg is therefore
at most 93 mΩ. every seam return must measure at least 2 mΩ at the cold
qualification corner. with at most 10 mV between the actual ground lands,
any one return is at most 5 A, regardless of sharing. those resistance and
temperature conditions are receiving/assembly requirements.

[AMASS 2025V0](https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf)
specifies 20 A at up to 85 K rise, 1.2 mΩ contact resistance, 100 mating
cycles and −20..120 °C. our assembled 8 A return-current bound still
requires thermal testing. the direct loom must stay at or below 80 °C,
including both solder joints and connector bodies. each mated and soldered
termination must remain at or below 5 mΩ after assembly, temperature and
life tests. the datasheet's contact value does not establish that assembled
hot/aged bound.

use [Alpha 5857](https://www.alphawire.com/products/wire/hook-up-wire/premium/5857),
red 5857 RD005 and black 5857 BK005: 18 AWG 19/30 silver-plated copper,
PTFE, UL1213 at 105 °C. maximum OD is 1.8796 mm and minimum bend radius is
18.796 mm. its published DCR is nominal; the assembled 30 mΩ/m hot limit
still needs checking. one positive wire and one full-current return remove
the parallel-positive and minimum-return-resistance conditions of the old
8-contact direct loom.

the local AMASS footprint follows the current F30 drawing: 5.00 mm power
pitch, 11.00 mm retention pitch, with retention pins 5.00 mm forward of the
power row. finished power holes are 1.85 ±0.05 mm and retention holes
1.15 ±0.05 mm. retention lands remain isolated and require a receiving
isolation check. the mated envelope is at most 23.10 × 13.60 mm, with a
conservative 5.75 mm above-board height from the independent total/tail
dimensions. reserve sleeve thickness, wire exit and bend space separately.
strain-relieve the wires independently. mate only while unpowered.

use 420 mm as the nominal direct-loom cut target. the rounded wire-exit
path is 370.47 mm for ground and 380.47 mm for USB5, using an 18.796 mm
bend radius between the reviewed front-left and rear-right positions.
reserve up to 12 mm inside the two solder/sleeve terminations. at 400 mm,
that leaves 17.53 mm and 7.53 mm for dressing and height detours; 420 mm
adds 20 mm. check the real component-height corridor before assembly.
a flat plan view does not prove the enclosure fit.

the vertical Micro-Fit body is 17.64 mm high, but Alpha 3253 wire has a
17.78 mm minimum bend radius. at the current header poses, a 90..100 mm
individual-wire model reaches about 54.4 mm above the board, including
wire radius and an 8 mm maximum hidden crimp allowance. reserve about
55 mm before any enclosure claim. verify numbered-wire bundle crossings,
actual crimp length and latch access in the assembled loom; the single-wire
curve calculation does not establish bundle clearance.


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

true center VSYS must remain at least 8.7 V during this high-power state.
BQ25798 reports 1 mV resolution, but its datasheet does not guarantee
absolute ADC accuracy. there is no existing STM32 VSYS channel: PA6 senses
AUX input, PA7 skin temperature, and PB0 Mu temperature. AUX voltage is
upstream of the charger and cannot establish this VSYS floor.
`DUCKTOP2_VSYS_SENSE_QUALIFIED`, `DUCKTOP2_VSYS_MAX_OVERESTIMATE_MV` and
`DUCKTOP2_VSYS_MAX_FALL_MV` remain zero. USB admission requires qualification
and tests measured VSYS minus both margins against 8.7 V. the fall margin
must cover the full observation age and shutoff latency. readings older
than 250 ms fail off. TI confirms the absence of a guaranteed absolute ADC
accuracy in its [BQ25798 support response](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1402524/bq25798-premature-vsys-ovp).

## system 5 V startup and brownout

U6 starts from MU_HOST_ACTIVE. its 900 µF / 1.9 ms startup screen is a
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
| selected main input | one selected PD/AUX input path | 3.500 A aggregate |
| raw AON inputs | all simultaneously active raw-port AON feeds | 2.000 A aggregate |

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

the corrected U7 divider gives a 3.254211 V DC floor. at 2 A, 93 mΩ loom,
10 mΩ board copper, 10 mV ground difference and 20 mV ripple, the left
SYS3 floor is 3.018211 V. verify it at the actual device pins. endpoint
limits remain 5 A total, 5.4 A startup, with 3.5 A NVMe, 1.0 A Wi-Fi and
0.4 A GbE branches. pair right power pin 5 physically with GND pin 10.

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
| left | 6.389980 A | 7.615 A |
| right | 3.391 A | 5.600 A |
| left plus right | 7.765980 A | 5.700 A |

the largest edge therefore remains below the 8 A continuous design bound.
this includes the entire endpoint startup allowance. resistance ratios
can move all of an edge's current into one remaining path; no equal split
is assumed. two independently attached Alpha 1230 braids cross each seam,
each complete bond at most 1 mΩ. either alone limits its ground difference
to 8 mV at 8 A, leaving 2 mV for local plane gradients in the 10 mV power
loom allowance. the FFC guard and shell constraints are separate in
`gen/signal_interconnect_contract.py`.

externally imposed ground-loop current, ESD and electrical faults are
outside this normal-load sum. measure these separately and preserve the
specified braid/FFC impedance bounds. a 3 A fuse does not limit an
instantaneous fault to 3 A. the current
[Littelfuse 297 datasheet, revised 2024-09-27](https://www.littelfuse.com/assetdocs/littelfuse_datasheet_297_mini32v.pdf?assetguid=42c9dd21-a88e-4328-8e67-2f832444faf1)
lists 20 A²s typical melting I²t for the 3 A fuse, before arcing. it is not
a guaranteed total clearing value. its opening-time maxima are 600 s at
135%, 5 s at 200%, 0.5 s at 350%, and 0.1 s at 600% rated current.
use the actual source fault current, total clearing energy, background
load and temperature when checking braid and small-conductor fault pulses.
that fault-energy and ESD qualification remains open.
