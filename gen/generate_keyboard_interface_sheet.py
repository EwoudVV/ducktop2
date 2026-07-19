from build_ducktop2 import Sheet, FOOTPRINTS


def mainboard_keyboard_connector_nets():
    """Map J310 through a same-side FFC to the manufactured J320 connector.

    J310 and J320 are both top-mounted, bottom-contact FH12 connectors. With the
    specified Type-A (contacts on the same side) FFC, physical pin n at J310
    reaches physical pin 31-n at J320.
    """
    nets = {
        "1": ("GND", "local"),
        "2": ("KB_FFC_5V", "local"),
        "3": ("KB_FFC_RGB_DATA", "local"),
        "27": ("KB_FFC_I2C_SDA", "local"),
        "28": ("KB_FFC_I2C_SCL", "local"),
        "29": ("KB_FFC_3V3", "local"),
        "30": ("GND", "local"),
        "MP": ("GND", "local"),
    }
    for pin, col in zip(range(4, 19), range(14, -1, -1)):
        nets[str(pin)] = (f"KB_FFC_COL{col}", "local")
    for pin, row in zip(range(19, 27), range(7, -1, -1)):
        nets[str(pin)] = (f"KB_FFC_ROW{row}", "local")
    return nets


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 310
    s.refcounters["#FLG"] = 310

    s.text(20, 12.7, "== Mainboard keyboard FFC interface ==")
    s.text(20, 20.32, "This sheet is the motherboard-side connector only; the MX ULP switches and diodes live on the separate keyboard PCB.")
    s.text(20, 27.94, "Keep this sheet in the main root so ducktop2.kicad_pcb imports only the laptop-side FFC connector, not keyboard-switch footprints.")

    s.place("J310", "Conn_01x30_FFC_MP", "Mainboard keyboard FFC to MX ULP daughterboard", 120, 150,
            footprint=FOOTPRINTS["Conn_01x30_FFC"], pin_nets=mainboard_keyboard_connector_nets(),
            extra_props={"Manufacturer": "Hirose", "MPN": "FH12-30S-0.5SH(55)"})

    for index in range(15):
        s.place(f"R{360 + index}", "R", "1k keyboard matrix series", 250, 45 + index * 10,
                footprint=FOOTPRINTS["R"],
                pin_nets={
                    "1": (f"KB_COL{index}", "hier"),
                    "2": (f"KB_FFC_COL{index}", "local"),
                })
    # R375 is deliberately removed from the matrix bank.  The manufactured
    # rev-A board leaves COL15 unused, so the same FFC conductor can carry a
    # future rev-B addressable-RGB data stream without changing rev A.
    s.place("R375", "R", "100R keyboard RGB data series", 250, 195,
            footprint=FOOTPRINTS["R"],
            pin_nets={
                "1": ("KB_RGB_DATA_5V", "local"),
                "2": ("KB_FFC_RGB_DATA", "local"),
            })

    for index in range(8):
        s.place(f"R{376 + index}", "R", "1k keyboard matrix series", 350, 45 + index * 10,
                footprint=FOOTPRINTS["R"],
                pin_nets={
                    "1": (f"KB_ROW{index}", "hier"),
                    "2": (f"KB_FFC_ROW{index}", "local"),
                })
    s.place("R384", "R", "100R keyboard I2C SCL series", 450, 45,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("I2C_SCL", "hier"), "2": ("KB_FFC_I2C_SCL", "local")})
    s.place("R385", "R", "100R keyboard I2C SDA series", 450, 60,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("I2C_SDA", "hier"), "2": ("KB_FFC_I2C_SDA", "local")})
    # Future keyboard RGB power is limited below the Molex 0150200315 cable's
    # 0.5 A/contact rating.  The switch and AHCT buffer both fail off while the
    # EC is resetting; rev A simply sees an unused, unpowered contact.
    s.place("U310", "TPS2553D", "TPS2553D keyboard RGB 5V switch 0.40A nominal",
            520, 55, footprint=FOOTPRINTS["TPS2553DDBV"],
            pin_nets={
                "1": ("SYS_5V", "hier"), "2": ("GND", "local"),
                "3": ("KB_RGB_PWR_EN", "hier"), "4": ("KB_RGB_FAULT_N", "hier"),
                "5": ("KB_RGB_ILIM", "local"), "6": ("KB_FFC_5V", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS2553DDBVR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps2553d.pdf",
            })
    s.place("R388", "R", "66.5k 1% keyboard RGB 0.40A ILIM", 590, 45,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("KB_RGB_ILIM", "local"), "2": ("GND", "local")})
    s.place("R389", "R", "100k keyboard RGB enable default-off", 590, 60,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("KB_RGB_PWR_EN", "hier"), "2": ("GND", "local")})
    s.place("R390", "R", "10k keyboard RGB fault pull-up", 590, 75,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("KB_RGB_FAULT_N", "hier")})
    s.place("C322", "C", "100n keyboard RGB switch input", 590, 90,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("C323", "C", "100n keyboard RGB switch output", 590, 105,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("KB_FFC_5V", "local"), "2": ("GND", "local")})

    s.place("U311", "74AHCT1G126", "SN74AHCT1G126 keyboard RGB 3V3-to-5V buffer",
            520, 130, footprint=FOOTPRINTS["SN74AHCT1G126DBV"],
            pin_nets={
                "1": ("KB_RGB_PWR_EN", "hier"), "2": ("KB_RGB_DATA_3V3", "hier"),
                "3": ("GND", "local"), "4": ("KB_RGB_DATA_5V", "local"),
                "5": ("SYS_5V", "hier"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "SN74AHCT1G126DBVR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74ahct1g126.pdf",
            })
    s.place("R391", "R", "100k keyboard RGB data default-low", 590, 130,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("KB_RGB_DATA_3V3", "hier"), "2": ("GND", "local")})
    s.place("C324", "C", "100n keyboard RGB buffer local", 590, 145,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})

    s.place("R386", "R", "0R DNP DO-NOT-FIT keyboard 5V protection bypass", 450, 90,
            footprint=FOOTPRINTS["R"], dnp=True,
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("KB_FFC_5V", "local")})
    s.place("R387", "R", "0R DNP keyboard 3V3 option", 450, 105,
            footprint=FOOTPRINTS["R"], dnp=True,
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("KB_FFC_3V3", "local")})

    s.place("C318", "C", "100n DNP keyboard 3V3 reserve", 450, 120,
            footprint=FOOTPRINTS["C_100n"], dnp=True,
            pin_nets={"1": ("KB_FFC_3V3", "local"), "2": ("GND", "local")})
    s.place("C319", "C", "10u keyboard RGB switched-output bulk", 300, 95,
            footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("KB_FFC_5V", "local"), "2": ("GND", "local")})

    # Anchor the sheet-local GND label to the project's global ground net.
    # Without this symbol, J310 pins 1/30/MP form an isolated hierarchical net.
    s.gnd(500, 135)

    s.text(20, 230, "NOTES:")
    s.text(20, 237.62, "J310 is deliberately pin-reversed relative to J320 for two top-side FH12 bottom-contact connectors and a Type-A same-side FFC.")
    s.text(20, 245.24, "Specified cable: Molex 0150200315, 30 circuits, 0.5 mm pitch, 30 mm, Type A / same-side contacts.")
    s.text(20, 252.86, "R386/R387 stay DNP. U310 limits the future RGB rail below 0.5A/contact and defaults off; rev A has no RGB load.")
    s.text(20, 260.48, "J310 pin 3 / rev-A J320 pin 28 repurposes unused COL15 for RGB data. Rows 5..7 and COL14 remain spare.")
    s.text(20, 268.1, "Rev B must add local LED bulk capacitance and firmware must enforce a 325mA LED budget; unrestricted full-white is unsupported.")

    return s
