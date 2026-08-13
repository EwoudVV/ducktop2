Name: Ducktop2

I'm designing: a full custom x86 laptop/cyberdeck on a single carrier PCB. it uses a LattePanda Mu (Intel N305, 16GB RAM, 64GB eMMC). I wanted to make a cyberdeck, but all the ones ive seen are really chunky. I wanted to make something thats actually portable and able to be daily driven. it has 2 embedded microcontrollers, 1 for controlling stuff like the keyboard matrix, fan speed, power management, etc and the other for exposed gpio, like an embedded arduino. it has an internal usb connection for programming. The main part of this project is making the pcb, its what im working on now.

the idea is one PCB replacing the mess of separate things and cables everywhere from ducktop1. it now has a 16" 2560x1600 120Hz display running direct eDP off the Mu module, instead of an hdmi cable. mechanical keyboard with Cherry MX ULP switches on a custom daughterboard. 3S battery with proper pack protection and a fuel gauge. it will go in a custom enclosure, cnced aluminum.

Inspo / reference:
- ducktop1: pi 500 plus and a 16" portable monitor, with a custom pcb for charging the batteries and supplying power to the monitor and pi from them.
- latte panda mu reference carrier: https://github.com/LattePandaTeam/LattePanda-Mu
- all kinds of cyberdecks people are making

Past projects:
- ducktop1: pi 500, 16" 2560x1600 panel at 90Hz, worked but the internal cabling was a mess. hdmi and usb-c cables had to run outside the case. power system, display were all separate stuff and it was messy (pcbway funded)
- a drawing machine (hc highway funded)
- rc tank (hc hackpac funded)

Why this is worth more than $200:
this is a laptop. not a breakout board or an arduino shield, an actual laptop with an x86 processor, 120Hz display, mechanical keyboard, multi-cell battery pack, and three custom PCBs. the mainboard alone is 358x185mm with over 1000 parts, most of them in fine-pitch packages (QFN, WCSP, 0402). nextpcb is giving me $300 already but the real total is way past that. i have some stuff from ducktop1 / early prototyping already, but the carrier board components, the Mu module, the ssd, keycaps, enclosure, and all the pcba work still needs to happen.

Rough BOM (what i still need, i already have the screen, keyboard pcb, ULP switches, and 3S cells):

LattePanda Mu N305 compute module $190
Main PCB fab (358x185mm 4-layer ENIG at nextpcb) $180
Main PCB assembly + component sourcing $250
Radio daughterboard PCB fab + assembly $50
Cherry MX ULP keycaps x65 $45
1TB NVMe SSD 2280 $60
WiFi 6E E-key card $18
Power management ICs (USB-C PD controllers, battery charger, fuel gauge, 3S protector, pack protector, buck-boost, bucks, eFuses, ideal diodes, supervisors, load switches) $95
MCUs and compute ICs (STM32F407, RP2350A, flash) $15
USB hub and interface ICs (USB7206C 6-port gen2 hub, RTL8111H gigabit ethernet, USB muxes, level translators, ESD diodes, i2c expanders) $55
Audio subsystem (class-D amp, codec, mic preamp, LDO) $15
Radio daughterboard components (DRA818V + DRA818U modules, u-blox MAX-M10S GNSS, Mini-Circuits ULP filters, PCM2900C codec) $70
Connectors and hardware (DDR4 SO-DIMM socket, M.2 sockets, SMT standoffs, ethernet jack, DF40 mezzanine, FFC connectors) $35
All passive components (~950+ resistors, capacitors, inductors, ferrites, crystals, diodes, fuses, buttons) $40
Cooling (blower fan, heatpipe, coldplate) $35
CNC aluminum enclosure $70

Total: $1,223
