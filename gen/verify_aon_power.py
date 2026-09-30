#!/usr/bin/env python3
"""Check standby wiring and tolerance screens from a native KiCad netlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from verify_electrical_calculations import (
    component_values, divider_corners, metal_strip_bounds, procurement_checks,
)

POWER = "/Power & Battery/"


@dataclass(frozen=True)
class AonLimits:
    """Explicit design allocations; none is a measured board rating."""

    load_a: float = .450
    efficiency: float = .80
    buck_input_floor_v: float = 4.05
    load_capacitance_f: float = 250e-6
    initial_case_c: float = 100
    # CSD18540Q5B Qg(max) is53nC at10V, not at the controller's18V
    # high corner. This200nC allocation needs a measured discharge waveform.
    intrinsic_gate_charge_c: float = 200e-9


def inspect(netlist: Path, limits: AonLimits = AonLimits()) -> dict:
    if (not 0 < limits.efficiency <= 1 or min(limits.load_a,
            limits.buck_input_floor_v, limits.load_capacitance_f,
            limits.intrinsic_gate_charge_c) <= 0):
        raise ValueError('AON load, voltage, capacitance, charge and efficiency must be positive')
    v = component_values(netlist)
    failures = []
    expected_pins = {}

    def require(ok, description):
        if not ok:
            failures.append(description)

    def pins(ref, expected):
        expected_pins.setdefault(ref, {}).update(
            {str(k): n for k, n in expected.items()}
        )
        actual = v.pins.get(ref, {})
        for pin, net in expected.items():
            require(
                actual.get(str(pin)) == net,
                f"{ref}.{pin}: expected {net}, got {actual.get(str(pin))}",
            )

    def identity(ref, mpn):
        require(v.mpn(ref) == mpn, f"{ref}: expected {mpn}")

    for ref, mpn in {
        "U718": "LTC4368IMS-2#PBF",
        "U2660": "LTC4231IMS-1#PBF",
        "U2650": "LM74700QDBVRQ1",
        "Q2660": "CSD18540Q5B",
        "RS2660": "WSL1206R1800FEA",
        "R2662": "WSL1206R1800FEA",
        "C2660": "C0805C223J5GACTU",
        "C2661": "GRT188R61H105ME13D",
        "C2662": "GRT188R61H105ME13D",
        "U5": "TPS62933DRLR",
        "RS2620": "WSL2512R0220FEA18",
    }.items():
        identity(ref, mpn)
    pins(
        "U2650",
        {
            1: POWER + "AON_SYS_VCAP",
            2: "GND",
            3: "/VSYS",
            4: POWER + "AON_RAW",
            5: POWER + "AON_SYS_GATE",
            6: "/VSYS",
        },
    )
    pins(
        "Q2650",
        {
            1: "/VSYS",
            2: "/VSYS",
            3: "/VSYS",
            4: POWER + "AON_SYS_GATE",
            5: POWER + "AON_RAW",
        },
    )
    pins(
        "U718",
        {
            1: POWER + "AON_RAW",
            2: POWER + "AON_EFUSE_UV",
            3: POWER + "AON_EFUSE_OV",
            4: POWER + "AON_RETRY",
            5: "GND",
            6: POWER + "AON_PROTECT_SHDN",
            7: "/AON_FAULT_N",
            8: POWER + "AON_PROTECTED",
            9: POWER + "AON_PROTECT_SENSE",
            10: POWER + "AON_GATE_DRV",
        },
    )
    for i in (1, 2):
        stem = POWER + f"AON_PD{i}"
        source = f"/PD{i}_VBUS_RAW"
        pins(
            f"U{2619+i}",
            {
                1: stem + "_VCAP",
                2: "GND",
                3: source,
                4: POWER + "AON_RAW",
                5: stem + "_GATE",
                6: source,
            },
        )
        pins(
            f"Q{2619+i}",
            {1: source, 2: source, 3: source, 4: stem + "_GATE", 5: POWER + "AON_RAW"},
        )
        pins(f"C{2619+i}", {1: stem + "_VCAP", 2: source})
    for ref, source, drain in (
        ("Q2622", POWER + "AON_FET_COMMON", POWER + "AON_RAW"),
        ("Q2623", POWER + "AON_FET_COMMON", POWER + "AON_PROTECT_SENSE"),
    ):
        pins(
            ref, {1: source, 2: source, 3: source, 4: POWER + "AON_FET_GATE", 5: drain}
        )
    for ref, a, b in (
        ("D711", POWER + "AON_RAW", POWER + "AUX_DC_FUSED"),
        ("R795", POWER + "AON_RAW", POWER + "AON_EFUSE_UV"),
        ("R796", POWER + "AON_EFUSE_UV", "GND"),
        ("R797", POWER + "AON_RAW", POWER + "AON_EFUSE_OV"),
        ("R798", POWER + "AON_EFUSE_OV", "GND"),
        ("R799", POWER + "AON_RAW", POWER + "AON_PROTECT_SHDN"),
        ("R2620", POWER + "AON_GATE_DRV", POWER + "AON_FET_GATE"),
        ("D2620", POWER + "AON_GATE_DRV", POWER + "AON_FET_GATE"),
        ("C799", POWER + "AON_FET_GATE", POWER + "AON_PROTECTED"),
        ("C2622", POWER + "AON_RETRY", "GND"),
        ("C795", POWER + "AON_RAW", "GND"),
        ("C796", POWER + "AON_RAW", "GND"),
        ("C797", "/EC_AON_IN", "GND"),
        ("C798", "/EC_AON_IN", "GND"),
        ("C2650", POWER + "AON_SYS_VCAP", "/VSYS"),
        ("C2651", POWER + "AON_PROTECTED", "GND"),
    ):
        pins(ref, {1: a, 2: b})
    pins("RS2620", {1: POWER + "AON_PROTECT_SENSE", 2: POWER + "AON_PROTECTED"})
    pins(
        "U2660",
        {
            1: POWER + "AON_LIMIT_SENSE",
            2: POWER + "AON_PROTECTED",
            3: POWER + "AON_LIMIT_SHDN",
            4: POWER + "AON_PROTECTED",
            5: POWER + "AON_PROTECTED",
            6: "GND",
            8: "GND",
            9: "/AON_FAULT_N",
            10: POWER + "AON_LIMIT_TIMER",
            11: "/EC_AON_IN",
            12: POWER + "AON_LIMIT_DRV",
        },
    )
    expected_pins["U2660"]["7"] = None
    require(
        v.pins.get("U2660", {}).get("7", "").startswith("unconnected-"),
        "unused GNDSW must be marked no-connect",
    )
    for ref in ("RS2660", "R2662"):
        pins(ref, {1: POWER + "AON_PROTECTED", 2: POWER + "AON_LIMIT_SENSE"})
    pins(
        "Q2660",
        {
            1: "/EC_AON_IN",
            2: "/EC_AON_IN",
            3: "/EC_AON_IN",
            4: POWER + "AON_LIMIT_GATE",
            5: POWER + "AON_LIMIT_SENSE",
        },
    )
    pins("R2661", {1: POWER + "AON_LIMIT_DRV", 2: POWER + "AON_LIMIT_GATE"})
    pins("R2664", {1: POWER + "AON_LIMIT_DRV", 2: POWER + "AON_LIMIT_RAMP"})
    pins("C2660", {1: POWER + "AON_LIMIT_RAMP", 2: "GND"})
    for ref in ("C2661", "C2662"):
        pins(ref, {1: POWER + "AON_LIMIT_TIMER", 2: "GND"})
    pins("R2663", {1: POWER + "AON_PROTECTED", 2: POWER + "AON_LIMIT_SHDN"})
    pins("TP2660", {1: POWER + "AON_LIMIT_SHDN"})
    pins("TP2661", {1: "GND"})
    pins("RS2601", {1: "/VSYS", 2: POWER + "CHG_SRN"})
    pins(
        "Q25",
        {
            1: "/PACK_POS_FUSED",
            2: "/PACK_POS_FUSED",
            3: "/PACK_POS_FUSED",
            5: POWER + "CHG_SRN",
        },
    )
    require(
        v.number("R2661") == 10 and v.number("R2664") == 1000,
        "gate damping and compensation branch changed",
    )

    parallel = lambda a, b: a * b / (a + b)
    sense = parallel(v.number("RS2660"), v.number("R2662"))
    # Conservative component/assembly screens, not service-life guarantees.
    rmin = parallel(v.number("RS2660") * 0.94, v.number("R2662") * 0.94)
    rmax = parallel(v.number("RS2660") * 1.06, v.number("R2662") * 1.06)
    for ref in ('RS2660','R2662'):
        derived_low,derived_high=metal_strip_bounds(v,ref)
        require(v.number(ref)*.94 <= derived_low and derived_high <= v.number(ref)*1.06,
                f'{ref}: six-percent screen does not cover the published drift terms')
    shunt_power = max(0.090**2/(v.number(ref)*.94) for ref in ('RS2660','R2662'))
    require(
        shunt_power < 0.25 * (170 - 100) / (170 - 70),
        "sense-resistor power exceeds the 100 C derating screen",
    )
    breaker_min = 0.047 / rmax
    limiter_min = 0.065 / rmax
    limiter_max = 0.090 / rmin
    fast_rmin,fast_rmax=metal_strip_bounds(v,'RS2620')
    # LTC4368 RevC p3:40..60mV with VOUT=VIN;30..70mV with
    # VOUT=0 at VIN12V. Keep the lower short-circuit floor for coordination.
    fast_breaker_min=.030/fast_rmax
    require(limiter_max < fast_breaker_min,
            'active-limit high corner can trip the upstream fast breaker')
    timer = v.number("C2661") + v.number("C2662")
    # X5R: initial, temperature, aging and low-voltage bias allowances.
    # Use the more conservative of the100nF delay table and independent
    # comparator/current corners. A fresh event must start at<=130mV;
    # otherwise timer accumulation makes a shorter event possible.
    timer_min = timer * 0.8 * 0.85 * 0.9 * 0.9 * min(17000,(1.170-.130)/65e-6)
    timer_max = timer * 1.2 * 1.15 * max(35000,1.216/35e-6)
    timer_discharge_max=timer*1.2*1.15*1.216/3e-6
    # Worst-case sustained pulse duty at which the timer can accumulate:
    # 65uA maximum charge against3uA minimum discharge.
    accumulating_duty=3/(65+3)
    gate_cap_max=v.number('C2660')*1.053
    # Fully discharge the external cap from25V output+18V gate overdrive,
    # at the minimum0.6mA slow pull-down, plus intrinsic gate charge and
    # five time constants of its series resistor. This replaces a fixed1.2ms.
    gate_off=((gate_cap_max*(25+18)+limits.intrinsic_gate_charge_c)/.0006
              +5*v.number('R2664')*(1+v.environment_tolerance('R2664'))*gate_cap_max)
    cap_refs = v.capacitors_on("/EC_AON_IN")
    require(
        set(cap_refs) == {"C797", "C798", "C36", "C37"},
        f"update the load-capacitance review for {cap_refs}",
    )
    cap_screen = 2 * v.number("C797") + 1.4 * sum(
        v.number(r) for r in cap_refs if r != "C797"
    )
    cap_max = limits.load_capacitance_f
    require(cap_screen <= cap_max, "fitted input capacitors exceed the 250 uF screen")
    low, high = divider_corners(
        v.number("R35"),
        v.number("R36"),
        v.environment_tolerance("R35"),
        v.environment_tolerance("R36"),
        0.784,
        0.816,
    )
    load_max = limits.load_a
    require(0 < limits.efficiency <= 1, 'invalid buck efficiency')
    input_power = load_max * (high + 0.020) / limits.efficiency + 0.020
    input_floor = limits.buck_input_floor_v
    require(
        input_power / input_floor < breaker_min,
        "steady standby allocation exceeds minimum breaker current",
    )
    # Constant-power load while the input capacitor charges at minimum limit.
    start, end = 3.8, 25.0
    require(
        limiter_min * start > input_power,
        "no positive charging current at the low corner",
    )
    recovery = cap_max * (
        (end - start) / limiter_min
        + input_power
        / limiter_min**2
        * math.log(
            (limiter_min * end - input_power) / (limiter_min * start - input_power)
        )
    ) if limiter_min*start > input_power else math.inf
    require(recovery < timer_min, "input step can expire the current-limit timer")
    startup_overcurrent = []
    for gate_current in (7e-6, 13e-6):
        for gate_cap in (v.number("C2660") * 0.947, v.number("C2660") * 1.053):
            slope = gate_current / gate_cap
            remaining = breaker_min - cap_max * slope
            require(remaining > 0, "capacitor ramp alone exceeds breaker")
            if remaining > 0:
                startup_overcurrent.append(
                    max(0, input_power / remaining - start) / slope
                )
    startup_worst=max(startup_overcurrent,default=math.inf)
    require(startup_worst < timer_min, "startup overcurrent outlasts timer")
    # CSD18540Q5B Fig.10: conservative graph-read 2.5 A at 30 V/100 ms,
    # Tc=25 C. Derate to initial Tc=100 C using Tjmax=175 C.
    soa_current = 2.5 * (175 - limits.initial_case_c) / (175 - 25)
    require(limiter_max < soa_current, "pass-FET pulse exceeds derated SOA screen")
    require(
        timer_max + gate_off < 0.100, "fault pulse exceeds reviewed 100 ms SOA point"
    )
    require(input_floor > 3.8, "buck input has no headroom above its operating minimum")
    # The arithmetic resolves actual MPN values; reject misleading labels too.
    failures.extend(f'{check.name}: {check.equation}'
                    for check in procurement_checks('AON',v) if not check.passed)
    report = {
        "status": "FAIL" if failures else "PASS_WITH_UNMEASURED_LIMITS",
        "netlist_sha256": hashlib.sha256(netlist.read_bytes()).hexdigest(),
        "failures": failures,
        "expected_pins": expected_pins,
        "sense_nominal_ohm": sense,
        "per_shunt_power_at_current_limit_w": shunt_power,
        "sense_screen_ohm": [rmin, rmax],
        "breaker_min_a": breaker_min,
        "active_limit_a": [limiter_min, limiter_max],
        "fast_breaker_normal_a": [.040/fast_rmax,.060/fast_rmin],
        "fast_breaker_short_at_12v_a": [fast_breaker_min,.070/fast_rmin],
        "active_to_fast_breaker_margin": fast_breaker_min/limiter_max,
        "timer_s": [timer_min, timer_max],
        "timer_full_discharge_screen_s": timer_discharge_max,
        "required_timer_start_below_v": .130,
        "minimum_accumulating_overload_duty": accumulating_duty,
        "fault_with_gate_off_s": timer_max + gate_off,
        "gate_off_screen_s": gate_off,
        "intrinsic_gate_charge_screen_c": limits.intrinsic_gate_charge_c,
        "load_capacitors": cap_refs,
        "load_cap_screen_f": cap_screen,
        "load_cap_ceiling_f": cap_max,
        "mcu_rail_static_v": [low, high],
        "standby_load_allocation_a": load_max,
        "input_power_screen_w": input_power,
        "required_buck_input_floor_v": input_floor,
        "recharge_s": recovery,
        "startup_overcurrent_s": startup_worst,
        "pass_fet_soa_screen_a": soa_current,
        "timed_breaker_scope": 'LTC4231 IN=12V electrical table; confirm4.05..25V and repeated events on hardware',
        "fast_breaker_scope": 'LTC4368 thresholds differ when its output is shorted; propagation overshoot remains unmeasured',
        "fault_recovery": 'LTC4231-1 latch resets after SHDN or IN is low for>100us; upstream faults can remove IN and reset it too',
        "unmeasured": [
            "complete standby load, including both OLED modules",
            "4.05 V minimum at the buck under the permitted source/load states",
            "at least 80 percent buck efficiency over the standby envelope",
            "effective capacitance and timer range over temperature and age",
            "initial pass-FET case at or below 100 C and timer capacitors at or below 85 C",
            "gate-loop stability, repeated source transitions and BMS/PROCHOT response",
            "gate discharge including the200nC intrinsic-charge screen and fault overshoot",
            "timer accumulation across repeated overload pulses; independent single pulses do not cover this",
            "load-side short discharges the input reservoir without either upstream limiter controlling that initial pulse",
        ],
        "physical_tests": "NOT_RUN",
    }
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("netlist", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = inspect(a.netlist)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])
    for failure in report["failures"]:
        print(failure)
    print(
        f"active limit {report['active_limit_a']}; recharge {report['recharge_s']*1000:.2f} ms; minimum timer {report['timer_s'][0]*1000:.2f} ms"
    )
    raise SystemExit(bool(report["failures"]))


if __name__ == "__main__":
    main()
