from build_ducktop2 import Sheet, FOOTPRINTS


RADIO_DB_SIGNAL_PINS = {
    "23": "RADIO_VHF_UART_TX",
    "24": "RADIO_VHF_UART_RX",
    "25": "RADIO_UHF_UART_TX",
    "26": "RADIO_UHF_UART_RX",
    "28": "RADIO_VHF_PTT_N",
    "29": "RADIO_UHF_PTT_N",
    "30": "RADIO_VHF_PD_N",
    "31": "RADIO_UHF_PD_N",
    "33": "RADIO_VHF_SQL",
    "34": "RADIO_UHF_SQL",
    "35": "RADIO_VHF_RF_SEL_3V3",
    "36": "RADIO_UHF_RF_SEL_3V3",
    "38": "GNSS_UART_RX",
    "39": "GNSS_UART_TX",
    "40": "GNSS_RESET_N",
    "41": "GNSS_PPS",
    "42": "GNSS_EXTINT",
}


RADIO_DB_PIN_NETS = {
    **{str(pin): ("RADIO_DB_5V", "local") for pin in range(1, 9)},
    **{str(pin): ("GND", "local") for pin in range(9, 17)},
    "17": ("RADIO_CODEC_USB_VBUS_DB", "local"),
    "18": ("RADIO_CODEC_USB_VBUS_DB", "local"),
    "19": ("RADIO_CODEC_USB_DP_DB", "local"),
    "20": ("RADIO_CODEC_USB_DM_DB", "local"),
    "21": ("GND", "local"),
    "22": ("GND", "local"),
    **{pin: (f"{net}_DB", "local") for pin, net in RADIO_DB_SIGNAL_PINS.items()},
    "27": ("GND", "local"),
    "32": ("GND", "local"),
    "37": ("GND", "local"),
    "43": ("GND", "local"),
    "44": ("RADIO_DB_PRESENT_N", "hier"),
    **{str(pin): ("GND", "local") for pin in range(45, 61)},
    "MP": ("GND", "local"),
}


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 2300
    s.refcounters["#FLG"] = 2300

    s.text(20, 12.7, "== Optional radio/GNSS/audio daughterboard interface ==")
    s.text(20, 20.32, "The main laptop cold-boots and operates normally with J2300 completely unpopulated.")
    s.text(20, 27.94, "Firmware may enable RADIO_DB_5V only after the passive PRESENT_N strap is detected.")

    s.text(20, 50.8, "== Default-off protected daughterboard power ==")
    s.place(
        "U2300", "TPS259470A", "TPS259470ARPW 2A reverse-blocking radio eFuse", 130, 105,
        footprint=FOOTPRINTS["TPS259470A"],
        pin_nets={
            "1": ("RADIO_DB_PWR_EN", "hier"),
            "2": ("GND", "local"),
            "3": ("", "nc"),
            "4": ("RADIO_DB_FAULT_N", "hier"),
            "5": ("SYS_5V", "hier"),
            "6": ("RADIO_DB_5V", "local"),
            "7": ("RADIO_DB_DVDT", "local"),
            "8": ("GND", "local"),
            "9": ("RADIO_DB_ILM", "local"),
            "10": ("", "nc"),
        },
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "TPS259470ARPW",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tps25947.pdf",
            "SafetyContract": "DEFAULT_OFF;REVERSE_BLOCKING;APPROX_2A_CURRENT_LIMIT",
        },
    )
    s.place("R2300", "R", "100k radio eFuse enable pulldown", 20, 76.2,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_DB_PWR_EN", "hier"), "2": ("GND", "local")})
    s.place("R2301", "R", "1.65k 0.1% radio eFuse ILM about 2.0A", 20, 88.9,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_DB_ILM", "local"), "2": ("GND", "local")})
    s.place("C2300", "C", "4.7n radio eFuse controlled rise", 20, 101.6,
            footprint=FOOTPRINTS["C_1n"],
            pin_nets={"1": ("RADIO_DB_DVDT", "local"), "2": ("GND", "local")})
    for ref, value, net, y, fp in (
        ("C2301", "10u SYS_5V radio eFuse input", "SYS_5V", 114.3, "C_10u"),
        ("C2302", "100n SYS_5V radio eFuse input HF", "SYS_5V", 127.0, "C_100n"),
        ("C2303", "22u RADIO_DB_5V output bulk", "RADIO_DB_5V", 139.7, "C_10u"),
        ("C2304", "100n RADIO_DB_5V output HF", "RADIO_DB_5V", 152.4, "C_100n"),
    ):
        s.place(ref, "C", value, 20, y, footprint=FOOTPRINTS[fp],
                pin_nets={"1": (net, "hier" if net == "SYS_5V" else "local"), "2": ("GND", "local")})

    # TLV803 asserts low until the switched rail is above 4.3 V. Its open-drain
    # output is pulled up by that same switched rail, divided, then restored to
    # a clean MCU_3V3 level by a Schmitt buffer. With the rail at 0 V the buffer
    # input is physically low, so PG cannot falsely assert while the board is off.
    s.place(
        "U2301", "TLV803EA43RDBZR", "TLV803EA43 4.3V radio rail supervisor", 260, 90,
        footprint=FOOTPRINTS["TLV803EA43RDBZR"],
        pin_nets={"1": ("RADIO_DB_PG_RAW", "local"), "2": ("GND", "local"), "3": ("RADIO_DB_5V", "local")},
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "TLV803EA43RDBZR"},
    )
    s.place("R2302", "R", "2.2k supervisor pull-up to switched 5V", 225, 115,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_DB_5V", "local"), "2": ("RADIO_DB_PG_RAW", "local")})
    s.place("R2303", "R", "10k radio PG level-divider top", 260, 115,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_DB_PG_RAW", "local"), "2": ("RADIO_DB_PG_DIV", "local")})
    s.place("R2304", "R", "20k radio PG level-divider bottom", 300, 115,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_DB_PG_DIV", "local"), "2": ("GND", "local")})
    s.place(
        "U2302", "74LVC1G17", "SN74LVC1G17DBVR radio PG level restore", 350, 100,
        footprint=FOOTPRINTS["SN74LVC1G17DBV"],
        pin_nets={
            "1": ("", "nc"), "2": ("RADIO_DB_PG_DIV", "local"), "3": ("GND", "local"),
            "4": ("RADIO_DB_PG", "hier"), "5": ("MCU_3V3", "hier"),
        },
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G17DBVR"},
    )
    s.place("C2305", "C", "100n radio PG buffer local", 350, 125,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("R2305", "R", "10k radio eFuse/shared fault pull-up", 420, 76.2,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("RADIO_DB_FAULT_N", "hier")})
    s.place("R2306", "R", "10k daughterboard-present pull-up; absent=high", 420, 88.9,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("RADIO_DB_PRESENT_N", "hier")})

    s.text(20, 190.5, "== USB codec isolation: no phantom device or back-power when daughterboard is absent ==")
    s.place(
        "U2303", "TS3USB30EDGSR", "TS3USB30E default-disconnected radio codec USB switch", 150, 245,
        footprint=FOOTPRINTS["TS3USB30EDGSR"],
        pin_nets={
            "1": ("GND", "local"),
            "2": ("RADIO_CODEC_USB_DP_HOST", "hier"),
            "3": ("", "nc"),
            "4": ("RADIO_CODEC_USB_DP_DB", "local"),
            "5": ("GND", "local"),
            "6": ("RADIO_CODEC_USB_DM_DB", "local"),
            "7": ("", "nc"),
            "8": ("RADIO_CODEC_USB_DM_HOST", "hier"),
            "9": ("RADIO_USB_OE_N", "local"),
            "10": ("MCU_3V3", "hier"),
        },
        extra_props={
            "Manufacturer": "Texas Instruments", "MPN": "TS3USB30EDGSR",
            "PowerOffContract": "USB_DP_DM_DISCONNECTED_UNLESS_RADIO_DB_PG_IS_HIGH",
        },
    )
    s.place("R2307", "R", "100k USB switch disable pull-up", 20, 228.6,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("RADIO_USB_OE_N", "local")})
    s.place("Q2300", "Q_NMOS_SOT23_GSD", "2N7002K radio-PG USB enable", 20, 241.3,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("RADIO_DB_PG", "hier"), "2": ("GND", "local"), "3": ("RADIO_USB_OE_N", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "2N7002KT1G"})
    s.place("C2306", "C", "100n USB switch local", 20, 254,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place(
        "U2304", "TPS2553D", "TPS2553D radio codec VBUS gate 0.20A", 330, 245,
        footprint=FOOTPRINTS["TPS2553DDBV"],
        pin_nets={
            "1": ("RADIO_CODEC_USB_VBUS_HOST", "hier"), "2": ("GND", "local"),
            "3": ("RADIO_DB_PG", "hier"), "4": ("RADIO_DB_FAULT_N", "hier"),
            "5": ("RADIO_CODEC_ILIM", "local"), "6": ("RADIO_CODEC_USB_VBUS_DB", "local"),
        },
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS2553DBVR"},
    )
    s.place("R2308", "R", "133k 1% TPS2553 current limit about 0.20A", 430, 228.6,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_CODEC_ILIM", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07133KL"})
    s.place("C2307", "C", "1u radio codec VBUS gate input", 430, 241.3,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("RADIO_CODEC_USB_VBUS_HOST", "hier"), "2": ("GND", "local")})
    s.place("C2308", "C", "10u radio codec VBUS gate output", 430, 254,
            footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("RADIO_CODEC_USB_VBUS_DB", "local"), "2": ("GND", "local")})
    s.place(
        "U2305", "USBLC6-2P6", "USBLC6-2P6 radio codec USB ESD", 520, 245,
        footprint=FOOTPRINTS["USBLC6-2P6"],
        pin_nets={
            "1": ("RADIO_CODEC_USB_DP_DB", "local"), "6": ("RADIO_CODEC_USB_DP_DB", "local"),
            "3": ("RADIO_CODEC_USB_DM_DB", "local"), "4": ("RADIO_CODEC_USB_DM_DB", "local"),
            "2": ("GND", "local"), "5": ("RADIO_CODEC_USB_VBUS_DB", "local"),
        },
        extra_props={"Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2P6"},
    )

    s.text(20, 304.8, "== Safe defaults for every off-board control ==")
    for idx, (net, rail, value, label) in enumerate((
        ("RADIO_VHF_PTT_N", "MCU_3V3", "10k", "VHF PTT inactive"),
        ("RADIO_UHF_PTT_N", "MCU_3V3", "10k", "UHF PTT inactive"),
        ("RADIO_VHF_PD_N", "GND", "10k", "VHF asleep"),
        ("RADIO_UHF_PD_N", "GND", "10k", "UHF asleep"),
        ("RADIO_VHF_RF_SEL_3V3", "GND", "100k", "VHF internal antenna"),
        ("RADIO_UHF_RF_SEL_3V3", "GND", "100k", "UHF internal antenna"),
        ("RADIO_VHF_UART_TX", "MCU_3V3", "100k", "VHF UART idle-high while absent"),
        ("RADIO_UHF_UART_TX", "MCU_3V3", "100k", "UHF UART idle-high while absent"),
        ("GNSS_UART_RX", "MCU_3V3", "100k", "GNSS RX idle-high while absent"),
        ("GNSS_RESET_N", "MCU_3V3", "100k", "GNSS reset released while absent"),
    )):
        x = 20 + (idx // 5) * 210
        y = 330.2 + (idx % 5) * 12.7
        s.place(f"R{2310 + idx}", "R", f"{value} {label}", x, y, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net, "hier"), "2": (rail, "hier" if rail == "MCU_3V3" else "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0710KL" if value == "10k" else "RC0603FR-07100KL"})
    for idx, (net, label) in enumerate((
        ("RADIO_VHF_UART_RX", "VHF RX default low"),
        ("RADIO_UHF_UART_RX", "UHF RX default low"),
        ("RADIO_VHF_SQL", "VHF SQL default low"),
        ("RADIO_UHF_SQL", "UHF SQL default low"),
        ("GNSS_UART_TX", "GNSS TX default low"),
        ("GNSS_PPS", "GNSS PPS default low"),
        ("GNSS_EXTINT", "GNSS EXTINT default low"),
    )):
        x = 440 + (idx // 4) * 190
        y = 330.2 + (idx % 4) * 12.7
        s.place(f"R{2320 + idx}", "R", f"100k {label} while daughterboard absent", x, y,
                footprint=FOOTPRINTS["R"], pin_nets={"1": (net, "hier"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100KL"})

    s.text(20, 398.78, "== Fault-isolating series resistors at the removable-board boundary ==")
    for idx, (pin, net) in enumerate(RADIO_DB_SIGNAL_PINS.items()):
        x = 20 + (idx // 9) * 300
        y = 426.72 + (idx % 9) * 10.16
        s.place(f"R{2340 + idx}", "R", f"4.7k J2300 pin {pin} signal isolation", x, y,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net, "hier"), "2": (f"{net}_DB", "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-074K7L",
                             "BoundaryContract": "LIMIT_FAULT_CURRENT_IF_DAUGHTERBOARD_IS_OFF_ABSENT_OR_DAMAGED"})

    s.text(20, 414.02, "== J2300 Hirose DF40 removable radio daughterboard connector ==")
    s.place(
        "J2300", "Conn_02x30_MP", "DF40C 60-pin optional radio daughterboard plug", 370, 540,
        footprint=FOOTPRINTS["Radio_DB_Main"], pin_nets=RADIO_DB_PIN_NETS,
        extra_props={
            "Manufacturer": "Hirose Electric", "MPN": "DF40C-60DP-0.4V(51)",
            "MatingConnector": "DF40C(2.0)-60DS-0.4V(51)",
            "StackHeight": "2.0mm",
            "AbsentBoardContract": "NO_RADIO_BOARD_REQUIRED_FOR_BOOT_OR_PRIMARY_LAPTOP_OPERATION",
        },
    )
    s.gnd(690, 600)
    s.text(20, 640, "NOTES:")
    s.text(20, 647.62, "Eight DF40 contacts share RADIO_DB_5V and thirty contacts are ground; route them as short, wide pours with stitching vias.")
    s.text(20, 655.24, "J2300 pin 44 is passively grounded only on the daughterboard. High means absent; low means physically installed.")
    s.text(20, 662.86, "The system-audio hub keeps its own codec on port 2; optional radio codec port 1 may remain empty without blocking enumeration.")
    s.text(20, 670.48, "USB data and VBUS remain physically disconnected until RADIO_DB_PG is valid; daughterboard faults cannot back-power the mainboard.")
    s.text(20, 678.1, "Firmware must require PRESENT_N low and FAULT_N high before asserting PWR_EN, then require PG high within a timeout.")
    s.text(20, 685.72, "R2340-R2356 limit fault current on every removable-board GPIO/UART/control line; no signal pin directly crosses J2300.")

    return s
