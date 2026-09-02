#!/usr/bin/env python3
"""FPC boundary contracts (ducktop2 board split, Phase 4a + Phase 5 remediation).

Single source of truth for the FPC-1/FPC-2/FPC-3 connector pin maps used by
every project generator (center root, left_io, right_io, bms) and by the
cable spec.  Pin maps are authoritative: the same conductor order must exist
on both ends, so both boards' connectors are wired from THIS table.

FPC-1 (left_io <-> center): Hirose FH41-68S-0.5SH, 68 pins (shielded FFC).
FPC-2 (right_io <-> center): Hirose FH41-68S-0.5SH, 68 pins (shielded FFC).
FPC-3 (bms <-> center):      Hirose FH12-30S-0.5SH, 30 pins.

Cable transform (Phase 5, fixes the mirrored-cable defect): the connectors
on each seam are mounted 180 deg apart (OPPOSITE rotations) so their mouths
(FFC entry = the actuator/front face, footprint-local +Y, opposite the
solder pins) face each other across the seam -- the only physically
assembleable configuration for in-line coplanar boards; the cable lies flat
across the seam.  Opposite rotations + a straight Type-A FFC means pin N of
the side-A connector reaches pin (N_max+1-N) of the side-B connector (the
cable mirrors the pin order), so every side-B map is the MIRROR of its
side-A map (reversed_map).  The build asserts the mounted rotations match
this transform.

Power budgets (Phase 5): every power rail gets enough pins for its worst
case at Hirose's 0.5 A/pin derated to 0.4 A/pin for cable-length margin.
Differential pairs are kept adjacent (P before N) with GND between pairs
for return/EMI.  Unused pins are GND.  MP (hold-down tab) pins are GND on
every connector; the FH41's SH shield pads are grounded via the symbol's
SH pin.

FPC-3 note (Phase 5): the pack NEGATIVE never crosses the cable.  The
return conductors carry FG_VSS -- the BQ77915's post-FET protected return,
which is the BMS board's ground reference.  On the center side the same
conductors land on /FG_VSS (the gauge-shunt output; RS1 ties it to system
GND).  This keeps the protector and the gauge shunt in series with the
load return: a protector trip opens the load's return path instead of
being bypassed by a pack-negative-to-ground bond.
"""

# Side A = daughterboard connector (FPC101 left, FPC104 right, FPC106 bms).
# Side B = center connector (FPC102, FPC103, FPC105) = reversed_map(side A).

FPC1_PINMAP = {
    1: "VSYS", 2: "VSYS", 3: "VSYS", 4: "VSYS", 5: "VSYS", 6: "VSYS",
    7: "GND", 8: "GND",
    9: "USB_PORT_5V", 10: "USB_PORT_5V", 11: "USB_PORT_5V", 12: "USB_PORT_5V",
    13: "GND",
    14: "SYS_3V3", 15: "SYS_3V3",
    16: "MCU_3V3",
    17: "PD1_VBUS_RAW", 18: "PD1_VBUS_RAW", 19: "PD1_VBUS_RAW",
    20: "PD1_VBUS_RAW", 21: "PD1_VBUS_RAW", 22: "PD1_VBUS_RAW",
    23: "USB_PD_SELECTED", 24: "USB_PD_SELECTED", 25: "USB_PD_SELECTED",
    26: "USB_PD_SELECTED", 27: "USB_PD_SELECTED", 28: "USB_PD_SELECTED",
    29: "AUX_DC_RAW", 30: "AUX_DC_RAW", 31: "AUX_DC_RAW",
    32: "AUX_DC_RAW", 33: "AUX_DC_RAW", 34: "AUX_DC_RAW",
    35: "GND", 36: "GND", 37: "GND",
    38: "INTERNAL_USB_VBUS_VALID",
    39: "PD1_I2C_SCL", 40: "PD1_I2C_SDA",
    41: "PD1_TCPC_IRQ_N",
    42: "PD1_PATH_EN",
    43: "PD1_VALID_N",
    44: "PD1_EFUSE_FAULT_N",
    45: "PD_PROTECT_FAULT_N",
    46: "HUB_DS4_DP", 47: "HUB_DS4_DM",
    48: "HUB_PRT_CTL4",
    49: "USBC1_DP", 50: "USBC1_DM",
    51: "GND",
    52: "USBC2_DP", 53: "USBC2_DM",
    54: "GND",
    55: "HUB_DS1_DP", 56: "HUB_DS1_DM",
    57: "GND",
    58: "USBC1_SSRX_P", 59: "USBC1_SSRX_N",
    60: "GND",
    61: "USBC1_SSTX_P", 62: "USBC1_SSTX_N",
    63: "GND",
    64: "USBC2_SSRX_P", 65: "USBC2_SSRX_N",
    66: "USBC2_SSTX_P", 67: "USBC2_SSTX_N",
    68: "GND",
}

