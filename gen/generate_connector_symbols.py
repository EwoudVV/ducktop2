#!/usr/bin/env python3
"""Connector symbols with the hold-down pads included in the netlist."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def symbol(count):
    name = f"Conn_01x{count:02d}_MP"
    bottom = -(count - 1) * 2.54 - 1.27
    pins = []
    for number in range(1, count + 1):
        pins.append(f'''(pin passive line (at -5.08 {-(number-1)*2.54:g} 0) (length 3.81)
          (name "Pin_{number}" (effects (font (size 1.27 1.27))))
          (number "{number}" (effects (font (size 1.27 1.27)))))''')
    pins.append(f'''(pin passive line (at 5.08 {-(count-1)*1.27:g} 180) (length 3.81)
      (name "MP" (effects (font (size 1.27 1.27))))
      (number "MP" (effects (font (size 1.27 1.27)))))''')
    return f'''(kicad_symbol_lib (version 20231120) (generator "ducktop2")
  (symbol "{name}"
    (pin_names (offset 1.016) hide)
    (in_bom yes) (on_board yes)
    (property "Reference" "J" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{name}" (at 0 {bottom-2.54:g} 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "{name}_0_1"
      (rectangle (start -1.27 1.27) (end 1.27 {bottom:g})
        (stroke (width 0.254) (type default)) (fill (type background))))
    (symbol "{name}_1_1"
      {chr(10).join(pins)})))
'''


if __name__ == "__main__":
    for count in (2, 3, 4):
        path = ROOT / f"Conn_01x{count:02d}_MP.kicad_sym"
        path.write_text(symbol(count))
        print("wrote", path.name)
