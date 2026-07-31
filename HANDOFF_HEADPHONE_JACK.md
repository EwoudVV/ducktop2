# Headphone Jack Implementation — Handoff

## Goal

Add a 3.5mm stereo headphone jack to the Ducktop2 motherboard (sheet 15, system audio). Jack plugs in → speakers mute automatically. Jack unplugged → speakers play. User confirmed: rear edge, auto-mute, TPA6130A2-class amp.

## What's Done

- User confirmed: rear-edge 3.5mm, plug-detect mutes speakers, TPA6130A2-class headphone amp from PCM2900C line-out.
- The speaker amp is TPA2012D2RTJR (U420), controlled by `AMP_ENABLE` (AND gate of `DAC_SSPND` + `AUDIO_AMP_EC_EN`).
- EC already has `AUDIO_AMP_EC_EN` (pin 43) → can mute speakers in firmware.
- `LID_CLOSED_N` (J53) shows the pattern for EC input sensing.
- The keyboard PCB is already fabricated; layout is locked.

## What's NOT Done

- **No headphone jack, no headphone amp, no detect circuit exists yet.**
- No custom TPA6130A2 symbol or footprint.
- No EC GPIO assigned for jack detect (need a pin on STM32F407VGTx LQFP-100).
- No speaker-mute logic added.

## Design Decisions

### Parts

- **Jack:** CUI SJ1-3535NG (3.5mm, 5+ pads: T, R, S, TN, SN). Footprint in stock KiCad: `Connector_Audio.pretty/Jack_3.5mm_CUI_SJ1-3535NG_Horizontal`. Symbol: use `AudioJack3_Dual_Ground_Switch` from `Connector_Audio` stock lib (has S/SN + T/R/RN/TN — 6 pins). Must add `"AudioJack3_Dual_Ground_Switch"` to `LIBMAP` as `"Connector_Audio"`.
- **Headphone amp:** TPA6130A2 (TI, capless output, 3.5mm drive). Needs a custom `.kicad_sym` in `gen/TPA6130A2.kicad_sym`. Check TPA6130A2 datasheet for pinout (likely 20-pin QFN) and gain settings (G0/G1 select 0.25/0.5/1/2.5 V/V). Use gain that matches PCM2900C line-out level.
- **Speaker mute:** hardware or firmware? User expects "normal laptop behavior". Options:
  - Hardware-only: Use the sleeve switch (SN) to directly pull `AMP_ENABLE` low when plugged. SN is GND when unplugged (shorted to S), floats when plugged → 100k pullup to MCU_3V3 when plugged → HP_DETECT = high when plugged. Wire into the AND gate somehow, or use a separate AND gate + inverter.
  - Firmware-only: EC reads HP_DETECT (SN + pullup) and drives `AUDIO_AMP_EC_EN` low → speakers mute via the existing AND gate (U421). More flexible, consistent with EC-controlled design philosophy.
  - **Recommendation:** Firmware-driven via EC. Simpler hardware, more control.

### Headphone Amp Circuit

- TPA6130A2: SHUTDOWN tied high (always on, ~7mA idle), or EC-controlled HP_EN if you want power saving.
- Inputs: DAC_VOUT_L / DAC_VOUT_R → 1uF coupling → TPA6130A2 INL/INR (reuse the same DAC output nodes as the speaker amp).
- Outputs: TPA6130A2 OUTL/OUTR → jack T/R (capless direct drive, no output caps needed — TPA6130A2 is designed for this).
- Supply: AUDIO_5V (same as speaker amp). Bypass caps: 1u + 100n on VDD.
- VREG bypass: 100n (TPA6130A2 has internal charge pump, needs VREG bypass cap).

### Detect Circuit

- SN (sleeve switch) + 100k pullup to MCU_3V3 → `HP_DETECT` net → EC GPIO.
- Unplugged: SN == S (GND) → HP_DETECT = 0V → "not plugged".
- Plugged: SN floats → 100k pulls to MCU_3V3 → HP_DETECT = 3.3V → "plugged".
- RN (ring switch): NC (not connected) — no use for it.

### EC Pin Assignment

- STM32F407VGTx LQFP-100, pins 86–100 are currently unused in the EC sheet generator (`gen/generate_ec_mcu_sheet.py`).
- Need to find which GPIO port/pin these correspond to (check the STM32F407VGTx pinout — use stock KiCad symbol or datasheet).
- Assign one free pin to `HP_DETECT` input (EC GPIO, floating, no pull — SN + 100k provides the pull).

## File Locations

- System audio generator: `gen/generate_system_audio_sheet.py`
- EC MCU generator: `gen/generate_ec_mcu_sheet.py`
- Symbol embedding: `gen/build_ducktop2.py` `Sheet._use_symbol()` → `genlib.load_renamed_symbol()` → checks `gen/{name}.kicad_sym` first
- LIBMAP: `gen/genlib.py` line ~30 — maps symbol name → KiCad stock lib name
- Stock symbols: `/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/`
- Stock footprints: `/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/`
- Sheet regeneration: `python3 gen/generate_mu_carrier_sheet.py`
- ERC: `python3 gen/check_release_candidate.py --stage schematic`
- Release contract check: `python3 gen/check_release_candidate.py --stage schematic`
- Custom symbols go in: `gen/TPA6130A2.kicad_sym` (new file)
- Verification record: `verification/USER_FACING_BEHAVIOR_2026-07-31.md` (update with headphone jack progress)
- Design-status WIP: `docs/design-status.md` (already has the action item at item 8)

