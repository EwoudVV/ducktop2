#!/usr/bin/env python3
"""Read-only independent regression checks for Ducktop2 schematic closure.

This checker intentionally imports none of the schematic generators or project
contract helpers. It consumes an already-exported KiCad XML netlist and guards
the exact electrical regressions found by the July 17-19 independent audits.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


class ClosureAudit:
    def __init__(self, netlist: Path) -> None:
        root = ET.parse(netlist).getroot()
        self.components: dict[str, dict[str, object]] = {}
        self.pin_nets: dict[tuple[str, str], str] = {}
        self.net_members: dict[str, set[tuple[str, str]]] = {}
        self.pin_names: dict[tuple[str, str], str] = {}
        self.failures: list[str] = []
        self.checks = 0

        lib_pins: dict[tuple[str, str], dict[str, str]] = {}
        for libpart in root.findall(".//libpart"):
            key = (libpart.get("lib") or "", libpart.get("part") or "")
            lib_pins[key] = {
                pin.get("num") or "": pin.get("name") or ""
                for pin in libpart.findall("./pins/pin")
            }

        for node in root.findall(".//comp"):
            ref = node.get("ref") or ""
            properties = {
                field.get("name") or "": field.text or ""
                for field in node.findall("./fields/field")
            }
            properties.update({
                prop.get("name") or "": prop.get("value") or ""
                for prop in node.findall("./property")
            })
            self.components[ref] = {
                "value": node.findtext("value") or "",
                "footprint": node.findtext("footprint") or "",
                "properties": properties,
            }
            source = node.find("libsource")
            if source is not None:
                key = (source.get("lib") or "", source.get("part") or "")
                for pin, name in lib_pins.get(key, {}).items():
                    self.pin_names[(ref, pin)] = name

        for net in root.findall(".//net"):
            name = net.get("name") or ""
            members = {
                (node.get("ref") or "", node.get("pin") or "")
                for node in net.findall("node")
            }
            self.net_members[name] = members
            for member in members:
                self.pin_nets[member] = name

    def check(self, condition: bool, label: str, got: object = None) -> None:
        self.checks += 1
        if not condition:
            suffix = "" if got is None else f"; got {got!r}"
            self.failures.append(label + suffix)

    def eq(self, got: object, want: object, label: str) -> None:
        self.check(got == want, f"{label}: expected {want!r}", got)

    def starts(self, got: str, want: str, label: str) -> None:
        self.check(got.startswith(want), f"{label}: expected prefix {want!r}", got)

    def pin(self, ref: str, pin: str, want: str, label: str | None = None) -> None:
        self.eq(self.pin_nets.get((ref, pin)), want, label or f"{ref}.{pin} net")

    def pin_name(self, ref: str, pin: str, want: str) -> None:
        self.eq(self.pin_names.get((ref, pin)), want, f"{ref}.{pin} library pin name")

    def value(self, ref: str) -> str:
        component = self.components.get(ref)
        return "" if component is None else str(component["value"])

    def footprint(self, ref: str) -> str:
        component = self.components.get(ref)
        return "" if component is None else str(component["footprint"])

    def prop(self, ref: str, name: str) -> str:
        component = self.components.get(ref)
        if component is None:
            return ""
        return str(component["properties"].get(name, ""))

    def value_starts(self, ref: str, want: str, label: str | None = None) -> None:
        self.starts(self.value(ref), want, label or f"{ref} value")

    def prop_eq(self, ref: str, name: str, want: str) -> None:
        self.eq(self.prop(ref, name), want, f"{ref} {name}")

    def absent(self, ref: str) -> None:
        self.check(ref not in self.components, f"obsolete component {ref} must be absent")


def run_checks(a: ClosureAudit) -> None:
    # TPS2553 regression: ILIM is physical pin 5 and OUT is physical pin 6.
    for pin, name, net in (
        ("1", "IN", "/SYS_5V"),
        ("2", "GND", "GND"),
        ("3", "EN", "/MU_HOST_ACTIVE"),
        ("4", "~{FAULT}", "/INTERNAL_USB_VBUS_FAULT_N"),
        ("5", "ILIM", "/Mu Carrier/INTERNAL_USB_VBUS_ILIM"),
        ("6", "OUT", "/Mu Carrier/INTERNAL_USB_VBUS"),
    ):
        a.pin_name("U770", pin, name)
        a.pin("U770", pin, net)

    # Battery entry, charger mandatory pins, fail-off CE, QON, and ship FET.
    a.pin("U11", "8", "/Power & Battery/PACK_POS_FUSED")
    a.value_starts("C725", "10u 25V X7R")
    a.pin("C725", "1", "/Power & Battery/PACK_POS_FUSED")
    a.pin("C725", "2", "GND")
    a.prop_eq("C725", "MPN", "GRM21BZ71E106KE15L")
    for pin in ("1", "2"):
        a.pin("J2", pin, "/Power & Battery/PACK_POS_RAW")
    for pin in ("3", "4"):
        a.pin("J2", pin, "/Power & Battery/PACK_NEG_RAW")
    a.pin("J2", "5", "/Power & Battery/CELL1_TAP")
    a.pin("J2", "6", "/Power & Battery/CELL2_TAP")
    for pin, name, net in (
        ("1", "VDD", "/Power & Battery/BMS_VDD"),
        ("2", "AVDD", "/Power & Battery/BMS_AVDD"),
        ("3", "VC5", "/Power & Battery/BMS_VC3_TOP"),
        ("4", "VC4", "/Power & Battery/BMS_VC3_TOP"),
        ("5", "VC3", "/Power & Battery/BMS_VC3_TOP"),
        ("6", "VC2", "/Power & Battery/BMS_VC2"),
        ("7", "VC1", "/Power & Battery/BMS_VC1"),
        ("8", "VC0", "/Power & Battery/BMS_VC0"),
        ("9", "VSS", "/Power & Battery/PACK_NEG_RAW"),
        ("10", "SRP", "/Power & Battery/BMS_SRP"),
        ("11", "SRN", "/Power & Battery/BMS_SRN"),
        ("12", "DSG", "/Power & Battery/BMS_DSG_DRV"),
        ("13", "CHG", "/Power & Battery/BMS_CHG_DRV"),
        ("14", "LD", "/Power & Battery/BMS_LD"),
        ("16", "CBI", "/Power & Battery/PACK_NEG_RAW"),
        ("17", "OCDP", "/Power & Battery/BMS_OCDP"),
        ("18", "TS", "/Power & Battery/BMS_TS_UNUSED"),
        ("20", "CCFG", "/Power & Battery/PACK_NEG_RAW"),
        ("22", "PRES", "/Power & Battery/BMS_PRES"),
        ("23", "CTRC", "/Power & Battery/PACK_NEG_RAW"),
        ("24", "CTRD", "/Power & Battery/PACK_NEG_RAW"),
    ):
        a.pin_name("U719", pin, name)
        a.pin("U719", pin, net)
    for pin, name in (("15", "LPWR"), ("19", "VTB"), ("21", "CBO")):
        a.pin_name("U719", pin, name)
        a.starts(a.pin_nets.get(("U719", pin), ""), "unconnected-(U719-",
                 f"U719.{pin} {name} must be explicitly NC")
    a.eq(a.footprint("U719"), "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", "U719 footprint")
    a.prop_eq("U719", "MPN", "BQ7791500PWR")
    for ref, value, p1, p2 in (
        ("R840", "1k 1%", "/Power & Battery/PACK_POS_RAW", "/Power & Battery/BMS_VDD"),
        ("R841", "75R 1%", "/Power & Battery/PACK_NEG_RAW", "/Power & Battery/BMS_VC0"),
        ("R842", "75R 1%", "/Power & Battery/CELL1_TAP", "/Power & Battery/BMS_VC1"),
        ("R843", "75R 1%", "/Power & Battery/CELL2_TAP", "/Power & Battery/BMS_VC2"),
        ("R844", "75R 1%", "/Power & Battery/PACK_POS_RAW", "/Power & Battery/BMS_VC3_TOP"),
        ("R845", "100R", "/Power & Battery/PACK_NEG_RAW", "/Power & Battery/BMS_SRP"),
        ("R846", "100R", "/Power & Battery/BMS_SENSE_N", "/Power & Battery/BMS_SRN"),
        ("R847", "4.53k 1%", "/Power & Battery/BMS_DSG_DRV", "/Power & Battery/BMS_DSG_GATE"),
        ("R848", "1k 1%", "/Power & Battery/BMS_CHG_DRV", "/Power & Battery/BMS_CHG_GATE"),
        ("R849", "1M 5%", "/Power & Battery/BMS_DSG_GATE", "/Power & Battery/BMS_SENSE_N"),
        ("R850", "3.3M 5%", "/Power & Battery/BMS_CHG_GATE", "/Power & Battery/FG_VSS"),
        ("R851", "453k 1%", "/Power & Battery/BMS_LD", "/Power & Battery/FG_VSS"),
        ("R852", "10k 5%", "/Power & Battery/PACK_POS_RAW", "/Power & Battery/BMS_PRES"),
        ("R853", "10k 1%", "/Power & Battery/BMS_TS_UNUSED", "/Power & Battery/PACK_NEG_RAW"),
        ("R854", "604k 1%", "/Power & Battery/BMS_OCDP", "/Power & Battery/PACK_NEG_RAW"),
    ):
        a.value_starts(ref, value)
        a.pin(ref, "1", p1)
        a.pin(ref, "2", p2)
    for ref, value, p1, p2 in (
        ("C840", "1u 25V", "/Power & Battery/BMS_VDD", "/Power & Battery/PACK_NEG_RAW"),
        ("C841", "1u 10V", "/Power & Battery/BMS_AVDD", "/Power & Battery/PACK_NEG_RAW"),
        ("C842", "1u 10V X7R", "/Power & Battery/BMS_VC0", "/Power & Battery/PACK_NEG_RAW"),
        ("C843", "1u 10V X7R", "/Power & Battery/BMS_VC1", "/Power & Battery/BMS_VC0"),
        ("C844", "1u 10V X7R", "/Power & Battery/BMS_VC2", "/Power & Battery/BMS_VC1"),
        ("C848", "1u 10V X7R", "/Power & Battery/BMS_VC3_TOP", "/Power & Battery/BMS_VC2"),
        ("C845", "100n", "/Power & Battery/BMS_SRP", "/Power & Battery/PACK_NEG_RAW"),
        ("C846", "100n", "/Power & Battery/BMS_SRP", "/Power & Battery/BMS_SRN"),
        ("C847", "100n", "/Power & Battery/BMS_SRN", "/Power & Battery/PACK_NEG_RAW"),
    ):
        a.value_starts(ref, value)
        a.pin(ref, "1", p1)
        a.pin(ref, "2", p2)
    a.value_starts("RS11", "8mOhm 1% 2W")
    a.pin("RS11", "1", "/Power & Battery/PACK_NEG_RAW")
    a.pin("RS11", "2", "/Power & Battery/BMS_SENSE_N")
    a.prop_eq("RS11", "MPN", "WSLP25128L000FEA")
    for ref, source, gate in (
        ("Q703", "/Power & Battery/BMS_SENSE_N", "/Power & Battery/BMS_DSG_GATE"),
        ("Q704", "/Power & Battery/FG_VSS", "/Power & Battery/BMS_CHG_GATE"),
    ):
        for pin in ("1", "2", "3"):
            a.pin(ref, pin, source)
        a.pin(ref, "4", gate)
        a.pin(ref, "5", "/Power & Battery/BMS_FET_COMMON")
        a.prop_eq(ref, "MPN", "CSD18540Q5B")
    a.absent("NTC2")
    a.absent("NTC4")
    for pin in ("2", "3", "8", "9"):
        a.pin("U2", pin, "/Power & Battery/VBUS_COMBINED")
    for pin in ("10", "11", "27"):
        a.pin("U2", pin, "GND")
    a.pin("U2", "16", "/Power & Battery/CHG_TS_FIXED")
    a.value_starts("R16", "5.24k 1%")
    a.pin("R16", "1", "/Power & Battery/REGN")
    a.pin("R16", "2", "/Power & Battery/CHG_TS_FIXED")
    a.value_starts("R705", "7.50k 1%")
    a.pin("R705", "1", "/Power & Battery/CHG_TS_FIXED")
    a.pin("R705", "2", "GND")
    a.pin("U2", "12", "/Power & Battery/PMIC_QON_PIN")
    a.pin("U2", "13", "/Power & Battery/CHG_CE_HW_N")
    a.pin("U2", "24", "/Power & Battery/SDRV_GATE")
    a.pin("Q25", "4", "/Power & Battery/SDRV_GATE")
    a.pin("Q25", "5", "/Power & Battery/PACK_POS_FUSED")
    a.pin("Q702", "1", "/PMIC_QON_ASSERT")
    a.pin("Q702", "2", "GND")
    a.pin("Q702", "3", "/Power & Battery/PMIC_QON_PIN")
    a.pin("R13", "1", "/PMIC_QON_ASSERT")
    a.pin("R13", "2", "GND")
    a.pin("D715", "1", "/CASE_PWRBTN_N")
    a.pin("D715", "2", "/Power & Battery/PMIC_QON_PIN")
    a.pin("D716", "1", "/CASE_PWRBTN_N")
    a.pin("D716", "2", "/MU_PWRBTN_N")
    a.eq(
        a.net_members.get("/Power & Battery/PMIC_QON_PIN"),
        {("D715", "2"), ("Q702", "3"), ("U2", "12")},
        "QON charger-domain membership",
    )
    a.absent("C184")
    a.pin("U10", "11", "/Power & Battery/FG_TS")
    a.value_starts("R855", "10k")
    a.pin("R855", "1", "/Power & Battery/FG_TS")
    a.pin("R855", "2", "/Power & Battery/FG_VSS")

    # AUX PGOOD and aggregate always-on cold-start boundary.
    a.pin("U12", "15", "/Power & Battery/AUX_PGTH")
    a.pin("U12", "16", "/AUX_PGOOD")
    for ref, p1, p2, value in (
        ("R739", "/Power & Battery/AUX_DC_PROTECTED", "/Power & Battery/AUX_PGTH", "332k 0.1%"),
        ("R740", "/Power & Battery/AUX_PGTH", "GND", "97.6k 0.1%"),
    ):
        a.pin(ref, "1", p1)
        a.pin(ref, "2", p2)
        a.value_starts(ref, value)
    for pin, net in {
        "1": "/Power & Battery/AON_EFUSE_UV",
        "2": "/Power & Battery/AON_EFUSE_OV",
        "4": "/AON_FAULT_N",
        "5": "/Power & Battery/AON_OR_RAW",
        "6": "/EC_AON_IN",
        "7": "/Power & Battery/AON_EFUSE_DVDT",
        "8": "GND",
        "9": "/Power & Battery/AON_EFUSE_ILM",
    }.items():
        a.pin("U718", pin, net)
    a.prop_eq("U718", "MPN", "TPS259470ARPW")
    for ref, value, mpn, p1, p2 in (
        ("R795", "301k 0.1%", "RT0603BRD07301KL", "/Power & Battery/AON_OR_RAW", "/Power & Battery/AON_EFUSE_UV"),
        ("R796", "52.3k 0.1%", "RT0603BRD0752K3L", "/Power & Battery/AON_EFUSE_UV", "/Power & Battery/AON_EFUSE_OV"),
        ("R797", "20.0k 0.1%", "RT0603BRD0720KL", "/Power & Battery/AON_EFUSE_OV", "GND"),
    ):
        a.value_starts(ref, value)
        a.prop_eq(ref, "MPN", mpn)
        a.pin(ref, "1", p1)
        a.pin(ref, "2", p2)

    # Resetting the STM32 resets the source manager and removes all PD enables.
    source_manager = {
        "3": "/EC & MCU/NRST_NET",
        "4": "/PD1_PATH_EN",
        "5": "/PD2_PATH_EN",
        "6": "/PD3_PATH_EN",
        "22": "/I2C_SCL",
        "23": "/I2C_SDA",
        "24": "/MCU_3V3",
    }
    for pin, net in source_manager.items():
        a.pin("U44", pin, net)
    a.prop_eq("U44", "MPN", "TCA9539PWR")

    # CH224A autonomous 15 V request, low-margin fix, and unattached capacitance.
    cold_start = (
        "RAW_VBUS_4_TO_30V;CFG1_56K_REQUESTS_15V_WITHOUT_EC;"
        "15V_PDO_REQUIRED_FOR_SYSTEM_BOOT"
    )
    for index, uref in enumerate(("U41", "U42", "U43"), start=1):
        base = 120 + (index - 1) * 10
        prefix = f"/Power Inputs/PD{index}_"
        raw = f"/PD{index}_VBUS_RAW"
        a.prop_eq(uref, "AutonomousColdStartContract", cold_start)
        a.pin(uref, "2", prefix + "CH224_SCL")
        a.pin(uref, "3", prefix + "CH224_SDA")
        a.pin(uref, "9", prefix + "CFG1")
        a.value_starts(f"R{base + 2}", "56k")
        a.pin(f"R{base + 2}", "1", prefix + "CFG1")
        a.pin(f"R{base + 2}", "2", "GND")
        for offset, upstream, downstream in (
            (3, f"/PD{index}_I2C_SCL", prefix + "CH224_SCL"),
            (4, f"/PD{index}_I2C_SDA", prefix + "CH224_SDA"),
        ):
            ref = f"R{base + offset}"
            a.value_starts(ref, "100R")
            a.pin(ref, "1", upstream)
            a.pin(ref, "2", downstream)
        for ref, value, rail in (
            (f"C{base + 1}", "1u 50V X7R", raw),
            (f"C{800 + (index - 1) * 10}", "1u 50V", raw),
            (f"C{801 + (index - 1) * 10}", "100n 50V", raw),
        ):
            a.value_starts(ref, value)
            a.pin(ref, "1", rail)
            a.pin(ref, "2", "GND")

    # Downstream and internal Type-C input reservoirs stay behind default-off switches.
    for branch, tps, ilim, pre, output, bulk_in, bulk_out in (
        ("U20", "U21", "/Native USB-C I/O/USB1_ILIM", "/Native USB-C I/O/USB1_5V_PRE", "/Native USB-C I/O/USB1_VBUS", "C78", "C75"),
        ("U30", "U31", "/Native USB-C I/O/USB2_ILIM", "/Native USB-C I/O/USB2_5V_PRE", "/Native USB-C I/O/USB2_VBUS", "C98", "C95"),
        ("U64", "U63", "/Internal Services/TPAD_ILIM", "/Internal Services/TPAD_5V_PRE", "/Internal Services/TPAD_5V", "C284", "C283"),
    ):
        a.pin(branch, "5", ilim)
        a.pin(branch, "6", pre)
        for pin in ("2", "3", "4"):
            a.pin(tps, pin, pre)
        for pin in ("14", "15"):
            a.pin(tps, pin, output)
        a.value_starts(bulk_in, "150u")
        a.pin(bulk_in, "1", pre)
        a.pin(bulk_in, "2", "GND")
        a.value_starts(bulk_out, "10u")
        a.pin(bulk_out, "1", output)
        a.pin(bulk_out, "2", "GND")

    # Host-active gating and the corrected PCIe coupling values.
    for ref, source, output in (
        ("U54", "/SYS_5V", "/TCP0 External HDMI/HDMI_SOURCE_5V"),
        ("U55", "/SYS_3V3", "/TCP0 External HDMI/HDMI_HOST_3V3"),
    ):
        a.pin(ref, "1", source)
        a.pin(ref, "3", "/MU_HOST_ACTIVE")
        a.pin(ref, "7", output)
        a.prop_eq(ref, "MPN", "TPS22975NDSGR")
    for ref in ("C500", "C501", "C502", "C503"):
        a.value_starts(ref, "220n")
        a.prop_eq(ref, "MPN", "GRM155R71C224KA12D")

    # PE42820 controls stay inside their 4 V domain; powered-down radios are isolated.
    for ref, band in (("U240", "VHF"), ("U250", "UHF")):
        a.pin(ref, "12", "/Ham Radio/RADIO_4V0")
        a.pin(ref, "13", f"/Ham Radio/RADIO_{band}_RF_SEL_4V0")
    for ref, band in (("U242", "VHF"), ("U252", "UHF")):
        a.pin(ref, "4", "GND")
        a.pin(ref, "8", "/Ham Radio/RADIO_4V0")
        a.pin(ref, "1", f"/RADIO_{band}_UART_TX")
        a.pin(ref, "7", f"/Ham Radio/RADIO_{band}_UART_RXD")
        a.prop_eq(ref, "MPN", "SN74LVC3G34DCUR")
    a.prop_eq("U261", "MPN", "SN74LVC2G32DCUR")
    a.prop_eq("FL240", "MPN", "LFCN-160+")
    a.prop_eq("FL250", "MPN", "ULP-470+")

    # Exact endpoint identity and retention contracts.
    a.prop_eq("J40", "QualifiedModuleMPN", "AX210.NGWGIE.NV")
    a.prop_eq("J40", "QualifiedModuleContract", "M2_2230_KEY_E_PCIE_WIFI_USB_BLUETOOTH_NOT_CNVIO2")
    for ref in ("H3", "H4"):
        a.prop_eq(ref, "MPN", "M2XC4X2.5+C2.7X1.5")
        a.eq(
            a.footprint(ref),
            "ducktop2:SMT_Standoff_M2_H2.5_C4_Tail2.7x1.5",
            f"{ref} M.2 retention footprint",
        )

    # Exact fan electrical contract and fail-safe PWM behavior.
    a.prop_eq("J52", "EndpointMPN", "BFB04512HHA-CZ0T")
    a.prop_eq(
        "J52",
        "EndpointWireMap",
        "1=BLACK/GND;2=RED/+12V;3=WHITE/FG;4=YELLOW/PWM",
    )
    a.pin("F200", "1", "/MU_12V")
    a.pin("F200", "2", "/Internal Services/FAN_12V")
    a.value_starts("R206", "8.2k")
    a.value_starts("C209", "3.9n")
    a.value_starts("R208", "100k gate pull-down; fan defaults full speed")
    a.absent("R216")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("netlist", type=Path, help="KiCad XML netlist to inspect")
    args = parser.parse_args()
    audit = ClosureAudit(args.netlist)
    run_checks(audit)
    if audit.failures:
        print(f"Schematic closure audit: {audit.checks - len(audit.failures)} PASS, {len(audit.failures)} FAIL")
        for failure in audit.failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"Schematic closure audit: {audit.checks} PASS, 0 FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