FPC2_PINMAP = {
    1: "SYS_5V", 2: "SYS_5V", 3: "SYS_5V", 4: "SYS_5V",
    5: "GND", 6: "GND",
    7: "PD2_VBUS_GATED", 8: "PD2_VBUS_GATED", 9: "PD2_VBUS_GATED",
    10: "PD2_VBUS_GATED", 11: "PD2_VBUS_GATED", 12: "PD2_VBUS_GATED",
    13: "PD2_VBUS_GATED",
    14: "PD2_VBUS_RAW", 15: "PD2_VBUS_RAW",
    16: "USB_PORT_5V", 17: "USB_PORT_5V", 18: "USB_PORT_5V", 19: "USB_PORT_5V",
    20: "GND", 21: "GND",
    22: "SYS_3V3", 23: "SYS_3V3",
    24: "PCIE_3V3", 25: "PCIE_3V3",
    26: "MCU_3V3", 27: "MCU_3V3",
    28: "GND",
    29: "HUB_DS4_DP", 30: "HUB_DS4_DM",
    31: "HUB_PRT_CTL4",
    32: "MU_HOST_ACTIVE",
    33: "PLTRST_SRC_N",
    34: "PCIE_WAKE_N",
    35: "GBE_CLKREQ_N",
    36: "PD2_I2C_SCL", 37: "PD2_I2C_SDA",
    38: "PD2_TCPC_IRQ_N",
    39: "PD2_PATH_EN",
    40: "PD2_EFUSE_FAULT_N",
    41: "PD_PROTECT_FAULT_N",
    42: "GND",
    43: "HUB_DS1_DP", 44: "HUB_DS1_DM",
    45: "GND",
    46: "TCP0_DDC_SCL", 47: "TCP0_DDC_SDA",
    48: "TCP0_HPD",
    49: "GND",
    50: "GBE_REFCLK_P", 51: "GBE_REFCLK_N",
    52: "GND",
    53: "GBE_HOST_RX_P", 54: "GBE_HOST_RX_N",
    55: "GND",
    56: "GBE_HOST_TX_P", 57: "GBE_HOST_TX_N",
    58: "GND",
    59: "TCP0_TX0_P", 60: "TCP0_TX0_N",
    61: "GND",
    62: "TCP0_TX1_P", 63: "TCP0_TX1_N",
    64: "GND",
    65: "TCP0_TXRX0_P", 66: "TCP0_TXRX0_N",
    67: "TCP0_TXRX1_P", 68: "TCP0_TXRX1_N",
}

