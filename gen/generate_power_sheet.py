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
    s.text(20, 20, "== U1 bq76920 3S Battery AFE / Protection ==")
    u1p1 = s.place("U1", "BQ76920PW", "BQ76920PW", 90, 60, unit=1,
                    footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
                    pin_nets={
                        "1": ("DSG_DRV", "local"), "2": ("CHG_DRV", "local"),
                        "3": ("PACK_NEG", "local"), "4": ("I2C_SDA", "hier"),
                        "5": ("I2C_SCL", "hier"),
                    })
    u1p2 = s.place("U1", "BQ76920PW", "BQ76920PW", 90, 140, unit=2,
                    footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
                    pin_nets={
                        "6": ("TS1_SENSE", "local"), "7": ("CAP1_NODE", "local"),
                        "8": ("REGOUT", "local"), "9": ("PACK_POS", "local"),
                        "10": ("PACK_POS", "local"), "11": ("", "nc"),
                        "12": ("PACK_POS", "local"), "13": ("PACK_POS", "local"),
                        "14": ("VC3_F", "local"), "15": ("VC2_F", "local"),
                        "16": ("VC1_F", "local"), "17": ("PACK_NEG", "local"),
                        "18": ("SRP_F", "local"), "19": ("SRN_F", "local"),
                        "20": ("BQ_ALERT", "hier"),
                    })

    c1 = Cur(20, 40)
    s.place("R1", "R", "1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DSG_DRV", "local"), "2": ("DSG_GATE", "local")})
    s.place("R2", "R", "100k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DSG_GATE", "local"), "2": ("FET_MID", "local")})
    s.place("R3", "R", "1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_DRV", "local"), "2": ("CHG_GATE", "local")})
    s.place("R4", "R", "100k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_GATE", "local"), "2": ("RSENSE_HI", "local")})
    s.place("Q1", "Q_NMOS", "Q_DSG (10A NMOS, TBD p/n)", *c1.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"D": ("PACK_NEG", "local"), "G": ("DSG_GATE", "local"), "S": ("FET_MID", "local")})
    s.place("Q2", "Q_NMOS", "Q_CHG (10A NMOS, TBD p/n)", *c1.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"D": ("FET_MID", "local"), "G": ("CHG_GATE", "local"), "S": ("RSENSE_HI", "local")})
    s.place("RS1", "R", "2mOhm (TBD - size for 10A cont.)", *c1.next(), footprint="",
            pin_nets={"1": ("RSENSE_HI", "local"), "2": ("GND", "local")})
    s.place("R5", "R", "1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RSENSE_HI", "local"), "2": ("SRP_F", "local")})
    s.place("R6", "R", "1k", *c1.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("GND", "local"), "2": ("SRN_F", "local")})
    s.place("C1", "C", "100n", *c1.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SRP_F", "local"), "2": ("SRN_F", "local")})
    s.place("DZ1", "D_Zener", "3.3V", *c1.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("SRP_F", "local"), "2": ("SRN_F", "local")})

    c2 = Cur(20, 150)
    s.place("R7", "R", "1k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CELL1", "local"), "2": ("VC1_F", "local")})
    s.place("C2", "C", "100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VC1_F", "local"), "2": ("PACK_NEG", "local")})
    s.place("DZ2", "D_Zener", "5.6V", *c2.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("VC1_F", "local"), "2": ("PACK_NEG", "local")})
    s.place("R8", "R", "1k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CELL2", "local"), "2": ("VC2_F", "local")})
    s.place("C3", "C", "100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VC2_F", "local"), "2": ("VC1_F", "local")})
    s.place("DZ3", "D_Zener", "5.6V", *c2.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("VC2_F", "local"), "2": ("VC1_F", "local")})
    s.place("R9", "R", "1k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS", "local"), "2": ("VC3_F", "local")})
    s.place("C4", "C", "100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VC3_F", "local"), "2": ("VC2_F", "local")})
    s.place("DZ4", "D_Zener", "5.6V", *c2.next(), footprint=FOOTPRINTS["D_Zener"],
            pin_nets={"1": ("VC3_F", "local"), "2": ("VC2_F", "local")})
    s.place("R10", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGOUT", "local"), "2": ("TS1_SENSE", "local")})
    s.place("NTC1", "Thermistor_NTC", "10k NTC", *c2.next(), footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("TS1_SENSE", "local"), "2": ("PACK_NEG", "local")})
    s.place("C5", "C", "100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("CAP1_NODE", "local"), "2": ("PACK_NEG", "local")})
    s.place("C6", "C", "1u", *c2.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("REGOUT", "local"), "2": ("PACK_NEG", "local")})
    s.place("R11", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGOUT", "local"), "2": ("BQ_ALERT", "hier")})

    s.place("J1", "Conn_01x04", "Battery balance taps (JST-XH 4pin)", 170, 40,
            footprint=FOOTPRINTS["Conn_01x04"],
            pin_nets={"1": ("PACK_POS", "local"), "2": ("CELL2", "local"),
                      "3": ("CELL1", "local"), "4": ("PACK_NEG", "local")})
    s.text(170, 30, "VERIFY: pack must expose 4-wire JST-XH balance tap (B-/C1/C2/B+)")
    s.place("F1", "Fuse", "10A (TBD)", 170, 60, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("PACK_POS", "local"), "2": ("PACK_POS_FUSED", "local")})
    s.place("J2", "Conn_01x02", "Battery power leads (heavy gauge)", 170, 80,
            footprint=FOOTPRINTS["Conn_01x02"],
            pin_nets={"1": ("PACK_POS_FUSED", "local"), "2": ("PACK_NEG", "local")})

    s.gnd(200, 90)
    s.pwrflag(200, 30, "PACK_NEG")
    s.pwrflag(200, 105, "GND")

    # ---------------- U2: BQ25798 USB-PD buck-boost charger ----------------
    s.text(260, 20, "== U2 bq25798 USB-PD Buck-Boost Charger (VSYS) ==")
    s.place("U2", "BQ25798", "BQ25798", 320, 120,
            footprint="Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm",
            pin_nets={
                "1": ("STAT_DRV", "local"), "2": ("VBUS_COMBINED", "local"),
                "3": ("VBUS_COMBINED", "local"), "4": ("BTST1_NODE", "local"),
                "5": ("REGN", "local"), "6": ("USB_DP1", "hier"), "7": ("USB_DM1", "hier"),
                "8": ("GND", "local"), "9": ("GND", "local"), "10": ("GND", "local"),
                "11": ("GND", "local"), "12": ("PMIC_QON", "hier"), "13": ("CHG_CE_N", "hier"),
                "14": ("I2C_SCL", "hier"), "15": ("I2C_SDA", "hier"), "16": ("TS2_SENSE", "local"),
                "17": ("ILIM_SET", "local"), "18": ("PACK_POS", "local"), "19": ("BTST2_NODE", "local"),
                "20": ("PROG_SET", "local"), "21": ("CHG_INT_N", "hier"), "22": ("PACK_POS", "local"),
                "23": ("PACK_POS", "local"), "24": ("", "nc"), "25": ("VSYS", "hier"),
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
    s.place("R13", "R", "100k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PMIC_QON", "hier"), "2": ("REGN", "local")})
    s.place("R14", "R", "100k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_CE_N", "hier"), "2": ("REGN", "local")})
    s.place("R15", "R", "10k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CHG_INT_N", "hier"), "2": ("REGN", "local")})
    s.place("R16", "R", "10k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("TS2_SENSE", "local")})
    s.place("R30", "R", "4.7k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("I2C_SCL", "hier")})
    s.place("R31", "R", "4.7k", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("REGN", "local"), "2": ("I2C_SDA", "hier")})
    s.place("NTC2", "Thermistor_NTC", "10k NTC", *c3.next(), footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("TS2_SENSE", "local"), "2": ("GND", "local")})
    s.place("R17", "R", "TBD (see ILIM_HIZ table)", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("ILIM_SET", "local"), "2": ("GND", "local")})
    s.place("R18", "R", "TBD (see PROG table)", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PROG_SET", "local"), "2": ("GND", "local")})
    s.place("C10", "C", "10u", *c3.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("PMID", "local"), "2": ("GND", "local")})
    s.place("C11", "C", "10u", *c3.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("L1", "L", "2.2uH (typ, verify per fsw)", *c3.next(), footprint="",
            pin_nets={"1": ("SW1", "local"), "2": ("SW2", "local")})

    c4 = Cur(380, 40)
    s.place("D5", "D_Schottky", "", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_PD1", "hier")})
    s.place("D6", "D_Schottky", "", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_PD2", "hier")})
    s.place("D7", "D_Schottky", "", *c4.next(), footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("VBUS_PD3", "hier")})
    s.place("C12", "C", "10u", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("GND", "local")})

    s.gnd(400, 120)
    s.pwrflag(400, 30, "VBUS_COMBINED")
    s.text(380, 20, "D5-D7: K(pin1)=VBUS_COMBINED, A(pin2)=port raw VBUS")

    # ---------------- U3: BQ24650 Solar MPPT charger ----------------
    s.text(460, 20, "== U3 bq24650 Solar MPPT Charger ==")
    s.place("U3", "BQ24650", "BQ24650", 520, 120,
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
    s.place("R19", "R", "100k (TBD-verify MPPT ratio)", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("MPPSET_ADJ", "local")})
    s.place("R20", "R", "10k (TBD-verify MPPT ratio)", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MPPSET_ADJ", "local"), "2": ("GND", "local")})
    s.place("R21", "R", "1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("STAT1_LED_A", "local")})
    s.place("LED2", "LED", "MPPT STAT1", *c5.next(), footprint=FOOTPRINTS["LED"],
            pin_nets={"2": ("STAT1_LED_A", "local"), "1": ("STAT1_DRV", "local")})
    s.place("R22", "R", "1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("STAT2_LED_A", "local")})
    s.place("LED3", "LED", "MPPT STAT2", *c5.next(), footprint=FOOTPRINTS["LED"],
            pin_nets={"2": ("STAT2_LED_A", "local"), "1": ("STAT2_DRV", "local")})
    s.place("R23", "R", "10k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VREF3", "local"), "2": ("TS3_SENSE", "local")})
    s.place("NTC3", "Thermistor_NTC", "10k NTC", *c5.next(), footprint=FOOTPRINTS["Thermistor_NTC"],
            pin_nets={"1": ("TS3_SENSE", "local"), "2": ("GND", "local")})
    s.place("C13", "C", "100n", *c5.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VREF3", "local"), "2": ("GND", "local")})
    s.place("R24", "R", "TBD (see VFB table)", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS", "local"), "2": ("VFB_ADJ", "local")})
    s.place("R25", "R", "TBD (see VFB table)", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VFB_ADJ", "local"), "2": ("GND", "local")})
    s.place("R26", "R", "1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SOLAR_ISNS_HI_RAW", "local"), "2": ("SRP3_F", "local")})
    s.place("R27", "R", "1k", *c5.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS", "local"), "2": ("SRN3_F", "local")})
    s.place("C14", "C", "100n", *c5.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SRP3_F", "local"), "2": ("SRN3_F", "local")})

    c6 = Cur(580, 40)
    s.place("C15", "C", "100n", *c6.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BTST3_NODE", "local"), "2": ("SOLAR_SW", "local")})
    s.place("C16", "C", "1u", *c6.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("REGN3", "local"), "2": ("GND", "local")})
    s.place("R28", "R", "4.7", *c6.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("HIDRV3", "local"), "2": ("QHI_GATE", "local")})
    s.place("R29", "R", "4.7", *c6.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("LODRV3", "local"), "2": ("QLO_GATE", "local")})
    s.place("Q3", "Q_NMOS", "Q_HI solar buck (TBD p/n)", *c6.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"D": ("SOLAR_IN", "local"), "G": ("QHI_GATE", "local"), "S": ("SOLAR_SW", "local")})
    s.place("Q4", "Q_NMOS", "Q_LO solar buck (TBD p/n)", *c6.next(), footprint=FOOTPRINTS["Q_power"],
            pin_nets={"D": ("SOLAR_SW", "local"), "G": ("QLO_GATE", "local"), "S": ("GND", "local")})
    s.place("L2", "L", "4.7uH (typ, verify)", *c6.next(), footprint="",
            pin_nets={"1": ("SOLAR_SW", "local"), "2": ("SOLAR_ISNS_HI_RAW", "local")})
    s.place("RS2", "R", "10mOhm (TBD - size for solar current)", *c6.next(), footprint="",
            pin_nets={"1": ("SOLAR_ISNS_HI_RAW", "local"), "2": ("PACK_POS", "local")})
    s.place("C17", "C", "1u", *c6.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("GND", "local")})

    s.place("J3", "Conn_01x02", "Solar panel input", 640, 40, footprint=FOOTPRINTS["Conn_01x02"],
            pin_nets={"1": ("SOLAR_IN_RAW", "local"), "2": ("GND", "local")})
    s.place("F2", "Fuse", "3A (TBD)", 640, 60, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SOLAR_IN_RAW", "local"), "2": ("SOLAR_IN_FUSED", "local")})
    s.place("D8", "D_Schottky", "reverse-polarity block", 640, 80, footprint=FOOTPRINTS["D_Schottky"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("SOLAR_IN_FUSED", "local")})
    s.place("C18", "C", "10u", 640, 100, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SOLAR_IN", "local"), "2": ("GND", "local")})

    s.gnd(660, 120)
    s.pwrflag(660, 30, "SOLAR_IN")

    s.text(20, 220, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 226, "TS1/TS2/TS3 use independent thermistor dividers per-IC (not shared) per design decision.")
    s.text(20, 232, "I2C pull-ups R30 (SCL)/R31 (SDA) sourced from U2 REGN only, to avoid cross-LDO backfeed between REGOUT and REGN.")
    s.text(20, 238, "SDRV (U2 pin24) intentionally left NC - ship-mode FET not yet designed.")

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
        "VSYS", "VBUS_PD1", "VBUS_PD2", "VBUS_PD3", "USB_DP1", "USB_DM1",
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
