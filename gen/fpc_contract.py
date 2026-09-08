#!/usr/bin/env python3
"""Board-to-board conductor maps used by the schematic generators.

FPC-1 joins the left and center boards; FPC-2 joins the right and center.
The 41- and 51-contact Molex interfaces carry signals and ground guards.
Power positives use separate crimp looms; two ground straps cross each seam.
J2071/J2072 carry protected pack power over an 18 AWG Micro-Fit harness,
with one rated contact per conductor. J2073/J2074 carry the isolated BMS
control interface and its own return over a separate five-wire harness.

A straight, same-side-contact FFC between oppositely mounted connectors
reverses the numbered pin map. The separate power harness is pin 1 to pin 1
and pin 2 to pin 2. Raw pack negative remains on the BMS. Its protected
return reaches system ground only through the center-board gauge shunt.
"""

# Side A: FPC101 left, FPC104 right. Side B: FPC102 and FPC103 on center.
# Same-side cables with facing mouths reverse numbered contacts.

from signal_interconnect_contract import LEFT_PINMAP, RIGHT_PINMAP, symbol_for

FPC1_PINMAP = dict(LEFT_PINMAP)
FPC2_PINMAP = dict(RIGHT_PINMAP)

# legacy ffc map, retained for old-board recovery only. new generators use
# bms_control_pinmap and do not place fpc105/fpc106.
FPC3_PINMAP = {
    **{pin: "NC" for pin in range(1, 31)},
    12: "PACK_CHG_TEMP_OK",
    13: "PACK_FAULT_N",
    14: "PACK_RETRY_PULSE",
    15: "MCU_3V3",
}

# power uses one rated contact per conductor. ctrl_gnd supplies only the
# isolated control island and must never be tied to fg_vss or raw negative.
BMS_POWER_PINMAP = {1: "PACK_POS_FUSED", 2: "FG_VSS"}
BMS_POWER_REFS = {"center": "J2071", "bms": "J2072"}
BMS_POWER_FOOTPRINT = "Connector_Molex:Molex_Micro-Fit_3.0_43650-0224_1x02-1MP_P3.00mm_Vertical"
BMS_POWER_MPN = "43650-0224"
BMS_POWER_HOUSING = "43645-0200"
BMS_POWER_CONTACT = "43030-0038"
BMS_POWER_WIRE_AWG = 18
BMS_POWER_WIRE_LENGTH_BUDGET_MM = 75

BMS_CONTROL_PINMAP = {1: "PACK_FAULT_N", 2: "PACK_RETRY_PULSE", 3: "MCU_3V3",
                      4: "PACK_CHG_TEMP_OK", 5: "CTRL_GND"}
BMS_CONTROL_CENTER_PINMAP = {**BMS_CONTROL_PINMAP, 5: "GND"}
BMS_CONTROL_REFS = {"center": "J2073", "bms": "J2074"}
BMS_CONTROL_FOOTPRINT = "Connector_JST:JST_SH_SM05B-SRSS-TB_1x05-1MP_P1.00mm_Horizontal"
BMS_CONTROL_MPN = "SM05B-SRSS-TB(LF)(SN)"
BMS_CONTROL_HOUSING = "SHR-05V-S"
BMS_CONTROL_CONTACT = "SSH-003T-P0.2-H"

# Cable transforms: side-B connectors are mounted 180 deg from side A, so
# their pin maps mirror side A.  The board build asserts the mounted
# rotations against this table (FPC_ROTATIONS).
CABLE_TRANSFORM = {"FPC-1": "reversed", "FPC-2": "reversed", "FPC-3": "reversed"}


from usb_power_contract import LEFT_POWER_PINMAP, RIGHT_POWER_PINMAP, boundary_nets

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
# solder pins -- verified against the Molex503908 drawing: the cable is
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
        if net in ("GND", "NC") or net in seen:
            continue
        seen.add(net)
        nets.append(net)
    return nets


FPC1_NETS = sorted(set(contract_nets(FPC1_PINMAP)) | set(boundary_nets(LEFT_POWER_PINMAP)))
FPC1_IO_NETS = FPC1_NETS + ["USB_PORT_5V"]
FPC2_NETS = sorted(set(contract_nets(FPC2_PINMAP)) | set(boundary_nets(RIGHT_POWER_PINMAP)))
FPC2_IO_NETS = FPC2_NETS + ["USB_PORT_5V"]
FPC3_NETS = contract_nets(FPC3_PINMAP) + contract_nets(BMS_POWER_PINMAP)
BMS_INTERCONNECT_NETS = contract_nets(BMS_CONTROL_CENTER_PINMAP) + contract_nets(BMS_POWER_PINMAP)

assert set(BMS_CONTROL_PINMAP) == set(range(1, 6))
assert all(BMS_CONTROL_PINMAP[p] == BMS_CONTROL_CENTER_PINMAP[p] for p in range(1, 5))
assert BMS_CONTROL_PINMAP[5] == "CTRL_GND" and BMS_CONTROL_CENTER_PINMAP[5] == "GND"
assert not {"FG_VSS", "PACK_NEG_RAW", "PACK_POS_FUSED"} & set(BMS_CONTROL_PINMAP.values())

if __name__ == "__main__":
    print(f"FPC-1: {len(FPC1_PINMAP)} pins, {len(FPC1_NETS)} nets")
    print(f"FPC-2: {len(FPC2_PINMAP)} pins, {len(FPC2_NETS)} nets")
    print(f"bms harness: {len(BMS_POWER_PINMAP)} power contacts, {len(BMS_CONTROL_PINMAP)} isolated control contacts")
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
