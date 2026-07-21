from build_ducktop2 import Sheet, FOOTPRINTS


def connector_pin_nets():
    nets = {
        **{str(pin): ("RADIO_DB_5V", "hier") for pin in range(1, 9)},
        **{str(pin): ("GND", "local") for pin in range(9, 17)},
        "17": ("RADIO_CODEC_USB_VBUS", "hier"),
        "18": ("RADIO_CODEC_USB_VBUS", "hier"),
        "19": ("RADIO_CODEC_USB_DP", "hier"),
        "20": ("RADIO_CODEC_USB_DM", "hier"),
        "21": ("GND", "local"),
        "22": ("GND", "local"),
        "23": ("RADIO_VHF_UART_TX", "hier"),
        "24": ("RADIO_VHF_UART_RX", "hier"),
        "25": ("RADIO_UHF_UART_TX", "hier"),
        "26": ("RADIO_UHF_UART_RX", "hier"),
        "27": ("GND", "local"),
        "28": ("RADIO_VHF_PTT_N", "hier"),
        "29": ("RADIO_UHF_PTT_N", "hier"),
        "30": ("RADIO_VHF_PD_N", "hier"),
        "31": ("RADIO_UHF_PD_N", "hier"),
        "32": ("GND", "local"),
        "33": ("RADIO_VHF_SQL", "hier"),
        "34": ("RADIO_UHF_SQL", "hier"),
        "35": ("RADIO_VHF_RF_SEL_3V3", "hier"),
        "36": ("RADIO_UHF_RF_SEL_3V3", "hier"),
        "37": ("GND", "local"),
        "38": ("GNSS_UART_RX", "hier"),
        "39": ("GNSS_UART_TX", "hier"),
        "40": ("GNSS_RESET_N", "hier"),
        "41": ("GNSS_PPS", "hier"),
        "42": ("GNSS_EXTINT", "hier"),
        "43": ("GND", "local"),
        "44": ("GND", "local"),
        **{str(pin): ("GND", "local") for pin in range(45, 61)},
    }
    return nets


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 3000
    s.refcounters["#FLG"] = 3000

    s.text(20, 12.7, "== Radio daughterboard connector and local logic supply ==")
    s.text(20, 20.32, "J1 pin 44 is the passive PRESENT_N strap: this board hard-connects it to GND.")
    s.place(
        "J1", "Conn_02x30_Odd_Even", "DF40C 60-pin radio daughterboard receptacle", 180, 185,
        footprint=FOOTPRINTS["Radio_DB_Daughter"], pin_nets=connector_pin_nets(),
        extra_props={
            "Manufacturer": "Hirose Electric", "MPN": "DF40C(2.0)-60DS-0.4V(51)",
            "MatingConnector": "DF40C-60DP-0.4V(51)", "StackHeight": "2.0mm",
        },
    )

    s.text(400, 50.8, "== RADIO_DB_3V3 local logic regulator ==")
    s.place(
        "U1", "AP2112K-3.3", "AP2112K-3.3 600mA daughterboard logic LDO", 500, 110,
        footprint=FOOTPRINTS["AP2112K-3.3"],
        pin_nets={
            "1": ("RADIO_DB_5V", "hier"), "2": ("GND", "local"),
            "3": ("RADIO_DB_5V", "hier"), "4": ("", "nc"),
            "5": ("RADIO_DB_3V3", "hier"),
        },
        extra_props={"Manufacturer": "Diodes Incorporated", "MPN": "AP2112K-3.3TRG1"},
    )
    for ref, value, net, y, fp in (
        ("C1", "10u 10V RADIO_DB_5V local bulk", "RADIO_DB_5V", 88.9, "C_10u"),
        ("C2", "1u AP2112 input local", "RADIO_DB_5V", 101.6, "C_1u"),
        ("C3", "1u AP2112 output local", "RADIO_DB_3V3", 114.3, "C_1u"),
        ("C4", "10u RADIO_DB_3V3 local bulk", "RADIO_DB_3V3", 127.0, "C_10u"),
        ("C5", "100n RADIO_DB_3V3 high-frequency", "RADIO_DB_3V3", 139.7, "C_100n"),
    ):
        s.place(ref, "C", value, 400, y, footprint=FOOTPRINTS[fp],
                pin_nets={"1": (net, "hier"), "2": ("GND", "local")})
    s.pwrflag(600, 101.6, "RADIO_DB_5V")
    s.pwrflag(620, 101.6, "GND")
    s.gnd(600, 127)
    s.text(400, 170.18, "RADIO_DB_5V feeds only the radio buck and local 3.3V regulator.")
    s.text(400, 177.8, "The PCM2902 radio codec is bus-powered from separately gated USB VBUS.")
    s.text(400, 185.42, "No daughterboard rail or signal is required for normal mainboard boot.")
    for ref, x, y in (
        ("H1", 420, 220),
        ("H2", 460, 220),
        ("H3", 500, 220),
        ("H4", 540, 220),
    ):
        s.place(
            ref,
            "MountingHole",
            "M2 daughterboard support hole",
            x,
            y,
            footprint=FOOTPRINTS["Radio_DB_M2_Hole"],
            pin_nets={},
            in_bom=False,
            extra_props={
                "MechanicalRole": "Required daughterboard support; do not rely on DF40 connector retention",
            },
        )
    return s
