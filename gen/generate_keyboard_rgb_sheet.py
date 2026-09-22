"""Add the per-key RGB circuit to the keyboard schematic."""
from keyboard_rgb_contract import *


def add_rgb(s, keys):
    assert len(keys)==65
    s.paper='A0'
    s.text(650,20,'keyboard rgb: 65 separate colours, hardware-limited current')
    s.text(650,28,'Everlight 19-337/R6GHBHC-C02/2T, 1.6 x 1.6 x 0.35 mm; LEDs are fitted before the switches.')
    s.text(650,36,'Each group has up to six nearby keys. Follow the RGB_SW and RGB_CS labels when routing.')
    for index,assignment in key_assignments().items():
        bank,slot=assignment['bank'],assignment['slot']
        row,col,code,value=keys[index]
        s.place(f'LED{320+index}','LED_19_337_C02',f'RGB {code}',650+60*slot,65+28*(bank-1),
                footprint=LED_FOOTPRINT,
                pin_nets={pin:(net,'local') for pin,net in led_nets(index).items()},
                extra_props={'Manufacturer':'Everlight','MPN':LED_MPN,'LCSC':LED_LCSC,
                             'Assembly':'fit before the matching MX ULP switch',
                             'Key':f'SW{320+index}','RGB_bank':str(bank)},datasheet=LED_DATASHEET)
    s.place('U320','IS31FL3743A',DRIVER_MPN,770,440,footprint=DRIVER_FOOTPRINT,
            pin_nets={str(pin):(net,'local') if net else ('','nc') for pin,net in DRIVER_PINS.items()},
            extra_props={'Manufacturer':'Lumissil','MPN':DRIVER_MPN,'LCSC':'C2678953'},datasheet=DRIVER_DATASHEET)
    s.place('U321','TCA9517A',BUFFER_MPN,1020,440,footprint=BUFFER_FOOTPRINT,
            pin_nets={str(pin):(net,'local')for pin,net in {
                1:'KB_RGB_5V',2:'RGB_SCL',3:'RGB_SDA',4:'GND',5:'KB_RGB_5V',
                6:'I2C_SDA',7:'I2C_SCL',8:'MCU_3V3'}.items()},
            extra_props={'Manufacturer':'Texas Instruments','MPN':BUFFER_MPN,'LCSC':'C201698'},datasheet=BUFFER_DATASHEET)
    def resistor(ref,value,mpn,a,b,x,y):
        s.place(ref,'R',value,x,y,footprint='Resistor_SMD:R_0603_1608Metric',
                pin_nets={'1':(a,'local'),'2':(b,'local')},
                extra_props={'Manufacturer':'Yageo','MPN':mpn})
    resistor('R320','33.2k 1% RGB current limit','RC0603FR-0733K2L','RGB_ISET','GND',875,420)
    resistor('R321','2.2k RGB SCL pull-up','RC0603FR-072K2L','KB_RGB_5V','RGB_SCL',960,490)
    resistor('R322','2.2k RGB SDA pull-up','RC0603FR-072K2L','KB_RGB_5V','RGB_SDA',1010,490)
    resistor('R323','100k RGB startup pull-up','RC0603FR-07100KL','KB_RGB_5V','RGB_SDB',875,470)
    for slot in range(6):
        cs=slot*3+1
        resistor(f'R{330+slot}','100R red-channel heat sharing','RC0603FR-07100RL',
                 f'RGB_CS{cs:02d}',f'RGB_RED{cs:02d}',670+60*slot,550)
    caps=[('C320','100n 50V buffer 3V3','CL10B104KB8NNNC','MCU_3V3',970,610,'0603'),
          ('C321','10u 25V RGB input bulk','CL21A106KAYNNNE','KB_RGB_5V',650,610,'0805'),
          ('C322','1u 25V RGB VCC','CL10B105KA8NNNC','KB_RGB_5V',710,610,'0603'),
          ('C323','100n 50V RGB VCC','CL10B104KB8NNNC','KB_RGB_5V',760,610,'0603'),
          ('C324','1u 25V RGB PVCC','CL10B105KA8NNNC','KB_RGB_5V',820,610,'0603'),
          ('C325','100n 50V RGB PVCC / buffer A','CL10B104KB8NNNC','KB_RGB_5V',870,610,'0603'),
          ('C326','100n 50V RGB startup delay','CL10B104KB8NNNC','RGB_SDB',920,610,'0603')]
    for ref,value,mpn,net,x,y,size in caps:
        fp='Capacitor_SMD:C_0603_1608Metric' if size=='0603' else 'Capacitor_SMD:C_0805_2012Metric'
        s.place(ref,'C',value,x,y,footprint=fp,pin_nets={'1':(net,'local'),'2':('GND','local')},
                extra_props={'Manufacturer':'Samsung Electro-Mechanics','MPN':mpn})
    for i,net in enumerate(('KB_RGB_5V','GND','MCU_3V3','RGB_SCL','RGB_SDA','RGB_SDB'),1):
        s.place(f'TPK{i}','TestPoint',net,650+60*(i-1),670,
                footprint='TestPoint:TestPoint_Pad_D1.0mm',in_bom=False,
                pin_nets={'1':(net,'local')})
    s.pwrflag(1060,610,'KB_RGB_5V');s.pwrflag(1100,610,'MCU_3V3')
    s.text(650,710,'J320 pin 29 is the switched 5 V rail. Pin 2 needs mainboard R387 fitted for the I2C buffer.')
    s.text(650,720,'U321 A side is switched 5 V; B side is 3.3 V. Its power-off isolation keeps the unpowered LED driver off the EC bus.')
    s.text(650,730,'ADDR1/ADDR2 at VCC select 7-bit address 0x2F. SDB rises through R323/C326; wait 20 ms before setup.')
    s.text(650,740,'R320 limits peak sink current to about 11.3 mA at the datasheet corner: 18 active sinks stay below the cable budget.')
    s.text(650,750,'Keep C322/C323 close to VCC, C324/C325 close to PVCC, and R320 close to ISET. Connect the exposed pad to ground.')
