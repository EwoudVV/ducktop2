from build_ducktop2 import Sheet, FOOTPRINTS


def usblc6(s, ref, value, x, y, dp, dm, rail):
    s.place(ref, "USBLC6-2P6", value, x, y, footprint=FOOTPRINTS["USBLC6-2P6"],
            pin_nets={
                "1": (dp, "local"), "6": (dp, "local"),
                "3": (dm, "local"), "4": (dm, "local"),
                "5": (rail, "local" if rail.startswith("MON_") else "hier"),
                "2": ("GND", "local"),
            })


HDMI_LINES = [
    ("DDIB_TX2_P", "HDMI_D2_P"),
    ("DDIB_TX2_N", "HDMI_D2_N"),
    ("DDIB_TX1_P", "HDMI_D1_P"),
    ("DDIB_TX1_N", "HDMI_D1_N"),
    ("DDIB_TX0_P", "HDMI_D0_P"),
    ("DDIB_TX0_N", "HDMI_D0_N"),
    ("DDIB_TX3_P", "HDMI_CK_P"),
    ("DDIB_TX3_N", "HDMI_CK_N"),
]


def hdmi_esd(s, ref, value, x, y, nets):
    s.place(ref, "TPD4E02B04DQA", value, x, y, footprint=FOOTPRINTS["TPD4E02B04DQA"],
            unit=1,
            pin_nets={
                "1": (nets[0], "local"),
                "2": (nets[1], "local"),
                "3": ("GND", "local"),
                "4": (nets[2], "local"),
                "5": (nets[3], "local"),
                "6": ("", "nc"),
                "7": ("", "nc"),
                "8": ("GND", "local"),
                "9": ("", "nc"),
                "10": ("", "nc"),
            })


def hdmi_connector_nets():
    return {
        "1": ("HDMI_D2_P", "local"),
        "2": ("GND", "local"),
        "3": ("HDMI_D2_N", "local"),
        "4": ("HDMI_D1_P", "local"),
        "5": ("GND", "local"),
        "6": ("HDMI_D1_N", "local"),
        "7": ("HDMI_D0_P", "local"),
        "8": ("GND", "local"),
        "9": ("HDMI_D0_N", "local"),
        "10": ("HDMI_CK_P", "local"),
        "11": ("GND", "local"),
        "12": ("HDMI_CK_N", "local"),
        "13": ("", "nc"),
        "14": ("", "nc"),
        "15": ("HDMI_SCL_CONN", "local"),
        "16": ("HDMI_SDA_CONN", "local"),
        "17": ("GND", "local"),
        "18": ("MON_HDMI_5V", "local"),
        "19": ("HDMI_HPD_CONN", "local"),
        "SH": ("GND", "local"),
    }


def monitor_usb_c_nets():
    return {
        "A1": ("GND", "local"), "A12": ("GND", "local"),
        "B1": ("GND", "local"), "B12": ("GND", "local"),
        "SH": ("GND", "local"),
        "A4": ("MON_USB_5V", "local"), "A9": ("MON_USB_5V", "local"),
        "B4": ("MON_USB_5V", "local"), "B9": ("MON_USB_5V", "local"),
        "A5": ("MON_CC1", "local"), "B5": ("MON_CC2", "local"),
        "A6": ("MON_TOUCH_DP", "local"), "B6": ("MON_TOUCH_DP", "local"),
        "A7": ("MON_TOUCH_DM", "local"), "B7": ("MON_TOUCH_DM", "local"),
        "A2": ("", "nc"), "A3": ("", "nc"), "A10": ("", "nc"), "A11": ("", "nc"),
        "B2": ("", "nc"), "B3": ("", "nc"), "B10": ("", "nc"), "B11": ("", "nc"),
        "A8": ("", "nc"), "B8": ("", "nc"),
    }


