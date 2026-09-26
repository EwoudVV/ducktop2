"""Reset-safe AUX permission and independent charger-bias observation."""
from build_ducktop2 import FOOTPRINTS


def add_power_control(s):
    hier={'MCU_3V3','I2C_SDA','I2C_SCL','NRST_NET','MU_PROCHOT_N','AUX_DC_ADC'}
    def n(name):return(name,'nc' if not name else 'hier' if name in hier else 'local')
    def part(ref,sym,value,x,y,fp,pins,mpn,maker='Texas Instruments'):
        s.place(ref,sym,value,x,y,footprint=fp,pin_nets={str(k):n(v) for k,v in pins.items()},
                extra_props={'Manufacturer':maker,'MPN':mpn})
    def r(ref,value,x,y,a,b,mpn):
        part(ref,'R',value,x,y,FOOTPRINTS['R'],{1:a,2:b},mpn,'Yageo')
    def bypass(ref,x,y):
        part(ref,'C','100n 50V bypass',x,y,FOOTPRINTS['C_100n'],
             {1:'MCU_3V3',2:'GND'},'GRM188R71H104KA93D','Murata')
    s.text(1200,20,'== source-control interlocks ==')
    part('U2634','TPS3700','TPS3700DDCR charger-bias detector',1240,80,
         'Package_TO_SOT_SMD:SOT-23-6',{1:'CHG_BIAS_GOOD',2:'GND',3:'CHG_BIAS_SENSE',
         4:'GND',5:'MCU_3V3',6:''},'TPS3700DDCR')
    r('R2640','100k 1% bias sense top',1200,120,'REGN','CHG_BIAS_SENSE','RC0603FR-07100KL')
    r('R2641','24.9k 1% bias sense bottom',1280,120,'CHG_BIAS_SENSE','GND','RC0603FR-0724K9L')
    r('R2642','10k bias-good pull-up',1200,140,'MCU_3V3','CHG_BIAS_GOOD','RC0603FR-0710KL')
    bypass('C2641',1280,140)
    part('U2635','PCA9537','TCA9537DGSR power status and AUX control',1240,200,
         'Package_SO:MSOP-10_3x3mm_P0.5mm',{1:'AUX_PATH_EN',2:'CHG_BIAS_GOOD',
         3:'PACK_CHG_TEMP_OK_IN',4:'MU_PROCHOT_N',5:'GND',6:'NRST_NET',7:'',
         8:'I2C_SCL',9:'I2C_SDA',10:'MCU_3V3'},'TCA9537DGSR')
    bypass('C2642',1200,240)
    r('R2643','100k PROCHOT sense default-low',1280,240,'MU_PROCHOT_N','GND','RC0603FR-07100KL')
    r('R2644','10k AUX permission series',1200,275,'AUX_PATH_EN','AUX_EFUSE_SHDN','RC0603FR-0710KL')
    r('R2645','47k AUX permission default-off',1280,275,'AUX_EFUSE_SHDN','GND','RC0603FR-0747KL')
    part('U2644','74LVC1G04','SN74LVC1G04DBVR AUX discharge',1200,315,
         FOOTPRINTS['SN74LVC1G08DBV'],{1:'',2:'AUX_PATH_EN',3:'GND',4:'AUX_DISCHARGE',5:'MCU_3V3'},'SN74LVC1G04DBVR')
    part('Q2644','Q_NMOS_SOT23_GSD','BSS138 AUX discharge',1280,315,
         FOOTPRINTS['Q_BSS138'],{1:'AUX_DISCHARGE',2:'GND',3:'AUX_DISCHARGE_DRAIN'},'BSS138LT1G','onsemi')
    part('R2646','R','1k 1W switched AUX discharge',1200,350,
         'Resistor_SMD:R_2512_6332Metric',{1:'AUX_DC_PROTECTED',2:'AUX_DISCHARGE_DRAIN'},'RC2512FR-071KL','Yageo')
    r('R2647','100k discharge gate default-low',1280,350,'AUX_DISCHARGE','GND','RC0603FR-07100KL')
    bypass('C2643',1200,370)
    part('D2640','BAT54S_AKC','BAT54S AUX ADC rail clamps',1280,370,
         'Package_TO_SOT_SMD:SOT-23',{1:'GND',2:'MCU_3V3',3:'AUX_DC_ADC'},
         'BAT54S,215','Nexperia')
    s.text(1200,410,'A low bias indication means REGN is below about 2V, beneath the charger reset threshold. Wait for detector startup before using it.')
    s.text(1200,420,'A powered charger must acknowledge a low input limit before any source is enabled. An I2C failure alone is not proof of reset.')
