# m.2 card space

checked the saved center-board placement against the 2280 SSD and 2230
Wi-Fi spaces used for the fan wiring. all 611 populated top-side parts
have courtyards, and the placement file matches the saved PCB.

![the two card spaces and C837 beside the SSD](views/m2-card-clearance.png)

the Wi-Fi space only overlaps its own socket and retainer. the SSD space
also catches a small edge of C837's courtyard. its nominal Fab body stays
0.267 mm outside the expanded card box, and its pad bounds stay 0.192 mm
outside. this does not show a reason to move C837. the exact capacitor
body tolerance and assembled position still need confirming; the Fab
outline is not a manufacturer maximum.

| space | installed X range, mm | installed Y range, mm | unrelated courtyard overlap |
| --- | --- | --- | --- |
| NVMe 2280 | 189.00 to 276.60 | 85.85 to 108.85 | C837, 0.172 mm² |
| Wi-Fi 2230 | 140.75 to 178.35 | 85.80 to 108.80 | none |

these are expanded selection boxes from the saved socket and retainer
positions. they are not the outlines of purchased cards. the fan route
allows card space from 1 to 6 mm above the motherboard. H3's complete
retainer stack has its own 6 mm allowance, and H4 has a separate 6.3 mm
allowance at the screw. those local fastener limits do not set the card's
underside clearance.

the [M-key socket](https://www.amphenol-cs.com/product/mdt420m01001.html)
and [E-key socket](https://www.amphenol-cs.com/product/mdt420e01001.html)
are both listed at 4.2 mm nominal height. that is the socket height, not
the card seating plane. the saved H3/H4 parts are nominal 2.5 mm
retainers. check the complete socket, card, retainer and screw stack
against the chosen modules before tightening anything down.

the SSD and Wi-Fi models are not recorded yet. their thickness,
underside components, antenna plugs and lead bends still need checking.
the straight plan boxes do not cover the tilted insertion motion or
clearance to remove a card. this screen leaves the PCB and all component
positions unchanged.

`m2-card-clearance.json` records the overlaps, native capacitor geometry
and source hashes. run `check_card_clearance.py` with the same Python
environment as the case scripts. it calls the installed KiCad Python to
read C837 from the saved PCB; `--kicad-python` can select that executable
on another machine. it does not save the board.
