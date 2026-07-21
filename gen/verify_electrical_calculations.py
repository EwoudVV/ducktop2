#!/usr/bin/env python3
"""Recalculate critical analog set-points from the exported KiCad netlist.

This intentionally does not import values from the schematic generators.  It
exports the current root schematic, reads the component values KiCad sees, and
then applies the equations from the relevant component datasheets.  Critical
thresholds include stated IC and resistor tolerance corners where the released
values depend on them.  PCB parasitics, thermals, control-loop stability, and
bench behavior remain separate release checks.
"""

from __future__ import annotations

import argparse
import datetime as dt
import itertools
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / "ducktop2.kicad_sch"
RADIO_SCHEMATIC = ROOT / "radio_daughterboard" / "radio_daughterboard.kicad_sch"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
EC_POLICY_HEADER = ROOT / "firmware/ec/include/ducktop2/ec/ec_policy.h"


@dataclass(frozen=True)
class Check:
    name: str
    value: float
    unit: str
    low: float
    high: float
    equation: str

    @property
    def passed(self) -> bool:
        return self.low <= self.value <= self.high


def parse_engineering(value: str) -> float:
    """Parse the leading engineering value used in generated part values."""
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*([pnumkM]?)", value)
    if not match:
        raise ValueError(f"cannot parse engineering value from {value!r}")
    number = float(match.group(1))
    multiplier = {
        "": 1.0,
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "k": 1e3,
        "M": 1e6,
    }[match.group(2)]
    return number * multiplier


def export_netlist(schematic: Path, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(KICAD_CLI),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(path),
            str(schematic),
        ],
        check=True,
        cwd=ROOT,
    )


def component_values(netlist: Path) -> dict[str, str]:
    root = ET.parse(netlist).getroot()
    values: dict[str, str] = {}
    for comp in root.findall(".//comp"):
        ref = comp.get("ref")
        if ref:
            values[ref] = comp.findtext("value") or ""
    return values


def resistor(values: dict[str, str], ref: str) -> float:
    try:
        return parse_engineering(values[ref])
    except KeyError as exc:
        raise KeyError(f"required component {ref} is absent from exported netlist") from exc


def capacitor(values: dict[str, str], ref: str) -> float:
    return resistor(values, ref)


def firmware_integer_define(name: str) -> int:
    text = EC_POLICY_HEADER.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{re.escape(name)}\s+(\d+)u\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"required firmware policy constant {name} is absent from {EC_POLICY_HEADER}")
    return int(match.group(1))


def three_resistor_window(r_top: float, r_mid: float, r_bottom: float,
                          reference: float) -> tuple[float, float]:
    total = r_top + r_mid + r_bottom
    uv = reference * total / (r_mid + r_bottom)
    ov = reference * total / r_bottom
    return uv, ov


def three_resistor_window_corners(r_top: float, r_mid: float, r_bottom: float,
                                  tolerance: float, reference_min: float,
                                  reference_max: float,
                                  leakage_abs: float) -> tuple[float, float, float, float]:
    """Return UV-min/UV-max/OV-min/OV-max including both comparator leakages."""
    results: list[tuple[float, float]] = []
    for top_scale, mid_scale, bottom_scale, reference, uv_leakage, ov_leakage in itertools.product(
        (1.0 - tolerance, 1.0 + tolerance),
        (1.0 - tolerance, 1.0 + tolerance),
        (1.0 - tolerance, 1.0 + tolerance),
        (reference_min, reference_max),
        (-leakage_abs, leakage_abs),
        (-leakage_abs, leakage_abs),
    ):
        top = r_top * top_scale
        middle = r_mid * mid_scale
        bottom = r_bottom * bottom_scale
        ov_node_at_uv = (reference / middle - ov_leakage) / (1.0 / middle + 1.0 / bottom)
        uv_input = reference + top * ((reference - ov_node_at_uv) / middle + uv_leakage)
        uv_node_at_ov = reference + middle * (reference / bottom + ov_leakage)
        ov_input = uv_node_at_ov + top * (reference / bottom + ov_leakage + uv_leakage)
        results.append((uv_input, ov_input))
    return (
        min(result[0] for result in results),
        max(result[0] for result in results),
        min(result[1] for result in results),
        max(result[1] for result in results),
    )


def add_window(checks: list[Check], name: str, refs: tuple[str, str, str],
               values: dict[str, str], reference: float,
               uv_limits: tuple[float, float], ov_limits: tuple[float, float]) -> None:
    top, middle, bottom = (resistor(values, ref) for ref in refs)
    uv, ov = three_resistor_window(top, middle, bottom, reference)
    refs_text = "/".join(refs)
    checks.extend([
        Check(f"{name} UV rising", uv, "V", *uv_limits,
              f"VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), {refs_text}"),
        Check(f"{name} OV rising", ov, "V", *ov_limits,
              f"VREF*(Rtop+Rmid+Rbot)/Rbot, {refs_text}"),
    ])

