# parts and cost

updated 4 september 2026. the split design needs a new per-board quote.
there is no reconciled current total yet.

## what the next estimate needs to cover

| Item | Basis for the next quote |
| --- | --- |
| Center, left, and right PCBs | Three separate eight-layer boards, current outlines, approved stackup/impedance requirements |
| BMS PCB | Corrected board, agreed layer count and copper weights |
| PCBA and component sourcing | Separate BOM/CPL for each board, DNPs, hand assembly, fixtures, setup charges, and spares |
| Radio board | Separate four-layer board and its assembly/components |
| Keyboard | Existing rev A package; check what has already been ordered/received |
| Mu | Exact N305 module/RAM variant and cooling/retention hardware |
| NVMe and Wi-Fi/Bluetooth | Final module identities and capacities |
| Display | Current AUO panel, final compatible eDP harness, mounting and hinge hardware |
| Pack | Exact cells and owned stock, harness, connectors, cutoff assemblies, fuse and mounting |
| Interconnect | Four FH41 connectors, two BMS FH12 connectors, compatible FFCs, and keyboard/radio/trackpad cables |
| Case and cooler | Measured design, material/process, fasteners, cold plate, heatpipe, fins, blower |
| Other costs | Shipping, tax, assembly tooling, test fixtures, and replacement parts |

## where part identity lives

schematic fields and generation-time assignments hold manufacturer, MPN,
footprint, DNP, and controlled assembly information. `gen/bom_catalog.py`
supplies many of the passive identities. component inventory tools turn a
schematic export into a sourcing report.

the latest copied-project inventory reported one center-board procurement
gap. that is not a combined count for all boards. inspect the missing R747
identity, BMS FPC106 fields, connector suffixes, and each board's inventory
before claiming the BOM is complete. DNPs and owner-supplied assemblies need
their intended classification rather than a made-up MPN.

one physical footprint is not necessarily one purchased component or one
assembler placement. test points, holes, modules, compound fuse/holder
assemblies, DNPs, and hand-soldered parts affect those counts.

## ownership and sponsorship

check receipts and actual on-hand stock before subtracting owned parts from
the budget. confirm supplier credits, covered costs, and timing from the
correspondence before using them in the total.

## quote record

for each quote, retain supplier/date, exact board revision, layer/finish/copper
options, assembly side and quantities, BOM/CPL versions, substitutions,
shipping/tax, and expiry. keep component cost separate from bare-board fab
and assembly labor so it is not counted twice.

the [manufacturing checklist](../manufacturing/README.md) describes the files
needed for an order. the [Forge pitch](forgery_pitch.md) should
use this page's reviewed budget once that quote work is complete.
