#!/usr/bin/env python3
"""Phase 3: produce 4 fabricable .kicad_pcb files from the split schematics.

Board part sets come from the project netlists (verification/*_netlist.xml),
NOT the stale board_partition.json scratch file (see notes in the report):
  - left_io  = left_io netlist (261) + holes H10/H11/H12/H16 + FPC-1 connector
  - right_io = right_io netlist (158) + holes H13/H15/H17/H27 + FPC-2 connector
  - bms      = bms netlist (45) + FPC-3 connector
  - center   = original board minus L/R/B netlist parts minus 46 obsolete
               SS-lane orphans; keeps TP1-17, H1/H2/H3/H4/H14/H21-26; plus
               FPC-1/FPC-2/FPC-3 connectors

Placement: every part is transplanted by reference from the original
ducktop2.kicad_pcb (preserving the careful manual placement). Parts whose
old position falls OUTSIDE their board's region (the monolithic board was
laid out without the future cuts in mind) are re-placed deterministically:
they are clustered by old-board proximity and each cluster is translated
into the region at the first collision-free slot, keeping internal
relative layout and rotation.

Outlines: cut from the original Edge.Cuts geometry at x=70 / x=300,
including both hinge notches and the right-edge slot. BMS board is 60x60
(free choice; the old 45-part layout spans 51mm so 45 was too tight).
"""

import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_ducktop2 import PROJDIR

PCB = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
import pcbnew  # noqa: E402

ORIG = os.path.join(PROJDIR, "ducktop2.kicad_pcb")
NETLISTS = {
    "L": os.path.join(PROJDIR, "verification", "left_io_netlist.xml"),
    "R": os.path.join(PROJDIR, "verification", "right_io_netlist.xml"),
    "B": os.path.join(PROJDIR, "verification", "bms_netlist.xml"),
    "C": os.path.join(PROJDIR, "verification", "ducktop2_netlist.xml"),
}

# Board regions in the original coordinate frame (x0 of chassis = left edge)
REGIONS = {
    "L": (0, 0, 70, 185),
    "C": (70, 0, 300, 185),
    "R": (300, 0, 358, 185),
    "B": (0, 0, 60, 60),  # BMS: free choice, 60x60
}

# Forbidden zones inside a region (hinge notches / edge slots) in board coords
FORBIDDEN = {
    "L": [(12, 0, 48, 18)],
    "C": [],
    "R": [(310, 0, 346, 18), (352.78, 88, 358, 107)],
    "B": [],
}

# Holes: assigned by PHYSICAL position (each hole rides the board that
# contains its location). All 19 holes are also in the center netlist, so
# H12 (x63.8) and H27 (x353.3) must be REMOVED from the center board and
# re-added to the left/right boards as board-only footprints.
HOLES = {
    "L": ["H10", "H11", "H12", "H16"],
    "C": ["H1", "H2", "H3", "H4", "H14", "H21", "H22", "H23", "H24", "H25", "H26"],
    "R": ["H13", "H15", "H17", "H27"],
    "B": [],
}

# FPC connectors (Phase 3 = placement only; Phase 4 wires them)
FH12_100 = "FH12-100S-0.5SH_1x100-1MP_P0.50mm_Horizontal"
FH12_30 = "Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal"
CONNECTORS = {
    "L": [("FPC1_L", "ducktop2", FH12_100, (65.6, 92.5), 90)],
    "C": [
        ("FPC1_C", "ducktop2", FH12_100, (72.75, 92.5), 270),
        ("FPC2_C", "ducktop2", FH12_100, (294.6, 92.5), 90),
        ("FPC3_C", "Connector_FFC-FPC", FH12_30, (120, 2.6), 0),
    ],
    "R": [("FPC2_R", "ducktop2", FH12_100, (302.7, 92.5), 270)],
    "B": [("FPC3_B", "Connector_FFC-FPC", FH12_30, (30, 55.8), 180)],
}

CONNECTOR_KEEPOUT = {
    "L": [(64.5, 63, 69.5, 122)],
    "C": [(69, 63, 79, 122), (291, 63, 298, 122), (112, 0, 128, 8)],
    "R": [(299.5, 63, 308, 122)],
    "B": [(24, 50, 36, 60)],
}

OUTLINES = {
    "L": [(0, 0), (12, 0), (12, 18), (48, 18), (48, 0), (70, 0), (70, 185), (0, 185)],
    "C": [(70, 0), (300, 0), (300, 185), (70, 185)],
    "R": [(300, 0), (310, 0), (310, 18), (346, 18), (346, 0), (358, 0),
          (358, 88), (352.78, 88), (352.78, 107), (358, 107), (358, 185), (300, 185)],
    "B": [(0, 0), (60, 0), (60, 60), (0, 60)],
}

