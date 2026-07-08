import re, uuid, os

SYMDIR = os.path.dirname(os.path.abspath(__file__))

STOCK_SYMBOL_DIRS = [
    d for d in [
        os.environ.get("KICAD10_SYMBOL_DIR"),
        os.environ.get("KICAD_SYMBOL_DIR"),
        "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",
        "/usr/share/kicad/symbols",
        "/usr/local/share/kicad/symbols",
    ]
    if d
]

LIBMAP = {
    "R": "Device", "C": "Device", "C_Polarized": "Device", "D": "Device", "D_Schottky": "Device",
    "D_Zener": "Device", "D_TVS": "Device", "Fuse": "Device", "Thermistor_NTC": "Device", "Q_NMOS": "Device",
    "Q_NMOS_SOT23_GSD": "Q_NMOS_SOT23_GSD", "Q_NMOS_TO252_GDS": "Q_NMOS_TO252_GDS",
    "Battery_Cell": "Device", "R_Small": "Device", "LED": "Device", "L": "Device",
    "GND": "power", "PWR_FLAG": "power",
    "Conn_01x02": "Connector_Generic", "Conn_01x04": "Connector_Generic",
    "Conn_01x10": "Connector_Generic", "Conn_01x18": "Connector_Generic",
    "Conn_01x20": "Connector_Generic", "Conn_01x30": "Connector_Generic",
    "Conn_01x40": "Connector_Generic",
    "Conn_02x20_Odd_Even": "Connector_Generic",
    "BQ76920PW": "ducktop2", "BQ25798": "ducktop2", "BQ24650": "ducktop2",
    "BQ34Z100-G1": "BQ34Z100-G1",
    "STM32F407VGTx": "MCU_ST_STM32F4",
    "TPS54202DDC": "ducktop2",
    "Crystal": "Device", "Crystal_GND24": "Device", "SW_Push": "Switch",
    "Conn_01x06": "Connector_Generic", "Conn_01x08": "Connector_Generic",
    "Conn_01x16": "Connector_Generic",
    "Conn_Coaxial": "Connector",
    "LattePanda_Mu": "Module_LattePanda",
    "TPS54302": "ducktop2",
    "PCM2902": "Audio",
    "Bus_M.2_Socket_M": "Connector", "Bus_M.2_Socket_E": "Connector",
    "USB3_A": "Connector",
    "HDMI_A": "Connector",
    "AP2112K-3.3": "ducktop2", "AMS1117-3.3": "ducktop2",
    "SY8253ADC": "ducktop2",
    "VL822-Q7": "ducktop2",
    "TPS7A0210": "ducktop2",
    "TPS2052B": "ducktop2",
    "TPS2592xx": "Power_Management",
    "USB_C_Receptacle": "Connector",
    "USB_C_Receptacle_Passive": "USB_C_Receptacle_Passive",
    "TPS25810RVC": "Interface_USB",
    "HD3SS6126": "Interface_USB",
    "CH224K": "Interface_USB",
    "TPD12S520DBT": "Interface_HDMI",
    "TPD4E02B04DQA": "Power_Protection",
    "TPD4EUSB30": "Power_Protection",
    "USBLC6-2P6": "Power_Protection",
    "BGS12WN6E6327": "RF_Switch",
    "MAX-M10S": "RF_GPS",
    "Cherry_MX_ULP": "Cherry_MX_ULP",
}

def extract_symbol_block(text, name):
    marker = f'(symbol "{name}"'
    idx = text.index(marker)
    depth = 0
    i = idx
    start = idx
    while True:
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                return text[start:end]
        i += 1

