# Current Design Status

Updated: 2026-07-19

## Schematic

The active motherboard hierarchy contains 14 generated child sheets and 1,004
components. The retired Intehill-controller, VL822 hub, carrier-eDP, and USB-C
video sheets are not part of the root design.

Current automated results:

| Check | Result |
| --- | --- |
| KiCad ERC | 0 errors; 13 classified `lib_symbol_mismatch` warnings |
| Independent netlist closure | 386 pass, 0 fail |
| Bounded electrical calculations | 129 pass, 0 fail |
| Pin review | 2,410 pass, 0 fail, 351 review |
| Schematic-to-PCB reference/pad-net parity | 997 of 997, no drift |
| Host firmware policy tests | Pass |

The remaining pin-review rows are broad Mu, M.2, MCU, spare, NC, and ground-pin
classifications that require human context; they are not detected electrical
failures. The ERC warnings come from flattened copies of KiCad symbols that use
`extends` and have been checked separately.

The latest closure summary is in
[`verification/SCHEMATIC_CLOSURE_2026-07-19.md`](../verification/SCHEMATIC_CLOSURE_2026-07-19.md).

## PCB

The mainboard is six layers and currently measures 358 x 185 mm, including the
fin-stack notch. It contains 997 footprints and 14 zones. The schematic and PCB
agree on references, footprints, pad nets, BOM flags, and DNP flags.

Routing has not started. The current 3D renders show placement only.

Before routing, the placement needs another pass around the active high-speed
interfaces. Several PCIe and HDMI coupling capacitors are still farther from
their source or endpoint than the LattePanda and component guidance allows.
Those parts will be moved first; existing low-speed MCU placement is not the
reference for high-speed routing.

The current DRC findings are placement-stage items:

- 499 unrouted connections
- 409 silkscreen overlap, over-copper, or edge-clearance warnings
- no current schematic-to-PCB parity findings

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

1. Correct the high-speed endpoint and coupling-capacitor placement.
2. Freeze the actual six-layer stackup and controlled-impedance geometries.
3. Finish the manufacturer part numbers and assembly constraints in the BOM.
4. Route power and high-speed interfaces, then low-speed control and GPIO.
5. Refill zones, clean silkscreen, run full DRC, and review every exception.
6. Complete the eDP harness, battery-pack, thermal, RF, and enclosure measurements.
7. Build target firmware and run the hardware-in-the-loop bring-up matrix.

The repository is useful for review now, but the mainboard files are not an
ordering package.
