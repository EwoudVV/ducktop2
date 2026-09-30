"""Standby feeds, fast voltage protection and controlled capacitor charging."""

from build_ducktop2 import FOOTPRINTS


def add_aon_input(s):
    hier = {"VSYS", "PD1_VBUS_RAW", "PD2_VBUS_RAW", "EC_AON_IN", "AON_FAULT_N"}

    def n(name):
        return (name, "hier" if name in hier else "local")

    def part(ref, symbol, value, x, y, fp, pins, mpn, maker):
        s.place(
            ref,
            symbol,
            value,
            x,
            y,
            footprint=fp,
            pin_nets={str(p): n(net) if net else ("", "nc") for p, net in pins.items()},
            extra_props={"Manufacturer": maker, "MPN": mpn},
        )

    def cap(
        ref, value, x, y, a, b, mpn="GRM188R71H104KA93D", fp="C_100n", maker="Murata"
    ):
        part(
            ref,
            "C_Polarized" if ref == "C797" else "C",
            value,
            x,
            y,
            FOOTPRINTS[fp],
            {1: a, 2: b},
            mpn,
            maker,
        )

    def resistor(ref, value, x, y, a, b, mpn, maker="Yageo", fp=None):
        part(ref, "R", value, x, y, fp or FOOTPRINTS["R"], {1: a, 2: b}, mpn, maker)

    def mosfet(ref, x, y, source, gate, drain):
        part(
            ref,
            "Q_NMOS_123S_4G_5678D",
            "CSD19537Q3 100V",
            x,
            y,
            FOOTPRINTS["Q_CSD19537Q3"],
            {1: source, 2: source, 3: source, 4: gate, 5: drain},
            "CSD19537Q3",
            "Texas Instruments",
        )

    s.text(650, 290, "== always-on supply: low-loss USB feeds and shared protection ==")
    part(
        "D711",
        "D_Schottky",
        "SS310 3A 100V AUX standby feed",
        650,
        335,
        FOOTPRINTS["D_Schottky_SMA"],
        {1: "AON_RAW", 2: "AUX_DC_FUSED"},
        "SS310-13-F",
        "Diodes Incorporated",
    )
    for index, source in enumerate(("PD1_VBUS_RAW", "PD2_VBUS_RAW")):
        y = 440 + 75 * index
        stem = f"AON_PD{index+1}"
        part(
            f"U{2620+index}",
            "LM74700",
            "LM74700QDBVRQ1",
            660,
            y,
            "Package_TO_SOT_SMD:SOT-23-6",
            {
                1: stem + "_VCAP",
                2: "GND",
                3: source,
                4: "AON_RAW",
                5: stem + "_GATE",
                6: source,
            },
            "LM74700QDBVRQ1",
            "Texas Instruments",
        )
        mosfet(f"Q{2620+index}", 745, y, source, stem + "_GATE", "AON_RAW")
        cap(f"C{2620+index}", "100n 50V charge pump", 810, y, stem + "_VCAP", source)

    part(
        "U718",
        "LTC4368-2",
        "LTC4368IMS-2#PBF standby breaker",
        705,
        335,
        FOOTPRINTS["LTC4368-1"],
        {
            1: "AON_RAW",
            2: "AON_EFUSE_UV",
            3: "AON_EFUSE_OV",
            4: "AON_RETRY",
            5: "GND",
            6: "AON_PROTECT_SHDN",
            7: "AON_FAULT_N",
            8: "AON_PROTECTED",
            9: "AON_PROTECT_SENSE",
            10: "AON_GATE_DRV",
        },
        "LTC4368IMS-2#PBF",
        "Analog Devices",
    )
    for ref, value, a, b, mpn, x, y in (
        (
            "R795",
            "56.2k 0.02% 5ppm AON UV top",
            "AON_RAW",
            "AON_EFUSE_UV",
            "TNPU060356K2HZEN00",
            755,
            315,
        ),
        (
            "R796",
            "8.25k 0.02% 5ppm AON UV bottom",
            "AON_EFUSE_UV",
            "GND",
            "TNPU06038K25HZEN00",
            755,
            330,
        ),
        (
            "R797",
            "100k 0.02% 5ppm AON OV top",
            "AON_RAW",
            "AON_EFUSE_OV",
            "TNPU0603100KHZEN00",
            755,
            345,
        ),
        (
            "R798",
            "2.15k 0.02% 5ppm AON OV bottom",
            "AON_EFUSE_OV",
            "GND",
            "TNPU06032K15HZEN00",
            755,
            360,
        ),
    ):
        resistor(ref, value, x, y, a, b, mpn, "Vishay")
    resistor(
        "R799",
        "100k standby enable pull-up",
        755,
        380,
        "AON_RAW",
        "AON_PROTECT_SHDN",
        "RC0603FR-07100KL",
    )
    mosfet("Q2622", 660, 595, "AON_FET_COMMON", "AON_FET_GATE", "AON_RAW")
    mosfet("Q2623", 745, 595, "AON_FET_COMMON", "AON_FET_GATE", "AON_PROTECT_SENSE")
    part(
        "RS2620",
        "R",
        "22m 1% 2W AON Kelvin shunt",
        810,
        590,
        "Resistor_SMD:R_2512_6332Metric",
        {1: "AON_PROTECT_SENSE", 2: "AON_PROTECTED"},
        "WSL2512R0220FEA18",
        "Vishay Dale",
    )
    resistor(
        "R2620",
        "10k gate ramp resistor",
        650,
        630,
        "AON_GATE_DRV",
        "AON_FET_GATE",
        "RC0603FR-0710KL",
    )
    part(
        "D2620",
        "D_Schottky",
        "BAT54WS fast gate discharge",
        745,
        630,
        FOOTPRINTS["D_Signal"],
        {1: "AON_GATE_DRV", 2: "AON_FET_GATE"},
        "BAT54WS-7-F",
        "Diodes Incorporated",
    )
    cap(
        "C799",
        "22n 50V C0G gate ramp",
        810,
        630,
        "AON_FET_GATE",
        "AON_PROTECTED",
        "C0805C223J5GACTU",
        "C_0805",
        "KEMET",
    )
    cap(
        "C2622",
        "22n 50V C0G retry timer",
        650,
        650,
        "AON_RETRY",
        "GND",
        "C0805C223J5GACTU",
        "C_0805",
        "KEMET",
    )
    cap("C795", "1u 50V AON input", 805, 315, "AON_RAW", "GND", "GRT188R61H105ME13D")
    cap("C796", "100n 50V AON input local", 805, 335, "AON_RAW", "GND")
    cap(
        "C797",
        "100u 35V hybrid AON hold-up",
        805,
        355,
        "EC_AON_IN",
        "GND",
        "EEHZK1V101XP",
        "C_100u_35V_hybrid",
        "Panasonic",
    )
    cap("C798", "100n 50V AON output local", 805, 375, "EC_AON_IN", "GND")
    s.pwrflag(650, 370, "AON_RAW")
    s.pwrflag(650, 390, "EC_AON_IN")
    s.text(
        650,
        685,
        "U718 provides fast voltage protection. U2660 controls inrush and latches a sustained overcurrent. Both start without the EC.",
    )

    # VSYS starts through the battery FET body diode and is regulated by the
    # NVDC charger on external power. This feed includes standby in RS2601's
    # discharge measurement and avoids a direct battery-current bypass.
    part(
        "U2650",
        "LM74700",
        "LM74700QDBVRQ1 system standby feed",
        660,
        730,
        "Package_TO_SOT_SMD:SOT-23-6",
        {
            1: "AON_SYS_VCAP",
            2: "GND",
            3: "VSYS",
            4: "AON_RAW",
            5: "AON_SYS_GATE",
            6: "VSYS",
        },
        "LM74700QDBVRQ1",
        "Texas Instruments",
    )
    mosfet("Q2650", 745, 730, "VSYS", "AON_SYS_GATE", "AON_RAW")
    cap("C2650", "100n 50V charge pump", 810, 730, "AON_SYS_VCAP", "VSYS")
    cap(
        "C2651",
        "1u 50V protected input bypass",
        650,
        770,
        "AON_PROTECTED",
        "GND",
        "GRT188R61H105ME13D",
    )
    s.pwrflag(745, 770, "AON_PROTECTED")
    s.text(
        650,
        815,
        "Raw USB/AUX can start the EC before source selection. VSYS supplies standby from the adapter or protected pack.",
    )

    s.text(850, 810, "== U2660 standby current limit and service reset ==")
    part(
        "U2660",
        "LTC4231-1",
        "LTC4231IMS-1#PBF standby current limiter",
        930,
        860,
        "Package_SO:MSOP-12_3x4.039mm_P0.65mm",
        {
            1: "AON_LIMIT_SENSE",
            2: "AON_PROTECTED",
            3: "AON_LIMIT_SHDN",
            4: "AON_PROTECTED",
            5: "AON_PROTECTED",
            6: "GND",
            7: "",
            8: "GND",
            9: "AON_FAULT_N",
            10: "AON_LIMIT_TIMER",
            11: "EC_AON_IN",
            12: "AON_LIMIT_DRV",
        },
        "LTC4231IMS-1#PBF",
        "Analog Devices",
    )
    for ref, y in (("RS2660", 910), ("R2662", 935)):
        part(
            ref,
            "R",
            "180m 1% 0.25W parallel AON shunt",
            850,
            y,
            "Resistor_SMD:R_1206_3216Metric",
            {1: "AON_PROTECTED", 2: "AON_LIMIT_SENSE"},
            "WSL1206R1800FEA",
            "Vishay Dale",
        )
    part(
        "Q2660",
        "Q_NMOS_123S_4G_5678D",
        "CSD18540Q5B AON pass FET",
        1010,
        910,
        FOOTPRINTS["Q_CSD18540Q5B"],
        {
            1: "EC_AON_IN",
            2: "EC_AON_IN",
            3: "EC_AON_IN",
            4: "AON_LIMIT_GATE",
            5: "AON_LIMIT_SENSE",
        },
        "CSD18540Q5B",
        "Texas Instruments",
    )
    resistor(
        "R2661",
        "10R gate damping",
        1090,
        910,
        "AON_LIMIT_DRV",
        "AON_LIMIT_GATE",
        "RC0402FR-0710RL",
        fp="Resistor_SMD:R_0402_1005Metric",
    )
    resistor(
        "R2664",
        "1k gate-ramp branch",
        1090,
        935,
        "AON_LIMIT_DRV",
        "AON_LIMIT_RAMP",
        "RC0603FR-071KL",
    )
    cap(
        "C2660",
        "22n 50V C0G gate ramp",
        1190,
        935,
        "AON_LIMIT_RAMP",
        "GND",
        "C0805C223J5GACTU",
        "C_0805",
        "KEMET",
    )
    cap(
        "C2661",
        "1u 50V fault timer",
        1010,
        960,
        "AON_LIMIT_TIMER",
        "GND",
        "GRT188R61H105ME13D",
    )
    cap(
        "C2662",
        "1u 50V fault timer",
        1010,
        985,
        "AON_LIMIT_TIMER",
        "GND",
        "GRT188R61H105ME13D",
    )
    resistor(
        "R2663",
        "100k always-on enable",
        1090,
        960,
        "AON_PROTECTED",
        "AON_LIMIT_SHDN",
        "RC0603FR-07100KL",
    )
    for ref, x, net in [("TP2660", 1190, "AON_LIMIT_SHDN"), ("TP2661", 1270, "GND")]:
        s.place(
            ref,
            "TestPoint",
            "AON reset" if ref == "TP2660" else "GND",
            x,
            995,
            footprint="TestPoint:TestPoint_Pad_D1.5mm",
            in_bom=False,
            pin_nets={"1": n(net)},
        )
    s.text(
        850,
        1030,
        "The combined sense resistance is 90mOhm. Kelvin-route IN and SENSE to the resistor pair; no load copper in the pickups.",
    )
    s.text(
        850,
        1040,
        "U718 supplies the fast UV/OV protection. U2660 UV/OV inputs are disabled; its current limiter and timer remain active.",
    )
    s.text(
        850,
        1050,
        "After fixing a standby short, remove all power or momentarily short TP2660 to TP2661 to reset the latch. This also restarts the EC.",
    )
