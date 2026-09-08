#!/usr/bin/env python3
"""Independent EC permissions and measured USB power protection.

This module builds symbols into caller-owned sheets. It never writes a PCB
or schematic. Power converter values remain in the converter generator.
"""
import build_ducktop2 as b
import genlib

PORTS = ('J21','J11','J22','J23','J12','J24','J25')
PERMIT_NETS = {port: 'USB_'+port+'_PERMIT' for port in PORTS}
GATE_REFS = {'J22':'U2405','J23':'U2406','J24':'U2407','J25':'U2408','J12':'U2409'}
PP5V_NETS = {'J21':'PD1_PP5V_GATED','J11':'PD2_PP5V_GATED'}
PP5V_PG = {'J21':'PD1_SOURCE_PG','J11':'PD2_SOURCE_PG'}
CTRL_OUT0 = ('USB5_PERMIT', *(PERMIT_NETS[p] for p in PORTS))
CTRL_OUT1 = {'0':'USB5_FAULT_CLEAR_N'}
CTRL_IN1 = {1:'USB5_FAULT_N',2:'USB5_OC_N',3:'USB5_PG',4:'PD1_SOURCE_PG',5:'PD2_SOURCE_PG'}

LOCAL_CONTROL_NETS = {'USB5_PERMIT', 'USB5_FAULT_N', 'USB5_OC_N',
                      'USB5_PG', 'USB5_FAULT_CLEAR_N',
                      *(PERMIT_NETS[p] for p in ('J22','J23','J24','J25'))}

def net_kind(net):
    return 'local' if net in LOCAL_CONTROL_NETS else 'hier'

def register_symbols():
    genlib.LIBMAP.update({'INA226':'Sensor_Energy','74LVC1G11':'74xGxx',
                         'SN74LVC1G74DCU':'SN74LVC1G74DCU','TPS22992S':'TPS22992S'})


def props(mpn, source):
    return {'Manufacturer':'Texas Instruments','MPN':mpn,'Datasheet':source}


def resistor(s, ref, value, x, y, first, second, first_kind='local', second_kind='local'):
    s.place(ref,'R',value,x,y,footprint=b.FOOTPRINTS['R'],
            pin_nets={'1':(first,first_kind),'2':(second,second_kind)})


def bypass(s, ref, x, y):
    s.place(ref,'C','100n',x,y,footprint=b.FOOTPRINTS['C_100n'],
            pin_nets={'1':('MCU_3V3','hier'),'2':('GND','local')})


def add_permission_io(s, x=1000, y=70):
    register_symbols()
    pins={'1':('','nc'),'2':('MCU_3V3','hier'),'3':('SERVICE_MUX_RESET_N','hier'),
          '12':('GND','local'),'21':('GND','local'),'22':('PD1_I2C_SCL','hier'),
          '23':('PD1_I2C_SDA','hier'),'24':('MCU_3V3','hier')}
    for n,net in enumerate(CTRL_OUT0):pins[str(4+n)]=(net,net_kind(net))
    pins['13']=('USB5_FAULT_CLEAR_N','local')
    for n in range(1,8):pins[str(13+n)]=(CTRL_IN1.get(n,'USB_IO_UNUSED'+str(n)),net_kind(CTRL_IN1[n]) if n in CTRL_IN1 else 'local')
    s.place('U2400','PCA9539xD','TCA9539PWR USB permissions @0x76',x,y,
            footprint=b.FOOTPRINTS['TCA9539PWR'],pin_nets=pins,
            extra_props={**props('TCA9539PWR','https://www.ti.com/lit/ds/symlink/tca9539.pdf'),
                         'I2CAddress7Bit':'0x76','ResetContract':'SERVICE_MUX_RESET_N follows EC NRST and reset request; local pulldown and permit pulldowns keep USB power off'})
    bypass(s,'C2400',x-40,y-30)
    resistor(s,'R2420','100k',x+60,y,'SERVICE_MUX_RESET_N','GND','hier')
    for bit,net in CTRL_IN1.items():
        resistor(s,'R'+str(2420+bit),'12.7k 1%' if bit in (4,5) else '100k',
                 x+60,y+bit*20,net,'GND',net_kind(net))
    for bit in (6,7):
        resistor(s,'R'+str(2420+bit),'100k',x+60,y+bit*20,'USB_IO_UNUSED'+str(bit),'GND')
    s.text(x-60,y-70,'USB permissions reset off; fault clear is active-low and defaults high.')


