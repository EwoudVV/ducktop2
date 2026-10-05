#!/usr/bin/env python3
"""Calculate limits for the BQ76922 and 2 milliohm BMS shunt.

The data-sheet corners below are kept separate from explicit assembly
acceptance allowances. Passing these rows does not release operation, OTP,
cells, routing, thermals, startup SOA, or the storage ECO.
"""

from __future__ import annotations

import json
import math
import datetime as dt
from pathlib import Path

from verify_electrical_calculations import Check, NetlistValues, capacitor, resistor


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "firmware/bq76922/profile.json"

# Reviewed primary-source constants. Assembly acceptance allowances are named
# separately and never promoted to data-sheet guarantees.
SOURCE_URLS = {
    "bq76922": "https://www.ti.com/lit/ds/symlink/bq76922.pdf",
    "bq76922_trm": "https://www.ti.com/lit/ug/sluucg7/sluucg7.pdf",
    "ina381": "https://www.ti.com/lit/ds/symlink/ina381.pdf",
    "ref3425": "https://www.ti.com/lit/ds/symlink/ref34.pdf",
    "tps3808": "https://www.ti.com/lit/ds/symlink/tps3808.pdf",
    "tps26600": "https://www.ti.com/lit/ds/symlink/tps2660.pdf",
    "tps709": "https://www.ti.com/lit/ds/symlink/tps709.pdf",
    "tps22810": "https://www.ti.com/lit/ds/symlink/tps22810.pdf",
    "css4j": "https://www.bourns.com/docs/product-datasheets/css4j-4026.pdf",
}
SHUNT_EXISTING_SCREEN = .050875
SHUNT_ALL_STRESS_SCREEN = .067875
GAIN_ERROR = .012
FILTER_RESISTOR_ACCEPTANCE = .025
FILTER_MISMATCH_ALLOWANCE_V = 25e-6
INA_VOS_V = 150e-6
INA_DRIFT_V_PER_C = 1e-6
INA_PSRR_V_PER_V = 40e-6
INA_SUPPLY_DELTA_V = 2.0
INA_CMRR_DB = 84
INA_COMMON_MODE_BOUND_V = .05
INA_COMPARATOR_OFFSET_V = .005
REF_OUTPUT_V = 2.5
REF_DISCHARGE_ACCEPTANCE = .0065
REF_CHARGE_ACCEPTANCE = .0085
TPS3808_FALLING_V = (2.79 * .985, 2.79 * 1.015)
TPS3808_RISING_V = (TPS3808_FALLING_V[0], TPS3808_FALLING_V[1] * 1.025)
STARTUP_CAPACITANCE_F = 695.3585e-6
STARTUP_LOAD_A = .8
STARTUP_STACK_V = 12.6
TPS26600_ILIM_COEFFICIENT_A_KOHM = 12.0
TPS26600_ILIM_COEFFICIENT_TOL = .05
TPS26600_ILIM_RESISTOR_TOL = .01
TPS26600_DVDT_CURRENT_A = (95e-6, 140.25e-6)
TPS26600_DVDT_CAP_ACCEPTANCE = .055


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _require(values: NetlistValues, expected: dict[str, str]) -> None:
    for ref, mpn in expected.items():
        if values.mpn(ref) != mpn:
            raise ValueError(f"{ref} requires selected {mpn}, got {values.mpn(ref)!r}")


def _parallel(a: float, b: float) -> float:
    return a * b / (a + b)


def _row_bytes(profile: dict) -> dict[str, list[int]]:
    return {row["name"]: row["bytes"] for row in profile["rows"]}


def _word(data: list[int]) -> int:
    return data[0] | data[1] << 8


