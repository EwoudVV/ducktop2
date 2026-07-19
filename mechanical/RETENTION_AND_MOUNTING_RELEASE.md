# Ducktop2 Retention and Mainboard Mounting Contract

Date: 2026-07-18

This document controls the PCB-side mechanical features for the LattePanda Mu,
the two M.2 cards, and the mainboard-to-chassis interface. It does not release
the enclosure or authorize fabrication by itself.

## LattePanda Mu Retention

The Mu uses a 260-pin DDR4 SO-DIMM-style edge connector, but the connector is
not the complete retention system. The socket provides the electrical contact
and insertion latch; two M2 screws and standoffs carry shock, vibration, and
long-term bending loads.

- Host socket: TE Connectivity `2309411-1`, standard orientation, 8.0 mm.
- Module support height: 5.5 mm above the carrier PCB, tolerance +/-0.1 mm.
- PCB hardware: two Wurth Elektronik `9774055243R` WA-SMSI steel SMT spacers,
  M2 internal thread, 4.35 mm outside diameter, and 5.5 +/-0.1 mm height.
- PCB geometry: exact 5.3 mm solder land and 3.0 mm non-plated locating hole
  from the Wurth drawing, implemented by
  `ducktop2:Wurth_9774055243R_M2_H5.5`.
- 3D model: `ducktop2.3dshapes/Wurth_9774055243R.step`, verified to resolve in
  a KiCad board render.
- Candidate mating screw: RS PRO `914-1462`, M2 x 4 mm DIN 7985 A2 stainless.
  Confirm thread engagement, head clearance, and sample fit before release.
- Maximum spacer torque: 0.2 N*m per Wurth. This is a component maximum, not a
  production assembly torque; the latter remains to be established by sample
  fit and assembler approval.
- Board references: `H1`, `H2`.
- Electrical treatment: both standoffs connect to `GND`, matching the official
  reference carrier.

The module must not be operated with only the SO-DIMM socket clips as the
structural restraint.

## M.2 Retention

Both 4.2 mm-high Amphenol sockets use a 2.5 mm-high grounded M2 standoff so the
card remains parallel to the board after it is screwed down.

| Card | Socket | Retainer | Card format | Standoff center (mm) |
|---|---|---|---|---|
| NVMe | `J10`, MDT420M01001 | `H3` | M-key 2280 | 279.975, 116.000 |
| Wi-Fi | `J40`, MDT420E01001 | `H4` | E-key 2230 | 285.250, 179.050 |

The PCB footprint and sourcing identity now match the official Mu Lite Carrier
V2 at commit `f954bf0275fa0aec4c1e9eb168f09644563b28a4`:

- Source designation: `M2XC4X2.5+C2.7X1.5`.
- Supplier listing: Taobao item `655855111684`, SKU `4725777108077`.
- Hardware: unbranded lead-free copper SMT nut/standoff, M2 internal thread,
  4 mm body, 2.5 mm support height, and 2.7 x 1.5 mm locating tail.
- Footprint: 2.75 mm drill and 5.0 mm top solder land, matching the official
  LattePanda V2 PCB.

Amphenol `MDT420STD001` was checked and rejected for this footprint. Its drawing
specifies an M3 thread, 4.2 mm PCB hole, and solder area out to 7.0 mm, so it is
not interchangeable with `H3` or `H4`.

## Mainboard Chassis Mounting

Eight isolated 2.7 mm NPTHs accept M2.5 chassis screws. They intentionally have
no copper connection; a deliberate chassis-bond point will be defined
separately after the enclosure material and EMC strategy are frozen.

| Ref | X (mm) | Y (mm) |
|---|---:|---:|
| `H10` | 20.000 | 28.000 |
| `H11` | 110.000 | 10.000 |
| `H12` | 180.000 | 10.000 |
| `H13` | 20.000 | 115.000 |
| `H14` | 120.000 | 70.000 |
| `H15` | 240.000 | 70.000 |
| `H16` | 342.000 | 120.000 |
| `H17` | 300.000 | 175.000 |

