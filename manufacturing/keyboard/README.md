# keyboard fabrication and assembly files

this package comes from the saved keyboard board and a fresh schematic
netlist. the manifest binds the source, staged board, checks and output files.
run `python3 gen/generate_keyboard_jlcpcb_package.py --verify-package manufacturing/keyboard`
before using a retained package. a source edit makes the old package stale.

to regenerate, install `shapely==2.1.2` and `gerbonara==1.6.3` in a Python
virtual environment, then run `python gen/generate_keyboard_jlcpcb_package.py
--output manufacturing/keyboard --replace` from the project root. KiCad 10
CLI and an interpreter with `pcbnew` are also required; use `--kicad-cli`
and `--kicad-python` if automatic discovery cannot find them. replacement
keeps the previous output as a sibling backup after the new checks pass.

- 273.5 x 80.0 mm, two copper layers, 0.8 mm FR-4.
- 65 CHERRY MX6C-T3NB switches, 65 JSCJ 1N4148WS diodes and one Hirose FH12-30S-0.5SH(55).
- `keyboard_GERBERS.zip` is the bare-board fabrication archive.
- `factory_BOM.csv` and `factory_CPL.csv` contain 66 placements. `complete_BOM.csv` contains all 131 parts. `switches_CPL.csv` contains the 65 later switch placements.
- `paste/factory/` excludes every switch land. `paste/switches/` contains 455 switch apertures, including all 325 fixation lands. the aperture and locating-hole CSVs use PCB coordinates with positive Y down. CPL Y follows the negative-Y KiCad export convention and shares the Gerber origin.

CHERRY VS-10107 revision 03, PCB-MX-ULP defines the contact exclusion used by
the public checker: local X -5.05 to -1.25 mm, local Y 2.20 to 4.20 mm. the
footprint's rule area prohibits tracks, vias, pads and filled copper on both
copper layers. the checker inspects native copper and the plotted Gerbers.

CHERRY VR00101_D specifies a lead-free process. its example uses a nitrogen
oven, gold-finished FR-4 and a 240 C maximum measured PCB-top temperature.
the classification table lists 217 C liquidus, at most 70 seconds above
liquidus, a 245 C recommended package peak and a 260 C absolute package peak.
follow the complete supplier process document and measure the actual profile.
stencil thickness, aperture reduction, finish and assembly fixtures still
need supplier review and a switch coupon. this package does not qualify a
hot plate process or a particular factory service.

review diode cathodes at pad 1, the connector opening and bottom contact,
the empty switch population in factory assembly, and the supplied separate
paste layers before ordering. no order or physical assembly test is recorded.

fabrication archive files:

- 12_keyboard_daughterboard-B_Cu.gbl
- 12_keyboard_daughterboard-B_Mask.gbs
- 12_keyboard_daughterboard-B_Silkscreen.gbo
- 12_keyboard_daughterboard-Edge_Cuts.gm1
- 12_keyboard_daughterboard-F_Cu.gtl
- 12_keyboard_daughterboard-F_Mask.gts
- 12_keyboard_daughterboard-F_Silkscreen.gto
- 12_keyboard_daughterboard-NPTH.drl
- 12_keyboard_daughterboard-PTH.drl
- 12_keyboard_daughterboard-job.gbrjob
