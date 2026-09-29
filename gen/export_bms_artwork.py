#!/usr/bin/env python3
"""Render the checked BMS Gerbers as front and back artwork previews."""

from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET

from gerbonara import LayerStack

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package", type=Path, default=ROOT / "manufacturing/bms/pcbway"
    )
    args = parser.parse_args()
    package = args.package.resolve()
    manifest = json.loads((package / "manifest.json").read_text())
    board = ROOT / "bms/bms.kicad_pcb"
    sha = hashlib.sha256(board.read_bytes()).hexdigest()
    assert manifest["source_sha256"]["bms/bms.kicad_pcb"] == sha, "package is stale"
    renderer = shutil.which("inkscape")
    if renderer is None:
        candidate = Path("/Applications/Inkscape.app/Contents/MacOS/inkscape")
        if candidate.is_file():
            renderer = str(candidate)
    if renderer is None:
        raise RuntimeError("Inkscape is needed to render the Gerber SVG previews")
    stack = LayerStack.open(package / "gerbers")
    datums = json.loads((ROOT / "mechanical/board-datums.json").read_text())["boards"][
        "bms"
    ]
    placement = json.loads((ROOT / "mechanical/board-placement.json").read_text())[
        "boards"
    ]["bms"]
    assert (
        datums["sha256"] == sha and placement["rotation"] == 0
    ), "refresh board datums"
    dx, dy = placement["translation"]
    out = ROOT / "manufacturing/bms"
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    for name, side in [("front", "top"), ("back", "bottom")]:
        svg = out / (name + "-artwork.svg")
        drawing = ET.fromstring(str(stack.to_pretty_svg(side=side, margin=1)))
        # The Gerber renderer closes a full-circle edge as a half disk. Apply
        # the native circular cutouts to the entire artwork, including mask.
        x, y, width, height = map(float, drawing.attrib["viewBox"].split())
        defs = drawing.find("{" + ns + "}defs")
        cutouts = ET.SubElement(
            defs,
            "{" + ns + "}mask",
            {
                "id": "mount-cutouts",
                "maskUnits": "userSpaceOnUse",
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
            },
        )
        ET.SubElement(
            cutouts,
            "{" + ns + "}rect",
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "fill": "white",
            },
        )
        for hole in datums["mounting_holes"]:
            px, py = hole["position"]
            ET.SubElement(
                cutouts,
                "{" + ns + "}circle",
                {
                    "cx": str(px - dx),
                    "cy": str(2 * y + height + py - dy),
                    "r": str(hole["drill"][0] / 2),
                    "fill": "black",
                },
            )
        drawing.find("{" + ns + "}g").set("mask", "url(#mount-cutouts)")
        svg.write_text(ET.tostring(drawing, encoding="unicode") + "\n")
        subprocess.run(
            [
                renderer,
                str(svg),
                "--export-width=1800",
                "--export-filename=" + str(out / (name + ".png")),
            ],
            check=True,
        )
    (out / "preview-source.json").write_text(
        json.dumps(
            {
                "board": "bms/bms.kicad_pcb",
                "board_sha256": sha,
                "gerbers": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((package / "gerbers").iterdir())
                },
                "view": "board artwork, without component bodies; back viewed from underneath",
                "mounting_cutouts": "native circles from matching board datums",
            },
            indent=2,
        )
        + "\n"
    )
    print("front and back artwork previews match the checked package")


if __name__ == "__main__":
    main()
