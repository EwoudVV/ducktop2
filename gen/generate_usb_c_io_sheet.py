from build_ducktop2 import FOOTPRINTS, Sheet


def props(manufacturer, mpn, datasheet="", **extra):
    result = {"Manufacturer": manufacturer, "MPN": mpn}
    if datasheet:
        result["Datasheet"] = datasheet
    result.update(extra)
    return result


def resistor(s, ref, value, x, y, a, b, *, a_kind="local", b_kind="local", mpn="RC0603FR-0710KL"):
    s.place(ref, "R", value, x, y, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (a, a_kind), "2": (b, b_kind)},
            extra_props=props("Yageo", mpn))


def capacitor(s, ref, value, x, y, net, *, kind="local", footprint="C_100n", mpn="GRM188R71H104KA93D"):
    s.place(ref, "C", value, x, y, footprint=FOOTPRINTS[footprint],
            pin_nets={"1": (net, kind), "2": ("GND", "local")},
            extra_props=props("Murata", mpn))


def ss_esd(s, base, x, y, nets):
    for index, net in enumerate(nets):
        s.place(f"D{base + index}", "TPD1E0B04", "TPD1E0B04DPLR 0.13pF USB3 ESD",
                x, y + index * 7.62, footprint=FOOTPRINTS["TPD1E0B04DPL"],
                pin_nets={"1": (net, "local"), "2": ("GND", "local")},
                extra_props=props(
                    "Texas Instruments", "TPD1E0B04DPLR",
                    "https://www.ti.com/lit/ds/symlink/tpd1e0b04.pdf",
                ))


def usb2_cc_esd(s, ref, x, y, dp, dm, cc1, cc2):
    s.place(ref, "TPD4E05U06DQA", "TPD4E05U06 USB2/CC ESD", x, y,
            footprint=FOOTPRINTS["TPD4E05U06DQA"],
            pin_nets={
                "1": (dp, "local"), "2": (dm, "local"), "3": ("GND", "local"),
                "4": (cc1, "local"), "5": (cc2, "local"),
                "6": ("", "nc"), "7": ("", "nc"), "8": ("GND", "local"),
                "9": ("", "nc"), "10": ("", "nc"),
            }, extra_props=props("Texas Instruments", "TPD4E05U06DQAR"))


