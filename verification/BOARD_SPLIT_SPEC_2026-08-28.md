# Ducktop2 Board-Split Specification — Phase 0 (FROZEN 2026-08-28)

Status: **FROZEN** — all decisions locked. This document is the contract the
schematic split, layout, and FPC design build against. It was generated from
the actual netlist + board placement (not hand-waving): every crossing count
below is computed from the real connectivity with the split rules applied.

## Architecture

Four boards, three FPCs (plus the already-manufactured keyboard FFC):

```
┌────────────┐   FPC-1   ┌──────────────────┐   FPC-2   ┌─────────────┐
│ LEFT I/O   │◄─────────►│ CENTER MAINBOARD │◄─────────►│ RIGHT I/O   │
│ x0–70      │   ~75     │ x70–300, 8L      │   ~83     │ x300–358    │
└────────────┘           └────────┬─────────┘           └─────────────┘
                                  │ FPC-3 (~16)
                                  ▼
                          ┌─────────────┐
                          │ BATTERY BMS │  (MacBook-style, on pack)
                          └─────────────┘
```

## Board assignments

| Board | Contents | Est. size |
|---|---|---|
| **L** Left I/O | J21-25, J190, hub U1700, PD1 chain (U41, U2000-06), SS muxes U1742/45/U1782/85, USB-A cluster U1800-04, their passives | ~70×185, 4-6L |
| **C** Center | Mu A1, M.2 J10, EC U4, all converters (U5/6/7/750/1703), charger U2, VSYS OR (D712/13), U14/U719 source-select, U45/U44, radio/GNSS interface | ~230×185, 8L |
| **R** Right I/O | J11/J12 (USB2-only), J30 HDMI + U50/51, J500 GbE + U501/500, PD2 chain (U42, U2010-15) | ~58×185, 4L |
| **B** BMS | J2, Q11/12, Q703/704, RS10/11, U10 gauge, U11 protector, F1 | ~40×50, 4L |

## FPC definitions

### FPC-1 (C↔L) — 75 signals + 8-10 power/GND pins
- 1× USB3 upstream pair + D± (Mu USBC2 → hub U1700)
- Hub control: SPI (CLK/D1/D2/D3), RESET_N, RBIAS, TEST1-3, CFG1/3, NON_REM,
  BC_EN, CORE_SW, VCORE, PRT_CTL, CLK (~20)
- PD1: I2C (SCL/SDA), TCPC_IRQ_N, GPIO_ATTACH, LDO1V5/3V3 sense, PPHV (~20)
- Maker MCU / AUX control (~10)
- Power: SYS_3V3, USB_PORT_5V, GND (multi-pin)
- **Impedance:** 1 pair 90Ω + D± 90Ω; rest low-speed

### FPC-2 (C↔R) — 83 signals + 8-10 power/GND pins
- HDMI: D0/D1/CK pairs + DDC SCL/SDA + HPD + 5V + BIAS (~12)
- GbE: GBE_HOST TX pair, REFCLK pair, XI/XO, RSET, ETH_1V0, HSO pair (~12)
- PD2 chain to center: I2C, TCPC_IRQ, EEPROM, LDO, PPHV sense, VBUS_RAW,
  SSRX_RAW (for U42's own PD operation — J11/J12 still negotiate PD) (~20)
- USB2: hub DS4 D± (from LEFT hub via center) → J11/J12
- EC debug: SWD, NRST, LSE, VTREF (~6)
- Power: SYS_3V3, GND (multi-pin)
- **Impedance:** HDMI pairs 100Ω, GBE host/REFCLK 100Ω, DS4 D± 90Ω

### FPC-3 (C↔B) — 16 signals + 4-6 pack power pins
- PACK_POS_RAW, PACK_NEG_RAW (2+2 pins, high-current)
- CELL1_TAP, CELL2_TAP
- Gauge I2C (SCL/SDA + ALERT via U45), CHG_GATE/DSG_GATE/DRV, PRES, FAULT
- **No impedance pairs** — battery bus is DC + slow I2C

### Keyboard FFC (existing, already manufactured) — NOT part of this spec
- KB_ROW/COL ×14, I2C, RGB, 3V3/5V — rides its own FFC, unchanged.

## Locked decisions (2026-08-28)

1. Keyboard FFC stays separate (keyboard PCB already manufactured — no changes).
2. J11/J12 are **USB2-only**, fed from the **LEFT hub** (DS4 D±) through center
   — NOT charge-only; data must work. DS4 SS lanes die (16 nets removed).
3. FPC-2 is a single ~90-signal-class FFC (83 signals + power).
4. PD controllers: PD1 chain (U41...) on LEFT, PD2 chain (U42...) on RIGHT.
5. BMS board is strictly 10 parts; all battery control nets cross to CENTER only.
6. No VSYS/VBUS_RAW/PPHV over FPC-1/-2 — power rails that cross are
   SYS_3V3 + USB_PORT_5V only (low-current class).

## Open items (block layout start)

1. FPC connector part numbers + FFC cable specs (impedance class per section).
2. FPC-2 at 83 signals: single 100-pin FFC or 2× 50-pin? (FAB availability)
3. Mechanical: cut-line validation vs mounting holes (H22@120, H25@209,
   H13@58, H27@180), BMS mount on pack, FPC routing vs battery band.
4. U14/U719/U2013/U2012 placement (source-select chain) — must be CENTER per
   the frozen assignment; verify physical space.

## Generation commands (for reproducibility)

Crossing analysis: from the netlist export, assign anchors per the tables
above, propagate by proximity, exclude SS_DEAD (J11/J12 USB2) and KB_*
(keyboard FFC), count nets spanning board sets. See session notes
2026-08-28.