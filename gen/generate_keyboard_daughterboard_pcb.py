#!/usr/bin/env python3
import re
import sys
from pathlib import Path

from build_ducktop2 import U, reset_uuid_sequence
from generate_keyboard_daughterboard_sheet import (
    KEY_ROWS,
    keyboard_connector_nets,
    safe_net_token,
)


PROJDIR = Path(__file__).resolve().parent.parent
OUT = PROJDIR / "12_keyboard_daughterboard.kicad_pcb"

KICAD_FOOTPRINTS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
FOOTPRINT_SOURCES = {
    "ducktop2:Cherry_MX_ULP_SMD": PROJDIR / "ducktop2.pretty" / "Cherry_MX_ULP_SMD.kicad_mod",
    "Diode_SMD:D_SOD-323": KICAD_FOOTPRINTS / "Diode_SMD.pretty" / "D_SOD-323.kicad_mod",
    "Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal": (
        KICAD_FOOTPRINTS / "Connector_FFC-FPC.pretty" / "Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal.kicad_mod"
    ),
}

BOARD_W = 300.0
BOARD_H = 80.0
UNIT = 18.0
ROW_PITCH = 16.0
ROW_Y0 = 8.0
KEYCAP_H = 14.8

KEY_WIDTHS = {
    "BKSP": 1.75,
    "TAB": 1.25,
    "CAPS": 1.5,
    "ENTER": 1.75,
    "LSHIFT": 1.75,
    "RSHIFT": 1.25,
    "SPACE_L": 2.25,
    "SPACE_R": 2.25,
}

GAP_AFTER = {
    "MENU": 1.0,
}


def fmt(n):
    text = f"{float(n):.4f}".rstrip("0").rstrip(".")
    return text or "0"


def sexpr_block_at(text, start):
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1], idx + 1
    raise ValueError("unterminated s-expression")


def iter_symbol_blocks(text):
    pos = 0
    while True:
        start = text.find("(symbol\n", pos)
        if start < 0:
            return
        block, pos = sexpr_block_at(text, start)
        yield block


def schematic_paths():
    paths = {}
    sch = (PROJDIR / "12_keyboard_daughterboard.kicad_sch").read_text(encoding="utf-8")
    for block in iter_symbol_blocks(sch):
        ref = re.search(r'\(property "Reference" "([^"]+)"', block)
        sym_uuid = re.search(r'\(uuid ([0-9a-f-]+)\)', block)
        sheet_path = re.search(r'\(path "([^"]+)"', block)
        if ref and sym_uuid and sheet_path:
            base = sheet_path.group(1).rstrip("/")
            paths[ref.group(1)] = f"{base}/{sym_uuid.group(1)}" if base else f"/{sym_uuid.group(1)}"
    return paths


def raw_footprint(lib_id):
    path = FOOTPRINT_SOURCES[lib_id]
    text = path.read_text(encoding="utf-8")
    short_name = lib_id.split(":", 1)[1]
    text = text.replace(f'(footprint "{short_name}"', f'(footprint "{lib_id}"', 1)
    return text


def set_reference_and_value(text, ref, value):
    text = re.sub(r'(\(property "Reference" ")[^"]*(")', rf'\g<1>{ref}\2', text, count=1)
    text = re.sub(r'(\(property "Value" ")[^"]*(")', rf'\g<1>{value}\2', text, count=1)
    text = re.sub(r'(\(fp_text reference ")[^"]*(")', rf'\g<1>{ref}\2', text, count=1)
    text = re.sub(r'(\(fp_text value ")[^"]*(")', rf'\g<1>{value}\2', text, count=1)
    return text


def add_pad_rotation(block, degrees):
    if degrees is None:
        return block

    def repl(match):
        x, y, existing = match.groups()
        if existing:
            return match.group(0)
        return f"(at {x} {y} {fmt(degrees)})"

    return re.sub(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)', repl, block, count=1)


