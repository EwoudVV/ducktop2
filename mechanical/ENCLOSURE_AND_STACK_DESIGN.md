# Ducktop2 Enclosure and Internal Stack Design (rev 2)

Status: DESIGN PLAN — geometry derived from measured part envelopes in
`MECHANICAL_MEASUREMENTS_AND_GATES.md`. Everything marked PROVISIONAL or
TO MEASURE requires a physical part in hand before the chassis is frozen.

Rev 2 change (2026-08-13): rev 1 serialized the battery band and the
trackpad into two front-to-back bands, producing a 362 mm-deep base. That
was wrong. The trackpad rides at palmrest height ABOVE the battery row
(standard practice: a stiffener plate between them, click travel and cell
swelling kept apart). With the overlap handled in Z, the original
**358 x 248 mm** envelope fits everything.

## 1. Coordinate frame

- Plan view: X = width (left to right), Y = depth (rear to front).
  Rear edge = Y 0 (hinge edge, board top edge). Front edge = +Y.
- Mainboard (358 x 185) occupies the rear 185 mm of the base, flush with
  the rear edge. Board Edge.Cuts is canonical; the chassis follows it.
- Z is measured up from the bottom-cover inner floor.

## 2. Envelope

| Plane | Size |
|---|---|
| Base (outer) | **358 x 248 mm** |
| Lid (outer) | **358 x 248 mm** |

Base depth budget: 185 (board) + 3 (cable gap) + 60 (battery row) = 248.
The trackpad shares the front band's XY footprint at a higher Z.

## 3. XY layout (base, plan view)

| Zone | X (mm) | Y (mm) | Notes |
|---|---|---|---|
| Rear hinge/service strip | 0-358 | 0-12 | hinge brackets at corners; rear exhaust center |
| Mainboard | 0-358 | 0-185 | canonical |
| Radio DB overhang | 2.5-122.5 | 185-222 | 120x40.5 DB PCB from J2300, at board height (see Z) |
| Cable gap band | 0-358 | 185-188 | pack harness + J58/J310 service loops |
| Battery row | 0-358 | 188-248 | three 100x60 cells, one row |
| Cell A | 5-105 | 188-248 | left |
| Cell B | 129-229 | 188-248 | center |
| Cell C | 253-353 | 188-248 | right |
| Trackpad (JOMAA) | 109-249 | 143-248 | front-center, at palmrest height, ABOVE the battery row and the board's front-edge strip |
| Speaker L | 3-21 | 205-243 | front-left corner |
| Speaker R | 337-355 | 205-243 | front-right corner |

- The trackpad's XY overlaps the board strip Y 143-185 (board's front edge)
  and the battery row Y 188-248. Both overlaps are resolved in Z (section 4).
- Board parts inside the trackpad shadow (U421/U425 audio cluster at
  (140-152, 158-165), low passives) top out around Z +7 - fine.
- **SW4 (BOOT0 pinhole switch) was moved on the board to (249, 171)** so
  it clears the trackpad's right edge; the chassis pinhole goes in the top
  case beside the trackpad (X 249-252, Y 168-174).
- Weight: cells A/C balance left/right; cell B centered. Verify on the
  assembled unit (gate 13).

## 4. Z-stack (bottom to top)

All heights PROVISIONAL (to measure):

| Layer | Z (mm) | Notes |
|---|---|---|
| Bottom cover | 0 .. +2 | 1.5-2.0 mm aluminum or PC/ABS + feet |
| Battery cells | +2 .. +11 | cell thickness TBD (TO MEASURE) + 1.0 swell + 0.5 adhesive |
| Palmrest support plate | +11 .. +13 | stiffener over the battery row; carries trackpad mounts; vented |
| Mainboard bosses | +0.5 .. +2.5 | M2.5 bosses at H10-H17 |
| Mainboard PCB | +2.5 .. +4.1 | 1.6 mm FR4 |
| Board low components | +4.1 .. +7 | passives, SOICs |
| Mu module + cooling | +4.1 .. +21 | socket 8 mm + module ~6 mm + coldplate/TIM (TO MEASURE) |
| NVMe card (J10) | +4.1 .. +7.5 | |
| Keyboard deck plate | +23 .. +32 | floats over the cooling zone (allowed overlap), >= 2 mm over the tallest cooling item |
| Keyboard caps (MX ULP) | +28 .. +33 | plate + switch + cap (TO MEASURE) |
| Trackpad mechanism | +20 .. +38 | clicks/haptics ride ABOVE the plate; surface flush with the top case |
| Top case / palmrest | +38 .. +41 | keyboard + trackpad both flush into it |

