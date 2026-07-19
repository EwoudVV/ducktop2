# Independent Review Prompt

Use this prompt for a fresh hardware review. It is written to stay useful as the
project changes; the reviewer must establish the current state from the files
rather than trust old dates or hashes.

```text
Review the Ducktop2 KiCad 10 project in the repository you were given. On
Ewoud's Mac, the canonical folder is:

/Users/ellievanvooren/Documents/KiCad/ducktop2

Treat that folder as the source of truth. Do not use old Codex session folders.
Start by reading README.md, docs/design-status.md, docs/hardware.md,
docs/display-direct-edp.md, verification/README.md, the root schematic, the
active generators, project-local symbols/footprints, and the newest applicable
verification files. Older reports may describe designs that no longer exist.

The PCB is in progress. Review the schematic first. Do not report ordinary
unrouted items or placement-stage silkscreen warnings as schematic defects.
Do report schematic-to-PCB reference, footprint, pad-net, BOM, or DNP drift.

Use four independent reviewers if the environment supports them:

1. Power and safety: battery entry, BQ77915 protection, fuse/LTC4368 backup,
   BQ25798 charger/NVDC, USB-C PD sinks, AUX input, source selection, all rails,
   reset defaults, reverse paths, startup, shutdown, and faults.
2. Mu and high speed: official Mu pins and default BIOS allocation, eDP,
   HDMI, USB-C, PCIe/NVMe/E-key, Ethernet, clocks, coupling, ESD, lane mapping,
   power-off behavior, and placement requirements.
3. Controllers and peripherals: STM32 EC, RP2350, keyboard FFC, trackpad,
   OLEDs, fan, system/radio audio, microphone, GNSS, radios, and user headers.
4. Libraries and manufacturing: every active custom symbol and footprint,
   exact orderable suffixes, pin/pad maps, DNP combinations, support circuits,
   BOM identities, package geometry, and assembly risks.

Each reviewer must return concrete P0-P3 findings with exact file, reference,
pin/net, datasheet section, failure mechanism, correction, and verification
test. The coordinating reviewer must independently reproduce every P0/P1 and
resolve disagreements against the generated netlist and primary manufacturer
documentation.

Rules:

- ERC success is not proof. Check absolute maximums, thresholds, startup state,
  power-off injection, reverse current, package suffixes, and what the circuit
  actually does.
- Prefer current primary datasheets and official LattePanda documentation.
- Inspect a script before running it. Several project tools regenerate sheets
  or overwrite fixed verification files.
- Run mutating checks in a complete temporary copy. Direct KiCad ERC/netlist/DRC
  output should also go to that copy or /tmp.
- Do not edit the project during REVIEW_ONLY mode.
- If the user switches to IMPLEMENT_AFTER_REVIEW, make fixes in the generators,
  regenerate deliberately, update/synchronize the PCB, and place affected new
  parts near their circuit. Preserve unrelated placement and existing routing.
  The PCB is not untouchable; it should track accepted schematic changes.
- Distinguish a circuit defect from a missing physical measurement, unfinished
  firmware, unfinished routing, or a manufacturing release task.
- Do not repeat generic warnings. Explain a real failure path or leave it out.

Minimum checks:

- full power-path state walk for battery, each adapter, source transfer, reset,
  brownout, reverse connection, short, and simultaneous inputs
- all Mu pin/lane assignments against the current official pinout and BIOS map
- all USB-C CC/VBUS/orientation/current-limit and power-off states
- PCIe/USB/HDMI/Ethernet coupling, clocks, reset, sideband, and ESD
- STM32 and RP2350 boot, clock, reset, USB, debug, and exposed-I/O contracts
- keyboard/trackpad/OLED/audio/radio/GNSS/fan signal and power boundaries
- custom symbol-to-footprint pin maps and exact active package suffixes
- DNP metadata and mutually exclusive population options
- schematic-to-PCB reference, footprint, pad-net, BOM, and DNP parity
- current generator/checker claims against at least one independent netlist walk

Lead the report with findings in severity order. Then give confirmed strengths,
physical/firmware/layout tasks, commands and results, and a direct verdict on
schematic completeness. Do not bury a blocker in a general summary.
```
