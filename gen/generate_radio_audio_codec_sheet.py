from build_ducktop2 import Sheet, FOOTPRINTS


def pcm2902c_nets():
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
        "12": ("CODEC_LINEIN_L", "local"),
        "13": ("CODEC_LINEIN_R", "local"),
        "14": ("CODEC_VCOM", "local"),
        "15": ("CODEC_TX_UHF", "local"),
        "16": ("CODEC_TX_VHF", "local"),
        "17": ("CODEC_VCCP1I", "local"),
        "18": ("GND", "local"),
        "19": ("CODEC_VCCP2I", "local"),
        "20": ("CODEC_XTO", "local"),
        "21": ("CODEC_XTI", "local"),
        "22": ("GND", "local"),
        "23": ("CODEC_VCCXI", "local"),
        "24": ("", "nc"),
        "25": ("", "nc"),
        "26": ("GND", "local"),
        "27": ("CODEC_VDDI", "local"),
        "28": ("CODEC_SSPND", "local"),
    }


def build(sheet_symbol_uuid, logic_3v3="MCU_3V3"):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 340
    s.refcounters["#FLG"] = 340

    s.text(20, 12.7, "== USB radio audio codec for DRA818 APRS/voice ==")
    s.text(20, 20.32, "PCM2902CDBR is downstream port 1 of the internal system-audio hub on Mu USB2_P5.")
    s.text(20, 27.94, "VHF/UHF use independent stereo ADC/DAC channels; each TX path is attenuated and fail-muted by its PTT_N signal.")

    s.text(20, 50.8, "== U330 PCM2902CDBR USB audio codec; TI Figure 39 core network ==")
    s.place("U330", "PCM2902", "PCM2902CDBR USB audio codec", 190, 145,
            footprint=FOOTPRINTS["PCM2902"], pin_nets=pcm2902c_nets(),
            extra_props={
                "Manufacturer": "Texas Instruments",
                "MPN": "PCM2902CDBR",
                "ReferenceCircuit": "PCM2902C Figure 39 bus-powered configuration",
            })
    s.place("R330", "R", "22R USB DP series", 20, 90, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_CODEC_USB_DP", "hier"), "2": ("CODEC_USB_DP", "local")})
    s.place("R331", "R", "22R USB DM series", 20, 102.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_CODEC_USB_DM", "hier"), "2": ("CODEC_USB_DM", "local")})
    s.place("R337", "R", "2.2R PCM2902C VBUS filter", 20, 125.73, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_CODEC_USB_VBUS", "hier"), "2": ("CODEC_VBUS", "local")})
    s.pwrflag(20, 132.08, "CODEC_VBUS")
    s.place("C330", "C", "1u PCM2902C VBUS", 20, 138.43, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("CODEC_VBUS", "local"), "2": ("GND", "local")})
    s.place("R338", "R", "1.5k USB D+ pull-up per TI Figure 39", 20, 151.13, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CODEC_VDDI", "local"), "2": ("CODEC_USB_DP", "local")})
    for ref, value, net, y, footprint in [
        ("C331", "10u VCCCI", "CODEC_VCCCI", 76.2, FOOTPRINTS["C_10u"]),
        ("C332", "1u VCCP1I (<2u)", "CODEC_VCCP1I", 88.9, FOOTPRINTS["C_1u"]),
        ("C333", "1u VCCP2I (<2u)", "CODEC_VCCP2I", 101.6, FOOTPRINTS["C_1u"]),
        ("C334", "1u VCCXI (<2u)", "CODEC_VCCXI", 114.3, FOOTPRINTS["C_1u"]),
        ("C335", "1u VDDI (<2u)", "CODEC_VDDI", 127, FOOTPRINTS["C_1u"]),
    ]:
        s.place(ref, "C", value, 330, y, footprint=footprint,
                pin_nets={"1": (net, "local"), "2": ("GND", "local")})
    s.place("C337", "C", "10u VCOM", 330, 149.86, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("CODEC_VCOM", "local"), "2": ("GND", "local")})
    s.place("Y330", "Crystal_GND24", "ABM8G-106-12.000MHZ-T 12MHz 10pF CL", 330, 180.34, footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={
                "1": ("CODEC_XTI", "local"),
                "2": ("GND", "local"),
                "3": ("CODEC_XTO", "local"),
                "4": ("GND", "local"),
            }, extra_props={
                "Manufacturer": "Abracon",
                "MPN": "ABM8G-106-12.000MHZ-T",
                "LoadCalculation": "18pF each leg gives about 10pF with approximately 1pF pin/PCB stray",
            })
    s.place("R340", "R", "1M crystal feedback", 390, 180.34, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CODEC_XTI", "local"), "2": ("CODEC_XTO", "local")})
    s.place("C338", "C", "18p C0G 5% PCM2902 crystal load", 330, 200.66, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("CODEC_XTI", "local"), "2": ("GND", "local")})
    s.place("C339", "C", "18p C0G 5% PCM2902 crystal load", 330, 213.36, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("CODEC_XTO", "local"), "2": ("GND", "local")})

    s.text(20, 250.19, "== Radio receive audio into codec line inputs ==")
    s.place("C340", "C", "1u VHF RX AC couple", 20, 275.59, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("RADIO_VHF_AUDIO_OUT", "hier"), "2": ("CODEC_LINEIN_L", "local")})
    s.place("C341", "C", "1u UHF RX AC couple", 20, 288.29, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("RADIO_UHF_AUDIO_OUT", "hier"), "2": ("CODEC_LINEIN_R", "local")})
    s.text(150, 275.59, "No codec-side bleed: PCM2902 biases VINL/VINR internally to VCOM through 30k.")

    s.text(390, 250.19, "== Codec transmit audio to radio mic inputs ==")
    s.place("C342", "C", "1u VHF TX audio AC couple", 390, 266.7, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("CODEC_TX_VHF", "local"), "2": ("VHF_TX_AUDIO", "local")})
    s.place("C343", "C", "1u UHF TX audio AC couple", 390, 279.4, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("CODEC_TX_UHF", "local"), "2": ("UHF_TX_AUDIO", "local")})
    s.place("R334", "R", "82k 1% VHF mic attenuator series", 520, 260.35, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VHF_TX_AUDIO", "local"), "2": ("RADIO_VHF_MIC_IN", "hier")},
            extra_props={"ReleaseGate": "CALIBRATE_DEVIATION_AND_LOCK_DRA818_MIC_INPUT_IMPEDANCE"})
    s.place("R335", "R", "82k 1% UHF mic attenuator series", 520, 273.05, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("UHF_TX_AUDIO", "local"), "2": ("RADIO_UHF_MIC_IN", "hier")},
            extra_props={"ReleaseGate": "CALIBRATE_DEVIATION_AND_LOCK_DRA818_MIC_INPUT_IMPEDANCE"})
    s.place("R336", "R", "1k 1% VHF mic attenuator shunt", 520, 285.75, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_VHF_MIC_IN", "hier"), "2": ("GND", "local")})
    s.place("R341", "R", "1k 1% UHF mic attenuator shunt", 520, 298.45, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_UHF_MIC_IN", "hier"), "2": ("GND", "local")})
    s.place("Q330", "Q_NMOS_SOT23_GSD", "2N7002KT1G VHF PTT/suspend fail-mute shunt", 650, 266.7,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={
                "1": ("VHF_MUTE_GATE", "local"),
                "2": ("GND", "local"),
                "3": ("RADIO_VHF_MIC_IN", "hier"),
            },
            extra_props={
                "Manufacturer": "onsemi",
                "MPN": "2N7002KT1G",
                "MuteLogic": "MUTE_GATE=PTT_N_OR_NOT_CODEC_SSPND",
            })
    s.place("Q331", "Q_NMOS_SOT23_GSD", "2N7002KT1G UHF PTT/suspend fail-mute shunt", 650, 292.1,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={
                "1": ("UHF_MUTE_GATE", "local"),
                "2": ("GND", "local"),
                "3": ("RADIO_UHF_MIC_IN", "hier"),
            },
            extra_props={
                "Manufacturer": "onsemi",
                "MPN": "2N7002KT1G",
                "MuteLogic": "MUTE_GATE=PTT_N_OR_NOT_CODEC_SSPND",
            })
    # PCM2902C SSPND is high while operational and low during USB suspend.
    # R342 also forces the gate low if the codec loses power, turning Q332 on.
    # The Schottky diode OR gates keep the two independent PTT_N nets isolated.
    s.place("Q332", "Q_PMOS_GSD", "BSS84LT1G codec-loss force-mute", 650, 317.5,
            footprint=FOOTPRINTS["Q_NMOS"],
            pin_nets={
                "1": ("CODEC_SSPND", "local"), "2": (logic_3v3, "hier"),
                "3": ("CODEC_FORCE_MUTE", "local"),
            }, extra_props={"Manufacturer": "onsemi", "MPN": "BSS84LT1G"})
    s.place("R342", "R", "100k SSPND fail-low pull-down", 700, 305, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CODEC_SSPND", "local"), "2": ("GND", "local")})
    s.place("R343", "R", "100k force-mute pull-down", 700, 317.5, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CODEC_FORCE_MUTE", "local"), "2": ("GND", "local")})
    for ref, source, gate, y in (
        ("D390", "RADIO_VHF_PTT_N", "VHF_MUTE_GATE", 330.2),
        ("D391", "CODEC_FORCE_MUTE", "VHF_MUTE_GATE", 342.9),
        ("D392", "RADIO_UHF_PTT_N", "UHF_MUTE_GATE", 355.6),
        ("D393", "CODEC_FORCE_MUTE", "UHF_MUTE_GATE", 368.3),
    ):
        s.place(ref, "D_Schottky", "BAT54WS PTT/suspend mute OR", 650, y,
                footprint=FOOTPRINTS["D_Signal"],
                pin_nets={"1": (gate, "local"), "2": (source, "hier" if source.startswith("RADIO_") else "local")},
                extra_props={"Manufacturer": "Diodes Incorporated", "MPN": "BAT54WS-7-F"})
    s.place("R344", "R", "100k VHF mute-gate pull-down", 745, 330.2, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("VHF_MUTE_GATE", "local"), "2": ("GND", "local")})
    s.place("R345", "R", "100k UHF mute-gate pull-down", 745, 342.9, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("UHF_MUTE_GATE", "local"), "2": ("GND", "local")})
    s.place("J330", "Conn_01x08", "DNP radio audio codec probe", 520, 330.2,
            footprint=FOOTPRINTS["Conn_01x08"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("RADIO_VHF_AUDIO_OUT", "hier"),
                "3": ("RADIO_UHF_AUDIO_OUT", "hier"),
                "4": ("VHF_TX_AUDIO", "local"),
                "5": ("UHF_TX_AUDIO", "local"),
                "6": ("RADIO_VHF_MIC_IN", "hier"),
                "7": ("RADIO_UHF_MIC_IN", "hier"),
                "8": ("GND", "local"),
            }, on_board=False)

    s.gnd(625, 380)
    s.text(20, 360.68, "NOTES:")
    s.text(20, 368.3, "TI Figure 39 core is implemented: SEL0/SEL1 direct-high, 1.5k D+ pull-up, filtered VBUS, and separate rail capacitors.")
    s.text(20, 375.92, "Independent 82k/1k dividers produce about 8.4mVrms open-circuit; Q330/Q331 mute on PTT_N high, USB suspend, or codec power loss.")
    s.text(20, 383.54, "RELEASE GATE: measure MIC impedance and deviation per band; preserve mainboard PTT defaults and hard-interlock both PTT_N signals.")

    return s
