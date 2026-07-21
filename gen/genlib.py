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
    "Q_NMOS_123S_4G_5678D": "Q_NMOS_123S_4G_5678D",
    "Q_PMOS_1G_234S_5D": "Q_PMOS_1G_234S_5D",
    "Q_PMOS_GSD": "Transistor_FET",
    "Battery_Cell": "Device", "R_Small": "Device", "LED": "Device", "L": "Device",
    "GND": "power", "PWR_FLAG": "power",
    "MountingHole": "Mechanical", "MountingHole_Pad": "Mechanical", "TestPoint": "Connector",
    "Conn_01x02": "Connector_Generic", "Conn_01x03": "Connector_Generic", "Conn_01x04": "Connector_Generic",
    "Conn_01x10": "Connector_Generic", "Conn_01x18": "Connector_Generic",
    "Conn_01x20": "Connector_Generic", "Conn_01x30": "Connector_Generic",
    "Conn_01x40": "Connector_Generic", "Conn_02x03_Odd_Even": "Connector_Generic",
    "Conn_02x30_Odd_Even": "Connector_Generic",
    "Conn_01x10_FFC_MP": "Conn_01x10_FFC_MP",
    "Conn_01x30_FFC_MP": "Conn_01x30_FFC_MP",
    "Conn_02x30_MP": "Conn_02x30_MP",
    "Conn_02x20_Odd_Even": "Connector_Generic",
    "BQ76920PW": "ducktop2", "BQ25798": "ducktop2", "BQ24650": "ducktop2",
    "BQ34Z100-G1": "BQ34Z100-G1", "BQ77915": "BQ77915", "LTC4368-1": "LTC4368-1",
    "LTC4417CGN": "Power_Management", "LTC4418IUF": "LTC4418IUF",
    "TPS26630RGE": "Power_Management",
    "STM32F407VGTx": "MCU_ST_STM32F4",
    "RP2350A": "MCU_RaspberryPi",
    "W25Q32JVZP": "Memory_Flash",
    "RT6150BGQW": "RT6150BGQW",
    "TPS54202DDC": "ducktop2",
    "Crystal": "Device", "Crystal_GND24": "Device", "ASDMB-xxxMHz": "Oscillator", "SW_Push": "Switch",
    "Conn_01x06": "Connector_Generic", "Conn_01x08": "Connector_Generic",
    "Conn_01x16": "Connector_Generic",
    "Conn_Coaxial": "Connector",
    "LattePanda_Mu": "Module_LattePanda",
    "DRA818": "DRA818",
    "PE42820": "PE42820",
    "MiniCircuits_ULP": "MiniCircuits_ULP",
    "LFCN-160": "RF_Filter",
    "TPS54302": "ducktop2",
    "PCM2902": "Audio",
    "PCM2900C": "PCM2900C",
    "RTL8111H": "RTL8111H",
    "JXD1-1022NL": "JXD1-1022NL",
    "D3V3XA4B10LP": "Power_Protection",
    "IM68A130V01": "IM68A130V01",
    "LP5907MFX-2.8": "Regulator_Linear",
    "TLV9061xDBV": "Amplifier_Operational",
    "Bus_M.2_Socket_M": "Connector", "Bus_M.2_Socket_E": "Connector",
    "USB3_A": "Connector",
    "HDMI_A": "Connector",
    "AP2112K-3.3": "ducktop2", "AMS1117-3.3": "ducktop2",
    "SY8253ADC": "ducktop2",
    "TPS56637": "TPS56637",
    "VL822-Q7": "ducktop2",
    "TPS7A0210": "ducktop2",
    "TUSB8020BIPHP": "TUSB8020BIPHP",
    "USB7206C": "USB7206C",
    "TPS62821DLC": "TPS62821DLC",
    "TPS62823DLC": "Regulator_Switching",
    "TPS2553D": "TPS2553D",
    "TPS552892": "TPS552892",
    "TLV803EA29RDBZR": "TLV803EA29RDBZR",
    "TLV803EA43RDBZR": "TLV803EA43RDBZR",
    "USB2512B": "USB2512B",
    "PCM2704C": "PCM2704C",
    "TPA2012D2": "TPA2012D2",
    "74LVC1G08": "74xGxx",
    "74LVC1G373": "74xGxx",
    "74LVC2G04": "74xGxx",
    "74LVC2G07": "74xGxx",
    "74LVC2G32": "74xGxx",
    "74LVC3G34": "74xGxx",
    "74LVC1G17": "74xGxx",
    "74AHCT1G126": "74xGxx",
    "TPS2052B": "ducktop2",
    "TPS2592xx": "Power_Management",
    "TPS259470A": "TPS259470A",
    "TPS22975N": "TPS22975N",
    "USB_C_Receptacle": "Connector",
    "USB_C_Receptacle_Passive": "USB_C_Receptacle_Passive",
    "TS3USB30EDGSR": "Interface_USB",
    "TPS25810RVC": "Interface_USB",
    "HD3SS6126": "Interface_USB",
    "TPS25751AD": "TPS25751AD",
    "TUSB1142": "TUSB1142",
    "TPD1E0B04": "TPD1E0B04",
    "TPD4S201": "TPD4S201",
    "TPD1S514_1YZR": "TPD1S514_1YZR",
    "TVS2200DRV": "Power_Protection",
    "SST26VF016B": "SST26VF016B",
    "CAT24C256": "Memory_EEPROM",
    "CH224K": "Interface_USB", "CH224A": "CH224A",
    "TPD12S520DBT": "Interface_HDMI",
    "TPD13S523PWR": "TPD13S523PWR",
    "PCA9306DCTR": "PCA9306DCTR",
    "TPD4E02B04DQA": "Power_Protection",
    "TPD4E05U06DQA": "Power_Protection",
    "TPD4EUSB30": "Power_Protection",
    "USBLC6-2P6": "Power_Protection",
    "MAX-M10S": "RF_GPS",
    "Cherry_MX_ULP": "Cherry_MX_ULP",
    "TCA9548APWR": "Interface_Expansion",
    "TCA9535PWR": "Interface_Expansion",
    # TCA9539PWR is pin-compatible with the stock PCA9539xD symbol when the
    # package is overridden to TSSOP-24.  Unlike TCA9535, pin 3 is RESET and
    # pin 21 is A0, which lets the source manager fail off on every EC reset.
    "PCA9539xD": "Interface_Expansion",
    "SN74LVC1T45DBV": "Logic_LevelTranslator",
    "SN74CB3T3245": "SN74CB3T3245",
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

