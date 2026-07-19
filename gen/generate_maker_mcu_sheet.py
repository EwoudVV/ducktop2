from build_ducktop2 import Sheet, FOOTPRINTS


def place_r(s, ref, value, x, y, net1, net2, *, size="0402", dnp=False,
            extra_props=None):
    footprint = {"0402": FOOTPRINTS["R_0402"], "0603": FOOTPRINTS["R"]}[size]
    s.place(ref, "R", value, x, y, footprint=footprint, dnp=dnp,
            extra_props=extra_props,
            pin_nets={"1": net1, "2": net2})


def place_c(s, ref, value, x, y, net1, net2=("GND", "local"), *, size="0402",
            extra_props=None):
    footprint = {
        "0402": FOOTPRINTS["C_0402"],
        "0603": FOOTPRINTS["C_100n"],
        "0805": FOOTPRINTS["C_0805"],
        "1206": FOOTPRINTS["C_1206"],
    }[size]
    s.place(ref, "C", value, x, y, footprint=footprint,
            pin_nets={"1": net1, "2": net2}, extra_props=extra_props)


def usblc6(s, ref, value, x, y, dp, dm, rail):
    return s.place(ref, "USBLC6-2P6", value, x, y, footprint=FOOTPRINTS["USBLC6-2P6"],
                   pin_nets={
                       "1": (dp, "local"), "6": (dp, "local"),
                       "3": (dm, "local"), "4": (dm, "local"),
                       "5": (rail, "local"), "2": ("GND", "local"),
                   }, extra_props={
                       "Manufacturer": "STMicroelectronics", "MPN": "USBLC6-2P6",
                       "Datasheet": "https://www.st.com/resource/en/datasheet/usblc6-2.pdf",
                   })


MAKER_HEADER_SIGNALS = [
    "MAKER_BOOT_N", "MAKER_RUN_N", "MAKER_SWDIO", "MAKER_SWCLK",
    "MAKER_UART_TX", "MAKER_UART_RX", "MAKER_I2C_SCL", "MAKER_I2C_SDA",
    "MAKER_SPI_SCK", "MAKER_SPI_MISO", "MAKER_SPI_MOSI", "MAKER_SPI_CS_N",
    *[f"MAKER_GPIO{i}" for i in range(15)],
    "MAKER_ADC0", "MAKER_ADC1", "MAKER_ADC2",
]


def exposed_maker_net(net):
    return f"J901_{net}"


def isolated_maker_net(net):
    return f"{exposed_maker_net(net)}_ISO"


MAKER_HEADER_PINS = {
    "1": ("GND", "local"),
    "2": ("J901_5V_OUT", "local"),
    "3": ("GND", "local"),
    "4": ("J901_3V3_OUT", "local"),
    **{str(5 + index): (exposed_maker_net(net), "local")
       for index, net in enumerate(MAKER_HEADER_SIGNALS[:27])},
    "32": ("", "nc"),
    "33": ("GND", "local"),
    "34": ("GND", "local"),
    "35": (exposed_maker_net("MAKER_ADC0"), "local"),
    "36": (exposed_maker_net("MAKER_ADC1"), "local"),
    "37": ("J901_3V3_OUT", "local"),
    "38": ("GND", "local"),
    "39": (exposed_maker_net("MAKER_ADC2"), "local"),
    "40": ("GND", "local"),
}


