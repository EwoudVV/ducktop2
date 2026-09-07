#!/usr/bin/env python3
"""
Check or update netclasses on the center and I/O boards.

Widths come from manufacturing/mainboard_stackup_release.json.

  DIFF_85   PCIe Gen3 (NextPCB 85 ohm approved)         w=0.183mm s=0.1524mm (L1/L8)
  DIFF_90   USB 2.0 and USB 3.x pairs                 w=0.1796mm s=0.2032mm
  DIFF_100  HDMI + Ethernet MDI                         w=0.1521mm s=0.254mm

The board rule files carry the inner-layer widths and permitted layers.

Usage:
  python3 gen/setup_net_classes.py --project all
  python3 gen/setup_net_classes.py --project all --apply
"""

from __future__ import annotations

import re
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "ducktop2-center.kicad_pcb"
PROJECT = ROOT / "ducktop2-center.kicad_pro"
PROJECTS = {
    "center": (BOARD, PROJECT),
    "left": (ROOT / "left_io/left_io.kicad_pcb", ROOT / "left_io/left_io.kicad_pro"),
    "right": (ROOT / "right_io/right_io.kicad_pcb", ROOT / "right_io/right_io.kicad_pro"),
}

NET_RE = re.compile(r'\(net "([^"]+)"\)')

DEFAULT_CLASS = {
    "clearance": 0.15,
    "track_width": 0.2,
    "via_dia": 0.6,
    "via_drill": 0.3,
    "diff_pair_gap": 0.25,
}

# 2026-08-24: NextPCB field-solved geometries (approved stackup report).
# L1 microstrip over L2 (H1=4.5433mil, Er=4.2, 1oz) and L3 stripline over
# L2/L4 (H1=4.1732, H2=10.2835).  All widths/gaps are the fabricator's
# numbers; the earlier Hammerstad candidates were too wide.
# 2026-08-25: NextPCB 85 ohm reply received (HQDFM stackup-impedance report,
# "8层叠构.pdf" follow-up).  Real 85 ohm geometry: L1/L8 outer differential
# w=7.19mil (0.183mm) / s=6.00mil (0.1524mm), ref L2/L7; L3/L6 inner
# differential w=4.48mil (0.114mm) / s=6.00mil (0.1524mm), ref L2+L4/L5+L7.
# The class below carries the L1/L8 microstrip numbers (0.183/0.1524),
# replacing the interim 80 ohm solve (0.2085/0.1524).  L3/L6 stripline uses
# 0.114/0.1524 when routed on inner layers.
CLASSES: dict[str, dict] = {
    "DIFF_85": {"description": "PCIe Gen3 85 ohm differential (NextPCB approved: L1/L8 w0.183 s0.1524; L3/L6 w0.114 s0.1524)", "clearance": 0.15, "track_width": 0.183, "diff_pair_width": 0.183, "diff_pair_gap": 0.1524},
    "DIFF_90": {"description": "USB 2.0 / USB 3.x 90 ohm differential (NextPCB approved)", "clearance": 0.15, "track_width": 0.1796, "diff_pair_width": 0.1796, "diff_pair_gap": 0.2032},
    "DIFF_100": {"description": "HDMI + Ethernet MDI 100 ohm differential (NextPCB approved)", "clearance": 0.15, "track_width": 0.1521, "diff_pair_width": 0.1521, "diff_pair_gap": 0.254},
    "POWER_HI": {"description": "High-current rails (planes carry bulk; 1.0 mm legs)", "clearance": 0.15, "track_width": 1.0},
    "POWER_MID": {"description": "Mid-current rails (0.6 mm legs)", "clearance": 0.15, "track_width": 0.6},
}

EXACT_CLASSES = {
    "/PD1_VBUS_RAW": "POWER_HI",
    "/PD2_VBUS_RAW": "POWER_HI",
    "/Mu Carrier/PCIE_3V3_IN": "POWER_HI",
    "/Maker MCU/MAKER_3V3_CORE": "POWER_MID",
    "/WIFI_USB_DN": "DIFF_90",
}

