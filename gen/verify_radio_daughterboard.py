#!/usr/bin/env python3
"""Verify the removable Ducktop2 radio/GNSS/audio daughterboard."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import sync_main_pcb_from_netlist as sync


ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = ROOT / "radio_daughterboard"
SCHEMATIC = BOARD_DIR / "radio_daughterboard.kicad_sch"
BOARD = BOARD_DIR / "radio_daughterboard.kicad_pcb"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


class CheckFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise CheckFailure(message)


def expect(got: str | None, want: str, label: str) -> None:
    if got != want:
        fail(f"{label}: expected {want!r}, got {got!r}")


def component(components, ref):
    if ref not in components:
        fail(f"missing radio daughterboard component {ref}")
    return components[ref]


def net(components, ref: str, pin: str | int) -> str | None:
    return component(components, ref).pin_nets.get(str(pin))


def prop(components, ref: str, name: str) -> str | None:
    return component(components, ref).properties.get(name)


def expect_value(components, ref: str, prefix: str) -> None:
    value = component(components, ref).value
    if not value.startswith(prefix):
        fail(f"{ref} value: expected prefix {prefix!r}, got {value!r}")


def expect_unconnected(components, ref: str, pin: str | int) -> None:
    actual = net(components, ref, pin)
    if actual is not None and not actual.startswith("unconnected-("):
        fail(f"{ref} pin {pin}: expected unconnected, got {actual!r}")


def local(sheet: str, name: str) -> str:
    return f"/{sheet}/{name}"


def collect_erc_items(path: Path) -> list[dict]:
    result: list[dict] = []

    def walk(value):
        if isinstance(value, dict):
            if "severity" in value and ("description" in value or "message" in value):
                result.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(json.loads(path.read_text(encoding="utf-8")))
    return result


def export_and_parse(temp_dir: Path):
    erc = temp_dir / "radio_erc.json"
    netlist = temp_dir / "radio.net"
    subprocess.run(
        [str(KICAD_CLI), "sch", "erc", "--format", "json", "--output", str(erc), str(SCHEMATIC)],
        cwd=ROOT,
        check=True,
    )
    errors = [item for item in collect_erc_items(erc) if item.get("severity") == "error"]
    if errors:
        fail(f"radio daughterboard ERC reported {len(errors)} error(s)")
    subprocess.run(
        [str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadxml", "--output", str(netlist), str(SCHEMATIC)],
        cwd=ROOT,
        check=True,
    )
    sync.NETLIST = netlist
    return sync.parse_netlist(), len(collect_erc_items(erc))


def check_connector_and_supply(components) -> None:
    expect(component(components, "J1").footprint,
           "Connector_Hirose_DF40:Hirose_DF40C(2.0)-60DS-0.4V_2x30_P0.4mm",
           "daughterboard DF40 receptacle footprint")
    expect(prop(components, "J1", "MPN"), "DF40C(2.0)-60DS-0.4V(51)", "daughterboard DF40 MPN")
    expect(prop(components, "J1", "MatingConnector"), "DF40C-60DP-0.4V(51)", "daughterboard mating connector")
    for pin in range(1, 9):
        expect(net(components, "J1", pin), "/RADIO_DB_5V", f"J1 shared 5V pin {pin}")
    for pin in (*range(9, 17), 21, 22, 27, 32, 37, 43, 44, *range(45, 61)):
        expect(net(components, "J1", pin), "GND", f"J1 ground pin {pin}")
    for pin, want in {
        1: "/RADIO_DB_5V", 2: "GND", 3: "/RADIO_DB_5V", 5: "/RADIO_DB_3V3",
    }.items():
        expect(net(components, "U1", pin), want, f"radio logic regulator pin {pin}")


def check_radio_controls(components) -> None:
    for ref, band in (("J70", "VHF"), ("J71", "UHF")):
        expect(net(components, ref, 5), local("VHF & UHF Radios", f"RADIO_{band}_PTT_LOCAL_N"), f"{band} PTT")
        expect(net(components, ref, 6), local("VHF & UHF Radios", f"RADIO_{band}_PD_LOCAL_N"), f"{band} PD")
        expect(net(components, ref, 16), local("VHF & UHF Radios", f"RADIO_{band}_UART_RXD"), f"{band} RXD")
        expect(net(components, ref, 17), local("VHF & UHF Radios", f"RADIO_{band}_UART_TXD"), f"{band} TXD")
    for ref, signal, rail in (
        ("R235", "RADIO_VHF_PTT_LOCAL_N", "RADIO_4V0"),
        ("R236", "RADIO_UHF_PTT_LOCAL_N", "RADIO_4V0"),
        ("R237", "RADIO_VHF_PD_LOCAL_N", "GND"),
        ("R238", "RADIO_UHF_PD_LOCAL_N", "GND"),
    ):
        expect_value(components, ref, "10k")
        expect(net(components, ref, 1), local("VHF & UHF Radios", signal), f"{ref} module control")
        expect(net(components, ref, 2), local("VHF & UHF Radios", rail) if rail != "GND" else "GND", f"{ref} default rail")
    for band, buffer, translator, series, bypass_a, bypass_b in (
        ("VHF", "U242", "U243", "R243", "C247", "C248"),
        ("UHF", "U252", "U253", "R261", "C257", "C258"),
    ):
        expect(net(components, buffer, 1), f"/RADIO_{band}_UART_TX", f"{band} UART buffer input")
        expect(net(components, buffer, 7), local("VHF & UHF Radios", f"RADIO_{band}_UART_RXD"), f"{band} UART buffer output")
        expect(prop(components, translator, "MPN"), "SN74LVC1T45DBVR", f"{band} TXD translator MPN")
        expect(net(components, translator, 3), local("VHF & UHF Radios", f"RADIO_{band}_UART_TXD"), f"{band} translator A")
        expect(net(components, translator, 4), local("VHF & UHF Radios", f"RADIO_{band}_UART_TXD_3V3"), f"{band} translator B")
        expect_value(components, series, "100R")
        expect(net(components, series, 1), local("VHF & UHF Radios", f"RADIO_{band}_UART_TXD_3V3"), f"{band} translated TXD")
        expect(net(components, series, 2), f"/RADIO_{band}_UART_RX", f"{band} host RX")
        for bypass, rail in ((bypass_a, "RADIO_4V0"), (bypass_b, "/RADIO_DB_3V3")):
            expected = local("VHF & UHF Radios", rail) if not rail.startswith("/") else rail
            expect(net(components, bypass, 1), expected, f"{bypass} bypass rail")
            expect(net(components, bypass, 2), "GND", f"{bypass} bypass return")
    for ref in ("R223", "R224", "R244", "R262"):
        if ref in components:
            fail(f"{ref} duplicates a mainboard signal default and can phantom-power RADIO_DB_3V3")


def check_gnss(components) -> None:
    for pin, want in {
        1: "GND",
        2: local("GNSS", "GNSS_UART_TX_LOCAL"),
        3: local("GNSS", "GNSS_UART_RX_LOCAL"),
        4: local("GNSS", "GNSS_PPS_LOCAL"),
        5: local("GNSS", "GNSS_EXTINT_LOCAL"),
        7: "/RADIO_DB_3V3",
        8: "/RADIO_DB_3V3",
        9: local("GNSS", "GNSS_RESET_LOCAL_N"),
        10: "GND",
        11: local("GNSS", "GNSS_RF_IN"),
        12: "GND",
    }.items():
        expect(net(components, "U40", pin), want, f"MAX-M10S pin {pin}")
    expect_unconnected(components, "U40", 6)
    for pin in (13, 14, 15, 16, 17, 18):
        expect_unconnected(components, "U40", pin)
    if "C43" in components:
        fail("C43 must be absent when MAX-M10S V_BCKP is intentionally unused")
    expect(net(components, "J42", 1), local("GNSS", "GNSS_RF_IN"), "GNSS U.FL center")
    expect(net(components, "J42", 2), "GND", "GNSS U.FL shield")


def check_rf_paths(components) -> None:
    for band, switch, blocks in (
        ("VHF", "U240", ("C270", "C271", "C272")),
        ("UHF", "U250", ("C273", "C274", "C275")),
    ):
        prefix = "VHF & UHF Radios"
        expect(net(components, switch, 28), local(prefix, f"{band}_RF_SWITCH_RFC"), f"{band} switch RFC")
        expect(net(components, switch, 2), local(prefix, f"{band}_RF_SWITCH_RF1"), f"{band} switch RF1")
        expect(net(components, switch, 23), local(prefix, f"{band}_RF_SWITCH_RF2"), f"{band} switch RF2")
        expected_paths = (
            (local(prefix, f"{band}_RF_FILTERED"), local(prefix, f"{band}_RF_SWITCH_RFC")),
            (local(prefix, f"{band}_RF_SWITCH_RF1"), local(prefix, f"{band}_ANT_EXTERNAL")),
            (local(prefix, f"{band}_RF_SWITCH_RF2"), local(prefix, f"{band}_ANT_ONBOARD")),
        )
        for ref, (net_a, net_b) in zip(blocks, expected_paths):
            expect(component(components, ref).footprint, "Capacitor_SMD:C_0603_1608Metric", f"{ref} RF footprint")
            expect(prop(components, ref, "MPN"), "600S101JT250XTV", f"{ref} exact RF capacitor")
            expect(net(components, ref, 1), net_a, f"{ref} RF side A")
            expect(net(components, ref, 2), net_b, f"{ref} RF side B")


def check_board(components, temp_dir: Path) -> tuple[int, int]:
    if not BOARD.exists():
        fail("radio daughterboard PCB is missing")
    board_text = BOARD.read_text(encoding="utf-8")
    footprints = {fp.ref: fp for fp in sync.footprints(board_text)}
    schematic_refs = {
        ref for ref, comp in components.items()
        if "exclude_from_board" not in comp.properties
    }
    if set(footprints) != schematic_refs:
        fail(f"radio PCB reference mismatch: missing={sorted(schematic_refs - set(footprints))}, extra={sorted(set(footprints) - schematic_refs)}")
    if '(layer "B.Cu")' not in footprints["J1"].text:
        fail("radio daughterboard J1 must be flipped to B.Cu to mate with mainboard J2300")
    for ref in ("J241", "J251"):
        _x, y, rotation = sync.at_tuple(footprints[ref].text)
        if abs(y - 20.0) > 0.01 or abs((rotation % 360.0) - 270.0) > 0.01:
            fail(
                f"{ref} SMA must face the radio-board rear edge; "
                f"got y={y}, rotation={rotation % 360.0}"
            )

    drc_path = temp_dir / "radio_drc.json"
    subprocess.run(
        [str(KICAD_CLI), "pcb", "drc", "--format", "json", "--output", str(drc_path), str(BOARD)],
        cwd=ROOT,
        check=True,
    )
    report = json.loads(drc_path.read_text(encoding="utf-8"))
    violations = report.get("violations", [])
    allowed_types = {"copper_edge_clearance", "silk_over_copper", "silk_overlap"}
    unexpected = [item for item in violations if item.get("type") not in allowed_types]
    if unexpected:
        kinds = sorted({item.get("type", "unknown") for item in unexpected})
        fail(f"radio daughterboard has unexpected DRC classes: {kinds}")
    for item in violations:
        if item.get("type") != "copper_edge_clearance":
            continue
        descriptions = " ".join(child.get("description", "") for child in item.get("items", []))
        if not re.search(r"\bJ(?:241|251)\b", descriptions):
            fail(f"unexpected copper-to-edge finding outside edge-launch SMA connectors: {descriptions}")
    return len(violations), len(report.get("unconnected_items", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schematic-only", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="ducktop2_radio_verify_") as temp:
        temp_dir = Path(temp)
        components, warning_count = export_and_parse(temp_dir)
        check_connector_and_supply(components)
        check_radio_controls(components)
        check_gnss(components)
        check_rf_paths(components)
        if args.schematic_only:
            print(f"radio daughterboard contracts OK; ERC 0 errors, {warning_count} warning(s)")
        else:
            drc_count, unconnected_count = check_board(components, temp_dir)
            print(
                "radio daughterboard contracts OK; "
                f"ERC 0 errors, {warning_count} warning(s); "
                f"DRC {drc_count} classified placement warning(s), {unconnected_count} unrouted"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
