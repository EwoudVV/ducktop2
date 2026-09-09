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

from part_identity import decode, identity_errors


ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = ROOT / "ducktop2.kicad_sch"
RADIO_SCHEMATIC = ROOT / "radio_daughterboard" / "radio_daughterboard.kicad_sch"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
EC_POLICY_HEADER = ROOT / "firmware/ec/include/ducktop2/ec/ec_policy.h"

# These entries come from the manufacturers' electrical tables, not schematic
# labels. Isat and Irms are 25 C characterization points, not guarantees of the
# assembled board's current rating. The source links are included in the report.
INDUCTORS = {
    "XAL7030-102MEC": (1e-6, .20, 28.0, 16.1, .0050),
    "XAL7030-472MEC": (4.7e-6, .20, 10.1, 6.9, .0300),
    "XAL7070-222MEC": (2.2e-6, .20, 19.6, 13.2, .0063),
    "XAL7070-332MEC": (3.3e-6, .20, 19.4, 11.5, .0094),
    "XAL7070-682MEC": (6.8e-6, .20, 12.8, 6.8, .0196),
    "XGL1060-822MEC": (8.2e-6, .20, 16.9, 9.9, .0150),
    "XGL1060-682MEC": (6.8e-6, .20, 18.4, 10.9, .0125),
    "XGL6030-103MEC": (10e-6, .20, 6.2, 5.0, .0440),
    # XGL5030 entries use the 20%-drop Isat column.
    "XGL5030-103MEC": (10e-6, .20, 3.3, 4.3, .0484),
    "XGL5030-332MEC": (3.3e-6, .20, 6.0, 7.2, .0149),
}

EXACT_PASSIVES = {
    # value, fractional initial tolerance, rated voltage (if applicable)
    "CGA5L1X7R1H106K160AC": (10e-6, .10, 50.0),
    "CGA3E3X7R1H334K080AB": (330e-9, .10, 50.0),
    "EEHZK1V101XP": (100e-6, .20, 35.0),
    "EEHZA1H680P": (68e-6, .20, 50.0),
    "T520D107M010ATE070": (100e-6, .20, 10.0),
    "T520D157M010ATE025": (150e-6, .20, 10.0),
    "T521V686M025ATE050": (68e-6, .20, 25.0),
    "T520X337M010ATE010": (330e-6, .20, 10.0),
    "T530D227M010ATE006": (220e-6, .20, 10.0),
    "C0603C224K5RACTU": (220e-9, .10, 50.0),
    "C0603C222J5GACTU": (2.2e-9, .05, 50.0),
    "WSL20105L600FEA": (.0056, .01, None),
    "ERJ8BWFR015V": (.015, .01, None),
    "ERJ8CWFR010V": (.010, .01, None),
    "ERJ8CWFR013V": (.013, .01, None),
    "C0805C223J5GACTU": (22e-9, .05, 50.0),
    "RC2010FK-071KL": (1000.0, .01, 200.0),
}


class NetlistValues(dict):
    """Values plus procurement identities and connectivity from the same export."""

    def __init__(self):
        super().__init__()
        self.parts: dict[str, tuple[str, str]] = {}
        self.pins: dict[str, dict[str, str]] = {}
        self.used: set[str] = set()

    def mpn(self, ref: str) -> str:
        return self.parts.get(ref, ("", ""))[0]

    def number(self, ref: str) -> float:
        self.used.add(ref)
        mpn = self.mpn(ref)
        identity = decode(mpn)
        if identity is not None:
            return identity.value
        if mpn in EXACT_PASSIVES:
            return EXACT_PASSIVES[mpn][0]
        if mpn in INDUCTORS:
            return INDUCTORS[mpn][0]
        return parse_engineering(self[ref])

    def tolerance(self, ref: str) -> float:
        self.used.add(ref)
        mpn = self.mpn(ref)
        identity = decode(mpn)
        if identity is not None and identity.tolerance is not None:
            return identity.tolerance / 100
        if mpn in EXACT_PASSIVES:
            return EXACT_PASSIVES[mpn][1]
        if mpn in INDUCTORS:
            return INDUCTORS[mpn][1]
        raise ValueError(f"no manufacturer tolerance data for {ref}: {mpn!r}")

    def temperature_tolerance(self, ref: str, low_c: float = -40,
                              high_c: float = 85) -> float:
        """Initial tolerance plus independent RT TCR drift from 25 C.

        This is the component temperature range used by the calculation. It
        does not establish an ambient or enclosure temperature rating.
        """
        identity = decode(self.mpn(ref))
        if identity is not None and identity.tcr_ppm is not None:
            return self.tolerance(ref) + identity.tcr_ppm*1e-6*max(abs(low_c-25), abs(high_c-25))
        match = re.match(r"RT\d{4}[BCDFPW][RK]([ABCDE])", self.mpn(ref))
        if not match:
            raise ValueError(f"no reviewed TCR code for {ref}: {self.mpn(ref)}")
        ppm = {"A": 5, "B": 10, "C": 15, "D": 25, "E": 50}[match[1]]
        return self.tolerance(ref) + ppm*1e-6*max(abs(low_c-25), abs(high_c-25))

    def environment_tolerance(self, ref: str, low_c: float = -40,
                              high_c: float = 85) -> float:
        """Independent initial, TCR, endurance and soldering-change screen.

        Vishay uses its 8000h endurance and soldering-heat requirements. Yageo
        RT uses its 1000h requirements. These sums are design stress envelopes,
        not a claim that dissimilar environmental tests establish service life.
        """
        mpn = self.mpn(ref)
        resistance = resistor(self, ref)
        if mpn.startswith(('TNPU', 'TNPW')):
            return self.temperature_tolerance(ref, low_c, high_c) + .001 + .02/resistance + .0002 + .01/resistance
        if mpn.startswith('RT'):
            return self.temperature_tolerance(ref, low_c, high_c) + .005 + .05/resistance + .005 + .05/resistance
        if mpn.startswith('RC'):
            # The reviewed RC1% envelope rounds initial, full TCR, endurance
            # and soldering change upward. It is also used by F12 branch ILIM.
            return .05
        raise ValueError(f'no reviewed endurance/assembly bounds for {ref}: {mpn}')

    def capacitors_on(self, net: str) -> list[str]:
        return sorted(ref for ref, pins in self.pins.items()
                      if ref.startswith("C") and net in pins.values()
                      and "GND" in pins.values()
                      and not self[ref].upper().startswith("DNP"))


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


def component_values(netlist: Path) -> NetlistValues:
    root = ET.parse(netlist).getroot()
    values = NetlistValues()
    for comp in root.findall(".//comp"):
        ref = comp.get("ref")
        if ref:
            values[ref] = comp.findtext("value") or ""
            fields = {field.get("name"): field.text or ""
                      for field in comp.findall("./fields/field")}
            values.parts[ref] = (fields.get("MPN", ""), comp.findtext("footprint") or "")
    for net in root.findall("./nets/net"):
        for node in net.findall("node"):
            values.pins.setdefault(node.get("ref"), {})[node.get("pin")] = net.get("name")
    return values


def resistor(values: dict[str, str], ref: str) -> float:
    try:
        if isinstance(values, NetlistValues):
            return values.number(ref)
        return parse_engineering(values[ref])
    except KeyError as exc:
        raise KeyError(f"required component {ref} is absent from exported netlist") from exc


def capacitor(values: dict[str, str], ref: str) -> float:
    return resistor(values, ref)


def divider_corners(top: float, bottom: float, top_tol: float, bottom_tol: float,
                    ref_low: float, ref_high: float,
                    feedback_leakage: float = 0) -> tuple[float, float]:
    """Feedback divider including independent resistor and leakage corners."""
    results = [vref * (1 + rt / rb) + leakage * rt
               for rt, rb, vref, leakage in itertools.product(
                   (top * (1-top_tol), top * (1+top_tol)),
                   (bottom * (1-bottom_tol), bottom * (1+bottom_tol)),
                   (ref_low, ref_high), (-feedback_leakage, feedback_leakage))]
    return min(results), max(results)


def buck_currents(vin: float, vout: float, load: float, inductance: float,
                  frequency: float) -> tuple[float, float, float, float]:
    """CCM ripple, peak, RMS inductor current and input capacitor RMS current."""
    if not 0 < vout < vin or min(inductance, frequency) <= 0 or load < 0:
        raise ValueError("buck model needs 0 < VOUT < VIN, L/f > 0 and load >= 0")
    duty = vout / vin
    ripple = vout * (1-duty) / (inductance * frequency)
    return (ripple, load + ripple/2, math.sqrt(load**2+ripple**2/12),
            math.sqrt(load**2*duty*(1-duty) + ripple**2*duty/12))


def boost_currents(vin: float, vout: float, load: float, inductance: float,
                   frequency: float, efficiency: float) -> tuple[float, float, float, float]:
    """Screening model: average, ripple, peak and RMS inductor current."""
    if not 0 < vin < vout or not 0 < efficiency <= 1:
        raise ValueError("boost model needs 0 < VIN < VOUT and 0 < efficiency <= 1")
    average = vout * load / (vin * efficiency)
    ripple = vin * (1-vin/vout) / (inductance*frequency)
    return average, ripple, average+ripple/2, math.sqrt(average**2+ripple**2/12)


def capacitor_retention_required(nominal: float, initial_tolerance: float,
                                 temperature_loss: float, aging_loss: float,
                                 required_effective: float) -> float:
    """Required bias retention, not an assertion that an MLCC achieves it."""
    return required_effective / (nominal * (1-initial_tolerance)
                                * (1-temperature_loss) * (1-aging_loss))


def direct_capacitance(boards: list[NetlistValues], net: str,
                       minimum: bool = False, polymer_only: bool = False) -> float:
    total = 0.0
    for values in boards:
        for ref in values.capacitors_on(net):
            if polymer_only and not values.mpn(ref).startswith(("T520", "T521", "T530", "EEH")):
                continue
            value = capacitor(values, ref)
            if minimum:
                value *= 1-values.tolerance(ref)
            total += value
    return total


