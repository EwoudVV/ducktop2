# Ducktop2 Post-Fix Release Audit — 2026-07-27

## Verdict: SCHEMATIC BLOCKED

The generated motherboard schematic remains internally consistent under the
repository checks, but the mainboard is not ready to order. This post-fix audit
records the narrowly supported changes made after the independent full review:
the duplicate physical references, J58 stored-zone conflict, and R250/R251
trackpad USB physical short are closed. The remaining routing, DRC, SI, power,
mechanical, procurement, firmware, and physical-validation holds remain open.

This document supplements, rather than replaces, the full review in
[`INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md`](INDEPENDENT_REVIEW_2026-07-27_trackpad-usba2.md).
It uses the canonical project only. No live-board broad regeneration,
uncontrolled zone refill, edge movement, or routed-footprint movement occurred.

## Installed-board integrity

| Item | Result |
| --- | --- |
| PCB SHA-256 | `25d06e11208187f597514f593d12ef28a139f637f6f02362e2592c7d4c6f4501` |
| Board outline | 358 x 185 mm, including the lower-left fin-stack notch |
| Physical footprints / references | 1,170 / 1,170 unique |
| Routed primitives | 4,527 segments, 52 arcs, 855 vias, five top-level zones |
| Root XML inventory | 1,173 components, 1,362 nets, 4,522 connected pins |
| Active hierarchy | Root plus 14 generated child sheets; direct Mu eDP, TCP0 HDMI, NVMe x4, E-key PCIe, RTL8111H Ethernet, native USB-C, and optional radio daughterboard |

The obsolete Intehill, VL822 hub, carrier-eDP, USB-C-video, monolithic-radio,
and internal-USB-C-trackpad architectures are not active in the root hierarchy.

## Closed findings

### Closed P0 — J58 direct-solder lands no longer overlap stored GND copper

J58 is now at `(171.2, 130.0)`. The zone correction was developed and refilled
only in a copied project; only the five top-level zone blocks were admitted to
the installed candidate. The final DRC has no `J58` or `C1720` entry. The full
evidence and test boundaries are in the main review.

### Closed P1 — duplicate physical PCB references

The three real physical duplicates `U170`, `U2004`, and `U2014` were not merely
schematic multi-unit symbols. The retained footprints were chosen using source
paths, routing, and duplicate-only copper evidence. The protected release gate
now fails if a top-level PCB reference repeats; the installed board has zero
duplicates. This was an in-progress PCB defect, not a harmless audit artifact.

### Closed P1 — R250/R251 trackpad USB short

**Refs, pins, and nets.** DRC showed R250.1 on `/TRACKPAD_USB_DP` physically
overlapping R251.2 on `/Internal Services/TPAD_CONN_DM`, with a solder-mask
bridge. The two populated 22 ohm series resistors are specified in the active
[internal-services generator](../gen/generate_internal_services_sheet.py#L68)
and checked by the [design contract](../gen/verify_design_contracts.py#L1936).

**Actual versus required.** D+ and D- were physically shorted at the resistor
pads. A USB 2.0 differential pair requires two independent signal paths; see
the [USB-IF USB 2.0 Specification](https://www.usb.org/document-library/usb-20-specification).

**Correction.** R251 had no attached track endpoints, so only R251 was moved
from `(179.3, 88.6)` to `(180.3, 90.3)`. Five top-level zones were refilled in a
copy and merged using
[`gen/merge_refilled_zone_blocks.py`](../gen/merge_refilled_zone_blocks.py),
which rejects non-zone changes. Existing routing was preserved.

**Verification.** Final all-track DRC has no entry matching `TPAD_CONN`,
`TRACKPAD_USB`, `J58`, or `C1720`. Confidence is high for removal of the
physical short. USB enumeration, cable integrity, eye margin, and real trackpad
operation still require first-article tests.

### Closed P2 — two safe trackpad capacitor identities added

`C280` now specifies Murata `GRM188R71E104KA01D`, and `C283` specifies Murata
`GRM31CR71E106KA12L`. These match the already selected package/value families;
the manufacturer records are [C280](https://www.murata.com/en-eu/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno=GRM188R71E104KA01%23)
and [C283](https://www.murata.com/en-us/products/productdetail?partno=GRM31CR71E106KA12%23).
The BOM gap count fell from 372 to 370. This is not an AVL release.

## Current checks

| Check | Result |
| --- | --- |
| KiCad ERC | 0 errors; 27 classified warnings (13 copied-library and 14 intentional grounded-pin cases) |
| Fresh XML netlist | 1,173 components, 1,362 nets |
| Schematic closure / electrical calculations / pin review | 1,569 / 123 / 2,603 pass; 0 fail |
| Schematic-to-PCB ECO in copied project | 0 missing references, extras, footprint drift, pad-net drift, or BOM/DNP drift |
| Physical duplicate-reference gate | PASS: zero duplicate references |
| KiCad all-track DRC | FAIL: 1,404 violations (948 errors, 456 warnings), 499 unconnected items, 199 parity observations |
| DRC principal categories | 203 solder-mask bridges, 199 shorting-item findings, 199 courtyard overlaps, 156 clearance violations, 153 starved thermals, 38 dangling track/via objects |
| BOM procurement gaps | 370 |
| Host firmware policy tests | PASS on host; 42 HIL rows remain `NOT_RUN` |
| `git diff --check` | PASS at final audit |

The ECO comparison excludes the three `exclude_from_board` XML components, so
its synchronized schematic population and board both contain 1,170 references.
The ECO pass proves current schematic/PCB identity at its comparison scope; it
does not waive KiCad's physical DRC or routing state. The 199 parity and 199
shorting-item findings must be classified one-by-one. They are evidence of an
in-progress board, not an accepted exception list.

## Open release holds

### P1 — PCB layout and routing

1. Remove or classify every DRC, unconnected, and parity observation; none is
   waived by the static schematic checks.
2. Freeze the fabrication stackup and impedance geometries, then reroute and
   review HDMI, PCIe/NVMe/E-key, USB3, eDP, Ethernet, and USB2 paths against
   their primary module/vendor requirements.
3. Re-layout C502/C503 and critical power loops only after proving the existing
   attached routing can be safely removed and rerouted. No blind move was made.

### P1 — power, thermal, and battery safety

The battery temperature/pack assumptions, protection and charger thermal
limits, current limits, failure defaults, and back-power paths require a
complete orderable BOM, primary-source review, bench measurements, and thermal
tests. Static checks do not establish safe charge or discharge behavior.

### P1 — physical and manufacturing release

The direct-solder trackpad cable has no released cable MPN, gauge, bend radius,
clamp, adhesive, service-loop, pull-test, or vibration result. The eDP harness,
battery retention, cooling and hinge Z-height stack, RF placement, assembly
clearances, programming/recovery access, and test coverage remain unreleased.

### P1 — firmware and bring-up

Host policy tests pass, but target startup, power sequencing, USB descriptors,
drivers, recovery, and the 42 HIL rows are not run on hardware. Firmware must
not be the sole protection against an unsafe source-path or power-state fault.

## Documentation and render update

The README, current design status, verification index, build/mechanical guides,
floorplans, retention gates, architecture image, routed-in-progress PCB renders,
and 14-page active-hierarchy schematic PDF were refreshed to the current design
boundary. The images are review artifacts, not manufacturing outputs.

## Bottom line

The closed defects were genuine: the duplicate references and R250/R251 were
physical PCB errors, not merely dirty-worktree noise. The limited fixes are
verified at their exact pads, nets, and board hash. The mainboard remains
**SCHEMATIC BLOCKED** until the listed physical and release evidence exists.
