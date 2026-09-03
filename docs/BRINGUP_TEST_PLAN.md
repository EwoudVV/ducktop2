# Bring-up test plan — 2026-09-02

Goal: prove every PCB is electrically correct BEFORE any board is
connected to another or to the battery. Each stage has a pass criterion;
do not advance until it passes. Equipment: DMM, oscilloscope, current
limited bench supply, ESD strap.

## Stage 0 — bare boards (before assembly)

For each of the four boards:

1. Visual: mask defects, silks legibility, drill burrs, board outline vs
   the chassis cutouts (hinge notches on left/right).
2. **Netlist continuity test** against the IPC-D-356 netlists in
   `verification/`:
   - `left_io_ipc356.ipc`, `right_io_ipc356.ipc`, `bms_ipc356.ipc`,
     `ducktop2-center_ipc356.ipc`
   - The file lists every pad with its net and XY. Two probes + DMM
     continuity:
     a. same-net pads: expect < 1 ohm between every pad pair on a net
        (spot-check: at least first/last pad of each net)
     b. adjacent different-net pads: expect open
   - This catches etch opens, via failures (barrel continuity), and
     mask/etch shorts before a single component is soldered.
3. Mark the board stage-0-pass, date it.

## Stage 1 — assembled, unpowered

1. Solder inspection under magnification: every IC orientation (U15/U15B
   LTC4418 pinouts, Q25 ship FET), every FPC connector seating.
2. **Rail resistance map, board unpowered** — DMM diode mode, both
   polarities, record values. The boards carry dedicated test points so
   nothing needs to be probed at a live pin:
   - BMS: TPB1 PACK_POS_RAW, TPB2 BAT_PROT_VIN, TPB3 PACK_POS_FUSED,
     TPB4 BAT_PROT_FET_COMMON, TPB5 BAT_PROT_GATE, TPB6 BAT_PROT_CGATE,
     TPB7 PACK_FAULT_N, TPB8 PACK_RETRY_PULSE, TPB9 MCU_3V3,
     TPB10 BMS_AVDD, TPB11 BMS_VDD, TPB12 BMS_SRP, TPB13 BMS_SRN,
     TPB14 BMS_PRES, TPB15 BMS_LD, TPB16 FG_VSS (scope ground)
   - BMS: PACK_POS_RAW->FG_VSS, PACK_POS_FUSED->FG_VSS, BMS_AVDD->FG_VSS,
     MCU_3V3->FG_VSS, each cell tap -> FG_VSS
   - Center: VBUS_COMBINED->GND, VSYS->GND, USB_PORT_5V->GND, SYS_3V3->GND,
     MCU_3V3->GND, SEL_STAGE2->GND, each Mu socket rail -> GND
   - Left/right: VBUS raw -> GND, USB_PORT_5V -> GND, 3V3 rails -> GND
   - A dead short (near 0 ohm both ways) = find it before power. Compare
     the diode readings between boards: identical designs should read
     alike; an outlier localizes a bridge.
3. **FPC cables**: continuity pin-to-pin along each cable (conductor N to
   conductor N), then cable-in-place check: with the cable seated in both
   connectors, verify board net N on side A reaches the contract's
   expected net on side B (the reversed maps in
   `verification/FPC_CABLE_SPEC_2026-09-02.md`).
4. Orientation sanity: the 3 cables are straight-through Type-A — if a
   cable refuses to seat flat or needs a twist, STOP and re-check the
   connector rotations.

## Stage 2 — first power, one board at a time, current limited

Rules: bench supply current limit at ~10x expected idle (start 50 mA),
external fuse in the lead, scope across the supply terminals for inrush.

1. **BMS first** (it wakes without the pack):
   - Bench supply on the cell-tap connector at 12.0 V (3S nominal), limit
     50 mA, fused.
   - Scope each rail: BMS_AVDD, MCU_3V3 — verify DC level and ripple.
   - Verify the protector FETs are OFF (gate nodes low) — the BQ77915
     must not enable the pack until it sees valid cells.
   - 5 min soak, finger/IR thermals. Expect: barely warm.
2. **Center** (no Mu inserted yet):
   - Power via the AUX jack or PD1 VBUS path at 9-12 V, limit 200 mA.
   - Scope every rail BEFORE inserting the Mu: VBUS_COMBINED, VSYS,
     USB_PORT_5V, SYS_3V3, MCU_3V3, and the Mu socket pins (3V3/5V/VBUS).
   - Verify the selector cascade: with one source present, USB_PD_SELECTED
     appears; remove it, feed AUX, verify the swap on the scope.
   - Then, and only then, insert the Mu. Re-check rails under Mu idle.
3. **Left/right**: 5 V bench on the 5 V rail, limit 100 mA; verify hub
   power-up and port VBUS switches off by default.

## Stage 3 — staged integration

1. BMS + real cells (external 5 A fuse in series), no load: pack voltage
   at the protector output, cell taps within 50 mV of each other, pack
   positive fused.
2. Trigger test: with the pack connected through the bench-supply
   series-limit, pull a fake over-current (briefly) and scope the
   protector gate — it must open. Reset works.
3. Connect FPC-1 (left<->center) with both boards powered OFF; power the
   center only; verify the left board's rails come up through the cable;
   then power the left.
4. Same for FPC-2, then FPC-3 (BMS last — it is the power source).

## Stage 4 — scope checklist (ongoing)

- Rail ripple at every regulator: < 1% of rail at idle, < 3% under load.
- Charger: scope the charge current shunt node during a charge cycle.
- USB: after enumeration, scope DP/DM lines for activity; full eye
  verification is out of scope without a proper capture card, but
  gross signal integrity (ringing, flat-lining) is visible.
- Any rail that sags when a downstream board connects = a wiring/fuse
  problem, not a design one — re-check Stage 1 resistance map.

## Pass/fail gate

A board advances to the next stage only when the current stage passes.
Never connect two boards, or the pack, to a board that has not passed
its isolated bring-up.
