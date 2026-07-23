#!/usr/bin/env python3
"""Narrow, auditable main-PCB sync from the exported KiCad XML netlist.

KiCad 10's CLI can export/check, but it does not expose the GUI
"Update PCB from Schematic" operation.  The pcbnew Python bindings are also
fragile in headless use on macOS, so this helper makes deterministic
S-expression edits instead.

It performs only the safe subset needed here:

* update footprint path/value/sheet metadata by reference
* update pad nets from the schematic netlist
* replace only explicitly allowed changed footprints
* add only explicitly allowed new footprints
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "ducktop2.kicad_pcb"
SCH = ROOT / "ducktop2.kicad_sch"
NETLIST = ROOT / "verification" / "ducktop2_netlist.xml"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

FOOTPRINT_DIRS = [
    ROOT / "ducktop2.pretty",
    ROOT / "Module_LattePanda.pretty",
    Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
]

CURRENT_ECO_ADD_ONLY = {
    # July 23 USB_PORT_5V over-voltage fix and U771 always-powered supervisor.
    "R777", "R778",
}
CURRENT_ECO_REPLACE_ONLY = {"U771"}
# These parts were added by the current ECO, then corrected from 0603 to 0805
# after the BQ77915 internal-balancing filter requirement was rechecked.
POST_ADD_FOOTPRINT_REFRESH = set()

ALLOWED_ADD_OR_REPLACE = CURRENT_ECO_REPLACE_ONLY | POST_ADD_FOOTPRINT_REFRESH
ALLOWED_ADD_ONLY = CURRENT_ECO_ADD_ONLY
ALLOWED_REMOVE_ONLY: set[str] = set()
FORCE_REPLACE = set(CURRENT_ECO_REPLACE_ONLY)
REPOSITION_EXISTING: set[str] = set()

ANCHORS_MM = {
    # Reset-qualified service mux logic.  Keep the gate, request pull-up and
    # bypass together; the reset output then runs directly to nearby U45.
    "U46": (236.0, 31.0, 0.0),
    "C781": (241.5, 31.0, 0.0),
    "R172": (236.0, 35.0, 0.0),

    # C502/C503 are the only Ethernet coupling capacitors with approved anchors.
    # C500/C501 must be re-placed beside the on-board U500 PCIe device per the
    # Mu guide; the current placement is a release hold and has no approved anchor.
    "C502": (314.5, 105.0, 0.0),
    "C503": (314.5, 103.8, 0.0),

    "U45": (296.0, 33.0, 0.0),
    "C185": (296.0, 42.0, 0.0),
    # Integrated RP2350 maker controller. This cluster replaces the former
    # 21 x 51 mm Pico module envelope; J901/J902 and their routing stay put.
    "F900": (356.0, 8.0, 0.0),
    "C921": (360.5, 8.0, 0.0),
    "C900": (362.5, 11.0, 0.0),
    "U903": (367.0, 8.0, 0.0),
    "L900": (371.0, 8.0, 0.0),
    "C901": (375.0, 8.0, 0.0),
    "R902": (378.0, 8.0, 0.0),
    "R903": (378.0, 10.0, 0.0),

    "U902": (359.5, 20.0, 0.0),
    "C902": (362.5, 16.0, 0.0),
    "C903": (363.0, 18.0, 0.0),
    "R904": (363.0, 20.5, 0.0),
    "R905": (354.5, 28.4, 0.0),

    "U901": (369.0, 28.0, 0.0),
    "L901": (369.0, 19.0, 0.0),
    "C911": (365.0, 19.0, 0.0),
    "C912": (373.0, 19.0, 0.0),
    "R907": (376.0, 19.0, 0.0),
    "C913": (378.5, 19.0, 0.0),
    "C904": (363.5, 24.0, 0.0),
    "C905": (366.0, 22.0, 0.0),
    "C906": (369.0, 22.5, 0.0),
    "C907": (372.0, 22.0, 0.0),
    "C908": (374.5, 24.0, 0.0),
    "C909": (363.5, 32.0, 0.0),
    "C910": (366.0, 34.0, 0.0),
    "C914": (369.0, 33.5, 0.0),
    "C915": (372.0, 34.0, 0.0),
    "C916": (374.5, 32.0, 0.0),
    "R908": (377.0, 30.0, 0.0),
    "R909": (379.0, 30.0, 0.0),
    "C922": (374.5, 36.0, 0.0),
    "C917": (378.0, 33.0, 0.0),

    "Y900": (371.0, 38.0, 0.0),
    "R906": (375.0, 38.0, 0.0),
    "C918": (369.0, 40.5, 0.0),
    "C919": (373.0, 40.5, 0.0),
    "U900": (378.0, 24.5, 0.0),
    "R900": (377.0, 27.0, 0.0),
    "R901": (379.0, 27.0, 0.0),
    "R910": (377.0, 36.0, 0.0),
    "R911": (379.0, 36.0, 0.0),

    "R912": (358.0, 35.0, 0.0),
    "R913": (360.5, 35.0, 0.0),
    "C920": (358.0, 37.5, 0.0),
    "Q900": (361.0, 39.0, 0.0),
    "R914": (358.0, 41.0, 0.0),
    "R915": (358.0, 44.0, 0.0),
    "D900": (361.0, 44.0, 0.0),
    "R916": (354.5, 36.0, 0.0),
    "R918": (354.5, 43.5, 0.0),
    "R919": (354.5, 45.5, 0.0),
}

# Final post-audit ECO anchors.  These are placement-stage functional clusters,
# not routed-layout approval.  Every new footprint is kept inside Edge.Cuts and
# close to the circuit it protects so the board can be reviewed and routed from
# a coherent starting point.
ANCHORS_MM.update({
    # July 19 audit remediation.  Keep the LTC4368 VOUT capacitor and QON
    # open-drain network local to the charger/protector cluster.  The two
    # button-isolation diodes sit beside that network, while the USB service
    # test points continue the existing rear pogo row below U770.
    "C725": (53.2, 148.8, 0.0),
    "Q702": (330.0, 134.0, 0.0),
    "D715": (334.0, 132.0, 0.0),
    "D716": (334.0, 136.0, 0.0),
    "R13": (330.0, 138.0, 0.0),
    "TP13": (166.0, 10.0, 0.0),
    "TP14": (172.0, 10.0, 0.0),
    "TP15": (166.0, 16.0, 0.0),

    # BQ25798 ship FET, between the charger and protected-pack power devices.
    "Q25": (95.0, 75.0, 0.0),

    # Shared always-on OR eFuse immediately after D710-D714.
    "U718": (238.0, 52.0, 0.0),
    "R795": (244.0, 49.0, 0.0),
    "R796": (247.0, 49.0, 0.0),
    "R797": (250.0, 49.0, 0.0),
    "R798": (253.0, 49.0, 0.0),
    "C795": (244.0, 54.0, 0.0),
    "C796": (249.0, 54.0, 0.0),
    "C797": (254.0, 54.0, 0.0),
    "C798": (259.0, 54.0, 0.0),
    "C799": (264.0, 54.0, 0.0),

    # First-article rail/fault pogo row in the open rear service area.
    "TP1": (118.0, 10.0, 0.0),
    "TP2": (124.0, 10.0, 0.0),
    "TP3": (130.0, 10.0, 0.0),
    "TP4": (136.0, 10.0, 0.0),
    "TP7": (142.0, 10.0, 0.0),
    "TP9": (148.0, 10.0, 0.0),
    "TP10": (154.0, 10.0, 0.0),
    "TP11": (160.0, 10.0, 0.0),

    # Carrier-generated physical host VBUS and switched PCIe endpoint power.
    "C794": (193.0, 89.0, 0.0),
    "U770": (198.0, 90.0, 0.0),
    "R773": (202.0, 88.0, 0.0),
    "C830": (193.0, 96.0, 0.0),
    "R774": (202.0, 94.0, 0.0),
    "U771": (207.0, 90.0, 0.0),
    "R775": (210.5, 88.0, 0.0),
    "C831": (207.0, 95.0, 0.0),
    "R777": (204.0, 92.0, 0.0),
    "R778": (204.0, 95.0, 0.0),
    "C832": (214.0, 88.0, 0.0),
    "U772": (217.0, 93.0, 0.0),
    "R776": (221.0, 88.0, 0.0),
    "C833": (222.0, 93.0, 0.0),
    "C834": (226.0, 88.0, 0.0),
    "C835": (226.0, 93.0, 0.0),
    "C836": (231.0, 88.0, 0.0),
    "C837": (231.0, 93.0, 0.0),
    "TP5": (195.0, 102.0, 0.0),
    "TP6": (203.0, 102.0, 0.0),
    "TP8": (211.0, 102.0, 0.0),
    "TP12": (219.0, 102.0, 0.0),

    # Maker-header isolators and their local bypassing in the open center-rear
    # area.  Connector-side ESD remains closest to the J901 routing corridor.
    "U910": (176.0, 64.0, 0.0),
    "U911": (187.0, 64.0, 0.0),
    "U912": (198.0, 64.0, 0.0),
    "U913": (209.0, 64.0, 0.0),
    "C930": (176.0, 70.0, 0.0),
    "C931": (187.0, 70.0, 0.0),
    "C932": (198.0, 70.0, 0.0),
    "C933": (209.0, 70.0, 0.0),
    "U922": (220.0, 64.0, 0.0),
    "R931": (224.0, 61.0, 0.0),
    "Q903": (229.0, 64.0, 0.0),
    "R930": (233.0, 61.0, 0.0),
    "C934": (224.0, 68.0, 0.0),

    # System-audio physical VBUS-valid link beside the internal USB audio hub.
    "R417": (97.5, 175.0, 0.0),

    # Replaced physical connectors keep their existing functional locations.
    "J9": (169.5, 132.0, 0.0),
    "J52": (61.0, 120.0, 180.0),
    "J53": (270.0, 119.5, 0.0),
    "J54": (95.0, 10.0, 0.0),
    "J56": (261.5, 119.5, 0.0),
    "J420": (18.0, 180.0, 0.0),
    "J421": (340.0, 180.0, 0.0),
    # Keyed maker I/O connector in the rear service area.  This avoids both
    # full-size SSD1306 module courtyards and remains reachable under a hatch.
    "J901": (190.0, 10.0, 0.0),
})

ANCHORS_MM.update({
    # Autonomous 3S protection.  This open strip is part of the power side of
    # the motherboard and keeps the protector, cell filters, shunt, and
    # back-to-back FETs together without putting parts under the Mu courtyard.
    "U719": (38.0, 83.0, 90.0),
    "R840": (24.0, 74.5, 0.0),
    "C840": (28.0, 74.5, 0.0),
    "C841": (32.0, 74.5, 0.0),
    "R841": (36.0, 74.5, 0.0),
    "R842": (40.0, 74.5, 0.0),
    "R843": (44.0, 74.5, 0.0),
    "R844": (48.0, 74.5, 0.0),
    "C842": (52.0, 74.5, 0.0),
    "C843": (56.0, 74.5, 0.0),
    "C844": (60.0, 74.5, 0.0),
    "C848": (64.0, 74.5, 0.0),
    "R845": (24.0, 79.0, 0.0),
    "R846": (28.0, 79.0, 0.0),
    "C845": (32.0, 79.0, 0.0),
    "C846": (46.0, 79.0, 0.0),
    "C847": (50.0, 79.0, 0.0),
    "R851": (54.0, 79.0, 0.0),
    "R852": (58.0, 79.0, 0.0),
    "R853": (62.0, 79.0, 0.0),
    "R854": (66.0, 79.0, 0.0),
    "R847": (24.0, 88.5, 0.0),
    "R848": (28.0, 88.5, 0.0),
    "R849": (32.0, 88.5, 0.0),
    "R850": (46.0, 88.5, 0.0),
    "RS11": (54.0, 88.5, 0.0),
    "Q703": (63.0, 87.5, 0.0),
    "Q704": (72.0, 87.5, 0.0),
    # BQ34Z100 external-temperature disable strap belongs at the gauge.
    "R855": (80.0, 87.5, 0.0),

    # HDMI host-active power gating beside the existing HDMI logic.
    "U54": (305.0, 77.5, 0.0),
    "C164": (309.0, 76.5, 0.0),
    "R168": (309.0, 78.2, 0.0),
    "U55": (305.0, 83.0, 0.0),
    "C165": (309.0, 82.0, 0.0),
    "R169": (309.0, 83.7, 0.0),

    # M.2 E-key reset-safe control isolation beside J40.
    "U170": (266.0, 142.0, 0.0),
    "C187": (266.0, 146.5, 0.0),
    "R198": (270.0, 142.0, 0.0),
    "R199": (270.0, 145.0, 0.0),

    # Fan tach input filter beside the existing fan-control passives.
    "C209": (270.0, 133.5, 0.0),

    # Radio reset-safe latches retain their existing locations.  Their former
    # optional capacitors are removed and replaced by the required pull-downs.
    "FL240": (229.5, 134.5, 0.0),
    "U241": (158.0, 24.0, 0.0),
    "U251": (154.0, 34.0, 0.0),
    "R230": (154.0, 25.0, 0.0),
    "R232": (150.0, 35.0, 0.0),
    "U260": (170.0, 24.0, 0.0),
    "C260": (175.0, 24.0, 0.0),
    "U261": (181.0, 24.0, 0.0),
    "C261": (186.0, 24.0, 0.0),
})

for index, ref_number in enumerate(range(932, 962)):
    ANCHORS_MM[f"R{ref_number}"] = (
        176.0 + (index % 10) * 4.2,
        76.0 + (index // 10) * 3.0,
        0.0,
    )

for index, ref_number in enumerate(range(914, 922)):
    ANCHORS_MM[f"U{ref_number}"] = (
        218.0 + (index % 4) * 5.0,
        76.0 + (index // 4) * 5.0,
        0.0,
    )

# This ECO is small enough to give every new part an audited in-board anchor.
# Refuse to add a footprint at a generic fallback location.
if not CURRENT_ECO_ADD_ONLY <= ANCHORS_MM.keys():
    raise RuntimeError("every added ECO footprint needs an audited board anchor")

UUID_NS = uuid.UUID("1f06b11b-1880-4840-a8c4-d508ec9c7994")


@dataclass
class Component:
    ref: str
    value: str
    footprint: str
    properties: dict[str, str]
    sheetname: str
    sheetfile: str
    path: str
    pin_nets: dict[str, str]


@dataclass
class BoardFootprint:
    start: int
    end: int
    text: str
    ref: str
    footprint: str


def q(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def stable_uuid(key: str) -> str:
    return str(uuid.uuid5(UUID_NS, key))


def fmt(x: float) -> str:
    if abs(x - round(x)) < 0.0005:
        return str(int(round(x)))
    return f"{x:.3f}".rstrip("0").rstrip(".")


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
    out: list[tuple[int, int, str]] = []
    idx = 0
    while True:
        i = text.find(marker, idx)
        if i < 0:
            return out
        start = i + (1 if marker.startswith("\n") else 0)
        end = balanced_end(text, start)
        out.append((start, end, text[start:end]))
        idx = end


def extract(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else default


def export_netlist() -> None:
    NETLIST.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(KICAD_CLI),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(NETLIST),
            str(SCH),
        ],
        check=True,
        cwd=ROOT,
    )


def encode_sheet_local_net(net_name: str, sheetname: str) -> str:
    if not sheetname or not net_name.startswith(sheetname):
        return net_name
    encoded_sheet = "/" + sheetname.strip("/").replace("/", "{slash}") + "/"
    return encoded_sheet + net_name[len(sheetname):]


def parse_netlist() -> dict[str, Component]:
    root = ET.parse(NETLIST).getroot()
    components: dict[str, Component] = {}
    sheet_by_ref: dict[str, str] = {}

    for comp in root.findall(".//comp"):
        ref = comp.get("ref") or ""
        sheetpath = comp.find("sheetpath")
        # KiCad writes standard symbol fields (notably Datasheet) under
        # <fields>, while custom fields live under <property>.  Preserve both
        # so a schematic-to-PCB ECO cannot leave stale library metadata behind.
        props = {
            field.get("name"): field.text or ""
            for field in comp.findall("./fields/field")
        }
        props.update({p.get("name"): p.get("value") for p in comp.findall("property")})
        sheetname = sheetpath.get("names", "") if sheetpath is not None else ""
        sheet_tstamps = sheetpath.get("tstamps", "") if sheetpath is not None else ""
        symbol_tstamp = comp.findtext("tstamps") or ""
        components[ref] = Component(
            ref=ref,
            value=comp.findtext("value") or "",
            footprint=comp.findtext("footprint") or "",
            properties={k: v or "" for k, v in props.items() if k},
            sheetname=sheetname,
            sheetfile=props.get("Sheetfile") or "",
            path=sheet_tstamps + symbol_tstamp,
            pin_nets={},
        )
        sheet_by_ref[ref] = sheetname

    for net in root.findall(".//net"):
        net_name = net.get("name") or ""
        for node in net.findall("node"):
            ref = node.get("ref") or ""
            pin = node.get("pin") or ""
            comp = components.get(ref)
            if not comp or not pin:
                continue
            comp.pin_nets[pin] = encode_sheet_local_net(net_name, sheet_by_ref.get(ref, ""))

    return components


def footprints(text: str) -> list[BoardFootprint]:
    out: list[BoardFootprint] = []
    for start, end, block in iter_blocks(text, "\n\t(footprint "):
        out.append(
            BoardFootprint(
                start=start,
                end=end,
                text=block,
                ref=extract(r'\(property\s+"Reference"\s+"([^"]+)"', block),
                footprint=extract(r'^\s*\(footprint\s+"([^"]+)"', block),
            )
        )
    return out


def footprint_library_file(footprint: str) -> Path:
    if ":" not in footprint:
        raise ValueError(f"footprint '{footprint}' is not library-qualified")
    lib, name = footprint.split(":", 1)
    for root in FOOTPRINT_DIRS:
        if root.name == f"{lib}.pretty":
            candidate = root / f"{name}.kicad_mod"
            if candidate.exists():
                return candidate
        candidate = root / f"{lib}.pretty" / f"{name}.kicad_mod"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"cannot find footprint {footprint}")


def at_tuple(block: str) -> tuple[float, float, float]:
    m = re.search(r'\n\s*\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)', block)
    if not m:
        return (30.0, 30.0, 0.0)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3) or 0.0))


def top_level_child_span(block: str, key: str) -> tuple[int, int] | None:
    """Find a direct child S-expression without assuming tab indentation."""
    depth = 0
    in_string = False
    escape = False
    index = 0
    while index < len(block):
        char = block[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "(":
                if depth == 1:
                    token = block[index + 1 : index + 1 + len(key)]
                    following = block[index + 1 + len(key) : index + 2 + len(key)]
                    if token == key and (not following or following.isspace() or following == ")"):
                        return (index, balanced_end(block, index))
                depth += 1
            elif char == ")":
                depth -= 1
        index += 1
    return None


def top_level_child_spans(block: str, key: str) -> list[tuple[int, int]]:
    """Find every direct child S-expression named ``key``."""
    spans: list[tuple[int, int]] = []
    depth = 0
    in_string = False
    escape = False
    index = 0
    while index < len(block):
        char = block[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "(":
                if depth == 1:
                    token = block[index + 1 : index + 1 + len(key)]
                    following = block[index + 1 + len(key) : index + 2 + len(key)]
                    if token == key and (not following or following.isspace() or following == ")"):
                        end = balanced_end(block, index)
                        spans.append((index, end))
                        index = end
                        continue
                depth += 1
            elif char == ")":
                depth -= 1
        index += 1
    return spans


def set_or_insert_top_line(block: str, key: str, line: str) -> str:
    span = top_level_child_span(block, key)
    if span is not None:
        start, end = span
        # The span begins at the opening parenthesis; existing indentation is
        # immediately before it and must not be duplicated on every refresh.
        return block[:start] + line + block[end:]

    # Identity and placement must precede pads.  Some KiCad parsers apply a
    # late footprint transform to already-read custom pads when ``at`` is
    # emitted at the end of the block, effectively rotating them twice.
    header_end = block.find("\n")
    if header_end < 0:
        raise ValueError("footprint block has no header line")
    replacement = "\t\t" + line
    return block[: header_end + 1] + replacement + "\n" + block[header_end + 1 :]


def replace_property(block: str, prop: str, value: str) -> str:
    pattern = r'(\(property\s+"' + re.escape(prop) + r'"\s+)"[^"]*"'
    if re.search(pattern, block):
        return re.sub(pattern, r'\1"' + q(value) + '"', block, count=1)
    insert = block.find("\n\t\t(attr")
    if insert < 0:
        insert = block.find("\n\t\t(fp_")
    if insert < 0:
        insert = block.rfind("\n\t)")
    property_block = (
        f'\n\t\t(property "{q(prop)}" "{q(value)}"\n'
        f'\t\t\t(at 0 0 0)\n'
        f'\t\t\t(layer "F.Fab")\n'
        f'\t\t\t(hide yes)\n'
        f'\t\t\t(uuid "{stable_uuid(f"property:{prop}:{value}")}")\n'
        f'\t\t\t(effects (font (size 1 1) (thickness 0.15)))\n'
        f'\t\t)'
    )
    return block[:insert] + property_block + block[insert:]


def footprint_attribute_flags(block: str) -> set[str]:
    span = top_level_child_span(block, "attr")
    if span is None:
        return set()
    start, end = span
    match = re.fullmatch(r'\s*\(attr(?:\s+([^)]*?))?\)\s*', block[start:end])
    if match is None:
        raise ValueError("cannot parse footprint attr line")
    return set((match.group(1) or "").split())


def update_attribute_flags(block: str, comp: Component) -> str:
    """Mirror schematic BOM/DNP state without disturbing geometry attributes."""
    flags = footprint_attribute_flags(block)
    for name in ("exclude_from_bom", "dnp"):
        if name in comp.properties:
            flags.add(name)
        else:
            flags.discard(name)

    preferred = ("smd", "through_hole", "board_only", "exclude_from_pos_files")
    ordered = [name for name in preferred if name in flags]
    ordered.extend(sorted(flags - set(preferred) - {"exclude_from_bom", "dnp"}))
    ordered.extend(name for name in ("exclude_from_bom", "dnp") if name in flags)
    return set_or_insert_top_line(block, "attr", f"(attr {' '.join(ordered)})")


def pad_name(pad: str) -> str:
    m = re.search(r'\(pad\s+("[^"]*"|[^\s\)]+)', pad)
    if not m:
        return ""
    raw = m.group(1)
    return raw[1:-1] if raw.startswith('"') else raw


def pad_blocks(block: str) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    idx = 0
    while True:
        # Project-local footprints are valid KiCad S-expressions but some use
        # spaces while stock libraries use tabs.  Treat either as indentation;
        # silently skipping space-indented pads would leave them without nets.
        m = re.search(r'\n[ \t]+\(pad\s+', block[idx:])
        if not m:
            return blocks
        start = idx + m.start() + 1
        end = balanced_end(block, start)
        blocks.append((start, end, block[start:end]))
        idx = end


def set_pad_net(pad: str, name: str) -> str:
    first = pad.splitlines()[0]
    indent = first[: len(first) - len(first.lstrip("\t"))] + "\t"
    line = f'(net "{q(name)}")'
    pattern = r'\n\s*\(net(?:\s+\d+)?\s+"[^"]*"\)'
    if re.search(pattern, pad):
        return re.sub(pattern, "\n" + indent + line, pad, count=1)
    close = pad.rfind("\n" + first[: len(first) - len(first.lstrip("\t"))] + ")")
    if close < 0:
        close = pad.rfind(")")
    return pad[:close] + "\n" + indent + line + pad[close:]


def clear_pad_net(pad: str) -> str:
    """Leave intentional no-connect pads electrically netless on the PCB."""
    return re.sub(r'\n\s*\(net(?:\s+\d+)?\s+"[^"]*"\)', "", pad, count=1)


def update_pad_nets(block: str, comp: Component) -> tuple[str, int]:
    updates = 0
    new_block = block
    for start, end, pad in reversed(pad_blocks(block)):
        # NPTH pads are mechanical holes, even when a library gives a
        # concentric electrical pad the same number.  Assigning the symbol net
        # to the NPTH causes KiCad to clear its number on load while retaining
        # a stale net, creating a permanent schematic-parity mismatch.
        if re.search(r'^\s*\(pad\s+(?:"[^"]*"|[^\s\)]+)\s+np_thru_hole\b', pad):
            new_pad = clear_pad_net(pad)
            if new_pad != pad:
                updates += 1
            new_block = new_block[:start] + new_pad + new_block[end:]
            continue
        pin = pad_name(pad)
        if pin not in comp.pin_nets:
            continue
        net_name = comp.pin_nets[pin]
        new_pad = (
            clear_pad_net(pad)
            if net_name.startswith("unconnected-")
            else set_pad_net(pad, net_name)
        )
        if new_pad != pad:
            updates += 1
        new_block = new_block[:start] + new_pad + new_block[end:]
    return new_block, updates


def rotate_pad_orientations(block: str, footprint_rotation: float) -> str:
    """Convert library-local pad angles to KiCad board absolute angles.

    Pad positions remain local to the footprint, but KiCad stores pad
    orientation in board coordinates.  Merely setting the footprint ``at``
    rotation moves the pads without rotating their shapes, which can turn a
    valid fine-pitch connector into overlapping copper.
    """
    if abs(footprint_rotation % 360.0) < 0.0005:
        return block

    new_block = block
    for start, end, pad in reversed(pad_blocks(block)):
        match = re.search(
            r'\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)',
            pad,
        )
        if not match:
            continue
        local_angle = float(match.group(3) or 0.0)
        board_angle = (local_angle + footprint_rotation) % 360.0
        replacement = f"(at {match.group(1)} {match.group(2)}"
        if abs(board_angle) >= 0.0005:
            replacement += f" {fmt(board_angle)}"
        replacement += ")"
        new_pad = pad[: match.start()] + replacement + pad[match.end() :]
        new_block = new_block[:start] + new_pad + new_block[end:]
    return new_block


def transform_footprint_zone_coordinates(
    block: str,
    footprint_x: float,
    footprint_y: float,
    footprint_rotation: float,
) -> str:
    """Convert library-local footprint rule-area polygons to board coordinates.

    KiCad stores footprint graphics and pad positions locally, but polygon
    points inside footprint rule areas are serialized in board coordinates.
    Leaving library-local points untouched moves connector keepouts to the
    board origin and makes KiCad report the placed footprint as modified.
    """
    theta = math.radians(footprint_rotation)
    cosine = math.cos(theta)
    sine = math.sin(theta)
    coordinate = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    pattern = re.compile(rf"\(xy\s+({coordinate})\s+({coordinate})\)")

    def transform_zone(zone: str) -> str:
        def replace(match: re.Match[str]) -> str:
            local_x = float(match.group(1))
            local_y = float(match.group(2))
            # KiCad board coordinates have Y increasing downward, so a
            # positive footprint angle is clockwise on screen.
            board_x = footprint_x + local_x * cosine + local_y * sine
            board_y = footprint_y - local_x * sine + local_y * cosine
            return f"(xy {fmt(board_x)} {fmt(board_y)})"

        return pattern.sub(replace, zone)

    new_block = block
    for start, end in reversed(top_level_child_spans(block, "zone")):
        new_block = new_block[:start] + transform_zone(block[start:end]) + new_block[end:]
    return new_block


def normalize_library_footprint(comp: Component, x: float, y: float, rot: float) -> str:
    raw = footprint_library_file(comp.footprint).read_text(encoding="utf-8")
    raw = re.sub(r'^\(footprint\s+"[^"]+"', f'(footprint "{q(comp.footprint)}"', raw, count=1)
    block = "\n".join("\t" + line if line else line for line in raw.splitlines())
    block = set_or_insert_top_line(block, "uuid", f'(uuid "{stable_uuid(f"footprint:{comp.ref}")}")')
    block = set_or_insert_top_line(block, "at", f"(at {fmt(x)} {fmt(y)} {fmt(rot % 360)})")
    block = rotate_pad_orientations(block, rot)
    block = transform_footprint_zone_coordinates(block, x, y, rot)
    block = replace_property(block, "Reference", comp.ref)
    block = replace_property(block, "Value", comp.value)
    return block


def update_metadata(block: str, comp: Component) -> str:
    block = replace_property(block, "Value", comp.value)
    internal_properties = {
        "Reference", "Value", "Footprint",
        "Sheetname", "Sheetfile", "exclude_from_board",
        "exclude_from_bom", "exclude_from_sim", "dnp",
    }
    for name, value in sorted(comp.properties.items()):
        if name in internal_properties or name.startswith("ki_"):
            continue
        block = replace_property(block, name, value)
    block = set_or_insert_top_line(block, "path", f'(path "{q(comp.path)}")')
    block = set_or_insert_top_line(block, "sheetname", f'(sheetname "{q(comp.sheetname)}")')
    block = set_or_insert_top_line(block, "sheetfile", f'(sheetfile "{q(comp.sheetfile)}")')
    block = update_attribute_flags(block, comp)
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pcb",
        type=Path,
        default=PCB,
        help="board file to update; defaults to the live ducktop2 main PCB",
    )
    parser.add_argument(
        "--refs",
        help="comma-separated references to update; omitted updates all existing footprints",
    )
    args = parser.parse_args(argv)
    selected_refs = {ref.strip() for ref in args.refs.split(",") if ref.strip()} if args.refs else None
    pcb_path = args.pcb.expanduser().resolve()
    if not pcb_path.exists():
        raise FileNotFoundError(pcb_path)

    export_netlist()
    components = {
        ref: comp
        for ref, comp in parse_netlist().items()
        if "exclude_from_board" not in comp.properties
    }
    text = pcb_path.read_text(encoding="utf-8")
    fps = footprints(text)
    existing = {fp.ref: fp for fp in fps}

    if len(existing) != len(fps):
        raise RuntimeError("duplicate footprint references are present on the PCB")

    if selected_refs is None:
        actual_missing = set(components) - set(existing)
        actual_extra = set(existing) - set(components)
        actual_replacements = {
            ref for ref in set(components) & set(existing)
            if components[ref].footprint != existing[ref].footprint
        }
        if actual_missing != CURRENT_ECO_ADD_ONLY:
            raise RuntimeError(
                "unexpected add ECO: "
                f"missing_allowed={sorted(CURRENT_ECO_ADD_ONLY - actual_missing)} "
                f"unexpected={sorted(actual_missing - CURRENT_ECO_ADD_ONLY)}"
            )
        if actual_extra != ALLOWED_REMOVE_ONLY:
            raise RuntimeError(f"unexpected remove ECO: {sorted(actual_extra)}")
        if actual_replacements != CURRENT_ECO_REPLACE_ONLY:
            raise RuntimeError(
                "unexpected footprint ECO: "
                f"missing_allowed={sorted(CURRENT_ECO_REPLACE_ONLY - actual_replacements)} "
                f"unexpected={sorted(actual_replacements - CURRENT_ECO_REPLACE_ONLY)}"
            )

    forbidden = []
    for ref in existing:
        matrix_match = re.fullmatch(r"(?:SW|D)(\d+)", ref)
        if ref in {"J320", "J321", "C320", "C321"} or (
            matrix_match and 320 <= int(matrix_match.group(1)) <= 384
        ):
            forbidden.append(ref)
    if forbidden:
        raise RuntimeError(f"keyboard daughterboard footprints are present on the main PCB: {forbidden[:8]}")

    added: list[str] = []
    removed: list[str] = []
    replaced: list[str] = []
    metadata_updated = 0
    pad_updates = 0

    new_text = text
    for fp in reversed(fps):
        if selected_refs is not None and fp.ref not in selected_refs:
            continue
        if fp.ref in ALLOWED_REMOVE_ONLY:
            new_text = new_text[:fp.start] + new_text[fp.end:]
            removed.append(fp.ref)
            continue
        comp = components.get(fp.ref)
        if comp is None:
            continue
        block = fp.text
        if fp.ref in ALLOWED_ADD_OR_REPLACE and (fp.footprint != comp.footprint or fp.ref in FORCE_REPLACE):
            x, y, rot = ANCHORS_MM.get(fp.ref, at_tuple(block))
            block = normalize_library_footprint(comp, x, y, rot)
            replaced.append(fp.ref)
        elif fp.ref in REPOSITION_EXISTING:
            x, y, rot = ANCHORS_MM[fp.ref]
            _, _, old_rot = at_tuple(block)
            block = set_or_insert_top_line(block, "at", f"(at {fmt(x)} {fmt(y)} {fmt(rot % 360)})")
            block = rotate_pad_orientations(block, rot - old_rot)
        block = update_metadata(block, comp)
        block, count = update_pad_nets(block, comp)
        metadata_updated += 1
        pad_updates += count
        new_text = new_text[:fp.start] + block + new_text[fp.end:]

    allowed_add = ALLOWED_ADD_OR_REPLACE | ALLOWED_ADD_ONLY
    missing = [ref for ref in sorted(allowed_add) if ref not in existing]
    if selected_refs is not None:
        missing = [ref for ref in missing if ref in selected_refs]
    if missing:
        insert = new_text.rfind("\n)")
        if insert < 0:
            raise RuntimeError("could not find final board close paren")
        blocks: list[str] = []
        for ref in missing:
            comp = components[ref]
            x, y, rot = ANCHORS_MM.get(ref, (30.0, 30.0, 0.0))
            block = normalize_library_footprint(comp, x, y, rot)
            block = update_metadata(block, comp)
            block, count = update_pad_nets(block, comp)
            pad_updates += count
            blocks.append(block)
            added.append(ref)
        new_text = new_text[:insert] + "\n" + "\n".join(blocks) + new_text[insert:]

    temporary = pcb_path.with_name(pcb_path.name + ".eco-tmp")
    temporary.write_text(new_text, encoding="utf-8")
    temporary.replace(pcb_path)

    print(f"Updated PCB: {pcb_path}")
    print(f"Exported netlist: {NETLIST.relative_to(ROOT)}")
    print(f"Added footprints: {', '.join(added) if added else 'none'}")
    print(f"Removed footprints: {', '.join(sorted(removed)) if removed else 'none'}")
    print(f"Replaced footprints: {', '.join(sorted(replaced)) if replaced else 'none'}")
    print(f"Updated metadata on {metadata_updated} existing footprints")
    print(f"Updated or inserted {pad_updates} pad net assignment(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