## Implementation Steps (in order)

1. **Research** — TPA6130A2 pinout + gain from datasheet (websearch the TI datasheet). Find STM32F407VGTx pin 86-100 GPIO port/pin mapping (check stock symbol `MCU_ST_STM32F4.kicad_sym` parent `STM32F407V_E-G_Tx`). Verify SJ1-3535NG footprint pads (Jack_3.5mm_CUI_SJ1-3535NG_Horizontal.kicad_mod).

2. **Create TPA6130A2 symbol** — `gen/TPA6130A2.kicad_sym`. KiCad format, standalone (no extends). Pins: VDD, GND, INL, INR, OUTL, OUTR, SHUTDOWN, G0, G1, SNS, VREG. Use footprint: check stock KiCad for WQFN-20 or SOT-23-20 (TPA6130A2 is "RUK" package = 20-pin QFN 3x3mm? Verify).

3. **Add to LIBMAP** — `gen/genlib.py`: add `"TPA6130A2": "TPA6130A2"` and `"AudioJack3_Dual_Ground_Switch": "Connector_Audio"`.

4. **Assign EC GPIO** — `gen/generate_ec_mcu_sheet.py`: add `"86": ("HP_DETECT", "hier")` (or whichever free pin).

5. **Implement in system audio generator** — `gen/generate_system_audio_sheet.py`:
   - Add jack J422 (AudioJack3_Dual_Ground_Switch, footprint Jack_3.5mm_CUI_SJ1-3535NG_Horizontal, T=HP_L, R=HP_R, S=GND, SN=HP_DETECT, TN=NC, RN=NC).
   - Add TPA6130A2 (U425) with gain G0/G1 set, SHUTDOWN tied to MCU_3V3 (always on) or EC control.
   - Route DAC_VOUT_L/R through 1u coupling to TPA6130A2 INL/INR.
   - Add HP_L/HP_R nets from TPA6130A2 OUTL/OUTR → jack T/R.
   - Add R420/R421 100k pullup and 100n bypass caps.
   - Update `hpamp_nets()` and `build()` text blocks.

6. **Regenerate schematics** — `python3 gen/generate_mu_carrier_sheet.py` (or just regenerate the system audio sheet if there's a direct function).

7. **Run ERC + netlist** — `python3 gen/check_release_candidate.py --stage schematic`. Verify 0 new errors (warnings OK if expected). Check netlist matches design intent.

8. **Update verification record** — `verification/USER_FACING_BEHAVIOR_2026-07-31.md`: update row 12 (speakers/headphones) to VERIFIED.

9. **Commit** — `git add` the new/changed files. Message: "Add headphone jack with auto-mute to system audio (sheet 15)"

## Gotchas

- The `Sheet` class embeds `lib_symbols` per sheet (line 371 of `build_ducktop2.py`). The TPA6130A2 symbol and AudioJack3_Dual_Ground_Switch symbol are automatically embedded when `s.place()` calls `_use_symbol()`.
- The audio ground is local per sheet (`"GND", "local"` in pin_nets). Jack sleeve = GND should be "local" too.
- TPA6130A2 and TPA2012D2 share the same DAC outputs (DAC_VOUT_L/R). The TPA2012D2 input network already has 100R+47n+1u coupling. The headphone amp should tap the SAME DAC LPF nodes (before the speaker amp's input coupling caps), or share the existing RC network — avoid doubling the load. Check PCM2900C output impedance vs drive capability (it's a line-out, can drive ~2 loads).
- The `pin_review` table and `verify_design_contracts.py` reference hardcoded net maps for TPA2012D2 (pins 7/8 = AMP_ENABLE). These will need updating if AMP_ENABLE routing changes — but the design above doesn't change AMP_ENABLE routing, only adds new nets (HP_L, HP_R, HP_DETECT).
- The `Sheet` counters `s.refcounters["#PWR"] = 1500` in generate_system_audio_sheet.py (line 127). Power symbol refs must not collide.

## TODO List (from broad todo)

- [x] Study 15_system_audio generator
- [ ] Design headphone path (you are here)
- [ ] Implement in generator
- [ ] Run ERC + netlist + release checks
- [ ] Update docs (design-status WIP, verification checklist, BOM)
- [ ] Commit
- [ ] Push to origin (at 5-10 commits threshold)

## Current Git State

- 4 commits ahead of origin/main
- `radio_daughterboard/radio_daughterboard.kicad_pcb` has unrelated uncommitted changes (pre-existing, do not touch)
- Last commit: `2ff5b2b` "Lock keyboard layout (board already fabricated), record headphone jack design, add rendered keyboard image"
