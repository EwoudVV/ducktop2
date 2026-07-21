#!/usr/bin/env python3
import compileall
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


GEN_DIR = Path(__file__).resolve().parent
PROJDIR = GEN_DIR.parent
KICAD_CLI_CANDIDATES = [
    os.environ.get("KICAD_CLI"),
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    "kicad-cli",
]
KICAD_FOOTPRINT_DIRS = [
    d for d in [
        os.environ.get("KICAD10_FOOTPRINT_DIR"),
        os.environ.get("KICAD_FOOTPRINT_DIR"),
        "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
        "/usr/share/kicad/footprints",
        "/usr/local/share/kicad/footprints",
    ]
    if d
]
EXPECTED_SHEETS = [
    "01_power_battery.kicad_sch",
    "02_ec_mcu.kicad_sch",
    "03_mu_carrier.kicad_sch",
    "04_usb_c_io.kicad_sch",
    "05_power_inputs.kicad_sch",
    "06_tcp0_external_hdmi.kicad_sch",
    "07_radio_oled_gps.kicad_sch",
    "08_internal_services.kicad_sch",
    "09_radio_daughterboard_interface.kicad_sch",
    "12_keyboard_interface.kicad_sch",
    "14_maker_mcu.kicad_sch",
    "15_system_audio.kicad_sch",
    "16_gigabit_ethernet.kicad_sch",
]

# These symbols are stock KiCad `extends` variants.  The generator deliberately
# embeds their complete flattened parent geometry so generated schematics are
# self-contained, which makes KiCad compare the flattened copy against the
# property-only stock child and report lib_symbol_mismatch.  Match the complete
# warning signature and reference so no unrelated warning can pass unnoticed.
ALLOWED_ERC_WARNINGS = Counter({
    (
        "warning", "lib_symbol_mismatch",
        "Symbol '74AHCT1G126' doesn't match copy in library '74xGxx'",
        ("Symbol U311 [74AHCT1G126]",),
    ): 1,
    (
        "warning", "lib_symbol_mismatch",
        "Symbol 'TPD4E05U06DQA' doesn't match copy in library 'Power_Protection'",
        ("Symbol U123 [TPD4E05U06DQA]",),
    ): 1,
    (
        "warning", "lib_symbol_mismatch",
        "Symbol 'TPD4E05U06DQA' doesn't match copy in library 'Power_Protection'",
        ("Symbol U133 [TPD4E05U06DQA]",),
    ): 1,
    (
        "warning", "lib_symbol_mismatch",
        "Symbol 'TPD4E05U06DQA' doesn't match copy in library 'Power_Protection'",
        ("Symbol U143 [TPD4E05U06DQA]",),
    ): 1,
    (
        "warning", "lib_symbol_mismatch",
        "Symbol 'TLV9061xDBV' doesn't match copy in library 'Amplifier_Operational'",
        ("Symbol U431 [TLV9061xDBV]",),
    ): 1,
})

# The user-facing maker header adds eight more instances of the same flattened
# stock TPD4E05U06 variant. Keep the allowlist reference-specific so a warning
# on any other symbol or failure mode still fails the check.
for ref in ("U914", "U915", "U916", "U917", "U918", "U919", "U920", "U921",
            "U1745", "U1765", "U1785"):
    ALLOWED_ERC_WARNINGS[(
        "warning", "lib_symbol_mismatch",
        "Symbol 'TPD4E05U06DQA' doesn't match copy in library 'Power_Protection'",
        (f"Symbol {ref} [TPD4E05U06DQA]",),
    )] += 1

