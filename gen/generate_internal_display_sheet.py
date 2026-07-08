from build_ducktop2 import Sheet, FOOTPRINTS


EDP_PIN_NETS = {
    "3": "EDP_TX3_N", "4": "EDP_TX3_P",
    "6": "EDP_TX2_N", "7": "EDP_TX2_P",
    "9": "EDP_TX1_N", "10": "EDP_TX1_P",
    "12": "EDP_TX0_N", "13": "EDP_TX0_P",
    "15": "EDP_AUX_P", "16": "EDP_AUX_N",
    "27": "EDP_HPD",
}


EDP_GND_PINS = ["2", "5", "8", "11", "14", "17", "23", "24", "25", "26", "28", "29", "30", "31"]


def source_connector_nets():
    nets = {pin: ("GND", "local") for pin in EDP_GND_PINS}
    for pin, net in EDP_PIN_NETS.items():
        nets[pin] = (net, "local")
    for pin in ["1", "18", "19", "20", "21", "32", "33", "34", "35", "36", "37", "38", "39", "40"]:
        nets[pin] = ("", "nc")
    nets["22"] = ("GND", "local")
    return nets


def panel_connector_nets():
    nets = {pin: ("GND", "local") for pin in EDP_GND_PINS}
    for pin, net in EDP_PIN_NETS.items():
        nets[pin] = (net, "local")
    for pin in ["18", "19", "20", "21"]:
        nets[pin] = ("LCD_3V3", "local")
    for pin in ["36", "37", "38", "39"]:
        nets[pin] = ("LCD_BL_PWR", "local")
    nets.update({
        "1": ("", "nc"),
        "22": ("GND", "local"),
        "32": ("LCD_BL_EN", "hier"),
        "33": ("LCD_BL_PWM", "hier"),
        "34": ("", "nc"),
        "35": ("", "nc"),
        "40": ("", "nc"),
    })
    return nets


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 140
    s.refcounters["#FLG"] = 140

    s.text(20, 12.7, "== Internal eDP display and touch harness ==")
    s.text(20, 20.32, "LattePanda Mu DDIA/eDP is on the module's own 40-pin I-PEX 20455-040E connector, not the SODIMM edge.")
    s.text(20, 27.94, "This sheet models the internal harness/adapter from that Mu eDP connector to the laptop panel path.")

    # ---------------- eDP source and panel connectors ----------------
    s.text(20, 50.8, "== eDP 4-lane source-to-panel harness ==")
    s.place("J80", "Conn_01x40", "Mu eDP source cable input (I-PEX 20455-040E mate TBD)", 145, 145,
            footprint="", pin_nets=source_connector_nets())
    s.place("J81", "Conn_01x40", "Internal 16in 2K eDP panel connector", 330, 145,
            footprint=FOOTPRINTS["Conn_01x40_FFC"], pin_nets=panel_connector_nets())

    # ---------------- Panel and backlight power ----------------
    s.text(520, 50.8, "== Panel power injection ==")
    s.place("F80", "Fuse", "1A LCD_3V3 resettable fuse", 520, 76.2, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("LCD_3V3", "local")})
    s.place("F81", "Fuse", "2A backlight resettable fuse", 520, 101.6, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("LCD_BL_PWR", "local")})
    s.place("C260", "C", "10u LCD_3V3 bulk", 610, 76.2, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("LCD_3V3", "local"), "2": ("GND", "local")})
    s.place("C261", "C", "100n LCD_3V3", 610, 88.9, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LCD_3V3", "local"), "2": ("GND", "local")})
    s.place("C262", "C", "22u backlight bulk", 610, 101.6, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("LCD_BL_PWR", "local"), "2": ("GND", "local")})
    s.place("C263", "C", "100n backlight", 610, 114.3, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LCD_BL_PWR", "local"), "2": ("GND", "local")})
    s.pwrflag(685, 76.2, "LCD_3V3")
    s.pwrflag(685, 101.6, "LCD_BL_PWR")

    # ---------------- Touch/control FFC ----------------
    s.text(520, 160.02, "== Optional I2C touch/control FFC ==")
    s.place("J82", "Conn_01x06", "I2C touch FFC per Mu reference pinout", 590, 200.66,
            footprint=FOOTPRINTS["Conn_01x06"],
            pin_nets={
                "1": ("I2C_SCL", "hier"),
                "2": ("I2C_SDA", "hier"),
                "3": ("GND", "local"),
                "4": ("TOUCH_RESET_N", "hier"),
                "5": ("TOUCH_INT_N", "hier"),
                "6": ("MCU_3V3", "hier"),
            })
    s.place("R260", "R", "100k touch reset pull-up", 520, 190.5, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TOUCH_RESET_N", "hier")})
    s.place("R261", "R", "100k touch INT pull-up", 520, 203.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("TOUCH_INT_N", "hier")})
    s.place("C264", "C", "1u touch 3V3", 520, 215.9, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})

    # ---------------- EC/display service pins ----------------
    s.text(520, 260.35, "== EC display service controls ==")
    s.place("J83", "Conn_01x08", "DNP display debug/service", 590, 307.34,
            footprint=FOOTPRINTS["Conn_01x08"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("LCD_BL_PWM", "hier"),
                "3": ("LCD_BL_EN", "hier"),
                "4": ("PANEL_PWR_EN", "hier"),
                "5": ("PANEL_RESET_N", "hier"),
                "6": ("I2C_SCL", "hier"),
                "7": ("I2C_SDA", "hier"),
                "8": ("MCU_3V3", "hier"),
            })
    s.place("R262", "R", "100k panel power default off", 520, 284.48, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PANEL_PWR_EN", "hier"), "2": ("GND", "local")})
    s.place("R263", "R", "100k panel reset pull-up", 520, 297.18, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("PANEL_RESET_N", "hier")})

    s.gnd(700, 330.2)
    s.text(20, 310, "NOTES:")
    s.text(20, 317.5, "J80 high-speed pins follow the Mu eDP source connector; power/backlight pins are not pass-through to avoid backfeed.")
    s.text(20, 325.12, "J81 follows the 40-pin eDP pinout in gen/Pinouts_README.md: lanes 3..0, AUX, HPD, LCD_3V3, BL_PWR, BL_EN/PWM.")
    s.text(20, 332.74, "J82 provides the reference I2C touch pinout; keep the separate USB touch header if the reused 16in panel uses USB touch.")
    s.text(20, 340.36, "Exact J80/J81 mechanical footprints and cable orientation still need the real panel/controller hardware on the bench.")

    return s
