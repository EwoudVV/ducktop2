# User-Functionality Review Prompt

Use this prompt when you need an independent check of "will this machine do
what the user wants it to do?" — requirements-first, from the user's
expectations, not from what the schematic happens to contain. A design can be
internally consistent and still fail the user. This prompt drives that
gap analysis.

```text
Review the Ducktop2 KiCad 10 project in the repository you were given. The
canonical folder is /Users/ellievanvooren/Documents/kicad/ducktop2 — treat it
as the source of truth. Read README.md, docs/hardware.md,
docs/design-status.md, verification/USER_FACING_BEHAVIOR_2026-07-31.md (the
project's own recorded user expectations), and the newest verification files
first.

YOUR JOB IS REQUIREMENTS VERIFICATION, NOT FEATURE INVENTORY. The question is
not "what is on the board?" but "does the board deliver what the USER expects?"
Start from the user's intent, state each expectation explicitly, then prove or
disprove it against the actual schematic and netlist. If a feature exists but
behaves differently than the user expects, that is a P1/P0 gap, not a pass.

STEP 1 — Derive the requirement set. Write the user's expectations as "When I
do X, I expect Y" for every user-visible behavior of this laptop:

  - Power: press power button -> boots to desktop; reset without opening the
    case; clean shutdown and reliable restart; boots after full battery drain.
  - Lid: closing turns the screen off but the machine keeps running; opening
    brings the display back without a power cycle.
  - Display: native 2560x1600 at 120 Hz, OS brightness control.
  - Keyboard: the confirmed 65-key layout works exactly (no F-row, split
    spacebar, arrows cluster); every key and Fn layer maps; keyboard is
    already fabricated so layout is LOCKED.
  - Trackpad: cursor, tap, click, scroll, gestures — normal laptop behavior.
  - USB-C, all five ports: plugging in ANY peripheral just works. Two rear
    ports (J11, J21) charge the laptop (15 V PD) and carry data; the other
    three (J12, J22, J23) deliver protected 5 V and NEVER charge it.
  - Charging: charges from any PD charger and from the AUX/solar terminal
    (6-22 V); charges while powered off (EC alive on the always-on rail).
  - Battery: trusted OS percentage; full charge/discharge accounting; OLED
    shows pack state.
  - Audio: speakers with volume; headphone jack that auto-mutes speakers;
    microphone works for calls/recording.
  - Fan: quiet at idle, ramps under load, never throttles the Mu.
  - OLEDs: both displays show all system status (power/battery, thermal/fan,
    radio DB state, maker, EC state).
  - Network: Wi-Fi and Bluetooth work; Ethernet works; external HDMI monitor
    works.
  - Storage: fast 2 TB NVMe as the primary drive; eMMC as recovery/hibernate.
  - Radios: 2 m and 70 cm FM transmit/receive from the laptop; GPS/GNSS with
    APRS position.
  - Maker port: GPIO experiments can never damage the laptop.
  - EC firmware updates through a dedicated USB port without opening the case.
  - Radio daughterboard can be removed; everything else still works.

Use the recorded expectations in USER_FACING_BEHAVIOR_2026-07-31.md to extend
this list, but do not trust them: verify each row against the CURRENT
schematic and netlist — that file is dated 2026-07-31 and the design may have
drifted since.

STEP 2 — Prove each expectation. For every "When I do X, I expect Y":
  - trace the full electrical chain in the netlist (kicad-cli sch export
    netlist --format kicadsexpr; count net nodes by (ref) — never filter on
    pinfunction/pintype, passives lack them and you will drop nodes)
  - name the parts and nets that deliver it, and where control lives
    (hardware vs EC firmware vs host OS/ACPI)
  - check the failure modes specific to that chain (e.g., charger-off
    charging needs the NVDC path; jack mute needs the detect wiring; radio
    chain needs the daughterboard FFC pin map)

PROJECT-SPECIFIC TRAPS:
  1. Zero-wire label-on-pin schematic: ERC misses floating passives. The
     netlist is the only trustworthy connectivity source.
  2. The PCB is stale vs the schematic: J2300 (radio daughterboard FFC) has
     26 of 30 pad nets that disagree with the schematic. This directly
     breaks the radios, GNSS/APRS, and daughterboard-removal expectations.
     Confirm it and hunt for other refs with the same drift using a
     (ref, pin) -> net diff of board vs schematic.
  3. Dead-end named nets exist and ERC will not flag them (known:
     MU_SIO_UART_RX/TX). Hunt for more; a dead-end in any user chain is a
     requirement failure.
  4. Many behaviors depend on EC firmware that is host-tested but not yet
     target-integrated. Classify those as PENDING firmware, not as hardware
     pass or fail.

STEP 3 — Report. For each requirement: status (DELIVERED / GAP / PENDING
firmware / UNVERIFIABLE-without-physical) + the chain evidence. Then P0-P3
findings with exact file, reference, pin/net, failure mechanism, correction,
and verification test. End with a short user-facing summary: "the user will
be able to do X, Y, Z — but not W."

Run mutating checks in a temporary copy; write exports to /tmp. Do not edit
the project during REVIEW_ONLY mode.
```
