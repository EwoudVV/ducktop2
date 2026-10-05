"""Main-interface direction, return, retired parts and exact NC regressions."""
import contextlib
import copy
import io
from types import SimpleNamespace
import unittest

import fpc_contract as fpc
from test_power_revision import monitor_center_fixture
from verify_design_contracts import (
    CheckFailure, check_main_pack_monitor_interface, check_bms_interconnect,
)

def components():
    values=monitor_center_fixture()
    return {ref:SimpleNamespace(value=values[ref],footprint=part[1],properties={'MPN':part[0]},
                               pin_nets=copy.deepcopy(values.pins[ref]),path='')
            for ref,part in values.parts.items()}

def interconnect_fixture(current, bms_side=False):
    side='bms' if bms_side else 'center'
    power=fpc.BMS_POWER_REFS[side];control=fpc.BMS_CONTROL_REFS[side]
    power_map=fpc.BMS_POWER_PINMAP if bms_side else fpc.BMS_POWER_CENTER_PINMAP
    power_pins={str(pin):(name if bms_side and not current and name=='FG_VSS' else '/'+name)
                for pin,name in power_map.items()}
    mapping=(fpc.BMS_CONTROL_PINMAP if bms_side else fpc.BMS_CONTROL_CENTER_PINMAP) if current else {
        1:'PACK_FAULT_N',2:'PACK_RETRY_PULSE',3:'MCU_3V3',4:'PACK_CHG_TEMP_OK',5:'CTRL_GND'if bms_side else'GND'}
    control_pins={str(pin):'GND'if name=='GND'else'/'+name for pin,name in mapping.items()}
    control_pins['MP']='/CTRL_GND'if bms_side else'GND'
    items={power:SimpleNamespace(value='power',footprint=fpc.BMS_POWER_FOOTPRINT,properties={'MPN':fpc.BMS_POWER_MPN},pin_nets=power_pins),
           control:SimpleNamespace(value='control',footprint=fpc.BMS_CONTROL_FOOTPRINT,properties={'MPN':fpc.BMS_CONTROL_MPN},pin_nets=control_pins)}
    if bms_side:
        items['U719']=SimpleNamespace(properties={'MPN':'BQ76922RSNR'if current else'BQ7791500PWR'},pin_nets={})
    elif not current:
        items['U2210']=SimpleNamespace(properties={'MPN':'SN74LVC1G08DBVR'},pin_nets={})
    return items

class MainMonitorInterfaceTests(unittest.TestCase):
    def test_current_main_interface_passes(self):
        check_main_pack_monitor_interface(components())

    def test_shared_or_misnamed_nc_is_rejected(self):
        for ref,pin in [('U44','13'),('U2635','3')]:
            for wrong in ['GND','unconnected-(OTHER-Pad'+pin+')']:
                parts=components();parts[ref].pin_nets[pin]=wrong
                with self.assertRaises(CheckFailure):check_main_pack_monitor_interface(parts)
            parts=components();parts['EXTRA']=SimpleNamespace(properties={},pin_nets={'1':parts[ref].pin_nets[pin]},path='')
            with self.assertRaises(CheckFailure):check_main_pack_monitor_interface(parts)

    def test_each_retired_component_is_rejected(self):
        for ref in ['C2260','R2260','R2261','R719','U2210']:
            parts=components();parts[ref]=SimpleNamespace(properties={},pin_nets={})
            with self.assertRaises(CheckFailure):check_main_pack_monitor_interface(parts)

    def test_current_and_legacy_five_wire_snapshots_pass(self):
        for current in (False,True):
            for side in (False,True):
                with self.subTest(current=current,bms_side=side), contextlib.redirect_stdout(io.StringIO()):
                    check_bms_interconnect(interconnect_fixture(current,side),bms_side=side)

    def test_current_center_requires_global_bus_names(self):
        parts=interconnect_fixture(True)
        parts['J2073'].pin_nets['2']='/PACK_I2C_SCL'
        with self.assertRaises(CheckFailure):check_bms_interconnect(parts)

if __name__=='__main__':unittest.main()
