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
import math
import re
import shutil
import subprocess
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMATIC = ROOT / "ducktop2.kicad_sch"
DEFAULT_PCB = ROOT / "ducktop2-center.kicad_pcb"
from board_release_contract import BOARD_PROJECTS
ACTIVE_BOARDS = tuple(item['pcb'] for item in BOARD_PROJECTS.values())
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


# The old monolith's waivers do not describe the split boards.
# Current PCB findings require review; none are waived by this checker.
DRC_ALLOWLIST = Counter()


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


def find_kicad_python() -> str:
    """Find an interpreter that actually imports the KiCad board API."""
    import os,sys
    candidates=[os.environ.get('KICAD_PYTHON'),sys.executable,shutil.which('python3')]
    candidates += [str(p) for p in Path('/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions').glob('*/bin/python3')]
    for candidate in dict.fromkeys(c for c in candidates if c):
        probe=subprocess.run([candidate,'-c','import pcbnew'],capture_output=True,timeout=15)
        if probe.returncode==0:return candidate
    raise RuntimeError('KiCad Python was not found; set KICAD_PYTHON to an interpreter with pcbnew')


def native_board_stats(pcb: Path, python: str | None = None) -> dict:
    code="""import json,sys,wx
app=wx.App(False)
import pcbnew as p
b=p.LoadBoard(sys.argv[1]);b.BuildConnectivity();tracks=list(b.GetTracks())
print(json.dumps(dict(footprints=len(list(b.GetFootprints())),copper_layers=b.GetCopperLayerCount(),
 native_airwires=b.GetConnectivity().GetUnconnectedCount(False),
 segments=sum(not isinstance(t,p.PCB_VIA) for t in tracks),vias=sum(isinstance(t,p.PCB_VIA) for t in tracks),
 thickness_mm=b.GetDesignSettings().GetBoardThickness()/1e6)))
"""
    output=subprocess.check_output([python or find_kicad_python(),'-c',code,str(pcb),*(['-ApplePersistenceIgnoreState','YES'] if __import__('sys').platform=='darwin' else [])],text=True,timeout=90)
    result=json.loads(output.strip().splitlines()[-1]);result['board_sha256']=sha256(pcb)
    return result


def board_contract(pcb: Path) -> dict | None:
    for name,item in BOARD_PROJECTS.items():
        if pcb.resolve()==(ROOT/item['pcb']).resolve():return {'name':name,**item}
    return None


def manufacturing_coverage(name: str) -> dict:
    """A retained package must bind its actual board, source and every artifact."""
    package = ROOT / "manufacturing" / name
    result = {"path": str(package.relative_to(ROOT)), "status": "MISSING", "fabrication_files_checked": False}
    if not package.is_dir():
        return result
    if name != "keyboard":
        result.update(status="UNREVIEWED", reason="no board-specific package verifier is implemented")
        return result
    try:
        from generate_keyboard_jlcpcb_package import verify_package
        manifest = verify_package(package)
        result.update(status=manifest["status"], fabrication_files_checked=True,
                      board_sha256=manifest["source_sha256"][BOARD_PROJECTS[name]["pcb"]])
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        result.update(status="STALE_OR_UNCHECKED", reason=str(exc))
    return result


def selection_coverage(pcbs: list[Path], stage: str, schematic: Path | None = None) -> dict:
    records = []
    for pcb in pcbs:
        contract = board_contract(pcb)
        sch = schematic_for_board(pcb, schematic)
        record = {"pcb": str(pcb), "schematic": str(sch), "pcb_sha256": sha256(pcb),
                  "schematic_sha256": sha256(sch), "contract": contract,
                  "physical_validation": "NOT_RUN"}
        try:
            record["native"] = native_board_stats(pcb)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            record["native_error"] = str(exc)
        record["manufacturing"] = manufacturing_coverage(contract["name"]) if contract else {"status":"UNSCOPED", "fabrication_files_checked":False}
        records.append(record)
    return {"stage":stage, "all_six_selected":len(pcbs)==6 and {board_contract(p)["name"] for p in pcbs if board_contract(p)}==set(BOARD_PROJECTS),
            "scope":"source identity and native inventory; DRC and physical validation are separate gates", "boards":records}


