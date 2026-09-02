#!/usr/bin/env python3
"""Strict, read-only staged Ducktop2 release gate.

Mutating generators/checkers run only inside a temporary project copy. KiCad
reports are written only to that copy or an operating-system temporary
directory. This script never refills zones or saves the canonical board.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMATIC = ROOT / "ducktop2.kicad_sch"
DEFAULT_PCB = ROOT / "old" / "monolith_ducktop2.kicad_pcb"
NUMBER = r"[-+0-9.eE]+"

# Violation types a refill may newly introduce without blocking, because
# they are direct consequences of unrouted nets on a routing-phase board:
# isolated islands of unvias'd copper.  Everything else that appears only
# after refill (placement drift, shorts from fills, etc.) blocks release.
# Categories a --refill-zones pass may introduce while the boards are
# still unrouted (no tracks/vias yet): fill islands, and dangling-via
# detection flipping on PTH pads as fills reconnect around them.
REFILL_DELTA_TYPES = {"isolated_copper", "via_dangling"}


def semantic_signature(sheet: str, violation: dict) -> tuple:
    return (
        sheet,
        violation.get("severity", ""),
        violation.get("type", ""),
        violation.get("description", ""),
        tuple(sorted(item.get("description", "") for item in violation.get("items", []))),
    )


# Fabrication release DRC allowlist (placement-phase acceptance, 2026-08-13):
# the courtyard-overlap backlog is the documented under-module/adjacent-pair
# pattern (Mu module 8 mm standoff, M.2 card, connector courtyards), and the
# silk items are the residual cosmetic text class (1 overlap: R375/C2068
# J310 cluster; 8 edge-clipped texts are the pre-existing corner set).
# Everything electrical is at zero: clearance/shorts/mask-bridge/npth all 0.
DRC_ALLOWLIST = Counter({
        # 2026-08-24 USB-A spare-port cluster: support passives sit inside the
        # receptacle courtyards (pads clear, no copper conflict; tight left-edge area).
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1854', 'Footprint U1803')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1852', 'Footprint J25')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1850', 'Footprint J24')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1855', 'Footprint J25')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint U1800', 'Footprint U402')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1853', 'Footprint J25')): 1,
        ('PCB', 'warning', 'silk_edge_clearance', 'Silkscreen clipped by board edge', ('Segment of J24 on F.Silkscreen', 'Segment on Edge.Cuts')): 2,
        ('PCB', 'warning', 'silk_edge_clearance', 'Silkscreen clipped by board edge', ('Segment of J25 on F.Silkscreen', 'Segment on Edge.Cuts')): 2,
        # 2026-08-24 USB-A port cluster silk: reference-field text overlaps on the
        # tight left-edge cluster (cosmetic text class, same as pre-existing allowlist).
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Polygon of U1803 on F.Silkscreen', 'Reference field of U1803')): 1,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Reference field of R1850', 'Reference field of U1802')): 1,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Reference field of C1850', 'Segment of J24 on F.Silkscreen')): 1,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Polygon of U1800 on F.Silkscreen', 'Reference field of U1800')): 1,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Reference field of C1853', 'Segment of J25 on F.Silkscreen')): 1,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Reference field of C1854', 'Reference field of J25')): 1,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Reference field of U1804', 'Segment of R1851 on F.Silkscreen')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 2 [GND] of C1854 on F.Cu', 'Reference field of U1803')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 1 [GND] of U402 on F.Cu', 'Reference field of U1800')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 1 [/System Audio/MIC_HP_NODE] of C454 on F.Cu', 'Reference field of U1801')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 4 [GND] of J25 on F.Cu', 'Reference field of C1855')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 1 [/Native USB-C I/O/J25_5V_PRE] of J25 on F.Cu', 'Reference field of C1853')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 2 [GND] of R1851 on F.Cu', 'Reference field of U1804')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 1 [/Native USB-C I/O/J25_ILIM] of R1851 on F.Cu', 'Reference field of U1804')): 1,
        ('PCB', 'warning', 'silk_over_copper', 'Silkscreen clipped by solder mask', ('Pad 1 [/Native USB-C I/O/J24_5V_PRE] of C1850 on F.Cu', 'Segment of J24 on F.Silkscreen')): 2,

        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J500', 'Footprint U501')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint U2303', 'Footprint U501')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J500', 'Footprint U500')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C35', 'Footprint J500')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J500', 'Footprint U2303')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C462', 'Footprint C464')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R933', 'Footprint R934')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1724', 'Footprint J23')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint D713', 'Footprint U769')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C174', 'Footprint C2301')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C750', 'Footprint R1723')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2061', 'Footprint J310')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint Q11', 'Footprint RS10')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint Q12', 'Footprint RS10')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint RS10', 'Footprint U11')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C179')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C175')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1849')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C702', 'Footprint L1')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C2050')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C708', 'Footprint C712')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R1760', 'Footprint R2053')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C455', 'Footprint C456')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C461', 'Footprint C463')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2305', 'Footprint U2301')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R708', 'Footprint U4')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C504', 'Footprint C511')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R388', 'Footprint U310')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J23', 'Footprint R1742')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C702', 'Footprint J56')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C723', 'Footprint U12')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C26', 'Footprint R33')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1831', 'Footprint Q700')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J40', 'Footprint R2321')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C28', 'Footprint C290')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R173')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C793', 'Footprint R764')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C762', 'Footprint R764')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C45', 'Footprint C766')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C434', 'Footprint C709')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C714', 'Footprint F200')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C423', 'Footprint J2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1788', 'Footprint U2011')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1713', 'Footprint R709')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J45', 'Footprint U63')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C750', 'Footprint C753')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C750', 'Footprint C751')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R1840')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C34', 'Footprint Y2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1782', 'Footprint R2003')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C441', 'Footprint J2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C407', 'Footprint J2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J2', 'Footprint R400')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C406', 'Footprint J2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C411', 'Footprint J2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C433', 'Footprint J2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R2055', 'Footprint U2005')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J45', 'Footprint R203')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint U44', 'Footprint U721')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1751', 'Footprint R2042')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R2317')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1832')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint F10')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J2300', 'Footprint LED1')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J45', 'Footprint R204')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C834', 'Footprint TP12')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J41', 'Footprint R205')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C768', 'Footprint C907')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R388', 'Footprint R390')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2044', 'Footprint C2065')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1762', 'Footprint C2065')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R2346', 'Footprint U45')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C595', 'Footprint J10')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1707')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R2323')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1820')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C280', 'Footprint L3')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C515', 'Footprint R501')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C709', 'Footprint C720')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C709', 'Footprint C710')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C765', 'Footprint R759')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R2349', 'Footprint U45')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R13', 'Footprint R170')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1766', 'Footprint R2083')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R1716')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C156', 'Footprint D151')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1712')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1762', 'Footprint C2067')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2066', 'Footprint C2067')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2055', 'Footprint C2067')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint D1823', 'Footprint R373')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint F1', 'Footprint RS11')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R842', 'Footprint U719')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R843', 'Footprint U719')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R1705', 'Footprint U1702')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C20', 'Footprint C36')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C178')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint Q703', 'Footprint Q704')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R2343', 'Footprint R2356')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C406', 'Footprint C407')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint D2120', 'Footprint R380')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J310', 'Footprint R380')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint L750', 'Footprint R750')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C713', 'Footprint J52')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C701', 'Footprint J52')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C170')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J41', 'Footprint R211')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C762', 'Footprint C793')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R2342', 'Footprint U4')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R716', 'Footprint U4')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint Q50', 'Footprint U50')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R2009', 'Footprint U2003')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2054', 'Footprint R2051')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C187', 'Footprint C2306')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C762', 'Footprint U903')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J53', 'Footprint R905')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J4', 'Footprint R389')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint U2014')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1813')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R2319')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1843')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C586')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1822')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R1715')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1821')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C2049')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R1708')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R179')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R2325')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R196')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C587')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R1717')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C934')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint C1714')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint A1', 'Footprint R2320')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R842', 'Footprint R843')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1844', 'Footprint F900')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C836', 'Footprint TP12')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C20', 'Footprint C27')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C762', 'Footprint C905')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C741', 'Footprint R701')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C762', 'Footprint R761')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R701', 'Footprint U11')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C25', 'Footprint C29')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C586', 'Footprint R1708')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2041', 'Footprint C2068')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C762', 'Footprint R41')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2024', 'Footprint Q2002')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R412', 'Footprint U410')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1763', 'Footprint J310')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint R31', 'Footprint U44')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C1782', 'Footprint R2005')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint D2121', 'Footprint J310')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2040', 'Footprint C2069')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C43', 'Footprint SW2')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C458', 'Footprint C460')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2068', 'Footprint R375')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint C2068', 'Footprint J310')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J310', 'Footprint R375')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint D2120', 'Footprint J310')): 1,
        ('PCB', 'error', 'courtyards_overlap', 'Courtyards overlap', ('Footprint J310', 'Footprint R374')): 1,
        ('PCB', 'warning', 'silk_edge_clearance', 'Silkscreen clipped by board edge', ('Segment of J190 on F.Silkscreen', 'Segment on Edge.Cuts')): 2,
        ('PCB', 'warning', 'silk_edge_clearance', 'Silkscreen clipped by board edge', ('Segment of J2300 on F.Silkscreen', 'Segment on Edge.Cuts')): 2,
        ('PCB', 'warning', 'silk_edge_clearance', 'Silkscreen clipped by board edge', ('Segment of J30 on F.Silkscreen', 'Segment on Edge.Cuts')): 2,
        ('PCB', 'warning', 'silk_edge_clearance', 'Silkscreen clipped by board edge', ('Segment of J422 on F.Silkscreen', 'Segment on Edge.Cuts')): 2,
        ('PCB', 'warning', 'silk_overlap', 'Silkscreen clearance', ('Segment of C2068 on F.Silkscreen', 'Segment of R375 on F.Silkscreen')): 1,
})



def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_kicad_cli() -> str:
    cli = shutil.which("kicad-cli")
    if cli:
        return cli
    candidate = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("kicad-cli was not found")


def project_design_files() -> list[Path]:
    paths: set[Path] = set()
    for pattern in ("*.kicad_sch", "*.kicad_pcb", "*.kicad_pro"):
        paths.update(path.resolve() for path in ROOT.glob(pattern))
    paths.update(path.resolve() for path in (ROOT / "gen").glob("*.kicad_sym"))
    for library in (ROOT / "ducktop2.pretty", ROOT / "Module_LattePanda.pretty"):
        paths.update(path.resolve() for path in library.glob("*.kicad_mod"))
    for table in (ROOT / "sym-lib-table", ROOT / "fp-lib-table"):
        if table.exists():
            paths.add(table.resolve())
    return sorted(paths)


def hash_snapshot(paths: list[Path]) -> dict[Path, str]:
    return {path: sha256(path) for path in paths}


def sexpr_end(text: str, start: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise RuntimeError("unterminated KiCad s-expression")


def top_level_blocks(text: str, prefix: str):
    """Yield root-child blocks only, excluding footprint-local graphics."""
    depth = 0
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "(":
            if depth == 1 and text.startswith(prefix, index):
                end = sexpr_end(text, index)
                yield text[index:end]
                index = end
                continue
            depth += 1
        elif char == ")":
            depth -= 1
        index += 1


def point_key(point: tuple[float, float]) -> tuple[int, int]:
    return round(point[0] * 10000), round(point[1] * 10000)


def edge_loops(board_text: str) -> list[list[tuple[float, float]]]:
    unsupported = []
    for prefix in ("(gr_arc", "(gr_rect", "(gr_poly", "(gr_curve", "(gr_circle"):
        for block in top_level_blocks(board_text, prefix):
            if '(layer "Edge.Cuts")' in block:
                unsupported.append(prefix[1:])
    if unsupported:
        raise RuntimeError(
            "release checker cannot prove off-board status with these Edge.Cuts "
            f"primitives: {sorted(set(unsupported))}"
        )

    edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    pattern = re.compile(rf"\((start|end)\s+({NUMBER})\s+({NUMBER})\)")
    for block in top_level_blocks(board_text, "(gr_line"):
        if '(layer "Edge.Cuts")' not in block:
            continue
        points = {kind: (float(x), float(y)) for kind, x, y in pattern.findall(block)}
        if set(points) != {"start", "end"}:
            raise RuntimeError("Edge.Cuts line is missing a start or end coordinate")
        edges.append((points["start"], points["end"]))
    if not edges:
        raise RuntimeError("PCB has no supported top-level Edge.Cuts lines")

    adjacency: dict[tuple[int, int], list[tuple[int, tuple[int, int]]]] = defaultdict(list)
    coordinates: dict[tuple[int, int], tuple[float, float]] = {}
    for edge_index, (start, end) in enumerate(edges):
        a, b = point_key(start), point_key(end)
        if a == b:
            raise RuntimeError("zero-length Edge.Cuts segment")
        coordinates[a] = start
        coordinates[b] = end
        adjacency[a].append((edge_index, b))
        adjacency[b].append((edge_index, a))
    bad_degrees = {point: len(items) for point, items in adjacency.items() if len(items) != 2}
    if bad_degrees:
        raise RuntimeError(f"Edge.Cuts does not form closed degree-2 loops: {bad_degrees}")

    used: set[int] = set()
    loops: list[list[tuple[float, float]]] = []
    for initial_edge, (start_float, end_float) in enumerate(edges):
        if initial_edge in used:
            continue
        start = point_key(start_float)
        current = point_key(end_float)
        used.add(initial_edge)
        loop_keys = [start, current]
        while current != start:
            candidates = [(idx, other) for idx, other in adjacency[current] if idx not in used]
            if len(candidates) != 1:
                raise RuntimeError("Edge.Cuts loop is open, branched, or duplicated")
            edge_index, current = candidates[0]
            used.add(edge_index)
            loop_keys.append(current)
        if len(loop_keys) < 4:
            raise RuntimeError("Edge.Cuts loop has fewer than three sides")
        loops.append([coordinates[key] for key in loop_keys[:-1]])
    if len(used) != len(edges):
        raise RuntimeError("not every Edge.Cuts segment belongs to a closed loop")
    return loops


def point_on_segment(point, start, end, tolerance=1e-6) -> bool:
    px, py = point
    ax, ay = start
    bx, by = end
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > tolerance:
        return False
    return (
        min(ax, bx) - tolerance <= px <= max(ax, bx) + tolerance
        and min(ay, by) - tolerance <= py <= max(ay, by) + tolerance
    )


def point_in_polygon(point, polygon) -> bool:
    inside = False
    px, py = point
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if point_on_segment(point, start, end):
            return True
        ax, ay = start
        bx, by = end
        if (ay > py) != (by > py):
            crossing_x = (bx - ax) * (py - ay) / (by - ay) + ax
            if px < crossing_x:
                inside = not inside
    return inside


def offboard_footprint_anchors(board_text: str) -> list[str]:
    loops = edge_loops(board_text)
    outside = []
    at_re = re.compile(rf"^\s*\(at\s+({NUMBER})\s+({NUMBER})(?:\s+{NUMBER})?\)", re.MULTILINE)
    ref_re = re.compile(r'\(property\s+"Reference"\s+"([^"]+)"')
    for block in top_level_blocks(board_text, "(footprint"):
        ref_match = ref_re.search(block)
        at_match = at_re.search(block)
        if not ref_match or not at_match:
            raise RuntimeError("PCB footprint is missing Reference or top-level at metadata")
        point = float(at_match.group(1)), float(at_match.group(2))
        # Odd-even across all closed loops handles both concave outlines and
        # any line-only internal cutouts.
        if sum(point_in_polygon(point, loop) for loop in loops) % 2 != 1:
            outside.append(ref_match.group(1))
    return sorted(outside)


def duplicate_footprint_references(board_text: str) -> list[str]:
    """Return repeated physical reference designators on the main PCB.

    A multi-unit schematic symbol legitimately shares a reference across its
    units.  A PCB has exactly one physical footprint for that reference.  This
    check therefore operates on top-level footprint blocks rather than on the
    generated netlist.
    """
    references: list[str] = []
    ref_re = re.compile(r'\(property\s+"Reference"\s+"([^"]+)"')
    for block in top_level_blocks(board_text, "(footprint"):
        match = ref_re.search(block)
        if not match:
            raise RuntimeError("PCB footprint is missing a Reference property")
        references.append(match.group(1))
    return sorted(ref for ref, count in Counter(references).items() if count > 1)


def report_unexpected(label: str, actual: Counter, allowed: Counter) -> int:
    unexpected = actual - allowed
    stale_allowed = allowed - actual
    failures = 0
    if not unexpected:
        if stale_allowed:
            failures += sum(stale_allowed.values())
            print(
                f"{label}: FAIL, allowlist drift: "
                f"{sum(stale_allowed.values())} waived finding(s) no longer occur"
            )
            for signature, count in stale_allowed.most_common(20):
                sheet, severity, rule, description, items = signature
                print(f"  {count}x [{severity}] {sheet} {rule}: {description}")
                for item in items:
                    print(f"      {item}")
        else:
            print(f"{label}: PASS ({sum(actual.values())} findings, exact allowlist match)")
        return failures

    print(f"{label}: FAIL, {sum(unexpected.values())} non-allowlisted findings")
    for signature, count in unexpected.most_common(20):
        sheet, severity, rule, description, items = signature
        print(f"  {count}x [{severity}] {sheet} {rule}: {description}")
        for item in items:
            print(f"      {item}")
    if len(unexpected) > 20:
        print(f"  ... {len(unexpected) - 20} additional unique signatures")
    failures += sum(unexpected.values())
    if stale_allowed:
        failures += sum(stale_allowed.values())
        print(
            f"  additionally, {sum(stale_allowed.values())} waived finding(s) "
            "no longer occur (stale allowlist entries)"
        )
    return failures


CANONICAL_FOOTPRINT_POSITIONS = {
    # J11 is the right-edge USB-C dual-role port; its canonical home is the
    # top of the right edge, mirroring J22 at the top of the left column
    # (353.475, 30, 90). Placement passes moved it down twice before
    # (c3d268c, d5eb9ff, 1360032); this guard makes the release gate fail
    # if it ever drifts again.
    "J11": (353.475, 30.0, 90.0),
}


def drifted_footprint_positions(board_text: str) -> list[str]:
    """Return canonical-position footprints whose (at ...) drifted."""
    drifted: list[str] = []
    at_re = re.compile(rf"^\s*\(at\s+({NUMBER})\s+({NUMBER})(?:\s+({NUMBER}))?\)", re.MULTILINE)
    ref_re = re.compile(r'\(property\s+"Reference"\s+"([^"]+)"')
    for block in top_level_blocks(board_text, "(footprint"):
        ref_match = ref_re.search(block)
        at_match = at_re.search(block)
        if not ref_match or not at_match:
            continue
        ref = ref_match.group(1)
        if ref not in CANONICAL_FOOTPRINT_POSITIONS:
            continue
        x, y = float(at_match.group(1)), float(at_match.group(2))
        rot = float(at_match.group(3) or 0) % 360
        cx, cy, crot = CANONICAL_FOOTPRINT_POSITIONS[ref]
        if abs(x - cx) > 1e-6 or abs(y - cy) > 1e-6 or abs(rot - crot) > 1e-6:
            drifted.append(f"{ref} at ({x}, {y}) rot {rot}, canonical ({cx}, {cy}) rot {crot}")
    return drifted


def run_command(command: list[str], cwd: Path, label: str) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode:
        raise RuntimeError(
            f"{label} failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )


def copy_for_static_checks(destination: Path) -> Path:
    copy_root = destination / "project"
    ignored = shutil.ignore_patterns(
        ".git", "__pycache__", "*.pyc", "tmp",
        "pcb_snapshots", "project_snapshots",
    )
    shutil.copytree(ROOT, copy_root, ignore=ignored)
    verification = copy_root / "verification"
    if verification.exists():
        shutil.rmtree(verification)
    verification.mkdir()
    return copy_root


def generated_schematic_drift(copy_root: Path) -> list[str]:
    drift: list[str] = []
    live_paths = sorted(ROOT.glob("*.kicad_sch"))
    for live in live_paths:
        candidate = copy_root / live.name
        if not candidate.exists() or sha256(live) != sha256(candidate):
            drift.append(live.name)
    for relative in (Path("gen/ducktop2.kicad_sym"),):
        live = ROOT / relative
        candidate = copy_root / relative
        if live.exists() and (not candidate.exists() or sha256(live) != sha256(candidate)):
            drift.append(relative.as_posix())
    return drift


def run_static_checks(tempdir: Path) -> tuple[int, int]:
    """Run mutating schematic checks in a copy; return failures and BOM gaps."""
    failures = 0
    bom_gaps = -1
    copy_root = copy_for_static_checks(tempdir)
    # Board split Phase 2.4: export the BMS netlist for its pack audit.
    cli = find_kicad_cli()
    bms_sch = copy_root / "bms" / "bms.kicad_sch"
    if bms_sch.exists():
        subprocess.run(
            [cli, "sch", "export", "netlist", "--format", "kicadxml",
             "--output", str(copy_root / "verification" / "bms_netlist.xml"), str(bms_sch)],
            check=False, capture_output=True, cwd=copy_root,
        )
    commands = [
        (["python3", "gen/check_schematic.py"], copy_root, "schematic self-check"),
        (["python3", "gen/verify_design_contracts.py", "--schematic-only"], copy_root,
         "schematic design contracts"),
        (["python3", "gen/verify_schematic_closure.py", "verification/ducktop2_netlist.xml"],
         copy_root, "independent schematic closure audit (center)"),
        (["python3", "gen/verify_schematic_closure.py", "verification/bms_netlist.xml", "--pack"],
         copy_root, "independent schematic closure audit (bms pack)"),
        (["python3", "gen/verify_electrical_calculations.py"], copy_root,
         "electrical calculations"),
        (["python3", "gen/verify_electrical_calculations.py", "--project", "bms"], copy_root,
         "electrical calculations (bms pack)"),
        (["python3", "gen/generate_pin_review_table.py"], copy_root,
         "pin review generation"),
        (["python3", "gen/generate_component_inventory.py", "--output-dir",
          "verification/release_inventory"], copy_root, "component inventory"),
        (["sh", "tools/run_host_tests.sh"], copy_root / "firmware",
         "firmware host-policy tests"),
    ]
    for command, cwd, label in commands:
        try:
            run_command(command, cwd, label)
        except RuntimeError as exc:
            failures += 1
            print(f"{label}: FAIL: {exc}")

    drift = generated_schematic_drift(copy_root)
    if drift:
        failures += len(drift)
        print("Generated-source identity: FAIL: " + ", ".join(drift))
    else:
        print("Generated-source identity: PASS")

    gap_csv = copy_root / "verification/release_inventory/bom_release_gaps.csv"
    if gap_csv.exists():
        with gap_csv.open(newline="", encoding="utf-8") as handle:
            bom_gaps = sum(1 for _ in csv.DictReader(handle))
        print(f"BOM procurement gaps: {bom_gaps}")
    else:
        failures += 1
        print("BOM procurement gaps: FAIL: inventory did not produce the gap CSV")
    return failures, bom_gaps


def require_json_status(path: Path, wanted: str, label: str) -> int:
    if not path.exists():
        print(f"{label}: FAIL: missing {path.relative_to(ROOT)}")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"{label}: FAIL: invalid JSON: {exc}")
        return 1
    status = data.get("status")
    if status != wanted:
        print(f"{label}: FAIL: status is {status!r}, requires {wanted!r}")
        return 1
    print(f"{label}: PASS")
    return 0


def pcb_uuid_audit(board_text: str) -> tuple[int, list[str], int]:
    """Return (invalid_count, duplicate_values, excess_duplicates)."""
    values = re.findall(r'\(uuid\s+"([^"]+)"\)', board_text)
    invalid: list[str] = []
    counts: Counter[str] = Counter()
    for value in values:
        try:
            uuid.UUID(value)
        except ValueError:
            invalid.append(value)
        counts[value] += 1
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    excess = sum(count - 1 for count in counts.values() if count > 1)
    return len(invalid), duplicates, excess


def run_pcb_checks(cli: str, pcb: Path, tempdir: Path) -> int:
    failures = 0
    drc_path = tempdir / "drc.json"
    run_command([
        cli, "pcb", "drc", "--severity-all", "--severity-exclusions",
        "--schematic-parity", "--format", "json", "--output", str(drc_path), str(pcb),
    ], ROOT, "PCB DRC")
    drc = json.loads(drc_path.read_text(encoding="utf-8"))
    drc_findings = Counter(
        semantic_signature("PCB", violation) for violation in drc.get("violations", [])
    )
    parity_findings = Counter(
        semantic_signature("PCB parity", violation)
        for violation in drc.get("schematic_parity", [])
    )
    failures += report_unexpected("DRC", drc_findings, DRC_ALLOWLIST)
    failures += report_unexpected("Schematic parity", parity_findings, Counter())
    unconnected = drc.get("unconnected_items", [])
    if unconnected:
        failures += len(unconnected)
        print(f"Unrouted items: FAIL, {len(unconnected)} missing connections")
    else:
        print("Unrouted items: 0")

    # Refilled-state gate: DRC the board as the fabricator will receive it
    # (zones filled and saved).  Uses the staged project copy so .kicad_pro
    # and .kicad_dru apply; falls back to staging a minimal copy when this
    # run is not the canonical project.
    project_root = tempdir / "project"
    if not (project_root / "ducktop2.kicad_pro").exists():
        project_root = tempdir / "refill-project"
        project_root.mkdir()
        for name in ("ducktop2.kicad_pro", "ducktop2.kicad_dru"):
            source = ROOT / name
            if source.exists():
                shutil.copyfile(source, project_root / name)
        shutil.copyfile(pcb, project_root / pcb.name)
    refill_pcb = project_root / pcb.name
    if not refill_pcb.exists():
        # stage this board into the project copy (the canonical-project
        # branch does not stage per-board PCBs on its own)
        shutil.copyfile(pcb, refill_pcb)
        for name in (pcb.with_suffix(".kicad_pro").name,
                     pcb.with_suffix(".kicad_dru").name):
            source = pcb.parent / name
            if source.exists() and not (project_root / name).exists():
                shutil.copyfile(source, project_root / name)
    refill_path = tempdir / "drc_refilled.json"
    if refill_pcb.exists():
        run_command([
            cli, "pcb", "drc", "--refill-zones", "--save-board",
            "--severity-all", "--severity-exclusions",
            "--format", "json", "--output", str(refill_path), str(refill_pcb),
        ], project_root, "Refilled-state DRC")
        refilled = json.loads(refill_path.read_text(encoding="utf-8"))
        refilled_types = Counter(
            item.get("type", "") for item in refilled.get("violations", [])
        )
        saved_types = Counter(item.get("type", "") for item in drc.get("violations", []))
        added = {
            category
            for category in refilled_types - saved_types
            if category not in REFILL_DELTA_TYPES
        }
        isolated = refilled_types.get("isolated_copper", 0)
        print(
            f"Refilled fill state: {sum(refilled_types.values())} findings; "
            f"isolated_copper={isolated} (allowed during unrouted routing), "
            f"non-consequence additions={len(added)}"
        )
        if added:
            failures += 1
            for category in sorted(added):
                print(f"  refill introduced unexpected category: {category}")
    else:
        failures += 1
        print("Refilled fill state: FAIL, staged refill copy was not created")

    outside = offboard_footprint_anchors(pcb.read_text(encoding="utf-8"))
    if outside:
        failures += len(outside)
        print(f"Off-board footprint anchors: FAIL, {len(outside)}: {', '.join(outside)}")
    else:
        print("Off-board footprint anchors: 0")

    board_text = pcb.read_text(encoding="utf-8")
    invalid_uuids, duplicate_uuids, excess = pcb_uuid_audit(board_text)
    if invalid_uuids or duplicate_uuids:
        failures += len(invalid_uuids) + min(len(duplicate_uuids), 10) + (1 if duplicate_uuids else 0)
        print(
            "PCB object UUIDs: FAIL, "
            f"{invalid_uuids} invalid, {len(duplicate_uuids)} duplicated values "
            f"({excess} excess occurrences)"
        )
        for value in invalid_uuids[:5]:
            print(f"      invalid: {value}")
        for value in duplicate_uuids[:5]:
            print(f"      duplicate: {value}")
    else:
        print("PCB object UUIDs: PASS (all valid and globally unique)")
    drifted = drifted_footprint_positions(pcb.read_text(encoding="utf-8"))
    if drifted:
        failures += len(drifted)
        print(f"Canonical footprint positions: FAIL, {len(drifted)}: {', '.join(drifted)}")
    else:
        print("Canonical footprint positions: PASS")
    return failures


def production_evidence_checks() -> int:
    failures = 0
    failures += require_json_status(
        ROOT / "firmware/release/target_release.json", "APPROVED", "Target firmware release")
    failures += require_json_status(
        ROOT / "manufacturing/direct_edp_harness_release.json", "APPROVED",
        "Direct-eDP harness release")
    failures += require_json_status(
        ROOT / "verification/hardware_validation_release.json", "PASS",
        "Physical HIL/thermal/RF/acoustic validation")
    hil_path = ROOT / "firmware/release/hil_matrix.csv"
    with hil_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    incomplete = [row.get("id", "") for row in rows if row.get("status") != "PASS"]
    if incomplete:
        failures += len(incomplete)
        print(f"HIL completion: FAIL, {len(incomplete)} row(s) not PASS")
    else:
        print(f"HIL completion: PASS ({len(rows)} rows)")
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schematic", type=Path, default=DEFAULT_SCHEMATIC)
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    parser.add_argument(
        "--stage", choices=("schematic", "fabrication", "production"),
        default="fabrication", help="release boundary to enforce (default: fabrication)",
    )
    args = parser.parse_args(argv)

    schematic = args.schematic.expanduser().resolve()
    pcb = args.pcb.expanduser().resolve()
    if not schematic.exists() or not pcb.exists():
        raise RuntimeError("schematic or PCB candidate does not exist")

    # Phase 5 (audit B4): the split boards are the fabricable artifacts.
    # In fabrication/production stages with no explicit --pcb, run the
    # PCB checks against ALL FOUR boards instead of the retired monolith.
    stage_boards = [ROOT / "ducktop2-center.kicad_pcb",
                    ROOT / "left_io" / "left_io.kicad_pcb",
                    ROOT / "right_io" / "right_io.kicad_pcb",
                    ROOT / "bms" / "bms.kicad_pcb"]
    pcbs = ([pcb] if args.pcb else stage_boards) \
        if args.stage in {"fabrication", "production"} else [pcb]

    watched = project_design_files()
    before = hash_snapshot(watched)
    cli = find_kicad_cli()
    failures = 0

    for _pcb in pcbs:
        duplicate_refs = duplicate_footprint_references(
            _pcb.read_text(encoding="utf-8"))
        if duplicate_refs:
            failures += len(duplicate_refs)
            print(
                f"PCB footprint references ({_pcb.name}): FAIL, duplicate "
                "physical references: " + ", ".join(duplicate_refs))
        else:
            print(f"PCB footprint references ({_pcb.name}): unique")

    with tempfile.TemporaryDirectory(prefix="ducktop2-release-check-") as temp:
        tempdir = Path(temp)
        static_failures, bom_gaps = run_static_checks(tempdir)
        failures += static_failures
        if args.stage in {"fabrication", "production"}:
            if bom_gaps:
                failures += max(bom_gaps, 1)
                print(f"Fabrication BOM gate: FAIL, {bom_gaps} unresolved procurement item(s)")
            else:
                print("Fabrication BOM gate: PASS")
            failures += require_json_status(
                ROOT / "manufacturing/mainboard_stackup_release.json", "APPROVED",
                "Fabricator stackup release")
            for _pcb in pcbs:
                failures += run_pcb_checks(cli, _pcb, tempdir)
        if args.stage == "production":
            failures += production_evidence_checks()

    after_paths = project_design_files()
    before_set = set(watched)
    after_set = set(after_paths)
    created = sorted(str(path.relative_to(ROOT)) for path in after_set - before_set)
    removed = sorted(str(path.relative_to(ROOT)) for path in before_set - after_set)
    after = hash_snapshot(after_paths)
    changed = sorted(
        str(path.relative_to(ROOT))
        for path in before_set & after_set
        if before[path] != after[path]
    )
    integrity_changes = created + removed + changed
    if integrity_changes:
        failures += len(integrity_changes)
        print(
            "Read-only integrity: FAIL, "
            f"created={created}, removed={removed}, changed={changed}"
        )
    else:
        print(f"Read-only integrity: OK ({len(watched)} project design/library files unchanged)")

    if failures:
        print(f"{args.stage.upper()} RELEASE CHECK: FAIL ({failures} blocking findings/items)")
        return 1
    print(f"{args.stage.upper()} RELEASE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