LIB_DIRS = {
    "ducktop2": os.path.join(PROJDIR, "ducktop2.pretty"),
    "Connector_FFC-FPC": "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_FFC-FPC.pretty",
    "MountingHole": "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/MountingHole.pretty",
}


def netlist_refs(xml):
    return set(re.findall(r'<comp ref="([^"]+)"', open(xml).read()))


def pads_bbox(fp):
    """Unused fallback; bboxes are computed text-side (see parse_pad_bboxes)."""
    raise SystemExit("use parse_pad_bboxes")


def parse_pad_bboxes(path):
    """Per-footprint pad AABBs (world mm) + per-pad geometry.

    Returns (footprint_bboxes, pad_lists):
      footprint_bboxes: ref -> (x0,y0,x1,y1) hull of all pads
      pad_lists:        ref -> [(cx, cy, hw, hh), ...] axis-aligned
                        half-extents of each pad (rotated into world frame)
    pcbnew's by-value returns (GetPosition/GetBoundingBox/...) leak BOX2/
    VECTOR2 wrappers and eventually corrupt the SWIG type table, so all
    geometry is read from the file instead.
    """
    import math

    txt = open(path).read()
    fb = {}
    pl = {}
    for m in re.finditer(r'^\t\(footprint "([^"]+)"\n', txt, re.M):
        start = m.start()
        depth = 0
        j = start
        while j < len(txt):
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = txt[start:j + 1]
        refm = re.search(r'\n\t\t\(property "Reference" "([^"]+)"\n', block)
        fm = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)\n', block)
        if not refm or not fm:
            continue
        ref = refm.group(1)
        fx, fy = float(fm.group(1)), float(fm.group(2))
        fr = float(fm.group(3)) if fm.group(3) else 0.0
        rad = math.radians(fr)
        x0 = y0 = 1e18
        x1 = y1 = -1e18
        pads = []
        for pm in re.finditer(r'\n\t\t\(pad "([^"]*)" [a-z_]+[^\n]*\n((?:\t\t\t[^\n]*\n)*?)\t\t\)',
                              block, re.M):
            pbody = pm.group(2)
            am = re.search(r'\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)', pbody)
            sm = re.search(r'\(size ([-\d.]+) ([-\d.]+)\)', pbody)
            if not am or not sm:
                continue
            px, py = float(am.group(1)), float(am.group(2))
            pa = float(am.group(3)) if am.group(3) else 0.0
            w, h = float(sm.group(1)), float(sm.group(2))
            # KiCad y-down convention: pad centre offset rotates by -R
            # relative to the mathematical +R of the footprint rotation
            cx = fx + px * math.cos(rad) + py * math.sin(rad)
            cy = fy - px * math.sin(rad) + py * math.cos(rad)
            ang = rad + math.radians(pa)
            hw = abs(w / 2 * math.cos(ang)) + abs(h / 2 * math.sin(ang))
            hh = abs(w / 2 * math.sin(ang)) + abs(h / 2 * math.cos(ang))
            pads.append((cx, cy, hw, hh))
            x0 = min(x0, cx - hw)
            y0 = min(y0, cy - hh)
            x1 = max(x1, cx + hw)
            y1 = max(y1, cy + hh)
        if pads:
            fb[ref] = (x0, y0, x1, y1)
            pl[ref] = pads
    return fb, pl


EDGE_MARGIN = 0.7   # keep re-placed pads this far from the board edge
PAD_MARGIN = 0.8    # min gap between pads of different parts (covers courtyards)


def pads_overlap(pads_a, pads_b, margin=PAD_MARGIN):
    """True if any pad AABB of a overlaps any of b, extended by margin."""
    for (ax, ay, ahw, ahh) in pads_a:
        for (bx, by, bhw, bhh) in pads_b:
            if not (ax + ahw + margin <= bx - bhw or bx + bhw + margin <= ax - ahw
                    or ay + ahh + margin <= by - bhh or by + bhh + margin <= ay - ahh):
                return True
    return False


def bbox2i(b):
    return (b.GetX() / 1e6, b.GetY() / 1e6,
            (b.GetX() + b.GetWidth()) / 1e6, (b.GetY() + b.GetHeight()) / 1e6)


def intersects(a, b, margin=0.2):
    return not (a[2] + margin <= b[0] or b[2] + margin <= a[0]
                or a[3] + margin <= b[1] or b[3] + margin <= a[1])


