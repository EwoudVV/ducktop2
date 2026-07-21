# Ducktop2 Pin-by-Pin Schematic Review - 2026-07-20

Generated from the live KiCad XML netlist. This table is a review aid, not a fab approval.

## Files

- CSV table: `verification/pin_by_pin_review_2026-07-20.csv`
- Source netlist: `verification/pin_review_netlist.xml`
- Contract source: `gen/generate_pin_review_table.py` and `gen/verify_design_contracts.py`

## Summary

- Total high-risk pin rows emitted: 2642
- Explicitly contracted rows: 2642
- PASS: 2642
- FAIL: 0
- REVIEW: 0

## Contract Failures

None in the generated table.

## REVIEW Rows

None. Every emitted high-risk pin row has an explicit contract.

## High-Risk Coverage Notes

- Battery fuse/shunt path, BQ25798 single-input wiring, and BQ34Z100 fuel gauge pins are contracted.
- Every STM32 package pin is contracted, including the keyboard matrix, ADC, USB, I2C, fan, radio, and system-control allocation.
- Every LattePanda Mu edge/mounting contact is contracted as used, grounded, or intentionally unconnected under the released BIOS allocation.
- Both TPS25751A dual-role ports, three source-only USB-C ports, every USB7206C pin, redrivers, protectors, EEPROMs, and default-off input paths are contracted.
- Every M.2 M-key contact is contracted, including all 3.3 V/ground contacts and intentionally unused optional sidebands.
- The optional radio daughterboard boundary is contracted so an absent board cannot block normal laptop operation or receive back-power.
- External HDMI, four-pin SSD1306 headers, TCA9548A, keyboard FFC, audio, and maker headers are contracted where the project has a clear decision.
- PCM2900C playback/record, IM68A130 microphone, privacy-enable path, speaker BTL outputs, RTL8111H HSIO6 PCIe, MDI ESD, and JXD1 integrated-magnetics jack pins are explicitly contracted.
- The native Mu eDP connector and panel harness are release-gated in docs/display-direct-edp.md because neither connector is routed through the carrier-board netlist.
- REVIEW is not failure. It is a deliberate flag for independent review.

## Independent Review Instructions

Ask the reviewer to open the CSV, sort by `status`, and attack the design in this order:

1. Any `FAIL` rows first.
2. `REVIEW` rows on power, battery, high-speed, RF, and module connectors.
3. Any row where the actual net name is surprising even if it passes the local contract.
4. Footprints and mechanical orientation separately during PCB review.
