import genlib

from build_ducktop2 import FOOTPRINTS, Sheet


USB2512B_FOOTPRINT = (
    "Package_DFN_QFN:QFN-36-1EP_6x6mm_P0.5mm_"
    "EP3.7x3.7mm_ThermalVias"
)
PCM2900C_FOOTPRINT = "Package_SO:SSOP-28_5.3x10.2mm_P0.65mm"
TPA2012D2_FOOTPRINT = (
    "Package_DFN_QFN:WQFN-20-1EP_4x4mm_P0.5mm_"
    "EP2.7x2.7mm_ThermalVias"
)
SINGLE_AND_FOOTPRINT = "Package_TO_SOT_SMD:SOT-23-5"
SPEAKER_FOOTPRINT = FOOTPRINTS["Conn_01x02_Service_GH"]
FERRITE_FOOTPRINT = "Inductor_SMD:L_0603_1608Metric"
POLYFUSE_FOOTPRINT = "Fuse:Fuse_1812_4532Metric"


def usb2512b_nets():
    return {
        "1": ("RADIO_CODEC_USB_DM", "hier"),
        "2": ("RADIO_CODEC_USB_DP", "hier"),
        "3": ("SYSTEM_DAC_USB_DM", "local"),
        "4": ("SYSTEM_DAC_USB_DP", "local"),
        "5": ("SYS_3V3", "hier"),
        "6": ("", "nc"),
        "7": ("", "nc"),
        "8": ("", "nc"),
        "9": ("", "nc"),
        "10": ("SYS_3V3", "hier"),
        "11": ("", "nc"),
        "12": ("HUB_PORT1_EN", "local"),
        "13": ("HUB_PORT1_OC_N", "local"),
        "14": ("HUB_CRFILT", "local"),
        "15": ("SYS_3V3", "hier"),
        "16": ("HUB_PORT2_EN", "local"),
        "17": ("HUB_PORT2_OC_N", "local"),
        "18": ("", "nc"),
        "19": ("", "nc"),
        "20": ("", "nc"),
        "21": ("", "nc"),
        "22": ("HUB_NON_REM1", "local"),
        "23": ("SYS_3V3", "hier"),
        "24": ("HUB_CFG_SEL0", "local"),
        "25": ("HUB_CFG_SEL1", "local"),
        "26": ("HUB_RESET_N", "local"),
        "27": ("HUB_VBUS_DET", "local"),
        "28": ("HUB_NON_REM0", "local"),
        "29": ("SYS_3V3", "hier"),
        "30": ("AUDIO_USB_DM", "hier"),
        "31": ("AUDIO_USB_DP", "hier"),
        "32": ("HUB_XO", "local"),
        "33": ("HUB_XI", "local"),
        "34": ("HUB_PLLFILT", "local"),
        "35": ("HUB_RBIAS", "local"),
        "36": ("SYS_3V3", "hier"),
        "37": ("GND", "local"),
    }


def pcm2900c_nets():
    return {
        "1": ("CODEC_USB_DP", "local"),
        "2": ("CODEC_USB_DM", "local"),
        "3": ("CODEC_VBUS", "local"),
        "4": ("GND", "local"),
        "5": ("", "nc"),
        "6": ("", "nc"),
        "7": ("", "nc"),
        "8": ("CODEC_VDDI", "local"),
        "9": ("CODEC_VDDI", "local"),
        "10": ("CODEC_VCCCI", "local"),
        "11": ("GND", "local"),
        "12": ("MIC_ADC_L", "local"),
        "13": ("MIC_ADC_R", "local"),
        "14": ("CODEC_VCOM", "local"),
        "15": ("DAC_VOUT_R", "local"),
        "16": ("DAC_VOUT_L", "local"),
        "17": ("CODEC_VCCP1I", "local"),
        "18": ("GND", "local"),
        "19": ("CODEC_VCCP2I", "local"),
        "20": ("CODEC_XTO", "local"),
        "21": ("CODEC_XTI", "local"),
        "22": ("GND", "local"),
        "23": ("CODEC_VCCXI", "local"),
        "24": ("GND", "local"),
        "25": ("", "nc"),
        "26": ("GND", "local"),
        "27": ("CODEC_VDDI", "local"),
        "28": ("DAC_SSPND", "local"),
    }


