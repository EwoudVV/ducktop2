from build_ducktop2 import Sheet, FOOTPRINTS


# LattePanda Mu TCP0 default-HDMI lane assignment from the Mu carrier reference.
HDMI_LINES = [
    ("TCP0_TX0_P", "EXT_HDMI_D2_P"),
    ("TCP0_TX0_N", "EXT_HDMI_D2_N"),
    ("TCP0_TXRX0_P", "EXT_HDMI_D1_P"),
    ("TCP0_TXRX0_N", "EXT_HDMI_D1_N"),
    ("TCP0_TX1_P", "EXT_HDMI_D0_P"),
    ("TCP0_TX1_N", "EXT_HDMI_D0_N"),
    ("TCP0_TXRX1_P", "EXT_HDMI_CK_P"),
    ("TCP0_TXRX1_N", "EXT_HDMI_CK_N"),
]


def hdmi_connector_nets():
    return {
        "1": ("EXT_HDMI_D2_P", "local"),
        "2": ("GND", "local"),
        "3": ("EXT_HDMI_D2_N", "local"),
        "4": ("EXT_HDMI_D1_P", "local"),
        "5": ("GND", "local"),
        "6": ("EXT_HDMI_D1_N", "local"),
        "7": ("EXT_HDMI_D0_P", "local"),
        "8": ("GND", "local"),
        "9": ("EXT_HDMI_D0_N", "local"),
        "10": ("EXT_HDMI_CK_P", "local"),
        "11": ("GND", "local"),
        "12": ("EXT_HDMI_CK_N", "local"),
        "13": ("", "nc"),
        "14": ("", "nc"),
        "15": ("EXT_HDMI_SCL_CONN", "local"),
        "16": ("EXT_HDMI_SDA_CONN", "local"),
        "17": ("GND", "local"),
        "18": ("EXT_HDMI_5V", "local"),
        "19": ("EXT_HDMI_HPD_CONN", "local"),
        "SH": ("GND", "local"),
    }