def trip_envelopes(values: NetlistValues) -> dict:
    """Recalculate signed INA381 and native BQ thresholds from selected parts."""
    _require(values, {
        "U719": "BQ76922RSNR",
        "RS11": "CSS4J-4026K-2L00F",
        "U2210": "INA381A3IDGSR",
        "U2211": "INA381A4IDGSR",
        "U2213": "REF3425IDBVR",
        "R2270": "TNPW060310K2BEEA",
        "R2271": "TNPW060326K7BEEA",
        "R2272": "TNPW060316K9BEEA",
        "R2273": "TNPW060331K6BEEA",
        "R2280": "TNPW06034R99BEEA",
        "R2281": "TNPW06034R99BEEA",
        "R2282": "TNPW06034R99BEEA",
        "R2283": "TNPW06034R99BEEA",
        "C2270": "GRM1885C1H103JA01J",
        "C2271": "GRM1885C1H103JA01J",
    })
    if values.parts["RS11"][1] != "ducktop2:Bourns_CSS4J_4026_Kelvin":
        raise ValueError("RS11 requires the reviewed true-Kelvin footprint")
    shunt = resistor(values, "RS11")
    if not math.isclose(shunt, .002, rel_tol=1e-12):
        raise ValueError("RS11 must be the selected 2 mOhm shunt")
    if not math.isclose(capacitor(values, "C2270"), 10e-9, rel_tol=1e-12):
        raise ValueError("INA381 differential filters require selected 10 nF C0G parts")
    if not math.isclose(capacitor(values, "C2271"), 10e-9, rel_tol=1e-12):
        raise ValueError("INA381 differential filters require selected 10 nF C0G parts")

    filter_r = sum(resistor(values, ref) for ref in ("R2280", "R2281", "R2282", "R2283")) / 4
    guaranteed_offset = (
        INA_VOS_V + INA_DRIFT_V_PER_C * 100
        + INA_PSRR_V_PER_V * INA_SUPPLY_DELTA_V
        + INA_COMMON_MODE_BOUND_V * 10 ** (-INA_CMRR_DB / 20)
    )
    acceptance_offset = guaranteed_offset + FILTER_MISMATCH_ALLOWANCE_V

    vref = REF_OUTPUT_V
    discharge_ref = vref * resistor(values, "R2271") / (resistor(values, "R2270") + resistor(values, "R2271"))
    charge_ref = vref * resistor(values, "R2273") / (resistor(values, "R2272") + resistor(values, "R2273"))

    def one(gain: int, ref: float, ref_e: float,
            shunt_e: float) -> tuple[float, float, float, float]:
        factor = ((lambda r: 1000 / (1000 + r)) if gain == 100
                  else (lambda r: 2500 / (2500 + 3 * r)))
        fmin = factor(filter_r * (1 + FILTER_RESISTOR_ACCEPTANCE))
        fmax = factor(filter_r * (1 - FILTER_RESISTOR_ACCEPTANCE))
        input_lo = ((ref * (1 - ref_e) - INA_COMPARATOR_OFFSET_V)
                    / (gain * (1 + GAIN_ERROR) * fmax) - acceptance_offset)
        input_hi = ((ref * (1 + ref_e) + INA_COMPARATOR_OFFSET_V)
                    / (gain * (1 - GAIN_ERROR) * fmin) + acceptance_offset)
        lo = input_lo / (shunt * (1 + shunt_e))
        hi = input_hi / (shunt * (1 - shunt_e))
        nominal = ref / (gain * factor(filter_r) * shunt)
        return lo, hi, nominal, factor(filter_r)

    d_lo, d_hi, d_nom, d_factor = one(100, discharge_ref, REF_DISCHARGE_ACCEPTANCE,
                                      SHUNT_EXISTING_SCREEN)
    c_lo, c_hi, c_nom, c_factor = one(200, charge_ref, REF_CHARGE_ACCEPTANCE,
                                      SHUNT_EXISTING_SCREEN)
    d_all_lo, d_all_hi, _, _ = one(100, discharge_ref, REF_DISCHARGE_ACCEPTANCE,
                                    SHUNT_ALL_STRESS_SCREEN)
    c_all_lo, c_all_hi, _, _ = one(200, charge_ref, REF_CHARGE_ACCEPTANCE,
                                    SHUNT_ALL_STRESS_SCREEN)
    return {
        "shunt_ohm": (shunt * (1 - SHUNT_EXISTING_SCREEN), shunt * (1 + SHUNT_EXISTING_SCREEN)),
        "shunt_all_stress_ohm": (shunt * (1 - SHUNT_ALL_STRESS_SCREEN),
                                  shunt * (1 + SHUNT_ALL_STRESS_SCREEN)),
        "guaranteed_low_cm_offset_V": guaranteed_offset,
        "acceptance_offset_V": acceptance_offset,
        "discharge_A": (d_lo, d_hi),
        "charge_A_signed": (-c_hi, -c_lo),
        "discharge_all_stress_A": (d_all_lo, d_all_hi),
        "charge_all_stress_A_signed": (-c_all_hi, -c_all_lo),
        "discharge_nominal_A": d_nom,
        "charge_nominal_A_signed": -c_nom,
        "discharge_filter_gain": d_factor,
        "charge_filter_gain": c_factor,
        "discharge_ref_V": discharge_ref,
        "charge_ref_V": charge_ref,
    }


