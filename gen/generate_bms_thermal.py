"""Three raw-referenced cell probes, hardware CTR inhibits and isolated fault.

The provisional temperatures do not qualify the owned AKZYTUE cells. Exact
electrical corner evidence lives in the private analog review directory.
"""
import build_ducktop2 as b

RAW='PACK_NEG_RAW'
BIAS='THERM_3V3'
CTRL='CTRL_GND'
CTRL_VCC='CTRL_3V3'
RFP='Resistor_SMD:R_0603_1608Metric'
CFP='Capacitor_SMD:C_0603_1608Metric'
C100='GRM188R71H104KA93D'
C10N='GRM188R71H103KA01D'


def add_bms_thermal(s):
    def part(ref,symbol,value,x,y,footprint,nets,mpn,manufacturer='Texas Instruments',**extra):
        return s.place(ref,symbol,value,x,y,footprint=footprint,
                       pin_nets={pin:((net,'local') if net else ('','nc')) for pin,net in nets.items()},
                       extra_props={'Manufacturer':manufacturer,'MPN':mpn},**extra)
    def resistor(ref,value,x,y,a,z,mpn,footprint=RFP):
        return part(ref,'R',value,x,y,footprint,{'1':a,'2':z},mpn,'Yageo')
    def cap(ref,value,x,y,a,z=RAW,mpn=C100,footprint=CFP):
        return part(ref,'C',value,x,y,footprint,{'1':a,'2':z},mpn,
                    'TDK' if mpn.startswith('CGA') else 'Murata')

    s.text(75,295,'== three-cell temperature inhibit: raw reference, independent of firmware ==')
    resistor('R2200','1k 1% 0.75W raw thermal supply limiter',80,320,
             'PACK_POS_RAW','THERM_RAW_IN','RC2010FK-071KL','Resistor_SMD:R_2010_5025Metric')
    cap('C2200','100n 50V thermal regulator input',80,335,'THERM_RAW_IN')
    part('U2200','TPS70933DBV','TPS70933DBVR raw-pack thermal bias',120,330,
         'Package_TO_SOT_SMD:SOT-23-5',{'1':'THERM_RAW_IN','2':RAW,'3':'','4':'','5':BIAS},'TPS70933DBVR')
    cap('C2201','10u 50V thermal bias; require Ceff >=2u',80,350,BIAS,
        mpn='CGA5L1X7R1H106K160AC',footprint='Capacitor_SMD:C_1206_3216Metric')
    resistor('R2201','9.53k 0.1% 25ppm thermal bias fault bleed',80,365,BIAS,RAW,'RT0603BRD079K53L')
    s.pwrflag(65,380,'THERM_RAW_IN')

    # Shared ratiometric references. Bottoms and tolerances are intentionally
    # identical; each midpoint drives one input on each of the three quads.
    for index,(name,top,mpn) in enumerate([
            ('CHG_COLD','243k','RT0603BRD07243KL'),
            ('CHG_HOT','634k','RT0603BRD07634KL'),
            ('DSG_COLD','147k','RT0603BRD07147KL'),
            ('DSG_HOT','845k','RT0603BRD07845KL')]):
        x=200+index*80; net=f'THERM_{name}_REF'
        resistor(f'R{2240+index*2}',f'{top} 0.1% 25ppm {name} top',x,460,BIAS,net,mpn)
        resistor(f'R{2241+index*2}','499k 0.1% 25ppm thermal reference bottom',x,475,net,RAW,'RT0603BRD07499KL')
        cap(f'C{2240+index}','10n 50V thermal reference filter',x,490,net,mpn=C10N)

    probe_nets={'MP':RAW}
    for cell in range(1,4):
        x=220+(cell-1)*100;sense=f'THERM_SENSE_{cell}'
        wire_a=f'THERM_PROBE_{cell}_A';wire_b=f'THERM_PROBE_{cell}_B'
        probe_nets[str(2*cell-1)]=wire_a;probe_nets[str(2*cell)]=wire_b
        resistor(f'R{2210+(cell-1)*3}','100k 0.1% 25ppm cell NTC pull-up',x,310,BIAS,sense,'RT0603BRD07100KL')
        resistor(f'R{2211+(cell-1)*3}','10k 0.1% 25ppm NTC sense-lead limit',x,325,sense,wire_a,'RT0603BRD0710KL')
        resistor(f'R{2212+(cell-1)*3}','10k 0.1% 25ppm NTC return-lead limit',x,340,wire_b,RAW,'RT0603BRD0710KL')
        cap(f'C{2210+cell}','10n 50V NTC sense filter',x,355,sense,mpn=C10N)
        part(f'U{2200+cell}','TLV1864PW',f'TLV1864PWR cell {cell} thermal windows',x,400,
             'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
             {'1':'THERM_CHG_HEALTH','2':sense,'3':'THERM_CHG_COLD_REF','4':BIAS,
              '5':sense,'6':'THERM_CHG_HOT_REF','7':'THERM_CHG_HEALTH',
              '8':'THERM_DSG_HEALTH','9':'THERM_DSG_HOT_REF','10':sense,'11':RAW,
              '12':'THERM_DSG_COLD_REF','13':sense,'14':'THERM_DSG_HEALTH'},'TLV1864PWR')
        cap(f'C{2220+cell}','100n 50V comparator supply',x,430,BIAS)
        part(f'TH{2200+cell}','Thermistor_NTC',f'104JT-025 cell {cell} insulated probe',700,270+cell*20,
             '',{'1':wire_a,'2':wire_b},'104JT-025','SEMITEC',on_board=False)
    part('J2200','Conn_01x06_Thermal_MP','three cell probes: paired 1/2, 3/4, 5/6',600,315,
         'Connector_JST:JST_SH_SM06B-SRSS-TB_1x06-1MP_P1.00mm_Horizontal',probe_nets,
         'SM06B-SRSS-TB(LF)(SN)','JST')
    s.text(545,365,'J2200 and its hold-downs are raw-pack referenced; no system-ground wire.')

    resistor('R2230','100k thermal charge-health pull-up',80,400,BIAS,'THERM_CHG_HEALTH','RC0603FR-07100KL')
    resistor('R2231','100k thermal discharge-health pull-up',80,415,BIAS,'THERM_DSG_HEALTH','RC0603FR-07100KL')
    part('U2204','TLV803EA29RDBZR','TLV803EA29RDBZR thermal startup hold',80,450,
         'Package_TO_SOT_SMD:SOT-23',{'1':'THERM_READY','2':RAW,'3':BIAS},'TLV803EA29RDBZR')
    cap('C2230','100n 50V thermal supervisor supply',80,470,BIAS)
    resistor('R2232','100k thermal-ready pull-up',80,485,BIAS,'THERM_READY','RC0603FR-07100KL')
    resistor('R2233','1M thermal-ready default-low',80,500,'THERM_READY',RAW,'RC0603FR-071ML')
    part('U2205','SN74AUP2G126DCU','SN74AUP2G126DCUR thermal startup gate',80,540,
         'ducktop2:TI_DCU0008A_VSSOP8',
         {'1':'THERM_READY','2':'THERM_CHG_HEALTH','3':'THERM_DSG_PERMIT',
          '4':RAW,'5':'THERM_DSG_HEALTH','6':'THERM_CHG_PERMIT','7':'THERM_READY','8':BIAS},'SN74AUP2G126DCUR')
    cap('C2231','100n 50V thermal buffer supply',80,565,BIAS)
    for index,kind in enumerate(['CHG','DSG']):
        x=200+index*110;gate=f'THERM_{kind}_GATE';ctr=f'BMS_CTR{kind[0]}'
        resistor(f'R{2234+index*3}','1k thermal CTR gate series',x,520,f'THERM_{kind}_PERMIT',gate,'RC0603FR-071KL')
        resistor(f'R{2235+index*3}','100k thermal CTR gate default-off',x,535,gate,RAW,'RC0603FR-07100KL')
        resistor(f'R{2236+index*3}','470k 0.1% 25ppm CTR fault pull-up',x,550,'BMS_VDD',ctr,'RT0603BRD07470KL')
        part(f'Q{2200+index}','Q_NMOS_SOT23_GSD',f'BSS138 {kind} thermal CTR pull-down',x+45,535,
             'Package_TO_SOT_SMD:SOT-23',{'1':gate,'2':RAW,'3':ctr},'BSS138LT1G','onsemi')

    # Three ground domains: raw probe/CTR, protected LTC, isolated controls.
    # The control ground never becomes a parallel pack-current return.
    part('U2206','ISO7041FDBQ','ISO7041FDBQR separate charge/discharge permits; default low',520,425,
         'Package_SO:QSOP-16_3.9x4.9mm_P0.635mm',
         {'1':BIAS,'2':RAW,'3':'THERM_CHG_GATE','4':'THERM_DSG_GATE','5':RAW,
          '6':'','7':RAW,'8':RAW,'9':CTRL,'10':CTRL,'11':CTRL,
          '12':'','13':'THERM_DSG_HEALTH_ISO','14':'THERM_CHG_HEALTH_ISO',
          '15':CTRL,'16':CTRL_VCC},'ISO7041FDBQR')
    cap('C2250','100n 50V raw isolator supply',500,460,BIAS)
    cap('C2251','100n 50V control-island isolator supply',555,460,CTRL_VCC,CTRL)
    part('U2207','SN74AUP2G07DCK','SN74AUP2G07DCKR thermal and LTC fault wired-OR',650,425,
         'Package_TO_SOT_SMD:SOT-363_SC-70-6',
         {'1':'THERM_DSG_HEALTH_ISO','2':CTRL,'3':'PACK_PROTECT_OK',
          '4':'CTRL_FAULT_LOCAL_N','5':CTRL_VCC,'6':'CTRL_FAULT_LOCAL_N'},'SN74AUP2G07DCKR')
    cap('C2252','100n 50V control fault-buffer supply',650,450,CTRL_VCC,CTRL)
    resistor('R2250','100k isolated discharge-health default-low',600,475,'THERM_DSG_HEALTH_ISO',CTRL,'RC0603FR-07100KL')
    resistor('R2251','100k isolated charge-permit default-low',650,475,'THERM_CHG_HEALTH_ISO',CTRL,'RC0603FR-07100KL')

    # The LTC-side transceiver is powered locally after F1. Its feed and
    # reverse-input diode cannot expose the control island to pack voltage.
    resistor('R2252','2.49k 1% 0.25W protected control supply limiter',80,610,
             'BAT_PROT_VIN','PROT_CTRL_FEED','RC1206FR-072K49L','Resistor_SMD:R_1206_3216Metric')
    part('D2200','D_Schottky','BAT54WS protected control reverse-input block',120,610,
         'Diode_SMD:D_SOD-323',{'1':'PROT_CTRL_IN','2':'PROT_CTRL_FEED'},'BAT54WS-7-F','Diodes Incorporated')
    cap('C2253','100n 50V protected control regulator input',160,610,'PROT_CTRL_IN','FG_VSS')
    part('U2208','TPS70933DBV','TPS70933DBVR protected-side local bias',210,620,
         'Package_TO_SOT_SMD:SOT-23-5',
         {'1':'PROT_CTRL_IN','2':'FG_VSS','3':'','4':'','5':'PROT_CTRL_3V3'},'TPS70933DBVR')
    cap('C2254','10u 50V protected local bias; Ceff >=2u',255,610,'PROT_CTRL_3V3','FG_VSS',
        mpn='CGA5L1X7R1H106K160AC',footprint='Capacitor_SMD:C_1206_3216Metric')
    resistor('R2253','30.1k 0.1% protected bias minimum load',300,610,'PROT_CTRL_3V3','FG_VSS','RT0603BRD0730K1L')
    s.pwrflag(160,625,'PROT_CTRL_IN')
    part('U2209','ISO7021FD','ISO7021FDR LTC fault and retry isolation',410,625,
         'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
         {'1':'PROT_CTRL_3V3','2':'PACK_RETRY_LOCAL','3':'BMS_PROTECT_FAULT_N','4':'FG_VSS',
          '5':CTRL,'6':'PACK_PROTECT_OK','7':'CTRL_RETRY_IN','8':CTRL_VCC},'ISO7021FDR')
    cap('C2255','100n 50V protected transceiver supply',360,650,'PROT_CTRL_3V3','FG_VSS')
    cap('C2256','100n 50V control transceiver supply',460,650,CTRL_VCC,CTRL)
    resistor('R2254','1k local retry gate series',360,670,'PACK_RETRY_LOCAL','PACK_RETRY_LOCAL_GATE','RC0603FR-071KL')
    resistor('R2255','100k isolated LTC-health default-low',520,610,'PACK_PROTECT_OK',CTRL,'RC0603FR-07100KL')
    resistor('R2256','3.3k control fault pull-up',520,625,CTRL_VCC,'CTRL_FAULT_LOCAL_N','RC0603FR-073K3L')
    resistor('R2257','100R 1% 0.25W control-island current limiter',575,610,
             'MCU_3V3',CTRL_VCC,'RC1206FR-07100RL','Resistor_SMD:R_1206_3216Metric')
    resistor('R2258','4.7k fault interface current limit',575,625,'CTRL_FAULT_LOCAL_N','PACK_FAULT_N','RC0603FR-074K7L')
    resistor('R2259','4.7k retry interface current limit',630,610,'PACK_RETRY_PULSE','CTRL_RETRY_IN','RC0603FR-074K7L')
    resistor('R2264','100k retry input default-low',630,625,'CTRL_RETRY_IN',CTRL,'RC0603FR-07100KL')
    resistor('R2265','4.7k charge-permit interface current limit',685,610,
             'THERM_CHG_HEALTH_ISO','PACK_CHG_TEMP_OK','RC0603FR-074K7L')
    for ref,signal,x in [('D2201','CTRL_RETRY_IN',585),('D2202','THERM_CHG_HEALTH_ISO',670)]:
        part(ref,'BAT54S_AKC','BAT54S control-island pin clamps',x,665,'Package_TO_SOT_SMD:SOT-23',
             {'1':CTRL,'2':CTRL_VCC,'3':signal},'BAT54S-7-F','Diodes Incorporated')
    s.pwrflag(730,620,CTRL);s.pwrflag(730,640,CTRL_VCC)
    for index,net in enumerate([BIAS,'THERM_READY','THERM_SENSE_1','THERM_SENSE_2',
                                'THERM_SENSE_3','BMS_CTRC','BMS_CTRD','PACK_CHG_TEMP_OK']):
        s.place(f'TPB{20+index}','TestPoint',net,480+(index%4)*55,520+(index//4)*25,
                footprint=b.FOOTPRINTS['TestPoint_Pad_1.5'],in_bom=False,
                pin_nets={'1':(net,'local')},extra_props={'Manufacturer':'-','Note':'thermal validation pad'})
    s.text(170,580,'provisional charge 10..40C / discharge 0..50C screen; actual cell profile and installed probe response remain unqualified.')
    s.text(170,588,'discharge faults assert PACK_FAULT_N; charge-only faults lower PACK_CHG_TEMP_OK. no raw-ground bypass.')
    s.text(170,690,'CTRL_GND belongs only to the isolated control island. Power-return disconnect cannot reach the center through fault/retry pins.')
