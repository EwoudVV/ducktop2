# Independent Ducktop2 Full-Release Review — 2026-07-27

## Verdict: SCHEMATIC BLOCKED

The active hierarchy passes its static schematic contracts, but the current
board is not a fabrication candidate. The earlier J58 stored-copper P0, the
R250/R251 physical trackpad USB short, and the three duplicate physical
references are closed by the corrective actions recorded below. Broad physical
DRC/parity findings, incomplete routing, no
released stackup, and unclosed safety, firmware, and physical-release contracts
remain. ERC is not evidence that the hardware works.

This review used the canonical tree only. Active architecture is direct Mu eDP, TCP0 HDMI, NVMe x4, E-key PCIe, RTL8111H Ethernet, native USB-C, and the optional radio daughterboard. Retired Intehill, VL822, carrier-eDP, monolithic-radio, and USB-C-trackpad architectures were not treated as active.

## Baseline and integrity

- Initial PCB SHA-256: 7a9901588f0543403025f248c84842ccc7058370dcdc033ea31654ee3fc313bc. A byte-identical snapshot is retained at .local/pcb_snapshots/20260727_trackpad_usba2_prechange/ducktop2.kicad_pcb.
- A second pre-J58 relocation snapshot is retained at .local/pcb_snapshots/20260727_j58_relocation_prechange/ducktop2.kicad_pcb.
- J58-zone corrective candidate SHA-256: `687f6f6abcf3b4dec172facf89abfe0fbff241e1d6e3cadf8baa62c83078181a`.
- Current reviewed PCB SHA-256: `25d06e11208187f597514f593d12ef28a139f637f6f02362e2592c7d4c6f4501`.
- Board: 358 x 185 mm outline with a 51 x 52 mm lower-left notch; 1,170
  footprint blocks and unique references, 4,527 segments, 52 arcs, 855 vias,
  and five top-level zones.
- Existing dirty and untracked work was retained. Git diff --check passed after every scoped change.

## P0 findings

There are no open P0 release holds from this review. The historical J58 finding
is retained below for traceability; its copied-board correction is verified in
the post-audit addendum.

### Closed P0.1 — historical stored GND pours overlapped J58 D-, D+, and VBUS

