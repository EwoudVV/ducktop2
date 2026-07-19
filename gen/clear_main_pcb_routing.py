#!/usr/bin/env python3
"""Atomically remove all routed tracks, track arcs, and vias from a KiCad PCB."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import sync_main_pcb_from_netlist as sync


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_top_level_blocks(text: str, marker: str) -> tuple[str, int]:
    blocks = list(sync.iter_blocks(text, marker))
    for start, end, _ in reversed(blocks):
        text = text[:start] + text[end:]
    return text, len(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    pcb = args.pcb if args.pcb.is_absolute() else ROOT / args.pcb
    backup = args.backup if args.backup.is_absolute() else ROOT / args.backup
    report_path = None
    if args.report:
        report_path = args.report if args.report.is_absolute() else ROOT / args.report

    before_hash = sha256(pcb)
    if before_hash != args.expected_sha256:
        raise RuntimeError(
            f"refusing to clear routing: expected {args.expected_sha256}, got {before_hash}"
        )
    if backup.exists():
        raise FileExistsError(f"backup already exists: {backup}")

    original = pcb.read_text(encoding="utf-8")
    before_footprints = len(sync.footprints(original))
    cleared = original
    removed: dict[str, int] = {}
    for name, marker in (
        ("segments", "\n\t(segment"),
        ("track_arcs", "\n\t(arc"),
        ("vias", "\n\t(via"),
    ):
        cleared, removed[name] = remove_top_level_blocks(cleared, marker)

    after_footprints = len(sync.footprints(cleared))
    if after_footprints != before_footprints:
        raise RuntimeError(
            f"footprint count changed during routing clear: {before_footprints} -> {after_footprints}"
        )
    for marker in ("\n\t(segment", "\n\t(arc", "\n\t(via"):
        if list(sync.iter_blocks(cleared, marker)):
            raise RuntimeError(f"routing block remained after clear: {marker.strip()}")

    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pcb, backup)
    temporary = pcb.with_name(pcb.name + ".routing-clear.tmp")
    temporary.write_text(cleared, encoding="utf-8")
    temporary.replace(pcb)

    result = {
        "pcb": str(pcb.relative_to(ROOT)),
        "backup": str(backup.relative_to(ROOT)),
        "before_sha256": before_hash,
        "after_sha256": sha256(pcb),
        "footprints_before": before_footprints,
        "footprints_after": after_footprints,
        "removed": removed,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
