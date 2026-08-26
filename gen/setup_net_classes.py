#!/usr/bin/env python3
"""
Set up Ducktop2 mainboard design rules and high-speed net classes.

Impedance targets -> candidate geometries (see gen/compute_impedance.py and
verification/IMPEDANCE_VERIFICATION_2026-08-01.md):

  DIFF_85   PCIe Gen3 (NextPCB 85 ohm approved)         w=0.183mm s=0.1524mm (L1/L8)
  DIFF_90   USB 3.0 / USB-C SS lanes                    w=0.1796mm s=0.2032mm
  DIFF_100  HDMI + Ethernet MDI                         w=0.1521mm s=0.254mm
  USB2_45   USB 2.0 D+/D- single-ended                  w=0.2248mm

All route on L1 referenced to the solid L2 GND plane.

Usage:
  python3 gen/setup_net_classes.py --dry-run   # print classification table
  python3 gen/setup_net_classes.py --apply     # edit ducktop2.kicad_pcb
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "ducktop2.kicad_pcb"

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
    "DIFF_90": {"description": "USB 3.x / USB-C 90 ohm differential (NextPCB approved)", "clearance": 0.15, "track_width": 0.1796, "diff_pair_width": 0.1796, "diff_pair_gap": 0.2032},
    "DIFF_100": {"description": "HDMI + Ethernet MDI 100 ohm differential (NextPCB approved)", "clearance": 0.15, "track_width": 0.1521, "diff_pair_width": 0.1521, "diff_pair_gap": 0.254},
    "USB2_45": {"description": "USB 2.0 D+/D- 45 ohm single-ended (NextPCB approved)", "clearance": 0.15, "track_width": 0.2248},
    "POWER_HI": {"description": "High-current rails (planes carry bulk; 1.0 mm legs)", "clearance": 0.15, "track_width": 1.0},
    "POWER_MID": {"description": "Mid-current rails (0.6 mm legs)", "clearance": 0.15, "track_width": 0.6},
}

SHEET_PREFIXES = (
    "Native USB-C I{slash}O/",
    "Mu Carrier/",
    "TCP0 External HDMI/",
    "Gigabit Ethernet/",
    "Internal Services/",
    "Maker MCU/",
    "System Audio/",
    "Power Inputs/",
    "Wi-Fi{slash}Bluetooth & OLEDs/",
    "Optional Radio Daughterboard Interface/",
)

LEAF_CLASSIFIERS: list[tuple[str, re.Pattern]] = [
    # 85-ohm differential (PCIe Gen3: NVMe x4 from Mu, Wi-Fi x1, REFCLK)
    ("DIFF_85", re.compile(r"^(PCIE_M_L[0-3]_(RX|TX)(_RAW)?|PCIE_M_REFCLK(_SRC)?|WIFI_PCIE_(RX|TX)|WIFI_PCIE_TX_RAW|WIFI_REFCLK(_E)?)_(N|P)$")),
    # 90-ohm differential (USB 3.x / USB-C SS lanes)
    ("DIFF_90", re.compile(r"^(HUB_(DS[0-9]|UP)_(SSRX|SSTX|TX_RAW)|HUB_DIS[0-9]_(TX|RX)|J12_(RX|TX)[0-9]|J24_SSTX|USBC[12]_SSTX_RAW|USBC[12]_(SSRX|SSTX)|PD[12]_SSRX_RAW)_(N|P)$")),
    # 100-ohm differential (HDMI + Ethernet MDI / host / REFCLK / HSI-HSO)
    ("DIFF_100", re.compile(r"^(EXT_HDMI_(CK|D[0-9])|ETH_MDI[0-9]|GBE_HOST_(RX|TX)|GBE_REFCLK|GBE_HS(I|O))_(N|P)$")),
    # 45-ohm single-ended (USB 2.0 D+/D-)
    ("USB2_45", re.compile(r"^(USBC[12]|HUB_DS[0-9]|HUB_DIS[0-9]|AUDIO_USB|EC_HOST_USB|MAKER_USB|MCU_USB|EC_USB_ISO|TPAD_CONN|MAKER_USB_ISO|CODEC_USB|SYSTEM_DAC_USB|TRACKPAD_USB|WIFI_USB|DFU_CONN|EC_DFU)_(DP|DM)$")),
    # High-current rails: pack bus, system 5 V/3.3 V, VSYS, Mu 12 V, VBUS_RAW
    ("POWER_HI", re.compile(r"^(VSYS|SYS_5V|SYS_3V3|MU_12V|VBUS_RAW|PACK_POS_RAW|PACK_NEG_RAW|PACK_POS_FUSED)$")),
    # Mid-current rails
    ("POWER_MID", re.compile(r"^(MCU_3V3|USB_PORT_5V|INTERNAL_USB_VBUS)$")),
]


def normalize(net: str) -> str:
    leaf = net.lstrip("/")
    for prefix in SHEET_PREFIXES:
        if leaf.startswith(prefix):
            leaf = leaf[len(prefix):]
            break
    return leaf


def classify(nets: set[str]) -> tuple[dict[str, list[str]], list[str]]:
    classes: dict[str, list[str]] = {name: [] for name in CLASSES}
    unclassified_hs: list[str] = []
    for net in sorted(nets):
        leaf = normalize(net)
        assigned = False
        for cls, pattern in LEAF_CLASSIFIERS:
            if pattern.match(leaf):
                classes[cls].append(net)
                assigned = True
                break
        if not assigned and HS_LOOKALIKE.search(net):
            unclassified_hs.append(net)
    return classes, unclassified_hs

# Look-alike nets that must not be classified (control/power riding HS-like names)
HS_LOOKALIKE = re.compile(r"HDMI|PCIE|USB3|SSRX|SSTX|MDI|REFCLK|_DP$|_DM$|TX_RAW", re.IGNORECASE)


def collect_nets() -> set[str]:
    text = BOARD.read_text(encoding="utf-8")
    return set(NET_RE.findall(text))


def render_classes(classes: dict[str, list[str]]) -> str:
    """Render KiCad 10 design-rule net_class blocks (top-level in the board
    file): (net_class "NAME" "DESCRIPTION" (clearance) (trace_width)
    (via_dia) (via_drill) (diff_pair_width) (diff_pair_gap) (add_net ...)*.

    The Default net class is included so the board has explicit base rules.
    """
    blocks = []
    all_classes = [("Default", DEFAULT_CLASS)] + list(CLASSES.items())
    for cls, params in all_classes:
        lines = [f'(net_class "{cls}" "{params.get("description", "Default net class")}"']
        lines.append(f'\t(clearance {params["clearance"]})')
        lines.append(f'\t(trace_width {params["track_width"]})')
        lines.append(f'\t(via_dia {DEFAULT_CLASS["via_dia"]})')
        lines.append(f'\t(via_drill {DEFAULT_CLASS["via_drill"]})')
        lines.append(f'\t(diff_pair_width {params.get("diff_pair_width", params["track_width"])})')
        lines.append(f'\t(diff_pair_gap {params.get("diff_pair_gap", DEFAULT_CLASS["diff_pair_gap"])})')
        if cls != "Default":
            for net in sorted(classes.get(cls, [])):
                lines.append(f'\t(add_net "{net}")')
        lines.append(")")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def block_bounds(text: str, token: str) -> tuple[int, int]:
    """Return (open, close) offsets of the depth-1 block named ``token``,
    skipping quoted strings (net names contain parens)."""
    depth = 0
    i = 0
    n = len(text)
    open_at = None
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == "(":
            depth += 1
            m = re.match(r"\(([A-Za-z0-9_.]+)", text[i:])
            if depth == 2 and m and m.group(1) == token:
                open_at = i
                close_at = None
                d = 1
                k = i + 1
                while k < n:
                    if text[k] == '"':
                        k += 1
                        while k < n and text[k] != '"':
                            k += 2 if text[k] == "\\" else 1
                        k += 1
                        continue
                    if text[k] == "(":
                        d += 1
                    elif text[k] == ")":
                        d -= 1
                        if d == 0:
                            close_at = k
                            break
                    k += 1
                if close_at is not None:
                    return open_at, close_at
            i += len(m.group(0)) if m else 1
        elif c == ")":
            depth -= 1
            i += 1
        else:
            i += 1
    raise SystemExit(f"block {token!r} not found")


def apply(classes: dict[str, list[str]]) -> None:
    text = BOARD.read_text(encoding="utf-8")

    _setup_open, setup_close = block_bounds(text, "setup")
    rendered = render_classes(classes)

    # Idempotent: drop any previously inserted net_class blocks first.
    while True:
        try:
            s, e = block_bounds(text, "net_class")
        except SystemExit:
            break
        text = text[:s] + text[e + 1:].lstrip("\n")

    text = text[:setup_close + 1] + "\n" + rendered + text[setup_close + 1:]

    shutil.copyfile(BOARD, BOARD.with_suffix(".kicad_pcb.bak"))
    BOARD.write_text(text, encoding="utf-8")
    print(f"wrote {BOARD.name} (backup: {BOARD.name}.bak)")


def validate() -> None:
    cli = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    import tempfile
    with tempfile.TemporaryDirectory(prefix="netclass-check-") as tmp:
        copy = Path(tmp) / BOARD.name
        shutil.copyfile(BOARD, copy)
        result = subprocess.run(
            [cli, "pcb", "drc", "--output", str(Path(tmp) / "drc.json"), str(copy)],
            capture_output=True, text=True,
        )
        print(result.stdout[-2000:] if result.stdout else "")
        if result.returncode != 0:
            print(result.stderr[-2000:])
            raise SystemExit(f"kicad-cli failed to parse board (rc={result.returncode})")
        print("board parses OK (kicad-cli drc accepted the net classes)")


def main() -> int:
    nets = collect_nets()
    classes, unclassified = classify(nets)

    print(f"{'Class':10s} {'Nets':>5s}")
    for cls in sorted(classes):
        print(f"{cls:10s} {len(classes[cls]):5d}")
    if unclassified:
        print("\nUNCLASSIFIED high-speed look-alikes:")
        for net in unclassified:
            print(f"  {net}")

    if "--apply" in sys.argv:
        apply(classes)
        validate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
