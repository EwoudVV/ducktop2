# Ducktop2 Rev A keyboard paste stencils

Two stencil options are available:

1. **Microstencil** — reusable single-switch stencil for one footprint at a time.
2. **Full-board stencil** — one-piece stencil covering all 65 switches with
   built-in diode clearance cutouts.

---

## 1. MX ULP fixation-pad microstencil

A reusable one-switch stencil for the five mechanical fixation pads on
the Ducktop2 Rev A MX ULP footprint. The two electrical contact pads are
intentionally covered and must receive a small manual paste deposit before the
switch is placed.

This stencil registers directly in the three MX ULP locating holes and is reused
for all 65 switches. Use this when you want to paste one switch at a time, or
when your printer cannot fit the full board.

### Output

- `ducktop2_mx_ulp_fixation_microstencil_revA.stl`
- `ducktop2_mx_ulp_fixation_microstencil_revA_p1s_0p4.3mf`
- `bambu_p1s_0p4_stencil_process.json`
- `stencil_manifest.json`
- `generate_stencil.py`

### Geometry

- Paste membrane: 0.12 mm.
- Fixation-pad aperture inset: 0.20 mm per edge.
- Aperture area: 58.3% to 67.1% of the matching copper pad.
- Registration pegs: 0.65 mm long, tapered, with nominal bases of 0.80 mm and
  0.95 mm for the 1.05 mm and 1.20 mm PCB holes.
- Overall print envelope: 17.45 x 13.5 x 0.77 mm including the lift tab and pegs.

---

## 2. Full-board paste stencil

A one-piece stencil covering all 65 Cherry MX ULP switches at their exact PCB
positions. Includes:

- 5 fixation-pad apertures per switch (325 total), inset 0.20 mm per edge
- Through-hole clearance cutouts at all 65 SOD-323 diode positions
- 3 short alignment nibs registering on switch locating holes
- 3 mm handling border around the PCB outline
- Lift tab at the FFC connector edge

The diodes are populated during PCBA and their bodies protrude above the PCB
surface. The diode cutouts (2.0 x 3.4 mm each at the exact diode position) let
the stencil lie flat across the entire board without the diode bodies lifting
the membrane.

### Print size

Board dimensions: 273.5 x 80 mm. The P1S bed is 256 x 256 mm. The stencil fits
**diagonally** on the P1S — load the STL and rotate ~16 degrees. The 256 mm
square bed diagonal of 362 mm easily accommodates the 273.5 mm long board.

### Output

- `ducktop2_fullboard_stencil_revA.stl` — geometry STL, pre-mirrored for printing
- `ducktop2_fullboard_stencil_revA.3mf` — 3MF with geometry only
- `fullboard_stencil_manifest.json` — validation manifest with SHA256s
- `bambu_p1s_0p4_fullboard_process.json` — Bambu Studio process preset
- `generate_fullboard_stencil.py` — generator script

### Registration

Three short alignment nibs (0.3 mm tall, tapered) register in the 1.05 mm
locating NPTHs of the leftmost, center, and rightmost switches on the top row.
The nibs are short enough that they only guide alignment; the 3 mm border
provides the primary registration on the board edges. Dry-fit on the bare PCB
before using paste.

### Diode cutout clearance

Each SOD-323 diode is at (switch_x + 8.2, switch_y), rotated 90 degrees. The
2.0 x 3.4 mm through-hole cutout at each diode position provides approximately
0.38 mm clearance per side around the diode body (nominal 1.25 x 2.0 mm at
90 degrees). The web between the right-edge fixation apertures and the adjacent
diode cutout is 0.4 mm, which prints reliably with the Arachne wall generator
at 0.35 mm line width.

---

## P1S print settings (both stencils)

- Material: dry PLA or PLA+; avoid PETG stringing for this part.
- Plate: smooth PEI or another genuinely smooth plate.
- Nozzle: 0.4 mm; a 0.2 mm nozzle is even better but is not required.
- First layer: 0.12 mm.
- Remaining layers: 0.08 mm.
- Line width: 0.35 mm.
- Wall generator: Arachne.
- Elephant-foot compensation: 0.10 mm.
- First-layer speed: 20 mm/s.
- Supports: off.
- Brim: off. Use a two-loop skirt.
- Ironing: off.
- Full-board stencil: print one copy (membrane has ~2750 mm³ volume).
- Microstencil: print two or three copies (the 0.12 mm membrane is intentionally
  thin and spares are useful).

---

## Print orientation (both stencils)

The STLs are already in print orientation and pre-mirrored. Print them exactly
as loaded: the membrane lies on the bed and the pegs/nibs point upward.
For use, flip the stencil over so the pegs/nibs point down into the PCB.
The bed-facing side becomes the smooth squeegee face.

Confirm in Preview that the membrane is exactly one 0.12 mm layer. A default
0.20 mm first layer will deposit too much paste and must not be used. Let the
plate cool before lifting the stencil.

---

## Dry fit

Dry-fit the stencil on a bare PCB before exposing it to paste. For the
microstencil, all three pegs must enter without force and the membrane must lie
flat. For the full-board stencil, the alignment nibs should enter the locator
holes at the three registration positions. The remaining locator holes are
covered by the membrane but do not need pegs.

Do not scale the STL to fix a tight fit — that would move the apertures away
from the copper pads. Lightly polish only the affected peg/nib with fine
abrasive or a sharp blade.

---

## Pasting sequence (full-board stencil)

1. Lay the stencil on the PCB, aligning the three nibs and the board outline.
   Tape the border corners if the stencil shifts during squeegee passes.
2. One light squeegee pass across all 325 apertures. Do not make a mound.
3. Lift straight up using the right-edge tab.
4. Check that all 325 deposits are complete and similar in height.
5. Add a very small, equal paste streak to each of the 130 electrical pads
   (pads 1 and 2 on each switch).
6. Place all 65 switches immediately and confirm every metal frame is sitting
   flat.

---

## Generator scripts

Both stencils are generated from the KiCad PCB file. The generators verify:

- KiCad footprint dimensions match expected values
- All 65 switches are present at 0-degree rotation
- A diode is present 8.2 mm to the right of every switch
- PCB thickness is 0.8 mm
- STL is watertight, winding-consistent, and one connected body

Regenerate with:

```sh
python3 -m pip install manifold3d trimesh networkx

# Microstencil (single switch)
python3 manufacturing/keyboard_revA_jlcpcb/mounting_pad_stencil/generate_stencil.py

# Full-board stencil
python3 manufacturing/keyboard_revA_jlcpcb/mounting_pad_stencil/generate_fullboard_stencil.py
```
