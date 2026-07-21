import os
import shutil

from build_ducktop2 import (
    PROJDIR,
    U,
    reset_uuid_sequence,
    stable_uuid,
    uuid_scope,
)
from generate_mu_carrier_sheet import root_label, sheet_block

import generate_gnss_daughterboard_sheet as gnss
import generate_ham_radio_sheet as ham
import generate_radio_audio_codec_sheet as codec
import generate_radio_daughterboard_core_sheet as core


BOARD_DIR = os.path.join(PROJDIR, "radio_daughterboard")
PROJECT_NAME = "radio_daughterboard"


def generated_hier_nets(sheet):
    nets = []
    seen = set()
    prefix = '(hierarchical_label "'
    for item in sheet.body:
        if not item.startswith(prefix):
            continue
        name = item[len(prefix):].split('"', 1)[0]
        if name not in seen:
            seen.add(name)
            nets.append(name)
    return nets


def write_generated_sheet(context, filename, builder, page_number):
    with uuid_scope(f"radio_daughterboard:{context}"):
        sheet = builder()
        text = sheet.render(
            stable_uuid(f"radio_daughterboard:{context}:self"),
            page_number=page_number,
        )
    with open(os.path.join(BOARD_DIR, filename), "w", encoding="utf-8") as handle:
        handle.write(text)
    return sheet


def write_library_tables():
    for filename in ("sym-lib-table", "fp-lib-table"):
        source = os.path.join(PROJDIR, filename)
        destination = os.path.join(BOARD_DIR, filename)
        with open(source, "r", encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace('${KIPRJMOD}/', '${KIPRJMOD}/../')
        with open(destination, "w", encoding="utf-8") as handle:
            handle.write(text)


def write_project_file():
    source = os.path.join(PROJDIR, "ducktop2.kicad_pro")
    destination = os.path.join(BOARD_DIR, f"{PROJECT_NAME}.kicad_pro")
    shutil.copyfile(source, destination)


def main():
    os.makedirs(BOARD_DIR, exist_ok=True)

    core_uuid = stable_uuid("radio_daughterboard:sheet-symbol:01_core")
    radio_uuid = stable_uuid("radio_daughterboard:sheet-symbol:02_radios")
    gnss_uuid = stable_uuid("radio_daughterboard:sheet-symbol:03_gnss")
    codec_uuid = stable_uuid("radio_daughterboard:sheet-symbol:04_codec")

    core_sheet = write_generated_sheet(
        "01_core",
        "01_core.kicad_sch",
        lambda: core.build(core_uuid),
        "2",
    )
    radio_sheet = write_generated_sheet(
        "02_radios",
        "02_radios.kicad_sch",
        lambda: ham.build(
            radio_uuid,
            supply_5v="RADIO_DB_5V",
            logic_3v3="RADIO_DB_3V3",
        ),
        "3",
    )
    gnss_sheet = write_generated_sheet(
        "03_gnss",
        "03_gnss.kicad_sch",
        lambda: gnss.build(gnss_uuid),
        "4",
    )
    codec_sheet = write_generated_sheet(
        "04_codec",
        "04_codec.kicad_sch",
        lambda: codec.build(codec_uuid, logic_3v3="RADIO_DB_3V3"),
        "5",
    )

    sheets = (
        ("Core & Mainboard Connector", "01_core.kicad_sch", core_uuid, core_sheet),
        ("VHF & UHF Radios", "02_radios.kicad_sch", radio_uuid, radio_sheet),
        ("GNSS", "03_gnss.kicad_sch", gnss_uuid, gnss_sheet),
        ("USB Radio Audio", "04_codec.kicad_sch", codec_uuid, codec_sheet),
    )

    reset_uuid_sequence("radio_daughterboard:root")
    blocks = []
    pin_maps = []
    for index, (name, filename, sheet_uuid, sheet) in enumerate(sheets):
        nets = generated_hier_nets(sheet)
        block, pins = sheet_block(
            sheet_uuid,
            30 + index * 150,
            40,
            120,
            150,
            name,
            filename,
            nets,
        )
        blocks.append(block)
        pin_maps.append((name, pins, nets))

    net_users = {}
    for name, pins, nets in pin_maps:
        for net in nets:
            net_users.setdefault(net, []).append((name, pins))

    orphan_nets = {
        net: users[0][0]
        for net, users in net_users.items()
        if len(users) < 2
    }
    if orphan_nets:
        details = ", ".join(
            f"{net} only on {sheet_name}"
            for net, sheet_name in sorted(orphan_nets.items())
        )
        raise ValueError(f"orphan hierarchical nets: {details}")

    labels = []
    seen_labels = set()
    for net, users in net_users.items():
        for _sheet_name, pins in users:
            coord = pins[net]
            key = (coord[0], coord[1], net)
            if key in seen_labels:
                continue
            labels.append(root_label(coord, net))
            seen_labels.add(key)

    root_text = (
        '(kicad_sch\n'
        '  (version 20260306)\n'
        '  (generator "eeschema")\n'
        '  (generator_version "10.0")\n'
        f'  (uuid {U()})\n'
        '  (paper "A2")\n'
        '  (lib_symbols\n  )\n'
        + "\n".join(blocks)
        + "\n"
        + "\n".join(labels)
        + "\n"
        '  (sheet_instances\n'
        '    (path "/"\n'
        '      (page "1")\n'
        '    )\n'
        '  )\n'
        '  (embedded_fonts no)\n'
        ')\n'
    )
    with open(
        os.path.join(BOARD_DIR, f"{PROJECT_NAME}.kicad_sch"),
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(root_text)

    write_project_file()
    write_library_tables()


if __name__ == "__main__":
    main()
