import uuid, os
import genlib

def U():
    return str(uuid.uuid4())

PROJECT = "ducktop2"
PROJDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOOTPRINTS = {
    "R": "Resistor_SMD:R_0603_1608Metric",
    "C_100n": "Capacitor_SMD:C_0603_1608Metric",
    "C_1u": "Capacitor_SMD:C_0805_2012Metric",
    "C_10u": "Capacitor_SMD:C_1206_3216Metric",
    "D_Schottky": "Diode_SMD:D_SOD-123",
    "D_Zener": "Diode_SMD:D_SOD-123",
    "LED": "LED_SMD:LED_0603_1608Metric",
    "Fuse": "Fuse:Fuse_1206_3216Metric",
    "Thermistor_NTC": "Resistor_SMD:R_0603_1608Metric",
    "Q_power": "Package_TO_SOT_SMD:TO-252-2",
    "Conn_01x02": "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
    "Conn_01x04": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "Conn_01x04_Header": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "Conn_01x06": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "Conn_01x08": "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
    "Conn_01x16": "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical",
    "Crystal_HSE": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Crystal_LSE": "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm",
    "SW_Push": "Button_Switch_SMD:SW_SPST_B3S-1000",
    "L_buck": "Inductor_SMD:L_1210_3225Metric",
    "U_SOT23_6": "Package_TO_SOT_SMD:SOT-23-6",
    "Conn_01x02_Header": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "LattePanda_Mu": "Module_LattePanda:LattePanda_Module_H8.0mm_Horizontal",
    "M2_M_key": "Connector_PCBEdge:M.2_2280-xx-M",
    "M2_E_key": "Connector_PCBEdge:M.2_2230-xx-E",
    "USB3_A": "Connector_USB:USB3_A_Receptacle_Wuerth_692122030100",
    "Q_NMOS": "Package_TO_SOT_SMD:SOT-23",
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

    def place(self, ref, symname, value, x, y, footprint="", pin_nets=None, unit=None, extra_props=None):
        lib = self._use_symbol(symname)
        all_pins = genlib.parse_pins(self.lib_symbols[(lib, symname)])
        units_present = sorted(set(p["unit"] for p in all_pins.values()))
        if unit is None:
            if len(units_present) != 1:
                raise ValueError(f"{symname} has multiple units {units_present}, must specify unit=")
            unit = units_present[0]
        pins = {n: p for n, p in all_pins.items() if p["unit"] == unit}

        sym_uuid = U()
        props = []
        props.append(f'(property "Reference" "{ref}" (at {x} {y - 2.5} 0) (effects (font (size 1.27 1.27))))')
        props.append(f'(property "Value" "{value}" (at {x} {y + 2.5} 0) (effects (font (size 1.27 1.27))))')
        props.append(f'(property "Footprint" "{footprint}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        props.append(f'(property "Datasheet" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        if extra_props:
            for k, v in extra_props.items():
                props.append(f'(property "{k}" "{v}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))')

        pin_lines = [f'(pin "{num}" (uuid {U()}))' for num in pins]

        sym_sexpr = (
            f'(symbol\n'
            f'  (lib_id "{lib}:{symname}")\n'
            f'  (at {x} {y} 0)\n'
            f'  (unit {unit})\n'
            f'  (exclude_from_sim no)\n'
            f'  (in_bom yes)\n'
            f'  (on_board yes)\n'
            f'  (dnp no)\n'
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
            ax = round(x + p["x"], 3)
            ay = round(y - p["y"], 3)
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
        kind = "hierarchical_label" if hier else "label"
        shape = "\n  (shape bidirectional)" if hier else ""
        s = (
            f'({kind} "{name}"{shape}\n'
            f'  (at {x} {y} 0)\n'
            f'  (effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'  (uuid {U()})\n'
            f')'
        )
        self.body.append(s)

    def no_connect(self, x, y):
        self.body.append(f'(no_connect (at {x} {y}) (uuid {U()}))')

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
        self.body.append(f'(text "{msg_escaped}" (at {x} {y} 0) (effects (font (size 1.27 1.27))) (uuid {U()}))')

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
