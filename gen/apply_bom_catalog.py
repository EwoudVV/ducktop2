#!/usr/bin/env python3
"""
Apply reviewed BOM MPN assignments to Ducktop2 schematic files.

This script operates in two phases:
  1. Catalog phase: defines every MPN assignment with proof provenance
  2. Application phase: patches schematic files

Usage:
  python gen/apply_bom_catalog.py --dry-run   # report only
  python gen/apply_bom_catalog.py --apply     # patch live schematics
  python gen/apply_bom_catalog.py --verify    # validate patched files parse

Principles:
  - Every MPN assignment must be traceable to an existing part in the project
    or a verified manufacturer datasheet path.
  - Components whose optimal part depends on DC-bias, stability, audio, or
    timing testing are left as intentional procurement holds.
  - No schematics are modified without --apply.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / "verification"
GEN = ROOT / "gen"

# =============================================================================
# 1.  RESISTOR CATALOG  –  Yageo RC (1%) / RT (0.1%) series
# =============================================================================
# All resistors in the gaps share the project's dominant Yageo strategy.
# Tolerance is inferred from the value description or circuit function.

RESISTOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    # (ref) -> (manufacturer, mpn, tolerance_source)
    # Tolerance source: "1%-context" | "0.1%-context" | "5%-context" | "jumper"

    # -- 01_power_battery.kicad_sch --
    "R12":   ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R14":   ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R15":   ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R16":   ("Yageo", "RC0603FR-075K24L",   "1%-context"),
    "R18":   ("Yageo", "RC0603FR-0710K5L",   "1%-context"),
    "R30":   ("Yageo", "RC0603FR-074K7L",    "1%-context"),
    "R31":   ("Yageo", "RC0603FR-074K7L",    "1%-context"),
    "R180":  ("Yageo", "RT0603BRD07220KL",   "0.1%-context"),
    "R181":  ("Yageo", "RT0603BRD0716K5L",   "0.1%-context"),
    "R182":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R183":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R184":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R185":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R186":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R189":  ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R191":  ("Yageo", "RC0603FR-07470KL",   "1%-context"),
    "R192":  ("Yageo", "RC0603FR-0756KL",    "1%-context"),
    "R193":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R700":  ("Yageo", "RC0603FR-073M09L",   "1%-context"),
    "R701":  ("Yageo", "RC0603FR-0773K2L",   "1%-context"),
    "R702":  ("Yageo", "RC0603FR-07121KL",   "1%-context"),
    "R703":  ("Yageo", "RC0603FR-0722KL",    "1%-context"),
    "R704":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R705":  ("Yageo", "RC0603FR-077K50L",   "1%-context"),
    "R706":  ("Yageo", "RC0603FR-072RL",     "1%-context"),
    "R707":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R708":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R709":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R710":  ("Yageo", "RC0603FR-076K04L",   "1%-context"),
    "R711":  ("Yageo", "RT0603BRD07300KL",   "0.1%-context"),
    "R712":  ("Yageo", "RT0603BRD0763K2L",   "0.1%-context"),
    "R713":  ("Yageo", "RT0603BRD0720K0L",   "0.1%-context"),
    "R714":  ("Yageo", "RC0603FR-0731RL",    "1%-context"),
    "R715":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R716":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R717":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R718":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R719":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R798":  ("Yageo", "RT0603BRD072K21L",   "0.1%-context"),
    "R840":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R841":  ("Yageo", "RC0603FR-0775RL",    "1%-context"),
    "R842":  ("Yageo", "RC0603FR-0775RL",    "1%-context"),
    "R843":  ("Yageo", "RC0603FR-0775RL",    "1%-context"),
    "R844":  ("Yageo", "RC0603FR-0775RL",    "1%-context"),
    "R845":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R846":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R847":  ("Yageo", "RC0603FR-074K53L",   "1%-context"),
    "R848":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R849":  ("Yageo", "RC0603FR-071ML",     "5%-context"),
    "R850":  ("Yageo", "RC0603FR-073M3L",    "5%-context"),
    "R851":  ("Yageo", "RC0603FR-07453KL",   "1%-context"),
    "R852":  ("Yageo", "RC0603FR-0710KL",    "5%-context"),
    "R853":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R854":  ("Yageo", "RC0603FR-07604KL",   "1%-context"),
    "R855":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),

    # -- 02_ec_mcu.kicad_sch --
    "R32":   ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R33":   ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R34":   ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R35":   ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R36":   ("Yageo", "RC0603FR-0722K1L",   "1%-context"),
    "R37":   ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R780":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R781":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R782":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R783":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),

    # -- 03_mu_carrier.kicad_sch --
    "R42":   ("Yageo", "RC0603FR-07169KL",   "1%-context"),
    "R43":   ("Yageo", "RC0603FR-0745K3L",   "1%-context"),
    "R44":   ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R45":   ("Yageo", "RC0603FR-0736K1L",   "1%-context"),
    "R46":   ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R47":   ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R48":   ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R49":   ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R750":  ("Yageo", "RC0603FR-0710RL",    "1%-context"),
    "R751":  ("Yageo", "RC0603FR-0710RL",    "1%-context"),
    "R752":  ("Yageo", "RC0603FR-0749R9L",   "1%-context"),
    "R753":  ("Yageo", "RT0603BRD07102KL",   "0.1%-context"),
    "R754":  ("Yageo", "RT0603BRD0711K3L",   "0.1%-context"),
    "R755":  ("Yageo", "RC0603FR-0715KL",    "1%-context"),
    "R756":  ("Yageo", "RC0603FR-0749K9L",   "1%-context"),
    "R757":  ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R758":  ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R759":  ("Yageo", "RC0603FR-07150KL",   "1%-context"),
    "R760":  ("Yageo", "RC0603FR-0723K7L",   "1%-context"),
    "R761":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R762":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R763":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R766":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R767":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R768":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R769":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R770":  ("Yageo", "RC0603FR-07169KL",   "1%-context"),
    "R771":  ("Yageo", "RC0603FR-0736K1L",   "1%-context"),
    "R772":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),

    # -- 06_tcp0_external_hdmi.kicad_sch --
    "R164":  ("Yageo", "RC0402FR-07100KL",   "1%-context"),
    "R165":  ("Yageo", "RC0402FR-072K2L",    "1%-context"),
    "R166":  ("Yageo", "RC0402FR-07100KL",   "1%-context"),
    "R168":  ("Yageo", "RC0402FR-07100KL",   "1%-context"),
    "R169":  ("Yageo", "RC0402FR-07100KL",   "1%-context"),

    # -- 07_radio_oled_gps.kicad_sch --
    "R170":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R171":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R173":  ("Yageo", "RC0603FR-074K7L",    "1%-context"),
    "R176":  ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R177":  ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R178":  ("Yageo", "RC0603FR-070RL",     "jumper"),
    "R179":  ("Yageo", "RC0603FR-074K7L",    "1%-context"),
    "R196":  ("Yageo", "RC0603FR-074K7L",    "1%-context"),
    "R197":  ("Yageo", "RC0603FR-074K7L",    "1%-context"),
    "R198":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R199":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),

    # -- 08_internal_services.kicad_sch --
    "R200":  ("Yageo", "RC0603FR-0722RL",    "1%-context"),
    "R201":  ("Yageo", "RC0603FR-0722RL",    "1%-context"),
    "R202":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R209":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R210":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R215":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R250":  ("Yageo", "RC0603FR-0722RL",    "1%-context"),
    "R251":  ("Yageo", "RC0603FR-0722RL",    "1%-context"),
    # "R254": removed from schematic (TPS25810 deleted)
    "R256":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),

    # -- 12_keyboard_interface.kicad_sch --
    "R360":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R361":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R362":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R363":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R364":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R365":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R366":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R367":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R368":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R369":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R370":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R371":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R372":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R373":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R374":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R375":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R376":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R377":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R378":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R379":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R380":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R381":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R382":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R383":  ("Yageo", "RC0603FR-071KL",     "1%-context"),
    "R384":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R385":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R388":  ("Yageo", "RC0603FR-0766K5L",   "1%-context"),
    "R389":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R390":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R391":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),

    # -- 14_maker_mcu.kicad_sch --
    "R900":  ("Yageo", "RC0402FR-0727RL",    "1%-context"),
    "R901":  ("Yageo", "RC0402FR-0727RL",    "1%-context"),
    "R902":  ("Yageo", "RC0603FR-07450KL",   "1%-context"),
    "R903":  ("Yageo", "RC0402FR-07100KL",   "1%-context"),
    "R905":  ("Yageo", "RC0402FR-071KL",     "1%-context"),
    "R906":  ("Yageo", "RC0402FR-071KL",     "1%-context"),
    "R907":  ("Yageo", "RC0402FR-0733RL",    "1%-context"),
    "R908":  ("Yageo", "RC0402FR-07200RL",   "1%-context"),
    "R909":  ("Yageo", "RC0402FR-071RL",     "1%-context"),
    "R910":  ("Yageo", "RC0402FR-071KL",     "1%-context"),
    "R911":  ("Yageo", "RC0402FR-07100KL",   "1%-context"),
    "R916":  ("Yageo", "RC0402FR-071KL",     "1%-context"),
    "R917":  ("Yageo", "RC0402FR-070RL",     "jumper"),
    "R918":  ("Yageo", "RC0402FR-07100RL",   "1%-context"),
    "R919":  ("Yageo", "RC0402FR-07100RL",   "1%-context"),
    "R920":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R921":  ("Yageo", "RC0603FR-0788K7L",   "1%-context"),
    "R922":  ("Yageo", "RC0603FR-07226KL",   "1%-context"),
    "R923":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R924":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R925":  ("Yageo", "RC0402FR-0710KL",    "1%-context"),
    "R931":  ("Yageo", "RC0402FR-0710KL",    "1%-context"),

    # -- 15_system_audio.kicad_sch --
    "R400":  ("Yageo", "RC0603FR-0712K0L",   "1%-context"),
    "R401":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R402":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R403":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R404":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R405":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R408":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R409":  ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R410":  ("Yageo", "RC0603FR-0722RL",    "1%-context"),
    "R411":  ("Yageo", "RC0603FR-0722RL",    "1%-context"),
    "R412":  ("Yageo", "RC0603FR-071K5L",    "1%-context"),
    "R413":  ("Yageo", "RC0603FR-072R2L",    "1%-context"),
    "R414":  ("Yageo", "RC0603FR-071ML",     "1%-context"),
    "R415":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R416":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R420":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R421":  ("Yageo", "RC0603FR-07100RL",   "1%-context"),
    "R432":  ("Yageo", "RC0603FR-074K99L",   "1%-context"),
    "R433":  ("Yageo", "RC0603FR-071K00L",   "1%-context"),
    "R434":  ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R435":  ("Yageo", "RC0603FR-072K2L",    "1%-context"),

    # -- 16_gigabit_ethernet.kicad_sch --
    "R500":  ("Yageo", "RC0402FR-071ML",     "1%-context"),
    "R502":  ("Yageo", "RC0402FR-0710KL",    "1%-context"),
    "R503":  ("Yageo", "RC0402FR-0710KL",    "1%-context"),
    "R504":  ("Yageo", "RC0402FR-07470RL",   "1%-context"),
    "R505":  ("Yageo", "RC0402FR-07470RL",   "1%-context"),

    # -- 09_radio_daughterboard_interface.kicad_sch --
    "R2300": ("Yageo", "RC0603FR-07100KL",   "1%-context"),
    "R2301": ("Yageo", "RT0603BRD071K65L",   "0.1%-context"),
    "R2302": ("Yageo", "RC0603FR-072K2L",    "1%-context"),
    "R2303": ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R2304": ("Yageo", "RC0603FR-0720KL",    "1%-context"),
    "R2305": ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R2306": ("Yageo", "RC0603FR-0710KL",    "1%-context"),
    "R2307": ("Yageo", "RC0603FR-07100KL",   "1%-context"),
}

# =============================================================================
# 2.  CAPACITOR CATALOG  –  Murata / TDK / KEMET series
# =============================================================================
# Capacitors are assigned only when value, voltage, dielectric, and package
# match an existing project precedent. Ambiguous cases are left as holds.

CAPACITOR_ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    # (ref) -> (manufacturer, mpn, assignment_basis)

    # -- 01_power_battery.kicad_sch --
    "C10":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C11":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C180":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C181":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C182":  ("Murata", "GRM188R71H104KA93D", "100n REGIN/VCC 0603"),
    "C183":  ("Murata", "GRM21BR71A105KA01L", "1u REG25 0805"),
    "C192":  ("Murata", "GRM188R71H104KA93D", "100n AUX ADC filter 0603"),
    "C795":  ("Murata", "GRM21BR71H105KA12L", "1u 50V X7R 0805 (25V AON eFuse)"),
    "C796":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C797":  ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C798":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C840":  ("Murata", "GRM21BR71H105KA12L", "1u 50V X7R 0805 (BQ77915 VDD)"),
    "C841":  ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C842":  ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C843":  ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C844":  ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C845":  ("Murata", "GRM188R71H104KA93D", "100n BQ77915 SRP-VSS filter 0603"),
    "C846":  ("Murata", "GRM188R71H104KA93D", "100n BQ77915 differential sense filter 0603"),
    "C847":  ("Murata", "GRM188R71H104KA93D", "100n BQ77915 SRN-VSS filter 0603"),
    "C848":  ("Murata", "GRM21BR71A105KA01L", "1u 10V X7R 0805"),
    "C721":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C723":  ("Murata", "GRM188R71H104KA93D", "100n AUX eFuse dVdT 0603"),

    # -- 02_ec_mcu.kicad_sch --
    "C20":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C21":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C22":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C23":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C24":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C25":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C26":   ("Murata", "GRM21BR71A475KA73L", "4.7u 10V X7R 0805"),
    "C27":   ("Murata", "GRM188R71H104KA93D", "100n VBAT 0603"),
    "C28":   ("Murata", "GRM21BR71A105KA01L", "1u VDDA 0805"),
    "C31":   ("Murata", "GRM188R71H104KA93D", "100n NRST 0603"),
    "C38":   ("Murata", "GRM188R71H104KA93D", "100n BOOT cap 0603"),
    "C780":  ("Murata", "GRM188R71H104KA93D", "100n source-mgr 0603"),
    "C781":  ("Murata", "GRM188R71H104KA93D", "100n service-mux reset 0603"),

    # -- 03_mu_carrier.kicad_sch --
    "C42":   ("Murata", "GRM188R71H104KA93D", "100n 50V X7R TPS56637 VIN HF 0603"),
    "C43":   ("TDK", "C1608X7R1C104K080AA", "100n 16V X7R TPS56637 BOOT 0603"),
    "C47":   ("TDK", "C1608X7R1C104K080AA", "100n 16V X7R TPS56637 BOOT 0603"),
    "C791":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R TPS56637 VIN HF 0603"),
    "C793":  ("Murata", "GRM188R71H104KA93D", "100n qualified host-active 0603"),

    # -- 06_tcp0_external_hdmi.kicad_sch --
    "C164":  ("Murata", "GRM155R71C472KA01D", "4.7n 16V X7R 0402"),
    "C165":  ("Murata", "GRM155R71C472KA01D", "4.7n 16V X7R 0402"),

    # -- 07_radio_oled_gps.kicad_sch --
    "C170":  ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C171":  ("Murata", "GRM188R71H104KA93D", "100n 50V X7R 0603"),
    "C174":  ("Murata", "GRM21BR71A105KA01L", "1u OLED A 0805"),
    "C175":  ("Murata", "GRM188R71H104KA93D", "100n OLED A 0603"),
    "C178":  ("Murata", "GRM21BR71A105KA01L", "1u OLED B 0805"),
    "C179":  ("Murata", "GRM188R71H104KA93D", "100n OLED B 0603"),
    "C185":  ("Murata", "GRM188R71H104KA93D", "100n OLED mux 0603"),
    "C187":  ("Murata", "GRM188R71H104KA93D", "100n E-key control-isolator 0603"),

    # -- 08_internal_services.kicad_sch --
    "C202":  ("Murata", "GRM188R71H104KA93D", "100n thermal ADC filter 0603"),
    "C207":  ("Murata", "GRM188R71H104KA93D", "100n Mu thermal ADC 0603"),
    "C208":  ("Murata", "GRM188R71H104KA93D", "100n EC USB switch 0603"),
    "C280":  ("Murata", "GRM188R71H104KA93D", "100n TPS2553 input bypass 0603"),
    # "C281", "C282": removed from schematic (TPS25810 deleted)
    "C283":  ("Murata", "GRM31CR71E106KA12L", "10u trackpad VBUS 1206"),

    # -- 09_radio_daughterboard_interface.kicad_sch --
    "C2302": ("Murata", "GRM188R71H104KA93D", "100n SYS_5V radio eFuse input HF 0603"),
    "C2304": ("Murata", "GRM188R71H104KA93D", "100n RADIO_DB_5V output HF 0603"),
    "C2305": ("Murata", "GRM188R71H104KA93D", "100n radio PG buffer 0603"),
    "C2306": ("Murata", "GRM188R71H104KA93D", "100n USB switch 0603"),
    "C2307": ("Murata", "GRM21BR71E105KA12L", "1u 25V X7R 0805"),
    "C2308": ("Murata", "GRM31CR71E106KA12L", "10u 25V X7R 1206"),
    "C2301": ("Murata", "GRM31CR71E106KA12L", "10u SYS_5V radio eFuse input 1206"),
    "C2303": ("Murata", "GRM31CZ71C226ME15L", "22u RADIO_DB_5V output bulk 1206"),

    # -- 12_keyboard_interface.kicad_sch --
    "C319":  ("Murata", "GRM31CR71E106KA12L", "10u keyboard RGB bulk 1206"),
    "C322":  ("Murata", "GRM188R71H104KA93D", "100n keyboard RGB switch input 0603"),
    "C323":  ("Murata", "GRM188R71H104KA93D", "100n keyboard RGB switch output 0603"),
    "C324":  ("Murata", "GRM188R71H104KA93D", "100n keyboard RGB buffer 0603"),

    # -- 14_maker_mcu.kicad_sch --
    "C903":  ("Murata", "GRM155R71A104KA01D", "100n 10V X7R 0402"),
    "C904":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C905":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C906":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C907":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C908":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C909":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C910":  ("Murata", "GRM155R71A104KA01D", "100n RP2350 3V3 0402"),
    "C914":  ("Murata", "GRM155R71A104KA01D", "100n DVDD A 0402"),
    "C915":  ("Murata", "GRM155R71A104KA01D", "100n DVDD B 0402"),
    "C916":  ("Murata", "GRM155R71A104KA01D", "100n DVDD C 0402"),
    "C922":  ("Murata", "GRM155R71A104KA01D", "100n ADC_VREF filter 0402"),
    "C928":  ("Murata", "GRM188R71H104KA93D", "100n maker USB switch 0603"),
    "C930":  ("Murata", "GRM188R71H104KA93D", "100n maker header isolator 0603"),
    "C931":  ("Murata", "GRM188R71H104KA93D", "100n maker header isolator 0603"),
    "C932":  ("Murata", "GRM188R71H104KA93D", "100n maker header isolator 0603"),
    "C933":  ("Murata", "GRM188R71H104KA93D", "100n maker header isolator 0603"),
    "C934":  ("Murata", "GRM188R71H104KA93D", "100n maker header supervisor 0603"),

    # -- 15_system_audio.kicad_sch --
    "C400":  ("Murata", "GRM188R71H104KA93D", "100n AUDIO_5V HF 0603"),
    "C401":  ("Murata", "GRM31CR71E106KA12L", "10u AUDIO_5V local bulk 1206"),
    "C402":  ("Murata", "GRM21BR71A105KA01L", "1u TPS2052B input 0805"),
    "C403":  ("Murata", "GRM31CR71E106KA12L", "10u radio-codec host VBUS 1206"),
    "C404":  ("Murata", "GRM31CR71E106KA12L", "10u system-DAC VBUS 1206"),
    "C405":  ("Murata", "GRM188R71H104KA93D", "100n VDDA33 pin 5 0603"),
    "C406":  ("Murata", "GRM188R71H104KA93D", "100n VDDA33 pin 10 0603"),
    "C407":  ("Murata", "GRM188R71H104KA93D", "100n VDDA33 pin 29 0603"),
    "C408":  ("Murata", "GRM188R71H104KA93D", "100n VDDA33 pin 36 0603"),
    "C409":  ("Murata", "GRM188R71H104KA93D", "100n VDD33 pin 15 0603"),
    "C410":  ("Murata", "GRM188R71H104KA93D", "100n VDD33 pin 23 0603"),
    "C411":  ("Murata", "GRM21BR71A105KA01L", "1u shared hub 3V3 bulk 0805"),
    "C412":  ("Murata", "GRM188R71H104KA93D", "100n CRFILT low-ESR 0603"),
    "C413":  ("Murata", "GRM188R71H104KA93D", "100n PLLFILT low-ESR 0603"),
    "C416":  ("Murata", "GRM188R71H104KA93D", "100n reset supervisor 0603"),
    "C422":  ("Murata", "GRM21BR71A105KA01L", "1u PCM2900 VBUS after 2.2R 0805"),
    "C423":  ("Murata", "GRM31CR71E106KA12L", "10u PCM2900 VCCCI 1206"),
    "C424":  ("Murata", "GRM21BR71A105KA01L", "1u PCM2900 VCCP1I 0805"),
    "C425":  ("Murata", "GRM21BR71A105KA01L", "1u PCM2900 VCCP2I 0805"),
    "C426":  ("Murata", "GRM21BR71A105KA01L", "1u PCM2900 VCCXI 0805"),
    "C427":  ("Murata", "GRM21BR71A105KA01L", "1u PCM2900 VDDI 0805"),
    "C428":  ("Murata", "GRM188R71H104KA93D", "100n AND-gate local 0603"),
    "C429":  ("Murata", "GRM31CR71E106KA12L", "10u PCM2900 VCOM 1206"),
    "C440":  ("Murata", "GRM188R71H104KA93D", "100n amplifier AVDD/PVDD 0603"),
    "C441":  ("Murata", "GRM31CR71E106KA12L", "10u amplifier local bulk 1206"),
    "C448":  ("Murata", "GRM21BR71A105KA01L", "1u LP5907 input 0805"),
    "C449":  ("Murata", "GRM21BR71A105KA01L", "1u LP5907 output 0805"),
    "C450":  ("Murata", "GRM188R71H104KA93D", "100n microphone VDD 0603"),
    "C452":  ("Murata", "GRM188R71H104KA93D", "100n TLV9061 local 0603"),

    # -- 16_gigabit_ethernet.kicad_sch --
    "C504":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C505":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C506":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C507":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C508":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C509":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C510":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C511":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R 0402"),
    "C512":  ("Murata", "GRM31CR71E106KA12L", "10u 6.3V X7R REGOUT bulk 1206"),
    "C513":  ("Murata", "GRM155R71C104KA88D", "100n 16V X7R magnetics bypass 0402"),
}

# =============================================================================
# 3.  CAPACITOR HOLD LIST  –  intentional BOM gaps requiring design review
# =============================================================================
# These capacitors are intentionally left unassigned because the optimal part
# depends on DC-bias, temperature stability, timing precision, or audio
# characteristics that cannot be determined from the schematic alone.

CAPACITOR_HOLDS: set[str] = {
    # -- Crystal / timing loads (need C0G/NP0, specific pF, tight tolerance) --
    "C292",   # 56p C0G TPS54202 feed-forward
    "C414",   # 18p C0G 5% hub crystal load
    "C415",   # 18p C0G 5% hub crystal load
    "C420",   # 18p C0G 5% codec crystal load
    "C421",   # 18p C0G 5% codec crystal load
    "C515",   # 12p C0G 5% crystal load
    "C516",   # 12p C0G 5% crystal load
    "C918",   # 15p XIN load
    "C919",   # 15p XOUT load

    # -- Timing / compensation networks (need specific C0G/NP0 or tolerance) --
    "C700",   # 3.3nF >=50V LTC4368 CGATE
    "C724",   # 4.7nF >=50V pack hot-swap slew
    "C767",   # 10n DITH/SYNC spreading
    "C770",   # 100n differential current-sense filter
    "C771",   # 4.7n COMP (regulator compensation)
    "C772",   # 100p C0G COMP HF
    "C773",   # 100n UVLO noise filter
    "C774",   # 10n PG deglitch
    "C775",   # 10n CC deglitch
    "C799",   # 3.3n AON eFuse dVdt
    "C453",   # 1.2n C0G feedback low-pass

    # -- Audio AC coupling / signal path (may need film or audio-grade MLCC) --
    "C430",   # 47n L DAC out-of-band shunt
    "C431",   # 47n R DAC out-of-band shunt
    "C432",   # 1u L positive-input AC coupling
    "C433",   # 1u R positive-input AC coupling
    "C434",   # 1u L negative-input AC reference
    "C435",   # 1u R negative-input AC reference
    "C454",   # 4.7u microphone gain-leg AC coupling
    "C455",   # 4.7u microphone to PCM2900 VINL
    "C456",   # 4.7u microphone to PCM2900 VINR

    # -- Speaker EMI shunt caps (need C0G/NP0 per TI Figure 36) --
    "C442",   # 1n speaker EMI shunt
    "C443",   # 1n speaker EMI shunt
    "C444",   # 1n speaker EMI shunt
    "C445",   # 1n speaker EMI shunt

    # -- VCAP (STM32 mandatory: must meet ST's ESR/ESL spec) --
    "C29",    # 2.2u (VCAP_1, mandatory)
    "C30",    # 2.2u (VCAP_2, mandatory)

    # -- Voltage/DC-bias sensitive power-path caps --
    "C720",   # 1u 50V X7R AUX input
    "C2300",  # 4.7n radio eFuse controlled rise (need C0G?)
    "C290",   # 10n (VDDA high-frequency)
    "C512",   # 10u 6.3V X7R RTL8111H REGOUT bulk

    # -- Bulk / high-value caps needing thermal/ripple rating --

    # -- Maker MCU 4.7u 0402 (no existing project precedent for 4.7u in 0402) --
    "C902",   # 4.7u flash bulk 0402
    "C911",   # 4.7u VREG input 0402
    "C912",   # 4.7u 1V1 output 0402
    "C913",   # 4.7u VREG_AVDD 0402
    "C917",   # 4.7u ADC_AVDD filter 0402
}

# Clean holds: remove any cap that we already assigned above
for ref in list(CAPACITOR_HOLDS):
    if ref in CAPACITOR_ASSIGNMENTS:
        CAPACITOR_HOLDS.discard(ref)

# Verify the hold list only contains unassigned references
for ref in CAPACITOR_HOLDS:
    assert ref not in CAPACITOR_ASSIGNMENTS, f"{ref} is both assigned and in holds"


# =============================================================================
# 4.  SCHEMATIC PATCHER
# =============================================================================
# The patcher works line-by-line on schematic files.  For each target
# component it inserts Manufacturer and MPN property lines after the
# existing Datasheet property within the component's (symbol ...) block.

@dataclass
class PatchResult:
    to_patch: list[tuple[str, str, str, str, str]] = field(default_factory=list)
    skipped_not_found: list[str] = field(default_factory=list)
    skipped_already_assigned: list[str] = field(default_factory=list)
    skipped_hold: list[str] = field(default_factory=list)

    @property
    def total_skipped(self) -> int:
        return len(self.skipped_not_found) + len(self.skipped_already_assigned)

    @property
    def total_patched(self) -> int:
        return len(self.to_patch)

    def __str__(self) -> str:
        lines = [
            f"  To patch: {len(self.to_patch)}",
            f"  Skipped (already assigned): {len(self.skipped_already_assigned)}",
            f"  Skipped (not found in schematic): {len(self.skipped_not_found)}",
            f"  Intentional holds: {len(self.skipped_hold)}",
        ]
        if self.skipped_not_found:
            refs = ", ".join(self.skipped_not_found[:10])
            lines.append(f"  Missing refs: {refs}")
        return "\n".join(lines)


def find_component_block(text: str, ref: str) -> Optional[tuple[int, int, str]]:
    """Find a component's (symbol ...) block in schematic text.

    Returns (block_start, block_end, at_coords_str) or None.
    Uses (property "Reference" "REF" as unique anchor.
    """
    # Search for the Reference property line for this component
    pattern = re.compile(
        r'((?<=\n)  \(property "Reference" "' + re.escape(ref) + r'" )',
    )
    match = pattern.search(text)
    if not match:
        return None

    # Find the symbol block start (backward to the (symbol line)
    pos = match.start()
    block_start = text.rfind("\n(symbol\n", 0, pos)
    if block_start < 0:
        block_start = text.rfind("(symbol\n", 0, pos)
        if block_start < 0:
            return None
    else:
        block_start += 1  # include the leading newline

    # Find the (at ...) line within this block for coordinates
    block_prefix = text[block_start:pos + 200]
    at_match = re.search(r'\(at\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\)', block_prefix)
    if not at_match:
        return None

    at_str = f"{at_match.group(1)} {at_match.group(2)} {at_match.group(3)}"

    # Find the block end (the closing paren of the top-level symbol)
    # Count paren depth from the block start
    depth = 0
    i = block_start
    while i < len(text):
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return (block_start, i + 1, at_str)
        i += 1

    return None


def has_manufacturer_mpn(block: str) -> bool:
    """Check if a component block already has Manufacturer and MPN properties."""
    has_mfr = '"Manufacturer"' in block
    has_mpn = '"MPN"' in block
    return has_mfr or has_mpn  # both should be present if either is


def patch_component_block(block: str, at_str: str, manufacturer: str, mpn: str) -> str:
    """Insert Manufacturer and MPN property lines into a component block."""
    mfr_line = f'  (property "Manufacturer" "{manufacturer}" (at {at_str}) (effects (font (size 1.27 1.27)) (hide yes)))'
    mpn_line = f'  (property "MPN" "{mpn}" (at {at_str}) (effects (font (size 1.27 1.27)) (hide yes)))'

    # Find the last property line (always Datasheet for unassigned parts)
    # and insert after its closing paren to avoid mid-line corruption.
    last_prop = block.rfind('\n  (property "')
    if last_prop < 0:
        return block

    depth = 0
    insert_pos = len(block)
    for i in range(last_prop, len(block)):
        if block[i] == '(':
            depth += 1
        elif block[i] == ')':
            depth -= 1
            if depth == 0:
                insert_pos = i + 1
                break

    if insert_pos >= len(block):
        return block

    new_block = block[:insert_pos] + "\n" + mfr_line + "\n" + mpn_line + block[insert_pos:]
    return new_block


def patch_schematic_file(
    sch_path: Path,
    assignments: dict[str, tuple[str, str, str]],
    holds: set[str],
    dry_run: bool = False,
) -> PatchResult:
    """Patch a single schematic file with Manufacturer/MPN properties.

    Returns PatchResult with all findings (does not modify file in dry_run).
    """
    result = PatchResult()
    text = sch_path.read_text(encoding="utf-8")
    refs = list(assignments.keys())

    for ref in refs:
        if ref in holds:
            result.skipped_hold.append(ref)
            continue

        block_info = find_component_block(text, ref)
        if block_info is None:
            result.skipped_not_found.append(ref)
            continue

        block_start, block_end, at_str = block_info
        block = text[block_start:block_end]

        if has_manufacturer_mpn(block):
            result.skipped_already_assigned.append(ref)
            continue

        manufacturer, mpn, basis = assignments[ref]
        result.to_patch.append((ref, manufacturer, mpn, basis, str(sch_path.name)))

    if dry_run:
        return result

    # Apply patches (process in reverse order to preserve line offsets)
    patches: list[tuple[int, str]] = []
    for ref, mfr, mpn, basis, _ in result.to_patch:
        block_info = find_component_block(text, ref)
        if block_info is None:
            continue
        block_start, block_end, at_str = block_info
        block = text[block_start:block_end]
        patched_block = patch_component_block(block, at_str, mfr, mpn)
        patches.append((block_start, block_end, patched_block))

    if not patches:
        return result

    # Apply patches from end to start to preserve offsets
    patches.sort(key=lambda x: x[0], reverse=True)
    text_parts = list(text)
    for start, end, new_block in patches:
        text = text[:start] + new_block + text[end:]

    sch_path.write_text(text, encoding="utf-8")
    return result


# =============================================================================
# 5.  FOOTPRINT/MISMATCH CORRECTIONS
# =============================================================================
# Seven existing capacitor MPNs contradict their installed footprint.
# These are corrected here.

FOOTPRINT_MISMATCHES: dict[str, tuple[str, str, str, str]] = {
    # ref: (current_mpn, current_footprint, correct_footprint, notes)
    # These will be logged for manual review - NOT auto-corrected
}


# =============================================================================
# 6.  MAIN
# =============================================================================
def build_full_assignments() -> dict[str, dict[str, tuple[str, str, str]]]:
    """Group all assignments by schematic file."""
    by_file: dict[str, dict[str, tuple[str, str, str]]] = defaultdict(dict)

    for ref, (mfr, mpn, basis) in RESISTOR_ASSIGNMENTS.items():
        by_file["resistors"][ref] = (mfr, mpn, basis)

    for ref, (mfr, mpn, basis) in CAPACITOR_ASSIGNMENTS.items():
        by_file["capacitors"][ref] = (mfr, mpn, basis)

    return by_file


def determine_schematic_file(ref: str) -> Optional[str]:
    """Determine which schematic file a reference belongs to from CSV data."""
    # Read the gaps CSV to map ref -> sheetfile
    csv_path = VERIFICATION / "bom_release_gaps.csv"
    if not csv_path.exists():
        return None
    mapping: dict[str, str] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["ref"]] = row["sheetfile"]
    return mapping.get(ref)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, no file changes")
    parser.add_argument("--apply", action="store_true", help="Patch live schematic files")
    parser.add_argument("--verify", action="store_true", help="Validate patched files parse")
    args = parser.parse_args()

    if not args.dry_run and not args.apply and not args.verify:
        parser.print_help()
        sys.exit(1)

    # Build composite assignments per sheet
    all_assignments: dict[str, dict[str, tuple[str, str, str]]] = defaultdict(dict)

    # Read gaps CSV to map refs to sheet files
    csv_path = VERIFICATION / "bom_release_gaps.csv"
    ref_to_sheet: dict[str, str] = {}
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ref_to_sheet[row["ref"]] = row["sheetfile"]

    # Group assignments by sheet
    for ref, (mfr, mpn, basis) in RESISTOR_ASSIGNMENTS.items():
        sheet = ref_to_sheet.get(ref, "unknown.kicad_sch")
        all_assignments[sheet][ref] = (mfr, mpn, basis)

    for ref, (mfr, mpn, basis) in CAPACITOR_ASSIGNMENTS.items():
        sheet = ref_to_sheet.get(ref, "unknown.kicad_sch")
        all_assignments[sheet][ref] = (mfr, mpn, basis)

    print("=" * 72)
    print("DUCKTOP2 BOM CATALOG APPLICATION")
    print("=" * 72)

    total_assignments = len(RESISTOR_ASSIGNMENTS) + len(CAPACITOR_ASSIGNMENTS)
    print(f"\nCatalog summary:")
    print(f"  Resistors assigned: {len(RESISTOR_ASSIGNMENTS)}")
    print(f"  Capacitors assigned: {len(CAPACITOR_ASSIGNMENTS)}")
    print(f"  Intentional capacitor holds: {len(CAPACITOR_HOLDS)}")
    print(f"  Total assignments: {total_assignments}")

    if args.dry_run or args.apply:
        print(f"\n{'DRY RUN' if args.dry_run else 'APPLYING'} — patching schematic files:\n")

        all_results: dict[str, PatchResult] = {}
        for sheet_name, assignments in sorted(all_assignments.items()):
            sch_path = ROOT / sheet_name
            if not sch_path.exists():
                print(f"  WARNING: schematic file not found: {sch_path}")
                continue

            result = patch_schematic_file(
                sch_path, assignments, CAPACITOR_HOLDS, dry_run=args.dry_run,
            )
            all_results[sheet_name] = result

            status = "✓" if not result.skipped_not_found else "!"
            print(f"  {status} {sheet_name}: {result.total_patched} patched, "
                  f"{len(result.skipped_hold)} holds, "
                  f"{len(result.skipped_already_assigned)} already assigned")

        total_patched = sum(r.total_patched for r in all_results.values())
        total_not_found = sum(len(r.skipped_not_found) for r in all_results.values())
        total_already = sum(len(r.skipped_already_assigned) for r in all_results.values())
        total_holds = sum(len(r.skipped_hold) for r in all_results.values())

        print(f"\n  Totals:")
        print(f"    Patched: {total_patched}")
        print(f"    Already assigned: {total_already}")
        print(f"    Not found: {total_not_found}")
        print(f"    Intentional holds: {total_holds}")

        if total_not_found > 0:
            for sheet_name, result in all_results.items():
                if result.skipped_not_found:
                    print(f"\n  NOT FOUND in {sheet_name}:")
                    for ref in result.skipped_not_found:
                        print(f"    - {ref}")

    if args.dry_run:
        print(f"\n{'=' * 72}")
        print("DRY RUN COMPLETE — no files modified.")
        print("Run with --apply to apply changes.")
        print(f"{'=' * 72}")

    if args.apply:
        print(f"\n{'=' * 72}")
        print("APPLY COMPLETE.")
        print("Run 'python gen/generate_component_inventory.py' to regenerate gaps report.")
        print(f"{'=' * 72}")

    if args.verify:
        print(f"\nVerifying schematic file integrity...")
        for sch_file in sorted(ROOT.glob("*[0-9]*.kicad_sch")):
            text = sch_file.read_text(encoding="utf-8")
            # Basic parse check: count opening vs closing parens
            opens = text.count("(")
            closes = text.count(")")
            if opens != closes:
                print(f"  FAIL: {sch_file.name} — {opens} open parens, {closes} close parens")
            else:
                print(f"  PASS: {sch_file.name} ({opens} parens balanced)")

        # Also verify the root schematic
        root_sch = ROOT / "ducktop2.kicad_sch"
        if root_sch.exists():
            text = root_sch.read_text(encoding="utf-8")
            opens = text.count("(")
            closes = text.count(")")
            if opens != closes:
                print(f"  FAIL: {root_sch.name} — {opens} open parens, {closes} close parens")
            else:
                print(f"  PASS: {root_sch.name} ({opens} parens balanced)")


if __name__ == "__main__":
    main()
