# Ducktop2

Ducktop2 is my second DIY laptop: a 16-inch x86 machine built around the
LattePanda Mu. I want the flexibility and exposed hardware of a cyberdeck,
without giving up the shape, portability, or everyday usability of a normal
laptop.

My first version used a Raspberry Pi 500+ and a complete portable monitor. It
worked, but HDMI and USB-C cables had to loop around the outside of the case.
Ducktop2 replaces that stack with one purpose-built motherboard, a direct eDP
display connection, and a separate low-profile mechanical keyboard.

![Top view of the Ducktop2 motherboard at placement stage](docs/images/ducktop2-pcb-top.png)

> **Current state, July 2026:** the generated motherboard schematic passes ERC
> and the project checks. The six-layer PCB has its outline and 1,173 synchronized
> footprints. High-speed placement is complete (23 AC coupling caps relocated on
> 2026-07-21) and the design issued a CONDITIONAL PASS at independent pre-route
> review. Routing has not started. The board images in this repository are
> placement-stage renders.

## What I Am Building

The target is a self-contained 16-inch Linux laptop with a 2560x1600 120 Hz
display, an Intel N305 compute module, real NVMe storage, a large trackpad, and
a Cherry MX Ultra Low Profile keyboard. It should close and carry like a normal
laptop, with no rear bump and no permanent cables hanging from the sides.

The extra cyberdeck hardware is built into the same machine:

- an independent RP2350 maker controller with protected GPIO;
- dual-band VHF/UHF radio hardware and GNSS;
- two small status OLEDs that remain under embedded-controller control;
- multiple USB-C ports, HDMI, Gigabit Ethernet, and M.2 expansion; and
- a protected three-cell battery system with several charging inputs.

The laptop EC and the maker controller are deliberately separate. Experiments
on the exposed GPIO should not be able to take over keyboard scanning, cooling,
charging, or system power sequencing.

## Design Goals

- **No external display wiring.** The internal panel connects directly to the
  LattePanda Mu's onboard eDP connector.
- **A normal laptop outline.** The measured panel is 352 x 227 mm and the
  provisional base is 358 x 248 mm.
- **Useful x86 performance.** The N305 module provides Linux graphics support,
  PCIe storage, and substantially more headroom than Ducktop1's Raspberry Pi.
- **Thin mechanical parts.** The keyboard uses Cherry MX Ultra Low Profile
  switches, and the cooling system uses a flat cold plate, heat pipe, fin stack,
  and blower.
- **Repairable major modules.** The Mu, NVMe drive, Wi-Fi card, display,
  keyboard, trackpad, speakers, battery cells, and cooling hardware remain
  replaceable.
- **Visible engineering evidence.** Generated schematics, calculations,
  verification summaries, renders, and the keyboard production package live in
  this repository.

## System Architecture

![Ducktop2 system architecture](docs/images/ducktop2-architecture.svg)

| Area | Current design |
| --- | --- |
| Compute | LattePanda Mu with Intel N305 processor, LPDDR5, and 64 GB eMMC |
| Internal display | AUO B160QAN03.K, 2560x1600 at 120 Hz through the Mu's onboard 40-pin eDP output |
| Storage | PCIe Gen3 x4 M.2 M-key 2280 NVMe plus onboard eMMC fallback |
| Networking | M.2 E-key 2230 Wi-Fi/Bluetooth and RTL8111H Gigabit Ethernet |
| User I/O | Five USB-C data ports, HDMI-A, Ethernet, trackpad, keyboard, and two OLEDs |
| Battery | Three 3.7 V pouch cells in series with cell-level and whole-pack protection |
| Charging | One rear USB-C PD data/charging port per side plus a protected variable-voltage AUX/DC input |
| Laptop controller | STM32F407 EC for power policy, keyboard, cooling, controls, radios, and status displays |
| Maker controller | Chip-down RP2350 exposed as an independent USB device with protected power and GPIO |
| Audio | Internal USB audio, stereo amplifier and speakers, digital microphone, and a separate radio audio path |
| Radio/navigation | DRA818V, DRA818U, external filtering and switching, and u-blox MAX-M10S GNSS |

## Power and Battery

Ducktop2 uses a 3S lithium-ion pack. The battery path includes a replaceable
10 A fuse, autonomous cell overvoltage/undervoltage/overcurrent protection,
back-to-back MOSFET disconnects, a second whole-pack protection layer, a
BQ25798 buck-boost charger and NVDC power path, and a BQ34Z100-G1 fuel gauge.

The two rear TPS25751A ports negotiate up to 15 V from USB-C PD sources while
also carrying USB data. The other three USB-C ports are protected host/data
ports and safely ignore a connected charger. A separate AUX/DC
input accepts a wider range of ordinary DC or occasional solar sources through
its own qualification and protection path. A regulated 12 V rail supplies the
LattePanda Mu; local converters generate the system 5 V and 3.3 V rails.

The small protection boards attached to the individual cells are kept for
cell-local thermal cutoff. Electrical pack overvoltage, undervoltage,
overcurrent, and short-circuit protection are handled on the motherboard.

## Display and Mechanical Layout

The replacement AUO panel has been tested through the original Intehill board
at its native 2560x1600 resolution and 120 Hz refresh rate. The finished laptop
will use the Mu's direct eDP connector instead, removing the 114 x 70 mm
portable-monitor controller board from the chassis.

The eDP harness is not considered generic just because both ends have 40 pins.
The connector families, contact orientation, pin mapping, cable length, power
rails, and lane arrangement all need to match before a cable is ordered.

Current measured parts:

| Part | Plan-view size |
| --- | --- |
| Display panel | 352 x 227 mm |
| Provisional base | 358 x 248 mm |
| Mainboard | 358 x 185 mm, including the fin-stack notch |
| Battery cells | 100 x 60 mm each |
| Keyboard PCB | 273.5 x 80.0 mm |
| Trackpad | 140 x 105 mm |
| Speakers | 38 x 18 mm each |

The next mechanical work is a proper Z-height model for the battery band,
trackpad, keyboard, cooling stack, hinges, board supports, and display cable.

## Keyboard

The keyboard is a separate two-layer PCB with 65 Cherry MX Ultra Low Profile
switches in a 5 x 14 matrix. It connects to the embedded controller through a
30-pin FFC, keeping the expensive six-layer motherboard out from underneath
most of the switch area.

The rev-A board has already been sent to production, and Cherry is supplying 70
switch samples. Rev A is intended to validate the switch footprint, matrix,
keycap fit, typing feel, and mechanical stack before optional lighting or other
changes are considered.

![Cherry MX Ultra Low Profile keyboard daughterboard](docs/images/ducktop2-keyboard-pcb.png)

## Current Verification

The active motherboard hierarchy contains 14 generated child sheets. The
checks below are reproducible from the repository rather than being a manually
maintained ERC screenshot.

| Check | Current result |
| --- | --- |
| KiCad ERC | 0 errors; 13 library-copy and 14 intentional grounded-pin warnings |
| Independent netlist closure | 1,571 pass, 0 fail |
| Bounded electrical calculations | 123 pass, 0 fail |
| Pin review | 2,642 pass, 0 fail, 0 review |
| Schematic-to-PCB parity | 1,173 of 1,173 references with no pad-net or metadata drift |
| PCB DRC | 0 copper violations (424 placement-stage silk/clearance warnings) |
| Independent design review | CONDITIONAL PASS (2026-07-21) |
| Host firmware policy tests | Pass |

The project has also been reviewed repeatedly against component datasheets.
An independent pre-route design review (2026-07-21) independently confirmed every
automated result and issued a CONDITIONAL PASS before routing.
The current summaries show what was checked and what remains uncertain; they
are not a substitute for target firmware, signal-integrity work, thermal and RF
measurements, or first-article testing.

## Open and Check the Project

KiCad 10.0.4 is the current reference version. Clone the repository and open
`ducktop2.kicad_pro`:

```sh
git clone https://github.com/EwoudVV/ducktop2.git
cd ducktop2
```

The preferred schematic check performs regenerating and report-writing work in
an isolated copy, then confirms that the live source did not change:

```sh
python3 gen/check_release_candidate.py --stage schematic
```

The host-side firmware policy tests do not require a vendor SDK:

```sh
firmware/tools/run_host_tests.sh
```

See [build and verification](docs/build-and-verify.md) before regenerating the
schematics or comparing the PCB to the netlist.

## Repository Layout

| Path | Contents |
| --- | --- |
| `ducktop2.kicad_*` | Main KiCad project and six-layer motherboard |
| `01_*.kicad_sch` ... `16_*.kicad_sch` | Generated hierarchical sheets |
| `gen/` | Schematic generators, local symbols, and verification tools |
| `ducktop2.pretty/` | Project-local footprints |
| `firmware/` | Host-tested EC and maker-controller policy cores |
| `mechanical/` | Current dimensions, floorplans, and retention contracts |
| `manufacturing/` | Keyboard rev-A production package and release gates |
| `radio_daughterboard/` | Removable VHF/UHF, GNSS, and radio-audio board |
| `software/os-theme/` | Early Fedora KDE theme work |
| `verification/` | Current checks and concise verification evidence |
| `docs/` | Architecture, status, renders, schematic exports, and project background |

## Documentation

- [Hardware architecture](docs/hardware.md)
- [Current design status](docs/design-status.md)
- [Direct-eDP panel and cable work](docs/display-direct-edp.md)
- [Mechanical measurements](docs/mechanical.md)
- [Firmware policy](firmware/README.md)
- [Radio/GNSS daughterboard](radio_daughterboard/README.md)
- [Keyboard production package](manufacturing/keyboard_revA_jlcpcb/README_JLCPCB.md)
- [Verification summary](verification/README.md)
- [Selected schematic export](docs/exports/ducktop2-selected-schematics.pdf)
- [Independent review prompt](docs/review-prompt.md)
- [Ducktop1 background](docs/ducktop1.md)

## Roadmap

1. ✅ High-speed placement — 23 AC coupling caps relocated and design review
   completed (2026-07-21).
2. Freeze the six-layer stackup and controlled-impedance geometries with the
   board manufacturer.
3. Complete manufacturer part numbers and assembly constraints in the BOM.
4. Route power and high-speed interfaces, followed by control, audio, and GPIO.
5. Refill zones, clean silkscreen, run full DRC, and review every exception.
6. Finalize the eDP harness, battery pack, cooling stack, and enclosure model.
7. Assemble the first article, bring up one rail at a time, and record the test
   results before installing the compute module or cells permanently.

## Reviews and Contributions

Technical review is welcome, especially around battery safety, USB-C and PD,
PCIe/eDP/HDMI layout, RF coexistence, embedded-controller defaults, and
manufacturing constraints. Please include the relevant sheet, reference, pin,
datasheet section, and expected failure mode when reporting an electrical
issue. The reusable [review prompt](docs/review-prompt.md) describes the current
architecture and avoids several retired design paths.

This is active prototype hardware. Do not order the mainboard directly from
the files in the repository without doing your own review. Lithium-ion packs,
USB-C power paths, RF transmitters, and high-current rails can damage hardware
or cause injury when assembled or tested incorrectly.

## License

Ducktop2 is released under the [MIT License](LICENSE). The license covers the
files in this repository, but it does not provide component certifications,
radio authorization, electrical-safety approval, or any warranty that a board
built from the current work in progress will function safely.