def build_checks(values: dict[str, str], radio_values: dict[str, str]) -> list[Check]:
    checks: list[Check] = []

    pack_uv, _ = three_resistor_window(
        resistor(values, "R700"), resistor(values, "R701"),
        resistor(values, "R702"), 0.5,
    )
    add_window(checks, "LTC4368 pack acceptance", ("R700", "R701", "R702"),
               values, 0.5, (8.2, 8.7), (13.2, 13.8))
    pack_breaker = 0.050 / resistor(values, "RS10")
    pack_shunt = resistor(values, "RS10")
    pack_breaker_min = 0.040 / (pack_shunt * 1.01)
    pack_breaker_max = 0.060 / (pack_shunt * 0.99)
    bms_shunt = resistor(values, "RS11")
    bms_ocd_nominal = 0.060 / bms_shunt
    bms_ocd_min = 0.048 / (bms_shunt * 1.01)
    bms_ocd_max = 0.072 / (bms_shunt * 0.99)
    bms_scd_nominal = 0.120 / bms_shunt
    bms_scd_min = 0.096 / (bms_shunt * 1.01)
    bms_scd_max = 0.144 / (bms_shunt * 0.99)
    bms_shunt_power_at_pack_trip = pack_breaker_max ** 2 * bms_shunt
    bms_balance_resistance = resistor(values, "R841")
    bms_balance_nominal = 4.2 / (2.0 * bms_balance_resistance + 12.0)
    bms_balance_worst_max = 4.24 / (2.0 * bms_balance_resistance * 0.99 + 8.0)
    charger_ts_ratio = resistor(values, "R705") / (
        resistor(values, "R16") + resistor(values, "R705")
    )
    checks.extend([
        Check("LTC4368 bidirectional pack breaker nominal", pack_breaker, "A", 4.4, 4.7,
              "50mV/RS10; nominal forward and reverse magnitude"),
        Check("LTC4368 breaker worst-case minimum", pack_breaker_min, "A", 3.5, 3.7,
              "40mV/(RS10*1.01); LTC4368 threshold minimum and shunt +1%"),
        Check("LTC4368 breaker worst-case maximum", pack_breaker_max, "A", 5.4, 5.6,
              "60mV/(RS10*0.99); LTC4368 threshold maximum and shunt -1%"),
        Check("LTC4368 nominal VOUT capacitance", capacitor(values, "C725") * 1e6,
              "uF", 9.9, 10.1,
              "C725 on PACK_POS_FUSED; datasheet requires at least 1uF effective at VOUT"),
        Check("BQ7791500 backup overcurrent nominal", bms_ocd_nominal, "A", 7.4, 7.6,
              "BQ7791500PWR 60mV OCD threshold / RS11"),
        Check("BQ7791500 backup overcurrent worst-case minimum", bms_ocd_min, "A", 5.9, 6.1,
              "48mV/(RS11*1.01); protector threshold minimum and shunt +1%"),
        Check("BQ7791500 backup overcurrent worst-case maximum", bms_ocd_max, "A", 9.0, 9.2,
              "72mV/(RS11*0.99); protector threshold maximum and shunt -1%"),
        Check("BQ7791500 short-circuit nominal", bms_scd_nominal, "A", 14.9, 15.1,
              "BQ7791500PWR 120mV SCD threshold / RS11"),
        Check("BQ7791500 short-circuit worst-case minimum", bms_scd_min, "A", 11.8, 12.0,
              "96mV/(RS11*1.01); protector threshold minimum and shunt +1%"),
        Check("BQ7791500 short-circuit worst-case maximum", bms_scd_max, "A", 18.0, 18.2,
              "144mV/(RS11*0.99); protector threshold maximum and shunt -1%"),
        Check("BQ7791500 shunt dissipation at LTC4368 worst-case trip",
              bms_shunt_power_at_pack_trip, "W", 0.0, 0.30,
              "I(LTC4368 max)^2*RS11; RS11 is rated 2W"),
        Check("BQ7791500 internal balance current nominal",
              bms_balance_nominal * 1000.0, "mA", 25.0, 27.0,
              "4.2V/(2*R841+12ohm typical internal balance FET)"),
        Check("BQ7791500 internal balance current worst-case maximum",
              bms_balance_worst_max * 1000.0, "mA", 0.0, 30.0,
              "4.24V/(2*R841*0.99+8ohm); below TI 50mA maximum"),
        Check("BQ7791500 internal balance filter capacitance",
              capacitor(values, "C842") * 1e6, "uF", 0.99, 1.01,
              "C842-C844/C848 are contract-checked at TI's 1uF internal-balance value"),
        Check("BQ25798 fixed TS divider", charger_ts_ratio * 100.0, "% REGN", 58.0, 60.0,
              "R705/(R16+R705); inside the default 44.8%-68.4% normal-temperature window"),
    ])
    aon_top = resistor(values, "R795")
    aon_middle = resistor(values, "R796")
    aon_bottom = resistor(values, "R797")
    aon_uv_min, aon_uv_max, aon_ov_min, aon_ov_max = three_resistor_window_corners(
        aon_top, aon_middle, aon_bottom, 0.001, 1.183, 1.223, 0.1e-6,
    )
    add_window(checks, "TPS259470A aggregate AON acceptance", ("R795", "R796", "R797"),
               values, 1.2, (6.1, 6.3), (22.1, 22.7))
    aon_5v_rejection_margin = aon_uv_min - 5.5
    aon_aux7_accept_margin = (7.0 - 0.5) - aon_uv_max
    aon_pd15_accept_margin = (15.0 * 0.95 - 0.5) - aon_uv_max
    aon_current_nominal = 3334.0 / resistor(values, "R798")
    aon_current_min = 0.850 * 3320.0 / (resistor(values, "R798") * 1.001)
    aon_current_max = 1.150 * 3320.0 / (resistor(values, "R798") * 0.999)
    aon_slew = 2000.0 / (capacitor(values, "C799") * 1e12)
    checks.extend([
        Check("TPS259470A aggregate AON UV rising worst-case minimum", aon_uv_min, "V", 6.02, 6.10,
              "R795/R796/R797 at 0.1%, VUV=1.183V, and both pin leakages at corners"),
        Check("TPS259470A aggregate AON UV rising worst-case maximum", aon_uv_max, "V", 6.32, 6.40,
              "R795/R796/R797 at 0.1%, VUV=1.223V, and both pin leakages at corners"),
        Check("TPS259470A aggregate AON OV rising worst-case minimum", aon_ov_min, "V", 21.8, 22.1,
              "R795/R796/R797 at 0.1%, VOV=1.183V, and both pin leakages at corners"),
        Check("TPS259470A aggregate AON OV rising worst-case maximum", aon_ov_max, "V", 22.7, 23.0,
              "R795/R796/R797 at 0.1%, VOV=1.223V, and both pin leakages at corners; below 23V recommended input maximum"),
        Check("AON rejection margin above USB-C default 5V maximum", aon_5v_rejection_margin, "V", 0.50, 0.70,
              "AON UVLO worst-case minimum-5.5V; a 5V-only source is negotiation-only and cannot boot the EC"),
        Check("AON acceptance margin at minimum 7V AUX", aon_aux7_accept_margin, "V", 0.10, 0.30,
              "7.0V minimum AUX-0.5V conservative Schottky drop-AON UVLO worst-case maximum"),
        Check("AON acceptance margin at minimum 15V PDO", aon_pd15_accept_margin, "V", 7.0, 8.0,
              "15V PDO at -5%-0.5V conservative Schottky drop-AON UVLO worst-case maximum"),
        Check("TPS259470A aggregate AON current limit nominal", aon_current_nominal, "A", 1.45, 1.56,
              "3334/R798, TI Equation 5"),
        Check("TPS259470A aggregate AON current limit worst-case minimum", aon_current_min, "A", 1.25, 1.35,
              "TPS25947 table minimum scaled from 3.32kOhm and R798 +0.1%"),
        Check("TPS259470A aggregate AON current limit worst-case maximum", aon_current_max, "A", 1.65, 1.75,
              "TPS25947 table maximum scaled from 3.32kOhm and R798 -0.1%"),
        Check("TPS259470A aggregate AON output slew", aon_slew, "V/ms", 0.55, 0.67,
              "2000/C799(pF), TI Equation 4"),
    ])
    pd_ports = (
        (1, ("R2080", "R2081", "R2082"), "R2083", 2000),
        (2, ("R2090", "R2091", "R2092"), "R2093", 2040),
    )
    for index, refs, ilim_ref, _cbase in pd_ports:
        add_window(checks, f"TPS26630 PD{index} eFuse acceptance", refs, values, 1.2,
                   (12.1, 12.6), (17.0, 17.6))
        pd_efuse_limit = 18.0 / (resistor(values, ilim_ref) / 1e3)
        checks.append(Check(f"TPS26630 PD{index} eFuse current limit", pd_efuse_limit, "A",
                            2.9, 3.1, f"18/{ilim_ref}(kOhm)"))
    # USB Type-C limits sink-side VBUS capacitance to 10 uF before attachment.
    # Count all direct raw-port capacitors plus the shared AON input reached
    # through the Schottky OR. Apply +20% capacitance tolerance and reserve an
    # additional 0.5 uF for IC, diode, connector, and layout parasitics.
    shared_raw_cap = capacitor(values, "C795") + capacitor(values, "C796")
    for index, _refs, _ilim_ref, cbase in pd_ports:
        raw_caps = tuple(f"C{cbase + offset}" for offset in range(15, 20))
        nominal = sum(capacitor(values, ref) for ref in raw_caps) + shared_raw_cap
        worst_case = nominal * 1.20 + 0.5e-6
        checks.extend([
            Check(f"USB-C PD{index} nominal pre-attach VBUS capacitance",
                  nominal * 1e6, "uF", 5.8, 5.9,
                  "+".join((*raw_caps, "C795", "C796"))),
            Check(f"USB-C PD{index} worst-case pre-attach VBUS capacitance",
                  worst_case * 1e6, "uF", 0.0, 10.0,
                  "nominal*1.20 + 0.5uF conservative unmodeled allowance; USB Type-C max 10uF"),
        ])
    for index, refs in enumerate((("R2140", "R2141", "R2142"),
                                  ("R2143", "R2144", "R2145")), start=1):
        add_window(checks, f"LTC4418 PD{index} selector acceptance", refs, values, 1.0,
                   (12.8, 13.3), (16.7, 17.5))
    add_window(checks, "LTC4418 USB acceptance", ("R730", "R731", "R732"),
               values, 1.0, (12.8, 13.3), (16.7, 17.5))
    add_window(checks, "LTC4418 AUX acceptance", ("R733", "R734", "R735"),
               values, 1.0, (5.3, 5.9), (22.5, 24.0))
    add_window(checks, "TPS26630 AUX protection", ("R711", "R712", "R713"),
               values, 1.2, (5.3, 5.8), (22.5, 23.5))
    aux_efuse_limit = 18.0 / (resistor(values, "R710") / 1e3)
    aux_pg_nominal = 1.2 * (1.0 + resistor(values, "R739") / resistor(values, "R740"))
    aux_pg_minimum = 1.176 * (
        1.0 + resistor(values, "R739") * 0.999 / (resistor(values, "R740") * 1.001)
    )
    aux_pg_maximum = 1.224 * (
        1.0 + resistor(values, "R739") * 1.001 / (resistor(values, "R740") * 0.999)
    )
    checks.extend([
        Check("TPS26630 AUX current limit", aux_efuse_limit, "A", 2.9, 3.1,
              "18/R710(kOhm)"),
        Check("TPS26630 AUX PGOOD rising nominal", aux_pg_nominal, "V", 5.20, 5.35,
              "1.2V*(1+R739/R740)"),
        Check("TPS26630 AUX PGOOD rising worst-case minimum", aux_pg_minimum, "V", 5.10, 5.25,
              "1.176V*(1+R739*0.999/(R740*1.001))"),
        Check("TPS26630 AUX PGOOD rising worst-case maximum", aux_pg_maximum, "V", 5.30, 5.45,
              "1.224V*(1+R739*1.001/(R740*0.999))"),
    ])

    r_ilim_top = resistor(values, "R17")
    r_ilim_bottom = resistor(values, "R190")
    bq_ilim = (5.0 * r_ilim_bottom / (r_ilim_top + r_ilim_bottom) - 1.0) / 0.8
    checks.append(Check("BQ25798 hardware input-current ceiling", bq_ilim, "A", 2.9, 3.1,
                        "(5V*R190/(R17+R190)-1V)/(0.8V/A)"))
    qualified_pd_power = 15.0 * (bq_ilim - 0.25)
    checks.append(Check("15V PD usable input budget with firmware reserve", qualified_pd_power, "W", 40.0, 42.0,
                        "15V*(ILIM ceiling-0.25A); firmware also caps IINDPM from the active TPS25751A PDO/RDO"))

    sys_5v = 0.6 * (1.0 + resistor(values, "R40") / resistor(values, "R41"))
    sys_5v_min = 0.591 * (
        1.0 + resistor(values, "R40") * 0.999 / (resistor(values, "R41") * 1.001)
    )
    sys_5v_max = 0.609 * (
        1.0 + resistor(values, "R40") * 1.001 / (resistor(values, "R41") * 0.999)
    )
    hdmi_5v_guaranteed_min = sys_5v_min - 0.002 - 0.205 - 0.050
    sys_5v_cout = capacitor(values, "C44") + capacitor(values, "C45")
    sys_3v3 = 0.6 * (1.0 + resistor(values, "R43") / resistor(values, "R44"))
    checks.extend([
        Check("TPS56637 SYS_5V set-point", sys_5v, "V", 5.18, 5.23,
              "0.6V*(1+R40/R41)"),
        Check("TPS56637 SYS_5V worst-case minimum", sys_5v_min, "V", 5.10, 5.15,
              "0.591V*(1+R40*0.999/(R41*1.001))"),
        Check("TPS56637 SYS_5V worst-case maximum", sys_5v_max, "V", 5.25, 5.35,
              "0.609V*(1+R40*1.001/(R41*0.999))"),
        Check("HDMI +5V guaranteed connector minimum", hdmi_5v_guaranteed_min, "V", 4.80, 5.25,
              "SYS_5V(min)-0.002V TPS22975 drop-0.205V TPD13S523 drop-0.050V board/connector allowance"),
        Check("TPS56637 SYS_5V nominal output capacitance", sys_5v_cout * 1e6, "uF", 40.0, 100.0,
              "C44+C45; effective capacitance under DC bias remains a release hold"),
        Check("TPS56637 SYS_3V3 set-point", sys_3v3, "V", 3.25, 3.35,
              "0.6V*(1+R43/R44)"),
    ])

    for name, ref in (
        ("Hub USB-C J22", "R1780"),
        ("Hub USB-C J23", "R1740"),
        ("Hub USB-C J12", "R1760"),
        ("Internal trackpad", "R252"),
    ):
        r_kohm = resistor(values, ref) / 1e3
        nominal = 26.38 / r_kohm
        minimum = 23.36 / r_kohm
        maximum = 29.84 / r_kohm
        expected = (1.15, 1.50) if ref != "R252" else (0.53, 0.70)
        checks.extend([
            Check(f"{name} TPS2553D nominal current limit", nominal, "A", *expected,
                  f"26.38/{ref}(kOhm)"),
            Check(f"{name} TPS2553D minimum current limit", minimum, "A", *expected,
                  f"23.36/{ref}(kOhm)"),
            Check(f"{name} TPS2553D maximum current limit", maximum, "A", *expected,
                  f"29.84/{ref}(kOhm)"),
        ])

    rgb_r_kohm = resistor(values, "R388") / 1e3
    rgb_nominal = 26.38 / rgb_r_kohm
    rgb_minimum = 23.36 / rgb_r_kohm
    rgb_maximum = 29.84 / rgb_r_kohm
    checks.extend([
        Check("Keyboard RGB TPS2553D nominal current limit", rgb_nominal, "A", 0.39, 0.41,
              "TPS2553D datasheet ILIM table interpolation; 26.38/R388(kOhm)"),
        Check("Keyboard RGB TPS2553D minimum current limit", rgb_minimum, "A", 0.34, 0.36,
              "TPS2553D lower tolerance; 23.36/R388(kOhm)"),
        Check("Keyboard RGB TPS2553D maximum current limit", rgb_maximum, "A", 0.44, 0.46,
              "TPS2553D upper tolerance; 29.84/R388(kOhm), below 0.5A/contact"),
    ])

    ec_vout = 0.596 * (1.0 + resistor(values, "R35") / resistor(values, "R36"))
    ec_inductor = parse_engineering(values["L3"])
    ec_lmin = 3.3 * (28.0 - 3.3) / (28.0 * 0.30 * 2.0 * 500e3)
    ec_peak = 2.0 + 3.3 * (28.0 - 3.3) / (28.0 * ec_inductor * 500e3 * 1.6)
    ec_cout = capacitor(values, "C39") + capacitor(values, "C291")
    checks.extend([
        Check("TPS54202 MCU_3V3 set-point", ec_vout, "V", 3.25, 3.35,
              "0.596V*(1+R35/R36)"),
        Check("TPS54202 inductor versus 28V design minimum", ec_inductor * 1e6, "uH",
              ec_lmin * 1e6, 10.5,
              "L3; Lmin=3.3V*(28V-3.3V)/(28V*0.30*2A*500kHz)"),
        Check("TPS54202 full-load peak inductor current", ec_peak, "A", 2.0, 3.3,
              "TI Eq.10 at 28V/2A; upper band is XGL5030-103 20%-drop Isat"),
        Check("TPS54202 nominal ceramic output capacitance", ec_cout * 1e6, "uF", 43.0, 45.0,
              "C39+C291; DC-bias derating remains a layout/bench hold"),
        Check("TPS54202 feed-forward capacitor", capacitor(values, "C292") * 1e12, "pF", 53.0, 59.0,
              "C292; TI 3.3V recommended-component table"),
    ])

    radio_vout = 0.596 * (
        1.0 + resistor(radio_values, "R221") / resistor(radio_values, "R222")
    )
    radio_vout_max = 0.611 * (
        1.0 + resistor(radio_values, "R221") * 1.01 /
        (resistor(radio_values, "R222") * 0.99)
    )
    pe42820_control_max = radio_vout_max * (
        resistor(radio_values, "R227") * 1.01 /
        (resistor(radio_values, "R242") * 0.99 +
         resistor(radio_values, "R227") * 1.01)
    )
    radio_inductor = parse_engineering(radio_values["L70"])
    radio_vin_max = sys_5v_max
    radio_ripple_worst = radio_vout * (radio_vin_max - radio_vout) / (
        radio_vin_max * radio_inductor * 0.80 * 290e3
    )
    radio_peak = 3.0 + radio_ripple_worst / 2.0
    radio_rms = math.sqrt(3.0**2 + radio_ripple_worst**2 / 12.0)
    radio_cout = capacitor(radio_values, "C222") + capacitor(radio_values, "C225")
    checks.extend([
        Check("TPS54302 RADIO_4V0 set-point", radio_vout, "V", 3.95, 4.08,
              "0.596V*(1+R221/R222)"),
        Check("PE42820 control worst-case maximum", pe42820_control_max, "V", 0.0, 3.55,
              "RADIO_4V0(max)*R227(max)/(R242(min)+R227(max)); PE42820 absolute max is 3.6V"),
        Check("TPS54302 worst-case full-load ripple ratio", radio_ripple_worst / 3.0, "ratio", 0.0, 0.45,
              "SYS_5V(max), L70 -20%, fSW(min)=290kHz; KIND is designer-selected per TI Eq.8"),
        Check("TPS54302 worst-case full-load peak current", radio_peak, "A", 3.0, 4.0,
              "Worst-case ripple at 3A; upper band is TPS54302 guaranteed minimum high-side current limit"),
        Check("XGL5030-332 worst-case full-load RMS current", radio_rms, "A", 3.0, 6.0,
              "TI Eq.9; upper band is below Coilcraft 7.2A 20C-rise Irms with margin"),
        Check("XGL5030-332 peak versus 20%-drop Isat", radio_peak, "A", 3.0, 6.0,
              "Worst-case peak current; XGL5030-332 20%-drop Isat is 6.0A"),
        Check("TPS54302 nominal ceramic output capacitance", radio_cout * 1e6, "uF", 43.0, 45.0,
              "C222+C225; DC-bias derating remains a layout/bench hold"),
        Check("TPS54302 feed-forward capacitor", capacitor(radio_values, "C224") * 1e12, "pF", 53.0, 59.0,
              "C224; interpolated starting point between TI 3.3V and 5V table rows"),
    ])

    mu_12v = 1.2 * (1.0 + resistor(values, "R753") / resistor(values, "R754"))
    mu_shunt = resistor(values, "RS750")
    mu_current = 0.050 / mu_shunt
    mu_current_min = 0.048 / (mu_shunt * 1.01)
    mu_current_max = 0.052 / (mu_shunt * 0.99)
    mu_power_min = (mu_12v * 0.99) * mu_current_min
    mu_power_max = (mu_12v * 1.01) * mu_current_max
    mu_uvlo = 1.23 * (1.0 + resistor(values, "R759") / resistor(values, "R760"))
    mu_uvlo_min = 1.20 * (1.0 + resistor(values, "R759") * 0.99 /
                          (resistor(values, "R760") * 1.01))
    mu_uvlo_max = 1.26 * (1.0 + resistor(values, "R759") * 1.01 /
                          (resistor(values, "R760") * 0.99))
    mu_force_off_gate = 8.45 * resistor(values, "R761") / (
        resistor(values, "R766") + resistor(values, "R761")
    )
    mu_fsw = 20e9 / resistor(values, "R756")
    low_pack_budget = firmware_integer_define("EC_DEFAULT_LOW_PACK_MU_EDP_BUDGET_MW") / 1000.0
    normal_mu_edp_budget = firmware_integer_define("EC_DEFAULT_NORMAL_MU_EDP_BUDGET_MW") / 1000.0
    low_pack_reserve = firmware_integer_define("EC_DEFAULT_SYSTEM_RESERVE_MW") / 1000.0
    source_efficiency = firmware_integer_define("EC_DEFAULT_SOURCE_EFFICIENCY_PERMILLE") / 1000.0
    low_pack_power = pack_uv * pack_breaker_min
    low_pack_continuous_power = 0.80 * low_pack_power
    low_pack_required_input = low_pack_budget / source_efficiency + low_pack_reserve
    low_pack_mu_headroom = low_pack_continuous_power - low_pack_required_input
    fan_max_current = 0.26
    fan_max_power = (mu_12v * 1.01) * fan_max_current
    fan_fuse_margin = resistor(values, "F200") / fan_max_current
    fan_fg_cutoff = 1.0 / (2.0 * math.pi * resistor(values, "R206") * capacitor(values, "C209"))
    fan_fg_max = 6100.0 * 2.0 / 60.0
    fan_fg_filter_ratio = fan_fg_cutoff / fan_fg_max
    normal_mu_rail_headroom = mu_power_min - normal_mu_edp_budget - fan_max_power
    support_reserve_after_fan = low_pack_reserve - fan_max_power
    checks.extend([
        Check("TPS552892 MU_12V set-point", mu_12v, "V", 11.9, 12.15,
              "1.2V*(1+R753/R754)"),
        Check("TPS552892 output-current limit", mu_current, "A", 3.2, 3.5,
              "50mV/RS750"),
        Check("TPS552892 output-current worst-case minimum", mu_current_min, "A", 3.1, 3.25,
              "48mV/(RS750*1.01); current-threshold minimum and shunt +1%"),
        Check("TPS552892 output-current worst-case maximum", mu_current_max, "A", 3.45, 3.55,
              "52mV/(RS750*0.99); current-threshold maximum and shunt -1%"),
        Check("TPS552892 total MU_12V worst-case low ceiling", mu_power_min, "W", 37.5, 38.5,
              "MU_12V*0.99*Ilimit_min; shared by Mu, eDP backlight, and fan"),
        Check("TPS552892 total MU_12V worst-case high ceiling", mu_power_max, "W", 42.0, 43.0,
              "MU_12V*1.01*Ilimit_max; shared by Mu, eDP backlight, and fan"),
        Check("Delta blower worst-case rail power", fan_max_power, "W", 3.0, 3.3,
              "MU_12V high corner*0.26A fan datasheet maximum"),
        Check("Delta blower PTC hold-current margin", fan_fuse_margin, "x", 2.5, 3.2,
              "F200 hold current/BFB04512HHA-CZ0T 0.26A maximum"),
        Check("Delta blower FG RC cutoff", fan_fg_cutoff / 1e3, "kHz", 4.5, 5.5,
              "1/(2*pi*R206*C209); Delta typical is 8.2k/4nF"),
        Check("Delta blower FG filter/pulse ratio", fan_fg_filter_ratio, "x", 20.0, 30.0,
              "FG RC cutoff/(6100RPM*2 pulses/rev/60)"),
        Check("MU_12V headroom after normal Mu/eDP budget and maximum fan", normal_mu_rail_headroom, "W", 4.0, 8.0,
              "MU_12V low current-limit ceiling-normal Mu/eDP budget-fan maximum"),
        Check("System reserve remaining after maximum fan", support_reserve_after_fan, "W", 2.5, 4.0,
              "EC system reserve-fan maximum; remaining reserve covers mandatory support loads"),
        Check("TPS552892 rising UVLO", mu_uvlo, "V", 8.8, 9.2,
              "1.23V*(1+R759/R760), hysteresis excluded"),
        Check("TPS552892 rising UVLO worst-case minimum", mu_uvlo_min, "V", 8.55, 8.75,
              "1.20V*(1+R759*0.99/(R760*1.01))"),
        Check("TPS552892 rising UVLO worst-case maximum", mu_uvlo_max, "V", 9.3, 9.5,
              "1.26V*(1+R759*1.01/(R760*0.99))"),
        Check("Mu fail-off Q750 gate at 8.45V VSYS", mu_force_off_gate, "V", 4.0, 4.5,
              "8.45V*R761/(R766+R761); reset-state gate divider"),
        Check("TPS552892 switching frequency", mu_fsw / 1e3, "kHz", 380, 420,
              "20e9/R756"),
        Check("Low-pack derated source power minus enforced firmware budget", low_pack_mu_headroom, "W", 0.5, 10.0,
              "0.80*LTC4368 pack UV*breaker_min-(EC low-pack Mu+eDP budget/efficiency)-EC system reserve"),
    ])

    mic_gain = 1.0 + resistor(values, "R432") / resistor(values, "R433")
    mic_shelf = 1.0 / (
        2.0 * math.pi * resistor(values, "R433") * capacitor(values, "C454")
    )
    mic_feedback_pole = 1.0 / (
        2.0 * math.pi * resistor(values, "R432") * capacitor(values, "C453")
    )
    mic_94db_rms_typ = 10.0 ** (-38.0 / 20.0)
    mic_adc_full_scale_rms_typ = 0.6 * 3.3 / (2.0 * math.sqrt(2.0))
    mic_headroom_typ = 20.0 * math.log10(
        mic_adc_full_scale_rms_typ / (mic_94db_rms_typ * mic_gain)
    )
    mic_noise_floor_typ = -(mic_headroom_typ + 68.0)
    mic_94db_rms_high = 10.0 ** (-37.0 / 20.0)
    mic_adc_full_scale_rms_min = 0.6 * 3.1 / (2.0 * math.sqrt(2.0))
    mic_headroom_worst = 20.0 * math.log10(
        mic_adc_full_scale_rms_min / (mic_94db_rms_high * mic_gain)
    )
    checks.extend([
        Check("Built-in microphone audio-band gain", mic_gain, "V/V", 5.9, 6.1,
              "1+R432/R433; C454 restores unity DC gain"),
        Check("Built-in microphone low-frequency gain shelf", mic_shelf, "Hz", 32.0, 36.0,
              "1/(2*pi*R433*C454)"),
        Check("Built-in microphone feedback pole", mic_feedback_pole / 1e3, "kHz", 24.0, 28.0,
              "1/(2*pi*R432*C453)"),
        Check("Built-in microphone typical ADC headroom at 94dBSPL", mic_headroom_typ, "dB", 18.8, 19.8,
              "PCM2900 0.6*3.3Vpp full scale versus IM68 -38dBV/Pa times preamp gain"),
        Check("Built-in microphone worst-case ADC headroom at 94dBSPL", mic_headroom_worst, "dB", 17.2, 18.4,
              "PCM2900 0.6*3.1Vpp minimum rail versus IM68 -37dBV/Pa maximum sensitivity"),
        Check("Built-in microphone nominal self-noise at ADC", mic_noise_floor_typ, "dBFS", -88.0, -86.5,
              "-(94dBSPL headroom + IM68 68dBA SNR); PCM2900 ADC SNR is 89dB typical"),
    ])

    eth_load_c1 = capacitor(values, "C515")
    eth_load_c2 = capacitor(values, "C516")
    eth_load = (eth_load_c1 * eth_load_c2) / (eth_load_c1 + eth_load_c2) + 2.0e-12
    checks.append(
        Check("RTL8111H 25MHz crystal effective load", eth_load * 1e12, "pF", 7.8, 8.2,
              "(C515*C516)/(C515+C516)+2.0pF assumed pin/PCB stray; Y500 CL=8pF")
    )

    pd_hold_up = capacitor(values, "C2146")
    main_hold_up = capacitor(values, "C746")
    pd_droop = bq_ilim * (7e-6 + 4e-6) / pd_hold_up
    main_droop = bq_ilim * (7e-6 + 4e-6) / main_hold_up
    checks.extend([
        Check("LTC4418 dual-PD selector handoff droop", pd_droop, "V", 0.0, 0.40,
              "BQ ILIM ceiling*(7us VALID-off max+4us break-before-make max)/C2146; ESR and adapter loss excluded"),
        Check("LTC4418 PD/AUX selector handoff droop", main_droop, "V", 0.0, 0.40,
              "BQ ILIM ceiling*(7us+4us)/C746; ESR and source loss excluded"),
    ])

    # ST AN2867 negative-resistance screening.  Stray capacitance is an
    # explicit prototype assumption until the assembled PCB is measured.
    hse_cap = capacitor(values, "C32")
    hse_load = hse_cap / 2.0 + 3.0e-12
    hse_gmcrit = (
        4.0 * 400.0 * (2.0 * math.pi * 8.0e6) ** 2
        * (5.0e-12 + hse_load) ** 2
    )
    hse_margin = 5.0e-3 / hse_gmcrit
    lse_cap = capacitor(values, "C34")
    lse_load = lse_cap / 2.0 + 2.6e-12
    lse_gmcrit = (
        4.0 * 50.0e3 * (2.0 * math.pi * 32768.0) ** 2
        * (1.0e-12 + lse_load) ** 2
    )
    lse_margin = 2.8e-6 / lse_gmcrit
    checks.extend([
        Check("STM32 HSE effective crystal load", hse_load * 1e12, "pF", 7.75, 8.25,
              "C32/2+3.0pF assumed PCB/pin stray; C32=C33=10pF"),
        Check("STM32 HSE critical transconductance", hse_gmcrit * 1e3, "mA/V", 0.0, 1.0,
              "4*ESR*(2*pi*f)^2*(C0+CL)^2; ESRmax=400ohm, C0max=5pF"),
        Check("STM32 HSE startup gain-margin screen", hse_margin, "x", 5.0, 20.0,
              "STM32 gm_min/gmcrit; gm_min=5mA/V"),
        Check("STM32 LSE effective crystal load", lse_load * 1e12, "pF", 5.75, 6.25,
              "C34/2+2.6pF assumed PCB/pin stray; C34=C35=6.8pF"),
        Check("STM32 LSE critical transconductance", lse_gmcrit * 1e6, "uA/V", 0.0, 0.56,
              "4*ESR*(2*pi*f)^2*(C0+CL)^2; ESRmax=50kohm, C0typ=1.0pF"),
        Check("STM32 LSE startup gain-margin screen", lse_margin, "x", 5.0, 20.0,
              "STM32 gm_min/gmcrit; gm_min=2.8uA/V"),
    ])

    return checks