def procurement_checks(board: str, values: NetlistValues) -> list[Check]:
    checks = []
    for ref in sorted(values.used):
        mpn, footprint = values.parts.get(ref, ("", ""))
        if decode(mpn) is not None:
            errors = identity_errors(values[ref], footprint, mpn)
        elif mpn in EXACT_PASSIVES:
            declared = parse_engineering(values[ref])
            errors = [] if math.isclose(declared, EXACT_PASSIVES[mpn][0], rel_tol=1e-9) else [
                f"manufacturer table value {EXACT_PASSIVES[mpn][0]:g} differs from label {declared:g}"]
        elif mpn in INDUCTORS:
            match = re.search(r"(?:^|\s)(\d+(?:\.\d+)?)\s*uH", values[ref], re.I)
            errors = [] if match and math.isclose(float(match[1])*1e-6, INDUCTORS[mpn][0], rel_tol=1e-9) else [
                "inductance label differs from the exact manufacturer's part table"]
        else:
            continue
        if errors:
            checks.append(Check(f"{board} {ref} procurement identity", len(errors),
                                "errors", 0, 0, f"{mpn}: {'; '.join(errors)}"))
    return checks


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
                                  tolerance: float | tuple[float, float, float], reference_min: float,
                                  reference_max: float,
                                  leakage_abs: float) -> tuple[float, float, float, float]:
    """Return UV-min/UV-max/OV-min/OV-max including both comparator leakages."""
    results: list[tuple[float, float]] = []
    tolerances = (tolerance,)*3 if isinstance(tolerance, (int, float)) else tolerance
    for top_scale, mid_scale, bottom_scale, reference, uv_leakage, ov_leakage in itertools.product(
        (1.0 - tolerances[0], 1.0 + tolerances[0]),
        (1.0 - tolerances[1], 1.0 + tolerances[1]),
        (1.0 - tolerances[2], 1.0 + tolerances[2]),
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
        Check(f"{name} UV {'falling' if name.startswith('LTC4418') else 'rising'}", uv, "V", *uv_limits,
              f"VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), {refs_text}"),
        Check(f"{name} OV rising", ov, "V", *ov_limits,
              f"VREF*(Rtop+Rmid+Rbot)/Rbot, {refs_text}"),
    ])

def system_5v_checks(r_top: float, r_bottom: float, hdmi_drop_v: float = .055 * .500) -> list[Check]:
    # Keep the 5.10 V system rail. The HDMI branch uses the TPS22948
    # maximum on-resistance across its full operating temperature range.
    nominal = 0.6 * (1.0 + r_top / r_bottom)
    minimum = 0.591 * (1.0 + r_top * 0.999 / (r_bottom * 1.001))
    maximum = 0.609 * (1.0 + r_top * 1.001 / (r_bottom * 0.999))
    return [
        Check("TPS56637 SYS_5V set-point", nominal, "V", 5.09, 5.11,
              "0.6V*(1+R40/R41); 5.10V target"),
        Check("TPS56637 SYS_5V worst-case minimum", minimum, "V", 5.00, 5.05,
              "0.591V*(1+R40*0.999/(R41*1.001))"),
        Check("TPS56637 SYS_5V worst-case maximum", maximum, "V", 5.15, 5.25,
              "0.609V*(1+R40*1.001/(R41*0.999))"),
        Check("HDMI +5V guaranteed connector minimum", minimum - hdmi_drop_v - 0.050,
              "V", 4.80, 5.25,
              "SYS_5V(min)-55mA*0.500ohm TPS22948(max at 125C)-0.050V board/connector allowance"),
    ]


def left_5v_checks(values: dict[str, str]) -> list[Check]:
    top, bottom = resistor(values, "R1712"), resistor(values, "R1713")
    if isinstance(values, NetlistValues) and values.mpn("U1703") == "LM706A0RRXR":
        minimum, maximum = divider_corners(top, bottom, values.environment_tolerance("R1712"),
                                           values.environment_tolerance("R1713"), .794, .806, 75e-9)
        return [
            Check("left LM706A0 USB_PORT_5V set-point", .8*(1+top/bottom), "V", 5.09, 5.18,
                  "0.8*(1+R1712/R1713); actual MPN resistance"),
            Check("left USB_PORT_5V minimum before branch losses", minimum, "V", 5.0, 5.25,
                  "0.794V; MPN initial/TCR/endurance/soldering corners; +/-75nA FB bias"),
            Check("left USB_PORT_5V maximum before branch losses", maximum, "V", 4.75, 5.25,
                  "0.806V; MPN initial/TCR/endurance/soldering corners; +/-75nA FB bias"),
        ]
    tt = values.tolerance("R1712") if isinstance(values, NetlistValues) else .001
    bt = values.tolerance("R1713") if isinstance(values, NetlistValues) else .001
    minimum, maximum = divider_corners(top, bottom, tt, bt, .591, .609)
    return [
        Check("left TPS56637 USB_PORT_5V set-point", .6*(1+top/bottom), "V", 5.09, 5.11,
              "0.6*(1+R1712/R1713); actual MPN resistance where decoded"),
        Check("left USB_PORT_5V minimum before branch losses", minimum, "V", 5.0, 5.25,
              "0.591V reference, independent MPN resistor tolerances"),
        Check("left USB_PORT_5V maximum before branch losses", maximum, "V", 4.75, 5.25,
              "0.609V reference, independent MPN resistor tolerances"),
    ]


def usb5_shunt_bounds(values: NetlistValues):
    """Effective Kelvin resistance, including the documented life allowance."""
    if 'RS1861' in values:
        for ref in ('RS1860','RS1861'):
            if values.mpn(ref)!='ERJ8CWFR010V':raise ValueError('unreviewed parallel USB5 shunt')
        nominal=1/sum(1/resistor(values,ref) for ref in ('RS1860','RS1861'))
        tolerance=.060  # initial1%,75ppm*105C,endurance3%,soldering1%, rounded upward
        # Sense RS1860 inner pad edges. A <=20uOhm power-branch mismatch
        # contributes <=0.11%; common power copper must be outside that span.
        return nominal,nominal*(1-tolerance)*.9989,nominal*(1+tolerance)*1.0011
    nominal=resistor(values,'RS1860');tolerance=values.tolerance('RS1860')+110e-6*65
    return nominal,nominal*(1-tolerance),nominal*(1+tolerance)


def lm706_checks(values: NetlistValues) -> list[Check]:
    inductance,ltol,isat,irms,dcr=INDUCTORS[values.mpn('L1701')]
    values.used.add('L1701')
    shunt,shunt_low,shunt_high=usb5_shunt_bounds(values)
    minimum_limit=.050/shunt_high;maximum_limit=.062/shunt_low
    rt=resistor(values,'R1860')
    if rt not in (22100,49900):raise ValueError('USB5 RT has no reviewed exact frequency-table point')
    fmin={22100:850e3,49900:400e3}[rt]/(1+values.environment_tolerance('R1860'))
    vout=left_5v_checks(values)[2].value
    modern='RS1861' in values;load=6.5 if modern else 5.5;vin=24.1 if modern else 22
    lmin=inductance*(1-ltol)*.70
    ripple,peak,rms,_=buck_currents(vin,vout,load,lmin,fmin)
    bank_floor=sum(capacitor(values,ref)*(1-values.tolerance(ref))*.80*.80*.95 for ref in ('C1864','C1865'))
    bank_ceiling=sum(capacitor(values,ref)*(1+values.tolerance(ref))*1.10*1.20*1.35 for ref in ('C1864','C1865'))
    checks=[
        Check('LM706A0 full-load peak versus current-limit minimum',peak,'A',0,minimum_limit,
              f'{vin}V,{load}A,L tolerance/-30% bias screen,fSW minimum plus RT tolerance/TCR; shunt initial/TCR/endurance/soldering/layout included for parallel ERJ pair'),
        Check('LM706A0 peak current-limit headroom',minimum_limit/peak,'x',1.25,math.inf,
              '50mV/(effective shunt maximum)/Ipeak;25% startup/load-step design margin'),
        Check('USB5 inductor RMS current screen',rms,'A',0,irms,
              'actual MPN; compare25C/20C-rise characterization, not installed thermal rating'),
        Check('USB5 inductor peak current screen',peak,'A',0,isat,
              'actual MPN; compare25C Isat30% characterization'),
        Check('USB5 current-limit high corner',maximum_limit,'A',0,isat,
              '62mV/effective shunt minimum; includes initial/TCR/endurance/layout on ERJ pair'),
        Check('USB5 short-circuit peak screen',maximum_limit+vin*(150e-9 if modern else 75e-9)/lmin,'A',0,isat*(.8 if modern else 1),
              'maximum threshold + VIN*150ns/Lmin for the6.5A build;150ns and20% hot-Isat reduction are explicit stress assumptions, not guaranteed limits'),
        Check('USB5 added reservoir compound environment floor',bank_floor*1e6,'uF',300,1500,
              'KEMET initial,-20% endurance,-20% temperature,-5% humidity multiplied as a stress envelope; not a cumulative-life guarantee'),
        Check('USB5 added reservoir compound environment ceiling',bank_ceiling*1e6,'uF',300,1500,
              'initial,+10% endurance,+20% temperature,+35% humidity stress; model spans300..1500uF'),
    ]
    if modern:
        rmax=.010*1.060
        shunt_power=(rms/2)**2*rmax*1.0022
        checks.append(Check('USB5 per-shunt power at maximum resistance',shunt_power,'W',0,1*(125-110)/(125-70),
                            'two ERJ8CW10mOhm parts; require case<=110C,1W rating derated from70C to125C'))
        checks.append(Check('USB5 winding copper-loss screen at125C',rms*rms*dcr*(1+.00393*100),'W',0,2,
                            'maximum DCR at25C with copper temperature coefficient; core loss/proximity/PCB cooling remain unmeasured'))
    else:
        checks.append(Check('USB5 shunt nominal full-load power',rms*rms*shunt,'W',0,.5,'Irms^2*RS1860; thermal and pulse derating remain'))
    return checks


