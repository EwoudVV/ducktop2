#!/usr/bin/env python3
"""Apply the current generated schematic ECO to the placed mainboard.

The script keeps every unchanged footprint at its existing position, removes
only references retired from the generated schematic, replaces changed
packages, updates pad nets and metadata, and collision-packs newly introduced
parts near their functional block.  It writes a candidate by default; the live
board changes only with ``--install`` after the candidate checks pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import rebuild_main_pcb_revC as layout
import sync_main_pcb_from_netlist as sync


ROOT = Path(__file__).resolve().parents[1]
LIVE_PCB = ROOT / "ducktop2.kicad_pcb"
OUT_DIR = ROOT / "mechanical" / "pcb_rebuild"
DEFAULT_OUTPUT = OUT_DIR / "ducktop2_current_eco_candidate.kicad_pcb"
REPORT = OUT_DIR / "ducktop2_current_eco_report.json"

EXPECTED_MISSING_SHEETS = {
    "04_usb_c_io.kicad_sch",
    "05_power_inputs.kicad_sch",
    "09_radio_daughterboard_interface.kicad_sch",
}
EXPECTED_EXTRA_SHEETS = {
    "01_power_battery.kicad_sch",
    "02_ec_mcu.kicad_sch",
    "04_usb_c_io.kicad_sch",
    "05_power_inputs.kicad_sch",
    "07_radio_oled_gps.kicad_sch",
    "09_ham_radio.kicad_sch",
    "13_radio_audio_codec.kicad_sch",
}

# One-time placement corrections belong here only until they have been applied
# to the live board. Keeping the set empty makes later ECO runs idempotent.
REPOSITION_EXISTING: set[str] = set()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sheetfile(block: str) -> str:
    return sync.extract(r'\(sheetfile\s+"([^"]*)"\)', block)


def ref_number(ref: str) -> int | None:
    match = re.fullmatch(r"[A-Z]+(\d+).*", ref)
    return int(match.group(1)) if match else None


def target_for(ref: str, component: sync.Component, old=None) -> tuple[float, float]:
    """Return the mechanical neighborhood for a newly placed component."""
    if old is not None:
        x, y, _rotation = sync.at_tuple(old.text)
        return (x, y)

    number = ref_number(ref)
    sheet = component.sheetfile
    if sheet == "04_usb_c_io.kicad_sch":
        if ref.startswith("D") and number is not None:
            if 1800 <= number <= 1807:
                return (42.0, 48.0)   # J22, left source-only port
            if 1808 <= number <= 1815:
                return (42.0, 68.0)   # J23, left source-only port
            if 1816 <= number <= 1823:
                return (316.0, 50.0)  # J12, right source-only port
        if number is not None and 1780 <= number <= 1799:
            return (42.0, 48.0)
        if number is not None and 1740 <= number <= 1759:
            return (42.0, 68.0)
        if number is not None and 1760 <= number <= 1779:
            return (316.0, 50.0)
        return (178.0, 48.0)          # USB7206C and shared port rails

    if sheet == "05_power_inputs.kicad_sch":
        port1 = (
            ref in {"J21", "U41", "U720", "Q2001", "D2080"}
            or (ref.startswith("U") and number is not None and 2000 <= number <= 2006)
            or (ref.startswith("R") and number is not None and 2000 <= number <= 2018)
            or (ref.startswith("R") and number is not None and 2080 <= number <= 2086)
            or (ref.startswith("C") and number is not None and 2000 <= number <= 2030)
            or (ref.startswith("C") and number is not None and 2080 <= number <= 2082)
            or (ref.startswith("D") and number is not None and 2100 <= number <= 2107)
        )
        port2 = (
            ref in {"J11", "U42", "U721", "Q2002", "D2090"}
            or (ref.startswith("U") and number is not None and 2010 <= number <= 2016)
            or (ref.startswith("R") and number is not None and 2040 <= number <= 2058)
            or (ref.startswith("R") and number is not None and 2090 <= number <= 2096)
            or (ref.startswith("C") and number is not None and 2040 <= number <= 2070)
            or (ref.startswith("C") and number is not None and 2090 <= number <= 2092)
            or (ref.startswith("D") and number is not None and 2120 <= number <= 2127)
        )
        if port1:
            return (47.0, 31.0)       # J21, left dual-role/PD port
        if port2:
            return (311.0, 31.0)      # J11, right dual-role/PD port
        return (91.0, 72.0)           # LTC4418 dual-input selector

    if sheet == "09_radio_daughterboard_interface.kicad_sch":
        return (239.0, 49.0)

    return layout.SHEET_TARGETS.get(sheet, (179.0, 92.0))


def build_candidate(source: Path, output: Path, *, normalize: bool = False) -> dict[str, object]:
    sync.export_netlist()
    components = {
        ref: component
        for ref, component in sync.parse_netlist().items()
        if component.footprint and "exclude_from_board" not in component.properties
    }
    source_text = source.read_text(encoding="utf-8")
    footprints = sync.footprints(source_text)
    existing = {footprint.ref: footprint for footprint in footprints}
    if len(existing) != len(footprints):
        raise RuntimeError("duplicate footprint references are present on the main PCB")

    missing = set(components) - set(existing)
    extra = set(existing) - set(components)
    replacements = {
        ref for ref in set(components) & set(existing)
        if components[ref].footprint != existing[ref].footprint
    }
    missing_sheets = {components[ref].sheetfile for ref in missing}
    extra_sheets = {sheetfile(existing[ref].text) for ref in extra}
    if not missing_sheets <= EXPECTED_MISSING_SHEETS:
        raise RuntimeError(f"unexpected missing-component sheets: {sorted(missing_sheets)}")
    if not extra_sheets <= EXPECTED_EXTRA_SHEETS:
        raise RuntimeError(f"unexpected retired-component sheets: {sorted(extra_sheets)}")

    prototype_blocks = {
        ref: layout.footprint_block(component, 0.0, 0.0, 0.0)
        for ref, component in components.items()
    }
    spatial = layout.SpatialIndex()
    for keepout in layout.PACK_KEEPOUTS:
        spatial.add(keepout)

    # Every unchanged footprint is a fixed obstacle and remains byte-positioned.
    reposition = REPOSITION_EXISTING & set(existing) & set(components)
    fixed_refs = (set(existing) & set(components)) - replacements - reposition
    for ref in sorted(fixed_refs, key=layout.natural_ref):
        footprint = existing[ref]
        x, y, rotation = sync.at_tuple(footprint.text)
        box = layout.footprint_bbox(footprint.text, x, y, rotation)
        # Mechanical holes need extra assembly clearance beyond their copper
        # pad envelope; otherwise tiny passives can land inside the washer or
        # standoff keepout even when their copper technically clears the hole.
        fixed_margin = 1.25 if ref.startswith("H") else 0.16
        spatial.add(layout.expand(box, fixed_margin))

    to_place = sorted(
        missing | replacements | reposition,
        key=lambda ref: (
            -max(
                0.0,
                (layout.footprint_bbox(prototype_blocks[ref], 0.0, 0.0, 0.0)[2]
                 - layout.footprint_bbox(prototype_blocks[ref], 0.0, 0.0, 0.0)[0])
                * (layout.footprint_bbox(prototype_blocks[ref], 0.0, 0.0, 0.0)[3]
                   - layout.footprint_bbox(prototype_blocks[ref], 0.0, 0.0, 0.0)[1]),
            ),
            components[ref].sheetfile,
            layout.natural_ref(ref),
        ),
    )
    placements: dict[str, tuple[float, float, float]] = {}
    candidates_by_target: dict[tuple[float, float], list[tuple[float, float]]] = {}
    for ref in to_place:
        component = components[ref]
        target = target_for(ref, component, None if ref in reposition else existing.get(ref))
        candidates = candidates_by_target.setdefault(target, layout.candidate_points(target))
        local_box = layout.footprint_bbox(prototype_blocks[ref], 0.0, 0.0, 0.0)
        area = max(0.0, (local_box[2] - local_box[0]) * (local_box[3] - local_box[1]))
        margin = layout.placement_margin(ref, area)
        desired_rotation = sync.at_tuple(existing[ref].text)[2] if ref in reposition else 0.0
        for x, y in candidates:
            box = layout.expand(
                layout.footprint_bbox(prototype_blocks[ref], x, y, desired_rotation),
                margin,
            )
            if not layout.board_fits(box):
                continue
            if any(layout.intersects(box, keepout) for keepout in layout.PACK_KEEPOUTS):
                continue
            if spatial.collides(box):
                continue
            placements[ref] = (x, y, desired_rotation)
            spatial.add(box)
            break
        else:
            raise RuntimeError(
                f"could not place {ref} ({component.sheetfile}, area={area:.1f} mm^2)"
            )

    new_text = source_text
    metadata_updates = 0
    pad_updates = 0
    removed: list[str] = []
    replaced: list[str] = []
    repositioned: list[str] = []
    for footprint in reversed(footprints):
        ref = footprint.ref
        if ref in extra:
            new_text = new_text[:footprint.start] + new_text[footprint.end:]
            removed.append(ref)
            continue
        component = components.get(ref)
        if component is None:
            continue
        if ref in replacements:
            block = layout.footprint_block(component, *placements[ref])
            replaced.append(ref)
        else:
            block = sync.update_metadata(footprint.text, component)
            block, count = sync.update_pad_nets(block, component)
            pad_updates += count
            metadata_updates += 1
            if ref in reposition:
                x, y, rotation = placements[ref]
                block = sync.set_or_insert_top_line(
                    block,
                    "at",
                    f"(at {sync.fmt(x)} {sync.fmt(y)} {sync.fmt(rotation % 360)})",
                )
                repositioned.append(ref)
        new_text = new_text[:footprint.start] + block + new_text[footprint.end:]

    added: list[str] = []
    insertion = new_text.rfind("\n)")
    if insertion < 0:
        raise RuntimeError("could not locate final board close parenthesis")
    blocks: list[str] = []
    for ref in sorted(missing, key=layout.natural_ref):
        blocks.append(layout.footprint_block(components[ref], *placements[ref]))
        added.append(ref)
    new_text = new_text[:insertion] + "\n" + "\n".join(blocks) + new_text[insertion:]

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(new_text, encoding="utf-8")
    temporary.replace(output)
    before_normalize = sha256(output)
    if normalize:
        pcbnew = layout.normalize_with_pcbnew(output)
    else:
        pcbnew = {"status": "skipped", "reason": "deterministic ECO does not require a PCB rewrite"}
    after_normalize = sha256(output)

    result = {
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "output": str(output.relative_to(ROOT)),
        "output_sha256": after_normalize,
        "component_count": len(components),
        "existing_footprint_count": len(existing),
        "added_count": len(added),
        "removed_count": len(removed),
        "replaced_count": len(replaced),
        "repositioned_count": len(repositioned),
        "metadata_updates": metadata_updates,
        "pad_net_updates": pad_updates,
        "missing_by_sheet": dict(Counter(components[ref].sheetfile for ref in missing)),
        "retired_by_sheet": dict(Counter(sheetfile(existing[ref].text) for ref in extra)),
        "added": added,
        "removed": sorted(removed, key=layout.natural_ref),
        "replaced": sorted(replaced, key=layout.natural_ref),
        "repositioned": sorted(repositioned, key=layout.natural_ref),
        "candidate_pre_normalize_sha256": before_normalize,
        "pcbnew": pcbnew,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=LIVE_PCB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="rewrite the candidate through pcbnew after the deterministic ECO",
    )
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output
    source_hash = sha256(source)
    result = build_candidate(source, output, normalize=args.normalize)
    if sha256(source) != source_hash:
        raise RuntimeError("source PCB changed while the ECO candidate was being built")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.install:
        shutil.copy2(output, LIVE_PCB)
        if sha256(LIVE_PCB) != result["output_sha256"]:
            raise RuntimeError("installed PCB does not match the checked ECO candidate")
        print(f"Installed {output.relative_to(ROOT)} -> {LIVE_PCB.name}")

    print(f"Built {output.relative_to(ROOT)}")
    print(
        f"Footprints: {result['component_count']} "
        f"(added {result['added_count']}, removed {result['removed_count']}, "
        f"replaced {result['replaced_count']})"
    )
    print(f"Pad-net updates on preserved footprints: {result['pad_net_updates']}")
    print(f"Report: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
