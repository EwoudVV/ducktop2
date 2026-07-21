# MX ULP fixation-pad microstencil

This is a reusable one-switch stencil for the five mechanical fixation pads on
the Ducktop2 Rev A MX ULP footprint. The two electrical contact pads are
intentionally covered and must receive a small manual paste deposit before the
switch is placed.

The full keyboard is 273.5 mm long, which does not fit a P1S bed. A full row
stencil would also accumulate more XY scale error and would have to bridge the
already-populated diodes. This stencil registers directly in the three MX ULP
locating holes and is reused for all 65 switches.

## Output

- `ducktop2_mx_ulp_fixation_microstencil_revA.stl`
- `ducktop2_mx_ulp_fixation_microstencil_revA_p1s_0p4.3mf`
- `bambu_p1s_0p4_stencil_process.json`
- `stencil_manifest.json`
- `generate_stencil.py`

The 3MF is the convenient P1S version with the validated layer settings already
embedded. The STL is the geometry-only source requested for general use.

The STL is already in print orientation and pre-mirrored. Print it exactly as
loaded: the membrane lies on the bed and the three tapered pegs point upward.
For use, flip it over so the pegs point down into the PCB.

## P1S print settings

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
- Print two or three copies because the 0.12 mm membrane is intentionally thin.

Confirm in Preview that the membrane is exactly one 0.12 mm layer. A default
0.20 mm first layer will deposit too much paste and must not be used. Let the
plate cool before lifting the stencil. The bed-facing side becomes the smooth
squeegee face.

## Dry fit

Dry-fit the stencil on a spare PCB before exposing it to paste. All three pegs
must enter without force and the membrane must lie flat. Do not scale the STL
to fix a tight peg because that would move the apertures. Lightly polish only
the affected peg with fine abrasive or a sharp blade.

The diode-side stencil edge clears the nominal SOD-323 package body by 0.40 mm
and clears its KiCad courtyard by 0.15 mm. The remaining web beside the right
paste apertures is 0.30 mm and is handled by the Arachne wall generator. If an
unusually shifted diode still touches the stencil, trim only that right edge;
do not move or enlarge the five paste apertures.

## Pasting sequence

1. Work left to right so the lift tab stays clear of the previous switch.
2. Seat all three pegs and hold the membrane flat without bending the PCB.
3. Use one light squeegee pass across the five apertures. Do not make a mound.
4. Lift straight up using the tab.
5. Check that all five deposits are complete and similar in height.
6. Add a very small, equal paste streak to each of the two electrical pads.
7. Place the switch immediately and confirm its metal frame is sitting flat.

Do a complete dry run and then a paste/reflow trial with two switches on one of
the spare PCBs before committing the 65-key board. That can all be done during
the same soldering day.

## Geometry

- Paste membrane: 0.12 mm.
- Fixation-pad aperture inset: 0.20 mm per edge.
- Aperture area: 58.3% to 67.1% of the matching copper pad.
- Registration pegs: 0.65 mm long, tapered, with nominal bases of 0.80 mm and
  0.95 mm for the 1.05 mm and 1.20 mm PCB holes.
- Overall print envelope: 17.45 x 13.5 x 0.77 mm including the lift tab and pegs.

The generator verifies the current KiCad footprint dimensions, all 65 switch
rotations, all 65 diode offsets, the 0.8 mm PCB thickness, and STL watertightness
before writing the manifest.

Regenerate with:

```sh
python3 -m pip install manifold3d trimesh networkx
python3 manufacturing/keyboard_revA_jlcpcb/mounting_pad_stencil/generate_stencil.py
```