def sys5_voltage_checks(values: NetlistValues) -> list[Check]:
    top, bottom = resistor(values, 'R40'), resistor(values, 'R41')
    lo, hi = divider_corners(top, bottom, values.environment_tolerance('R40'),
                             values.environment_tolerance('R41'), .794, .806, 75e-9)
    return [
        Check('LM706A0 SYS_5V set-point', .8*(1+top/bottom), 'V', 5.09, 5.12,
              '0.8V reference; actual R40/R41 order codes'),
        Check('LM706A0 SYS_5V DC minimum', lo, 'V', 5.0, 5.25,
              '0.794V reference; independent initial/TCR/endurance/soldering corners;75nA FB bias'),
        Check('LM706A0 SYS_5V DC maximum', hi, 'V', 5.0, 5.23,
              '0.806V reference; independent initial/TCR/endurance/soldering corners;75nA FB bias;20mV ripple reserved'),
    ]


def sys5_checks(values: NetlistValues) -> list[Check]:
    """Complete 4.5A bank startup screen, separate from source admission."""
    if values.mpn('U6') != 'LM706A0RRXR':
        raise ValueError('SYS5 enabled bank requires the reviewed externally compensated regulator')
    for ref in ('RS2360', 'RS2361'):
        if values.mpn(ref) != 'ERJ8CWFR010V':
            raise ValueError('unreviewed SYS5 shunt')
    rs = 1/sum(1/resistor(values, ref) for ref in ('RS2360', 'RS2361'))
    rslow, rshigh = rs*.940*.9989, rs*1.060*1.0011
    limit_min, limit_max = .050/rshigh, .062/rslow
    l, ltol, isat, irms, dcr = INDUCTORS[values.mpn('L4')]
    values.used.add('L4')
    lmin = l*(1-ltol)*.70
    fmin = 850e3*22100/resistor(values, 'R2360')/(1+values.environment_tolerance('R2360'))
    vhi = sys5_voltage_checks(values)[2].value
    ripple, peak, rms, _ = buck_currents(24.1, vhi, 4.5, lmin, fmin)
    # This is the full model envelope, including directly connected bypasses
    # and every enabled branch. It is not merely the fitted local label sum.
    ctotal_max = (80+500+300)*1e-6
    startup = ctotal_max*vhi/1.9e-3
    reservoir = capacitor(values, 'C2364')
    reservoir_floor = reservoir*(1-values.tolerance('C2364'))*.80*.80*.95
    reservoir_ceiling = reservoir*(1+values.tolerance('C2364'))*1.10*1.20*1.35
    branch_max = sum(22.98/(resistor(values, ref)/1000*.95)**.94
                     for ref in ('R773', 'R252', 'R388'))
    branch_max += 2.2*1650/(resistor(values, 'R2301')*(1-values.environment_tolerance('R2301')))+.350
    return [
        *sys5_voltage_checks(values),
        Check('SYS5 combined branch current-limit high corners', branch_max, 'A', 0, 4.5,
              'TPS2553D Eq1 with ±5% R including life; TPS25947 2.2A table maximum with RT corners; TPS22948 350mA maximum; remaining allowance covers bias'),
        Check('SYS5 25-percent steady peak margin', limit_min/peak, 'x', 1.25, math.inf,
              '4.5A plus ripple;L -20%/-30% stress;0.85MHz minimum and RT drift;shunt initial/TCR/endurance/soldering/layout'),
        Check('SYS5 25-percent startup peak margin', limit_min/(peak+startup), 'x', 1.25, math.inf,
              'full 880uF model ceiling charged to VOUTmax in1.9ms minimum soft start, concurrent4.5A load and ripple'),
        Check('SYS5 high-limit fault peak screen', limit_max+24.1*150e-9/lmin, 'A', 0, isat*.8,
              '62mV/shunt minimum plus150ns stress;20% hot-Isat reduction is a screen, not a guaranteed fault bound'),
        Check('SYS5 inductor RMS screen', rms, 'A', 0, irms,
              '25C/20C-rise manufacturer characterization; installed thermal loss remains to be measured'),
        Check('SYS5 winding copper-loss screen at125C', rms*rms*dcr*(1+.00393*100), 'W', 0, .5,
              'maximum DCR and copper TCR; excludes core and switching losses'),
        Check('SYS5 per-shunt continuous power', (rms/2)**2*.010*1.060*1.0022, 'W', 0, (125-110)/(125-70),
              'ERJ8CW1W derated to110C; pair mismatch allowance included'),
        Check('SYS5 polymer environment floor', reservoir_floor*1e6, 'uF', 90, 500,
              'initial,-20% endurance,-20% temperature,-5% humidity stress; model envelope90..500uF'),
        Check('SYS5 polymer environment ceiling', reservoir_ceiling*1e6, 'uF', 90, 500,
              'initial,+10% endurance,+20% temperature,+35% humidity stress; not a cumulative-life guarantee'),
    ]


def sys3_distribution_checks(values: NetlistValues) -> list[Check]:
    lo, hi = divider_corners(resistor(values, 'R43'), resistor(values, 'R44'),
                             values.environment_tolerance('R43'), values.environment_tolerance('R44'),
                             .591, .609)
    return [
        Check('SYS3 left 2A qualified distribution minimum', lo-.02-.01-2*(.093+.010), 'V', 3.0, 3.465,
              'initial/TCR/endurance/soldering;20mV ripple,10mV ground,93mOhm positive loom and10mOhm board loop; these path limits require assembly qualification'),
        Check('SYS3 maximum including ripple allocation', hi+.020, 'V', 3.0, 3.465,
              'initial/TCR/endurance/soldering and20mV positive ripple allocation'),
    ]


def aon_window_checks(values: NetlistValues) -> list[Check]:
    refs=('R795','R796','R797');r=[resistor(values,ref) for ref in refs]
    tolerance=tuple(values.environment_tolerance(ref) for ref in refs)
    if values.mpn('U718')!='TPS26600RHFR':
        fall=three_resistor_window_corners(*r,tolerance,1.076,1.116,.1e-6)
        return [Check('AON OV recovery covers a21V source',fall[2],'V',21,25,
                      'TPS25947 falling threshold and both leakages; old22.4V ladder does not cover21V recovery')]
    uv=three_resistor_window_corners(*r,tolerance,1.175,1.225,.1e-6)
    ov=three_resistor_window_corners(*r,tolerance,1.17,1.225,.1e-6)
    fall=three_resistor_window_corners(*r,tolerance,1.085,1.125,.1e-6)
    rlimit=1/sum(1/resistor(values,ref) for ref in ('R798','R799'))
    rtol=max(values.environment_tolerance(ref) for ref in ('R798','R799'))
    return [
        Check('AON UV rising minimum',uv[0],'V',5.5,6.5,'TPS26600 UV minimum, both100nA leakages and RT initial/TCR corners'),
        Check('AON UV rising maximum',uv[1],'V',5.5,6.5,'TPS26600 UV maximum with RT corners'),
        Check('AON OV rising maximum versus25V capacitors',ov[3],'V',21,25,'1.225V OVP comparator,both100nA leakages,initial/TCR; transient overshoot excluded'),
        Check('AON OV recovery covers21V source',fall[2],'V',21,25,'1.085V falling threshold,both100nA leakages,initial/TCR'),
        Check('AON minimum current limit',1.425*8000/(rlimit*(1+rtol)),'A',1.35,1.6,'8k realized by parallel16k parts;1.425A table minimum plus resistor corners'),
        Check('AON maximum current limit',1.575*8000/(rlimit*(1-rtol)),'A',1.4,1.65,'1.575A table maximum plus resistor corners'),
        Check('AON slew capacitor effective floor',capacitor(values,'C799')*(.95-30e-6*100)*1e9,'nF',10,100,
              'KEMET C0G5% plus30ppm/C over100C; no class-II dc-bias or aging factor'),
    ]


def aon_converter_checks(values: NetlistValues) -> list[Check]:
    lo,hi=divider_corners(resistor(values,'R35'),resistor(values,'R36'),
                         values.environment_tolerance('R35'),values.environment_tolerance('R36'),.581,.611)
    nominal=.596*(1+resistor(values,'R35')/resistor(values,'R36'))
    mpn=values.mpn('L3');inductance,tol,isat,irms,dcr=INDUCTORS[mpn]
    lmin=inductance*(1-tol)*.80
    ripple,peak,rms,_=buck_currents(24.1,hi,1.5,lmin,390e3*.94)
    isat30=6.2 if mpn=='XGL6030-103MEC' else 4.5
    return [
        Check('TPS54202 MCU_3V3 set-point',nominal,'V',3.25,3.35,'actual R35/R36 order codes;0.596V reference'),
        Check('TPS54202 MCU_3V3 minimum',lo,'V',3.135,3.465,'0.581V reference; independent initial, -40..85C TCR, endurance and soldering corners'),
        Check('TPS54202 MCU_3V3 maximum',hi,'V',3.135,3.465,'0.611V reference; independent initial, -40..85C TCR, endurance and soldering corners'),
        Check('TPS54202 1.5A peak versus high-side minimum limit',peak,'A',0,2.5,
              '24.1V,L -20% initial/-20% bias stress,390kHz minimum center frequency and -6% spread spectrum'),
        Check('TPS54202 1.5A valley versus low-side minimum limit',1.5-ripple/2,'A',0,2.0,'minimum low-side limit2A'),
        Check('AON inductor RMS screen',rms,'A',0,irms,'manufacturer25C/20C-rise characterization; installed temperature remains unmeasured'),
        Check('AON high-limit fault peak screen',3.9+28*150e-9/lmin,'A',0,isat30*.80,
              '3.9A maximum high-side limit plus28V*150ns/Lmin;150ns and20% hot-Isat reduction are stress assumptions;28V is not an allowed AON-path voltage'),
        Check('AON inductor copper-loss screen at125C',rms*rms*dcr*(1+.00393*100),'W',0,.30,
              'maximum DCR with copper TCR; excludes core/switch/PCB losses'),
        Check('TPS54202 nominal local output capacitance',(capacitor(values,'C39')+capacitor(values,'C291'))*1e6,'uF',43,45,
              'TI3.3V reference local bank; additional AON bypasses and exact bias/load-step response remain in the qualification budget'),
        Check('TPS54202 feed-forward capacitor',capacitor(values,'C292')*1e12,'pF',53,59,'TI3.3V recommended56pF'),
    ]


