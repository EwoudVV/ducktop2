#!/usr/bin/env python3
"""Generate Ducktop2 pin-by-pin schematic review artifacts.

This is a human-review companion to gen/verify_design_contracts.py.  It reads
the live KiCad XML netlist, emits one row per selected high-risk component pin,
and marks each row as:

* PASS: covered by an explicit project/datasheet contract and matching
* FAIL: covered by a contract and not matching
* REVIEW: intentionally included for human review but not yet contract-checked

The goal is traceability, not magic.  Uncontracted REVIEW rows are work for a
second reviewer before fab.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NETLIST = ROOT / "verification" / "pin_review_netlist.xml"
REPORT_DATE = dt.date.today().isoformat()
CSV_OUT = ROOT / "verification" / f"pin_by_pin_review_{REPORT_DATE}.csv"
MD_OUT = ROOT / "verification" / f"PIN_BY_PIN_REVIEW_{REPORT_DATE}.md"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


@dataclass(frozen=True)
class Contract:
    expected: str
    requirement: str
    source: str
    mode: str = "exact"


CRITICAL_REFS = [
    "J2", "F1", "RS1", "LED1", "U11", "Q11", "Q12", "RS10", "R700", "R701", "R702",
    "U719", "Q703", "Q704", "RS11",
    "R840", "R841", "R842", "R843", "R844", "R845", "R846", "R847", "R848", "R849", "R850", "R851", "R852", "R853", "R854", "R855",
    "C840", "C841", "C842", "C843", "C844", "C845", "C846", "C847", "C848",
    "TP1", "TP2", "TP3", "TP4", "TP7", "TP9", "TP10", "TP11",
    "C725", "R707", "R708", "Q701", "R709", "R13", "Q702", "D715", "D716", "R14", "Q700", "R719", "R16", "R705",
    "J190", "F190", "D190", "U12", "R739", "R740", "U15", "Q21", "Q22", "Q23", "Q24",
    "R730", "R731", "R732", "R733", "R734", "R735", "C740", "C741", "C742", "C743", "C744", "C745", "C746",
    "D710", "D711", "D712", "D713", "D714", "U718",
    "R795", "R796", "R797", "R798", "C795", "C796", "C797", "C798", "C799",
    "U2", "Q25", "U10",
    "U4", "U5", "L3", "U44", "J4", "Y1", "C32", "C33", "R37", "Y2", "C34", "C35", "J16",
    "A1", "A2", "U6", "U7", "J9", "TP5", "TP6", "TP8", "TP12", "TP13", "TP14", "TP15", "U769", "U770", "U771", "U772", "R773", "R774", "R775", "R776",
    "C794", "C830", "C831", "C832", "C833", "C834", "C835", "C836", "C837",
    "U750", "L750", "RS750", "Q750", "Q751", "R761", "R766", "R767", "R768", "J10", "J40", "F10", "R170", "R171", "U170",
    "U20", "R70", "C70", "C71", "C75", "C78", "U21", "U22", "J11",
    "U30", "R90", "C90", "C91", "C95", "C98", "U31", "U32", "J12",
    "U41", "U42", "U43", "U123", "U133", "U143", "J21", "J22", "J23",
    "C120", "C121", "C130", "C131", "C140", "C141", "C800", "C801", "C810", "C811", "C820", "C821",
    "U720", "U721", "U722", "U14", "R736", "R737", "R738",
    "Q15", "Q16", "Q17", "Q18", "Q19", "Q20",
    "R720", "R721", "R722", "R723", "R724", "R725", "R726", "R727", "R728",
    "C730", "C731", "C732", "C733", "C734", "C735", "C736", "C737",
    "J30", "U50", "U51", "U53", "U54", "U55", "R165", "C158", "C159", "C162", "C163",
    "C150", "C151", "C152", "C153", "C154", "C155", "C156", "C157",
    "R150", "R151", "R152", "R153", "R154", "R155", "R156", "R157",
    "D150", "D151", "D152", "D153", "D154", "D155", "D156", "D157",
    "R570", "R571", "R572", "R573", "R574", "R575", "R576", "R577", "R578", "R579",
    "U61", "Q60", "R202", "J58", "U62", "U63", "U64",
    "R252", "C280", "C281", "C283", "C284", "R256", "J52", "J53", "J54", "J56", "Q200",
    "U45", "J41", "J45",
    "U40", "J42", "U70", "L70", "FL240", "FL250", "U240", "U241", "R242", "R227", "U260", "U261",
    "U242", "C246", "R243", "R244", "U250", "U251", "R260", "R228",
    "U252", "C256", "R261", "R262", "J70", "J71",
    "U330", "R330", "R331", "R337", "Q330", "Q331", "Q332", "D390", "D391", "D392", "D393",
    "F400", "U400", "U401", "U402", "R417", "U410", "U420", "U421", "J420", "J421",
    "U430", "MK430", "U431", "R432", "R433", "R434", "R435",
    "C453", "C454", "C455", "C456", "LED430",
    "U500", "U501", "U502", "J500", "Y500", "R500", "R501", "R502", "R503",
    "R504", "R505", "R506", "C500", "C501", "C502", "C503", "C513", "C514",
    "J310",
    "U901", "U902", "U903", "U904", "U905", "U906", "Q901", "J901", "J902",
    "U910", "U911", "U912", "U913", "U914", "U915", "U916", "U917",
    "U918", "U919", "U920", "U921", "U922", "Q903", "R930", "R931",
    *[f"R{ref}" for ref in range(932, 962)],
]

# Current high-risk parts that must exist in the active design.  The historical
# CRITICAL_REFS list is retained as review history, but it contains retired
# architecture references and is no longer used as the netlist authority.
CURRENT_REQUIRED_REFS = {
    # Battery protection, power path, charger, and always-on control.
    "J2", "F1", "RS1", "RS11", "U719", "Q703", "Q704", "U2", "U10", "U11", "Q25", "J190",
    # EC, source manager, Mu, storage, and Wi-Fi.
    "U4", "U44", "A1", "A2", "J9", "F10", "U170",
    # Five external USB-C ports: two dual-role PD/data and three source/data-only.
    "U14", "U41", "U42", "U720", "U721",
    "U2000", "U2010", "U2001", "U2011", "U2002", "U2012", "U2003", "U2013",
    "U2004", "U2014", "U2006", "U2016",
    "J21", "J11", "J22", "J23", "J12", "U1700", "R1730", "R1731", "R1732", "R1733",
    # User I/O, audio, keyboard, maker MCU, and optional radio boundary.
    "U45", "J41", "J45", "U400", "U402", "U430", "MK430", "J310", "U500", "U501", "U502",
    "J2300", "U2300", "U2303", "U2304",
}


contracts: dict[tuple[str, str], Contract] = {}


def add(ref: str, pin: str | int, expected: str, requirement: str, source: str) -> None:
    contracts[(ref, str(pin))] = Contract(expected, requirement, source)


def add_nc(ref: str, pin: str | int, requirement: str, source: str) -> None:
    contracts[(ref, str(pin))] = Contract("unconnected", requirement, source, "unconnected")


def add_many(ref: str, pins, expected: str, requirement: str, source: str) -> None:
    for pin in pins:
        add(ref, pin, expected, requirement, source)


def local(sheet: str, name: str) -> str:
    return f"/{sheet}/{name}"


def clear_ref_contracts(*refs: str) -> None:
    ref_set = set(refs)
    for key in list(contracts):
        if key[0] in ref_set:
            del contracts[key]


def load_contracts() -> None:
    project = "Ducktop2 project contract"

    # Battery power entry and aux/random DC input.
    for pin in (1, 2):
        add("J2", pin, "/Power & Battery/PACK_POS_RAW", "Paired raw pack-positive power contact.", "Ducktop2 autonomous 3S protection contract")
    for pin in (3, 4):
        add("J2", pin, "/Power & Battery/PACK_NEG_RAW", "Paired raw pack-negative power contact before protector shunt/FETs.", "Ducktop2 autonomous 3S protection contract")
    add("J2", 5, "/Power & Battery/CELL1_TAP", "Cell-1 positive / cell-2 negative balance tap.", "TI BQ77915 3S connection contract")
    add("J2", 6, "/Power & Battery/CELL2_TAP", "Cell-2 positive / cell-3 negative balance tap.", "TI BQ77915 3S connection contract")
    add("F1", 1, "/Power & Battery/PACK_POS_RAW", "Main pack fuse input is raw pack positive.", "Ducktop2 battery safety review")
    add("F1", 2, "/Power & Battery/BAT_PROT_VIN", "Main pack fuse output enters the high-side reversal/UV/OV protection stage.", "Ducktop2 battery safety review")
    add("RS1", 1, "/Power & Battery/FG_VSS", "Fuel-gauge pack-side Kelvin return flows through the populated shunt.", "Ducktop2 battery safety review")
    add("RS1", 2, "GND", "System side of shunt is board ground.", "Ducktop2 battery safety review")
    bms = "TI BQ77915 Rev L 3S autonomous primary-protector contract"
    for pin, net in {
        1: "/Power & Battery/BMS_VDD", 2: "/Power & Battery/BMS_AVDD",
        3: "/Power & Battery/BMS_VC3_TOP", 4: "/Power & Battery/BMS_VC3_TOP",
        5: "/Power & Battery/BMS_VC3_TOP", 6: "/Power & Battery/BMS_VC2",
        7: "/Power & Battery/BMS_VC1", 8: "/Power & Battery/BMS_VC0",
        9: "/Power & Battery/PACK_NEG_RAW", 10: "/Power & Battery/BMS_SRP",
        11: "/Power & Battery/BMS_SRN", 12: "/Power & Battery/BMS_DSG_DRV",
        13: "/Power & Battery/BMS_CHG_DRV", 14: "/Power & Battery/BMS_LD",
        16: "/Power & Battery/PACK_NEG_RAW", 17: "/Power & Battery/BMS_OCDP",
        18: "/Power & Battery/BMS_TS_UNUSED", 20: "/Power & Battery/PACK_NEG_RAW",
        22: "/Power & Battery/BMS_PRES", 23: "/Power & Battery/PACK_NEG_RAW",
        24: "/Power & Battery/PACK_NEG_RAW",
    }.items():
        add("U719", pin, net, "BQ7791500 monitors three cells and autonomously controls charge/discharge FETs.", bms)
    for pin, reason in ((15, "Single-device LPWR is unused."), (19, "VTB is unused because motherboard thermal sensing is disabled."), (21, "Single-device CBO is unused.")):
        add_nc("U719", pin, reason, bms)
    for ref, p1, p2 in (
        ("R840", "/Power & Battery/PACK_POS_RAW", "/Power & Battery/BMS_VDD"),
        ("R841", "/Power & Battery/PACK_NEG_RAW", "/Power & Battery/BMS_VC0"),
        ("R842", "/Power & Battery/CELL1_TAP", "/Power & Battery/BMS_VC1"),
        ("R843", "/Power & Battery/CELL2_TAP", "/Power & Battery/BMS_VC2"),
        ("R844", "/Power & Battery/PACK_POS_RAW", "/Power & Battery/BMS_VC3_TOP"),
        ("R845", "/Power & Battery/PACK_NEG_RAW", "/Power & Battery/BMS_SRP"),
        ("R846", "/Power & Battery/BMS_SENSE_N", "/Power & Battery/BMS_SRN"),
        ("R847", "/Power & Battery/BMS_DSG_DRV", "/Power & Battery/BMS_DSG_GATE"),
        ("R848", "/Power & Battery/BMS_CHG_DRV", "/Power & Battery/BMS_CHG_GATE"),
        ("R849", "/Power & Battery/BMS_DSG_GATE", "/Power & Battery/BMS_SENSE_N"),
        ("R850", "/Power & Battery/BMS_CHG_GATE", "/Power & Battery/FG_VSS"),
        ("R851", "/Power & Battery/BMS_LD", "/Power & Battery/FG_VSS"),
        ("R852", "/Power & Battery/PACK_POS_RAW", "/Power & Battery/BMS_PRES"),
        ("R853", "/Power & Battery/BMS_TS_UNUSED", "/Power & Battery/PACK_NEG_RAW"),
        ("R854", "/Power & Battery/BMS_OCDP", "/Power & Battery/PACK_NEG_RAW"),
    ):
        add(ref, 1, p1, "BQ7791500 released support network.", bms)
        add(ref, 2, p2, "BQ7791500 released support network.", bms)
    for ref, p1, p2 in (
        ("C840", "/Power & Battery/BMS_VDD", "/Power & Battery/PACK_NEG_RAW"),
        ("C841", "/Power & Battery/BMS_AVDD", "/Power & Battery/PACK_NEG_RAW"),
        ("C842", "/Power & Battery/BMS_VC0", "/Power & Battery/PACK_NEG_RAW"),
        ("C843", "/Power & Battery/BMS_VC1", "/Power & Battery/BMS_VC0"),
        ("C844", "/Power & Battery/BMS_VC2", "/Power & Battery/BMS_VC1"),
        ("C848", "/Power & Battery/BMS_VC3_TOP", "/Power & Battery/BMS_VC2"),
        ("C845", "/Power & Battery/BMS_SRP", "/Power & Battery/PACK_NEG_RAW"),
        ("C846", "/Power & Battery/BMS_SRP", "/Power & Battery/BMS_SRN"),
        ("C847", "/Power & Battery/BMS_SRN", "/Power & Battery/PACK_NEG_RAW"),
    ):
        add(ref, 1, p1, "BQ7791500 released filter network.", bms)
        add(ref, 2, p2, "BQ7791500 released filter network.", bms)
    add("RS11", 1, "/Power & Battery/PACK_NEG_RAW", "BQ7791500 battery-side shunt terminal.", bms)
    add("RS11", 2, "/Power & Battery/BMS_SENSE_N", "BQ7791500 FET-side shunt terminal.", bms)
    for ref, source, gate in (("Q703", "/Power & Battery/BMS_SENSE_N", "/Power & Battery/BMS_DSG_GATE"), ("Q704", "/Power & Battery/FG_VSS", "/Power & Battery/BMS_CHG_GATE")):
        add_many(ref, [1, 2, 3], source, "Low-side protection MOSFET source pads.", bms)
        add(ref, 4, gate, "BQ7791500 gate-control node.", bms)
        add(ref, 5, "/Power & Battery/BMS_FET_COMMON", "Back-to-back MOSFET common-drain node.", bms)
    add("LED1", 1, "/Power & Battery/STAT_DRV", "Charge indicator cathode is driven by the charger status sink.", "BQ25798 status-indicator contract")
    add("LED1", 2, "/Power & Battery/STAT_LED_A", "Charge indicator anode is current-limited from REGN.", "BQ25798 status-indicator contract")
    for ref, expected, note in (
        ("TP1", "GND", "Ground fixture reference."),
        ("TP2", "/Power & Battery/PACK_POS_FUSED", "Protected pack fixture point."),
        ("TP3", "/VSYS", "System-power fixture point."),
        ("TP4", "/EC_AON_IN", "Always-on input fixture point."),
        ("TP7", "/MCU_3V3", "EC 3.3 V fixture point."),
        ("TP9", "/CHG_INT_N", "Charger interrupt fixture point."),
        ("TP10", "/PACK_FAULT_N", "Pack-protection fault fixture point."),
        ("TP11", "/AON_FAULT_N", "Always-on eFuse fault fixture point."),
    ):
        add(ref, 1, expected, note, "Ducktop2 first-article DFT contract")
    for pin, net in {
        1: "/Power & Battery/BAT_PROT_VIN", 2: "/Power & Battery/BAT_PROT_UV",
        3: "/Power & Battery/BAT_PROT_OV", 4: "GND", 5: "GND",
        6: "/Power & Battery/BAT_PROT_SHDN", 7: "/PACK_FAULT_N",
        8: "/Power & Battery/PACK_POS_FUSED",
        9: "/Power & Battery/BAT_PROT_SENSE", 10: "/Power & Battery/BAT_PROT_GATE",
    }.items():
        add("U11", pin, net, "LTC4368-1 protects the fused pack input against reverse polarity and out-of-window voltage.", "Analog Devices LTC4368-1 datasheet plus Ducktop2 battery-entry contract")
    for ref, pin, net, note in (
        ("R707", 1, "/Power & Battery/BAT_PROT_VIN", "SHDN defaults high from protected pack input."),
        ("R707", 2, "/Power & Battery/BAT_PROT_SHDN", "LTC4368 SHDN latch-reset node."),
        ("R708", 1, "/MCU_3V3", "FAULT open-drain pull-up rail."),
        ("R708", 2, "/PACK_FAULT_N", "Pack-protector fault reaches the source manager."),
        ("Q701", 1, "/PACK_RETRY_PULSE", "Firmware retry pulse gate."),
        ("Q701", 2, "GND", "Retry NMOS source."),
        ("Q701", 3, "/Power & Battery/BAT_PROT_SHDN", "Retry NMOS clears the latched fault by pulsing SHDN low."),
        ("R709", 1, "/PACK_RETRY_PULSE", "Retry control defaults inactive."),
        ("R709", 2, "GND", "Retry pull-down return."),
    ):
        add(ref, pin, net, note, "Analog Devices LTC4368-1 latch/retry contract")
    for ref, drain in [("Q11", "/Power & Battery/BAT_PROT_VIN"), ("Q12", "/Power & Battery/BAT_PROT_SENSE")]:
        add_many(ref, [1, 2, 3], "/Power & Battery/BAT_PROT_FET_COMMON", "Back-to-back MOSFET source pins share the protected common-source node.", "Analog Devices LTC4368-1 reverse-protection topology")
        add(ref, 4, "/Power & Battery/BAT_PROT_GATE", "MOSFET gate is driven through the protected gate network.", "Analog Devices LTC4368-1 reverse-protection topology")
        add(ref, 5, drain, "MOSFET drain terminates its side of the protected pack path.", "Analog Devices LTC4368-1 reverse-protection topology")
    add("RS10", 1, "/Power & Battery/BAT_PROT_SENSE", "High-side shunt controller-side sense node.", "Ducktop2 protected-pack contract")
    add("RS10", 2, "/Power & Battery/PACK_POS_FUSED", "High-side shunt protected output node.", "Ducktop2 protected-pack contract")
    for ref, net_a, net_b in (
        ("R700", "/Power & Battery/BAT_PROT_VIN", "/Power & Battery/BAT_PROT_UV"),
        ("R701", "/Power & Battery/BAT_PROT_UV", "/Power & Battery/BAT_PROT_OV"),
        ("R702", "/Power & Battery/BAT_PROT_OV", "GND"),
    ):
        add(ref, 1, net_a, "LTC4368 pack UV/OV qualification ladder.", "Analog Devices LTC4368-1 datasheet")
        add(ref, 2, net_b, "LTC4368 pack UV/OV qualification ladder.", "Analog Devices LTC4368-1 datasheet")
    add("J190", 1, "/Power & Battery/AUX_DC_RAW", "Aux/random-DC positive enters before fuse.", project)
    add("J190", 2, "GND", "Aux/random-DC return is board ground.", project)
    add("F190", 1, "/Power & Battery/AUX_DC_RAW", "Aux input fuse input.", project)
    add("F190", 2, "/Power & Battery/AUX_DC_FUSED", "Aux input fuse output.", project)
    add("D190", 1, "/Power & Battery/AUX_DC_FUSED", "Aux TVS clamps protected aux input node.", project)
    add("D190", 2, "GND", "Aux TVS returns to ground.", project)
    aux_efuse = "TI TPS26630 datasheet plus Ducktop2 default-off AUX-input contract"
    for pin, net in {
        1: "/Power & Battery/AUX_DC_FUSED",
        2: "/Power & Battery/AUX_DC_FUSED",
        3: "/Power & Battery/AUX_EFUSE_BGATE",
        4: "/Power & Battery/AUX_EFUSE_DRV",
        5: "/Power & Battery/AUX_EFUSE_IN_SYS",
        6: "/Power & Battery/AUX_EFUSE_UV",
        7: "/Power & Battery/AUX_EFUSE_OV",
        8: "GND",
        9: "/Power & Battery/AUX_EFUSE_DVDT",
        10: "/Power & Battery/AUX_EFUSE_ILIM",
        11: "GND",
        14: "/AUX_FAULT_N",
        15: "/Power & Battery/AUX_PGTH",
        16: "/AUX_PGOOD",
        17: "/Power & Battery/AUX_DC_PROTECTED",
        18: "/Power & Battery/AUX_DC_PROTECTED",
        25: "GND",
    }.items():
        add("U12", pin, net, "AUX input is surge-protected, current-limited, and observable by the source manager.", aux_efuse)
    for pin in (12, 13, 19, 20, 21, 22, 23, 24):
        add_nc("U12", pin, "Unused TPS26630 optional pin is intentionally NC.", aux_efuse)
    add("R739", 1, "/Power & Battery/AUX_DC_PROTECTED", "PGTH divider senses the protected AUX output.", aux_efuse)
    add("R739", 2, "/Power & Battery/AUX_PGTH", "PGTH divider top sets the output-good threshold.", aux_efuse)
    add("R740", 1, "/Power & Battery/AUX_PGTH", "PGTH divider bottom sets the output-good threshold.", aux_efuse)
    add("R740", 2, "GND", "PGTH divider returns to ground; PGTH is not hard-grounded.", aux_efuse)
    selector = "ADI LTC4418 Rev A plus Vishay SiSS4409DN datasheets"
    for pin, net in {
        1: "/Power & Battery/MAIN_SEL_TMR",
        2: "/Power & Battery/USB_MAIN_UV", 3: "/Power & Battery/USB_MAIN_OV",
        4: "/Power & Battery/AUX_MAIN_UV", 5: "/Power & Battery/AUX_MAIN_OV",
        7: "GND", 8: "/Power & Battery/MAIN_SEL_INTVCC",
        11: "/Power & Battery/AUX_MAIN_GATE", 12: "/Power & Battery/AUX_MAIN_FET_COMMON",
        13: "/Power & Battery/USB_MAIN_GATE", 14: "/Power & Battery/USB_MAIN_FET_COMMON",
        15: "/Power & Battery/VBUS_COMBINED", 16: "/Power & Battery/AUX_DC_PROTECTED",
        17: "/USB_PD_SELECTED", 18: "/Power & Battery/MAIN_SEL_INTVCC",
        19: "/Power & Battery/MAIN_SEL_INTVCC", 20: "GND", 21: "GND",
    }.items():
        add("U15", pin, net, "Dual-input selector validates USB/AUX, gives USB priority, and drives reverse-blocking PMOS pairs.", selector)
    add_nc("U15", 6, "Unused cascade output is intentionally open.", selector)
    add("U15", 9, "/MAIN_USB_VALID_N", "Active-low USB source-valid output reaches source manager.", selector)
    add("U15", 10, "/MAIN_AUX_VALID_N", "Active-low AUX source-valid output reaches source manager.", selector)
    for ref, gate, common, drain in (
        ("Q21", "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "/USB_PD_SELECTED"),
        ("Q22", "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "/Power & Battery/VBUS_COMBINED"),
        ("Q23", "AUX_MAIN_GATE", "AUX_MAIN_FET_COMMON", "/Power & Battery/AUX_DC_PROTECTED"),
        ("Q24", "AUX_MAIN_GATE", "AUX_MAIN_FET_COMMON", "/Power & Battery/VBUS_COMBINED"),
    ):
        add(ref, 1, local("Power & Battery", gate), "Selector gate controller drives both PMOS gates directly.", selector)
        add_many(ref, [2, 3, 4], local("Power & Battery", common), "Back-to-back pair shares this common-source node.", selector)
        add(ref, 5, drain, "PMOS unified drain land terminates one side of the isolated path.", selector)
    for ref, net_a, net_b in (
        ("R730", "/USB_PD_SELECTED", "/Power & Battery/USB_MAIN_UV"),
        ("R731", "/Power & Battery/USB_MAIN_UV", "/Power & Battery/USB_MAIN_OV"),
        ("R732", "/Power & Battery/USB_MAIN_OV", "GND"),
        ("R733", "/Power & Battery/AUX_DC_PROTECTED", "/Power & Battery/AUX_MAIN_UV"),
        ("R734", "/Power & Battery/AUX_MAIN_UV", "/Power & Battery/AUX_MAIN_OV"),
        ("R735", "/Power & Battery/AUX_MAIN_OV", "GND"),
    ):
        add(ref, 1, net_a, "LTC4418 UV/OV qualification ladder.", selector)
        add(ref, 2, net_b, "LTC4418 UV/OV qualification ladder.", selector)
    for ref, net in (
        ("C740", "/Power & Battery/MAIN_SEL_INTVCC"), ("C741", "/Power & Battery/MAIN_SEL_TMR"),
        ("C742", "/USB_PD_SELECTED"), ("C743", "/Power & Battery/USB_MAIN_FET_COMMON"),
        ("C744", "/Power & Battery/AUX_DC_PROTECTED"), ("C745", "/Power & Battery/AUX_MAIN_FET_COMMON"),
    ):
        add(ref, 1, net, "Selector local bypass/timer capacitor.", selector)
        add(ref, 2, "GND", "Selector capacitor returns directly to ground.", selector)
    add("C746", 1, "/Power & Battery/VBUS_COMBINED", "LTC4418 output hold-up capacitor.", selector)
    add("C746", 2, "GND", "LTC4418 output hold-up return.", selector)

    aon_or = (
        "Ducktop2 source-independent EC always-on Schottky-OR contract: "
        "6.20V nominal UVLO rejects default USB-C 5V and accepts the autonomous 15V PDO"
    )
    for ref, source in (
        ("D710", "/Power & Battery/BAT_CHARGER"),
        ("D711", "/Power & Battery/AUX_DC_PROTECTED"),
        ("D712", "/PD1_VBUS_RAW"),
        ("D713", "/PD2_VBUS_RAW"),
        ("D714", "/PD3_VBUS_RAW"),
    ):
        add(ref, 1, "/Power & Battery/AON_OR_RAW", "Schottky cathode joins the aggregate always-on eFuse input.", aon_or)
        add(ref, 2, source, "Schottky anode senses one available input source ahead of source selection.", aon_or)
    for pin, net in {
        1: "/Power & Battery/AON_EFUSE_UV",
        2: "/Power & Battery/AON_EFUSE_OV",
        4: "/AON_FAULT_N",
        5: "/Power & Battery/AON_OR_RAW",
        6: "/EC_AON_IN",
        7: "/Power & Battery/AON_EFUSE_DVDT",
        8: "GND",
        9: "/Power & Battery/AON_EFUSE_ILM",
    }.items():
        add("U718", pin, net,
            "TPS259470A bounds the combined always-on source with true reverse blocking and a 6.06-6.36V UVLO window.",
            "TI TPS25947 datasheet plus Ducktop2 aggregate AON safety contract")
    add_nc("U718", 3, "TPS259470A AUXOFF is intentionally left open; the aggregate AON path does not use auxiliary power-off control.", aon_or)
    add_nc("U718", 10, "TPS259470A ITIMER is intentionally left open for the minimum current-limit fault timer delay allowed by the datasheet.", aon_or)
    for ref, net_a, net_b in (
        ("R795", "/Power & Battery/AON_OR_RAW", "/Power & Battery/AON_EFUSE_UV"),
        ("R796", "/Power & Battery/AON_EFUSE_UV", "/Power & Battery/AON_EFUSE_OV"),
        ("R797", "/Power & Battery/AON_EFUSE_OV", "GND"),
        ("R798", "/Power & Battery/AON_EFUSE_ILM", "GND"),
        ("C795", "/Power & Battery/AON_OR_RAW", "GND"),
        ("C796", "/Power & Battery/AON_OR_RAW", "GND"),
        ("C797", "/EC_AON_IN", "GND"),
        ("C798", "/EC_AON_IN", "GND"),
        ("C799", "/Power & Battery/AON_EFUSE_DVDT", "GND"),
    ):
        add(ref, 1, net_a, "Aggregate AON eFuse support component follows the released threshold/current/slew network.", aon_or)
        add(ref, 2, net_b, "Aggregate AON eFuse support component follows the released threshold/current/slew network.", aon_or)

    # BQ25798 charger/power path.
    bq = "TI BQ25798 datasheet plus Ducktop2 single-input charger contract"
    for pin, net in {
        1: "/Power & Battery/STAT_DRV",
        2: "/Power & Battery/VBUS_COMBINED",
        3: "/Power & Battery/VBUS_COMBINED",
        4: "/Power & Battery/BTST1_NODE",
        5: "/Power & Battery/REGN",
        8: "/Power & Battery/VBUS_COMBINED",
        9: "/Power & Battery/VBUS_COMBINED",
        10: "GND",
        11: "GND",
        12: "/Power & Battery/PMIC_QON_PIN",
        13: "/Power & Battery/CHG_CE_HW_N",
        14: "/I2C_SCL",
        15: "/I2C_SDA",
        16: "/Power & Battery/CHG_TS_FIXED",
        17: "/Power & Battery/ILIM_SET",
        18: "/Power & Battery/BATP_SENSE",
        19: "/Power & Battery/BTST2_NODE",
        20: "/Power & Battery/PROG_SET",
        21: "/CHG_INT_N",
        22: "/Power & Battery/BAT_CHARGER",
        23: "/Power & Battery/BAT_CHARGER",
        24: "/Power & Battery/SDRV_GATE",
        25: "/VSYS",
        26: "/Power & Battery/SW2",
        27: "GND",
        28: "/Power & Battery/SW1",
        29: "/Power & Battery/PMID",
    }.items():
        add("U2", pin, net, "BQ25798 wired as charger/NVDC path for protected 3S pack; VAC1/VAC2 tied to VBUS and ACDRV pins grounded when no external input mux FETs are used.", bq)
    add_nc("U2", 6, "D+ must remain open because the upstream adapter is selected after independent PD negotiation.", bq)
    add_nc("U2", 7, "D- must remain open because the upstream adapter is selected after independent PD negotiation.", bq)
    add("R16", 1, "/Power & Battery/REGN", "Fixed non-sensing TS divider top is biased from REGN.", bq)
    add("R16", 2, "/Power & Battery/CHG_TS_FIXED", "Fixed TS divider drives the charger's TS input.", bq)
    add("R705", 1, "/Power & Battery/CHG_TS_FIXED", "Fixed TS divider bottom holds a valid room-temperature ratio.", bq)
    add("R705", 2, "GND", "Fixed TS divider returns to ground.", bq)
    for pin in (1, 2, 3):
        add("Q25", pin, "/Power & Battery/BAT_CHARGER", "BQ25798 ship-FET source is on the charger-side BAT node.", bq)
    add("Q25", 4, "/Power & Battery/SDRV_GATE", "BQ25798 SDRV directly controls the qualified ship FET gate.", bq)
    add("Q25", 5, "/Power & Battery/PACK_POS_FUSED", "Ship-FET drain connects to the protected pack for electronic ship/hard-off.", bq)
    for ref, pin, net, note in (
        ("C725", 1, "/Power & Battery/PACK_POS_FUSED", "LTC4368 VOUT retains local capacitance even with the ship FET open."),
        ("C725", 2, "GND", "LTC4368 VOUT capacitor return."),
        ("R13", 1, "/PMIC_QON_ASSERT", "QON open-drain gate control defaults low."),
        ("R13", 2, "GND", "QON gate pull-down return."),
        ("Q702", 1, "/PMIC_QON_ASSERT", "Active-high EC pulse drives the QON open-drain gate."),
        ("Q702", 2, "GND", "QON open-drain source."),
        ("Q702", 3, "/Power & Battery/PMIC_QON_PIN", "QON open-drain drain; no dead-rail pull-up is allowed."),
        ("D715", 1, "/CASE_PWRBTN_N", "Case-button cathode shared only by the two isolation diodes."),
        ("D715", 2, "/Power & Battery/PMIC_QON_PIN", "Case button can wake the BQ25798 through a Schottky anode."),
        ("D716", 1, "/CASE_PWRBTN_N", "Case-button cathode shared only by the two isolation diodes."),
        ("D716", 2, "/MU_PWRBTN_N", "Case button reaches Mu PWRBTN through an independent Schottky anode."),
    ):
        add(ref, pin, net, note, bq)
    for ref, pin, net, note in (
        ("R14", 1, "/Power & Battery/REGN", "REGN pulls charger CE inactive by default."),
        ("R14", 2, "/Power & Battery/CHG_CE_HW_N", "Hardware CE defaults high, disabling charging."),
        ("Q700", 1, "/CHG_ENABLE", "Active-high EC charger-enable gate."),
        ("Q700", 2, "GND", "Charger-enable NMOS source."),
        ("Q700", 3, "/Power & Battery/CHG_CE_HW_N", "NMOS pulls BQ25798 CE low only after validation."),
        ("R719", 1, "/CHG_ENABLE", "Charger enable defaults low."),
        ("R719", 2, "GND", "Charger-enable pull-down return."),
    ):
        add(ref, pin, net, note, bq)

    # BQ34Z100-G1 fuel gauge.
    fg = "TI BQ34Z100-G1 datasheet plus Ducktop2 protected-pack fuel-gauge contract"
    for pin, net in {
        1: "/BQ_ALERT",
        2: "unconnected",
        3: "/Power & Battery/FG_P1_TIE",
        4: "/Power & Battery/FG_BAT_SENSE",
        5: "/Power & Battery/FG_CE",
        6: "/MCU_3V3",
        7: "/Power & Battery/FG_REG25",
        8: "/Power & Battery/FG_VSS",
        9: "/Power & Battery/FG_SRP",
        10: "/Power & Battery/FG_SRN",
        11: "/Power & Battery/FG_TS",
        12: "unconnected",
        13: "/I2C_SCL",
        14: "/I2C_SDA",
    }.items():
        if net == "unconnected":
            add_nc("U10", pin, "Unused BQ34Z100-G1 optional pin intentionally left NC.", fg)
        else:
            add("U10", pin, net, "Fuel gauge uses pack divider, shunt sense, internal temperature mode, 3.3 V host rail, and EC I2C.", fg)
    add("R855", 1, "/Power & Battery/FG_TS", "Unused external fuel-gauge TS input is pulled low.", fg)
    add("R855", 2, "/Power & Battery/FG_VSS", "TS pulldown returns to the gauge Kelvin VSS node.", fg)

    # EC buck and core STM32 pins that are easy to get catastrophically wrong.
    stm = "ST STM32F407 datasheet plus Ducktop2 EC core contract"
    add_many("U4", [6, 11, 19, 21, 22, 28, 50, 75, 100], "/MCU_3V3", "STM32 VDD/VBAT/VDDA pins require 3.3 V rail.", stm)
    add_many("U4", [10, 20, 27, 74, 99], "GND", "STM32 VSS/VSSA pins require ground.", stm)
    for pin, net in {49: "/EC & MCU/VCAP1_NODE", 73: "/EC & MCU/VCAP2_NODE", 94: "/EC & MCU/BOOT0_NET", 14: "/EC & MCU/NRST_NET", 72: "/EC & MCU/SWDIO_NET", 76: "/EC & MCU/SWCLK_NET"}.items():
        add("U4", pin, net, "STM32 reset, boot, SWD, and VCAP pins follow the EC core contract.", stm)
    for pin, net in {8: "/EC & MCU/LSE_IN", 9: "/EC & MCU/LSE_OUT",
                     12: "/EC & MCU/HSE_IN", 13: "/EC & MCU/HSE_OUT"}.items():
        add("U4", pin, net, "STM32 oscillator pin follows the qualified prototype oscillator contract.", stm)
    for pin, net, requirement in [
        (47, "/RADIO_VHF_UART_TX", "PB10 is USART3_TX for VHF radio hardware UART."),
        (48, "/RADIO_VHF_UART_RX", "PB11 is USART3_RX for VHF radio hardware UART."),
        (63, "/RADIO_UHF_UART_TX", "PC6 is USART6_TX for UHF radio hardware UART."),
        (64, "/RADIO_UHF_UART_RX", "PC7 is USART6_RX for UHF radio hardware UART."),
        (67, "/WIFI_W_DISABLE1_N_EC", "PA8 drives the powered-off-isolated WLAN disable input."),
        (68, "/GNSS_UART_TX", "PA9 is USART1_TX for GNSS hardware UART."),
        (69, "/GNSS_UART_RX", "PA10 is USART1_RX for GNSS hardware UART."),
        (77, "/WIFI_W_DISABLE2_N_EC", "PA15 drives the powered-off-isolated Bluetooth disable input."),
        (36, "/TRACKPAD_FAULT_N", "PB1 reads the trackpad Type-C power-switch fault output."),
        (44, "/MU_12V_ENABLE", "PE13 explicitly enables the regulated Mu 12 V rail after source qualification."),
        (45, "/MU_S0_HIGH", "PE14 reads the Mu PSON/S0 status signal."),
        (46, "/MU_12V_PG", "PE15 reads the regulated Mu 12 V power-good signal."),
        (42, "/AUDIO_MIC_EN", "PE11 controls the fail-off microphone rail; the privacy indicator monitors the actual MIC_2V8 output."),
        (15, "/KB_RGB_PWR_EN", "PC0 enables both the current-limited keyboard RGB rail and its level buffer."),
        (16, "/KB_RGB_FAULT_N", "PC1 reads the active-low keyboard RGB power-switch fault output."),
        (62, "/KB_RGB_DATA_3V3", "PD15/TIM4_CH4 emits the future keyboard addressable-RGB data stream."),
        (33, "/PD1_VALID_N", "PC4 reads the left dual-role sink-path validity input."),
        (37, "/PD2_VALID_N", "PB2 reads the right dual-role sink-path validity input."),
        (39, "/PD1_TCPC_IRQ_N", "PE8 receives the left TPS25751A interrupt."),
        (90, "/PD2_TCPC_IRQ_N", "PB4 receives the right TPS25751A interrupt."),
        (91, "/RADIO_DB_PWR_EN", "PB5 enables the optional radio daughterboard power switch."),
        (96, "/PD_PROTECT_FAULT_N", "PB8 receives the aggregate dual-role protection fault."),
        (7, "/EC & MCU/SOURCE_MGR_INT_N", "PE5 receives the always-on source-manager interrupt."),
        (17, "/RADIO_VHF_RF_SEL_3V3", "PC2 drives the VHF RF-select level shifter."),
        (18, "/RADIO_UHF_RF_SEL_3V3", "PC3 drives the UHF RF-select level shifter."),
        (29, "/CHG_ENABLE", "PA4 explicitly releases the fail-off BQ25798 CE hardware path."),
        (26, "/PMIC_QON_ASSERT", "PA3 emits an active-high pulse into the fail-safe QON open-drain transistor."),
        (51, "/EC & MCU/SERVICE_MUX_RESET_REQ_N", "PD8 requests a service-I2C-mux reset; U46 also forces reset during EC NRST."),
        (89, "/INTERNAL_USB_VBUS_FAULT_N", "PB3 reads the physical internal-host VBUS switch fault output."),
    ]:
        add("U4", pin, net, requirement, stm)
    for pin, net in {1: "GND", 2: "/EC & MCU/BUCK_SW", 3: "/EC_AON_IN", 4: "/EC & MCU/BUCK_FB", 6: "/EC & MCU/BUCK_BOOT"}.items():
        add("U5", pin, net, "TPS54202 generates MCU_3V3 from the diode-ORed always-on source.", "TI TPS54202 datasheet plus Ducktop2 EC buck contract")
    add_nc("U5", 5, "TPS54202 EN is intentionally floated; its internal pull-up enables the always-on EC rail.", "TI TPS54202 datasheet")
    add("L3", 1, "/EC & MCU/BUCK_SW", "10uH XGL5030 switch-side connection.", "TI TPS54202 and Coilcraft XGL5030 datasheets")
    add("L3", 2, "/MCU_3V3", "10uH XGL5030 filtered-output connection.", "TI TPS54202 and Coilcraft XGL5030 datasheets")
    source_mgr = "TI TCA9539 datasheet plus Ducktop2 warm-reset fail-off source-manager contract"
    for pin, net in {
        1: "/EC & MCU/SOURCE_MGR_INT_N", 2: "GND", 3: "/EC & MCU/NRST_NET",
        4: "/PD1_PATH_EN", 5: "/PD2_PATH_EN", 6: "/EC & MCU/SOURCE_MGR_SPARE1",
        7: "/PD1_EFUSE_FAULT_N", 8: "/PD2_EFUSE_FAULT_N", 9: "/EC & MCU/SOURCE_MGR_SPARE2",
        10: "/PACK_FAULT_N", 11: "/AUX_FAULT_N", 12: "GND",
        13: "/PACK_RETRY_PULSE", 14: "/AUX_PGOOD",
        15: "/MAIN_USB_VALID_N", 16: "/MAIN_AUX_VALID_N",
        17: "/AON_FAULT_N", 18: "/RADIO_DB_PG",
        19: "/RADIO_DB_FAULT_N", 20: "/RADIO_DB_PRESENT_N",
        21: "GND", 22: "/I2C_SCL", 23: "/I2C_SDA", 24: "/MCU_3V3",
    }.items():
        add("U44", pin, net,
            "TCA9539 RESET follows EC NRST; all ports return to inputs and external eFuse SHDN pull-downs keep every PD path off until restarted firmware validates one source.",
            source_mgr)
    reset_gate = "TI SN74LVC1G08 and TCA9548A datasheets plus Ducktop2 EC-reset recovery contract"
    for pin, net in {
        1: "/EC & MCU/NRST_NET", 2: "/EC & MCU/SERVICE_MUX_RESET_REQ_N",
        3: "GND", 4: "/SERVICE_MUX_RESET_N", 5: "/MCU_3V3",
    }.items():
        add("U46", pin, net,
            "Hardware AND gate asserts the TCA9548A reset whenever EC NRST or the firmware reset request is low.",
            reset_gate)
    for pin, net in {1: "/EC & MCU/EC_SWD_VTREF", 2: "/EC & MCU/SWDIO_NET",
                     3: "/EC & MCU/NRST_NET", 4: "/EC & MCU/SWCLK_NET", 5: "GND"}.items():
        add("J4", pin, net, "TC2030 Cortex SWD target pinout; VTref is sense-only through 10k.", "Tag-Connect TC2030-CTX pinout")
    add_nc("J4", 6, "SWO is not routed on the EC TC2030 target.", "Tag-Connect TC2030-CTX pinout")

    osc = "STM32F407 datasheet, ST AN2867, and exact Jauch/Epson crystal datasheets"
    for pin, net in {1: "/EC & MCU/HSE_IN", 2: "GND",
                     3: "/EC & MCU/HSE_XTAL_OUT", 4: "GND"}.items():
        add("Y1", pin, net, "Jauch HSE crystal active pins and both grounded lid pads.", osc)
    add("C32", 1, "/EC & MCU/HSE_IN", "10pF C0G HSE input load capacitor.", osc)
    add("C32", 2, "GND", "HSE input load capacitor return.", osc)
    add("C33", 1, "/EC & MCU/HSE_XTAL_OUT", "10pF C0G HSE output load capacitor.", osc)
    add("C33", 2, "GND", "HSE output load capacitor return.", osc)
    add("R37", 1, "/EC & MCU/HSE_XTAL_OUT", "Zero-ohm prototype HSE drive/tuning position, crystal side.", osc)
    add("R37", 2, "/EC & MCU/HSE_OUT", "Zero-ohm prototype HSE drive/tuning position, MCU side.", osc)
    add("Y2", 1, "/EC & MCU/LSE_IN", "Epson 32.768kHz crystal input pin.", osc)
    add("Y2", 2, "/EC & MCU/LSE_OUT", "Epson 32.768kHz crystal output pin.", osc)
    add("C34", 1, "/EC & MCU/LSE_IN", "6.8pF C0G LSE input load capacitor.", osc)
    add("C34", 2, "GND", "LSE input load capacitor return.", osc)
    add("C35", 1, "/EC & MCU/LSE_OUT", "6.8pF C0G LSE output load capacitor.", osc)
    add("C35", 2, "GND", "LSE output load capacitor return.", osc)
    for pin, net in {1: "GND", 2: "/CASE_PWRBTN_N", 3: "/MU_RSTBTN_N"}.items():
        add("J16", pin, net, "Three-wire JST-SH case-button harness; power is diode-isolated to charger QON and Mu PWRBTN.", "JST SM03B-SRSS-TB and Ducktop2 case-control contract")

    # LattePanda Mu carrier and rails.
    mu = "Official LattePanda Mu edge pinout, DFLT BIOS mapping, and Ducktop2 allocation"
    for pin in range(250, 261):
        add("A1", pin, "/MU_12V", "Mu VIN is supplied by the regulated 12 V buck-boost stage shared with the released blower.", mu)
    add("J9", 1, "/Mu Carrier/RTC_BAT", "Keyed RTC backup-cell positive contact.", mu)
    add("J9", 2, "GND", "RTC backup-cell return.", mu)
    add("TP5", 1, "/SYS_5V", "System 5 V fixture point.", "Ducktop2 first-article DFT contract")
    add("TP6", 1, "/SYS_3V3", "System 3.3 V fixture point.", "Ducktop2 first-article DFT contract")
    add("TP8", 1, "/MU_12V", "Regulated Mu/fan rail fixture point.", "Ducktop2 first-article DFT contract")
    add("TP12", 1, "/MU_12V_PG", "Mu 12 V power-good fixture point.", "Ducktop2 first-article DFT contract")
    tps = "TI TPS552892 datasheet and TPS552892EVM 12 V reference topology"
    for pin, net in {
        1: "/Mu Carrier/MU12_EN_UVLO", 2: "/Mu Carrier/MU12_MODE",
        3: "/MU_12V_PG", 4: "/Mu Carrier/MU12_CC_N",
        5: "/Mu Carrier/MU12_DITH", 6: "/Mu Carrier/MU12_FSW", 7: "/VSYS",
        8: "/Mu Carrier/MU12_SW1", 9: "GND", 10: "/Mu Carrier/MU12_SW2",
        11: "/Mu Carrier/MU12_PRE_SENSE", 12: "/Mu Carrier/MU12_ISP",
        13: "/Mu Carrier/MU12_ISN", 14: "/Mu Carrier/MU12_FB",
        15: "/Mu Carrier/MU12_COMP", 17: "GND", 18: "/Mu Carrier/MU12_VCC",
        19: "/Mu Carrier/MU12_BOOT2", 20: "/Mu Carrier/MU12_BOOT1",
        21: "/Mu Carrier/MU12_EXTVCC",
    }.items():
        add("U750", pin, net, "TPS552892 pin follows the EVM-derived 12 V buck-boost topology.", tps)
    add_nc("U750", 16, "CDC output is intentionally unused.", tps)
    add("L750", 1, "/Mu Carrier/MU12_SW1", "Buck-boost inductor terminates at SW1.", tps)
    add("L750", 2, "/Mu Carrier/MU12_SW2", "Buck-boost inductor terminates at SW2.", tps)
    add("RS750", 1, "/Mu Carrier/MU12_PRE_SENSE", "Output-current shunt converter side.", tps)
    add("RS750", 2, "/MU_12V", "Output-current shunt load side shared by Mu and released blower.", tps)
    add("Q750", 1, "/Mu Carrier/MU12_FORCE_OFF", "Force-off NMOS gate defaults high until the EC explicitly enables the Mu rail.", tps)
    add("Q750", 2, "GND", "Force-off NMOS source.", tps)
    add("Q750", 3, "/Mu Carrier/MU12_EN_UVLO", "Force-off NMOS clamps EN/UVLO low by default.", tps)
    add("Q751", 1, "/MU_12V_ENABLE", "EC active-high enable drives the release NMOS gate.", tps)
    add("Q751", 2, "GND", "Release NMOS source.", tps)
    add("Q751", 3, "/Mu Carrier/MU12_FORCE_OFF", "Release NMOS pulls the force-off gate low only after firmware qualification.", tps)
    add("R761", 1, "/Mu Carrier/MU12_FORCE_OFF", "Force-off gate has a defined divider node.", tps)
    add("R761", 2, "GND", "Force-off divider low side.", tps)
    add("R766", 1, "/VSYS", "VSYS biases the Mu force-off gate high when the EC is reset or unpowered.", tps)
    add("R766", 2, "/Mu Carrier/MU12_FORCE_OFF", "Force-off divider high side.", tps)
    add("R767", 1, "/MU_12V_ENABLE", "EC Mu-enable output has a reset-state pull-down.", tps)
    add("R767", 2, "GND", "Mu-enable pull-down return.", tps)
    add("R768", 1, "/MCU_3V3", "LattePanda PSON requires an external 10k pull-up.", mu)
    add("R768", 2, "/MU_S0_HIGH", "Pulled-up PSON is used only as a weak status/control signal.", mu)
    for pin, net in {
        13: "/Mu Carrier/USBC1_SSTX_RAW_P", 15: "/Mu Carrier/USBC1_SSTX_RAW_N",
        16: "/USBC1_SSRX_P", 18: "/USBC1_SSRX_N", 73: "/USBC1_DM", 75: "/USBC1_DP",
        19: "/Mu Carrier/USBC2_SSTX_RAW_P", 21: "/Mu Carrier/USBC2_SSTX_RAW_N",
        22: "/USBC2_SSRX_P", 24: "/USBC2_SSRX_N", 70: "/USBC2_DP", 72: "/USBC2_DM",
        129: "/MU_USB_OC_N", 79: "/EC_HOST_USB_DM", 81: "/EC_HOST_USB_DP",
        109: "/AUDIO_USB_DM", 111: "/AUDIO_USB_DP", 76: "/MAKER_USB_DP", 78: "/MAKER_USB_DM",
        82: "/TRACKPAD_USB_DP", 84: "/TRACKPAD_USB_DM",
        37: "/Mu Carrier/PCIE_M_L0_TX_RAW_P", 39: "/Mu Carrier/PCIE_M_L0_TX_RAW_N",
        40: "/Mu Carrier/PCIE_M_L0_RX_P", 42: "/Mu Carrier/PCIE_M_L0_RX_N",
        43: "/Mu Carrier/PCIE_M_L1_TX_RAW_P", 45: "/Mu Carrier/PCIE_M_L1_TX_RAW_N",
        46: "/Mu Carrier/PCIE_M_L1_RX_P", 48: "/Mu Carrier/PCIE_M_L1_RX_N",
        49: "/Mu Carrier/PCIE_M_L2_TX_RAW_P", 51: "/Mu Carrier/PCIE_M_L2_TX_RAW_N",
        52: "/Mu Carrier/PCIE_M_L2_RX_P", 54: "/Mu Carrier/PCIE_M_L2_RX_N",
        55: "/Mu Carrier/PCIE_M_L3_TX_RAW_P", 57: "/Mu Carrier/PCIE_M_L3_TX_RAW_N",
        58: "/Mu Carrier/PCIE_M_L3_RX_P", 60: "/Mu Carrier/PCIE_M_L3_RX_N",
        61: "/GBE_HOST_TX_P", 63: "/GBE_HOST_TX_N",
        64: "/GBE_HOST_RX_P", 66: "/GBE_HOST_RX_N",
        94: "/GBE_REFCLK_P", 96: "/GBE_REFCLK_N", 102: "/GBE_CLKREQ_N",
        97: "/Mu Carrier/PCIE_M_REFCLK_SRC_P", 99: "/Mu Carrier/PCIE_M_REFCLK_SRC_N",
    }.items():
        add("A1", pin, net, "Mu USB/PCIe allocation follows the stock DFLT BIOS lane map.", mu)
    for pin in [112, 114, 169, 171, 183, 191, 193, 197, 199, 203, 205, 209, 211, 215, 217]:
        add_nc("A1", pin, "USB2_P6 is reserved and DDIB is unused because the panel uses onboard eDP.", mu)
    tps5 = "TI TPS56637 datasheet and RPA0010A package drawing"
    for pin, net in {
        1: "/Mu Carrier/BUCK5_EN", 2: "/Mu Carrier/BUCK5_FB", 3: "GND",
        4: "/Mu Carrier/SYS_5V_PG", 6: "/Mu Carrier/BUCK5_SW",
        7: "/Mu Carrier/BUCK5_BOOT", 8: "/VSYS", 9: "GND", 10: "GND",
    }.items():
        add("U6", pin, net, "TPS56637 6A-class SYS_5V converter pin contract.", tps5)
    add_nc("U6", 5, "TPS56637 NC pin intentionally left unconnected.", tps5)
    add("L4", 1, "/Mu Carrier/BUCK5_SW", "XAL7070 switch-node side.", tps5)
    add("L4", 2, "/SYS_5V", "XAL7070 regulated-output side.", tps5)
    for pin, net in {
        1: "/Mu Carrier/BUCK33_EN", 2: "/Mu Carrier/BUCK33_FB", 3: "GND",
        4: "/Mu Carrier/SYS_3V3_PG", 6: "/Mu Carrier/BUCK33_SW",
        7: "/Mu Carrier/BUCK33_BOOT", 8: "/VSYS", 9: "GND", 10: "GND",
    }.items():
        add("U7", pin, net, "TPS56637 6A-class SYS_3V3 converter pin contract.", tps5)
    add_nc("U7", 5, "TPS56637 NC pin intentionally left unconnected.", tps5)
    host_active = "TI SN74LVC1G08 datasheet plus Ducktop2 qualified-host-state contract"
    for pin, net in {
        1: "/MU_S0_HIGH", 2: "/MU_12V_PG", 3: "GND",
        4: "/MU_HOST_ACTIVE", 5: "/MCU_3V3",
    }.items():
        add("U769", pin, net, "Host-dependent loads enable only when Mu S0 and the regulated Mu rail are both valid.", host_active)
    internal_vbus = "TI TPS2553D and TLV803EA43RDBZR datasheets plus Ducktop2 4.38V physical internal-host VBUS contract"
    for pin, net in {
        1: "/SYS_5V", 2: "GND", 3: "/MU_HOST_ACTIVE",
        4: "/INTERNAL_USB_VBUS_FAULT_N", 5: local("Mu Carrier", "INTERNAL_USB_VBUS_ILIM"),
        6: local("Mu Carrier", "INTERNAL_USB_VBUS"),
    }.items():
        add("U770", pin, net, "Carrier creates a protected physical upstream VBUS for permanently attached Mu USB devices.", internal_vbus)
    for pin, net in {1: "/INTERNAL_USB_VBUS_VALID", 2: "GND", 3: local("Mu Carrier", "INTERNAL_USB_VBUS")}.items():
        add("U771", pin, net, "4.38V supervisor qualifies the actual carrier-generated internal USB VBUS.", internal_vbus)
    for ref, net_a, net_b in (
        ("R773", local("Mu Carrier", "INTERNAL_USB_VBUS_ILIM"), "GND"),
        ("R774", "/MCU_3V3", "/INTERNAL_USB_VBUS_FAULT_N"),
        ("R775", "/MCU_3V3", "/INTERNAL_USB_VBUS_VALID"),
        ("C794", "/SYS_5V", "GND"),
        ("C830", local("Mu Carrier", "INTERNAL_USB_VBUS"), "GND"),
        ("C831", local("Mu Carrier", "INTERNAL_USB_VBUS"), "GND"),
    ):
        add(ref, 1, net_a, "Physical internal-host VBUS support network.", internal_vbus)
        add(ref, 2, net_b, "Physical internal-host VBUS support network.", internal_vbus)
    for ref, target in (("TP13", local("Mu Carrier", "INTERNAL_USB_VBUS")),
                        ("TP14", "/INTERNAL_USB_VBUS_VALID"),
                        ("TP15", "/INTERNAL_USB_VBUS_FAULT_N")):
        add(ref, 1, target, "First-article physical internal-host VBUS fixture point.", internal_vbus)
    pcie_power = "TI TPS22975N datasheet plus Ducktop2 S0-only PCIe endpoint power contract"
    for pin, net in {
        1: "/SYS_3V3", 2: "/SYS_3V3", 3: "/MU_HOST_ACTIVE", 4: "/SYS_3V3",
        5: "GND", 6: local("Mu Carrier", "PCIE_3V3_CT"),
        7: "/PCIE_3V3", 8: "/PCIE_3V3", 9: "GND",
    }.items():
        add("U772", pin, net, "All PCIe endpoints are unpowered unless the Mu host is fully active.", pcie_power)
    for ref, first, second in (
        ("R776", "/MU_HOST_ACTIVE", "GND"),
        ("C832", "/SYS_3V3", "GND"),
        ("C833", local("Mu Carrier", "PCIE_3V3_CT"), "GND"),
        ("C834", "/PCIE_3V3", "GND"), ("C835", "/PCIE_3V3", "GND"),
        ("C836", "/PCIE_3V3", "GND"), ("C837", "/PCIE_3V3", "GND"),
    ):
        add(ref, 1, first, "S0-switched PCIe endpoint rail support network.", pcie_power)
        add(ref, 2, second, "S0-switched PCIe endpoint rail support network.", pcie_power)
    for pin, net in {
        41: "/Mu Carrier/PCIE_M_L0_RX_N", 43: "/Mu Carrier/PCIE_M_L0_RX_P",
        47: "/Mu Carrier/PCIE_M_L0_TX_N", 49: "/Mu Carrier/PCIE_M_L0_TX_P",
        29: "/Mu Carrier/PCIE_M_L1_RX_N", 31: "/Mu Carrier/PCIE_M_L1_RX_P",
        35: "/Mu Carrier/PCIE_M_L1_TX_N", 37: "/Mu Carrier/PCIE_M_L1_TX_P",
        17: "/Mu Carrier/PCIE_M_L2_RX_N", 19: "/Mu Carrier/PCIE_M_L2_RX_P",
        23: "/Mu Carrier/PCIE_M_L2_TX_N", 25: "/Mu Carrier/PCIE_M_L2_TX_P",
        5: "/Mu Carrier/PCIE_M_L3_RX_N", 7: "/Mu Carrier/PCIE_M_L3_RX_P",
        11: "/Mu Carrier/PCIE_M_L3_TX_N", 13: "/Mu Carrier/PCIE_M_L3_TX_P",
        53: "/Mu Carrier/PCIE_M_REFCLK_N", 55: "/Mu Carrier/PCIE_M_REFCLK_P",
        50: "/Mu Carrier/PCIE_M_PERST_N", 52: "/Mu Carrier/PCIE_M_CLKREQ_N", 54: "/PCIE_WAKE_N",
    }.items():
        add("J10", pin, net, "M.2 M-key PCIe Gen3 x4 lane and sideband contract.", mu)
    ekey_power = "Ducktop2 S0-only PCIe endpoint power contract"
    add("F10", 1, "/PCIE_3V3", "E-key input is removed whenever the Mu host is not fully active.", ekey_power)
    add("F10", 2, local("Radio/OLED/GNSS", "WIFI_3V3"), "E-key local rail is fused after the common PCIe switch.", ekey_power)
    for ref, signal in (("R170", "WIFI_W_DISABLE1_N"), ("R171", "WIFI_W_DISABLE2_N")):
        add(ref, 1, local("Radio/OLED/GNSS", "WIFI_3V3"), "E-key pull-up cannot back-power an unpowered module.", ekey_power)
        add(ref, 2, local("Radio/OLED/GNSS", signal), "E-key module-side radio-disable sideband.", ekey_power)
    for pin, net in {
        1: "/WIFI_W_DISABLE1_N_EC", 7: local("Radio/OLED/GNSS", "WIFI_W_DISABLE1_N"),
        6: "/WIFI_W_DISABLE2_N_EC", 2: local("Radio/OLED/GNSS", "WIFI_W_DISABLE2_N"),
        3: "GND", 4: "GND", 8: local("Radio/OLED/GNSS", "WIFI_3V3"),
    }.items():
        add("U170", pin, net, "Radio-powered Ioff buffer isolates the E-key controls while its rail is off.", "TI SN74LVC3G34 datasheet")
    add_nc("U170", 5, "Unused third buffer output.", "TI SN74LVC3G34 datasheet")
    for ref, net in (("R198", "/WIFI_W_DISABLE1_N_EC"), ("R199", "/WIFI_W_DISABLE2_N_EC")):
        add(ref, 1, net, "EC-reset default holds the corresponding radio disabled.", "Ducktop2 E-key fail-disable contract")
        add(ref, 2, "GND", "Fail-disable pull-down return.", "Ducktop2 E-key fail-disable contract")
    add("C187", 1, local("Radio/OLED/GNSS", "WIFI_3V3"), "E-key control-isolator bypass.", "TI SN74LVC3G34 datasheet")
    add("C187", 2, "GND", "E-key control-isolator bypass return.", "TI SN74LVC3G34 datasheet")

    # Native Type-C host ports directly use Mu HSIO0/1 and USB2_P2/P4.
    for port, tps, mux, conn in [(1, "U21", "U22", "J11"), (2, "U31", "U32", "J12")]:
        native = f"/USBC{port}"
        usb = f"USB{port}"
        sheet = "Native USB-C I/O"
        tps_src = "TI TPS25810 datasheet plus Ducktop2 native Type-C DFP contract"
        branch = f"U{10 + port * 10}"
        rbase = 50 + port * 20
        pre_vbus = local(sheet, f"{usb}_5V_PRE")
        ilim = local(sheet, f"{usb}_ILIM")
        branch_src = "TI TPS2553 datasheet plus TPS25810 input-capacitance isolation contract"
        for pin, net in {
            1: "/SYS_5V", 2: "GND", 3: "/MU_HOST_ACTIVE",
            4: "/MU_USB_OC_N", 5: ilim, 6: pre_vbus,
        }.items():
            add(branch, pin, net, "Current-limited branch isolates the TPS25810 input reservoir from shared SYS_5V.", branch_src)
        add(f"R{rbase}", 1, ilim, "TPS2553 current-limit programming resistor.", branch_src)
        add(f"R{rbase}", 2, "GND", "TPS2553 current-limit resistor return.", branch_src)
        for ref, net, note in (
            (f"C{rbase}", "/SYS_5V", "TPS2553 input bypass"),
            (f"C{rbase + 1}", pre_vbus, "TPS25810 local input bypass"),
            (f"C{rbase + 5}", local(sheet, f"{usb}_VBUS"), "connector-side VBUS capacitance"),
            (f"C{rbase + 8}", pre_vbus, "isolated TPS25810 input reservoir"),
        ):
            add(ref, 1, net, f"{note} positive rail.", branch_src)
            add(ref, 2, "GND", f"{note} return.", branch_src)
        for pin, net in {
            1: "/MU_USB_OC_N", 2: pre_vbus, 3: pre_vbus, 4: pre_vbus, 5: "/SYS_3V3",
            6: "/MU_HOST_ACTIVE", 7: "GND", 8: "GND", 9: local(sheet, f"{usb}_REF_RTN"),
            10: local(sheet, f"{usb}_REF"), 11: local(sheet, f"{usb}_CC1"), 12: "GND",
            13: local(sheet, f"{usb}_CC2"), 14: local(sheet, f"{usb}_VBUS"),
            15: local(sheet, f"{usb}_VBUS"), 18: local(sheet, f"{usb}_POL_N"), 21: "GND",
        }.items():
            add(tps, pin, net, "TPS25810 provides DFP CC/VBUS/VCONN and wire-OR fault reporting.", tps_src)
        for pin in [16, 17, 19, 20]:
            add_nc(tps, pin, "Unused TPS25810 status output intentionally NC.", tps_src)

        mux_src = "TI HD3SS6126 datasheet (10Gbps high-bandwidth path) plus Ducktop2 native SuperSpeed orientation contract"
        for pin in [1, 2, 3, 4, 5, 18, 35, 36, 37, 38, 39, 40, 41, 42, 7, 8, 31, 32, 33, 34]:
            add_nc(mux, pin, "Unused/NC HD3SS6126 pin; USB2 bypasses the mux.", mux_src)
        for pin, net in {
            6: "/SYS_3V3", 9: local(sheet, f"{usb}_POL_N"), 10: "GND",
            11: f"{native}_SSTX_P", 12: f"{native}_SSTX_N", 13: "/SYS_3V3", 14: "GND",
            15: f"{native}_SSRX_P", 16: f"{native}_SSRX_N", 17: "GND", 19: "GND",
            20: "/SYS_3V3", 21: "GND", 22: local(sheet, f"{usb}_RX1_N_CONN"),
            23: local(sheet, f"{usb}_RX1_P_CONN"), 24: local(sheet, f"{usb}_TX1_N_CONN"),
            25: local(sheet, f"{usb}_TX1_P_CONN"), 26: local(sheet, f"{usb}_RX2_N_CONN"),
            27: local(sheet, f"{usb}_RX2_P_CONN"), 28: local(sheet, f"{usb}_TX2_N_CONN"),
            29: local(sheet, f"{usb}_TX2_P_CONN"), 30: "/SYS_3V3", 43: "GND",
        }.items():
            add(mux, pin, net, "HD3SS6126 routes native Mu SuperSpeed through the Type-C orientation sets.", mux_src)

        conn_src = "USB Type-C receptacle pinout plus Ducktop2 native host-port contract"
        add_many(conn, ["A1", "A12", "B1", "B12", "SH"], "GND", "USB-C shell/ground pins.", conn_src)
        add_many(conn, ["A4", "A9", "B4", "B9"], local(sheet, f"{usb}_VBUS"), "USB-C VBUS pins sourced by TPS25810.", conn_src)
        add(conn, "A5", local(sheet, f"{usb}_CC1"), "USB-C CC1 to TPS25810.", conn_src)
        add(conn, "B5", local(sheet, f"{usb}_CC2"), "USB-C CC2 to TPS25810.", conn_src)
        add_many(conn, ["A6", "B6"], f"{native}_DP", "Native USB2 D+ tied to both Type-C orientations.", conn_src)
        add_many(conn, ["A7", "B7"], f"{native}_DM", "Native USB2 D- tied to both Type-C orientations.", conn_src)
        for pin, net in {
            "A2": local(sheet, f"{usb}_TX1_P_CONN"), "A3": local(sheet, f"{usb}_TX1_N_CONN"),
            "A10": local(sheet, f"{usb}_RX2_N_CONN"), "A11": local(sheet, f"{usb}_RX2_P_CONN"),
            "B2": local(sheet, f"{usb}_TX2_P_CONN"), "B3": local(sheet, f"{usb}_TX2_N_CONN"),
            "B10": local(sheet, f"{usb}_RX1_N_CONN"), "B11": local(sheet, f"{usb}_RX1_P_CONN"),
        }.items():
            add(conn, pin, net, "USB-C SuperSpeed pins route through HD3SS6126.", conn_src)
        add_nc(conn, "A8", "SBU unused on native host data port.", conn_src)
        add_nc(conn, "B8", "SBU unused on native host data port.", conn_src)

    pd_selector = "ADI LTC4417 Rev G plus Vishay SiSS4409DN datasheets"
    for pin, net in {
        3: "GND", 4: "/Power Inputs/PD1_UV", 5: "/Power Inputs/PD1_OV",
        6: "/Power Inputs/PD2_UV", 7: "/Power Inputs/PD2_OV",
        8: "/Power Inputs/PD3_UV", 9: "/Power Inputs/PD3_OV",
        10: "/PD1_VALID_N", 11: "/PD2_VALID_N", 12: "/PD3_VALID_N", 13: "GND",
        15: "/USB_PD_SELECTED", 16: "/Power Inputs/PD3_GATE", 17: "/Power Inputs/PD3_FET_COMMON",
        18: "/Power Inputs/PD2_GATE", 19: "/Power Inputs/PD2_FET_COMMON",
        20: "/Power Inputs/PD1_GATE", 21: "/Power Inputs/PD1_FET_COMMON",
        22: "/Power Inputs/PD3_VBUS_GATED", 23: "/Power Inputs/PD2_VBUS_GATED", 24: "/Power Inputs/PD1_VBUS_GATED",
    }.items():
        add("U14", pin, net, "Three-input selector validates each 15 V contract, applies port priority, and drives an isolating PMOS pair.", pd_selector)
    for pin in (1, 2, 14):
        add_nc("U14", pin, "Unused control/status pin follows the always-on selector configuration.", pd_selector)
    for ref, valid in (("R736", "PD1_VALID_N"), ("R737", "PD2_VALID_N"), ("R738", "PD3_VALID_N")):
        add(ref, 1, "/MCU_3V3", "LTC4417 VALID output requires an always-on pull-up.", pd_selector)
        add(ref, 2, f"/{valid}", "Pulled-up active-low source-valid signal reaches the EC.", pd_selector)
    for idx, (qa, qb) in enumerate((("Q15", "Q16"), ("Q17", "Q18"), ("Q19", "Q20")), start=1):
        gate = f"/Power Inputs/PD{idx}_GATE"
        common = f"/Power Inputs/PD{idx}_FET_COMMON"
        gated = f"/Power Inputs/PD{idx}_VBUS_GATED"
        for ref, drain in ((qa, gated), (qb, "/USB_PD_SELECTED")):
            add(ref, 1, gate, "LTC4417 gate output drives both PMOS gates.", pd_selector)
            add_many(ref, [2, 3, 4], common, "Back-to-back pair shares this common-source node.", pd_selector)
            add(ref, 5, drain, "PMOS unified drain land terminates one side of the isolated adapter path.", pd_selector)
        base = 720 + (idx - 1) * 3
        for ref, net_a, net_b in (
            (f"R{base}", gated, f"/Power Inputs/PD{idx}_UV"),
            (f"R{base + 1}", f"/Power Inputs/PD{idx}_UV", f"/Power Inputs/PD{idx}_OV"),
            (f"R{base + 2}", f"/Power Inputs/PD{idx}_OV", "GND"),
        ):
            add(ref, 1, net_a, "LTC4417 15 V qualification ladder.", pd_selector)
            add(ref, 2, net_b, "LTC4417 15 V qualification ladder.", pd_selector)
    for ref, net in (
        ("C730", "/Power Inputs/PD1_VBUS_GATED"), ("C731", "/Power Inputs/PD2_VBUS_GATED"),
        ("C732", "/Power Inputs/PD3_VBUS_GATED"), ("C733", "/Power Inputs/PD1_FET_COMMON"),
        ("C734", "/Power Inputs/PD2_FET_COMMON"), ("C735", "/Power Inputs/PD3_FET_COMMON"),
        ("C736", "/USB_PD_SELECTED"), ("C737", "/USB_PD_SELECTED"),
    ):
        add(ref, 1, net, "LTC4417 input/source/output local bypass capacitor.", pd_selector)
        add(ref, 2, "GND", "Selector bypass capacitor returns to ground.", pd_selector)

    efuse_src = "TI TPS26630 datasheet plus Ducktop2 default-off PD-input contract"
    for idx, ref in enumerate(("U720", "U721", "U722"), start=1):
        raw = f"/PD{idx}_VBUS_RAW"
        gated = f"/Power Inputs/PD{idx}_VBUS_GATED"
        for pin, net in {
            1: raw, 2: raw, 5: raw,
            6: f"/Power Inputs/PD{idx}_EFUSE_UV",
            7: f"/Power Inputs/PD{idx}_EFUSE_OV", 8: "GND",
            9: f"/Power Inputs/PD{idx}_EFUSE_DVDT",
            10: f"/Power Inputs/PD{idx}_EFUSE_ILIM",
            12: f"/Power Inputs/PD{idx}_EFUSE_SHDN_N",
            14: f"/PD{idx}_EFUSE_FAULT_N", 15: "GND",
            17: gated, 18: gated, 25: "GND",
        }.items():
            add(ref, pin, net, "PD input is current-limited and held off by hardware until EC validation.", efuse_src)
        for pin in (3, 4, 11, 13, 16, 19, 20, 21, 22, 23, 24):
            add_nc(ref, pin, "Unused TPS26630 optional pin.", efuse_src)

    # External HDMI plus the internal USB trackpad.  The Intehill controller is
    # now a bench fixture/fallback and has no motherboard components.
    hdmi_src = "HDMI Type-A pinout plus Ducktop2 TCP0 external-output contract"
    for pin, name in {1: "D2_P", 3: "D2_N", 4: "D1_P", 6: "D1_N", 7: "D0_P", 9: "D0_N", 10: "CK_P", 12: "CK_N", 15: "SCL_CONN", 16: "SDA_CONN", 18: "5V", 19: "HPD_CONN"}.items():
        add("J30", pin, local("TCP0 External HDMI", f"EXT_HDMI_{name}"), "External HDMI signal/power pin follows the TCP0 output contract.", hdmi_src)
    add_many("J30", [2, 5, 8, 11, 17, "SH"], "GND", "HDMI shield/grounds.", hdmi_src)
    add_nc("J30", 13, "CEC is intentionally not implemented on this source port.", hdmi_src)
    add_nc("J30", 14, "HDMI utility pin not used.", hdmi_src)
    for source, connector, cref, rref, dref in (
        ("/TCP0_TX0_P", "EXT_HDMI_D2_P", "C150", "R150", "D150"),
        ("/TCP0_TX0_N", "EXT_HDMI_D2_N", "C151", "R151", "D151"),
        ("/TCP0_TXRX0_P", "EXT_HDMI_D1_P", "C152", "R152", "D152"),
        ("/TCP0_TXRX0_N", "EXT_HDMI_D1_N", "C153", "R153", "D153"),
        ("/TCP0_TX1_P", "EXT_HDMI_D0_P", "C154", "R154", "D154"),
        ("/TCP0_TX1_N", "EXT_HDMI_D0_N", "C155", "R155", "D155"),
        ("/TCP0_TXRX1_P", "EXT_HDMI_CK_P", "C156", "R156", "D156"),
        ("/TCP0_TXRX1_N", "EXT_HDMI_CK_N", "C157", "R157", "D157"),
    ):
        connector_net = local("TCP0 External HDMI", connector)
        add(cref, 1, source, "Mu-side HDMI transmitter AC coupling.", "LattePanda Mu HDMI reference")
        add(cref, 2, connector_net, "Connector-side HDMI transmitter AC coupling.", "LattePanda Mu HDMI reference")
        add(rref, 1, connector_net, "HDMI source bias return resistor.", "LattePanda Mu HDMI reference")
        add(rref, 2, local("TCP0 External HDMI", "EXT_HDMI_BIAS_RETURN"), "Host-state-gated HDMI bias return.", "LattePanda Mu HDMI reference")
        add(dref, 1, connector_net, "0.15pF-max ESD shunt is placed on the connector side of AC coupling.", "TI TPD1E0B04 datasheet")
        add(dref, 2, "GND", "HDMI ESD shunt return.", "TI TPD1E0B04 datasheet")
    for pin, net in {
        1: local("TCP0 External HDMI", "EXT_HDMI_SCL_CONN"),
        2: local("TCP0 External HDMI", "EXT_HDMI_SDA_CONN"),
        3: local("TCP0 External HDMI", "EXT_HDMI_HPD_CONN"),
        5: local("TCP0 External HDMI", "HDMI_SOURCE_5V"), 6: local("TCP0 External HDMI", "EXT_HDMI_5V"), 8: "GND",
    }.items():
        add("U50", pin, net, "TPD13S523 clamps HDMI control lines and supplies current-limited reverse-blocking connector 5 V.", "TI TPD13S523 datasheet")
    for offset, pin in enumerate((4, 7, 9, 10, 11, 12, 13, 14, 15, 16)):
        unused = local("TCP0 External HDMI", f"HDMI_TPD_D{offset}_UNUSED")
        add("U50", pin, unused, "Unused TPD13S523 TMDS clamp is terminated as TI requires instead of floating.", "TI TPD13S523 datasheet")
        add(f"R{570 + offset}", 1, unused, "Unused TPD13S523 clamp-channel termination.", "TI TPD13S523 datasheet")
        add(f"R{570 + offset}", 2, "GND", "75R unused-channel termination return.", "TI TPD13S523 datasheet")
    add("R165", 1, "/MU_HOST_ACTIVE", "HDMI bias network follows qualified Mu host state.", "Ducktop2 HDMI host-state contract")
    add("R165", 2, local("TCP0 External HDMI", "EXT_HDMI_BIAS_GATE"), "Qualified host-state series drive reaches the HDMI bias gate.", "Ducktop2 HDMI host-state contract")
    for ref, net, note in (
        ("C158", local("TCP0 External HDMI", "HDMI_SOURCE_5V"), "TPD13S523 input bulk"),
        ("C159", local("TCP0 External HDMI", "EXT_HDMI_5V"), "TPD13S523 output bulk"),
        ("C162", local("TCP0 External HDMI", "HDMI_SOURCE_5V"), "TPD13S523 input high-frequency bypass"),
        ("C163", local("TCP0 External HDMI", "EXT_HDMI_5V"), "TPD13S523 output high-frequency bypass"),
    ):
        add(ref, 1, net, f"{note} positive rail.", "TI TPD13S523 datasheet")
        add(ref, 2, "GND", f"{note} return.", "TI TPD13S523 datasheet")
    for pin, net in {
        1: "GND", 2: local("TCP0 External HDMI", "HDMI_HOST_3V3"), 3: "/TCP0_DDC_SCL", 4: "/TCP0_DDC_SDA",
        5: local("TCP0 External HDMI", "EXT_HDMI_SDA_CONN"),
        6: local("TCP0 External HDMI", "EXT_HDMI_SCL_CONN"),
        7: local("TCP0 External HDMI", "HDMI_DDC_REF5"),
        8: local("TCP0 External HDMI", "HDMI_DDC_REF5"),
    }.items():
        add("U51", pin, net, "PCA9306 provides the characterized bidirectional DDC/SCDC level-translation path.", "TI PCA9306 datasheet")
    add_nc("U53", 1, "SN74LVC1G17 DBV pin 1 is NC.", "TI SN74LVC1G17 datasheet")
    for pin, net in {2: local("TCP0 External HDMI", "EXT_HDMI_HPD_NODE"), 3: "GND", 4: "/TCP0_HPD", 5: local("TCP0 External HDMI", "HDMI_HOST_3V3")}.items():
        add("U53", pin, net, "5.5-V-tolerant Schmitt buffer translates connector HPD to Mu 3.3 V.", "TI SN74LVC1G17 datasheet")
    for ref, source, output, ct, cap, bleed in (
        ("U54", "/SYS_5V", "HDMI_SOURCE_5V", "HDMI_5V_SWITCH_CT", "C164", "R168"),
        ("U55", "/SYS_3V3", "HDMI_HOST_3V3", "HDMI_3V3_SWITCH_CT", "C165", "R169"),
    ):
        for pin, net in {
            1: source, 2: source, 3: "/MU_HOST_ACTIVE", 4: source, 5: "GND",
            6: local("TCP0 External HDMI", ct),
            7: local("TCP0 External HDMI", output),
            8: local("TCP0 External HDMI", output), 9: "GND",
        }.items():
            add(ref, pin, net, "Host-state load switch removes HDMI interface power while the Mu is off.", "TI TPS22975N datasheet")
        add(cap, 1, local("TCP0 External HDMI", ct), "Load-switch rise-time capacitor.", "TI TPS22975N datasheet")
        add(cap, 2, "GND", "Load-switch rise-time return.", "TI TPS22975N datasheet")
        add(bleed, 1, local("TCP0 External HDMI", output), "Discharges the switched HDMI rail after host shutdown.", "Ducktop2 HDMI host-state contract")
        add(bleed, 2, "GND", "Switched-rail discharge return.", "Ducktop2 HDMI host-state contract")

    ec_usb_src = "TI TS3USB30E and TLV803E datasheets plus Ducktop2 physical internal-host VBUS contract"
    for pin, net in {
        1: "GND", 2: "/EC_HOST_USB_DP", 4: local("Internal Services", "EC_USB_ISO_DP"),
        5: "GND", 6: local("Internal Services", "EC_USB_ISO_DM"), 8: "/EC_HOST_USB_DM",
        9: local("Internal Services", "EC_USB_OE_N"), 10: "/MCU_3V3",
    }.items():
        add("U61", pin, net, "EC USB data is disconnected unless the physical carrier host VBUS is valid.", ec_usb_src)
    add_nc("U61", 3, "Unused alternate USB D+ input is intentionally NC.", ec_usb_src)
    add_nc("U61", 7, "Unused alternate USB D- input is intentionally NC.", ec_usb_src)
    for pin, net in {1: "/INTERNAL_USB_VBUS_VALID", 2: "GND", 3: local("Internal Services", "EC_USB_OE_N")}.items():
        add("Q60", pin, net, "NMOS enables EC USB data only after physical host VBUS qualification.", ec_usb_src)
    add("R202", 1, "/MCU_3V3", "USB switch enable defaults high/disconnected.", ec_usb_src)
    add("R202", 2, local("Internal Services", "EC_USB_OE_N"), "USB switch default-disconnect control.", ec_usb_src)

    trackpad_src = "USB Type-C receptacle pinout plus internal USB2 trackpad cable contract"
    add_many("J58", ["A1", "A12", "B1", "B12", "SH"], "GND", "Trackpad USB-C shell/ground pins.", trackpad_src)
    add_many("J58", ["A4", "A9", "B4", "B9"], local("Internal Services", "TPAD_5V"), "Trackpad USB-C VBUS pins.", trackpad_src)
    add("J58", "A5", local("Internal Services", "TPAD_CC1"), "Trackpad USB-C CC1.", trackpad_src)
    add("J58", "B5", local("Internal Services", "TPAD_CC2"), "Trackpad USB-C CC2.", trackpad_src)
    add_many("J58", ["A6", "B6"], local("Internal Services", "TPAD_CONN_DP"), "Trackpad USB2 D+ tied to both orientations.", trackpad_src)
    add_many("J58", ["A7", "B7"], local("Internal Services", "TPAD_CONN_DM"), "Trackpad USB2 D- tied to both orientations.", trackpad_src)
    for pin in ["A2", "A3", "A8", "A10", "A11", "B2", "B3", "B8", "B10", "B11"]:
        add_nc("J58", pin, "Internal trackpad cable does not use SuperSpeed/SBU.", trackpad_src)
    for pin, net in {
        1: "/TRACKPAD_FAULT_N", 2: local("Internal Services", "TPAD_5V_PRE"),
        3: local("Internal Services", "TPAD_5V_PRE"), 4: local("Internal Services", "TPAD_5V_PRE"),
        5: "/SYS_3V3", 6: "/MU_HOST_ACTIVE",
        7: "GND", 8: "GND", 9: local("Internal Services", "TPAD_REF_RTN"),
        10: local("Internal Services", "TPAD_REF"), 11: local("Internal Services", "TPAD_CC1"),
        12: "GND", 13: local("Internal Services", "TPAD_CC2"),
        14: local("Internal Services", "TPAD_5V"), 15: local("Internal Services", "TPAD_5V"), 21: "GND",
    }.items():
        add("U63", pin, net, "TPS25810 provides attach-controlled, reverse-blocked trackpad VBUS and Type-C CC handling.", "TI TPS25810 datasheet")
    for pin in [16, 17, 18, 19, 20]:
        add_nc("U63", pin, "Unused trackpad TPS25810 status/strap output.", "TI TPS25810 datasheet")
    trackpad_branch = "TI TPS2553 datasheet plus TPS25810 input-capacitance isolation contract"
    for pin, net in {
        1: "/SYS_5V", 2: "GND", 3: "/MU_HOST_ACTIVE", 4: "/TRACKPAD_FAULT_N",
        5: local("Internal Services", "TPAD_ILIM"), 6: local("Internal Services", "TPAD_5V_PRE"),
    }.items():
        add("U64", pin, net, "Current-limited branch isolates the trackpad TPS25810 input reservoir from shared SYS_5V.", trackpad_branch)
    add("R252", 1, local("Internal Services", "TPAD_ILIM"), "Trackpad TPS2553 current-limit programming resistor.", trackpad_branch)
    add("R252", 2, "GND", "Trackpad TPS2553 current-limit resistor return.", trackpad_branch)
    for ref, net, note in (
        ("C280", "/SYS_5V", "trackpad TPS2553 input bypass"),
        ("C281", local("Internal Services", "TPAD_5V_PRE"), "trackpad TPS25810 input bypass"),
        ("C283", local("Internal Services", "TPAD_5V"), "trackpad connector-side VBUS capacitance"),
        ("C284", local("Internal Services", "TPAD_5V_PRE"), "isolated trackpad TPS25810 input reservoir"),
    ):
        add(ref, 1, net, f"{note} positive rail.", trackpad_branch)
        add(ref, 2, "GND", f"{note} return.", trackpad_branch)
    add("R256", 1, "/MCU_3V3", "Trackpad fault open-drain output requires an always-on pull-up.", "TI TPS25810 datasheet")
    add("R256", 2, "/TRACKPAD_FAULT_N", "Trackpad fault reaches the EC as an active-low signal.", "TI TPS25810 datasheet")
    for pin, net in {1: local("Internal Services", "TPAD_CONN_DP"),
                     2: local("Internal Services", "TPAD_CONN_DM"), 3: "GND",
                     4: local("Internal Services", "TPAD_CC1"),
                     5: local("Internal Services", "TPAD_CC2"), 8: "GND"}.items():
        add("U62", pin, net, "Trackpad USB2 and CC connector-side ESD protection.", "TI TPD4E05U06 datasheet")
    for pin in [6, 7, 9, 10]:
        add_nc("U62", pin, "Unused TPD4E05U06 package pin.", "TI TPD4E05U06 datasheet")

    delta_fan = "Delta BFB04512HHA-CZ0T specification"
    for pin, net in {1: "GND", 2: local("Internal Services", "FAN_12V"), 3: "/FAN_TACH", 4: local("Internal Services", "FAN_PWM_CONN")}.items():
        add("J52", pin, net, "Released 4-wire Delta PWM blower connector contract.", delta_fan)
    add("F200", 1, "/MU_12V", "Delta blower uses the regulated 12 V rail through a 16 V-rated PTC.", delta_fan)
    add("F200", 2, local("Internal Services", "FAN_12V"), "Protected fan supply after the PTC.", delta_fan)
    add("R206", 1, "/MCU_3V3", "8.2k Delta-typical FG pull-up rail.", delta_fan)
    add("R206", 2, "/FAN_TACH", "Open-collector FG signal, two pulses per revolution.", delta_fan)
    add("C209", 1, "/FAN_TACH", "3.9nF implementation of Delta's 4nF typical FG filter.", delta_fan)
    add("C209", 2, "GND", "FG filter return.", delta_fan)
    for ref, signal, note in (
        ("J53", "/LID_CLOSED_N", "lid/hall switch"),
        ("J54", "/THERM_SKIN_ADC", "skin/hinge thermistor"),
        ("J56", "/THERM_MU_ADC", "Mu heatsink thermistor"),
    ):
        add(ref, 1, signal, f"Keyed {note} signal contact.", project)
        add(ref, 2, "GND", f"Keyed {note} return contact.", project)
    for pin, net in {1: local("Internal Services", "FAN_PWM_GATE"), 2: "GND", 3: local("Internal Services", "FAN_PWM_CONN")}.items():
        add("Q200", pin, net, "Fan PWM is open-drain sink style.", project)

    # OLED and dual TPS25751A service buses.
    tca = "TI TCA9548A datasheet plus Ducktop2 OLED and TPS25751A service-I2C contract"
    for pin, net in {
        1: "GND", 2: "GND", 3: "/SERVICE_MUX_RESET_N",
        4: "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_A_SDA",
        5: "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_A_SCL",
        6: "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_B_SDA",
        7: "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_B_SCL",
        8: "/PD1_I2C_SDA", 9: "/PD1_I2C_SCL",
        10: "/PD2_I2C_SDA", 11: "/PD2_I2C_SCL",
        12: "GND", 21: "GND", 22: "/I2C_SCL", 23: "/I2C_SDA", 24: "/MCU_3V3",
    }.items():
        add("U45", pin, net, "TCA9548A isolates two OLEDs and the two TPS25751A service buses; address pins strap to 0x70.", tca)
    for pin in [13, 14, 15, 16, 17, 18, 19, 20]:
        add_nc("U45", pin, "Unused TCA9548A downstream channels intentionally NC.", tca)
    for ref, suffix in [("J41", "A"), ("J45", "B")]:
        add(ref, 1, "GND", "SSD1306 module pin 1 is GND.", "Common 4-pin SSD1306 module pinout from user photo")
        add(ref, 2, "/MCU_3V3", "SSD1306 module pin 2 is VDD; use 3.3 V modules.", "Common 4-pin SSD1306 module pinout from user photo")
        add(ref, 3, f"/Wi-Fi{{slash}}Bluetooth & OLEDs/OLED_{suffix}_SCL", "SSD1306 module pin 3 is SCK/SCL.", "Common 4-pin SSD1306 module pinout from user photo")
        add(ref, 4, f"/Wi-Fi{{slash}}Bluetooth & OLEDs/OLED_{suffix}_SDA", "SSD1306 module pin 4 is SDA.", "Common 4-pin SSD1306 module pinout from user photo")

    gnss = "u-blox MAX-M10S datasheet plus Ducktop2 GNSS contract"
    for pin, net in {1: "GND", 2: "/GNSS_UART_RX", 3: "/GNSS_UART_TX", 4: "/GNSS_PPS", 5: "/GNSS_EXTINT", 6: "/MCU_3V3", 7: "/MCU_3V3", 8: "/MCU_3V3", 9: "/GNSS_RESET_N", 10: "GND", 11: "/Radio/OLED/GNSS/GNSS_RF_IN", 12: "GND"}.items():
        add("U40", pin, net, "MAX-M10S power, UART, PPS/reset/control, and RF input contract.", gnss)
    for pin in [13, 14, 15, 16, 17, 18]:
        add_nc("U40", pin, "Unused MAX-M10S optional pin intentionally NC.", gnss)
    add("J42", 1, "/Radio/OLED/GNSS/GNSS_RF_IN", "GNSS U.FL center to MAX-M10S RF input.", gnss)
    add("J42", 2, "GND", "GNSS U.FL shield to ground.", gnss)

    radio_buck = "TI TPS54302 and Coilcraft XGL5030-332 datasheets"
    for pin, net in {
        1: "GND", 2: "/Ham Radio/RADIO_BUCK_SW", 3: "/SYS_5V",
        4: "/Ham Radio/RADIO_BUCK_FB", 5: "/Ham Radio/RADIO_BUCK_EN",
        6: "/Ham Radio/RADIO_BUCK_BOOT",
    }.items():
        add("U70", pin, net, "TPS54302 creates the 4.0 V radio rail from SYS_5V.", radio_buck)
    add("L70", 1, "/Ham Radio/RADIO_BUCK_SW", "3.3uH XGL5030 switch-side connection.", radio_buck)
    add("L70", 2, "/Ham Radio/RADIO_4V0", "3.3uH XGL5030 filtered-output connection.", radio_buck)

    rf_switch_src = "pSemi PE42820 datasheet plus Ducktop2 powered internal/external antenna contract"
    for ref, band in [("U240", "VHF"), ("U250", "UHF")]:
        src = rf_switch_src
        add(ref, 2, f"/Ham Radio/{band}_ANT_EXTERNAL", "RF1 routes to the rear external antenna connector.", src)
        add(ref, 12, "/Ham Radio/RADIO_4V0", "RF switch VDD follows the radio rail.", src)
        add(ref, 13, f"/Ham Radio/RADIO_{band}_RF_SEL_4V0", "CTRL low selects internal RF2; high selects external RF1.", src)
        add(ref, 23, f"/Ham Radio/{band}_ANT_ONBOARD", "RF2 routes to the default onboard antenna feed.", src)
        add(ref, 28, f"/Ham Radio/{band}_RF_FILTERED", "RFC receives the filtered transmitter/receiver path.", src)
        add_many(ref, [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 29, 30, 31, 32, 33], "GND", "PE42820 ground and exposed-pad pins.", src)
    for ref, band, top, bottom in (("U241", "VHF", "R242", "R227"), ("U251", "UHF", "R260", "R228")):
        raw = f"/Ham Radio/RADIO_{band}_RF_SEL_4V0_RAW"
        ctrl = f"/Ham Radio/RADIO_{band}_RF_SEL_4V0"
        for pin, net in {
            1: f"/Ham Radio/RADIO_{band}_PTT_SAFE_N", 2: "GND",
            3: f"/RADIO_{band}_RF_SEL_3V3", 4: raw,
            5: "/Ham Radio/RADIO_4V0", 6: "GND",
        }.items():
            add(ref, pin, net, "Radio-powered latch freezes antenna selection for the entire transmit interval.", "TI SN74LVC1G373 datasheet")
        add(top, 1, raw, "RF-select divider limits PE42820 control voltage below absolute maximum.", rf_switch_src)
        add(top, 2, ctrl, "RF-select divider output drives PE42820 CTRL.", rf_switch_src)
        add(bottom, 1, ctrl, "RF-select divider output drives PE42820 CTRL.", rf_switch_src)
        add(bottom, 2, "GND", "RF-select divider bottom return.", rf_switch_src)

    for pin, net in {
        1: "/RADIO_VHF_PTT_N", 6: "/Ham Radio/RADIO_VHF_PTT_REQ",
        3: "/RADIO_UHF_PTT_N", 4: "/Ham Radio/RADIO_UHF_PTT_REQ",
        2: "GND", 5: "/MCU_3V3",
    }.items():
        add("U260", pin, net, "Creates active-high transmit requests from the EC active-low PTT controls.", "TI SN74LVC2G04 datasheet")
    for pin, net in {
        1: "/RADIO_VHF_PTT_N", 2: "/Ham Radio/RADIO_UHF_PTT_REQ",
        7: "/Ham Radio/RADIO_VHF_PTT_SAFE_N",
        5: "/RADIO_UHF_PTT_N", 6: "/Ham Radio/RADIO_VHF_PTT_REQ",
        3: "/Ham Radio/RADIO_UHF_PTT_SAFE_N", 4: "GND", 8: "/MCU_3V3",
    }.items():
        add("U261", pin, net, "Hardware interlock makes both module PTT outputs inactive for simultaneous requests.", "TI SN74LVC2G32 datasheet")
    for ref in ("C260", "C261"):
        add(ref, 1, "/MCU_3V3", "PTT interlock bypass.", "TI LVC logic decoupling guidance")
        add(ref, 2, "GND", "PTT interlock bypass return.", "TI LVC logic decoupling guidance")
    for ref, band in (("R230", "VHF"), ("R232", "UHF")):
        add(ref, 1, f"/RADIO_{band}_RF_SEL_3V3", "EC reset defaults antenna selection to the internal path.", "Ducktop2 RF-select safety contract")
        add(ref, 2, "GND", "RF-select reset-default return.", "Ducktop2 RF-select safety contract")

    radio_io = "TI SN74LVC3G34 Ioff contract plus DRA818 powered-off input-isolation contract"
    for ref, band, bypass, tx_series, tx_default in (
        ("U242", "VHF", "C246", "R243", "R244"),
        ("U252", "UHF", "C256", "R261", "R262"),
    ):
        for pin, net in {
            1: f"/RADIO_{band}_UART_TX",
            7: f"/Ham Radio/RADIO_{band}_UART_RXD",
            6: f"/Ham Radio/RADIO_{band}_PTT_SAFE_N",
            2: f"/Ham Radio/RADIO_{band}_PTT_LOCAL_N",
            3: f"/RADIO_{band}_PD_N",
            5: f"/Ham Radio/RADIO_{band}_PD_LOCAL_N",
            4: "GND", 8: "/Ham Radio/RADIO_4V0",
        }.items():
            add(ref, pin, net, "Radio-powered Ioff buffer prevents live EC signals from back-powering an unpowered DRA818 module.", radio_io)
        add(bypass, 1, "/Ham Radio/RADIO_4V0", "Fail-safe radio buffer local bypass.", radio_io)
        add(bypass, 2, "GND", "Fail-safe radio buffer bypass return.", radio_io)
        add(tx_series, 1, f"/Ham Radio/RADIO_{band}_UART_TXD", "Module TXD output reaches the EC through series isolation.", radio_io)
        add(tx_series, 2, f"/RADIO_{band}_UART_RX", "Series-isolated module TXD reaches the EC UART RX.", radio_io)
        add(tx_default, 1, f"/RADIO_{band}_UART_TX", "EC UART TX defaults low before firmware configuration.", radio_io)
        add(tx_default, 2, "GND", "EC UART TX default resistor return.", radio_io)

    for ref, band, part, grounds, package in [
        ("FL240", "VHF", "LFCN-160+", [2, 4], "FV1206"),
        ("FL250", "UHF", "ULP-470+", [2, 4, 5, 6], "PL-484"),
    ]:
        src = f"Mini-Circuits {part} datasheet and {package} land-pattern drawing"
        add(ref, 1, f"/Ham Radio/{band}_RF_RAW", "Packaged LPF RF1 connects directly to the radio module RF output.", src)
        add(ref, 3, f"/Ham Radio/{band}_RF_FILTERED", "Packaged LPF RF2 feeds the antenna-selection switch.", src)
        add_many(ref, grounds, "GND", "All LPF ground terminals require a low-inductance stitched ground plane.", src)

    for ref, band in [("J70", "VHF"), ("J71", "UHF")]:
        src = "DRA818/SA818 module pin contract from Ducktop2 ham-radio sheet"
        for pin, net in {
            1: f"/RADIO_{band}_SQL", 3: f"/Ham Radio/{band}_AF_OUT",
            5: f"/Ham Radio/RADIO_{band}_PTT_LOCAL_N",
            6: f"/Ham Radio/RADIO_{band}_PD_LOCAL_N",
            7: f"/Ham Radio/{band}_HL", 8: "/Ham Radio/RADIO_4V0",
            9: "GND", 10: "GND", 12: f"/Ham Radio/{band}_RF_RAW",
            16: f"/Ham Radio/RADIO_{band}_UART_RXD",
            17: f"/Ham Radio/RADIO_{band}_UART_TXD",
            18: f"/RADIO_{band}_MIC_IN",
        }.items():
            add(ref, pin, net, "Radio module socket contract.", src)
        for pin in [2, 4, 11, 13, 14, 15]:
            add_nc(ref, pin, "Unused radio module socket pin intentionally NC.", src)

    pcm = "TI PCM2902C datasheet Figure 39 plus Ducktop2 radio-audio USB codec contract"
    for pin, net in {
        1: local("Radio Audio Codec", "CODEC_USB_DP"),
        2: local("Radio Audio Codec", "CODEC_USB_DM"),
        3: local("Radio Audio Codec", "CODEC_VBUS"),
        4: "GND", 8: local("Radio Audio Codec", "CODEC_VDDI"),
        9: local("Radio Audio Codec", "CODEC_VDDI"),
        10: local("Radio Audio Codec", "CODEC_VCCCI"), 11: "GND",
        12: local("Radio Audio Codec", "CODEC_LINEIN_L"),
        13: local("Radio Audio Codec", "CODEC_LINEIN_R"),
        14: local("Radio Audio Codec", "CODEC_VCOM"),
        15: local("Radio Audio Codec", "CODEC_TX_UHF"),
        16: local("Radio Audio Codec", "CODEC_TX_VHF"),
        17: local("Radio Audio Codec", "CODEC_VCCP1I"), 18: "GND",
        19: local("Radio Audio Codec", "CODEC_VCCP2I"),
        20: local("Radio Audio Codec", "CODEC_XTO"),
        21: local("Radio Audio Codec", "CODEC_XTI"), 22: "GND",
        23: local("Radio Audio Codec", "CODEC_VCCXI"), 26: "GND",
        27: local("Radio Audio Codec", "CODEC_VDDI"),
        28: local("Radio Audio Codec", "CODEC_SSPND"),
    }.items():
        add("U330", pin, net, "PCM2902C USB audio codec core contract.", pcm)
    for pin in [5, 6, 7, 24, 25]:
        add_nc("U330", pin, "Unused PCM2902C HID/serial/status pin intentionally NC.", pcm)
    add("R330", 1, "/RADIO_CODEC_USB_DP", "Radio codec D+ comes from downstream port 1 of the embedded audio hub.", pcm)
    add("R330", 2, local("Radio Audio Codec", "CODEC_USB_DP"), "Radio codec D+ series resistor device side.", pcm)
    add("R331", 1, "/RADIO_CODEC_USB_DM", "Radio codec D- comes from downstream port 1 of the embedded audio hub.", pcm)
    add("R331", 2, local("Radio Audio Codec", "CODEC_USB_DM"), "Radio codec D- series resistor device side.", pcm)
    add("R337", 1, "/RADIO_CODEC_USB_VBUS", "Radio codec VBUS comes from the hub-controlled downstream power switch.", pcm)
    add("R337", 2, local("Radio Audio Codec", "CODEC_VBUS"), "Radio codec filtered VBUS sense/supply node.", pcm)
    for ref, gate, mic in [("Q330", "VHF_MUTE_GATE", "/RADIO_VHF_MIC_IN"),
                           ("Q331", "UHF_MUTE_GATE", "/RADIO_UHF_MIC_IN")]:
        add(ref, 1, local("Radio Audio Codec", gate), "PTT/suspend fail-mute NMOS gate.", pcm)
        add(ref, 2, "GND", "PTT/suspend fail-mute NMOS source.", pcm)
        add(ref, 3, mic, "PTT/suspend fail-mute shunts the radio microphone input.", pcm)
    for pin, net in {1: local("Radio Audio Codec", "CODEC_SSPND"), 2: "/MCU_3V3",
                     3: local("Radio Audio Codec", "CODEC_FORCE_MUTE")}.items():
        add("Q332", pin, net, "PMOS forces radio TX muted during USB suspend or codec power loss.", pcm)
    for ref, source, gate in [
        ("D390", "/RADIO_VHF_PTT_N", "VHF_MUTE_GATE"),
        ("D391", local("Radio Audio Codec", "CODEC_FORCE_MUTE"), "VHF_MUTE_GATE"),
        ("D392", "/RADIO_UHF_PTT_N", "UHF_MUTE_GATE"),
        ("D393", local("Radio Audio Codec", "CODEC_FORCE_MUTE"), "UHF_MUTE_GATE"),
    ]:
        add(ref, 1, local("Radio Audio Codec", gate), "Schottky OR cathode at mute gate.", pcm)
        add(ref, 2, source, "Schottky OR anode at PTT or codec force-mute source.", pcm)

    audio = "Microchip USB2512B, TI PCM2900C, TPS2052B, TPA2012D2, LP5907, TLV9061, and Infineon IM68A130 datasheets plus Ducktop2 system-audio contract"
    sa = "System Audio"
    add("F400", 1, "/SYS_5V", "Protected system-audio branch enters from SYS_5V.", audio)
    add("F400", 2, local(sa, "AUDIO_5V"), "Audio branch fuse feeds the local amplifier and downstream-port switch.", audio)
    hub = {
        1: local(sa, "SYSTEM_DAC_USB_DM"), 2: local(sa, "SYSTEM_DAC_USB_DP"),
        3: "/RADIO_CODEC_USB_DM_HOST", 4: "/RADIO_CODEC_USB_DP_HOST",
        5: "/SYS_3V3", 10: "/SYS_3V3", 12: local(sa, "HUB_PORT1_EN"),
        13: local(sa, "HUB_PORT1_OC_N"), 14: local(sa, "HUB_CRFILT"),
        15: "/SYS_3V3", 16: local(sa, "HUB_PORT2_EN"),
        17: local(sa, "HUB_PORT2_OC_N"), 22: local(sa, "HUB_NON_REM1"),
        23: "/SYS_3V3", 24: local(sa, "HUB_CFG_SEL0"),
        25: local(sa, "HUB_CFG_SEL1"), 26: local(sa, "HUB_RESET_N"),
        27: local(sa, "HUB_VBUS_DET"), 28: local(sa, "HUB_NON_REM0"),
        29: "/SYS_3V3", 30: "/AUDIO_USB_DM", 31: "/AUDIO_USB_DP",
        32: local(sa, "HUB_XO"), 33: local(sa, "HUB_XI"),
        34: local(sa, "HUB_PLLFILT"), 35: local(sa, "HUB_RBIAS"),
        36: "/SYS_3V3", 37: "GND",
    }
    for pin, net in hub.items():
        add("U400", pin, net, "USB2512B self-powered two-port internal hub pin contract.", audio)
    for pin in [6, 7, 8, 9, 11, 18, 19, 20, 21]:
        add_nc("U400", pin, "USB2512B reserved/test pin intentionally NC.", audio)
    add("R417", 1, "/INTERNAL_USB_VBUS_VALID", "Audio hub receives the supervised physical upstream-VBUS state.", audio)
    add("R417", 2, local(sa, "HUB_VBUS_DET"), "Audio hub VBUS_DET follows the physical upstream-VBUS state.", audio)
    for pin, net in {
        1: "GND", 2: local(sa, "AUDIO_5V"), 3: local(sa, "HUB_PORT1_EN"),
        4: local(sa, "HUB_PORT2_EN"), 5: local(sa, "HUB_PORT2_OC_N"),
        6: "/RADIO_CODEC_USB_VBUS_HOST", 7: local(sa, "SYSTEM_DAC_USB_VBUS"),
        8: local(sa, "HUB_PORT1_OC_N"),
    }.items():
        add("U402", pin, net, "TPS2052B implements individual downstream-port power and OC feedback.", audio)
    for pin, net in {1: local(sa, "HUB_RESET_N"), 2: "GND", 3: "/SYS_3V3"}.items():
        add("U401", pin, net, "TLV803E holds the hub in reset until 3.3 V is valid.", audio)
    codec = {
        1: local(sa, "CODEC_USB_DP"), 2: local(sa, "CODEC_USB_DM"),
        3: local(sa, "CODEC_VBUS"), 4: "GND", 8: local(sa, "CODEC_VDDI"),
        9: local(sa, "CODEC_VDDI"), 10: local(sa, "CODEC_VCCCI"), 11: "GND",
        12: local(sa, "MIC_ADC_L"), 13: local(sa, "MIC_ADC_R"),
        14: local(sa, "CODEC_VCOM"), 15: local(sa, "DAC_VOUT_R"),
        16: local(sa, "DAC_VOUT_L"), 17: local(sa, "CODEC_VCCP1I"),
        18: "GND", 19: local(sa, "CODEC_VCCP2I"), 20: local(sa, "CODEC_XTO"),
        21: local(sa, "CODEC_XTI"), 22: "GND", 23: local(sa, "CODEC_VCCXI"),
        24: "GND", 26: "GND", 27: local(sa, "CODEC_VDDI"),
        28: local(sa, "DAC_SSPND"),
    }
    for pin, net in codec.items():
        add("U410", pin, net, "PCM2900C USB playback and stereo ADC pin contract.", audio)
    for pin in [5, 6, 7, 25]:
        add_nc("U410", pin, "Unused PCM2900C HID, serial, or TEST1 pin intentionally NC.", audio)
    for pin, net in {
        1: local(sa, "DAC_SSPND"), 2: "/AUDIO_AMP_EC_EN", 3: "GND",
        4: local(sa, "AMP_ENABLE"), 5: "/SYS_3V3",
    }.items():
        add("U421", pin, net, "AND gate permits speaker enable only when the DAC is operational and the EC allows it.", audio)
    amp = {
        1: "GND", 2: local(sa, "AMP_OUT_LP"), 3: local(sa, "AUDIO_5V"),
        4: "GND", 5: local(sa, "AMP_OUT_LN"), 7: local(sa, "AMP_ENABLE"),
        8: local(sa, "AMP_ENABLE"), 9: local(sa, "AUDIO_5V"),
        11: local(sa, "AMP_OUT_RN"), 12: "GND", 13: local(sa, "AUDIO_5V"),
        14: local(sa, "AMP_OUT_RP"), 15: local(sa, "AUDIO_5V"),
        16: local(sa, "AMP_IN_RP"), 17: local(sa, "AMP_IN_RN"), 18: "GND",
        19: local(sa, "AMP_IN_LN"), 20: local(sa, "AMP_IN_LP"), 21: "GND",
    }
    for pin, net in amp.items():
        add("U420", pin, net, "TPA2012D2 stereo BTL amplifier pin contract.", audio)
    for pin in [6, 10]:
        add_nc("U420", pin, "TPA2012D2 NC pin intentionally unconnected.", audio)
    for ref, p, n in [("J420", "SPK_L_P", "SPK_L_N"), ("J421", "SPK_R_P", "SPK_R_N")]:
        add(ref, 1, local(sa, p), "Speaker connector positive BTL leg; never ground.", audio)
        add(ref, 2, local(sa, n), "Speaker connector negative BTL leg; never ground.", audio)

    for pin, net in {1: "/SYS_3V3", 2: "GND", 3: "/AUDIO_MIC_EN", 5: local(sa, "MIC_2V8")}.items():
        add("U430", pin, net, "LP5907 produces a fail-off 2.8 V low-noise microphone rail.", audio)
    add_nc("U430", 4, "LP5907 NC pin intentionally unconnected.", audio)
    for pin, net in {1: local(sa, "MIC_RAW"), 2: "GND", 3: local(sa, "MIC_2V8"), 4: "GND"}.items():
        add("MK430", pin, net, "IM68A130 bottom-port analog microphone pin contract.", audio)
    for pin, net in {1: local(sa, "MIC_PREAMP"), 2: "GND", 3: local(sa, "MIC_RAW"),
                     4: local(sa, "MIC_FB"), 5: "/SYS_3V3"}.items():
        add("U431", pin, net, "TLV9061 non-inverting microphone preamplifier pin contract.", audio)
    for ref, pin1, pin2 in [
        ("R432", "MIC_PREAMP", "MIC_FB"), ("C453", "MIC_PREAMP", "MIC_FB"),
        ("R433", "MIC_FB", "MIC_HP_NODE"), ("C454", "MIC_HP_NODE", "GND"),
        ("C455", "MIC_PREAMP", "MIC_ADC_L"), ("C456", "MIC_PREAMP", "MIC_ADC_R"),
    ]:
        add(ref, 1, "GND" if pin1 == "GND" else local(sa, pin1), "Microphone analog network pin 1.", audio)
        add(ref, 2, "GND" if pin2 == "GND" else local(sa, pin2), "Microphone analog network pin 2.", audio)
    add("R434", 1, "/AUDIO_MIC_EN", "Microphone-enable fail-off pull-down node.", audio)
    add("R434", 2, "GND", "Microphone-enable fail-off return.", audio)
    add("R435", 1, local(sa, "MIC_2V8"), "Privacy indicator is powered from the actual microphone supply rail.", audio)
    add("R435", 2, local(sa, "MIC_LED_A"), "Privacy indicator current-limit output.", audio)
    add("LED430", 1, "GND", "Privacy indicator cathode.", audio)
    add("LED430", 2, local(sa, "MIC_LED_A"), "Privacy indicator anode.", audio)

    ethernet = "LattePanda DFR1142 Mu carrier Gigabit Ethernet reference, Realtek RTL8111H, Diodes D3V3XA4B10LP, and Yageo JXD1-1022NL documentation"
    ge = "Gigabit Ethernet"
    rtl = {
        1: "ETH_MDI0_P", 2: "ETH_MDI0_N", 3: "ETH_1V0", 4: "ETH_MDI1_P",
        5: "ETH_MDI1_N", 6: "ETH_MDI2_P", 7: "ETH_MDI2_N", 8: "ETH_1V0",
        9: "ETH_MDI3_P", 10: "ETH_MDI3_N", 11: "/PCIE_3V3", 12: "/GBE_CLKREQ_N",
        13: "GBE_HSI_P", 14: "GBE_HSI_N", 15: "/GBE_REFCLK_P", 16: "/GBE_REFCLK_N",
        17: "GBE_HSO_P", 18: "GBE_HSO_N", 19: "/PLTRST_SRC_N", 20: "GBE_ISOLATE_N",
        21: "/PCIE_WAKE_N", 22: "ETH_1V0", 23: "/PCIE_3V3", 24: "ETH_1V0",
        25: "ETH_LED_ACT_N", 26: "ETH_LED_1000_N", 28: "ETH_XI", 29: "ETH_XO",
        30: "ETH_1V0", 31: "ETH_RSET", 32: "/PCIE_3V3", 33: "GND",
    }
    for pin, name in rtl.items():
        expected = name if name.startswith("/") or name == "GND" else local(ge, name)
        add("U500", pin, expected, "RTL8111H native HSIO6 PCIe Gigabit Ethernet contract.", ethernet)
    add_nc("U500", 27, "Unused RTL8111H LED0 pin intentionally NC.", ethernet)
    for ref, names in [
        ("U501", ["ETH_MDI0_P", "ETH_MDI0_N", "ETH_MDI1_P", "ETH_MDI1_N"]),
        ("U502", ["ETH_MDI2_P", "ETH_MDI2_N", "ETH_MDI3_P", "ETH_MDI3_N"]),
    ]:
        for pin, name in zip([1, 2, 4, 5], names):
            add(ref, pin, local(ge, name), "Low-capacitance MDI ESD channel.", ethernet)
        add_many(ref, [3, 8], "GND", "ESD array ground.", ethernet)
        for pin in [6, 7, 9, 10]:
            add_nc(ref, pin, "Unused ESD package pin intentionally NC.", ethernet)
    jack = {
        1: "ETH_MDI0_P", 2: "ETH_MDI0_N", 3: "ETH_CT", 4: "ETH_MDI1_P",
        5: "ETH_MDI1_N", 6: "ETH_CT", 7: "ETH_MDI2_P", 8: "ETH_MDI2_N",
        9: "ETH_CT", 10: "ETH_MDI3_P", 11: "ETH_MDI3_N", 12: "ETH_CT",
        13: "ETH_LED_ACT_N", 14: "ETH_LED_ACT_A", 15: "ETH_LED_1000_N",
        16: "ETH_LED_1000_A", "SH": "ETH_CHASSIS",
    }
    for pin, name in jack.items():
        add("J500", pin, local(ge, name), "JXD1-1022NL integrated-magnetics mid-mount jack pin contract.", ethernet)
    for pin, net in {
        1: local(ge, "ETH_XI"), 2: "GND",
        3: local(ge, "ETH_XO"), 4: "GND",
    }.items():
        add("Y500", pin, net, "25 MHz crystal signal and grounded-case pin contract.", ethernet)
    for ref, first, second in [
        ("C500", "/GBE_HOST_TX_P", "GBE_HSI_P"), ("C501", "/GBE_HOST_TX_N", "GBE_HSI_N"),
        ("C502", "GBE_HSO_P", "/GBE_HOST_RX_P"), ("C503", "GBE_HSO_N", "/GBE_HOST_RX_N"),
        ("R500", "ETH_XI", "ETH_XO"), ("R501", "ETH_RSET", "GND"),
        ("R502", "/PCIE_3V3", "GBE_ISOLATE_N"), ("R503", "/PCIE_3V3", "/PCIE_WAKE_N"),
        ("R504", "/PCIE_3V3", "ETH_LED_ACT_A"), ("R505", "/PCIE_3V3", "ETH_LED_1000_A"),
        ("R506", "ETH_CHASSIS", "GND"), ("C513", "ETH_CT", "GND"),
        ("C514", "ETH_CHASSIS", "GND"),
    ]:
        for pin, name in [(1, first), (2, second)]:
            expected = name if name.startswith("/") or name == "GND" else local(ge, name)
            add(ref, pin, expected, "Ethernet reference-design support network.", ethernet)

    keyboard = "Ducktop2 MX ULP rev-A physical FFC mapping"
    for pin, net in {
        1: "GND", 2: "/Keyboard Mainboard FFC/KB_FFC_5V",
        27: "/Keyboard Mainboard FFC/KB_FFC_I2C_SDA",
        28: "/Keyboard Mainboard FFC/KB_FFC_I2C_SCL",
        29: "/Keyboard Mainboard FFC/KB_FFC_3V3",
        30: "GND", "MP": "GND",
    }.items():
        add("J310", pin, net, "Motherboard connector is physically reversed relative to J320 for two top-side bottom-contact connectors and a Type-A FFC.", keyboard)
    add("J310", 3, "/Keyboard Mainboard FFC/KB_FFC_RGB_DATA", "Rev-A spare COL15 conductor is reserved for future keyboard RGB data.", keyboard)
    for pin, col in zip(range(4, 19), range(14, -1, -1)):
        add("J310", pin, f"/Keyboard Mainboard FFC/KB_FFC_COL{col}", "Reversed physical keyboard-column conductor.", keyboard)
    for pin, row in zip(range(19, 27), range(7, -1, -1)):
        add("J310", pin, f"/Keyboard Mainboard FFC/KB_FFC_ROW{row}", "Reversed physical keyboard-row conductor.", keyboard)
    rgb = "TI TPS2553D and SN74AHCT1G126 datasheets plus Molex 0150200315 0.5A/contact rating"
    for pin, net in {
        1: "/SYS_5V", 2: "GND", 3: "/KB_RGB_PWR_EN", 4: "/KB_RGB_FAULT_N",
        5: "/Keyboard Mainboard FFC/KB_RGB_ILIM", 6: "/Keyboard Mainboard FFC/KB_FFC_5V",
    }.items():
        add("U310", pin, net, "Current-limited, default-off future keyboard RGB power path.", rgb)
    for pin, net in {
        1: "/KB_RGB_PWR_EN", 2: "/KB_RGB_DATA_3V3", 3: "GND",
        4: "/Keyboard Mainboard FFC/KB_RGB_DATA_5V", 5: "/SYS_5V",
    }.items():
        add("U311", pin, net, "AHCT buffer translates EC RGB data to the 5V LED domain and tri-states while disabled.", rgb)

    maker = "RP2350 hardware design, TPS62821, and TPS2553D datasheets"
    rp = {
        1: "MAKER_3V3_CORE", 2: "MAKER_UART_TX", 3: "MAKER_UART_RX", 4: "MAKER_I2C_SDA",
        5: "MAKER_I2C_SCL", 6: "MAKER_1V1", 7: "MAKER_GPIO0", 8: "MAKER_GPIO1",
        9: "MAKER_GPIO2", 10: "MAKER_GPIO3", 11: "MAKER_3V3_CORE", 12: "MAKER_GPIO4",
        13: "MAKER_GPIO5", 14: "MAKER_GPIO6", 15: "MAKER_GPIO7", 16: "MAKER_GPIO8",
        17: "MAKER_GPIO9", 18: "MAKER_GPIO10", 19: "MAKER_GPIO11", 20: "MAKER_3V3_CORE",
        21: "MAKER_XIN", 22: "MAKER_XOUT", 23: "MAKER_1V1", 24: "MAKER_SWCLK_MCU",
        25: "MAKER_SWDIO_MCU", 26: "MAKER_RUN_N", 27: "MAKER_SPI_MISO",
        28: "MAKER_SPI_CS_N", 29: "MAKER_SPI_SCK", 30: "MAKER_3V3_CORE", 31: "MAKER_SPI_MOSI",
        32: "MAKER_GPIO12", 33: "MAKER_GPIO13", 34: "MAKER_GPIO14", 35: "MAKER_SMPS_PS",
        36: "MAKER_HOST_ACTIVE_N", 37: "MAKER_PWR_FAULT_N", 38: "MAKER_3V3_CORE", 39: "MAKER_1V1",
        40: "MAKER_ADC0", 41: "MAKER_ADC1", 42: "MAKER_ADC2", 43: "MAKER_PWR_EN",
        44: "MAKER_ADC_AVDD", 45: "MAKER_3V3_CORE", 46: "MAKER_VREG_AVDD",
        48: "MAKER_VREG_LX", 49: "MAKER_3V3_CORE", 50: "MAKER_1V1", 51: "MAKER_USB_DM_MCU",
        52: "MAKER_USB_DP_MCU", 53: "MAKER_3V3_CORE", 54: "MAKER_3V3_CORE", 55: "MAKER_QSPI_SD3",
        56: "MAKER_QSPI_SCLK", 57: "MAKER_QSPI_SD0", 58: "MAKER_QSPI_SD2",
        59: "MAKER_QSPI_SD1", 60: "MAKER_QSPI_SS",
    }
    for pin, name in rp.items():
        add("U901", pin, local("Maker MCU", name), "Integrated RP2350A pin contract.", maker)
    add_many("U901", [47, 61], "GND", "RP2350A ground and exposed pad.", maker)
    for pin, name in {1: "MAKER_QSPI_SS", 2: "MAKER_QSPI_SD1", 3: "MAKER_QSPI_SD2",
                      5: "MAKER_QSPI_SD0", 6: "MAKER_QSPI_SCLK", 7: "MAKER_QSPI_SD3",
                      8: "MAKER_3V3_CORE"}.items():
        add("U902", pin, local("Maker MCU", name), "Integrated 4MB QSPI flash contract.", maker)
    add_many("U902", [4, 9], "GND", "Flash ground and exposed pad.", maker)
    for pin, name in {
        1: "MAKER_5V_CORE", 2: "MAKER_3V3_FB", 3: "GND", 5: "GND",
        6: "MAKER_3V3_SW", 7: "MAKER_5V_CORE",
    }.items():
        expected = "GND" if name == "GND" else local("Maker MCU", name)
        add("U903", pin, expected, "TPS62821 5V-to-3.3V buck contract.", maker)
    for pin in [4, 8]:
        add_nc("U903", pin, "Unused TPS62821 pin intentionally NC.", maker)
    for ref, rail_in, rail_out, ilim in [
        ("U904", "MAKER_5V_CORE", "J901_5V_OUT", "MAKER_5V_ILIM"),
        ("U905", "MAKER_3V3_CORE", "J901_3V3_OUT", "MAKER_3V3_ILIM"),
    ]:
        for pin, name in {1: rail_in, 3: "MAKER_PWR_EN", 4: "MAKER_PWR_FAULT_N", 5: ilim, 6: rail_out}.items():
            add(ref, pin, local("Maker MCU", name), "TPS2553D protected, reverse-blocking header power switch.", maker)
        add(ref, 2, "GND", "TPS2553D ground.", maker)
    add("R923", 1, local("Maker MCU", "MAKER_PWR_EN"), "Maker header power defaults off across reset.", maker)
    add("R923", 2, "GND", "Maker power-enable pull-down return.", maker)
    add("R924", 1, local("Maker MCU", "MAKER_3V3_CORE"), "Shared open-drain fault requires a pull-up.", maker)
    add("R924", 2, local("Maker MCU", "MAKER_PWR_FAULT_N"), "Shared maker power fault reaches RP2350.", maker)

    maker_usb = "TI TS3USB30E and TLV803E datasheets plus Ducktop2 physical internal-host VBUS contract"
    for pin, net in {
        1: "GND", 2: "/MAKER_USB_DP", 4: local("Maker MCU", "MAKER_USB_ISO_DP"),
        5: "GND", 6: local("Maker MCU", "MAKER_USB_ISO_DM"), 8: "/MAKER_USB_DM",
        9: local("Maker MCU", "MAKER_USB_OE_N"), 10: local("Maker MCU", "MAKER_3V3_CORE"),
    }.items():
        add("U906", pin, net, "Maker USB data is disconnected unless physical carrier host VBUS is valid.", maker_usb)
    add_nc("U906", 3, "Unused alternate USB D+ input is intentionally NC.", maker_usb)
    add_nc("U906", 7, "Unused alternate USB D- input is intentionally NC.", maker_usb)
    for pin, net in {1: "/INTERNAL_USB_VBUS_VALID", 2: "GND", 3: local("Maker MCU", "MAKER_USB_OE_N")}.items():
        add("Q901", pin, net, "NMOS enables maker USB data only after physical host VBUS qualification.", maker_usb)
    for ref, first, second, requirement in (
        ("R925", "MAKER_3V3_CORE", "MAKER_USB_OE_N", "USB switch enable defaults high/disconnected."),
        ("R910", "MAKER_USB_OE_N", "MAKER_HOST_ACTIVE_N", "RP2350 senses the active-low qualified USB-connect state."),
        ("R911", "MAKER_3V3_CORE", "MAKER_HOST_ACTIVE_N", "Host-disconnected input has a defined high state."),
    ):
        first_net = first if first.startswith("/") or first == "GND" else local("Maker MCU", first)
        second_net = second if second.startswith("/") or second == "GND" else local("Maker MCU", second)
        add(ref, 1, first_net, requirement, maker_usb)
        add(ref, 2, second_net, requirement, maker_usb)

    protected_signals = [
        "MAKER_BOOT_N", "MAKER_RUN_N", "MAKER_SWDIO", "MAKER_SWCLK",
        "MAKER_UART_TX", "MAKER_UART_RX", "MAKER_I2C_SCL", "MAKER_I2C_SDA",
        "MAKER_SPI_SCK", "MAKER_SPI_MISO", "MAKER_SPI_MOSI", "MAKER_SPI_CS_N",
        *[f"MAKER_GPIO{i}" for i in range(15)], "MAKER_ADC0", "MAKER_ADC1", "MAKER_ADC2",
    ]
    exposed = lambda name: local("Maker MCU", f"J901_{name}")
    isolated = lambda name: local("Maker MCU", f"J901_{name}_ISO")
    maker_boundary = "TI SN74CB3T3245 and TPD4E05U06 datasheets plus Ducktop2 protected-maker-header contract"
    for bank in range(4):
        ref = f"U{910 + bank}"
        add_nc(ref, 1, "Unused SN74CB3T3245 pin.", maker_boundary)
        add(ref, 10, "GND", "Powered-off maker isolator ground.", maker_boundary)
        add(ref, 19, local("Maker MCU", "MAKER_HEADER_OE_N"), "All maker signals default disconnected until the rail is valid.", maker_boundary)
        add(ref, 20, local("Maker MCU", "MAKER_3V3_CORE"), "Powered-off maker isolator supply.", maker_boundary)
        for channel in range(8):
            index = bank * 8 + channel
            a_pin, b_pin = 2 + channel, 18 - channel
            if index < len(protected_signals):
                signal = protected_signals[index]
                add(ref, a_pin, local("Maker MCU", signal), "RP2350-side protected maker signal.", maker_boundary)
                add(ref, b_pin, isolated(signal), "Powered-off-tolerant maker signal boundary.", maker_boundary)
            else:
                add_nc(ref, a_pin, "Unused maker isolator channel.", maker_boundary)
                add_nc(ref, b_pin, "Unused maker isolator channel.", maker_boundary)
    for index, signal in enumerate(protected_signals):
        ref = f"R{932 + index}"
        add(ref, 1, isolated(signal), "330R fault-limit resistor protected side.", maker_boundary)
        add(ref, 2, exposed(signal), "330R fault-limit resistor connector side.", maker_boundary)
    for bank in range(8):
        ref = f"U{914 + bank}"
        add_many(ref, [3, 8], "GND", "Maker-header ESD return.", maker_boundary)
        for pin in [6, 7, 9, 10]:
            add_nc(ref, pin, "Unused TPD4E05U06 package pin.", maker_boundary)
        for channel, pin in enumerate([1, 2, 4, 5]):
            index = bank * 4 + channel
            if index < len(protected_signals):
                add(ref, pin, exposed(protected_signals[index]), "Connector-side 5.5V-standoff ESD shunt.", maker_boundary)
            else:
                add_nc(ref, pin, "Unused final ESD channel.", maker_boundary)
    for pin, net in {1: local("Maker MCU", "MAKER_HEADER_VALID"), 2: "GND", 3: local("Maker MCU", "MAKER_3V3_CORE")}.items():
        add("U922", pin, net, "Maker-header isolators release only after the local 3.3V rail is valid.", maker_boundary)
    for pin, net in {1: local("Maker MCU", "MAKER_HEADER_VALID"), 2: "GND", 3: local("Maker MCU", "MAKER_HEADER_OE_N")}.items():
        add("Q903", pin, net, "Hardware gate defaults all external maker signals disconnected.", maker_boundary)
    add("R930", 1, local("Maker MCU", "MAKER_3V3_CORE"), "Maker isolator disable pull-up rail.", maker_boundary)
    add("R930", 2, local("Maker MCU", "MAKER_HEADER_OE_N"), "Maker isolator default-off control.", maker_boundary)
    add("R931", 1, local("Maker MCU", "MAKER_3V3_CORE"), "Maker rail supervisor pull-up.", maker_boundary)
    add("R931", 2, local("Maker MCU", "MAKER_HEADER_VALID"), "Maker rail-valid signal.", maker_boundary)

    header = {
        1: "GND", 2: "J901_5V_OUT", 3: "GND", 4: "J901_3V3_OUT",
        **{5 + i: f"J901_{name}" for i, name in enumerate(protected_signals[:27])},
        33: "GND", 34: "GND", 35: "J901_MAKER_ADC0",
        36: "J901_MAKER_ADC1", 37: "J901_3V3_OUT", 38: "GND",
        39: "J901_MAKER_ADC2", 40: "GND",
    }
    for pin, name in header.items():
        expected = "GND" if name == "GND" else local("Maker MCU", name)
        add("J901", pin, expected, "Keyed JST PUD maker header exposes only protected signals and current-limited power.", maker_boundary)
    add_nc("J901", 32, "Header pin 32 is intentionally reserved and unconnected.", maker)
    for pin, net in {1: local("Maker MCU", "MAKER_SWD_VTREF"), 2: local("Maker MCU", "MAKER_SWDIO"),
                     3: local("Maker MCU", "MAKER_RUN_N"), 4: local("Maker MCU", "MAKER_SWCLK"),
                     5: "GND"}.items():
        add("J902", pin, net, "TC2030 Cortex SWD target pinout; VTref is sense-only through 10k.", "Tag-Connect TC2030-CTX pinout")
    add_nc("J902", 6, "SWO is not available on RP2350 SWD.", "Tag-Connect TC2030-CTX pinout")


def load_current_architecture_overrides() -> None:
    """Replace retired contracts for references reused by the current design."""
    project = "Ducktop2 released five-port USB-C and optional-radio architecture"

    # Pins reused by the current EC/source-manager allocation.
    for pin in (33, 37, 39, 90, 91, 96):
        contracts.pop(("U4", str(pin)), None)
    for pin, net in {
        33: "/PD1_VALID_N", 37: "/PD2_VALID_N",
        39: "/PD1_TCPC_IRQ_N", 90: "/PD2_TCPC_IRQ_N",
        91: "/RADIO_DB_PWR_EN", 96: "/PD_PROTECT_FAULT_N",
    }.items():
        add("U4", pin, net, "Current STM32 source-manager and optional-radio allocation.", project)

    clear_ref_contracts("U44")
    for pin, net in {
        1: "/EC & MCU/SOURCE_MGR_INT_N", 2: "GND", 3: "/EC & MCU/NRST_NET",
        4: "/PD1_PATH_EN", 5: "/PD2_PATH_EN", 6: "/EC & MCU/SOURCE_MGR_SPARE1",
        7: "/PD1_EFUSE_FAULT_N", 8: "/PD2_EFUSE_FAULT_N", 9: "/EC & MCU/SOURCE_MGR_SPARE2",
        10: "/PACK_FAULT_N", 11: "/AUX_FAULT_N", 12: "GND", 13: "/PACK_RETRY_PULSE",
        14: "/AUX_PGOOD", 15: "/MAIN_USB_VALID_N", 16: "/MAIN_AUX_VALID_N",
        17: "/AON_FAULT_N", 18: "/RADIO_DB_PG", 19: "/RADIO_DB_FAULT_N",
        20: "/RADIO_DB_PRESENT_N", 21: "GND", 22: "/I2C_SCL", 23: "/I2C_SDA", 24: "/MCU_3V3",
    }.items():
        add("U44", pin, net, "TCA9535 source manager and optional-radio status allocation.", project)

    contracts.pop(("A1", "129"), None)
    add("A1", 129, "/PD_PROTECT_FAULT_N", "Mu input receives the combined USB-C connector-protection fault.", project)

    # Current Wi-Fi/OLED sheet path.  These references survived the sheet rename.
    clear_ref_contracts("F10", "R170", "R171", "U170", "C187")
    wifi = "Ducktop2 Wi-Fi powered-off isolation contract"
    add("F10", 1, "/PCIE_3V3", "E-key rail fuse input.", wifi)
    add("F10", 2, local("Wi-Fi/Bluetooth & OLEDs", "WIFI_3V3"), "Fused E-key local rail.", wifi)
    for ref, signal in (("R170", "WIFI_W_DISABLE1_N"), ("R171", "WIFI_W_DISABLE2_N")):
        add(ref, 1, local("Wi-Fi/Bluetooth & OLEDs", "WIFI_3V3"), "Radio-disable pull-up follows E-key power.", wifi)
        add(ref, 2, local("Wi-Fi/Bluetooth & OLEDs", signal), "Module-side radio-disable signal.", wifi)
    for pin, net in {
        1: "/WIFI_W_DISABLE1_N_EC", 7: local("Wi-Fi/Bluetooth & OLEDs", "WIFI_W_DISABLE1_N"),
        6: "/WIFI_W_DISABLE2_N_EC", 2: local("Wi-Fi/Bluetooth & OLEDs", "WIFI_W_DISABLE2_N"),
        3: "GND", 4: "GND", 8: local("Wi-Fi/Bluetooth & OLEDs", "WIFI_3V3"),
    }.items():
        add("U170", pin, net, "Ioff buffer prevents back-power through E-key control pins.", wifi)
    add_nc("U170", 5, "Unused SN74LVC3G34 channel pin.", wifi)
    add("C187", 1, local("Wi-Fi/Bluetooth & OLEDs", "WIFI_3V3"), "E-key isolator bypass rail.", wifi)
    add("C187", 2, "GND", "E-key isolator bypass return.", wifi)

    # Two default-off PD input paths selected by LTC4418.
    clear_ref_contracts("U14", "U41", "U42", "U720", "U721", "Q15", "Q16", "Q17", "Q18")
    selector = "LTC4418 two-input prioritized USB-PD selector"
    for pin, net in {
        1: local("Power Inputs", "PD_SEL_TMR"), 2: local("Power Inputs", "PD1_SEL_UV"),
        3: local("Power Inputs", "PD1_SEL_OV"), 4: local("Power Inputs", "PD2_SEL_UV"),
        5: local("Power Inputs", "PD2_SEL_OV"), 7: "GND", 8: local("Power Inputs", "PD_SEL_INTVCC"),
        9: "/PD1_VALID_N", 10: "/PD2_VALID_N", 11: local("Power Inputs", "PD2_SEL_GATE"),
        12: local("Power Inputs", "PD2_SEL_FET_COMMON"), 13: local("Power Inputs", "PD1_SEL_GATE"),
        14: local("Power Inputs", "PD1_SEL_FET_COMMON"), 15: "/USB_PD_SELECTED",
        16: local("Power Inputs", "PD2_VBUS_GATED"), 17: local("Power Inputs", "PD1_VBUS_GATED"),
        18: local("Power Inputs", "PD_SEL_INTVCC"), 19: local("Power Inputs", "PD_SEL_INTVCC"),
        20: "GND", 21: "GND",
    }.items():
        add("U14", pin, net, "Two-input PD selector connection.", selector)
    add_nc("U14", 6, "LTC4418 cascade input is unused.", selector)

    for port, input_ref, output_ref in ((1, "Q15", "Q16"), (2, "Q17", "Q18")):
        for ref in (input_ref, output_ref):
            add(ref, 1, local("Power Inputs", f"PD{port}_SEL_GATE"), "LTC4418 selector FET gate.", selector)
            add_many(ref, (2, 3, 4), local("Power Inputs", f"PD{port}_SEL_FET_COMMON"), "Back-to-back selector FET common source.", selector)
        add(input_ref, 5, local("Power Inputs", f"PD{port}_VBUS_GATED"), "Selected input-side drain.", selector)
        add(output_ref, 5, "/USB_PD_SELECTED", "Common selected USB-PD output.", selector)

    for port, ref in ((1, "U41"), (2, "U42")):
        prefix = f"PD{port}"
        tps = "TI TPS25751A dead-battery DRP controller reference connection"
        pin_map = {
            1: local("Power Inputs", f"{prefix}_LDO3V3"),
            2: local("Power Inputs", f"{prefix}_LDO3V3") if port == 1 else "GND",
            3: "GND", 4: local("Power Inputs", f"{prefix}_LDO1V5"),
            5: "GND", 6: "GND", 7: "GND", 8: f"/{prefix}_I2C_SDA", 9: f"/{prefix}_I2C_SCL",
            10: f"/{prefix}_TCPC_IRQ_N", 11: "GND", 12: "GND", 13: "GND", 14: "GND",
            15: local("Power Inputs", f"{prefix}_DRAIN_THERMAL"),
            16: local("Power Inputs", f"{prefix}_EEPROM_SDA"),
            17: local("Power Inputs", f"{prefix}_EEPROM_SCL"),
            18: local("Power Inputs", f"{prefix}_EEPROM_IRQ_N"), 19: "GND",
            20: local("Power Inputs", f"{prefix}_PPHV"), 23: f"/{prefix}_VBUS_RAW",
            26: local("Power Inputs", f"{prefix}_GPIO_DFP"), 27: "GND",
            28: local("Power Inputs", f"{prefix}_CC1_SYS"),
            29: local("Power Inputs", f"{prefix}_CC2_SYS"),
            30: local("Power Inputs", f"{prefix}_DRAIN_THERMAL"), 31: "GND",
            32: f"/{prefix}_VBUS_RAW", 34: "/USB_PORT_5V",
            36: local("Power Inputs", f"{prefix}_GPIO_ATTACH"),
            37: local("Power Inputs", f"{prefix}_GPIO_FLIP"), 38: "/MCU_3V3", 39: "GND",
            40: local("Power Inputs", f"{prefix}_DRAIN_THERMAL"),
        }
        for pin, net in pin_map.items():
            add(ref, pin, net, "TPS25751A port controller pin contract.", tps)

    for port, ref in ((1, "U720"), (2, "U721")):
        prefix = f"PD{port}"
        efuse = "TI TPS26630 default-off negotiated-input protection contract"
        for pin in (1, 2, 5):
            add(ref, pin, local("Power Inputs", f"{prefix}_PPHV"), "Protected-input source pins.", efuse)
        for pin, net in {
            6: local("Power Inputs", f"{prefix}_EFUSE_UV"), 7: local("Power Inputs", f"{prefix}_EFUSE_OV"),
            8: "GND", 9: local("Power Inputs", f"{prefix}_EFUSE_DVDT"),
            10: local("Power Inputs", f"{prefix}_EFUSE_ILIM"), 11: "GND",
            12: local("Power Inputs", f"{prefix}_EFUSE_SHDN"), 14: f"/{prefix}_EFUSE_FAULT_N",
            15: "GND", 17: local("Power Inputs", f"{prefix}_VBUS_GATED"),
            18: local("Power Inputs", f"{prefix}_VBUS_GATED"), 25: "GND",
        }.items():
            add(ref, pin, net, "Default-off negotiated-input eFuse connection.", efuse)
        for pin in (3, 4, 13, 16, 19, 20, 21, 22, 23, 24):
            add_nc(ref, pin, "Unused TPS26630 function is explicitly NC.", efuse)

    # Dual-role connector, redriver, CC/USB2 protector, EEPROM, and USB2 gate.
    dual_ports = {
        1: {"j": "J21", "mux": "U2000", "protect": "U2001", "eeprom": "U2002", "usb2": "U2003",
            "control": "U2004", "qualifier": "U2006",
            "host_dp": "/USBC1_DP", "host_dm": "/USBC1_DM", "host_tx_p": "/USBC1_SSTX_P", "host_tx_n": "/USBC1_SSTX_N"},
        2: {"j": "J11", "mux": "U2010", "protect": "U2011", "eeprom": "U2012", "usb2": "U2013",
            "control": "U2014", "qualifier": "U2016",
            "host_dp": "/HUB_DS1_DP", "host_dm": "/HUB_DS1_DM", "host_tx_p": "/HUB_DS1_SSTX_P", "host_tx_n": "/HUB_DS1_SSTX_N"},
    }
    clear_ref_contracts(*(value for cfg in dual_ports.values() for value in (
        cfg["j"], cfg["mux"], cfg["protect"], cfg["eeprom"], cfg["usb2"],
        cfg["control"], cfg["qualifier"],
    )))
    for port, cfg in dual_ports.items():
        prefix = f"PD{port}"
        source = "Ducktop2 dual-role USB 3.2 Gen 2 plus USB-PD port contract"
        jref = cfg["j"]
        add_many(jref, ("A1", "A12", "B1", "B12", "SH"), "GND", "Connector grounds and shield.", source)
        add_many(jref, ("A4", "A9", "B4", "B9"), f"/{prefix}_VBUS_RAW", "Raw connector VBUS before the default-off eFuse.", source)
        for pin, net in {
            "A5": local("Power Inputs", f"{prefix}_CC1_CONN"), "B5": local("Power Inputs", f"{prefix}_CC2_CONN"),
            "A6": local("Power Inputs", f"{prefix}_DP_CONN"), "B6": local("Power Inputs", f"{prefix}_DP_CONN"),
            "A7": local("Power Inputs", f"{prefix}_DM_CONN"), "B7": local("Power Inputs", f"{prefix}_DM_CONN"),
            "A2": local("Power Inputs", f"{prefix}_TX1_P"), "A3": local("Power Inputs", f"{prefix}_TX1_N"),
            "B2": local("Power Inputs", f"{prefix}_TX2_P"), "B3": local("Power Inputs", f"{prefix}_TX2_N"),
            "B11": local("Power Inputs", f"{prefix}_RX1_P"), "B10": local("Power Inputs", f"{prefix}_RX1_N"),
            "A11": local("Power Inputs", f"{prefix}_RX2_P"), "A10": local("Power Inputs", f"{prefix}_RX2_N"),
        }.items():
            add(jref, pin, net, "Dual-role connector signal.", source)
        add_nc(jref, "A8", "SBU1 is unused.", source)
        add_nc(jref, "B8", "SBU2 is unused.", source)

        mux = cfg["mux"]
        mux_map = {
            1: "/SYS_3V3", 2: local("Power Inputs", f"{prefix}_MUX_SSEQ1"),
            3: local("Power Inputs", f"{prefix}_MUX_EQCFG"), 4: local("Power Inputs", f"{prefix}_MUX_SLEEP_N"),
            6: "/SYS_3V3", 14: local("Power Inputs", f"{prefix}_MUX_VIO"),
            15: cfg["host_tx_n"], 16: cfg["host_tx_p"], 17: local("Power Inputs", f"{prefix}_MUX_MODE"),
            18: local("Power Inputs", f"{prefix}_SSRX_RAW_N"), 19: local("Power Inputs", f"{prefix}_SSRX_RAW_P"),
            20: "/SYS_3V3", 21: local("Power Inputs", f"{prefix}_MUX_FLIP"), 22: "GND",
            26: local("Power Inputs", f"{prefix}_MUX_EN"), 27: "GND", 28: "/SYS_3V3",
            30: local("Power Inputs", f"{prefix}_RX1_P"), 31: local("Power Inputs", f"{prefix}_RX1_N"),
            33: local("Power Inputs", f"{prefix}_CTX1_RAW_P"), 34: local("Power Inputs", f"{prefix}_CTX1_RAW_N"),
            36: local("Power Inputs", f"{prefix}_RX2_N"), 37: local("Power Inputs", f"{prefix}_RX2_P"),
            39: local("Power Inputs", f"{prefix}_CTX2_RAW_N"), 40: local("Power Inputs", f"{prefix}_CTX2_RAW_P"), 41: "GND",
        }
        for pin, net in mux_map.items():
            add(mux, pin, net, "TUSB1142 orientation and Gen 2 redriver signal.", source)
        for pin in (5, 7, 8, 9, 10, 11, 12, 13, 23, 24, 25, 29, 32, 35, 38):
            add_nc(mux, pin, "Unused TUSB1142 pin is explicitly NC.", source)

        protect = cfg["protect"]
        for pin, net in {
            1: local("Power Inputs", f"{prefix}_DP_CONN"), 2: local("Power Inputs", f"{prefix}_DM_CONN"),
            3: local("Power Inputs", f"{prefix}_CC_ESD_VBIAS"), 4: local("Power Inputs", f"{prefix}_CC1_CONN"),
            5: local("Power Inputs", f"{prefix}_CC2_CONN"), 6: local("Power Inputs", f"{prefix}_CC2_CONN"),
            7: local("Power Inputs", f"{prefix}_CC1_CONN"), 8: "GND",
            9: local("Power Inputs", f"{prefix}_CC_FAULT_LOCAL_N"), 10: local("Power Inputs", f"{prefix}_LDO3V3"),
            11: local("Power Inputs", f"{prefix}_CC2_SYS"), 12: local("Power Inputs", f"{prefix}_CC1_SYS"),
            13: "GND", 14: local("Power Inputs", f"{prefix}_DM_HOST_SWITCHED"),
            15: local("Power Inputs", f"{prefix}_DP_HOST_SWITCHED"), 18: "GND", 21: "GND",
        }.items():
            add(protect, pin, net, "TPD4S201 CC and USB2 short-to-VBUS protection path.", source)
        for pin in (16, 17, 19, 20):
            add_nc(protect, pin, "Unused TPD4S201 pin is explicitly NC.", source)

        eeprom = cfg["eeprom"]
        for pin in (1, 2, 3, 4, 7):
            add(eeprom, pin, "GND", "Private TCPC EEPROM address/write-protect strap.", source)
        add(eeprom, 5, local("Power Inputs", f"{prefix}_EEPROM_SDA"), "Private TCPC EEPROM SDA.", source)
        add(eeprom, 6, local("Power Inputs", f"{prefix}_EEPROM_SCL"), "Private TCPC EEPROM SCL.", source)
        add(eeprom, 8, local("Power Inputs", f"{prefix}_LDO3V3"), "Private EEPROM follows TCPC LDO.", source)

        usb2 = cfg["usb2"]
        for pin, net in {
            1: "GND", 2: cfg["host_dp"], 4: local("Power Inputs", f"{prefix}_DP_HOST_SWITCHED"),
            5: "GND", 6: local("Power Inputs", f"{prefix}_DM_HOST_SWITCHED"), 8: cfg["host_dm"],
            9: local("Power Inputs", f"{prefix}_USB2_OE_N"), 10: "/SYS_3V3",
        }.items():
            add(usb2, pin, net, "USB2 remains disconnected until DFP data role is confirmed.", source)
        add_nc(usb2, 3, "Unused TS3USB30E throw.", source)
        add_nc(usb2, 7, "Unused TS3USB30E throw.", source)

        control = cfg["control"]
        for pin, net in {
            1: local("Power Inputs", f"{prefix}_GPIO_FLIP"),
            2: "GND",
            3: local("Power Inputs", f"{prefix}_HOST_ATTACHED"),
            4: local("Power Inputs", f"{prefix}_MUX_EN"),
            5: "/SYS_3V3",
            6: local("Power Inputs", f"{prefix}_MUX_FLIP"),
        }.items():
            add(control, pin, net, "Partial-power-down mux controls fail off when the TCPC is unavailable.", source)

        qualifier = cfg["qualifier"]
        for pin, net in {
            1: local("Power Inputs", f"{prefix}_GPIO_DFP"),
            2: local("Power Inputs", f"{prefix}_GPIO_ATTACH"),
            3: "GND",
            4: local("Power Inputs", f"{prefix}_HOST_ATTACHED"),
            5: "/SYS_3V3",
        }.items():
            add(qualifier, pin, net, "Host data is enabled only when TPS25751A reports both DFP role and attachment.", source)

    # Four-port hub. Downstream port 1 feeds J11; ports 2/3/4 feed J22/J23/J12.
    clear_ref_contracts("U1700", "J22", "J23", "J12")
    hub_sheet = "Native USB-C I/O"
    hub = "Microchip USB7206C four-active-port USB 3.2 hub contract"
    for pin, net in {
        2: "/INTERNAL_USB_VBUS_VALID",
        5: "/HUB_DS1_DP", 6: "/HUB_DS1_DM", 7: local(hub_sheet, "HUB_DS1_TX_RAW_P"),
        8: local(hub_sheet, "HUB_DS1_TX_RAW_N"), 10: "/HUB_DS1_SSRX_P", 11: "/HUB_DS1_SSRX_N",
        14: local(hub_sheet, "HUB_DS2_DP"), 15: local(hub_sheet, "HUB_DS2_DM"),
        16: local(hub_sheet, "HUB_DS2_TX_RAW_P"), 17: local(hub_sheet, "HUB_DS2_TX_RAW_N"),
        19: local(hub_sheet, "HUB_DS2_SSRX_P"), 20: local(hub_sheet, "HUB_DS2_SSRX_N"),
        27: local(hub_sheet, "HUB_DS3_DP"), 28: local(hub_sheet, "HUB_DS3_DM"),
        29: local(hub_sheet, "HUB_DS3_TX_RAW_P"), 30: local(hub_sheet, "HUB_DS3_TX_RAW_N"),
        32: local(hub_sheet, "HUB_DS3_SSRX_P"), 33: local(hub_sheet, "HUB_DS3_SSRX_N"),
        34: local(hub_sheet, "HUB_DS4_DP"), 35: local(hub_sheet, "HUB_DS4_DM"),
        36: local(hub_sheet, "HUB_DS4_TX_RAW_P"), 37: local(hub_sheet, "HUB_DS4_TX_RAW_N"),
        39: local(hub_sheet, "HUB_DS4_SSRX_P"), 40: local(hub_sheet, "HUB_DS4_SSRX_N"),
        89: "/USBC2_DP", 90: "/USBC2_DM", 91: local(hub_sheet, "HUB_UP_TX_RAW_P"),
        92: local(hub_sheet, "HUB_UP_TX_RAW_N"), 94: "/USBC2_SSTX_P", 95: "/USBC2_SSTX_N",
    }.items():
        add("U1700", pin, net, "Hub upstream or active downstream data lane.", hub)
    for pin, ref, name in (
        (41, "R1733", "HUB_DIS6_DM"),
        (42, "R1732", "HUB_DIS6_DP"),
        (81, "R1730", "HUB_DIS5_DP"),
        (82, "R1731", "HUB_DIS5_DM"),
    ):
        strap_net = local(hub_sheet, name)
        add("U1700", pin, strap_net, "Unused USB7206C downstream port strap is held high through a dedicated zero-ohm link.", hub)
        add(ref, 1, "/SYS_3V3", "Zero-ohm source for the mandatory high port-disable strap.", hub)
        add(ref, 2, strap_net, "Zero-ohm destination at the USB7206C D+/D- strap pin.", hub)
    for pin in (83, 84, 86, 87):
        add_nc("U1700", pin, "Unused hub downstream port is explicitly disabled and NC.", hub)

    for jref, ds in (("J22", 2), ("J23", 3), ("J12", 4)):
        source = "Ducktop2 source-only USB 3.2 Gen 2 port contract"
        add_many(jref, ("A1", "A12", "B1", "B12", "SH"), "GND", "Connector grounds and shield.", source)
        add_many(jref, ("A4", "A9", "B4", "B9"), local(hub_sheet, f"{jref}_VBUS"), "Current-limited source VBUS.", source)
        for pin, net in {
            "A5": local(hub_sheet, f"{jref}_CC1"), "B5": local(hub_sheet, f"{jref}_CC2"),
            "A6": local(hub_sheet, f"HUB_DS{ds}_DP"), "B6": local(hub_sheet, f"HUB_DS{ds}_DP"),
            "A7": local(hub_sheet, f"HUB_DS{ds}_DM"), "B7": local(hub_sheet, f"HUB_DS{ds}_DM"),
            "A2": local(hub_sheet, f"{jref}_TX1_P"), "A3": local(hub_sheet, f"{jref}_TX1_N"),
            "B2": local(hub_sheet, f"{jref}_TX2_P"), "B3": local(hub_sheet, f"{jref}_TX2_N"),
            "B11": local(hub_sheet, f"{jref}_RX1_P"), "B10": local(hub_sheet, f"{jref}_RX1_N"),
            "A11": local(hub_sheet, f"{jref}_RX2_P"), "A10": local(hub_sheet, f"{jref}_RX2_N"),
        }.items():
            add(jref, pin, net, "Source-only connector data or CC signal.", source)
        add_nc(jref, "A8", "SBU1 is unused.", source)
        add_nc(jref, "B8", "SBU2 is unused.", source)

    # Two four-pin OLED modules behind dedicated TCA9548A channels.
    clear_ref_contracts("U45", "J41", "J45")
    oled = "Dual four-pin SSD1306 modules through TCA9548A"
    for pin, net in {
        1: "GND", 2: "GND", 3: "/SERVICE_MUX_RESET_N",
        4: local("Wi-Fi/Bluetooth & OLEDs", "OLED_A_SDA"), 5: local("Wi-Fi/Bluetooth & OLEDs", "OLED_A_SCL"),
        6: local("Wi-Fi/Bluetooth & OLEDs", "OLED_B_SDA"), 7: local("Wi-Fi/Bluetooth & OLEDs", "OLED_B_SCL"),
        8: "/PD1_I2C_SDA", 9: "/PD1_I2C_SCL", 10: "/PD2_I2C_SDA", 11: "/PD2_I2C_SCL",
        12: "GND", 21: "GND", 22: "/I2C_SCL", 23: "/I2C_SDA", 24: "/MCU_3V3",
    }.items():
        add("U45", pin, net, "OLED and two TCPC I2C channel allocation.", oled)
    for pin in range(13, 21):
        add_nc("U45", pin, "Unused TCA9548A channel is explicitly NC.", oled)
    for ref, suffix in (("J41", "A"), ("J45", "B")):
        for pin, net in {
            1: "GND", 2: "/MCU_3V3", 3: local("Wi-Fi/Bluetooth & OLEDs", f"OLED_{suffix}_SCL"),
            4: local("Wi-Fi/Bluetooth & OLEDs", f"OLED_{suffix}_SDA"),
        }.items():
            add(ref, pin, net, "User-supplied SSD1306 module pinout GND/VDD/SCK/SDA.", oled)

    # The radio/GNSS/codec assembly is optional. The mainboard boundary must be
    # inert when J2300 is empty and may not back-power an absent daughterboard.
    clear_ref_contracts("J2300", "U2300", "U2303", "U2304")
    radio = "Ducktop2 optional radio daughterboard fail-safe interface"
    add_many("J2300", range(1, 9), local("Optional Radio Daughterboard Interface", "RADIO_DB_5V"), "Parallel current-sharing radio-board supply contacts.", radio)
    add_many("J2300", (9, 10, 11, 12, 13, 14, 15, 16, 21, 22, 27, 32, 37, 43, *range(45, 61), "MP"), "GND", "Ground and return contacts remain harmless with the daughterboard absent.", radio)
    for pin in (17, 18):
        add("J2300", pin, local("Optional Radio Daughterboard Interface", "RADIO_CODEC_USB_VBUS_DB"), "Current-limited codec USB VBUS contacts.", radio)
    radio_header = {
        19: local("Optional Radio Daughterboard Interface", "RADIO_CODEC_USB_DP_DB"),
        20: local("Optional Radio Daughterboard Interface", "RADIO_CODEC_USB_DM_DB"),
        23: local("Optional Radio Daughterboard Interface", "RADIO_VHF_UART_TX_DB"),
        24: local("Optional Radio Daughterboard Interface", "RADIO_VHF_UART_RX_DB"),
        25: local("Optional Radio Daughterboard Interface", "RADIO_UHF_UART_TX_DB"),
        26: local("Optional Radio Daughterboard Interface", "RADIO_UHF_UART_RX_DB"),
        28: local("Optional Radio Daughterboard Interface", "RADIO_VHF_PTT_N_DB"),
        29: local("Optional Radio Daughterboard Interface", "RADIO_UHF_PTT_N_DB"),
        30: local("Optional Radio Daughterboard Interface", "RADIO_VHF_PD_N_DB"),
        31: local("Optional Radio Daughterboard Interface", "RADIO_UHF_PD_N_DB"),
        33: local("Optional Radio Daughterboard Interface", "RADIO_VHF_SQL_DB"),
        34: local("Optional Radio Daughterboard Interface", "RADIO_UHF_SQL_DB"),
        35: local("Optional Radio Daughterboard Interface", "RADIO_VHF_RF_SEL_3V3_DB"),
        36: local("Optional Radio Daughterboard Interface", "RADIO_UHF_RF_SEL_3V3_DB"),
        38: local("Optional Radio Daughterboard Interface", "GNSS_UART_RX_DB"),
        39: local("Optional Radio Daughterboard Interface", "GNSS_UART_TX_DB"),
        40: local("Optional Radio Daughterboard Interface", "GNSS_RESET_N_DB"),
        41: local("Optional Radio Daughterboard Interface", "GNSS_PPS_DB"),
        42: local("Optional Radio Daughterboard Interface", "GNSS_EXTINT_DB"),
        44: "/RADIO_DB_PRESENT_N",
    }
    for pin, net in radio_header.items():
        add("J2300", pin, net, "Optional daughterboard signal boundary.", radio)
    radio_signals = {
        23: "RADIO_VHF_UART_TX", 24: "RADIO_VHF_UART_RX",
        25: "RADIO_UHF_UART_TX", 26: "RADIO_UHF_UART_RX",
        28: "RADIO_VHF_PTT_N", 29: "RADIO_UHF_PTT_N",
        30: "RADIO_VHF_PD_N", 31: "RADIO_UHF_PD_N",
        33: "RADIO_VHF_SQL", 34: "RADIO_UHF_SQL",
        35: "RADIO_VHF_RF_SEL_3V3", 36: "RADIO_UHF_RF_SEL_3V3",
        38: "GNSS_UART_RX", 39: "GNSS_UART_TX", 40: "GNSS_RESET_N",
        41: "GNSS_PPS", 42: "GNSS_EXTINT",
    }
    for index, (pin, signal) in enumerate(radio_signals.items()):
        ref = f"R{2340 + index}"
        add(ref, 1, f"/{signal}", "Mainboard side of removable-radio fault isolation.", radio)
        add(ref, 2, radio_header[pin], "Connector side of removable-radio fault isolation.", radio)
    for pin, net in {
        1: "/RADIO_DB_PWR_EN", 2: "GND", 4: "/RADIO_DB_FAULT_N", 5: "/SYS_5V",
        6: local("Optional Radio Daughterboard Interface", "RADIO_DB_5V"),
        7: local("Optional Radio Daughterboard Interface", "RADIO_DB_DVDT"), 8: "GND",
        9: local("Optional Radio Daughterboard Interface", "RADIO_DB_ILM"),
    }.items():
        add("U2300", pin, net, "Default-off radio daughterboard load switch.", radio)
    add_nc("U2300", 3, "AUXOFF is unused.", radio)
    add_nc("U2300", 10, "ITIMER is unused for the released radio branch.", radio)
    for pin, net in {
        1: "GND", 2: "/RADIO_CODEC_USB_DP_HOST",
        4: local("Optional Radio Daughterboard Interface", "RADIO_CODEC_USB_DP_DB"), 5: "GND",
        6: local("Optional Radio Daughterboard Interface", "RADIO_CODEC_USB_DM_DB"),
        8: "/RADIO_CODEC_USB_DM_HOST", 9: local("Optional Radio Daughterboard Interface", "RADIO_USB_OE_N"),
        10: "/MCU_3V3",
    }.items():
        add("U2303", pin, net, "USB2 disconnect prevents an absent radio codec from loading or back-powering the host.", radio)
    add_nc("U2303", 3, "Unused USB switch throw.", radio)
    add_nc("U2303", 7, "Unused USB switch throw.", radio)
    for pin, net in {
        1: "/RADIO_CODEC_USB_VBUS_HOST", 2: "GND", 3: "/RADIO_DB_PG", 4: "/RADIO_DB_FAULT_N",
        5: local("Optional Radio Daughterboard Interface", "RADIO_CODEC_ILIM"),
        6: local("Optional Radio Daughterboard Interface", "RADIO_CODEC_USB_VBUS_DB"),
    }.items():
        add("U2304", pin, net, "Codec VBUS is separately current-limited and off when the radio board is absent.", radio)

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
            str(ROOT / "ducktop2.kicad_sch"),
        ],
        cwd=ROOT,
        check=True,
    )


def parse_netlist():
    root = ET.parse(NETLIST).getroot()
    comp_meta = {}
    comp_pins = {}
    libpins = {}

    for libpart in root.findall(".//libpart"):
        key = (libpart.get("lib") or "", libpart.get("part") or "")
        pins = {}
        pins_node = libpart.find("pins")
        if pins_node is not None:
            for pin in pins_node.findall("pin"):
                pins[pin.get("num") or ""] = {
                    "pin_name": pin.get("name") or "",
                    "pin_type": pin.get("type") or "",
                }
        libpins[key] = pins

    for comp in root.findall(".//comp"):
        ref = comp.get("ref") or ""
        libsource = comp.find("libsource")
        sheetpath = comp.find("sheetpath")
        props = {p.get("name"): p.get("value") for p in comp.findall("property")}
        lib = libsource.get("lib") if libsource is not None else ""
        part = libsource.get("part") if libsource is not None else ""
        comp_meta[ref] = {
            "ref": ref,
            "value": comp.findtext("value") or "",
            "lib": lib or "",
            "part": part or "",
            "footprint": comp.findtext("footprint") or "",
            "sheetname": sheetpath.get("names", "") if sheetpath is not None else "",
            "sheetfile": props.get("Sheetfile") or "",
            "dnp": "dnp" in props,
            "exclude_from_bom": "exclude_from_bom" in props,
            "libpins": libpins.get((lib or "", part or ""), {}),
        }
        comp_pins[ref] = {}

    for net in root.findall(".//net"):
        net_name = net.get("name") or ""
        for node in net.findall("node"):
            ref = node.get("ref") or ""
            pin = node.get("pin") or ""
            if ref and pin:
                comp_pins.setdefault(ref, {})[pin] = net_name

    return comp_meta, comp_pins


def pin_sort_key(pin: str):
    if pin.isdigit():
        return (0, int(pin))
    prefix = pin[:1]
    rest = pin[1:]
    if prefix in {"A", "B"} and rest.isdigit():
        return (1, prefix, int(rest))
    return (2, pin)


def ref_sort_key(ref: str):
    split = 0
    while split < len(ref) and not ref[split].isdigit():
        split += 1
    prefix = ref[:split]
    suffix = ref[split:]
    return (prefix, int(suffix) if suffix.isdigit() else 10**9, suffix)


def row_status(ref: str, pin: str, actual: str, contract: Contract | None):
    if contract is None:
        return (
            "REVIEW",
            "",
            "No explicit contract in this pass; review against datasheet/reference before fab.",
            "Not yet contract-checked",
        )
    if contract.mode == "unconnected":
        passed = re.fullmatch(
            rf"unconnected-\({re.escape(ref)}[A-Z]?-.*Pad{re.escape(pin)}\)",
            actual,
        ) is not None
    else:
        passed = actual == contract.expected
    return (
        "PASS" if passed else "FAIL",
        contract.expected,
        contract.requirement,
        contract.source,
    )


def generate_rows(comp_meta, comp_pins):
    rows = []
    missing_refs = sorted(CURRENT_REQUIRED_REFS - set(comp_meta), key=ref_sort_key)
    selected_refs = sorted(
        CURRENT_REQUIRED_REFS | {ref for ref, _pin in contracts if ref in comp_meta},
        key=ref_sort_key,
    )
    for ref in selected_refs:
        meta = comp_meta.get(ref)
        if not meta:
            continue
        all_pins = set(meta["libpins"]) | set(comp_pins.get(ref, {})) | {
            pin for (r, pin) in contracts
            if r == ref
        }
        for pin in sorted(all_pins, key=pin_sort_key):
            pin_meta = meta["libpins"].get(pin, {})
            actual = comp_pins.get(ref, {}).get(pin, "")
            contract = contracts.get((ref, pin))
            status, expected, requirement, source = row_status(ref, pin, actual, contract)
            rows.append({
                "status": status,
                "ref": ref,
                "value": meta["value"],
                "libpart": f'{meta["lib"]}:{meta["part"]}',
                "sheetfile": meta["sheetfile"],
                "pin": pin,
                "pin_name": pin_meta.get("pin_name", ""),
                "pin_type": pin_meta.get("pin_type", ""),
                "actual_net": actual,
                "expected_net": expected,
                "requirement": requirement,
                "source": source,
                "dnp": "yes" if meta["dnp"] else "no",
                "exclude_from_bom": "yes" if meta["exclude_from_bom"] else "no",
                "footprint": meta["footprint"],
            })
    return rows, missing_refs


def write_csv(rows) -> None:
    CSV_OUT.parent.mkdir(exist_ok=True)
    fields = [
        "status", "ref", "value", "libpart", "sheetfile", "pin", "pin_name", "pin_type",
        "actual_net", "expected_net", "requirement", "source", "dnp", "exclude_from_bom", "footprint",
    ]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md(rows, missing_refs) -> None:
    counts = Counter(row["status"] for row in rows)
    contracted = counts["PASS"] + counts["FAIL"]
    fail_rows = [row for row in rows if row["status"] == "FAIL"]
    review_by_ref = Counter(row["ref"] for row in rows if row["status"] == "REVIEW")
    review_refs = ", ".join(f"{ref} ({count})" for ref, count in review_by_ref.most_common(20))

    lines = [
        f"# Ducktop2 Pin-by-Pin Schematic Review - {REPORT_DATE}",
        "",
        "Generated from the live KiCad XML netlist. This table is a review aid, not a fab approval.",
        "",
        "## Files",
        "",
        f"- CSV table: `{CSV_OUT.relative_to(ROOT)}`",
        f"- Source netlist: `{NETLIST.relative_to(ROOT)}`",
        "- Contract source: `gen/generate_pin_review_table.py` and `gen/verify_design_contracts.py`",
        "",
        "## Summary",
        "",
        f"- Total high-risk pin rows emitted: {len(rows)}",
        f"- Explicitly contracted rows: {contracted}",
        f"- PASS: {counts['PASS']}",
        f"- FAIL: {counts['FAIL']}",
        f"- REVIEW: {counts['REVIEW']}",
        "",
    ]
    if missing_refs:
        lines.extend([
            "## Missing References",
            "",
            "These requested review references were not found in the netlist:",
            "",
        ])
        lines.extend(f"- `{ref}`" for ref in missing_refs)
        lines.append("")
    if fail_rows:
        lines.extend(["## Contract Failures", ""])
        for row in fail_rows[:50]:
            lines.append(f"- `{row['ref']}` pin `{row['pin']}` `{row['pin_name']}`: actual `{row['actual_net']}`, expected `{row['expected_net']}`")
        lines.append("")
    else:
        lines.extend([
            "## Contract Failures",
            "",
            "None in the generated table.",
            "",
        ])
    lines.extend([
        "## REVIEW Rows",
        "",
        "Rows marked `REVIEW` are intentionally included because they belong to important chips/modules,",
        "but they are not yet backed by a hard coded contract. They should be checked by a second",
        "reviewer against the datasheet or the relevant reference design before fabrication.",
        "",
        f"Most REVIEW-heavy refs: {review_refs or 'none'}",
        "",
        "## High-Risk Coverage Notes",
        "",
        "- Battery fuse/shunt path, BQ25798 single-input wiring, and BQ34Z100 fuel gauge pins are contracted.",
        "- STM32 power, reset, boot, SWD, VCAP, and EC buck pins are contracted; general GPIO allocation rows remain REVIEW.",
        "- LattePanda Mu VIN, USB2 allocation, native USB3 pairs, NVMe PCIe lanes, and exposed display outputs are contracted; the rest of the module pins remain REVIEW.",
        "- Both TPS25751A dual-role ports, three source-only USB-C ports, USB7206C hub, redrivers, protectors, EEPROMs, and default-off input paths are contracted.",
        "- The optional radio daughterboard boundary is contracted so an absent board cannot block normal laptop operation or receive back-power.",
        "- External HDMI, four-pin SSD1306 headers, TCA9548A, keyboard FFC, audio, and maker headers are contracted where the project has a clear decision.",
        "- PCM2900C playback/record, IM68A130 microphone, privacy-enable path, speaker BTL outputs, RTL8111H HSIO6 PCIe, MDI ESD, and JXD1 integrated-magnetics jack pins are explicitly contracted.",
        "- The native Mu eDP connector and panel harness are release-gated in docs/display-direct-edp.md because neither connector is routed through the carrier-board netlist.",
        "- REVIEW is not failure. It is a deliberate flag for independent review.",
        "",
        "## Independent Review Instructions",
        "",
        "Ask the reviewer to open the CSV, sort by `status`, and attack the design in this order:",
        "",
        "1. Any `FAIL` rows first.",
        "2. `REVIEW` rows on power, battery, high-speed, RF, and module connectors.",
        "3. Any row where the actual net name is surprising even if it passes the local contract.",
        "4. Footprints and mechanical orientation separately during PCB review.",
        "",
    ])
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    global REPORT_DATE, CSV_OUT, MD_OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-date",
        default=REPORT_DATE,
        help="date label used in output filenames (default: today)",
    )
    args = parser.parse_args()
    REPORT_DATE = args.report_date
    CSV_OUT = ROOT / "verification" / f"pin_by_pin_review_{args.report_date}.csv"
    MD_OUT = ROOT / "verification" / f"PIN_BY_PIN_REVIEW_{args.report_date}.md"
    load_contracts()
    load_current_architecture_overrides()
    export_netlist()
    comp_meta, comp_pins = parse_netlist()
    rows, missing_refs = generate_rows(comp_meta, comp_pins)
    write_csv(rows)
    write_md(rows, missing_refs)
    counts = Counter(row["status"] for row in rows)
    print(f"wrote {CSV_OUT}")
    print(f"wrote {MD_OUT}")
    print(f"rows={len(rows)} pass={counts['PASS']} fail={counts['FAIL']} review={counts['REVIEW']}")
    if counts["FAIL"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
