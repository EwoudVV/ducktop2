#!/usr/bin/env python3
"""Generate the BATTERY BMS board project skeleton (ducktop2 board split).

J2 pack connector, Q11/Q12 reverse FETs, Q703/Q704 charge/discharge FETs,
RS10/RS11 shunts, U10 fuel gauge, U11 protector, F1 fuse. MacBook-style
board mounted on the pack. FPC-3: 16 signals center<->BMS. Crossing nets
frozen in verification/BOARD_SPLIT_SPEC_2026-08-28.md.
Phase 1 skeleton: directory + library tables. Phase 2 fills schematics.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))

from build_ducktop2 import PROJDIR

BOARD_DIR = os.path.join(PROJDIR, "bms")
PROJECT_NAME = "bms"


def main() -> int:
    os.makedirs(BOARD_DIR, exist_ok=True)
    for name in ("fp-lib-table", "sym-lib-table"):
        src = os.path.join(PROJDIR, "radio_daughterboard", name)
        dst = os.path.join(BOARD_DIR, name)
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copyfile(src, dst)
            print(f"copied {name}")
    print("bms skeleton ready (Phase 2 fills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())