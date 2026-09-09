#!/usr/bin/env python3
"""
Apply BOM MPN assignments to the radio daughterboard schematics.

Pattern: same Yageo/Murata strategy as the main project catalog.
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
from apply_bom_catalog import (
    ROOT, PatchResult, find_component_block, has_manufacturer_mpn,
    patch_component_block, patch_schematic_file,
)
from part_identity import identity_errors

RADIO = ROOT / "radio_daughterboard"

# =============================================================================
# RESISTOR CATALOG
# =============================================================================
RESISTOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    # -- 01_core.kicad_sch --
    "R220": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R221": ("Vishay", "TNPU0603100KHZEN00", "0.02%-5ppm"),
    "R222": ("Vishay", "TNPU060317K4HZEN00", "0.02%-5ppm"),

    # -- 02_radios.kicad_sch --
    "R225": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R226": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R227": ("Vishay", "TNPU060347K0HZEN00", "0.02%-5ppm"),
    "R228": ("Vishay", "TNPU060347K0HZEN00", "0.02%-5ppm"),
    "R229": ("Yageo", "RC0603FR-070RL",   "jumper"),
    "R230": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R231": ("Yageo", "RC0603FR-070RL",   "jumper"),
    "R232": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R233": ("Yageo", "RC0603FR-071KL",   "1%-context"),
    "R234": ("Yageo", "RC0603FR-071KL",   "1%-context"),
    "R242": ("Vishay", "TNPU060310K0HZEN00", "0.02%-5ppm"),
    "R243": ("Yageo", "RC0603FR-07100RL", "1%-context"),
    "R260": ("Vishay", "TNPU060310K0HZEN00", "0.02%-5ppm"),
    "R261": ("Yageo", "RC0603FR-07100RL", "1%-context"),

    # -- 03_gnss.kicad_sch --
    "R40":  ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R41":  ("Yageo", "RC0603FR-07100RL", "1%-context"),
    "R42":  ("Yageo", "RC0603FR-07100RL", "1%-context"),

    # -- 04_codec.kicad_sch --
    "R330": ("Yageo", "RC0603FR-0722RL",  "1%-context"),
    "R331": ("Yageo", "RC0603FR-0722RL",  "1%-context"),
    "R334": ("Yageo", "RC0603FR-0782KL",  "1%-context"),
    "R335": ("Yageo", "RC0603FR-0782KL",  "1%-context"),
    "R336": ("Yageo", "RC0603FR-071KL",   "1%-context"),
    "R337": ("Yageo", "RC0603FR-072R2L",  "1%-context"),
    "R338": ("Yageo", "RC0603FR-071K5L",  "1%-context"),
    "R340": ("Yageo", "RC0603FR-071ML",   "1%-context"),
    "R341": ("Yageo", "RC0603FR-071KL",   "1%-context"),
    "R342": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R343": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R344": ("Yageo", "RC0603FR-07100KL", "1%-context"),
    "R345": ("Yageo", "RC0603FR-07100KL", "1%-context"),
}

# =============================================================================
# CAPACITOR CATALOG
# =============================================================================
CAPACITOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    # -- 01_core.kicad_sch --
    "C1":   ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C2":   ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C3":   ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C4":   ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C5":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),

    # -- 02_radios.kicad_sch --
    "C221": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C224": ("Murata", "GRM1555C1H560JA01D", "56p C0G 50V 5% 0402; Murata GRM1555C1H560JA01 reference sheet"),
    "C226": ("Murata", "GRM188R71H103KA01D", "10n 50V X7R 0603"),
    "C227": ("Murata", "GRM188R71H103KA01D", "10n 50V X7R 0603"),
    "C240": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C243": ("Murata", "GRM188R71H103KA01D", "10n 50V X7R 0603"),
    "C244": ("Murata", "GRM1885C1H101JA01D", "100p C0G 50V 0603"),
    "C245": ("Murata", "GRM1885C1H0R2CA01D", "0.2p C0G 50V 0603"),
    "C246": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C247": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C248": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C250": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C253": ("Murata", "GRM188R71H103KA01D", "10n 50V X7R 0603"),
    "C254": ("Murata", "GRM1885C1H101JA01D", "100p C0G 50V 0603"),
    "C255": ("Murata", "GRM1885C1H0R2CA01D", "0.2p C0G 50V 0603"),
    "C256": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C257": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C258": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C260": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C261": ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),

    # -- 03_gnss.kicad_sch --
    "C40":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C41":  ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C42":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),

    # -- 04_codec.kicad_sch --
    "C330": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C331": ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C332": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C333": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C334": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C335": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C337": ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C338": ("Murata", "GRM1885C1H180JA01D", "18p C0G 50V 5% 0603 crystal load"),
    "C339": ("Murata", "GRM1885C1H180JA01D", "18p C0G 50V 5% 0603 crystal load"),
    "C340": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C341": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C342": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C343": ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
}

# Merge all assignments
ALL_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {}
ALL_ASSIGNMENTS.update(RESISTOR_ASSIGNMENTS)
ALL_ASSIGNMENTS.update(CAPACITOR_ASSIGNMENTS)

# The optional matching capacitors remain DNP pending measured RF tuning.
HOLDS: set[str] = {"C245", "C255"}


def stamp_sheet_identities(sheet):
    """Stamp this board's catalog without using colliding main-board refs."""
    for index, block in enumerate(sheet.body):
        if not re.match(r"\(symbol\s", block):
            continue
        props = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', block))
        ref = props.get("Reference", "")
        if ref.startswith("#") or "(in_bom no)" in block or "(dnp yes)" in block:
            continue
        value, footprint = props.get("Value", ""), props.get("Footprint", "")
        assignment = None if ref in HOLDS else ALL_ASSIGNMENTS.get(ref)
        mpn = props.get("MPN")
        if mpn:
            if assignment and mpn != assignment[1]:
                raise ValueError(f"{ref}: source MPN {mpn} differs from radio catalog {assignment[1]}")
        elif assignment:
            manufacturer, mpn, _ = assignment
            at = re.search(r"\(at ([^\)]+)\)", block)
            if at is None:
                raise ValueError(f"{ref}: missing symbol position")
            block = patch_component_block(block, at.group(1), manufacturer, mpn)
            sheet.body[index] = block
        else:
            raise ValueError(f"{ref}: missing radio order code for {value} / {footprint}")
        errors = identity_errors(value, footprint, mpn)
        if errors:
            raise ValueError(f"{ref} ({mpn}): " + "; ".join(errors))
    return sheet


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    do_apply = "--apply" in sys.argv

    print("=" * 72)
    print("RADIO DAUGHTERBOARD BOM CATALOG APPLICATION")
    print("=" * 72)
    print(f"\nCatalog summary:")
    print(f"  Resistors assigned:  {len(RESISTOR_ASSIGNMENTS)}")
    print(f"  Capacitors assigned: {len(CAPACITOR_ASSIGNMENTS)}")
    print(f"  Holds:               {len(HOLDS)}")
    print(f"  Total assignments:   {len(ALL_ASSIGNMENTS)}")

    if not do_apply:
        print("\nDRY RUN — use --apply to patch")
    else:
        print(f"\n{'APPLYING' if do_apply else 'DRY RUN'} — patching schematic files:\n")

    # Patch each schematic sheet
    sheet_order = [
        ("01_core.kicad_sch", "01_core"),
        ("02_radios.kicad_sch", "02_radios"),
        ("03_gnss.kicad_sch", "03_gnss"),
        ("04_codec.kicad_sch", "04_codec"),
    ]

    total_patched = 0
    total_already = 0
    total_not_found = 0

    for sch_name, label in sheet_order:
        sch_path = RADIO / sch_name
        if not sch_path.exists():
            print(f"  ! {sch_name}: not found")
            continue

        result = patch_schematic_file(sch_path, ALL_ASSIGNMENTS, HOLDS, dry_run=not do_apply)

        status = "✓" if result.skipped_not_found == [] else "!"
        print(f"  {status} {sch_name}: {len(result.to_patch)} patched, "
              f"{len(result.skipped_hold)} holds, "
              f"{len(result.skipped_already_assigned)} already assigned")

        total_patched += len(result.to_patch)
        total_already += len(result.skipped_already_assigned)
        total_not_found += len(result.skipped_not_found)

        if result.skipped_not_found:
            print(f"         NOT FOUND: {', '.join(result.skipped_not_found)}")

    print(f"\n  Totals:")
    print(f"    Patched:          {total_patched}")
    print(f"    Already assigned: {total_already}")
    print(f"    Not found:        {total_not_found}")
    print(f"    Intentional holds: {len(HOLDS)}")
    print()


if __name__ == "__main__":
    main()
