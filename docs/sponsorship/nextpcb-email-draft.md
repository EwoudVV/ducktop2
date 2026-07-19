# NextPCB Email Draft

Before sending, add the two Ducktop1 photos listed in
[`attachment-checklist.md`](attachment-checklist.md). The generated assets in
that checklist are ready to attach.

**Subject:** Ducktop2 project package and sponsorship timeline

Dear Viviane,

Thank you for the flexibility on the timeline and for offering to present the
project to LattePanda. I have now prepared a more complete Ducktop2 package
rather than sending unfinished screenshots without context.

The public project repository is:

https://github.com/EwoudVV/ducktop2

I have attached:

- photos of Ducktop1, including the external cable layout that motivated the
  new design;
- a Ducktop2 system block diagram;
- top and perspective renders of the current motherboard placement;
- selected power, Mu carrier, I/O, and controller schematic pages; and
- a render or photo of the separate Cherry MX Ultra Low Profile keyboard PCB.

Ducktop1 was a one-off laptop built from a Raspberry Pi 500+ and a 16-inch
2560x1600 portable monitor. It proved that I liked the form factor, but the
external HDMI and USB-C wiring made it bulky and inconvenient. It does not have
its own GitHub repository, so I included its background and design lessons in
the Ducktop2 repository instead.

Ducktop2 replaces that stack with a six-layer motherboard built around the
LattePanda Mu N305. The design includes a protected three-cell battery and
USB-C PD charging system, direct 2560x1600 120 Hz eDP display connection, NVMe
and M.2 E-key expansion, two native 10 Gbit/s USB-C ports, external HDMI,
Gigabit Ethernet, an STM32 embedded controller, an independent RP2350 maker
controller, a USB trackpad, speakers and microphone, dual OLED status displays,
GNSS, and VHF/UHF radio hardware.

The separate 65-key Cherry MX Ultra Low Profile keyboard PCB has already been
sent to production, and Cherry is providing 70 switch samples. The replacement
AUO display panel has also arrived and has been tested successfully at
2560x1600 and 120 Hz.

The motherboard schematic is generated hierarchically in KiCad 10. It currently
passes ERC and the project electrical/netlist checks, and it has been through
several independent datasheet reviews. The PCB shown in the attached renders is
still at placement stage: I am revising the high-speed component placement
before routing, then I will complete DRC, BOM, stackup, and manufacturing review.
I have labeled the renders accordingly so they are not mistaken for a finished
layout.

My proposed schedule is to finish placement, routing, and the final review over
the next four to six weeks. I would prefer to begin the two-week ordering window
only after I send you the completed manufacturing package and confirm that the
design is ready to submit. After receiving the boards, I can publish an initial
assembly and bring-up update within one month, followed by a fuller project
article after testing.

I understand that the proposed $300 credit would cover PCB fabrication, SMT
assembly, component procurement, and shipping through NextPCB. I am happy to
share progress publicly and to let NextPCB feature the project and its design
process, provided I can approve the final technical text and images. Since I am
15, a parent or guardian can handle any agreement, account, or payment details.

Please let me know whether this package is enough for the application, or if
there is a particular schematic export, BOM format, board render, or photo you
would like me to add. I would also be glad to share the project in the
LattePanda Discord while the layout is being reviewed.

Thank you again for considering Ducktop2.

Best regards,

Ewoud Van Vooren
