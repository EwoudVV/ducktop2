#!/usr/bin/env python3
"""Place the final parked mainboard parts without disturbing existing work.

This is a one-purpose Rev C placement ECO.  It starts from the byte-exact
pre-placement snapshot, changes only top-level footprint transforms, and also
regroups the existing SYS_3V3 buck core so its newly placed mandatory passives
are not left electrically remote from U7.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"
BASELINE_PCB = (
    ROOT
    / "mechanical"
    / "pcb_snapshots"
    / "ducktop2_pre_remaining_placement_2026-07-18.kicad_pcb"
)
BASELINE_SHA256 = "8dc3f2bf55d1e6f530d10d43e62d733bba23c19cff5fe3de189a9128581e9a44"

sys.path.insert(0, str(ROOT / "gen"))
import sync_main_pcb_from_netlist as sync  # noqa: E402


# Each coordinate is a functional-cluster anchor, not a routed-layout release.
PLACEMENTS_MM: dict[str, tuple[float, float, float]] = {
    # Connector-side CC protection for the three left-edge PD inputs.
    "U123": (15.0, 30.0, 0.0),
    "U133": (15.0, 48.0, 0.0),
    "U143": (15.0, 66.0, 0.0),

    # CH224A I2C damping, kept beside the existing sink-controller cluster.
    "R133": (64.0, 40.0, 0.0),
    "R134": (67.0, 40.0, 0.0),
    "R143": (64.0, 48.0, 0.0),
    "R144": (67.0, 48.0, 0.0),
    "R123": (64.0, 56.0, 0.0),
    "R124": (67.0, 56.0, 0.0),

    # PD1 TPS26630 path. Input parts are left of U720; output is on the right.
    "U720": (80.0, 26.0, 0.0),
    "C800": (73.5, 23.0, 0.0),
    "C801": (73.5, 26.0, 0.0),
    "C802": (86.5, 26.0, 0.0),
    "C803": (80.0, 32.0, 0.0),
    "R800": (73.5, 32.0, 0.0),
    "R801": (76.5, 35.0, 0.0),
    "R802": (73.5, 35.0, 0.0),
    "R803": (80.0, 35.0, 0.0),
    "R804": (83.0, 35.0, 0.0),
    "R805": (86.0, 35.0, 0.0),
    "R806": (89.0, 35.0, 0.0),

    # PD2 TPS26630 path.
    "U721": (102.0, 46.0, 0.0),
    "C810": (95.5, 43.0, 0.0),
    "C811": (95.5, 46.0, 0.0),
    "C812": (108.5, 46.0, 0.0),
    "C813": (102.0, 52.0, 0.0),
    "R810": (95.5, 52.0, 0.0),
    "R811": (98.5, 55.0, 0.0),
    "R812": (95.5, 55.0, 0.0),
    "R813": (102.0, 55.0, 0.0),
    "R814": (105.0, 55.0, 0.0),
    "R815": (108.0, 55.0, 0.0),
    "R816": (111.0, 55.0, 0.0),

    # PD3 TPS26630 path, clear of the H14 mainboard support.
    "U722": (140.0, 63.0, 0.0),
    "C820": (133.5, 60.0, 0.0),
    "C821": (133.5, 63.0, 0.0),
    "C822": (146.5, 63.0, 0.0),
    "C823": (140.0, 69.0, 0.0),
    "R820": (133.5, 69.0, 0.0),
    "R821": (136.5, 72.0, 0.0),
    "R822": (133.5, 72.0, 0.0),
    "R823": (140.0, 72.0, 0.0),
    "R824": (143.0, 72.0, 0.0),
    "R825": (146.0, 72.0, 0.0),
    "R826": (149.0, 72.0, 0.0),

    # Compact SYS_3V3 TPS56637 core. U7 VIN is on its right, SW/BOOT below,
    # and EN/FB/PG on the left; the passive placement follows those sides.
    "U7": (135.0, 30.0, 0.0),
    "C46": (140.0, 27.0, 0.0),
    "C790": (140.0, 30.0, 0.0),
    "C791": (140.0, 33.0, 0.0),
    "C47": (137.5, 34.5, 0.0),
    "L5": (135.0, 39.5, 0.0),
    "C48": (132.5, 46.0, 0.0),
    "C792": (137.5, 46.0, 0.0),
    "R770": (125.5, 27.0, 0.0),
    "R771": (125.5, 30.0, 0.0),
    "R43": (129.0, 27.0, 0.0),
    "R44": (129.0, 30.0, 0.0),
    "R772": (125.5, 33.0, 0.0),

    # Resettable source manager, status pulls, and fail-safe control devices.
    "U44": (250.0, 30.0, 0.0),
    "C780": (245.5, 35.0, 0.0),
    "R780": (255.5, 24.0, 0.0),
    "R781": (255.5, 27.0, 0.0),
    "R782": (255.5, 30.0, 0.0),
    "R783": (255.5, 33.0, 0.0),
    "R784": (255.5, 36.0, 0.0),
    "R715": (259.0, 24.0, 0.0),
    "R716": (259.0, 27.0, 0.0),
    "R717": (259.0, 30.0, 0.0),
    "R718": (259.0, 33.0, 0.0),
    "R719": (259.0, 36.0, 0.0),
    "Q700": (264.0, 25.5, 0.0),
    "Q701": (264.0, 34.5, 0.0),
    "R707": (268.0, 25.0, 0.0),
    "R708": (268.0, 28.0, 0.0),
    "R709": (268.0, 31.0, 0.0),

    # EC always-on source OR, kept as a short common-output row.
    "D710": (244.0, 43.0, 0.0),
    "D711": (251.0, 43.0, 0.0),
    "D712": (258.0, 43.0, 0.0),
    "D713": (265.0, 43.0, 0.0),
    "D714": (272.0, 43.0, 0.0),

    # RF-domain level shifters and their local VCCA/VCCB bypassing.
    "U241": (158.0, 24.0, 0.0),
    "C240": (154.0, 22.0, 0.0),
    "C241": (154.0, 25.0, 0.0),
    "U251": (154.0, 34.0, 0.0),
    "C250": (150.0, 32.0, 0.0),
    "C251": (150.0, 35.0, 0.0),
}


OFFBOARD_REFS = {
    "C240", "C241", "C250", "C251", "C780", "C790", "C791", "C792",
    "C800", "C801", "C802", "C803", "C810", "C811", "C812", "C813",
    "C820", "C821", "C822", "C823", "D710", "D711", "D712", "D713",
    "D714", "Q700", "Q701", "R123", "R124", "R133", "R134", "R143",
    "R144", "R707", "R708", "R709", "R715", "R716", "R717", "R718",
    "R719", "R770", "R771", "R772", "R780", "R781", "R782", "R783",
    "R784", "R800", "R801", "R802", "R803", "R804", "R805", "R806",
    "R810", "R811", "R812", "R813", "R814", "R815", "R816", "R820",
    "R821", "R822", "R823", "R824", "R825", "R826", "U123", "U133",
    "U143", "U241", "U251", "U44", "U720", "U721", "U722",
}
SYS_3V3_REWORK = {"U7", "C46", "C47", "C48", "L5", "R43", "R44"}


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def set_footprint_at(block: str, x: float, y: float, rotation: float) -> str:
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


def in_board_center(x: float, y: float) -> bool:
    if not (0.0 <= x <= 358.0 and 0.0 <= y <= 185.0):
        return False
    return not (0.0 <= x < 51.0 and 124.0 < y < 176.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    args = parser.parse_args()

    if set(PLACEMENTS_MM) != OFFBOARD_REFS | SYS_3V3_REWORK:
        fail("placement map does not match the audited move set")
    if len(OFFBOARD_REFS) != 79:
        fail("audited off-board reference set must contain exactly 79 parts")
    if sha256(BASELINE_PCB) != BASELINE_SHA256:
        fail("protected placement baseline hash changed")

    pcb = args.pcb.resolve()
    before_text = pcb.read_text(encoding="utf-8")
    baseline_text = BASELINE_PCB.read_text(encoding="utf-8")
    if before_text != baseline_text:
        fail("candidate does not match the protected pre-placement snapshot")

    before_items = sync.footprints(before_text)
    before = {item.ref: item for item in before_items if item.ref}
    missing = set(PLACEMENTS_MM) - set(before)
    if missing:
        fail(f"PCB is missing placement references: {sorted(missing)}")

    after_text = before_text
    for item in reversed(before_items):
        target = PLACEMENTS_MM.get(item.ref)
        if target is None:
            continue
        new_block = set_footprint_at(item.text, *target)
        after_text = after_text[: item.start] + new_block + after_text[item.end :]

    after_items = sync.footprints(after_text)
    after = {item.ref: item for item in after_items if item.ref}
    if set(after) != set(before):
        fail("reference set changed during placement")
    if without_footprints(after_text) != without_footprints(before_text):
        fail("non-footprint PCB content changed during placement")
    if routing_counts(after_text) != routing_counts(before_text):
        fail("routing primitives changed during placement")

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

    if changed != set(PLACEMENTS_MM):
        fail(f"unexpected changed reference set: {sorted(changed)}")
    outside = [
        ref for ref, item in after.items()
        if not in_board_center(*sync.at_tuple(item.text)[:2])
    ]
    if outside:
        fail(f"active footprints remain outside Edge.Cuts: {sorted(outside)}")

    temporary = pcb.with_name(pcb.name + ".placement-tmp")
    temporary.write_text(after_text, encoding="utf-8")
    temporary.replace(pcb)
    print(f"Placed {len(changed)} footprints in {pcb}")
    print(f"Off-board active footprints: {len(outside)}")
    print(f"Routing preserved: {routing_counts(after_text)}")


if __name__ == "__main__":
    main()
