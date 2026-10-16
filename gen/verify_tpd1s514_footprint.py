"""Check the TPD1S514 lands against TI drawing 4221703/A."""
import argparse
import json
import re
from pathlib import Path
from check_release_candidate import top_level_blocks
from report_schematic_pcb_eco import field
from generate_tpd1s514_footprint import NAME, LIB_ID

ROOT = Path(__file__).resolve().parents[1]


def validate(text):
    errors = []
    pads = list(top_level_blocks(text, "(pad"))
    copper = {}
    paste = {}
    for block in pads:
        number = re.match(r'\(pad\s+"([^"]*)"', block)[1]
        at = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)', block)
        size = re.search(r'\(size\s+([-\d.]+)\s+([-\d.]+)', block)
        xy = tuple(round(float(v), 6) for v in at.groups())
        dimensions = tuple(float(v) for v in size.groups())
        if number:
            if number in copper: errors.append("duplicate copper pad " + number)
            copper[number] = (xy, dimensions)
            if dimensions != (.225, .225): errors.append(number + " copper diameter")
            if 'smd circle' not in block: errors.append(number + " copper shape")
            layers = re.search(r'\(layers ([^)]+)\)', block)[1]
            if set(re.findall(r'"([^"]+)"', layers)) != {"F.Cu", "F.Mask"}:
                errors.append(number + " copper/mask layers")
            margin = re.search(r'\(solder_mask_margin\s+([-\d.]+)\)', block)
            if not margin or float(margin[1]) != .0375: errors.append(number + " mask opening")
        else:
            paste[xy] = dimensions
            if '"F.Paste"' not in block or dimensions != (.25, .25): errors.append("paste aperture")
            ratio = re.search(r'\(roundrect_rratio\s+([-\d.]+)\)', block)
            if not ratio or float(ratio[1]) != .2: errors.append("paste corner radius")
    expected = {row+str(col): (x, y) for row,y in zip("ABC",(-.4,0,.4))
                for col,x in enumerate((-.6,-.2,.2,.6),1)}
    if set(copper) != set(expected): errors.append("twelve named electrical pads required")
    for number, xy in expected.items():
        if number in copper and copper[number][0] != xy: errors.append(number + " grid position")
    if set(paste) != set(expected.values()) or len(pads) != 24:
        errors.append("twelve separate paste apertures required")
    if not re.search(r'\(clearance\s+0\.15\)', text): errors.append("local land clearance")
    return {"passed": not errors, "errors": errors, "pitch_mm": .4,
            "copper_diameter_mm": .225, "mask_opening_mm": .3,
            "nominal_mask_web_mm": .1, "paste_size_mm": .25,
            "paste_radius_mm": .05, "stencil_reference_mm": .1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcb", type=Path, action="append")
    args = ap.parse_args()
    rows = {"library": validate((ROOT/"ducktop2.pretty"/(NAME+".kicad_mod")).read_text())}
    files = args.pcb or [ROOT/"left_io/left_io.kicad_pcb", ROOT/"right_io/right_io.kicad_pcb"]
    for pcb in files:
        found = []
        for fp in top_level_blocks(pcb.read_text(), "(footprint"):
            ref = field(fp,"Reference")
            if ref not in {"U1743","U1783","U1763"}: continue
            found.append(ref)
            result = validate(fp)
            if re.match(r'\(footprint\s+"([^"]+)"',fp)[1] != LIB_ID:
                result["passed"] = False;result["errors"].append("wrong library identifier")
            rows[ref] = result
        if not found: raise ValueError("no TPD1S514 footprint in " + str(pcb))
    print(json.dumps(rows,indent=2))
    raise SystemExit(not all(r["passed"] for r in rows.values()))


if __name__ == "__main__": main()
