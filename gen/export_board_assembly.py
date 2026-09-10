#!/usr/bin/env python3
"""Export installed board outlines, connectors, datums and planner geometry.

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
wx.Log.EnableLogging(False)
import pcbnew as pcb
import fpc_contract as interconnect

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

def courtyard_rings(footprint, spec):
    footprint.BuildCourtyardCaches()
    result = {}
    for side, layer in (("front", pcb.F_CrtYd), ("back", pcb.B_CrtYd)):
        courtyard = footprint.GetCourtyard(layer)
        result[side] = [ring(courtyard.COutline(i), spec) for i in range(courtyard.OutlineCount())]
    return result

def rectangle(points):
    assert points, "empty mechanical envelope"
    x, y = min(p[0] for p in points), min(p[1] for p in points)
    return {"x": round(x, 6), "y": round(y, 6),
            "w": round(max(p[0] for p in points)-x, 6),
            "h": round(max(p[1] for p in points)-y, 6)}

def updated_floorplan():
    plan = json.loads((ROOT / "mechanical/floorplan.json").read_text())
    parts = {part["id"]: part for part in plan["parts"]}
    actual = {name: {f.GetReference(): f for f in board.GetFootprints()} for name, board in loaded.items()}
    for name, record in data["boards"].items():
        part = parts[name+"-pcb"]
        assert len(record["outlines"]) == 1, name+" needs a multi-body planner representation"
        outline = record["outlines"][0]
        bounds = rectangle(outline["outer"])
        part.update(bounds, rot=0, locked=True)
        local = lambda points: [[round(x-bounds["x"],6), round(y-bounds["y"],6)] for x,y in points]
        part["outline"] = local(outline["outer"])
        part["outlineHoles"] = [local(points) for points in outline["holes"]]
        part["pcbSha256"] = record["sha256"]
    for old, board_name, ref in (("mount-center-H14","center","H14"), ("mount-right-H27","right","H27")):
        if old in parts:
            assert ref not in actual[board_name], old+" is no longer obsolete"
            del parts[old]
    parts.pop("bms-ffc", None)
    for name, refs in (("power",interconnect.BMS_POWER_REFS), ("control",interconnect.BMS_CONTROL_REFS)):
        for board_name, ref in refs.items():
            key = "bms-"+name+"-"+board_name
            parts.setdefault(key, {"id":key,"name":ref+" bms "+name,"kind":"port","zone":"base",
                                   "hidden":False,"pcbSource":[board_name,ref]})
    for part in parts.values():
        if "pcbSource" not in part:
            continue
        name, ref = part["pcbSource"]
        assert ref in actual[name], part["id"]+" points to a missing footprint"
        footprint = actual[name][ref]
        spec = config["boards"][name]
        if part["id"].startswith("mount-"):
            zones = [z for z in loaded[name].Zones() if z.GetIsRuleArea() and z.GetZoneName()=="mount "+ref]
            assert len(zones)==1, part["id"]+" needs its actual support keepout"
            points = [point for i in range(zones[0].Outline().OutlineCount())
                      for point in ring(zones[0].Outline().COutline(i),spec)]
        else:
            points = [point for rings in courtyard_rings(footprint,spec).values() for points in rings for point in points]
        part.update(rectangle(points), rot=0, locked=True)
        part["pcbAnchor"] = transform(xy(footprint.GetPosition()),spec)
        part["pcbRotation"] = (footprint.GetOrientationDegrees()+spec["rotation"]) % 360
        part["pcbSide"] = "back" if footprint.GetLayer()==pcb.B_Cu else "front"
        part["pcbSha256"] = data["boards"][name]["sha256"]
    plan["parts"] = list(parts.values())
    plan["pcbGeometrySource"] = "saved boards and board-placement.json; free case parts remain a packaging sketch"
    return plan

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
            courtyards = courtyard_rings(footprint, spec)
            bounds = []
            for side, rings in courtyards.items():
                for points in rings:
                    bounds.extend(points)
                    dash = ' stroke-dasharray=".7 .5"' if side == "back" else ''
                    svg.append(f'<path d="{path_text(points)}" fill="#ffffff" fill-opacity=".34" stroke="#658875" stroke-width=".15"{dash}/>')
            entries.append({"reference": ref, "position": pos,
                            "rotation": (footprint.GetOrientationDegrees()+spec["rotation"]) % 360,
                            "side": "back" if footprint.GetLayer()==pcb.B_Cu else "front",
                            "courtyard": bounds, "courtyards": courtyards})
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
data["bms_harnesses"] = {}
for name, maps, refs, footprint_id, mpn, housing, contact in (
    ("power", {"center": interconnect.BMS_POWER_PINMAP, "bms": interconnect.BMS_POWER_PINMAP},
     interconnect.BMS_POWER_REFS, interconnect.BMS_POWER_FOOTPRINT, interconnect.BMS_POWER_MPN,
     interconnect.BMS_POWER_HOUSING, interconnect.BMS_POWER_CONTACT),
    ("control", {"center": interconnect.BMS_CONTROL_CENTER_PINMAP, "bms": interconnect.BMS_CONTROL_PINMAP},
     interconnect.BMS_CONTROL_REFS, interconnect.BMS_CONTROL_FOOTPRINT, interconnect.BMS_CONTROL_MPN,
     interconnect.BMS_CONTROL_HOUSING, interconnect.BMS_CONTROL_CONTACT),
):
    spec = config["bms_harnesses"][name]
    ends, rows = {}, []
    for board_name, reference in refs.items():
        matches = [f for f in loaded[board_name].GetFootprints() if f.GetReference() == reference]
        assert len(matches) == 1, f"{board_name} needs the current BMS connector {reference}"
        footprint = matches[0]
        actual_id = str(footprint.GetFPID().GetLibNickname()) + ":" + str(footprint.GetFPID().GetLibItemName())
        assert actual_id == footprint_id, f"{reference} has the wrong connector footprint"
        pads = {pad.GetNumber(): pad for pad in footprint.Pads()}
        for pin, net in maps[board_name].items():
            assert str(pin) in pads, f"{reference} is missing pin {pin}"
            actual = pads[str(pin)].GetNetname().rsplit("/", 1)[-1]
            assert actual == net, f"{reference} pin {pin}: {actual} instead of {net}"
        mounting_pads = [pad for pad in footprint.Pads() if pad.GetNumber() == "MP"]
        assert mounting_pads, f"{reference} is missing its hold-down pads"
        for pad in mounting_pads:
            mp_net = pad.GetNetname().rsplit("/", 1)[-1]
            if name == "power":
                assert not mp_net or mp_net.startswith("unconnected-"), f"{reference} hold-down must remain isolated"
            else:
                assert mp_net == maps[board_name][5], f"{reference} hold-down crosses a ground domain"
        ends[board_name] = {"reference": reference,
                            "position": transform(xy(footprint.GetPosition()), config["boards"][board_name]),
                            "pin_map": maps[board_name]}
    a, z = ends["center"]["position"], ends["bms"]["position"]
    straight = math.dist(a, z)
    assert straight < spec["wire_length_budget_mm"], f"{name} harness cannot fit its wire-length budget"
    for pin in maps["center"]:
        rows.append({"center_pin": pin, "center_net": maps["center"][pin],
                     "bms_pin": pin, "bms_net": maps["bms"][pin]})
    data["bms_harnesses"][name] = {**spec, "ends": ends, "pcb_connector_mpn": mpn,
                                   "housing_mpn": housing, "contact_mpn": contact,
                                   "connections": rows, "origin_distance_mm": round(straight, 6),
                                   "installed_route_verified": False}
    color = "#b98237" if name == "power" else "#627cab"
    svg.append(f'<path d="M {a[0]},{a[1]} L {z[0]},{z[1]}" fill="none" stroke="{color}" stroke-width="1" stroke-dasharray="2 1"/>')
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
floorplan = updated_floorplan()
(ROOT / "mechanical/board-layout.svg").write_text("\n".join(svg)+"\n")
(ROOT / "mechanical/board-datums.json").write_text(json.dumps(data, indent=2)+"\n")
(ROOT / "mechanical/floorplan.json").write_text(json.dumps(floorplan, indent=1)+"\n")
print("exported board outlines, both-side connector datums and planner geometry; BMS maps and M.2 offsets match")
