# Build and Verification

## Requirements

- KiCad 10.0.4 or a compatible KiCad 10 release
- Python 3.11 or newer
- CMake 3.20 or newer for the host firmware tests
- A POSIX shell for the helper scripts

The project uses stock KiCad libraries plus `sym-lib-table`, `fp-lib-table`,
`gen/ducktop2.kicad_sym`, `ducktop2.pretty`, and `Module_LattePanda.pretty`.

## Open the Project

Open `ducktop2.kicad_pro` in KiCad 10. The main schematic is
`ducktop2.kicad_sch`; the separate keyboard project is
`12_keyboard_daughterboard.kicad_pro`.

## Generated Schematics

`gen/generate_mu_carrier_sheet.py` is the main schematic build entry point. It
rewrites the generated child sheets and root schematic. Do not run it casually
after making manual edits to generated `.kicad_sch` files; make the change in
the generator instead.

To compile-check the generator source without writing schematics:

```sh
python3 -m compileall -q gen
```

To regenerate the full hierarchy deliberately:

```sh
python3 gen/generate_mu_carrier_sheet.py
```

After regeneration, inspect `git diff` before updating the PCB.

## Schematic Release Check

The staged checker copies the project before running tools that rewrite
generated sheets or fixed report paths:

```sh
python3 gen/check_release_candidate.py --stage schematic
```

For a direct KiCad ERC run:

```sh
kicad-cli sch erc --severity-all --exit-code-violations \
  --output /tmp/ducktop2-erc.rpt ducktop2.kicad_sch
```

The current expected result is zero errors and 13 classified flattened-library
warnings. A different warning class or count should be reviewed rather than
silenced.

## Firmware Policy Tests

The EC and maker-controller policy cores build on a host compiler:

```sh
firmware/tools/run_host_tests.sh
```

Or with CMake presets:

```sh
cmake --preset host-debug -S firmware
cmake --build --preset host-debug
ctest --preset host-debug --test-dir firmware
```

These tests cover policy and command ordering. They do not replace target
firmware, peripheral-driver tests, watchdog tests, or hardware-in-the-loop work.

## PCB Checks

The PCB is synchronized but intentionally unrouted. The normal DRC therefore
contains unrouted and silkscreen findings. Run it to catch new copper,
clearance, hole, mask, and parity problems, not to hide the expected routing
count:

```sh
kicad-cli pcb drc --format json \
  --output /tmp/ducktop2-drc.json ducktop2.kicad_pcb
```

Before applying an ECO, use the report and candidate checkers in `gen/`. Keep a
snapshot for any operation that changes references, footprints, pad nets, board
outline, or routing.

## Mainboard Render

The repository images can be refreshed from KiCad without opening the editor:

```sh
kicad-cli pcb render -o docs/images/ducktop2-pcb-top.png \
  -w 2400 -h 1500 --side top --background opaque \
  --quality basic --zoom 1.28 ducktop2.kicad_pcb
```

KiCad's high-quality CLI renderer currently throws a macOS `bad_any_cast` for
this project, so the checked-in images use the basic renderer.