def project_design_files() -> list[Path]:
    paths: set[Path] = set()
    project_dirs = [ROOT] + [ROOT / name for name in
                            ("keyboard", "left_io", "right_io", "bms", "radio_daughterboard")]
    for directory in project_dirs:
        for pattern in ("*.kicad_sch", "*.kicad_pcb", "*.kicad_pro", "*.kicad_dru"):
            paths.update(path.resolve() for path in directory.glob(pattern))
        for name in ("sym-lib-table", "fp-lib-table"):
            table = directory / name
            if table.exists():
                paths.add(table.resolve())
    paths.update(path.resolve() for path in (ROOT / "gen").glob("*.kicad_sym"))
    paths.update(path.resolve() for path in (ROOT / "gen").glob("*.py"))
    for library in (ROOT / "ducktop2.pretty", ROOT / "Module_LattePanda.pretty"):
        paths.update(path.resolve() for path in library.glob("*.kicad_mod"))
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
    edges = []
    loops = []
    pattern = re.compile(rf"\((start|mid|end|center)\s+({NUMBER})\s+({NUMBER})\)")
    for kind in ("gr_line", "gr_arc", "gr_rect", "gr_poly", "gr_circle", "gr_curve"):
        for block in top_level_blocks(board_text, "(" + kind):
            if '(layer "Edge.Cuts")' not in block:
                continue
            points = {key: (float(x), float(y)) for key,x,y in pattern.findall(block)}
            if kind == "gr_curve":
                raise RuntimeError("Bezier Edge.Cuts needs a native outline check")
            if kind == "gr_poly":
                polygon = [(float(x),float(y)) for x,y in re.findall(rf"\(xy\s+({NUMBER})\s+({NUMBER})\)", block)]
                if len(polygon) < 3:
                    raise RuntimeError("Edge.Cuts polygon has fewer than three vertices")
                loops.append(polygon)
            elif kind == "gr_rect":
                (x0,y0),(x1,y1) = points['start'],points['end']
                loops.append([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
            elif kind == "gr_circle":
                cx,cy = points['center'];radius = math.dist(points['center'],points['end'])
                if radius <= 0:
                    raise RuntimeError("zero-radius Edge.Cuts circle")
                n = max(32, math.ceil(2*math.pi/(2*math.acos(max(-1,1-.002/radius)))))
                loops.append([(cx+radius*math.cos(2*math.pi*i/n),cy+radius*math.sin(2*math.pi*i/n)) for i in range(n)])
            elif kind == "gr_arc":
                x1,y1 = points['start'];x2,y2 = points['mid'];x3,y3 = points['end']
                d = 2*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2))
                if abs(d) < 1e-10:
                    raise RuntimeError("collinear Edge.Cuts arc")
                a,b,c = x1*x1+y1*y1,x2*x2+y2*y2,x3*x3+y3*y3
                cx = (a*(y2-y3)+b*(y3-y1)+c*(y1-y2))/d
                cy = (a*(x3-x2)+b*(x1-x3)+c*(x2-x1))/d
                radius = math.hypot(x1-cx,y1-cy)
                start,mid,end = [math.atan2(y-cy,x-cx) for x,y in (points['start'],points['mid'],points['end'])]
                sweep = (end-start)%(2*math.pi)
                if (mid-start)%(2*math.pi) > sweep:
                    sweep -= 2*math.pi
                n = max(8,math.ceil(abs(sweep)/(2*math.acos(max(-1,1-.002/radius)))))
                arc = [points['start']]+[(cx+radius*math.cos(start+sweep*i/n),cy+radius*math.sin(start+sweep*i/n)) for i in range(1,n)]+[points['end']]
                edges.extend(zip(arc,arc[1:]))
            else:
                edges.append((points['start'],points['end']))
    if not edges and not loops:
        raise RuntimeError("PCB has no supported top-level Edge.Cuts outline")

    # KiCad joins outline endpoints within its 5 um polygon tolerance.
    vertices = []
    def snap(point):
        for existing in vertices:
            if math.dist(point,existing) <= .005:
                return existing
        vertices.append(point)
        return point
    edges = [(snap(a),snap(b)) for a,b in edges]

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


def run_command(command: list[str], cwd: Path, label: str) -> str:
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
    return result.stdout + "\n" + result.stderr


def native_parity_completed(output: str, report: dict) -> bool:
    # KiCad can return success and an empty parity array when it skipped the
    # comparison. Require its completion message as well as the JSON result.
    match = re.search(r"Found\s+(\d+)\s+schematic parity issues?\b", output)
    if not match or "Failed to fetch schematic netlist" in output:
        return False
    findings = report.get("schematic_parity")
    return isinstance(findings, list) and int(match.group(1)) == len(findings)


