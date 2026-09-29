#!/usr/bin/env python3
"""Export proposed power-wire paths in installed coordinates. No PCB edits.

Uses numpy, scipy, shapely and matplotlib from the layout environment.
The result is a case input, not approval of an assembled harness.
"""

from pathlib import Path
import json, math, sys
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Polygon, Point
from shapely.affinity import translate

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "gen"))
import usb_power_contract as contract
import hashlib

data = json.loads((R / "mechanical/board-datums.json").read_text())["boards"]
for name, board in data.items():
    assert (
        hashlib.sha256((R / board["file"]).read_bytes()).hexdigest() == board["sha256"]
    ), "refresh board datums before exporting harness geometry"
pinmaps = {}
for loom in ["left", "right"]:
    for side in ["center", "io"]:
        for ref, pins in contract.terminal_groups(loom, side):
            pinmaps[ref] = pins
pinmaps.update(
    J2071={"1": "FG_VSS", "2": "PACK_POS_FUSED"},
    J2072={"1": "PACK_POS_FUSED", "2": "FG_VSS"},
)

tops = {"left": 8, "center": 8, "right": 8, "bms": 12}
od = contract.WIRE_MAX_OD_MM


def smooth(u):
    u = np.clip(u, 0, 1)
    return 10 * u**3 - 15 * u**4 + 6 * u**5


def port(board, ref, pin):
    f = next(f for f in data[board]["connectors_and_supports"] if f["reference"] == ref)
    theta = math.radians(f["rotation"])
    c, s = math.cos(theta), math.sin(theta)
    pins = pinmaps[ref]
    u = (int(pin) - (len(pins) + 1) / 2) * 4
    x, y = f["position"]
    return dict(
        board=board,
        ref=ref,
        pin=pin,
        net=pins[str(pin)],
        point=[x + c * u - 6.55 * s, y - s * u - 6.55 * c, tops[board] + 2.3],
        direction=[-s, -c, 0],
    )


def straight_pair(a, b, lead=2, bump=0.2, profile=None):
    a = np.array(a)
    b = np.array(b)
    length = b[0] - a[0] - 2 * lead
    assert length > 0
    u = np.linspace(0, 1, max(500, math.ceil(length / 0.025)))
    f = smooth(u)
    q = 64 * u**3 * (1 - u) ** 3
    pts = np.column_stack(
        [
            a[0] + lead + length * u,
            a[1] + (b[1] - a[1]) * f,
            a[2] + (b[2] - a[2]) * f + bump * q,
        ]
    )
    if profile is not None:
        pts[:, 2] = profile(pts[:, 0])
    return np.vstack(
        [
            np.linspace(a, pts[0], math.ceil(lead / 0.025) + 1)[:-1],
            pts,
            np.linspace(pts[-1], b, math.ceil(lead / 0.025) + 1)[1:],
        ]
    )


def right_ground(a, b):
    radius = 18.8
    cx = a[0] + radius
    cy = b[1] - radius
    s1 = np.linspace(a[:2], [a[0], cy], max(2, math.ceil((cy - a[1]) / 0.025)))
    t = np.linspace(math.pi, math.pi / 2, 2000)
    arc = np.column_stack([cx + radius * np.cos(t), cy + radius * np.sin(t)])
    s2 = np.linspace(arc[-1], b[:2], max(2, math.ceil((b[0] - cx) / 0.025)))
    xy = np.vstack([s1[:-1], arc, s2[1:]])
    arclength = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    # Rise gently over the regulator, then return horizontally into the terminal.
    h = (
        3
        * smooth((arclength - 1) / 18)
        * (1 - smooth((arclength - (arclength[-1] - 19)) / 18))
    )
    return np.column_stack([xy, a[2] + h])