def supply_metrics(values: NetlistValues) -> dict:
    """Selected REGIN, raw thermal, and isolated-control load screens."""
    _require(values, {
        "U708": "TPS70950DBVR",
        "R880": "CRCW2512430RFKEGHP",
        "R881": "CRCW2512430RFKEGHP",
        "U2206": "ISO1640BDR",
        "U2207": "TCA9517AIDGKR",
        "U2209": "ISO7021FDR",
    })
    feed = _parallel(resistor(values, "R880"), resistor(values, "R881"))
    feed_high = feed * 1.05
    raw_pullups = 3.6 / resistor(values, "R2260") + 3.6 / resistor(values, "R2261")
    reg1_selected = 6.7e-3 + raw_pullups + 2 * .45e-3 + .25e-3 + .20e-3 + .12e-3
    reg1_acceptance = 12e-3
    reg_input_at_8v4 = 8.4 - reg1_acceptance * feed_high
    each_short_21_w = 21 ** 2 / (resistor(values, "R880") * .95)

    v = 3.6
    passive = v / resistor(values, "R2201")
    for cell in range(3):
        passive += v / sum(resistor(values, f"R{2210 + 3 * cell + j}") for j in range(3))
    passive += sum(v / (resistor(values, f"R{2240 + 2 * i}") + resistor(values, f"R{2241 + 2 * i}")) for i in range(4))
    passive += sum(v / resistor(values, ref) for ref in ("R2230", "R2231", "R2232", "R2233", "R2235", "R2238"))
    passive += 2 * v / 10000  # both healthy OFF-bias paths, worst normal-state draw
    # TPS22810 enabled IQ is 85uA maximum through105C. Keep it in the
    # operating thermal-feed screen; shutdown current is checked separately.
    thermal_ic = 12 * .85e-6 + 1.2e-6 + .9e-6 + 10e-6 + 10e-6
    if "U2217" in values:
        thermal_ic += 85e-6
    thermal_demand = passive + thermal_ic
    thermal_input_at_8v4 = 8.4 - thermal_demand * resistor(values, "R2200") * 1.05

    ctrl_pullups = sum(3.6 / resistor(values, ref) for ref in ("R2262", "R2263", "R2266", "R2267"))
    isolated_control = 7.1e-3 + 5.0e-3 + 1.5e-3 + ctrl_pullups
    return {
        "regin_feed_ohm": feed,
        "reg1_selected_load_A": reg1_selected,
        "reg1_acceptance_load_A": reg1_acceptance,
        "regin_input_at_8v4_V": reg_input_at_8v4,
        "regin_each_resistor_21V_W": each_short_21_w,
        "thermal_demand_A": thermal_demand,
        "thermal_input_at_8v4_V": thermal_input_at_8v4,
        "isolated_control_load_A": isolated_control,
    }


