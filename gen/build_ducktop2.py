import contextlib
import uuid, os
import genlib

GRID_MM = 1.27

UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "ducktop2/kicad/generated")
_uuid_stack = [{"context": "global", "counter": 0}]


@contextlib.contextmanager
def uuid_scope(context):
    _uuid_stack.append({"context": context, "counter": 0})
    try:
        yield
    finally:
        _uuid_stack.pop()


def stable_uuid(name):
    return str(uuid.uuid5(UUID_NAMESPACE, str(name)))


def reset_uuid_sequence(context="global"):
    _uuid_stack[-1] = {"context": context, "counter": 0}


def U(label=None):
    frame = _uuid_stack[-1]
    frame["counter"] += 1
    suffix = f":{label}" if label is not None else ""
    seed = f'{frame["context"]}:{frame["counter"]:06d}{suffix}'
    return stable_uuid(seed)


def snap_coord(value, grid=GRID_MM):
    return round(round(float(value) / grid) * grid, 4)


def fmt_coord(value):
    snapped = snap_coord(value)
    text = f"{snapped:.4f}".rstrip("0").rstrip(".")
    return text or "0"


PROJECT = "ducktop2"
PROJDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOOTPRINTS = {
    "R": "Resistor_SMD:R_0603_1608Metric",
    "R_0402": "Resistor_SMD:R_0402_1005Metric",
    "R_0805": "Resistor_SMD:R_0805_2012Metric",
    "C_100n": "Capacitor_SMD:C_0603_1608Metric",
    "C_0402": "Capacitor_SMD:C_0402_1005Metric",
    "C_0805": "Capacitor_SMD:C_0805_2012Metric",
    "C_1206": "Capacitor_SMD:C_1206_3216Metric",
    "C_1812": "Capacitor_SMD:C_1812_4532Metric",
    "C_1n": "Capacitor_SMD:C_0402_1005Metric",
    "C_1u": "Capacitor_SMD:C_0805_2012Metric",
    "C_10u": "Capacitor_SMD:C_1206_3216Metric",
    "D_Signal": "Diode_SMD:D_SOD-323",
    "D_Schottky": "Diode_SMD:D_SMB",
    "D_Schottky_Power_SMC": "Diode_SMD:D_SMC",
    "D_Schottky_SMA": "Diode_SMD:D_SMA",
    "D_Schottky_SOD123W": "Diode_SMD:D_SOD-123W",
    "D_TVS": "Diode_SMD:D_SMC",
    "D_Zener": "Diode_SMD:D_SOD-123",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "Fuse": "Fuse:Fuse_1206_3216Metric",
    "Fuse_Pack_Blade_Mini": "Fuse:Fuseholder_Blade_Mini_Keystone_3568",
    "Thermistor_NTC": "Resistor_SMD:R_0603_1608Metric",
    "Q_power": "Package_TO_SOT_SMD:TO-252-2",
    "Q_CSD18540Q5B": "ducktop2:CSD18540Q5B_DNK",
    "Q_CSD19537Q3": "ducktop2:CSD19537Q3_DQG",
    # CSD17575Q3 and CSD19537Q3 share TI's exact DQG0008A VSON-CLIP land pattern.
    "Q_CSD17575Q3": "ducktop2:CSD19537Q3_DQG",
    "Q_BSS138": "Package_TO_SOT_SMD:SOT-23",
    "Q_SiSS4409DN": "Package_SO:Vishay_PowerPAK_1212-8_Single",
    "LTC4368-1": "Package_SO:MSOP-10_3x3mm_P0.5mm",
    "BQ77915": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
    "LTC4417IGN": "Package_SO:SSOP-24_3.9x8.7mm_P0.635mm",
    "LTC4418IUF": "ducktop2:ADI_UF20_QFN20_4x4_P0.5_EP2.45",
    "TPS26630RGE": "Package_DFN_QFN:Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm_ThermalVias",
    "Conn_01x02": "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
    "Conn_01x02_Pack_MegaFit": "Connector_Molex:Molex_Mega-Fit_76829-0002_2x01_P5.70mm_Vertical",
    "Conn_02x03_Pack_MegaFit": "Connector_Molex:Molex_Mega-Fit_76829-0006_2x03_P5.70mm_Vertical",
    "Terminal_01x02_5.08": "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
    "Conn_01x03": "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
    "Conn_01x04": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "Conn_01x02_Service_GH": "Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal",
    "Conn_01x04_Service_GH": "Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal",
    "Conn_01x04_Header": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "SSD1306_0.96in_Module": "ducktop2:SSD1306_0.96in_Module_4Pin",
    "Conn_01x06": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "Conn_01x08": "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
    "Conn_01x10": "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical",
    "Conn_01x10_FFC": "Connector_FFC-FPC:Hirose_FH12-10S-0.5SH_1x10-1MP_P0.50mm_Horizontal",
    "Conn_01x16": "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
    "Conn_01x18": "Connector_PinHeader_1.27mm:PinHeader_1x18_P1.27mm_Vertical",
    "Conn_01x20_FFC": "Connector_FFC-FPC:Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal",
    "Conn_01x30_FFC": "Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal",
    "Conn_01x40_FFC": "Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal",
    # Polarized/latching 2.00 mm cable header. J901 is deliberately not a
    # Raspberry Pi HAT connector and cannot accept a 2.54 mm HAT plug.
    "Conn_02x20_Maker": "Connector_JST:JST_PUD_B40B-PUDSS_2x20_P2.00mm_Vertical",
    "TagConnect_SWD": "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
    "TestPoint_Pad": "TestPoint:TestPoint_Pad_D1.0mm",
    "RP2350A": "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm_ThermalVias",
    "W25Q32RVXHJQ": "Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm",
    "RT6150BGQW": "Package_SON:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias",
    "L_RP2350": "Inductor_SMD:L_Wuerth_PMFI-201610_PMCI-compatible",
    "Q_SOT523": "Package_TO_SOT_SMD:SOT-523",
    "Conn_Coaxial_UFL": "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
    "Conn_Coaxial_SMA_Edge": "Connector_Coaxial:SMA_Molex_73251-1153_EdgeMount_Horizontal",
    "DRA818": "ducktop2:DRA818_Castellated",
    "PE42820": "ducktop2:PE42820_QFN-32-1EP_5x5mm_P0.5mm",
    "MiniCircuits_ULP": "ducktop2:MiniCircuits_QA2224_PL484",
    "MiniCircuits_LFCN_FV1206": "Filter:Filter_Mini-Circuits_FV1206",
    "Crystal_HSE": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Crystal_LSE": "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm",
    "SW_Push": "Button_Switch_SMD:SW_SPST_B3S-1000",
    "L_buck": "Inductor_SMD:L_1210_3225Metric",
    "L_XGL4020": "ducktop2:Coilcraft_XGL4020",
    "L_XGL5030": "ducktop2:Coilcraft_XGL5030",
    "L_XGL6030": "ducktop2:Coilcraft_XGL6030",
    "L_XAL7070": "Inductor_SMD:L_Coilcraft_XAL7070-XXX",
    "L_SY8253": "ducktop2:Coilcraft_XGL4020",
    "L_BQ25798": "Inductor_SMD:L_Coilcraft_XAL7030-102",
    "L_RF": "Inductor_SMD:L_0603_1608Metric",
    "C_RF": "Capacitor_SMD:C_0603_1608Metric",
    "U_SOT23_6": "Package_TO_SOT_SMD:SOT-23-6",
    "Conn_01x02_Header": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "LattePanda_Mu": "Module_LattePanda:LattePanda_Module_H8.0mm_Horizontal",
    "M2_M_key": "ducktop2:Amphenol_MDT420M01001_H4.2",
    "M2_E_key": "ducktop2:Amphenol_MDT420E01001_H4.2",
    "Mu_M2_Standoff_H5.5": "ducktop2:Wurth_9774055243R_M2_H5.5",
    "M2_Card_Standoff_H2.5": "ducktop2:SMT_Standoff_M2_H2.5_C4_Tail2.7x1.5",
    "Mainboard_M2.5_Hole": "MountingHole:MountingHole_2.7mm_M2.5",
    "USB3_A": "Connector_USB:USB3_A_Receptacle_Wuerth_692122030100",
    "HDMI_A": "Connector_Video:HDMI_A_Molex_208658-1001_Horizontal",
    "Q_NMOS": "Package_TO_SOT_SMD:SOT-23",
    "AP2112K-3.3": "Package_TO_SOT_SMD:SOT-23-5",
    "AMS1117-3.3": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SY8253ADC": "Package_TO_SOT_SMD:TSOT-23-6",
    "TPS56637": "ducktop2:Texas_RPA0010A_VQFN-HR-10_3x3mm",
    "VL822-Q7": "ducktop2:QFN-76-1EP_9x9mm_P0.4mm_EP6.3x6.3mm",
    "TPS7A0210": "Package_SON:Texas_X2SON-4_1x1mm_P0.65mm",
    "TUSB8020BIPHP": "Package_QFP:Texas_PHP0048E_HTQFP-48-1EP_7x7mm_P0.5mm_EP6.5x6.5mm_Mask3.62x3.62mm_ThermalVias",
    "TPS62821DLC": "Package_SON:Texas_VSON-HR-8_1.5x2mm_P0.5mm",
    "TPS2553DDBV": "Package_TO_SOT_SMD:SOT-23-6",
    "L_TFM201610": "ducktop2:TDK_TFM201610",
    "TPS552892": "ducktop2:Texas_RYQ0021A_VQFN-HR-21_3x5mm",
    "L_MU12": "Inductor_SMD:L_Coilcraft_XAL7030-472",
    "C_100u_25V_poly": "Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D",
    "C_68u_50V_hybrid": "Capacitor_SMD:CP_Elec_8x10",
    "C_100u_35V_hybrid": "Capacitor_SMD:CP_Elec_6.3x5.8",
    "R_1206": "Resistor_SMD:R_1206_3216Metric",
    "TLV803EA29RDBZR": "Package_TO_SOT_SMD:SOT-23-3",
    "TLV803EA43RDBZR": "Package_TO_SOT_SMD:SOT-23-3",
    "L_DFE201610": "Inductor_SMD:L_Murata_DFE201610P",
    "TPS2052B": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "TPS2592xx": "Package_SON:VSON-10-1EP_3x3mm_P0.5mm_EP1.2x2mm_ThermalVias",
    "TPS259470A": "ducktop2:Texas_RPW0010A_VQFN-HR-10_2x2mm",
    "TPS22975N": "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
    "PCM2902": "Package_SO:SSOP-28_5.3x10.2mm_P0.65mm",
    "PCM2900C": "Package_SO:SSOP-28_5.3x10.2mm_P0.65mm",
    "LP5907MFX-2.8": "Package_TO_SOT_SMD:SOT-23-5",
    "TLV9061xDBV": "Package_TO_SOT_SMD:SOT-23-5",
    "IM68A130V01": "ducktop2:Infineon_IM68A130V01",
    "RTL8111H": "Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm",
    "D3V3XA4B10LP": "Package_DFN_QFN:Diodes_UDFN-10_1x2.5mm_P0.5mm",
    "JXD1-1022NL": "ducktop2:JXD1-1022NL_MidMount",
    "USB_C_Receptacle": "Connector_USB:USB_C_Receptacle_Molex_105450-0101",
    "TS3USB30EDGSR": "Package_SO:TSSOP-10_3x3mm_P0.5mm",
    "TPS25810RVC": "Package_DFN_QFN:Texas_RVC0020A_WQFN-20-1EP_3x4mm_P0.5mm_EP1.6x2.6mm",
    "HD3SS6126": "Package_DFN_QFN:WQFN-42-1EP_3.5x9mm_P0.5mm_EP2.05x7.55mm_ThermalVias",
    "CH224K": "Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm",
    "CH224A": "Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm",
    "TPD12S520DBT": "Package_SO:TSSOP-38_4.4x9.7mm_P0.5mm",
    "TPD13S523PWR": "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
    "PCA9306DCTR": "Package_SO:SSOP-8_2.95x2.8mm_P0.65mm",
    "SN74LVC1G17DBV": "Package_TO_SOT_SMD:SOT-23-5",
    "SN74LVC1G08DBV": "Package_TO_SOT_SMD:SOT-23-5",
    "SN74LVC1G373DCK": "Package_TO_SOT_SMD:SOT-363_SC-70-6",
    "SN74LVC2G04DCK": "Package_TO_SOT_SMD:SOT-363_SC-70-6",
    "SN74LVC2G32DCU": "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
    "SN74LVC3G34DCU": "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
    "SN74AHCT1G126DBV": "Package_TO_SOT_SMD:SOT-23-5",
    "TPD4E02B04DQA": "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
    "TPD4E05U06DQA": "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
    "TPD1E0B04DPL": "Diode_SMD:D_0201_0603Metric",
    "PESD4V0Y1BCSF": "Diode_SMD:Nexperia_DSN0603-2_0.6x0.3mm_P0.4mm",
    "PESD7V0R1BSF": "Diode_SMD:Nexperia_DSN0603-2_0.6x0.3mm_P0.4mm",
    "TPD4EUSB30": "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
    "USBLC6-2P6": "Package_TO_SOT_SMD:SOT-666",
    "BQ34Z100-G1": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
    "MAX-M10S": "RF_GPS:ublox_MAX",
    "Cherry_MX_ULP": "ducktop2:Cherry_MX_ULP_SMD",
    "TCA9548APWR": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
    "TCA9535PWR": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
    "TCA9539PWR": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
    "SN74LVC1T45DBV": "Package_TO_SOT_SMD:SOT-23-6",
    "SN74CB3T3245": "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
}


