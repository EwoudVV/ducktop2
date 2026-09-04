# ducktop2

i'm making a custom x86 laptop around a LattePanda Mu. i wanted a cyberdeck
with exposed hardware and room to experiment, but something i could actually
carry around and use as a normal laptop too.

ducktop1 used a Pi 500+ and a 16-inch portable monitor. it worked, but the
cabling was a mess. the HDMI and USB-C cables had to run outside the case.
this version uses direct eDP for the display and custom boards for the power,
ports, and laptop controls.

it has a 16-inch 2560x1600 120 Hz display target, a Cherry MX ULP mechanical
keyboard, NVMe, a large trackpad, and a 3S battery. there's an STM32 for the
laptop controls and a separate RP2350 for exposed GPIO. the optional radio
board adds VHF/UHF, GNSS, and its own audio path.

the main carrier is now split into a center board, left and right I/O, and a
small BMS. the keyboard and radio are separate boards too. i'm doing the PCB
routing by hand. the BMS is routed and under review, and the other main boards
still need routing.

## why it needs more than a small-project budget

the expensive work is spread across fine-pitch parts, multilayer PCBs,
assembly, the compute module, cooling, cables, and the enclosure. the split
also needs proper connectors and cables between the boards.

i already have work and parts from ducktop1 and the earlier prototype stages.
the keyboard has a rev A production package, and the replacement panel has
been tested at full resolution and refresh rate on the Intehill controller.
the final Mu display harness and full laptop assembly still need testing.

i still need current parts and assembly quotes for the split boards before
putting a total in the budget. [parts and cost](bom-and-cost.md)

## previous projects and references

- [ducktop1](ducktop1.md), supported by PCBWay
- [drawing machine](https://github.com/EwoudVV/drawbot), from Hack Club Highway
- [RC tank](https://github.com/EwoudVV/rc-tank), from Hack Club Hackpac
- [LattePanda Mu reference hardware](https://github.com/LattePandaTeam/LattePanda-Mu)

[current progress](design-status.md) and [next steps](design-status.md#work-order) have the
detailed state. this pitch was refreshed on 4 september 2026.
