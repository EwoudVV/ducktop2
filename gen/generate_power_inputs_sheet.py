import os

from build_ducktop2 import Sheet, FOOTPRINTS, PROJDIR, U


def add_pd_input(s, port, x0, y0):
    jref = f"J{20 + port}"
    uref = f"U{40 + port}"
    rbase = 120 + (port - 1) * 10
    cbase = 120 + (port - 1) * 10

    vbus = f"VBUS_PD{port}"
    cc1 = f"PD{port}_CC1"
    cc2 = f"PD{port}_CC2"
    cfg1 = f"PD{port}_CFG1"
    chip_vdd = f"PD{port}_CH224_VDD"
    chip_vbus = f"PD{port}_CH224_VBUS_SENSE"
    chip_dpdm = f"PD{port}_CH224_DPDM"

    s.text(x0, y0, f"== {jref} USB-C PD sink input {port}: CH224K requests 15V ==")

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
    if port == 1:
        connector_nets.update({
            "A6": ("USB_DP1", "hier"), "B6": ("USB_DP1", "hier"),
            "A7": ("USB_DM1", "hier"), "B7": ("USB_DM1", "hier"),
        })
    else:
        connector_nets.update({
            "A6": ("", "nc"), "B6": ("", "nc"),
            "A7": ("", "nc"), "B7": ("", "nc"),
        })

    s.place(jref, "USB_C_Receptacle", f"USB-C PD input {port}", x0 + 35.56, y0 + 53.34,
            footprint=FOOTPRINTS["USB_C_Receptacle"], pin_nets=connector_nets)

    s.place(uref, "CH224K", f"CH224K 15V sink {port}", x0 + 116.84, y0 + 53.34,
            footprint=FOOTPRINTS["CH224K"],
            pin_nets={
                "1": (chip_vdd, "local"),
                "2": ("", "nc"),
                "3": ("", "nc"),
                "4": (chip_dpdm, "local"),
                "5": (chip_dpdm, "local"),
                "6": (cc2, "local"),
                "7": (cc1, "local"),
                "8": (chip_vbus, "local"),
                "9": (cfg1, "local"),
                "10": ("", "nc"),
                "11": ("GND", "local"),
            })

    s.place(f"R{rbase}", "R", "5.1k CH224 VDD feed", x0 + 83.82, y0 + 17.78,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vbus, "hier"), "2": (chip_vdd, "local")})
    s.place(f"R{rbase + 1}", "R", "5.1k VBUS sense", x0 + 83.82, y0 + 27.94,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vbus, "hier"), "2": (chip_vbus, "local")})
    s.place(f"R{rbase + 2}", "R", "56k CFG1 to GND (15V)", x0 + 162.56, y0 + 25.4,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (cfg1, "local"), "2": ("GND", "local")})

    s.place(f"C{cbase}", "C", "1u CH224 VDD", x0 + 162.56, y0 + 40.64,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": (chip_vdd, "local"), "2": ("GND", "local")})
    s.place(f"C{cbase + 1}", "C", "10u port VBUS", x0 + 162.56, y0 + 53.34,
            footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": (vbus, "hier"), "2": ("GND", "local")})

    s.pwrflag(x0 + 193.04, y0 + 35.56, chip_vdd)
    s.pwrflag(x0 + 193.04, y0 + 50.8, vbus)
    s.gnd(x0 + 193.04, y0 + 68.58)

    if port == 1:
        s.text(x0, y0 + 91.44, f"{jref}: D+/D- route to BQ25798 USB_DP1/USB_DM1 for fallback detection.")
    else:
        s.text(x0, y0 + 91.44, f"{jref}: power-only PD input; connector D+/D- are intentionally NC.")


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 50
    s.refcounters["#FLG"] = 50

    s.text(20, 12.7, "== USB-C power inputs: three CH224K PD sink triggers ==")
    s.text(20, 20.32, "Each CH224K uses resistor mode: CFG1=56k to GND requests 15V; CFG2/CFG3 are NC.")
    s.text(20, 27.94, "CH224K performs USB-C PD negotiation; BQ25798 on sheet 1 is the buck-boost charger / NVDC power path.")
    s.text(20, 35.56, "Only J21 carries USB2 D+/D- to BQ25798; J22/J23 are power-only charge inputs.")

    add_pd_input(s, 1, 20.32, 50.8)
    add_pd_input(s, 2, 20.32, 157.48)
    add_pd_input(s, 3, 20.32, 264.16)

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
