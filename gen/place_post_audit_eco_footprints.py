#!/usr/bin/env python3
"""Place the post-audit ECO additions without touching any other PCB content."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"

sys.path.insert(0, str(ROOT / "gen"))
import sync_main_pcb_from_netlist as sync  # noqa: E402


# These locations are deliberately grouped by function. They are placement
# anchors, not routing or final silkscreen approval.
PLACEMENTS_MM: dict[str, tuple[float, float, float]] = {
    # AUX-input eFuse PGOOD divider, beside U12.
    "R739": (97.5, 129.0, 0.0),
    "R740": (97.5, 127.0, 0.0),

    # Qualified Mu host-active gate, beside the MU_12V regulator controls.
    "U769": (184.0, 96.0, 0.0),
    "C793": (179.5, 96.0, 0.0),
    "R769": (188.5, 96.0, 0.0),

    # Downstream USB-C branch switches and their current-limit resistors.
    "U20": (334.5, 54.0, 0.0),
    "R70": (339.0, 54.0, 0.0),
    "U30": (318.0, 18.0, 0.0),
    "R90": (313.5, 18.0, 0.0),

    # HDMI switch high-frequency bypass and unused-channel terminations.
    "C162": (313.0, 66.5, 0.0),
    "C163": (328.5, 74.5, 0.0),
    "R570": (297.0, 78.0, 0.0),
    "R571": (297.0, 75.5, 0.0),
    "R572": (297.0, 88.0, 0.0),
    "R573": (310.5, 93.0, 0.0),
    "R574": (313.5, 93.5, 0.0),
    "R575": (310.5, 95.0, 0.0),
    "R576": (313.5, 96.5, 0.0),
    "R577": (331.5, 89.0, 0.0),
    "R578": (331.5, 92.0, 0.0),
    "R579": (334.5, 84.5, 0.0),

    # Internal trackpad branch switch.
    "U64": (260.0, 94.5, 0.0),
    "R252": (255.5, 96.0, 0.0),

    # VHF radio fail-safe control and UART conditioning.
    "U242": (204.0, 137.5, 0.0),
    "C246": (199.5, 137.5, 0.0),
    "R242": (205.5, 134.5, 0.0),
    "R243": (195.0, 138.5, 0.0),
    "R244": (200.5, 134.0, 0.0),

    # UHF radio fail-safe control and UART conditioning.
    "U252": (204.0, 164.5, 0.0),
    "C256": (199.5, 164.5, 0.0),
    "R260": (205.5, 167.5, 0.0),
    "R261": (199.5, 167.0, 0.0),
    "R262": (208.0, 170.0, 0.0),
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def fmt(value: float) -> str:
    if abs(value - round(value)) < 0.0005:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def routing_counts(text: str) -> dict[str, int]:
    return {
        kind: len(re.findall(rf"^\s*\({kind}\b", text, re.MULTILINE))
        for kind in ("segment", "arc", "via", "zone")
    }


def without_footprints(text: str) -> str:
    for item in reversed(sync.footprints(text)):
        text = text[: item.start] + text[item.end :]
    return text


def without_at(block: str) -> str:
    span = sync.top_level_child_span(block, "at")
    if span is None:
        fail("footprint has no placement transform")
    return block[: span[0]] + "<AT>" + block[span[1] :]


def set_footprint_at(
    block: str, x: float, y: float, rotation: float
) -> str:
    replacement = f"(at {fmt(x)} {fmt(y)} {fmt(rotation)})"
    updated, count = re.subn(
        r"(?m)^(\s*)\(at\s+[-0-9.]+\s+[-0-9.]+(?:\s+[-0-9.]+)?\)$",
        lambda match: match.group(1) + replacement,
        block,
        count=1,
    )
    if count != 1:
        fail("could not replace exactly one footprint placement transform")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    args = parser.parse_args()
    pcb = args.pcb.resolve()
    before_text = pcb.read_text(encoding="utf-8")
    before_items = sync.footprints(before_text)
    before = {item.ref: item for item in before_items if item.ref}

    if set(PLACEMENTS_MM) != sync.CURRENT_ECO_ADD_ONLY:
        fail("placement map does not exactly match the current add-only ECO")
    missing = set(PLACEMENTS_MM) - set(before)
    if missing:
        fail(f"PCB is missing ECO references: {sorted(missing)}")

    for ref, target in PLACEMENTS_MM.items():
        current = sync.at_tuple(before[ref].text)
        staged = sync.ANCHORS_MM[ref]
        if current not in (staged, target):
            fail(f"{ref} is neither staged nor already placed: {current}")

    after_text = before_text
    for item in reversed(before_items):
        target = PLACEMENTS_MM.get(item.ref)
        if target is None:
            continue
        x, y, rotation = target
        new_block = set_footprint_at(item.text, x, y, rotation)
        after_text = after_text[: item.start] + new_block + after_text[item.end :]

    after_items = sync.footprints(after_text)
    after = {item.ref: item for item in after_items if item.ref}
    if set(after) != set(before):
        fail("reference set changed while placing footprints")
    if without_footprints(after_text) != without_footprints(before_text):
        fail("non-footprint PCB content changed while placing footprints")
    if routing_counts(after_text) != routing_counts(before_text):
        fail("routing primitives changed while placing footprints")

    changed: set[str] = set()
    for ref in before:
        if before[ref].text == after[ref].text:
            continue
        changed.add(ref)
        if ref not in PLACEMENTS_MM:
            fail(f"unexpected footprint changed: {ref}")
        if without_at(before[ref].text) != without_at(after[ref].text):
            fail(f"{ref} changed beyond its placement transform")
        if sync.at_tuple(after[ref].text) != PLACEMENTS_MM[ref]:
            fail(f"{ref} did not land at its audited placement")

    expected_changed = {
        ref
        for ref, target in PLACEMENTS_MM.items()
        if sync.at_tuple(before[ref].text) != target
    }
    if changed != expected_changed:
        fail(f"unexpected changed reference set: {sorted(changed)}")

    temporary = pcb.with_name(pcb.name + ".placement-tmp")
    temporary.write_text(after_text, encoding="utf-8")
    temporary.replace(pcb)
    print(f"Placed {len(changed)} post-audit ECO footprints in {pcb}")
    print(f"Routing preserved: {routing_counts(after_text)}")


if __name__ == "__main__":
    main()
