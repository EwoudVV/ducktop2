# Verification

This directory keeps the current, useful verification summaries. Older audits,
raw netlists, DRC JSON files, copied datasheets, and pre-fix snapshots are kept
locally outside the public working tree.

## Current Results

| Check | Current result |
| --- | --- |
| KiCad ERC | 0 errors, 13 library-copy and 14 intentional grounded-pin warnings |
| Generated schematic self-check | Pass |
| Schematic design contracts | Pass |
| Independent netlist closure | 1,569 pass, 0 fail |
| Electrical calculations | 123 pass, 0 fail |
| Pin review | 2,603 pass, 0 fail, 0 review |
| Mainboard physical reference uniqueness | 0 duplicate references |
| Mainboard PCB DRC / parity baseline | 1,404 all-track violations, 499 unconnected items, 199 parity observations |
| BOM procurement gaps | 370 |
| Radio daughterboard ERC | 0 errors, 0 warnings |
| Host firmware policy tests | Pass on host; 42 HIL rows remain `NOT_RUN` |

The schematic result means the current generated netlist is internally
consistent under the checks implemented here. It does not substitute for target
firmware, SI simulation, RF measurements, thermal testing, a complete
manufacturer BOM, or first-article bring-up.

The PCB has active routing in progress. Its DRC, unrouted, and parity findings
are tracked separately from schematic correctness and are not release waivers.
The current independent verdict remains **SCHEMATIC BLOCKED**.

## Current Evidence

- [`SCHEMATIC_CLOSURE_2026-07-20.md`](SCHEMATIC_CLOSURE_2026-07-20.md) - closed
  electrical findings and current endpoint measurements
- [`ELECTRICAL_CALCULATIONS_2026-07-20.md`](ELECTRICAL_CALCULATIONS_2026-07-20.md)
  - bounded threshold, current, power, and timing calculations
- [`PIN_BY_PIN_REVIEW_2026-07-20.md`](PIN_BY_PIN_REVIEW_2026-07-20.md) - pin
  classification summary
- [`INVENTORY_MANIFEST_2026-07-20.md`](INVENTORY_MANIFEST_2026-07-20.md) - active
  component and net inventory
- [`BOM_RELEASE_GAPS_2026-07-20.md`](BOM_RELEASE_GAPS_2026-07-20.md) - procurement
  fields that still need exact identities
- [`SCHEMATIC_TO_PCB_ECO_2026-07-20.md`](SCHEMATIC_TO_PCB_ECO_2026-07-20.md) -
  current reference and pad-net comparison
- [`SCHEMATIC_TO_PCB_ECO_2026-07-27_postfix.md`](SCHEMATIC_TO_PCB_ECO_2026-07-27_postfix.md)
  - copied-project post-fix reference, footprint, pad-net, and DNP comparison
- [`INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md`](INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md)
  - current independent review, closed J58 P0, duplicate-reference fix, and
  remaining release holds
- [`INDEPENDENT_REVIEW_2026-07-27_postfix.md`](INDEPENDENT_REVIEW_2026-07-27_postfix.md)
  - post-fix audit: closed R250/R251 trackpad USB physical short, current PCB
  integrity, and the remaining release holds
- [`USER_FACING_BEHAVIOR_2026-07-31.md`](USER_FACING_BEHAVIOR_2026-07-31.md) -
  user-visible feature checklist: intended behavior and schematic evidence for
  every user-facing function (lid, USB-C roles, boot, audio, display, input)
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