def add_pad_nets(text, pad_net_names, net_ids, pad_rotation=None):
    out = []
    pos = 0
    while True:
        start = text.find("(pad ", pos)
        if start < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        block, end = sexpr_block_at(text, start)
        match = re.match(r'\(pad\s+("[^"]*"|[^\s\)]+)\s+([^\s\)]+)', block)
        if match:
            raw_name, pad_type = match.groups()
            pad_name = raw_name[1:-1] if raw_name.startswith('"') else raw_name
            block = add_pad_rotation(block, pad_rotation)
            net_name = pad_net_names.get(pad_name)
            if net_name and pad_type != "np_thru_hole":
                pinfunction = pad_name if pad_name else "MP"
                net_line = (
                    f'\n\t\t(net {net_ids[net_name]} "{net_name}")'
                    f' (pinfunction "{pinfunction}") (pintype "passive")'
                )
                block = block[:-1] + net_line + block[-1]
        out.append(block)
        pos = end
    return "".join(out)


def footprint(lib_id, ref, value, x, y, rot, pad_net_names, net_ids, path, dnp=False, pad_rotation=None):
    text = raw_footprint(lib_id)
    text = set_reference_and_value(text, ref, value)
    text = add_pad_nets(text, pad_net_names, net_ids, pad_rotation=pad_rotation)
    lines = text.splitlines()
    lines.insert(1, f'  (tstamp {U()})')
    lines.insert(2, f'  (at {fmt(x)} {fmt(y)} {fmt(rot)})')
    if path:
        lines.insert(3, f'  (path "{path}")')
    if dnp:
        lines.insert(4 if path else 3, '  (dnp yes)')
        lines.insert(5 if path else 4, '  (in_bom no)')
    return "\n".join("  " + line if line else "" for line in lines)


def key_width(code):
    return KEY_WIDTHS.get(code, 1.0)


def key_placements():
    index = 0
    for row, keys in enumerate(KEY_ROWS):
        row_units = sum(key_width(code) + GAP_AFTER.get(code, 0.0) for _col, code, _value in keys)
        left = (BOARD_W - row_units * UNIT) / 2.0
        cursor = left
        y = ROW_Y0 + row * ROW_PITCH
        for col, code, value in keys:
            width = key_width(code)
            x = cursor + width * UNIT / 2.0
            yield {
                "index": index,
                "row": row,
                "col": col,
                "code": code,
                "value": value,
                "width": width,
                "x": x,
                "y": y,
            }
            cursor += (width + GAP_AFTER.get(code, 0.0)) * UNIT
            index += 1


def board_header():
    return f'''(kicad_pcb (version 20260206) (generator "codex") (generator_version "10.0")
  (general
    (thickness 0.8)
  )
  (paper "A3")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
    (50 "User.1" user)
    (51 "User.2" user)
    (52 "User.3" user)
    (53 "User.4" user)
    (54 "User.5" user)
    (55 "User.6" user)
    (56 "User.7" user)
    (57 "User.8" user)
    (58 "User.9" user)
  )
  (setup
    (pad_to_mask_clearance 0)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros false)
      (usegerberextensions false)
      (usegerberattributes true)
      (usegerberadvancedattributes true)
      (creategerberjobfile true)
      (dashed_line_dash_ratio 12.000000)
      (dashed_line_gap_ratio 3.000000)
      (svgprecision 4)
      (plotframeref false)
      (viasonmask false)
      (mode 1)
      (useauxorigin false)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (dxfpolygonmode true)
      (dxfimperialunits true)
      (dxfusepcbnewfont true)
      (psnegative false)
      (psa4output false)
      (plotreference true)
      (plotvalue true)
      (plotinvisibletext false)
      (sketchpadsonfab false)
      (subtractmaskfromsilk false)
      (outputformat 1)
      (mirror false)
      (drillshape 0)
      (scaleselection 1)
      (outputdirectory "")
    )
  )
'''


def gr_line(x1, y1, x2, y2, layer="Edge.Cuts", width=0.1):
    return (
        f'  (gr_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)})\n'
        f'    (stroke (width {fmt(width)}) (type default)) (layer "{layer}") (uuid {U()}))'
    )