def startup_metrics(values: NetlistValues) -> dict:
    """TPS26600 selected 8 kOhm/100 nF startup screen."""
    _require(values, {
        "U2218": "TPS26600PWPR",
        "R887": "TNPW060312K0BEEN",
        "R888": "TNPW060324K0BEEN",
        "C882": "C1206C104F3GECAUTO",
    })
    ilim = _parallel(resistor(values, "R887"), resistor(values, "R888"))
    if not math.isclose(ilim, 8000, rel_tol=1e-12):
        raise ValueError("TPS26600 ILIM must be the selected 12 kOhm || 24 kOhm = 8 kOhm")
    cdvdt = capacitor(values, "C882")
    if not math.isclose(cdvdt, 100e-9, rel_tol=1e-12):
        raise ValueError("TPS26600 dVdt must be selected 100 nF C0G")
    low = (TPS26600_ILIM_COEFFICIENT_A_KOHM * (1 - TPS26600_ILIM_COEFFICIENT_TOL)
           / (ilim / 1000 * (1 + TPS26600_ILIM_RESISTOR_TOL)))
    high = (TPS26600_ILIM_COEFFICIENT_A_KOHM * (1 + TPS26600_ILIM_COEFFICIENT_TOL)
            / (ilim / 1000 * (1 - TPS26600_ILIM_RESISTOR_TOL)))
    slew_low = TPS26600_DVDT_CURRENT_A[0] / (cdvdt * (1 + TPS26600_DVDT_CAP_ACCEPTANCE))
    slew_high = TPS26600_DVDT_CURRENT_A[1] / (cdvdt * (1 - TPS26600_DVDT_CAP_ACCEPTANCE))
    slew_time = STARTUP_STACK_V / slew_low
    current_time = STARTUP_CAPACITANCE_F * STARTUP_STACK_V / (low - STARTUP_LOAD_A)
    time_max = max(slew_time, current_time)
    peak = STARTUP_LOAD_A + STARTUP_CAPACITANCE_F * slew_high
    stored = .5 * STARTUP_CAPACITANCE_F * STARTUP_STACK_V ** 2
    load_loss = .5 * STARTUP_STACK_V * STARTUP_LOAD_A * time_max
    return {
        "ilim_ohm": ilim,
        "current_A": (low, high),
        "cdvdt_F": cdvdt,
        "slew_V_per_s": (slew_low, slew_high),
        "startup_time_s": time_max,
        "startup_peak_A": peak,
        "ramp_loss_J": stored + load_loss,
        "timer_status": "thermal latch; no guaranteed maximum fault time or energy in TPS26600 data sheet",
    }


def optional_storage_checks(values: NetlistValues) -> list[Check]:
    if "U2217" not in values:
        return []
    _require(values, {
        "U2217": "TPS22810DBVR",
        "R2290": "RC0603FR-07390KL",
        "C2281": "GRM21BR71H105KA12L",
        "U2208": "SN74LVC1G17DBVR",
    })
    return [
        Check("optional storage-switch EN high margin", 1.6 - 1.3, "V", .25, math.inf,
              "[guaranteed table] REG18 minimum minus TPS22810 maximum EN rising threshold"),
        Check("optional storage-switch shutdown EN leakage screen",
              (1.0e-6 + .1e-6) * resistor(values, "R2290") * 1.05, "V", 0, .5,
              "[required assembly acceptance] published BQ input-mode leakage plus TPS22810 EN leakage; output-mode SHUTDOWN voltage must be measured"),
        Check("optional storage-switch input capacitance", capacitor(values, "C2281") * 1e6,
              "uF", .9, 1.1,
              "[selected component] nominal capacitor only; effective bias/temperature value remains an assembly check"),
    ]


def charge_voltage_metrics(profile: dict) -> dict:
    rows = _row_bytes(profile)
    a = profile["admission"]
    cov_low = rows["COV Threshold"][0] * .0506 - .025
    cv = a["charge_voltage_mv"] / 1000
    error = a["cell_voltage_error_mv"] / 1000
    spread = a["charge_spread_max_mv"] / 1000
    return {
        "cov_low_V": cov_low,
        "cov_high_V": rows["COV Threshold"][0] * .0506 + .025,
        "charger_high_pack_V": cv * 1.005,
        "highest_static_cell_V": cv * 1.005 / 3 + (2/3) * (spread + 2*error),
        "minimum_cov_margin_V": cov_low - (cv * 1.005 / 3 + (2/3) * (spread + 2*error)),
        "charge_ceiling_rise_room_V": cov_low - a["charge_cell_max_mv"] / 1000 - error,
        "taper_min_measured_cell_V": cv * .995 / 3 - error - (2/3) * spread,
        "taper_min_measured_sum_V": cv * .995 - 3*error,
    }


