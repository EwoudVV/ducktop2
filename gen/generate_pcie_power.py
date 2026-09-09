"""Externally compensated, host-gated PCIe endpoint supply."""
import genlib
from build_ducktop2 import FOOTPRINTS


def add_pcie_power(s):
    genlib.LIBMAP['TPS22992S']='TPS22992S'
    def part(ref,symbol,value,x,y,footprint,pins,mpn,maker='Texas Instruments',**extra):
        s.place(ref,symbol,value,x,y,footprint=footprint,
                pin_nets={str(k):(v if isinstance(v,tuple) else (v,'local') if v else ('','nc')) for k,v in pins.items()},
                extra_props={'Manufacturer':maker,'MPN':mpn,**extra})
    def r(ref,value,x,y,a,b,mpn):
        part(ref,'R',value,x,y,FOOTPRINTS['R'],{1:a,2:b},mpn,'Vishay' if mpn.startswith('TNP') else 'Yageo')
    def c(ref,value,x,y,a,b='GND',mpn='GRM188R71H104KA93D',fp='C_100n',maker='Murata'):
        part(ref,'C',value,x,y,FOOTPRINTS[fp],{1:a,2:b},mpn,maker)
    out='PCIE_3V3_IN';post=('PCIE_3V3','hier');vin=('VSYS','hier');logic=('MCU_3V3','hier');active=('MU_HOST_ACTIVE','hier')
    pins={**{str(n):vin for n in (1,2,3,27,28,29)},
          **{str(n):'GND' for n in (6,8,17,23,24,25,26,30)},
          **{str(n):'BUCKPE_SW' for n in (20,21,22)},
          '4':'BUCKPE_BOOT','5':'BUCKPE_SW_BOOT','7':'PCIE_3V3_PG','9':'BUCKPE_EN','10':'',
          '11':'PCIE_PRE_SENSE','12':out,'13':'BUCKPE_CONFIG','14':'BUCKPE_RT','15':'BUCKPE_COMP',
          '16':'BUCKPE_FB','18':'BUCKPE_VDDA','19':'BUCKPE_VCC'}
    part('U773','LM706A0','LM706A0RRXR endpoint 3.392V; 5A continuous envelope',820,535,
         FOOTPRINTS['LM706A0'],pins,'LM706A0RRXR',Datasheet='https://www.ti.com/lit/gpn/LM706A0',
         Compensation='3.3k+220n;2.2nHF;0.95MHz;local300..1500uF;endpoint10..2000uF',
         Layout='local_power_return;module_branch_L_le150nH;Kelvin_shunt_pair;qualify_load_steps')
    part('L1702','L','8.2uH 16.9A Isat30; endpoint',930,515,FOOTPRINTS['L_XGL1060_CENTER'],
         {1:'BUCKPE_SW',2:'PCIE_PRE_SENSE'},'XGL1060-822MEC','Coilcraft',
         Layout='pad1_marked_short_lead_to_SW;6mm_max_height')
    for ref,y in [('RS2280',515),('RS2281',535)]:
        part(ref,'R','13mOhm 1% 1W; parallel pair gives 6.5mOhm',1020,y,FOOTPRINTS['R_ERJ8CW_CENTER'],
             {1:'PCIE_PRE_SENSE',2:out},'ERJ8CWFR013V','Panasonic',
             Layout='Kelvin_at_RS2280_inner_pad_edges;power_branch_mismatch_le20uOhm')
    r('R785',"32.4k 0.02% 5ppm endpoint FB high",950,565,out,'BUCKPE_FB',"TNPU060332K4HZEN00")
    r('R786',"10k 0.02% 5ppm endpoint FB low",980,565,'BUCKPE_FB','GND',"TNPU060310K0HZEN00")
    r('R787','100k endpoint EN top',760,580,active,'BUCKPE_EN','RC0603FR-07100KL')
    r('R788','100k endpoint EN bottom',790,580,'BUCKPE_EN','GND','RC0603FR-07100KL')
    r('R789','10k endpoint converter PG pull-up',825,580,logic,'PCIE_3V3_PG','RC0603FR-0710KL')
    r('R2280',"22.1k 0.02% 5ppm endpoint RT",855,580,'BUCKPE_RT','GND',"TNPU060322K1HZEN00")
    r('R2281','29.4k endpoint standalone config',885,580,'BUCKPE_CONFIG','GND','RC0603FR-0729K4L')
    r('R2282',"3.3k endpoint COMP",760,615,'BUCKPE_COMP','BUCKPE_COMP_RC',"TNPU06033K30HZEN00")
    c('C2282','220n 50V X7R endpoint COMP',790,615,'BUCKPE_COMP_RC',mpn='C0603C224K5RACTU',maker='KEMET')
    c('C2283','2.2n 50V C0G endpoint COMP HF',825,615,'BUCKPE_COMP',mpn='C0603C222J5GACTU',maker='KEMET')
    r('R2283','1R endpoint BOOT damping',870,615,'BUCKPE_BOOT','BUCKPE_BOOT_C','RC0603FR-071RL')
    c('C779','47n 25V endpoint bootstrap',905,615,'BUCKPE_BOOT_C','BUCKPE_SW_BOOT','GRM155R71E473KA88D','C_0402')
    for ref,x in [('C776',760),('C777',790)]:
        c(ref,'10u 50V endpoint input',x,655,vin,mpn='CGA5L1X7R1H106K160AC',fp='C_10u',maker='TDK')
    for ref,x in [('C778',825),('C2286',855)]:c(ref,'100n 50V endpoint input HF',x,655,vin)
    c('C2280','22u 25V endpoint VCC; effective minimum 4.7u',885,655,'BUCKPE_VCC',mpn='GRM32ER71E226KE15L',fp='C_1210')
    c('C2281','100n 50V endpoint VDDA',920,655,'BUCKPE_VDDA')
    for ref,x in [('C782',950),('C2287',985)]:
        c(ref,'22u 25V endpoint output; TI characterized part',x,655,out,mpn='GRM32ER71E226KE15L',fp='C_1210')
    for ref,x in [('C2284',1020),('C2285',1060)]:
        part(ref,'C_Polarized','330u 10V endpoint local reservoir',x,615,FOOTPRINTS['C_330u_10V_poly'],
             {1:out,2:'GND'},'T520X337M010ATE010','KEMET')
    # The load switch remains off until the regulator's local bank has started.
    part('U2280','74LVC1G08','SN74LVC1G08DBVR endpoint PG-qualified enable',900,715,
         FOOTPRINTS['SN74LVC1G08DBV'],{1:active,2:'PCIE_3V3_PG',3:'GND',4:'PCIE_LOAD_EN',5:logic},
         'SN74LVC1G08DBVR')
    c('C2288','100n 50V endpoint enable gate supply',900,745,logic)
    part('U772','TPS22992S','TPS22992SRXNR endpoint slew and short protection',1030,710,
         'ducktop2:Texas_RXN0008A_WQFN-HR-8_1.25x1.25mm',
         {1:out,2:out,3:'PCIE_LOAD_PG',4:'GND',5:'PCIE_QOD',6:post,7:'PCIE_3V3_CT',8:'PCIE_LOAD_EN'},
         'TPS22992SRXNR',Datasheet='https://www.ti.com/lit/ds/symlink/tps22992.pdf',
         PowerContract='host_S0_and_converter_PG;5A_continuous;6A_including_inrush;Cmodule_le2mF;qualify_slew_and_short_response')
    part('R2292','R','10mOhm 1% 1W NVMe branch damping',1030,775,FOOTPRINTS['R_ERJ8CW_CENTER'],
         {1:post,2:'NVME_3V3'},'ERJ8CWFR010V','Panasonic',
         Layout='NVMe_branch_impedance_floor;case_le100C;wide_power_copper')
    r('R776','10k endpoint switch fail-low',975,745,'PCIE_LOAD_EN','GND','RC0603FR-0710KL')
    c('C832','1u endpoint switch input',975,710,out,mpn='GRM188R60J105KA01D')
    for ref,x in [('C833',1080),('C2289',1110)]:
        c(ref,'22n 50V C0G 5% endpoint slew; parallel pair',x,715,'PCIE_3V3_CT',mpn='C0805C223J5GACTU',fp='C_0805',maker='KEMET')
    part('R2290','R','100R 1% 0.25W endpoint QOD discharge',1080,750,'Resistor_SMD:R_1206_3216Metric',
         {1:post,2:'PCIE_QOD'},'RC1206FR-07100RL','Yageo')
    r('R2291','100k endpoint load-switch PG pull-up',1120,750,post,'PCIE_LOAD_PG','RC0603FR-07100KL')
    c('C834','22u 25V NVMe local bulk; TI characterized part',1140,685,'NVME_3V3',mpn='GRM32ER71E226KE15L',fp='C_1210')
    c('C835','100n NVMe rail HF',1140,710,'NVME_3V3',mpn='GRM188R71A104KA01D')
    s.pwrflag(940,685,out)
    s.place('TP2280','TestPoint','PCIE_LOAD_PG',1150,775,footprint=FOOTPRINTS['TestPoint_Pad_1.5'],
            pin_nets={'1':('PCIE_LOAD_PG','local')},in_bom=False,extra_props={'ProcurementClass':'PCB copper test feature'})
    s.text(760,790,'endpoint: local module-loop L <=150nH; total post-switch C <=2mF including board parts; 5A DC plus <=0.4A inrush; qualify transients.')


def add_pcie_remote_bulk(s):
    s.place('C2293','C','22u 25V GbE input bulk; TI characterized part',305,200,
            footprint=FOOTPRINTS['C_1210'],pin_nets={'1':('PCIE_3V3','hier'),'2':('GND','local')},
            extra_props={'Manufacturer':'Murata','MPN':'GRM32ER71E226KE15L',
                         'Layout':'near_U500_3V3_pins;continuous_ground_plane;GbE_return_paired_with_loom_pin5'})
