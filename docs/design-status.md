# Current Design Status

Updated: 2026-07-21

## Schematic

The active motherboard hierarchy contains 14 generated child sheets, 1,176
components, 1,378 nets, and 4,565 connected pins. The retired Intehill
controller, VL822 hub, carrier-eDP, and USB-C video sheets are not part of the
root design.

Current automated results:

| Check | Result |
| --- | --- |
| KiCad ERC | 0 errors; 13 library-copy and 14 intentional grounded-pin warnings |
| Independent netlist closure | 1,571 pass, 0 fail |
| Bounded electrical calculations | 123 pass, 0 fail |
| Pin review | 2,642 pass, 0 fail, 0 review |
| Schematic-to-PCB reference/pad-net parity | 1,173 of 1,173, no drift |
| Host firmware policy tests | Pass |

The remaining pin-review rows are broad Mu, M.2, MCU, spare, NC, and ground-pin
classifications that require human context; they are not detected electrical
failures. The ERC warning allowlist is tied to exact references and pins. It
covers 13 flattened KiCad symbol copies and 14 required GPIO/strap ties that
KiCad sees sharing the global ground power flag.

The latest closure summary is in
[`verification/SCHEMATIC_CLOSURE_2026-07-20.md`](../verification/SCHEMATIC_CLOSURE_2026-07-20.md).

## PCB

The mainboard is six layers and currently measures 358 x 185 mm, including the
fin-stack notch. It contains 1,173 footprints and 14 zones. The schematic and PCB
agree on references, footprints, pad nets, BOM flags, and DNP flags.

Routing has not started. The current 3D renders show placement only.

Routing is now gated by the coupling-capacitor placement fix completed on
2026-07-21. All high-speed AC coupling caps (PCIe, USB3, HDMI) were relocated
from 12-90 mm away from their endpoints. The move affected 23 0402 capacitors
across the NVMe, WiFi, USB3 right PD, USB3 left PD, hub-side, and Mu-side
paths. An independent pre-order design review
([`verification/DESIGN_REVIEW_2026-07-21.md`](../verification/DESIGN_REVIEW_2026-07-21.md))
confirmed the schematic is clean and issued a CONDITIONAL PASS.

**Coupling-cap placement note:** The independent review flagged 8 caps as
12-33 mm from their endpoints, measured from component *centers*. A corrected
analysis ([`verification/COUPLING_CAP_ANALYSIS_2026-07-21.md`](../verification/COUPLING_CAP_ANALYSIS_2026-07-21.md))
shows actual distances to the nearest signal pins are ~11 mm for Mu USB3 TX
caps and potentially 4-14 mm for NVMe caps depending on pin assignment.
These values are acceptable for USB 3.0 / PCIe Gen3 and can be revisited
on the routed PCB.

The current DRC findings are placement-stage items:

- 499 unrouted connections
- 424 silkscreen, edge-clearance, or text-size warnings (14 new reference-field
  overlaps on the right USB-C PD caps from the relocation)
- no current schematic-to-PCB parity findings
- no new copper clearance or shorting violations

The removable radio/GNSS/audio daughterboard has 126 placed footprints. Its
schematic passes ERC with no warnings, and its mainboard interface defaults off
so the laptop, system audio, microphone, charging, and boot path do not depend
on the daughterboard being installed.

## Mechanical

Confirmed plan-view measurements:

- panel: 352 x 227 mm
- provisional lid/base: 358 x 248 mm
- three cells: 100 x 60 mm each
- keyboard PCB: 273.5 x 80.0 mm
- trackpad: 140 x 105 mm
- speakers: 38 x 18 mm each

The battery, trackpad, cooling, and hinge stack still need a physical Z-height
model. The panel and trackpad dimensions changed after the earliest floorplans,
so the final enclosure and board-support web cannot be frozen from the old JSON
alone.

## Firmware

The repository contains deterministic C11 policy cores and host tests for the
STM32 EC and RP2350 maker controller. It does not yet contain target startup,
USB descriptors, board drivers, vendor SDK integration, final binaries, or HIL
results. The hardware defaults were designed so reset removes source-path and
load enables before firmware runs.

## Work in Progress

The next electrical/layout sequence is:

1. ✅ High-speed coupling-capacitor placement corrected (2026-07-21).
2. Freeze the actual six-layer stackup and controlled-impedance geometries.
3. Finish the manufacturer part numbers and assembly constraints in the BOM.
4. Route power and high-speed interfaces, then low-speed control and GPIO.
5. Refill zones, clean silkscreen, run full DRC, and review every exception.
6. Complete the eDP harness, battery-pack, thermal, RF, and enclosure measurements.
7. Build target firmware and run the hardware-in-the-loop bring-up matrix.

The repository is useful for review now, but the mainboard files are not an
ordering package.
