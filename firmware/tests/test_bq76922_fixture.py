"""Synthetic readback tests; no OTP programming or cell qualification."""
import copy
import importlib.util
import json
import struct
from pathlib import Path
import unittest

folder=Path(__file__).resolve().parents[1]/'bq76922'
spec=importlib.util.spec_from_file_location('fixture', folder/'fixture_profile.py')
fixture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.profile=json.loads((folder/'profile.json').read_text())
        self.complete=copy.deepcopy(self.profile)
        for row in self.complete['rows']:
            if row['bytes'] is None:
                row['bytes']=[0x01]*row['length']
        self.complete['admission'].update({
            'discharge_cell_min_mv':3000, 'normal_charge_cell_min_mv':3200,
            'cell_max_mv':4300, 'pack_min_mv':9000, 'current_gain_min_permille':1000,
            'current_offset_ma':0, 'dynamic_reserve_ma':100})
        self.capture={'part':'BQ76922RSNR','security_state':'UNSEALED',
                      'manufacturing_status':0x50,'cold_cycle_readback':True,'rows':[]}
        for row in self.complete['rows']:
            self.capture['rows'].append(dict(address=row['address'],bytes=row['bytes'],
                length=row['length']+4,checksum=fixture.transfer_checksum(fixture.address(row),row['bytes']),
                crc_verified=True))
    def test_actual_profile_stays_blocked(self):
        self.assertEqual(fixture.check_profile(self.profile), [])
        self.assertTrue(self.profile['complete_prototype_register_choices'])
        with self.assertRaisesRegex(fixture.ProfileError,'not been released'):
            fixture.ram_plan(self.profile)
        self.assertFalse(self.profile['released_for_ram_test'])
        self.assertFalse(self.profile['released_for_otp'])
        self.assertFalse(self.profile['released_for_assembly'])
        self.assertTrue(all(x is False for x in self.profile['qualification'].values()))
    def test_charge_limits_and_measurement_gates_are_bound(self):
        for key,value in [('charge_voltage_mv',12528),('charge_cell_max_mv',4200),('charge_spread_max_mv',100)]:
            bad=copy.deepcopy(self.profile);bad['admission'][key]=value
            with self.assertRaisesRegex(fixture.ProfileError,'charge admission'):
                fixture.check_profile(bad)
        for key in ('cell_voltage_qualified','charge_voltage_qualified','termination_qualified'):
            bad=copy.deepcopy(self.profile);bad[key]=True
            with self.assertRaisesRegex(fixture.ProfileError,'qualification remains false'):
                fixture.check_profile(bad)
        bad=copy.deepcopy(self.profile)
        bad['host_charge']['session_max_ms']=bad['host_charge'].pop('cv_dwell_max_ms')
        with self.assertRaisesRegex(fixture.ProfileError,'host charge criteria'):
            fixture.check_profile(bad)
        bad=copy.deepcopy(self.profile);bad['host_charge']['taper_hold_ms']=1
        with self.assertRaisesRegex(fixture.ProfileError,'host charge criteria'):
            fixture.check_profile(bad)

    def test_synthetic_readback_matches(self):
        self.assertTrue(fixture.verify_readback(self.complete,self.capture))
    def test_corrupted_data(self):
        self.capture['rows'][0]['bytes']=[0x0c]
        with self.assertRaisesRegex(fixture.ProfileError,'mismatch'):
            fixture.verify_readback(self.complete,self.capture)
    def test_corrupted_checksum(self):
        self.capture['rows'][0]['checksum']^=1
        with self.assertRaisesRegex(fixture.ProfileError,'checksum'):
            fixture.verify_readback(self.complete,self.capture)
    def test_crc_required(self):
        self.capture['rows'][0]['crc_verified']=False
        with self.assertRaisesRegex(fixture.ProfileError,'CRC'):
            fixture.verify_readback(self.complete,self.capture)
    def test_sealed_readback(self):
        self.capture['security_state']='SEALED'
        with self.assertRaisesRegex(fixture.ProfileError,'UNSEALED'):
            fixture.verify_readback(self.complete,self.capture)
    def test_unprogrammed_fet_mode(self):
        self.capture['manufacturing_status']=0x40
        with self.assertRaisesRegex(fixture.ProfileError,'autonomous'):
            fixture.verify_readback(self.complete,self.capture)
    def test_cold_cycle_required(self):
        self.capture['cold_cycle_readback']=False
        with self.assertRaisesRegex(fixture.ProfileError,'cold-cycle'):
            fixture.verify_readback(self.complete,self.capture)
    def test_recovery_disabled(self):
        self.complete['recovery_charging_enabled']=True
        with self.assertRaisesRegex(fixture.ProfileError,'recovery'):
            fixture.check_profile(self.complete)
    def test_ram_plan_stays_disabled(self):
        with self.assertRaisesRegex(fixture.ProfileError,'not been released'):
            fixture.ram_plan(self.complete)
    def test_protection_rows_required(self):
        self.complete['rows'] = [r for r in self.complete['rows'] if r['name'] != 'OCD1 Threshold']
        with self.assertRaisesRegex(fixture.ProfileError,'missing protection'):
            fixture.check_profile(self.complete)
    def test_actuation_address_rejected(self):
        self.complete['rows'].append(dict(address='0x0022',name='bad command',length=1,bytes=[0]))
        with self.assertRaisesRegex(fixture.ProfileError,'data-memory'):
            fixture.check_profile(self.complete)
    def test_ram_plan_has_no_otp_write(self):
        self.complete['released_for_ram_test']=True
        self.complete['unit_factory_trim_capture_applied']=True
        plan=fixture.ram_plan(self.complete)
        self.assertFalse(plan['otp_write'])

    def test_predischarge_cannot_promote_on_timeout(self):
        row=next(r for r in self.profile['rows'] if fixture.address(r)==0x930E)
        self.assertEqual(row['bytes'],[0])
        wrong=copy.deepcopy(self.profile)
        next(r for r in wrong['rows'] if fixture.address(r)==0x930E)['bytes']=[25]
        with self.assertRaisesRegex(fixture.ProfileError,'interface mismatch'):
            fixture.check_profile(wrong)
    def test_awake_pin_has_no_alarm_authorization_mask(self):
        rows={fixture.address(r):r['bytes']for r in self.profile['rows']}
        self.assertEqual(rows[0x92FC],[0x8A])
        self.assertEqual(rows[0x926D],[0,0])
        self.assertEqual(rows[0x9263],[0x60])
        self.assertEqual(rows[0x926B],[0x60])
        self.assertEqual(rows[0x9271],[0x60])
        for addr,wrong in [(0x92FC,[0x2A]),(0x926D,[0x18,0xF8]),(0x9263,[0xC0])]:
            changed=copy.deepcopy(self.profile)
            next(r for r in changed['rows']if fixture.address(r)==addr)['bytes']=wrong
            with self.assertRaisesRegex(fixture.ProfileError,'interface mismatch'):
                fixture.check_profile(changed)

    def test_otint_literal_masks_and_thresholds(self):
        values={fixture.address(r):r['bytes'] for r in self.profile['rows']}
        for addr in (0x9262,0x9266,0x926A,0x9270):
            self.assertEqual(values[addr],[0x40])
        self.assertEqual(values[0x92A3],[75])
        self.assertEqual(values[0x92A4],[0])
        self.assertEqual(values[0x92A5],[65])
        self.assertEqual(values[0x9303],[5])
        self.assertEqual(values[0x92FA],[2])
        self.assertEqual(values[0x92FB],[2])
        for addr in (0x9262,0x9266,0x926A,0x9270):
            wrong=copy.deepcopy(self.profile)
            next(r for r in wrong['rows'] if fixture.address(r)==addr)['bytes']=[0]
            with self.assertRaisesRegex(fixture.ProfileError,'interface mismatch'):
                fixture.check_profile(wrong)

    def test_factory_capture_required(self):
        self.complete['released_for_ram_test']=True
        with self.assertRaisesRegex(fixture.ProfileError,'factory trim'):
            fixture.ram_plan(self.complete)
    def test_per_unit_factory_trims_preserved(self):
        entries=[]
        for row in self.profile['rows']:
            addr=fixture.address(row)
            if addr in (0x9180,0x9182,0x9188,0x91B0,0x91A8):
                data=[0x79,0x30] if addr!=0x91A8 else list(struct.pack('<f',7.4768))
                entries.append(dict(address=row['address'],bytes=data,length=len(data)+4,
                    checksum=fixture.transfer_checksum(addr,data),crc_verified=True))
        factory={'part':'BQ76922RSNR','before_any_ram_or_otp_write':True,'rows':entries}
        result=fixture.prepare_unit_profile(self.profile,factory)
        captured={fixture.address(r):r for r in result['rows']}
        self.assertEqual(captured[0x9180]['bytes'],[0x79,0x30])
        self.assertAlmostEqual(struct.unpack('<f',bytes(captured[0x91A8]['bytes']))[0],3.7384,places=5)
        self.assertFalse(result['released_for_ram_test'])
        self.assertTrue(all(x is False for x in result['qualification'].values()))
        emitted=fixture.c_profile(result)
        self.assertIn('.qualified = false',emitted)
        self.assertIn('0x9237u, 1, {0x00u}',emitted)

if __name__=='__main__':
    unittest.main()
