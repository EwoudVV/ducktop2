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
    s.paper = (1400, 1100)

    class Cur:
        def __init__(self, x0, y0, col_w=55, row_h=10, rows_per_col=22):
            self.x0, self.y0, self.col_w, self.row_h, self.rows = x0, y0, col_w, row_h, rows_per_col
            self.i = 0

        def next(self):
            col, row = divmod(self.i, self.rows)
            self.i += 1
            return (self.x0 + col * self.col_w, self.y0 + row * self.row_h)

    # The BMS provides pack protection. The purchased cells retain their
    # protection boards until their exact ratings and series use are verified.
    # ---- Board split Phase 2.4: pack protection moved to the BMS board ----
    # The pack connector, fuse, BQ77915, LTC4368, FETs, and shunts now live
    # on the BMS daughterboard (bms/bms.kicad_sch). The gauge (U10), charger
    # (U2), and battery power-path FET (Q25) stay here. FPC-3 boundary nets below.
    s.gnd(200, 90)
    s.pwrflag(200, 45, "FG_VSS")
    s.pwrflag(200, 105, "GND")
    s.text(200, 55, "FPC-3 to BMS: PACK_POS_FUSED / PACK_FAULT_N / PACK_RETRY_PULSE cross here")
    # The protected pack rail crosses FPC-3 as PACK_POS_FUSED (BMS LTC4368
    # output). The gauge divider and the charger BAT sense both tap this
    # rail; it was historically named BAT_PROT_VIN here and is reconciled
    # to the FPC-3 contract name (Phase 4a).
    s.pwrflag(650, 30, "PACK_POS_FUSED")

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
                "8": ("FG_VSS", "hier"),
                "9": ("FG_SRP", "local"),
                "10": ("FG_SRN", "local"),
                "11": ("FG_TS", "local"),
                "12": ("", "nc"),
                "13": ("I2C_SCL", "hier"),
                "14": ("I2C_SDA", "hier"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "BQ34Z100PWR-G1"})
    s.place("R180", "R", "220k 0.1% <=25ppm pack divider hi", 170, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PACK_POS_FUSED", "hier"), "2": ("FG_BAT_DIV", "local")})
    # The gauge's 5 mOhm Kelvin shunt stays on center (Phase 2.4): it measures
    # the system-side current through FG_VSS, distinct from the pack shunts
    # (RS10/RS11) which moved to the BMS board.
    s.place("RS1", "R", "5mOhm 1% 2W BQ34Z100 Kelvin shunt", 170, 120,
            footprint="Resistor_SMD:R_2512_6332Metric",
            pin_nets={"1": ("FG_VSS", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Vishay Dale", "MPN": "WSLP25125L000FEA"})

    s.place("R181", "R", "16.5k 0.1% pack divider lo", 170, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_BAT_DIV", "local"), "2": ("FG_VSS", "hier")})
    s.place("R182", "R", "100R BAT filter", 170, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_BAT_DIV", "local"), "2": ("FG_BAT_SENSE", "local")})
    s.place("C180", "C", "100n BAT filter", 170, 180, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FG_BAT_SENSE", "local"), "2": ("FG_VSS", "hier")})
    s.place("R183", "R", "100R SRP filter", 170, 190, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_VSS", "hier"), "2": ("FG_SRP", "local")})
    s.place("R184", "R", "100R SRN filter", 170, 200, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("GND", "local"), "2": ("FG_SRN", "local")})
    s.place("C181", "C", "100n sense filter", 170, 210, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FG_SRP", "local"), "2": ("FG_SRN", "local")})
    s.place("R185", "R", "10k CE pull-up", 290, 150, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FG_CE", "local")})
    s.place("R186", "R", "10k gauge ALERT pull-up", 290, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BQ_ALERT", "hier")})
    s.place("C182", "C", "100n REGIN/VCC", 290, 190, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FG_VSS", "hier")})
    s.place("C183", "C", "1u REG25", 290, 200, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("FG_REG25", "local"), "2": ("FG_VSS", "hier")})
    s.place("R189", "R", "0R P1 not-used tie to VSS", 345, 160, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_P1_TIE", "local"), "2": ("FG_VSS", "hier")})
    s.place("R855", "R", "10k unused external TS pulldown", 345, 170, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FG_TS", "local"), "2": ("FG_VSS", "hier")})

    # The charger block is kept together with its power and hardware gates.
    from generate_isl9241_charger import add_charger
    add_charger(s)
    from generate_power_control import add_power_control
    add_power_control(s)

    c4 = Cur(380, 40)
    s.place("C12", "C", "100n 50V X7R VBUS local", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D"})

    s.place("F190", "Fuse", "3A MINI AUX input fuse: Littelfuse 0297003.WXNV", *c4.next(),
            footprint=FOOTPRINTS["Fuse_Pack_Blade_Mini"],
            pin_nets={"1": ("AUX_DC_RAW", "hier"), "2": ("AUX_DC_FUSED", "local")},
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
    # Readability: U12 (25-pin eFuse, tall body) sat inside the c4 passive
    # column at x=380 overlapping Q13/Q14/R710/R711. Waste one c4 slot, move
    # U12 +25 mm right to clear the column. Nets unchanged.
    c4.next()
    s.place("U12", "TPS26630RGE", "TPS26630RGER 3A AUX eFuse / surge cutoff", 405.13, 90.17,
            footprint=FOOTPRINTS["TPS26630RGE"],
            pin_nets={
                "1": ("AUX_DC_FUSED", "local"), "2": ("AUX_DC_FUSED", "local"),
                "3": ("AUX_EFUSE_BGATE", "local"), "4": ("AUX_EFUSE_DRV", "local"),
                "5": ("AUX_EFUSE_IN_SYS", "local"), "6": ("AUX_EFUSE_UV", "local"),
                "7": ("AUX_EFUSE_OV", "local"), "8": ("GND", "local"),
                "9": ("AUX_EFUSE_DVDT", "local"), "10": ("AUX_EFUSE_ILIM", "local"),
                "11": ("GND", "local"), "12": ("AUX_EFUSE_SHDN", "local"), "13": ("", "nc"),
                "14": ("AUX_FAULT_N", "hier"), "15": ("AUX_PGTH", "local"), "16": ("AUX_PGOOD", "hier"),
                "17": ("AUX_DC_PROTECTED", "local"), "18": ("AUX_DC_PROTECTED", "local"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("", "nc"),
                "22": ("", "nc"), "23": ("", "nc"), "24": ("", "nc"),
                "25": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS26630RGER"})
    s.place("R710", "R", "6.04k 1% AUX 3A current limit", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_ILIM", "local"), "2": ("GND", "local")})
    s.place("R711", "R", "300k 0.1% 10ppm AUX UV/OV top", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_IN_SYS", "local"), "2": ("AUX_EFUSE_UV", "local")},
            extra_props={"Manufacturer": "Vishay", "MPN": "TNPW0603300KBYEA"})
    s.place("R712", "R", "63.4k 0.02% 5ppm AUX UV/OV middle", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_UV", "local"), "2": ("AUX_EFUSE_OV", "local")},
            extra_props={"Manufacturer": "Vishay", "MPN": "TNPU060363K4HZEN00"})
    s.place("R713", "R", "20.0k 0.02% 5ppm AUX UV/OV bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_OV", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Vishay", "MPN": "TNPU060320K0HZEN00"})
    s.place("R714", "R", "31R AUX reverse-FET pulldown gate", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_EFUSE_DRV", "local"), "2": ("AUX_EFUSE_Q2_GATE", "local")})
    s.place("R715", "R", "10k AUX eFuse FLT pull-up", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("AUX_FAULT_N", "hier")})
    s.place("R716", "R", "10k AUX eFuse PGOOD pull-up", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("AUX_PGOOD", "hier")})
    s.place("R739", "R", "332k 0.1% 10ppm AUX PGOOD threshold top", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_PROTECTED", "local"), "2": ("AUX_PGTH", "local")},
            extra_props={"Manufacturer": "Vishay", "MPN": "TNPW0603332KBYEA"})
    s.place("R740", "R", "97.6k 0.02% 5ppm AUX PGOOD threshold bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_PGTH", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Vishay", "MPN": "TNPU060397K6HZEN00"})
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
            pin_nets={"1": ("AUX_DC_FUSED", "local"), "2": ("AUX_DC_DIV", "local")})
    s.place("R192", "R", "56k 1% AUX ADC bottom", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_DIV", "local"), "2": ("GND", "local")})
    s.place("R193", "R", "1k AUX ADC series", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUX_DC_DIV", "local"), "2": ("AUX_DC_ADC", "hier")})
    s.place("C192", "C", "100n AUX ADC filter", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("AUX_DC_ADC", "hier"), "2": ("GND", "local")})

    # U15 provides qualified, reverse-blocking priority selection between USB-C PD and AUX/solar.
    # The industrial I-grade part is used because commercial C-grade selectors stop at 70 C.
    #
    # Phase 5: THREE charge sources (PD1 via FPC-1, PD2 via FPC-2, AUX).
    # The LTC4418 datasheet sanctions cascading: U16 (stage 2) selects
    # PD2 over AUX into SEL_STAGE2; U15 (stage 1) selects PD1 over
    # SEL_STAGE2 into VBUS_COMBINED.  Priority: PD1 > PD2 > AUX.
    #
    # Phase 5 pinout fix: the LTC4418IUF symbol had pins 6-10 transcribed
    # from the wrong datasheet column.  Real UF20 pinout (datasheet Rev A
    # pin functions): 6=VALID1, 7=VALID2 (both open-drain), 8=GND,
    # 9=CAS, 10=INTVCC, 18=EN, 19=SHDN, 20=HYS.  The old wiring put the
    # real GND on the INTVCC bypass node and real INTVCC on a 3V3-pulled
    # logic net -- U14/U15 could never have functioned.  Symbol corrected;
    # VALID outputs now land on 6/7 with their existing pull-ups.
    s.text(470, 20, "== U15/U16 LTC4418IUF cascade: PD1 > PD2 > AUX into VBUS_COMBINED ==")
    s.place("U15", "LTC4418IUF", "LTC4418IUF#PBF dual-input selector (stage 1)", 520, 165,
            footprint=FOOTPRINTS["LTC4418IUF"],
            pin_nets={
                "1": ("MAIN_SEL_TMR", "local"),
                "2": ("USB_MAIN_UV", "local"), "3": ("USB_MAIN_OV", "local"),
                "4": ("ST2_MAIN_UV", "local"), "5": ("ST2_MAIN_OV", "local"),
                "6": ("MAIN_USB_VALID_N", "hier"), "7": ("MAIN_AUX_VALID_N", "hier"),
                "8": ("GND", "local"), "9": ("", "nc"), "10": ("MAIN_SEL_INTVCC", "local"),
                "11": ("ST2_MAIN_GATE", "local"), "12": ("ST2_MAIN_FET_COMMON", "local"),
                "13": ("USB_MAIN_GATE", "local"), "14": ("USB_MAIN_FET_COMMON", "local"),
                "15": ("VBUS_COMBINED", "local"),
                "16": ("SEL_STAGE2", "local"), "17": ("USB_PD_SELECTED", "hier"),
                "18": ("MAIN_SEL_INTVCC", "local"), "19": ("MAIN_SEL_INTVCC", "local"),
                "20": ("GND", "local"), "21": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Analog Devices", "MPN": "LTC4418IUF#PBF"})

    # Stage 2: PD2 (from the right board via FPC-2) over AUX.
    s.place("U16", "LTC4418IUF", "LTC4418IUF#PBF dual-input selector (stage 2)", 520, 425,
            footprint=FOOTPRINTS["LTC4418IUF"],
            pin_nets={
                "1": ("ST2_SEL_TMR", "local"),
                "2": ("ST2_USB_UV", "local"), "3": ("ST2_USB_OV", "local"),
                "4": ("ST2_AUX_UV", "local"), "5": ("ST2_AUX_OV", "local"),
                "6": ("PD2_VALID_N", "hier"), "7": ("", "nc"),
                "8": ("GND", "local"), "9": ("", "nc"), "10": ("ST2_SEL_INTVCC", "local"),
                "11": ("ST2_AUX_GATE", "local"), "12": ("ST2_AUX_FET_COMMON", "local"),
                "13": ("ST2_USB_GATE", "local"), "14": ("ST2_USB_FET_COMMON", "local"),
                "15": ("SEL_STAGE2", "local"),
                "16": ("AUX_DC_PROTECTED", "local"), "17": ("PD2_VBUS_GATED", "hier"),
                "18": ("ST2_SEL_INTVCC", "local"), "19": ("ST2_SEL_INTVCC", "local"),
                "20": ("GND", "local"), "21": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Analog Devices", "MPN": "LTC4418IUF#PBF"})

    add_selector_fet(s, "Q21", 485, 70, "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "USB_PD_SELECTED", "hier")
    add_selector_fet(s, "Q22", 545, 70, "USB_MAIN_GATE", "USB_MAIN_FET_COMMON", "VBUS_COMBINED", "local")
    # stage-1 V2 channel: SEL_STAGE2 -> VBUS_COMBINED
    add_selector_fet(s, "Q28", 485, 137, "ST2_MAIN_GATE", "ST2_MAIN_FET_COMMON", "SEL_STAGE2", "local")
    add_selector_fet(s, "Q29", 545, 137, "ST2_MAIN_GATE", "ST2_MAIN_FET_COMMON", "VBUS_COMBINED", "local")
    # stage-2 channels: PD2 and AUX into SEL_STAGE2
    add_selector_fet(s, "Q26", 485, 350, "ST2_USB_GATE", "ST2_USB_FET_COMMON", "PD2_VBUS_GATED", "hier")
    add_selector_fet(s, "Q27", 545, 350, "ST2_USB_GATE", "ST2_USB_FET_COMMON", "SEL_STAGE2", "local")
    add_selector_fet(s, "Q23", 485, 385, "ST2_AUX_GATE", "ST2_AUX_FET_COMMON", "AUX_DC_PROTECTED", "local")
    add_selector_fet(s, "Q24", 545, 385, "ST2_AUX_GATE", "ST2_AUX_FET_COMMON", "SEL_STAGE2", "local")

    # USB windows accept 5/9/15/20 V. Check threshold accuracy, resistor
    # corners, leakage and the complete 15..45 mV fixed-hysteresis range.
    #   AUX window (on U16.V2) 5.59-23.3 V: V(UV) = Vin*83.4k/466.4k,
    #   V(OV) = Vin*20k/466.4k -- wide by design; the AUX eFuse (5.53-22.99 V)
    #   performs the real 7-22 V qualification upstream.
    #   Stage-2 383k/54.9k/20k also covers 21V OV recovery after TCR.
    for ref, value, net_a, net_b, x, y, mpn in (
        ("R730", "75.0k 0.02% 5ppm UV top", "USB_PD_SELECTED", "USB_MAIN_UV", 475, 225, "TNPU060375K0HZEN00"),
        ("R731", "23.2k 0.02% 5ppm window middle", "USB_MAIN_UV", "USB_MAIN_OV", 475, 237.7, "TNPU060323K2HZEN00"),
        ("R732", "4.53k 0.02% 5ppm OV bottom", "USB_MAIN_OV", "GND", 475, 250.4, "TNPU06034K53HZEN00"),
        ("R741", "75.0k 0.02% 5ppm UV top", "PD2_VBUS_GATED", "ST2_USB_UV", 475, 462.3, "TNPU060375K0HZEN00"),
        ("R742", "23.2k 0.02% 5ppm window middle", "ST2_USB_UV", "ST2_USB_OV", 475, 475, "TNPU060323K2HZEN00"),
        ("R743", "4.53k 0.02% 5ppm OV bottom", "ST2_USB_OV", "GND", 475, 487.7, "TNPU06034K53HZEN00"),
        ("R733", "383k 0.1% AUX UV top", "AUX_DC_PROTECTED", "ST2_AUX_UV", 555, 462.3, "RT0603BRD07383KL"),
        ("R734", "63.4k 0.02% 5ppm AUX window middle", "ST2_AUX_UV", "ST2_AUX_OV", 555, 475, "TNPU060363K4HZEN00"),
        ("R735", "20.0k 0.02% 5ppm AUX OV bottom", "ST2_AUX_OV", "GND", 555, 487.7, "TNPU060320K0HZEN00"),
        ("R744", "75.0k 0.02% 5ppm UV top", "SEL_STAGE2", "ST2_MAIN_UV", 615, 225, "TNPU060375K0HZEN00"),
        ("R745", "23.2k 0.02% 5ppm window middle", "ST2_MAIN_UV", "ST2_MAIN_OV", 615, 237.7, "TNPU060323K2HZEN00"),
        ("R746", "4.53k 0.02% 5ppm OV bottom", "ST2_MAIN_OV", "GND", 615, 250.4, "TNPU06034K53HZEN00"),
    ):
        kind_a = "hier" if net_a in ("USB_PD_SELECTED", "PD2_VBUS_GATED") else "local"
        s.place(ref, "R", value, x, y, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net_a, kind_a), "2": (net_b, "local")},
                extra_props={"Manufacturer": "Vishay" if mpn.startswith("TNP") else "Yageo", "MPN": mpn})

    for ref, value, net, x, y, fp, mpn in (
        ("C740", "100n 50V INTVCC", "MAIN_SEL_INTVCC", 475, 275, "C_100n", "GRM188R71H104KA93D"),
        ("C741", "1n 50V C0G selector validation", "MAIN_SEL_TMR", 515, 275, "C_0402", "GRM1555C1H102JA01D"),
        ("C742", "100n 50V USB V1 local", "USB_PD_SELECTED", 555, 275, "C_100n", "GRM188R71H104KA93D"),
        ("C743", "100n 50V USB VS1 local", "USB_MAIN_FET_COMMON", 475, 292.8, "C_100n", "GRM188R71H104KA93D"),
        ("C744", "100n 50V stage2 V2 local", "AUX_DC_PROTECTED", 515, 292.8, "C_100n", "GRM188R71H104KA93D"),
        ("C745", "100n 50V AUX VS2 local", "ST2_AUX_FET_COMMON", 555, 292.8, "C_100n", "GRM188R71H104KA93D"),
        ("C747", "100n 50V stage2 VS1 local", "ST2_MAIN_FET_COMMON", 635, 292.8, "C_100n", "GRM188R71H104KA93D"),
        ("C748", "100n 50V stage2 out local", "SEL_STAGE2", 615, 275, "C_100n", "GRM188R71H104KA93D"),
        ("C749", "100n 50V stage2 INTVCC", "ST2_SEL_INTVCC", 475, 505, "C_100n", "GRM188R71H104KA93D"),
    ):
        kind = "hier" if net == "USB_PD_SELECTED" else "local"
        s.place(ref, "C", value, x, y, footprint=FOOTPRINTS[fp],
                pin_nets={"1": (net, kind), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": mpn})
    s.place("R717", "R", "10k main USB VALID pull-up", 595, 225, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("MAIN_USB_VALID_N", "hier")})
    s.place("R718", "R", "10k main AUX VALID pull-up", 595, 237.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("MAIN_AUX_VALID_N", "hier")})
    s.place("R747", "R", "10k PD2 VALID pull-up", 595, 250.4, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("PD2_VALID_N", "hier")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0710KL"})
    s.place("C715", "C", "1n 50V C0G stage2 validation", 515, 505,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("ST2_SEL_TMR", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM1555C1H102JA01D"})
    s.place("C746", "C_Polarized", "100u 35V hybrid selector output hold-up", 595, 292.8,
            footprint=FOOTPRINTS["C_100u_35V_hybrid"],
            pin_nets={"1": ("VBUS_COMBINED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Panasonic", "MPN": "EEHZK1V101XP"})
    s.place("C2685", "C", "100n 50V U15 V2 local", 685.8, 275.59,
            footprint=FOOTPRINTS["C_100n"], text_right=True,
            pin_nets={"1": ("SEL_STAGE2", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D",
                         "DecouplingFor": "U15 V2"})

    s.gnd(400, 120)
    # The switched rails are physically driven through passive external FETs;
    # both selector VOUT pins are supply/sense inputs rather than power sources.
    s.pwrflag(650, 90, "VBUS_COMBINED")
    # USB_PD_SELECTED enters as connector power (FPC-1); the selector's V1
    # is a power input, so flag the net for ERC.
    s.pwrflag(650, 75, "USB_PD_SELECTED")
    s.pwrflag(650, 45, "AUX_DC_FUSED")
    # stage-2 output and the FPC-2-sourced PD2 rail are power inputs to
    # the cascade's V1/V2 sense pins
    s.pwrflag(650, 105, "SEL_STAGE2")
    s.pwrflag(650, 120, "PD2_VBUS_GATED")
    s.pwrflag(650, 60, "AUX_EFUSE_IN_SYS")
    from generate_aon_input import add_aon_input
    add_aon_input(s)

    s.text(380, 20, "J190 is the single AUX/SOLAR physical input; USB-C PD negotiation remains only on sheet 5.")
    s.text(380, 26, "TPS26630 accepts 7-22V nominal; 0.1% ladder targets 5.53V/22.99V rising UV/OV and a 3A limit.")
    s.text(380, 32, "U15/U16 accepts fixed 5/9/15/20V PD contracts and AUX across 7-22V; priority remains PD1 > PD2 > AUX.")
    s.text(380, 38.1, "SMCJ24CA protects the AUX eFuse input. The common LTC4418 window protects the charger input.")

    s.text(20, 220, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 226, "BMS J2: 1 raw negative, 2 cell2 tap, 3 raw positive, 4 cell1 tap. Verify the assembled harness before connecting cells.")
    s.text(20, 232, "U719 BQ7791500 autonomously protects each cell at 4.20V OV / 2.90V UV and drives back-to-back low-side FETs.")
    s.text(20, 238, "RS11=8mOhm gives 7.5A nominal OCD and 15A nominal SCD; U11/RS10 and F1 remain independent tighter/secondary protection.")
    s.text(20, 244, "Three insulated cell probes drive raw-referenced BMS comparators and CTRC/CTRD. U719 TS retains its unused-function strap.")
    s.text(20, 250, "Charging requires CHG_ENABLE AND isolated PACK_CHG_TEMP_OK. Q700 clamps NTC hot until both permits are present.")
    s.text(20, 256, "ISL9241 starts with a 200mA input limit and charging off. Firmware must verify the source and program bounded limits.")
    s.text(20, 263.62, "J190 is the one 7-22V nominal AUX input; TPS26630 protects it before the source selector.")
    s.text(20, 271.24, "AUX current is limited by the released source profile. Solar MPPT is not implemented in this charger driver.")
    s.text(20, 286.48, "AUX_DC_ADC measures the protected input so firmware can detect droop and reduce charger input current.")
    s.text(20, 294.1, "RS2600 is the 20mOhm input shunt. RS2601 is the separate 10mOhm battery-current shunt; both need Kelvin routing.")
    s.text(20, 301.72, "Q25 is the ISL9241 battery-path FET. Battery standby comes through VSYS and the discharge shunt; disabling Mu keeps button wake available.")
    s.text(20, 309.34, "U11 accepts about 8.45-13.57V nominal; 11mOhm RS10 gives 4.55A nominal and <=5.51A worst-case trips.")
    s.text(20, 316.96, "The charger NTC pin receives a hardware inhibit from the BMS permit. The fixed 10k state is not a cell-temperature measurement.")
    s.text(20, 324.58, "STARTUP: keep Mu enable low and PROCHOT asserted. Read TCPC PD Status 0x40 and active PDO/RDO 0x34/0x35 before selecting a source.")
    s.text(20, 332.2, "Require the qualified VSYS threshold before Mu enable and confirm MU_12V_PG. Source, charger, watchdog or PG faults revoke enable; profile gates remain off until qualified.")
    s.text(20, 339.82, "The charger watchdog stays enabled. JEITA, source limits and throttle settings must be read back before the hardware gates are released.")
    s.text(20, 347.44, "U718 provides fast voltage protection. U2660 limits standby inrush and latches a persistent fault; TP2660/TP2661 provide a service reset.")
    s.text(20, 355.06, "USB and VSYS use reverse-blocking ideal-diode feeds. AUX uses D711. The EC can start from 5V USB before the main source paths are enabled.")
    s.text(20, 362.68, "5V and 9V adapters use the buck-boost path. Running and charging share the measured input budget; a qualified pack can cover a shortfall.")
    s.text(20, 370.3, "C746 provides low-ESR hold-up through LTC4418 break-before-make source switching.")

    # First-article pogo access. These pads are not user connectors; they make
    # the power-up and fault-state procedure electrically observable.
    for ref, label, x, y, net_name, scope in [
        ("TP1", "GND test", 1200, 480, "GND", "local"),
        ("TP2", "PACK_POS_FUSED test", 1280, 480, "PACK_POS_FUSED", "local"),
        ("TP3", "VSYS test", 1200, 505, "VSYS", "hier"),
        ("TP4", "EC_AON_IN test", 1280, 505, "EC_AON_IN", "hier"),
        ("TP7", "MCU_3V3 test", 1200, 530, "MCU_3V3", "hier"),
        ("TP9", "CHG_INT_N test", 1280, 530, "CHG_INT_N", "hier"),
        ("TP10", "PACK_FAULT_N test", 1200, 555, "PACK_FAULT_N", "hier"),
        ("TP11", "AON_FAULT_N test", 1280, 555, "AON_FAULT_N", "hier"),
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
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "MU_PROCHOT_RELEASE", "CHG_ENABLE",
        "CASE_PWRBTN_N", "MU_PWRBTN_N",
        "VSYS", "MCU_3V3", "EC_AON_IN", "AUX_DC_ADC", "USB_PD_SELECTED",
        "PD1_VBUS_RAW", "PD2_VBUS_RAW",
        "PACK_FAULT_N", "PACK_RETRY_PULSE", "PACK_CHG_TEMP_OK", "AUX_FAULT_N", "AUX_PGOOD",
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
