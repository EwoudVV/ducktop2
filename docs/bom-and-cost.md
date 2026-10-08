# parts and cost

updated 8 october 2026. the split design needs a new per-board quote.
there is no reconciled current total yet.

## what the next estimate needs to cover

| Item | Basis for the next quote |
| --- | --- |
| Center, left, and right PCBs | Three separate eight-layer boards, current outlines, approved stackup/impedance requirements |
| BMS PCB | Four layers, 35 um copper, 1.6 mm board; confirm 20 um hole plating in the quote |
| PCBA and component sourcing | Separate BOM/CPL for each board, DNPs, hand assembly, fixtures, setup charges, and spares |
| Radio board | Separate four-layer board and its assembly/components |
| Keyboard | New four-layer, 0.8 mm RGB revision; 65 LEDs, driver and support parts. Original boards have diodes fitted and no switches fitted |
| Mu | DFR1294 Ultra 226V initially, or DFR1294-1 development kit; carrier and cooling must also support DFR1295 Ultra 256V |
| NVMe and Wi-Fi/Bluetooth | Final module identities and capacities |
| Display | Current AUO panel, final compatible eDP harness, mounting and hinge hardware |
| Pack | Three owned AKZYTUE 1160100 packs, confirmed listing B0FBRGNCJF; replacement wiring, insulation, connectors, probes, fuse and mounting |
| Interconnect | Four Molex 503908 signal connectors and their 41/51-contact cables, WAGO auxiliary/BMS power links, direct XT30 USB5 loom, ground braids, BMS control/probe cables, and keyboard/radio/trackpad cables |
| Case and cooler | Measured design, material/process, fasteners, cold plate, heatpipe, fins, blower |
| Other costs | Shipping, tax, assembly tooling, test fixtures, and replacement parts |

## where part identity lives

schematic fields and generation-time assignments hold manufacturer, MPN,
footprint, DNP, and controlled assembly information. `gen/bom_catalog.py`
supplies many of the passive identities. component inventory tools turn a
schematic export into a sourcing report.

the center and I/O boards have manufacturer and part-number fields for all
1,315 populated sourcing items. the [main-board part selections](hardware/main-board-parts.md)
record the corrected capacitor codes, body heights and assembly details.
export a separate BOM for each of the six boards when quoting. include off-board items such as
probes, fuse/holder assemblies, crimp contacts, housings, braids and wire.
DNPs and owned assemblies need their intended classification.

one physical footprint is not necessarily one purchased component or one
assembler placement. test points, holes, modules, compound fuse/holder
assemblies, DNPs, and hand-soldered parts affect those counts.

DFR1294-1 includes the 226V compute module, Mini Carrier Board and Ultra
active cooler. do not also count a separate DFR1294 module or FIT1049 cooler
when quoting that kit. NVMe storage and a suitable power supply are separate.
the Mini Carrier is for development; the finished laptop uses its custom boards.

the [cooler parts](../mechanical/case-prototype/cooling-parts.json) now include
a stock ATS-HP-F7L200S65W-018 pipe candidate. the observed single-part price
was [$5.68 at DigiKey](https://www.digikey.com/en/products/detail/advanced-thermal-solutions-inc/ATS-HP-F7L200S65W-018/5049701)
on 8 october, before forming, shipping and tax. that
is not a price for a complete cooler. the spreader, fins, duct, forming
and assembly still need quotes. request small memory-pad samples instead
of budgeting a full 9-inch sheet. do not count another FIT1049 if it comes
with the module kit; it is also the reference for the custom spring mount.

## ownership and sponsorship

check receipts and actual on-hand stock before subtracting owned parts from
the budget. confirm supplier credits, covered costs, and timing from the
correspondence before using them in the total.

## quote record

for each quote, retain supplier/date, exact board revision, layer/finish/copper
options, assembly side and quantities, BOM/CPL versions, substitutions,
shipping/tax, and expiry. keep component cost separate from bare-board fab
and assembly labor so it is not counted twice.

the [build and verification guide](build-and-verify.md) describes the files
needed for an order. the [Forge pitch](forgery_pitch.md) should
use this page's reviewed budget once that quote work is complete.
