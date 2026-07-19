# Ducktop2 Release Checker Authority

`gen/check_release_candidate.py` is the strict, read-only fabrication gate. It is intentionally separate from generation, inventory, contract, and ECO scripts.

## What It Does

- Runs KiCad ERC and PCB DRC with all severities and excluded findings included.
- Writes both KiCad JSON reports only inside an operating-system temporary directory.
- Never invokes a generator, refills zones, saves a board, or writes a report into the project.
- Hashes live schematics, PCBs, project files, local symbols, local footprints, and library tables before and after the run; any byte change is a failure.
- Fails on every unrouted item and every schematic-parity finding.
- Reconstructs closed, line-only `Edge.Cuts` loops and fails when any active footprint anchor is outside the board area or inside a cutout.
- Fails rather than guessing if `Edge.Cuts` uses an unsupported arc, rectangle, curve, circle, or polygon primitive.

## Exact Allowlists

The DRC allowlist is empty. Fabrication release requires zero physical DRC violations.

ERC permits only five semantic signatures, all current KiCad library-copy mismatches:

- `U311`: `74AHCT1G126` versus the installed `74xGxx` library copy.
- `U123`, `U133`, and `U143`: `TPD4E05U06DQA` versus the installed `Power_Protection` library copy.
- `U431`: `TLV9061xDBV` versus the installed `Amplifier_Operational` library copy.

Each signature includes sheet path, severity, rule type, full description, and every item description. UUIDs and coordinates are excluded because KiCad can regenerate them without an electrical change. A changed reference, symbol name, rule, severity, description, duplicate count, or additional finding is not allowlisted.

## What It Does Not Prove

- The off-board check evaluates footprint anchors, not full courtyard or body extents. Final mechanical review must still inspect edge clearances, connector engagement, component height, and enclosure collisions.
- A zero DRC result does not prove signal-integrity, thermal, RF, power-integrity, firmware, assembly, or component-source correctness.
- The checker does not refill copper zones. The release operator must intentionally refill and save zones before the final checked candidate, then run this checker against that saved board.
- It does not replace first-article bring-up, current-limited power testing, or hardware-in-loop safety tests.

## Other Script Authority

- `gen/generate_component_inventory.py` is an evidence generator, not a release gate. It writes inventories and a recursive provenance manifest; use `--output-dir /tmp/...` for non-project test runs.
- `gen/check_schematic.py` regenerates generated sheets and therefore is not read-only.
- Contract and ECO scripts verify only the contracts they explicitly encode. Their `PASS` result cannot waive a release-check failure.
- `gen/generate_keyboard_daughterboard_pcb.py` produces only an unreleased candidate under `tmp/` by default. It hard-refuses the live manufactured Rev A PCB and every path under `manufacturing/`.

## Current Expected Result

The main PCB is still in placement/routing work. Until routing is complete and all physical/parity findings are resolved, the strict release checker must return nonzero. That failure is correct behavior, not a checker defect.
