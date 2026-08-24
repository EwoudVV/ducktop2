# Ducktop2 High-Speed Routing Plan — 2026-08-01

Companion to `verification/IMPEDANCE_VERIFICATION_2026-08-01.md` (geometries)
and the review items P1.4/P1.6 (skew > Mu limits). The impedance-driven net
classes are already committed to `ducktop2.kicad_pcb`
(`gen/setup_net_classes.py`).

## Net Classes (committed to the board)

| Class | Target | Width | Spacing | Members |
| --- | --- | --- | --- | --- |
| `DIFF_85` | PCIe Gen3 85 Ω diff | 0.2085 mm | 0.1524 mm | 38 nets (NextPCB interim 80 Ω solve; 85 Ω reply pending) |
| `DIFF_90` | USB 3.x 90 Ω diff | 0.1796 mm | 0.2032 mm | 50 nets (NextPCB approved) |
| `DIFF_100` | HDMI + Ethernet 100 Ω diff | 0.1521 mm | 0.254 mm | 26 nets (NextPCB approved) |
| `USB2_45` | USB 2.0 45 Ω SE | 0.2248 mm | — | 37 nets (NextPCB approved) |
| `Default` | base rules | 0.25 mm | clr 0.2 mm, via 0.6/0.3 | everything else |

All high-speed pairs route on L1 referenced to the solid L2 GND plane. No vias
on differential pairs (L2 is the uninterrupted return path).

## 2026-08-24: NextPCB approved geometry (fab field-solve)

NextPCB's engineers field-solved the stackup (report on file in
manufacturing/mainboard_stackup_release.json). L1-microstrip widths/gaps in
the table above are their numbers. For **L3 (stripline over L2/L4)** the
fab geometries are: 90 Ω diff w=4.37 mil (0.111) / s=8.00 mil (0.203);
100 Ω diff w=3.59 mil (0.091) / s=10.00 mil (0.254); 45 Ω SE w=5.17 mil
(0.131); 50 Ω SE w=4.06 mil (0.103). Routing impedance pairs on L3 uses
these values. PCIe 85 Ω: their report gave an 80 Ω solve (within PCIe CEM
85±15%); a one-line follow-up for the exact 85 Ω geometry is pending before
the PCIe pairs are routed.

## 2026-08-13: 8-layer stackup

The board moved to 8 copper layers. The outer microstrip interfaces keep the
2116 prepreg (h=0.125 mm, Dk=4.2) geometry of the 6L release, so every
geometry in this plan is unchanged:

| Layer | Assignment |
| --- | --- |
| L1 F.Cu | signals — impedance-critical microstrip over L2 |
| L2 In1.Cu | GND, solid |
| L3 In2.Cu | signals — GND/GND stripline (L2 above, L4 below) |
| L4 In3.Cu | GND, solid |
| L5 In4.Cu | POWER islands (VSYS, SYS_5V, SYS_3V3, MCU_3V3, MU_12V, USB_PORT_5V, ...) |
| L6 In5.Cu | signals — PWR/GND stripline, general routing |
| L7 In6.Cu | GND, solid |
| L8 B.Cu | signals — impedance-critical microstrip over L7 (same geometry as L1) |

Rules:
- Impedance-critical pairs route on L1 or L8 (identical geometry), or L3
  (clean GND/GND stripline). L6 is for general routing and must not carry
  impedance-critical pairs unless the L5 PWR island above is unbroken for
  the whole run.
- No differential-pair vias; layer changes (if ever needed) switch between
  L1 and L3 with a GND stub via adjacent, and only after a field-solver pass.
- L5 PWR islands: keep island boundaries clear of L6 impedance runs; the
  power budget (trace/plane widths per rail) is in
  `verification/POWER_PLAN_8L.md` (see power-plan task list).

## Skew Budgets (review P1.6)