def endpoint_checks(values: NetlistValues) -> list[Check]:
    if values.mpn('U773')!='LM706A0RRXR':return []
    for ref in ('RS2280','RS2281'):
        if values.mpn(ref)!='ERJ8CWFR013V':raise ValueError('unreviewed endpoint shunt')
    rs=1/sum(1/resistor(values,ref) for ref in ('RS2280','RS2281'))
    rslow=rs*.940*.9989;rshigh=rs*1.060*1.0011
    limit_min=.050/rshigh;limit_max=.062/rslow
    vlo,vhi=divider_corners(resistor(values,'R785'),resistor(values,'R786'),
                            values.environment_tolerance('R785'),values.environment_tolerance('R786'),.794,.806,75e-9)
    l,ltol,isat,irms,dcr=INDUCTORS[values.mpn('L1702')];lmin=l*(1-ltol)*.7
    fmin=850e3*22100/resistor(values,'R2280')/(1+values.environment_tolerance('R2280'))
    ripple,peak,rms,_=buck_currents(24.1,vhi,5.0,lmin,fmin)
    ctmin=sum(capacitor(values,ref) for ref in ('C833','C2289'))*(.95-.003)
    rise_fast=(vhi*(.27*ctmin*1e12+25.5)+24.9)*.5e-6
    inrush=2e-3*.8*vhi/rise_fast
    return [
        Check('endpoint minimum regulator voltage',vlo,'V',3.3,3.465,'LM0.794V;actual divider tolerance/TCR;75nA bias'),
        Check('endpoint maximum including20mV ripple allocation',vhi+.02,'V',3.135,3.465,'static upper plus positive ripple allocation'),
        Check('endpoint 25-percent steady peak margin',limit_min/peak,'x',1.25,math.inf,'5A load;0.85MHz table minimum with RT drift;L -20%/-30% stress;shunt initial/TCR/endurance/soldering/layout'),
        Check('endpoint 25-percent peak margin including controlled inrush',limit_min/(peak+.4),'x',1.25,math.inf,'5A module draw plus0.4A inrush allowance plusinductor ripple'),
        Check('endpoint2mF startup current screen',inrush,'A',0,.4,'two22n C0G caps at tolerance/TCR floor;TPS22992 rise-time equation with2x-fast stress, not guaranteed silicon timing'),
        Check('endpoint switch including startup allowance',5+.4,'A',0,6,'TPS22992S maximum continuous current6A; selected endpoint operating envelope5A'),
        Check('endpoint high-limit fault peak screen',limit_max+24.1*150e-9/lmin,'A',0,isat*.8,'62mV/shunt minimum plus150ns delay;20% hot-Isat stress;SCC limiter remains separately qualified'),
        Check('endpoint inductor RMS screen',rms,'A',0,irms,'compare25C/20C-rise reference; installed switching/core loss remains'),
        Check('endpoint guaranteed path damping floor',resistor(values,'R2292')*.940*1000,'mOhm',9,20,
              'ERJ8CW initial/TCR/endurance stress; no minimum switch RON is assumed'),
        Check('endpoint remaining common-path voltage allowance',(vlo-.02-5*.015-3.5*resistor(values,'R2292')*1.060-3.135)*1000,'mV',0,250,
              'regulator low-20mV ripple-5A*15mOhm switch-3.5A*NVMe damping resistor-3.135V; residual covers NVMe copper and contacts'),
        Check('NVMe damping resistor steady dissipation',3.5**2*resistor(values,'R2292')*1.060,'W',0,(125-100)/(125-70),
              'require resistor case<=100C; short-circuit pulse and recovery remain hardware qualification'),
        Check('endpoint regulator input resistance per shunt power',(rms/2)**2*.013*1.060*1.0022,'W',0,(125-110)/(125-70),
              'ERJ8CW1W derated to110C;parallel balance allowance included'),
    ]


def mu_voltage_corners(values: NetlistValues) -> tuple[float, float]:
    refs = ('R752', 'R753')
    top = sum(resistor(values, ref) for ref in refs)
    top_tolerance = sum(resistor(values, ref)*values.environment_tolerance(ref)
                        for ref in refs)/top
    return divider_corners(top, resistor(values, 'R754'), top_tolerance,
                           values.environment_tolerance('R754'), 1.188, 1.212, 100e-9)


def mu_shunt_bounds(values: NetlistValues) -> tuple[float, float]:
    if values.mpn('RS750') not in ('ERJ8BWFR015V','ERJ8CWFR013V'):
        raise ValueError('unreviewed Mu current-limit shunt')
    # CW:1% initial+75ppm*105C+3% endurance+1% soldering, rounded to6%.
    # The old BW part needs7.5% for its larger positive-only200ppm TCR.
    tolerance=.060 if values.mpn('RS750')=='ERJ8CWFR013V' else .075
    return (resistor(values, 'RS750')*(1-tolerance)*.998,
            resistor(values, 'RS750')*(1+tolerance)*1.002)


def mu_operating_checks(values: NetlistValues) -> list[Check]:
    inductance, tolerance, isat, irms, dcr = INDUCTORS[values.mpn('L750')]
    values.used.add('L750')
    _, vout = mu_voltage_corners(values)
    shunt_low, shunt_high = mu_shunt_bounds(values)
    frequency = 20e9/resistor(values, 'R756')*.90*.93/(1+values.environment_tolerance('R756'))
    lmin = inductance*(1-tolerance)*.70
    average, ripple, peak, rms = boost_currents(8.55, vout, 3.3, lmin, frequency, .85)
    clamp_rms = math.sqrt(9**2+ripple**2/12)
    return [
        Check('Mu3.3A allocation below output-limit minimum', .048/shunt_high, 'A', 3.3, math.inf,
              'actual shunt; initial/TCR/endurance/soldering and0.2% Kelvin allowance;48mV threshold minimum'),
        Check('Mu3.3A average-current margin screen', 7/average, 'x', 1.25, math.inf,
              '8.55V input,85% efficiency requirement;7A minimum is specified at VIN8V/VOUT20V/400kHz and must be confirmed at12V output'),
        Check('Mu3.3A inductor RMS screen', rms, 'A', 0, irms,
              'actual MPN; compare25C/20C-rise characterization, not an installed temperature guarantee'),
        Check('Mu average-clamp inductor RMS screen', clamp_rms, 'A', 0, irms,
              '9A maximum average-current table point plus ripple; operating allocation remains3.3A output'),
        Check('Mu typical peak-clamp fault screen', 13+24.1*150e-9/lmin, 'A', 0, isat*.8,
              '13A high-side clamp is typical only;150ns delay and20% hot-Isat reduction are stress assumptions; no guaranteed peak-clamp maximum is published'),
        Check('Mu output shunt dissipation at3.3A', 3.3**2*shunt_high, 'W', 0, (125-110)/(125-70),
              '1W CW resistor derated to case110C; fault pulse energy and installed case temperature remain unmeasured'),
        Check('Mu COMP capacitor nominal identity', capacitor(values, 'C771')*1e9, 'nF', 329, 331,
              'TDK330nF50V0603; finite model covers210..500nF effective including drift'),
    ]


def source_window_checks(name: str, values: NetlistValues, refs: tuple[str, str, str],
                         ltc4418: bool = False) -> list[Check]:
    top, middle, bottom = (resistor(values, ref) for ref in refs)
    tolerance = tuple(values.environment_tolerance(ref) for ref in refs)
    # Both pin leakages are varied independently in the three-resistor network.
    vlow, vhigh, leakage = (.985, 1.015, 10e-9) if ltc4418 else (1.176, 1.224, 150e-9)
    _, _, ovmin, ovmax = three_resistor_window_corners(
        top, middle, bottom, tolerance, vlow, vhigh, leakage)
    uvlow = 1.000 if ltc4418 else 1.176
    uvhigh = 1.060 if ltc4418 else 1.224
    uvmin, uvmax, _, _ = three_resistor_window_corners(
        top, middle, bottom, tolerance, uvlow, uvhigh, leakage)
    resetlow, resethigh = (.940, 1.000) if ltc4418 else (1.09, 1.15)
    _, _, resetmin, _ = three_resistor_window_corners(
        top, middle, bottom, tolerance, resetlow, resethigh, leakage)
    return [
        Check(f"{name} 20V-source startup UV maximum", uvmax, "V", 0, 19.0,
              f"{'/'.join(refs)}; IC, asymmetric initial/TCR/endurance/soldering corners, "
              "both leakages and fixed hysteresis"),
        Check(f"{name} 20V-source OV recovery minimum", resetmin, "V", 21.0, 24.0,
              "must recover with source at 20V+5%; both comparator leakages included"),
        Check(f"{name} OV cutoff maximum", ovmax, "V", 21.0, 24.0,
              "DC trip must remain below BQ25798 24V operating limit; delay/overshoot excluded"),
    ]


