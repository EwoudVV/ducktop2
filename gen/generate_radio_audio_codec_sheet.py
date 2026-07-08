from build_ducktop2 import Sheet, FOOTPRINTS


def pcm2902_nets():
    return {
        "1": ("CODEC_USB_DP", "local"),
        "2": ("CODEC_USB_DM", "local"),
        "3": ("SYS_5V", "hier"),
        "4": ("GND", "local"),
        "5": ("GND", "local"),
        "6": ("GND", "local"),
        "7": ("GND", "local"),
        "8": ("GND", "local"),
        "9": ("GND", "local"),
        "10": ("CODEC_3V3", "local"),
        "11": ("GND", "local"),
        "12": ("CODEC_LINEIN_L", "local"),
        "13": ("CODEC_LINEIN_R", "local"),
        "14": ("CODEC_VCOM", "local"),
        "15": ("", "nc"),
        "16": ("CODEC_TX_L", "local"),
        "17": ("CODEC_3V3", "local"),
        "18": ("GND", "local"),
        "19": ("CODEC_3V3", "local"),
        "20": ("CODEC_XTO", "local"),
        "21": ("CODEC_XTI", "local"),
        "22": ("GND", "local"),
        "23": ("CODEC_3V3", "local"),
        "24": ("", "nc"),
        "25": ("", "nc"),
        "26": ("GND", "local"),
        "27": ("CODEC_3V3", "local"),
        "28": ("", "nc"),
    }


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 340
    s.refcounters["#FLG"] = 340

    s.text(20, 12.7, "== USB radio audio codec for DRA818 APRS/voice ==")
    s.text(20, 20.32, "PCM2902 appears to the host as a USB audio device on Mu USB2_P5.")
    s.text(20, 27.94, "VHF/UHF receive feed stereo inputs; left DAC output feeds both radio mic inputs through isolation resistors.")

    s.text(20, 50.8, "== U330 PCM2902 USB audio codec ==")
    s.place("U330", "PCM2902", "PCM2902 USB audio codec", 190, 145,
            footprint=FOOTPRINTS["PCM2902"], pin_nets=pcm2902_nets())
    s.place("R330", "R", "22R USB DP series", 20, 90, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUDIO_USB_DP", "hier"), "2": ("CODEC_USB_DP", "local")})
    s.place("R331", "R", "22R USB DM series", 20, 102.7, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("AUDIO_USB_DM", "hier"), "2": ("CODEC_USB_DM", "local")})
    s.place("C330", "C", "10u codec VBUS", 20, 125.73, footprint=FOOTPRINTS["C_10u"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    s.place("C331", "C", "100n codec VBUS", 20, 138.43, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("SYS_5V", "hier"), "2": ("GND", "local")})
    for i, y in enumerate([76.2, 88.9, 101.6, 114.3]):
        s.place(f"C{332+i}", "C", "100n codec 3V3", 330, y, footprint=FOOTPRINTS["C_100n"],
                pin_nets={"1": ("CODEC_3V3", "local"), "2": ("GND", "local")})
    s.place("C336", "C", "4.7u codec 3V3 bulk", 330, 127, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("CODEC_3V3", "local"), "2": ("GND", "local")})
    s.place("C337", "C", "1u VCOM", 330, 149.86, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("CODEC_VCOM", "local"), "2": ("GND", "local")})
    s.place("Y330", "Crystal_GND24", "12MHz PCM2902", 330, 180.34, footprint=FOOTPRINTS["Crystal_HSE"],
            pin_nets={"1": ("CODEC_XTI", "local"), "2": ("GND", "local"), "3": ("CODEC_XTO", "local")})
    s.place("C338", "C", "18p", 330, 200.66, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("CODEC_XTI", "local"), "2": ("GND", "local")})
    s.place("C339", "C", "18p", 330, 213.36, footprint=FOOTPRINTS["C_100n"],
            pin_nets={"1": ("CODEC_XTO", "local"), "2": ("GND", "local")})

    s.text(20, 250.19, "== Radio receive audio into codec line inputs ==")
    s.place("C340", "C", "1u VHF RX AC couple", 20, 275.59, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("RADIO_VHF_AUDIO_OUT", "hier"), "2": ("CODEC_LINEIN_L", "local")})
    s.place("C341", "C", "1u UHF RX AC couple", 20, 288.29, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("RADIO_UHF_AUDIO_OUT", "hier"), "2": ("CODEC_LINEIN_R", "local")})
    s.place("R332", "R", "100k line-in L bleed", 150, 275.59, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CODEC_LINEIN_L", "local"), "2": ("GND", "local")})
    s.place("R333", "R", "100k line-in R bleed", 150, 288.29, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("CODEC_LINEIN_R", "local"), "2": ("GND", "local")})

    s.text(390, 250.19, "== Codec transmit audio to radio mic inputs ==")
    s.place("C342", "C", "1u TX audio AC couple", 390, 275.59, footprint=FOOTPRINTS["C_1u"],
            pin_nets={"1": ("CODEC_TX_L", "local"), "2": ("RADIO_TX_AUDIO", "local")})
    s.place("R334", "R", "10k VHF mic feed", 520, 260.35, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_TX_AUDIO", "local"), "2": ("RADIO_VHF_MIC_IN", "hier")})
    s.place("R335", "R", "10k UHF mic feed", 520, 273.05, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_TX_AUDIO", "local"), "2": ("RADIO_UHF_MIC_IN", "hier")})
    s.place("R336", "R", "100k TX audio bleed", 390, 298.45, footprint=FOOTPRINTS["R"],
            pin_nets={"1": ("RADIO_TX_AUDIO", "local"), "2": ("GND", "local")})
    s.place("J330", "Conn_01x08", "DNP radio audio codec probe", 520, 330.2,
            footprint=FOOTPRINTS["Conn_01x08"],
            pin_nets={
                "1": ("GND", "local"),
                "2": ("RADIO_VHF_AUDIO_OUT", "hier"),
                "3": ("RADIO_UHF_AUDIO_OUT", "hier"),
                "4": ("RADIO_TX_AUDIO", "local"),
                "5": ("RADIO_VHF_MIC_IN", "hier"),
                "6": ("RADIO_UHF_MIC_IN", "hier"),
                "7": ("SYS_5V", "hier"),
                "8": ("GND", "local"),
            })

    s.gnd(625, 380)
    s.text(20, 360.68, "NOTES:")
    s.text(20, 368.3, "Host software handles APRS/audio decoding through USB audio; EC GPIO still owns PTT, PD, SQL, and antenna select.")
    s.text(20, 375.92, "Only assert one PTT at a time; both radio mic inputs receive the same isolated DAC audio through large resistors.")
    s.text(20, 383.54, "Final DRA818 audio gain/attenuation values require bench measurements; current values are safe first-pass starts.")

    return s
