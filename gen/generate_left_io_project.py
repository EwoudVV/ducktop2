#!/usr/bin/env python3
"""Generate the Left I/O board project (ducktop2 board split, Phase 2.1).

Left board carries: J21-25, J190, hub U1700 + PD1 chain + SS muxes +
USB-A cluster. FPC-1 (75 signals) connects it to the center board.

This Phase 2.1 cut reuses the existing sheet builders from the main
project at their native coordinates, emitting them as the left_io
project's own sheets with a left_io root. The 75 FPC-1 nets are the
hierarchical labels already produced by the builders (the "hier" nets).

NOTE: the main ducktop2 project still contains these parts until the
Phase 2.4 center trim; the two projects coexist during the transition.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import generate_usb_c_io_sheet as usb
import generate_power_inputs_sheet as pwrin
import build_ducktop2 as b
from build_ducktop2 import PROJDIR, stable_uuid, uuid_scope, U, FOOTPRINTS
from generate_mu_carrier_sheet import root_label, sheet_block, build_fpc_sheet
import fpc_contract as fpc

BOARD_DIR = os.path.join(PROJDIR, "left_io")
PROJECT_NAME = "left_io"


def build_left_usb_sheet(sheet_symbol_uuid):
    """Hub + source ports (J22/J23) + USB-A cluster (J24/J25)."""
    s = b.Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 1700
    s.refcounters["#FLG"] = 1700
    s.text(20, 12.7, "== Left I/O: USB7206C hub, source ports, USB-A spare ports ==")
    s.text(20, 20.32, "Board split Phase 2.1: hub + PD1 moved left; FPC-1 crosses to center.")
    usb.add_hub_supplies(s)
    usb.add_hub(s)  # includes add_usba_ports (J24/J25)
    # J22/J23 source ports (J12 stays on center for now — it is on the
    # right edge; the center trim removes it from this sheet later).
    usb.add_source_port(s, jref="J22", port=2, base=1780, x0=20.32, y0=238.76)
    usb.add_source_port(s, jref="J23", port=3, base=1740, x0=304.8, y0=238.76)
    s.pwrflag(571.5, 198.12, "HUB_VCORE")
    s.pwrflag(571.5, 215.9, "USB_PORT_5V")
    s.gnd(571.5, 228.6)
    return s


def build_left_pd_sheet(sheet_symbol_uuid):
    """PD1 dual-role port (J21) + selector + AUX input terminal (J190)."""
    s = b.Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 2000
    s.refcounters["#FLG"] = 2000
    s.text(20.32, 12.7, "== Left I/O: PD1 dual-role port (J21) + AUX input (J190) ==")
    pwrin.add_dual_role_port(
        s, port=1, jref="J21", host={
            "dp": "USBC1_DP", "dm": "USBC1_DM",
            "sstx_p": "USBC1_SSTX_P", "sstx_n": "USBC1_SSTX_N",
            "ssrx_p": "USBC1_SSRX_P", "ssrx_n": "USBC1_SSRX_N",
        }, x0=20.32, y0=50.8, rbase=2000, cbase=2000, ubase=2000, dbase=2100, ebase=2080)
    pwrin.add_pd_selector(s)
    # AUX/SOLAR input terminal — the raw terminal lives on the left board;
    # the protection chain (fuse/TVS/reverse FET/efuse) stays on the center
    # board where the VSYS OR-ing is. AUX_DC_RAW crosses FPC-1.
    s.place("J190", "Conn_01x02", "AUX/SOLAR protected screw terminal 6-22V nominal",
            680, 50.8, footprint=FOOTPRINTS["Terminal_01x02_5.08"],
            pin_nets={"1": ("AUX_DC_RAW", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Phoenix Contact", "MPN": "1715022"})
    s.text(20.32, 693.42, "Five-port source budget: 5 x 0.9A maximum advertised load = 4.5A on the dedicated 6A USB_PORT_5V rail.")
    s.gnd(431.8, 622.3)
    return s


def write_generated_sheet(context, filename, builder):
    sheet_uuid = stable_uuid(f"left_io:sheet:{context}")
    with uuid_scope(f"left_io:{context}"):
        sheet = builder(sheet_uuid)
        text = sheet.render(stable_uuid(f"left_io:self:{context}"), page_number=1)
    path = os.path.join(BOARD_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return sheet


def main() -> int:
    os.makedirs(BOARD_DIR, exist_ok=True)

    usb_s = write_generated_sheet("usb", "left_usb.kicad_sch", build_left_usb_sheet)
    pd_s = write_generated_sheet("pd", "left_pd.kicad_sch", build_left_pd_sheet)

    # Phase 4a: FPC-1 connector sheet (the physical FH12-100S on the left
    # board edge).  Pin map from fpc_contract.py -- same conductor order as
    # the center's FPC1_C.
    fpc1_sheet_uuid = stable_uuid("left_io:sheet:fpc1")
    with uuid_scope("left_io:fpc1"):
        fpc1_s = build_fpc_sheet(fpc1_sheet_uuid, "FPC101", "Conn_01x68_FFC_MP",
                                 fpc.FPC1_PINMAP, "FH41-68S-0.5SH (FPC-1)",
                                 pwr_base=3400)
        fpc1_text = fpc1_s.render(stable_uuid("left_io:self:fpc1"),
                                  page_number=3, paper="A1")
    with open(os.path.join(BOARD_DIR, "left_fpc.kicad_sch"), "w",
              encoding="utf-8") as f:
        f.write(fpc1_text)

    # Collect the FPC-1 boundary nets = all hier labels across both sheets.
    hier_nets = set()
    sheet_nets = {}
    for key, sheet in (("usb", usb_s), ("pd", pd_s)):
        nets = set()
        for item in sheet.body:
            if not item.startswith('(hierarchical_label "'):
                continue
            name = item[len('(hierarchical_label "'):].split('"', 1)[0]
            nets.add(name)
            hier_nets.add(name)
        sheet_nets[key] = nets
    print(f"left_io FPC-1 boundary nets: {len(hier_nets)}")

    # Build the left_io root.
    usb_uuid = stable_uuid("left_io:sheet:usb")
    pd_uuid = stable_uuid("left_io:sheet:pd")
    # Each sheet block declares ONLY the nets its sheet actually hosts.
    usb_sheet_nets = sorted(sheet_nets['usb'])
    pd_sheet_nets = sorted(sheet_nets['pd'])
    usb_block, usb_pins = sheet_block(usb_uuid, 30.48, 39.37, 119.38, 149.86,
                               "USB Hub + Ports", "left_usb.kicad_sch", usb_sheet_nets)
    pd_block, pd_pins = sheet_block(pd_uuid, 30.48, 219.71, 119.38, 149.86,
                              "PD1 Dual-Role", "left_pd.kicad_sch", pd_sheet_nets)
    fpc1_block, fpc1_pins = sheet_block(fpc1_sheet_uuid, 170.0, 39.37, 119.38, 149.86,
                                 "FPC-1 (to Center)", "left_fpc.kicad_sch",
                                 fpc.FPC1_NETS)

    root = []
    root.append(f'(kicad_sch\n  (version 20260306)\n  (generator "eeschema")\n  (generator_version "10.0")\n'
                f'  (uuid {stable_uuid("left_io:root")})\n  (paper "A2")\n')
    root.append(usb_block)
    root.append(pd_block)
    root.append(fpc1_block)
    # Root labels for the FPC-1 boundary nets: each sits exactly on the sheet
    # block pin endpoint of the sheet that hosts it, so KiCad wires the label
    # to that sheet's hierarchical label (same pattern as the main root).
    # FPC-1 nets are hosted by the usb/pd sheets AND the FPC-1 connector
    # sheet; labels at both block pins join the nets by name.
    for net in usb_sheet_nets:
        root.append(root_label(usb_pins[net], net))
    for net in pd_sheet_nets:
        root.append(root_label(pd_pins[net], net))
    for net in fpc.FPC1_NETS:
        root.append(root_label(fpc1_pins[net], net))
    root.append(f'  (sheet_instances\n    (path "/"\n      (page "1")\n    )\n  )\n  (embedded_fonts no)\n)')
    with open(os.path.join(BOARD_DIR, "left_io.kicad_sch"), "w", encoding="utf-8") as f:
        f.write("\n".join(root))
    print(f"wrote left_io project (root + {2} sheets) with {len(hier_nets)} FPC-1 nets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())