def bq76922_checks(values: NetlistValues, profile_path: Path = PROFILE) -> list[Check]:
    profile = _load(profile_path)
    rows = _row_bytes(profile)
    if profile["part"] != "BQ76922RSNR" or values.mpn("U719") != "BQ76922RSNR":
        raise ValueError("BQ76922 calculation path requires selected U719/profile")
    if profile["released_for_assembly"]:
        raise ValueError("numeric screen must not silently promote an operating release")

    for key in ("cell_voltage_qualified", "charge_voltage_qualified", "termination_qualified"):
        if profile.get(key) is not False:
            raise ValueError("numeric screen cannot qualify charge measurements: " + key)
    charge = charge_voltage_metrics(profile)
    trip = trip_envelopes(values)
    supply = supply_metrics(values)
    startup = startup_metrics(values)
    checks = [
        Check("BQ76922 shunt 8A component loss", 64 * trip["shunt_ohm"][1], "W", 0, 6,
              "[guaranteed component table plus explicit stress screen] 8A^2*RS11(high); installed terminal temperature still requires measurement"),
        Check("INA381 discharge nominal signed trip", trip["discharge_nominal_A"], "A", 8.8, 9.3,
              "[selected values] +current through 2m shunt, gain100 and actual reference/filter values"),
        Check("INA381 discharge acceptance floor", trip["discharge_A"][0], "A", 8.1, math.inf,
              "[required assembly acceptance] guaranteed IC terms plus 25uV filter-mismatch allowance and 5.0875% shunt stress screen"),
        Check("INA381 discharge acceptance ceiling", trip["discharge_A"][1], "A", 0, 10.2,
              "[required assembly acceptance] must be measured; this is not an 8A clamp"),
        Check("INA381 charge nominal signed trip", trip["charge_nominal_A_signed"], "A", -4.3, -3.9,
              "[selected values] negative shunt polarity, gain200 and actual reference/filter values"),
        Check("INA381 charge acceptance magnitude floor", -trip["charge_A_signed"][1], "A", 3.2, math.inf,
              "[required assembly acceptance] signed negative-current envelope"),
        Check("INA381 charge acceptance magnitude ceiling", -trip["charge_A_signed"][0], "A", 0, 4.8,
              "[required assembly acceptance] measured transfer still required"),
        Check("INA381 discharge all-stress floor", trip["discharge_all_stress_A"][0], "A", 8.1, math.inf,
              "[conservative acceptance] every published shunt stress applied once gives only a small margin above8A"),
        Check("INA381 discharge all-stress ceiling", trip["discharge_all_stress_A"][1], "A", 0, 10.3,
              "[conservative acceptance] 6.7875% shunt envelope; not a cumulative lifetime guarantee"),
        Check("INA381 charge all-stress magnitude floor", -trip["charge_all_stress_A_signed"][1], "A", 3.2, math.inf,
              "[conservative acceptance] 6.7875% shunt envelope remains above3A"),
        Check("INA381 charge all-stress magnitude ceiling", -trip["charge_all_stress_A_signed"][0], "A", 0, 4.8,
              "[conservative acceptance] every published shunt stress applied once"),
        Check("8A objective all-stress static margin", trip["discharge_all_stress_A"][0] - 8,
              "A", .15, math.inf, "[conservative acceptance] calibration, ripple and startup must fit inside this remaining margin"),
        Check("INA381 guaranteed low-common-mode offset screen", trip["guaranteed_low_cm_offset_V"] * 1e6,
              "uV", 0, 340, "[guaranteed tables] Vos, drift, PSRR and 84dB CMRR at bounded 50mV common mode"),
        Check("INA381 total offset acceptance allowance", trip["acceptance_offset_V"] * 1e6,
              "uV", 0, 360, "[required assembly acceptance] adds 25uV for typical-only input/filter mismatch"),
        Check("REG1 guaranteed low rail", 3.0, "V", 3.0, 3.6,
              "[BQ76922 table] REGIN>=4.1V and load<=45mA"),
        Check("REG1 guaranteed high rail", 3.6, "V", 3.0, 3.6,
              "[BQ76922 table] full selected 3.3V output range"),
        Check("TPS3808 maximum release threshold", TPS3808_RISING_V[1],
              "V", 0, 3.0, "[guaranteed table] 2.79V threshold tolerance plus maximum hysteresis"),
        Check("TPS3808 minimum falling threshold", TPS3808_FALLING_V[0],
              "V", 2.7, math.inf, "[guaranteed table] INA381 remains inside its supply range before CURRENT_READY falls"),
        Check("REF3425 selected nominal output capacitance",
              (capacitor(values, "C2273") + capacitor(values, "C2280")) * 1e6,
              "uF", .1, 10, "[guaranteed stability table] nominal parallel output capacitors; effective 0.1..10uF across bias/temp is an assembly acceptance test"),
        Check("external REGIN selected-load screen", supply["reg1_selected_load_A"] * 1000,
              "mA", 0, 12, "[selected parts] ISO1640, raw pullups, two INA381s, reference/dividers and alarm-interface allowances"),
        Check("external REGIN minimum input at 8.4V", supply["regin_input_at_8v4_V"],
              "V", 5.5, 8.4, "[required assembly acceptance] 12mA allocation through 2x430R with 5% resistance screen; TPS70950 dropout/dynamics require measurement"),
        Check("each 430R REGIN resistor 21V short screen", supply["regin_each_resistor_21V_W"],
              "W", 0, 1.2, "[required fault screen] each selected 1.5W part; 21V is not an allowed pack operating voltage"),
        Check("raw thermal maximum-demand input at 8.4V", supply["thermal_input_at_8v4_V"],
              "V", 4.6, 8.4, "[required assembly acceptance] actual divider/pull loads and data-sheet IC maxima through R2200; thermal rail is separate from REGIN"),
        Check("isolated control-domain load screen", supply["isolated_control_load_A"] * 1000,
              "mA", 0, 21, "[required harness acceptance] ISO1640, TCA9517A, ISO7021 and four actual 2.2k pullups; measure bus duty/capacitance"),
        Check("TPS26600 selected ILIM low", startup["current_A"][0], "A", 1.40, 1.50,
              "[guaranteed table] 12A*kOhm coefficient +/-5% with selected 8k network +/-1%"),
        Check("TPS26600 selected ILIM high", startup["current_A"][1], "A", 1.50, 1.60,
              "[guaranteed table] current-limit pin screen, not a guaranteed fault-energy timeout"),
        Check("TPS26600 startup slew high", startup["slew_V_per_s"][1], "V/s", 0, 1500,
              "[required assembly acceptance] selected 100n C0G, reviewed dVdt-source bounds and explicit 5.5% capacitor envelope"),
        Check("TPS26600 startup current peak screen", startup["startup_peak_A"], "A", 0, 1.85,
              "[required assembly acceptance] 0.8A unmeasured load plus worst dV/dt charging current"),
        Check("TPS26600 startup ramp-loss screen", startup["ramp_loss_J"], "J", 0, .13,
              "[required assembly acceptance] no guaranteed thermal-latch timeout; scope hot startup and short"),
    ]

    cuv_code = rows["CUV Threshold"][0]
    cov_code = rows["COV Threshold"][0]
    cuv = cuv_code * .0506
    cov = cov_code * .0506
    cov_recover = cov - rows["COV Recovery Hysteresis"][0] * .0506
    checks.extend([
        Check("profile ALERT awake configuration", rows["ALERT Pin Config"][0], "code", 0x8A, 0x8A,
              "[actual profile] active-low ALERT, REG18 high drive, strong deasserted high"),
        Check("profile alarm mask for awake-only pin", _word(rows["Default Alarm Mask"]), "mask", 0, 0,
              "[actual profile] ordinary faults stay in fresh I2C status and cannot remove thermal power"),
        Check("profile enabled protections C", rows["Enabled Protections C"][0], "code", 0x60, 0x60,
              "[actual profile] selected C protection bits; directional recovery remains a firmware policy"),
        Check("profile CUV threshold", cuv, "V/cell", 3.0, 3.1,
              "[actual profile] code*50.6mV; directionally blocks discharge, not recovery charge"),
        Check("profile COV threshold", cov, "V/cell", 4.1, 4.2,
              "[actual profile] code*50.6mV; directionally blocks charge"),
        Check("profile COV recovery level", cov_recover, "V/cell", 3.95, 4.05,
              "[actual profile] COV minus hysteresis; bounded discharge recovery must remain possible"),
        Check("native OCD backup floor", (.022 - .004) / trip["shunt_ohm"][1],
              "A", 8.2, math.inf, "[BQ guaranteed threshold table plus shunt screen] profile code11=22mV backup above 8A target"),
        Check("native OCC backup floor", (.014 - .002) / trip["shunt_ohm"][1],
              "A", 3.2, math.inf, "[BQ guaranteed threshold table plus shunt screen] profile code7=14mV backup above 3A target"),
        Check("native SCD backup floor", .040 * .85 / trip["shunt_ohm"][1],
              "A", 15, math.inf, "[BQ guaranteed threshold table plus shunt screen] profile code2=40mV fast backstop"),
        Check("native OCD all-stress floor", (.022 - .004) / trip["shunt_all_stress_ohm"][1],
              "A", 8.2, math.inf, "[conservative acceptance] native backup with 6.7875% shunt envelope"),
        Check("native OCC all-stress floor", (.014 - .002) / trip["shunt_all_stress_ohm"][1],
              "A", 3.2, math.inf, "[conservative acceptance] native backup with 6.7875% shunt envelope"),
        Check("native SCD all-stress floor", .040 * .85 / trip["shunt_all_stress_ohm"][1],
              "A", 15, math.inf, "[conservative acceptance] native fast backup with 6.7875% shunt envelope"),
        Check("operation release remains disabled", float(profile["released_for_assembly"]), "bool", 0, 0,
              "Passing numeric rows does not qualify operation, OTP, cells, routing, thermals, startup SOA or storage behavior"),
    ])
    a = profile["admission"]
    host = profile["host_charge"]
    checks.extend([
        Check("profile BQ-specific CV target", a["charge_voltage_mv"], "mV", 12120, 12120,
              "[actual profile] exact 8 mV code; legacy 12.528 V does not apply to this monitor"),
        Check("profile charge-only cell ceiling", a["charge_cell_max_mv"], "mV", 4100, 4100,
              "[actual profile] bounded discharge retains its separate 4200 mV ceiling"),
        Check("profile measured cell spread", a["charge_spread_max_mv"], "mV", 30, 30,
              "[calibrated-data requirement] individual cells, not stack or gauge voltage"),
        Check("calibrated cell error allocation", a["cell_voltage_error_mv"], "mV", 15, 15,
              "[TI guaranteed table after board-offset calibration] full-temperature cell measurement error"),
        Check("COV late-corner ceiling", charge["cov_high_V"], "V/cell", 4.1, 4.2,
              "[TI guaranteed table] code*50.6mV+25mV must stay below selected 4.20 V"),
        Check("CV/imbalance minimum COV margin", charge["minimum_cov_margin_V"]*1000, "mV", 23.9, math.inf,
              "[required charger qualification] CV*1.005/3+2/3*(measured spread+2*15mV) below COVlow"),
        Check("charge ceiling response headroom", charge["charge_ceiling_rise_room_V"]*1000, "mV", 9, math.inf,
              "[required response qualification] COVlow minus 4100 mV measured ceiling and 15 mV error"),
        Check("unreleased charge response bound", a["charge_max_rise_mv"], "mV", 0, 9,
              "[unqualified placeholder] zero denies runtime charge; measured 1..9 mV is required before release"),
        Check("taper cell floor reachable at low CV corner", charge["taper_min_measured_cell_V"]*1000,
              "mV", host["taper_cell_min_mv"], math.inf,
              "[static corner] CV*.995/3-15mV-2/3*30mV; timing/current still need qualification"),
        Check("taper sum floor reachable at low CV corner", charge["taper_min_measured_sum_V"]*1000,
              "mV", host["taper_cell_sum_min_mv"], math.inf,
              "[static corner] CV*.995-3*15mV, using individual cells"),
        Check("host taper debounce", host["taper_hold_ms"], "ms", 30000, 30000,
              "[prototype criterion] continuous CV and bounded 200 mA taper; not a qualified cell termination rating"),
        Check("host cumulative qualified CV dwell", host["cv_dwell_max_ms"], "ms", 7200000, 7200000,
              "[prototype criterion] accumulated fresh enabled CV only; bulk and interruptions do not spend or reset this budget"),
        Check("host recharge ceiling", host["recharge_cell_max_mv"], "mV", 3950, 3950,
              "[prototype criterion] every cell at or below this value for 5 s; normal 3100 mV floor remains"),
    ])
    checks.extend(optional_storage_checks(values))
    return checks