def render_report(checks: list[Check], netlist: Path, radio_netlist: Path) -> str:
    lines = [
        "# Ducktop2 Electrical Calculations",
        "",
        f"Generated: {dt.date.today().isoformat()}",
        "",
        "These values were recalculated from the component values in a fresh KiCad XML netlist, not copied from generator comments.",
        "",
        "| Check | Result | Required band | Status | Equation |",
        "|---|---:|---:|:---:|---|",
    ]
    for check in checks:
        result = f"{check.value:.4g} {check.unit}"
        band = f"{check.low:g} to {check.high:g} {check.unit}"
        lines.append(f"| {check.name} | {result} | {band} | {'PASS' if check.passed else 'FAIL'} | {check.equation} |")

    failures = [check for check in checks if not check.passed]
    lines.extend([
        "",
        f"Result: **{len(checks) - len(failures)} PASS, {len(failures)} FAIL**.",
        "",
        "## Scope And Holds",
        "",
        "- This is a DC/set-point and selector hold-up calculation, not a substitute for vendor-model loop simulation or bench validation.",
        "- The LTC4368, TPS552892, TPS26630 PGOOD, TPS56637 SYS_5V, TPS54302/PE42820, and TPS2553 rows include the stated IC and/or resistor corners shown in their equations. Other resistor/reference tolerances, capacitor DC-bias derating, capacitor ESR, MOSFET loss, connector/cable loss, thermal rise, and PCB parasitics are not included.",
        "- C725 is 10 uF nominal against the LTC4368 minimum 1 uF effective VOUT requirement. Confirm the selected 25 V X7R part remains above 1 uF at the actual pack bias, tolerance, and temperature before release.",
        "- Each USB-C pre-attach capacitance row includes every explicit raw-port capacitor, the shared AON input capacitors reached through the Schottky OR, +20% capacitance tolerance, and a 0.5 uF unmodeled allowance. Recheck against final fitted parts and parasitics before Type-C compliance testing.",
        "- The two selector droop rows use the 3 A hardware ceiling, datasheet maximum validation-off plus break-before-make times, and only the dedicated 100 uF hybrid capacitor; ESR is still excluded.",
        "- The oscillator rows use ST AN2867's negative-resistance screen with assumed total PCB/pin stray capacitance of 3.0 pF for HSE and 2.6 pF for LSE. These are starting-value calculations, not measured qualification.",
        "- Verify HSE/LSE startup time, frequency error, and crystal drive level on assembled hardware across supply voltage and temperature before release.",
        "- TPS25751A power telemetry and firmware policy are functional requirements: keep the Mu rail disabled until the selected source is valid, read Active PDO (0x31), Active RDO (0x32), and PD Status (0x35), program VSYSMIN/IINDPM, require VSYS >=10.0 V, and cap IINDPM below the negotiated current with a 2.75 A ceiling.",
        "- Verify both TPS25751A service-I2C channels for rise time, powered-off leakage, stale-read rejection, interrupt recovery, and negotiated-contract decoding at 100 kHz and 400 kHz.",
        "- TPS552892 compensation and current-sense filtering must still be reviewed against the final layout and measured on first hardware.",
        "- The tolerance-aware MU_12V ceiling is approximately 38 to 42.5 W and is shared by the complete Mu module, eDP backlight, and Delta blower. The normal 30 W Mu/eDP budget leaves about 4.8 W at the low current-limit corner after the fan's 0.26 A maximum. Measure all three loads and lock BIOS PL1/PL2 accordingly.",
        "- The 6 W firmware system reserve explicitly includes the Delta blower's approximately 3.15 W worst-case rail draw, leaving about 2.85 W for mandatory support loads in the low-pack calculation. HIL power measurements must confirm that assumption with optional loads shed.",
        "- The low-pack row reads the released EC constants directly, derates the minimum hardware breaker power to 80%, includes the firmware source-efficiency assumption and a dedicated system reserve, and requires positive headroom. Exact cell/BMS/harness limits and HIL transient/latch-recovery tests remain release holds.",
        "- The microphone rows verify the nominal small-signal network only. Acoustic sealing, microphone sensitivity spread, ADC headroom, clipping, echo, fan noise, charger noise, and RF desense require assembled-hardware tests.",
        "- The Ethernet crystal row assumes 2.0 pF total pin/PCB stray. Confirm 25 MHz startup and frequency on assembled hardware before production release.",
        "",
        "## Primary Sources",
        "",
        "- Analog Devices LTC4368: https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4368.pdf",
        "- Analog Devices LTC4417: https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4417.pdf",
        "- Analog Devices LTC4418: https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4418.pdf",
        "- Texas Instruments TPS2663: https://www.ti.com/lit/ds/symlink/tps2663.pdf",
        "- Texas Instruments TPS25947: https://www.ti.com/lit/ds/symlink/tps25947.pdf",
        "- Texas Instruments BQ25798: https://www.ti.com/lit/ds/symlink/bq25798.pdf",
        "- Texas Instruments TPS552892: https://www.ti.com/lit/ds/symlink/tps552892.pdf",
        "- Delta BFB04512HHA-CZ0T: https://www.delta-fan.com/Download/Spec/BFB04512HHA-CZ0T.pdf",
        "- Texas Instruments TPS54202: https://www.ti.com/lit/ds/symlink/tps54202.pdf",
        "- Texas Instruments TPS54302: https://www.ti.com/lit/ds/symlink/tps54302.pdf",
        "- Texas Instruments TPS56637: https://www.ti.com/lit/ds/symlink/tps56637.pdf",
        "- Texas Instruments TPS2553: https://www.ti.com/lit/ds/symlink/tps2553.pdf",
        "- Texas Instruments TPD13S523: https://www.ti.com/lit/ds/symlink/tpd13s523.pdf",
        "- pSemi PE42820: https://www.psemi.com/pdf/datasheets/pe42820ds.pdf",
        "- Texas Instruments PCM2900C: https://www.ti.com/lit/ds/symlink/pcm2900c.pdf",
        "- Texas Instruments TLV9061/TLV9062: https://www.ti.com/lit/ds/symlink/tlv9062.pdf",
        "- Infineon IM68A130: https://www.infineon.com/dgdl/Infineon-IM68A130-DataSheet-v01_10-EN.pdf?fileId=8ac78c8c85ecb34701860371623f1204",
        "- STMicroelectronics AN2867 oscillator design guide: https://www.st.com/resource/en/application_note/an2867-oscillator-design-guide-for-stm8afals-stm32-mcus-and-mpus-stmicroelectronics.pdf",
        "- STMicroelectronics STM32F407 datasheet: https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
        "- Jauch J32SMX crystal: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7432/JQG_DB_Q-J32SMX_250618_online.pdf",
        "- Epson FC-135R crystal: https://download.epsondevice.com/td/pdf/td_xtal_32khz/FC-135R_X1A0001410006_en.pdf",
        "- Coilcraft XGL5030: https://www.coilcraft.com/getmedia/e64ac115-95f2-45c7-b798-1b3769b91583/xgl5030.pdf",
        "- Coilcraft XGL5030-332: https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xgl/xgl5030/xgl5030-332/",
        "- Texas Instruments TPS25751A: https://www.ti.com/lit/ds/symlink/tps25751a.pdf",
        "- USB-IF USB Type-C Cable and Connector Specification: https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf",
        "- Texas Instruments TCA9548A: https://www.ti.com/lit/ds/symlink/tca9548a.pdf",
        "- ECS ECS-250-8-33-AGN-TR crystal: https://ecsxtal.com/products/crystals/surface-mount-crystals/ecs-250-8-33-agn-tr/",
        "- ECS ECX-32 crystal datasheet: https://ecsxtal.com/store/pdf/ecx-32.pdf",
        "",
        f"Mainboard netlist evidence: `{netlist.relative_to(ROOT)}`",
        f"Radio daughterboard netlist evidence: `{radio_netlist.relative_to(ROOT)}`",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "verification" /
                        f"ELECTRICAL_CALCULATIONS_{dt.date.today().isoformat()}.md")
    args = parser.parse_args()

    netlist = ROOT / "verification" / "electrical_calculations_netlist.xml"
    radio_netlist = ROOT / "verification" / "radio_electrical_calculations_netlist.xml"
    export_netlist(SCHEMATIC, netlist)
    export_netlist(RADIO_SCHEMATIC, radio_netlist)
    checks = build_checks(component_values(netlist), component_values(radio_netlist))
    report = render_report(checks, netlist, radio_netlist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    failures = [check for check in checks if not check.passed]
    print(f"Electrical calculations: {len(checks) - len(failures)} PASS, {len(failures)} FAIL")
    print(f"Report: {args.output}")
    if failures:
        for check in failures:
            print(f"FAIL: {check.name}: {check.value:g} {check.unit}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