def extended_checks(center: NetlistValues, left: NetlistValues,
                    right: NetlistValues) -> list[Check]:
    """Independent desktop screens added after the 2026-09-07 audit.

    A passing current screen uses the explicit operating point and manufacturer
    typical frequency/Isat where stated. It is not a thermal or loop signoff.
    """
    checks = left_5v_checks(left)
    for name, values, refs in [
        ("left PD1 selector", left, ("R2140", "R2141", "R2142")),
        ("center PD1 selector", center, ("R730", "R731", "R732")),
        ("center PD2 selector", center, ("R741", "R742", "R743")),
        ("center stage2 selector", center, ("R744", "R745", "R746")),
    ]:
        checks.extend(source_window_checks(name, values, refs, ltc4418=True))
    for name, values, refs in [
        ("left PD1 eFuse", left, ("R2080", "R2081", "R2082")),
        ("right PD2 eFuse", right, ("R2090", "R2091", "R2092")),
    ]:
        checks.extend(source_window_checks(name, values, refs))

    for name, values, top_ref, bottom_ref, lref, load in [
        ("SYS_5V", center, "R40", "R41", "L4", 6.0),
        ("SYS_3V3", center, "R43", "R44", "L5", 6.0),
        ("PCIE_3V3_IN", center, "R785", "R786", "L1702", 6.0),
        ("USB_PORT_5V", left, "R1712", "R1713", "L1701", 5.5),
    ]:
        if ((name == "USB_PORT_5V" and values.mpn("U1703") == "LM706A0RRXR")
                or (name == "PCIE_3V3_IN" and values.mpn("U773") == "LM706A0RRXR")
                or (name == "SYS_5V" and values.mpn("U6") == "LM706A0RRXR")):
            continue
        top, bottom = resistor(values, top_ref), resistor(values, bottom_ref)
        low, high = divider_corners(top, bottom, values.environment_tolerance(top_ref),
                                   values.environment_tolerance(bottom_ref), .591, .609)
        inductor_mpn = values.mpn(lref)
        if inductor_mpn not in INDUCTORS:
            raise ValueError(f"unreviewed {name} inductor: {inductor_mpn}")
        inductance, ltol, isat, irms, dcr = INDUCTORS[inductor_mpn]
        values.used.add(lref)
        # TPS56637 only publishes a typical 500kHz frequency. This is a stated
        # design screen at VIN=22V, not a guaranteed worst-frequency corner.
        ripple, peak, rms, _ = buck_currents(22, high, load, inductance*(1-ltol), 500e3)
        checks.extend([
            Check(f"{name} DC minimum", low, "V", 4.75 if high > 4 else 3.135,
                  5.25 if high > 4 else 3.465, "0.591V, independent manufacturer initial/TCR resistor corners"),
            Check(f"{name} DC maximum", high, "V", 4.75 if high > 4 else 3.135,
                  5.25 if high > 4 else 3.465, "0.609V, independent manufacturer initial/TCR resistor corners"),
            Check(f"{name} peak current screen", peak, "A", 0, isat,
                  f"22V input, {load:g}A load, L -20%, 500kHz typical; {inductor_mpn} 25C Isat30%"),
            Check(f"{name} RMS current screen", rms, "A", 0, irms,
                  f"sqrt(Iout^2+dIL^2/12); {inductor_mpn} 25C/20C-rise reference"),
            Check(f"{name} guaranteed valley-limit load screen", load-ripple/2, "A", 0, 6.3,
                  "Iout-dIL/2 versus TPS56637 minimum valley current limit; frequency remains typical"),
        ])

    core_top, core_bottom = resistor(left, "R1705"), resistor(left, "R1706")
    core_min, core_max = divider_corners(core_top, core_bottom, left.environment_tolerance("R1705"),
                                         left.environment_tolerance("R1706"), .594, .606, 50e-9)
    checks.extend([
        Check("left USB7206C core minimum", core_min, "V", 1.1, 1.2,
              "TPS62823 0.594V reference, resistor tolerance, 50nA FB leakage"),
        Check("left USB7206C core maximum", core_max, "V", 1.1, 1.2,
              "TPS62823 0.606V reference, resistor tolerance, 50nA FB leakage"),
    ])
    polymer_min = direct_capacitance([center, left, right], "/USB_PORT_5V", True, True)
    if left.mpn("U1703") == "LM706A0RRXR":
        checks.extend(lm706_checks(left))
        usb5_low=left_5v_checks(left)[1].value
        for board,jref,base,current in [(left,'J22',1780,.9),(left,'J23',1740,.9),(right,'J12',1760,.5)]:
            for ref,mpn in [(f'U{base}','TPS2553DDBVR'),(f'U{base+1}','TPS25810RVCR'),
                            (f'U{base+3}','TPD1S514-1YZR')]:
                if board.mpn(ref)!=mpn:raise ValueError(f'unreviewed {jref} series switch: {ref}')
            if any(board.pins[f'U{base+1}'].get(pin)!='GND' for pin in ('7','8')):
                raise ValueError(f'{jref} source-current advertisement changed; recalculate voltage/current budget')
            branch_input=current+.25+.025
            remaining=usb5_low-.020-branch_input*.135-current*(.046+.050)-4.75
            checks.append(Check(f'{jref} remaining USB-default voltage-drop allowance',remaining*1000,'mV',0,500,
                                f'USB5 minimum-20mV ripple-{branch_input:g}A*TPS2553 135mOhm-{current:g}A*(TPS25810 46mOhm at85C+TPD1S514 50mOhm at25C)-4.75V; VCONN250mA+bleed25mA included; residual covers copper, contacts and unbounded TPD hot RON'))
    else:
        checks.append(Check("USB_PORT_5V direct polymer bank versus published LC range",
                            polymer_min*1e6, "uF", 0, 100,
                            "connected polymers only, MPN initial tolerance; TPS56637 Table4 max100uF. "
                            "Exceeding the table requires a separate loop design, not an assertion of instability."))

    checks.extend(aon_window_checks(center))
    checks.extend(endpoint_checks(center))
    checks.extend(mu_operating_checks(center))
    checks.extend(sys3_distribution_checks(center))
    sys3_cap_max = sum(capacitor(values, ref)*(1+values.tolerance(ref))*1.15
                       for values in (center, left, right)
                       for ref in values.capacitors_on('/SYS_3V3'))
    # U55's switched HDMI-side bypass joins SYS_3V3 when enabled.
    sys3_cap_max += capacitor(right, 'C161')*(1+right.tolerance('C161'))*1.15
    checks.append(Check('SYS3 complete enabled bank upper bound', sys3_cap_max*1e6, 'uF', 20, 100,
                        'all three native netlists, actual MPN initial tolerance and+15% temperature; DC bias ignored on the upper bound; includes C161 behind U55'))

    # The idealized ILIM setting is not the same thing as guaranteed measured
    # input-current regulation. Do not turn the 3A nominal label into a limit.
    rt, rb = resistor(center, "R17"), resistor(center, "R190")
    settings = []
    for top, bottom, regn, leakage in itertools.product(
        (rt*(1-center.environment_tolerance("R17")), rt*(1+center.environment_tolerance("R17"))),
        (rb*(1-center.environment_tolerance("R190")), rb*(1+center.environment_tolerance("R190"))),
        (4.8, 5.2), (-1.5e-6, 1.5e-6)):
        settings.append((regn*bottom/(top+bottom)-leakage*top*bottom/(top+bottom)-1)/.8)
    checks.append(Check("BQ25798 2.50A bootstrap command below ILIM setting floor",
                        min(settings)-2.50, "A", 0, 1,
                        "REGN4.8-5.2V, MPN resistor corners, +/-1.5uA leakage; ADC/current-loop errors remain"))
    if 'R2262' in center:
        output_rmax=resistor(center,'R2262')*(1+center.environment_tolerance('R2262'))
        checks.append(Check('charger-enable gate when AND is unpowered',output_rmax*10.1e-6,'V',0,.1,
                            '(10uA LVC Ioff+100nA MOS gate leakage)*R2262(high); full isolated-link screens run against the BMS netlist'))

    mu_mpn = center.mpn("L750")
    if mu_mpn not in INDUCTORS:
        raise ValueError(f"unreviewed Mu inductor {mu_mpn}")
    inductance, ltol, isat, irms, _ = INDUCTORS[mu_mpn]
    center.used.add("L750")
    frequency = 20e9/resistor(center, "R756")
    # +/-10% is a conservative interpolation from TI's specified clock
    # endpoints, not a guaranteed specification at 49.9k. DITH is fitted.
    fmin = frequency*.90*.93/(1+center.environment_tolerance("R756"))
    lscreen = inductance*(1-ltol)*.70
    checks.append(Check("TPS552892 minimum L with tolerance and 30-percent bias screen",
                        lscreen*1e6, "uH", 1.2/fmin*1e6, math.inf,
                        f"{mu_mpn}; Lnom*(1-tolerance)*0.70; requires L>1.2/fSW; "
                        "clock -10%, R tolerance, dither -7%; typical bias boundary only"))
    mu_max = .052/mu_shunt_bounds(center)[0]
    mu_vmax = mu_voltage_corners(center)[1]
    average, ripple, peak, rms = boost_currents(8.55, mu_vmax, mu_max, lscreen, fmin, .90)
    checks.extend([
        Check("Mu average inductor current screen at 8.55V", average, "A", 0, 7.0,
              "Vout(max)*Ilimit(max)/(8.55V*90% assumed efficiency); 7A IC minimum average limit"),
        Check("Mu peak inductor current screen at 8.55V", peak, "A", 0, isat,
              "average+dIL/2; tolerance/bias/frequency screen versus 25C Isat reference"),
        Check("Mu RMS inductor current screen at 8.55V", rms, "A", 0, irms,
              "sqrt(Iavg^2+dIL^2/12); compare 25C/20C-rise reference, not installed temperature"),
    ])
    for name, values in [("center", center), ("left", left), ("right", right)]:
        checks.extend(procurement_checks(name, values))
    return checks


def thermal_supply_budget(feed_ohms: float, values=None) -> dict[str, float]:
    """Raw thermal supply sizing, with explicit non-guaranteed IC allowances.

    TI limits: TLV1864 850nA/ch; AUP2G126 0.9uA ICC, 50uA/data input and
    120uA/OE input delta ICC; ISO7041 395.7uA side1 at 1Mbps, all channels;
    TLV803E 1uA. These simultaneous states overcount real static operation.
    TPS709 gives loaded ground current as typical, not a maximum: allocate
    its 350uA/150mA-load characterization plus 100uA additional reserve here.
    The allocation must be measured; this function does not relabel it a limit.
    """
    v=3.393; tr=.001+25e-6*65+.010+.1/10000; tc=.05
    defaults={'R2201':9.53e3,'R2230':100e3,'R2231':100e3,'R2232':100e3,
              'R2233':1e6,'R2235':100e3,'R2238':100e3}
    for cell in range(3):
        defaults.update({f'R{2210+3*cell}':100e3,f'R{2211+3*cell}':10e3,f'R{2212+3*cell}':10e3})
    for index,top in enumerate([243e3,634e3,147e3,845e3]):
        defaults[f'R{2240+2*index}']=top;defaults[f'R{2241+2*index}']=499e3
    def r(ref):return resistor(values,ref) if values is not None else defaults[ref]
    passive=v/(r('R2201')*(1-tr))
    passive+=sum(v/(sum(r(f'R{2210+3*cell+j}') for j in range(3))*(1-tr)) for cell in range(3))
    passive+=sum(v/(r(ref)*(1-tc)) for ref in ['R2230','R2231','R2232','R2233','R2235','R2238'])
    passive+=sum(v/((r(f'R{2240+2*i}')+r(f'R{2241+2*i}'))*(1-tr)) for i in range(4))
    ic_screen=12*.85e-6+.9e-6+2*50e-6+2*120e-6+395.7e-6+1e-6+3e-6
    loaded_ldo_allowance=350e-6;additional_allowance=100e-6
    demand=passive+ic_screen+loaded_ldo_allowance+additional_allowance
    rmax=feed_ohms*(1+tc);rmin=feed_ohms*(1-tc)
    return {'passive_current_max_a':passive,'ic_current_screen_a':ic_screen,
            'loaded_ldo_ground_current_allowance_a':loaded_ldo_allowance,
            'additional_allowance_a':additional_allowance,'demand_screen_a':demand,
            'available_at_8v4_a':(8.4-(v+1))/rmax,
            'regulator_input_min_v':8.4-demand*rmax,
            'short_13v8_a':13.8/rmin,'short_13v8_w':13.8**2/rmin,
            'short_21v_a':21/rmin,'short_21v_w':21**2/rmin,
            'resistor_derated_85c_w':.75*(155-85)/(155-70)}


