# Ducktop2 Thermal Plan (8L) — copper and via strategy

Status: DESIGN PLAN — defines the copper budget BEFORE planes are drawn so
routing never has to re-invent power/thermal copper. Values are first-pass
engineering; refine with the real cooling stack measurements (gate 7/14).

## Heat sources and where they sit

| Source | Power (class) | Board zone | Cooling path |
|---|---|---|---|
| Mu module (N305/N100, 6-35 W TDP) | 15-35 W | board (176-241, 6-83) | coldplate/TIM -> heatpipe -> fin -> blower (chassis) |
| TPS56637 x4 (U6/U7/U773/U1703) | ~0.8-1.2 W each at load | U6 (145,91), U7 (135,30), U773 (238,104), U1703 (171,28) | board copper + chassis air |
| TPS552892 (U750, 12 V/3.33 A) | ~1 W | U750 (157,79) | board copper |
| BQ25798 (U2 charger) | ~1 W at charge | U2 | board copper |
| USB7206C hub (U1700) | ~0.7 W | (245,47) | board copper |
| NVMe (J10) | 2-5 W peak | under M.2 card | card -> chassis coldplate contact (gate 7) |
| RTL8111H (U500) | ~0.5 W | (325,97) | board copper |

## Board-side copper requirements

### VRM thermal relief (U6/U7/U773/U1703, TPS56637)

- VIN/VSYS and GND pours extend >= 4 mm beyond each IC with thermal-via
  arrays: 9-16 vias (0.6/0.3) around each converter, GND vias stitched to
  L2/L4/L7.
- Output rail (SW -> inductor) copper: >= 3 mm wide path to the inductor
  pads; keep the SW node copper moderate (reduce capacitance) but sized for
  the ripple current.
- Inductor (XAL7070) pads: solid pours on both pads; no thermal spokes on
  the high-current pad side.

### U750 (TPS552892)

- Same treatment as the bucks; the output 12 V rail to the Mu connector
  needs >= 2 mm effective copper (via farm at both ends) for 2.8 A.

### U2 (BQ25798, charger)

- VSYS/charger node copper >= 3 mm; GND EP vias 9+; the pack current path
  (J2 -> F1 -> protector -> charger) is a power trace/plane pair on L5
  island + vias at each end.

### U1700 (hub)

- EP thermal vias per the footprint's ThermalVias pattern; local pour.

## Zones to keep free of thermal-blocking geometry

- Under the Mu coldplate (176-241 x 6-83): no tall copper features; the
  coldplate carries the heat — board side just needs GND continuity and the
  module's mounting-plane clearance (keepout already enforced).
- Under the M.2 card (196-276 x 114-136): card-mounted heat sinks may
  contact the chassis; keep the board-side height < 1.4 mm (already the
  placement rule).

## Via rules of thumb (all 0.6/0.3 through)

- 1 via ≈ 0.5-0.8 A of thermal transfer (4 A per via farm of 6-8).
- Every GND EP of a power part: 9-16 vias into L2 + L7.
- GND stitching across the board: 1 via per ~25 x 25 mm grid on the plane
  islands (L5 power islands also get stitched to L2/L7 GND via pairs).

## Open items

1. Cooling stack measurements (gate 7): exact coldplate/fin/blower geometry
   and airflow — may force a heatpipe-side design change, not a copper one.
2. NVMe card chassis contact (gate 14): if no contact, board-side copper
   under the card area should carry the card heat — decide before routing
   the L5 island shape there.
3. Ambient/soak targets for the VRMs at 35 W Mu + NVMe write — set the
   final thermal-via counts.