import re
from pathlib import Path

from build_ducktop2 import Sheet, FOOTPRINTS, stable_uuid, snap_coord, fmt_coord
from apply_bom_keyboard_daughterboard import ALL_ASSIGNMENTS
from generate_keyboard_rgb_sheet import add_rgb
import genlib


class KeyboardSheet(Sheet):
    def _use_symbol(self, name):
        lib = super()._use_symbol(name)
        if name in ('R', 'TestPoint'):
            # These parts use stock footprints. Do not attach the main board's
            # extra footprint filters to this standalone sheet.
            text = self.lib_symbols[(lib, name)]
            for extra in genlib.PROJECT_FOOTPRINT_FILTERS.get(name, ()):
                text = text.replace(' ' + extra, '')
            self.lib_symbols[(lib, name)] = text
        return lib

    def __init__(self, sheet_path_prefix):
        super().__init__(sheet_path_prefix)
        path = Path(__file__).resolve().parents[1] / "keyboard/12_keyboard_daughterboard.kicad_sch"
        self.existing_symbol_ids = {}
        if path.exists():
            for block in re.split(r'(?=\(symbol\s+\(lib_id)', path.read_text())[1:]:
                ref = re.search(r'\(property "Reference" "([^"]+)"', block)
                ident = re.search(r'\(uuid "?([0-9a-f-]+)"?\)', block)
                if ref and ident:
                    self.existing_symbol_ids[ref.group(1)] = ident.group(1)

    def place(self, ref, *args, **kwargs):
        # Adding frame pins or notes must not disconnect existing PCB links.
        first = len(self.body)
        self._vertical_passive = args[0] in ('R', 'C')
        pins = super().place(ref, *args, **kwargs)
        self._vertical_passive = False
        ident = self.existing_symbol_ids.get(ref, stable_uuid(f"keyboard-symbol:{ref}"))
        self.body[first] = re.sub(r'\(uuid [0-9a-f-]+\)', f'(uuid {ident})', self.body[first], count=1)
        x, y = snap_coord(args[2]), snap_coord(args[3])
        if args[0] in ('R', 'C'):
            for field, dy in (('Reference', -1.27), ('Value', 1.27)):
                self.move_field(first, field, x+3.81, y+dy, left=True)
        elif args[0] == 'Cherry_MX_ULP':
            self.move_field(first, 'Reference', x, y-3.81)
            self.move_field(first, 'Value', x, y-8.89)
        return pins

    def move_field(self, index, field, x, y, left=False):
        pattern = rf'(\(property "{field}" "[^"]*" )\(at [^)]*\) \(effects \(font \(size 1.27 1.27\)\)\)'
        replacement = rf'\1(at {fmt_coord(x)} {fmt_coord(y)} 0) (effects (font (size 1.27 1.27))'+(' (justify left)' if left else '')+')'
        self.body[index], count = re.subn(pattern, replacement, self.body[index], count=1)
        assert count == 1, field

    def wire(self, start, end):
        points = ' '.join(f'(xy {fmt_coord(x)} {fmt_coord(y)})' for x,y in (start,end))
        ident = stable_uuid(f'keyboard-wire:{start}:{end}')
        self.body.append(f'(wire (pts {points}) (stroke (width 0) (type default)) (uuid {ident}))')

    def text(self, x, y, msg):
        super().text(x, y, msg)
        self.body[-1] = self.body[-1].replace('(effects (font (size 1.27 1.27)))',
                                             '(effects (font (size 1.27 1.27)) (justify left))')

    def label(self, x, y, name, hier=False, angle=None, justify=None,
                pin_dx=None, pin_dy=None):
        if getattr(self, '_vertical_passive', False) and pin_dy:
            new_y = y + (-5.08 if pin_dy > 0 else 5.08)
            self.wire((x,y), (x,new_y))
            y = new_y
        # This board is a standalone schematic. Global labels keep the existing
        # matrix net names without a nonexistent parent sheet or a path prefix.
        # Cosmetic orientation (angle/justify) is preserved; only the kind is
        # forced to global for electrical compatibility with the released board.
        super().label(x, y, name, hier=False, angle=angle, justify=justify,
                      pin_dx=pin_dx, pin_dy=pin_dy)
        self.body[-1] = self.body[-1].replace('(label ', '(global_label ', 1).replace(
            '\n  (at ', '\n  (shape bidirectional)\n  (at ', 1)


RELEASED_BOARD_W_MM = 273.5
RELEASED_BOARD_H_MM = 80.0