def summarize(points, diameter):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    d1 = np.gradient(points, s, axis=0)
    d2 = np.gradient(d1, s, axis=0)
    curv = np.linalg.norm(np.cross(d1, d2), axis=1) / np.linalg.norm(d1, axis=1) ** 3
    radius = 1 / curv.max() if curv.max() > 1e-8 else None
    inside = None if radius is None else radius - diameter / 2
    return dict(
        exposed_length_mm=float(s[-1]),
        nominal_cut_length_mm=round(float(s[-1]) + 16, 1),
        strip_mm_each=8,
        minimum_centerline_radius_mm=radius,
        minimum_inside_radius_mm=inside,
        max_wire_height_mm=float(points[:, 2].max() + diameter / 2 + 0.2),
        bend_5d_pass=bool(inside is None or inside >= 5 * diameter * 1.01),
        bend_10d_pass=bool(inside is None or inside >= 10 * diameter * 1.01),
    )


def usb_pair(y0, y1, vertical_x, height):
    radius = 18
    start = 56.7
    finish = 306.3
    x = np.linspace(start, vertical_x - radius, 9000)
    u = np.clip((x - 65) / 195, 0, 1)
    yy = y0 - 31 * (1 - np.cos(4 * math.pi * u)) / 2
    first = np.column_stack([x, yy])
    t = np.linspace(math.pi / 2, 0, 1200)
    arc1 = np.column_stack(
        [vertical_x - radius + radius * np.cos(t), y0 - radius + radius * np.sin(t)]
    )
    vertical = np.column_stack(
        [np.full(4000, vertical_x), np.linspace(y0 - radius, y1 + radius, 4000)]
    )
    t = np.linspace(math.pi, 3 * math.pi / 2, 1200)
    arc2 = np.column_stack(
        [vertical_x + radius + radius * np.cos(t), y1 + radius + radius * np.sin(t)]
    )
    last = np.column_stack(
        [np.linspace(vertical_x + radius, finish, 1000), np.full(1000, y1)]
    )
    xy = np.vstack([first[:-1], arc1[:-1], vertical[:-1], arc2[:-1], last])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    z = 10.8 + (height - 10.8) * smooth((s - 3) / 50) * (
        1 - smooth((s - (s[-1] - 52)) / 47)
    )
    z += 0.6 * smooth((s - 5) / 10) * (1 - smooth((s - (s[-1] - 10)) / 10))
    return np.column_stack([xy, z])


routes = []
for loom in ["left", "right"]:
    for source_group, target_group in zip(
        contract.terminal_groups(loom, "center"), contract.terminal_groups(loom, "io")
    ):
        ref_c, map_c = source_group
        ref_i, map_i = target_group
        for pin_c, net in map_c.items():
            pin_i = next(p for p, n in map_i.items() if n == net)
            ends = [port("center", ref_c, int(pin_c)), port(loom, ref_i, int(pin_i))]
            ends.sort(key=lambda e: e["point"][0])
            points = (
                right_ground(ends[0]["point"], ends[1]["point"])
                if ref_c == "J2462"
                else straight_pair(
                    ends[0]["point"],
                    ends[1]["point"],
                    bump=0.1 if ref_c == "J2460" else 1.5 if ref_c == "J2452" else 0.2,
                )
            )
            routes.append(
                dict(
                    name=loom + "-" + net,
                    group=loom + "-" + ref_c,
                    ends=ends,
                    points=points.tolist(),
                    wire_od_mm=od,
                    **summarize(points, od),
                )
            )
for net in ["FG_VSS", "PACK_POS_FUSED"]:
    ends = [
        port("center", "J2071", 1 if net == "FG_VSS" else 2),
        port("bms", "J2072", 2 if net == "FG_VSS" else 1),
    ]
    assert all(e["net"] == net for e in ends)

    def profile(x):
        return 10.3 + 4.7 * smooth((x - 120) / 33) - 0.7 * smooth((x - 170) / 10.45)

    points = straight_pair(
        ends[0]["point"], ends[1]["point"], lead=0.5, profile=profile
    )
    routes.append(
        dict(
            name="bms-" + net,
            group="bms-power",
            ends=ends,
            points=points.tolist(),
            wire_od_mm=od,
            **summarize(points, od),
        )
    )
