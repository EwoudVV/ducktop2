# Phase 4a Verification — FPC connector wiring (2026-08-30)

The four split schematics now carry the physical FFC connectors and the
boundary nets are wired through them.  Boards re-synced/re-placed; all
four DRC-clean at the connector level.

## What changed

1. **Authoritative pin maps** in `gen/fpc_contract.py` — the single source
   of truth for every connector on every board, the cable spec, and the
   gate contracts.  The same conductor order exists on both ends of each
   FPC (verified netlist-by-netlist: 230 pins checked, 0 mismatches).
2. **Connector symbols/sheets**:
   - `gen/Conn_01x100_FFC_MP.kicad_sym` (new, derived from the 30-pin
     pattern; 101 pins incl. MP), registered in genlib + sym-lib-tables.
   - Center root: real FPC sheets `fpc1_left/fpc2_right/fpc3_bms.kicad_sch`
     (replacing the Phase 2.4 label-row placeholders), wired to the host
     sheet block pins by net-name labels.
   - left_io `left_fpc.kicad_sch` (FPC101), right_io `right_fpc.kicad_sch`
     (FPC104), BMS sheet carries FPC106 inline.
3. **Connector refs** FPC101..FPC106 (valid designators — the FPC1_L-style
   refs used in Phase 3 break KiCad annotation).
4. **Pack-rail naming reconciled**: the center's gauge divider input was
   historically BAT_PROT_VIN; it is now PACK_POS_FUSED (the FPC-3 contract
   name for the same node — the LTC4368 output on the BMS).  R180 taps the
   protected rail correctly.
5. **BMS ground net renamed /GND -> GND** (the connector's GND power
   symbols make the pack negative the global ground it always was);
   contracts updated.
6. **Boards**:
   - left/right/bms re-synced from their (now connector-bearing)
     schematics; the split script places the connectors at resolved
     anchors and assigns no nets itself for those (sync does it).
   - Center board: connectors added text-side, pad nets assigned
     text-side from the contract maps (`(net "NAME")` lines — this
     project's code-less net convention).
   - Connectors verified pad-level vs every other footprint: 0 overlaps.
   - **Fixed two pre-existing generator bugs found while wiring**:
     (a) `resolve_connectors` used a naive +R rotation that mirrored the
     connector pads — Phase 3 connectors were placed against phantom
     positions; (b) pad half-extents were computed with
     footprint_rot + pad_rot, but KiCad stores pads with WORLD
     orientation — pin pads of the FH12-100S are 1.3 mm wide, not 0.3 mm.
     Both corrected (verified against pcbnew empirically); a connector
     nudge pass moves the handful of parts squeezed between the connector
     body and its pin columns (the center edges are packed from the
     monolithic layout).

## DRC (per board, project rules)

| Board | shorts | clearance | courtyard | edge | notes |
|---|---|---|---|---|---|
| left_io | 0 | 26 | 16 | 3 | remaining = pre-existing footprint-level |
| right_io | 0 | 25 | 15 | 10 | edge = chassis I/O by design |
| bms | 0 | 0 | 4 | 0 | near-clean |
| center | 16 | 174 | 199 | 20 | ALL 16 shorts are original-board pre-existing (was 17); 0 involve connectors or nudged parts |

Unconnected-items = unrouted nets (Phase 4b+).

## Gate

- `verify_design_contracts.py` per project: PASS (FPC pin contracts added).
- `check_release_candidate.py --stage schematic`: **SCHEMATIC RELEASE
  CHECK: PASS**.
- Schematic closure audits: 89 + 150 PASS, 0 FAIL.

## Artifacts

- `gen/fpc_contract.py` — pin maps, center-side renames, contract nets.
- `gen/generate_conn100_ffc_symbol.py` + `gen/Conn_01x100_FFC_MP.kicad_sym`.
- FPC sheets: `fpc1_left/fpc2_right/fpc3_bms.kicad_sch` (center),
  `left_fpc.kicad_sch`, `right_fpc.kicad_sch`, FPC106 on `bms.kicad_sch`.
- `verification/FPC_CABLE_SPEC_2026-08-30.md` — cable spec (the maps).

## Open items

1. Routing (Phase 4b) — all FPC nets are unrouted; the connector fanout
   plus net-class differential pairs is the next work.
2. Mechanical retention: MP tabs are grounded; cable routing/bend radius
   to be validated at integration.

## Addendum (same day) — Phase 4 deep audit: one-shot readiness

A full pre-fab audit found and fixed four classes of board-killer:

1. **Fictional connector**: the Hirose FH12 series tops out at 60
   positions -- "FH12-100S-0.5SH" does not exist.  FPC-1/FPC-2 now use
   **Hirose FH41-68S-0.5SH(05)** (shielded-FFC, 68 positions; FPC-1 uses
   pins 1-53, FPC-2 pins 1-61).  New footprint derived from the KiCad
   FH41-30S (68 pins at 0.5mm, MP at +/-18, 14 SH solder-holds at 2.5mm
   steps, 38mm body), new 68-pin symbol (Conn_01x68_FFC_MP), pin maps
   trimmed to 68, SH pads to GND (shield return).  The fictional
   FH12-100S footprint/symbol were removed.
2. **Connector courtyard conflicts**: parts were sitting under the
   connector bodies (pads cleared, bodies collided).  The placement now
   enforces courtyard clearance against the connector BODY (library
   courtyard rects), and parts squeezed between a body and its pin
   columns are nudged away; the resolver scans with courtyard checks.
   Fixed a double-shift bug that hid re-placed parts' true positions.
3. **FPC-3 orientation**: the FH12's FPC enters from the +y side; both
   FPC-3 connectors had the cable facing AWAY from the seam.  FPC105
   (center) is now rot 180 at (123.5, 6.5) -- cable exits the bottom edge
   toward the BMS; FPC106 (BMS) is rot 0 at (30, 54) -- cable enters from
   the top edge.
4. **Original-layout defects**: the monolithic board had 16 genuine
   pad-pad shorts (inductor pads swallowing caps, passives on each
   other, parts on mounting holes) and 23 parts inside the hinge
   cutouts (physically off the board).  A courtyard-aware overlap sweep
   plus a forbidden-zone sweep moved them all to legal spots; the
   zones were refilled against the final placement.

The placement passes grew a post-build hygiene sweep (fix_board_hygiene.py)
that uses the FINAL board text as the geometry oracle and converges to a
clean state; residuals are reported, never dropped.

### Final DRC (all boards, project rules)

| Board | shorts | clearance | hole | courtyard | notes |
|---|---|---|---|---|---|
| left_io | 0 | 24* | 0 | 10 | *pre-existing intra-footprint pad pitches |
| right_io | 0 | 24* | 0 | 9 | *pre-existing; edge items are chassis I/O + notch-adjacent |
| bms | 0 | 0 | 0 | 0 | fully clean |
| center | 0 | 0 | 0 | 96 | courtyard = module-socket moat class (design-inherent) |

Remaining categories: courtyards around the Mu socket and M.2 slot
(parts must sit at the component edges), chassis-edge copper clearances
(USB/HDMI/GbE through the chassis wall), 11 isolated zone islands, silk
cosmetics, and 499 unconnected items (unrouted nets -- Phase 4b routing).
