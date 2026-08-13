# Independent Review — 2026-08-12

Method: read board via IPC backend + fresh kicad-cli pcb drc (error severity:
263 violations = 199 courtyards, 51 clearance, 8 copper_edge, 4 mask-bridge,
1 NPTH-in-courtyard; 0 shorts — consistent with committed 871 total). All
positions below are KiCad board coords (origin top-left, y down).

## CRITICAL

### F1 — FIXED 2026-08-13 — A1 Mu carrier is non-mountable
A1 now sits at (181.3, 45) rot 90 with all pads on-board (0
copper_edge_clearance items). Standoffs H1/H2 were re-placed onto the module's
M2 hole datums: H1 (238.3, 76.8), H2 (238.3, 13.2) — RETENTION_AND_MOUNTING_RELEASE.md
updated to match. Remaining A1-courtyard overlaps are the low-profile AC caps
under the module's 8 mm standoff (pre-existing pattern).

Original finding (as reviewed):
Pads, mounting holes, and module body are off-board, and standoffs H1/H2 are
orphaned.

- Location: A1 (180,30) rot 90, fp Module_LattePanda:LattePanda_Module_H8.0mm_Horizontal
- Evidence: A1 pad row maps to global x≈168–184, y −7.5..+0.6 (pads 1–17+,
  plus NPTH at (180,−4.4), MP pad at (168,−7.5)); module body bbox y
  −8.55..68.55. DRC copper_edge_clearance items = 6× "Pad 12–17 of A1"
  against the top edge segment. Module screw-hole features (local ±31.8,57)
  land at (237,−1.8) (off-board) and (237,61.8) at the new position.
- Standoffs: H1 (162.2,175.55), H2 (162.2,111.95) solve exactly for A1's old
  position (105.2,143.75,90) (pre-e48ad3c); they were not moved with the
  module. They don't even overlap A1's courtyard now, so the kicad_dru
  "H1/H2 × A1 courtyard overlap" allowance is dead weight.
- Fix: re-place A1 south by ≥9 mm AND re-place H1/H2 onto the module's two
  hole positions, as one coordinated move (or revert the Mu move). Everything
  downstream of the Mu (PCIe, USB-C, cooling) depends on this.

## HIGH

