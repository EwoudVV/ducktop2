"""Fault injections for cell mapping, power orientation and independent inhibits."""
from copy import deepcopy
from pathlib import Path
import unittest
from verify_bms_monitor import ContractError, read_netlist, verify

FIXTURE = Path(__file__).parent/'testdata/bms_monitor.xml'


class MonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = read_netlist(FIXTURE)

    def reject(self, ref, number, net):
        parts = deepcopy(self.base)
        parts[ref]['pins'][str(number)] = net
        with self.assertRaises(ContractError):
            verify(parts)

    def test_native_netlist_passes(self):
        self.assertEqual(verify(self.base)['status'], 'PASS')

    def test_unused_cell_input_cannot_be_tied_to_top_cell(self):
        self.reject('U719', 3, '/BQ_VC5')

    def test_three_cell_top_sense_must_be_input_five(self):
        self.reject('U719', 2, '/BQ_VC2')

    def test_charge_fet_must_block_charging_direction(self):
        self.reject('Q11', 1, '/PACK_POS_FUSED')

    def test_common_drain_cannot_be_changed_to_common_source(self):
        self.reject('Q12', 5, '/BAT_PROT_VIN')

    def test_srn_must_reach_the_separate_output_kelvin_terminal(self):
        self.reject('R846', 1, '/FG_VSS')

    def test_raw_and_control_returns_cannot_be_bonded_by_support_resistor(self):
        parts = deepcopy(self.base)
        parts['R2274']['pins'] = {'1': '/PACK_NEG_RAW', '2': '/CTRL_GND'}
        with self.assertRaises(ContractError):
            verify(parts)

    def test_efuse_thermal_pad_cannot_join_raw_ground(self):
        self.reject('U2218', 17, '/PACK_NEG_RAW')

    def test_release_links_cannot_be_populated_by_default(self):
        for ref in ('R870', 'R871', 'R872'):
            with self.subTest(ref=ref):
                parts = deepcopy(self.base)
                parts[ref]['attributes'].discard('dnp')
                with self.assertRaises(ContractError):
                    verify(parts)

    def test_pdsg_translator_tracks_filtered_controller_bat(self):
        self.reject('Q2211', 2, '/BAT_PROT_VIN')

    def test_startup_branch_has_independent_discharge_permission(self):
        self.reject('R894', 1, '/BQ_REG1')

    def test_guard_polarity_cannot_be_reversed(self):
        self.reject('R2280', 1, '/BMS_RAW_KELVIN')

    def test_charge_guard_cannot_disable_only_discharge(self):
        self.reject('U2211', 3, '/THERM_DSG_HEALTH')

    def test_current_ready_must_gate_temperature_permission(self):
        self.reject('U2205', 1, '/THERM_READY')

    def test_guard_ground_cannot_follow_load_return(self):
        self.reject('U2210', 5, '/FG_VSS')

    def test_thermal_off_bias_survives_either_supply_loss(self):
        self.reject('D2221', 2, '/THERM_3V3')

    def test_i2c_isolator_side_offset_cannot_face_bq(self):
        self.reject('U2206', 2, '/BMS_RAW_SDA')

    def test_bus_cannot_bypass_local_capacitance_buffer(self):
        self.reject('U2207', 3, '/PACK_I2C_SDA')

    def test_alarm_requires_default_low_isolator_variant(self):
        parts = deepcopy(self.base)
        parts['U2209']['fields']['MPN'] = 'ISO7021DR'
        with self.assertRaises(ContractError):
            verify(parts)

    def test_ctrl_supply_enable_is_active_low(self):
        self.reject('U2216', 4, '/MCU_3V3')

    def test_thermal_shutdown_switch_cannot_bypass_its_input_limiter(self):
        self.reject('U2217', 1, '/PACK_POS_RAW')

    def test_awake_output_cannot_be_driven_from_reg1(self):
        parts = deepcopy(self.base)
        parts['R2250'] = deepcopy(parts['R2290'])
        parts['R2250']['pins'] = {'1': '/BQ_REG1', '2': '/BQ_ALERT_AWAKE'}
        with self.assertRaises(ContractError):
            verify(parts)

    def test_ready_wire_cannot_claim_that_all_fault_registers_are_clear(self):
        self.reject('U2208', 2, '/BQ_ALERT_AWAKE')


if __name__ == '__main__':
    unittest.main()
