#!/usr/bin/env python3
"""Rebuild the Ducktop2 Rev C main PCB from the current schematic.

This is intentionally a reconstruction, not a broad edit of the stale routed
board.  It keeps only the two local routing islands the user explicitly asked
to preserve, removes every route leaving those islands, and rebuilds all
board-intended footprints from the current schematic/library definitions.

The live PCB is never overwritten unless ``--install`` is supplied.  Even
then, installation is refused unless the live PCB still matches the archived
pre-rebuild SHA-256 snapshot.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import prepare_main_pcb_layout as layout
import sync_main_pcb_from_netlist as sync


ROOT = Path(__file__).resolve().parents[1]
LIVE_PCB = ROOT / "ducktop2.kicad_pcb"
SNAPSHOT = ROOT / "mechanical" / "pcb_snapshots" / "ducktop2_pre_battery_band_relayout_2026-07-16.kicad_pcb"
FLOORPLAN = ROOT / "mechanical" / "floorplan_revC_battery_band.json"
OUT_DIR = ROOT / "mechanical" / "pcb_rebuild"
DEFAULT_OUTPUT = OUT_DIR / "ducktop2_revC_candidate.kicad_pcb"
REPORT = OUT_DIR / "ducktop2_revC_rebuild_report.json"
DRC_REPORT = ROOT / "verification" / "ducktop2_revC_candidate_drc.json"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
KICAD_PYTHON = Path(
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
)

EXPECTED_SOURCE_SHA256 = "0f92e5e86755a14ebebf5bd39368bd4f9d2d6b7309de82cd0cf9bf6b62ac6ea9"

BOARD_W = 358.0
BOARD_H = 185.0
# The purchased SKV505014-AL fin stack is nominally 50 x 50 mm.  Give it
# 1.0 mm clearance on the three PCB-facing sides instead of making the board
# edge a press fit around a heatsink with its own manufacturing tolerance.
FIN_NOTCH = (0.0, 124.0, 51.0, 176.0)

# Source boxes were measured against the archived routed board.  The clusters
# are translated to clear J310 and the right-edge I/O while keeping all local
# geometry exactly relative to itself.
ISLANDS = {
    "maker_rp2350": {
        "source_box": (318.75, 45.5, 336.4, 78.0),
        "offset": (-40.0, 0.0),
    },
    "stm32_ec": {
        "source_box": (326.25, 94.25, 349.25, 121.25),
        "offset": (-35.0, 0.0),
    },
}

# Major parts and externally constrained connectors.  Coordinates are board
# footprint origins, not generic rectangle centers.
ANCHORS: dict[str, tuple[float, float, float]] = {
    # Compute and storage.
    # The footprint origin is offset from the module courtyard center.  This
    # origin places the actual 65.4 x 77.4 mm Mu envelope at x=100..165.4,
    # y=105.05..182.45, matching the measured Rev C floorplan.
    "A1": (105.2, 143.75, 90.0),
    "J10": (240.0, 116.0, 0.0),
    "J40": (276.0, 149.0, 0.0),

    # Main keyboard FFC.  Its old routing is intentionally not preserved: the
    # Rev A cable reverses pin order and the current schematic reflects that.
    "J310": (319.0, 59.0, 270.0),

    # Left-side charging and universal AUX/solar input.
    "J21": (4.525, 30.0, 270.0),
    "J22": (4.525, 48.0, 270.0),
    "J23": (4.525, 66.0, 270.0),
    "J190": (8.0, 96.0, 270.0),

    # Right-side user I/O.
    "J11": (353.475, 30.0, 90.0),
    "J12": (353.475, 48.0, 90.0),
    "J30": (352.285, 72.0, 0.0),
    # The custom RJ45 footprint's local panel plane is y=20.78 mm.  At 90
    # degrees, x=337.22 puts that plane on the 358 mm board edge.
    "J500": (337.22, 104.0, 90.0),

    # Rear-facing external radio connectors; 270 degrees points the connector
    # body toward negative Y, outside the rear edge.
    "J241": (245.0, 2.0, 270.0),
    "J251": (278.0, 2.0, 270.0),
    "J240": (245.0, 15.0, 0.0),
    "J250": (278.0, 15.0, 0.0),
    "J42": (305.0, 15.0, 0.0),

    # Internal physical interfaces.
    "J58": (179.0, 130.0, 0.0),
    "J52": (61.0, 120.0, 180.0),
    "J2": (178.0, 170.0, 0.0),
    "J420": (18.0, 180.0, 0.0),
    "J421": (340.0, 180.0, 0.0),
    "MK430": (40.0, 110.0, 0.0),

    # Two radio modules.
    "J70": (190.0, 151.0, 0.0),
    "J71": (232.0, 151.0, 0.0),

    # Maker-user interface around the translated RP2350 island.
    "J901": (304.0, 57.5, 0.0),
    "J902": (314.0, 86.0, 0.0),
    "SW900": (303.0, 34.0, 0.0),
    "SW901": (315.0, 34.0, 0.0),

    # EC service interfaces around the translated STM32 island.
    "J4": (321.0, 109.0, 0.0),
    "J16": (320.0, 134.0, 0.0),
    "SW1": (321.0, 124.0, 0.0),
}

SHEET_TARGETS = {
    "01_power_battery.kicad_sch": (78.0, 147.0),
    "02_ec_mcu.kicad_sch": (295.0, 111.0),
    "03_mu_carrier.kicad_sch": (146.0, 127.0),
    "04_usb_c_io.kicad_sch": (319.0, 39.0),
    "05_power_inputs.kicad_sch": (43.0, 51.0),
    "06_tcp0_external_hdmi.kicad_sch": (315.0, 79.0),
    "07_radio_oled_gps.kicad_sch": (214.0, 41.0),
    "08_internal_services.kicad_sch": (270.0, 113.0),
    "09_ham_radio.kicad_sch": (229.0, 151.0),
    "12_keyboard_interface.kicad_sch": (317.0, 70.0),
    "13_radio_audio_codec.kicad_sch": (245.0, 165.0),
    "14_maker_mcu.kicad_sch": (288.0, 61.0),
    "15_system_audio.kicad_sch": (92.0, 158.0),
    "16_gigabit_ethernet.kicad_sch": (319.0, 104.0),
}

# Component-free mechanical regions.  Anchored parts may intentionally occupy
# these areas; the automatic packer may not.
PACK_KEEPOUTS = [
    FIN_NOTCH,                        # fin-stack notch
    (0.0, 20.0, 11.0, 121.0),       # left side I/O corridor
    (347.0, 20.0, 358.0, 121.0),    # right side I/O corridor
    (8.0, 0.0, 58.0, 20.0),         # left hinge
    (310.0, 0.0, 350.0, 20.0),      # right hinge
    (60.0, 0.0, 88.0, 30.0),        # eDP hinge-cable chase
    (220.0, 0.0, 306.0, 20.0),      # rear antenna recess
]


@dataclass
class Copper:
    kind: str
    block: str
    net: str
    points: tuple[tuple[float, float], ...]
    seeded: bool = False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def natural_ref(ref: str) -> tuple[str, int, str]:
    match = re.match(r"([A-Z]+)([0-9]+)(.*)", ref)
    return (match.group(1), int(match.group(2)), match.group(3)) if match else (ref, -1, "")


def in_box(point: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def expand(box: tuple[float, float, float, float], margin: float) -> tuple[float, float, float, float]:
    return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


def point_in_rect(point: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    return rect[0] <= point[0] <= rect[2] and rect[1] <= point[1] <= rect[3]


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> int:
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(value) < 1e-9:
        return 0
    return 1 if value > 0 else 2


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return min(a[0], c[0]) - 1e-9 <= b[0] <= max(a[0], c[0]) + 1e-9 and min(a[1], c[1]) - 1e-9 <= b[1] <= max(a[1], c[1]) + 1e-9


def line_intersects(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]
) -> bool:
    o1, o2 = orientation(a, b, c), orientation(a, b, d)
    o3, o4 = orientation(c, d, a), orientation(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return (
        (o1 == 0 and on_segment(a, c, b))
        or (o2 == 0 and on_segment(a, d, b))
        or (o3 == 0 and on_segment(c, a, d))
        or (o4 == 0 and on_segment(c, b, d))
    )


def segment_hits_rect(
    a: tuple[float, float], b: tuple[float, float], rect: tuple[float, float, float, float]
) -> bool:
    if point_in_rect(a, rect) or point_in_rect(b, rect):
        return True
    x1, y1, x2, y2 = rect
    edges = [
        ((x1, y1), (x2, y1)),
        ((x2, y1), (x2, y2)),
        ((x2, y2), (x1, y2)),
        ((x1, y2), (x1, y1)),
    ]
    return any(line_intersects(a, b, c, d) for c, d in edges)


def normalize_net(name: str | None) -> str | None:
    if not name or name.startswith("unconnected-"):
        return None
    return name


def child_blocks(block: str, kind: str) -> list[str]:
    """Return footprint child blocks independent of tabs-vs-spaces style."""
    children: list[str] = []
    index = 0
    pattern = re.compile(r"\n[ \t]+\(" + re.escape(kind) + r"\b")
    while True:
        match = pattern.search(block, index)
        if match is None:
            return children
        start = match.start() + 1
        end = sync.balanced_end(block, start)
        children.append(block[start:end])
        index = end


def footprint_bbox(
    block: str, x: float, y: float, rotation: float
) -> tuple[float, float, float, float]:
    """Approximate a footprint's physical/courtyard envelope for staging."""
    points: list[tuple[float, float]] = []
    for pad in child_blocks(block, "pad"):
        at = re.search(
            r"\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)", pad
        )
        size = re.search(r"\(size\s+([-0-9.]+)\s+([-0-9.]+)\)", pad)
        if not at or not size:
            continue
        px, py = float(at.group(1)), float(at.group(2))
        angle = math.radians(float(at.group(3) or 0.0))
        width, height = float(size.group(1)), float(size.group(2))
        for dx, dy in (
            (-width / 2, -height / 2),
            (width / 2, -height / 2),
            (width / 2, height / 2),
            (-width / 2, height / 2),
        ):
            points.append(
                (
                    px + dx * math.cos(angle) - dy * math.sin(angle),
                    py + dx * math.sin(angle) + dy * math.cos(angle),
                )
            )

    accepted_layers = {
        '"F.Fab"', '"B.Fab"', '"F.CrtYd"', '"B.CrtYd"',
        '"F.SilkS"', '"B.SilkS"', '"Dwgs.User"',
    }
    for kind in ("fp_rect", "fp_line", "fp_circle", "fp_arc", "fp_poly"):
        for graphic in child_blocks(block, kind):
            layer = re.search(r"\(layer\s+([^\)]+)\)", graphic)
            if layer and layer.group(1).strip() not in accepted_layers:
                continue
            for xy in re.finditer(
                r"\((?:start|end|center|mid|xy)\s+([-0-9.]+)\s+([-0-9.]+)", graphic
            ):
                points.append((float(xy.group(1)), float(xy.group(2))))

    if not points:
        points = [(-1.0, -1.0), (1.0, 1.0)]
    world = [layout.transform_local(point, x, y, rotation) for point in points]
    xs, ys = [point[0] for point in world], [point[1] for point in world]
    return (min(xs), min(ys), max(xs), max(ys))


