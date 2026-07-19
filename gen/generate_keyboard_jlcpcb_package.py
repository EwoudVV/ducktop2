#!/usr/bin/env python3
"""Generate the JLCPCB fabrication and assembly package for the keyboard PCB."""

from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
BOARD = PROJECT_DIR / "12_keyboard_daughterboard.kicad_pcb"
OUTPUT = PROJECT_DIR / "manufacturing" / "keyboard_revA_jlcpcb"
REFERENCE = OUTPUT / "reference"
RAW = OUTPUT / "_raw"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

GERBER_LAYERS = (
    "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
)


def run(*args: str) -> None:
    subprocess.run([str(KICAD_CLI), *args], cwd=PROJECT_DIR, check=True)


def natural_ref_key(ref: str) -> tuple[str, int]:
    prefix = "".join(character for character in ref if not character.isdigit())
    suffix = "".join(character for character in ref if character.isdigit())
    return prefix, int(suffix or 0)


def comma_refs(prefix: str, first: int, last: int) -> str:
    return ",".join(f"{prefix}{number}" for number in range(first, last + 1))


def write_bom(path: Path) -> set[str]:
    rows = [
        {
            "Comment": "1N4148WS 100V switching diode",
            "Designator": comma_refs("D", 320, 384),
            "Footprint": "SOD-323",
            "JLCPCB Part #": "C2128",
        },
        {
            "Comment": "Hirose FH12-30S-0.5SH(55), 30-pin 0.5mm bottom-contact FFC",
            "Designator": "J320",
            "Footprint": "SMD 30P P0.50mm right-angle FFC",
            "JLCPCB Part #": "C506793",
        },
    ]

    with path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["Comment", "Designator", "Footprint", "JLCPCB Part #"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return {
        ref
        for row in rows
        for ref in row["Designator"].split(",")
    }


def write_cpl(
    raw_positions: Path,
    path: Path,
    included_refs: set[str],
) -> set[str]:
    with raw_positions.open(newline="", encoding="utf-8-sig") as input_file:
        rows = [
            row
            for row in csv.DictReader(input_file)
            if row["Ref"] in included_refs
        ]

    rows.sort(key=lambda row: natural_ref_key(row["Ref"]))
    with path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["Designator", "Mid X", "Mid Y", "Rotation", "Layer"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Designator": row["Ref"],
                    "Mid X": f'{float(row["PosX"]):.4f}mm',
                    "Mid Y": f'{float(row["PosY"]):.4f}mm',
                    "Rotation": f'{float(row["Rot"]) % 360:.2f}',
                    "Layer": "Top" if row["Side"].lower() == "top" else "Bottom",
                }
            )

    return {row["Ref"] for row in rows}