Rules:
- Trackpad bottom (+20) clears the board strip parts (+7) by 13 mm and the
  cell tops (+11) by 9 mm; the support plate separates click loads from the
  cells entirely. No part of the click mechanism may bear on a cell.
- The radio DB overhang (bottom ~+15) clears the cells (+11 incl. swell) by
  ~4 mm. If measured cell thickness exceeds 9 mm, raise the board bosses to
  3.5 mm or recess the DB-area floor (see section 4.1, rev 1).
- The deck plane (+38..41) is set by the keyboard stack over the Mu/cooling
  and the trackpad thickness. Total base thickness ~41-43 mm + feet —
  chunky by thin-laptop standards; thinning requires changing the Mu socket
  height or the cooling stack (flagged, not resolved).

## 5. Hinge plan — Framework 13 Hinge Kit (2 hinges + screws)

PROVISIONAL until the physical kit is measured.

- **Axis**: base rear edge, Y = -2 (pivot just behind the rear wall),
  continuous left-to-right; hinges in the rear corners.
- **Base-side brackets**: keepouts 40 x 20 mm at (8, 0)-(48, 20) and
  (310, 0)-(350, 20), fastened to the bottom cover with the kit screws
  (M2 class; count/size TO MEASURE). Board corners there are free of
  through-hole/tall parts (headphone jack J422 starts at x=50).
- **Lid-side brackets**: mirror keepouts at lid (8, 228)-(48, 248) and
  (310, 228)-(350, 248).
- **Sweep**: design max 135°. The rear exhaust (x 70-120, y 0-12) is
  center-mounted between the hinges; beyond 135° the lid shades it.
- **eDP corridor**: the direct-eDP cable exits the Mu's onboard 40-pin
  connector (module near board (181, 45)) and runs rearward through the
  center gap between the hinges (x ~150-300 at y 0-12), folds over the rear
  wall into the lid. Bend radius >= 5 mm over the full sweep + service
  loop + no bracket contact at any angle — TO VERIFY (gate 2).

## 6. Case mounting

- Mainboard: M2.5 x 4-6 mm through isolated NPTHs H10-H17 into bottom-cover
  bosses (6 mm OD, 2.5 mm high, 0.5 mm radial clearance; no copper within
  1.5 mm of the boss). Board is canonical (`RETENTION_AND_MOUNTING_RELEASE.md`).
- Mu module: Wurth 9774055243R M2 standoffs H1 (238.3, 76.8), H2 (238.3, 13.2);
  module M2 x 4 screws, <= 0.2 N*m (component max; production torque after
  sample fit).
- M.2 cards: M2 standoffs H3/H4 per the M.2 retention table.
- Lid: panel adhesive + locating pins (positions TO MEASURE); hinge bosses
  reinforced; eDP channel; bezel 3 mm sides / 10.5 mm top-bottom.
- Cutouts follow board Edge.Cuts + connector shells:
  left USB-Cs at base Y 25/70; right USB-C at Y 135; Ethernet recess
  x 352.78-358, y 88-107 (opening 17.98 x 9.69 mm, jack body +2.1 mm into
  the recess); rear headphone jack ~x 50; rear exhaust grille x 70-120;
  mic acoustic port at board (40, 110) sealed through the bottom cover.

## 7. Measurement gates (in addition to gates 1-10)

11. Framework 13 hinge kit: bracket geometry, screw size/count, pivot
    offset, torque, geometry at 0/90/135°.
12. Cell thickness + tabs + swelling allowance — governs the Z-stack and
    the DB-over-cell clearance.
13. Assembled weight balance left/right.
14. Keyboard plate-to-cooling clearance (>= 2 mm) with the real stack.
15. eDP cable length/route through the hinge at every lid angle.
16. Trackpad thickness + click travel — governs the deck plane height.
