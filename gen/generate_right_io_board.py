#!/usr/bin/env python3
"""Generate the RIGHT I/O board project skeleton (ducktop2 board split).

J11/J12 (USB2-only), J30 HDMI, J500 GbE, PD2 chain (U42, U2010-15).
FPC-2: 83 signals center<->right. Crossing nets frozen in
verification/BOARD_SPLIT_SPEC_2026-08-28.md.
Phase 1 skeleton: directory + library tables. Phase 2 fills schematics.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))

from build_ducktop2 import PROJDIR

BOARD_DIR = os.path.join(PROJDIR, "right_io")
PROJECT_NAME = "right_io"


def main() -> int:
    os.makedirs(BOARD_DIR, exist_ok=True)
    for name in ("fp-lib-table", "sym-lib-table"):
        src = os.path.join(PROJDIR, "radio_daughterboard", name)
        dst = os.path.join(BOARD_DIR, name)
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copyfile(src, dst)
            print(f"copied {name}")
    print("right_io skeleton ready (Phase 2 fills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())