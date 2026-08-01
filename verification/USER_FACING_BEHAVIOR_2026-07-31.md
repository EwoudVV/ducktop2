# User-Facing Behavior Verification

Updated: 2026-07-31

Scope: every user-visible behavior of the Ducktop2 written as the user's
expectation ("when I do X, I expect Y"), the agreed answer, and the design
evidence that implements it. Confirmed by walkthrough on 2026-07-31. This pass
records design intent; it does not waive physical validation, firmware, or HIL.

Legend: **RESOLVED** = expectation confirmed, hardware present; **VERIFIED** =
schematic evidence confirms the expectation; **PENDING** = depends on firmware
or physical validation; **ACTION** = hardware/firmware change still needed.

## Decisions Confirmed This Pass

1. **Lid close (RESOLVED):** closing the lid turns the screen off but the Mu
   keeps running — opening the lid must bring the display back without a power
   cycle (no shutdown/startup). EC reads active-low `LID_CLOSED_N` from J53
   (hall/reed switch, R209 10k pull-up to `MCU_3V3`) on EC pin 41 (sheets 08,
   02). Display-off on lid close is EC/firmware behavior on the first article.
2. **USB-C ports (RESOLVED):** all five USB-C receptacles behave like a normal
   laptop — plug in a flash drive, phone, cable, or peripheral and it works.
   Two rear ports (J21, J11) are dual-role data + PD charge (TPS25751A, 15 V
   negotiated). Three source-only ports (J22, J23, J12) deliver protected 5 V
   VBUS to peripherals and never charge the laptop. No USB-A ports.
3. **Charging (RESOLVED):** plugging in the charger charges the laptop, and it
   also charges when the laptop is off (NVDC path works with Mu off; EC runs on
   the always-on rail).
4. **AUX input (RESOLVED):** the AUX/solar connector is for bench or solar
   power and should accept any voltage within its design range and charge from
   it. Design range: "AUX/SOLAR protected screw terminal 6-22V nominal" — 3 A
   fuse, SMCJ24CA 24 V bidirectional clamp, 100 V reverse FET, TPS26630 eFuse,
   then BQ25798 (01, 05).
5. **Headphone output (RESOLVED):** the 3.5 mm stereo jack is now on sheet 15
   on the **rear edge** (J422, CUI SJ1-3535NG) driven by a TPA6130A2RTJR
   DirectPath headphone amp (U425) fed from the PCM2900C line-out. Plug-detect
   mutes the speakers: the jack ring-normalling contact (RN) = HP_DETECT, read
   by the EC on U44 pin 6 (a recovered source-manager spare); on plug-in the EC
   drives AUDIO_AMP_EC_EN low (U421 AND gate mutes TPA2012D2) and I2C-unmutes
   U425. /SD is tied to MU_HOST_ACTIVE (S0-only, 0.4 uA in S3); power-on default
   is muted with outputs disabled (fail-safe OFF until EC firmware enables it).
