from build_ducktop2 import Sheet, FOOTPRINTS


def usblc6(s, ref, value, x, y, dp, dm, rail):
    s.place(ref, "USBLC6-2P6", value, x, y, footprint=FOOTPRINTS["USBLC6-2P6"],
            pin_nets={
                "1": (dp, "local"), "6": (dp, "local"),
                "3": (dm, "local"), "4": (dm, "local"),
                "5": (rail, "hier" if rail != "GND" else "local"),
                "2": ("GND", "local"),
            }, extra_props={
                "Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2P6",
                "Datasheet": "https://www.st.com/resource/en/datasheet/usblc6-2.pdf",
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

    s.text(20, 12.7, "== Internal laptop services: EC USB, trackpad, fan, lid, thermal ==")
    s.text(20, 20.32, "This sheet turns spare Mu USB2 ports and EC GPIO into internal laptop plumbing.")
    s.text(20, 27.94, "The internal display uses the Mu onboard eDP connector and needs no motherboard USB path.")

    # ---------------- EC USB device link to Mu host ----------------
    s.text(20, 50.8, "== EC USB device link to host Mu USB2_P3 ==")
    s.place("R200", "R", "22R USB DP series", 20, 76.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("EC_USB_ISO_DP", "local"), "2": ("MCU_USB_DP", "hier")})
    s.place("R201", "R", "22R USB DM series", 20, 88.9, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("EC_USB_ISO_DM", "local"), "2": ("MCU_USB_DM", "hier")})
    s.place("U61", "TS3USB30EDGSR", "TS3USB30EDGSR EC USB host-state isolation", 70, 82.55,
            footprint=FOOTPRINTS["TS3USB30EDGSR"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("EC_HOST_USB_DP", "hier"), "3": ("", "nc"),
                "4": ("EC_USB_ISO_DP", "local"), "5": ("GND", "local"),
                "6": ("EC_USB_ISO_DM", "local"), "7": ("", "nc"),
                "8": ("EC_HOST_USB_DM", "hier"), "9": ("EC_USB_OE_N", "local"),
                "10": ("MCU_3V3", "hier"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TS3USB30EDGSR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf",
            })
    s.place("Q60", "Q_NMOS_SOT23_GSD", "2N7002 physical host-VBUS USB connect gate", 150, 63.5,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("INTERNAL_USB_VBUS_VALID", "hier"), "2": ("GND", "local"),
                      "3": ("EC_USB_OE_N", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "2N7002KT1G"})
    s.place("R202", "R", "10k EC USB default-disconnect pull-up", 195, 63.5,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("EC_USB_OE_N", "local")})
    s.place("C208", "C", "100n EC USB switch local", 285, 63.5,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    usblc6(s, "U60", "USBLC6-2P6 EC USB ESD", 110, 82.55, "EC_HOST_USB_DP", "EC_HOST_USB_DM", "MCU_3V3")
    s.place("J50", "Conn_01x04", "DNP EC USB probe", 205, 82.55,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("EC_HOST_USB_DM", "hier"),
                "3": ("EC_HOST_USB_DP", "hier"),
                "4": ("MCU_3V3", "hier"),
            }, on_board=False)

    # ---------------- Internal trackpad USB2/HID link ----------------
    s.text(20, 235.0, "== Required internal trackpad on Mu USB2_P8 ==")
    s.place("R250", "R", "22R trackpad DP series", 20, 259.08, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TRACKPAD_USB_DP", "hier"), "2": ("TPAD_CONN_DP", "local")})
    s.place("R251", "R", "22R trackpad DM series", 20, 271.78, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TRACKPAD_USB_DM", "hier"), "2": ("TPAD_CONN_DM", "local")})
    s.place("U62", "TPD4EUSB30", "TPD4E05U06 trackpad USB2/CC ESD", 110, 265.43,
            footprint=FOOTPRINTS["TPD4E05U06DQA"],
            pin_nets={
                "1": ("TPAD_CONN_DP", "local"), "2": ("TPAD_CONN_DM", "local"),
                "3": ("GND", "local"), "4": ("TPAD_CC1", "local"),
                "5": ("TPAD_CC2", "local"), "6": ("", "nc"),
                "7": ("", "nc"), "8": ("GND", "local"),
                "9": ("", "nc"), "10": ("", "nc"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPD4E05U06DQAR"})
    s.place("U63", "TPS25810RVC", "TPS25810 attach-controlled trackpad Type-C source", 20, 310,
            footprint=FOOTPRINTS["TPS25810RVC"],
            pin_nets={
                "1": ("TRACKPAD_FAULT_N", "hier"),
                "2": ("TPAD_5V_PRE", "local"), "3": ("TPAD_5V_PRE", "local"),
                "4": ("TPAD_5V_PRE", "local"), "5": ("SYS_3V3", "hier"),
                "6": ("MU_HOST_ACTIVE", "hier"),
                "7": ("GND", "local"), "8": ("GND", "local"),
                "9": ("TPAD_REF_RTN", "local"), "10": ("TPAD_REF", "local"),
                "11": ("TPAD_CC1", "local"), "12": ("GND", "local"),
                "13": ("TPAD_CC2", "local"),
                "14": ("TPAD_5V", "local"), "15": ("TPAD_5V", "local"),
                "16": ("", "nc"), "17": ("", "nc"), "18": ("", "nc"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("GND", "local"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS25810RVCR"})
    s.place("U64", "TPS2553D", "TPS2553DDBVR trackpad 0.61A branch switch", 470, 322.58,
            footprint=FOOTPRINTS["TPS2553DDBV"],
            pin_nets={
                "1": ("SYS_5V", "hier"), "2": ("GND", "local"),
                "3": ("MU_HOST_ACTIVE", "hier"), "4": ("TRACKPAD_FAULT_N", "hier"),
                "5": ("TPAD_ILIM", "local"), "6": ("TPAD_5V_PRE", "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS2553DDBVR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps2553.pdf",
            })
    s.place("J58", "USB_C_Receptacle_Passive", "Internal USB-C receptacle for cable-attached USB trackpad", 205, 278.13,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets=trackpad_usb_c_nets(),
            extra_props={"Manufacturer": "Molex", "MPN": "105450-0101"})
    s.place("R254", "R", "100k 1% <=100ppm TPS25810 REF", 330, 246.38, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TPAD_REF", "local"), "2": ("TPAD_REF_RTN", "local")})
    s.place("R252", "R", "43.2k 1% TPS2553 trackpad ILIM 0.61A nominal", 380, 271.78,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TPAD_ILIM", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0743K2L"})
    s.place("C280", "C", "100n TPS2553 input bypass", 330, 271.78, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("C281", "C", "100n TPS25810 input", 330, 284.48, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("TPAD_5V_PRE", "local"), "2": ("GND", "local")})
    s.place("C282", "C", "100n TPS25810 AUX", 330, 297.18, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place("C283", "C", "10u trackpad VBUS", 330, 309.88, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("TPAD_5V", "local"), "2": ("GND", "local")})
    s.place("C284", "C_Polarized", "150u 10V TPS25810 input reservoir", 330, 322.58,
            footprint="Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D",
            pin_nets={"1": ("TPAD_5V_PRE", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "KEMET", "MPN": "T520D157M010ATE025"})
    s.place("R256", "R", "10k trackpad fault pull-up", 380, 322.58,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TRACKPAD_FAULT_N", "hier")})
    s.text(20, 345.44, "J58 is the only trackpad connector. TPS2553 isolates the 150uF input reservoir; TPS25810 applies connector VBUS only after attach.")

    # ---------------- Fan and thermal service ----------------
    s.text(330, 50.8, "== Fan, lid, and thermal service ==")
    s.place("J52", "Conn_01x04", "Delta BFB04512HHA-CZ0T: GND, fused 12V, FG, PWM", 410, 82.55,
            footprint=FOOTPRINTS["Conn_01x04_Service_GH"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("FAN_12V", "local"),
                "3": ("FAN_TACH", "hier"),
                "4": ("FAN_PWM_CONN", "local"),
            }, extra_props={
                "Manufacturer": "JST", "MPN": "SM04B-GHS-TB",
                "MatingHousing": "GHR-04V-S", "Contacts": "SSHL-002T-P0.2",
                "EndpointManufacturer": "Delta Electronics",
                "EndpointMPN": "BFB04512HHA-CZ0T",
                "EndpointDatasheet": "https://www.delta-fan.com/Download/Spec/BFB04512HHA-CZ0T.pdf",
                "EndpointWireMap": "1=BLACK/GND;2=RED/+12V;3=WHITE/FG;4=YELLOW/PWM",
                "EndpointElectricalContract": "12V_NOMINAL_5.0_TO_13.5V;0.26A_MAX;25KHZ_OPEN_DRAIN_PWM;FLOAT_PWM_FULL_SPEED;FG_OPEN_COLLECTOR_2PPR",
            })
    s.place("F200", "Fuse", "750mA 16V fan polyfuse", 330, 63.5, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("MU_12V", "hier"), "2": ("FAN_12V", "local")},
            extra_props={"Manufacturer": "Littelfuse", "MPN": "1206L075/16WR"})
    s.place("C205", "C", "10u 25V X7R fan local bulk", 330, 114.3, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("FAN_12V", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    s.place("C206", "C", "100n 25V X7R fan local", 330, 127, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("FAN_12V", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71E104KA01D"})
    s.place("R206", "R", "8.2k fan FG pull-up", 330, 76.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("FAN_TACH", "hier")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-078K2L"})
    s.place("C209", "C", "3.9n fan FG filter", 520, 114.3, footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("FAN_TACH", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM1555C1H392JA01D"})
    s.place("R207", "R", "100R fan PWM gate series", 330, 88.9, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FAN_PWM", "hier"), "2": ("FAN_PWM_GATE", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100RL"})
    s.place("R208", "R", "100k gate pull-down; fan defaults full speed", 330, 101.6,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("FAN_PWM_GATE", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100KL"})
    s.place("Q200", "Q_NMOS_SOT23_GSD", "2N7002KT1G fan PWM open-drain sink", 520, 88.9,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("FAN_PWM_GATE", "local"), "2": ("GND", "local"), "3": ("FAN_PWM_CONN", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "2N7002KT1G"})
    s.place("J53", "Conn_01x02", "Lid/hall switch", 410, 130.81,
            footprint=FOOTPRINTS["Conn_01x02_Service_GH"],
            pin_nets={"1": ("LID_CLOSED_N", "hier"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "JST", "MPN": "SM02B-GHS-TB",
                "MatingHousing": "GHR-02V-S", "Contacts": "SSHL-002T-P0.2",
            })
    s.place("R209", "R", "10k lid pull-up", 330, 130.81, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("LID_CLOSED_N", "hier")})
    s.place("J54", "Conn_01x02", "Skin/hinge NTC", 410, 160.02,
            footprint=FOOTPRINTS["Conn_01x02_Service_GH"],
            pin_nets={"1": ("THERM_SKIN_ADC", "hier"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "JST", "MPN": "SM02B-GHS-TB",
                "MatingHousing": "GHR-02V-S", "Contacts": "SSHL-002T-P0.2",
            })
    s.place("R210", "R", "10k thermal divider pull-up", 330, 160.02, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("THERM_SKIN_ADC", "hier")})
    s.place("C202", "C", "100n thermal ADC filter", 330, 172.72, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("THERM_SKIN_ADC", "hier"), "2": ("GND", "local")})
    s.place("J56", "Conn_01x02", "Mu heatsink/spreader NTC", 570, 160.02,
            footprint=FOOTPRINTS["Conn_01x02_Service_GH"],
            pin_nets={"1": ("THERM_MU_ADC", "hier"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "JST", "MPN": "SM02B-GHS-TB",
                "MatingHousing": "GHR-02V-S", "Contacts": "SSHL-002T-P0.2",
            })
    s.place("R215", "R", "10k Mu thermal pull-up", 490, 160.02, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("THERM_MU_ADC", "hier")})
    s.place("C207", "C", "100n Mu thermal ADC filter", 490, 172.72, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("THERM_MU_ADC", "hier"), "2": ("GND", "local")})

    s.gnd(520, 360)
    s.text(20, 355.6, "NOTES:")
    s.text(20, 363.22, "EC enumerates over Mu USB2_P3 only after the carrier-generated physical INTERNAL_USB_VBUS is above the supervisor threshold. U61 defaults disconnected so an always-powered EC cannot back-drive an off host PHY.")
    s.text(20, 370.84, "The verified B160QAN03.K panel is non-touch; USB2_P4 is paired with native USB-C port 2.")
    s.text(20, 378.46, "Trackpad uses Mu USB2_P8 as a direct internal USB HID device. TRACKPAD_FAULT_N is pulled up to the EC; S3 removes trackpad VBUS, so wake-from-trackpad is not supported.")
    s.text(20, 386.08, "The Intehill controller remains a bench fixture/fallback and is not populated on the motherboard.")
    s.text(20, 393.7, "J52 is released for Delta BFB04512HHA-CZ0T: fused MU_12V, 8.2k/3.9n FG interface, and 25kHz open-drain PWM. Floating PWM commands full speed; firmware never drives the fan PWM node high.")
    s.text(20, 401.32, "Delta contract: 0.26A maximum, 35% minimum start duty, FG is open collector at 2 pulses/revolution, and 0% PWM stops the fan. Gate pull-down makes an unpowered/reset EC command full fan speed, not fan-off.")
    s.text(20, 408.94, "Thermal control has separate skin/hinge and Mu heatsink NTCs on ADC-capable EC pins.")
    s.text(20, 416.56, "The blower shares MU_12V: it is available whenever the Mu is powered. Thermal policy commands full fan and host throttle/shutdown before any final MU_12V cut; after a cut the passive coldplate/heatpipe/fin stack absorbs residual heat while heat generation is removed.")
    s.text(20, 424.18, "Cooling default is copper spreader/heatpipe/vapor chamber plus the released Delta blower; no Peltier/TEC in the base design. Solid-state AirJet-style modules are a future mechanical option only.")

    return s