def bms_thermal_checks(values) -> list[Check]:
    if values.mpn('R2200')!='RC2010FK-071KL':
        raise ValueError('thermal supply sizing requires the reviewed RC2010 1k/0.75W part')
    budget=thermal_supply_budget(resistor(values,'R2200'),values)
    return [
        Check('thermal raw supply at explicit maximum-demand screen',budget['regulator_input_min_v'],'V',4.393,8.4,
              '8.4V - R2200(high)*sum(passives, TI IC screens, 350uA loaded-LDO and100uA extra allowances); loaded LDO maximum remains unmeasured'),
        Check('thermal raw feed short dissipation at13.8V',budget['short_13v8_w'],'W',0,budget['resistor_derated_85c_w'],
              '13.8^2/R2200(low); RC2010 0.75W derated from70C to85C; includes1%+100ppm*65C'),
        Check('thermal raw feed short dissipation at21V fault screen',budget['short_21v_w'],'W',0,budget['resistor_derated_85c_w'],
              '21^2/R2200(low); branch fault screen only, never an allowed cell voltage'),
    ]


def bms_control_budget(values: NetlistValues, center: NetlistValues | None = None):
    """Three-domain supply and logic screens for the isolated five-wire link.

    The 20uA combined output-leakage, 50mV wire allocations, 350uA loaded
    TPS709 ground current and 100uA reserves are explicit qualification
    allowances. The LVC data sheet does not specify powered output leakage.
    Open-ground states preserve DC isolation; they do not guarantee valid logic.
    """
    # RC initial, full-category TCR, endurance and assembly-change stress.
    # Separate qualification tests do not establish a cumulative-life guarantee.
    tolerance=.05
    def lo(ref):return resistor(values,ref)*(1-tolerance)
    def hi(ref):return resistor(values,ref)*(1+tolerance)
    def center_r(ref,default):return resistor(center,ref) if center is not None else default
    supply_min,supply_max=3.135,3.465
    ctrl_passive=sum(supply_max/lo(ref) for ref in ('R2250','R2251','R2255','R2264','R2256'))
    ctrl_passive+=sum(supply_max/(center_r(ref,100e3)*(1-tolerance)) for ref in ('R2261','R2263'))
    aup=values.mpn('U2207')=='SN74AUP2G07DCKR'
    ctrl_ic=188.2e-6+175e-6+(.9e-6+2*50e-6 if aup else 10e-6+2*500e-6)+20e-6+100e-6
    ctrl_demand=ctrl_passive+ctrl_ic
    ctrl_min=supply_min-.05-ctrl_demand*hi('R2257')
    fault_down=center_r('R2263',100e3)*(1-tolerance)
    fault_high=(ctrl_min-20e-6*hi('R2256')-1e-6*(hi('R2256')+hi('R2258')))*fault_down/(fault_down+hi('R2256')+hi('R2258'))-.05
    charge_series=hi('R2265')+center_r('R2260',1000)*(1+tolerance)
    charge_down=center_r('R2261',100e3)*(1-tolerance)
    charge_high=(ctrl_min-.3-5e-6*charge_series)*charge_down/(charge_down+charge_series)-.05
    prot_passive=3.393/(resistor(values,'R2253')*(1-.002625))+3.393/lo('R708')+3.393/lo('R709')
    prot_demand=prot_passive+175e-6+1e-6+350e-6+100e-6
    prot_min=8.4-1.0-prot_demand*hi('R2252')
    return {
        'control_passive_a':ctrl_passive,'control_ic_and_reserve_a':ctrl_ic,
        'control_demand_a':ctrl_demand,'control_supply_min_v':ctrl_min,
        'charge_high_min_v':charge_high,'charge_low_max_v':.05+.3+5e-6*charge_series,
        'fault_high_min_v':fault_high,'fault_high_threshold_v':.7*supply_max,
        'fault_low_max_v':.05+(.45 if aup else .55)+1e-6*hi('R2258'),
        'fault_low_threshold_v':.3*supply_min,
        'protected_demand_a':prot_demand,'protected_ldo_input_min_v':prot_min,
        'protected_feed_short_21v_a':21/lo('R2252'),
        'protected_feed_short_21v_w':21**2/lo('R2252'),
        'control_feed_short_a':supply_max/lo('R2257'),
        'control_feed_short_w':supply_max**2/lo('R2257'),
        'interface_pin_short_a':supply_max/min(lo(r) for r in ('R2258','R2259','R2265')),
        'resistor_1206_derated_85c_w':.25*(155-85)/(155-70),
        'clamp_forward_max_25c_v':.32,
        'charger_gate_unpowered_max_v':center_r('R2262',4700)*(1+tolerance)*10.1e-6,
    }


def bms_control_checks(values: NetlistValues, center: NetlistValues | None = None):
    budget=bms_control_budget(values,center)
    return [
        Check('control-island minimum supply screen',budget['control_supply_min_v'],'V',2.25,3.6,
              'MCU3V3 3.135V,50mV wire allocation,all IC/input-state current screens and R2257 tolerance/TCR'),
        Check('isolated charge-permit high screen',budget['charge_high_min_v'],'V',2.0,3.6,
              'ISO VOH drop300mV,R2265/R2260/R2261,5uA input and independent50mV return allowance'),
        Check('isolated charge-permit low screen',budget['charge_low_max_v'],'V',0,.8,
              'ISO VOL300mV,5uA input,series resistors and50mV control-return allowance'),
        Check('isolated pack-health high screen',budget['fault_high_min_v'],'V',budget['fault_high_threshold_v'],3.6,
              'R2256/R2258/R2263;20uA combined output-leakage stress,1uA TCA input,50mV return allowance'),
        Check('isolated pack-health low screen',budget['fault_low_max_v'],'V',0,budget['fault_low_threshold_v'],
              'LVC VOL550mV conservative bound,1uA TCA input,50mV control-return allowance'),
        Check('protected control regulator input screen',budget['protected_ldo_input_min_v'],'V',4.393,8.4,
              '8.4V source,1V diode-drop stress,2.49k feed and loaded-LDO/current allowances'),
        Check('protected supply-feed short dissipation',budget['protected_feed_short_21v_w'],'W',0,budget['resistor_1206_derated_85c_w'],
              '21V fault screen,RC1206 0.25W derated to85C; not an allowed battery voltage'),
        Check('control-island supply-feed short dissipation',budget['control_feed_short_w'],'W',0,budget['resistor_1206_derated_85c_w'],
              '3.465V and R2257 minimum with tolerance/TCR'),
        Check('control-interface steady pin-short current',budget['interface_pin_short_a']*1000,'mA',0,1,
              '3.465V through4.7k minimum;BAT54S VFmax320mV at1mA only specified at25C'),
        Check('charger-enable gate when AND is unpowered',budget['charger_gate_unpowered_max_v'],'V',0,.1,
              '(10uA LVC Ioff+100nA MOS gate leakage)*R2262(high); brownout transients remain'),
    ]


