import os

import genlib
from build_ducktop2 import (
    Sheet, U, PROJDIR, FOOTPRINTS, fmt_coord, snap_coord,
    reset_uuid_sequence, stable_uuid, uuid_scope,
)


def symbol_pins(name):
    _lib, text = genlib.load_renamed_symbol(name)
    return genlib.parse_pins(text)


def default_pin_map(symname, power_3v3_net="SYS_3V3"):
    nets = {}
    for num, pin in symbol_pins(symname).items():
        name = pin["name"]
        if name == "GND" or num == "MP":
            nets[num] = ("GND", "local")
        elif name in ("3.3V", "+3.3V"):
            nets[num] = (power_3v3_net, "local")
        elif name == "NC":
            nets[num] = ("", "nc")
        else:
            nets[num] = ("", "nc")
    return nets


def build(sheet_symbol_uuid, pwr_start=400, flg_start=400):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = pwr_start
    s.refcounters["#FLG"] = flg_start

    class Cur:
        def __init__(self, x0, y0, col_w=55, row_h=10, rows_per_col=20):
            self.x0, self.y0, self.col_w, self.row_h, self.rows = x0, y0, col_w, row_h, rows_per_col
            self.i = 0

        def next(self):
            col, row = divmod(self.i, self.rows)
            self.i += 1
            return (self.x0 + col * self.col_w, self.y0 + row * self.row_h)

    # ---------------- A1: LattePanda Mu module ----------------
    s.text(20, 20, "== A1 LattePanda Mu carrier core ==")
    mu_nets = default_pin_map("LattePanda_Mu")

    # The Mu and its onboard eDP backlight input use a regulated 12 V rail.
    # Raw 3S VSYS spans too much voltage to guarantee the module's 15 W mode.
    for pin in [str(n) for n in range(250, 261)]:
        mu_nets[pin] = ("MU_12V", "local")
    mu_nets["115"] = ("RTC_BAT", "local")

    # Local buttons and debug.
    mu_nets["1"] = ("MU_PWRBTN_N", "hier")
    mu_nets["3"] = ("MU_RSTBTN_N", "hier")
    mu_nets["5"] = ("MU_S0_HIGH", "hier")
    mu_nets["10"] = ("MU_SIO_UART_TX", "local")
    mu_nets["12"] = ("MU_SIO_UART_RX", "local")

    # Default BIOS exposes HSIO0 and HSIO1 as two independent USB 3.2 Gen 2
    # host lanes. Pair them with USB2_P2 and USB2_P4 for the two external
    # Type-C downstream ports. Mu host TX requires 100 nF series coupling.
    mu_nets.update({
        "13": ("USBC1_SSTX_RAW_P", "local"),
        "15": ("USBC1_SSTX_RAW_N", "local"),
        "16": ("USBC1_SSRX_P", "hier"),
        "18": ("USBC1_SSRX_N", "hier"),
        "73": ("USBC1_DM", "hier"),
        "75": ("USBC1_DP", "hier"),
        "19": ("USBC2_SSTX_RAW_P", "local"),
        "21": ("USBC2_SSTX_RAW_N", "local"),
        "22": ("USBC2_SSRX_P", "hier"),
        "24": ("USBC2_SSRX_N", "hier"),
        "70": ("USBC2_DP", "hier"),
        "72": ("USBC2_DM", "hier"),
        "129": ("MU_USB_OC_N", "hier"),
    })

    # Default-BIOS HSIO3 + USB2_P1 feed the M.2 E-key Wi-Fi/Bluetooth module.
    mu_nets.update({
        "31": ("WIFI_PCIE_TX_RAW_P", "local"),
        "33": ("WIFI_PCIE_TX_RAW_N", "local"),
        "34": ("WIFI_PCIE_RX_P", "hier"),
        "36": ("WIFI_PCIE_RX_N", "hier"),
        "67": ("WIFI_USB_DN", "hier"),
        "69": ("WIFI_USB_DP", "hier"),
        "88": ("WIFI_REFCLK_P", "hier"),
        "90": ("WIFI_REFCLK_N", "hier"),
        "100": ("WIFI_CLKREQ_N", "hier"),
    })

    # Spare native USB2 ports become internal laptop service links.
    # USB2_P3 hosts the EC USB device; USB2_P4 is paired with native USB-C port 2.
    # USB2_P5 hosts the internal two-port system-audio hub; USB2_P7 hosts the maker MCU sandbox.
    # USB2_P8 hosts the internal trackpad so the OS sees a normal USB HID pointing device.
    mu_nets.update({
        "79": ("EC_HOST_USB_DM", "hier"),
        "81": ("EC_HOST_USB_DP", "hier"),
        "109": ("AUDIO_USB_DM", "hier"),
        "111": ("AUDIO_USB_DP", "hier"),
        "76": ("MAKER_USB_DP", "hier"),
        "78": ("MAKER_USB_DM", "hier"),
        "82": ("TRACKPAD_USB_DP", "hier"),
        "84": ("TRACKPAD_USB_DM", "hier"),
    })

    # The panel connects to the Mu module's onboard eDP connector; no display
    # lanes leave the SODIMM edge connector. DDIB therefore remains unused.

    # Default BIOS aggregates HSIO8..11 into one PCIe Gen3 x4 link. REFCLK2 is
    # the documented default clock for HSIO8. Host TX requires 220 nF coupling.
    mu_nets.update({
        "37": ("PCIE_M_L0_TX_RAW_P", "local"),
        "39": ("PCIE_M_L0_TX_RAW_N", "local"),
        "40": ("PCIE_M_L0_RX_P", "local"),
        "42": ("PCIE_M_L0_RX_N", "local"),
        "43": ("PCIE_M_L1_TX_RAW_P", "local"),
        "45": ("PCIE_M_L1_TX_RAW_N", "local"),
        "46": ("PCIE_M_L1_RX_P", "local"),
        "48": ("PCIE_M_L1_RX_N", "local"),
        "49": ("PCIE_M_L2_TX_RAW_P", "local"),
        "51": ("PCIE_M_L2_TX_RAW_N", "local"),
        "52": ("PCIE_M_L2_RX_P", "local"),
        "54": ("PCIE_M_L2_RX_N", "local"),
        "55": ("PCIE_M_L3_TX_RAW_P", "local"),
        "57": ("PCIE_M_L3_TX_RAW_N", "local"),
        "58": ("PCIE_M_L3_RX_P", "local"),
        "60": ("PCIE_M_L3_RX_N", "local"),
        "97": ("PCIE_M_REFCLK_SRC_P", "local"),
        "99": ("PCIE_M_REFCLK_SRC_N", "local"),
        "103": ("PCIE_WAKE_N", "hier"),
        "105": ("PLTRST_SRC_N", "hier"),
    })

    # Default BIOS exposes HSIO6 as PCIe Gen3 x1. It feeds the onboard
    # RTL8111H Gigabit Ethernet controller on sheet 16 using REFCLK4/CLKREQ4.
    mu_nets.update({
        "61": ("GBE_HOST_TX_P", "hier"),
        "63": ("GBE_HOST_TX_N", "hier"),
        "64": ("GBE_HOST_RX_P", "hier"),
        "66": ("GBE_HOST_RX_N", "hier"),
        "94": ("GBE_REFCLK_P", "hier"),
        "96": ("GBE_REFCLK_N", "hier"),
        "102": ("GBE_CLKREQ_N", "hier"),
    })

    # TCP0 is the second default-BIOS HDMI 2.0 output; it leaves to sheet 6 for the external HDMI-A jack.
    mu_nets.update({
        "177": ("TCP0_DDC_SDA", "hier"),
        "179": ("TCP0_DDC_SCL", "hier"),
        "187": ("TCP0_HPD", "hier"),
        "227": ("TCP0_TXRX1_N", "hier"),
        "229": ("TCP0_TXRX1_P", "hier"),
        "233": ("TCP0_TX1_N", "hier"),
        "235": ("TCP0_TX1_P", "hier"),
        "239": ("TCP0_TXRX0_N", "hier"),
        "241": ("TCP0_TXRX0_P", "hier"),
        "245": ("TCP0_TX0_N", "hier"),
        "247": ("TCP0_TX0_P", "hier"),
    })

    s.place("A1", "LattePanda_Mu", "TE 2309411-1 LattePanda Mu host socket/interface", 160, 180,
            footprint=FOOTPRINTS["LattePanda_Mu"], pin_nets=mu_nets,
            extra_props={
                "Manufacturer": "TE Connectivity", "MPN": "2309411-1",
                "SocketHeight": "8.0mm standard orientation",
                "ModuleAssemblyItem": "A2 DFRobot DFR1149",
                "BIOSProfile": "DFLT S70NC1R200-16G-B.bin; SHA256 6edcfe021d84baf2b6ea3e4f4df4e81442a6be3580905f255221644d0eeb0bed",
            })
    s.place("A2", "MountingHole", "DFR1149 LattePanda Mu N305 16GB/64GB removable module", 270, 180,
            footprint="", pin_nets={}, on_board=False, in_bom=True,
            extra_props={
                "Manufacturer": "DFRobot", "MPN": "DFR1149",
                "AssemblyType": "Customer-fitted removable compute module",
                "RequiredSocket": "A1 TE Connectivity 2309411-1",
                "BIOSProfile": "DFLT S70NC1R200-16G-B.bin; build 2026-06-03; SHA256 6edcfe021d84baf2b6ea3e4f4df4e81442a6be3580905f255221644d0eeb0bed",
            })
    standoff_props = {
        "Manufacturer": "Wurth Elektronik",
        "MPN": "9774055243R",
        "Hardware_Spec": "WA-SMSI M2 internal thread; 4.35mm OD; 5.5+/-0.1mm above PCB; 3.0mm NPTH; 5.3mm solder land",
        "MatingScrew": "RS PRO 914-1462; M2x4mm DIN 7985 A2 stainless; confirm sample engagement",
        "TorqueLimit": "0.2 N*m maximum per Wurth; production torque TBD after sample fit",
    }
    s.place("H1", "MountingHole_Pad", "Wurth 9774055243R Mu M2 standoff 5.5mm A", 225, 170,
            footprint=FOOTPRINTS["Mu_M2_Standoff_H5.5"],
            pin_nets={"1": ("GND", "local")}, extra_props=standoff_props)
    s.place("H2", "MountingHole_Pad", "Wurth 9774055243R Mu M2 standoff 5.5mm B", 225, 190,
            footprint=FOOTPRINTS["Mu_M2_Standoff_H5.5"],
            pin_nets={"1": ("GND", "local")}, extra_props=standoff_props)

    s.place("SW2", "SW_Push", "Mu Power", 30, 50, footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MU_PWRBTN_N", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Omron", "MPN": "B3S-1000"})
    s.place("SW3", "SW_Push", "Mu Reset", 30, 70, footprint=FOOTPRINTS["SW_Push"],
            pin_nets={"1": ("MU_RSTBTN_N", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Omron", "MPN": "B3S-1000"})
    s.place("J8", "Conn_01x04", "DNP Mu SIO UART debug (IO voltage unverified)", 30, 100,
            footprint=FOOTPRINTS["Conn_01x04_Header"],
            pin_nets={"1": ("GND", "local"), "2": ("MU_SIO_UART_TX", "local"),
                      "3": ("MU_SIO_UART_RX", "local"), "4": ("GND", "local")},
            on_board=False)
    s.place("J9", "Conn_01x02", "RTC backup coin-cell header", 30, 130,
            footprint=FOOTPRINTS["Conn_01x02_Service_GH"],
            pin_nets={"1": ("RTC_BAT", "local"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "JST", "MPN": "SM02B-GHS-TB",
                "MatingHousing": "GHR-02V-S", "Contacts": "SSHL-002T-P0.2",
            })
    s.gnd(30, 160)
    s.pwrflag(30, 180, "RTC_BAT")

    # ---------------- U6/U7: local buck rails ----------------
    s.text(300, 20, "== Local carrier rails from VSYS ==")
    p = Cur(300, 45)
    s.place("U6", "TPS56637", "TPS56637RPAR VSYS -> SYS_5V (5.10V, 6A class)",
            *p.next(), footprint=FOOTPRINTS["TPS56637"],
            pin_nets={
                "1": ("BUCK5_EN", "local"), "2": ("BUCK5_FB", "local"),
                "3": ("GND", "local"), "4": ("SYS_5V_PG", "local"),
                "5": ("", "nc"), "6": ("BUCK5_SW", "local"),
                "7": ("BUCK5_BOOT", "local"), "8": ("VSYS", "hier"),
                "9": ("GND", "local"), "10": ("GND", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS56637RPAR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps56637.pdf",
            })
    for ref in ("C40", "C41"):
        s.place(ref, "C", "10u 50V X7R TPS56637 VIN", *p.next(),
                footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "TDK", "MPN": "CGA5L1X7R1H106K160AC"})
    s.place("C42", "C", "100n 50V X7R TPS56637 VIN HF", *p.next(),
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("C43", "C", "100n 16V X7R TPS56637 BOOT", *p.next(),
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BUCK5_BOOT", "local"), "2": ("BUCK5_SW", "local")})
    s.place("L4", "L", "XAL7070-332MEC 3.3uH 19.4A Isat30%", *p.next(),
            footprint=FOOTPRINTS["L_XAL7070"],
            pin_nets={"1": ("BUCK5_SW", "local"), "2": ("SYS_5V", "hier")},
            extra_props={
                "Manufacturer": "Coilcraft", "MPN": "XAL7070-332MEC",
                "Datasheet": "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal7070/",
            })
    s.place("R40", "R", "76.8k 0.1% TPS56637 FB high", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_5V", "local"), "2": ("BUCK5_FB", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0776K8L"})
    s.place("R41", "R", "10k 0.1% TPS56637 FB low", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK5_FB", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RT0603BRD0710KL"})
    s.place("R42", "R", "169k 1% TPS56637 EN high", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("BUCK5_EN", "local")})
    s.place("R45", "R", "36.1k 1% TPS56637 EN low", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK5_EN", "local"), "2": ("GND", "local")})
    s.place("R46", "R", "100k SYS_5V PG pull-up", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("SYS_5V_PG", "local")})
    for ref in ("C44", "C45"):
        s.place(ref, "C", "22u 16V X7R TPS56637 OUT", *p.next(),
                footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("SYS_5V", "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CZ71C226ME15L"})

    s.place("U7", "TPS56637", "TPS56637RPAR VSYS -> SYS_3V3 (3.32V, 6A class)", *p.next(),
            footprint=FOOTPRINTS["TPS56637"],
            pin_nets={
                "1": ("BUCK33_EN", "local"), "2": ("BUCK33_FB", "local"),
                "3": ("GND", "local"), "4": ("SYS_3V3_PG", "local"),
                "5": ("", "nc"), "6": ("BUCK33_SW", "local"),
                "7": ("BUCK33_BOOT", "local"), "8": ("VSYS", "hier"),
                "9": ("GND", "local"), "10": ("GND", "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS56637RPAR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps56637.pdf",
            })
    s.place("C46", "C", "10u 50V X7R TPS56637 VIN", *p.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "TDK", "MPN": "CGA5L1X7R1H106K160AC"})
    s.place("C790", "C", "10u 50V X7R TPS56637 VIN", *p.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "TDK", "MPN": "CGA5L1X7R1H106K160AC"})
    s.place("C791", "C", "100n 50V X7R TPS56637 VIN HF", *p.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")})
    s.place("C47", "C", "100n 16V X7R TPS56637 BOOT", *p.next(), footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("BUCK33_BOOT", "local"), "2": ("BUCK33_SW", "local")})
    s.place("L5", "L", "XAL7070-222MEC 2.2uH 19.6A Isat30%", *p.next(),
            footprint=FOOTPRINTS["L_XAL7070"],
            pin_nets={"1": ("BUCK33_SW", "local"), "2": ("SYS_3V3", "hier")},
            extra_props={
                "Manufacturer": "Coilcraft", "MPN": "XAL7070-222MEC",
                "Datasheet": "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xal/xal7070/",
            })
    s.place("R43", "R", "45.3k 1% TPS56637 FB high", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_3V3", "local"), "2": ("BUCK33_FB", "local")})
    s.place("R44", "R", "10k 1% TPS56637 FB low", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK33_FB", "local"), "2": ("GND", "local")})
    s.place("R770", "R", "169k 1% TPS56637 EN high", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("BUCK33_EN", "local")})
    s.place("R771", "R", "36.1k 1% TPS56637 EN low", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("BUCK33_EN", "local"), "2": ("GND", "local")})
    s.place("R772", "R", "100k SYS_3V3 PG pull-up", *p.next(), footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("SYS_3V3_PG", "local")})
    s.place("C48", "C", "22u 16V X7R TPS56637 OUT", *p.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_3V3", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM31CZ71C226ME15L"})
    s.place("C792", "C", "22u 16V X7R TPS56637 OUT", *p.next(), footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_3V3", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM31CZ71C226ME15L"})

    # Native USB 3.2 host TX pairs need 100 nF coupling on the carrier.
    # Place these close to the Type-C port signal path; Mu RX stays direct.
    q = Cur(520, 45)
    for ref, raw, coupled in [
        ("C66", "USBC1_SSTX_RAW_P", "USBC1_SSTX_P"),
        ("C67", "USBC1_SSTX_RAW_N", "USBC1_SSTX_N"),
        ("C586", "USBC2_SSTX_RAW_P", "USBC2_SSTX_P"),
        ("C587", "USBC2_SSTX_RAW_N", "USBC2_SSTX_N"),
    ]:
        s.place(ref, "C", "100n 10V X7R Mu USB3 TX AC", *q.next(),
                footprint=FOOTPRINTS["C_0402"],
                pin_nets={"1": (raw, "local"), "2": (coupled, "hier")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A104KA01D"})
    s.pwrflag(640, 150, "SYS_5V")
    s.pwrflag(640, 165, "SYS_3V3")

    # ---------------- U750: regulated Mu / eDP 12 V rail ----------------
    # This is based on TI's TPS552892EVM-111 12 V reference design. The
    # 15 mOhm output shunt sets a 3.33 A nominal current limit (50 mV threshold).
    # A 9.0 V nominal rising UVLO is the final analog backstop. The separate
    # two-NMOS interlock keeps this stage disabled until the EC explicitly
    # qualifies the source and asserts active-high MU_12V_ENABLE.
    s.text(520, 200, "== U750 TPS552892 VSYS -> regulated MU_12V, 12 V / 3.3 A limit ==")
    s.place(
        "U750", "TPS552892", "TPS552892RYQR 12V buck-boost", 620, 250,
        footprint=FOOTPRINTS["TPS552892"],
        pin_nets={
            "1": ("MU12_EN_UVLO", "local"),
            "2": ("MU12_MODE", "local"),
            "3": ("MU_12V_PG", "hier"),
            "4": ("MU12_CC_N", "local"),
            "5": ("MU12_DITH", "local"),
            "6": ("MU12_FSW", "local"),
            "7": ("VSYS", "hier"),
            "8": ("MU12_SW1", "local"),
            "9": ("GND", "local"),
            "10": ("MU12_SW2", "local"),
            "11": ("MU12_PRE_SENSE", "local"),
            "12": ("MU12_ISP", "local"),
            "13": ("MU12_ISN", "local"),
            "14": ("MU12_FB", "local"),
            "15": ("MU12_COMP", "local"),
            "16": ("", "nc"),
            "17": ("GND", "local"),
            "18": ("MU12_VCC", "local"),
            "19": ("MU12_BOOT2", "local"),
            "20": ("MU12_BOOT1", "local"),
            "21": ("MU12_EXTVCC", "local"),
        },
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "TPS552892RYQR"},
    )
    s.place("L750", "L", "4.7uH 10.1A Isat / 6.9A Irms", 520, 220,
            footprint=FOOTPRINTS["L_MU12"],
            pin_nets={"1": ("MU12_SW1", "local"), "2": ("MU12_SW2", "local")},
            extra_props={"Manufacturer": "Coilcraft", "MPN": "XAL7030-472MEC"})
    s.place("RS750", "R", "15mOhm 1% 1W; 3.33A output current limit", 520, 230,
            footprint=FOOTPRINTS["R_1206"],
            pin_nets={"1": ("MU12_PRE_SENSE", "local"), "2": ("MU_12V", "hier")},
            extra_props={"Manufacturer": "Panasonic", "MPN": "ERJ8BWFR015V"})

    # Input and output reservoirs use the exact voltage classes from TI's EVM.
    # This preserves DC-bias margin and avoids relying on the surge clamp to make
    # 25 V MLCCs acceptable on the nominally <=22 V VSYS rail.
    for ref, value, footprint, mpn in [
        ("C750", "68u 50V hybrid input bulk", FOOTPRINTS["C_68u_50V_hybrid"], "EEHZA1H680P"),
        ("C751", "10u 50V X7R input", FOOTPRINTS["C_10u"], "CGA5L1X7R1H106K160AC"),
        ("C752", "10u 50V X7R input", FOOTPRINTS["C_10u"], "CGA5L1X7R1H106K160AC"),
        ("C753", "1u 50V X5R input", FOOTPRINTS["C_100n"], "GRT188R61H105ME13D"),
        ("C754", "100n 50V X7R input HF", FOOTPRINTS["C_0402"], "GRM155R71H104ME14D"),
        ("C755", "100n 50V X7R input HF", FOOTPRINTS["C_0402"], "GRM155R71H104ME14D"),
    ]:
        s.place(ref, "C_Polarized" if ref == "C750" else "C", value,
                520, 240 + (int(ref[1:]) - 750) * 10,
                footprint=footprint,
                pin_nets={"1": ("VSYS", "hier"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Panasonic" if ref == "C750" else
                             ("TDK" if ref in ("C751", "C752") else "Murata"),
                             "MPN": mpn})

    # Output reservoir remains before the Kelvin shunt, matching the TI EVM.
    for ref, value, footprint, mpn in [
        ("C756", "100n 50V X7R output HF", FOOTPRINTS["C_0402"], "GRM155R71H104ME14D"),
        ("C757", "100n 50V X7R output HF", FOOTPRINTS["C_0402"], "GRM155R71H104ME14D"),
        ("C758", "1u 50V X5R output", FOOTPRINTS["C_100n"], "GRT188R61H105ME13D"),
        ("C759", "10u 50V X7R output", FOOTPRINTS["C_10u"], "CGA5L1X7R1H106K160AC"),
        ("C760", "10u 50V X7R output", FOOTPRINTS["C_10u"], "CGA5L1X7R1H106K160AC"),
        ("C761", "10u 50V X7R output", FOOTPRINTS["C_10u"], "CGA5L1X7R1H106K160AC"),
        ("C762", "100u 35V hybrid output bulk", FOOTPRINTS["C_100u_35V_hybrid"], "EEHZK1V101XP"),
    ]:
        s.place(ref, "C_Polarized" if ref == "C762" else "C", value,
                575, 310 + (int(ref[1:]) - 756) * 10,
                footprint=footprint,
                pin_nets={"1": ("MU12_PRE_SENSE", "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Panasonic" if ref == "C762" else
                             ("TDK" if ref in ("C759", "C760", "C761") else "Murata"),
                             "MPN": mpn})
    s.place("C763", "C", "1u 50V post-sense load-side bypass", 575, 380,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU_12V", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRT188R61H105ME13D"})

    # Gate-drive, mode, clock, UVLO, current-sense, and loop networks.
    s.place("C764", "C", "22u 16V X7R VCC mandatory; effective >4.7u", 685, 220,
            footprint=FOOTPRINTS["C_1206"],
            pin_nets={"1": ("MU12_VCC", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM31CZ71C226ME15L"})
    for ref, boot, sw in (("C765", "MU12_BOOT1", "MU12_SW1"),
                          ("C766", "MU12_BOOT2", "MU12_SW2")):
        s.place(ref, "C", "100n 50V X8L bootstrap", 685,
                230 if ref == "C765" else 240, footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (boot, "local"), "2": (sw, "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GCM188L81H104KA57D"})

    # TI fits these footprints on the EVM but leaves them unpopulated. They make
    # switch-node ringing tunable after first-board probing without a PCB respin.
    for resistor, capacitor, sw, node, y in [
        ("R764", "C768", "MU12_SW1", "MU12_SNUB1", 220),
        ("R765", "C769", "MU12_SW2", "MU12_SNUB2", 230),
    ]:
        s.place(resistor, "R", "DNP 2.2R 0.25W switch-node snubber", 850, y,
                footprint=FOOTPRINTS["R_1206"], dnp=True,
                pin_nets={"1": (sw, "local"), "2": (node, "local")},
                extra_props={"Manufacturer": "Panasonic", "MPN": "ERJ-8RQF2R2V"})
        s.place(capacitor, "C", "DNP 2.2n 250V X7R switch-node snubber", 900, y,
                footprint=FOOTPRINTS["C_0805"], dnp=True,
                pin_nets={"1": (node, "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM21AR72E222KW01D"})
    s.place("R750", "R", "10R ISP Kelvin filter", 685, 250, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_PRE_SENSE", "local"), "2": ("MU12_ISP", "local")})
    s.place("R751", "R", "10R ISN Kelvin filter", 685, 260, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU_12V", "local"), "2": ("MU12_ISN", "local")})
    s.place("C770", "C", "100n differential current-sense filter", 685, 270,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU12_ISP", "local"), "2": ("MU12_ISN", "local")})
    s.place("R752", "R", "49.9R FB isolation", 685, 280, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU_12V", "local"), "2": ("MU12_FB_TOP", "local")})
    s.place("R753", "R", "102k 0.1% 12V FB high", 685, 290, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_FB_TOP", "local"), "2": ("MU12_FB", "local")})
    s.place("R754", "R", "11.3k 0.1% 12V FB low", 685, 300, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_FB", "local"), "2": ("GND", "local")})
    s.place("R755", "R", "15k COMP series", 685, 310, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_COMP", "local"), "2": ("MU12_COMP_RC", "local")})
    s.place("C771", "C", "4.7n COMP", 685, 320, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU12_COMP_RC", "local"), "2": ("GND", "local")})
    s.place("C772", "C", "100p C0G COMP HF", 685, 330, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU12_COMP", "local"), "2": ("GND", "local")})
    s.place("R756", "R", "49.9k 1% FSW = 400kHz", 685, 340, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_FSW", "local"), "2": ("GND", "local")})
    s.place("C767", "C", "10n DITH/SYNC spreading", 685, 350, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU12_DITH", "local"), "2": ("GND", "local")})
    s.place("R757", "R", "0R MODE forced-PWM", 685, 360, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_VCC", "local"), "2": ("MU12_MODE", "local")})
    s.place("R758", "R", "0R EXTVCC selects internal LDO", 685, 370, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_VCC", "local"), "2": ("MU12_EXTVCC", "local")})
    s.place("R759", "R", "150k 1% UVLO high; 9.0V rising", 740, 220, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("MU12_EN_UVLO", "local")})
    s.place("R760", "R", "23.7k 1% UVLO low", 740, 230, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_EN_UVLO", "local"), "2": ("GND", "local")})
    s.place("C773", "C", "100n UVLO noise filter", 740, 240, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU12_EN_UVLO", "local"), "2": ("GND", "local")})
    s.place("Q750", "Q_NMOS_SOT23_GSD", "BSS138 fail-off EN/UVLO clamp", 740, 250,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("MU12_FORCE_OFF", "local"), "2": ("GND", "local"),
                      "3": ("MU12_EN_UVLO", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"})
    s.place("Q751", "Q_NMOS_SOT23_GSD", "BSS138 active-high enable release", 790, 250,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={"1": ("MU_12V_ENABLE", "hier"), "2": ("GND", "local"),
                      "3": ("MU12_FORCE_OFF", "local")},
            extra_props={"Manufacturer": "onsemi", "MPN": "BSS138LT1G"})
    s.place("R761", "R", "100k fail-off gate divider low", 740, 260, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_FORCE_OFF", "local"), "2": ("GND", "local")})
    s.place("R766", "R", "100k fail-off gate divider high", 790, 260, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VSYS", "hier"), "2": ("MU12_FORCE_OFF", "local")})
    s.place("R767", "R", "100k MU_12V_ENABLE reset pulldown", 840, 260, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU_12V_ENABLE", "hier"), "2": ("GND", "local")})
    s.place("R768", "R", "10k LattePanda PSON required pull-up", 840, 270, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("MU_S0_HIGH", "hier")},
            extra_props={
                "ReferenceCircuit": "LattePanda Mu Power Control and Status design guide",
                "Datasheet": "https://docs.lattepanda.com/content/mu_edition/design_guide_pwctl_stat/",
            })
    s.place("U769", "74LVC1G08", "SN74LVC1G08DBVR qualified host-active AND", 840, 290,
            footprint=FOOTPRINTS["SN74LVC1G08DBV"],
            pin_nets={
                "1": ("MU_S0_HIGH", "hier"), "2": ("MU_12V_PG", "hier"),
                "3": ("GND", "local"), "4": ("MU_HOST_ACTIVE", "hier"),
                "5": ("MCU_3V3", "hier"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G08DBVR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf",
                "LogicContract": "MU_HOST_ACTIVE=MU_S0_HIGH_AND_MU_12V_PG",
            })
    s.place("C793", "C", "100n qualified host-active gate local", 840, 300,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("GND", "local")})
    s.place("R769", "R", "100k MU_HOST_ACTIVE fail-low", 840, 310,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU_HOST_ACTIVE", "hier"), "2": ("GND", "local")})

    # The Mu module does not export a host-port VBUS pin.  Create the physical
    # upstream VBUS used by permanently attached internal USB devices on the
    # carrier, then qualify its actual voltage.  Downstream data switches and
    # hub VBUS_DET consume INTERNAL_USB_VBUS_VALID, not a GPIO-state proxy.
    s.place("U770", "TPS2553D", "TPS2553DDBVR internal host VBUS 0.61A", 900, 325,
            footprint=FOOTPRINTS["TPS2553DDBV"],
            pin_nets={
                "1": ("SYS_5V", "hier"), "2": ("GND", "local"),
                "3": ("MU_HOST_ACTIVE", "hier"), "4": ("INTERNAL_USB_VBUS_FAULT_N", "hier"),
                "5": ("INTERNAL_USB_VBUS_ILIM", "local"), "6": ("INTERNAL_USB_VBUS", "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS2553DDBVR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps2553.pdf",
                "Function": "Carrier-generated physical VBUS for permanently attached Mu USB2 devices",
            })
    s.place("R773", "R", "43.2k 1% internal host VBUS 0.61A ILIM", 900, 337.7,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("INTERNAL_USB_VBUS_ILIM", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0743K2L"})
    s.place("R774", "R", "10k internal host VBUS fault pull-up", 900, 350.4,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("INTERNAL_USB_VBUS_FAULT_N", "hier")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0710KL"})
    s.place("C794", "C", "1u internal host VBUS switch input", 955, 325,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A105KA61D"})
    s.place("C830", "C", "10u internal host VBUS output", 955, 337.7,
            footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("INTERNAL_USB_VBUS", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BR61A106KE19L"})
    s.place("U771", "TLV803EA43RDBZR", "TLV803EA43RDBZR 4.38V physical internal VBUS supervisor", 900, 370,
            footprint=FOOTPRINTS["TLV803EA43RDBZR"],
            pin_nets={
                "1": ("INTERNAL_USB_VBUS_VALID", "hier"), "2": ("GND", "local"),
                "3": ("INTERNAL_USB_VBUS", "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TLV803EA43RDBZR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tlv803e.pdf",
                "Function": "Assert valid only after carrier-generated host VBUS exceeds the 4.38V falling threshold",
            })
    s.place("R775", "R", "10k internal host VBUS valid pull-up", 955, 370,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("INTERNAL_USB_VBUS_VALID", "hier")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0710KL"})
    s.place("C831", "C", "100n internal VBUS supervisor local", 955, 382.7,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("INTERNAL_USB_VBUS", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A104KA01D"})
    for ref, label, x, y, net_name, scope in (
        ("TP13", "Internal USB VBUS test", 1005, 325, "INTERNAL_USB_VBUS", "local"),
        ("TP14", "Internal USB VBUS valid test", 1005, 337.7, "INTERNAL_USB_VBUS_VALID", "hier"),
        ("TP15", "Internal USB VBUS fault test", 1005, 350.4, "INTERNAL_USB_VBUS_FAULT_N", "hier"),
    ):
        s.place(ref, "TestPoint", label, x, y,
                footprint=FOOTPRINTS["TestPoint_Pad"],
                pin_nets={"1": (net_name, scope)},
                extra_props={"ProcurementClass": "PCB copper test feature"},
                in_bom=False)

    # PCIe endpoints must not remain powered while the Mu host is off. One
    # slew-controlled 6A switch supplies NVMe, E-key and RTL8111H only in S0.
    # This intentionally means those endpoints cannot wake the Mu from S3.
    s.place("U772", "TPS22975N", "TPS22975NDSGR switched PCIe endpoint 3V3", 900, 420,
            footprint=FOOTPRINTS["TPS22975N"],
            pin_nets={
                "1": ("SYS_3V3", "hier"), "2": ("SYS_3V3", "hier"),
                "3": ("MU_HOST_ACTIVE", "hier"), "4": ("SYS_3V3", "hier"),
                "5": ("GND", "local"), "6": ("PCIE_3V3_CT", "local"),
                "7": ("PCIE_3V3", "hier"), "8": ("PCIE_3V3", "hier"),
                "9": ("GND", "local"),
            }, extra_props={
                "Manufacturer": "Texas Instruments", "MPN": "TPS22975NDSGR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps22975.pdf",
                "PowerPolicy": "PCIE_3V3 enabled only by MU_HOST_ACTIVE; no PCIe wake from S3",
            })
    s.place("R776", "R", "100k PCIe endpoint rail fail-low", 955, 420,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU_HOST_ACTIVE", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-07100KL"})
    s.place("C832", "C", "1u PCIe endpoint switch input", 955, 432.7,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R60J105KA01D"})
    s.place("C833", "C", "4.7n PCIe endpoint controlled slew", 955, 445.4,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("PCIE_3V3_CT", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71H472KA01D"})
    s.place("C834", "C", "47u 6.3V PCIe endpoint rail bulk", 955, 458.1,
            footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM32ER60J476ME20L"})
    s.place("C835", "C", "100n PCIe endpoint rail HF", 955, 470.8,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A104KA01D"})
    s.place("R762", "R", "100k PG pull-up", 740, 270, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MCU_3V3", "hier"), "2": ("MU_12V_PG", "hier")})
    s.place("C774", "C", "10n PG deglitch", 740, 280, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU_12V_PG", "hier"), "2": ("GND", "local")})
    s.place("R763", "R", "100k CC pull-up", 740, 290, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("MU12_VCC", "local"), "2": ("MU12_CC_N", "local")})
    s.place("C775", "C", "10n CC deglitch", 740, 300, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("MU12_CC_N", "local"), "2": ("GND", "local")})
    s.pwrflag(740, 320, "MU_12V")
    s.place("TP8", "TestPoint", "MU_12V test", 930, 440,
            footprint=FOOTPRINTS["TestPoint_Pad"],
            pin_nets={"1": ("MU_12V", "local")},
            extra_props={"ProcurementClass": "PCB copper test feature"}, in_bom=False)
    s.place("TP5", "TestPoint", "SYS_5V test", 900, 470,
            footprint=FOOTPRINTS["TestPoint_Pad"],
            pin_nets={"1": ("SYS_5V", "local")},
            extra_props={"ProcurementClass": "PCB copper test feature"}, in_bom=False)
    s.place("TP6", "TestPoint", "SYS_3V3 test", 930, 470,
            footprint=FOOTPRINTS["TestPoint_Pad"],
            pin_nets={"1": ("SYS_3V3", "local")},
            extra_props={"ProcurementClass": "PCB copper test feature"}, in_bom=False)
    s.place("TP12", "TestPoint", "MU_12V_PG test", 955, 440,
            footprint=FOOTPRINTS["TestPoint_Pad"],
            pin_nets={"1": ("MU_12V_PG", "hier")},
            extra_props={"ProcurementClass": "PCB copper test feature"}, in_bom=False)

    # Every Mu PCIe host-TX pair is externally AC-coupled. SSD PET is host TX;
    # SSD PER is host RX and already has coupling on the endpoint transmitter.
    for ref, raw, coupled in [
        ("C68", "PCIE_M_L0_TX_RAW_P", "PCIE_M_L0_TX_P"),
        ("C69", "PCIE_M_L0_TX_RAW_N", "PCIE_M_L0_TX_N"),
        ("C592", "PCIE_M_L1_TX_RAW_P", "PCIE_M_L1_TX_P"),
        ("C593", "PCIE_M_L1_TX_RAW_N", "PCIE_M_L1_TX_N"),
        ("C594", "PCIE_M_L2_TX_RAW_P", "PCIE_M_L2_TX_P"),
        ("C595", "PCIE_M_L2_TX_RAW_N", "PCIE_M_L2_TX_N"),
        ("C596", "PCIE_M_L3_TX_RAW_P", "PCIE_M_L3_TX_P"),
        ("C597", "PCIE_M_L3_TX_RAW_N", "PCIE_M_L3_TX_N"),
    ]:
        s.place(ref, "C", "220n 10V X7R NVMe TX AC", *q.next(),
                footprint=FOOTPRINTS["C_0402"],
                pin_nets={"1": (raw, "local"), "2": (coupled, "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A224KE01D"})
    s.place("C590", "C", "220n 10V X7R Wi-Fi TX AC", *q.next(), footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("WIFI_PCIE_TX_RAW_P", "local"), "2": ("WIFI_PCIE_TX_P", "hier")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A224KE01D"})
    s.place("C591", "C", "220n 10V X7R Wi-Fi TX AC", *q.next(), footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("WIFI_PCIE_TX_RAW_N", "local"), "2": ("WIFI_PCIE_TX_N", "hier")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM155R71A224KE01D"})

    # ---------------- J10: M.2 M-key NVMe slot ----------------
    s.text(300, 520, "== J10 M.2 M-key NVMe, default-BIOS PCIe Gen3 x4 ==")
    s.place("R47", "R", "0R / PERST isolation", 300, 545, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PLTRST_SRC_N", "local"), "2": ("PCIE_M_PERST_N", "local")})
    s.place("R48", "R", "0R / REFCLK+ isolation", 300, 555, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PCIE_M_REFCLK_SRC_P", "local"), "2": ("PCIE_M_REFCLK_P", "local")})
    s.place("R49", "R", "0R / REFCLK- isolation", 300, 565, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PCIE_M_REFCLK_SRC_N", "local"), "2": ("PCIE_M_REFCLK_N", "local")})
    s.place("R50", "R", "1k NVMe CLKREQ# low: request REFCLK", 300, 575, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("PCIE_M_CLKREQ_N", "local"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "Yageo", "MPN": "RC0603FR-071KL",
                "ClockPolicy": "Requests REFCLK; Mu BIOS/device-presence policy still controls clock availability",
            })
    m2m = default_pin_map("Bus_M.2_Socket_M", power_3v3_net="PCIE_3V3")
    m2m.update({
        "41": ("PCIE_M_L0_RX_N", "local"),
        "43": ("PCIE_M_L0_RX_P", "local"),
        "47": ("PCIE_M_L0_TX_N", "local"),
        "49": ("PCIE_M_L0_TX_P", "local"),
        "29": ("PCIE_M_L1_RX_N", "local"),
        "31": ("PCIE_M_L1_RX_P", "local"),
        "35": ("PCIE_M_L1_TX_N", "local"),
        "37": ("PCIE_M_L1_TX_P", "local"),
        "17": ("PCIE_M_L2_RX_N", "local"),
        "19": ("PCIE_M_L2_RX_P", "local"),
        "23": ("PCIE_M_L2_TX_N", "local"),
        "25": ("PCIE_M_L2_TX_P", "local"),
        "5": ("PCIE_M_L3_RX_N", "local"),
        "7": ("PCIE_M_L3_RX_P", "local"),
        "11": ("PCIE_M_L3_TX_N", "local"),
        "13": ("PCIE_M_L3_TX_P", "local"),
        "53": ("PCIE_M_REFCLK_N", "local"),
        "55": ("PCIE_M_REFCLK_P", "local"),
        "50": ("PCIE_M_PERST_N", "local"),
        "54": ("PCIE_WAKE_N", "local"),
        "52": ("PCIE_M_CLKREQ_N", "local"),
    })
    s.place("J10", "Bus_M.2_Socket_M", "Amphenol MDT420M01001 M-key NVMe socket (PCIe x4)", 440, 620,
            footprint=FOOTPRINTS["M2_M_key"], pin_nets=m2m,
            extra_props={"Manufacturer": "Amphenol", "MPN": "MDT420M01001"})
    s.place("C836", "C", "10u 6.3V NVMe socket local bulk", 500, 595,
            footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM21BR60J106ME19L"})
    s.place("C837", "C", "100n NVMe socket local HF", 540, 595,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71A104KA01D"})
    s.place("H3", "MountingHole_Pad", "M.2 M-key 2280 M2 grounded standoff 2.5mm", 520, 620,
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

    mainboard_hole_props = {
        "Hardware_Spec": "2.7mm isolated NPTH for M2.5 chassis screw; no electrical chassis bond",
    }
    for index, (x, y) in enumerate(((600, 600), (620, 600), (640, 600), (660, 600),
                                    (600, 620), (620, 620), (640, 620), (660, 620)), start=10):
        s.place(f"H{index}", "MountingHole", "M2.5 isolated mainboard mounting hole", x, y,
                footprint=FOOTPRINTS["Mainboard_M2.5_Hole"],
                extra_props=mainboard_hole_props, in_bom=False)

    s.text(20, 330, "NOTES:")
    s.text(20, 338, "Mu VIN and onboard eDP BL_PWR use regulated MU_12V; the exact B160QAN03.K harness/pinout remains a release gate.")
    s.text(20, 346, "Default-BIOS HSIO0/1 are independent native USB 3.2 Gen2 ports; HSIO3 + USB2_P1 feed M.2 E-key.")
    s.text(20, 354, "The verified B160QAN03.K panel connects to the Mu onboard eDP connector; DDIB is unused.")
    s.text(20, 362, "TCP0 HDMI 2.0 lane/HPD/DDC nets leave to sheet 6 for the external HDMI-A output.")
    s.text(20, 370, "USB2_P3 is EC; P4 pairs with USB-C 2; P5 is the system-audio hub; P7 is maker MCU; P8 is trackpad.")
    s.text(20, 378, "Native USB-C data/OC nets leave to sheet 4; VBUS switching, CC, muxing, and ESD live there.")
    s.text(20, 386, "SYS_5V and SYS_3V3 use TPS56637 6A-class bucks with XAL7070 inductors; endpoint load budgets remain a release check.")
    s.text(20, 393.7, "M.2 M-key uses default HSIO8-11 x4 and REFCLK2; no lane reversal and no TX/RX direction swap.")
    s.text(20, 401.32, "M.2 M-key: Mu TX->PET through 220n near J10; PET/PER naming is from the host perspective.")
    s.text(20, 408.94, "USB2_P6 is reserved for the Mu Type-C PD controller direction; trackpad consumes the former USB2_P8 spare.")
    s.text(20, 416.56, "MU_12V is a TPS552892EVM-derived 12V stage: 400kHz forced PWM, 3.33A nominal limit, and about 8.65-9.40V worst-case rising UVLO. Firmware requires VSYS >=10.0V.")
    s.text(20, 424.18, "MU_12V_ENABLE is active high and defaults low. Q750/Q751 force EN/UVLO low until EC firmware explicitly releases the rail; MU_12V_PG is pulled up to MCU_3V3.")
    s.text(20, 431.8, "POWER BUDGET HOLD: MU_12V is about 40W maximum for Mu plus eDP backlight. Lock BIOS PL1/PL2 only after measuring panel and whole-module draw; unrestricted 35W CPU mode is not released.")
    s.text(20, 439.42, "MU_S0_HIGH is Mu PSON with the required 10k pull-up to always-on MCU_3V3. It is a weak status signal for logic/NMOS gates only, never a load supply.")
    s.text(20, 447.04, "SLEEP POLICY: PSON is low in S3, so PCIe endpoint 3V3, user USB-C VBUS, trackpad, maker USB, and internal audio detach. Wake from those devices is intentionally unsupported.")
    s.text(20, 454.66, "MECHANICAL: the 8.0mm standard-orientation TE 2309411-1 socket requires two grounded 5.5mm M2 standoffs at H1/H2; SO-DIMM clips alone are not structural retention.")
    s.text(20, 462.28, "MECHANICAL: H3 is the grounded 2280 retainer for the 4.2mm M-key socket. H10-H17 are isolated M2.5 chassis holes; chassis bonding is a separate controlled point.")

    return s


def sheet_block(uuid_, x, y, w, h, name, filename, pins):
    x = snap_coord(x)
    y = snap_coord(y)
    w = snap_coord(w)
    h = snap_coord(h)
    pins_sexpr = []
    pin_coords = {}
    for i, pin_name in enumerate(pins):
        py = snap_coord(y + 5.08 + i * 5.08)
        px = snap_coord(x + w)
        pin_coords[pin_name] = (px, py)
        pins_sexpr.append(
            f'  (pin "{pin_name}" bidirectional\n'
            f'    (at {fmt_coord(px)} {fmt_coord(py)} 0)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left))\n'
            f'    (uuid {U()})\n'
            f'  )'
        )
    block = (
        f'(sheet\n'
        f'  (at {fmt_coord(x)} {fmt_coord(y)})\n'
        f'  (size {fmt_coord(w)} {fmt_coord(h)})\n'
        f'  (stroke (width 0.1524) (type solid))\n'
        f'  (fill (color 0 0 0 0.0))\n'
        f'  (uuid {uuid_})\n'
        f'  (property "Sheetname" "{name}"\n'
        f'    (at {fmt_coord(x)} {fmt_coord(y - 1.27)} 0)\n'
        f'    (effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'  )\n'
        f'  (property "Sheetfile" "{filename}"\n'
        f'    (at {fmt_coord(x)} {fmt_coord(y + h + 1.27)} 0)\n'
        f'    (effects (font (size 1.27 1.27)) (justify left top))\n'
        f'  )\n'
        + "\n".join(pins_sexpr) + "\n"
        f')'
    )
    return block, pin_coords


def wire_between(a, b):
    x1, y1 = (snap_coord(a[0]), snap_coord(a[1]))
    x2, y2 = (snap_coord(b[0]), snap_coord(b[1]))
    segments = []
    if y1 == y2:
        points = [(x1, y1), (x2, y2)]
    else:
        mid = snap_coord(max(x1, x2) + 10.16)
        points = [(x1, y1), (mid, y1), (mid, y2), (x2, y2)]
    for start, end in zip(points, points[1:]):
        sx, sy = start
        ex, ey = end
        segments.append(
            f'(wire\n'
            f'  (pts (xy {fmt_coord(sx)} {fmt_coord(sy)}) (xy {fmt_coord(ex)} {fmt_coord(ey)}))\n'
            f'  (stroke (width 0) (type default))\n'
            f'  (uuid {U()})\n'
            f')'
        )
    return "\n".join(segments)


def root_no_connect(coord):
    x, y = coord
    return f'(no_connect (at {fmt_coord(x)} {fmt_coord(y)}) (uuid {U()}))'


def root_label(coord, name):
    x, y = coord
    return (
        f'(label "{name}"\n'
        f'  (at {fmt_coord(x)} {fmt_coord(y)} 0)\n'
        f'  (effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'  (uuid {U()})\n'
        f')'
    )


def main():
    import generate_power_sheet as ps
    import generate_ec_mcu_sheet as ec
    import generate_usb_c_io_sheet as usb
    import generate_power_inputs_sheet as pwrin
    import generate_tcp0_external_hdmi_sheet as tcp0
    import generate_radio_oled_gps_sheet as radio
    import generate_internal_services_sheet as internal
    import generate_ham_radio_sheet as ham
    import generate_keyboard_interface_sheet as keyboard_if
    import generate_keyboard_daughterboard_sheet as keyboard
    import generate_radio_audio_codec_sheet as audio
    import generate_maker_mcu_sheet as maker
    import generate_system_audio_sheet as system_audio
    import generate_ethernet_sheet as ethernet

    power_sheet_uuid = stable_uuid("sheet-symbol:01_power_battery")
    ec_sheet_uuid = stable_uuid("sheet-symbol:02_ec_mcu")
    mu_sheet_uuid = stable_uuid("sheet-symbol:03_mu_carrier")
    usb_sheet_uuid = stable_uuid("sheet-symbol:04_usb_c_io")
    pwrin_sheet_uuid = stable_uuid("sheet-symbol:05_power_inputs")
    tcp0_sheet_uuid = stable_uuid("sheet-symbol:06_tcp0_external_hdmi")
    radio_sheet_uuid = stable_uuid("sheet-symbol:07_radio_oled_gps")
    internal_sheet_uuid = stable_uuid("sheet-symbol:08_internal_services")
    ham_sheet_uuid = stable_uuid("sheet-symbol:09_ham_radio")
    keyboard_interface_sheet_uuid = stable_uuid("sheet-symbol:12_keyboard_interface")
    keyboard_daughterboard_sheet_uuid = stable_uuid("sheet-symbol:12_keyboard_daughterboard")
    audio_sheet_uuid = stable_uuid("sheet-symbol:13_radio_audio_codec")
    maker_sheet_uuid = stable_uuid("sheet-symbol:14_maker_mcu")
    system_audio_sheet_uuid = stable_uuid("sheet-symbol:15_system_audio")
    ethernet_sheet_uuid = stable_uuid("sheet-symbol:16_gigabit_ethernet")

    def write_generated_sheet(context, filename, builder, page_number):
        with uuid_scope(context):
            sheet = builder()
            text = sheet.render(stable_uuid(f"{context}:self"), page_number=page_number)
        with open(os.path.join(PROJDIR, filename), "w", encoding="utf-8") as f:
            f.write(text)
        return sheet

    power_s = write_generated_sheet(
        "01_power_battery", "01_power_battery.kicad_sch", lambda: ps.build(power_sheet_uuid), "2"
    )
    ec_s = write_generated_sheet(
        "02_ec_mcu", "02_ec_mcu.kicad_sch", lambda: ec.build(ec_sheet_uuid), "3"
    )
    mu_s = write_generated_sheet(
        "03_mu_carrier", "03_mu_carrier.kicad_sch", lambda: build(mu_sheet_uuid), "4"
    )
    usb_s = write_generated_sheet(
        "04_usb_c_io", "04_usb_c_io.kicad_sch", lambda: usb.build(usb_sheet_uuid), "5"
    )
    pwrin_s = write_generated_sheet(
        "05_power_inputs", "05_power_inputs.kicad_sch", lambda: pwrin.build(pwrin_sheet_uuid), "6"
    )
    tcp0_s = write_generated_sheet(
        "06_tcp0_external_hdmi", "06_tcp0_external_hdmi.kicad_sch", lambda: tcp0.build(tcp0_sheet_uuid), "7"
    )
    radio_s = write_generated_sheet(
        "07_radio_oled_gps", "07_radio_oled_gps.kicad_sch", lambda: radio.build(radio_sheet_uuid), "8"
    )
    internal_s = write_generated_sheet(
        "08_internal_services", "08_internal_services.kicad_sch", lambda: internal.build(internal_sheet_uuid), "9"
    )
    ham_s = write_generated_sheet(
        "09_ham_radio", "09_ham_radio.kicad_sch", lambda: ham.build(ham_sheet_uuid), "10"
    )
    keyboard_if_s = write_generated_sheet(
        "12_keyboard_interface", "12_keyboard_interface.kicad_sch",
        lambda: keyboard_if.build(keyboard_interface_sheet_uuid), "12"
    )
    keyboard_daughterboard_s = write_generated_sheet(
        "12_keyboard_daughterboard", "12_keyboard_daughterboard.kicad_sch",
        lambda: keyboard.build(keyboard_daughterboard_sheet_uuid), "K1"
    )
    audio_s = write_generated_sheet(
        "13_radio_audio_codec", "13_radio_audio_codec.kicad_sch", lambda: audio.build(audio_sheet_uuid), "13"
    )
    maker_s = write_generated_sheet(
        "14_maker_mcu", "14_maker_mcu.kicad_sch", lambda: maker.build(maker_sheet_uuid), "14"
    )
    system_audio_s = write_generated_sheet(
        "15_system_audio", "15_system_audio.kicad_sch",
        lambda: system_audio.build(system_audio_sheet_uuid), "15"
    )
    ethernet_s = write_generated_sheet(
        "16_gigabit_ethernet", "16_gigabit_ethernet.kicad_sch",
        lambda: ethernet.build(ethernet_sheet_uuid), "16"
    )

    power_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON_ASSERT", "CHG_ENABLE",
        "CASE_PWRBTN_N", "MU_PWRBTN_N",
        "VSYS", "MCU_3V3", "EC_AON_IN", "AUX_DC_ADC", "USB_PD_SELECTED",
        "PD1_VBUS_RAW", "PD2_VBUS_RAW", "PD3_VBUS_RAW",
        "PACK_FAULT_N", "PACK_RETRY_PULSE", "AUX_FAULT_N", "AUX_PGOOD",
        "MAIN_USB_VALID_N", "MAIN_AUX_VALID_N", "AON_FAULT_N",
    ]
    ec_hier_nets = [
        "I2C_SCL", "I2C_SDA", "BQ_ALERT", "CHG_INT_N", "PMIC_QON_ASSERT", "CHG_ENABLE",
        "CASE_PWRBTN_N", "EC_AON_IN", "MCU_USB_DP", "MCU_USB_DM", "MCU_3V3", "AUX_DC_ADC", "MU_PWRBTN_N", "MU_RSTBTN_N",
        "WIFI_W_DISABLE1_N_EC", "WIFI_W_DISABLE2_N_EC", "SERVICE_MUX_RESET_N",
        "GNSS_UART_RX", "GNSS_UART_TX", "GNSS_RESET_N", "GNSS_PPS", "GNSS_EXTINT",
        "RADIO_GPIO0",
        "FAN_PWM", "FAN_TACH", "LID_CLOSED_N",
        "THERM_SKIN_ADC", "THERM_MU_ADC", "TRACKPAD_FAULT_N", "MU_S0_HIGH",
        "PD1_VALID_N", "PD2_VALID_N", "PD3_VALID_N",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N", "RADIO_VHF_PD_N", "RADIO_UHF_PD_N",
        "RADIO_VHF_SQL", "RADIO_UHF_SQL", "RADIO_VHF_RF_SEL_3V3", "RADIO_UHF_RF_SEL_3V3", "RADIO_AUDIO_SEL",
        "AUDIO_AMP_EC_EN", "AUDIO_MIC_EN", "INTERNAL_USB_VBUS_FAULT_N",
        "MU_12V_ENABLE", "MU_12V_PG",
        "KB_RGB_PWR_EN", "KB_RGB_FAULT_N", "KB_RGB_DATA_3V3",
        "KB_ROW0", "KB_ROW1", "KB_ROW2", "KB_ROW3", "KB_ROW4", "KB_ROW5", "KB_ROW6", "KB_ROW7",
        "KB_COL0", "KB_COL1", "KB_COL2", "KB_COL3", "KB_COL4", "KB_COL5", "KB_COL6", "KB_COL7",
        "KB_COL8", "KB_COL9", "KB_COL10", "KB_COL11", "KB_COL12", "KB_COL13", "KB_COL14",
        "PD1_PATH_EN", "PD2_PATH_EN", "PD3_PATH_EN",
        "PD1_EFUSE_FAULT_N", "PD2_EFUSE_FAULT_N", "PD3_EFUSE_FAULT_N",
        "PACK_FAULT_N", "PACK_RETRY_PULSE", "AUX_FAULT_N", "AUX_PGOOD",
        "MAIN_USB_VALID_N", "MAIN_AUX_VALID_N", "AON_FAULT_N",
    ]
    mu_hier_nets = [
        "VSYS", "SYS_5V", "SYS_3V3", "MCU_3V3", "MU_12V", "MU_PWRBTN_N", "MU_RSTBTN_N", "MU_S0_HIGH",
        "MU_HOST_ACTIVE", "PCIE_3V3", "INTERNAL_USB_VBUS_VALID", "INTERNAL_USB_VBUS_FAULT_N",
        "MU_12V_ENABLE", "MU_12V_PG",
        "EC_HOST_USB_DP", "EC_HOST_USB_DM", "AUDIO_USB_DP", "AUDIO_USB_DM",
        "TRACKPAD_USB_DP", "TRACKPAD_USB_DM",
        "MAKER_USB_DP", "MAKER_USB_DM",
        "USBC1_SSTX_P", "USBC1_SSTX_N", "USBC1_SSRX_P", "USBC1_SSRX_N", "USBC1_DP", "USBC1_DM",
        "USBC2_SSTX_P", "USBC2_SSTX_N", "USBC2_SSRX_P", "USBC2_SSRX_N", "USBC2_DP", "USBC2_DM",
        "MU_USB_OC_N",
        "TCP0_DDC_SDA", "TCP0_DDC_SCL", "TCP0_HPD",
        "TCP0_TX0_P", "TCP0_TX0_N", "TCP0_TX1_P", "TCP0_TX1_N",
        "TCP0_TXRX0_P", "TCP0_TXRX0_N", "TCP0_TXRX1_P", "TCP0_TXRX1_N",
        "WIFI_PCIE_TX_P", "WIFI_PCIE_TX_N", "WIFI_PCIE_RX_P", "WIFI_PCIE_RX_N",
        "WIFI_USB_DN", "WIFI_USB_DP", "WIFI_REFCLK_P", "WIFI_REFCLK_N",
        "WIFI_CLKREQ_N", "PCIE_WAKE_N", "PLTRST_SRC_N",
        "GBE_HOST_TX_P", "GBE_HOST_TX_N", "GBE_HOST_RX_P", "GBE_HOST_RX_N",
        "GBE_REFCLK_P", "GBE_REFCLK_N", "GBE_CLKREQ_N",
    ]
    usb_hier_nets = [
        "SYS_5V", "SYS_3V3", "MU_HOST_ACTIVE", "MU_USB_OC_N",
        "USBC1_SSTX_P", "USBC1_SSTX_N", "USBC1_SSRX_P", "USBC1_SSRX_N", "USBC1_DP", "USBC1_DM",
        "USBC2_SSTX_P", "USBC2_SSTX_N", "USBC2_SSRX_P", "USBC2_SSRX_N", "USBC2_DP", "USBC2_DM",
    ]
    pwrin_hier_nets = [
        "MCU_3V3", "USB_PD_SELECTED", "PD1_VALID_N", "PD2_VALID_N", "PD3_VALID_N",
        "PD1_VBUS_RAW", "PD2_VBUS_RAW", "PD3_VBUS_RAW",
        "PD1_PATH_EN", "PD2_PATH_EN", "PD3_PATH_EN",
        "PD1_EFUSE_FAULT_N", "PD2_EFUSE_FAULT_N", "PD3_EFUSE_FAULT_N",
        "PD1_I2C_SCL", "PD1_I2C_SDA", "PD2_I2C_SCL", "PD2_I2C_SDA",
        "PD3_I2C_SCL", "PD3_I2C_SDA",
    ]
    tcp0_hier_nets = [
        "SYS_5V", "SYS_3V3", "MU_HOST_ACTIVE", "TCP0_HPD", "TCP0_DDC_SDA", "TCP0_DDC_SCL",
        "TCP0_TX0_P", "TCP0_TX0_N", "TCP0_TX1_P", "TCP0_TX1_N",
        "TCP0_TXRX0_P", "TCP0_TXRX0_N", "TCP0_TXRX1_P", "TCP0_TXRX1_N",
    ]
    radio_hier_nets = [
        "PCIE_3V3", "MCU_3V3", "I2C_SCL", "I2C_SDA",
        "WIFI_PCIE_TX_P", "WIFI_PCIE_TX_N", "WIFI_PCIE_RX_P", "WIFI_PCIE_RX_N",
        "WIFI_USB_DN", "WIFI_USB_DP", "WIFI_REFCLK_P", "WIFI_REFCLK_N",
        "WIFI_CLKREQ_N", "PCIE_WAKE_N", "PLTRST_SRC_N",
        "WIFI_W_DISABLE1_N_EC", "WIFI_W_DISABLE2_N_EC",
        "SERVICE_MUX_RESET_N", "GNSS_UART_RX", "GNSS_UART_TX", "GNSS_RESET_N",
        "GNSS_PPS", "GNSS_EXTINT", "RADIO_GPIO0",
        "PD1_I2C_SCL", "PD1_I2C_SDA", "PD2_I2C_SCL", "PD2_I2C_SDA",
        "PD3_I2C_SCL", "PD3_I2C_SDA",
    ]
    internal_hier_nets = [
        "SYS_5V", "SYS_3V3", "MCU_3V3", "MU_12V", "MU_HOST_ACTIVE",
        "INTERNAL_USB_VBUS_VALID",
        "EC_HOST_USB_DP", "EC_HOST_USB_DM", "MCU_USB_DP", "MCU_USB_DM",
        "TRACKPAD_USB_DP", "TRACKPAD_USB_DM",
        "FAN_PWM", "FAN_TACH", "LID_CLOSED_N",
        "THERM_SKIN_ADC", "THERM_MU_ADC", "TRACKPAD_FAULT_N",
    ]
    ham_hier_nets = [
        "SYS_5V", "MCU_3V3",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N", "RADIO_VHF_PD_N", "RADIO_UHF_PD_N",
        "RADIO_VHF_SQL", "RADIO_UHF_SQL", "RADIO_VHF_RF_SEL_3V3", "RADIO_UHF_RF_SEL_3V3",
        "RADIO_AUDIO_SEL", "RADIO_GPIO0",
        "RADIO_VHF_AUDIO_OUT", "RADIO_UHF_AUDIO_OUT", "RADIO_VHF_MIC_IN", "RADIO_UHF_MIC_IN",
    ]
    keyboard_hier_nets = [
        "MCU_3V3", "SYS_5V", "I2C_SCL", "I2C_SDA",
        "KB_RGB_PWR_EN", "KB_RGB_FAULT_N", "KB_RGB_DATA_3V3",
        "KB_ROW0", "KB_ROW1", "KB_ROW2", "KB_ROW3", "KB_ROW4", "KB_ROW5", "KB_ROW6", "KB_ROW7",
        "KB_COL0", "KB_COL1", "KB_COL2", "KB_COL3", "KB_COL4", "KB_COL5", "KB_COL6", "KB_COL7",
        "KB_COL8", "KB_COL9", "KB_COL10", "KB_COL11", "KB_COL12", "KB_COL13", "KB_COL14",
    ]
    audio_hier_nets = [
        "MCU_3V3",
        "RADIO_CODEC_USB_DP", "RADIO_CODEC_USB_DM", "RADIO_CODEC_USB_VBUS",
        "RADIO_VHF_AUDIO_OUT", "RADIO_UHF_AUDIO_OUT", "RADIO_VHF_MIC_IN", "RADIO_UHF_MIC_IN",
        "RADIO_VHF_PTT_N", "RADIO_UHF_PTT_N",
    ]
    maker_hier_nets = [
        "SYS_5V", "INTERNAL_USB_VBUS_VALID", "MAKER_USB_DP", "MAKER_USB_DM",
    ]
    system_audio_hier_nets = [
        "SYS_5V", "SYS_3V3", "INTERNAL_USB_VBUS_VALID", "AUDIO_USB_DP", "AUDIO_USB_DM",
        "RADIO_CODEC_USB_DP", "RADIO_CODEC_USB_DM", "RADIO_CODEC_USB_VBUS",
        "AUDIO_AMP_EC_EN", "AUDIO_MIC_EN",
    ]
    ethernet_hier_nets = [
        "PCIE_3V3",
        "GBE_HOST_TX_P", "GBE_HOST_TX_N", "GBE_HOST_RX_P", "GBE_HOST_RX_N",
        "GBE_REFCLK_P", "GBE_REFCLK_N", "GBE_CLKREQ_N",
        "PLTRST_SRC_N", "PCIE_WAKE_N",
    ]

    reset_uuid_sequence("root")

    power_block, power_pins = sheet_block(
        power_sheet_uuid, 30, 40, 60, 150, "Power & Battery", "01_power_battery.kicad_sch",
        power_hier_nets,
    )
    ec_block, ec_pins = sheet_block(
        ec_sheet_uuid, 160, 40, 60, 480, "EC & MCU", "02_ec_mcu.kicad_sch",
        ec_hier_nets,
    )
    mu_block, mu_pins = sheet_block(
        mu_sheet_uuid, 290, 40, 70, 340, "Mu Carrier", "03_mu_carrier.kicad_sch",
        mu_hier_nets,
    )
    usb_block, usb_pins = sheet_block(
        usb_sheet_uuid, 30, 200, 90, 125, "Native USB-C I/O", "04_usb_c_io.kicad_sch",
        usb_hier_nets,
    )
    pwrin_block, pwrin_pins = sheet_block(
        pwrin_sheet_uuid, 550, 500, 90, 140, "Power Inputs", "05_power_inputs.kicad_sch",
        pwrin_hier_nets,
    )
    tcp0_block, tcp0_pins = sheet_block(
        tcp0_sheet_uuid, 420, 40, 105, 80, "TCP0 External HDMI", "06_tcp0_external_hdmi.kicad_sch",
        tcp0_hier_nets,
    )
    radio_block, radio_pins = sheet_block(
        radio_sheet_uuid, 30, 380, 105, 155, "Radio/OLED/GNSS", "07_radio_oled_gps.kicad_sch",
        radio_hier_nets,
    )
    internal_block, internal_pins = sheet_block(
        internal_sheet_uuid, 290, 390, 115, 155, "Internal Services", "08_internal_services.kicad_sch",
        internal_hier_nets,
    )
    ham_block, ham_pins = sheet_block(
        ham_sheet_uuid, 420, 220, 115, 170, "Ham Radio", "09_ham_radio.kicad_sch",
        ham_hier_nets,
    )
    keyboard_block, keyboard_pins = sheet_block(
        keyboard_interface_sheet_uuid, 420, 410, 120, 170, "Keyboard Mainboard FFC", "12_keyboard_interface.kicad_sch",
        keyboard_hier_nets,
    )
    audio_block, audio_pins = sheet_block(
        audio_sheet_uuid, 550, 330, 125, 85, "Radio Audio Codec", "13_radio_audio_codec.kicad_sch",
        audio_hier_nets,
    )
    maker_block, maker_pins = sheet_block(
        maker_sheet_uuid, 550, 440, 125, 45, "Maker MCU", "14_maker_mcu.kicad_sch",
        maker_hier_nets,
    )
    system_audio_block, system_audio_pins = sheet_block(
        system_audio_sheet_uuid, 680, 330, 135, 60, "System Audio", "15_system_audio.kicad_sch",
        system_audio_hier_nets,
    )
    ethernet_block, ethernet_pins = sheet_block(
        ethernet_sheet_uuid, 680, 420, 135, 65, "Gigabit Ethernet", "16_gigabit_ethernet.kicad_sch",
        ethernet_hier_nets,
    )

    root_labels = []
    seen_root_labels = set()

    def add_root_label(pins, net):
        coord = pins[net]
        key = (coord[0], coord[1], net)
        if key not in seen_root_labels:
            root_labels.append(root_label(coord, net))
            seen_root_labels.add(key)

    for net in [n for n in ec_hier_nets if n in power_hier_nets]:
        add_root_label(power_pins, net)
        add_root_label(ec_pins, net)
    add_root_label(power_pins, "VSYS")
    add_root_label(mu_pins, "VSYS")
    add_root_label(power_pins, "MCU_3V3")
    add_root_label(ec_pins, "MCU_3V3")
    add_root_label(mu_pins, "MCU_3V3")
    for net in ["MU_PWRBTN_N", "MU_RSTBTN_N"]:
        add_root_label(ec_pins, net)
        add_root_label(mu_pins, net)
    for net in ["MU_12V_ENABLE", "MU_12V_PG"]:
        add_root_label(ec_pins, net)
        add_root_label(mu_pins, net)
    for net in ["MU_S0_HIGH", "INTERNAL_USB_VBUS_FAULT_N"]:
        add_root_label(ec_pins, net)
        add_root_label(mu_pins, net)
    for net in usb_hier_nets:
        add_root_label(mu_pins, net)
        add_root_label(usb_pins, net)
    for net in pwrin_hier_nets:
        add_root_label(pwrin_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in radio_hier_nets:
            add_root_label(radio_pins, net)
    for net in tcp0_hier_nets:
        add_root_label(tcp0_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in radio_hier_nets:
        add_root_label(radio_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in internal_hier_nets:
        add_root_label(internal_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in ham_hier_nets:
        add_root_label(ham_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in keyboard_hier_nets:
        add_root_label(keyboard_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in audio_hier_nets:
        add_root_label(audio_pins, net)
        if net in ham_hier_nets:
            add_root_label(ham_pins, net)
        if net in system_audio_hier_nets:
            add_root_label(system_audio_pins, net)
    for net in maker_hier_nets:
        add_root_label(maker_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
    for net in system_audio_hier_nets:
        add_root_label(system_audio_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in ec_hier_nets:
            add_root_label(ec_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)
        if net in audio_hier_nets:
            add_root_label(audio_pins, net)
    for net in ethernet_hier_nets:
        add_root_label(ethernet_pins, net)
        if net in mu_hier_nets:
            add_root_label(mu_pins, net)
        if net in power_hier_nets:
            add_root_label(power_pins, net)

    root_ncs = []
    root_text = (
        f'(kicad_sch\n'
        f'  (version 20260306)\n'
        f'  (generator "eeschema")\n'
        f'  (generator_version "10.0")\n'
        f'  (uuid {U()})\n'
        f'  (paper "A1")\n'
        f'  (lib_symbols\n  )\n'
        f'{power_block}\n'
        f'{ec_block}\n'
        f'{mu_block}\n'
        f'{usb_block}\n'
        f'{pwrin_block}\n'
        f'{tcp0_block}\n'
        f'{radio_block}\n'
        f'{internal_block}\n'
        f'{ham_block}\n'
        f'{keyboard_block}\n'
        f'{audio_block}\n'
        f'{maker_block}\n'
        f'{system_audio_block}\n'
        f'{ethernet_block}\n'
        + "\n".join(root_labels) + "\n"
        + "\n".join(root_ncs) + "\n"
        f'  (sheet_instances\n'
        f'    (path "/"\n'
        f'      (page "1")\n'
        f'    )\n'
        f'  )\n'
        f'  (embedded_fonts no)\n'
        f')\n'
    )
    with open(os.path.join(PROJDIR, "ducktop2.kicad_sch"), "w", encoding="utf-8") as f:
        f.write(root_text)


if __name__ == "__main__":
    main()
