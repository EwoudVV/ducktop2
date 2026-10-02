"""Fault injections for the8A design objective and independent charge guard."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest

import sync_main_pcb_from_netlist as sync
from verify_electrical_calculations import (
    bms_current_budget, bms_shunt_bounds, build_checks, component_values,
    pack_breaker_environment_checks, thermal_supply_budget, bms_uv_load_detect_voltage,
)
from verify_design_contracts import (
    CheckFailure, check_bms_pack, check_bms_current, check_bms_current_pcb,
    check_bms_control_domains, check_bms_current_pin_semantics,
    component_pin_names,
)

FIXTURE=Path(__file__).parent/'testdata/bms_current.xml'
CURRENT_REFS={'RS10','RS11','F1','J2','J2201','U2210','U2211','Q2210',
              'U2204','U2205','U2206','R850','R854','R2232','C2270','C2271',
              *(f'R{x}' for x in range(2270,2276))}


def pcb_fixture(parts):
    """A pin-parity board fixture, deliberately not a geometric DRC fixture."""
    blocks=[]
    for ref in sorted(CURRENT_REFS):
        c=parts[ref]
        body=[f'\t(footprint "{c.footprint}"',f'\t\t(property "Reference" "{ref}")']
        body.extend([f'\t\t(property "Value" "{c.value}")',
                     f'\t\t(property "MPN" "{c.properties.get("MPN", "")}")'])
        for pin,value in c.pin_nets.items():
            count=2 if ref=='J2' or (ref=='J2201' and pin=='MP') else 1
            for _ in range(count):
                connection='' if value.startswith('unconnected-') else f' (net "{value}")'
                body.append(f'\t\t(pad "{pin}" smd rect (at 0 0) (size 1 1) (layers "F.Cu"){connection})')
        body.append('\t)');blocks.append('\n'.join(body))
    return '(kicad_pcb\n'+'\n'.join(blocks)+'\n)'


class BmsCurrentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old=sync.PROJECTS['bms']
        try:
            sync.PROJECTS['bms']=(Path('unused'),FIXTURE)
            cls.base=sync.parse_netlist('bms')
        finally:
            sync.PROJECTS['bms']=old
        cls.pin_names=component_pin_names(FIXTURE)

    def setUp(self):
        self.parts=copy.deepcopy(self.base)
        self.values=component_values(FIXTURE)

    def reject_pin(self,ref,pin,net):
        self.parts[ref].pin_nets[pin]=net
        with self.assertRaises(CheckFailure):check_bms_pack(self.parts)

    def test_accepted_native_netlist_and_all_numeric_rows(self):
        check_bms_pack(self.parts)
        check_bms_current_pin_semantics(self.pin_names)
        self.assertTrue(all(row.passed for row in build_checks(self.values,{},project='bms')))
        check_bms_current_pcb(self.parts,pcb_fixture(self.parts))

    def test_full_stress_corners_are_wider_than_initial_only(self):
        lo,hi=bms_shunt_bounds(self.values,'RS10')
        self.assertAlmostEqual(lo,.002847375)
        self.assertAlmostEqual(hi,.003152625)
        result=bms_current_budget(self.values)
        self.assertAlmostEqual(result['discharge_A'][0],8.234731374648112)
        self.assertAlmostEqual(result['discharge_A'][1],9.988505202159883)
        self.assertAlmostEqual(result['charge_A'][1],4.313067825628868)
        self.assertGreater(result['ltc_forward_A'][1],result['discharge_A'][1])

    def test_swapped_polarity_fails_for_each_guard(self):
        for ref in ('U2210','U2211'):
            with self.subTest(ref=ref):
                parts=copy.deepcopy(self.base)
                nets=parts[ref].pin_nets;nets['1'],nets['2']=nets['2'],nets['1']
                with self.assertRaises(CheckFailure):check_bms_current(parts)

    def test_symbol_pin_rename_cannot_hide_swapped_inputs(self):
        names=dict(self.pin_names);names[('U2210','1')]='IN-'
        with self.assertRaises(CheckFailure):check_bms_current_pin_semantics(names)

    def test_raw_guard_ground_cannot_follow_protected_return(self):
        self.reject_pin('U2211','8','FG_VSS')

    def test_charge_alert_cannot_control_only_discharge(self):
        self.reject_pin('U2211','5','/THERM_DSG_HEALTH')

    def test_latch_cannot_bypass_startup_supervisor(self):
        self.reject_pin('U2210','6','/THERM_3V3')

    def test_enable_and_delay_are_not_silently_changed(self):
        for pin in ('4','7'):
            with self.subTest(pin=pin):
                parts=copy.deepcopy(self.base);parts['U2210'].pin_nets[pin]='/PACK_NEG_RAW'
                with self.assertRaises(CheckFailure):check_bms_current(parts)

    def test_hysteresis_pin_remains_deliberately_unconnected(self):
        self.reject_pin('U2210','10','/PACK_NEG_RAW')

    def test_missing_reset_transistor_is_rejected(self):
        self.parts.pop('Q2210')
        with self.assertRaises(CheckFailure):check_bms_current(self.parts)

    def test_reset_source_and_destination_cannot_be_omitted(self):
        for pin in ('6','11'):
            with self.subTest(pin=pin):
                parts=copy.deepcopy(self.base);parts['U2206'].pin_nets.pop(pin)
                with self.assertRaises(CheckFailure):check_bms_pack(parts)

    def test_fixed_temperature_input_still_needs_its_bias_resistor(self):
        parts=copy.deepcopy(self.base)
        parts['U719'].pin_nets['19']='unconnected-(U719-VTB-Pad19)'
        with self.assertRaises(CheckFailure):check_bms_pack(parts)
        parts=copy.deepcopy(self.base);parts.pop('R855')
        with self.assertRaises(CheckFailure):check_bms_pack(parts)
        parts=copy.deepcopy(self.base);parts['R855'].pin_nets['1']='/PACK_NEG_RAW'
        with self.assertRaises(CheckFailure):check_bms_pack(parts)

    def test_missing_supervisor_or_buffer_startup_link_is_rejected(self):
        for ref,pin in [('U2204','1'),('U2205','1'),('U2205','7')]:
            with self.subTest(ref=ref,pin=pin):
                parts=copy.deepcopy(self.base);parts[ref].pin_nets[pin]='/THERM_3V3'
                with self.assertRaises(CheckFailure):check_bms_current(parts)

    def test_wrong_shunt_order_code_or_generic_land_pattern_fails(self):
        for ref,mpn in [('RS10','CSS2H-2512K-2L00F'),('RS11','WSLP25125L000FEA')]:
            with self.subTest(ref=ref):
                values=copy.deepcopy(self.values);values.parts[ref]=(mpn,values.parts[ref][1])
                with self.assertRaises(ValueError):bms_current_budget(values)
        self.values.parts['RS10']=(self.values.mpn('RS10'),'Resistor_SMD:R_2512_6332Metric')
        with self.assertRaises(ValueError):bms_current_budget(self.values)

    def test_stale_label_and_less_precise_limit_order_code_fail(self):
        self.values['R2270']='10k 0.1%'
        with self.assertRaises(ValueError):bms_current_budget(self.values)
        self.values=component_values(FIXTURE)
        self.values.parts['R2270']=('RC0603FR-071KL',self.values.parts['R2270'][1])
        with self.assertRaises(ValueError):bms_current_budget(self.values)

    def test_current_equations_require_the_actual_silicon_variants(self):
        for ref,mpn in [('U11','LTC4368IMS-2#PBF'),('U719','BQ7791501PWR'),
                        ('U2210','INA301A1IDGKR'),('U2211','INA301A1IDGKR')]:
            with self.subTest(ref=ref):
                values=copy.deepcopy(self.values)
                values.parts[ref]=(mpn,values.parts[ref][1])
                with self.assertRaises(ValueError):bms_current_budget(values)

    def test_fifteen_amp_fuse_cannot_replace_ten_amp_part(self):
        self.parts['F1'].properties['MPN']='3-101-062'
        with self.assertRaises(CheckFailure):check_bms_current(self.parts)
        self.values.parts['F1']=('3-101-062',self.values.parts['F1'][1])
        with self.assertRaises(ValueError):pack_breaker_environment_checks(self.values)

    def test_old_gate_delay_and_ready_parts_fail(self):
        for ref,mpn in [('R850','RC0603FR-07100KL'),('R854','RC0603FR-07604KL'),
                        ('R2232','RC0603FR-07100KL')]:
            with self.subTest(ref=ref):
                parts=copy.deepcopy(self.base);parts[ref].properties['MPN']=mpn
                with self.assertRaises(CheckFailure):check_bms_current(parts)

    def test_sense_pin_cannot_be_shortened_to_force_net(self):
        self.reject_pin('RS11','3','/PACK_NEG_RAW')

    def test_added_analog_return_on_sense_terminal_is_rejected(self):
        self.parts['R9999']=SimpleNamespace(pin_nets={'1':'/BMS_RAW_KELVIN','2':'/THERM_3V3'})
        with self.assertRaises(CheckFailure):check_bms_current(self.parts)

    def test_raw_power_and_midpoint_taps_cannot_be_swapped(self):
        self.reject_pin('J2','2','/CELL1_TAP')

    def test_tap_mounts_do_not_join_control_ground(self):
        self.reject_pin('J2201','MP','/CTRL_GND')

    def test_new_raw_to_control_ground_resistor_is_rejected(self):
        self.parts['R9999']=SimpleNamespace(pin_nets={'1':'/CTRL_GND','2':'/PACK_NEG_RAW'})
        with self.assertRaises(CheckFailure):check_bms_control_domains(self.parts)

    def test_native_pad_net_shortcut_fails_with_unchanged_schematic(self):
        board_parts=copy.deepcopy(self.parts);board_parts['RS11'].pin_nets['3']='/PACK_NEG_RAW'
        with self.assertRaises(CheckFailure):check_bms_current_pcb(self.parts,pcb_fixture(board_parts))

    def test_native_part_metadata_cannot_stay_at_old_shunt(self):
        parts=copy.deepcopy(self.parts);parts['RS10'].properties['MPN']='WSL2512R0110FEA18'
        with self.assertRaises(CheckFailure):check_bms_current_pcb(self.parts,pcb_fixture(parts))

    def test_missing_native_sense_pad_and_duplicate_footprint_fail(self):
        board_parts=copy.deepcopy(self.parts);board_parts['RS11'].pin_nets.pop('4')
        with self.assertRaises(CheckFailure):check_bms_current_pcb(self.parts,pcb_fixture(board_parts))
        text=pcb_fixture(self.parts);fp=next(f for f in sync.footprints(text) if f.ref=='RS11')
        with self.assertRaises(CheckFailure):
            check_bms_current_pcb(self.parts,text[:-1]+'\n'+fp.text+'\n)')
        with self.assertRaises(CheckFailure):
            check_bms_current_pcb(self.parts,text[:-1]+'\n'+fp.text.replace('\t','  ')+'\n)')

    def test_guard_load_is_included_and_weak_feed_fails(self):
        result=thermal_supply_budget(1000,self.values)
        self.assertAlmostEqual(result['current_guard_screen_a'],.0003503)
        self.assertAlmostEqual(result['demand_screen_a'],.0022712823878432127)
        self.assertGreater(result['regulator_input_min_v'],4.393)
        self.assertLess(thermal_supply_budget(3300,self.values)['regulator_input_min_v'],4.393)

    def test_small_charge_gate_resistor_prevents_uv_load_removal(self):
        self.assertGreater(bms_uv_load_detect_voltage(8.4,100000,453000,1000),1.35)
        self.assertLess(bms_uv_load_detect_voltage(14,3300000,453000,1000),1.25)
        self.values.parts['R850']=('RC0603FR-07100KL',self.values.parts['R850'][1])
        self.values['R850']='100k 1% CHG gate-source'
        with self.assertRaises(ValueError):pack_breaker_environment_checks(self.values)


if __name__=='__main__':unittest.main()