def add_hub_supplies(s):
    s.text(20, 45.72, "== Dedicated 6A-class port rail and 1.15V hub-core rail ==")
    s.place("U1703", "TPS56637", "TPS56637RPAR VSYS to USB_PORT_5V 5.21V", 63.5, 73.66,
            footprint=FOOTPRINTS["TPS56637"], pin_nets={
                "1": ("USB5_EN", "local"), "2": ("USB5_FB", "local"),
                "3": ("GND", "local"), "4": ("USB5_PG", "local"), "5": ("", "nc"),
                "6": ("USB5_SW", "local"), "7": ("USB5_BOOT", "local"),
                "8": ("VSYS", "hier"), "9": ("GND", "local"), "10": ("GND", "local"),
            }, extra_props=props("Texas Instruments", "TPS56637RPAR"))
    s.place("L1701", "L", "3.3uH >=9A USB port buck", 121.92, 73.66,
            footprint=FOOTPRINTS["L_XAL7070"],
            pin_nets={"1": ("USB5_SW", "local"), "2": ("USB_PORT_5V", "hier")},
            extra_props=props("Coilcraft", "XAL7070-332MEC"))
    resistor(s, "R1710", "169k 1% USB5 EN top", 38.1, 106.68, "VSYS", "USB5_EN", a_kind="hier", mpn="RC0603FR-07169KL")
    resistor(s, "R1711", "36.1k 1% USB5 EN bottom", 63.5, 106.68, "USB5_EN", "GND", mpn="RC0603FR-0736K1L")
    resistor(s, "R1712", "76.8k 1% USB5 FB top", 101.6, 106.68, "USB_PORT_5V", "USB5_FB", a_kind="hier", mpn="RC0603FR-0776K8L")
    resistor(s, "R1713", "10.0k 1% USB5 FB bottom", 127, 106.68, "USB5_FB", "GND", mpn="RC0603FR-0710KL")
    resistor(s, "R1714", "100k USB5 PG pull-up", 152.4, 106.68, "SYS_3V3", "USB5_PG", a_kind="hier", mpn="RC0603FR-07100KL")
    s.place("C1710", "C", "100n USB5 bootstrap", 101.6, 91.44,
            footprint=FOOTPRINTS["C_100n"], pin_nets={"1": ("USB5_BOOT", "local"), "2": ("USB5_SW", "local")},
            extra_props=props("Murata", "GRM188R71H104KA93D"))
    for ref, x in (("C1711", 20.32), ("C1712", 33.02)):
        capacitor(s, ref, "10u 50V USB5 input", x, 121.92, "VSYS", kind="hier", footprint="C_10u", mpn="CGA5L1X7R1H106K160AC")
    capacitor(s, "C1713", "100n 50V USB5 input HF", 45.72, 121.92, "VSYS", kind="hier")
    for ref, x in (("C1714", 101.6), ("C1715", 114.3)):
        capacitor(s, ref, "22u 10V USB5 output", x, 121.92, "USB_PORT_5V", kind="hier", footprint="C_1210", mpn="GRM32ER71A226KE20L")

    s.place("U1701", "TPS62823DLC", "TPS62823DLC 3A USB7206C 1.146V core buck", 205.74, 73.66,
            footprint=FOOTPRINTS["TPS62823DLC"], pin_nets={
                "1": ("SYS_3V3", "hier"), "2": ("HUB_CORE_FB", "local"),
                "3": ("GND", "local"), "4": ("", "nc"), "5": ("GND", "local"),
                "6": ("HUB_CORE_SW", "local"), "7": ("SYS_3V3", "hier"),
                "8": ("HUB_CORE_PG", "local"),
            }, extra_props=props("Texas Instruments", "TPS62823DLC"))
    s.place("L1700", "L", "470nH >=3.9A USB hub core", 251.46, 73.66,
            footprint=FOOTPRINTS["L_TFM201610"],
            pin_nets={"1": ("HUB_CORE_SW", "local"), "2": ("HUB_VCORE", "local")},
            extra_props=props("TDK", "TFM201610ALMA-R47MTAA"))
    resistor(s, "R1705", "91.0k 1% core FB top", 215.9, 106.68, "HUB_VCORE", "HUB_CORE_FB", mpn="RC0603FR-0791KL")
    resistor(s, "R1706", "100k 1% core FB bottom", 241.3, 106.68, "HUB_CORE_FB", "GND", mpn="RC0603FR-07100KL")
    resistor(s, "R1707", "100k core PG pull-up", 266.7, 106.68, "SYS_3V3", "HUB_CORE_PG", a_kind="hier", mpn="RC0603FR-07100KL")
    s.place("C1705", "C", "120p core feed-forward", 215.9, 121.92,
            footprint=FOOTPRINTS["C_0402"], pin_nets={"1": ("HUB_VCORE", "local"), "2": ("HUB_CORE_FB", "local")},
            extra_props=props("Murata", "GRM1555C1H121JA01D"))
    capacitor(s, "C1706", "4.7u core input", 190.5, 121.92, "SYS_3V3", kind="hier", footprint="C_0805", mpn="GRM21BR71A475KA73L")
    capacitor(s, "C1707", "100n core input HF", 203.2, 121.92, "SYS_3V3", kind="hier")
    capacitor(s, "C1708", "10u core output", 254, 121.92, "HUB_VCORE", footprint="C_0805", mpn="GRM21BR71A106KE51L")
    capacitor(s, "C1709", "10u core output", 266.7, 121.92, "HUB_VCORE", footprint="C_0805", mpn="GRM21BR71A106KE51L")


