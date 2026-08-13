# Ducktop2 — Electronics-Correctness Review (v4, FINAL)

Generated: 2026-08-13 — net-level audit. This review covers electrical
correctness only (nets, power, integrity). Routing state is covered in
HANDOFF_ELECTRONICS_REVIEW.md §0 and is excluded here by request.

Method: schematic ERC + full sexpr netlist audit (1372 nets) vs board
(4076 pads, ref-count based — immune to the pinfunction parsing trap that
caused two false alarms in v2, both retracted below).

Independent reviewer confirmation (2026-08-13, /tmp/ducktop2-review): P0
J2300 re-verified with fresh evidence incl. the 60-pin DF40 footprint detail;
P2 MU_SIO_UART re-verified (J8 no longer exists); P3.1–P3.5 new notes
(EC VBAT, PRT_CTL pull-ups, BQ25798 BC1.2, BQ34Z100 VEN/TS, TPS25751A straps).
All verified-clean rows reproduced.

---

## 1. FIXED — J2300 radio FFC (was P0 blocker, resolved 2026-08-13)

The board's J2300 was the 60-pin `Hirose_DF40C-60DP` with a stale pin map.
Fixed by replacing the footprint with the schematic's 30-pin
`Hirose_FH12-30S-0.5SH` and assigning the schematic's pin nets:

- Footprint: `Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal`
  (30 + MP pads, 31 total; DF40 pads 31–60 removed)
- MPN `FH12-30S-0.5SH(55)`, MatingConnector/StackHeight/AbsentBoardContract
  properties set per schematic; Reference/Value corrected
- Position (62.5, 181.5) unchanged
- C7 (BQ25798 BTST1 bootstrap cap) relocated from under the FFC to
  (64.3, 136.6) — 4 mm from U2, electrically the correct home
- **Verified: 0 net conflicts board↔schematic for every ref**; spot checks
  pins 1/5/11/20/23/30/MP correct; DRC: 164 courtyards / 16 clearance /
  8 silk-edge / 1 npth, 0 shorts, 0 mask bridges

## 2. FIXED 2026-08-13 — MU_SIO_UART_RX / MU_SIO_UART_TX were dead-end nets

The Mu SIO console is the 3.3 V Super I/O UART (SIO JP3/GP41 per the
LattePanda-Mu `Electricals/Pinouts` tables). It is now exposed on on-board
test pads TP16 (SIO_UART_TX) and TP17 (SIO_UART_RX) on the rear service edge
with 100k MCU_3V3 idle pull-ups (R779/R784). The EC (STM32F407) has no spare
UART-capable pin to capture the console; probing via pads + the DNP J8 header
is the deliberate design termination.

## 3. Notes from the independent review (2026-08-13)

- **EC VBAT tied to MCU_3V3** — no EC RTC backup; the coin cell (J9) backs
  only the Mu. Confirm intentional; add VBAT diode-OR if EC RTC across pack
  swaps matters.
- **HUB_PRT_CTL2/3/4 lack pull-ups** — wire-AND of hub GPIO + TPS2553/
  TPS25810 OC/EN; other fault buses have 10k. Add 10k pull-ups for a defined
  reset state (recommended).
- **BQ25798 D+/D− NC** — BC1.2 input detection unused; IINDPM is
  firmware-only (must not enable DCD/ICO).
- **BQ34Z100-G1** — VEN floating is datasheet-sanctioned; ALERT on P2 matches
  the G1 default. Configure the gauge for the internal temperature sensor
  (TS pulled to VSS).
- **TPS25751A ADCIN straps valid**; EEPROM image must be programmed at
  assembly.

## 4. Verified CLEAN (netlist-level, no action)