def gr_rect(x1, y1, x2, y2, layer="Dwgs.User", width=0.05):
    return (
        f'  (gr_rect (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)})\n'
        f'    (stroke (width {fmt(width)}) (type dash)) (fill no) (layer "{layer}") (uuid {U()}))'
    )


def gr_text(text, x, y, layer="Cmts.User"):
    escaped = text.replace('"', "'")
    return (
        f'  (gr_text "{escaped}" (at {fmt(x)} {fmt(y)} 0) (layer "{layer}") (uuid {U()})\n'
        f'    (effects (font (size 1.2 1.2) (thickness 0.15)) (justify left bottom)))'
    )


def main():
    reset_uuid_sequence("12_keyboard_daughterboard_pcb")
    schematic_path_by_ref = schematic_paths()

    net_ids = {"": 0}

    def net_id(name):
        if name not in net_ids:
            net_ids[name] = len(net_ids)
        return net_ids[name]

    for name in ["GND", "MCU_3V3", "I2C_SCL", "I2C_SDA", "SYS_5V"]:
        net_id(name)
    for idx in range(8):
        net_id(f"KB_ROW{idx}")
    for idx in range(16):
        net_id(f"KB_COL{idx}")
    for key in key_placements():
        net_id(f"KB_R{key['row']}_C{key['col']}_{safe_net_token(key['code'])}")

    footprints = []
    drawings = []

    for key in key_placements():
        ref_n = 320 + key["index"]
        key_node = f"KB_R{key['row']}_C{key['col']}_{safe_net_token(key['code'])}"
        footprints.append(footprint(
            "ducktop2:Cherry_MX_ULP_SMD",
            f"SW{ref_n}",
            key["value"],
            key["x"],
            key["y"],
            0,
            {"1": key_node, "2": f"KB_COL{key['col']}"},
            net_ids,
            schematic_path_by_ref.get(f"SW{ref_n}"),
        ))
        footprints.append(footprint(
            "Diode_SMD:D_SOD-323",
            f"D{ref_n}",
            "1N4148W",
            key["x"] + 8.2,
            key["y"],
            90,
            {"1": key_node, "2": f"KB_ROW{key['row']}"},
            net_ids,
            schematic_path_by_ref.get(f"D{ref_n}"),
        ))
        cap_w = key["width"] * UNIT - 1.2
        drawings.append(gr_rect(
            key["x"] - cap_w / 2.0,
            key["y"] - KEYCAP_H / 2.0,
            key["x"] + cap_w / 2.0,
            key["y"] + KEYCAP_H / 2.0,
        ))

    connector_nets = {pin: net for pin, (net, _kind) in keyboard_connector_nets().items()}
    footprints.append(footprint(
        "Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal",
        "J320",
        "Keyboard FFC",
        292.0,
        40.0,
        90,
        connector_nets,
        net_ids,
        schematic_path_by_ref.get("J320"),
        pad_rotation=90,
    ))

    edge = [
        gr_line(0, 0, BOARD_W, 0),
        gr_line(BOARD_W, 0, BOARD_W, BOARD_H),
        gr_line(BOARD_W, BOARD_H, 0, BOARD_H),
        gr_line(0, BOARD_H, 0, 0),
    ]

    comments = [
        gr_text("Ducktop2 MX ULP keyboard daughterboard rev A: 300 x 80 mm Edge.Cuts", 4, 86),
        gr_text("Switches use 18 mm X pitch / 16 mm row pitch. Dashed rectangles are intended keycap envelopes.", 4, 91),
        gr_text("J320 is parked in the right margin as a routing anchor; move only if the final flex exit requires it.", 4, 96),
    ]

    body = [board_header()]
    for name, idx in sorted(net_ids.items(), key=lambda item: item[1]):
        body.append(f'  (net {idx} "{name}")')
    body.append("")
    body.extend(footprints)
    body.extend(edge)
    body.extend(drawings)
    body.extend(comments)
    body.append(")")
    OUT.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"switches={sum(1 for _ in key_placements())} diodes={sum(1 for _ in key_placements())} outline={BOARD_W:g}x{BOARD_H:g}mm")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
