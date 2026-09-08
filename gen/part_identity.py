"""Compare declared passive values and packages with manufacturer order codes.

Yageo RC/RT: resistance follows the reel code, with R/K/M as the decimal.
Murata GRM/GCM/GRT: dimensions precede the dielectric, voltage and capacitance.
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


def engineering_value(token: str) -> float | None:
    token = token.rstrip("FfΩ")
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
        return []
    words = re.sub(r"^DNP\s+", "", value.strip(), flags=re.I).split()
    declared = engineering_value(words[0]) if words else None
    errors = []
    if declared is None:
        errors.append(f"cannot read the declared value {value!r}")
    elif not math.isclose(actual.value, declared, rel_tol=1e-9, abs_tol=0):
        errors.append(f"order code specifies {actual.value:g}, label specifies {declared:g}")
    package = re.search(r"(?:^|:)([RC])_(\d{4})_", footprint)
    if package is None:
        errors.append(f"cannot compare the package {footprint!r}")
    elif package[1] != actual.kind or package[2] != actual.size:
        errors.append(f"order code specifies {actual.kind} {actual.size}, footprint is {footprint}")
    tolerance = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
    if tolerance and actual.tolerance is not None and actual.tolerance > float(tolerance[1]):
        errors.append(f"order code tolerance {actual.tolerance:g}% exceeds {tolerance[1]}%")
    if actual.kind == "C" and actual.voltage is not None:
        ratings = [float(word[:-1]) for word in words if re.fullmatch(r"\d+(?:\.\d+)?V", word)]
        if ratings and actual.voltage < max(ratings):
            errors.append(f"order code voltage {actual.voltage:g}V is below {max(ratings):g}V")
    return errors
