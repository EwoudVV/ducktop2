#!/usr/bin/env python3
"""Export radio connector datums from the saved PCB, in its local frame."""
import hashlib
import json
from pathlib import Path

from check_radio_sma_geometry import check, p

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "radio_daughterboard/radio_daughterboard.kicad_pcb"


def main():
    checked = check(SOURCE)
    board = p.LoadBoard(str(SOURCE))
    axes = []
    for connector in checked["connectors"]:
        x, y = connector["origin_mm"]
        axes.append({
            "reference": connector["reference"],
            "axis_at_rear_edge_mm": [x, 20, 0.38],
            "direction": [0, -1, 0],
            "nominal_body_bounds_mm": [[x-4.76, y-13.78, -3.58],
                                       [x+4.76, y+0.49, 4.34]],
        })
    mounts = []
    for footprint in board.GetFootprints():
        if not footprint.GetReference().startswith("H"):
            continue
        for pad in footprint.Pads():
            if pad.GetDrillSize().x:
                mounts.append({"reference": footprint.GetReference(),
                               "position_mm": [pad.GetPosition().x/1e6, pad.GetPosition().y/1e6],
                               "drill_mm": [pad.GetDrillSize().x/1e6, pad.GetDrillSize().y/1e6]})
    report = {
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "coordinate_system": "radio PCB coordinates; z is relative to the top of the PCB",
        "board_thickness_mm": checked["board_thickness_mm"],
        "sma_mpn": "73251-1153",
        "sma_axes": sorted(axes, key=lambda row: row["reference"]),
        "mounting_holes": sorted(mounts, key=lambda row: row["reference"]),
        "case_transform": None,
        "mating_antenna_or_plug": None,
        "case_fit_verified": False,
        "geometry_note": "nominal body and slot-stop coordinates come from the connector model; add part tolerances, mating-plug volume and installation access in the case model",
        "drawing_reference": {
            "document": "Molex SD-73251-115 revision B3",
            "url": "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/732/73251/732511150_sd.pdf",
            "body_width_mm": 9.52,
            "body_width_tolerance_mm": 0.13,
            "board_slot_mm": 1.68,
            "board_slot_tolerance_mm": 0.08,
            "contact_projection_mm": 4.75,
            "contact_projection_tolerance_mm": 0.20,
        },
    }
    destination = ROOT / "mechanical/radio-datums.json"
    destination.write_text(json.dumps(report, indent=2)+"\n")
    print("exported radio mounting holes and both SMA body envelopes; case placement is still pending")


if __name__ == "__main__":
    main()
