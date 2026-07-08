import os
from build_ducktop2 import Sheet, U, PROJDIR, FOOTPRINTS

SHEET_SYMBOL_UUID = None  # filled by main()


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

    # ---------------- U1: BQ76920PW battery AFE ----------------
    s.text(20, 20, "== U1 bq76920 3S Battery AFE / Protection (optional/DNP with protected pack) ==")
    u1p1 = s.place("U1", "BQ76920PW", "BQ76920PW (DNP if pack BMS remains)", 90, 60, unit=1,
                    footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
                    pin_nets={
                        "1": ("DSG_DRV", "local"), "2": ("CHG_DRV", "local"),
                        "3": ("CELL0_BAL", "local"), "4": ("I2C_SDA", "hier"),
                        "5": ("I2C_SCL", "hier"),
                    })
    u1p2 = s.place("U1", "BQ76920PW", "BQ76920PW (DNP if pack BMS remains)", 90, 140, unit=2,
                    footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
                    pin_nets={
                        "6": ("TS1_SENSE", "local"), "7": ("CAP1_NODE", "local"),
                        "8": ("REGOUT", "local"), "9": ("CELL3_BAL", "local"),
                        "10": ("CELL3_BAL", "local"), "11": ("", "nc"),
                        "12": ("CELL3_BAL", "local"), "13": ("CELL3_BAL", "local"),
                        "14": ("VC3_F", "local"), "15": ("VC2_F", "local"),
                        "16": ("VC1_F", "local"), "17": ("CELL0_BAL", "local"),
                        "18": ("SRP_F", "local"), "19": ("SRN_F", "local"),
                        "20": ("BQ_ALERT", "hier"),
                    })

    c1 = Cur(20, 40)
    s.place("R1", "R", "DNP 1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DSG_DRV", "local"), "2": ("DSG_GATE", "local")})
    s.place("R2", "R", "DNP 100k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DSG_GATE", "local"), "2": ("FET_MID", "local")})
    s.place("R3", "R", "DNP 1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_DRV", "local"), "2": ("CHG_GATE", "local")})
    s.place("R4", "R", "DNP 100k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_GATE", "local"), "2": ("PACK_NEG_RAW", "local")})
    s.place("Q1", "Q_NMOS_TO252_GDS", "DNP IPD90N04S4L-04 Q_DSG bare-cell pack", *c1.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"1": ("DSG_GATE", "local"), "2": ("CELL0_BAL", "local"), "3": ("FET_MID", "local")})
    s.place("Q2", "Q_NMOS_TO252_GDS", "DNP IPD90N04S4L-04 Q_CHG bare-cell pack", *c1.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"1": ("CHG_GATE", "local"), "2": ("FET_MID", "local"), "3": ("PACK_NEG_RAW", "local")})
    s.place("RS1", "R", "5mOhm 1% Kelvin gauge shunt >=5A", *c1.next(), footprint="Resistor_SMD:R_2512_6332Metric",
            pin_nets={"1": ("PACK_NEG_RAW", "local"), "2": ("GND", "local")})
    s.place("R5", "R", "DNP 1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_NEG_RAW", "local"), "2": ("SRP_F", "local")})
    s.place("R6", "R", "DNP 1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("GND", "local"), "2": ("SRN_F", "local")})
    s.place("C1", "C", "DNP 100n", *c1.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SRP_F", "local"), "2": ("SRN_F", "local")})
    s.place("DZ1", "D_Zener", "DNP 3.3V", *c1.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("SRP_F", "local"), "2": ("SRN_F", "local")})

    c2 = Cur(20, 150)
    s.place("R7", "R", "DNP 1k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CELL1", "local"), "2": ("VC1_F", "local")})
    s.place("C2", "C", "DNP 100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VC1_F", "local"), "2": ("CELL0_BAL", "local")})
    s.place("DZ2", "D_Zener", "DNP 5.6V", *c2.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("VC1_F", "local"), "2": ("CELL0_BAL", "local")})
    s.place("R8", "R", "DNP 1k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CELL2", "local"), "2": ("VC2_F", "local")})
    s.place("C3", "C", "DNP 100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VC2_F", "local"), "2": ("VC1_F", "local")})
    s.place("DZ3", "D_Zener", "DNP 5.6V", *c2.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("VC2_F", "local"), "2": ("VC1_F", "local")})
    s.place("R9", "R", "DNP 1k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CELL3_BAL", "local"), "2": ("VC3_F", "local")})
    s.place("C4", "C", "DNP 100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VC3_F", "local"), "2": ("VC2_F", "local")})
    s.place("DZ4", "D_Zener", "DNP 5.6V", *c2.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("VC3_F", "local"), "2": ("VC2_F", "local")})
    s.place("R10", "R", "DNP 10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGOUT", "local"), "2": ("TS1_SENSE", "local")})
    s.place("NTC1", "Thermistor_NTC", "DNP 10k NTC", *c2.next(), footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("TS1_SENSE", "local"), "2": ("CELL0_BAL", "local")})
    s.place("C5", "C", "DNP 100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("CAP1_NODE", "local"), "2": ("CELL0_BAL", "local")})
    s.place("C6", "C", "DNP 1u", *c2.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("REGOUT", "local"), "2": ("CELL0_BAL", "local")})
    s.place("R11", "R", "DNP 10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGOUT", "local"), "2": ("BQ_ALERT", "hier")})

    s.place("J1", "Conn_01x04", "DNP sense-only balance taps (B+/C2/C1/B-)", 170, 40,
            footprint=FOOTPRINTS["Conn_01x04"],
            pin_nets={"1": ("CELL3_BAL", "local"), "2": ("CELL2", "local"),
                      "3": ("CELL1", "local"), "4": ("CELL0_BAL", "local")})
    s.text(170, 30, "Balance taps are sense-only and DNP by default; they never feed PACK_POS_FUSED.")
    s.pwrflag(145, 30, "CELL3_BAL")
    s.pwrflag(145, 45, "CELL0_BAL")
    s.place("F1", "Fuse", "10A replaceable pack fuse", 170, 60, footprint=FOOTPRINTS["Fuse_Pack_Blade_Mini"],
            pin_nets={"1": ("PACK_POS_RAW", "local"), "2": ("PACK_POS_FUSED", "local")})
    s.place("J2", "Conn_01x02", "Battery power leads (heavy gauge)", 170, 80,
            footprint=FOOTPRINTS["Conn_01x02_Pack_MegaFit"],
            pin_nets={"1": ("PACK_POS_RAW", "local"), "2": ("PACK_NEG_RAW", "local")})

    s.gnd(200, 90)
    s.pwrflag(200, 30, "PACK_POS_RAW")
    s.pwrflag(200, 45, "PACK_NEG_RAW")
    s.pwrflag(200, 105, "GND")

    # ---------------- U10: protected-pack fuel gauge ----------------
    s.text(170, 125, "== U10 BQ34Z100-G1 3S fuel gauge for protected external pack ==")
    s.place("U10", "BQ34Z100-G1", "BQ34Z100-G1 protected-pack gauge", 230, 175,
            footprint=FOOTPRINTS["BQ34Z100-G1"],
            pin_nets={
                "1": ("FG_P2_TIE", "local"),
                "2": ("", "nc"),
                "3": ("FG_P1_TIE", "local"),
                "4": ("FG_BAT_SENSE", "local"),
                "5": ("FG_CE", "local"),
                "6": ("MCU_3V3", "hier"),
                "7": ("FG_REG25", "local"),
                "8": ("GND", "local"),
                "9": ("FG_SRP", "local"),
                "10": ("FG_SRN", "local"),
                "11": ("FG_TS", "local"),
                "12": ("", "nc"),
                "13": ("I2C_SCL", "hier"),
                "14": ("I2C_SDA", "hier"),
            })
    s.place("R180", "R", "215k 0.1% pack divider hi", 170, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("FG_BAT_DIV", "local")})
    s.place("R181", "R", "16.5k 0.1% pack divider lo", 170, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_BAT_DIV", "local"), "2": ("GND", "local")})
    s.place("R182", "R", "100R BAT filter", 170, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_BAT_DIV", "local"), "2": ("FG_BAT_SENSE", "local")})
    s.place("C180", "C", "100n BAT filter", 170, 180, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FG_BAT_SENSE", "local"), "2": ("GND", "local")})
    s.place("R183", "R", "100R SRP filter", 170, 190, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_NEG_RAW", "local"), "2": ("FG_SRP", "local")})
    s.place("R184", "R", "100R SRN filter", 170, 200, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("GND", "local"), "2": ("FG_SRN", "local")})
    s.place("C181", "C", "100n sense filter", 170, 210, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FG_SRP", "local"), "2": ("FG_SRN", "local")})
    s.place("R185", "R", "10k CE pull-up", 290, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FG_CE", "local")})
    s.place("R186", "R", "10k gauge ALERT pull-up", 290, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BQ_ALERT", "hier")})
    s.place("R187", "R", "10k TS pull-up", 290, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FG_TS", "local")})
    s.place("NTC4", "Thermistor_NTC", "10k pack NTC", 290, 180, footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("FG_TS", "local"), "2": ("GND", "local")})
    s.place("C182", "C", "100n REGIN/VCC", 290, 190, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C183", "C", "1u REG25", 290, 200, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("FG_REG25", "local"), "2": ("GND", "local")})
    s.place("R188", "R", "0R P2 not-used tie to VSS", 345, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_P2_TIE", "local"), "2": ("GND", "local")})
    s.place("R189", "R", "0R P1 not-used tie to VSS", 345, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_P1_TIE", "local"), "2": ("GND", "local")})

    # ---------------- U2: BQ25798 buck-boost charger / NVDC path ----------------
    s.text(260, 20, "== U2 bq25798 Buck-Boost Charger / NVDC Power Path (VSYS) ==")
    s.place("U2", "BQ25798", "BQ25798", 320, 120,
            footprint="Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm",
            pin_nets={
                "1": ("STAT_DRV", "local"), "2": ("VBUS_COMBINED", "local"),
                "3": ("VBUS_COMBINED", "local"), "4": ("BTST1_NODE", "local"),
                "5": ("REGN", "local"), "6": ("USB_DP1", "hier"), "7": ("USB_DM1", "hier"),
                "8": ("VBUS_COMBINED", "local"), "9": ("VBUS_COMBINED", "local"), "10": ("GND", "local"),
                "11": ("GND", "local"), "12": ("PMIC_QON", "hier"), "13": ("CHG_CE_N", "hier"),
                "14": ("I2C_SCL", "hier"), "15": ("I2C_SDA", "hier"), "16": ("TS2_SENSE", "local"),
                "17": ("ILIM_SET", "local"), "18": ("PACK_POS_FUSED", "local"), "19": ("BTST2_NODE", "local"),
                "20": ("PROG_SET", "local"), "21": ("CHG_INT_N", "hier"), "22": ("PACK_POS_FUSED", "local"),
                "23": ("PACK_POS_FUSED", "local"), "24": ("SDRV_DAMP", "local"), "25": ("VSYS", "hier"),
                "26": ("SW2", "local"), "27": ("GND", "local"), "28": ("SW1", "local"),
                "29": ("PMID", "local"),
            })

    c3 = Cur(260, 40)
    s.place("R12", "R", "1k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("STAT_LED_A", "local")})
    s.place("LED1", "LED", "Charge STAT", *c3.next(), footprint=FOOTPRINTS["LED"],
            pin_nets={"2": ("STAT_LED_A", "local"), "1": ("STAT_DRV", "local")})
    s.place("C7", "C", "100n", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BTST1_NODE", "local"), "2": ("SW1", "local")})
    s.place("C8", "C", "100n", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BTST2_NODE", "local"), "2": ("SW2", "local")})
    s.place("C9", "C", "1u", *c3.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("REGN", "local"), "2": ("GND", "local")})
    s.place("R13", "R", "100k QON pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PMIC_QON", "hier"), "2": ("MCU_3V3", "hier")})
    s.place("R14", "R", "100k CE pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_CE_N", "hier"), "2": ("MCU_3V3", "hier")})
    s.place("R15", "R", "10k INT pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_INT_N", "hier"), "2": ("MCU_3V3", "hier")})
    s.place("R16", "R", "10k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("TS2_SENSE", "local")})
    s.place("R30", "R", "4.7k I2C SCL pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("I2C_SCL", "hier")})
    s.place("R31", "R", "4.7k I2C SDA pull-up to 3V3", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("I2C_SDA", "hier")})
    s.place("NTC2", "Thermistor_NTC", "10k NTC", *c3.next(), footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("TS2_SENSE", "local"), "2": ("GND", "local")})
    s.place("R17", "R", "47k 1% ILIM top (3A clamp)", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("ILIM_SET", "local")})
    s.place("R190", "R", "100k 1% ILIM bottom", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("ILIM_SET", "local"), "2": ("GND", "local")})
    s.place("R18", "R", "10.5k 1% PROG: 3S, 1.5MHz", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PROG_SET", "local"), "2": ("GND", "local")})
    s.place("C10", "C", "10u", *c3.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("PMID", "local"), "2": ("GND", "local")})
    s.place("C11", "C", "10u", *c3.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("L1", "L", "2.2uH >=6A buck-boost", *c3.next(), footprint=FOOTPRINTS["L_buck"],
            pin_nets={"1": ("SW1", "local"), "2": ("SW2", "local")})
    s.place("C184", "C", "1nF SDRV cap, ship FET unused", *c3.next(), footprint=FOOTPRINTS["C_1n"],
            pin_nets={"1": ("SDRV_DAMP", "local"), "2": ("GND", "local")})

    c4 = Cur(380, 40)
    s.place("D5", "D_Schottky", "", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_PD1", "hier")})
    s.place("D6", "D_Schottky", "", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_PD2", "hier")})
    s.place("D7", "D_Schottky", "", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_PD3", "hier")})
    s.place("C12", "C", "10u", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("GND", "local")})
    s.place("J190", "Conn_01x02", "AUX/SOLAR wide-DC screw terminal 6-24V nominal", *c4.next(),
            footprint=FOOTPRINTS["Terminal_01x02_5.08"],
            pin_nets={"1": ("AUX_DC_RAW", "local"), "2": ("GND", "local")})
    s.place("F190", "Fuse", "3A AUX/SOLAR input fuse/polyfuse", *c4.next(), footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("AUX_DC_RAW", "local"), "2": ("AUX_DC_FUSED", "local")})
    s.place("D190", "D_TVS", "SMBJ24CA-class AUX/SOLAR input TVS", *c4.next(), footprint=FOOTPRINTS["D_TVS"],
            pin_nets={"1": ("AUX_DC_FUSED", "local"), "2": ("GND", "local")})
    s.place("D191", "D_Schottky", "POP default AUX -> BQ25798 reverse block", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("AUX_DC_FUSED", "local")})
    s.place("C190", "C", "10u AUX input bulk", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("AUX_DC_FUSED", "local"), "2": ("GND", "local")})
    s.place("C191", "C", "100n AUX input", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AUX_DC_FUSED", "local"), "2": ("GND", "local")})
    s.place("R191", "R", "470k 1% AUX ADC top", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_FUSED", "local"), "2": ("AUX_DC_DIV", "local")})
    s.place("R192", "R", "56k 1% AUX ADC bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_DIV", "local"), "2": ("GND", "local")})
    s.place("R193", "R", "1k AUX ADC series", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_DIV", "local"), "2": ("AUX_DC_ADC", "hier")})
    s.place("C192", "C", "100n AUX ADC filter", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AUX_DC_ADC", "hier"), "2": ("GND", "local")})

    s.gnd(400, 120)
    s.pwrflag(400, 30, "VBUS_COMBINED")
    s.text(380, 20, "D5-D7/D191: K(pin1)=VBUS_COMBINED, A(pin2)=input raw/fused VBUS")
    s.text(380, 26, "J190 is the single AUX/SOLAR physical input; USB-C PD negotiation remains only on sheet 5.")
    s.text(380, 32, "AUX divider maps 24V to about 2.56V and 30V abs-max to about 3.19V at the EC ADC.")
    s.text(380, 38.1, "Default build populates D191 for random DC; solar option feeds U3 from same terminal via D8.")
    s.text(380, 44.45, "Do not populate D8 and D191 together unless dual-charger input policy is intentionally reviewed.")

    # ---------------- U3: BQ24650 Solar MPPT charger ----------------
    s.text(460, 20, "== U3 bq24650 optional solar MPPT from shared AUX/SOLAR input ==")
    s.place("U3", "BQ24650", "DNP BQ24650 optional solar MPPT", 520, 120,
            footprint="Package_DFN_QFN:Texas_RVA_VQFN-16-1EP_3.5x3.5mm_P0.5mm_EP2.14x2.14mm_ThermalVias",
            pin_nets={
                "1": ("SOLAR_IN", "local"), "2": ("MPPSET_ADJ", "local"), "3": ("STAT1_DRV", "local"),
                "4": ("TS3_SENSE", "local"), "5": ("STAT2_DRV", "local"), "6": ("VREF3", "local"),
                "7": ("VREF3", "local"), "8": ("VFB_ADJ", "local"), "9": ("SRN3_F", "local"),
                "10": ("SRP3_F", "local"), "11": ("GND", "local"), "12": ("REGN3", "local"),
                "13": ("LODRV3", "local"), "14": ("SOLAR_SW", "local"), "15": ("HIDRV3", "local"),
                "16": ("BTST3_NODE", "local"), "17": ("GND", "local"),
            })

    c5 = Cur(460, 40)
    s.place("R19", "R", "DNP 140k 1% MPPSET top (18V)", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("MPPSET_ADJ", "local")})
    s.place("R20", "R", "DNP 10k 1% MPPSET bottom", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MPPSET_ADJ", "local"), "2": ("GND", "local")})
    s.place("R21", "R", "DNP 1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("STAT1_LED_A", "local")})
    s.place("LED2", "LED", "DNP MPPT STAT1", *c5.next(), footprint=FOOTPRINTS["LED"],
            pin_nets={"2": ("STAT1_LED_A", "local"), "1": ("STAT1_DRV", "local")})
    s.place("R22", "R", "DNP 1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("STAT2_LED_A", "local")})
    s.place("LED3", "LED", "DNP MPPT STAT2", *c5.next(), footprint=FOOTPRINTS["LED"],
            pin_nets={"2": ("STAT2_LED_A", "local"), "1": ("STAT2_DRV", "local")})
    s.place("R23", "R", "DNP 10k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VREF3", "local"), "2": ("TS3_SENSE", "local")})
    s.place("NTC3", "Thermistor_NTC", "DNP 10k NTC", *c5.next(), footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("TS3_SENSE", "local"), "2": ("GND", "local")})
    s.place("C13", "C", "DNP 1u VREF", *c5.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("VREF3", "local"), "2": ("GND", "local")})
    s.place("R24", "R", "DNP 499k 0.1% 3S charge VFB hi", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("VFB_ADJ", "local")})
    s.place("R25", "R", "DNP 100k 0.1% 3S charge VFB lo", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VFB_ADJ", "local"), "2": ("GND", "local")})
    s.place("R26", "R", "DNP 1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_ISNS_HI_RAW", "local"), "2": ("SRP3_F", "local")})
    s.place("R27", "R", "DNP 1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("SRN3_F", "local")})
    s.place("C14", "C", "DNP 100n", *c5.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SRP3_F", "local"), "2": ("SRN3_F", "local")})

    c6 = Cur(580, 40)
    s.place("C15", "C", "DNP 100n", *c6.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BTST3_NODE", "local"), "2": ("SOLAR_SW", "local")})
    s.place("C16", "C", "DNP 1u", *c6.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("REGN3", "local"), "2": ("GND", "local")})
    s.place("R28", "R", "DNP 4.7", *c6.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("HIDRV3", "local"), "2": ("QHI_GATE", "local")})
    s.place("R29", "R", "DNP 4.7", *c6.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("LODRV3", "local"), "2": ("QLO_GATE", "local")})
    s.place("Q3", "Q_NMOS_TO252_GDS", "DNP IPD50N04S4L-08 solar high-side FET", *c6.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"1": ("QHI_GATE", "local"), "2": ("SOLAR_IN", "local"), "3": ("SOLAR_SW", "local")})
    s.place("Q4", "Q_NMOS_TO252_GDS", "DNP IPD50N04S4L-08 solar low-side FET", *c6.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"1": ("QLO_GATE", "local"), "2": ("SOLAR_SW", "local"), "3": ("GND", "local")})
    s.place("L2", "L", "DNP 10uH >=3A solar buck", *c6.next(), footprint=FOOTPRINTS["L_buck"],
            pin_nets={"1": ("SOLAR_SW", "local"), "2": ("SOLAR_ISNS_HI_RAW", "local")})
    s.place("RS2", "R", "DNP 40mOhm 1% solar sense, 1A fast-charge", *c6.next(), footprint="Resistor_SMD:R_2512_6332Metric",
            pin_nets={"1": ("SOLAR_ISNS_HI_RAW", "local"), "2": ("PACK_POS_FUSED", "local")})
    s.place("C17", "C", "DNP 1u", *c6.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("GND", "local")})
    s.place("D8", "D_Schottky", "DNP solar MPPT feed from AUX/SOLAR input", *c6.next(),
            footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("AUX_DC_FUSED", "local")})
    s.place("C18", "C", "DNP 10u solar MPPT input bulk", *c6.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("GND", "local")})

    s.gnd(660, 120)
    s.pwrflag(660, 30, "SOLAR_IN")

    s.text(20, 220, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 226, "The real pack already has a protection-only BMS; U1/Q1/Q2 are optional/DNP unless a bare-cell pack is used.")
    s.text(20, 232, "RS1 remains populated as the BQ34Z100-G1 low-side current shunt; Kelvin route SRP/SRN per TI layout guidance.")
    s.text(20, 238, "U10 pinout is verified against TI Table 5-1; divider 215k/16.5k gives about 0.90V at 12.6V full-charge 3S.")
    s.text(20, 244, "TS1/TS2/TS3/FG_TS use independent thermistor dividers per-IC (not shared) per design decision.")
    s.text(20, 250, "Charger I2C/INT/QON/CE pull-ups use MCU_3V3 so STM32 pins never see REGN-level logic.")
    s.text(20, 256, "U2 ILIM_HIZ divider sets about 3A input-current clamp from REGN; PROG selects 3S/1.5MHz POR defaults.")
    s.text(20, 263.62, "J190 is shared: default random-DC mode populates D191 to U2; solar mode populates D8/U3 MPPT option.")
    s.text(20, 271.24, "If solar option is used, U3 starts at 18V nominal MPP, 12.6V 3S regulation, and 1A solar charge current.")
    s.text(20, 278.86, "Default BOM should not populate D8 with D191; choose random-DC charger input or solar MPPT behavior for J190.")
    s.text(20, 286.48, "AUX_DC_ADC lets EC firmware detect random bench/DC inputs and reduce BQ25798 input current if the source droops.")
    s.text(20, 294.1, "U2 VAC1/VAC2 tie to VBUS_COMBINED in no-external-mux mode; ACDRV1/2 go to GND.")
    s.text(20, 301.72, "SDRV has 1nF to GND because the ship FET is unused in this first integrated laptop spin.")
    s.text(20, 309.34, "DNP Q1/Q2 candidate: Infineon IPD90N04S4L-04, 40V 3.8mR DPAK, active/preferred, pin 1=G 2=D/tab 3=S.")
    s.text(20, 316.96, "DNP Q3/Q4 candidate: Infineon IPD50N04S4L-08, 40V 7.3mR DPAK, lower Qg for BQ24650 6V gate drive.")

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
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "MCU_3V3", "AUX_DC_ADC", "VBUS_PD1", "VBUS_PD2", "VBUS_PD3", "USB_DP1", "USB_DM1",
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
