# Ducktop2 — Funding Application Pitch

Application text for Ducktop2. The full cost breakdown behind the rough BOM
below lives in [`docs/bom-and-cost.md`](../bom-and-cost.md).

**Name: Ducktop2**

## Project

I'm designing a full custom x86 laptop/cyberdeck on a single carrier PCB. It
uses a LattePanda Mu (Intel N305, 16GB RAM, 64GB eMMC). I wanted to make a
cyberdeck, but all the ones I've seen are really chunky. I wanted to make
something that's actually portable and able to be daily driven.

It has 2 embedded microcontrollers:

- one for controlling stuff like the keyboard matrix, fan speed, power
  management, etc; and
- one for exposed GPIO, like an embedded Arduino, with an internal USB
  connection for programming.

The main part of this project is making the PCB — that's what I'm working on
now.

The idea is one PCB replacing the mess of separate things and cables everywhere
from Ducktop1. It now has:

- a 16" 2560x1600 120 Hz display running direct eDP off the Mu module, instead
  of an HDMI cable;
- a mechanical keyboard with Cherry MX ULP switches on a custom daughterboard;
- a 3S battery with proper pack protection and a fuel gauge.

It will go in a custom enclosure, CNC'd aluminum.

## Inspiration and Reference

- **Ducktop1:** Pi 500 Plus and a 16" portable monitor, with a custom PCB for
  charging the batteries and supplying power to the monitor and Pi from them.
- **LattePanda Mu reference carrier:**
  https://github.com/LattePandaTeam/LattePanda-Mu
- All kinds of cyberdecks people are making.

## Past Projects

- **Ducktop1:** Pi 500, 16" 2560x1600 panel at 90 Hz. Worked, but the internal
  cabling was a mess — HDMI and USB-C cables had to run outside the case. Power
  system and display were all separate stuff and it was messy (PCBWay funded).
- **A drawing machine** (HC Highway funded): https://github.com/EwoudVV/drawbot
- **RC tank** (HC Hackpac funded): https://github.com/EwoudVV/rc-tank

## Why This Is Worth More Than $200

This is a laptop. Not a breakout board or an Arduino shield — an actual laptop
with an x86 processor, 120 Hz display, mechanical keyboard, multi-cell battery
pack, and three custom PCBs. The mainboard alone is 358 x 185 mm with over 1,000
parts, most of them in fine-pitch packages (QFN, WCSP, 0402).

NextPCB is giving me $300 already, but the real total is way past that. I have
some stuff from Ducktop1 / early prototyping already, but the carrier board
components, the Mu module, the SSD, keycaps, enclosure, and all the PCBA work
still needs to happen.

## Rough BOM

| Item | Cost |
| --- | --- |
| LattePanda Mu N305 compute module | $300 |
| Main PCB fab (358 x 185 mm, NextPCB) | $200 |
| Main PCB assembly + component sourcing | $1,500 |
| Radio daughterboard PCB fab + assembly + component sourcing | $600 |
| Cherry MX ULP keycaps x65 | $50 |
| 256 GB NVMe SSD 2280 | $50 |
| Wi-Fi 6E E-key card | $40 |
| Cooling (blower fan, heatpipe, coldplate) | $50 |
| CNC aluminum enclosure | $300 |
| 5000 mAh battery (100 x 60 x 6) | $50 |
| eDP panel (Samsung ATNA60HU01-0) | $400 |
| Framework 13 hinges | $20 |
| **Total** | **~$3,560** |

See [`docs/bom-and-cost.md`](../bom-and-cost.md) for the full line-item
breakdown of the main PCB components and assembly.