for net, pin, y0, y1, vx, height in [
    ("GND", 1, 150, 29, 282, 18.7),
    ("USB_PORT_5V", 2, 155, 24, 278, 21.9),
]:
    points = usb_pair(y0, y1, vx, height)
    ends = [
        dict(
            board="left",
            ref="J2434",
            pin=pin,
            net=net,
            point=points[0].tolist(),
            direction=[1, 0, 0],
        ),
        dict(
            board="right",
            ref="J2435",
            pin=pin,
            net=net,
            point=points[-1].tolist(),
            direction=[-1, 0, 0],
        ),
    ]
    check = summarize(points, contract.USB5_WIRE_MAX_OD_MM)
    check.update(
        nominal_cut_length_mm=round(check["exposed_length_mm"] + 4, 1),
        strip_mm_each=None,
        solder_cup_hidden_length_mm_each=2,
    )
    routes.append(
        dict(
            name="usb5-" + net,
            group="usb5",
            ends=ends,
            points=points.tolist(),
            wire_od_mm=contract.USB5_WIRE_MAX_OD_MM,
            **check,
        )
    )
distances = []
for i, a in enumerate(routes):
    for b in routes[i + 1 :]:
        pa = np.array(a["points"])
        pb = np.array(b["points"])
        dist = float(cKDTree(pa).query(pb)[0].min())
        sampling = max(
            np.linalg.norm(np.diff(pa, axis=0), axis=1).max(),
            np.linalg.norm(np.diff(pb, axis=0), axis=1).max(),
        )
        clearance = dist - (a["wire_od_mm"] + b["wire_od_mm"]) / 2 - sampling - 0.4
        if a["group"] == b["group"] or clearance < 0.5:
            distances.append(
                dict(
                    a=a["name"],
                    b=b["name"],
                    surface_clearance_after_0_2mm_each_path_allowance_mm=clearance,
                )
            )

for name, ref, expected in [
    ("left", "J2434", [35, 150, 270]),
    ("right", "J2435", [328, 29, 90]),
]:
    f = next(f for f in data[name]["connectors_and_supports"] if f["reference"] == ref)
    assert (
        max(abs(f["position"][i] - expected[i]) for i in [0, 1]) < 0.001
        and abs(f["rotation"] - expected[2]) < 0.001
    ), "review the long cable path after moving its connector"
for route in routes:
    assert route["bend_5d_pass"], (
        route["name"] + " violates the current wire bend limit"
    )
    low, high = (
        (400, 420)
        if route["group"] == "usb5"
        else (20, 90) if route["group"] == "bms-power" else (20, 100)
    )
    assert low <= route["nominal_cut_length_mm"] <= high, (
        route["name"] + " exceeds its electrical length bounds"
    )
for pair in distances:
    assert pair["surface_clearance_after_0_2mm_each_path_allowance_mm"] > 0.3, pair
result = {
    "status": "proposed cable paths; clamp, case and physical fit checks still required",
    "units": "mm",
    "coordinates": "installed board XY; Z above the outside bottom of the case",
    "source_sha256": {v["file"]: v["sha256"] for v in data.values()},
    "study_board_top_z": tops,
    "board_heights_are_fixed_requirements": False,
    "wire_position_allowance_mm": 0.2,
    "minimum_wire_surface_clearance_mm": min(
        v["surface_clearance_after_0_2mm_each_path_allowance_mm"] for v in distances
    ),
    "raw_pack_path_complete": False,
    "battery_thickness_measured": False,
    "battery_lead_lengths_measured": False,
    "notes": [
        "current Alpha 6715/6716 pages specify 5D minimum bend radius; the old 2010 6715 sheet said 10D",
        "curvature is checked at the inside of the wire, with an extra 1 percent numerical margin",
        "the 2 mm hidden length per XT30 solder cup is a planning allowance; confirm the soldered sample and final cut length",
        "wire curves assume guides hold the path within 0.2 mm; they do not establish hand-dressed bundle clearance",
        "the case study, signal cables, cooling, clamps and new power-component placement still need combined checks",
    ],
    "sources": [
        "https://www.alphawire.com/en/products/wire/ecogen/ecowire/6715",
        "https://www.alphawire.com/en/products/wire/ecogen/ecowire/6716",
        "https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf",
    ],
    "routes": [],
    "wire_clearances": distances,
    "terminals": [],
}
for route in routes:
    row = dict(route)
    row["points"] = route["points"][::10]
    if row["points"][-1] != route["points"][-1]:
        row["points"].append(route["points"][-1])
    result["routes"].append(row)
