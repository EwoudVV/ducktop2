#!/usr/bin/env python3
"""Generate the Battery BMS board project (ducktop2 board split, Phase 2.3).

BMS board (on the pack, MacBook-style): J2 pack connector, F1 fuse,
U719 BQ77915 primary protector + filters, Q703/Q704 charge/discharge
FETs, U11 LTC4368 + Q11/Q12 + RS10 + divider, pack fault/retry path.

Crosses FPC-3 to center: PACK_POS_FUSED, PACK_NEG_RAW, PACK_FAULT_N,
PACK_RETRY_PULSE, MCU_3V3, GND. The gauge (U10 BQ34Z100), charger
(U2), and ship FET (Q25) stay on center.

Reuses the part definitions (nets, footprints, MPNs) from the main
power_sheet builder, reproduced at fresh coordinates on the BMS sheet.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import build_ducktop2 as b
from build_ducktop2 import PROJDIR, stable_uuid, uuid_scope, FOOTPRINTS
from generate_mu_carrier_sheet import root_label, place_fpc_connector
import fpc_contract as fpc

BOARD_DIR = os.path.join(PROJDIR, "bms")
PROJECT_NAME = "bms"


def build_bms_sheet(sheet_symbol_uuid):
    s = b.Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 700
    s.refcounters["#FLG"] = 700

    s.text(20, 20, "== 3S pack BMS: fuse, primary protector, redundant LTC4368, FETs ==")
    s.text(20, 30, "Board split Phase 2.3: pack measurement + protection live on the pack board;")
    s.text(20, 40, "the gauge (U10), charger (U2), and ship FET (Q25) stay on the center board.")

    # Fuse + pack connector
    s.place("F1", "Fuse", "10A MINI pack fuse: Littelfuse 0297010.WXNV", 170, 60,
            footprint=FOOTPRINTS["Fuse_Pack_Blade_Mini"],
            pin_nets={"1": ("PACK_POS_RAW", "local"), "2": ("BAT_PROT_VIN", "local")},
            extra_props={"Manufacturer": "Littelfuse / Keystone", "MPN": "0297010.WXNV + 3568"})
    s.place("J2", "Conn_02x03_Odd_Even", "3S pack power + cell-tap harness", 170, 80,
            footprint=FOOTPRINTS["Conn_02x03_Pack_MegaFit"],
            pin_nets={
                "1": ("PACK_POS_RAW", "local"), "2": ("PACK_POS_RAW", "local"),
                "3": ("PACK_NEG_RAW", "local"), "4": ("PACK_NEG_RAW", "local"),
                "5": ("CELL1_TAP", "local"), "6": ("CELL2_TAP", "local"),
            },
            extra_props={"Manufacturer": "Molex", "MPN": "76829-0006"})

    # BQ7791500 autonomous primary protector
    s.place("U719", "BQ77915", "BQ7791500PWR autonomous 3S primary protector", 80, 105,
            footprint=FOOTPRINTS["BQ77915"],
            pin_nets={
                "1": ("BMS_VDD", "local"), "2": ("BMS_AVDD", "local"),
                "3": ("BMS_VC3_TOP", "local"), "4": ("BMS_VC3_TOP", "local"),
                "5": ("BMS_VC3_TOP", "local"), "6": ("BMS_VC2", "local"),
                "7": ("BMS_VC1", "local"), "8": ("BMS_VC0", "local"),
                "9": ("PACK_NEG_RAW", "local"), "10": ("BMS_SRP", "local"),
                "11": ("BMS_SRN", "local"), "12": ("BMS_DSG_DRV", "local"),
                "13": ("BMS_CHG_DRV", "local"), "14": ("BMS_LD", "local"),
                "15": ("", "nc"), "16": ("PACK_NEG_RAW", "local"),
                "17": ("BMS_OCDP", "local"), "18": ("BMS_TS_UNUSED", "local"),
                "19": ("", "nc"), "20": ("PACK_NEG_RAW", "local"),
                "21": ("", "nc"), "22": ("BMS_PRES", "local"),
                "23": ("PACK_NEG_RAW", "local"), "24": ("PACK_NEG_RAW", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "BQ7791500PWR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/bq77915.pdf",
            })
    s.place("R840", "R", "1k 1% BQ77915 VDD filter", 20, 35, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS_RAW", "local"), "2": ("BMS_VDD", "local")})
    s.place("C840", "C", "1u 25V X7R BQ77915 VDD", 20, 45, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("BMS_VDD", "local"), "2": ("PACK_NEG_RAW", "local")})
    s.place("C841", "C", "1u 10V X7R BQ77915 AVDD", 20, 55, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("BMS_AVDD", "local"), "2": ("PACK_NEG_RAW", "local")})

    for ref, source, sense, y in (
        ("R841", "PACK_NEG_RAW", "BMS_VC0", 65),
        ("R842", "CELL1_TAP", "BMS_VC1", 75),
        ("R843", "CELL2_TAP", "BMS_VC2", 85),
        ("R844", "PACK_POS_RAW", "BMS_VC3_TOP", 95),
    ):
        s.place(ref, "R", "75R 1% BQ77915 cell/balance filter", 20, y,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (source, "local"), "2": (sense, "local")})
    for ref, upper, lower, y in (
        ("C842", "BMS_VC0", "PACK_NEG_RAW", 105),
        ("C843", "BMS_VC1", "BMS_VC0", 115),
        ("C844", "BMS_VC2", "BMS_VC1", 125),
        ("C848", "BMS_VC3_TOP", "BMS_VC2", 135),
    ):
        s.place(ref, "C", "1u 10V X7R BQ77915 internal-balance filter", 20, y,
                footprint=FOOTPRINTS["C_1u"],
                pin_nets={"1": (upper, "local"), "2": (lower, "local")})

    s.place("RS11", "R", "8mOhm 1% 2W BQ77915 current shunt", 20, 150,
            footprint="Resistor_SMD:R_2512_6332Metric",
            pin_nets={"1": ("PACK_NEG_RAW", "local"), "2": ("BMS_SENSE_N", "local")},
            extra_props={"Manufacturer": "Vishay Dale", "MPN": "WSLP25128L000FEA"})
    s.place("R845", "R", "100R BQ77915 SRP filter", 20, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_NEG_RAW", "local"), "2": ("BMS_SRP", "local")})
    s.place("R846", "R", "100R BQ77915 SRN filter", 20, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BMS_SENSE_N", "local"), "2": ("BMS_SRN", "local")})
    s.place("C845", "C", "100n BQ77915 SRP-VSS filter", 20, 180,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BMS_SRP", "local"), "2": ("PACK_NEG_RAW", "local")})
    s.place("C846", "C", "100n BQ77915 differential sense filter", 20, 190,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BMS_SRP", "local"), "2": ("BMS_SRN", "local")})
    s.place("C847", "C", "100n BQ77915 SRN-VSS filter", 20, 200,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BMS_SRN", "local"), "2": ("PACK_NEG_RAW", "local")})

    # Charge/discharge FETs
    s.place("Q703", "Q_NMOS_123S_4G_5678D", "CSD18540Q5B BQ77915 discharge FET", 80, 160,
            footprint=FOOTPRINTS["Q_CSD18540Q5B"],
            pin_nets={
                "1": ("BMS_SENSE_N", "local"), "2": ("BMS_SENSE_N", "local"),
                "3": ("BMS_SENSE_N", "local"), "4": ("BMS_DSG_GATE", "local"),
                "5": ("BMS_FET_COMMON", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "CSD18540Q5B"})
    s.place("Q704", "Q_NMOS_123S_4G_5678D", "CSD18540Q5B BQ77915 charge FET", 125, 160,
            footprint=FOOTPRINTS["Q_CSD18540Q5B"],
            pin_nets={
                "1": ("FG_VSS", "local"), "2": ("FG_VSS", "local"),
                "3": ("FG_VSS", "local"), "4": ("BMS_CHG_GATE", "local"),
                "5": ("BMS_FET_COMMON", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "CSD18540Q5B"})
    for ref, value, net_a, net_b, x, y in (
        ("R847", "4.53k 1% DSG gate resistor", "BMS_DSG_DRV", "BMS_DSG_GATE", 80, 180),
        ("R848", "1k 1% CHG gate resistor", "BMS_CHG_DRV", "BMS_CHG_GATE", 125, 180),
        ("R849", "1M 5% DSG gate-source", "BMS_DSG_GATE", "BMS_SENSE_N", 80, 190),
        ("R850", "3.3M 5% CHG gate-source", "BMS_CHG_GATE", "FG_VSS", 125, 190),
        ("R851", "453k 1% load-detect resistor", "BMS_LD", "FG_VSS", 80, 200),
        ("R852", "10k 5% PRES normal-mode pull-up", "PACK_POS_RAW", "BMS_PRES", 125, 200),
        ("R853", "10k 1% unused TS to VSS", "BMS_TS_UNUSED", "PACK_NEG_RAW", 80, 210),
        ("R854", "604k 1% OCD delay program", "BMS_OCDP", "PACK_NEG_RAW", 125, 210),
    ):
        s.place(ref, "R", value, x, y, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net_a, "local"), "2": (net_b, "local")})

    # LTC4368-1 redundant pack protector + reverse FETs
    s.place("U11", "LTC4368-1", "LTC4368IMS-1 bidirectional pack protector", 230, 70,
            footprint=FOOTPRINTS["LTC4368-1"],
            pin_nets={
                "1": ("BAT_PROT_VIN", "local"), "2": ("BAT_PROT_UV", "local"),
                "3": ("BAT_PROT_OV", "local"), "4": ("GND", "local"),
                "5": ("GND", "local"), "6": ("BAT_PROT_SHDN", "local"),
                "7": ("PACK_FAULT_N", "hier"), "8": ("PACK_POS_FUSED", "local"),
                "9": ("BAT_PROT_SENSE", "local"), "10": ("BAT_PROT_GATE", "local"),
            },
            extra_props={"Manufacturer": "Analog Devices", "MPN": "LTC4368IMS-1#PBF"})
    s.place("Q11", "Q_NMOS_123S_4G_5678D", "CSD18540Q5B reverse-pack FET A", 230, 95,
            footprint=FOOTPRINTS["Q_CSD18540Q5B"],
            pin_nets={
                "1": ("BAT_PROT_FET_COMMON", "local"), "2": ("BAT_PROT_FET_COMMON", "local"),
                "3": ("BAT_PROT_FET_COMMON", "local"), "4": ("BAT_PROT_GATE", "local"),
                "5": ("BAT_PROT_VIN", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "CSD18540Q5B"})
    s.place("Q12", "Q_NMOS_123S_4G_5678D", "CSD18540Q5B reverse-pack FET B", 280, 95,
            footprint=FOOTPRINTS["Q_CSD18540Q5B"],
            pin_nets={
                "1": ("BAT_PROT_FET_COMMON", "local"), "2": ("BAT_PROT_FET_COMMON", "local"),
                "3": ("BAT_PROT_FET_COMMON", "local"), "4": ("BAT_PROT_GATE", "local"),
                "5": ("BAT_PROT_SENSE", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "CSD18540Q5B"})
    s.place("RS10", "R", "11mOhm 1% 2W LTC4368 bounded pack-current shunt", 335, 60,
            footprint="Resistor_SMD:R_2512_6332Metric",
            pin_nets={"1": ("BAT_PROT_SENSE", "local"), "2": ("PACK_POS_FUSED", "local")},
            extra_props={"Manufacturer": "Vishay Dale", "MPN": "WSLP2512R0110FEA"})
    s.place("C725", "C", "10u 25V X7R LTC4368 VOUT", 390, 60,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BZ71E106KE15L"})
    s.place("R700", "R", "3.09M 1% BAT UV/OV top", 335, 70, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_VIN", "local"), "2": ("BAT_PROT_UV", "local")})
    s.place("R701", "R", "73.2k 1% BAT UV/OV middle", 335, 80, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_UV", "local"), "2": ("BAT_PROT_OV", "local")})
    s.place("R702", "R", "121k 1% BAT UV/OV bottom", 335, 90, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_OV", "local"), "2": ("GND", "local")})
    s.place("R703", "R", "22k LTC4368 CGATE series", 335, 100, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_GATE", "local"), "2": ("BAT_PROT_CGATE", "local")})
    s.place("C700", "C", "3.3nF >=50V LTC4368 CGATE", 335, 110, footprint=FOOTPRINTS["C_1n"],
            pin_nets={"1": ("BAT_PROT_CGATE", "local"), "2": ("GND", "local")})
    s.place("C724", "C", "4.7nF >=50V pack hot-swap slew", 335, 120, footprint=FOOTPRINTS["C_1n"],
            pin_nets={"1": ("BAT_PROT_GATE", "local"), "2": ("BAT_PROT_FET_COMMON", "local")})
    s.place("R707", "R", "100k pack protector SHDN pull-up", 390, 70, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_VIN", "local"), "2": ("BAT_PROT_SHDN", "local")})
    s.place("R708", "R", "10k pack FAULT pull-up", 390, 80, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("PACK_FAULT_N", "hier")})
    s.place("Q701", "Q_NMOS_SOT23_GSD", "BSS138 pack protector latch reset", 390, 90,
            footprint=FOOTPRINTS["Q_BSS138"],
            pin_nets={"1": ("PACK_RETRY_PULSE", "hier"), "2": ("GND", "local"),
                      "3": ("BAT_PROT_SHDN", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"})
    s.place("R709", "R", "100k pack retry gate pulldown", 390, 100, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_RETRY_PULSE", "hier"), "2": ("GND", "local")})

    # FPC-3 boundary markers
    s.pwrflag(20, 400, "PACK_POS_FUSED")
    s.pwrflag(20, 420, "PACK_NEG_RAW")

    # Phase 4a: FPC-3 connector (the physical FH12-30S on the BMS board
    # edge).  Pin map from fpc_contract.py -- same conductor order as the
    # center's FPC3_C.  The pack rails (PACK_POS_FUSED, PACK_NEG_RAW),
    # FG_VSS, MCU_3V3, PACK_FAULT_N and PACK_RETRY_PULSE cross here; the
    # hier labels at the connector pins make them boundary nets.
    place_fpc_connector(s, "FPC106", "Conn_01x30_FFC_MP", fpc.FPC3_PINMAP,
                        "FH12-30S-0.5SH (FPC-3)", x=490, y=250, pwr_base=3600)
    return s


def main() -> int:
    os.makedirs(BOARD_DIR, exist_ok=True)
    sheet_uuid = stable_uuid("bms:sheet:main")
    with uuid_scope("bms:main"):
        sheet = build_bms_sheet(sheet_uuid)
        text = sheet.render(stable_uuid("bms:self:main"), page_number=1, paper="A1")
    with open(os.path.join(BOARD_DIR, "bms.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(text)

    # BMS is a single flat sheet; the root is the sheet itself.
    print(f"wrote bms project (single sheet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())