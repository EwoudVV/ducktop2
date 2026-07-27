#!/usr/bin/env python3
"""Create a candidate PCB with three verified stale duplicate footprints removed.

This is deliberately not a general deduplicator.  It accepts only the
2026-07-27 Ducktop2 board hash and removes only the three independently
reviewed duplicate blocks below. U170 and U2004 retain the routed legacy
locations; a scoped schematic-to-PCB metadata sync must follow on the
candidate so those retained blocks regain their current source paths.

The U2004 duplicate-pad routes were traced before this helper was released.
It removes the complete duplicate-only MUX_EN loop and the MUX_FLIP spur only
up to its tee, while preserving the live U2000/R2006 MUX_FLIP trunk. No other
copper or non-footprint board text is changed by this helper.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sync_main_pcb_from_netlist import at_tuple, footprints, top_level_child_spans


EXPECTED_INPUT_SHA256 = "687f6f6abcf3b4dec172facf89abfe0fbff241e1d6e3cadf8baa62c83078181a"


@dataclass(frozen=True)
class DuplicatePolicy:
    ref: str
    keep_at: tuple[float, float, float]
    remove_at: tuple[float, float, float]
    direct_copper: tuple[tuple[str, str], ...] = ()


POLICIES = (
    # Preserve the fully routed E-key isolator.  The source-linked copy is
    # physically un-routed and will be removed, then the keeper is scoped-sync'd.
    DuplicatePolicy("U170", (259.5, 162.5, 180.0), (185.405, 79.89, 0.0)),
    # The MUX_EN route is a loop from the duplicate to the retained U2004 and
    # has no external pad endpoint. The MUX_FLIP subset below ends at its tee
    # at (21.1, 34.6), preserving the U2000/R2006 trunk beyond it.
    DuplicatePolicy(
        "U2004",
        (20.1375, 35.45, 0.0),
        (25.9375, 31.3, 0.0),
        (
            # Isolated GPIO/host-attached/SYS_3V3 duplicate pad stubs.
            ("segment", "75f070f8-1b15-43f4-9ccc-dc34ed0ab7eb"),
            ("segment", "13bf6e5c-2730-4e6e-8bd9-0f58a1548558"),
            ("segment", "ba1dee56-41bf-4d65-9a1e-4a8788469f10"),
            ("segment", "1a1b6cc7-a67b-4022-a6a5-f3febcf66a81"),
            ("via", "8bf47d71-a72d-4d47-9d3c-66d742d755ea"),
            # Complete duplicate-to-keeper PD1_MUX_EN loop.
            ("via", "b8bce366-d3a8-4094-a6d1-333f74e16417"),
            ("segment", "e35150dd-22f6-4954-aa7f-1ea68b02343c"),
            ("segment", "5b203b93-9145-4900-988f-b002e86f7e21"),
            ("segment", "71232a26-9441-4e62-82ac-8eef7c7266b4"),
            ("segment", "f0b8c40d-0099-4707-a633-b56d4c4b3231"),
            ("segment", "254a9559-7893-46e0-8be7-340e00b5912e"),
            ("segment", "725c3b29-835b-4f42-bf2e-d2435812dcb2"),
            ("segment", "1be13125-9b88-46ac-8ae0-147a6287d736"),
            ("segment", "13eceeba-dd60-46ca-abd5-16c9d9b1ca29"),
            ("segment", "5325e5ae-1ce9-41bc-a4eb-6743c5db9d22"),
            ("segment", "472db3b8-dc15-4a49-b23a-4010d0fa35d4"),
            ("via", "bc913654-bfb7-4991-b9b1-4e29f9595eb8"),
            ("segment", "365b7ed7-c453-45c7-b593-caf6f2f3808e"),
            ("segment", "69a1f741-2e79-4d45-a9c8-89790df32eed"),
            ("via", "1822b291-2e8e-4a37-8800-221040aa8564"),
            # PD1_MUX_FLIP spur, ending before the live route tee.
            ("via", "12dbbf4c-1f35-4745-83c9-61833076d1c8"),
            ("segment", "f1663c43-6b2a-4bbf-b3f1-c778553b1af9"),
            ("segment", "af221f25-7f81-44e6-8e02-cca3671b57f2"),
            ("segment", "b6aae7e1-9f95-405b-b272-952b1234cb48"),
            ("segment", "8fac11c2-9a86-4d2c-8948-486ab4eee2de"),
            ("segment", "6b5f0716-56e4-4cca-bc6e-82b4fbd88877"),
            ("segment", "a0e23d6e-178d-4d85-b5e4-d4429dc1f87b"),
            ("segment", "5dbc0a2a-b646-4bd8-820c-3a81d5209279"),
            ("segment", "69310a69-e706-4278-b2ff-289fc5a72463"),
            ("segment", "8be1db8a-036e-4659-bb6d-c5a097668d84"),
        ),
    ),
    # The source-linked PD2 control-buffer copy has no attached copper and
    # remains at its current placement; remove only the pathless old copy.
    DuplicatePolicy("U2014", (201.195, 67.05, 0.0), (69.0, 32.5, 0.0)),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close_enough(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
    return all(abs(left - right) < 0.0001 for left, right in zip(a, b))


def block_uuid(block: str) -> str:
    match = re.search(r'\(uuid\s+"([^"]+)"', block)
    if not match:
        raise RuntimeError("target board block has no UUID")
    return match.group(1)


def uuid_span(text: str, item_kind: str, wanted_uuid: str) -> tuple[int, int]:
    matches = []
    for start, end in top_level_child_spans(text, item_kind):
        if block_uuid(text[start:end]) == wanted_uuid:
            matches.append((start, end))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {item_kind} with UUID {wanted_uuid}, found {len(matches)}"
        )
    return matches[0]


def remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    result = text
    for start, end in sorted(spans, reverse=True):
        result = result[:start] + result[end:]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="immutable source PCB")
    parser.add_argument("--output", type=Path, required=True, help="new candidate PCB")
    args = parser.parse_args(argv)

    source = args.input.resolve()
    output = args.output.resolve()
    if source == output:
        raise RuntimeError("input and output must be different files")
    if output.exists():
        raise FileExistsError(output)
    if sha256(source) != EXPECTED_INPUT_SHA256:
        raise RuntimeError("input PCB hash does not match the reviewed duplicate-removal baseline")

    text = source.read_text(encoding="utf-8")
    board_footprints = footprints(text)
    drops: list[tuple[int, int]] = []
    removed_refs: list[str] = []
    removed_copper: list[str] = []

    for policy in POLICIES:
        matches = [item for item in board_footprints if item.ref == policy.ref]
        if len(matches) != 2:
            raise RuntimeError(f"expected exactly two {policy.ref} footprints, found {len(matches)}")
        keep = [item for item in matches if close_enough(at_tuple(item.text), policy.keep_at)]
        drop = [item for item in matches if close_enough(at_tuple(item.text), policy.remove_at)]
        if len(keep) != 1 or len(drop) != 1:
            raise RuntimeError(f"{policy.ref} coordinate policy no longer matches the reviewed board")
        drops.append((drop[0].start, drop[0].end))
        removed_refs.append(f"{policy.ref}@{policy.remove_at[0]:.4f},{policy.remove_at[1]:.4f}")
        for item_kind, copper_uuid in policy.direct_copper:
            drops.append(uuid_span(text, item_kind, copper_uuid))
            removed_copper.append(copper_uuid)

    candidate = remove_spans(text, drops)
    remaining = footprints(candidate)
    duplicate_refs = sorted({item.ref for item in remaining if sum(x.ref == item.ref for x in remaining) > 1})
    if any(policy.ref in duplicate_refs for policy in POLICIES):
        raise RuntimeError(f"duplicate references remain after candidate edit: {duplicate_refs}")

    output.write_text(candidate, encoding="utf-8")
    print(f"wrote {output}")
    print(f"removed footprints: {', '.join(removed_refs)}")
    print(f"removed direct copper UUIDs: {', '.join(removed_copper) or 'none'}")
    print(f"output_sha256={sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
