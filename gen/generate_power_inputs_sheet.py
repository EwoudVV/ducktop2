import os

from build_ducktop2 import FOOTPRINTS, PROJDIR, Sheet, U


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


def capacitor(s, ref, value, x, y, net, *, kind="local", footprint="C_100n",
              manufacturer="Murata", mpn="GRM188R71H104KA93D"):
    s.place(ref, "C", value, x, y, footprint=FOOTPRINTS[footprint],
            pin_nets={"1": (net, kind), "2": ("GND", "local")},
            extra_props=props(manufacturer, mpn))


def series_capacitor(s, ref, value, x, y, a, b, *, b_kind="local"):
    s.place(ref, "C", value, x, y, footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": (a, "local"), "2": (b, b_kind)},
            extra_props=props("Murata", "GRM155R71C224KA12D"))


def ss_esd(s, base, x, y, nets):
    for index, net in enumerate(nets):
        s.place(f"D{base + index}", "TPD1E0B04", "TPD1E0B04DPLR 0.13pF USB3 ESD",
                x, y + index * 6.35, footprint=FOOTPRINTS["TPD1E0B04DPL"],
                pin_nets={"1": (net, "local"), "2": ("GND", "local")},
                extra_props=props(
                    "Texas Instruments", "TPD1E0B04DPLR",
                    "https://www.ti.com/lit/ds/symlink/tpd1e0b04.pdf",
                ))