class Packer:
    """Deterministic cluster packing for out-of-region parts.

    Collision checks are done at PAD level (per-pad AABBs + margin), not
    footprint-hull level: hulls under-reserve parts with uneven pad layouts
    (e.g. a THT fuse whose pads sit at its bbox edge).
    """

    def __init__(self, region, occupied_pads, forbidden, padlists):
        self.region = region            # (x0, y0, x1, y1)
        self.placed_pads = list(occupied_pads)  # pad AABBs of placed parts
        self.forbidden = list(forbidden)
        self.padlists = padlists        # ref -> list of (cx, cy, hw, hh)
        self.translations = {}

    def _clear_pads(self, pads, dx, dy):
        moved = [(px + dx, py + dy, hw, hh) for (px, py, hw, hh) in pads]
        for f in self.forbidden:
            for (px, py, hw, hh) in moved:
                if not (px + hw <= f[0] or f[2] <= px - hw
                        or py + hh <= f[1] or f[3] <= py - hh):
                    return False
        for o in self.placed_pads:
            if pads_overlap(moved, [o], margin=0.35):
                return False
        return True

    def _try(self, cl, dx, dy, oldpos):
        x0, y0, x1, y1 = self.region
        for r in cl:
            pads = self.padlists.get(r)
            if not pads:
                continue
            if not self._clear_pads(pads, dx, dy):
                return False
            for (px, py, phw, phh) in pads:
                cx, cy = px + dx, py + dy
                if cx - phw < x0 + EDGE_MARGIN or cy - phh < y0 + EDGE_MARGIN \
                   or cx + phw > x1 - EDGE_MARGIN or cy + phh > y1 - EDGE_MARGIN:
                    return False
        for r in cl:
            pads = self.padlists.get(r)
            if pads:
                self.placed_pads.extend([(px + dx, py + dy, hw, hh)
                                         for (px, py, hw, hh) in pads])
            self.translations[r] = (dx, dy)
        return True

    def pack(self, refs, oldpos):
        clusters = self._cluster(refs, oldpos)
        clusters.sort(key=len, reverse=True)
        for cl in clusters:
            self._place_cluster(cl, oldpos)
        for r in refs:
            if r not in self.translations:
                self._place_one(r, oldpos)
        return self.translations

    def _cluster(self, refs, oldpos, link=10.0):
        refs = list(refs)
        parent = {r: r for r in refs}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i in range(len(refs)):
            for j in range(i + 1, len(refs)):
                a, b = refs[i], refs[j]
                dx = oldpos[a][0] - oldpos[b][0]
                dy = oldpos[a][1] - oldpos[b][1]
                if dx * dx + dy * dy <= link * link:
                    union(a, b)
        groups = {}
        for r in refs:
            groups.setdefault(find(r), []).append(r)
        return list(groups.values())

    def _bbox(self, cl, oldpos):
        xs = [oldpos[r][0] for r in cl]
        ys = [oldpos[r][1] for r in cl]
        return (min(xs), min(ys), max(xs), max(ys))

    def _place_cluster(self, cl, oldpos):
        x0, y0, x1, y1 = self.region
        b = self._bbox(cl, oldpos)
        w, h = b[2] - b[0], b[3] - b[1]
        if w > (x1 - x0) or h > (y1 - y0):
            if len(cl) <= 1:
                self._place_one(cl[0], oldpos)
                return
            if w / (x1 - x0) > h / (y1 - y0):
                cl = sorted(cl, key=lambda r: oldpos[r][0])
            else:
                cl = sorted(cl, key=lambda r: oldpos[r][1])
            mid = max(1, len(cl) // 2)
            self._place_cluster(cl[:mid], oldpos)
            self._place_cluster(cl[mid:], oldpos)
            return
        cands = []
        old_mid_x = (b[0] + b[2]) / 2
        if old_mid_x < x0:
            cands.append((x0 + 2 - b[0], y0 + 2 - b[1]))
        elif old_mid_x > x1:
            cands.append((x1 - 2 - b[2], y0 + 2 - b[1]))
        cands.append((x0 + 2 - b[0], y0 + 2 - b[1]))
        cands.append((x1 - 2 - b[2], y0 + 2 - b[1]))
        cands.append((x0 + 2 - b[0], y1 - 2 - b[3]))
        cands.append((x1 - 2 - b[2], y1 - 2 - b[3]))
        for dx, dy in cands:
            if self._try(cl, dx, dy, oldpos):
                return
        for yy in range(int(y0 + 2), int(y1 - h - 2) + 1, 2):
            for xx in range(int(x0 + 2), int(x1 - w - 2) + 1, 2):
                if self._try(cl, xx - b[0], yy - b[1], oldpos):
                    return
        for r in cl:
            self._place_one(r, oldpos)

    def _place_one(self, r, oldpos):
        pads = self.padlists.get(r)
        if not pads:
            return
        x0, y0, x1, y1 = self.region
        bw = max(p[2] for p in pads) * 2
        bh = max(p[3] for p in pads) * 2
        for yy in range(int(y0 + 2), int(y1 - bh - 2) + 1, 2):
            for xx in range(int(x0 + 2), int(x1 - bw - 2) + 1, 2):
                dx = xx - oldpos[r][0]
                dy = yy - oldpos[r][1]
                if self._try([r], dx, dy, oldpos):
                    return


def extract_block(txt, name):
    """Return (start_index, end_index) of the top-level '(name ...)' block."""
    m = re.search(r'^\t\(' + re.escape(name) + r'\n', txt, re.M)
    if not m:
        return None
    start = m.start()
    depth = 0
    i = start
    while i < len(txt):
        if txt[i] == "(":
            depth += 1
        elif txt[i] == ")":
            depth -= 1
            if depth == 0:
                return (start, i + 1)
        i += 1
    raise RuntimeError(f"unbalanced block {name}")


def parse_fp_pads(path):
    """Parse a .kicad_mod into [(cx, cy, hw, hh), ...] relative to the anchor."""
    import math
    txt = open(path).read()
    pads = []
    for pm in re.finditer(r'\t\(pad "[^"]*" [a-z_]+[^\n]*\n((?:\t\t[^\n]*\n)*?)\t\)',
                          txt, re.M):
        body = pm.group(1)
        am = re.search(r'\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)', body)
        sm = re.search(r'\(size ([-\d.]+) ([-\d.]+)\)', body)
        if not am or not sm:
            continue
        px, py = float(am.group(1)), float(am.group(2))
        pa = float(am.group(3)) if am.group(3) else 0.0
        w, h = float(sm.group(1)), float(sm.group(2))
        rad = math.radians(pa)
        hw = abs(w / 2 * math.cos(rad)) + abs(h / 2 * math.sin(rad))
        hh = abs(w / 2 * math.sin(rad)) + abs(h / 2 * math.cos(rad))
        pads.append((px, py, hw, hh))
    return pads


def resolve_connectors(board_key, final_pads, region, keepout, holes_pads):
    """Find clear positions for the board's FPC connectors.

    final_pads: pad AABBs of every placed part at its final anchor.
    Returns a new CONNECTORS list with resolved anchors (same rotations,
    scanned along the connector length axis to avoid parts/edge)."""
    import math
    x0, y0, x1, y1 = region
    # spatial grid over final_pads (4mm cells) for fast overlap rejection
    grid = {}
    for (px, py, hw, hh) in final_pads:
        for gx in range(int(px // 4) - 1, int(px // 4) + 2):
            for gy in range(int(py // 4) - 1, int(py // 4) + 2):
                grid.setdefault((gx, gy), []).append((px, py, hw, hh))

    def clear_against(wp):
        seen = set()
        for (cx, cy, hw, hh) in wp:
            for gx in range(int(cx // 4) - 1, int(cx // 4) + 2):
                for gy in range(int(cy // 4) - 1, int(cy // 4) + 2):
                    for o in grid.get((gx, gy), ()):
                        key = id(o)
                        if key in seen:
                            continue
                        seen.add(key)
                        if pads_overlap(wp, [o]):
                            return False
        return True

    out = []
    for (ref, lib, name, pos, rot) in CONNECTORS[board_key]:
        fname = name if lib == "ducktop2" else name
        fpath = os.path.join(LIB_DIRS[lib], fname + ".kicad_mod")
        pads = parse_fp_pads(fpath)
        rad = math.radians(rot)
        bx = pos[0]
        by = pos[1]
        best = None
        if board_key == "B":
            candidates = [(bx, by + off) for off in range(-(y1 - y0), int(y1 - y0) + 1, 4)]
        else:
            span = (y1 - y0 - 20)
            candidates = [(bx, by + off) for off in range(-int(span / 2), int(span / 2) + 1, 4)]
        for (ax, ay) in candidates:
            wp = []
            for (lx, ly, hw, hh) in pads:
                cx = ax + lx * math.cos(rad) - ly * math.sin(rad)
                cy = ay + lx * math.sin(rad) + ly * math.cos(rad)
                wp.append((cx, cy, hw, hh))
            ok = True
            for (cx, cy, hw, hh) in wp:
                if cx - hw < x0 + 0.6 or cy - hh < y0 + 0.6 \
                   or cx + hw > x1 - 0.6 or cy + hh > y1 - 0.6:
                    ok = False
                    break
            if not ok:
                continue
            if not clear_against(wp):
                continue
            best = (ax, ay)
            break
        if best is None:
            print(f"  WARN: no clear position for {ref} on {board_key}")
            best = pos
        out.append((ref, lib, name, best, rot))
    return out


def splice_setup_layers(path):
    """Replace the (layers) and (setup) blocks with the 8-layer originals."""
    orig = open(ORIG).read()
    layers = orig[extract_block(orig, "layers")[0]:extract_block(orig, "layers")[1]]
    setup = orig[extract_block(orig, "setup")[0]:extract_block(orig, "setup")[1]]
    txt = open(path).read()
    for name, block in (("layers", layers), ("setup", setup)):
        s, e = extract_block(txt, name)
        txt = txt[:s] + block + txt[e:]
    open(path, "w").write(txt)


def add_fp(board, lib, name, ref, pos_mm, rot, net=None):
    fp = pcbnew.FootprintLoad(LIB_DIRS[lib], name)
    assert fp, f"footprint not found: {lib}:{name}"
    fp.SetReference(ref)
    fp.SetValue(name if lib == "ducktop2" else name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetPosition(pcbnew.VECTOR2I(int(pos_mm[0] * 1e6), int(pos_mm[1] * 1e6)))
    fp.SetOrientationDegrees(rot)
    fp.SetLayer(pcbnew.F_Cu)
    if net:
        for p in fp.Pads():
            p.SetNetName(net)
    board.Add(fp)
    return fp


def _scan_blocks(txt):
    """Yield (start, end, block, ref) for every top-level footprint block."""
    pos = 0
    while True:
        m = re.search(r'^\t\(footprint "([^"]+)"\n', txt[pos:], re.M)
        if not m:
            return
        start = pos + m.start()
        depth = 0
        j = start
        while j < len(txt):
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = txt[start:j + 1]
        refm = re.search(r'\n\t\t\(property "Reference" "([^"]+)"\n', block)
        yield (start, j + 1, block, refm.group(1) if refm else None)
        pos = j + 1


def remove_footprint_blocks(txt, drop_refs):
    """Remove top-level (footprint ...) blocks whose Reference is in drop_refs."""
    out = []
    last = 0
    for (start, end, block, ref) in _scan_blocks(txt):
        out.append(txt[last:start])
        if ref not in drop_refs:
            out.append(block)
        last = end
    out.append(txt[last:])
    return "".join(out)


def rewrite_at_lines(txt, moves):
    """Rewrite the (at x y rot) line of footprint blocks by Reference."""
    out = []
    last = 0
    for (start, end, block, ref) in _scan_blocks(txt):
        out.append(txt[last:start])
        if ref in moves:
            nx, ny, nrot = moves[ref]
            block = re.sub(r'\n\t\t\(at [-\d.]+ [-\d.]+( [-\d.]+)?\)\n',
                           f"\n\t\t(at {nx:g} {ny:g} {nrot:g})\n", block, count=1)
        out.append(block)
        last = end
    out.append(txt[last:])
    return "".join(out)


def build_center_text(out, keep_refs, moves):
    """Build the center board from the ORIGINAL board text: drop non-keep
    footprint blocks, rewrite (at) for re-placed parts. No pcbnew mutation
    (SWIG corruption: Remove+Set* poisons the type table)."""
    txt = open(ORIG).read()
    drop = set(keep_refs.keys()) - set(keep_refs.values()) if False else None
    all_refs = set(re.findall(r'\n\t\t\(property "Reference" "([^"]+)"\n', txt))
    drop = all_refs - set(keep_refs)
    txt = remove_footprint_blocks(txt, drop)
    txt = rewrite_at_lines(txt, moves)
    open(out, "w").write(txt)


def add_connectors_pcbnew(out, connectors):
    """Add FPC connector footprints in a FRESH pcbnew process (never mutates
    existing footprints, so no SWIG corruption)."""
    code = f"""
import pcbnew
b = pcbnew.LoadBoard({out!r})
import json
for ref, lib, name, pos, rot in {connectors!r}:
    fp = pcbnew.FootprintLoad({LIB_DIRS['ducktop2']!r} if lib == 'ducktop2' else {LIB_DIRS['Connector_FFC-FPC']!r}, name)
    fp.SetReference(ref)
    fp.SetValue(name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetPosition(pcbnew.VECTOR2I(int(pos[0]*1e6), int(pos[1]*1e6)))
    fp.SetOrientationDegrees(rot)
    fp.SetLayer(pcbnew.F_Cu)
    b.Add(fp)
pcbnew.SaveBoard({out!r}, b)
"""
    import subprocess
    r = subprocess.run([PCB, "-c", code], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit("connector add failed")


def inject_outline_text(path, pts):
    """Append Edge.Cuts gr_line segments to the board file, removing any
    existing Edge.Cuts gr_lines (center board keeps the old monolithic
    outline). Text-based to avoid the SWIG PCB_SHAPE corruption."""
    txt = open(path).read()
    # remove existing Edge.Cuts gr_line blocks
    def remove_edge_lines(t):
        out = []
        i = 0
        while True:
            m = re.search(r'^\t\(gr_line\n', t[i:], re.M)
            if not m:
                out.append(t[i:])
                break
            out.append(t[i:i + m.start()])
            start = i + m.start()
            depth = 0
            j = start
            while j < len(t):
                if t[j] == "(":
                    depth += 1
                elif t[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = t[start:j + 1]
            if '(layer "Edge.Cuts")' not in block:
                out.append(block)
            i = j + 1
        return "".join(out)
    txt = remove_edge_lines(txt)
    n = len(pts)
    lines = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        lines.append(
            "\t(gr_line\n"
            f"\t\t(start {a[0]:g} {a[1]:g})\n"
            f"\t\t(end {b[0]:g} {b[1]:g})\n"
            "\t\t(stroke\n"
            "\t\t\t(width 0.05)\n"
            "\t\t\t(type solid)\n"
            "\t\t)\n"
            '\t\t(layer "Edge.Cuts")\n'
            "\t)\n"
        )
    insert = "".join(lines)
    # insert before the final closing paren of the root sexpr
    idx = txt.rstrip().rfind(")")
    txt = txt[:idx] + "\n" + insert + txt[idx:]
    open(path, "w").write(txt)


def parse_old_placements(path):
    """ref -> (x, y, rot, flipped) from the board TEXT (no pcbnew reads —
    by-value returns leak and corrupt SWIG)."""
    txt = open(path).read()
    out = {}
    for m in re.finditer(r'^\t\(footprint "([^"]+)"\n', txt, re.M):
        start = m.start()
        depth = 0
        j = start
        while j < len(txt):
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = txt[start:j + 1]
        refm = re.search(r'\n\t\t\(property "Reference" "([^"]+)"\n', block)
        am = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)\n', block)
        if not refm or not am:
            continue
        flipped = re.search(r'\n\t\t\(layer "B\.Cu"\)\n', block) is not None
        out[refm.group(1)] = (float(am.group(1)), float(am.group(2)),
                              float(am.group(3)) if am.group(3) else 0.0,
                              flipped)
    return out


def main():
    parts = {k: netlist_refs(v) for k, v in NETLISTS.items()}
    orphans = None
    old = parse_old_placements(ORIG)  # ref -> (x, y, rot, flipped)

    pcb_refs = set(old)
    orphans = pcb_refs - parts["L"] - parts["R"] - parts["B"] - parts["C"]
    print(f"orphans (in no schematic, dropped): {len(orphans)} "
          f"{sorted(orphans)[:8]}...")

    keep_center = pcb_refs - parts["L"] - parts["R"] - parts["B"] - orphans \
        - set(HOLES["L"]) - set(HOLES["R"])
    print(f"center keeps {len(keep_center)} footprints")

    # geometry is read from the original board TEXT (pcbnew by-value
    # returns corrupt SWIG after many calls; text parsing is leak-free).
    all_bboxes, all_pads = parse_pad_bboxes(ORIG)
    fpboxes = {r: (bb[2] - bb[0], bb[3] - bb[1]) for r, bb in all_bboxes.items()}
    occupied_by_ref = all_bboxes
    padlists = all_pads

    # FPC connector keepouts as pad-AABB rects (centre + half extents)
    def rect_to_pads(rects):
        out = []
        for (x0, y0, x1, y1) in rects:
            out.append(((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2))
        return out
    conn_keepout_pads = {k: rect_to_pads(v) for k, v in CONNECTOR_KEEPOUT.items()}
    CONNECTORS_FINAL = {}

    for board_key, out_rel, build in (
        ("L", "left_io/left_io.kicad_pcb", True),
        ("R", "right_io/right_io.kicad_pcb", True),
        ("B", "bms/bms.kicad_pcb", True),
        ("C", "ducktop2-center.kicad_pcb", False),
    ):
        out = os.path.join(PROJDIR, out_rel)
        region = REGIONS[board_key]
        x0, y0, x1, y1 = region
        if build:
            board = pcbnew.LoadBoard(out)
            board_refs = {fp.GetReference(): fp for fp in board.GetFootprints()}
            leftovers = [r for r in board_refs if r.startswith("FPC")
                         or r in HOLES[board_key]]
            assert not leftovers, \
                f"{board_key} board not clean, leftovers: {leftovers}"
            refs = set(board_refs)
        else:
            board = None
            board_refs = {}
            refs = set(keep_center)

        # 1) classify: a part is "in place" iff its pad bbox does not cross an
        # INTERNAL boundary (x=70 / x=300 cut lines). Outer chassis edges
        # (x=0, x=358) may be overhung by I/O connectors by design.
        def crosses_internal(r):
            bb = occupied_by_ref.get(r)
            if bb is None:
                return False
            if board_key in ("L", "C") and bb[2] > x1 + 0.1:
                return True
            if board_key in ("R", "C") and bb[0] < x0 - 0.1:
                return True
            if board_key == "B":
                if bb[0] < -0.1 or bb[1] < -0.1 or bb[2] > x1 + 0.1 or bb[3] > y1 + 0.1:
                    return True
            return False

        in_region = sorted(r for r in refs if r in old and not crosses_internal(r))
        out_region = sorted(r for r in refs if r in old and crosses_internal(r)) \
            + sorted(r for r in refs if r not in old)

        # 2) transplant placement from the original board
        for r in in_region + out_region:
            if build and r in old and r in board_refs:
                ox, oy, rot, flipped = old[r]
                fp = board_refs[r]
                fp.SetPosition(pcbnew.VECTOR2I(int(ox * 1e6), int(oy * 1e6)))
                fp.SetOrientationDegrees(rot)
                fp.SetLayer(pcbnew.B_Cu if flipped else pcbnew.F_Cu)

        # 3) re-place out-of-region parts (cluster translate, pad-level checks)
        occupied_pads = list(conn_keepout_pads[board_key])
        for r in in_region:
            if r in padlists:
                occupied_pads.extend(padlists[r])
        for h in HOLES[board_key]:
            if h in padlists:
                occupied_pads.extend(padlists[h])
        packer = Packer(region, occupied_pads, FORBIDDEN[board_key], padlists)
        moves = {}
        if out_region:
            trans = packer.pack(out_region,
                                {r: (old[r][0], old[r][1]) for r in out_region})
            for r, (dx, dy) in trans.items():
                nx = old[r][0] + dx
                ny = old[r][1] + dy
                moves[r] = (nx, ny, old[r][2])
                if build:
                    fp = board_refs[r]
                    fp.SetPosition(pcbnew.VECTOR2I(int(nx * 1e6), int(ny * 1e6)))

        # 3b) legality nudge: pad-level re-check of every moved part against
        # the region and all placed pads (belt-and-braces over the packer)
        if out_region:
            placed_after = list(conn_keepout_pads[board_key])
            for r in in_region:
                if r in padlists:
                    placed_after.extend(padlists[r])
            for h in HOLES[board_key]:
                if h in padlists:
                    placed_after.extend(padlists[h])
            for r in sorted(moves):
                pads = padlists.get(r)
                if not pads:
                    continue
                dx0 = moves[r][0] - old[r][0]
                dy0 = moves[r][1] - old[r][1]
                moved = [(px + dx0, py + dy0, hw, hh) for (px, py, hw, hh) in pads]
                bad = False
                for (px, py, hw, hh) in moved:
                    if px - hw < x0 + EDGE_MARGIN or py - hh < y0 + EDGE_MARGIN \
                       or px + hw > x1 - EDGE_MARGIN or py + hh > y1 - EDGE_MARGIN:
                        bad = True
                if not bad:
                    for o in placed_after:
                        if pads_overlap(moved, [o]):
                            bad = True
                            break
                if not bad:
                    placed_after.extend(moved)
                    continue
                # re-scan a 1mm grid for a legal spot INSIDE the region
                bbox = occupied_by_ref.get(r)
                bw = bbox[2] - bbox[0] if bbox else 6.0
                bh = bbox[3] - bbox[1] if bbox else 6.0
                found = None
                for yy in range(int(y0 + 1), int(y1 - bh - 1) + 1):
                    for xx in range(int(x0 + 1), int(x1 - bw - 1) + 1):
                        cand = (xx - old[r][0], yy - old[r][1])
                        cm = [(px + cand[0], py + cand[1], hw, hh)
                              for (px, py, hw, hh) in pads]
                        ok = True
                        for (px, py, hw, hh) in cm:
                            if px - hw < x0 + EDGE_MARGIN or py - hh < y0 + EDGE_MARGIN \
                               or px + hw > x1 - EDGE_MARGIN or py + hh > y1 - EDGE_MARGIN:
                                ok = False
                                break
                        if ok:
                            for o in placed_after:
                                if pads_overlap(cm, [o]):
                                    ok = False
                                    break
                        if ok:
                            found = cand
                            break
                    if found:
                        break
                if found:
                    dx0, dy0 = found
                    moves[r] = (old[r][0] + dx0, old[r][1] + dy0, old[r][2])
                    if build:
                        fp = board_refs[r]
                        fp.SetPosition(pcbnew.VECTOR2I(
                            int((old[r][0] + dx0) * 1e6),
                            int((old[r][1] + dy0) * 1e6)))
                    placed_after.extend([(px + dx0, py + dy0, hw, hh)
                                         for (px, py, hw, hh) in pads])
        print(f"[{board_key}] {len(in_region)} kept in place, "
              f"{len(out_region)} re-placed")

        # 4) resolve FPC connector positions against all final parts
        final_pads = []
        for r in refs:
            if r not in padlists:
                continue
            if r in moves:
                dx = moves[r][0] - old[r][0]
                dy = moves[r][1] - old[r][1]
            else:
                dx = dy = 0
            final_pads.extend([(px + dx, py + dy, hw, hh)
                               for (px, py, hw, hh) in padlists[r]])
        for h in HOLES[board_key]:
            if h in padlists:
                final_pads.extend(padlists[h])
        connectors = resolve_connectors(board_key, final_pads, region,
                                        [], [])
        for (ref, lib, name, pos, rot) in connectors:
            if board_key == "L":
                assert 65.0 <= pos[0] <= 70, f"{ref} not on L edge: {pos}"
            if board_key == "R":
                assert 300.0 <= pos[0] <= 305, f"{ref} not on R edge: {pos}"
        CONNECTORS_FINAL[board_key] = connectors

        if build:
            # 4) holes (board-only, loaded from their libraries)
            if HOLES[board_key]:
                for h in HOLES[board_key]:
                    ox, oy = old[h][0], old[h][1]
                    add_fp(board, "MountingHole", "MountingHole_2.7mm_M2.5",
                           h, (ox, oy), 0)

            # 5) FPC connectors
            for ref, lib, name, pos, rot in CONNECTORS_FINAL[board_key]:
                add_fp(board, lib, name, ref, pos, rot)

            pcbnew.SaveBoard(out, board)
            splice_setup_layers(out)
        else:
            # center: text surgery (no pcbnew mutation) then connectors in a
            # fresh subprocess (Remove+Set* poisons SWIG in-process)
            build_center_text(out, keep_center, moves)
            add_connectors_pcbnew(out, CONNECTORS_FINAL[board_key])
        inject_outline_text(out, OUTLINES[board_key])
        print(f"[{board_key}] wrote {out}")
        print(f"    footprints: {len(board_refs) + len(HOLES[board_key]) + len(CONNECTORS_FINAL[board_key])}")

    # --- verification: every footprint inside its region (pad-based bbox) ---
    for board_key, out_rel in (
        ("L", "left_io/left_io.kicad_pcb"),
        ("R", "right_io/right_io.kicad_pcb"),
        ("B", "bms/bms.kicad_pcb"),
        ("C", "ducktop2-center.kicad_pcb"),
    ):
        out = os.path.join(PROJDIR, out_rel)
        board = pcbnew.LoadBoard(out)
        x0, y0, x1, y1 = REGIONS[board_key]
        parsed, _ = parse_pad_bboxes(out)
        bad, overhang = [], []
        for fp in board.GetFootprints():
            bb = parsed.get(fp.GetReference())
            if bb is None:
                continue
            if board_key in ("L", "C") and bb[2] > x1 + 0.5:
                bad.append((fp.GetReference(), bb))
            if board_key in ("R", "C") and bb[0] < x0 - 0.5:
                bad.append((fp.GetReference(), bb))
            if board_key == "B" and (bb[0] < -0.5 or bb[1] < -0.5
                                     or bb[2] > x1 + 0.5 or bb[3] > y1 + 0.5):
                bad.append((fp.GetReference(), bb))
            if bb[0] < -0.5 or bb[1] < -0.5 or bb[2] > x1 + 0.5 or bb[3] > y1 + 0.5:
                overhang.append((fp.GetReference(), bb))
        print(f"[{board_key}] {len(board.GetFootprints())} footprints, "
              f"{len(bad)} crossing internal boundary, "
              f"{len(overhang)} total edge overhang")
        for r, b in bad[:10]:
            print("   boundary:", r, tuple(round(v, 1) for v in b))
        for r, b in overhang[:5]:
            print("   edge overhang (chassis, ok):", r,
                  tuple(round(v, 1) for v in b))


if __name__ == "__main__":
    main()