def add_hub(s):
    unit1 = {
        "1": ("HUB_RESET_N", "local"), "2": ("INTERNAL_USB_VBUS_VALID", "hier"), "3": ("", "nc"), "4": ("", "nc"),
        "21": ("HUB_CFG1", "local"), "22": ("HUB_CFG2", "local"), "23": ("HUB_CFG3", "local"),
        "24": ("GND", "local"), "25": ("HUB_VCORE", "local"), "26": ("SYS_3V3", "hier"),
        "43": ("SYS_3V3", "hier"), "44": ("", "nc"), "45": ("", "nc"), "46": ("", "nc"),
        "47": ("", "nc"), "48": ("", "nc"), "49": ("", "nc"), "50": ("", "nc"),
        "51": ("", "nc"), "52": ("", "nc"), "53": ("SYS_3V3", "hier"), "54": ("", "nc"),
        "55": ("HUB_VCORE", "local"), "56": ("", "nc"),
        "57": ("HUB_PRT_CTL4", "local"), "58": ("HUB_PRT_CTL3", "local"),
        "59": ("HUB_PRT_CTL2", "local"), "60": ("HUB_DS1_PRT_CTL", "local"),
        "61": ("", "nc"), "62": ("SYS_3V3", "hier"),
        "63": ("HUB_TEST1", "local"), "64": ("HUB_TEST2", "local"), "65": ("HUB_TEST3", "local"),
        "66": ("", "nc"), "67": ("SYS_3V3", "hier"), "68": ("HUB_SPI_CLK", "local"),
        "69": ("HUB_NON_REM", "local"), "70": ("HUB_BC_EN", "local"),
        "71": ("HUB_SPI_D1", "local"), "72": ("HUB_SPI_D2", "local"),
        "73": ("HUB_SPI_D3", "local"), "74": ("", "nc"),
        "75": ("", "nc"), "76": ("", "nc"), "77": ("", "nc"),
        "78": ("HUB_VCORE", "local"), "79": ("SYS_3V3", "hier"), "80": ("", "nc"),
        "88": ("SYS_3V3", "hier"), "96": ("", "nc"), "97": ("", "nc"),
        "98": ("HUB_CLK", "local"), "99": ("SYS_3V3", "hier"),
        "100": ("HUB_RBIAS", "local"), "101": ("GND", "local"),
    }
    s.place("U1700", "USB7206C", "USB7206C-I/KDX six-port USB 3.2 Gen 2 hub", 345.44, 88.9,
            unit=1, footprint=FOOTPRINTS["USB7206C"], pin_nets=unit1,
            extra_props=props("Microchip", "USB7206C-I/KDX",
                              "https://ww1.microchip.com/downloads/aemDocuments/documents/NCS/ProductDocuments/DataSheets/USB7206C-Data-Sheet-DS00003850.pdf"))
    resistor(s, "R1840", "10k DS1 PRT_CTL idle pull-up; VBUS is managed by its TCPC",
             304.8, 132.08, "SYS_3V3", "HUB_DS1_PRT_CTL", a_kind="hier",
             mpn="RC0603FR-0710KL")
    unit2 = {
        "5": ("HUB_DS1_DP", "hier"), "6": ("HUB_DS1_DM", "hier"),
        "7": ("HUB_DS1_TX_RAW_P", "local"), "8": ("HUB_DS1_TX_RAW_N", "local"),
        "9": ("HUB_VCORE", "local"), "10": ("HUB_DS1_SSRX_P", "hier"), "11": ("HUB_DS1_SSRX_N", "hier"),
        "12": ("", "nc"), "13": ("", "nc"),
        "14": ("HUB_DS2_DP", "local"), "15": ("HUB_DS2_DM", "local"),
        "16": ("HUB_DS2_TX_RAW_P", "local"), "17": ("HUB_DS2_TX_RAW_N", "local"),
        "18": ("HUB_VCORE", "local"), "19": ("HUB_DS2_SSRX_P", "local"), "20": ("HUB_DS2_SSRX_N", "local"),
    }
    unit3 = {
        "27": ("HUB_DS3_DP", "local"), "28": ("HUB_DS3_DM", "local"),
        "29": ("HUB_DS3_TX_RAW_P", "local"), "30": ("HUB_DS3_TX_RAW_N", "local"),
        "31": ("HUB_VCORE", "local"), "32": ("HUB_DS3_SSRX_P", "local"), "33": ("HUB_DS3_SSRX_N", "local"),
        "34": ("HUB_DS4_DP", "local"), "35": ("HUB_DS4_DM", "local"),
        "36": ("HUB_DS4_TX_RAW_P", "local"), "37": ("HUB_DS4_TX_RAW_N", "local"),
        "38": ("HUB_VCORE", "local"), "39": ("HUB_DS4_SSRX_P", "local"), "40": ("HUB_DS4_SSRX_N", "local"),
    }
    unit4 = {
        "41": ("HUB_DIS6_DM", "local"), "42": ("HUB_DIS6_DP", "local"),
        "81": ("HUB_DIS5_DP", "local"), "82": ("HUB_DIS5_DM", "local"),
        "83": ("", "nc"), "84": ("", "nc"), "85": ("HUB_VCORE", "local"),
        "86": ("", "nc"), "87": ("", "nc"),
    }
    unit5 = {
        "89": ("USBC2_DP", "hier"), "90": ("USBC2_DM", "hier"),
        "91": ("HUB_UP_TX_RAW_P", "local"), "92": ("HUB_UP_TX_RAW_N", "local"),
        "93": ("HUB_VCORE", "local"), "94": ("USBC2_SSTX_P", "hier"), "95": ("USBC2_SSTX_N", "hier"),
    }
    for unit, nets, x, y in ((2, unit2, 424.18, 63.5), (3, unit3, 424.18, 134.62),
                              (4, unit4, 500.38, 63.5), (5, unit5, 500.38, 134.62)):
        s.place("U1700", "USB7206C", "USB7206C-I/KDX six-port USB 3.2 Gen 2 hub", x, y,
                unit=unit, footprint=FOOTPRINTS["USB7206C"], pin_nets=nets,
                extra_props=props("Microchip", "USB7206C-I/KDX"))

    for ref, net, value, x, mpn in (
        ("R1700", "HUB_CFG1", "10k CFG_STRAP1", 300.99, "RC0603FR-0710KL"),
        ("R1701", "HUB_CFG2", "200k CFG_STRAP2", 313.69, "RC0603FR-07200KL"),
        ("R1702", "HUB_CFG3", "200k CFG_STRAP3", 326.39, "RC0603FR-07200KL"),
        ("R1703", "HUB_NON_REM", "200k all ports removable", 339.09, "RC0603FR-07200KL"),
        ("R1704", "HUB_BC_EN", "200k BC1.2 disabled", 351.79, "RC0603FR-07200KL"),
        ("R1708", "HUB_RBIAS", "12.0k 1% USB7206C RBIAS", 364.49, "RC0603FR-0712KL"),
    ):
        resistor(s, ref, value, x, 160.02, net, "GND", mpn=mpn)
    for ref, net, x in (("R1715", "HUB_TEST1", 389.89), ("R1716", "HUB_TEST2", 402.59), ("R1717", "HUB_TEST3", 415.29)):
        resistor(s, ref, "10k TEST pull-up", x, 160.02, "SYS_3V3", net, a_kind="hier")
    for ref, net, x in (
        ("R1720", "HUB_SPI_CLK", 427.99),
        ("R1721", "HUB_SPI_D1", 440.69),
        ("R1722", "HUB_SPI_D2", 453.39),
        ("R1723", "HUB_SPI_D3", 466.09),
    ):
        resistor(s, ref, "100k unused SPI pull-down", x, 160.02, net, "GND", mpn="RC0603FR-07100KL")
    for ref, net, x in (
        ("R1730", "HUB_DIS5_DP", 478.79),
        ("R1731", "HUB_DIS5_DM", 491.49),
        ("R1732", "HUB_DIS6_DP", 504.19),
        ("R1733", "HUB_DIS6_DM", 516.89),
    ):
        resistor(s, ref, "0R unused-port disable strap to 3V3", x, 160.02,
                 "SYS_3V3", net, a_kind="hier", mpn="RC0603JR-070RL")

    s.place("U1702", "TLV803EA29RDBZR", "TLV803EA29 USB hub reset supervisor", 459.74, 177.8,
            footprint=FOOTPRINTS["TLV803EA29RDBZR"],
            pin_nets={"1": ("HUB_3V3_OK", "local"), "2": ("GND", "local"), "3": ("SYS_3V3", "hier")},
            extra_props=props("Texas Instruments", "TLV803EA29RDBZR"))
    resistor(s, "R1718", "10k hub 3V3 supervisor pull-up", 487.68, 177.8, "SYS_3V3", "HUB_3V3_OK", a_kind="hier")
    s.place("U1704", "74LVC1G08", "SN74LVC1G08 hub 3V3/core-PG reset gate", 510.54, 177.8,
            footprint=FOOTPRINTS["SN74LVC1G08DBV"], pin_nets={
                "1": ("HUB_3V3_OK", "local"), "2": ("HUB_CORE_PG", "local"),
                "3": ("GND", "local"), "4": ("HUB_RESET_N", "local"),
                "5": ("SYS_3V3", "hier"),
            }, extra_props=props("Texas Instruments", "SN74LVC1G08DBVR"))
    capacitor(s, "C1717", "100n hub reset-gate bypass", 510.54, 193.04, "SYS_3V3", kind="hier")
    s.place("Y1700", "ASDMB-xxxMHz", "25.000MHz 3.3V USB hub oscillator", 546.1, 177.8,
            footprint=FOOTPRINTS["Oscillator_ASDMB"], pin_nets={
                "1": ("SYS_3V3", "hier"), "2": ("GND", "local"),
                "3": ("HUB_CLK", "local"), "4": ("SYS_3V3", "hier"),
            }, extra_props=props("Abracon", "ASDMB-25.000MHZ-LC-T"))
    capacitor(s, "C1716", "100n oscillator bypass", 571.5, 177.8, "SYS_3V3", kind="hier")
    for ref, raw, coupled, x in (
        ("C1720", "HUB_DS1_TX_RAW_P", "HUB_DS1_SSTX_P", 424.18),
        ("C1721", "HUB_DS1_TX_RAW_N", "HUB_DS1_SSTX_N", 436.88),
        ("C1722", "HUB_DS2_TX_RAW_P", "HUB_DS2_SSTX_P", 449.58),
        ("C1723", "HUB_DS2_TX_RAW_N", "HUB_DS2_SSTX_N", 462.28),
        ("C1724", "HUB_DS3_TX_RAW_P", "HUB_DS3_SSTX_P", 474.98),
        ("C1725", "HUB_DS3_TX_RAW_N", "HUB_DS3_SSTX_N", 487.68),
        ("C1726", "HUB_DS4_TX_RAW_P", "HUB_DS4_SSTX_P", 500.38),
        ("C1727", "HUB_DS4_TX_RAW_N", "HUB_DS4_SSTX_N", 513.08),
        ("C1728", "HUB_UP_TX_RAW_P", "USBC2_SSRX_P", 525.78),
        ("C1729", "HUB_UP_TX_RAW_N", "USBC2_SSRX_N", 538.48),
    ):
        kind = "hier" if coupled.startswith(("HUB_DS1", "USBC2")) else "local"
        s.place(ref, "C", "100n USB 3.2 TX AC coupling", x, 203.2, footprint=FOOTPRINTS["C_0402"],
                pin_nets={"1": (raw, "local"), "2": (coupled, kind)},
                extra_props=props("Murata", "GRM155R71C104KA88D"))
    # One 100 nF + 1 nF pair per USB7206C supply pin: eight VDD33 and nine VCORE pins.
    for index in range(8):
        capacitor(s, f"C{1810 + index}", "100n USB7206C VDD33 local", 292.1 + index * 10.16, 215.9,
                  "SYS_3V3", kind="hier")
        capacitor(s, f"C{1830 + index}", "1n USB7206C VDD33 HF", 292.1 + index * 10.16, 226.06,
                  "SYS_3V3", kind="hier", footprint="C_0402", mpn="GRM155R71H102KA01D")
    for index in range(9):
        capacitor(s, f"C{1820 + index}", "100n USB7206C VCORE local", 381 + index * 10.16, 215.9,
                  "HUB_VCORE")
        capacitor(s, f"C{1840 + index}", "1n USB7206C VCORE HF", 381 + index * 10.16, 226.06,
                  "HUB_VCORE", footprint="C_0402", mpn="GRM155R71H102KA01D")
    capacitor(s, "C1849", "10u USB7206C VDD33 bulk", 482.6, 226.06, "SYS_3V3",
              kind="hier", footprint="C_0805", mpn="GRM21BR71A106KE51L")


