#!/usr/bin/env python3
"""Export the installed board outlines, connectors, and mounting datums.

Run with KiCad's Python from the project root. Board placement comes from
mechanical/board-placement.json; footprint positions come from the PCBs.
"""
import hashlib
import html
import json
import math
from pathlib import Path

import wx
app = wx.App(False)
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / "mechanical/board-placement.json").read_text())
colors = {"left": "#d5e8dc", "center": "#c3ddce", "right": "#d5e8dc", "bms": "#c2ddeb"}
svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -16 382 277" width="1528" height="1108">',
       '<rect x="-12" y="-16" width="382" height="277" fill="#faf9f4"/>',
       '<g font-family="sans-serif" fill="#20352a">',
       '<text x="0" y="-6" font-size="5">ducktop2 board placement</text>',
       '<text x="358" y="-6" font-size="3" text-anchor="end">top view · dimensions in mm</text>']
data = {"units": "mm", "boards": {}}
loaded = {}

def xy(point):
    return [point.x / 1e6, point.y / 1e6]

def transform(point, spec):
    angle = math.radians(-spec["rotation"])
    c, s = math.cos(angle), math.sin(angle)
    x, y = point
    return [round(c*x-s*y+spec["translation"][0], 6),
            round(s*x+c*y+spec["translation"][1], 6)]

def ring(poly, spec):
    return [transform(xy(poly.CPoint(i)), spec) for i in range(poly.PointCount())]

def path_text(points):
    return "M " + " L ".join(f"{x:.6f},{y:.6f}" for x, y in points) + " Z"

def label(x, y, text, size=2.2, color="#344e40"):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="middle">{html.escape(text)}</text>')