LEAF_CLASSIFIERS: list[tuple[str, re.Pattern]] = [
    # 85-ohm differential (PCIe Gen3: NVMe x4 from Mu, Wi-Fi x1, REFCLK)
    ("DIFF_85", re.compile(r"^(PCIE_M_L[0-3]_(RX|TX)(_RAW)?|PCIE_M_REFCLK(_SRC)?|WIFI_PCIE_(RX|TX)|WIFI_PCIE_TX_RAW|WIFI_REFCLK(_E)?)_(N|P)$")),
    # 90-ohm differential (USB 3.x / USB-C SS lanes)
    ("DIFF_90", re.compile(r"^(HUB_(DS[0-9]|UP)_(SSRX|SSTX|TX_RAW)|HUB_DIS[0-9]_(TX|RX)|J(12|22|23)_(RX|TX)[0-9]|J24_SSTX|USBC[12]_SSTX_RAW|USBC[12]_(SSRX|SSTX)|PD[12]_(SSRX_RAW|CTX[12]_RAW|TX[12]))_(N|P)$")),
    # 100-ohm differential (HDMI + Ethernet MDI / host / REFCLK / HSI-HSO)
    ("DIFF_100", re.compile(r"^(TCP0_(TX|TXRX)[01]|EXT_HDMI_(CK|D[0-9])|ETH_MDI[0-9]|GBE_HOST_(RX|TX)|GBE_REFCLK|GBE_HS(I|O))_(N|P)$")),
    # USB 2.0 uses the same approved 90-ohm coupled geometry.
    ("DIFF_90", re.compile(r"^(USBC[12]|HUB_DS[0-9]|HUB_DIS[0-9]|AUDIO_USB|EC_HOST_USB|MAKER_USB|MCU_USB|EC_USB_ISO|TPAD_CONN|MAKER_USB_ISO|CODEC_USB|SYSTEM_DAC_USB|TRACKPAD_USB|WIFI_USB|DFU_CONN|EC_DFU)_(DP|DN)$")),
    ("DIFF_90", re.compile(r"^RADIO_CODEC_USB_(HOST|DB)_(DP|DN)$")),
    ("DIFF_90", re.compile(r"^PD[12]_(CONN|HOST_SWITCHED)_(DP|DN)$")),
    ("DIFF_90", re.compile(r"^MAKER_USB_MCU_(DP|DN)$")),
    # High-current rails: pack bus, system 5 V/3.3 V, VSYS, Mu 12 V, VBUS_RAW
    ("POWER_HI", re.compile(r"^(VSYS|SYS_5V|SYS_3V3|MU_12V|VBUS_RAW|PACK_POS_RAW|PACK_NEG_RAW|PACK_POS_FUSED|FG_VSS|VBUS_COMBINED|SEL_STAGE2|USB_PD_SELECTED|PD[12]_(VBUS_GATED|VBUS_RAW|PPHV)|AUX_DC_(RAW|TERM|FUSED|PROTECTED)|AUX_EFUSE_IN_SYS|BAT_CHARGER|MU12_PRE_SENSE|PCIE_3V3(_IN)?|USB_PORT_5V)$")),
    # Mid-current rails
    ("POWER_MID", re.compile(r"^(MCU_3V3|USB_PORT_5V|INTERNAL_USB_VBUS)$")),
    ("POWER_MID", re.compile(r"^(J(12|22|23|24|25)_5V_PRE|J(12|22|23)_VBUS(_SYS|_POWER)?|RADIO_DB_5V|EC_AON_IN|AON_OR_RAW|WIFI_3V3|MAKER_(3V3|5V)_CORE|RADIO_CODEC_USB_VBUS_(HOST|DB)|SYSTEM_DAC_USB_VBUS|TPAD_5V|KB_FFC_5V|AUDIO_5V)$")),
]


def normalize(net: str) -> str:
    return net.rsplit("/", 1)[-1]


def project_pattern(net: str) -> str:
    # Braces are bus syntax in KiCad's project settings. Match the escaped
    # sheet-name slash without letting that parser turn it into a bus.
    return net.replace("{slash}", "*")


