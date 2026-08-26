# Bill of Materials and Cost Breakdown

Updated: 2026-08-26

Cost estimate for the Ducktop2 build, including the full line-item breakdown of
the main PCB components and assembly. These are planning numbers for the
funding pitch in
[`docs/sponsorship/funding-pitch.md`](sponsorship/funding-pitch.md), not
vendor quotes.

> **Note on line items:** unit prices are per-part estimates. Category
> subtotals are as stated and may not sum exactly to the line items. Re-quote
> against the current BOM before ordering.

> **Note on fabrication layers:** the "main PCB fab" line below predates the
> committed stackup. The board is now a **six-layer** stackup (see
> [`manufacturing/mainboard_stackup_release.json`](../manufacturing/mainboard_stackup_release.json),
> status `PENDING_NEXTPCB`), so the fab line should be re-quoted before
> ordering.

## Total

| Item | Cost |
| --- | --- |
| LattePanda Mu N305 compute module | $300 |
| Main PCB fab (358 x 185 mm, NextPCB) | $200 |
| Main PCB assembly + component sourcing | $1,500 |
| Radio daughterboard PCB fab + assembly + component sourcing | $600 |
| Cherry MX ULP keycaps x65 | $50 |
| 256 GB NVMe SSD 2280 | $50 |
| Wi-Fi 6E E-key card | $40 |
| Cooling (blower fan, heatpipe, coldplate) | $50 |
| CNC aluminum enclosure | $300 |
| 5000 mAh battery (100 x 60 x 6) | $50 |
| eDP panel (Samsung ATNA60HU01-0) | $400 |
| Framework 13 hinges | $20 |
| **Total** | **~$3,560** |

## Main PCB — Component Breakdown (~$700)

### Power Management

Charger, fuel gauge, protectors, bucks, eFuses, supervisors, load switches.

| Part | Qty | Cost |
| --- | --- | --- |
| BQ25798RQMR battery charger | 1 | $8 |
| BQ34Z100PWR-G1 fuel gauge | 1 | $6 |
| BQ7791500PWR 3S protector | 1 | $4 |
| LTC4368IMS-1 pack protector | 1 | $14 |
| TPS259470ARPW eFuse | 2 | $14 |
| TPS26630RGER sink eFuse | 3 | $18 |
| LTC4418IUF#PBF ideal diode | 2 | $16 |
| TPS552892RYQR 12 V buck-boost | 1 | $9 |
| TPS56637RPAR 6 A buck | 3 | $12 |
| TPS54202DDCR buck | 1 | $2 |
| TPS62821DLCR buck | 1 | $4 |
| TPS62823DLC buck | 1 | $4 |
| TPS2553DDBVR power switch | 4 | $8 |
| TPS22975NDSGR load switch | 3 | $6 |
| TLV803EA29RDBZR supervisor | 4 | $6 |
| TLV803EA43RDBZR supervisor | 1 | $2 |
| TPS3897ADRYR supervisor | 1 | $4 |
| TPS2052BDR dual USB switch | 1 | $2 |
| **Category subtotal** | | **$145** |

### USB, HDMI, Ethernet, ESD Protection

| Part | Qty | Cost |
| --- | --- | --- |
| USB7206C 6-port USB3 Gen2 hub | 1 | $18 |
| USB2512B 2-port HS hub | 1 | $8 |
| TUSB1142IRNQR USB3 redriver | 2 | $16 |
| HD3SS6126RUAR USB3 mux | 3 | $24 |
| TPS25810RVCR Type-C DFP | 3 | $18 |
| TS3USB30EDGSR USB2 disconnect | 3 | $6 |
| TPD4S201RUKR CC protector | 2 | $6 |
| TVS2200DRVR VBUS clamp | 2 | $4 |
| TPD1S514-1YZR VBUS OVP | 3 | $6 |
| TPD13S523PWR HDMI ESD | 1 | $6 |
| TPD4E05U06DQAR ESD array | 12 | $18 |
| USBLC6-2P6 USB ESD | 2 | $2 |
| D3V3XA4B10LP-7 ethernet ESD | 2 | $2 |
| TPS259470ARPW radio eFuse | 1 | $7 |
| TPS2553DDBVR radio VBUS gate | 1 | $2 |
| TLV803EA43RDBZR radio supervisor | 1 | $2 |
| TS3USB30EDGSR radio USB switch | 1 | $2 |
| USBLC6-2P6 radio USB ESD | 1 | $1 |
| **Category subtotal** | | **$155** |

### Radio Buffer / Translator Passives

| Category subtotal | | **$7** |

### MCUs and Compute

| Part | Qty | Cost |
| --- | --- | --- |
| STM32F407VGT6 EC | 1 | $15 |
| RP2350A maker MCU | 1 | $3 |
| RTL8111H-CG ethernet | 1 | $8 |
| TPS25751ADREFR USB-PD | 2 | $16 |
| CAT24C256WI-GT3 EEPROM | 2 | $4 |
| TCA9539PWR I2C GPIO | 1 | $4 |
| TCA9548APWR I2C mux | 1 | $4 |
| W25Q32RVXHJQ flash | 2 | $2 |
| STM32 support passives (crystals, decoupling) | | $4 |
| **Category subtotal** | | **$60** |

