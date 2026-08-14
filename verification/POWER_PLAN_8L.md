# Ducktop2 Power Load Audit (rail budget) — 8L

Status: WORKING DRAFT. Rail membership is parsed from the schematic netlist
(verified). Current values are ENGINEERING ESTIMATES from public datasheet
figures; each row marked EST must be confirmed against the datasheet before
the final order. Converter ratings are the schematic's own specifications.

## Rail budget

### VSYS (3S pack input, ~9.0-12.6 V)

Feeds U6 (SYS_5V), U7 (SYS_3V3), U750 (MU_12V), U1703 (USB_PORT_5V);
the charger path (U2 BQ25798) is a separate pack connection.

| Consumer | Est. current | Basis |
|---|---|---|
| Everything below, summed through ~90% buck efficiency | ~9.5-11 A equivalent at 10.8 V | derived |

Pack peak ≈ (5V*5A + 3.3V*5.5A + 12V*2.8A + 5V*3.5A)/0.9 / 10.8V ≈ **8.6 A**
at 30 W Mu + NVMe write + radio TX. J2 Mega-Fit 2-position rated 23 A —
connector fine; the pack harness and protector (LTC4368 + BQ77915) must be
rated for 10 A continuous (EST).

### MU_12V — U750 TPS552892 (12 V, 3.33 A limit, 400 kHz)

| Consumer | Est. current | Basis |
|---|---|---|
| Mu module, 15 W class | 1.25 A | LattePanda Mu spec (VERIFIED class) |
| Mu module, 30 W boost | 2.5 A | Mu spec |
| Fan (Delta BFB04512HHA, F200 750 mA fuse) | 0.26 A | datasheet (VERIFIED) |
| **Total peak** | **~2.8 A** | 84% of limit |

Flag: Mu BIOS allows up to 35 W TDP → 2.9 A → 88% of limit. Acceptable but
no further loads may be added to this rail.

### SYS_5V — U6 TPS56637 (6 A class)

| Consumer | Est. current | Basis |
|---|---|---|
| Radio DB eFuse branch (U2300 2 A) — 2x DRA818 TX + codec + GNSS | 1.8 A peak (EST) | DRA818V/U datasheet 1.5 A max each, duty-limited |
| Speaker amp TPA2012D2 (2.5 W class-D via U54) | 0.7 A (EST) | datasheet |
| Trackpad branch (U64 TPS2553 0.61 A) | 0.5 A | switch limit |
| Internal host VBUS (U770 TPS2553 0.61 A) | 0.5 A | switch limit |
| Keyboard RGB (U310 TPS2553 0.40 A) | 0.4 A | switch limit |
| Maker section (F900 1.1 A PPTC) | 0.6 A | fuse-limited |
| **Total peak** | **~4.5-5 A** | ~80% of U6 rating |

### SYS_3V3 — U7 TPS56637 (6 A class)

| Consumer | Est. current | Basis |
|---|---|---|
| PCIE_3V3 endpoints via U772: NVMe (J10) | **1.5-2.5 A peak** (EST — MUST confirm on the chosen drive) | PCIe x4 3.3 V spec range |
| PCIE_3V3: Wi-Fi E-key (F10 2 A fuse) | 0.7 A (EST) | Wi-Fi module class |
| PCIE_3V3: RTL8111H GbE | 0.3 A | datasheet (VERIFIED class) |
| USB7206C hub (VDD33 + core via U1700) | 0.7 A (EST) | datasheet |
| TPS25751A x2 | 0.1 A | datasheet class |
| USB muxes/redrivers | 0.3 A (EST) | datasheet class |
| Mu module IO-rail 3.3 V input | 0.5 A (EST) | Mu spec class |
| Misc logic (keyboard buffer, ESD, gates) | 0.3 A | EST |
| **Total peak** | **~4.9-5.9 A** | up to 98% of U6-class rating |

**Flag: this is the tightest rail.** If the chosen NVMe's 3.3 V max exceeds
2.2 A, SYS_3V3 must be re-scoped (drop to x2 mode is not acceptable; the
fix would be a dedicated NVMe buck). Confirm the drive datasheet BEFORE
ordering.

### USB_PORT_5V — U1703 TPS56637 (5.06 V, >=9 A inductor)

| Consumer | Est. current | Basis |
|---|---|---|
| 3x source-only branches (U1740/U1760/U1780 TPS2553 1.3 A) | 3.0 A max | switch limits |
| 2x TPS25751A PD DRP ports (5 V mode) | included above | |
| **Total peak** | **~3.5 A** | ~60% of rating |

### MCU_3V3 — U5 TPS54202 (2 A)

| Consumer | Est. current | Basis |
|---|---|---|
| STM32F407 EC | 0.15 A | datasheet |
| TCA9539 + supervisor + OLEDs x2 + PD VIN3V3 + pull-ups + LEDs | 0.25 A | EST |
| **Total** | **~0.4 A** | 20% of rating — comfortable |

### MAKER_3V3_CORE — TPS62821 (0.4 A output A + B)

| Consumer | Est. current | Basis |
|---|---|---|
| RP2350 + flash + isolators + header IO | 0.25 A | EST (header sinks fused upstream) |
| **Total** | **~0.25 A** | comfortable |

## Converter margin summary

| Rail | Converter | Rating | Peak est. | Margin |
|---|---|---|---|---|
| MU_12V | TPS552892 | 3.33 A | 2.8 A | 84% (88% @35W Mu) |
| SYS_5V | TPS56637 | 6 A | 5.0 A | 83% |
| SYS_3V3 | TPS56637 | 6 A | 5.9 A | **98% — CONFIRM NVMe** |
| USB_PORT_5V | TPS56637 | 6 A class | 3.5 A | 58% |
| MCU_3V3 | TPS54202 | 2 A | 0.4 A | 20% |

## Open items (close before order)

1. NVMe drive selected part's 3.3 V max current (the SYS_3V3 headroom depends on it).
2. Mu BIOS TDP ceiling the firmware will actually permit (30 W vs 35 W).
3. Radio DB transmit duty assumptions (DRA818 TX is duty-limited; confirm the firmware policy).
4. Pack harness/protector 10 A continuous rating confirmation (LTC4368 + BQ77915 + wiring).