FFC_MP_SYMBOLS = {
    "Conn_01x10_FFC_MP": ("Conn_01x10", -15.24),
    "Conn_01x30_FFC_MP": ("Conn_01x30", -40.64),
    "Conn_02x30_MP": ("Conn_02x30_Odd_Even", -40.64),
}

LOCAL_SYMBOL_SOURCE_NAMES = {
    "TPD1S514_1YZR": "TPD1S514_1YZR",
    "SST26VF016B": "SST26VF016B-104I_SM",
}


def add_mp_pin(block, name, y):
    unit_block = extract_symbol_block(block, f"{name}_1_1")
    mp_pin = (
        f'\t(pin passive line\n'
        f'\t\t\t\t(at 5.08 {y} 180)\n'
        f'\t\t\t\t(length 2.54)\n'
        f'\t\t\t\t(name "MP"\n'
        f'\t\t\t\t\t(effects\n'
        f'\t\t\t\t\t\t(font\n'
        f'\t\t\t\t\t\t\t(size 1.27 1.27)\n'
        f'\t\t\t\t\t\t)\n'
        f'\t\t\t\t\t)\n'
        f'\t\t\t\t)\n'
        f'\t\t\t\t(number "MP"\n'
        f'\t\t\t\t\t(effects\n'
        f'\t\t\t\t\t\t(font\n'
        f'\t\t\t\t\t\t\t(size 1.27 1.27)\n'
        f'\t\t\t\t\t\t)\n'
        f'\t\t\t\t\t)\n'
        f'\t\t\t\t)\n'
        f'\t\t\t)\n'
    )
    return block.replace(unit_block, unit_block[:-1] + mp_pin + "\t\t)")


def override_pin_types(block, overrides):
    """Return a symbol block with selected pin electrical types replaced."""
    replacements = dict(overrides)
    cursor = 0
    while True:
        start = block.find("(pin ", cursor)
        if start < 0:
            break
        depth = 0
        in_string = False
        escape = False
        end = None
        for i in range(start, len(block)):
            c = block[i]
            if in_string:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
        if end is None:
            raise ValueError("unbalanced pin block")
        pin_block = block[start:end]
        number = re.search(r'\(number "([^"]+)"', pin_block)
        if number and number.group(1) in replacements:
            new_type = replacements[number.group(1)]
            pin_block = re.sub(r'^\(pin \w+ line', f'(pin {new_type} line', pin_block, count=1)
            block = block[:start] + pin_block + block[end:]
            end = start + len(pin_block)
        cursor = end
    return block


