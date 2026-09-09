"""Separate I/O power looms and conservative assembly acceptance limits.

Current ratings use the populated circuit count. Resistance limits are
assembly requirements, not measurements or inferred cable guarantees.
"""
import genlib

LEFT_POWER_PINMAP = {1:'VSYS',2:'PD1_VBUS_RAW',3:'USB_PD_SELECTED',4:'AUX_DC_RAW',
                     5:'SYS_3V3',6:'MCU_3V3',**{n:'GND' for n in range(7,13)}}
RIGHT_POWER_PINMAP = {1:'PD2_VBUS_GATED',2:'PD2_VBUS_RAW',3:'SYS_5V',4:'SYS_3V3',
                      5:'PCIE_3V3',6:'MCU_3V3',**{n:'GND' for n in range(7,11)}}
USB5_POWER_PINMAP = {1:'GND',2:'USB_PORT_5V'}
SEAMS = {
    'left': {'refs':{'center':'J2430','io':'J2431'},'pins':LEFT_POWER_PINMAP,
             'header':'43045-1212','housing':'43025-1200','length_min_mm':90,'length_max_mm':100},
    'right':{'refs':{'center':'J2432','io':'J2433'},'pins':RIGHT_POWER_PINMAP,
             'header':'43045-1012','housing':'43025-1000','length_min_mm':90,'length_max_mm':100},
    'usb5': {'refs':{'left':'J2434','right':'J2435'},'pins':USB5_POWER_PINMAP,
             'header':'XT30PW-F30.G.Y','housing':'XT30U-M.G.Y','length_min_mm':400,'length_max_mm':420},
}
CONTACT_MPN='43030-0038'
WIRE_SERIES='Alpha Wire 3253'
WIRE_ORDER_CODES={'positive':'3253 RD005','return':'3253 BK005'}
# Alpha 3253: 18 AWG 7/26 tinned copper, UL1061, OD 0.068 +/-0.002 in.
WIRE_MAX_OD_MM=1.778
WIRE_MIN_TEMPERATURE_C=-10
WIRE_MAX_TEMPERATURE_C=80
LOOM_MATED_BODY_HEIGHT_MM=17.64
WIRE_BEND_RADIUS_MIN_MM=17.78
# Molex PS-43045 revision R (2025-11-14), pp8/12/13/15:
# 18 AWG all circuits powered: 6 circuits 6.5 A, 12 circuits 5.5 A at 30 C rise.
# Use the lower 12-circuit screen for both Micro-Fit looms, never the 2-circuit 8.5 A.
CONTACT_CONTINUOUS_SCREEN_A=5.5
CONTACT_INITIAL_MAX_OHM=.010
CRIMP_INITIAL_MAX_OHM=.005
CONTACT_LIFE_CHANGE_OHM=.020
# Includes initial contact, crimp, life change and an additional hot-state
# allowance. The published LLCR tests alone do not guarantee this hot bound.
TERMINATION_HOT_MAX_OHM=.045
WIRE_HOT_MAX_OHM_PER_M=.030
USB5_BOARD_LOOP_MAX_OHM=.020
USB5_GROUND_DIFFERENCE_MAX_V=.020
USB5_RIGHT_CURRENT_MAX_A=2.015
USB5_RETURN_CONTINUOUS_A=8.0
USB5_TERMINATION_HOT_MAX_OHM=.005
USB5_WIRE_SERIES='Alpha Wire 5857'
USB5_WIRE_ORDER_CODES={'positive':'5857 RD005','return':'5857 BK005'}
USB5_WIRE_MAX_OD_MM=1.8796
USB5_WIRE_BEND_RADIUS_MIN_MM=18.796
USB5_CONNECTOR_MAX_TEMPERATURE_C=80
USB5_MATED_HEIGHT_MAX_MM=5.75
USB5_MATED_LENGTH_MAX_MM=23.10
USB5_MATED_WIDTH_MAX_MM=13.60
SEAM_RETURN_MIN_OHM=.002
SEAM_GROUND_DIFFERENCE_MAX_V=.010


def boundary_nets(pinmap):
    return sorted(set(pinmap.values())-{'GND'})


def conductor_max_resistance(length_mm):
    if length_mm<=0 or length_mm>300:raise ValueError('unqualified power loom length')
    return 2*TERMINATION_HOT_MAX_OHM+length_mm/1000*WIRE_HOT_MAX_OHM_PER_M


def parallel_resistance(resistances):
    if not resistances or any(r<=0 for r in resistances):raise ValueError('invalid conductor resistance')
    return 1/sum(1/r for r in resistances)


def usb5_conductor_max_resistance(length_mm):
    if not 400<=length_mm<=420:raise ValueError('unqualified direct USB loom length')
    return 2*USB5_TERMINATION_HOT_MAX_OHM+length_mm/1000*WIRE_HOT_MAX_OHM_PER_M


