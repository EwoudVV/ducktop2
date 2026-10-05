"""Unarmed BMS population, native coverage and retained-package failure gates."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import export_bms_assembly as drawings
import generate_bms_pcbway_package as export

FIXTURES = Path(__file__).parent / 'testdata'


class BmsManufacturing(unittest.TestCase):
    def setUp(self):
        self.netlist = ET.parse(FIXTURES/'bms_monitor.xml').getroot()
        self.geometry = json.loads((FIXTURES/'bms_monitor_fabrication.json').read_text())
        self.profile = json.loads((export.ROOT/'firmware/bq76922/profile.json').read_text())
        self.parity = {'passed': True, 'counts': {'physical_pads_checked': 567}}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        (self.out/'checks').mkdir()
        self.write_inputs()

    def component(self, ref):
        return self.netlist.find(f"./components/comp[@ref='{ref}']")

    def footprint(self, ref):
        return next(f for f in self.geometry['footprints'] if f['ref'] == ref)

    def write_inputs(self, extra=()):
        ET.ElementTree(self.netlist).write(self.out/'checks/netlist.xml')
        rows = []
        for f in self.geometry['footprints']:
            if f['attributes'] & 2 and not f['attributes'] & (8 | 64):
                rows.append(dict(Ref=f['ref'], Package=f['footprint'].split(':',1)[1],
                    PosX=f['position'][0], PosY=-f['position'][1], Rot=f['rotation'],
                    Side='bottom' if f['layer']=='B.Cu' else 'top'))
        rows.extend(extra)
        export.write_csv(self.out/'checks/raw-positions.csv',
                         ['Ref','Package','PosX','PosY','Rot','Side'], rows)

    def contract(self):
        return export.assembly_contract(self.netlist)

    def completed_native_fixture(self):
        # Only the connectivity condition is simulated. The source fixture
        # remains explicitly unrouted and is never a fabrication artifact.
        self.geometry['native_airwires'] = 0
        return export.check_native_gate(self.geometry, self.parity, self.contract())

    def test_exact_current_population_is_unarmed_and_all_smt(self):
        result = export.assembly_files(self.out, self.geometry)
        self.assertEqual((result['schematic_components'],result['onboard_footprints'],
                          result['board_components'],result['smt_components']), (204,201,168,168))
        self.assertEqual(result['unique_board_parts'],74)
        self.assertEqual(result['through_hole_components'],0)
        self.assertEqual(result['soldered_through_holes'],0)
        self.assertEqual(result['footprint_thermal_holes'],15)
        self.assertTrue(result['unarmed_prototype'])
        for file, field in [('BOM.csv','Designator'),('CPL.csv','Ref Des')]:
            with (self.out/file).open() as f:
                refs = {ref for row in csv.DictReader(f) for ref in row[field].split(',')}
            self.assertEqual(len(refs),168)
            self.assertFalse(refs & (export.RELEASE_LINKS | export.OFFBOARD_PROBES))
            self.assertFalse(any(ref.startswith('TP') for ref in refs))
        with (self.out/'not-fitted.csv').open() as f:
            excluded={r['Designator']:r['Reason'] for r in csv.DictReader(f)}
        self.assertEqual(len(excluded),36)
        self.assertTrue(all('DNP gate-drive release' in excluded[r] for r in export.RELEASE_LINKS))
        self.assertTrue(all('offboard' in excluded[r] for r in export.OFFBOARD_PROBES))
        with (self.out/'through-hole-positions.csv').open() as f:
            self.assertEqual(list(csv.DictReader(f)),[])

    def test_release_link_missing_schematic_dnp_or_bom_exclusion_fails(self):
        for ref in export.RELEASE_LINKS:
            for flag in ('dnp','exclude_from_bom'):
                with self.subTest(ref=ref,flag=flag):
                    old=self.netlist;self.netlist=copy.deepcopy(old)
                    c=self.component(ref);c.remove(c.find(f"property[@name='{flag}']"))
                    with self.assertRaisesRegex(RuntimeError,'must remain DNP'):
                        self.contract()
                    self.netlist=old

    def test_release_link_missing_pcb_dnp_fails(self):
        self.footprint('R870')['attributes'] &= ~64
        with self.assertRaisesRegex(RuntimeError,'PCB assembly flags differ'):
            export.assembly_files(self.out,self.geometry)

    def test_bare_test_point_missing_bom_exclusion_fails(self):
        c=self.component('TPB1');c.remove(c.find("property[@name='exclude_from_bom']"))
        with self.assertRaises(RuntimeError):self.contract()

    def test_unknown_offboard_or_offboard_probe_footprint_fails(self):
        ET.SubElement(self.component('TH2201'),'footprint').text='Resistor_SMD:R_0603_1608Metric'
        with self.assertRaisesRegex(RuntimeError,'remain offboard'):self.contract()

    def test_wrong_controller_does_not_fall_back_to_legacy(self):
        self.component('U719').find("fields/field[@name='MPN']").text='BQ76952'
        with self.assertRaisesRegex(RuntimeError,'reviewed BQ76922'):self.contract()

    def test_wrong_shunt_or_height_fails(self):
        self.component('RS11').find("fields/field[@name='Height']").text='2.63 mm'
        with self.assertRaisesRegex(RuntimeError,'2.93 mm'):self.contract()

    def test_test_pad_in_raw_positions_is_removed(self):
        f=self.footprint('TPB1')
        self.write_inputs([dict(Ref='TPB1',Package=f['footprint'].split(':',1)[1],
            PosX=f['position'][0],PosY=-f['position'][1],Rot=f['rotation'],Side='top')])
        self.assertEqual(export.assembly_files(self.out,self.geometry)['smt_components'],168)

    def test_dnp_unknown_missing_duplicate_or_nonfinite_position_fails(self):
        original=(self.out/'checks/raw-positions.csv').read_text()
        for kind in ('dnp','unknown','missing','duplicate','nonfinite'):
            with self.subTest(kind=kind):
                with (self.out/'checks/raw-positions.csv').open() as f: rows=list(csv.DictReader(f))
                if kind in ('dnp','unknown'):rows.append(dict(rows[0],Ref='R870' if kind=='dnp' else 'TH2201'))
                if kind=='missing':rows.pop()
                if kind=='duplicate':rows.append(rows[0])
                if kind=='nonfinite':rows[0]['PosX']='nan'
                export.write_csv(self.out/'checks/raw-positions.csv',list(rows[0]),rows)
                with self.assertRaises(RuntimeError):export.assembly_files(self.out,self.geometry)
                (self.out/'checks/raw-positions.csv').write_text(original)

    def test_actual_unrouted_native_fixture_fails_full_airwire_gate(self):
        self.assertGreater(self.geometry['native_airwires'],0)
        with self.assertRaisesRegex(RuntimeError,'open airwires'):
            export.check_native_gate(self.geometry,self.parity,self.contract())

    def test_all_608_native_pad_objects_are_checked(self):
        result=self.completed_native_fixture()
        self.assertEqual(result,dict(all_physical_pads_checked=608,electrical_pads_checked=567,
                                    non_electrical_pad_objects_checked=41,native_airwires=0))

    def test_missing_pad_or_electrical_parity_coverage_fails(self):
        self.geometry['native_airwires']=0
        pads=self.footprint('Q11')['pads']
        pads.remove(next(p for p in pads if not p['number']))
        with self.assertRaisesRegex(RuntimeError,'pad population changed'):
            export.check_native_gate(self.geometry,self.parity,self.contract())

    def test_paste_object_with_net_or_copper_fails(self):
        self.geometry['native_airwires']=0
        pad=next(p for p in self.footprint('Q11')['pads']if not p['number'])
        pad['net']='/PACK_POS_RAW'
        with self.assertRaisesRegex(RuntimeError,'non-electrical pad'):
            export.check_native_gate(self.geometry,self.parity,self.contract())

    def test_native_pad_net_short_fails_even_with_passing_summary(self):
        self.geometry['native_airwires']=0
        self.footprint('R870')['pads'][0]['net']='/CTRL_GND'
        with self.assertRaisesRegex(RuntimeError,'native pad net differs'):
            export.check_native_gate(self.geometry,self.parity,self.contract())

    def test_missing_library_proof_outline_or_layers_fails(self):
        original=copy.deepcopy(self.geometry)
        for key in ('library','layers','outline','parity'):
            with self.subTest(key=key):
                self.geometry=copy.deepcopy(original);self.geometry['native_airwires']=0
                parity=copy.deepcopy(self.parity)
                if key=='library':self.geometry['library_pad_differences']=['RS11']
                if key=='layers':self.geometry['copper_layers']=['F.Cu','B.Cu']
                if key=='outline':
                    for point in self.geometry['outline'][0]['outer']:point[0]*=1.1
                if key=='parity':parity['counts']['physical_pads_checked']=566
                with self.assertRaises(RuntimeError):export.check_native_gate(self.geometry,parity,self.contract())

    def test_all_qualification_and_release_flags_stay_false(self):
        export.check_prototype_profile(self.profile)
        for key in export.QUALIFICATION_KEYS:
            bad=copy.deepcopy(self.profile);bad['qualification'][key]=True
            with self.subTest(key=key),self.assertRaisesRegex(RuntimeError,'qualification'):
                export.check_prototype_profile(bad)
        for key in ('released_for_ram_test','released_for_otp','released_for_assembly','calibration_qualified'):
            bad=copy.deepcopy(self.profile);bad[key]=True
            with self.subTest(key=key),self.assertRaisesRegex(RuntimeError,'release'):
                export.check_prototype_profile(bad)

    def test_exact_benign_drc_filter_only(self):
        path=self.out/'drc.json'
        finding=dict(type='footprint_filters_mismatch',severity='warning',
            description="ducktop2:WAGO_2060_452_SMD doesn't match symbol's footprint filters (Connector*:*_1x??_*)",
            items=[dict(description='Footprint J2')])
        report=dict(violations=[],schematic_parity=[finding],unconnected_items=[])
        export.write_json(path,report);export.check_drc(path)
        for field,value in [('description','different mismatch'),('severity','error'),('type','lib_footprint_mismatch')]:
            bad=copy.deepcopy(report);bad['schematic_parity'][0][field]=value;export.write_json(path,bad)
            with self.assertRaises(RuntimeError):export.check_drc(path)
        for kind in ('lib_footprint_mismatch','track_not_centered_on_via','clearance'):
            bad=copy.deepcopy(report);bad['violations']=[dict(type=kind,severity='warning')];export.write_json(path,bad)
            with self.assertRaisesRegex(RuntimeError,'DRC finding'):export.check_drc(path)
        bad=copy.deepcopy(report);bad['unconnected_items']=[{}];export.write_json(path,bad)
        with self.assertRaisesRegex(RuntimeError,'unconnected'):export.check_drc(path)

    def test_exact_raw_ground_erc_only(self):
        finding=dict(type='ground_pin_not_ground',severity='warning',description='Pin GND2 not connected to ground net',
                     items=[dict(description='Symbol U2206 Pin 5 [GND2, Power input, Line]')])
        erc={'sheets':[{'violations':[finding]}]}
        self.assertEqual(export.check_erc(erc,self.contract())['errors'],0)
        for field,value in [('description','other ground'),('severity','error'),('type','lib_symbol_mismatch')]:
            bad=copy.deepcopy(erc);bad['sheets'][0]['violations'][0][field]=value
            with self.assertRaises(RuntimeError):export.check_erc(bad,self.contract())
        c=self.contract();by_ref={p['ref']:p for p in c['components']};by_ref['U2206']['pin_nets']['5']='/CTRL_GND'
        with self.assertRaisesRegex(RuntimeError,'PACK_NEG_RAW'):export.check_erc(erc,c)

    def test_legacy_current_fixture_retains_its_population(self):
        contract=export.assembly_contract(ET.parse(FIXTURES/'bms_current.xml').getroot())
        self.assertFalse(contract['unarmed'])
        self.assertEqual((contract['onboard_footprints'],contract['fitted_components']),(162,138))

    def test_drawing_testpoint_detection_is_not_limited_to_tpb(self):
        self.assertTrue(drawings.is_test_point('TP34','ducktop2:Pad'))
        self.assertTrue(drawings.is_test_point('J100','TestPoint:TestPoint_Pad_D1.0mm'))
        self.assertFalse(drawings.is_test_point('R870','Resistor_SMD:R_0603_1608Metric'))

    def checked_package(self):
        assembly=export.assembly_files(self.out,self.geometry)
        native=self.completed_native_fixture()
        for name in ('saved','refilled'):
            export.write_json(self.out/'checks'/(name+'-drc.json'),dict(violations=[],schematic_parity=[],unconnected_items=[]))
        erc={'sheets':[{'violations':[]}]};export.write_json(self.out/'checks/erc.json',erc)
        (self.out/'programming').mkdir()
        export.write_json(self.out/'programming/profile-template.json',self.profile)
        manifest=dict(schema=1,source_sha256={'board':'hash'},assembly=assembly,assembly_state='UNARMED_PROTOTYPE',
            operating_ready=False,order_submitted=False,programming=export.check_prototype_profile(self.profile),
            checks=dict(**native,library_pad_differences=[],parity_passed=True,erc_errors=0,erc_warnings={},
                erc_accepted_findings=[],saved=export.check_drc(self.out/'checks/saved-drc.json'),
                refilled=export.check_drc(self.out/'checks/refilled-drc.json')))
        export.write_json(self.out/'manifest.json',manifest)
        self.checksums()
        return manifest

    def checksums(self):
        (self.out/'SHA256SUMS.txt').write_text(''.join(f'{export.digest(p)}  {p.relative_to(self.out)}\n'
            for p in sorted(self.out.rglob('*'))if p.is_file()and p.name!='SHA256SUMS.txt'))

    def test_retained_package_rechecks_manifest_not_just_checksums(self):
        manifest=self.checked_package()
        with patch.object(export,'source_hashes',return_value={'board':'hash'}):
            export.verify_package(self.out)
            manifest['checks']['all_physical_pads_checked']=567
            export.write_json(self.out/'manifest.json',manifest);self.checksums()
            with self.assertRaisesRegex(RuntimeError,'incomplete native'):export.verify_package(self.out)

    def test_recomputed_checksum_cannot_hide_population_mistake(self):
        self.checked_package()
        with (self.out/'CPL.csv').open()as f: rows=list(csv.DictReader(f))
        rows.append(dict(rows[0],**{'Ref Des':'R870'}));export.write_csv(self.out/'CPL.csv',list(rows[0]),rows);self.checksums()
        with patch.object(export,'source_hashes',return_value={'board':'hash'}),self.assertRaisesRegex(RuntimeError,'population differs'):
            export.verify_package(self.out)

    def test_manifest_cannot_disable_unarmed_checks(self):
        manifest=self.checked_package();manifest['assembly']['unarmed_prototype']=False
        export.write_json(self.out/'manifest.json',manifest);self.checksums()
        with patch.object(export,'source_hashes',return_value={'board':'hash'}),self.assertRaisesRegex(RuntimeError,'controller state'):
            export.verify_package(self.out)

    def test_recomputed_checksum_cannot_hide_wrong_shunt_bom_part(self):
        self.checked_package()
        with (self.out/'BOM.csv').open()as f: rows=list(csv.DictReader(f))
        next(r for r in rows if r['Designator']=='RS11')['MPN']='CSS4J-4026K-5L00F'
        export.write_csv(self.out/'BOM.csv',list(rows[0]),rows);self.checksums()
        with patch.object(export,'source_hashes',return_value={'board':'hash'}),self.assertRaisesRegex(RuntimeError,'exact part differs'):
            export.verify_package(self.out)

    def test_stale_missing_changed_and_unlisted_package_files_fail(self):
        self.checked_package()
        with patch.object(export,'source_hashes',return_value={'board':'changed'}),self.assertRaisesRegex(RuntimeError,'source'):
            export.verify_package(self.out)
        with patch.object(export,'source_hashes',return_value={'board':'hash'}):
            (self.out/'BOM.csv').write_text((self.out/'BOM.csv').read_text()+'\n')
            with self.assertRaisesRegex(RuntimeError,'file changed'):export.verify_package(self.out)
            self.checksums();(self.out/'unexpected.txt').write_text('extra')
            with self.assertRaisesRegex(RuntimeError,'file list differs'):export.verify_package(self.out)

    def test_generated_notes_preserve_quote_cases_and_unarmed_state(self):
        manifest=self.checked_package()
        export.write_json(self.out/'checks/export-check.json',{'electrical_test':{'records':608,'nets':100}})
        export.write_order_notes(self.out)
        text=(self.out/'README.md').read_text()
        self.assertIn('80.000 x 36.148',text)
        self.assertIn('2.93 mm',text)
        self.assertIn('one-time-programmable',text)
        self.assertIn('not a released',text)
        self.assertIn('five bare PCBs with one assembled',text)
        self.assertIn('five bare PCBs with two',text)
        self.assertNotIn('no programming is required',text)
        self.assertNotIn('BQ77915',text)
        self.assertNotIn('LTC4368',text)
        self.assertNotIn('/Users/',text)
        self.assertFalse(manifest['operating_ready'])


class ExposedPadViaReview(unittest.TestCase):
    def setUp(self):
        from shapely.geometry import box
        from shapely.ops import unary_union
        self.geometry = {'footprints': [{'ref': 'U719', 'layer': 'B.Cu',
            'footprint': 'ducktop2:TI_RSN0032B_WQFN32_4x4mm',
            'pads': [{'number': '33', 'net': '/PACK_NEG_RAW', 'position': [0, 0],
                'polygons': {'B.Cu': [{'outer': [[-1.4,-1.4],[1.4,-1.4],[1.4,1.4],[-1.4,1.4]], 'holes': []}]}}]}]}
        self.via = {'id': 'reviewed', 'net': '/PACK_NEG_RAW', 'position': [0, -.15], 'drill': .2, 'diameter': .5}
        self.front = box(3, 3, 4, 4)
        self.paste = unary_union([box(x0,y0,x1,y1) for x0,x1 in [(-1.33,-.1),(.1,1.33)]
                                 for y0,y1 in [(-1.33,-.1),(.1,1.33)]])

    def test_review_records_exposure_without_claiming_assembly_release(self):
        result = export.exposed_pad_via_review(self.geometry, self.via, self.front, self.paste)
        self.assertTrue(result['factory_review_required'])
        self.assertEqual(result['nominal_paste_hole_overlap_mm2'], 0)
        self.assertEqual(result['paste_hole_edge_margin_mm'], 0)

    def test_other_pad_or_net_gets_no_exception(self):
        via = dict(self.via, position=[1, 1])
        self.assertIsNone(export.exposed_pad_via_review(self.geometry, via, self.front, self.paste))
        via = dict(self.via, net='/CTRL_GND')
        self.assertIsNone(export.exposed_pad_via_review(self.geometry, via, self.front, self.paste))

    def test_front_mask_registration_can_reject_nominally_covered_hole(self):
        from shapely.geometry import box
        with self.assertRaisesRegex(RuntimeError, 'opposite-face'):
            export.exposed_pad_via_review(self.geometry, self.via, box(.12,-1,1,1), self.paste)

    def test_paste_over_the_hole_is_rejected(self):
        from shapely.geometry import box
        with self.assertRaisesRegex(RuntimeError, 'nominal paste'):
            export.exposed_pad_via_review(self.geometry, self.via, self.front, box(-1,-1,1,1))

    def test_larger_hole_gets_no_exception(self):
        self.assertIsNone(export.exposed_pad_via_review(self.geometry, dict(self.via, drill=.3), self.front, self.paste))


class ElectricalTestThermalPads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'thermal.ipc'
        self.lines = [
            '317/PDSG_RTN        U2218 -17   D0118PA00X+045079Y-033858X0236Y0000R000S3',
            '327/PDSG_RTN        U2218 -17         A01X+045079Y-033858X1339Y1969R000S3',
            '327/PDSG_RTN        U2218 -17         A04X+045079Y-033858X1339Y1969R000S3',
        ]
        common = dict(number='17', net='/PDSG_RTN', position=[114.5, 86], polygons={'F.Cu': []})
        self.geometry = {'copper_layers': ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], 'vias': [],
            'footprints': [{'ref': 'U2218', 'pads': [
                dict(common, attribute=0, layers=['F.Cu','B.Cu'], drill=[.3,.3]),
                dict(common, attribute=1, layers=['F.Cu'], drill=[0,0]),
                dict(common, attribute=1, layers=['B.Cu'], drill=[0,0]),
            ]}]}

    def check(self, lines):
        self.path.write_text('\n'.join(lines)+'\n')
        return export.check_ipc(self.path, self.geometry)

    def test_coincident_hole_and_surface_pads_are_each_checked(self):
        self.assertEqual(self.check(self.lines)['records'], 3)

    def test_wrong_access_or_drill_is_rejected(self):
        for old, new in [('A04','A01'), ('D0118','D0079')]:
            with self.subTest(old=old), self.assertRaisesRegex(RuntimeError, 'reference/coordinate'):
                self.check([line.replace(old,new) for line in self.lines])

    def test_missing_or_duplicate_record_is_rejected(self):
        for lines in [self.lines[:-1], self.lines+[self.lines[-1]]]:
            with self.subTest(records=len(lines)), self.assertRaises(RuntimeError):
                self.check(lines)


if __name__=='__main__':unittest.main()
