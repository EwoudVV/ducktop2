#!/usr/bin/env python3
"""Verify a controlled schematic-to-PCB ECO against the protected snapshot."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"
DEFAULT_BASELINE = (
    ROOT
    / "mechanical"
    / "pcb_snapshots"
    / "ducktop2_pre_bq77915_eco_2026-07-19.kicad_pcb"
)

EXPECTED_ATTRIBUTE_UPDATES = {
    "J4": ({"exclude_from_pos_files"}, {"exclude_from_pos_files", "exclude_from_bom"}),
    "J902": ({"exclude_from_pos_files"}, {"exclude_from_pos_files", "exclude_from_bom"}),
}

sys.path.insert(0, str(ROOT / "gen"))
import sync_main_pcb_from_netlist as sync  # noqa: E402


def fail(message: str) -> None:
    raise RuntimeError(message)


def normalize_net(name: str | None) -> str | None:
    if not name or name.startswith("unconnected-"):
        return None
    return name


def board_pad_nets(block: str) -> dict[str, str | None]:
    nets: dict[str, str | None] = {}
    for _, _, pad in sync.pad_blocks(block):
        pin = sync.pad_name(pad)
        match = re.search(r'\(net(?:\s+\d+)?\s+"([^"]*)"\)', pad)
        net = normalize_net(match.group(1) if match else None)
        previous = nets.get(pin)
        if pin in nets and previous != net:
            fail(f"duplicate pad {pin} carries conflicting nets: {previous!r}, {net!r}")
        nets[pin] = net
    return nets


def meaningful_non_footprint_text(text: str) -> str:
    blocks = sync.footprints(text)
    for block in reversed(blocks):
        text = text[: block.start] + text[block.end :]
    return "\n".join(line for line in text.splitlines() if line.strip())


def routing_counts(text: str) -> dict[str, int]:
    return {
        key: len(re.findall(rf"^\s*\({key}\b", text, flags=re.MULTILINE))
        for key in ("segment", "arc", "via")
    }


def footprint_layer(block: str) -> str:
    match = re.search(r'^\s*\(layer\s+"([^"]+)"\)', block, re.MULTILINE)
    return match.group(1) if match else ""


def footprint_locked(block: str) -> bool:
    return bool(
        re.search(r'^\s*\(locked(?:\s+yes)?\)', block, re.MULTILINE)
    )


def normalized_footprint_body(block: str, *, ignore_attributes: bool = False) -> str:
    """Remove only metadata and net assignments that this ECO may update."""
    for key in ("path", "sheetname", "sheetfile"):
        for start, end in reversed(sync.top_level_child_spans(block, key)):
            block = block[:start] + block[end:]
    # Schematic fields are deliberately propagated to PCB footprint metadata.
    # Ignore those top-level properties here, except Reference; reference sets
    # are checked separately and remain part of a footprint's identity.
    for start, end in reversed(sync.top_level_child_spans(block, "property")):
        prop = block[start:end]
        name = sync.extract(r'^\s*\(property\s+"([^"]+)"', prop)
        if name != "Reference":
            block = block[:start] + block[end:]
    if ignore_attributes:
        for start, end in reversed(sync.top_level_child_spans(block, "attr")):
            block = block[:start] + block[end:]
    block = re.sub(r'\n\s*\(net(?:\s+\d+)?\s+"[^"]*"\)', "", block)
    # Property removal can leave a different count of empty lines; those are
    # serialization whitespace, not footprint geometry.
    return "\n".join(line.rstrip() for line in block.splitlines() if line.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()

    pcb_path = args.pcb.resolve()
    baseline_path = args.baseline.resolve()
    pcb_text = pcb_path.read_text(encoding="utf-8")
    baseline_text = baseline_path.read_text(encoding="utf-8")
    board_items = sync.footprints(pcb_text)
    baseline_items = sync.footprints(baseline_text)

    board_refs = [item.ref for item in board_items if item.ref]
    baseline_refs = [item.ref for item in baseline_items if item.ref]
    if len(board_refs) != len(set(board_refs)):
        fail("candidate PCB contains duplicate references")
    if len(baseline_refs) != len(set(baseline_refs)):
        fail("baseline PCB contains duplicate references")

    board = {item.ref: item for item in board_items if item.ref}
    baseline = {item.ref: item for item in baseline_items if item.ref}
    added = set(board) - set(baseline)
    removed = set(baseline) - set(board)
    if added != sync.CURRENT_ECO_ADD_ONLY:
        fail(
            "unexpected added references: "
            f"missing={sorted(sync.CURRENT_ECO_ADD_ONLY - added)} "
            f"extra={sorted(added - sync.CURRENT_ECO_ADD_ONLY)}"
        )
    if removed != sync.ALLOWED_REMOVE_ONLY:
        fail(
            "unexpected removed references: "
            f"missing={sorted(sync.ALLOWED_REMOVE_ONLY - removed)} "
            f"extra={sorted(removed - sync.ALLOWED_REMOVE_ONLY)}"
        )

    changed_footprints = {
        ref
        for ref in set(baseline) & set(board)
        if baseline[ref].footprint != board[ref].footprint
    }
    if changed_footprints != sync.CURRENT_ECO_REPLACE_ONLY:
        fail(f"unexpected footprint replacements: {sorted(changed_footprints)}")

    changed_layers = {
        ref
        for ref in set(baseline) & set(board)
        if footprint_layer(baseline[ref].text) != footprint_layer(board[ref].text)
    }
    if changed_layers:
        fail(f"existing-footprint sides changed: {sorted(changed_layers)}")

    changed_lock_state = {
        ref
        for ref in set(baseline) & set(board)
        if footprint_locked(baseline[ref].text) != footprint_locked(board[ref].text)
    }
    if changed_lock_state:
        fail(f"existing-footprint lock state changed: {sorted(changed_lock_state)}")

    for ref, (before_flags, after_flags) in EXPECTED_ATTRIBUTE_UPDATES.items():
        if ref not in baseline or ref not in board:
            fail(f"attribute-only correction reference missing: {ref}")
        actual_before = sync.footprint_attribute_flags(baseline[ref].text)
        actual_after = sync.footprint_attribute_flags(board[ref].text)
        if (actual_before, actual_after) != (before_flags, after_flags):
            fail(
                f"{ref} unexpected attribute correction: "
                f"{sorted(actual_before)} -> {sorted(actual_after)}"
            )

    changed_bodies = {
        ref
        for ref in set(baseline) & set(board)
        if ref not in sync.CURRENT_ECO_REPLACE_ONLY
        and ref not in sync.REPOSITION_EXISTING
        and normalized_footprint_body(
            baseline[ref].text,
            ignore_attributes=ref in EXPECTED_ATTRIBUTE_UPDATES,
        )
        != normalized_footprint_body(
            board[ref].text,
            ignore_attributes=ref in EXPECTED_ATTRIBUTE_UPDATES,
        )
    }
    if changed_bodies:
        fail(f"unexpected existing-footprint body changes: {sorted(changed_bodies)}")

    moved = {
        ref
        for ref in set(baseline) & set(board)
        if sync.at_tuple(baseline[ref].text) != sync.at_tuple(board[ref].text)
    }
    allowed_moves = sync.REPOSITION_EXISTING | sync.CURRENT_ECO_REPLACE_ONLY
    if not moved <= allowed_moves:
        fail(f"unexpected existing-footprint moves: {sorted(moved - allowed_moves)}")
    for ref in allowed_moves:
        if ref in board and ref in sync.ANCHORS_MM and sync.at_tuple(board[ref].text) != sync.ANCHORS_MM[ref]:
            fail(f"{ref} is not at its audited ECO anchor")
    for ref in moved:
        if sync.at_tuple(board[ref].text) != sync.ANCHORS_MM[ref]:
            fail(f"{ref} did not land at its audited ECO anchor")

    misplaced_additions = {
        ref: sync.at_tuple(board[ref].text)
        for ref in added
        if sync.at_tuple(board[ref].text) != sync.ANCHORS_MM[ref]
    }
    if misplaced_additions:
        fail(f"new footprints missed their audited board anchors: {misplaced_additions}")

    # Never certify an ECO against whatever XML happened to be left by a
    # previous run.  Export the live schematic immediately before parity
    # checks so stale verification artifacts cannot create a false pass/fail.
    sync.export_netlist()
    netlist_root = ET.parse(sync.NETLIST).getroot()
    excluded = {
        comp.get("ref") or ""
        for comp in netlist_root.findall(".//comp")
        if comp.find("property[@name='exclude_from_board']") is not None
    }
    schematic = {
        ref: comp for ref, comp in sync.parse_netlist().items() if ref not in excluded
    }
    if set(board) != set(schematic):
        fail(
            "schematic/PCB reference mismatch: "
            f"missing={sorted(set(schematic) - set(board))} "
            f"extra={sorted(set(board) - set(schematic))}"
        )

    footprint_mismatches: list[str] = []
    pad_net_mismatches: list[str] = []
    attribute_mismatches: list[str] = []
    for ref, item in board.items():
        component = schematic[ref]
        if item.footprint != component.footprint:
            footprint_mismatches.append(
                f"{ref}: {item.footprint} != {component.footprint}"
            )
        actual_nets = board_pad_nets(item.text)
        pins = set(actual_nets) | set(component.pin_nets)
        for pin in pins:
            actual = normalize_net(actual_nets.get(pin))
            wanted = normalize_net(component.pin_nets.get(pin))
            if actual != wanted:
                pad_net_mismatches.append(f"{ref}.{pin}: {actual!r} != {wanted!r}")
        attributes = sync.footprint_attribute_flags(item.text)
        for flag in ("exclude_from_bom", "dnp"):
            actual_flag = flag in attributes
            wanted_flag = flag in component.properties
            if actual_flag != wanted_flag:
                attribute_mismatches.append(
                    f"{ref}.{flag}: {actual_flag!r} != {wanted_flag!r}"
                )
    if footprint_mismatches:
        fail("footprint mismatches remain: " + "; ".join(footprint_mismatches[:10]))
    if pad_net_mismatches:
        fail("pad-net mismatches remain: " + "; ".join(pad_net_mismatches[:10]))
    if attribute_mismatches:
        fail("attribute mismatches remain: " + "; ".join(attribute_mismatches[:10]))

    baseline_routing = routing_counts(baseline_text)
    candidate_routing = routing_counts(pcb_text)
    if candidate_routing != baseline_routing:
        fail(f"routing primitives changed: {baseline_routing} -> {candidate_routing}")
    if meaningful_non_footprint_text(pcb_text) != meaningful_non_footprint_text(
        baseline_text
    ):
        fail("non-footprint board content changed")

    print("PCB ECO integrity: OK")
    print(f"Candidate: {pcb_path}")
    print(f"References: {len(board)} ({len(added)} added, {len(removed)} removed)")
    print(f"Footprint replacements: {', '.join(sorted(changed_footprints))}")
    print(f"Existing moves: {', '.join(sorted(moved))}")
    print("Schematic/PCB drift: 0 refs, 0 footprints, 0 pad nets, 0 BOM/DNP attributes")
    print(f"Routing primitives preserved: {candidate_routing}")


if __name__ == "__main__":
    main()