def add_source_port(s, *, jref, port, base, x0, y0):
    ctl = f"HUB_PRT_CTL{port}"
    dp = f"HUB_DS{port}_DP"
    dm = f"HUB_DS{port}_DM"
    host_tx_p = f"HUB_DS{port}_SSTX_P"
    host_tx_n = f"HUB_DS{port}_SSTX_N"
    host_rx_p = f"HUB_DS{port}_SSRX_P"
    host_rx_n = f"HUB_DS{port}_SSRX_N"
    pre = f"J{jref[1:]}_5V_PRE"
    vbus_sys = f"J{jref[1:]}_VBUS_SYS"
    vbus = f"J{jref[1:]}_VBUS"
    vbus_power = f"J{jref[1:]}_VBUS_POWER"
    ilim = f"J{jref[1:]}_ILIM"
    cc1, cc2 = f"J{jref[1:]}_CC1", f"J{jref[1:]}_CC2"
    pol, refnet, refrtn = f"J{jref[1:]}_POL_N", f"J{jref[1:]}_REF", f"J{jref[1:]}_REF_RTN"
    tx1p, tx1n, tx2p, tx2n = (f"J{jref[1:]}_{n}" for n in ("TX1_P", "TX1_N", "TX2_P", "TX2_N"))
    rx1p, rx1n, rx2p, rx2n = (f"J{jref[1:]}_{n}" for n in ("RX1_P", "RX1_N", "RX2_P", "RX2_N"))
    u_sw, u_cc, u_mux, u_ovp = f"U{base}", f"U{base + 1}", f"U{base + 2}", f"U{base + 3}"
    s.text(x0, y0, f"== {jref}: source-only USB-C data port, USB7206C downstream {port} ==")
    s.place(u_sw, "TPS2553D", "TPS2553DDBVR 1.3A USB branch", x0 + 25.4, y0 + 22.86,
            footprint=FOOTPRINTS["TPS2553DDBV"], pin_nets={
                "1": ("USB_PORT_5V", "hier"), "2": ("GND", "local"), "3": (ctl, "local"),
                "4": (ctl, "local"), "5": (ilim, "local"), "6": (pre, "local"),
            }, extra_props=props("Texas Instruments", "TPS2553DDBVR"))
    resistor(s, f"R{base}", "20.0k 1% TPS2553 1.3A ILIM", x0 + 2.54, y0 + 55.88, ilim, "GND", mpn="RC0603FR-0720KL")
    s.place(u_cc, "TPS25810RVC", "TPS25810RVCR Type-C DFP controller", x0 + 78.74, y0 + 43.18,
            footprint=FOOTPRINTS["TPS25810RVC"], pin_nets={
                "1": (ctl, "local"), "2": (pre, "local"), "3": (pre, "local"), "4": (pre, "local"),
                "5": ("SYS_3V3", "hier"), "6": (ctl, "local"), "7": ("GND", "local"), "8": ("GND", "local"),
                "9": (refrtn, "local"), "10": (refnet, "local"), "11": (cc1, "local"), "12": ("GND", "local"),
                "13": (cc2, "local"), "14": (vbus_sys, "local"), "15": (vbus_sys, "local"),
                "16": ("", "nc"), "17": ("", "nc"), "18": (pol, "local"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("GND", "local"),
            }, extra_props=props("Texas Instruments", "TPS25810RVCR"))
    s.place(u_mux, "HD3SS6126", "HD3SS6126RUAR USB3 orientation mux", x0 + 147.32, y0 + 43.18,
            footprint=FOOTPRINTS["HD3SS6126"], pin_nets={
                "1": ("", "nc"), "2": ("", "nc"), "3": ("", "nc"), "4": ("", "nc"), "5": ("", "nc"),
                "6": ("GND", "local"), "7": ("", "nc"), "8": ("", "nc"), "9": (pol, "local"),
                "10": ("GND", "local"), "11": (host_tx_p, "local"), "12": (host_tx_n, "local"),
                "13": ("SYS_3V3", "hier"), "14": ("GND", "local"),
                "15": (host_rx_p, "local"), "16": (host_rx_n, "local"),
                "17": ("GND", "local"), "18": ("", "nc"), "19": ("GND", "local"),
                "20": ("SYS_3V3", "hier"), "21": ("GND", "local"),
                "22": (rx1n, "local"), "23": (rx1p, "local"), "24": (tx1n, "local"), "25": (tx1p, "local"),
                "26": (rx2n, "local"), "27": (rx2p, "local"), "28": (tx2n, "local"), "29": (tx2p, "local"),
                "30": ("SYS_3V3", "hier"), "31": ("", "nc"), "32": ("", "nc"), "33": ("", "nc"),
                "34": ("", "nc"), "35": ("", "nc"), "36": ("", "nc"), "37": ("", "nc"),
                "38": ("", "nc"), "39": ("", "nc"), "40": ("", "nc"), "41": ("", "nc"), "42": ("", "nc"),
                "43": ("GND", "local"),
            }, extra_props=props(
                "Texas Instruments", "HD3SS6126RUAR",
                "https://www.ti.com/lit/ds/symlink/hd3ss6126.pdf",
                EnableState="HS_OE_GND_NORMAL_OPERATION",
            ))
    s.place(u_ovp, "TPD1S514_1YZR", "TPD1S514-1YZR 5.9V VBUS OVP", x0 + 203.2, y0 + 20.32,
            footprint=FOOTPRINTS["TPD1S514_YZ"], pin_nets={
                "A1": ("GND", "local"),
                "A2": (vbus_sys, "local"), "A3": (vbus_sys, "local"), "B2": (vbus_sys, "local"),
                "B1": (vbus_power, "local"),
                "B3": (vbus, "local"), "C2": (vbus, "local"), "C3": (vbus, "local"),
                "A4": ("GND", "local"), "B4": ("GND", "local"),
                "C1": ("GND", "local"), "C4": ("GND", "local"),
            }, extra_props=props(
                "Texas Instruments", "TPD1S514-1YZR",
                "https://www.ti.com/lit/ds/symlink/tpd1s514.pdf",
            ))
    s.place(jref, "USB_C_Receptacle", f"USB-C source-only data port {jref}", x0 + 226.06, y0 + 43.18,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets={
                "A1": ("GND", "local"), "A12": ("GND", "local"), "B1": ("GND", "local"), "B12": ("GND", "local"),
                "SH": ("GND", "local"), "A4": (vbus, "local"), "A9": (vbus, "local"), "B4": (vbus, "local"), "B9": (vbus, "local"),
                "A5": (cc1, "local"), "B5": (cc2, "local"),
                "A6": (dp, "local"), "B6": (dp, "local"), "A7": (dm, "local"), "B7": (dm, "local"),
                "A2": (tx1p, "local"), "A3": (tx1n, "local"), "B2": (tx2p, "local"), "B3": (tx2n, "local"),
                "B11": (rx1p, "local"), "B10": (rx1n, "local"), "A11": (rx2p, "local"), "A10": (rx2n, "local"),
                "A8": ("", "nc"), "B8": ("", "nc"),
            }, extra_props=props("Molex", "105450-0101"))
    capacitor(s, f"C{base}", "100n branch input", x0 + 25.4, y0 + 68.58, "USB_PORT_5V", kind="hier")
    capacitor(s, f"C{base + 1}", "100n TPS25810 IN HF", x0 + 78.74, y0 + 68.58, pre)
    s.place(f"C{base + 2}", "C_Polarized", "150u 10V TPS25810 input reservoir", x0 + 101.6, y0 + 68.58,
            footprint="Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D",
            pin_nets={"1": (pre, "local"), "2": ("GND", "local")},
            extra_props=props("KEMET", "T520D157M010ATE025"))
    capacitor(s, f"C{base + 3}", "10u protected VBUS_SYS", x0 + 226.06, y0 + 68.58,
              vbus_sys, footprint="C_10u", mpn="GRM31CR71A106KA01L")
    capacitor(s, f"C{base + 4}", "100n TPS25810 AUX", x0 + 91.44, y0 + 78.74, "SYS_3V3", kind="hier")
    for offset, x in enumerate((132.08, 144.78, 157.48)):
        capacitor(s, f"C{base + 5 + offset}", "100n mux VDD", x0 + x, y0 + 78.74, "SYS_3V3", kind="hier")
    capacitor(s, f"C{base + 8}", "1u mux local bulk", x0 + 170.18, y0 + 78.74,
              "SYS_3V3", kind="hier", footprint="C_100n", mpn="GRM188R71A105KA61D")
    capacitor(s, f"C{base + 9}", "10n mux HF", x0 + 182.88, y0 + 78.74,
              "SYS_3V3", kind="hier", footprint="C_0402", mpn="GRM155R71H103KA88D")
    resistor(s, f"R{base + 1}", "4.99k POL pull-up", x0 + 116.84, y0 + 68.58, "SYS_3V3", pol, a_kind="hier", mpn="RC0603FR-074K99L")
    resistor(s, f"R{base + 2}", "100k 1% TPS25810 REF", x0 + 101.6, y0 + 78.74, refnet, refrtn, mpn="RC0603FR-07100KL")
    s.place(f"R{base + 10}", "R", "249R 0.25W TPS25810 OUT discharge", x0 + 203.2, y0 + 78.74,
            footprint=FOOTPRINTS["R_1206"], pin_nets={"1": (vbus_sys, "local"), "2": ("GND", "local")},
            extra_props=props("Yageo", "RC1206FR-07249RL"))
    capacitor(s, f"C{base + 10}", "1u 50V connector-side VBUS", x0 + 215.9, y0 + 78.74,
              vbus, footprint="C_0805", mpn="GRM21BR71H105KA12L")
    capacitor(s, f"C{base + 11}", "1u TPD1S514 VBUS_POWER stability", x0 + 228.6, y0 + 78.74,
              vbus_power, footprint="C_100n", mpn="GRM188R71A105KA61D")
    ss_esd(s, 1800 + (port - 2) * 8, x0 + 264.16, y0 + 5.08,
           [tx1p, tx1n, tx2p, tx2n, rx1p, rx1n, rx2p, rx2n])
    usb2_cc_esd(s, f"U{base + 5}", x0 + 264.16, y0 + 68.58, dp, dm, cc1, cc2)


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 1700
    s.refcounters["#FLG"] = 1700
    s.text(20, 12.7, "== Five-port external USB architecture: USB7206C hub and three source-only Type-C ports ==")
    s.text(20, 20.32, "Mu HSIO1 plus USB2_P4 is the hub upstream. Hub port 1 feeds rear-right dual-role J11 on sheet 5.")
    s.text(20, 27.94, "J22, J23, and J12 are data/source-only. TPD1S514-1 blocks forced high-voltage VBUS; compliant charger attach is a safe no-op.")
    s.text(20, 35.56, "USB_PORT_5V is private to the five external ports; per-port current limiting prevents one cable fault from dropping the laptop.")
    s.text(20, 43.18, "USB7206C VBUS_DET follows supervised physical host VBUS; unused ports 5/6 are disabled by DP/DM high straps.")
    add_hub_supplies(s)
    add_hub(s)
    add_source_port(s, jref="J22", port=2, base=1780, x0=20.32, y0=238.76)
    add_source_port(s, jref="J23", port=3, base=1740, x0=304.8, y0=238.76)
    add_source_port(s, jref="J12", port=4, base=1760, x0=20.32, y0=337.82)
    s.pwrflag(571.5, 198.12, "HUB_VCORE")
    s.pwrflag(571.5, 215.9, "USB_PORT_5V")
    s.gnd(571.5, 228.6)
    return s
