#!/usr/bin/env python3
"""Verify the released Ducktop2 TPS25751A policy and local TI output."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "ducktop2_dual_role_config.json"
MANIFEST = ROOT / "release_manifest.json"
GENERATED = ROOT / "generated"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_map(document: dict) -> dict[int, list[int]]:
    entries = document["configuration"]["data"]["selected_ace"]
    return {entry["register"]: entry["data"] for entry in entries}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def verify_policy(document: dict, label: str, errors: list[str]) -> None:
    answers = document["questionnaire"]["answers"]
    registers = register_map(document)

    require(answers[1] == 1, f"{label}: power policy is not DRP/no-BQ", errors)
    require(answers[6] == 1, f"{label}: data role is not host-only", errors)
    require(registers[41] == [112, 193, 129, 0, 0],
            f"{label}: Port Control (0x29) drifted", errors)
    require(registers[50][:8] == [1, 168, 42, 90, 144, 1, 6, 44],
            f"{label}: source PDO is not exactly 5 V / 900 mA", errors)

    io_config = registers[92]
    require(io_config[0] == 219, f"{label}: GPIO output-enable map drifted", errors)
    require(io_config[32] == 16, f"{label}: GPIO4 inversion is missing", errors)
    require(io_config[40] == 29, f"{label}: GPIO4 is not UFP_DFP event 29", errors)
    require(io_config[42] == 3, f"{label}: GPIO6 is not orientation event 3", errors)
    require(io_config[43] == 61, f"{label}: GPIO7 is not data-mux event 61", errors)
    require(registers[119][13] == 5, f"{label}: source power is not 5 W encoded", errors)
    require(registers[120][2] == 5, f"{label}: product source power drifted", errors)


def xml_value(root: ET.Element, tag: str) -> ET.Element | None:
    return root.find(f".//{{http://usb.org/VendorInfoFile.xsd}}{tag}")


def verify_vif(path: Path, errors: list[str]) -> None:
    root = ET.parse(path).getroot()

    expected = {
        "PD_Port_Type": ("4", "DRP"),
        "RP_Value": ("0", "Default"),
        "Type_C_Can_Act_As_Host": ("true", ""),
        "Type_C_Can_Act_As_Device": ("false", ""),
        "Data_Capable_As_USB_Host_SOP": ("true", ""),
        "Data_Capable_As_USB_Device_SOP": ("false", ""),
        "PD_Power_As_Source": ("4500", "4500 mW"),
        "Src_PDO_Voltage": ("100", "5000 mV"),
        "Src_PDO_Max_Current": ("90", "900 mA"),
    }
    for tag, (value, text) in expected.items():
        element = xml_value(root, tag)
        require(element is not None, f"VIF: missing {tag}", errors)
        if element is None:
            continue
        if value is not None:
            require(element.get("value") == value,
                    f"VIF: {tag} value is {element.get('value')!r}, expected {value!r}", errors)
        require((element.text or "").strip() == text,
                f"VIF: {tag} text is {(element.text or '').strip()!r}, expected {text!r}", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-generated", action="store_true",
                        help="also require and hash-check local TI output")
    args = parser.parse_args()

    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text())
    source = json.loads(SOURCE.read_text())

    require(sha256(SOURCE) == manifest["source"]["sha256"],
            "tracked source hash does not match release_manifest.json", errors)
    verify_policy(source, "source", errors)

    generated_entries = manifest["generated"]
    if args.require_generated:
        for name, metadata in generated_entries.items():
            path = GENERATED / name
            require(path.is_file(), f"generated file is missing: {name}", errors)
            if not path.is_file():
                continue
            require(sha256(path) == metadata["sha256"],
                    f"generated hash mismatch: {name}", errors)
            if "bytes" in metadata:
                require(path.stat().st_size == metadata["bytes"],
                        f"generated size mismatch: {name}", errors)

        raw_path = GENERATED / "ducktop2_dual_role_raw.json"
        vif_path = GENERATED / "ducktop2_dual_role_vif.xml"
        if raw_path.is_file():
            verify_policy(json.loads(raw_path.read_text()), "TI export", errors)
        if vif_path.is_file():
            verify_vif(vif_path, errors)

    if errors:
        print("TPS25751A CONFIGURATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("TPS25751A configuration OK")
    print("- 5 V / 900 mA source, default Rp")
    print("- 5/9/15 V sink, DRP power policy")
    print("- host-only USB data with GPIO4/GPIO7 qualified enable")
    if args.require_generated:
        print("- TI output hashes and VIF match release_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
