#!/usr/bin/env python3
"""Check standby wiring and tolerance screens from a native KiCad netlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from verify_electrical_calculations import component_values, divider_corners

POWER = "/Power & Battery/"


def inspect(netlist: Path) -> dict:
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
    shunt_power = 0.090**2 / (v.number("RS2660") * 0.94)
    require(
        shunt_power < 0.25 * (170 - 100) / (170 - 70),
        "sense-resistor power exceeds the 100 C derating screen",
    )
    breaker_min = 0.047 / rmax
    limiter_min = 0.065 / rmax
    limiter_max = 0.090 / rmin
    timer = v.number("C2661") + v.number("C2662")
    # X5R: initial, temperature, aging and low-voltage bias allowances.
    timer_min = timer * 0.8 * 0.85 * 0.9 * 0.9 * 17000
    timer_max = timer * 1.2 * 1.15 * 35000
    gate_off = 0.0012
    cap_refs = v.capacitors_on("/EC_AON_IN")
    require(
        set(cap_refs) == {"C797", "C798", "C36", "C37"},
        f"update the load-capacitance review for {cap_refs}",
    )
    cap_screen = 2 * v.number("C797") + 1.4 * sum(
        v.number(r) for r in cap_refs if r != "C797"
    )
    cap_max = 250e-6
    require(cap_screen <= cap_max, "fitted input capacitors exceed the 250 uF screen")
    low, high = divider_corners(
        v.number("R35"),
        v.number("R36"),
        v.environment_tolerance("R35"),
        v.environment_tolerance("R36"),
        0.784,
        0.816,
    )
    load_max = 0.450
    input_power = load_max * (high + 0.020) / 0.80 + 0.020
    input_floor = 4.05
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
    )
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
    require(max(startup_overcurrent) < timer_min, "startup overcurrent outlasts timer")
    # CSD18540Q5B Fig.10: conservative graph-read 2.5 A at 30 V/100 ms,
    # Tc=25 C. Derate to initial Tc=100 C using Tjmax=175 C.
    soa_current = 2.5 * (175 - 100) / (175 - 25)
    require(limiter_max < soa_current, "pass-FET pulse exceeds derated SOA screen")
    require(
        timer_max + gate_off < 0.100, "fault pulse exceeds reviewed 100 ms SOA point"
    )
    require(input_floor > 3.8, "buck input has no headroom above its operating minimum")
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
        "timer_s": [timer_min, timer_max],
        "fault_with_gate_off_s": timer_max + gate_off,
        "load_capacitors": cap_refs,
        "load_cap_screen_f": cap_screen,
        "load_cap_ceiling_f": cap_max,
        "mcu_rail_static_v": [low, high],
        "standby_load_allocation_a": load_max,
        "input_power_screen_w": input_power,
        "required_buck_input_floor_v": input_floor,
        "recharge_s": recovery,
        "startup_overcurrent_s": max(startup_overcurrent),
        "pass_fet_soa_screen_a": soa_current,
        "unmeasured": [
            "complete standby load, including both OLED modules",
            "4.05 V minimum at the buck under the permitted source/load states",
            "at least 80 percent buck efficiency over the standby envelope",
            "effective capacitance and timer range over temperature and age",
            "initial pass-FET case at or below 100 C and timer capacitors at or below 85 C",
            "gate-loop stability, repeated source transitions and BMS/PROCHOT response",
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
