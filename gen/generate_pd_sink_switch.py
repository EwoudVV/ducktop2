"""5..20 V sink protection, power-good feedback and controlled discharge."""
from build_ducktop2 import FOOTPRINTS


def add_pd_sink_switch(s,port,x0,y0,base,gated_hier=False):
    raw=f'PD{port}_PPHV';out=f'PD{port}_VBUS_GATED'
    enable=f'PD{port}_PATH_EN';gate=f'PD{port}_EFUSE_SHDN'
    pg=f'PD{port}_EFUSE_PG';ilim=f'PD{port}_EFUSE_ILIM'
    dvdt=f'PD{port}_EFUSE_DVDT';discharge=f'PD{port}_DISCHARGE'
    drain=f'PD{port}_DISCHARGE_DRAIN';imon=f'PD{port}_EFUSE_IMON'
    hier={enable,pg,'MCU_3V3'}|({out} if gated_hier else set())
    def n(net):return(net,'nc' if not net else 'hier' if net in hier else 'local')
    def part(ref,sym,value,x,y,fp,pins,mpn,maker='Texas Instruments'):
        s.place(ref,sym,value,x,y,footprint=fp,pin_nets={str(pin):n(net) for pin,net in pins.items()},
                extra_props={'Manufacturer':maker,'MPN':mpn})
    part(f'U{719+port}','TPS25982',f'TPS259827ONRGER PD{port} sink breaker',x0,y0,
         'ducktop2:Texas_RGE0024M_QFN24_4x4_2EP',{
            **{pin:raw for pin in (1,2,3,16,25)},
            **{pin:out for pin in range(17,25)},
            **{pin:'GND' for pin in (4,5,10,11,12,14,26)},
            6:gate,7:'',8:ilim,9:imon,13:pg,15:dvdt},'TPS259827ONRGER')
    # No OVLO is built into this variant. The TCPC and downstream LTC4418
    # provide the reviewed voltage window; this IC is rated for 24 V input.
    entries=(
        (base,'1k 1W switched input discharge',out,drain,'RC2512FR-071KL','Resistor_SMD:R_2512_6332Metric'),
        (base+1,'100k discharge gate default-low',discharge,'GND','RC0603FR-07100KL',FOOTPRINTS['R']),
        (base+2,'1k IMON load',imon,'GND','RC0603FR-071KL',FOOTPRINTS['R']),
        (base+3,'267R 0.1% sink breaker; 5.58A nominal',ilim,'GND','RT0603BRD07267RL',FOOTPRINTS['R']),
        (base+4,'47k sink enable default-off',gate,'GND','RC0603FR-0747KL',FOOTPRINTS['R']),
        (base+5,'10k sink enable series',enable,gate,'RC0603FR-0710KL',FOOTPRINTS['R']),
        (base+6,'150k sink PG pull-up; valid with input off','MCU_3V3',pg,'RC0603FR-07150KL',FOOTPRINTS['R']))
    for i,(ref,value,a,b,mpn,fp) in enumerate(entries):
        part(f'R{ref}','R',value,x0+45.72,y0-30.48+i*10.16,fp,{1:a,2:b},mpn,'Yageo')
    for ref,value,net,y,mpn,fp in (
        (base,'100n 50V input local',raw,y0-17.78,'GRM188R71H104KA93D','C_100n'),
        (base+1,'10u 25V output',out,y0-5.08,'GRM31CR71E106KA12L','C_10u'),
        (base+2,'10n 50V C0G slew control',dvdt,y0+7.62,'GRM1885C1H103JA01D','C_100n')):
        part(f'C{ref}','C',value,x0+96.52,y,FOOTPRINTS[fp],{1:net,2:'GND'},mpn,'Murata')
    i=port-1
    part(f'U{2630+i}','74LVC1G04','SN74LVC1G04DBVR discharge control',x0,y0+58.42,
         FOOTPRINTS['SN74LVC1G08DBV'],{1:'',2:enable,3:'GND',4:discharge,5:'MCU_3V3'},'SN74LVC1G04DBVR')
    part(f'Q{2630+i}','Q_NMOS_SOT23_GSD','BSS138 switched discharge',x0+45.72,y0+63.5,
         FOOTPRINTS['Q_BSS138'],{1:discharge,2:'GND',3:drain},'BSS138LT1G','onsemi')
    part(f'C{2630+i}','C','100n 50V inverter bypass',x0+96.52,y0+63.5,
         FOOTPRINTS['C_100n'],{1:'MCU_3V3',2:'GND'},'GRM188R71H104KA93D','Murata')
