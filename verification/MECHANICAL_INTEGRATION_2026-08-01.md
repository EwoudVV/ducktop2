# Mechanical Integration Analysis — 2026-08-01

Closes review OPEN items: battery/trackpad floorplan overlap (accepted by
design decision) and IM68A130 bottom-port mic acoustic opening (analyzed;
requirements + placement actions below).

## Trackpad / Battery Overlap — ACCEPTED (design decision)

The review OPEN item "140 × 105 mm trackpad overlaps center cell" is
**accepted as necessary by the owner (2026-08-01)**. The floorplan
(`docs/mechanical.md`) keeps the front battery band outside the motherboard
outline; the trackpad (140 × 105 mm) and the 100 × 60 × 3 cell stack share the
front-band footprint. No placement change. Closing the item requires only the
final Z-stack proof in the enclosure step (WIP item 12).

## IM68A130 Bottom-Port Microphone — analysis

### Placement (MK430)

- Mic at (40.0, 110.0) on the 358 × 185 mm board.
- The board has a **51 × 52 mm fin-stack notch on the left edge (x 0–51,
  y 124–176)**. The mic is **14 mm below the notch and inside its x-range**
  (x = 40) — directly adjacent to the blower/fin-stack zone.

### Noise-source distances (top side, all on L1)

| Ref | Part | Distance | Concern |
| --- | --- | --- | --- |
| U410 | PCM2900C USB audio codec | 4.7 mm | digital I/O; **pad-collides with MK430 (DRC short)** |
| R410/R432/R435/C455/C456 | passives | 4.6–7.5 mm | benign |
| U431 | TLV9061 op-amp | 11.5 mm | benign |
| U430 | LP5907 LDO | 12.8 mm | benign |
| U402 | TPS2052B switch | 18.4 mm | switching current |
| L421 | inductor | 20.2 mm | switching dV/dt field |
| L420 | inductor | 39.3 mm | switching dV/dt field |
| U420 | TPA2012D2 Class-D amp | 74.1 mm | OK (far) |
| J420 | speaker connector | 73.4 mm | OK |
| Blower/fin stack | chassis, notch region | ~15–40 mm | **adjacent — primary concern** |

### Findings

1. **Blower proximity:** the mic port is ~15–40 mm from the blower/fin-stack
   zone (notch above it). The sealed acoustic channel must route away from the
   notch (e.g. down and out through the left base wall or palm rest), or the
   mic must move. This is the mechanical-integration item the review flagged
   as "not yet proven".
2. **MK430 / U410 pad collision:** from the placement pass
   (`PLACEMENT_REVIEW_2026-08-01.md`, manual list). When separating them, keep
   the codec clear of the mic's port direction.
3. **Port geometry:** the IM68A130's 0.6 mm bottom acoustic port sits inside
   the pad-4 ground ring (audited rule in `ducktop2.kicad_dru`). The PCB hole
   is part of the footprint; the bottom side is routing-only, so nothing
   mechanical blocks below — but no copper/traces may be routed under the
   port region (footprint ground ring enforces this).
4. **Acoustic channel requirements (for enclosure step):** sealed channel from
   the PCB hole to the exterior, no gaps to the blower duct, ≥ 5 mm from the
   cooling airflow, acoustic seal around the mic-to-chassis interface.

### Actions

- Placement: resolve MK430/U410 collision (keep ≥ 0.25 mm; prefer moving the
  codec-side passives, keep mic fixed if the chassis opening is fixed).
- Chassis: design the sealed mic channel with the blower exclusion above;
  verify the opening location in the enclosure validation (WIP item 12).
- No PCB change is required for the port itself.