### F2 — J40 (Wi-Fi E-key socket) was moved on top of three components
- Location: J40 (235.45,158) rot −90; even-pin row at x=227.9, y 158–175.
- Evidence (DRC itemized): U170 (SN74LVC3G34 VSSOP-8 at (228.5,165.59))
  pads 6/7/8 touch/overlap J40 pins 32/34/36 — actual 0.0000 mm ×2 (pins are
  <no net> so no short is reported, but the pin metal sits on U170's pads);
  R2316 (0603 at (228.5,160.05)) pads touch pins 8/10/12 (actual
  0.0/0.0/0.075); U46 (at ~(232.7,163.1)) pads 0.105/0.124 mm from pins
  17/19. All three bodies are under the socket body (x 227.85–240.1). Plus
  4× solder_mask_bridge (J40 pins ↔ R2316/U170). 14 of the 51 clearance items
  + all 4 mask-bridge items are this cluster.
- Fix: move U170, R2316, U46 (and re-check anything else under J40) clear of
  the socket body + pin field; or reposition J40.

### F3 — FIXED 2026-08-13 — Keyboard FFC connector J310 pad field overlaps its series resistors

R374/R375 moved west of the FFC pad field (R374 (315.5,50.8), R375 (315.5,48.5));
R386 stays at (329.5,41.5). All J310 pad-field clearance items are cleared
(board-wide clearance count is now 0); the resistors remain inside J310's
connector-body courtyard, which is inherent to keeping the series terminations
near the connector.
- Location: J310 (320,50) rot −90 (FH12-30S, pads at x=321.85, y 40.85–59.15);
  R374 (323,53), R375, R386.
- Evidence: 9 clearance items — R374.1/2 ↔ J310 pads 19–24 (0.025–0.118 mm),
  R375.2 ↔ pads 16–18, R386.2 ↔ pads 13–15 (0.03–0.042 mm). Resistor pads
  sit ~1.1 mm from the FFC pads with y-overlap — solder-bridge hazard on the
  keyboard matrix nets.
- Fix: move the three resistors off the connector pad field (east/west), keep
  ≥0.15 mm + mask web.

### F4 — J2300 hangs its pads off the bottom edge; radio DB can't mate
- Evidence: all 30 signal pads at y=184.85 (pad half-height 0.65 → pads reach
  y≈185.5; board bottom = 185); 2× copper_edge_clearance on J2300 MP pads
  (actual 0.0/0.47). Connector body overhangs to y≈187.5.
- Mating contract: radio DB 01_core.kicad_sch J1 is still
  Conn_02x30_Odd_Even / DF40C(2.0)-60DS-0.4V (60-pin 0.4 mm B2B); mainboard
  is 30-pin 0.5 mm FFC. 30 ≠ 60, FH12 ≠ DF40 — cannot mate. Also the 30-pin
  set carries no 3V3 rail and no I2C/SPI (only 5V, UARTs, GPIOs, USB) —
  confirm the DB's local-supply plan covers GNSS/radio needs.
- BOM trap: J2300 properties on the PCB are still MPN =
  DF40C-60DP-0.4V(51), MatingConnector = DF40C(2.0)-60DS-0.4V(51) — a BOM
  run would order the wrong part.
- Fix: move J2300 north ≥1.5 mm so pads are fully on-board; update
  MPN/MatingConnector to FH12 parts; redesign the radio DB connector to a
  30-pin FH12 and publish the pin map (do not touch
  radio_daughterboard/radio_daughterboard.kicad_pcb — it's the DB's job).

### F5 — Mainboard mounting holes H10–H13 contradict the released retention doc
- Board: H10 (355.56,182.55), H11 (240.46,182.55), H12 (355.56,147),
  H13 (240.46,147.05).
- Doc (mechanical/RETENTION_AND_MOUNTING_RELEASE.md table): H10 (20,28),
  H11 (110,10), H12 (180,10), H13 (20,115). H14–H17 match the board.
  Chassis bosses built from the doc will miss H10–H13.
- Also: H17 (300,175) NPTH sits inside J41's courtyard (SSD1306 OLED at
  (310,155)) — DRC npth_inside_courtyard. Boss/screw vs OLED conflict.
- Fix: pick canonical hole positions (doc or board) and update the other;
  relocate either J41 or H17.

### F6 — Impedance net classes are NOT committed as claimed
- Evidence: .kicad_pro net_settings classes are PCIe_85R (0.12/0.15 diff),
  USB3_90R_PROVISIONAL (0.12/0.15), HDMI_100R_PROVISIONAL (0.12/0.15),
  ETHERNET_MDI_100R_PROVISIONAL (0.12/0.15), USB2_90R (0.15 SE). The classes
  named in the handoff (DIFF_85/DIFF90/DIFF100/USB2_45) do not exist; the
  board file contains zero (net_class … (add_net …)) assignments.
  verification/IMPEDANCE_VERIFICATION_2026-08-01.md targets are 0.29/0.80,
  0.26/0.61, 0.215/0.68, 0.262 mm. gen/setup_net_classes.py exists with the
  correct values but has not been applied.
- Fix: run gen/setup_net_classes.py (non-dry-run) to create
  DIFF_85/DIFF90/DIFF100/USB2_45 with the doc geometries and assign all
  high-speed nets, then re-sync the board before any routing.

## MEDIUM

### F7 — Ethernet notch is an unreleased mechanical contract change
- Edge.Cuts: right-edge recess x 352.78–358, y 88–107 ✓ (verified segments).
  But mechanical/floorplan_revD_current.json still names the outline
  "358x185, left fin-stack notch" (left notch was removed in 32a29a8, right
  notch added in a283abc), and MECHANICAL_MEASUREMENTS_AND_GATES.md items
  9/10 (jack recessed mounting, hole/boss pattern) are open gates. J500 body
  extends 2.1 mm into the notch by design (mid-mount) — chassis/panel cutout
  must be released.

