from build_ducktop2 import Sheet, FOOTPRINTS


def esd4(s, ref, value, x, y, nets):
    """Place a 4-line ESD array on named local nets."""
    s.place(ref, "TPD4EUSB30", value, x, y, footprint=FOOTPRINTS["TPD4EUSB30"],
            pin_nets={
                "1": (nets[0], "local"), "2": (nets[1], "local"),
                "3": ("GND", "local"),
                "4": (nets[2], "local"), "5": (nets[3], "local"),
                "6": ("", "nc"), "7": ("", "nc"),
                "8": ("GND", "local"),
                "9": ("", "nc"), "10": ("", "nc"),
            })


def add_port(s, port, x0, y0):
    hub = f"HUB{port}"
    usb = f"USB{port}"
    jref = f"J{10 + port}"
    ubase = 10 + port * 10
    rbase = 70 + (port - 1) * 20
    cbase = 70 + (port - 1) * 20

    tps = f"U{ubase + 1}"
    mux = f"U{ubase + 2}"
    esd_tx = f"U{ubase + 3}"
    esd_rx = f"U{ubase + 4}"
    esd_aux = f"U{ubase + 5}"

    vbus = f"{usb}_VBUS"
    cc1 = f"{usb}_CC1"
    cc2 = f"{usb}_CC2"
    pol = f"{usb}_POL_N"
    ufp = f"{usb}_UFP_N"
    ld_det = f"{usb}_LD_DET_N"
    ref = f"{usb}_REF"
    tx_cap_p = f"{usb}_TX_CAP_P"
    tx_cap_n = f"{usb}_TX_CAP_N"
    tx1_p = f"{usb}_TX1_P_CONN"
    tx1_n = f"{usb}_TX1_N_CONN"
    tx2_p = f"{usb}_TX2_P_CONN"
    tx2_n = f"{usb}_TX2_N_CONN"
    rx1_p = f"{usb}_RX1_P_CONN"
    rx1_n = f"{usb}_RX1_N_CONN"
    rx2_p = f"{usb}_RX2_P_CONN"
    rx2_n = f"{usb}_RX2_N_CONN"

    s.text(x0, y0, f"== {jref} USB-C downstream port {port} from VL822 ==")

    s.place(tps, "TPS25810RVC", f"TPS25810 Type-C DFP port {port}", x0 + 25.4, y0 + 48.26,
            footprint=FOOTPRINTS["TPS25810RVC"],
            pin_nets={
                "1": (f"{hub}_OC_N", "hier"),
                "2": ("SYS_5V", "hier"), "3": ("SYS_5V", "hier"),
                "4": ("SYS_5V", "hier"),
                "5": ("SYS_3V3", "hier"),
                "6": (f"{hub}_PE", "hier"),
                "7": ("GND", "local"), "8": ("GND", "local"),
                "9": ("GND", "local"), "10": (ref, "local"),
                "11": (cc1, "local"), "12": ("GND", "local"), "13": (cc2, "local"),
                "14": (vbus, "local"), "15": (vbus, "local"),
                "16": ("", "nc"), "17": ("", "nc"),
                "18": (pol, "local"),
                "19": (ufp, "local"),
                "20": (ld_det, "local"),
                "21": ("GND", "local"),
            })

    s.place(mux, "HD3SS6126", f"HD3SS6126 USB3 orientation mux {port}", x0 + 114.3, y0 + 50.8,
            footprint=FOOTPRINTS["HD3SS6126"],
            pin_nets={
                "1": ("", "nc"), "2": ("", "nc"), "3": ("", "nc"),
                "4": ("", "nc"), "5": ("", "nc"),
                "6": ("GND", "local"),
                "7": ("", "nc"), "8": ("", "nc"),
                "9": (pol, "local"),
                "10": ("GND", "local"),
                "11": ("", "nc"), "12": ("", "nc"),
                "13": ("SYS_3V3", "hier"),
                "14": ("GND", "local"),
                "15": ("", "nc"), "16": ("", "nc"),
                "17": ("GND", "local"), "18": ("", "nc"),
                "19": ("GND", "local"), "20": ("SYS_3V3", "hier"),
                "21": ("GND", "local"),
                "22": (rx2_n, "local"), "23": (rx2_p, "local"),
                "24": (rx1_n, "local"), "25": (rx1_p, "local"),
                "26": (tx2_n, "local"), "27": (tx2_p, "local"),
                "28": (tx1_n, "local"), "29": (tx1_p, "local"),
                "30": ("SYS_3V3", "hier"),
                "31": (tx_cap_p, "local"), "32": (tx_cap_n, "local"),
                "33": (f"{hub}_SSRX_P", "hier"), "34": (f"{hub}_SSRX_N", "hier"),
                "35": ("", "nc"), "36": ("", "nc"), "37": ("", "nc"),
                "38": ("", "nc"), "39": ("", "nc"), "40": ("", "nc"),
                "41": ("", "nc"), "42": ("", "nc"),
                "43": ("GND", "local"),
            })

    s.place(jref, "USB_C_Receptacle", f"USB-C downstream {port}", x0 + 220.98, y0 + 50.8,
            footprint=FOOTPRINTS["USB_C_Receptacle"],
            pin_nets={
                "A1": ("GND", "local"), "A12": ("GND", "local"),
                "B1": ("GND", "local"), "B12": ("GND", "local"),
                "SH": ("GND", "local"),
                "A4": (vbus, "local"), "A9": (vbus, "local"),
                "B4": (vbus, "local"), "B9": (vbus, "local"),
                "A5": (cc1, "local"), "B5": (cc2, "local"),
                "A6": (f"{hub}_DP", "hier"), "B6": (f"{hub}_DP", "hier"),
                "A7": (f"{hub}_DM", "hier"), "B7": (f"{hub}_DM", "hier"),
                "A2": (tx1_p, "local"), "A3": (tx1_n, "local"),
                "B2": (tx2_p, "local"), "B3": (tx2_n, "local"),
                "B11": (rx1_p, "local"), "B10": (rx1_n, "local"),
                "A11": (rx2_p, "local"), "A10": (rx2_n, "local"),
                "A8": ("", "nc"), "B8": ("", "nc"),
            })

    s.place(f"C{cbase}", "C", "10u TPS25810 IN", x0 + 55.88, y0 + 7.62, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 1}", "C", "100n TPS25810 IN", x0 + 55.88, y0 + 17.78, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 2}", "C", "100n AUX", x0 + 55.88, y0 + 27.94, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 3}", "C", "100n mux VDD", x0 + 149.86, y0 + 7.62, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 4}", "C", "100n mux VDD", x0 + 149.86, y0 + 17.78, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 5}", "C", "10u port VBUS", x0 + 261.62, y0 + 17.78, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": (vbus, "local"), "2": ("GND", "local")})

    s.place(f"C{cbase + 6}", "C", "100n USB3 TX AC", x0 + 88.9, y0 + 91.44, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": (f"{hub}_SSTX_P", "hier"), "2": (tx_cap_p, "local")})
    s.place(f"C{cbase + 7}", "C", "100n USB3 TX AC", x0 + 88.9, y0 + 101.6, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": (f"{hub}_SSTX_N", "hier"), "2": (tx_cap_n, "local")})

    s.place(f"R{rbase}", "R", "10k FAULT pull-up", x0 + 7.62, y0 + 91.44, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": (f"{hub}_OC_N", "hier")})
    s.place(f"R{rbase + 1}", "R", "10k POL pull-up", x0 + 7.62, y0 + 101.6, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": (pol, "local")})
    s.place(f"R{rbase + 2}", "R", "10k UFP pull-up", x0 + 7.62, y0 + 111.76, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": (ufp, "local")})
    s.place(f"R{rbase + 3}", "R", "10k LD_DET pull-up", x0 + 7.62, y0 + 121.92, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": (ld_det, "local")})
    s.place(f"R{rbase + 4}", "R", "100k REF", x0 + 55.88, y0 + 121.92, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (ref, "local"), "2": ("GND", "local")})

    esd4(s, esd_tx, "TPD4EUSB30 TX ESD", x0 + 302.26, y0 + 15.24,
         [tx1_p, tx1_n, tx2_p, tx2_n])
    esd4(s, esd_rx, "TPD4EUSB30 RX ESD", x0 + 302.26, y0 + 50.8,
         [rx1_p, rx1_n, rx2_p, rx2_n])
    esd4(s, esd_aux, "TPD4EUSB30 USB2/CC ESD", x0 + 302.26, y0 + 86.36,
         [f"{hub}_DP", f"{hub}_DM", cc1, cc2])

    s.gnd(x0 + 276.86, y0 + 121.92)
    s.text(x0, y0 + 134.62,
           f"{jref}: advertises standard USB current; TCP0 is now the external HDMI-A output on sheet 6.")


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 30
    s.refcounters["#FLG"] = 20

    s.text(20, 12.7, "== USB-C hub I/O: VL822 downstream ports only ==")
    s.text(20, 20.32, "TPS25810 handles DFP CC/VBUS; HD3SS6126 handles reversible SuperSpeed orientation.")
    s.text(20, 27.94, "CHG/CHG_HI are strapped low for standard USB current advertisement.")

    add_port(s, 1, 20.32, 43.18)
    add_port(s, 2, 20.32, 205.74)

    return s
