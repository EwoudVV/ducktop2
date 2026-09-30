"""Netlist-based screens for the 100 W power revision.

These are placement/routing design limits. Efficiency, current-limit scaling,
loop stability and hot fault response still need measurements on the prototype.
"""
import math
import re
from pathlib import Path
from verify_electrical_calculations import (
    Check, INDUCTORS, resistor as r, capacitor as c, divider_corners,
    buck_currents, boost_currents, mu_voltage_corners, mu_shunt_bounds,
)

ROOT=Path(__file__).resolve().parents[1]

def aon_window(v):
    uv=divider_corners(r(v,'R795'),r(v,'R796'),v.environment_tolerance('R795'),v.environment_tolerance('R796'),.4925+.020,.5075+.032,10e-9)
    ov=divider_corners(r(v,'R797'),r(v,'R798'),v.environment_tolerance('R797'),v.environment_tolerance('R798'),.4925,.5075,10e-9)
    return [
        Check('standby UV rising maximum',uv[1],'V',3.7,4.3,'LTC4368 divider, reference and leakage corners'),
        Check('standby OV falling recovery floor',divider_corners(r(v,'R797'),r(v,'R798'),v.environment_tolerance('R797'),v.environment_tolerance('R798'),.4925-.032,.5075-.020,10e-9)[0],'V',21.0,25,'LTC4368 maximum32mV OV hysteresis; source at20V+5% must recover'),
        Check('standby OV rising ceiling',ov[1],'V',21,25,'static comparator ceiling; fast overshoot remains a hardware test'),
    ]

def aon_buck(v):
    lo,hi=divider_corners(r(v,'R35'),r(v,'R36'),v.environment_tolerance('R35'),v.environment_tolerance('R36'),.784,.816)
    l,tol,isat,irms,dcr=INDUCTORS[v.mpn('L3')]
    ripple,peak,rms,_=buck_currents(25,hi,1.5,l*(1-tol)*.8,450e3)
    return [
        Check('TPS62933 MCU rail minimum',lo,'V',3.135,3.465,'0.784V reference plus divider environment corners'),
        Check('TPS62933 MCU rail maximum',hi,'V',3.135,3.465,'0.816V reference plus divider environment corners'),
        Check('TPS62933 1.5A sizing peak below minimum limit',peak,'A',0,4.2,'25V, 450kHz minimum, L -20% tolerance and -20% bias screen; standby allocation is separately limited to450mA'),
        Check('TPS62933 inductor RMS sizing screen',rms,'A',0,irms,'25C manufacturer RMS characterization; installed temperature not measured'),
        Check('TPS62933 inductor copper loss at125C',rms*rms*dcr*1.393,'W',0,.30,'DCRmax with copper TCR; switching/core loss excluded'),
        Check('TPS62933 soft-start capacitor',c(v,'C2640')*1e6,'uF',.99,1.01,'external slow-start nominal1uF; biased capacitance and startup separately checked'),
        Check('TPS62933 local output bank',(c(v,'C39')+c(v,'C291'))*1e6,'uF',43,45,'nominal44uF; effective-capacitance requirement in addendum'),
    ]

def charger(v):
    return [
        Check('ISL9241 input shunt',r(v,'RS2600')*1000,'mOhm',20,20,'20mOhm matches adapter current-register scaling'),
        Check('ISL9241 battery shunt',r(v,'RS2601')*1000,'mOhm',10,10,'10mOhm matches charge/discharge current-register scaling'),
        Check('ISL9241 3S startup selection',r(v,'R18'),'Ohm',2209,2211,'2.21k PROG selects3S,724kHz and200mA adapter startup'),
        Check('ISL9241 input-shunt 4.4A loss',4.4**2*r(v,'RS2600')*1.08,'W',0,2*(170-100)/(170-70),'8% component envelope includes fixed-ohm drift; 2W rating derated to100C'),
        Check('ISL9241 battery-shunt 4A loss',4**2*r(v,'RS2601')*1.14,'W',0,2*(170-100)/(170-70),'14% component screen includes fixed-ohm drift; physical shunt temperature remains unmeasured'),
    ]

def pd_switch(name,v,base):
    current=1489/r(v,f'R{base+3}')
    return [
        Check(name+' nominal breaker setting',current,'A',5.5,5.7,'TPS25982 nominal1490/R approximation; this does not establish a guaranteed5A cable limit'),
        Check(name+' discharge resistor at21V',21**2/(r(v,f'R{base}')*.95),'W',0,1*(155-85)/(155-70),'1W resistor with5% resistance screen, derated to85C'),
        Check(name+' slew capacitor',c(v,f'C{base+2}')*1e9,'nF',9.9,10.1,'10nF C0G nominal; downstream inrush and source response require measurement'),
    ]

