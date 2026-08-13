# Nets & Electronics Review Prompt

Use this prompt when you need an independent, net-level electrical review of
Ducktop2. It deliberately excludes placement cosmetics and the known-unrouted
state (covered by review-prompt.md and HANDOFF_ELECTRONICS_REVIEW.md). This
prompt is for the state AFTER routing will exist: it hunts net, power, and
circuit errors that survive routing.

```text
Review the Ducktop2 KiCad 10 project in the repository you were given. The
canonical folder is /Users/ellievanvooren/Documents/kicad/ducktop2 — treat it
as the source of truth. Read README.md, docs/hardware.md,
docs/design-status.md, verification/README.md, and the newest verification
files first; old reports may describe designs that no longer exist.

SCOPE — review ONLY electrical correctness:
  * net-level connectivity (every intended pin-to-pin path exists)
  * schematic-to-board net parity (pad nets on the PCB vs the schematic)
  * power architecture and integrity (rails, sources, protection, battery)
  * circuit-level correctness (strap pins, enables, feedback, crystals,
    differential pairing, reset/boot chains)
  * single-node or open nets, multi-driver nets, floating critical pins

OUT OF SCOPE — do NOT report:
  * unrouted items, airwires, missing tracks, unfilled zones (the board has
    never contained routing; that is a known work item)
  * placement DRC cosmetics (courtyards, silkscreen, text, lib parity noise)
  * anything already documented as known (HANDOFF_ELECTRONICS_REVIEW.md §0-1)

PROJECT-SPECIFIC TRAPS — the schematic style hides defects from ERC:
  1. The schematic is drawn label-on-pin with ZERO wires anywhere. ERC cannot
     catch floating passive pins (passives are exempt from pin-not-connected),
     so a net that LOOKS connected may be a dead end. The only reliable
     connectivity source is the generated netlist:
       kicad-cli sch export netlist --format kicadsexpr --output /tmp/nl.sexpr <root>.kicad_sch
     Count net nodes by (ref "X") occurrences. DO NOT require or assume
     (pinfunction)/(pintype) fields — passives often lack them, and filtering
     on them silently drops nodes (this has caused false positives before).
  2. The PCB is stale relative to the schematic for at least one connector.
     Compare every board pad net against the schematic pin net using the
     (ref, pin-number) key. Expect to reproduce: J2300 (radio daughterboard
     FFC, 30 pins) — 26 pads carry the wrong nets vs the schematic. Confirm it
     and look for any OTHER refs with drift.
  3. Named nets with exactly one node are real dead ends (ERC will not flag
     them). Known: /Mu Carrier/MU_SIO_UART_RX and MU_SIO_UART_TX (A1 pins
     10/12) connect to nothing; the J8 header is floating. Verify and hunt
     for others of the same class.
  4. lib_footprint_mismatch severity is "ignore" in ducktop2.kicad_pro; that
     check covers geometry, never pin nets. Ignore it for this review.

METHOD — reproduce every finding against primary evidence:
  1. ERC (kicad-cli sch erc) on the root schematic; treat 0 errors as
     necessary but NOT sufficient (see traps 1-3).
  2. Netlist audit with the node-counting rule above:
     a. named single-node nets (dead ends)
     b. nets with 2+ output/power_out drivers (conflicts)
     c. every buck: switch node has its inductor, inductor output reaches the
        correct rail, feedback divider present
     d. battery chain end-to-end: pack connector -> fuse -> protect FETs +
        LTC4368 -> charge/discharge FET -> BQ25798 BAT, sense resistors,
        AON/OR diode path
     e. differential pairs (USB-C, HDMI, GbE) P/N mapping on connectors
     f. EC boot chain: HSE/LSE crystals + load caps, NRST pull-up/reset
        drivers, BOOT0 strap, VCAP caps
  3. Board-vs-schematic pad-net diff ((ref, pin) key), for every ref.
  4. For any suspect: open the sheet, confirm the label/pin/wire geometry, and
     name the exact failure mechanism.

REPORT — same conventions as the project's other reviews:
  * P0-P3 findings, each with: exact file, reference, pin/net, datasheet
    section, failure mechanism, correction, and a verification test.
  * A verified-clean table of the subsystems you actually checked.
  * Explicitly distinguish: circuit defect vs missing measurement vs
    unfinished firmware vs unfinished routing vs manufacturing task.
  * Do not repeat known findings without re-verifying them against the
    current files; if you confirm one, say so with fresh evidence.
  * Prefer current primary datasheets and official LattePanda documentation.

Run mutating checks in a temporary copy; write exported reports to /tmp. Do
not edit the project during REVIEW_ONLY mode.
```
