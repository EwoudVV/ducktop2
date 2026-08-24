#!/usr/bin/env python3
"""
Spec-keyed procurement catalog for the Ducktop2 main board.

Sources (highest authority first):
  1. gen/apply_bom_catalog.py reviewed per-ref assignments (2026-08-01).
  2. verification/BOM_MPN_ASSIGNMENTS.md reviewed Murata GRM hold suggestions
     (2026-07-30) for the intentional capacitor holds.
  3. MCP-verified alternates (LCSC spec search, 2026-08-01) recorded in
     ALTERNATES for dual sourcing only; never stamped.

The catalog is inverted from per-ref assignments into spec keys so that the
generators can stamp Manufacturer/MPN at Sheet.place() time and regeneration
can never lose procurement identity again (the fix for commit c329f95 which
wiped the post-processing patches of commit 57008c8).

Rules:
  - Every reviewed ref resolves by reference (REF_FALLBACKS), so stamping is
    deterministic and exact even in the release gate's temp copy where
    verification/ is emptied.
  - The inverted SPEC_CATALOG (value+footprint driven) covers refs unknown to
    the reviewed dicts so future passives get stamped automatically.
  - A spec key that maps to more than one reviewed part is not used for spec
    lookup; such refs keep their own reviewed part.
  - Refs whose value string cannot be parsed resolve by reference.
  - No reviewed part is ever silently changed (REF_OVERRIDES documents the
    one intentional unification).

Run as a script for a coverage self-test:
  python3 gen/bom_catalog.py
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from apply_bom_catalog import CAPACITOR_ASSIGNMENTS, RESISTOR_ASSIGNMENTS

ROOT = Path(__file__).resolve().parents[1]
GAP_CSV = ROOT / "verification" / "bom_release_gaps.csv"


# =============================================================================
# 1.  INTENTIONAL-HOLD PARTS  (verification/BOM_MPN_ASSIGNMENTS.md, 2026-07-30)
# =============================================================================
# These refs were deliberately left unassigned by apply_bom_catalog.py pending
# review; the reviewed Murata GRM suggestions below close them out.
HOLD_PARTS: dict[str, tuple[str, str]] = {
    # (ref) -> (manufacturer, mpn)
    # -- 02_ec_mcu.kicad_sch --
    "C29":  ("Murata", "GRM21BR60J225ME01"),  # 2.2u 0805 X5R 6.3V VCAP_1 (ST mandatory low-ESR)
    "C30":  ("Murata", "GRM21BR60J225ME01"),  # 2.2u 0805 X5R 6.3V VCAP_2 (ST mandatory low-ESR)
    "C290": ("Murata", "GRM188R71H103KA01"),  # 10n 0603 X7R 50V VDDA high-frequency
    "C292": ("Murata", "GRM1555C1H560JA01"),  # 56p 0402 C0G 50V +/-5% feed-forward
    # -- 15_system_audio.kicad_sch --
    "C414": ("Murata", "GRM1885C1H180JA01"),  # 18p 0603 C0G 50V +/-5% hub crystal load
    "C415": ("Murata", "GRM1885C1H180JA01"),
    "C420": ("Murata", "GRM1885C1H180JA01"),  # 18p codec crystal load
    "C421": ("Murata", "GRM1885C1H180JA01"),
    "C430": ("Murata", "GRM188R71H473KA01"),  # 47n 0603 X7R 50V L DAC out-of-band shunt
    "C431": ("Murata", "GRM188R71H473KA01"),  # 47n R DAC out-of-band shunt
    "C432": ("Murata", "GRM21BR71H105KA01"),  # 1u 0805 X7R 50V L positive-input AC coupling
    "C433": ("Murata", "GRM21BR71H105KA01"),  # 1u R positive-input AC coupling
    "C434": ("Murata", "GRM21BR71H105KA01"),  # 1u L negative-input AC reference
    "C435": ("Murata", "GRM21BR71H105KA01"),  # 1u R negative-input AC reference
    "C442": ("Murata", "GRM155R71H102KA01"),  # 1n 0402 X7R 50V speaker EMI shunt
    "C443": ("Murata", "GRM155R71H102KA01"),
    "C444": ("Murata", "GRM155R71H102KA01"),
    "C445": ("Murata", "GRM155R71H102KA01"),
    "C453": ("Murata", "GRM1885C1H122JA01"),  # 1.2n 0603 C0G 50V +/-5% feedback low-pass
    "C454": ("Murata", "GRM31CR61C475KA01"),  # 4.7u 1206 X5R 16V mic gain-leg AC coupling
    "C455": ("Murata", "GRM31CR61C475KA01"),  # 4.7u mic to PCM2900 VINL
    "C456": ("Murata", "GRM31CR61C475KA01"),  # 4.7u mic to PCM2900 VINR
    # -- 16_gigabit_ethernet.kicad_sch --
    "C515": ("Murata", "GRM1555C1H120JA01"),  # 12p 0402 C0G 50V +/-5% crystal load
    "C516": ("Murata", "GRM1555C1H120JA01"),
    # -- 01_power_battery.kicad_sch --
    "C700": ("Murata", "GRM155R71H332KA01"),  # 3.3n 0402 X7R 50V LTC4368 CGATE
    "C720": ("Murata", "GRM21BR71H105KA01"),  # 1u 0805 X7R 50V AUX input
    "C724": ("Murata", "GRM155R71H472KA01"),  # 4.7n 0402 X7R 50V pack hot-swap slew
    "C799": ("Murata", "GRM155R71H332KA01"),  # 3.3n 0402 X7R 50V AON eFuse dVdt
    # -- 03_mu_carrier.kicad_sch --
    "C767": ("Murata", "GRM188R71H103KA01"),  # 10n 0603 X7R 50V DITH/SYNC spreading
    "C770": ("Murata", "GRM188R71H104KA93D"),  # 100n 0603 X7R 50V current-sense filter (majority-collapsed)
    "C771": ("Murata", "GRM188R71H472KA01"),  # 4.7n 0603 X7R 50V COMP
    "C772": ("Murata", "GRM1885C1H101JA01"),  # 100p 0603 C0G 50V +/-5% COMP HF
    "C773": ("Murata", "GRM188R71H104KA93D"),  # 100n 0603 X7R 50V UVLO noise filter (majority-collapsed)
    "C774": ("Murata", "GRM188R71H103KA01"),  # 10n 0603 X7R 50V PG deglitch
    "C775": ("Murata", "GRM188R71H103KA01"),  # 10n 0603 X7R 50V CC deglitch
    # -- 2026-08-13 additions (DFU port, PCIe endpoint buck, SIO pads, RTC) --
    "C778": ("Murata", "GRM188R71H104KA93D"),  # 100n 0603 X7R 50V PCIe endpoint buck VIN HF
    "C779": ("TDK", "C1608X7R1C104K080AA"),  # 100n 0603 X7R 16V PCIe endpoint buck BOOT (matches U7 BOOT C47)
    "R203": ("Yageo", "RC0603FR-0722RL"),  # 22R DFU USB DP series
    "R204": ("Yageo", "RC0603FR-0722RL"),  # 22R DFU USB DM series
    "R205": ("Yageo", "RC0603FR-075K1L"),  # 5.1k USB-C CC1 Rd (UFP)
    "R211": ("Yageo", "RC0603FR-075K1L"),  # 5.1k USB-C CC2 Rd (UFP)
    "R212": ("Yageo", "RC0603FR-071KL"),  # 1k DFU select series
    "R779": ("Yageo", "RC0603FR-07100KL"),  # 100k MU_SIO_UART_TX idle pull-up
    "R784": ("Yageo", "RC0603FR-07100KL"),  # 100k MU_SIO_UART_RX idle pull-up
    "R787": ("Yageo", "RC0603FR-07100KL"),  # 100k TPS56637 EN high (host-active gate)
    "R788": ("Yageo", "RC0603FR-07100KL"),  # 100k TPS56637 EN low
    # -- 14_maker_mcu.kicad_sch --
    "C902": ("Murata", "GRM155R61A475KE15"),  # 4.7u 0402 X5R 10V flash bulk
    "C911": ("Murata", "GRM155R61A475KE15"),  # 4.7u VREG input
    "C912": ("Murata", "GRM155R61A475KE15"),  # 4.7u 1V1 output
    "C913": ("Murata", "GRM155R61A475KE15"),  # 4.7u VREG_AVDD
    "C917": ("Murata", "GRM155R61A475KE15"),  # 4.7u ADC_AVDD filter
    "C918": ("Murata", "GRM1555C1H150JA01"),  # 15p 0402 C0G 50V +/-5% XIN load
    "C919": ("Murata", "GRM1555C1H150JA01"),  # 15p XOUT load
    # -- 09_radio_daughterboard_interface.kicad_sch --
    "C2300": ("Murata", "GRM155R71H472KA01"),  # 4.7n 0402 X7R 50V radio eFuse controlled rise
    # -- 15_system_audio.kicad_sch (uncovered in the 2026-07-30 review; closed out
    #    consistent with the design's own AC-coupling precedent C432-C435) --
    "C457": ("Murata", "GRM21BR71H474KA01"),  # 0.47u 0805 X7R 50V L input AC coupling
    "C458": ("Murata", "GRM21BR71H474KA01"),  # 0.47u L INP AC-ground reference
    "C459": ("Murata", "GRM21BR71H474KA01"),  # 0.47u R input AC coupling
    "C460": ("Murata", "GRM21BR71H474KA01"),  # 0.47u R INP AC-ground reference
    "C461": ("Murata", "GRM21BR71H105KA01"),  # 1u 0805 X7R 50V charge-pump flying CPP-CPN
    "C462": ("Murata", "GRM21BR71H105KA01"),  # 1u CPVSS negative-rail decoupling
    "C463": ("Murata", "GRM21BR71H105KA01"),  # 1u VDD pin 12 analog bypass
    "C464": ("Murata", "GRM21BR71H105KA01"),  # 1u VDD pin 20 charge-pump supply bypass
    "C465": ("Murata", "GRM188R71H104KA93D"),  # 100n 0603 X7R 50V VDD high-frequency bypass
}


# =============================================================================
# 2.  MCP-VERIFIED ALTERNATES  (LCSC spec search, 2026-08-01)  -- dual sourcing
# =============================================================================
# Legacy MPN string searches return 0 results at LCSC; spec searches verified
# these high-stock alternates for the canonical GRM/Yageo parts above.
# Key: (kind, value_nf/ohm, size, voltage, dielectric) -> (mfr, mpn, provenance)
ALTERNATES: dict[tuple, tuple[str, str, str]] = {
    ("C", 1000.0, "0805", "50V", "X7R"): ("Samsung Electro-Mechanics", "CL21B105KBFNNNE", "LCSC C28323, stock 6.16M"),
    ("C", 0.015, "0402", "50V", "C0G"): ("YAGEO", "CC0402JRNPO9BN150", "LCSC C106997, stock 1.51M"),
    ("C", 4.7, "0402", "50V", "X7R"): ("YAGEO", "CC0402KRX7R9BB472", "LCSC C106208, stock 477k"),
    ("C", 100.0, "0402", "10V", "X7R"): ("HRE", "CGA0402X7R104K100GT", "LCSC C22435935, stock 10.5k"),
    ("C", 47.0, "0603", "50V", "X7R"): ("muRata", "GCM188R71H473KA55J", "LCSC C3853032, stock 3.9k"),
    ("C", 2200.0, "0805", "6.3V", "X5R"): ("Samsung Electro-Mechanics", "CL21A225KBQNNNE", "LCSC C377773, VCAP class"),
}


# =============================================================================
# 3.  SPEC PARSING
# =============================================================================
CAP_TOKEN = re.compile(r"^(\d+(?:\.\d+)?)([pnuµm])F?$")
RES_TOKEN = re.compile(r"^(\d+(?:\.\d+)?)([RkKmM]?)(\d*)$")
VOLTAGE_TOKEN = re.compile(r"(6\.3|10|16|25|35|50|63|100)V")
DIELECTRIC_TOKEN = re.compile(r"(X7R|X5R|X6S|X8R|C0G|NP0)", re.IGNORECASE)
TOLERANCE_TOKEN = re.compile(r"(0\.1|0\.25|0\.5|1|2|5)%")
FOOTPRINT_TOKEN = re.compile(r"[CR]_(\d{4})_")

CAP_UNIT_NF = {"p": 1e-3, "n": 1.0, "u": 1e3, "µ": 1e3, "m": 1e6}
RES_UNIT = {"R": 1.0, "k": 1e3, "K": 1e3, "m": 1e-3, "M": 1e6}


@dataclass(frozen=True)
class CapSpec:
    value_nf: float
    size: str
    voltage: Optional[str]
    dielectric: Optional[str]


@dataclass(frozen=True)
class ResSpec:
    value_ohm: float
    size: str
    tolerance: Optional[str]


def footprint_size(footprint: str) -> Optional[str]:
    match = FOOTPRINT_TOKEN.search(footprint)
    return match.group(1) if match else None


def parse_cap(value: str, footprint: str) -> Optional[CapSpec]:
    size = footprint_size(footprint)
    if size is None:
        return None
    for token in re.split(r"[\s(),]+", value):
        match = CAP_TOKEN.match(token)
        if not match:
            continue
        value_nf = float(match.group(1)) * CAP_UNIT_NF[match.group(2)]
        voltage_match = VOLTAGE_TOKEN.search(value)
        dielectric_match = DIELECTRIC_TOKEN.search(value)
        dielectric = dielectric_match.group(1).upper() if dielectric_match else None
        if dielectric == "NP0":
            dielectric = "C0G"
        return CapSpec(
            value_nf=value_nf,
            size=size,
            voltage=voltage_match.group(0) if voltage_match else None,
            dielectric=dielectric,
        )
    return None


def parse_res(value: str, footprint: str) -> Optional[ResSpec]:
    size = footprint_size(footprint)
    if size is None:
        return None
    for token in re.split(r"[\s(),]+", value):
        match = RES_TOKEN.match(token)
        if not match:
            continue
        mantissa = float(match.group(1))
        unit = match.group(2) or "R"
        fraction = match.group(3)
        if fraction:
            mantissa += int(fraction) / (10 ** len(fraction))
        tolerance_match = TOLERANCE_TOKEN.search(value)
        return ResSpec(
            value_ohm=mantissa * RES_UNIT[unit],
            size=size,
            tolerance=tolerance_match.group(0) if tolerance_match else None,
        )
    return None


def parse_spec(value: str, footprint: str):
    cap = parse_cap(value, footprint)
    if cap is not None:
        return ("C", cap.value_nf, cap.size, cap.voltage, cap.dielectric)
    res = parse_res(value, footprint)
    if res is not None:
        return ("R", res.value_ohm, res.size, res.tolerance)
    return None


# =============================================================================
# 4.  REF-LEVEL OVERRIDES
# =============================================================================
# Ref-level part corrections that supersede the reviewed dicts.  R433 was
# assigned RC0603FR-071K00L; RC0603FR-071K00L and RC0603FR-071KL are the same
# Yageo part (4-digit vs 3-digit E96 code) — unify to the majority form.
REF_OVERRIDES: dict[str, tuple[str, str]] = {
    "R433": ("Yageo", "RC0603FR-071KL"),
}


def _ref_parts() -> dict[str, tuple[str, str]]:
    ref_parts: dict[str, tuple[str, str]] = {}
    for ref, (mfr, mpn, _basis) in RESISTOR_ASSIGNMENTS.items():
        ref_parts[ref] = (mfr, mpn)
    for ref, (mfr, mpn, _basis) in CAPACITOR_ASSIGNMENTS.items():
        ref_parts[ref] = (mfr, mpn)
    for ref, part in HOLD_PARTS.items():
        ref_parts[ref] = part
    for ref, part in REF_OVERRIDES.items():
        ref_parts[ref] = part
    return ref_parts


def _load_gap_refs() -> dict[str, tuple[str, str]]:
    refs: dict[str, tuple[str, str]] = {}
    with GAP_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            refs[row["ref"]] = (row["value"], row["footprint"])
    return refs


def build_catalog():
    """Returns (spec_catalog, ref_fallbacks, diagnostics).

    ref_fallbacks covers every reviewed ref and never needs the gap CSV, so
    the release gate's temp copy (which empties verification/) resolves the
    same parts.  The spec catalog is an optional inversion for future refs and
    is only built when the gap CSV is non-empty; unreviewed new passives
    surface as gaps and go through the review flow before stamping.
    """
    ref_parts = _ref_parts()
    ref_fallbacks = dict(ref_parts)
    spec_catalog: dict[tuple, tuple[str, str]] = {}
    diagnostics: list[str] = []

    if not GAP_CSV.exists():
        diagnostics.append("no gap CSV (release-gate copy): spec catalog skipped, per-ref fallbacks cover all reviewed refs")
        return spec_catalog, ref_fallbacks, diagnostics

    gap_refs = _load_gap_refs()
    if not gap_refs:
        diagnostics.append("zero gap refs: spec catalog empty (review-first flow for new passives)")
        return spec_catalog, ref_fallbacks, diagnostics

    buckets: dict[tuple, list[str]] = defaultdict(list)
    for ref, (value, footprint) in gap_refs.items():
        if ref not in ref_parts:
            diagnostics.append(f"{ref}: in gaps but not in assignments/holds")
            continue
        spec = parse_spec(value, footprint)
        if spec is not None:
            buckets[spec].append(ref)

    for spec, refs in sorted(buckets.items(), key=lambda item: str(item[0])):
        parts = {ref_parts[ref] for ref in refs}
        if len(parts) == 1:
            spec_catalog[spec] = parts.pop()
        else:
            diagnostics.append(
                f"spec collision {spec}: {len(refs)} refs, parts {sorted(parts)} (per-ref fallbacks)"
            )

    return spec_catalog, ref_fallbacks, diagnostics


SPEC_CATALOG, REF_FALLBACKS, BUILD_DIAGNOSTICS = build_catalog()


# =============================================================================
# 5.  RESOLUTION API  (used by build_ducktop2.Sheet.place)
# =============================================================================
def resolve(ref: str, value: str, footprint: str) -> Optional[tuple[str, str]]:
    """Returns (manufacturer, mpn) for a passive reference, or None.

    Reviewed refs resolve by reference first (deterministic and exact); specs
    unknown to the catalog fall through to the inverted spec catalog so new
    passives added in later design iterations still get stamped.
    """
    hit = REF_FALLBACKS.get(ref)
    if hit is not None:
        return hit
    spec = parse_spec(value, footprint)
    if spec is not None:
        return SPEC_CATALOG.get(spec)
    return None


# =============================================================================
# 6.  SELF-TEST  (requires the gap CSV; skipped when absent)
# =============================================================================
def selftest() -> int:
    if not GAP_CSV.exists():
        print("no gap CSV: self-test skipped (release-gate copy)")
        return 0
    ref_parts = _ref_parts()
    gap_refs = _load_gap_refs()
    failures = 0
    covered = 0

    for ref, (value, footprint) in sorted(
        gap_refs.items(), key=lambda kv: (kv[0][0], int(re.sub(r"\D", "", kv[0]) or 0))
    ):
        resolved = resolve(ref, value, footprint)
        if resolved is None:
            print(f"FAIL: {ref} ({value}) did not resolve")
            failures += 1
            continue
        expected = ref_parts.get(ref)
        if expected is not None and resolved != expected:
            print(f"FAIL: {ref} resolved {resolved}, expected {expected}")
            failures += 1
            continue
        covered += 1

    orphaned = sorted(ref_parts.keys() - gap_refs.keys())
    if orphaned:
        print(f"note: {len(orphaned)} reviewed refs not in the gap CSV (already stamped): {orphaned[:8]}...")
    print(f"coverage: {covered}/{len(gap_refs)} gap refs resolve to their reviewed part")
    print(f"reviewed parts: {len(ref_parts)} refs, spec catalog entries: {len(SPEC_CATALOG)}")
    if BUILD_DIAGNOSTICS:
        print("build diagnostics:")
        for line in BUILD_DIAGNOSTICS:
            print(f"  {line}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(selftest())
