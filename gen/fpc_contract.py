#!/usr/bin/env python3
"""FPC boundary contracts (ducktop2 board split, Phase 4a).

Single source of truth for the FPC-1/FPC-2/FPC-3 connector pin maps used by
every project generator (center root, left_io, right_io, bms) and by the
cable spec.  Pin maps are authoritative: the same conductor order must exist
on both ends, so both boards' connectors are wired from THIS table.

FPC-1 (left_io <-> center): Hirose FH12-100S-0.5SH, 100 pins.
FPC-2 (right_io <-> center): Hirose FH12-100S-0.5SH, 100 pins.
FPC-3 (bms <-> center):      Hirose FH12-30S-0.5SH, 30 pins.

Power rails get 2 pins each where current matters (VSYS, USB_PORT_5V,
SYS_5V, PACK_POS_FUSED, PACK_NEG_RAW).  Differential pairs are kept
adjacent (P before N) with GND between pairs for return/EMI.  Unused pins
are GND.  MP (hold-down tab) pins are GND on every connector.

FPC-3 note: PACK_NEG_RAW (the pack negative) is named GND on the center
side -- the pack negative IS the system ground reference.  The BMS-side
name is authoritative in FPC3_PINMAP; the center side maps those pins to
GND (see center_pinmap()).
"""

FPC1_PINMAP = {
    1: "VSYS", 2: "VSYS", 3: "GND", 4: "USB_PORT_5V", 5: "USB_PORT_5V",
    6: "GND", 7: "SYS_3V3", 8: "GND", 9: "MCU_3V3", 10: "GND",
    11: "PD1_VBUS_RAW", 12: "GND", 13: "AUX_DC_RAW", 14: "GND",
    15: "USB_PD_SELECTED", 16: "GND", 17: "INTERNAL_USB_VBUS_VALID", 18: "GND",
    19: "PD1_I2C_SCL", 20: "PD1_I2C_SDA", 21: "GND", 22: "PD1_TCPC_IRQ_N",
    23: "GND", 24: "PD1_PATH_EN", 25: "GND", 26: "PD1_VALID_N", 27: "GND",
    28: "PD2_VALID_N", 29: "GND", 30: "PD1_EFUSE_FAULT_N", 31: "GND",
    32: "PD_PROTECT_FAULT_N", 33: "GND", 34: "USBC1_DP", 35: "USBC1_DM",
    36: "GND", 37: "USBC2_DP", 38: "USBC2_DM", 39: "GND",
    40: "HUB_DS1_DP", 41: "HUB_DS1_DM", 42: "GND",
    43: "USBC1_SSRX_P", 44: "USBC1_SSRX_N", 45: "GND",
    46: "USBC1_SSTX_P", 47: "USBC1_SSTX_N", 48: "GND",
    49: "USBC2_SSRX_P", 50: "USBC2_SSRX_N", 51: "GND",
    52: "USBC2_SSTX_P", 53: "USBC2_SSTX_N",
}
for _pin in range(54, 101):
    FPC1_PINMAP[_pin] = "GND"

