from build_ducktop2 import Sheet, FOOTPRINTS


def dra818_module(s, ref, value, x, y, prefix, sql, rf_sel):
    rf_raw = f"{prefix}_RF_RAW"
    af_out = f"{prefix}_AF_OUT"
    mic_in = f"RADIO_{prefix}_MIC_IN"
    hl = f"{prefix}_HL"
    uart_rxd = f"RADIO_{prefix}_UART_RXD"
    uart_txd = f"RADIO_{prefix}_UART_TXD"
    ptt_local_n = f"RADIO_{prefix}_PTT_LOCAL_N"
    pd_local_n = f"RADIO_{prefix}_PD_LOCAL_N"
    s.place(ref, "DRA818", value, x, y, footprint=FOOTPRINTS["DRA818"],
            pin_nets={
                # Dorji DRA818V V1.23 and DRA818U V1.13: only pins 9/10 are GND.
                "1": (sql, "hier"),
                "2": ("", "nc"),
                "3": (af_out, "local"),
                "4": ("", "nc"),
                "5": (ptt_local_n, "local"),
                "6": (pd_local_n, "local"),
                "7": (hl, "local"),
                "8": ("RADIO_4V0", "local"),
                "9": ("GND", "local"),
                "10": ("GND", "local"),
                "11": ("", "nc"),
                "12": (rf_raw, "local"),
                "13": ("", "nc"),
                "14": ("", "nc"),
                "15": ("", "nc"),
                "16": (uart_rxd, "local"),
                "17": (uart_txd, "local"),
                "18": (mic_in, "hier"),
            }, extra_props={
                "Manufacturer": "Dorji Applied Technologies",
                "MPN": "DRA818V" if prefix == "VHF" else "DRA818U",
            })
    return {
        "rf_raw": rf_raw,
        "rf_filtered": f"{prefix}_RF_FILTERED",
        "af_out": af_out,
        "mic_in": mic_in,
        "hl": hl,
        "rf_sel": rf_sel,
        "uart_rxd": uart_rxd,
        "uart_txd": uart_txd,
        "ptt_local_n": ptt_local_n,
        "pd_local_n": pd_local_n,
    }


LPF_PARTS = {
    "VHF": {
        "mpn": "LFCN-160+", "rating": "8W_MAX_AT_25C_DERATE_TO_3W_AT_100C",
        "datasheet": "https://www.minicircuits.com/pdfs/LFCN-160%2B.pdf",
        "symbol": "LFCN-160", "footprint": "MiniCircuits_LFCN_FV1206",
        "pin_nets": {"1": "rf_raw", "2": "GND", "3": "rf_filtered", "4": "GND"},
    },
    "UHF": {
        "mpn": "ULP-470+", "rating": "2W_MAX",
        "datasheet": "https://www.minicircuits.com/pdfs/ULP-470%2B.pdf",
        "symbol": "MiniCircuits_ULP", "footprint": "MiniCircuits_ULP",
        "pin_nets": {
            "1": "rf_raw", "2": "GND", "3": "rf_filtered",
            "4": "GND", "5": "GND", "6": "GND",
        },
    },
}


PE42820_GROUND_PINS = (
    "1", "3", "4", "5", "6", "7", "8", "9", "10", "11", "14", "15",
    "17", "18", "19", "20", "21", "22", "24", "25", "26", "27", "29",
    "30", "31", "32", "33",
)


def pe42820_nets(rfc, rf1, rf2, ctrl):
    pin_nets = {pin: ("GND", "local") for pin in PE42820_GROUND_PINS}
    pin_nets.update({
        "2": (rf1, "local"),
        "12": ("RADIO_4V0", "local"),
        "13": (ctrl, "local"),
        "16": ("GND", "local"),
        "23": (rf2, "local"),
        "28": (rfc, "local"),
    })
    return pin_nets


