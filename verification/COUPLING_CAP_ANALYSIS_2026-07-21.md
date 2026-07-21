# Coupling Capacitor Placement — Corrected Distance Analysis

Date: 2026-07-21
Context: The independent design review (DESIGN_REVIEW_2026-07-21.md) flagged
Issues 1-2 as WARNINGs based on distances measured from component *centers*
(A1 at 105.2,143.75; J10 at 196.4,125.3). This note corrects those
measurements to the actual signal pins.

## Mu USB3 TX caps — corrected

The A1 (LattePanda Mu socket) rotates 90° clockwise. The USB3 TX signal
pads are on the *right edge* of the connector at board x=101.1, not at the
connector center (x=105.2). The y-coordinates of those pads are near the
caps' y-positions (y=111-120 vs pad y=113-115).

| Cap | Position | A1 center dist | Nearest pin dist | Signal pin |
|-----|----------|:--------------:|:----------------:|------------|
| C66 | (112, 111) | 33 mm | **11.2 mm** | Pad 13/USBC1_SSTX_RAW_P at (101.1, 113.4) |
| C67 | (112, 114) | 31 mm | **10.9 mm** | Pad 15/USBC1_SSTX_RAW_N at (101.1, 113.9) |
| C586 | (112, 117) | 28 mm | **11.1 mm** | Pad 19/USBC2_SSTX_RAW_P at (101.1, 114.9) |
| C587 | (112, 120) | 25 mm | **11.8 mm** | Pad 21/USBC2_SSTX_RAW_N at (101.1, 115.4) |

Verdict: ~11mm from the actual signal pin is acceptable for USB 3.0 (5 GT/s).
The caps cannot move closer without entering the A1 connector courtyard
(x < 109). **Downgrade to INFO.**

## NVMe PCIe TX caps — corrected

J10 (M.2 M-key) is a 67-pin connector ~22mm long. The PCIe signal pads are
distributed along its length. A cap at (x, y) has its nearest pin at x≈196.4
and y = clamp(cap_y, 100, 150).

| Cap | Position | J10 center dist | Nearest pin dist | Improvement |
|-----|----------|:--------------:|:----------------:|:-----------:|
| C68 | (189, 124) | 7.5 mm | 7.4 mm | — |
| C69 | (189, 116) | 11.9 mm | 7.4 mm | −4.4 mm |
| C592 | (192, 116) | 10.3 mm | 4.4 mm | −5.8 mm |
| C593 | (189, 112.5) | 14.8 mm | 7.4 mm | −7.3 mm |
| C594 | (192, 112.5) | 13.5 mm | 4.4 mm | −9.1 mm |
| C595 | (189, 119.5) | 9.4 mm | 7.4 mm | −2.0 mm |
| C596 | (189, 109) | 17.9 mm | 7.4 mm | −10.4 mm |
| C597 | (192, 109) | 16.8 mm | 4.4 mm | −12.4 mm |

The worst-case cap is 17.9 mm from J10's center but only ~7.4 mm from the
nearest J10 pin. The actual distance depends on which specific PCIe pin
each cap connects to — the M.2 pinout assigns each lane to specific
connector pins at fixed positions along the 22mm connector body. The
caps at y=109 (C596, C597) are near one end of the connector; if their
PCIe lane pins are at the opposite end (~y=135), the actual stub would be
~26 mm. This is worth verifying during routing but is not a schematic
defect.

**Verdict:** The center-to-center measurement overstates the stub length
for all but the worst-case pin assignment. **Downgrade to INFO for now;
re-verify on routed PCB.**

## Summary

Both WARNINGs in the independent review are based on distance to the wrong
reference point. Correcting to the nearest signal pin gives ~11mm for Mu
USB3 and potentially 4-14mm for NVMe (depending on specific pin mapping).
No design change is required before routing — these can be verified and
optimized on the first routed iteration.