# The TPS25751A unused GPIO/USB pins and the TUSB1142 GPIO-mode SDA strap are
# tied to ground exactly as required by their datasheets. KiCad reports the
# intentional connection only because the global GND PWR_FLAG is a power-output
# pin. Keep every allowed warning tied to one physical reference and pin.
for ref in ("U41", "U42"):
    for pin, name in (
        ("5", "GPIO0/LD1"), ("6", "GPIO1"), ("7", "GPIO2/LD2"),
        ("13", "GPIO11"), ("19", "GPIO3"),
        ("27", "GPIO5/USB_N"),
    ):
        ALLOWED_ERC_WARNINGS[(
            "warning", "pin_to_pin",
            "Pins of type Bidirectional and Power output are connected",
            (
                "Symbol #FLG005 Pin 1 [Power output, Line]",
                f"Symbol {ref} Pin {pin} [{name}, Bidirectional, Line]",
            ),
        )] += 1
for ref in ("U2000", "U2010"):
    ALLOWED_ERC_WARNINGS[(
        "warning", "pin_to_pin",
        "Pins of type Bidirectional and Power output are connected",
        (
            "Symbol #FLG005 Pin 1 [Power output, Line]",
            f"Symbol {ref} Pin 22 [AEQENZ/SDA, Bidirectional, Line]",
        ),
    )] += 1


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd, cwd=PROJDIR):
    subprocess.run(cmd, cwd=cwd, check=True)


def find_kicad_cli():
    for candidate in KICAD_CLI_CANDIDATES:
        if not candidate:
            continue
        try:
            subprocess.run([candidate, "version"], cwd=PROJDIR, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return candidate
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    fail("could not find kicad-cli; set KICAD_CLI")


def collect_erc_items(path):
    data = json.loads(path.read_text())
    items = []

    def walk(value):
        if isinstance(value, dict):
            if "severity" in value and ("description" in value or "message" in value):
                items.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return items


def erc_signature(item):
    child_descriptions = tuple(sorted(
        child.get("description", "")
        for child in item.get("items", [])
        if isinstance(child, dict)
    ))
    return (
        item.get("severity", ""),
        item.get("type", ""),
        item.get("description") or item.get("message") or "",
        child_descriptions,
    )


def iter_symbol_blocks(text):
    pos = 0
    while True:
        start = text.find("(symbol\n", pos)
        if start == -1:
            return
        depth = 0
        for end in range(start, len(text)):
            char = text[end]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    yield text[start:end + 1]
                    pos = end + 1
                    break
        else:
            fail("unterminated symbol block in schematic")


def sexpr_block_at(text, start):
    depth = 0
    for end in range(start, len(text)):
        char = text[end]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:end + 1]
    fail("unterminated s-expression block")


def concrete_symbol_refs(path):
    text = path.read_text()
    refs = []
    for block in iter_symbol_blocks(text):
        ref = re.search(r'\(property "Reference" "([^"]+)"', block)
        lib_id = re.search(r'\(lib_id "([^"]+)"', block)
        unit = re.search(r'\(unit (\d+)\)', block)
        if ref and lib_id and unit:
            refs.append({
                "ref": ref.group(1),
                "lib_id": lib_id.group(1),
                "unit": int(unit.group(1)),
                "path": path.name,
            })
    return refs


def check_duplicate_refs():
    refs_by_name = defaultdict(list)
    for sch in sorted(PROJDIR.glob("*.kicad_sch")):
        for ref in concrete_symbol_refs(sch):
            refs_by_name[ref["ref"]].append(ref)

    problems = []
    for ref, entries in refs_by_name.items():
        if len(entries) <= 1:
            continue
        same_sheet = len({entry["path"] for entry in entries}) == 1
        same_lib = len({entry["lib_id"] for entry in entries}) == 1
        unique_units = len({entry["unit"] for entry in entries}) == len(entries)
        if same_sheet and same_lib and unique_units:
            continue
        problems.append((ref, entries))

    if problems:
        for ref, entries in problems:
            print(f"duplicate ref {ref}: {entries}", file=sys.stderr)
        fail("duplicate concrete schematic references found")