def copy_for_static_checks(destination: Path) -> Path:
    copy_root = destination / "project"
    ignored = shutil.ignore_patterns(
        ".git", ".workbench", ".local", ".history", ".mcp-backups", "__pycache__", "*.pyc", "tmp",
        "pcb_snapshots", "project_snapshots", "build", ".venv",
    )
    def ignore(directory, names):
        omit = set(ignored(directory, names))
        if Path(directory).resolve() == (ROOT / "verification").resolve():
            omit.add("generated")
        return omit
    shutil.copytree(ROOT, copy_root, ignore=ignore)
    verification = copy_root / "verification" / "generated"
    if verification.exists():
        shutil.rmtree(verification)
    verification.mkdir(parents=True)
    return copy_root


def generated_schematic_drift(copy_root: Path) -> list[str]:
    drift: list[str] = []
    live_paths = sorted(ROOT.glob("*.kicad_sch"))
    for board in ("keyboard", "left_io", "right_io", "bms", "radio_daughterboard"):
        live_paths += sorted((ROOT / board).glob("*.kicad_sch"))
    for live in live_paths:
        candidate = copy_root / live.relative_to(ROOT)
        if not candidate.exists() or sha256(live) != sha256(candidate):
            drift.append(live.relative_to(ROOT).as_posix())
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
             "--output", str(copy_root / "verification" / "generated" / "bms_netlist.xml"), str(bms_sch)],
            check=False, capture_output=True, cwd=copy_root,
        )
    commands = [
        (["python3", "gen/check_schematic.py"], copy_root, "schematic self-check"),
        (["python3", "gen/check_schematic_annotation.py"], copy_root, "complete schematic annotation"),
        (["python3", "gen/verify_design_contracts.py", "--schematic-only"], copy_root,
         "schematic design contracts"),
        (["python3", "gen/verify_schematic_closure.py", "verification/generated/ducktop2_netlist.xml"],
         copy_root, "independent schematic closure audit (center)"),
        (["python3", "gen/verify_schematic_closure.py", "verification/generated/bms_netlist.xml", "--pack"],
         copy_root, "independent schematic closure audit (bms pack)"),
        (["python3", "gen/verify_electrical_calculations.py"], copy_root,
         "electrical calculations"),
        (["python3", "gen/verify_electrical_calculations.py", "--project", "bms"], copy_root,
         "electrical calculations (bms pack)"),
        (["python3", "gen/generate_pin_review_table.py"], copy_root,
         "pin review generation"),
        (["python3", "gen/generate_component_inventory.py", "--output-dir",
          "verification/generated/release_inventory"], copy_root, "component inventory"),
        (["sh", "tools/run_host_tests.sh"], copy_root / "firmware",
         "firmware host-policy tests"),
    ]
    for command, cwd, label in commands:
        try:
            run_command(command, cwd, label)
        except RuntimeError as exc:
            failures += 1
            print(f"{label}: FAIL: {exc}")

    # The old inventory is center-focused. Export and inspect every physical
    # board explicitly, retaining excluded/DNP rows instead of losing them.
    from report_schematic_pcb_eco import compare,parse_schematic
    import xml.etree.ElementTree as ET
    inventory=[];all_board_gaps=0
    for name,item in BOARD_PROJECTS.items():
        schematic=copy_root/item['schematic'];pcb=copy_root/item['pcb']
        netlist=copy_root/'verification/generated'/f'{name}-release-netlist.xml'
        try:
            run_command([cli,'sch','export','netlist','--format','kicadxml','--output',str(netlist),str(schematic)],
                        schematic.parent,f'{name} netlist')
            tree=ET.parse(netlist).getroot()
            parity=compare(pcb.read_text(),tree,standalone_root_prefix=name=='keyboard')
            (netlist.with_suffix('.parity.json')).write_text(json.dumps(parity,indent=2)+'\n')
            if not parity['passed']:failures+=1
            print(f"{name} independent pad parity: {'PASS' if parity['passed'] else 'FAIL'}; {parity['counts']['physical_pads_checked']} physical pads")
            for comp in parse_schematic(tree):
                fields=comp.get('fields',{});excluded=bool(comp['attributes'] & {'dnp','exclude_from_bom'})
                missing=[] if excluded else [key for key in ('Manufacturer','MPN') if not fields.get(key,'').strip()]
                all_board_gaps+=bool(missing)
                inventory.append({'board':name,'reference':comp['ref'],'value':comp['value'],
                    'footprint':comp['footprint'],'manufacturer':fields.get('Manufacturer',''),
                    'mpn':fields.get('MPN',''),'population':'excluded or DNP' if excluded else 'populated',
                    'missing_fields':';'.join(missing)})
        except (RuntimeError,OSError,ET.ParseError) as exc:
            failures+=1;all_board_gaps+=1;print(f'{name} coverage: FAIL: {exc}')
    with (copy_root/'verification/generated/six-board-inventory.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['board','reference','value','footprint','manufacturer','mpn','population','missing_fields'])
        writer.writeheader();writer.writerows(inventory)
    print(f'Six-board procurement coverage: {len(inventory)} physical component rows; {all_board_gaps} unresolved identities')

    drift = generated_schematic_drift(copy_root)
    if drift:
        failures += len(drift)
        print("Generated-source identity: FAIL: " + ", ".join(drift))
    else:
        print("Generated-source identity: PASS")

    gap_csv = copy_root / "verification/generated/release_inventory/bom_release_gaps.csv"
    if gap_csv.exists():
        with gap_csv.open(newline="", encoding="utf-8") as handle:
            bom_gaps = sum(1 for _ in csv.DictReader(handle))
        print(f"BOM procurement gaps: {bom_gaps}")
    else:
        failures += 1
        print("BOM procurement gaps: FAIL: inventory did not produce the gap CSV")
    return failures, all_board_gaps


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


def select_pcbs(stage: str, requested: Path | None) -> list[Path]:
    if requested is not None:
        return [requested.expanduser().resolve()]
    names = ACTIVE_BOARDS
    return [(ROOT / name).resolve() for name in names]


def schematic_for_board(pcb: Path, requested: Path | None = None) -> Path:
    if requested is not None:
        return requested.expanduser().resolve()
    for item in BOARD_PROJECTS.values():
        if pcb.resolve()==(ROOT/item['pcb']).resolve():return (ROOT/item['schematic']).resolve()
    if pcb.resolve() == DEFAULT_PCB.resolve():return DEFAULT_SCHEMATIC.resolve()
    return pcb.with_suffix(".kicad_sch")


def stage_pcb_project(pcb: Path, schematic: Path, destination: Path) -> Path:
    """Copy the board, its rules, and its actual schematic association."""
    destination.mkdir(parents=True, exist_ok=False)
    # Match the schematic basename without borrowing its PCB rules. The center
    # layout and schematic use different project names in the working tree.
    staged = destination / schematic.with_suffix(".kicad_pcb").name
    shutil.copyfile(pcb, staged)
    for suffix in (".kicad_pro", ".kicad_dru"):
        source = pcb.with_suffix(suffix)
        if suffix == ".kicad_pro" and not source.is_file():
            raise RuntimeError(f"missing board settings: {source}")
        if source.exists():
            shutil.copyfile(source, staged.with_suffix(suffix))
    for source in schematic.parent.glob("*.kicad_sch"):
        shutil.copyfile(source, destination / source.name)
    for name in ("fp-lib-table", "sym-lib-table"):
        source = pcb.parent / name
        if not source.exists():
            source = ROOT / name
        if source.exists():
            text = source.read_text().replace("${KIPRJMOD}", str(source.parent.resolve()))
            (destination / name).write_text(text)
    return staged


def refill_additions(saved: dict, refilled: dict, *, unrouted: bool) -> Counter:
    def findings(report):
        return Counter(semantic_signature("PCB", v) for v in report.get("violations", []))
    added = findings(refilled) - findings(saved)
    return Counter({key: count for key, count in added.items()
                    if not (unrouted and key[2] in REFILL_DELTA_TYPES)})


def report_limit_hits(report: dict) -> dict[str, int]:
    """Identify counts reaching the KiCad 10 DRC engine's per-code caps."""
    counts = Counter(item.get("type", "unconnected_items" if section == "unconnected_items" else "unknown")
                     for section in ("violations", "schematic_parity", "unconnected_items")
                     for item in report.get(section, []))
    limits = {"clearance": 499, "unconnected_items": 499}
    return {kind: count for kind, count in counts.items()
            if count >= limits.get(kind, 199)}


def run_pcb_checks(cli: str, pcb: Path, tempdir: Path,
                   schematic: Path | None = None, reports: Path | None = None, *, stage: str = 'fabrication') -> int:
    failures = 0
    schematic = schematic_for_board(pcb, schematic)
    reports = reports or tempdir / (pcb.stem + "-reports")
    reports.mkdir(parents=True, exist_ok=True)
    staged = stage_pcb_project(pcb, schematic, tempdir / (pcb.stem + "-project"))
    settings_path=staged.with_suffix('.kicad_pro')
    settings=json.loads(settings_path.read_text())
    design=settings.get('board',{}).get('design_settings',{})
    ignored=[key for key,value in design.get('rule_severities',{}).items() if value=='ignore']
    for key in ignored:design['rule_severities'][key]='warning'
    design['drc_exclusions']=[]
    settings_path.write_text(json.dumps(settings,indent=2)+'\n')
    if ignored:print('Staged DRC restores ignored categories: '+', '.join(ignored))
    drc_path = reports / "drc.json"
    drc_output = run_command([
        cli, "pcb", "drc", "--severity-all", "--severity-exclusions",
        "--schematic-parity", "--format", "json", "--output", str(drc_path), str(staged),
    ], staged.parent, "PCB DRC")
    drc = json.loads(drc_path.read_text(encoding="utf-8"))
    parity_completed = native_parity_completed(drc_output, drc)
    (reports / "native-parity-execution.json").write_text(json.dumps({
        "completed": parity_completed, "output": drc_output,
    }, indent=2) + "\n")
    if not parity_completed:
        failures += 1
        print("Schematic parity: FAIL, the native comparison did not complete")
    capped = report_limit_hits(drc)
    if capped:
        print(f"KiCad 10 reporting caps reached: {capped}. These are incomplete lists; "
              "use native connectivity for the full airwire count.")
    drc_findings = Counter(semantic_signature("PCB", v) for v in drc.get("violations", []))
    parity_findings = Counter(semantic_signature("PCB parity", v)
                              for v in drc.get("schematic_parity", []))
    failures += report_unexpected("DRC", drc_findings, DRC_ALLOWLIST)
    failures += report_unexpected("Schematic parity", parity_findings, Counter())
    unconnected = drc.get("unconnected_items", [])
    contract=board_contract(pcb)
    allow_unrouted=stage=='routing' and contract is not None and not contract['routing_complete_required']
    stats=native_board_stats(staged)
    if contract and stats['copper_layers']!=contract['copper_layers']:
        failures+=1;print(f"Copper layer count: FAIL, {stats['copper_layers']} != {contract['copper_layers']}")
    if stats['native_airwires'] and not allow_unrouted:failures+=stats['native_airwires']
    print(f"Native airwires: {stats['native_airwires']}; listed DRC items: {len(unconnected)}; expected state: {contract['routing_state'] if contract else 'explicit board, no routing exemption'}")
    (reports/'native-stats.json').write_text(json.dumps({'contract':contract,'actual':stats,'unrouted_allowed_at_this_stage':allow_unrouted},indent=2)+'\n')

    refill_path = reports / "drc_refilled.json"
    run_command([
        cli, "pcb", "drc", "--refill-zones", "--save-board",
        "--severity-all", "--severity-exclusions", "--format", "json",
        "--output", str(refill_path), str(staged),
    ], staged.parent, "Refilled-state DRC")
    refilled = json.loads(refill_path.read_text(encoding="utf-8"))
    if capped or report_limit_hits(refilled):
        print("Refill comparison is report-limited in capped categories; "
              "listed deltas do not prove the full connectivity count stayed unchanged.")
    board_text = pcb.read_text(encoding="utf-8")
    unrouted = not re.search(r"\(segment\s|\(via\s|\(arc\s+\(start", board_text)
    added = refill_additions(drc, refilled, unrouted=unrouted)
    print(f"Refilled fill state: {len(refilled.get('violations', []))} findings; "
          f"{sum(added.values())} new findings requiring review")
    failures += sum(added.values())
    for signature, count in added.most_common(10):
        print(f"  {count}x {signature[2]}: {signature[3]}")
    refilled_stats=native_board_stats(staged)
    extra_unconnected = max(0,refilled_stats['native_airwires']-stats['native_airwires'])
    (reports/'native-refilled-stats.json').write_text(json.dumps(refilled_stats,indent=2)+'\n')
    failures += extra_unconnected
    if extra_unconnected:
        print(f"Refill disconnected {extra_unconnected} additional item(s)")

    outside = offboard_footprint_anchors(pcb.read_text(encoding="utf-8"))
    if outside:
        failures += len(outside)
        print(f"Off-board footprint anchors: FAIL, {len(outside)}: {', '.join(outside)}")
    else:
        print("Off-board footprint anchors: 0")

    board_text = pcb.read_text(encoding="utf-8")
    invalid_uuids, duplicate_uuids, excess = pcb_uuid_audit(board_text)
    if invalid_uuids or duplicate_uuids:
        failures += invalid_uuids + min(len(duplicate_uuids), 10) + (1 if duplicate_uuids else 0)
        print(
            "PCB object UUIDs: FAIL, "
            f"{invalid_uuids} invalid, {len(duplicate_uuids)} duplicated values "
            f"({excess} excess occurrences)"
        )
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
    parser.add_argument("--schematic", type=Path, help="schematic associated with an explicit --pcb")
    parser.add_argument("--pcb", type=Path, help="scope PCB checks to one board")
    parser.add_argument("--output-dir", type=Path, help="retain PCB reports in this directory")
    parser.add_argument(
        "--stage", choices=("schematic", "routing", "fabrication", "production"),
        default="fabrication", help="release boundary to enforce (default: fabrication)",
    )
    args = parser.parse_args(argv)

    pcbs = select_pcbs(args.stage, args.pcb)
    if args.schematic is not None and len(pcbs) != 1:
        parser.error("--schematic needs an explicit --pcb when checking multiple boards")
    for pcb in pcbs:
        schematic = schematic_for_board(pcb, args.schematic)
        if not pcb.is_file() or not schematic.is_file():
            raise RuntimeError(f"board or associated schematic missing: {pcb}, {schematic}")
    reports = args.output_dir.expanduser().resolve() if args.output_dir else None
    if reports is not None:
        reports.mkdir(parents=True, exist_ok=True)
    print("PCB selection: " + ", ".join(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT)
                                         else str(p) for p in pcbs))

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

    try:
        with tempfile.TemporaryDirectory(prefix="ducktop2-release-check-") as temp:
            tempdir = Path(temp)
            coverage=selection_coverage(pcbs,args.stage,args.schematic)
            for row in coverage['boards']:
                if 'native_error' in row:
                    failures+=1;print(f"Native inventory: FAIL: {row['native_error']}")
                elif row['contract'] and row['native']['copper_layers']!=row['contract']['copper_layers']:
                    failures+=1;print(f"Layer count: FAIL: {row['pcb']}")
                print(f"Board coverage: {row['pcb']}; native={row.get('native')}; manufacturing={row['manufacturing']['status']}")
            if reports:(reports/'selection-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
            static_failures, bom_gaps = run_static_checks(tempdir)
            if reports:
                for path in (tempdir/'project/verification/generated').glob('*release-netlist*'):
                    shutil.copyfile(path,reports/path.name)
                inventory=tempdir/'project/verification/generated/six-board-inventory.csv'
                if inventory.exists():shutil.copyfile(inventory,reports/inventory.name)
            failures += static_failures
            if args.stage in {"fabrication", "production"}:
                for row in coverage['boards']:
                    if not row['manufacturing']['fabrication_files_checked']:
                        failures+=1
                        print(f"Manufacturing package: FAIL: {row['pcb']}: {row['manufacturing']}")
                if bom_gaps:
                    failures += max(bom_gaps, 1)
                    print(f"Fabrication BOM gate: FAIL, {bom_gaps} unresolved procurement item(s)")
                else:
                    print("Fabrication BOM gate: PASS")
                failures += require_json_status(
                    ROOT / "manufacturing/mainboard_stackup_release.json", "APPROVED",
                    "Fabricator stackup release")
            if args.stage in {"routing","fabrication","production"}:
                for _pcb in pcbs:
                    try:
                        failures += run_pcb_checks(cli, _pcb, tempdir,
                                                  schematic_for_board(_pcb, args.schematic),
                                                  reports / _pcb.stem if reports else None,stage=args.stage)
                    except (RuntimeError, OSError) as exc:
                        failures += 1
                        print(f"PCB checks ({_pcb.name}): FAIL: {exc}")
            if args.stage == "production":
                failures += production_evidence_checks()
    except (RuntimeError, OSError) as exc:
        failures += 1
        print(f"release checks: FAIL: {exc}")

    finally:
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
        print(f"{args.stage.upper()} RELEASE CHECK: FAIL ({failures} listed blocking findings/items)")
        return 1
    scope='all six boards' if args.pcb is None else 'explicitly scoped board'
    if args.stage=='schematic':
        print(f"SCHEMATIC CHECK: PASS ({scope}); no routing or fabrication approval")
    elif args.stage=='routing':
        print(f"ROUTING PREPARATION CHECK: PASS ({scope}); expected open nets remain, no fabrication approval")
    else:print(f"{args.stage.upper()} RELEASE CHECK: PASS ({scope})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
