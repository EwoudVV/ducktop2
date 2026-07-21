# Ducktop2 Motherboard Schematic Closure - 2026-07-20

## Current Result

All confirmed motherboard and removable radio-board schematic defects found in
the July 17-20 reviews are fixed in the generated source. The current checks do
not contain an active P0 or P1 electrical finding.

This is a statement about the schematic and its explicit firmware contracts.
Physical cable measurements, target-hardware firmware, RF/thermal testing, and
first-article behavior remain separate work because they cannot be proved from
a netlist.

## Changes Closed In This Pass

- All five external USB-C ports carry data. J21 and J11 are the rear PD/data
  ports; J22, J23, and J12 are protected source/data ports that safely ignore a
  connected charger.
- The two TPS25751A policies advertise 5 V at 900 mA as sources and request up
  to 15 V at 3 A as sinks. Their GPIO state is part of the EC host-data policy.
- The fixed PCM2900C system codec is on internal hub port 1. The removable
  radio codec is on port 2 and is separately switched.
- The mainboard works with the radio/GNSS/audio daughterboard absent. Its power,
  USB, UART, I2C, PTT, and control paths default off or isolated.
- Duplicate daughterboard-side pull-ups were removed so an unpowered radio
  board cannot be weakly powered through signal nets.
- MAX-M10S V_BCKP is now open because the board has no independent backup
  source. The main 3.3 V rail remains the GNSS supply.
- The EC now converts BQ34Z100 remaining-time values from minutes to seconds and
  handles the 0xffff unavailable sentinel before publishing OLED telemetry.
- AUX input enable requires both qualified voltage/current and verified charger
  IINDPM programming.
- The mainboard contract explicitly checks both Mu-to-J21 USB3 TX coupling
  capacitors, including the cross-sheet path that was easy to overlook in a
  visual review.

## Fresh Evidence

| Check | Result |
| --- | --- |
| KiCad ERC | 0 errors; 13 library-copy and 14 intentional grounded-pin warnings |
| Generated schematic self-check | Pass |
| Schematic design contracts | Pass |
| Independent exported-netlist closure | 1,571 pass, 0 fail |
| Bounded electrical calculations | 123 pass, 0 fail |
| Pin review | 2,642 pass, 0 fail, 0 review |
| Mainboard schematic/PCB parity | 1,173/1,173 refs; zero footprint, pad-net, or attribute drift |
| Radio daughterboard ERC | 0 errors, 0 warnings |
| Radio daughterboard contracts | Pass |
| Firmware host tests | Pass |

The exported motherboard hierarchy contains 1,176 components, 1,378 nets, and
4,565 connected pins across 14 child sheets.

The 27 ERC warnings are exact-reference allowlisted checks, not a broad waiver.
Thirteen report flattened copies of KiCad library symbols. Fourteen report
required bidirectional GPIO/strap pins tied to ground on nets that also contain
the global ground power flag. Any new warning type, reference, pin, or count is
treated as a regression.

The current main PCB has 499 unrouted connections and 410 placement text/silk
findings. It has no schematic-to-PCB parity finding and no copper-clearance,
hole-clearance, or solder-mask violation in the current contract report. The
radio daughterboard has 385 unrouted connections and 96 classified placement
warnings.

Mainboard SHA-256 during the final parity run:
`b01b917665cb4631a3df28e41a38ae34bb3a555ba46d14226d542ab60db59f4b`

Radio daughterboard SHA-256 during its final contract run:
`6a4505fbbe5cbb6eeab0b18e504edb4732f8f6337019633ba2a68d1b6fedcb61`

## Facts Still Needed From Physical Hardware

- Exact panel-side and Mu-side eDP connector orientation, contact mapping,
  cable length, and a continuity-checked harness drawing.
- Exact battery cell identity, chemistry, wire gauge, connector pin order, and
  cell-board thermal cutoff behavior.
- Exact speaker impedance/power rating and the final microphone acoustic port.
- Final SSD1306 and trackpad connector orientation in the enclosure.
- A target STM32 hardware adapter, hardware-in-the-loop results, and the final
  BQ34Z100 data-flash image for the selected cells.

Those items stay visible because guessing them would weaken the schematic rather
than finish it.