def build_checks(values: dict[str, str], radio_values: dict[str, str],
                 project: str = "ducktop2") -> list[Check]:
    checks: list[Check] = []

    # Board split Phase 2.4: pack protection calculations (LTC4368 window,
    # RS10/RS11 breakers, C725, BQ77915 OCD/SCD) moved to the BMS board and
    # are verified against the bms project netlist.  The center project skips
    # this section.
    if project == "bms":
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
            Check("BQ7791500 shunt power at pack trip", bms_shunt_power_at_pack_trip, "W", 0.0, 0.30,
                  "I(LTC4368 max)^2*RS11; RS11 is rated 2W"),
            Check("BQ7791500 balance current nominal", bms_balance_nominal * 1000.0, "mA", 25.0, 27.0,
                  "4.2V/(2*75R+12R); internal-balance current"),
            Check("BQ7791500 balance worst-case max", bms_balance_worst_max * 1000.0, "mA", 0.0, 30.0,
                  "4.24V/(2*75R*0.99+8R); worst-case high balance current"),
        ])
        if isinstance(values, NetlistValues) and 'U2200' in values:
            checks.extend(bms_thermal_checks(values))
            checks.extend(bms_control_checks(values))
        return checks
    # Board split Phase 2.4: the LTC4418 PD selectors (R2140-R2145) moved to
    # the left I/O board; the USB selector (R730-R732) stays on center.
    if "R2140" in values:
        for index, refs in enumerate((("R2140", "R2141", "R2142"),
                                      ("R2143", "R2144", "R2145")), start=1):
            add_window(checks, f"LTC4418 PD{index} selector acceptance", refs, values, 1.0,
                       (12.8, 13.3), (16.7, 17.5))
    add_window(checks, "LTC4418 USB acceptance", ("R730", "R731", "R732"),
               values, 1.0, (12.8, 13.3), (16.7, 23.4))
    add_window(checks, "LTC4418 AUX acceptance", ("R733", "R734", "R735"),
               values, 1.0, (5.3, 5.9), (22.5, 24.0))
    add_window(checks, "TPS26630 AUX protection", ("R711", "R712", "R713"),
               values, 1.2, (5.3, 5.8), (22.5, 23.5))
    aux_efuse_limit = 18.0 / (resistor(values, "R710") / 1e3)
    aux_pg_nominal = 1.2 * (1.0 + resistor(values, "R739") / resistor(values, "R740"))
    aux_pg_minimum, aux_pg_maximum = divider_corners(
        resistor(values, 'R739'), resistor(values, 'R740'),
        values.environment_tolerance('R739'), values.environment_tolerance('R740'),
        1.176, 1.224)
    checks.extend([
        Check("TPS26630 AUX current limit", aux_efuse_limit, "A", 2.9, 3.1,
              "18/R710(kOhm)"),
        Check("TPS26630 AUX PGOOD rising nominal", aux_pg_nominal, "V", 5.20, 5.35,
              "1.2V*(1+R739/R740)"),
        Check("TPS26630 AUX PGOOD rising worst-case minimum", aux_pg_minimum, "V", 5.10, 5.25,
              "1.176V; actual R739/R740 independent initial/TCR/endurance/soldering bounds"),
        Check("TPS26630 AUX PGOOD rising worst-case maximum", aux_pg_maximum, "V", 5.30, 5.45,
              "1.224V; actual R739/R740 independent initial/TCR/endurance/soldering bounds"),
    ])

    r_ilim_top = resistor(values, "R17")
    r_ilim_bottom = resistor(values, "R190")
    bq_ilim = (5.0 * r_ilim_bottom / (r_ilim_top + r_ilim_bottom) - 1.0) / 0.8
    checks.append(Check("BQ25798 nominal ILIM pin setting", bq_ilim, "A", 2.9, 3.1,
                        "(5V*R190/(R17+R190)-1V)/(0.8V/A); not a guaranteed 3A current ceiling"))

    if values.mpn('U6') == 'LM706A0RRXR':
        rail_checks = sys5_voltage_checks(values)
        checks.extend(sys5_checks(values))
    else:
        rail_checks = system_5v_checks(resistor(values, "R40"), resistor(values, "R41"))
        checks.extend(rail_checks)
        checks.append(Check("TPS56637 SYS_5V local capacitance only", (capacitor(values, 'C44')+capacitor(values, 'C45'))*1e6,
                            'uF', 40, 100, 'local bank only; enabled branch bank must also be below the published100uF range'))
    sys_5v_max = rail_checks[2].value
    sys_3v3 = 0.6 * (1.0 + resistor(values, "R43") / resistor(values, "R44"))
    checks.extend([
        Check("TPS56637 SYS_3V3 set-point", sys_3v3, "V", 3.25, 3.35,
              "0.6V*(1+R43/R44)"),
    ])

    for name, ref in (
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

    checks.extend(aon_converter_checks(values))

    radio_vout = 0.596 * (
        1.0 + resistor(radio_values, "R221") / resistor(radio_values, "R222")
    )
    _, radio_vout_max = divider_corners(resistor(radio_values, 'R221'), resistor(radio_values, 'R222'),
                                       radio_values.environment_tolerance('R221'), radio_values.environment_tolerance('R222'),
                                       .581, .611)
    pe42820_control_max = max(
        radio_vout_max*resistor(radio_values, bottom)*(1+radio_values.environment_tolerance(bottom)) /
        (resistor(radio_values, top)*(1-radio_values.environment_tolerance(top))+
         resistor(radio_values, bottom)*(1+radio_values.environment_tolerance(bottom)))
        for top, bottom in (('R242', 'R227'), ('R260', 'R228')))
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
              "both VHF/UHF dividers and TPS54302 output divider include actual initial/TCR/endurance/soldering bounds; PE42820 absolute max is3.6V"),
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

    mu_12v = 1.2 * (1.0 + (resistor(values, "R753")+resistor(values, 'R752')) / resistor(values, "R754"))
    mu_shunt = resistor(values, "RS750")
    mu_current = 0.050 / mu_shunt
    shunt_min, shunt_max = mu_shunt_bounds(values)
    mu_current_min = 0.048 / shunt_max
    mu_current_max = 0.052 / shunt_min
    mu_vmin, mu_vmax = mu_voltage_corners(values)
    mu_power_min = mu_vmin * mu_current_min
    mu_power_max = mu_vmax * mu_current_max
    mu_uvlo = 1.23 * (1.0 + resistor(values, "R759") / resistor(values, "R760"))
    mu_uvlo_min, mu_uvlo_max = divider_corners(resistor(values, 'R759'), resistor(values, 'R760'),
                                               values.environment_tolerance('R759'), values.environment_tolerance('R760'),
                                               1.20, 1.26)
    mu_force_off_gate = 8.45 * resistor(values, "R761") / (
        resistor(values, "R766") + resistor(values, "R761")
    )
    mu_fsw = 20e9 / resistor(values, "R756")
    low_pack_budget = firmware_integer_define("EC_DEFAULT_LOW_PACK_MU_EDP_BUDGET_MW") / 1000.0
    normal_mu_edp_budget = firmware_integer_define("EC_DEFAULT_NORMAL_MU_EDP_BUDGET_MW") / 1000.0
    low_pack_reserve = firmware_integer_define("EC_DEFAULT_SYSTEM_RESERVE_MW") / 1000.0
    source_efficiency = firmware_integer_define("EC_DEFAULT_SOURCE_EFFICIENCY_PERMILLE") / 1000.0
    if project == "bms":
        low_pack_power = pack_uv * pack_breaker_min
        low_pack_continuous_power = 0.80 * low_pack_power
    else:
        low_pack_power = low_pack_continuous_power = 0.0
    low_pack_required_input = low_pack_budget / source_efficiency + low_pack_reserve
    low_pack_mu_headroom = low_pack_continuous_power - low_pack_required_input
    fan_max_current = 0.26
    fan_max_power = mu_vmax * fan_max_current
    fan_fuse_margin = resistor(values, "F200") / fan_max_current
    fan_fg_cutoff = 1.0 / (2.0 * math.pi * resistor(values, "R206") * capacitor(values, "C209"))
    fan_fg_max = 6100.0 * 2.0 / 60.0
    fan_fg_filter_ratio = fan_fg_cutoff / fan_fg_max
    normal_mu_rail_headroom = 3.3*mu_vmin - normal_mu_edp_budget - fan_max_power
    support_reserve_after_fan = low_pack_reserve - fan_max_power
    checks.extend([
        Check("TPS552892 MU_12V set-point", mu_12v, "V", 11.9, 12.15,
              "1.2V*(1+R753/R754)"),
        Check("TPS552892 nominal output-current limit", mu_current, "A", 3.7, 4.0,
              "50mV/RS750"),
        Check("TPS552892 output-current limit minimum", mu_current_min, "A", 3.3, math.inf,
              "48mV/full effective shunt maximum;initial,TCR,endurance,soldering and Kelvin allowance"),
        Check("Mu output-limit high corner versus average-clamp maximum", mu_power_max/(8.55*.85), "A", 0, 9,
              "VOUTmax*IOUT-limit-max/(8.55V*85%); the lower7A input-limit corner can act first; this is fault coordination, not an operating entitlement"),
        Check("Delta blower worst-case rail power", fan_max_power, "W", 3.0, 3.3,
              "MU_12V high corner*0.26A fan datasheet maximum"),
        Check("Delta blower PTC hold-current margin", fan_fuse_margin, "x", 2.5, 3.2,
              "F200 hold current/BFB04512HHA-CZ0T 0.26A maximum"),
        Check("Delta blower FG RC cutoff", fan_fg_cutoff / 1e3, "kHz", 4.5, 5.5,
              "1/(2*pi*R206*C209); Delta typical is 8.2k/4nF"),
        Check("Delta blower FG filter/pulse ratio", fan_fg_filter_ratio, "x", 20.0, 30.0,
              "FG RC cutoff/(6100RPM*2 pulses/rev/60)"),
        Check("MU_12V headroom after normal Mu/eDP budget and maximum fan", normal_mu_rail_headroom, "W", 4.0, 8.0,
              "3.3A operating allocation*VOUTmin-normal Mu/eDP budget-fan maximum"),
        Check("System reserve remaining after maximum fan", support_reserve_after_fan, "W", 2.5, 4.0,
              "EC system reserve-fan maximum; remaining reserve covers mandatory support loads"),
        Check("TPS552892 rising UVLO", mu_uvlo, "V", 8.8, 9.2,
              "1.23V*(1+R759/R760), hysteresis excluded"),
        Check("TPS552892 rising UVLO minimum", mu_uvlo_min, "V", 8.55, 9.0,
              "1.20V with individual R759/R760 initial,TCR,endurance,soldering bounds"),
        Check("TPS552892 rising UVLO maximum", mu_uvlo_max, "V", 9.0, 9.5,
              "1.26V with individual R759/R760 initial,TCR,endurance,soldering bounds"),
        Check("Mu fail-off Q750 gate at 8.45V VSYS", mu_force_off_gate, "V", 4.0, 4.5,
              "8.45V*R761/(R766+R761); reset-state gate divider"),
        Check("TPS552892 switching frequency", mu_fsw / 1e3, "kHz", 380, 420,
              "20e9/R756"),
    ])
    # Board split Phase 2.4: the low-pack budget check uses the pack UV/breaker
    # capability and runs against the bms project netlist instead.
    if project == "bms":
        checks.append(
            Check("Low-pack derated source power minus enforced firmware budget", low_pack_mu_headroom, "W", 0.5, 10.0,
                  "0.80*LTC4368 pack UV*breaker_min-(EC low-pack Mu+eDP budget/efficiency)-EC system reserve")
        )

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

    # Board split Phase 2.4: the RTL8111H crystal load (C515/C516) moved to
    # the right I/O board; the LTC4418 selector hold-up (C2146) moved left.
    if "C515" in values:
        eth_load_c1 = capacitor(values, "C515")
        eth_load_c2 = capacitor(values, "C516")
        eth_load = (eth_load_c1 * eth_load_c2) / (eth_load_c1 + eth_load_c2) + 2.0e-12
        checks.append(
            Check("RTL8111H 25MHz crystal effective load", eth_load * 1e12, "pF", 7.8, 8.2,
                  "(C515*C516)/(C515+C516)+2.0pF assumed pin/PCB stray; Y500 CL=8pF")
        )

    pd_hold_up = capacitor(values, "C2146") if "C2146" in values else 0.0
    main_hold_up = capacitor(values, "C746")
    main_droop = bq_ilim * (7e-6 + 4e-6) / main_hold_up
    if pd_hold_up > 0:
        pd_droop = bq_ilim * (7e-6 + 4e-6) / pd_hold_up
        checks.extend([
            Check("LTC4418 dual-PD selector handoff droop", pd_droop, "V", 0.0, 0.40,
                  "BQ ILIM ceiling*(7us VALID-off max+4us break-before-make max)/C2146; ESR and adapter loss excluded"),
        ])
    checks.append(
        Check("LTC4418 PD/AUX selector handoff droop", main_droop, "V", 0.0, 0.40,
              "BQ ILIM ceiling*(7us+4us)/C746; ESR and source loss excluded")
    )

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


