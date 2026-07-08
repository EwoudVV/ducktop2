import genlib
from build_ducktop2 import Sheet, FOOTPRINTS


def symbol_pins(name):
    _lib, text = genlib.load_renamed_symbol(name)
    return genlib.parse_pins(text)


def default_pin_map(symname, power_3v3_net="SYS_3V3"):
    nets = {}
    for num, pin in symbol_pins(symname).items():
        name = pin["name"]
        if name == "GND":
            nets[num] = ("GND", "local")
        elif name in ("3.3V", "+3.3V"):
            nets[num] = (power_3v3_net, "local")
        elif name == "NC":
            nets[num] = ("", "nc")
        else:
            nets[num] = ("", "nc")
    return nets


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 90
    s.refcounters["#FLG"] = 90

    s.text(20, 12.7, "== Radio, OLED, and GNSS peripherals ==")
    s.text(20, 20.32, "M.2 E-key is the main Wi-Fi/Bluetooth path; OLED and GNSS stay on EC-controlled low-speed interfaces.")
    s.text(20, 27.94, "RF stays inside modules for this pass; antenna, keepout, and exact module qualification are layout-stage work.")

    # ---------------- J40: M.2 E-key Wi-Fi/Bluetooth module ----------------
    s.text(20, 50.8, "== J40 M.2 E-key Wi-Fi/Bluetooth module ==")
    wifi_perst = "WIFI_PERST_N"
    wifi_refclk_p = "WIFI_REFCLK_E_P"
    wifi_refclk_n = "WIFI_REFCLK_E_N"
    m2e = default_pin_map("Bus_M.2_Socket_E", power_3v3_net="WIFI_3V3")
    m2e.update({
        "3": ("WIFI_USB_DP", "hier"),
        "5": ("WIFI_USB_DN", "hier"),
        "35": ("WIFI_PCIE_RX_P", "hier"),
        "37": ("WIFI_PCIE_RX_N", "hier"),
        "41": ("WIFI_PCIE_TX_P", "hier"),
        "43": ("WIFI_PCIE_TX_N", "hier"),
        "47": (wifi_refclk_p, "local"),
        "49": (wifi_refclk_n, "local"),
        "52": (wifi_perst, "local"),
        "53": ("WIFI_CLKREQ_N", "hier"),
        "54": ("WIFI_W_DISABLE2_N", "hier"),
        "55": ("PCIE_WAKE_N", "hier"),
        "56": ("WIFI_W_DISABLE1_N", "hier"),
        "58": ("I2C_SDA", "hier"),
        "60": ("I2C_SCL", "hier"),
    })
    s.place("J40", "Bus_M.2_Socket_E", "M.2 E-key Wi-Fi/Bluetooth", 170, 180,
            footprint=FOOTPRINTS["M2_E_key"], pin_nets=m2e)

    s.place("F10", "Fuse", "2A E-key 3V3 fuse/polyfuse", 20, 76.2, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("WIFI_3V3", "local")})
    s.place("C170", "C", "47u E-key bulk", 20, 91.44, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("GND", "local")})
    s.place("C171", "C", "100n radio bypass", 20, 104.14, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("GND", "local")})
    s.pwrflag(20, 119.38, "WIFI_3V3")
    s.place("R170", "R", "10k W_DISABLE1 pull-up", 20, 139.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("WIFI_W_DISABLE1_N", "hier")})
    s.place("R171", "R", "10k W_DISABLE2 pull-up", 20, 152.4, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("WIFI_W_DISABLE2_N", "hier")})
    s.place("R176", "R", "0R / PERST isolation", 20, 170.18, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PLTRST_SRC_N", "hier"), "2": (wifi_perst, "local")})
    s.place("R177", "R", "0R / REFCLK+ isolation", 20, 182.88, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_REFCLK_P", "hier"), "2": (wifi_refclk_p, "local")})
    s.place("R178", "R", "0R / REFCLK- isolation", 20, 195.58, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_REFCLK_N", "hier"), "2": (wifi_refclk_n, "local")})

    # ---------------- J41/J45: SSD1306 I2C OLED/status displays ----------------
    s.text(20, 260.35, "== Dual SSD1306 I2C OLED/status display headers ==")
    s.place("J41", "Conn_01x06", "SSD1306 OLED A 0x3C (3.3V)", 90, 300,
            footprint=FOOTPRINTS["Conn_01x06"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MCU_3V3", "hier"),
                "3": ("I2C_SCL", "hier"),
                "4": ("I2C_SDA", "hier"),
                "5": ("OLED_RESET_N", "hier"),
                "6": ("OLED_SA0", "local"),
            })
    s.place("R172", "R", "100k OLED reset pull-up", 20, 287.02, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("OLED_RESET_N", "hier")})
    s.place("R173", "R", "0R SSD1306 SA0=0x3C default", 20, 299.72, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("OLED_SA0", "local"), "2": ("GND", "local")})
    s.place("R179", "R", "DNP 0R SA0=0x3D option", 20, 312.42, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("OLED_SA0", "local"), "2": ("MCU_3V3", "hier")})
    s.place("C174", "C", "1u OLED local", 90, 325.12, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C175", "C", "100n OLED local", 90, 337.82, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("J45", "Conn_01x06", "SSD1306 OLED B 0x3D (3.3V)", 205, 300,
            footprint=FOOTPRINTS["Conn_01x06"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MCU_3V3", "hier"),
                "3": ("I2C_SCL", "hier"),
                "4": ("I2C_SDA", "hier"),
                "5": ("OLED_RESET_N", "hier"),
                "6": ("OLED2_SA0", "local"),
            })
    s.place("R196", "R", "0R SSD1306 B SA0=0x3D default", 205, 325.12, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("OLED2_SA0", "local"), "2": ("MCU_3V3", "hier")})
    s.place("R197", "R", "DNP 0R OLED B SA0=0x3C option", 205, 337.82, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("OLED2_SA0", "local"), "2": ("GND", "local")})
    s.place("C178", "C", "1u OLED B local", 205, 350.52, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C179", "C", "100n OLED B local", 205, 363.22, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})

    # ---------------- U40: u-blox MAX-M10S GNSS ----------------
    s.text(330, 50.8, "== U40 u-blox MAX-M10S GNSS module ==")
    s.place("U40", "MAX-M10S", "MAX-M10S GNSS", 410, 110,
            footprint=FOOTPRINTS["MAX-M10S"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("GNSS_UART_RX", "hier"),
                "3": ("GNSS_UART_TX", "hier"),
                "4": ("GNSS_PPS", "hier"),
                "5": ("GNSS_EXTINT", "hier"),
                "6": ("SYS_3V3", "hier"),
                "7": ("SYS_3V3", "hier"),
                "8": ("SYS_3V3", "hier"),
                "9": ("GNSS_RESET_N", "hier"),
                "10": ("GND", "local"),
                "11": ("GNSS_RF_IN", "local"),
                "12": ("GND", "local"),
                "13": ("", "nc"),
                "14": ("", "nc"),
                "15": ("", "nc"),
                "16": ("", "nc"),
                "17": ("", "nc"),
                "18": ("", "nc"),
            })
    s.place("J42", "Conn_Coaxial", "GNSS passive antenna U.FL", 520, 110,
            footprint=FOOTPRINTS["Conn_Coaxial_UFL"],
            pin_nets={"1": ("GNSS_RF_IN", "local"), "2": ("GND", "local")})
    s.place("R195", "R", "DNP 0R active antenna bias enable", 520, 140,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GNSS_ANT_BIAS", "local")})
    s.place("L40", "L", "DNP 56nH active antenna RF choke", 520, 152.4,
            footprint=FOOTPRINTS["L_RF"],
            pin_nets={"1": ("GNSS_ANT_BIAS", "local"), "2": ("GNSS_RF_IN", "local")})
    s.place("C176", "C", "DNP 100p bias RF bypass", 590, 140,
            footprint=FOOTPRINTS["C_RF"],
            pin_nets={"1": ("GNSS_ANT_BIAS", "local"), "2": ("GND", "local")})
    s.place("C177", "C", "DNP 100n bias bypass", 590, 152.4,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("GNSS_ANT_BIAS", "local"), "2": ("GND", "local")})
    s.place("J44", "Conn_01x06", "DNP MAX-M10S debug/program", 410, 190,
            footprint=FOOTPRINTS["Conn_01x06"],
            pin_nets={
                "1": ("SYS_3V3", "hier"),
                "2": ("GND", "local"),
                "3": ("GNSS_UART_RX", "hier"),
                "4": ("GNSS_UART_TX", "hier"),
                "5": ("GNSS_PPS", "hier"),
                "6": ("GNSS_RESET_N", "hier"),
            })
    s.place("C172", "C", "10u GNSS local", 330, 83.82, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place("C173", "C", "100n GNSS local", 330, 96.52, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")})
    s.place("R174", "R", "100k GNSS reset pull-up", 330, 121.92, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GNSS_RESET_N", "hier")})
    s.place("R175", "R", "100k GNSS EXTINT pulldown", 330, 134.62, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("GNSS_EXTINT", "hier"), "2": ("GND", "local")})

    # ---------------- J43: reserved low-speed radio/debug expansion ----------------
    s.text(330, 200.66, "== J43 low-speed radio/debug expansion ==")
    s.place("J43", "Conn_01x08", "DNP radio/debug expansion", 410, 250,
            footprint=FOOTPRINTS["Conn_01x08"],
            pin_nets={
                "1": ("MCU_3V3", "hier"),
                "2": ("GND", "local"),
                "3": ("I2C_SCL", "hier"),
                "4": ("I2C_SDA", "hier"),
                "5": ("RADIO_GPIO0", "hier"),
                "6": ("GNSS_EXTINT", "hier"),
                "7": ("GNSS_UART_TX", "hier"),
                "8": ("GNSS_UART_RX", "hier"),
            })

    s.gnd(520, 300)
    s.text(20, 350.52, "NOTES:")
    s.text(20, 358.14, "M.2 E-key PCIe lane follows the existing Mu-host-to-socket naming convention used by the NVMe M-key slot.")
    s.text(20, 365.76, "USB2_P1 is reserved for the E-key Bluetooth/USB function; HSIO1 is reserved for the E-key PCIe lane.")
    s.text(20, 373.38, "Target radio is an Intel AX210-class M.2 2230 Key-E module: Wi-Fi over PCIe, Bluetooth over USB.")
    s.text(20, 381, "OLED headers are SSD1306 I2C: GND, 3V3, SCL, SDA, RES, SA0. Use 3.3V OLED modules only.")
    s.text(20, 388.62, "MAX-M10S uses EC UART here. VIO_SEL, SAFEBOOT_N, SDA/SCL, VCC_RF, and LNA_EN are NC.")
    s.text(20, 396.24, "OLED A defaults to 0x3C; OLED B defaults to 0x3D. Do not run both at the same address.")
    s.text(20, 403.86, "GNSS RF layout: place U.FL near board edge, route RF_IN as 50 ohm, and keep it away from Wi-Fi antennas/noisy bucks.")
    s.text(20, 411.48, "Avoid CNVio/CNVio2-only E-key modules unless LattePanda Mu support is explicitly verified.")
    s.text(20, 419.1, "R195/L40/C176/C177 are DNP active-GNSS-antenna bias options; leave open for passive antennas.")
    s.text(20, 426.72, "SUSCLK, SDIO, PCM/I2S, UIM, and vendor-defined E-key pins remain NC for the AX210-class module target.")

    return s
