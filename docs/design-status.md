# current status

checked 4 september 2026 against the working tree based on commit `57ccc3c`.
the BMS routing, its project settings, and center project settings were
already uncommitted. the checks below did not change those files.

the BMS is routed, but needs corrections. the center and I/O boards still
need routing. there is no complete laptop fabrication release yet.

## boards

counts came from the KiCad board files. "unconnected" below is the number
reported by the CLI, not a count of electrical nets. the repeated 499 on
large unrouted boards should not be used as an exact measure of remaining work.

| Board | Physical footprints | Tracks / arcs | Vias | Copper layers enabled | CLI unconnected |
| --- | ---: | ---: | ---: | ---: | ---: |
| Center | 728 | 0 | 0 | 8 | 499 |
| Left I/O | 260 | 0 | 0 | 8 | 499 |
| Right I/O | 163 | 0 | 0 | 8 | 499 |
| BMS | 62 | 744 | 319 | 8, conflicting with its 4-layer stackup | 0 |
| Keyboard | 131 | 1,296 | 152 | 2 | Not rechecked in this pass |
| Radio | 126 | 0 | 0 | 4 | Not rechecked in this pass |

the old monolithic PCB is in `old/monolith_ducktop2.kicad_pcb`. its old routed
segment counts do not describe any of the current center or I/O boards.

## checks from this pass

| Check | Result |
| --- | --- |
| Center ERC | 0 errors, 10 warnings |
| Left ERC | 0 errors, 9 warnings |
| Right ERC | 0 errors, 7 warnings |
| BMS ERC | 0 errors, 0 warnings |
| Center / left / right ordinary DRC | 406 / 355 / 224 findings |
| BMS ordinary DRC | 284 findings, 0 unconnected items |
| Duplicate physical references | None in the six inspected boards |
| FPC signal assignments | All six connectors match the shared pin-map contract |
| BMS schematic-to-board pad-net comparison | F1 pad 2 differs on both physical pads |
| Copied-project schematic release checker | FAIL, 7 blocking findings/items reported |
| Center procurement inventory from that checker | 1 gap; this is not a whole-laptop BOM count |
| Host firmware tests | 15 suites pass; release-contract check also passes |
| Firmware HIL | 42 rows, all `NOT_RUN` |

the BMS DRC breakdown is 157 silk overlaps, 118 silk-over-copper findings,
5 copper-edge clearances, 2 starved thermals, 1 courtyard overlap, and
1 silk-edge clearance. the two starved thermals are at C700 and R850.
none of the four ordinary DRC reports listed shorts, ordinary copper
clearance violations, or drill-clearance violations. that does not check
whether a pad was assigned to the right net in the first place.

the BMS CLI schematic-parity pass reported 113 observations, mostly footprint
fields and attributes. it is not a replacement for comparing pad nets against
a fresh schematic export. center comparisons also need to account explicitly
for XML-escaped sheet names and intentionally unconnected pins.

## open work

these IDs are used by the work order and topic pages. closing a row needs a file
change or measured evidence, followed by the relevant check.

