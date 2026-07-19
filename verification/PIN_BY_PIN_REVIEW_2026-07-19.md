# Ducktop2 Pin-by-Pin Schematic Review - 2026-07-19

Generated from the live KiCad XML netlist. This table is a review aid, not a fab approval.

## Files

- CSV table: `verification/pin_by_pin_review_2026-07-19.csv`
- Source netlist: `verification/pin_review_netlist.xml`
- Contract source: `gen/generate_pin_review_table.py` and `gen/verify_design_contracts.py`

## Summary

- Total high-risk pin rows emitted: 2761
- Explicitly contracted rows: 2410
- PASS: 2410
- FAIL: 0
- REVIEW: 351

## Contract Failures

None in the generated table.

## REVIEW Rows

Rows marked `REVIEW` are intentionally included because they belong to important chips/modules,
but they are not yet backed by a hard coded contract. They should be checked by a second
reviewer against the datasheet or the relevant reference design before fabrication.

Most REVIEW-heavy refs: A1 (189), J40 (67), U4 (49), J10 (46)

## High-Risk Coverage Notes

- Battery fuse/shunt path, BQ25798 single-input wiring, and BQ34Z100 fuel gauge pins are contracted.
- STM32 power, reset, boot, SWD, VCAP, and EC buck pins are contracted; general GPIO allocation rows remain REVIEW.
- LattePanda Mu VIN, USB2 allocation, native USB3 pairs, NVMe PCIe lanes, and exposed display outputs are contracted; the rest of the module pins remain REVIEW.
- TPS25810, HD3SS6126, CH224A, USB-C connectors, external HDMI, SSD1306 headers, TCA9548A, GNSS, RF switch, radio sockets, keyboard FFC, and maker headers are contracted where the project has a clear decision.
- PCM2900C playback/record, IM68A130 microphone, privacy-enable path, speaker BTL outputs, RTL8111H HSIO6 PCIe, MDI ESD, and JXD1 integrated-magnetics jack pins are explicitly contracted.
- The native Mu eDP connector and panel harness are release-gated in `docs/display-direct-edp.md` because neither connector is routed through the carrier-board netlist.
- REVIEW is not failure. It is a deliberate flag for independent review.

## Independent Review Instructions

Ask the reviewer to open the CSV, sort by `status`, and attack the design in this order:

1. Any `FAIL` rows first.
2. `REVIEW` rows on power, battery, high-speed, RF, and module connectors.
3. Any row where the actual net name is surprising even if it passes the local contract.
4. Footprints and mechanical orientation separately during PCB review.
