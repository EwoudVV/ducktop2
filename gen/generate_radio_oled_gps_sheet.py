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

    s.text(20, 12.7, "== Wi-Fi/Bluetooth and dual OLED peripherals ==")
    s.text(20, 20.32, "M.2 E-key remains on the mainboard; GNSS and amateur-radio hardware moved to the optional radio daughterboard.")
    s.text(20, 27.94, "Both SSD1306 displays remain on the always-on EC service bus and work without the radio daughterboard.")

    # ---------------- J40: M.2 E-key Wi-Fi/Bluetooth module ----------------
    s.text(20, 50.8, "== J40 M.2 E-key Wi-Fi/Bluetooth module ==")
    wifi_perst = "WIFI_PERST_N"
    wifi_refclk_p = "WIFI_REFCLK_E_P"
    wifi_refclk_n = "WIFI_REFCLK_E_N"
    m2e = default_pin_map("Bus_M.2_Socket_E", power_3v3_net="WIFI_3V3")
    m2e.update({
        "3": ("WIFI_USB_DP", "hier"),
        "5": ("WIFI_USB_DN", "hier"),
        "35": ("WIFI_PCIE_TX_P", "hier"),
        "37": ("WIFI_PCIE_TX_N", "hier"),
        "41": ("WIFI_PCIE_RX_P", "hier"),
        "43": ("WIFI_PCIE_RX_N", "hier"),
        "47": (wifi_refclk_p, "local"),
        "49": (wifi_refclk_n, "local"),
        "52": (wifi_perst, "local"),
        "53": ("WIFI_CLKREQ_N", "hier"),
        "54": ("WIFI_W_DISABLE2_N", "local"),
        "55": ("PCIE_WAKE_N", "hier"),
        "56": ("WIFI_W_DISABLE1_N", "local"),
        "58": ("", "nc"),
        "60": ("", "nc"),
    })
    s.place("J40", "Bus_M.2_Socket_E", "Amphenol MDT420E01001 E-key Wi-Fi/Bluetooth socket", 170, 180,
            footprint=FOOTPRINTS["M2_E_key"], pin_nets=m2e,
            extra_props={
                "Manufacturer": "Amphenol", "MPN": "MDT420E01001",
                "QualifiedModuleManufacturer": "Intel",
                "QualifiedModuleMPN": "AX210.NGWGIE.NV",
                "QualifiedModuleContract": "M2_2230_KEY_E_PCIE_WIFI_USB_BLUETOOTH_NOT_CNVIO2",
            })
    s.place("H4", "MountingHole_Pad", "M.2 E-key 2230 M2 grounded standoff 2.5mm", 250, 180,
            footprint=FOOTPRINTS["M2_Card_Standoff_H2.5"],
            pin_nets={"1": ("GND", "local")},
            extra_props={
                "Manufacturer": "Unbranded",
                "MPN": "M2XC4X2.5+C2.7X1.5",
                "Supplier": "Taobao",
                "Supplier_SKU": "4725777108077",
                "Buy_Link": "https://item.taobao.com/item.htm?abbucket=8&id=655855111684&ns=1&skuId=4725777108077&spm=a21n57.1.0.0.5263523chYMn0X",
                "Reference_Design": "LattePanda Mu Lite Carrier V2 f954bf0275fa0aec4c1e9eb168f09644563b28a4",
                "Hardware_Spec": "M2 internal thread; 4mm body; 2.5mm above PCB; 2.7x1.5mm locating tail",
            })

    s.place("F10", "Fuse", "2A E-key 3V3 fuse/polyfuse", 20, 76.2, footprint=FOOTPRINTS["Fuse"],
            pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("WIFI_3V3", "local")},
            extra_props={"Manufacturer": "Littelfuse", "MPN": "1206L200PR"})
    s.place("C170", "C", "47u E-key bulk", 20, 91.44, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("GND", "local")})
    s.place("C171", "C", "100n radio bypass", 20, 104.14, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("GND", "local")})
    s.pwrflag(20, 119.38, "WIFI_3V3")
    s.place("R170", "R", "10k W_DISABLE1 pull-up", 20, 139.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("WIFI_W_DISABLE1_N", "local")})
    s.place("R171", "R", "10k W_DISABLE2 pull-up", 20, 152.4, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("WIFI_W_DISABLE2_N", "local")})
    wifi_isolation = {
        "Manufacturer": "Texas Instruments", "MPN": "SN74LVC3G34DCUR",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc3g34.pdf",
        "PowerOffContract": "IOFF_OUTPUTS_HIGH_Z_WHEN_WIFI_3V3_IS_0V",
    }
    s.place("U170", "74LVC3G34", "SN74LVC3G34DCUR E-key control isolation", 95, 139.7,
            unit=1, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
            pin_nets={"1": ("WIFI_W_DISABLE1_N_EC", "hier"),
                      "7": ("WIFI_W_DISABLE1_N", "local")}, extra_props=wifi_isolation)
    s.place("U170", "74LVC3G34", "SN74LVC3G34DCUR E-key control isolation", 125, 139.7,
            unit=2, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
            pin_nets={"6": ("WIFI_W_DISABLE2_N_EC", "hier"),
                      "2": ("WIFI_W_DISABLE2_N", "local")}, extra_props=wifi_isolation)
    s.place("U170", "74LVC3G34", "SN74LVC3G34DCUR E-key control isolation", 155, 139.7,
            unit=3, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
            pin_nets={"3": ("GND", "local"), "5": ("", "nc")}, extra_props=wifi_isolation)
    s.place("U170", "74LVC3G34", "SN74LVC3G34DCUR E-key control isolation", 185, 139.7,
            unit=4, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
            pin_nets={"4": ("GND", "local"), "8": ("WIFI_3V3", "local")},
            extra_props=wifi_isolation)
    s.place("C187", "C", "100n E-key control-isolator local", 215, 139.7,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("WIFI_3V3", "local"), "2": ("GND", "local")})
    s.place("R198", "R", "100k WLAN disable default asserted", 95, 152.4,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_W_DISABLE1_N_EC", "hier"), "2": ("GND", "local")})
    s.place("R199", "R", "100k Bluetooth disable default asserted", 125, 152.4,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_W_DISABLE2_N_EC", "hier"), "2": ("GND", "local")})
    s.place("R176", "R", "0R / PERST isolation", 20, 170.18, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PLTRST_SRC_N", "hier"), "2": (wifi_perst, "local")})
    s.place("R177", "R", "0R / REFCLK+ isolation", 20, 182.88, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_REFCLK_P", "hier"), "2": (wifi_refclk_p, "local")})
    s.place("R178", "R", "0R / REFCLK- isolation", 20, 195.58, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("WIFI_REFCLK_N", "hier"), "2": (wifi_refclk_n, "local")})

    # ---------------- J41/J45: SSD1306 I2C OLED/status displays ----------------
    s.text(20, 260.35, "== Dual SSD1306 I2C OLED/status display headers ==")
    s.place("U45", "TCA9548APWR", "TCA9548A service I2C mux @0x70", 90, 300,
            footprint=FOOTPRINTS["TCA9548APWR"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("GND", "local"),
                "3": ("SERVICE_MUX_RESET_N", "hier"),
                "4": ("OLED_A_SDA", "local"),
                "5": ("OLED_A_SCL", "local"),
                "6": ("OLED_B_SDA", "local"),
                "7": ("OLED_B_SCL", "local"),
                "8": ("PD1_I2C_SDA", "hier"),
                "9": ("PD1_I2C_SCL", "hier"),
                "10": ("PD2_I2C_SDA", "hier"),
                "11": ("PD2_I2C_SCL", "hier"),
                "12": ("GND", "local"),
                "13": ("", "nc"),
                "14": ("", "nc"),
                "15": ("", "nc"),
                "16": ("", "nc"),
                "17": ("", "nc"),
                "18": ("", "nc"),
                "19": ("", "nc"),
                "20": ("", "nc"),
                "21": ("GND", "local"),
                "22": ("I2C_SCL", "hier"),
                "23": ("I2C_SDA", "hier"),
                "24": ("MCU_3V3", "hier"),
            },
            extra_props={"Manufacturer": "Texas Instruments", "MPN": "TCA9548APWR"})
    s.place("R173", "R", "4.7k OLED A SCL pull-up", 20, 299.72, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("OLED_A_SCL", "local")})
    s.place("R179", "R", "4.7k OLED A SDA pull-up", 20, 312.42, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("OLED_A_SDA", "local")})
    s.place("C174", "C", "1u OLED A local", 90, 325.12, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C175", "C", "100n OLED A local", 90, 337.82, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("J41", "Conn_01x04", "SSD1306 OLED A 4-pin GND/VDD/SCK/SDA", 205, 287.02,
            footprint=FOOTPRINTS["SSD1306_0.96in_Module"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MCU_3V3", "hier"),
                "3": ("OLED_A_SCL", "local"),
                "4": ("OLED_A_SDA", "local"),
            }, extra_props={
                "ProcurementClass": "Owner-supplied measured module",
                "AssemblyID": "OLED-A-SSD1306-0P96-4PIN-GND-VDD-SCK-SDA",
                "MechanicalEnvelope": "27.0x27.0mm module; verify owned sample before enclosure release",
            })
    s.place("R196", "R", "4.7k OLED B SCL pull-up", 205, 312.42, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("OLED_B_SCL", "local")})
    s.place("R197", "R", "4.7k OLED B SDA pull-up", 205, 325.12, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("OLED_B_SDA", "local")})
    s.place("C178", "C", "1u OLED B local", 205, 350.52, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C179", "C", "100n OLED B local", 205, 363.22, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("C185", "C", "100n OLED mux local", 90, 350.52, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("J45", "Conn_01x04", "SSD1306 OLED B 4-pin GND/VDD/SCK/SDA", 205, 375.92,
            footprint=FOOTPRINTS["SSD1306_0.96in_Module"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("MCU_3V3", "hier"),
                "3": ("OLED_B_SCL", "local"),
                "4": ("OLED_B_SDA", "local"),
            }, extra_props={
                "ProcurementClass": "Owner-supplied measured module",
                "AssemblyID": "OLED-B-SSD1306-0P96-4PIN-GND-VDD-SCK-SDA",
                "MechanicalEnvelope": "27.0x27.0mm module; verify owned sample before enclosure release",
            })

    s.gnd(520, 300)
    s.text(20, 350.52, "NOTES:")
    s.text(20, 358.14, "M.2 E-key directions are host TX->PET35/37 and PER41/43->host RX; Mu-side TX has 220n AC coupling.")
    s.text(20, 365.76, "USB2_P1 carries Bluetooth; default-BIOS HSIO3/REFCLK3/CLKREQ3 carry the E-key PCIe function.")
    s.text(20, 373.38, "Qualified radio is Intel AX210.NGWGIE.NV M.2 2230 Key-E: Wi-Fi over PCIe and Bluetooth over USB; AX211/CNVio2 is prohibited.")
    s.text(20, 381, "OLED headers match common 4-pin SSD1306 modules: GND, VDD/3V3, SCK/SCL, SDA. Use 3.3V modules only.")
    s.text(20, 388.62, "GNSS, amateur-radio modules, RF switching, and the dedicated radio codec are isolated on the removable daughterboard.")
    s.text(20, 396.24, "TCA9548A channels 0/1 isolate the identical 0x3C OLEDs; channels 2/3 isolate the two TPS25751A service buses.")
    s.text(20, 403.86, "Hardware-gated SERVICE_MUX_RESET_N asserts during every EC reset; firmware selects one TPS25751A channel and validates PD Status 0x35 plus PDO/RDO 0x31/0x32.")
    s.text(20, 411.48, "The mainboard OLED and Wi-Fi functions do not depend on radio-daughterboard presence or power.")
    s.text(20, 419.1, "U170 isolates powered-off E-key controls; R198/R199 keep WLAN and Bluetooth disabled until EC firmware explicitly enables them.")
    s.text(20, 426.72, "Channels 4-7 remain unused and explicitly no-connected for future service expansion.")
    s.text(20, 434.34, "SUSCLK, SDIO, PCM/I2S, UIM, and vendor-defined E-key pins remain NC for the AX210-class module target.")
    s.text(20, 441.96, "The optional-board interface provides independent safe defaults for every radio/GNSS signal.")

    return s
