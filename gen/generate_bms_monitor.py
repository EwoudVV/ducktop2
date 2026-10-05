"""Three-cell monitor, high-side power path and service connections."""
import build_ducktop2 as b
from generate_mu_carrier_sheet import place_bms_control_connector, place_bms_power_connector

RAW = 'PACK_NEG_RAW'
REG = 'BQ_REG1'
RFP = 'Resistor_SMD:R_0603_1608Metric'
CFP = 'Capacitor_SMD:C_0603_1608Metric'


def part(s, ref, symbol, value, x, y, footprint, nets, mpn, maker='Texas Instruments', **kw):
    fields = kw.pop('extra_props', {})
    return s.place(ref, symbol, value, x, y, footprint=footprint,
                   pin_nets={p: ((n, 'local') if n else ('', 'nc')) for p, n in nets.items()},
                   extra_props={'Manufacturer': maker, 'MPN': mpn, **fields}, **kw)


def resistor(s, ref, value, x, y, first, second, mpn, fp=RFP, maker='Yageo', **kw):
    return part(s, ref, 'R', value, x, y, fp, {'1': first, '2': second}, mpn, maker, **kw)


def capacitor(s, ref, value, x, y, first, second, mpn, fp=CFP, maker='Murata'):
    return part(s, ref, 'C', value, x, y, fp, {'1': first, '2': second}, mpn, maker)


