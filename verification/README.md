# verification

`generated/` contains regeneratable netlists, DRC/ERC output, pin reviews,
inventories, and working IPC-D-356 exports. it is ignored by git.
generators and checkers create the directory when needed.

`hardware_validation_release.json` remains tracked. firmware release/HIL
records are under `firmware/release/`, and manufacturing packages retain
their own released test files and manifests.

use fresh schematic exports for comparisons. retain source revision,
command, tool version, and date with evidence. ordinary DRC, expanded
track checks, parity, and schematic contracts cover different things.

[build and verification](../docs/build-and-verify.md)
