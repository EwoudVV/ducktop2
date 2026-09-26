"""Low-loss USB standby feeds and the shared always-on circuit breaker."""
from build_ducktop2 import FOOTPRINTS


def add_aon_input(s):
    hier={'PACK_POS_FUSED','PD1_VBUS_RAW','PD2_VBUS_RAW','EC_AON_IN','AON_FAULT_N'}
    def n(name):return (name,'hier' if name in hier else 'local')
    def part(ref,symbol,value,x,y,fp,pins,mpn,maker):
        s.place(ref,symbol,value,x,y,footprint=fp,pin_nets={str(p):n(net) if net else ('','nc') for p,net in pins.items()},
                extra_props={'Manufacturer':maker,'MPN':mpn})
    def cap(ref,value,x,y,a,b,mpn='GRM188R71H104KA93D',fp='C_100n',maker='Murata'):
        part(ref,'C_Polarized' if ref=='C797' else 'C',value,x,y,FOOTPRINTS[fp],{1:a,2:b},mpn,maker)
    def resistor(ref,value,x,y,a,b,mpn,maker='Yageo'):
        part(ref,'R',value,x,y,FOOTPRINTS['R'],{1:a,2:b},mpn,maker)
    def mosfet(ref,x,y,source,gate,drain):
        part(ref,'Q_NMOS_123S_4G_5678D','CSD19537Q3 100V',x,y,FOOTPRINTS['Q_CSD19537Q3'],
             {1:source,2:source,3:source,4:gate,5:drain},'CSD19537Q3','Texas Instruments')

    s.text(650,290,'== always-on supply: low-loss USB feeds and shared protection ==')
    part('D711','D_Schottky','SS310 3A 100V AUX standby feed',650,335,FOOTPRINTS['D_Schottky_SMA'],
         {1:'AON_EXT_RAW',2:'AUX_DC_FUSED'},'SS310-13-F','Diodes Incorporated')
    for index,source in enumerate(('PD1_VBUS_RAW','PD2_VBUS_RAW')):
        y=440+75*index;stem=f'AON_PD{index+1}'
        part(f'U{2620+index}','LM74700','LM74700QDBVRQ1',660,y,
             'Package_TO_SOT_SMD:SOT-23-6',
             {1:stem+'_VCAP',2:'GND',3:source,4:'AON_EXT_RAW',5:stem+'_GATE',6:source},
             'LM74700QDBVRQ1','Texas Instruments')
        mosfet(f'Q{2620+index}',745,y,source,stem+'_GATE','AON_EXT_RAW')
        cap(f'C{2620+index}','100n 50V charge pump',810,y,stem+'_VCAP',source)

    part('U718','LTC4368-2','LTC4368IMS-2#PBF standby breaker',705,335,
         FOOTPRINTS['LTC4368-1'],{1:'AON_OR_RAW',2:'AON_EFUSE_UV',3:'AON_EFUSE_OV',
         4:'AON_RETRY',5:'GND',6:'AON_PROTECT_SHDN',7:'AON_FAULT_N',
         8:'EC_AON_IN',9:'AON_PROTECT_SENSE',10:'AON_GATE_DRV'},'LTC4368IMS-2#PBF','Analog Devices')
    for ref,value,a,b,mpn,x,y in (
        ('R795','56.2k 0.02% 5ppm AON UV top','AON_OR_RAW','AON_EFUSE_UV','TNPU060356K2HZEN00',755,315),
        ('R796','8.25k 0.02% 5ppm AON UV bottom','AON_EFUSE_UV','GND','TNPU06038K25HZEN00',755,330),
        ('R797','100k 0.02% 5ppm AON OV top','AON_OR_RAW','AON_EFUSE_OV','TNPU0603100KHZEN00',755,345),
        ('R798','2.15k 0.02% 5ppm AON OV bottom','AON_EFUSE_OV','GND','TNPU06032K15HZEN00',755,360)):
        resistor(ref,value,x,y,a,b,mpn,'Vishay')
    resistor('R799','100k standby enable pull-up',755,380,'AON_OR_RAW','AON_PROTECT_SHDN','RC0603FR-07100KL')
    mosfet('Q2622',660,595,'AON_FET_COMMON','AON_FET_GATE','AON_OR_RAW')
    mosfet('Q2623',745,595,'AON_FET_COMMON','AON_FET_GATE','AON_PROTECT_SENSE')
    part('RS2620','R','22m 1% 2W AON Kelvin shunt',810,590,'Resistor_SMD:R_2512_6332Metric',
         {1:'AON_PROTECT_SENSE',2:'EC_AON_IN'},'WSLP2512R0220FEA','Vishay Dale')
    resistor('R2620','10k gate ramp resistor',650,630,'AON_GATE_DRV','AON_FET_GATE','RC0603FR-0710KL')
    part('D2620','D_Schottky','BAT54WS fast gate discharge',745,630,FOOTPRINTS['D_Signal'],
         {1:'AON_GATE_DRV',2:'AON_FET_GATE'},'BAT54WS-7-F','Diodes Incorporated')
    cap('C799','22n 50V C0G gate ramp',810,630,'AON_FET_GATE','EC_AON_IN',
        'C0805C223J5GACTU','C_0805','KEMET')
    cap('C2622','22n 50V C0G retry timer',650,650,'AON_RETRY','GND',
        'C0805C223J5GACTU','C_0805','KEMET')
    cap('C795','1u 50V AON input',805,315,'AON_OR_RAW','GND','GRT188R61H105ME13D')
    cap('C796','100n 50V AON input local',805,335,'AON_OR_RAW','GND')
    cap('C797','100u 35V hybrid AON hold-up',805,355,'EC_AON_IN','GND','EEHZK1V101XP','C_100u_35V_hybrid','Panasonic')
    cap('C798','100n 50V AON output local',805,375,'EC_AON_IN','GND')
    s.pwrflag(650,370,'AON_OR_RAW')
    s.pwrflag(650,390,'EC_AON_IN')
    s.text(650,685,'The USB ideal diodes avoid the Schottky drop at 5V. U718 retries automatically; the EC never has to enable its own starting supply.')

    # Prefer a valid adapter even when its voltage is below the pack. A plain
    # diode OR would keep feeding standby from a 3S pack on 5/9 V input.
    s.text(850,690,'== standby priority: external input first, protected pack second ==')
    part('U2650','LTC4418IUF','LTC4418IUF#PBF standby source priority',930,740,
         FOOTPRINTS['LTC4418IUF'],{
          1:'AON_SEL_TMR',2:'AON_EXT_UV',3:'AON_EXT_OV',4:'AON_PACK_UV',5:'AON_PACK_OV',
          6:'',7:'',8:'GND',9:'',10:'AON_SEL_INTVCC',11:'AON_PACK_GATE',12:'AON_PACK_COMMON',
          13:'AON_EXT_GATE',14:'AON_EXT_COMMON',15:'AON_OR_RAW',16:'PACK_POS_FUSED',17:'AON_EXT_RAW',
          18:'AON_SEL_INTVCC',19:'AON_SEL_INTVCC',20:'GND',21:'GND'},'LTC4418IUF#PBF','Analog Devices')
    for ref,x,y,gate,common,drain in (
        ('Q2650',850,710,'AON_EXT_GATE','AON_EXT_COMMON','AON_EXT_RAW'),
        ('Q2651',850,755,'AON_EXT_GATE','AON_EXT_COMMON','AON_OR_RAW'),
        ('Q2652',1010,710,'AON_PACK_GATE','AON_PACK_COMMON','PACK_POS_FUSED'),
        ('Q2653',1010,755,'AON_PACK_GATE','AON_PACK_COMMON','AON_OR_RAW')):
        part(ref,'Q_PMOS_1G_234S_5D','SiSS4409DN 40V standby selector',x,y,
             FOOTPRINTS['Q_SiSS4409DN'],{1:gate,2:common,3:common,4:common,5:drain},
             'SiSS4409DN-T1-GE3','Vishay')
    for ref,value,x,y,a,b,mpn in (
        ('R2650','75.0k 0.02% 5ppm ext UV top',1090,710,'AON_EXT_RAW','AON_EXT_UV','TNPU060375K0HZEN00'),
        ('R2651','23.2k 0.02% 5ppm ext window',1090,735,'AON_EXT_UV','AON_EXT_OV','TNPU060323K2HZEN00'),
        ('R2652','4.53k 0.02% 5ppm ext OV bottom',1090,760,'AON_EXT_OV','GND','TNPU06034K53HZEN00'),
        ('R2653','121k 0.02% 5ppm pack UV top',1190,710,'PACK_POS_FUSED','AON_PACK_UV','TNPU0603121KHZEN00'),
        ('R2654','8.66k 0.02% 5ppm pack window',1190,735,'AON_PACK_UV','AON_PACK_OV','TNPU06038K66HZEN00'),
        ('R2655','10.0k 0.02% 5ppm pack OV bottom',1190,760,'AON_PACK_OV','GND','TNPU060310K0HZEN00')):
        resistor(ref,value,x,y,a,b,mpn,'Vishay')
    cap('C2650','100n 10V INTVCC',850,805,'AON_SEL_INTVCC','GND','GRM188R71A104KA61D')
    cap('C2651','1n 50V C0G validation',930,805,'AON_SEL_TMR','GND','GRM1555C1H102JA01D','C_0402')
    for ref,x,net in [('C2652',1010,'AON_EXT_RAW'),('C2653',1090,'PACK_POS_FUSED'),
                      ('C2654',1190,'AON_EXT_COMMON'),('C2655',1270,'AON_PACK_COMMON')]:
        cap(ref,'100n 50V selector local',x,805,net,'GND')
    cap('C2656','10u 50V AON selector local',850,845,'AON_OR_RAW','GND',
        'CGA5L1X7R1H106K160AC','C_10u','TDK')
    s.pwrflag(1190,845,'AON_EXT_RAW')
