#!/usr/bin/env python3
"""Export BMS assembly drawings from a display copy; keep the PCB unchanged."""

import sys, csv, hashlib, json, subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

if "--headless" not in sys.argv:
    import wx

    app = wx.App(False)
    wx.Log.EnableLogging(False)
import pcbnew as p

root = Path(__file__).resolve().parents[1]
source = root / "bms/bms.kicad_pcb"
out = root / "manufacturing/bms"
scratch = root / ".workbench/bms-assembly-export"
scratch.mkdir(parents=True, exist_ok=True)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
b = p.LoadBoard(str(source))
rows = []
for f in b.GetFootprints():
    ref = f.GetReference()
    side = "bottom" if f.GetLayer() == p.B_Cu else "top"
    f.Value().SetVisible(False)
    if ref.startswith("TPB"):
        pad = next(iter(f.Pads()))
        rows.append(
            [
                ref,
                pad.GetNetname(),
                round(pad.GetPosition().x / 1e6, 6),
                round(pad.GetPosition().y / 1e6, 6),
                side,
                ref[3:] if ref != "TPB14" else "14 (stacked)",
            ]
        )
    if not any(
        isinstance(i, p.PCB_TEXT) and i.GetText() == "${REFERENCE}"
        for i in f.GraphicalItems()
    ):
        t = p.PCB_TEXT(f)
        t.SetText("${REFERENCE}")
        t.SetLayer(p.B_Fab if side == "bottom" else p.F_Fab)
        t.SetPosition(f.GetPosition())
        t.SetTextSize(p.VECTOR2I(650000, 650000))
        t.SetTextThickness(100000)
        t.SetMirrored(side == "bottom")
        f.Add(t)
    for t in f.GraphicalItems():
        if not isinstance(t, p.PCB_TEXT) or t.GetText() != "${REFERENCE}":
            continue
        t.SetPosition(f.GetPosition())
        t.SetTextThickness(80000)
        if ref.startswith("TPB"):
            t.SetText("TPB\n" + ref[3:])
            t.SetMultilineAllowed(True)
            t.SetTextSize(p.VECTOR2I(420000, 420000))
            t.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
        else:
            shapes = [
                i.GetBoundingBox()
                for i in f.GraphicalItems()
                if isinstance(i, p.PCB_SHAPE)
                and i.GetLayer() == (p.B_Fab if side == "bottom" else p.F_Fab)
            ]
            if shapes:
                x0 = min(r.GetLeft() for r in shapes)
                x1 = max(r.GetRight() for r in shapes)
                y0 = min(r.GetTop() for r in shapes)
                y1 = max(r.GetBottom() for r in shapes)
                t.SetPosition(p.VECTOR2I((x0 + x1) // 2, (y0 + y1) // 2))
                width = (x1 - x0) / 1e6
                height = (y1 - y0) / 1e6
                vertical = height > width * 1.3
                major, minor = (height, width) if vertical else (width, height)
                size = max(0.27, min(0.85, major / (len(ref) * 1.15), minor * 0.7))
                t.SetTextSize(p.VECTOR2I(round(size * 1e6), round(size * 1e6)))
                t.SetTextThickness(round(min(0.08, size * 0.14) * 1e6))
                t.SetTextAngle(p.EDA_ANGLE(90 if vertical else 0, p.DEGREES_T))
                if ref == "D2200":
                    position = t.GetPosition()
                    t.SetPosition(p.VECTOR2I(position.x, position.y + 1200000))
                    t.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
p.SaveBoard(str(scratch / "bms.kicad_pcb"), b)
cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
for name, layer, mirror in [("front", "F.Fab", False), ("back", "B.Fab", True)]:
    args = [
        cli,
        "pcb",
        "export",
        "svg",
        "--layers",
        layer + ",Edge.Cuts",
        "--mode-single",
        "--page-size-mode",
        "2",
        "--exclude-drawing-sheet",
        "--black-and-white",
        "--output",
        str(out / (name + "-assembly.svg")),
    ]
    if mirror:
        args += ["--mirror"]
    args += [str(scratch / "bms.kicad_pcb")]
    subprocess.run(args, check=True)
    file = out / (name + "-assembly.svg")
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    drawing = ET.fromstring(file.read_text())
    defs = ET.SubElement(drawing, "{" + ns + "}defs")
    halo = ET.SubElement(
        defs,
        "{" + ns + "}filter",
        {
            "id": "reference-halo",
            "x": "-30%",
            "y": "-30%",
            "width": "160%",
            "height": "160%",
        },
    )
    ET.SubElement(
        halo,
        "{" + ns + "}feMorphology",
        {
            "in": "SourceAlpha",
            "operator": "dilate",
            "radius": "0.055",
            "result": "expanded",
        },
    )
    ET.SubElement(
        halo, "{" + ns + "}feFlood", {"flood-color": "white", "result": "paper"}
    )
    ET.SubElement(
        halo,
        "{" + ns + "}feComposite",
        {"in": "paper", "in2": "expanded", "operator": "in", "result": "halo"},
    )
    merge = ET.SubElement(halo, "{" + ns + "}feMerge")
    ET.SubElement(merge, "{" + ns + "}feMergeNode", {"in": "halo"})
    ET.SubElement(merge, "{" + ns + "}feMergeNode", {"in": "SourceGraphic"})
    parents = {child: parent for parent in drawing.iter() for child in parent}
    for group in list(drawing.iter("{" + ns + "}g")):
        if group.get("class") == "stroked-text":
            group.set("filter", "url(#reference-halo)")
            chain = []
            parent = parents[group]
            while parent is not drawing:
                chain.append(parent)
                parent = parents[parent]
            group.set("style", ";".join(a.get("style", "") for a in reversed(chain)))
            transforms = " ".join(
                a.get("transform", "") for a in reversed(chain)
            ).strip()
            if transforms:
                group.set("transform", transforms)
            parents[group].remove(group)
            drawing.append(group)
    file.write_text(
        "\n".join(
            line.rstrip()
            for line in ET.tostring(drawing, encoding="unicode").splitlines()
        )
        + "\n"
    )
with (out / "test-points.csv").open("w") as stream:
    w = csv.writer(stream, lineterminator="\n")
    w.writerow(["reference", "net", "pcb_x_mm", "pcb_y_mm", "side", "board_mark"])
    w.writerows(sorted(rows, key=lambda x: int(x[0][3:])))
(out / "assembly-source.json").write_text(
    json.dumps(
        dict(
            board="bms/bms.kicad_pcb",
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            front_view="top",
            back_view="bottom, mirrored",
            test_point_coordinates="native board coordinates in mm",
            rendering="values hidden; reference labels sized and centered on the component bodies, with white halos; component geometry unchanged",
        ),
        indent=2,
    )
    + "\n"
)
assert (
    hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
), "source changed during export"
print("assembly views and", len(rows), "test points exported")