FPC2_PINMAP = {
    1: "SYS_5V", 2: "SYS_5V", 3: "GND", 4: "USB_PORT_5V", 5: "USB_PORT_5V",
    6: "GND", 7: "SYS_3V3", 8: "GND", 9: "PCIE_3V3", 10: "GND",
    11: "MCU_3V3", 12: "GND", 13: "PD2_VBUS_RAW", 14: "GND",
    15: "MU_HOST_ACTIVE", 16: "GND", 17: "PLTRST_SRC_N", 18: "GND",
    19: "PCIE_WAKE_N", 20: "GND", 21: "GBE_CLKREQ_N", 22: "GND",
    23: "PD2_I2C_SCL", 24: "PD2_I2C_SDA", 25: "GND", 26: "PD2_TCPC_IRQ_N",
    27: "GND", 28: "PD2_PATH_EN", 29: "GND", 30: "PD2_EFUSE_FAULT_N",
    31: "GND", 32: "PD_PROTECT_FAULT_N", 33: "GND",
    34: "HUB_DS1_DP", 35: "HUB_DS1_DM", 36: "GND",
    37: "TCP0_DDC_SCL", 38: "TCP0_DDC_SDA", 39: "GND", 40: "TCP0_HPD",
    41: "GND", 42: "GBE_REFCLK_P", 43: "GBE_REFCLK_N", 44: "GND",
    45: "GBE_HOST_RX_P", 46: "GBE_HOST_RX_N", 47: "GND",
    48: "GBE_HOST_TX_P", 49: "GBE_HOST_TX_N", 50: "GND",
    51: "TCP0_TX0_P", 52: "TCP0_TX0_N", 53: "GND",
    54: "TCP0_TX1_P", 55: "TCP0_TX1_N", 56: "GND",
    57: "TCP0_TXRX0_P", 58: "TCP0_TXRX0_N", 59: "GND",
    60: "TCP0_TXRX1_P", 61: "TCP0_TXRX1_N",
}
for _pin in range(62, 101):
    FPC2_PINMAP[_pin] = "GND"

# BMS-side names.  PACK_NEG_RAW becomes GND on the center side.
FPC3_PINMAP = {
    1: "PACK_POS_FUSED", 2: "PACK_POS_FUSED",
    3: "PACK_NEG_RAW", 4: "PACK_NEG_RAW",
    5: "PACK_FAULT_N", 6: "PACK_RETRY_PULSE",
    7: "FG_VSS", 8: "MCU_3V3",
    9: "GND", 10: "GND", 11: "GND", 12: "GND", 13: "GND", 14: "GND",
    15: "GND", 16: "GND", 17: "GND", 18: "GND", 19: "GND", 20: "GND",
    21: "GND", 22: "GND", 23: "GND", 24: "GND", 25: "GND", 26: "GND",
    27: "GND", 28: "GND", 29: "GND", 30: "GND",
}

# Center-side pin maps: PACK_NEG_RAW pins join the system GND net.
CENTER_RENAME = {"PACK_NEG_RAW": "GND"}


def center_pinmap(pinmap: dict) -> dict:
    """Return the same map with center-side net names (FPC-3)."""
    return {pin: CENTER_RENAME.get(net, net) for pin, net in pinmap.items()}


def contract_nets(pinmap: dict) -> list:
    """Ordered unique non-GND net names in the map (block-pin contract)."""
    nets = []
    seen = set()
    for pin in sorted(pinmap):
        net = pinmap[pin]
        if net == "GND" or net in seen:
            continue
        seen.add(net)
        nets.append(net)
    return nets


FPC1_NETS = contract_nets(FPC1_PINMAP)
FPC2_NETS = contract_nets(FPC2_PINMAP)
FPC3_NETS = contract_nets(FPC3_PINMAP)
FPC3_NETS_CENTER = contract_nets(center_pinmap(FPC3_PINMAP))

if __name__ == "__main__":
    print(f"FPC-1: {len(FPC1_PINMAP)} pins, {len(FPC1_NETS)} nets")
    print(f"FPC-2: {len(FPC2_PINMAP)} pins, {len(FPC2_NETS)} nets")
    print(f"FPC-3: {len(FPC3_PINMAP)} pins, {len(FPC3_NETS)} nets")
    dupes = [n for n in set(FPC1_NETS) if FPC1_NETS.count(n) > 1]
    if dupes:
        raise SystemExit(f"FPC-1 duplicate nets: {dupes}")
    for name, m in (("FPC-1", FPC1_PINMAP), ("FPC-2", FPC2_PINMAP),
                    ("FPC-3", FPC3_PINMAP)):
        for pin, net in sorted(m.items()):
            if not isinstance(pin, int) or not isinstance(net, str) or not net:
                raise SystemExit(f"{name} bad entry pin={pin!r} net={net!r}")
    print("fpc_contract ok")