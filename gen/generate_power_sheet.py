import os
from build_ducktop2 import Sheet, U, PROJDIR, FOOTPRINTS

SHEET_SYMBOL_UUID = None  # filled by main()


def add_selector_fet(s, ref, x, y, gate, common_source, drain, drain_kind):
    s.place(ref, "Q_PMOS_1G_234S_5D", "SiSS4409DN 40V reverse-blocking PMOS", x, y,
            footprint=FOOTPRINTS["Q_SiSS4409DN"],
            pin_nets={
                "1": (gate, "local"),
                "2": (common_source, "local"),
                "3": (common_source, "local"),
                "4": (common_source, "local"),
                "5": (drain, drain_kind),
            },
            extra_props={"Manufacturer": "Vishay", "MPN": "SiSS4409DN-T1-GE3"})


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")

    class Cur:
        def __init__(self, x0, y0, col_w=55, row_h=10, rows_per_col=22):
            self.x0, self.y0, self.col_w, self.row_h, self.rows = x0, y0, col_w, row_h, rows_per_col
            self.i = 0

        def next(self):
            col, row = divmod(self.i, self.rows)
            self.i += 1
            return (self.x0 + col * self.col_w, self.y0 + row * self.row_h)

    # The motherboard provides autonomous per-cell protection.  The tiny PCBs
    # attached to the user's cells are thermal-only and are not part of the
    # electrical protection or current path.
    s.text(20, 20, "== 3S cell entry, autonomous primary protection, fuse and redundant pack protection ==")
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

    # BQ7791500 is an autonomous primary protector.  For 3S, VC3/VC4/VC5
    # short together at the top-cell sense node and CCFG is tied to VSS.
    # Temperature protection is intentionally disabled exactly as TI directs:
    # TS has 10 kOhm to VSS and VTB is unused.  The user's cell-mounted boards
    # retain their independent thermal-only cutoff behavior.
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

    # Internal balancing is intentionally current-limited below TI's 50 mA
    # maximum.  Two 75-ohm VC resistors plus the internal balance FET target
    # about 26 mA at 4.2 V.  TI specifies 1 uF VC filtering when internal
    # balancing is enabled.
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

    # The 8 mOhm primary-protector shunt gives a 7.5 A nominal OCD threshold
    # and 15 A nominal short-circuit threshold.  The high-side LTC4368 remains
    # the tighter normal pack breaker; BQ7791500 is independent backup.
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

    # Common-drain, back-to-back low-side FETs support both charging and
    # discharging while allowing the protector to interrupt either direction.
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

    s.place("RS1", "R", "5mOhm 1% 2W BQ34Z100 Kelvin shunt", 170, 120,
            footprint="Resistor_SMD:R_2512_6332Metric",
            pin_nets={"1": ("FG_VSS", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Vishay Dale", "MPN": "WSLP2512R0050FEA"})

    # Bidirectional battery isolation is mandatory because the charger both charges and discharges the pack.
    # The LTC4368-1 controls common-source FETs.  Its 50 mV forward/reverse
    # threshold and the 11 mOhm high-side shunt keep worst-case trips below the
    # BQ25798 6 A continuous BAT-pin rating.
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
    # LTC4368 requires at least 1 uF from VOUT to GND.  Keep this capacitor on
    # the protector side of the BQ25798 ship FET so it remains present when
    # Q25 disconnects BAT_CHARGER from PACK_POS_FUSED.
    s.place("C725", "C", "10u 25V X7R LTC4368 VOUT", 390, 60,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BZ71E106KE15L"})
    # The 0.5 V LTC4368 thresholds set an approximately 8.45 V to 13.57 V
    # accepted pack window.  This keeps the motherboard from relying on the
    # protection BMS as its normal deep-discharge cutoff.
    s.place("R700", "R", "3.09M 1% BAT UV/OV top", 335, 70, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_VIN", "local"), "2": ("BAT_PROT_UV", "local")})
    s.place("R701", "R", "73.2k 1% BAT UV/OV middle", 335, 80, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_UV", "local"), "2": ("BAT_PROT_OV", "local")})
    s.place("R702", "R", "121k 1% BAT UV/OV bottom", 335, 90, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_OV", "local"), "2": ("GND", "local")})
    # LTC4368 GATE must connect directly to both FET gates so fault turn-off is not resistor-limited.
    # R703 is only in series with CGATE; C724 supplies the optional live-mating gate-to-source slew.
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

    s.gnd(200, 90)
    s.pwrflag(200, 30, "PACK_POS_RAW")
    s.pwrflag(200, 37.5, "PACK_NEG_RAW")
    s.pwrflag(200, 42.5, "BMS_VDD")
    s.pwrflag(200, 45, "FG_VSS")
    s.pwrflag(200, 105, "GND")
    s.pwrflag(650, 30, "BAT_PROT_VIN")

    # ---------------- U10: protected-pack fuel gauge ----------------
    s.text(170, 125, "== U10 BQ34Z100-G1 3S fuel gauge for protected external pack ==")
    s.place("U10", "BQ34Z100-G1", "BQ34Z100-G1 protected-pack gauge", 230, 175,
            footprint=FOOTPRINTS["BQ34Z100-G1"],
            pin_nets={
                "1": ("BQ_ALERT", "hier"),
                "2": ("", "nc"),
                "3": ("FG_P1_TIE", "local"),
                "4": ("FG_BAT_SENSE", "local"),
                "5": ("FG_CE", "local"),
                "6": ("MCU_3V3", "hier"),
                "7": ("FG_REG25", "local"),
                "8": ("FG_VSS", "local"),
                "9": ("FG_SRP", "local"),
                "10": ("FG_SRN", "local"),
                "11": ("FG_TS", "local"),
                "12": ("", "nc"),
                "13": ("I2C_SCL", "hier"),
                "14": ("I2C_SDA", "hier"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "BQ34Z100PWR-G1"})
    s.place("R180", "R", "220k 0.1% <=25ppm pack divider hi", 170, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BAT_PROT_VIN", "local"), "2": ("FG_BAT_DIV", "local")})
    s.place("R181", "R", "16.5k 0.1% pack divider lo", 170, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_BAT_DIV", "local"), "2": ("FG_VSS", "local")})
    s.place("R182", "R", "100R BAT filter", 170, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_BAT_DIV", "local"), "2": ("FG_BAT_SENSE", "local")})
    s.place("C180", "C", "100n BAT filter", 170, 180, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FG_BAT_SENSE", "local"), "2": ("FG_VSS", "local")})
    s.place("R183", "R", "100R SRP filter", 170, 190, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_VSS", "local"), "2": ("FG_SRP", "local")})
    s.place("R184", "R", "100R SRN filter", 170, 200, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("GND", "local"), "2": ("FG_SRN", "local")})
    s.place("C181", "C", "100n sense filter", 170, 210, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FG_SRP", "local"), "2": ("FG_SRN", "local")})
    s.place("R185", "R", "10k CE pull-up", 290, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FG_CE", "local")})
    s.place("R186", "R", "10k gauge ALERT pull-up", 290, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BQ_ALERT", "hier")})
    s.place("C182", "C", "100n REGIN/VCC", 290, 190, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FG_VSS", "local")})
    s.place("C183", "C", "1u REG25", 290, 200, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("FG_REG25", "local"), "2": ("FG_VSS", "local")})
    s.place("R189", "R", "0R P1 not-used tie to VSS", 345, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_P1_TIE", "local"), "2": ("FG_VSS", "local")})
    s.place("R855", "R", "10k unused external TS pulldown", 345, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_TS", "local"), "2": ("FG_VSS", "local")})

    # ---------------- U2: BQ25798 buck-boost charger / NVDC path ----------------
    s.text(260, 20, "== U2 bq25798 Buck-Boost Charger / NVDC Power Path (VSYS) ==")
    s.place("U2", "BQ25798", "BQ25798RQMR", 320, 120,
            footprint="Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm",
            pin_nets={
                "1": ("STAT_DRV", "local"), "2": ("VBUS_COMBINED", "local"),
                "3": ("VBUS_COMBINED", "local"), "4": ("BTST1_NODE", "local"),
                "5": ("REGN", "local"), "6": ("", "nc"), "7": ("", "nc"),
                "8": ("VBUS_COMBINED", "local"), "9": ("VBUS_COMBINED", "local"), "10": ("GND", "local"),
                "11": ("GND", "local"), "12": ("PMIC_QON_PIN", "local"), "13": ("CHG_CE_HW_N", "local"),
                "14": ("I2C_SCL", "hier"), "15": ("I2C_SDA", "hier"), "16": ("CHG_TS_FIXED", "local"),
                "17": ("ILIM_SET", "local"), "18": ("BATP_SENSE", "local"), "19": ("BTST2_NODE", "local"),
                "20": ("PROG_SET", "local"), "21": ("CHG_INT_N", "hier"), "22": ("BAT_CHARGER", "local"),
                "23": ("BAT_CHARGER", "local"), "24": ("SDRV_GATE", "local"), "25": ("VSYS", "hier"),
                "26": ("SW2", "local"), "27": ("GND", "local"), "28": ("SW1", "local"),
                "29": ("PMID", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "BQ25798RQMR"})

    c3 = Cur(260, 40)
    s.place("R12", "R", "1k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("STAT_LED_A", "local")})
    s.place("LED1", "LED", "Charge STAT", *c3.next(), footprint=FOOTPRINTS["LED"],
            pin_nets={"2": ("STAT_LED_A", "local"), "1": ("STAT_DRV", "local")},
            extra_props={
                "Manufacturer": "Kingbright", "MPN": "APT1608SGC",
                "Datasheet": "https://www.kingbrightusa.com/images/catalog/SPEC/APT1608SGC.pdf",
            })
    s.place("C7", "C", "47n 25V X7R BTST1", *c3.next(), footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("BTST1_NODE", "local"), "2": ("SW1", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71E473KA88D"})
    s.place("C8", "C", "47n 25V X7R BTST2", *c3.next(), footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("BTST2_NODE", "local"), "2": ("SW2", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71E473KA88D"})
    s.place("C9", "C", "4.7u 10V X7R REGN", *c3.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("REGN", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BR71A475KA73L"})
    # QON has its own charger-domain pull-up and must not be pulled to a rail
    # that disappears in hard-off.  Q702 provides a high-impedance, active-high
    # MCU pulse; the physical case button reaches QON and Mu PWRBTN through
    # separate Schottky diodes so neither input can back-drive the other.
    s.place("R13", "R", "100k QON-control gate pulldown", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PMIC_QON_ASSERT", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100KL"})
    s.place("Q702", "Q_NMOS_SOT23_GSD", "BSS138 QON open-drain pulse", *c3.next(),
            footprint=FOOTPRINTS["Q_BSS138"],
            pin_nets={"1": ("PMIC_QON_ASSERT", "hier"), "2": ("GND", "local"),
                      "3": ("PMIC_QON_PIN", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"})
    s.place("D715", "D_Schottky", "BAT54WS case button to charger QON", *c3.next(),
            footprint=FOOTPRINTS["D_Signal"],
            pin_nets={"1": ("CASE_PWRBTN_N", "hier"), "2": ("PMIC_QON_PIN", "local")},
            extra_props={"Manufacturer": "Diodes Incorporated", "MPN": "BAT54WS-7-F"})
    s.place("D716", "D_Schottky", "BAT54WS case button to Mu PWRBTN", *c3.next(),
            footprint=FOOTPRINTS["D_Signal"],
            pin_nets={"1": ("CASE_PWRBTN_N", "hier"), "2": ("MU_PWRBTN_N", "hier")},
            extra_props={"Manufacturer": "Diodes Incorporated", "MPN": "BAT54WS-7-F"})
    s.place("R14", "R", "10k CE hardware-disable pull-up to REGN", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("CHG_CE_HW_N", "local")})
    s.place("Q700", "Q_NMOS_SOT23_GSD", "BSS138 active-high charger enable pull-down", *c3.next(),
            footprint=FOOTPRINTS["Q_BSS138"],
            pin_nets={"1": ("CHG_ENABLE", "hier"), "2": ("GND", "local"),
                      "3": ("CHG_CE_HW_N", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"})
    s.place("R719", "R", "100k charger-enable gate pulldown", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_ENABLE", "hier"), "2": ("GND", "local")})
    s.place("R15", "R", "10k INT pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_INT_N", "hier"), "2": ("MCU_3V3", "hier")})
    s.place("R16", "R", "5.24k 1% fixed-valid TS top", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("CHG_TS_FIXED", "local")})
    s.place("R30", "R", "4.7k I2C SCL pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("I2C_SCL", "hier")})
    s.place("R31", "R", "4.7k I2C SDA pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("I2C_SDA", "hier")})
    s.place("R705", "R", "7.50k 1% fixed-valid TS bottom", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_TS_FIXED", "local"), "2": ("GND", "local")})
    s.place("R17", "R", "47.0k 0.1% ILIM top (3.0A ceiling)", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("ILIM_SET", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0747KL"})
    s.place("R190", "R", "100k 0.1% ILIM bottom", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("ILIM_SET", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD07100KL"})
    s.place("R18", "R", "10.5k 1% PROG: 3S, 1.5MHz", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PROG_SET", "local"), "2": ("GND", "local")})
    s.place("C10", "C", "100n 50V X7R PMID local", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("PMID", "local"), "2": ("GND", "local")})
    s.place("C11", "C", "100n 50V X7R SYS local", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("L1", "L", "1.0uH 20% 28A Isat BQ25798 1.5MHz", *c3.next(), footprint=FOOTPRINTS["L_BQ25798"],
            pin_nets={"1": ("SW1", "local"), "2": ("SW2", "local")},
            extra_props={"Manufacturer": "Coilcraft", "MPN": "XAL7030-102MEC"})
    # TI BQ25798EVM-842 Q5 implementation: a single CSD17575Q3 ship FET
    # blocks battery discharge into BAT/SYS when SDRV is low, while its body
    # diode still permits adapter-powered charging and wake-up.
    s.place("Q25", "Q_NMOS_123S_4G_5678D", "CSD17575Q3 BQ25798 ship FET", *c3.next(),
            footprint=FOOTPRINTS["Q_CSD17575Q3"],
            pin_nets={
                "1": ("BAT_CHARGER", "local"), "2": ("BAT_CHARGER", "local"),
                "3": ("BAT_CHARGER", "local"), "4": ("SDRV_GATE", "local"),
                "5": ("PACK_POS_FUSED", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "CSD17575Q3",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/csd17575q3.pdf",
            })
    s.place("R704", "R", "100R BATP Kelvin filter", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("BATP_SENSE", "local")})

    # BQ25798 Rev C Figure 8-1 nominal capacitor network. Route the 100 nF parts closest to their pins.
    for ref, net in (("C701", "VBUS_COMBINED"), ("C702", "VBUS_COMBINED")):
        s.place(ref, "C", "10u 25V X7R VBUS", *c3.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": (net, "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    for ref in ("C703", "C704", "C705"):
        s.place(ref, "C", "10u 25V X7R PMID", *c3.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("PMID", "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    for ref in ("C706", "C707", "C708", "C709", "C710"):
        s.place(ref, "C", "10u 25V X7R SYS", *c3.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    s.place("C711", "C", "100n 50V X7R BAT local", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BAT_CHARGER", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D"})
    for ref in ("C712", "C713"):
        s.place(ref, "C", "10u 25V X7R BAT", *c3.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("BAT_CHARGER", "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    s.place("R706", "R", "2R VBUS hot-plug damper", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_DAMP", "local")})
    s.place("C714", "C", "2.2u 25V X7R VBUS hot-plug damper", *c3.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("VBUS_DAMP", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BR71E225KA73L"})

    c4 = Cur(380, 40)
    s.place("C12", "C", "100n 50V X7R VBUS local", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D"})

    s.place("J190", "Conn_01x02", "AUX/SOLAR protected screw terminal 6-22V nominal", *c4.next(),
            footprint=FOOTPRINTS["Terminal_01x02_5.08"],
            pin_nets={"1": ("AUX_DC_RAW", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Phoenix Contact", "MPN": "1715022"})
    s.place("F190", "Fuse", "3A MINI AUX input fuse: Littelfuse 0297003.WXNV", *c4.next(),
            footprint=FOOTPRINTS["Fuse_Pack_Blade_Mini"],
            pin_nets={"1": ("AUX_DC_RAW", "local"), "2": ("AUX_DC_FUSED", "local")},
            extra_props={"Manufacturer": "Littelfuse / Keystone", "MPN": "0297003.WXNV + 3568"})
    s.place("D190", "D_TVS", "SMCJ24CA bidirectional AUX surge clamp", *c4.next(), footprint=FOOTPRINTS["D_TVS"],
            pin_nets={"1": ("AUX_DC_FUSED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Vishay", "MPN": "SMCJ24CA-E3/57T"})
    s.place("Q13", "Q_NMOS_123S_4G_5678D", "CSD19537Q3 100V AUX reverse FET", *c4.next(),
            footprint=FOOTPRINTS["Q_CSD19537Q3"],
            pin_nets={
                "1": ("AUX_EFUSE_IN_SYS", "local"), "2": ("AUX_EFUSE_IN_SYS", "local"),
                "3": ("AUX_EFUSE_IN_SYS", "local"), "4": ("AUX_EFUSE_BGATE", "local"),
                "5": ("AUX_DC_FUSED", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "CSD19537Q3"})
    s.place("Q14", "Q_NMOS_SOT23_GSD", "BSS138 fast reverse-gate pulldown", *c4.next(),
            footprint=FOOTPRINTS["Q_BSS138"],
            pin_nets={"1": ("AUX_EFUSE_Q2_GATE", "local"), "2": ("AUX_EFUSE_IN_SYS", "local"),
                      "3": ("AUX_EFUSE_BGATE", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"})
    s.place("U12", "TPS26630RGE", "TPS26630RGER 3A AUX eFuse / surge cutoff", *c4.next(),
            footprint=FOOTPRINTS["TPS26630RGE"],
            pin_nets={
                "1": ("AUX_DC_FUSED", "local"), "2": ("AUX_DC_FUSED", "local"),
                "3": ("AUX_EFUSE_BGATE", "local"), "4": ("AUX_EFUSE_DRV", "local"),
                "5": ("AUX_EFUSE_IN_SYS", "local"), "6": ("AUX_EFUSE_UV", "local"),
                "7": ("AUX_EFUSE_OV", "local"), "8": ("GND", "local"),
                "9": ("AUX_EFUSE_DVDT", "local"), "10": ("AUX_EFUSE_ILIM", "local"),
                "11": ("GND", "local"), "12": ("", "nc"), "13": ("", "nc"),
                "14": ("AUX_FAULT_N", "hier"), "15": ("AUX_PGTH", "local"), "16": ("AUX_PGOOD", "hier"),
                "17": ("AUX_DC_PROTECTED", "local"), "18": ("AUX_DC_PROTECTED", "local"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("", "nc"),
                "22": ("", "nc"), "23": ("", "nc"), "24": ("", "nc"),
                "25": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS26630RGER"})
    s.place("R710", "R", "6.04k 1% AUX 3A current limit", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_ILIM", "local"), "2": ("GND", "local")})
    s.place("R711", "R", "300k 0.1% AUX UV/OV top", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_IN_SYS", "local"), "2": ("AUX_EFUSE_UV", "local")})
    s.place("R712", "R", "63.2k 0.1% AUX UV/OV middle", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_UV", "local"), "2": ("AUX_EFUSE_OV", "local")})
    s.place("R713", "R", "20.0k 0.1% AUX UV/OV bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_OV", "local"), "2": ("GND", "local")})
    s.place("R714", "R", "31R AUX reverse-FET pulldown gate", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_DRV", "local"), "2": ("AUX_EFUSE_Q2_GATE", "local")})
    s.place("R715", "R", "10k AUX eFuse FLT pull-up", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("AUX_FAULT_N", "hier")})
    s.place("R716", "R", "10k AUX eFuse PGOOD pull-up", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("AUX_PGOOD", "hier")})
    s.place("R739", "R", "332k 0.1% AUX PGOOD threshold top", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_PROTECTED", "local"), "2": ("AUX_PGTH", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD07332KL"})
    s.place("R740", "R", "97.6k 0.1% AUX PGOOD threshold bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_PGTH", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0797K6L"})
    s.place("C720", "C", "1u 50V X7R AUX input", *c4.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("AUX_EFUSE_IN_SYS", "local"), "2": ("GND", "local")})
    s.place("C721", "C", "100n 50V X7R AUX eFuse local", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AUX_EFUSE_IN_SYS", "local"), "2": ("GND", "local")})
    s.place("C722", "C", "10u 50V X7R AUX output", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("AUX_DC_PROTECTED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "TDK", "MPN": "CGA5L1X7R1H106K160AC"})
    s.place("C723", "C", "100n AUX eFuse dVdT approx 50ms at 24V", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AUX_EFUSE_DVDT", "local"), "2": ("GND", "local")})
    s.place("R191", "R", "470k 1% AUX ADC top", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_IN_SYS", "local"), "2": ("AUX_DC_DIV", "local")})
    s.place("R192", "R", "56k 1% AUX ADC bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_DIV", "local"), "2": ("GND", "local")})
    s.place("R193", "R", "1k AUX ADC series", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_DIV", "local"), "2": ("AUX_DC_ADC", "hier")})
    s.place("C192", "C", "100n AUX ADC filter", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AUX_DC_ADC", "hier"), "2": ("GND", "local")})

    # U15 provides qualified, reverse-blocking priority selection between USB-C PD and AUX/solar.
    # The industrial I-grade part is used because commercial C-grade selectors stop at 70 C.
    s.text(470, 20, "== U15 LTC4418IUF: USB-C PD priority over protected AUX/solar ==")
    s.place("U15", "LTC4418IUF", "LTC4418IUF#PBF dual-input selector", 520, 165,
            footprint=FOOTPRINTS["LTC4418IUF"],
            pin_nets={
                "1": ("MAIN_SEL_TMR", "local"),
                "2": ("USB_MAIN_UV", "local"), "3": ("USB_MAIN_OV", "local"),
                "4": ("AUX_MAIN_UV", "local"), "5": ("AUX_MAIN_OV", "local"),
                "6": ("", "nc"), "7": ("GND", "local"),
                "8": ("MAIN_SEL_INTVCC", "local"), "9": ("MAIN_USB_VALID_N", "hier"),
                "10": ("MAIN_AUX_VALID_N", "hier"),
                "11": ("AUX_MAIN_GATE", "local"), "12": ("AUX_MAIN_FET_COMMON", "local"),
                "13": ("USB_MAIN_GATE", "local"), "14": ("USB_MAIN_FET_COMMON", "local"),
                "15": ("VBUS_COMBINED", "local"),
                "16": ("AUX_DC_PROTECTED", "local"), "17": ("USB_PD_SELECTED", "hier"),
                "18": ("MAIN_SEL_INTVCC", "local"), "19": ("MAIN_SEL_INTVCC", "local"),
                "20": ("GND", "local"), "21": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Analog Devices", "MPN": "LTC4418IUF#PBF"})

    add_selector_fet(s, "Q21", 485, 70, "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "USB_PD_SELECTED", "hier")
    add_selector_fet(s, "Q22", 545, 70, "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "VBUS_COMBINED", "local")
    add_selector_fet(s, "Q23", 485, 105, "AUX_MAIN_GATE", "AUX_MAIN_FET_COMMON", "AUX_DC_PROTECTED", "local")
    add_selector_fet(s, "Q24", 545, 105, "AUX_MAIN_GATE", "AUX_MAIN_FET_COMMON", "VBUS_COMBINED", "local")

    for ref, value, net_a, net_b, x, y, mpn in (
        ("R730", "1.00M 0.1% USB UV top", "USB_PD_SELECTED", "USB_MAIN_UV", 475, 225, "RT0603BRD071ML"),
        ("R731", "19.6k 0.1% USB window middle", "USB_MAIN_UV", "USB_MAIN_OV", 475, 237.7, "RT0603BRD0719K6L"),
        ("R732", "63.4k 0.1% USB OV bottom", "USB_MAIN_OV", "GND", 475, 250.4, "RT0603BRD0763K4L"),
        ("R733", "383k 0.1% AUX UV top", "AUX_DC_PROTECTED", "AUX_MAIN_UV", 555, 225, "RT0603BRD07383KL"),
        ("R734", "63.4k 0.1% AUX window middle", "AUX_MAIN_UV", "AUX_MAIN_OV", 555, 237.7, "RT0603BRD0763K4L"),
        ("R735", "20.0k 0.1% AUX OV bottom", "AUX_MAIN_OV", "GND", 555, 250.4, "RT0603BRD0720KL"),
    ):
        kind_a = "hier" if net_a == "USB_PD_SELECTED" else "local"
        s.place(ref, "R", value, x, y, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net_a, kind_a), "2": (net_b, "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": mpn})

    for ref, value, net, x, y, fp, mpn in (
        ("C740", "100n 10V INTVCC", "MAIN_SEL_INTVCC", 475, 275, "C_100n", "GRM188R71A104KA61D"),
        ("C741", "15n 50V TMR approx 240ms", "MAIN_SEL_TMR", 515, 275, "C_0402", "GRM155R71H153KA12D"),
        ("C742", "100n 50V USB V1 local", "USB_PD_SELECTED", 555, 275, "C_100n", "GRM188R71H104KA93D"),
        ("C743", "100n 50V USB VS1 local", "USB_MAIN_FET_COMMON", 475, 292.8, "C_100n", "GRM188R71H104KA93D"),
        ("C744", "100n 50V AUX V2 local", "AUX_DC_PROTECTED", 515, 292.8, "C_100n", "GRM188R71H104KA93D"),
        ("C745", "100n 50V AUX VS2 local", "AUX_MAIN_FET_COMMON", 555, 292.8, "C_100n", "GRM188R71H104KA93D"),
    ):
        kind = "hier" if net == "USB_PD_SELECTED" else "local"
        s.place(ref, "C", value, x, y, footprint=FOOTPRINTS[fp],
                pin_nets={"1": (net, kind), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": mpn})
    s.place("R717", "R", "10k main USB VALID pull-up", 595, 225, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("MAIN_USB_VALID_N", "hier")})
    s.place("R718", "R", "10k main AUX VALID pull-up", 595, 237.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("MAIN_AUX_VALID_N", "hier")})
    s.place("C746", "C_Polarized", "100u 35V hybrid selector output hold-up", 595, 292.8,
            footprint=FOOTPRINTS["C_100u_35V_hybrid"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Panasonic", "MPN": "EEHZK1V101XP"})

    s.gnd(400, 120)
    # The switched rails are physically driven through passive external FETs;
    # both selector VOUT pins are supply/sense inputs rather than power sources.
    s.pwrflag(650, 90, "VBUS_COMBINED")
    s.pwrflag(650, 45, "AUX_DC_FUSED")
    s.pwrflag(650, 60, "AUX_EFUSE_IN_SYS")
    # Keep the EC alive before source selection. These Schottky diodes OR the
    # protected battery/AUX paths and each raw PD port into one shared,
    # reverse-blocking current-limited AON eFuse before the small AON buck.
    for ref, source, source_kind, y in (
        ("D710", "BAT_CHARGER", "local", 315),
        ("D711", "AUX_DC_PROTECTED", "local", 325),
        ("D712", "PD1_VBUS_RAW", "hier", 335),
        ("D713", "PD2_VBUS_RAW", "hier", 345),
    ):
        s.place(ref, "D_Schottky", "B340A 3A 40V EC always-on OR", 650, y,
                footprint=FOOTPRINTS["D_Schottky_SMA"],
                pin_nets={"1": ("AON_OR_RAW", "local"), "2": (source, source_kind)},
                extra_props={"Manufacturer": "Diodes Incorporated", "MPN": "B340A-13-F"})
    s.place("U718", "TPS259470A", "TPS259470ARPW aggregate EC AON eFuse", 705, 335,
            footprint=FOOTPRINTS["TPS259470A"],
            pin_nets={
                "1": ("AON_EFUSE_UV", "local"), "2": ("AON_EFUSE_OV", "local"),
                "3": ("", "nc"), "4": ("AON_FAULT_N", "hier"),
                "5": ("AON_OR_RAW", "local"), "6": ("EC_AON_IN", "hier"),
                "7": ("AON_EFUSE_DVDT", "local"), "8": ("GND", "local"),
                "9": ("AON_EFUSE_ILM", "local"), "10": ("", "nc"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS259470ARPW",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps25947.pdf",
            })
    s.place("R795", "R", "301k 0.1% AON UV/OV top", 755, 315, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AON_OR_RAW", "local"), "2": ("AON_EFUSE_UV", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD07301KL"})
    s.place("R796", "R", "52.3k 0.1% AON UV/OV middle", 755, 325, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AON_EFUSE_UV", "local"), "2": ("AON_EFUSE_OV", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0752K3L"})
    s.place("R797", "R", "20.0k 0.1% AON UV/OV bottom", 755, 335, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AON_EFUSE_OV", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0720KL"})
    s.place("R798", "R", "2.21k 0.1% AON ILM 1.51A typ", 755, 345, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AON_EFUSE_ILM", "local"), "2": ("GND", "local")})
    s.place("C795", "C", "1u 25V AON eFuse input", 805, 315, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("AON_OR_RAW", "local"), "2": ("GND", "local")})
    s.place("C796", "C", "100n 50V AON eFuse input local", 805, 325, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AON_OR_RAW", "local"), "2": ("GND", "local")})
    s.place("C797", "C", "10u 25V AON eFuse output", 805, 335, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("EC_AON_IN", "hier"), "2": ("GND", "local")})
    s.place("C798", "C", "100n 50V AON eFuse output local", 805, 345, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("EC_AON_IN", "hier"), "2": ("GND", "local")})
    s.place("C799", "C", "3.3n AON eFuse dVdt", 805, 355, footprint=FOOTPRINTS["C_1n"],
            pin_nets={"1": ("AON_EFUSE_DVDT", "local"), "2": ("GND", "local")})
    s.pwrflag(650, 370, "AON_OR_RAW")
    s.text(380, 20, "J190 is the single AUX/SOLAR physical input; USB-C PD negotiation remains only on sheet 5.")
    s.text(380, 26, "TPS26630 accepts 7-22V nominal; 0.1% ladder targets 5.53V/22.99V rising UV/OV and a 3A limit.")
    s.text(380, 32, "U15 validates USB near 15V and AUX across 7-22V, gives USB priority, and prevents inactive-source backfeed.")
    s.text(380, 38.1, "SMCJ24CA protects the 67V eFuse input; active OVP protects the BQ25798 24V recommended input limit.")

    s.text(20, 220, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 226, "J2: pins 1/2 PACK+, pins 3/4 PACK-, pin 5 cell1 tap, pin 6 cell2 tap. Verify harness order before first connection.")
    s.text(20, 232, "U719 BQ7791500 autonomously protects each cell at 4.20V OV / 2.90V UV and drives back-to-back low-side FETs.")
    s.text(20, 238, "RS11=8mOhm gives 7.5A nominal OCD and 15A nominal SCD; U11/RS10 and F1 remain independent tighter/secondary protection.")
    s.text(20, 244, "No motherboard battery thermistors are fitted. U719 TS uses TI's 10k-to-VSS unused-function connection; VTB is NC.")
    s.text(20, 250, "BQ25798 /CE is fail-off: REGN pulls it high; active-high CHG_ENABLE turns Q700 on only after EC source validation.")
    s.text(20, 256, "U2 ILIM_HIZ divider is a 3.0A hardware ceiling; EC programs a lower IINDPM from the selected TPS25751A Active PDO Contract (0x31).")
    s.text(20, 263.62, "J190 is the one 7-22V nominal AUX/solar input; TPS26630 protects it before BQ25798.")
    s.text(20, 271.24, "Solar MPPT is implemented by BQ25798 firmware on this same input; there is no second charger path.")
    s.text(20, 286.48, "AUX_DC_ADC measures the post-reverse-FET input so firmware can detect droop and reduce BQ25798 input current.")
    s.text(20, 294.1, "U2 VAC1/VAC2 tie to VBUS_COMBINED in no-external-mux mode; ACDRV1/2 go to GND.")
    s.text(20, 301.72, "Q25 follows BQ25798EVM-842: SDRV disconnects pack discharge for electronic ship/hard-off while adapter charging can wake the pack.")
    s.text(20, 309.34, "U11 accepts about 8.45-13.57V nominal; 11mOhm RS10 gives 4.55A nominal and <=5.51A worst-case trips.")
    s.text(20, 316.96, "BQ25798 TS is fixed at 58.9% REGN by 5.24k/7.50k; firmware sets TS_IGNORE=1. BQ34Z100 TS has 10k to VSS; set TEMPS=0.")
    s.text(20, 324.58, "MANDATORY STARTUP: hold MU_12V_ENABLE low; read TPS25751A PD Status 0x35 plus Active PDO/RDO 0x31/0x32; program VSYSMIN and IINDPM <= min(PDO-0.25A, 2.75A); require VSYS >=10.0V.")
    s.text(20, 332.2, "Then assert MU_12V_ENABLE and require MU_12V_PG within 20ms. Any PG timeout, source-invalid, charger fault, watchdog fault, or VSYS<10V disables the Mu rail.")
    s.text(20, 339.82, "BQ25798 firmware must set STOP_WD_CHG=1 and TS_IGNORE=1, service faults, validate PDO current, and assert CHG_ENABLE only after safe limits are programmed.")
    s.text(20, 347.44, "U718 is the aggregate AON safety boundary: 1.51A typical limit, true reverse blocking, 6.20V nominal UVLO, and 22.40V nominal OVLO.")
    s.text(20, 355.06, "AON UVLO corners are 6.06-6.36V: default 5V USB-C is negotiation-only; TPS25751A dead-battery boot must obtain a valid higher-voltage PDO before EC_AON_IN starts.")
    s.text(20, 362.68, "A 5V-only USB-C source leaves the laptop off. AON_FAULT_N inhibits charging and Mu start; the service connector remains the assembly hard disconnect.")
    s.text(20, 370.3, "C746 provides low-ESR hold-up through LTC4418 break-before-make source switching.")

    # First-article pogo access. These pads are not user connectors; they make
    # the power-up and fault-state procedure electrically observable.
    for ref, label, x, y, net_name, scope in [
        ("TP1", "GND test", 860, 260, "GND", "local"),
        ("TP2", "PACK_POS_FUSED test", 880, 260, "PACK_POS_FUSED", "local"),
        ("TP3", "VSYS test", 900, 260, "VSYS", "hier"),
        ("TP4", "EC_AON_IN test", 920, 260, "EC_AON_IN", "hier"),
        ("TP7", "MCU_3V3 test", 980, 260, "MCU_3V3", "hier"),
        ("TP9", "CHG_INT_N test", 860, 280, "CHG_INT_N", "hier"),
        ("TP10", "PACK_FAULT_N test", 890, 280, "PACK_FAULT_N", "hier"),
        ("TP11", "AON_FAULT_N test", 920, 280, "AON_FAULT_N", "hier"),
    ]:
        s.place(ref, "TestPoint", label, x, y,
                footprint=FOOTPRINTS["TestPoint_Pad"],
                pin_nets={"1": (net_name, scope)},
                extra_props={"ProcurementClass": "PCB copper test feature"},
                in_bom=False)

    return s


def main():
    sheet_symbol_uuid = U()
    child_self_uuid = U()

    s = build(sheet_symbol_uuid)
    child_text = s.render(child_self_uuid, page_number="2")

    child_path = os.path.join(PROJDIR, "01_power_battery.kicad_sch")
    with open(child_path, "w", encoding="utf-8") as f:
        f.write(child_text)
    print("wrote", child_path, len(child_text), "bytes")

    # ---- Root sheet ----
    hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON_ASSERT", "CHG_ENABLE",
        "CASE_PWRBTN_N", "MU_PWRBTN_N",
        "VSYS", "MCU_3V3", "EC_AON_IN", "AUX_DC_ADC", "USB_PD_SELECTED",
        "PD1_VBUS_RAW", "PD2_VBUS_RAW",
        "PACK_FAULT_N", "PACK_RETRY_PULSE", "AUX_FAULT_N", "AUX_PGOOD",
        "MAIN_USB_VALID_N", "MAIN_AUX_VALID_N", "AON_FAULT_N",
    ]
    sheet_x, sheet_y, sheet_w, sheet_h = 50, 50, 60, 80
    pins_sexpr = []
    for i, name in enumerate(hier_nets):
        py = sheet_y + 5 + i * 6
        pins_sexpr.append(
            f'  (pin "{name}" bidirectional\n'
            f'    (at {sheet_x + sheet_w} {py} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left))\n'
            f'    (uuid {U()})\n'
            f'  )'
        )
    sheet_block = (
        f'(sheet\n'
        f'  (at {sheet_x} {sheet_y})\n'
        f'  (size {sheet_w} {sheet_h})\n'
        f'  (stroke (width 0.1524) (type solid))\n'
        f'  (fill (color 0 0 0 0.0))\n'
        f'  (uuid {sheet_symbol_uuid})\n'
        f'  (property "Sheetname" "Power & Battery"\n'
        f'    (at {sheet_x} {sheet_y - 1} 0)\n'
        f'    (effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'  )\n'
        f'  (property "Sheetfile" "01_power_battery.kicad_sch"\n'
        f'    (at {sheet_x} {sheet_y + sheet_h + 1} 0)\n'
        f'    (effects (font (size 1.27 1.27)) (justify left top))\n'
        f'  )\n'
        + "\n".join(pins_sexpr) + "\n"
        f')'
    )

    root_text = (
        f'(kicad_sch\n'
        f'  (version 20260306)\n'
        f'  (generator "eeschema")\n'
        f'  (generator_version "10.0")\n'
        f'  (uuid {U()})\n'
        f'  (paper "A4")\n'
        f'  (lib_symbols\n  )\n'
        f'{sheet_block}\n'
        f'  (sheet_instances\n'
        f'    (path "/"\n'
        f'      (page "1")\n'
        f'    )\n'
        f'  )\n'
        f'  (embedded_fonts no)\n'
        f')\n'
    )
    root_path = os.path.join(PROJDIR, "ducktop2.kicad_sch")
    with open(root_path, "w", encoding="utf-8") as f:
        f.write(root_text)
    print("wrote", root_path, len(root_text), "bytes")


if __name__ == "__main__":
    main()