def classify(nets: set[str]) -> tuple[dict[str, list[str]], list[str]]:
    classes: dict[str, list[str]] = {name: [] for name in CLASSES}
    unclassified_hs: list[str] = []
    for net in sorted(nets):
        exact_class = EXACT_CLASSES.get(net)
        if exact_class is not None:
            classes[exact_class].append(net)
            continue
        leaf = normalize(net)
        assigned = False
        for cls, pattern in LEAF_CLASSIFIERS:
            if pattern.match(leaf):
                classes[cls].append(net)
                assigned = True
                break
        if not assigned and not net.startswith("unconnected-") and HS_LOOKALIKE.search(net):
            unclassified_hs.append(net)
    return classes, unclassified_hs

# Look-alike nets that must not be classified (control/power riding HS-like names)
HS_LOOKALIKE = re.compile(r"HDMI|PCIE|USB3|SSRX|SSTX|MDI|REFCLK|_DP$|_DN$|TX_RAW", re.IGNORECASE)


def collect_nets(board: Path = BOARD) -> set[str]:
    text = board.read_text(encoding="utf-8")
    return set(NET_RE.findall(text))


def expected_project(classes: dict[str, list[str]], project_path: Path = PROJECT) -> dict:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    net_settings = project.setdefault("net_settings", {})
    existing = {item["name"]: item for item in net_settings.get("classes", [])}
    for name, params in [("Default", DEFAULT_CLASS), *CLASSES.items()]:
        item = existing.setdefault(name, {"name": name})
        item.pop("description", None)
        if name != "Default" or "clearance" not in item:
            item["clearance"] = params["clearance"]
        item["track_width"] = params["track_width"]
        item["diff_pair_width"] = params.get("diff_pair_width", params["track_width"])
        item["diff_pair_gap"] = params.get("diff_pair_gap", DEFAULT_CLASS["diff_pair_gap"])
        item["via_diameter"] = DEFAULT_CLASS["via_dia"]
        item["via_drill"] = DEFAULT_CLASS["via_drill"]
    net_settings["classes"] = list(existing.values())
    classified = {net for nets in classes.values() for net in nets}
    classified |= {project_pattern(net) for net in classified}
    present = collect_nets(project_path.with_suffix(".kicad_pcb"))
    retained = [item for item in net_settings.get("netclass_patterns", [])
                if item["pattern"] not in classified and
                (item["pattern"] in present or any(c in item["pattern"] for c in "*?"))]
    net_settings["netclass_patterns"] = retained + [
        {"netclass": class_name, "pattern": project_pattern(net)}
        for class_name in sorted(classes)
        for net in sorted(classes[class_name])
    ]
    if not any(item["netclass"] == "USB2_45" for item in net_settings["netclass_patterns"]):
        net_settings["classes"] = [item for item in net_settings["classes"] if item["name"] != "USB2_45"]

    settings = project["board"]["design_settings"]
    settings["track_widths"] = sorted({
        0.091, 0.111, 0.114, 0.1521, 0.1796, 0.183,
        0.25, 0.3, 0.4, 0.6, 1.0,
    })
    settings["diff_pair_dimensions"] = [
        {"gap": 0.0, "via_gap": 0.0, "width": 0.0},
        {"gap": 0.1524, "via_gap": 0.25, "width": 0.183},
        {"gap": 0.2032, "via_gap": 0.25, "width": 0.1796},
        {"gap": 0.254, "via_gap": 0.25, "width": 0.1521},
    ]
    return project


def apply_or_check(classes: dict[str, list[str]], apply: bool, project_path: Path = PROJECT) -> bool:
    expected = expected_project(classes, project_path)
    actual = json.loads(project_path.read_text(encoding="utf-8"))
    if actual == expected:
        print("project net classes: exact")
        return True
    if not apply:
        print("project net classes: DRIFT")
        return False
    project_path.write_text(json.dumps(expected, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {project_path.name}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=[*PROJECTS, "all"], default="center")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    passed = True
    for name in PROJECTS if args.project == "all" else [args.project]:
        board, project = PROJECTS[name]
        classes, unclassified = classify(collect_nets(board))
        print(name, {key: len(value) for key, value in classes.items()})
        if unclassified:
            print("unclassified names to review:", ", ".join(unclassified))
        passed = apply_or_check(classes, args.apply and not args.dry_run, project) and passed
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
