#!/usr/bin/env python3
"""Initial main-PCB layout prep for ducktop2.

This script is intentionally conservative: it does not regenerate schematics,
does not import footprints, and does not touch the keyboard daughterboard PCB.
It only normalizes the main board layer table, adds starter routing presets in
the KiCad project file, drops non-fabrication mechanical guide rectangles on
Dwgs.User, and moves already-imported mainboard footprints into rough zones.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from sync_main_pcb_from_netlist import ANCHORS_MM as MAKER_ANCHORS_MM


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "ducktop2.kicad_pcb"
PRO = ROOT / "ducktop2.kicad_pro"


STANDARD_6LAYER_BLOCK = """\t(layers
\t\t(0 "F.Cu" signal)
\t\t(1 "In1.Cu" power)
\t\t(2 "In2.Cu" signal)
\t\t(3 "In3.Cu" signal)
\t\t(4 "In4.Cu" power)
\t\t(31 "B.Cu" signal)
\t\t(32 "B.Adhes" user "B.Adhesive")
\t\t(33 "F.Adhes" user "F.Adhesive")
\t\t(34 "B.Paste" user)
\t\t(35 "F.Paste" user)
\t\t(36 "B.SilkS" user "B.Silkscreen")
\t\t(37 "F.SilkS" user "F.Silkscreen")
\t\t(38 "B.Mask" user)
\t\t(39 "F.Mask" user)
\t\t(40 "Dwgs.User" user "User.Drawings")
\t\t(41 "Cmts.User" user "User.Comments")
\t\t(42 "Eco1.User" user "User.Eco1")
\t\t(43 "Eco2.User" user "User.Eco2")
\t\t(44 "Edge.Cuts" user)
\t\t(45 "Margin" user)
\t\t(46 "B.CrtYd" user "B.Courtyard")
\t\t(47 "F.CrtYd" user "F.Courtyard")
\t\t(48 "B.Fab" user)
\t\t(49 "F.Fab" user)
\t\t(50 "User.1" user)
\t\t(51 "User.2" user)
\t\t(52 "User.3" user)
\t\t(53 "User.4" user)
\t\t(54 "User.5" user)
\t\t(55 "User.6" user)
\t\t(56 "User.7" user)
\t\t(57 "User.8" user)
\t\t(58 "User.9" user)
\t)"""


def balanced_end(text: str, start: int) -> int:
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
    raise ValueError(f"unbalanced S-expression starting at {start}")


def iter_blocks(text: str, marker: str) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    idx = 0
    while True:
        i = text.find(marker, idx)
        if i < 0:
            return blocks
        start = i + (1 if marker.startswith("\n") else 0)
        end = balanced_end(text, start)
        blocks.append((start, end, text[start:end]))
        idx = end


def extract(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else default


@dataclass(frozen=True)
class Footprint:
    start: int
    end: int
    text: str
    ref: str
    value: str
    sheetfile: str
    footprint: str


def footprints(text: str) -> list[Footprint]:
    out: list[Footprint] = []
    for start, end, block in iter_blocks(text, "\n\t(footprint "):
        out.append(
            Footprint(
                start=start,
                end=end,
                text=block,
                ref=extract(r'\(property\s+"Reference"\s+"([^"]+)"', block),
                value=extract(r'\(property\s+"Value"\s+"([^"]*)"', block),
                sheetfile=extract(r'\(sheetfile\s+"([^"]*)"', block),
                footprint=extract(r'^\s*\(footprint\s+"([^"]+)"', block),
            )
        )
    return out


def format_num(x: float) -> str:
    if abs(x - round(x)) < 0.0005:
        return str(int(round(x)))
    return f"{x:.3f}".rstrip("0").rstrip(".")


def set_footprint_at(block: str, x: float, y: float, rot: float | None = None) -> str:
    def repl(match: re.Match[str]) -> str:
        if rot is None or abs(rot) < 0.0005:
            return f'{match.group(1)}{format_num(x)} {format_num(y)})'
        return f'{match.group(1)}{format_num(x)} {format_num(y)} {format_num(rot % 360)})'

    return re.sub(
        r'(\n\s*\(at\s+)[-0-9.]+\s+[-0-9.]+(?:\s+[-0-9.]+)?\)',
        repl,
        block,
        count=1,
    )


def natural_key(ref: str) -> tuple[str, int, str]:
    m = re.match(r"([A-Z]+)(\d+)(.*)", ref)
    if not m:
        return (ref, -1, "")
    return (m.group(1), int(m.group(2)), m.group(3))


CUTOUTS = [
    (18, 8, 122, 72),
    (23, 183, 127, 247),
    (128, 8, 246, 82),
    (248, 58, 312, 162),
]


def in_cutout(x: float, y: float, clearance: float = 2.0) -> bool:
    for x1, y1, x2, y2 in CUTOUTS:
        if x1 - clearance <= x <= x2 + clearance and y1 - clearance <= y <= y2 + clearance:
            return True
    return False


def grid_points(x: float, y: float, w: float, h: float, step_x: float = 4.0, step_y: float = 4.0):
    yy = y
    while yy <= y + h + 1e-6:
        xx = x
        while xx <= x + w + 1e-6:
            if not in_cutout(xx, yy) and 3 <= xx <= 387 and 3 <= yy <= 247:
                yield (xx, yy)
            xx += step_x
        yy += step_y


SHEET_ZONES = {
    "01_power_battery.kicad_sch": (18, 76, 116, 52),
    "02_ec_mcu.kicad_sch": (162, 95, 82, 58),
    "03_mu_carrier.kicad_sch": (218, 162, 68, 44),
    "04_usb_c_io.kicad_sch": (315, 40, 58, 76),
    "05_power_inputs.kicad_sch": (16, 82, 118, 44),
    "06_tcp0_external_hdmi.kicad_sch": (322, 82, 52, 42),
    "07_radio_oled_gps.kicad_sch": (18, 112, 105, 60),
    "08_internal_services.kicad_sch": (185, 118, 190, 42),
    "09_ham_radio.kicad_sch": (18, 112, 118, 64),
    "11_intehill_monitor_interface.kicad_sch": (132, 84, 110, 42),
    "12_keyboard_interface.kicad_sch": (318, 82, 48, 18),
    "13_radio_audio_codec.kicad_sch": (210, 202, 68, 36),
    "14_maker_mcu.kicad_sch": (338, 18, 42, 110),
}


# Hand-placed anchors for the big/externally constrained parts. Coordinates are
# rough KiCad board coordinates in millimeters, derived from mechanical/floorplan_revA.json.
PLACEMENTS: dict[str, tuple[float, float, float | None]] = {
    # Battery and wide-DC power entry
    "J2": (128, 96, 0),
    "J1": (126, 42, 0),
    "F1": (124, 108, 0),
    "RS1": (132, 116, 0),
    "J190": (6, 92, 270),
    "F190": (24, 92, 0),
    "D190": (37, 92, 0),
    "U2": (82, 98, 0),
    "U10": (118, 82, 0),
    "U1": (112, 112, 0),
    "U3": (56, 114, 0),
    "L1": (82, 118, 0),
    "L2": (42, 118, 0),
    # EC and service headers
    "U4": (205, 122, 0),
    "U5": (230, 128, 0),
    "J4": (168, 151, 0),
    "J7": (190, 153, 0),
    "J13": (214, 153, 0),
    "J14": (238, 153, 0),
    "J15": (238, 137, 0),
    "J16": (168, 137, 0),
    "SW1": (156, 125, 0),
    # LattePanda Mu, hub, storage
    "A1": (305, 215, 0),
    "J10": (170, 151, 0),
    "U9": (242, 174, 0),
    "Y3": (228, 188, 0),
    "U6": (230, 214, 0),
    "U7": (248, 214, 0),
    "U8": (224, 174, 0),
    "L4": (230, 226, 0),
    "L5": (248, 226, 0),
    "J8": (286, 172, 0),
    "J9": (266, 172, 0),
    "SW2": (286, 185, 0),
    "SW3": (286, 198, 0),
    # External and hub USB-C ports
    "J21": (6, 40, 270),
    "J22": (6, 58, 270),
    "J23": (6, 76, 270),
    "U41": (36, 40, 0),
    "U42": (36, 58, 0),
    "U43": (36, 76, 0),
    "J11": (384, 42, 90),
    "J12": (384, 62, 90),
    "U21": (340, 42, 0),
    "U22": (356, 42, 0),
    "U31": (340, 66, 0),
    "U32": (356, 66, 0),
    "U23": (367, 42, 0),
    "U24": (367, 50, 0),
    "U25": (367, 58, 0),
    "U33": (367, 66, 0),
    "U34": (367, 74, 0),
    "U35": (367, 82, 0),
    # External HDMI side port
    "J30": (384, 92, 90),
    "U50": (358, 92, 0),
    "U51": (358, 104, 0),
    "U52": (346, 116, 0),
    "F150": (374, 116, 0),
    # Intehill monitor interface near controller cutout
    "J300": (178, 86, 0),
    "J301": (178, 100, 0),
    "J302": (224, 86, 0),
    "J303": (224, 100, 0),
    "U300": (146, 94, 0),
    "U301": (146, 108, 0),
    "U302": (202, 113, 0),
    "U303": (224, 116, 0),
    "F300": (214, 116, 0),
    # Trackpad, touch, fan/cooling
    "J58": (197.5, 127.5, 0),
    "J57": (182, 133, 0),
    "U62": (208, 128, 0),
    "F201": (197, 140, 0),
    "J52": (337, 136, 0),
    "F200": (328, 136, 0),
    "Q200": (319, 136, 0),
    "J56": (276, 176, 0),
    "J54": (176, 118, 0),
    "J53": (166, 118, 0),
    "J50": (174, 144, 0),
    "J51": (186, 144, 0),
    # Radio/GNSS/OLED
    "J41": (268, 24, 0),
    "J45": (306.96, 15, 90),
    "J40": (82, 142, 0),
    "U40": (112, 120, 0),
    "J42": (112, 136, 0),
    "J43": (112, 152, 0),
    "J44": (112, 168, 0),
    "F10": (118, 154, 0),
    "J240": (6, 122, 270),
    "J241": (6, 140, 270),
    "J250": (6, 158, 270),
    "J251": (6, 176, 270),
    "U240": (36, 132, 0),
    "U250": (36, 160, 0),
    "J70": (74, 124, 0),
    "J71": (74, 154, 0),
    "J72": (116, 172, 0),
    "U70": (114, 148, 0),
    # Radio USB audio codec and front speaker area
    "U330": (238, 214, 0),
    "Y330": (258, 214, 0),
    "J330": (274, 214, 0),
    # Maker MCU / exposed tinkering header
    "U901": (369, 28, 0),
    "U902": (359.5, 20, 0),
    "U903": (367, 8, 0),
    "J901": (356, 82, 0),
    "J902": (356, 116, 0),
    "U900": (338, 58, 0),
    "SW900": (338, 34, 0),
    "SW901": (338, 46, 0),
    # Keyboard interface only; the switch matrix belongs to 12_keyboard_daughterboard.kicad_pcb.
    "J310": (334, 89, 0),
    "C318": (320, 94, 0),
    "C319": (326, 94, 0),
}


MECH_RECTS = [
    ("MECH: battery B cutout", 18, 8, 122, 72),
    ("MECH: Intehill controller cutout", 128, 8, 246, 82),
    ("MECH: battery C cutout", 248, 58, 312, 162),
    ("MECH: battery A cutout", 23, 183, 127, 247),
    ("MECH: MX ULP keyboard PCB", 60, 45, 333.5, 125),
    ("MECH: keyboard FFC exit", 320, 70, 365, 94),
    ("MECH: trackpad bay", 130, 170, 265, 244),
    ("MECH: palm-rest comfort zone", 70, 166, 320, 244),
    ("MECH: Mu module envelope", 270, 185, 340, 245),
    ("MECH: cold plate", 270, 180, 344, 244),
    ("MECH: blower", 290, 130, 335, 175),
    ("MECH: fin stack", 340, 130, 390, 180),
    ("MECH: left side ports", 0, 30, 12, 96),
    ("MECH: right side ports", 378, 30, 390, 96),
    ("MECH: rear antenna connectors", 0, 105, 12, 191),
]


GUIDE_NAMESPACE = uuid.UUID("5ce02a94-0d46-45f8-bf53-edcbf5531db7")


def guide_uuid(name: str) -> str:
    return str(uuid.uuid5(GUIDE_NAMESPACE, name))


def remove_generated_guides(text: str) -> str:
    guide_ids = {guide_uuid(f"rect:{name}") for name, *_ in MECH_RECTS}
    guide_ids |= {guide_uuid(f"text:{name}") for name, *_ in MECH_RECTS}
    for marker in ("\n\t(gr_rect", "\n\t(gr_text"):
        for start, end, block in reversed(iter_blocks(text, marker)):
            if any(gid in block for gid in guide_ids):
                text = text[:start - 1] + text[end:]
    return text


def make_guides() -> str:
    blocks: list[str] = []
    for name, x1, y1, x2, y2 in MECH_RECTS:
        blocks.append(
            f'''\t(gr_rect
\t\t(start {format_num(x1)} {format_num(y1)})
\t\t(end {format_num(x2)} {format_num(y2)})
\t\t(stroke
\t\t\t(width 0.12)
\t\t\t(type dash)
\t\t)
\t\t(fill no)
\t\t(layer "Dwgs.User")
\t\t(uuid "{guide_uuid(f"rect:{name}")}")
\t)'''
        )
        blocks.append(
            f'''\t(gr_text "{name}"
\t\t(at {format_num(x1 + 2)} {format_num(y1 + 4)} 0)
\t\t(layer "Dwgs.User")
\t\t(uuid "{guide_uuid(f"text:{name}")}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.4 1.4)
\t\t\t\t(thickness 0.18)
\t\t\t)
\t\t\t(justify left)
\t\t)
\t)'''
        )
    return "\n" + "\n".join(blocks) + "\n"


def replace_layers(text: str) -> str:
    start = text.find("\n\t(layers")
    if start < 0:
        raise RuntimeError("could not find board layer table")
    start += 1
    end = balanced_end(text, start)
    return text[:start] + STANDARD_6LAYER_BLOCK + text[end:]


def place_footprints(text: str) -> str:
    fps = footprints(text)
    if any(re.match(r"SW3[2-9][0-9]$", fp.ref) or re.match(r"D3[2-9][0-9]$", fp.ref) or fp.ref == "J320" for fp in fps):
        raise RuntimeError("keyboard daughterboard footprints are present in main PCB; aborting placement")

    occupied_refs: set[str] = set(PLACEMENTS)
    sheet_iters = {
        sheet: iter(grid_points(*zone, 3.0, 3.0))
        for sheet, zone in SHEET_ZONES.items()
    }
    updates: dict[str, tuple[float, float, float | None]] = dict(PLACEMENTS)

    for fp in sorted(fps, key=lambda f: (f.sheetfile, natural_key(f.ref))):
        if fp.ref in occupied_refs:
            continue
        if not fp.sheetfile or fp.sheetfile not in sheet_iters:
            continue
        point_iter = sheet_iters[fp.sheetfile]
        while True:
            try:
                x, y = next(point_iter)
            except StopIteration as exc:
                raise RuntimeError(f"ran out of placement grid for {fp.sheetfile}") from exc
            # Keep a tiny moat around explicit anchors so repeated footprints are readable.
            if all(math.hypot(x - ax, y - ay) > 2.2 for ax, ay, _ in updates.values()):
                updates[fp.ref] = (x, y, 0)
                break

    new_text = text
    for fp in reversed(fps):
        if fp.ref not in updates:
            continue
        x, y, rot = updates[fp.ref]
        new_block = set_footprint_at(fp.text, x, y, rot)
        new_text = new_text[:fp.start] + new_block + new_text[fp.end:]
    return new_text


def demote_footprint_edge_cuts(text: str) -> str:
    """Keep board outline Edge.Cuts clean by moving footprint-local cut guides."""
    new_text = text
    for fp in reversed(footprints(text)):
        if '"Edge.Cuts"' not in fp.text:
            continue
        new_block = fp.text.replace('(layer "Edge.Cuts")', '(layer "Dwgs.User")')
        new_text = new_text[:fp.start] + new_block + new_text[fp.end:]
    return new_text


def add_guides(text: str) -> str:
    text = remove_generated_guides(text)
    insert = text.rfind("\n)")
    if insert < 0:
        raise RuntimeError("could not find final board close paren")
    return text[:insert] + make_guides() + text[insert:]


OLED_MODULE_FOOTPRINT = "ducktop2:SSD1306_0.96in_Module_4Pin"


def add_oled_module_envelopes(text: str) -> str:
    """Attach the 27.3 mm module outline to J41/J45 without touching their pads or nets."""
    replacements: list[tuple[int, int, str]] = []
    for fp in footprints(text):
        if fp.ref not in {"J41", "J45"}:
            continue
        block = re.sub(
            r'^(\s*\(footprint )"[^"]+"',
            lambda match: f'{match.group(1)}"{OLED_MODULE_FOOTPRINT}"',
            fp.text,
            count=1,
        )
        # Replace the old generic pin-header artwork with the module envelope.
        # Properties, paths, pads, pad UUIDs, and net assignments remain intact.
        for marker in (
            "\n\t\t(fp_line",
            "\n\t\t(fp_rect",
            "\n\t\t(fp_circle",
            "\n\t\t(fp_arc",
            "\n\t\t(fp_poly",
            "\n\t\t(fp_text",
            "\n\t\t(model",
        ):
            for start, end, _ in reversed(iter_blocks(block, marker)):
                block = block[:start - 1] + block[end:]
        insert = block.find("\n\t\t(pad ")
        if insert < 0:
            raise RuntimeError(f"{fp.ref} has no pads")
        graphics = f'''\n\t\t(fp_rect
\t\t\t(start -25.8 -9.84)
\t\t\t(end 1.5 17.46)
\t\t\t(stroke (width 0.25) (type solid))
\t\t\t(fill none)
\t\t\t(layer "Dwgs.User")
\t\t\t(uuid "{guide_uuid(f"oled:{fp.ref}:dwgs-outline")}")
\t\t)
\t\t(fp_rect
\t\t\t(start -25.8 -9.84)
\t\t\t(end 1.5 17.46)
\t\t\t(stroke (width 0.1) (type solid))
\t\t\t(fill none)
\t\t\t(layer "F.Fab")
\t\t\t(uuid "{guide_uuid(f"oled:{fp.ref}:fab-outline")}")
\t\t)
\t\t(fp_rect
\t\t\t(start -26.05 -10.09)
\t\t\t(end 1.75 17.71)
\t\t\t(stroke (width 0.05) (type solid))
\t\t\t(fill none)
\t\t\t(layer "F.CrtYd")
\t\t\t(uuid "{guide_uuid(f"oled:{fp.ref}:courtyard")}")
\t\t)
\t\t(fp_text user "SSD1306 0.96in MODULE 27.3x27.3"
\t\t\t(at -12.15 3.81 90)
\t\t\t(layer "Dwgs.User")
\t\t\t(uuid "{guide_uuid(f"oled:{fp.ref}:label")}")
\t\t\t(effects (font (size 1.1 1.1) (thickness 0.16)))
\t\t)'''
        block = block[:insert] + graphics + block[insert:]
        replacements.append((fp.start, fp.end, block))

    if len(replacements) != 2:
        raise RuntimeError(f"expected J41 and J45, found {len(replacements)} OLED footprints")
    for start, end, block in reversed(replacements):
        text = text[:start] + block + text[end:]
    return text


def update_project_settings() -> None:
    data = json.loads(PRO.read_text())
    ds = data.setdefault("board", {}).setdefault("design_settings", {})
    rules = ds.setdefault("rules", {})
    rules.update(
        {
            "min_clearance": 0.09,
            "min_copper_edge_clearance": 0.5,
            "min_track_width": 0.09,
            "min_via_diameter": 0.45,
            "min_via_annular_width": 0.1,
            "min_hole_clearance": 0.25,
            "min_hole_to_hole": 0.25,
            "min_through_hole_diameter": 0.2,
        }
    )
    ds["track_widths"] = [0.0, 0.1, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    ds["via_dimensions"] = [
        {"diameter": 0.0, "drill": 0.0},
        {"diameter": 0.45, "drill": 0.2},
        {"diameter": 0.5, "drill": 0.25},
        {"diameter": 0.6, "drill": 0.3},
        {"diameter": 0.8, "drill": 0.4},
        {"diameter": 1.0, "drill": 0.5},
        {"diameter": 1.5, "drill": 0.75},
    ]
    ds["diff_pair_dimensions"] = [
        {"gap": 0.0, "via_gap": 0.0, "width": 0.0},
        {"gap": 0.15, "via_gap": 0.2, "width": 0.12},
        {"gap": 0.15, "via_gap": 0.2, "width": 0.15},
        {"gap": 0.25, "via_gap": 0.25, "width": 0.2},
    ]

    classes = data.setdefault("net_settings", {}).setdefault("classes", [])
    by_name = {cls.get("name"): cls for cls in classes}
    class_updates = {
        "Default": {"track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3, "clearance": 0.15},
        "USB2_90R": {"track_width": 0.15, "via_diameter": 0.45, "via_drill": 0.2, "diff_pair_width": 0.15, "diff_pair_gap": 0.15},
        "USB3_HDMI_100R": {"track_width": 0.12, "via_diameter": 0.45, "via_drill": 0.2, "diff_pair_width": 0.12, "diff_pair_gap": 0.15},
        "PCIe_85R": {"track_width": 0.12, "via_diameter": 0.45, "via_drill": 0.2, "diff_pair_width": 0.12, "diff_pair_gap": 0.15},
        "RF_50R": {"track_width": 0.25, "via_diameter": 0.5, "via_drill": 0.25, "clearance": 0.2},
        "POWER_5A": {"track_width": 1.5, "via_diameter": 0.8, "via_drill": 0.4, "clearance": 0.3},
        "POWER_10A_PACK": {"track_width": 3.0, "via_diameter": 1.0, "via_drill": 0.5, "clearance": 0.5},
    }
    for name, updates in class_updates.items():
        if name in by_name:
            by_name[name].update(updates)

    PRO.write_text(json.dumps(data, indent=2) + "\n")


FOOTPRINT_DIRS = [
    ROOT / "ducktop2.pretty",
    ROOT / "Module_LattePanda.pretty",
    Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
]


def footprint_library_file(footprint: str) -> Path | None:
    if ":" not in footprint:
        return None
    lib, name = footprint.split(":", 1)
    for root in FOOTPRINT_DIRS:
        if not root.exists():
            continue
        candidate = root / f"{lib}.pretty" / f"{name}.kicad_mod"
        if candidate.exists():
            return candidate
        candidate = root / f"{name}.kicad_mod"
        if root.name == f"{lib}.pretty" and candidate.exists():
            return candidate
    return None


def block_at(block: str) -> tuple[float, float, float]:
    m = re.search(r'\n\s*\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)', block)
    if not m:
        return (0.0, 0.0, 0.0)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3) or 0.0))


def transform_local(point: tuple[float, float], x: float, y: float, rot: float) -> tuple[float, float]:
    px, py = point
    angle = math.radians(rot)
    ca = math.cos(angle)
    sa = math.sin(angle)
    # KiCad board coordinates have +Y downward, so positive footprint rotation is
    # clockwise in mathematical coordinates.
    return (x + px * ca + py * sa, y - px * sa + py * ca)


def bbox_for(block: str, x: float, y: float, rot: float) -> tuple[float, float, float, float]:
    pts: list[tuple[float, float]] = []

    for start, end, pad in iter_blocks(block, "\n\t\t(pad "):
        at = re.search(r'\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?', pad)
        size = re.search(r'\(size\s+([-0-9.]+)\s+([-0-9.]+)', pad)
        if not at or not size:
            continue
        px = float(at.group(1))
        py = float(at.group(2))
        w = float(size.group(1))
        h = float(size.group(2))
        pts.extend([(px - w / 2, py - h / 2), (px + w / 2, py + h / 2)])

    for kind in ("fp_rect", "fp_line", "fp_circle", "fp_arc", "fp_poly"):
        marker = f"\n\t\t({kind}"
        for _, _, graphic in iter_blocks(block, marker):
            if "(layer \"F.Fab\")" not in graphic and "(layer \"B.Fab\")" not in graphic and "(layer \"F.CrtYd\")" not in graphic and "(layer \"B.CrtYd\")" not in graphic and "(layer \"F.SilkS\")" not in graphic and "(layer \"B.SilkS\")" not in graphic and "(layer \"Dwgs.User\")" not in graphic:
                continue
            for xy in re.finditer(r'\((?:start|end|center|mid|xy)\s+([-0-9.]+)\s+([-0-9.]+)', graphic):
                pts.append((float(xy.group(1)), float(xy.group(2))))

    if not pts:
        pts = [(-1.0, -1.0), (1.0, 1.0)]

    world = [transform_local(pt, x, y, rot) for pt in pts]
    xs = [pt[0] for pt in world]
    ys = [pt[1] for pt in world]
    return (min(xs), min(ys), max(xs), max(ys))


def expand_bbox(bbox: tuple[float, float, float, float], margin: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 - margin, y1 - margin, x2 + margin, y2 + margin)


def intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def fits_board(bbox: tuple[float, float, float, float]) -> bool:
    if bbox[0] < 0.5 or bbox[1] < 0.5 or bbox[2] > 389.5 or bbox[3] > 249.5:
        return False
    return not any(intersects(bbox, cutout) for cutout in CUTOUTS)


def zone_blocks(block: str) -> list[tuple[int, int, str]]:
    zones: list[tuple[int, int, str]] = []
    idx = 0
    while True:
        m = re.search(r'\n\t+\(zone\b', block[idx:])
        if not m:
            return zones
        start = idx + m.start() + 1
        end = balanced_end(block, start)
        zones.append((start, end, block[start:end]))
        idx = end


def local_zone_blocks(footprint: str) -> list[str]:
    path = footprint_library_file(footprint)
    if path is None:
        return []
    text = path.read_text(errors="ignore")
    return [block for _, _, block in zone_blocks(text)]


def pad_name(pad: str) -> str:
    m = re.match(r'\s*\(pad\s+("[^"]*"|[^\s\)]+)', pad)
    if not m:
        return ""
    raw = m.group(1)
    return raw[1:-1] if raw.startswith('"') else raw


def pad_blocks(block: str) -> list[tuple[int, int, str]]:
    return iter_blocks(block, "\n\t\t(pad ")


def local_pad_blocks(footprint: str) -> dict[str, list[str]]:
    path = footprint_library_file(footprint)
    if path is None:
        return {}
    text = path.read_text(errors="ignore")
    pads: dict[str, list[str]] = {}
    for _, _, pad in iter_blocks(text, "\n\t(pad "):
        name = pad_name(pad)
        if name:
            pads.setdefault(name, []).append(pad)
    return pads


def normalize_child_indent(block: str, desired_tabs: int = 2) -> str:
    desired = "\t" * desired_tabs
    lines = block.splitlines()
    out = []
    for line in lines:
        stripped_tabs = len(line) - len(line.lstrip("\t"))
        if stripped_tabs:
            out.append(desired + line[stripped_tabs:])
        else:
            out.append(desired + line)
    return "\n".join(out)


def s_expr_line(block: str, key: str) -> str | None:
    m = re.search(r'\n\s*\(' + re.escape(key) + r'\b[^\n]*\)', block)
    return m.group(0).strip() if m else None


def set_or_insert_line(block: str, key: str, line: str) -> str:
    pattern = r'\n\s*\(' + re.escape(key) + r'\b[^\n]*\)'
    replacement = "\n\t\t\t" + line
    if re.search(pattern, block):
        return re.sub(pattern, replacement, block, count=1)
    close = block.rfind("\n\t\t)")
    if close < 0:
        close = block.rfind(")")
    return block[:close] + replacement + block[close:]


def refresh_pads_from_library(block: str, footprint: str) -> str:
    library_pads = local_pad_blocks(footprint)
    if not library_pads:
        return block
    seen: dict[str, int] = {}
    replacements: list[tuple[int, int, str]] = []

    for start, end, old_pad in pad_blocks(block):
        name = pad_name(old_pad)
        occurrence = seen.get(name, 0)
        seen[name] = occurrence + 1
        lib_occurrences = library_pads.get(name)
        if not lib_occurrences or occurrence >= len(lib_occurrences):
            continue
        lib_pad = lib_occurrences[occurrence]
        new_pad = normalize_child_indent(lib_pad, desired_tabs=2)
        for key in ("net", "pinfunction", "pintype"):
            line = s_expr_line(old_pad, key)
            if line:
                new_pad = set_or_insert_line(new_pad, key, line)
        old_uuid = s_expr_line(old_pad, "uuid")
        if old_uuid:
            new_pad = set_or_insert_line(new_pad, "uuid", old_uuid)
        replacements.append((start, end, new_pad))

    new_block = block
    for start, end, new_pad in reversed(replacements):
        new_block = new_block[:start] + new_pad + new_block[end:]
    return new_block


def apply_pad_shape_rotation(block: str, rot: float) -> str:
    """Write pad-local angles needed when a footprint is rotated on the PCB.

    KiCad stores pad locations in footprint-local coordinates, but DRC treats a
    rectangular pad's own angle from the pad's `(at ... angle)` field. If a
    side-facing footprint is rotated without also rotating its rectangular pads,
    adjacent fine-pitch pads can overlap electrically even though their centers
    move to the right places.
    """
    if abs(rot % 360) < 0.0005:
        return block

    def rotate_pad(pad: str) -> str:
        def repl(at_match: re.Match[str]) -> str:
            old_angle = float(at_match.group(3) or 0.0)
            angle = (old_angle + rot) % 360
            if abs(angle) < 0.0005:
                return f"(at {at_match.group(1)} {at_match.group(2)})"
            return f"(at {at_match.group(1)} {at_match.group(2)} {format_num(angle)})"

        return re.sub(
            r'\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)',
            repl,
            pad,
            count=1,
        )

    pieces = []
    last = 0
    for start, end, pad in pad_blocks(block):
        pieces.append(block[last:start])
        pieces.append(rotate_pad(pad))
        last = end
    if not pieces:
        return block
    pieces.append(block[last:])
    return "".join(pieces)


def transformed_zone_block(zone: str, ref: str, index: int, x: float, y: float, rot: float) -> str:
    zone = re.sub(
        r'\(xy\s+([-0-9.]+)\s+([-0-9.]+)\)',
        lambda m: '(xy {} {})'.format(
            format_num(transform_local((float(m.group(1)), float(m.group(2))), x, y, rot)[0]),
            format_num(transform_local((float(m.group(1)), float(m.group(2))), x, y, rot)[1]),
        ),
        zone,
    )
    zone = re.sub(r'\(uuid\s+"[^"]+"\)', f'(uuid "{guide_uuid(f"embedded-zone:{ref}:{index}")}")', zone, count=1)
    lines = zone.splitlines()
    # Library footprint zones are indented one tab. Board footprint children are indented two tabs.
    lines = [line.replace("\t", "\t\t", 1) if line.startswith("\t") else "\t" + line for line in lines]
    return "\n".join(lines)


def refresh_embedded_zones(block: str, ref: str, footprint: str, x: float, y: float, rot: float) -> str:
    existing = zone_blocks(block)
    if not existing:
        return block
    local_zones = local_zone_blocks(footprint)
    if not local_zones:
        return block
    new_zones = [
        transformed_zone_block(zone, ref, idx, x, y, rot)
        for idx, zone in enumerate(local_zones)
    ]
    new_block = block
    for (start, end, _), zone in zip(reversed(existing), reversed(new_zones)):
        new_block = new_block[:start] + zone + new_block[end:]
    return new_block


def set_footprint_full(block: str, ref: str, footprint: str, x: float, y: float, rot: float | None = None) -> str:
    rot = 0.0 if rot is None else rot % 360
    block = refresh_pads_from_library(block, footprint)
    block = apply_pad_shape_rotation(block, rot)
    block = set_footprint_at(block, x, y, rot)
    return refresh_embedded_zones(block, ref, footprint, x, y, rot)


SAFE_ANCHORS: dict[str, tuple[float, float, float | None]] = {
    # Side-facing ports. USB-C footprint's local "PCB Edge" is +Y, so left
    # edge ports face out with 270 degrees and right edge ports with 90 degrees.
    "J21": (4.525, 32, 270),
    "J22": (4.525, 50, 270),
    "J23": (4.525, 68, 270),
    "J11": (385.475, 32, 90),
    "J12": (385.475, 50, 90),
    "J30": (382.975, 78, 0),
    "J190": (8, 92, 270),
    # Internal monitor and user-input cable interfaces.
    "J300": (164, 94, 0),
    "J301": (188, 96, 0),
    "J302": (218, 90, 0),
    "J303": (218, 106, 0),
    "J58": (197.5, 127.5, 0),
    "J310": (334, 89, 0),
    # Major compute/storage/mechanical anchors.
    "A1": (305, 185, 0),
    "J10": (204, 151, 90),
    "U4": (224, 142, 0),
    "U9": (244, 174, 0),
    # Service / human-facing headers.
    "J41": (268, 24, 0),
    "U45": (296, 36, 0),
    "C185": (296, 45, 0),
    "J45": (306.96, 15, 90),
    "J52": (336, 136, 0),
    "J53": (168, 126, 0),
    "J54": (180, 126, 0),
    "J56": (252, 176, 0),
    "J57": (184, 140, 0),
    # Radio/GNSS/mechanical RF I/O.
    "J40": (100, 146, 0),
    "J42": (114, 120, 0),
    "J43": (36, 112, 0),
    "J44": (48, 112, 0),
    "J70": (70, 126, 0),
    "J71": (70, 158, 0),
    "J72": (124, 120, 0),
    "J240": (6, 122, 0),
    "J241": (6, 140, 0),
    "J250": (6, 158, 0),
    "J251": (6, 176, 0),
    # Maker/tinker headers.
    "J901": (337.5, 34.1, 0),
    "J902": (349.072157, 44.407419, 0),
    "SW900": (348.131982, 36.041993, 0),
    "SW901": (348.139376, 28.423485, 0),
    # Small front/audio anchor.
    "J330": (250, 214, 0),
}

# Keep the initial-layout helper aligned with the surgical netlist sync helper.
# This deliberately contains no J900 module anchor.
SAFE_ANCHORS.update(MAKER_ANCHORS_MM)


SAFE_ZONE_TARGETS = {
    "01_power_battery.kicad_sch": (70, 102),
    "02_ec_mcu.kicad_sch": (218, 140),
    "03_mu_carrier.kicad_sch": (244, 184),
    "04_usb_c_io.kicad_sch": (342, 48),
    "05_power_inputs.kicad_sch": (72, 92),
    "06_tcp0_external_hdmi.kicad_sch": (342, 84),
    "07_radio_oled_gps.kicad_sch": (76, 128),
    "08_internal_services.kicad_sch": (218, 132),
    "09_ham_radio.kicad_sch": (72, 150),
    "11_intehill_monitor_interface.kicad_sch": (178, 102),
    "12_keyboard_interface.kicad_sch": (334, 96),
    "13_radio_audio_codec.kicad_sch": (244, 214),
    "14_maker_mcu.kicad_sch": (350, 72),
}


def candidate_points(target: tuple[float, float]) -> list[tuple[float, float]]:
    tx, ty = target
    points = []
    step = 3.0
    # Keep everything on a coarse but editable grid.
    y = 9.0
    while y <= 244.0:
        x = 9.0
        while x <= 381.0:
            if not in_cutout(x, y, clearance=1.0):
                points.append((x, y))
            x += step
        y += step
    points.sort(key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)
    return points


def place_footprints(text: str) -> str:
    fps = footprints(text)
    if any(re.match(r"SW3[2-9][0-9]$", fp.ref) or re.match(r"D3[2-9][0-9]$", fp.ref) or fp.ref == "J320" for fp in fps):
        raise RuntimeError("keyboard daughterboard footprints are present in main PCB; aborting placement")

    by_ref = {fp.ref: fp for fp in fps}
    updates: dict[str, tuple[float, float, float | None]] = {}
    obstacles: list[tuple[float, float, float, float]] = []

    def add_update(fp: Footprint, x: float, y: float, rot: float | None, margin: float = 0.8) -> None:
        r = 0.0 if rot is None else rot
        updates[fp.ref] = (x, y, r)
        obstacles.append(expand_bbox(bbox_for(fp.text, x, y, r), margin))

    for ref, placement in SAFE_ANCHORS.items():
        fp = by_ref.get(ref)
        if fp is not None:
            add_update(fp, *placement, margin=1.0)

    unplaced = [fp for fp in fps if fp.ref not in updates]
    # Place larger footprints first so headers and ICs do not get boxed out by passives.
    unplaced.sort(
        key=lambda fp: (
            fp.sheetfile,
            -((bbox_for(fp.text, 0, 0, 0)[2] - bbox_for(fp.text, 0, 0, 0)[0]) * (bbox_for(fp.text, 0, 0, 0)[3] - bbox_for(fp.text, 0, 0, 0)[1])),
            natural_key(fp.ref),
        )
    )

    cached_candidates: dict[tuple[float, float], list[tuple[float, float]]] = {}
    for fp in unplaced:
        target = SAFE_ZONE_TARGETS.get(fp.sheetfile, (195, 125))
        candidates = cached_candidates.setdefault(target, candidate_points(target))
        placed = False
        for x, y in candidates:
            rot = 0.0
            bbox = expand_bbox(bbox_for(fp.text, x, y, rot), 0.35)
            if not fits_board(bbox):
                continue
            if any(intersects(bbox, other) for other in obstacles):
                continue
            add_update(fp, x, y, rot, margin=0.35)
            placed = True
            break
        if not placed:
            raise RuntimeError(f"could not find safe staging spot for {fp.ref} ({fp.sheetfile})")

    new_text = text
    for fp in reversed(fps):
        if fp.ref not in updates:
            continue
        x, y, rot = updates[fp.ref]
        new_block = set_footprint_full(fp.text, fp.ref, fp.footprint, x, y, rot)
        new_text = new_text[:fp.start] + new_block + new_text[fp.end:]
    return new_text


def main() -> None:
    text = PCB.read_text()
    text = replace_layers(text)
    text = place_footprints(text)
    text = demote_footprint_edge_cuts(text)
    text = add_oled_module_envelopes(text)
    text = add_guides(text)
    PCB.write_text(text)
    update_project_settings()
    print("Prepared ducktop2 main PCB: 6 copper layers, routing presets, mechanical guides, rough placement.")


if __name__ == "__main__":
    main()
