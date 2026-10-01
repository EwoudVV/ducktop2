#!/usr/bin/env python3
"""Export the power parts for the case model.

Run with KiCad's Python from the project root:
    python3 gen/export_power_placement.py --study-top-z 8
    python3 gen/export_power_placement.py --study-top-z 8 --check

Add --all-components for the full main-board component-placement export.

Omit --study-top-z to leave case Z undefined. The optional value is a packaging
study datum, not a fixed enclosure dimension. Positions and courtyards come
from the saved boards. Heights come only from the manufacturer table below.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "mechanical/board-placement.json"
CSV_PATH = ROOT / "mechanical/power-placement.csv"
JSON_PATH = ROOT / "mechanical/power-placement.json"

# Keep this list explicit. It covers the revised charger, standby, Mu supply,
# source control and the two PD sink paths. New parts need a scope review.
REVIEWED_GROUPS = {
    "center": {
        "charger": """
            C10 C11 C2260 C2600 C2601 C2602 C2603 C2604 C2605 C2606 C2607
            C2608 C2609 C7 C701 C702 C703 C704 C705 C706 C707 C708 C709 C710
            C711 C712 C713 C714 C8 C9 D2600 D2601 L1 LED1 Q25 Q2600 Q2601
            Q2602 Q2603 Q2604 Q2605 Q700 Q702 R12 R13 R14 R16 R18 R2260
            R2261 R2262 R2263 R2600 R2601 R2602 R2603 R2604 R2605 R2606
            R2607 R2608 R2609 R2610 R2611 R2612 R704 R706 R719 RS2600
            RS2601 U2 U2210
        """.split(),
        "standby": """
            C2620 C2621 C2622 C2650 C2651 C2660 C2661 C2662 C795 C796 C797
            C798 C799 D2620 D711 Q2620 Q2621 Q2622 Q2623 Q2650 Q2660 R2620
            R2661 R2662 R2663 R2664 R781 R795 R796 R797 R798 R799 RS2620
            RS2660 TP2660 TP2661 U2620 U2621 U2650 U2660 U718
        """.split(),
        "source_control": """
            C2641 C2642 C2643 D2640 Q2644 R2640 R2641 R2642 R2643 R2644
            R2645 R2646 R2647 U2634 U2635 U2644
        """.split(),
        "mu_supply": """
            C2610 C2670 C750 C751 C752 C753 C754 C755 C756 C757 C758 C759
            C760 C761 C762 C763 C764 C765 C766 C767 C768 C769 C770 C771 C772
            C773 C774 C775 L750 Q2610 Q2611 Q750 Q751 R2613 R2614 R750
            R751 R752 R753 R754 R755 R756 R757 R758 R759 R760 R761 R762
            R763 R764 R765 R766 RS2670 RS750 U750
        """.split(),
        "ec_soft_start": ["C2640"],
    },
    "left": {
        "pd1_input": """
            U720 C2080 C2081 C2082 R2083 R2082 R2084 R2086 R2085
            U2630 C2630 Q2630 R2081 R2080
        """.split(),
    },
    "right": {
        "pd2_input": """
            U721 C2090 C2091 C2092 R2093 R2092 R2094 R2095 R2096
            U2631 C2631 Q2631 R2091 R2090
        """.split(),
    },
}
EXPECTED_COUNTS = {"center": 185, "left": 14, "right": 14}


def height(value: float, kind: str, url: str, note: str) -> dict:
    return {"value_mm": value, "kind": kind, "source_url": url, "basis": note}


# Nominal dimensions are not promoted to maxima. No height is inferred from a
# package name, a footprint, a STEP bounding box or an unreviewed substitute.
MANUFACTURER_HEIGHTS = {
    'GRM1885C1H180JA01': height(0.9, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM1885C1H180JA01-01A.pdf',
        'Murata exact-part sheet: 0.80 +/-0.10 mm body thickness.'),
    'GRM155R71H102KA01': height(0.55, "maximum",
        'https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-s-mlcc-2506.ashx?cvid=20250805040438000000&la=ko-kr',
        'Murata exact-part table and drawing: 0.50 +/-0.05 mm body thickness.'),
    'GRM1555C1H150JA01': height(0.55, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM1555C1H150JA01-01A.pdf',
        'Murata exact-part drawing: 0.50 +/-0.05 mm body thickness.'),
    '1812L150/16DR': height(1.25, "maximum",
        'https://www.littelfuse.com/~/media/electronics/datasheets/resettable_ptcs/littelfuse_ptc_1812l_datasheet.pdf.pdf',
        'Littelfuse 1812L150/16 dimension C is 0.75 to 1.25 mm. DR is the listed ordering suffix.'),
    'MPZ1608S221A': height(0.95, "maximum",
        'https://product.tdk.com/en/system/files/dam/doc/product/emc/emc/beads/catalog/beads_commercial_power_mpz1608_en.pdf',
        'TDK MPZ1608S221A body thickness is 0.80 +/-0.15 mm; packaging is specified separately.'),
    'PCM2900CDBR': height(2.0, "maximum",
        'https://www.ti.com/lit/ds/symlink/pcm2900c.pdf',
        'TI DB0028A outline: 2.0 mm maximum seated height for the DB SSOP-28 package.'),
    'TPA2012D2RTJR': height(0.8, "maximum",
        'https://www.ti.com/lit/ds/symlink/tpa2012d2.pdf',
        'TI RTJ0020D outline: 0.8 mm maximum height for the RTJ WQFN-20 package.'),
    'ABM8G-106-12.000MHZ-T': height(1.0, "maximum",
        'https://abracon.com/datasheets/ABM8G-106-12.000MHz-T.pdf',
        'Abracon exact-part outline, page 2: 1.0 mm maximum body height.'),
    'ABM8-272-T3': height(0.8, "maximum",
        'https://abracon.com/datasheets/ABM8-272-T3.pdf',
        'The exact-part drawing uses the ABM8 outline; Abracon Table 2 specifies 0.80 mm maximum height.'),
    'GRM155R71A224KE01D': height(0.55, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM155R71A224KE01-01.pdf',
        'ExactMurata reference sheet page1 section3: T=0.50+/-0.05mm; D packaging explicitly listed.'),
    'GRM155R71H104ME14D': height(0.55, "maximum",
        'https://datasheet.octopart.com/GRM155R71H104ME14D-Murata-datasheet-138740983.pdf',
        'ExactMurata product sheet2020-01-25 page1: T=0.50+/-0.05mm; D/J/W packaging explicitly listed.'),
    'GRM1885C1H103JA01D': height(0.9, "maximum",
        'https://www.farnell.com/datasheets/2048016.pdf',
        'ExactMurata product sheet2015-12-04 page1: T=0.80+/-0.10mm; D/J packaging explicitly listed.'),
    'GRM1555C1H101JA01D': height(0.55, "maximum",
        'https://datasheet.ciiva.com/18184/getdatasheetpartid-199957-18184175.pdf',
        'ExactMurata product sheet2014-09-18 page1: T=0.50+/-0.05mm; D/W/J packaging explicitly listed.'),
    'C0805C223J5GACTU': height(1.2, "maximum",
        'https://docs.rs-online.com/6448/0900766b817074ee.pdf',
        'ExactKEMET part sheet2019-06-27, Dimensions T=1.10+/-0.10mm.'),
    'GRM1555C1H102JA01D': height(0.55, "maximum",
        'https://datasheet.octopart.com/GRM1555C1H102JA01D-Murata-datasheet-7625556.pdf',
        'ExactMurata part sheet: thickness T=0.50+/-0.05mm; D packaging listed.'),
    'GRM188R71H473KA61D': height(0.9, "maximum",
        'https://www.mouser.com/datasheet/2/281/murata_mured00583-1-1740351.pdf',
        'Murata catalogC02E-16, exactMPN listed on printedp38/PDFpage40; GRM188 dimensional row on printedp8/PDFpage10 specifiesT=0.80+/-0.10mm for taped parts. Bulk-case0.07mm tolerance footnote is not used forDsuffix. Manufacturer family drawing explicitly linked to exactpart listing, not a generic0603model.'),
    'GRM188R71H224KAC4D': height(0.9, "maximum",
        'https://www.farnell.com/datasheets/2189130.pdf',
        'ExactMurata product sheet: T=0.80+/-0.10mm; D/J packaging explicitly listed.'),
    'BAT54WS-7-F': height(1.1, "maximum",
        'https://datasheet.octopart.com/BAT54WS-7-F-Diodes-Inc.-datasheet-14053335.pdf',
        'DiodesIncorporated DS30098Rev11-2 page3 exactorder row andSOD323outline: K=1.0..1.1mm. Do notuseunrelatedHXYorMulticomp same-name parts.'),
    'BAT54S,215': height(1.1, "maximum",
        'https://assets.nexperia.com/documents/outline-drawing/SOT23.pdf',
        'Nexperia SOT23 packageinformation2022-10-12 Table1: seatedheightA max1.1mm. ExactBAT54S,215 manufacturer mapping identifiesSOT23(TO-236AB).'),
    'BSS138LT1G': height(1.12, "maximum",
        'https://www.alldatasheet.com/html-pdf/115982/ONSEMI/BSS138LT1G/1119/5/BSS138LT1G.html',
        'ONSemiconductor exactBSS138LT1G drawing page5, case318-08issueAH: heightC max0.044in, printed1.11mm. Drawing statesinchcontrols;0.044x25.4=1.1176mm, conservativelyroundedup to1.12mm. NotinferredfromcachedBSS138nonLsheet.'),
    'TNPW04022K21BEED': height(0.4, "maximum",
        'https://www.vishay.com/doc?28758',
        'VishayTNPWe3 revision2026-04-10 page15, TNPW0402e3 rowH=0.35+/-0.05mm; resistance/tolerance/packaging options share mechanicalsize.'),
    'TNPW0603102KBYEA': height(0.55, "maximum",
        'https://www.vishay.com/doc?28758',
        'VishayTNPWe3 revision2026-04-10 page15, TNPW0603e3 rowH=0.45+/-0.10mm; resistance/tolerance/packaging options share mechanicalsize.'),
    'TNPW0603150KBYEA': height(0.55, "maximum",
        'https://www.vishay.com/doc?28758',
        'VishayTNPWe3 revision2026-04-10 page15, TNPW0603e3 rowH=0.45+/-0.10mm; resistance/tolerance/packaging options share mechanicalsize.'),
    'LTC4368IMS-2#PBF': height(1.1, "maximum",
        'https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4368.pdf',
        'ADIRevC page2 exactordering row mapsIMS-2#PBF to10leadMSOP. Page19 MSpackage drawing05-08-1661RevF specifies1.10mmmaximum;0.86mm isreferenceonly.'),
    'RC2512FR-071KL': height(0.65, "maximum",
        'https://yageogroup.com/content/datasheet/asset/file/PYU-RC_51_ROHS_P',
        'YageoRCL product specification dimensionTable1 page4, RC2512H=0.55+/-0.10mm. FR-07resistance/packaging options do not changeRC2512mechanicaldimensions.'),
    'TPS259827ONRGER': height(1.0, "maximum",
        'https://www.ti.com/lit/ds/symlink/tps25982.pdf',
        'TI exactordering rowTPS259827ONRGER mapsRGE24pins; RGE0024M packageoutline specifies1mmmaximum. Do notconfuse1.1mm tape-pocketK0 or35mmboxheight withpartheight.'),
    'GRM155R71H472KA01': height(0.55, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM155R71H472KA01-01A.pdf',
        'Exact2024Murata reference sheet page2: T=0.50+/-0.05mm; base part and packaging suffix separated.'),
    'TLV803EA43RDBZR': height(1.12, "maximum",
        'https://www.ti.com/lit/ds/symlink/tlv803e.pdf',
        'TIRevJ exact orderrow mapsTLV803EA43RDBZR toDBZ; page39 DBZ0003A outline maximum1.12mm.'),
    'SN74LVC1G17DBVR': height(1.45, "maximum",
        'https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf',
        'TIRevY page23 DBV0005A outline maximum1.45mm; exactDBVR ordering suffix.'),
    'TCA9537DGSR': height(1.1, "maximum",
        'https://www.ti.com/lit/ds/symlink/tca9537.pdf',
        'TI exact orderrow mapsTCA9537DGSR toDGS; page33 DGS0010A outline maximum1.1mm.'),
    'TPS3700DDCR': height(1.1, "maximum",
        'https://www.ti.com/lit/ds/symlink/tps3700.pdf',
        'TPS3700 exact ordering table mapsDDCR toDDC6-pin. TI DDC0006A SOT-23 package outline in TPS561201 datasheet specifies1.1mm maximum; same vendor package drawing, not nominal 3D model.'),
    'GRM32ER71E226KE15L': height(2.7, "maximum",
        'https://www.murata.com/en-global/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno=GRM32ER71E226KE15%23',
        'ExactMurata product sheet dated2025-07-30: T=2.5+/-0.2mm. Exceeds1.8mm provisional backsideallocation; C2303muststayF.'),
    "GRM21BR71C225KA12L": height(1.35, "maximum",
        "https://www.farnell.com/datasheets/4088041.pdf",
        "Murata product sheet, 20 December 2023, page 2: thickness 1.25+/-0.10mm; 2.2uF,16V,X7R,0805."),
    'GRM188R71H103KA01': height(0.9, "maximum",
        'https://www.farnell.com/datasheets/1747461.pdf',
        'Exact Murata base-part drawing page1: T=0.80+/-0.10mm; D/J packaging dimensions shared.'),
    'GRM155R71A104KA01D': height(0.55, "maximum",
        'https://www.farnell.com/datasheets/4087771.pdf',
        'Exact Murata product sheet dated2023-12-20, page2: T=0.50+/-0.05mm.'),
    'GRM155R60J475ME47D': height(0.6, "maximum",
        'https://media.distrelec.com/Web/Downloads/_t/ds/Murata_GRM155R60J475ME47_eng_tds.pdf',
        'Exact Murata product sheet dated2020-02-11, page1: T=0.50+/-0.10mm; D/J packaging explicitly listed.'),
    'USBLC6-2P6': height(0.62, "maximum",
        'https://www.st.com/resource/en/datasheet/usblc6-2.pdf',
        'ST DS4260Rev7, page14 Table4 SOT-666 A=0.62mm maximum; page18 maps exact USBLC6-2P6 to SOT-666.'),
    'GRM21BR71A105KA01L': height(1.35, "maximum",
        'https://www.mouser.com/catalog/specsheets/grm21br71a105ka01.pdf',
        'Exact Murata drawing, page1: T=1.25+/-0.10mm; L packaging explicitly listed.'),
    'GRM155R71H102KA01D': height(0.55, "maximum",
        'https://www.murata.com/en-sg/products/productdetail?partno=GRM155R71H102KA01D',
        'Exact manufacturer product specifications: T=0.50+/-0.05mm; D packaging explicitly listed.'),
    'GRM155R71H103KA88D': height(0.55, "maximum",
        'https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/dynamic-model/component-list-d-mlcc-2506.ashx?cvid=20250805040419000000&la=en-sg',
        'Exact manufacturer part-number table row GRM155R71H103KA88: T size maximum0.55mm. Packaging suffix does not change chip dimensions.'),
    'GRM188R71A105KA61D': height(0.9, "maximum",
        'https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-s-mlcc-2506.ashx?cvid=20250805040438000000&la=ko-kr',
        'Exact manufacturer part-number table row GRM188R71A105KA61: T size maximum0.90mm. Packaging suffix does not change chip dimensions.'),
    'GRM1555C1H121JA01D': height(0.55, "maximum",
        'https://datasheet.octopart.com/GRM1555C1H121JA01D-Murata-datasheet-14396354.pdf',
        'Exact Murata drawing, page1: T=0.50+/-0.05mm; D packaging explicitly listed.'),
    'C0603C222J5GACTU': height(0.87, "maximum",
        'https://static.chipdip.ru/lib/165/DOC028165738.pdf',
        'Exact KEMET generated part drawing, page1: T=0.80+/-0.07mm.'),
    'C0603C224K5RACTU': height(0.95, "maximum",
        'https://search.kemet.com/download/specsheet/C0603C224K5RACTU',
        'Exact KEMET generated part specification dated2026-02-04: T=0.80+/-0.15mm.'),
    'GRM155R71C104KA88D': height(0.55, "maximum",
        'https://www.murata.com/en-global/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno=GRM155R71C104KA88%23',
        'Exact manufacturer product sheet: T=0.50+/-0.05mm; packaging code is separate from chip dimensional control code.'),
    'GRM1555C1H120JA01': height(0.55, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM1555C1H120JA01-01.pdf',
        'Exact manufacturer reference sheet, page1 section3: T=0.50+/-0.05mm; base part used in CAD, D/W/J packaging listed separately.'),
    "W25Q32RVXHJQ": height(.4, "maximum",
        "https://www.marthel.pl/katalog/W25Q32RV%20RevC%2006062024%20Plus.pdf",
        "Winbond W25Q32RV Rev. C, 6 June 2024, pages 77/80: XH USON outline A=0.40mm maximum and XHJQ ordering code."),
    "GRM31CR61C475KA01": height(1.8, "maximum",
        "https://cms.nacsemi.com/content/AuthDatasheets/MURE-S-A0003031232-1.pdf",
        "Murata GRM31CR61C475KA01# drawing, mirrored by NAC: T=1.6+/-0.2mm for L/K packaging. CAD records the base part number."),
    'TPD4S201RUKR': height(0.8, "maximum",
        'https://www.ti.com/lit/ds/symlink/tpd4s201.pdf',
        'RUK0020B package outline, page 25: 0.8mm max'),
    'TS3USB30EDGSR': height(1.1, "maximum",
        'https://www.ti.com/lit/ds/symlink/ts3usb30e.pdf',
        'DGS0010A package outline, page 25: 1.1mm max'),
    'INA226AIDGSR': height(1.1, "maximum",
        'https://www.ti.com/lit/ds/symlink/ina226.pdf',
        'DGS0010A package outline, page 38: 1.1mm max'),
    'SN74LVC2G07DCKR': height(1.1, "maximum",
        'https://www.ti.com/lit/ds/symlink/sn74lvc2g07.pdf',
        'DCK0006A package outline, pages 18-19: 1.1mm max'),
    'TLV803EA29RDBZR': height(1.12, "maximum",
        'https://www.ti.com/lit/ds/symlink/tlv803e.pdf',
        'DBZ0003A package outline, page 39: 1.12mm max; rendered and visually checked'),
    '2N7002KT1G': height(1.11, "maximum",
        'https://www.onsemi.com/download/package-drawing/pdf/318-08.pdf',
        '2N7002K datasheet maps toCASE318 issueAU; mechanical drawing dimensionA0.89/1.00/1.11mm min/nom/max'),
    'ASDMB-25.000MHZ-LC-T': height(0.9, "maximum",
        'https://abracon.com/Oscillators/ASDMB.pdf',
        'RevisionI, page7 side view:0.85±0.05mm; rendered and visually checked'),
    'TPS2553DDBVR': height(1.45, "maximum",
        'https://www.ti.com/lit/ds/symlink/tps2553.pdf',
        'DBV0006A package outline, page 41: 1.45mm max'),
    'GRM188R71H104KA93D': height(0.9, "maximum",
        'https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/dynamic-model/component-list-d-mlcc-2506.ashx?cvid=20250805040419000000&la=ja-jp',
        'Exact GRM188R71H104KA93 manufacturer table row:T size max0.9mm; indexed primary content (direct download failed)'),
    'GRM31CR71A106KA01L': height(1.8, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM31CR71A106KA01-01.pdf',
        'Reference sheet section 3: T1.6±0.2mm'),
    'GRM31CR71E475KA88L': height(1.8, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM31CR71E475KA88-01.pdf',
        'Reference sheet section 3: T1.6±0.2mm'),
    'GRM21BR71A106KE51L': height(1.4, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BR71A106KE51-01.pdf',
        'Reference sheet section 3: T1.25±0.15mm; do not substitute1.35mm'),
    'GRM21BR71H105KA12L': height(1.35, "maximum",
        'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BR71H105KA12-01.pdf',
        'Reference sheet section 3: T1.25±0.1mm'),
    'TNPU060322K1HZEN00': height(0.55, "maximum",
        'https://www.vishay.com/docs/28779/tnpue3.pdf',
        'TNPU0603 e3 dimensions table, page 8: H0.45±0.10mm; family dimensions apply across resistance values'),
    'TNPU06032K49HZEN00': height(0.55, "maximum",
        'https://www.vishay.com/docs/28779/tnpue3.pdf',
        'TNPU0603 e3 dimensions table, page 8: H0.45±0.10mm; family dimensions apply across resistance values'),
    "CSD17575Q3": height(1.1, "maximum",
        "https://www.ti.com/lit/ds/symlink/csd17575q3.pdf",
        "SLPS489A, section 7.1 Q3 package dimensions: A=1.10mm maximum."),
    "CSD19537Q3": height(1.1, "maximum",
        "https://www.ti.com/lit/ds/symlink/csd19537q3.pdf",
        "SLPS549B, section 7.1 Q3 package dimensions: A=1.10mm maximum."),
    "CSD17577Q3A": height(.9, "maximum",
        "https://www.ti.com/lit/ds/symlink/csd17577q3a.pdf",
        "SLPS515A, DNH package outline: 0.9mm maximum."),
    "ISL9241IRTZ": height(.85, "maximum",
        "https://www.renesas.com/en/document/dst/isl9241-datasheet",
        "L32.4x4D outline: 0.75mm body height with +/-0.10mm tolerance."),
    "WSL1206R1800FEA": height(.889, "maximum",
        "https://www.vishay.com/docs/30100/wsl.pdf",
        "WSL1206 dimensions: H=0.635+/-0.254mm."),
    "WSL2512R0200FEA18": height(.889, "maximum",
        "https://www.vishay.com/doc?31057",
        "WSL2512...18 dimensions: H=0.635+/-0.254mm."),
    "WSL2512R0220FEA18": height(.889, "maximum",
        "https://www.vishay.com/doc?31057",
        "WSL2512...18 dimensions: H=0.635+/-0.254mm."),
    "WSLP2512R0100FEA": height(.889, "maximum",
        "https://www.vishay.com/docs/30122/wslp.pdf",
        "WSLP2512 dimensions: H=0.635+/-0.254mm."),
    "TNPU0603100KHZEN00": height(.55, "maximum",
        "https://www.vishay.com/docs/28779/tnpue3.pdf",
        "TNPU0603 e3 dimensions: H=0.45+/-0.10mm."),
    "RC0603FR-072R2L": height(.55, "maximum",
        "https://www.mouser.com/catalog/specsheets/RC0603.pdf",
        "Yageo RC0603 product specification, mirrored by Mouser: H=0.45+/-0.10mm."),
    "GRM31CR71H475KA12L": height(1.8, "maximum",
        "https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM31CR71H475KA12-01A.pdf",
        "Thickness 1.6+/-0.2mm."),
    "GRM31CR71E106KA12L": height(1.8, "maximum",
        "https://docs.rs-online.com/aab4/0900766b813d2ca8.pdf",
        "Murata GRM31CR71E106KA12# drawing, mirrored by RS: thickness 1.6+/-0.2mm; L packaging included."),
    "GRM21BR71A475KA73L": height(1.4, "maximum",
        "https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BR71A475KA73-01.pdf",
        "Thickness 1.25+/-0.15mm in the manufacturer's reference sheet."),
    "C1608X7R1E474K080AE": height(.95, "maximum",
        "https://product.tdk.com/system/files/dam/doc/product/capacitor/ceramic/mlcc/charasheet/c1608x7r1e474k080ae_200111.pdf",
        "Thickness 0.80mm, +0.15/-0.10mm."),
    "CGA5L1X7R1H106K160AC": height(1.9, "maximum",
        "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=CGA5L1X7R1H106K160AC",
        "Thickness 1.60mm, +0.30/-0.10mm."),
    "GRT188R61H105ME13D": height(.9, "maximum",
        "https://www.mouser.com/datasheet/2/281/product-837155.pdf",
        "Murata GRT188R61H105ME13# drawing, mirrored by Mouser: thickness 0.8+/-0.1mm; D packaging included."),
    "LTC4231IMS-1#PBF": height(1.1, "maximum",
        "https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4231.pdf",
        "MS12 package drawing: 1.10mm maximum."),
    "SN74LVC1G08DBVR": height(1.45, "maximum",
        "https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf",
        "DBV0005A package outline: 1.45mm maximum."),
    "SN74LVC1G04DBVR": height(1.45, "maximum",
        "https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf",
        "DBV0005A package outline: 1.45mm maximum."),
    "LM74700QDBVRQ1": height(1.45, "maximum",
        "https://www.ti.com/lit/ds/symlink/lm74700-q1.pdf",
        "DBV0006A package outline: 1.45mm maximum."),
    "XGL1060-222MEC": height(6.0, "maximum",
        "https://www.coilcraft.com/pdfs/ShortFormCatalog.pdf",
        "XGL1060 dimension C maximum: 6.0mm."),
    "XGL1060-682MEC": height(6.0, "maximum",
        "https://www.coilcraft.com/pdfs/ShortFormCatalog.pdf",
        "XGL1060 dimension C maximum: 6.0mm."),
    "EEHZA1H680P": height(10.5, "maximum",
        "https://industrial.panasonic.com/cdbs/www-data/pdf/RDD0000/ABA0000C1221.pdf",
        "ZA series, 1 September 2025, standard F outline: L=10.2+/-0.3mm. P is the standard version."),
    "EEHZK1V101XP": height(8.0, "maximum",
        "https://util01.industrial.panasonic.com/ea/utilities/ds/chr-vw/EEHZK1V101XP",
        "ZK series, 1 September 2025, standard D8 outline: L=7.7+/-0.3mm. XP is the standard version."),
}
# These dimensions are specified for the manufacturer's whole series, rather
# than inferred from a generic footprint or another manufacturer's package.
FAMILY_HEIGHTS = {
    r"RT0603[A-Z]{3}[0-9]{2}[0-9RKM]+L": height(0.55, "maximum",
        'https://www.datasheets.com/yageo/RT0603BRD0710RL/datasheet.pdf',
        'Yageo RT manufacturer product specificationv9 page4: RT0603 H=0.45+/-0.10mm; dimensions independent of resistance value.'),
    r"RC0603JR-07[0-9RKM]+L": height(0.55, "maximum",
        'https://www.mouser.com/catalog/specsheets/RC0603.pdf',
        'Yageo RC0603 product specification page4: H=0.45+/-0.10mm. F/J tolerance and zero-ohm resistor options share the RC0603 mechanical dimensions.'),
    r"TNPU0603[0-9RKM]+HZEN00": height(0.55, "maximum",
        'https://www.vishay.com/docs/28779/tnpue3.pdf',
        'Vishay TNPUe3 dimensions page8: TNPU0603e3 H=0.45+/-0.10mm; dimensions independent of resistance value.'),
    r"RC0402FR-07[0-9RKM]+L": height(.4, "maximum",
        "https://yageogroup.com/content/datasheet/asset/file/PYU-RC_51_ROHS_P",
        "Yageo RC_L product specification, page 4: RC0402 H=0.35+/-0.05mm across resistance values."),
    r"RC0603FR-07[0-9RKM]+L": height(.55, "maximum",
        "https://www.mouser.com/catalog/specsheets/RC0603.pdf",
        "Yageo RC0603 product specification v7, page 4: H=0.45+/-0.10mm across resistance values, including zero-ohm jumpers."),
}


def resolve_height(mpn):
    if mpn in MANUFACTURER_HEIGHTS:
        return MANUFACTURER_HEIGHTS[mpn]
    if mpn:
        for pattern, record in FAMILY_HEIGHTS.items():
            if re.fullmatch(pattern, mpn):
                return record
    return None


PLANNING_ALLOWANCES = {
    ("center", "C2600"): {
        "outward_clearance_mm": .3,
        "basis": "Chosen assembly allowance beyond the maximum body height, not a measured case clearance.",
    },
}

CSV_FIELDS = [
    "board", "group", "reference", "value", "mpn", "footprint", "dnp",
    "side", "layer", "native_x_mm", "native_y_mm", "native_rotation_deg",
    "installed_x_mm", "installed_y_mm", "installed_rotation_deg",
    "board_thickness_mm", "local_solder_plane_z_mm", "height_status",
    "height_kind", "height_mm", "height_source_url", "local_body_max_outer_z_mm",
    "local_body_nominal_outer_z_mm", "planning_allowance_mm",
    "local_planning_outer_z_mm", "study_solder_plane_z_mm",
    "study_body_max_outer_z_mm", "study_body_nominal_outer_z_mm",
    "study_planning_outer_z_mm", "source_board_sha256",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref_key(ref: str) -> tuple:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", ref)
    return (match.group(1), int(match.group(2))) if match else (ref, 0)


def ref_groups(board: str) -> dict[str, str]:
    refs = [ref for group in REVIEWED_GROUPS[board].values() for ref in group]
    assert len(refs) == EXPECTED_COUNTS[board], (board, len(refs))
    assert len(refs) == len(set(refs)), f"duplicate reference in {board} scope"
    return {ref: group for group, values in REVIEWED_GROUPS[board].items() for ref in values}


def transform(point: list[float], placement: dict) -> list[float]:
    # Match export_board_assembly.py and the existing installed board frame.
    angle = math.radians(-placement["rotation"])
    c, s = math.cos(angle), math.sin(angle)
    x, y = point
    return [round(c*x-s*y+placement["translation"][0], 6),
            round(s*x+c*y+placement["translation"][1], 6)]


def read_native_board(name: str, source: Path, all_components: bool = False) -> dict:
    """Read one board per process; do not retain pcbnew objects across boards."""
    import pcbnew as pcb

    def xy(point):
        return [round(point.x/1e6, 6), round(point.y/1e6, 6)]

    def rings(poly):
        return [{"outer": [xy(poly.COutline(i).CPoint(j)) for j in range(poly.COutline(i).PointCount())],
                 "holes": [[xy(poly.CHole(i, h).CPoint(j)) for j in range(poly.CHole(i, h).PointCount())]
                           for h in range(poly.HoleCount(i))]}
                for i in range(poly.OutlineCount())]

    before = sha256(source)
    board = pcb.LoadBoard(str(source))
    scope = ref_groups(name)
    footprints = list(board.GetFootprints())
    if all_components:
        scope = {f.GetReference(): scope.get(f.GetReference(), "other") for f in footprints}
    count = Counter(f.GetReference() for f in footprints)
    invalid = {ref: count[ref] for ref in scope if count[ref] != 1}
    if invalid:
        raise ValueError(f"{name}: expected each reviewed reference once: {invalid}")
    records = []
    for fp in sorted((f for f in footprints if f.GetReference() in scope), key=lambda f: ref_key(f.GetReference())):
        ref = fp.GetReference()
        if fp.GetLayer() not in {pcb.F_Cu, pcb.B_Cu}:
            raise ValueError(f"{name}/{ref}: unsupported component side")
        fields = {field.GetName(): field.GetText() for field in fp.GetFields()}
        fp.BuildCourtyardCaches()
        courtyards = {side: rings(fp.GetCourtyard(layer))
                      for side, layer in (("front", pcb.F_Cu), ("back", pcb.B_Cu))}
        records.append({
            "reference": ref, "group": scope[ref], "value": fp.GetValue(),
            "mpn": fields.get("MPN") or None,
            "manufacturer": fields.get("Manufacturer") or None,
            "footprint": fp.GetFPID().GetUniStringLibId(),
            "dnp": bool(fp.GetAttributes() & pcb.FP_DNP),
            "position_mm": xy(fp.GetPosition()),
            "rotation_deg": round(fp.GetOrientationDegrees() % 360, 6),
            "side": "back" if fp.GetLayer() == pcb.B_Cu else "front",
            "layer": fp.GetLayerName(), "courtyards_native_mm": courtyards,
        })
    if sha256(source) != before:
        raise RuntimeError(f"{name}: source board changed during export; run again")
    return {"sha256": before, "board_thickness_mm": board.GetDesignSettings().GetBoardThickness()/1e6,
            "copper_layers": board.GetCopperLayerCount(), "pcbnew_version": pcb.GetBuildVersion(),
            "parts": records}


def read_boards(config: dict, all_components: bool = False) -> dict:
    result = {}
    for name in REVIEWED_GROUPS:
        spec = config["boards"][name]
        if spec["components"] != "up":
            raise ValueError(f"{name}: define the mounting-flip transform before exporting this board")
        source = ROOT / spec["file"]
        process = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--read-board", name, str(source)]
            + (["--all-components"] if all_components else []),
            text=True, capture_output=True,
        )
        if process.returncode:
            raise RuntimeError(f"{name}: native PCB read failed:\n{process.stderr.strip()}")
        result[name] = json.loads(process.stdout)
    return result


def installed_courtyards(courtyards: dict, placement: dict) -> dict:
    return {side: [{"outer": [transform(point, placement) for point in poly["outer"]],
                    "holes": [[transform(point, placement) for point in hole] for hole in poly["holes"]]}
                   for poly in polygons]
            for side, polygons in courtyards.items()}


def build_export(config: dict, config_sha: str, boards: dict, study_top_z: float | None,
                 all_components: bool = False) -> tuple[dict, list[dict]]:
    if config.get("units") != "mm":
        raise ValueError("board-placement.json must use mm")
    rows, parts = [], []
    source_boards = {}
    for name, native in boards.items():
        placement = config["boards"][name]
        thickness = native["board_thickness_mm"]
        if not math.isfinite(thickness) or thickness <= 0:
            raise ValueError(f"{name}: invalid board thickness")
        source_boards[name] = {key: value for key, value in native.items() if key != "parts"}
        source_boards[name].update(file=placement["file"], installed_placement=placement)
        for part in native["parts"]:
            height_record = resolve_height(part["mpn"])
            h = height_record["value_mm"] if height_record else None
            kind = height_record["kind"] if height_record else None
            status = "verified_" + kind if kind else "unverified"
            direction = -1 if part["side"] == "back" else 1
            z = -thickness if direction == -1 else 0.0
            outer = round(z+direction*h, 6) if h is not None else None
            allowance = PLANNING_ALLOWANCES.get((name, part["reference"]))
            if allowance is None and part["side"] == "back":
                allowance = {
                    "outward_clearance_mm": .3,
                    "basis": "Chosen underside assembly allowance beyond the maximum body height, not a measured case clearance.",
                }
            margin = allowance["outward_clearance_mm"] if allowance else None
            planning_outer = round(outer+direction*margin, 6) if kind == "maximum" and margin is not None else None
            pos = transform(part["position_mm"], placement)

            def study(value):
                return round(study_top_z+value, 6) if study_top_z is not None and value is not None else None

            row = {
                "board": name, "group": part["group"], "reference": part["reference"],
                "value": part["value"], "mpn": part["mpn"], "footprint": part["footprint"], "dnp": part["dnp"],
                "side": part["side"], "layer": part["layer"],
                "native_x_mm": part["position_mm"][0], "native_y_mm": part["position_mm"][1],
                "native_rotation_deg": part["rotation_deg"], "installed_x_mm": pos[0], "installed_y_mm": pos[1],
                "installed_rotation_deg": round((part["rotation_deg"]+placement["rotation"]) % 360, 6),
                "board_thickness_mm": thickness, "local_solder_plane_z_mm": z,
                "height_status": status, "height_kind": kind, "height_mm": h,
                "height_source_url": height_record["source_url"] if height_record else None,
                "local_body_max_outer_z_mm": outer if kind == "maximum" else None,
                "local_body_nominal_outer_z_mm": outer if kind == "nominal" else None,
                "planning_allowance_mm": margin, "local_planning_outer_z_mm": planning_outer,
                "study_solder_plane_z_mm": study(z),
                "study_body_max_outer_z_mm": study(outer) if kind == "maximum" else None,
                "study_body_nominal_outer_z_mm": study(outer) if kind == "nominal" else None,
                "study_planning_outer_z_mm": study(planning_outer), "source_board_sha256": native["sha256"],
            }
            rows.append(row)
            parts.append({**row, "manufacturer": part["manufacturer"],
                          "height_basis": height_record["basis"] if height_record else "No reviewed manufacturer height for this MPN.",
                          "planning_allowance_basis": allowance["basis"] if allowance else None,
                          "courtyards_native_mm": part["courtyards_native_mm"],
                          "courtyards_installed_mm": installed_courtyards(part["courtyards_native_mm"], placement)})
    report = {
        "schema_version": 1, "units": {"length": "mm", "rotation": "degrees"},
        "scope": "all main-board footprints" if all_components else "reviewed power groups",
        "generator": "gen/export_power_placement.py", "generator_sha256": sha256(Path(__file__).resolve()),
        "sources": {"board_placement": {"file": "mechanical/board-placement.json", "sha256": config_sha},
                    "boards": source_boards},
        "coordinates": {
            "native_xy": "KiCad native board coordinates, shown from the front for both component sides.",
            "installed_xy": "board-placement.json transform; rotate by the negative mathematical angle, then translate.",
            "rotation": "KiCad orientation; installed rotation adds the board-placement rotation.",
            "local_z": "Front solder plane is 0 mm. Back solder plane is minus the PCB's specified thickness. Bodies extend outward.",
            "board_thickness_basis": "Saved PCB design setting; manufacturing tolerance is not included.",
            "study_top_z_mm": study_top_z, "study_z_is_fixed_requirement": False,
            "study_z_note": "Optional common front-solder-plane datum for a packaging study. It is not a measured or required case height.",
        },
        "reviewed_groups": REVIEWED_GROUPS, "part_counts": dict(Counter(row["board"] for row in rows)),
        "height_counts": dict(Counter(row["height_status"] for row in rows)),
        "height_data": MANUFACTURER_HEIGHTS, "family_height_data": FAMILY_HEIGHTS,
        "geometry_notes": [
            "Courtyards are native assembly-spacing polygons, not component body outlines or 3D solids.",
            "Custom pads are not approximated by their anchor rectangles; no pad-derived body dimensions are used.",
            "Unverified heights are null in JSON and blank in CSV. Nominal heights do not define maximum clearance.",
            "Package-height Z values do not add solder stand-off or an assembly tolerance stack.",
            "The 0.3mm underside planning allowance is separate from manufacturer maximum body height and measured case clearance.",
            "DNP footprints remain listed; their inclusion does not mean a component is fitted.",
            "No enclosure fit, tolerance stack, thermal result or hardware qualification is implied.",
        ],
        "parts": parts,
    }
    validate(report, rows, boards, config, all_components)
    return report, rows


def validate(report: dict, rows: list[dict], boards: dict, config: dict, all_components: bool = False) -> None:
    assert report["units"] == {"length": "mm", "rotation": "degrees"}
    expected = {name: len(native["parts"]) for name, native in boards.items()} if all_components else EXPECTED_COUNTS
    assert report["part_counts"] == expected and len(rows) == sum(expected.values())
    keys = [(row["board"], row["reference"]) for row in rows]
    assert len(keys) == len(set(keys))
    for row in rows:
        name, ref = row["board"], row["reference"]
        original = next(p for p in boards[name]["parts"] if p["reference"] == ref)
        assert [row["native_x_mm"], row["native_y_mm"]] == original["position_mm"]
        assert row["native_rotation_deg"] == original["rotation_deg"]
        assert row["side"] == original["side"] and row["layer"] == original["layer"]
        assert [row["installed_x_mm"], row["installed_y_mm"]] == transform(original["position_mm"], config["boards"][name])
        assert row["local_solder_plane_z_mm"] == (-row["board_thickness_mm"] if row["side"] == "back" else 0)
        if row["height_status"] == "unverified":
            assert row["height_mm"] is None and row["height_source_url"] is None
        if row["height_kind"] != "maximum":
            assert row["local_body_max_outer_z_mm"] is None and row["local_planning_outer_z_mm"] is None


def csv_text(rows: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare saved exports with a fresh native read; write nothing")
    parser.add_argument("--all-components", action="store_true", help="Export every footprint on the three main boards to component-placement.csv/json")
    parser.add_argument("--study-top-z", type=float, help="Optional front-plane Z for a packaging study, in mm")
    parser.add_argument("--read-board", nargs=2, metavar=("BOARD", "FILE"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.read_board:
        name, source = args.read_board
        print(json.dumps(read_native_board(name, Path(source), args.all_components)))
        return 0
    if args.study_top_z is not None and not math.isfinite(args.study_top_z):
        parser.error("--study-top-z must be a finite number")
    config_sha = sha256(CONFIG)
    config = json.loads(CONFIG.read_text())
    boards = read_boards(config, args.all_components)
    report, rows = build_export(config, config_sha, boards, args.study_top_z, args.all_components)
    assert sha256(CONFIG) == config_sha, "board placement changed during export"
    for name, data in boards.items():
        assert sha256(ROOT/config["boards"][name]["file"]) == data["sha256"], f"{name} changed during export"
    stem = "component-placement" if args.all_components else "power-placement"
    outputs = {ROOT/f"mechanical/{stem}.csv": csv_text(rows),
               ROOT/f"mechanical/{stem}.json": json.dumps(report, indent=2)+"\n"}
    if args.check:
        stale = [path.relative_to(ROOT).as_posix() for path, text in outputs.items()
                 if not path.exists() or path.read_text() != text]
        if stale:
            raise SystemExit("Regenerate the placement export: " + ", ".join(stale))
        print(f"Placement export matches all {len(rows)} native source positions, board transforms and height status.")
    else:
        for path, text in outputs.items():
            path.write_text(text)
        print(f"Exported {len(rows)} footprints to mechanical/{stem}.csv and mechanical/{stem}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
