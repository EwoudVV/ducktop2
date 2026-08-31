# FPC Cable Specifications (ducktop2 board split, Phase 4a)

Authoritative pin maps live in `gen/fpc_contract.py` — this document is the
human-readable cable spec.  The same conductor order is wired on BOTH ends
of every cable; the schematic connectors (FPC101..FPC106) and the gate
contracts (`verify_design_contracts.py --project <p> --schematic-only`)
enforce it.

## Cable summary

| Cable | Between | Connectors | Pitch | Pins used | Cable |
|---|---|---|---|---|---|
| FPC-1 | Left I/O <-> Center | FPC101 <-> FPC102 | 0.5 mm | 68 | 68-pin shielded FFC, 30 signals + rails, rest GND |
| FPC-2 | Center <-> Right I/O | FPC103 <-> FPC104 | 0.5 mm | 68 | 68-pin shielded FFC, 35 signals + rails, rest GND |
| FPC-3 | Center <-> BMS (on pack) | FPC105 <-> FPC106 | 0.5 mm | 30 | 30-pin FFC, 8 signals/power, rest GND |

Connectors: Hirose FH41-68S-0.5SH(05) (FPC-1/-2) -- the FH41 series is the
shielded-FFC 0.5mm connector and tops out at 68 positions (the FH12 series
stops at 60; the 100-pin "FH12-100S" does not exist -- Phase 4 deep audit).
The 14 SH solder-hold pads are connected to GND on both ends (shield
return).  FPC-3: Hirose FH12-30S-0.5SH, horizontal, top-contact, MP tabs
to GND on both ends.

## FPC-1 (68 pins) — FPC101 (left) <-> FPC102 (center)

| Pins | Nets |
|---|---|
| 1-2 | VSYS (2) |
| 4-5 | USB_PORT_5V (2) |
| 7 | SYS_3V3 |
| 9 | MCU_3V3 |
| 11 | PD1_VBUS_RAW |
| 13 | AUX_DC_RAW |
| 15 | USB_PD_SELECTED |
| 17 | INTERNAL_USB_VBUS_VALID |
| 19-20 | PD1_I2C_SCL / PD1_I2C_SDA |
| 22 | PD1_TCPC_IRQ_N |
| 24 | PD1_PATH_EN |
| 26 | PD1_VALID_N |
| 28 | PD2_VALID_N |
| 30 | PD1_EFUSE_FAULT_N |
| 32 | PD_PROTECT_FAULT_N |
| 34-35 | USBC1_DP / USBC1_DM |
| 37-38 | USBC2_DP / USBC2_DM |
| 40-41 | HUB_DS1_DP / HUB_DS1_DM |
| 43-44 | USBC1_SSRX_P / USBC1_SSRX_N |
| 46-47 | USBC1_SSTX_P / USBC1_SSTX_N |
| 49-50 | USBC2_SSRX_P / USBC2_SSRX_N |
| 52-53 | USBC2_SSTX_P / USBC2_SSTX_N |
| 54-68 | GND |

Differential pairs kept adjacent (P before N) with a GND conductor between
pairs.  Power pins concentrated at the cable start.

## FPC-2 (68 pins) — FPC103 (center) <-> FPC104 (right)

| Pins | Nets |
|---|---|
| 1-2 | SYS_5V (2) |
| 4-5 | USB_PORT_5V (2) |
| 7 | SYS_3V3 |
| 9 | PCIE_3V3 |
| 11 | MCU_3V3 |
| 13 | PD2_VBUS_RAW |
| 15 | MU_HOST_ACTIVE |
| 17 | PLTRST_SRC_N |
| 19 | PCIE_WAKE_N |
| 21 | GBE_CLKREQ_N |
| 23-24 | PD2_I2C_SCL / PD2_I2C_SDA |
| 26 | PD2_TCPC_IRQ_N |
| 28 | PD2_PATH_EN |
| 30 | PD2_EFUSE_FAULT_N |
| 32 | PD_PROTECT_FAULT_N |
| 34-35 | HUB_DS1_DP / HUB_DS1_DM |
| 37-38 | TCP0_DDC_SCL / TCP0_DDC_SDA |
| 40 | TCP0_HPD |
| 42-43 | GBE_REFCLK_P / GBE_REFCLK_N |
| 45-46 | GBE_HOST_RX_P / GBE_HOST_RX_N |
| 48-49 | GBE_HOST_TX_P / GBE_HOST_TX_N |
| 51-52 | TCP0_TX0_P / TCP0_TX0_N |
| 54-55 | TCP0_TX1_P / TCP0_TX1_N |
| 57-58 | TCP0_TXRX0_P / TCP0_TXRX0_N |
| 60-61 | TCP0_TXRX1_P / TCP0_TXRX1_N |
| 62-68 | GND |

## FPC-3 (30 pins) — FPC105 (center) <-> FPC106 (BMS)

| Pin | BMS side | Center side |
|---|---|---|
| 1-2 | PACK_POS_FUSED (2) | PACK_POS_FUSED |
| 3-4 | PACK_NEG_RAW (2) | GND |
| 5 | PACK_FAULT_N | PACK_FAULT_N |
| 6 | PACK_RETRY_PULSE | PACK_RETRY_PULSE |
| 7 | FG_VSS | FG_VSS |
| 8 | MCU_3V3 | MCU_3V3 |
| 9-30 | GND | GND |

PACK_NEG_RAW is the pack negative = the system ground reference, so the
center side joins those conductors to GND.  The pack rails get two
conductors each (protection path current).

## Design notes

- **No VSYS/VBUS_RAW/PPHV over FPC-1/-2**: only the low-current control,
  USB2/USB3 signal pairs, and the SYS_3V3/SYS_5V/MCU_3V3/USB_PORT_5V rails
  cross (Phase 1 decision).  FPC-3 carries the protected pack rails to the
  center's charger path (explicitly allowed for the battery interface).
- **MP (hold-down) tabs**: grounded on both ends for EMI and mechanical
  connection; they are also the strain-relief solder points.
- **Unused pins are GND** (never floating) so the 100-pin cables get a
  near-continuous ground plane between signal groups.
- Cable length: determined at integration (duct through the hinge channel);
  the FH41 accepts 0.3 mm shielded FFC.  For the USB3/HDMI pairs a
  30-50 mm short cable is assumed for Phase 4 length budgets; GbE
  (RTL8111H MDI is magnetics-side, no FPC) and HDMI are 100-ohm
  differential pairs per the net class plan.  The FH41-68S's shield
  return is the SH pad row (GND on both ends).