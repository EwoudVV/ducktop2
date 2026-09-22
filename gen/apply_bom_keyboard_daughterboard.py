#!/usr/bin/env python3
"""
Apply BOM MPN assignments to the keyboard daughterboard schematic.

The keyboard is built around 65× Cherry MX ULP switches and
65× JSCJ 1N4148WS diodes in a SOD-323 package.
"""

from __future__ import annotations

import sys
from pathlib import Path
from apply_bom_catalog import (
    ROOT, PatchResult, find_component_block, has_manufacturer_mpn,
    patch_component_block, patch_schematic_file,
)
from keyboard_rgb_contract import LED_MPN, DRIVER_MPN, BUFFER_MPN

# =============================================================================
# DIODE CATALOG
# =============================================================================
DIODE_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    f"D{ref}": ("Jiangsu Changjing Electronics Technology Co., Ltd.", "1N4148WS",
                "SOD-323 switching diode; JLCPCB/LCSC C2128")
    for ref in range(320, 385)
}

# =============================================================================
# SWITCH CATALOG
# =============================================================================
SWITCH_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    f"SW{ref}": ("CHERRY", "MX6C-T3NB",
                 "MX Ultra Low Profile tactile switch")
    for ref in range(320, 385)
}

# =============================================================================
# CAPACITOR CATALOG
# =============================================================================
CAPACITOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    "C320": ("Samsung Electro-Mechanics", "CL10B104KB8NNNC", "100n 50V buffer 3V3"),
    "C321": ("Samsung Electro-Mechanics", "CL21A106KAYNNNE", "10u 25V RGB input bulk"),
    "C322": ("Samsung Electro-Mechanics", "CL10B105KA8NNNC", "1u 25V RGB VCC"),
    "C323": ("Samsung Electro-Mechanics", "CL10B104KB8NNNC", "100n 50V RGB VCC"),
    "C324": ("Samsung Electro-Mechanics", "CL10B105KA8NNNC", "1u 25V RGB PVCC"),
    "C325": ("Samsung Electro-Mechanics", "CL10B104KB8NNNC", "100n 50V RGB PVCC / buffer A"),
    "C326": ("Samsung Electro-Mechanics", "CL10B104KB8NNNC", "100n 50V RGB startup delay"),
}

RGB_ASSIGNMENTS = {
    **{f'LED{ref}': ('Everlight', LED_MPN, 'per-key RGB') for ref in range(320,385)},
    'U320': ('Lumissil', DRIVER_MPN, '18 x 11 matrix driver'),
    'U321': ('Texas Instruments', BUFFER_MPN, 'I2C buffer with power-off isolation'),
    'R320': ('Yageo', 'RC0603FR-0733K2L', '33.2k 1% RGB current limit'),
    'R321': ('Yageo', 'RC0603FR-072K2L', '2.2k RGB SCL pull-up'),
    'R322': ('Yageo', 'RC0603FR-072K2L', '2.2k RGB SDA pull-up'),
    'R323': ('Yageo', 'RC0603FR-07100KL', '100k RGB startup pull-up'),
    **{f'R{ref}': ('Yageo', 'RC0603FR-07100RL', '100R red-channel heat sharing') for ref in range(330,336)},
}

# =============================================================================
# CONNECTOR CATALOG
# =============================================================================
CONNECTOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    "J320": ("Hirose", "FH12-30S-0.5SH(55)",
             "30-pin 0.5mm pitch FFC connector for keyboard matrix"),
}

# Merge all assignments
ALL_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {}
ALL_ASSIGNMENTS.update(DIODE_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(SWITCH_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(CAPACITOR_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(CONNECTOR_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(RGB_ASSIGNMENTS)

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

    sch_path = ROOT / "keyboard" / "12_keyboard_daughterboard.kicad_sch"
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
