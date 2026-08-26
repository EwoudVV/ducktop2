#!/usr/bin/env python3
"""Regenerate the NextPCB mainboard BOM/CPL quote package (2026-08-26).

The previously committed package predates the J2300 FH12-30S redesign and
the J24/J25 USB-A cluster, and still placed the retired R1730-R1733 straps.
This tool rebuilds both CSVs from the CURRENT schematic netlist and PCB so a
quote can never describe a different board revision.  It also writes a
manifest binding the outputs to source hashes and asserting the must-have /
must-not-exist reference sets from the 2026-08-26 design review.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync_main_pcb_from_netlist as sync

ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / "ducktop2.kicad_sch"
PCB = ROOT / "ducktop2.kicad_pcb"
OUT_DIR = ROOT / "manufacturing" / "nextpcb_quote"

# Post-8862f57 identities: active cluster + DFU mux must be present; retired
# coin-cell header and disable straps must never return.
MUST_INCLUDE = {"J24", "J25", "Q62"}
MUST_EXCLUDE = {"J9", "R1730", "R1731", "R1732", "R1733"}
# Intentionally footprint-less schematic entries (2026-08-26 review):
# A2 LattePanda Mu module, J8/J50 DNP debug headers.
EXPECTED_SCHEMATIC_ONLY = {"A2", "J8", "J50"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(*args: str) -> None:
    cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    subprocess.run([cli, *args], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)


def load_netlist() -> tuple[dict[str, dict], None]:
    netlist_path = OUT_DIR / ".netlist_export.xml"
    run_cli("sch", "export", "netlist", "--format", "kicadxml",
            "--output", str(netlist_path), SCHEMATIC.name)
    root = ET.parse(netlist_path).getroot()
    comps: dict[str, dict] = {}
    for node in root.findall(".//comp"):
        ref = node.get("ref") or ""
        value = (node.findtext("value") or "").strip()
        footprint = (node.findtext("footprint") or "").strip()
        props = {p.get("name"): (p.text or "").strip()
                 for p in node.findall("./fields/field")}
        dnp = ("dnp" in props or "DNP" in value.upper())
        excluded = "exclude_from_bom" in props
        comps[ref] = {
            "value": value,
            "footprint": footprint,
            "manufacturer": props.get("Manufacturer", ""),
            "mpn": props.get("MPN", ""),
            "sheet": "",
            "exclude": bool(excluded),
            "dnp": bool(dnp),
        }
    netlist_path.unlink()
    return comps


def board_positions() -> dict[str, tuple[float, float, float, str]]:
    """Footprint placements via the audited sync parser (Reference order and
    footprint-internal layout are guaranteed by that toolchain).  CPL Y is
    negated to the legacy quote coordinate convention."""
    text = PCB.read_text(encoding="utf-8")
    positions: dict[str, tuple[float, float, float, str]] = {}
    for footprint in sync.footprints(text):
        x, y, rot = sync.at_tuple(footprint.text)
        side = "bottom" if '(layer "B.Cu")' in footprint.text else "top"
        positions[footprint.ref] = (x, -y, rot % 360, side)
    return positions


def write_bom(comps: dict[str, dict]) -> int:
    groups: dict[tuple, list[str]] = defaultdict(list)
    for ref, item in sorted(comps.items()):
        if item["exclude"] or not ref[0].isalpha():
            continue
        key = (item["value"], item["footprint"], item["manufacturer"],
               item["mpn"], "DNP" if item["dnp"] else "")
        groups[key].append(ref)

    path = OUT_DIR / "mainboard_bom.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(["Designator", "Value", "Footprint", "Qty",
                         "Manufacturer", "MPN", "DNP", "Sheet"])
        total = 0
        for key, refs in sorted(groups.items()):
            value, footprint, manufacturer, mpn, dnp = key
            writer.writerow([",".join(refs), value, footprint, len(refs),
                             manufacturer, mpn, dnp, ""])
            total += len(refs)
    return total


def write_cpl(comps: dict[str, dict], positions) -> int:
    path = OUT_DIR / "mainboard_cpl.csv"
    rows = []
    for ref, item in sorted(comps.items()):
        if item["exclude"] or item["dnp"] or not item["footprint"]:
            continue
        pos = positions.get(ref)
        if pos is None:
            raise RuntimeError(f"CPL: board position missing for {ref}")
        package = item["footprint"].split(":", 1)[1]
        rows.append((ref, item["value"], package, *pos))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(["Ref", "Val", "Package", "PosX", "PosY", "Rot", "Side"])
        for row in rows:
            writer.writerow([row[0], row[1], row[2],
                             f"{row[3]:.6f}", f"{row[4]:.6f}",
                             f"{row[5]:.6f}", row[6]])
    return len(rows)


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    comps = load_netlist()
    positions = board_positions()

    missing_board = sorted(set(comps) - set(positions))
    unexpected_only = sorted(set(missing_board) - EXPECTED_SCHEMATIC_ONLY)
    extra_board = sorted(set(positions) - set(comps))

    bom_refs = {ref for ref, item in comps.items()
                if not item["exclude"] and not item["dnp"] and item["footprint"]}
    cpl_refs = set(positions)
    problems = []
    for ref in MUST_INCLUDE:
        if ref not in bom_refs or ref not in cpl_refs:
            problems.append(f"required reference absent from package: {ref}")
    for ref in MUST_EXCLUDE & (bom_refs | cpl_refs):
        problems.append(f"retired reference present in package: {ref}")
    for ref in missing_board:
        if ref in unexpected_only:
            problems.append(f"schematic component without board instance: {ref}")

    bom_count = write_bom(comps)
    cpl_count = write_cpl(comps, positions)

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "gen/generate_nextpcb_mainboard_package.py",
        "sources": {
            "schematic_sha256": sha256(SCHEMATIC),
            "pcb_sha256": sha256(PCB),
        },
        "outputs": {
            "bom_rows_components": bom_count,
            "cpl_rows_placements": cpl_count,
            "bom_sha256": sha256(OUT_DIR / "mainboard_bom.csv"),
            "cpl_sha256": sha256(OUT_DIR / "mainboard_cpl.csv"),
        },
        "parity": {
            "must_include_present": sorted(MUST_INCLUDE - (bom_refs & cpl_refs)) == [],
            "must_exclude_absent": sorted(MUST_EXCLUDE & (bom_refs | cpl_refs)) == [],
            "expected_schematic_only_present": sorted(EXPECTED_SCHEMATIC_ONLY),
            "unexpected_schematic_only_refs": unexpected_only,
            "board_only_refs": extra_board,
        },
        "note": ("Legacy files retained under retired_pre_8862f57/; this "
                 "package supersedes them and binds to the sources above."),
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    print(json.dumps(manifest["parity"], indent=1))
    if problems:
        for problem in problems:
            print(f"PACKAGE PROBLEM: {problem}")
        return 1
    print(f"quote package regenerated: BOM {bom_count} components, "
          f"CPL {cpl_count} placements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
