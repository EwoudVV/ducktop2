from build_ducktop2 import Sheet, FOOTPRINTS


def usblc6(s, ref, value, x, y, dp, dm, rail):
    s.place(ref, "USBLC6-2P6", value, x, y, footprint=FOOTPRINTS["USBLC6-2P6"],
            pin_nets={
                "1": (dp, "local"), "6": (dp, "local"),
                "3": (dm, "local"), "4": (dm, "local"),
                "5": (rail, "hier" if rail != "GND" else "local"),
                "2": ("GND", "local"),
            })


def trackpad_usb_c_nets():
    return {
        "A1": ("GND", "local"), "A12": ("GND", "local"),
        "B1": ("GND", "local"), "B12": ("GND", "local"),
        "SH": ("GND", "local"),
        "A4": ("TPAD_5V", "local"), "A9": ("TPAD_5V", "local"),
        "B4": ("TPAD_5V", "local"), "B9": ("TPAD_5V", "local"),
        "A5": ("TPAD_CC1", "local"), "B5": ("TPAD_CC2", "local"),
        "A6": ("TPAD_CONN_DP", "local"), "B6": ("TPAD_CONN_DP", "local"),
        "A7": ("TPAD_CONN_DM", "local"), "B7": ("TPAD_CONN_DM", "local"),
        "A2": ("", "nc"), "A3": ("", "nc"), "A10": ("", "nc"), "A11": ("", "nc"),
        "B2": ("", "nc"), "B3": ("", "nc"), "B10": ("", "nc"), "B11": ("", "nc"),
        "A8": ("", "nc"), "B8": ("", "nc"),
    }


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 100
    s.refcounters["#FLG"] = 100

    s.text(20, 12.7, "== Internal laptop services: EC USB, touch, trackpad, fan, lid, display service ==")
    s.text(20, 20.32, "This sheet turns spare Mu USB2 ports and EC GPIO into internal laptop plumbing.")
    s.text(20, 27.94, "Display-specific retained-controller and raw-panel paths live on sheets 10 and 11.")

    # ---------------- EC USB device link to Mu host ----------------
    s.text(20, 50.8, "== EC USB device link to host Mu USB2_P3 ==")
    s.place("R200", "R", "22R USB DP series", 20, 76.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("EC_HOST_USB_DP", "hier"), "2": ("MCU_USB_DP", "hier")})
    s.place("R201", "R", "22R USB DM series", 20, 88.9, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("EC_HOST_USB_DM", "hier"), "2": ("MCU_USB_DM", "hier")})
    usblc6(s, "U60", "USBLC6-2P6 EC USB ESD", 110, 82.55, "EC_HOST_USB_DP", "EC_HOST_USB_DM", "MCU_3V3")
    s.place("J50", "Conn_01x04", "DNP EC USB probe", 205, 82.55,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("EC_HOST_USB_DM", "hier"),
                "3": ("EC_HOST_USB_DP", "hier"),
                "4": ("MCU_3V3", "hier"),
            })

    # ---------------- Internal touchscreen USB2 link ----------------
    s.text(20, 135.89, "== Internal touchscreen USB2 link on Mu USB2_P4 ==")
    s.place("R202", "R", "22R touch DP series", 20, 160.02, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TOUCH_USB_DP", "hier"), "2": ("TOUCH_CONN_DP", "local")})
    s.place("R203", "R", "22R touch DM series", 20, 172.72, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TOUCH_USB_DM", "hier"), "2": ("TOUCH_CONN_DM", "local")})
    usblc6(s, "U61", "USBLC6-2P6 touch USB ESD", 110, 166.37, "TOUCH_CONN_DP", "TOUCH_CONN_DM", "SYS_5V")
    s.place("J51", "Conn_01x06", "DNP alternate touchscreen USB/control", 205, 166.37,
            footprint=FOOTPRINTS["Conn_01x06"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("SYS_5V", "hier"),
                "3": ("TOUCH_CONN_DM", "local"),
                "4": ("TOUCH_CONN_DP", "local"),
                "5": ("TOUCH_RESET_N", "hier"),
                "6": ("TOUCH_INT_N", "hier"),
            })
    s.place("C200", "C", "10u touch VBUS local", 205, 198.12, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("C201", "C", "100n touch local", 205, 210.82, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("R204", "R", "100k touch reset pull-up", 20, 190.5, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TOUCH_RESET_N", "hier")})
    s.place("R205", "R", "100k touch INT pull-up", 20, 203.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TOUCH_INT_N", "hier")})

    # ---------------- Internal trackpad USB2/HID link ----------------
    s.text(20, 235.0, "== Required internal trackpad on Mu USB2_P8 ==")
    s.place("R250", "R", "22R trackpad DP series", 20, 259.08, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TRACKPAD_USB_DP", "hier"), "2": ("TPAD_CONN_DP", "local")})
    s.place("R251", "R", "22R trackpad DM series", 20, 271.78, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TRACKPAD_USB_DM", "hier"), "2": ("TPAD_CONN_DM", "local")})
    usblc6(s, "U62", "USBLC6-2P6 trackpad USB ESD", 110, 265.43, "TPAD_CONN_DP", "TPAD_CONN_DM", "SYS_5V")
    s.place("F201", "Fuse", "500mA trackpad 5V polyfuse", 20, 297.18, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("TPAD_5V", "local")})
    s.place("J58", "USB_C_Receptacle_Passive", "Internal USB-C receptacle for cable-attached USB trackpad", 205, 278.13,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets=trackpad_usb_c_nets())
    s.place("R254", "R", "56k USB-C Rp default current CC1", 330, 246.38, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TPAD_5V", "local"), "2": ("TPAD_CC1", "local")})
    s.place("R255", "R", "56k USB-C Rp default current CC2", 330, 259.08, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TPAD_5V", "local"), "2": ("TPAD_CC2", "local")})
    s.place("J57", "Conn_01x10", "DNP trackpad FFC fallback: USB HID plus optional EC I2C/control", 205, 335.28,
            footprint=FOOTPRINTS["Conn_01x10_FFC"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("TPAD_5V", "local"),
                "3": ("TPAD_CONN_DM", "local"),
                "4": ("TPAD_CONN_DP", "local"),
                "5": ("MCU_3V3", "hier"),
                "6": ("I2C_SCL", "hier"),
                "7": ("I2C_SDA", "hier"),
                "8": ("TPAD_INT_N", "hier"),
                "9": ("TPAD_RESET_N", "hier"),
                "10": ("GND", "local"),
            })
    s.place("C280", "C", "10u trackpad 5V local", 330, 284.48, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("TPAD_5V", "local"), "2": ("GND", "local")})
    s.place("C281", "C", "100n trackpad 3V3 sideband", 330, 297.18, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("R252", "R", "10k trackpad INT pull-up", 20, 309.88, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TPAD_INT_N", "hier")})
    s.place("R253", "R", "100k trackpad reset pull-up", 20, 322.58, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TPAD_RESET_N", "hier")})
    s.text(20, 345.44, "J58 is the normal trackpad connector for a USB-C cable trackpad. J57 is DNP fallback only if the trackpad is gutted to FFC/wires.")

    # ---------------- Fan and thermal service ----------------
    s.text(330, 50.8, "== Fan, lid, and thermal service ==")
    s.place("J52", "Conn_01x04", "4-wire 5V PWM blower/fan: GND, fused 5V, tach, PWM", 410, 82.55,
            footprint=FOOTPRINTS["Conn_01x04"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("FAN_5V", "local"),
                "3": ("FAN_TACH", "hier"),
                "4": ("FAN_PWM_CONN", "local"),
            })
    s.place("F200", "Fuse", "750mA fan polyfuse", 330, 63.5, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("FAN_5V", "local")})
    s.place("C205", "C", "10u fan local bulk", 330, 114.3, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("FAN_5V", "local"), "2": ("GND", "local")})
    s.place("C206", "C", "100n fan local", 330, 127, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FAN_5V", "local"), "2": ("GND", "local")})
    s.place("R206", "R", "10k fan tach pull-up", 330, 76.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FAN_TACH", "hier")})
    s.place("R207", "R", "100R fan PWM gate series", 330, 88.9, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FAN_PWM", "hier"), "2": ("FAN_PWM_GATE", "local")})
    s.place("R208", "R", "100k fan PWM default off", 330, 101.6, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FAN_PWM_GATE", "local"), "2": ("GND", "local")})
    s.place("Q200", "Q_NMOS_SOT23_GSD", "Fan PWM open-drain sink", 520, 88.9, footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("FAN_PWM_GATE", "local"), "2": ("GND", "local"), "3": ("FAN_PWM_CONN", "local")})
    s.place("R216", "R", "DNP 10k fan PWM pull-up", 520, 114.3, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FAN_5V", "local"), "2": ("FAN_PWM_CONN", "local")})
    s.place("J53", "Conn_01x02", "Lid/hall switch", 410, 130.81,
            footprint=FOOTPRINTS["Conn_01x02_Header"],
            pin_nets={"1": ("LID_CLOSED_N", "hier"), "2": ("GND", "local")})
    s.place("R209", "R", "10k lid pull-up", 330, 130.81, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("LID_CLOSED_N", "hier")})
    s.place("J54", "Conn_01x02", "Skin/hinge NTC", 410, 160.02,
            footprint=FOOTPRINTS["Conn_01x02_Header"],
            pin_nets={"1": ("THERM_SKIN_ADC", "hier"), "2": ("GND", "local")})
    s.place("R210", "R", "10k thermal divider pull-up", 330, 160.02, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("THERM_SKIN_ADC", "hier")})
    s.place("C202", "C", "100n thermal ADC filter", 330, 172.72, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("THERM_SKIN_ADC", "hier"), "2": ("GND", "local")})
    s.place("J56", "Conn_01x02", "Mu heatsink/spreader NTC", 570, 160.02,
            footprint=FOOTPRINTS["Conn_01x02_Header"],
            pin_nets={"1": ("THERM_MU_ADC", "hier"), "2": ("GND", "local")})
    s.place("R215", "R", "10k Mu thermal pull-up", 490, 160.02, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("THERM_MU_ADC", "hier")})
    s.place("C207", "C", "100n Mu thermal ADC filter", 490, 172.72, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("THERM_MU_ADC", "hier"), "2": ("GND", "local")})

    # ---------------- Display/backlight service harness ----------------
    s.text(330, 220.98, "== DNP low-speed display/backlight service harness ==")
    s.place("J55", "Conn_01x20", "DNP low-speed display/backlight service FFC", 435, 285.75,
            footprint=FOOTPRINTS["Conn_01x20_FFC"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("SYS_5V", "hier"),
                "3": ("SYS_3V3", "hier"),
                "4": ("I2C_SCL", "hier"),
                "5": ("I2C_SDA", "hier"),
                "6": ("LCD_BL_PWM_FFC", "local"),
                "7": ("LCD_BL_EN", "hier"),
                "8": ("PANEL_PWR_EN", "hier"),
                "9": ("PANEL_RESET_N", "hier"),
                "10": ("TOUCH_INT_N", "hier"),
                "11": ("TOUCH_RESET_N", "hier"),
                "12": ("GND", "local"),
                "13": ("", "nc"), "14": ("", "nc"), "15": ("", "nc"), "16": ("", "nc"),
                "17": ("", "nc"), "18": ("", "nc"), "19": ("", "nc"), "20": ("", "nc"),
            })
    s.place("R211", "R", "100k panel power default off", 330, 246.38, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PANEL_PWR_EN", "hier"), "2": ("GND", "local")})
    s.place("R212", "R", "100k backlight EN default off", 330, 259.08, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("LCD_BL_EN", "hier"), "2": ("GND", "local")})
    s.place("R213", "R", "100R backlight PWM series", 330, 271.78, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("LCD_BL_PWM", "hier"), "2": ("LCD_BL_PWM_FFC", "local")})
    s.place("R214", "R", "100k panel reset pull-up", 330, 284.48, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("PANEL_RESET_N", "hier")})
    s.place("C203", "C", "10u display service bulk", 330, 307.34, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("C204", "C", "100n display service", 330, 320.04, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})

    s.gnd(520, 360)
    s.text(20, 355.6, "NOTES:")
    s.text(20, 363.22, "EC enumerates to the x86 host as a plain USB device over Mu USB2_P3; firmware exposes keyboard/power/telemetry.")
    s.text(20, 370.84, "Touchscreen USB is separate on Mu USB2_P4; sheet 11 owns the retained Intehill USB-C touch/power path.")
    s.text(20, 378.46, "Trackpad uses Mu USB2_P8 as a direct internal USB HID pointing device; EC only owns reset/interrupt/sideband.")
    s.text(20, 386.08, "J51 and J55 are DNP alternate/service harnesses; sheets 10/11 own the real display video paths.")
    s.text(20, 393.7, "Fan PWM/tach are EC-owned. J52 uses fused 5V, 3.3V tach pull-up, and an open-drain PWM sink.")
    s.text(20, 401.32, "Thermal control has separate skin/hinge and Mu heatsink NTCs on ADC-capable EC pins.")
    s.text(20, 408.94, "Cooling default is copper spreader/heatpipe/vapor chamber plus quiet blower; no Peltier/TEC in the base design.")
    s.text(20, 416.56, "Solid-state AirJet-style modules are a future mechanical option, not the assumed electrical baseline.")

    return s