def lpf_and_antennas(s, refbase, prefix, x, y, nets, band_label):
    rf_raw = nets["rf_raw"]
    rf_filtered = nets["rf_filtered"]
    onboard = f"{prefix}_ANT_ONBOARD"
    external = f"{prefix}_ANT_EXTERNAL"
    rf_switch_rfc = f"{prefix}_RF_SWITCH_RFC"
    rf_switch_rf1 = f"{prefix}_RF_SWITCH_RF1"
    rf_switch_rf2 = f"{prefix}_RF_SWITCH_RF2"
    dc_block_refs = {
        "VHF": ("C270", "C271", "C272"),
        "UHF": ("C273", "C274", "C275"),
    }[prefix]
    part = LPF_PARTS[prefix]
    filter_nets = {
        pin: ((rf_raw if name == "rf_raw" else rf_filtered) if name != "GND" else "GND", "local")
        for pin, name in part["pin_nets"].items()
    }
    s.place(f"FL{refbase}", part["symbol"], f"Mini-Circuits {part['mpn']} {band_label} LPF", x + 27.94, y,
            footprint=FOOTPRINTS[part["footprint"]], pin_nets=filter_nets,
            dnp=False, in_bom=True,
            extra_props={
                "Manufacturer": "Mini-Circuits", "MPN": part["mpn"],
                "DatasheetURL": part["datasheet"], "PowerRating": part["rating"],
                "ReleaseGate": "VERIFY_ZERO_DC_50OHM_LAYOUT_VNA_SA_HARMONICS_AND_WORST_CASE_VSWR",
            })
    s.place(f"U{refbase}", "PE42820", f"PE42820B-X {band_label} 43dBm-CW RF switch", x + 112, y + 5.08,
            footprint=FOOTPRINTS["PE42820"],
            pin_nets=pe42820_nets(rf_switch_rfc, rf_switch_rf1, rf_switch_rf2, nets["rf_sel"]),
            dnp=False, in_bom=True,
            extra_props={
                "Manufacturer": "pSemi (Murata)",
                "MPN": "PE42820B-X",
                "DatasheetURL": "https://www.psemi.com/pdf/datasheets/pe42820ds.pdf",
                "PowerRating": "43dBm_CW_30MHz_TO_2GHz_POWERED_50OHM",
                "ControlRule": "CTRL_LOW_RFC_TO_RF2_INTERNAL;CTRL_HIGH_RFC_TO_RF1_EXTERNAL",
                "ReleaseGate": "NO_HOT_SWITCHING;VERIFY_0VDC_RF_PORTS_THERMAL_PATH_AND_VSWR",
            })
    s.place(f"C{refbase+3}", "C", "10n PE42820 VDD bypass per eval board", x + 132, y + 35.56,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")})
    s.place(f"C{refbase+4}", "C", "100p PE42820 V1 RF bypass per eval board", x + 150, y + 35.56,
            footprint=FOOTPRINTS["C_RF"],
            pin_nets={"1": (nets["rf_sel"], "local"), "2": ("GND", "local")})
    s.place(f"C{refbase+5}", "C", "DNP 0.2p PE42820 RFC match candidate", x + 75, y + 35.56,
            footprint=FOOTPRINTS["C_RF"],
            pin_nets={"1": (rf_switch_rfc, "local"), "2": ("GND", "local")},
            dnp=True, in_bom=False,
            extra_props={
                "CandidateValue": "0.2pF",
                "ReleaseGate": "FIT_ONLY_AFTER_BOARD_SPARAMETER_AND_VNA_MATCHING",
            })
    dc_block_props = {
        "Manufacturer": "KYOCERA AVX",
        "MPN": "600S101JT250XTV",
        "DatasheetURL": "https://www.kyocera-avx.com/products/rfmicrowave/capacitors/600-series/600s-series/",
        "RFContract": "100PF_C0G_250V_HIGH_Q_SERIES_DC_BLOCK;VERIFY_FINAL_50OHM_LAYOUT_WITH_VNA",
    }
    for ref, net_a, net_b, role, dx, dy in (
        (dc_block_refs[0], rf_filtered, rf_switch_rfc, "RFC", 88.9, 0),
        (dc_block_refs[1], rf_switch_rf1, external, "RF1_EXTERNAL", 142.24, 27.94),
        (dc_block_refs[2], rf_switch_rf2, onboard, "RF2_INTERNAL", 142.24, 0),
    ):
        s.place(ref, "C", f"100p C0G 250V {prefix} PE42820 {role} DC block", x + dx, y + dy,
                footprint="Capacitor_SMD:C_0603_1608Metric",
                pin_nets={"1": (net_a, "local"), "2": (net_b, "local")},
                extra_props=dc_block_props)
    s.place(f"J{refbase}", "Conn_Coaxial", f"{band_label} internal/PCB antenna feed U.FL", x + 170, y,
            footprint=FOOTPRINTS["Conn_Coaxial_UFL"],
            pin_nets={"1": (onboard, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Hirose", "MPN": "U.FL-R-SMT-1(01)"})
    s.place(f"J{refbase+1}", "Conn_Coaxial", f"{band_label} rear external SMA/u.FL path", x + 170, y + 27.94,
            footprint=FOOTPRINTS["Conn_Coaxial_SMA_Edge"],
            pin_nets={"1": (external, "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Molex", "MPN": "73251-1153"})


def build(sheet_symbol_uuid, supply_5v="SYS_5V", logic_3v3="MCU_3V3"):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 120
    s.refcounters["#FLG"] = 120

    s.text(20, 12.7, "== Dual-band amateur FM radio subsystem ==")
    s.text(20, 20.32, "VHF uses the DRA818V 2m module; UHF uses the DRA818U 70cm module.")
    s.text(20, 27.94, "RF output must pass real low-pass filters before either internal or rear external antenna selection.")

    # ---------------- Radio 4 V rail ----------------
    s.text(20, 50.8, f"== RADIO_4V0 rail from {supply_5v} ==")
    s.place("U70", "TPS54302", f"TPS54302 {supply_5v} -> RADIO_4V0", 80, 100,
            footprint=FOOTPRINTS["U_SOT23_6"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("RADIO_BUCK_SW", "local"),
                "3": (supply_5v, "hier"),
                "4": ("RADIO_BUCK_FB", "local"),
                "5": ("RADIO_BUCK_EN", "local"),
                "6": ("RADIO_BUCK_BOOT", "local"),
            },
            extra_props={
                "Manufacturer": "Texas Instruments",
                "MPN": "TPS54302DDCR",
                "Datasheet": "https://www.ti.com/lit/ds/symlink/tps54302.pdf",
            })
    s.place("R220", "R", "100k radio rail enable", 20, 76.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (supply_5v, "hier"), "2": ("RADIO_BUCK_EN", "local")})
    s.place("C220", "C", "10u 25V X7R radio VIN", 20, 88.9, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": (supply_5v, "hier"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM31CR71E106KA12L"})
    s.place("C221", "C", "100n BOOT", 20, 101.6, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_BUCK_BOOT", "local"), "2": ("RADIO_BUCK_SW", "local")})
    s.place("L70", "L", "3.3uH 20% 6.0A Isat20", 20, 114.3, footprint=FOOTPRINTS["L_XGL5030"],
            pin_nets={"1": ("RADIO_BUCK_SW", "local"), "2": ("RADIO_4V0", "local")},
            extra_props={
                "Manufacturer": "Coilcraft", "MPN": "XGL5030-332MEC",
                "Datasheet": "https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xgl/xgl5030/xgl5030-332/",
            })
    s.place("R221", "R", "100k 1% 4.0V FB hi", 20, 127, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("RADIO_BUCK_FB", "local")})
    s.place("R222", "R", "17.4k 1% 4.0V FB lo", 20, 139.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_BUCK_FB", "local"), "2": ("GND", "local")})
    for ref, y in (("C222", 152.4), ("C225", 158.75)):
        s.place(ref, "C", "22u 16V X7R radio output", 20, y, footprint=FOOTPRINTS["C_10u"],
                pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")},
                extra_props={"Manufacturer": "Murata", "MPN": "GRM31CZ71C226ME15L"})
    s.place("C223", "C", "100n 50V X7R radio HF", 20, 165.1, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")},
            extra_props={"Manufacturer": "Murata", "MPN": "GRM188R71H104KA93D"})
    s.place("C224", "C", "56p C0G TPS54302 feed-forward", 20, 171.45, footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("RADIO_BUCK_FB", "local")})
    s.pwrflag(110, 152.4, "RADIO_4V0")

    # ---------------- DRA818 module sockets ----------------
    s.text(250, 50.8, "== DRA818V/U castellated radio modules ==")
    vhf = dra818_module(
        s, "J70", "DRA818V 2m FM module", 300, 135, "VHF",
        "RADIO_VHF_SQL", "RADIO_VHF_RF_SEL_4V0",
    )
    uhf = dra818_module(
        s, "J71", "DRA818U 70cm FM module", 470, 135, "UHF",
        "RADIO_UHF_SQL", "RADIO_UHF_RF_SEL_4V0",
    )

    # Always-on logic converts the active-low EC requests and prevents both
    # modules from remaining in transmit at once. If both PTT requests assert,
    # both SAFE_N outputs go high (inactive). Firmware still uses break-before-
    # make sequencing, but the steady-state safety property is now hardware.
    interlock_props = {
        "Manufacturer": "Texas Instruments",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc2g32.pdf",
        "SafetyContract": "BOTH_PTT_REQUESTS_ASSERTED_FORCES_BOTH_MODULE_PTT_OUTPUTS_INACTIVE",
    }
    inverter_props = {
        **interlock_props,
        "MPN": "SN74LVC2G04DCKR",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc2g04.pdf",
    }
    s.place("U260", "74LVC2G04", "SN74LVC2G04DCKR PTT request inverter", 80, 185.42,
            unit=1, footprint=FOOTPRINTS["SN74LVC2G04DCK"],
            pin_nets={"1": ("RADIO_VHF_PTT_N", "hier"), "6": ("RADIO_VHF_PTT_REQ", "local")},
            extra_props=inverter_props)
    s.place("U260", "74LVC2G04", "SN74LVC2G04DCKR PTT request inverter", 110, 185.42,
            unit=2, footprint=FOOTPRINTS["SN74LVC2G04DCK"],
            pin_nets={"3": ("RADIO_UHF_PTT_N", "hier"), "4": ("RADIO_UHF_PTT_REQ", "local")},
            extra_props=inverter_props)
    s.place("U260", "74LVC2G04", "SN74LVC2G04DCKR PTT request inverter", 140, 185.42,
            unit=3, footprint=FOOTPRINTS["SN74LVC2G04DCK"],
            pin_nets={"2": ("GND", "local"), "5": (logic_3v3, "hier")},
            extra_props=inverter_props)
    s.place("U261", "74LVC2G32", "SN74LVC2G32DCUR dual-radio PTT interlock", 170, 185.42,
            unit=1, footprint=FOOTPRINTS["SN74LVC2G32DCU"],
            pin_nets={
                "1": ("RADIO_VHF_PTT_N", "hier"), "2": ("RADIO_UHF_PTT_REQ", "local"),
                "7": ("RADIO_VHF_PTT_SAFE_N", "local"),
            }, extra_props={**interlock_props, "MPN": "SN74LVC2G32DCUR"})
    s.place("U261", "74LVC2G32", "SN74LVC2G32DCUR dual-radio PTT interlock", 200, 185.42,
            unit=2, footprint=FOOTPRINTS["SN74LVC2G32DCU"],
            pin_nets={
                "5": ("RADIO_UHF_PTT_N", "hier"), "6": ("RADIO_VHF_PTT_REQ", "local"),
                "3": ("RADIO_UHF_PTT_SAFE_N", "local"),
            }, extra_props={**interlock_props, "MPN": "SN74LVC2G32DCUR"})
    s.place("U261", "74LVC2G32", "SN74LVC2G32DCUR dual-radio PTT interlock", 230, 185.42,
            unit=3, footprint=FOOTPRINTS["SN74LVC2G32DCU"],
            pin_nets={"4": ("GND", "local"), "8": (logic_3v3, "hier")},
            extra_props={**interlock_props, "MPN": "SN74LVC2G32DCUR"})
    for ref, x in (("C260", 170), ("C261", 205)):
        s.place(ref, "C", "100n PTT interlock local", x, 198.12,
                footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (logic_3v3, "hier"), "2": ("GND", "local")})

    # A radio-powered LVC buffer isolates every module input from the always-on
    # EC domain. SN74LVC3G34 specifies Ioff partial-power-down behavior, so its
    # outputs are high impedance while RADIO_4V0 is absent. Module TXD remains
    # an output and reaches the EC through a current-limiting series resistor.
    for ref, prefix, y, bypass, translator, tx_series, tx_bypass_a, tx_bypass_b, nets in (
        ("U242", "VHF", 205.74, "C246", "U243", "R243", "C247", "C248", vhf),
        ("U252", "UHF", 256.54, "C256", "U253", "R261", "C257", "C258", uhf),
    ):
        common = {
            "Manufacturer": "Texas Instruments", "MPN": "SN74LVC3G34DCUR",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc3g34.pdf",
            "PowerOffContract": "IOFF_OUTPUTS_HIGH_Z_WHEN_RADIO_4V0_IS_0V",
        }
        s.place(ref, "74LVC3G34", f"SN74LVC3G34DCUR {prefix} fail-safe control buffer",
                80, y, unit=1, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
                pin_nets={"1": (f"RADIO_{prefix}_UART_TX", "hier"),
                          "7": (nets["uart_rxd"], "local")}, extra_props=common)
        ptt_safe_n = f"RADIO_{prefix}_PTT_SAFE_N"
        s.place(ref, "74LVC3G34", f"SN74LVC3G34DCUR {prefix} fail-safe control buffer",
                120, y, unit=2, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
                pin_nets={"6": (ptt_safe_n, "local"),
                          "2": (nets["ptt_local_n"], "local")}, extra_props=common)
        s.place(ref, "74LVC3G34", f"SN74LVC3G34DCUR {prefix} fail-safe control buffer",
                160, y, unit=3, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
                pin_nets={"3": (f"RADIO_{prefix}_PD_N", "hier"),
                          "5": (nets["pd_local_n"], "local")}, extra_props=common)
        s.place(ref, "74LVC3G34", f"SN74LVC3G34DCUR {prefix} fail-safe control buffer",
                200, y, unit=4, footprint=FOOTPRINTS["SN74LVC3G34DCU"],
                pin_nets={"4": ("GND", "local"), "8": ("RADIO_4V0", "local")},
                extra_props=common)
        s.place(bypass, "C", f"100n {prefix} fail-safe buffer local", 220, y,
                footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")})
        # Translate the module's RADIO_4V0 UART output into the local 3.3 V
        # logic domain. The LVC1T45 has Ioff, so an unpowered daughterboard
        # cannot inject the always-on EC through its receive pin.
        translated_txd = f"RADIO_{prefix}_UART_TXD_3V3"
        s.place(translator, "SN74LVC1T45DBV", f"SN74LVC1T45 {prefix} TXD 4V-to-3V3 translator", 80, y + 15.24,
                footprint=FOOTPRINTS["SN74LVC1T45DBV"],
                pin_nets={
                    "1": ("RADIO_4V0", "local"), "2": ("GND", "local"),
                    "3": (nets["uart_txd"], "local"), "4": (translated_txd, "local"),
                    "5": ("RADIO_4V0", "local"), "6": (logic_3v3, "hier"),
                }, extra_props={
                    "Manufacturer": "Texas Instruments", "MPN": "SN74LVC1T45DBVR",
                    "PowerOffContract": "IOFF_PREVENTS_EC_INJECTION_WHEN_RADIO_RAILS_ARE_OFF",
                })
        s.place(tx_series, "R", f"100R {prefix} translated TXD series", 120, y + 15.24,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (translated_txd, "local"),
                          "2": (f"RADIO_{prefix}_UART_RX", "hier")})
        s.place(tx_bypass_a, "C", f"100n {prefix} UART translator RADIO_4V0", 160, y + 15.24,
                footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")})
        s.place(tx_bypass_b, "C", f"100n {prefix} UART translator 3V3", 200, y + 15.24,
                footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": (logic_3v3, "hier"), "2": ("GND", "local")})
    for ref, net, rail, value in (
        ("R235", vhf["ptt_local_n"], "RADIO_4V0", "10k VHF local PTT inactive"),
        ("R236", uhf["ptt_local_n"], "RADIO_4V0", "10k UHF local PTT inactive"),
        ("R237", vhf["pd_local_n"], "GND", "10k VHF local sleep"),
        ("R238", uhf["pd_local_n"], "GND", "10k UHF local sleep"),
    ):
        s.place(ref, "R", value, 20, 299.72 + (int(ref[1:]) - 235) * 10.16,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net, "local"), "2": (rail, "local")},
                extra_props={"Manufacturer": "Yageo", "MPN": "RC0603FR-0710KL"})

    # A radio-powered transparent latch follows antenna selection only while
    # PTT_SAFE_N is high. Once transmission starts, LE goes low and freezes the
    # selected antenna. The divider keeps the PE42820 CTRL pin below 3.6 V.
    for ref, prefix, y, bypass, divider, default in (
        ("U241", "VHF", 195.58, "C240", "R242", "R230"),
        ("U251", "UHF", 208.28, "C250", "R260", "R232"),
    ):
        raw = f"RADIO_{prefix}_RF_SEL_4V0_RAW"
        ctrl = f"RADIO_{prefix}_RF_SEL_4V0"
        s.place(ref, "74LVC1G373", f"SN74LVC1G373DCKR {prefix} transmit-safe RF-select latch", 390, y,
                footprint=FOOTPRINTS["SN74LVC1G373DCK"],
                pin_nets={
                    "1": (f"RADIO_{prefix}_PTT_SAFE_N", "local"), "2": ("GND", "local"),
                    "3": (f"RADIO_{prefix}_RF_SEL_3V3", "hier"),
                    "4": (raw, "local"),
                    "5": ("RADIO_4V0", "local"), "6": ("GND", "local"),
                }, extra_props={
                    "Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G373DCKR",
                    "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc1g373.pdf",
                    "SafetyContract": "ANTENNA_SELECTION_LATCHED_WHILE_PTT_SAFE_N_LOW",
                })
        s.place(divider, "R", f"10k 1% {prefix} PE42820 control divider top", 550, y,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (raw, "local"), "2": (ctrl, "local")})
        s.place(bypass, "C", f"100n {prefix} RF-select latch local", 450, y,
                footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")})
        s.place(default, "R", f"100k {prefix} RF-select EC reset default internal", 500, y,
                footprint=FOOTPRINTS["R"],
                pin_nets={"1": (f"RADIO_{prefix}_RF_SEL_3V3", "hier"), "2": ("GND", "local")})

    # The mainboard owns reset-safe defaults for every signal crossing the
    # daughterboard connector. Do not duplicate pull-ups to RADIO_DB_3V3 here:
    # they would weakly phantom-power the switched-off daughterboard rail.
    # Module-side defaults remain after the Ioff isolation buffers below.
    for i, (net, label) in enumerate([
        ("RADIO_VHF_PD_N", "VHF default sleep"),
        ("RADIO_UHF_PD_N", "UHF default sleep"),
    ]):
        s.place(f"R{225+i}", "R", f"100k {label}", 250, 246.38 + i * 12.7, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net, "hier"), "2": ("GND", "local")})
    for i, (net, label) in enumerate([
        ("RADIO_VHF_RF_SEL_4V0", "VHF antenna select default internal"),
        ("RADIO_UHF_RF_SEL_4V0", "UHF antenna select default internal"),
    ]):
        s.place(f"R{227+i}", "R", f"47k 1% {label}; PE42820 control divider low", 250, 271.78 + i * 12.7, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net, "local"), "2": ("GND", "local")})
    s.place("R229", "R", "0R VHF H/L LOW POWER - FIT", 390, 220.98, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vhf["hl"], "local"), "2": ("GND", "local")},
            dnp=False, in_bom=True,
            extra_props={
                "AssemblyState": "MUST_FIT_FOR_PROTOTYPE",
                "VariantRule": "FIT=LOW_0.5W;LFCN160_POWER_MARGIN_DOES_NOT_WAIVE_RF_SPECTRUM_TEST",
            })
    s.place("R231", "R", "0R UHF H/L LOW POWER - FIT", 530, 220.98, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (uhf["hl"], "local"), "2": ("GND", "local")},
            dnp=False, in_bom=True,
            extra_props={
                "AssemblyState": "MUST_FIT_FOR_PROTOTYPE",
                "VariantRule": "FIT=LOW_0.5W;OMIT=FLOAT_HIGH_1W_ONLY_AFTER_RF_RELEASE",
            })

    # ---------------- Audio/control harness ----------------
    s.text(250, 325.12, "== Radio audio/control harness to PCM2902 codec sheet ==")
    s.place("R233", "R", "1k VHF AF out", 250, 350.52, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vhf["af_out"], "local"), "2": ("RADIO_VHF_AUDIO_OUT", "hier")})
    s.place("R234", "R", "1k UHF AF out", 250, 363.22, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (uhf["af_out"], "local"), "2": ("RADIO_UHF_AUDIO_OUT", "hier")})
    s.place("C226", "C", "10n VHF audio RF shunt", 250, 375.92, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_VHF_AUDIO_OUT", "hier"), "2": ("GND", "local")})
    s.place("C227", "C", "10n UHF audio RF shunt", 250, 388.62, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_UHF_AUDIO_OUT", "hier"), "2": ("GND", "local")})
    s.place("J72", "Conn_01x10", "DNP radio audio/codec harness", 390, 375.92,
            footprint=FOOTPRINTS["Conn_01x10"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("RADIO_VHF_AUDIO_OUT", "hier"),
                "3": ("RADIO_UHF_AUDIO_OUT", "hier"),
                "4": (vhf["mic_in"], "hier"),
                "5": (uhf["mic_in"], "hier"),
                "6": ("", "nc"),
                "7": (logic_3v3, "hier"),
                "8": ("", "nc"),
                "9": ("GND", "local"),
                "10": ("GND", "local"),
            }, on_board=False)

    # ---------------- RF low-pass filters and antenna switches ----------------
    s.text(650, 50.8, "== VHF/UHF RF LPF + antenna selection ==")
    lpf_and_antennas(s, 240, "VHF", 650, 88.9, vhf, "2m/VHF")
    lpf_and_antennas(s, 250, "UHF", 650, 205.74, uhf, "70cm/UHF")

    s.gnd(830, 330.2)
    s.text(20, 205.74, "NOTES:")
    s.text(20, 213.36, "Dorji pinout: pins 9/10 GND; pins 2/4/11/13/14/15 NC; pin12 ANT 50 ohm; pin16 RXD; pin17 TXD.")
    s.text(20, 220.98, "H/L is never driven high: fitted 0R selects low power; omitted 0R floats for high power only after RF release.")
    s.text(20, 228.6, "FL240 LFCN-160+ (8W at 25C) and FL250 ULP-470+ (2W) are fitted LPFs; calculate both 50-ohm launches from the final stackup.")
    s.text(20, 236.22, "PE42820 is rated 43dBm CW through 2GHz when powered; RADIO_4V0 powers switch and module together.")
    s.text(20, 243.84, "A true 2m PCB antenna is laptop-scale-impractical; use a loaded internal/enclosure antenna feed or rear external whip.")
    s.text(20, 251.46, "Validate antenna match/VSWR, enclosure detuning, duty cycle, harmonics, and GNSS/Wi-Fi isolation before RF release.")
    s.text(20, 259.08, "GPS APRS support is software/audio-path work using the MAX-M10S sheet and the VHF radio path.")
    s.text(20, 266.7, "U260/U261 force both radios out of TX for simultaneous requests; U241/U251 freeze antenna selection for the full transmit interval.")
    s.text(20, 274.32, "R229/R231 select 0.5W prototype power. Filter ratings do not prove emissions compliance; verify both outputs on a spectrum analyzer.")
    s.text(20, 281.94, "R225/R226 and R235-R238 keep both modules asleep and PTT inactive through connector faults, reset, and rail ramp.")
    s.text(20, 289.56, "Firmware wake sequence: assert PD high, wait at least 500ms, complete/retry DMOCONNECT plus configuration, then allow PTT.")
    s.text(20, 297.18, "C270-C275 guarantee 0VDC at all PE42820 RF ports; verify their 50-ohm launches and both antenna paths with a VNA.")

    return s