def copy_gerbers_to_upload_zip(zip_path: Path) -> list[str]:
    extension_names = {
        ".gtl": "ducktop2_keyboard_revA.GTL",
        ".gbl": "ducktop2_keyboard_revA.GBL",
        ".gts": "ducktop2_keyboard_revA.GTS",
        ".gbs": "ducktop2_keyboard_revA.GBS",
        ".gto": "ducktop2_keyboard_revA.GTO",
        ".gbo": "ducktop2_keyboard_revA.GBO",
        ".gm1": "ducktop2_keyboard_revA.GM1",
        ".gbrjob": "ducktop2_keyboard_revA.gbrjob",
    }
    archive_files: dict[str, Path] = {}

    for source in RAW.iterdir():
        destination = extension_names.get(source.suffix.lower())
        if destination:
            archive_files[destination] = source

    drill_files = sorted(RAW.glob("*.drl"))
    for source in drill_files:
        drill_type = "NPTH" if "NPTH" in source.name.upper() else "PTH"
        archive_files[f"ducktop2_keyboard_revA-{drill_type}.XLN"] = source

    expected = set(extension_names.values()) | {
        "ducktop2_keyboard_revA-PTH.XLN",
        "ducktop2_keyboard_revA-NPTH.XLN",
    }
    missing = sorted(expected - archive_files.keys())
    if missing:
        raise RuntimeError(f"Missing fabrication outputs: {', '.join(missing)}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for destination, source in sorted(archive_files.items()):
            archive.write(source, destination)

    return sorted(archive_files)


def write_readme(path: Path, gerber_files: list[str]) -> None:
    file_listing = "\n".join(f"- `{name}`" for name in gerber_files)
    path.write_text(
        f"""# Ducktop2 keyboard rev A: JLCPCB production package

## Upload these three files

1. `ducktop2_keyboard_revA_GERBERS.zip` in the PCB Gerber upload field.
2. `ducktop2_keyboard_revA_BOM.csv` in the PCBA BOM field.
3. `ducktop2_keyboard_revA_CPL.csv` in the PCBA CPL/Pick-and-Place field.

The BOM and CPL use JLCPCB's current required headers. Every designator in the
BOM appears in the CPL. All 66 JLCPCB placements are on the top side.

## PCB order selections

- 2 layers, FR-4, 1 oz copper
- Finished size: 273.5 x 80.0 mm
- PCB thickness: 0.8 mm
- Green solder mask and white silkscreen
- Economic PCBA-compatible finish: lead-free HASL
- Assembly side: top
- Remove the JLC order number, or approve its location manually

JLCPCB permits 0.8 mm Economic PCBA with green solder mask and lead-free HASL.
Because this is a long 0.8 mm board, expect a carrier/fixture charge.

## Parts

- D320-D384: JLCPCB basic part `C2128`, 1N4148WS, SOD-323.
- J320: LCSC/JLC part `C506793`, Hirose FH12-30S-0.5SH(55). Stock can change;
  pre-order/global-source it before submitting the PCBA order if requested.
- SW320-SW384: DNP for JLCPCB. Install CHERRY `MX6C-T3NB` switches separately
  using the user's stencil/paste and hot plate after receiving the boards.

Paste printed and reflowed on empty MX ULP pads can leave solder bumps that
prevent the switches from sitting flat. Copy the contents of
`PCBA_ORDER_REMARK.txt` into the order remarks and confirm the production file
does not print paste on SW320-SW384.

## Placement review

JLCPCB requires the customer to review the assembly preview. Before approval:

- Confirm every diode cathode stripe agrees with pad 1/the line on F.Fab.
- Confirm J320 is a bottom-contact connector and its FFC opening faces outward.
- Confirm SW320-SW384 are absent from the placement preview.
- Confirm the board outline is 273.5 x 80.0 mm, not 300 mm wide.

The CPL coordinates deliberately retain KiCad's Gerber coordinate system,
including negative Y values. The Gerbers and CPL therefore share the same
origin and orientation.

## Fabrication archive contents

{file_listing}

## Reference files

The `reference` directory is not uploaded in the normal order flow. It contains
the DRC report, assembly drawing, drill map, raw placement export, board stats,
IPC-D-356 netlist, and SHA-256 checksums.

Generated with KiCad 10.0.4 on 2026-07-08.
""",
        encoding="utf-8",
    )


def write_checksums(path: Path) -> None:
    files = [
        candidate
        for candidate in OUTPUT.rglob("*")
        if candidate.is_file()
        and candidate != path
        and "_raw" not in candidate.parts
    ]
    lines = []
    for candidate in sorted(files):
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        lines.append(f"{digest}  {candidate.relative_to(OUTPUT)}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    if not KICAD_CLI.exists():
        raise RuntimeError(f"KiCad CLI not found at {KICAD_CLI}")

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    RAW.mkdir(parents=True)
    REFERENCE.mkdir(parents=True)

    drc_report = REFERENCE / "ducktop2_keyboard_revA_DRC.txt"
    run(
        "pcb",
        "drc",
        "--output",
        str(drc_report),
        str(BOARD),
    )
    if "; error" in drc_report.read_text(encoding="utf-8"):
        raise RuntimeError("DRC contains errors; production package was not generated")

    run(
        "pcb",
        "export",
        "gerbers",
        "--output",
        str(RAW),
        "--layers",
        GERBER_LAYERS,
        "--precision",
        "6",
        str(BOARD),
    )
    run(
        "pcb",
        "export",
        "drill",
        "--output",
        str(RAW),
        "--format",
        "excellon",
        "--drill-origin",
        "absolute",
        "--excellon-units",
        "mm",
        "--excellon-zeros-format",
        "decimal",
        "--excellon-separate-th",
        str(BOARD),
    )
    run(
        "pcb",
        "export",
        "drill",
        "--output",
        str(REFERENCE),
        "--format",
        "excellon",
        "--drill-origin",
        "absolute",
        "--excellon-units",
        "mm",
        "--generate-map",
        "--map-format",
        "pdf",
        str(BOARD),
    )

    raw_positions = REFERENCE / "ducktop2_keyboard_revA_raw_positions.csv"
    run(
        "pcb",
        "export",
        "pos",
        "--output",
        str(raw_positions),
        "--format",
        "csv",
        "--units",
        "mm",
        "--side",
        "both",
        "--smd-only",
        str(BOARD),
    )
    run(
        "pcb",
        "export",
        "ipcd356",
        "--output",
        str(REFERENCE / "ducktop2_keyboard_revA.ipc"),
        str(BOARD),
    )
    run(
        "pcb",
        "export",
        "stats",
        "--output",
        str(REFERENCE / "ducktop2_keyboard_revA_stats.txt"),
        "--format",
        "report",
        "--units",
        "mm",
        str(BOARD),
    )
    run(
        "pcb",
        "export",
        "pdf",
        "--output",
        str(REFERENCE / "ducktop2_keyboard_revA_top_assembly.pdf"),
        "--layers",
        "F.Fab,F.Silkscreen,Edge.Cuts",
        "--mode-single",
        "--black-and-white",
        "--exclude-value",
        "--sketch-pads-on-fab-layers",
        "--scale",
        "0",
        str(BOARD),
    )

    bom_refs = write_bom(OUTPUT / "ducktop2_keyboard_revA_BOM.csv")
    cpl_refs = write_cpl(
        raw_positions,
        OUTPUT / "ducktop2_keyboard_revA_CPL.csv",
        bom_refs,
    )
    if bom_refs != cpl_refs:
        missing_from_cpl = sorted(bom_refs - cpl_refs, key=natural_ref_key)
        missing_from_bom = sorted(cpl_refs - bom_refs, key=natural_ref_key)
        raise RuntimeError(
            "BOM/CPL mismatch: "
            f"missing from CPL={missing_from_cpl}, "
            f"missing from BOM={missing_from_bom}"
        )
    if len(cpl_refs) != 66:
        raise RuntimeError(f"Expected 66 JLCPCB placements, got {len(cpl_refs)}")

    archive_files = copy_gerbers_to_upload_zip(
        OUTPUT / "ducktop2_keyboard_revA_GERBERS.zip"
    )
    write_readme(OUTPUT / "README_JLCPCB.md", archive_files)
    (OUTPUT / "PCBA_ORDER_REMARK.txt").write_text(
        "PARTIAL ASSEMBLY: Populate only D320-D384 and J320. "
        "SW320-SW384 are DNP and will be installed by the customer after "
        "delivery. Do not print or dispense solder paste on any SW320-SW384 "
        "pads. Please confirm the production paste data excludes all MX ULP "
        "switch pads. No switch substitutions are permitted.\n",
        encoding="ascii",
    )

    shutil.copy2(BOARD, REFERENCE / BOARD.name)
    shutil.rmtree(RAW)
    write_checksums(REFERENCE / "SHA256SUMS.txt")

    print(f"Generated {OUTPUT}")
    print(f"Gerber/drill files: {len(archive_files)}")
    print(f"Assembly placements: {len(cpl_refs)}")


if __name__ == "__main__":
    main()