RP2350_PINS = {
    "1": ("MAKER_3V3_CORE", "local"),
    "2": ("MAKER_UART_TX", "local"),
    "3": ("MAKER_UART_RX", "local"),
    "4": ("MAKER_I2C_SDA", "local"),
    "5": ("MAKER_I2C_SCL", "local"),
    "6": ("MAKER_1V1", "local"),
    "7": ("MAKER_GPIO0", "local"),
    "8": ("MAKER_GPIO1", "local"),
    "9": ("MAKER_GPIO2", "local"),
    "10": ("MAKER_GPIO3", "local"),
    "11": ("MAKER_3V3_CORE", "local"),
    "12": ("MAKER_GPIO4", "local"),
    "13": ("MAKER_GPIO5", "local"),
    "14": ("MAKER_GPIO6", "local"),
    "15": ("MAKER_GPIO7", "local"),
    "16": ("MAKER_GPIO8", "local"),
    "17": ("MAKER_GPIO9", "local"),
    "18": ("MAKER_GPIO10", "local"),
    "19": ("MAKER_GPIO11", "local"),
    "20": ("MAKER_3V3_CORE", "local"),
    "21": ("MAKER_XIN", "local"),
    "22": ("MAKER_XOUT", "local"),
    "23": ("MAKER_1V1", "local"),
    "24": ("MAKER_SWCLK_MCU", "local"),
    "25": ("MAKER_SWDIO_MCU", "local"),
    "26": ("MAKER_RUN_N", "local"),
    "27": ("MAKER_SPI_MISO", "local"),
    "28": ("MAKER_SPI_CS_N", "local"),
    "29": ("MAKER_SPI_SCK", "local"),
    "30": ("MAKER_3V3_CORE", "local"),
    "31": ("MAKER_SPI_MOSI", "local"),
    "32": ("MAKER_GPIO12", "local"),
    "33": ("MAKER_GPIO13", "local"),
    "34": ("MAKER_GPIO14", "local"),
    "35": ("MAKER_SMPS_PS", "local"),
    "36": ("MAKER_HOST_ACTIVE_N", "local"),
    "37": ("MAKER_PWR_FAULT_N", "local"),
    "38": ("MAKER_3V3_CORE", "local"),
    "39": ("MAKER_1V1", "local"),
    "40": ("MAKER_ADC0", "local"),
    "41": ("MAKER_ADC1", "local"),
    "42": ("MAKER_ADC2", "local"),
    "43": ("MAKER_PWR_EN", "local"),
    "44": ("MAKER_ADC_AVDD", "local"),
    "45": ("MAKER_3V3_CORE", "local"),
    "46": ("MAKER_VREG_AVDD", "local"),
    "47": ("GND", "local"),
    "48": ("MAKER_VREG_LX", "local"),
    "49": ("MAKER_3V3_CORE", "local"),
    "50": ("MAKER_1V1", "local"),
    "51": ("MAKER_USB_DM_MCU", "local"),
    "52": ("MAKER_USB_DP_MCU", "local"),
    "53": ("MAKER_3V3_CORE", "local"),
    "54": ("MAKER_3V3_CORE", "local"),
    "55": ("MAKER_QSPI_SD3", "local"),
    "56": ("MAKER_QSPI_SCLK", "local"),
    "57": ("MAKER_QSPI_SD0", "local"),
    "58": ("MAKER_QSPI_SD2", "local"),
    "59": ("MAKER_QSPI_SD1", "local"),
    "60": ("MAKER_QSPI_SS", "local"),
    "61": ("GND", "local"),
}


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 900
    s.refcounters["#FLG"] = 900

    s.text(20, 12.7, "== Integrated RP2350 maker controller (Pico 2 architecture, no module/cable) ==")
    s.text(20, 20.32, "The Mu USB2_P7 pair reaches U901 through a default-disconnected host-state switch. J901 is the external tinkering header, not a module socket.")
    s.text(20, 27.94, "Power, flash, crystal, BOOTSEL, reset, SWD, ADC filtering, and decoupling follow Raspberry Pi Pico 2 guidance.")

    s.text(20, 48.26, "== RP2350A and 4MB QSPI flash ==")
    s.place("U901", "RP2350A", "RP2350A", 300, 145, footprint=FOOTPRINTS["RP2350A"],
            pin_nets=RP2350_PINS,
            extra_props={"Manufacturer": "Raspberry Pi", "MPN": "RP2350A (A4 stepping)"})
    s.place("U902", "W25Q32JVZP", "W25Q32RVXHJQ 32Mbit (4MiB)", 105, 125,
            footprint=FOOTPRINTS["W25Q32RVXHJQ"],
            pin_nets={
                "1": ("MAKER_QSPI_SS", "local"),
                "2": ("MAKER_QSPI_SD1", "local"),
                "3": ("MAKER_QSPI_SD2", "local"),
                "4": ("GND", "local"),
                "5": ("MAKER_QSPI_SD0", "local"),
                "6": ("MAKER_QSPI_SCLK", "local"),
                "7": ("MAKER_QSPI_SD3", "local"),
                "8": ("MAKER_3V3_CORE", "local"),
                "9": ("GND", "local"),
            },
            extra_props={"Manufacturer": "Winbond", "MPN": "W25Q32RVXHJQ"})
    place_c(s, "C902", "4.7u flash bulk", 45, 100, ("MAKER_3V3_CORE", "local"))
    place_c(s, "C903", "100n flash local", 45, 112.7, ("MAKER_3V3_CORE", "local"))
    place_r(s, "R904", "DNP 10k QSPI CS pull-up", 45, 125.4,
            ("MAKER_3V3_CORE", "local"), ("MAKER_QSPI_SS", "local"), dnp=True)
    place_r(s, "R905", "1k BOOTSEL isolation", 45, 138.1,
            ("MAKER_QSPI_SS", "local"), ("MAKER_BOOT_N", "local"))

    s.text(20, 177.8, "== RP2350 12MHz clock and internal 1.1V switcher ==")
    s.place("Y900", "Crystal_GND24", "Abracon ABM8-272-T3 12MHz", 90, 215,
            footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={
                "1": ("MAKER_XIN", "local"), "2": ("GND", "local"),
                "3": ("MAKER_XTAL_R", "local"), "4": ("GND", "local"),
            }, extra_props={"Manufacturer": "Abracon", "MPN": "ABM8-272-T3"})
    place_r(s, "R906", "1k crystal damping", 150, 215,
            ("MAKER_XTAL_R", "local"), ("MAKER_XOUT", "local"))
    place_c(s, "C918", "15p XIN load", 90, 235, ("MAKER_XIN", "local"))
    place_c(s, "C919", "15p XOUT load", 150, 235, ("MAKER_XTAL_R", "local"))

    s.place("L901", "L", "3.3u AOTA-B201610S3R3-101-T (orientation critical)", 260, 215,
            footprint=FOOTPRINTS["L_RP2350"],
            pin_nets={"1": ("MAKER_1V1", "local"), "2": ("MAKER_VREG_LX", "local")},
            extra_props={"Manufacturer": "Abracon", "MPN": "AOTA-B201610S3R3-101-T"})
    place_c(s, "C911", "4.7u VREG input", 220, 235, ("MAKER_3V3_CORE", "local"))
    place_c(s, "C912", "4.7u 1V1 output", 260, 235, ("MAKER_1V1", "local"))
    place_r(s, "R907", "33R VREG_AVDD filter", 310, 215,
            ("MAKER_3V3_CORE", "local"), ("MAKER_VREG_AVDD", "local"))
    place_c(s, "C913", "4.7u VREG_AVDD", 310, 235, ("MAKER_VREG_AVDD", "local"))
    place_c(s, "C914", "100n DVDD A", 350, 215, ("MAKER_1V1", "local"))
    place_c(s, "C915", "100n DVDD B", 350, 227.7, ("MAKER_1V1", "local"))
    place_c(s, "C916", "100n DVDD C", 350, 240.4, ("MAKER_1V1", "local"))

    for index, ref in enumerate(("C904", "C905", "C906", "C907", "C908", "C909", "C910")):
        place_c(s, ref, "100n RP2350 3V3 local", 400 + (index % 4) * 42,
                205 + (index // 4) * 17, ("MAKER_3V3_CORE", "local"))

    s.text(20, 266.7, "== Maker core rails and reverse-blocked header power outputs ==")
    s.place("F900", "Fuse", "1.1A hold PPTC Littelfuse 1206L110/16WR", 30, 295,
            footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("MAKER_5V_CORE", "local")},
            extra_props={"Manufacturer": "Littelfuse", "MPN": "1206L110/16WR"})
    s.place("U903", "TPS62821DLC", "TPS62821DLC 1A adjustable buck", 150, 305,
            footprint=FOOTPRINTS["TPS62821DLC"],
            pin_nets={
                "1": ("MAKER_5V_CORE", "local"),
                "2": ("MAKER_3V3_FB", "local"),
                "3": ("GND", "local"),
                "4": ("", "nc"),
                "5": ("GND", "local"),
                "6": ("MAKER_3V3_SW", "local"),
                "7": ("MAKER_5V_CORE", "local"),
                "8": ("", "nc"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS62821DLCR"})
    s.place("L900", "L", "470nH TDK TFM201610ALM-R47MTAA", 225, 305,
            footprint=FOOTPRINTS["L_TFM201610"],
            pin_nets={"1": ("MAKER_3V3_SW", "local"), "2": ("MAKER_3V3_CORE", "local")},
            extra_props={"Manufacturer": "TDK", "MPN": "TFM201610ALM-R47MTAA"})
    place_c(s, "C900", "4.7u 6.3V X7R TPS62821 input", 65, 315,
            ("MAKER_5V_CORE", "local"), size="0603",
            extra_props={"Manufacturer": "Taiyo Yuden", "MPN": "JMK107BB7475MA-T"})
    tps62821_out = {"Manufacturer": "Murata", "MPN": "GRM188Z71A106MA73D"}
    place_c(s, "C901", "10u 10V X7R TPS62821 output A", 275, 315,
            ("MAKER_3V3_CORE", "local"), size="0603", extra_props=tps62821_out)
    place_c(s, "C921", "10u 10V X7R TPS62821 output B", 320, 315,
            ("MAKER_3V3_CORE", "local"), size="0603", extra_props=tps62821_out)
    place_r(s, "R902", "450k 1% TPS62821 feedback high", 255, 330,
            ("MAKER_3V3_CORE", "local"), ("MAKER_3V3_FB", "local"), size="0603")
    place_r(s, "R920", "100k 1% TPS62821 feedback low", 300, 330,
            ("MAKER_3V3_FB", "local"), ("GND", "local"), size="0603")
    place_c(s, "C923", "120p 50V C0G TPS62821 feed-forward", 255, 342.7,
            ("MAKER_3V3_CORE", "local"), ("MAKER_3V3_FB", "local"), size="0603",
            extra_props={"Manufacturer": "Murata", "MPN": "GRM1885C1H121JA01D"})
    place_r(s, "R903", "100k RP2350 SMPS power-save pull-down", 350, 340.4,
            ("MAKER_SMPS_PS", "local"), ("GND", "local"))

    switch_cap = {"Manufacturer": "TDK", "MPN": "C1608X7R1C104K080AA"}
    s.place("U904", "TPS2553D", "TPS2553DDBVR 5V header, 300mA nominal", 405, 300,
            footprint=FOOTPRINTS["TPS2553DDBV"],
            pin_nets={
                "1": ("MAKER_5V_CORE", "local"), "2": ("GND", "local"),
                "3": ("MAKER_PWR_EN", "local"), "4": ("MAKER_PWR_FAULT_N", "local"),
                "5": ("MAKER_5V_ILIM", "local"), "6": ("J901_5V_OUT", "local"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS2553DDBVR"})
    place_r(s, "R921", "88.7k 1% (262-342mA 5V header limit)", 405, 325,
            ("MAKER_5V_ILIM", "local"), ("GND", "local"), size="0603")
    place_c(s, "C924", "100n 16V X7R 5V switch input", 375, 325,
            ("MAKER_5V_CORE", "local"), size="0603", extra_props=switch_cap)
    place_c(s, "C925", "100n 16V X7R 5V header output", 435, 325,
            ("J901_5V_OUT", "local"), size="0603", extra_props=switch_cap)

    s.place("U905", "TPS2553D", "TPS2553DDBVR 3V3 header, 120mA nominal", 510, 300,
            footprint=FOOTPRINTS["TPS2553DDBV"],
            pin_nets={
                "1": ("MAKER_3V3_CORE", "local"), "2": ("GND", "local"),
                "3": ("MAKER_PWR_EN", "local"), "4": ("MAKER_PWR_FAULT_N", "local"),
                "5": ("MAKER_3V3_ILIM", "local"), "6": ("J901_3V3_OUT", "local"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS2553DDBVR"})
    place_r(s, "R922", "226k 1% (101-142mA 3V3 header limit)", 510, 325,
            ("MAKER_3V3_ILIM", "local"), ("GND", "local"), size="0603")
    place_c(s, "C926", "100n 16V X7R 3V3 switch input", 480, 325,
            ("MAKER_3V3_CORE", "local"), size="0603", extra_props=switch_cap)
    place_c(s, "C927", "100n 16V X7R 3V3 header output", 540, 325,
            ("J901_3V3_OUT", "local"), size="0603", extra_props=switch_cap)
    place_r(s, "R923", "100k maker header rails default-off", 570, 312.3,
            ("MAKER_PWR_EN", "local"), ("GND", "local"), size="0603")
    place_r(s, "R924", "10k maker header shared fault pull-up", 570, 325,
            ("MAKER_3V3_CORE", "local"), ("MAKER_PWR_FAULT_N", "local"), size="0603")

    place_r(s, "R908", "200R ADC reference filter", 350, 290,
            ("MAKER_3V3_CORE", "local"), ("MAKER_ADC_VREF", "local"))
    place_r(s, "R909", "1R ADC input isolator", 430, 290,
            ("MAKER_ADC_VREF", "local"), ("MAKER_ADC_AVDD", "local"))
    place_c(s, "C922", "100n ADC_VREF filter", 430, 305, ("MAKER_ADC_VREF", "local"))
    place_c(s, "C917", "4.7u ADC_AVDD filter", 475, 305, ("MAKER_ADC_AVDD", "local"))

    s.text(20, 363.22, "== Direct internal USB, Pico utility GPIO, reset/boot, and SWD ==")
    usb_pins = usblc6(s, "U900", "USBLC6-2P6 maker USB ESD", 90, 395,
                      "MAKER_USB_DP", "MAKER_USB_DM", "MAKER_5V_CORE")
    s.label(*usb_pins["1"], "MAKER_USB_DP", hier=True)
    s.label(*usb_pins["3"], "MAKER_USB_DM", hier=True)
    s.place("U906", "TS3USB30EDGSR", "TS3USB30EDGSR maker USB host-state isolation", 150, 395,
            footprint=FOOTPRINTS["TS3USB30EDGSR"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MAKER_USB_DP", "hier"), "3": ("", "nc"),
                "4": ("MAKER_USB_ISO_DP", "local"), "5": ("GND", "local"),
                "6": ("MAKER_USB_ISO_DM", "local"), "7": ("", "nc"),
                "8": ("MAKER_USB_DM", "hier"), "9": ("MAKER_USB_OE_N", "local"),
                "10": ("MAKER_3V3_CORE", "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TS3USB30EDGSR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf",
            })
    place_r(s, "R900", "27R USB DP termination", 220, 387.35,
            ("MAKER_USB_ISO_DP", "local"), ("MAKER_USB_DP_MCU", "local"))
    place_r(s, "R901", "27R USB DM termination", 220, 402.59,
            ("MAKER_USB_ISO_DM", "local"), ("MAKER_USB_DM_MCU", "local"))
    s.place("Q901", "Q_NMOS_SOT23_GSD", "2N7002 physical host-VBUS USB connect gate", 285, 380,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("INTERNAL_USB_VBUS_VALID", "hier"), "2": ("GND", "local"),
                      "3": ("MAKER_USB_OE_N", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "2N7002KT1G"})
    place_r(s, "R925", "10k maker USB default-disconnect pull-up", 330, 380,
            ("MAKER_3V3_CORE", "local"), ("MAKER_USB_OE_N", "local"))
    place_c(s, "C928", "100n maker USB switch local", 420, 380,
            ("MAKER_3V3_CORE", "local"), size="0603")

    place_r(s, "R910", "1k active-low host-connected sense series", 245, 420,
            ("MAKER_USB_OE_N", "local"), ("MAKER_HOST_ACTIVE_N", "local"))
    place_r(s, "R911", "100k maker host-disconnected pull-up", 300, 420,
            ("MAKER_3V3_CORE", "local"), ("MAKER_HOST_ACTIVE_N", "local"))

    s.place("SW900", "SW_Push", "Maker reset/RUN", 470, 410,
            footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MAKER_RUN_N", "local"), "2": ("MAKER_RUN_SW", "local")},
            extra_props={"Manufacturer": "Omron", "MPN": "B3S-1000"})
    place_r(s, "R916", "1k reset switch series", 430, 422.7,
            ("MAKER_RUN_SW", "local"), ("GND", "local"))
    s.place("SW901", "SW_Push", "Maker BOOTSEL", 530, 410,
            footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MAKER_BOOT_N", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Omron", "MPN": "B3S-1000"})

    place_r(s, "R918", "100R SWDIO series", 590, 380,
            ("MAKER_SWDIO_MCU", "local"), ("MAKER_SWDIO", "local"))
    place_r(s, "R919", "100R SWCLK series", 590, 392.7,
            ("MAKER_SWCLK_MCU", "local"), ("MAKER_SWCLK", "local"))
    place_r(s, "R917", "0R VTref sense link", 650, 367,
            ("MAKER_3V3_CORE", "local"), ("MAKER_SWD_VTREF", "local"))
    s.place("J902", "Conn_01x06", "TC2030 Cortex SWD: VTref/SWDIO/RUN/SWCLK/GND/NC", 650, 397,
            footprint=FOOTPRINTS["TagConnect_SWD"],
            pin_nets={
                "1": ("MAKER_SWD_VTREF", "local"), "2": ("MAKER_SWDIO", "local"),
                "3": ("MAKER_RUN_N", "local"), "4": ("MAKER_SWCLK", "local"),
                "5": ("GND", "local"), "6": ("", "nc"),
            }, in_bom=False, extra_props={
                "ProcurementClass": "PCB copper test feature",
                "FixtureCable": "TC2030-CTX-NL external programming cable; not fitted",
            })

    s.text(500, 48.26, "== Protected user-facing maker GPIO header ==")

    # Four powered-off-isolating, 5-V-tolerant bus switches form the boundary
    # between the RP2350 and the outside world.  The supervisor/Q903 gate keeps
    # every signal disconnected until MAKER_3V3_CORE is valid for 200 ms.
    for bank in range(4):
        pin_nets = {
            "1": ("", "nc"), "10": ("GND", "local"),
            "19": ("MAKER_HEADER_OE_N", "local"),
            "20": ("MAKER_3V3_CORE", "local"),
        }
        for channel in range(8):
            index = bank * 8 + channel
            a_pin = str(2 + channel)
            b_pin = str(18 - channel)
            if index < len(MAKER_HEADER_SIGNALS):
                signal = MAKER_HEADER_SIGNALS[index]
                pin_nets[a_pin] = (signal, "local")
                pin_nets[b_pin] = (isolated_maker_net(signal), "local")
            else:
                pin_nets[a_pin] = ("", "nc")
                pin_nets[b_pin] = ("", "nc")
        s.place(
            f"U{910 + bank}", "SN74CB3T3245",
            f"SN74CB3T3245PWR maker header isolation bank {bank + 1}",
            500 + (bank % 2) * 100, 95 + (bank // 2) * 105,
            footprint=FOOTPRINTS["SN74CB3T3245"], pin_nets=pin_nets,
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "SN74CB3T3245PWR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74cb3t3245.pdf",
            },
        )
        place_c(s, f"C{930 + bank}", "100n maker header isolator local",
                500 + (bank % 2) * 100, 135 + (bank // 2) * 105,
                ("MAKER_3V3_CORE", "local"), size="0603")

    # Series resistance bounds a sustained connector short or output conflict
    # and separates the bus switches from connector/cable capacitance. Keep the
    # ESD shunts on the connector side of these resistors.
    for index, signal in enumerate(MAKER_HEADER_SIGNALS):
        place_r(
            s, f"R{932 + index}", "330R maker header fault limit",
            500 + (index % 5) * 60, 330 + (index // 5) * 12.7,
            (isolated_maker_net(signal), "local"),
            (exposed_maker_net(signal), "local"),
            extra_props={
                "Manufacturer": "Yageo", "MPN": "RC0402FR-07330RL",
            },
        )

    # Each connector-side signal receives its own low-capacitance ESD channel.
    # TPD4E05U06 exposes four independent 5.5-V-standoff shunts, preserving the
    # header's accidental-5-V tolerance while protecting the bus-switch edge.
    esd_pins = ("1", "2", "4", "5")
    for bank in range(8):
        pin_nets = {"3": ("GND", "local"), "8": ("GND", "local"),
                    "6": ("", "nc"), "7": ("", "nc"),
                    "9": ("", "nc"), "10": ("", "nc")}
        for channel, pin in enumerate(esd_pins):
            index = bank * 4 + channel
            if index < len(MAKER_HEADER_SIGNALS):
                pin_nets[pin] = (exposed_maker_net(MAKER_HEADER_SIGNALS[index]), "local")
            else:
                pin_nets[pin] = ("", "nc")
        s.place(
            f"U{914 + bank}", "TPD4E05U06DQA",
            f"TPD4E05U06DQAR maker header ESD bank {bank + 1}",
            700 + (bank % 2) * 65, 75 + (bank // 2) * 55,
            footprint=FOOTPRINTS["TPD4E05U06DQA"], pin_nets=pin_nets,
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPD4E05U06DQAR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf",
            },
        )

    s.place(
        "U922", "TLV803EA29RDBZR", "TLV803EA29RDBZR maker header rail supervisor",
        520, 285, footprint=FOOTPRINTS["TLV803EA29RDBZR"],
        pin_nets={"1": ("MAKER_HEADER_VALID", "local"), "2": ("GND", "local"),
                  "3": ("MAKER_3V3_CORE", "local")},
        extra_props={
            "Manufacturer": "Texas Instruments", "MPN": "TLV803EA29RDBZR",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tlv803e.pdf",
        },
    )
    place_r(s, "R931", "10k maker header supervisor pull-up", 565, 275,
            ("MAKER_3V3_CORE", "local"), ("MAKER_HEADER_VALID", "local"))
    s.place(
        "Q903", "Q_NMOS_SOT23_GSD", "2N7002 maker header isolation enable gate",
        610, 285, footprint=FOOTPRINTS["Q_NMOS"],
        pin_nets={"1": ("MAKER_HEADER_VALID", "local"), "2": ("GND", "local"),
                  "3": ("MAKER_HEADER_OE_N", "local")},
        extra_props={"Manufacturer": "onsemi", "MPN": "2N7002KT1G"},
    )
    place_r(s, "R930", "47k maker header isolation default-off", 655, 275,
            ("MAKER_3V3_CORE", "local"), ("MAKER_HEADER_OE_N", "local"),
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-0747KL"})
    place_c(s, "C934", "100n maker header supervisor local", 565, 300,
            ("MAKER_3V3_CORE", "local"), size="0603")

    s.place(
        "J901", "Conn_02x20_Odd_Even",
        "JST PUD 2x20 protected maker GPIO/power; NOT A PI HAT", 820, 170,
        footprint=FOOTPRINTS["Conn_02x20_Maker"], pin_nets=MAKER_HEADER_PINS,
        extra_props={
            "Manufacturer": "JST", "MPN": "B40B-PUDSS",
            "MatingHousing": "PUDP-40V-S",
            "Contacts": "SPUD-001T-P0.5 or SPUD-002T-P0.5",
            "InterfaceWarning": "NOT_RASPBERRY_PI_HAT_PINOUT_OR_PITCH",
            "Datasheet": "https://www.jst-mfg.com/product/pdf/eng/ePUD.pdf",
        },
    )

    s.gnd(690, 430.53)
    s.pwrflag(70, 295, "MAKER_5V_CORE")
    s.pwrflag(110, 295, "MAKER_3V3_CORE")
    s.pwrflag(360, 250, "MAKER_1V1")
    s.pwrflag(400, 250, "MAKER_VREG_AVDD")
    s.pwrflag(440, 250, "MAKER_ADC_AVDD")

    s.text(20, 449.58, "LAYOUT-CRITICAL NOTES:")
    s.text(20, 457.2, "Place L901/C911/C912/C913/R907 exactly around U901 per Raspberry Pi RP2350 guidance; keep LX copper tiny.")
    s.text(20, 464.82, "Place R900/R901 at U901 USB pins and U906 in the short Mu path; route both pairs as 90-ohm differential over uninterrupted ground.")
    s.text(20, 472.44, "Keep Y900/R906/C918/C919 tight to XIN/XOUT. Keep QSPI traces short; place C902/C903 at U902.")
    s.text(20, 480.06, "No Pico module, Micro-USB receptacle, or internal USB cable is used. The integrated RP2350 is the USB device.")
    s.text(20, 487.68, "J901 is keyed/latching JST PUD 2.00mm and NOT Pi-HAT compatible. U910-U913 isolate and tolerate 5V at the connector; 5.5V-standoff U914-U921 provide connector-side ESD.")
    s.text(20, 495.3, "R932-R961 are 330R fault-limit resistors. Digital outputs are 3.3V only; use external I2C pull-ups >=4.7k and initially keep SPI/SWD <=10MHz.")
    s.text(20, 502.92, "The ADC reference remains internal. J901 ADC precision range is 0-3.0V; 5.5V tolerance is for accidental input only and must be validated, not treated as an ADC range.")
    s.text(20, 510.54, "U922/Q903 hold all 30 signals disconnected until MAKER_3V3_CORE is valid. Header power rails separately default OFF and are current-limited.")
    s.text(20, 518.16, "U906 defaults disconnected and connects only after physical INTERNAL_USB_VBUS is valid. The maker cannot wake S3; firmware reinitializes USB when MAKER_HOST_ACTIVE_N falls.")

    return s
