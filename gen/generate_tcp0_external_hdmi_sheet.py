from build_ducktop2 import Sheet, FOOTPRINTS


HDMI_LINES = [
    ("TCP0_TXRX0_P", "EXT_HDMI_D2_P"),
    ("TCP0_TXRX0_N", "EXT_HDMI_D2_N"),
    ("TCP0_TX1_P", "EXT_HDMI_D1_P"),
    ("TCP0_TX1_N", "EXT_HDMI_D1_N"),
    ("TCP0_TX0_P", "EXT_HDMI_D0_P"),
    ("TCP0_TX0_N", "EXT_HDMI_D0_N"),
    ("TCP0_TXRX1_P", "EXT_HDMI_CK_P"),
    ("TCP0_TXRX1_N", "EXT_HDMI_CK_N"),
]


def hdmi_connector_nets():
    return {
        "1": ("EXT_HDMI_D2_P", "local"),
        "2": ("GND", "local"),
        "3": ("EXT_HDMI_D2_N", "local"),
        "4": ("EXT_HDMI_D1_P", "local"),
        "5": ("GND", "local"),
        "6": ("EXT_HDMI_D1_N", "local"),
        "7": ("EXT_HDMI_D0_P", "local"),
        "8": ("GND", "local"),
        "9": ("EXT_HDMI_D0_N", "local"),
        "10": ("EXT_HDMI_CK_P", "local"),
        "11": ("GND", "local"),
        "12": ("EXT_HDMI_CK_N", "local"),
        "13": ("EXT_HDMI_CEC", "local"),
        "14": ("", "nc"),
        "15": ("EXT_HDMI_SCL_CONN", "local"),
        "16": ("EXT_HDMI_SDA_CONN", "local"),
        "17": ("GND", "local"),
        "18": ("EXT_HDMI_5V", "local"),
        "19": ("EXT_HDMI_HPD_CONN", "local"),
        "SH": ("GND", "local"),
    }


def hdmi_esd(s, ref, value, x, y, nets):
    s.place(ref, "TPD4E02B04DQA", value, x, y, footprint=FOOTPRINTS["TPD4E02B04DQA"],
            unit=1,
            pin_nets={
                "1": (nets[0], "local"),
                "2": (nets[1], "local"),
                "3": ("GND", "local"),
                "4": (nets[2], "local"),
                "5": (nets[3], "local"),
                "6": ("", "nc"),
                "7": ("", "nc"),
                "8": ("GND", "local"),
                "9": ("", "nc"),
                "10": ("", "nc"),
            })


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 80
    s.refcounters["#FLG"] = 80

    s.text(20, 12.7, "== TCP0 external HDMI 2.0 output ==")
    s.text(20, 20.32, "LattePanda Mu default BIOS maps TCP0 as HDMI 2.0; DDIB remains the internal Intehill display.")
    s.text(20, 27.94, "This sheet is the user-accessible external HDMI-A connector for a second monitor.")

    s.text(20, 50.8, "== J30 external HDMI-A connector ==")
    s.place("J30", "HDMI_A", "External HDMI-A from TCP0", 115, 125,
            footprint=FOOTPRINTS["HDMI_A"], pin_nets=hdmi_connector_nets())

    for i, (source, conn) in enumerate(HDMI_LINES):
        x = 250 + (i % 4) * 55
        y = 82.55 + (i // 4) * 25.4
        s.place(f"C{150 + i}", "C", "100n HDMI AC cap", x, y, footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (source, "hier"), "2": (conn, "local")})
        s.place(f"R{150 + i}", "R", "470R HDMI bias per Mu ref", x, y + 10.16, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (conn, "local"), "2": ("GND", "local")})

    hdmi_esd(s, "U50", "TPD4E02B04DQA HDMI2.0 TMDS ESD A", 250, 160,
             ["EXT_HDMI_D2_P", "EXT_HDMI_D2_N", "EXT_HDMI_D1_P", "EXT_HDMI_D1_N"])
    hdmi_esd(s, "U51", "TPD4E02B04DQA HDMI2.0 TMDS ESD B", 390, 160,
             ["EXT_HDMI_D0_P", "EXT_HDMI_D0_N", "EXT_HDMI_CK_P", "EXT_HDMI_CK_N"])
    hdmi_esd(s, "U52", "TPD4E02B04DQA HDMI sideband ESD", 530, 160,
             ["EXT_HDMI_SCL_CONN", "EXT_HDMI_SDA_CONN", "EXT_HDMI_HPD_CONN", "EXT_HDMI_CEC"])

    s.place("F150", "Fuse", "100mA HDMI 5V detect fuse", 520, 76.2,
            footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("EXT_HDMI_5V", "local")})
    s.place("C158", "C", "1u HDMI 5V", 600, 76.2, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("GND", "local")})
    s.place("R158", "R", "2.2k HDMI DDC SCL pull-up", 520, 101.6, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("EXT_HDMI_SCL_CONN", "local")})
    s.place("R159", "R", "2.2k HDMI DDC SDA pull-up", 520, 114.3, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("EXT_HDMI_5V", "local"), "2": ("EXT_HDMI_SDA_CONN", "local")})
    s.place("R160", "R", "100R HPD series", 520, 127, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TCP0_HPD", "hier"), "2": ("EXT_HDMI_HPD_CONN", "local")})
    s.place("R161", "R", "100R DDC SCL series", 520, 139.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TCP0_DDC_SCL", "hier"), "2": ("EXT_HDMI_SCL_CONN", "local")})
    s.place("R162", "R", "100R DDC SDA series", 520, 152.4, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("TCP0_DDC_SDA", "hier"), "2": ("EXT_HDMI_SDA_CONN", "local")})
    s.pwrflag(665, 76.2, "EXT_HDMI_5V")
    s.gnd(665, 101.6)

    s.text(20, 220.98, "NOTES:")
    s.text(20, 228.6, "J30 is the outside-world HDMI jack; sheet 11 J300 remains only the internal Intehill HDMI plug.")
    s.text(20, 236.22, "CEC is ESD-protected but not connected to the Mu or EC in this pass.")
    s.text(20, 243.84, "Pre-layout must verify TCP0 HDMI lane order/polarity against the selected Mu BIOS/reference design.")
    s.text(20, 251.46, "Treat this as HDMI 2.0/18Gbps capable: short routing, low-cap ESD, solid return path, no HDMI 1.4-only parts.")
    s.text(20, 259.08, "TCP1 remains the better future candidate for a Type-C video/PD port if a later BIOS/display plan needs it.")

    return s
