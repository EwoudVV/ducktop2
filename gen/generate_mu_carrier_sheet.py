import os

import genlib
from build_ducktop2 import Sheet, U, PROJDIR, FOOTPRINTS, fmt_coord, snap_coord


def symbol_pins(name):
    _lib, text = genlib.load_renamed_symbol(name)
    return genlib.parse_pins(text)


def default_pin_map(symname, power_3v3_net="SYS_3V3"):
    nets = {}
    for num, pin in symbol_pins(symname).items():
        name = pin["name"]
        if name == "GND" or num == "MP":
            nets[num] = ("GND", "local")
        elif name in ("3.3V", "+3.3V"):
            nets[num] = (power_3v3_net, "local")
        elif name == "NC":
            nets[num] = ("", "nc")
        else:
            nets[num] = ("", "nc")
    return nets


def build(sheet_symbol_uuid, pwr_start=400, flg_start=400):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = pwr_start
    s.refcounters["#FLG"] = flg_start

    class Cur:
        def __init__(self, x0, y0, col_w=55, row_h=10, rows_per_col=20):
            self.x0, self.y0, self.col_w, self.row_h, self.rows = x0, y0, col_w, row_h, rows_per_col
            self.i = 0

        def next(self):
            col, row = divmod(self.i, self.rows)
            self.i += 1
            return (self.x0 + col * self.col_w, self.y0 + row * self.row_h)

    # ---------------- A1: LattePanda Mu module ----------------
    s.text(20, 20, "== A1 LattePanda Mu carrier core ==")
    mu_nets = default_pin_map("LattePanda_Mu")

    # Direct system power: BQ25798 VSYS is kept inside Mu's 9-20V VIN window.
    for pin in [str(n) for n in range(250, 261)]:
        mu_nets[pin] = ("VSYS", "hier")
    mu_nets["115"] = ("RTC_BAT", "local")

    # Local buttons and debug.
    mu_nets["1"] = ("MU_PWRBTN_N", "hier")
    mu_nets["3"] = ("MU_RSTBTN_N", "hier")
    mu_nets["10"] = ("MU_SIO_UART_TX", "local")
    mu_nets["12"] = ("MU_SIO_UART_RX", "local")

    # HSIO0 + USB2_P2 feed the VL822 upstream port.
    mu_nets.update({
        "13": ("HUB_UP_TX_P", "local"),
        "15": ("HUB_UP_TX_N", "local"),
        "16": ("HUB_UP_RX_P", "local"),
        "18": ("HUB_UP_RX_N", "local"),
        "73": ("HUB_UP_DM", "local"),
        "75": ("HUB_UP_DP", "local"),
    })

    # HSIO1 + USB2_P1 are reserved for the M.2 E-key Wi-Fi/Bluetooth module.
    mu_nets.update({
        "19": ("WIFI_PCIE_TX_P", "hier"),
        "21": ("WIFI_PCIE_TX_N", "hier"),
        "22": ("WIFI_PCIE_RX_P", "hier"),
        "24": ("WIFI_PCIE_RX_N", "hier"),
        "67": ("WIFI_USB_DN", "hier"),
        "69": ("WIFI_USB_DP", "hier"),
        "91": ("WIFI_REFCLK_P", "hier"),
        "93": ("WIFI_REFCLK_N", "hier"),
        "100": ("WIFI_CLKREQ_N", "hier"),
    })

    # Spare native USB2 ports become internal laptop service links.
    # USB2_P3 hosts the EC USB device; USB2_P4 hosts the internal touchscreen controller.
    # USB2_P5 hosts the internal USB radio audio codec; USB2_P7 hosts the maker MCU sandbox.
    # USB2_P8 hosts the internal trackpad so the OS sees a normal USB HID pointing device.
    mu_nets.update({
        "79": ("EC_HOST_USB_DM", "hier"),
        "81": ("EC_HOST_USB_DP", "hier"),
        "70": ("TOUCH_USB_DP", "hier"),
        "72": ("TOUCH_USB_DM", "hier"),
        "109": ("AUDIO_USB_DM", "hier"),
        "111": ("AUDIO_USB_DP", "hier"),
        "76": ("MAKER_USB_DP", "hier"),
        "78": ("MAKER_USB_DM", "hier"),
        "82": ("TRACKPAD_USB_DP", "hier"),
        "84": ("TRACKPAD_USB_DM", "hier"),
    })

    # DDIB is the Mu default HDMI 2.0 output; it feeds the retained Intehill monitor controller path.
    mu_nets.update({
        "169": ("DDIB_DDC_SDA", "hier"),
        "171": ("DDIB_DDC_SCL", "hier"),
        "183": ("DDIB_HPD", "hier"),
        "197": ("DDIB_TX3_N", "hier"),
        "199": ("DDIB_TX3_P", "hier"),
        "203": ("DDIB_TX2_N", "hier"),
        "205": ("DDIB_TX2_P", "hier"),
        "209": ("DDIB_TX1_N", "hier"),
        "211": ("DDIB_TX1_P", "hier"),
        "215": ("DDIB_TX0_N", "hier"),
        "217": ("DDIB_TX0_P", "hier"),
    })

    # NVMe M-key slot, one PCIe lane. CLKREQM is intentionally not wired.
    mu_nets.update({
        "25": ("PCIE_M_TX_P", "local"),
        "27": ("PCIE_M_TX_N", "local"),
        "28": ("PCIE_M_RX_P", "local"),
        "30": ("PCIE_M_RX_N", "local"),
        "85": ("PCIE_M_REFCLK_SRC_P", "local"),
        "87": ("PCIE_M_REFCLK_SRC_N", "local"),
        "103": ("PCIE_WAKE_N", "hier"),
        "105": ("PLTRST_SRC_N", "hier"),
    })

    # TCP0 is the second default-BIOS HDMI 2.0 output; it leaves to sheet 6 for the external HDMI-A jack.
    mu_nets.update({
        "177": ("TCP0_DDC_SDA", "hier"),
        "179": ("TCP0_DDC_SCL", "hier"),
        "187": ("TCP0_HPD", "hier"),
        "227": ("TCP0_TXRX1_N", "hier"),
        "229": ("TCP0_TXRX1_P", "hier"),
        "233": ("TCP0_TX1_N", "hier"),
        "235": ("TCP0_TX1_P", "hier"),
        "239": ("TCP0_TXRX0_N", "hier"),
        "241": ("TCP0_TXRX0_P", "hier"),
        "245": ("TCP0_TX0_N", "hier"),
        "247": ("TCP0_TX0_P", "hier"),
    })

    s.place("A1", "LattePanda_Mu", "LattePanda Mu", 160, 180,
            footprint=FOOTPRINTS["LattePanda_Mu"], pin_nets=mu_nets)

    s.place("SW2", "SW_Push", "Mu Power", 30, 50, footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MU_PWRBTN_N", "local"), "2": ("GND", "local")})
    s.place("SW3", "SW_Push", "Mu Reset", 30, 70, footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MU_RSTBTN_N", "local"), "2": ("GND", "local")})
    s.place("J8", "Conn_01x04", "Mu SIO UART debug (verify IO voltage)", 30, 100,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={"1": ("GND", "local"), "2": ("MU_SIO_UART_TX", "local"),
                      "3": ("MU_SIO_UART_RX", "local"), "4": ("GND", "local")})
    s.place("J9", "Conn_01x02", "RTC backup coin-cell header", 30, 130,
            footprint=FOOTPRINTS["Conn_01x02_Header"],
            pin_nets={"1": ("RTC_BAT", "local"), "2": ("GND", "local")})
    s.gnd(30, 160)
    s.pwrflag(30, 180, "RTC_BAT")

    # ---------------- U6/U7: local buck rails ----------------
    s.text(300, 20, "== Local carrier rails from VSYS ==")
    p = Cur(300, 45)
    for ref, rail, sw, fb, boot, value, l_value, r_hi, r_lo in [
        ("U6", "SYS_5V", "BUCK5_SW", "BUCK5_FB", "BUCK5_BOOT",
         "SY8253ADC VSYS -> SYS_5V", "2.2uH >=4.3A", "732k 1%", "100k 1%"),
        ("U7", "SYS_3V3", "BUCK33_SW", "BUCK33_FB", "BUCK33_BOOT",
         "SY8253ADC VSYS -> SYS_3V3", "2.2uH >=4.3A", "450k 1%", "100k 1%"),
    ]:
        s.place(ref, "SY8253ADC", value, *p.next(), footprint=FOOTPRINTS["SY8253ADC"],
                pin_nets={"1": (boot, "local"), "2": ("GND", "local"), "3": (fb, "local"),
                          "4": ("VSYS", "hier"), "5": ("VSYS", "hier"), "6": (sw, "local")})
        s.place(f"C{40 if ref == 'U6' else 46}", "C", "10u VIN", *p.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
        s.place(f"C{41 if ref == 'U6' else 47}", "C", "100n BOOT", *p.next(), footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (boot, "local"), "2": (sw, "local")})
        s.place(f"L{4 if ref == 'U6' else 5}", "L", l_value, *p.next(), footprint=FOOTPRINTS["L_buck"],
                pin_nets={"1": (sw, "local"), "2": (rail, "hier")})
        s.place(f"R{40 if ref == 'U6' else 43}", "R", r_hi, *p.next(), footprint=FOOTPRINTS["R"],
                pin_nets={"1": (rail, "local"), "2": (fb, "local")})
        s.place(f"R{41 if ref == 'U6' else 44}", "R", r_lo, *p.next(), footprint=FOOTPRINTS["R"],
                pin_nets={"1": (fb, "local"), "2": ("GND", "local")})
        s.place(f"C{42 if ref == 'U6' else 48}", "C", "22u OUT", *p.next(), footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": (rail, "local"), "2": ("GND", "local")})

    s.place("U8", "TPS7A0210", "TPS7A0210 (VL822 1.0V)", 520, 45,
            footprint=FOOTPRINTS["TPS7A0210"],
            pin_nets={"1": ("HUB_1V0", "local"), "2": ("GND", "local"),
                      "3": ("SYS_3V3", "local"), "4": ("SYS_3V3", "local"),
                      "5": ("GND", "local")})
    s.place("C52", "C", "1u IN", 520, 70, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("SYS_3V3", "local"), "2": ("GND", "local")})
    s.place("C53", "C", "1u OUT", 520, 80, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("HUB_1V0", "local"), "2": ("GND", "local")})
    s.gnd(520, 100)
    s.pwrflag(540, 100, "SYS_5V")
    s.pwrflag(560, 100, "SYS_3V3")

    # ---------------- U9: VL822 hub ----------------
    s.text(300, 250, "== U9 VL822-Q7 USB3 hub, upstream on Mu HSIO0/USB2_P2 ==")
    hub = default_pin_map("VL822-Q7")
    for num, pin in symbol_pins("VL822-Q7").items():
        if pin["name"] in ("VCC10I", "VDD"):
            hub[num] = ("HUB_1V0", "local")
        elif pin["name"] == "VCC33I":
            hub[num] = ("SYS_3V3", "local")

    hub.update({
        "43": ("HUB_UP_VBUS_DET", "local"),
        "49": ("HUB_UP_RX_N", "local"),
        "50": ("HUB_UP_RX_P", "local"),
        "52": ("HUB_UP_TX_N", "local"),
        "53": ("HUB_UP_TX_P", "local"),
        "55": ("HUB_UP_DP", "local"),
        "56": ("HUB_UP_DM", "local"),
        "68": ("PLTRST_SRC_N", "local"),
        "74": ("GND", "local"),
        "47": ("HUB_REXT", "local"),
        "44": ("HUB_XO", "local"),
        "45": ("HUB_XI", "local"),
        "1": ("HUB1_OC_N", "hier"),
        "2": ("HUB1_PE", "hier"),
        "3": ("HUB1_SSTX_P", "hier"),
        "4": ("HUB1_SSTX_N", "hier"),
        "6": ("HUB1_SSRX_P", "hier"),
        "7": ("HUB1_SSRX_N", "hier"),
        "9": ("HUB1_DP", "hier"),
        "10": ("HUB1_DM", "hier"),
        "75": ("HUB2_OC_N", "hier"),
        "76": ("HUB2_PE", "hier"),
        "12": ("HUB2_SSTX_P", "hier"),
        "13": ("HUB2_SSTX_N", "hier"),
        "15": ("HUB2_SSRX_P", "hier"),
        "16": ("HUB2_SSRX_N", "hier"),
        "18": ("HUB2_DP", "hier"),
        "19": ("HUB2_DM", "hier"),
    })
    s.place("U9", "VL822-Q7", "VL822-Q7", 400, 350,
            footprint=FOOTPRINTS["VL822-Q7"], pin_nets=hub)

    q = Cur(560, 250)
    for i in range(6):
        s.place(f"C{54+i}", "C", "100n hub bypass", *q.next(), footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("SYS_3V3", "local"), "2": ("GND", "local")})
    for i in range(4):
        s.place(f"C{60+i}", "C", "100n hub 1V0 bypass", *q.next(), footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("HUB_1V0", "local"), "2": ("GND", "local")})
    s.place("Y3", "Crystal_GND24", "25MHz (VL822)", *q.next(), footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={"1": ("HUB_XI", "local"), "2": ("GND", "local"), "3": ("HUB_XO", "local")})
    q.next()
    s.place("C64", "C", "18p", *q.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HUB_XI", "local"), "2": ("GND", "local")})
    s.place("C65", "C", "18p", *q.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HUB_XO", "local"), "2": ("GND", "local")})
    s.place("R45", "R", "12.1k (verify VL822 REXT)", *q.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("HUB_REXT", "local"), "2": ("GND", "local")})
    s.place("R46", "R", "100k", *q.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "local"), "2": ("HUB_UP_VBUS_DET", "local")})

    # ---------------- J10: M.2 M-key NVMe slot ----------------
    s.text(300, 520, "== J10 M.2 M-key NVMe, PCIe x1 only ==")
    s.place("R47", "R", "0R / PERST isolation", 300, 545, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PLTRST_SRC_N", "local"), "2": ("PCIE_M_PERST_N", "local")})
    s.place("R48", "R", "0R / REFCLK+ isolation", 300, 555, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PCIE_M_REFCLK_SRC_P", "local"), "2": ("PCIE_M_REFCLK_P", "local")})
    s.place("R49", "R", "0R / REFCLK- isolation", 300, 565, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PCIE_M_REFCLK_SRC_N", "local"), "2": ("PCIE_M_REFCLK_N", "local")})
    m2m = default_pin_map("Bus_M.2_Socket_M")
    m2m.update({
        "41": ("PCIE_M_TX_N", "local"),
        "43": ("PCIE_M_TX_P", "local"),
        "47": ("PCIE_M_RX_N", "local"),
        "49": ("PCIE_M_RX_P", "local"),
        "53": ("PCIE_M_REFCLK_N", "local"),
        "55": ("PCIE_M_REFCLK_P", "local"),
        "50": ("PCIE_M_PERST_N", "local"),
        "54": ("PCIE_WAKE_N", "local"),
        "52": ("", "nc"),
    })
    s.place("J10", "Bus_M.2_Socket_M", "M.2 M-key NVMe (x1)", 440, 620,
            footprint=FOOTPRINTS["M2_M_key"], pin_nets=m2m)

    s.text(20, 330, "NOTES:")
    s.text(20, 338, "Mu VIN is tied directly to VSYS; no intermediate module VIN buck.")
    s.text(20, 346, "HSIO0 + USB2_P2 feed VL822 upstream; HSIO1 + USB2_P1 feed the M.2 E-key radio slot.")
    s.text(20, 354, "DDIB HDMI 2.0 nets leave to sheet 11 for the retained Intehill monitor/controller path.")
    s.text(20, 362, "TCP0 HDMI 2.0 lane/HPD/DDC nets leave to sheet 6 for the external HDMI-A output.")
    s.text(20, 370, "USB2_P3 is EC; USB2_P4 is touch; USB2_P5 is radio audio; USB2_P7 is maker MCU USB; USB2_P8 is trackpad.")
    s.text(20, 378, "VL822 downstream PE/OC/data leave this sheet; USB-C VBUS/CC/muxing lives on sheet 4.")
    s.text(20, 386, "SYS_5V/SYS_3V3 use 0.6V FB dividers: 732k/100k and 450k/100k; verify compensation before fab.")
    s.text(20, 393.7, "TPS7A0210 is a real 1.0V part, but sits at the low edge of the VL822 1.0-1.1V rail range.")
    s.text(20, 401.32, "M.2 M-key is wired as PCIe x1. CLKREQM is intentionally left NC per DFRobot reference mining.")
    s.text(20, 408.94, "USB2_P6 is reserved for the Mu Type-C PD controller direction; trackpad consumes the former USB2_P8 spare.")

    return s


def sheet_block(uuid_, x, y, w, h, name, filename, pins):
    x = snap_coord(x)
    y = snap_coord(y)
    w = snap_coord(w)
    h = snap_coord(h)
    pins_sexpr = []
    pin_coords = {}
    for i, pin_name in enumerate(pins):
        py = snap_coord(y + 5.08 + i * 5.08)
        px = snap_coord(x + w)
        pin_coords[pin_name] = (px, py)
        pins_sexpr.append(
            f'  (pin "{pin_name}" bidirectional\n'
            f'    (at {fmt_coord(px)} {fmt_coord(py)} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left))\n'
            f'    (uuid {U()})\n'
            f'  )'
        )
    block = (
        f'(sheet\n'
        f'  (at {fmt_coord(x)} {fmt_coord(y)})\n'
        f'  (size {fmt_coord(w)} {fmt_coord(h)})\n'
        f'  (stroke (width 0.1524) (type solid))\n'
        f'  (fill (color 0 0 0 0.0))\n'
        f'  (uuid {uuid_})\n'
        f'  (property "Sheetname" "{name}"\n'
        f'    (at {fmt_coord(x)} {fmt_coord(y - 1.27)} 0)\n'
        f'    (effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'  )\n'
        f'  (property "Sheetfile" "{filename}"\n'
        f'    (at {fmt_coord(x)} {fmt_coord(y + h + 1.27)} 0)\n'
        f'    (effects (font (size 1.27 1.27)) (justify left top))\n'
        f'  )\n'
        + "\n".join(pins_sexpr) + "\n"
        f')'
    )
    return block, pin_coords


def wire_between(a, b):
    x1, y1 = (snap_coord(a[0]), snap_coord(a[1]))
    x2, y2 = (snap_coord(b[0]), snap_coord(b[1]))
    segments = []
    if y1 == y2:
        points = [(x1, y1), (x2, y2)]
    else:
        mid = snap_coord(max(x1, x2) + 10.16)
        points = [(x1, y1), (mid, y1), (mid, y2), (x2, y2)]
    for start, end in zip(points, points[1:]):
        sx, sy = start
        ex, ey = end
        segments.append(
            f'(wire\n'
            f'  (pts (xy {fmt_coord(sx)} {fmt_coord(sy)}) (xy {fmt_coord(ex)} {fmt_coord(ey)}))\n'
            f'  (stroke (width 0) (type default))\n'
            f'  (uuid {U()})\n'
            f')'
        )
    return "\n".join(segments)


def root_no_connect(coord):
    x, y = coord
    return f'(no_connect (at {fmt_coord(x)} {fmt_coord(y)}) (uuid {U()}))'


def root_label(coord, name):
    x, y = coord
    return (
        f'(label "{name}"\n'
        f'  (at {fmt_coord(x)} {fmt_coord(y)} 0)\n'
        f'  (effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'  (uuid {U()})\n'
        f')'
    )


def main():
    import generate_power_sheet as ps
    import generate_ec_mcu_sheet as ec
    import generate_usb_c_io_sheet as usb
    import generate_power_inputs_sheet as pwrin
    import generate_tcp0_external_hdmi_sheet as tcp0
    import generate_radio_oled_gps_sheet as radio
    import generate_internal_services_sheet as internal
    import generate_ham_radio_sheet as ham
    import generate_internal_display_sheet as display
    import generate_intehill_monitor_interface_sheet as intehill
    import generate_keyboard_daughterboard_sheet as keyboard
    import generate_radio_audio_codec_sheet as audio
    import generate_maker_mcu_sheet as maker

    power_sheet_uuid = U()
    ec_sheet_uuid = U()
    mu_sheet_uuid = U()
    usb_sheet_uuid = U()
    pwrin_sheet_uuid = U()
    tcp0_sheet_uuid = U()
    radio_sheet_uuid = U()
    internal_sheet_uuid = U()
    ham_sheet_uuid = U()
    display_sheet_uuid = U()
    intehill_sheet_uuid = U()
    keyboard_sheet_uuid = U()
    audio_sheet_uuid = U()
    maker_sheet_uuid = U()

    power_s = ps.build(power_sheet_uuid)
    power_text = power_s.render(U(), page_number="2")
    with open(os.path.join(PROJDIR, "01_power_battery.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(power_text)

    ec_s = ec.build(ec_sheet_uuid)
    ec_text = ec_s.render(U(), page_number="3")
    with open(os.path.join(PROJDIR, "02_ec_mcu.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(ec_text)

    mu_s = build(mu_sheet_uuid)
    mu_text = mu_s.render(U(), page_number="4")
    with open(os.path.join(PROJDIR, "03_mu_carrier.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(mu_text)

    usb_s = usb.build(usb_sheet_uuid)
    usb_text = usb_s.render(U(), page_number="5")
    with open(os.path.join(PROJDIR, "04_usb_c_io.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(usb_text)

    pwrin_s = pwrin.build(pwrin_sheet_uuid)
    pwrin_text = pwrin_s.render(U(), page_number="6")
    with open(os.path.join(PROJDIR, "05_power_inputs.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(pwrin_text)

    tcp0_s = tcp0.build(tcp0_sheet_uuid)
    tcp0_text = tcp0_s.render(U(), page_number="7")
    with open(os.path.join(PROJDIR, "06_tcp0_external_hdmi.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(tcp0_text)

    radio_s = radio.build(radio_sheet_uuid)
    radio_text = radio_s.render(U(), page_number="8")
    with open(os.path.join(PROJDIR, "07_radio_oled_gps.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(radio_text)

    internal_s = internal.build(internal_sheet_uuid)
    internal_text = internal_s.render(U(), page_number="9")
    with open(os.path.join(PROJDIR, "08_internal_services.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(internal_text)

    ham_s = ham.build(ham_sheet_uuid)
    ham_text = ham_s.render(U(), page_number="10")
    with open(os.path.join(PROJDIR, "09_ham_radio.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(ham_text)

    display_s = display.build(display_sheet_uuid)
    display_text = display_s.render(U(), page_number="11")
    with open(os.path.join(PROJDIR, "10_internal_display.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(display_text)

    intehill_s = intehill.build(intehill_sheet_uuid)
    intehill_text = intehill_s.render(U(), page_number="12")
    with open(os.path.join(PROJDIR, "11_intehill_monitor_interface.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(intehill_text)

    keyboard_s = keyboard.build(keyboard_sheet_uuid)
    keyboard_text = keyboard_s.render(U(), page_number="13")
    with open(os.path.join(PROJDIR, "12_keyboard_daughterboard.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(keyboard_text)

    audio_s = audio.build(audio_sheet_uuid)
    audio_text = audio_s.render(U(), page_number="14")
    with open(os.path.join(PROJDIR, "13_radio_audio_codec.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(audio_text)

    maker_s = maker.build(maker_sheet_uuid)
    maker_text = maker_s.render(U(), page_number="15")
    with open(os.path.join(PROJDIR, "14_maker_mcu.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(maker_text)

    power_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "MCU_3V3", "AUX_DC_ADC", "VBUS_PD1", "VBUS_PD2", "VBUS_PD3", "USB_DP1", "USB_DM1",
    ]
    ec_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "MCU_USB_DP", "MCU_USB_DM", "MCU_3V3", "AUX_DC_ADC", "MU_PWRBTN_N", "MU_RSTBTN_N",
        "WIFI_W_DISABLE1_N", "WIFI_W_DISABLE2_N", "OLED_RESET_N",
        "GNSS_UART_RX", "GNSS_UART_TX", "GNSS_RESET_N", "GNSS_PPS", "GNSS_EXTINT",
        "RADIO_GPIO0",
        "FAN_PWM", "FAN_TACH", "LCD_BL_PWM", "LCD_BL_EN", "LID_CLOSED_N",
        "THERM_SKIN_ADC", "THERM_MU_ADC", "TOUCH_RESET_N", "TOUCH_INT_N", "PANEL_PWR_EN", "PANEL_RESET_N",
        "TPAD_RESET_N", "TPAD_INT_N",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N", "RADIO_VHF_PD_N", "RADIO_UHF_PD_N",
        "RADIO_VHF_SQL", "RADIO_UHF_SQL", "RADIO_VHF_RF_SEL", "RADIO_UHF_RF_SEL", "RADIO_AUDIO_SEL",
        "KB_ROW0", "KB_ROW1", "KB_ROW2", "KB_ROW3", "KB_ROW4", "KB_ROW5", "KB_ROW6", "KB_ROW7",
        "KB_COL0", "KB_COL1", "KB_COL2", "KB_COL3", "KB_COL4", "KB_COL5", "KB_COL6", "KB_COL7",
        "KB_COL8", "KB_COL9", "KB_COL10", "KB_COL11", "KB_COL12", "KB_COL13", "KB_COL14", "KB_COL15",
    ]
    mu_hier_nets = [
        "VSYS", "SYS_5V", "SYS_3V3", "MU_PWRBTN_N", "MU_RSTBTN_N",
        "EC_HOST_USB_DP", "EC_HOST_USB_DM", "TOUCH_USB_DP", "TOUCH_USB_DM", "AUDIO_USB_DP", "AUDIO_USB_DM",
        "TRACKPAD_USB_DP", "TRACKPAD_USB_DM",
        "MAKER_USB_DP", "MAKER_USB_DM",
        "HUB1_PE", "HUB1_OC_N", "HUB1_SSTX_P", "HUB1_SSTX_N", "HUB1_SSRX_P", "HUB1_SSRX_N", "HUB1_DP", "HUB1_DM",
        "HUB2_PE", "HUB2_OC_N", "HUB2_SSTX_P", "HUB2_SSTX_N", "HUB2_SSRX_P", "HUB2_SSRX_N", "HUB2_DP", "HUB2_DM",
        "TCP0_DDC_SDA", "TCP0_DDC_SCL", "TCP0_HPD",
        "TCP0_TX0_P", "TCP0_TX0_N", "TCP0_TX1_P", "TCP0_TX1_N",
        "TCP0_TXRX0_P", "TCP0_TXRX0_N", "TCP0_TXRX1_P", "TCP0_TXRX1_N",
        "DDIB_DDC_SDA", "DDIB_DDC_SCL", "DDIB_HPD",
        "DDIB_TX0_P", "DDIB_TX0_N", "DDIB_TX1_P", "DDIB_TX1_N",
        "DDIB_TX2_P", "DDIB_TX2_N", "DDIB_TX3_P", "DDIB_TX3_N",
        "WIFI_PCIE_TX_P", "WIFI_PCIE_TX_N", "WIFI_PCIE_RX_P", "WIFI_PCIE_RX_N",
        "WIFI_USB_DN", "WIFI_USB_DP", "WIFI_REFCLK_P", "WIFI_REFCLK_N",
        "WIFI_CLKREQ_N", "PCIE_WAKE_N", "PLTRST_SRC_N",
    ]
    usb_hier_nets = [
        "SYS_5V", "SYS_3V3",
        "HUB1_PE", "HUB1_OC_N", "HUB1_SSTX_P", "HUB1_SSTX_N", "HUB1_SSRX_P", "HUB1_SSRX_N", "HUB1_DP", "HUB1_DM",
        "HUB2_PE", "HUB2_OC_N", "HUB2_SSTX_P", "HUB2_SSTX_N", "HUB2_SSRX_P", "HUB2_SSRX_N", "HUB2_DP", "HUB2_DM",
    ]
    pwrin_hier_nets = [
        "VBUS_PD1", "VBUS_PD2", "VBUS_PD3", "USB_DP1", "USB_DM1",
    ]
    tcp0_hier_nets = [
        "SYS_5V", "TCP0_HPD", "TCP0_DDC_SDA", "TCP0_DDC_SCL",
        "TCP0_TX0_P", "TCP0_TX0_N", "TCP0_TX1_P", "TCP0_TX1_N",
        "TCP0_TXRX0_P", "TCP0_TXRX0_N", "TCP0_TXRX1_P", "TCP0_TXRX1_N",
    ]
    radio_hier_nets = [
        "SYS_3V3", "MCU_3V3", "I2C_SCL", "I2C_SDA",
        "WIFI_PCIE_TX_P", "WIFI_PCIE_TX_N", "WIFI_PCIE_RX_P", "WIFI_PCIE_RX_N",
        "WIFI_USB_DN", "WIFI_USB_DP", "WIFI_REFCLK_P", "WIFI_REFCLK_N",
        "WIFI_CLKREQ_N", "PCIE_WAKE_N", "PLTRST_SRC_N",
        "WIFI_W_DISABLE1_N", "WIFI_W_DISABLE2_N",
        "OLED_RESET_N", "GNSS_UART_RX", "GNSS_UART_TX", "GNSS_RESET_N",
        "GNSS_PPS", "GNSS_EXTINT", "RADIO_GPIO0",
    ]
    internal_hier_nets = [
        "SYS_5V", "SYS_3V3", "MCU_3V3", "I2C_SCL", "I2C_SDA",
        "EC_HOST_USB_DP", "EC_HOST_USB_DM", "MCU_USB_DP", "MCU_USB_DM",
        "TOUCH_USB_DP", "TOUCH_USB_DM", "TOUCH_RESET_N", "TOUCH_INT_N",
        "TRACKPAD_USB_DP", "TRACKPAD_USB_DM", "TPAD_RESET_N", "TPAD_INT_N",
        "FAN_PWM", "FAN_TACH", "LCD_BL_PWM", "LCD_BL_EN", "LID_CLOSED_N",
        "THERM_SKIN_ADC", "THERM_MU_ADC", "PANEL_PWR_EN", "PANEL_RESET_N",
    ]
    ham_hier_nets = [
        "SYS_5V", "MCU_3V3",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N", "RADIO_VHF_PD_N", "RADIO_UHF_PD_N",
        "RADIO_VHF_SQL", "RADIO_UHF_SQL", "RADIO_VHF_RF_SEL", "RADIO_UHF_RF_SEL",
        "RADIO_AUDIO_SEL", "RADIO_GPIO0",
        "RADIO_VHF_AUDIO_OUT", "RADIO_UHF_AUDIO_OUT", "RADIO_VHF_MIC_IN", "RADIO_UHF_MIC_IN",
    ]
    display_hier_nets = [
        "VSYS", "SYS_3V3", "MCU_3V3", "I2C_SCL", "I2C_SDA",
        "LCD_BL_PWM", "LCD_BL_EN", "PANEL_PWR_EN", "PANEL_RESET_N",
        "TOUCH_RESET_N", "TOUCH_INT_N",
    ]
    intehill_hier_nets = [
        "SYS_5V", "PANEL_PWR_EN", "TOUCH_USB_DP", "TOUCH_USB_DM",
        "DDIB_DDC_SDA", "DDIB_DDC_SCL", "DDIB_HPD",
        "DDIB_TX0_P", "DDIB_TX0_N", "DDIB_TX1_P", "DDIB_TX1_N",
        "DDIB_TX2_P", "DDIB_TX2_N", "DDIB_TX3_P", "DDIB_TX3_N",
    ]
    keyboard_hier_nets = [
        "MCU_3V3", "SYS_5V", "I2C_SCL", "I2C_SDA",
        "KB_ROW0", "KB_ROW1", "KB_ROW2", "KB_ROW3", "KB_ROW4", "KB_ROW5", "KB_ROW6", "KB_ROW7",
        "KB_COL0", "KB_COL1", "KB_COL2", "KB_COL3", "KB_COL4", "KB_COL5", "KB_COL6", "KB_COL7",
        "KB_COL8", "KB_COL9", "KB_COL10", "KB_COL11", "KB_COL12", "KB_COL13", "KB_COL14", "KB_COL15",
    ]
    audio_hier_nets = [
        "SYS_5V", "AUDIO_USB_DP", "AUDIO_USB_DM",
        "RADIO_VHF_AUDIO_OUT", "RADIO_UHF_AUDIO_OUT", "RADIO_VHF_MIC_IN", "RADIO_UHF_MIC_IN",
    ]
    maker_hier_nets = [
        "SYS_5V", "MAKER_USB_DP", "MAKER_USB_DM",
    ]

    power_block, power_pins = sheet_block(
        power_sheet_uuid, 30, 40, 60, 80, "Power & Battery", "01_power_battery.kicad_sch",
        power_hier_nets,
    )
    ec_block, ec_pins = sheet_block(
        ec_sheet_uuid, 160, 40, 60, 400, "EC & MCU", "02_ec_mcu.kicad_sch",
        ec_hier_nets,
    )
    mu_block, mu_pins = sheet_block(
        mu_sheet_uuid, 290, 40, 70, 340, "Mu Carrier", "03_mu_carrier.kicad_sch",
        mu_hier_nets,
    )
    usb_block, usb_pins = sheet_block(
        usb_sheet_uuid, 30, 150, 90, 125, "USB-C Hub I/O", "04_usb_c_io.kicad_sch",
        usb_hier_nets,
    )
    pwrin_block, pwrin_pins = sheet_block(
        pwrin_sheet_uuid, 30, 300, 90, 60, "Power Inputs", "05_power_inputs.kicad_sch",
        pwrin_hier_nets,
    )
    tcp0_block, tcp0_pins = sheet_block(
        tcp0_sheet_uuid, 420, 40, 105, 80, "TCP0 External HDMI", "06_tcp0_external_hdmi.kicad_sch",
        tcp0_hier_nets,
    )
    radio_block, radio_pins = sheet_block(
        radio_sheet_uuid, 30, 380, 105, 155, "Radio/OLED/GNSS", "07_radio_oled_gps.kicad_sch",
        radio_hier_nets,
    )
    internal_block, internal_pins = sheet_block(
        internal_sheet_uuid, 290, 390, 115, 155, "Internal Services", "08_internal_services.kicad_sch",
        internal_hier_nets,
    )
    ham_block, ham_pins = sheet_block(
        ham_sheet_uuid, 420, 220, 115, 170, "Ham Radio", "09_ham_radio.kicad_sch",
        ham_hier_nets,
    )
    display_block, display_pins = sheet_block(
        display_sheet_uuid, 550, 40, 115, 110, "Internal Display", "10_internal_display.kicad_sch",
        display_hier_nets,
    )
    intehill_block, intehill_pins = sheet_block(
        intehill_sheet_uuid, 550, 180, 125, 125, "Intehill Monitor Interface", "11_intehill_monitor_interface.kicad_sch",
        intehill_hier_nets,
    )
    keyboard_block, keyboard_pins = sheet_block(
        keyboard_sheet_uuid, 420, 410, 120, 170, "Keyboard Daughterboard", "12_keyboard_daughterboard.kicad_sch",
        keyboard_hier_nets,
    )
    audio_block, audio_pins = sheet_block(
        audio_sheet_uuid, 550, 330, 125, 85, "Radio Audio Codec", "13_radio_audio_codec.kicad_sch",
        audio_hier_nets,
    )
    maker_block, maker_pins = sheet_block(
        maker_sheet_uuid, 550, 440, 125, 45, "Maker MCU", "14_maker_mcu.kicad_sch",
        maker_hier_nets,
    )

    root_labels = []
    seen_root_labels = set()

    def add_root_label(pins, net):
        coord = pins[net]
        key = (coord[0], coord[1], net)
        if key not in seen_root_labels:
            root_labels.append(root_label(coord, net))
            seen_root_labels.add(key)

    for net in [n for n in ec_hier_nets if n in power_hier_nets]:
        add_root_label(power_pins, net)
        add_root_label(ec_pins, net)
    add_root_label(power_pins, "VSYS")
    add_root_label(mu_pins, "VSYS")
    for net in ["MU_PWRBTN_N", "MU_RSTBTN_N"]:
        add_root_label(ec_pins, net)
        add_root_label(mu_pins, net)
    for net in usb_hier_nets:
        add_root_label(mu_pins, net)
        add_root_label(usb_pins, net)
    for net in pwrin_hier_nets:
        add_root_label(power_pins, net)
        add_root_label(pwrin_pins, net)
    for net in tcp0_hier_nets:
        add_root_label(tcp0_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in radio_hier_nets:
        add_root_label(radio_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in internal_hier_nets:
        add_root_label(internal_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in ham_hier_nets:
        add_root_label(ham_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in display_hier_nets:
        add_root_label(display_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in intehill_hier_nets:
        add_root_label(intehill_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in internal_hier_nets:
            add_root_label(internal_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in keyboard_hier_nets:
        add_root_label(keyboard_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in audio_hier_nets:
        add_root_label(audio_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ham_hier_nets:
            add_root_label(ham_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in maker_hier_nets:
        add_root_label(maker_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)

    root_ncs = []
    root_text = (
        f'(kicad_sch\n'
        f'  (version 20260306)\n'
        f'  (generator "eeschema")\n'
        f'  (generator_version "10.0")\n'
        f'  (uuid {U()})\n'
        f'  (paper "A1")\n'
        f'  (lib_symbols\n  )\n'
        f'{power_block}\n'
        f'{ec_block}\n'
        f'{mu_block}\n'
        f'{usb_block}\n'
        f'{pwrin_block}\n'
        f'{tcp0_block}\n'
        f'{radio_block}\n'
        f'{internal_block}\n'
        f'{ham_block}\n'
        f'{display_block}\n'
        f'{intehill_block}\n'
        f'{keyboard_block}\n'
        f'{audio_block}\n'
        f'{maker_block}\n'
        + "\n".join(root_labels) + "\n"
        + "\n".join(root_ncs) + "\n"
        f'  (sheet_instances\n'
        f'    (path "/"\n'
        f'      (page "1")\n'
        f'    )\n'
        f'  )\n'
        f'  (embedded_fonts no)\n'
        f')\n'
    )
    with open(os.path.join(PROJDIR, "ducktop2.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(root_text)


if __name__ == "__main__":
    main()
