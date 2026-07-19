#!/usr/bin/env python3
"""Generate reviewer inventories plus recursive, reproducible source provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERIFY = ROOT / "verification"
ROOT_SCHEMATIC = ROOT / "ducktop2.kicad_sch"
KIPRJMOD_PREFIX = "${KIPRJMOD}/"
SHEETFILE_RE = re.compile(r'\(property\s+"Sheetfile"\s+"([^"]+)"')
URI_RE = re.compile(r'\(uri\s+"([^"]+)"\)')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def natural_ref(ref: str) -> tuple[str, int, str]:
    prefix = "".join(ch for ch in ref if not ch.isdigit())
    digits = "".join(ch for ch in ref if ch.isdigit())
    return prefix, int(digits or 0), ref


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def local_table_paths(table: Path) -> list[Path]:
    """Resolve only ${KIPRJMOD} entries from a KiCad library table."""
    if not table.exists():
        raise RuntimeError(f"missing project library table: {table}")
    paths: list[Path] = []
    for uri in URI_RE.findall(table.read_text(encoding="utf-8")):
        if not uri.startswith(KIPRJMOD_PREFIX):
            continue
        path = (ROOT / uri[len(KIPRJMOD_PREFIX):]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"project-local URI escapes project root: {uri}") from exc
        if not path.exists():
            raise RuntimeError(f"project-local library path is missing: {path}")
        paths.append(path)
    return sorted(set(paths), key=relative)


def schematic_hierarchy(root_schematic: Path = ROOT_SCHEMATIC) -> list[Path]:
    """Walk the exact Sheetfile hierarchy rooted at ducktop2.kicad_sch."""
    pending = [root_schematic.resolve()]
    seen: set[Path] = set()
    while pending:
        schematic = pending.pop()
        if schematic in seen:
            continue
        if not schematic.exists():
            raise RuntimeError(f"referenced schematic is missing: {schematic}")
        try:
            schematic.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"schematic hierarchy escapes project root: {schematic}") from exc
        seen.add(schematic)
        text = schematic.read_text(encoding="utf-8")
        for sheetfile in SHEETFILE_RE.findall(text):
            child = (schematic.parent / sheetfile).resolve()
            if child not in seen:
                pending.append(child)
    return sorted(seen, key=relative)


def provenance_files() -> dict[str, list[Path]]:
    symbol_table = ROOT / "sym-lib-table"
    footprint_table = ROOT / "fp-lib-table"

    symbol_paths = set(local_table_paths(symbol_table))
    symbol_paths.update((ROOT / "gen").rglob("*.kicad_sym"))
    symbol_files = sorted(
        (path.resolve() for path in symbol_paths if path.is_file()),
        key=relative,
    )

    footprint_files: set[Path] = set()
    for library in local_table_paths(footprint_table):
        if not library.is_dir() or library.suffix != ".pretty":
            raise RuntimeError(f"project footprint library is not a .pretty directory: {library}")
        footprint_files.update(path.resolve() for path in library.rglob("*.kicad_mod"))

    groups = {
        "Schematic hierarchy": schematic_hierarchy(),
        "Generator and checker Python": sorted(
            (path.resolve() for path in (ROOT / "gen").rglob("*.py")),
            key=relative,
        ),
        "Project-local symbol libraries": symbol_files,
        "Project-local footprint libraries": sorted(footprint_files, key=relative),
        "KiCad project library tables": [symbol_table.resolve(), footprint_table.resolve()],
    }
    for label, paths in groups.items():
        if not paths:
            raise RuntimeError(f"provenance group is unexpectedly empty: {label}")
    return groups


def source_tree_sha256(groups: dict[str, list[Path]]) -> str:
    digest = hashlib.sha256()
    for label in sorted(groups):
        for path in groups[label]:
            digest.update(label.encode("utf-8"))
            digest.update(b"\0")
            digest.update(relative(path).encode("utf-8"))
            digest.update(b"\0")
            digest.update(sha256(path).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def export_netlist(netlist: Path) -> None:
    cli = shutil.which("kicad-cli")
    if cli is None:
        candidate = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
        if candidate.exists():
            cli = str(candidate)
    if cli is None:
        raise SystemExit("kicad-cli was not found")
    subprocess.run(
        [
            cli,
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(netlist),
            str(ROOT_SCHEMATIC),
        ],
        cwd=ROOT,
        check=True,
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_VERIFY,
        help="inventory destination (default: project verification/)",
    )
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="date token used in generated filenames (YYYY-MM-DD)",
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    netlist = output_dir / f"inventory_netlist_{args.date}.xml"
    component_csv = output_dir / "component_inventory.csv"
    bom_gap_csv = output_dir / "bom_release_gaps.csv"
    bom_gap_report = output_dir / f"BOM_RELEASE_GAPS_{args.date}.md"
    pin_csv = output_dir / "active_pin_inventory.csv"
    manifest = output_dir / f"INVENTORY_MANIFEST_{args.date}.md"

    export_netlist(netlist)
    root = ET.parse(netlist).getroot()
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    netlist_hash = sha256(netlist)
    schematic_hash = sha256(ROOT_SCHEMATIC)
    provenance = provenance_files()
    source_tree_hash = source_tree_sha256(provenance)

    components: dict[str, dict[str, str]] = {}
    for node in root.findall("./components/comp"):
        ref = node.get("ref") or ""
        libsource = node.find("libsource")
        props = {p.get("name") or "": p.get("value") or "" for p in node.findall("property")}
        sheetpath = node.find("sheetpath")
        components[ref] = {
            "ref": ref,
            "value": node.findtext("value") or "",
            "part": libsource.get("part") if libsource is not None else "",
            "lib": libsource.get("lib") if libsource is not None else "",
            "footprint": node.findtext("footprint") or "",
            "sheetfile": props.get("Sheetfile", ""),
            "sheetname": (sheetpath.get("names") if sheetpath is not None else props.get("Sheetname", "")) or "",
            "manufacturer": props.get("Manufacturer", ""),
            "mpn": props.get("MPN", ""),
            "procurement_class": props.get("ProcurementClass", ""),
            "assembly_id": props.get("AssemblyID", ""),
            "module_assembly_item": props.get("ModuleAssemblyItem", ""),
            "mating_housing": props.get("MatingHousing", ""),
            "contacts": props.get("Contacts", ""),
            "endpoint_assembly": props.get("EndpointAssembly", ""),
            "datasheet": node.findtext("datasheet") or props.get("Datasheet", ""),
            "description": node.findtext("description") or props.get("Description", ""),
            "dnp": "yes" if "dnp" in props else "no",
            "exclude_from_bom": "yes" if "exclude_from_bom" in props else "no",
            "exclude_from_board": "yes" if "exclude_from_board" in props else "no",
        }

    component_fields = [
        "ref", "value", "part", "lib", "footprint", "sheetfile", "sheetname",
        "manufacturer", "mpn", "procurement_class", "assembly_id",
        "module_assembly_item", "mating_housing", "contacts", "endpoint_assembly",
        "datasheet", "description", "dnp", "exclude_from_bom", "exclude_from_board",
        "source_netlist_sha256", "source_schematic_sha256", "source_tree_sha256", "generated_utc",
    ]
    with component_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=component_fields)
        writer.writeheader()
        for ref in sorted(components, key=natural_ref):
            row = dict(components[ref])
            row.update(
                source_netlist_sha256=netlist_hash,
                source_schematic_sha256=schematic_hash,
                source_tree_sha256=source_tree_hash,
                generated_utc=generated,
            )
            writer.writerow(row)

    controlled_non_mpn_classes = {
        "PCB copper test feature",
        "Owner-supplied measured module",
        "External pack harness component",
    }
    gap_rows: list[dict[str, str]] = []
    for ref in sorted(components, key=natural_ref):
        item = components[ref]
        if not item["footprint"] or item["exclude_from_bom"] == "yes" or item["dnp"] == "yes":
            continue
        reasons: list[str] = []
        controlled_class = item["procurement_class"] in controlled_non_mpn_classes
        if not controlled_class:
            if not item["manufacturer"]:
                reasons.append("missing Manufacturer")
            if not item["mpn"]:
                reasons.append("missing MPN")
        elif item["procurement_class"] != "PCB copper test feature" and not item["assembly_id"]:
            reasons.append("controlled non-MPN item missing AssemblyID")
        if reasons:
            gap_rows.append({
                "ref": ref,
                "value": item["value"],
                "footprint": item["footprint"],
                "sheetfile": item["sheetfile"],
                "procurement_class": item["procurement_class"],
                "reason": "; ".join(reasons),
            })

    gap_fields = ["ref", "value", "footprint", "sheetfile", "procurement_class", "reason"]
    with bom_gap_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=gap_fields)
        writer.writeheader()
        writer.writerows(gap_rows)

    gap_lines = [
        "# Ducktop2 BOM Release Gaps",
        "",
        f"Generated UTC: `{generated}`",
        f"Recursive source-tree SHA-256: `{source_tree_hash}`",
        f"Populated physical items missing controlled procurement identity: `{len(gap_rows)}`",
        "",
        "This report excludes DNP, exclude-from-BOM, and non-physical schematic symbols.",
        "PCB copper test features and controlled owner/external assemblies are accepted only through their explicit ProcurementClass and AssemblyID metadata.",
        "",
    ]
    if gap_rows:
        gap_lines.extend(["| Ref | Sheet | Reason |", "|---|---|---|"])
        gap_lines.extend(
            f"| `{row['ref']}` | `{row['sheetfile']}` | {row['reason']} |"
            for row in gap_rows
        )
    else:
        gap_lines.append("No uncontrolled procurement gaps were found.")
    bom_gap_report.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")

    pin_rows: list[dict[str, str]] = []
    for net in root.findall("./nets/net"):
        net_name = net.get("name") or ""
        for node in net.findall("node"):
            ref = node.get("ref") or ""
            if ref not in components:
                continue
            pin_rows.append({
                "sheetfile": components[ref]["sheetfile"],
                "ref": ref,
                "value": components[ref]["value"],
                "part": components[ref]["part"],
                "pin": node.get("pin") or "",
                "pin_name": node.get("pinfunction") or "",
                "pin_type": node.get("pintype") or "",
                "net": net_name,
                "source_netlist_sha256": netlist_hash,
                "source_schematic_sha256": schematic_hash,
                "source_tree_sha256": source_tree_hash,
                "generated_utc": generated,
            })
    pin_rows.sort(key=lambda row: (natural_ref(row["ref"]), row["pin"], row["net"]))
    pin_fields = [
        "sheetfile", "ref", "value", "part", "pin", "pin_name", "pin_type", "net",
        "source_netlist_sha256", "source_schematic_sha256", "source_tree_sha256", "generated_utc",
    ]
    with pin_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=pin_fields)
        writer.writeheader()
        writer.writerows(pin_rows)

    net_count = len(root.findall("./nets/net"))
    active_custom_names = sorted({
        item["footprint"].split(":", 1)[1]
        for item in components.values()
        if item["footprint"].startswith("ducktop2:")
    })
    active_custom_lines = []
    for name in active_custom_names:
        path = ROOT / "ducktop2.pretty" / f"{name}.kicad_mod"
        if not path.exists():
            raise SystemExit(f"missing active custom footprint source: {path}")
        pad_count = path.read_text(encoding="utf-8").count("(pad ")
        active_custom_lines.append(f"- `{name}`: `{sha256(path)}` ({pad_count} pad records)")

    manifest_lines = [
        "# Ducktop2 Inventory Manifest",
        "",
        f"Generated UTC: `{generated}`",
        f"Root schematic SHA-256: `{schematic_hash}`",
        f"Normalized XML netlist SHA-256: `{netlist_hash}`",
        f"Recursive source-tree SHA-256: `{source_tree_hash}`",
        f"Components: `{len(components)}`",
        f"Connected pin rows: `{len(pin_rows)}`",
        f"Nets: `{net_count}`",
        "",
        "The CSV inventories are valid only when all three embedded hashes match this manifest.",
        "The recursive digest covers the live hierarchy, every generator/checker Python file, all project-local symbol libraries, every footprint in each project-local .pretty library, and both library tables.",
        "Older inventory counts and retired design rows are historical and must not be used for procurement.",
        "",
    ]
    for label, paths in provenance.items():
        manifest_lines.extend([f"## {label}", ""])
        manifest_lines.extend(f"- `{relative(path)}`: `{sha256(path)}`" for path in paths)
        manifest_lines.append("")
    manifest_lines.extend([
        "## Active ducktop2 Footprints in the Netlist",
        "",
        "These active-source hashes are a convenience subset; the project-local footprint section above is authoritative and complete.",
        "",
        *active_custom_lines,
        "",
    ])
    manifest.write_text("\n".join(manifest_lines), encoding="utf-8")

    print(f"components={len(components)} connected_pins={len(pin_rows)} nets={net_count}")
    print(f"bom_release_gaps={len(gap_rows)}")
    print(f"netlist_sha256={netlist_hash}")
    print(f"source_tree_sha256={source_tree_hash}")
    print(
        "provenance="
        + ", ".join(f"{label}:{len(paths)}" for label, paths in provenance.items())
    )


if __name__ == "__main__":
    main()
