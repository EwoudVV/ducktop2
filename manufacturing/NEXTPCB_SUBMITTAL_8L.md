# Ducktop2 → NextPCB — 8-Layer Stackup + Impedance Submittal

Status: READY TO SEND. Companion to `manufacturing/mainboard_stackup_release.json`
(which stays PENDING until NextPCB engineering replies).

## Board facts

- Board: ducktop2 mainboard, 358 x 185 mm, 1.6 mm finished, CNC routed
  outline with one right-edge recess (Ethernet jack: x 352.78-358, y 88-107).
- Copper: 1 oz all layers (sheet), inner 1 oz acceptable (0.5 oz option
  noted for impedance gain, not required).
- No blind/buried vias, no via-in-pad, no HDI. All vias through 0.6/0.3 mm.
- Electrical test: continuous (flying probe), plus assembly test later.

## Proposed 8-layer stackup (our design; NextPCB to confirm/adjust)

| Layer | Copper | Dielectric | Thickness (mm) | Material / Dk |
|---|---|---|---|---|
| L1 F.Cu | SIGNAL | — | 0.035 | copper |
| — | — | prepreg 2116 | 0.125 | FR4, Dk 4.2 |
| L2 In1.Cu | GND | — | 0.035 | copper |
| — | — | core | 0.15 | FR4, Dk 4.5 |
| L3 In2.Cu | SIGNAL | — | 0.035 | copper |
| — | — | prepreg 2313 | 0.103 | FR4, Dk 4.2 |
| L4 In3.Cu | GND | — | 0.035 | copper |
| — | — | core | 0.586 | FR4, Dk 4.5 |
| L5 In4.Cu | POWER islands | — | 0.035 | copper |
| — | — | prepreg 2313 | 0.103 | FR4, Dk 4.2 |
| L6 In5.Cu | SIGNAL | — | 0.035 | copper |
| — | — | core | 0.15 | FR4, Dk 4.5 |
| L7 In6.Cu | GND | — | 0.035 | copper |
| — | — | prepreg 2116 | 0.125 | FR4, Dk 4.2 |
| L8 B.Cu | SIGNAL | — | 0.035 | copper |

Dielectric sum 1.342 mm + 8 x 0.035 mm copper = 1.622 mm. NextPCB trims the
center core (0.586 -> ~0.56 mm) to land 1.6 mm finished.

L1-over-L2 and L8-over-L7 are the impedance-critical microstrip interfaces
(2116, 0.125 mm) — identical to the previously released 6L design geometry.

## Impedance requirements (controlled-impedance option requested)

| Interface | Target | Tolerance | Our candidate geometry (L1 microstrip, 1 oz) |
|---|---|---|---|
| PCIe Gen3 (NVMe x4, Wi-Fi x1, REFCLK) | 85 ohms diff | ±10% | w 0.29 mm, gap 0.80 mm (model 84.8 Ω) |
| USB 3.x / USB-C SS lanes | 90 ohms diff | ±10% | w 0.26 mm, gap 0.612 mm (model 90.0 Ω) |
| HDMI + Ethernet MDI | 100 ohms diff | ±10% | w 0.215 mm, gap 0.679 mm (model 100.0 Ω) |
| USB 2.0 D+/D− single-ended | 45 ohms SE | ±10% | w 0.262 mm (model 45.0 Ω) |
| General single-ended | 50 ohms SE | ±10% | w 0.216 mm (model 50.0 Ω) |

Candidates from Hammerstad/Jensen + IPC-2141 (see
`verification/IMPEDANCE_VERIFICATION_2026-08-01.md`, `gen/compute_impedance.py`).
**NextPCB: field-solve these on your exact 8L stackup and confirm the widths
we should target in the Gerbers** (or accept ours within ±10%).

## Questions for NextPCB engineering

1. Confirm the 8L stackup above, including the 0.125 mm/2116 outer prepregs
   and the center core thickness for 1.6 mm finished.
2. Provide the field-solved widths for the five impedance targets on your
   production stackup (controlled-impedance service).
3. Inner copper weight confirmation (1 oz throughout acceptable?).
4. Surface finish recommendation for 0.3 mm-pitch connectors + fine-pitch
   QFN: confirm ENIG (we will specify ENIG unless recommended otherwise).
6. Solder mask color: BLACK (Matte Black preferred if available). All
   copper spacing >= 0.15 mm (5.9 mil) so the black 5 mil mask-bridge
   requirement is met with margin.
5. Confirm the right-edge recess routing (x 352.78-358, y 88-107) and the
   ±0.15 mm outline tolerance are fine for the recess corners.

## Submittal inputs to include

- ducktop2.kicad_pcb (current) + generated Gerbers after routing
- This file + manufacturing/mainboard_stackup_release.json
- verification/IMPEDANCE_VERIFICATION + net-class definitions
- Mounting-hole pattern (RETENTION_AND_MOUNTING_RELEASE.md) for tooling alignment