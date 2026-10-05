# bms prototype files

this package contains checked files for an unarmed BQ76922 prototype. source hashes,
checks and output hashes are recorded in `manifest.json` and `SHA256SUMS.txt`.
factory review and physical qualification are pending. no order has been
submitted, and this is not an operating release.

## uploads

- `bms_GERBERS.zip`: all four copper layers, masks, printing, routed outline,
  and separate plated and unplated drill files.
- `BOM.csv`: 168 fitted parts, grouped into 74 part numbers.
- `CPL.csv`: 168 SMT placements, 54 on top and 114 underneath.
- `through-hole-positions.csv`: header-only file; no through-hole assembly parts.
- `not-fitted.csv`: DNP links, bare test points and offboard cell probes.
- `paste/`: top and bottom stencil artwork. review stencil thickness and
  power-FET aperture windows before assembly. do not fit the DNP links.
- `bms.ipc`: electrical test netlist, with 847 records and 99 nets.
- `assembly/`: both assembly drawings and the test-point map.
- `previews/`: rendered Gerbers for inspection; Gerbers control fabrication.

the CPL uses millimetres, the Gerber absolute origin, positive X right and
positive Y up. bottom X is not mirrored. rotations follow KiCad. check pin 1
and polarity against the assembly drawings. the bottom drawing is viewed
from underneath; that view is separate from the CPL coordinate convention.

## board settings

| setting | value |
| --- | --- |
| outline | 80.000 x 36.148 mm, routed contour |
| layers, top to bottom | F.Cu, In1.Cu, In2.Cu, B.Cu |
| material and nominal thickness | standard FR-4, 1.6 mm |
| copper | 1 oz on all four layers, including the inner layers |
| finish | ENIG |
| mask and printing | green mask, white printing on both sides |
| smallest track | 0.10 mm |
| smallest via hole / land | 0.20 / 0.50 mm |
| via annular ring | at least 0.15 mm |
| vias | through vias; see the exposed-pad note for U719 |
| filled or capped vias | see the exposed-pad review below |
| impedance control | not requested |
| electrical test | flying probe against the supplied IPC-D-356 netlist |

the four support holes are unplated circular cutouts in Edge.Cuts. retain
all outline cutouts and all holes in the supplied drill files. the dielectric
entries are indicative, not a custom impedance stackup. quote a standard
1.6 mm build with 1 oz copper on every layer. the design basis is 35 um
copper and 20 um barrel plating. confirm the finished copper and minimum
hole plating; report lower guaranteed thickness for review.

## assembly and programming

