from build_ducktop2 import Sheet, FOOTPRINTS


def dra818_module(s, ref, value, x, y, prefix, uart_tx, uart_rx, ptt_n, pd_n, sql, rf_sel):
    rf_raw = f"{prefix}_RF_RAW"
    af_out = f"{prefix}_AF_OUT"
    mic_in = f"RADIO_{prefix}_MIC_IN"
    hl = f"{prefix}_HL"
    s.place(ref, "Conn_01x18", value, x, y, footprint=FOOTPRINTS["Conn_01x18"],
            pin_nets={
                # DRA818V/DRA818U V1.23 pin table: pins 2/4/11/13/14/15 are NC.
                "1": (sql, "hier"),
                "2": ("", "nc"),
                "3": (af_out, "local"),
                "4": ("", "nc"),
                "5": (ptt_n, "hier"),
                "6": (pd_n, "hier"),
                "7": (hl, "local"),
                "8": ("RADIO_4V0", "local"),
                "9": ("GND", "local"),
                "10": ("GND", "local"),
                "11": ("", "nc"),
                "12": (rf_raw, "local"),
                "13": ("GND", "local"),
                "14": ("", "nc"),
                "15": ("", "nc"),
                "16": (uart_tx, "hier"),
                "17": (uart_rx, "hier"),
                "18": (mic_in, "hier"),
            })
    return {
        "rf_raw": rf_raw,
        "rf_filtered": f"{prefix}_RF_FILTERED",
        "af_out": af_out,
        "mic_in": mic_in,
        "hl": hl,
        "rf_sel": rf_sel,
    }


LPF_VALUES = {
    "VHF": {"l": "75nH RF inductor", "c1": "12pF C0G", "c2": "39pF C0G", "c3": "12pF C0G"},
    "UHF": {"l": "24nH RF inductor", "c1": "3.9pF C0G", "c2": "12pF C0G", "c3": "3.9pF C0G"},
}


