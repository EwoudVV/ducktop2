"""Independent current trips and the startup permission hold."""
from generate_bms_monitor import RAW, REG, part, resistor, capacitor


def add_bms_guards(s):
    s.text(725, 290, '== current guards: signed low-side sense, hardware latches ==')
    part(s, 'U2213', 'REF3425DBV', 'REF3425IDBVR current-trip reference', 780, 335,
         'Package_TO_SOT_SMD:SOT-23-6',
         {'1': RAW, '2': RAW, '3': REG, '4': REG, '5': 'BMS_CURRENT_REF', '6': 'BMS_CURRENT_REF'},
         'REF3425IDBVR')
    capacitor(s, 'C2272', '1u 10V reference input', 740, 365, REG, RAW, 'GRM188R71A105KA61D')
    capacitor(s, 'C2273', '1u 10V reference output', 780, 365,
              'BMS_CURRENT_REF', RAW, 'GRM188R71A105KA61D')
    capacitor(s, 'C2280', '100n 50V reference output', 790, 380,
              'BMS_CURRENT_REF', RAW, 'GRM188R71H104KA93D')
    for ref, symbol, kind, x, plus, minus in [
        ('U2210', 'INA381A3DGS', 'DSG', 860, 'BMS_FG_KELVIN', 'BMS_RAW_KELVIN'),
        ('U2211', 'INA381A4DGS', 'CHG', 970, 'BMS_RAW_KELVIN', 'BMS_FG_KELVIN'),
    ]:
        part(s, ref, symbol, ('INA381A3IDGSR discharge' if kind=='DSG' else 'INA381A4IDGSR charge')+' current latch',
             x, 335, 'Package_SO:MSOP-10_3x3mm_P0.5mm',
             {'1': f'BMS_OC_{kind}_IN_P', '2': REG, '3': f'THERM_{kind}_HEALTH',
              '4': 'CURRENT_READY', '5': RAW, '6': '', '7': f'BMS_OC_{kind}_LIMIT',
              '8': f'BMS_OC_{kind}_OUT', '9': f'BMS_OC_{kind}_OUT', '10': f'BMS_OC_{kind}_IN_N'},
             'INA381A3IDGSR' if kind=='DSG' else 'INA381A4IDGSR')
        base = 2280 if kind=='DSG' else 2282
        for offset, source, suffix in [(0, plus, 'P'), (1, minus, 'N')]:
            resistor(s, f'R{base+offset}', '4.99R 0.1% 25ppm sense filter', x-40, 385+offset*15,
                     source, f'BMS_OC_{kind}_IN_{suffix}', 'TNPW06034R99BEEA', maker='Vishay')
        capacitor(s, 'C2270' if kind=='DSG' else 'C2271', '10n 50V C0G differential filter', x, 385,
                  f'BMS_OC_{kind}_IN_P', f'BMS_OC_{kind}_IN_N', 'GRM1885C1H103JA01J')
        capacitor(s, 'C2274' if kind=='DSG' else 'C2275', '100n 50V current guard supply', x+40, 385,
                  REG, RAW, 'GRM188R71H104KA93D')
    for ref, value, top, bottom, mpn, x, y in [
        ('R2270', '10.2k', 'BMS_CURRENT_REF', 'BMS_OC_DSG_LIMIT', 'TNPW060310K2BEEA', 850, 430),
        ('R2271', '26.7k', 'BMS_OC_DSG_LIMIT', RAW, 'TNPW060326K7BEEA', 850, 445),
        ('R2272', '16.9k', 'BMS_CURRENT_REF', 'BMS_OC_CHG_LIMIT', 'TNPW060316K9BEEA', 965, 430),
        ('R2273', '31.6k', 'BMS_OC_CHG_LIMIT', RAW, 'TNPW060331K6BEEA', 965, 445),
    ]:
        resistor(s, ref, value+' 0.1% 25ppm current limit', x, y, top, bottom, mpn, maker='Vishay')
    capacitor(s, 'C2276', '10n 50V current reference filter', 890, 460,
              'BMS_OC_DSG_LIMIT', RAW, 'GRM188R71H103KA01D')
    capacitor(s, 'C2277', '10n 50V current reference filter', 995, 460,
              'BMS_OC_CHG_LIMIT', RAW, 'GRM188R71H103KA01D')

    part(s, 'U2214', 'TPS3808G30DBV', 'TPS3808G30DBVR current startup hold', 780, 490,
         'Package_TO_SOT_SMD:SOT-23-6',
         {'1': 'CURRENT_READY', '2': RAW, '3': 'CURRENT_CLR_N', '4': 'CURRENT_DELAY', '5': REG, '6': REG},
         'TPS3808G30DBVR')
    resistor(s, 'R2274', '10k current-ready pull-up', 725, 525, REG, 'CURRENT_READY', 'RC0603FR-0710KL')
    resistor(s, 'R2275', '100k current-ready default-low', 780, 525, 'CURRENT_READY', RAW, 'RC0603FR-07100KL')
    resistor(s, 'R2276', '100k current reset pull-up', 725, 545, REG, 'CURRENT_CLR_N', 'RC0603FR-07100KL')
    resistor(s, 'R2277', '100k 180..420ms current hold', 780, 545, REG, 'CURRENT_DELAY', 'RC0603FR-07100KL')
    capacitor(s, 'C2278', '100n 50V current supervisor supply', 780, 565, REG, RAW, 'GRM188R71H104KA93D')
    part(s, 'U2215', '74LVC1G08', 'SN74LVC1G08DBVR temperature/current readiness', 870, 510,
         'Package_TO_SOT_SMD:SOT-23-5',
         {'1': 'THERM_READY', '2': 'CURRENT_READY', '3': RAW,
          '4': 'BMS_PERMIT_READY', '5': 'THERM_3V3'}, 'SN74LVC1G08DBVR')
    capacitor(s, 'C2279', '100n 50V readiness logic supply', 875, 545,
              'THERM_3V3', RAW, 'GRM188R71H104KA93D')
    resistor(s, 'R2278', '100k permission default-low', 925, 545, 'BMS_PERMIT_READY', RAW, 'RC0603FR-07100KL')
    for ref, net, x in [('TPB33', 'CURRENT_READY', 850), ('TPB34', 'CURRENT_CLR_N', 900),
                        ('TPB35', 'BMS_CURRENT_REF', 950)]:
        part(s, ref, 'TestPoint', net, x, 585, 'TestPoint:TestPoint_Pad_D1.0mm', {'1': net}, '-', '-', in_bom=False)
    s.text(725, 610, 'Nominal trips: about9.1A discharge and4.1A charge. These are fault trips, not operating ratings.')
    s.text(725, 620, 'CLR is a raw-side service input. The five-wire control harness does not reset these latches.')
