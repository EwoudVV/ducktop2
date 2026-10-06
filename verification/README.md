# verification

`generated/` contains regeneratable netlists, DRC/ERC output, pin reviews,
inventories, and working IPC-D-356 exports. it is ignored by git.
generators and checkers create the directory when needed.

`hardware_validation_release.json` remains tracked. firmware release/HIL
records are under `firmware/release/`, and manufacturing packages retain
their own released test files and manifests.

`power-revision-checkpoint.json` records the main-board power checks,
source hashes, uncapped connection counts and remaining routing work.
the source hashes need to match before using its results for a later board.

`erc-symbols.json` binds the intentional library warnings to checked symbol
templates and stock-library hashes. the separate pin-warning checks require
the matching nets, parts and PD configuration. ERC errors are never exempted.

use fresh schematic exports for comparisons. retain source revision,
command, tool version, and date with evidence. ordinary DRC, expanded
track checks, parity, and schematic contracts cover different things.

[build and verification](../docs/build-and-verify.md)
