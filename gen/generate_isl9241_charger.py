"""3S NVDC charger, independent charge permission and Mu throttle output."""
from build_ducktop2 import FOOTPRINTS

HIER = {'I2C_SCL','I2C_SDA','CHG_INT_N','CHG_ENABLE','PACK_CHG_TEMP_OK',
        'PACK_FAULT_N','PACK_POS_FUSED','VSYS','MCU_3V3','CASE_PWRBTN_N',
        'MU_PWRBTN_N','MU_PROCHOT_N','MU_PROCHOT_RELEASE'}


def add_charger(s):
    def net(name):
        return (name, 'nc' if not name else 'hier' if name in HIER else 'local')
    def part(ref,symbol,value,x,y,fp,pins,mpn,maker='Texas Instruments',**props):
        s.place(ref,symbol,value,x,y,footprint=fp,
                pin_nets={str(p):net(n) for p,n in pins.items()},
                extra_props={'Manufacturer':maker,'MPN':mpn,**props})
    def r(ref,value,x,y,a,b,mpn=None,fp=None,maker='Yageo'):
        if mpn:
            part(ref,'R',value,x,y,fp or FOOTPRINTS['R'],{1:a,2:b},mpn,maker)
        else:
            package=fp or FOOTPRINTS['R']
            codes={'100k':'100K','10R':'10R','4.7R':'4R7','0R':'0R',
                   '2R':'2R','100R':'100R','1k':'1K','4.53k':'4K53',
                   '20k':'20K','2.2k':'2K2','10k':'10K','4.7k':'4K7','2.2R':'2R2'}
            code=codes[value.split()[0]]
            order='RC0603'+('JR' if code=='0R' else 'FR')+'-07'+code+'L'
            part(ref,'R',value,x,y,package,{1:a,2:b},order,'Yageo')
    def c(ref,value,x,y,a,b,mpn,fp='C_100n',maker='Murata'):
        part(ref,'C',value,x,y,FOOTPRINTS[fp],{1:a,2:b},mpn,maker)
    def nfet(ref,value,x,y,gate,source,drain,mpn='CSD17577Q3A',fp=None):
        part(ref,'Q_NMOS_123S_4G_5678D',value,x,y,
             fp or 'Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET',
             {1:source,2:source,3:source,4:gate,5:drain},mpn)
    def small_fet(ref,x,y,gate,drain):
        part(ref,'Q_NMOS_SOT23_GSD','BSS138',x,y,FOOTPRINTS['Q_BSS138'],
             {1:gate,2:'GND',3:drain},'BSS138LT1G','onsemi')

    s.text(850,20,'== U2 ISL9241: 3S NVDC charger and system supply ==')
    part('U2','ISL9241','ISL9241IRTZ',930,90,
         'ducktop2:Renesas_L32_4x4D_QFN32_EP2.7',{
            1:'CHG_SRN',2:'VSYS',3:'',4:'BTST2_NODE',5:'CHG_HS2_DRV',
            6:'SW2',7:'CHG_LS2_DRV',8:'CHG_VDDP',9:'CHG_LS1_DRV',
            10:'SW1',11:'CHG_HS1_DRV',12:'BTST1_NODE',13:'CHG_VDDP',
            14:'CHG_INPUT',15:'CHG_CSIP',16:'',17:'CHG_DCIN',18:'REGN',
            19:'PROG_SET',20:'GND',21:'I2C_SDA',22:'I2C_SCL',
            23:'MU_PROCHOT_N',24:'CHG_ACOK',25:'CHG_NTC',26:'CHG_INT_N',
            27:'CHG_COMPR',28:'CHG_COMPF',29:'CHG_IMON',30:'CHG_PSYS',
            31:'BATP_SENSE',32:'CHG_BGATE',33:'GND'},'ISL9241IRTZ','Renesas',
         Datasheet='https://www.renesas.com/en/document/dst/isl9241-datasheet')
    # The same four-switch stage handles 5/9 V boost and 15/20 V buck input.
    for ref,x,gate,source,drain in (
        ('Q2600',850,'CHG_HS1_GATE','SW1','CHG_INPUT'),
        ('Q2601',930,'CHG_LS1_GATE','GND','SW1'),
        ('Q2602',1010,'CHG_LS2_GATE','GND','SW2'),
        ('Q2603',1090,'CHG_HS2_GATE','SW2','VSYS')):
        nfet(ref,'CSD17577Q3A 30V switching FET',x,160,gate,source,drain)
    part('L1','L','2.2uH 20%; 31A Isat30',930,200,
         FOOTPRINTS['L_XGL1060_CENTER'],{1:'SW1',2:'SW2'},'XGL1060-222MEC','Coilcraft')
    part('RS2600','R','20m 1% 2W input Kelvin shunt',850,200,
         'Resistor_SMD:R_2512_6332Metric',{1:'VBUS_COMBINED',2:'CHG_INPUT'},
         'WSLP2512R0200FEA','Vishay Dale')
    part('RS2601','R','10m 1% 2W battery Kelvin shunt',1010,200,
         'Resistor_SMD:R_2512_6332Metric',{1:'VSYS',2:'CHG_SRN'},
         'WSLP2512R0100FEA','Vishay Dale')
    # Source is the battery side. Its body diode allows battery-to-system
    # startup; charging is controlled in the opposite direction by BGATE.
    nfet('Q25','CSD17575Q3 battery power-path FET',1090,210,
         'CHG_BGATE','PACK_POS_FUSED','CHG_SRN','CSD17575Q3',FOOTPRINTS['Q_CSD17575Q3'])
    r('R2600','100k BGATE to source',1090,240,'CHG_BGATE','PACK_POS_FUSED')

    # VDD and VDDP come from the protected adapter or the system rail.
    for ref,x,source in (('D2600',850,'CHG_INPUT'),('D2601',930,'VSYS')):
        part(ref,'D_Schottky','BAT54WS bias OR',x,240,FOOTPRINTS['D_Signal'],
             {1:'CHG_BIAS_OR',2:source},'BAT54WS-7-F','Diodes Incorporated')
    r('R2601','10R DCIN filter',1010,250,'CHG_BIAS_OR','CHG_DCIN')
    c('C2600','4.7u 50V X7R DCIN',1090,260,'CHG_DCIN','GND','GRM31CR71H475KA12L','C_10u')
    c('C9','4.7u 10V X7R VDD',850,275,'REGN','GND','GRM21BR71A475KA73L','C_1u')
    r('R2602','4.7R VDDP filter',930,275,'REGN','CHG_VDDP')
    c('C2601','4.7u 10V X7R VDDP',1010,275,'CHG_VDDP','GND','GRM21BR71A475KA73L','C_1u')
    for ref,x,boot,sw in (('C7',850,'BTST1_NODE','SW1'),('C8',930,'BTST2_NODE','SW2')):
        c(ref,'470n 25V X7R bootstrap',x,295,boot,sw,'C1608X7R1E474K080AE',maker='TDK')
    for index,(driver,gate) in enumerate((('CHG_HS1_DRV','CHG_HS1_GATE'),
          ('CHG_LS1_DRV','CHG_LS1_GATE'),('CHG_LS2_DRV','CHG_LS2_GATE'),
          ('CHG_HS2_DRV','CHG_HS2_GATE'))):
        r('R'+str(2603+index),'0R gate link',850+80*index,315,driver,gate)

    r('R18','2.21k 1% 3S / 724kHz / 200mA startup',850,340,'PROG_SET','GND','RC0603FR-072K21L')
    c('C2602','1n 50V C0G PROG filter',930,340,'PROG_SET','GND','GRM1885C1H102JA01D')
    r('R2607','2R input sense filter',1010,340,'VBUS_COMBINED','CHG_CSIP')
    c('C2603','100n 50V input sense filter',1090,340,'CHG_CSIP','CHG_INPUT','GRM188R71H104KA93D')
    c('C2604','100n 50V battery sense filter',850,360,'VSYS','CHG_SRN','GRM188R71H104KA93D')
    r('R704','100R battery voltage filter',930,360,'PACK_POS_FUSED','BATP_SENSE')
    c('C711','100n 50V battery voltage filter',1010,360,'BATP_SENSE','GND','GRM188R71H104KA93D')
    r('R2608','1k forward compensation',850,385,'CHG_COMPF','CHG_COMPF_RC')
    c('C2605','22n 50V C0G forward compensation',930,385,'CHG_COMPF_RC','GND',
      'C0805C223J5GACTU','C_0805','KEMET')
    r('R2609','1k reverse compensation',1010,385,'CHG_COMPR','CHG_COMPR_RC')
    c('C2606','47n 50V X7R reverse compensation',1090,385,'CHG_COMPR_RC','GND','GRM188R71H473KA61D')
    r('R2610','4.53k current monitor filter',850,405,'CHG_IMON','CHG_IMON_FILTER')
    c('C2607','220n 50V X7R current monitor',930,405,'CHG_IMON_FILTER','GND','GRM188R71H224KAC4D')
    r('R2611','20k PSYS monitor load',1010,405,'CHG_PSYS','GND')
    # ACOK is high with a valid adapter. The LED indicates adapter absent.
    r('R12','2.2k adapter-status LED',1090,405,'REGN','STAT_LED_A')
    part('LED1','LED','Adapter absent',1090,425,FOOTPRINTS['LED'],
         {1:'CHG_ACOK',2:'STAT_LED_A'},'APT1608SGC','Kingbright')
    r('R15','10k charger interrupt pull-up',850,425,'CHG_INT_N','MCU_3V3')
    r('R30','4.7k SCL pull-up',930,425,'MCU_3V3','I2C_SCL')
    r('R31','4.7k SDA pull-up',1010,425,'MCU_3V3','I2C_SDA')

    # Hardware inhibit drives the NTC input hot. The fixed 10k state is
    # released only by both permits. JEITA must be enabled/read back before
    # any nonzero charge-current or minimum-system-voltage command.
    part('U2210','74LVC1G08','SN74LVC1G08DBVR',850,465,FOOTPRINTS['SN74LVC1G08DBV'],
         {1:'CHG_ENABLE',2:'PACK_CHG_TEMP_OK_IN',3:'GND',4:'CHG_ENABLE_THERM',5:'MCU_3V3'},'SN74LVC1G08DBVR')
    r('R2260','1k temperature-permit input',930,455,'PACK_CHG_TEMP_OK','PACK_CHG_TEMP_OK_IN','RC0603FR-071KL')
    r('R2261','100k temperature-permit default-low',1010,455,'PACK_CHG_TEMP_OK_IN','GND','RC0603FR-07100KL')
    r('R2262','4.7k charge-permit default-low',1090,455,'CHG_ENABLE_THERM','GND','RC0603FR-074K7L')
    c('C2260','100n 50V AND bypass',930,475,'MCU_3V3','GND','GRM188R71H104KA93D')
    r('R719','100k charge request default-low',1010,475,'CHG_ENABLE','GND')
    r('R2263','100k pack-fault default-low',1090,475,'PACK_FAULT_N','GND','RC0603FR-07100KL')
    r('R14','100k NTC-inhibit default-on',850,500,'REGN','CHG_NTC_HOT_GATE')
    small_fet('Q700',930,510,'CHG_NTC_HOT_GATE','CHG_NTC')
    small_fet('Q702',1010,510,'CHG_ENABLE_THERM','CHG_NTC_HOT_GATE')
    r('R16','10k fixed-valid NTC resistance',1090,510,'CHG_NTC','GND')

    # The module supplies the PROCHOT pull-up. An AON pull-up here would
    # back-power an unpowered module. Both sink outputs are open drain.
    r('R2612','100k throttle default-on',850,540,'REGN','CHG_THROTTLE_GATE')
    small_fet('Q2604',930,550,'CHG_THROTTLE_GATE','MU_PROCHOT_N')
    small_fet('Q2605',1010,550,'MU_PROCHOT_RELEASE','CHG_THROTTLE_GATE')
    r('R13','100k throttle-release default-low',1090,550,'MU_PROCHOT_RELEASE','GND')
    part('D716','D_Schottky','BAT54WS case button to Mu',850,565,FOOTPRINTS['D_Signal'],
         {1:'CASE_PWRBTN_N',2:'MU_PWRBTN_N'},'BAT54WS-7-F','Diodes Incorporated')

    for i,ref in enumerate(('C701','C702','C703','C704','C705')):
        c(ref,'10u 50V X7R input',850+(i%4)*80,600+(i//4)*20,'CHG_INPUT','GND',
          'CGA5L1X7R1H106K160AC','C_10u','TDK')
    for i,ref in enumerate(('C706','C707','C708','C709','C710')):
        c(ref,'10u 25V X7R system',850+(i%4)*80,640+(i//4)*20,'VSYS','GND',
          'GRM31CR71E106KA12L','C_10u')
    c('C10','1u 50V input local',930,620,'CHG_INPUT','GND','GRT188R61H105ME13D')
    c('C11','1u 50V system local',1010,620,'VSYS','GND','GRT188R61H105ME13D')
    for i,ref in enumerate(('C712','C713')):
        c(ref,'10u 25V X7R battery',930+i*80,660,'PACK_POS_FUSED','GND','GRM31CR71E106KA12L','C_10u')
    for i,ref in enumerate(('C2608','C2609')):
        part(ref,'C_Polarized','100u 35V hybrid system bulk',850+100*i,695,
             FOOTPRINTS['C_100u_35V_hybrid'],{1:'VSYS',2:'GND'},'EEHZK1V101XP','Panasonic')
    r('R706','2.2R input damper',1050,695,'VBUS_COMBINED','VBUS_DAMP')
    c('C714','2.2u 50V X7R input damper',1050,715,'VBUS_DAMP','GND','MSASU21GBB7225KTNA01','C_1u','Taiyo Yuden')
    s.text(850,750,'Charge current and VSYSMIN power up at zero. Check JEITA, 3S strap, current limits and throttle before releasing the hardware gates.')
    s.text(850,758,'Q25 is the NVDC battery FET. Shutdown disables the loads; this FET alone does not provide complete pack isolation.')

    for i,name in enumerate(("CHG_DCIN","CHG_VDDP","VSYS","PD1_VBUS_RAW","PD2_VBUS_RAW")):
        s.pwrflag(850+i*50,780,name)
