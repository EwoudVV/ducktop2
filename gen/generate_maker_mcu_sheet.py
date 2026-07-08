from build_ducktop2 import Sheet, FOOTPRINTS


def usblc6(s, ref, value, x, y, dp, dm, rail):
    s.place(ref, "USBLC6-2P6", value, x, y, footprint=FOOTPRINTS["USBLC6-2P6"],
            pin_nets={
                "1": (dp, "local"), "6": (dp, "local"),
                "3": (dm, "local"), "4": (dm, "local"),
                "5": (rail, "local"),
                "2": ("GND", "local"),
            })


MAKER_PINS = {
    "1": ("GND", "local"),
    "2": ("MAKER_5V", "local"),
    "3": ("MAKER_USB_CONN_DM", "local"),
    "4": ("MAKER_USB_CONN_DP", "local"),
    "5": ("MAKER_BOOT_N", "local"),
    "6": ("MAKER_RUN_N", "local"),
    "7": ("MAKER_SWDIO", "local"),
    "8": ("MAKER_SWCLK", "local"),
    "9": ("MAKER_UART_TX", "local"),
    "10": ("MAKER_UART_RX", "local"),
    "11": ("MAKER_I2C_SCL", "local"),
    "12": ("MAKER_I2C_SDA", "local"),
    "13": ("MAKER_SPI_SCK", "local"),
    "14": ("MAKER_SPI_MISO", "local"),
    "15": ("MAKER_SPI_MOSI", "local"),
    "16": ("MAKER_SPI_CS_N", "local"),
    "17": ("MAKER_GPIO0", "local"),
    "18": ("MAKER_GPIO1", "local"),
    "19": ("MAKER_GPIO2", "local"),
    "20": ("MAKER_GPIO3", "local"),
    "21": ("MAKER_GPIO4", "local"),
    "22": ("MAKER_GPIO5", "local"),
    "23": ("MAKER_GPIO6", "local"),
    "24": ("MAKER_GPIO7", "local"),
    "25": ("MAKER_GPIO8", "local"),
    "26": ("MAKER_GPIO9", "local"),
    "27": ("MAKER_GPIO10", "local"),
    "28": ("MAKER_GPIO11", "local"),
    "29": ("MAKER_GPIO12", "local"),
    "30": ("MAKER_GPIO13", "local"),
    "31": ("MAKER_GPIO14", "local"),
    "32": ("MAKER_GPIO15", "local"),
    "33": ("MAKER_GPIO16", "local"),
    "34": ("MAKER_GPIO17", "local"),
    "35": ("MAKER_ADC0", "local"),
    "36": ("MAKER_ADC1", "local"),
    "37": ("MAKER_3V3", "local"),
    "38": ("GND", "local"),
    "39": ("MAKER_ADC2", "local"),
    "40": ("GND", "local"),
}


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 900
    s.refcounters["#FLG"] = 900

    s.text(20, 12.7, "== User maker MCU bay: Arduino/Pico-class sandbox controller ==")
    s.text(20, 20.32, "This is intentionally separate from the laptop EC so experiments cannot break keyboard/power/fan control.")
    s.text(20, 27.94, "Module is host-programmable over Mu USB2_P7 and exposes 3.3V GPIO on a user header.")

    s.text(20, 50.8, "== Maker MCU module/mezzanine interface ==")
    s.place("J900", "Conn_02x20_Odd_Even", "Maker MCU module socket, Pico/Arduino-class", 130, 155,
            footprint=FOOTPRINTS["Conn_02x20_Header"], pin_nets=MAKER_PINS)

    s.text(390, 50.8, "== User-facing maker GPIO header ==")
    s.place("J901", "Conn_02x20_Odd_Even", "Exposed maker GPIO/power header", 500, 155,
            footprint=FOOTPRINTS["Conn_02x20_Header"], pin_nets=MAKER_PINS)

    # Power and USB host link.
    s.text(20, 285.75, "== Power, USB, and bring-up controls ==")
    s.place("F900", "Fuse", "500mA maker 5V fuse/polyfuse", 20, 312.42, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("MAKER_5V", "local")})
    s.place("C900", "C", "10u maker 5V bulk", 20, 325.12, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("MAKER_5V", "local"), "2": ("GND", "local")})
    s.place("C901", "C", "1u maker 3V3 local", 20, 337.82, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MAKER_3V3", "local"), "2": ("GND", "local")})

    s.place("R900", "R", "22R maker USB DP series", 190, 300, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MAKER_USB_DP", "hier"), "2": ("MAKER_USB_CONN_DP", "local")})
    s.place("R901", "R", "22R maker USB DM series", 190, 312.42, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MAKER_USB_DM", "hier"), "2": ("MAKER_USB_CONN_DM", "local")})
    usblc6(s, "U900", "USBLC6-2P6 maker USB ESD", 300, 306.07, "MAKER_USB_CONN_DP", "MAKER_USB_CONN_DM", "MAKER_5V")

    s.place("R902", "R", "100k RUN pull-up", 390, 285.75, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MAKER_3V3", "local"), "2": ("MAKER_RUN_N", "local")})
    s.place("SW900", "SW_Push", "Maker reset/RUN", 390, 298.45, footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MAKER_RUN_N", "local"), "2": ("GND", "local")})
    s.place("R903", "R", "100k BOOT pull-up", 390, 311.15, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MAKER_3V3", "local"), "2": ("MAKER_BOOT_N", "local")})
    s.place("SW901", "SW_Push", "Maker boot/user", 390, 323.85, footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MAKER_BOOT_N", "local"), "2": ("GND", "local")})

    s.place("J902", "Conn_01x04", "Maker SWD/debug header", 560, 305,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MAKER_3V3", "local"),
                "3": ("MAKER_SWDIO", "local"),
                "4": ("MAKER_SWCLK", "local"),
            })

    s.gnd(650, 330.2)
    s.pwrflag(80, 312.42, "MAKER_5V")
    s.pwrflag(80, 337.82, "MAKER_3V3")

    s.text(20, 375.92, "NOTES:")
    s.text(20, 383.54, "Treat J900 as the internal programmable module interface; J901 exposes the same sandbox pins for tinkering.")
    s.text(20, 391.16, "Use 3.3V GPIO only. MAKER_5V is fused and intended for the module/input side, not arbitrary high-current loads.")
    s.text(20, 398.78, "MAKER_USB_DP/DM come from Mu USB2_P7 so the host OS sees this as a normal USB dev board.")
    s.text(20, 406.4, "If a specific Pico/RP2350/Arduino module is chosen later, replace J900 pinout/footprint with that exact module.")

    return s