the BQ76922's single 0.2 mm exposed-pad ground via is open within the
bottom pad's mask opening. its front face is tented, and nominal paste
does not overlap the hole. the paste edge has no registration margin at
that location. confirm front-tent closure, stencil alignment and the
solder-wicking/voiding process before assembly; quote filling or plugging
if that process cannot be qualified. this is the only intentional
PCB-via mask opening. its measured geometry is in
`checks/export-check.json`. the [TI package notes](https://www.ti.com/lit/ds/symlink/bq76922.pdf)
cover thermal-pad soldering and via treatment.


fit the exact BOM, including the precision thermal resistors and shunt.
substitutions need review. U719 is BQ76922RSNR. RS11 is Bourns CSS4J-4026K-2L00F,
2 milliohms, 1%, 6 W, with a 2.93 mm maximum body height. F1 is the
soldered SCHURTER 3-101-051 10 A fuse. J2 and J2072 are SMT WAGO
2060-452/998-404 terminals. solder both lands for every terminal contact.
J2 pin 1 is raw negative and pin 2 is raw positive; follow the top-side
polarity marks. all five cable connectors are on top. keep their edge-facing
wire exits, plug withdrawal and terminal-button access clear.

leave R870, R871 and R872 unpopulated. these are the CHG, DSG and PDSG
gate-drive release links. do not bridge them, fit substitutes, or treat
bare pads as completed assembly. every test point is exposed copper.
TH2201, TH2202 and TH2203 are insulated probes fitted to the cells later;
they are offboard and are not parts for PCB assembly.

there is no permanent MCU on this board. the BQ76922 needs a per-unit
configuration image in its one-time-programmable memory. the supplied
`programming/profile-template.json` is a prototype template, not a released
programming image. capture the actual unit's factory trims before any RAM
or OTP write. prepare and calibrate that unit's image, test it in RAM with
simulated cells and faults, and record the image hash, checksum and I2C CRC
readback. programming, OTP burn and release-link fitting need a separate
fixture release. this exporter performs none of those actions.

read back the complete approved image with CRC after programming and after
repeated cold starts. prove autonomous startup, protection timing, the
latched startup path, regulator headroom, harness integrity, cell limits,
current transfer and all three thermal windows before fitting any release
link. the EC's expected image must match the unit's programmed bytes; load
its matching firmware image and record that image hash too. the EC runtime
does not program OTP, configure the monitor or enable the FETs automatically.
all operating and calibration qualification flags remain false. recovery
charging remains disabled.

the fitted SMT count is 516 copper lands. stencil windows within a
land are not extra components. there are 0 soldered through holes,
excluding vias and locating holes. inspect the power-FET joints and use
lead-free assembly with component-appropriate reflow profiles.
the 15 plated holes within SMT footprints are thermal features,
not through-hole component placements.

keep PACK_NEG_RAW, FG_VSS and CTRL_GND separate. use insulating board
supports. batteries, probe wiring and mating cable harnesses are not
included in the PCB assembly. powered protection tests start with simulated
cells and the release links absent.

PCBWay can propose process rails and fiducials. send the panel drawing for
review without changing the finished outline, support holes or component
positions. return the unused bare boards.

## quantity and quote

compare five bare PCBs with one assembled against five bare PCBs with two
assembled. keep the stackup, parts and shipping choices identical. one is
enough to start testing; two gives me a spare. the quote needs the parts,
assembly setup, attrition, shipping and tax. no total or order is confirmed.

check sourced parts, availability, placement preview, finished copper,
hole plating and proposed panel changes before payment. the design targets
8 A discharge and at most 3 A charge; these are unqualified allocations.
a 10 A fuse does not establish a safe pack operating limit.

## checks and regeneration

both saved and refilled boards passed the full native zero-airwire gate,
complete schematic parity, library pad/drill checks and 0.10 mm fabrication
checks. this package records 608 physical pad objects, including
567 electrical pads and 41 non-electrical paste/mask objects.
all four plotted copper layers match native geometry within the 2 um
boundary allowance. drill coordinates match their 1 um export grid. mask
openings expose no unintended via holes, including the 0.05 mm outward-margin
screen around SMT openings. the intentional U719 exposed-pad opening is
recorded separately with its required assembly review. paste stays on pads.
confirm factory mask and stencil registration.

physical DRC errors and warnings are zero. only literal footprint-name
filter messages for the reviewed fuse and WAGO connectors are allowed;
exact parts, library geometry and pad assignments are checked separately.
ERC errors are zero. any accepted raw-ground naming warnings are recorded
with their exact pins in the manifest. `checks/layout-checks.json` is the
source-bound power-path evidence. none of these checks enables operation.

install `gen/requirements-bms-fabrication.txt` in a local virtual environment.
run `python gen/generate_bms_pcbway_package.py --output NEW_PACKAGE --work
NEW_SCRATCH_DIRECTORY` from the project root after the finished canonical
board is promoted and its layout evidence and assembly drawings are refreshed.
keep both paths in this project and keep an old package until its replacement
passes. verify a retained package with
`python gen/generate_bms_pcbway_package.py --output manufacturing/bms/pcbway --verify`.
any source edit makes the retained package stale.

## supplier references

- [PCBWay fabrication limits](https://www.pcbway.com/capabilities.html)
- [PCBWay assembly files](https://www.pcbway.com/assembly-file-requirements.html)
- [PCBWay assembly quantities](https://www.pcbway.com/blog/PCB_Basic_Information/PCBWay_Q_A_003___Common_Questions_for_PCBA_Ordering_01.html)
- [Bourns CSS4J-4026](https://www.bourns.com/docs/product-datasheets/css4j-4026.pdf)
- [TI BQ76922](https://www.ti.com/lit/ds/symlink/bq76922.pdf)
- [SCHURTER HCF fuse](https://www.schurter.com/en/datasheet/typ_HCF.pdf)
- [WAGO 2060-452](https://www.wago.com/2060-452/998-404)