### F8 — 51 clearance items are real, scattered pad-pad proximity
Itemized by cluster (F2 and F3 excluded): U2011↔R2018 (0.025/0.025/0.139),
D1820↔R372 (0.07×2), C501↔C513 (0.025, PCIe_85R), R700↔R701 (0.05×2),
C39↔Y500 (0.13×2), R504↔U51.7 (0.095), R2043↔R2044 (0.05),
U45.24↔R2044.2 (0.04), R2306↔C506 (0.015 — tightest on board), R505↔R506
(0.136), R2058↔C1760 (0.085), C921↔R902 (0.10), C208↔C205 (0.144),
C2061↔C2060 (0.105), Q701↔R2347 (0.115), R178↔C40 (0.12), R1790↔C2027
(0.05), R774↔R778 (0.05), plus netclass-rule marginals C709↔C720 (0.295 vs
0.3), C708↔C712 (0.20 vs 0.3), C422↔C725 (0.42 vs 0.5), RS10↔U11 (0.47 vs
0.5), R733↔R731 (0.15 vs 0.3). All are different-net pairs with gaps < rule;
the ≤0.05 mm ones are solder-bridge hazards.
- Fix: nudge each pair apart (≥0.15/0.3/0.5 mm per class); worst first:
  R2306/C506, C501/C513, R504/U51.

### F9 — Ethernet cluster identities: handoff mislabels, design is coherent
- U500 = RTL8111H (QFN-32+EP, PCIe GbE MAC+PHY) at (325.9,97.3). U501/U502 =
  D3V3XA4B10LP-7 4-ch ESD arrays (UDFN-10); magnetics inside the JXD1-1022NL
  jack, so PHY→ESD→magjack is a valid MDI chain. C501 is the Mu↔RTL8111H
  PCIe TX AC cap. J500 pins (x≥329.07) vs U501/U502 pads (x≤327.6) ≈ 1.5 mm —
  MDI routing feasible but tight.
- Concern: Y500 (25 MHz crystal, ETH_XO) at (342.13,127.9) is ~35 mm from
  U500 — long crystal loop; consider moving it adjacent to the PHY.

### F10 — M.2 relocations: verified mostly OK
- J10 card (x≈204–284, y≈104–128) vs U4: 12 mm clear ✓; vs U60: clear ✓;
  vs Q60: 0.55 mm under card shadow but ≥3 mm vertical clearance — flag for
  3D check. J40 card vs J10 card: no overlap ✓. H3 ≈ 80 mm from J10 pin row
  ✓ 2280; H4 ≈ 30 mm from J40 pin row ✓ 2230.

### F11 — copper_edge_clearance 8 = A1 ×6 (F1) + J2300 MP ×2 (F4)
Nothing near the ethernet notch violates edge clearance.

## LOW / INFORMATIONAL

- F12 — silk_edge_clearance 8 and text_height 3: corner silk text <0.8 mm
  and silk near edges; cosmetic, pre-existing.
- F13 — The 199-group (courtyards_overlap / lib_footprint_mismatch /
  silk_overlap / silk_over_copper) is byte-identical in count to the
  2026-07-20 snapshot — no regression; the 16 courtyards_overlap at (180,30)
  are A1-vs-underneath parts (F1 fallout).
- F14 — Board has 91 keepout zones (tracks/vias not_allowed, e.g. under the
  Mu area) and no copper zones/vias/tracks at all — routing must respect
  keepouts; the L1-over-L2 no-via plan is blocked by F6.
- F15 — Handoff fact-checks: H16 is (342,120) not (342,117.5); "clearance 51
  mostly U501/U502" → actually 0 items; "DIFF_85/DIFF90/DIFF100/USB2_45
  committed" → not present; U500/U501/U502 descriptions → see F9.

## Routing gate

Do not start routing until F1, F2, F3, F4, F6 are resolved (F6 alone
invalidates every impedance-critical trace).
