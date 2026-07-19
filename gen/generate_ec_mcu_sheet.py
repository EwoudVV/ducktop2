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
                "7": ("SOURCE_MGR_INT_N", "local"), "8": ("LSE_IN", "local"), "9": ("LSE_OUT", "local"),
                "10": ("GND", "local"), "11": ("MCU_3V3", "hier"), "12": ("HSE_IN", "local"),
                "13": ("HSE_OUT", "local"), "14": ("NRST_NET", "local"),
                "15": ("KB_RGB_PWR_EN", "hier"), "16": ("KB_RGB_FAULT_N", "hier"),
                "17": ("RADIO_VHF_RF_SEL_3V3", "hier"),
                "18": ("RADIO_UHF_RF_SEL_3V3", "hier"), "19": ("MCU_3V3", "hier"),
                "20": ("GND", "local"), "21": ("MCU_3V3", "hier"), "22": ("MCU_3V3", "hier"),
                "23": ("MU_PWRBTN_N", "hier"), "24": ("BQ_ALERT", "hier"), "25": ("CHG_INT_N", "hier"),
                "26": ("PMIC_QON_ASSERT", "hier"), "27": ("GND", "local"), "28": ("MCU_3V3", "hier"),
                "29": ("CHG_ENABLE", "hier"), "30": ("MU_RSTBTN_N", "hier"), "31": ("AUX_DC_ADC", "hier"),
                "32": ("THERM_SKIN_ADC", "hier"), "33": ("PD1_VALID_N", "hier"), "34": ("FAN_TACH", "hier"),
                "35": ("THERM_MU_ADC", "hier"), "36": ("TRACKPAD_FAULT_N", "hier"), "37": ("PD2_VALID_N", "hier"),
                "38": ("KB_ROW7", "hier"), "39": ("PD3_VALID_N", "hier"), "40": ("FAN_PWM", "hier"),
                "41": ("LID_CLOSED_N", "hier"), "42": ("AUDIO_MIC_EN", "hier"),
                "43": ("AUDIO_AMP_EC_EN", "hier"), "44": ("MU_12V_ENABLE", "hier"),
                "45": ("MU_S0_HIGH", "hier"), "46": ("MU_12V_PG", "hier"),
                "47": ("RADIO_VHF_UART_TX", "hier"), "48": ("RADIO_VHF_UART_RX", "hier"),
                "49": ("VCAP1_NODE", "local"), "50": ("MCU_3V3", "hier"),
                "51": ("SERVICE_MUX_RESET_REQ_N", "local"), "52": ("GNSS_RESET_N", "hier"), "53": ("GNSS_PPS", "hier"),
                "54": ("RADIO_VHF_PTT_N", "hier"), "55": ("KB_COL8", "hier"), "56": ("KB_COL9", "hier"),
                "57": ("KB_COL10", "hier"), "58": ("KB_COL11", "hier"), "59": ("KB_COL12", "hier"),
                "60": ("KB_COL13", "hier"), "61": ("KB_COL14", "hier"),
                "62": ("KB_RGB_DATA_3V3", "hier"),
                "63": ("RADIO_UHF_UART_TX", "hier"), "64": ("RADIO_UHF_UART_RX", "hier"),
                "65": ("RADIO_UHF_PTT_N", "hier"), "66": ("RADIO_VHF_PD_N", "hier"),
                "67": ("WIFI_W_DISABLE1_N_EC", "hier"), "68": ("GNSS_UART_TX", "hier"), "69": ("GNSS_UART_RX", "hier"),
                "70": ("MCU_USB_DM", "hier"), "71": ("MCU_USB_DP", "hier"), "72": ("SWDIO_NET", "local"),
                "73": ("VCAP2_NODE", "local"), "74": ("GND", "local"), "75": ("MCU_3V3", "hier"),
                "76": ("SWCLK_NET", "local"), "77": ("WIFI_W_DISABLE2_N_EC", "hier"), "78": ("RADIO_UHF_PD_N", "hier"),
                "79": ("RADIO_VHF_SQL", "hier"), "80": ("RADIO_UHF_SQL", "hier"),
                "81": ("KB_COL0", "hier"), "82": ("KB_COL1", "hier"),
                "83": ("KB_COL2", "hier"), "84": ("KB_COL3", "hier"), "85": ("KB_COL4", "hier"),
                "86": ("KB_COL5", "hier"), "87": ("KB_COL6", "hier"), "88": ("KB_COL7", "hier"),
                "89": ("INTERNAL_USB_VBUS_FAULT_N", "hier"), "90": ("", "nc"),
                "91": ("RADIO_AUDIO_SEL", "hier"), "92": ("I2C_SCL", "hier"),
                "93": ("I2C_SDA", "hier"), "94": ("BOOT0_NET", "local"), "95": ("GNSS_EXTINT", "hier"),
                "96": ("RADIO_GPIO0", "hier"), "97": ("KB_ROW0", "hier"), "98": ("KB_ROW1", "hier"),
                "99": ("GND", "local"), "100": ("MCU_3V3", "hier"),
            },
            extra_props={"Manufacturer": "STMicroelectronics", "MPN": "STM32F407VGT6"})

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
    s.place("C290", "C", "10n (VDDA high-frequency)", *c1.next(), footprint=FOOTPRINTS["C_100n"],
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
            pin_nets={"1": ("NRST_NET", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Omron", "MPN": "B3S-1000"})
    s.place("R33", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BOOT0_NET", "local"), "2": ("GND", "local")})

    # ---------------- HSE / LSE crystals ----------------
    s.text(20, 230, "-- HSE 8MHz + LSE 32.768kHz crystals --")
    c3 = Cur(20, 240)
    s.place("Y1", "Crystal_GND24", "J32SMX-K-F-G-I-8M0 8MHz CL8pF", *c3.next(),
            footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={
                "1": ("HSE_IN", "local"), "2": ("GND", "local"),
                "3": ("HSE_XTAL_OUT", "local"), "4": ("GND", "local"),
            },
            extra_props={
                "Manufacturer": "Jauch Quartz", "MPN": "J32SMX-K-F-G-I-8M0",
                "Datasheet": "https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7432/JQG_DB_Q-J32SMX_250618_online.pdf",
            })
    s.place("C32", "C", "10p C0G 0.25pF HSE load", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HSE_IN", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "KEMET", "MPN": "C0603C100C5GACTU"})
    s.place("C33", "C", "10p C0G 0.25pF HSE load", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HSE_XTAL_OUT", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "KEMET", "MPN": "C0603C100C5GACTU"})
    s.place("R37", "R", "0R HSE drive/tuning position", *c3.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("HSE_XTAL_OUT", "local"), "2": ("HSE_OUT", "local")})
    s.place("Y2", "Crystal", "X1A000141000612 32.768kHz CL6pF", *c3.next(),
            footprint=FOOTPRINTS["Crystal_LSE"],
            pin_nets={"1": ("LSE_IN", "local"), "2": ("LSE_OUT", "local")},
            extra_props={
                "Manufacturer": "Epson", "MPN": "X1A000141000612",
                "Datasheet": "https://download.epsondevice.com/td/pdf/td_xtal_32khz/FC-135R_X1A0001410006_en.pdf",
            })
    s.place("C34", "C", "6.8p C0G 0.25pF LSE load", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LSE_IN", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "KEMET", "MPN": "C0603C689C5GACTU"})
    s.place("C35", "C", "6.8p C0G 0.25pF LSE load", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LSE_OUT", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "KEMET", "MPN": "C0603C689C5GACTU"})

    # ---------------- SWD debug header ----------------
    s.text(20, 320, "-- Standard TC2030 Cortex SWD target pads --")
    s.place("R34", "R", "0R VTref sense link", 20, 342.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("EC_SWD_VTREF", "local")})
    s.place("J4", "Conn_01x06", "TC2030 Cortex SWD: VTref/SWDIO/NRST/SWCLK/GND/NC", 20, 330,
            footprint=FOOTPRINTS["TagConnect_SWD"],
            pin_nets={"1": ("EC_SWD_VTREF", "local"), "2": ("SWDIO_NET", "local"),
                      "3": ("NRST_NET", "local"), "4": ("SWCLK_NET", "local"),
                      "5": ("GND", "local"), "6": ("", "nc")},
            in_bom=False,
            extra_props={
                "ProcurementClass": "PCB copper test feature",
                "FixtureCable": "TC2030-CTX-NL external programming cable; not fitted",
            })

    s.gnd(20, 360)

    # The final laptop exposes only the isolated RP2350 maker header. Redundant
    # EC map/probe headers were removed so internal buses and EC rails are not
    # touch-accessible and do not consume motherboard area.
    s.text(450, 260, "== Final case controls (no exposed EC/service-map headers) ==")
    s.place("J16", "Conn_01x03", "Case power/reset button harness: GND/CASE_PWR/RESET", 450, 535,
            footprint=FOOTPRINTS["Conn_01x03"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("CASE_PWRBTN_N", "hier"),
                "3": ("MU_RSTBTN_N", "hier"),
            },
            extra_props={"Manufacturer": "JST", "MPN": "SM03B-SRSS-TB"})

    # ---------------- U5: TPS54202DDC always-on source -> 3.3V buck ----------------
    s.text(650, 20, "== U5 TPS54202DDC EC_AON_IN -> MCU_3V3 Buck (3.3V, 2A) ==")
    s.place("U5", "TPS54202DDC", "TPS54202DDC", 700, 100,
            footprint=FOOTPRINTS["U_SOT23_6"],
            pin_nets={
                "1": ("GND", "local"), "2": ("BUCK_SW", "local"), "3": ("EC_AON_IN", "hier"),
                "4": ("BUCK_FB", "local"), "5": ("", "nc"), "6": ("BUCK_BOOT", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments",
                "MPN": "TPS54202DDCR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps54202.pdf",
            })
    c4 = Cur(650, 40)
    s.place("C36", "C", "10u 50V X7R VIN", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("EC_AON_IN", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "TDK", "MPN": "CGA5L1X7R1H106K160AC"})
    s.place("C37", "C", "100n 50V X7R VIN HF", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("EC_AON_IN", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D"})
    s.place("C38", "C", "100n (BOOT cap)", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BUCK_BOOT", "local"), "2": ("BUCK_SW", "local")})
    s.place("L3", "L", "10uH 20% 3.3A Isat20", *c4.next(), footprint=FOOTPRINTS["L_XGL5030"],
            pin_nets={"1": ("BUCK_SW", "local"), "2": ("MCU_3V3", "hier")},
            extra_props={
                "Manufacturer": "Coilcraft", "MPN": "XGL5030-103MEC",
                "Datasheet": "https://www.coilcraft.com/getmedia/e64ac115-95f2-45c7-b798-1b3769b91583/xgl5030.pdf",
            })
    s.place("R35", "R", "100k 1% (3.3V FB hi)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BUCK_FB", "local")})
    s.place("R36", "R", "22.1k 1% (3.3V FB lo)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK_FB", "local"), "2": ("GND", "local")})
    for ref in ("C39", "C291"):
        s.place(ref, "C", "22u 16V X7R MCU_3V3 output", *c4.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CZ71C226ME15L"})
    s.place("C292", "C", "56p C0G TPS54202 feed-forward", *c4.next(), footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BUCK_FB", "local")})

    # TCA9539 resets every port to input whenever the EC supervisor/reset domain
    # asserts NRST. External SHDN pulldowns then force all PD eFuses off and they
    # stay off until restarted firmware deliberately reconfigures and validates
    # one source. This closes the warm-reset state-retention hole in TCA9535.
    s.text(650, 250, "== U44 resettable always-on source manager I/O expander ==")
    s.place("U44", "PCA9539xD", "TCA9539PWR resettable source manager @0x20", 700, 330,
            footprint=FOOTPRINTS["TCA9539PWR"],
            pin_nets={
                "1": ("SOURCE_MGR_INT_N", "local"), "2": ("GND", "local"), "3": ("NRST_NET", "local"),
                "4": ("PD1_PATH_EN", "hier"), "5": ("PD2_PATH_EN", "hier"),
                "6": ("PD3_PATH_EN", "hier"), "7": ("PD1_EFUSE_FAULT_N", "hier"),
                "8": ("PD2_EFUSE_FAULT_N", "hier"), "9": ("PD3_EFUSE_FAULT_N", "hier"),
                "10": ("PACK_FAULT_N", "hier"), "11": ("AUX_FAULT_N", "hier"),
                "12": ("GND", "local"), "13": ("PACK_RETRY_PULSE", "hier"),
                "14": ("AUX_PGOOD", "hier"), "15": ("MAIN_USB_VALID_N", "hier"),
                "16": ("MAIN_AUX_VALID_N", "hier"), "17": ("AON_FAULT_N", "hier"),
                "18": ("SOURCE_MGR_SPARE1", "local"), "19": ("SOURCE_MGR_SPARE2", "local"),
                "20": ("SOURCE_MGR_SPARE3", "local"), "21": ("GND", "local"),
                "22": ("I2C_SCL", "hier"), "23": ("I2C_SDA", "hier"),
                "24": ("MCU_3V3", "hier"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TCA9539PWR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tca9539.pdf",
                "ResetContract": "Pin 3 follows EC NRST; all P-ports reset to inputs and external SHDN pulldowns force every PD path off",
            })
    s.place("R780", "R", "10k source-manager INT pull-up", 650, 270, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("SOURCE_MGR_INT_N", "local")})
    s.place("R781", "R", "10k aggregate AON fault pull-up", 650, 282.7,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("AON_FAULT_N", "hier")})
    for idx in range(1, 4):
        s.place(f"R{781 + idx}", "R", "100k unused source-manager I/O pulldown", 650, 282.7 + idx * 10,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (f"SOURCE_MGR_SPARE{idx}", "local"), "2": ("GND", "local")})
    s.place("C780", "C", "100n source-manager local", 650, 322.7,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})

    # PB12 remains a firmware-controlled active-low mux reset request, but the
    # AND gate independently forces U45 RESET low whenever NRST is low. R172
    # gives the request a defined released state while the GPIO is high-Z.
    s.place("R172", "R", "100k service mux reset-request pull-up", 650, 345.44,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("SERVICE_MUX_RESET_REQ_N", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100KL"})
    s.place("U46", "74LVC1G08", "SN74LVC1G08DBVR EC-reset-qualified service mux reset", 700, 370,
            footprint=FOOTPRINTS["SN74LVC1G08DBV"],
            pin_nets={
                "1": ("NRST_NET", "local"),
                "2": ("SERVICE_MUX_RESET_REQ_N", "local"),
                "3": ("GND", "local"),
                "4": ("SERVICE_MUX_RESET_N", "hier"),
                "5": ("MCU_3V3", "hier"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G08DBVR",
                "ResetContract": "U45 RESET_N = EC NRST AND firmware reset request",
            })
    s.place("C781", "C", "100n service-mux reset gate local", 650, 358.14,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})

    s.gnd(650, 200)
    s.pwrflag(650, 220, "MCU_3V3")

    s.text(20, 340, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 346, "EC_GPIOx numbering is a local convenience mapping - see U4 pin_nets for actual STM32 pin/net cross-ref.")
    s.text(20, 352, "Anti-ghosting diodes for the keyboard matrix live on the separate MX ULP keyboard PCB.")
    s.text(20, 358, "MCU_USB_DP/DM (PA12/PA11, OTG_FS device mode) are unrelated to the power-only USB-C PD sink ports.")
    s.text(20, 364, "EC can assert Mu PWRBTN_N/RSTBTN_N; J16 case power is diode-isolated to Mu PWRBTN and charger QON.")
    s.text(20, 370, "Hardware UARTs: VHF USART3 on PB10/PB11, UHF USART6 on PC6/PC7, GNSS USART1 on PA9/PA10.")
    s.text(20, 376, "AUX_DC_ADC monitors the screw-terminal wide-DC input so firmware can classify and current-limit that source.")
    s.text(20, 383.54, "PA7/PB0 are thermal ADCs; fan PWM uses timer-capable PE9/TIM1_CH1 and tach remains EC-owned.")
    s.text(20, 391.16, "The EC has no user GPIO header; all tinkering I/O is isolated to the integrated RP2350 maker domain.")
    s.text(20, 398.78, "U5 follows the TPS54202 3.3V table and runs from EC_AON_IN so source validation firmware can execute before arbitration.")
    s.text(20, 414.02, "U5 EN is intentionally floated: TI specifies an internal pull-up that enables the converter when EN is open.")
    s.text(20, 406.4, "PE13 drives active-high MU_12V_ENABLE; PE14 reads MU_S0_HIGH; PE15 reads MU_12V_PG; PB1 reads TRACKPAD_FAULT_N.")

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
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON_ASSERT", "CHG_ENABLE",
        "CASE_PWRBTN_N", "MU_PWRBTN_N",
        "VSYS", "MCU_3V3", "EC_AON_IN", "AUX_DC_ADC", "USB_PD_SELECTED",
    ]
    ec_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON_ASSERT", "CHG_ENABLE",
        "CASE_PWRBTN_N", "MU_PWRBTN_N",
        "EC_AON_IN", "MCU_USB_DP", "MCU_USB_DM", "MCU_3V3", "AUX_DC_ADC",
        "FAN_PWM", "FAN_TACH", "LID_CLOSED_N",
        "THERM_SKIN_ADC", "THERM_MU_ADC",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N", "RADIO_VHF_PD_N", "RADIO_UHF_PD_N",
        "RADIO_VHF_SQL", "RADIO_UHF_SQL", "RADIO_VHF_RF_SEL_3V3", "RADIO_UHF_RF_SEL_3V3", "RADIO_AUDIO_SEL",
        "AUDIO_MIC_EN", "INTERNAL_USB_VBUS_FAULT_N",
        "SERVICE_MUX_RESET_N",
        "PD1_PATH_EN", "PD2_PATH_EN", "PD3_PATH_EN",
        "PD1_EFUSE_FAULT_N", "PD2_EFUSE_FAULT_N", "PD3_EFUSE_FAULT_N",
        "PACK_FAULT_N", "PACK_RETRY_PULSE", "AUX_FAULT_N", "AUX_PGOOD", "AON_FAULT_N",
        "MAIN_USB_VALID_N", "MAIN_AUX_VALID_N",
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