def add_tps26630(s, port, x0, y0, base):
    raw = f"PD{port}_PPHV"
    gated = f"PD{port}_VBUS_GATED"
    uv = f"PD{port}_EFUSE_UV"
    ov = f"PD{port}_EFUSE_OV"
    shdn = f"PD{port}_EFUSE_SHDN"
    ilim = f"PD{port}_EFUSE_ILIM"
    dvdt = f"PD{port}_EFUSE_DVDT"
    fault = f"PD{port}_EFUSE_FAULT_N"
    path_en = f"PD{port}_PATH_EN"
    uref = f"U{719 + port}"

    s.place(uref, "TPS26630RGE", f"TPS26630RGER PD{port} default-off 3A sink eFuse", x0, y0,
            footprint=FOOTPRINTS["TPS26630RGE"], pin_nets={
                "1": (raw, "local"), "2": (raw, "local"),
                "3": ("", "nc"), "4": ("", "nc"), "5": (raw, "local"),
                "6": (uv, "local"), "7": (ov, "local"), "8": ("GND", "local"),
                "9": (dvdt, "local"), "10": (ilim, "local"), "11": ("GND", "local"),
                "12": (shdn, "local"), "13": ("", "nc"), "14": (fault, "hier"),
                "15": ("GND", "local"), "16": ("", "nc"),
                "17": (gated, "local"), "18": (gated, "local"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("", "nc"),
                "22": ("", "nc"), "23": ("", "nc"), "24": ("", "nc"),
                "25": ("GND", "local"),
            }, extra_props=props(
                "Texas Instruments", "TPS26630RGER",
                "https://www.ti.com/lit/ds/symlink/tps2663.pdf",
                SafetyState="MODE_GND_AUTORETRY;PGTH_GND_PGOOD_UNUSED;SHDN_47K_PULLDOWN",
            ))

    entries = (
        (base, "887k 0.1% 15V eFuse UV/OV top", raw, uv, "RT0603BRD07887KL", "local", "local"),
        (base + 1, "27.4k 0.1% 15V eFuse UV/OV middle", uv, ov, "RT0603BRD0727K4L", "local", "local"),
        (base + 2, "68.1k 0.1% 15V eFuse UV/OV bottom", ov, "GND", "RT0603BRD0768K1L", "local", "local"),
        (base + 3, "6.04k 1% eFuse 2.98A ILIM", ilim, "GND", "RC0603FR-076K04L", "local", "local"),
        (base + 4, "47k eFuse default-off pulldown", shdn, "GND", "RC0603FR-0747KL", "local", "local"),
        (base + 5, "10k path-enable series", path_en, shdn, "RC0603FR-0710KL", "hier", "local"),
        (base + 6, "10k eFuse FLT pull-up", "MCU_3V3", fault, "RC0603FR-0710KL", "hier", "hier"),
    )
    for offset, (refn, value, a, b, mpn, ak, bk) in enumerate(entries):
        resistor(s, f"R{refn}", value, x0 + 45.72, y0 - 30.48 + offset * 10.16,
                 a, b, a_kind=ak, b_kind=bk, mpn=mpn)

    capacitor(s, f"C{base}", "100n 50V eFuse input local", x0 + 96.52, y0 - 17.78, raw)
    capacitor(s, f"C{base + 1}", "10u 25V eFuse output", x0 + 96.52, y0 - 5.08, gated,
              footprint="C_10u", mpn="GRM31CR71E106KA12L")
    capacitor(s, f"C{base + 2}", "22n eFuse dVdT", x0 + 96.52, y0 + 7.62, dvdt,
              footprint="C_0402", mpn="GRM155R71H223KA12D")
    s.place(f"D{base}", "D_Schottky", "B340A eFuse output negative-transient clamp",
            x0 + 96.52, y0 + 20.32, footprint=FOOTPRINTS["D_Schottky_SMA"],
            pin_nets={"1": (gated, "local"), "2": ("GND", "local")},
            extra_props=props("Diodes Incorporated", "B340A-13-F"))


def add_dual_role_port(s, *, port, jref, host, x0, y0, rbase, cbase, ubase, dbase, ebase):
    raw_vbus = f"PD{port}_VBUS_RAW"
    pphv = f"PD{port}_PPHV"
    ldo3v3 = f"PD{port}_LDO3V3"
    ldo1v5 = f"PD{port}_LDO1V5"
    drain = f"PD{port}_DRAIN_THERMAL"
    cc1_c, cc2_c = f"PD{port}_CC1_CONN", f"PD{port}_CC2_CONN"
    cc1_s, cc2_s = f"PD{port}_CC1_SYS", f"PD{port}_CC2_SYS"
    dp_c, dm_c = f"PD{port}_DP_CONN", f"PD{port}_DM_CONN"
    dp_host, dm_host = f"PD{port}_DP_HOST_SWITCHED", f"PD{port}_DM_HOST_SWITCHED"
    esd_bias = f"PD{port}_CC_ESD_VBIAS"
    cc_fault = f"PD{port}_CC_FAULT_LOCAL_N"
    eeprom_sda, eeprom_scl = f"PD{port}_EEPROM_SDA", f"PD{port}_EEPROM_SCL"
    eeprom_irq = f"PD{port}_EEPROM_IRQ_N"
    gpio_flip = f"PD{port}_GPIO_FLIP"
    gpio_dfp = f"PD{port}_GPIO_DFP"
    gpio_attach = f"PD{port}_GPIO_ATTACH"
    host_attached = f"PD{port}_HOST_ATTACHED"
    mux_flip, mux_en = f"PD{port}_MUX_FLIP", f"PD{port}_MUX_EN"
    usb2_oe_n = f"PD{port}_USB2_OE_N"
    mux_sleep = f"PD{port}_MUX_SLEEP_N"
    tx1p, tx1n = f"PD{port}_TX1_P", f"PD{port}_TX1_N"
    tx2p, tx2n = f"PD{port}_TX2_P", f"PD{port}_TX2_N"
    rx1p, rx1n = f"PD{port}_RX1_P", f"PD{port}_RX1_N"
    rx2p, rx2n = f"PD{port}_RX2_P", f"PD{port}_RX2_N"
    ctx1p, ctx1n = f"PD{port}_CTX1_RAW_P", f"PD{port}_CTX1_RAW_N"
    ctx2p, ctx2n = f"PD{port}_CTX2_RAW_P", f"PD{port}_CTX2_RAW_N"
    ssrxp, ssrxn = f"PD{port}_SSRX_RAW_P", f"PD{port}_SSRX_RAW_N"
    mode, vio, eqcfg, sseq1 = (f"PD{port}_{name}" for name in ("MUX_MODE", "MUX_VIO", "MUX_EQCFG", "MUX_SSEQ1"))

    s.text(x0, y0, f"== {jref}: USB 3.2 Gen 2 data plus USB-PD charging, side port {port} ==")
    s.place(jref, "USB_C_Receptacle", f"USB-C dual-role data/PD port {jref}", x0 + 254, y0 + 55.88,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets={
                "A1": ("GND", "local"), "A12": ("GND", "local"),
                "B1": ("GND", "local"), "B12": ("GND", "local"), "SH": ("GND", "local"),
                "A4": (raw_vbus, "hier"), "A9": (raw_vbus, "hier"),
                "B4": (raw_vbus, "hier"), "B9": (raw_vbus, "hier"),
                "A5": (cc1_c, "local"), "B5": (cc2_c, "local"),
                "A6": (dp_c, "local"), "B6": (dp_c, "local"),
                "A7": (dm_c, "local"), "B7": (dm_c, "local"),
                "A2": (tx1p, "local"), "A3": (tx1n, "local"),
                "B2": (tx2p, "local"), "B3": (tx2n, "local"),
                "B11": (rx1p, "local"), "B10": (rx1n, "local"),
                "A11": (rx2p, "local"), "A10": (rx2n, "local"),
                "A8": ("", "nc"), "B8": ("", "nc"),
            }, extra_props=props("Molex", "105450-0101"))

    s.place(f"U{ubase + 1}", "TPD4S201", "TPD4S201 CC and USB2 short-to-VBUS protector",
            x0 + 205.74, y0 + 55.88, footprint=FOOTPRINTS["TPD4S201"], pin_nets={
                "1": (dp_c, "local"), "2": (dm_c, "local"), "3": (esd_bias, "local"),
                "4": (cc1_c, "local"), "5": (cc2_c, "local"),
                "6": (cc2_c, "local"), "7": (cc1_c, "local"),
                "8": ("GND", "local"), "9": (cc_fault, "local"), "10": (ldo3v3, "local"),
                "11": (cc2_s, "local"), "12": (cc1_s, "local"), "13": ("GND", "local"),
                "14": (dm_host, "local"), "15": (dp_host, "local"),
                "16": ("", "nc"), "17": ("", "nc"), "18": ("GND", "local"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("GND", "local"),
            }, extra_props=props(
                "Texas Instruments", "TPD4S201RUKR",
                "https://www.ti.com/lit/ds/symlink/tpd4s201.pdf",
                ChannelUse="CC1_CC2_AND_USB2_DP_DM;DEAD_BATTERY_RD_ENABLED",
            ))
    capacitor(s, f"C{cbase}", "100n 100V TPD4S201 VBIAS", x0 + 205.74, y0 + 91.44,
              esd_bias, footprint="C_0805", mpn="GRM21BR72A104KA01L")
    capacitor(s, f"C{cbase + 1}", "820n 10V TPD4S201 VPWR", x0 + 218.44, y0 + 91.44,
              ldo3v3, footprint="C_0805", mpn="GRM21BR71A824KA01L")
    resistor(s, f"R{rbase}", "10k shared CC/USB2 protector FLT pull-up", x0 + 231.14, y0 + 91.44,
             "MCU_3V3", "PD_PROTECT_FAULT_N", a_kind="hier", b_kind="hier", mpn="RC0603FR-0710KL")
    resistor(s, f"R{rbase + 17}", "0R protector FLT wired-OR link", x0 + 243.84, y0 + 91.44,
             cc_fault, "PD_PROTECT_FAULT_N", b_kind="hier", mpn="RC0603FR-070RL")

    s.place(f"U{40 + port}", "TPS25751AD", "TPS25751AD USB-PD DRP controller", x0 + 63.5, y0 + 55.88,
            footprint=FOOTPRINTS["TPS25751AD"], pin_nets={
                "1": (ldo3v3, "local"),
                "2": (ldo3v3 if port == 1 else "GND", "local"), "3": ("GND", "local"),
                "4": (ldo1v5, "local"),
                "5": ("GND", "local"), "6": ("GND", "local"), "7": ("GND", "local"),
                "8": (f"PD{port}_I2C_SDA", "hier"), "9": (f"PD{port}_I2C_SCL", "hier"),
                "10": (f"PD{port}_TCPC_IRQ_N", "hier"),
                "11": ("GND", "local"), "12": ("GND", "local"), "13": ("GND", "local"),
                "14": ("GND", "local"), "15": (drain, "local"),
                "16": (eeprom_sda, "local"), "17": (eeprom_scl, "local"), "18": (eeprom_irq, "local"),
                "19": ("GND", "local"),
                "20": (pphv, "local"),
                "23": (raw_vbus, "hier"),
                "26": (gpio_dfp, "local"), "27": ("GND", "local"),
                "28": (cc1_s, "local"), "29": (cc2_s, "local"), "30": (drain, "local"),
                "31": ("GND", "local"), "32": (raw_vbus, "hier"),
                "34": ("USB_PORT_5V", "hier"),
                "36": (gpio_attach, "local"), "37": (gpio_flip, "local"),
                "38": ("MCU_3V3", "hier"), "39": ("GND", "local"), "40": (drain, "local"),
            }, extra_props=props(
                "Texas Instruments", "TPS25751ADREFR",
                "https://www.ti.com/lit/ds/symlink/tps25751a.pdf",
                PortPolicy="DRP_PREFER_SINK;HOST_DATA_ONLY;15V_3A_SINK;5V_900MA_SOURCE;DEFAULT_RP",
                EEPROMContract=f"U{ubase + 2}_PROGRAM_WITH_VERSIONED_TPS25751_IMAGE",
                EEPROMSource="firmware/tps25751a/ducktop2_dual_role_config.json",
                ADCStrap="SAFE_MODE_ADDR_0X20" if port == 1 else "SAFE_MODE_ADDR_0X21",
            ))

    s.place(f"U{ubase + 2}", "CAT24C256", "CAT24C256 32KB private TPS25751A EEPROM",
            x0 + 20.32, y0 + 119.38, footprint=FOOTPRINTS["CAT24C256"], pin_nets={
                "1": ("GND", "local"), "2": ("GND", "local"), "3": ("GND", "local"),
                "4": ("GND", "local"), "5": (eeprom_sda, "local"), "6": (eeprom_scl, "local"),
                "7": ("GND", "local"), "8": (ldo3v3, "local"),
            }, extra_props=props(
                "onsemi", "CAT24C256WI-GT3",
                "https://www.onsemi.com/pdf/datasheet/cat24c256-d.pdf",
                ProgrammingState="PROGRAM_BEFORE_ASSEMBLY_OR_VIA_TP;READBACK_VERIFY_RELEASE_IMAGE",
            ))
    resistor(s, f"R{rbase + 1}", "2.2k EEPROM SDA pull-up", x0 + 20.32, y0 + 149.86,
             ldo3v3, eeprom_sda, mpn="RC0603FR-072K2L")
    resistor(s, f"R{rbase + 2}", "2.2k EEPROM SCL pull-up", x0 + 45.72, y0 + 149.86,
             ldo3v3, eeprom_scl, mpn="RC0603FR-072K2L")
    resistor(s, f"R{rbase + 15}", "10k I2Cc IRQ inactive pull-up", x0 + 71.12, y0 + 139.7,
             ldo3v3, eeprom_irq, mpn="RC0603FR-0710KL")
    capacitor(s, f"C{cbase + 2}", "100n EEPROM local", x0 + 71.12, y0 + 149.86, ldo3v3)
    resistor(s, f"R{rbase + 3}", "4.7k TCPC SDA pull-up", x0 + 96.52, y0 + 149.86,
             "MCU_3V3", f"PD{port}_I2C_SDA", a_kind="hier", b_kind="hier", mpn="RC0603FR-074K7L")
    resistor(s, f"R{rbase + 4}", "4.7k TCPC SCL pull-up", x0 + 121.92, y0 + 149.86,
             "MCU_3V3", f"PD{port}_I2C_SCL", a_kind="hier", b_kind="hier", mpn="RC0603FR-074K7L")
    resistor(s, f"R{rbase + 5}", "10k TCPC IRQ pull-up", x0 + 147.32, y0 + 149.86,
             "MCU_3V3", f"PD{port}_TCPC_IRQ_N", a_kind="hier", b_kind="hier")

    s.place(f"U{ubase + 4}", "74LVC2G07", "SN74LVC2G07 partial-power-down mux controls",
            x0 + 109.22, y0 + 104.14, unit=1, footprint=FOOTPRINTS["SN74LVC2G07DCK"],
            pin_nets={"1": (gpio_flip, "local"), "6": (mux_flip, "local")},
            extra_props=props("Texas Instruments", "SN74LVC2G07DCKR",
                              "https://www.ti.com/lit/ds/symlink/sn74lvc2g07.pdf"))
    s.place(f"U{ubase + 4}", "74LVC2G07", "SN74LVC2G07 partial-power-down mux controls",
            x0 + 139.7, y0 + 104.14, unit=2, footprint=FOOTPRINTS["SN74LVC2G07DCK"],
            pin_nets={"3": (host_attached, "local"), "4": (mux_en, "local")},
            extra_props=props("Texas Instruments", "SN74LVC2G07DCKR"))
    s.place(f"U{ubase + 4}", "74LVC2G07", "SN74LVC2G07 partial-power-down mux controls",
            x0 + 170.18, y0 + 104.14, unit=3, footprint=FOOTPRINTS["SN74LVC2G07DCK"],
            pin_nets={"2": ("GND", "local"), "5": ("SYS_3V3", "hier")},
            extra_props=props("Texas Instruments", "SN74LVC2G07DCKR"))
    resistor(s, f"R{rbase + 6}", "10k mux FLIP pull-up", x0 + 109.22, y0 + 132.08,
             "SYS_3V3", mux_flip, a_kind="hier")
    resistor(s, f"R{rbase + 7}", "10k mux EN pull-up", x0 + 139.7, y0 + 132.08,
             "SYS_3V3", mux_en, a_kind="hier")
    capacitor(s, f"C{cbase + 3}", "100n mux-control buffer local", x0 + 170.18, y0 + 132.08,
              "SYS_3V3", kind="hier")

    s.place(f"U{ubase + 6}", "74LVC1G08", "SN74LVC1G08 DFP and attached qualifier",
            x0 + 170.18, y0 + 116.84, footprint=FOOTPRINTS["SN74LVC1G08DBV"], pin_nets={
                "1": (gpio_dfp, "local"), "2": (gpio_attach, "local"),
                "3": ("GND", "local"), "4": (host_attached, "local"),
                "5": ("SYS_3V3", "hier"),
            }, extra_props=props(
                "Texas Instruments", "SN74LVC1G08DBVR",
                "https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf",
                Qualification="GPIO4_INVERTED_UFP_DFP_AND_GPIO7_DP_DM_MUX_ENABLE",
                DefaultState="LOW_WHEN_CONTROLLER_UNPOWERED_RESET_DETACHED_OR_SINK",
            ))

    # USB2 must follow the negotiated data role just like the SuperSpeed path.
    # GPIO4 is high only in DFP role and GPIO7 is high only while the data path
    # is attached. Their partial-power-down AND output qualifies both USB2 and
    # SuperSpeed, so reset, detach, and sink-only operation all fail off.
    # The redriver takes active-high MUX_EN directly; Qx inverts that same
    # signal for the active-low USB2 switch enable. Both paths default off.
    s.place(f"U{ubase + 3}", "TS3USB30EDGSR", "TS3USB30E DFP-qualified USB2 disconnect",
            x0 + 190.5, y0 + 116.84, footprint=FOOTPRINTS["TS3USB30EDGSR"], pin_nets={
                "1": ("GND", "local"), "2": (host["dp"], "hier"), "3": ("", "nc"),
                "4": (dp_host, "local"), "5": ("GND", "local"),
                "6": (dm_host, "local"), "7": ("", "nc"), "8": (host["dm"], "hier"),
                "9": (usb2_oe_n, "local"), "10": ("SYS_3V3", "hier"),
            }, extra_props=props(
                "Texas Instruments", "TS3USB30EDGSR",
                "https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf",
                DataRoleContract="DEFAULT_DISCONNECTED;ENABLE_ONLY_AFTER_CONFIRMED_DFP",
            ))
    resistor(s, f"R{rbase + 16}", "100k USB2 switch default-disable pull-up",
             x0 + 190.5, y0 + 144.78, "SYS_3V3", usb2_oe_n, a_kind="hier",
             mpn="RC0603FR-07100KL")
    s.place(f"Q{2000 + port}", "Q_NMOS_SOT23_GSD", "2N7002K DFP USB2 enable inverter",
            x0 + 218.44, y0 + 116.84, footprint=FOOTPRINTS["Q_NMOS"], pin_nets={
                "1": (mux_en, "local"), "2": ("GND", "local"), "3": (usb2_oe_n, "local"),
            }, extra_props=props("onsemi", "2N7002KT1G"))
    capacitor(s, f"C{cbase + 30}", "100n USB2 switch local", x0 + 218.44, y0 + 144.78,
              "SYS_3V3", kind="hier")

    s.place(f"U{ubase}", "TUSB1142", "TUSB1142 USB 3.2 Gen 2 orientation redriver",
            x0 + 147.32, y0 + 55.88, footprint=FOOTPRINTS["TUSB1142"], pin_nets={
                "1": ("SYS_3V3", "hier"), "2": (sseq1, "local"), "3": (eqcfg, "local"),
                "4": (mux_sleep, "local"), "5": ("", "nc"), "6": ("SYS_3V3", "hier"),
                "7": ("", "nc"), "8": ("", "nc"), "9": ("", "nc"), "10": ("", "nc"),
                "11": ("", "nc"), "12": ("", "nc"), "13": ("", "nc"),
                "14": (vio, "local"),
                "15": (host["sstx_n"], "hier"), "16": (host["sstx_p"], "hier"),
                "17": (mode, "local"), "18": (ssrxn, "local"), "19": (ssrxp, "local"),
                "20": ("SYS_3V3", "hier"), "21": (mux_flip, "local"), "22": ("GND", "local"),
                "23": ("", "nc"), "24": ("", "nc"), "25": ("", "nc"),
                "26": (mux_en, "local"), "27": ("GND", "local"), "28": ("SYS_3V3", "hier"),
                "29": ("", "nc"), "30": (rx1p, "local"), "31": (rx1n, "local"),
                "32": ("", "nc"), "33": (ctx1p, "local"), "34": (ctx1n, "local"),
                "35": ("", "nc"), "36": (rx2n, "local"), "37": (rx2p, "local"),
                "38": ("", "nc"), "39": (ctx2n, "local"), "40": (ctx2p, "local"),
                "41": ("GND", "local"),
            }, extra_props=props(
                "Texas Instruments", "TUSB1142IRNQR",
                "https://www.ti.com/lit/ds/symlink/tusb1142.pdf",
                StrapMode="GPIO_MODE;FULL_AEQ;4P5DB_HOST_EQ;VIO_3V3",
            ))
    for offset, (net, label) in enumerate(((mode, "MODE=0"), (vio, "VIO=3V3"),
                                           (eqcfg, "EQCFG=0"), (sseq1, "SSEQ1=0"))):
        resistor(s, f"R{rbase + 8 + offset}", f"1k TUSB1142 {label} strap", x0 + 180.34,
                 y0 + 119.38 + offset * 10.16, net, "GND", mpn="RC0603FR-071KL")
    resistor(s, f"R{rbase + 12}", "10k TUSB1142 SLP_S0# pull-up", x0 + 231.14, y0 + 132.08,
             "SYS_3V3", mux_sleep, a_kind="hier")
    resistor(s, f"R{rbase + 13}", "100k mux FLIP input default-low", x0 + 109.22, y0 + 142.24,
             gpio_flip, "GND", mpn="RC0603FR-07100KL")
    resistor(s, f"R{rbase + 14}", "100k data-attach input default-low", x0 + 139.7, y0 + 142.24,
             gpio_attach, "GND", mpn="RC0603FR-07100KL")
    resistor(s, f"R{rbase + 18}", "100k DFP-role input default-low", x0 + 154.94, y0 + 142.24,
             gpio_dfp, "GND", mpn="RC0603FR-07100KL")
    capacitor(s, f"C{cbase + 4}", "10u TUSB1142 local", x0 + 147.32, y0 + 160.02,
              "SYS_3V3", kind="hier", footprint="C_10u", mpn="GRM31CR71A106KA01L")
    for index in range(4):
        capacitor(s, f"C{cbase + 5 + index}", "100n TUSB1142 VCC local",
                  x0 + 172.72 + index * 12.7, y0 + 160.02, "SYS_3V3", kind="hier")

    for offset, (raw, coupled, kind) in enumerate((
        (ssrxp, host["ssrx_p"], "hier"), (ssrxn, host["ssrx_n"], "hier"),
        (ctx1p, tx1p, "local"), (ctx1n, tx1n, "local"),
        (ctx2p, tx2p, "local"), (ctx2n, tx2n, "local"),
    )):
        series_capacitor(s, f"C{cbase + 9 + offset}", "220n USB3 TX AC coupling",
                         x0 + 20.32 + offset * 22.86, y0 + 177.8, raw, coupled, b_kind=kind)

    s.place(f"U{ubase + 5}", "TVS2200DRV", "TVS2200 22V USB VBUS surge clamp",
            x0 + 279.4, y0 + 104.14, footprint=FOOTPRINTS["TVS2200DRV"], pin_nets={
                "1": ("GND", "local"), "2": ("GND", "local"), "3": ("GND", "local"),
                "4": (raw_vbus, "hier"), "5": (raw_vbus, "hier"), "6": (raw_vbus, "hier"),
                "7": ("GND", "local"),
            }, extra_props=props("Texas Instruments", "TVS2200DRVR",
                                  "https://www.ti.com/lit/ds/symlink/tvs2200.pdf"))
    capacitor(s, f"C{cbase + 15}", "4.7u 25V raw VBUS; pre-attach total below 10uF",
              x0 + 254, y0 + 132.08, raw_vbus, kind="hier", footprint="C_1206",
              mpn="GRM31CR71E475KA88L")
    for index in range(4):
        capacitor(s, f"C{cbase + 16 + index}", "10n 50V connector VBUS HF",
                  x0 + 254 + index * 12.7, y0 + 149.86, raw_vbus, kind="hier",
                  footprint="C_0402", mpn="GRM155R71H103KA88D")
    capacitor(s, f"C{cbase + 20}", "6.8u 25V X7R TPS25751A LDO3V3; verify >=5u effective",
              x0 + 63.5, y0 + 91.44, ldo3v3, footprint="C_1206", mpn="GRM31CR71E685KA88L")
    capacitor(s, f"C{cbase + 21}", "10u 16V X7R TPS25751A LDO1V5; verify 4.5-12u effective",
              x0 + 76.2, y0 + 91.44, ldo1v5, footprint="C_1206", mpn="GRM31CR71C106KA01L")
    capacitor(s, f"C{cbase + 22}", "10u TPS25751A VIN3V3", x0 + 88.9, y0 + 91.44,
              "MCU_3V3", kind="hier", footprint="C_10u", mpn="GRM31CR71A106KA01L")
    capacitor(s, f"C{cbase + 23}", "270p C0G CC1 total-capacitance component", x0 + 101.6, y0 + 91.44,
              cc1_s, footprint="C_0402", mpn="GRM1555C1H271JA01D")
    capacitor(s, f"C{cbase + 24}", "270p C0G CC2 total-capacitance component", x0 + 114.3, y0 + 91.44,
              cc2_s, footprint="C_0402", mpn="GRM1555C1H271JA01D")
    for index, x in enumerate((20.32, 35.56)):
        s.place(f"C{cbase + 25 + index}", "C_Polarized", "100u 10V PP5V source bulk",
                x0 + x, y0 + 195.58, footprint="Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D",
                pin_nets={"1": ("USB_PORT_5V", "hier"), "2": ("GND", "local")},
                extra_props=props("KEMET", "T520D107M010ATE070"))
    capacitor(s, f"C{cbase + 27}", "10u PP5V local ceramic", x0 + 50.8, y0 + 195.58,
              "USB_PORT_5V", kind="hier", footprint="C_10u", mpn="GRM31CR71A106KA01L")
    s.place(f"C{cbase + 28}", "C_Polarized", "68u 25V PPHV sink bulk",
            x0 + 73.66, y0 + 195.58, footprint=FOOTPRINTS["C_100u_25V_poly"],
            pin_nets={"1": (pphv, "local"), "2": ("GND", "local")},
            extra_props=props("KEMET", "T521V686M025ATE050"))
    capacitor(s, f"C{cbase + 29}", "100n 50V PPHV local", x0 + 88.9, y0 + 195.58, pphv)

    ss_esd(s, dbase, x0 + 299.72, y0 + 25.4,
           (tx1p, tx1n, tx2p, tx2n, rx1p, rx1n, rx2p, rx2n))
    add_tps26630(s, port, x0 + 355.6, y0 + 93.98, ebase)
    s.pwrflag(x0 + 327.66, y0 + 187.96, raw_vbus)
    s.pwrflag(x0 + 347.98, y0 + 187.96, pphv)
    s.text(x0, y0 + 213.36,
           f"{jref}: EEPROM configures DRP prefer-sink, 15V/3A sink, 5V/0.9A source, default Rp, GPIO6 FLIP, GPIO4 DFP, and GPIO7 data-attached.")
    s.text(x0, y0 + 220.98,
           "GPIO4 AND GPIO7 qualifies both host USB2 and SuperSpeed. They remain disconnected through reset, detach, and sink-only operation.")


def add_selector_fet(s, ref, x, y, gate, common_source, drain, drain_kind):
    s.place(ref, "Q_PMOS_1G_234S_5D", "SiSS4409DN 40V reverse-blocking PMOS", x, y,
            footprint=FOOTPRINTS["Q_SiSS4409DN"], pin_nets={
                "1": (gate, "local"), "2": (common_source, "local"),
                "3": (common_source, "local"), "4": (common_source, "local"),
                "5": (drain, drain_kind),
            }, extra_props=props("Vishay", "SiSS4409DN-T1-GE3"))


def add_pd_selector(s):
    s.text(20.32, 505.46, "== U14: two-input qualified PD selector; J21 has priority over J11 ==")
    s.place("U14", "LTC4418IUF", "LTC4418IUF#PBF dual-input PD selector", 116.84, 574.04,
            footprint=FOOTPRINTS["LTC4418IUF"], pin_nets={
                "1": ("PD_SEL_TMR", "local"), "2": ("PD1_SEL_UV", "local"),
                "3": ("PD1_SEL_OV", "local"), "4": ("PD2_SEL_UV", "local"),
                "5": ("PD2_SEL_OV", "local"), "6": ("", "nc"), "7": ("GND", "local"),
                "8": ("PD_SEL_INTVCC", "local"), "9": ("PD1_VALID_N", "hier"),
                "10": ("PD2_VALID_N", "hier"), "11": ("PD2_SEL_GATE", "local"),
                "12": ("PD2_SEL_FET_COMMON", "local"), "13": ("PD1_SEL_GATE", "local"),
                "14": ("PD1_SEL_FET_COMMON", "local"), "15": ("USB_PD_SELECTED", "hier"),
                "16": ("PD2_VBUS_GATED", "local"), "17": ("PD1_VBUS_GATED", "local"),
                "18": ("PD_SEL_INTVCC", "local"), "19": ("PD_SEL_INTVCC", "local"),
                "20": ("GND", "local"), "21": ("GND", "local"),
            }, extra_props=props(
                "Analog Devices", "LTC4418IUF#PBF",
                "https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4418.pdf",
            ))
    add_selector_fet(s, "Q15", 205.74, 543.56, "PD1_SEL_GATE", "PD1_SEL_FET_COMMON", "PD1_VBUS_GATED", "local")
    add_selector_fet(s, "Q16", 259.08, 543.56, "PD1_SEL_GATE", "PD1_SEL_FET_COMMON", "USB_PD_SELECTED", "hier")
    add_selector_fet(s, "Q17", 205.74, 586.74, "PD2_SEL_GATE", "PD2_SEL_FET_COMMON", "PD2_VBUS_GATED", "local")
    add_selector_fet(s, "Q18", 259.08, 586.74, "PD2_SEL_GATE", "PD2_SEL_FET_COMMON", "USB_PD_SELECTED", "hier")

    for index, port in enumerate((1, 2)):
        x = 20.32 + index * 66.04
        resistor(s, f"R{2140 + index * 3}", "1.00M 0.1% 15V UV top", x, 622.3,
                 f"PD{port}_VBUS_GATED", f"PD{port}_SEL_UV", mpn="RT0603BRD071ML")
        resistor(s, f"R{2141 + index * 3}", "19.6k 0.1% 15V window middle", x, 635,
                 f"PD{port}_SEL_UV", f"PD{port}_SEL_OV", mpn="RT0603BRD0719K6L")
        resistor(s, f"R{2142 + index * 3}", "63.4k 0.1% 15V OV bottom", x, 647.7,
                 f"PD{port}_SEL_OV", "GND", mpn="RT0603BRD0763K4L")
    resistor(s, "R2146", "10k PD1 VALID pull-up", 152.4, 622.3,
             "MCU_3V3", "PD1_VALID_N", a_kind="hier", b_kind="hier")
    resistor(s, "R2147", "10k PD2 VALID pull-up", 177.8, 622.3,
             "MCU_3V3", "PD2_VALID_N", a_kind="hier", b_kind="hier")
    capacitor(s, "C2140", "100n selector INTVCC", 203.2, 622.3, "PD_SEL_INTVCC")
    capacitor(s, "C2141", "15n selector TMR approx 240ms", 228.6, 622.3,
              "PD_SEL_TMR", footprint="C_0402", mpn="GRM155R71H153KA12D")
    for index, net in enumerate(("PD1_VBUS_GATED", "PD1_SEL_FET_COMMON",
                                 "PD2_VBUS_GATED", "PD2_SEL_FET_COMMON")):
        capacitor(s, f"C{2142 + index}", "100n 50V selector local",
                  254 + index * 25.4, 622.3, net)
    s.place("C2146", "C_Polarized", "100u 35V selected-PD hold-up", 355.6, 622.3,
            footprint=FOOTPRINTS["C_100u_35V_hybrid"],
            pin_nets={"1": ("USB_PD_SELECTED", "hier"), "2": ("GND", "local")},
            extra_props=props("Panasonic", "EEHZK1V101XP"))
    s.pwrflag(393.7, 622.3, "USB_PD_SELECTED")
    s.text(20.32, 670.56,
           "The EC reads each TPS25751A contract first, programs the BQ25798 input limit, then enables exactly one default-off TPS26630 path.")
    s.text(20.32, 678.18,
           "LTC4418 independently validates approximately 13.1V to 17.1V and prevents either attached adapter from backfeeding the other.")


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 2000
    s.refcounters["#FLG"] = 2000
    s.text(20.32, 12.7, "== Two rear USB-C data/charging ports: J21 left and J11 right ==")
    s.text(20.32, 20.32, "Both ports carry USB 3.2 Gen 2 plus USB2 and can sink negotiated 15V or source protected default USB current.")
    s.text(20.32, 27.94, "TPS25751A loads a versioned 32KB EEPROM image while powered from dead-battery VBUS; no EC is needed to obtain the first 15V contract.")
    s.text(20.32, 35.56, "The raw 5V attach rail stays below the Type-C pre-attach capacitance limit; large sink bulk is behind the integrated PD switch.")
    add_dual_role_port(s, port=1, jref="J21", host={
        "dp": "USBC1_DP", "dm": "USBC1_DM",
        "sstx_p": "USBC1_SSTX_P", "sstx_n": "USBC1_SSTX_N",
        "ssrx_p": "USBC1_SSRX_P", "ssrx_n": "USBC1_SSRX_N",
    }, x0=20.32, y0=50.8, rbase=2000, cbase=2000, ubase=2000, dbase=2100, ebase=2080)
    add_dual_role_port(s, port=2, jref="J11", host={
        "dp": "HUB_DS1_DP", "dm": "HUB_DS1_DM",
        "sstx_p": "HUB_DS1_SSTX_P", "sstx_n": "HUB_DS1_SSTX_N",
        "ssrx_p": "HUB_DS1_SSRX_P", "ssrx_n": "HUB_DS1_SSRX_N",
    }, x0=20.32, y0=276.86, rbase=2040, cbase=2040, ubase=2010, dbase=2120, ebase=2090)
    add_pd_selector(s)
    s.text(20.32, 693.42, "Five-port source budget: 5 x 0.9A maximum advertised load = 4.5A on the dedicated 6A USB_PORT_5V rail.")
    s.text(20.32, 701.04, "Firmware must reject any configuration that advertises more than default USB current and must shed optional ports on rail fault.")
    s.gnd(431.8, 622.3)
    return s


def main():
    sheet_symbol_uuid = U()
    s = build(sheet_symbol_uuid)
    child_text = s.render(U(), page_number="6")
    child_path = os.path.join(PROJDIR, "05_power_inputs.kicad_sch")
    with open(child_path, "w", encoding="utf-8") as f:
        f.write(child_text)
    print("wrote", child_path, len(child_text), "bytes")


if __name__ == "__main__":
    main()