for name, spec in config["boards"].items():
    source = ROOT / spec["file"]
    board = pcb.LoadBoard(str(source))
    loaded[name] = board
    outline = pcb.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False), f"invalid {name} outline"
    paths, outlines = [], []
    for i in range(outline.OutlineCount()):
        outer = ring(outline.COutline(i), spec)
        holes = [ring(outline.CHole(i, h), spec) for h in range(outline.HoleCount(i))]
        outlines.append({"outer": outer, "holes": holes})
        paths.extend(path_text(points) for points in [outer, *holes])
    svg.append(f'<path d="{" ".join(paths)}" fill="{colors[name]}" stroke="#365846" stroke-width=".35" fill-rule="evenodd"/>')
    entries = []
    mounts = []
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        pos = transform(xy(footprint.GetPosition()), spec)
        if ref.startswith(("J", "FPC", "H")) or ref in ("A1", "F1", "F190", "F195", "SW900"):
            footprint.BuildCourtyardCaches()
            cy = footprint.GetCourtyard(pcb.F_CrtYd)
            bounds = []
            for i in range(cy.OutlineCount()):
                points = ring(cy.COutline(i), spec)
                bounds.extend(points)
                svg.append(f'<path d="{path_text(points)}" fill="#ffffff" fill-opacity=".34" stroke="#658875" stroke-width=".15"/>')
            entries.append({"reference": ref, "position": pos,
                            "rotation": (footprint.GetOrientationDegrees()+spec["rotation"]) % 360,
                            "courtyard": bounds})
            if ref.startswith(("J", "FPC")) or ref == "A1":
                label(pos[0], pos[1], ref, 1.9)
        if ref.startswith("H"):
            for pad in footprint.Pads():
                drill = xy(pad.GetDrillSize())
                if drill[0] > 0:
                    point = transform(xy(pad.GetPosition()), spec)
                    mounts.append({"reference": ref, "position": point, "drill": drill})
                    svg.append(f'<circle cx="{point[0]}" cy="{point[1]}" r="{drill[0]/2}" fill="#faf9f4" stroke="#517261" stroke-width=".15"/>')
    for graphic in board.GetDrawings():
        if isinstance(graphic, pcb.PCB_SHAPE) and graphic.GetLayer() == pcb.Edge_Cuts and graphic.GetShape() == pcb.SHAPE_T_CIRCLE:
            point = transform(xy(graphic.GetCenter()), spec)
            mounts.append({"reference": None, "position": point, "drill": [graphic.GetRadius()/5e5]*2})
    data["boards"][name] = {"file": spec["file"], "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                            "outlines": outlines, "connectors_and_supports": entries, "mounting_holes": mounts}
    footprint_positions = {f.GetReference(): xy(f.GetPosition()) for f in board.GetFootprints()}
    for zone in board.Zones():
        if zone.GetIsRuleArea() and zone.GetZoneName().startswith("mount "):
            ref = zone.GetZoneName()[6:]
            assert ref in footprint_positions, f"{name} keepout has no matching mount: {ref}"
            center = xy(zone.GetBoundingBox().GetCenter())
            assert math.dist(center, footprint_positions[ref]) < .01, f"{name} {ref} keepout is out of position"

center = next(f for f in loaded["center"].GetFootprints() if f.GetReference() == "FPC105")
bms = next(f for f in loaded["bms"].GetFootprints() if f.GetReference() == "FPC106")
mount_checks = {}
center_parts = {f.GetReference(): f for f in loaded["center"].GetFootprints()}
for name, card in config["m2_cards"].items():
    socket = center_parts[card["socket"]]
    pads = {pad.GetNumber(): pad for pad in socket.Pads()}
    first, last, opposite = [xy(pads[n].GetPosition()) for n in ("1", "75", "2")]
    length = math.dist(first, last)
    x_axis = [(last[i]-first[i])/length for i in (0, 1)]
    y_axis = [-x_axis[1], x_axis[0]]
    if sum((opposite[i]-first[i])*y_axis[i] for i in (0, 1)) < 0:
        y_axis = [-v for v in y_axis]
    nut = xy(center_parts[card["retainer"]].GetPosition())
    offset = [sum((nut[i]-first[i])*axis[i] for i in (0, 1)) for axis in (x_axis, y_axis)]
    assert max(abs(offset[i]-card["retainer_from_pad1_local"][i]) for i in (0, 1)) < .01, f"{name} socket and retainer do not line up"
    mount_checks[name] = {"socket": card["socket"], "retainer": card["retainer"], "local_offset": offset}
data["m2_mount_checks"] = mount_checks
cp = {p.GetNumber(): p for p in center.Pads()}
bp = {p.GetNumber(): p for p in bms.Pads()}
for number in range(1, 31):
    a, z = cp[str(number)], bp[str(31-number)]
    ac = transform(xy(a.GetPosition()), config["boards"]["center"])
    bc = transform(xy(z.GetPosition()), config["boards"]["bms"])
    assert abs(ac[0]-bc[0]) < .00001, f"FPC-3 conductor {number} misaligned"
    assert a.GetNetname().rsplit("/", 1)[-1] == z.GetNetname().rsplit("/", 1)[-1], f"FPC-3 conductor {number} net mismatch"
a = transform(xy(center.GetPosition()), config["boards"]["center"])
z = transform(xy(bms.GetPosition()), config["boards"]["bms"])
y0, y1 = a[1]+4.4, z[1]-4.4
svg.append(f'<rect x="{a[0]-8.5}" y="{y0}" width="17" height="{y1-y0}" fill="#ead399" fill-opacity=".75" stroke="#ac8230" stroke-width=".25"/>')
label(185, 175, "bms", 4, "#28586d")
label(185, 180, "1.5 mm board clearance", 2.3, "#28586d")
for x, text in [(35, "left I/O"), (185, "center"), (329, "right I/O")]:
    label(x, 92, text, 4)
for x, text in [(5, "cell A"), (129, "cell B"), (253, "cell C")]:
    svg.append(f'<rect x="{x}" y="188" width="100" height="60" rx="2" fill="#e5e1d7" stroke="#a7a08e" stroke-width=".3"/>')
    label(x+50, 222, text, 3.5, "#655f50")
svg.append('<rect x="109" y="143" width="140" height="105" rx="2" fill="none" stroke="#8c8371" stroke-width=".3" stroke-dasharray="2 2"/>')
label(179, 240, "trackpad above the front area", 2.8, "#655f50")
label(179, 255, "board XY placement; case height, cable loops and supports still need a measured fit", 2.7)
svg.append('</g></svg>')
data["fpc3"] = {"pin_map_checked": 30, "actuator_envelope_gap": round(y1-y0, 6),
                 "center_position": a, "bms_position": z}
(ROOT / "mechanical/board-layout.svg").write_text("\n".join(svg)+"\n")
(ROOT / "mechanical/board-datums.json").write_text(json.dumps(data, indent=2)+"\n")
print("exported four board outlines and mounting datums; all 30 FPC-3 conductors align")
