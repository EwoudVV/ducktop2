# center PCIe layout

keep the data and clock pairs together. the center board uses the widths and
gaps from [the stackup](mainboard_stackup_release.json): 0.183 / 0.1524 mm on
F.Cu and B.Cu, and 0.114 / 0.1524 mm on In2.Cu. In1.Cu, In3.Cu and In6.Cu are
ground references. signal tracks stay off those ground layers.

TX capacitors sit near the M.2 sockets. the complete path check follows both
sides of each capacitor, and both sides of the clock resistors. data P/N
mismatch must stay below 0.127 mm; clock mismatch must stay below 0.381 mm.
each capacitor-to-socket path also stays below 8 mm, including a conservative
full-board thickness for its through via. these limits follow the
[Mu PCIe guide](https://docs.lattepanda.com/content/mu_edition/design_guide_pcie/).

## local gaps

pads, vias and length tuning briefly spread the pairs apart. their named
windows and limits are in [center_pcie_layout_limits.json](center_pcie_layout_limits.json).
each window has a fixed layer, exact pair name, maximum gap, total copper
length and uncoupled length for P and N. moving the route outside a window
makes the nominal gap apply again.

the two NVMe clock tuning windows contain about 2.77 mm of uncoupled copper
on the longer leg. the other NVMe via and socket windows are about 2.18 mm or
less per leg. the checker records every window separately so those lengths
stay visible when the layout changes. ordinary paired corners are checked
against their actual bend angle and two matching offset legs.

the Wi-Fi receive and source-clock turns use concentric arcs. its capacitor
outputs join a coupled section before the final via fanout. the complete
capacitor-to-socket paths, including nominal via depth, are 6.27 mm and
7.84 mm. the NVMe paths are 4.13 to 4.71 mm. all 12 data and clock signals
pass their complete P/N path limits.

the same check covers the existing GbE and TCP0 escapes at A1 and FPC103.
the fixed limits contain 57 NVMe windows, 30 Wi-Fi windows, 9 GbE windows
and 12 TCP0 windows. the FPC103 pads and vias account for much of each
short escape; the exposed uncoupled copper is at most 1.362 mm on GbE
and 0.895 mm on TCP0. the full copper length stays checked too.

KiCad applies an area condition to a whole track object. a long track can
cross a small tuning window, so the native local rules also need the geometry
check. it clips each track or arc to the actual window and checks all the
remaining copper. a 2 mm local window cannot permit an 8 mm gap error further
along the same track. the regression tests include that exact case.

arcs use KiCad's native center, radius and sweep. clipping and uncoupled
lengths are calculated from line and circle intersections. the maximum-gap
samples are at most 0.005 mm apart, giving a conservative 0.0025 mm error
bound. KiCad can round arc centers to 100 nm; each arc's measured center
rounding is recorded and limited to 0.15 micrometre of gap uncertainty.
straight-to-straight checks keep their 2 nm coordinate tolerance.

these local rules keep the normal minimum gap, width, clearance, drill and
layer checks. the full release gate still requires native DRC, correct pad
endpoints, complete signal paths, matching P/N lengths and no duplicate
copper or free branch stubs. geometry gives a repeatable layout check;
signal quality still needs to be checked on the assembled board.

## running the check

install `gen/requirements-release.txt` into the Python environment used for
release checks. KiCad's Python is found separately, or can be selected with
`KICAD_PYTHON`.

```sh
python gen/check_center_pcie_coupling.py \
  --pcb ducktop2-center.kicad_pcb \
  --limits manufacturing/center_pcie_layout_limits.json \
  --output /tmp/center-pcie-layout-check.json
```

the routing and fabrication release commands run this check automatically.
it reads the PCB passed on the command line and leaves that file untouched.
a missing dependency, failed export or failed geometry check blocks the gate.

KiCad's [custom-rule documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#custom-design-rules)
explains area matching and differential-pair gap checks. its
[arc-center implementation](https://gitlab.com/kicad/code/kicad/-/raw/10.0/libs/kimath/src/trigo.cpp)
documents the coordinate rounding used here. the short fanout approach also
follows [TI's high-speed layout guidance](https://www.ti.com/lit/an/spraar7j/spraar7j.pdf).
