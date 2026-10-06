#!/usr/bin/env python3
"""Check the center battery path and its shared startup envelope from netlists."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from verify_electrical_calculations import Check, component_values, metal_strip_bounds
from verify_100w_calculations import gate_return
from verify_bq76922_calculations import (
    STARTUP_CAPACITANCE_F, STARTUP_LOAD_A, STARTUP_STACK_V, startup_metrics,
)

P = "/Power & Battery/"
DISCHARGE_A = 8.0
CHARGE_A = 3.0


def inspect(center, left, right, bms):
    failures = []
    checks = []

    def require(ok, text):
        if not ok:
            failures.append(text)

    def pins(values, ref, wanted):
        for pin, net in wanted.items():
            require(values.pins.get(ref, {}).get(str(pin)) == net,
                    f"{ref}.{pin} must connect to {net}")

    identities = {
        "U2": "ISL9241IRTZ", "Q25": "CSD17575Q3",
        "U10": "BQ34Z100PWR-G1", "RS1": "WSLP25125L000FEA",
        "RS2601": "WSLP2512R0100FEA", "J2071": "2060-452/998-404",
    }
    for ref, mpn in identities.items():
        require(center.mpn(ref) == mpn, f"{ref} requires {mpn}")
    require(center.parts.get("Q25", (None, None))[1] == "ducktop2:CSD17575Q3_DQG",
            "Q25 requires the DQG footprint")
    pins(center, "Q25", {1: "/PACK_POS_FUSED", 2: "/PACK_POS_FUSED",
                        3: "/PACK_POS_FUSED", 4: P + "CHG_BGATE", 5: P + "CHG_SRN"})
    pins(center, "R2600", {1: P + "CHG_BGATE", 2: "/PACK_POS_FUSED"})
    pins(center, "RS2601", {1: "/VSYS", 2: P + "CHG_SRN"})
    pins(center, "RS1", {1: "/FG_VSS", 2: "GND"})
    pins(center, "U2", {1: P + "CHG_SRN", 2: "/VSYS", 31: P + "BATP_SENSE",
                       32: P + "CHG_BGATE"})
    pins(center, "R704", {1: "/PACK_POS_FUSED", 2: P + "BATP_SENSE"})
    pins(center, "U10", {8: "/FG_VSS", 9: P + "FG_SRP", 10: P + "FG_SRN"})
    pins(center, "R183", {1: "/FG_VSS", 2: P + "FG_SRP"})
    pins(center, "R184", {1: "GND", 2: P + "FG_SRN"})
    pins(center, "C181", {1: P + "FG_SRP", 2: P + "FG_SRN"})
    pins(center, "J2071", {1: "/FG_VSS", 2: "/PACK_POS_FUSED"})
    pins(bms, "J2072", {1: "/PACK_POS_FUSED", 2: "/FG_VSS"})
    pins(bms, "J2", {1: "/PACK_NEG_RAW", 2: "/PACK_POS_RAW"})
    require(bms.mpn("J2072") == "2060-452/998-404", "J2072 requires the two-pole WAGO")
    require(bms.mpn("F1") == "3-101-051", "F1 requires the selected 10 A fuse")

    # FN8945 Rev6 specifies 15 uA minimum sourcing at BGATE = VBAT + 2 V.
    # This is a test-point load check, not a guaranteed current over the
    # entire gate ramp. CSD17575Q3 IGSS(max) is 100 nA at the stated 25 C point.
    gate_r_low = center.number("R2600") * (1 - center.environment_tolerance("R2600"))
    gate_load = 2.0 / gate_r_low + .1e-6
    checks.extend(gate_return(center))
    require(center.mpn("R2600") == "RC0603FR-071ML", "R2600 requires RC0603FR-071ML")

    # Resistance includes the resistor's rated 170C temperature ceiling.
    # Power is separately derated for a 100C local ambient. A surface
    # temperature reading alone does not establish the element temperature.
    rs1_low, rs1_high = metal_strip_bounds(center, "RS1", high_c=170)
    rs2_low, rs2_high = metal_strip_bounds(center, "RS2601", high_c=170)
    # Retain the design's conservative 2 W labels although WSLP2512 is
    # specified at 3 W. Neither rating proves the installed temperature.
    shunt_power = 2.0 * (170 - 100) / (170 - 70)
    for ref, high in (("RS1", rs1_high), ("RS2601", rs2_high)):
        checks.append(Check(ref + " loss at 8 A", DISCHARGE_A ** 2 * high,
                            "W", 0, shunt_power,
                            "I^2*R(high), with TCR through 170C plus initial/endurance/solder drift; conservative 2W derated for 100C ambient"))
    for current, label in ((DISCHARGE_A, "discharge"), (CHARGE_A, "charge")):
        checks.append(Check("gauge " + label + " sense magnitude", current * rs1_high * 1000,
                            "mV", 0, 125,
                            "I*RS1(high); BQ34Z100-G1 recommended differential range is +/-125mV"))
    checks.append(Check("charger discharge sense magnitude", DISCHARGE_A * rs2_high * 1000,
                        "mV", 0, 300,
                        "I*RS2601(high); ISL9241 +/-300mV absolute differential limit, not an accuracy guarantee"))

    # The 2x hot multiplier is an explicit sizing screen above TI's typical
    # temperature curve. It is not a guaranteed hot RDS(on) specification.
    q25_r_hot_screen = .0032 * 2.0
    q25_loss = DISCHARGE_A ** 2 * q25_r_hot_screen
    component_r = rs1_high + rs2_high + q25_r_hot_screen
    from fpc_contract import BMS_POWER_WIRE_LENGTH_BUDGET_MM
    wire_r = 2 * BMS_POWER_WIRE_LENGTH_BUDGET_MM / 1000 * .030
    checks.append(Check("protected WAGO operating current", DISCHARGE_A,
                        "A", 0, 9, "9A published terminal rating with the specified 18AWG; assembled temperature remains a test"))

    # Only direct input banks go here. Energy drawn by the always-on buck
    # and disabled-rail leakage is covered by the separate 0.8 A startup
    # load envelope, which must be measured through the complete ramp.
    bank = []
    for board, values, rails, returns in (
        ("center", center, {"/VSYS", "/PACK_POS_FUSED"}, {"GND", "/FG_VSS"}),
        ("left", left, {"/VSYS"}, {"GND"}),
        ("right", right, {"/VSYS"}, {"GND"}),
        ("bms", bms, {"/PACK_POS_FUSED"}, {"/FG_VSS", "/PACK_NEG_RAW"}),
    ):
        for ref, nets in values.pins.items():
            if not ref.startswith("C") or ref not in values or values[ref].upper().startswith("DNP"):
                continue
            joined = set(nets.values())
            if joined & rails and joined & returns:
                nominal = values.number(ref)
                high = nominal * (1 + values.tolerance(ref))
                bank.append({"board": board, "ref": ref, "mpn": values.mpn(ref),
                             "nominal_uF": nominal * 1e6, "initial_upper_uF": high * 1e6})
    initial_bank = sum(c["initial_upper_uF"] for c in bank) * 1e-6
    checks.append(Check("direct input bank within startup allocation", initial_bank * 1e6,
                        "uF", 0, STARTUP_CAPACITANCE_F * 1e6,
                        "fresh netlist capacitance plus initial tolerance; installed hot capacitance must also remain within the allocation"))
    startup = startup_metrics(bms)
    # These conditional startup screens use the existing eFuse model. Its
    # coefficients come from other test voltages and need 3S measurements.
    diode_energy_screen = startup["startup_peak_A"] * 1.0 * startup["startup_time_s"]
    for row in checks:
        require(row.passed, row.name)
    return {
        "passed": not failures, "failures": failures,
        "scope": "component sizing and wiring; no operating or fabrication qualification",
        "checks": [{**asdict(c), "passed": c.passed} for c in checks],
        "metrics": {
            "discharge_A": DISCHARGE_A, "charge_A": CHARGE_A,
            "gate_load_at_2V_uA": gate_load * 1e6,
            "gate_bleed_at_5V_uA": 5 / gate_r_low * 1e6,
            "shunt_resistance_temperature_C": [-40, 170],
            "shunt_power_derating_ambient_C": 100,
            "RS1_ohm": [rs1_low, rs1_high], "RS2601_ohm": [rs2_low, rs2_high],
            "Q25_hot_resistance_screen_ohm": q25_r_hot_screen,
            "Q25_loss_screen_W": q25_loss,
            "Q25_required_theta_JA_at_85C_air_for_125C_junction_C_per_W": (125 - 85) / q25_loss,
            "Q25_junction_screen_at_100C_case_C": 100 + q25_loss * 1.5,
            "center_component_drop_at_8A_mV": DISCHARGE_A * component_r * 1000,
            "center_component_loss_at_8A_W": DISCHARGE_A ** 2 * component_r,
            "protected_wire_pair_drop_at_8A_mV": DISCHARGE_A * wire_r * 1000,
            "protected_wire_length_budget_mm_each": BMS_POWER_WIRE_LENGTH_BUDGET_MM,
            "protected_wire_pair_loss_at_8A_W": DISCHARGE_A ** 2 * wire_r,
            "minimum_protected_pack_voltage_for_10V_VSYS_before_contacts_and_copper_V": 10 + DISCHARGE_A * (component_r + wire_r),
            "gauge_differential_range_current_at_shunt_high_A": .125 / rs1_high,
            "startup_allocated_capacitance_uF": STARTUP_CAPACITANCE_F * 1e6,
            "startup_load_allocation_A": STARTUP_LOAD_A,
            "startup_stack_V": STARTUP_STACK_V,
            "startup_initial_bank_uF": initial_bank * 1e6,
            "startup_ramp_screen_ms": startup["startup_time_s"] * 1000,
            "startup_peak_screen_A": startup["startup_peak_A"],
            "Q25_diode_startup_energy_screen_mJ": diode_energy_screen * 1000,
        },
        "startup_direct_bank": bank,
        "not_qualified": [
            "BGATE must reach at least 4.5V above Q25 source before a sustained heavy load; a 2V pump test point does not specify the entire ramp",
            "Q25 hot resistance, installed copper thermal resistance and neighboring heat sources",
            "complete protected loop resistance, including four wire terminations, solder and PCB necks",
            "complete startup input load versus voltage and installed capacitance over temperature",
            "TPS26600 short and startup energy at 3S; thermal latch has no guaranteed maximum fault duration",
            "BMS handoff, fault peak, repeated pulses, fuse clearing and gauge input excursions",
            "cell, raw-pack wiring and operating-profile qualification",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for board in ("center", "left", "right", "bms"):
        ap.add_argument("--" + board, type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    paths = [getattr(args, name) for name in ("center", "left", "right", "bms")]
    result = inspect(*(component_values(path) for path in paths))
    result["netlist_sha256"] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                for name, path in zip(("center", "left", "right", "bms"), paths)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks": len(result["checks"]),
                      "failures": result["failures"]}))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
