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

    # Remove locally powered interfaces from the Mu pins while the host is off.
    # TPS22975N does not specify reverse-current blocking, so the downstream rails
    # must not be externally driven while SYS_5V/SYS_3V3 are absent.
    # MU_HOST_ACTIVE is already fail-low in the Mu carrier power sequencing.
    for ref, source, output, ct, y in (
        ("U54", "SYS_5V", "HDMI_SOURCE_5V", "HDMI_5V_SWITCH_CT", 38.1),
        ("U55", "SYS_3V3", "HDMI_HOST_3V3", "HDMI_3V3_SWITCH_CT", 101.6),
    ):
        source_kind = "hier"
        s.place(
            ref, "TPS22975N", f"TPS22975NDSGR host-active {source} switch", 405, y,
            footprint=FOOTPRINTS["TPS22975N"],
            pin_nets={
                "1": (source, source_kind), "2": (source, source_kind),
                "3": ("MU_HOST_ACTIVE", "hier"), "4": (source, source_kind),
                "5": ("GND", "local"), "6": (ct, "local"),
                "7": (output, "local"), "8": (output, "local"),
                "9": ("GND", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS22975NDSGR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps22975.pdf",
                "PowerOffContract": "OUTPUT_OFF_WHEN_MU_HOST_ACTIVE_LOW; NO_REVERSE_BLOCK_GUARANTEE",
            },
        )
    s.place("C164", "C", "4.7n HDMI 5V switch rise-time", 455, 38.1,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("HDMI_5V_SWITCH_CT", "local"), "2": ("GND", "local")})
    s.place("C165", "C", "4.7n HDMI 3V3 switch rise-time", 455, 101.6,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("HDMI_3V3_SWITCH_CT", "local"), "2": ("GND", "local")})
    s.place("R168", "R", "100k HDMI switched 5V discharge", 455, 50.8,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("HDMI_SOURCE_5V", "local"), "2": ("GND", "local")})
    s.place("R169", "R", "100k HDMI switched 3V3 discharge", 455, 114.3,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": ("HDMI_HOST_3V3", "local"), "2": ("GND", "local")})

    # TPD13S523 supplies a current-limited, reverse-blocking HDMI 5 V output
    # and clamps the three connector-side control lines. Its legacy TMDS
    # clamps remain unused; the 0.15-pF-max TI shunts stay at J30.
    s.place(
        "U50", "TPD13S523PWR", "TPD13S523PWR HDMI control ESD / 5V switch", 500, 63.5,
        footprint=FOOTPRINTS["TPD13S523PWR"],
        pin_nets={
            "1": ("EXT_HDMI_SCL_CONN", "local"),
            "2": ("EXT_HDMI_SDA_CONN", "local"),
            "3": ("EXT_HDMI_HPD_CONN", "local"),
            "4": ("HDMI_TPD_D0_UNUSED", "local"),
            "5": ("HDMI_SOURCE_5V", "local"),
            "6": ("EXT_HDMI_5V", "local"),
            "7": ("HDMI_TPD_D1_UNUSED", "local"),
            "8": ("GND", "local"),
            "9": ("HDMI_TPD_D2_UNUSED", "local"),
            "10": ("HDMI_TPD_D3_UNUSED", "local"),
            "11": ("HDMI_TPD_D4_UNUSED", "local"),
            "12": ("HDMI_TPD_D5_UNUSED", "local"),
            "13": ("HDMI_TPD_D6_UNUSED", "local"),
            "14": ("HDMI_TPD_D7_UNUSED", "local"),
            "15": ("HDMI_TPD_D8_UNUSED", "local"),
            "16": ("HDMI_TPD_D9_UNUSED", "local"),
        },
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPD13S523PWR"},
    )
    s.place(
        "C158", "C", "1u 10V X7R HDMI 5V switch input", 570, 58.42,
        footprint=FOOTPRINTS["C_1u"],
        pin_nets={"1": ("HDMI_SOURCE_5V", "local"), "2": ("GND", "local")},
        extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A105KA61D"},
    )
    s.place(
        "C159", "C", "1u 10V X7R HDMI 5V switch output", 570, 68.58,
        footprint=FOOTPRINTS["C_1u"],
        pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("GND", "local")},
        extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A105KA61D"},
    )
    s.place(
        "C162", "C", "100n 10V X7R HDMI 5V switch input HF", 620, 58.42,
        footprint=FOOTPRINTS["C_0402"],
        pin_nets={"1": ("HDMI_SOURCE_5V", "local"), "2": ("GND", "local")},
        extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A104KA01D"},
    )
    s.place(
        "C163", "C", "100n 10V X7R HDMI 5V switch output HF", 620, 68.58,
        footprint=FOOTPRINTS["C_0402"],
        pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("GND", "local")},
        extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A104KA01D"},
    )
    for offset, pin in enumerate(("4", "7", "9", "10", "11", "12", "13", "14", "15", "16")):
        s.place(
            f"R{570 + offset}", "R", "75R 1% unused TPD13S523 channel termination",
            700 + (offset % 2) * 45, 55.88 + (offset // 2) * 12.7,
            footprint=FOOTPRINTS["R_0402"],
            pin_nets={"1": (f"HDMI_TPD_D{offset}_UNUSED", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-0775RL"},
        )

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
    s.text(20, 251.46, "CEC and utility are explicitly NC; unused TPD13S523 legacy channels use the datasheet 75R-to-GND termination.")
    s.text(20, 259.08, "U54/U55 remove 5V/DDC/HPD power while the Mu is off; PCA9306 translates DDC/SCDC and U53 buffers HPD.")
    s.text(20, 266.7, "LAYOUT: HDMI TMDS pairs are 100-ohm differential. Match pair skew to under 10 mil per Mu HDMI guide (current ~495 mil).")
    s.text(20, 274.32, "LAYOUT: PCIe Gen3 pairs are 85-ohm differential. Match data-pair skew under 5 mil and refclock under 5 mil per Mu PCIe guide.")
    s.text(20, 281.94, "Release gate: verify >=4.8V at J30 pin 18 under 55mA and validate the finished HDMI 2.0 layout on hardware.")

    return s
