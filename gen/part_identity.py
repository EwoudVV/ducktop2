"""Compare declared passive values and packages with manufacturer order codes.

Yageo RC/RT: resistance follows the reel code, with R/K/M as the decimal.
Murata GRM/GCM/GRT: dimensions precede the dielectric, voltage and capacitance.
Vishay TNPU/TNPW: four-character resistance, then tolerance, TCR and packaging.
An unsupported family stays unverified; it is never counted as a match.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class Identity:
    kind: str
    value: float
    size: str
    tolerance: float | None = None
    voltage: float | None = None
    tcr_ppm: float | None = None
    power_w: float | None = None


def engineering_value(token: str) -> float | None:
    token = re.sub(r"(?:[Ff]|[Oo]hm|Ω)$", "", token)
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([pnuµmRrKkM]?)(\d*)", token)
    if not match:
        return None
    number, unit, tail = match.groups()
    if tail:
        if "." in number:
            return None
        number += "." + tail
    return float(number) * {"": 1, "R": 1, "r": 1, "k": 1e3, "K": 1e3,
                           "M": 1e6, "m": 1e-3, "u": 1e-6, "µ": 1e-6,
                           "n": 1e-9, "p": 1e-12}[unit]


def decode(mpn: str) -> Identity | None:
    # Reviewed Bourns CSS2H/CSS4J parts. Ratings are at a 70 C terminal;
    # the board still needs its own temperature and Kelvin-layout checks.
    bourns = {
        "CSS2H-2512K-3L00F": (.003, "2512", 4.0),
        "CSS4J-4026K-5L00F": (.005, "4026", 4.0),
    }
    if mpn in bourns:
        value, size, power = bourns[mpn]
        return Identity('R', value, size, 1.0, tcr_ppm=75, power_w=power)
    # Vishay 30100, 30122, 30121 and 31057. These are the package
    # sizes reviewed here. A plausible-looking code outside the table is invalid.
    strip = re.fullmatch(r"(WSL|WSLP|WSLT)(1206|2010|2512)(R\d{4}|\dL\d{3}|L\d{4})([DF])(EA|EK)(18)?", mpn)
    if strip:
        family, size, code, tolerance, _, high_power = strip.groups()
        value = (int(code[1:])/10000 if code[0] == 'R' else
                 float('0.'+code[1:])/1000 if code[0] == 'L' else
                 float(code.replace('L', '.'))/1000)
        if (code.startswith('R') and value < .01) or (not code.startswith('R') and value >= .01):
            return None
        if high_power and family != 'WSL':
            return None
        initial = .5 if tolerance == 'D' else 1.0
        if family == 'WSLT':
            low, high, power = .01, .5, 1.0
            if size != '2512':
                return None
            if value > .1:
                power *= 1-.2*(value-.1)/.4
        else:
            low = {'1206': .001, '2010': .001, '2512': .0005}[size]
            if tolerance == 'D':
                low = {'1206': .005, '2010': .004, '2512': .003}[size]
            high = ({'1206': .05, '2010': .03, '2512': .01}[size] if family == 'WSLP' else
                    .04 if high_power and size == '2512' else .2 if size == '1206' else .5)
            power = ({'1206': 1.0, '2010': 2.0, '2512': 3.0}[size] if family == 'WSLP' else
                     {'1206': .25, '2010': .5, '2512': 1.0}[size]*(2 if high_power else 1))
        if not low <= value <= high:
            return None
        ppm = 75 if value >= .007 else 110 if value >= .005 else 150 if value >= .003 else 275 if value >= .001 else 400
        return Identity('R', value, size, initial, tcr_ppm=ppm, power_w=power)
    # Vishay 28779 (TNPU, 2025-03-04) and 28758 (TNPW, 2026-04-10).
    # Reject combinations outside their published precision/resistance tables.
    precision = re.fullmatch(r"(TNPU)(0402|0603|0805|1206)([\dRKM]{4})([ABH])([YZW])(E[AINP])00", mpn)
    if precision:
        _, size, code, tolerance, tcr, packaging = precision.groups()
        value = engineering_value(code)
        initial = {"B": .1, "A": .05, "H": .02}[tolerance]
        ppm = {"Y": 10, "Z": 5, "W": 2}[tcr]
        valid = value is not None and sum(code.count(c) for c in 'RKM') == 1
        valid = valid and packaging in (("EP", "EI") if size == "0402" else ("EN", "EA"))
        low, high = {"0402": (100, 100e3), "0603": (24.9, 100e3),
                     "0805": (100, 332e3), "1206": (100, 511e3)}[size]
        if ppm == 10:
            valid = valid and initial == .05
        elif ppm == 5 and initial == .02:
            valid = valid and size != "0402"
            low, high = 100, 100e3 if size == "0603" else 200e3
        elif ppm == 2:
            valid = valid and size != "0402"
            low, high = 500, 20e3
        if valid and low <= value <= high:
            return Identity("R", value, size, initial, tcr_ppm=ppm)
        return None
    precision = re.fullmatch(r"(TNPW)(0402|0603|0805|1206)([\dRKM]{4})([BDF])([HEXY])(E[ACD])", mpn)
    if precision:
        _, size, code, tolerance, tcr, packaging = precision.groups()
        value = engineering_value(code)
        initial = {"B": .1, "D": .5, "F": 1}[tolerance]
        ppm = {"H": 50, "E": 25, "X": 15, "Y": 10}[tcr]
        valid = value is not None and sum(code.count(c) for c in 'RKM') == 1
        valid = valid and packaging in (("ED",) if size == "0402" else ("EA", "EC"))
        valid = valid and (packaging != "EC" or ppm in (25, 50))
        low, high = {"0402": (10, 100e3), "0603": (1, 332e3),
                     "0805": (1, 1e6), "1206": (1, 2e6), "1210": (10, 3.01e6)}[size]
        if initial == .1 and size in ("0603", "0805", "1206"):
            low = 3.5
        if ppm in (10, 15):
            valid = valid and initial == .1
            low = 47 if size in ("0402", "0603", "1206") else 3.5
        if valid and low <= value <= high:
            return Identity("R", value, size, initial, tcr_ppm=ppm)
        return None
    resistor = re.fullmatch(
        r"(?:RC(\d{4})([BDFJ])[RK]-?(?:07|10|13)|"
        r"RT(\d{4})([BCDFPW])[RK][ABCDE](?:07|10|13|7W))([\dRKM]+)L", mpn)
    if resistor:
        size = resistor[1] or resistor[3]
        tol = resistor[2] or resistor[4]
        value = engineering_value(resistor[5])
        if value is not None:
            return Identity("R", value, size,
                            {"B": .1, "C": .25, "D": .5, "F": 1,
                             "J": 5, "P": .02, "W": .05}[tol])
    capacitor = re.fullmatch(r"(?:GRM|GCM|GRT)([A-Z0-9]{3})([A-Z0-9]{2})"
                             r"([A-Z0-9]{2})(\d{3})([A-Z])([A-Z0-9]+)", mpn)
    if capacitor:
        sizes = {"03": "0201", "15": "0402", "18": "0603", "21": "0805",
                 "31": "1206", "32": "1210", "43": "1812"}
        size = sizes.get(capacitor[1][:2])
        if size is None:
            return None
        code = capacitor[4]
        value = int(code[:2]) * 10 ** int(code[2]) * 1e-12
        voltage = {"0J": 6.3, "1A": 10, "1C": 16, "1E": 25, "1H": 50,
                   "1J": 63, "2A": 100, "2D": 200, "2E": 250}.get(capacitor[3])
        return Identity("C", value, size, {"J": 5, "K": 10, "M": 20}.get(capacitor[5]), voltage)
    return None


def identity_errors(value: str, footprint: str, mpn: str) -> list[str]:
    actual = decode(mpn)
    if actual is None:
        if mpn.startswith(('WSL1206', 'WSLP1206', 'WSL2010', 'WSL2512', 'WSLP2010', 'WSLP2512', 'WSLT2512', 'CSS2H-', 'CSS4J-')):
            return [f"unverified metal-strip code or value outside the published family range: {mpn}"]
        return []
    words = re.sub(r"^DNP\s+", "", value.strip(), flags=re.I).split()
    declared = engineering_value(words[0]) if words else None
    errors = []
    if declared is None:
        errors.append(f"cannot read the declared value {value!r}")
    elif not math.isclose(actual.value, declared, rel_tol=1e-9, abs_tol=0):
        errors.append(f"order code specifies {actual.value:g}, label specifies {declared:g}")
    package = re.search(r"(?:^|:)([RC])_(\d{4})_", footprint)
    kelvin_package = {
        "ducktop2:Bourns_CSS2H_2512_Kelvin": ('R', '2512'),
        "ducktop2:Bourns_CSS4J_4026_Kelvin": ('R', '4026'),
    }.get(footprint)
    if kelvin_package is not None:
        if kelvin_package != (actual.kind, actual.size):
            errors.append(f"order code specifies {actual.kind} {actual.size}, footprint is {footprint}")
    elif package is None:
        errors.append(f"cannot compare the package {footprint!r}")
    elif package[1] != actual.kind or package[2] != actual.size:
        errors.append(f"order code specifies {actual.kind} {actual.size}, footprint is {footprint}")
    tolerance = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
    if tolerance and actual.tolerance is not None and actual.tolerance > float(tolerance[1]):
        errors.append(f"order code tolerance {actual.tolerance:g}% exceeds {tolerance[1]}%")
    tcr = re.search(r"(\d+(?:\.\d+)?)\s*ppm", value, re.I)
    if tcr and actual.tcr_ppm is not None and actual.tcr_ppm > float(tcr[1]):
        errors.append(f"order code TCR {actual.tcr_ppm:g}ppm exceeds {tcr[1]}ppm")
    if actual.kind == "C" and actual.voltage is not None:
        ratings = [float(word[:-1]) for word in words if re.fullmatch(r"\d+(?:\.\d+)?V", word)]
        if ratings and actual.voltage < max(ratings):
            errors.append(f"order code voltage {actual.voltage:g}V is below {max(ratings):g}V")
    power = re.search(r"(\d+(?:\.\d+)?)\s*W\b", value)
    if power and actual.power_w is not None and actual.power_w < float(power[1]):
        errors.append(f"order code power {actual.power_w:g}W is below {power[1]}W")
    return errors
