# USB-A Port Cluster Routing Plan (2026-08-24)

Status: PLAN — the cluster is placed and netlist-wired; the routing phase
(3,307 unrouted board-wide per pcbnew; the cluster is part of that work) is not yet complete. This
document captures the exact topology, the verified routing strategy, and the
blockers, so the routing can be finished with interactive KiCad routing or
Freerouting (Java) without re-deriving anything.

## Cluster netlist (complete, verified)

| Net | Node 1 | Node 2 | Node 3 | Node 4 |
|---|---|---|---|---|
| J24_5V_PRE | U1800.6 | C1850.1 | C1851.1 | J24.1 |
| J25_5V_PRE | U1803.6 | C1854.1 | C1855.1 | J25.1 |
| J24_ILIM | U1800.5 | R1850.1 | | |
| J25_ILIM | U1803.5 | R1851.1 | | |
| HUB_DIS5_DP | U1700.81 | U1801.1 | U1801.6 | J24.3 |
| HUB_DIS5_DM | U1700.82 | U1801.3 | U1801.4 | J24.2 |
| HUB_DIS5_TX_P | U1700.83 | U1802.1 | C1852.1 | |
| HUB_DIS5_TX_N | U1700.84 | U1802.2 | C1853.1 | |
| HUB_DIS5_RX_P | U1700.86 | U1802.4 | J24.6 | |
| HUB_DIS5_RX_N | U1700.87 | U1802.5 | J24.5 | |
| HUB_DIS6_DP | U1700.42 | U1804.1 | U1804.6 | J25.3 |
| HUB_DIS6_DM | U1700.41 | U1804.3 | U1804.4 | J25.2 |
| J24_SSTX_P | C1852.2 | J24.9 | | |
| J24_SSTX_N | C1853.2 | J24.8 | | |
| USB_PORT_5V | L1701.2 | U1800.1 | U1803.1 | (+18 more) |
| INTERNAL_USB_VBUS_VALID | R417.1 | U1800.3 | U1803.3 | (+6 more) |

## Placement (final)

- J24 (USB3-A) (4.5, 115) rot 270; J25 (USB2-A) (4.5, 137.5) rot 270.
- Support cluster: U1800 (19,120), U1801 (18,113), U1802 (22,128),
  R1850 (19,127), C1850 (13.5,122), C1851 (14,126), C1852 (14,130),
  C1853 (14.6,134), U1803 (20.5,141), U1804 (19,148), R1851 (19,145),
  C1854 (16.5,139.5), C1855 (14,143).
- Hub U1700 at (261.18, 38.38), VQFN-100 12x12 mm, pins on 0.4 mm pitch.

## Verified routing strategy

1. **Long runs on B.Cu.** The B.Cu layer is empty of components (only ~360
   TH pads in the whole board block it). All hub<->cluster runs and the
   power/control runs should travel on B.Cu with vias at each end.
2. **Hub fanout**: hub SS/D pins are at y=32.54 (pins 81-87) and y=44.22
   (41/42), x 261.4-264.0. A clean via band exists at y=29.5 across
   x 258-266. Fan out to vias at 1.2 mm pitch: 81->267.4, 82->266.2,
   83->265.0, 84->263.8, 86->262.6, 87->261.4, 42->268.6, 41->269.8.
   This yields zero via-via shorts.
3. **Cluster-side vias**: B.Cu near the cluster is blocked only by the J24
   SH pads ((3.55,108.6),(3.55,121.4),(9.75,121.4),(9.75,108.6)) and J25 SH
   ((8.05,131.1),(8.05,143.9)). Place vias >= 1.2 mm from any pad.
4. **Pad rotation accounting (critical!)**: J24/J25 pads carry their own
   270-degree pad rotation on top of the footprint's 270. World-space pad
   sizes DIFFER between the receptacles (verified 2026-08-26 via pcbnew):
   - J24 (USB3-A): signal pads **1.6 mm x 0.7 mm** in world coords.
   - J25 (USB2-A): signal pads **3.0 mm x 1.3 mm** in world coords.
   Any tooling must add footprint rotation + pad rotation AND use the
   per-connector world bounding box, or it will place vias/tracks inside
   the larger J25 pads.
5. **Widths**: SS pairs (HUB_DIS5_TX/RX, J24_SSTX) use 0.1796 mm
   (DIFF_90 class); D+/D- (HUB_DIS5_DP/DM, HUB_DIS6_DP/DM) 0.2248
   (USB2_45); VBUS/power 0.4 mm; ILIM/control 0.25 mm. The project
   min-track floor is 0.09 mm (`ducktop2.kicad_pro`), so no DRU override
   is needed for class widths below 0.2 mm.

## Blockers / why scripted routing stopped

- Freerouting does not converge on this board (handoff decision); the
  manual/interactive finish below is the approved path.
- Scripted candidate-path routing connected most nets but could not reach
  zero shorts: fine-pitch fanout (0.4 mm hub pins, 1 mm J24/J25 pads) plus
  the dense cluster left no room for the simple L/detour candidate set.
  Best attempt (14 iterations): all local cluster nets + hub fanout + most
  B.Cu long runs, but 11 shorts remained, all inside the cluster footprint.

## Recommended finish

Use interactive KiCad routing (B.Cu for long runs, F.Cu stubs, via fanout
per above) or install Java (e.g. `brew install openjdk@21`) and run
Freerouting with the DSN export. After routing: expect DRC to drop to the
pre-routing allowlist (167 courtyards + silk) with 0 shorts/clearances, and
the release gate's "Unrouted" item to clear.

## Verify after routing

- `python3 gen/check_release_candidate.py` (release gate)

J24/J25 SH pads are GND nets (verified in the current sync; the earlier
"no net" note predates the J24 SH pin contract).