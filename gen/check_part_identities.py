#!/usr/bin/env python3
"""Check known passive order codes on fresh exports from all six boards."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from check_release_candidate import find_kicad_cli
from part_identity import decode, identity_errors

ROOT = Path(__file__).resolve().parents[1]
SCHEMATICS = {
    "center": "ducktop2.kicad_sch",
    "left_io": "left_io/left_io.kicad_sch",
    "right_io": "right_io/right_io.kicad_sch",
    "bms": "bms/bms.kicad_sch",
    "keyboard": "keyboard/12_keyboard_daughterboard.kicad_sch",
    "radio": "radio_daughterboard/radio_daughterboard.kicad_sch",
}


def inspect_netlist(path):
    matched, errors, unverified, missing = [], [], [], []
    for comp in ET.parse(path).getroot().findall("./components/comp"):
        ref = comp.get("ref")
        flags = {p.get("name") for p in comp.findall("property")}
        if "exclude_from_bom" in flags or "dnp" in flags:
            continue
        fields = {p.get("name"): p.text for p in comp.findall("./fields/field")}
        fields.update({p.get("name"): p.get("value") for p in comp.findall("property")
                       if p.get("value")})
        mpn = fields.get("MPN") or ""
        row = {"ref": ref, "value": comp.findtext("value") or "", "mpn": mpn,
               "footprint": comp.findtext("footprint") or ""}
        if not mpn:
            missing.append(row)
        elif decode(mpn) is None:
            unverified.append(row)
        else:
            failures = identity_errors(row["value"], row["footprint"], mpn)
            if failures:
                errors.append(dict(row, errors=failures))
            else:
                matched.append(ref)
    return {"matched_known_codes": matched, "errors": errors,
            "unverified_order_codes": unverified, "missing_order_codes": missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=[*SCHEMATICS, "all"], default="all")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "verification/generated/part-identities")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in SCHEMATICS if args.project == "all" else [args.project]:
        sch = ROOT / SCHEMATICS[name]
        xml = output / f"{name}.xml"
        subprocess.run([find_kicad_cli(), "sch", "export", "netlist", "--format", "kicadxml",
                        "--output", str(xml), str(sch)], cwd=sch.parent, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result = inspect_netlist(xml)
        result["netlist_sha256"] = hashlib.sha256(xml.read_bytes()).hexdigest()
        results[name] = result
        print(f"{name}: {len(result['matched_known_codes'])} known codes match, "
              f"{len(result['errors'])} mismatches, "
              f"{len(result['unverified_order_codes'])} need another identity check, "
              f"{len(result['missing_order_codes'])} have no order code")
        for row in result["errors"]:
            print(row["ref"], row["mpn"], "; ".join(row["errors"]))
    (output / "identities.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(any(result["errors"] for result in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
