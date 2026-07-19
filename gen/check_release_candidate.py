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
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMATIC = ROOT / "ducktop2.kicad_sch"
DEFAULT_PCB = ROOT / "ducktop2.kicad_pcb"
NUMBER = r"[-+0-9.eE]+"


def semantic_signature(sheet: str, violation: dict) -> tuple:
    return (
        sheet,
        violation.get("severity", ""),
        violation.get("type", ""),
        violation.get("description", ""),
        tuple(sorted(item.get("description", "") for item in violation.get("items", []))),
    )


# Fabrication release currently permits no physical or parity DRC violations.
DRC_ALLOWLIST: Counter = Counter()


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


def report_unexpected(label: str, actual: Counter, allowed: Counter) -> int:
    unexpected = actual - allowed
    if not unexpected:
        print(f"{label}: {sum(actual.values())} findings, all exactly allowlisted")
        return 0
    print(f"{label}: FAIL, {sum(unexpected.values())} non-allowlisted findings")
    for signature, count in unexpected.most_common(20):
        sheet, severity, rule, description, items = signature
        print(f"  {count}x [{severity}] {sheet} {rule}: {description}")
        for item in items:
            print(f"      {item}")
    if len(unexpected) > 20:
        print(f"  ... {len(unexpected) - 20} additional unique signatures")
    return sum(unexpected.values())


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
    commands = [
        (["python3", "gen/check_schematic.py"], copy_root, "schematic self-check"),
        (["python3", "gen/verify_design_contracts.py", "--schematic-only"], copy_root,
         "schematic design contracts"),
        (["python3", "gen/verify_schematic_closure.py", "verification/ducktop2_netlist.xml"],
         copy_root, "independent schematic closure audit"),
        (["python3", "gen/verify_electrical_calculations.py"], copy_root,
         "electrical calculations"),
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
    outside = offboard_footprint_anchors(pcb.read_text(encoding="utf-8"))
    if outside:
        failures += len(outside)
        print(f"Off-board footprint anchors: FAIL, {len(outside)}: {', '.join(outside)}")
    else:
        print("Off-board footprint anchors: 0")
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

    watched = project_design_files()
    before = hash_snapshot(watched)
    cli = find_kicad_cli()
    failures = 0

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
            failures += run_pcb_checks(cli, pcb, tempdir)
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
