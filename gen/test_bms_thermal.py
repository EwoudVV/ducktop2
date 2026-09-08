"""Electrical isolation, manufacturer pins and fail-off thermal regressions."""
import unittest
from types import SimpleNamespace
import genlib
import fpc_contract
from generate_bms_thermal import add_bms_thermal
from generate_bms_thermal_library import library_text
from verify_electrical_calculations import thermal_supply_budget, NetlistValues, bms_control_checks, bms_control_budget
from verify_design_contracts import expect_unconnected, CheckFailure


class Capture:
    def __init__(self):self.parts={}
    def place(self,ref,symbol,value,x,y,**kwargs):
        if ref in self.parts:raise ValueError('duplicate reference '+ref)
        self.parts[ref]={'symbol':symbol,'value':value,**kwargs}
    def text(self,*args):pass
    def pwrflag(self,*args):pass


class BmsThermalTests(unittest.TestCase):
    def test_exact_kicad_mounting_pad_no_connect_names(self):
        for name in ('unconnected-(J2072-PadMP)','unconnected-(J2072-MountingPin-PadMP)'):
            expect_unconnected({'J2072':SimpleNamespace(pin_nets={'MP':name})},'J2072','MP')
        for name in ('GND','/CTRL_GND','unconnected-(J2071-PadMP)',
                     'unconnected-(J2072-Pad1)','unconnected-(J2072A-PadMP)',
                     'unconnected-(J2072-PadMP)-GND',None):
            with self.assertRaises(CheckFailure):
                expect_unconnected({'J2072':SimpleNamespace(pin_nets={'MP':name})},'J2072','MP')

    def setUp(self):
        self.capture=Capture();add_bms_thermal(self.capture);self.parts=self.capture.parts
    def net(self,ref,pin):return self.parts[ref]['pin_nets'][str(pin)][0]

    def test_primary_iso7041_pin_table_and_refresh(self):
        pins=genlib.parse_pins(genlib.extract_symbol_block(library_text(),'ISO7041FDBQ'))
        for number,name in {'1':'VCC1','3':'INA','4':'INB','7':'EN1','10':'EN2',
                            '13':'OUTB','14':'OUTA','16':'VCC2'}.items():
            self.assertEqual(pins[number]['name'],name)
        self.assertEqual(self.net('U2206',7),'PACK_NEG_RAW')
        self.assertEqual(self.net('U2206',10),'CTRL_GND')
        self.assertEqual(self.net('U2206',3),'THERM_CHG_GATE')
        self.assertEqual(self.net('U2206',4),'THERM_DSG_GATE')
        self.assertEqual(self.net('U2206',14),'THERM_CHG_HEALTH_ISO')
        self.assertEqual(self.net('U2206',13),'THERM_DSG_HEALTH_ISO')

    def test_only_isolators_span_control_and_pack_domains(self):
        control={'CTRL_GND','CTRL_3V3','MCU_3V3','PACK_FAULT_N','PACK_CHG_TEMP_OK',
                 'PACK_RETRY_PULSE','THERM_DSG_HEALTH_ISO','THERM_CHG_HEALTH_ISO',
                 'PACK_PROTECT_OK','CTRL_RETRY_IN','CTRL_FAULT_LOCAL_N'}
        spanning=[]
        for ref,part in self.parts.items():
            nets={entry[0] for entry in part['pin_nets'].values()}-{''}
            if nets & control and nets-control:spanning.append(ref)
        self.assertEqual(spanning,['U2206','U2209'])
        self.assertEqual(self.net('J2200','MP'),'PACK_NEG_RAW')

    def test_charger_fault_does_not_assert_discharge_fault(self):
        self.assertEqual(self.net('U2207',1),'THERM_DSG_HEALTH_ISO')
        self.assertEqual(self.net('U2207',3),'PACK_PROTECT_OK')
        self.assertEqual(self.net('U2207',4),'CTRL_FAULT_LOCAL_N')
        self.assertEqual(self.net('U2207',6),'CTRL_FAULT_LOCAL_N')
        self.assertEqual(fpc_contract.BMS_CONTROL_PINMAP[4],'PACK_CHG_TEMP_OK')
        self.assertEqual(fpc_contract.BMS_CONTROL_PINMAP[5],'CTRL_GND')
        self.assertEqual(fpc_contract.BMS_CONTROL_CENTER_PINMAP[5],'GND')

    def test_ltc_fault_and_retry_are_isolated_in_both_directions(self):
        self.assertEqual(self.net('U2209',1),'PROT_CTRL_3V3')
        self.assertEqual(self.net('U2209',2),'PACK_RETRY_LOCAL')
        self.assertEqual(self.net('U2209',3),'BMS_PROTECT_FAULT_N')
        self.assertEqual(self.net('U2209',4),'FG_VSS')
        self.assertEqual(self.net('U2209',5),'CTRL_GND')
        self.assertEqual(self.net('U2209',6),'PACK_PROTECT_OK')
        self.assertEqual(self.net('U2209',7),'CTRL_RETRY_IN')
        self.assertEqual(self.net('U2209',8),'CTRL_3V3')

    def test_every_center_facing_active_pin_has_current_limiting(self):
        for ref,source,destination in [('R2257','MCU_3V3','CTRL_3V3'),
            ('R2258','CTRL_FAULT_LOCAL_N','PACK_FAULT_N'),
            ('R2259','PACK_RETRY_PULSE','CTRL_RETRY_IN'),
            ('R2265','THERM_CHG_HEALTH_ISO','PACK_CHG_TEMP_OK')]:
            self.assertEqual(self.net(ref,1),source)
            self.assertEqual(self.net(ref,2),destination)
        for ref,node in [('D2201','CTRL_RETRY_IN'),('D2202','THERM_CHG_HEALTH_ISO')]:
            self.assertEqual(self.net(ref,1),'CTRL_GND')
            self.assertEqual(self.net(ref,2),'CTRL_3V3')
            self.assertEqual(self.net(ref,3),node)

    def test_ctr_gate_default_off_and_pullup_domain(self):
        for q,pull,ctr in [('Q2200','R2236','BMS_CTRC'),('Q2201','R2239','BMS_CTRD')]:
            self.assertEqual(self.net(q,2),'PACK_NEG_RAW')
            self.assertEqual(self.net(q,3),ctr)
            self.assertEqual(self.net(pull,1),'BMS_VDD')
            self.assertEqual(self.net(pull,2),ctr)
        self.assertEqual(self.net('U2205',1),'THERM_READY')
        self.assertEqual(self.net('U2205',7),'THERM_READY')

    def test_probes_are_external_and_each_lead_is_limited(self):
        for cell in range(1,4):
            probe=self.parts[f'TH{2200+cell}']
            self.assertFalse(probe['on_board'])
            self.assertEqual(probe['extra_props']['MPN'],'104JT-025')
            self.assertEqual(self.net('J2200',2*cell-1),f'THERM_PROBE_{cell}_A')
            self.assertEqual(self.net('J2200',2*cell),f'THERM_PROBE_{cell}_B')
            self.assertEqual(self.net(f'R{2211+(cell-1)*3}',2),f'THERM_PROBE_{cell}_A')
            self.assertEqual(self.net(f'R{2212+(cell-1)*3}',1),f'THERM_PROBE_{cell}_B')

    def test_raw_supply_has_current_limiter_before_every_bypass(self):
        touching_raw=[ref for ref,p in self.parts.items()
                      if any(net[0]=='PACK_POS_RAW' for net in p['pin_nets'].values())]
        self.assertEqual(touching_raw,['R2200'])
        self.assertEqual(self.parts['R2200']['extra_props']['MPN'],'RC2010FK-071KL')
        self.assertEqual(self.parts['R2200']['footprint'],'Resistor_SMD:R_2010_5025Metric')
        self.assertEqual(self.net('C2200',1),'THERM_RAW_IN')

    def test_supply_budget_and_fault_power_have_margin(self):
        result=thermal_supply_budget(1000)
        self.assertLess(result['demand_screen_a'],result['available_at_8v4_a'])
        self.assertLess(result['short_21v_w'],result['resistor_derated_85c_w'])
        self.assertGreater(result['regulator_input_min_v'],4.393)
        # A nominally convenient 10k feed cannot run this actual load screen.
        self.assertLess(thermal_supply_budget(10000)['regulator_input_min_v'],4.393)

    def test_control_island_budget_rejects_weak_fault_pullup(self):
        values=NetlistValues()
        for ref,p in self.parts.items():
            if not ref.startswith('R'):continue
            values[ref]=p['value']
            values.parts[ref]=(p['extra_props']['MPN'],p['footprint'])
        for ref in ('R708','R709'):
            values[ref]='100k';values.parts[ref]=('RC0603FR-07100KL','Resistor_SMD:R_0603_1608Metric')
        values['U2207']='SN74AUP2G07DCKR';values.parts['U2207']=('SN74AUP2G07DCKR','Package_TO_SOT_SMD:SOT-363_SC-70-6')
        self.assertTrue(all(c.passed for c in bms_control_checks(values)))
        self.assertLess(bms_control_budget(values)['control_demand_a'],.002)
        self.assertGreater(bms_control_budget(values)['fault_high_min_v']-.7*3.465,.10)
        values['R2256']='10k';values.parts['R2256']=('RC0603FR-0710KL',values.parts['R2256'][1])
        high=next(c for c in bms_control_checks(values) if 'pack-health high' in c.name)
        self.assertFalse(high.passed)

    def test_aup_buffer_preserves_all_reviewed_physical_pins(self):
        old=genlib.parse_pins(genlib.extract_symbol_block(library_text(),'SN74LVC2G07DCK'))
        new=genlib.parse_pins(genlib.extract_symbol_block(library_text(),'SN74AUP2G07DCK'))
        self.assertEqual(old,new)
        self.assertEqual(self.parts['U2207']['extra_props']['MPN'],'SN74AUP2G07DCKR')


if __name__=='__main__':unittest.main()