def check_label_coordinate_collisions():
    """Reject different net names attached to the same schematic coordinate.

    KiCad electrically joins labels that land on one pin endpoint.  Generated
    sheets therefore must never place two different labels at an identical
    coordinate, even though ERC may report only the resulting merged net.
    Repeated labels with the same name are harmless and are allowed.
    """
    problems = []
    label_re = re.compile(r'\((label|hierarchical_label|global_label)\s+"([^"]+)"')
    at_re = re.compile(r'\(at\s+([-0-9.]+)\s+([-0-9.]+)')

    for sch in sorted(PROJDIR.glob("*.kicad_sch")):
        text = sch.read_text(errors="ignore")
        names_by_coord = defaultdict(set)
        for match in label_re.finditer(text):
            block = sexpr_block_at(text, match.start())
            at = at_re.search(block)
            if at:
                names_by_coord[(at.group(1), at.group(2))].add(match.group(2))
        for coord, names in names_by_coord.items():
            if len(names) > 1:
                problems.append((sch.name, coord, sorted(names)))

    if problems:
        for sheet, coord, names in problems[:40]:
            print(f"label collision {sheet} at {coord}: {names}", file=sys.stderr)
        fail(f"found {len(problems)} coordinate(s) carrying different net labels")


def property_value(block, name):
    match = re.search(r'\(property "' + re.escape(name) + r'" "([^"]*)"', block)
    return match.group(1) if match else ""


def footprint_roots():
    roots = {
        "ducktop2": PROJDIR / "ducktop2.pretty",
        "Module_LattePanda": PROJDIR / "Module_LattePanda.pretty",
    }
    for root in KICAD_FOOTPRINT_DIRS:
        path = Path(root)
        if not path.exists():
            continue
        for pretty in path.glob("*.pretty"):
            roots[pretty.stem] = pretty
    return roots


def footprint_pads(roots, footprint):
    if ":" not in footprint:
        fail(f"bad footprint string {footprint!r}")
    lib, name = footprint.split(":", 1)
    root = roots.get(lib)
    if root is None:
        fail(f"missing footprint library {lib!r} for {footprint}")
    path = root / f"{name}.kicad_mod"
    if not path.exists():
        fail(f"missing footprint file {path}")

    pads = set()
    text = path.read_text(errors="ignore")
    for match in re.finditer(r'\(pad\s+("[^"]*"|[^\s\)]+)\s+([^\s\)]+)', text):
        raw_name, pad_type = match.groups()
        pad_name = raw_name[1:-1] if raw_name.startswith('"') else raw_name
        if pad_type == "np_thru_hole" or not pad_name:
            continue
        pads.add(pad_name)
    return pads


def ignorable_extra_pad(pad):
    upper = pad.upper()
    if upper in {"EP", "EPAD", "PAD", "MP", "MH", "SH"}:
        return True
    return re.fullmatch(r"(MP|MH|SH|S|H|M)\d+", upper) is not None


def check_footprint_pad_matches():
    roots = footprint_roots()
    grouped = defaultdict(lambda: {"values": set(), "pins": set()})
    for sch in sorted(PROJDIR.glob("*.kicad_sch")):
        text = sch.read_text(errors="ignore")
        pos = 0
        while True:
            start = text.find("(symbol", pos)
            if start == -1:
                break
            block = sexpr_block_at(text, start)
            pos = start + len(block)
            if not re.match(r'\(symbol\s+\(lib_id', block):
                continue
            ref = property_value(block, "Reference")
            value = property_value(block, "Value")
            footprint = property_value(block, "Footprint")
            if not ref or not footprint:
                continue
            pins = set(re.findall(r'\(pin "([^"]+)"', block))
            if not pins:
                continue
            entry = grouped[(sch.name, ref, footprint)]
            entry["values"].add(value)
            entry["pins"].update(pins)

    problems = []
    for (sheet, ref, footprint), data in grouped.items():
        pads = footprint_pads(roots, footprint)
        missing_pads = sorted(pin for pin in data["pins"] if pin not in pads)
        extra_pads = sorted(
            pad for pad in pads
            if pad not in data["pins"] and not ignorable_extra_pad(pad)
        )
        if missing_pads or extra_pads:
            problems.append((sheet, ref, sorted(data["values"]), footprint, missing_pads, extra_pads))

    if problems:
        for sheet, ref, values, footprint, missing_pads, extra_pads in problems[:40]:
            print(
                f"footprint pad mismatch {sheet} {ref} {values} {footprint}: "
                f"symbol pins missing pads={missing_pads}, footprint pads without pins={extra_pads}",
                file=sys.stderr,
            )
        fail(f"found {len(problems)} symbol/footprint pad mismatch(es)")