### Logic and Level Translation

| Part | Qty | Cost |
| --- | --- | --- |
| PCA9306DCTR translator | 1 | $2 |
| SN74LVC1G17DBVR buffer | 2 | $1 |
| SN74LVC1G08DBVR AND | 3 | $2 |
| SN74LVC2G07DCKR open drain | 2 | $1 |
| SN74LVC3G34DCUR buffer | 1 | $1 |
| SN74LVC1T45DBVR translator | 1 | $1 |
| SN74AHCT1G126DCVR buffer | 1 | $1 |
| SN74CB3T3245PWR 8-bit | 4 | $24 |
| SN74LVC1G373DCKR latch | 2 | $2 |
| **Category subtotal** | | **$35** |

### Audio

| Part | Qty | Cost |
| --- | --- | --- |
| PCM2900CDBR USB codec | 1 | $10 |
| TPA2012D2RTJR class-D amp | 1 | $8 |
| TLV9061IDBVR mic preamp | 1 | $2 |
| LP5907MFX-2.8 mic LDO | 1 | $2 |
| IM68A130V01 MEMS mic | 1 | $4 |
| TPS2052BDR dual USB switch | 1 | $2 |
| Audio passives (coupling caps, filters) | | $2 |
| **Category subtotal** | | **$30** |

### MOSFETs

| Part | Qty | Cost |
| --- | --- | --- |
| CSD18540Q5B | 1 | $3 |
| CSD19537Q3 | 1 | $3 |
| BSS84LT1G | 1 | $1 |
| 2N7002KT1G | 1 | $1 |
| **Category subtotal** | | **$8** |

### Diodes and LEDs

| Part | Qty | Cost |
| --- | --- | --- |
| BAT54WS Schottky | 4 | $1.50 |
| PRTR5V0U2X ESD | 1 | $1 |
| BZT52C5V1 zener | 1 | $0.50 |
| 1N4148WS switching | 1 | $0.50 |
| LED SML-P11 | 2 | $1.50 |
| **Category subtotal** | | **$5** |

### Crystals and Oscillators

| Part | Qty | Cost |
| --- | --- | --- |
| J32SMX-K-F-I 8 MHz | 1 | $2 |
| X1A000141000612 32.768 kHz | 1 | $2 |
| ECS-250-8-33-AGN 25 MHz | 1 | $2 |
| ABM8-272-T3 12 MHz | 1 | $2 |
| ASDMB-25.000MHZ oscillator | 1 | $4 |
| **Category subtotal** | | **$12** |

### Current Sense Shunts

| Part | Qty | Cost |
| --- | --- | --- |
| WSLP2512 5 mOhm | 1 | $3 |
| WSLP2512 11 mOhm | 1 | $3 |
| WSLP2512 8 mOhm | 1 | $2 |
| ERJ8B 15 mOhm | 1 | $2 |
| **Category subtotal** | | **$10** |

### Inductors and Ferrites

| Part | Qty | Cost |
| --- | --- | --- |
| XGL5030 3.3 uH | 1 | $6 |
| XGL6030 4.7 uH | 1 | $6 |
| XGL4020 2.2 uH | 1 | $5 |
| TFM201610 1 uH | 1 | $1 |
| BLM18SG bead | 3 | $2 |
| **Category subtotal** | | **$20** |

### Connectors and Hardware

| Part | Qty | Cost |
| --- | --- | --- |
| TE 2309411-1 SO-DIMM | 1 | $8 |
| MDT420M01001 M.2 M-key | 1 | $5 |
| MDT420E01001 M.2 E-key | 1 | $5 |
| JXD1-1022NL ethernet jack | 1 | $6 |
| DF40C-60DS mezzanine | 1 | $8 |
| FH12-30S FFC | 1 | $4 |
| U.FL-R-SMT | 3 | $4 |
| 73251-1153 SMA edge | 2 | $6 |
| USB4085-GF-A USB-C | 1 | $2 |
| B3S-1000 button | 5 | $2 |
| 9774055243R Wurth spacer | 2 | $6 |
| FFC cables and misc | | $9 |
| **Category subtotal** | | **$65** |

### Passives

| Item | Cost |
| --- | --- |
| ~460 capacitors (265 values, Murata/TDK) | $70 |
| ~428 resistors (305 values, Yageo) | $40 |
| Fuses, thermistors, misc | $20 |
| **Category subtotal** | **$130** |

### Misc

| Item | Cost |
| --- | --- |
| SSD1306 OLEDs x2 | $15 |
| Maker header ESD stuff, DNP, assembly spares | $10 |
| **Category subtotal** | **$25** |

### Main PCB — Assembly

| Item | Cost |
| --- | --- |
| 747 lines setup + 1,134 placements | $800 |

## Main PCB Totals

| Item | Cost |
| --- | --- |
| Components | $700 |
| Assembly (747 lines setup + 1,134 placements) | $800 |
| **Main PCB total** | **$1,500** |

The main PCB total matches the "main PCB assembly + component sourcing" line in
the rough BOM above; the separate fab line covers the bare boards.