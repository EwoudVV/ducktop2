# Mechanical Retention ECO Validation

Date: 2026-07-18

## Result

The Mu, M.2, and mainboard mounting ECO is applied to the live PCB and is
schematic/PCB synchronized. It closes the missing PCB geometry from audit
findings P1-08 through P1-10, while leaving procurement, enclosure, assembly,
and first-article tests as release holds.

The later exact-hardware ECO replaces only the generic `H1`/`H2` support
footprints with Wurth Elektronik `9774055243R` 5.5 mm M2 SMT spacers. The
manufacturer's 5.3 mm solder land, 3.0 mm NPTH, exact 5.5 mm STEP model, MPN,
maximum torque, and candidate M2 x 4 mm mating screw are now captured in the
project. The Mu socket and both support centers did not move.

## Change Containment

- Pre-ECO board: 848 footprints, SHA-256
  `d798cf0c56a0b32c296f3ab8ed13d09b2fff9761b1b5cb0ce0a1154d0d862e63`.
- Post-ECO board: 860 footprints, SHA-256
  `81b48a7c39be1fe368af1cffde7525a8868dc116df159df6e6b4f3b15f6788bd`.
- Added references: `H1`, `H2`, `H3`, `H4`, `H10`, `H11`, `H12`, `H13`,
  `H14`, `H15`, `H16`, `H17`.
- Existing references deliberately changed: `C26`, `J10`, `J40`, `J54`.
- Existing references removed: none.
- Existing footprint blocks preserved byte-for-byte: 844.
- Copper tracks, arcs, and vias: zero before and after.

`J10` and `J40` were aligned to their 2280/2230 card datums. `C26` and `J54`
were moved out of the resulting standoff/card envelopes.

## Electrical and Parity Checks

- `python3 gen/check_schematic.py`: pass; ERC 0 errors and five known
  `lib_symbol_mismatch` warnings (`U311`, `U123`, `U133`, `U143`, `U431`).
- `python3 gen/verify_design_contracts.py`: pass.
- `python3 gen/report_schematic_pcb_eco.py`: pass.
- Schematic components / PCB footprints: 860 / 860.
- Missing / obsolete references: 0 / 0.
- Footprint differences: 0.
- Pad-net differences: 0.
- Python compile checks and `git diff --check`: pass; the only console note is
  the pre-existing CRLF warning for `gen/generate_ec_mcu_sheet.py`.

## DRC Delta

| Type | Before | After | Delta |
|---|---:|---:|---:|
| `copper_edge_clearance` | 10 | 10 | 0 |
| `hole_clearance` | 1 | 1 | 0 |
| `silk_edge_clearance` | 10 | 10 | 0 |
| `silk_over_copper` | 199 | 199 | 0 |
| `silk_overlap` | 199 | 199 | 0 |
| `courtyards_overlap` | 0 | 2 | +2 |
| `pth_inside_courtyard` | 0 | 2 | +2 |

The four added reports are exactly the intentional vertical stack at `A1/H1`
and `A1/H2`. No other DRC category changed. The board remains unrouted, so the
499 unconnected items and pre-existing placement-stage violations are still a
fabrication blocker.

## Exact-Hardware ECO

- Pre-ECO PCB SHA-256:
  `903de727a674d67a9013e3d43eeeec5bd8f06126023cc5a1d359140805760323`.
- Post-ECO PCB SHA-256:
  `8a9c31afab677d28948ccb90e50d3b6c99c2c358c7811257cd8d15af7a3309d7`.
- Post-ECO PCB size: 3,507,477 bytes and 862 footprints.
- Changed references: `H1`, `H2` only; positions and rotation unchanged.
- Routing and zones: zero segments, zero arcs, zero vias, and 14 zones before
  and after.
- DRC: 423 violations and 499 unconnected items before and after. The only
  wording change is `pth_inside_courtyard` to `npth_inside_courtyard`, matching
  the manufacturer's non-plated locating-hole drawing.
- KiCad 3D render: passed; the exact STEP model resolves without a missing-model
  error.
- ERC: zero errors and the same five classified warnings.
- Schematic/PCB reference, footprint, and connected-pad/net drift: zero.

The footprint intentionally gives its coincident NPTH and grounded solder land
the same logical pad number. This represents one mechanical/electrical mounting
feature to KiCad while retaining a non-plated fabrication drill. It avoids a
false same-feature overlap error without converting the locating hole into a
plated barrel.

## Artifacts

- Top render:
  `mechanical/mechanical_retention_top_2026-07-18.png`
- Mechanical release contract:
  `mechanical/RETENTION_AND_MOUNTING_RELEASE.md`
- Mechanical ECO script: `gen/apply_mechanical_retention_eco.py`
- Exact-hardware ECO script: `gen/apply_mu_standoff_release_eco.py`

Raw pre/post board snapshots and DRC JSON files are retained in the ignored
local archive. They are intentionally not published as alternate working
boards.