This pattern supports the long 358 x 185 mm board near its ends, center, side
connectors, Mu/cooling area, and M.2 area without placing bosses inside the
battery, trackpad, hinge, antenna, or cooling envelopes.

## Assembly Sequence

1. Inspect the mainboard NPTHs and the soldered standoff joints before fitting
   modules.
2. Fasten the bare mainboard to flat chassis bosses through `H10`-`H17`; verify
   the board is not bowed.
3. Insert the Mu at the socket's specified angle, press it flat, then install
   both M2 fasteners at `H1` and `H2`.
4. Insert the M.2 cards, press each card parallel to the board, and install the
   retaining screw at `H3` or `H4`.
5. Verify connector engagement, module clearance, card flatness, and cold-plate
   contact before powering the first article.

Do not use the Wurth 0.2 N*m component maximum as the production torque. Thread
engagement, screw-head clearance, washer choice, thread-locking method, and a
lower production torque must be approved as one assembly stack.

## DRC Interpretation

The mechanical ECO adds exactly four DRC reports:

- `H1` courtyard overlaps `A1` and its NPTH lies inside the `A1` courtyard.
- `H2` courtyard overlaps `A1` and its NPTH lies inside the `A1` courtyard.

These are intentional 2D reports: `H1` and `H2` are coaxial with the Mu module
mounting holes and sit below the module. They are not copper shorts or accidental
component collisions. Keep them as documented waivers; do not delete either
courtyard to make the count look cleaner.

## Evidence and Remaining Release Gates

- Validation summary:
  `verification/MECHANICAL_RETENTION_VALIDATION_2026-07-18.md`
- Mechanical ECO script: `gen/apply_mechanical_retention_eco.py`
- Exact-hardware ECO script: `gen/apply_mu_standoff_release_eco.py`
- Schematic/PCB reference, footprint, and pad-net drift: zero.
- Existing footprints preserved byte-for-byte except the deliberately moved
  `C26`, `J10`, `J40`, and `J54`; twelve retention/mount references were added.

The raw pre-ECO board snapshots and DRC JSON files are retained in the local,
ignored archive rather than published as duplicate working boards. The scripts,
current board, and concise validation summary remain in the repository.

Still required before mechanical release:

1. Purchase samples of the TE socket, both M.2 sockets, Wurth spacers, and RS
   PRO screw candidate.
2. Confirm the assembler can place/reflow the soldered standoffs and approves
   the paste apertures, locating-tail drill, body material, and finish.
3. Freeze chassis boss height, boss diameter, fastener length, thread
   engagement, torque, washers, and service-removal method.
4. Check the first article with physical Mu, SSD, Wi-Fi card, cold plate, heat
   pipe, keyboard, trackpad, batteries, cables, and enclosure.
5. Run fit, bow, connector-engagement, thermal-cycle, vibration, and drop tests.

## Primary References

- LattePanda Mu edge-connector design guide:
  https://docs.lattepanda.com/content/mu_edition/design_guide_edge_connector/
- LattePanda Mu FAQ:
  https://docs.lattepanda.com/content/mu_edition/faq/
- Amphenol MDT420 M.2 connector drawing:
  https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/mdtxxxxxx001.pdf
- Official LattePanda M.2 standoff source listing:
  https://item.taobao.com/item.htm?id=655855111684&skuId=4725777108077
- LattePanda Mu official hardware repository:
  https://github.com/LattePandaTeam/LattePanda-Mu
- Wurth 9774055243R product page and drawing:
  https://www.we-online.com/en/components/products/SMSI_SMT_STEEL_SPACER_M2_THREAD_INTERNAL
  https://www.we-online.com/components/products/datasheet/9774055243R.pdf
- RS PRO 914-1462 M2 x 4 mm screw datasheet:
  https://us.rs-online.com/m/d/ccfed953c22f2a7df2b0ba2c0124154e.pdf