# BMS-side names.  The pack negative stays inside the BMS; the return
# conductors are the protected FG_VSS (see module docstring).
FPC3_PINMAP = {
    1: "PACK_POS_FUSED", 2: "PACK_POS_FUSED", 3: "PACK_POS_FUSED",
    4: "PACK_POS_FUSED", 5: "PACK_POS_FUSED", 6: "PACK_POS_FUSED",
    7: "PACK_POS_FUSED", 8: "PACK_POS_FUSED", 9: "PACK_POS_FUSED",
    10: "PACK_POS_FUSED", 11: "PACK_POS_FUSED", 12: "PACK_POS_FUSED",
    13: "PACK_FAULT_N",
    14: "PACK_RETRY_PULSE",
    15: "MCU_3V3",
    16: "FG_VSS", 17: "FG_VSS", 18: "FG_VSS", 19: "FG_VSS", 20: "FG_VSS",
    21: "FG_VSS", 22: "FG_VSS", 23: "FG_VSS", 24: "FG_VSS", 25: "FG_VSS",
    26: "FG_VSS", 27: "FG_VSS", 28: "FG_VSS", 29: "FG_VSS", 30: "FG_VSS",
}

# Cable transforms: side-B connectors are mounted 180 deg from side A, so
# their pin maps mirror side A.  The board build asserts the mounted
# rotations against this table (FPC_ROTATIONS).
CABLE_TRANSFORM = {"FPC-1": "reversed", "FPC-2": "reversed", "FPC-3": "reversed"}


def reversed_map(pinmap: dict) -> dict:
    """Mirror a pin map end-to-end (pin p of side B carries the net of
    pin N_max+1-p of side A: the 180-deg-mounted side-B connector mirrors
    the pin order through the straight FFC)."""
    n = max(pinmap)
    return {pin: pinmap[n + 1 - pin] for pin in pinmap}


# Center-side (side B) maps.
FPC102_PINMAP = reversed_map(FPC1_PINMAP)
FPC103_PINMAP = reversed_map(FPC2_PINMAP)
FPC105_PINMAP = reversed_map(FPC3_PINMAP)

# Mounted rotations per connector (degrees, KiCad CCW).  The FFC entry
# (mouth) is the actuator/front face = footprint-local +Y (opposite the
# solder pins -- verified against the Hirose FH12 2D drawing: the FPC is
# drawn entering on the side opposite the tails).  Mouths must face each
# other across every seam.  Verified against the pad transform in
# generate_split_boards.
FPC_ROTATIONS = {
    "FPC101": 90, "FPC102": 270,     # seam x=70: mouths face each other
    "FPC103": 90, "FPC104": 270,     # seam x=300
    "FPC105": 180, "FPC106": 0,      # seam y=0 (center bottom <-> BMS top)
}


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

if __name__ == "__main__":
    print(f"FPC-1: {len(FPC1_PINMAP)} pins, {len(FPC1_NETS)} nets")
    print(f"FPC-2: {len(FPC2_PINMAP)} pins, {len(FPC2_NETS)} nets")
    print(f"FPC-3: {len(FPC3_PINMAP)} pins, {len(FPC3_NETS)} nets")
    for name, m in (("FPC-1", FPC1_PINMAP), ("FPC-2", FPC2_PINMAP),
                    ("FPC-3", FPC3_PINMAP)):
        dupes = [n for n in set(contract_nets(m)) if contract_nets(m).count(n) > 1]
        if dupes:
            raise SystemExit(f"{name} duplicate nets: {dupes}")
        for pin, net in sorted(m.items()):
            if not isinstance(pin, int) or not isinstance(net, str) or not net:
                raise SystemExit(f"{name} bad entry pin={pin!r} net={net!r}")
    # mirror sanity: side B is the exact mirror of side A
    for a, b, label in ((FPC1_PINMAP, FPC102_PINMAP, "FPC-1"),
                        (FPC2_PINMAP, FPC103_PINMAP, "FPC-2"),
                        (FPC3_PINMAP, FPC105_PINMAP, "FPC-3")):
        n = max(a)
        for pin in a:
            assert b[n + 1 - pin] == a[pin], f"{label} mirror broken at {pin}"
    print("fpc_contract ok")
