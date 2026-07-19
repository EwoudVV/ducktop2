from build_ducktop2 import Sheet, FOOTPRINTS


def esd4(s, ref, value, x, y, nets, *, usb3=True):
    """Place a 4-line ESD array on named local nets."""
    symbol = "TPD4E02B04DQA" if usb3 else "TPD4EUSB30"
    footprint = FOOTPRINTS["TPD4E02B04DQA"] if usb3 else FOOTPRINTS["TPD4E05U06DQA"]
    mpn = "TPD4E02B04DQAR" if usb3 else "TPD4E05U06DQAR"
    s.place(ref, symbol, value, x, y, footprint=footprint,
            pin_nets={
                "1": (nets[0], "local"), "2": (nets[1], "local"),
                "3": ("GND", "local"),
                "4": (nets[2], "local"), "5": (nets[3], "local"),
                "6": ("", "nc"), "7": ("", "nc"),
                "8": ("GND", "local"),
                "9": ("", "nc"), "10": ("", "nc"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": mpn})


def superspeed_esd(s, first_ref, x, y, nets):
    """Protect four SuperSpeed conductors with sub-0.18-pF shunt TVS parts."""
    for offset, net in enumerate(nets):
        s.place(
            f"D{first_ref + offset}", "D_TVS", "TPD1E0B04DPL USB3 ESD",
            x, y + offset * 10.16,
            footprint=FOOTPRINTS["TPD1E0B04DPL"],
            pin_nets={"1": (net, "local"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "Texas Instruments",
                "MPN": "TPD1E0B04DPLR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tpd1e0b04.pdf",
            },
        )


def add_port(s, port, x0, y0):
    native = f"USBC{port}"
    usb = f"USB{port}"
    jref = f"J{10 + port}"
    ubase = 10 + port * 10
    rbase = 70 + (port - 1) * 20
    cbase = 70 + (port - 1) * 20

    tps = f"U{ubase + 1}"
    branch_switch = f"U{ubase}"
    mux = f"U{ubase + 2}"
    esd_aux = f"U{ubase + 5}"
    esd_base = 210 if port == 1 else 230

    vbus = f"{usb}_VBUS"
    pre_vbus = f"{usb}_5V_PRE"
    ilim = f"{usb}_ILIM"
    cc1 = f"{usb}_CC1"
    cc2 = f"{usb}_CC2"
    pol = f"{usb}_POL_N"
    ref = f"{usb}_REF"
    ref_rtn = f"{usb}_REF_RTN"
    tx1_p = f"{usb}_TX1_P_CONN"
    tx1_n = f"{usb}_TX1_N_CONN"
    tx2_p = f"{usb}_TX2_P_CONN"
    tx2_n = f"{usb}_TX2_N_CONN"
    rx1_p = f"{usb}_RX1_P_CONN"
    rx1_n = f"{usb}_RX1_N_CONN"
    rx2_p = f"{usb}_RX2_P_CONN"
    rx2_n = f"{usb}_RX2_N_CONN"

    s.text(x0, y0, f"== {jref} native Mu USB 3.2 Gen 2 Type-C host port {port} ==")

    # TPS25810 requires at least 120 uF close to each IN supply, while the
    # TPS56637 shared rail supports a much smaller effective output-capacitance
    # range.  A current-limited branch switch isolates each 150 uF reservoir
    # from the shared converter and also removes branch power outside qualified S0.
    s.place(branch_switch, "TPS2553D", f"TPS2553DDBVR USB-C port {port} 1.3A branch switch",
            x0 + 25.4, y0 + 17.78, footprint=FOOTPRINTS["TPS2553DDBV"],
            pin_nets={
                "1": ("SYS_5V", "hier"), "2": ("GND", "local"),
                "3": ("MU_HOST_ACTIVE", "hier"), "4": ("MU_USB_OC_N", "hier"),
                "5": (ilim, "local"), "6": (pre_vbus, "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS2553DDBVR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps2553.pdf",
            })
    s.place(f"R{rbase}", "R", "20.0k 1% TPS2553 ILIM 1.3A nominal",
            x0 + 7.62, y0 + 88.9, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (ilim, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0720KL"})

    s.place(tps, "TPS25810RVC", f"TPS25810 Type-C DFP port {port}", x0 + 25.4, y0 + 48.26,
            footprint=FOOTPRINTS["TPS25810RVC"],
            pin_nets={
                "1": ("MU_USB_OC_N", "hier"),
                "2": (pre_vbus, "local"), "3": (pre_vbus, "local"),
                "4": (pre_vbus, "local"),
                "5": ("SYS_3V3", "hier"),
                "6": ("MU_HOST_ACTIVE", "hier"),
                "7": ("GND", "local"), "8": ("GND", "local"),
                "9": (ref_rtn, "local"), "10": (ref, "local"),
                "11": (cc1, "local"), "12": ("GND", "local"), "13": (cc2, "local"),
                "14": (vbus, "local"), "15": (vbus, "local"),
                "16": ("", "nc"), "17": ("", "nc"),
                "18": (pol, "local"),
                "19": ("", "nc"),
                "20": ("", "nc"),
                "21": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS25810RVCR"})

    s.place(mux, "HD3SS6126", f"HD3SS6126 USB3 orientation mux {port}", x0 + 114.3, y0 + 50.8,
            footprint=FOOTPRINTS["HD3SS6126"],
            pin_nets={
                "1": ("", "nc"), "2": ("", "nc"), "3": ("", "nc"),
                "4": ("", "nc"), "5": ("", "nc"),
                # HD3SS6126 HSA/HSB/HSC are the USB2 low-speed/full-speed/high-speed
                # path. USB2 D+/D- is already tied A/B-side at the Type-C receptacle,
                # so keep the mux's USB2 channel unused.
                # HS_OE is active low.  USB2 bypasses this device, so disable
                # the unused HSA/HSB/HSC path instead of leaving it powered.
                "6": ("SYS_3V3", "hier"),
                "7": ("", "nc"), "8": ("", "nc"),
                "9": (pol, "local"),
                "10": ("GND", "local"),
                # SuperSpeed Port A is the common Mu host side. Host TX was
                # AC-coupled on sheet 3; host RX remains direct.
                "11": (f"{native}_SSTX_P", "hier"), "12": (f"{native}_SSTX_N", "hier"),
                "13": ("SYS_3V3", "hier"),
                "14": ("GND", "local"),
                "15": (f"{native}_SSRX_P", "hier"), "16": (f"{native}_SSRX_N", "hier"),
                "17": ("GND", "local"), "18": ("", "nc"),
                "19": ("GND", "local"), "20": ("SYS_3V3", "hier"),
                "21": ("GND", "local"),
                # TPS25810 ~POL is high/Hi-Z for CC1 and low for CC2.
                # HD3SS6126 SEL=1 selects C and SEL=0 selects B, so C carries
                # connector lane set 1 and B carries connector lane set 2.
                "22": (rx1_n, "local"), "23": (rx1_p, "local"),
                "24": (tx1_n, "local"), "25": (tx1_p, "local"),
                "26": (rx2_n, "local"), "27": (rx2_p, "local"),
                "28": (tx2_n, "local"), "29": (tx2_p, "local"),
                "30": ("SYS_3V3", "hier"),
                "31": ("", "nc"), "32": ("", "nc"),
                "33": ("", "nc"), "34": ("", "nc"),
                "35": ("", "nc"), "36": ("", "nc"), "37": ("", "nc"),
                "38": ("", "nc"), "39": ("", "nc"), "40": ("", "nc"),
                "41": ("", "nc"), "42": ("", "nc"),
                "43": ("GND", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "HD3SS6126RUAR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/hd3ss6126.pdf",
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
                "A6": (f"{native}_DP", "hier"), "B6": (f"{native}_DP", "hier"),
                "A7": (f"{native}_DM", "hier"), "B7": (f"{native}_DM", "hier"),
                "A2": (tx1_p, "local"), "A3": (tx1_n, "local"),
                "B2": (tx2_p, "local"), "B3": (tx2_n, "local"),
                "B11": (rx1_p, "local"), "B10": (rx1_n, "local"),
                "A11": (rx2_p, "local"), "A10": (rx2_n, "local"),
                "A8": ("", "nc"), "B8": ("", "nc"),
            }, extra_props={"Manufacturer": "Molex", "MPN": "105450-0101"})

    s.place(f"C{cbase}", "C", "100n TPS2553 input bypass", x0 + 55.88, y0 + 7.62, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 1}", "C", "100n TPS25810 IN", x0 + 55.88, y0 + 17.78, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": (pre_vbus, "local"), "2": ("GND", "local")})
    s.place(f"C{cbase + 2}", "C", "100n AUX", x0 + 55.88, y0 + 27.94, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 3}", "C", "100n mux VDD", x0 + 149.86, y0 + 7.62, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 4}", "C", "100n mux VDD", x0 + 149.86, y0 + 17.78, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 6}", "C", "100n mux VDD (third supply pin)", x0 + 149.86, y0 + 27.94,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 7}", "C", "1u mux shared bulk", x0 + 149.86, y0 + 38.1,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 9}", "C", "10n mux high-frequency bypass", x0 + 149.86, y0 + 48.26,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place(f"C{cbase + 5}", "C", "10u port VBUS", x0 + 261.62, y0 + 17.78, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": (vbus, "local"), "2": ("GND", "local")})
    s.place(f"C{cbase + 8}", "C_Polarized", "150u 10V TPS25810 input reservoir", x0 + 55.88, y0 + 38.1,
            footprint="Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D",
            pin_nets={"1": (pre_vbus, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "KEMET", "MPN": "T520D157M010ATE025"})

    # Mu already provides the documented 10k USB_OC# pull-up internally.
    # TPS25810 POL is open drain, while HD3SS6126 SEL can draw 95uA high;
    # TI recommends 5k rather than the former 100k value.
    s.place(f"R{rbase + 1}", "R", "4.99k 1% POL pull-up", x0 + 7.62, y0 + 101.6, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": (pol, "local")})
    s.place(f"R{rbase + 4}", "R", "100k 1% <=100ppm REF", x0 + 55.88, y0 + 121.92, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (ref, "local"), "2": (ref_rtn, "local")})

    # The Mu guide recommends <0.18 pF per SuperSpeed conductor. TI's DPL
    # package is 0.13 pF typical/0.15 pF maximum and its datasheet shows this
    # exact eight-device Type-C topology. Keep each shunt path stubless at PCB
    # layout and give every device an immediate ground-via return.
    superspeed_esd(s, esd_base, x0 + 302.26, y0 + 5.08,
                   [tx1_p, tx1_n, tx2_p, tx2_n])
    superspeed_esd(s, esd_base + 4, x0 + 327.66, y0 + 5.08,
                   [rx1_p, rx1_n, rx2_p, rx2_n])
    esd4(s, esd_aux, "TPD4E05U06 USB2/CC ESD", x0 + 302.26, y0 + 86.36,
         [f"{native}_DP", f"{native}_DM", cc1, cc2], usb3=False)

    s.gnd(x0 + 276.86, y0 + 121.92)
    s.text(x0, y0 + 134.62,
           f"{jref}: native USB 10Gbps host, default-current advertisement; TCP0 is HDMI-A on sheet 6.")


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 30
    s.refcounters["#FLG"] = 20

    s.text(20, 12.7, "== Two native Mu USB 3.2 Gen 2 Type-C host ports ==")
    s.text(20, 20.32, "TPS25810 handles DFP CC/VBUS; TI rates the HD3SS6126 high-bandwidth path up to 10Gbps.")
    s.text(20, 27.94, "CHG/CHG_HI are strapped low for default USB current; branch-switch and port FAULT outputs share Mu USB_OC#.")
    s.text(20, 35.56, "Both ports use MU_HOST_ACTIVE = PSON AND MU_12V_PG; suspend or a failed Mu rail removes VBUS.")
    s.text(20, 43.18, "SYS_5V BUDGET HOLD: default-current ports still share one rail with trackpad, fan, audio, radios, and maker power; simultaneous-load validation/load shedding is mandatory.")

    add_port(s, 1, 20.32, 58.42)
    add_port(s, 2, 20.32, 220.98)

    return s
