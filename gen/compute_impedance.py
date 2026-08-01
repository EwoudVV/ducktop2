#!/usr/bin/env python3
"""
Compute candidate trace geometries for the Ducktop2 6-layer stackup.

Uses the industry-standard Hammerstad/Jensen microstrip and IPC-2141
edge-coupled differential approximations for a reproducible engineering
package.  Final production geometries must come from the fabricator's field
solver; this tool sizes the starting point and the submission expectations.

Stackup (from manufacturing/mainboard_stackup_release.json + board setup):
  L1 signal   -- 2116 prepreg h=0.125mm, eps_r=4.2 -- L2 GND
  All high-speed pairs route on L1 referenced to the solid L2 GND plane.
  1 oz copper everywhere (t = 35 um).

Run:
  python3 gen/compute_impedance.py [--width-sweep] [--json path]
"""

from __future__ import annotations

import json
import math
import sys

ETA0 = 119.9169832 * math.pi  # free-space impedance, ohms

H_MM = 0.125      # prepreg thickness to reference plane
T_MM = 0.035      # 1 oz copper
EPS_R = 4.2       # 2116 prepreg Dk
EPS_R_LO, EPS_R_HI = 4.0, 4.4  # sensitivity range

# Impedance targets: (label, type, target, tolerance_pct)
TARGETS = [
    ("PCIe Gen3 (NVMe x4, Wi-Fi x1)", "diff", 85.0, 10),
    ("USB 3.0 (single pair)", "diff", 90.0, 10),
    ("HDMI (4 diff pairs)", "diff", 100.0, 10),
    ("Ethernet MDI (4 diff pairs)", "diff", 100.0, 10),
    ("General single-ended", "se", 50.0, 10),
    ("USB 2.0 D+/D-", "se", 45.0, 10),
]


def w_eff(w: float) -> float:
    # Hammerstad copper-thickness correction (t/h ~ 0.28 here, not negligible)
    return w + (T_MM / math.pi) * (1.0 + math.log(2.0 * H_MM / T_MM))


def eps_eff(eps_r: float, w: float) -> float:
    u = w_eff(w) / H_MM
    return (eps_r + 1.0) / 2.0 + (eps_r - 1.0) / 2.0 * (1.0 + 12.0 / u) ** -0.5


def z0_se(eps_r: float, w: float) -> float:
    u = w_eff(w) / H_MM
    if u <= 1.0:
        return ETA0 / (2.0 * math.pi * math.sqrt(eps_eff(eps_r, w))) * math.log(
            8.0 / u + u / 4.0
        )
    return ETA0 / (math.sqrt(eps_eff(eps_r, w)) * (u + 1.393 + 0.667 * math.log(u + 1.444)))


def z0_diff(eps_r: float, w: float, s: float) -> float:
    # IPC-2141 edge-coupled microstrip approximation
    return 2.0 * z0_se(eps_r, w) * (1.0 - 0.48 * math.exp(-0.96 * s / H_MM))


def solve_se(target: float, eps_r: float, w_min: float = 0.075, w_max: float = 0.5) -> float:
    lo, hi = w_min, w_max
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if z0_se(eps_r, mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def solve_diff(target: float, eps_r: float) -> tuple[float, float]:
    """Joint (w, s) solve: prefer the most manufacturable geometry (largest
    min(w, s) margin) that lands within 0.5 ohm of the target."""
    best = None
    w = 0.075
    while w <= 0.35:
        lo, hi = 0.075, 0.8
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if z0_diff(eps_r, w, mid) > target:
                hi = mid
            else:
                lo = mid
        s = (lo + hi) / 2.0
        z = z0_diff(eps_r, w, s)
        if abs(z - target) < 0.5:
            margin = min(w, s)
            if best is None or margin > best[0]:
                best = (margin, w, s, z)
        w += 0.005
    if best is None:
        raise RuntimeError(f"no manufacturable geometry for {target} ohm diff on this stackup")
    return best[1], best[2], best[3]


def fmt(mm: float) -> str:
    return f"{mm:.3f} mm ({mm / 0.0254:.2f} mil)"


def main() -> int:
    out: dict = {"stackup": {"h_mm": H_MM, "t_mm": T_MM, "eps_r": EPS_R}, "results": []}

    print(f"Stackup: L1 microstrip to L2 GND, h={H_MM} mm, t={T_MM} mm, eps_r={EPS_R}")
    print(f"{'Interface':44s} {'Type':5s} {'Target':>7s} {'Width':>16s} {'Spacing':>16s} {'Width @eps4.0':>14s} {'Width @eps4.4':>14s}")
    for label, kind, target, tol in TARGETS:
        entry = {"interface": label, "type": kind, "target_ohm": target, "tolerance_pct": tol}
        if kind == "se":
            w = solve_se(target, EPS_R)
            w_lo = solve_se(target, EPS_R_LO)
            w_hi = solve_se(target, EPS_R_HI)
            z = z0_se(EPS_R, w)
            entry.update({"width_mm": round(w, 4), "z_ohm": round(z, 1),
                          "width_mm_eps4_0": round(w_lo, 4), "width_mm_eps4_4": round(w_hi, 4)})
            print(f"{label:44s} {'SE':5s} {target:7.0f} {fmt(w):>16s} {'-':>16s} {fmt(w_lo):>14s} {fmt(w_hi):>14s}")
        else:
            w, s, z = solve_diff(target, EPS_R)
            _w_lo, _s_lo, _ = solve_diff(target, EPS_R_LO)
            _w_hi, _s_hi, _ = solve_diff(target, EPS_R_HI)
            entry.update({"width_mm": round(w, 4), "spacing_mm": round(s, 4),
                          "z_ohm": round(z, 1),
                          "width_mm_eps4_0": round(_w_lo, 4), "spacing_mm_eps4_0": round(_s_lo, 4),
                          "width_mm_eps4_4": round(_w_hi, 4), "spacing_mm_eps4_4": round(_s_hi, 4)})
            print(f"{label:44s} {'DIFF':5s} {target:7.0f} {fmt(w):>16s} {fmt(s):>16s} {fmt(_w_lo):>14s} {fmt(_w_hi):>14s}")
        out["results"].append(entry)

    print("\nNotes:")
    print("  - Candidates use Hammerstad/Jensen microstrip + IPC-2141 edge-coupled approximation.")
    print("  - eps_r sensitivity shown as width range; NextPCB field solver is authoritative.")
    print("  - 2116 prepreg is glass-weave: expect +/-0.1 Dk variance; confirm with fabricator.")

    if "--json" in sys.argv:
        path = sys.argv[sys.argv.index("--json") + 1]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=2)
            handle.write("\n")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