6. **Keyboard layout (VERIFIED, locked):** 65-key compact layout, **no
   function-key row**, split spacebar, arrows in the bottom-right cluster.
   User confirmed on 2026-07-31 — and the keyboard PCB is **already
   fabricated**, so the layout is locked. Fn layers (F1-F10, `~, brightness,
   volume) remain a firmware assignment, not a board change. See rendered
   board: `docs/images/keyboard-layout-2026-07-31.png`.
7. **Fan policy (RESOLVED):** fan is controlled by the STM32 EC; the curve must
   never be annoyingly loud at idle but must not throttle under load either —
   "I'll take the noise if it's more performing" (performance-biased curve).
8. **OLED displays (RESOLVED):** both displays show status of all system
   components (see content spec below).
9. **Onboard eMMC (RESOLVED question):** the 64 GB eMMC is not usable as RAM —
   eMMC is a block device with ~200-300 MB/s bandwidth and millisecond
   latency; LPDDR5 RAM is tens of GB/s with nanosecond latency. As swap it
   would make the machine crawl. Planned use: recovery/rescue OS (boots if the
   NVMe fails), suspend-to-disk (hibernation) image, and offline data
   (APRS/maps/logs). Primary storage is a 2 TB NVMe.

## Checklist (user expectations)

| # | When I... | I expect... | Design evidence | Status |
| --- | --- | --- | --- | --- |
| 1 | close/open the lid | screen off, Mu keeps running, display back on instantly (no power cycle) | J53 + R209 `LID_CLOSED_N` -> EC pin 41 (08, 02); EC display-off firmware pending | RESOLVED |
| 2 | plug anything into any USB-C port | it just works like a normal laptop | J21/J11 dual-role (05); J22/J23/J12 source-only (04) | RESOLVED |
| 3 | plug in the charger | laptop charges, including when off | TPS25751A -> LTC4418 -> BQ25798 NVDC (05, 01) | RESOLVED |
| 4 | press the power button | boots to my desktop, fast | J16 case harness (02) -> EC power sequencing | VERIFIED |
| 5 | need to reset | reset without opening the case | J16 RESET line; SW1 onboard (02) | VERIFIED |
| 6 | shut down / run out of battery | clean shutdown, no corruption, boots normally next time | EC sequencing + protection (02, 01) | VERIFIED |
| 7 | check battery | trusted OS percentage + OLED status of all system components | BQ34Z100-G1 gauge (01); OLED content spec below | RESOLVED |
| 8 | use the AUX connector | it accepts any voltage in range and charges | 6-22V nominal: fuse + 24V clamp + eFuse -> BQ25798 (01) | RESOLVED |
| 9 | use the screen | full res, smooth 120 Hz, OS brightness control | Mu 40-pin eDP -> AUO B160QAN03.K (03, docs/display-direct-edp.md) | VERIFIED |
| 10 | type | layout is what I expect (confirmed; board already fabricated) | 65-key matrix, no F-row, split space; Fn layers = firmware | VERIFIED |
| 11 | use the trackpad | cursor, tap, click, scroll, gestures like a normal laptop | J58 direct-solder USB (GND/D-/D+/VBUS) -> hub (08, docs) | VERIFIED |
| 12 | listen to speakers / headphones | speakers work with volume control; headphones when plugged in (jack auto-mutes speakers) | PCM2900CDBR -> TPA2012D2 -> speakers; J422 SJ1-3535NG + U425 TPA6130A2 headphone amp with HP_DETECT plug-mute (15); mute firmware pending | RESOLVED |
| 13 | do a call / recording | onboard mic works like any laptop mic | chip-down digital mic path (15) | VERIFIED |
| 14 | load it hard | fan runs under load, quiet at idle, never throttles | EC FAN_PWM (Q200) + FAN_TACH + skin/Mu NTCs (02, 08); curve is firmware | RESOLVED |
| 15 | glance at the status displays | all laptop statistics shown | J41/J45 SSD1306 on always-on EC bus (07); content spec below | RESOLVED |
| 16 | connect Wi-Fi / BT | network connects; BT peripherals work | M.2 E-key AX210-class + rear antennas (03) | VERIFIED |
| 17 | use storage | fast boot/apps, ~2 TB NVMe | M.2 M-key 2280 PCIe Gen3 x4 (03); 64 GB eMMC = recovery/hibernate | VERIFIED |
| 18 | plug in Ethernet | on the network like any laptop | RTL8111H + integrated-magnetics jack (16) | VERIFIED |
| 19 | plug in an external monitor | it shows my stuff via HDMI | Mu TCP0 -> HDMI-A (06) | VERIFIED |
| 20 | work the radios | 2 m and 70 cm FM from the laptop | DRA818V/U + LPF + RF switch (09) | VERIFIED |
| 21 | need position | I can see where I am, run APRS | MAX-M10S on radio daughterboard (10) | VERIFIED |
| 22 | experiment with the maker port | GPIO experiments can't hurt the laptop | RP2350 separate USB device, protected (14) | VERIFIED |
| 23 | update EC firmware | update through the dedicated USB port, no case opening | SW2 BOOT0 + J70 rear USB-C prog port (08) | VERIFIED |
| 24 | remove the radio daughterboard | everything else still works | all daughterboard enables default off (docs/design-status.md) | VERIFIED |

## Keyboard layout (65-key, no F-row)

Row 0: `Esc 1 2 3 4 5 6 7 8 9 0 - = Bksp(1.75u)`
Row 1: `Tab(1.25u) Q W E R T Y U I O P [ ] \`
Row 2: `Caps(1.5u) A S D F G H J K L ; ' Enter(1.75u)`
Row 3: `Shift(1.75u) Z X C V B N M , . / Up Shift(1.25u)`
Row 4: `Ctrl Fn Super Alt Space(2.25u) Space(2.25u) Alt Menu Left Down Right`

Notes: no F1-F12, no dedicated `~, no volume/brightness keys — these are Fn
layers in EC firmware (e.g., Fn+1..0 = F1..F10, Fn+Esc = `~, Fn+arrows =
brightness/volume). Layout is locked: the keyboard PCB is already fabricated.
Rendered board: `docs/images/keyboard-layout-2026-07-31.png`.

## OLED content spec (2x SSD1306)

All system component status: battery % + charge/discharge state, source in use
(PD1/PD2/AUX) and input voltage, fan duty + both thermistor temps, charging
current, radio/GNSS state (daughterboard installed), maker-controller status,
EC firmware version.

## Action Items

1. **Add headphone jack to the motherboard** (sheet 15): 3.5 mm stereo jack,
   rear edge, plug-detect mutes speakers, TPA6130A2-class amp from the
   PCM2900C line-out. User-confirmed on 2026-07-31.
2. **Keyboard Fn-layer assignments** (firmware only — board is fabricated and
   layout is locked): F1-F10, `~, brightness, volume — **host-tested keymap core
   DONE** in `firmware/ec/src/ec_keymap.c` (commit pending): Fn+1..0=F1..F10,
   Fn+Esc=`~, Fn+Bksp=Delete, Fn+Up/Down=brightness, Fn+Left/Right=volume.
   22 host tests pass; remaining is the target-side matrix scan + USB HID.
3. OLED content is a firmware spec; record confirmed above.

## Held Items (not waived)

- Firmware/ACPI: lid display-off behavior, battery ACPI reporting, power-button
  sequencing, PD negotiation caps, fan curve, OLED content — target port + HIL
  pending (firmware/target_port_status.md; 42 HIL rows NOT_RUN).
- eDP harness, keyboard FFC, J58 cable retention, RF/antenna tuning,
  speaker/AUX acoustic, thermal, and enclosure measurements.
- HDMI/PCIe/USB high-speed routing and SI on the final stackup.
