import os
from build_ducktop2 import Sheet, U, PROJDIR, FOOTPRINTS


def build(sheet_symbol_uuid, pwr_start=3, flg_start=4):
    s = Sheet(f"/{sheet_symbol_uuid}")
    # continue global numbering for #PWR/#FLG pseudo-refs so they don't collide
    # with the ones already used on the Power & Battery sheet.
    s.refcounters["#PWR"] = pwr_start
    s.refcounters["#FLG"] = flg_start

    class Cur:
        def __init__(self, x0, y0, col_w=55, row_h=10, rows_per_col=22):
            self.x0, self.y0, self.col_w, self.row_h, self.rows = x0, y0, col_w, row_h, rows_per_col
            self.i = 0

        def next(self):
            col, row = divmod(self.i, self.rows)
            self.i += 1
            return (self.x0 + col * self.col_w, self.y0 + row * self.row_h)

    # ---------------- U4: STM32F407VGTx EC/MCU core ----------------
    s.text(20, 20, "== U4 STM32F407VGTx EC/MCU Core ==")
    s.place("U4", "STM32F407VGTx", "STM32F407VGTx", 250, 400,
            footprint="Package_QFP:LQFP-100_14x14mm_P0.5mm",
            pin_nets={
                "1": ("KB_ROW2", "local"), "2": ("KB_ROW3", "local"), "3": ("KB_ROW4", "local"),
                "4": ("KB_ROW5", "local"), "5": ("KB_ROW6", "local"), "6": ("MCU_3V3", "hier"),
                "7": ("", "nc"), "8": ("LSE_IN", "local"), "9": ("LSE_OUT", "local"),
                "10": ("GND", "local"), "11": ("MCU_3V3", "hier"), "12": ("HSE_IN", "local"),
                "13": ("HSE_OUT", "local"), "14": ("NRST_NET", "local"), "15": ("", "nc"),
                "16": ("", "nc"), "17": ("", "nc"), "18": ("", "nc"), "19": ("MCU_3V3", "hier"),
                "20": ("GND", "local"), "21": ("MCU_3V3", "hier"), "22": ("MCU_3V3", "hier"),
                "23": ("EC_GPIO0", "local"), "24": ("BQ_ALERT", "hier"), "25": ("CHG_INT_N", "hier"),
                "26": ("PMIC_QON", "hier"), "27": ("GND", "local"), "28": ("MCU_3V3", "hier"),
                "29": ("CHG_CE_N", "hier"), "30": ("EC_GPIO1", "local"), "31": ("EC_GPIO2", "local"),
                "32": ("EC_GPIO3", "local"), "33": ("", "nc"), "34": ("", "nc"),
                "35": ("EC_GPIO8", "local"), "36": ("EC_GPIO9", "local"), "37": ("EC_GPIO10", "local"),
                "38": ("KB_ROW7", "local"), "39": ("", "nc"), "40": ("", "nc"), "41": ("", "nc"),
                "42": ("", "nc"), "43": ("", "nc"), "44": ("", "nc"), "45": ("", "nc"), "46": ("", "nc"),
                "47": ("", "nc"), "48": ("", "nc"), "49": ("VCAP1_NODE", "local"), "50": ("MCU_3V3", "hier"),
                "51": ("EC_GPIO13", "local"), "52": ("EC_GPIO14", "local"), "53": ("EC_GPIO15", "local"),
                "54": ("", "nc"), "55": ("KB_COL8", "local"), "56": ("KB_COL9", "local"),
                "57": ("KB_COL10", "local"), "58": ("KB_COL11", "local"), "59": ("KB_COL12", "local"),
                "60": ("KB_COL13", "local"), "61": ("KB_COL14", "local"), "62": ("KB_COL15", "local"),
                "63": ("", "nc"), "64": ("", "nc"), "65": ("", "nc"), "66": ("", "nc"),
                "67": ("EC_GPIO4", "local"), "68": ("EC_GPIO5", "local"), "69": ("EC_GPIO6", "local"),
                "70": ("MCU_USB_DM", "hier"), "71": ("MCU_USB_DP", "hier"), "72": ("SWDIO_NET", "local"),
                "73": ("VCAP2_NODE", "local"), "74": ("GND", "local"), "75": ("MCU_3V3", "hier"),
                "76": ("SWCLK_NET", "local"), "77": ("EC_GPIO7", "local"), "78": ("", "nc"),
                "79": ("", "nc"), "80": ("", "nc"), "81": ("KB_COL0", "local"), "82": ("KB_COL1", "local"),
                "83": ("KB_COL2", "local"), "84": ("KB_COL3", "local"), "85": ("KB_COL4", "local"),
                "86": ("KB_COL5", "local"), "87": ("KB_COL6", "local"), "88": ("KB_COL7", "local"),
                "89": ("", "nc"), "90": ("", "nc"), "91": ("", "nc"), "92": ("I2C_SCL", "hier"),
                "93": ("I2C_SDA", "hier"), "94": ("BOOT0_NET", "local"), "95": ("EC_GPIO11", "local"),
                "96": ("EC_GPIO12", "local"), "97": ("KB_ROW0", "local"), "98": ("KB_ROW1", "local"),
                "99": ("GND", "local"), "100": ("MCU_3V3", "hier"),
            })

    # ---------------- Power-supply decoupling / VCAPs / VDDA ----------------
    s.text(20, 40, "-- U4 decoupling (one 100n per VDD pin, per datasheet) --")
    c1 = Cur(20, 50)
    for i in range(6):
        s.place(f"C{20+i}", "C", "100n", *c1.next(), footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C26", "C", "4.7u (bulk)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C27", "C", "100n (VBAT)", *c1.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C28", "C", "1u (VDDA)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C29", "C", "2.2u (VCAP_1, mandatory)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("VCAP1_NODE", "local"), "2": ("GND", "local")})
    s.place("C30", "C", "2.2u (VCAP_2, mandatory)", *c1.next(), footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("VCAP2_NODE", "local"), "2": ("GND", "local")})

    # ---------------- NRST / BOOT0 ----------------
    s.text(20, 170, "-- NRST filter/button, BOOT0 strap --")
    c2 = Cur(20, 180)
    s.place("R32", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("NRST_NET", "local")})
    s.place("C31", "C", "100n", *c2.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("NRST_NET", "local"), "2": ("GND", "local")})
    s.place("SW1", "SW_Push", "Reset", *c2.next(), footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("NRST_NET", "local"), "2": ("GND", "local")})
    s.place("R33", "R", "10k", *c2.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BOOT0_NET", "local"), "2": ("GND", "local")})

    # ---------------- HSE / LSE crystals ----------------
    s.text(20, 230, "-- HSE 8MHz + LSE 32.768kHz crystals --")
    c3 = Cur(20, 240)
    s.place("Y1", "Crystal", "8MHz HSE", *c3.next(), footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={"1": ("HSE_IN", "local"), "2": ("HSE_OUT", "local")})
    s.place("C32", "C", "18p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HSE_IN", "local"), "2": ("GND", "local")})
    s.place("C33", "C", "18p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("HSE_OUT", "local"), "2": ("GND", "local")})
    s.place("Y2", "Crystal", "32.768kHz LSE", *c3.next(), footprint=FOOTPRINTS["Crystal_LSE"],
            pin_nets={"1": ("LSE_IN", "local"), "2": ("LSE_OUT", "local")})
    s.place("C34", "C", "12p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LSE_IN", "local"), "2": ("GND", "local")})
    s.place("C35", "C", "12p", *c3.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("LSE_OUT", "local"), "2": ("GND", "local")})

    # ---------------- SWD debug header ----------------
    s.text(20, 320, "-- SWD debug header --")
    s.place("J4", "Conn_01x04", "SWD (VDD/SWDIO/SWCLK/GND)", 20, 330,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("SWDIO_NET", "local"),
                      "3": ("SWCLK_NET", "local"), "4": ("GND", "local")})

    s.gnd(20, 360)
    s.pwrflag(20, 380, "MCU_3V3")

    # ---------------- Keyboard matrix headers ----------------
    s.text(450, 20, "== Keyboard Matrix (8 rows x 16 cols, diodes on membrane PCB) ==")
    s.place("J5", "Conn_01x08", "KB rows (PE0-7)", 450, 60,
            footprint=FOOTPRINTS["Conn_01x08"],
            pin_nets={
                "1": ("KB_ROW0", "local"), "2": ("KB_ROW1", "local"), "3": ("KB_ROW2", "local"),
                "4": ("KB_ROW3", "local"), "5": ("KB_ROW4", "local"), "6": ("KB_ROW5", "local"),
                "7": ("KB_ROW6", "local"), "8": ("KB_ROW7", "local"),
            })
    s.place("J6", "Conn_01x16", "KB columns (PD0-15)", 450, 140,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("KB_COL0", "local"), "2": ("KB_COL1", "local"), "3": ("KB_COL2", "local"),
                "4": ("KB_COL3", "local"), "5": ("KB_COL4", "local"), "6": ("KB_COL5", "local"),
                "7": ("KB_COL6", "local"), "8": ("KB_COL7", "local"), "9": ("KB_COL8", "local"),
                "10": ("KB_COL9", "local"), "11": ("KB_COL10", "local"), "12": ("KB_COL11", "local"),
                "13": ("KB_COL12", "local"), "14": ("KB_COL13", "local"), "15": ("KB_COL14", "local"),
                "16": ("KB_COL15", "local"),
            })

    # ---------------- GPIO expansion header ----------------
    s.text(450, 260, "== EC_GPIO expansion header (16 spare GPIO) ==")
    s.place("J7", "Conn_01x16", "EC_GPIO0-15 expansion", 450, 300,
            footprint=FOOTPRINTS["Conn_01x16"],
            pin_nets={
                "1": ("EC_GPIO0", "local"), "2": ("EC_GPIO1", "local"), "3": ("EC_GPIO2", "local"),
                "4": ("EC_GPIO3", "local"), "5": ("EC_GPIO4", "local"), "6": ("EC_GPIO5", "local"),
                "7": ("EC_GPIO6", "local"), "8": ("EC_GPIO7", "local"), "9": ("EC_GPIO8", "local"),
                "10": ("EC_GPIO9", "local"), "11": ("EC_GPIO10", "local"), "12": ("EC_GPIO11", "local"),
                "13": ("EC_GPIO12", "local"), "14": ("EC_GPIO13", "local"), "15": ("EC_GPIO14", "local"),
                "16": ("EC_GPIO15", "local"),
            })

    # ---------------- U5: TPS54202DDC VSYS -> 3.3V buck ----------------
    s.text(650, 20, "== U5 TPS54202DDC VSYS -> MCU_3V3 Buck (3.3V, 2A) ==")
    s.place("U5", "TPS54202DDC", "TPS54202DDC", 700, 100,
            footprint=FOOTPRINTS["U_SOT23_6"],
            pin_nets={
                "1": ("GND", "local"), "2": ("BUCK_SW", "local"), "3": ("VSYS", "hier"),
                "4": ("BUCK_FB", "local"), "5": ("BUCK_EN", "local"), "6": ("BUCK_BOOT", "local"),
            })
    c4 = Cur(650, 40)
    s.place("C36", "C", "10u (VIN bulk)", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("C37", "C", "100n (VIN bypass)", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("R34", "R", "100k (EN pull-up, always-on)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("BUCK_EN", "local")})
    s.place("C38", "C", "100n (BOOT cap)", *c4.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BUCK_BOOT", "local"), "2": ("BUCK_SW", "local")})
    s.place("L3", "L", "3.3uH (typ, verify per fsw)", *c4.next(), footprint=FOOTPRINTS["L_buck"],
            pin_nets={"1": ("BUCK_SW", "local"), "2": ("MCU_3V3", "hier")})
    s.place("R35", "R", "31.6k (FB divider hi)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("BUCK_FB", "local")})
    s.place("R36", "R", "10k (FB divider lo)", *c4.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK_FB", "local"), "2": ("GND", "local")})
    s.place("C39", "C", "22u (TBD - verify output ripple)", *c4.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})

    s.gnd(650, 200)

    s.text(20, 340, "NOTE: no wires used - connectivity is via matching label names (valid KiCad practice).")
    s.text(20, 346, "EC_GPIOx numbering is a local convenience mapping - see U4 pin_nets for actual STM32 pin/net cross-ref.")
    s.text(20, 352, "Anti-ghosting diodes for the keyboard matrix live on the keyboard membrane PCB, not this board.")
    s.text(20, 358, "MCU_USB_DP/DM (PA12/PA11, OTG_FS device mode) intentionally distinct from Power sheet's USB_DP1/DM1 (PD sink port).")

    return s


def main():
    from build_ducktop2 import Sheet as _S  # noqa: F401
    import generate_power_sheet as ps

    power_sheet_uuid = U()
    ec_sheet_uuid = U()

    power_s = ps.build(power_sheet_uuid)
    power_text = power_s.render(U(), page_number="2")
    power_path = os.path.join(PROJDIR, "01_power_battery.kicad_sch")
    with open(power_path, "w", encoding="utf-8") as f:
        f.write(power_text)
    print("wrote", power_path, len(power_text), "bytes")

    ec_s = build(ec_sheet_uuid)
    ec_text = ec_s.render(U(), page_number="3")
    ec_path = os.path.join(PROJDIR, "02_ec_mcu.kicad_sch")
    with open(ec_path, "w", encoding="utf-8") as f:
        f.write(ec_text)
    print("wrote", ec_path, len(ec_text), "bytes")

    # ---- Root sheet (both sheets + cross-sheet wiring for shared nets) ----
    power_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "VBUS_PD1", "VBUS_PD2", "VBUS_PD3", "USB_DP1", "USB_DM1",
    ]
    ec_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON", "CHG_CE_N",
        "VSYS", "MCU_USB_DP", "MCU_USB_DM", "MCU_3V3",
    ]
    shared_nets = [n for n in ec_hier_nets if n in power_hier_nets]

    def sheet_block(uuid_, x, y, w, h, name, filename, pins):
        pins_sexpr = []
        pin_coords = {}
        for i, name_ in enumerate(pins):
            py = y + 5 + i * 6
            pin_coords[name_] = (x + w, py)
            pins_sexpr.append(
                f'  (pin "{name_}" bidirectional\n'
                f'    (at {x + w} {py} 0)\n'
                f'    (effects (font (size 1.27 1.27)) (justify left))\n'
                f'    (uuid {U()})\n'
                f'  )'
            )
        block = (
            f'(sheet\n'
            f'  (at {x} {y})\n'
            f'  (size {w} {h})\n'
            f'  (stroke (width 0.1524) (type solid))\n'
            f'  (fill (color 0 0 0 0.0))\n'
            f'  (uuid {uuid_})\n'
            f'  (property "Sheetname" "{name}"\n'
            f'    (at {x} {y - 1} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'  )\n'
            f'  (property "Sheetfile" "{filename}"\n'
            f'    (at {x} {y + h + 1} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left top))\n'
            f'  )\n'
            + "\n".join(pins_sexpr) + "\n"
            f')'
        )
        return block, pin_coords

    power_block, power_pins = sheet_block(
        power_sheet_uuid, 50, 50, 60, 80, "Power & Battery", "01_power_battery.kicad_sch",
        power_hier_nets,
    )
    ec_block, ec_pins = sheet_block(
        ec_sheet_uuid, 180, 50, 60, 70, "EC & MCU", "02_ec_mcu.kicad_sch",
        ec_hier_nets,
    )

    wires = []
    for net in shared_nets:
        x1, y1 = power_pins[net]
        x2, y2 = ec_pins[net]
        wires.append(
            f'(wire\n'
            f'  (pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'  (stroke (width 0) (type default))\n'
            f'  (uuid {U()})\n'
            f')'
        )

    root_text = (
        f'(kicad_sch\n'
        f'  (version 20260306)\n'
        f'  (generator "eeschema")\n'
        f'  (generator_version "10.0")\n'
        f'  (uuid {U()})\n'
        f'  (paper "A3")\n'
        f'  (lib_symbols\n  )\n'
        f'{power_block}\n'
        f'{ec_block}\n'
        + "\n".join(wires) + "\n"
        f'  (sheet_instances\n'
        f'    (path "/"\n'
        f'      (page "1")\n'
        f'    )\n'
        f'  )\n'
        f'  (embedded_fonts no)\n'
        f')\n'
    )
    root_path = os.path.join(PROJDIR, "ducktop2.kicad_sch")
    with open(root_path, "w", encoding="utf-8") as f:
        f.write(root_text)
    print("wrote", root_path, len(root_text), "bytes")


if __name__ == "__main__":
    main()
