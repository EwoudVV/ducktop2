import os
from build_ducktop2 import Sheet, U, PROJDIR, FOOTPRINTS


def build(sheet_symbol_uuid, pwr_start=20, flg_start=20):
    s = Sheet(f"/{sheet_symbol_uuid}")
    # continue global numbering for #PWR/#FLG pseudo-refs so they don't collide
    # with the ones already used on the Power & Battery sheet.
    s.refcounters["#PWR"] = pwr_start
    s.refcounters["#FLG"] = flg_start

    class Cur:
        def __init__(self, x0, y0, col_w=55, row_h=10, rows_per_col=22):
            self.x0, self.y0, self.col_w, self.row_h, self.rows = x0, y0, col_w, row_h, rows_per_col
            self.i = 0

        def next(self):
            col, row = divmod(self.i, self.rows)
            self.i += 1
            return (self.x0 + col * self.col_w, self.y0 + row * self.row_h)

    # ---------------- U4: STM32F407VGTx EC/MCU core ----------------
    s.text(20, 20, "== U4 STM32F407VGTx EC/MCU Core ==")
    s.place("U4", "STM32F407VGTx", "STM32F407VGTx", 250, 400,
            footprint="Package_QFP:LQFP-100_14x14mm_P0.5mm",
            pin_nets={
                "1": ("KB_ROW2", "hier"), "2": ("KB_ROW3", "hier"), "3": ("KB_ROW4", "hier"),
                "4": ("KB_ROW5", "hier"), "5": ("KB_ROW6", "hier"), "6": ("MCU_3V3", "hier"),
                "7": ("USER_GPIO4", "local"), "8": ("LSE_IN", "local"), "9": ("LSE_OUT", "local"),
                "10": ("GND", "local"), "11": ("MCU_3V3", "hier"), "12": ("HSE_IN", "local"),
                "13": ("HSE_OUT", "local"), "14": ("NRST_NET", "local"), "15": ("USER_GPIO0_SPI_SCK", "local"),
                "16": ("USER_GPIO1_SPI_MISO", "local"), "17": ("USER_GPIO2_SPI_MOSI", "local"),
                "18": ("USER_GPIO3_SPI_CS_N", "local"), "19": ("MCU_3V3", "hier"),
                "20": ("GND", "local"), "21": ("MCU_3V3", "hier"), "22": ("MCU_3V3", "hier"),
                "23": ("MU_PWRBTN_N", "hier"), "24": ("BQ_ALERT", "hier"), "25": ("CHG_INT_N", "hier"),
                "26": ("PMIC_QON", "hier"), "27": ("GND", "local"), "28": ("MCU_3V3", "hier"),
                "29": ("CHG_CE_N", "hier"), "30": ("MU_RSTBTN_N", "hier"), "31": ("AUX_DC_ADC", "hier"),
                "32": ("THERM_SKIN_ADC", "hier"), "33": ("FAN_PWM", "hier"), "34": ("FAN_TACH", "hier"),
                "35": ("THERM_MU_ADC", "hier"), "36": ("TPAD_INT_N", "hier"), "37": ("EC_SPARE_GPIO5", "local"),
                "38": ("KB_ROW7", "hier"), "39": ("LCD_BL_PWM", "hier"), "40": ("LCD_BL_EN", "hier"),
                "41": ("LID_CLOSED_N", "hier"), "42": ("TPAD_RESET_N", "hier"),
                "43": ("TOUCH_RESET_N", "hier"), "44": ("PANEL_PWR_EN", "hier"),
                "45": ("PANEL_RESET_N", "hier"), "46": ("TOUCH_INT_N", "hier"),
                "47": ("RADIO_VHF_UART_TX", "hier"), "48": ("RADIO_VHF_UART_RX", "hier"),
                "49": ("VCAP1_NODE", "local"), "50": ("MCU_3V3", "hier"),
                "51": ("OLED_RESET_N", "hier"), "52": ("GNSS_RESET_N", "hier"), "53": ("GNSS_PPS", "hier"),
                "54": ("RADIO_UHF_UART_TX", "hier"), "55": ("KB_COL8", "hier"), "56": ("KB_COL9", "hier"),
                "57": ("KB_COL10", "hier"), "58": ("KB_COL11", "hier"), "59": ("KB_COL12", "hier"),
                "60": ("KB_COL13", "hier"), "61": ("KB_COL14", "hier"), "62": ("KB_COL15", "hier"),
                "63": ("RADIO_UHF_UART_RX", "hier"), "64": ("RADIO_VHF_PTT_N", "hier"),
                "65": ("RADIO_UHF_PTT_N", "hier"), "66": ("RADIO_VHF_PD_N", "hier"),
                "67": ("WIFI_W_DISABLE1_N", "hier"), "68": ("WIFI_W_DISABLE2_N", "hier"), "69": ("GNSS_UART_RX", "hier"),
                "70": ("MCU_USB_DM", "hier"), "71": ("MCU_USB_DP", "hier"), "72": ("SWDIO_NET", "local"),
                "73": ("VCAP2_NODE", "local"), "74": ("GND", "local"), "75": ("MCU_3V3", "hier"),
                "76": ("SWCLK_NET", "local"), "77": ("GNSS_UART_TX", "hier"), "78": ("RADIO_UHF_PD_N", "hier"),
                "79": ("RADIO_VHF_SQL", "hier"), "80": ("RADIO_UHF_SQL", "hier"),
                "81": ("KB_COL0", "hier"), "82": ("KB_COL1", "hier"),
                "83": ("KB_COL2", "hier"), "84": ("KB_COL3", "hier"), "85": ("KB_COL4", "hier"),
                "86": ("KB_COL5", "hier"), "87": ("KB_COL6", "hier"), "88": ("KB_COL7", "hier"),
                "89": ("RADIO_VHF_RF_SEL", "hier"), "90": ("RADIO_UHF_RF_SEL", "hier"),
                "91": ("RADIO_AUDIO_SEL", "hier"), "92": ("I2C_SCL", "hier"),
                "93": ("I2C_SDA", "hier"), "94": ("BOOT0_NET", "local"), "95": ("GNSS_EXTINT", "hier"),
                "96": ("RADIO_GPIO0", "hier"), "97": ("KB_ROW0", "hier"), "98": ("KB_ROW1", "hier"),
                "99": ("GND", "local"), "100": ("MCU_3V3", "hier"),
            })

    # ---------------- Power-supply decoupling / VCAPs / VDDA ----------------
    s.text(20, 40, "-- U4 decoupling (one 100n per VDD pin, per datasheet) --")
    c1 = Cur(20, 50)
    for i in range(6):
        s.place(f"C{20+i}", "C", "100n", *c1.next(), footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C26", "C", "4.7u (bulk)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C27", "C", "100n (VBAT)", *c1.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C28", "C", "1u (VDDA)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C29", "C", "2.2u (VCAP_1, mandatory)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("VCAP1_NODE", "local"), "2": ("GND", "local")})
    s.place("C30", "C", "2.2u (VCAP_2, mandatory)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("VCAP2_NODE", "local"), "2": ("GND", "local")})

    # ---------------- NRST / BOOT0 ----------------
    s.text(20, 170, "-- NRST filter/button, BOOT0 strap --")
    c2 = Cur(20, 180)
    s.place("R32", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("NRST_NET", "local")})
    s.place("C31", "C", "100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("NRST_NET", "local"), "2": ("GND", "local")})
    s.place("SW1", "SW_Push", "Reset", *c2.next(), footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("NRST_NET", "local"), "2": ("GND", "local")})
    s.place("R33", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BOOT0_NET", "local"), "2": ("GND", "local")})

    # ---------------- HSE / LSE crystals ----------------
    s.text(20, 230, "-- HSE 8MHz + LSE 32.768kHz crystals --")
    c3 = Cur(20, 240)
    s.place("Y1", "Crystal_GND24", "8MHz HSE", *c3.next(), footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={"1": ("HSE_IN", "local"), "2": ("GND", "local"), "3": ("HSE_OUT", "local")})
    s.place("C32", "C", "18p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HSE_IN", "local"), "2": ("GND", "local")})
    s.place("C33", "C", "18p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HSE_OUT", "local"), "2": ("GND", "local")})
    s.place("Y2", "Crystal", "32.768kHz LSE", *c3.next(), footprint=FOOTPRINTS["Crystal_LSE"],
            pin_nets={"1": ("LSE_IN", "local"), "2": ("LSE_OUT", "local")})
    s.place("C34", "C", "12p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LSE_IN", "local"), "2": ("GND", "local")})
    s.place("C35", "C", "12p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LSE_OUT", "local"), "2": ("GND", "local")})

    # ---------------- SWD debug header ----------------
    s.text(20, 320, "-- SWD debug header --")
    s.place("J4", "Conn_01x04", "SWD (VDD/SWDIO/SWCLK/GND)", 20, 330,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("SWDIO_NET", "local"),
                      "3": ("SWCLK_NET", "local"), "4": ("GND", "local")})

    s.gnd(20, 360)
    s.pwrflag(20, 380, "MCU_3V3")

    # ---------------- Keyboard matrix headers ----------------
    s.text(450, 20, "== Keyboard Matrix GPIO bank (MX ULP rev A uses 5 rows x 14 cols) ==")
    s.place("J5", "Conn_01x08", "DNP KB row probe; R5-R7 spare in MX ULP rev A", 450, 60,
            footprint=FOOTPRINTS["Conn_01x08"],
            pin_nets={
                "1": ("KB_ROW0", "hier"), "2": ("KB_ROW1", "hier"), "3": ("KB_ROW2", "hier"),
                "4": ("KB_ROW3", "hier"), "5": ("KB_ROW4", "hier"), "6": ("KB_ROW5", "hier"),
                "7": ("KB_ROW6", "hier"), "8": ("KB_ROW7", "hier"),
            })
    s.place("J6", "Conn_01x16", "DNP KB column probe; C14-C15 spare in MX ULP rev A", 450, 140,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("KB_COL0", "hier"), "2": ("KB_COL1", "hier"), "3": ("KB_COL2", "hier"),
                "4": ("KB_COL3", "hier"), "5": ("KB_COL4", "hier"), "6": ("KB_COL5", "hier"),
                "7": ("KB_COL6", "hier"), "8": ("KB_COL7", "hier"), "9": ("KB_COL8", "hier"),
                "10": ("KB_COL9", "hier"), "11": ("KB_COL10", "hier"), "12": ("KB_COL11", "hier"),
                "13": ("KB_COL12", "hier"), "14": ("KB_COL13", "hier"), "15": ("KB_COL14", "hier"),
                "16": ("KB_COL15", "hier"),
            })

    # ---------------- GPIO expansion header ----------------
    s.text(450, 260, "== EC GPIO expansion / laptop power controls ==")
    s.place("J7", "Conn_01x16", "EC power controls + spare GPIO expansion", 450, 300,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("MU_PWRBTN_N", "hier"), "2": ("MU_RSTBTN_N", "hier"),
                "3": ("AUX_DC_ADC", "hier"), "4": ("TPAD_RESET_N", "hier"),
                "5": ("TPAD_INT_N", "hier"), "6": ("EC_SPARE_GPIO5", "local"),
                "7": ("THERM_MU_ADC", "hier"), "8": ("WIFI_W_DISABLE1_N", "hier"),
                "9": ("WIFI_W_DISABLE2_N", "hier"), "10": ("GNSS_UART_RX", "hier"),
                "11": ("GNSS_UART_TX", "hier"), "12": ("OLED_RESET_N", "hier"),
                "13": ("GNSS_RESET_N", "hier"), "14": ("GNSS_PPS", "hier"),
                "15": ("GNSS_EXTINT", "hier"), "16": ("RADIO_GPIO0", "hier"),
            })

    s.place("J13", "Conn_01x16", "Laptop service GPIO map", 590, 300,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("FAN_PWM", "hier"), "2": ("FAN_TACH", "hier"),
                "3": ("LCD_BL_PWM", "hier"), "4": ("LCD_BL_EN", "hier"),
                "5": ("LID_CLOSED_N", "hier"), "6": ("THERM_SKIN_ADC", "hier"),
                "7": ("THERM_MU_ADC", "hier"), "8": ("TOUCH_RESET_N", "hier"),
                "9": ("TOUCH_INT_N", "hier"), "10": ("PANEL_PWR_EN", "hier"),
                "11": ("PANEL_RESET_N", "hier"), "12": ("MCU_USB_DP", "hier"),
                "13": ("MCU_USB_DM", "hier"), "14": ("MCU_3V3", "hier"),
                "15": ("VSYS", "hier"), "16": ("GND", "local"),
            })

    s.place("J14", "Conn_01x16", "Ham radio EC GPIO map", 590, 420,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("RADIO_VHF_UART_TX", "hier"), "2": ("RADIO_VHF_UART_RX", "hier"),
                "3": ("RADIO_UHF_UART_TX", "hier"), "4": ("RADIO_UHF_UART_RX", "hier"),
                "5": ("RADIO_VHF_PTT_N", "hier"), "6": ("RADIO_UHF_PTT_N", "hier"),
                "7": ("RADIO_VHF_PD_N", "hier"), "8": ("RADIO_UHF_PD_N", "hier"),
                "9": ("RADIO_VHF_SQL", "hier"), "10": ("RADIO_UHF_SQL", "hier"),
                "11": ("RADIO_VHF_RF_SEL", "hier"), "12": ("RADIO_UHF_RF_SEL", "hier"),
                "13": ("RADIO_AUDIO_SEL", "hier"), "14": ("RADIO_GPIO0", "hier"),
                "15": ("MCU_3V3", "hier"), "16": ("GND", "local"),
            })

    s.place("J15", "Conn_01x16", "Exposed EC-owned GPIO header", 450, 420,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("MCU_3V3", "hier"), "2": ("GND", "local"),
                "3": ("I2C_SCL", "hier"), "4": ("I2C_SDA", "hier"),
                "5": ("USER_GPIO0_SPI_SCK", "local"), "6": ("USER_GPIO1_SPI_MISO", "local"),
                "7": ("USER_GPIO2_SPI_MOSI", "local"), "8": ("USER_GPIO3_SPI_CS_N", "local"),
                "9": ("USER_GPIO4", "local"), "10": ("RADIO_GPIO0", "hier"),
                "11": ("MCU_3V3", "hier"), "12": ("GND", "local"),
                "13": ("", "nc"), "14": ("", "nc"), "15": ("", "nc"), "16": ("GND", "local"),
            })

    s.place("J16", "Conn_01x04", "Case power/reset button harness", 450, 535,
            footprint=FOOTPRINTS["Conn_01x04"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MU_PWRBTN_N", "hier"),
                "3": ("MU_RSTBTN_N", "hier"),
                "4": ("MCU_3V3", "hier"),
            })

    # ---------------- U5: TPS54202DDC VSYS -> 3.3V buck ----------------
    s.text(650, 20, "== U5 TPS54202DDC VSYS -> MCU_3V3 Buck (3.3V, 2A) ==")
    s.place("U5", "TPS54202DDC", "TPS54202DDC", 700, 100,
            footprint=FOOTPRINTS["U_SOT23_6"],
            pin_nets={
                "1": ("GND", "local"), "2": ("BUCK_SW", "local"), "3": ("VSYS", "hier"),
                "4": ("BUCK_FB", "local"), "5": ("BUCK_EN", "local"), "6": ("BUCK_BOOT", "local"),
            })
    c4 = Cur(650, 40)
    s.place("C36", "C", "10u (VIN bulk)", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("C37", "C", "100n (VIN bypass)", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("R34", "R", "100k (EN pull-up, always-on)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("BUCK_EN", "local")})
    s.place("C38", "C", "100n (BOOT cap)", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BUCK_BOOT", "local"), "2": ("BUCK_SW", "local")})
    s.place("L3", "L", "3.3uH >=3A", *c4.next(), footprint=FOOTPRINTS["L_buck"],
            pin_nets={"1": ("BUCK_SW", "local"), "2": ("MCU_3V3", "hier")})
    s.place("R35", "R", "45.3k 1% (3.3V FB hi)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BUCK_FB", "local")})
    s.place("R36", "R", "10k 1% (3.3V FB lo)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK_FB", "local"), "2": ("GND", "local")})
    s.place("C39", "C", "22u MCU_3V3 output", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})

    s.gnd(650, 200)

    s.text(20, 340, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 346, "EC_GPIOx numbering is a local convenience mapping - see U4 pin_nets for actual STM32 pin/net cross-ref.")
    s.text(20, 352, "Anti-ghosting diodes for the keyboard matrix live on the separate MX ULP keyboard PCB.")
    s.text(20, 358, "MCU_USB_DP/DM (PA12/PA11, OTG_FS device mode) intentionally distinct from Power sheet's USB_DP1/DM1 (PD sink port).")
    s.text(20, 364, "EC can assert Mu PWRBTN_N/RSTBTN_N as open-drain GPIOs; J16 also allows physical case buttons.")
    s.text(20, 370, "Second spare GPIO bank is assigned to E-key radio disables, GNSS UART/control/PPS, OLED reset, trackpad reset/INT, and one spare radio GPIO.")
    s.text(20, 376, "AUX_DC_ADC monitors the screw-terminal wide-DC input so firmware can classify and current-limit that source.")
    s.text(20, 383.54, "PA7/PB0 are assigned to skin and Mu-heatsink thermistors; fan PWM/tach remain EC-owned.")
    s.text(20, 391.16, "J15 is the user-facing EC GPIO header: EC I2C, five GPIO/SPI-capable signals, power, and grounds.")
    s.text(20, 398.78, "U5 uses TPS54202/TPS54302-style 0.596V feedback; R35/R36 set MCU_3V3 to about 3.30V.")

    return s