def add_left_monitor(s, x=650, y=70):
    register_symbols()
    s.place('U2401','INA226','INA226AIDGSR USB5 monitor @0x40',x,y,
            footprint='Package_SO:TSSOP-10_3x3mm_P0.5mm',pin_nets={
                '1':('GND','local'),'2':('GND','local'),'3':('USB5_OC_N','local'),
                '4':('PD1_I2C_SDA','hier'),'5':('PD1_I2C_SCL','hier'),
                '6':('MCU_3V3','hier'),'7':('GND','local'),'8':('USB_PORT_5V','hier'),
                '9':('USB_PORT_5V','hier'),'10':('USB5_PRE_SENSE','local')},
            extra_props={**props('INA226AIDGSR','https://www.ti.com/lit/ds/symlink/ina226.pdf'),
                         'I2CAddress7Bit':'0x40','ShuntContract':'Kelvin taps on the common pre/post nodes of RS1860 and RS1861',
                         'AlertContract':'latched shunt overcurrent; independent hardware latch prevents read-clear re-enabling'})
    bypass(s,'C2401',x-35,y-30)
    resistor(s,'R2401','10k',x+45,y,'MCU_3V3','USB5_OC_N','hier','local')
    # Existing converter PG has a weak pull-up. This permits a fail-low
    # receiver pulldown at U2400 without losing the logic-high margin.
    resistor(s,'R2412','10k',x+45,y+25,'SYS_3V3','USB5_PG','hier','local')
    s.place('U2402','SN74LVC1G74DCU','SN74LVC1G74DCUR USB fault latch',x,y+80,
            footprint='ducktop2:TI_DCU0008A_VSSOP8',pin_nets={
                '1':('GND','local'),'2':('GND','local'),'3':('USB5_FAULT_N','local'),
                '4':('GND','local'),'5':('','nc'),'6':('USB5_FAULT_CLEAR_N','local'),
                '7':('USB5_OC_N','local'),'8':('MCU_3V3','hier')},
            extra_props=props('SN74LVC1G74DCUR','https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf'))
    bypass(s,'C2402',x-35,y+50)
    resistor(s,'R2402','10k',x+45,y+80,'MCU_3V3','USB5_FAULT_CLEAR_N','hier','local')
    s.place('U2410','74LVC1G11','SN74LVC1G11DCKR USB5 permit AND',x,y+160,
            footprint='Package_TO_SOT_SMD:SOT-363_SC-70-6',pin_nets={
                '1':('USB5_PERMIT','local'),'2':('GND','local'),'3':('USB5_FAULT_N','local'),
                '4':('USB5_LATCH_ENABLE','local'),'5':('MCU_3V3','hier'),'6':('SYS_3V3','hier')},
            extra_props=props('SN74LVC1G11DCKR','https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf'))
    bypass(s,'C2410',x-35,y+130)
    s.place('U2411','74LVC1G08','SN74LVC1G08DBVR raw fault veto',x,y+240,
            footprint='Package_TO_SOT_SMD:SOT-23-5',pin_nets={
                '1':('USB5_LATCH_ENABLE','local'),'2':('USB5_OC_N','local'),
                '3':('GND','local'),'4':('USB5_HW_ENABLE','local'),'5':('MCU_3V3','hier')},
            extra_props=props('SN74LVC1G08DBVR','https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf'))
    bypass(s,'C2411',x-35,y+210)
    resistor(s,'R2400','10k',x+45,y+240,'USB5_HW_ENABLE','GND')
    resistor(s,'R2410','100k',x+45,y+160,'USB5_PERMIT','GND','local')
    s.text(x-45,y+275,'Raw ALERT veto remains active during fault-clear; never tie the fault-latch clear to NRST.')


def switch_enable_net(port):
    return 'USB_'+port+'_SWITCH_EN'


def add_hub_veto(s, port, hub_ctl, hub_kind='local', x=650, y=450):
    register_symbols()
    ref=GATE_REFS[port];number=int(ref[1:]);out=switch_enable_net(port)
    s.place(ref,'74LVC1G08','SN74LVC1G08DBVR '+port+' source permission',x,y,
            footprint='Package_TO_SOT_SMD:SOT-23-5',pin_nets={
                '1':(PERMIT_NETS[port],net_kind(PERMIT_NETS[port])),'2':(hub_ctl,hub_kind),
                '3':('GND','local'),'4':(out,'local'),'5':('MCU_3V3','hier')},
            extra_props=props('SN74LVC1G08DBVR','https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf'))
    bypass(s,'C'+str(number),x-35,y-30)
    resistor(s,'R'+str(number),'100k',x+40,y,PERMIT_NETS[port],'GND',net_kind(PERMIT_NETS[port]))
    return out


def add_pd_gate(s, port, x=790, y=250):
    register_symbols()
    n=2403 if port=='J21' else 2404
    out=PP5V_NETS[port];pg=PP5V_PG[port];ct=port+'_PP5V_CT'
    s.place('U'+str(n),'TPS22992S','TPS22992SRXNR '+port+' PP5V gate',x,y,
            footprint='ducktop2:Texas_RXN0008A_WQFN-HR-8_1.25x1.25mm',pin_nets={
                '1':('USB_PORT_5V','hier'),'2':('USB_PORT_5V','hier'),
                '3':(pg,'hier'),'4':('GND','local'),'5':(out,'local'),
                '6':(out,'local'),'7':(ct,'local'),'8':(PERMIT_NETS[port],net_kind(PERMIT_NETS[port]))},
            extra_props={**props('TPS22992SRXNR','https://www.ti.com/lit/ds/symlink/tps22992.pdf'),
                         'PowerContract':'permit off before loss/reset; wait PG before Source role; TCPC PP5V path retains VBUS reverse blocking'})
    s.place('C'+str(n),'C','1u',x-35,y-25,footprint=b.FOOTPRINTS['C_0805'],
            pin_nets={'1':('USB_PORT_5V','hier'),'2':('GND','local')})
    s.place('C'+str(n+10),'C','4.7n C0G PP5V slew',x+45,y-25,
            footprint=b.FOOTPRINTS['C_100n'],pin_nets={'1':(ct,'local'),'2':('GND','local')},
            extra_props={'Manufacturer':'Murata','MPN':'GRM1885C1H472JA01D'})
    resistor(s,'R'+str(n),'100k',x-35,y+25,PERMIT_NETS[port],'GND',net_kind(PERMIT_NETS[port]))
    # Pull PG to the gated rail, so an unpowered gate cannot read falsely high.
    # A 12.7k receiver pulldown divides this rail below MCU_3V3 while
    # remaining above VIH at the lowest valid PP5V voltage.
    resistor(s,'R'+str(n+10),'10k',x+45,y+25,out,pg,'local','hier')
