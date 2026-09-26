"""Separate I/O power looms and conservative assembly acceptance limits.

Current ratings use the populated circuit count. Resistance limits are
assembly requirements, not measurements or inferred cable guarantees.
"""
import genlib

LEFT_POWER_PINMAP = {1:'VSYS',2:'PD1_VBUS_RAW',3:'USB_PD_SELECTED',4:'AUX_DC_RAW',
                     5:'SYS_3V3',6:'MCU_3V3',7:'GND'}
RIGHT_POWER_PINMAP = {1:'PD2_VBUS_GATED',2:'PD2_VBUS_RAW',3:'SYS_5V',4:'SYS_3V3',
                      5:'PCIE_3V3',6:'MCU_3V3',7:'GND'}
USB5_POWER_PINMAP = {1:'GND',2:'USB_PORT_5V'}
SEAMS = {
    'left': {'refs':{'center':'J2430','io':'J2431'},'aux_refs':{'center':'J2450','io':'J2451'},
             'return_refs':{'center':'J2460','io':'J2461'},'pins':LEFT_POWER_PINMAP,
             'header':'2060-453/998-404','length_min_mm':20,'length_max_mm':100},
    'right':{'refs':{'center':'J2432','io':'J2433'},'aux_refs':{'center':'J2452','io':'J2453'},
             'return_refs':{'center':'J2462','io':'J2463'},'pins':RIGHT_POWER_PINMAP,
             'header':'2060-453/998-404','length_min_mm':20,'length_max_mm':100},
    'usb5': {'refs':{'left':'J2434','right':'J2435'},'pins':USB5_POWER_PINMAP,
             'header':'XT30PW-F30.G.Y','housing':'XT30U-M.G.Y','length_min_mm':400,'length_max_mm':420},
}

def terminal_groups(loom,side):
    spec=SEAMS[loom];pins=spec['pins'];groups=[]
    for key,logical in [('refs',[1,2,3]),('aux_refs',[4,5,6]),('return_refs',[7])]:
        ordered=list(reversed(logical)) if side=='center' else logical
        mapping={str(i+1):pins[n] for i,n in enumerate(ordered)}
        groups.append((spec[key][side],mapping))
    return groups

CONTACT_MPN=None  # bare stranded wire enters the spring terminal
WIRE_SERIES='Alpha Wire 6715'
WIRE_ORDER_CODES={'positive':'6715 RD005','return':'6715 BK005'}
# Alpha 6715: 18 AWG 16/30 tinned copper, UL11028, OD 0.067 +/-0.002 in.
WIRE_MAX_OD_MM=1.7526
WIRE_MIN_TEMPERATURE_C=-40
WIRE_MAX_TEMPERATURE_C=105
LOOM_MATED_BODY_HEIGHT_MM=4.5
WIRE_BEND_RADIUS_MIN_MM=8.763
# WAGO 2060, three poles, 18 AWG: 9 A IEC and UL rating.
CONTACT_CONTINUOUS_SCREEN_A=9.0
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
USB5_RETURN_CONTINUOUS_A=10.0
USB5_TERMINATION_HOT_MAX_OHM=.005
USB5_WIRE_SERIES='Alpha Wire 6716'
USB5_WIRE_ORDER_CODES={'positive':'6716 RD005','return':'6716 BK005'}
USB5_WIRE_MAX_OD_MM=2.1082
USB5_WIRE_BEND_RADIUS_MIN_MM=10.541
USB5_CONNECTOR_MAX_TEMPERATURE_C=80
USB5_MATED_HEIGHT_MAX_MM=5.75
USB5_MATED_LENGTH_MAX_MM=23.10
USB5_MATED_WIDTH_MAX_MM=13.60
SEAM_RETURN_MIN_OHM=.00012
SEAM_BRAID_MAX_OHM=.001
SEAM_GROUND_DIFFERENCE_MAX_V=.010


def ground_terminal_current_bound(total_cut_a, wire_min_ohm=SEAM_RETURN_MIN_OHM,
                                  braid_max_ohm=SEAM_BRAID_MAX_OHM):
    """One remaining braid; no credit for equal sharing or the signal cable."""
    if total_cut_a<0 or wire_min_ohm<=0 or braid_max_ohm<=0:raise ValueError('invalid return bounds')
    return total_cut_a/(1+wire_min_ohm/braid_max_ohm)


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
                'Wire':'Alpha 6716 RD005/BK005; 16 AWG 26/30 tinned copper, mPPE',
                'HarnessWireLength':'400..420 mm between solder terminations; 420 mm nominal cut target, dress slack above minimum bend radius',
                'HarnessPinOrder':'1 negative/GND; 2 positive/USB5; continuity and isolation test before power',
                'CurrentRatingBasis':'AMASS 2025V0: 20 A at up to 85 K rise; project return design 10 A with 16 AWG wire, qualification <=80 C',
                'ResistanceAcceptance':'each mated/soldered termination <=5 mOhm hot/aged; wire <=30 mOhm/m hot',
                'MatedEnvelope':'23.10 x 13.60 x 5.75 mm conservative; reserve sleeve and 10.541 mm wire bend radius',
                'CableEnvelope':'rounded exit path 354.47 mm GND / 364.47 mm USB5; retain up to 12 mm termination/sleeve allowance and fit remaining height/service detour before assembly',
                'Assembly':'unpowered mating only; insulate solder joints and strain-relieve wires independently; retention lands isolated',
                'Fabrication':'power holes 1.85 +/-0.05 mm, retention holes 1.15 +/-0.05 mm finished diameter',
                'Datasheet':'https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf'})
    result=None
    for index,(ref,mapping) in enumerate(terminal_groups(loom,side)):
        n=len(mapping);symbol=f'Conn_01x{n:02d}'
        genlib.LIBMAP.setdefault(symbol,'Connector_Generic')
        result=s.place(ref,symbol,loom+' power '+('return' if n==1 else 'rails'),x,y+25*index,
            footprint=f'ducktop2:WAGO_2060_{450+n}_SMD',
            pin_nets={pin:(net,'local' if net=='GND' else 'hier') for pin,net in mapping.items()},
            extra_props={'Manufacturer':'WAGO','MPN':f'2060-{450+n}/998-404',
                'Wire':'Alpha 6715, 18 AWG 16/30 tinned copper; no ferrule',
                'Assembly':'strip 7..9 mm; hold the button to insert or remove stranded wire; never solder-tin the wire end',
                'HarnessPinOrder':'match rail names in the harness drawing; each three-pole group reverses at the center board',
                'CurrentRatingBasis':'9 A IEC and UL; the 10 A ground-cut screen requires both seam braids installed and covers one open braid',
                'ReturnAcceptance':'remaining complete braid <=1 mOhm; each return wire >=0.12 mOhm cold; terminal current <=8.93 A at a 10 A cut',
                'MatedHeight':'4.5 mm terminal body; wire and release-tool envelopes are separate',
                'Datasheet':'https://www.wago.com/2060-453/998-404'})
    return result


def add_board_power(s, fpc_ref):
    mapping={'FPC101':('left','io'),'FPC102':('left','center'),
             'FPC103':('right','center'),'FPC104':('right','io')}
    if fpc_ref not in mapping:return
    loom,side=mapping[fpc_ref]
    add_connector(s,loom,side,230,160)
    if side=='io':add_connector(s,'usb5',loom,230,230)
    s.text(180,310,'Power uses the separate rated looms. The signal cable carries no positive supply rails.')
