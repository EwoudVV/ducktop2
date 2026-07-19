# Schematic-to-PCB ECO Report

This report is read-only with respect to `ducktop2.kicad_pcb`. It compares a fresh
KiCad XML schematic netlist with the protected placement-stage board and normalizes KiCad's
generated unconnected-net names to a single NC state.

## Safety Check

- PCB bytes before/after: `4376967` / `4376967`
- PCB SHA-256 before/after: `6e86ad2362b5a7c3094c3f8f10d3c1a9cc38128c757603a13be0a97d0f550edc` / `6e86ad2362b5a7c3094c3f8f10d3c1a9cc38128c757603a13be0a97d0f550edc`
- Result: PCB was not modified.

## Summary

- Schematic components: **997**
- PCB footprints: **997**
- Schematic references missing from PCB: **0**
- Obsolete PCB references absent from schematic: **0**
- Existing references with changed footprints: **0**
- Existing pad assignments with changed nets: **0**
- Existing BOM/DNP attribute mismatches: **0**

> **ECO status: synchronized.** Schematic and PCB references, footprints, and
> pad-net assignments match. This proves parity only; physical placement, DRC,
> routing, and manufacturing release remain separate checks.

## Missing PCB References

## Obsolete PCB References

None

## Footprint Changes

| Ref | Sheet | PCB footprint | Schematic footprint |
|---|---|---|---|

## Pad-Net Change Hotspots

| Ref | Changed pads |
|---|---:|

## BOM/DNP Attribute Changes

| Ref | Sheet | Attribute | PCB | Schematic |
|---|---|---|---:|---:|

## Detailed Files

- Footprint changes: `verification/schematic_to_pcb_eco_footprint_changes.csv`
- Pad-net changes: `verification/schematic_to_pcb_eco_net_changes.csv`
- BOM/DNP attribute changes: `verification/schematic_to_pcb_eco_attribute_changes.csv`

## Next PCB Steps

1. Complete and review physical placement for every functional block.
2. Re-run DRC after each placement pass and resolve or document every violation.
3. Route by subsystem, preserving the documented six-layer stackup and net classes.
4. Re-run ERC, contracts, this ECO report, DRC, and manufacturing review before fab.