def monitor_button_nets():
    return {
        "1": ("MON_KEY_COMMON", "local"),
        "2": ("MON_KEY_POWER", "local"),
        "3": ("MON_KEY_MENU", "local"),
        "4": ("MON_KEY_VOL_UP", "local"),
        "5": ("MON_KEY_VOL_DN", "local"),
        "6": ("MON_KEY_BRIGHT_UP", "local"),
        "7": ("MON_KEY_BRIGHT_DN", "local"),
        "8": ("MON_KEY_SOURCE_EXIT", "local"),
        "9": ("MON_KEY_LED_IR", "local"),
        "10": ("MON_KEY_SPARE", "local"),
    }


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 300
    s.refcounters["#FLG"] = 300

    s.text(20, 12.7, "== Intehill retained-controller monitor interface ==")
    s.text(20, 20.32, "Internal-cable path for the 16in 2560x1600 120Hz touchscreen portable monitor/controller.")
    s.text(20, 27.94, "Video/audio use Mu DDIB HDMI 2.0; touch/power use an internal 5V USB-C source harness.")
    s.text(20, 35.56, "Monitor power/volume/brightness buttons are passed through by traces only; no EC control is added.")

    # ---------------- HDMI video/audio to retained monitor controller ----------------
    s.text(20, 50.8, "== DDIB HDMI 2.0 video/audio to monitor HDMI input, 2560x1600@120 target ==")
    s.place("J300", "HDMI_A", "Internal HDMI to Intehill controller", 115, 125,
            footprint=FOOTPRINTS["HDMI_A"], pin_nets=hdmi_connector_nets())

    for i, (source, conn) in enumerate(HDMI_LINES):
        x = 250 + (i % 4) * 55
        y = 82.55 + (i // 4) * 25.4
        s.place(f"C{300 + i}", "C", "100n HDMI AC cap", x, y, footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (source, "hier"), "2": (conn, "local")})
        s.place(f"R{300 + i}", "R", "470R HDMI bias per Mu ref", x, y + 10.16, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (conn, "local"), "2": ("GND", "local")})

    hdmi_esd(s, "U300", "TPD4E02B04DQA HDMI2.0 TMDS ESD A", 250, 160,
             ["HDMI_D2_P", "HDMI_D2_N", "HDMI_D1_P", "HDMI_D1_N"])
    hdmi_esd(s, "U301", "TPD4E02B04DQA HDMI2.0 TMDS ESD B", 390, 160,
             ["HDMI_D0_P", "HDMI_D0_N", "HDMI_CK_P", "HDMI_CK_N"])

    s.place("F300", "Fuse", "100mA HDMI 5V detect fuse", 520, 76.2,
            footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("MON_HDMI_5V", "local")})
    s.place("C308", "C", "1u HDMI 5V", 600, 76.2, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MON_HDMI_5V", "local"), "2": ("GND", "local")})
    s.place("R308", "R", "2.2k HDMI DDC SCL pull-up", 520, 101.6, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MON_HDMI_5V", "local"), "2": ("HDMI_SCL_CONN", "local")})
    s.place("R309", "R", "2.2k HDMI DDC SDA pull-up", 520, 114.3, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MON_HDMI_5V", "local"), "2": ("HDMI_SDA_CONN", "local")})
    s.place("R310", "R", "100R HPD series", 520, 127, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DDIB_HPD", "hier"), "2": ("HDMI_HPD_CONN", "local")})
    s.place("R311", "R", "100R DDC SCL series", 520, 139.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DDIB_DDC_SCL", "hier"), "2": ("HDMI_SCL_CONN", "local")})
    s.place("R312", "R", "100R DDC SDA series", 520, 152.4, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("DDIB_DDC_SDA", "hier"), "2": ("HDMI_SDA_CONN", "local")})
    s.pwrflag(665, 76.2, "MON_HDMI_5V")

    # ---------------- USB-C power and touch to retained monitor controller ----------------
    s.text(20, 215.9, "== Internal USB-C monitor power and touchscreen USB2 ==")
    s.place("J301", "USB_C_Receptacle", "Internal USB-C to Intehill power/touch port", 125, 300,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets=monitor_usb_c_nets())
    s.place("U303", "TPS2592xx", "TPS2592xx monitor 5V eFuse, set ~3A", 315, 246.38,
            footprint=FOOTPRINTS["TPS2592xx"],
            pin_nets={
                "1": ("MON_EFUSE_DVDT", "local"),
                "2": ("PANEL_PWR_EN", "hier"),
                "3": ("SYS_5V", "hier"), "4": ("SYS_5V", "hier"), "5": ("SYS_5V", "hier"),
                "6": ("MON_USB_5V", "local"), "7": ("MON_USB_5V", "local"), "8": ("MON_USB_5V", "local"),
                "9": ("", "nc"),
                "10": ("MON_EFUSE_ILIM", "local"),
                "11": ("GND", "local"),
            })
    s.place("R320", "R", "22R touch DP series", 300, 279.4, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TOUCH_USB_DP", "hier"), "2": ("MON_TOUCH_DP", "local")})
    s.place("R321", "R", "22R touch DM series", 300, 292.1, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TOUCH_USB_DM", "hier"), "2": ("MON_TOUCH_DM", "local")})
    s.place("R322", "R", "10k Rp 3A advertise", 300, 317.5, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MON_USB_5V", "local"), "2": ("MON_CC1", "local")})
    s.place("R323", "R", "10k Rp 3A advertise", 300, 330.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MON_USB_5V", "local"), "2": ("MON_CC2", "local")})
    s.place("R324", "R", "100k monitor power default off", 390, 220.98, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PANEL_PWR_EN", "hier"), "2": ("GND", "local")})
    s.place("R325", "R", "82.5k 1% ILIM ~3A", 390, 233.68, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MON_EFUSE_ILIM", "local"), "2": ("GND", "local")})
    s.place("C311", "C", "10n dV/dT soft-start", 390, 246.38, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MON_EFUSE_DVDT", "local"), "2": ("GND", "local")})
    usblc6(s, "U302", "USBLC6-2P6 monitor USB2 ESD", 430, 285.75,
           "MON_TOUCH_DP", "MON_TOUCH_DM", "MON_USB_5V")
    s.place("C309", "C", "47u monitor VBUS bulk", 520, 246.38, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("MON_USB_5V", "local"), "2": ("GND", "local")})
    s.place("C310", "C", "100n monitor VBUS", 520, 259.08, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MON_USB_5V", "local"), "2": ("GND", "local")})
    s.gnd(585, 330.2)

    # ---------------- Monitor keypad/button pass-through ----------------
    s.text(20, 365.76, "== Monitor keypad/button pass-through ==")
    s.place("J302", "Conn_01x10", "Monitor controller button harness in", 115, 424.18,
            footprint=FOOTPRINTS["Conn_01x10_FFC"], pin_nets=monitor_button_nets())
    s.place("J303", "Conn_01x10", "Case button board harness out", 300, 424.18,
            footprint=FOOTPRINTS["Conn_01x10_FFC"], pin_nets=monitor_button_nets())
    s.text(390, 383.54, "J302/J303 are one-to-one traces only.")
    s.text(390, 391.16, "Use for power/menu/volume/brightness keypad or resistor ladder.")
    s.text(390, 398.78, "Final pin order must follow the opened monitor's button board.")

    s.text(20, 480.06, "NOTES:")
    s.text(20, 487.68, "This retained-controller path avoids external cables while preserving the Intehill controller, touch board, and speakers.")
    s.text(20, 495.3, "HDMI carries display audio to the monitor's integrated speakers; no separate speaker amplifier is added in this pass.")
    s.text(20, 502.92, "DDIB_TX3 is HDMI TMDS clock; DDIB_TX2/1/0 map to HDMI data2/1/0 per the Mu HDMI reference direction.")
    s.text(20, 510.54, "Keep this path HDMI 2.0/18Gbps capable end-to-end for 2560x1600@120; avoid HDMI 1.4-only cables/adapters/ESD.")
    s.text(20, 518.16, "U303 lets the EC gate monitor power with soft-start/current limit; set ILIM/dVdT after measuring monitor inrush/current.")
    s.text(20, 525.78, "J301 is a 5V-only Type-C source with 10k Rp for 3A advertisement; add PD only if the monitor demands it.")
    s.text(20, 533.4, "Mechanical choice remains open: disassembled internal HDMI/USB-C plugs, low-profile adapters, or raw-panel replacement.")

    return s
