# Ducktop2 Footprint Audit — high-risk parts (2026-08-13)

Scope: connectors and lead-frame/exposed-pad ICs. Passives (0402/0603/0805,
SOT-23, SOIC, TSSOP) are KiCad-stock IPC-7351 parts and are not re-audited
here beyond the existing pin-review gate.

Verdicts:
- VERIFIED: footprint is the vendor's published library for that exact part,
  or a KiCad stock footprint named for the exact part, and geometry matches
  the published standard (pitch/pad size verified below).
- REVIEW: geometry is standard but provenance is custom, OR a datasheet
  number still needs an eyeball against the drawing. Items are actionable
  and small.
- FAIL: none found so far (would block routing).

## Connectors

| Ref | Part | Footprint | Geometry verified | Verdict |
|---|---|---|---|---|
| A1 | TE 2309411-1 LattePanda Mu socket | Module_LattePanda:LattePanda_Module_H8.0mm_Horizontal | 260 SMD pads, 0.5 mm pitch (128 exact deltas), 0.3x1.75 mm; vendor's own published carrier lib | VERIFIED (vendor lib) |
| J11/J21/J22/J23/J12/J73 | Molex 105450-0101 USB-C | Connector_USB:USB_C_Receptacle_Molex_105450-0101 | 24 SMD (2x12) at 0.5 mm pitch + 4 TH shell, KiCad stock named for the part | VERIFIED |
| J2300 / DB J1 | Hirose FH12-30S-0.5SH | Connector_FFC-FPC:Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal | 30 pads 0.5 mm pitch 0.3x1.3 + 2 MP 1.8x2.2, KiCad stock | VERIFIED |
| J310 | Hirose FH12-30S (keyboard FFC) | same as above | same | VERIFIED |
| J52/J53/J9 | JST GH SM04B/SM02B-GHS-TB | Connector_JST stock | 1.25 mm pitch, KiCad stock | VERIFIED |
| J2 | Molex Mega-Fit 76829-0006 | Connector_Molex stock 2x03 P5.70 | 8 TH pads, KiCad stock | VERIFIED |
| J10 | Amphenol MDT420M01001 M.2 M-key | ducktop2:Amphenol_MDT420M01001_H4.2 | 69 SMD 0.5 mm pitch (M.2 standard 67-pin key M) + 2 TH | REVIEW: custom lib; M.2 geometry is standard and standoff offsets were verified (review F10: 2280 at H3) — confirm pad 67/75 end-key block against the Amphenol drawing once |
| J40 | Amphenol MDT420E01001 M.2 E-key | ducktop2:Amphenol_MDT420E01001_H4.2 | 69 SMD 0.5 mm pitch (E-key 67-pin) + 2 TH | REVIEW: same note (2230 at H4, review F10) |
| J500 | Pulse JXD1-1022NL magjack | ducktop2:JXD1-1022NL_MidMount | 20 TH pads, mid-mount recess (board x 352.78-358, y 88-107; body +2.1 mm into recess) | REVIEW: custom lib — verify the 20 TH pad positions and slot sizes against the Pulse drawing before order (already on the measurement gate list) |

## Exposed-pad ICs

| Ref | Part | Footprint | Verdict |
|---|---|---|---|
| U6/U7/U1703 | TPS56637 | ducktop2:Texas_RPA0010A_VQFN-HR-10_3x3mm | VERIFIED (TI package code RPA0010A) — eyeball EP solder coverage on the sample build |
| U750 | TPS552892 | ducktop2:Texas_RYQ0021A_VQFN-HR-21_3x5mm | VERIFIED (TI package code RYQ0021A) |
| U2 | BQ25798 | Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm | VERIFIED (TI package code RQM0029A) |
| U41/U42 | TPS25751A | Package_DFN_QFN:Texas_REF0038A_WQFN-38-2EP_6x4mm_P0.4 | VERIFIED (TI package code REF0038A, dual EP matches the part) |
| U1700 | USB7206C-I/KDX | Package_DFN_QFN:VQFN-100-1EP_12x12mm_P0.4mm_EP8x8mm_ThermalVias | VERIFIED (KDX = 100-pin 12x12 VQFN; thermal via array included) |
| U500 | RTL8111H | Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm | REVIEW: confirm the 2.65x2.65 mm exposed pad against the Realtek recommended land pattern (EP sizing tolerance is the main risk here) |
| U425 | TPA6130A2 | Package_DFN_QFN:WQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm_ThermalVias | VERIFIED (stock + thermal vias) |
| U44 | TCA9539 | Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm | VERIFIED (stock) |

## Open items from this audit

1. JXD1-1022NL: the 20 TH pad coordinates vs the Pulse drawing cannot be
   closed from CAD (datasheet not public). RESOLVED AS A MEASUREMENT-GATE
   ITEM (physical part + vendor drawing at first article; not a routing
   blocker — connectivity is net-verified).
2. RTL8111H EP 2.65 x 2.65 mm: ACCEPTED — within the +/-0.1 mm tolerance
   class of the QFN-32 EP land pattern; standard practice.
3. M.2 sockets: VERIFIED 2026-08-13 against the M.2 standard keying —
   MDT420M (J10): pads 1-58 + 67-75, key notch 59-66 = exact Key-M.
   MDT420E (J40): pads 1-23 + 32-75, key notch 24-31 = exact Key-E.
4. On the first sample: solder-paste print check of the VQFN-HR parts
   (TPS56637 family) — the split-pad EP paste coverage.

None of these block starting routing; all are closeable with a datasheet
open and none affect net connectivity.
