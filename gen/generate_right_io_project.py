#!/usr/bin/env python3
"""Generate the Right I/O board project (ducktop2 board split, Phase 2.2).

Right board carries: J11/J12 (USB2-only), PD2 chain (U42, U2010-15),
HDMI (J30 + U50/U51), GbE (J500 + U501/U500). FPC-2 (~83 signals)
connects it to the center board.

Reuses the existing sheet builders: generate_tcp0_external_hdmi_sheet
(HDMI), generate_ethernet_sheet (GbE), and the PD2 dual-role builder
(add_dual_role_port usb2_only=True for J11).

NOTE: the main ducktop2 project still contains these parts until the
Phase 2.4 center trim; the projects coexist during the transition.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import generate_tcp0_external_hdmi_sheet as hdmi
import generate_ethernet_sheet as eth
import generate_power_inputs_sheet as pwrin
import generate_usb_c_io_sheet as usb
import build_ducktop2 as b
from build_ducktop2 import PROJDIR, stable_uuid, uuid_scope, FOOTPRINTS
from generate_mu_carrier_sheet import root_label, sheet_block

BOARD_DIR = os.path.join(PROJDIR, "right_io")
PROJECT_NAME = "right_io"


def build_right_pd_sheet(sheet_symbol_uuid):
    """PD2 dual-role port (J11) + source port (J12) — both USB2-only."""
    s = b.Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 2000
    s.refcounters["#FLG"] = 2000
    s.text(20.32, 12.7, "== Right I/O: PD2 dual-role (J11) + source (J12), USB2-only ==")
    pwrin.add_dual_role_port(
        s, port=2, jref="J11", host={
            "dp": "HUB_DS1_DP", "dm": "HUB_DS1_DM",
            "sstx_p": None, "sstx_n": None,
            "ssrx_p": None, "ssrx_n": None,
        }, x0=20.32, y0=50.8, rbase=2040, cbase=2040, ubase=2010, dbase=2120, ebase=2090,
        usb2_only=True)
    usb.add_source_port(s, jref="J12", port=4, base=1760, x0=20.32, y0=337.82,
                        usb2_only=True)
    s.gnd(431.8, 622.3)
    return s


def build_right_hdmi_sheet(sheet_symbol_uuid):
    """HDMI-A (J30) + DDC/5V chain — reuses the main HDMI builder."""
    s = hdmi.build(sheet_symbol_uuid)
    return s


def build_right_eth_sheet(sheet_symbol_uuid):
    """GbE (RTL8111H + magnetics + RJ45) — reuses the main GbE builder."""
    s = eth.build(sheet_symbol_uuid)
    return s


def write_generated_sheet(context, filename, builder):
    sheet_uuid = stable_uuid(f"right_io:sheet:{context}")
    with uuid_scope(f"right_io:{context}"):
        sheet = builder(sheet_uuid)
        text = sheet.render(stable_uuid(f"right_io:self:{context}"), page_number=1)
    path = os.path.join(BOARD_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return sheet


def main() -> int:
    os.makedirs(BOARD_DIR, exist_ok=True)

    pd_s = write_generated_sheet("pd", "right_pd.kicad_sch", build_right_pd_sheet)
    hdmi_s = write_generated_sheet("hdmi", "right_hdmi.kicad_sch", build_right_hdmi_sheet)
    eth_s = write_generated_sheet("eth", "right_eth.kicad_sch", build_right_eth_sheet)

    # Collect the FPC-2 boundary nets = all hier labels across the sheets.
    hier_nets = set()
    pd_sheet_nets, hdmi_sheet_nets, eth_sheet_nets = set(), set(), set()
    for sheet, sink in ((pd_s, pd_sheet_nets), (hdmi_s, hdmi_sheet_nets), (eth_s, eth_sheet_nets)):
        for item in sheet.body:
            if not item.startswith('(hierarchical_label "'):
                continue
            name = item[len('(hierarchical_label "'):].split('"', 1)[0]
            hier_nets.add(name)
            sink.add(name)
    print(f"right_io FPC-2 boundary nets: {len(hier_nets)}")

    # Build the right_io root.
    pd_uuid = stable_uuid("right_io:sheet:pd")
    hdmi_uuid = stable_uuid("right_io:sheet:hdmi")
    eth_uuid = stable_uuid("right_io:sheet:eth")
    pd_block, pd_pins = sheet_block(pd_uuid, 30.48, 39.37, 119.38, 149.86,
                              "PD2 Dual-Role", "right_pd.kicad_sch", sorted(pd_sheet_nets))
    hdmi_block, hdmi_pins = sheet_block(hdmi_uuid, 30.48, 219.71, 119.38, 149.86,
                                "HDMI", "right_hdmi.kicad_sch", sorted(hdmi_sheet_nets))
    eth_block, eth_pins = sheet_block(eth_uuid, 30.48, 400.05, 119.38, 149.86,
                               "GbE", "right_eth.kicad_sch", sorted(eth_sheet_nets))

    root = []
    root.append(f'(kicad_sch\n  (version 20260306)\n  (generator "eeschema")\n  (generator_version "10.0")\n'
                f'  (uuid {stable_uuid("right_io:root")})\n  (paper "A2")\n')
    root.append(pd_block)
    root.append(hdmi_block)
    root.append(eth_block)
    # Root labels sit exactly on the hosting sheet's block pin endpoint so
    # KiCad wires each label to that sheet's hierarchical label.
    for net in sorted(pd_sheet_nets):
        root.append(root_label(pd_pins[net], net))
    for net in sorted(hdmi_sheet_nets):
        root.append(root_label(hdmi_pins[net], net))
    for net in sorted(eth_sheet_nets):
        root.append(root_label(eth_pins[net], net))
    root.append(f'  (sheet_instances\n    (path "/"\n      (page "1")\n    )\n  )\n  (embedded_fonts no)\n)')
    with open(os.path.join(BOARD_DIR, "right_io.kicad_sch"), "w", encoding="utf-8") as f:
        f.write("\n".join(root))
    print(f"wrote right_io project (root + {3} sheets) with {len(hier_nets)} FPC-2 nets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())