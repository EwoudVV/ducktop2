# build and verify

updated 4 september 2026. these are the entry points for checking the working
files. the latest results and known checker failures are in [current status](design-status.md).

## before running anything

work from the project root and check `git status --short`. i keep manual
routing in the working tree, so do not reset, stash, regenerate, or sync a
board as part of an ordinary review.

KiCad 10.0.4 was used for the latest checks. on this Mac:

```sh
DUCKTOP_KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
DUCKTOP_KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
mkdir -p verification/local
```

use the KiCad Python for pcbnew work. regular `python3` is used by the
schematic generators and most text/netlist checks. some generator files use
newer Python syntax, so the bundled KiCad Python is not interchangeable with
system Python for every script.

## direct ERC, netlist, and DRC checks

the center schematic is `ducktop2.kicad_sch`. its routed-board filename is
`ducktop2-center.kicad_pcb`. the daughterboards each have a matching project
name in their own directory.

from the root, export the center schematic and check it:

```sh
"$DUCKTOP_KCLI" sch erc --format json \
  --output verification/local/center-erc.json ducktop2.kicad_sch
"$DUCKTOP_KCLI" sch export netlist --format kicadxml \
  --output verification/local/center-netlist.xml ducktop2.kicad_sch
"$DUCKTOP_KCLI" pcb drc --format json \
  --output verification/local/center-drc.json ducktop2-center.kicad_pcb
```

run the daughterboard checks from their own directories so KiCad finds the
matching project settings and rule files:

```sh
for board in left_io right_io bms; do
  (
    cd "$board" || exit
    "$DUCKTOP_KCLI" sch erc --format json \
      --output "../verification/local/$board-erc.json" "$board.kicad_sch"
    "$DUCKTOP_KCLI" sch export netlist --format kicadxml \
      --output "../verification/local/$board-netlist.xml" "$board.kicad_sch"
    "$DUCKTOP_KCLI" pcb drc --format json \
      --output "../verification/local/$board-drc.json" "$board.kicad_pcb"
  )
done
```

these commands write reports without saving a board. ordinary DRC uses the
stored zone fill. refill and compare zones in a copied candidate before a
release review. do not add `--save-board` to a read-only check.

`--all-track-errors` expands the DRC report. `--schematic-parity` adds
KiCad's schematic comparison, but on the center the schematic and PCB have
different basenames. use an isolated project with the correct association
or compare against an explicit fresh XML export. the ordinary report,
expanded report, and parity report are different checks; label their counts.

inspect the report's errors, warnings, unconnected items, and parity findings.
the CLI can exit successfully while reporting violations unless
`--exit-code-violations` is requested. zero unconnected items proves only
connectivity under the board's current pad-net assignments.

## schematic-to-board comparison

compare physical reference, pad number, and assigned net against the fresh
schematic export. include pads that share a number. classify DNP and no-connect
cases explicitly, and handle XML entity escaping in center sheet names.

the FPC contract comparison is a separate check. it verifies the cable
boundary, not every component on a board. the F1 mismatch found on 4 september
is why both checks are needed. also check that every schematic component has
the intended footprint, value, and procurement fields on the correct board.

## copied-project release checker

```sh
python3 gen/check_release_candidate.py --stage schematic
```

the checker runs generators and report writers in a temporary project copy.
it checks the live design/library files for changes afterwards. its current
result is FAIL for the reasons listed in [status](design-status.md).

two limitations matter before using its other stages:

- some helpers still expect the former root monolith path;
- `--pcb` has a nonempty default, so the current selection logic takes the
  monolith instead of the intended four-board list when no PCB is supplied.

repair those paths and board associations before treating a fabrication or
production result as a whole-laptop check. an explicit `--pcb` selects one
board; it does not validate the other boards. the `production` stage also
checks target firmware, display, HIL, and hardware release records.

## firmware checks

```sh
sh firmware/tools/run_host_tests.sh
```