KEY_ROWS = [
    [
        (0, "ESC", "Esc 1u"),
        (1, "1", "1 1u"),
        (2, "2", "2 1u"),
        (3, "3", "3 1u"),
        (4, "4", "4 1u"),
        (5, "5", "5 1u"),
        (6, "6", "6 1u"),
        (7, "7", "7 1u"),
        (8, "8", "8 1u"),
        (9, "9", "9 1u"),
        (10, "0", "0 1u"),
        (11, "MINUS", "Minus 1u"),
        (12, "EQUAL", "Equal 1u"),
        (13, "BKSP", "Backspace 1.75u"),
    ],
    [
        (0, "TAB", "Tab 1.25u"),
        (1, "Q", "Q 1u"),
        (2, "W", "W 1u"),
        (3, "E", "E 1u"),
        (4, "R", "R 1u"),
        (5, "T", "T 1u"),
        (6, "Y", "Y 1u"),
        (7, "U", "U 1u"),
        (8, "I", "I 1u"),
        (9, "O", "O 1u"),
        (10, "P", "P 1u"),
        (11, "LBRACKET", "[ 1u"),
        (12, "RBRACKET", "] 1u"),
        (13, "BSLASH", "Backslash 1u"),
    ],
    [
        (0, "CAPS", "Caps 1.5u"),
        (1, "A", "A 1u"),
        (2, "S", "S 1u"),
        (3, "D", "D 1u"),
        (4, "F", "F 1u"),
        (5, "G", "G 1u"),
        (6, "H", "H 1u"),
        (7, "J", "J 1u"),
        (8, "K", "K 1u"),
        (9, "L", "L 1u"),
        (10, "SEMICOLON", "Semicolon 1u"),
        (11, "QUOTE", "Quote 1u"),
        (12, "ENTER", "Enter 1.75u"),
    ],
    [
        (0, "LSHIFT", "Shift L 1.75u"),
        (1, "Z", "Z 1u"),
        (2, "X", "X 1u"),
        (3, "C", "C 1u"),
        (4, "V", "V 1u"),
        (5, "B", "B 1u"),
        (6, "N", "N 1u"),
        (7, "M", "M 1u"),
        (8, "COMMA", "Comma 1u"),
        (9, "PERIOD", "Period 1u"),
        (10, "SLASH", "Slash 1u"),
        (11, "UP", "Up 1u"),
        (12, "RSHIFT", "Shift R 1.25u"),
    ],
    [
        (0, "CTRL", "Ctrl 1u"),
        (1, "FN", "Fn 1u"),
        (2, "SUPER", "Super 1u"),
        (3, "LALT", "Alt L 1u"),
        (4, "SPACE_L", "Space L 2.25u"),
        (5, "SPACE_R", "Space R 2.25u"),
        (6, "RALT", "Alt R 1u"),
        (7, "MENU", "Menu 1u"),
        (9, "LEFT", "Left 1u"),
        (10, "DOWN", "Down 1u"),
        (11, "RIGHT", "Right 1u"),
    ],
]


def keyboard_connector_nets():
    """Keep the 30-pin cable and active matrix contacts; use its reserved I2C and power."""
    nets = {
        "1": ("GND", "local"),
        "2": ("MCU_3V3", "local"),
        "3": ("I2C_SCL", "local"),
        "4": ("I2C_SDA", "local"),
    }
    for i in range(5):
        nets[str(5 + i)] = (f"KB_ROW{i}", "local")
    for i in range(14):
        nets[str(13 + i)] = (f"KB_COL{i}", "local")
    nets.update({
        "29": ("KB_RGB_5V", "local"),
        "30": ("GND", "local"),
    })
    for pin in ('10','11','12','27','28'):
        nets[pin] = ('', 'nc')
    # The two J320 hold-down pads are mechanical-only and are netless on the
    # manufactured Rev A PCB. Leaving MP absent here makes that released state
    # authoritative instead of inventing a ground bond during regeneration.
    return nets


def safe_net_token(text):
    token = re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")
    return token or "KEY"


def iter_keys():
    for row, keys in enumerate(KEY_ROWS):
        for col, code, value in keys:
            yield row, col, code, value


