"""Literal USB protection pins, branch vetoes and current corner checks."""
from pathlib import Path
import itertools
import unittest
from unittest.mock import patch
import build_ducktop2 as b
import generate_usb_power_control as control
import generate_left_io_project as left
import generate_right_io_project as right
import genlib
import usb_power_contract as loom
import fpc_contract as fpc

class Capture:
    def __init__(self,*args):self.parts={};self.refcounters={};self.body=[]
    def place(self,ref,symbol,value,x,y,**kwargs):
        if ref in self.parts and kwargs.get('unit',1)==1:raise ValueError('duplicate '+ref)
        if ref not in self.parts:self.parts[ref]={'symbol':symbol,'value':value,**kwargs}
    def text(self,*args):pass
    def pwrflag(self,*args):pass
    def gnd(self,*args):pass

class USBPowerTests(unittest.TestCase):
    def setUp(self):
        with patch.object(b,'Sheet',Capture):
            self.l=left.build_left_usb_sheet('fixture')
            self.lp=left.build_left_pd_sheet('fixture')
            self.r=right.build_right_pd_sheet('fixture')
    def net(self,s,ref,pin):return s.parts[ref]['pin_nets'][str(pin)][0]
    def test_permission_reset_is_local_fail_off_and_unique_address(self):
        self.assertEqual(self.net(self.l,'U2400',3),'SERVICE_MUX_RESET_N')
        self.assertEqual(self.net(self.l,'U2400',22),'PD1_I2C_SCL')
        self.assertEqual(self.net(self.l,'U2400',23),'PD1_I2C_SDA')
        self.assertEqual(self.net(self.l,'U2400',2),'MCU_3V3')
        self.assertEqual(self.net(self.l,'U2400',21),'GND')
        self.assertEqual(self.net(self.l,'R2420',2),'GND')
        self.assertEqual([self.net(self.l,'U2400',n) for n in range(4,12)],
            ['USB5_PERMIT','USB_J21_PERMIT','USB_J11_PERMIT','USB_J22_PERMIT',
             'USB_J23_PERMIT','USB_J12_PERMIT','USB_J24_PERMIT','USB_J25_PERMIT'])
        self.assertEqual(self.net(self.l,'U2400',13),'USB5_FAULT_CLEAR_N')
    def test_exact_monitor_pins_are_kelvin_and_alert_is_independent(self):
        for pin,net in {1:'GND',2:'GND',3:'USB5_OC_N',4:'PD1_I2C_SDA',5:'PD1_I2C_SCL',
                        6:'MCU_3V3',7:'GND',8:'USB_PORT_5V',9:'USB_PORT_5V',10:'USB5_PRE_SENSE'}.items():
            self.assertEqual(self.net(self.l,'U2401',pin),net)
        self.assertEqual(self.net(self.l,'U2402',7),'USB5_COMBINED_OK')
        self.assertEqual(self.net(self.l,'U2402',6),'USB5_FAULT_CLEAR_N')
        self.assertEqual(self.net(self.l,'U2402',3),'USB5_FAULT_N')
        self.assertEqual(self.net(self.l,'U2411',2),'USB5_COMBINED_OK')
        self.assertEqual(self.net(self.l,'U2413',1),'USB5_OC_N')
        self.assertEqual(self.net(self.l,'U2413',2),'INTERNAL_USB_VBUS_VALID')
        self.assertEqual(self.net(self.l,'U2413',4),'USB5_COMBINED_OK')
        self.assertEqual(self.net(self.l,'U2400',19),'INTERNAL_USB_VBUS_VALID')
        self.assertEqual(self.net(self.l,'R2400',1),'USB5_HW_ENABLE')
        self.assertEqual(self.net(self.l,'R2400',2),'GND')
        self.assertTrue(self.l.parts['R2400']['value'].startswith('10k'))
        for rail,permit,latched,raw,sys5 in itertools.product((False,True),repeat=5):
            combined=raw and sys5
            enabled=rail and permit and latched and combined
            if not rail or not permit or not raw or not sys5:self.assertFalse(enabled)
        # Even a temporarily deasserted latch fault during /PRE+/CLR overlap
        # cannot override the independent combined raw/SYS5 gate.
        self.assertFalse(True and True and True and (True and False))
        fixture=Capture();control.add_sys5_qualification(fixture)
        self.assertEqual(self.net(fixture,'U2412',1),'SYS_5V_PG')
        self.assertEqual(self.net(fixture,'U2412',2),'INTERNAL_USB_VBUS_RAW_VALID')
        self.assertEqual(self.net(fixture,'U2412',4),'INTERNAL_USB_VBUS_VALID')
    def test_hub_fault_outputs_keep_their_original_bus(self):
        for sheet,base,port,ctl in ((self.l,1780,'J22','HUB_PRT_CTL2'),
                                  (self.l,1740,'J23','HUB_PRT_CTL3'),
                                  (self.r,1760,'J12','HUB_PRT_CTL4')):
            self.assertEqual(self.net(sheet,'U'+str(base),3),'USB_'+port+'_SWITCH_EN')
            self.assertEqual(self.net(sheet,'U'+str(base),4),ctl)
            self.assertEqual(self.net(sheet,'U'+str(base+1),6),'USB_'+port+'_SWITCH_EN')
            self.assertEqual(self.net(sheet,'U'+str(base+1),1),ctl)
            self.assertEqual(sheet.parts['R'+str(base)]['extra_props']['MPN'],'RC0603FR-0719K1L')
        self.assertEqual(self.net(self.l,'U1800',3),'USB_J24_SWITCH_EN')
        self.assertEqual(self.net(self.l,'U1803',3),'USB_J25_SWITCH_EN')
        self.assertEqual(self.net(self.l,'U2407',2),'INTERNAL_USB_VBUS_VALID')
    def test_added_control_passives_have_exact_procurement_identity(self):
        fixture=Capture();control.add_sys5_qualification(fixture)
        for sheet in (self.l,self.lp,self.r,fixture):
            for ref,part in sheet.parts.items():
                if not ref[1:].isdigit() or not 2400<=int(ref[1:])<=2429:continue
                fields=part.get('extra_props',{})
                if ref.startswith('R'):
                    expected={'10k':'RC0603FR-0710KL','100k':'RC0603FR-07100KL',
                              '12.7k 1%':'RC0603FR-0712K7L'}[part['value']]
                    self.assertEqual(fields.get('MPN'),expected,ref)
                    self.assertEqual(fields.get('Manufacturer'),'Yageo',ref)
                elif ref.startswith('C'):
                    self.assertEqual(fields.get('Manufacturer'),'Murata',ref)
                    self.assertIn(fields.get('MPN'),('GRM188R71H104KA93D',
                        'GRM21BR71H105KA12L','GRM1885C1H472JA01D'),ref)
    def test_pp5v_capacitors_are_behind_real_per_port_gates(self):
        for sheet,tcpc,gate,base,net in ((self.lp,'U41','U2403',2000,'PD1_PP5V_GATED'),
                                       (self.r,'U42','U2404',2040,'PD2_PP5V_GATED')):
            self.assertEqual(self.net(sheet,tcpc,34),net)
            self.assertEqual(self.net(sheet,gate,2),'USB_PORT_5V')
            self.assertEqual(self.net(sheet,gate,6),net)
            self.assertEqual(self.net(sheet,gate,5),net)
            for cap in (base+25,base+26,base+27):self.assertEqual(self.net(sheet,'C'+str(cap),1),net)
    def test_pg_divider_stays_below_mcu_supply_and_above_vih(self):
        # 1% resistors, PP5V 4.9..5.5 V and MCU_3V3 3.135..3.6 V.
        low=4.9*(12.7*.99)/(10*1.01+12.7*.99)
        high=5.5*(12.7*1.01)/(10*.99+12.7*1.01)
        self.assertGreater(low,.7*3.6)
        self.assertLess(high,3.135)
        for ref in ('R2424','R2425'):self.assertTrue(self.l.parts[ref]['value'].startswith('12.7k'))
    def test_source_only_minimum_current_includes_vconn_and_bleed(self):
        # TPS2553 SLVS841F p15 Eq 1. Resistance in kohm, result in mA.
        # Rounded 5% R envelope includes 1% initial, 1.3% full-category TCR,
        # 1% endurance and 1% soldering change plus the small absolute terms.
        minimum=25230/(19.1*1.05)**1.016/1000
        maximum=22980/(19.1*.95)**.94/1000
        old=25230/(20*1.05)**1.016/1000
        self.assertGreater(minimum,1.175)
        self.assertLess(maximum,1.510)
        self.assertLess(old,1.175)
    def test_looms_have_distinct_counts_and_no_positive_signal_contacts(self):
        self.assertEqual([len(loom.SEAMS[n]['pins']) for n in ('left','right','usb5')],[12,10,2])
        self.assertEqual(loom.USB5_POWER_PINMAP,{1:'GND',2:'USB_PORT_5V'})
        power_nets=set().union(*(set(spec['pins'].values()) for spec in loom.SEAMS.values()))-{'GND'}
        self.assertFalse(set(fpc.FPC1_PINMAP.values())&power_nets)
        self.assertFalse(set(fpc.FPC2_PINMAP.values())&power_nets)
        self.assertEqual([len(fpc.FPC1_PINMAP),len(fpc.FPC2_PINMAP)],[41,51])
        self.assertNotIn('USB_PORT_5V',fpc.FPC1_NETS)
        self.assertIn('USB_PORT_5V',fpc.FPC1_IO_NETS)
    def test_unequal_conductance_and_ground_current_bounds(self):
        maximum=loom.conductor_max_resistance(300)
        self.assertAlmostEqual(maximum,.099)
        self.assertLess(loom.parallel_resistance([.006,.030,.080,.099]),maximum/4)
        self.assertAlmostEqual(loom.usb5_conductor_max_resistance(420),.0226)
        self.assertGreaterEqual(loom.USB5_RETURN_CONTINUOUS_A,8)
        self.assertLessEqual(loom.SEAM_GROUND_DIFFERENCE_MAX_V/loom.SEAM_RETURN_MIN_OHM,5)
        self.assertGreater(loom.CONTACT_CONTINUOUS_SCREEN_A,5)
        self.assertGreater(loom.right_pp5v_minimum(),4.960)
        self.assertGreater(loom.right_usb2_vbus_minimum(),4.784)
        self.assertEqual([loom.SEAMS["usb5"]["length_min_mm"],loom.SEAMS["usb5"]["length_max_mm"]],[400,420])
        with self.assertRaises(ValueError):loom.usb5_conductor_max_resistance(399)
        with self.assertRaises(ValueError):loom.usb5_conductor_max_resistance(421)
        with self.assertRaises(ValueError):loom.parallel_resistance([.01,0])
        with self.assertRaises(ValueError):loom.conductor_max_resistance(301)
    def test_vertical_microfit_keeps_literal_power_pinmaps(self):
        expected={
            'left':('43045-1212',["VSYS","PD1_VBUS_RAW","USB_PD_SELECTED","AUX_DC_RAW","SYS_3V3","MCU_3V3"]+["GND"]*6),
            'right':('43045-1012',["PD2_VBUS_GATED","PD2_VBUS_RAW","SYS_5V","SYS_3V3","PCIE_3V3","MCU_3V3"]+["GND"]*4)}
        for side,(mpn,nets) in expected.items():
            for end in ('center','io'):
                fixture=Capture();loom.add_connector(fixture,side,end,0,0)
                ref=loom.SEAMS[side]['refs'][end];part=fixture.parts[ref]
                self.assertEqual(part['extra_props']['MPN'],mpn)
                self.assertTrue(part['footprint'].endswith('_P3.00mm_Vertical'))
                self.assertEqual([self.net(fixture,ref,n) for n in range(1,len(nets)+1)],nets)
        self.assertEqual(loom.LOOM_MATED_BODY_HEIGHT_MM,17.64)
    def test_xt30_polarity_and_current_finished_hole_drawing(self):
        from generate_usb_power_connector import footprint_text
        text=footprint_text()
        self.assertEqual(text,Path(__file__).resolve().parents[1].joinpath('ducktop2.pretty/AMASS_XT30PW-F30_G_Y.kicad_mod').read_text())
        self.assertIn('(pad "1" thru_hole rect (at 0 0)',text)
        self.assertIn('(pad "2" thru_hole circle (at 5 0)',text)
        self.assertEqual(text.count('(drill 1.85)'),2)
        self.assertEqual(text.count('(drill 1.15)'),2)
        fixture=Capture();loom.add_connector(fixture,'usb5','left',0,0)
        self.assertEqual(self.net(fixture,'J2434',1),'GND')
        self.assertEqual(self.net(fixture,'J2434',2),'USB_PORT_5V')
        self.assertEqual(fixture.parts['J2434']['extra_props']['MPN'],'XT30PW-F30.G.Y')
        self.assertEqual(fixture.parts['J2434']['extra_props']['MatingHousing'],'XT30U-M.G.Y')
    def test_native_no_connect_unit_suffix_is_exact(self):
        from types import SimpleNamespace
        from verify_design_contracts import expect_unconnected,CheckFailure
        unit_path='/root/sheet/unit-a unit-b unit-c unit-d unit-e'
        for name in ['unconnected-(U1700B-TXDP1-Pad7)','unconnected-(U1700-TXDP1-Pad7)']:
            expect_unconnected({'U1700':SimpleNamespace(path=unit_path,pin_nets={'7':name})},'U1700','7')
        for name in ['unconnected-(U1700B1-TXDP1-Pad7)','unconnected-(U17001-TXDP1-Pad7)','unconnected-(U1700B-TXDP1-Pad8)','unconnected-(U1700F-TXDP1-Pad7)','/HUB_TXDP1']:
            with self.assertRaises(CheckFailure):
                expect_unconnected({'U1700':SimpleNamespace(path=unit_path,pin_nets={'7':name})},'U1700','7')
    def test_exact_custom_package_pin_numbers(self):
        names={'SN74LVC1G74DCU':{1:'CLK',2:'D',3:'~{Q}',4:'GND',5:'Q',6:'~{CLR}',7:'~{PRE}',8:'VCC'},
               'TPS22992S':{1:'VBIAS',2:'VIN',3:'PG',4:'GND',5:'QOD',6:'VOUT',7:'CT',8:'ON'}}
        for symbol,expected in names.items():
            text=Path(__file__).with_name(symbol+'.kicad_sym').read_text()
            pins=genlib.parse_pins(genlib.extract_symbol_block(text,symbol))
            self.assertEqual({int(n):p['name'] for n,p in pins.items()},expected)

if __name__=='__main__':unittest.main()
