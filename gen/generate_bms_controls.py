"""Buffered I2C, monitor readiness and the protected control supply."""
from generate_bms_monitor import RAW, REG, part, resistor, capacitor

CTRL = 'CTRL_GND'
VCC = 'CTRL_3V3'


def add_bms_controls(s):
    s.text(725, 30, '== isolated control interface: I2C and monitor readiness ==')
    part(s, 'U2216', 'TPS22941DCK', 'TPS22941DCKR control supply current limit', 760, 65,
         'Package_TO_SOT_SMD:SOT-353_SC-70-5',
         {'1': VCC, '2': CTRL, '3': 'PACK_MONITOR_READY', '4': CTRL, '5': 'MCU_3V3'},
         'TPS22941DCKR')
    capacitor(s, 'C2257', '1u 10V control input', 725, 95, 'MCU_3V3', CTRL, 'GRM188R71A105KA61D')
    capacitor(s, 'C2258', '1u 10V control output', 775, 95, VCC, CTRL, 'GRM188R71A105KA61D')
    s.pwrflag(720, 110, CTRL)

    part(s, 'U2206', 'ISO1640BD', 'ISO1640BDR BQ I2C isolation', 880, 75,
         'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
         {'1': VCC, '2': 'ISO_CTRL_SDA', '3': 'ISO_CTRL_SCL', '4': CTRL,
          '5': RAW, '6': 'BMS_RAW_SCL', '7': 'BMS_RAW_SDA', '8': REG}, 'ISO1640BDR')
    for ref, rail, gnd, x in [('C2250', REG, RAW, 850), ('C2251', VCC, CTRL, 905)]:
        capacitor(s, ref, '100n 50V I2C isolator supply', x, 105, rail, gnd, 'GRM188R71H104KA93D')
    part(s, 'U2207', 'TCA9517A', 'TCA9517AIDGKR isolated-bus buffer', 980, 75,
         'Package_SO:VSSOP-8_3x3mm_P0.65mm',
         {'1': VCC, '2': 'ISO_CTRL_SCL', '3': 'ISO_CTRL_SDA', '4': CTRL,
          '5': VCC, '6': 'PACK_I2C_SDA', '7': 'PACK_I2C_SCL', '8': VCC}, 'TCA9517AIDGKR')
    capacitor(s, 'C2252', '100n 50V bus buffer supply', 980, 105, VCC, CTRL, 'GRM188R71H104KA93D')
    for ref, value, rail, net, mpn, x, y in [
        ('R2260', '4.7k', REG, 'BMS_RAW_SCL', 'RC0603FR-074K7L', 830, 130),
        ('R2261', '4.7k', REG, 'BMS_RAW_SDA', 'RC0603FR-074K7L', 830, 145),
        ('R2262', '2.2k', VCC, 'ISO_CTRL_SCL', 'RC0603FR-072K2L', 900, 130),
        ('R2263', '2.2k', VCC, 'ISO_CTRL_SDA', 'RC0603FR-072K2L', 900, 145),
        ('R2266', '2.2k', VCC, 'PACK_I2C_SCL', 'RC0603FR-072K2L', 980, 130),
        ('R2267', '2.2k', VCC, 'PACK_I2C_SDA', 'RC0603FR-072K2L', 980, 145),
    ]:
        resistor(s, ref, value+' 1% I2C pull-up', x, y, rail, net, mpn)
    s.text(820, 170, 'BQ uses isolator side2. Side1 is a short local bus; the buffer carries the longer harness load.')

    # Readiness reports powered hardware. Fresh I2C status supplies fault detail.
    part(s, 'U2208', '74LVC1G17', 'SN74LVC1G17DBVR raw readiness buffer', 775, 205,
         'Package_TO_SOT_SMD:SOT-23-5',
         {'1': '', '2': 'THERM_READY', '3': RAW, '4': 'BMS_MONITOR_READY_RAW', '5': REG},
         'SN74LVC1G17DBVR')
    capacitor(s, 'C2253', '100n 50V readiness buffer supply', 775, 235, REG, RAW, 'GRM188R71H104KA93D')
    resistor(s, 'R2251', '100k raw health default-low', 775, 250,
             'BMS_MONITOR_READY_RAW', RAW, 'RC0603FR-07100KL')
    part(s, 'U2209', 'ISO7021FD', 'ISO7021FDR readiness isolation; default low', 880, 215,
         'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
         {'1': REG, '2': '', '3': 'BMS_MONITOR_READY_RAW', '4': RAW,
          '5': CTRL, '6': 'CTRL_MONITOR_READY', '7': CTRL, '8': VCC}, 'ISO7021FDR')
    for ref, rail, gnd, x in [('C2255', REG, RAW, 850), ('C2256', VCC, CTRL, 905)]:
        capacitor(s, ref, '100n 50V readiness isolator supply', x, 250, rail, gnd, 'GRM188R71H104KA93D')
    resistor(s, 'R2258', '4.7k readiness output current limit', 960, 210,
             'CTRL_MONITOR_READY', 'PACK_MONITOR_READY', 'RC0603FR-074K7L')
    resistor(s, 'R2255', '100k control health default-low', 960, 230,
             'PACK_MONITOR_READY', CTRL, 'RC0603FR-07100KL')
    s.text(730, 265, 'High readiness means REG1 and the thermal supervisor are powered. Faults and freshness come from verified I2C samples.')
    s.text(730, 275, 'The control connector supplies only CTRL_GND. Programming and current-clear pads belong to RAW.')
