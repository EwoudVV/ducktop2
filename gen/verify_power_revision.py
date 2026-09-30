#!/usr/bin/env python3
"""Check the 100 W power topology against native netlists and reviewed pin maps."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from part_identity import identity_errors
from verify_electrical_calculations import component_values

P = "/Power & Battery/"
M = "/Mu Carrier/"
E = "/EC & MCU/"


def check(center, left=None, right=None):
    failures = []
    expected_pins = {}
    count = 0

    def pins(v, ref, expected):
        nonlocal count
        if v is center:
            expected_pins.setdefault(ref, {}).update(
                {str(k): n for k, n in expected.items()}
            )
        for pin, want in expected.items():
            count += 1
            got = v.pins.get(ref, {}).get(str(pin))
            good = (
                got == want
                if want is not None
                else bool(got and got.startswith("unconnected-"))
            )
            if not good:
                failures.append(f"{ref}.{pin}: expected {want}, got {got}")

    def mpn(v, ref, want):
        nonlocal count
        count += 1
        if v.mpn(ref) != want:
            failures.append(f"{ref}: expected {want}, got {v.mpn(ref)}")

    def footprint(v, ref, want):
        nonlocal count
        count += 1
        got = v.parts.get(ref, ("", ""))[1]
        if got != want:
            failures.append(f"{ref}: expected footprint {want}, got {got}")

    def pair(v, ref, first, second):
        pins(v, ref, {1: first, 2: second})

    def fet(v, ref, source, gate, drain):
        pins(v, ref, {1: source, 2: source, 3: source, 4: gate, 5: drain})

    def bypass(v, ref, rail, want_mpn):
        nonlocal count
        pair(v, ref, rail, "GND")
        mpn(v, ref, want_mpn)
        footprint(v, ref, "Capacitor_SMD:C_0603_1608Metric")
        count += 1
        value = v.get(ref, "")
        errors = identity_errors(value, v.parts.get(ref, ("", ""))[1], v.mpn(ref))
        if value.lstrip().upper().startswith("DNP"):
            errors.append("local bypass must be fitted")
        if errors:
            failures.append(f"{ref}: " + "; ".join(errors))

    mpn(center, "U2", "ISL9241IRTZ")
    # Renesas FN8945 rev 6.00, Table 1; NVDC-only connections.
    pins(
        center,
        "U2",
        {
            1: P + "CHG_SRN",
            2: "/VSYS",
            3: None,
            4: P + "BTST2_NODE",
            5: P + "CHG_HS2_DRV",
            6: P + "SW2",
            7: P + "CHG_LS2_DRV",
            8: P + "CHG_VDDP",
            9: P + "CHG_LS1_DRV",
            10: P + "SW1",
            11: P + "CHG_HS1_DRV",
            12: P + "BTST1_NODE",
            13: P + "CHG_VDDP",
            14: P + "CHG_INPUT",
            15: P + "CHG_CSIP",
            16: None,
            17: P + "CHG_DCIN",
            18: P + "REGN",
            19: P + "PROG_SET",
            20: "GND",
            21: "/I2C_SDA",
            22: "/I2C_SCL",
            23: "/MU_PROCHOT_N",
            24: P + "CHG_ACOK",
            25: P + "CHG_NTC",
            26: "/CHG_INT_N",
            27: P + "CHG_COMPR",
            28: P + "CHG_COMPF",
            29: P + "CHG_IMON",
            30: P + "CHG_PSYS",
            31: P + "BATP_SENSE",
            32: P + "CHG_BGATE",
            33: "GND",
        },
    )
    for ref, source, gate, drain in (
        ("Q2600", P + "SW1", P + "CHG_HS1_GATE", P + "CHG_INPUT"),
        ("Q2601", "GND", P + "CHG_LS1_GATE", P + "SW1"),
        ("Q2602", "GND", P + "CHG_LS2_GATE", P + "SW2"),
        ("Q2603", P + "SW2", P + "CHG_HS2_GATE", "/VSYS"),
    ):
        fet(center, ref, source, gate, drain)
    # TI's CSD17577Q3A uses DNH. A generic 3.3 mm SON association can have
    # different exposed-drain geometry even when its logical pin map matches.
    for ref in ("Q2600", "Q2601", "Q2602", "Q2603", "Q2610", "Q2611"):
        mpn(center, ref, "CSD17577Q3A")
        footprint(center, ref, "ducktop2:CSD17577Q3A_DNH")
    fet(center, "Q25", "/PACK_POS_FUSED", P + "CHG_BGATE", P + "CHG_SRN")
    pair(center, "L1", P + "SW1", P + "SW2")
    pair(center, "RS2600", P + "VBUS_COMBINED", P + "CHG_INPUT")
    pair(center, "RS2601", "/VSYS", P + "CHG_SRN")
    mpn(center, "RS2600", "WSL2512R0200FEA18")
    mpn(center, "RS2601", "WSLP2512R0100FEA")
    mpn(center, "R18", "TNPW04022K21BEED")
    pair(center, "R18", P + "PROG_SET", "GND")
    pair(center, "R2607", P + "VBUS_COMBINED", P + "CHG_CSIP")
    pair(center, "C2603", P + "CHG_CSIP", P + "CHG_INPUT")
    pair(center, "C2604", "/VSYS", P + "CHG_SRN")
    pair(center, "C7", P + "BTST1_NODE", P + "SW1")
    pair(center, "C8", P + "BTST2_NODE", P + "SW2")
    pair(center, "C9", P + "REGN", "GND")
    pair(center, "R2602", P + "REGN", P + "CHG_VDDP")
    pair(center, "C2601", P + "CHG_VDDP", "GND")
    for ref, source in [("D2600", P + "CHG_INPUT"), ("D2601", "/VSYS")]:
        pair(center, ref, P + "CHG_BIAS_OR", source)
    pair(center, "R2601", P + "CHG_BIAS_OR", P + "CHG_DCIN")
    for ref, source in [
        ("C2600", P + "CHG_DCIN"),
        ("C701", P + "CHG_INPUT"),
        ("C702", P + "CHG_INPUT"),
        ("C703", P + "CHG_INPUT"),
        ("C704", P + "CHG_INPUT"),
        ("C705", P + "CHG_INPUT"),
        ("C706", "/VSYS"),
        ("C707", "/VSYS"),
        ("C708", "/VSYS"),
        ("C709", "/VSYS"),
        ("C710", "/VSYS"),
        ("C2608", "/VSYS"),
        ("C2609", "/VSYS"),
        ("C712", "/PACK_POS_FUSED"),
        ("C713", "/PACK_POS_FUSED"),
    ]:
        pair(center, ref, source, "GND")
    for ref, first, second in (
        ("R704", "/PACK_POS_FUSED", P + "BATP_SENSE"),
        ("C711", P + "BATP_SENSE", "GND"),
        ("R2608", P + "CHG_COMPF", P + "CHG_COMPF_RC"),
        ("C2605", P + "CHG_COMPF_RC", "GND"),
        ("R2609", P + "CHG_COMPR", P + "CHG_COMPR_RC"),
        ("C2606", P + "CHG_COMPR_RC", "GND"),
        ("R2611", P + "CHG_PSYS", "GND"),
        ("R14", P + "REGN", P + "CHG_NTC_HOT_GATE"),
        ("R16", P + "CHG_NTC", "GND"),
        ("R719", "/CHG_ENABLE", "GND"),
        ("R2612", P + "REGN", P + "CHG_THROTTLE_GATE"),
        ("R13", "/MU_PROCHOT_RELEASE", "GND"),
    ):
        pair(center, ref, first, second)
    pins(center, "Q700", {1: P + "CHG_NTC_HOT_GATE", 2: "GND", 3: P + "CHG_NTC"})
    pins(
        center, "Q702", {1: P + "CHG_ENABLE_THERM", 2: "GND", 3: P + "CHG_NTC_HOT_GATE"}
    )
    pins(
        center,
        "U2210",
        {
            1: "/CHG_ENABLE",
            2: P + "PACK_CHG_TEMP_OK_IN",
            3: "GND",
            4: P + "CHG_ENABLE_THERM",
            5: "/MCU_3V3",
        },
    )
    pins(center, "Q2604", {1: P + "CHG_THROTTLE_GATE", 2: "GND", 3: "/MU_PROCHOT_N"})
    pins(
        center,
        "Q2605",
        {1: "/MU_PROCHOT_RELEASE", 2: "GND", 3: P + "CHG_THROTTLE_GATE"},
    )
    pins(center, "A1", {117: "/MU_PROCHOT_N"})
    pins(center, "U4", {26: "/MU_PROCHOT_RELEASE"})
    pins(center, "U12", {12: P+"AUX_EFUSE_SHDN"})
    pins(
        center,
        "U2634",
        {
            1: P + "CHG_BIAS_GOOD",
            2: "GND",
            3: P + "CHG_BIAS_SENSE",
            4: "GND",
            5: "/MCU_3V3",
            6: None,
        },
    )
    pins(
        center,
        "U2635",
        {
            1: P + "AUX_PATH_EN",
            2: P + "CHG_BIAS_GOOD",
            3: P + "PACK_CHG_TEMP_OK_IN",
            4: "/MU_PROCHOT_N",
            5: "GND",
            6: "/NRST_NET",
            7: None,
            8: "/I2C_SCL",
            9: "/I2C_SDA",
            10: "/MCU_3V3",
        },
    )
    mpn(center, "U5", "TPS62933DRLR")
    pins(
        center,
        "U5",
        {
            1: None,
            2: None,
            3: "/EC_AON_IN",
            4: "GND",
            5: E + "BUCK_SW",
            6: E + "BUCK_BOOT",
            7: E + "AON_BUCK_SS",
            8: E + "BUCK_FB",
        },
    )
    mpn(center, "U750", "TPS552882RPMR")
    pins(
        center,
        "U750",
        {
            1: M + "MU12_LS_DRV",
            2: M + "MU12_HS_DRV",
            3: "/VSYS",
            4: M + "MU12_EN_UVLO",
            5: "/MU_12V_PG",
            6: M + "MU12_CC_N",
            7: M + "MU12_DITH",
            8: M + "MU12_FSW",
            9: "GND",
            10: "GND",
            11: M + "MU12_PRE_SENSE",
            12: M + "MU12_ISP",
            13: M + "MU12_ISN",
            14: M + "MU12_FB",
            15: M + "MU12_MODE",
            16: None,
            17: M + "MU12_ILIM",
            18: M + "MU12_COMP",
            19: M + "MU12_VCC",
            20: M + "MU12_BOOT2",
            21: M + "MU12_SW2",
            22: M + "MU12_BOOT1",
            23: M + "MU12_SW1",
            24: "GND",
            25: M + "MU12_SW2",
            26: M + "MU12_PRE_SENSE",
        },
    )
    fet(center, "Q2610", M + "MU12_SW1", M + "MU12_HS_GATE", "/VSYS")
    fet(center, "Q2611", "GND", M + "MU12_LS_GATE", M + "MU12_SW1")
    pair(center, "L750", M + "MU12_SW1", M + "MU12_SW2")
    pair(center, "RS750", M + "MU12_PRE_SENSE", "/MU_12V")
    mpn(center, "RS750", "ERJ8CWFR016V")
    mpn(center, "RS2670", "ERJ8CWFR016V")
    pair(center, "RS2670", M+"MU12_PRE_SENSE", "/MU_12V")
    pair(center, "C2670", M+"MU12_VCC", "GND")
    for ref, a, b in (
        ("R2600", P + "CHG_BGATE", "/PACK_POS_FUSED"),
        ("C2602", P + "PROG_SET", "GND"),
        ("R2610", P + "CHG_IMON", P + "CHG_IMON_FILTER"),
        ("C2607", P + "CHG_IMON_FILTER", "GND"),
        ("R12", P + "REGN", P + "STAT_LED_A"),
        ("LED1", P + "CHG_ACOK", P + "STAT_LED_A"),
        ("C10", P + "CHG_INPUT", "GND"),
        ("C11", "/VSYS", "GND"),
        ("R2260", "/PACK_CHG_TEMP_OK", P + "PACK_CHG_TEMP_OK_IN"),
        ("R2261", P + "PACK_CHG_TEMP_OK_IN", "GND"),
        ("R2262", P + "CHG_ENABLE_THERM", "GND"),
        ("R2263", "/PACK_FAULT_N", "GND"),
        ("C2260", "/MCU_3V3", "GND"),
        ("R2640", P + "REGN", P + "CHG_BIAS_SENSE"),
        ("R2641", P + "CHG_BIAS_SENSE", "GND"),
        ("R2642", "/MCU_3V3", P + "CHG_BIAS_GOOD"),
        ("R2643", "/MU_PROCHOT_N", "GND"),
        ("R2644", P + "AUX_PATH_EN", P + "AUX_EFUSE_SHDN"),
        ("R2645", P + "AUX_EFUSE_SHDN", "GND"),
        ("R2646", P + "AUX_DC_PROTECTED", P + "AUX_DISCHARGE_DRAIN"),
        ("R2647", P + "AUX_DISCHARGE", "GND"),
        ("C2641", "/MCU_3V3", "GND"),
        ("C2642", "/MCU_3V3", "GND"),
        ("C2643", "/MCU_3V3", "GND"),
        ("C2640", E + "AON_BUCK_SS", "GND"),
        ("L3", E + "BUCK_SW", "/MCU_3V3"),
        ("R35", "/MCU_3V3", E + "BUCK_FB"),
        ("R36", E + "BUCK_FB", "GND"),
        ("C36", "/EC_AON_IN", "GND"),
        ("C37", "/EC_AON_IN", "GND"),
        ("C38", E + "BUCK_BOOT", E + "BUCK_SW"),
        ("C39", "/MCU_3V3", "GND"),
        ("C291", "/MCU_3V3", "GND"),
        ("R2613", M + "MU12_HS_DRV", M + "MU12_HS_GATE"),
        ("R2614", M + "MU12_LS_DRV", M + "MU12_LS_GATE"),
        ("C2610", M + "MU12_PRE_SENSE", "GND"),
        ("R755", M + "MU12_COMP", M + "MU12_COMP_RC"),
        ("C771", M + "MU12_COMP_RC", "GND"),
        ("C772", M + "MU12_COMP", "GND"),
        ("R757", M + "MU12_MODE", "GND"),
        ("R758", M + "MU12_ILIM", "GND"),
    ):
        pair(center, ref, a, b)
    for i, (driver, gate) in enumerate(
        (
            ("CHG_HS1_DRV", "CHG_HS1_GATE"),
            ("CHG_LS1_DRV", "CHG_LS1_GATE"),
            ("CHG_LS2_DRV", "CHG_LS2_GATE"),
            ("CHG_HS2_DRV", "CHG_HS2_GATE"),
        )
    ):
        pair(center, "R" + str(2603 + i), P + driver, P + gate)
    pins(
        center,
        "U2644",
        {
            1: None,
            2: P + "AUX_PATH_EN",
            3: "GND",
            4: P + "AUX_DISCHARGE",
            5: "/MCU_3V3",
        },
    )
    pins(
        center,
        "Q2644",
        {1: P + "AUX_DISCHARGE", 2: "GND", 3: P + "AUX_DISCHARGE_DRAIN"},
    )
    pins(center, "D2640", {1: "GND", 2: "/MCU_3V3", 3: "/AUX_DC_ADC"})
    # These checks establish the local-bypass circuit and procurement identity,
    # not physical loop length or effective capacitance under DC bias.
    # TPS22975 SLVSDD0B 10.1.2; TPS2553 SLVS841F 10.2.1.2.4;
    # SN74LVC1G08 SCES217AA 8.3/8.4.
    # LTC4418 Rev A figures 7/8: each selector needs its own local input bypass.
    bypass(center, "C2685", P + "SEL_STAGE2", "GRM188R71H104KA93D")
    bypass(center, "C740", P + "MAIN_SEL_INTVCC", "GRM188R71H104KA93D")
    bypass(center, "C749", P + "ST2_SEL_INTVCC", "GRM188R71H104KA93D")
    pins(center, "U15", {8: "GND", 10: P + "MAIN_SEL_INTVCC", 16: P + "SEL_STAGE2", 21: "GND"})
    pins(center, "U16", {8: "GND", 10: P + "ST2_SEL_INTVCC", 21: "GND"})
    if right is not None:
        bypass(right, "C2680", "/SYS_3V3", "GRT188R61H105ME13D")
        mpn(right, "U55", "TPS22975NDSGR")
        pins(right, "U55", {1: "/SYS_3V3", 2: "/SYS_3V3",
                             4: "/SYS_3V3", 5: "GND", 9: "GND"})
        bypass(right, "C2681", "/SYS_3V3", "GRM188R71H104KA93D")
        mpn(right, "U2016", "SN74LVC1G08DBVR")
        pins(right, "U2016", {5: "/SYS_3V3", 3: "GND"})
    if left is not None:
        bypass(left, "C2682", "/SYS_3V3", "GRM188R71H104KA93D")
        mpn(left, "U2006", "SN74LVC1G08DBVR")
        pins(left, "U2006", {5: "/SYS_3V3", 3: "GND"})
        for capacitor, switch in (("C2683", "U1800"), ("C2684", "U1803")):
            bypass(left, capacitor, "/USB_PORT_5V", "GRT188R61H105ME13D")
            mpn(left, switch, "TPS2553DDBVR")
            pins(left, switch, {1: "/USB_PORT_5V", 2: "GND"})
    for port, v, prefix in [(1, left, "/USB-C PD1/"), (2, right, "/USB-C PD2/")]:
        if v is None:
            continue
        # Resolve the existing standalone sheet prefix; signal boundary names
        # themselves remain explicit and cannot be guessed from board pads.
        ref = "U" + str(719 + port)
        raw = next(
            (n for n in v.pins.get(ref, {}).values() if n.endswith(f"/PD{port}_PPHV")),
            None,
        )
        if raw is None:
            failures.append(ref + ": missing PPHV net")
            continue
        prefix = raw.rsplit("/", 1)[0] + "/"
        out = f"/PD{port}_VBUS_GATED" if port == 2 else prefix + f"PD{port}_VBUS_GATED"
        mpn(v, ref, "TPS259827ONRGER")
        mpn(v, "R2086" if port == 1 else "R2096", "RC0603FR-07150KL")
        pins(
            v,
            ref,
            {
                **{n: raw for n in (1, 2, 3, 16, 25)},
                **{n: out for n in range(17, 25)},
                **{n: "GND" for n in (4, 5, 10, 11, 12, 14, 26)},
                6: prefix + f"PD{port}_EFUSE_SHDN",
                7: None,
                8: prefix + f"PD{port}_EFUSE_ILIM",
                9: prefix + f"PD{port}_EFUSE_IMON",
                13: f"/PD{port}_EFUSE_PG",
                15: prefix + f"PD{port}_EFUSE_DVDT",
            },
        )
    return {
        "checks": count,
        "failures": failures,
        "expected_pins": expected_pins,
        "physical_tests": "NOT_RUN",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("center", "left", "right"):
        p.add_argument("--" + n, type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = check(*(component_values(getattr(a, n)) for n in ("center", "left", "right")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, indent=2) + "\n")
    print(f"{r['checks']} wiring checks, {len(r['failures'])} failures")
    for f in r["failures"]:
        print(f)
    raise SystemExit(bool(r["failures"]))


if __name__ == "__main__":
    main()
