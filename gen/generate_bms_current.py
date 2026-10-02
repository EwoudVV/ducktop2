"""Draft current guards; startup and fault recovery still need revision.

The static trip checks do not qualify this circuit for assembly or operation.
"""

RAW = 'PACK_NEG_RAW'
BIAS = 'THERM_3V3'
RFP = 'Resistor_SMD:R_0603_1608Metric'
CFP = 'Capacitor_SMD:C_0603_1608Metric'


def add_bms_current(s):
    """Add the current guards after add_bms_thermal(s).

    This expects the separately documented changes to RS10, RS11, R2232,
    U2206 and R854. R850 retains the UV-recovery value. Neither guard connects to FG_VSS or CTRL_GND.
    """
    def part(ref, symbol, value, x, y, footprint, nets, mpn,
             manufacturer='Texas Instruments', datasheet=''):
        return s.place(
            ref, symbol, value, x, y, footprint=footprint,
            pin_nets={pin: ((net, 'local') if net else ('', 'nc'))
                      for pin, net in nets.items()},
            extra_props={'Manufacturer': manufacturer, 'MPN': mpn},
            datasheet=datasheet,
        )

    def resistor(ref, value, x, y, a, z, mpn, manufacturer='Yageo'):
        datasheet = ('https://www.vishay.com/docs/28758/tnpw_e3.pdf'
                     if manufacturer == 'Vishay' else '')
        return part(ref, 'R', value, x, y, RFP, {'1': a, '2': z},
                    mpn, manufacturer, datasheet)

    s.text(805, 290, '== current guards: raw reference, latched hardware permits ==')
    for ref, kind, x, inp, inn in (
        ('U2210', 'DSG', 850, 'BAT_PROT_SENSE', 'PACK_POS_FUSED'),
        ('U2211', 'CHG', 960, 'PACK_POS_FUSED', 'BAT_PROT_SENSE'),
    ):
        part(ref, 'INA300AIDGS', f'INA300AIDGSR {kind} current guard', x, 330,
             'Package_SO:MSOP-10_3x3mm_P0.5mm',
             {'1': inp, '2': inn, '3': f'BMS_OC_{kind}_LIMIT', '4': BIAS,
              '5': f'THERM_{kind}_HEALTH', '6': 'THERM_READY', '7': BIAS,
              '8': RAW, '9': BIAS, '10': ''}, 'INA300AIDGSR',
             datasheet='https://www.ti.com/lit/ds/symlink/ina300.pdf')
    # 1k +360R uses stocked values to make1.36k without a special-value order.
    resistor('R2270', '1k 0.1% 25ppm discharge limit', 820, 375,
             'BMS_OC_DSG_LIMIT', 'BMS_OC_DSG_LIMIT_MID', 'TNPW06031K00BEEA', 'Vishay')
    resistor('R2271', '360R 0.1% 25ppm discharge limit', 820, 390,
             'BMS_OC_DSG_LIMIT_MID', RAW, 'TNPW0603360RBEEA', 'Vishay')
    resistor('R2272', '562R 0.1% 25ppm charge limit', 960, 375,
             'BMS_OC_CHG_LIMIT', RAW, 'TNPW0603562RBEEA', 'Vishay')
    for ref, x in (('C2270', 850), ('C2271', 990)):
        part(ref, 'C', '100n 50V current guard supply', x, 405, CFP,
             {'1': BIAS, '2': RAW}, 'GRM188R71H104KA93D', 'Murata',
             'https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H104KA93D')

    resistor('R2273', '1k raw retry gate series', 850, 435,
             'RAW_RETRY', 'RAW_RETRY_GATE', 'RC0603FR-071KL')
    resistor('R2274', '100k raw retry default-off', 850, 450,
             'RAW_RETRY_GATE', RAW, 'RC0603FR-07100KL')
    part('Q2210', 'Q_NMOS_SOT23_GSD', 'BSS138 raw current-latch reset', 900, 445,
         'Package_TO_SOT_SMD:SOT-23',
         {'1': 'RAW_RETRY_GATE', '2': RAW, '3': 'THERM_READY'},
         'BSS138LT1G', 'onsemi', 'https://www.onsemi.com/pdf/datasheet/bss138-d.pdf')

    # A defined off-state bias for the downstream shunt input common mode.
    # This permits a small, documented current around the high-side switch.
    resistor('R2275', '47k fused input to shunt common-mode bias', 1010, 445,
             'BAT_PROT_VIN', 'BAT_PROT_SENSE', 'RC0603FR-0747KL')
    s.text(805, 480, 'Both guards use100us response and2mV hysteresis; limits are trips, not operating ratings.')
    s.text(805, 490, 'Retry holds both BQ permits off and clears the latches; raw startup supervision remains active.')
    s.text(805, 500, 'R2275 allows less than0.3mA high-side-off leakage at12.6V; no raw-ground bypass is added.')