def right_pp5v_minimum(rail_min_v=5.102994474,ripple_v=.020):
    positive=usb5_conductor_max_resistance(SEAMS['usb5']['length_max_mm'])
    # One full-current-rated contact and wire per polarity.
    # The ground limit includes all signed return current through the seam
    # bonds, cable returns and shields. It is not added to another assumed
    # equal-share return drop and is not yet physical qualification evidence.
    return rail_min_v-ripple_v-USB5_RIGHT_CURRENT_MAX_A*(positive+USB5_BOARD_LOOP_MAX_OHM)-\
           USB5_GROUND_DIFFERENCE_MAX_V-1.216*.014


def right_usb2_vbus_minimum():
    # Remove PP5V-gate loss, then apply J12's own chain. The 40 mV hot
    # TPD1S514 allowance is an explicit device/assembly acceptance limit.
    return right_pp5v_minimum()+1.216*.014-.775*.135-.500*(.046+.050)-.040



def add_connector(s, loom, side, x, y):
    spec=SEAMS[loom];pins=spec['pins'];count=len(pins)
    if loom=='usb5':
        genlib.LIBMAP.setdefault('Conn_01x02','Connector_Generic')
        return s.place(spec['refs'][side],'Conn_01x02','USB5 direct power loom',x,y,
            footprint='ducktop2:AMASS_XT30PW-F30_G_Y',
            pin_nets={'1':('GND','local'),'2':('USB_PORT_5V','hier')},
            extra_props={'Manufacturer':'AMASS','MPN':'XT30PW-F30.G.Y','MatingHousing':'XT30U-M.G.Y',
                'Wire':'Alpha 5857 RD005/BK005; 18 AWG 19/30 silver-plated copper, PTFE',
                'HarnessWireLength':'400..420 mm between solder terminations; 420 mm nominal cut target, dress slack above minimum bend radius',
                'HarnessPinOrder':'1 negative/GND; 2 positive/USB5; continuity and isolation test before power',
                'CurrentRatingBasis':'AMASS 2025V0: 20 A at up to 85 K rise; project return design 8 A, qualification <=80 C',
                'ResistanceAcceptance':'each mated/soldered termination <=5 mOhm hot/aged; wire <=30 mOhm/m hot',
                'MatedEnvelope':'23.10 x 13.60 x 5.75 mm conservative; reserve sleeve and 18.80 mm wire bend radius',
                'CableEnvelope':'rounded exit path 370.47 mm GND / 380.47 mm USB5; retain up to 12 mm termination/sleeve allowance and fit remaining height/service detour before assembly',
                'Assembly':'unpowered mating only; insulate solder joints and strain-relieve wires independently; retention lands isolated',
                'Fabrication':'power holes 1.85 +/-0.05 mm, retention holes 1.15 +/-0.05 mm finished diameter',
                'Datasheet':'https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf'})
    symbol=f'Conn_02x{count//2:02d}_Odd_Even'
    genlib.LIBMAP.setdefault(symbol,'Connector_Generic')
    ref=spec['refs'][side]
    fp=f"Connector_Molex:Molex_Micro-Fit_3.0_{spec['header']}_2x{count//2:02d}_P3.00mm_Vertical"
    return s.place(ref,symbol,loom+' power loom, straight-numbered',x,y,footprint=fp,
        pin_nets={str(n):(net,'local' if net=='GND' else 'hier') for n,net in pins.items()},
        extra_props={'Manufacturer':'Molex','MPN':spec['header'],'MatingHousing':spec['housing'],
            'Contacts':CONTACT_MPN+' tin 18 AWG','Wire':WIRE_SERIES+' UL1061 18 AWG tinned stranded',
            'HarnessWireLength':str(spec['length_min_mm'])+'..'+str(spec['length_max_mm'])+' mm between crimp barrels, including tolerance',
            'HarnessPinOrder':'pin n to pin n; continuity and isolation test every conductor',
            'CurrentRatingBasis':'PS-43045 R; use 12-circuit 18 AWG 5.5 A reference screen; assembled wire <=80 C',
            'ResistanceAcceptance':'termination <=45 mOhm hot/aged; wire <=30 mOhm/m hot; each return >='+'2 mOhm cold',
            'MatedHeight':'17.64 mm connector body; current 90..100 mm wire poses require about 55 mm individual-loop clearance; qualify bundle crossing, exact crimp allowance and cover fit',
            'Datasheet':'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43045/430451012_sd.pdf'})


def add_board_power(s, fpc_ref):
    mapping={'FPC101':('left','io'),'FPC102':('left','center'),
             'FPC103':('right','center'),'FPC104':('right','io')}
    if fpc_ref not in mapping:return
    loom,side=mapping[fpc_ref]
    add_connector(s,loom,side,230,160)
    if side=='io':add_connector(s,'usb5',loom,230,230)
    s.text(180,310,'Power uses the separate rated looms. The signal cable carries no positive supply rails.')