def top_level_copper(text: str, box: tuple[float, float, float, float]) -> list[Copper]:
    copper: list[Copper] = []
    for _, _, block in sync.iter_blocks(text, "\n\t(segment"):
        start = re.search(r"\(start\s+([-0-9.]+)\s+([-0-9.]+)\)", block)
        end = re.search(r"\(end\s+([-0-9.]+)\s+([-0-9.]+)\)", block)
        net = sync.extract(r'\(net\s+"([^"]+)"\)', block)
        if not start or not end or not net:
            continue
        points = (
            (float(start.group(1)), float(start.group(2))),
            (float(end.group(1)), float(end.group(2))),
        )
        if all(in_box(point, box) for point in points):
            copper.append(Copper("segment", block, net, points))

    for _, _, block in sync.iter_blocks(text, "\n\t(via"):
        at = re.search(r"\(at\s+([-0-9.]+)\s+([-0-9.]+)\)", block)
        net = sync.extract(r'\(net\s+"([^"]+)"\)', block)
        if not at or not net:
            continue
        point = (float(at.group(1)), float(at.group(2)))
        if in_box(point, box):
            copper.append(Copper("via", block, net, (point,)))
    return copper


def board_pad_nets(block: str) -> dict[str, str | None]:
    nets: dict[str, str | None] = {}
    for _, _, pad in sync.pad_blocks(block):
        pin = sync.pad_name(pad)
        match = re.search(r'\(net(?:\s+\d+)?\s+"([^"]*)"\)', pad)
        nets[pin] = normalize_net(match.group(1) if match else None)
    return nets


