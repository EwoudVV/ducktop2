"""Compile-time pack gates. All nonzero analog bounds below are synthetic tests."""
import argparse
from pathlib import Path
import subprocess
import tempfile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cc',default='cc');a=ap.parse_args()
    include=Path(__file__).resolve().parents[1]/'ec_target'
    cases=[]
    def case(name,defines=None,error=None,default_asserts=False):
        cases.append((name,defines or {},error,default_asserts))
    case('defaults_locked',default_asserts=True)
    case('legacy_3a',{'PACK_USABLE_CURRENT_MA':3000})
    case('legacy_8000_unqualified_rejected',{'PACK_USABLE_CURRENT_MA':8000},'legacy pack revision')
    case('legacy_throttle_raise_rejected',{'ISL_DC_PROCHOT_MA':8192},'legacy pack revision')
    case('unknown_revision',{'PACK_HARDWARE_REVISION':3},'unknown pack hardware revision')
    case('negative_current',{'PACK_USABLE_CURRENT_MA':-1},'invalid pack current')
    case('guarded_disabled_8a',{'PACK_HARDWARE_REVISION':2,'PACK_USABLE_CURRENT_MA':8000})
    case('guarded_over_8a',{'PACK_HARDWARE_REVISION':2,'PACK_USABLE_CURRENT_MA':8001},'8A continuous design ceiling')
    for command in [0,255,8193,13056]:
        case('invalid_throttle_'+str(command),{'PACK_HARDWARE_REVISION':2,'ISL_DC_PROCHOT_MA':command},'256..12800mA')
    for command in [256,8192,12800]:
        case('bench_throttle_'+str(command),{'PACK_HARDWARE_REVISION':2,'ISL_DC_PROCHOT_MA':command})
    common={'PACK_QUALIFIED':1,'GAUGE_QUALIFIED':1,'MU_THROTTLE_QUALIFIED':1,
            'AUX_LOADS_QUALIFIED':1,'PACK_BOOT_QUALIFIED':1,'PACK_BOOT_BUDGET_MW':10000}
    case('legacy_qualified_3a',dict(common,PACK_USABLE_CURRENT_MA=3000))
    case('legacy_qualified_8a_rejected',dict(common,PACK_USABLE_CURRENT_MA=8000),'legacy pack revision')
    # These tight bounds exercise only compiler arithmetic. They are NOT a
    # Renesas accuracy claim or a candidate assembled-board qualification.
    qualified=dict(common,PACK_HARDWARE_REVISION=2,PACK_USABLE_CURRENT_MA=8000,
        PACK_GUARDS_QUALIFIED=1,PACK_DISCHARGE_SENSE_QUALIFIED=1,
        DISCHARGE_SENSE_MIN_PERMILLE=869,DISCHARGE_GAIN_MIN_PERMILLE=950,
        DISCHARGE_OFFSET_MA=100,PACK_DYNAMIC_RESERVE_MA=100,
        ISL_DC_PROCHOT_MA=8192,ISL_DC_PROCHOT_QUALIFIED=1,
        ISL_DC_PROCHOT_ACTUAL_MIN_MA=8050,ISL_DC_PROCHOT_ACTUAL_MAX_MA=8100)
    case('synthetic_fully_bounded_profile',qualified)
    for field in ['PACK_GUARDS_QUALIFIED','PACK_DISCHARGE_SENSE_QUALIFIED','ISL_DC_PROCHOT_QUALIFIED','PACK_DYNAMIC_RESERVE_MA']:
        case('missing_'+field,dict(qualified,**{field:0}),'requires qualified guards')
    case('host_path_cannot_bypass_guards',dict(qualified,PACK_BOOT_QUALIFIED=0,PACK_GUARDS_QUALIFIED=0),'requires qualified guards')
    case('reserve_exceeds_234ma',dict(qualified,PACK_DYNAMIC_RESERVE_MA=235),'allocation and dynamic reserve')
    case('throttle_does_not_hold_steady_load',dict(qualified,ISL_DC_PROCHOT_ACTUAL_MIN_MA=8000),'actual throttle bounds')
    case('throttle_too_late',dict(qualified,ISL_DC_PROCHOT_ACTUAL_MAX_MA=8200),'actual throttle bounds')
    case('throttle_bounds_reversed',dict(qualified,ISL_DC_PROCHOT_ACTUAL_MIN_MA=8150),'actual minimum and maximum')
    case('sense_unresolved',dict(qualified,DISCHARGE_SENSE_MIN_PERMILLE=0),'measured shunt and ADC')
    case('gain_unresolved',dict(qualified,DISCHARGE_GAIN_MIN_PERMILLE=0),'measured shunt and ADC')
    for field,value in [('DISCHARGE_GAIN_MIN_PERMILLE',1001),('DISCHARGE_SENSE_MIN_PERMILLE',-1),('DISCHARGE_OFFSET_MA',-1)]:
        case('invalid_'+field,dict(qualified,**{field:value}),'invalid discharge measurement')
    case('invalid_qualifier',dict(qualified,PACK_GUARDS_QUALIFIED=2),'qualification fields are 0 or 1')
    charge={'PACK_QUALIFIED':1,'GAUGE_QUALIFIED':1,'CHARGER_CURRENT_QUALIFIED':1,
            'CHARGING_QUALIFIED':1,'PACK_CHARGE_CURRENT_MA':3000,'PACK_CHARGE_VOLTAGE_MV':12528}
    case('legacy_charge_3a',charge)
    case('guarded_charge_3a',dict(charge,PACK_HARDWARE_REVISION=2,PACK_GUARDS_QUALIFIED=1))
    case('guarded_charge_without_guards',dict(charge,PACK_HARDWARE_REVISION=2),'charging requires the independent guards')
    case('charge_over_3a',dict(charge,PACK_CHARGE_CURRENT_MA=3001),'charging requires qualified current')
    qualifiers=['PACK_QUALIFIED','GAUGE_QUALIFIED','CHARGING_QUALIFIED','PACK_BRIDGE_QUALIFIED',
                'PACK_BOOT_QUALIFIED','EXTERNAL_BOOT_QUALIFIED','CHARGER_CURRENT_QUALIFIED',
                'MU_THROTTLE_QUALIFIED','AUX_LOADS_QUALIFIED','USB_POWER_QUALIFIED','VSYS_SENSE_QUALIFIED',
                'PACK_GUARDS_QUALIFIED','PACK_DISCHARGE_SENSE_QUALIFIED','ISL_DC_PROCHOT_QUALIFIED']
    with tempfile.TemporaryDirectory(prefix='ducktop2-pack-profile-') as td:
        src=Path(td)/'profile.c';obj=Path(td)/'profile.o'
        for name,defines,error,defaults in cases:
            text='#include "board_profile.h"\n#include "pack_current.h"\n'
            if defaults:
                text+='\n'.join(f'_Static_assert(DUCKTOP2_{q}==0,"default qualification changed");' for q in qualifiers)
                text+='\n_Static_assert(DUCKTOP2_PACK_USABLE_CURRENT_MA==0 && DUCKTOP2_PACK_CHARGE_CURRENT_MA==0,"current default changed");\n'
                text+='_Static_assert(DUCKTOP2_PACK_HARDWARE_REVISION==1 && DUCKTOP2_ISL_DC_PROCHOT_MA==2048,"legacy defaults changed");\n'
            text+='int main(void){return 0;}\n';src.write_text(text)
            command=[a.cc,'-std=c11','-Wall','-Wextra','-Werror','-I',str(include),'-c',str(src),'-o',str(obj)]
            command += [f'-DDUCKTOP2_{key}={value}' for key,value in defines.items()]
            run=subprocess.run(command,text=True,capture_output=True)
            if (error is None and run.returncode) or (error is not None and (run.returncode==0 or error not in run.stderr)):
                raise AssertionError(f'{name}: unexpected compile result {run.returncode}\n{run.stderr}')
    print(f'pack profile: PASS ({len(cases)} compile cases; default locks, revision isolation, reserve, throttle and charge bounds)')
if __name__=='__main__':main()
