import re, uuid, os

SYMDIR = os.path.dirname(os.path.abspath(__file__))

LIBMAP = {
    "R": "Device", "C": "Device", "C_Polarized": "Device", "D_Schottky": "Device",
    "D_Zener": "Device", "Fuse": "Device", "Thermistor_NTC": "Device", "Q_NMOS": "Device",
    "Battery_Cell": "Device", "R_Small": "Device", "LED": "Device", "L": "Device",
    "GND": "power", "PWR_FLAG": "power",
    "Conn_01x02": "Connector_Generic", "Conn_01x04": "Connector_Generic",
    "BQ76920PW": "ducktop2", "BQ25798": "ducktop2", "BQ24650": "ducktop2",
    "STM32F407VGTx": "MCU_ST_STM32F4",
    "TPS54202DDC": "ducktop2",
    "Crystal": "Device", "SW_Push": "Switch",
    "Conn_01x06": "Connector_Generic", "Conn_01x08": "Connector_Generic",
    "Conn_01x16": "Connector_Generic",
    "LattePanda_Mu": "Module_LattePanda",
    "TPS54302": "ducktop2",
    "Bus_M.2_Socket_M": "Connector", "Bus_M.2_Socket_E": "Connector",
    "USB3_A": "Connector",
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

def load_renamed_symbol(name):
    lib = LIBMAP[name]
    path = os.path.join(SYMDIR, f"{name}.kicad_sym")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    block = extract_symbol_block(text, name)
    qualified = f'(symbol "{lib}:{name}"'
    renamed = qualified + block[len(f'(symbol "{name}"'):]
    return lib, renamed

PIN_RE = re.compile(
    r'\(pin (\w+) line\s*\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)\s*\(length [\-\d.]+\)(?:\s*\(hide yes\))?'
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