def pad_bbox(pad: str, fp_at: tuple[float, float, float]) -> tuple[float, float, float, float] | None:
    at = re.search(r"\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)", pad)
    size = re.search(r"\(size\s+([-0-9.]+)\s+([-0-9.]+)\)", pad)
    if not at or not size:
        return None
    px, py = float(at.group(1)), float(at.group(2))
    w, h = float(size.group(1)), float(size.group(2))
    x, y, rotation = fp_at
    corners = [
        layout.transform_local((px - w / 2, py - h / 2), x, y, rotation),
        layout.transform_local((px + w / 2, py - h / 2), x, y, rotation),
        layout.transform_local((px + w / 2, py + h / 2), x, y, rotation),
        layout.transform_local((px - w / 2, py + h / 2), x, y, rotation),
    ]
    xs, ys = [p[0] for p in corners], [p[1] for p in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def stale_copper_rects(
    old_footprints: dict[str, sync.BoardFootprint],
    components: dict[str, sync.Component],
    box: tuple[float, float, float, float],
) -> list[tuple[float, float, float, float]]:
    rects: list[tuple[float, float, float, float]] = []
    for ref, old in old_footprints.items():
        x, y, rotation = sync.at_tuple(old.text)
        if not in_box((x, y), box):
            continue
        component = components.get(ref)
        if component is None or "exclude_from_board" in component.properties:
            rects.append(expand(footprint_bbox(old.text, x, y, rotation), 0.35))
            continue
        if old.footprint != component.footprint:
            rects.append(expand(footprint_bbox(old.text, x, y, rotation), 0.35))
            continue

        old_nets = board_pad_nets(old.text)
        for _, _, pad in sync.pad_blocks(old.text):
            pin = sync.pad_name(pad)
            if old_nets.get(pin) == normalize_net(component.pin_nets.get(pin)):
                continue
            bbox = pad_bbox(pad, (x, y, rotation))
            if bbox is not None:
                rects.append(expand(bbox, 0.18))
    return rects


def filter_connected_stale(copper: list[Copper], stale_rects: list[tuple[float, float, float, float]], current_nets: set[str]) -> tuple[list[Copper], int]:
    for item in copper:
        if item.net not in current_nets:
            item.seeded = True
        elif item.kind == "segment":
            item.seeded = any(segment_hits_rect(item.points[0], item.points[1], rect) for rect in stale_rects)
        else:
            item.seeded = any(point_in_rect(item.points[0], rect) for rect in stale_rects)

    node_map: dict[tuple[str, tuple[float, float]], list[int]] = defaultdict(list)
    for index, item in enumerate(copper):
        for point in item.points:
            key = (item.net, (round(point[0], 6), round(point[1], 6)))
            node_map[key].append(index)

    removed: set[int] = {index for index, item in enumerate(copper) if item.seeded}
    queue = deque(removed)
    while queue:
        index = queue.popleft()
        item = copper[index]
        for point in item.points:
            key = (item.net, (round(point[0], 6), round(point[1], 6)))
            for linked in node_map[key]:
                if linked not in removed:
                    removed.add(linked)
                    queue.append(linked)
    return [item for index, item in enumerate(copper) if index not in removed], len(removed)


def island_owned_nets(
    components: dict[str, sync.Component], refs: list[str]
) -> set[str]:
    """Return only current nets that terminate on preserved island parts."""
    return {
        net
        for ref in refs
        for raw_net in components[ref].pin_nets.values()
        if (net := normalize_net(raw_net)) is not None
    }


def island_pad_anchor_map(
    old_footprints: dict[str, sync.BoardFootprint],
    components: dict[str, sync.Component],
    refs: list[str],
) -> dict[tuple[str, tuple[float, float]], set[str]]:
    """Collect old pad centers whose net still matches the current schematic.

    Copper is preserved only when its connected graph reaches one of these
    points.  This removes unrelated traces that merely crossed an island box.
    """
    anchors: dict[tuple[str, tuple[float, float]], set[str]] = defaultdict(set)
    for ref in refs:
        old = old_footprints[ref]
        component = components[ref]
        x, y, rotation = sync.at_tuple(old.text)
        old_nets = board_pad_nets(old.text)
        for _, _, pad in sync.pad_blocks(old.text):
            pin = sync.pad_name(pad)
            net = old_nets.get(pin)
            if net is None or net != normalize_net(component.pin_nets.get(pin)):
                continue
            at = re.search(r"\(at\s+([-0-9.]+)\s+([-0-9.]+)", pad)
            if at is None:
                continue
            point = layout.transform_local(
                (float(at.group(1)), float(at.group(2))), x, y, rotation
            )
            key = (net, (round(point[0], 6), round(point[1], 6)))
            anchors[key].add(ref)
    return dict(anchors)


def filter_pad_anchored_copper(
    copper: list[Copper],
    anchors: set[tuple[str, tuple[float, float]]],
) -> tuple[list[Copper], int]:
    """Drop copper graph components that do not touch a preserved pad."""
    node_map: dict[tuple[str, tuple[float, float]], list[int]] = defaultdict(list)
    for index, item in enumerate(copper):
        for point in item.points:
            key = (item.net, (round(point[0], 6), round(point[1], 6)))
            node_map[key].append(index)

    visited: set[int] = set()
    kept: set[int] = set()
    for seed in range(len(copper)):
        if seed in visited:
            continue
        component_indices: set[int] = set()
        component_nodes: set[tuple[str, tuple[float, float]]] = set()
        queue = deque([seed])
        visited.add(seed)
        while queue:
            index = queue.popleft()
            component_indices.add(index)
            item = copper[index]
            for point in item.points:
                key = (item.net, (round(point[0], 6), round(point[1], 6)))
                component_nodes.add(key)
                for linked in node_map[key]:
                    if linked not in visited:
                        visited.add(linked)
                        queue.append(linked)
        if component_nodes & anchors:
            kept.update(component_indices)

    return [item for index, item in enumerate(copper) if index in kept], len(copper) - len(kept)


def trim_external_fanout(
    copper: list[Copper],
    anchor_map: dict[tuple[str, tuple[float, float]], set[str]],
    max_stub_mm: float = 3.0,
) -> tuple[list[Copper], int]:
    """Keep local routing, but stop single-part signals at their first via.

    Graphs touching pads on two or more preserved references are local
    inter-component routing and remain intact.  A graph touching only one
    preserved reference is an external signal fanout: keep at most a short
    pad escape and include the first via, but do not retain the former board-
    level route beyond it.
    """
    node_map: dict[tuple[str, tuple[float, float]], list[int]] = defaultdict(list)
    via_nodes: set[tuple[str, tuple[float, float]]] = set()
    for index, item in enumerate(copper):
        for point in item.points:
            key = (item.net, (round(point[0], 6), round(point[1], 6)))
            node_map[key].append(index)
            if item.kind == "via":
                via_nodes.add(key)

    visited: set[int] = set()
    kept: set[int] = set()
    for seed in range(len(copper)):
        if seed in visited:
            continue
        component_indices: set[int] = set()
        component_nodes: set[tuple[str, tuple[float, float]]] = set()
        queue = deque([seed])
        visited.add(seed)
        while queue:
            index = queue.popleft()
            component_indices.add(index)
            for point in copper[index].points:
                key = (copper[index].net, (round(point[0], 6), round(point[1], 6)))
                component_nodes.add(key)
                for linked in node_map[key]:
                    if linked not in visited:
                        visited.add(linked)
                        queue.append(linked)

        sources = component_nodes & set(anchor_map)
        anchored_refs = {ref for node in sources for ref in anchor_map[node]}
        if len(anchored_refs) >= 2:
            kept.update(component_indices)
            continue

        distances: dict[tuple[str, tuple[float, float]], float] = {
            node: 0.0 for node in sources
        }
        frontier = [(0.0, node) for node in sources]
        heapq.heapify(frontier)
        while frontier:
            distance, node = heapq.heappop(frontier)
            if distance > distances.get(node, math.inf) + 1e-9:
                continue
            if node in via_nodes and node not in sources:
                kept.update(
                    index for index in node_map[node] if copper[index].kind == "via"
                )
                continue
            for index in node_map[node]:
                item = copper[index]
                if item.kind == "via":
                    kept.add(index)
                    continue
                a = (item.net, (round(item.points[0][0], 6), round(item.points[0][1], 6)))
                b = (item.net, (round(item.points[1][0], 6), round(item.points[1][1], 6)))
                other = b if node == a else a
                length = math.dist(item.points[0], item.points[1])
                new_distance = distance + length
                if new_distance > max_stub_mm + 1e-9:
                    continue
                kept.add(index)
                if new_distance + 1e-9 < distances.get(other, math.inf):
                    distances[other] = new_distance
                    heapq.heappush(frontier, (new_distance, other))

    return [item for index, item in enumerate(copper) if index in kept], len(copper) - len(kept)


def translate_copper(block: str, dx: float, dy: float) -> str:
    def replace_xy(match: re.Match[str]) -> str:
        return f"({match.group(1)} {sync.fmt(float(match.group(2)) + dx)} {sync.fmt(float(match.group(3)) + dy)})"

    return re.sub(r"\((start|end|at)\s+([-0-9.]+)\s+([-0-9.]+)\)", replace_xy, block)


def set_attr_flags(block: str, component: sync.Component) -> str:
    match = re.search(r"\n\s*\(attr\s+([^\)]*)\)", block)
    flags = match.group(1).split() if match else []
    flags = [flag for flag in flags if flag not in {"dnp", "exclude_from_bom"}]
    if "exclude_from_bom" in component.properties:
        flags.append("exclude_from_bom")
    if "dnp" in component.properties:
        flags.append("dnp")
    line = "(attr" + (" " + " ".join(flags) if flags else "") + ")"
    if match:
        return block[: match.start()] + "\n\t\t" + line + block[match.end() :]
    insert = block.find("\n\t\t(fp_")
    if insert < 0:
        insert = block.rfind("\n\t)")
    return block[:insert] + "\n\t\t" + line + block[insert:]


def reuuid_footprint(block: str, ref: str) -> str:
    index = 0

    def replace_uuid(_: re.Match[str]) -> str:
        nonlocal index
        value = sync.stable_uuid(f"revc:{ref}:{index}")
        index += 1
        return f'(uuid "{value}")'

    return re.sub(r'\(uuid\s+"[^"]+"\)', replace_uuid, block)


def footprint_block(component: sync.Component, x: float, y: float, rotation: float) -> str:
    block = sync.normalize_library_footprint(component, x, y, rotation)
    block = sync.update_metadata(block, component)
    block, _ = sync.update_pad_nets(block, component)
    block = set_attr_flags(block, component)
    return reuuid_footprint(block, component.ref)


class SpatialIndex:
    def __init__(self, cell: float = 8.0) -> None:
        self.cell = cell
        self.boxes: list[tuple[float, float, float, float]] = []
        self.cells: dict[tuple[int, int], set[int]] = defaultdict(set)

    def keys(self, box: tuple[float, float, float, float]):
        x1 = math.floor(box[0] / self.cell)
        x2 = math.floor(box[2] / self.cell)
        y1 = math.floor(box[1] / self.cell)
        y2 = math.floor(box[3] / self.cell)
        for gx in range(x1, x2 + 1):
            for gy in range(y1, y2 + 1):
                yield (gx, gy)

    def add(self, box: tuple[float, float, float, float]) -> None:
        index = len(self.boxes)
        self.boxes.append(box)
        for key in self.keys(box):
            self.cells[key].add(index)

    def collides(self, box: tuple[float, float, float, float]) -> bool:
        candidates: set[int] = set()
        for key in self.keys(box):
            candidates.update(self.cells.get(key, set()))
        return any(intersects(box, self.boxes[index]) for index in candidates)


def board_fits(box: tuple[float, float, float, float], margin: float = 0.45) -> bool:
    if box[0] < margin or box[1] < margin or box[2] > BOARD_W - margin or box[3] > BOARD_H - margin:
        return False
    return not intersects(box, FIN_NOTCH)


def candidate_points(target: tuple[float, float]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    step = 1.5
    y = 22.0
    while y <= BOARD_H - 3.0:
        x = 12.0
        while x <= BOARD_W - 12.0:
            points.append((x, y))
            x += step
        y += step
    tx, ty = target
    points.sort(key=lambda p: ((p[0] - tx) ** 2 + (p[1] - ty) ** 2, p[1], p[0]))
    return points


def placement_margin(ref: str, area: float) -> float:
    if ref.startswith(("J", "SW", "F")) or area > 100.0:
        return 0.8
    if area > 20.0 or ref.startswith(("U", "Q", "L")):
        return 0.45
    return 0.24


def fixed_island_positions(
    old_footprints: dict[str, sync.BoardFootprint], components: dict[str, sync.Component]
) -> tuple[dict[str, tuple[float, float, float]], dict[str, list[str]]]:
    fixed: dict[str, tuple[float, float, float]] = {}
    refs_by_island: dict[str, list[str]] = {}
    for name, config in ISLANDS.items():
        source_box = config["source_box"]
        dx, dy = config["offset"]
        refs: list[str] = []
        for ref, old in old_footprints.items():
            x, y, rotation = sync.at_tuple(old.text)
            component = components.get(ref)
            if not in_box((x, y), source_box) or component is None or "exclude_from_board" in component.properties:
                continue
            # Changed footprints cannot retain old pad-local routing safely;
            # stage them near the island instead of pretending they still fit.
            if old.footprint != component.footprint:
                continue
            fixed[ref] = (x + dx, y + dy, rotation)
            refs.append(ref)
        refs_by_island[name] = sorted(refs, key=natural_ref)
    return fixed, refs_by_island


def place_components(
    components: dict[str, sync.Component],
    old_footprints: dict[str, sync.BoardFootprint],
) -> tuple[
    dict[str, tuple[float, float, float]],
    dict[str, list[str]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    fixed, refs_by_island = fixed_island_positions(old_footprints, components)
    for ref, placement in ANCHORS.items():
        if ref in components and ref not in fixed:
            fixed[ref] = placement

    prototype_blocks = {
        ref: footprint_block(component, 0.0, 0.0, 0.0)
        for ref, component in components.items()
    }
    placements = dict(fixed)
    spatial = SpatialIndex()
    fixed_overlaps: list[dict[str, object]] = []
    fixed_pairwise: list[dict[str, object]] = []

    fixed_boxes = {
        ref: footprint_bbox(prototype_blocks[ref], *placement)
        for ref, placement in fixed.items()
    }
    fixed_refs = sorted(fixed_boxes, key=natural_ref)
    for index, ref_a in enumerate(fixed_refs):
        for ref_b in fixed_refs[index + 1 :]:
            if any(ref_a in refs and ref_b in refs for refs in refs_by_island.values()):
                continue
            box_a, box_b = fixed_boxes[ref_a], fixed_boxes[ref_b]
            if not intersects(box_a, box_b):
                continue
            overlap = (
                min(box_a[2], box_b[2]) - max(box_a[0], box_b[0]),
                min(box_a[3], box_b[3]) - max(box_a[1], box_b[1]),
            )
            fixed_pairwise.append(
                {
                    "refs": [ref_a, ref_b],
                    "bbox_a": list(box_a),
                    "bbox_b": list(box_b),
                    "overlap_mm": [overlap[0], overlap[1]],
                }
            )
    if fixed_pairwise:
        raise RuntimeError(
            "fixed footprint anchors overlap: "
            + ", ".join("/".join(item["refs"]) for item in fixed_pairwise)
        )

    # Reserve physical keepouts for automatically packed components.
    for keepout in PACK_KEEPOUTS:
        spatial.add(keepout)

    # Treat each preserved island as one obstacle, allowing its intentionally
    # dense internal placement while protecting it from auto-packed parts.
    for name, config in ISLANDS.items():
        box = config["source_box"]
        dx, dy = config["offset"]
        spatial.add((box[0] + dx - 0.8, box[1] + dy - 0.8, box[2] + dx + 0.8, box[3] + dy + 0.8))

    for ref, (x, y, rotation) in fixed.items():
        if any(ref in refs for refs in refs_by_island.values()):
            continue
        box = footprint_bbox(prototype_blocks[ref], x, y, rotation)
        padded = expand(box, placement_margin(ref, max(0.0, (box[2] - box[0]) * (box[3] - box[1]))))
        if spatial.collides(padded):
            fixed_overlaps.append({"ref": ref, "bbox": list(box)})
        spatial.add(padded)

    candidates_by_sheet = {
        sheet: candidate_points(target) for sheet, target in SHEET_TARGETS.items()
    }

    unplaced = [ref for ref in components if ref not in placements]
    local_area: dict[str, float] = {}
    for ref in unplaced:
        box = footprint_bbox(prototype_blocks[ref], 0.0, 0.0, 0.0)
        local_area[ref] = max(0.0, (box[2] - box[0]) * (box[3] - box[1]))
    unplaced.sort(key=lambda ref: (-local_area[ref], components[ref].sheetfile, natural_ref(ref)))

    for ref in unplaced:
        component = components[ref]
        target = SHEET_TARGETS.get(component.sheetfile, (179.0, 92.0))
        candidates = candidates_by_sheet.setdefault(component.sheetfile, candidate_points(target))
        margin = placement_margin(ref, local_area[ref])
        placed = False
        for x, y in candidates:
            box = expand(footprint_bbox(prototype_blocks[ref], x, y, 0.0), margin)
            if not board_fits(box):
                continue
            if any(intersects(box, keepout) for keepout in PACK_KEEPOUTS):
                continue
            if spatial.collides(box):
                continue
            placements[ref] = (x, y, 0.0)
            spatial.add(box)
            placed = True
            break
        if not placed:
            raise RuntimeError(f"could not place {ref} ({component.sheetfile}, area={local_area[ref]:.1f} mm^2)")
    return placements, refs_by_island, fixed_overlaps, fixed_pairwise


def edge_graphics() -> list[str]:
    _, notch_top, notch_right, notch_bottom = FIN_NOTCH
    points = [
        (0.0, 0.0),
        (BOARD_W, 0.0),
        (BOARD_W, BOARD_H),
        (0.0, BOARD_H),
        (0.0, notch_bottom),
        (notch_right, notch_bottom),
        (notch_right, notch_top),
        (0.0, notch_top),
        (0.0, 0.0),
    ]
    blocks: list[str] = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        blocks.append(
            "\n".join(
                [
                    "\t(gr_line",
                    f"\t\t(start {sync.fmt(start[0])} {sync.fmt(start[1])})",
                    f"\t\t(end {sync.fmt(end[0])} {sync.fmt(end[1])})",
                    "\t\t(stroke (width 0.1) (type solid))",
                    '\t\t(layer "Edge.Cuts")',
                    f'\t\t(uuid "{sync.stable_uuid(f"revc-edge:{index}")}")',
                    "\t)",
                ]
            )
        )
    return blocks


def floorplan_graphics() -> list[str]:
    data = json.loads(FLOORPLAN.read_text(encoding="utf-8"))
    blocks: list[str] = []
    for part in data["parts"]:
        if part.get("zone") != "base":
            continue
        x1, y1 = float(part["x"]), float(part["y"])
        x2, y2 = x1 + float(part["w"]), y1 + float(part["h"])
        key = part["id"]
        blocks.append(
            "\n".join(
                [
                    "\t(gr_rect",
                    f"\t\t(start {sync.fmt(x1)} {sync.fmt(y1)})",
                    f"\t\t(end {sync.fmt(x2)} {sync.fmt(y2)})",
                    "\t\t(stroke (width 0.12) (type dash))",
                    "\t\t(fill no)",
                    '\t\t(layer "Dwgs.User")',
                    f'\t\t(uuid "{sync.stable_uuid(f"revc-guide:{key}")}")',
                    "\t)",
                ]
            )
        )
        blocks.append(
            "\n".join(
                [
                    f'\t(gr_text "MECH: {sync.q(part["name"])}"',
                    f"\t\t(at {sync.fmt(x1 + 1.2)} {sync.fmt(y1 + 2.0)} 0)",
                    '\t\t(layer "Dwgs.User")',
                    f'\t\t(uuid "{sync.stable_uuid(f"revc-label:{key}")}")',
                    "\t\t(effects (font (size 1.15 1.15) (thickness 0.16)) (justify left))",
                    "\t)",
                ]
            )
        )
    return blocks


def verify_generated_board(
    path: Path,
    components: dict[str, sync.Component],
    expected_copper: int,
) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    footprints = sync.footprints(text)
    by_ref = {fp.ref: fp for fp in footprints}
    missing = sorted(set(components) - set(by_ref), key=natural_ref)
    extra = sorted(set(by_ref) - set(components), key=natural_ref)
    footprint_mismatches = sorted(
        ref for ref in set(components) & set(by_ref)
        if components[ref].footprint != by_ref[ref].footprint
    )
    pad_mismatches: list[tuple[str, str, str | None, str | None]] = []
    for ref in set(components) & set(by_ref):
        actual = board_pad_nets(by_ref[ref].text)
        for pin, expected_name in components[ref].pin_nets.items():
            expected = normalize_net(expected_name)
            observed = normalize_net(actual.get(pin))
            if expected != observed:
                pad_mismatches.append((ref, pin, observed, expected))

    segments = len(sync.iter_blocks(text, "\n\t(segment"))
    vias = len(sync.iter_blocks(text, "\n\t(via"))
    edge_lines = [
        block for _, _, block in sync.iter_blocks(text, "\n\t(gr_line")
        if '(layer "Edge.Cuts")' in block
    ]
    result = {
        "footprints": len(footprints),
        "missing": missing,
        "extra": extra,
        "footprint_mismatches": footprint_mismatches,
        "pad_mismatches": pad_mismatches,
        "segments": segments,
        "vias": vias,
        "edge_lines": len(edge_lines),
        "expected_copper_blocks": expected_copper,
    }
    if missing or extra or footprint_mismatches or pad_mismatches:
        raise RuntimeError(f"generated PCB parity failure: {json.dumps(result, default=str)[:3000]}")
    if segments + vias != expected_copper:
        raise RuntimeError(
            f"salvaged copper count mismatch: wrote {segments + vias}, expected {expected_copper}"
        )
    if len(edge_lines) != 8:
        raise RuntimeError(f"expected 8 Rev C outer Edge.Cuts segments, found {len(edge_lines)}")
    return result


def normalize_with_pcbnew(path: Path) -> dict[str, float | int]:
    try:
        import pcbnew  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            f"pcbnew is unavailable; run with {KICAD_PYTHON}"
        ) from exc
    board = pcbnew.LoadBoard(str(path))
    bbox = board.GetBoardEdgesBoundingBox()
    stats = {
        "bbox_x_mm": bbox.GetX() / 1_000_000,
        "bbox_y_mm": bbox.GetY() / 1_000_000,
        "bbox_w_mm": bbox.GetWidth() / 1_000_000,
        "bbox_h_mm": bbox.GetHeight() / 1_000_000,
        "pcbnew_footprints": len(board.GetFootprints()),
        "pcbnew_tracks": len(board.GetTracks()),
        "pcbnew_zones": board.GetAreaCount(),
    }
    # KiCad's board-edge bounding box includes half the Edge.Cuts stroke on
    # both sides, so a 0.1 mm line makes a nominal 358 x 185 mm contour report
    # as 358.1 x 185.1 mm.
    if abs(stats["bbox_w_mm"] - BOARD_W) > 0.12 or abs(stats["bbox_h_mm"] - BOARD_H) > 0.12:
        raise RuntimeError(f"unexpected board-edge bounding box: {stats}")
    pcbnew.SaveBoard(str(path), board)
    return stats


def copy_project_settings_for_candidate(path: Path) -> Path:
    """Make candidate DRC use the canonical Ducktop2 rules and presets."""
    source = ROOT / "ducktop2.kicad_pro"
    target = path.with_suffix(".kicad_pro")
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    fp_table = (ROOT / "fp-lib-table").read_text(encoding="utf-8")
    fp_table = fp_table.replace(
        '${KIPRJMOD}/ducktop2.pretty',
        '${KIPRJMOD}/../../ducktop2.pretty',
    ).replace(
        '${KIPRJMOD}/Module_LattePanda.pretty',
        '${KIPRJMOD}/../../Module_LattePanda.pretty',
    )
    (path.parent / "fp-lib-table").write_text(fp_table, encoding="utf-8")
    return target


def run_drc(path: Path) -> dict[str, object]:
    DRC_REPORT.parent.mkdir(exist_ok=True)
    process = subprocess.run(
        [
            str(KICAD_CLI),
            "pcb",
            "drc",
            "--format",
            "json",
            "--output",
            str(DRC_REPORT),
            str(path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    data = json.loads(DRC_REPORT.read_text(encoding="utf-8")) if DRC_REPORT.exists() else {}
    counts: dict[str, int] = defaultdict(int)
    for violation in data.get("violations", []):
        counts[violation.get("type", "unknown")] += 1
    return {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "violation_counts": dict(sorted(counts.items())),
        "unconnected_items": len(data.get("unconnected_items", [])),
        "report": str(DRC_REPORT.relative_to(ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--install", action="store_true", help="replace ducktop2.kicad_pcb after all checks pass")
    parser.add_argument("--skip-drc", action="store_true")
    args = parser.parse_args()

    if not SNAPSHOT.exists():
        raise FileNotFoundError(SNAPSHOT)
    snapshot_hash = sha256(SNAPSHOT)
    if snapshot_hash != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(f"snapshot hash changed: {snapshot_hash}")
    if args.install and sha256(LIVE_PCB) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("refusing installation: live PCB no longer matches the archived source snapshot")

    sync.export_netlist()
    all_components = sync.parse_netlist()
    components = {
        ref: component
        for ref, component in all_components.items()
        if component.footprint and "exclude_from_board" not in component.properties
    }
    if len(components) != 736:
        raise RuntimeError(f"expected 736 board components, found {len(components)}")

    old_text = SNAPSHOT.read_text(encoding="utf-8")
    old_footprints_list = sync.footprints(old_text)
    old_footprints = {fp.ref: fp for fp in old_footprints_list}
    _, source_island_refs = fixed_island_positions(old_footprints, components)

    salvaged: list[str] = []
    salvage_report: dict[str, object] = {}
    for name, config in ISLANDS.items():
        source_box = config["source_box"]
        dx, dy = config["offset"]
        refs = source_island_refs[name]
        all_copper = top_level_copper(old_text, source_box)
        owned_nets = island_owned_nets(components, refs)
        copper = [item for item in all_copper if item.net in owned_nets]
        foreign_removed = len(all_copper) - len(copper)
        stale_rects = stale_copper_rects(old_footprints, components, source_box)
        current, stale_removed = filter_connected_stale(copper, stale_rects, owned_nets)
        anchor_map = island_pad_anchor_map(old_footprints, components, refs)
        anchored, unanchored_removed = filter_pad_anchored_copper(
            current, set(anchor_map)
        )
        kept, external_route_removed = trim_external_fanout(anchored, anchor_map)
        salvaged.extend(translate_copper(item.block, dx, dy) for item in kept)
        salvage_report[name] = {
            "source_box": list(source_box),
            "offset": [dx, dy],
            "candidate_copper_blocks": len(all_copper),
            "owned_nets": len(owned_nets),
            "foreign_net_blocks_removed": foreign_removed,
            "stale_connected_blocks_removed": stale_removed,
            "unanchored_blocks_removed": unanchored_removed,
            "external_route_blocks_removed": external_route_removed,
            "copper_blocks_kept": len(kept),
            "stale_seed_rects": len(stale_rects),
            "matching_pad_anchors": len(anchor_map),
        }

    placements, island_refs, fixed_overlaps, fixed_pairwise = place_components(components, old_footprints)
    if island_refs != source_island_refs:
        raise RuntimeError("preserved island references changed during placement")
    blocks = [
        footprint_block(components[ref], *placements[ref])
        for ref in sorted(components, key=natural_ref)
    ]

    first_footprint = old_footprints_list[0]
    prefix = old_text[: first_footprint.start].rstrip()
    graphics = edge_graphics() + floorplan_graphics()
    candidate_text = (
        prefix
        + "\n"
        + "\n".join(blocks)
        + "\n"
        + "\n".join(graphics)
        + ("\n" + "\n".join(salvaged) if salvaged else "")
        + "\n\t(embedded_fonts no)\n)\n"
    )

    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(candidate_text, encoding="utf-8")

    pre_normalize = verify_generated_board(output, components, len(salvaged))
    pcbnew_stats = normalize_with_pcbnew(output)
    post_normalize = verify_generated_board(output, components, len(salvaged))
    candidate_project = copy_project_settings_for_candidate(output)
    drc = {} if args.skip_drc else run_drc(output)
    install_blocker_types = {
        "clearance",
        "invalid_outline",
        "items_not_allowed",
        "lib_footprint_issues",
        "lib_footprint_mismatch",
        "shorting_items",
    }
    drc_counts = drc.get("violation_counts", {})
    install_blockers = {
        violation: drc_counts[violation]
        for violation in sorted(install_blocker_types)
        if drc_counts.get(violation)
    }

    report = {
        "source_snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "source_sha256": snapshot_hash,
        "output": str(output.relative_to(ROOT)),
        "output_sha256": sha256(output),
        "board_outline_mm": {"width": BOARD_W, "height": BOARD_H},
        "fin_stack_notch_mm": list(FIN_NOTCH),
        "component_count": len(components),
        "island_footprints": island_refs,
        "salvage": salvage_report,
        "fixed_anchor_overlaps_with_reserved_or_fixed_areas": fixed_overlaps,
        "fixed_pairwise_overlaps": fixed_pairwise,
        "pre_normalize": pre_normalize,
        "pcbnew": pcbnew_stats,
        "candidate_project_settings": str(candidate_project.relative_to(ROOT)),
        "post_normalize": post_normalize,
        "drc": drc,
        "install_blockers": install_blockers,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.install:
        if install_blockers:
            raise RuntimeError(f"refusing installation due to DRC blockers: {install_blockers}")
        shutil.copy2(output, LIVE_PCB)
        if sha256(LIVE_PCB) != sha256(output):
            raise RuntimeError("installed PCB hash does not match candidate")
        print(f"Installed {output.relative_to(ROOT)} -> {LIVE_PCB.name}")

    print(f"Built {output.relative_to(ROOT)}")
    print(f"Footprints: {len(components)}")
    print(f"Salvaged copper blocks: {len(salvaged)}")
    print(f"Board outline: {BOARD_W:g} x {BOARD_H:g} mm with fin-stack notch")
    print(f"Report: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