| ID | Issue | What closes it |
| --- | --- | --- |
| BMS-01 | F1.2 is `PACK_POS_FUSED` on the board and `BAT_PROT_VIN` in the schematic. this bypasses the intended LTC4368 positive-side stage. | Correct pad nets and affected copper, then compare the entire current path to the schematic. |
| BMS-02 | Eight copper layers are enabled while the stackup describes four. | Agree the real layer count, copper weights, and stackup, then verify the saved board and fabrication outputs. |
| BMS-03 | Narrow routes remain in the pack path. `BAT_PROT_SENSE` and `BMS_SENSE_N` also have no `POWER_HI` pattern. | Review actual series paths, branches, vias, shared connector contacts, and worst-case current. |
| BMS-04 | Five edge-clearance findings and two incomplete thermal connections remain. | Correct and recheck them, then finish courtyard and silkscreen review. |
| CHECK-01 | Some checkers still require the removed root `ducktop2.kicad_pcb`. the release checker's default PCB selection also picks the monolith. | Make each check use the intended current project and board. |
| CHECK-02 | Schematic checks have stale expectations, plus generated-source drift. | Resolve each difference without weakening the checks to hide a circuit error. |
| CABLE-01 | FPC106 moved and rotated; the old installed-cable geometry no longer describes it. | Freeze installed board orientation, connector mouths, conductor map, and measured cable length. |
| CABLE-02 | The earlier FFC spec says 1.0 mm thickness. the FH12-30S mating thickness is 0.3 mm. | Release exact compatible cable drawings, contact construction, and connector suffixes. |
| LAYOUT-01 | Center, left, right, and radio still need routing and placement review. | Complete routing, power/SI review, and per-board DRC/parity. |
| FW-01 | Target charge-budget and Mu/eDP-budget commits are unfinished; normal load requests remain off. | Implement real applied-limit feedback and complete target integration. |
| MECH-01 | Enclosure height, board supports, cooling, cell clearance, and cable retention remain provisional. | Measured parts, installed board positions, and a checked mechanical assembly. |
| DISPLAY-01 | Direct-eDP harness release is pending. | Confirm the panel connector, all 40 conductors, rail limits, hinge route, and operation on the Mu. |
| SOURCING-01 | The split boards need a fresh combined sourcing and assembly review. | Per-board BOMs, DNP handling, approved substitutions, and current quotes. |
| TEST-01 | The bring-up instructions need to match the split boards and actual supplies. hardware validation has not run. | Reviewed fixtures and procedure, then recorded first-article tests. |

BMS-01 and BMS-02 both existed in the pre-routing commit `57ccc3c`. they were
not introduced by the manual routing shown in this working tree.

## why the schematic checker fails

the copied-project run found:

- a missing old PCB path in `check_schematic.py`;
- a TP1 footprint expectation of a round 1.0 mm pad versus the square pad in the schematic;
- BMS closure assertions that still expect `GND` or `/FG_VSS` where this board uses `FG_VSS`;
- three SYS_5V checks still aimed at the former 5.2 V target, while the design now specifies 5.10 V;
- an HDMI minimum-voltage calculation of 4.75764 V against its 4.80 V check. this still needs an electrical review of the drop budget;
- a pin review with 24 failed rows and a required A2 reference missing from the center netlist;
- generated-source differences in `01_power_battery.kicad_sch` and `03_mu_carrier.kicad_sch`.

some of these are outdated checks. the generated-source differences and HDMI
budget still need examination. the fail result should stay visible until the
underlying reasons are resolved.

## release records

| Record | State stored in the repository |
| --- | --- |
| `manufacturing/mainboard_stackup_release.json` | `APPROVED`, eight-layer NextPCB stackup and impedance geometry |
| `manufacturing/direct_edp_harness_release.json` | `PENDING` |
| `firmware/release/target_release.json` | `PENDING_TARGET_PORTS` |
| `verification/hardware_validation_release.json` | `NOT_RUN` |

the stackup approval is useful input for the eight-layer boards. it does not
release their routing, the BMS stackup, or the finished laptop.

## work order

1. Fix BMS-01 and BMS-02, with a fresh pad-net comparison and consistent
   layer/stackup settings. preserve unrelated manual routing.
2. Review the BMS current paths, vias, shunts, contacts, edge clearances,
   thermals, and test access. finish BMS-03 and BMS-04.
3. Repair CHECK-01/CHECK-02 and settle CABLE-01/CABLE-02 before routing the
   remaining boards around their connector positions and constraints.
4. Route and review center, left, right, and radio by subsystem. check Q25
   pad/package compatibility, the Mu socket orientation, and the FH41
   footprint/model against the exact parts. the radio can be deferred for
   initial laptop operation.
5. Complete firmware budgets, normal operating requests, controls/displays,
   host telemetry, and the RP2350 target. this can progress alongside layout.
6. Finish the measured enclosure/cooling stack, cable retention, eDP harness,
   sourcing, and per-board manufacturing packages.
7. Use the reviewed fixtures and bring-up procedure on first articles, then
   integrate the laptop and record hardware validation results.

commands and limits: [build and verify](build-and-verify.md).
hardware test order: [bring-up](BRINGUP_TEST_PLAN.md).
