"""Parts, pin maps and key assignments for the RGB keyboard."""

LED_MPN = '19-337/R6GHBHC-C02/2T'
LED_LCSC = 'C409504'
LED_DATASHEET = 'https://www.endrich.com/Datenbl%C3%A4tter/Lichtl%C3%B6sungen/Everlight/RGB%20LED/19-337R6GHBHC-C022T.pdf'
LED_FOOTPRINT = 'ducktop2:LED_Everlight_19-337_1616'
DRIVER_MPN = 'IS31FL3743A-QULS4-TR'
DRIVER_DATASHEET = 'https://www.lumissil.com/assets/pdf/core/IS31FL3743A_DS.pdf'
DRIVER_FOOTPRINT = 'ducktop2:IS31FL3743A_UQFN40'
BUFFER_MPN = 'TCA9517ADGKR'
BUFFER_DATASHEET = 'https://www.ti.com/lit/ds/symlink/tca9517a.pdf'
BUFFER_FOOTPRINT = 'Package_SO:VSSOP-8_3x3mm_P0.65mm'
DRIVER_ADDRESS = 0x2f  # ADDR1 and ADDR2 tied to the driver's VCC.
ISET_OHMS = 33200
LED_OFFSET_MM = (0.0, -2.8)  # CHERRY VS-10107 rev 03 / pcb-mx-ulp.dxf.
ROW_COUNTS = (14, 14, 13, 13, 11)
COPPER_LAYERS = 4

DRIVER_PINS = {
    1:'RGB_SW08', 2:'RGB_SW06', 3:'RGB_SW04', 4:'RGB_SW02', 5:'KB_RGB_5V',
    6:'RGB_SW01', 7:'RGB_SW03', 8:'RGB_SW05', 9:'RGB_SW07', 10:'RGB_SW09',
    11:'RGB_SW11', 12:'RGB_CS18', 13:'RGB_CS17', 14:'RGB_CS16', 15:'RGB_CS15',
    16:'GND', 17:'RGB_CS14', 18:'RGB_CS13', 19:'RGB_CS12', 20:'RGB_CS11',
    21:'RGB_CS10', 22:'KB_RGB_5V', 23:'GND', 24:'KB_RGB_5V', 25:'KB_RGB_5V',
    26:'RGB_SDB', 27:'RGB_SCL', 28:'RGB_SDA', 29:'RGB_ISET',
    30:None, 31:'RGB_CS09', 32:'RGB_CS08', 33:'RGB_CS07', 34:'RGB_CS06',
    35:'RGB_CS05', 36:'RGB_CS04', 37:'RGB_CS03', 38:'RGB_CS02',
    39:'RGB_CS01', 40:'RGB_SW10', 41:'GND',
}


def key_assignments():
    """Six neighbouring keys per scan bank, following alternate row directions."""
    order, offset = [], 0
    for row, count in enumerate(ROW_COUNTS):
        indices = list(range(offset, offset+count))
        order.extend(indices if row % 2 == 0 else reversed(indices))
        offset += count
    return {index: {'bank': n//6+1, 'slot': n%6,
                    'registers': [n//6*18+n%6*3+c+1 for c in range(3)]}
            for n,index in enumerate(order)}


def led_nets(index):
    assignment = key_assignments()[index]
    bank, slot = assignment['bank'], assignment['slot']
    red, green, blue = slot*3+1, slot*3+2, slot*3+3
    common = f'RGB_SW{bank:02d}'
    # Everlight top view: B anode/cathode 1/2, R 3/4, G 5/6.
    return {'1':common, '2':f'RGB_CS{blue:02d}', '3':common,
            '4':f'RGB_RED{red:02d}', '5':common, '6':f'RGB_CS{green:02d}'}


def write_firmware_map(path):
    rows=['#ifndef DUCKTOP2_KEYBOARD_RGB_MAP_H', '#define DUCKTOP2_KEYBOARD_RGB_MAP_H',
          '#include <stdint.h>', '#define KEYBOARD_RGB_KEYS 65u',
          '#define KEYBOARD_RGB_CHANNELS 198u', '#define KEYBOARD_RGB_BANKS 11u',
          '#define KEYBOARD_RGB_ADDRESS 0x2fu',
          '/* PWM register numbers, R/G/B, in the existing switch-reference order. */',
          'static const uint8_t keyboard_rgb_map[65][3] = {']
    for index,assignment in sorted(key_assignments().items()):
        rows.append('    {'+', '.join(str(n)+'u' for n in assignment['registers'])+
                    '}, /* SW'+str(320+index)+' */')
    rows += ['};', '#endif', '']
    path.write_text('\n'.join(rows))
