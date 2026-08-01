# Ducktop2 Impedance Verification — 2026-08-01

Status: **CANDIDATE GEOMETRIES READY — awaiting NextPCB engineering review.**
Completes review item 7 ("Run NextPCB impedance calculator…") up to the
fabricator hand-off: candidate trace geometries are computed here with
standard analytic models; the NextPCB field solver is authoritative for the
final production numbers.

## Stackup (L1 microstrip to solid L2 GND)

| Parameter | Value |
| --- | --- |
| Reference plane | L2 (solid GND, 1 oz) |
| Dielectric | 2116 prepreg, h = 0.125 mm, εr = 4.2 |
| Copper | 1 oz, t = 0.035 mm (L1) |
| Source | `manufacturing/mainboard_stackup_release.json`, board setup in `ducktop2.kicad_pcb`, review §9 |

## Candidate Trace Geometries

Model: Hammerstad/Jensen microstrip (with copper-thickness correction) for
single-ended; IPC-2141 edge-coupled approximation for differential.
Criterion: for differential pairs, the (width, spacing) pair with the largest
manufacturability margin (max min(w, s)) landing within 0.5 Ω of target —
these are loose-coupled designs (per-line impedance ≈ target/2), which is the
standard construction on thin dielectrics and maximises tolerance to fab
variation. Widths/spacings are also reported at εr 4.0 and 4.4 to bound the
glass-weave Dk spread.

| Interface | Type | Target | Width | Spacing | Z (model) | Width @ εr 4.0 | Width @ εr 4.4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PCIe Gen3 (NVMe x4, Wi-Fi x1) | Diff | 85 Ω ±10% | 0.290 mm (11.4 mil) | 0.800 mm (31.5 mil) | 84.8 Ω | 0.300 mm | 0.280 mm |
| USB 3.0 (single pair) | Diff | 90 Ω ±10% | 0.260 mm (10.2 mil) | 0.612 mm (24.1 mil) | 90.0 Ω | 0.270 mm | 0.250 mm |
| HDMI (4 diff pairs) | Diff | 100 Ω ±10% | 0.215 mm (8.5 mil) | 0.679 mm (26.7 mil) | 100.0 Ω | 0.225 mm | 0.205 mm |
| Ethernet MDI (4 diff pairs) | Diff | 100 Ω ±10% | 0.215 mm (8.5 mil) | 0.679 mm (26.7 mil) | 100.0 Ω | 0.225 mm | 0.205 mm |
| General single-ended | SE | 50 Ω ±10% | 0.216 mm (8.5 mil) | — | 50.0 Ω | 0.225 mm | 0.208 mm |
| USB 2.0 D+/D− | SE | 45 Ω ±10% | 0.262 mm (10.3 mil) | — | 45.0 Ω | 0.272 mm | 0.252 mm |

Reproduce with:

```sh
python3 gen/compute_impedance.py
```

## Method and Limitations

- Analytic approximations only (Hammerstad/Jensen + IPC-2141), accurate to
  roughly ±5 % for these geometries; they size the starting point, not the
  final answer.
- 2116 prepreg is glass-weave: εr varies with resin content and trace
  orientation. The ±0.2 Dk range is reflected in the width columns.
- Soldermask loading (~0.5–1 % effect) is not modelled; NextPCB's solver
  accounts for it.
- All high-speed pairs route on L1 referenced to L2; inner layers L3/L4 carry
  power islands and general routing only, so no inner-layer impedance targets
  are required.

## NextPCB Engineering-Review Submission

Submit the following to NextPCB with the stackup:

1. `manufacturing/mainboard_stackup_release.json` (stackup + target table).
2. Candidate geometries above; request field-solver confirmation for:
   - 85 Ω differential (PCIe Gen3), 90 Ω (USB3), 100 Ω (HDMI + Ethernet MDI),
     50 Ω single-ended, 45 Ω USB 2.0.
3. Ask for their production values for: trace width/spacing per target,
   prepreg style confirmation (2116/2313), εr values used, and any
   recommended adjustments to the dielectric build.

## Approval Flow

When NextPCB returns production geometries:

1. Update `manufacturing/mainboard_stackup_release.json`:
   - `approved_trace_geometries` ← fabricator values,
   - `fabricator_quote_or_drawing` ← reference,
   - `approved_by` / `approved_utc` ← approval record,
   - `status` ← `APPROVED`.
2. Convert the approved widths/spacings into KiCad board net classes
   (`ducktop2.kicad_pcb`) before high-speed routing starts (todo item 2).
