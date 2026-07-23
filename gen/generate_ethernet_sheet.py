from build_ducktop2 import Sheet, FOOTPRINTS


def build(sheet_symbol_uuid):
    s = Sheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 500
    s.refcounters["#FLG"] = 500

    s.text(20, 12.7, "== Native PCIe Gigabit Ethernet on LattePanda Mu default HSIO6 ==")
    s.text(20, 20.32, "RTL8111H support circuit follows LattePanda's DFR1142 Mu carrier reference: HSIO6, REFCLK4, CLKREQ4, and PLT_RST.")
    s.text(20, 27.94, "JXD1-1022NL is a true recessed through-hole mid-mount RJ45 with integrated magnetics; no external transformer is required.")

    rtl_nets = {
        "1": ("ETH_MDI0_P", "local"),
        "2": ("ETH_MDI0_N", "local"),
        "3": ("ETH_1V0", "local"),
        "4": ("ETH_MDI1_P", "local"),
        "5": ("ETH_MDI1_N", "local"),
        "6": ("ETH_MDI2_P", "local"),
        "7": ("ETH_MDI2_N", "local"),
        "8": ("ETH_1V0", "local"),
        "9": ("ETH_MDI3_P", "local"),
        "10": ("ETH_MDI3_N", "local"),
        "11": ("PCIE_3V3", "hier"),
        "12": ("GBE_CLKREQ_N", "hier"),
        "13": ("GBE_HSI_P", "local"),
        "14": ("GBE_HSI_N", "local"),
        "15": ("GBE_REFCLK_P", "hier"),
        "16": ("GBE_REFCLK_N", "hier"),
        "17": ("GBE_HSO_P", "local"),
        "18": ("GBE_HSO_N", "local"),
        "19": ("PLTRST_SRC_N", "hier"),
        "20": ("GBE_ISOLATE_N", "local"),
        "21": ("PCIE_WAKE_N", "hier"),
        "22": ("ETH_1V0", "local"),
        "23": ("PCIE_3V3", "hier"),
        "24": ("ETH_1V0", "local"),
        "25": ("ETH_LED_ACT_N", "local"),
        "26": ("ETH_LED_1000_N", "local"),
        "27": ("", "nc"),
        "28": ("ETH_XI", "local"),
        "29": ("ETH_XO", "local"),
        "30": ("ETH_1V0", "local"),
        "31": ("ETH_RSET", "local"),
        "32": ("PCIE_3V3", "hier"),
        "33": ("GND", "local"),
    }
    s.place(
        "U500", "RTL8111H", "RTL8111H-CG-RH PCIe Gigabit Ethernet", 280, 160,
        footprint=FOOTPRINTS["RTL8111H"], pin_nets=rtl_nets,
        extra_props={
            "Manufacturer": "Realtek",
            "MPN": "RTL8111H-CG-RH",
            "ReferenceCircuit": "LattePanda Mu DFR1142 Gigabit Ethernet sheet",
            "HostInterface": "Default BIOS HSIO6 PCIe host lane with REFCLK4 and CLKREQ4; endpoint negotiates supported PCIe speed",
        },
    )

    s.text(20, 55.88, "== PCIe x1 host TX from Mu to RTL8111H; C500/C501 are at the Mu transmitter pads, not by U500 ==")
    for ref, source, sink, x, y in [
        ("C500", "GBE_HOST_TX_P", "GBE_HSI_P", 20, 76.2),
        ("C501", "GBE_HOST_TX_N", "GBE_HSI_N", 20, 88.9),
        ("C502", "GBE_HSO_P", "GBE_HOST_RX_P", 150, 76.2),
        ("C503", "GBE_HSO_N", "GBE_HOST_RX_N", 150, 88.9),
    ]:
        source_kind = "hier" if source.startswith("GBE_HOST") else "local"
        sink_kind = "hier" if sink.startswith("GBE_HOST") else "local"
        s.place(
            ref, "C", "220n 16V X7R PCIe TX AC per current Mu guide", x, y,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": (source, source_kind), "2": (sink, sink_kind)},
            extra_props={
                "Manufacturer": "Murata", "MPN": "GRM155R71C224KA12D",
                "DesignAuthority": "Current LattePanda Mu PCIe design guide; 220n in both directions",
            },
        )

    s.text(20, 116.84, "== RTL8111H 3.3V / internal 1.0V rails and reset-side straps ==")
    for ref, net, x, y in [
        ("C504", "PCIE_3V3", 20, 137.16),
        ("C505", "PCIE_3V3", 20, 149.86),
        ("C506", "PCIE_3V3", 20, 162.56),
        ("C507", "ETH_1V0", 130, 137.16),
        ("C508", "ETH_1V0", 130, 149.86),
        ("C509", "ETH_1V0", 130, 162.56),
        ("C510", "ETH_1V0", 130, 175.26),
        ("C511", "ETH_1V0", 130, 187.96),
    ]:
        s.place(
            ref, "C", "100n 16V X7R local decoupling", x, y,
            footprint=FOOTPRINTS["C_0402"],
            pin_nets={"1": (net, "hier" if net == "PCIE_3V3" else "local"), "2": ("GND", "local")},
        )
    s.place(
        "C512", "C", "10u 6.3V X7R RTL8111H REGOUT bulk", 130, 200.66,
        footprint=FOOTPRINTS["C_10u"],
        pin_nets={"1": ("ETH_1V0", "local"), "2": ("GND", "local")},
    )
    s.place(
        "R501", "R", "2.49k 1% RTL8111H RSET", 20, 187.96,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("ETH_RSET", "local"), "2": ("GND", "local")},
        extra_props={"Manufacturer": "Yageo", "MPN": "RC0402FR-072K49L"},
    )
    s.place(
        "R502", "R", "10k 1% ISOLATEB pull-up", 20, 200.66,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("GBE_ISOLATE_N", "local")},
    )
    s.place(
        "R503", "R", "10k 1% PCIe WAKE# pull-up", 20, 213.36,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("PCIE_WAKE_N", "hier")},
    )

    s.text(20, 243.84, "== 25MHz reference crystal; 12pF legs implement the qualified 8pF load including about 2pF stray ==")
    s.place(
        "Y500", "Crystal_GND24", "ECS-250-8-33-AGN-TR 25MHz 8pF crystal", 80, 271.78,
        footprint=FOOTPRINTS["Crystal_HSE"],
        pin_nets={"1": ("ETH_XI", "local"), "2": ("GND", "local"), "3": ("ETH_XO", "local"), "4": ("GND", "local")},
        extra_props={
            "Manufacturer": "ECS Inc.",
            "MPN": "ECS-250-8-33-AGN-TR",
            "Specification": "25MHz fundamental, 8pF CL, 40R max ESR, -40C to +85C",
            "LoadCalculation": "12pF each leg with about 2pF pin/PCB stray gives 8pF effective load",
        },
    )
    s.place(
        "R500", "R", "1M 1% crystal feedback", 150, 271.78,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("ETH_XI", "local"), "2": ("ETH_XO", "local")},
    )
    s.place(
        "C515", "C", "12p C0G 5% crystal load", 20, 266.7,
        footprint=FOOTPRINTS["C_0402"],
        pin_nets={"1": ("ETH_XI", "local"), "2": ("GND", "local")},
    )
    s.place(
        "C516", "C", "12p C0G 5% crystal load", 20, 279.4,
        footprint=FOOTPRINTS["C_0402"],
        pin_nets={"1": ("ETH_XO", "local"), "2": ("GND", "local")},
    )

    s.text(390, 55.88, "== Four 100-ohm MDI pairs, low-capacitance ESD, and integrated-magnetics RJ45 ==")
    for ref, nets, y in [
        ("U501", ["ETH_MDI0_P", "ETH_MDI0_N", "ETH_MDI1_P", "ETH_MDI1_N"], 105),
        ("U502", ["ETH_MDI2_P", "ETH_MDI2_N", "ETH_MDI3_P", "ETH_MDI3_N"], 185),
    ]:
        s.place(
            ref, "D3V3XA4B10LP", "D3V3XA4B10LP-7 four-channel 0.3pF Ethernet ESD", 455, y,
            footprint=FOOTPRINTS["D3V3XA4B10LP"],
            pin_nets={
                "1": (nets[0], "local"), "2": (nets[1], "local"),
                "3": ("GND", "local"), "4": (nets[2], "local"),
                "5": (nets[3], "local"), "6": ("", "nc"), "7": ("", "nc"),
                "8": ("GND", "local"), "9": ("", "nc"), "10": ("", "nc"),
            },
            extra_props={"Manufacturer": "Diodes Incorporated", "MPN": "D3V3XA4B10LP-7"},
        )

    jack_nets = {
        "1": ("ETH_MDI0_P", "local"), "2": ("ETH_MDI0_N", "local"), "3": ("ETH_CT", "local"),
        "4": ("ETH_MDI1_P", "local"), "5": ("ETH_MDI1_N", "local"), "6": ("ETH_CT", "local"),
        "7": ("ETH_MDI2_P", "local"), "8": ("ETH_MDI2_N", "local"), "9": ("ETH_CT", "local"),
        "10": ("ETH_MDI3_P", "local"), "11": ("ETH_MDI3_N", "local"), "12": ("ETH_CT", "local"),
        "13": ("ETH_LED_ACT_N", "local"), "14": ("ETH_LED_ACT_A", "local"),
        "15": ("ETH_LED_1000_N", "local"), "16": ("ETH_LED_1000_A", "local"),
        "SH": ("ETH_CHASSIS", "local"),
    }
    s.place(
        "J500", "JXD1-1022NL", "JXD1-1022NL recessed 1GbE RJ45", 635, 150,
        footprint=FOOTPRINTS["JXD1-1022NL"], pin_nets=jack_nets,
        extra_props={
            "Manufacturer": "Pulse Electronics / Yageo",
            "MPN": "JXD1-1022NL",
            "MechanicalDrawing": "Yageo J513.C page 2",
            "AssemblyGate": "CONFIRM_THR_MIDMOUNT_SUPPORT_AND_SAMPLE_LED_LANDS",
        },
    )
    s.place(
        "C513", "C", "100n 16V X7R magnetics center-tap bypass", 520, 243.84,
        footprint=FOOTPRINTS["C_0402"],
        pin_nets={"1": ("ETH_CT", "local"), "2": ("GND", "local")},
    )
    s.place(
        "R504", "R", "470R 1% yellow activity LED", 570, 256.54,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("ETH_LED_ACT_A", "local")},
    )
    s.place(
        "R505", "R", "470R 1% green 1000M indicator LED", 570, 269.24,
        footprint=FOOTPRINTS["R_0402"],
        pin_nets={"1": ("PCIE_3V3", "hier"), "2": ("ETH_LED_1000_A", "local")},
    )

    s.text(390, 302.26, "== Connector shield / aluminum chassis interface ==")
    s.place(
        "C514", "C", "1n 2kV X7R 10% shield-to-digital return", 390, 322.58,
        footprint=FOOTPRINTS["C_1812"],
        pin_nets={"1": ("ETH_CHASSIS", "local"), "2": ("GND", "local")},
        extra_props={
            "Manufacturer": "KEMET",
            "MPN": "C1812C102KGRACTU",
            "Specification": "1000pF 10% 2000VDC X7R 1812",
            "ReleaseGate": "VERIFY_CHASSIS_BONDING_AND_ESD_BEHAVIOR",
        },
    )
    s.place(
        "R506", "R", "DNP 0R direct shield-to-GND option", 520, 322.58,
        footprint=FOOTPRINTS["R_1206"],
        pin_nets={"1": ("ETH_CHASSIS", "local"), "2": ("GND", "local")},
        dnp=True,
    )

    s.text(20, 350.52, "LAYOUT: PCIe Gen3 pairs are 85-ohm differential; for this on-board PCIe device, place C500-C503 beside U500 per the Mu guide and route over an uninterrupted reference plane.")
    s.text(20, 358.14, "LAYOUT: MDI pairs are 100-ohm differential. Put U501/U502 immediately behind J500, avoid stubs, and do not route digital signals under the magnetics.")
    s.text(20, 365.76, "MECHANICAL: manufacturer body 17.58 x 26.06 x 11.30mm; PCB/panel plane is 2.03mm behind the front face; panel opening 17.98 x 9.69mm.")
    s.text(20, 373.38, "RELEASE HOLD: verify all four unnumbered shell stakes are common and confirm LED copper lands on one physical JXD1 sample before ordering the motherboard.")
    s.text(20, 381.0, "ASSEMBLY HOLD: ask the assembler to confirm through-hole mid-mount RJ45 support and whether J500 is manual/post-reflow insertion.")
    s.text(20, 388.62, "LED HOLD: RTL8111H pin 26 is the default 1000M indication, not a generic link LED. Verify both jack LEDs at 10/100/1000 on hardware.")

    return s
