#!/usr/bin/env python3
"""Build the BMS flat schematic from its monitor, inhibits and isolated controls."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import build_ducktop2 as b
import genlib
from build_ducktop2 import PROJDIR, stable_uuid, uuid_scope
from generate_bms_monitor import add_bms_monitor
from generate_bms_thermal import add_bms_thermal
from generate_bms_guards import add_bms_guards
from generate_bms_startup import add_bms_startup
from generate_bms_controls import add_bms_controls

BOARD_DIR = Path(PROJDIR) / 'bms'
PROJECT_NAME = 'bms'


def build_bms_sheet(sheet_symbol_uuid):
    s = b.Sheet(f'/{sheet_symbol_uuid}')
    s.refcounters['#PWR'] = 700
    s.refcounters['#FLG'] = 700
    prior = {name: genlib.LIBMAP[name] for name in ('R', 'TestPoint')}
    genlib.LIBMAP.update({name: 'BMS_Passives' for name in prior})
    try:
        add_bms_monitor(s)
        add_bms_thermal(s)
        add_bms_guards(s)
        add_bms_startup(s)
        add_bms_controls(s)
    finally:
        genlib.LIBMAP.update(prior)
    return s


def main():
    BOARD_DIR.mkdir(parents=True, exist_ok=True)
    with uuid_scope('bms:main'):
        sheet = build_bms_sheet(stable_uuid('bms:sheet:main'))
        source = sheet.render(stable_uuid('bms:self:main'), page_number=1, paper='A0')
    (BOARD_DIR / 'bms.kicad_sch').write_text(source)
    print('wrote bms schematic')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
