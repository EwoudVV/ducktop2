# Verification

This directory keeps the current, useful verification summaries. Older audits,
raw netlists, DRC JSON files, copied datasheets, and pre-fix snapshots are kept
locally outside the public working tree.

## Current Results

| Check | Current result |
| --- | --- |
| KiCad ERC | 0 errors, 27 intentional warnings (13 library-copy + 14 grounded-pin ties) |
| Generated schematic self-check | Pass |
| Schematic design contracts | Pass |
| Independent netlist closure | 1,580 pass, 0 fail |
| Electrical calculations | 123 pass, 0 fail |
| Pin review | 2,603 pass, 0 fail, 0 review |
| Mainboard physical reference uniqueness | 0 duplicate references |
| Mainboard PCB DRC / parity baseline | 1,404 all-track violations, 499 unconnected items, 199 parity observations |
| BOM procurement gaps | 0 (378 closed via generation-time catalog) |
| Radio daughterboard ERC | 0 errors, 0 warnings |
| Host firmware policy tests | Pass on host (9 suites: policy, commit, telemetry, keymap, fan, oled, lid, battery, maker); 42 HIL rows remain `NOT_RUN` |

The schematic result means the current generated netlist is internally
consistent under the checks implemented here. It does not substitute for target
firmware, SI simulation, RF measurements, thermal testing, a complete
manufacturer BOM, or first-article bring-up.

The PCB has active routing in progress. Its DRC, unrouted, and parity findings
are tracked separately from schematic correctness and are not release waivers.
The current independent verdict remains **SCHEMATIC BLOCKED**.

## Current Evidence

- [`COMPREHENSIVE_REVIEW_2026-07-30.md`](COMPREHENSIVE_REVIEW_2026-07-30.md) -
  full hardware review (9 P1 items: 3 closed, 1 handed off, 3 resolved, 2 open)
- [`SCHEMATIC_CLOSURE_2026-07-20.md`](SCHEMATIC_CLOSURE_2026-07-20.md) - closed
  electrical findings and current endpoint measurements
- [`ELECTRICAL_CALCULATIONS_2026-07-25.md`](ELECTRICAL_CALCULATIONS_2026-07-25.md)
  - bounded threshold, current, power, and timing calculations (current series)
- [`PIN_BY_PIN_REVIEW_2026-07-25.md`](PIN_BY_PIN_REVIEW_2026-07-25.md) - pin
  classification summary (current series)
- [`INVENTORY_MANIFEST_2026-07-28.md`](INVENTORY_MANIFEST_2026-07-28.md) - active
  component and net inventory (current series)
- [`BOM_RELEASE_GAPS_2026-08-01.md`](BOM_RELEASE_GAPS_2026-08-01.md) -
  procurement identity gaps: 0 (closed 2026-08-01; all passives stamped at
  generation time from [`gen/bom_catalog.py`](../gen/bom_catalog.py))
- [`IMPEDANCE_VERIFICATION_2026-08-01.md`](IMPEDANCE_VERIFICATION_2026-08-01.md)
  - candidate 50/85/90/100 Ω trace geometries on the committed stackup
  (reproducible via [`gen/compute_impedance.py`](../gen/compute_impedance.py));
  pending NextPCB field-solver confirmation
- [`HIGH_SPEED_ROUTING_PLAN_2026-08-01.md`](HIGH_SPEED_ROUTING_PLAN_2026-08-01.md)
  - net classes committed to the board (85/90/100 Ω diff + 45 Ω USB2),
  skew budgets, routing order (HDMI -> PCIe -> USB3 -> Ethernet -> USB2)
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
  every user-facing function (lid, USB-C roles, boot, audio, display, input);
  firmware cores for rows 1/5/6/7/8/12/15 are host-tested DONE
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
sh firmware/tools/run_host_tests.sh
```

For an independent review, use [`docs/review-prompt.md`](../docs/review-prompt.md)
and verify important claims from the current files rather than accepting these
summaries on authority.