def check_root_sheets():
    root = (PROJDIR / "ducktop2.kicad_sch").read_text()
    for sheet in EXPECTED_SHEETS:
        if not (PROJDIR / sheet).exists():
            fail(f"missing generated sheet {sheet}")
        if f'(property "Sheetfile" "{sheet}"' not in root:
            fail(f"root sheet does not reference {sheet}")
    root_ncs = root.count("(no_connect")
    if root_ncs != 0:
        fail(f"expected 0 root no-connects, found {root_ncs}")


def check_main_pcb_contract():
    pcb = PROJDIR / "ducktop2.kicad_pcb"
    text = pcb.read_text(errors="ignore")
    if '"Edge.Cuts"' not in text:
        fail("main PCB has no Edge.Cuts outline")
    if '"J310"' not in text:
        fail("main PCB is missing the keyboard FFC connector J310")
    keyboard_daughterboard_markers = [
        '"J320"',
        '"SW320"',
        '"D320"',
        "12_keyboard_daughterboard.kicad_sch",
        "Cherry_MX_ULP",
    ]
    for marker in keyboard_daughterboard_markers:
        if marker in text:
            fail(f"main PCB includes keyboard daughterboard marker {marker}")
    copper_layers = re.findall(r'\(\d+\s+"(?:F|B|In\d)\.Cu"\s+\w+\)', text)
    if len(copper_layers) != 6:
        fail(f"expected 6 copper layers in main PCB, found {len(copper_layers)}")


def main():
    if not compileall.compile_dir(GEN_DIR, quiet=1):
        fail("Python compile check failed")

    run([sys.executable, str(PROJDIR / "firmware" / "tps25751a" / "verify_config.py")])
    run([sys.executable, str(GEN_DIR / "generate_mu_carrier_sheet.py")])
    run([sys.executable, str(GEN_DIR / "generate_radio_daughterboard_project.py")])
    run([sys.executable, str(GEN_DIR / "verify_radio_daughterboard.py"), "--schematic-only"])
    check_root_sheets()
    check_duplicate_refs()
    check_label_coordinate_collisions()
    check_footprint_pad_matches()
    check_main_pcb_contract()

    kicad_cli = find_kicad_cli()
    with tempfile.TemporaryDirectory(prefix="ducktop2_self_check_") as temp_dir:
        erc_path = Path(temp_dir) / "erc.json"
        run([kicad_cli, "sch", "erc", "--format", "json", "--output", str(erc_path), "ducktop2.kicad_sch"])
        erc_items = collect_erc_items(erc_path)
        actual = Counter(erc_signature(item) for item in erc_items)
        unexpected = actual - ALLOWED_ERC_WARNINGS
        if unexpected:
            for signature, count in unexpected.items():
                severity, item_type, description, children = signature
                print(
                    f"{count}x {severity} {item_type}: {description}; items={children}",
                    file=sys.stderr,
                )
            fail(f"ERC reported {sum(unexpected.values())} unexpected violation(s)")
        if erc_items:
            print(
                f"ERC: 0 errors, {len(erc_items)} classified intentional warning(s)"
            )

        netlist_path = Path(temp_dir) / "ducktop2.net"
        run([kicad_cli, "sch", "export", "netlist", "--output", str(netlist_path), "ducktop2.kicad_sch"])

    print("ducktop2 schematic self-check OK")


if __name__ == "__main__":
    main()
