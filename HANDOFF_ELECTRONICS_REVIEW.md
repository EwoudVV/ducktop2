# Ducktop2 — Electronics-Correctness Review (v3, FINAL)

Generated: 2026-08-13 — net-level audit. This review covers electrical
correctness only (nets, power, integrity). Routing state is covered in
HANDOFF_ELECTRONICS_REVIEW.md §0 and is excluded here by request.

Method: schematic ERC + full sexpr netlist audit (1372 nets) vs board
(4076 pads, ref-count based — immune to the pinfunction parsing trap that
caused two false alarms in v2, both retracted below).

---

## 1. BLOCKER — J2300 radio FFC: 26 of 30 board pads on the WRONG NETS

Board vs current schematic, verified pad-by-pad (ref+pin on both sides):

- Board pin 1 = RADIO_DB_5V — schematic says GND
- Board pins 4, 7 = RADIO_DB_5V — schematic says GND
- Board pins 5, 8 = RADIO_DB_5V — schematic says RADIO_CODEC_USB_DM/DP_DB
- Board pin 9 = GND — schematic says RADIO_CODEC_USB_VBUS_DB
- Board pins 11–16 = GND / RADIO_CODEC_* — schematic says the four radio
  UART/PTT/PD/SQL signals
- Board pins 17–30 = shifted one position vs schematic (VHF/UHF/GNSS/DB_PRESENT)
- Board pin 23–25 = VHF/UHF TX — schematic says UHF_RF_SEL / GNSS_UART_RX/TX
- Board pin 30 = RADIO_VHF_PD_N_DB — schematic says RADIO_DB_PRESENT_N

**Impact: the radio daughterboard is completely miswired when routed as-is —
VHF, UHF, GNSS, codec-USB, DB power, DB-present all land on the wrong FFC
pins; RADIO_DB_5V would sit on pads the schematic grounds. Radios/GPS dead,
possible 5V→GND stress.**

**Fix:** `Update PCB from Schematic`, then re-verify J2300's pad↔pin map
(J2300 is a customized FH12-30S — update nets only, never the footprint).

## 2. MINOR — MU_SIO_UART_RX / MU_SIO_UART_TX are dead-end nets

A1 pins 10/12 connect to nothing else; the J8 debug header and nearby labels
are floating. The Mu SIO debug UART is unavailable. Not boot-blocking; wire
it or drop it deliberately.

## 3. Verified CLEAN (netlist-level, no action)

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