def load_renamed_symbol(name):
    lib = LIBMAP[name]
    if name in FFC_MP_SYMBOLS:
        source_name, mp_y = FFC_MP_SYMBOLS[name]
        source_lib = "Connector_Generic"
    else:
        source_name = LOCAL_SYMBOL_SOURCE_NAMES.get(
            name,
            "USB_C_Receptacle" if name == "USB_C_Receptacle_Passive" else name,
        )
        source_lib = "Connector" if name == "USB_C_Receptacle_Passive" else lib
    path = symbol_file_for(source_lib, name if name in LOCAL_SYMBOL_SOURCE_NAMES else source_name)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    block = extract_symbol_block(text, source_name)
    # KiCad stock libraries increasingly express orderable variants with
    # `(extends "parent")`.  A generated schematic must embed the complete
    # symbol, not the property-only child block, so flatten it in memory while
    # retaining the child's value, footprint, datasheet, and description.
    extends = re.search(r'\(extends "([^"]+)"\)', block)
    if extends:
        parent_name = extends.group(1)
        parent = extract_symbol_block(text, parent_name)
        parent = re.sub(rf'"{re.escape(parent_name)}_(\d+)_(\d+)"',
                        f'"{source_name}_\\1_\\2"', parent)
        parent = parent.replace(f'(symbol "{parent_name}"', f'(symbol "{source_name}"', 1)
        for prop, value in re.findall(r'\(property "([^"]+)" "([^"]*)"', block):
            parent = re.sub(
                rf'(\(property "{re.escape(prop)}" ")[^"]*(")',
                lambda m, v=value: m.group(1) + v + m.group(2),
                parent, count=1,
            )
        block = parent
    if name == "USB_C_Receptacle_Passive":
        block = block.replace('"USB_C_Receptacle', '"USB_C_Receptacle_Passive')
        block = re.sub(r'\(pin \w+ line', '(pin passive line', block)
    elif name in FFC_MP_SYMBOLS:
        block = block.replace(f'"{source_name}', f'"{name}')
        block = add_mp_pin(block, name, mp_y)
    elif name in {"Bus_M.2_Socket_M", "Bus_M.2_Socket_E"}:
        # These are physical sockets.  The stock symbols encode host-facing
        # PCIe directions, which makes the absent plug-in card look like an
        # undriven input to ERC.  Passive connector pins leave directionality
        # to the Mu endpoint while preserving every official pin name/number.
        block = re.sub(r'\(pin \w+ line', '(pin passive line', block)
    elif name == "LattePanda_Mu":
        # USB_OC# has the documented on-module pull-up and is driven only by
        # external open-drain FAULT outputs.  Treat this one pad as passive so
        # ERC does not demand a push-pull driver that would be electrically wrong.
        block = override_pin_types(block, {"129": "passive"})
    elif name == "LTC4417CGN":
        # VOUT is a supply/sense input connected to the external MOSFET output;
        # the controller does not source the selected rail through this pin.
        block = override_pin_types(block, {"15": "power_in"})
    if name in LOCAL_SYMBOL_SOURCE_NAMES:
        # KiCad requires every graphical/unit sub-symbol identifier to use the
        # same base name as the outer symbol.  Local libraries often name the
        # source after the full orderable part (for example TPD1E0B04DPLR),
        # while the generated library uses a shorter project-facing name.
        block = block.replace(f'"{source_name}_', f'"{name}_')
    # Transformations above may already rename the outer symbol (for example
    # the passive USB-C and FFC-with-mounting-pad variants).  Replacing the
    # complete outer identifier is robust; slicing by the original source-name
    # length corrupts any variant whose generated name has a different length.
    qualified = f'(symbol "{lib}:{name}"'
    renamed = re.sub(r'^\(symbol "[^"]+"', qualified, block, count=1)
    if renamed == block:
        raise ValueError(f"could not qualify outer symbol name for {name}")
    return lib, renamed

PIN_RE = re.compile(
    r'\(pin (\w+) \w+\s*\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)\s*\(length [\-\d.]+\)(?:\s*(?:\(hide yes\)|hide))?'
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