def mu_operating(v):
    l,tol,isat,irms,dcr=INDUCTORS[v.mpn('L750')]
    vlo,vhi=mu_voltage_corners(v);slow,shigh=mu_shunt_bounds(v)
    frequency=20e9/r(v,'R756')*.90*.93/(1+v.environment_tolerance('R756'))
    lmin=l*(1-tol)*.70
    avg,ripple,peak,rms=boost_currents(10,vhi,5.5,lmin,frequency,.85)
    # Datasheet limits are at20k,8Vin,20Vout,500kHz. Resistor scaling
    # is a design screen, not a guaranteed limit at this12V/400kHz point.
    imin=14*20000/(r(v,'R758')*(1+v.environment_tolerance('R758')))
    return [
        Check('Mu5.5A allocation below output-limit minimum',.048/shigh,'A',5.5,math.inf,'parallel16m shunts;6% component plus0.2% Kelvin resistance screen'),
        Check('Mu5.5A scaled average-current margin',imin/avg,'x',1.25,math.inf,'10V minimum full-load input and85% efficiency; resistor-scaled14A table minimum; verify at12V output'),
        Check('Mu5.5A operating peak screen',peak,'A',0,isat*.8,'L tolerance/bias and20% hot-Isat stress; no guaranteed fault peak-clamp maximum is published'),
        Check('Mu5.5A operating RMS screen',rms,'A',0,irms,'manufacturer25C/20C-rise reference; installed temperature remains unmeasured'),
        Check('Mu inductor copper loss at125C',rms*rms*dcr*1.393,'W',0,1.6,'copper loss only; core and switching losses excluded'),
        Check('Mu minimum inductance screen',lmin*1e6,'uH',1.2/frequency*1e6,math.inf,'TI L>1.2/fSW; L -20% tolerance/-30% bias; oscillator -10%/dither -7%'),
        Check('Mu per-shunt dissipation at5.5A',(5.5/2*1.06)**2*r(v,'RS750')*1.06,'W',0,(125-100)/(125-70),'current-sharing imbalance and resistance high corner;1W derated tocase100C'),
        Check('Mu COMP series resistor',r(v,'R755'),'Ohm',14999,15001,'reviewed15k/10n/100p compensation candidate; loop gain still requires measurement'),
        Check('Mu COMP capacitor',c(v,'C771')*1e9,'nF',9.9,10.1,'C0G10nF nominal'),
        Check('Mu COMP HF capacitor',c(v,'C772')*1e12,'pF',99,101,'C0G100pF nominal'),
    ]

def mu_rail(v):
    vlo,vhi=mu_voltage_corners(v);slow,shigh=mu_shunt_bounds(v)
    budget=int(re.search(r'normal_mu_edp_budget_mw\s*=\s*(\d+)',(ROOT/'firmware/ec_target/power_profile.h').read_text())[1])/1000
    fan=vhi*.26
    uvlo,uvhi=divider_corners(r(v,'R759'),r(v,'R760'),v.environment_tolerance('R759'),v.environment_tolerance('R760'),1.20,1.26)
    return [
        Check('TPS552882 MU rail minimum',vlo,'V',11.4,12.6,'1.188V plus divider and100nA leakage corners'),
        Check('TPS552882 MU rail maximum',vhi,'V',11.4,12.6,'1.212V plus divider and100nA leakage corners'),
        Check('Mu nominal output-current limit',.050/(1/(1/r(v,'RS750')+1/r(v,'RS2670'))),'A',6.24,6.26,'50mV across two parallel16m shunts'),
        Check('Mu/display budget plus fan within5.5A envelope',budget+fan,'W',0,5.5*vlo,'target firmware budget plus0.26A fan at high voltage versus5.5A at low voltage'),
        Check('Mu/display budget plus fan below current-limit floor',budget+fan,'W',0,.048/shigh*vlo,'independent rail-voltage and current-limit low corners'),
        Check('Mu full-load VSYS floor above UVLO maximum',uvhi,'V',8.8,10.0,'full5.5A operating screen begins at10V; lower input needs power throttling'),
        Check('Mu switching frequency',20e9/r(v,'R756')/1000,'kHz',380,420,'20e9/RFSW'),
        Check('Mu fail-off gate at8.45V',8.45*r(v,'R761')/(r(v,'R766')+r(v,'R761')),'V',4,4.5,'reset-state pull-up divider'),
        Check('Delta blower PTC hold-current margin',r(v,'F200')/.26,'x',2.5,3.2,'fuse hold current/0.26A blower maximum'),
        Check('Delta blower FG RC cutoff',1/(2*math.pi*r(v,'R206')*c(v,'C209'))/1000,'kHz',4.5,5.5,'1/(2*pi*R*C)'),
    ]
