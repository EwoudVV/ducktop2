import uuid, os
import genlib

GRID_MM = 1.27


def U():
    return str(uuid.uuid4())


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
    "C_100n": "Capacitor_SMD:C_0603_1608Metric",
    "C_1n": "Capacitor_SMD:C_0402_1005Metric",
    "C_1u": "Capacitor_SMD:C_0805_2012Metric",
    "C_10u": "Capacitor_SMD:C_1206_3216Metric",
    "D_Signal": "Diode_SMD:D_SOD-323",
    "D_Schottky": "Diode_SMD:D_SMB",
    "D_TVS": "Diode_SMD:D_SOD-123",
    "D_Zener": "Diode_SMD:D_SOD-123",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "Fuse": "Fuse:Fuse_1206_3216Metric",
    "Fuse_Pack_Blade_Mini": "Fuse:Fuseholder_Blade_Mini_Keystone_3568",
    "Thermistor_NTC": "Resistor_SMD:R_0603_1608Metric",
    "Q_power": "Package_TO_SOT_SMD:TO-252-2",
    "Conn_01x02": "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
    "Conn_01x02_Pack_MegaFit": "Connector_Molex:Molex_Mega-Fit_76829-0002_2x01_P5.70mm_Vertical",
    "Terminal_01x02_5.08": "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
    "Conn_01x04": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "Conn_01x04_Header": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "Conn_01x06": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "Conn_01x08": "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
    "Conn_01x10": "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical",
    "Conn_01x10_FFC": "Connector_FFC-FPC:Hirose_FH12-10S-0.5SH_1x10-1MP_P0.50mm_Horizontal",
    "Conn_01x16": "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
    "Conn_01x18": "Connector_PinHeader_1.27mm:PinHeader_1x18_P1.27mm_Vertical",
    "Conn_01x20_FFC": "Connector_FFC-FPC:Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal",
    "Conn_01x30_FFC": "Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal",
    "Conn_01x40_FFC": "Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal",
    "Conn_02x20_Header": "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
    "Conn_Coaxial_UFL": "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical",
    "Conn_Coaxial_SMA_Edge": "Connector_Coaxial:SMA_Molex_73251-1153_EdgeMount_Horizontal",
    "Crystal_HSE": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Crystal_LSE": "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm",
    "SW_Push": "Button_Switch_SMD:SW_SPST_B3S-1000",
    "L_buck": "Inductor_SMD:L_1210_3225Metric",
    "L_RF": "Inductor_SMD:L_0603_1608Metric",
    "C_RF": "Capacitor_SMD:C_0603_1608Metric",
    "U_SOT23_6": "Package_TO_SOT_SMD:SOT-23-6",
    "Conn_01x02_Header": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "LattePanda_Mu": "Module_LattePanda:LattePanda_Module_H8.0mm_Horizontal",
    "M2_M_key": "Connector_PCBEdge:M.2_2280-xx-M",
    "M2_E_key": "Connector_PCBEdge:M.2_2230-xx-E",
    "USB3_A": "Connector_USB:USB3_A_Receptacle_Wuerth_692122030100",
    "HDMI_A": "Connector_Video:HDMI_A_Molex_208658-1001_Horizontal",
    "Q_NMOS": "Package_TO_SOT_SMD:SOT-23",
    "AP2112K-3.3": "Package_TO_SOT_SMD:SOT-23-5",
    "AMS1117-3.3": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "SY8253ADC": "Package_TO_SOT_SMD:TSOT-23-6",
    "VL822-Q7": "ducktop2:QFN-76-1EP_9x9mm_P0.4mm_EP6.3x6.3mm",
    "TPS7A0210": "ducktop2:X2SON-4_1.0x1.0mm_P0.65mm",
    "TPS2052B": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "TPS2592xx": "Package_SON:VSON-10-1EP_3x3mm_P0.5mm_EP1.2x2mm_ThermalVias",
    "PCM2902": "Package_SO:SSOP-28_5.3x10.2mm_P0.65mm",
    "USB_C_Receptacle": "Connector_USB:USB_C_Receptacle_Molex_105450-0101",
    "TPS25810RVC": "Package_DFN_QFN:Texas_RVC0020A_WQFN-20-1EP_3x4mm_P0.5mm_EP1.6x2.6mm",
    "HD3SS6126": "Package_DFN_QFN:WQFN-42-1EP_3.5x9mm_P0.5mm_EP2.05x7.55mm_ThermalVias",
    "CH224K": "Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm",
    "TPD12S520DBT": "Package_SO:TSSOP-38_4.4x9.7mm_P0.5mm",
    "TPD4E02B04DQA": "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
    "TPD4EUSB30": "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
    "USBLC6-2P6": "Package_TO_SOT_SMD:SOT-666",
    "BGS12WN6E6327": "Package_LGA:Infineon_PG-TSNP-6-10_0.7x1.1mm_0.7x1.1mm_P0.4mm",
    "BQ34Z100-G1": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
    "MAX-M10S": "RF_GPS:ublox_MAX",
    "Cherry_MX_ULP": "ducktop2:Cherry_MX_ULP_SMD",
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
            if not placeable_units and units_present == [0]:
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
