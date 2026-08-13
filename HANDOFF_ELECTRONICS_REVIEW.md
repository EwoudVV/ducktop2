# Ducktop2 — Electronics-Correctness Review (v2)

Generated: 2026-08-13 (revised after full schematic-vs-board net audit)

This review hunts the electrical bugs that survive routing — wrong nets,
broken connections, dead rails — not placement cosmetics.

---

## VERDICT: ONE BOARD-KILLING DEFECT FOUND (fix before routing)

### 1. J2300 (radio daughterboard FFC) — 26 of 30 pins on the WRONG NETS

The board's J2300 pad nets do not match the current schematic.

| Board pad | Board net (WRONG) | Schematic net (correct) |
| --- | --- | --- |
| 1 | RADIO_DB_5V | GND |
| 4 | RADIO_DB_5V | GND |
| 5 | RADIO_DB_5V | RADIO_CODEC_USB_DM_DB |
| 8 | RADIO_DB_5V | RADIO_CODEC_USB_DP_DB |
| 9 | GND | RADIO_CODEC_USB_VBUS_DB |
| 11 | GND | RADIO_VHF_UART_RX_DB |
| 13 | GND | RADIO_UHF_UART_RX_DB |
| 15 | GND | RADIO_VHF_PTT_N_DB |
| 17 | RADIO_CODEC_USB_* | RADIO_VHF_PD_N_DB |
| 19 | RADIO_CODEC_USB_* | GND |
| 21 | GND | RADIO_UHF_SQL_DB |
| 23 | RADIO_VHF_UART_TX_DB | RADIO_UHF_RF_SEL_3V3_DB |
| 24 | RADIO_VHF_UART_TX_DB | GNSS_UART_RX_DB |
| 25 | RADIO_UHF_UART_TX_DB | GNSS_UART_TX_DB |
| 27 | GND | GNSS_RESET_N_DB |
| 28 | RADIO_VHF_PTT_N_DB | GNSS_PPS_DB |
| 29 | RADIO_UHF_PTT_N_DB | GNSS_EXTINT_DB |
| 30 | RADIO_VHF_PD_N_DB | RADIO_DB_PRESENT_N |
| … | (26 pads total) | |

**Effect if routed as-is:** every VHF/UHF/GNSS/codec signal and the DB power
pins land on the wrong FFC pin — the radio daughterboard is completely
miswired. Radios dead, GNSS dead, codec USB wrong, and RADIO_DB_5V shorted
onto pads that the schematic says are GND.

**Fix:** `Update PCB from Schematic` (Tools → Update PCB from Schematic), then
re-verify the J2300 footprint pad↔pin map (J2300 is a customized FH12-30S
with remapped pins — do NOT replace the footprint from library, only refresh
nets). After sync, re-check the 16 remaining clearances near J310 and the
R374/R375 pair.

---

## Verified CORRECT (no action needed)

- **Schematic ERC: clean** — 0 errors (unconnected-pin and power-pin checks
  are enabled at error severity). The 14 pin-to-pin warnings are benign
  GPIO+power-flag strapping.
- **No multi-driver (output/output) net conflicts** anywhere.
- **Power tree complete:** all bucks have inductors + correct output rails
  (VSYS→U6/U7/U750/U1703; BUCK5_SW→L4→SYS_5V; BUCK33_SW→L5→SYS_3V3;
  HUB_CORE_SW→L1700→HUB_VCORE; USB5_SW→L1701→USB_PORT_5V;
  MAKER_3V3_SW→L900→MAKER_3V3_CORE; BUCK_SW→L3→MCU_3V3).
- **MU_12V rail:** fed correctly by U750 (TPS552892) VOUT through RS750
  sense resistor + R751/R752 divider + C763 — 12V for the Mu module is real.
- **Battery chain:** J2 PACK_POS_RAW → F1 fuse → BAT_PROT_VIN → Q11/Q12 +
  U11 (LTC4368) → PACK_POS_FUSED → Q25 → BAT_CHARGER → U2 (BQ25798) BAT —
  charge/discharge via NVDC is complete and correct.
- **EC (STM32) boot chain:** HSE/LSE crystals with correct load caps, NRST
  with pull-up + reset button + reset drivers, BOOT0 strap, VCAP caps, buck
  feedback divider — all sound.
- **Differential pairs:** USB-C SSTX/SSRX (J12/J22/J23), HDMI D0-D2/CK, GbE
  MDI0-3 — all P/N paired correctly on the connectors.
- **PD controllers (U41/U42):** GPIO config straps on GND per TPS25751A
  practice; LDO3V3/LDO1V5 outputs present.
- **INTERNAL_USB_VBUS cluster:** board nets match schematic
  (SENSE/VALID/FAULT_N/ILIM all on the right pins).
- **Board↔schematic parity (DRC): clean** — no missing/extra/mismatched
  footprints; 4050 of 4076 board pads match the schematic netlist exactly
  (the 26 exceptions are all J2300).

## Known non-blocking issues

- **MU_SIO_UART_RX/TX dead-end:** A1 pins 10/12 are single-node nets; the
  nearby labels and J8 debug header are floating (not wired). The Mu SIO
  debug UART is unavailable and J8 does nothing. Harmless to boot; fix the
  wiring if the SIO UART or J8 is ever needed.
- **U10 (BQ34Z100) VEN pin is no-connect** — verify against the G1 datasheet
  that VEN may float (G1 allows this); if the variant needs VEN = VSS/BAT,
  tie it.
- **Board has never contained routing** (see HANDOFF_ELECTRONICS_REVIEW.md):
  890 nets, 2030 airwires, 0 tracks, unfilled planes. Routing is the
  remaining task.
- **lib_footprint_mismatch severity = ignore** (set during the DRC cleanup):
  re-enable after the re-sync; the J2300 pin-net issue is separate from
  footprint geometry and would NOT have been caught by that check anyway.

## Pre-flight checklist before fabrication

1. Run `Update PCB from Schematic`; confirm J2300's 26 nets change to match
   the schematic (and that nothing else changes).
2. Route all signals; fill the inner-layer planes (GND / SYS_3V3 / SYS_5V /
   VSYS / MCU_3V3 / VBUS_RAW / MU_12V / USB_PORT_5V / INTERNAL_USB_VBUS).
3. DRC after fill — shorts/clearances only fully appear with copper.
4. Re-enable lib_footprint_mismatch; update the 2.5–5 µm pad drift by
   refreshing footprints (or accept and document).
5. Decide on MU_SIO_UART/J8 (wire or formally drop).
