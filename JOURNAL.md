---
title: "Ducktop2"
author: "duck"
description: "An open-source 16-inch laptop designed from scratch."
created_at: "2026-08-26"
---

# 2026-09-18: more bms routing

**Total time spent: 1 hour**

worked on the bms thermal and control wiring and added nine connections. it still has 44 unconnected items, with no physical drc errors. also fixed the c2243 and r2254 datasheet links so they survive schematic generation. all 13 thermal tests passed. the generator fixes are committed, and the unfinished routing is saved locally.
![image.png](https://cdn.hackclub.com/01a0b1d0-285f-77fe-9d2b-c9baa8bb3703/image.png)

# 2026-09-16: more routing: diff pairs + stm32

**Total time spent: 1 hour**

I realized that i did not need to have a whole bunch of grounded stitching vias in between the differential pairs, and i could have just run a ground trace between them, so that's what i did. also did some routing for the stm32, mostly the keyboard nets.
screenshots: ![image.png](https://cdn.hackclub.com/01a0ac70-f6e3-75b8-b58d-57d1b7f6683a/image.png)![image.png](https://cdn.hackclub.com/01a0ac71-1e37-7bca-bcf5-92ebb4256f29/image.png)![image.png](https://cdn.hackclub.com/01a0ac71-3ee3-7403-be03-c81e1c5b4886/image.png)![image.png](https://cdn.hackclub.com/01a0ac71-6618-7479-94a5-9f860795def2/image.png)![Uploading image.png...]()

# 2026-09-16: nextpcb sponsor!

**Total time spent: 10 minutes**

added nextpcb to the repo's sponsors section with their official logo and a link to their site. they're supporting pcb manufacturing and assembly for ducktop2.
![image.png](https://cdn.hackclub.com/01a0aa19-004f-772c-8e63-c053212d5e7e/image.png)

# 2026-09-15: more routing

**Total time spent: 1 hour**

routed a lot of differential pairs, including gigabit ethernet and usb3 port, to the lattepanda mu. also did some miscellaneous routing.
i forgot to start my lapse after like 15 minutes, so lapse only shows 50 minutes :(
![image.png](https://cdn.hackclub.com/01a0a778-5296-75d3-84d0-2cfef724890c/image.png)

# 2026-09-14: put a lot of work into the bms and fixed the usb stuff

**Total time spent: 8 hours**

fixed the 42 usb spacing issues on the center board, corrected the m.2 socket and microphone models, and cleaned up stale footprint warnings. i also investigated the missing ground segment. it was an overlapping stub, so removing it hadn't broken the return path.
most of this session went into the bms: temperature interlocks, isolated controls, the reset circuit and ground returns. some routes passed the normal checks but interrupted important copper paths, so i reworked those and compared the current paths before and after. i also checked smaller resistor and capacitor packages and updated their source definitions. the bms routing is still unfinished, so it isn't ready to order yet.

screenshots: ![image.png](https://cdn.hackclub.com/01a0a1a9-cb19-751d-8837-10939e93d8a2/image.png)![image.png](https://cdn.hackclub.com/01a0a1a9-e5af-7a3a-8361-3989a1dc7640/image.png)![image.png](https://cdn.hackclub.com/01a0a1aa-0aea-7d0c-bd47-e1c45108a213/image.png)![image.png](https://cdn.hackclub.com/01a0a1aa-2a7d-7fc3-80a3-92872410e5d9/image.png)![image.png](https://cdn.hackclub.com/01a0a1aa-4c87-7977-8b9b-e385e3eb6aa2/image.png)![image.png](https://cdn.hackclub.com/01a0a1aa-81ba-7731-a964-bcae3956b353/image.png)

# 2026-09-13: fix the pcie routing and ground layers

**Total time spent: 4 hours**

reworked the nvme and wifi pcie routing. the fast signals now use F.Cu, In2.Cu and B.Cu, leaving the ground layers clear of signal tracks. when i originally routed this, i put some pcie diff pairs through dedicated ground layers which was bad. moved the tx coupling caps to the back of the board near the m.2 sockets, tightened the pair spacing, rounded sharp bends and matched the complete paths through the capacitors. also finished the reset, wake and clock-request connections and connected the remaining socket grounds.
fixed placement collisions and the maker supply trace that crossed its switching keepout. corrected the ethernet controller's pcie link to the 85 ohm netclass, while keeping its mdi pairs at 100 ohms. added checks for complete pair lengths, local fanouts and spacing further along each trace. all 12 pcie paths pass the layout checks, and all 49 tests passed.
updated the board documentation and assembly coordinates, keeping the 358 mm span and both 1.5 mm board gaps. saved and reopened the board to verify the changes survived correctly. there are still 1,725 unconnected items and 42 usb spacing findings to work through. the full assembly export also needs the existing bms connector mismatch resolved.

screenshots: ![image.png](https://cdn.hackclub.com/01a09c07-55e5-7f60-a3ce-c0dd5a8d76f0/image.png)![image.png](https://cdn.hackclub.com/01a09c07-77c6-726a-8476-2915a4094eb3/image.png)![image.png](https://cdn.hackclub.com/01a09c07-c8a0-76a1-96fa-7d2436d5e0a7/image.png)

# 2026-09-13: length matched pcie diff pairs

**Total time spent: 30 minutes**

I forgot to do length matching on the pcie differential pairs last time, so i did it now. luckily it wasnt too much work, because kicad has a very helpful tool for this.
screenshot: ![image.png](https://cdn.hackclub.com/01a09a7a-cbc8-7020-a8d0-80245c8ff7db/image.png)![image.png](https://cdn.hackclub.com/01a09a7a-fdb1-7c5e-8cb9-02117fc967f2/image.png)

# 2026-09-12: finish wifi routing and do fpc routing

**Total time spent: 1 hour**

i finished the wifi routing, with the leftover stuff that wasnt part of the diff pairs, and the main thing i did now was both io fpc connectors. i routed a fanout of vias, and then i had to put ground lines through them as well, which was hard and annoying. i couldnt put the ground vias on the other side because the spec sheet of the connector says there needs to be a keepout there.
screenshots:
![image.png](https://cdn.hackclub.com/01a097b9-920a-75a4-9757-afb81dfcb68d/image.png)![image.png](https://cdn.hackclub.com/01a097b9-b020-74bc-b1c1-cb9c6429cdca/image.png)![image.png](https://cdn.hackclub.com/01a097b9-d0ed-79f3-b395-d41d5ff13941/image.png)

# 2026-09-12: Routed the diff pairs for the nvme

**Total time spent: 1.5 hours**

i routed the differential pairs, 4 total because 4 lanes, of the pcie3 nvme ssd. i had to use some vias for shifting layers, but i did my best to keep everything in their pairs. i also did the gnd stitching of the lattepanda, and added the coupling capacitors for the pcie lanes.
images: ![image.png](https://cdn.hackclub.com/01a0965a-6405-7440-81f2-12dc98443ecf/image.png)![image.png](https://cdn.hackclub.com/01a0965a-9e48-73d8-961d-963e89f0d228/image.png)![image.png](https://cdn.hackclub.com/01a0965a-b620-7a9f-82db-05393e690eec/image.png)

# 2026-09-11: more routing, more checking

**Total time spent: 1 hour**

did more maker mcu routing, continued the bms thermal and control routing, including a smaller test point to make room for the comparator signals. the first temperature channel repair has passed its local checks, and the cell-monitor connections are being rebuilt around it. the cable now is a compact soldered one for the board seams and bms.

images: ![image.png](https://cdn.hackclub.com/01a0927b-a4e7-76e5-8df7-a3133809aa2c/image.png)![image.png](https://cdn.hackclub.com/01a0927c-726f-7408-b4dd-666ed6aa2340/image.png)![image.png](https://cdn.hackclub.com/01a0927c-9e45-7050-a2d4-2aeadc26c867/image.png)![image.png](https://cdn.hackclub.com/01a0927c-dc0d-7b6d-a1b9-36a28f56fe1f/image.png)![image.png](https://cdn.hackclub.com/01a0927d-1dc2-798d-b391-58c5b657984c/image.png)

# 2026-09-11: did some center board routing

**Total time spent: 30 minutes**

I did some routing for the keybaord FFC connector (the 1k resistors), and also some routing for the maker mcu gpio pins.

screenshots: ![image.png](https://cdn.hackclub.com/01a090f6-6fda-7765-8fbb-2e0754340826/image.png)![image.png](https://cdn.hackclub.com/01a090f6-8dc4-70c2-a681-094ce0c58372/image.png)![image.png](https://cdn.hackclub.com/01a090f6-c898-766a-a8f3-08beac6e475e/image.png)![image.png](https://cdn.hackclub.com/01a090f6-fc76-7ca8-9eb6-2854b35496aa/image.png)

# 2026-09-10: did a lot of work, on the center and right board

**Total time spent: 8 hours**

narrowed the center board by 1.5 mm on each side, giving the boards clearance while keeping the overall span at 358 mm. also fixed the placement around the power converters, checked that both M.2 sockets line up with their retainers, and adjusted the front cutout for the revised bms.
corrected hdmi pairs and usb routing on the right board. the radio’s component information now matches the schematics too. another check caught a missing keepout around the microphone opening and 343 duplicated object ids across three boards. fixed those and updated the footprint importer to prevent the same copying issue.
cleaned up more outdated documentation and tightened the board checks. reviewed footprint differences are now tied to the actual saved components, so later changes need another review. all 159 design tests pass, and the left, center, right and radio boards pass their board-level preparation checks.
the mechanical exporter now follows the actual pcb outlines and includes connectors on the underside. this also caught a proposed cable connector sitting beyond the shortened right board, so that placement was rejected. bms routing and the final power-cable fit are still unfinished, and those trials are kept separate from the saved boards.

images: ![image.png](https://cdn.hackclub.com/01a08d84-4489-7b85-b5c1-880328fe6189/image.png) ![image.png](https://cdn.hackclub.com/01a08d85-01a6-79bc-827f-b313c70a80a6/image.png)![image.png](https://cdn.hackclub.com/01a08d85-2a2e-78fa-b1d0-5580223b3ad0/image.png)

# 2026-09-09: left board changes!

**Total time spent: 10 hours**

got the left board’s power changes into the actual kicad project. it now has 325 parts, up from 273, including the revised USB supply, current monitor, fault latch, and permission circuitry. i made room for separate power wiring and the new signal connector while keeping the existing USB routing intact.
also cleaned up the footprint copies and crowded reference labels. the checks compare the actual pads, nets, solder mask, and paste openings, and preserve the deliberate silkscreen edits. the left board has no physical clearance or courtyard errors in the checked version, although there are still a few documented library and package-filter warnings.
spent more time checking the power limits and firmware behavior. the two usbc power controllers now have separate configurations for their actual ports. USB startup allowance is now 5.6 A, with 5.5 A steady, and losing the system supply leaves the USB power fault latched until it can be cleared safely. the design/import tests and firmware host tests pass; hardware testing still needs to happen.
fixed an import bug too: chips drawn across multiple schematic units could end up with broken component links on the PCB. those links now survive a normal save. my newer HDMI and USB routing on the right board is saved as well. the remaining center, right, and BMS revisions still need integration and checking, so there’s more to do before routing readiness or ordering boards.

image: ![image.png](https://cdn.hackclub.com/01a0889c-8ede-7164-ade9-5d88fae6aafc/image.png)

# 2026-09-09: started on the hdmi routing

**Total time spent: 30 minutes**

i did some hdmi routing. only the front layer to start. mostly all resistors/capacitors/diodes done, and ground planes.

images: ![image.png](https://cdn.hackclub.com/01a08686-5018-73b4-a73a-3786f0d6f898/image.png)![image.png](https://cdn.hackclub.com/01a08686-7ad4-763d-adb6-e2f4c6f5c49c/image.png)

# 2026-09-08: fixed a whole bunch of stuff from an audit

**Total time spent: 15 hours**

spent this stretch working through a project audit. there were a lot of problems across the power circuits, component choices, firmware, and board layout, so this turned into a pretty extensive fix. fixed incorrect resistor part numbers, capacitor packages, the rtc diode orientation, and usb protection connections. also corrected the rp2350 regulator placement and its copper keepouts using the reference design.
the keyboard repairs are finished and its manufacturing files have been rebuilt. checked the switch copper exclusions, mounting pads, paste openings, drill files, and component positions. the checked keyboard has zero drc errors and zero unconnected items. the radio board’s antenna connectors also now line up with the actual mounting geometry.
on the firmware side, fixed the charger’s byte order and worked through the startup, register, watchdog, and fan handling problems. added checks around those paths and continued the usb power controls so port permissions account for available power, startup current, and vconn. physical testing is still ahead.
spent quite a bit of time on the connections between boards too. the revised design separates power wiring from the signal cables. found lower-profile shielded cable connectors, built their footprints from the manufacturer drawings, and remapped the signals with ground guards around the high-speed pairs. cable bends, ground straps, and the complete channel still need checking before those changes are applied.
the bms is still being reworked. a power-path check caught new signal routing breaking up the main battery return plane in the test layout. that version has not been applied. the return path needs to stay wide and continuous while the temperature sensing and isolated controls are added.
also moved several connectors and both m.2 sockets to positions that make more sense for the laptop. those positions are saved now, but the card supports, cable access, and nearby components still need another fit check. the remaining main-board routing hasn’t started.

images: ![image.png](https://cdn.hackclub.com/01a082c7-d06a-7c43-a760-4b9f2679363f/image.png)
![image.png](https://cdn.hackclub.com/01a082c8-0e44-7c9d-a8e4-51cf00c01273/image.png)
![image.png](https://cdn.hackclub.com/01a082c8-5b6b-7cf3-a45d-e529e60236a8/image.png)
![image.png](https://cdn.hackclub.com/01a082c8-946c-7aa6-98cb-dee32462ceba/image.png)
![image.png](https://cdn.hackclub.com/01a082c8-f000-79db-99d8-eec59b225a40/image.png)

# 2026-09-07: fixed a whole bunch of stuff to prepare for center board routing

**Total time spent: 7 hours**

i finished a big preparation pass on the main boards for before routing. i added a rounded cutout at the front center of the main pcb for the bms, with 1.5 mm clearance around it. this keeps the bms out of the middle battery cell’s space. i moved the battery connector to face it and checked that all 30 cable contacts line up with the correct reversed pin mapping.
the placement review uncovered several problems that would have been bad to find later. both m.2 sockets faced away from their mounting nuts, and some power components, the boot button, and the programming connector occupied the card areas. i fixed the socket positions using the reference carrier’s mounting dimensions and added the full card outlines to their courtyards so future placement checks catch overlaps.
i also regrouped the regulator capacitors, feedback networks, inductors, crystals, and battery-gauge parts. several were much too far from their circuits. two usb coupling capacitors had 100pF part numbers despite being labelled 100nF, and another capacitor had a mismatched capacitance and part number. fixed that.
the remaining work included cleaning up reference labels, restoring 18 connector mounting-pad grounds, fixing usb net names so kicad recognizes the differential pairs, and replacing obsolete routing keepouts. i also fixed an editing-tool bug that removed component models during rotation.
all 5,197 checked pads match their schematics, all 27 regression tests pass, and all 67 (shush) electrical calculations pass. the center board is clean apart from its 2,038 airwires. i preserved the existing left-board and bms copper. routing is next, including correcting the left board’s existing usb widths and spacing.

layout diagram: ![image.png](https://cdn.hackclub.com/01a07bb6-e3e9-743e-89d1-eb532020e2b5/image.png)

# 2026-09-06: changed oled connections, doing more stuff to make the routing ready

**Total time spent: 1 hour**

switched both oleds to wired connectors and moved the maker header beside the mu. fixed the copper-edge errors, cleaned up 37 placements, and tested the layer rules. center board drc is down from 158 to 61 errors; routing still needs doing.

![image.png](https://cdn.hackclub.com/01a07765-7bde-7c10-92ec-07346f6e9836/image.png)

# 2026-09-06: did more stuff to prepare for center board routing

**Total time spent: 1.5 hours**

fixed the center board checks and documented what still needs work. corrected the board selection, net-name parsing, selector pin review, and test-point generation. added 20 regression tests.

diagram showing clearance violations: ![image.png](https://cdn.hackclub.com/01a076e0-3efa-7be1-8200-1fde458e3d3a/image.png)

# 2026-09-05: finish bms routing

**Total time spent: 5 hours**

finished the 4-layer bms routing. fixed the shunt sense paths and battery references, widened the power routes, and improved fpc current sharing. cleaned up the silkscreen, updated the docs, and regenerated the board exports. drc and erc both have zero errors and warnings.

this took a lot of time because i already made the board as compact as i could, so i had to squeeze the new stuff in.

screenshots of each layer:
![image.png](https://cdn.hackclub.com/01a073a6-9048-7082-94d6-53b0e83836f3/image.png)
![image.png](https://cdn.hackclub.com/01a073a6-bb19-744f-87be-656d787aa879/image.png)
![image.png](https://cdn.hackclub.com/01a073a7-1d06-7e2b-930d-75ea6e5ffb24/image.png)
![image.png](https://cdn.hackclub.com/01a073a7-4f0c-7bfe-899f-6fef67b0c379/image.png)
render:
![image.png](https://cdn.hackclub.com/01a073a7-a22c-71e5-b1bb-8f9ce35d2bbd/image.png)
![image.png](https://cdn.hackclub.com/01a073a7-f8cb-76e4-9ba0-f12984ad3366/image.png)

# 2026-09-05: clean up file structure and update documentation

**Total time spent: 1 hour**

i noticed the documentation was getting really outdated, as far as one month, and because i have made so much progress since then, it looks confusing. so, i updated all the documentation, and also cleaned up the file structure because it was messy.
structure image: ![image.png](https://cdn.hackclub.com/01a0714b-6cee-7a22-875c-1106cb16ec58/image.png)

# 2026-09-04: 1/4 PCBs routed: BMS board routed!

**Total time spent: 5 hours**

I routed the BMS board. I kept in mind the trace thicknesses, because a lot of power will go through this. I had 2 uninterrupted ground zones in the inner 2 layers, and another two on the top and bottom. I also added stiching vias. Also there are mounting holes.
Images: ![image.png](https://cdn.hackclub.com/01a06d38-73ad-7ae8-888b-2f76c6792516/image.png) ![image.png](https://cdn.hackclub.com/01a06d38-15cd-7c46-b633-3fdd64733ecf/image.png) ![image.png](https://cdn.hackclub.com/01a06d38-e662-782f-9ffe-5e293bdf5a61/image.png)

# 2026-09-03: Finished and prepared the BMS pcb daughterboard for routing, and some other stuff

**Total time spent: 3 hours**

 - i found more than 35 differential pairs with no impedance class across the three i/o boards, the left's hub/usb3 port pairs and the right's hdmi/gbe pairs would have routed at 0.2mm default width. 72 netclass patterns added. same thing on the bms power rails, only the fused positive and pack negative were power_hi: the raw input, post-fuse vin, both fet commons, and the fg_vss return were all default. everything high-current is now power_hi.

 - changed to 4 layer board, with the 2 inner ones being solid fg_vss

 - i wanted to verify individually that the board work before i would plug anything in and fry something, so i added 16 test points

starting routing now

image: ![image.png](https://cdn.hackclub.com/01a068d3-c59d-755c-a8f5-9ef7fbb2cf46/image.png)

# 2026-09-02: I had someone audit the whole project (big thanks to them, they found a lot of stuff!) and fixed them

**Total time spent: 15 hours**

what the audit found:
- shadow nets: the fpc connector pads carried bare net names (VSYS) while the circuits used prefixed ones (/VSYS). same word, different nets. the battery never reached the charger.
- mirrored cables: a straight ffc between two connectors mounted 180deg apart mirrors the pin order (n <-> 69−n). my boards had straight through maps. fpc3's fused pack positive would have went on gnd. battery had a direct short through the cable.
- both power selectors were dead: the ltc4418 symbol had pins 6 to 10 transcribed from the wrong datasheet column. gnd wired to the intvcc bypass node.
- fh41 shield row 1.25mm off the datasheet, fpc power rails on single pins

right now:
- 4 boards: 0 shorts, 0 clearance, 0 drill/hole · 0 boundary crossings
- 6/6 connectors good
- 0 shadow nets anywhere, ERC 0 x4

images: ![image.png](https://cdn.hackclub.com/01a063ef-f55d-7c44-8241-8cc7a00cc101/image.png) ![image.png](https://cdn.hackclub.com/01a063f0-4abb-7da3-86b9-256b37882fc8/image.png) ![image.png](https://cdn.hackclub.com/01a063f0-8b43-7976-a5ff-e136b3a243ec/image.png) ![image.png](https://cdn.hackclub.com/01a063f0-d2ed-7eb3-b87e-5bc52f36aa95/image.png)

# 2026-08-31: fixed an fpc connector issue

**Total time spent: 5 hours**

i found a problem. the fpc-1 and fpc-2 connectors are a part that doesn't exist. the hirose fh12 series stops at 60 pins, there are no fh12-100s.
i replaced replaced both with the fh41-68s-0.5sh(05). 68 pins, and its a shielded ffc connector so the usb3/hdmi/gbe pairs get a shielded cable, which was the intent anyway. both pin maps are good (fpc-1 uses 1-53, fpc-2 uses 1-61). new footprint derived from kicad's fh41-30s, new 68-pin symbol, solder-hold pads tied to gnd as the shield return, cable spec updated. updated the nets as well.
i also fixed some smaller stuff, like the placement of some components, clearing the shorts and other drc violations.
screenshots:
left io new fpc: ![image.png](https://cdn.hackclub.com/01a05810-569f-7cdc-b635-67d12af9d067/image.png)
right io new fpc: ![image.png](https://cdn.hackclub.com/01a05810-9b77-7fc5-8a3b-d255848b156c/image.png)
also updated on the main board: ![image.png](https://cdn.hackclub.com/01a05812-d01b-7f4d-9e83-1be18cbbbc22/image.png)

# 2026-08-30: wired up fpc connectors

**Total time spent: 5 hours**

every new daughterboards schematic has its hirose connector on it: fpc-1 and fpc-2 are 100-pin, fpc-3 is 30-pin, and all the boundary nets run through them. about to start routing!
image: ![image.png](https://cdn.hackclub.com/01a0540f-7fe8-72c2-862e-d4ceb2ab4763/image.png)

# 2026-08-30: made all .pcb files

**Total time spent: 6 hours**

the main board is now four real .kicad_pcb files: left_io (266 parts), right_io (163), bms (46), ducktop2-center (710). built each from its own schematic so the nets are right, then transplanted the old placement by reference so all the placement keeps.
pcbnew's python wrapper corrupts its own type table after a few hundred by-value returns, so all geometry gets parsed from the board text files instead.
drc: zero shorts on all three daughterboards, zero clearances on bms, all the remaining violations are pre existing footprint level stuff that's also on the original board. center board went from 51 shorts to 17 and none of those involve re placed parts. also generated the FH12-100S footprint (derived from the 50-pin, 100 pads, MP tabs) since kiCad doesn't ship one, and sorted out that kicad-cli resolves project rules from the cwd, which took way too long to figure out.

pcb screenshots:
main board:![image.png](https://cdn.hackclub.com/01a052bd-bdf4-7b2e-9065-1365d9742e35/image.png)
left io board: ![image.png](https://cdn.hackclub.com/01a052be-4f9b-7ff1-bf6f-5930085ea273/image.png)
right io board: ![image.png](https://cdn.hackclub.com/01a052be-cdac-7f9c-b18c-c9c345943fca/image.png)
bms board: ![image.png](https://cdn.hackclub.com/01a052bf-5ab8-78bd-972e-e6aab283b037/image.png)

# 2026-08-29: center board got cut down

**Total time spent: 1 hour**

the big trim is done. the center board went from 14 sheets to 9: the usb-c i/o sheet, power inputs, hdmi, and ethernet are all gone from it, plus the whole pack-protection section of the power sheet. the center now keeps only whats central: the charger, fuel gauge, and ship fet; the ec and mu; radio; internal services; keyboard; maker; audio. 717 components, down from 1100.
the hard part was the boundary. every net that crosses an fpc now has to exist on the center root as a declared boundary label: 30 to the left board, 35 to the right, plus the pack nets to the bms. and two of them (hub ds1 dp/dm) are pass throughs: they come in on fpc-1 from the left hub and go right back out on fpc-2 to the right board's usb-c port, with nothing on center touching them. the center is just a wire for those.
the verification system had to be rebuilt for four boards. the contract checker now takes a --project flag and runs the right checks against the right netlist, pd1 contracts on the left board, pd2/hdmi/gbe on the right, pack protection on the bms, everything else on center. same for the closure audit and the electrical calculations.
the trim exposed 2 bugs. the daughterboard roots were placing their fpc boundary labels at arbitrary coordinates instead of on the sheet-pin endpoints, so the left and right boards internal wiring never actually connected to their own roots, the netlists showed the pd1 vbus rail as an orphan. and there was a duplicate ground pwrflag sitting on the same spot in the power sheet from my earlier edit, which the erc caught.

image: ![image.png](https://cdn.hackclub.com/01a04f62-da9f-7f2d-9dc3-81e7f27977da/image.png)

# 2026-08-29: bms board!!

**Total time spent: 1 hour**

the bms board has schematics now. 45 components. the protector filter networks. the bq77915 needs a divider and caps per cell tap, and the ltc4368 needs its uv/ov divider, gate slew network, and the whole fault/retry path.
the board has the fuse, pack connector, both protectors (bq77915 primary + ltc4368 redundant), all four fets, both shunts, and the charge/discharge gate network.the fuel gauge is still on the center board, its i2c and alert lines go to the ec and the source manager, so it's electrically center bound even though it's battery stuff. the charger and ship fet stay center too. what crosses to center is just the pack terminals, fault lines, and 3v3: six nets on fpc-3.
schematic image:![image.png](https://cdn.hackclub.com/01a04d8b-8873-7785-bc58-6ae7269bb790/image.png)

# 2026-08-28: right I/O board!!

**Total time spent: 1 hour**

the right board (right_io/) has pd2 (u42), j11/j12 (already usb2), the hdmi chain, and gigabit ethernet. added to its own schematics and subproject.

schematic screenshots: ![image.png](https://cdn.hackclub.com/01a04aad-9b86-74c4-b7c9-11e74763bedd/image.png)![image.png](https://cdn.hackclub.com/01a04aad-d4d7-738b-9755-ca4129571c8b/image.png)![image.png](https://cdn.hackclub.com/01a04aad-ff87-7c43-93ca-e20bdb208125/image.png)![image.png](https://cdn.hackclub.com/01a04aae-3524-7949-bed3-0aeb6034b237/image.png)

# 2026-08-28: left I/O board!!

**Total time spent: 1 hour**

the left board project exists now. it's a standalone kicad project in left_io/ with its own root schematic and two sheets, holding the hub, the pd1 chain, all five left ports, the usb-a cluster, the ss muxes, and the aux screw terminal — 261 components total.
the aux screw terminal (j190) lives on the left board but its protection chain, fuse, tvs, reverse fet, the whole efuse, stays on center next to the vsys or-ing where it belongs. only the raw AUX_DC_RAW crosses the fpc. second, the left sheets are big because they reuse the main board's full layouts, that's fine for now, a compaction pass can come later.

schematic screenshots: ![image.png](https://cdn.hackclub.com/01a04a06-a744-7335-806b-70d252e030aa/image.png)![image.png](https://cdn.hackclub.com/01a04a06-dc35-7b70-867f-cf2253f66e1d/image.png)![image.png](https://cdn.hackclub.com/01a04a07-0933-7700-ae05-c586b4ac1110/image.png)

# 2026-08-28: starting schematic edits

**Total time spent: 45 minutes**

first schematic edit for the split. the right-side usb-c ports (j11 and j12) are losing their super-speed lanes, because after the split there's no usb3 host port left on that side of the board, the mu has only one usb3 host, and it's feeding the left hub. so j11/j12 keep pd charging (15v sink, 5v/0.9a source) and usb2 data, but their ss pins are now no-connect.
the work was mostly in the generators. j11's port lost its tusb1142 redriver and the whole ss coupling/esd chain. j12 lost its hd3ss6126 orientation mux. the hub's ds1 and ds4 ports became usb2-only, their ss pins (7/8/10/11 and 36/37/39/40) are retired to nc, keeping only the d+/d- pairs that feed the ports' usb2.
net result: 16 ss nets deleted, and the schematic gate is back to pass — closure 1574/0, contracts ok, erc 0, and the pin review table at 2602/2602 all pass.
image: ![image.png](https://cdn.hackclub.com/01a049ce-d680-7cdf-b744-73d644c38625/image.png)

# 2026-08-28: connectors picked, cuts validated, boards scaffolded

**Total time spent: 30 minutes**

first, the fpc connectors. the obvious move was to stay in the hirose fh12 family, i already have that for the radio and keyboard (j2300, j310), so one family, one footprint style, one supplier. fpc-1 and fpc-2 get 100-pin versions, fpc-3 gets the same 30-pin part already in the BOM. the important thing i realized is that the impedance for the high-speed pairs is a cable spec, not a connector spec, the fh12 is just a 0.5mm interface, and the 90/100-ohm sections come from ordering impedance-controlled shielded ffc. so the connector decision is boring, which is exactly what you want.
then i validated the cut lines against the actual mechanicals. left cut at x=70 clears the left mounting holes and the hinge notch with 22mm of connector space. right cut at x=300 keeps the right holes and hinge notch with 54mm of space. no hole straddles a cut, which would have been a nightmare for the chassis.
next up is the actual schematic surgery: j11/j12 go usb2-only, the hub and pd1 chain move to the left board, pd2+hdmi+gbe move right, and the bms sheet gets built. that's the real work.
image: ![image.png](https://cdn.hackclub.com/01a0499a-58b7-7725-b349-d5f355002ad4/image.png)

# 2026-08-28: worked out the specs of the split. 4 boards, 3 fpc connectors.

**Total time spent: 2 hours**

so i spent the last session doing the math on the board split. i built a script that assigns every one of the 1225 footprints to its board — left i/o, center mainboard, right i/o, or the battery bms, and then counted every single net that has to cross a board boundary.
the results surprised me a little:
- fpc-1 (center <->left): 75 signals. usb3 upstream pair to the hub, all the hub control (spi, reset, config), the pd1 i2c and irq lines, plus power.
- fpc-2 (center <-> right): 83 signals. hdmi, gigabit ethernet, the whole pd2 chain, usb2 for j11/j12, ec debug.
- fpc-3 (center <-> bms): 16 signals. just the pack terminals, cell taps, gauge i2c, and the charge/discharge gate lines. this one is beautifully small — it's basically the macbook battery board interface.
- the keyboard ffc stays as it is. the keyboard pcb is already manufactured.
the pd controllers had to be split by function, not by side. pd1 chain goes left with the left ports, pd2 chain goes right with j11/j12. and i confirmed that j11/j12 going usb2-only kills 16 super-speed nets that would have been a nightmare to route across two fpc boundaries.
one thing i didnt do for good reason: no vsys, no vbus_raw, no pphv over any fpc. only sys3v3 and usb_port5v cross, and those are the low-current class. running 8.6a of vsys through an ffc would need like 18 pins and would drop voltage anyway.
the spec is committed and frozen. next is picking the actual ffc connectors, validating the cut lines against the mounting holes, and then the schematic work.
image: ![image.png](https://cdn.hackclub.com/01a04970-aae1-7313-9f65-4255538c6313/image.png)

# 2026-08-28: Big change: splitting the PCB into multiple daughterboards.

**Total time spent: 4 hours**

Big change: splitting the PCB into multiple daughterboards
so this day started with someone from hack club messaging me about my decoupling caps. honestly they were right, i measured pin-to-cap distances in the actual pcb files and it was bad. one of the pd controllers had its 68µf pphv bulk cap sitting ~260mm from the chip, basically the other side of the board. the ldo caps were 30-268mm out. the mu's 12v bulk was ~100mm from the module pins. that's a lot of loop inductance for a 30w part, this would have been a pain to debug on a one-shot board.
but the deeper issue was the layout itself. the usb hub sits at x261 and the ports it feeds are at x4.5 and x353, so every super-speed lane runs 200-300mm across the board just to reach a connector. i looked at splitting into two hubs but the mu only has ONE usb3 host port, so there's no way to feed a second usb3 hub without daisy-chaining (latency) or downgrading.
so i settled on a proper 4-board architecture:
 - left i/o board: 3 usb-c (usb3) + 2 usb-a (usb3) + aux input + the hub + the whole pd controller chain. hub finally sits next to the ports it feeds, and all the decoupling caps become naturally local — the cap fix and the layout fix solve each other.
 - right i/o board: hdmi + gigabit ethernet + 2 usb-c (downgraded to usb2 — the mu has no spare usb3 host port, so they'd have to be usb2 anyway). hdmi and gbe were already on that edge so nothing long crosses.
 - battery bms board: like a macbook — a small board at the pack with the connector, protection fets, current shunts, fuel gauge. only pack terminals + i2c cross to the mainboard. the charger stays on the mainboard because it's the hinge of the whole power tree.
 - center mainboard: mu, m.2, ec, all the converters, battery charger, vsys.
the rule that kept me honest: nothing high-current crosses an fpc. no vsys, no vbus_raw, no pphv. i checked the current math — a full power split would need ~110 ffc pins of power and gnd return at 8.6a, which is just asking for voltage droop and heat. the only things crossing are the hub's one usb3 upstream pair, some i2c and irqs, hdmi/gbe pairs, and pack terminals.
the connectors stay exactly where they are today, the only electrical change is the two right-side usb-c ports become usb2. i'd rather have 5 usb3 ports that are actually good than 7 ports where half are running super-speed lanes across 300mm of fpc.
this is a big layout job — moving the hub and pd chain to the left board, redoing zones for 4 boards, three fpc connectors — but it fixes the actual problems (decoupling, hub fanout, respin cost) instead of papering over them.

mock up of the splits: ![image.png](https://cdn.hackclub.com/01a0490a-68b1-773a-9575-819af38c85ab/image.png)

# 2026-08-27: LattePanda MU power and ground routing

**Total time spent: 15 minutes**

wired all the gnd stitching vias to the lattepanda mu, and also the 12 volt net. also routed miscellaneous nets.
![image.png](https://cdn.hackclub.com/01a04484-f2fa-772a-8d0f-dda4058154a3/image.png)

# 2026-08-27: Designed the PCB layout and schematics and EC firmware for ducktop2

**Total time spent: 142 hours**

Yes, this is very big, but i started this project before i knew about Forge, and i didn't want my hours go to waste.

July 2
- 8f9f31b 07-02. Made the initial commit with the power/battery and EC/MCU sheets, ERC clean. This has the generator state that had been built up before the repo existed. 51 files. 5 h
July 8
- 4fae95c 07-08. Checkpointed the generated schematic baseline across 68 files. 5 h
- 46bb178 07-08. Made the generated schematics deterministic so diffs stopped being noise. 8 min
July 19
- 6b47a97 07-19. Published the current Ducktop2 design, all child sheets, board, and docs. 214 files. 10 h
- eee41e4 07-19. Updated the README. 7 min
- 9073acc 07-19. Expanded the project documentation and added the MIT license. 7 min
- e14f134 07-19. Removed outdated pin-review details from the README. 8 min
July 20
- ab3b887 07-20. Finished the USB-C policy and split the radio hardware out onto its own daughterboard. 96 files. 8 h
July 21
- 720bd9f 07-21. Closed the remaining pin-review contracts. 2 h
- c4217c1 07-21. Relocated 23 high-speed AC coupling caps and completed the pre-routing design review. 1 h 25 min
July 23
- 764558d 07-23. Refreshed the repo with updated PCB renders and the current design state. 2 h
July 27
- 8f2b992 07-27. Wired the trackpad directly over USB2 and recorded the audit holds. 5 h
- 66c243f 07-27. Fixed what the trackpad rewire broke and removed duplicate footprints. 3 h
July 28
- 57008c8 07-28. Assigned 327 BOM MPNs across 11 schematic sheets, closing the procurement gaps from 370 down to 43. 2.5 h
- 3271f16 07-28. Applied the BOM to the radio and keyboard daughterboards and added Cherry MX switch 3D models. 18 min
- 059dbb2 07-28. Added 3D models for 9 more footprints on the main PCB and radio daughterboard. 22 min
- e8a8249 07-28. Added 3D STEP models for the remaining ducktop2 components. 29 min
- 015e06f 07-28. Added the Amphenol MDT420M01001 3D model (M.2 Key M) and re-added the remaining models. 2 min
- 9a02516 07-28. Fixed the radio DB J1 layer (F.Cu to B.Cu) for the mezzanine stack and added the radio DB outline to the mainboard Dwgs.User. 7 min
- b4d83e6 07-28. Fixed the 3D model paths to use KIPRJMOD, moved J1 to B.Cu, and relocated 77 fanout traces plus 42 stitch vias for the mezzanine stack. 4 min
July 30
- dc019f9 07-30. Defined the 6-layer fabrication stackup for NextPCB. 3 h
- cbbc6c9 07-30. Fixed 3D model paths and updated the PCB format to KiCad 10.0. 1.5 h
- 5fe84ee 07-30. Added the power loop relocation scripts and BOM MPN assignments. 3 h
- ab1ab99 07-30. Ported the EC target firmware to the STM32F407. 2.5 h
July 31
- dc893b5 07-31. Added the EC DFU programming path: BOOT0 button (SW2) and the rear-edge USB-C prog port (J70/U70/U71/D70) in 08_internal_services. 3 h
- 744f320 07-31. Fixed the ERC and annotation issues in the EC DFU programming section. 2.5 h
- fbc8981 07-31. Added the user-facing behavior verification checklist covering lid, USB-C roles, boot, audio, display, input. 24 min
- db86159 07-31. Recorded the user-confirmed behavior expectations: lid means display off, wide-range AUX, headphone jack as an action item, keyboard/OLED/fan specs. 19 min
- 2ff5b2b 07-31. Locked the keyboard layout (board already fabricated), recorded the headphone jack design (rear 3.5mm with plug-detect mute), and added the rendered keyboard image. 13 min
- 6fe853f 07-31. Wrote the headphone jack implementation plan as a handoff for the next session. 28 min
- 90f3521 07-31. Wrote the full project handoff for the next session. 1 h
- c329f95 07-31. Regenerated the child schematics to sync with the current generators. 29 min
- fae06d4 07-31. Added the rear 3.5mm headphone jack with plug-detect speaker mute as sheet 15. 45 min
- 70811a2 07-31. Documented the headphone jack completion across verification, design-status, and handoffs. 10 min
August 1
- d0991b3 08-01. Added the host-tested keyboard Fn-layer keymap (ec_keymap). 1.5 h
- d1396d0 08-01. Added the host-tested EC fan policy core (ec_fan). 3 min
- d95d9f2 08-01. Added the host-tested OLED status content composer (ec_oled). 9 min
- 22a966d 08-01. Added the host-tested lid switch debouncer (ec_lid). 18 min
- f223750 08-01. Added the host-tested battery state machine (ec_battery). 36 min
- e2c594f 08-01. Added the eMMC recovery/hibernate setup design and tooling. 9 min
- 14a7a89 08-01. Refreshed the documentation across the repo. 15 min
- 68cd774 08-01. Stamped the generation-time BOM catalog and closed the remaining 378 procurement gaps. 43 min
- 98d614d 08-01. Computed candidate impedance geometries for the NextPCB review. 2.5 h
- b805412 08-01. Added impedance-driven net classes and base design rules to the mainboard. 18 min
- 4dda560 08-01. Documented the high-speed routing plan and skew budgets. 20 min
- 42abc43 08-01. Added the placement-collision analyzer for pre-routing triage. 13 min
- 7877b5c 08-01. Added the placement-collision fixer with conservative grid moves for passives. 21 min
- e23a151 08-01. Documented the pre-routing placement review checklist. 2 min
- d53b337 08-01. Analyzed the mic acoustic integration and accepted the trackpad/battery overlap. 8 min
- 1e346eb 08-01. Fixed the placement analyzer pad parsing (at/size/at_span). 28 min
- ee8a2bf 08-01. Added the EC target driver stack: BQ25798/BQ34Z100, ADC/PWM/tach hardening, and app glue. 1.5 h
- dc4a1f8 08-01. Added the EC keyboard matrix scan with debounce and wired the keymap into the target loop. 1 h 7 min
- a6bddbd 08-01. Added the EC USB HID keyboard device stack (OTG_FS) with report transport. 11 min
- 5dd8b29 08-01. Documented the EC driver stack and keyboard path completion in the target port status. 10 min
- 203083f 08-01. Synced 11 headphone-jack section footprints onto the mainboard (ECO). 40 min
- 7d5caa5 08-01. Ran placement fixer pass 2: 190 passive moves, shorts 199 to 97, mask 199 to 107. 1 min
- 08673af 08-01. Ran placement fixer pass 3: 59 more passive moves, shorts 97 to 54. 7 min
- b93a023 08-01. Documented the big-part placement proposals for review. 15 min
- aa10d03 08-01. Added first-pass GND planes, power islands, and mechanical keepouts, unfilled. 8 min
- 8199ed3 08-01. Aligned the min through-drill constraint with NextPCB capability (0.2mm), clearing 199 drill findings. 1 min
- c555bf9 08-01. Ran placement fixer pass 4 with board-bounds enforcement and recovered the pushed-off caps. 3 min
- dec7206 08-01. Updated the placement review, 27 off-board anchors left for manual work. 10 min
- 8271eda 08-01. Revived the floorplan workflow, planner updated with all major parts plus apply_floorplan_layout.py. 31 min
- 3717620 08-01. Verified all part sizes in the floorplan, added OLED modules, unlocked all parts. 23 min
- 35006b8 08-01. Set the hinge keepouts to the Framework 13 hinge dimensions, identical L/R modules. 4 min
- c5cefd7 08-01. Adopted the user floorplan layout and fixed the mainboard coordinate to (0,0). 16 min
- e48ad3c 08-01. Applied the floorplan revD layout to the mainboard, 10 parts with the Mu upper-middle. 20 min
- ced8650 08-01. Fixed Edge.Cuts (removed the stale notch), cleaned zones, keepouts, and guides, ran fixer pass 5. 52 min
- f4c8a3d 08-01. Added board-bounds enforcement to the floorplan apply script. 10 min
- 986616b 08-01. Applied the user layout rev2 and ran fixer pass 6, shorts 90 to 76. 4 min
- d8df625 08-01. Swapped the radio daughterboard connector from DF40-60 to FH12-30S FFC. 1 h 25 min
August 2
- 4a14b0c 08-02. Did a thorough cleanup: fixed Edge.Cuts, cleared Dwgs.User guides, clipped zones, restored J2300. 1 h
- ab101bc 08-02. Fixed Edge.Cuts to a plain rect, cleared all Dwgs.User guides, restored J2300. 10 min
- c86cdd1 08-02. Reverted to d8df625, restoring the original Edge.Cuts, guides, and zones. 6 min
August 9
- 7a94c7d 08-09. Updated Edge.Cuts to a plain 358x185 rect, regenerated the Dwgs.User sheet guides, fixed the J2300 position. 1.5 h
- d93fcd6 08-09. Fixed Edge.Cuts properly, replacing 5 notch lines with 1 rect edge. 26 min
- f0902e6 08-09. Deduplicated the UUIDs on the outline segments. 40 min
- 0b3a3a3 08-09. Regenerated the Dwgs.User sheet guides with valid unique UUIDs. 8 min
- 32a29a8 08-09. Removed the old left-side notch, leaving a plain 358x185 rectangle. 55 min
- eecee42 08-09. Restored the J2300 radio-DF40 position to on-board at (288.4, 149.1). 16 min
August 11
- c3d268c 08-11. Resolved all pad collisions in placement and applied the user floorplan export. 3 h
- 8a18fc9 08-11. Fixed the port positions, J22 to y=25, J21 to y=36.4, and set the guides to the footprint bboxes. 1 h 13 min
- d5eb9ff 08-11. Fixed the port positions and M.2 card layout, guides verified with DRC. 2 h
August 12
- a283abc 08-12. Added the ethernet jack mid-mount cutout and verified the M.2 slots and port alignment. 1 h
- 1435f20 08-12. Fixed all remaining DRC shorts, 49 to 0. 29 min
- f3e4074 08-12. Cleaned up the Dwgs.User guides, removed 67 stale blocks, regenerated 21 aligned pairs. 29 min
- ab33172 08-12. Swapped J2300 to the FH12-30S FFC and removed 52 dangling route stubs. 24 min
- b8e329f 08-12. Fixed F1, made the Mu carrier (A1) mountable by moving it south and relocating H1/H2. 1 h 15 min
- 5c33a8a 08-12. Fixed F2, moved U170, R2316, and U46 clear of the J40 WiFi socket. 4 min
- 262ba3b 08-12. Fixed F3, moved the keyboard FFC series resistors clear of the J310 pad field. 4 min
- 5fe1b61 08-12. Fixed F4, J2300 fully on-board, and fixed the FH12-30S BOM properties. 4 min
- 8bbfa01 08-12. Fixed F5, the mounting hole pattern, board is canonical, updated the retention doc. 7 min
- e57919a 08-12. Fixed F6+F8, committed the real impedance net classes and fixed all external clearances. 7 min
- 0cf5f36 08-12. Fixed F9, moved the ethernet PHY crystal Y500 adjacent to U500. 9 min
- 91c4f3b 08-12. Fixed F7, documented the ethernet notch and mounting pattern as the released contract. 5 min
- caf6ffb 08-12. Redocumented F7, same ethernet notch and mounting pattern contract. 5 min
- a5b4f3a 08-12. Recorded the independent review findings and the final F1-F9 fix state. 20 min
August 13
- 0b3974d 08-13. Resolved all placement DRC classes, board at 186 violations. 2 h
- c8316e3 08-13. Added the electronics-correctness handoff review. 4 min
- 9716bc6 08-13. Ran the electronics review v2 and found the J2300 pin-net mismatch across 26 pads. 1 h
- 77484dd 08-13. Ran the electronics review v3, retracted the false alarms, confirmed J2300 as the blocker. 1 h
- 9a2d7a5 08-13. Added the independent review prompts for nets/electronics and user-functionality. 8 min
- b13a110 08-13. Fixed P0, replaced J2300 with the FH12-30S and resynced all 30 pin nets. 55 min
- f3c0fe1 08-13. Recorded the user-functionality review, noted the DB J1 (P0-2) and EC-update/S5-gating decisions as open. 35 min
- 3176d90 08-13. Completed the EC DFU port (J73) and the DB power rework, verified schematic and board. 1 h
- 8a64108 08-13. Closed the remaining electronics-review items: FAN1_TAC, SLS_S3, SIO UART, F5/F6. 1.5 h
- ec8ea47 08-13. Fixed the F1 (Mu mountability) and F3 (keyboard FFC) review findings. 25 min
- 39123b2 08-13. Did the mechanical enclosure/stack design, hinge plan, and battery-trackpad resolution. 2 h
- 5bbfe91 08-13. Did mechanical rev 2, trackpad stacks above the battery row, 358x248 envelope. 15 min
- 7351b21 08-13. Transitioned the mainboard stackup to 8 layers, impedance geometry preserved. 40 min
- a7268a4 08-13. Drafted the 8L power plan with the rail inventory, L5 island rules, and open items. 10 min
August 14
- e069a6f 08-14. Did the pre-routing audits: Mu fan-out feasibility, power load budget, footprint audit. 2 h
August 23
- 6513f54 08-23. Added NVMe power headroom and the pack-backed RTC, coin cell removed. 3 h
- fd5a419 08-23. Prepared the NextPCB 8L fab submittal with the DRC-vs-capability gap table. 10 min
- 367b55e 08-23. Set the fab submittal solder mask to BLACK (matte preferred), 0.15mm spacing clears the 5mil black bridge rule. 15 min
August 24
- fe23e7d 08-24. Closed out phase 1: fab rules, thermal/routing plans, audits, silk cleanup. 2 h
- 1f735b5 08-24. Ran the independent-verifier sweep, fixed 12 stale contracts and 4 real board bugs. 1 h 20 min
- 019de9e 08-24. Applied the fab field-solved impedance geometry after the NextPCB stackup approval. 5 min
- 757482c 08-24. Set the stackup release status to APPROVED, fab gate now passes. 5 min
- 14e332e 08-24. Corrected the radio DB floorplan footprint (160x110, 4x M2 mounts) and documented the DB mounting contract. 25 min
- 92751f9 08-24. Added the USB-A spare-port headers on hub DIS5 (USB3) and DIS6 (USB2). 30 min
- 1360032 08-24. Applied the J73/J190/C35/J11 placement updates from the live KiCad session. 30 min
- 7ff43e4 08-24. Did the USB-A spare port board placement and full schematic/board sync. 55 min
- 72bc0a9 08-24. Regenerated the schematic sheets as a deterministic snapshot after the USB-A work. 20 min
- 6897d31 08-24. Cleaned up the USB-A port placement, refreshed the DRC allowlist, restored Q60B. 10 min
- 1b47b5f 08-24. Set the intentional 8-point mounting hole pattern, clear of mechanical envelopes. 20 min
- 8576f12 08-24. Wrote the USB-A port cluster routing plan and strategy analysis. 25 min
- ceff6ca 08-24. Regenerated the power zones and mounting-hole keepouts at the current positions. 2 h
- 8643449 08-24. Wired the hub DIS5 SuperSpeed lanes to USB3-A J24, tied the J24 shield to GND, applied net classes. 1 h 15 min
- 3326e81 08-24. Added the full-board routing plan. 8 min
- 8c8d5fe 08-24. Synced the project net-class settings to the approved board geometries. 10 min
- c456299 08-24. Added the POWER_HI/POWER_MID net classes for phase 1 routing prep. 5 min
August 25
- 2ceabaf 08-25. Put the spec-sheet routing presets into the project design settings. 1.5 h
- 3c84d5d 08-25. Restored J11 to the top of the right edge at (353.475, 30) mirroring J22, with a position guard. 20 min
- 54f1726 08-25. Assigned ratnest net colors by routing function across 518 nets. 4 min
- 5ae4cb0 08-25. Fixed the power-zone layer architecture to match the routing-plan stackup. 25 min
- 4f9caaa 08-25. Regenerated the Dwgs.User guides to reflect the current board. 4 min
- dd332ac 08-25. Added the Framework 13 hinge cutouts to Edge.Cuts and removed the Dwgs.User guides. 35 min
- 7ee8c4d 08-25. Fixed the net-color serialization to KiCad's CSS-string format and re-applied the presets. 40 min
- 449c2a5 08-25. Aligned the user-moved mounting holes to the edge rails. 25 min
- 42708da 08-25. Made the hinge cutouts symmetric and set AON_FAULT_N to pure red. 1 h 15 min
- 388f876 08-25. Moved the net colors to the app's real location, net_settings.net_colors. 10 min
- 955904c 08-25. Fixed the report_unexpected NameError in the release gate, a lost diff line from an earlier edit. 30 min
August 26
- e0a8dce 08-26. Renumbered the duplicated mounting holes H21-H27 and added the schematic symbols. 1.5 h
- 8862f57 08-26. Fixed the dead L5 power islands: hierarchical zone net names, split VBUS_RAW, applied the 85-ohm DIFF_85 geometry. 3 h
- 87d3dfe 08-26. Fixed the stale USB7206C DIS5/DIS6 contract, these are active USB-A ports, not 0R straps. 15 min
- 66ad851 08-26. Renamed Q60B to Q62, the letter-suffix reference broke the KiCad annotation check. 25 min
- df45a4c 08-26. Normalized the TPS7A0210_unit1.svg to LF line endings. 3 min
- 29ffb8a 08-26. Added the funding pitch, the full BOM cost breakdown at about $3,560, and the README cost section. 1 h
- dcbf6a6 08-26. Merged the remote-tracking branch origin/main. 4 min
- 05e0188 08-26. Fixed the EC startup memory initialization. 1.5 h
- 78d98b4 08-26. Corrected the EC clock tree and timer rates. 2 min
- 5fd464c 08-26. Corrected the EC ADC register mapping. 2 min
- b960da7 08-26. Made the EC source manager fail safe. 9 min
- 35ceb4c 08-26. Fixed the authoritative mainboard net classes. 3 min
- 488c7fb 08-26. Partitioned the mainboard power zones. 45 min
- 8da03cd 08-26. Corrected the EC USB register and request mappings. 3 min
- 99f06b4 08-26. Grounded the EC target observations and power limits. 10 min
- 1ae4b5e 08-26. Hardened the release gate with refilled-state DRC and an exact allowlist. 6 min
- 88417fb 08-26. Made the PCB object UUIDs deterministic and unique, with gate enforcement. 5 min
- 0722019 08-26. Contracted the U773 endpoint buck and USB-A cluster pins. 7 min
- 9e14f10 08-26. Regenerated the NextPCB mainboard quote package from the current sources. 7 min
- d2a97e7 08-26. Completed the structured impedance approvals in the stackup record. 5 min
- be371a6 08-26. Refreshed the stale design docs to the current 8-layer state. 3 min
August 27
- 20de7a4 08-27. Documented the source-local L5 island architecture for power routing. 45 min

Pictures:
![Screenshot_2026-08-27_at_13.50.28.png](https://cdn.hackclub.com/01a0445c-9019-7fef-a079-2795fc54d2f0/Screenshot_2026-08-27_at_13.50.28.png)
![Screenshot_2026-08-27_at_13.50.36.png](https://cdn.hackclub.com/01a0445c-88bf-7293-b4a7-17e53fc211ac/Screenshot_2026-08-27_at_13.50.36.png)
![Screenshot_2026-08-27_at_13.50.49.png](https://cdn.hackclub.com/01a0445c-878e-7920-8afe-d62ad111fe86/Screenshot_2026-08-27_at_13.50.49.png)
![Screenshot_2026-08-27_at_13.51.02.png](https://cdn.hackclub.com/01a0445c-8918-78fa-be9e-9139f733ea99/Screenshot_2026-08-27_at_13.51.02.png)
![Screenshot_2026-08-27_at_13.51.15.png](https://cdn.hackclub.com/01a0445c-7acf-7d15-9243-0419b7d7638e/Screenshot_2026-08-27_at_13.51.15.png)
![Screenshot_2026-08-27_at_13.51.28.png](https://cdn.hackclub.com/01a0445c-8a39-7c83-b561-85f4c6efb3ca/Screenshot_2026-08-27_at_13.51.28.png)
![Screenshot_2026-08-27_at_13.51.41.png](https://cdn.hackclub.com/01a0445c-8b4e-7ffc-91fc-97281ed9fed2/Screenshot_2026-08-27_at_13.51.41.png)
![Screenshot_2026-08-27_at_13.51.57.png](https://cdn.hackclub.com/01a0445c-85a5-7275-a78a-80709adb04cf/Screenshot_2026-08-27_at_13.51.57.png)
![Screenshot_2026-08-27_at_13.52.21.png](https://cdn.hackclub.com/01a0445c-7a63-76e6-9e95-feeab91d41ed/Screenshot_2026-08-27_at_13.52.21.png)
![Screenshot_2026-08-27_at_13.52.32.png](https://cdn.hackclub.com/01a0445c-8615-796c-9c15-28fc8250076e/Screenshot_2026-08-27_at_13.52.32.png)
![Screenshot_2026-08-27_at_13.52.47.png](https://cdn.hackclub.com/01a0445c-84f4-7e82-9686-8d427443ac1f/Screenshot_2026-08-27_at_13.52.47.png)
![Screenshot_2026-08-27_at_13.52.55.png](https://cdn.hackclub.com/01a0445c-89b1-7123-9c68-9b411397cba0/Screenshot_2026-08-27_at_13.52.55.png)
![Screenshot_2026-08-27_at_13.53.03.png](https://cdn.hackclub.com/01a0445c-8bbd-73d3-a4c2-9e4ed64f2fc4/Screenshot_2026-08-27_at_13.53.03.png)
![Screenshot_2026-08-27_at_13.53.44.png](https://cdn.hackclub.com/01a0445c-8733-761b-82ca-6d1c6f7adbe8/Screenshot_2026-08-27_at_13.53.44.png)
![Screenshot_2026-08-27_at_13.54.28.png](https://cdn.hackclub.com/01a0445c-8bf5-7077-bd14-64a2bf529805/Screenshot_2026-08-27_at_13.54.28.png)
![Screenshot_2026-08-27_at_13.54.37.png](https://cdn.hackclub.com/01a0445c-82f6-7259-9a74-9089135c7363/Screenshot_2026-08-27_at_13.54.37.png)