def main():
    from build_ducktop2 import Sheet as _S  # noqa: F401
    import generate_power_sheet as ps

    power_sheet_uuid = U()
    ec_sheet_uuid = U()

    power_s = ps.build(power_sheet_uuid)
    power_text = power_s.render(U(), page_number="2")
    power_path = os.path.join(PROJDIR, "01_power_battery.kicad_sch")
    with open(power_path, "w", encoding="utf-8") as f:
        f.write(power_text)
    print("wrote", power_path, len(power_text), "bytes")

    ec_s = build(ec_sheet_uuid)
    ec_text = ec_s.render(U(), page_number="3")
    ec_path = os.path.join(PROJDIR, "02_ec_mcu.kicad_sch")
    with open(ec_path, "w", encoding="utf-8") as f:
        f.write(ec_text)
    print("wrote", ec_path, len(ec_text), "bytes")

    # ---- Root sheet (both sheets + cross-sheet wiring for shared nets) ----
    power_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "MCU_3V3", "AUX_DC_ADC", "VBUS_PD1", "VBUS_PD2", "VBUS_PD3", "USB_DP1", "USB_DM1",
    ]
    ec_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "MCU_USB_DP", "MCU_USB_DM", "MCU_3V3", "AUX_DC_ADC",
        "FAN_PWM", "FAN_TACH", "LCD_BL_PWM", "LCD_BL_EN", "LID_CLOSED_N",
        "THERM_SKIN_ADC", "THERM_MU_ADC", "TOUCH_RESET_N", "TOUCH_INT_N", "PANEL_PWR_EN", "PANEL_RESET_N",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N", "RADIO_VHF_PD_N", "RADIO_UHF_PD_N",
        "RADIO_VHF_SQL", "RADIO_UHF_SQL", "RADIO_VHF_RF_SEL", "RADIO_UHF_RF_SEL", "RADIO_AUDIO_SEL",
    ]
    shared_nets = [n for n in ec_hier_nets if n in power_hier_nets]

    def sheet_block(uuid_, x, y, w, h, name, filename, pins):
        pins_sexpr = []
        pin_coords = {}
        for i, name_ in enumerate(pins):
            py = y + 5 + i * 6
            pin_coords[name_] = (x + w, py)
            pins_sexpr.append(
                f'  (pin "{name_}" bidirectional\n'
                f'    (at {x + w} {py} 0)\n'
                f'    (effects (font (size 1.27 1.27)) (justify left))\n'
                f'    (uuid {U()})\n'
                f'  )'
            )
        block = (
            f'(sheet\n'
            f'  (at {x} {y})\n'
            f'  (size {w} {h})\n'
            f'  (stroke (width 0.1524) (type solid))\n'
            f'  (fill (color 0 0 0 0.0))\n'
            f'  (uuid {uuid_})\n'
            f'  (property "Sheetname" "{name}"\n'
            f'    (at {x} {y - 1} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'  )\n'
            f'  (property "Sheetfile" "{filename}"\n'
            f'    (at {x} {y + h + 1} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left top))\n'
            f'  )\n'
            + "\n".join(pins_sexpr) + "\n"
            f')'
        )
        return block, pin_coords

    power_block, power_pins = sheet_block(
        power_sheet_uuid, 50, 50, 60, 80, "Power & Battery", "01_power_battery.kicad_sch",
        power_hier_nets,
    )
    ec_block, ec_pins = sheet_block(
        ec_sheet_uuid, 180, 50, 60, 70, "EC & MCU", "02_ec_mcu.kicad_sch",
        ec_hier_nets,
    )

    wires = []
    for net in shared_nets:
        x1, y1 = power_pins[net]
        x2, y2 = ec_pins[net]
        wires.append(
            f'(wire\n'
            f'  (pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'  (stroke (width 0) (type default))\n'
            f'  (uuid {U()})\n'
            f')'
        )

    root_text = (
        f'(kicad_sch\n'
        f'  (version 20260306)\n'
        f'  (generator "eeschema")\n'
        f'  (generator_version "10.0")\n'
        f'  (uuid {U()})\n'
        f'  (paper "A3")\n'
        f'  (lib_symbols\n  )\n'
        f'{power_block}\n'
        f'{ec_block}\n'
        + "\n".join(wires) + "\n"
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
