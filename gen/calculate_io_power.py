#!/usr/bin/env python3
"""Conditional I/O loom and signed ground-cut bounds, with no equal sharing."""
from dataclasses import asdict,dataclass
import argparse
import json
import math

@dataclass(frozen=True)
class Limits:
    center_vsys_min_v: float=8.7
    usb_max_v: float=5.238866489
    usb_startup_a: float=5.6
    usb_steady_a: float=5.5
    converter_efficiency_min: float=.85
    vsys_loom_positive_ohm: float=.093
    vsys_board_positive_ohm: float=.015
    seam_ground_max_v: float=.010
    left_sys3_a: float=2.0
    right_sys3_a: float=.025
    left_mcu3_a: float=.100
    right_mcu3_a: float=.100
    right_sys5_a: float=.351
    right_pcie_a: float=.400
    endpoint_startup_extra_a: float=.400
    right_usb5_a: float=2.015
    main_selected_input_a: float=3.5
    raw_aon_aggregate_a: float=2.0
    left_dc_signal_a: float=.100
    right_dc_signal_a: float=.100
    seam_design_a: float=8.0


def constant_power_current(power_w,source_v,positive_ohm,ground_v):
    if power_w<0 or source_v<=ground_v or positive_ohm<0:raise ValueError('invalid power path')
    voltage=source_v-ground_v
    if not positive_ohm:return power_w/voltage
    discriminant=voltage*voltage-4*positive_ohm*power_w
    if discriminant<=0:raise ValueError('constant-power operating point is not supported')
    # Stable, low-current root of I*(V-R*I)=P. The other root is unstable.
    return 2*power_w/(voltage+math.sqrt(discriminant))


def calculate(l=Limits()):
    if not 0<l.converter_efficiency_min<=1:raise ValueError('invalid efficiency')
    resistance=l.vsys_loom_positive_ohm+l.vsys_board_positive_ohm
    usb_w=l.usb_max_v*l.usb_startup_a
    current=constant_power_current(usb_w/l.converter_efficiency_min,
                                  l.center_vsys_min_v,resistance,l.seam_ground_max_v)
    # Signed injections into left and right ground are:
    # gL = VSYS + SYS3L + MCU3L - USB5LR - PD1selected - AUXraw - PD1rawAON + dL
    # gR = USB5LR + SYS5R + SYS3R + PCIeR + MCU3R - PD2selected - PD2rawAON + dR
    # selected inputs are mutually exclusive. Raw AON feeds can coexist, but
    # their sum is bounded. USB5LR cancels in gL+gR. Signed signal currents
    # include USB2, HCSL, DDC/HPD and control paths; no AC-coupled DC is invented.
    bounds={
      'left_positive':current+l.left_sys3_a+l.left_mcu3_a+l.left_dc_signal_a,
      'left_negative':l.right_usb5_a+l.main_selected_input_a+l.raw_aon_aggregate_a+l.left_dc_signal_a,
      'right_positive':l.right_usb5_a+l.right_sys5_a+l.right_sys3_a+l.right_pcie_a+
                       l.endpoint_startup_extra_a+l.right_mcu3_a+l.right_dc_signal_a,
      'right_negative':l.main_selected_input_a+l.raw_aon_aggregate_a+l.right_dc_signal_a,
      'combined_positive':current+l.left_sys3_a+l.right_sys3_a+l.left_mcu3_a+l.right_mcu3_a+
                          l.right_sys5_a+l.right_pcie_a+l.endpoint_startup_extra_a+
                          l.left_dc_signal_a+l.right_dc_signal_a,
      'combined_negative':l.main_selected_input_a+l.raw_aon_aggregate_a+l.left_dc_signal_a+l.right_dc_signal_a}
    worst=max(bounds.values())
    whole_eff=usb_w/(l.center_vsys_min_v*current)
    return {'status':'PASS_CONDITIONAL' if worst<=l.seam_design_a and whole_eff>=.80 else 'FAIL',
            'boundary':'normal and qualified startup states only; no physical qualification or fuse/ESD fault clearance',
            'qualification_limits':asdict(l),'usb_input_a':current,
            'regulator_input_min_v':l.center_vsys_min_v-l.seam_ground_max_v-resistance*current,
            'whole_path_efficiency_min':whole_eff,'signed_cut_absolute_bounds_a':bounds,
            'worst_ground_edge_a':worst,'remaining_to_8a':l.seam_design_a-worst,
            'left_sys3_min_v':3.258999702-l.left_sys3_a*(.093+.010)-.010-.020}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
    result=calculate();text=json.dumps(result,indent=2)+'\n'
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(text)
    print(text,end='');return 0 if result['status']=='PASS_CONDITIONAL' else 1

if __name__=='__main__':raise SystemExit(main())
