# Ducktop2 Enclosure and Internal Stack Design (rev 1)

Status: DESIGN PLAN — geometry derived from measured part envelopes in
`MECHANICAL_MEASUREMENTS_AND_GATES.md`. Everything marked PROVISIONAL or
TO MEASURE requires a physical part in hand before the chassis is frozen.

## 1. Coordinate frame

- Plan view: base/lid are X = width (left to right), Y = depth (rear to front).
  Rear edge = Y 0 (hinge edge, board top edge). Front edge = +Y.
- The mainboard occupies the rear 185 mm of the base, flush with the rear
  edge: board (0,0)-(358,185). Board Edge.Cuts is canonical; the chassis
  follows the board.
- All Z heights are measured from the bottom-cover inner floor, upward.

## 2. Envelope decision

Measured parts: board 358x185, panel 352x227, three 100x60 pouch cells,
keyboard PCB 273.5x80, trackpad 140x105, speakers 38x18.

The previously provisional 358x248 base **cannot** hold the three cells and
the 140x105 trackpad together with the 185-deep board (the gates doc already
flagged this). Geometry: the front strip of a 248-deep base is 63 mm, which
holds only one 60-deep cell row; the trackpad's 140 mm center width leaves
only ~200 mm of strip width, i.e. two cells; the third cell has no legal
home in 248 mm.

Working envelope (this design):

| Plane | Size |
|---|---|
| Base (outer) | **358 x 362 mm** |
| Lid (outer) | 358 x 248 mm (panel 352x227 + 3 mm sides / 10.5 mm rear) |

Base depth budget: 12 (rear hinge/service) + 185 (board) + 2 (cable gap) +
60 (battery band) + 2 (gap) + 93 (trackpad/speaker band) + 8 (front lip) = 362.

Alternatives considered: keep 248 deep and drop to a 2-cell pack, or use a
smaller trackpad. Neither was chosen; the 3-cell pack and the 140x105
trackpad are user-provided parts.

## 3. XY layout (base, plan view, Y rear-to-front)

| Zone | X (mm) | Y (mm) | Notes |
|---|---|---|---|
| Rear hinge/service strip | 0-358 | 0-12 | hinge brackets at corners; rear exhaust center |
| Mainboard | 0-358 | 0-185 | board is canonical |
| Radio daughterboard overhang | 2.5-122.5 | 185-222 | 120x40.5 DB PCB cantilevered from J2300; see Z-stack |
| Battery band | see cells | 187-247 | three 100x60 cells |
| Cell A | 5-105 | 187-247 | left |
| Cell B | 129-229 | 187-247 | center |
| Cell C | 253-353 | 187-247 | right |
| Trackpad (JOMAA) | 109-249 | 249-354 | front-center, flush in palmrest |
| Speaker L | 3-21 | 330-348 | 38x18, front-left corner |
| Speaker R | 337-355 | 330-348 | front-right corner |
| Front lip / palmrest | 0-358 | 354-362 | |

Weight balance note: A+C are ~150 mm outside the center; B is centered.
A/C pairs are symmetric left/right; total pack weight is centered within
+/-25 mm. The mainboard's heavy items (Mu+cooling at board x~70-260,
y~20-120) sit in the rear — final balance must be checked on the assembled
unit (measurement gate).

### 3.1 Battery band clearances

- The band starts at Y 187, i.e. 2 mm forward of the board's front edge;
  that gap carries the J58 trackpad solder-land cable and the keyboard FFC
  service loop.
- Radio DB (x 2.5-122.5, y 185-222) hangs over the band's left cell area.
  Cell A stays at Y 187-247 directly below it — permitted only with the
  Z-stack in section 4 (DB plane is above the cell plane).
- Cell swelling allowance: +1.0 mm per cell top; keep 1 mm air gap above
  every cell in Z.

## 4. Z-stack (bottom to top)

Heights marked PROVISIONAL (to measure):

| Layer | Height above floor | Notes |
|---|---|---|
| Bottom cover | 0 to +2.0 | 1.5-2.0 mm aluminum or PC/ABS; foot pads |
| Battery cells | +2.0 to +10.0 | cell thickness TBD (TO MEASURE) + 0.5 adhesive + 1.0 swell |
| Board bosses | +10.0 to +12.5 | M2.5 bosses at H10-H17, 2.5 mm standoff |
| Mainboard PCB | +12.5 to +14.1 | 1.6 mm FR4; solder side faces down |
| Low board components | up to +17 | passives, SOICs |
| Mu module + cooling stack | +14.1 to +31 | socket 8 mm + module ~6-8 mm + coldplate/TIM/blower (~12 mm class) — TO MEASURE |
| NVMe card (J10) | +14.1 to +17.5 | card ~3.4 mm on socket |
| Keyboard deck plate | +32 to +34 | floats over the cooling zone (allowed overlap per gates) |
| Keyboard keycap tops | +34 to +41 | plate + switch + cap stack |
| Top case / palmrest | +38 to +43 over front | trackpad sits in palmrest at ~+36, click travel below |