def lpf_and_antennas(s, refbase, prefix, x, y, nets, band_label):
    rf_raw = nets["rf_raw"]
    rf_mid = f"{prefix}_LPF_MID"
    rf_filtered = nets["rf_filtered"]
    onboard = f"{prefix}_ANT_ONBOARD"
    external = f"{prefix}_ANT_EXTERNAL"
    values = LPF_VALUES[prefix]
    s.place(f"L{refbase}", "L", f"{band_label} LPF L1 {values['l']}", x, y, footprint=FOOTPRINTS["L_RF"],
            pin_nets={"1": (rf_raw, "local"), "2": (rf_mid, "local")})
    s.place(f"L{refbase+1}", "L", f"{band_label} LPF L2 {values['l']}", x + 55, y, footprint=FOOTPRINTS["L_RF"],
            pin_nets={"1": (rf_mid, "local"), "2": (rf_filtered, "local")})
    s.place(f"C{refbase}", "C", f"{band_label} LPF C1 {values['c1']}", x, y + 12.7, footprint=FOOTPRINTS["C_RF"],
            pin_nets={"1": (rf_raw, "local"), "2": ("GND", "local")})
    s.place(f"C{refbase+1}", "C", f"{band_label} LPF C2 {values['c2']}", x + 27.94, y + 12.7, footprint=FOOTPRINTS["C_RF"],
            pin_nets={"1": (rf_mid, "local"), "2": ("GND", "local")})
    s.place(f"C{refbase+2}", "C", f"{band_label} LPF C3 {values['c3']}", x + 55, y + 12.7, footprint=FOOTPRINTS["C_RF"],
            pin_nets={"1": (rf_filtered, "local"), "2": ("GND", "local")})
    s.place(f"U{refbase}", "BGS12WN6E6327", f"{band_label} RF SPDT antenna switch", x + 112, y + 5.08,
            footprint=FOOTPRINTS["BGS12WN6E6327"],
            pin_nets={
                "1": (external, "local"),
                "2": ("GND", "local"),
                "3": (onboard, "local"),
                "4": ("MCU_3V3", "hier"),
                "5": (rf_filtered, "local"),
                "6": (nets["rf_sel"], "hier"),
            })
    s.place(f"J{refbase}", "Conn_Coaxial", f"{band_label} internal/PCB antenna feed U.FL", x + 170, y,
            footprint=FOOTPRINTS["Conn_Coaxial_UFL"],
            pin_nets={"1": (onboard, "local"), "2": ("GND", "local")})
    s.place(f"J{refbase+1}", "Conn_Coaxial", f"{band_label} rear external SMA/u.FL path", x + 170, y + 27.94,
            footprint=FOOTPRINTS["Conn_Coaxial_SMA_Edge"],
            pin_nets={"1": (external, "local"), "2": ("GND", "local")})


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 120
    s.refcounters["#FLG"] = 120

    s.text(20, 12.7, "== Dual-band amateur FM radio subsystem ==")
    s.text(20, 20.32, "VHF uses DRA818V/SA818-compatible 2m module; UHF uses DRA818U/SA818-compatible 70cm module.")
    s.text(20, 27.94, "RF output must pass real low-pass filters before either internal or rear external antenna selection.")

    # ---------------- Radio 4 V rail ----------------
    s.text(20, 50.8, "== RADIO_4V0 rail from SYS_5V ==")
    s.place("U70", "TPS54302", "TPS54302 SYS_5V -> RADIO_4V0", 80, 100,
            footprint=FOOTPRINTS["U_SOT23_6"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("RADIO_BUCK_SW", "local"),
                "3": ("SYS_5V", "hier"),
                "4": ("RADIO_BUCK_FB", "local"),
                "5": ("RADIO_BUCK_EN", "local"),
                "6": ("RADIO_BUCK_BOOT", "local"),
            })
    s.place("R220", "R", "100k radio rail enable", 20, 76.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("RADIO_BUCK_EN", "local")})
    s.place("C220", "C", "10u radio VIN", 20, 88.9, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("C221", "C", "100n BOOT", 20, 101.6, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_BUCK_BOOT", "local"), "2": ("RADIO_BUCK_SW", "local")})
    s.place("L70", "L", "2.2uH >=2A", 20, 114.3, footprint=FOOTPRINTS["L_buck"],
            pin_nets={"1": ("RADIO_BUCK_SW", "local"), "2": ("RADIO_4V0", "local")})
    s.place("R221", "R", "576k 1% 4.0V FB hi", 20, 127, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("RADIO_BUCK_FB", "local")})
    s.place("R222", "R", "100k 1% 4.0V FB lo", 20, 139.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_BUCK_FB", "local"), "2": ("GND", "local")})
    s.place("C222", "C", "47u radio rail bulk", 20, 152.4, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")})
    s.place("C223", "C", "100n radio rail", 20, 165.1, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("RADIO_4V0", "local"), "2": ("GND", "local")})
    s.pwrflag(110, 152.4, "RADIO_4V0")

    # ---------------- DRA818 module sockets ----------------
    s.text(250, 50.8, "== DRA818/SA818-compatible module sockets ==")
    vhf = dra818_module(
        s, "J70", "DRA818V 2m FM module socket", 300, 135, "VHF",
        "RADIO_VHF_UART_TX", "RADIO_VHF_UART_RX", "RADIO_VHF_PTT_N",
        "RADIO_VHF_PD_N", "RADIO_VHF_SQL", "RADIO_VHF_RF_SEL",
    )
    uhf = dra818_module(
        s, "J71", "DRA818U 70cm FM module socket", 470, 135, "UHF",
        "RADIO_UHF_UART_TX", "RADIO_UHF_UART_RX", "RADIO_UHF_PTT_N",
        "RADIO_UHF_PD_N", "RADIO_UHF_SQL", "RADIO_UHF_RF_SEL",
    )

    # Module control defaults.
    for i, (net, label) in enumerate([
        ("RADIO_VHF_PTT_N", "VHF PTT default inactive"),
        ("RADIO_UHF_PTT_N", "UHF PTT default inactive"),
        ("RADIO_VHF_PD_N", "VHF PD default pulled up"),
        ("RADIO_UHF_PD_N", "UHF PD default pulled up"),
    ]):
        s.place(f"R{223+i}", "R", f"100k {label}", 250, 220.98 + i * 12.7, footprint=FOOTPRINTS["R"],
                pin_nets={"1": ("MCU_3V3", "hier"), "2": (net, "hier")})
    for i, (net, label) in enumerate([
        ("RADIO_VHF_RF_SEL", "VHF antenna select default internal"),
        ("RADIO_UHF_RF_SEL", "UHF antenna select default internal"),
    ]):
        s.place(f"R{227+i}", "R", f"100k {label}", 250, 271.78 + i * 12.7, footprint=FOOTPRINTS["R"],
                pin_nets={"1": (net, "hier"), "2": ("GND", "local")})
    s.place("R229", "R", "0R VHF H/L default low power", 390, 220.98, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vhf["hl"], "local"), "2": ("GND", "local")})
    s.place("R230", "R", "DNP 0R VHF H/L high power", 390, 233.68, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (vhf["hl"], "local"), "2": ("MCU_3V3", "hier")})
    s.place("R231", "R", "0R UHF H/L default low power", 530, 220.98, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (uhf["hl"], "local"), "2": ("GND", "local")})
    s.place("R232", "R", "DNP 0R UHF H/L high power", 530, 233.68, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (uhf["hl"], "local"), "2": ("MCU_3V3", "hier")})

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
                "6": ("RADIO_AUDIO_SEL", "hier"),
                "7": ("MCU_3V3", "hier"),
                "8": ("RADIO_GPIO0", "hier"),
                "9": ("GND", "local"),
                "10": ("GND", "local"),
            })

    # ---------------- RF low-pass filters and antenna switches ----------------
    s.text(650, 50.8, "== VHF/UHF RF LPF + antenna selection ==")
    lpf_and_antennas(s, 240, "VHF", 650, 88.9, vhf, "2m/VHF")
    lpf_and_antennas(s, 250, "UHF", 650, 205.74, uhf, "70cm/UHF")

    s.gnd(830, 330.2)
    s.text(20, 205.74, "NOTES:")
    s.text(20, 213.36, "DRA818V/U pinout is locked to Dorji V1.23: pin16 RXD<-EC_TX, pin17 TXD->EC_RX, pin12 RF 50 ohm.")
    s.text(20, 220.98, "LPF values are 5th-order Butterworth starting points; simulate/bench-check harmonics for Part 97 before fab.")
    s.text(20, 228.6, "BGS12 control low selects RF1/pin3 internal feed; high selects RF2/pin1 rear external feed.")
    s.text(20, 236.22, "Default RF switch state selects the internal/PCB antenna feed; rear external SMA/u.FL is the high-performance option.")
    s.text(20, 243.84, "A true 2m PCB antenna is laptop-scale-impractical; use a loaded internal/enclosure antenna feed or rear external whip.")
    s.text(20, 251.46, "Use board-edge keepouts around rear external SMA paths; internal antennas need separation from GPS and Wi-Fi antennas.")
    s.text(20, 259.08, "GPS APRS support is software/audio-path work using the MAX-M10S sheet and the VHF radio path.")
    s.text(20, 266.7, "RF switch truth table, RF layout, and filter parasitics remain RF-review items; DRA818 module pinout is set.")

    return s
