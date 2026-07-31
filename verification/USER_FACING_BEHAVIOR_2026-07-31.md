# User-Facing Behavior Verification

Updated: 2026-07-31

Scope: every user-visible behavior of the Ducktop2, the intended answer, and
the design evidence that implements it. This pass is design-intent
verification: each row proves the schematic carries the feature and records
the agreed behavior. It does not waive physical validation, firmware, or HIL.

Legend: **RESOLVED** = user decision recorded, hardware present; **VERIFIED**
= schematic evidence confirms the intended behavior; **PENDING** = depends on
firmware or physical validation.

## Decisions Confirmed This Pass

1. **Lid close behavior (RESOLVED):** closing the lid puts the system to sleep
   (S3) with the display off; opening resumes. The EC reads an active-low
   `LID_CLOSED_N` hall/reed switch (J53, JST GH 1x2, "Lid/hall switch", pin 1
   net, pin 2 GND) pulled up by R209 (10k to `MCU_3V3`), routed to EC pin 41
   (`LID_CLOSED_N`). Sleep/resume signaling to the OS still needs target
   firmware + ACPI behavior on the first article.
2. **USB-C port roles (RESOLVED):** all five USB-C receptacles are
   data-capable. Two rear ports (J21, J11) are dual-role: USB 3.2 Gen 2 data
   plus USB-PD charging (TPS25751A per port, 15 V PD negotiated). Three
   source-only ports (J22, J23, J12) provide protected 5 V VBUS
   (TPS25810/TPS2594x eFuse + TPD1S514 OVP) for peripherals and never charge
   the laptop. Charging inputs are J21/J11 (15 V PD) plus the protected AUX
   input for bench/solar. No USB-A ports on this design.

## Checklist

| # | User-visible feature | Intended behavior | Design evidence | Status |
| --- | --- | --- | --- | --- |
| 1 | Lid close / open | Sleep on close, resume on open | J53 hall switch + R209 pull-up to `LID_CLOSED_N` (08) -> EC pin 41 (02); firmware/ACPI pending | RESOLVED |
| 2 | USB-C data, all ports | 5 ports, all data-capable | J21/J11 dual-role (05, TPS25751A); J22/J23/J12 source-only (04, USB7206C hub + TPS25810) | RESOLVED |
| 3 | USB-C charging | Charge from rear PD ports only | J21/J11 raw VBUS -> TPS25751A -> LTC4418 selector -> BQ25798 (05, 01) | RESOLVED |
| 4 | Power button | One-button power on/off from the case | J16 case harness GND/CASE_PWR/RESET (02) -> EC power sequencing | VERIFIED |
| 5 | Reset | Case reset + onboard reset | J16 RESET line; SW1 push (02) | VERIFIED |
| 6 | Boot / power sequencing | Source validated, loads enabled after firmware | EC source states + SHDN pulldowns reset to off; TCA9539 P-ports reset to inputs (02) | VERIFIED |
| 7 | Battery / charging state | OS battery reporting via gauge | BQ34Z100-G1 on EC I2C (01), ACPI/_SB battery pending firmware | VERIFIED |
| 8 | Display | 2560x1600 @ 120 Hz eDP | Mu 40-pin eDP direct to AUO B160QAN03.K; harness + timing on first article (docs/display-direct-edp.md) | VERIFIED |
| 9 | Keyboard | 65 keys, 5x14 matrix, USB HID | 12_keyboard_daughterboard (273.5x80 mm, rev-A files generated), 30-pin FFC to mainboard | VERIFIED |
| 10 | Trackpad | USB trackpad, always the same device | J58 four-land direct-solder USB (GND/D-/D+/VBUS) to USB7206C hub; assembly contract | VERIFIED |
| 11 | Speakers | Stereo system audio | PCM2900CDBR codec (U410) -> TPA2012D2 amp -> 2x 38x18 mm speakers (15) | VERIFIED |
| 12 | Microphone | Built-in digital mic | Chip-down digital mic/preamp path on system audio (15) | VERIFIED |
| 13 | Headphone/radio audio | Radio RX/TX audio path | Second USB audio codec on radio path (13) | VERIFIED |
| 14 | Fan / thermals | Automatic fan, safe temps | EC FAN_PWM (Q200 sink) + FAN_TACH, skin (J54) and Mu (THERM_MU_ADC) NTCs (02, 08) | VERIFIED |
| 15 | Status displays | Two OLED readouts | J41/J45 SSD1306 on always-on EC bus (07) | VERIFIED |
| 16 | Wi-Fi / Bluetooth | AX210-class, external antennas | M.2 E-key 2230 + rear antenna connectors (03) | VERIFIED |
| 17 | NVMe storage | Fast primary drive | M.2 M-key 2280 PCIe Gen3 x4 (03); SI validation pending | VERIFIED |
| 18 | Ethernet | Gigabit wired net | RTL8111H + integrated-magnetics jack (16) | VERIFIED |
| 19 | HDMI out | External monitor | Mu TCP0 -> HDMI-A (06) | VERIFIED |
| 20 | Ham radio | 2 m + 70 cm FM | DRA818V/DRA818U with LPF + RF switch, external feed or rear antenna (09) | VERIFIED |
| 21 | GNSS | Position/APRS | MAX-M10S on radio daughterboard (10) | VERIFIED |
| 22 | Maker controller | Protected GPIO + user power, own USB device | RP2350 separate USB device; cannot touch EC (14) | VERIFIED |
| 23 | EC firmware updates | Field-programmable EC | SW2 BOOT0 + J70 rear-edge USB-C prog port, U70/U71 isolation (08) | VERIFIED |
| 24 | Radio daughterboard absent | Laptop fully works without it | All daughterboard enables default off; system audio, mic, charging, boot independent (docs/design-status.md) | VERIFIED |
| 25 | Solar / bench AUX input | Occasional external power | Protected AUX/DC input -> LTC4418 -> BQ25798 MPPT (05) | VERIFIED |

## Held Items (not waived)

- Firmware/ACPI: lid sleep/resume, battery ACPI reporting, power-button
  sequencing, PD negotiation caps — target port + HIL pending
  (firmware/target_port_status.md; 42 HIL rows NOT_RUN).
- eDP harness, keyboard FFC, J58 cable retention, RF/antenna tuning,
  speaker/AUX acoustic, thermal, and enclosure measurements.
- HDMI/PCIe/USB high-speed routing and SI on the final stackup.
