"""Check the AUX fuse identities, protection topology and current allocations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from aux_input_contract import (
    AUX_MAX_SOURCE_BUDGET_MA, FUSE_BODY_MAX_HEIGHT_MM,
    FUSE_BREAKING_DC_A, FUSE_CONTINUOUS_DESIGN_FACTOR, FUSE_DATASHEET,
    FUSE_DATASHEET_SHA256, FUSE_FOOTPRINT, FUSE_INSTALLED_HEIGHT_BUDGET_MM,
    FUSE_LOCAL_AMBIENT_LIMIT_C, FUSE_MPN, FUSE_RATED_A, FUSE_RATED_DC_V,
    FUSE_TEMPERATURE_FACTOR, FUSE_TYPICAL_COLD_OHM, FUSE_TYPICAL_MELTING_I2T,
)
from verify_electrical_calculations import component_values, resistor

P = '/Power & Battery/'
L = '/PD1 Dual-Role/'


def inspect(center, left):
    failures = []
    assertions = 0

    def require(ok, message):
        nonlocal assertions
        assertions += 1
        if not ok:
            failures.append(message)

    def pins(values, ref, expected):
        for pin, net in expected.items():
            require(values.pins.get(ref, {}).get(str(pin)) == net,
                    f'{ref}.{pin}: expected {net}')

    def part(values, ref, mpn):
        require(values.mpn(ref) == mpn, f'{ref}: expected {mpn}')

    for values, ref in [(center, 'F190'), (left, 'F195')]:
        part(values, ref, FUSE_MPN)
        require(values.parts.get(ref, ('', ''))[1] == FUSE_FOOTPRINT,
                ref + ': wrong land pattern')
        require(values.get(ref, '').startswith('5A AUX '), ref + ': wrong value or population')
    pins(left, 'J190', {1: L + 'AUX_DC_TERM', 2: 'GND'})
    pins(left, 'F195', {1: L + 'AUX_DC_TERM', 2: '/AUX_DC_RAW'})
    pins(center, 'F190', {1: '/AUX_DC_RAW', 2: P + 'AUX_DC_FUSED'})
    part(center, 'D190', 'SMCJ24CA-E3/57T')
    pins(center, 'D190', {1: P + 'AUX_DC_FUSED', 2: 'GND'})
    part(center, 'Q13', 'CSD19537Q3')
    pins(center, 'Q13', {1: P + 'AUX_EFUSE_IN_SYS', 2: P + 'AUX_EFUSE_IN_SYS',
                        3: P + 'AUX_EFUSE_IN_SYS', 4: P + 'AUX_EFUSE_BGATE',
                        5: P + 'AUX_DC_FUSED'})
    part(center, 'U12', 'TPS26630RGER')
    pins(center, 'U12', {1: P + 'AUX_DC_FUSED', 2: P + 'AUX_DC_FUSED',
                        3: P + 'AUX_EFUSE_BGATE', 4: P + 'AUX_EFUSE_DRV',
                        5: P + 'AUX_EFUSE_IN_SYS', 9: P + 'AUX_EFUSE_DVDT',
                        10: P + 'AUX_EFUSE_ILIM', 11: 'GND',
                        14: '/AUX_FAULT_N', 16: '/AUX_PGOOD',
                        17: P + 'AUX_DC_PROTECTED', 18: P + 'AUX_DC_PROTECTED',
                        8: 'GND', 25: 'GND'})
    pins(center, 'R710', {1: P + 'AUX_EFUSE_ILIM', 2: 'GND'})
    pins(center, 'C723', {1: P + 'AUX_EFUSE_DVDT', 2: 'GND'})
    require(center.get('C723', '').startswith('100n'), 'C723: retain the controlled output ramp')
    # Both main and standby branches must stay downstream of the center fuse.
    pins(center, 'D711', {1: P + 'AON_RAW', 2: P + 'AUX_DC_FUSED'})
    pins(center, 'R191', {1: P + 'AUX_DC_FUSED', 2: P + 'AUX_DC_DIV'})
    r = resistor(center, 'R710')
    tolerance = center.environment_tolerance('R710')
    require(abs(r - 6040) < .01, 'R710: retain the 6.04 kohm main-branch current limit')
    require(tolerance <= .05, 'R710: the full resistance allowance exceeds 5 percent')
    nominal = 18000 / r
    # Use the widest listed IOL percentage (10%) across the programmed range,
    # plus the complete resistor allowance. This is a conservative screen;
    # the assembled eFuse and startup waveforms still require measurement.
    low = 18000 * .90 / (r * (1 + tolerance))
    high = 18000 * 1.10 / (r * (1 - tolerance))
    require(low >= 2.5 and high <= 3.5, 'AUX main-branch current-limit screen changed')
    continuous = FUSE_RATED_A * FUSE_CONTINUOUS_DESIGN_FACTOR * FUSE_TEMPERATURE_FACTOR
    require(AUX_MAX_SOURCE_BUDGET_MA / 1000 < continuous,
            'total AUX source budget exceeds the derated fuse allocation')
    require(FUSE_RATED_DC_V >= 32 and FUSE_BREAKING_DC_A >= 1000,
            'replacement must retain the original fuse voltage and interruption capability')
    require(FUSE_INSTALLED_HEIGHT_BUDGET_MM >= FUSE_BODY_MAX_HEIGHT_MM + .3 - 1e-9,
            'installed height must include assembly space')
    return {
        'status': 'PASS_DESIGN_SCREEN' if not failures else 'FAIL',
        'assertions': assertions, 'failures': failures,
        'part': {'mpn': FUSE_MPN, 'footprint': FUSE_FOOTPRINT,
                 'datasheet': FUSE_DATASHEET, 'datasheet_sha256': FUSE_DATASHEET_SHA256,
                 'body_max_height_mm': FUSE_BODY_MAX_HEIGHT_MM,
                 'installed_height_budget_mm': FUSE_INSTALLED_HEIGHT_BUDGET_MM,
                 'rated_a': FUSE_RATED_A, 'rated_dc_v': FUSE_RATED_DC_V,
                 'interrupting_a_at_rated_dc_voltage': FUSE_BREAKING_DC_A},
        'normal_operation': {
            'total_source_budget_a': AUX_MAX_SOURCE_BUDGET_MA / 1000,
            'fuse_local_ambient_design_limit_c': FUSE_LOCAL_AMBIENT_LIMIT_C,
            'continuous_design_factor': FUSE_CONTINUOUS_DESIGN_FACTOR,
            'temperature_screen_factor': FUSE_TEMPERATURE_FACTOR,
            'fuse_continuous_allocation_a': continuous,
            'main_efuse_nominal_limit_a': nominal,
            'main_efuse_screen_min_a': low, 'main_efuse_screen_max_a': high,
            'R710_environment_allowance_fraction': tolerance,
            'two_fuse_typical_cold_drop_at_3a_v': 2 * 3 * FUSE_TYPICAL_COLD_OHM,
            'each_fuse_typical_cold_loss_at_3a_w': 3**2 * FUSE_TYPICAL_COLD_OHM,
            'note': 'The 0.75 continuous factor is a project allocation. The 0.95 temperature factor is below the published curve through 85 C. Neither is a measured installed rating. The existing firmware reserves raw standby current before allocating charger current.'},
        'fault_and_pulse_limits': {
            'guaranteed_max_opening_at_2x_rated_s': 60,
            'I2t_upper_for_constant_10a_until_60s_a2s': 6000,
            'typical_melting_I2t_at_10x_rated_a2s': FUSE_TYPICAL_MELTING_I2T,
            'typical_melting_I2t_is_total_clearing_limit': False,
            'selective_opening_of_F190_before_F195_guaranteed': False,
            'notes': [
                'The manufacturer prohibits prolonged operation between 100% and 200% of fuse rating. A current-limited fault source in that region needs its own shutdown or a demonstrated safe result.',
                'The ordinary overload limiter is U12; these fuses back up wiring and faults ahead of or through failed semiconductor protection.',
                'The 6000 A2s figure is a conservative constant-current integration at the one specified 200% time limit. It is not a fuse total-clearing rating or proof that the unrouted copper survives.',
                'The manufacturer test board uses 1 oz copper, 5 mm wide, for this fuse rating. Final pad entries, copper, transitions and wire joints need their own current and fault checks.',
                'Measure hot-plug and repeated-start I2t. The typical melting value is not a guaranteed pulse-withstand limit.',
                'No arbitrary battery, solar source or fault-current range is approved by the part substitution alone. Keep AUX operation within a separately qualified source envelope.'
            ]},
        'hardware_qualified': False,
        'manufacturing_ready': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--center-netlist', type=Path, required=True)
    parser.add_argument('--left-netlist', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(component_values(args.center_netlist), component_values(args.left_netlist))
    report['input_netlist_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                    for name, path in [('center', args.center_netlist), ('left', args.left_netlist)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], report['assertions'], 'assertions;', len(report['failures']), 'failures')
    for failure in report['failures']:
        print(failure)
    return bool(report['failures'])


if __name__ == '__main__':
    raise SystemExit(main())