class Sheet:
    def __init__(self, sheet_path_prefix):
        self.sheet_path_prefix = sheet_path_prefix
        self.lib_symbols = {}
        self.body = []
        self.refcounters = {}

    def _use_symbol(self, name):
        lib, text = genlib.load_renamed_symbol(name)
        self.lib_symbols[(lib, name)] = text
        return lib

    def nextref(self, prefix):
        n = self.refcounters.get(prefix, 0) + 1
        self.refcounters[prefix] = n
        if prefix.startswith("#"):
            return f"{prefix}{n:03d}"
        return f"{prefix}{n}"

    def place(self, ref, symname, value, x, y, footprint="", pin_nets=None, unit=None, extra_props=None,
              dnp=None, in_bom=None, on_board=True):
        x = snap_coord(x)
        y = snap_coord(y)
        lib = self._use_symbol(symname)
        all_pins = genlib.parse_pins(self.lib_symbols[(lib, symname)])
        units_present = sorted(set(p["unit"] for p in all_pins.values()))
        placeable_units = [u for u in units_present if u != 0]
        if unit is None:
            if not units_present:
                unit = 1
            elif not placeable_units and units_present == [0]:
                unit = 0
            elif len(placeable_units) == 1:
                unit = placeable_units[0]
            else:
                raise ValueError(f"{symname} has multiple units {units_present}, must specify unit=")
        pins = {n: p for n, p in all_pins.items() if p["unit"] in (0, unit)}

        sym_uuid = U()
        is_dnp = ("DNP" in value.upper()) if dnp is None else bool(dnp)
        if in_bom is None:
            in_bom = not is_dnp
        props = []
        props.append(f'(property "Reference" "{ref}" (at {fmt_coord(x)} {fmt_coord(y - 2.54)} 0) (effects (font (size 1.27 1.27))))')
        props.append(f'(property "Value" "{value}" (at {fmt_coord(x)} {fmt_coord(y + 2.54)} 0) (effects (font (size 1.27 1.27))))')
        props.append(f'(property "Footprint" "{footprint}" (at {fmt_coord(x)} {fmt_coord(y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        props.append(f'(property "Datasheet" "" (at {fmt_coord(x)} {fmt_coord(y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        if extra_props:
            for k, v in extra_props.items():
                props.append(f'(property "{k}" "{v}" (at {fmt_coord(x)} {fmt_coord(y)} 0) (effects (font (size 1.27 1.27)) (hide yes)))')

        pin_lines = [f'(pin "{num}" (uuid {U()}))' for num in pins]

        sym_sexpr = (
            f'(symbol\n'
            f'  (lib_id "{lib}:{symname}")\n'
            f'  (at {fmt_coord(x)} {fmt_coord(y)} 0)\n'
            f'  (unit {unit})\n'
            f'  (exclude_from_sim no)\n'
            f'  (in_bom {"yes" if in_bom else "no"})\n'
            f'  (on_board {"yes" if on_board else "no"})\n'
            f'  (dnp {"yes" if is_dnp else "no"})\n'
            f'  (uuid {sym_uuid})\n'
            + "\n".join("  " + p for p in props) + "\n"
            + "\n".join("  " + p for p in pin_lines) + "\n"
            f'  (instances\n'
            f'    (project "{PROJECT}"\n'
            f'      (path "{self.sheet_path_prefix}"\n'
            f'        (reference "{ref}")\n'
            f'        (unit {unit})\n'
            f'      )\n'
            f'    )\n'
            f'  )\n'
            f')'
        )
        self.body.append(sym_sexpr)

        abs_pins = {}
        for num, p in pins.items():
            ax = snap_coord(x + p["x"])
            ay = snap_coord(y - p["y"])
            abs_pins[num] = (ax, ay)

        if pin_nets:
            for num, spec in pin_nets.items():
                if num not in abs_pins:
                    raise ValueError(f"{ref} ({symname} unit {unit}) has no pin {num}; available: {list(abs_pins)}")
                ax, ay = abs_pins[num]
                netname, kind = spec
                if kind == "local":
                    self.label(ax, ay, netname, hier=False)
                elif kind == "hier":
                    self.label(ax, ay, netname, hier=True)
                elif kind == "nc":
                    self.no_connect(ax, ay)
                elif kind == "none":
                    pass
                else:
                    raise ValueError(f"unknown kind {kind}")
        return abs_pins

    def label(self, x, y, name, hier=False):
        x = snap_coord(x)
        y = snap_coord(y)
        kind = "hierarchical_label" if hier else "label"
        shape = "\n  (shape bidirectional)" if hier else ""
        s = (
            f'({kind} "{name}"{shape}\n'
            f'  (at {fmt_coord(x)} {fmt_coord(y)} 0)\n'
            f'  (effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'  (uuid {U()})\n'
            f')'
        )
        self.body.append(s)

    def no_connect(self, x, y):
        self.body.append(f'(no_connect (at {fmt_coord(x)} {fmt_coord(y)}) (uuid {U()}))')

    def gnd(self, x, y):
        pins = self.place(self.nextref("#PWR"), "GND", "GND", x, y)
        ax, ay = pins["1"]
        self.label(ax, ay, "GND", hier=False)

    def pwrflag(self, x, y, netname):
        pins = self.place(self.nextref("#FLG"), "PWR_FLAG", "PWR_FLAG", x, y)
        ax, ay = pins["1"]
        self.label(ax, ay, netname, hier=False)

    def text(self, x, y, msg):
        msg_escaped = msg.replace('"', "'")
        self.body.append(f'(text "{msg_escaped}" (at {fmt_coord(x)} {fmt_coord(y)} 0) (effects (font (size 1.27 1.27))) (uuid {U()}))')

    def render(self, self_uuid, page_number):
        libsyms = "\n".join(self.lib_symbols[k] for k in sorted(self.lib_symbols))
        body = "\n".join(self.body)
        sheet_instances = (
            f'(sheet_instances\n'
            f'  (path "{self.sheet_path_prefix}"\n'
            f'    (page "{page_number}")\n'
            f'  )\n'
            f')'
        )
        return (
            f'(kicad_sch\n'
            f'  (version 20260306)\n'
            f'  (generator "eeschema")\n'
            f'  (generator_version "10.0")\n'
            f'  (uuid {self_uuid})\n'
            f'  (paper "A2")\n'
            f'  (lib_symbols\n{libsyms}\n  )\n'
            f'{body}\n'
            f'{sheet_instances}\n'
            f'  (embedded_fonts no)\n'
            f')\n'
        )
