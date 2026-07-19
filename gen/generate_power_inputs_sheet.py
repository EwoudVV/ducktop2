import os

from build_ducktop2 import Sheet, FOOTPRINTS, PROJDIR, U


def add_pd_input(s, port, x0, y0):
    jref = f"J{20 + port}"
    uref = f"U{40 + port}"
    rbase = 120 + (port - 1) * 10
    cbase = 120 + (port - 1) * 10

    vbus = f"PD{port}_VBUS_RAW"
    cc1 = f"PD{port}_CC1"
    cc2 = f"PD{port}_CC2"
    cfg1 = f"PD{port}_CFG1"
    chip_vhv = f"PD{port}_CH224_VHV"
    chip_vbus = f"PD{port}_CH224_VBUS_SENSE"
    i2c_scl = f"PD{port}_I2C_SCL"
    i2c_sda = f"PD{port}_I2C_SDA"
    chip_i2c_scl = f"PD{port}_CH224_SCL"
    chip_i2c_sda = f"PD{port}_CH224_SDA"

    s.text(x0, y0, f"== {jref} USB-C PD sink input {port}: CH224A requests 15V and reports PDO current ==")

    connector_nets = {
        "A1": ("GND", "local"), "A12": ("GND", "local"),
        "B1": ("GND", "local"), "B12": ("GND", "local"),
        "SH": ("GND", "local"),
        "A4": (vbus, "hier"), "A9": (vbus, "hier"),
        "B4": (vbus, "hier"), "B9": (vbus, "hier"),
        "A5": (cc1, "local"), "B5": (cc2, "local"),
        "A2": ("", "nc"), "A3": ("", "nc"),
        "B2": ("", "nc"), "B3": ("", "nc"),
        "A10": ("", "nc"), "A11": ("", "nc"),
        "B10": ("", "nc"), "B11": ("", "nc"),
        "A8": ("", "nc"), "B8": ("", "nc"),
    }
    connector_nets.update({
        "A6": ("", "nc"), "B6": ("", "nc"),
        "A7": ("", "nc"), "B7": ("", "nc"),
    })

    s.place(jref, "USB_C_Receptacle", f"USB-C PD input {port}", x0 + 35.56, y0 + 53.34,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets=connector_nets,
            extra_props={"Manufacturer": "Molex", "MPN": "105450-0101"})
    s.place(f"U{113 + port * 10}", "TPD4E05U06DQA", f"TPD4E05U06 CC ESD port {port}",
            x0 + 60.96, y0 + 76.2, footprint=FOOTPRINTS["TPD4E05U06DQA"],
            pin_nets={
                "1": (cc1, "local"), "2": (cc2, "local"),
                "3": ("GND", "local"), "4": ("", "nc"), "5": ("", "nc"),
                "6": ("", "nc"), "7": ("", "nc"), "8": ("GND", "local"),
                "9": ("", "nc"), "10": ("", "nc"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPD4E05U06DQAR"})

    s.place(uref, "CH224A", f"CH224A 15V sink {port}", x0 + 116.84, y0 + 53.34,
            footprint=FOOTPRINTS["CH224A"],
            pin_nets={
                "1": (chip_vhv, "local"),
                "2": (chip_i2c_scl, "local"),
                "3": (chip_i2c_sda, "local"),
                # USB-C PD negotiation uses CC1/CC2. Keep CH224A DP/DM open so its
                # legacy-QC transceiver cannot contend with the BQ25798 D+/D-
                # detector on the primary input.
                "4": ("", "nc"),
                "5": ("", "nc"),
                "6": (cc2, "local"),
                "7": (cc1, "local"),
                "8": (chip_vbus, "local"),
                "9": (cfg1, "local"),
                "10": ("", "nc"),
                "11": ("GND", "local"),
            },
            extra_props={
                "Manufacturer": "WCH",
                "MPN": "CH224A",
                "AutonomousColdStartContract": "RAW_VBUS_4_TO_30V;CFG1_56K_REQUESTS_15V_WITHOUT_EC;15V_PDO_REQUIRED_FOR_SYSTEM_BOOT",
            })

    s.place(f"R{rbase}", "R", "0R CH224A VHV link", x0 + 83.82, y0 + 17.78,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vbus, "local"), "2": (chip_vhv, "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603JR-070RL"})
    s.place(f"R{rbase + 1}", "R", "0R CH224A VBUS sense link", x0 + 83.82, y0 + 27.94,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vbus, "local"), "2": (chip_vbus, "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603JR-070RL"})
    s.place(f"R{rbase + 2}", "R", "56k CFG1 to GND (15V)", x0 + 162.56, y0 + 25.4,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (cfg1, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0756KL"})
    s.place(f"R{rbase + 3}", "R", "100R CH224A SCL series damping", x0 + 116.84, y0 + 81.28,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (i2c_scl, "hier"), "2": (chip_i2c_scl, "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100RL"})
    s.place(f"R{rbase + 4}", "R", "100R CH224A SDA series damping", x0 + 162.56, y0 + 81.28,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (i2c_sda, "hier"), "2": (chip_i2c_sda, "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100RL"})

    s.place(f"C{cbase}", "C", "1u 50V X7R CH224A VHV", x0 + 162.56, y0 + 40.64,
            footprint=FOOTPRINTS["C_0805"],
            pin_nets={"1": (chip_vhv, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BR71H105KA12L"})
    # Keep total pre-attach sink capacitance below the USB Type-C 10 uF
    # maximum even with +20% capacitor tolerance and shared AON capacitance.
    # The 10 uF energy storage remains after the default-off TPS26630 eFuse.
    s.place(f"C{cbase + 1}", "C", "1u 50V X7R port VBUS", x0 + 162.56, y0 + 53.34,
            footprint=FOOTPRINTS["C_0805"],
            pin_nets={"1": (vbus, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BR71H105KA12L"})

    s.pwrflag(x0 + 193.04, y0 + 35.56, chip_vhv)
    s.pwrflag(x0 + 193.04, y0 + 50.8, vbus)
    s.gnd(x0 + 193.04, y0 + 68.58)

    s.text(x0, y0 + 91.44, f"{jref}: power-only PD input; CH224A D+/D- are NC; 100R-damped muxed I2C reports PDO current.")


def add_pd_efuse(s, port, x0, y0):
    uref = f"U{719 + port}"
    rbase = 800 + (port - 1) * 10
    cbase = 800 + (port - 1) * 10
    raw = f"PD{port}_VBUS_RAW"
    gated = f"PD{port}_VBUS_GATED"
    uv = f"PD{port}_EFUSE_UV"
    ov = f"PD{port}_EFUSE_OV"
    shdn = f"PD{port}_EFUSE_SHDN_N"
    ilim = f"PD{port}_EFUSE_ILIM"
    dvdt = f"PD{port}_EFUSE_DVDT"
    fault = f"PD{port}_EFUSE_FAULT_N"
    path_en = f"PD{port}_PATH_EN"

    s.place(uref, "TPS26630RGE", f"TPS26630RGER PD{port} default-off 3A eFuse", x0, y0,
            footprint=FOOTPRINTS["TPS26630RGE"],
            pin_nets={
                "1": (raw, "local"), "2": (raw, "local"),
                "3": ("", "nc"), "4": ("", "nc"), "5": (raw, "local"),
                "6": (uv, "local"), "7": (ov, "local"), "8": ("GND", "local"),
                "9": (dvdt, "local"), "10": (ilim, "local"), "11": ("", "nc"),
                "12": (shdn, "local"), "13": ("", "nc"), "14": (fault, "hier"),
                "15": ("GND", "local"), "16": ("", "nc"),
                "17": (gated, "local"), "18": (gated, "local"),
                "19": ("", "nc"), "20": ("", "nc"), "21": ("", "nc"),
                "22": ("", "nc"), "23": ("", "nc"), "24": ("", "nc"),
                "25": ("GND", "local"),
            }, extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS26630RGER"})
    for ref, value, net_a, net_b, mpn in (
        (f"R{rbase}", "887k 0.1% PD eFuse UV/OV top", raw, uv, "RT0603BRD07887KL"),
        (f"R{rbase + 1}", "27.4k 0.1% PD eFuse UV/OV middle", uv, ov, "RT0603BRD0727K4L"),
        (f"R{rbase + 2}", "68.1k 0.1% PD eFuse UV/OV bottom", ov, "GND", "RT0603BRD0768K1L"),
        (f"R{rbase + 3}", "6.04k 1% PD eFuse 2.98A ILIM", ilim, "GND", "RC0603FR-076K04L"),
        (f"R{rbase + 4}", "47k PD eFuse SHDN default-off pulldown", shdn, "GND", "RC0603FR-0747KL"),
        (f"R{rbase + 5}", "10k PD path-enable series", path_en, shdn, "RC0603FR-0710KL"),
        (f"R{rbase + 6}", "10k PD eFuse FLT pull-up", "MCU_3V3", fault, "RC0603FR-0710KL"),
    ):
        kind_a = "hier" if net_a in (path_en, "MCU_3V3") else "local"
        kind_b = "hier" if net_b == fault else "local"
        s.place(ref, "R", value, x0 + 60, y0 - 30 + (int(ref[1:]) - rbase) * 10,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net_a, kind_a), "2": (net_b, kind_b)},
                extra_props={"Manufacturer": "Yageo", "MPN": mpn})
    for ref, value, net, fp, mpn in (
        (f"C{cbase}", "1u 50V PD eFuse input", raw, "C_0805", "GRM21BR71H105KA12L"),
        (f"C{cbase + 1}", "100n 50V PD eFuse input HF", raw, "C_100n", "GRM188R71H104KA93D"),
        (f"C{cbase + 2}", "10u 50V PD eFuse output", gated, "C_10u", "CGA5L1X7R1H106K160AC"),
        (f"C{cbase + 3}", "22n PD eFuse dVdT", dvdt, "C_0402", "GRM155R71H223KA12D"),
    ):
        s.place(ref, "C", value, x0 + 115, y0 - 15 + (int(ref[1:]) - cbase) * 12.7,
                footprint=FOOTPRINTS[fp], pin_nets={"1": (net, "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata" if ref != f"C{cbase + 2}" else "TDK", "MPN": mpn})


def add_selector_fet(s, ref, x, y, gate, common_source, drain, drain_kind):
    s.place(ref, "Q_PMOS_1G_234S_5D", "SiSS4409DN 40V reverse-blocking PMOS", x, y,
            footprint=FOOTPRINTS["Q_SiSS4409DN"],
            pin_nets={
                "1": (gate, "local"),
                "2": (common_source, "local"),
                "3": (common_source, "local"),
                "4": (common_source, "local"),
                "5": (drain, drain_kind),
            },
            extra_props={"Manufacturer": "Vishay", "MPN": "SiSS4409DN-T1-GE3"})


def add_pd_selector(s):
    s.text(250, 50.8, "== U14 LTC4417IGN: qualified, prioritized selection of the three negotiated 15V inputs ==")
    s.place("U14", "LTC4417CGN", "LTC4417IGN#PBF three-input PD selector", 315, 170,
            footprint=FOOTPRINTS["LTC4417IGN"],
            pin_nets={
                "1": ("", "nc"), "2": ("", "nc"), "3": ("GND", "local"),
                "4": ("PD1_UV", "local"), "5": ("PD1_OV", "local"),
                "6": ("PD2_UV", "local"), "7": ("PD2_OV", "local"),
                "8": ("PD3_UV", "local"), "9": ("PD3_OV", "local"),
                "10": ("PD1_VALID_N", "hier"), "11": ("PD2_VALID_N", "hier"),
                "12": ("PD3_VALID_N", "hier"),
                "13": ("GND", "local"), "14": ("", "nc"),
                "15": ("USB_PD_SELECTED", "hier"),
                "16": ("PD3_GATE", "local"), "17": ("PD3_FET_COMMON", "local"),
                "18": ("PD2_GATE", "local"), "19": ("PD2_FET_COMMON", "local"),
                "20": ("PD1_GATE", "local"), "21": ("PD1_FET_COMMON", "local"),
                "22": ("PD3_VBUS_GATED", "local"),
                "23": ("PD2_VBUS_GATED", "local"),
                "24": ("PD1_VBUS_GATED", "local"),
            },
            extra_props={"Manufacturer": "Analog Devices", "MPN": "LTC4417IGN#PBF"})

    for ref, valid, x in (
        ("R736", "PD1_VALID_N", 555),
        ("R737", "PD2_VALID_N", 595),
        ("R738", "PD3_VALID_N", 635),
    ):
        s.place(ref, "R", "10k VALID open-drain pull-up", x, 170,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": ("MCU_3V3", "hier"), "2": (valid, "hier")})

    for idx, (qa, qb, y) in enumerate((("Q15", "Q16", 85), ("Q17", "Q18", 135), ("Q19", "Q20", 185)), start=1):
        add_selector_fet(s, qa, 390, y, f"PD{idx}_GATE", f"PD{idx}_FET_COMMON", f"PD{idx}_VBUS_GATED", "local")
        add_selector_fet(s, qb, 445, y, f"PD{idx}_GATE", f"PD{idx}_FET_COMMON", "USB_PD_SELECTED", "hier")

    for idx, base in enumerate((720, 723, 726), start=1):
        x = 260 + (idx - 1) * 85
        s.place(f"R{base}", "R", "1.00M 0.1% 15V UV top", x, 270, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (f"PD{idx}_VBUS_GATED", "local"), "2": (f"PD{idx}_UV", "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD071ML"})
        s.place(f"R{base + 1}", "R", "19.6k 0.1% 15V window middle", x, 282.7, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (f"PD{idx}_UV", "local"), "2": (f"PD{idx}_OV", "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0719K6L"})
        s.place(f"R{base + 2}", "R", "63.4k 0.1% 15V OV bottom", x, 295.4, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (f"PD{idx}_OV", "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0763K4L"})

    for ref, net, x, y in (
        ("C730", "PD1_VBUS_GATED", 500, 82.5), ("C731", "PD2_VBUS_GATED", 500, 107.5),
        ("C732", "PD3_VBUS_GATED", 500, 132.5), ("C733", "PD1_FET_COMMON", 500, 157.5),
        ("C734", "PD2_FET_COMMON", 500, 182.5), ("C735", "PD3_FET_COMMON", 500, 207.5),
    ):
        s.place(ref, "C", "100n 50V selector local", x, y, footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (net, "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D"})
    s.place("C736", "C", "10u 25V selected-PD output", 500, 232.5, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("USB_PD_SELECTED", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    s.place("C737", "C_Polarized", "100u 35V hybrid selected-PD hold-up", 500, 245,
            footprint=FOOTPRINTS["C_100u_35V_hybrid"],
            pin_nets={"1": ("USB_PD_SELECTED", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Panasonic", "MPN": "EEHZK1V101XP"})

    s.text(250, 320, "Priority is J21, then J22, then J23; every input must validate inside approximately 13.1V to 17.1V.")
    s.text(250, 327.66, "Q15-Q20 are common-source back-to-back pairs, so inactive adapters are reverse-isolated instead of diode-ORed.")
    s.text(250, 335.28, "EN/SHDN use LTC4417 internal pull-ups; HYS is grounded; VALID1/2/3 have external 10k pull-ups to always-on MCU_3V3.")
    s.text(250, 342.9, "U720-U722 enforce 3A current limits and default off; EC validates CH224A PDO current before enabling exactly one path.")
    s.text(250, 350.52, "C737 provides low-ESR hold-up through LTC4417 break-before-make adapter switching.")


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 50
    s.refcounters["#FLG"] = 50

    s.text(20, 12.7, "== USB-C power inputs: three CH224A PD sink controllers ==")
    s.text(20, 20.32, "Raw 5V attachment powers CH224A directly; CFG1=56k autonomously requests 15V without EC firmware.")
    s.text(20, 27.94, "Only a source offering the 15V PDO crosses the 6.06-6.36V AON UVLO and boots the EC; a 5V-only source leaves the laptop off.")
    s.text(20, 35.56, "CH224A reports negotiated PDO current; LTC4417 validates, prioritizes, and reverse-isolates the three adapters.")
    s.text(20, 43.18, "All three ports are power-only. USB D+/D- stay open because the selected source can change after arbitration.")

    add_pd_input(s, 1, 20.32, 50.8)
    add_pd_input(s, 2, 20.32, 157.48)
    add_pd_input(s, 3, 20.32, 264.16)
    add_pd_efuse(s, 1, 560, 80)
    add_pd_efuse(s, 2, 560, 190)
    add_pd_efuse(s, 3, 560, 300)
    add_pd_selector(s)

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