- The keyboard plate bridges the board zone and bolts to the top case; it
  must clear the tallest cooling item by >= 2 mm (measure on the real
  stack).
- The trackpad (105 deep) occupies the front band; it mounts on the
  palmrest with its USB-C plug facing the J58 lands at board (171.2, 130):
  cable runs rearward through the 2 mm gap band, retained in a chase (see
  retention gates — cable retention is NOT released).

### 4.1 Radio DB vs battery Z-fit

J2300 (board top, y 181.5) holds the DB PCB at board-top height
(+13.4 to +15.0). DB components face up; DB bottom is ~+15.0. Cell tops are
at +10.0 (plus 1.0 swell) => ~4 mm clearance. Fits. If the measured cell
thickness exceeds 9 mm, raise the board bosses to 3.5 mm or recess the DB
area floor 1.5 mm.

## 5. Hinge plan — Framework 13 Hinge Kit (2 hinges + screws)

PROVISIONAL until the physical kit is measured.

- **Axis**: at the base rear edge, Y = -2 (pivot just behind the rear wall),
  continuous left-to-right; hinges sit in the rear corners.
- **Base-side brackets**: keepouts 40 x 20 mm at (8, 0)-(48, 20) and
  (310, 0)-(350, 20) (existing floorplan keepouts retained). Each bracket
  fastens to the bottom cover with the kit screws (M2 class; count/size TO
  MEASURE). The bracket lies BELOW the board plane in that corner — the
  board corners at (8-48, 0-20) and (310-350, 0-20) must stay free of
  through-hole components and tall parts (currently: headphone jack J422
  starts at x=50 — clear; the right corner is clear).
- **Lid-side brackets**: mount into the lid back cover's bottom corners,
  mirroring the base keepouts at lid (8, 228)-(48, 248) and (310, 228)-(350, 248).
- **Sweep**: design max 135°. The rear exhaust (x 70-120, y 0-12) is
  center-mounted between the hinges; at angles >135° the lid starts shading
  the exhaust. (Framework 13 goes further, but it exhausts elsewhere.)
- **Cable corridor**: the direct-eDP cable exits the Mu's onboard 40-pin
  connector (module near board (181,45)) and runs rearward through the
  center gap between the hinges (x ~150-300 at y 0-12), folds over the rear
  wall, and enters the lid. Required: bend radius >= 5 mm through the full
  sweep, a service loop, and no contact with the hinge brackets at any
  angle — TO VERIFY on the rigged assembly (gate 2).

## 6. Case mounting

### 6.1 Mainboard

M2.5 x 4-6 mm flat-head screws through isolated NPTHs H10-H17 into bottom-
cover bosses. Canonical positions from `RETENTION_AND_MOUNTING_RELEASE.md`
(board is canonical). Boss design: 6 mm OD, 2.5 mm height, 0.5 mm radial
clearance around each NPTH; no copper within 1.5 mm of the boss land.

### 6.2 Modules

- Mu module: Wurth 9774055243R M2 standoffs H1 (238.3, 76.8), H2 (238.3, 13.2)
  — module M2 x 4 screws, torque <= 0.2 N*m (component max; production
  torque after sample fit).
- M.2 cards: M2 standoffs H3/H4 per the M.2 retention table.

### 6.3 Lid

- Panel mounts: adhesive + locating pins per B160QAN03.K mounting holes
  (positions TO MEASURE from the panel sample).
- Lid back cover: 1.5 mm, hinge bosses reinforced, eDP cable channel.
- Bezel: 3 mm sides / 10.5 mm top-bottom margins (provisional).

### 6.4 Cutouts (follow board Edge.Cuts + connector shells)

- Left edge: two USB-C receptacles at base Y 25 and 70 (board J22/J23).
- Right edge: USB-C at Y 135 (J11); Ethernet recess x 352.78-358, y 88-107,
  panel opening 17.98 x 9.69 mm around the JXD1-1022NL (jack body extends
  2.1 mm into the recess).
- Rear edge: headphone jack at x ~50 (J422), rear exhaust grille x 70-120.
- Front edge: no board connectors.
- Mic acoustic port: IM68A130 bottom-port at board (40,110) — sealed
  channel through the bottom cover, away from blower/inductor/PA noise.

## 7. New measurement gates (in addition to gates 1-10)

11. Framework 13 hinge kit: bracket geometry, screw size/count, pivot
    offset, torque, and closed/open geometry at 0/90/135°.
12. Cell thickness + tabs + swelling allowance (gates 3) — the 358x362
    envelope and the DB-over-cell Z-fit depend on it.
13. Assembled weight balance left/right (A+C vs B symmetry assumption).
14. Keyboard plate-to-cooling clearance (>= 2 mm) with the real blower/
    fin/heatpipe stack.
15. eDP cable length/route through the hinge at all angles (gate 2).
