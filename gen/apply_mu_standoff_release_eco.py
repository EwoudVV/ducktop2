#!/usr/bin/env python3
"""Replace only H1/H2 with the released LattePanda Mu standoff footprint.

The live Ducktop2 PCB contains valuable placement work.  This ECO therefore
requires the reviewed pre-ECO SHA-256, preserves both standoff coordinates,
and proves that no other footprint, routing primitive, zone, or board object
changed before replacing the target file atomically.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import sync_main_pcb_from_netlist as sync


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"
DEFAULT_NETLIST = ROOT / "verification" / "mu_standoff_release_netlist_2026-07-18.xml"
EXPECTED_INPUT_SHA256 = "903de727a674d67a9013e3d43eeeec5bd8f06126023cc5a1d359140805760323"
TARGET_REFS = {"H1", "H2"}
TARGET_FOOTPRINT = "ducktop2:Wurth_9774055243R_M2_H5.5"


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def routing_counts(text: str) -> dict[str, int]:
    return {
        kind: len(re.findall(rf"^\s*\({kind}\b", text, re.MULTILINE))
        for kind in ("segment", "arc", "via", "zone")
    }


def without_footprints(text: str) -> str:
    for item in reversed(sync.footprints(text)):
        text = text[: item.start] + text[item.end :]
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    parser.add_argument("--netlist", type=Path, default=DEFAULT_NETLIST)
    args = parser.parse_args()

    pcb = args.pcb.expanduser().resolve()
    netlist = args.netlist.expanduser().resolve()
    before_text = pcb.read_text(encoding="utf-8")
    actual_sha = sha256(before_text)
    if actual_sha != EXPECTED_INPUT_SHA256:
        fail(
            "refusing unreviewed PCB input: expected "
            f"{EXPECTED_INPUT_SHA256}, got {actual_sha}"
        )
    if not netlist.exists():
        fail(f"netlist does not exist: {netlist}")

    sync.NETLIST = netlist
    components = sync.parse_netlist()
    for ref in TARGET_REFS:
        comp = components.get(ref)
        if comp is None:
            fail(f"netlist is missing {ref}")
        if comp.footprint != TARGET_FOOTPRINT:
            fail(f"{ref} has unexpected netlist footprint {comp.footprint!r}")
        if comp.pin_nets.get("1") != "GND":
            fail(f"{ref} solder land is not GND in the netlist")

    before_items = sync.footprints(before_text)
    before = {item.ref: item for item in before_items if item.ref}
    if len(before) != len(before_items):
        fail("duplicate or blank footprint references are present")
    missing = TARGET_REFS - set(before)
    if missing:
        fail(f"PCB is missing target references: {sorted(missing)}")

    transforms = {ref: sync.at_tuple(before[ref].text) for ref in TARGET_REFS}
    after_text = before_text
    for item in reversed(before_items):
        if item.ref not in TARGET_REFS:
            continue
        x, y, rotation = transforms[item.ref]
        comp = components[item.ref]
        block = sync.normalize_library_footprint(comp, x, y, rotation)
        block = sync.update_metadata(block, comp)
        block, _ = sync.update_pad_nets(block, comp)
        after_text = after_text[: item.start] + block + after_text[item.end :]

    after_items = sync.footprints(after_text)
    after = {item.ref: item for item in after_items if item.ref}
    if set(after) != set(before):
        fail("reference set changed during the Mu standoff ECO")
    if without_footprints(after_text) != without_footprints(before_text):
        fail("non-footprint PCB content changed during the Mu standoff ECO")
    if routing_counts(after_text) != routing_counts(before_text):
        fail("routing primitives changed during the Mu standoff ECO")

    changed = {ref for ref in before if before[ref].text != after[ref].text}
    if changed != TARGET_REFS:
        fail(f"unexpected changed footprint set: {sorted(changed)}")
    for ref in TARGET_REFS:
        if sync.at_tuple(after[ref].text) != transforms[ref]:
            fail(f"{ref} moved during footprint replacement")
        if after[ref].footprint != TARGET_FOOTPRINT:
            fail(f"{ref} did not receive the released footprint")

    temporary = pcb.with_name(pcb.name + ".mu-standoff-tmp")
    temporary.write_text(after_text, encoding="utf-8")
    temporary.replace(pcb)
    print(f"Replaced H1/H2 with {TARGET_FOOTPRINT} in {pcb}")
    print(f"Coordinates preserved: {transforms}")
    print(f"Routing preserved: {routing_counts(after_text)}")
    print(f"Output SHA-256: {sha256(after_text)}")


if __name__ == "__main__":
    main()