for name, board in data.items():
    for f in board["connectors_and_supports"]:
        ref = f["reference"]
        if (
            ref not in pinmaps
            and ref not in ["J2434", "J2435"]
            and not (name == "bms" and ref == "J2")
        ):
            continue
        if ref in pinmaps:
            count = len(pinmaps[ref])
            mpn = f"2060-{450+count}/998-404"
            height = 4.5
            service = "open the case and remove the keyboard or bridge above the buttons; support both wire ends while releasing the springs"
        elif ref in ["J2434", "J2435"]:
            mpn = "XT30PW-F30.G.Y / XT30U-M.G.Y"
            height = 6.0
            service = "reserve 14 mm axial withdrawal and room to grip the housings; release the nearby cable support first"
        else:
            mpn = "43045-0400 / 43025-0400"
            height = 11.35
            service = "reserve 14 mm axial withdrawal, top latch access, and 12.7 mm free wire before the first bend or clamp"
        result["terminals"].append(
            {
                "board": name,
                "reference": ref,
                "parts": mpn,
                "pcb_anchor_xyz": [*f["position"], tops[name]],
                "rotation_deg": f["rotation"],
                "reserved_height_above_pcb_mm": height,
                "courtyard_xy": f["courtyards"]["front"],
                "service": service,
                "case_and_clamp_fit_verified": False,
            }
        )
(R / "mechanical/power-harness.json").write_text(json.dumps(result, indent=2) + "\n")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch

fig, ax = plt.subplots(figsize=(15, 8.5))
fig.subplots_adjust(left=0.055, right=0.995, bottom=0.10, top=0.92)
fig.patch.set_facecolor("#faf9f4")
ax.set_facecolor("#faf9f4")
for name, board in data.items():
    for outline in board["outlines"]:
        ax.add_patch(
            Patch(
                outline["outer"],
                closed=True,
                facecolor="#e5e8e3" if name != "bms" else "#ddebf4",
                edgecolor="#53635d",
                linewidth=0.8,
            )
        )
    for f in board["connectors_and_supports"]:
        for ring in f["courtyards"]["front"]:
            ax.add_patch(
                Patch(
                    ring, closed=True, fill=False, edgecolor="#b0b6b1", linewidth=0.35
                )
            )
palette = {"left": "#238368", "right": "#976016", "bms": "#37599a", "usb5": "#9b487c"}
seen = set()
for route in routes:
    pts = np.array(route["points"])
    group = route["name"].split("-")[0]
    label = {
        "left": "left power wires",
        "right": "right power wires",
        "bms": "protected BMS pair",
        "usb5": "direct USB power pair",
    }[group]
    ax.plot(
        pts[:, 0],
        pts[:, 1],
        color=palette[group],
        linewidth=1.4,
        label=label if group not in seen else None,
    )
    seen.add(group)
    for end in route["ends"]:
        ax.plot(*end["point"][:2], marker="o", markersize=2, color=palette[group])
ax.set_aspect("equal")
ax.set_xlim(-3, 361)
ax.set_ylim(191, -4)
ax.set_xlabel("installed X (mm)")
ax.set_ylabel("installed Y (mm)")
ax.set_title(
    "power-wire paths with the revised connector positions",
    loc="left",
    fontsize=15,
    pad=15,
)
ax.legend(loc="lower left", frameon=True, fontsize=9)
fig.text(
    0.40,
    0.02,
    "proposed geometry; raw-pack leads and case/clamp fit still pending",
    fontsize=9,
    color="#5d5b54",
)
fig.savefig(R / "mechanical/power-harness.png", dpi=170)
plt.close(fig)
print("exported", len(routes), "wire paths; all meet 5D and length bounds")
