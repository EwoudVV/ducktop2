"""Exact signal counts, mirrored pin order and bounded shell-return topology."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fpc_contract as fpc
import signal_interconnect_contract as signal
from verify_design_contracts import CheckFailure, check_fpc_connectors


def candidate(ref):
    spec=signal.INTERFACES[ref]
    kind='fpc1' if spec['count']==41 else 'fpc2'
    base=fpc.FPC1_PINMAP if kind=='fpc1' else fpc.FPC2_PINMAP
    mapping=fpc.reversed_map(base) if ref in ('FPC102','FPC103') else base
    shell='/connector/'+ref+'_SHELL'
    pins={str(pin): ('unconnected-('+ref+'-Pad'+str(pin)+')' if name=='NC'
                    else 'GND' if name=='GND' else '/'+name) for pin,name in mapping.items()}
    pins['SH']=shell
    parts={ref:SimpleNamespace(footprint=signal.footprint_for(ref),value=signal.mpn_for(ref),
                              properties={'MPN':signal.mpn_for(ref)},pin_nets=pins,
                              sheetname='/connector/',path='/sheet/symbol')}
    for resistor in spec['resistors']:
        parts[resistor]=SimpleNamespace(footprint='Resistor_SMD:R_0603_1608Metric',value='0.33',
                                       properties={'MPN':signal.SHELL_RESISTOR_MPN},pin_nets={'1':shell,'2':'GND'})
    for strap in spec['straps']:
        parts[strap]=SimpleNamespace(footprint='Connector_Wire:SolderWirePad_1x01_SMD_5x10mm',
                                    value='main ground strap',properties={},pin_nets={'1':'GND'})
    return parts,kind


def check(parts,ref,kind):
    check_fpc_connectors(parts,ref,'ducktop2',signal.footprint_for(ref).split(':',1)[1],kind)


class SignalConnectorContractTests(unittest.TestCase):
    def test_all_four_actual_pin_maps_and_shell_returns(self):
        for ref in signal.INTERFACES:
            with self.subTest(ref=ref):
                parts,kind=candidate(ref)
                check(parts,ref,kind)

    def test_wrong_footprint_fails(self):
        parts,kind=candidate('FPC101')
        parts['FPC101'].footprint=signal.footprint_for('FPC104')
        with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)

    def test_extra_mounting_pin_is_not_accepted(self):
        parts,kind=candidate('FPC101');parts['FPC101'].pin_nets['MP']='GND'
        with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)

    def test_wrong_signal_polarity_fails(self):
        parts,kind=candidate('FPC101');pins=parts['FPC101'].pin_nets
        pins['2'],pins['3']=pins['3'],pins['2']
        with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)

    def test_shell_must_not_be_directly_grounded(self):
        parts,kind=candidate('FPC101');parts['FPC101'].pin_nets['SH']='GND'
        with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)

    def test_extra_shell_bypass_fails(self):
        parts,kind=candidate('FPC101')
        parts['R_BYPASS']=SimpleNamespace(pin_nets={'1':'/connector/FPC101_SHELL','2':'GND'})
        with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)

    def test_shell_return_value_and_fitted_state_are_required(self):
        for change in ('value','dnp'):
            parts,kind=candidate('FPC101');resistor=parts['R2440']
            if change=='value':resistor.value='0.033'
            else:resistor.properties['dnp']=''
            with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)

    def test_a_named_nc_with_another_connection_fails(self):
        with patch.dict(fpc.FPC1_PINMAP,{41:'NC'}):
            parts,kind=candidate('FPC101')
            check(parts,'FPC101',kind)
            parts['R_LIVE']=SimpleNamespace(pin_nets={'1':parts['FPC101'].pin_nets['41']})
            with self.assertRaises(CheckFailure):check(parts,'FPC101',kind)


if __name__=='__main__':unittest.main()