**Refs, pins, nets, and evidence.** J58 is at 171.2, 130.0. Its pads are 1 GND, 2 /Internal Services/TPAD_CONN_DM, 3 /Internal Services/TPAD_CONN_DP, and 4 /Internal Services/TPAD_5V; see [PCB J58](../ducktop2.kicad_pcb#L203345) and [pad geometry](../ducktop2.pretty/USB2_Trackpad_Cable_SolderPads_1x04_P2.54mm.kicad_mod#L18). A read-only KiCad pcbnew query independently reported GND zone 0 as filled and not needing refill, and its persisted F.Cu, In1.Cu, and In4.Cu filled polygons contain the centres of pads 2, 3, and 4.

**Historical actual versus required.** Stored manufacturing copper occupied
non-GND through-hole land locations. Every one required clearance from GND.

**Historical consequence.** A cable installation could have shorted USB D-,
D+, and the switched 5 V branch to ground through copper and plated holes.

**Correction applied.** The five zone-fill records were refreshed in an
isolated candidate and merged with an object-level diff; pads 2–4 are now
outside every stored GND polygon on F.Cu, In1.Cu, and In4.Cu.

**Remaining verification.** Inspect Gerber layers and perform the pre-power
four-wire continuity/isolation test on the assembled cable.

**Primary source.** [USB-IF Type-C Specification Rev. 2.0](https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf), section 3.5.2.

**Confidence.** High; reproduced independently by the primary reviewer.

## P1 findings

### P1.1 — The current PCB has physical shorts, clearance, mask, thermal, and unrouted failures

**Refs/nets.** The successful read-only KiCad DRC on the pre-label board reported 1,609 violations and 499 unconnected items. Examples include D2120 PD2_TX1_P shorted to keyboard columns; C502/C503 pads shorted by Wi-Fi PCIe tracks; and unrelated SYS_3V3, GND, battery, USB, audio, and HDMI pad overlaps.

**Actual versus required.** Routing in progress can explain unrouted items but not different-net copper shorts, solder-mask bridges, clearance failures, starved thermals, dangling copper, or overlapping populated footprints.

**Consequence.** The board cannot be powered, fabricated, or used as signal-integrity evidence.

**Correction.** Partition layout into placement/routing packages, remove every short before power-up, then resolve every clearance, mask, thermal, and dangling-copper failure.

**Verification.** Fresh DRC with zero non-waived errors, zero shorts, and zero unrouted items before fabrication; each deliberate exclusion needs documented rationale.

**Confidence.** High; direct KiCad result: 204 mask bridges, 199 courtyard overlaps, 154 starved thermals, 132 zero-clearance zone conflicts, 57 hole-clearance errors, 25 dangling vias, and 13 dangling tracks.

### Closed P1.2 — U170, U2004, and U2014 had duplicated PCB footprints

**Historical refs/evidence.** Each reference occurred twice on the PCB while
the active schematic had one. U170 was at 185.405,79.890 and 259.500,162.500;
U2004 at 20.138,35.450 and 25.938,31.300; U2014 at 69.000,32.500 and
201.195,67.050.

**Actual versus required.** Manufacturing requires a unique reference for each
fitted component. The current PCB has one physical block for each reference.

**Historical consequence.** BOM, PnP, assembly, test, rework, and all-board
ECO automation were ambiguous.

**Correction applied.** The stale U170, U2004, and U2014 blocks were removed
in a hash-locked copied-board candidate. The U2004 duplicate-only MUX_EN loop
and MUX_FLIP spur were removed only through their tee; the live U2000/R2006
trunk was preserved. A scoped candidate metadata sync then relinked the kept
U170/U2004 blocks to their active schematic paths.

**Verification.** The current release gate reports `PCB footprint references:
unique`; no new dangling track or via object was introduced. The remaining 199
parity observations still require separate classification.

**Confidence.** High; direct parser and KiCad parity evidence.

### P1.3 — Battery temperature protection is delegated to an unspecified external cell assembly

**Refs/pins/nets.** U719.18 BMS_TS_UNUSED goes through R853 to PACK_NEG_RAW; U719.19 VTB is NC. U2 uses fixed CHG_TS_FIXED through R16/R705 and the source requires TS_IGNORE=1. See [power sheet source](../gen/generate_power_sheet.py#L50), [TS components](../gen/generate_power_sheet.py#L144), and [charger policy](../gen/generate_power_sheet.py#L624).

**Actual versus required.** The TS-to-VSS resistor is the BQ77915 unused-function connection, not a specified pack-temperature safeguard. No cell board, cell, trip curve, harness, or qualification is released.

**Consequence.** Charge/discharge can continue outside allowable cell temperature if the external protection is absent, miswired, or fails.

**Correction.** Add specified pack NTC hardware with independent fail-safe behavior, or release an exact independently qualified cell/protection assembly.

**Verification.** Chamber hot/cold plus NTC-open/short tests that shut down safely without EC firmware.

**Primary source.** [TI BQ77915 datasheet](https://www.ti.com/lit/ds/symlink/bq77915.pdf).

**Confidence.** High.

### P1.4 — Target firmware, programming evidence, and all HIL evidence are absent

**Refs.** U4 STM32F407 and U901 RP2350 control PD, charger/source, fan, maker boundary, and fault contracts. The release is PENDING_TARGET_PORTS; all 42 HIL rows are NOT_RUN in [HIL matrix](../firmware/release/hil_matrix.csv#L2). The target boundary is explicit in [firmware README](../firmware/README.md#L105).

**Actual versus required.** Host policy tests pass but do not prove startup, reset, brownout, fault, watchdog, recovery, or real-board safety behavior.

**Consequence.** Firmware-dependent safety and normal laptop operation remain unproven.

**Correction.** Release reproducible STM32/RP2350 target builds, programming/readback and recovery procedures, then execute all programming, EC, PD, thermal/fan, and maker HIL cases.

**Verification.** Attach instrumented actual-board evidence for every HIL row.

**Confidence.** High.

### P1.5 — Charger, protector, and Mu-12-V power loops are not placed for production routing

**Refs/nets.** U2 with C701–C714, U11/Q11/Q12/RS10, and U750/L750/RS750/C750–C766 are widely separated. Critical U2 VBUS_COMBINED, PMID, VSYS, BAT_CHARGER and U750 switching nets have zero segments. U2-to-local capacitors are about 48–50 mm apart; U750-to-L750 is about 28 mm.

**Actual versus required.** BQ25798 requires close PMID ceramics, LTC4368 needs short gate/sense paths, and TPS552892 needs a tight switching loop.

**Consequence.** Ringing, EMI, heat, unstable control, and protection failure are credible.

**Correction.** Perform a dedicated unrouted-only power layout pass following the vendor layouts. Do not move existing routed parts.

**Verification.** Re-run DRC/ECO, inspect loop and return geometry, then measure ringing, transients, heat, and hot-plug behavior on the released stackup.

**Primary sources.** [TI BQ25798](https://www.ti.com/lit/ds/symlink/bq25798.pdf), [ADI LTC4368](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4368.pdf), [TI TPS552892](https://www.ti.com/lit/ds/symlink/tps552892.pdf).

**Confidence.** High for placement; parasitic margin awaits the released stackup.

### P1.6 — Routed HDMI, Wi-Fi PCIe, and NVMe pairs exceed Mu skew limits

**Refs/nets.** HDMI C150–C157/J30 skew: D2 147.2 mil, D1 71.0 mil, D0 343.5 mil, CLK 494.1 mil. Wi-Fi A1 HSIO3/J40: TX 44.3 mil, RX 41.7 mil, REFCLK 33.7 mil. NVMe J10: L1 RX 6.3 mil, L2 TX/RX 6.5 mil, L3 RX 6.5 mil, L3 TX 26.7 mil.

**Actual versus required.** The active lane mapping and AC coupling are coherent, but copper exceeds the official Mu under-5-mil data/HDMI criterion and under-15-mil PCIe REFCLK criterion.

**Consequence.** HDMI display failure, Wi-Fi PCIe downtraining/enumeration failure, and NVMe training/AER errors are credible.

**Correction.** Reroute only after stackup release using 100 Ohm HDMI and 85 Ohm PCIe geometries.

**Verification.** Coupon TDR; 4K60 boot/hot-plug/suspend tests; PCIe negotiated-speed/AER tests; sustained NVMe traffic.

**Primary sources.** [Mu HDMI guide](https://docs.lattepanda.com/content/mu_edition/design_guide_hdmi/) and [Mu PCIe guide](https://docs.lattepanda.com/content/mu_edition/design_guide_pcie/).

**Confidence.** High for the reported copper measurements; repeat after reroute.

### P1.7 — RTL8111H C502/C503 return-path capacitors are hundreds of millimetres from U500

**Refs/pins/nets.** C502 connects U500.17 GBE_HSO_P to GBE_HOST_RX_P; C503 connects U500.18 GBE_HSO_N to GBE_HOST_RX_N. They are about 205/232 mm from U500 while their nets have zero segments. C500/C501 are about 4.4 mm from U500 and that earlier concern is closed.

**Actual versus required.** The Mu guide recommends on-board Ethernet AC coupling close to the chip, under 8 mm.

**Consequence.** Long discontinuities/stubs can prevent reliable RTL8111H PCIe/Ethernet operation.

**Correction.** Move only the two unrouted capacitors beside U500 during a dedicated layout pass, then route an 85 Ohm pair.

**Verification.** Re-measure spacing/skew; demonstrate PCIe enumeration and 1 GbE error-free traffic.

**Primary source.** [Mu PCIe guide](https://docs.lattepanda.com/content/mu_edition/design_guide_pcie/).

**Confidence.** High.

### P1.8 — ~~Fabrication stackup~~ [RESOLVED via P1.4], direct-eDP harness and mainboard package are not released

**Refs/evidence.** Stackup was PENDING_NEXTPCB — now committed to `ducktop2.kicad_pcb` (6-layer 1.6mm, 2116/2313 prepreg, 1oz all layers, dual GND planes, ENIG). [Direct-eDP ledger](../manufacturing/direct_edp_harness_release.json#L2) remains PENDING without panel endpoint, 40-wire map, harness drawing/MPN, isolation, 120 Hz, or hinge-cycle evidence. The tree has keyboard release outputs but no hash-locked mainboard Gerber/drill/IPC/BOM/CPL/fab drawing.

**Consequence.** The display harness and mainboard package are not manufacturable or auditable.

**Correction.** Release a controlled eDP harness and a hash-locked mainboard package. Stackup specification is complete.

**Verification.** Fabricator written approval, TDR coupons for 85/90/100 Ohm nets, harness continuity/isolation, boot/resume/120 Hz, and hinge-cycle evidence.

**Confidence.** High.

### P1.9 — 370 passive procurement gaps prevent a released mainboard BOM

**Refs/evidence.** The isolated inventory now finds 370 gaps. [Inventory
generator](../gen/generate_component_inventory.py#L243) treats missing
manufacturer/MPN as a release gap. Trackpad C280 and C283 now have the approved
Murata MPNs used by matching existing capacitor footprints, but that targeted
correction does not create a released mainboard AVL.

**Actual versus required.** Value plus footprint is not an exact orderable part; voltage, dielectric, tolerance, current, and effective capacitance cannot be reviewed.

**Consequence.** Assembly substitutes can be unsuitable and no controlled AVL/BOM exists.

**Correction.** Assign approved manufacturer, MPN, ratings, and alternates to every populated passive, starting with power/decoupling.

**Verification.** Regenerate inventory with zero gaps and cross-check BOM/PnP against schematic and PCB.

**Confidence.** High.

### P1.10 — J58 cable retention is required but not designed

**Refs/evidence.** J58 is only four 1.0 mm drill/2.2 mm land holes in [custom footprint](../ducktop2.pretty/USB2_Trackpad_Cable_SolderPads_1x04_P2.54mm.kicad_mod#L18). [Mechanical documentation](../docs/mechanical.md#L30) requires retention but specifies no clamp, hole pattern, adhesive, tie, service loop, or test.

**Actual versus required.** The assembly instruction demands a retention feature with no released physical implementation.

**Consequence.** Solder-joint fatigue, pad damage, and intermittent USB service failures are credible.

**Correction.** Release a clamp, tie-down, or specified adhesive solution with bend radius and service removal rules.

**Verification.** First-article fit plus pull, flex, vibration, thermal-cycle, continuity, and enumeration testing.

**Primary sources.** [USB-IF Type-C Specification Rev. 2.0](https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf) and [TI TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf).

**Confidence.** High that the controlled retention design is absent.

## P2 findings

### P2.1 — Trackpad cable and current profile remain unqualified

**Refs/nets.** U64 limits J58.4 TPAD_5V to about 0.61 A. J58 1/2/3/4 is GND/D-/D+/VBUS in [generator](../gen/generate_internal_services_sheet.py#L66), [design contract](../gen/verify_design_contracts.py#L1946), and PCB.

**Actual versus required.** The electrical topology is correct for a compliant cut USB2 A-to-C cable, but no exact trackpad/cable MPN, gauge, length, inrush, or service test is released.

**Consequence.** Cable quality/current behavior and long-term reliability are unknown.

**Correction and verification.** Freeze the endpoint MPNs and test polarity/continuity, actual inrush/steady current, current-limit/short behavior, enumeration under flex, and thermal/pull/bend cycling.

**Confidence.** High for topology; medium for physical outcome.

### P2.2 — J58 silkscreen can print REF** and crosses the wire lands

**Refs/evidence.** The footprint uses literal REF** on F.SilkS and places its wire map at y=0 across the pads; see [footprint source](../ducktop2.pretty/USB2_Trackpad_Cable_SolderPads_1x04_P2.54mm.kicad_mod#L12). Plot settings do not subtract mask from silk in [PCB settings](../ducktop2.kicad_pcb#L91).

**Consequence.** Hand wiring can be misread and silkscreen can contaminate solderable copper.

**Correction.** Use J58 or the reference variable, move the legend off pads or to F.Fab/assembly data, and inspect silk/mask Gerbers.

**Verification.** Gerber inspection and first-article hand-solder review prove no silk crosses pad apertures.

**Confidence.** High for source geometry; medium for a fabricator-specific outcome.

### P2.3 — Speaker, AUX surge, Mu-12-V thermal, RF, SI, acoustic, and mechanics remain measurement holds

U420 requires an 8 Ohm, at-least-2-W continuous speaker but no exact endpoint/acoustic assembly is released; see [audio source](../gen/generate_system_audio_sheet.py#L442) and [TI TPA2012D2](https://www.ti.com/lit/ds/symlink/tpa2012d2.pdf). AUX hot-plug, 40-W Mu rail, RF coexistence, TDR, VNA, thermal, acoustic, panel mechanics, and enclosure fit need real measurements. These are release holds, not confirmed schematic defects.

## Confirmed strengths and closed findings

- The direct cable electrical ECO is coherent: U64.6, C283, and J58.4 are TPAD_5V; J58.1–3 are GND/D-/D+; U63/R254/C281/C282/C284 are absent; U62 CC channels are no-connect. The interim TPAD_5V_PRE mismatch is closed.
- The original J58-to-C1720 USB3 collision is closed by moving only unrouted
  J58 to 171.2,130.0. The stored-zone P0 is also closed by the copied,
  diffed zone-fill correction.
- U170, U2004, and U2014 now each have one physical footprint. The release
  gate enforces physical-reference uniqueness before it runs schematic checks.
- U771 now uses always-defined MCU_3V3; the previous false-VBUS-valid concern is closed.
- C500/C501 are close to U500; only C502/C503 remain misplaced.
- EC SWD recovery, maker Ioff isolation, fan full-speed default, and GNSS unused-backup treatment have explicit hardware contracts. Target implementation and measurement evidence remain holds.
- The release-facing README, verification index, build guide, mechanical
  contracts, floorplans, architecture render, PCB renders, and schematic PDF
  were refreshed to state that routing is in progress and fabrication is
  blocked.

## Commands and results

| Check | Result |
|---|---|
| Isolated python3 gen/check_release_candidate.py --stage schematic | PASS. ERC: 0 errors and 27 classified warnings; closure 1,569 pass/0 fail; electrical calculations 123 pass/0 fail; pin review 2,603 pass/0 fail; source identity pass. |
| Fresh XML netlist and isolated schematic-to-PCB ECO report | After U62/U64 correction: 0 missing refs, 0 extras, 0 footprint drift, 0 pad-net drift, 0 BOM/DNP drift. Its reference map collapses duplicates, so it cannot waive P1.2. |
| Duplicate reference scan | PASS: zero duplicate physical references after the reviewed candidate repair. |
| Read-only KiCad DRC with severity/parity/all-track reporting | FAIL: 1,404 violations (948 errors, 456 warnings), 499 unconnected items, and 199 parity observations. Principal categories: 203 mask bridges, 199 shorting-item findings, 199 courtyard overlaps, 156 clearances, 153 starved thermals, and 38 dangling track/via objects. These are in-progress routing findings, not accepted waivers. |
| J58 copied-board DRC after relocation | Original C1720 shorts/courtyard conflict removed; final DRC has no J58 or C1720 entry. |
| Read-only pcbnew stored-pour query | PASS: J58.2/J58.3/J58.4 are outside every GND stored polygon on F.Cu, In1.Cu, and In4.Cu. |
| git diff --check | PASS. |

## Required release holds before money is spent

1. Eliminate all remaining physical shorts, clearance/mask/thermal failures,
   parity observations, and unrouted fabrication connections.
2. Re-layout the critical power loops and C502/C503 without touching routed
   copper; reroute failed high-speed pairs on the defined stackup.
3. ~~Release stackup~~ — COMPLETED via P1.4. Release impedance coupons, exact BOM/AVL, battery thermal contract,
   trackpad retention/cable assembly, speakers, and direct-eDP harness.
4. Produce target firmware, programming/recovery proof, HIL, SI, thermal, RF,
   acoustic, mechanical, and manufacturing evidence.

Nothing here proves the assembled laptop will work. It proves a subset of schematic contracts and identifies the physical work and evidence required before fabrication or power-up.

## Post-audit corrective-action addendum — 2026-07-27

### Closed P0.1 — stale GND zone fill at the relocated J58 lands

The stored-pour finding above was confirmed, then corrected without regenerating the live PCB or altering non-zone board content. The pre-change snapshot is [ducktop2.kicad_pcb](../.local/pcb_snapshots/20260727_j58_zone_refill_prechange/ducktop2.kicad_pcb), SHA-256 `59eb2802432aecb4de8b5fbccc70a140cbeb4cc4a9f216b51e67a4acece404fb`.

First, a full `kicad-cli pcb drc --refill-zones --save-board` run was made only in a disposable copy. That result was intentionally rejected because KiCad rewrote unrelated board text. `gen/merge_refilled_zone_blocks.py` then admitted only the five refilled top-level zone blocks into a candidate whose non-zone text was byte-identical to the snapshot. A second candidate-only `sync_main_pcb_from_netlist.py --refs J58` refreshed the moved-land silk marker; the final comparison again proved all non-zone, non-J58 text byte-identical.

Before installation, pcbnew queried the actual candidate zone polygons: J58.2
(D-), J58.3 (D+), and J58.4 (TPAD_5V) were all outside every GND polygon on
F.Cu, In1.Cu, and In4.Cu, and the zones reported `NeedRefill=False`.
Project-name DRC found 1,407 violations, 499 unrouted items, and zero J58
findings. The corrected candidate was then installed. At that point, the final
C283 metadata-only candidate removed its `10u` value mismatch; its full parity
DRC result was 1,374 violations, 499 unrouted items, and 202 remaining
schematic-parity issues. The then-installed-board DRC, with all-track reporting
enabled, found 1,405 violations, 499 unrouted items, and 202 schematic-parity
issues, again with no J58 or C1720 entry. The later duplicate-reference repair
supersedes those board-wide counts.

The then-installed PCB SHA-256 was
`687f6f6abcf3b4dec172facf89abfe0fbff241e1d6e3cadf8baa62c83078181a`; it had
1,173 footprint blocks, 4,552 tracks, 52 arcs, 860 vias, and five top-level
zones. A final ECO comparison was attempted only in a disposable copy; it
correctly refused the then-known duplicate targets `U170`, `U2004`, and
`U2014`, and its copied PCB SHA-256 remained identical. This closes P0.1 and
the earlier C1720 collision P0. It does not clear the P1 release holds listed
above. The later duplicate-reference addendum supersedes these transitional
board-wide counts.

### Corrected P2.2 — J58 hand-solder legend

The custom footprint now prints literal `J58` and moves the wire map clear of the four solder lands. Gerber inspection remains required, but the reviewed source no longer places `REF**` or its legend over the hand-solder pads.

### Closed P1.2 — duplicate physical-reference repair and targeted BOM update

The J58-corrected board, SHA-256
`687f6f6abcf3b4dec172facf89abfe0fbff241e1d6e3cadf8baa62c83078181a`,
was copied to `.local/pcb_snapshots/20260727_duplicate_refs_prechange/` before
any duplicate-reference repair. A hash-locked helper
[`gen/prune_known_duplicate_footprints.py`](../gen/prune_known_duplicate_footprints.py)
accepted only that baseline and removed exactly three stale footprint blocks:

- source-linked unrouted `U170` at `(185.405, 79.890)`; the routed legacy
  `U170` at `(259.500, 162.500)` was retained and relinked;
- source-linked `U2004` at `(25.938, 31.300)`; the routed legacy `U2004` at
  `(20.138, 35.450)` was retained and relinked; and
- pathless legacy `U2014` at `(69.000, 32.500)`; the source-linked `U2014` at
  `(201.195, 67.050)` was retained.

The helper removed only the duplicate U2004's isolated pad stubs, complete
`PD1_MUX_EN` loop, and `PD1_MUX_FLIP` spur through its tee. It preserved the
live U2000/R2006 trunk. A copied-project scoped sync then restored current
schematic paths/metadata to the retained blocks. The candidate had 1,170
footprints, 4,527 segments, 855 vias, and 52 arcs; it introduced no new
dangling track or via objects. Its DRC baseline was 1,405 violations, 499
unconnected items, and 199 parity observations. Those existing routing findings
remain open and are not waived by this correction.

The helper's documented policy is intentionally narrow rather than a general
automatic deduplicator. The permanent copied-project release gate now checks
top-level PCB footprint reference uniqueness before running its schematic
checks. It reports `PCB footprint references: unique` for the installed board.

Two missing trackpad capacitor orderable identities were also assigned without
a bulk heuristic: `C280` is Murata `GRM188R71E104KA01D` and `C283` is Murata
`GRM31CR71E106KA12L`. The latter is a 1206, 10 uF, 25 V X7R part per the
[manufacturer product record](https://www.murata.com/en-us/products/productdetail?partno=GRM31CR71E106KA12%23);
the former uses the matching existing 0603 100 nF Murata family
[datasheet](https://www.murata.com/en-eu/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno=GRM188R71E104KA01%23).
The copied-project inventory consequently falls from 372 to 370 procurement
gaps. It is not a complete AVL.

The then-current installed board SHA-256 was
`e1b4f590c8ee18abc3f8849530292c0c808833ee830b017f976ba5acd1a70dc9`.
The content change from the duplicate-repair board is the scoped C280/C283
metadata refresh; a later whitespace-only normalization cleared the modified
lines reported by `git diff --check`. Neither operation moved footprints,
changed routing, altered Edge.Cuts, or refilled zones.

The final all-track read-only DRC at that hash reported 1,403 violations (947
errors and 456 warnings), 499 unconnected items, and 199 parity observations.
The largest categories are 201 solder-mask bridges, 199 shorts, 199 courtyard
overlaps, 157 clearances, 153 starved thermals, and 38 dangling track/via
objects. These remain release-blocking routing/layout work.

No high-speed, power-loop, battery-temperature, C502/C503, or mechanical
retention finding was auto-fixed: the present placement/routing evidence does
not support a safe blind move. Those remain the P1 release holds stated above.

### Closed P1.3 — R250/R251 trackpad USB physical short and mask bridge

**Refs, pins, nets, and evidence.** The active internal-services generator
populates two 22 ohm series resistors: [R250](../gen/generate_internal_services_sheet.py#L68)
and [R251](../gen/generate_internal_services_sheet.py#L70). The design contract
requires the corresponding trackpad USB connections at
[R250.1/R251.2](../gen/verify_design_contracts.py#L1936). Before correction,
KiCad DRC reported R250.1 on `/TRACKPAD_USB_DP` physically overlapping R251.2
on `/Internal Services/TPAD_CONN_DM`, plus a solder-mask bridge. The nets must
remain separate for the USB 2.0 differential pair to function; see the
[USB-IF USB 2.0 Specification](https://www.usb.org/document-library/usb-20-specification).

**Actual versus required.** R251 was at `(179.3, 88.6)` with its pad 2
overlapping R250 pad 1. It required enough clearance that the two USB signals
and their mask openings were independent.

**Consequence.** The overlap shorted the D+ and D- paths, so the trackpad USB
link could not operate as intended and the pair could not be meaningfully
qualified.

**Correction and verification.** A hash-locked helper
[`gen/relocate_unrouted_r251.py`](../gen/relocate_unrouted_r251.py) first
proved R251 had no attached segment endpoints, then moved only R251 to
`(180.3, 90.3)`. A full refill was run only in a disposable project copy;
[`gen/merge_refilled_zone_blocks.py`](../gen/merge_refilled_zone_blocks.py)
admitted only its five top-level zone blocks into the candidate and proved its
non-zone text byte-identical. The installed board is
`25d06e11208187f597514f593d12ef28a139f637f6f02362e2592c7d4c6f4501`.
Its all-track DRC has no entry matching `TPAD_CONN`, `TRACKPAD_USB`, `J58`, or
`C1720`. The remaining global DRC count is not waived.

**Confidence and remaining information.** High confidence in removal of this
physical overlap: it is directly checked by the pad positions and final DRC.
USB enumeration, eye margin, cable assembly, and trackpad behavior remain
physical bring-up work.
