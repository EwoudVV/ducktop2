# Schematic-to-PCB ECO Report — Post-Fix 2026-07-27

This evidence was generated in a disposable copy of the canonical project by
[`gen/report_schematic_pcb_eco.py`](../gen/report_schematic_pcb_eco.py). The
script exported a fresh KiCad XML netlist, wrote only inside that copy, and
hashed its copied PCB before and after. This canonical summary preserves the
result without overwriting the historical 2026-07-20 evidence.

## Safety Check

- PCB bytes before/after: `12676510` / `12676510`
- PCB SHA-256 before/after:
  `25d06e11208187f597514f593d12ef28a139f637f6f02362e2592c7d4c6f4501` /
  `25d06e11208187f597514f593d12ef28a139f637f6f02362e2592c7d4c6f4501`
- Result: the checked PCB was not modified.

## Summary

The fresh XML contains 1,173 components and 1,362 nets. The ECO comparator
correctly excludes the three components marked `exclude_from_board`, leaving
1,170 schematic references to compare with 1,170 physical PCB footprints.

| Comparison | Result |
| --- | ---: |
| Schematic references missing from PCB | 0 |
| Obsolete PCB references absent from schematic | 0 |
| Existing references with changed footprints | 0 |
| Existing pad assignments with changed nets | 0 |
| Existing BOM/DNP attribute mismatches | 0 |

**ECO status: synchronized.** This proves reference, footprint, attribute, and
pad-net parity only. It does not waive physical placement, routing, DRC,
stackup, safety, manufacturing, or first-article validation holds.
