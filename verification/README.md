# Verification

This directory keeps the current, useful verification summaries. Older audits,
raw netlists, DRC JSON files, copied datasheets, and pre-fix snapshots are kept
locally outside the public working tree.

## Current Results

| Check | Current result |
| --- | --- |
| KiCad ERC | 0 errors, 13 classified flattened-library warnings |
| Generated schematic self-check | Pass |
| Schematic design contracts | Pass |
| Independent netlist closure | 386 pass, 0 fail |
| Electrical calculations | 129 pass, 0 fail |
| Pin review | 2,410 pass, 0 fail, 351 review |
| Mainboard schematic/PCB parity | 997 of 997 references, no pad-net or metadata drift |
| Host firmware policy tests | Pass |

The schematic result means the current generated netlist is internally
consistent under the checks implemented here. It does not substitute for target
firmware, SI simulation, RF measurements, thermal testing, a complete
manufacturer BOM, or first-article bring-up.

The PCB is still at placement stage. Its unrouted and silkscreen findings are
tracked separately from schematic correctness.

## Current Evidence

- [`SCHEMATIC_CLOSURE_2026-07-19.md`](SCHEMATIC_CLOSURE_2026-07-19.md) - closed
  electrical findings and current endpoint measurements
- [`ELECTRICAL_CALCULATIONS_2026-07-19.md`](ELECTRICAL_CALCULATIONS_2026-07-19.md)
  - bounded threshold, current, power, and timing calculations
- [`PIN_BY_PIN_REVIEW_2026-07-19.md`](PIN_BY_PIN_REVIEW_2026-07-19.md) - pin
  classification summary
- [`INVENTORY_MANIFEST_2026-07-19.md`](INVENTORY_MANIFEST_2026-07-19.md) - active
  component and net inventory
- [`BOM_RELEASE_GAPS_2026-07-19.md`](BOM_RELEASE_GAPS_2026-07-19.md) - procurement
  fields that still need exact identities
- [`SCHEMATIC_TO_PCB_ECO_2026-07-18.md`](SCHEMATIC_TO_PCB_ECO_2026-07-18.md) -
  current reference and pad-net comparison
- [`KEYBOARD_FFC_ASSEMBLY_CONTRACT_2026-07-15.md`](KEYBOARD_FFC_ASSEMBLY_CONTRACT_2026-07-15.md)
  - keyboard cable orientation and continuity checks
- [`MECHANICAL_RETENTION_VALIDATION_2026-07-18.md`](MECHANICAL_RETENTION_VALIDATION_2026-07-18.md)
  - Mu, M.2, and mainboard retention checks

## Reproduce the Schematic Check

From the repository root:

```sh
python3 gen/check_release_candidate.py --stage schematic
```

This is the preferred entry point because it performs regenerating and
report-writing work in a copied project and checks that the live source remains
unchanged.

To run the firmware policy tests separately:

```sh
firmware/tools/run_host_tests.sh
```

For an independent review, use [`docs/review-prompt.md`](../docs/review-prompt.md)
and verify important claims from the current files rather than accepting these
summaries on authority.
