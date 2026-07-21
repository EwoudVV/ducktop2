#!/usr/bin/env python3
"""Report schematic-to-PCB drift without modifying the PCB.

This is deliberately separate from ``sync_main_pcb_from_netlist.py``.  It may
export a fresh XML netlist and write reports under ``verification/``, but it
only reads ``ducktop2.kicad_pcb`` and asserts that the board hash is unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "ducktop2.kicad_pcb"
SCHEMATIC = ROOT / "ducktop2.kicad_sch"
NETLIST = ROOT / "verification" / "ducktop2_netlist.xml"
REPORT = ROOT / "verification" / "SCHEMATIC_TO_PCB_ECO_2026-07-20.md"
NET_CSV = ROOT / "verification" / "schematic_to_pcb_eco_net_changes.csv"
FOOTPRINT_CSV = ROOT / "verification" / "schematic_to_pcb_eco_footprint_changes.csv"
ATTRIBUTE_CSV = ROOT / "verification" / "schematic_to_pcb_eco_attribute_changes.csv"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_parsers():
    """Load only the proven netlist/S-expression parsers from the sync helper."""
    path = ROOT / "gen" / "sync_main_pcb_from_netlist.py"
    spec = importlib.util.spec_from_file_location("ducktop2_sync_parser", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parser from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def export_netlist() -> None:
    NETLIST.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(KICAD_CLI),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(NETLIST),
            str(SCHEMATIC),
        ],
        check=True,
        cwd=ROOT,
    )


def board_pad_nets(parser, block: str) -> dict[str, str | None]:
    nets: dict[str, str | None] = {}
    for _, _, pad in parser.pad_blocks(block):
        pin = parser.pad_name(pad)
        match = re.search(r'\(net(?:\s+\d+)?\s+"([^"]*)"\)', pad)
        nets[pin] = match.group(1) if match else None
    return nets


def normalize_net(name: str | None) -> str | None:
    """Treat all KiCad-generated unconnected names as the same NC state."""
    if not name or name.startswith("unconnected-"):
        return None
    return name


def pin_sort_key(pin: str):
    return (not pin.isdigit(), int(pin) if pin.isdigit() else pin)


def markdown_refs(refs: list[str]) -> str:
    return ", ".join(f"`{ref}`" for ref in refs) if refs else "None"


def write_csv(path: Path, header: list[str], rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    parser_arg = argparse.ArgumentParser(description=__doc__)
    parser_arg.add_argument(
        "--no-export",
        action="store_true",
        help="use the existing verification/ducktop2_netlist.xml",
    )
    args = parser_arg.parse_args()

    before_hash = sha256(PCB)
    before_size = PCB.stat().st_size
    if not args.no_export:
        export_netlist()

    parser = load_parsers()
    schematic = parser.parse_netlist()
    netlist_root = ET.parse(NETLIST).getroot()
    excluded_from_board = {
        comp.get("ref") or ""
        for comp in netlist_root.findall(".//comp")
        if comp.find("property[@name='exclude_from_board']") is not None
    }
    schematic = {
        ref: comp for ref, comp in schematic.items() if ref not in excluded_from_board
    }
    pcb_text = PCB.read_text(encoding="utf-8")
    board = {item.ref: item for item in parser.footprints(pcb_text) if item.ref}

    missing = sorted(set(schematic) - set(board))
    extra = sorted(set(board) - set(schematic))
    footprint_changes: list[tuple[str, str, str, str]] = []
    net_changes: list[tuple[str, str, str, str, str]] = []
    attribute_changes: list[tuple[str, str, str, str, str]] = []

    for ref in sorted(set(schematic) & set(board)):
        wanted = schematic[ref]
        actual = board[ref]
        if wanted.footprint != actual.footprint:
            footprint_changes.append(
                (ref, wanted.sheetfile, actual.footprint, wanted.footprint)
            )
        actual_pads = board_pad_nets(parser, actual.text)
        for pin in sorted(set(wanted.pin_nets) | set(actual_pads), key=pin_sort_key):
            old_net = normalize_net(actual_pads.get(pin))
            new_net = normalize_net(wanted.pin_nets.get(pin))
            if old_net != new_net:
                net_changes.append(
                    (ref, wanted.sheetfile, pin, old_net or "NC", new_net or "NC")
                )
        actual_attributes = parser.footprint_attribute_flags(actual.text)
        for flag in ("exclude_from_bom", "dnp"):
            old_state = flag in actual_attributes
            new_state = flag in wanted.properties
            if old_state != new_state:
                attribute_changes.append(
                    (ref, wanted.sheetfile, flag, str(old_state), str(new_state))
                )

    after_hash = sha256(PCB)
    after_size = PCB.stat().st_size
    if (before_hash, before_size) != (after_hash, after_size):
        raise RuntimeError("PCB changed during read-only ECO report")

    write_csv(
        FOOTPRINT_CSV,
        ["reference", "sheet", "pcb_footprint", "schematic_footprint"],
        footprint_changes,
    )
    write_csv(
        NET_CSV,
        ["reference", "sheet", "pin", "pcb_net", "schematic_net"],
        net_changes,
    )
    write_csv(
        ATTRIBUTE_CSV,
        ["reference", "sheet", "attribute", "pcb_state", "schematic_state"],
        attribute_changes,
    )

    missing_by_sheet: dict[str, list[str]] = defaultdict(list)
    for ref in missing:
        missing_by_sheet[schematic[ref].sheetfile or "(root)"] .append(ref)
    net_counts = Counter(row[0] for row in net_changes)
    drift_count = (
        len(missing) + len(extra) + len(footprint_changes) + len(net_changes)
        + len(attribute_changes)
    )
    if drift_count:
        status_lines = [
            "> **Routing hold:** the current PCB is materially behind the current schematic.",
            "> Do not continue routing affected blocks until a controlled schematic-to-PCB",
            "> ECO is reviewed and applied. This report does not perform that update.",
        ]
        next_steps = [
            "## Recommended ECO Sequence",
            "",
            "1. Commit or externally back up the current board.",
            "2. Review the controlled ECO without applying it to the live board.",
            "3. Resolve every missing, obsolete, footprint, and pad-net change.",
            "4. Apply the ECO only after a copied-board trial passes DRC and integrity checks.",
            "5. Run this report again; all five difference counts must reach zero.",
        ]
    else:
        status_lines = [
            "> **ECO status: synchronized.** Schematic and PCB references, footprints, and",
            "> pad-net assignments match. This proves parity only; physical placement, DRC,",
            "> routing, and manufacturing release remain separate checks.",
        ]
        next_steps = [
            "## Next PCB Steps",
            "",
            "1. Complete and review physical placement for every functional block.",
            "2. Re-run DRC after each placement pass and resolve or document every violation.",
            "3. Route by subsystem, preserving the documented six-layer stackup and net classes.",
            "4. Re-run ERC, contracts, this ECO report, DRC, and manufacturing review before fab.",
        ]

    lines = [
        "# Schematic-to-PCB ECO Report",
        "",
        "This report is read-only with respect to `ducktop2.kicad_pcb`. It compares a fresh",
        "KiCad XML schematic netlist with the protected placement-stage board and normalizes KiCad's",
        "generated unconnected-net names to a single NC state.",
        "",
        "## Safety Check",
        "",
        f"- PCB bytes before/after: `{before_size}` / `{after_size}`",
        f"- PCB SHA-256 before/after: `{before_hash}` / `{after_hash}`",
        "- Result: PCB was not modified.",
        "",
        "## Summary",
        "",
        f"- Schematic components: **{len(schematic)}**",
        f"- PCB footprints: **{len(board)}**",
        f"- Schematic references missing from PCB: **{len(missing)}**",
        f"- Obsolete PCB references absent from schematic: **{len(extra)}**",
            f"- Existing references with changed footprints: **{len(footprint_changes)}**",
            f"- Existing pad assignments with changed nets: **{len(net_changes)}**",
            f"- Existing BOM/DNP attribute mismatches: **{len(attribute_changes)}**",
        "",
        *status_lines,
        "",
        "## Missing PCB References",
        "",
    ]
    for sheet, refs in sorted(missing_by_sheet.items()):
        lines.extend([f"### {sheet}", "", markdown_refs(refs), ""])

    lines.extend(["## Obsolete PCB References", "", markdown_refs(extra), ""])
    lines.extend(
        [
            "## Footprint Changes",
            "",
            "| Ref | Sheet | PCB footprint | Schematic footprint |",
            "|---|---|---|---|",
        ]
    )
    for ref, sheet, old, new in footprint_changes:
        lines.append(f"| `{ref}` | `{sheet or '(root)'}` | `{old}` | `{new}` |")

    lines.extend(
        [
            "",
            "## Pad-Net Change Hotspots",
            "",
            "| Ref | Changed pads |",
            "|---|---:|",
        ]
    )
    for ref, count in net_counts.most_common():
        lines.append(f"| `{ref}` | {count} |")

    lines.extend(
        [
            "",
            "## BOM/DNP Attribute Changes",
            "",
            "| Ref | Sheet | Attribute | PCB | Schematic |",
            "|---|---|---|---:|---:|",
        ]
    )
    for ref, sheet, flag, old, new in attribute_changes:
        lines.append(f"| `{ref}` | `{sheet}` | `{flag}` | {old} | {new} |")

    lines.extend(
        [
            "",
            "## Detailed Files",
            "",
            f"- Footprint changes: `{FOOTPRINT_CSV.relative_to(ROOT)}`",
            f"- Pad-net changes: `{NET_CSV.relative_to(ROOT)}`",
            f"- BOM/DNP attribute changes: `{ATTRIBUTE_CSV.relative_to(ROOT)}`",
            "",
            *next_steps,
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report: {REPORT.relative_to(ROOT)}")
    print(f"PCB SHA-256 unchanged: {before_hash}")
    print(
        f"missing={len(missing)} extra={len(extra)} "
        f"footprints={len(footprint_changes)} pad_nets={len(net_changes)} "
        f"attributes={len(attribute_changes)}"
    )


if __name__ == "__main__":
    main()
