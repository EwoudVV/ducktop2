#!/usr/bin/env python3
"""Generate the Left I/O board project skeleton (ducktop2 board split).

The left board carries: J21-25, J190, hub U1700, PD1 chain (U41, U2000-06),
SS muxes (U1742/45, U1782/85), USB-A cluster (U1800-04). Contents and
crossing nets are frozen in verification/BOARD_SPLIT_SPEC_2026-08-28.md
(FPC-1: 75 signals center<->left).

Phase 1 skeleton: creates the project directory + library tables.
Phase 2 fills the schematics (see the split plan).
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))

from build_ducktop2 import PROJDIR

BOARD_DIR = os.path.join(PROJDIR, "left_io")
PROJECT_NAME = "left_io"

BOARD_PARTS = {
    # (reference, lib_id, value) — populated in Phase 2 from the frozen
    # board assignment (/tmp/board_of.json 'L' set).
}

FPC1_SIGNALS = 75  # frozen in BOARD_SPLIT_SPEC_2026-08-28.md


def main() -> int:
    os.makedirs(BOARD_DIR, exist_ok=True)
    for name in ("fp-lib-table", "sym-lib-table"):
        src = os.path.join(PROJDIR, "radio_daughterboard", name)
        dst = os.path.join(BOARD_DIR, name)
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copyfile(src, dst)
            print(f"copied {name}")
    print(f"left_io skeleton ready: {len(BOARD_PARTS)} parts (Phase 2 fills)")
    print(f"FPC-1 crossing: {FPC1_SIGNALS} signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())