def flatten_extends_symbol(lib_path, base_name, new_name, overrides, out_path):
    """Flatten a KiCad `extends`-based symbol into a standalone .kicad_sym file.

    base_name: symbol in lib_path that actually has pin geometry (the parent).
    new_name: name for the flattened output symbol (becomes the LIBMAP key).
    overrides: dict of property name -> value stamped onto the result
      (e.g. Value/Footprint/Datasheet/Description), whether relabeling a
      vendor's own derived variant or reusing a base part as an electrical
      stand-in for an unrelated real part with the same pinout/package.
    """
    text = open(lib_path, encoding="utf-8").read()
    block = extract_symbol_block(text, base_name)
    flat = re.sub(rf'"{re.escape(base_name)}_(\d+)_(\d+)"', f'"{new_name}_\\1_\\2"', block)
    flat = flat.replace(f'(symbol "{base_name}"', f'(symbol "{new_name}"', 1)
    for prop, value in overrides.items():
        flat = re.sub(
            rf'(\(property "{re.escape(prop)}" ")[^"]*(")',
            lambda m, v=value: m.group(1) + v + m.group(2),
            flat, count=1,
        )
    wrapped = (
        '(kicad_symbol_lib\n'
        '\t(version 20251024)\n'
        '\t(generator "kicad_symbol_editor")\n'
        '\t(generator_version "10.0")\n'
        '\t' + flat + '\n'
        ')\n'
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(wrapped)
    return out_path

def symbol_file_for(lib, name):
    local_path = os.path.join(SYMDIR, f"{name}.kicad_sym")
    if os.path.exists(local_path):
        return local_path

    for root in STOCK_SYMBOL_DIRS:
        stock_path = os.path.join(root, f"{lib}.kicad_sym")
        if os.path.exists(stock_path):
            return stock_path

    searched = ", ".join(STOCK_SYMBOL_DIRS)
    raise FileNotFoundError(f"no symbol file for {lib}:{name}; searched {local_path}, {searched}")

def load_renamed_symbol(name):
    lib = LIBMAP[name]
    source_name = "USB_C_Receptacle" if name == "USB_C_Receptacle_Passive" else name
    source_lib = "Connector" if name == "USB_C_Receptacle_Passive" else lib
    path = symbol_file_for(source_lib, source_name)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    block = extract_symbol_block(text, source_name)
    if name == "USB_C_Receptacle_Passive":
        block = block.replace('"USB_C_Receptacle', '"USB_C_Receptacle_Passive')
        block = re.sub(r'\(pin \w+ line', '(pin passive line', block)
    qualified = f'(symbol "{lib}:{name}"'
    renamed = qualified + block[len(f'(symbol "{name}"'):]
    return lib, renamed

PIN_RE = re.compile(
    r'\(pin (\w+) line\s*\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)\s*\(length [\-\d.]+\)(?:\s*(?:\(hide yes\)|hide))?'
    r'\s*\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"',
)

SUBSYM_RE = re.compile(r'\(symbol "[^"]+_(\d+)_(\d+)"')

def parse_pins(symbol_text):
    """Returns dict: pin_number -> dict(name, x, y, rot, etype, unit)"""
    pins = {}
    # find sub-symbol blocks with their unit number, then parse pins within each
    for m in re.finditer(r'\(symbol "([^"]+)_(\d+)_(\d+)"', symbol_text):
        subname, unit, style = m.group(1), int(m.group(2)), int(m.group(3))
        start = m.start()
        block = extract_symbol_block(symbol_text[start:], f"{subname}_{unit}_{style}")
        for pm in PIN_RE.finditer(block):
            etype, x, y, rot, name, number = pm.groups()
            pins[number] = {
                "name": name, "x": float(x), "y": float(y), "rot": int(rot),
                "type": etype, "unit": unit,
            }
    return pins

if __name__ == "__main__":
    for testname in ["R", "GND", "Q_NMOS", "BQ76920PW", "BQ25798", "BQ24650", "Conn_01x04"]:
        lib, renamed = load_renamed_symbol(testname)
        pins = parse_pins(renamed)
        print(f"=== {lib}:{testname} ({len(pins)} pins) ===")
        for num, p in sorted(pins.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
            print(f"  {num}: {p['name']:12s} type={p['type']:14s} at=({p['x']},{p['y']}) rot={p['rot']} unit={p['unit']}")