def tmds_esd(s, ref, x, y, net):
    s.place(
        ref, "D_TVS", "TPD1E0B04DPLR HDMI TMDS ESD (0.15pF max)", x, y,
        footprint=FOOTPRINTS["TPD1E0B04DPL"],
        pin_nets={"1": (net, "local"), "2": ("GND", "local")},
        extra_props={
            "Manufacturer": "Texas Instruments", "MPN": "TPD1E0B04DPLR",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tpd1e0b04.pdf",
        },
    )


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 80
    s.refcounters["#FLG"] = 80

    s.text(20, 12.7, "== TCP0 external HDMI 2.0 output ==")
    s.text(20, 20.32, "LattePanda Mu default BIOS maps TCP0 as HDMI 2.0; the internal panel uses the Mu module's onboard eDP connector.")
    s.text(20, 27.94, "Lane map, AC coupling, bias gating, DDC/HPD translation, and 5V isolation follow the Mu reference.")

    s.text(20, 50.8, "== J30 external HDMI-A connector ==")
    s.place(
        "J30", "HDMI_A", "External HDMI-A from TCP0", 115, 125,
        footprint=FOOTPRINTS["HDMI_A"], pin_nets=hdmi_connector_nets(),
        extra_props={"Manufacturer": "Molex", "MPN": "208658-1001"},
    )

    # Mu HDMI transmitters need series AC coupling and a 470R pull-down return
    # that is connected only while the module reports the S0 power state.
    for i, (source, conn) in enumerate(HDMI_LINES):
        x = 250 + (i % 4) * 55
        y = 82.55 + (i // 4) * 25.4
        s.place(
            f"C{150 + i}", "C", "100n 16V HDMI AC coupling", x, y,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": (source, "hier"), "2": (conn, "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71C104KA88D"},
        )
        s.place(
            f"R{150 + i}", "R", "470R 1% HDMI bias", x, y + 10.16,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": (conn, "local"), "2": ("EXT_HDMI_BIAS_RETURN", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-07470RL"},
        )
        tmds_esd(s, f"D{150 + i}", x, y + 20.32, conn)

    s.place(
        "Q50", "Q_NMOS_SOT23_GSD", "BSS138 HDMI bias gate", 475, 180,
        footprint=FOOTPRINTS["Q_BSS138"],
        pin_nets={"1": ("EXT_HDMI_BIAS_GATE", "local"), "2": ("GND", "local"),
                  "3": ("EXT_HDMI_BIAS_RETURN", "local")},
        extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"},
    )
    s.place(
        "R165", "R", "2.2k S0 bias-gate series", 530, 177.8,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("MU_HOST_ACTIVE", "hier"), "2": ("EXT_HDMI_BIAS_GATE", "local")},
    )
    s.place(
        "R166", "R", "100k bias-gate default off", 530, 190.5,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("EXT_HDMI_BIAS_GATE", "local"), "2": ("GND", "local")},
    )
    s.place(
        "R167", "R", "0R DNP HDMI bias always-on option", 600, 180,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("EXT_HDMI_BIAS_RETURN", "local"), "2": ("GND", "local")},
        dnp=True,
    )

    # The HDMI power branch uses its own current-limited, reverse-blocking switch.
    s.place("U54", "TPS22948", "TPS22948DCKR HDMI 5V current-limited switch", 405, 38.1,
            footprint=FOOTPRINTS["TPS22948"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local"),
                      "3": ("MU_HOST_ACTIVE", "hier"), "4": ("", "nc"),
                      "5": ("", "nc"), "6": ("EXT_HDMI_5V", "local")},
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS22948DCKR",
                         "Datasheet": "https://www.ti.com/lit/ds/symlink/tps22948.pdf",
                         "PowerOffContract": "OUTPUT_OFF_WHEN_MU_HOST_ACTIVE_LOW; ALWAYS_ON_REVERSE_BLOCKING"})
    s.place("R570", "R", "100k HDMI enable pulldown", 365, 50.8,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("MU_HOST_ACTIVE", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-07100KL"})
    s.place("C164", "C", "18n 50V X7R TPS22948 output", 455, 38.1,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "CC0402KRX7R9BB183",
                         "Datasheet": "https://yageogroup.com/download/specsheet/CC0402KRX7R9BB183"})

    # Keep the DDC/HPD host-side 3V3 rail off when the Mu is off.
    s.place("U55", "TPS22975N", "TPS22975NDSGR host-active SYS_3V3 switch", 405, 101.6,
            footprint=FOOTPRINTS["TPS22975N"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("SYS_3V3", "hier"),
                      "3": ("MU_HOST_ACTIVE", "hier"), "4": ("SYS_3V3", "hier"),
                      "5": ("GND", "local"), "6": ("HDMI_3V3_SWITCH_CT", "local"),
                      "7": ("HDMI_HOST_3V3", "local"), "8": ("HDMI_HOST_3V3", "local"),
                      "9": ("GND", "local")},
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS22975NDSGR",
                         "Datasheet": "https://www.ti.com/lit/ds/symlink/tps22975.pdf",
                         "PowerOffContract": "OUTPUT_OFF_WHEN_MU_HOST_ACTIVE_LOW; NO_REVERSE_BLOCK_GUARANTEE"})
    s.place("C165", "C", "4.7n HDMI 3V3 switch rise-time", 455, 101.6,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("HDMI_3V3_SWITCH_CT", "local"), "2": ("GND", "local")})
    s.place("R168", "R", "100k HDMI switched 5V discharge", 455, 50.8,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("GND", "local")})
    s.place("R169", "R", "100k HDMI switched 3V3 discharge", 455, 114.3,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("HDMI_HOST_3V3", "local"), "2": ("GND", "local")})

    s.place("U50", "TPD4E05U06DQA", "TPD4E05U06DQAR HDMI control and 5V ESD", 500, 63.5,
            footprint=FOOTPRINTS["TPD4E05U06DQA"],
            pin_nets={"1": ("EXT_HDMI_SCL_CONN", "local"), "2": ("EXT_HDMI_SDA_CONN", "local"),
                      "3": ("GND", "local"), "4": ("EXT_HDMI_HPD_CONN", "local"),
                      "5": ("EXT_HDMI_5V", "local"), "6": ("", "nc"), "7": ("", "nc"),
                      "8": ("GND", "local"), "9": ("", "nc"), "10": ("", "nc")},
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPD4E05U06DQAR",
                         "Datasheet": "https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf"})
    s.place("C158", "C", "1u 10V X7R HDMI switch input", 570, 58.42,
            footprint="Capacitor_SMD:C_0603_1608Metric",
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A105KA61D"})
    s.place("C162", "C", "100n 10V X7R HDMI switch input HF", 620, 58.42,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A104KA01D"})

    # PCA9306 provides a characterized bidirectional DDC/SCDC translation
    # path. VREF2 and EN share the application-circuit bias node.
    s.place(
        "U51", "PCA9306DCTR", "PCA9306DCTR HDMI DDC level translator", 500, 119.38,
        footprint=FOOTPRINTS["PCA9306DCTR"],
        pin_nets={
            "1": ("GND", "local"), "2": ("HDMI_HOST_3V3", "local"),
            "3": ("TCP0_DDC_SCL", "hier"), "4": ("TCP0_DDC_SDA", "hier"),
            "5": ("EXT_HDMI_SDA_CONN", "local"), "6": ("EXT_HDMI_SCL_CONN", "local"),
            "7": ("HDMI_DDC_REF5", "local"), "8": ("HDMI_DDC_REF5", "local"),
        },
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "PCA9306DCTR"},
    )
    for ref, rail, net, y in [
        ("R158", "HDMI_HOST_3V3", "TCP0_DDC_SCL", 96.52),
        ("R159", "HDMI_HOST_3V3", "TCP0_DDC_SDA", 109.22),
        ("R160", "EXT_HDMI_5V", "EXT_HDMI_SCL_CONN", 121.92),
        ("R161", "EXT_HDMI_5V", "EXT_HDMI_SDA_CONN", 134.62),
    ]:
        value = "2.2k HDMI DDC pull-up" if rail == "HDMI_HOST_3V3" else "1.8k HDMI DDC pull-up"
        s.place(
            ref, "R", value, 575, y,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": (rail, "local"),
                      "2": (net, "hier" if net.startswith("TCP0_") else "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-072K2L" if rail == "HDMI_HOST_3V3" else "RC0402FR-071K8L"},
        )
    s.place("R162", "R", "200k PCA9306 VREF2/EN bias", 650, 96.52,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("HDMI_DDC_REF5", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-07200KL"})
    s.place("C160", "C", "100p PCA9306 VREF2/EN filter", 650, 106.68,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("HDMI_DDC_REF5", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM1555C1H101JA01D"})

    # A 5.5-V-tolerant Schmitt buffer translates connector HPD to Mu 3.3 V.
    s.place(
        "U53", "74LVC1G17", "SN74LVC1G17DBVR HDMI HPD buffer", 500, 157.48,
        footprint=FOOTPRINTS["SN74LVC1G17DBV"],
        pin_nets={"1": ("", "nc"), "2": ("EXT_HDMI_HPD_NODE", "local"),
                  "3": ("GND", "local"), "4": ("TCP0_HPD", "hier"),
                  "5": ("HDMI_HOST_3V3", "local")},
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G17DBVR"},
    )
    s.place("R163", "R", "1k HPD input series", 650, 119.38, footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("EXT_HDMI_HPD_CONN", "local"), "2": ("EXT_HDMI_HPD_NODE", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-071KL"})
    s.place("R164", "R", "100k HPD input pull-down", 650, 132.08, footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("EXT_HDMI_HPD_NODE", "local"), "2": ("GND", "local")})
    s.place("C161", "C", "100n HPD buffer local", 650, 144.78,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("HDMI_HOST_3V3", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A104KA01D"})
    s.gnd(705, 190.5)

    s.text(20, 228.6, "NOTES:")
    s.text(20, 236.22, "J30 is the outside-world HDMI jack. The retired Intehill controller is a bench-test/fallback fixture, not motherboard circuitry.")
    s.text(20, 243.84, "TMDS ESD uses 0.15pF-max, +/-3.6V TPD1E0B04DPLR single-line parts; route each shunt at J30 with no stub.")
    s.text(20, 251.46, "CEC and utility are NC. TPS22948 supplies current-limited, reverse-blocking 5V; TPD4E05U06 protects DDC, HPD, and 5V.")
    s.text(20, 259.08, "U54/U55 remove 5V/DDC/HPD power while the Mu is off; PCA9306 translates DDC/SCDC and U53 buffers HPD.")
    s.text(20, 266.7, "LAYOUT: validate 100-ohm differential impedance against the actual stackup. Match each routed TMDS pair to less than 0.127 mm (5 mil) skew per the Mu HDMI guide.")
    s.text(20, 274.32, "LAYOUT: PCIe Gen3 pairs are 85-ohm differential. Match data-pair skew under 5 mil and refclock under 5 mil per Mu PCIe guide.")
    s.text(20, 281.94, "Release gate: verify >=4.8V at J30 pin 18 under 55mA and validate the finished HDMI 2.0 layout on hardware.")

    return s
