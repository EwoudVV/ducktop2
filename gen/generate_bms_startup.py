"""High-side charge/discharge FETs and the current-limited startup branch."""
from generate_bms_monitor import RAW, REG, part, resistor, capacitor
from build_ducktop2 import FOOTPRINTS


def add_bms_startup(s):
    fp = FOOTPRINTS['Q_CSD18540Q5B']
    for ref, source, gate, x in [('Q11', 'BAT_PROT_VIN', 'CHG_GATE', 380),
                                ('Q12', 'PACK_POS_FUSED', 'DSG_GATE', 470)]:
        part(s, ref, 'Q_NMOS_123S_4G_5678D', 'CSD18540Q5B high-side '+('charge' if ref=='Q11' else 'discharge'),
             x, 65, fp, {'1': source, '2': source, '3': source,
                         '4': gate, '5': 'BAT_PROT_FET_COMMON'}, 'CSD18540Q5B')
        kind = 'CHG' if ref=='Q11' else 'DSG'
        i = 0 if kind=='CHG' else 1
        resistor(s, f'R{870+i}', 'DNP 0R drive release', x, 90,
                 'BQ_'+kind, kind+'_DRV_RELEASED', 'RC0603JR-070RL', dnp=True)
        resistor(s, f'R{847+i}', '100R gate series', x, 105,
                 kind+'_DRV_RELEASED', gate, 'RC0603FR-07100RL')
        resistor(s, f'R{849+i}', '1M gate-source', x, 120, gate, source, 'RC0603FR-071ML')
        part(s, f'D{847+i}', 'D_Zener', 'BZT52C15 gate-source clamp', x+45, 115,
             'Diode_SMD:D_SOD-123', {'1': gate, '2': source}, 'BZT52C15-7-F', 'Diodes Incorporated')

    capacitor(s, 'C724', '470n 25V CP1; effective >=100n at11V', 390, 145,
              'BQ_CP1', 'BQ_BAT', 'GRM188R71E474KA12D')
    resistor(s, 'R851', '10k PACK sense', 470, 140, 'PACK_POS_FUSED', 'BQ_PACK', 'RC0603FR-0710KL')
    resistor(s, 'R852', '10k LD sense', 470, 155, 'PACK_POS_FUSED', 'BQ_LD', 'RC0603FR-0710KL')

    s.text(375, 185, '== startup branch: active current limit, thermal latch-off ==')
    s.text(375, 195, 'PDSG timeout stays0; only voltage completion may enable the main DSG path.')
    part(s, 'U2218', 'TPS26600PWP', 'TPS26600PWPR latched startup current limit', 440, 240,
         'ducktop2:HTSSOP16_EP_ThermalVias',
         {'1': 'BAT_PROT_VIN', '2': 'BAT_PROT_VIN', '3': 'PDSG_UVLO', '4': '',
          '5': 'PDSG_RTN', '6': 'PDSG_MODE', '7': 'PDSG_SHDN', '8': 'PDSG_RTN',
          '9': RAW, '10': '', '11': 'PDSG_ILIM', '12': 'PDSG_DVDT', '13': '',
          '14': 'PDSG_FLT_N', '15': 'PACK_POS_FUSED', '16': 'PACK_POS_FUSED',
          '17': 'PDSG_RTN'}, 'TPS26600PWPR')
    resistor(s, 'R884', '100k UVLO top', 355, 225, 'BAT_PROT_VIN', 'PDSG_UVLO', 'RC0603FR-07100KL')
    resistor(s, 'R885', '24.9k UVLO bottom', 355, 240, 'PDSG_UVLO', 'PDSG_RTN', 'RC0603FR-0724K9L')
    resistor(s, 'R886', '402k latched current-limit mode', 355, 255, 'PDSG_MODE', 'PDSG_RTN', 'RC0603FR-07402KL')
    for ref, value, mpn, y in [('R887', '12k 0.1% 25ppm ILIM', 'TNPW060312K0BEEN', 270),
                               ('R888', '24k 0.1% 25ppm ILIM', 'TNPW060324K0BEEN', 285)]:
        resistor(s, ref, value, 355, y, 'PDSG_ILIM', 'PDSG_RTN', mpn, maker='Vishay')
    capacitor(s, 'C882', '100n 25V C0G startup ramp', 355, 305,
              'PDSG_DVDT', 'PDSG_RTN', 'C1206C104F3GECAUTO',
              'Capacitor_SMD:C_1206_3216Metric', 'KEMET')
    capacitor(s, 'C883', '1u 50V startup input', 440, 290, 'BAT_PROT_VIN', RAW,
              'GRM21BR71H105KA12L', 'Capacitor_SMD:C_0805_2012Metric')
    capacitor(s, 'C884', '220n 50V startup output; effective >=100n', 485, 290,
              'PACK_POS_FUSED', 'FG_VSS', 'GRM188R71H224KA93D')
    resistor(s, 'R889', '100k startup fault pull-up', 485, 315,
             REG, 'PDSG_FLT_N', 'RC0603FR-07100KL')
    s.pwrflag(330, 325, 'PDSG_RTN')
    s.text(355, 345, 'PDSG_RTN is the local eFuse reference. Do not bond it to RAW, FG, CTRL or a mounting hole.')

    part(s, 'Q2211', 'Q_PMOS_GSD', 'ZXMP6A13FTA PDSG signal translator', 540, 220,
         'Package_TO_SOT_SMD:SOT-23',
         {'1': 'PDSG_CTRL_GATE', '2': 'BQ_BAT', '3': 'PDSG_CTRL_HIGH'},
         'ZXMP6A13FTA', 'Diodes Incorporated')
    resistor(s, 'R890', '1k PDSG translator gate', 525, 195, 'BQ_PDSG', 'PDSG_CTRL_GATE', 'RC0603FR-071KL')
    resistor(s, 'R891', '1M translator gate-source', 565, 195, 'PDSG_CTRL_GATE', 'BQ_BAT', 'RC0603FR-071ML')
    resistor(s, 'R872', 'DNP 0R startup drive release', 555, 245,
             'PDSG_CTRL_HIGH', 'PDSG_CTRL_RELEASED', 'RC0603JR-070RL', dnp=True)
    resistor(s, 'R892', '100k startup shutdown top', 555, 265,
             'PDSG_CTRL_RELEASED', 'PDSG_SHDN_DRIVE', 'RC0603FR-07100KL')
    part(s, 'Q2212', 'Q_NMOS_SOT23_GSD', 'BSS138 independent discharge inhibit', 590, 290,
         'Package_TO_SOT_SMD:SOT-23',
         {'1': 'PDSG_PERMIT_GATE', '2': 'PDSG_SHDN', '3': 'PDSG_SHDN_DRIVE'},
         'BSS138LT1G', 'onsemi')
    resistor(s, 'R893', '33.2k startup shutdown default-low', 600, 310,
             'PDSG_SHDN', 'PDSG_RTN', 'RC0603FR-0733K2L')
    resistor(s, 'R894', '100k startup permit gate series', 600, 330,
             'THERM_DSG_GATE', 'PDSG_PERMIT_GATE', 'RC0603FR-07100KL')
    part(s, 'D849', 'D_Zener', 'BZT52C5V1 startup permit VGS clamp', 655, 330,
         'Diode_SMD:D_SOD-123', {'1': 'PDSG_PERMIT_GATE', '2': 'PDSG_SHDN'},
         'BZT52C5V1-7-F', 'Diodes Incorporated')
    s.text(525, 360, 'The independent discharge permit also covers PDSG; a disabled main FET cannot leave an unchecked bypass.')
    for ref, net, x in [('TPB30', 'PDSG_FLT_N', 565), ('TPB31', 'PDSG_SHDN', 600),
                        ('TPB32', 'PDSG_RTN', 635)]:
        part(s, ref, 'TestPoint', net, x, 380, 'TestPoint:TestPoint_Pad_D1.0mm',
             {'1': net}, '-', '-', in_bom=False)