- **ERC: 0 errors** (pin-not-connected and power-pin checks at error severity;
  the all-passive keyboard chain is why ERC alone can't catch floating nets)
- **Power tree complete:** VSYS → U6/U7/U1703/U750 bucks; BUCK5_SW→L4→SYS_5V,
  BUCK33_SW→L5→SYS_3V3, HUB_CORE_SW→L1700→HUB_VCORE, USB5_SW→L1701→
  USB_PORT_5V, MAKER_3V3_SW→L900→MAKER_3V3_CORE, BUCK_SW→L3→MCU_3V3
- **MU_12V fed correctly:** U750 (TPS552892) VOUT → caps → RS750 sense →
  MU_12V → A1 VIN (+R751/R752 divider, C763 bulk)
- **Battery chain complete:** J2 → F1 → BAT_PROT_VIN → Q11/Q12+U11 (LTC4368)
  → PACK_POS_FUSED → Q25 → BAT_CHARGER → U2 (BQ25798), with RS10 sense and
  D710→AON_OR_RAW
- **Keyboard matrix connected:** U4 ↔ R360–R383 (1k series) ↔ J310 FFC
  (rows, cols, RGB data/pwr/fault all bridged)
- **Trackpad connected:** A1 USB2_P8 ↔ R250/R251 ↔ J58 (+U62 ESD/mux)
- **EC boot chain sound:** HSE/LSE crystals + load caps, NRST (pull-up, SW1,
  reset drivers), BOOT0 strap, VCAP caps
- **Differential pairs P/N-correct:** J11/J21/J12/J22/J23 USB3,
  HDMI D0–D2+CK, GbE MDI0–3
- **No multi-driver (out/out or power-out/power-out) net conflicts**
- **INTERNAL_USB_VBUS sensing cluster:** SENSE/VALID/FAULT_N/ILIM on the right
  pins (v2 alarm retracted — exact-net check is clean)
- **Board↔schematic parity: 4050/4076 pads match; the 26 exceptions are all
  J2300**

## 4. Notes

- `lib_footprint_mismatch` severity is `ignore` in the project (set during DRC
  cleanup). Re-enable after the J2300 re-sync. It checks footprint geometry,
  not pin nets — it never would have caught the J2300 issue.
- U10 (BQ34Z100) VEN pin is no-connect — confirm acceptable for the G1.
- Retractions from v2 (parsing bug, now verified correct): MU_12V *is* fed;
  keyboard and trackpad *are* connected.

## Pre-fabrication sequence

1. Update PCB from Schematic → confirm J2300's 26 nets change (and nothing else).
2. Route signals; fill inner planes; DRC with copper.
3. Re-enable lib-footprint parity.

---

## 5. User-Functionality review (independent, 2026-08-13)

/ tmp/ducktop2_review/REPORT_USER_FUNCTIONALITY.md — requirements verification,
20 user expectations. Summary:

DELIVERED (hardware, EC-firmware pending): power-on/recovery-from-dead-battery
(QON + AON OR), reset, lid, keyboard (65-key contract verified vs fabricated
board), trackpad, all 5 USB-C (2× PD dual-role + 3× source-only with
charger-refusal), off-state charging, battery gauge, audio (jack auto-mute,
fail-safe muted), fan, OLEDs, Wi-Fi/BT/GbE/HDMI, NVMe x4, maker isolation,
DB-removal defaults.

GAPS:
- P0-1 (mainboard J2300) — FIXED 2026-08-13 (FH12-30S swap + pin resync,
  see §1). Pads fully on-board (max y 182.9).
- P0-2 (radio daughterboard J1 = DF40C-60DS) — FIXED 2026-08-13. DB J1 is
  now FH12-30S-0.5SH (30+MP), pin map matches mainboard J2300 net-for-net
  (DB pin 30 grounds the MB RADIO_DB_PRESENT_N pull-up as the presence
  detect), DB-local 3V3 regulator from RADIO_DB_5V, DB verify gate passes.
- P1-1 (EC update port) — FIXED 2026-08-13. Rear USB-C J73 UFP/DFU port
  (USBLC6 ESD, 5.1k CC Rd, 22R series D+/D-) with EC_DFU_SEL/BOOT0 forcing
  the USB mux onto the port. EC DFU firmware is the remaining firmware-side
  follow-up.
- P2-1 (always-on S5 load) — FIXED 2026-08-13. DB rails gated behind
  RADIO_DB_PWR_EN (EC, PG/FAULT contract); headphone amp /SD shutdown via
  MU_HOST_ACTIVE (0.4 uA in S3); retired hub is out of the design; EC's own
  always-on 3.3 V is intentional.
- P2-2 (Mu FAN1_TAC unconnected) — FIXED 2026-08-13. FAN_TACH (fan FG,
  open-collector, 8.2k MCU_3V3 pull-up) now feeds A1 FAN1_TAC (SIO GP52
  tachometer input per the Mu pin tables).
- P3-2 (SLP_S3 unobserved) — FIXED 2026-08-13. A1 SLS_S3 (SoC GPD5, high in
  S0/S3 per the Mu pin tables) observed on the TCA9539 spare input with
  R783 100k default-low pull-down (absent Mu reads off).
- P3-1 (MU_SIO_UART dead-ends) — FIXED 2026-08-13. See §2 (TP16/TP17 probe
  pads + idle pull-ups; EC has no spare UART pin).

Verified clean (no alarms): TPS26630 floating B_GATE/DRV correct; TPS25751A
DRAIN thermal island correct; U170 gate pairing valid; keyboard FFC reversed
pin map intentional (n→31−n contract).