def add_key_cell(s, index, row, col, code, value):
    x0 = 40 + col * 40
    y0 = 90 + row * 50
    key_node = f"KB_R{row}_C{col}_{safe_net_token(code)}"

    switch_manufacturer, switch_mpn, _ = ALL_ASSIGNMENTS[f"SW{320 + index}"]
    diode_manufacturer, diode_mpn, _ = ALL_ASSIGNMENTS[f"D{320 + index}"]
    switch = s.place(f"SW{320 + index}", "Cherry_MX_ULP", value, x0, y0,
            footprint=FOOTPRINTS["Cherry_MX_ULP"],
            extra_props={"Manufacturer": switch_manufacturer, "MPN": switch_mpn,
                         "Assembly": "fit after LEDs, diodes, connector and support parts"},
            pin_nets={
                "1": (key_node, "none"),
                "2": (f"KB_COL{col}", "local"),
                "MP": ("GND", "local"),
            })
    diode = s.place(f"D{320 + index}", "D", "1N4148WS", x0, y0+20.32,
            footprint="ducktop2:D_SOD-323_JSCJ_1N4148WS",
            extra_props={"Manufacturer": diode_manufacturer, "MPN": diode_mpn,
                         "LCSC": "C2128", "JLCPCB Part #": "C2128"},
            pin_nets={
                "1": (key_node, "none"),
                "2": (f"KB_ROW{row}", "local"),
            })
    x = switch['1'][0] - 5.08
    a, b = (x,switch['1'][1]), (x,diode['1'][1])
    s.wire(switch['1'], a)
    s.wire(a, b)
    s.wire(b, diode['1'])
    s.label(*b, key_node, angle=90, justify='left')
    s.body[-1] = s.body[-1].replace('(size 1.27 1.27)', '(size 1 1)')


def build(sheet_symbol_uuid):
    s = KeyboardSheet(f"/{sheet_symbol_uuid}")
    s.refcounters["#PWR"] = 320
    s.refcounters["#FLG"] = 320

    s.text(20, 12.7, "== Ducktop2 MX ULP keyboard daughterboard ==")
    s.text(20, 20.32, "65-key compact laptop-style layout, Cherry MX Ultra Low Profile tactile switches, one diode per key.")
    s.text(20, 27.94, "RGB revision: same 273.5 x 80.0 mm outline, key positions and active matrix contacts.")
    s.text(20, 35.56, "This sheet is the keyboard PCB itself: switches, matrix diodes, EC FFC, and bring-up notes.")

    s.text(20, 55.88, "== 5x14 switch matrix, diode direction locked for EC firmware ==")
    s.text(20, 63.5, "Scan assumption: EC drives one column low at a time and reads rows with pull-ups. Each key path is ROW -> diode anode -> diode cathode -> switch -> COL.")
    for idx, key in enumerate(iter_keys()):
        add_key_cell(s, idx, *key)

    s.text(20, 335.28, "== J320 keyboard FFC / board-to-board connector ==")
    s.place("J320", "Conn_01x30_FFC_MP", "Keyboard FFC: MX ULP 5x14 matrix on 30-pin EC contract", 165, 400,
            footprint=FOOTPRINTS["Conn_01x30_FFC"],
            pin_nets={**keyboard_connector_nets(), "MP": ("", "nc")},
            extra_props={"Manufacturer": "Hirose", "MPN": "FH12-30S-0.5SH(55)",
                         "LCSC": "C506793", "JLCPCB Part #": "C506793",
                         "Assembly": "connector MP hold-downs are mechanical and netless"})

    s.gnd(420, 450)
    s.pwrflag(420, 460, "GND")
    s.text(20, 482.6, "NOTES:")
    s.text(20, 490.22, "Use CHERRY MX6C-T3NB tactile switches. The five MP fixation lands connect to GND per CHERRY PCB-reference-design; pins 1/2 form the matrix.")
    s.text(20, 497.84, "D320-D384 are JSCJ 1N4148WS, SOD-323, C2128. Pin 2 is anode on KB_ROWn; pin 1 is cathode at the per-key switch node.")
    s.text(20, 505.46, "J320 mirrors mainboard J310. Fit mainboard R387 for the RGB I2C buffer; keep R386 absent so the 5 V current limit cannot be bypassed.")
    s.text(20, 513.08, "Fit LEDs and support parts before the MX ULP switches. Follow CHERRY's assembly process and check a first article.")
    s.text(20, 520.7, "The split space layout is unchanged. Check the large keycaps and stabilizers with the actual switch/plate stack.")
    s.text(20, 528.32, "Legends/keycaps are mechanical deliverables: prototype blank resin/MJF caps and clip coupons before final legends or stabilizer bars.")

    add_rgb(s, list(iter_keys()))
    return s