def render_analog_addendum(boards: dict[str, NetlistValues]) -> str:
    lines = ["", "## analog coverage and qualification limits", "",
             "these are calculations from native netlists and manufacturer order codes. "
             "they are not physical rail, loop, harness, cell or fabrication qualification.", "",
             "| local bank | nominal capacitance | effective lower bound | required dc-bias retention |",
             "|---|---:|---:|---:|"]
    for board, name, refs, requirement in [
        ("center", "U5 output", ("C39", "C291"), 20e-6),
        ("center", "U6 output ceramics", ("C44", "C45"), 20e-6),
        ("center", "U7 output ceramics", ("C48", "C792"), 20e-6),
        ("center", "U773 local output ceramics", ("C782", "C2287"), 20e-6),
        ("left", "U1703 local output ceramics", ("C1714", "C1715", "C1868", "C1869"), 20e-6),
        ("left", "U1701 hub core", ("C1708", "C1709"), 5e-6),
        ("center", "U750 VCC", ("C764",), 4.7e-6),
        ("center", "U6 VCC", ("C2360",), 4.7e-6),
        ("center", "U773 VCC", ("C2280",), 4.7e-6),
        ("left", "U1703 VCC", ("C1860",), 4.7e-6),
    ]:
        values=boards[board]
        nominal=sum(capacitor(values, ref) for ref in refs)
        tol=max(values.tolerance(ref) for ref in refs)
        retention=capacitor_retention_required(nominal,tol,.15,.10,requirement)
        lines.append(f"| {name}, {'/'.join(refs)} | {nominal*1e6:.3g} µf | {requirement*1e6:g} µf | {retention*100:.2f}% |")
    total=direct_capacitance(list(boards.values()), '/USB_PORT_5V')
    lines += ["", "the retention column is an acceptance requirement. it combines initial tolerance, "
              "a15% temperature screen and an explicit10% aging allowance. exact biased capacitance "
              "and the service interval must be confirmed for the installed parts; a nominal label is not an effective-capacitance result.", "",
              f"USB_PORT_5V has {total*1e6:.4g} µf nominal directly connected in these three exports. "
              "the two PP5V gate states are separate networks. the final USB5 sensitivity model includes "
              "both reservoirs off, either on, both on, remote cable R/L and optional capacitance.", "",
              "U6 uses external compensation for the complete bank: at most80µf local ceramics,500µf "
              "local polymer and300µf across all enabled branches. U7's separate upper-bank check "
              "includes all three boards and the switched HDMI bypass. the endpoint model separates "
              "NVMe, wi-fi and the right-board GbE branch; its2mf ceiling includes board and module capacitors.", "",
              "critical voltage windows use independent resistor-family initial,TCR,endurance and "
              "soldering-change screens. TNPU/TNPW use their8000h endurance requirements; retainedRT "
              "parts use their1000h requirements. summing those changes is a conservative design screen, "
              "not a claim that different qualification tests establish product service life. "
              "the resistor temperature range is−40..85°C; it is not a released ambient range.", "",
              "the CW shunt component envelope is rounded to±6%, including initial tolerance, "
              "75ppm×105°C,3% endurance and1% soldering change. Kelvin/layout allowances are additional. "
              "the inductors' Isat and Irms figures are25°C characterization points. the stated hot-Isat "
              "reductions, propagation delays and copper losses are screens, not installed thermal or fault guarantees.", "",
              "the Mu3.3A allocation requires at least85% conversion efficiency at the modeled8.55V input. "
              "the7..9A average-current table is specified at VIN8V/VOUT20V/400kHz, and the13A peak clamp "
              "is typical only. confirm those limits at12V output. the finite Mu model includes resistive, "
              "constant-current and100kHz constant-power loads in boost operation; buck/transition behavior remains to be measured.", "",
              "the accepted BQ bootstrap command is2.50A IINDPM. the0.50A difference from a3A source "
              "is nominal only. actual AON headroom requires the source-minimum current minus the "
              "BQ maximum current at15/20V, with path and voltage tolerances. the available IINDPM "
              "accuracy table does not supply that bound at these operating points. all simultaneous "
              "rail allocations must fit the independently qualified whole-system source budget.", "",
              "unrun physical checks are finite: capacitor bias/aging and module input impedance; "
              "startup, load steps, ripple and loop gain across gate states and converter modes; "
              "hot converter/coil/shunt and harness temperatures; current-limit, short, negative-input "
              "and OV-recovery waveforms; actual branch R/L and return drop; and the insulated probes' "
              "contact/lag and cell-specific temperature/current limits. operating qualification gates remain off.", "",
              "### procurement coverage", ""]
    for name, values in boards.items():
        unknown=[f"{ref} ({values.mpn(ref) or 'missing MPN'})" for ref in sorted(values.used)
                 if decode(values.mpn(ref)) is None and values.mpn(ref) not in EXACT_PASSIVES
                 and values.mpn(ref) not in INDUCTORS]
        lines.append(f"- {name}: {len(values.used)} numeric component values used; "+
                     ("unverified procurement values: "+", ".join(unknown) if unknown else
                      "all used numeric values resolve to supported manufacturer data."))
    return "\n".join(lines)+"\n"


def render_report(checks: list[Check], netlist: Path, radio_netlist: Path) -> str:
    lines = [
        "# Ducktop2 Electrical Calculations",
        "",
        f"Generated: {dt.date.today().isoformat()}",
        "",
        "values come from KiCad XML netlists. supported manufacturer order codes supply the numerical values; mismatches with labels fail. unsupported identities remain explicit.",
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
        "## scope and remaining evidence",
        "",
        "- the default run exports center, left, right and radio electrical netlists. the BMS project has a separate run. this is not a complete six-board hardware audit.",
        "- each equation states its operating point and included tolerances. nominal capacitance, assumed efficiency, oscillator characterization and typical inductor heating/saturation figures do not become guaranteed limits when a row passes.",
        "- source windows distinguish UV entry, UV recovery, OV entry and OV recovery. the 20V candidate rows include resistor TCR and comparator leakage. switching delay and transient overshoot require routed-hardware validation.",
        "- capacitor dc bias, temperature, aging, actual module capacitance, harness impedance and regulator compensation must be reconciled with the selected parts. the connected-capacitor check includes reservoirs on the other boards.",
        "- the firmware constants used in arithmetic are requested budgets. this runner does not prove that the target enforces them or that the loads fit them. exact cells, protection, harness and module limits remain separate requirements.",
        "- oscillator and microphone calculations use the explicit stray-capacitance, sensitivity and load assumptions in their equations. startup, noise, clipping and timing still need measurement.",
        "- a desktop pass does not record any physical test as completed. protection fault response, startup, load steps, loop gain, ripple, thermal rise and recovery remain first-article tests.",
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
        "- Texas Instruments TPS22948: https://www.ti.com/lit/ds/symlink/tps22948.pdf",
        "- Texas Instruments TPD4E05U06: https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf",
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
                        default=ROOT / "verification" / "generated" /
                        f"ELECTRICAL_CALCULATIONS_{dt.date.today().isoformat()}.md")
    parser.add_argument("--project", choices=("ducktop2", "bms"), default="ducktop2",
                        help="board split Phase 2.4: which project to verify (bms = pack calculations)")
    parser.add_argument("--netlist-dir", type=Path, default=ROOT / "verification/generated",
                        help="directory for fresh electrical evidence exports")
    args = parser.parse_args()
    args.netlist_dir = args.netlist_dir.resolve()

    netlist = args.netlist_dir / "electrical_calculations_netlist.xml"
    radio_netlist = args.netlist_dir / "radio_electrical_calculations_netlist.xml"
    boards = {}
    if args.project == "bms":
        bms_sch = ROOT / "bms" / "bms.kicad_sch"
        netlist = args.netlist_dir / "bms_netlist.xml"
        export_netlist(bms_sch, netlist)
        checks = build_checks(component_values(netlist), {}, project="bms")
    else:
        export_netlist(SCHEMATIC, netlist)
        export_netlist(RADIO_SCHEMATIC, radio_netlist)
        right_netlist = args.netlist_dir / "right_electrical_calculations_netlist.xml"
        export_netlist(ROOT / "right_io/right_io.kicad_sch", right_netlist)
        left_netlist = args.netlist_dir / "left_electrical_calculations_netlist.xml"
        export_netlist(ROOT / "left_io/left_io.kicad_sch", left_netlist)
        right_values = component_values(right_netlist)
        if not right_values.get("U54", "").startswith("TPS22948DCKR") or not right_values.get("U50", "").startswith("TPD4E05U06DQAR"):
            raise ValueError("HDMI voltage calculation requires the checked TPS22948/TPD4E05U06 power path")
        center_values = component_values(netlist)
        left_values = component_values(left_netlist)
        checks = build_checks(center_values, component_values(radio_netlist))
        checks.extend(extended_checks(center_values, left_values, right_values))
        boards = {"center": center_values, "left": left_values, "right": right_values}
    report = render_report(checks, netlist, radio_netlist)
    if boards:
        report += render_analog_addendum(boards)
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
