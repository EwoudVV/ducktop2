# power revision

4 october 2026. the BMS routing is finished. the 100 W main-board work still
needs routing and hardware tests, so the complete laptop is not ready to order.

the BMS now uses a BQ76922 high-side circuit,
independent signed current guards and a limited startup branch. the target
is 8 A discharge and 3 A charging. the 80 mm board fits a wider center
cutout with the same 1.5 mm gaps. both outlines and the moved center support
are saved. the BMS has zero native unconnected items and zero physical DRC
findings with the fabrication checks enabled.

the 100 W main-board revisions use the revised connector footprints and
pin maps. the main power links use WAGO 2060
spring terminals. the protected BMS pair uses the two-pole version, and
the replacement BMS raw input uses another two-pole WAGO, with separate
JST GH cell taps. F1 is a 10 A Schurter HCF fuse in that revision. Alpha 6715 is specified for the
18 AWG links and Alpha 6716 for the 16 AWG direct USB5 loom.

the [layout report](../../verification/bms-layout.md) covers the new board,
its filled power paths, isolated returns, footprints and assembly checks.
the main boards remain unfinished. obsolete power
tracks and 28 incorrectly assigned MCU escape stubs have been removed.
the existing PCIe and clock routing is preserved.

the ISL9241 charger, TPS552882 Mu supply, input switches and always-on power
changes are now in the saved main-board schematics and PCBs as well as the
generators and firmware. the first power placement pass covers 185 center
parts and 14 parts on each I/O board. it includes a dedicated land pattern
for the CSD17577Q3A FETs, shorter bootstrap and gate-drive connections, and
small support parts on the back. the broader MCU, audio and port placement
pass is also saved. repairs to existing main-board routes are in progress;
most of the board is still unrouted.

the center pass moved 230 existing footprints and added C2685 beside the
selector's V2 input. the MCU clocks and bypasses, codec, microphone,
headphone stage, maker flash and radio interface now follow their actual
connections. C427 sits at the codec's VDDI output, and the selector INTVCC
capacitors are less than 0.8 mm from their pins. the programming voltage-sense
link stays on the front, clear of the Tag-Connect area.

C29/C30 use documented 2.2 uF, 16 V X7R parts in the same 0805 footprints.
C740/C749 keep 100 nF and use the documented 50 V parts already used on
the board. these choices support short underside connections. the center
matches all 868 schematic parts and 3,372 numbered pads, with no physical
DRC errors involving moved or added parts. its 330 remaining physical DRC
errors and 1,816 unconnected items belong to the unfinished routing work.
all 698 reviewed PCIe, clock and associated control routing objects are
preserved. 75 obsolete copper objects are removed with an exact record.

the left and right placement pass is saved. 172 left footprints and 38 right
footprints were moved, including the five added local bypass capacitors.
the USB protection now follows its own connector, the hub and Ethernet
bypasses sit near their supply pins, and the power selector has a shorter
shared-source path. 121 parts moved to the back. each has a checked maximum
body height of 1.8 mm or less, with a separate 0.3 mm assembly allowance.
the case still needs checking against those positions and heights.

both I/O boards have zero physical DRC errors and match their schematics.
the left keeps all its existing copper. the right removes seven obsolete
crystal segments and adds one short ground connection and via for U2014.
its missing In3/In6 ground pours are now present. the remaining unconnected
counts are 948 left and 331 right, so neither board is ready to order.
library warnings and a few existing right-board dangling items remain.

standby power now uses the system rail for its battery feed, so that current
passes through the charger's discharge shunt. an LTC4231 adds active current
limiting and a deliberate reset after a persistent fault. the startup and
fault calculations still depend on measured load, capacitor and temperature
limits. the Mu output uses two 16 milliohm shunts in parallel, and its firmware
budget is now 60 W for the module and display, leaving room for the fan.
the calculations now include charger current-sense error, precharge, voltage
tolerance and repeated standby faults. the firmware only uses the guaranteed
lower input-current bound for its available-power budget. these are design
checks; the real current, startup, temperature and transient tests remain.

both official PD exports now include the 20 V / 5 A sink setting. their register
data, binaries, C arrays and archives pass the updated checks and 23 configuration
tests. the firmware host tests, ARM build and linked-image checks pass. no hardware
has been programmed or tested, and the qualification flags remain off. this
firmware belongs to the revised power circuit, not the previous board.

the integrated schematic ERC checks have zero errors, with warnings
remaining. schematic-to-board comparisons pass for the saved power revision.
the firmware host suite passes all 34 CMake tests, and the ARM build and
linked-image checks pass. all 63 hardware test rows remain NOT_RUN. the
main center board still has existing routing and clearance errors, so these
results are not a routing or fabrication approval.

the case study contains the mounting schedule, Framework hinge supports,
keyboard and trackpad supports, battery trays, lid, cooling reservations,
STEP/STL exports and an interactive viewer. its exports still use the
previous PCB snapshots. the 35 mm study has unresolved harness conflicts;
the final thickness is still undecided. the saved connector placements now
have [proposed wire paths and service requirements](power-harness-fit.md).
raw-pack lead measurements, clamps and the complete assembly check remain.

the BMS prototype uses CSS4J-4026K-2L00F, 2 milliohms, with separate
force and sense contacts. the first assembly keeps its drive-release links
open for fixture tests.
