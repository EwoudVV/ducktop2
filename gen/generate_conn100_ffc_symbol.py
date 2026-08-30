#!/usr/bin/env python3
"""Generate gen/Conn_01x100_FFC_MP.kicad_sym (Phase 4a).

Derived from the existing 30-pin FFC/MP symbol pattern (pins every 2.54mm,
small tick rectangles at each pin, MP hold-down pin at the bottom).  The
MP pin is passive; boards ground it via the schematic wiring.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from build_ducktop2 import U

OUT = os.path.join(os.path.dirname(__file__), "Conn_01x100_FFC_MP.kicad_sym")
PINS = 100
PIN_PITCH = 2.54
PIN1_Y = 35.56
PIN_LAST_Y = PIN1_Y - (PINS - 1) * PIN_PITCH
BODY_TOP = 36.83
BODY_BOTTOM = PIN_LAST_Y - 1.27
MP_Y = BODY_BOTTOM - 1.27
VALUE_Y = BODY_BOTTOM - 2.54


def pin_y(n):
    return round(PIN1_Y - (n - 1) * PIN_PITCH, 6)


parts = []
parts.append("(kicad_symbol_lib")
parts.append("\t(version 20251024)")
parts.append('\t(generator "ducktop2_project_lib")')
parts.append('\t(generator_version "10.0")')
parts.append('\t(symbol "Conn_01x100_FFC_MP"')
parts.append("\t\t(pin_names")
parts.append("\t\t\t(offset 1.016)")
parts.append("\t\t\t(hide yes)")
parts.append("\t\t)")
parts.append("\t\t(exclude_from_sim no)")
parts.append("\t\t(in_bom yes)")
parts.append("\t\t(on_board yes)")
parts.append("\t\t(in_pos_files yes)")
parts.append("\t\t(duplicate_pin_numbers_are_jumpers no)")
for prop, value, y in (("Reference", "J", 38.1),
                       ("Value", "Conn_01x100_FFC_MP", VALUE_Y)):
    parts.append(f'\t\t(property "{prop}" "{value}"')
    parts.append(f"\t\t\t(at 0 {y:g} 0)")
    parts.append("\t\t\t(show_name no)")
    parts.append("\t\t\t(do_not_autoplace no)")
    parts.append("\t\t\t(effects")
    parts.append("\t\t\t\t(font")
    parts.append("\t\t\t\t\t(size 1.27 1.27)")
    parts.append("\t\t\t\t)")
    parts.append("\t\t\t)")
    parts.append("\t\t)")
for prop in ("Footprint", "Datasheet", "Description", "ki_keywords"):
    value = {"Footprint": "", "Datasheet": "",
             "Description": "Generic connector, single row, 01x100, script generated",
             "ki_keywords": "connector"}[prop]
    parts.append(f'\t\t(property "{prop}" "{value}"')
    parts.append("\t\t\t(at 0 0 0)")
    parts.append("\t\t\t(show_name no)")
    parts.append("\t\t\t(do_not_autoplace no)")
    parts.append("\t\t\t(hide yes)")
    parts.append("\t\t\t(effects")
    parts.append("\t\t\t\t(font")
    parts.append("\t\t\t\t\t(size 1.27 1.27)")
    parts.append("\t\t\t\t)")
    parts.append("\t\t\t)")
    parts.append("\t\t)")
parts.append('\t\t(property "ki_fp_filters" "Connector*:*_1x??_*"')
parts.append("\t\t\t(at 0 0 0)")
parts.append("\t\t\t(show_name no)")
parts.append("\t\t\t(do_not_autoplace no)")
parts.append("\t\t\t(hide yes)")
parts.append("\t\t\t(effects")
parts.append("\t\t\t\t(font")
parts.append("\t\t\t\t\t(size 1.27 1.27)")
parts.append("\t\t\t\t)")
parts.append("\t\t\t)")
parts.append("\t\t)")
parts.append('\t\t(symbol "Conn_01x100_FFC_MP_1_1"')
parts.append("\t\t\t(rectangle")
parts.append(f"\t\t\t\t(start -1.27 {BODY_TOP:g})")
parts.append(f"\t\t\t\t(end 1.27 {BODY_BOTTOM:g})")
parts.append("\t\t\t\t(stroke")
parts.append("\t\t\t\t\t(width 0.254)")
parts.append("\t\t\t\t\t(type default)")
parts.append("\t\t\t\t)")
parts.append("\t\t\t\t(fill")
parts.append("\t\t\t\t\t(type background)")
parts.append("\t\t\t\t)")
parts.append("\t\t\t)")
for n in range(1, PINS + 1):
    y = pin_y(n)
    parts.append("\t\t\t(rectangle")
    parts.append(f"\t\t\t\t(start -1.27 {y + 0.127:g})")
    parts.append(f"\t\t\t\t(end 0 {y - 0.127:g})")
    parts.append("\t\t\t\t(stroke")
    parts.append("\t\t\t\t\t(width 0.1524)")
    parts.append("\t\t\t\t\t(type default)")
    parts.append("\t\t\t\t)")
    parts.append("\t\t\t\t(fill")
    parts.append("\t\t\t\t\t(type none)")
    parts.append("\t\t\t\t)")
    parts.append("\t\t\t)")
for n in range(1, PINS + 1):
    y = pin_y(n)
    parts.append("\t\t\t(pin passive line")
    parts.append(f"\t\t\t\t(at -5.08 {y:g} 0)")
    parts.append("\t\t\t\t(length 3.81)")
    parts.append(f'\t\t\t\t(name "Pin_{n}"')
    parts.append("\t\t\t\t\t(effects")
    parts.append("\t\t\t\t\t\t(font")
    parts.append("\t\t\t\t\t\t\t(size 1.27 1.27)")
    parts.append("\t\t\t\t\t\t)")
    parts.append("\t\t\t\t\t)")
    parts.append("\t\t\t\t)")
    parts.append(f'\t\t\t\t(number "{n}"')
    parts.append("\t\t\t\t\t(effects")
    parts.append("\t\t\t\t\t\t(font")
    parts.append("\t\t\t\t\t\t\t(size 1.27 1.27)")
    parts.append("\t\t\t\t\t\t)")
    parts.append("\t\t\t\t\t)")
    parts.append("\t\t\t\t)")
    parts.append("\t\t\t)")
parts.append("\t\t\t(pin passive line")
parts.append(f"\t\t\t\t(at 5.08 {MP_Y:g} 180)")
parts.append("\t\t\t\t(length 2.54)")
parts.append('\t\t\t\t(name "MP"')
parts.append("\t\t\t\t\t(effects")
parts.append("\t\t\t\t\t\t(font")
parts.append("\t\t\t\t\t\t\t(size 1.27 1.27)")
parts.append("\t\t\t\t\t\t)")
parts.append("\t\t\t\t\t)")
parts.append("\t\t\t\t)")
parts.append('\t\t\t\t(number "MP"')
parts.append("\t\t\t\t\t(effects")
parts.append("\t\t\t\t\t\t(font")
parts.append("\t\t\t\t\t\t\t(size 1.27 1.27)")
parts.append("\t\t\t\t\t\t)")
parts.append("\t\t\t\t\t)")
parts.append("\t\t\t\t)")
parts.append("\t\t\t)")
parts.append("\t\t)")
parts.append("\t\t(embedded_fonts no)")
parts.append("\t)")
parts.append(")")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(parts) + "\n")
print(f"wrote {OUT}")