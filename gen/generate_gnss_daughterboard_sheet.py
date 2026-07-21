from build_ducktop2 import Sheet, FOOTPRINTS


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 3100
    s.refcounters["#FLG"] = 3100

    s.text(20, 12.7, "== Optional daughterboard u-blox MAX-M10S GNSS ==")
    s.place(
        "U40", "MAX-M10S", "MAX-M10S GNSS", 300, 130,
        footprint=FOOTPRINTS["MAX-M10S"],
        pin_nets={
            "1": ("GND", "local"), "2": ("GNSS_UART_TX_LOCAL", "local"),
            "3": ("GNSS_UART_RX_LOCAL", "local"), "4": ("GNSS_PPS_LOCAL", "local"),
            "5": ("GNSS_EXTINT_LOCAL", "local"),
            "6": ("", "nc"), "7": ("RADIO_DB_3V3", "hier"),
            "8": ("RADIO_DB_3V3", "hier"), "9": ("GNSS_RESET_LOCAL_N", "local"),
            "10": ("GND", "local"), "11": ("GNSS_RF_IN", "local"), "12": ("GND", "local"),
            "13": ("", "nc"), "14": ("", "nc"), "15": ("", "nc"),
            "16": ("", "nc"), "17": ("", "nc"), "18": ("", "nc"),
        },
        extra_props={"Manufacturer": "u-blox", "MPN": "MAX-M10S-00B"},
    )
    s.place("J42", "Conn_Coaxial", "GNSS passive antenna U.FL", 470, 130,
            footprint=FOOTPRINTS["Conn_Coaxial_UFL"],
            pin_nets={"1": ("GNSS_RF_IN", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Hirose", "MPN": "U.FL-R-SMT-1(01)"})

    # All EC-to-GNSS signals terminate in an Ioff-capable buffer powered by the
    # removable board. They therefore cannot back-power the uninstalled or
    # switched-off GNSS domain.
    props = {
        "Manufacturer": "Texas Instruments", "MPN": "SN74LVC3G34DCUR",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc3g34.pdf",
        "PowerOffContract": "IOFF_OUTPUTS_HIGH_Z_WHEN_RADIO_DB_3V3_IS_OFF",
    }
    for unit, x, source, target in (
        (1, 20, "GNSS_UART_TX", "GNSS_UART_RX_LOCAL"),
        (2, 80, "GNSS_RESET_N", "GNSS_RESET_LOCAL_N"),
        (3, 140, "GNSS_EXTINT", "GNSS_EXTINT_LOCAL"),
    ):
        pins = {1: ("1", "7"), 2: ("6", "2"), 3: ("3", "5")}[unit]
        s.place("U41", "74LVC3G34", "SN74LVC3G34 GNSS input isolation", x, 88.9,
                unit=unit, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
                pin_nets={pins[0]: (source, "hier"), pins[1]: (target, "local")},
                extra_props=props)
    s.place("U41", "74LVC3G34", "SN74LVC3G34 GNSS input isolation", 200, 88.9,
            unit=4, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
            pin_nets={"4": ("GND", "local"), "8": ("RADIO_DB_3V3", "hier")},
            extra_props=props)
    s.place("C40", "C", "100n GNSS input-buffer local", 200, 106.68,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_DB_3V3", "hier"), "2": ("GND", "local")})
    s.place("R40", "R", "100k GNSS local reset pull-up", 20, 127,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_DB_3V3", "hier"), "2": ("GNSS_RESET_LOCAL_N", "local")})
    for ref, local, external, y in (
        ("R41", "GNSS_UART_TX_LOCAL", "GNSS_UART_RX", 152.4),
        ("R42", "GNSS_PPS_LOCAL", "GNSS_PPS", 165.1),
    ):
        s.place(ref, "R", "100R GNSS output series", 20, y, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (local, "local"), "2": (external, "hier")})
    for ref, value, y, fp in (
        ("C41", "10u GNSS local", 190.5, "C_10u"),
        ("C42", "100n GNSS local", 203.2, "C_100n"),
    ):
        s.place(ref, "C", value, 20, y, footprint=FOOTPRINTS[fp],
                pin_nets={"1": ("RADIO_DB_3V3", "hier"), "2": ("GND", "local")})
    s.place("J44", "Conn_01x06", "DNP MAX-M10S debug/program", 300, 220,
            footprint=FOOTPRINTS["Conn_01x06"],
            pin_nets={
                "1": ("RADIO_DB_3V3", "hier"), "2": ("GND", "local"),
                "3": ("GNSS_UART_RX_LOCAL", "local"), "4": ("GNSS_UART_TX_LOCAL", "local"),
                "5": ("GNSS_PPS_LOCAL", "local"), "6": ("GNSS_RESET_LOCAL_N", "local"),
            }, on_board=False)
    s.gnd(470, 250)
    s.text(20, 266.7, "J42 is passive-antenna-only; active bias requires a complete supervised bias network.")
    s.text(20, 274.32, "GNSS signals are nonessential. Removing this board cannot hold any mainboard reset, power, or USB rail.")
    s.text(20, 281.94, "MAX-M10S V_BCKP is intentionally open: this revision has no independent backup supply.")
    return s
