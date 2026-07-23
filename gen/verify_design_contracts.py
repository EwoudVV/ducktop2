#!/usr/bin/env python3
"""Ducktop2 high-risk design contract checks.

This complements KiCad ERC/DRC.  It asserts project-specific wiring decisions
that generic electrical rules cannot know, especially around battery entry,
USB-C power, OLED module pin order, and main-PCB footprint staging.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import sync_main_pcb_from_netlist as sync


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "ducktop2.kicad_pcb"
CURRENT_DRC = ROOT / "verification" / "contract_drc_current.json"


class CheckFailure(RuntimeError):
    pass


def fail(msg: str) -> None:
    raise CheckFailure(msg)


def expect(got: str | None, want: str, label: str) -> None:
    if got != want:
        fail(f"{label}: expected {want!r}, got {got!r}")


def expect_prefix(got: str | None, prefix: str, label: str) -> None:
    if got is None or not got.startswith(prefix):
        fail(f"{label}: expected prefix {prefix!r}, got {got!r}")


def expect_contains(got: str | None, needle: str, label: str) -> None:
    if got is None or needle not in got:
        fail(f"{label}: expected to contain {needle!r}, got {got!r}")


def comp(components, ref):
    item = components.get(ref)
    if item is None:
        fail(f"missing schematic component {ref}")
    return item


def net(components, ref, pin):
    return comp(components, ref).pin_nets.get(pin)


def prop(components, ref, name):
    return comp(components, ref).properties.get(name)


def local_net(sheet: str, name: str) -> str:
    return "/" + sheet.replace("/", "{slash}") + "/" + name


def expect_unconnected(components, ref: str, pin: str) -> None:
    got = net(components, ref, pin)
    pattern = rf"unconnected-\({re.escape(ref)}[A-Z]*-.*-Pad{re.escape(pin)}\)"
    if got is None or re.fullmatch(pattern, got) is None:
        fail(f"{ref} pin {pin}: expected an exact KiCad unconnected net, got {got!r}")


def expect_value_prefix(components, ref: str, prefix: str, label: str | None = None) -> None:
    expect_prefix(comp(components, ref).value, prefix, label or f"{ref} value")


def component_flags() -> tuple[set[str], set[str]]:
    root = ET.parse(sync.NETLIST).getroot()
    dnp: set[str] = set()
    exclude_bom: set[str] = set()
    for node in root.findall(".//comp"):
        ref = node.get("ref") or ""
        props = {p.get("name") for p in node.findall("property")}
        if "dnp" in props:
            dnp.add(ref)
        if "exclude_from_bom" in props:
            exclude_bom.add(ref)
    return dnp, exclude_bom


def component_pin_names() -> dict[tuple[str, str], str]:
    """Return the library-declared pin name for every instantiated pin."""
    root = ET.parse(sync.NETLIST).getroot()
    library_pins: dict[tuple[str, str], dict[str, str]] = {}
    for libpart in root.findall(".//libpart"):
        key = (libpart.get("lib") or "", libpart.get("part") or "")
        library_pins[key] = {
            pin.get("num") or "": pin.get("name") or ""
            for pin in libpart.findall("./pins/pin")
        }
    result: dict[tuple[str, str], str] = {}
    for node in root.findall(".//comp"):
        ref = node.get("ref") or ""
        source = node.find("libsource")
        if source is None:
            continue
        key = (source.get("lib") or "", source.get("part") or "")
        for pin, name in library_pins.get(key, {}).items():
            result[(ref, pin)] = name
    return result


def net_nodes() -> dict[str, set[tuple[str, str]]]:
    root = ET.parse(sync.NETLIST).getroot()
    return {
        node.get("name") or "": {
            (item.get("ref") or "", item.get("pin") or "")
            for item in node.findall("node")
        }
        for node in root.findall(".//net")
    }


def check_tps2553_semantics(components, pin_names) -> None:
    expected = {
        "1": ("IN", "/SYS_5V"),
        "2": ("GND", "GND"),
        "3": ("EN", "/MU_HOST_ACTIVE"),
        "4": ("~{FAULT}", "/INTERNAL_USB_VBUS_FAULT_N"),
        "5": ("ILIM", "/Mu Carrier/INTERNAL_USB_VBUS_ILIM"),
        "6": ("OUT", "/Mu Carrier/INTERNAL_USB_VBUS"),
    }
    for pin, (name, expected_net) in expected.items():
        expect(pin_names.get(("U770", pin)), name, f"U770 physical pin {pin} function")
        expect(net(components, "U770", pin), expected_net,
               f"U770 {name} physical pin {pin} net")


def self_test_tps2553_guard(components, pin_names) -> None:
    """Prove the semantic guard rejects the exact OUT/ILIM regression."""
    swapped = dict(components)
    bad = copy.copy(comp(components, "U770"))
    bad.pin_nets = dict(bad.pin_nets)
    bad.pin_nets["5"], bad.pin_nets["6"] = bad.pin_nets["6"], bad.pin_nets["5"]
    swapped["U770"] = bad
    try:
        check_tps2553_semantics(swapped, pin_names)
    except CheckFailure:
        return
    fail("TPS2553 negative fixture did not reject swapped OUT/ILIM nets")


def footprint_map():
    text = PCB.read_text(encoding="utf-8")
    return {fp.ref: fp for fp in sync.footprints(text)}, text


def at_tuple(block: str):
    m = re.search(r'\n\s*\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)', block)
    if not m:
        fail("footprint is missing top-level at")
    return float(m.group(1)), float(m.group(2)), float(m.group(3) or 0.0)


def source_footprint_pads(path: Path) -> list[tuple[str, float, float, float | None]]:
    """Return named/unnamed source-footprint pad coordinates and drill sizes."""
    text = path.read_text(encoding="utf-8")
    pads: list[tuple[str, float, float, float | None]] = []
    for _, _, block in sync.iter_blocks(text, "(pad "):
        at = re.search(r'\(at\s+([-0-9.]+)\s+([-0-9.]+)', block)
        if not at:
            fail(f"{path.name}: pad is missing an at coordinate")
        drill = re.search(r'\(drill\s+([-0-9.]+)', block)
        pads.append(
            (
                sync.pad_name(block),
                float(at.group(1)),
                float(at.group(2)),
                float(drill.group(1)) if drill else None,
            )
        )
    return pads


def rounded_pad_set(pads: list[tuple[str, float, float, float | None]]):
    rounded = [
        (name, round(x, 3), round(y, 3), None if drill is None else round(drill, 3))
        for name, x, y, drill in pads
    ]
    return sorted(
        rounded,
        key=lambda item: (item[0], item[1], item[2], -1.0 if item[3] is None else item[3]),
    )


def check_custom_footprint_sources() -> None:
    m2_standoff_path = (
        ROOT / "ducktop2.pretty" /
        "SMT_Standoff_M2_H2.5_C4_Tail2.7x1.5.kicad_mod"
    )
    m2_standoff_text = m2_standoff_path.read_text(encoding="utf-8")
    m2_standoff_pads = rounded_pad_set(source_footprint_pads(m2_standoff_path))
    expected_m2_standoff_pads = rounded_pad_set([
        ("1", 0.0, 0.0, 2.75),
        ("1", 0.0, 0.0, None),
    ])
    if m2_standoff_pads != expected_m2_standoff_pads:
        fail(
            "M.2 standoff source pads differ from the LattePanda V2 land "
            f"pattern: {m2_standoff_pads}"
        )
    expect_contains(m2_standoff_text, "M2XC4X2.5+C2.7X1.5",
                    "M.2 standoff official source designation")
    if "MDT420STD001" in m2_standoff_text:
        fail("M.2 standoff footprint must not cite incompatible MDT420STD001")

    aux_fet_path = ROOT / "ducktop2.pretty" / "CSD19537Q3_DQG.kicad_mod"
    aux_fet_text = aux_fet_path.read_text(encoding="utf-8")
    aux_fet_expected = [
        ("1", -1.44, -0.975, None),
        ("2", -1.44, -0.325, None),
        ("3", -1.44, 0.325, None),
        ("4", -1.44, 0.975, None),
        ("5", 0.385, 0.0, None),
    ]
    named_aux_fet_pads = [
        pad for pad in source_footprint_pads(aux_fet_path) if pad[0]
    ]
    if rounded_pad_set(named_aux_fet_pads) != rounded_pad_set(aux_fet_expected):
        fail("CSD19537Q3 source footprint pad centers changed")
    for required in (
        'TI CSD19537Q3, DQG VSON-CLIP 3.3x3.3 mm',
        '(xy 1.371 -0.72)',
        '(size 0.63 0.5)',
    ):
        if required not in aux_fet_text:
            fail(f"CSD19537Q3 source footprint is missing {required}")

    jack_path = ROOT / "ducktop2.pretty" / "JXD1-1022NL_MidMount.kicad_mod"
    jack_text = jack_path.read_text(encoding="utf-8")
    jack_expected: list[tuple[str, float, float, float | None]] = []
    for pin in range(1, 13):
        jack_expected.append(
            (str(pin), 1.27 * (pin - 1), 0.0 if pin % 2 else -1.27, 0.91)
        )
    jack_expected.extend(
        [
            ("13", 14.51, 15.70, 1.02),
            ("14", 14.51, 18.24, 1.02),
            ("15", -0.53, 15.70, 1.02),
            ("16", -0.53, 18.24, 1.02),
            ("SH", -1.80, 4.42, 2.03),
            ("SH", 15.78, 6.76, 1.40),
            ("SH", -1.80, 11.13, 1.40),
            ("SH", 15.78, 13.21, 2.03),
        ]
    )
    if rounded_pad_set(source_footprint_pads(jack_path)) != rounded_pad_set(jack_expected):
        fail("JXD1-1022NL source footprint pin/stake coordinates or drills changed")
    for required in (
        '(fp_rect (start -1.8 -3.25) (end 15.78 22.81)',
        '(fp_line (start -1.8 20.78) (end 15.78 20.78)',
        '(pad "SH" thru_hole oval (at 15.78 13.21) (size 4 2.5) (drill 2.03)',
        '(attr through_hole)',
    ):
        if required not in jack_text:
            fail(f"JXD1-1022NL source footprint is missing {required}")

    mic_path = ROOT / "ducktop2.pretty" / "Infineon_IM68A130V01.kicad_mod"
    mic_text = mic_path.read_text(encoding="utf-8")
    named_mic_pads = [pad for pad in source_footprint_pads(mic_path) if pad[0]]
    mic_expected = [
        ("1", -1.09, 0.775, None),
        ("2", -1.09, 0.0, None),
        ("3", -1.09, -0.775, None),
        ("4", 0.575, -0.64, None),
    ]
    if rounded_pad_set(named_mic_pads) != rounded_pad_set(mic_expected):
        fail("IM68A130 source footprint electrical-pad coordinates changed")
    for required in (
        '(fp_rect (start -1.675 -1.25) (end 1.675 1.25)',
        '(pad "" np_thru_hole circle (at 0.575 0) (size 0.6 0.6) (drill 0.6)',
        '(gr_circle (center 0 0.64) (end 0.64 0.64) (width 0.37)',
        '(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed)',
    ):
        if required not in mic_text:
            fail(f"IM68A130 source footprint is missing {required}")


def check_active_custom_footprint_pin_sets(components) -> None:
    """Require every active project-local symbol pin to exist in its footprint."""
    checked: set[str] = set()
    for component in components.values():
        footprint = component.footprint or ""
        if not footprint.startswith("ducktop2:"):
            continue
        name = footprint.split(":", 1)[1]
        path = ROOT / "ducktop2.pretty" / f"{name}.kicad_mod"
        if not path.exists():
            fail(f"active custom footprint source is missing: {path.name}")
        pad_names = {pad[0] for pad in source_footprint_pads(path) if pad[0]}
        missing = sorted(pin for pin in component.pin_nets if pin and pin not in pad_names)
        if missing:
            fail(f"{component.ref} symbol pins absent from {path.name}: {missing}")
        checked.add(name)
    if len(checked) < 10:
        fail(f"unexpectedly few active custom footprints checked: {len(checked)}")


def check_oled(components, fps=None):
    expect(comp(components, "J41").footprint, "ducktop2:SSD1306_0.96in_Module_4Pin", "J41 footprint")
    expect(comp(components, "J45").footprint, "ducktop2:SSD1306_0.96in_Module_4Pin", "J45 footprint")
    expect(comp(components, "U45").footprint, "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", "U45 footprint")
    for ref, sda, scl in [
        ("J41", "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_A_SDA", "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_A_SCL"),
        ("J45", "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_B_SDA", "/Wi-Fi{slash}Bluetooth & OLEDs/OLED_B_SCL"),
    ]:
        expect(net(components, ref, "1"), "GND", f"{ref} pin 1")
        expect(net(components, ref, "2"), "/MCU_3V3", f"{ref} pin 2")
        expect(net(components, ref, "3"), scl, f"{ref} pin 3")
        expect(net(components, ref, "4"), sda, f"{ref} pin 4")
        expect(prop(components, ref, "ProcurementClass"), "Owner-supplied measured module",
               f"{ref} controlled owner-supplied identity")
        if fps is not None:
            if ref not in fps:
                fail(f"{ref} missing from PCB")
            if fps[ref].footprint != "ducktop2:SSD1306_0.96in_Module_4Pin":
                fail(f"{ref} PCB footprint is not the exact OLED module: {fps[ref].footprint}")

    for pin in ("1", "2", "12", "21"):
        expect(net(components, "U45", pin), "GND", f"U45 pin {pin}")
    expect(net(components, "U45", "3"), "/SERVICE_MUX_RESET_N", "U45 service-mux reset")
    expect(net(components, "U45", "22"), "/I2C_SCL", "U45 upstream SCL")
    expect(net(components, "U45", "23"), "/I2C_SDA", "U45 upstream SDA")
    expect(net(components, "U45", "24"), "/MCU_3V3", "U45 VCC")
    for idx, (sda_pin, scl_pin) in enumerate((("8", "9"), ("10", "11")), start=1):
        expect(net(components, "U45", sda_pin), f"/PD{idx}_I2C_SDA", f"U45 PD{idx} downstream SDA")
        expect(net(components, "U45", scl_pin), f"/PD{idx}_I2C_SCL", f"U45 PD{idx} downstream SCL")
    for pin in ("13", "14", "15", "16", "17", "18", "19", "20"):
        expect_unconnected(components, "U45", pin)
    expect(net(components, "C185", "1"), "/MCU_3V3", "C185 pin 1")
    expect(net(components, "C185", "2"), "GND", "C185 pin 2")


def check_battery_and_charger(components):
    for pin in ("1", "2"):
        expect(net(components, "J2", pin), "/Power & Battery/PACK_POS_RAW",
               f"J2 paired pack-positive pin {pin}")
    for pin in ("3", "4"):
        expect(net(components, "J2", pin), "/Power & Battery/PACK_NEG_RAW",
               f"J2 paired raw pack-negative pin {pin}")
    expect(net(components, "J2", "5"), "/Power & Battery/CELL1_TAP", "J2 cell-1 tap")
    expect(net(components, "J2", "6"), "/Power & Battery/CELL2_TAP", "J2 cell-2 tap")

    # Autonomous per-cell primary protection.  These checks deliberately cover
    # physical pin numbers, sense direction, FET orientation, and every strap.
    for pin, want in {
        "1": "/Power & Battery/BMS_VDD", "2": "/Power & Battery/BMS_AVDD",
        "3": "/Power & Battery/BMS_VC3_TOP", "4": "/Power & Battery/BMS_VC3_TOP",
        "5": "/Power & Battery/BMS_VC3_TOP", "6": "/Power & Battery/BMS_VC2",
        "7": "/Power & Battery/BMS_VC1", "8": "/Power & Battery/BMS_VC0",
        "9": "/Power & Battery/PACK_NEG_RAW", "10": "/Power & Battery/BMS_SRP",
        "11": "/Power & Battery/BMS_SRN", "12": "/Power & Battery/BMS_DSG_DRV",
        "13": "/Power & Battery/BMS_CHG_DRV", "14": "/Power & Battery/BMS_LD",
        "16": "/Power & Battery/PACK_NEG_RAW", "17": "/Power & Battery/BMS_OCDP",
        "18": "/Power & Battery/BMS_TS_UNUSED", "20": "/Power & Battery/PACK_NEG_RAW",
        "22": "/Power & Battery/BMS_PRES", "23": "/Power & Battery/PACK_NEG_RAW",
        "24": "/Power & Battery/PACK_NEG_RAW",
    }.items():
        expect(net(components, "U719", pin), want, f"BQ7791500 pin {pin}")
    for pin in ("15", "19", "21"):
        expect_unconnected(components, "U719", pin)
    expect(comp(components, "U719").footprint,
           "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", "BQ7791500 exact footprint")
    expect(prop(components, "U719", "MPN"), "BQ7791500PWR", "BQ7791500 exact MPN")

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
        expect_value_prefix(components, ref, value, f"{ref} BQ7791500 support value")
        expect(net(components, ref, "1"), p1, f"{ref} BQ7791500 pin 1")
        expect(net(components, ref, "2"), p2, f"{ref} BQ7791500 pin 2")
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
        expect_value_prefix(components, ref, value, f"{ref} BQ7791500 filter value")
        expect(net(components, ref, "1"), p1, f"{ref} BQ7791500 pin 1")
        expect(net(components, ref, "2"), p2, f"{ref} BQ7791500 pin 2")
    expect_value_prefix(components, "RS11", "8mOhm 1% 2W", "BQ7791500 current shunt")
    expect(net(components, "RS11", "1"), "/Power & Battery/PACK_NEG_RAW", "BQ7791500 SRP shunt side")
    expect(net(components, "RS11", "2"), "/Power & Battery/BMS_SENSE_N", "BQ7791500 SRN shunt side")
    expect(prop(components, "RS11", "MPN"), "WSLP25128L000FEA", "BQ7791500 exact shunt")
    for ref, source, gate in (
        ("Q703", "/Power & Battery/BMS_SENSE_N", "/Power & Battery/BMS_DSG_GATE"),
        ("Q704", "/Power & Battery/FG_VSS", "/Power & Battery/BMS_CHG_GATE"),
    ):
        for pin in ("1", "2", "3"):
            expect(net(components, ref, pin), source, f"{ref} source pin {pin}")
        expect(net(components, ref, "4"), gate, f"{ref} gate")
        expect(net(components, ref, "5"), "/Power & Battery/BMS_FET_COMMON", f"{ref} common drain")
        expect(prop(components, ref, "MPN"), "CSD18540Q5B", f"{ref} exact MOSFET")

    expect(net(components, "F1", "1"), "/Power & Battery/PACK_POS_RAW", "F1 input")
    expect(net(components, "F1", "2"), "/Power & Battery/BAT_PROT_VIN", "F1 protected-entry output")
    expect(net(components, "RS1", "1"), "/Power & Battery/FG_VSS", "RS1 pack-side Kelvin node")
    expect(net(components, "RS1", "2"), "GND", "RS1 system side")
    for pin, want in {
        "1": "/Power & Battery/BAT_PROT_VIN", "2": "/Power & Battery/BAT_PROT_UV",
        "3": "/Power & Battery/BAT_PROT_OV", "4": "GND", "5": "GND",
        "6": "/Power & Battery/BAT_PROT_SHDN", "7": "/PACK_FAULT_N",
        "8": "/Power & Battery/PACK_POS_FUSED",
        "9": "/Power & Battery/BAT_PROT_SENSE", "10": "/Power & Battery/BAT_PROT_GATE",
    }.items():
        expect(net(components, "U11", pin), want, f"LTC4368-1 pin {pin}")
    for ref, drain in (("Q11", "/Power & Battery/BAT_PROT_VIN"),
                       ("Q12", "/Power & Battery/BAT_PROT_SENSE")):
        for pin in ("1", "2", "3"):
            expect(net(components, ref, pin), "/Power & Battery/BAT_PROT_FET_COMMON", f"{ref} common source {pin}")
        expect(net(components, ref, "4"), "/Power & Battery/BAT_PROT_GATE", f"{ref} gate")
        expect(net(components, ref, "5"), drain, f"{ref} drain")
    expect(net(components, "RS10", "1"), "/Power & Battery/BAT_PROT_SENSE", "LTC4368 shunt sense side")
    expect(net(components, "RS10", "2"), "/Power & Battery/PACK_POS_FUSED", "LTC4368 shunt output side")
    expect_value_prefix(components, "RS10", "11mOhm", "LTC4368 bounded-current shunt")
    expect_value_prefix(components, "C725", "10u 25V X7R", "LTC4368 VOUT capacitor")
    expect(net(components, "C725", "1"), "/Power & Battery/PACK_POS_FUSED",
           "LTC4368 VOUT capacitor protected rail")
    expect(net(components, "C725", "2"), "GND", "LTC4368 VOUT capacitor return")
    expect(prop(components, "C725", "MPN"), "GRM21BZ71E106KE15L",
           "LTC4368 VOUT capacitor exact MPN")
    expect_value_prefix(components, "R700", "3.09M 1%", "LTC4368 pack-window top")
    expect_value_prefix(components, "R701", "73.2k 1%", "LTC4368 pack-window middle")
    expect_value_prefix(components, "R702", "121k 1%", "LTC4368 pack-window bottom")
    expect(net(components, "R703", "1"), "/Power & Battery/BAT_PROT_GATE", "LTC4368 CGATE resistor input")
    expect(net(components, "R703", "2"), "/Power & Battery/BAT_PROT_CGATE", "LTC4368 CGATE resistor output")
    expect(net(components, "C700", "1"), "/Power & Battery/BAT_PROT_CGATE", "LTC4368 CGATE capacitor")
    expect(net(components, "C700", "2"), "GND", "LTC4368 CGATE capacitor return")
    expect(net(components, "C724", "1"), "/Power & Battery/BAT_PROT_GATE", "LTC4368 hot-swap capacitor gate")
    expect(net(components, "C724", "2"), "/Power & Battery/BAT_PROT_FET_COMMON", "LTC4368 hot-swap capacitor source")
    expect(net(components, "R707", "1"), "/Power & Battery/BAT_PROT_VIN", "pack protector SHDN pull-up source")
    expect(net(components, "R707", "2"), "/Power & Battery/BAT_PROT_SHDN", "pack protector SHDN pull-up node")
    expect_value_prefix(components, "R707", "100k", "pack protector SHDN pull-up")
    expect(net(components, "R708", "1"), "/MCU_3V3", "pack protector FAULT pull-up rail")
    expect(net(components, "R708", "2"), "/PACK_FAULT_N", "pack protector FAULT output")
    expect_value_prefix(components, "R708", "10k", "pack protector FAULT pull-up")
    for pin, want in {
        "1": "/PACK_RETRY_PULSE", "2": "GND", "3": "/Power & Battery/BAT_PROT_SHDN",
    }.items():
        expect(net(components, "Q701", pin), want, f"pack protector retry transistor pin {pin}")
    expect_value_prefix(components, "R709", "100k", "pack retry default-off pull-down")
    expect(net(components, "R709", "1"), "/PACK_RETRY_PULSE", "pack retry pull-down signal")
    expect(net(components, "R709", "2"), "GND", "pack retry pull-down return")
    for obsolete in ("NTC2", "NTC4"):
        if obsolete in components:
            fail(f"obsolete motherboard battery thermistor {obsolete} remains")

    expect(prop(components, "LED1", "Manufacturer"), "Kingbright", "charger LED manufacturer")
    expect(prop(components, "LED1", "MPN"), "APT1608SGC", "charger LED exact MPN")

    for ref, want in {
        "TP1": "GND",
        "TP2": "/Power & Battery/PACK_POS_FUSED",
        "TP3": "/VSYS",
        "TP4": "/EC_AON_IN",
        "TP7": "/MCU_3V3",
        "TP9": "/CHG_INT_N",
        "TP10": "/PACK_FAULT_N",
        "TP11": "/AON_FAULT_N",
    }.items():
        expect(comp(components, ref).footprint,
               "TestPoint:TestPoint_Pad_D1.0mm", f"{ref} fixture footprint")
        expect(net(components, ref, "1"), want, f"{ref} fixture net")
        expect(prop(components, ref, "ProcurementClass"),
               "PCB copper test feature", f"{ref} procurement class")

    for pin in ("2", "3", "8", "9"):
        expect(net(components, "U2", pin), "/Power & Battery/VBUS_COMBINED", f"BQ25798 VBUS/VAC pin {pin}")
    for pin in ("10", "11", "27"):
        expect(net(components, "U2", pin), "GND", f"BQ25798 ground pin {pin}")
    expect(net(components, "U2", "16"), "/Power & Battery/CHG_TS_FIXED",
           "BQ25798 fixed non-sensing TS input")
    expect_value_prefix(components, "R16", "5.24k 1%", "BQ25798 fixed TS top")
    expect(net(components, "R16", "1"), "/Power & Battery/REGN", "BQ25798 TS divider source")
    expect(net(components, "R16", "2"), "/Power & Battery/CHG_TS_FIXED", "BQ25798 TS divider node")
    expect_value_prefix(components, "R705", "7.50k 1%", "BQ25798 fixed TS bottom")
    expect(net(components, "R705", "1"), "/Power & Battery/CHG_TS_FIXED", "BQ25798 TS divider bottom")
    expect(net(components, "R705", "2"), "GND", "BQ25798 TS divider return")
    expect(net(components, "U2", "12"), "/Power & Battery/PMIC_QON_PIN",
           "BQ25798 QON local charger-domain node")
    for pin, want in {
        "1": "/PMIC_QON_ASSERT", "2": "GND", "3": "/Power & Battery/PMIC_QON_PIN",
    }.items():
        expect(net(components, "Q702", pin), want, f"QON open-drain transistor pin {pin}")
    expect(prop(components, "Q702", "MPN"), "BSS138LT1G", "QON transistor exact MPN")
    expect_value_prefix(components, "R13", "100k QON-control gate pulldown",
                        "QON gate default-off resistor")
    expect(net(components, "R13", "1"), "/PMIC_QON_ASSERT", "QON gate control")
    expect(net(components, "R13", "2"), "GND", "QON gate default-off return")
    for ref, anode in (("D715", "/Power & Battery/PMIC_QON_PIN"),
                       ("D716", "/MU_PWRBTN_N")):
        expect(net(components, ref, "1"), "/CASE_PWRBTN_N", f"{ref} case-button cathode")
        expect(net(components, ref, "2"), anode, f"{ref} isolated target anode")
        expect(prop(components, ref, "MPN"), "BAT54WS-7-F", f"{ref} exact Schottky")
    nodes = net_nodes()
    expect(nodes.get("/Power & Battery/PMIC_QON_PIN"),
           {("U2", "12"), ("Q702", "3"), ("D715", "2")},
           "QON charger-domain node membership")
    expect(nodes.get("/PMIC_QON_ASSERT"),
           {("U4", "26"), ("Q702", "1"), ("R13", "1")},
           "QON active-high control node membership")
    expect(nodes.get("/CASE_PWRBTN_N"),
           {("J16", "2"), ("D715", "1"), ("D716", "1")},
           "case power-button isolated fanout membership")
    expect(net(components, "U2", "18"), "/Power & Battery/BATP_SENSE", "BQ25798 BATP Kelvin sense")
    for pin in ("22", "23"):
        expect(net(components, "U2", pin), "/Power & Battery/BAT_CHARGER", f"BQ25798 BAT pin {pin}")
    expect(net(components, "U2", "24"), "/Power & Battery/SDRV_GATE", "BQ25798 SDRV")
    if "C184" in components:
        fail("obsolete SDRV-to-ground capacitor C184 remains; the released design uses Q25 ship FET")
    for pin in ("1", "2", "3"):
        expect(net(components, "Q25", pin), "/Power & Battery/BAT_CHARGER", f"ship FET source pin {pin}")
    expect(net(components, "Q25", "4"), "/Power & Battery/SDRV_GATE", "ship FET gate")
    expect(net(components, "Q25", "5"), "/Power & Battery/PACK_POS_FUSED", "ship FET pack-side drain")
    expect(prop(components, "Q25", "MPN"), "CSD17575Q3", "ship FET exact MPN")
    expect(comp(components, "Q25").footprint, "ducktop2:CSD19537Q3_DQG", "ship FET TI DQG footprint")
    expect(net(components, "U2", "25"), "/VSYS", "BQ25798 SYS")
    expect(net(components, "U2", "13"), "/Power & Battery/CHG_CE_HW_N", "BQ25798 fail-off CE")
    expect_unconnected(components, "U2", "6")
    expect_unconnected(components, "U2", "7")
    expect_value_prefix(components, "R18", "10.5k", "BQ25798 PROG default")
    expect_value_prefix(components, "R14", "10k", "BQ25798 CE hardware-disable pull-up")
    expect(net(components, "R14", "1"), "/Power & Battery/REGN", "BQ25798 CE pull-up source")
    expect(net(components, "R14", "2"), "/Power & Battery/CHG_CE_HW_N", "BQ25798 CE pull-up node")
    for pin, want in {
        "1": "/CHG_ENABLE", "2": "GND", "3": "/Power & Battery/CHG_CE_HW_N",
    }.items():
        expect(net(components, "Q700", pin), want, f"charger enable transistor pin {pin}")
    expect_value_prefix(components, "R719", "100k", "charger-enable default-off pull-down")
    expect(net(components, "R719", "1"), "/CHG_ENABLE", "charger-enable pull-down signal")
    expect(net(components, "R719", "2"), "GND", "charger-enable pull-down return")
    expect(net(components, "R18", "1"), "/Power & Battery/PROG_SET", "BQ25798 PROG resistor top")
    expect(net(components, "R18", "2"), "GND", "BQ25798 PROG resistor bottom")
    expect(net(components, "R17", "1"), "/Power & Battery/REGN", "BQ25798 ILIM top source")
    expect_value_prefix(components, "R17", "47.0k 0.1%", "BQ25798 3A ILIM top")
    expect_value_prefix(components, "R190", "100k 0.1%", "BQ25798 3A ILIM bottom")
    expect(net(components, "R190", "2"), "GND", "BQ25798 ILIM bottom")
    expect(net(components, "L1", "1"), "/Power & Battery/SW1", "BQ25798 inductor side A")
    expect(net(components, "L1", "2"), "/Power & Battery/SW2", "BQ25798 inductor side B")
    expect_value_prefix(components, "L1", "1.0uH 20% 28A Isat", "BQ25798 released inductor value")
    expect(comp(components, "L1").footprint, "Inductor_SMD:L_Coilcraft_XAL7030-102",
           "BQ25798 exact inductor footprint")
    expect(prop(components, "L1", "Manufacturer"), "Coilcraft", "BQ25798 inductor manufacturer")
    expect(prop(components, "L1", "MPN"), "XAL7030-102MEC", "BQ25798 inductor MPN")

    # BQ25798 Rev C Figure 8-1 support network. ERC cannot establish that the
    # required local energy-storage and bootstrap population is complete.
    for ref, value, net_a, net_b in (
        ("C7", "47n 25V X7R", "/Power & Battery/BTST1_NODE", "/Power & Battery/SW1"),
        ("C8", "47n 25V X7R", "/Power & Battery/BTST2_NODE", "/Power & Battery/SW2"),
        ("C9", "4.7u 10V X7R", "/Power & Battery/REGN", "GND"),
        ("C10", "100n 50V X7R", "/Power & Battery/PMID", "GND"),
        ("C11", "100n 50V X7R", "/VSYS", "GND"),
        ("C12", "100n 50V X7R", "/Power & Battery/VBUS_COMBINED", "GND"),
        ("C701", "10u 25V X7R", "/Power & Battery/VBUS_COMBINED", "GND"),
        ("C702", "10u 25V X7R", "/Power & Battery/VBUS_COMBINED", "GND"),
        ("C703", "10u 25V X7R", "/Power & Battery/PMID", "GND"),
        ("C704", "10u 25V X7R", "/Power & Battery/PMID", "GND"),
        ("C705", "10u 25V X7R", "/Power & Battery/PMID", "GND"),
        ("C706", "10u 25V X7R", "/VSYS", "GND"),
        ("C707", "10u 25V X7R", "/VSYS", "GND"),
        ("C708", "10u 25V X7R", "/VSYS", "GND"),
        ("C709", "10u 25V X7R", "/VSYS", "GND"),
        ("C710", "10u 25V X7R", "/VSYS", "GND"),
        ("C711", "100n 50V X7R", "/Power & Battery/BAT_CHARGER", "GND"),
        ("C712", "10u 25V X7R", "/Power & Battery/BAT_CHARGER", "GND"),
        ("C713", "10u 25V X7R", "/Power & Battery/BAT_CHARGER", "GND"),
        ("C714", "2.2u 25V X7R", "/Power & Battery/VBUS_DAMP", "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} BQ25798 support value")
        expect(net(components, ref, "1"), net_a, f"{ref} BQ25798 support pin 1")
        expect(net(components, ref, "2"), net_b, f"{ref} BQ25798 support pin 2")
    expect(net(components, "J190", "1"), "/Power & Battery/AUX_DC_RAW", "AUX/SOLAR terminal positive")
    expect(net(components, "F190", "1"), "/Power & Battery/AUX_DC_RAW", "AUX fuse input")
    expect(net(components, "F190", "2"), "/Power & Battery/AUX_DC_FUSED", "AUX fuse output")
    expect(net(components, "D190", "1"), "/Power & Battery/AUX_DC_FUSED", "AUX TVS protected node")
    expect(net(components, "D190", "2"), "GND", "AUX TVS ground")
    for obsolete in ("D5", "D6", "D7", "D191"):
        if obsolete in components:
            fail(f"obsolete passive source-ORing diode {obsolete} is still present")
    for pin in ("1", "2"):
        expect(net(components, "U12", pin), "/Power & Battery/AUX_DC_FUSED", f"TPS26630 input pin {pin}")
    expect(net(components, "U12", "5"), "/Power & Battery/AUX_EFUSE_IN_SYS", "TPS26630 IN_SYS")
    for pin in ("17", "18"):
        expect(net(components, "U12", pin), "/Power & Battery/AUX_DC_PROTECTED", f"TPS26630 output pin {pin}")
    expect_value_prefix(components, "R711", "300k", "TPS26630 UV/OV top")
    expect_value_prefix(components, "R712", "63.2k", "TPS26630 UV/OV middle")
    expect_value_prefix(components, "R713", "20.0k", "TPS26630 UV/OV bottom")
    expect(net(components, "U12", "14"), "/AUX_FAULT_N", "TPS26630 AUX fault output")
    expect(net(components, "U12", "15"), "/Power & Battery/AUX_PGTH", "TPS26630 PGOOD threshold input")
    expect(net(components, "U12", "16"), "/AUX_PGOOD", "TPS26630 AUX power-good output")
    for ref, value, pin1, pin2 in (
        ("R739", "332k 0.1%", "/Power & Battery/AUX_DC_PROTECTED", "/Power & Battery/AUX_PGTH"),
        ("R740", "97.6k 0.1%", "/Power & Battery/AUX_PGTH", "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} AUX PGOOD threshold divider")
        expect(net(components, ref, "1"), pin1, f"{ref} AUX PGOOD divider pin 1")
        expect(net(components, ref, "2"), pin2, f"{ref} AUX PGOOD divider pin 2")
    for ref, signal in (("R715", "/AUX_FAULT_N"), ("R716", "/AUX_PGOOD")):
        expect_value_prefix(components, ref, "10k", f"{ref} AUX status pull-up")
        expect(net(components, ref, "1"), "/MCU_3V3", f"{ref} pull-up rail")
        expect(net(components, ref, "2"), signal, f"{ref} status signal")

    # U15 qualifies and prioritizes the already-selected 15 V USB rail over protected AUX.
    expect_contains(comp(components, "U15").value, "LTC4418IUF", "industrial dual-input selector")
    expect(comp(components, "U15").footprint,
           "ducktop2:ADI_UF20_QFN20_4x4_P0.5_EP2.45", "U15 exact ADI UF20 footprint")
    for pin, want in {
        "1": "/Power & Battery/MAIN_SEL_TMR",
        "2": "/Power & Battery/USB_MAIN_UV", "3": "/Power & Battery/USB_MAIN_OV",
        "4": "/Power & Battery/AUX_MAIN_UV", "5": "/Power & Battery/AUX_MAIN_OV",
        "7": "GND", "8": "/Power & Battery/MAIN_SEL_INTVCC",
        "11": "/Power & Battery/AUX_MAIN_GATE", "12": "/Power & Battery/AUX_MAIN_FET_COMMON",
        "13": "/Power & Battery/USB_MAIN_GATE", "14": "/Power & Battery/USB_MAIN_FET_COMMON",
        "15": "/Power & Battery/VBUS_COMBINED", "16": "/Power & Battery/AUX_DC_PROTECTED",
        "17": "/USB_PD_SELECTED", "18": "/Power & Battery/MAIN_SEL_INTVCC",
        "19": "/Power & Battery/MAIN_SEL_INTVCC", "20": "GND", "21": "GND",
    }.items():
        expect(net(components, "U15", pin), want, f"LTC4418 U15 pin {pin}")
    expect_unconnected(components, "U15", "6")
    for pin, signal in (("9", "/MAIN_USB_VALID_N"), ("10", "/MAIN_AUX_VALID_N")):
        expect(net(components, "U15", pin), signal, f"LTC4418 status pin {pin}")
    for ref, signal in (("R717", "/MAIN_USB_VALID_N"), ("R718", "/MAIN_AUX_VALID_N")):
        expect_value_prefix(components, ref, "10k", f"{ref} main-selector status pull-up")
        expect(net(components, ref, "1"), "/MCU_3V3", f"{ref} pull-up rail")
        expect(net(components, ref, "2"), signal, f"{ref} status signal")

    for ref, gate, common, drain in (
        ("Q21", "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "/USB_PD_SELECTED"),
        ("Q22", "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "/Power & Battery/VBUS_COMBINED"),
        ("Q23", "AUX_MAIN_GATE", "AUX_MAIN_FET_COMMON", "/Power & Battery/AUX_DC_PROTECTED"),
        ("Q24", "AUX_MAIN_GATE", "AUX_MAIN_FET_COMMON", "/Power & Battery/VBUS_COMBINED"),
    ):
        expect_contains(comp(components, ref).value, "SiSS4409DN", f"{ref} selector PMOS")
        expect(comp(components, ref).footprint, "Package_SO:Vishay_PowerPAK_1212-8_Single", f"{ref} footprint")
        expect(net(components, ref, "1"), local_net("Power & Battery", gate), f"{ref} gate")
        for pin in ("2", "3", "4"):
            expect(net(components, ref, pin), local_net("Power & Battery", common), f"{ref} source {pin}")
        expect(net(components, ref, "5"), drain, f"{ref} drain")

    for ref, value, net_a, net_b in (
        ("R730", "1.00M 0.1%", "/USB_PD_SELECTED", "/Power & Battery/USB_MAIN_UV"),
        ("R731", "19.6k 0.1%", "/Power & Battery/USB_MAIN_UV", "/Power & Battery/USB_MAIN_OV"),
        ("R732", "63.4k 0.1%", "/Power & Battery/USB_MAIN_OV", "GND"),
        ("R733", "383k 0.1%", "/Power & Battery/AUX_DC_PROTECTED", "/Power & Battery/AUX_MAIN_UV"),
        ("R734", "63.4k 0.1%", "/Power & Battery/AUX_MAIN_UV", "/Power & Battery/AUX_MAIN_OV"),
        ("R735", "20.0k 0.1%", "/Power & Battery/AUX_MAIN_OV", "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} selector threshold value")
        expect(net(components, ref, "1"), net_a, f"{ref} pin 1")
        expect(net(components, ref, "2"), net_b, f"{ref} pin 2")
    expect_value_prefix(components, "C741", "15n", "LTC4418 validation timer")
    expect(net(components, "C740", "1"), "/Power & Battery/MAIN_SEL_INTVCC", "LTC4418 INTVCC bypass")
    expect(net(components, "C741", "1"), "/Power & Battery/MAIN_SEL_TMR", "LTC4418 timer capacitor")
    for ref in ("C740", "C741", "C742", "C743", "C744", "C745"):
        expect(net(components, ref, "2"), "GND", f"{ref} selector capacitor return")
    expect_value_prefix(components, "C746", "100u 35V hybrid", "LTC4418 output hold-up")
    expect(net(components, "C746", "1"), "/Power & Battery/VBUS_COMBINED", "LTC4418 output hold-up rail")
    expect(net(components, "C746", "2"), "GND", "LTC4418 output hold-up return")

    for ref, source in (
        ("D710", "/Power & Battery/BAT_CHARGER"),
        ("D711", "/Power & Battery/AUX_DC_PROTECTED"),
        ("D712", "/PD1_VBUS_RAW"),
        ("D713", "/PD2_VBUS_RAW"),
    ):
        expect(net(components, ref, "1"), "/Power & Battery/AON_OR_RAW", f"{ref} always-on OR cathode")
        expect(net(components, ref, "2"), source, f"{ref} always-on OR source")
        expect_contains(comp(components, ref).value, "B340A", f"{ref} always-on Schottky")
    for pin, want in {
        "1": "/Power & Battery/AON_EFUSE_UV",
        "2": "/Power & Battery/AON_EFUSE_OV",
        "4": "/AON_FAULT_N",
        "5": "/Power & Battery/AON_OR_RAW",
        "6": "/EC_AON_IN",
        "7": "/Power & Battery/AON_EFUSE_DVDT",
        "8": "GND",
        "9": "/Power & Battery/AON_EFUSE_ILM",
    }.items():
        expect(net(components, "U718", pin), want, f"aggregate AON eFuse pin {pin}")
    expect_unconnected(components, "U718", "3")
    expect_unconnected(components, "U718", "10")
    expect(prop(components, "U718", "MPN"), "TPS259470ARPW", "aggregate AON eFuse exact MPN")
    expect(comp(components, "U718").footprint,
           "ducktop2:Texas_RPW0010A_VQFN-HR-10_2x2mm", "aggregate AON eFuse exact footprint")
    for ref, value, net_a, net_b in (
        ("R795", "301k 0.1%", "/Power & Battery/AON_OR_RAW", "/Power & Battery/AON_EFUSE_UV"),
        ("R796", "52.3k 0.1%", "/Power & Battery/AON_EFUSE_UV", "/Power & Battery/AON_EFUSE_OV"),
        ("R797", "20.0k 0.1%", "/Power & Battery/AON_EFUSE_OV", "GND"),
        ("R798", "2.21k 0.1%", "/Power & Battery/AON_EFUSE_ILM", "GND"),
        ("C795", "1u 25V", "/Power & Battery/AON_OR_RAW", "GND"),
        ("C796", "100n 50V", "/Power & Battery/AON_OR_RAW", "GND"),
        ("C797", "10u 25V", "/EC_AON_IN", "GND"),
        ("C798", "100n 50V", "/EC_AON_IN", "GND"),
        ("C799", "3.3n", "/Power & Battery/AON_EFUSE_DVDT", "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} aggregate AON support value")
        expect(net(components, ref, "1"), net_a, f"{ref} aggregate AON support pin 1")
        expect(net(components, ref, "2"), net_b, f"{ref} aggregate AON support pin 2")
    expect(prop(components, "R795", "MPN"), "RT0603BRD07301KL", "AON ladder R795 exact MPN")
    expect(prop(components, "R796", "MPN"), "RT0603BRD0752K3L", "AON ladder R796 exact MPN")

    expect(net(components, "U10", "1"), "/BQ_ALERT", "BQ34Z100 ALERT output")
    expect(net(components, "U10", "4"), "/Power & Battery/FG_BAT_SENSE", "BQ34Z100 BAT sense")
    expect(net(components, "U10", "6"), "/MCU_3V3", "BQ34Z100 REGIN/VCC")
    expect(net(components, "U10", "8"), "/Power & Battery/FG_VSS", "BQ34Z100 battery-side VSS")
    expect(net(components, "U10", "9"), "/Power & Battery/FG_SRP", "BQ34Z100 SRP")
    expect(net(components, "U10", "10"), "/Power & Battery/FG_SRN", "BQ34Z100 SRN")
    expect(net(components, "U10", "11"), "/Power & Battery/FG_TS", "BQ34Z100 unused external TS pin")
    expect(net(components, "U10", "13"), "/I2C_SCL", "BQ34Z100 SCL")
    expect(net(components, "U10", "14"), "/I2C_SDA", "BQ34Z100 SDA")
    expect_value_prefix(components, "R855", "10k", "BQ34Z100 unused TS pulldown")
    expect(net(components, "R855", "1"), "/Power & Battery/FG_TS", "BQ34Z100 TS pulldown input")
    expect(net(components, "R855", "2"), "/Power & Battery/FG_VSS", "BQ34Z100 TS pulldown return")
    expect_value_prefix(components, "R180", "220k", "fuel gauge divider top")
    expect_value_prefix(components, "R181", "16.5k", "fuel gauge divider bottom")
    expect(net(components, "R180", "1"), "/Power & Battery/BAT_PROT_VIN", "fuel gauge divider pack input")
    expect(net(components, "R181", "2"), "/Power & Battery/FG_VSS", "fuel gauge divider Kelvin return")
    for ref in ("C180", "C182", "C183", "R189"):
        expect(net(components, ref, "2"), "/Power & Battery/FG_VSS", f"{ref} fuel-gauge Kelvin return")
    expect(net(components, "R183", "1"), "/Power & Battery/FG_VSS", "fuel gauge SRP pack-side source")


def check_dnp_metadata(components):
    dnp, exclude_bom = component_flags()
    for ref, item in components.items():
        if "DNP" in item.value.upper():
            if ref not in dnp:
                fail(f"{ref} value says DNP but KiCad dnp property is missing")
            if ref not in exclude_bom:
                fail(f"{ref} value says DNP but it is not excluded from BOM")
    for ref in dnp:
        if ref not in exclude_bom:
            fail(f"{ref} is DNP but not excluded from BOM")


def check_ec_core(components):
    for pin in ("6", "11", "19", "21", "22", "28", "50", "75", "100"):
        expect(net(components, "U4", pin), "/MCU_3V3", f"STM32 VDD/VBAT/VDDA pin {pin}")
    for pin in ("10", "20", "27", "74", "99"):
        expect(net(components, "U4", pin), "GND", f"STM32 VSS/VSSA pin {pin}")
    expect(net(components, "U4", "49"), "/EC & MCU/VCAP1_NODE", "STM32 VCAP1")
    expect(net(components, "U4", "73"), "/EC & MCU/VCAP2_NODE", "STM32 VCAP2")
    for pin, want, note in [
        ("47", "/RADIO_VHF_UART_TX", "PB10 USART3_TX"),
        ("48", "/RADIO_VHF_UART_RX", "PB11 USART3_RX"),
        ("63", "/RADIO_UHF_UART_TX", "PC6 USART6_TX"),
        ("64", "/RADIO_UHF_UART_RX", "PC7 USART6_RX"),
        ("67", "/WIFI_W_DISABLE1_N_EC", "PA8 drives the isolated WLAN disable input"),
        ("68", "/GNSS_UART_TX", "PA9 USART1_TX"),
        ("69", "/GNSS_UART_RX", "PA10 USART1_RX"),
        ("77", "/WIFI_W_DISABLE2_N_EC", "PA15 drives the isolated Bluetooth disable input"),
    ]:
        expect(net(components, "U4", pin), want, f"STM32 hardware UART/GPIO allocation {note}")
    expect(net(components, "U4", "44"), "/MU_12V_ENABLE", "STM32 PE13 Mu 12V active-high enable")
    expect(net(components, "U4", "45"), "/MU_S0_HIGH", "STM32 PE14 Mu S0 status input")
    expect(net(components, "U4", "46"), "/MU_12V_PG", "STM32 Mu 12V power-good input")
    expect(net(components, "U4", "36"), "/TRACKPAD_FAULT_N", "STM32 PB1 trackpad fault input")
    expect(net(components, "U4", "42"), "/AUDIO_MIC_EN", "STM32 microphone privacy-enable output")
    expect(net(components, "U4", "15"), "/KB_RGB_PWR_EN", "STM32 PC0 keyboard RGB enable")
    expect(net(components, "U4", "16"), "/KB_RGB_FAULT_N", "STM32 PC1 keyboard RGB fault input")
    expect(net(components, "U4", "62"), "/KB_RGB_DATA_3V3", "STM32 PD15/TIM4_CH4 keyboard RGB data")
    expect(net(components, "U4", "7"), "/EC & MCU/SOURCE_MGR_INT_N", "STM32 source-manager interrupt")
    expect(net(components, "U4", "17"), "/RADIO_VHF_RF_SEL_3V3", "STM32 VHF RF-select logic")
    expect(net(components, "U4", "18"), "/RADIO_UHF_RF_SEL_3V3", "STM32 UHF RF-select logic")
    expect(net(components, "U4", "29"), "/CHG_ENABLE", "STM32 fail-off charger enable")
    expect(net(components, "U4", "26"), "/PMIC_QON_ASSERT",
           "STM32 active-high open-drain QON pulse control")
    expect(net(components, "U4", "51"), "/EC & MCU/SERVICE_MUX_RESET_REQ_N", "STM32 service-mux reset request")
    for pin, want, note in (
        ("33", "/PD1_VALID_N", "left dual-role source-qualified input"),
        ("37", "/PD2_VALID_N", "right dual-role source-qualified input"),
        ("39", "/PD1_TCPC_IRQ_N", "left TPS25751A interrupt"),
        ("90", "/PD2_TCPC_IRQ_N", "right TPS25751A interrupt"),
        ("91", "/RADIO_DB_PWR_EN", "optional radio daughterboard power enable"),
        ("96", "/PD_PROTECT_FAULT_N", "dual-role protection aggregate fault"),
    ):
        expect(net(components, "U4", pin), want, f"STM32 source/radio allocation {note}")
    for obsolete in ("J5", "J6", "J7", "J13", "J14", "J15"):
        if obsolete in components:
            fail(f"obsolete EC map/probe header {obsolete} is still present")
    expect(net(components, "U4", "89"), "/INTERNAL_USB_VBUS_FAULT_N",
           "STM32 internal USB power-switch fault input")
    expect(net(components, "R34", "1"), "/MCU_3V3", "EC SWD VTref source")
    expect(net(components, "R34", "2"), "/EC & MCU/EC_SWD_VTREF", "EC SWD VTref isolated target")
    expect_value_prefix(components, "R34", "0R", "EC SWD VTref link")
    expect(comp(components, "J4").footprint,
           "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical", "EC SWD footprint")
    for pin, want in {
        "1": "/EC & MCU/EC_SWD_VTREF", "2": "/EC & MCU/SWDIO_NET",
        "3": "/EC & MCU/NRST_NET", "4": "/EC & MCU/SWCLK_NET", "5": "GND",
    }.items():
        expect(net(components, "J4", pin), want, f"EC TC2030 pin {pin}")
    expect_unconnected(components, "J4", "6")
    _dnp, exclude_bom = component_flags()
    if "J4" not in exclude_bom:
        fail("J4 is a PCB copper programming target and must be excluded from BOM")
    expect(prop(components, "J4", "ProcurementClass"), "PCB copper test feature",
           "EC TC2030 procurement class")
    for cref, vcap in (("C29", "/EC & MCU/VCAP1_NODE"), ("C30", "/EC & MCU/VCAP2_NODE")):
        expect(net(components, cref, "1"), vcap, f"{cref} VCAP side")
        expect(net(components, cref, "2"), "GND", f"{cref} ground side")
        expect_contains(comp(components, cref).value, "2.2u", f"{cref} value")

    # Oscillator parts are a qualified starting combination, not generic
    # placeholder values. Both grounded-can pads on the HSE crystal matter.
    expect(comp(components, "Y1").footprint,
           "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "HSE crystal footprint")
    expect(prop(components, "Y1", "MPN"), "J32SMX-K-F-G-I-8M0", "HSE crystal MPN")
    for pin, want in {
        "1": local_net("EC & MCU", "HSE_IN"),
        "2": "GND",
        "3": local_net("EC & MCU", "HSE_XTAL_OUT"),
        "4": "GND",
    }.items():
        expect(net(components, "Y1", pin), want, f"HSE crystal pin {pin}")
    expect_value_prefix(components, "C32", "10p C0G", "HSE input load capacitor")
    expect_value_prefix(components, "C33", "10p C0G", "HSE output load capacitor")
    expect(prop(components, "C32", "MPN"), "C0603C100C5GACTU", "HSE C32 MPN")
    expect(prop(components, "C33", "MPN"), "C0603C100C5GACTU", "HSE C33 MPN")
    expect(net(components, "C32", "1"), local_net("EC & MCU", "HSE_IN"), "HSE C32 signal")
    expect(net(components, "C33", "1"), local_net("EC & MCU", "HSE_XTAL_OUT"), "HSE C33 signal")
    expect_value_prefix(components, "R37", "0R HSE", "HSE series tuning position")
    expect(net(components, "R37", "1"), local_net("EC & MCU", "HSE_XTAL_OUT"), "HSE R37 crystal side")
    expect(net(components, "R37", "2"), local_net("EC & MCU", "HSE_OUT"), "HSE R37 MCU side")

    expect(comp(components, "Y2").footprint,
           "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", "LSE crystal footprint")
    expect(prop(components, "Y2", "MPN"), "X1A000141000612", "LSE crystal MPN")
    expect(net(components, "Y2", "1"), local_net("EC & MCU", "LSE_IN"), "LSE crystal pin 1")
    expect(net(components, "Y2", "2"), local_net("EC & MCU", "LSE_OUT"), "LSE crystal pin 2")
    expect_value_prefix(components, "C34", "6.8p C0G", "LSE input load capacitor")
    expect_value_prefix(components, "C35", "6.8p C0G", "LSE output load capacitor")
    expect(prop(components, "C34", "MPN"), "C0603C689C5GACTU", "LSE C34 MPN")
    expect(prop(components, "C35", "MPN"), "C0603C689C5GACTU", "LSE C35 MPN")
    for cref in ("C32", "C33", "C34", "C35"):
        expect(net(components, cref, "2"), "GND", f"{cref} oscillator ground")

    expect(comp(components, "J16").footprint,
           "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
           "case-control harness footprint")
    expect(prop(components, "J16", "MPN"), "SM03B-SRSS-TB", "case-control connector MPN")
    for pin, want in {"1": "GND", "2": "/CASE_PWRBTN_N", "3": "/MU_RSTBTN_N"}.items():
        expect(net(components, "J16", pin), want, f"case-control harness pin {pin}")
    expect(net(components, "R32", "1"), "/MCU_3V3", "NRST pull-up top")
    expect(net(components, "R32", "2"), "/EC & MCU/NRST_NET", "NRST pull-up bottom")
    expect(net(components, "C31", "1"), "/EC & MCU/NRST_NET", "NRST cap")
    expect(net(components, "SW1", "1"), "/EC & MCU/NRST_NET", "reset switch signal")
    expect(net(components, "SW1", "2"), "GND", "reset switch ground")
    expect(prop(components, "SW1", "MPN"), "B3S-1000", "EC reset switch exact MPN")
    expect(net(components, "R33", "1"), "/EC & MCU/BOOT0_NET", "BOOT0 strap signal")
    expect(net(components, "R33", "2"), "GND", "BOOT0 strap ground")
    expect(net(components, "U5", "3"), "/EC_AON_IN", "EC buck VIN")
    expect(net(components, "U5", "1"), "GND", "EC buck GND")
    expect(net(components, "L3", "1"), "/EC & MCU/BUCK_SW", "EC buck inductor switch side")
    expect(net(components, "L3", "2"), "/MCU_3V3", "EC buck output rail")
    expect_value_prefix(components, "L3", "10uH", "EC buck inductor")
    expect_value_prefix(components, "R35", "100k", "EC buck feedback top")
    expect_value_prefix(components, "R36", "22.1k", "EC buck feedback bottom")
    expect(net(components, "C292", "1"), "/MCU_3V3", "EC buck feed-forward output side")
    expect(net(components, "C292", "2"), "/EC & MCU/BUCK_FB", "EC buck feed-forward FB side")
    for ref in ("C36", "C37"):
        expect(net(components, ref, "1"), "/EC_AON_IN", f"{ref} always-on buck input")
        expect(net(components, ref, "2"), "GND", f"{ref} always-on buck return")

    source_manager_pins = {
        "1": "/EC & MCU/SOURCE_MGR_INT_N", "2": "GND", "3": "/EC & MCU/NRST_NET",
        "4": "/PD1_PATH_EN", "5": "/PD2_PATH_EN",
        "6": "/EC & MCU/SOURCE_MGR_SPARE1",
        "7": "/PD1_EFUSE_FAULT_N", "8": "/PD2_EFUSE_FAULT_N",
        "9": "/EC & MCU/SOURCE_MGR_SPARE2", "10": "/PACK_FAULT_N",
        "11": "/AUX_FAULT_N", "12": "GND", "13": "/PACK_RETRY_PULSE",
        "14": "/AUX_PGOOD", "15": "/MAIN_USB_VALID_N",
        "16": "/MAIN_AUX_VALID_N", "17": "/AON_FAULT_N",
        "18": "/RADIO_DB_PG", "19": "/RADIO_DB_FAULT_N",
        "20": "/RADIO_DB_PRESENT_N", "21": "GND",
        "22": "/I2C_SCL", "23": "/I2C_SDA", "24": "/MCU_3V3",
    }
    expect_contains(comp(components, "U44").value, "TCA9539PWR", "resettable always-on source manager")
    expect(prop(components, "U44", "MPN"), "TCA9539PWR", "source-manager exact MPN")
    expect(prop(components, "U44", "I2CAddress7Bit"), "0x74", "source-manager 7-bit I2C address")
    for pin, want in source_manager_pins.items():
        expect(net(components, "U44", pin), want, f"TCA9539 source-manager pin {pin}")
    expect_value_prefix(components, "R780", "10k", "source-manager interrupt pull-up")
    expect(net(components, "R780", "1"), "/MCU_3V3", "source-manager interrupt pull-up rail")
    expect(net(components, "R780", "2"), "/EC & MCU/SOURCE_MGR_INT_N", "source-manager interrupt signal")
    expect_value_prefix(components, "R781", "10k", "aggregate AON fault pull-up")
    expect(net(components, "R781", "1"), "/MCU_3V3", "aggregate AON fault pull-up rail")
    expect(net(components, "R781", "2"), "/AON_FAULT_N", "aggregate AON fault input")
    for index in range(1, 3):
        ref = f"R{781 + index}"
        expect_value_prefix(components, ref, "100k", f"{ref} source-manager spare pull-down")
        expect(net(components, ref, "1"), f"/EC & MCU/SOURCE_MGR_SPARE{index}", f"{ref} spare signal")
        expect(net(components, ref, "2"), "GND", f"{ref} spare return")
    expect(net(components, "C780", "1"), "/MCU_3V3", "source-manager bypass rail")
    expect(net(components, "C780", "2"), "GND", "source-manager bypass return")
    expect_value_prefix(components, "R172", "100k", "service-mux reset request pull-up")
    expect(net(components, "R172", "1"), "/MCU_3V3", "service-mux reset request pull-up rail")
    expect(net(components, "R172", "2"), "/EC & MCU/SERVICE_MUX_RESET_REQ_N", "service-mux reset request")
    for pin, want in {
        "1": "/EC & MCU/NRST_NET", "2": "/EC & MCU/SERVICE_MUX_RESET_REQ_N",
        "3": "GND", "4": "/SERVICE_MUX_RESET_N", "5": "/MCU_3V3",
    }.items():
        expect(net(components, "U46", pin), want, f"service-mux reset gate pin {pin}")
    expect_contains(comp(components, "U46").value, "SN74LVC1G08", "service-mux hardware reset gate")
    expect(net(components, "C781", "1"), "/MCU_3V3", "service-mux reset gate bypass rail")
    expect(net(components, "C781", "2"), "GND", "service-mux reset gate bypass return")


def check_mu_carrier(components, pin_names):
    standoff_path = ROOT / "ducktop2.pretty" / "Wurth_9774055243R_M2_H5.5.kicad_mod"
    standoff_text = standoff_path.read_text(encoding="utf-8")
    standoff_pads = rounded_pad_set(source_footprint_pads(standoff_path))
    expected_standoff_pads = rounded_pad_set([
        ("1", 0.0, 0.0, 3.0),
        ("1", 0.0, 0.0, None),
    ])
    if standoff_pads != expected_standoff_pads:
        fail(f"Mu standoff source pads differ from released land pattern: {standoff_pads}")
    expect_contains(standoff_text,
                    '(pad "1" np_thru_hole circle (at 0 0) (size 3.0 3.0) (drill 3.0)',
                    "Mu standoff 3.0mm NPTH locating hole")
    expect_contains(standoff_text,
                    '(pad "1" smd roundrect (at 0 0) (size 5.3 5.3)',
                    "Mu standoff 5.3mm solder land")
    if not (ROOT / "ducktop2.3dshapes" / "Wurth_9774055243R.step").exists():
        fail("Mu standoff exact 5.5mm STEP model is missing")

    expect(comp(components, "A1").footprint,
           "Module_LattePanda:LattePanda_Module_H8.0mm_Horizontal",
           "LattePanda Mu 8mm standard-orientation socket footprint")
    expect(prop(components, "A1", "Manufacturer"), "TE Connectivity",
           "LattePanda Mu socket manufacturer")
    expect(prop(components, "A1", "MPN"), "2309411-1",
           "LattePanda Mu socket MPN")
    expect(prop(components, "A1", "ModuleAssemblyItem"), "A2 DFRobot DFR1149",
           "LattePanda Mu socket-to-module assembly contract")
    expect_contains(prop(components, "A1", "BIOSProfile"),
                    "S70NC1R200-16G-B.bin", "LattePanda Mu BIOS profile")
    expect_contains(prop(components, "A1", "BIOSProfile"),
                    "6edcfe021d84baf2b6ea3e4f4df4e81442a6be3580905f255221644d0eeb0bed",
                    "LattePanda Mu BIOS binary hash")
    expect(prop(components, "A2", "Manufacturer"), "DFRobot",
           "LattePanda Mu module manufacturer")
    expect(prop(components, "A2", "MPN"), "DFR1149",
           "LattePanda Mu module SKU")
    expect_contains(prop(components, "A2", "BIOSProfile"), "build 2026-06-03",
                    "LattePanda Mu BIOS build date")
    for ref in ("H1", "H2"):
        expect(comp(components, ref).footprint,
               "ducktop2:Wurth_9774055243R_M2_H5.5",
               f"{ref} exact Mu standoff footprint")
        expect(prop(components, ref, "Manufacturer"), "Wurth Elektronik",
               f"{ref} standoff manufacturer")
        expect(prop(components, ref, "MPN"), "9774055243R",
               f"{ref} standoff MPN")
        expect_contains(prop(components, ref, "Hardware_Spec"), "5.5+/-0.1mm",
                        f"{ref} standoff height contract")
        expect_contains(prop(components, ref, "MatingScrew"), "M2x4mm",
                        f"{ref} mating screw contract")
        expect_contains(prop(components, ref, "TorqueLimit"), "0.2 N*m maximum",
                        f"{ref} torque ceiling")
        expect(net(components, ref, "1"), "GND", f"{ref} grounded solder land")

    for ref in ("H3", "H4"):
        expect(comp(components, ref).footprint,
               "ducktop2:SMT_Standoff_M2_H2.5_C4_Tail2.7x1.5",
               f"{ref} LattePanda V2 M.2 standoff footprint")
        expect(prop(components, ref, "Manufacturer"), "Unbranded",
               f"{ref} M.2 standoff manufacturer classification")
        expect(prop(components, ref, "MPN"), "M2XC4X2.5+C2.7X1.5",
               f"{ref} official M.2 standoff source designation")
        expect(prop(components, ref, "Supplier"), "Taobao",
               f"{ref} official M.2 standoff supplier")
        expect(prop(components, ref, "Supplier_SKU"), "4725777108077",
               f"{ref} official M.2 standoff supplier SKU")
        expect_contains(prop(components, ref, "Buy_Link"), "id=655855111684",
                        f"{ref} official source listing")
        expect_contains(prop(components, ref, "Reference_Design"),
                        "f954bf0275fa0aec4c1e9eb168f09644563b28a4",
                        f"{ref} pinned LattePanda source revision")
        expect_contains(prop(components, ref, "Hardware_Spec"),
                        "2.7x1.5mm locating tail",
                        f"{ref} locating-tail contract")
        expect(net(components, ref, "1"), "GND", f"{ref} grounded solder land")

    for pin in [str(n) for n in range(250, 261)]:
        expect(net(components, "A1", pin), "/MU_12V", f"LattePanda Mu regulated VIN pin {pin}")

    for pin, want in {
        "1": "/Mu Carrier/MU12_EN_UVLO", "2": "/Mu Carrier/MU12_MODE",
        "3": "/MU_12V_PG", "4": "/Mu Carrier/MU12_CC_N",
        "5": "/Mu Carrier/MU12_DITH", "6": "/Mu Carrier/MU12_FSW",
        "7": "/VSYS", "8": "/Mu Carrier/MU12_SW1", "9": "GND",
        "10": "/Mu Carrier/MU12_SW2", "11": "/Mu Carrier/MU12_PRE_SENSE",
        "12": "/Mu Carrier/MU12_ISP", "13": "/Mu Carrier/MU12_ISN",
        "14": "/Mu Carrier/MU12_FB", "15": "/Mu Carrier/MU12_COMP",
        "17": "GND", "18": "/Mu Carrier/MU12_VCC",
        "19": "/Mu Carrier/MU12_BOOT2", "20": "/Mu Carrier/MU12_BOOT1",
        "21": "/Mu Carrier/MU12_EXTVCC",
    }.items():
        expect(net(components, "U750", pin), want, f"TPS552892 pin {pin}")
    expect_unconnected(components, "U750", "16")
    expect(net(components, "L750", "1"), "/Mu Carrier/MU12_SW1", "Mu 12V inductor SW1")
    expect(net(components, "L750", "2"), "/Mu Carrier/MU12_SW2", "Mu 12V inductor SW2")
    expect_contains(comp(components, "L750").value, "4.7uH", "Mu 12V inductor value")
    expect(net(components, "RS750", "1"), "/Mu Carrier/MU12_PRE_SENSE", "Mu 12V current shunt source")
    expect(net(components, "RS750", "2"), "/MU_12V", "Mu 12V current shunt load")
    expect_value_prefix(components, "RS750", "15mOhm", "Mu 12V 3.33A current shunt")
    for ref, value, footprint in [
        ("C750", "68u 50V", "Capacitor_SMD:CP_Elec_8x10"),
        ("C751", "10u 50V", "Capacitor_SMD:C_1206_3216Metric"),
        ("C752", "10u 50V", "Capacitor_SMD:C_1206_3216Metric"),
        ("C759", "10u 50V", "Capacitor_SMD:C_1206_3216Metric"),
        ("C760", "10u 50V", "Capacitor_SMD:C_1206_3216Metric"),
        ("C761", "10u 50V", "Capacitor_SMD:C_1206_3216Metric"),
        ("C762", "100u 35V", "Capacitor_SMD:CP_Elec_6.3x5.8"),
        ("C764", "22u 16V", "Capacitor_SMD:C_1206_3216Metric"),
    ]:
        expect_value_prefix(components, ref, value, f"{ref} TPS552892 EVM-rated capacitor")
        expect(comp(components, ref).footprint, footprint, f"{ref} TPS552892 capacitor footprint")
    for ref, sw, node in [
        ("R764", "/Mu Carrier/MU12_SW1", "/Mu Carrier/MU12_SNUB1"),
        ("R765", "/Mu Carrier/MU12_SW2", "/Mu Carrier/MU12_SNUB2"),
    ]:
        expect_value_prefix(components, ref, "DNP 2.2R", f"{ref} optional switch-node snubber")
        expect(net(components, ref, "1"), sw, f"{ref} switch-node side")
        expect(net(components, ref, "2"), node, f"{ref} snubber RC node")
    for ref, node in (("C768", "/Mu Carrier/MU12_SNUB1"),
                      ("C769", "/Mu Carrier/MU12_SNUB2")):
        expect_value_prefix(components, ref, "DNP 2.2n 250V", f"{ref} optional switch-node snubber")
        expect(net(components, ref, "1"), node, f"{ref} snubber RC node")
        expect(net(components, ref, "2"), "GND", f"{ref} snubber return")
    for ref, value in (("R753", "102k"), ("R754", "11.3k"),
                       ("R756", "49.9k"), ("R759", "150k"), ("R760", "23.7k")):
        expect_value_prefix(components, ref, value, f"{ref} Mu 12V control value")
    expect(net(components, "A1", "5"), "/MU_S0_HIGH", "LattePanda PSON S0 status")
    expect(net(components, "Q750", "1"), "/Mu Carrier/MU12_FORCE_OFF", "Mu 12V fail-off clamp gate")
    expect(net(components, "Q750", "2"), "GND", "Mu 12V fail-off clamp source")
    expect(net(components, "Q750", "3"), "/Mu Carrier/MU12_EN_UVLO", "Mu 12V fail-off clamp drain")
    expect(net(components, "Q751", "1"), "/MU_12V_ENABLE", "Mu 12V explicit enable release gate")
    expect(net(components, "Q751", "2"), "GND", "Mu 12V explicit enable release source")
    expect(net(components, "Q751", "3"), "/Mu Carrier/MU12_FORCE_OFF", "Mu 12V explicit enable release drain")
    for ref, value, pin1, pin2 in (
        ("R761", "100k", "/Mu Carrier/MU12_FORCE_OFF", "GND"),
        ("R766", "100k", "/VSYS", "/Mu Carrier/MU12_FORCE_OFF"),
        ("R767", "100k", "/MU_12V_ENABLE", "GND"),
        ("R768", "10k", "/MCU_3V3", "/MU_S0_HIGH"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} Mu power/status bias")
        expect(net(components, ref, "1"), pin1, f"{ref} pin 1")
        expect(net(components, ref, "2"), pin2, f"{ref} pin 2")
    expect_contains(comp(components, "U769").value, "SN74LVC1G08", "qualified host-active gate")
    for pin, want in {
        "1": "/MU_S0_HIGH", "2": "/MU_12V_PG", "3": "GND",
        "4": "/MU_HOST_ACTIVE", "5": "/MCU_3V3",
    }.items():
        expect(net(components, "U769", pin), want, f"U769 qualified host-active pin {pin}")
    expect_value_prefix(components, "R769", "100k", "MU_HOST_ACTIVE fail-low bias")
    expect(net(components, "R769", "1"), "/MU_HOST_ACTIVE", "MU_HOST_ACTIVE fail-low signal")
    expect(net(components, "R769", "2"), "GND", "MU_HOST_ACTIVE fail-low return")
    expect_value_prefix(components, "C793", "100n", "host-active gate bypass")
    expect(net(components, "C793", "1"), "/MCU_3V3", "host-active gate bypass rail")
    expect(net(components, "C793", "2"), "GND", "host-active gate bypass return")
    for ref in ("SW2", "SW3"):
        expect(prop(components, ref, "MPN"), "B3S-1000", f"{ref} exact switch MPN")
    expect(comp(components, "J9").footprint,
           "Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal",
           "RTC connector low-profile keyed footprint")
    expect(prop(components, "J9", "MPN"), "SM02B-GHS-TB", "RTC connector exact MPN")
    expect(prop(components, "J9", "MatingHousing"), "GHR-02V-S", "RTC mating housing")
    for ref, want in (
        ("TP5", "/SYS_5V"), ("TP6", "/SYS_3V3"),
        ("TP8", "/MU_12V"), ("TP12", "/MU_12V_PG"),
    ):
        expect(comp(components, ref).footprint,
               "TestPoint:TestPoint_Pad_D1.0mm", f"{ref} fixture footprint")
        expect(net(components, ref, "1"), want, f"{ref} fixture net")
        expect(prop(components, ref, "ProcurementClass"),
               "PCB copper test feature", f"{ref} procurement class")
    check_tps2553_semantics(components, pin_names)
    self_test_tps2553_guard(components, pin_names)
    expect_value_prefix(components, "U770", "TPS2553DDBVR", "physical internal host-VBUS switch")
    expect_value_prefix(components, "R773", "43.2k", "internal host-VBUS current limit")
    expect(net(components, "R773", "1"), "/Mu Carrier/INTERNAL_USB_VBUS_ILIM", "internal VBUS ILIM node")
    expect(net(components, "R773", "2"), "GND", "internal VBUS ILIM return")
    expect_value_prefix(components, "R774", "10k", "internal VBUS fault pull-up")
    expect(net(components, "R774", "1"), "/MCU_3V3", "internal VBUS fault pull-up rail")
    expect(net(components, "R774", "2"), "/INTERNAL_USB_VBUS_FAULT_N", "internal VBUS fault signal")
    # U771 is always powered from MCU_3V3 (TPS3897 VCC), so SENSE_OUT
    # is deterministic even when VBUS is absent.
    for pin, want in {
        "1": "/MCU_3V3", "2": "GND", "3": local_net("Mu Carrier", "INTERNAL_USB_VBUS_SENSE"),
        "4": "/INTERNAL_USB_VBUS_VALID", "6": "/MCU_3V3",
    }.items():
        expect(net(components, "U771", pin), want, f"physical internal VBUS supervisor pin {pin}")
    expect_unconnected(components, "U771", "5")
    expect_value_prefix(components, "U771", "TPS3897ADRYR", "always-powered internal VBUS supervisor")
    expect(prop(components, "U771", "MPN"), "TPS3897ADRYR", "physical internal VBUS supervisor orderable")
    expect_value_prefix(components, "R775", "10k", "internal VBUS valid pull-up")
    expect(net(components, "R775", "1"), "/MCU_3V3", "internal VBUS valid pull-up rail")
    expect(net(components, "R775", "2"), "/INTERNAL_USB_VBUS_VALID", "internal VBUS valid signal")
    for ref, value, rail in (
        ("C794", "1u", "/SYS_5V"),
        ("C830", "10u", "/Mu Carrier/INTERNAL_USB_VBUS"),
        ("C831", "100n", "/MCU_3V3"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} internal host-VBUS support")
        expect(net(components, ref, "1"), rail, f"{ref} internal host-VBUS rail")
        expect(net(components, ref, "2"), "GND", f"{ref} internal host-VBUS return")
    # TPS3897 divider: 78.7k/10.0k sets VBUS trip at ~4.44V (0.5V at SENSE)
    expect_value_prefix(components, "R777", "78.7k", "VBUS sense top divider")
    expect(net(components, "R777", "1"), local_net("Mu Carrier", "INTERNAL_USB_VBUS"), "VBUS sense top input")
    expect(net(components, "R777", "2"), local_net("Mu Carrier", "INTERNAL_USB_VBUS_SENSE"), "VBUS sense divider mid")
    expect_value_prefix(components, "R778", "10.0k", "VBUS sense bottom divider")
    expect(net(components, "R778", "1"), local_net("Mu Carrier", "INTERNAL_USB_VBUS_SENSE"), "VBUS sense divider mid")
    expect(net(components, "R778", "2"), "GND", "VBUS sense bottom return")
    for ref, want in (
        ("TP13", "/Mu Carrier/INTERNAL_USB_VBUS"),
        ("TP14", "/INTERNAL_USB_VBUS_VALID"),
        ("TP15", "/INTERNAL_USB_VBUS_FAULT_N"),
    ):
        expect(comp(components, ref).footprint,
               "TestPoint:TestPoint_Pad_D1.0mm", f"{ref} fixture footprint")
        expect(net(components, ref, "1"), want, f"{ref} fixture net")
        expect(prop(components, ref, "ProcurementClass"),
               "PCB copper test feature", f"{ref} procurement class")

    # All PCIe endpoints are unpowered unless the Mu is fully in S0. This
    # prevents powered endpoint I/O from back-powering an unpowered host.
    for pin, want in {
        "1": "/SYS_3V3", "2": "/SYS_3V3", "3": "/MU_HOST_ACTIVE",
        "4": "/SYS_3V3", "5": "GND",
        "6": "/Mu Carrier/PCIE_3V3_CT",
        "7": "/PCIE_3V3", "8": "/PCIE_3V3", "9": "GND",
    }.items():
        expect(net(components, "U772", pin), want, f"PCIe endpoint switch pin {pin}")
    expect_contains(comp(components, "U772").value, "TPS22975NDSGR",
                    "PCIe endpoint load switch")
    expect(prop(components, "U772", "MPN"), "TPS22975NDSGR",
           "PCIe endpoint switch MPN")
    expect_value_prefix(components, "R776", "100k", "PCIe switch fail-low bias")
    expect(net(components, "R776", "1"), "/MU_HOST_ACTIVE", "PCIe switch enable")
    expect(net(components, "R776", "2"), "GND", "PCIe switch fail-low return")
    for ref, value, rail in (
        ("C832", "1u", "/SYS_3V3"),
        ("C833", "4.7n", "/Mu Carrier/PCIE_3V3_CT"),
        ("C834", "47u", "/PCIE_3V3"),
        ("C835", "100n", "/PCIE_3V3"),
        ("C836", "10u", "/PCIE_3V3"),
        ("C837", "100n", "/PCIE_3V3"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} PCIe rail support")
        expect(net(components, ref, "1"), rail, f"{ref} PCIe rail")
        expect(net(components, ref, "2"), "GND", f"{ref} PCIe return")

    # Default-BIOS lane allocation used by Ducktop2.  Keep the host-side TX
    # coupling nodes explicit so a TX/RX or polarity swap cannot hide behind
    # matching hierarchical net names.
    for pin, want in {
        "13": "/Mu Carrier/USBC1_SSTX_RAW_P", "15": "/Mu Carrier/USBC1_SSTX_RAW_N",
        "16": "/USBC1_SSRX_P", "18": "/USBC1_SSRX_N",
        "73": "/USBC1_DM", "75": "/USBC1_DP",
        "19": "/Mu Carrier/USBC2_SSTX_RAW_P", "21": "/Mu Carrier/USBC2_SSTX_RAW_N",
        "22": "/USBC2_SSRX_P", "24": "/USBC2_SSRX_N",
        "70": "/USBC2_DP", "72": "/USBC2_DM",
        "129": "/PD_PROTECT_FAULT_N",
        "31": "/Mu Carrier/WIFI_PCIE_TX_RAW_P", "33": "/Mu Carrier/WIFI_PCIE_TX_RAW_N",
        "34": "/WIFI_PCIE_RX_P", "36": "/WIFI_PCIE_RX_N",
        "67": "/WIFI_USB_DN", "69": "/WIFI_USB_DP",
        "88": "/WIFI_REFCLK_P", "90": "/WIFI_REFCLK_N",
        "100": "/WIFI_CLKREQ_N",
        "79": "/EC_HOST_USB_DM", "81": "/EC_HOST_USB_DP",
        "109": "/AUDIO_USB_DM", "111": "/AUDIO_USB_DP",
        "76": "/MAKER_USB_DP", "78": "/MAKER_USB_DM",
        "82": "/TRACKPAD_USB_DP", "84": "/TRACKPAD_USB_DM",
        "37": "/Mu Carrier/PCIE_M_L0_TX_RAW_P", "39": "/Mu Carrier/PCIE_M_L0_TX_RAW_N",
        "40": "/Mu Carrier/PCIE_M_L0_RX_P", "42": "/Mu Carrier/PCIE_M_L0_RX_N",
        "43": "/Mu Carrier/PCIE_M_L1_TX_RAW_P", "45": "/Mu Carrier/PCIE_M_L1_TX_RAW_N",
        "46": "/Mu Carrier/PCIE_M_L1_RX_P", "48": "/Mu Carrier/PCIE_M_L1_RX_N",
        "49": "/Mu Carrier/PCIE_M_L2_TX_RAW_P", "51": "/Mu Carrier/PCIE_M_L2_TX_RAW_N",
        "52": "/Mu Carrier/PCIE_M_L2_RX_P", "54": "/Mu Carrier/PCIE_M_L2_RX_N",
        "55": "/Mu Carrier/PCIE_M_L3_TX_RAW_P", "57": "/Mu Carrier/PCIE_M_L3_TX_RAW_N",
        "58": "/Mu Carrier/PCIE_M_L3_RX_P", "60": "/Mu Carrier/PCIE_M_L3_RX_N",
        "61": "/GBE_HOST_TX_P", "63": "/GBE_HOST_TX_N",
        "64": "/GBE_HOST_RX_P", "66": "/GBE_HOST_RX_N",
        "94": "/GBE_REFCLK_P", "96": "/GBE_REFCLK_N",
        "102": "/GBE_CLKREQ_N",
        "97": "/Mu Carrier/PCIE_M_REFCLK_SRC_P", "99": "/Mu Carrier/PCIE_M_REFCLK_SRC_N",
        "103": "/PCIE_WAKE_N", "105": "/PLTRST_SRC_N",
        "177": "/TCP0_DDC_SDA", "179": "/TCP0_DDC_SCL", "187": "/TCP0_HPD",
        "227": "/TCP0_TXRX1_N", "229": "/TCP0_TXRX1_P",
        "233": "/TCP0_TX1_N", "235": "/TCP0_TX1_P",
        "239": "/TCP0_TXRX0_N", "241": "/TCP0_TXRX0_P",
        "245": "/TCP0_TX0_N", "247": "/TCP0_TX0_P",
    }.items():
        expect(net(components, "A1", pin), want, f"LattePanda Mu pin {pin}")

    # The panel uses the Mu module's onboard 40-pin eDP connector.  DDIB on
    # the SODIMM edge is intentionally unused, as is USB2_P6 (reserved for a
    # future Mu Type-C/PD-controller configuration).
    for pin in ("169", "171", "183", "191", "193", "197", "199", "203", "205",
                "209", "211", "215", "217", "112", "114"):
        expect_unconnected(components, "A1", pin)

    expect_contains(comp(components, "U6").value, "TPS56637RPAR", "SYS_5V regulator exact part")
    expect(comp(components, "U6").footprint,
           "ducktop2:Texas_RPA0010A_VQFN-HR-10_3x3mm", "TPS56637 exact RPA footprint")
    for pin, want in {
        "1": "/Mu Carrier/BUCK5_EN", "2": "/Mu Carrier/BUCK5_FB",
        "3": "GND", "4": "/Mu Carrier/SYS_5V_PG", "6": "/Mu Carrier/BUCK5_SW",
        "7": "/Mu Carrier/BUCK5_BOOT", "8": "/VSYS", "9": "GND", "10": "GND",
    }.items():
        expect(net(components, "U6", pin), want, f"TPS56637 pin {pin}")
    expect_unconnected(components, "U6", "5")
    expect(comp(components, "L4").footprint, "Inductor_SMD:L_Coilcraft_XAL7070-XXX", "SYS_5V inductor footprint")
    expect_value_prefix(components, "L4", "XAL7070-332MEC", "SYS_5V inductor exact part")
    expect(net(components, "L4", "1"), "/Mu Carrier/BUCK5_SW", "SYS_5V inductor switch side")
    expect(net(components, "L4", "2"), "/SYS_5V", "SYS_5V inductor output side")
    for ref in ("C40", "C41", "C42"):
        expect(net(components, ref, "1"), "/VSYS", f"{ref} TPS56637 input rail")
        expect(net(components, ref, "2"), "GND", f"{ref} TPS56637 input return")
    expect(net(components, "C43", "1"), "/Mu Carrier/BUCK5_BOOT", "TPS56637 bootstrap capacitor")
    expect(net(components, "C43", "2"), "/Mu Carrier/BUCK5_SW", "TPS56637 bootstrap switch side")
    for ref in ("C44", "C45"):
        expect(net(components, ref, "1"), "/SYS_5V", f"{ref} TPS56637 output rail")
        expect(net(components, ref, "2"), "GND", f"{ref} TPS56637 output return")
    expect_value_prefix(components, "R40", "76.8k 0.1%", "SYS_5V HDMI-headroom FB top value")
    expect_value_prefix(components, "R41", "10k 0.1%", "SYS_5V HDMI-headroom FB bottom value")
    expect_value_prefix(components, "R42", "169k 1%", "TPS56637 enable divider top")
    expect_value_prefix(components, "R45", "36.1k 1%", "TPS56637 enable divider bottom")
    expect_value_prefix(components, "R46", "100k", "TPS56637 power-good pull-up")

    expect_contains(comp(components, "U7").value, "TPS56637RPAR", "SYS_3V3 regulator exact part")
    expect(comp(components, "U7").footprint,
           "ducktop2:Texas_RPA0010A_VQFN-HR-10_3x3mm", "SYS_3V3 TPS56637 footprint")
    for pin, want in {
        "1": "/Mu Carrier/BUCK33_EN", "2": "/Mu Carrier/BUCK33_FB",
        "3": "GND", "4": "/Mu Carrier/SYS_3V3_PG", "6": "/Mu Carrier/BUCK33_SW",
        "7": "/Mu Carrier/BUCK33_BOOT", "8": "/VSYS", "9": "GND", "10": "GND",
    }.items():
        expect(net(components, "U7", pin), want, f"SYS_3V3 TPS56637 pin {pin}")
    expect_unconnected(components, "U7", "5")
    expect(comp(components, "L5").footprint, "Inductor_SMD:L_Coilcraft_XAL7070-XXX", "SYS_3V3 inductor footprint")
    expect_value_prefix(components, "L5", "XAL7070-222MEC", "SYS_3V3 inductor exact part")
    expect(net(components, "L5", "1"), "/Mu Carrier/BUCK33_SW", "SYS_3V3 inductor switch side")
    expect(net(components, "L5", "2"), "/SYS_3V3", "SYS_3V3 inductor output side")
    expect_value_prefix(components, "R43", "45.3k", "SYS_3V3 FB top value")
    expect_value_prefix(components, "R44", "10k", "SYS_3V3 FB bottom value")
    expect_value_prefix(components, "R770", "169k", "SYS_3V3 enable top value")
    expect_value_prefix(components, "R771", "36.1k", "SYS_3V3 enable bottom value")
    expect_value_prefix(components, "R772", "100k", "SYS_3V3 power-good pull-up")
    for ref in ("C46", "C790", "C791"):
        expect(net(components, ref, "1"), "/VSYS", f"{ref} SYS_3V3 input rail")
        expect(net(components, ref, "2"), "GND", f"{ref} SYS_3V3 input return")
    expect(net(components, "C47", "1"), "/Mu Carrier/BUCK33_BOOT", "SYS_3V3 bootstrap node")
    expect(net(components, "C47", "2"), "/Mu Carrier/BUCK33_SW", "SYS_3V3 bootstrap switch node")
    for ref in ("C48", "C792"):
        expect(net(components, ref, "1"), "/SYS_3V3", f"{ref} SYS_3V3 output rail")
        expect(net(components, ref, "2"), "GND", f"{ref} SYS_3V3 output return")

    for ref, p1, p2 in (
        ("C66", "/Mu Carrier/USBC1_SSTX_RAW_P", "/USBC1_SSTX_P"),
        ("C67", "/Mu Carrier/USBC1_SSTX_RAW_N", "/USBC1_SSTX_N"),
        ("C586", "/Mu Carrier/USBC2_SSTX_RAW_P", "/USBC2_SSTX_P"),
        ("C587", "/Mu Carrier/USBC2_SSTX_RAW_N", "/USBC2_SSTX_N"),
    ):
        expect(net(components, ref, "1"), p1, f"{ref} Mu USB transmitter-side AC coupling")
        expect(net(components, ref, "2"), p2, f"{ref} native USB-C side")
        expect_value_prefix(components, ref, "100n", f"{ref} USB3 coupling value")

    for lane, refs in enumerate((("C68", "C69"), ("C592", "C593"),
                                 ("C594", "C595"), ("C596", "C597"))):
        for polarity, ref in zip(("P", "N"), refs):
            expect(net(components, ref, "1"), f"/Mu Carrier/PCIE_M_L{lane}_TX_RAW_{polarity}",
                   f"{ref} Mu NVMe TX source")
            expect(net(components, ref, "2"), f"/Mu Carrier/PCIE_M_L{lane}_TX_{polarity}",
                   f"{ref} NVMe socket side")
            expect_value_prefix(components, ref, "220n", f"{ref} PCIe coupling value")

    m2_lane_pins = {
        "41": "PCIE_M_L0_RX_N", "43": "PCIE_M_L0_RX_P",
        "47": "PCIE_M_L0_TX_N", "49": "PCIE_M_L0_TX_P",
        "29": "PCIE_M_L1_RX_N", "31": "PCIE_M_L1_RX_P",
        "35": "PCIE_M_L1_TX_N", "37": "PCIE_M_L1_TX_P",
        "17": "PCIE_M_L2_RX_N", "19": "PCIE_M_L2_RX_P",
        "23": "PCIE_M_L2_TX_N", "25": "PCIE_M_L2_TX_P",
        "5": "PCIE_M_L3_RX_N", "7": "PCIE_M_L3_RX_P",
        "11": "PCIE_M_L3_TX_N", "13": "PCIE_M_L3_TX_P",
        "53": "PCIE_M_REFCLK_N", "55": "PCIE_M_REFCLK_P",
        "50": "PCIE_M_PERST_N", "52": "PCIE_M_CLKREQ_N", "54": "PCIE_WAKE_N",
    }
    for pin, name in m2_lane_pins.items():
        expected = f"/{name}" if name in ("PCIE_WAKE_N",) else f"/Mu Carrier/{name}"
        expect(net(components, "J10", pin), expected, f"M.2 M-key pin {pin}")

    for obsolete in ("U8", "U9", "U13", "R560", "R561", "R563", "R564", "R565"):
        if obsolete in components:
            fail(f"obsolete external USB-hub component {obsolete} is still in the schematic")


def _check_legacy_native_usb_c_ports(components):
    for port in (1, 2):
        branch = f"U{port * 10 + 10}"
        tps = f"U{port * 10 + 11}"
        mux = f"U{port * 10 + 12}"
        jref = f"J{10 + port}"
        native = f"/USBC{port}"
        sheet = "Native USB-C I/O"
        usb = f"USB{port}"
        pre_rail = local_net(sheet, f"{usb}_5V_PRE")
        expect_contains(comp(components, branch).value, "TPS2553D", f"{branch} USB-C branch switch")
        for pin, want in {
            "1": "/SYS_5V", "2": "GND", "3": "/MU_HOST_ACTIVE",
            "4": "/MU_USB_OC_N", "5": local_net(sheet, f"{usb}_ILIM"),
            "6": pre_rail,
        }.items():
            expect(net(components, branch, pin), want, f"{branch} pin {pin}")
        for pin in ("2", "3", "4"):
            expect(net(components, tps, pin), pre_rail, f"{tps} isolated IN pin {pin}")
        expect(net(components, tps, "5"), "/SYS_3V3", f"{tps} AUX")
        expect(net(components, tps, "6"), "/MU_HOST_ACTIVE", f"{tps} qualified EN")
        expect(net(components, tps, "1"), "/MU_USB_OC_N", f"{tps} FAULT to Mu USB OC")
        expect(net(components, tps, "7"), "GND", f"{tps} CHG standard-current strap")
        expect(net(components, tps, "8"), "GND", f"{tps} CHG_HI standard-current strap")
        expect(net(components, tps, "9"), local_net(sheet, f"{usb}_REF_RTN"), f"{tps} REF_RTN isolated node")
        expect(net(components, tps, "10"), local_net(sheet, f"{usb}_REF"), f"{tps} REF node")
        rbase = 70 + (port - 1) * 20
        expect(net(components, f"R{rbase + 4}", "1"), local_net(sheet, f"{usb}_REF"), f"{tps} REF resistor top")
        expect(net(components, f"R{rbase + 4}", "2"), local_net(sheet, f"{usb}_REF_RTN"), f"{tps} REF_RTN resistor bottom")
        expect(net(components, tps, "11"), local_net(sheet, f"{usb}_CC1"), f"{tps} CC1")
        expect(net(components, tps, "13"), local_net(sheet, f"{usb}_CC2"), f"{tps} CC2")
        expect(net(components, tps, "14"), local_net(sheet, f"{usb}_VBUS"), f"{tps} OUT1")
        expect(net(components, tps, "15"), local_net(sheet, f"{usb}_VBUS"), f"{tps} OUT2")
        expect(net(components, tps, "18"), local_net(sheet, f"{usb}_POL_N"), f"{tps} POL")
        for pin in ("16", "17", "19", "20"):
            expect_unconnected(components, tps, pin)

        expect(net(components, mux, "6"), "/SYS_3V3", f"{mux} unused USB2 path disabled")
        expect_contains(comp(components, mux).value, "HD3SS6126", f"{mux} Gen2-capable orientation mux")
        expect(prop(components, mux, "MPN"), "HD3SS6126RUAR", f"{mux} exact 10Gbps-rated mux MPN")
        expect(net(components, mux, "9"), local_net(sheet, f"{usb}_POL_N"), f"{mux} SEL")
        for pin in ("13", "20", "30"):
            expect(net(components, mux, pin), "/SYS_3V3", f"{mux} VDD pin {pin}")
        for pin in ("10", "14", "17", "19", "21", "43"):
            expect(net(components, mux, pin), "GND", f"{mux} GND pin {pin}")
        expect(net(components, mux, "11"), f"{native}_SSTX_P", f"{mux} SSA0p native Mu TX")
        expect(net(components, mux, "12"), f"{native}_SSTX_N", f"{mux} SSA0n native Mu TX")
        expect(net(components, mux, "15"), f"{native}_SSRX_P", f"{mux} SSA1p native Mu RX")
        expect(net(components, mux, "16"), f"{native}_SSRX_N", f"{mux} SSA1n native Mu RX")
        expect(net(components, mux, "29"), local_net(sheet, f"{usb}_TX2_P_CONN"), f"{mux} SSB0p TX2")
        expect(net(components, mux, "28"), local_net(sheet, f"{usb}_TX2_N_CONN"), f"{mux} SSB0n TX2")
        expect(net(components, mux, "27"), local_net(sheet, f"{usb}_RX2_P_CONN"), f"{mux} SSB1p RX2")
        expect(net(components, mux, "26"), local_net(sheet, f"{usb}_RX2_N_CONN"), f"{mux} SSB1n RX2")
        expect(net(components, mux, "25"), local_net(sheet, f"{usb}_TX1_P_CONN"), f"{mux} SSC0p TX1")
        expect(net(components, mux, "24"), local_net(sheet, f"{usb}_TX1_N_CONN"), f"{mux} SSC0n TX1")
        expect(net(components, mux, "23"), local_net(sheet, f"{usb}_RX1_P_CONN"), f"{mux} SSC1p RX1")
        expect(net(components, mux, "22"), local_net(sheet, f"{usb}_RX1_N_CONN"), f"{mux} SSC1n RX1")
        for pin in ("7", "8", "31", "32", "33", "34"):
            expect_unconnected(components, mux, pin)

        expect_value_prefix(components, f"R{rbase + 1}", "4.99k", f"{tps} POL pull-up")
        expect_value_prefix(components, f"R{rbase + 4}", "100k 1% <=100ppm", f"{tps} REF resistor")
        expect_value_prefix(components, f"R{rbase}", "20.0k 1%", f"{branch} ILIM resistor")
        expect(net(components, f"R{rbase}", "1"), local_net(sheet, f"{usb}_ILIM"),
               f"{branch} ILIM node")
        expect(net(components, f"R{rbase}", "2"), "GND", f"{branch} ILIM return")
        for obsolete in (f"R{rbase + 2}", f"R{rbase + 3}"):
            if obsolete in components:
                fail(f"obsolete or unnecessary USB-C pull-up {obsolete} is still fitted")
        for offset, value in ((3, "100n"), (4, "100n"), (6, "100n"), (7, "1u"), (9, "10n")):
            cref = f"C{70 + (port - 1) * 20 + offset}"
            expect(net(components, cref, "1"), "/SYS_3V3", f"{mux} bypass {cref} rail")
            expect(net(components, cref, "2"), "GND", f"{mux} bypass {cref} ground")
            expect_value_prefix(components, cref, value, f"{mux} bypass {cref} value")
        input_bypass = f"C{70 + (port - 1) * 20}"
        tps_bypass = f"C{71 + (port - 1) * 20}"
        connector_bulk = f"C{75 + (port - 1) * 20}"
        input_bulk = f"C{78 + (port - 1) * 20}"
        for ref, value, rail, label in (
            (input_bypass, "100n", "/SYS_5V", "branch-switch input bypass"),
            (tps_bypass, "100n", pre_rail, "TPS25810 input bypass"),
            (input_bulk, "150u", pre_rail, "TPS25810 input reservoir"),
            (connector_bulk, "10u", local_net(sheet, f"{usb}_VBUS"), "connector VBUS bulk"),
        ):
            expect_value_prefix(components, ref, value, f"{ref} {label}")
            expect(net(components, ref, "1"), rail, f"{ref} {label} rail")
            expect(net(components, ref, "2"), "GND", f"{ref} {label} return")
        expect(net(components, jref, "A5"), local_net(sheet, f"{usb}_CC1"), f"{jref} CC1")
        expect(net(components, jref, "B5"), local_net(sheet, f"{usb}_CC2"), f"{jref} CC2")
        for pin in ("A4", "A9", "B4", "B9"):
            expect(net(components, jref, pin), local_net(sheet, f"{usb}_VBUS"), f"{jref} VBUS {pin}")
        expect(net(components, jref, "A6"), f"{native}_DP", f"{jref} D+ A")
        expect(net(components, jref, "B6"), f"{native}_DP", f"{jref} D+ B")
        expect(net(components, jref, "A7"), f"{native}_DM", f"{jref} D- A")
        expect(net(components, jref, "B7"), f"{native}_DM", f"{jref} D- B")


def _check_legacy_ch224_inputs(components):
    cold_start_contract = (
        "RAW_VBUS_4_TO_30V;CFG1_56K_REQUESTS_15V_WITHOUT_EC;"
        "15V_PDO_REQUIRED_FOR_SYSTEM_BOOT"
    )
    for idx, uref in enumerate(("U41", "U42", "U43"), start=1):
        prefix = f"/Power Inputs/PD{idx}_"
        expect_contains(comp(components, uref).value, "CH224A", f"{uref} current-reporting PD sink")
        expect(comp(components, uref).footprint,
               "Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm", f"{uref} CH224A footprint")
        expect(prop(components, uref, "AutonomousColdStartContract"), cold_start_contract,
               f"{uref} autonomous 15V cold-start contract")
        expect(net(components, uref, "1"), f"{prefix}CH224_VHV", f"{uref} VHV")
        expect(net(components, uref, "2"), f"{prefix}CH224_SCL", f"{uref} isolated SCL")
        expect(net(components, uref, "3"), f"{prefix}CH224_SDA", f"{uref} isolated SDA")
        expect(net(components, uref, "8"), f"{prefix}CH224_VBUS_SENSE", f"{uref} VBUS sense")
        expect(net(components, uref, "9"), f"{prefix}CFG1", f"{uref} CFG1")
        for ref in (f"R{120 + (idx - 1) * 10}", f"R{120 + (idx - 1) * 10 + 1}"):
            expect_value_prefix(components, ref, "0R", f"{ref} CH224A direct VBUS link")
        expect(net(components, f"R{120 + (idx - 1) * 10 + 2}", "1"), f"{prefix}CFG1", f"PD{idx} CFG1 resistor top")
        expect(net(components, f"R{120 + (idx - 1) * 10 + 2}", "2"), "GND", f"PD{idx} CFG1 resistor bottom")
        expect_prefix(comp(components, f"R{120 + (idx - 1) * 10 + 2}").value, "56k", f"PD{idx} CFG1 value")
        expect(net(components, uref, "6"), f"{prefix}CC2", f"{uref} CC2")
        expect(net(components, uref, "7"), f"{prefix}CC1", f"{uref} CC1")
        expect_unconnected(components, uref, "4")
        expect_unconnected(components, uref, "5")
        base = 120 + (idx - 1) * 10
        for ref, upstream, downstream in (
            (f"R{base + 3}", f"/PD{idx}_I2C_SCL", f"{prefix}CH224_SCL"),
            (f"R{base + 4}", f"/PD{idx}_I2C_SDA", f"{prefix}CH224_SDA"),
        ):
            expect_value_prefix(components, ref, "100R", f"{ref} CH224 I2C series damping")
            expect(prop(components, ref, "MPN"), "RC0603FR-07100RL", f"{ref} CH224 I2C resistor MPN")
            expect(net(components, ref, "1"), upstream, f"{ref} service-mux side")
            expect(net(components, ref, "2"), downstream, f"{ref} CH224 side")

        # Every capacitor visible from an unattached receptacle is deliberately
        # small; bulk energy storage lives after the default-off eFuse.
        raw = f"/PD{idx}_VBUS_RAW"
        for ref, value, rail, footprint, mpn in (
            (f"C{base}", "1u 50V X7R", f"{prefix}CH224_VHV",
             "Capacitor_SMD:C_0805_2012Metric", "GRM21BR71H105KA12L"),
            (f"C{base + 1}", "1u 50V X7R", raw,
             "Capacitor_SMD:C_0805_2012Metric", "GRM21BR71H105KA12L"),
            (f"C{800 + (idx - 1) * 10}", "1u 50V", raw,
             "Capacitor_SMD:C_0805_2012Metric", "GRM21BR71H105KA12L"),
            (f"C{801 + (idx - 1) * 10}", "100n 50V", raw,
             "Capacitor_SMD:C_0603_1608Metric", "GRM188R71H104KA93D"),
        ):
            expect_value_prefix(components, ref, value, f"{ref} pre-attach VBUS capacitor")
            expect(net(components, ref, "1"), rail, f"{ref} pre-attach VBUS rail")
            expect(net(components, ref, "2"), "GND", f"{ref} pre-attach VBUS return")
            expect(comp(components, ref).footprint, footprint, f"{ref} pre-attach footprint")
            expect(prop(components, ref, "MPN"), mpn, f"{ref} pre-attach exact MPN")

        esd = f"U{113 + idx * 10}"
        expect_contains(comp(components, esd).value, "TPD4E05U06", f"{esd} CC ESD array")
        expect(net(components, esd, "1"), f"{prefix}CC1", f"{esd} CC1")
        expect(net(components, esd, "2"), f"{prefix}CC2", f"{esd} CC2")
        expect(net(components, esd, "3"), "GND", f"{esd} ground 1")
        expect(net(components, esd, "8"), "GND", f"{esd} ground 2")

    for idx, ref in enumerate(("J21", "J22", "J23"), start=1):
        raw = f"/PD{idx}_VBUS_RAW"
        for pin in ("A4", "A9", "B4", "B9"):
            expect(net(components, ref, pin), raw, f"{ref} raw VBUS {pin}")
        for pin in ("A6", "B6", "A7", "B7"):
            expect_prefix(net(components, ref, pin), f"unconnected-({ref}-", f"{ref} power-only {pin}")

    expect_contains(comp(components, "U14").value, "LTC4417IGN", "industrial three-input PD selector")
    expect(comp(components, "U14").footprint,
           "Package_SO:SSOP-24_3.9x8.7mm_P0.635mm", "U14 exact LTC4417 GN footprint")
    for pin, want in {
        "3": "GND", "4": "/Power Inputs/PD1_UV", "5": "/Power Inputs/PD1_OV",
        "6": "/Power Inputs/PD2_UV", "7": "/Power Inputs/PD2_OV",
        "8": "/Power Inputs/PD3_UV", "9": "/Power Inputs/PD3_OV",
        "10": "/PD1_VALID_N", "11": "/PD2_VALID_N", "12": "/PD3_VALID_N",
        "13": "GND", "15": "/USB_PD_SELECTED",
        "16": "/Power Inputs/PD3_GATE", "17": "/Power Inputs/PD3_FET_COMMON",
        "18": "/Power Inputs/PD2_GATE", "19": "/Power Inputs/PD2_FET_COMMON",
        "20": "/Power Inputs/PD1_GATE", "21": "/Power Inputs/PD1_FET_COMMON",
        "22": "/Power Inputs/PD3_VBUS_GATED", "23": "/Power Inputs/PD2_VBUS_GATED",
        "24": "/Power Inputs/PD1_VBUS_GATED",
    }.items():
        expect(net(components, "U14", pin), want, f"LTC4417 U14 pin {pin}")
    for pin in ("1", "2", "14"):
        expect_unconnected(components, "U14", pin)
    for ref, valid in (("R736", "/PD1_VALID_N"), ("R737", "/PD2_VALID_N"), ("R738", "/PD3_VALID_N")):
        expect_value_prefix(components, ref, "10k", f"{ref} LTC4417 VALID pull-up")
        expect(net(components, ref, "1"), "/MCU_3V3", f"{ref} always-on pull-up rail")
        expect(net(components, ref, "2"), valid, f"{ref} VALID output")

    for idx, (qa, qb) in enumerate((("Q15", "Q16"), ("Q17", "Q18"), ("Q19", "Q20")), start=1):
        gate = local_net("Power Inputs", f"PD{idx}_GATE")
        common = local_net("Power Inputs", f"PD{idx}_FET_COMMON")
        gated = local_net("Power Inputs", f"PD{idx}_VBUS_GATED")
        for ref, drain in ((qa, gated), (qb, "/USB_PD_SELECTED")):
            expect_contains(comp(components, ref).value, "SiSS4409DN", f"{ref} PD selector PMOS")
            expect(comp(components, ref).footprint, "Package_SO:Vishay_PowerPAK_1212-8_Single", f"{ref} footprint")
            expect(net(components, ref, "1"), gate, f"{ref} gate")
            for pin in ("2", "3", "4"):
                expect(net(components, ref, pin), common, f"{ref} source {pin}")
            expect(net(components, ref, "5"), drain, f"{ref} drain")

        base = 720 + (idx - 1) * 3
        for ref, value, net_a, net_b in (
            (f"R{base}", "1.00M 0.1%", gated, local_net("Power Inputs", f"PD{idx}_UV")),
            (f"R{base + 1}", "19.6k 0.1%", local_net("Power Inputs", f"PD{idx}_UV"), local_net("Power Inputs", f"PD{idx}_OV")),
            (f"R{base + 2}", "63.4k 0.1%", local_net("Power Inputs", f"PD{idx}_OV"), "GND"),
        ):
            expect_value_prefix(components, ref, value, f"{ref} PD validation value")
            expect(net(components, ref, "1"), net_a, f"{ref} pin 1")
            expect(net(components, ref, "2"), net_b, f"{ref} pin 2")

        uref = f"U{719 + idx}"
        raw = f"/PD{idx}_VBUS_RAW"
        shdn = local_net("Power Inputs", f"PD{idx}_EFUSE_SHDN_N")
        fault = f"/PD{idx}_EFUSE_FAULT_N"
        efuse_pins = {
            "1": raw, "2": raw, "5": raw,
            "6": local_net("Power Inputs", f"PD{idx}_EFUSE_UV"),
            "7": local_net("Power Inputs", f"PD{idx}_EFUSE_OV"), "8": "GND",
            "9": local_net("Power Inputs", f"PD{idx}_EFUSE_DVDT"),
            "10": local_net("Power Inputs", f"PD{idx}_EFUSE_ILIM"),
            "12": shdn, "14": fault, "15": "GND",
            "17": gated, "18": gated, "25": "GND",
        }
        expect_contains(comp(components, uref).value, "TPS26630RGER", f"{uref} PD eFuse")
        for pin, want in efuse_pins.items():
            expect(net(components, uref, pin), want, f"{uref} pin {pin}")
        for pin in ("3", "4", "11", "13", "16", "19", "20", "21", "22", "23", "24"):
            expect_unconnected(components, uref, pin)
        ebase = 800 + (idx - 1) * 10
        for ref, value, net_a, net_b in (
            (f"R{ebase}", "887k 0.1%", raw, local_net("Power Inputs", f"PD{idx}_EFUSE_UV")),
            (f"R{ebase + 1}", "27.4k 0.1%", local_net("Power Inputs", f"PD{idx}_EFUSE_UV"), local_net("Power Inputs", f"PD{idx}_EFUSE_OV")),
            (f"R{ebase + 2}", "68.1k 0.1%", local_net("Power Inputs", f"PD{idx}_EFUSE_OV"), "GND"),
            (f"R{ebase + 3}", "6.04k 1%", local_net("Power Inputs", f"PD{idx}_EFUSE_ILIM"), "GND"),
            (f"R{ebase + 4}", "47k", shdn, "GND"),
            (f"R{ebase + 5}", "10k", f"/PD{idx}_PATH_EN", shdn),
            (f"R{ebase + 6}", "10k", "/MCU_3V3", fault),
        ):
            expect_value_prefix(components, ref, value, f"{ref} PD eFuse network")
            expect(net(components, ref, "1"), net_a, f"{ref} pin 1")
            expect(net(components, ref, "2"), net_b, f"{ref} pin 2")

    for ref in ("C730", "C731", "C732", "C733", "C734", "C735", "C736"):
        expect(net(components, ref, "2"), "GND", f"{ref} LTC4417 capacitor return")
    expect_value_prefix(components, "C737", "100u 35V hybrid", "LTC4417 output hold-up")
    expect(net(components, "C737", "1"), "/USB_PD_SELECTED", "LTC4417 output hold-up rail")
    expect(net(components, "C737", "2"), "GND", "LTC4417 output hold-up return")
    expect(net(components, "C736", "1"), "/USB_PD_SELECTED", "selected-PD output capacitor")


def check_five_port_usb_c_architecture(components):
    """Assert the complete five-port data map and the two dual-role power paths."""
    pd_sheet = "Power Inputs"
    hub_sheet = "Native USB-C I/O"

    dual_role = (
        (1, "J21", "U41", 2000, {
            "dp": "/USBC1_DP", "dm": "/USBC1_DM",
            "sstx_p": "/USBC1_SSTX_P", "sstx_n": "/USBC1_SSTX_N",
            "ssrx_p": "/USBC1_SSRX_P", "ssrx_n": "/USBC1_SSRX_N",
        }),
        (2, "J11", "U42", 2010, {
            "dp": "/HUB_DS1_DP", "dm": "/HUB_DS1_DM",
            "sstx_p": "/HUB_DS1_SSTX_P", "sstx_n": "/HUB_DS1_SSTX_N",
            "ssrx_p": "/HUB_DS1_SSRX_P", "ssrx_n": "/HUB_DS1_SSRX_N",
        }),
    )

    # End-to-end host-TX contract for the Mu-native left charging/data port.
    # The Mu has no onboard TX coupling capacitors: C66/C67 are the one and
    # only 100 nF series pair between A1 and the TUSB1142 SSTX inputs.
    for mu_pin, capacitor, redriver_pin, raw_net, coupled_net in (
        ("13", "C66", "16", "/Mu Carrier/USBC1_SSTX_RAW_P", "/USBC1_SSTX_P"),
        ("15", "C67", "15", "/Mu Carrier/USBC1_SSTX_RAW_N", "/USBC1_SSTX_N"),
    ):
        expect(net(components, "A1", mu_pin), raw_net, f"Mu USB-C TX pin {mu_pin} raw side")
        expect_value_prefix(components, capacitor, "100n", f"{capacitor} Mu USB-C TX coupling")
        expect(net(components, capacitor, "1"), raw_net, f"{capacitor} Mu side")
        expect(net(components, capacitor, "2"), coupled_net, f"{capacitor} redriver side")
        expect(net(components, "U2000", redriver_pin), coupled_net,
               f"U2000 pin {redriver_pin} receives coupled Mu TX")

    for port, jref, tcpc, ubase, host in dual_role:
        raw = f"/PD{port}_VBUS_RAW"
        local = lambda name: local_net(pd_sheet, f"PD{port}_{name}")
        expect(comp(components, jref).footprint,
               "Connector_USB:USB_C_Receptacle_Molex_105450-0101", f"{jref} exact connector")
        expect(prop(components, jref, "MPN"), "105450-0101", f"{jref} exact MPN")
        for pin in ("A4", "A9", "B4", "B9"):
            expect(net(components, jref, pin), raw, f"{jref} dual-role VBUS {pin}")
        for pin, want in {
            "A5": local("CC1_CONN"), "B5": local("CC2_CONN"),
            "A6": local("DP_CONN"), "B6": local("DP_CONN"),
            "A7": local("DM_CONN"), "B7": local("DM_CONN"),
            "A2": local("TX1_P"), "A3": local("TX1_N"),
            "B2": local("TX2_P"), "B3": local("TX2_N"),
            "B11": local("RX1_P"), "B10": local("RX1_N"),
            "A11": local("RX2_P"), "A10": local("RX2_N"),
        }.items():
            expect(net(components, jref, pin), want, f"{jref} data pin {pin}")

        expect_contains(comp(components, tcpc).value, "TPS25751AD", f"{tcpc} DRP controller")
        expect(prop(components, tcpc, "MPN"), "TPS25751ADREFR", f"{tcpc} exact MPN")
        expect(prop(components, tcpc, "PortPolicy"),
               "DRP_PREFER_SINK;HOST_DATA_ONLY;15V_3A_SINK;5V_900MA_SOURCE;DEFAULT_RP",
               f"{tcpc} released port policy")
        expect(prop(components, tcpc, "EEPROMSource"),
               "firmware/tps25751a/ducktop2_dual_role_config.json",
               f"{tcpc} versioned EEPROM source")
        for pin in ("23", "32"):
            expect(net(components, tcpc, pin), raw, f"{tcpc} raw VBUS pin {pin}")
        for pin in ("20",):
            expect(net(components, tcpc, pin), local("PPHV"), f"{tcpc} protected PPHV pin {pin}")
        expect(net(components, tcpc, "34"), "/USB_PORT_5V", f"{tcpc} source PP5V land")
        expect(net(components, tcpc, "28"), local("CC1_SYS"), f"{tcpc} CC1")
        expect(net(components, tcpc, "29"), local("CC2_SYS"), f"{tcpc} CC2")
        expect(net(components, tcpc, "26"), local("GPIO_DFP"), f"{tcpc} DFP-role output")
        expect(net(components, tcpc, "36"), local("GPIO_ATTACH"), f"{tcpc} attach output")
        expect(net(components, tcpc, "37"), local("GPIO_FLIP"), f"{tcpc} orientation output")

        qualifier = f"U{ubase + 6}"
        expect_contains(comp(components, qualifier).value, "SN74LVC1G08",
                        f"{qualifier} DFP-and-attach qualifier")
        expect(prop(components, qualifier, "MPN"), "SN74LVC1G08DBVR",
               f"{qualifier} exact MPN")
        for pin, want in {
            "1": local("GPIO_DFP"), "2": local("GPIO_ATTACH"),
            "3": "GND", "4": local("HOST_ATTACHED"), "5": "/SYS_3V3",
        }.items():
            expect(net(components, qualifier, pin), want, f"{qualifier} pin {pin}")
        expect(prop(components, qualifier, "DefaultState"),
               "LOW_WHEN_CONTROLLER_UNPOWERED_RESET_DETACHED_OR_SINK",
               f"{qualifier} fail-off contract")
        expect_value_prefix(components, f"R{2000 + (port - 1) * 40 + 14}", "100k",
                            f"PD{port} attach input default-low")
        expect_value_prefix(components, f"R{2000 + (port - 1) * 40 + 18}", "100k",
                            f"PD{port} DFP input default-low")

        protector = f"U{ubase + 1}"
        expect_contains(comp(components, protector).value, "TPD4S201", f"{protector} CC/USB2 protector")
        expect(prop(components, protector, "ChannelUse"),
               "CC1_CC2_AND_USB2_DP_DM;DEAD_BATTERY_RD_ENABLED",
               f"{protector} protected-channel contract")
        expect(net(components, protector, "14"), local("DM_HOST_SWITCHED"), f"{protector} USB2 D-")
        expect(net(components, protector, "15"), local("DP_HOST_SWITCHED"), f"{protector} USB2 D+")

        usb2_switch = f"U{ubase + 3}"
        expect_contains(comp(components, usb2_switch).value, "TS3USB30E", f"{usb2_switch} USB2 disconnect")
        expect(prop(components, usb2_switch, "DataRoleContract"),
               "DEFAULT_DISCONNECTED;ENABLE_ONLY_AFTER_CONFIRMED_DFP",
               f"{usb2_switch} fail-safe data role")
        expect(net(components, usb2_switch, "2"), host["dp"], f"{usb2_switch} host D+")
        expect(net(components, usb2_switch, "8"), host["dm"], f"{usb2_switch} host D-")
        expect(net(components, usb2_switch, "9"), local("USB2_OE_N"), f"{usb2_switch} default-off enable")
        expect_value_prefix(components, f"R{2000 + (port - 1) * 40 + 16}", "100k",
                            f"PD{port} USB2 default-disable pull-up")

        mux_control = f"U{ubase + 4}"
        expect(net(components, mux_control, "3"), local("HOST_ATTACHED"),
               f"{mux_control} qualified role/attach input")
        expect(net(components, mux_control, "4"), local("MUX_EN"),
               f"{mux_control} SuperSpeed enable output")

        redriver = f"U{ubase}"
        expect_contains(comp(components, redriver).value, "TUSB1142", f"{redriver} Gen2 redriver")
        expect(prop(components, redriver, "MPN"), "TUSB1142IRNQR", f"{redriver} exact MPN")
        expect(prop(components, redriver, "StrapMode"),
               "GPIO_MODE;FULL_AEQ;4P5DB_HOST_EQ;VIO_3V3", f"{redriver} strap policy")
        expect(net(components, redriver, "15"), host["sstx_n"], f"{redriver} host TX-")
        expect(net(components, redriver, "16"), host["sstx_p"], f"{redriver} host TX+")
        expect(net(components, redriver, "18"), local("SSRX_RAW_N"), f"{redriver} host RX-")
        expect(net(components, redriver, "19"), local("SSRX_RAW_P"), f"{redriver} host RX+")
        expect(net(components, redriver, "21"), local("MUX_FLIP"), f"{redriver} orientation")
        expect(net(components, redriver, "26"), local("MUX_EN"), f"{redriver} role enable")

        eeprom = f"U{ubase + 2}"
        expect_contains(comp(components, eeprom).value, "CAT24C256", f"{eeprom} TCPC EEPROM")
        expect(prop(components, eeprom, "ProgrammingState"),
               "PROGRAM_BEFORE_ASSEMBLY_OR_VIA_TP;READBACK_VERIFY_RELEASE_IMAGE",
               f"{eeprom} release-image contract")
        efuse = f"U{719 + port}"
        expect_contains(comp(components, efuse).value, "TPS26630", f"{efuse} sink eFuse")
        expect(prop(components, efuse, "SafetyState"),
               "MODE_GND_AUTORETRY;PGTH_GND_PGOOD_UNUSED;SHDN_47K_PULLDOWN",
               f"{efuse} default-off safety state")
        expect(net(components, efuse, "12"), local("EFUSE_SHDN"), f"{efuse} shutdown")
        expect_value_prefix(components, f"R{2084 + (port - 1) * 10}", "47k",
                            f"PD{port} eFuse default-off pull-down")
        expect_value_prefix(components, f"C{2000 + (port - 1) * 40 + 15}", "4.7u 25V",
                            f"{jref} pre-attach capacitance")

    expect_contains(comp(components, "U14").value, "LTC4418", "two-input PD selector")
    expect(net(components, "U14", "15"), "/USB_PD_SELECTED", "selected PD output")
    expect(net(components, "U14", "17"), local_net(pd_sheet, "PD1_VBUS_GATED"), "PD1 selector input")
    expect(net(components, "U14", "16"), local_net(pd_sheet, "PD2_VBUS_GATED"), "PD2 selector input")
    for component in components.values():
        if "CH224" in component.value:
            fail(f"obsolete CH224 power-only controller remains: {component.ref}")

    expect_contains(comp(components, "U1700").value, "USB7206C", "six-port Gen2 hub")
    expect(prop(components, "U1700", "MPN"), "USB7206C-I/KDX", "hub exact MPN")
    for pin, want in {
        "2": "/INTERNAL_USB_VBUS_VALID",
        "89": "/USBC2_DP", "90": "/USBC2_DM",
        "94": "/USBC2_SSTX_P", "95": "/USBC2_SSTX_N",
        "5": "/HUB_DS1_DP", "6": "/HUB_DS1_DM",
        "10": "/HUB_DS1_SSRX_P", "11": "/HUB_DS1_SSRX_N",
    }.items():
        expect(net(components, "U1700", pin), want, f"USB7206C pin {pin}")
    disable_straps = {
        "41": ("R1733", "HUB_DIS6_DM"),
        "42": ("R1732", "HUB_DIS6_DP"),
        "81": ("R1730", "HUB_DIS5_DP"),
        "82": ("R1731", "HUB_DIS5_DM"),
    }
    for pin, (ref, local_name) in disable_straps.items():
        strap_net = local_net(hub_sheet, local_name)
        expect(net(components, "U1700", pin), strap_net,
               f"USB7206C unused port-disable strap pin {pin}")
        expect_value_prefix(components, ref, "0R", f"{ref} unused-port disable link")
        expect(net(components, ref, "1"), "/SYS_3V3", f"{ref} strap source")
        expect(net(components, ref, "2"), strap_net, f"{ref} strap destination")
        expect(prop(components, ref, "MPN"), "RC0603JR-070RL", f"{ref} exact strap MPN")

    source_ports = (("J22", 2, 1780), ("J23", 3, 1740), ("J12", 4, 1760))
    for jref, port, base in source_ports:
        local = lambda name: local_net(hub_sheet, name)
        expect(comp(components, jref).footprint,
               "Connector_USB:USB_C_Receptacle_Molex_105450-0101", f"{jref} exact connector")
        expect_contains(comp(components, f"U{base + 1}").value, "TPS25810", f"{jref} DFP controller")
        expect_contains(comp(components, f"U{base + 2}").value, "HD3SS6126", f"{jref} orientation mux")
        expect(net(components, f"U{base + 2}", "6"), "GND",
               f"{jref} HD3SS6126 HS_OE low for normal USB3 operation")
        expect(prop(components, f"U{base + 2}", "EnableState"),
               "HS_OE_GND_NORMAL_OPERATION", f"{jref} mux enable contract")
        expect_contains(comp(components, f"U{base + 3}").value, "TPD1S514", f"{jref} VBUS OVP")
        expect(net(components, f"U{base + 3}", "B3"), local(f"J{jref[1:]}_VBUS"),
               f"{jref} protected connector VBUS")
        for pin in ("A4", "A9", "B4", "B9"):
            expect(net(components, jref, pin), local(f"J{jref[1:]}_VBUS"), f"{jref} VBUS {pin}")
        for pin, want in {
            "A6": local(f"HUB_DS{port}_DP"), "B6": local(f"HUB_DS{port}_DP"),
            "A7": local(f"HUB_DS{port}_DM"), "B7": local(f"HUB_DS{port}_DM"),
            "A2": local(f"J{jref[1:]}_TX1_P"), "A3": local(f"J{jref[1:]}_TX1_N"),
            "B2": local(f"J{jref[1:]}_TX2_P"), "B3": local(f"J{jref[1:]}_TX2_N"),
            "B11": local(f"J{jref[1:]}_RX1_P"), "B10": local(f"J{jref[1:]}_RX1_N"),
            "A11": local(f"J{jref[1:]}_RX2_P"), "A10": local(f"J{jref[1:]}_RX2_N"),
        }.items():
            expect(net(components, jref, pin), want, f"{jref} data pin {pin}")

    external_ports = {"J11", "J12", "J21", "J22", "J23"}
    found_ports = {
        ref for ref, item in components.items()
        if item.value.startswith("USB-C ") and ref in external_ports
    }
    expect(",".join(sorted(found_ports)), ",".join(sorted(external_ports)),
           "complete five-port external USB-C set")


def check_external_hdmi_path(components):
    sheet = "TCP0 External HDMI"
    for pin, want in {
        "1": "EXT_HDMI_D2_P", "3": "EXT_HDMI_D2_N", "4": "EXT_HDMI_D1_P", "6": "EXT_HDMI_D1_N",
        "7": "EXT_HDMI_D0_P", "9": "EXT_HDMI_D0_N", "10": "EXT_HDMI_CK_P", "12": "EXT_HDMI_CK_N",
        "15": "EXT_HDMI_SCL_CONN", "16": "EXT_HDMI_SDA_CONN",
        "18": "EXT_HDMI_5V", "19": "EXT_HDMI_HPD_CONN",
    }.items():
        expect(net(components, "J30", pin), local_net(sheet, want), f"J30 HDMI pin {pin}")
    for pin in ("2", "5", "8", "11", "17", "SH"):
        expect(net(components, "J30", pin), "GND", f"J30 HDMI ground {pin}")
    expect_unconnected(components, "J30", "13")
    expect_unconnected(components, "J30", "14")
    for src, conn, cref, rref, dref in [
        ("/TCP0_TX0_P", "EXT_HDMI_D2_P", "C150", "R150", "D150"),
        ("/TCP0_TX0_N", "EXT_HDMI_D2_N", "C151", "R151", "D151"),
        ("/TCP0_TXRX0_P", "EXT_HDMI_D1_P", "C152", "R152", "D152"),
        ("/TCP0_TXRX0_N", "EXT_HDMI_D1_N", "C153", "R153", "D153"),
        ("/TCP0_TX1_P", "EXT_HDMI_D0_P", "C154", "R154", "D154"),
        ("/TCP0_TX1_N", "EXT_HDMI_D0_N", "C155", "R155", "D155"),
        ("/TCP0_TXRX1_P", "EXT_HDMI_CK_P", "C156", "R156", "D156"),
        ("/TCP0_TXRX1_N", "EXT_HDMI_CK_N", "C157", "R157", "D157"),
    ]:
        expect(net(components, cref, "1"), src, f"{cref} HDMI source side")
        expect(net(components, cref, "2"), local_net(sheet, conn), f"{cref} HDMI connector side")
        expect(net(components, rref, "1"), local_net(sheet, conn), f"{rref} HDMI bias signal")
        expect(net(components, rref, "2"), local_net(sheet, "EXT_HDMI_BIAS_RETURN"), f"{rref} gated HDMI bias return")
        expect_contains(comp(components, dref).value, "TPD1E0B04DPLR",
                        f"{dref} low-capacitance HDMI ESD")
        expect(prop(components, dref, "MPN"), "TPD1E0B04DPLR",
               f"{dref} exact HDMI ESD MPN")
        expect(comp(components, dref).footprint,
               "Diode_SMD:D_0201_0603Metric",
               f"{dref} 0.6x0.3mm DPL land pattern")
        expect(net(components, dref, "1"), local_net(sheet, conn), f"{dref} TMDS shunt")
        expect(net(components, dref, "2"), "GND", f"{dref} ESD return")
    for pin, want in {
        "1": "EXT_HDMI_SCL_CONN", "2": "EXT_HDMI_SDA_CONN", "3": "EXT_HDMI_HPD_CONN",
        "5": "HDMI_SOURCE_5V", "6": "EXT_HDMI_5V", "8": "GND",
    }.items():
        expected = want if want.startswith("/") or want == "GND" else local_net(sheet, want)
        expect(net(components, "U50", pin), expected, f"TPD13S523 pin {pin}")
    unused_pins = ("4", "7", "9", "10", "11", "12", "13", "14", "15", "16")
    for index, pin in enumerate(unused_pins):
        unused = local_net(sheet, f"HDMI_TPD_D{index}_UNUSED")
        ref = f"R{570 + index}"
        expect(net(components, "U50", pin), unused, f"TPD13S523 unused channel pin {pin}")
        expect_value_prefix(components, ref, "75R 1%", f"{ref} unused HDMI termination")
        expect(net(components, ref, "1"), unused, f"{ref} unused HDMI channel")
        expect(net(components, ref, "2"), "GND", f"{ref} unused HDMI termination return")
    for ref, value, rail in (
        ("C158", "1u", local_net(sheet, "HDMI_SOURCE_5V")),
        ("C162", "100n", local_net(sheet, "HDMI_SOURCE_5V")),
        ("C159", "1u", local_net(sheet, "EXT_HDMI_5V")),
        ("C163", "100n", local_net(sheet, "EXT_HDMI_5V")),
    ):
        expect_value_prefix(components, ref, value, f"{ref} HDMI switch bypass")
        expect(net(components, ref, "1"), rail, f"{ref} HDMI switch bypass rail")
        expect(net(components, ref, "2"), "GND", f"{ref} HDMI switch bypass return")
    expect(net(components, "R165", "1"), "/MU_HOST_ACTIVE", "HDMI bias qualified host-active source")

    for ref, source, output, ct, cap, bleed in (
        ("U54", "/SYS_5V", "HDMI_SOURCE_5V", "HDMI_5V_SWITCH_CT", "C164", "R168"),
        ("U55", "/SYS_3V3", "HDMI_HOST_3V3", "HDMI_3V3_SWITCH_CT", "C165", "R169"),
    ):
        for pin, want in {
            "1": source, "2": source, "3": "/MU_HOST_ACTIVE", "4": source,
            "5": "GND", "6": local_net(sheet, ct),
            "7": local_net(sheet, output), "8": local_net(sheet, output), "9": "GND",
        }.items():
            expect(net(components, ref, pin), want, f"{ref} host-active rail switch pin {pin}")
        expect(prop(components, ref, "MPN"), "TPS22975NDSGR", f"{ref} exact load-switch MPN")
        expect(
            prop(components, ref, "PowerOffContract"),
            "OUTPUT_OFF_WHEN_MU_HOST_ACTIVE_LOW; NO_REVERSE_BLOCK_GUARANTEE",
            f"{ref} power-off contract must not claim unsupported reverse blocking",
        )
        expect(comp(components, ref).footprint,
               "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
               f"{ref} exact TPS22975N footprint")
        expect_value_prefix(components, cap, "4.7n", f"{cap} load-switch rise-time capacitor")
        expect(net(components, cap, "1"), local_net(sheet, ct), f"{cap} CT node")
        expect(net(components, cap, "2"), "GND", f"{cap} CT return")
        expect_value_prefix(components, bleed, "100k", f"{bleed} switched-rail discharge")
        expect(net(components, bleed, "1"), local_net(sheet, output), f"{bleed} switched rail")
        expect(net(components, bleed, "2"), "GND", f"{bleed} discharge return")

    for pin, want in {
        "1": "GND", "2": "HDMI_HOST_3V3", "3": "/TCP0_DDC_SCL", "4": "/TCP0_DDC_SDA",
        "5": "EXT_HDMI_SDA_CONN", "6": "EXT_HDMI_SCL_CONN", "7": "HDMI_DDC_REF5", "8": "HDMI_DDC_REF5",
    }.items():
        expected = want if want.startswith("/") or want == "GND" else local_net(sheet, want)
        expect(net(components, "U51", pin), expected, f"PCA9306 pin {pin}")
    expect_value_prefix(components, "R158", "2.2k", "HDMI low-side SCL pull-up")
    expect_value_prefix(components, "R159", "2.2k", "HDMI low-side SDA pull-up")
    expect_value_prefix(components, "R160", "1.8k", "HDMI connector-side SCL pull-up")
    expect_value_prefix(components, "R161", "1.8k", "HDMI connector-side SDA pull-up")
    for ref in ("R158", "R159"):
        expect(prop(components, ref, "MPN"), "RC0402FR-072K2L", f"{ref} 2.2k procurement MPN")
    for ref in ("R160", "R161"):
        expect(prop(components, ref, "MPN"), "RC0402FR-071K8L", f"{ref} 1.8k procurement MPN")
    expect_value_prefix(components, "R162", "200k", "PCA9306 VREF2/EN bias")
    expect_value_prefix(components, "C160", "100p", "PCA9306 VREF2/EN filter")

    expect_unconnected(components, "U53", "1")
    expect(net(components, "U53", "2"), local_net(sheet, "EXT_HDMI_HPD_NODE"), "HPD buffer input")
    expect(net(components, "U53", "3"), "GND", "HPD buffer ground")
    expect(net(components, "U53", "4"), "/TCP0_HPD", "HPD buffer Mu output")
    expect(net(components, "U53", "5"), local_net(sheet, "HDMI_HOST_3V3"), "HPD buffer switched supply")
    expect(net(components, "R163", "1"), local_net(sheet, "EXT_HDMI_HPD_CONN"), "HPD input series connector side")
    expect(net(components, "R163", "2"), local_net(sheet, "EXT_HDMI_HPD_NODE"), "HPD input series buffer side")
    expect(net(components, "R164", "1"), local_net(sheet, "EXT_HDMI_HPD_NODE"), "HPD pull-down input")
    for obsolete in ("D158", "F150", "Q51", "Q52", "Q53", "U52"):
        if obsolete in components:
            fail(f"obsolete provisional HDMI component {obsolete} is still in the schematic")


def check_internal_services(components):
    sheet = "Internal Services"
    expect(net(components, "R200", "1"), local_net(sheet, "EC_USB_ISO_DP"), "EC USB DP isolated side")
    expect(net(components, "R200", "2"), "/MCU_USB_DP", "EC USB DP MCU side")
    expect(net(components, "R201", "1"), local_net(sheet, "EC_USB_ISO_DM"), "EC USB DM isolated side")
    expect(net(components, "R201", "2"), "/MCU_USB_DM", "EC USB DM MCU side")
    expect(comp(components, "U61").footprint, "Package_SO:TSSOP-10_3x3mm_P0.5mm", "EC USB isolation switch footprint")
    for pin, want in {
        "1": "GND", "2": "/EC_HOST_USB_DP", "4": local_net(sheet, "EC_USB_ISO_DP"),
        "5": "GND", "6": local_net(sheet, "EC_USB_ISO_DM"), "8": "/EC_HOST_USB_DM",
        "9": local_net(sheet, "EC_USB_OE_N"), "10": "/MCU_3V3",
    }.items():
        expect(net(components, "U61", pin), want, f"EC USB isolation U61 pin {pin}")
    for pin in ("3", "7"):
        expect_unconnected(components, "U61", pin)
    expect(net(components, "Q60", "1"), "/INTERNAL_USB_VBUS_VALID", "EC USB physical VBUS-valid interlock gate")
    expect(net(components, "Q60", "2"), "GND", "EC USB interlock return")
    expect(net(components, "Q60", "3"), local_net(sheet, "EC_USB_OE_N"), "EC USB interlock drain")
    expect(net(components, "R202", "1"), "/MCU_3V3", "EC USB default-disconnect rail")
    expect(net(components, "R202", "2"), local_net(sheet, "EC_USB_OE_N"), "EC USB default-disconnect control")
    for obsolete in ("Q61", "R203"):
        if obsolete in components:
            fail(f"obsolete status-proxy EC USB component {obsolete} remains")
    expect(net(components, "R250", "1"), "/TRACKPAD_USB_DP", "trackpad USB DP Mu side")
    expect(net(components, "R250", "2"), local_net(sheet, "TPAD_CONN_DP"), "trackpad USB DP connector side")
    expect(net(components, "R251", "1"), "/TRACKPAD_USB_DM", "trackpad USB DM Mu side")
    expect(net(components, "R251", "2"), local_net(sheet, "TPAD_CONN_DM"), "trackpad USB DM connector side")
    for obsolete in ("F201", "R253", "R255", "J57"):
        if obsolete in components:
            fail(f"obsolete passive/fallback trackpad part {obsolete} is still present")
    tps_trackpad = {
        "2": local_net(sheet, "TPAD_5V_PRE"), "3": local_net(sheet, "TPAD_5V_PRE"),
        "4": local_net(sheet, "TPAD_5V_PRE"), "5": "/SYS_3V3",
        "6": "/MU_HOST_ACTIVE", "7": "GND", "8": "GND",
        "9": local_net(sheet, "TPAD_REF_RTN"), "10": local_net(sheet, "TPAD_REF"),
        "11": local_net(sheet, "TPAD_CC1"), "12": "GND", "13": local_net(sheet, "TPAD_CC2"),
        "14": local_net(sheet, "TPAD_5V"), "15": local_net(sheet, "TPAD_5V"), "21": "GND",
    }
    expect_value_prefix(components, "U63", "TPS25810", "trackpad attach-controlled source")
    expect(prop(components, "U63", "MPN"), "TPS25810RVCR", "trackpad source-controller MPN")
    for pin, want in tps_trackpad.items():
        expect(net(components, "U63", pin), want, f"trackpad TPS25810 pin {pin}")
    expect(net(components, "U63", "1"), "/TRACKPAD_FAULT_N", "trackpad TPS25810 active-low fault")
    for pin in ("16", "17", "18", "19", "20"):
        expect_unconnected(components, "U63", pin)
    expect_contains(comp(components, "U64").value, "TPS2553D", "trackpad branch switch")
    for pin, want in {
        "1": "/SYS_5V", "2": "GND", "3": "/MU_HOST_ACTIVE",
        "4": "/TRACKPAD_FAULT_N", "5": local_net(sheet, "TPAD_ILIM"),
        "6": local_net(sheet, "TPAD_5V_PRE"),
    }.items():
        expect(net(components, "U64", pin), want, f"trackpad branch switch pin {pin}")
    expect_value_prefix(components, "R252", "43.2k 1%", "trackpad branch ILIM resistor")
    expect(net(components, "R252", "1"), local_net(sheet, "TPAD_ILIM"), "trackpad ILIM node")
    expect(net(components, "R252", "2"), "GND", "trackpad ILIM return")
    expect_value_prefix(components, "R256", "10k", "trackpad fault pull-up")
    expect(net(components, "R256", "1"), "/MCU_3V3", "trackpad fault pull-up rail")
    expect(net(components, "R256", "2"), "/TRACKPAD_FAULT_N", "trackpad fault signal")
    expect_value_prefix(components, "R254", "100k 1%", "trackpad TPS25810 REF resistor")
    expect(net(components, "R254", "1"), local_net(sheet, "TPAD_REF"), "trackpad REF resistor top")
    expect(net(components, "R254", "2"), local_net(sheet, "TPAD_REF_RTN"), "trackpad REF resistor return")
    for ref, value, rail in (
        ("C280", "100n", "/SYS_5V"),
        ("C281", "100n", local_net(sheet, "TPAD_5V_PRE")),
        ("C282", "100n", "/SYS_3V3"), ("C283", "10u", local_net(sheet, "TPAD_5V")),
        ("C284", "150u", local_net(sheet, "TPAD_5V_PRE")),
    ):
        expect_value_prefix(components, ref, value, f"{ref} trackpad source capacitance")
        expect(net(components, ref, "1"), rail, f"{ref} trackpad source rail")
        expect(net(components, ref, "2"), "GND", f"{ref} trackpad source return")
    for pin, want in {
        "1": local_net(sheet, "TPAD_CONN_DP"), "2": local_net(sheet, "TPAD_CONN_DM"),
        "3": "GND", "4": local_net(sheet, "TPAD_CC1"),
        "5": local_net(sheet, "TPAD_CC2"), "8": "GND",
    }.items():
        expect(net(components, "U62", pin), want, f"trackpad USB2/CC ESD pin {pin}")
    for pin in ("6", "7", "9", "10"):
        expect_unconnected(components, "U62", pin)
    for pin in ("A4", "A9", "B4", "B9"):
        expect(net(components, "J58", pin), local_net(sheet, "TPAD_5V"), f"trackpad USB-C VBUS {pin}")
    expect(net(components, "J52", "1"), "GND", "fan connector ground")
    expect(net(components, "J52", "2"), local_net(sheet, "FAN_12V"), "fan connector fused 12V")
    expect(net(components, "J52", "3"), "/FAN_TACH", "fan tach")
    expect(net(components, "J52", "4"), local_net(sheet, "FAN_PWM_CONN"), "fan PWM")
    expect(comp(components, "J52").footprint,
           "Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal",
           "fan connector low-profile keyed footprint")
    expect(prop(components, "J52", "MPN"), "SM04B-GHS-TB", "fan connector exact MPN")
    expect(prop(components, "J52", "EndpointMPN"), "BFB04512HHA-CZ0T", "released fan exact MPN")
    expect(prop(components, "J52", "EndpointWireMap"),
           "1=BLACK/GND;2=RED/+12V;3=WHITE/FG;4=YELLOW/PWM", "released fan wire map")
    expect(prop(components, "J52", "EndpointElectricalContract"),
           "12V_NOMINAL_5.0_TO_13.5V;0.26A_MAX;25KHZ_OPEN_DRAIN_PWM;FLOAT_PWM_FULL_SPEED;FG_OPEN_COLLECTOR_2PPR",
           "released fan electrical contract")
    expect(prop(components, "F200", "MPN"), "1206L075/16WR", "fan PTC exact MPN")
    expect(net(components, "F200", "1"), "/MU_12V", "fan PTC regulated input")
    expect(net(components, "F200", "2"), local_net(sheet, "FAN_12V"), "fan PTC protected output")
    for ref, value, rail, mpn in (
        ("C205", "10u 25V X7R", local_net(sheet, "FAN_12V"), "GRM31CR71E106KA12L"),
        ("C206", "100n 25V X7R", local_net(sheet, "FAN_12V"), "GRM188R71E104KA01D"),
        ("C209", "3.9n", "/FAN_TACH", "GRM1555C1H392JA01D"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} fan interface value")
        expect(net(components, ref, "1"), rail, f"{ref} fan interface signal")
        expect(net(components, ref, "2"), "GND", f"{ref} fan interface return")
        expect(prop(components, ref, "MPN"), mpn, f"{ref} fan interface exact MPN")
    expect_value_prefix(components, "R206", "8.2k", "fan FG pull-up")
    expect(net(components, "R206", "1"), "/MCU_3V3", "fan FG pull-up rail")
    expect(net(components, "R206", "2"), "/FAN_TACH", "fan FG pull-up signal")
    expect(prop(components, "R206", "MPN"), "RC0603FR-078K2L", "fan FG pull-up exact MPN")
    expect_value_prefix(components, "R207", "100R", "fan PWM gate resistor")
    expect(net(components, "R207", "1"), "/FAN_PWM", "fan PWM source")
    expect(net(components, "R207", "2"), local_net(sheet, "FAN_PWM_GATE"), "fan PWM gate")
    expect(prop(components, "R207", "MPN"), "RC0603FR-07100RL", "fan PWM gate resistor exact MPN")
    expect_value_prefix(components, "R208", "100k", "fan PWM gate pull-down")
    expect(net(components, "R208", "1"), local_net(sheet, "FAN_PWM_GATE"), "fan PWM default gate state")
    expect(net(components, "R208", "2"), "GND", "fan PWM gate pull-down return")
    expect(prop(components, "R208", "MPN"), "RC0603FR-07100KL", "fan PWM gate pull-down exact MPN")
    expect("R216" not in components, True, "obsolete external fan-PWM pull-up is absent")
    for ref in ("J53", "J54", "J56"):
        expect(comp(components, ref).footprint,
               "Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal",
               f"{ref} low-profile keyed service footprint")
        expect(prop(components, ref, "MPN"), "SM02B-GHS-TB", f"{ref} exact MPN")
        expect(prop(components, ref, "MatingHousing"), "GHR-02V-S", f"{ref} mating housing")
    expect(net(components, "Q200", "1"), local_net(sheet, "FAN_PWM_GATE"), "fan FET gate")
    expect(net(components, "Q200", "2"), "GND", "fan FET source")
    expect(net(components, "Q200", "3"), local_net(sheet, "FAN_PWM_CONN"), "fan FET drain/open-drain PWM")
    expect(prop(components, "Q200", "MPN"), "2N7002KT1G", "fan PWM transistor MPN")


def check_keyboard_interface(components):
    sheet = "Keyboard Mainboard FFC"
    expect(comp(components, "J310").footprint, "Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal", "J310 footprint")
    for pin in ("1", "30", "MP"):
        expect(net(components, "J310", pin), "GND", f"keyboard FFC ground {pin}")
    expect(net(components, "J310", "2"), local_net(sheet, "KB_FFC_5V"), "keyboard FFC reversed 5V pin")
    expect(net(components, "J310", "29"), local_net(sheet, "KB_FFC_3V3"), "keyboard FFC reversed 3V3 pin")
    expect(net(components, "J310", "27"), local_net(sheet, "KB_FFC_I2C_SDA"), "keyboard FFC reversed I2C SDA")
    expect(net(components, "J310", "28"), local_net(sheet, "KB_FFC_I2C_SCL"), "keyboard FFC reversed I2C SCL")
    expect(net(components, "J310", "3"), local_net(sheet, "KB_FFC_RGB_DATA"),
           "keyboard FFC RGB data uses rev-A spare COL15 conductor")
    for pin, col in zip(range(4, 19), range(14, -1, -1)):
        expect(net(components, "J310", str(pin)), local_net(sheet, f"KB_FFC_COL{col}"),
               f"keyboard FFC reversed column {col}")
    for pin, row in zip(range(19, 27), range(7, -1, -1)):
        expect(net(components, "J310", str(pin)), local_net(sheet, f"KB_FFC_ROW{row}"),
               f"keyboard FFC reversed row {row}")

    for index in range(15):
        ref = f"R{360 + index}"
        expect(net(components, ref, "1"), f"/KB_COL{index}", f"{ref} EC column side")
        expect(net(components, ref, "2"), local_net(sheet, f"KB_FFC_COL{index}"), f"{ref} FFC column side")
        expect_value_prefix(components, ref, "1k", f"{ref} keyboard matrix series value")
    expect(net(components, "R375", "1"), local_net(sheet, "KB_RGB_DATA_5V"), "R375 RGB buffer side")
    expect(net(components, "R375", "2"), local_net(sheet, "KB_FFC_RGB_DATA"), "R375 RGB FFC side")
    expect_value_prefix(components, "R375", "100R", "R375 keyboard RGB data series value")
    for index in range(8):
        ref = f"R{376 + index}"
        expect(net(components, ref, "1"), f"/KB_ROW{index}", f"{ref} EC row side")
        expect(net(components, ref, "2"), local_net(sheet, f"KB_FFC_ROW{index}"), f"{ref} FFC row side")
        expect_value_prefix(components, ref, "1k", f"{ref} keyboard matrix series value")
    for ref, upstream, downstream in (
        ("R384", "/I2C_SCL", "KB_FFC_I2C_SCL"),
        ("R385", "/I2C_SDA", "KB_FFC_I2C_SDA"),
    ):
        expect(net(components, ref, "1"), upstream, f"{ref} upstream I2C")
        expect(net(components, ref, "2"), local_net(sheet, downstream), f"{ref} FFC I2C")
        expect_value_prefix(components, ref, "100R", f"{ref} I2C series value")
    for ref, upstream, downstream in (
        ("R386", "/SYS_5V", "KB_FFC_5V"),
        ("R387", "/MCU_3V3", "KB_FFC_3V3"),
    ):
        expect(net(components, ref, "1"), upstream, f"{ref} optional rail source")
        expect(net(components, ref, "2"), local_net(sheet, downstream), f"{ref} optional FFC rail")
    for pin, want in {
        "1": "/SYS_5V", "2": "GND", "3": "/KB_RGB_PWR_EN",
        "4": "/KB_RGB_FAULT_N", "5": local_net(sheet, "KB_RGB_ILIM"),
        "6": local_net(sheet, "KB_FFC_5V"),
    }.items():
        expect(net(components, "U310", pin), want, f"keyboard RGB power switch pin {pin}")
    expect_contains(comp(components, "U310").value, "TPS2553D", "keyboard RGB power switch exact family")
    expect_value_prefix(components, "R388", "66.5k 1%", "keyboard RGB current limit")
    expect_value_prefix(components, "R389", "100k", "keyboard RGB enable fail-off pull-down")
    expect_value_prefix(components, "R390", "10k", "keyboard RGB fault pull-up")
    for pin, want in {
        "1": "/KB_RGB_PWR_EN", "2": "/KB_RGB_DATA_3V3", "3": "GND",
        "4": local_net(sheet, "KB_RGB_DATA_5V"), "5": "/SYS_5V",
    }.items():
        expect(net(components, "U311", pin), want, f"keyboard RGB AHCT buffer pin {pin}")
    expect_contains(comp(components, "U311").value, "SN74AHCT1G126", "keyboard RGB level buffer exact part")
    expect_value_prefix(components, "C319", "10u", "keyboard RGB switched-output bulk")
    dnp, exclude_bom = component_flags()
    for ref in ("R386", "R387", "C318"):
        if ref not in dnp or ref not in exclude_bom:
            fail(f"{ref} keyboard option must remain DNP and excluded from BOM")
    if "C319" in dnp or "C319" in exclude_bom:
        fail("C319 keyboard RGB output bulk must be populated")


def _check_legacy_monolithic_radio_gnss_audio(components):
    expect(net(components, "F10", "1"), "/PCIE_3V3",
           "E-key fuse uses the S0-switched PCIe endpoint rail")
    expect(net(components, "F10", "2"), local_net("Radio/OLED/GNSS", "WIFI_3V3"),
           "E-key fused local rail")
    expect(prop(components, "F10", "MPN"), "1206L200PR", "E-key PTC exact MPN")
    expect(prop(components, "J40", "QualifiedModuleMPN"), "AX210.NGWGIE.NV",
           "E-key qualified module exact ordering code")
    expect(prop(components, "J40", "QualifiedModuleContract"),
           "M2_2230_KEY_E_PCIE_WIFI_USB_BLUETOOTH_NOT_CNVIO2",
           "E-key module electrical contract")
    for ref, signal in (("R170", "WIFI_W_DISABLE1_N"),
                        ("R171", "WIFI_W_DISABLE2_N")):
        expect_value_prefix(components, ref, "10k", f"{ref} E-key disable pull-up")
        expect(net(components, ref, "1"), local_net("Radio/OLED/GNSS", "WIFI_3V3"),
               f"{ref} cannot back-power an unpowered E-key slot")
        expect(net(components, ref, "2"), local_net("Radio/OLED/GNSS", signal),
               f"{ref} E-key module-side disable signal")
    for pin, want in {
        "1": "/WIFI_W_DISABLE1_N_EC", "7": local_net("Radio/OLED/GNSS", "WIFI_W_DISABLE1_N"),
        "6": "/WIFI_W_DISABLE2_N_EC", "2": local_net("Radio/OLED/GNSS", "WIFI_W_DISABLE2_N"),
        "3": "GND", "4": "GND", "8": local_net("Radio/OLED/GNSS", "WIFI_3V3"),
    }.items():
        expect(net(components, "U170", pin), want, f"E-key control-isolator pin {pin}")
    expect_unconnected(components, "U170", "5")
    expect(prop(components, "U170", "MPN"), "SN74LVC3G34DCUR",
           "E-key control isolator exact MPN")
    for ref, signal in (("R198", "/WIFI_W_DISABLE1_N_EC"),
                        ("R199", "/WIFI_W_DISABLE2_N_EC")):
        expect_value_prefix(components, ref, "100k", f"{ref} E-key reset default")
        expect(net(components, ref, "1"), signal, f"{ref} EC-side disable signal")
        expect(net(components, ref, "2"), "GND", f"{ref} fail-disable return")
    expect(net(components, "C187", "1"), local_net("Radio/OLED/GNSS", "WIFI_3V3"),
           "E-key isolator bypass rail")
    expect(net(components, "C187", "2"), "GND", "E-key isolator bypass return")

    for pin, want in {
        "1": "GND", "2": "/Ham Radio/RADIO_BUCK_SW", "3": "/SYS_5V",
        "4": "/Ham Radio/RADIO_BUCK_FB", "5": "/Ham Radio/RADIO_BUCK_EN",
        "6": "/Ham Radio/RADIO_BUCK_BOOT",
    }.items():
        expect(net(components, "U70", pin), want, f"TPS54302 radio buck pin {pin}")
    expect_value_prefix(components, "L70", "3.3uH", "radio buck inductor")
    expect(comp(components, "L70").footprint, "ducktop2:Coilcraft_XGL5030", "radio buck inductor footprint")
    expect_value_prefix(components, "R221", "100k", "radio buck feedback top")
    expect_value_prefix(components, "R222", "17.4k", "radio buck feedback bottom")
    expect(net(components, "C224", "1"), "/Ham Radio/RADIO_4V0", "radio buck feed-forward output side")
    expect(net(components, "C224", "2"), "/Ham Radio/RADIO_BUCK_FB", "radio buck feed-forward FB side")

    expect(net(components, "U40", "6"), "/MCU_3V3", "MAX-M10S V_BCKP always-on supply")
    expect(net(components, "U40", "7"), "/MCU_3V3", "MAX-M10S VCC_IO always-on supply")
    expect(net(components, "U40", "8"), "/MCU_3V3", "MAX-M10S VCC always-on supply")
    expect(net(components, "U40", "2"), "/GNSS_UART_RX", "MAX-M10S RX")
    expect(net(components, "U40", "3"), "/GNSS_UART_TX", "MAX-M10S TX")
    expect(net(components, "U40", "11"), local_net("Radio/OLED/GNSS", "GNSS_RF_IN"), "MAX-M10S RF input")
    expect(net(components, "J42", "1"), local_net("Radio/OLED/GNSS", "GNSS_RF_IN"), "GNSS U.FL center")
    expect(net(components, "J42", "2"), "GND", "GNSS U.FL shield")
    expect(prop(components, "J42", "MPN"), "U.FL-R-SMT-1(01)", "GNSS U.FL MPN")
    for ref in ("C172", "C173", "C186"):
        expect(net(components, ref, "1"), "/MCU_3V3", f"{ref} GNSS always-on rail")
        expect(net(components, ref, "2"), "GND", f"{ref} GNSS return")
    expect_value_prefix(components, "R174", "100k", "GNSS reset pull-up")
    expect(net(components, "R174", "1"), "/MCU_3V3", "GNSS reset pull-up rail")
    expect(net(components, "R174", "2"), "/GNSS_RESET_N", "GNSS reset signal")
    for obsolete in ("R195", "L40", "C176", "C177"):
        if obsolete in components:
            fail(f"obsolete unprotected active-GNSS-bias part {obsolete} is still present")

    pe42820_ground_pins = (
        "1", "3", "4", "5", "6", "7", "8", "9", "10", "11", "14", "15",
        "16", "17", "18", "19", "20", "21", "22", "24", "25", "26", "27",
        "29", "30", "31", "32", "33",
    )
    for ref, band, rfsel in [
        ("U240", "VHF", "/Ham Radio/RADIO_VHF_RF_SEL_4V0"),
        ("U250", "UHF", "/Ham Radio/RADIO_UHF_RF_SEL_4V0"),
    ]:
        expect(net(components, ref, "2"), local_net("Ham Radio", f"{band}_ANT_EXTERNAL"),
               f"{ref} RF1 external antenna port")
        expect(net(components, ref, "23"), local_net("Ham Radio", f"{band}_ANT_ONBOARD"),
               f"{ref} RF2 internal antenna port")
        expect(net(components, ref, "28"), local_net("Ham Radio", f"{band}_RF_FILTERED"),
               f"{ref} RFC filtered radio port")
        expect(net(components, ref, "12"), local_net("Ham Radio", "RADIO_4V0"), f"{ref} VDD")
        expect(net(components, ref, "13"), rfsel, f"{ref} antenna select")
        for pin in pe42820_ground_pins:
            expect(net(components, ref, pin), "GND", f"{ref} ground pin {pin}")
    for ref, top, band in (("R227", "R242", "VHF"), ("R228", "R260", "UHF")):
        expect_value_prefix(components, ref, "47k 1%", f"{band} PE42820 divider low")
        expect(net(components, ref, "1"), f"/Ham Radio/RADIO_{band}_RF_SEL_4V0",
               f"{band} RF select node")
        expect(net(components, ref, "2"), "GND", f"{band} RF select divider return")
        expect_value_prefix(components, top, "10k 1%", f"{band} PE42820 divider top")
        expect(net(components, top, "1"), f"/Ham Radio/RADIO_{band}_RF_SEL_4V0_RAW",
               f"{band} RF-select level-shifter output")
        expect(net(components, top, "2"), f"/Ham Radio/RADIO_{band}_RF_SEL_4V0",
               f"{band} PE42820 control node")
    for ref, band, bypass, default in (
        ("U241", "VHF", "C240", "R230"),
        ("U251", "UHF", "C250", "R232"),
    ):
        expect_contains(comp(components, ref).value, "SN74LVC1G373", f"{ref} transmit-safe RF-select latch")
        expect(prop(components, ref, "MPN"), "SN74LVC1G373DCKR", f"{ref} exact latch MPN")
        for pin, want in {
            "1": f"/Ham Radio/RADIO_{band}_PTT_SAFE_N", "2": "GND",
            "3": f"/RADIO_{band}_RF_SEL_3V3",
            "4": f"/Ham Radio/RADIO_{band}_RF_SEL_4V0_RAW",
            "5": "/Ham Radio/RADIO_4V0", "6": "GND",
        }.items():
            expect(net(components, ref, pin), want, f"{ref} pin {pin}")
        expect_value_prefix(components, bypass, "100n", f"{ref} RF-select latch bypass")
        expect(net(components, bypass, "1"), "/Ham Radio/RADIO_4V0", f"{ref} bypass rail")
        expect(net(components, bypass, "2"), "GND", f"{ref} bypass return")
        expect_value_prefix(components, default, "100k", f"{ref} RF-select reset default")
        expect(net(components, default, "1"), f"/RADIO_{band}_RF_SEL_3V3",
               f"{ref} reset-default input")
        expect(net(components, default, "2"), "GND", f"{ref} reset-default return")
    for obsolete in ("C241", "C251"):
        if obsolete in components:
            fail(f"obsolete dual-rail RF-select bypass {obsolete} remains")

    for pin, want in {
        "1": "/RADIO_VHF_PTT_N", "6": "/Ham Radio/RADIO_VHF_PTT_REQ",
        "3": "/RADIO_UHF_PTT_N", "4": "/Ham Radio/RADIO_UHF_PTT_REQ",
        "2": "GND", "5": "/MCU_3V3",
    }.items():
        expect(net(components, "U260", pin), want, f"PTT request inverter pin {pin}")
    expect(prop(components, "U260", "MPN"), "SN74LVC2G04DCKR", "PTT inverter exact MPN")
    for pin, want in {
        "1": "/RADIO_VHF_PTT_N", "2": "/Ham Radio/RADIO_UHF_PTT_REQ",
        "7": "/Ham Radio/RADIO_VHF_PTT_SAFE_N",
        "5": "/RADIO_UHF_PTT_N", "6": "/Ham Radio/RADIO_VHF_PTT_REQ",
        "3": "/Ham Radio/RADIO_UHF_PTT_SAFE_N", "4": "GND", "8": "/MCU_3V3",
    }.items():
        expect(net(components, "U261", pin), want, f"dual-radio PTT interlock pin {pin}")
    expect(prop(components, "U261", "MPN"), "SN74LVC2G32DCUR", "PTT interlock exact MPN")
    for ref in ("C260", "C261"):
        expect_value_prefix(components, ref, "100n", f"{ref} PTT interlock bypass")
        expect(net(components, ref, "1"), "/MCU_3V3", f"{ref} PTT interlock rail")
        expect(net(components, ref, "2"), "GND", f"{ref} PTT interlock return")
    for ref, band, bypass, tx_iso, tx_bias in (
        ("U242", "VHF", "C246", "R243", "R244"),
        ("U252", "UHF", "C256", "R261", "R262"),
    ):
        expect_contains(comp(components, ref).value, "SN74LVC3G34", f"{ref} powered-off-safe radio controls")
        for pin, want in {
            "1": f"/RADIO_{band}_UART_TX",
            "2": f"/Ham Radio/RADIO_{band}_PTT_LOCAL_N",
            "3": f"/RADIO_{band}_PD_N", "4": "GND",
            "5": f"/Ham Radio/RADIO_{band}_PD_LOCAL_N",
            "6": f"/Ham Radio/RADIO_{band}_PTT_SAFE_N",
            "7": f"/Ham Radio/RADIO_{band}_UART_RXD",
            "8": "/Ham Radio/RADIO_4V0",
        }.items():
            expect(net(components, ref, pin), want, f"{ref} pin {pin}")
        expect_value_prefix(components, bypass, "100n", f"{ref} local bypass")
        expect(net(components, bypass, "1"), "/Ham Radio/RADIO_4V0", f"{ref} bypass rail")
        expect(net(components, bypass, "2"), "GND", f"{ref} bypass return")
        expect_value_prefix(components, tx_iso, "1k", f"{band} module TX isolation")
        expect(net(components, tx_iso, "1"), f"/Ham Radio/RADIO_{band}_UART_TXD",
               f"{band} module TXD side")
        expect(net(components, tx_iso, "2"), f"/RADIO_{band}_UART_RX", f"{band} EC RX side")
        expect_value_prefix(components, tx_bias, "100k", f"{band} EC TX default-low bias")
        expect(net(components, tx_bias, "1"), f"/RADIO_{band}_UART_TX", f"{band} EC TX node")
        expect(net(components, tx_bias, "2"), "GND", f"{band} EC TX bias return")
    for ref, band in (("J70", "VHF"), ("J71", "UHF")):
        expect(net(components, ref, "8"), "/Ham Radio/RADIO_4V0", f"{ref} radio module VCC")
        for pin in ("9", "10"):
            expect(net(components, ref, pin), "GND", f"{ref} module GND {pin}")
        for pin in ("2", "4", "11", "13", "14", "15"):
            expect_unconnected(components, ref, pin)
        expect(net(components, ref, "3"), local_net("Ham Radio", f"{band}_AF_OUT"), f"{ref} AF output")
        expect(net(components, ref, "5"), local_net("Ham Radio", f"RADIO_{band}_PTT_LOCAL_N"), f"{ref} fail-safe PTT")
        expect(net(components, ref, "6"), local_net("Ham Radio", f"RADIO_{band}_PD_LOCAL_N"), f"{ref} fail-safe PD")
        expect(net(components, ref, "12"), local_net("Ham Radio", f"{band}_RF_RAW"), f"{ref} RF output")
        expect(net(components, ref, "16"), local_net("Ham Radio", f"RADIO_{band}_UART_RXD"), f"{ref} buffered RXD input")
        expect(net(components, ref, "17"), local_net("Ham Radio", f"RADIO_{band}_UART_TXD"), f"{ref} isolated TXD output")

    for ref, net_name in (("R223", "/RADIO_VHF_PTT_N"), ("R224", "/RADIO_UHF_PTT_N")):
        expect_value_prefix(components, ref, "100k", f"{ref} PTT reset default")
        expect(net(components, ref, "1"), "/MCU_3V3", f"{ref} PTT pull-up rail")
        expect(net(components, ref, "2"), net_name, f"{ref} PTT inactive node")
    for ref, net_name in (("R225", "/RADIO_VHF_PD_N"), ("R226", "/RADIO_UHF_PD_N")):
        expect_value_prefix(components, ref, "100k", f"{ref} radio sleep default")
        expect(net(components, ref, "1"), net_name, f"{ref} radio power-down node")
        expect(net(components, ref, "2"), "GND", f"{ref} reset-time radio sleep return")

    for ref, band, value, footprint, ground_pins in (
        ("FL240", "VHF", "Mini-Circuits LFCN-160+", "Filter:Filter_Mini-Circuits_FV1206", ("2", "4")),
        ("FL250", "UHF", "Mini-Circuits ULP-470+", "ducktop2:MiniCircuits_QA2224_PL484", ("2", "4", "5", "6")),
    ):
        expect_value_prefix(components, ref, value, f"{ref} released packaged LPF")
        expect(comp(components, ref).footprint, footprint, f"{ref} exact LPF footprint")
        expect(net(components, ref, "1"), local_net("Ham Radio", f"{band}_RF_RAW"), f"{ref} module-side RF")
        expect(net(components, ref, "3"), local_net("Ham Radio", f"{band}_RF_FILTERED"), f"{ref} switch-side RF")
        for pin in ground_pins:
            expect(net(components, ref, pin), "GND", f"{ref} ground pin {pin}")
    expect(prop(components, "FL240", "MPN"), "LFCN-160+", "VHF LPF exact MPN")
    expect(prop(components, "FL240", "PowerRating"),
           "8W_MAX_AT_25C_DERATE_TO_3W_AT_100C", "VHF LPF released power rating")

    expect(net(components, "U330", "1"), local_net("Radio Audio Codec", "CODEC_USB_DP"), "PCM2902 D+")
    expect(net(components, "U330", "2"), local_net("Radio Audio Codec", "CODEC_USB_DM"), "PCM2902 D-")
    expect(net(components, "R330", "1"), "/RADIO_CODEC_USB_DP", "codec USB DP hub side")
    expect(net(components, "R331", "1"), "/RADIO_CODEC_USB_DM", "codec USB DM hub side")
    expect(net(components, "R337", "1"), "/RADIO_CODEC_USB_VBUS", "codec switched VBUS hub side")
    expect(net(components, "R337", "2"), local_net("Radio Audio Codec", "CODEC_VBUS"),
           "codec filtered VBUS side")
    expect(net(components, "U330", "3"), local_net("Radio Audio Codec", "CODEC_VBUS"), "PCM2902 VBUS")
    for pin in ("8", "9", "27"):
        expect(net(components, "U330", pin), local_net("Radio Audio Codec", "CODEC_VDDI"),
               f"PCM2902 VDDI pin {pin}")
    expect(net(components, "U330", "10"), local_net("Radio Audio Codec", "CODEC_VCCCI"), "PCM2902 VCCCI")
    expect(net(components, "U330", "14"), local_net("Radio Audio Codec", "CODEC_VCOM"), "PCM2902 VCOM")
    expect(net(components, "U330", "15"), local_net("Radio Audio Codec", "CODEC_TX_UHF"), "PCM2902 UHF DAC")
    expect(net(components, "U330", "16"), local_net("Radio Audio Codec", "CODEC_TX_VHF"), "PCM2902 VHF DAC")
    expect(net(components, "U330", "17"), local_net("Radio Audio Codec", "CODEC_VCCP1I"), "PCM2902 VCCP1I")
    expect(net(components, "U330", "19"), local_net("Radio Audio Codec", "CODEC_VCCP2I"), "PCM2902 VCCP2I")
    expect(net(components, "U330", "23"), local_net("Radio Audio Codec", "CODEC_VCCXI"), "PCM2902 VCCXI")
    for pin in ("5", "6", "7", "24", "25"):
        expect_unconnected(components, "U330", pin)
    expect(net(components, "U330", "28"), local_net("Radio Audio Codec", "CODEC_SSPND"),
           "PCM2902 suspend status")
    expect(net(components, "Y330", "1"), local_net("Radio Audio Codec", "CODEC_XTI"), "PCM2902 crystal XTI")
    expect(net(components, "Y330", "3"), local_net("Radio Audio Codec", "CODEC_XTO"), "PCM2902 crystal XTO")
    expect(net(components, "Q330", "1"), local_net("Radio Audio Codec", "VHF_MUTE_GATE"),
           "VHF fail-mute gate")
    expect(net(components, "Q330", "2"), "GND", "VHF fail-mute source")
    expect(net(components, "Q330", "3"), "/RADIO_VHF_MIC_IN", "VHF fail-mute shunt")
    expect(net(components, "Q331", "1"), local_net("Radio Audio Codec", "UHF_MUTE_GATE"),
           "UHF fail-mute gate")
    expect(net(components, "Q331", "2"), "GND", "UHF fail-mute source")
    expect(net(components, "Q331", "3"), "/RADIO_UHF_MIC_IN", "UHF fail-mute shunt")
    expect(net(components, "Q332", "1"), local_net("Radio Audio Codec", "CODEC_SSPND"),
           "codec-loss PMOS gate")
    expect(net(components, "Q332", "2"), "/MCU_3V3", "codec-loss PMOS source")
    expect(net(components, "Q332", "3"), local_net("Radio Audio Codec", "CODEC_FORCE_MUTE"),
           "codec-loss PMOS drain")
    expect(prop(components, "Q332", "MPN"), "BSS84LT1G", "codec-loss PMOS MPN")
    for ref, source, gate in (
        ("D390", "/RADIO_VHF_PTT_N", "VHF_MUTE_GATE"),
        ("D391", local_net("Radio Audio Codec", "CODEC_FORCE_MUTE"), "VHF_MUTE_GATE"),
        ("D392", "/RADIO_UHF_PTT_N", "UHF_MUTE_GATE"),
        ("D393", local_net("Radio Audio Codec", "CODEC_FORCE_MUTE"), "UHF_MUTE_GATE"),
    ):
        expect(net(components, ref, "1"), local_net("Radio Audio Codec", gate), f"{ref} mute OR cathode")
        expect(net(components, ref, "2"), source, f"{ref} mute OR anode")
        expect(prop(components, ref, "MPN"), "BAT54WS-7-F", f"{ref} mute OR diode MPN")
    for ref, rail in (("R342", "CODEC_SSPND"), ("R343", "CODEC_FORCE_MUTE"),
                      ("R344", "VHF_MUTE_GATE"), ("R345", "UHF_MUTE_GATE")):
        expect_value_prefix(components, ref, "100k", f"{ref} fail-mute default")
        expect(net(components, ref, "1"), local_net("Radio Audio Codec", rail), f"{ref} fail-mute node")
        expect(net(components, ref, "2"), "GND", f"{ref} fail-mute return")

    for ref, value, net_a, net_b in (
        ("R334", "82k 1%", local_net("Radio Audio Codec", "VHF_TX_AUDIO"), "/RADIO_VHF_MIC_IN"),
        ("R335", "82k 1%", local_net("Radio Audio Codec", "UHF_TX_AUDIO"), "/RADIO_UHF_MIC_IN"),
        ("R336", "1k 1%", "/RADIO_VHF_MIC_IN", "GND"),
        ("R341", "1k 1%", "/RADIO_UHF_MIC_IN", "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} radio mic attenuation value")
        expect(net(components, ref, "1"), net_a, f"{ref} radio mic attenuation pin 1")
        expect(net(components, ref, "2"), net_b, f"{ref} radio mic attenuation pin 2")

    dnp, exclude_bom = component_flags()
    for obsolete in ("L240", "L241", "C242", "L250", "L251", "C252"):
        if obsolete in components:
            fail(f"obsolete provisional RF-filter component {obsolete} is still in the schematic")
    for ref in ("C245", "C255"):
        if ref not in dnp or ref not in exclude_bom:
            fail(f"{ref} optional RF match must remain DNP and excluded from BOM until VNA release")
    for ref in ("R229", "R231"):
        if ref in dnp or ref in exclude_bom:
            fail(f"{ref} radio H/L strap must be fitted for the low-power prototype")


def check_optional_radio_interface(components):
    """Require a usable laptop and electrically quiet nets with no radio board fitted."""
    wifi_sheet = "Wi-Fi/Bluetooth & OLEDs"
    radio_sheet = "Optional Radio Daughterboard Interface"
    rloc = lambda name: local_net(radio_sheet, name)

    expect(net(components, "F10", "1"), "/PCIE_3V3", "E-key switched endpoint input")
    expect(net(components, "F10", "2"), local_net(wifi_sheet, "WIFI_3V3"),
           "E-key local fused rail")
    expect(prop(components, "J40", "QualifiedModuleMPN"), "AX210.NGWGIE.NV",
           "E-key qualified module")
    expect(prop(components, "J40", "QualifiedModuleContract"),
           "M2_2230_KEY_E_PCIE_WIFI_USB_BLUETOOTH_NOT_CNVIO2",
           "E-key electrical contract")
    for ref, signal in (("R170", "WIFI_W_DISABLE1_N"), ("R171", "WIFI_W_DISABLE2_N")):
        expect(net(components, ref, "1"), local_net(wifi_sheet, "WIFI_3V3"),
               f"{ref} powered-slot pull-up")
        expect(net(components, ref, "2"), local_net(wifi_sheet, signal), f"{ref} disable output")
    for pin, want in {
        "1": "/WIFI_W_DISABLE1_N_EC", "7": local_net(wifi_sheet, "WIFI_W_DISABLE1_N"),
        "6": "/WIFI_W_DISABLE2_N_EC", "2": local_net(wifi_sheet, "WIFI_W_DISABLE2_N"),
        "3": "GND", "4": "GND", "8": local_net(wifi_sheet, "WIFI_3V3"),
    }.items():
        expect(net(components, "U170", pin), want, f"E-key powered-off isolator pin {pin}")

    expect(comp(components, "J2300").footprint,
           "Connector_Hirose_DF40:Hirose_DF40C-60DP-0.4V_2x30-1MP_P0.4mm",
           "radio daughterboard mainboard connector")
    expect(prop(components, "J2300", "MPN"), "DF40C-60DP-0.4V(51)",
           "radio daughterboard connector MPN")
    expect(prop(components, "J2300", "MatingConnector"), "DF40C(2.0)-60DS-0.4V(51)",
           "radio daughterboard mating connector")
    expect(prop(components, "J2300", "AbsentBoardContract"),
           "NO_RADIO_BOARD_REQUIRED_FOR_BOOT_OR_PRIMARY_LAPTOP_OPERATION",
           "radio daughterboard absent-board contract")
    for pin in range(1, 9):
        expect(net(components, "J2300", str(pin)), rloc("RADIO_DB_5V"),
               f"J2300 shared 5V pin {pin}")
    for pin in (*range(9, 17), 21, 22, 27, 32, 37, 43, *range(45, 61)):
        expect(net(components, "J2300", str(pin)), "GND", f"J2300 ground pin {pin}")
    for pin in ("17", "18"):
        expect(net(components, "J2300", pin), rloc("RADIO_CODEC_USB_VBUS_DB"),
               f"J2300 codec VBUS pin {pin}")
    expect(net(components, "J2300", "19"), rloc("RADIO_CODEC_USB_DP_DB"), "J2300 codec D+")
    expect(net(components, "J2300", "20"), rloc("RADIO_CODEC_USB_DM_DB"), "J2300 codec D-")
    expect(net(components, "J2300", "44"), "/RADIO_DB_PRESENT_N", "J2300 passive presence strap")
    expect(net(components, "J2300", "MP"), "GND", "J2300 mounting-pad ground")

    expect_contains(comp(components, "U2300").value, "TPS259470", "radio daughterboard eFuse")
    expect(prop(components, "U2300", "SafetyContract"),
           "DEFAULT_OFF;REVERSE_BLOCKING;APPROX_2A_CURRENT_LIMIT",
           "radio daughterboard power isolation")
    for pin, want in {
        "1": "/RADIO_DB_PWR_EN", "2": "GND", "4": "/RADIO_DB_FAULT_N",
        "5": "/SYS_5V", "6": rloc("RADIO_DB_5V"),
        "7": rloc("RADIO_DB_DVDT"), "8": "GND", "9": rloc("RADIO_DB_ILM"),
    }.items():
        expect(net(components, "U2300", pin), want, f"U2300 pin {pin}")
    expect_value_prefix(components, "R2300", "100k", "radio eFuse default-off pull-down")
    expect(net(components, "R2300", "1"), "/RADIO_DB_PWR_EN", "radio eFuse enable")
    expect(net(components, "R2300", "2"), "GND", "radio eFuse fail-off return")
    expect_value_prefix(components, "R2306", "10k", "radio board presence pull-up")
    expect(net(components, "R2306", "1"), "/MCU_3V3", "presence pull-up rail")
    expect(net(components, "R2306", "2"), "/RADIO_DB_PRESENT_N", "presence sense")

    expect_contains(comp(components, "U2301").value, "TLV803EA43", "radio rail supervisor")
    expect_contains(comp(components, "U2302").value, "74LVC1G17", "radio PG level restore")
    expect(net(components, "U2302", "4"), "/RADIO_DB_PG", "qualified radio power-good")
    expect(net(components, "U2302", "5"), "/MCU_3V3", "radio PG logic rail")

    expect_contains(comp(components, "U2303").value, "TS3USB30E", "radio codec USB disconnect")
    expect(prop(components, "U2303", "PowerOffContract"),
           "USB_DP_DM_DISCONNECTED_UNLESS_RADIO_DB_PG_IS_HIGH",
           "radio codec data isolation")
    expect(net(components, "U2303", "9"), rloc("RADIO_USB_OE_N"), "radio USB switch enable")
    expect_value_prefix(components, "R2307", "100k", "radio USB default-disconnect pull-up")
    expect(net(components, "Q2300", "1"), "/RADIO_DB_PG", "radio USB PG gate")
    expect(net(components, "Q2300", "3"), rloc("RADIO_USB_OE_N"), "radio USB active-low enable")
    expect_contains(comp(components, "U2304").value, "TPS2553D", "radio codec VBUS gate")
    expect(net(components, "U2304", "3"), "/RADIO_DB_PG", "radio codec VBUS qualified enable")
    expect(net(components, "U2304", "5"), rloc("RADIO_CODEC_ILIM"), "radio codec VBUS ILIM")
    expect(net(components, "U2304", "6"), rloc("RADIO_CODEC_USB_VBUS_DB"), "radio codec switched VBUS")
    expect_value_prefix(components, "R2308", "133k 1%", "radio codec 200mA current limit")
    expect(prop(components, "R2308", "MPN"), "RC0603FR-07133KL", "radio codec ILIM exact MPN")

    radio_signals = {
        "23": "RADIO_VHF_UART_TX", "24": "RADIO_VHF_UART_RX",
        "25": "RADIO_UHF_UART_TX", "26": "RADIO_UHF_UART_RX",
        "28": "RADIO_VHF_PTT_N", "29": "RADIO_UHF_PTT_N",
        "30": "RADIO_VHF_PD_N", "31": "RADIO_UHF_PD_N",
        "33": "RADIO_VHF_SQL", "34": "RADIO_UHF_SQL",
        "35": "RADIO_VHF_RF_SEL_3V3", "36": "RADIO_UHF_RF_SEL_3V3",
        "38": "GNSS_UART_RX", "39": "GNSS_UART_TX", "40": "GNSS_RESET_N",
        "41": "GNSS_PPS", "42": "GNSS_EXTINT",
    }
    for index, (pin, signal) in enumerate(radio_signals.items()):
        boundary = rloc(f"{signal}_DB")
        resistor = f"R{2340 + index}"
        expect(net(components, "J2300", pin), boundary, f"J2300 isolated signal pin {pin}")
        expect_value_prefix(components, resistor, "4.7k", f"{resistor} daughterboard fault isolation")
        expect(prop(components, resistor, "MPN"), "RC0603FR-074K7L", f"{resistor} exact MPN")
        expect(net(components, resistor, "1"), f"/{signal}", f"{resistor} mainboard side")
        expect(net(components, resistor, "2"), boundary, f"{resistor} connector side")

    defaults = {
        "R2310": ("/RADIO_VHF_PTT_N", "/MCU_3V3", "10k"),
        "R2311": ("/RADIO_UHF_PTT_N", "/MCU_3V3", "10k"),
        "R2312": ("/RADIO_VHF_PD_N", "GND", "10k"),
        "R2313": ("/RADIO_UHF_PD_N", "GND", "10k"),
        "R2314": ("/RADIO_VHF_RF_SEL_3V3", "GND", "100k"),
        "R2315": ("/RADIO_UHF_RF_SEL_3V3", "GND", "100k"),
        "R2316": ("/RADIO_VHF_UART_TX", "/MCU_3V3", "100k"),
        "R2317": ("/RADIO_UHF_UART_TX", "/MCU_3V3", "100k"),
        "R2318": ("/GNSS_UART_RX", "/MCU_3V3", "100k"),
        "R2319": ("/GNSS_RESET_N", "/MCU_3V3", "100k"),
        "R2320": ("/RADIO_VHF_UART_RX", "GND", "100k"),
        "R2321": ("/RADIO_UHF_UART_RX", "GND", "100k"),
        "R2322": ("/RADIO_VHF_SQL", "GND", "100k"),
        "R2323": ("/RADIO_UHF_SQL", "GND", "100k"),
        "R2324": ("/GNSS_UART_TX", "GND", "100k"),
        "R2325": ("/GNSS_PPS", "GND", "100k"),
        "R2326": ("/GNSS_EXTINT", "GND", "100k"),
    }
    for ref, (signal, default, value) in defaults.items():
        expect_value_prefix(components, ref, value, f"{ref} absent-board default")
        expect(net(components, ref, "1"), signal, f"{ref} signal")
        expect(net(components, ref, "2"), default, f"{ref} safe default")

    for obsolete in ("U70", "J70", "J71", "U240", "U250", "U330", "U40", "J42"):
        if obsolete in components:
            fail(f"radio/GNSS daughterboard component {obsolete} remains on the mainboard")


def check_system_audio(components):
    sheet = "System Audio"
    loc = lambda name: local_net(sheet, name)

    expect(comp(components, "U400").footprint,
           "Package_DFN_QFN:QFN-36-1EP_6x6mm_P0.5mm_EP3.7x3.7mm_ThermalVias",
           "USB2512B footprint")
    expect_value_prefix(components, "U400", "USB2512B-AEZG-TR", "system-audio hub part")
    expect(net(components, "F400", "1"), "/SYS_5V", "audio branch fuse input")
    expect(net(components, "F400", "2"), loc("AUDIO_5V"), "audio branch fuse output")

    hub_pins = {
        "1": loc("SYSTEM_DAC_USB_DM"), "2": loc("SYSTEM_DAC_USB_DP"),
        "3": "/RADIO_CODEC_USB_DM_HOST", "4": "/RADIO_CODEC_USB_DP_HOST",
        "5": "/SYS_3V3", "10": "/SYS_3V3", "12": loc("HUB_PORT1_EN"),
        "13": loc("HUB_PORT1_OC_N"), "14": loc("HUB_CRFILT"),
        "15": "/SYS_3V3", "16": loc("HUB_PORT2_EN"),
        "17": loc("HUB_PORT2_OC_N"), "22": loc("HUB_NON_REM1"),
        "23": "/SYS_3V3", "24": loc("HUB_CFG_SEL0"),
        "25": loc("HUB_CFG_SEL1"), "26": loc("HUB_RESET_N"),
        "27": loc("HUB_VBUS_DET"), "28": loc("HUB_NON_REM0"),
        "29": "/SYS_3V3", "30": "/AUDIO_USB_DM", "31": "/AUDIO_USB_DP",
        "32": loc("HUB_XO"), "33": loc("HUB_XI"),
        "34": loc("HUB_PLLFILT"), "35": loc("HUB_RBIAS"),
        "36": "/SYS_3V3", "37": "GND",
    }
    for pin, want in hub_pins.items():
        expect(net(components, "U400", pin), want, f"USB2512B pin {pin}")
    for pin in ("6", "7", "8", "9", "11", "18", "19", "20", "21"):
        expect_unconnected(components, "U400", pin)

    # Strap mode: self-powered, individual switching/OC, fixed system codec on
    # non-removable port 1 and optional radio codec on removable port 2.
    for ref, pin_net, rail in (
        ("R402", loc("HUB_NON_REM1"), "GND"),
        ("R403", loc("HUB_NON_REM0"), "/SYS_3V3"),
        ("R404", loc("HUB_CFG_SEL0"), "GND"),
        ("R405", loc("HUB_CFG_SEL1"), "GND"),
    ):
        expect(net(components, ref, "1"), pin_net, f"{ref} strap pin 1")
        expect(net(components, ref, "2"), rail, f"{ref} strap pin 2")
    expect_value_prefix(components, "R403", "10k", "NON_REM0 high strap")
    for ref in ("R402", "R404", "R405"):
        expect_value_prefix(components, ref, "100k", f"{ref} low strap")
    expect_value_prefix(components, "R417", "0R", "physical internal VBUS-valid hub link")
    expect(net(components, "R417", "1"), "/INTERNAL_USB_VBUS_VALID", "audio-hub physical VBUS-valid input")
    expect(net(components, "R417", "2"), loc("HUB_VBUS_DET"), "audio-hub VBUS detect node")
    for obsolete in ("U403", "C417"):
        if obsolete in components:
            fail(f"obsolete status-proxy audio USB component {obsolete} remains")
    if "R406" in components:
        fail("obsolete unqualified audio-hub PSON link R406 is still present")

    for pin, want in {
        "1": "GND", "2": loc("AUDIO_5V"), "3": loc("HUB_PORT1_EN"),
        "4": loc("HUB_PORT2_EN"), "5": loc("HUB_PORT2_OC_N"),
        "6": "/RADIO_CODEC_USB_VBUS_HOST", "7": loc("SYSTEM_DAC_USB_VBUS"),
        "8": loc("HUB_PORT1_OC_N"),
    }.items():
        expect(net(components, "U402", pin), want, f"TPS2052B pin {pin}")
    for pin, want in {"1": loc("HUB_RESET_N"), "2": "GND", "3": "/SYS_3V3"}.items():
        expect(net(components, "U401", pin), want, f"audio-hub reset supervisor pin {pin}")

    codec_pins = {
        "1": loc("CODEC_USB_DP"), "2": loc("CODEC_USB_DM"),
        "3": loc("CODEC_VBUS"), "4": "GND",
        "8": loc("CODEC_VDDI"), "9": loc("CODEC_VDDI"),
        "10": loc("CODEC_VCCCI"), "11": "GND",
        "12": loc("MIC_ADC_L"), "13": loc("MIC_ADC_R"),
        "14": loc("CODEC_VCOM"), "15": loc("DAC_VOUT_R"),
        "16": loc("DAC_VOUT_L"), "17": loc("CODEC_VCCP1I"),
        "18": "GND", "19": loc("CODEC_VCCP2I"),
        "20": loc("CODEC_XTO"), "21": loc("CODEC_XTI"),
        "22": "GND", "23": loc("CODEC_VCCXI"), "24": "GND",
        "26": "GND", "27": loc("CODEC_VDDI"),
        "28": loc("DAC_SSPND"),
    }
    for pin, want in codec_pins.items():
        expect(net(components, "U410", pin), want, f"PCM2900C pin {pin}")
    for pin in ("5", "6", "7", "25"):
        expect_unconnected(components, "U410", pin)
    expect_value_prefix(components, "U410", "PCM2900CDBR", "system USB audio codec")
    expect_value_prefix(components, "R410", "22R", "system codec USB D- series")
    expect(net(components, "R410", "1"), loc("SYSTEM_DAC_USB_DM"), "R410 hub side")
    expect(net(components, "R410", "2"), loc("CODEC_USB_DM"), "R410 codec side")
    expect_value_prefix(components, "R411", "22R", "system codec USB D+ series")
    expect(net(components, "R411", "1"), loc("SYSTEM_DAC_USB_DP"), "R411 hub side")
    expect(net(components, "R411", "2"), loc("CODEC_USB_DP"), "R411 codec side")
    expect_value_prefix(components, "R412", "1.5k", "PCM2900C D+ pull-up")
    expect(net(components, "R412", "1"), loc("CODEC_VDDI"), "R412 pull-up rail")
    expect(net(components, "R412", "2"), loc("CODEC_USB_DP"), "R412 D+ node")
    expect_value_prefix(components, "R413", "2.2R", "PCM2900C VBUS filter")
    expect(net(components, "R413", "1"), loc("SYSTEM_DAC_USB_VBUS"), "R413 switched VBUS side")
    expect(net(components, "R413", "2"), loc("CODEC_VBUS"), "R413 codec VBUS side")

    for pin, want in {
        "1": loc("DAC_SSPND"), "2": "/AUDIO_AMP_EC_EN", "3": "GND",
        "4": loc("AMP_ENABLE"), "5": "/SYS_3V3",
    }.items():
        expect(net(components, "U421", pin), want, f"audio pop-suppression gate pin {pin}")
    expect(net(components, "R415", "1"), "/AUDIO_AMP_EC_EN", "amp EC-enable pull-down node")
    expect(net(components, "R415", "2"), "GND", "amp EC-enable fail-safe ground")
    expect(net(components, "R416", "1"), loc("DAC_SSPND"), "DAC operational pull-down node")
    expect(net(components, "R416", "2"), "GND", "DAC operational fail-safe ground")

    amp_pins = {
        "1": "GND", "2": loc("AMP_OUT_LP"), "3": loc("AUDIO_5V"),
        "4": "GND", "5": loc("AMP_OUT_LN"), "7": loc("AMP_ENABLE"),
        "8": loc("AMP_ENABLE"), "9": loc("AUDIO_5V"),
        "11": loc("AMP_OUT_RN"), "12": "GND", "13": loc("AUDIO_5V"),
        "14": loc("AMP_OUT_RP"), "15": loc("AUDIO_5V"),
        "16": loc("AMP_IN_RP"), "17": loc("AMP_IN_RN"), "18": "GND",
        "19": loc("AMP_IN_LN"), "20": loc("AMP_IN_LP"), "21": "GND",
    }
    for pin, want in amp_pins.items():
        expect(net(components, "U420", pin), want, f"TPA2012D2 pin {pin}")
    for pin in ("6", "10"):
        expect_unconnected(components, "U420", pin)
    expect(net(components, "J420", "1"), loc("SPK_L_P"), "left speaker positive BTL leg")
    expect(net(components, "J420", "2"), loc("SPK_L_N"), "left speaker negative BTL leg")
    expect(net(components, "J421", "1"), loc("SPK_R_P"), "right speaker positive BTL leg")
    expect(net(components, "J421", "2"), loc("SPK_R_N"), "right speaker negative BTL leg")
    for ref in ("J420", "J421"):
        expect(comp(components, ref).footprint,
               "Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal",
               f"{ref} low-profile keyed speaker footprint")
        expect(prop(components, ref, "MPN"), "SM02B-GHS-TB", f"{ref} exact MPN")
        expect(prop(components, ref, "MatingHousing"), "GHR-02V-S", f"{ref} mating housing")

    mic_ldo = {
        "1": "/SYS_3V3", "2": "GND", "3": "/AUDIO_MIC_EN",
        "5": loc("MIC_2V8"),
    }
    for pin, want in mic_ldo.items():
        expect(net(components, "U430", pin), want, f"LP5907 microphone LDO pin {pin}")
    expect_unconnected(components, "U430", "4")
    expect_value_prefix(components, "U430", "LP5907MFX-2.8", "microphone LDO")
    expect(comp(components, "MK430").footprint,
           "ducktop2:Infineon_IM68A130V01", "microphone acoustic footprint")
    expect(prop(components, "MK430", "Manufacturer"), "Infineon Technologies",
           "microphone manufacturer")
    expect(prop(components, "MK430", "MPN"), "IM68A130V01XTMA1",
           "active microphone ordering code")
    for pin, want in {
        "1": loc("MIC_RAW"), "2": "GND", "3": loc("MIC_2V8"), "4": "GND",
    }.items():
        expect(net(components, "MK430", pin), want, f"IM68A130 pin {pin}")
    for pin, want in {
        "1": loc("MIC_PREAMP"), "2": "GND", "3": loc("MIC_RAW"),
        "4": loc("MIC_FB"), "5": "/SYS_3V3",
    }.items():
        expect(net(components, "U431", pin), want, f"TLV9061 microphone preamp pin {pin}")
    for ref, value, pin1, pin2 in (
        ("R432", "4.99k", loc("MIC_PREAMP"), loc("MIC_FB")),
        ("C453", "1.2n", loc("MIC_PREAMP"), loc("MIC_FB")),
        ("R433", "1.00k", loc("MIC_FB"), loc("MIC_HP_NODE")),
        ("C454", "4.7u", loc("MIC_HP_NODE"), "GND"),
        ("C455", "4.7u", loc("MIC_PREAMP"), loc("MIC_ADC_L")),
        ("C456", "4.7u", loc("MIC_PREAMP"), loc("MIC_ADC_R")),
        ("R434", "100k", "/AUDIO_MIC_EN", "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} microphone network value")
        expect(net(components, ref, "1"), pin1, f"{ref} microphone network pin 1")
        expect(net(components, ref, "2"), pin2, f"{ref} microphone network pin 2")
    expect(net(components, "R435", "1"), loc("MIC_2V8"), "microphone indicator actual supply rail")
    expect(net(components, "R435", "2"), loc("MIC_LED_A"), "microphone indicator anode resistor")
    expect(net(components, "LED430", "1"), "GND", "microphone indicator cathode")
    expect(net(components, "LED430", "2"), loc("MIC_LED_A"), "microphone indicator anode")
    expect(prop(components, "LED430", "MPN"), "APT1608SGC", "microphone indicator exact MPN")


def check_ethernet(components):
    sheet = "Gigabit Ethernet"
    loc = lambda name: local_net(sheet, name)

    expect_value_prefix(components, "U500", "RTL8111H-CG-RH", "Ethernet controller")
    expect(comp(components, "U500").footprint,
           "Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm",
           "RTL8111H footprint")
    rtl_pins = {
        "1": loc("ETH_MDI0_P"), "2": loc("ETH_MDI0_N"), "3": loc("ETH_1V0"),
        "4": loc("ETH_MDI1_P"), "5": loc("ETH_MDI1_N"), "6": loc("ETH_MDI2_P"),
        "7": loc("ETH_MDI2_N"), "8": loc("ETH_1V0"), "9": loc("ETH_MDI3_P"),
        "10": loc("ETH_MDI3_N"), "11": "/PCIE_3V3", "12": "/GBE_CLKREQ_N",
        "13": loc("GBE_HSI_P"), "14": loc("GBE_HSI_N"), "15": "/GBE_REFCLK_P",
        "16": "/GBE_REFCLK_N", "17": loc("GBE_HSO_P"), "18": loc("GBE_HSO_N"),
        "19": "/PLTRST_SRC_N", "20": loc("GBE_ISOLATE_N"), "21": "/PCIE_WAKE_N",
        "22": loc("ETH_1V0"), "23": "/PCIE_3V3", "24": loc("ETH_1V0"),
        "25": loc("ETH_LED_ACT_N"), "26": loc("ETH_LED_1000_N"),
        "28": loc("ETH_XI"), "29": loc("ETH_XO"), "30": loc("ETH_1V0"),
        "31": loc("ETH_RSET"), "32": "/PCIE_3V3", "33": "GND",
    }
    for pin, want in rtl_pins.items():
        expect(net(components, "U500", pin), want, f"RTL8111H pin {pin}")
    expect_unconnected(components, "U500", "27")

    for ref, pin1, pin2 in (
        ("C500", "/GBE_HOST_TX_P", loc("GBE_HSI_P")),
        ("C501", "/GBE_HOST_TX_N", loc("GBE_HSI_N")),
        ("C502", loc("GBE_HSO_P"), "/GBE_HOST_RX_P"),
        ("C503", loc("GBE_HSO_N"), "/GBE_HOST_RX_N"),
    ):
        expect_value_prefix(components, ref, "220n", f"{ref} PCIe AC coupling")
        expect(prop(components, ref, "MPN"), "GRM155R71C224KA12D", f"{ref} PCIe AC-coupling MPN")
        expect(net(components, ref, "1"), pin1, f"{ref} pin 1")
        expect(net(components, ref, "2"), pin2, f"{ref} pin 2")

    expect_value_prefix(components, "Y500", "ECS-250-8-33-AGN-TR 25MHz 8pF",
                        "qualified Ethernet crystal")
    expect(prop(components, "Y500", "Manufacturer"), "ECS Inc.",
           "Ethernet crystal manufacturer")
    expect(prop(components, "Y500", "MPN"), "ECS-250-8-33-AGN-TR",
           "Ethernet crystal MPN")
    for pin, want in {
        "1": loc("ETH_XI"), "2": "GND", "3": loc("ETH_XO"), "4": "GND",
    }.items():
        expect(net(components, "Y500", pin), want, f"Ethernet crystal pin {pin}")
    for ref, signal in (("C515", "ETH_XI"), ("C516", "ETH_XO")):
        expect_value_prefix(components, ref, "12p C0G 5%", f"{ref} Ethernet crystal load")
        expect(net(components, ref, "1"), loc(signal), f"{ref} signal pin")
        expect(net(components, ref, "2"), "GND", f"{ref} ground pin")

    for ref, nets in (
        ("U501", ("ETH_MDI0_P", "ETH_MDI0_N", "ETH_MDI1_P", "ETH_MDI1_N")),
        ("U502", ("ETH_MDI2_P", "ETH_MDI2_N", "ETH_MDI3_P", "ETH_MDI3_N")),
    ):
        for pin, name in zip(("1", "2", "4", "5"), nets):
            expect(net(components, ref, pin), loc(name), f"{ref} protected pair pin {pin}")
        for pin in ("3", "8"):
            expect(net(components, ref, pin), "GND", f"{ref} ESD ground pin {pin}")
        for pin in ("6", "7", "9", "10"):
            expect_unconnected(components, ref, pin)

    expect(comp(components, "J500").footprint,
           "ducktop2:JXD1-1022NL_MidMount", "mid-mount integrated-magnetics RJ45 footprint")
    jack_pins = {
        "1": "ETH_MDI0_P", "2": "ETH_MDI0_N", "3": "ETH_CT",
        "4": "ETH_MDI1_P", "5": "ETH_MDI1_N", "6": "ETH_CT",
        "7": "ETH_MDI2_P", "8": "ETH_MDI2_N", "9": "ETH_CT",
        "10": "ETH_MDI3_P", "11": "ETH_MDI3_N", "12": "ETH_CT",
        "13": "ETH_LED_ACT_N", "14": "ETH_LED_ACT_A",
        "15": "ETH_LED_1000_N", "16": "ETH_LED_1000_A", "SH": "ETH_CHASSIS",
    }
    for pin, name in jack_pins.items():
        expect(net(components, "J500", pin), loc(name), f"J500 pin {pin}")

    for ref, value, pin1, pin2 in (
        ("R500", "1M", loc("ETH_XI"), loc("ETH_XO")),
        ("R501", "2.49k", loc("ETH_RSET"), "GND"),
        ("R502", "10k", "/PCIE_3V3", loc("GBE_ISOLATE_N")),
        ("R503", "10k", "/PCIE_3V3", "/PCIE_WAKE_N"),
        ("R504", "470R", "/PCIE_3V3", loc("ETH_LED_ACT_A")),
        ("R505", "470R", "/PCIE_3V3", loc("ETH_LED_1000_A")),
        ("C513", "100n", loc("ETH_CT"), "GND"),
        ("C514", "1n", loc("ETH_CHASSIS"), "GND"),
        ("R506", "DNP 0R", loc("ETH_CHASSIS"), "GND"),
    ):
        expect_value_prefix(components, ref, value, f"{ref} Ethernet value")
        expect(net(components, ref, "1"), pin1, f"{ref} Ethernet pin 1")
        expect(net(components, ref, "2"), pin2, f"{ref} Ethernet pin 2")
    expect(prop(components, "C514", "Manufacturer"), "KEMET",
           "Ethernet chassis capacitor manufacturer")
    expect(prop(components, "C514", "MPN"), "C1812C102KGRACTU",
           "Ethernet chassis capacitor MPN")
    dnp, exclude_bom = component_flags()
    if "R506" not in dnp or "R506" not in exclude_bom:
        fail("R506 direct chassis bond option must be DNP and excluded from BOM")


def check_maker_mcu(components):
    expect(net(components, "F900", "1"), "/SYS_5V", "maker 5V fuse input")
    expect(net(components, "F900", "2"), local_net("Maker MCU", "MAKER_5V_CORE"), "maker 5V core fuse output")
    expect_value_prefix(components, "F900", "1.1A hold PPTC", "maker-domain PPTC")
    expect(net(components, "R900", "1"), local_net("Maker MCU", "MAKER_USB_ISO_DP"), "maker USB DP isolated side")
    expect(net(components, "R901", "1"), local_net("Maker MCU", "MAKER_USB_ISO_DM"), "maker USB DM isolated side")
    expect_value_prefix(components, "R900", "27R", "maker USB DP termination")
    expect_value_prefix(components, "R901", "27R", "maker USB DM termination")

    rp = comp(components, "U901")
    expect(rp.footprint, "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm_ThermalVias", "U901 RP2350A footprint")
    expect(comp(components, "U902").footprint, "Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm", "U902 flash footprint")
    expect(comp(components, "U903").footprint, "Package_SON:Texas_VSON-HR-8_1.5x2mm_P0.5mm", "U903 TPS62821 footprint")
    expect_value_prefix(components, "U902", "W25Q32RVXHJQ", "maker flash value")
    expect_value_prefix(components, "U903", "TPS62821DLC", "maker 3V3 regulator value")
    tps62821 = {
        "1": "MAKER_5V_CORE", "2": "MAKER_3V3_FB", "3": "GND",
        "5": "GND", "6": "MAKER_3V3_SW", "7": "MAKER_5V_CORE",
    }
    for pin, name in tps62821.items():
        expected = "GND" if name == "GND" else local_net("Maker MCU", name)
        expect(net(components, "U903", pin), expected, f"U903 TPS62821 pin {pin}")
    for pin in ("4", "8"):
        expect_unconnected(components, "U903", pin)
    expect(comp(components, "L900").footprint, "ducktop2:TDK_TFM201610", "TPS62821 inductor footprint")
    expect_value_prefix(components, "L900", "470nH TDK TFM201610ALM-R47MTAA", "TPS62821 inductor value")
    expect(net(components, "L900", "1"), local_net("Maker MCU", "MAKER_3V3_SW"), "TPS62821 inductor switch side")
    expect(net(components, "L900", "2"), local_net("Maker MCU", "MAKER_3V3_CORE"), "TPS62821 inductor output side")
    expect_value_prefix(components, "C900", "4.7u 6.3V X7R", "TPS62821 input capacitance")
    expect(net(components, "C900", "1"), local_net("Maker MCU", "MAKER_5V_CORE"), "TPS62821 input capacitor rail")
    for ref in ("C901", "C921"):
        expect_value_prefix(components, ref, "10u 10V X7R", f"{ref} TPS62821 output capacitance")
        expect(net(components, ref, "1"), local_net("Maker MCU", "MAKER_3V3_CORE"), f"{ref} TPS62821 output rail")
    for ref in ("C900", "C901", "C921"):
        expect(comp(components, ref).footprint, "Capacitor_SMD:C_0603_1608Metric", f"{ref} TPS62821 capacitor package")
        expect(net(components, ref, "2"), "GND", f"{ref} return")
    expect_value_prefix(components, "R902", "450k 1%", "TPS62821 high feedback resistor")
    expect_value_prefix(components, "R920", "100k 1%", "TPS62821 low feedback resistor")
    expect_value_prefix(components, "C923", "120p 50V C0G", "TPS62821 feed-forward capacitor")
    for ref in ("R902", "C923"):
        expect(net(components, ref, "1"), local_net("Maker MCU", "MAKER_3V3_CORE"), f"{ref} feedback source")
        expect(net(components, ref, "2"), local_net("Maker MCU", "MAKER_3V3_FB"), f"{ref} feedback node")
    expect(net(components, "R920", "1"), local_net("Maker MCU", "MAKER_3V3_FB"), "TPS62821 feedback low node")
    expect(net(components, "R920", "2"), "GND", "TPS62821 feedback return")

    for ref, rail_in, rail_out, ilim, resistor in (
        ("U904", "MAKER_5V_CORE", "J901_5V_OUT", "MAKER_5V_ILIM", "R921"),
        ("U905", "MAKER_3V3_CORE", "J901_3V3_OUT", "MAKER_3V3_ILIM", "R922"),
    ):
        expect(comp(components, ref).footprint, "Package_TO_SOT_SMD:SOT-23-6", f"{ref} TPS2553D footprint")
        expect_value_prefix(components, ref, "TPS2553DDBVR", f"{ref} reverse-blocked header switch")
        expect(net(components, ref, "1"), local_net("Maker MCU", rail_in), f"{ref} input")
        expect(net(components, ref, "2"), "GND", f"{ref} ground")
        expect(net(components, ref, "3"), local_net("Maker MCU", "MAKER_PWR_EN"), f"{ref} firmware enable")
        expect(net(components, ref, "4"), local_net("Maker MCU", "MAKER_PWR_FAULT_N"), f"{ref} active-low fault")
        expect(net(components, ref, "5"), local_net("Maker MCU", ilim), f"{ref} current-limit node")
        expect(net(components, ref, "6"), local_net("Maker MCU", rail_out), f"{ref} protected output")
        expect(net(components, resistor, "1"), local_net("Maker MCU", ilim), f"{resistor} current-limit node")
        expect(net(components, resistor, "2"), "GND", f"{resistor} current-limit return")
    expect_value_prefix(components, "R921", "88.7k 1%", "5V header current limit")
    expect_value_prefix(components, "R922", "226k 1%", "3V3 header current limit")
    expect_value_prefix(components, "R923", "100k", "maker header default-off pull-down")
    expect(net(components, "R923", "1"), local_net("Maker MCU", "MAKER_PWR_EN"), "maker header enable bias")
    expect(net(components, "R923", "2"), "GND", "maker header enable bias return")
    expect_value_prefix(components, "R924", "10k", "maker header shared fault pull-up")
    expect(net(components, "R924", "1"), local_net("Maker MCU", "MAKER_3V3_CORE"), "maker fault pull-up rail")
    expect(net(components, "R924", "2"), local_net("Maker MCU", "MAKER_PWR_FAULT_N"), "maker fault signal")

    rp_pins = {
        "1": "MAKER_3V3_CORE", "2": "MAKER_UART_TX", "3": "MAKER_UART_RX",
        "4": "MAKER_I2C_SDA", "5": "MAKER_I2C_SCL", "6": "MAKER_1V1",
        "7": "MAKER_GPIO0", "8": "MAKER_GPIO1", "9": "MAKER_GPIO2",
        "10": "MAKER_GPIO3", "11": "MAKER_3V3_CORE", "12": "MAKER_GPIO4",
        "13": "MAKER_GPIO5", "14": "MAKER_GPIO6", "15": "MAKER_GPIO7",
        "16": "MAKER_GPIO8", "17": "MAKER_GPIO9", "18": "MAKER_GPIO10",
        "19": "MAKER_GPIO11", "20": "MAKER_3V3_CORE", "21": "MAKER_XIN",
        "22": "MAKER_XOUT", "23": "MAKER_1V1", "24": "MAKER_SWCLK_MCU",
        "25": "MAKER_SWDIO_MCU", "26": "MAKER_RUN_N", "27": "MAKER_SPI_MISO",
        "28": "MAKER_SPI_CS_N", "29": "MAKER_SPI_SCK", "30": "MAKER_3V3_CORE",
        "31": "MAKER_SPI_MOSI", "32": "MAKER_GPIO12", "33": "MAKER_GPIO13",
        "34": "MAKER_GPIO14", "35": "MAKER_SMPS_PS", "36": "MAKER_HOST_ACTIVE_N",
        "37": "MAKER_PWR_FAULT_N", "38": "MAKER_3V3_CORE", "39": "MAKER_1V1",
        "40": "MAKER_ADC0", "41": "MAKER_ADC1", "42": "MAKER_ADC2",
        "43": "MAKER_PWR_EN", "44": "MAKER_ADC_AVDD", "45": "MAKER_3V3_CORE",
        "46": "MAKER_VREG_AVDD", "48": "MAKER_VREG_LX", "49": "MAKER_3V3_CORE",
        "50": "MAKER_1V1", "51": "MAKER_USB_DM_MCU", "52": "MAKER_USB_DP_MCU",
        "53": "MAKER_3V3_CORE", "54": "MAKER_3V3_CORE", "55": "MAKER_QSPI_SD3",
        "56": "MAKER_QSPI_SCLK", "57": "MAKER_QSPI_SD0", "58": "MAKER_QSPI_SD2",
        "59": "MAKER_QSPI_SD1", "60": "MAKER_QSPI_SS",
    }
    for pin, name in rp_pins.items():
        expect(net(components, "U901", pin), local_net("Maker MCU", name), f"U901 RP2350A pin {pin}")
    for pin in ("47", "61"):
        expect(net(components, "U901", pin), "GND", f"U901 RP2350A ground {pin}")

    flash = {"1": "MAKER_QSPI_SS", "2": "MAKER_QSPI_SD1", "3": "MAKER_QSPI_SD2",
             "5": "MAKER_QSPI_SD0", "6": "MAKER_QSPI_SCLK", "7": "MAKER_QSPI_SD3",
             "8": "MAKER_3V3_CORE"}
    for pin, name in flash.items():
        expect(net(components, "U902", pin), local_net("Maker MCU", name), f"U902 flash pin {pin}")
    for pin in ("4", "9"):
        expect(net(components, "U902", pin), "GND", f"U902 flash ground {pin}")

    expect(net(components, "L901", "1"), local_net("Maker MCU", "MAKER_1V1"), "RP2350 core inductor output")
    expect(net(components, "L901", "2"), local_net("Maker MCU", "MAKER_VREG_LX"), "RP2350 core inductor switch node")
    expect(net(components, "R907", "1"), local_net("Maker MCU", "MAKER_3V3_CORE"), "VREG_AVDD filter input")
    expect(net(components, "R907", "2"), local_net("Maker MCU", "MAKER_VREG_AVDD"), "VREG_AVDD filter output")
    expect_value_prefix(components, "R907", "33R", "VREG_AVDD filter value")
    expect(net(components, "R908", "2"), local_net("Maker MCU", "MAKER_ADC_VREF"), "ADC reference filter")
    expect(net(components, "R909", "2"), local_net("Maker MCU", "MAKER_ADC_AVDD"), "ADC supply filter")
    expect_value_prefix(components, "R908", "200R", "ADC reference filter value")
    expect_value_prefix(components, "R909", "1R", "ADC isolator value")
    expect(net(components, "C922", "1"), local_net("Maker MCU", "MAKER_ADC_VREF"), "ADC reference filter capacitor")
    expect(net(components, "C922", "2"), "GND", "ADC reference filter capacitor ground")
    expect_value_prefix(components, "C922", "100n", "ADC reference filter capacitor value")
    expect(comp(components, "U906").footprint, "Package_SO:TSSOP-10_3x3mm_P0.5mm", "maker USB isolation switch footprint")
    for pin, want in {
        "1": "GND", "2": "/MAKER_USB_DP", "4": local_net("Maker MCU", "MAKER_USB_ISO_DP"),
        "5": "GND", "6": local_net("Maker MCU", "MAKER_USB_ISO_DM"), "8": "/MAKER_USB_DM",
        "9": local_net("Maker MCU", "MAKER_USB_OE_N"), "10": local_net("Maker MCU", "MAKER_3V3_CORE"),
    }.items():
        expect(net(components, "U906", pin), want, f"maker USB isolation U906 pin {pin}")
    for pin in ("3", "7"):
        expect_unconnected(components, "U906", pin)
    expect(net(components, "Q901", "1"), "/INTERNAL_USB_VBUS_VALID", "maker USB physical VBUS-valid interlock gate")
    expect(net(components, "Q901", "2"), "GND", "maker USB interlock return")
    expect(net(components, "Q901", "3"), local_net("Maker MCU", "MAKER_USB_OE_N"), "maker USB interlock drain")
    expect(net(components, "R925", "1"), local_net("Maker MCU", "MAKER_3V3_CORE"), "maker USB default-disconnect rail")
    expect(net(components, "R925", "2"), local_net("Maker MCU", "MAKER_USB_OE_N"), "maker USB default-disconnect control")
    for obsolete in ("Q902", "R926"):
        if obsolete in components:
            fail(f"obsolete status-proxy maker USB component {obsolete} remains")
    expect(net(components, "R910", "1"), local_net("Maker MCU", "MAKER_USB_OE_N"), "maker active-low host source")
    expect(net(components, "R910", "2"), local_net("Maker MCU", "MAKER_HOST_ACTIVE_N"), "maker active-low host input")
    expect(net(components, "R911", "1"), local_net("Maker MCU", "MAKER_3V3_CORE"), "maker host-disconnected pull-up")
    expect(net(components, "R911", "2"), local_net("Maker MCU", "MAKER_HOST_ACTIVE_N"), "maker host-disconnected input bias")
    for obsolete in ("Q900", "R912", "R913", "R914", "R915", "C920", "D900"):
        if obsolete in components:
            fail(f"obsolete maker monitor/LED part {obsolete} is still present")

    protected_signals = [
        "MAKER_BOOT_N", "MAKER_RUN_N", "MAKER_SWDIO", "MAKER_SWCLK",
        "MAKER_UART_TX", "MAKER_UART_RX", "MAKER_I2C_SCL", "MAKER_I2C_SDA",
        "MAKER_SPI_SCK", "MAKER_SPI_MISO", "MAKER_SPI_MOSI", "MAKER_SPI_CS_N",
        *[f"MAKER_GPIO{i}" for i in range(15)],
        "MAKER_ADC0", "MAKER_ADC1", "MAKER_ADC2",
    ]
    loc = lambda name: local_net("Maker MCU", name)
    exposed = lambda name: loc(f"J901_{name}")
    isolated = lambda name: loc(f"J901_{name}_ISO")

    # Powered-off protection boundary: the RP2350 side cannot be driven from
    # J901 unless the maker 3V3 rail is valid and Q903 releases every /OE pin.
    for bank in range(4):
        ref = f"U{910 + bank}"
        expect_contains(comp(components, ref).value, "SN74CB3T3245PWR",
                        f"{ref} powered-off maker isolator")
        expect(prop(components, ref, "MPN"), "SN74CB3T3245PWR",
               f"{ref} exact isolator MPN")
        expect_unconnected(components, ref, "1")
        expect(net(components, ref, "10"), "GND", f"{ref} ground")
        expect(net(components, ref, "19"), loc("MAKER_HEADER_OE_N"), f"{ref} common disable")
        expect(net(components, ref, "20"), loc("MAKER_3V3_CORE"), f"{ref} supply")
        for channel in range(8):
            index = bank * 8 + channel
            a_pin, b_pin = str(2 + channel), str(18 - channel)
            if index < len(protected_signals):
                signal = protected_signals[index]
                expect(net(components, ref, a_pin), loc(signal), f"{ref} A{channel + 1}")
                expect(net(components, ref, b_pin), isolated(signal), f"{ref} B{channel + 1}")
            else:
                expect_unconnected(components, ref, a_pin)
                expect_unconnected(components, ref, b_pin)
        cref = f"C{930 + bank}"
        expect_value_prefix(components, cref, "100n", f"{ref} local bypass")
        expect(net(components, cref, "1"), loc("MAKER_3V3_CORE"), f"{cref} rail")
        expect(net(components, cref, "2"), "GND", f"{cref} return")

    for index, signal in enumerate(protected_signals):
        ref = f"R{932 + index}"
        expect_value_prefix(components, ref, "330R", f"{ref} maker fault limit")
        expect(net(components, ref, "1"), isolated(signal), f"{ref} protected side")
        expect(net(components, ref, "2"), exposed(signal), f"{ref} connector side")

    esd_signal_pins = ("1", "2", "4", "5")
    for bank in range(8):
        ref = f"U{914 + bank}"
        expect_contains(comp(components, ref).value, "TPD4E05U06DQAR",
                        f"{ref} maker connector ESD")
        expect(prop(components, ref, "MPN"), "TPD4E05U06DQAR",
               f"{ref} exact ESD MPN")
        for pin in ("3", "8"):
            expect(net(components, ref, pin), "GND", f"{ref} ESD ground {pin}")
        for pin in ("6", "7", "9", "10"):
            expect_unconnected(components, ref, pin)
        for channel, pin in enumerate(esd_signal_pins):
            index = bank * 4 + channel
            if index < len(protected_signals):
                expect(net(components, ref, pin), exposed(protected_signals[index]),
                       f"{ref} protected connector signal {pin}")
            else:
                expect_unconnected(components, ref, pin)

    for pin, want in {
        "1": loc("MAKER_HEADER_VALID"), "2": "GND", "3": loc("MAKER_3V3_CORE"),
    }.items():
        expect(net(components, "U922", pin), want, f"maker header supervisor pin {pin}")
    expect_contains(comp(components, "U922").value, "TLV803EA29RDBZR",
                    "maker header rail supervisor")
    expect_value_prefix(components, "R931", "10k", "maker header supervisor pull-up")
    expect(net(components, "R931", "1"), loc("MAKER_3V3_CORE"), "maker supervisor pull-up rail")
    expect(net(components, "R931", "2"), loc("MAKER_HEADER_VALID"), "maker supervisor output")
    for pin, want in {
        "1": loc("MAKER_HEADER_VALID"), "2": "GND", "3": loc("MAKER_HEADER_OE_N"),
    }.items():
        expect(net(components, "Q903", pin), want, f"maker isolation gate pin {pin}")
    expect_value_prefix(components, "R930", "47k", "maker isolation default-off pull-up")
    expect(net(components, "R930", "1"), loc("MAKER_3V3_CORE"), "maker isolation pull-up rail")
    expect(net(components, "R930", "2"), loc("MAKER_HEADER_OE_N"), "maker isolation disable")

    header = {
        "1": "GND", "2": "J901_5V_OUT", "3": "GND", "4": "J901_3V3_OUT",
        **{str(5 + i): f"J901_{name}" for i, name in enumerate(protected_signals[:27])},
        "33": "GND", "34": "GND",
        "35": "J901_MAKER_ADC0", "36": "J901_MAKER_ADC1",
        "37": "J901_3V3_OUT", "38": "GND",
        "39": "J901_MAKER_ADC2", "40": "GND",
    }
    for pin, name in header.items():
        expected = "GND" if name == "GND" else loc(name)
        expect(net(components, "J901", pin), expected, f"J901 maker header pin {pin}")
    expect_unconnected(components, "J901", "32")
    expect(comp(components, "J901").footprint,
           "Connector_JST:JST_PUD_B40B-PUDSS_2x20_P2.00mm_Vertical",
           "maker header exact keyed JST PUD footprint")
    expect(prop(components, "J901", "MPN"), "B40B-PUDSS", "maker header exact MPN")
    expect(prop(components, "J901", "MatingHousing"), "PUDP-40V-S",
           "maker header mating housing")
    for ref in ("SW900", "SW901"):
        expect(prop(components, ref, "MPN"), "B3S-1000", f"{ref} exact switch MPN")
    expect(net(components, "R917", "1"), local_net("Maker MCU", "MAKER_3V3_CORE"),
           "maker SWD VTref source")
    expect(net(components, "R917", "2"), local_net("Maker MCU", "MAKER_SWD_VTREF"),
           "maker SWD VTref isolated target")
    expect_value_prefix(components, "R917", "0R", "maker SWD VTref link")
    expect(comp(components, "J902").footprint,
           "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical", "maker SWD footprint")
    for pin, want in {
        "1": local_net("Maker MCU", "MAKER_SWD_VTREF"),
        "2": local_net("Maker MCU", "MAKER_SWDIO"),
        "3": local_net("Maker MCU", "MAKER_RUN_N"),
        "4": local_net("Maker MCU", "MAKER_SWCLK"), "5": "GND",
    }.items():
        expect(net(components, "J902", pin), want, f"maker TC2030 pin {pin}")
    expect_unconnected(components, "J902", "6")
    _dnp, exclude_bom = component_flags()
    if "J902" not in exclude_bom:
        fail("J902 is a PCB copper programming target and must be excluded from BOM")
    expect(prop(components, "J902", "ProcurementClass"), "PCB copper test feature",
           "maker TC2030 procurement class")


def check_pcb_attribute_parity(components, fps):
    for ref in sorted(set(components) & set(fps)):
        actual = sync.footprint_attribute_flags(fps[ref].text)
        for flag in ("exclude_from_bom", "dnp"):
            wanted = flag in components[ref].properties
            if (flag in actual) != wanted:
                fail(
                    f"{ref} PCB {flag}={flag in actual} does not match "
                    f"schematic {flag}={wanted}"
                )


def check_main_pcb_contract(components, fps, pcb_text):
    check_pcb_attribute_parity(components, fps)
    if "J900" in fps:
        fail("obsolete Pico 2 module footprint J900 must not be on the main PCB")
    expect(fps["U901"].footprint, "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm_ThermalVias", "main PCB integrated RP2350 footprint")
    expect(fps["U902"].footprint, "Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm", "main PCB integrated flash footprint")
    expect(fps["U903"].footprint, "Package_SON:Texas_VSON-HR-8_1.5x2mm_P0.5mm", "main PCB maker 3V3 regulator footprint")
    for ref in ("J320", "J321", "C320", "C321"):
        if ref in fps:
            fail(f"{ref} keyboard daughterboard-only footprint must not be on main PCB")
    for ref in fps:
        matrix_match = re.fullmatch(r"(?:SW|D)(\d+)", ref)
        if matrix_match and 320 <= int(matrix_match.group(1)) <= 384:
            fail(f"keyboard matrix footprint leaked onto main PCB: {ref}")
    for ref in ("J21", "J22", "J23"):
        x, _, rot = at_tuple(fps[ref].text)
        rot %= 360
        if x > 10 or abs(rot - 270) > 0.01:
            fail(f"{ref} should face left edge; got x={x}, rot={rot}")
    for ref in ("J11", "J12"):
        x, _, rot = at_tuple(fps[ref].text)
        rot %= 360
        if x < 348 or abs(rot - 90) > 0.01:
            fail(f"{ref} should face right edge; got x={x}, rot={rot}")
    for layer in ('(0 "F.Cu"', '(4 "In1.Cu"', '(6 "In2.Cu"', '(8 "In3.Cu"', '(10 "In4.Cu"', '(2 "B.Cu"'):
        if layer not in pcb_text:
            fail(f"missing expected 6-layer stack entry {layer}")


def run_current_drc() -> Path:
    CURRENT_DRC.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(sync.KICAD_CLI),
            "pcb", "drc",
            "--format", "json",
            "--output", str(CURRENT_DRC),
            str(PCB),
        ],
        cwd=ROOT,
        check=True,
    )
    return CURRENT_DRC


def check_drc_fatal_categories(report: Path):
    data = json.loads(report.read_text())
    for bad in ("shorting_items", "items_not_allowed", "invalid_outline"):
        count = sum(1 for v in data.get("violations", []) if v.get("type") == bad)
        if count:
            fail(f"DRC fatal category {bad} has {count} violation(s) in {report.name}")
    for violation in data.get("violations", []):
        if violation.get("type") != "copper_edge_clearance":
            continue
        descriptions = " ".join(
            item.get("description", "") for item in violation.get("items", [])
        )
        fail(f"unexpected mainboard copper-to-edge violation: {descriptions}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schematic-only",
        action="store_true",
        help="run generated-netlist contracts without inspecting the in-progress PCB",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sync.export_netlist()
    components = sync.parse_netlist()
    pin_names = component_pin_names()
    fps = pcb_text = None
    if not args.schematic_only:
        fps, pcb_text = footprint_map()
    check_oled(components, fps)
    check_custom_footprint_sources()
    check_active_custom_footprint_pin_sets(components)
    check_battery_and_charger(components)
    check_dnp_metadata(components)
    check_ec_core(components)
    check_mu_carrier(components, pin_names)
    check_five_port_usb_c_architecture(components)
    check_external_hdmi_path(components)
    check_internal_services(components)
    check_keyboard_interface(components)
    check_optional_radio_interface(components)
    check_system_audio(components)
    check_ethernet(components)
    check_maker_mcu(components)
    if args.schematic_only:
        print("ducktop2 schematic design contract checks OK")
    else:
        check_main_pcb_contract(components, fps, pcb_text)
        check_drc_fatal_categories(run_current_drc())
        print("ducktop2 full design contract checks OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