the runner compiles host tests into its temporary directory, then checks the
release contract. it does not flash hardware. see [target status](../firmware/README.md#stm32-target)
for what the tests cover and what is still missing on the STM32/RP2350.

## report storage

keep retained project evidence in `verification/`, with the source revision
or working-tree hashes, command, date, and result. `verification/local/` is a
suggested working-report directory, not an automatically ignored directory.
review generated files before staging them. the `.gitignore` already ignores
some ERC/DRC reports and some generated XML paths may be tracked.

do not use an old XML file as evidence that the current schematic is correct.
it may have survived a stash, checkout, or generator change.




## deliberate rebuilds

for a schematic change, edit its generator. for an FPC signal change, edit
`gen/fpc_contract.py` and account for both ends of the cable. placement,
footprint, net-assignment, and track changes are separate operations.

make a candidate copy that includes the current uncommitted work, libraries,
and project settings. keep the canonical working tree intact while checking
the candidate. a checkout of HEAD alone would omit the current BMS routing.

## dependency order in the candidate

| Step | Script or action | What it can change |
| --- | --- | --- |
| 1 | `gen/generate_fh41_68s_footprint.py` | Project FH41 footprint |
| 2 | `gen/generate_conn100_ffc_symbol.py` | FFC symbols; the filename is historical, current I/O maps use 68 pins |
| 3 | `gen/generate_mu_carrier_sheet.py` | Root/center schematic and generated sheets |
| 4 | `gen/generate_left_io_project.py` | Left schematic project |
| 5 | `gen/generate_right_io_project.py` | Right schematic project |
| 6 | `gen/generate_bms_project.py` | BMS schematic project |
| 7 | `gen/verify_design_contracts.py --project NAME --schematic-only` for `ducktop2`, `left_io`, `right_io`, `bms` | Checks and refreshes the corresponding verification netlist |
| 8 | Recreate daughterboards only if a new placement board is actually wanted | Replaces the routing/placement starting point |
| 9 | `gen/generate_split_boards.py`, using KiCad Python | Board split, footprints, pad nets, connector maps, normalization, project rules |
| 10 | `gen/fix_board_hygiene.py`, using KiCad Python | Placement, board hygiene, and zone fills |
| 11 | `gen/add_test_points.py bms`, using KiCad Python | Adds missing test points using the defined table |
| 12 | Per-project ERC, fresh netlists, pad-net comparison, per-board DRC, and release checks | Evidence for the candidate |

use system Python for steps 1-7. use the pcbnew-capable KiCad Python for
steps 9-11. exact paths are in [build and verify](build-and-verify.md).

the earlier workflow used `create_board_from_schematic` for step 8. that was
a board-creation operation, not a safe incremental update of a routed board.
the radio and keyboard also have their own generators and are not recreated
by the four-board split.

## before bringing a candidate back

compare the candidate to the starting working tree by object and purpose:

- generated schematic changes match the requested circuit change;
- all required footprint references exist once, on the intended board;
- pads agree with fresh netlists, including all repeated pad numbers;
- FPC maps, installed orientations, and ground/shield pads agree;
- net names and classes match the actual circuit nets;
- board layer tables and stackups agree;
- board outlines and placement stay within the intended mechanical model;
- unrelated routing is preserved;
- fills and DRC are checked using the actual project rules.

if a hygiene pass is supposed to converge, run it a second time in the
candidate and confirm zero additional moves. do not run a placement fixer on
the live routed BMS just to clear a historical courtyard count.

## the center board's special case

the root schematic is `ducktop2.kicad_sch`, but the center board is
`ducktop2-center.kicad_pcb`. the split pipeline resolves FPC names and
normalizes legacy sheet prefixes. a normal F8 update skips that process.

`resync_pad_nets`, `resolve_net_names`, and `normalize_board_nets` are the
relevant parts of the splitter. check their output, including XML-escaped
sheet names, instead of assuming a successful script exit proves parity.

`gen/recover_center.py` cuts another center board from the old monolith.
that is recovery of a starting point, not restoration of current manual work.

## known tool problems

pcbnew operations that remove and re-add parts have previously failed through
SWIG object corruption. use fresh subprocesses where the scripts require it.
initialize wx for headless reads when needed, and reject a `None` result
from `LoadBoard`.

read files before opening them for writing. never combine a truncating open
with a nested read of the same path. after any branch/stash operation,
regenerate the candidate netlists before building from them.
