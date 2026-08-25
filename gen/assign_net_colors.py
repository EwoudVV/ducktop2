#!/usr/bin/env python3
"""
Assign ratnest net colors in ducktop2.kicad_pro by routing function.

The user routes by hand and wants the ratsnest sorted by function so the
high-speed and power groups are immediately distinguishable:
  SSD PCIe  -> green      USB ports -> orange      Ethernet -> blue
  WiFi      -> cyan       HDMI      -> magenta     Audio     -> purple
  Power rails -> red      GND       -> gray        Battery/PD -> gold
  Control/I2C/clocks -> slate (low-contrast; routing-irrelevant)

Nets not in any group keep KiCad's default ratsnest color.

Stored under the pro's top-level net_settings.net_colors as
{netname: css-string} - the app's authoritative location (proven by the
app itself: a GUI-assigned color lands there, while a copy under
board.design_settings is ignored).
KiCad's COLOR4D JSON serialization is a CSS string ("rgb(r, g, b)" with
0-255 ints for opaque colors), NOT an array - see
common/gal/color4d.cpp to_json/from_json. Regenerate with:
  python3 gen/assign_net_colors.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRO = ROOT / "ducktop2.kicad_pro"
BOARD = ROOT / "ducktop2.kicad_pcb"

COLORS: list[tuple[str, tuple[float, float, float], re.Pattern]] = [
    ("SSD PCIe", (0.00, 0.70, 0.10), re.compile(
        r"^(PCIE_M_L[0-3]_(RX|TX)(_RAW)?|PCIE_M_REFCLK(_SRC)?)_(N|P)$|^PCIE_M_REFCLK$|^PCIE_3V3$|^PCIE_WAKE_N$|^PCIE_M_PERST_N$|^PCIE_M_CLKREQ_N$")),
    ("WiFi", (0.00, 0.80, 0.80), re.compile(
        r"^(WIFI_|BT_|WL_)")),
    ("USB ports", (1.00, 0.50, 0.00), re.compile(
        r"^(HUB_|USBC[12]_|J1[12]_|J2[2345]_|USB2_|USB3_|USB5_|INTERNAL_USB_|AUDIO_USB|EC_HOST_USB|MAKER_USB|MCU_USB|EC_USB_ISO|TPAD_CONN|MAKER_USB_ISO|CODEC_USB|SYSTEM_DAC_USB|TRACKPAD_USB|WIFI_USB|DFU_CONN|EC_DFU)")),
    ("HDMI", (0.80, 0.20, 0.80), re.compile(
        r"^(EXT_HDMI_|HDMI_)")),
    ("Ethernet", (0.30, 0.50, 1.00), re.compile(
        r"^(ETH_|GBE_)")),
    ("Audio", (0.60, 0.10, 0.90), re.compile(
        r"^(AUDIO_|CODEC_|SPK_|SPEAKER_|HPA_|AMP_|MIC_|J422_|JAC_)")),
    ("Power rails", (1.00, 0.15, 0.10), re.compile(
        r"^(VSYS|SYS_5V|SYS_3V3|MCU_3V3|MU_12V|VBUS_RAW|USB_PORT_5V|INTERNAL_USB_VBUS|MAKER_3V3|PCIE_3V3|SYS_3V3_SWITCH|3V3|5V|12V)")),
    ("Battery/PD", (0.90, 0.70, 0.00), re.compile(
        r"^(PACK_|PD1_|PD2_|CHG_|BQ|BMS_|CELL[0-9]|PACK_RAW)")),
    ("Control/I2C/clocks", (0.35, 0.45, 0.60), re.compile(
        r"(_SCL$|_SDA$|_CLK$|_SPI_|_EN$|_PG$|_RESET|_RST$|_FAULT|_INT$|^I2C_|^SPI_|_TEST|_BOOT|_STRAP|_CTL$|_DET$)")),
]


def leaf(net: str) -> str:
    return net.rsplit("/", 1)[-1]


def classify(leaf_name: str) -> tuple[float, float, float] | None:
    for _label, rgb, pattern in COLORS:
        if pattern.match(leaf_name):
            return rgb
    return None


def css(rgb: tuple[float, float, float]) -> str:
    r, g, b = (round(c * 255) for c in rgb)
    return f"rgb({r}, {g}, {b})"


def main() -> int:
    nets = set(re.findall(r'\(net "([^"]+)"\)', BOARD.read_text(encoding="utf-8")))
    assignments: dict[str, str] = {}
    unmatched = []
    for net in sorted(nets):
        rgb = classify(leaf(net))
        if rgb is None:
            unmatched.append(net)
        else:
            assignments[net] = css(rgb)
    assignments["GND"] = css((0.55, 0.55, 0.55))
    assignments["/AON_FAULT_N"] = "rgb(255, 0, 0)"  # user override: pure red

    pro = json.loads(PRO.read_text(encoding="utf-8"))
    pro.setdefault("net_settings", {}).setdefault("net_colors", {}).update(assignments)
    PRO.write_text(json.dumps(pro, indent=1), encoding="utf-8")
    print(f"{len(assignments)} nets colored; {len(unmatched)} left at default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())