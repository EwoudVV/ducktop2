#!/usr/bin/env python3
"""
Assign manufacturer/MPN to Ducktop2 BOM gaps by matching normalized
value and footprint against already-assigned parts.

Usage: python gen/assign_bom_mpns.py
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

PROJDIR = Path(__file__).resolve().parent.parent
INVENTORY = PROJDIR / "verification" / "component_inventory.csv"


def norm_val(v):
    v = v.strip().strip('"')
    m = re.match(r'^([\d.]+)\s*(p|n|u|k|M|R|m)\b', v, re.I)
    if m:
        return m.group(1).rstrip('.').lstrip('0') + m.group(2).upper()
    m = re.match(r'^(0R|0)\b', v)
    if m:
        return "0R"
    m = re.match(r'^([\d.]+[pnumkMR])\b', v, re.I)
    if m:
        return m.group(1).upper()
    return v.split()[0].upper() if v else ""


def norm_fp(fp):
    m = re.search(r'(C|R|D)_0\d+', fp)
    return m.group(0) if m else fp.split(":")[-1] if ":" in fp else fp


def main():
    # Index by 3 levels of specificity
    assigned_exact = defaultdict(lambda: defaultdict(list))  # (nv, nf, fp)
    assigned_norm = defaultdict(lambda: defaultdict(list))   # (nv, nf)
    assigned_val = defaultdict(lambda: defaultdict(list))    # (nv,)
    gaps = []

    with open(INVENTORY, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref = row["ref"]
            val = row["value"].strip()
            fp = row["footprint"].strip()
            mfr = row["manufacturer"].strip()
            mpn = row["mpn"].strip()
            sheet = row["sheetfile"].strip()
            eb = row["exclude_from_bom"].strip()
            ef = row["exclude_from_board"].strip()
            if eb == "yes" or ef == "yes":
                continue
            nv = norm_val(val)
            nf = norm_fp(fp)
            if mfr and mpn:
                t = (mfr, mpn)
                assigned_exact[(nv, nf, fp)][t].append((ref, val))
                assigned_norm[(nv, nf)][t].append((ref, val))
                assigned_val[(nv,)][t].append((ref, val))
            elif not mfr or not mpn:
                gaps.append((ref, sheet, val, nv, fp, nf))

    print(f"Assigned exact patterns: {len(assigned_exact)}")
    print(f"Assigned norm patterns: {len(assigned_norm)}")
    print(f"Gap components: {len(gaps)}\n")

    def best_mpn(table, key):
        if key in table:
            mpns = table[key]
            return max(mpns.items(), key=lambda x: len(x[1]))
        return None

    matchable = []
    unmatched = []

    for ref, sheet, val, nv, fp, nf in gaps:
        result = (
            best_mpn(assigned_exact, (nv, nf, fp))
            or best_mpn(assigned_norm, (nv, nf))
            or best_mpn(assigned_val, (nv,))
        )
        if result:
            (mfr, mpn), src = result
            matchable.append((mfr, mpn, nv, nf, ref, sheet, val, fp, src))
        else:
            unmatched.append((nv, nf, ref, sheet, val, fp))

    # Group matchable
    groups = defaultdict(list)
    for mfr, mpn, nv, nf, ref, sheet, val, fp, src in matchable:
        groups[(mfr, mpn, nv, nf)].append((ref, sheet, val, fp, src))

    print("=" * 80)
    print(f"ASSIGNABLE: {len(matchable)} items ({len(groups)} groups)")
    print("=" * 80)
    for (mfr, mpn, nv, nf), items in sorted(groups.items()):
        refs = ", ".join(r for r, _, _, _, _ in items)
        vals = ", ".join(sorted(set(v for _, _, v, _, _ in items), key=lambda x: (len(x), x))[:3])
        fps = list(set(f for _, _, _, f, _ in items))[0].split(":")[-1].replace("_Metric", "")
        n_src = sum(len(s) for _, _, _, _, s in items)
        print(f"  {mfr:12s} {mpn:30s}  {nv:6s} {nf:10s}  [{len(items):3d}x] {refs}")
        print(f"  {'':12s} {'':30s}  {'':6s} {'':10s}  vals: {vals}")
        print()

    # Group unmatched
    um = defaultdict(list)
    for nv, nf, ref, sheet, val, fp in unmatched:
        um[(nv, nf)].append((ref, sheet, val, fp))

    print("=" * 80)
    print(f"MANUAL REVIEW: {len(unmatched)} items ({len(um)} groups)")
    print("=" * 80)
    for (nv, nf), items in sorted(um.items()):
        refs = ", ".join(r for r, _, _, _ in items[:8])
        if len(items) > 8:
            refs += f" ... (+{len(items)-8})"
        vals = "; ".join(sorted(set(v for _, _, v, _ in items), key=lambda x: (len(x), x))[:3])
        sheets = sorted(set(s for _, s, _, _ in items))
        print(f"  {nv:6s} {nf:10s} ({len(items):3d}x) refs: {refs}")
        print(f"  {'':6s} {'':10s}  vals: {vals}")
        print(f"  {'':6s} {'':10s}  sheets: {', '.join(sheets[:3])}")
        print()

    print("=" * 80)
    print(f"SUMMARY: {len(matchable)} assignable from precedent, {len(unmatched)} need manual review")


if __name__ == "__main__":
    main()
