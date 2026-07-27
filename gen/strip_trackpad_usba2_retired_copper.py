#!/usr/bin/env python3
"""Remove only copper that terminates at the retired trackpad USB-C parts.

This is deliberately a candidate-only ECO helper.  It starts at pads belonging
to the obsolete USB-C receptacle/attach controller network and removes routed
stubs only until a retained pad or the first via.  It never edits zones,
footprints, Edge.Cuts, graphics, or unrelated routing.
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import sync_main_pcb_from_netlist as sync


RETIRED_REFS = frozenset({"J58", "U63", "R254", "C281", "C282", "C284"})
COPPER_MARKERS = ("\n\t(segment", "\n\t(arc", "\n\t(via")


@dataclass(frozen=True)
class Copper:
    start: int
    end: int
    block: str
    kind: str
    net: str
    points: tuple[tuple[float, float], ...]


def point_key(net: str, point: tuple[float, float]) -> tuple[str, float, float]:
    return (net, round(point[0], 6), round(point[1], 6))


def world_point(
    local: tuple[float, float], transform: tuple[float, float, float]
) -> tuple[float, float]:
    x, y, angle = transform
    radians = math.radians(angle)
    lx, ly = local
    return (
        x + lx * math.cos(radians) - ly * math.sin(radians),
        y + lx * math.sin(radians) + ly * math.cos(radians),
    )


def pad_anchors(text: str, refs: set[str]) -> set[tuple[str, float, float]]:
    anchors: set[tuple[str, float, float]] = set()
    for footprint in sync.footprints(text):
        if footprint.ref not in refs:
            continue
        transform = sync.at_tuple(footprint.text)
        for _start, _end, pad in sync.pad_blocks(footprint.text):
            net = sync.extract(r'\(net(?:\s+\d+)?\s+"([^"]+)"\)', pad)
            at = re.search(r'\(at\s+([-0-9.]+)\s+([-0-9.]+)', pad)
            if not net or at is None:
                continue
            point = world_point((float(at.group(1)), float(at.group(2))), transform)
            anchors.add(point_key(net, point))
    return anchors


def copper_items(text: str) -> list[Copper]:
    items: list[Copper] = []
    patterns = {
        "segment": ("\n\t(segment", ("start", "end")),
        "arc": ("\n\t(arc", ("start", "end")),
        "via": ("\n\t(via", ("at",)),
    }
    for kind, (marker, point_names) in patterns.items():
        for start, end, block in sync.iter_blocks(text, marker):
            net = sync.extract(r'\(net\s+"([^"]+)"\)', block)
            points: list[tuple[float, float]] = []
            for name in point_names:
                match = re.search(rf'\({name}\s+([-0-9.]+)\s+([-0-9.]+)', block)
                if match is None:
                    raise RuntimeError(f"cannot parse {kind} {name}: {block[:120]}")
                points.append((float(match.group(1)), float(match.group(2))))
            if not net:
                raise RuntimeError(f"cannot parse {kind} net: {block[:120]}")
            items.append(Copper(start, end, block, kind, net, tuple(points)))
    return items


def without_copper(text: str) -> str:
    result = text
    spans: list[tuple[int, int]] = []
    for marker in COPPER_MARKERS:
        spans.extend((start, end) for start, end, _block in sync.iter_blocks(result, marker))
    for start, end in sorted(spans, reverse=True):
        result = result[:start] + result[end:]
    return result


def remove_retired_stubs(before: str, candidate: str) -> tuple[str, Counter[str], Counter[str]]:
    before_refs = [item.ref for item in sync.footprints(before)]
    missing = RETIRED_REFS - set(before_refs)
    if missing:
        raise RuntimeError(f"source board is missing retired references: {sorted(missing)}")
    target_anchors = pad_anchors(before, set(RETIRED_REFS))
    retained_anchors = pad_anchors(before, set(before_refs) - set(RETIRED_REFS))
    items = copper_items(candidate)
    node_items: dict[tuple[str, float, float], list[int]] = defaultdict(list)
    via_items: dict[tuple[str, float, float], list[int]] = defaultdict(list)
    for index, item in enumerate(items):
        for point in item.points:
            key = point_key(item.net, point)
            node_items[key].append(index)
            if item.kind == "via":
                via_items[key].append(index)

    removed: set[int] = set()
    queued: set[tuple[str, float, float]] = set(target_anchors)
    queue = deque(sorted(target_anchors))
    while queue:
        node = queue.popleft()
        for index in node_items.get(node, []):
            item = items[index]
            if index in removed:
                continue
            removed.add(index)
            for point in item.points:
                next_node = point_key(item.net, point)
                if next_node in retained_anchors:
                    continue
                if next_node in via_items:
                    # Delete the via joined to the retired stub, but do not
                    # follow its other exits into retained routing.
                    removed.update(via_items[next_node])
                    continue
                if next_node not in queued:
                    queued.add(next_node)
                    queue.append(next_node)

    by_kind = Counter(items[index].kind for index in removed)
    by_net = Counter(items[index].net for index in removed)
    output = candidate
    for index in sorted(removed, key=lambda item: items[item].start, reverse=True):
        item = items[index]
        output = output[: item.start] + output[item.end :]
    if without_copper(output) != without_copper(candidate):
        raise RuntimeError("copper cleanup changed non-routing PCB content")
    return output, by_kind, by_net


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path, help="pre-ECO PCB used for retired-pad anchors")
    parser.add_argument("--candidate", required=True, type=Path, help="PCB after the footprint-only ECO")
    parser.add_argument("--output", required=True, type=Path, help="new PCB candidate; it must not already exist")
    args = parser.parse_args()
    before = args.before.resolve()
    candidate = args.candidate.resolve()
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {output}")
    updated, by_kind, by_net = remove_retired_stubs(
        before.read_text(encoding="utf-8"), candidate.read_text(encoding="utf-8")
    )
    output.write_text(updated, encoding="utf-8")
    print(f"Wrote candidate: {output}")
    print("Removed routed primitives: " + ", ".join(f"{kind}={by_kind[kind]}" for kind in sorted(by_kind)))
    print("Removed nets: " + ", ".join(f"{net}={by_net[net]}" for net in sorted(by_net)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