def render_bq76922_report(checks: list[Check], netlist: Path) -> str:
    failures = [check for check in checks if not check.passed]
    lines = [
        "# Ducktop2 BQ76922 Candidate Calculations",
        "",
        f"Generated: {dt.date.today().isoformat()}",
        "",
        "Values come from the selected KiCad XML netlist. Passing rows are numeric screens, not an operating release.",
        "",
        "| Check | Result | Required band | Status | Basis |",
        "|---|---:|---:|:---:|---|",
    ]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(
            f"| {check.name} | {check.value:.4g} {check.unit} | "
            f"{check.low:.4g} to {check.high:.4g} {check.unit} | {status} | {check.equation} |"
        )
    lines.extend([
        "",
        f"Result: **{len(checks) - len(failures)} PASS, {len(failures)} FAIL**.",
        "",
        "## Qualification boundary",
        "",
        "- Guaranteed table limits are labeled separately from assembly acceptance allowances.",
        "- INA381 filter mismatch, shunt stress accumulation, effective capacitance, harness load, startup loss, and storage shutdown voltage require physical acceptance tests.",
        "- COV, CUV, overcurrent, and temperature recovery decisions are directional. A numeric threshold pass does not authorize both current directions.",
        "- TPS26600 thermal latch behavior has no guaranteed maximum fault time or energy in the data sheet.",
        "- operation, OTP, cells, routing, thermals, calibration, startup SOA and storage current remain unreleased.",
        "- the lower CV target has a qualified host taper/recharge latch. cell offsets, low-current transfer and the complete sensing-to-inhibit rise remain unqualified.",
        "",
        "## Primary sources",
        "",
        f"- TI BQ76922 data sheet SLUSE86A: {SOURCE_URLS['bq76922']}",
        f"- TI BQ76922 TRM SLUUCG7: {SOURCE_URLS['bq76922_trm']}",
        f"- TI INA381 data sheet SBOS848: {SOURCE_URLS['ina381']}",
        f"- TI REF3425 data sheet SBAS804: {SOURCE_URLS['ref3425']}",
        f"- TI TPS3808 data sheet SBVS050: {SOURCE_URLS['tps3808']}",
        f"- TI TPS26600 data sheet SLVSDG2: {SOURCE_URLS['tps26600']}",
        f"- TI TPS709 data sheet SBVS186: {SOURCE_URLS['tps709']}",
        f"- TI TPS22810 data sheet SLVSDH0: {SOURCE_URLS['tps22810']}",
        f"- Bourns CSS4J-4026 data sheet: {SOURCE_URLS['css4j']}",
        "- Reviewed numeric constants and official source URLs embedded in gen/verify_bq76922_calculations.py",
        "",
        f"BMS netlist evidence: `{netlist}`",
        "",
    ])
    return "\n".join(lines)


__all__ = ["bq76922_checks", "optional_storage_checks", "render_bq76922_report",
           "startup_metrics", "supply_metrics", "trip_envelopes"]