def add_bms_monitor(s):
    s.text(20, 20, '== three-cell BMS: high-side protection, cell monitoring and independent inhibits ==')
    s.text(20, 30, '8 A discharge / 3 A charge design targets; installed current, startup and temperature limits need bench verification.')
    s.text(20, 40, 'Leave the three drive-release links open until configuration and fault tests pass.')

    part(s, 'F1', 'Fuse', '10A fast pack fuse', 170, 60,
         'ducktop2:Schurter_HCF_8.05x5mm', {'1': 'PACK_POS_RAW', '2': 'BAT_PROT_VIN'},
         '3-101-051', 'SCHURTER', datasheet='https://www.schurter.com/en/datasheet/typ_HCF.pdf')
    part(s, 'J2', 'Conn_01x02', 'raw pack power: 1 negative, 2 positive', 170, 85,
         'ducktop2:WAGO_2060_452_SMD', {'1': RAW, '2': 'PACK_POS_RAW'},
         '2060-452/998-404', 'WAGO')
    part(s, 'J2201', 'Conn_01x02_MP', 'cell taps: 1 cell 1, 2 cell 2', 170, 115,
         'Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal',
         {'1': 'CELL1_TAP', '2': 'CELL2_TAP', 'MP': RAW}, 'SM02B-GHS-TB(LF)(SN)', 'JST')

    # TI requires physical cells 1, 2 and 5 for a three-cell stack.
    monitor_pins = {
        '1': 'BQ_BAT', '2': 'BQ_VC5', '3': 'BQ_VC2', '4': 'BQ_VC2',
        '5': 'BQ_VC2', '6': 'BQ_VC2', '7': 'BQ_VC2', '8': 'BQ_VC1',
        '9': 'BQ_VC0', '10': RAW, '11': 'BMS_SRP', '12': 'BMS_SRN',
        '13': 'BQ_TS1', '14': 'BQ_WAKE', '15': 'BQ_REG18', '16': 'BQ_ALERT_AWAKE',
        '17': 'BMS_RAW_SCL', '18': 'BMS_RAW_SDA', '19': 'BMS_CFETOFF',
        '20': 'BMS_DFETOFF', '21': 'BQ_RST_SHUT', '22': REG,
        '23': 'BQ_REGIN', '24': 'BQ_REGIN', '25': '', '26': 'BQ_PDSG',
        '27': '', '28': 'BQ_LD', '29': 'BQ_PACK', '30': 'BQ_DSG',
        '31': 'BQ_CHG', '32': 'BQ_CP1', '33': RAW,
    }
    part(s, 'U719', 'BQ76922RSN', 'BQ76922RSNR three-cell monitor and protector', 80, 100,
         'ducktop2:TI_RSN0032B_WQFN32_4x4mm', monitor_pins, 'BQ76922RSNR',
         datasheet='https://www.ti.com/lit/ds/symlink/bq76922.pdf')

    part(s, 'D840', 'D_Schottky', 'BAT54WS BAT supply reverse block', 20, 65,
         'Diode_SMD:D_SOD-323', {'1': 'BQ_BAT_FEED', '2': 'PACK_POS_RAW'},
         'BAT54WS-7-F', 'Diodes Incorporated')
    resistor(s, 'R840', '100R BAT input filter', 20, 80, 'BQ_BAT_FEED', 'BQ_BAT', 'RC0603FR-07100RL')
    capacitor(s, 'C840', '1u 25V BAT supply', 20, 95, 'BQ_BAT', RAW, 'GRM188R71E105KA12D')
    capacitor(s, 'C841', '1u 10V REG18', 20, 110, 'BQ_REG18', RAW, 'GRM188R71A105KA61D')
    capacitor(s, 'C845', '4.7u 10V REG1; effective >=1u', 20, 125, REG, RAW,
              'GRM21BR71A475KA73L', 'Capacitor_SMD:C_0805_2012Metric')

    for i, (raw, filtered) in enumerate([(RAW, 'BQ_VC0'), ('CELL1_TAP', 'BQ_VC1'),
                                       ('CELL2_TAP', 'BQ_VC2'), ('PACK_POS_RAW', 'BQ_VC5')]):
        resistor(s, f'R{841+i}', '75R 1% cell input/balance filter', 230, 55+i*15,
                 raw, filtered, 'RC0603FR-0775RL')
    for i, (upper, lower) in enumerate([('BQ_VC0', RAW), ('BQ_VC1', 'BQ_VC0'),
                                      ('BQ_VC2', 'BQ_VC1'), ('BQ_VC5', 'BQ_VC2')]):
        capacitor(s, f'C{842+i+10}', '220n 50V cell filter', 285, 55+i*15,
                  upper, lower, 'GRM188R71H224KA93D')

    part(s, 'RS11', 'BMS_Shunt4', '2mOhm 1% 6W four-terminal pack shunt', 20, 170,
         'ducktop2:Bourns_CSS4J_4026_Kelvin',
         {'1': RAW, '2': 'FG_VSS', '3': 'BMS_RAW_KELVIN', '4': 'BMS_FG_KELVIN'},
         'CSS4J-4026K-2L00F', 'Bourns', extra_props={'Height':'2.93 mm'}, datasheet='https://www.bourns.com/docs/product-datasheets/css4j-4026.pdf')
    resistor(s, 'R845', '100R SRP filter', 20, 190, 'BMS_RAW_KELVIN', 'BMS_SRP', 'RC0603FR-07100RL')
    resistor(s, 'R846', '100R SRN filter', 20, 205, 'BMS_FG_KELVIN', 'BMS_SRN', 'RC0603FR-07100RL')
    capacitor(s, 'C846', '100n 50V differential current filter', 20, 220,
              'BMS_SRP', 'BMS_SRN', 'GRM188R71H104KA93D')

    # Separate raw-side bias for REGIN. REG0 stays disabled in the profile.
    for ref, y in [('R880', 155), ('R881', 175)]:
        resistor(s, ref, '430R 1% 1.5W REGIN supply limiter', 230, y,
                 'PACK_POS_RAW', 'BQ_REGIN_FEED', 'CRCW2512430RFKEGHP',
                 'Resistor_SMD:R_2512_6332Metric', 'Vishay')
    part(s, 'U708', 'TPS70950DBV', 'TPS70950DBVR REGIN supply', 280, 175,
         'Package_TO_SOT_SMD:SOT-23-5',
         {'1': 'BQ_REGIN_FEED', '2': RAW, '3': '', '4': '', '5': 'BQ_REGIN'}, 'TPS70950DBVR')
    capacitor(s, 'C880', '1u 50V REGIN input', 230, 195, 'BQ_REGIN_FEED', RAW,
              'GRM21BR71H105KA12L', 'Capacitor_SMD:C_0805_2012Metric')
    capacitor(s, 'C881', '10u 25V REGIN; effective >=2u', 280, 195, 'BQ_REGIN', RAW,
              'GRM21BZ71E106KE15L', 'Capacitor_SMD:C_0805_2012Metric')
    resistor(s, 'R882', '100k reset default-low', 320, 185, 'BQ_RST_SHUT', RAW, 'RC0603FR-07100KL')
    # TS1 is disabled in the initial profile; the three external windows protect cells.
    resistor(s, 'R883', '10k TS1 termination', 320, 200, 'BQ_TS1', RAW, 'RC0603FR-0710KL')

    place_bms_control_connector(s, 'bms', 490, 250, 'local')
    place_bms_power_connector(s, 'bms', 560, 250, 'local')
    for i, net in enumerate(['PACK_POS_RAW', 'BAT_PROT_VIN', RAW,
                            'FG_VSS', 'BQ_BAT', 'BQ_REGIN_FEED', 'MCU_3V3']):
        s.pwrflag(20+i*25, 265, net)
    s.text(450, 290, 'CTRL_GND stays isolated from RAW and FG. All external pack current crosses RS11 and the center gauge shunt.')
    for i, net in enumerate(['PACK_POS_RAW', 'BAT_PROT_VIN', 'PACK_POS_FUSED',
                            'BAT_PROT_FET_COMMON', RAW, 'FG_VSS', 'BQ_BAT', 'BQ_WAKE',
                            'BQ_RST_SHUT', REG, 'BMS_SRP', 'BMS_SRN',
                            'BMS_RAW_SCL', 'BMS_RAW_SDA', 'BQ_ALERT_AWAKE', 'BQ_REGIN']):
        part(s, f'TPB{i+1}', 'TestPoint', net, 600+i%4*40, 60+i//4*20,
             'TestPoint:TestPoint_Pad_D1.0mm', {'1': net}, '-', '-', in_bom=False)
    s.text(565, 165, 'Raw service pads: use an isolated programmer. Do not attach system-ground equipment across either shunt.')
