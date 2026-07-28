#!/usr/bin/env python3
"""
Apply BOM MPN assignments to the keyboard daughterboard schematic.

The keyboard is built around 65× Cherry MX ULP switches and
65× 1N4148W diodes in a SOD-323 package.
"""

from __future__ import annotations

import sys
from pathlib import Path
from apply_bom_catalog import (
    ROOT, PatchResult, find_component_block, has_manufacturer_mpn,
    patch_component_block, patch_schematic_file,
)

# =============================================================================
# DIODE CATALOG
# =============================================================================
DIODE_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    f"D{ref}": ("Diodes Incorporated", "1N4148W-7-F",
                "1N4148W standard SOD-323 switching diode")
    for ref in range(320, 385)
}

# =============================================================================
# SWITCH CATALOG
# =============================================================================
SWITCH_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    f"SW{ref}": ("Cherry", "MX4A-L1NA",
                 "Cherry MX ULP linear switch, 1.5N actuation")
    for ref in range(320, 385)
}

# =============================================================================
# CAPACITOR CATALOG
# =============================================================================
CAPACITOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    "C320": ("Murata", "GRM188R71H104KA93D",
             "100n 50V X7R 0603 (DNP reserve)"),
    "C321": ("Murata", "GRM31CR71E106KA12L",
             "10u 25V X7R 1206 (DNP backlight)"),
}

# =============================================================================
# CONNECTOR CATALOG
# =============================================================================
CONNECTOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    "J320": ("Hirose", "FH12-30S-0.5SH(55)",
             "30-pin 0.5mm pitch FFC connector for keyboard matrix"),
    "J321": ("Samtec", "TMM-104-01-T-S",
             "1x04 2.54mm pin header (DNP debug)"),
}

# Merge all assignments
ALL_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {}
ALL_ASSIGNMENTS.update(DIODE_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(SWITCH_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(CAPACITOR_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(CONNECTOR_ASSIGNMENTS)

HOLDS: set[str] = set()


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    do_apply = "--apply" in sys.argv

    print("=" * 72)
    print("KEYBOARD DAUGHTERBOARD BOM CATALOG APPLICATION")
    print("=" * 72)
    print(f"\nCatalog summary:")
    print(f"  Diodes assigned:     {len(DIODE_ASSIGNMENTS)}")
    print(f"  Switches assigned:   {len(SWITCH_ASSIGNMENTS)}")
    print(f"  Capacitors assigned: {len(CAPACITOR_ASSIGNMENTS)}")
    print(f"  Connectors assigned: {len(CONNECTOR_ASSIGNMENTS)}")
    print(f"  Total assignments:   {len(ALL_ASSIGNMENTS)}")

    sch_path = ROOT / "12_keyboard_daughterboard.kicad_sch"
    if not sch_path.exists():
        print(f"\nERROR: {sch_path} not found")
        sys.exit(1)

    if not do_apply:
        print(f"\nDRY RUN — use --apply to patch\n")
        result = patch_schematic_file(sch_path, ALL_ASSIGNMENTS, HOLDS, dry_run=True)
    else:
        print(f"\nAPPLYING — patching schematic files:\n")
        result = patch_schematic_file(sch_path, ALL_ASSIGNMENTS, HOLDS, dry_run=False)

    print(f"  {'✓' if not result.skipped_not_found else '!'} "
          f"12_keyboard_daughterboard.kicad_sch: "
          f"{len(result.to_patch)} patched, "
          f"{len(result.skipped_already_assigned)} already assigned, "
          f"{len(result.skipped_not_found)} not found")

    if result.skipped_not_found:
        print(f"    NOT FOUND: {', '.join(result.skipped_not_found)}")

    print(f"\n  Totals:")
    print(f"    Patched:          {len(result.to_patch)}")
    print(f"    Already assigned: {len(result.skipped_already_assigned)}")
    print(f"    Not found:        {len(result.skipped_not_found)}")
    print()


if __name__ == "__main__":
    main()