def tpa2012d2_nets():
    return {
        "1": ("GND", "local"),
        "2": ("AMP_OUT_LP", "local"),
        "3": ("AUDIO_5V", "local"),
        "4": ("GND", "local"),
        "5": ("AMP_OUT_LN", "local"),
        "6": ("", "nc"),
        "7": ("AMP_ENABLE", "local"),
        "8": ("AMP_ENABLE", "local"),
        "9": ("AUDIO_5V", "local"),
        "10": ("", "nc"),
        "11": ("AMP_OUT_RN", "local"),
        "12": ("GND", "local"),
        "13": ("AUDIO_5V", "local"),
        "14": ("AMP_OUT_RP", "local"),
        "15": ("AUDIO_5V", "local"),
        "16": ("AMP_IN_RP", "local"),
        "17": ("AMP_IN_RN", "local"),
        "18": ("GND", "local"),
        "19": ("AMP_IN_LN", "local"),
        "20": ("AMP_IN_LP", "local"),
        "21": ("GND", "local"),
    }


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    # Keep generated power-symbol references globally unique across the
    # hierarchical project.  The Mu carrier already owns the 400 range.
    s.refcounters["#PWR"] = 1500
    s.refcounters["#FLG"] = 1500

    s.text(20, 12.7, "== System audio: embedded two-port USB hub, playback/record codec, microphone, and stereo BTL amplifier ==")
    s.text(20, 20.32, "Mu USB2_P5 feeds a self-powered USB2512B multi-TT hub. Port 1 is the existing radio codec; port 2 is the PCM2900C system codec.")
    s.text(20, 27.94, "Both downstream devices are non-removable. TPS2052B implements host-controlled VBUS and individual overcurrent feedback.")

    s.text(20, 45.72, "== Protected 5V audio branch and downstream USB power ==")
    s.place(
        "F400", "Fuse", "1.5A hold resettable PTC; Littelfuse 1812L150/16DR",
        20, 63.5, footprint=POLYFUSE_FOOTPRINT,
        pin_nets={"1": ("SYS_5V", "hier"), "2": ("AUDIO_5V", "local")},
        extra_props={
            "Manufacturer": "Littelfuse",
            "MPN": "1812L150/16DR",
            "Function": "Protected local system-audio branch",
        },
    )
    s.place(
        "C400", "C", "100n AUDIO_5V high-frequency bypass", 150, 55.88,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("AUDIO_5V", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C401", "C", "10u AUDIO_5V local bulk", 150, 68.58,
        footprint=FOOTPRINTS["C_10u"],
        pin_nets={"1": ("AUDIO_5V", "local"), "2": ("GND", "local")},
    )
    s.pwrflag(720, 63.5, "AUDIO_5V")
    # Bind every local "GND" label on this generated sheet to KiCad's global
    # ground net.  Without one GND power symbol, KiCad scopes those labels to
    # /System Audio/GND instead of joining the motherboard ground plane.
    s.gnd(720, 76.2)
    s.place(
        "U402", "TPS2052B", "TPS2052BDR dual 500mA USB power switch",
        280, 63.5, footprint=FOOTPRINTS["TPS2052B"],
        pin_nets={
            "1": ("GND", "local"),
            "2": ("AUDIO_5V", "local"),
            "3": ("HUB_PORT1_EN", "local"),
            "4": ("HUB_PORT2_EN", "local"),
            "5": ("HUB_PORT2_OC_N", "local"),
            "6": ("SYSTEM_DAC_USB_VBUS", "local"),
            "7": ("RADIO_CODEC_USB_VBUS", "hier"),
            "8": ("HUB_PORT1_OC_N", "local"),
        },
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "TPS2052BDR",
            "ReferenceCircuit": "USB2512B checklist Figure 5-2 individual port power",
        },
    )
    for ref, value, net, x in [
        ("C402", "1u TPS2052B input", "AUDIO_5V", 400),
        ("C403", "10u radio-codec VBUS", "RADIO_CODEC_USB_VBUS", 500),
        ("C404", "10u system-DAC VBUS", "SYSTEM_DAC_USB_VBUS", 600),
    ]:
        s.place(
            ref, "C", value, x, 63.5,
            footprint=FOOTPRINTS["C_10u"] if "10u" in value else FOOTPRINTS["C_1u"],
            pin_nets={"1": (net, "hier" if net == "RADIO_CODEC_USB_VBUS" else "local"), "2": ("GND", "local")},
        )
    for ref, net, x in [
        ("C446", "RADIO_CODEC_USB_VBUS", 500),
        ("C447", "SYSTEM_DAC_USB_VBUS", 600),
    ]:
        s.place(
            ref, "C_Polarized", "100u 10V polymer downstream VBUS bulk", x, 76.2,
            footprint="Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B",
            pin_nets={"1": (net, "hier" if net == "RADIO_CODEC_USB_VBUS" else "local"), "2": ("GND", "local")},
            extra_props={
                "Manufacturer": "KEMET",
                "MPN": "T520B107M010ATE070",
                "Polarity": "PAD1_POSITIVE",
            },
        )

    s.text(20, 93.98, "== U400 USB2512B-AEZG-TR: self-powered, strap-configured, both ports non-removable ==")
    s.place(
        "U400", "USB2512B", "USB2512B-AEZG-TR two-port HS multi-TT hub",
        300, 160.02, footprint=USB2512B_FOOTPRINT,
        pin_nets=usb2512b_nets(),
        extra_props={
            "Manufacturer": "Microchip Technology",
            "MPN": "USB2512B-AEZG-TR",
            "Configuration": "CFG_SEL[1:0]=00 self-powered straps; NON_REM[1:0]=10",
            "ReferenceCircuit": "Current DS00001692 plus DS00004539A hardware checklist",
        },
    )

    for ref, value, net, x, y in [
        ("C405", "100n VDDA33 pin 5", "SYS_3V3", 20, 116.84),
        ("C406", "100n VDDA33 pin 10", "SYS_3V3", 100, 116.84),
        ("C407", "100n VDDA33 pin 29", "SYS_3V3", 180, 116.84),
        ("C408", "100n VDDA33 pin 36", "SYS_3V3", 20, 129.54),
        ("C409", "100n VDD33 pin 15", "SYS_3V3", 100, 129.54),
        ("C410", "100n VDD33 pin 23", "SYS_3V3", 180, 129.54),
        ("C411", "1u shared hub 3V3 bulk", "SYS_3V3", 100, 142.24),
    ]:
        s.place(
            ref, "C", value, x, y,
            footprint=FOOTPRINTS["C_1u"] if value.startswith("1u") else FOOTPRINTS["C_100n"],
            pin_nets={"1": (net, "hier"), "2": ("GND", "local")},
        )

    s.place(
        "C412", "C", "100n CRFILT low-ESR", 440, 116.84,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("HUB_CRFILT", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C413", "C", "100n PLLFILT low-ESR", 440, 129.54,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("HUB_PLLFILT", "local"), "2": ("GND", "local")},
    )
    s.place(
        "R400", "R", "12.0k 1% USB transceiver RBIAS", 440, 142.24,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("HUB_RBIAS", "local"), "2": ("GND", "local")},
        extra_props={"Tolerance": "1%", "Placement": "Close to U400 pin 35"},
    )

    s.place(
        "Y400", "Crystal_GND24", "ABM8-24.000MHZ-10-1-U-T 24MHz 10pF CL",
        540, 121.92, footprint=FOOTPRINTS["Crystal_HSE"],
        pin_nets={
            "1": ("HUB_XI", "local"),
            "2": ("GND", "local"),
            "3": ("HUB_XO", "local"),
            "4": ("GND", "local"),
        },
        extra_props={
            "Manufacturer": "Abracon",
            "MPN": "ABM8-24.000MHZ-10-1-U-T",
            "Requirement": "24MHz fundamental; total tolerance comfortably inside +/-350ppm",
            "LoadCalculation": "18pF each leg gives about 10pF with approximately 1pF pin/PCB stray",
        },
    )
    s.place(
        "C414", "C", "18p C0G 5% hub crystal load", 650, 116.84,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("HUB_XI", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C415", "C", "18p C0G 5% hub crystal load", 650, 129.54,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("HUB_XO", "local"), "2": ("GND", "local")},
    )

    s.place(
        "U401", "TLV803EA29RDBZR", "TLV803EA29RDBZR 2.93V reset supervisor",
        540, 157.48, footprint=FOOTPRINTS["TLV803EA29RDBZR"],
        pin_nets={
            "1": ("HUB_RESET_N", "local"),
            "2": ("GND", "local"),
            "3": ("SYS_3V3", "hier"),
        },
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "TLV803EA29RDBZR",
            "Function": "Hold USB hub reset until 3.3V is valid",
        },
    )
    s.place(
        "R401", "R", "10k reset open-drain pull-up", 650, 149.86,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("HUB_RESET_N", "local")},
    )
    s.place(
        "C416", "C", "100n reset supervisor local", 650, 162.56,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")},
    )

    for ref, value, pin_net, rail_net, rail_kind, x, y in [
        ("R402", "10k NON_REM1 strap high", "HUB_NON_REM1", "SYS_3V3", "hier", 20, 177.8),
        ("R403", "100k NON_REM0 strap low", "HUB_NON_REM0", "GND", "local", 150, 177.8),
        ("R404", "100k CFG_SEL0 strap low", "HUB_CFG_SEL0", "GND", "local", 280, 177.8),
        ("R405", "100k CFG_SEL1 strap low", "HUB_CFG_SEL1", "GND", "local", 410, 177.8),
    ]:
        s.place(
            ref, "R", value, x, y, footprint=FOOTPRINTS["R"],
            pin_nets={"1": (pin_net, "local"), "2": (rail_net, rail_kind)},
        )
    s.place(
        "R417", "R", "0R physical internal-host VBUS-valid link", 540, 177.8,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("INTERNAL_USB_VBUS_VALID", "hier"), "2": ("HUB_VBUS_DET", "local")},
        extra_props={
            "Manufacturer": "Yageo", "MPN": "RC0603JR-070RL",
            "Function": "USB2512B VBUS_DET follows a supervisor on the physical carrier-generated upstream VBUS",
        },
    )
    s.place(
        "R408", "R", "10k port 1 OC_N noise-margin pull-up", 540, 190.5,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("HUB_PORT1_OC_N", "local")},
    )
    s.place(
        "R409", "R", "10k port 2 OC_N noise-margin pull-up", 650, 190.5,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("HUB_PORT2_OC_N", "local")},
    )

    s.text(20, 210.82, "== U410 PCM2900CDBR system USB playback/record codec; TI Figure 38 bus-powered core ==")
    s.place(
        "U410", "PCM2900C", "PCM2900CDBR USB Audio Class stereo codec",
        300, 266.7, footprint=PCM2900C_FOOTPRINT,
        pin_nets=pcm2900c_nets(),
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "PCM2900CDBR",
            "ReferenceCircuit": "PCM2900C/PCM2902C datasheet Figure 38 PCM2900C bus-powered application",
            "USBIdentity": "VID 0x08BB / PID 0x29C0; distinct from radio PCM2902C PID 0x29C2",
        },
    )
    s.place(
        "R410", "R", "22R system DAC USB D- series", 20, 233.68,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("SYSTEM_DAC_USB_DM", "local"), "2": ("CODEC_USB_DM", "local")},
    )
    s.place(
        "R411", "R", "22R system DAC USB D+ series", 20, 246.38,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("SYSTEM_DAC_USB_DP", "local"), "2": ("CODEC_USB_DP", "local")},
    )
    s.place(
        "R412", "R", "1.5k USB D+ pull-up per TI Figure 38", 150, 233.68,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("CODEC_VDDI", "local"), "2": ("CODEC_USB_DP", "local")},
    )
    s.place(
        "R413", "R", "2.2R PCM2900C VBUS filter", 150, 246.38,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("SYSTEM_DAC_USB_VBUS", "local"), "2": ("CODEC_VBUS", "local")},
    )
    s.pwrflag(250, 246.38, "CODEC_VBUS")

    s.place(
        "Y410", "Crystal_GND24", "ABM8G-106-12.000MHZ-T 12MHz 10pF CL",
        500, 233.68, footprint=FOOTPRINTS["Crystal_HSE"],
        pin_nets={
            "1": ("CODEC_XTI", "local"),
            "2": ("GND", "local"),
            "3": ("CODEC_XTO", "local"),
            "4": ("GND", "local"),
        },
        extra_props={
            "Manufacturer": "Abracon",
            "MPN": "ABM8G-106-12.000MHZ-T",
            "LoadCalculation": "18pF each leg gives about 10pF with approximately 1pF pin/PCB stray",
        },
    )
    s.place(
        "R414", "R", "1M PCM2900 crystal feedback", 620, 233.68,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("CODEC_XTI", "local"), "2": ("CODEC_XTO", "local")},
    )
    s.place(
        "C420", "C", "18p C0G 5% codec crystal load", 500, 251.46,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("CODEC_XTI", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C421", "C", "18p C0G 5% codec crystal load", 620, 251.46,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("CODEC_XTO", "local"), "2": ("GND", "local")},
    )

    for ref, value, net, x, y, footprint in [
        ("C422", "1u PCM2900 VBUS after 2.2R", "CODEC_VBUS", 20, 274.32, FOOTPRINTS["C_1u"]),
        ("C423", "10u PCM2900 VCCCI", "CODEC_VCCCI", 130, 274.32, FOOTPRINTS["C_10u"]),
        ("C424", "1u PCM2900 VCCP1I less than 2u", "CODEC_VCCP1I", 20, 287.02, FOOTPRINTS["C_1u"]),
        ("C425", "1u PCM2900 VCCP2I less than 2u", "CODEC_VCCP2I", 130, 287.02, FOOTPRINTS["C_1u"]),
        ("C426", "1u PCM2900 VCCXI less than 2u", "CODEC_VCCXI", 20, 299.72, FOOTPRINTS["C_1u"]),
        ("C427", "1u PCM2900 VDDI less than 2u", "CODEC_VDDI", 130, 299.72, FOOTPRINTS["C_1u"]),
        ("C429", "10u PCM2900 VCOM", "CODEC_VCOM", 250, 299.72, FOOTPRINTS["C_10u"]),
    ]:
        s.place(
            ref, "C", value, x, y, footprint=footprint,
            pin_nets={"1": (net, "local"), "2": ("GND", "local")},
        )

    s.text(390, 276.86, "== Pop-safe amplifier enable: PCM2900 operational AND EC permission ==")
    s.place(
        "U421", "74LVC1G08", "SN74LVC1G08DBVR SSPND AND EC audio enable",
        540, 292.1, footprint=SINGLE_AND_FOOTPRINT,
        pin_nets={
            "1": ("DAC_SSPND", "local"),
            "2": ("AUDIO_AMP_EC_EN", "hier"),
            "3": ("GND", "local"),
            "4": ("AMP_ENABLE", "local"),
            "5": ("SYS_3V3", "hier"),
        },
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "SN74LVC1G08DBVR",
            "Logic": "AMP_ENABLE = DAC_SSPND(active high operational) AND AUDIO_AMP_EC_EN",
        },
    )
    s.place(
        "R415", "R", "100k EC enable fail-safe pull-down", 660, 281.94,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("AUDIO_AMP_EC_EN", "hier"), "2": ("GND", "local")},
    )
    s.place(
        "R416", "R", "100k SSPND fail-safe pull-down", 660, 294.64,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("DAC_SSPND", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C428", "C", "100n AND-gate local", 660, 307.34,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")},
    )

    s.text(20, 332.74, "== U420 TPA2012D2RTJR, 12dB gain, TI single-ended input and EMI networks ==")
    s.place(
        "U420", "TPA2012D2", "TPA2012D2RTJR stereo BTL class-D amplifier",
        390, 393.7, footprint=TPA2012D2_FOOTPRINT,
        pin_nets=tpa2012d2_nets(),
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "TPA2012D2RTJR",
            "Gain": "12dB (G1=0, G0=1)",
            "SpeakerContract": "8 ohm nominal, >=2W continuous module per channel",
        },
    )

    for channel, source, plus_net, minus_net, x, y in [
        ("L", "DAC_VOUT_L", "AMP_IN_LP", "AMP_IN_LN", 20, 360.68),
        ("R", "DAC_VOUT_R", "AMP_IN_RP", "AMP_IN_RN", 20, 408.94),
    ]:
        suffix = "20" if channel == "L" else "21"
        s.place(
            f"R4{suffix}", "R", f"100R {channel} DAC out-of-band filter", x, y,
            footprint=FOOTPRINTS["R"],
            pin_nets={"1": (source, "local"), "2": (f"DAC_{channel}_LPF", "local")},
        )
        s.place(
            f"C4{int(suffix) + 10}", "C", f"47n {channel} DAC out-of-band shunt", x + 110, y,
            footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": (f"DAC_{channel}_LPF", "local"), "2": ("GND", "local")},
        )
        s.place(
            f"C4{int(suffix) + 12}", "C", f"1u {channel} positive-input AC coupling", x + 220, y,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": (f"DAC_{channel}_LPF", "local"), "2": (plus_net, "local")},
        )
        s.place(
            f"C4{int(suffix) + 14}", "C", f"1u {channel} negative-input AC reference", x + 220, y + 12.7,
            footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": (minus_net, "local"), "2": ("GND", "local")},
        )

    s.place(
        "C440", "C", "100n amplifier supply at AVDD/PVDD", 520, 355.6,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("AUDIO_5V", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C441", "C", "10u amplifier local bulk", 650, 355.6,
        footprint=FOOTPRINTS["C_10u"],
        pin_nets={"1": ("AUDIO_5V", "local"), "2": ("GND", "local")},
    )

    for ref, source, filtered, y in [
        ("L420", "AMP_OUT_LP", "SPK_L_P", 381.0),
        ("L421", "AMP_OUT_LN", "SPK_L_N", 393.7),
        ("L422", "AMP_OUT_RP", "SPK_R_P", 406.4),
        ("L423", "AMP_OUT_RN", "SPK_R_N", 419.1),
    ]:
        s.place(
            ref, "L", "MPZ1608S221A 220R@100MHz speaker EMI bead", 540, y,
            footprint=FERRITE_FOOTPRINT,
            pin_nets={"1": (source, "local"), "2": (filtered, "local")},
            extra_props={"Manufacturer": "TDK", "MPN": "MPZ1608S221A"},
        )
    for ref, net, y in [
        ("C442", "SPK_L_P", 381.0),
        ("C443", "SPK_L_N", 393.7),
        ("C444", "SPK_R_P", 406.4),
        ("C445", "SPK_R_N", 419.1),
    ]:
        s.place(
            ref, "C", "1n speaker EMI shunt per TI Figure 36", 650, y,
            footprint=FOOTPRINTS["C_1n"],
            pin_nets={"1": (net, "local"), "2": ("GND", "local")},
        )

    s.place(
        "J420", "Conn_01x02", "Left 8-ohm BTL speaker; pin 1 +, pin 2 -",
        540, 444.5, footprint=SPEAKER_FOOTPRINT,
        pin_nets={"1": ("SPK_L_P", "local"), "2": ("SPK_L_N", "local")},
        extra_props={
            "Manufacturer": "JST", "MPN": "SM02B-GHS-TB",
            "MatingHousing": "GHR-02V-S", "Contacts": "SSHL-002T-P0.2",
            "EndpointAssembly": "Owner-supplied 38x18mm 8-ohm speaker module",
            "Warning": "BTL OUTPUT: NEITHER PIN IS GROUND",
        },
    )
    s.place(
        "J421", "Conn_01x02", "Right 8-ohm BTL speaker; pin 1 +, pin 2 -",
        650, 444.5, footprint=SPEAKER_FOOTPRINT,
        pin_nets={"1": ("SPK_R_P", "local"), "2": ("SPK_R_N", "local")},
        extra_props={
            "Manufacturer": "JST", "MPN": "SM02B-GHS-TB",
            "MatingHousing": "GHR-02V-S", "Contacts": "SSHL-002T-P0.2",
            "EndpointAssembly": "Owner-supplied 38x18mm 8-ohm speaker module",
            "Warning": "BTL OUTPUT: NEITHER PIN IS GROUND",
        },
    )

    s.text(20, 538.48, "== Built-in mono microphone: IM68A130 + low-noise 2.8V rail + low-noise preamp ==")
    s.place(
        "U430", "LP5907MFX-2.8", "LP5907MFX-2.8/NOPB low-noise microphone LDO",
        90, 574.04, footprint=FOOTPRINTS["LP5907MFX-2.8"],
        pin_nets={
            "1": ("SYS_3V3", "hier"),
            "2": ("GND", "local"),
            "3": ("AUDIO_MIC_EN", "hier"),
            "4": ("", "nc"),
            "5": ("MIC_2V8", "local"),
        },
        extra_props={
            "Manufacturer": "Texas Instruments",
            "MPN": "LP5907MFX-2.8/NOPB",
            "Function": "Keep IM68A130 below its 3.3V operating maximum with a quiet rail",
        },
    )
    s.place(
        "C448", "C", "1u LP5907 input", 20, 558.8,
        footprint=FOOTPRINTS["C_1u"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")},
    )
    s.place(
        "C449", "C", "1u LP5907 output", 20, 571.5,
        footprint=FOOTPRINTS["C_1u"],
        pin_nets={"1": ("MIC_2V8", "local"), "2": ("GND", "local")},
    )
    s.place(
        "R434", "R", "100k microphone enable fail-off pull-down", 20, 584.2,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("AUDIO_MIC_EN", "hier"), "2": ("GND", "local")},
    )
    s.place(
        "R435", "R", "2.2k microphone-active indicator", 130, 584.2,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("MIC_2V8", "local"), "2": ("MIC_LED_A", "local")},
    )
    s.place(
        "LED430", "LED", "green microphone-active indicator", 240, 584.2,
        footprint=FOOTPRINTS["LED"],
        pin_nets={"1": ("GND", "local"), "2": ("MIC_LED_A", "local")},
        extra_props={
            "Manufacturer": "Kingbright", "MPN": "APT1608SGC",
            "Datasheet": "https://www.kingbrightusa.com/images/catalog/SPEC/APT1608SGC.pdf",
            "Function": "Indicator is supplied by the actual microphone rail, not only its enable command",
        },
    )
    s.place(
        "MK430", "IM68A130V01", "IM68A130V01 bottom-port analog MEMS microphone",
        220, 574.04, footprint=FOOTPRINTS["IM68A130V01"],
        pin_nets={
            "1": ("MIC_RAW", "local"),
            "2": ("GND", "local"),
            "3": ("MIC_2V8", "local"),
            "4": ("GND", "local"),
        },
        extra_props={
            "Manufacturer": "Infineon Technologies",
            "MPN": "IM68A130V01XTMA1",
            "AcousticPort": "0.6mm NPTH through PCB; keep paste/copper/debris out of port",
        },
    )
    s.place(
        "C450", "C", "100n microphone VDD at pin 3", 310, 558.8,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("MIC_2V8", "local"), "2": ("GND", "local")},
    )

    s.text(20, 607.06, "U431 has DC gain 1 and audio-band gain 5.99V/V; the microphone's 1.3V output bias sets the quiescent output.")
    s.place(
        "U431", "TLV9061xDBV", "TLV9061IDBVR microphone preamplifier", 440, 631.19,
        footprint=FOOTPRINTS["TLV9061xDBV"],
        pin_nets={
            "1": ("MIC_PREAMP", "local"),
            "2": ("GND", "local"),
            "3": ("MIC_RAW", "local"),
            "4": ("MIC_FB", "local"),
            "5": ("SYS_3V3", "hier"),
        },
        extra_props={"Manufacturer": "Texas Instruments", "MPN": "TLV9061IDBVR"},
    )
    s.place(
        "C452", "C", "100n TLV9061 local bypass", 670, 624.84,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("SYS_3V3", "hier"), "2": ("GND", "local")},
    )
    s.place(
        "R432", "R", "4.99k 1% microphone feedback", 330, 660.4,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("MIC_PREAMP", "local"), "2": ("MIC_FB", "local")},
    )
    s.place(
        "C453", "C", "1.2n C0G feedback low-pass", 440, 660.4,
        footprint=FOOTPRINTS["C_100n"],
        pin_nets={"1": ("MIC_PREAMP", "local"), "2": ("MIC_FB", "local")},
    )
    s.place(
        "R433", "R", "1.00k 1% microphone gain leg", 330, 673.1,
        footprint=FOOTPRINTS["R"],
        pin_nets={"1": ("MIC_FB", "local"), "2": ("MIC_HP_NODE", "local")},
    )
    s.place(
        "C454", "C", "4.7u microphone gain-leg AC coupling", 440, 673.1,
        footprint=FOOTPRINTS["C_10u"],
        pin_nets={"1": ("MIC_HP_NODE", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C455", "C", "4.7u microphone to PCM2900 VINL per TI analog front-end", 570, 660.4,
        footprint=FOOTPRINTS["C_10u"],
        pin_nets={"1": ("MIC_PREAMP", "local"), "2": ("MIC_ADC_L", "local")},
    )
    s.place(
        "C456", "C", "4.7u microphone to PCM2900 VINR per TI analog front-end", 570, 673.1,
        footprint=FOOTPRINTS["C_10u"],
        pin_nets={"1": ("MIC_PREAMP", "local"), "2": ("MIC_ADC_R", "local")},
    )
    s.text(20, 698.5, "MIC PERFORMANCE: DC gain 1, audio-band gain 5.99V/V; shelving pole about 34Hz; feedback pole about 27kHz.")
    s.text(20, 702.31, "MIC TARGET: voice/conference capture up to about 105dBSPL. Expected analog clipping near 112-113dBSPL; this assembly is not a high-SPL recorder.")
    s.text(20, 706.12, "MIC LAYOUT: microphone and preamp are chip-down on the main PCB. Place at a front/top acoustic opening, far from blower, class-D outputs, RF PAs, and switching inductors.")
    s.text(20, 713.74, "MIC RELEASE GATE: verify footprint/stencil with assembler, seal the acoustic path, and test clipping/noise/echo with fans, radios, speakers, USB, and charging active.")

    s.text(20, 736.6, "RELEASE GATES:")
    s.text(20, 744.22, "1. Initial speakers: 8 ohm nominal and >=2W continuous each. Never join either BTL output to GND or use a shared speaker return.")
    s.text(20, 751.84, "2. A 4-ohm speaker is allowed only after amplifier/PCB thermal test, excursion test, current-budget check, and enforced host volume limiting.")
    s.text(20, 759.46, "3. Measure both crystal frequencies/startup margin, USB2 90-ohm routing, reset timing, and P5 enumeration on the production Mu BIOS.")
    s.text(20, 767.08, "4. Confirm the OS enumerates distinct PCM2900C system audio and PCM2902C radio audio devices across cold boot and suspend/resume.")
    s.text(20, 774.7, "5. Verify fail-off AUDIO_MIC_EN and the actual MIC_2V8-rail indicator; then run pop, echo, privacy, fan/charger noise, excursion, and RF-desense tests.")
    s.text(20, 782.32, "LAYOUT: place hub bypass/RBIAS/crystal at U400; codec crystal/decoupling at U410; mic chain at MK430; keep BTL pairs away from RF and mic input.")
    s.text(20, 789.94, "HUB_VBUS_DET follows the supervised carrier-generated physical INTERNAL_USB_VBUS. The audio hub cannot wake S3 and must re-enumerate after resume.")

    return s
