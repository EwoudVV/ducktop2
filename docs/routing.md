# routing and layout review

updated 4 september 2026. i want routing and board edits to happen in the
visible KiCad editor so i can watch the work. the next infrastructure step
is a live connection that reads the editor state and applies small, undoable
changes there. this page keeps the review order and constraints together.

## starting point

the BMS is routed and under review. center, left, right, and radio are
unrouted. the keyboard has its own routed rev A design. use the actual
board files listed in the [README](../README.md), not old monolith renders
or segment counts.

before changing the BMS, resolve its fuse-net mismatch and layer conflict.
then review the current paths described in [power and battery](power-and-battery.md).

## power routes

the complete positive path includes `PACK_POS_RAW`, `BAT_PROT_VIN`,
`BAT_PROT_FET_COMMON`, `BAT_PROT_SENSE`, and `PACK_POS_FUSED`.
the return includes `PACK_NEG_RAW`, `BMS_SENSE_N`, `BMS_FET_COMMON`, and
`FG_VSS`, followed by the center gauge shunt.

`BAT_PROT_SENSE` and `BMS_SENSE_N` currently lack the expected power-class
patterns. the gauge/protector's filtered SRP/SRN branches are different
from the shunts' main current paths.

for each path, identify the component pads carrying the load, narrow sections,
shared/parallel traces, vias, and connector contacts. use copper thickness,
length, actual current, voltage drop, and surrounding copper in the review.


parallel copper and heavier copper can help, but both need a real connection
and a checked current-sharing path. a single via at a bottleneck can undo
the benefit of a wider trace. a short pad escape also needs context; it is
not automatically safe just because it is short.

## eight-layer signal routing

the field-solved geometry is recorded in
[`manufacturing/mainboard_stackup_release.json`](../manufacturing/mainboard_stackup_release.json),
under `approved_trace_geometries`. do not use the older Hammerstad candidate
values as the approved values.

| Interface | Target | Relevant class family |
| --- | --- | --- |
| PCIe data | 85 ohm differential | DIFF_85 |
| USB3 | 90 ohm differential | DIFF_90 |
| HDMI and Ethernet MDI | 100 ohm differential | DIFF_100 |
| Reference clocks | Follow the endpoint clock requirement; current patterns include DIFF_100 | Check the specific net |
| USB2 | 45 ohm single-ended basis, with the complete differential geometry checked | USB2_45 |

outer microstrip and inner stripline need different widths. select the
approved geometry for the actual routing layer and reference planes.
the eight-layer assignment is signal / GND / signal / GND / power islands /
signal / GND / signal. a signal routed beside a power-island boundary needs
its return path reviewed.

netclass names do not enforce every aspect of impedance, return continuity,
skew, or layer choice. review `*.kicad_pro` and `*.kicad_dru` on each board
and check that their exact net-name patterns still match.

## board and cable boundaries

freeze connector placement and the [cable assembly](cables-and-connectors.md)
before routing to it. review the whole channel across both PCBs and the FFC,
including reference conductors, coupling capacitors, protection, connector
transitions, and the cable's own impedance/loss.

on the center board, keep the split pipeline's normalized net names. a
normal F8 update can sever the relationship between connector and circuit
nets. [rebuild details](build-and-verify.md#deliberate-rebuilds)

## review order for each board

1. Confirm the schematic, pad nets, footprints, layer setup, outline, and
   connector placement used for the route.
2. Review local converter loops, decoupling, shunts, sensing, and power distribution.
3. Review high-speed placement and routes, coupling, clocks, skew, and returns.
4. Route the slower control, audio, and general I/O connections.
5. Refill a copied board and compare DRC, clearances, thermals, and islands.
6. Finish assembly access, test points, reference text, and silkscreen.
7. Export and inspect fabrication outputs from the reviewed file revision.

## converter and thermal checks

check U2, U750, the system/endpoint bucks, and the left hub converters
against their actual input/output conditions and manufacturer layout guidance.
include compensation, effective capacitance under DC bias, transient
response, gate drive, inductor loss, local hot loops, and exposed-pad heat
paths. choose thermal copper/vias using actual geometry and measured load
conditions rather than a universal amps-per-via rule.

for each high-speed interface, record its required intra-pair skew,
lane-to-lane matching where applicable, channel length/loss, coupling-cap
position, layer changes, and return path. derive those limits from the exact
Mu/device/cable requirements and the approved stackup before routing.