| Interface | Intra-pair | Inter-pair | Source |
| --- | --- | --- | --- |
| HDMI | ≤ 5 mil (0.127 mm) | ≤ 5 mil between lanes and CLK | review: "limit 5 mil" |
| PCIe Gen3 (NVMe x4, Wi-Fi x1) | ≤ 15 mil (0.381 mm) | ≤ 15 mil lane-to-lane, REFCLK included | review: "exceeds 15 mil" |
| USB 3.0 | ≤ 5 mil | TX/RX independent | USB 3.0 spec practice |
| Ethernet MDI | ≤ 5 mil intra-pair | pairs independent | 1000BASE-T practice |
| USB 2.0 | ≤ 10 mil | — | USB 2.0 practice |

## Routing Order

1. **HDMI** (4 pairs, 100 Ω, skew ≤ 5 mil) — TCP0 connector to TPD12S015/DP mux;
   neck-downs at the connector and mux pads; keep D0-D2 and CLK together,
   same layer, no vias, matched to within 5 mil.
2. **PCIe Gen3** (NVMe x4 + Wi-Fi x1 + REFCLK, 85 Ω, skew ≤ 15 mil) — Mu LGA A1
   to M.2 M-key (J31?) and Wi-Fi slot; AC-coupling caps within 8 mm of the Mu
   socket (Mu guide, review P1.7); REFCLK pairs shortest, matched to the lane
   budget; neck-downs at the 0.4 mm LGA pitch.
3. **USB 3.0 / USB-C SS** (90 Ω) — VL822 hub DS1-4 to the two USB-C ports +
   front port; USB-C SS pairs stay on L1, 90 Ω, neck-downs at the 0.5 mm
   connector pitch.
4. **Ethernet MDI** (100 Ω) — RTL8111H to the RJ45 magnetics; 4 MDI pairs +
   REFCLK + HSI/HSO.
5. **USB 2.0 D+/D−** (45 Ω SE) — all USB2 pairs (hub, EC, maker, trackpad,
   audio, Wi-Fi); 0.262 mm traces, 10 mil length matching where routed long.
6. Remaining general routing with Default rules (0.25 mm).

## Execution Notes

- Route with the committed net classes so track width/gap auto-follows.
- Pair members per class are listed in the board file `(add_net ...)` tokens;
  `python3 gen/setup_net_classes.py --dry-run` prints the classification and
  flags any new high-speed-looking net that is unclassified (run after each
  schematic change).
- After routing: length-tune with KiCad interactive tuning; run
  `gen/check_release_candidate.py --stage fabrication` and drive DRC to zero
  (WIP item 7/10/11).
- Impedance geometries are candidates pending the NextPCB field-solver
  confirmation (`mainboard_stackup_release.json`); update the net class
  widths/spacings when the fabricator returns production values.

## Execution order (2026-08-13) — do not reorder

1. **L5 power islands** (POWER_PLAN_8L.md): draw the VSYS / MU_12V /
   SYS_5V / SYS_3V3 / MCU_3V3 / PCIE_3V3_IN / USB_PORT_5V / MAKER islands
   with >= 1.0 mm gaps. Source via farms per rail.
2. **GND pours** L2, L4, L7: solid; then board-wide GND stitching on the
   25 mm grid. Zone priority: L2 > L7 > L4.
3. **Mu fan-out** (MU_CONNECTOR_FANOUT_8L.md): escape rows on L1/L3/L6,
   via farms west (X < 177.2) and east (X > 185.4, nudging C586/C587/R1708
   if needed). The three signal layers' escapes must be registered together.
4. **Impedance pairs** (this plan's tables): route on L1 (microstrip) with
   L8/L3 as relief; length-tune per the skew budgets. No pair vias.
5. **Power + remaining signal**: all other nets, honoring the fab custom
   rules (PTH >= 0.23, NPTH >= 0.2, via >= 0.18, via-via >= 0.2, TH-TH >=
   0.4 mm) and the 0.2 mm copper-to-edge.
6. **Thermal copper** per THERMAL_PLAN_8L.md during steps 1-5 (VRM pours +
   thermal via farms are part of the island/stitch steps).
7. **Finish**: refill zones, full DRC, exception review (courtyard/silk
   backlog is a documented acceptance list), Gerbers + drill + pos.
